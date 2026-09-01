"""Tests for the token & DeFi protocol research module.

覆盖两类：

1. 纯计算函数（无网络依赖）——指标口径与边界条件。
2. ``TokenDefiResearcher`` 取数封装——通过注入 mock 客户端验证映射与派生指标。

运行：
    pytest tests/research/test_token_defi.py -v
"""
from unittest.mock import MagicMock

import pytest

from src.research.token_defi import (
    UNLOCK_RISK_HIGH,
    UNLOCK_RISK_MEDIUM,
    TokenDefiResearcher,
    circulating_ratio,
    dilution_multiple,
    fdv_mc_ratio,
    fee_to_tvl,
    locked_supply,
    price_to_sales,
    unlock_risk_level,
)


# --------------------------------------------------------------------------
# 纯计算函数
# --------------------------------------------------------------------------

class TestCirculatingRatio:
    """流通率计算测试。"""

    def test_uses_max_supply_as_denominator(self):
        """max_supply 存在时优先作为分母。"""
        assert circulating_ratio(6.0, 10.0, 15.0) == pytest.approx(0.4)

    def test_falls_back_to_total_supply(self):
        """max_supply 缺失时回退到 total_supply。"""
        assert circulating_ratio(5.0, 10.0, None) == pytest.approx(0.5)

    def test_returns_none_when_circulating_missing(self):
        """流通量缺失时返回 None（不编造）。"""
        assert circulating_ratio(None, 10.0, 15.0) is None

    def test_returns_none_when_denominator_missing(self):
        """总量与最大量都缺失时返回 None。"""
        assert circulating_ratio(5.0, None, None) is None

    def test_returns_none_on_zero_denominator(self):
        """分母为 0 时返回 None，避免除零。"""
        assert circulating_ratio(5.0, 0, 0) is None


class TestDilutionMultiple:
    """稀释倍数计算测试。"""

    def test_computes_multiple(self):
        """稀释倍数 = 最大供应量 / 流通量。"""
        assert dilution_multiple(6.0, 10.0, 15.0) == pytest.approx(2.5)

    def test_equals_inverse_of_circulating_ratio(self):
        """稀释倍数与流通率互为倒数。"""
        ratio = circulating_ratio(6.0, 10.0, 15.0)
        assert dilution_multiple(6.0, 10.0, 15.0) == pytest.approx(1 / ratio)

    def test_returns_none_when_inputs_missing(self):
        """输入缺失时返回 None。"""
        assert dilution_multiple(None, 10.0, 15.0) is None
        assert dilution_multiple(6.0, None, None) is None


class TestLockedSupply:
    """待解锁量计算测试。"""

    def test_computes_locked_amount(self):
        """待解锁量 = 最大供应量 - 流通量。"""
        assert locked_supply(9.83, 15.0, 15.0) == pytest.approx(5.17, abs=1e-2)

    def test_clamps_negative_to_zero(self):
        """流通量大于总量时不返回负数，钳制为 0。"""
        assert locked_supply(12.0, 10.0, 10.0) == 0.0

    def test_returns_none_when_inputs_missing(self):
        """输入缺失时返回 None。"""
        assert locked_supply(None, 10.0, 15.0) is None


class TestValuationRatios:
    """估值类比率测试。"""

    def test_fdv_mc_ratio(self):
        """FDV/MC 正常计算。"""
        assert fdv_mc_ratio(2.0e9, 1.0e9) == pytest.approx(2.0)

    def test_fdv_mc_ratio_none_on_zero_market_cap(self):
        """市值为 0 时返回 None，避免除零。"""
        assert fdv_mc_ratio(2.0e9, 0) is None

    def test_price_to_sales(self):
        """P/S 正常计算。"""
        assert price_to_sales(5.0e9, 1.0e9) == pytest.approx(5.0)

    def test_price_to_sales_none_on_zero_fees(self):
        """费用为 0 时返回 None，避免无意义倍数。"""
        assert price_to_sales(5.0e9, 0) is None

    def test_fee_to_tvl(self):
        """资本效率 = 年化费用 / TVL。"""
        assert fee_to_tvl(2.0e8, 1.0e9) == pytest.approx(0.2)

    def test_fee_to_tvl_none_on_zero_tvl(self):
        """TVL 为 0 时返回 None。"""
        assert fee_to_tvl(2.0e8, 0) is None


class TestUnlockRiskLevel:
    """解锁风险分档测试。"""

    def test_high_risk(self):
        """待解锁占比 >= 50% 判为高。"""
        assert unlock_risk_level(0.60) == "高"

    def test_high_risk_boundary(self):
        """边界值 50% 属于高。"""
        assert unlock_risk_level(UNLOCK_RISK_HIGH) == "高"

    def test_medium_risk(self):
        """待解锁占比 >= 30% 且 < 50% 判为中。"""
        assert unlock_risk_level(UNLOCK_RISK_MEDIUM) == "中"
        assert unlock_risk_level(0.45) == "中"

    def test_low_risk(self):
        """待解锁占比 < 30% 判为低。"""
        assert unlock_risk_level(0.10) == "低"

    def test_unknown_when_missing(self):
        """数据缺失时返回未知。"""
        assert unlock_risk_level(None) == "未知"


