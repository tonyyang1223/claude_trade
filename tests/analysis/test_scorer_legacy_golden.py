"""Golden (regression) test: legacy 7-dimension scorer is byte-for-byte stable.

After introducing the type-aware path and analyzer-skip logic, the legacy
path (Scorer() with no profile) must keep producing identical ratings and
structures so existing consumers / charts / templates don't break.
"""
from unittest.mock import Mock, patch

from src.analysis.scorer import Scorer
from src.data.models import ProjectScore


@patch("src.analysis.scorer.Scorer._get_market_data")
@patch("src.analysis.scorer.Scorer._get_technical_indicators")
@patch("src.analysis.scorer.Scorer._get_onchain_data")
@patch("src.analysis.scorer.Scorer._get_sentiment_data")
@patch("src.analysis.scorer.Scorer._get_github_data")
@patch("src.analysis.scorer.Scorer._get_social_data")
@patch("src.analysis.scorer.Scorer._get_risk_data")
def test_legacy_total_score_is_deterministic(
    mock_risk, mock_social, mock_github, mock_sentiment,
    mock_onchain, mock_technical, mock_market,
):
    market = Mock()
    market.market_cap_rank = 1
    market.name = "Bitcoin"
    market.symbol = "btc"
    mock_market.return_value = market

    tech = Mock()
    tech.rsi_signal = 4
    tech.ma_signal = 4
    tech.trend_signal = 4
    tech.volume_signal = 4
    mock_technical.return_value = tech

    onchain = Mock()
    onchain.onchain_signal = 4
    mock_onchain.return_value = onchain

    sent = Mock()
    sent.sentiment_signal = 3
    mock_sentiment.return_value = sent

    gh = Mock()
    gh.activity_score = 5
    mock_github.return_value = gh

    mock_social.return_value = Mock(social_score=4)
    mock_risk.return_value = Mock(risk_score=4)

    s = Scorer()
    ps = s.score_project("bitcoin")

    # Manual: 5*.20 + 4*.15 + 4*.20 + 3*.10 + 5*.10 + 4*.10 + 4*.15 = 4.2 -> 84
    assert isinstance(ps, ProjectScore)
    assert ps.total_score == 84.0
    assert ps.rating == "A"
    # Legacy parallel fields still populated (kept for backward compatibility).
    assert ps.market_score == 5
    assert ps.technical_score == 4
    assert ps.onchain_score == 4
    assert ps.sentiment_score == 3
    assert ps.github_score == 5
    assert ps.social_score == 4
    assert ps.risk_score == 4


def test_legacy_profile_is_none():
    s = Scorer()
    # No token_type -> legacy path, default analyzers created.
    assert s.profile is None
    assert s.technical is not None
    ps = s.score_project("bitcoin")
    # Legacy ProjectScore has no type-aware payload noise.
    assert ps.token_type is None
