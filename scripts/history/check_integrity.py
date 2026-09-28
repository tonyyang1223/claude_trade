"""历史库完整性自检（P0-1 / P0-2 回归护栏）。

检查两类问题：

1. **等值查找 vs 全表扫不一致**（`date_equality_mismatches`）：
   逐表逐日比较 ``WHERE date = ?::DATE``（可能命中单列 date 二级索引）与
   ``WHERE date::VARCHAR = ?``（强制全表扫，即真值）。不一致 ⇒ 存在「陈旧二级索引
   遮蔽正确 PK 索引」的等值查找错误 —— 即 P0-1（category_membership 06-27 查得 0/真值 1241）
   与 P0-2（source_status 06-30 查得 618/真值 871）。

2. **冗余单列 date 二级索引**（`redundant_date_indexes`）：
   表达式单列且等于该表 PK 首列 ⇒ 纯冗余（PK 的 ART 索引已覆盖其前缀查找），
   是上面第 1 类的**隐患来源**。新版 ``ddl.sql`` 已不再创建它们。

用法（项目根目录）::

    python scripts/history/check_integrity.py            # 只读自检；有问题→退出码 1
    python scripts/history/check_integrity.py --fix      # 顺带删除冗余 date 索引（需写锁）
    python scripts/history/check_integrity.py --db <path>

修复后自检应「0 不一致、0 冗余索引」，退出码 0。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # 作为包导入
    from . import etl_common as ec
    from .init_db import LEGACY_REDUNDANT_INDEXES
except ImportError:  # 直接以脚本运行
    import etl_common as ec  # type: ignore[no-redef]
    from init_db import LEGACY_REDUNDANT_INDEXES  # type: ignore[no-redef]


def _drop_indexes(conn: Any, names: List[str], verbose: bool = True) -> List[str]:
    """删除给定索引（幂等）；返回实际删除者。索引名来自库内查询，非外部输入。"""
    dropped: List[str] = []
    for name in names:
        if conn.execute(
            "SELECT 1 FROM duckdb_indexes() WHERE index_name = ?", [name]
        ).fetchone():
            conn.execute(f"DROP INDEX IF EXISTS {name}")
            dropped.append(name)
    if dropped and verbose:
        print(f"[check_integrity] 已删除冗余索引：{dropped}")
    return dropped


def check_integrity(
    db_path: Optional[Path] = None,
    fix: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """执行完整性自检（可选顺带修复）。

    Args:
        db_path: 库文件路径；默认 ``ec.DB_PATH``。
        fix: 为 True 时先删除冗余 date 索引再检查（需要写连接）。

    Returns:
        ``{"db_path", "redundant_indexes", "dropped_indexes", "mismatches", "ok"}``。
    """
    ec.require_duckdb()
    target = Path(db_path) if db_path else ec.DB_PATH
    if not target.exists():
        raise SystemExit(f"[check_integrity] 历史库不存在：{target}")

    # --fix 需要写连接（DuckDB 单写者，勿与只读/ETL 并发）；否则只读打开即可
    conn = ec.connect(target) if fix else _connect_read_only(target)
    try:
        redundant_before = ec.redundant_date_indexes(conn)
        dropped: List[str] = []
        if fix and redundant_before:
            dropped = _drop_indexes(conn, redundant_before, verbose=verbose)

        # 若库内还残留已知的遗留冗余索引名，也一并纳入报告（即使未被 redundancy 规则命中）
        legacy_left = [
            n for n in LEGACY_REDUNDANT_INDEXES
            if conn.execute("SELECT 1 FROM duckdb_indexes() WHERE index_name = ?", [n]).fetchone()
        ]

        mismatches = ec.date_equality_mismatches(conn)
        redundant_after = ec.redundant_date_indexes(conn)
    finally:
        conn.close()

    ok = not mismatches and not redundant_after
    if verbose:
        print("=" * 68)
        print(f"[check_integrity] 库文件：{target}")
        print("-" * 68)
        if mismatches:
            print("❌ 等值查找 vs 全表扫 不一致（陈旧索引遮蔽 PK）：")
            for table, rows in mismatches.items():
                detail = "  ".join(f"{d}: eq={e} scan={s}" for d, e, s in rows)
                print(f"   {table:22s} {detail}")
        else:
            print("✅ 各表各日 `date = ?` 与全表扫一致（0 处不一致）")
        if redundant_after:
            print(f"❌ 仍存在冗余单列 date 索引：{redundant_after}")
        else:
            print("✅ 无冗余单列 date 索引")
        if legacy_left:
            print(f"⚠️ 残留已知遗留索引名（应被 --fix 清理）：{legacy_left}")
        print("-" * 68)
        print(f"[check_integrity] 结论：{'PASS ✓' if ok else 'FAIL ✗'}"
              + (f"（本次删除 {len(dropped)} 个）" if dropped else ""))
        print("=" * 68)

    return {
        "db_path": str(target),
        "redundant_indexes": redundant_before,
        "dropped_indexes": dropped,
        "mismatches": mismatches,
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
        description="历史库完整性自检：等值查找一致性 + 冗余 date 索引"
    )
    parser.add_argument("--db", default=str(ec.DB_PATH), help="库文件路径")
    parser.add_argument("--fix", action="store_true", help="删除冗余单列 date 索引（需写锁）")
    parser.add_argument("--quiet", action="store_true", help="减少输出")
    args = parser.parse_args(argv)

    result = check_integrity(db_path=Path(args.db), fix=args.fix, verbose=not args.quiet)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
