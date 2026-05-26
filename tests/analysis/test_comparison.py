"""Tests for project comparison engine."""
from datetime import datetime

import pytest

from src.data.models import ProjectScore, ComparisonReport
from src.analysis.comparison import ProjectComparator


@pytest.fixture
def sample_score1():
    """Create sample project score 1."""
    return ProjectScore(
        coin_id='bitcoin',
        coin_name='Bitcoin',
        symbol='BTC',
        market_score=5,
        technical_score=4,
        onchain_score=5,
        sentiment_score=4,
        github_score=4,
        social_score=5,
        risk_score=5,
        total_score=90.0,
        rating='A+',
        recommendation='强烈建议关注',
        risk_level='low'
    )


@pytest.fixture
def sample_score2():
    """Create sample project score 2."""
    return ProjectScore(
        coin_id='ethereum',
        coin_name='Ethereum',
        symbol='ETH',
        market_score=4,
        technical_score=5,
        onchain_score=4,
        sentiment_score=4,
        github_score=5,
        social_score=4,
        risk_score=4,
        total_score=82.0,
        rating='A',
        recommendation='建议关注',
        risk_level='low'
    )


@pytest.fixture
def sample_score3():
    """Create sample project score 3."""
    return ProjectScore(
        coin_id='cardano',
        coin_name='Cardano',
        symbol='ADA',
        market_score=3,
        technical_score=3,
        onchain_score=3,
        sentiment_score=3,
        github_score=4,
        social_score=3,
        risk_score=3,
        total_score=65.0,
        rating='C',
        recommendation='谨慎观望',
        risk_level='medium'
    )


@pytest.fixture
def comparator():
    """Create comparator instance."""
    return ProjectComparator()


