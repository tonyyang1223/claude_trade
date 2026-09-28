"""历史库完整性自检 / 修复（P0-1 / P0-2 回归护栏）。

检查「**单列二级索引损坏**」：某些 **``col = <字面量>`` 等值谓词的计数偏小甚至为 0**，
而全表扫才是真值（``content_archive.source='bilibili'`` 得 286 / 真值 455；
``category_membership.date='2026-06-27'`` 得 0 / 真值 1241 …）。根因是 **ART 二级索引损坏/陈旧**，
**不是数据损坏**（见 ARCHITECTURE §12）。修复 = ``DROP INDEX`` + ``CREATE INDEX`` **重建**
（幂等、不动数据、不碰 FTS），**严禁物理重写整表**。

关键点（务必遵守，否则会「假绿」）：
1. **覆盖全部单列索引列**，不限于 ``date``——只查 ``date`` 会漏
   ``content_archive.source`` / ``content_archive.coin_id`` / ``source_status.source``；
2. **真值必须「物化 + 纯全表扫」**（temp 表无索引）：普通 ``GROUP BY`` / 把等值下推进子查询
   都可能被坏索引一并答复而**一起算错**（见 ``etl_common.materialized_truth_counts``）。

用法（项目根目录）::

    python scripts/history/check_integrity.py          # 只读自检；有坏索引 → 退出码 1
    python scripts/history/check_integrity.py --fix    # 检测并**重建**损坏索引（需写锁）
    python scripts/history/check_integrity.py --db <path>

修复后自检应「0 处不一致」，退出码 0。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # 作为包导入
    from . import etl_common as ec
except ImportError:  # 直接以脚本运行
    import etl_common as ec  # type: ignore[no-redef]


def check_integrity(
    db_path: Optional[Path] = None,
    fix: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """执行完整性自检（可选重建损坏索引）。

    Args:
        db_path: 库文件路径；默认 ``ec.DB_PATH``。
        fix: 为 True 时**重建**所有损坏的单列二级索引（需要写连接 / 写锁）。

    Returns:
        ``{"db_path", "indexed_columns", "redundant_indexes", "mismatches_before",
            "rebuilt", "mismatches_after", "index_lost", "ok"}``。
    """
    ec.require_duckdb()
    target = Path(db_path) if db_path else ec.DB_PATH
    if not target.exists():
        raise SystemExit(f"[check_integrity] 历史库不存在：{target}")

    # --fix 需要写连接（DuckDB 单写者，勿与只读/其它 ETL 并发）；否则只读打开即可
    conn = ec.connect(target) if fix else _connect_read_only(target)
    try:
        indexed_columns = ec.single_column_indexes(conn)
        redundant = ec.redundant_date_indexes(conn)
        mismatches_before = ec.index_equality_mismatches(conn)

        rebuilt: List[str] = []
        index_lost = False
        mismatches_after = mismatches_before
        if fix and mismatches_before:
            report = ec.rebuild_damaged_indexes(conn)
            rebuilt = report["rebuilt"]
            index_lost = report["index_lost"]
            mismatches_after = report["mismatches_after"]
            if verbose:
                print(f"[check_integrity] 已重建损坏索引：{rebuilt}")
                if index_lost:
                    print(f"[check_integrity] ⚠️ 索引集合发生变化！"
                          f" before={report['indexes_before']} after={report['indexes_after']}")
        elif fix:
            mismatches_after = mismatches_before  # 无损坏，无需重建
    finally:
        conn.close()

    ok = (not mismatches_after) and (not index_lost)
    if verbose:
        print("=" * 68)
        print(f"[check_integrity] 库文件：{target}")
        print(f"[check_integrity] 单列索引 {len(indexed_columns)} 个："
              + ", ".join(f"{n}({t}.{c})" for n, t, c in indexed_columns))
        print("-" * 68)
        if mismatches_before:
            print("❌ 等值计数 ≠ 物化全表扫真值（索引损坏）：")
            for index_name, rows in mismatches_before.items():
                detail = "  ".join(f"{v}: indexed={e} truth={s}" for v, e, s in rows[:4])
                more = f" …(+{len(rows) - 4})" if len(rows) > 4 else ""
                print(f"   {index_name:22s} {detail}{more}")
        else:
            print("✅ 全部单列索引：等值计数 == 物化全表扫真值（0 处不一致）")
        if rebuilt:
            print(f"🔧 已重建：{rebuilt}"
                  + ("（复检仍不一致！）" if mismatches_after else "（复检通过）"))
        if redundant:
            print(f"ℹ️ 冗余单列 date 索引（PK 首列即该列，建议不建）：{redundant}")
        if index_lost:
            print("🔴 索引集合在重建过程中发生变化（有索引丢失）——请人工检查！")
        print("-" * 68)
        print(f"[check_integrity] 结论：{'PASS ✓' if ok else 'FAIL ✗'}")
        print("=" * 68)

    return {
        "db_path": str(target),
        "indexed_columns": indexed_columns,
        "redundant_indexes": redundant,
        "mismatches_before": mismatches_before,
        "rebuilt": rebuilt,
        "mismatches_after": mismatches_after,
        "index_lost": index_lost,
        "ok": ok,
    }


def _connect_read_only(target: Path) -> Any:
    """以只读方式打开（自检默认不持写锁，避免阻塞/被阻塞）。"""
    import duckdb  # 局部导入，保持与 etl_common 一致的 HAS_DUCKDB guard 语义

    conn = duckdb.connect(str(target), read_only=True)
    ec.ensure_fts_extension(conn)
    return conn


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="历史库完整性自检/修复：单列二级索引「等值计数 vs 物化全表扫真值」"
    )
    parser.add_argument("--db", default=str(ec.DB_PATH), help="库文件路径")
    parser.add_argument("--fix", action="store_true", help="重建损坏的单列二级索引（需写锁）")
    parser.add_argument("--quiet", action="store_true", help="减少输出")
    args = parser.parse_args(argv)

    result = check_integrity(db_path=Path(args.db), fix=args.fix, verbose=not args.quiet)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
