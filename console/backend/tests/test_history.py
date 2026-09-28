"""H5 全文检索 + 历史端点（H1/H7）单元测试。

- ``build_fts_query`` 是纯函数，断言其**确切输出字符串**（§8.1 映射表）；
- H5/H1/H7 依赖真实历史库（与 ``test_loader`` 依赖真实 daily_scan 同风格），
  库不可用时 skip；H5 断言真实 ``total``（含 FTS 0 命中走 ILIKE 兜底的路径）。
"""
from __future__ import annotations

from datetime import date

import pytest

from data.repository import history_db_available
from services import history_svc


@pytest.fixture(scope="module")
def db() -> bool:
    """历史库可用性守卫：不可用则 skip（避免 CI 无库时误报失败）。"""
    if not history_db_available():
        pytest.skip("历史库不可用（data/history/ct_history.duckdb）")
    return True


# --------------------------------------------------------------------------
# build_fts_query —— 纯函数，§8.1 映射表逐条断言
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("哔哩哔哩 ETF", "哔哩 哩哔 etf"),
        ("哔哩哔哩", "哔哩 哩哔"),
        ("Solana 生态", "solana 生态"),
        ("Solana", "solana"),
        ("以太坊", "以太 太坊"),
        ("治理", "治理"),
        ("a", "a"),
    ],
)
def test_build_fts_query_cases(raw: str, expected: str) -> None:
    assert history_svc.build_fts_query(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
def test_build_fts_query_empty_returns_none(raw: str) -> None:
    assert history_svc.build_fts_query(raw) is None


def test_build_fts_query_dedup_preserves_order() -> None:
    # '哔哩哔哩' → ['哔哩','哩哔','哔哩'] → 去重后 ['哔哩','哩哔']（保留首次出现）
    assert history_svc.build_fts_query("哔哩哔哩") == "哔哩 哩哔"
    # 跨段去重：两段产生相同 token 时只保留一次
    assert history_svc.build_fts_query("治理 治理") == "治理"


def test_build_fts_query_single_cjk_char_kept() -> None:
    assert history_svc.build_fts_query("坊") == "坊"
    assert history_svc.build_fts_query("ETF") == "etf"


# --------------------------------------------------------------------------
# H5 真实召回量（§8.1 映射表）
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "q, expected_total",
    [
        ("哔哩哔哩 ETF", 1122),   # FTS(OR)：455 + 667
        ("哔哩哔哩", 455),        # CJK 必须 bigram 化才命中
        ("Solana 生态", 869),     # 仅 solana 命中
        ("Solana", 869),
        ("以太坊", 0),            # FTS 0 → ILIKE 兜底，语料亦无 → 0
        ("治理", 0),              # FTS 0 → ILIKE 兜底，语料亦无 → 0
        ("a", 37794),             # FTS 0 → ILIKE 兜底（命中面广）
    ],
)
def test_h5_search_totals(db: bool, q: str, expected_total: int) -> None:
    resp = history_svc.search(q)
    assert resp.query == q.strip()
    assert resp.total == expected_total, f"{q!r}: total={resp.total} != {expected_total}"


def test_h5_empty_query_returns_empty(db: bool) -> None:
    resp = history_svc.search("   ")
    assert resp.hits == [] and resp.total == 0 and resp.took_ms >= 0.0


def test_h5_ilike_fallback_path_marker(db: bool) -> None:
    """'a' 走 ILIKE 兜底：命中项的 score 为 NULL（FTS 路径才有 bm25 分数）。"""
    resp = history_svc.search("a", limit=5)
    assert resp.total > 0 and resp.hits
    assert all(h.score is None for h in resp.hits)


def test_h5_hits_shape_and_no_body_grams(db: bool) -> None:
    """命中项字段完整；绝不泄露 body_grams。"""
    resp = history_svc.search("Solana", limit=3)
    assert resp.hits
    hit = resp.hits[0]
    dumped = hit.model_dump()
    assert set(dumped.keys()) == {
        "content_id", "date", "coin_id", "source", "title", "snippet", "url", "origin_path", "score"
    }
    assert "body_grams" not in dumped and isinstance(hit.snippet, str)


def test_h5_source_filter(db: bool) -> None:
    """来源过滤生效：哔哩哔哩 bigram 命中全部来自 bilibili 源。"""
    resp = history_svc.search("哔哩哔哩", source="bilibili", limit=5)
    assert resp.total == 455
    assert all(h.source == "bilibili" for h in resp.hits)


# --------------------------------------------------------------------------
# H1 最新 / 最新完整日
# --------------------------------------------------------------------------
def test_h1_latest_and_latest_complete(db: bool) -> None:
    resp = history_svc.list_dates()
    assert resp.latest == "2026-08-26"           # 最新扫描日（含 08-26 残缺日）
    assert resp.latest_complete == "2026-08-25"  # 最新完整日（前端自救开关）
    assert resp.latest_macro == "2026-09-27"
    row = next(d for d in resp.dates if d.date == "2026-08-26")
    assert row.is_partial is True


# --------------------------------------------------------------------------
# H7 gap_days —— 参照日可注入（固定日期断言，避免随时间漂移）
# --------------------------------------------------------------------------
def test_h7_gap_days_injectable_today(db: bool) -> None:
    resp = history_svc.health_overview(today=date(2026, 9, 28))
    assert resp.collections["scan"].last_date == "2026-08-26"
    assert resp.collections["scan"].gap_days == 33
    assert resp.collections["scan"].status == "stale"
    assert resp.collections["macro"].last_date == "2026-09-27"
    assert resp.collections["macro"].gap_days == 1
    assert resp.collections["macro"].status == "ok"


def test_h7_gap_days_ok_when_fresh(db: bool) -> None:
    resp = history_svc.health_overview(today=date(2026, 8, 26))
    assert resp.collections["scan"].gap_days == 0
    assert resp.collections["scan"].status == "ok"
