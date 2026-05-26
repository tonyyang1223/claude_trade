"""Tests for report generator."""
from datetime import datetime
from pathlib import Path
import tempfile

import pytest

from src.data.models import ProjectScore, ComparisonReport
from src.report.generator import ReportGenerator


@pytest.fixture
def sample_score():
    """Create sample project score."""
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
        recommendation='强烈建议关注，项目综合表现优秀，风险较低',
        risk_level='low'
    )


@pytest.fixture
def sample_score2():
    """Create another sample project score."""
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
        recommendation='建议关注，项目综合表现良好，风险可控',
        risk_level='low'
    )


@pytest.fixture
def sample_comparison_report(sample_score, sample_score2):
    """Create sample comparison report."""
    return ComparisonReport(
        projects=[sample_score, sample_score2],
        comparison_matrix={
            'bitcoin': {'market': 5, 'technical': 4},
            'ethereum': {'market': 4, 'technical': 5}
        },
        winner='bitcoin',
        analysis_summary='Bitcoin 在综合评分上领先，市场数据表现更好',
        created_at=datetime.now()
    )


@pytest.fixture
def generator():
    """Create report generator."""
    return ReportGenerator()


class TestReportGenerator:
    """Tests for ReportGenerator class."""

    def test_initialization(self):
        """Test generator initialization."""
        gen = ReportGenerator()
        assert gen.template_dir.exists()

    def test_initialization_custom_path(self):
        """Test generator with custom template path."""
        custom_path = Path('/tmp/templates')
        gen = ReportGenerator(template_dir=custom_path)
        assert gen.template_dir == custom_path

    def test_generate_html_report(self, generator, sample_score):
        """Test single project report generation."""
        html = generator.generate_html_report(sample_score)

        assert isinstance(html, str)
        assert 'Bitcoin' in html
        assert 'BTC' in html
        assert '90' in html
        assert 'A+' in html
        assert '强烈建议关注' in html
        assert '<!DOCTYPE html>' in html

    def test_generate_html_report_contains_charts(self, generator, sample_score):
        """Test report contains chart placeholders."""
        html = generator.generate_html_report(sample_score)

        # Should contain plotly divs
        assert 'plotly' in html.lower()

    def test_generate_comparison_report(self, generator, sample_comparison_report):
        """Test comparison report generation."""
        html = generator.generate_comparison_report(sample_comparison_report)

        assert isinstance(html, str)
        assert 'Bitcoin' in html
        assert 'Ethereum' in html
        assert 'BTC' in html
        assert 'ETH' in html
        assert '推荐' in html
        assert '<!DOCTYPE html>' in html

    def test_generate_comparison_report_contains_charts(self, generator, sample_comparison_report):
        """Test comparison report contains chart."""
        html = generator.generate_comparison_report(sample_comparison_report)

        # Should contain plotly chart
        assert 'plotly' in html.lower()

    def test_save_report(self, generator, sample_score):
        """Test saving report to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'test_report.html'

            generator.save_report(sample_score, output_path)

            assert output_path.exists()
            content = output_path.read_text(encoding='utf-8')
            assert 'Bitcoin' in content
            assert 'BTC' in content

    def test_save_report_creates_directory(self, generator, sample_score):
        """Test saving report creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'subdir' / 'test_report.html'

            generator.save_report(sample_score, output_path)

            assert output_path.exists()

    def test_save_comparison_report(self, generator, sample_comparison_report):
        """Test saving comparison report to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'comparison_report.html'

            generator.save_comparison_report(sample_comparison_report, output_path)

            assert output_path.exists()
            content = output_path.read_text(encoding='utf-8')
            assert 'Bitcoin' in content
            assert 'Ethereum' in content

    def test_report_with_entry_suggestion(self, generator):
        """Test report with entry suggestion."""
        score = ProjectScore(
            coin_id='cardano',
            coin_name='Cardano',
            symbol='ADA',
            market_score=3,
            technical_score=4,
            onchain_score=3,
            sentiment_score=3,
            github_score=4,
            social_score=3,
            risk_score=3,
            total_score=65.0,
            rating='C',
            recommendation='谨慎观望',
            risk_level='medium',
            entry_suggestion='建议等待技术指标确认趋势后再入场'
        )

        html = generator.generate_html_report(score)

        assert '入场建议' in html
        assert '等待技术指标确认趋势' in html
