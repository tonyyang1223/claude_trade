"""Tests for multi-coin analysis functionality."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from src.data.models import ProjectScore
from src.report.generator import ReportGenerator
from src.report.charts import ChartGenerator
from scripts.report.generate_report import generate_top_n_report, _generate_top_n_summary


@pytest.fixture
def sample_scores():
    """Create sample ProjectScore objects for testing."""
    return [
        ProjectScore(
            coin_id='bitcoin',
            coin_name='Bitcoin',
            symbol='BTC',
            market_score=5,
            technical_score=4,
            onchain_score=5,
            sentiment_score=4,
            github_score=5,
            social_score=5,
            risk_score=5,
            total_score=92.0,
            rating='A+',
            recommendation='强烈建议关注',
            risk_level='low'
        ),
        ProjectScore(
            coin_id='ethereum',
            coin_name='Ethereum',
            symbol='ETH',
            market_score=5,
            technical_score=4,
            onchain_score=4,
            sentiment_score=4,
            github_score=5,
            social_score=4,
            risk_score=4,
            total_score=85.0,
            rating='A',
            recommendation='建议关注',
            risk_level='low'
        ),
        ProjectScore(
            coin_id='solana',
            coin_name='Solana',
            symbol='SOL',
            market_score=4,
            technical_score=3,
            onchain_score=4,
            sentiment_score=4,
            github_score=4,
            social_score=4,
            risk_score=3,
            total_score=72.0,
            rating='B',
            recommendation='可考虑投资',
            risk_level='medium'
        ),
        ProjectScore(
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
            total_score=62.0,
            rating='C',
            recommendation='谨慎观望',
            risk_level='medium'
        ),
        ProjectScore(
            coin_id='dogecoin',
            coin_name='Dogecoin',
            symbol='DOGE',
            market_score=3,
            technical_score=2,
            onchain_score=2,
            sentiment_score=3,
            github_score=2,
            social_score=5,
            risk_score=2,
            total_score=48.0,
            rating='D',
            recommendation='暂不推荐',
            risk_level='high'
        )
    ]


@pytest.fixture
def mock_top_coins():
    """Create mock top coins data."""
    return [
        {'id': 'bitcoin', 'name': 'Bitcoin', 'symbol': 'BTC', 'market_cap_rank': 1},
        {'id': 'ethereum', 'name': 'Ethereum', 'symbol': 'ETH', 'market_cap_rank': 2},
        {'id': 'solana', 'name': 'Solana', 'symbol': 'SOL', 'market_cap_rank': 3},
        {'id': 'cardano', 'name': 'Cardano', 'symbol': 'ADA', 'market_cap_rank': 4},
        {'id': 'dogecoin', 'name': 'Dogecoin', 'symbol': 'DOGE', 'market_cap_rank': 5},
    ]


class TestChartGenerator:
    """Test ChartGenerator heatmap functionality."""

    def test_generate_heatmap_basic(self, sample_scores):
        """Test basic heatmap generation."""
        generator = ChartGenerator()
        heatmap_html = generator.generate_heatmap(sample_scores)

        assert isinstance(heatmap_html, str)
        assert 'plotly' in heatmap_html.lower()
        assert 'Bitcoin' in heatmap_html
        assert 'Ethereum' in heatmap_html

    def test_generate_heatmap_empty_scores(self):
        """Test heatmap with empty scores raises error."""
        generator = ChartGenerator()
        with pytest.raises(ValueError, match="cannot be empty"):
            generator.generate_heatmap([])

    def test_generate_heatmap_contains_all_dimensions(self, sample_scores):
        """Test heatmap includes all scoring dimensions."""
        generator = ChartGenerator()
        heatmap_html = generator.generate_heatmap(sample_scores[:1])

        dimensions = ['Market', 'Technical', 'Onchain', 'Sentiment', 'GitHub', 'Social', 'Risk']
        for dim in dimensions:
            assert dim in heatmap_html


class TestReportGenerator:
    """Test ReportGenerator Top N functionality."""

    def test_generate_top_n_report_html(self, sample_scores, tmp_path):
        """Test HTML generation for Top N report."""
        generator = ReportGenerator()
        summary = "Test summary"
        output_file = tmp_path / "test_report.html"

        generator.save_top_n_report(sample_scores, summary, output_file)

        assert output_file.exists()
        content = output_file.read_text(encoding='utf-8')
        assert '<!DOCTYPE html>' in content
        assert 'Bitcoin' in content
        assert 'Test summary' in content

    def test_generate_top_n_report_creates_directory(self, sample_scores, tmp_path):
        """Test that report generation creates output directory."""
        generator = ReportGenerator()
        summary = "Test summary"
        output_file = tmp_path / "nested" / "dir" / "report.html"

        generator.save_top_n_report(sample_scores, summary, output_file)

        assert output_file.exists()
        assert output_file.parent.is_dir()


class TestGenerateTopNReport:
    """Test generate_top_n_report function."""

    @patch('scripts.report.generate_report.CoinGeckoClient')
    @patch('scripts.report.generate_report.Scorer')
    @patch('scripts.report.generate_report.ReportGenerator')
    def test_generate_top_n_report_success(
        self, mock_generator_class, mock_scorer_class, mock_coingecko_class,
        sample_scores, mock_top_coins, tmp_path
    ):
        """Test successful Top N report generation."""
        # Setup mocks
        mock_coingecko = Mock()
        mock_coingecko.get_top_coins.return_value = mock_top_coins
        mock_coingecko_class.return_value = mock_coingecko

        mock_scorer = Mock()
        mock_scorer.score_project.side_effect = lambda coin_id: next(
            (s for s in sample_scores if s.coin_id == coin_id), sample_scores[0]
        )
        mock_scorer_class.return_value = mock_scorer

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        # Run with small N for testing
        output_file = tmp_path / "test_top5.html"
        generate_top_n_report(
            top_n=5,
            output_path=str(output_file),
            scorer=mock_scorer,
            generator=mock_generator,
            coingecko=mock_coingecko
        )

        # Verify calls
        mock_coingecko.get_top_coins.assert_called_once_with(limit=5)
        assert mock_scorer.score_project.call_count == 5
        mock_generator.save_top_n_report.assert_called_once()

    @patch('scripts.report.generate_report.CoinGeckoClient')
    @patch('scripts.report.generate_report.Scorer')
    @patch('scripts.report.generate_report.ReportGenerator')
    def test_generate_top_n_report_with_failures(
        self, mock_generator_class, mock_scorer_class, mock_coingecko_class,
        sample_scores, mock_top_coins, tmp_path
    ):
        """Test Top N report with some coins failing analysis."""
        # Setup mocks
        mock_coingecko = Mock()
        mock_coingecko.get_top_coins.return_value = mock_top_coins
        mock_coingecko_class.return_value = mock_coingecko

        mock_scorer = Mock()
        call_count = [0]

        def score_side_effect(coin_id):
            call_count[0] += 1
            # Fail on some coins
            if coin_id in ['cardano', 'dogecoin']:
                raise Exception(f"Failed to analyze {coin_id}")
            return next(
                (s for s in sample_scores if s.coin_id == coin_id), sample_scores[0]
            )

        mock_scorer.score_project.side_effect = score_side_effect
        mock_scorer_class.return_value = mock_scorer

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        output_file = tmp_path / "test_top5_failures.html"
        generate_top_n_report(
            top_n=5,
            output_path=str(output_file),
            scorer=mock_scorer,
            generator=mock_generator,
            coingecko=mock_coingecko
        )

        # Should still generate report with successful coins
        mock_generator.save_top_n_report.assert_called_once()
        # Check that only 3 scores were saved (5 - 2 failures)
        saved_args = mock_generator.save_top_n_report.call_args
        saved_scores = saved_args[0][0]
        assert len(saved_scores) == 3


class TestGenerateTopNSummary:
    """Test _generate_top_n_summary function."""

    def test_generate_summary_basic(self, sample_scores):
        """Test basic summary generation."""
        summary = _generate_top_n_summary(sample_scores)

        assert 'Bitcoin' in summary
        assert '92.0' in summary  # Top score
        assert 'A+' in summary  # Top rating
        assert '高评级币种' in summary or '评分分布' in summary

    def test_generate_summary_empty_scores(self):
        """Test summary with empty scores."""
        summary = _generate_top_n_summary([])
        assert summary == "无分析数据"

    def test_generate_summary_includes_risk_distribution(self, sample_scores):
        """Test summary includes risk distribution."""
        summary = _generate_top_n_summary(sample_scores)

        assert '风险分布' in summary
        assert '低风险' in summary
        assert '中风险' in summary
        assert '高风险' in summary

    def test_generate_summary_includes_rating_distribution(self, sample_scores):
        """Test summary includes rating distribution."""
        summary = _generate_top_n_summary(sample_scores)

        assert '评级分布' in summary
        assert 'A+' in summary
        assert 'B' in summary

    def test_generate_summary_includes_average_score(self, sample_scores):
        """Test summary includes average score."""
        summary = _generate_top_n_summary(sample_scores)

        assert '平均分' in summary
        # Calculate expected average
        expected_avg = sum(s.total_score for s in sample_scores) / len(sample_scores)
        assert f'{expected_avg:.1f}' in summary


class TestTopNReportIntegration:
    """Integration tests for Top N report functionality."""

    def test_full_report_structure(self, sample_scores, tmp_path):
        """Test that generated report has all required sections."""
        generator = ReportGenerator()
        summary = _generate_top_n_summary(sample_scores)
        output_file = tmp_path / "full_report.html"

        generator.save_top_n_report(sample_scores, summary, output_file)

        content = output_file.read_text(encoding='utf-8')

        # Check for required sections
        assert 'Top 5' in content or '综合评分报告' in content
        assert '综合排名表' in content
        assert '各维度得分热力图' in content
        assert '推荐列表' in content
        assert '分析总结' in content

        # Check for table structure
        assert '<table' in content
        assert '<thead>' in content
        assert '<tbody>' in content

        # Check for heatmap
        assert 'plotly' in content.lower()

    def test_report_handles_unicode(self, sample_scores, tmp_path):
        """Test that report handles Chinese characters correctly."""
        generator = ReportGenerator()
        summary = "测试中文摘要：强烈建议关注"
        output_file = tmp_path / "unicode_report.html"

        generator.save_top_n_report(sample_scores, summary, output_file)

        content = output_file.read_text(encoding='utf-8')

        # Check that Chinese characters are properly encoded
        assert '测试中文摘要' in content
        assert '强烈建议关注' in content
        # Check template Chinese text
        assert '综合排名表' in content
        assert '推荐列表' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
