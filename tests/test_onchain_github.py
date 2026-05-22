"""Tests for onchain and GitHub analysis."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.analysis.onchain import OnchainAnalyzer
from src.analysis.github_analyzer import GithubAnalyzer
from src.data.models import OnchainData, GithubData


class TestOnchain:
    """Tests for onchain analysis."""

    def test_score_onchain_extreme_fear(self):
        """Test extreme fear scoring (NUPL < 0)."""
        analyzer = OnchainAnalyzer()
        assert analyzer.score_onchain(-0.1, 1000) == 5

    def test_score_onchain_optimism(self):
        """Test optimism scoring (NUPL 0-0.25)."""
        analyzer = OnchainAnalyzer()
        assert analyzer.score_onchain(0.15, 1000) == 4

    def test_score_onchain_belief(self):
        """Test belief scoring (NUPL 0.25-0.5)."""
        analyzer = OnchainAnalyzer()
        assert analyzer.score_onchain(0.35, 1000) == 3

    def test_score_onchain_greed(self):
        """Test greed scoring (NUPL 0.5-0.75)."""
        analyzer = OnchainAnalyzer()
        assert analyzer.score_onchain(0.6, 1000) == 2

    def test_score_onchain_euphoria(self):
        """Test euphoria scoring (NUPL > 0.75)."""
        analyzer = OnchainAnalyzer()
        assert analyzer.score_onchain(0.8, 1000) == 1

    def test_score_onchain_none(self):
        """Test scoring with no NUPL data."""
        analyzer = OnchainAnalyzer()
        assert analyzer.score_onchain(None, 1000) == 3

    def test_calculate_nupl_proxy_high_mvrp(self):
        """Test NUPL proxy with high MVRV."""
        analyzer = OnchainAnalyzer()
        nupl = analyzer.calculate_nupl_proxy(50000, mvrv=3.5)
        assert nupl == 0.7

    def test_calculate_nupl_proxy_low_mvrp(self):
        """Test NUPL proxy with low MVRV."""
        analyzer = OnchainAnalyzer()
        nupl = analyzer.calculate_nupl_proxy(50000, mvrv=0.8)
        assert nupl == -0.2

    def test_analyze_with_mock(self):
        """Test full analysis with mock data."""
        analyzer = OnchainAnalyzer()
        analyzer.fetch_btc_stats = lambda: {
            "market_price_usd": 50000,
            "n_tx": 1000000,
            "market_cap_usd": 1000000000000
        }
        analyzer.fetch_btc_address_count = lambda: 500000

        result = analyzer.analyze("bitcoin")
        assert isinstance(result, OnchainData)
        assert result.onchain_signal >= 1 and result.onchain_signal <= 5

    def test_analyze_non_bitcoin(self):
        """Test analysis for non-BTC coin returns neutral."""
        analyzer = OnchainAnalyzer()
        result = analyzer.analyze("ethereum")
        assert isinstance(result, OnchainData)
        assert result.onchain_signal == 3


class TestGithub:
    """Tests for GitHub analysis."""

    def test_score_activity_very_active(self):
        """Test very active scoring."""
        analyzer = GithubAnalyzer()
        assert analyzer.score_activity(150, 60) == 5

    def test_score_activity_active(self):
        """Test active scoring."""
        analyzer = GithubAnalyzer()
        assert analyzer.score_activity(60, 30) == 4

    def test_score_activity_moderate(self):
        """Test moderate scoring."""
        analyzer = GithubAnalyzer()
        assert analyzer.score_activity(30, 15) == 3

    def test_score_activity_low(self):
        """Test low scoring."""
        analyzer = GithubAnalyzer()
        assert analyzer.score_activity(10, 6) == 2

    def test_score_activity_inactive(self):
        """Test inactive scoring."""
        analyzer = GithubAnalyzer()
        assert analyzer.score_activity(3, 2) == 1

    def test_analyze_with_mock(self):
        """Test full analysis with mock data."""
        analyzer = GithubAnalyzer()
        analyzer.fetch_repo_info = lambda o, r: {"full_name": f"{o}/{r}"}
        analyzer.fetch_contributors = lambda o, r: list(range(50))
        analyzer.fetch_commits = lambda o, r, days=30: [
            {"commit": {"author": {"date": "2026-05-22T00:00:00Z"}}}
        ] * 30
        analyzer.fetch_issues = lambda o, r, state="open": list(range(20))
        analyzer.fetch_pull_requests = lambda o, r, state="open": list(range(10))

        result = analyzer.analyze("bitcoin", "bitcoin/bitcoin")
        assert isinstance(result, GithubData)
        assert result.commit_count_30d == 30
        assert result.contributor_count == 50
        assert result.activity_score >= 1 and result.activity_score <= 5
