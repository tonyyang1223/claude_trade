"""文件仓储 ↔ DuckDB 仓储**同构性**测试（R8 核心）—— 见 ARCHITECTURE.md §7。

目标：证明 ``FileRepository`` 与 ``DuckDBRepository`` 对同一输入产出**结构等价**的 Python 对象，
从而让上层 ``services/*`` 对数据源无感（这正是不变量 R8「双读零差异」的底座）。

设计要点
--------
- **不使用 ``fastapi.testclient``**：本机 starlette 需要未安装的 ``httpx2``，故直连仓储层比对；
- 真实数据：与 ``test_loader`` 同风格，依赖真实 ``data/reports/daily_scan`` 与
  ``data/history/ct_history.duckdb``；任一不可用则 ``skip``（避免 CI 误报）；
- 等价口径按「**消费者实际读取的语义**」定义（而非源字典逐字节）：
  - ``load_deep_raw``：整条 ``payload_json`` 回放 → 全等（实测 0 差异）；
  - ``load_all_coins``：Python ``==`` 全等（仅 int/float 的 JSON 字面量表示有别，数值相等）；
  - ``load_summary``：DuckDB 仅重建已入库列，源里 ``highlights`` / ``elapsed_seconds`` 等
    **未入库字段**不参与比对（无任何端点消费，见 ``DuckDBRepository.load_summary`` docstring）；
  - ``load_by_category_raw``：源字典 vs DB 重建字典形状不同（DB 仅回放 ``coin_id`` +
    ``sources.market.data``），故比对**下游消费投影**：slug 集合、成员数、
    以及每个成员的 ``(coin_id, has_market, market_cap, chg24)`` 多重集。
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional
import json

import pytest

from core.config import HISTORY_DB_PATH
from data import duck
from data.repository import DuckDBRepository, FileRepository

# 源 ``summary.json`` 中「已入库、可被 DuckDB 重建」的字段（其余为源独有，不参与比对）
SUMMARY_REPRODUCIBLE_KEYS = (
    "scan_time", "total_coins", "deep_researched", "light_researched",
    "categories", "market_stats", "state_stats",
)


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def repos():
    """返回 ``(file_repo, duck_repo)``；依赖不可用时 skip。"""
    files = FileRepository()
    if not files.list_scan_dates():
        pytest.skip("无 daily_scan 数据（data/reports/daily_scan）")
    if not duck.db_available():
        pytest.skip("历史库不可用（data/history/ct_history.duckdb）")
    return files, DuckDBRepository(HISTORY_DB_PATH)


@pytest.fixture(scope="module")
def scan_dates(repos) -> List[str]:
    return repos[0].list_scan_dates()


# --------------------------------------------------------------------------
# 归一辅助
# --------------------------------------------------------------------------
def _num(value: Any) -> Optional[float]:
    """数值统一为 ``float``（抹平 DuckDB DOUBLE 与源 int 的表示差异）；非数值原样、``None`` 原样。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _member_projection(member: dict) -> str:
    """``by_category`` 成员的**下游消费投影**：``(coin_id, has_market, market_cap, chg24)``。

    与 ``build_sectors`` 实际读取的字段一致（其余字段两端形状不同、无消费者，故不入比对）。
    以字符串形式返回，便于做多重集（``Counter``）比较且规避 ``None`` 参与排序的问题。
    """
    sources = member.get("sources") if isinstance(member, dict) else None
    market = sources.get("market") if isinstance(sources, dict) else None
    data = market.get("data") if isinstance(market, dict) else None
    has_market = bool(data)
    mcap = data.get("market_cap") if isinstance(data, dict) else None
    chg24 = data.get("price_change_percentage_24h") if isinstance(data, dict) else None
    coin_id = member.get("coin_id") if isinstance(member, dict) else None
    return json.dumps(
        [coin_id, has_market, _num(mcap), _num(chg24)], ensure_ascii=False
    )


def _cat_multiset(raw: Dict[str, List[dict]]) -> Dict[str, Counter]:
    """``{slug: Counter(成员投影)}``——对成员顺序不敏感的多重集。"""
    return {slug: Counter(_member_projection(m) for m in members) for slug, members in raw.items()}


def _assert_cat_parity(files: FileRepository, duckdb: DuckDBRepository, date: str) -> None:
    """断言某日 ``load_by_category_raw`` 两端结构等价（slug 集合 / 成员数 / 成员投影多重集）。"""
    f_raw = files.load_by_category_raw(date)
    d_raw = duckdb.load_by_category_raw(date)
    assert set(f_raw) == set(d_raw), f"{date}: 板块 slug 集合不一致"
    assert {k: len(v) for k, v in f_raw.items()} == {k: len(v) for k, v in d_raw.items()}, \
        f"{date}: 各板块成员数不一致"
    assert _cat_multiset(f_raw) == _cat_multiset(d_raw), f"{date}: 成员消费投影多重集不一致"


