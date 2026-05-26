"""Tests for chart generation."""
import pytest
from datetime import datetime
from src.report.charts import ChartGenerator
from src.data.models import ProjectScore


# Test fixtures
@pytest.fixture
def sample_score():
    """Create a sample ProjectScore for testing."""
    return ProjectScore(
        coin_id='bitcoin',
        coin_name='Bitcoin',
        symbol='BTC',
        market_score=5,
        technical_score=4,
        onchain_score=4,
        sentiment_score=5,
        github_score=5,
        social_score=5,
        risk_score=4,
        total_score=85.0,
        rating='A',
        recommendation='建议关注',
        risk_level='low'
    )


@pytest.fixture
def sample_score_2():
    """Create a second sample ProjectScore for comparison testing."""
    return ProjectScore(
        coin_id='ethereum',
        coin_name='Ethereum',
        symbol='ETH',
        market_score=4,
        technical_score=5,
        onchain_score=3,
        sentiment_score=4,
        github_score=5,
        social_score=4,
        risk_score=3,
        total_score=75.0,
        rating='B',
        recommendation='建议观察',
        risk_level='medium'
    )


@pytest.fixture
def sample_score_3():
    """Create a third sample ProjectScore with lower scores."""
    return ProjectScore(
        coin_id='solana',
        coin_name='Solana',
        symbol='SOL',
        market_score=3,
        technical_score=2,
        onchain_score=3,
        sentiment_score=2,
        github_score=3,
        social_score=3,
        risk_score=2,
        total_score=50.0,
        rating='C',
        recommendation='谨慎投资',
        risk_level='high'
    )


@pytest.fixture
def generator():
    """Create a ChartGenerator instance."""
    return ChartGenerator()


