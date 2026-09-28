"""回填编排：建表 → 开批次 → 载 daily_scan → 载 macro → 算残缺日 → **最后**建双列 FTS。

用法（在项目根目录执行）::

    python scripts/history/backfill_history.py            # 全量回填（幂等，可重复执行）

流程严格对齐 `docs/history-db/ARCHITECTURE.md` §5.1：

    ① 预检（HAS_DUCKDB guard）
    ② 建库建表（执行 §2 DDL，CREATE TABLE IF NOT EXISTS 幂等）
    ③ 开批次（ingest_batch: running，**确定性 batch_id=backfill-all**）
    ④ 遍历 9 扫描日（light/deep/source_status/category_membership/content_archive）
    ⑤ 遍历 19 宏观日 / 45 快照（macro_snapshot + 3 子表）
    ⑥ 计算派生：更新 scan_day.is_partial
    ⑦ **数据全部写完后**建/重建双列 FTS（索引为静态，顺序敏感；见 §0 验证1）
    ⑧ 关批次（success + rows_loaded）
    ⑨ 打印 get_stats()（各表行数 / 视图 / FTS 状态 / 库体积）

幂等说明（两层，缺一不可）：
1. **数据层**：主表 UPSERT / 可缩小子表按自然键单元事务内 DELETE+INSERT；
2. **台账层**：全量回填使用**确定性 batch_id**（``backfill-all``），
   使 ``ingest_batch`` / ``ingest_file_log`` 主键天然幂等，无需清理也不会随重跑增长。

本脚本**每次都是全量重跑**（不做「跳过未变更文件」优化），
以便让「连续执行两次、行数完全相同」成为 UPSERT / DELETE+INSERT 幂等性的**真实证据**；
「跳过未变更文件」的性能优化留给增量入库（T05）。
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # 作为包导入
    from . import etl_common as ec
    from .init_db import apply_schema, build_fts_index, get_stats, print_report
    from .load_daily_scan import load_daily_scan
    from .load_macro import load_macro
except ImportError:  # 直接以脚本运行
    import etl_common as ec  # type: ignore[no-redef]
    from init_db import apply_schema, build_fts_index, get_stats, print_report  # type: ignore[no-redef]
    from load_daily_scan import load_daily_scan  # type: ignore[no-redef]
    from load_macro import load_macro  # type: ignore[no-redef]

# 残缺日判定口径（ARCHITECTURE §2 尾注）：
#   deep_files_actual < GREATEST(4, 0.5 × median(近 7 日 deep_files_actual)) → is_partial=TRUE
PARTIAL_WINDOW = 7
PARTIAL_ABS_FLOOR = 4
PARTIAL_RATIO = 0.5


def compute_partial_flags(
    conn: Any,
    window: int = PARTIAL_WINDOW,
    verbose: bool = True,
) -> Dict[str, bool]:
    """按「近 7 日 deep_files_actual 的 0.5 倍中位数（下限 4）」判定并回写 ``scan_day.is_partial``。

    以**落盘事实**（``deep_files_actual``）为准，不采信 ``summary.deep_researched``
    （实测 08-25 声明 69、实际 55）。残缺日**原样入库 + 标记**，不伪造不插值（R7 / Q3）。

    Returns:
        ``{date_str: is_partial}``。
    """
    rows = conn.execute("SELECT date, deep_files_actual FROM scan_day ORDER BY date").fetchall()
    dates: List[Any] = [r[0] for r in rows]
    actual: Dict[Any, int] = {r[0]: int(r[1] or 0) for r in rows}

    flags: Dict[str, bool] = {}
    for idx, day in enumerate(dates):
        # 「近 7 日」= 含当日在内的最近 N 个扫描日（不足 N 则取全部）
        window_values = [actual[d] for d in dates[max(0, idx - window + 1) : idx + 1]]
        median = statistics.median(window_values)
        threshold = max(PARTIAL_ABS_FLOOR, PARTIAL_RATIO * median)
        flags[day.isoformat()] = bool(actual[day] < threshold)

    for date_str, is_partial in flags.items():
        conn.execute("UPDATE scan_day SET is_partial = ? WHERE date = ?", [is_partial, date_str])

    if verbose:
        partial_days = [d for d, flag in flags.items() if flag]
        print(
            f"[backfill] 残缺日判定完成：共 {len(flags)} 日，残缺 {len(partial_days)} 日 "
            f"{partial_days}"
        )
    return flags


def run_backfill(
    db_path: Optional[Path] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """执行一次完整回填（幂等）。

    Returns:
        字典：``batch_id``、各表行数 ``counts``、``partial_flags``、``fts_ready``、
        ``stats``（``init_db.get_stats`` 结果）。
    """
    ec.require_duckdb()
    target = Path(db_path) if db_path else ec.DB_PATH
    conn = ec.connect(target)
    result: Dict[str, Any] = {}
    try:
        # ② 建库建表（幂等）
        apply_schema(conn, verbose=verbose)

        # ③ 开批次（**确定性** batch_id → ingest_batch/ingest_file_log 主键天然幂等，无需清理）
        #    先回收上次被中断遗留的悬挂批次（此刻已持写锁 ⇒ 无活跃写者，running 行必为残留）
        reaped = ec.reap_stale_batches(conn)
        if reaped and verbose:
            print(f"[backfill] 已回收悬挂批次（status→interrupted）：{reaped}")
        batch_id = ec.stable_batch_id("backfill", "all")
        result["batch_id"] = batch_id
        if verbose:
            print(f"[backfill] 批次 {batch_id} 开始（mode=backfill, scope=all）")

        counts: Dict[str, int] = {}
        # 生命周期由 running_batch 兜底：异常/中断也会落终态，不留 running（见 etl_common）
        with ec.running_batch(conn, batch_id, "backfill", "all") as box:
            # ④ 扫描日
            for key, value in load_daily_scan(conn, batch_id, verbose=verbose).items():
                counts[key] = counts.get(key, 0) + value
            box["rows"] = sum(counts.values())
            # ⑤ 宏观
            for key, value in load_macro(conn, batch_id, verbose=verbose).items():
                counts[key] = counts.get(key, 0) + value
            box["rows"] = sum(counts.values())
            # ⑥ 派生：残缺日
            flags = compute_partial_flags(conn, verbose=verbose)
            # ⑦ **最后**建双列 FTS（必须晚于所有数据写入）
            fts_ready = build_fts_index(conn, verbose=verbose)
            # ⑦′ 完整性自检（§12/§13-O11）：单列二级索引损坏 → **自动重建**（DROP+CREATE，不动数据）
            integrity_before = ec.index_equality_mismatches(conn)
            integrity_rebuilt = []
            if integrity_before:
                repair = ec.rebuild_damaged_indexes(conn)
                integrity_rebuilt = repair["rebuilt"]
                integrity_bad = repair["mismatches_after"]
                integrity_ok = (not integrity_bad) and (not repair["index_lost"])
            else:
                integrity_bad = {}
                integrity_ok = True
        rows_loaded = sum(counts.values())

        if verbose:
            if integrity_ok and not integrity_rebuilt:
                print("[backfill] 完整性自检 [PASS ✓]：全部单列索引与物化全表扫真值一致")
            elif integrity_ok:
                print(f"[backfill] 完整性自检 [修复 ✓]：重建损坏索引 {integrity_rebuilt}，复检通过")
            else:
                print(f"[backfill] 完整性自检 [FAIL ✗]：索引损坏且重建后仍不一致 {integrity_bad}")

        result.update(
            {
                "counts": counts,
                "rows_loaded": sum(counts.values()),
                "partial_flags": flags,
                "fts_ready": fts_ready,
                "integrity_ok": integrity_ok,
                "integrity_rebuilt": integrity_rebuilt,
                "integrity_mismatches": integrity_bad,
            }
        )

        # ⑨ 打印统计
        stats = get_stats(conn, target)
        result["stats"] = stats
        if verbose:
            print_report(stats)
            print(
                f"[backfill] 批次 {batch_id} 完成：status=success, rows_loaded={result['rows_loaded']}"
            )
        return result
    finally:
        conn.close()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="claude_trading 历史库全量回填（幂等）")
    parser.add_argument(
        "--db", default=str(ec.DB_PATH), help="库文件路径（默认 data/history/ct_history.duckdb）"
    )
    parser.add_argument("--quiet", action="store_true", help="减少过程日志，仅打印最终报告")
    args = parser.parse_args(argv)

    result = run_backfill(db_path=Path(args.db), verbose=not args.quiet)
    ok = bool(result.get("fts_ready", True)) and bool(result.get("integrity_ok", True))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
