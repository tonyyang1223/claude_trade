"""增量入库：按「文件水位线 + md5/mtime 跳过未变更文件」，只写入新数据，**末步重建双列 FTS**。

设计依据：`docs/history-db/ARCHITECTURE.md` §5.4（幂等）、§6（定时增量 Q1）、§11-T05。

用法（在项目根目录执行）::

    python scripts/history/ingest_history.py --incremental
    python scripts/history/ingest_history.py --incremental --dry-run   # 只报告，不写库

⚠️ **顺序硬约束（违反 → 数据进了库却搜不到）**：
``create_fts_index`` 建立的是**静态索引**，只覆盖「建索引那一刻已存在的行」；
之后的 INSERT **不会**自动进入索引。故本脚本固定流程为「**先写完所有数据行 → 最后重建 FTS**」。

并发约定（ARCHITECTURE §5.4）：增量入库为**独立进程、独占写**（DuckDB 单写者），
**不要**与只读查询 / 其他写进程并发运行。

幂等（ARCHITECTURE §5.4 / §12）：
- 数据层：主表 UPSERT、可缩小子表按自然键单元「事务内 DELETE + INSERT」；
- 台账层：增量批次使用**确定性 batch_id**（``incremental-history``），
  使 ``ingest_batch``（PK=batch_id）与 ``ingest_file_log``（PK=(batch_id,file_path)）
  天然 upsert，**重复跑各表行数完全不变**。
  （偏离 §5.3「增量用时间戳批次」——为让台账层可复跑幂等，这里采用确定性 id；
  如需保留每次增量的历史行，改用时间戳批次并接受台账随运行增长。）

水位线口径：``scan`` 取 ``MAX(scan_day.date)``、``macro`` 取 ``MAX(macro_snapshot.date)``；
**只考虑 ``date >= 水位线`` 的候选**（用 ``>=`` 而非 ``>`` 是为了不漏「水位当日新增的
macro 快照」——macro 一天会有多个 ``HHMM`` 快照，严格 ``>`` 会丢弃当日后续快照），
再由**逐文件 md5/mtime 跳过**决定是否真正处理，故「无新数据」时近乎零成本。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # 作为包导入（scripts.history.ingest_history）
    from . import etl_common as ec
    from .export_grams import make_grams
    from .init_db import build_fts_index, fts_index_ready, get_stats, print_report
    from .load_daily_scan import (
        CATEGORY_DIRNAME,
        DEEP_DIRNAME,
        LIGHT_DIRNAME,
        LIGHT_FILENAME,
        SUMMARY_FILENAME,
        list_scan_dates,
        load_daily_scan,
    )
    from .load_macro import list_macro_snapshots, load_macro
except ImportError:  # 直接以脚本运行（python scripts/history/ingest_history.py）
    import etl_common as ec  # type: ignore[no-redef]
    from export_grams import make_grams  # type: ignore[no-redef]
    from init_db import build_fts_index, fts_index_ready, get_stats, print_report  # type: ignore[no-redef]
    from load_daily_scan import (  # type: ignore[no-redef]
        CATEGORY_DIRNAME,
        DEEP_DIRNAME,
        LIGHT_DIRNAME,
        LIGHT_FILENAME,
        SUMMARY_FILENAME,
        list_scan_dates,
        load_daily_scan,
    )
    from load_macro import list_macro_snapshots, load_macro  # type: ignore[no-redef]

# 确定性增量批次号（重跑复用同一行 → 台账层天然幂等，见模块 docstring）
INCREMENTAL_BATCH_ID = ec.stable_batch_id("incremental", "history")

# FTS 冒烟基线（当前语料实测）：英文整词 + 中文子串各一条。
# 增量**只增不减**，故用 ``>=`` 判定「索引未被破坏」（小于基线 = 索引丢数据 → 失败）。
FTS_SMOKE_EXPECT: Dict[str, int] = {"Solana": 869, "哔哩哔哩": 455}


# --------------------------------------------------------------------------
# 水位线 / 候选文件
# --------------------------------------------------------------------------
def _max_date(conn: Any, table: str) -> Optional[str]:
    """取 ``table.date`` 的最大值（``YYYY-MM-DD``）；空表 / 失败返回 ``None``。"""
    try:
        row = conn.execute(f"SELECT MAX(date) FROM {table}").fetchone()
    except Exception as exc:  # noqa: BLE001
        print(f"[ingest] 查询 {table} 水位线失败：{exc}")
        return None
    if not row or row[0] is None:
        return None
    value = row[0]
    return value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value)[:10]


def _scan_day_files(day_dir: Path) -> List[Path]:
    """一个扫描日目录下的全部源文件（供 md5/mtime 跳过判断）。

    覆盖 ``summary.json`` + ``top_800_light/all_coins.json`` + ``top_50_detailed/*.json``
    + ``by_category/<slug>/*.json``——与 ``load_daily_scan`` 实际读取的文件集合一致。
    """
    files: List[Path] = []
    summary = day_dir / SUMMARY_FILENAME
    if summary.is_file():
        files.append(summary)
    light = day_dir / LIGHT_DIRNAME / LIGHT_FILENAME
    if light.is_file():
        files.append(light)
    deep_dir = day_dir / DEEP_DIRNAME
    if deep_dir.is_dir():
        files.extend(sorted(deep_dir.glob("*.json")))
    cat_dir = day_dir / CATEGORY_DIRNAME
    if cat_dir.is_dir():
        files.extend(sorted(cat_dir.glob("*/*.json")))
    return files


