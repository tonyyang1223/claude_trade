"""Tests for BTC dominance and sentiment analysis."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.analysis.btc_dominance import BTCDominanceAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.data.models import BTCDominance, SentimentData


class TestBTCDominance:
    """Tests for BTC dominance analysis."""

    def test_determine_trend_rising(self):
        """Test rising trend detection."""
        analyzer = BTCDominanceAnalyzer()
        assert analyzer.determine_trend(55) == "rising"

    def test_determine_trend_falling(self):
        """Test falling trend detection."""
        analyzer = BTCDominanceAnalyzer()
        assert analyzer.determine_trend(35) == "falling"

    def test_determine_trend_stable(self):
        """Test stable trend detection."""
        analyzer = BTCDominanceAnalyzer()
        assert analyzer.determine_trend(45) == "stable"

    def test_is_altcoin_season(self):
        """Test altcoin season detection."""
        analyzer = BTCDominanceAnalyzer()
        assert analyzer.is_altcoin_season(40) == True
        assert analyzer.is_altcoin_season(50) == False

    def test_determine_market_phase(self):
        """Test market phase determination."""
        analyzer = BTCDominanceAnalyzer()
        phase = analyzer.determine_market_phase(55, "rising")
        assert "BTC主导" in phase

    def test_analyze_with_mock(self):
        """Test full analysis with mock data."""
        analyzer = BTCDominanceAnalyzer()
        analyzer.fetch_dominance_data = lambda: {"btc_dominance": 52.5}

        result = analyzer.analyze()
        assert isinstance(result, BTCDominance)
        assert result.current_dominance == 52.5
        assert result.trend in ["rising", "falling", "stable"]
        assert isinstance(result.altcoin_season, bool)
        assert isinstance(result.recommendation, str)


class TestSentiment:
    """Tests for sentiment analysis."""

    def test_score_fear_greed_extreme_fear(self):
        """Test extreme fear scoring."""
        analyzer = SentimentAnalyzer()
        assert analyzer.score_fear_greed(10) == 5
        assert analyzer.score_fear_greed(25) == 5

    def test_score_fear_greed_extreme_greed(self):
        """Test extreme greed scoring."""
        analyzer = SentimentAnalyzer()
        assert analyzer.score_fear_greed(80) == 1
        assert analyzer.score_fear_greed(95) == 1

    def test_score_fear_greed_neutral(self):
        """Test neutral scoring."""
        analyzer = SentimentAnalyzer()
        assert analyzer.score_fear_greed(50) == 3

    def test_determine_social_sentiment(self):
        """Test social sentiment determination."""
        analyzer = SentimentAnalyzer()
        assert analyzer.determine_social_sentiment(70, 70) == "greedy"
        assert analyzer.determine_social_sentiment(20, 20) == "fearful"
        assert analyzer.determine_social_sentiment(50, 50) == "neutral"

    def test_analyze_with_mock(self):
        """Test full analysis with mock data."""
        analyzer = SentimentAnalyzer()
        mock_fg = {"data": [{"value": "45", "classification": "Neutral"}]}
        analyzer.fetch_fear_greed_index = lambda: mock_fg

        result = analyzer.analyze("bitcoin")
        assert isinstance(result, SentimentData)
        assert 0 <= result.fear_greed_index <= 100
        assert 1 <= result.sentiment_signal <= 5
        assert result.social_sentiment in ["greedy", "fearful", "neutral"]