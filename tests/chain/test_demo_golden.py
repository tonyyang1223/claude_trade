"""P0 冻结基线 + 决策护栏（demo 确定性 & config 驱动档位/护栏边界）。

demo 三链不触网、数据静态 → 断言综合分/决策/仓位固定（迁移回归基线）。
护栏测试用合成 ctx 验证「只降不升」且档位受 config 驱动。
"""
from __future__ import annotations

import pytest

from src.chain.advisor import decide
from src.chain.config import AnalysisConfig
from src.chain.orchestrator import analyze
from src.chain.types import AnalysisResult, Chain, DexQuote, TokenProfile


class TestDemoGolden:
    """重构回归基线：demo 结论不得漂移（skill_design.md §6 Phase 0）。"""

    def test_demo_bnb_cashcat_golden(self):
        ctx, dec = analyze("bnb", "CASHCAT", demo=True)
        assert dec["total"] == pytest.approx(7.0, abs=0.05)
        assert dec["decision"] == "🟡 持有/观察"
        assert dec["position"] == "3%-5%"
        assert dec["risk"] == "中"
        assert "sentiment" in dec["missing"]  # 无凭证维度应缺失并排除
        assert ctx.engine_version
        assert ctx.fetched_at is not None

    def test_demo_all_chains_ok(self):
        for c in ("bnb", "sol", "robinhood"):
            ctx, dec = analyze(c, f"DEMO{c}", demo=True)
            assert 0.0 <= dec["total"] <= 10.0
            assert dec["position"]
            assert ctx.symbol

    def test_demo_deterministic(self):
        a1, d1 = analyze("sol", "DEMO", demo=True)
        a2, d2 = analyze("sol", "DEMO", demo=True)
        assert d1["total"] == d2["total"]
        assert d1["decision"] == d2["decision"]


class TestDecisionGuards:
    """护栏语义：只降不升；阈值与降档级别由 config 驱动。"""

    def _ctx(self, *, age_days=40.0, lp_locked=None, cfg=None):
        ctx = AnalysisResult(
            chain=Chain.BNB, address="0x" + "3" * 40,
            symbol="T", name="Test",
            profile=TokenProfile(chain=Chain.BNB, address="0x" + "3" * 40,
                                 age_days=age_days),
            dex=DexQuote(liquidity_usd=1_000_000, price_change_24h=5.0,
                         age_days=age_days),
            cfg=cfg,
        )
        if lp_locked is not None:
            from src.chain.types import LiquidityInfo
            ctx.liquidity = LiquidityInfo(total_liquidity_usd=1_000_000,
                                          locked_pct=lp_locked)
        return ctx

    def test_no_guard_high_total_keeps_top_band(self):
        ctx = self._ctx(age_days=40, lp_locked=90)
        dec = decide(ctx, total=8.5, scored={"security": 9.0,
                                             "liquidity_health": 8.0}, missing=[])
        assert dec["decision"] == "🟢 可关注 · 小仓试探"
        assert dec["position"] == "5%-10%"

    def test_guard_newcoin_lp_unknown_forced_avoid(self):
        ctx = self._ctx(age_days=0.5, lp_locked=None)
        dec = decide(ctx, total=8.5, scored={"security": 9.0,
                                             "liquidity_health": 8.0}, missing=[])
        # age<1(→档2) 且 <7天+LP未知(→档3=回避)：护栏只降不升
        assert dec["decision"] == "🔴 回避"
        assert dec["position"] == "0%"
        assert any("风险护栏" in t for t in dec["triggers"])

    def test_guard_age_only_downgrade_to_light(self):
        # age<1 但 LP 已知（locked=90）→ 无第3护栏，只降到第2档
        ctx = self._ctx(age_days=0.5, lp_locked=90)
        dec = decide(ctx, total=8.5, scored={"security": 9.0,
                                             "liquidity_health": 8.0}, missing=[])
        assert dec["decision"] == "🟡 轻仓观察"
        assert dec["position"] == "1%-3%"

    def test_guard_liquidity_health_level_configurable(self):
        # meme_strict：流动性健康<3 直接回避（level 3），与默认(level 2)不同
        from pathlib import Path
        strict = AnalysisConfig.load(str(
            Path(__file__).resolve().parents[2] / "config" / "chain" / "meme_strict.yaml"))
        ctx = self._ctx(age_days=40, lp_locked=90, cfg=strict)
        dec = decide(ctx, total=7.0, scored={"security": 9.0,
                                             "liquidity_health": 2.5}, missing=[])
        assert dec["decision"] == "🔴 回避"
        # 对照默认配置 → 仅降到轻仓观察
        ctx2 = self._ctx(age_days=40, lp_locked=90)
        dec2 = decide(ctx2, total=7.0, scored={"security": 9.0,
                                               "liquidity_health": 2.5}, missing=[])
        assert dec2["decision"] == "🟡 轻仓观察"

    def test_hard_block_when_security_low(self):
        ctx = self._ctx(age_days=40, lp_locked=90)
        dec = decide(ctx, total=8.0, scored={"security": 3.0}, missing=[])
        assert dec["decision"] == "🚫 高风险 · 不建议参与"
        assert dec["position"] == "0%"

    def test_security_hard_block_threshold_configurable(self):
        cfg = AnalysisConfig.load({"decision": {"hard_block_security_lt": 8.5}})
        ctx = self._ctx(age_days=40, lp_locked=90, cfg=cfg)
        dec = decide(ctx, total=8.0, scored={"security": 8.0}, missing=[])
        assert dec["decision"] == "🚫 高风险 · 不建议参与"