def _is_unchanged(path: Path, states: Dict[str, Dict[str, Any]]) -> bool:
    """文件是否「已成功登记且内容未变」→ 可跳过。

    判定：先比 ``mtime``（快路径，未变则不读文件）；``mtime`` 变了再比 ``md5``
    （内容相同则仍可跳过，如重新拷贝但内容一致）。仅当上次 ``status == "ok"`` 才跳过。
    """
    st = states.get(ec.to_rel(path))
    if not st or st.get("status") != "ok":
        return False
    logged_mtime = st.get("mtime")
    cur_mtime = ec.file_mtime(path)
    if logged_mtime is not None and cur_mtime is not None and logged_mtime == cur_mtime:
        return True
    logged_md5 = st.get("md5") or ""
    return bool(logged_md5) and logged_md5 == ec.file_md5(path)


def _scan_candidates(
    root: Path,
    watermark: Optional[str],
    states: Dict[str, Dict[str, Any]],
) -> Tuple[List[str], List[str], int]:
    """扫描日候选：返回 ``(待处理日, 跳过日, 待处理日涉及源文件数)``。

    只考虑 ``date >= watermark`` 的日；日目录内**全部**源文件均未变 → 跳过该日。
    """
    process_dates: List[str] = []
    skipped_dates: List[str] = []
    n_files = 0
    for name in list_scan_dates(root):
        if watermark and name < watermark:
            continue
        files = _scan_day_files(root / name)
        changed = [f for f in files if not _is_unchanged(f, states)]
        if changed:
            process_dates.append(name)
            n_files += len(files)
        else:
            skipped_dates.append(name)
    return process_dates, skipped_dates, n_files


def _macro_candidates(
    root: Path,
    watermark: Optional[str],
    states: Dict[str, Dict[str, Any]],
) -> Tuple[List[Tuple[str, str, Path]], List[Tuple[str, str, Path]]]:
    """宏观快照候选：返回 ``(待处理快照, 跳过快照)``，均为 ``(date, HHMM, path)``。"""
    process: List[Tuple[str, str, Path]] = []
    skipped: List[Tuple[str, str, Path]] = []
    for date, snapshot_time, path in list_macro_snapshots(root):
        if watermark and date < watermark:
            continue
        (skipped if _is_unchanged(path, states) else process).append((date, snapshot_time, path))
    return process, skipped


