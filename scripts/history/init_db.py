"""初始化历史库：执行 DDL、确保 FTS 扩展加载、打印各表行数。

用法（在项目根目录执行）::

    python scripts/history/init_db.py            # 建库建表（幂等）+ 建/重建双列 FTS
    python scripts/history/init_db.py --rebuild  # 先删除库文件再重建（清空历史数据）

验收（ARCHITECTURE §11-T01）：生成 ``data/history/ct_history.duckdb``，
14 张基表 + 5 个业务视图 + **双列 FTS 索引**（``body_text`` + ``body_grams``）就绪。

实现要点：
- ``ddl.sql`` 为 ``ARCHITECTURE.md §2`` 的逐字落盘；
- **建表语句与 FTS 语句必须分开执行**（§2 尾注）——本模块把 DDL 拆成单条语句
  逐条 ``execute``，天然把 ``create_fts_index`` 放到独立批次，规避
  `Table with name content_archive does not exist` 的绑定期报错；
- FTS 索引为**静态索引**：建索引后新插入的行检索不到，故 ETL 顺序固定为
  「先写完所有数据行 → 最后建/重建 FTS」（见 ``backfill_history.py``）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # 作为包导入（scripts.history.init_db）
    from . import etl_common as ec
except ImportError:  # 直接以脚本运行（python scripts/history/init_db.py）
    import etl_common as ec  # type: ignore[no-redef]

# 5 个业务视图（验收口径，缺失任一即视为不通过）
BUSINESS_VIEWS: tuple = (
    "v_collection_calendar",
    "v_collection_freshness",
    "v_latest_complete_date",
    "v_source_drift",
    "v_source_health_daily",
)


# --------------------------------------------------------------------------
# SQL 文本处理：把整段 DDL 拆成「单条语句」，逐条执行
# --------------------------------------------------------------------------
def _strip_line_comments(sql_text: str) -> str:
    """去掉 ``--`` 行注释（本 DDL 的字符串字面量中不含 ``--``，故可安全按行处理）。"""
    cleaned: List[str] = []
    for line in sql_text.splitlines():
        idx = line.find("--")
        cleaned.append(line[:idx] if idx >= 0 else line)
    return "\n".join(cleaned)


def split_sql_statements(sql_text: str) -> List[str]:
    """把多语句 SQL 文本拆成单条语句列表（去空、去注释）。

    逐条执行而非整段执行，是为了满足「建表批次与 FTS 批次分开」的硬约束。
    """
    without_comments = _strip_line_comments(sql_text)
    statements = [chunk.strip() for chunk in without_comments.split(";")]
    return [stmt for stmt in statements if stmt]


def load_ddl(ddl_path: Optional[Path] = None) -> str:
    """读取 DDL 文本（默认 ``scripts/history/ddl.sql``）。"""
    path = Path(ddl_path) if ddl_path else ec.DDL_PATH
    return path.read_text(encoding="utf-8")


def apply_schema(conn: "Any", ddl_path: Optional[Path] = None, verbose: bool = True) -> List[str]:
    """执行 DDL 中的全部语句（CREATE TABLE IF NOT EXISTS / VIEW / FTS）。

    逐条 ``execute``：FTS 的 ``INSTALL/LOAD/create_fts_index`` 天然落在建表之后，
    规避 DuckDB 绑定期「表不存在」的报错。

    Returns:
        实际执行的语句列表（便于单测/排查）。
    """
    statements = split_sql_statements(load_ddl(ddl_path))
    for stmt in statements:
        conn.execute(stmt)
    if verbose:
        print(f"[init_db] 已执行 DDL 语句 {len(statements)} 条（含 FTS 建索引）")
    return statements


# --------------------------------------------------------------------------
# FTS 索引状态与重建
# --------------------------------------------------------------------------
def fts_index_ready(conn: "Any") -> bool:
    """FTS 索引是否已建立（检查 DuckDB 自动创建的 ``fts_main_content_archive`` schema）。"""
    try:
        rows = conn.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = 'fts_main_content_archive'"
        ).fetchall()
        return bool(rows)
    except Exception as exc:  # noqa: BLE001
        print(f"[init_db] 检查 FTS schema 失败：{exc}")
        return False


def build_fts_index(conn: "Any", verbose: bool = True) -> bool:
    """建/重建 ``content_archive`` 的**双列单索引**（``body_text`` + ``body_grams``）。

    ⚠️ 严禁只索引 ``body_grams``（会把英文切碎 → ``Solana``/``Uniswap`` 等英文关键词全失效）。
    索引为静态：任何 INSERT/DELETE 之后都必须以 ``overwrite=1`` 重建才可见。
    """
    if not ec.ensure_fts_extension(conn):
        return False
    conn.execute(
        "PRAGMA create_fts_index('content_archive', 'content_id', 'body_text', 'body_grams', "
        "stemmer='none', lower=1, strip_accents=0, overwrite=1)"
    )
    if verbose:
        print("[init_db] 已重建双列 FTS 索引 content_archive(content_id: body_text, body_grams)")
    return True


# --------------------------------------------------------------------------
# 统计
# --------------------------------------------------------------------------
def _main_objects(conn: "Any", object_type: str) -> List[str]:
    rows = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_type = ? ORDER BY table_name",
        [object_type],
    ).fetchall()
    return [r[0] for r in rows]


def get_stats(conn: Optional["Any"] = None, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """收集库级统计：基表清单与行数、视图清单、FTS 状态、库体积。

    与 ``src/research/database.py::get_stats`` 同风格，但返回更细的结构供 CLI 打印。
    """
    owns_conn = conn is None
    conn = conn or ec.connect(db_path)
    try:
        base_tables = _main_objects(conn, "BASE TABLE")
        views = _main_objects(conn, "VIEW")
        table_counts: Dict[str, int] = {}
        for name in base_tables:
            table_counts[name] = int(conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0])
        fts_ready = fts_index_ready(conn)
        resolved = Path(db_path) if db_path else ec.DB_PATH
        size_bytes = resolved.stat().st_size if resolved.exists() else 0
        return {
            "db_path": str(resolved),
            "db_size_bytes": size_bytes,
            "base_tables": base_tables,
            "table_counts": table_counts,
            "views": views,
            "missing_business_views": [v for v in BUSINESS_VIEWS if v not in views],
            "fts_index_ready": fts_ready,
            "total_rows": sum(table_counts.values()),
        }
    finally:
        if owns_conn:
            conn.close()


def print_report(stats: Dict[str, Any]) -> None:
    """把 ``get_stats`` 结果打印成人类可读的验收报告。"""
    size_mb = stats["db_size_bytes"] / (1024 * 1024)
    print("=" * 68)
    print("claude_trading 历史数据库 —— 状态报告")
    print("=" * 68)
    print(f"库文件: {stats['db_path']}  ({size_mb:.2f} MB)")
    print(f"基表: {len(stats['base_tables'])} 张 | 视图: {len(stats['views'])} 个 | "
          f"总行数: {stats['total_rows']}")
    print("-" * 68)
    print("[基表行数]")
    for name in stats["base_tables"]:
        print(f"  {name:<24} {stats['table_counts'][name]:>10,}")
    print("-" * 68)
    print("[视图]")
    for name in stats["views"]:
        mark = "✓" if name in BUSINESS_VIEWS else "·"
        print(f"  {mark} {name}")
    print("-" * 68)
    fts_ok = "就绪 ✓" if stats["fts_index_ready"] else "缺失 ✗"
    print(f"双列 FTS 索引 content_archive(body_text, body_grams): {fts_ok}")
    if stats["missing_business_views"]:
        print(f"⚠️ 缺失业务视图: {stats['missing_business_views']}")
    else:
        print("5 个业务视图齐备 ✓")
    print("=" * 68)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _remove_db_files(db_path: Path) -> None:
    """删除库文件及其 WAL（``--rebuild`` 用）。"""
    for suffix in ("", ".wal"):
        target = Path(str(db_path) + suffix)
        if target.exists():
            target.unlink()
            print(f"[init_db] 已删除 {target}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="初始化 claude_trading 历史数据库（DuckDB）")
    parser.add_argument("--rebuild", action="store_true", help="先删除库文件再重建（清空历史数据）")
    parser.add_argument("--db", default=str(ec.DB_PATH), help="库文件路径（默认 data/history/ct_history.duckdb）")
    args = parser.parse_args(argv)

    ec.require_duckdb()
    db_path = Path(args.db)

    if args.rebuild:
        _remove_db_files(db_path)

    conn = ec.connect(db_path)
    try:
        apply_schema(conn)
        build_fts_index(conn)
        stats = get_stats(conn, db_path)
    finally:
        conn.close()

    print_report(stats)
    ok = not stats["missing_business_views"] and len(stats["base_tables"]) >= 14
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