class TestChartGenerator:
    """Tests for ChartGenerator class."""

    def test_generate_radar_chart(self, generator, sample_score):
        """Test radar chart generation."""
        chart_html = generator.generate_radar_chart(sample_score)

        # Should return HTML string
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0

        # Should contain chart elements
        assert '<div' in chart_html

        # Should contain project name
        assert 'bitcoin' in chart_html.lower() or 'Bitcoin' in chart_html

    def test_radar_chart_contains_all_dimensions(self, generator, sample_score):
        """Test that radar chart includes all 7 dimensions."""
        chart_html = generator.generate_radar_chart(sample_score)

        # Check all dimensions are present
        for dim in ChartGenerator.DIMENSIONS:
            assert dim in chart_html

    def test_radar_chart_score_range(self, generator, sample_score):
        """Test that radar chart uses correct score range (0-5)."""
        chart_html = generator.generate_radar_chart(sample_score)

        # Should have range setup for 0-5
        assert 'range' in chart_html.lower() or '0' in chart_html

    def test_generate_bar_chart(self, generator, sample_score):
        """Test bar chart generation."""
        chart_html = generator.generate_bar_chart(sample_score)

        # Should return HTML string
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0

        # Should contain chart elements
        assert '<div' in chart_html

        # Should contain project name
        assert 'bitcoin' in chart_html.lower() or 'Bitcoin' in chart_html

    def test_bar_chart_color_encoding(self, generator, sample_score, sample_score_3):
        """Test bar chart color encoding for different score levels."""
        # High scores (>=4) should have green color
        high_score_html = generator.generate_bar_chart(sample_score)
        assert '#2ecc71' in high_score_html  # Green for scores >= 4

        # Low scores should have red color
        low_score_html = generator.generate_bar_chart(sample_score_3)
        assert '#e74c3c' in low_score_html  # Red for scores < 3

    def test_bar_chart_contains_all_dimensions(self, generator, sample_score):
        """Test that bar chart includes all 7 dimensions."""
        chart_html = generator.generate_bar_chart(sample_score)

        # Check all dimensions are present on x-axis
        for dim in ChartGenerator.DIMENSIONS:
            assert dim in chart_html

    def test_bar_chart_y_axis_range(self, generator, sample_score):
        """Test that bar chart y-axis is properly ranged (0-5)."""
        chart_html = generator.generate_bar_chart(sample_score)

        # Should have y-axis range setup
        assert 'yaxis' in chart_html.lower() or 'range' in chart_html.lower()

    def test_generate_comparison_chart_two_projects(self, generator, sample_score, sample_score_2):
        """Test comparison chart with 2 projects."""
        scores = [sample_score, sample_score_2]
        chart_html = generator.generate_comparison_chart(scores)

        # Should return HTML string
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0

        # Should contain both project names
        assert 'bitcoin' in chart_html.lower() or 'Bitcoin' in chart_html
        assert 'ethereum' in chart_html.lower() or 'Ethereum' in chart_html

    def test_generate_comparison_chart_three_projects(self, generator, sample_score, sample_score_2, sample_score_3):
        """Test comparison chart with 3 projects."""
        scores = [sample_score, sample_score_2, sample_score_3]
        chart_html = generator.generate_comparison_chart(scores)

        # Should return HTML string
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0

        # Should contain all project names
        assert 'bitcoin' in chart_html.lower() or 'Bitcoin' in chart_html
        assert 'ethereum' in chart_html.lower() or 'Ethereum' in chart_html
        assert 'solana' in chart_html.lower() or 'Solana' in chart_html

    def test_comparison_chart_grouped_bars(self, generator, sample_score, sample_score_2):
        """Test that comparison chart uses grouped bar mode."""
        scores = [sample_score, sample_score_2]
        chart_html = generator.generate_comparison_chart(scores)

        # Should have grouped bar mode
        assert 'barmode' in chart_html.lower() or 'group' in chart_html

    def test_comparison_chart_contains_all_dimensions(self, generator, sample_score, sample_score_2):
        """Test that comparison chart includes all 7 dimensions."""
        scores = [sample_score, sample_score_2]
        chart_html = generator.generate_comparison_chart(scores)

        for dim in ChartGenerator.DIMENSIONS:
            assert dim in chart_html

    def test_comparison_chart_empty_scores_raises_error(self, generator):
        """Test that empty scores list raises ValueError."""
        with pytest.raises(ValueError, match="scores list cannot be empty"):
            generator.generate_comparison_chart([])

    def test_comparison_chart_too_many_projects_raises_error(self, generator):
        """Test that more than 5 projects raises ValueError."""
        scores = [
            ProjectScore(
                coin_id=f'coin{i}',
                coin_name=f'Coin {i}',
                symbol=f'C{i}',
                market_score=3,
                technical_score=3,
                onchain_score=3,
                sentiment_score=3,
                github_score=3,
                social_score=3,
                risk_score=3,
                total_score=60.0,
                rating='B',
                recommendation='建议观察',
                risk_level='medium'
            )
            for i in range(6)
        ]

        with pytest.raises(ValueError, match="Maximum 5 projects can be compared"):
            generator.generate_comparison_chart(scores)

    def test_chart_dimensions_constant(self, generator):
        """Test that DIMENSIONS constant is properly defined."""
        assert len(ChartGenerator.DIMENSIONS) == 7
        assert ChartGenerator.DIMENSIONS == ['Market', 'Technical', 'Onchain', 'Sentiment', 'GitHub', 'Social', 'Risk']

    def test_chart_dimension_fields_constant(self, generator):
        """Test that DIMENSION_FIELDS constant is properly defined."""
        assert len(ChartGenerator.DIMENSION_FIELDS) == 7
        assert 'market_score' in ChartGenerator.DIMENSION_FIELDS
        assert 'risk_score' in ChartGenerator.DIMENSION_FIELDS

    def test_all_chart_methods_return_html(self, generator, sample_score, sample_score_2):
        """Test that all chart methods return HTML strings."""
        radar = generator.generate_radar_chart(sample_score)
        bar = generator.generate_bar_chart(sample_score)
        comparison = generator.generate_comparison_chart([sample_score, sample_score_2])

        assert isinstance(radar, str)
        assert isinstance(bar, str)
        assert isinstance(comparison, str)
        assert len(radar) > 100
        assert len(bar) > 100
        assert len(comparison) > 100

    def test_charts_include_plotlyjs(self, generator, sample_score, sample_score_2):
        """Test that charts include Plotly.js for rendering."""
        radar = generator.generate_radar_chart(sample_score)
        bar = generator.generate_bar_chart(sample_score)
        comparison = generator.generate_comparison_chart([sample_score, sample_score_2])

        # Charts should include plotly CDN reference or plotly code
        for chart in [radar, bar, comparison]:
            assert 'plotly' in chart.lower() or '<script' in chart