# --------------------------------------------------------------------------
# FTS 复验
# --------------------------------------------------------------------------
def _fts_totals(conn: Any) -> Dict[str, int]:
    """用 ``match_bm25(conjunctive:=false)`` 取 FTS 命中数。

    查询串必须与入库 ``body_grams`` 同口径 —— **复用 ``make_grams``**（中文 bigram 化），
    否则 ``'哔哩哔哩'`` 会被 simple 分词器当单个 token 而命中 0。
    """
    totals: Dict[str, int] = {}
    for label, raw in (("Solana", "Solana"), ("哔哩哔哩", "哔哩哔哩")):
        query = make_grams(raw)
        totals[label] = int(
            conn.execute(
                "SELECT COUNT(*) FROM content_archive c "
                "WHERE fts_main_content_archive.match_bm25"
                "(c.content_id, ?, conjunctive := false) IS NOT NULL",
                [query],
            ).fetchone()[0]
        )
    return totals


def verify_fts(conn: Any, verbose: bool = True) -> Tuple[bool, Dict[str, int]]:
    """增量后 FTS 可检索性复验：英文整词 ``Solana`` + 中文子串 ``哔哩哔哩`` ≥ 基线。

    Returns:
        ``(ok, totals)``；``ok=False`` 表示索引覆盖少于基线（疑似重建失败/丢行）。
    """
    try:
        totals = _fts_totals(conn)
    except Exception as exc:  # noqa: BLE001
        print(f"[ingest] ⚠️ FTS 复验失败（索引不可用？）：{exc}")
        return False, {}
    ok = all(totals.get(k, 0) >= v for k, v in FTS_SMOKE_EXPECT.items())
    if verbose:
        detail = "  ".join(f"{k}={totals.get(k)}" for k in FTS_SMOKE_EXPECT)
        mark = "PASS ✓" if ok else "FAIL ✗（索引覆盖不足）"
        print(f"[ingest] FTS 复验 [{mark}]：{detail}（基线 "
              + ", ".join(f"{k}>={v}" for k, v in FTS_SMOKE_EXPECT.items()) + "）")
    return ok, totals


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def _assert_schema(conn: Any) -> None:
    """预检：库中必须有 ``scan_day``（否则 ``init_db`` / ``backfill`` 未跑）。"""
    try:
        conn.execute("SELECT 1 FROM scan_day LIMIT 1")
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"[ingest] 历史库 schema 未就绪（scan_day 缺失）：{exc}\n"
            "         请先执行：python scripts/history/init_db.py && "
            "python scripts/history/backfill_history.py"
        ) from exc


