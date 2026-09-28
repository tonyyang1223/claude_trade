"""索引完整性回归测试（P0-1 / P0-2）。

真实缺陷：三张表存在「PK 首列即 date」的**冗余**单列 date 索引（``idx_catmem_date`` /
``idx_srcstat_date`` / ``idx_snap_date``）。这些表按「自然键单元 DELETE + INSERT」重写后，
冗余二级索引会**陈旧**，且被优化器选中做**等值查找** → 返回错误行数
（category_membership 2026-06-27 等值查 0 / 真值 1241；source_status 2026-06-30 查 618 / 真值 871），
而 PK 索引本身是正确的（被冗余索引「遮蔽」）。应用层因此静默回退文件。

修复：
1. ``ddl.sql`` 不再创建这三个冗余索引；
2. ``init_db.apply_schema`` 幂等 ``DROP INDEX IF EXISTS`` 清理旧库残留；
3. ``etl_common`` 提供 ``redundant_date_indexes`` / ``date_equality_mismatches`` 自检，
   并接入 ingest/backfill 的收尾校验 + ``scripts/history/check_integrity.py`` CLI。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core import paths  # noqa: F401  确保项目根入 sys.path（scripts 属于命名空间包）
from scripts.history import etl_common as ec
from scripts.history import init_db
from scripts.history.init_db import apply_schema


@pytest.fixture
def conn(tmp_path: Path):
    """独立临时库 + 完整 schema（不触碰真实历史库）。"""
    c = ec.connect(tmp_path / "integrity.duckdb")
    apply_schema(c, verbose=False)
    try:
        yield c
    finally:
        c.close()


def _seed_catmem(conn, date: str, n: int) -> None:
    conn.executemany(
        "INSERT INTO category_membership VALUES (?, ?, ?, ?, ?, ?, ?)",
        [[date, "defi", f"m{i}", None, False, None, None] for i in range(n)],
    )


# --------------------------------------------------------------------------
# 1) schema 层：新版 DDL 不再产生冗余单列 date 索引
# --------------------------------------------------------------------------
def test_schema_creates_no_redundant_date_index(conn):
    assert ec.redundant_date_indexes(conn) == [], "新版 schema 不应再创建冗余单列 date 索引"


def test_legacy_index_names_absent_from_ddl_text():
    ddl = init_db.load_ddl()
    for name in init_db.LEGACY_REDUNDANT_INDEXES:
        assert f"{name} ON" not in ddl, f"ddl.sql 不应再定义冗余索引 {name}"


def test_redundant_detection_ignores_non_leading_pk_columns(conn):
    """PK 非首列的索引（如 coin_id）不是冗余 —— 不得误报。

    ``idx_snap_coin``（coin_daily_snapshot.coin_id，PK 次列）已由 DDL 创建，应保留且不被判为冗余。
    """
    assert conn.execute(
        "SELECT 1 FROM duckdb_indexes() WHERE index_name = 'idx_snap_coin'"
    ).fetchone(), "DDL 应创建 idx_snap_coin"
    assert "idx_snap_coin" not in ec.redundant_date_indexes(conn)


# --------------------------------------------------------------------------
# 2) 迁移：apply_schema / drop_legacy 清理遗留冗余索引（幂等）
# --------------------------------------------------------------------------
def test_apply_schema_drops_legacy_redundant_index(conn):
    conn.execute("CREATE INDEX idx_catmem_date ON category_membership(date)")
    assert "idx_catmem_date" in ec.redundant_date_indexes(conn)

    dropped = init_db.drop_legacy_redundant_indexes(conn, verbose=False)
    assert "idx_catmem_date" in dropped
    assert not conn.execute(
        "SELECT 1 FROM duckdb_indexes() WHERE index_name = 'idx_catmem_date'"
    ).fetchone()
    # 幂等：再次调用无事发生
    assert init_db.drop_legacy_redundant_indexes(conn, verbose=False) == []


# --------------------------------------------------------------------------
# 3) 自检函数：健康库无「等值 vs 全表扫」不一致（无假阳性）
# --------------------------------------------------------------------------
def test_date_equality_mismatches_clean_on_healthy_db(conn):
    _seed_catmem(conn, "2026-06-27", 10)
    _seed_catmem(conn, "2026-06-28", 5)
    conn.executemany(
        "INSERT INTO source_status VALUES (?, ?, ?, ?, ?, ?, ?)",
        [["2026-06-30", f"c{i}", "market", "ok", None, None, None] for i in range(7)],
    )
    assert ec.date_equality_mismatches(conn) == {}


# --------------------------------------------------------------------------
# 4) CLI/入口：check_integrity(fix=True) 一步到位修复并报 PASS
# --------------------------------------------------------------------------
def test_check_integrity_fix_detects_and_removes(tmp_path: Path):
    from scripts.history import check_integrity as ci

    db_path = tmp_path / "ci.duckdb"
    c = ec.connect(db_path)
    apply_schema(c, verbose=False)
    _seed_catmem(c, "2026-06-27", 4)
    c.execute("CREATE INDEX idx_catmem_date ON category_membership(date)")
    c.close()

    result = ci.check_integrity(db_path=db_path, fix=True, verbose=False)
    assert result["ok"] is True
    assert "idx_catmem_date" in result["redundant_indexes"]
    assert "idx_catmem_date" in result["dropped_indexes"]
    assert result["mismatches"] == {}

    # 再查一次：既无冗余索引也无不一致
    again = ci.check_integrity(db_path=db_path, fix=False, verbose=False)
    assert again["ok"] is True
    assert again["dropped_indexes"] == []
