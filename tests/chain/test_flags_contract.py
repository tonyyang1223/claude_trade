"""P3 红旗契约 + 安全维度边界测试（设计文档 §1.2 / §3）。"""
from __future__ import annotations

from src.chain.config import AnalysisConfig
from src.chain.security import FLAG_CODES, analyze_security
from src.chain.types import (
    AnalysisResult,
    Chain,
    ContractSecurity,
    Flag,
    HolderStats,
    LiquidityInfo,
    TokenProfile,
)


def _mk(**kw):
    base = dict(chain=Chain.BNB, address="0x" + "1" * 40)
    base.update(kw)
    return AnalysisResult(**base)


def _sec_clean() -> ContractSecurity:
    return ContractSecurity(is_verified=True, owner_renounced=True, is_mintable=False,
                            can_take_back_ownership=False, buy_tax_pct=0.0, sell_tax_pct=0.0,
                            hidden_honeypot=False, is_in_blacklist=False,
                            is_proxy=False, can_blacklist=False, can_pause=False,
                            has_owner_fn=True)


class TestFlagSchema:
    def test_flag_levels_and_codes(self):
        f = Flag(level="ok", code="SUPPLY_FIXED", msg="x")
        assert f.level == "ok"
        for bad_level in ("info", "HIGH", 1):
            try:
                Flag(level=bad_level, code="X", msg="x")  # type: ignore
                raise AssertionError(f"level 应被拒绝: {bad_level!r}")
            except Exception:
                pass

    def test_flag_code_set_exhaustive(self):
        """红旗 code 全部来自受控枚举，便于下游程序化消费。"""
        ctx = _mk()
        _, flags = analyze_security(ctx)  # 空数据 → 无红旗
        assert flags == []
        # 覆盖能触发的 code 均应在枚举集合
        assert FLAG_CODES

    def test_legacy_str_flags_coerce(self):
        """历史 dump 的字符串 flags 可被向后加载为结构化 Flag。"""
        ctx = AnalysisResult.model_validate({
            "chain": "bnb",
            "address": "0x" + "2" * 40,
            "flags": ["🚨 honeypot!", "✅ 供应固定", "⚠️ 待确认"],
        })
        assert [f.level for f in ctx.flags] == ["bad", "ok", "warn"]
        assert ctx.flags[0].code == "LEGACY"
        assert ctx.flags[0].msg == "🚨 honeypot!"
        assert ctx.flags[1].code == "LEGACY"


class TestSecurityBoundaries:
    def test_no_data_means_missing(self):
        score, flags = analyze_security(_mk())
        assert score is None and flags == []

    def test_honeypot_zeroes_score(self):
        ctx = _mk(security=ContractSecurity(hidden_honeypot=True))
        score, flags = analyze_security(ctx)
        assert score == 0.0
        assert flags[0].level == "bad" and flags[0].code == "HONEYPOT"

    def test_clean_contract_with_unknown_lp_capped_at_7_5(self):
        """合约干净但 LP+持币集中度均未知 → 安全分上限 7.5 + LP_UNVERIFIED。"""
        ctx = _mk(security=_sec_clean())
        score, flags = analyze_security(ctx)
        assert score <= 7.5
        assert any(f.code == "LP_UNVERIFIED" for f in flags)

    def test_full_evidence_clean_gets_high_score(self):
        ctx = _mk(
            security=_sec_clean(),
            holders=HolderStats(total_holders=10_000, top10_pct=12.0, creator_pct=1.0),
            liquidity=LiquidityInfo(total_liquidity_usd=1e6, locked_pct=90.0, is_burned=True),
        )
        score, flags = analyze_security(ctx)
        assert score >= 8.0
        # 正面 ok 证据应存在
        assert any(f.level == "ok" for f in flags)
        assert not any(f.code == "LP_UNVERIFIED" for f in flags)

    def test_mintable_penalty_and_flag(self):
        ctx = _mk(security=ContractSecurity(is_mintable=True),
                  holders=HolderStats(total_holders=100),
                  liquidity=LiquidityInfo(locked_pct=80))
        score, flags = analyze_security(ctx)
        assert any(f.code == "MINTABLE" and f.level == "warn" for f in flags)
        assert score < 8.0

    def test_config_cap_override(self):
        """配置可将 LP 未验证上限调高/调低，说明策略确实外置。"""
        ctx = _mk(security=_sec_clean())
        cfg = AnalysisConfig.load({"security": {"lp_unverified_cap": 5.0}})
        ctx.cfg = cfg
        score, _ = analyze_security(ctx)
        assert score == 5.0
