"""GoPlus 解析单元测试（白盒，不触网）：LP 锁死推导 + owner renounce + 字段映射。

覆盖 bibi 实战发现的 lp_holders / launchpad / owner 强信号（skill_design.md §5.4）。
"""
from __future__ import annotations

from src.chain.sources import goplus


def _fake_goplus_result() -> dict:
    return {
        "contract_name": "Bibi",
        "is_open_source": "1",
        "owner_address": "0x0000000000000000000000000000000000000000",
        "creator_address": "0x36b854d67ba956fd359911e5d3c177caaaff9464",
        "creator_percent": "0.000000",
        "is_mintable": "0",
        "is_proxy": "0",
        "can_take_back_ownership": "0",
        "selfdestruct": "0",
        "hidden_owner": "0",
        "external_call": "0",
        "transfer_pausable": "0",
        "buy_tax": "0",
        "sell_tax": "0",
        "is_honeypot": "0",
        "holder_count": "57619",
        "top_10_holder_percent": "45.0",
        "top_50_holder_percent": "66.0",
        "lp_total_supply": "59396.96",
        "lp_holders": [
            {"address": "0x000000000000000000000000000000000000dead",
             "percent": "0.99999999", "is_locked": 1},
            {"address": "0x0000000000000000000000000000000000000000",
             "percent": "0.0", "is_locked": 0},
        ],
    }


class TestLpLockDerivation:
    def test_burned_lp_full_lock(self):
        liq = goplus._lp_liquidity(_fake_goplus_result())
        assert liq is not None
        assert liq.locked_pct == pytest_approx(99.999999)
        assert liq.is_burned is True
        assert liq.dex == "goplus"

    def test_no_lp_holders_returns_none(self):
        r = _fake_goplus_result()
        r["lp_holders"] = []
        assert goplus._lp_liquidity(r) is None

    def test_partial_lock_not_burned(self):
        r = _fake_goplus_result()
        r["lp_holders"] = [
            {"address": "0xabcdef", "percent": "0.40", "is_locked": 0},
            {"address": "0xdead", "percent": "0.60", "is_locked": 1},
        ]
        liq = goplus._lp_liquidity(r)
        assert liq.locked_pct == pytest_approx(60.0)
        assert liq.is_burned is False


class TestModelMapping:
    def test_owner_renounced_and_fields(self):
        sec, holders = goplus._to_models(_fake_goplus_result())
        assert sec.owner_renounced is True
        assert sec.is_mintable is False
        assert sec.is_proxy is False
        assert sec.is_verified is True          # is_open_source=1
        assert sec.buy_tax_pct == 0.0
        assert holders.total_holders == 57619
        assert holders.top10_pct == 45.0
        assert holders.creator_pct == 0.0

    def test_owner_active_detection(self):
        r = _fake_goplus_result()
        r["owner_address"] = "0x36b854d67ba956fd359911e5d3c177caaaff9464"
        sec, _ = goplus._to_models(r)
        assert sec.owner_renounced is False


def pytest_approx(v):
    from pytest import approx
    return approx(v)