# --------------------------------------------------------------------------
# 研究器（mock 客户端）
# --------------------------------------------------------------------------

def _coingecko_mock(payload):
    """构造 CoinGecko 客户端 mock。"""
    client = MagicMock()
    client.get_coin_research_data.return_value = payload
    return client


def _defillama_mock(tvl_payload=None, fee_payload=None):
    """构造 DefiLlama 客户端 mock。"""
    client = MagicMock()
    client.get_protocol_tvl.return_value = tvl_payload or {}
    client.get_protocol_fees.return_value = fee_payload or {}
    return client


class TestAnalyzeToken:
    """analyze_token 映射与派生指标测试。"""

    def test_maps_fields_and_derives_ratios(self):
        """正确映射字段并计算流通率 / 稀释倍数 / 待解锁占比。"""
        payload = {
            "symbol": "ENA",
            "name": "Ethena",
            "categories": ["DeFi"],
            "price": 0.15,
            "market_cap": 1.47e9,
            "fdv": 2.25e9,
            "circulating_supply": 9.83e9,
            "total_supply": 15e9,
            "max_supply": 15e9,
            "ath": 1.52,
            "ath_change_pct": -90.1,
            "change_24h": -6.0,
            "change_30d": 86.0,
            "last_updated": "2026-08-31T06:25:40.000Z",
        }
        researcher = TokenDefiResearcher(coingecko=_coingecko_mock(payload))

        snapshot = researcher.analyze_token("ethena")

        assert snapshot.symbol == "ENA"
        assert snapshot.name == "Ethena"
        assert snapshot.price == 0.15
        assert snapshot.circulating_ratio == pytest.approx(9.83 / 15)
        assert snapshot.dilution_multiple == pytest.approx(15 / 9.83)
        assert snapshot.locked_ratio == pytest.approx(1 - 9.83 / 15)
        assert snapshot.fdv_mc_ratio == pytest.approx(2.25e9 / 1.47e9)
        assert snapshot.fetched_at == "2026-08-31T06:25:40.000Z"

    def test_missing_supply_yields_none_ratios(self):
        """供应量缺失时派生指标为 None，不填充占位值。"""
        payload = {
            "symbol": "X", "name": "X", "price": 1.0,
            "circulating_supply": None, "total_supply": None, "max_supply": None,
        }
        researcher = TokenDefiResearcher(coingecko=_coingecko_mock(payload))

        snapshot = researcher.analyze_token("unknown-coin")

        assert snapshot.circulating_ratio is None
        assert snapshot.dilution_multiple is None
        assert snapshot.locked_ratio is None

    def test_to_dict_serializable(self):
        """快照可转字典（供 JSON 输出）。"""
        payload = {"symbol": "BTC", "circulating_supply": 19e6, "max_supply": 21e6}
        researcher = TokenDefiResearcher(coingecko=_coingecko_mock(payload))

        data = researcher.analyze_token("bitcoin").to_dict()

        assert isinstance(data, dict)
        assert data["symbol"] == "BTC"
        assert data["circulating_ratio"] == pytest.approx(19 / 21)


class TestAnalyzeProtocol:
    """analyze_protocol 费用、TVL 与 P/S 测试。"""

    def test_computes_ps_and_fee_to_tvl(self):
        """协议指标与 P/S（FDV / 市值两种口径）正确计算。"""
        researcher = TokenDefiResearcher(
            coingecko=_coingecko_mock(
                {"symbol": "UNI", "market_cap": 3.1e9, "fdv": 4.4e9}
            ),
            defillama=_defillama_mock(
                tvl_payload={
                    "protocol": "Uniswap",
                    "tvl": 3.4e9,
                    "tvl_change_24h": 1.0,
                    "tvl_change_7d": 2.0,
                    "chain_breakdown": {"Ethereum": 2.0e9, "Base": 1.4e9},
                },
                fee_payload={"fees_annualized": 8.3e8, "fees_30d": 9.5e7},
            ),
        )

        snapshot = researcher.analyze_protocol("uniswap", coin_id="uniswap")

        assert snapshot.name == "Uniswap"
        assert snapshot.tvl == 3.4e9
        assert snapshot.fees_annualized == 8.3e8
        assert snapshot.fee_to_tvl == pytest.approx(8.3e8 / 3.4e9)
        assert snapshot.ps_fdv == pytest.approx(4.4e9 / 8.3e8)
        assert snapshot.ps_mcap == pytest.approx(3.1e9 / 8.3e8)
        assert snapshot.chain_breakdown == {"Ethereum": 2.0e9, "Base": 1.4e9}

    def test_ps_none_without_coin_id(self):
        """未传 coin_id 时没有代币估值，P/S 为 None。"""
        researcher = TokenDefiResearcher(
            defillama=_defillama_mock(
                tvl_payload={"protocol": "Curve", "tvl": 1.3e9},
                fee_payload={"fees_annualized": 6.0e7},
            )
        )

        snapshot = researcher.analyze_protocol("curve-dex")

        assert snapshot.token is None
        assert snapshot.ps_fdv is None
        assert snapshot.ps_mcap is None

    def test_ps_none_when_fees_missing(self):
        """费用缺失时 P/S 为 None，不返回 inf。"""
        researcher = TokenDefiResearcher(
            coingecko=_coingecko_mock({"symbol": "X", "fdv": 1e9, "market_cap": 5e8}),
            defillama=_defillama_mock(tvl_payload={"tvl": 1e9}, fee_payload={}),
        )

        snapshot = researcher.analyze_protocol("x", coin_id="x")

        assert snapshot.ps_fdv is None
        assert snapshot.ps_mcap is None