class TestProjectComparator:
    """Tests for ProjectComparator class."""

    def test_initialization(self):
        """Test comparator initialization."""
        comp = ProjectComparator()
        assert comp.scorer is not None

    def test_initialization_with_scorer(self):
        """Test comparator with custom scorer."""
        from src.analysis.scorer import Scorer

        scorer = Scorer()
        comp = ProjectComparator(scorer=scorer)
        assert comp.scorer == scorer

    def test_build_comparison_matrix(self, comparator, sample_score1, sample_score2):
        """Test building comparison matrix."""
        scores = [sample_score1, sample_score2]

        matrix = comparator.build_comparison_matrix(scores)

        assert 'bitcoin' in matrix
        assert 'ethereum' in matrix
        assert matrix['bitcoin']['market'] == 5
        assert matrix['ethereum']['market'] == 4
        assert matrix['bitcoin']['total'] == 90.0
        assert matrix['ethereum']['total'] == 82.0

    def test_get_dimension_rankings(self, comparator, sample_score1, sample_score2):
        """Test dimension rankings."""
        scores = [sample_score1, sample_score2]

        rankings = comparator.get_dimension_rankings(scores)

        assert 'market' in rankings
        assert 'technical' in rankings
        assert len(rankings['market']) == 2

        # Bitcoin should be ranked first in market
        assert rankings['market'][0]['coin'] == 'Bitcoin'
        assert rankings['market'][0]['score'] == 5

        # Ethereum should be ranked first in technical
        assert rankings['technical'][0]['coin'] == 'Ethereum'
        assert rankings['technical'][0]['score'] == 5

    def test_calculate_win_counts(self, comparator, sample_score1, sample_score2):
        """Test win count calculation."""
        scores = [sample_score1, sample_score2]

        win_counts = comparator.calculate_win_counts(scores)

        # Bitcoin wins market(5>4), onchain(5>4), sentiment(4=4 tie), social(5>4), risk(5>4)
        # sentiment is tied so both get a win
        assert win_counts['bitcoin'] == 5

        # Ethereum wins technical(5>4), github(5>4), sentiment(4=4 tie)
        assert win_counts['ethereum'] == 3

    def test_calculate_win_counts_ties(self, comparator):
        """Test win counts with ties."""
        score1 = ProjectScore(
            coin_id='coin1',
            coin_name='Coin1',
            symbol='C1',
            market_score=4,
            technical_score=4,
            onchain_score=3,
            sentiment_score=3,
            github_score=3,
            social_score=3,
            risk_score=3,
            total_score=70.0,
            rating='B',
            recommendation='test',
            risk_level='medium'
        )

        score2 = ProjectScore(
            coin_id='coin2',
            coin_name='Coin2',
            symbol='C2',
            market_score=4,
            technical_score=4,
            onchain_score=3,
            sentiment_score=3,
            github_score=3,
            social_score=3,
            risk_score=3,
            total_score=70.0,
            rating='B',
            recommendation='test',
            risk_level='medium'
        )

        scores = [score1, score2]
        win_counts = comparator.calculate_win_counts(scores)

        # All dimensions are tied, so both get 7 wins
        assert win_counts['coin1'] == 7
        assert win_counts['coin2'] == 7

    def test_compare_projects_two(self, comparator):
        """Test comparing two projects."""
        # Mock the scorer to return test scores
        def mock_score_project(coin_id):
            if coin_id == 'bitcoin':
                return ProjectScore(
                    coin_id='bitcoin',
                    coin_name='Bitcoin',
                    symbol='BTC',
                    market_score=5,
                    technical_score=4,
                    onchain_score=5,
                    sentiment_score=4,
                    github_score=4,
                    social_score=5,
                    risk_score=5,
                    total_score=90.0,
                    rating='A+',
                    recommendation='强烈建议关注',
                    risk_level='low'
                )
            else:
                return ProjectScore(
                    coin_id='ethereum',
                    coin_name='Ethereum',
                    symbol='ETH',
                    market_score=4,
                    technical_score=5,
                    onchain_score=4,
                    sentiment_score=4,
                    github_score=5,
                    social_score=4,
                    risk_score=4,
                    total_score=82.0,
                    rating='A',
                    recommendation='建议关注',
                    risk_level='low'
                )

        comparator.scorer.score_project = mock_score_project

        report = comparator.compare_projects(['bitcoin', 'ethereum'])

        assert isinstance(report, ComparisonReport)
        assert len(report.projects) == 2
        assert report.winner == 'bitcoin'
        assert 'bitcoin' in report.comparison_matrix
        assert 'ethereum' in report.comparison_matrix
        assert 'Bitcoin' in report.analysis_summary

    def test_compare_projects_three(self, comparator):
        """Test comparing three projects."""
        def mock_score_project(coin_id):
            scores = {
                'bitcoin': ProjectScore(
                    coin_id='bitcoin',
                    coin_name='Bitcoin',
                    symbol='BTC',
                    market_score=5,
                    technical_score=4,
                    onchain_score=5,
                    sentiment_score=4,
                    github_score=4,
                    social_score=5,
                    risk_score=5,
                    total_score=90.0,
                    rating='A+',
                    recommendation='强烈建议关注',
                    risk_level='low'
                ),
                'ethereum': ProjectScore(
                    coin_id='ethereum',
                    coin_name='Ethereum',
                    symbol='ETH',
                    market_score=4,
                    technical_score=5,
                    onchain_score=4,
                    sentiment_score=4,
                    github_score=5,
                    social_score=4,
                    risk_score=4,
                    total_score=82.0,
                    rating='A',
                    recommendation='建议关注',
                    risk_level='low'
                ),
                'cardano': ProjectScore(
                    coin_id='cardano',
                    coin_name='Cardano',
                    symbol='ADA',
                    market_score=3,
                    technical_score=3,
                    onchain_score=3,
                    sentiment_score=3,
                    github_score=4,
                    social_score=3,
                    risk_score=3,
                    total_score=65.0,
                    rating='C',
                    recommendation='谨慎观望',
                    risk_level='medium'
                )
            }
            return scores.get(coin_id)

        comparator.scorer.score_project = mock_score_project

        report = comparator.compare_projects(['bitcoin', 'ethereum', 'cardano'])

        assert len(report.projects) == 3
        assert report.winner == 'bitcoin'

    def test_compare_projects_minimum_error(self, comparator):
        """Test error when less than 2 projects."""
        with pytest.raises(ValueError, match="At least 2 projects required"):
            comparator.compare_projects(['bitcoin'])

    def test_compare_projects_maximum_error(self, comparator):
        """Test error when more than 5 projects."""
        with pytest.raises(ValueError, match="Maximum 5 projects can be compared"):
            comparator.compare_projects([
                'bitcoin', 'ethereum', 'cardano',
                'solana', 'polkadot', 'ripple'
            ])

    def test_generate_analysis_summary(self, comparator, sample_score1, sample_score2):
        """Test analysis summary generation."""
        scores = [sample_score1, sample_score2]
        winner = 'bitcoin'

        summary = comparator._generate_analysis_summary(scores, winner)

        assert 'Bitcoin' in summary
        assert '90' in summary
        assert 'A+' in summary
        assert '领先' in summary
        assert '82' in summary
        assert '优势' in summary
        assert '劣势' in summary
        assert '投资建议' in summary

    def test_generate_analysis_summary_with_weaknesses(self, comparator):
        """Test summary with weaknesses."""
        score = ProjectScore(
            coin_id='test',
            coin_name='TestCoin',
            symbol='TEST',
            market_score=2,
            technical_score=2,
            onchain_score=5,
            sentiment_score=4,
            github_score=4,
            social_score=5,
            risk_score=5,
            total_score=70.0,
            rating='B',
            recommendation='test',
            risk_level='medium'
        )

        scores = [score]
        summary = comparator._generate_analysis_summary(scores, 'test')

        assert '市场数据' in summary
        assert '劣势' in summary

    def test_dimensions_defined(self, comparator):
        """Test dimensions are properly defined."""
        assert len(comparator.DIMENSIONS) == 7

        for dim_key, dim_name, weight in comparator.DIMENSIONS:
            assert isinstance(dim_key, str)
            assert isinstance(dim_name, str)
            assert isinstance(weight, int)
            assert weight > 0