"""P1 配置层契约测试：加载 / 合并 / 校验 / 覆盖 / 异常。"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.chain.config import (
    AnalysisConfig,
    DecisionBand,
    SecurityPolicy,
    WeightsConfig,
)

CHAIN_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "chain"

_KNOWN_DIMS = {"security", "trend", "momentum", "liquidity_health",
               "sentiment", "innovation", "taxonomy", "community"}


def _sum1(ws: dict) -> bool:
    return abs(sum(ws.values()) - 1.0) < 1e-9


class TestLoad:
    def test_default_loads_and_weights_sum_to_one(self):
        cfg = AnalysisConfig.load()
        assert cfg.engine_version
        assert _sum1(cfg.weights.default)
        for cat, ws in cfg.weights.categories.items():
            assert _sum1(ws), f"类别权重和必须为1: {cat}"
        assert set(cfg.weights.default) == _KNOWN_DIMS

    def test_dict_override_decision(self):
        cfg = AnalysisConfig.load({"decision": {"hard_block_security_lt": 5.5}})
        assert cfg.decision.hard_block_security_lt == 5.5
        # 未覆盖字段仍回落默认
        assert cfg.decision.soft_block_security_lt == 6.0

    def test_yaml_override_file(self):
        path = CHAIN_CONFIG_DIR / "meme_strict.yaml"
        cfg = AnalysisConfig.load(str(path))
        assert cfg.decision.guard_newcoin_days_lt == 14.0
        assert cfg.decision.guard_age_level == 3
        assert cfg.weights.categories["Meme"]["security"] == pytest.approx(0.30)
        assert cfg.weights.categories["Meme"]["momentum"] == pytest.approx(0.15)
        assert _sum1(cfg.weights.categories["Meme"])

    def test_yaml_default_file_roundtrip(self):
        path = CHAIN_CONFIG_DIR / "default.yaml"
        cfg = AnalysisConfig.load(str(path))
        base = AnalysisConfig.load()
        assert cfg.weights.default == base.weights.default
        assert cfg.decision.bands == base.decision.bands

    def test_weights_for_category(self):
        cfg = AnalysisConfig.load()
        assert cfg.weights_for("Meme")["momentum"] == pytest.approx(0.18)
        assert cfg.weights_for("UnknownCat") == cfg.weights.default

    def test_invalid_enabled_dims_raises(self):
        with pytest.raises(Exception):
            AnalysisConfig.load({"enabled_dims": ["bogus_dim"]})

    def test_bad_weights_sum_raises(self):
        with pytest.raises(Exception):
            WeightsConfig(
                default={k: 0.1 for k in _KNOWN_DIMS},  # 和 0.8 ≠ 1
                categories={},
            )

    def test_security_policy_defaults(self):
        p = SecurityPolicy()
        assert p.lp_unverified_cap == 7.5
        assert p.low_coverage_cap == 7.0
        assert p.penalties["mint"] == -2.5


class TestSchema:
    def test_decision_bands_sorted_semantics(self):
        cfg = AnalysisConfig.load()
        mins = [b.min_total for b in cfg.decision.bands]
        assert mins == sorted(mins, reverse=True)

    def test_band_model(self):
        b = DecisionBand(min_total=6.0, label="x", position="1-3%", risk="中")
        assert b.note == ""