def run_incremental(
    db_path: Optional[Path] = None,
    scan_dir: Optional[Path] = None,
    macro_dir: Optional[Path] = None,
    dry_run: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """执行一次增量入库。

    Returns:
        ``{"batch_id", "dry_run", "scan_dates", "macro_snapshots",
            "counts", "row_delta", "fts_rebuilt", "fts_ok", "fts_totals",
            "integrity_ok", "integrity_created", "integrity_rebuilt",
            "integrity_mismatches", "missing_indexes", "stats"}``。
    """
    ec.require_duckdb()
    target = Path(db_path) if db_path else ec.DB_PATH
    if not target.exists():
        raise SystemExit(
            f"[ingest] 历史库不存在：{target}\n"
            "         请先执行：python scripts/history/init_db.py && "
            "python scripts/history/backfill_history.py"
        )

    conn = ec.connect(target)
    try:
        _assert_schema(conn)
        base_counts = get_stats(conn, target)["table_counts"]
        states = ec.latest_file_states(conn)

        scan_root = Path(scan_dir) if scan_dir else ec.DAILY_SCAN_DIR
        macro_root = Path(macro_dir) if macro_dir else ec.MACRO_DIR
        scan_wm = _max_date(conn, "scan_day")
        macro_wm = _max_date(conn, "macro_snapshot")

        scan_days, scan_skipped, scan_files = _scan_candidates(scan_root, scan_wm, states)
        macro_proc, macro_skipped = _macro_candidates(macro_root, macro_wm, states)

        if verbose:
            print(f"[ingest] 水位线：scan_day<={scan_wm or '∅'} / macro_snapshot<={macro_wm or '∅'}")
            print(f"[ingest] scan：待入 {len(scan_days)} 日（≈{scan_files} 文件）/ "
                  f"跳过 {len(scan_skipped)} 日")
            print(f"[ingest] macro：待入 {len(macro_proc)} 快照 / 跳过 {len(macro_skipped)} 快照")

        result: Dict[str, Any] = {
            "batch_id": INCREMENTAL_BATCH_ID,
            "dry_run": bool(dry_run),
            "scan_dates": scan_days,
            "scan_skipped_dates": scan_skipped,
            "macro_snapshots": [(d, t) for d, t, _ in macro_proc],
            "macro_skipped": [(d, t) for d, t, _ in macro_skipped],
        }

        if dry_run:
            if verbose:
                print("[ingest] --dry-run：仅报告，未写库")
            return result

        # ---- 回收历史悬挂批次（此时已持有写锁 ⇒ 无活跃写者，任何 running 行都是残留）----
        reaped = ec.reap_stale_batches(conn)
        if reaped and verbose:
            print(f"[ingest] 已回收悬挂批次（status→interrupted）：{reaped}")

        # ---- 开批次（确定性 batch_id + 批次级时间戳）；生命周期由 running_batch 兜底 ----
        batch_id = INCREMENTAL_BATCH_ID
        batch_ts = ec.local_now()
        counts: Dict[str, int] = {}
        with ec.running_batch(conn, batch_id, "incremental", "history") as box:
            # ④ 写 scan（先写数据）
            if scan_days:
                for key, value in load_daily_scan(
                    conn, batch_id, daily_dir=scan_root, verbose=verbose,
                    dates=scan_days, batch_processed_at=batch_ts,
                ).items():
                    counts[key] = counts.get(key, 0) + value
                box["rows"] = sum(counts.values())
            # ⑤ 写 macro
            if macro_proc:
                for key, value in load_macro(
                    conn, batch_id, macro_dir=macro_root, verbose=verbose,
                    snapshots=macro_proc, batch_processed_at=batch_ts,
                ).items():
                    counts[key] = counts.get(key, 0) + value
                box["rows"] = sum(counts.values())

            rows_loaded = sum(counts.values())

            # ⑦ **最后**重建双列 FTS（顺序硬约束）——无写入且索引已在则不重建（省算力）
            if rows_loaded > 0 or not fts_index_ready(conn):
                build_fts_index(conn, verbose=verbose)
                fts_rebuilt = True
            else:
                fts_rebuilt = False
                if verbose:
                    print("[ingest] 无新数据：跳过 FTS 重建（索引已在）")
        # running_batch 正常退出即落 success；异常/中断 → failed/interrupted 并向上抛

        after_counts = get_stats(conn, target)["table_counts"]
        all_keys = set(after_counts) | set(base_counts)
        row_delta = {
            k: after_counts.get(k, 0) - base_counts.get(k, 0)
            for k in sorted(all_keys)
            if after_counts.get(k, 0) - base_counts.get(k, 0) != 0
        }

        fts_ok, fts_totals = verify_fts(conn, verbose=verbose)

        # 完整性自愈（§12 / §13-O11）：**按 ddl.sql 补齐缺失索引** + **重建「存在但算错」索引**
        # （与 check_integrity --fix 共用同一自愈例程 ec.heal_indexes）
        heal = ec.heal_indexes(conn)
        integrity_created = heal["created"]
        integrity_rebuilt = heal["rebuilt"]
        integrity_dropped = heal["dropped_redundant"]
        integrity_bad = heal["mismatches_after"]
        missing_indexes = heal["missing_after"]
        integrity_ok = bool(heal["ok"])
        if verbose:
            if integrity_ok and not (integrity_created or integrity_rebuilt):
                print("[ingest] 完整性自检 [PASS ✓]：预期 6 个索引齐备，且等值计数 == 物化全表扫真值")
            elif integrity_ok:
                print(f"[ingest] 完整性自检 [自愈 ✓]：补齐 {integrity_created}、"
                      f"重建 {integrity_rebuilt}，复检通过")
            else:
                reason = "索引损坏且重建后仍不一致" if integrity_bad else (
                    "重建期丢索引" if heal["index_lost"] else f"缺失预期索引 {missing_indexes}")
                print(f"[ingest] 完整性自检 [FAIL ✗]：{reason}")
            if integrity_dropped:
                print(f"[ingest] 已清理冗余 date 索引：{integrity_dropped}")
            if heal["unknown_unexpected"]:
                print(f"[ingest] ⚠️ 未知多余索引（不自动删除，请人工确认）：{heal['unknown_unexpected']}")

        result.update(
            {
                "counts": counts,
                "rows_loaded": rows_loaded,
                "row_delta": row_delta,
                "reaped_batches": reaped,
                "fts_rebuilt": fts_rebuilt,
                "fts_ok": fts_ok,
                "fts_totals": fts_totals,
                "integrity_ok": integrity_ok,
                "integrity_created": integrity_created,
                "integrity_rebuilt": integrity_rebuilt,
                "integrity_dropped_redundant": integrity_dropped,
                "integrity_mismatches": integrity_bad,
                "missing_indexes": missing_indexes,
                "stats": after_counts,
            }
        )
        if verbose:
            delta_desc = ", ".join(f"{k}:{v:+d}" for k, v in row_delta.items()) or "（无变化）"
            print(f"[ingest] 批次 {batch_id} 完成：status=success, rows_loaded={rows_loaded}")
            print(f"[ingest] 各表行数增量：{delta_desc}")
        return result
    finally:
        conn.close()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="claude_trading 历史库增量入库（水位线 + 跳未变更文件 + 末步重建 FTS）"
    )
    parser.add_argument(
        "--incremental", action="store_true",
        help="增量模式（当前唯一模式；与定时任务约定一致，缺省即增量）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只报告将处理什么，不写库")
    parser.add_argument("--db", default=str(ec.DB_PATH), help="库文件路径（默认 data/history/ct_history.duckdb）")
    parser.add_argument("--scan-dir", default=None, help="daily_scan 根目录（默认 data/reports/daily_scan）")
    parser.add_argument("--macro-dir", default=None, help="macro 根目录（默认 data/macro）")
    parser.add_argument("--quiet", action="store_true", help="减少过程日志")
    parser.add_argument("--stats", action="store_true", help="结束后打印库状态报告")
    args = parser.parse_args(argv)

    scan_dir = Path(args.scan_dir) if args.scan_dir else None
    macro_dir = Path(args.macro_dir) if args.macro_dir else None
    result = run_incremental(
        db_path=Path(args.db),
        scan_dir=scan_dir,
        macro_dir=macro_dir,
        dry_run=args.dry_run,
        verbose=not args.quiet,
    )

    if args.stats and "stats" in result:
        conn = ec.connect(Path(args.db))
        try:
            print_report(get_stats(conn, Path(args.db)))
        finally:
            conn.close()

    # 退出码：FTS 复验或完整性自检失败 → 2（让 cron 日志显式暴露「数据进了库却搜不到 / 查不全」）
    if result.get("dry_run"):
        return 0
    ok = result.get("fts_ok", True) and result.get("integrity_ok", True)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