class TestCompareProtocols:
    """批量协议对比测试。"""

    def test_compares_multiple_and_preserves_order(self):
        """按输入顺序返回对比结果。"""
        researcher = TokenDefiResearcher(
            defillama=_defillama_mock(
                tvl_payload={"protocol": "P", "tvl": 1e9},
                fee_payload={"fees_annualized": 1e8},
            )
        )

        results = researcher.compare_protocols([{"slug": "a"}, {"slug": "b"}])

        assert [r.slug for r in results] == ["a", "b"]

    def test_accepts_optional_coin_id(self):
        """支持每项可选 coin_id。"""
        researcher = TokenDefiResearcher(
            coingecko=_coingecko_mock({"symbol": "T", "fdv": 1e9, "market_cap": 5e8}),
            defillama=_defillama_mock(
                tvl_payload={"protocol": "P", "tvl": 1e9},
                fee_payload={"fees_annualized": 1e8},
            ),
        )

        results = researcher.compare_protocols(
            [{"slug": "p", "coin_id": "t"}, {"slug": "q"}]
        )

        assert results[0].token is not None
        assert results[0].ps_fdv == pytest.approx(10.0)
        assert results[1].token is None


class TestUnlockProfiles:
    """解锁抛压画像测试。"""

    def test_builds_profiles_with_risk_levels(self):
        """按流通量计算待解锁占比与风险分档。"""
        researcher = TokenDefiResearcher(
            coingecko=_coingecko_mock(
                {"symbol": "ARB", "circulating_supply": 6.68e9, "max_supply": 10e9,
                 "market_cap": 5.6e8}
            )
        )

        profiles = researcher.unlock_profiles(["arbitrum"])

        assert len(profiles) == 1
        profile = profiles[0]
        assert profile.symbol == "ARB"
        assert profile.circulating_ratio == pytest.approx(0.668, abs=1e-3)
        assert profile.locked_ratio == pytest.approx(0.332, abs=1e-3)
        assert profile.risk_level == "中"

    def test_high_risk_when_mostly_locked(self):
        """流通率低于 50% 时判为高风险。"""
        researcher = TokenDefiResearcher(
            coingecko=_coingecko_mock(
                {"symbol": "NEW", "circulating_supply": 2e9, "max_supply": 10e9}
            )
        )

        profile = researcher.unlock_profiles(["new-coin"])[0]

        assert profile.locked_ratio == pytest.approx(0.8)
        assert profile.risk_level == "高"
        assert profile.dilution_multiple == pytest.approx(5.0)

    def test_skips_failed_symbol_without_breaking(self):
        """单个代币取数失败只跳过，不中断整体。"""
        client = MagicMock()
        client.get_coin_research_data.side_effect = [
            Exception("API unavailable"),
            {"symbol": "OK", "circulating_supply": 5e9, "max_supply": 10e9},
        ]
        researcher = TokenDefiResearcher(coingecko=client)

        profiles = researcher.unlock_profiles(["bad-coin", "good-coin"])

        assert len(profiles) == 1
        assert profiles[0].symbol == "OK"


class TestDependencyInjection:
    """依赖注入与默认构造测试。"""

    def test_injected_clients_are_used(self):
        """注入的客户端被实际调用（未新建真实客户端）。"""
        cg = _coingecko_mock({"symbol": "A", "circulating_supply": 1e9, "max_supply": 2e9})
        dl = _defillama_mock(tvl_payload={"protocol": "A", "tvl": 1e8})

        researcher = TokenDefiResearcher(coingecko=cg, defillama=dl)
        researcher.analyze_protocol("a", coin_id="a")

        cg.get_coin_research_data.assert_called_once_with("a")
        dl.get_protocol_tvl.assert_called_once_with("a")
        dl.get_protocol_fees.assert_called_once_with("a")

    def test_default_clients_created_lazily(self):
        """默认构造会创建真实客户端（仅验证类型不发起请求）。"""
        researcher = TokenDefiResearcher()
        assert researcher.coingecko is not None
        assert researcher.defillama is not None
