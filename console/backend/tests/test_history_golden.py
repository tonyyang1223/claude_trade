"""H3 板块时间线 golden 对齐测试（P1-A 回归护栏）。

## 为什么要这个测试

``avg_chg`` 曾用 ``AVG(chg24)``——它**跳过 NULL**、把分母变小；而 ``build_sectors``
（files 模式，即 ``golden-sectors.json`` 的出处）是**把缺失 ``chg24`` 的成员按 0 计入分母**。
实测偏差：``rwa`` 0.7991 vs golden 0.5994、``unclassified`` -0.9559 vs -0.9269
（数据日 2026-06-27，两者各缺 1 个成员）。改为 ``AVG(COALESCE(chg24, 0))`` 后 9 日逐值零差异。

## 两个容易混淆的维度（本测试只覆盖前者）

1. **``avg_chg`` 口径**（本测试的靶心）：缺失涨跌是否计入分母 → **H3 必须与 golden 一致**。
2. **日期解析**：``build_sectors`` / 仓储层会在 ``[请求日-7, 请求日]`` 内取**成员数最多**的一天
   （并列取较晚）——故 golden 的 ``2026-06-27``~``2026-07-03`` 七个请求日**重复同一份快照**
   （都解析到 2026-06-27），``2026-08-26`` 解析到 2026-08-25。
   **而 H3 是按请求日直查、不做跨日解析**（请求 06-28 即返回 06-28 的行）——
   这是 H3 作为「时间线」的**正确设计**，不是缺陷。

故本测试按**解析后的数据日**对齐：``H3(数据日 R)`` ↔ ``golden[解析到 R 的请求日]``。
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

import pytest

from data.repository import history_db_available
from services import history_svc

GOLDEN_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "history-db" / "golden-sectors.json"
)


@pytest.fixture(scope="module")
def golden() -> dict:
    if not history_db_available():
        pytest.skip("历史库不可用（data/history/ct_history.duckdb）")
    if not GOLDEN_PATH.exists():
        pytest.skip("golden-sectors.json 不存在：%s" % GOLDEN_PATH)
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def db(golden: dict) -> bool:
    return True


def _resolve_data_day(conn, requested: date) -> Optional[date]:
    """独立复刻仓储层跨日解析：[requested-7, requested] 内成员数最多的日；并列取较晚。

    刻意不复用生产代码——否则生产逻辑一起错时测试会跟着一起绿。
    """
    days: List[date] = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT date FROM category_membership WHERE date IS NOT NULL ORDER BY 1"
        ).fetchall()
    ]
    lo = requested - timedelta(days=7)
    best: Optional[date] = None
    best_n = -1
    for d in days:
        if not (lo <= d <= requested):
            continue
        n = conn.execute(
            "SELECT count(*) FROM category_membership WHERE date = ?", [d]
        ).fetchone()[0]
        if n >= best_n:  # >= 使并列取较晚者
            best, best_n = d, n
    return best


def test_h3_golden_sectors_parity(golden: dict) -> None:
    """H3 的 count / mcap / avg_chg 必须与 golden 逐值一致（含「缺失按 0」口径）。"""
    from data.duck import read_conn

    conn = read_conn()
    by_data_day: dict = {}
    checked = 0

    for requested, expected_sectors in sorted(golden["sectors_by_requested_date"].items()):
        resolved = _resolve_data_day(conn, date.fromisoformat(requested))
        assert resolved is not None, "无法解析请求日 %s 的数据日" % requested
        key = resolved.isoformat()

        if key not in by_data_day:
            resp = history_svc.categories_timeline(from_=key, to=key)
            by_data_day[key] = {
                p.category: {"count": p.coin_count, "mcap": p.total_mcap, "avg": p.avg_chg}
                for p in resp.series
                if p.date == key
            }
        got = by_data_day[key]
        assert got, "H3 在数据日 %s 未返回任何板块（请求日 %s）" % (key, requested)

        for item in expected_sectors:
            cat = item["cat"]
            assert cat in got, (
                "数据日 %s（请求日 %s）缺少板块 %s" % (key, requested, cat)
            )
            g = got[cat]
            assert g["count"] == item["count"], (
                "%s/%s count: got %s, golden %s" % (key, cat, g["count"], item["count"])
            )
            assert g["mcap"] is not None and abs(g["mcap"] - item["mcap"]) <= 1, (
                "%s/%s mcap: got %s, golden %s" % (key, cat, g["mcap"], item["mcap"])
            )
            assert g["avg"] is not None and abs(g["avg"] - item["avgChg"]) <= 1e-3, (
                "%s/%s avg_chg: got %s, golden %s —— 若实现退回 AVG(chg24)（跳过 NULL）"
                "而非 AVG(COALESCE(chg24,0))，此处必红" % (key, cat, g["avg"], item["avgChg"])
            )
            checked += 1

    assert checked == 81, "应比对 9 请求日 × 9 板块 = 81 项，实际 %d" % checked


def test_h3_unknown_category_returns_empty(db: bool) -> None:
    """未知 slug 不得静默返回全量（P1-B 回归护栏）。"""
    resp = history_svc.categories_timeline(
        from_="2026-06-27", to="2026-06-27", category="__nope__"
    )
    assert resp.series == []


def test_h3_known_category_filters(db: bool) -> None:
    """已知 slug 只返回该 slug（对照组，确保上面那条不是「恒为空」）。"""
    resp = history_svc.categories_timeline(
        from_="2026-06-27", to="2026-06-27", category="defi"
    )
    assert resp.series, "defi 应有数据"
    assert {p.category for p in resp.series} == {"defi"}
