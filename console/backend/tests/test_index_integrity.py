"""索引完整性回归测试（P0-1 / P0-2 / ARCHITECTURE §12）。

真实缺陷：**5 个单列 ART 二级索引损坏**（索引项缺失/陈旧），优化器经其做**等值点查**时少算行
（``content_archive.source='bilibili'`` 得 286/真值 455；``category_membership.date='2026-06-27'``
得 0/真值 1241；``content_archive.coin_id='bitcoin'`` 得 322/真值 670 …）。**不是数据损坏**。

修复 = ``DROP INDEX`` + ``CREATE INDEX`` **重建**（不动数据、不碰 FTS）。

⚠️ 关键陷阱（§12 🔴 假绿警告）：**只查 ``date`` 的检测必漏报非 date 列**
（``content_archive.source`` / ``content_archive.coin_id`` / ``source_status.source``）。
本测试**显式断言检测覆盖非 date 列**，防止「改回只查 date」的回归。

另有**冗余单列 date 索引移除**（``idx_catmem_date`` / ``idx_srcstat_date`` / ``idx_snap_date``，
PK 首列即该列 ⇒ 冗余）：由 ``ddl.sql`` 不再创建 + ``init_db`` 幂等清理。
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


def _seed_content(conn) -> None:
    """插入 content_archive 行（含非 date 索引列 source / coin_id 的多取值）。"""
    rows = []
    for i in range(5):
        rows.append([f"c-bili-{i}", "2026-06-27", "bilibili-coin", "bilibili", f"h{i}"])
    for i in range(3):
        rows.append([f"c-btc-{i}", "2026-06-27", "bitcoin", "crypto_news", f"h{i}"])
    for i in range(2):
        rows.append([f"c-eth-{i}", "2026-06-28", "ethereum", "rss", f"h{i}"])
    conn.executemany(
        "INSERT INTO content_archive (content_id, date, coin_id, source, doc_hash) VALUES (?,?,?,?,?)",
        rows,
    )


def _seed_catmem(conn, date: str, n: int) -> None:
    conn.executemany(
        "INSERT INTO category_membership VALUES (?, ?, ?, ?, ?, ?, ?)",
        [[date, "defi", f"m{i}", None, False, None, None] for i in range(n)],
    )


# --------------------------------------------------------------------------
# 1) schema 层：不再产生冗余单列 date 索引（PK 首列即该列）
# --------------------------------------------------------------------------
def test_schema_creates_no_redundant_date_index(conn):
    assert ec.redundant_date_indexes(conn) == [], "新版 schema 不应再创建冗余单列 date 索引"


def test_legacy_index_names_absent_from_ddl_text():
    ddl = init_db.load_ddl()
    for name in init_db.LEGACY_REDUNDANT_INDEXES:
        assert f"{name} ON" not in ddl, f"ddl.sql 不应再定义冗余索引 {name}"


def test_redundant_detection_ignores_non_leading_pk_columns(conn):
    """PK 非首列的索引（如 coin_id）不是冗余 —— 不得误报。"""
    assert conn.execute(
        "SELECT 1 FROM duckdb_indexes() WHERE index_name = 'idx_snap_coin'"
    ).fetchone(), "DDL 应创建 idx_snap_coin"
    assert "idx_snap_coin" not in ec.redundant_date_indexes(conn)


# --------------------------------------------------------------------------
# 2) 迁移：init_db 幂等清理遗留冗余索引
# --------------------------------------------------------------------------
def test_drop_legacy_redundant_indexes_removes_and_idempotent(conn):
    conn.execute("CREATE INDEX idx_catmem_date ON category_membership(date)")
    assert "idx_catmem_date" in ec.redundant_date_indexes(conn)

    dropped = init_db.drop_legacy_redundant_indexes(conn, verbose=False)
    assert "idx_catmem_date" in dropped
    assert not conn.execute(
        "SELECT 1 FROM duckdb_indexes() WHERE index_name = 'idx_catmem_date'"
    ).fetchone()
    assert init_db.drop_legacy_redundant_indexes(conn, verbose=False) == []  # 幂等


# --------------------------------------------------------------------------
# 3) 检测覆盖「全部单列索引列」（防假绿：不得只查 date）
# --------------------------------------------------------------------------
def test_single_column_indexes_cover_non_date_columns(conn):
    cols = {(t, c) for _, t, c in ec.single_column_indexes(conn)}
    expected = {
        ("content_archive", "date"),
        ("content_archive", "coin_id"),
        ("content_archive", "source"),
        ("source_status", "source"),
        ("deep_research", "coin_id"),
        ("coin_daily_snapshot", "coin_id"),
    }
    for pair in expected:
        assert pair in cols, f"检测必须覆盖非 date 索引列 {pair}（否则假绿）"
    # 「不多不少」：健康 schema 恰好这 6 个；多出即说明冗余 date 索引回归
    # （idx_catmem_date / idx_srcstat_date / idx_snap_date 属设计清理对象，不应复活）。
    assert cols == expected, (
        f"单列索引集合应为恰好 6 个，实际 {len(cols)} 个；"
        f"多出={sorted(cols - expected)}，缺失={sorted(expected - cols)}"
    )


def test_index_equality_mismatches_clean_on_healthy_db(conn):
    _seed_content(conn)
    _seed_catmem(conn, "2026-06-27", 10)
    conn.executemany(
        "INSERT INTO source_status VALUES (?, ?, ?, ?, ?, ?, ?)",
        [["2026-06-30", f"c{i}", "market", "ok", None, None, None] for i in range(7)],
    )
    assert ec.index_equality_mismatches(conn) == {}


def test_index_equality_mismatches_detects_non_date_column(conn, monkeypatch):
    """伪造「真值 > 等值计数」⇒ 检测必须报出**非 date** 索引 ``idx_content_source``。"""
    _seed_content(conn)
    real_truth = ec.materialized_truth_counts

    def fake_truth(c, table, column):
        data = real_truth(c, table, column)
        if (table, column) == ("content_archive", "source"):
            return {k: v + 999 for k, v in data.items()}  # 模拟索引少算
        return data

    monkeypatch.setattr(ec, "materialized_truth_counts", fake_truth)
    mismatches = ec.index_equality_mismatches(conn)
    assert "idx_content_source" in mismatches, "必须检出非 date 列的索引损坏（防假绿）"


# --------------------------------------------------------------------------
# 4) 修复 = 重建（DROP+CREATE），不动数据、索引集合不丢
# --------------------------------------------------------------------------
def test_rebuild_index_recreates_and_keeps_data(conn):
    _seed_content(conn)
    before = conn.execute("SELECT COUNT(*) FROM content_archive").fetchone()[0]
    ec.rebuild_index(conn, "idx_content_source", "content_archive", "source")
    assert conn.execute(
        "SELECT 1 FROM duckdb_indexes() WHERE index_name = 'idx_content_source'"
    ).fetchone(), "重建后索引应仍存在"
    assert conn.execute("SELECT COUNT(*) FROM content_archive").fetchone()[0] == before


def test_rebuild_damaged_indexes_plumbing(conn, monkeypatch):
    """伪造一次「idx_content_source 损坏」→ rebuild_damaged_indexes 应重建它且索引集合不变。"""
    _seed_content(conn)
    calls = {"n": 0}

    def fake_mismatches(_conn):
        calls["n"] += 1
        if calls["n"] == 1:  # 首次检测：报出损坏
            return {"idx_content_source": [("bilibili", 286, 455)]}
        return {}  # 重建后复检：干净

    monkeypatch.setattr(ec, "index_equality_mismatches", fake_mismatches)
    report = ec.rebuild_damaged_indexes(conn)
    assert report["rebuilt"] == ["idx_content_source"]
    assert report["index_lost"] is False
    assert report["mismatches_after"] == {}
    assert conn.execute(
        "SELECT 1 FROM duckdb_indexes() WHERE index_name = 'idx_content_source'"
    ).fetchone()


# --------------------------------------------------------------------------
# 5) CLI：健康库 check_integrity(fix=True) 直接 PASS
# --------------------------------------------------------------------------
def test_check_integrity_pass_on_healthy(tmp_path: Path):
    from scripts.history import check_integrity as ci

    db_path = tmp_path / "ci.duckdb"
    c = ec.connect(db_path)
    apply_schema(c, verbose=False)
    _seed_content(c)
    c.close()

    result = ci.check_integrity(db_path=db_path, fix=True, verbose=False)
    assert result["ok"] is True
    assert result["created"] == []
    assert result["rebuilt"] == []
    assert result["index_lost"] is False
    assert result["mismatches_after"] == {}
    assert result["missing_indexes"] == []
    assert len(result["expected_indexes"]) == 6


# --------------------------------------------------------------------------
# 6) 预期索引集合存在性断言（防「意外丢索引」，独立于重建流程）
# --------------------------------------------------------------------------
def test_expected_indexes_parsed_from_ddl_matches_schema(conn):
    """``expected_indexes()`` 从 ddl.sql 解析出的口径必须与库里实际建出的索引一致。"""
    expected = ec.expected_indexes()
    assert len(expected) == 6, f"ddl.sql 应声明 6 个单列索引，实际 {len(expected)}：{expected}"
    schema = {(t, c) for _, t, c in ec.single_column_indexes(conn)}
    assert set(expected.values()) == schema, (
        f"DDL 预期 {sorted(expected.values())} 与库内 {sorted(schema)} 不一致"
    )


def test_expected_indexes_ignores_commented_out_statements():
    """``--`` 注释里的 ``CREATE INDEX`` 不得被当成预期索引（锚定行首 → 天然跳过）。"""
    ddl = (
        "CREATE INDEX IF NOT EXISTS idx_content_date ON content_archive(date);\n"
        "-- 原 idx_catmem_date 已移除：\n"
        "-- CREATE INDEX idx_catmem_date ON category_membership(date);\n"
        "  CREATE INDEX idx_srcstat_source ON source_status(source);\n"
    )
    got = ec.expected_indexes(ddl)
    assert set(got) == {"idx_content_date", "idx_srcstat_source"}, got
    assert "idx_catmem_date" not in got, "注释里的 CREATE INDEX 不应被解析为预期索引"


def test_audit_expected_indexes_clean_on_healthy(conn):
    audit = ec.audit_expected_indexes(conn)
    assert audit["missing"] == [], f"健康库不应缺预期索引：{audit}"
    assert audit["expected"] == audit["present"]


def test_audit_expected_indexes_detects_missing(conn):
    """DROP 掉一个预期索引（非重建路径）→ 必须被存在性断言抓住。"""
    conn.execute("DROP INDEX IF EXISTS idx_content_source")
    audit = ec.audit_expected_indexes(conn)
    assert audit["missing"] == ["idx_content_source"], audit


def test_check_integrity_fails_when_expected_index_missing(tmp_path: Path):
    from scripts.history import check_integrity as ci

    db_path = tmp_path / "ci_missing.duckdb"
    c = ec.connect(db_path)
    apply_schema(c, verbose=False)
    _seed_content(c)
    c.execute("DROP INDEX IF EXISTS idx_content_source")  # 模拟意外丢索引
    c.close()

    result = ci.check_integrity(db_path=db_path, fix=False, verbose=False)
    assert result["ok"] is False, "缺预期索引时自检必须 FAIL（否则是假绿）"
    assert result["missing_indexes"] == ["idx_content_source"]


# --------------------------------------------------------------------------
# 7) 自愈：--fix / ETL 收尾**按 ddl.sql 补齐缺失** + 重建「存在但算错」
# --------------------------------------------------------------------------
def test_ensure_expected_indexes_recreates_missing(conn):
    conn.execute("DROP INDEX IF EXISTS idx_content_source")
    created = ec.ensure_expected_indexes(conn)
    assert created == ["idx_content_source"], created
    assert ("content_archive", "source") in {(t, c) for _, t, c in ec.single_column_indexes(conn)}
    assert ec.audit_expected_indexes(conn)["missing"] == []
    assert ec.ensure_expected_indexes(conn) == []  # 幂等：已存在则不动作


def test_heal_indexes_creates_missing_and_reports_ok(conn):
    conn.execute("DROP INDEX IF EXISTS idx_srcstat_source")
    heal = ec.heal_indexes(conn)
    assert heal["created"] == ["idx_srcstat_source"], heal
    assert heal["missing_after"] == []
    assert heal["missing_before"] == ["idx_srcstat_source"]
    assert heal["ok"] is True


def test_check_integrity_fix_recreates_missing(tmp_path: Path):
    from scripts.history import check_integrity as ci

    db_path = tmp_path / "ci_fix.duckdb"
    c = ec.connect(db_path)
    apply_schema(c, verbose=False)
    _seed_content(c)
    c.execute("DROP INDEX IF EXISTS idx_content_source")
    c.close()

    result = ci.check_integrity(db_path=db_path, fix=True, verbose=False)
    assert result["ok"] is True, result
    assert result["created"] == ["idx_content_source"]
    assert result["missing_indexes"] == []


def test_heal_indexes_drops_redundant_but_keeps_unknown(conn):
    """unexpected 拆分：冗余 date 索引 → 清理；未知多余索引 → 仅告警、不自动删。"""
    conn.execute("CREATE INDEX idx_catmem_date ON category_membership(date)")  # 冗余（PK 首列=date）
    conn.execute("CREATE INDEX idx_unknown_coin ON macro_watchlist(coin_id)")  # 非冗余 → 未知

    heal = ec.heal_indexes(conn)
    assert "idx_catmem_date" in heal["dropped_redundant"], heal
    assert not conn.execute(
        "SELECT 1 FROM duckdb_indexes() WHERE index_name = 'idx_catmem_date'"
    ).fetchone(), "冗余 date 索引应被清理"
    assert conn.execute(
        "SELECT 1 FROM duckdb_indexes() WHERE index_name = 'idx_unknown_coin'"
    ).fetchone(), "未知多余索引**不得**被自动删除"
    assert "idx_unknown_coin" in heal["unknown_unexpected"], heal


def test_check_integrity_fix_snapshot_reflects_post_heal(tmp_path: Path):
    """`--fix` 的「现存/多出/未知」快照必须是**自愈后**的：不得残留刚删的冗余、
    也不得漏掉刚补齐的缺失索引（回归 team-lead 报的报告缺陷）。"""
    from scripts.history import check_integrity as ci

    db_path = tmp_path / "ci_snap.duckdb"
    c = ec.connect(db_path)
    apply_schema(c, verbose=False)
    _seed_content(c)
    c.execute("DROP INDEX IF EXISTS idx_content_source")                       # 缺失
    c.execute("CREATE INDEX idx_catmem_date ON category_membership(date)")      # 冗余（应被清）
    c.execute("CREATE INDEX idx_unknown_coin ON macro_watchlist(coin_id)")      # 未知（应保留）
    c.close()

    result = ci.check_integrity(db_path=db_path, fix=True, verbose=False)
    cols = {n for n, _, _ in result["indexed_columns"]}
    assert result["ok"] is True, result
    assert "idx_content_source" in cols, "补齐的索引必须出现在「现存」快照里"
    assert "idx_catmem_date" not in cols, "已清理的冗余索引不得残留在「现存」快照里"
    assert result["redundant_indexes"] == [], "自愈后不应再有冗余索引"
    assert result["unknown_unexpected_indexes"] == ["idx_unknown_coin"]
    assert "idx_catmem_date" not in result["unknown_unexpected_indexes"]
    assert result["missing_indexes"] == []
