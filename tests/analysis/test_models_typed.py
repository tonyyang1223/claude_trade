"""Tests for the type-aware fields added to ProjectScore (src.data.models)."""
from src.data.models import ProjectScore


def test_project_score_new_fields_have_sensible_defaults():
    ps = ProjectScore(
        coin_id="bitcoin", coin_name="Bitcoin", symbol="BTC",
        market_score=5, technical_score=4, onchain_score=5,
        sentiment_score=4, github_score=4, social_score=5, risk_score=5,
        total_score=90.0, rating="A+", recommendation="x", risk_level="low",
    )
    assert ps.token_type is None
    assert ps.peer_group is None
    assert ps.dimension_scores == {}
    assert ps.data_coverage is None
    assert ps.action is None
    assert ps.position_range is None
    assert ps.advice_triggers == []
    # Disclaimer is always attached (carried inline to avoid circular import).
    assert "不构成任何投资建议" in ps.disclaimer


def test_project_score_accepts_typed_payload():
    ps = ProjectScore(
        coin_id="binancecoin", coin_name="BNB", symbol="BNB",
        market_score=4, technical_score=3, onchain_score=3,
        sentiment_score=2, github_score=1, social_score=1, risk_score=3,
        total_score=68.9, rating="C", recommendation="观望", risk_level="medium",
        token_type="layer-1", peer_group="l1",
        dimension_scores={"market": 4, "risk": 3, "tokenomics": 3, "valuation": 5},
        data_coverage=0.63, action="观望", position_range="0–1%",
        advice_triggers=["价格站稳 200 日均线"], disclaimer="⚠️ x",
    )
    assert ps.token_type == "layer-1"
    assert ps.peer_group == "l1"
    assert ps.dimension_scores["tokenomics"] == 3
    assert ps.data_coverage == 0.63
    assert ps.position_range == "0–1%"
    assert ps.advice_triggers == ["价格站稳 200 日均线"]


def test_project_score_disclaimer_inline_constant():
    # The inline DISCLAIMER must match the advice module's red-line text.
    from src.analysis.advice import DISCLAIMER
    ps = ProjectScore(
        coin_id="x", coin_name="X", symbol="X",
        market_score=3, technical_score=3, onchain_score=3, sentiment_score=3,
        github_score=3, social_score=3, risk_score=3, total_score=60.0,
        rating="C", recommendation="y", risk_level="medium",
    )
    # Default disclaimer comes from the inline constant, not the advice import.
    assert ps.disclaimer == DISCLAIMER
