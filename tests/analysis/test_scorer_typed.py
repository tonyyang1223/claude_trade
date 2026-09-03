"""Tests for the type-aware (typed) scoring path in src.analysis.scorer.

Focus: when analyzers are passed as None in typed mode, the Scorer must
*skip* them (dimension -> None, excluded from coverage) rather than
re-instantiating defaults that would hit blocked external hosts.
"""
import pytest
from unittest.mock import Mock

from src.analysis.scorer import Scorer
from src.analysis.profiles import get_profile


class _Snapshot:
    circulating_ratio = 0.8
    dilution_multiple = 1.5
    locked_ratio = 0.2
    fdv_mc_ratio = 2.0


def _make_typed_scorer(token_type="layer-1"):
    token_researcher = Mock()
    token_researcher.analyze_token.return_value = _Snapshot()
    return Scorer(
        token_type=token_type,
        token_researcher=token_researcher,
        # All blocked external analyzers explicitly disabled.
        technical_analyzer=None,
        onchain_analyzer=None,
        sentiment_analyzer=None,
        github_analyzer=None,
    )


def test_typed_analyzers_stay_none_when_passed_none():
    s = _make_typed_scorer()
    assert s.profile is not None
    assert s.technical is None
    assert s.onchain is None
    assert s.sentiment is None
    assert s.github is None


def test_typed_scorer_skips_none_analyzers(monkeypatch):
    s = _make_typed_scorer()

    # Only CoinGecko-backed dims are available; the rest are None analyzers.
    market = Mock()
    market.market_cap_rank = 1
    market.name = "Bitcoin"
    market.symbol = "btc"
    social = Mock()
    social.social_score = 4
    risk = Mock()
    risk.risk_score = 3

    monkeypatch.setattr(s, "_get_market_data", lambda cid: market)
    monkeypatch.setattr(s, "_get_social_data", lambda cid: social)
    monkeypatch.setattr(s, "_get_risk_data", lambda cid, md=None: risk)

    ps = s.score_project("bitcoin")

    # None analyzers must NOT appear as scored dimensions.
    scored = ps.dimension_scores
    assert "technical" not in scored
    assert "onchain" not in scored
    assert "sentiment" not in scored
    assert "github" not in scored
    # CoinGecko dims + tokenomics/valuation (from snapshot) must be present.
    assert scored["market"] == 5
    assert scored["social"] == 4
    assert scored["risk"] == 3
    assert "tokenomics" in scored
    assert "valuation" in scored


def test_typed_coverage_excludes_skipped_dims():
    s = _make_typed_scorer()
    prof = get_profile("layer-1")
    # Sum of weights for the dims we actually scored.
    expected = sum(
        prof.weights[d] for d in ("market", "social", "risk", "tokenomics", "valuation")
    )
    assert abs(s.score_project("bitcoin").data_coverage - round(expected, 3)) < 0.02


def test_typed_adds_research_fields():
    s = _make_typed_scorer()
    ps = s.score_project("bitcoin")
    assert ps.token_type == "layer-1"
    assert ps.peer_group == "l1"
    assert ps.action in ("重点关注", "建议关注", "小仓试探", "观望", "回避")
    assert "%" in ps.position_range
    assert "不构成任何投资建议" in ps.disclaimer


def test_typed_legacy_path_keeps_defaults_when_no_profile():
    # Without a token_type/profile, legacy mode must still create defaults.
    s = Scorer()
    assert s.profile is None
    assert s.technical is not None
    assert s.onchain is not None