# --------------------------------------------------------------------------
# 1) 日期解析 / 日历
# --------------------------------------------------------------------------
def test_resolve_scan_date_parity(repos):
    files, duckdb = repos
    for probe in (None, "latest", "2026-08-26", "2099-01-01", "not-a-date"):
        assert files.resolve_scan_date(probe) == duckdb.resolve_scan_date(probe), probe


def test_list_scan_dates_parity(repos):
    files, duckdb = repos
    assert files.list_scan_dates() == duckdb.list_scan_dates()


# --------------------------------------------------------------------------
# 2) load_deep_raw —— 期望**全等**（DB 回放 payload_json）
# --------------------------------------------------------------------------
def test_load_deep_raw_full_parity(repos, scan_dates):
    files, duckdb = repos
    for date in scan_dates:
        f_deep = files.load_deep_raw(date)
        d_deep = duckdb.load_deep_raw(date)
        assert set(f_deep) == set(d_deep), f"{date}: deep coin_id 集合不一致"
        for cid in f_deep:
            assert f_deep[cid] == d_deep[cid], f"{date}/{cid}: deep payload 不等"


# --------------------------------------------------------------------------
# 3) load_all_coins —— 期望 Python ``==`` 全等
# --------------------------------------------------------------------------
def test_load_all_coins_parity(repos, scan_dates):
    files, duckdb = repos
    for date in scan_dates:
        f_coins = files.load_all_coins(date)
        d_coins = duckdb.load_all_coins(date)
        assert len(f_coins) == len(d_coins), f"{date}: 币数不一致"
        assert [c.get("id") for c in f_coins] == [c.get("id") for c in d_coins], f"{date}: 顺序不一致"
        # 逐币比较消费字段（price_usd/market_cap/rank 等），数值以 ``==`` 判定
        for fc, dc in zip(f_coins, d_coins):
            assert fc == dc, f"{date}/{fc.get('id')}: 币字段不等"


# --------------------------------------------------------------------------
# 4) load_summary —— 比对「已入库可重建」字段
# --------------------------------------------------------------------------
def test_load_summary_reproducible_fields_parity(repos, scan_dates):
    files, duckdb = repos
    for date in scan_dates:
        f_sum = files.load_summary(date)
        d_sum = duckdb.load_summary(date)
        assert f_sum is not None and d_sum is not None, f"{date}: summary 缺失"
        # 仅比对**两端共有的可重建字段**：早期扫描日（06-27/06-28）源用旧字段名
        # （top_50_detailed / top_800_light），DuckDB 统一归一为 deep/light_researched，
        # 故不能要求键集相等，只要求交集的取值一致。
        shared = [k for k in SUMMARY_REPRODUCIBLE_KEYS if k in f_sum and k in d_sum]
        assert shared, f"{date}: 无可比字段"
        for key in shared:
            assert d_sum[key] == f_sum[key], f"{date}: summary.{key} 不等"


# --------------------------------------------------------------------------
# 5) load_by_category_raw —— 比对 slug 集合 / 成员数 / 成员投影多重集
# --------------------------------------------------------------------------
def test_load_by_category_raw_parity(repos, scan_dates):
    files, duckdb = repos
    for date in scan_dates:
        _assert_cat_parity(files, duckdb, date)


# --------------------------------------------------------------------------
# 6) find_coin_raw —— 抽样全等
# --------------------------------------------------------------------------
def test_find_coin_raw_parity(repos, scan_dates):
    files, duckdb = repos
    for date in scan_dates:
        deep = files.load_deep_raw(date)
        sample = sorted(deep)[:8]
        for cid in sample:
            assert files.find_coin_raw(date, cid) == duckdb.find_coin_raw(date, cid), f"{date}/{cid}"


# --------------------------------------------------------------------------
# 7) 边界：DB 未收录、源目录也不存在的日期 —— 两端应给出**同一结果**
# --------------------------------------------------------------------------
def test_unknown_date_parity(repos):
    """``2000-01-01``：deep / all_coins 两端皆空；``by_category`` 因「近 7 日窗口取成员最多日」
    会把古老日期解析到历史最优日（保持既有语义），两端须给出**相同**结果。"""
    files, duckdb = repos
    missing = "2000-01-01"
    assert files.load_deep_raw(missing) == duckdb.load_deep_raw(missing) == {}
    assert files.load_all_coins(missing) == duckdb.load_all_coins(missing) == []
    _assert_cat_parity(files, duckdb, missing)


def test_invalid_date_does_not_raise(repos):
    files, duckdb = repos
    bad = "not-a-date"
    assert files.load_by_category_raw(bad) == {}
    # DB 版对非法日期应显式委托文件版（同样为空），而非把非日期字符串 cast 成 DATE 抛错
    assert duckdb.load_by_category_raw(bad) == {}
