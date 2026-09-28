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
   都可能被坏索引一并答复而**一起算错**（见 ``etl_common.materialized_truth_counts``）；
3. **预期索引集合存在性断言**：除「重建期不丢索引」（``index_lost``）外，另把
   ``ddl.sql`` 声明的 **6 个具名索引**逐个查存在性（``etl_common.audit_expected_indexes``）——
   任何**非重建路径**的丢索引（误 ``DROP`` / 物理重写 / 半损坏）都会被抓住（ARCHITECTURE §12）。

``--fix`` 执行**索引自愈**（``etl_common.heal_indexes``，与 ETL 收尾共用同一例程）：
① **按 ``ddl.sql`` 原语句补齐「缺失」索引**（DDL 单一真源）；
② ``DROP`` + ``CREATE`` **重建「存在但算错」**的索引；
③ ``unexpected`` 里的**冗余 date 索引**清理，**未知**多余索引**只告警不自动删**。

用法（项目根目录）::

    python scripts/history/check_integrity.py          # 只读自检；有坏索引/缺索引 → 退出码 1
    python scripts/history/check_integrity.py --fix    # 自愈：补齐缺失 + 重建损坏（需写锁）
    python scripts/history/check_integrity.py --db <path>

自愈后应「0 处不一致」且「预期 6 个索引齐备」，退出码 0。
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
    """执行完整性自检（可选自愈：补齐缺失 + 重建损坏索引）。

    Args:
        db_path: 库文件路径；默认 ``ec.DB_PATH``。
        fix: 为 True 时执行**索引自愈**（``ec.heal_indexes``）——按 ``ddl.sql`` 补齐**缺失**索引
            + ``DROP/CREATE`` **重建**「存在但算错」的索引（需要写连接 / 写锁）。

    Returns:
        ``{"db_path", "expected_indexes", "missing_indexes", "indexed_columns",
            "redundant_indexes", "dropped_redundant_indexes", "unknown_unexpected_indexes",
            "mismatches_before", "created", "rebuilt", "mismatches_after", "index_lost", "ok"}``。
    """
    ec.require_duckdb()
    target = Path(db_path) if db_path else ec.DB_PATH
    if not target.exists():
        raise SystemExit(f"[check_integrity] 历史库不存在：{target}")

    # --fix 需要写连接（DuckDB 单写者，勿与只读/其它 ETL 并发）；否则只读打开即可
    conn = ec.connect(target) if fix else _connect_read_only(target)
    try:
        indexed_columns = ec.single_column_indexes(conn)
        expected = ec.expected_indexes()
        redundant = ec.redundant_date_indexes(conn)

        created: List[str] = []
        rebuilt: List[str] = []
        dropped_redundant: List[str] = []
        index_lost = False
        if fix:
            # 一套自愈例程（补齐缺失 + 重建损坏 + 清理冗余），与 ETL 收尾共用
            heal = ec.heal_indexes(conn, expected)
            mismatches_before = heal["mismatches_before"]
            mismatches_after = heal["mismatches_after"]
            created = heal["created"]
            rebuilt = heal["rebuilt"]
            dropped_redundant = heal["dropped_redundant"]
            index_lost = bool(heal["index_lost"])
            unknown_unexpected = heal["unknown_unexpected"]
            if verbose:
                if created:
                    print(f"[check_integrity] 已按 ddl.sql 补齐缺失索引：{created}")
                if heal["dropped_redundant"]:
                    print(f"[check_integrity] 已清理冗余 date 索引：{heal['dropped_redundant']}")
                if rebuilt:
                    print(f"[check_integrity] 已重建损坏索引：{rebuilt}")
                if index_lost:
                    print("[check_integrity] ⚠️ 重建期索引集合发生变化（有索引丢失）！")
        else:
            audit = ec.audit_expected_indexes(conn, expected)
            mismatches_before = ec.index_equality_mismatches(conn)
            mismatches_after = mismatches_before
            unexpected = audit["unexpected"]
            unknown_unexpected = sorted(set(unexpected) - set(redundant))
        # 复检预期索引集合（fix 与 non-fix 都算）：任何非重建路径的丢索引都在此暴露
        audit_after = ec.audit_expected_indexes(conn, expected)
    finally:
        conn.close()

    missing = audit_after["missing"]
    ok = (not mismatches_after) and (not index_lost) and (not missing)
    if verbose:
        print("=" * 68)
        print(f"[check_integrity] 库文件：{target}")
        print(f"[check_integrity] 预期索引 {len(expected)} 个：" + ", ".join(sorted(expected)))
        print(f"[check_integrity] 现存单列索引 {len(indexed_columns)} 个："
              + ", ".join(f"{n}({t}.{c})" for n, t, c in indexed_columns))
        print("-" * 68)
        if missing:
            print(f"🔴 缺失预期索引（库中不存在，疑似意外 DROP / 物理重写）：{missing}")
        else:
            print("✅ 预期索引集合完整（6 个具名索引全部存在）")
        if audit_after["unexpected"]:
            print(f"ℹ️ 库中多出预期外的索引（信息）：{audit_after['unexpected']}")
        if unknown_unexpected:
            print(f"⚠️ 未知多余索引（**不自动删除**，请人工确认归属）：{unknown_unexpected}")
        if mismatches_before:
            label = "【修复前】" if fix else ""
            print(f"❌ {label}等值计数 ≠ 物化全表扫真值（索引损坏）：")
            for index_name, rows in mismatches_before.items():
                detail = "  ".join(f"{v}: indexed={e} truth={s}" for v, e, s in rows[:4])
                more = f" …(+{len(rows) - 4})" if len(rows) > 4 else ""
                print(f"   {index_name:22s} {detail}{more}")
        else:
            print("✅ 全部单列索引：等值计数 == 物化全表扫真值（0 处不一致）")
        if created:
            print(f"🔧 已补齐缺失索引：{created}")
        if rebuilt:
            print(f"🔧 已重建：{rebuilt}"
                  + ("（复检仍不一致！）" if mismatches_after else "（复检通过）"))
        if redundant and not fix:
            print(f"ℹ️ 冗余单列 date 索引（PK 首列即该列，建议不建）：{redundant}")
        if index_lost:
            print("🔴 索引集合在重建过程中发生变化（有索引丢失）——请人工检查！")
        print("-" * 68)
        print(f"[check_integrity] 结论：{'PASS ✓' if ok else 'FAIL ✗'}")
        print("=" * 68)

    return {
        "db_path": str(target),
        "expected_indexes": sorted(expected),
        "missing_indexes": missing,
        "indexed_columns": indexed_columns,
        "redundant_indexes": redundant,
        "dropped_redundant_indexes": dropped_redundant,
        "unknown_unexpected_indexes": unknown_unexpected,
        "mismatches_before": mismatches_before,
        "created": created,
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
