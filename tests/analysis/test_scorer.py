"""Tests for the scoring system."""
import pytest
from src.analysis.scorer import Scorer


def test_default_weights():
    """Test default weight configuration."""
    scorer = Scorer()
    assert scorer.weights == {
        'market': 0.20,
        'technical': 0.15,
        'onchain': 0.20,
        'sentiment': 0.10,
        'github': 0.10,
        'social': 0.10,
        'risk': 0.15
    }


def test_weights_sum_to_one():
    """Test that weights sum to 1.0."""
    scorer = Scorer()
    assert sum(scorer.weights.values()) == 1.0


def test_custom_weights():
    """Test custom weight configuration."""
    custom_weights = {
        'market': 0.30,
        'technical': 0.20,
        'onchain': 0.15,
        'sentiment': 0.10,
        'github': 0.05,
        'social': 0.10,
        'risk': 0.10
    }
    scorer = Scorer(custom_weights=custom_weights)
    assert scorer.weights == custom_weights
    assert scorer.weights['market'] == 0.30


def test_invalid_weights_raises_error():
    """Test that invalid weights raise ValueError."""
    invalid_weights = {
        'market': 0.50,
        'technical': 0.50,
        'onchain': 0.50,
        'sentiment': 0.10,
        'github': 0.10,
        'social': 0.10,
        'risk': 0.10
    }
    with pytest.raises(ValueError, match="Weights must sum to 1.0"):
        Scorer(custom_weights=invalid_weights)


def test_weights_do_not_modify_defaults():
    """Test that modifying instance weights doesn't affect defaults."""
    scorer = Scorer()
    scorer.weights['market'] = 0.99
    scorer2 = Scorer()
    assert scorer2.weights['market'] == 0.20


def test_generate_rating():
    """Test rating generation based on total score."""
    scorer = Scorer()

    assert scorer.generate_rating(95) == 'A+'
    assert scorer.generate_rating(85) == 'A'
    assert scorer.generate_rating(75) == 'B'
    assert scorer.generate_rating(65) == 'C'
    assert scorer.generate_rating(55) == 'D'
    assert scorer.generate_rating(45) == 'F'


def test_rating_boundary_values():
    """Test rating at boundary values."""
    scorer = Scorer()

    # A+ boundary (90-100)
    assert scorer.generate_rating(90) == 'A+'
    assert scorer.generate_rating(89.99) == 'A'

    # A boundary (80-89)
    assert scorer.generate_rating(80) == 'A'
    assert scorer.generate_rating(79.99) == 'B'

    # B boundary (70-79)
    assert scorer.generate_rating(70) == 'B'
    assert scorer.generate_rating(69.99) == 'C'

    # C boundary (60-69)
    assert scorer.generate_rating(60) == 'C'
    assert scorer.generate_rating(59.99) == 'D'

    # D boundary (50-59)
    assert scorer.generate_rating(50) == 'D'
    assert scorer.generate_rating(49.99) == 'F'


def test_generate_rating_out_of_range():
    """Test rating generation with out-of-range scores."""
    scorer = Scorer()

    with pytest.raises(ValueError):
        scorer.generate_rating(-1)

    with pytest.raises(ValueError):
        scorer.generate_rating(101)


def test_generate_recommendation():
    """Test recommendation generation based on rating."""
    scorer = Scorer()

    # A+ and A rating
    assert '建议关注' in scorer.generate_recommendation('A+')
    assert '建议关注' in scorer.generate_recommendation('A')

    # B rating
    assert '可考虑' in scorer.generate_recommendation('B')

    # C rating
    assert '谨慎观望' in scorer.generate_recommendation('C')

    # D and F rating
    assert '不推荐' in scorer.generate_recommendation('D')
    assert '不推荐' in scorer.generate_recommendation('F')


def test_generate_recommendation_unknown_rating():
    """Test recommendation generation with unknown rating."""
    scorer = Scorer()
    assert scorer.generate_recommendation('X') == '无法生成建议'


def test_determine_risk_level_invalid_rating():
    """Test risk level determination with invalid rating."""
    scorer = Scorer()

    with pytest.raises(ValueError, match="Invalid rating"):
        scorer.determine_risk_level('X')

    with pytest.raises(ValueError, match="Invalid rating"):
        scorer.determine_risk_level('')

    with pytest.raises(ValueError, match="Invalid rating"):
        scorer.determine_risk_level('G')


def test_determine_risk_level():
    """Test risk level determination based on rating."""
    scorer = Scorer()

    assert scorer.determine_risk_level('A+') == 'low'
    assert scorer.determine_risk_level('A') == 'low'
    assert scorer.determine_risk_level('B') == 'medium'
    assert scorer.determine_risk_level('C') == 'medium'
    assert scorer.determine_risk_level('D') == 'high'
    assert scorer.determine_risk_level('F') == 'high'


def test_calculate_weighted_score():
    """Test weighted score calculation."""
    scorer = Scorer()

    scores = {
        'market': 5,
        'technical': 4,
        'onchain': 4,
        'sentiment': 3,
        'github': 5,
        'social': 4,
        'risk': 4
    }

    # 手动计算: 5*0.2 + 4*0.15 + 4*0.2 + 3*0.1 + 5*0.1 + 4*0.1 + 4*0.15
    # = 1.0 + 0.6 + 0.8 + 0.3 + 0.5 + 0.4 + 0.6 = 4.2
    # 转换为100分制: 4.2 * 20 = 84
    total = scorer.calculate_weighted_score(scores)
    assert abs(total - 84.0) < 0.01


def test_calculate_weighted_score_with_missing_data():
    """Test weighted score with missing dimensions (weight redistribution)."""
    scorer = Scorer()

    # 缺少 sentiment 和 social 数据
    scores = {
        'market': 5,
        'technical': 4,
        'onchain': 4,
        'github': 5,
        'risk': 4
    }

    # 原权重: 0.2 + 0.15 + 0.2 + 0.1 + 0.1 + 0.1 + 0.15 = 1.0
    # 缺失: sentiment(0.1) + social(0.1) = 0.2
    # 剩余权重: 0.8，需要归一化
    # 新权重: market=0.25, technical=0.1875, onchain=0.25, github=0.125, risk=0.1875
    total = scorer.calculate_weighted_score(scores)
    assert total > 0  # 确保计算出结果
    assert total <= 100  # 确保不超过满分


def test_calculate_weighted_score_all_missing():
    """Test weighted score with all dimensions missing."""
    scorer = Scorer()

    # 所有维度都缺失，应该返回0
    scores = {}
    total = scorer.calculate_weighted_score(scores)
    assert total == 0.0


def test_calculate_weighted_score_single_dimension():
    """Test weighted score with only one dimension."""
    scorer = Scorer()

    # 只有一个维度
    scores = {'market': 5}
    total = scorer.calculate_weighted_score(scores)
    # 只剩下market，权重归一化为1.0，5分制转100分制 = 100
    assert abs(total - 100.0) < 0.01


def test_calculate_weighted_score_boundary_values():
    """Test weighted score with boundary values."""
    scorer = Scorer()

    # 所有维度都是最高分
    scores_max = {
        'market': 5,
        'technical': 5,
        'onchain': 5,
        'sentiment': 5,
        'github': 5,
        'social': 5,
        'risk': 5
    }
    total_max = scorer.calculate_weighted_score(scores_max)
    assert abs(total_max - 100.0) < 0.01

    # 所有维度都是最低分
    scores_min = {
        'market': 1,
        'technical': 1,
        'onchain': 1,
        'sentiment': 1,
        'github': 1,
        'social': 1,
        'risk': 1
    }
    total_min = scorer.calculate_weighted_score(scores_min)
    assert abs(total_min - 20.0) < 0.01


from unittest.mock import Mock, patch
from src.data.models import ProjectScore, CoinData, TechnicalIndicators, SentimentData, OnchainData, GithubData


@patch('src.analysis.scorer.Scorer._get_market_data')
@patch('src.analysis.scorer.Scorer._get_technical_indicators')
@patch('src.analysis.scorer.Scorer._get_onchain_data')
@patch('src.analysis.scorer.Scorer._get_sentiment_data')
@patch('src.analysis.scorer.Scorer._get_github_data')
@patch('src.analysis.scorer.Scorer._get_social_data')
@patch('src.analysis.scorer.Scorer._get_risk_data')
def test_score_project(mock_risk, mock_social, mock_github, mock_sentiment,
                       mock_onchain, mock_technical, mock_market):
    """Test complete project scoring."""
    # Create proper mock objects with all attributes using spec
    mock_market_data = Mock(spec=CoinData)
    mock_market_data.market_cap_rank = 1
    mock_market_data.name = 'Bitcoin'
    mock_market_data.symbol = 'btc'
    mock_market.return_value = mock_market_data

    mock_technical_data = Mock(spec=TechnicalIndicators)
    mock_technical_data.rsi_signal = 4
    mock_technical_data.ma_signal = 4
    mock_technical_data.trend_signal = 4
    mock_technical_data.volume_signal = 4
    mock_technical.return_value = mock_technical_data

    mock_onchain_data = Mock(spec=OnchainData)
    mock_onchain_data.onchain_signal = 4
    mock_onchain.return_value = mock_onchain_data

    mock_sentiment_data = Mock(spec=SentimentData)
    mock_sentiment_data.sentiment_signal = 4
    mock_sentiment.return_value = mock_sentiment_data

    mock_github_data = Mock(spec=GithubData)
    mock_github_data.activity_score = 5
    mock_github.return_value = mock_github_data

    mock_social.return_value = Mock(social_score=5)
    mock_risk.return_value = Mock(risk_score=4)

    scorer = Scorer()
    score = scorer.score_project('bitcoin')

    assert isinstance(score, ProjectScore)
    assert score.coin_id == 'bitcoin'
    assert score.total_score > 0
    assert score.rating in ['A+', 'A', 'B', 'C', 'D', 'F']
    assert score.recommendation != ''


# =============================================================================
# Phase 1: Market Data Integration Tests
# =============================================================================

class TestMarketDataIntegration:
    """Tests for market data integration with CoinGecko."""

    @patch('src.analysis.scorer.CoinGeckoClient')
    def test_get_market_data_success(self, mock_client_class):
        """Test successful market data fetch from CoinGecko."""
        mock_client = Mock()
        mock_client.get_coin_data.return_value = {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "current_price": 50000.0,
            "market_cap": 1000000000000.0,
            "market_cap_rank": 1,
            "total_volume": 50000000000.0,
            "circulating_supply": 19000000.0,
            "total_supply": 21000000.0,
            "max_supply": 21000000.0,
            "price_change_24h": 1000.0,
            "price_change_percentage_24h": 2.0,
        }
        mock_client_class.return_value = mock_client

        scorer = Scorer()
        result = scorer._get_market_data("bitcoin")

        assert result is not None
        assert result.id == "bitcoin"
        assert result.name == "Bitcoin"
        assert result.market_cap_rank == 1
        assert result.current_price == 50000.0

    @patch('src.analysis.scorer.CoinGeckoClient')
    def test_get_market_data_api_failure(self, mock_client_class):
        """Test handling of API failure gracefully."""
        mock_client = Mock()
        mock_client.get_coin_data.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        scorer = Scorer()
        result = scorer._get_market_data("bitcoin")

        assert result is None

    @patch('src.analysis.scorer.CoinGeckoClient')
    def test_get_market_data_missing_fields(self, mock_client_class):
        """Test handling of missing optional fields."""
        mock_client = Mock()
        mock_client.get_coin_data.return_value = {
            "id": "newcoin",
            "symbol": "new",
            "name": "New Coin",
            "current_price": 1.0,
            "market_cap": 1000000.0,
            "market_cap_rank": 500,
        }
        mock_client_class.return_value = mock_client

        scorer = Scorer()
        result = scorer._get_market_data("newcoin")

        assert result is not None
        assert result.id == "newcoin"
        assert result.total_volume is None
        assert result.max_supply is None


# =============================================================================
# Phase 2: Technical Indicators Integration Tests
# =============================================================================

class TestTechnicalIndicatorsIntegration:
    """Tests for technical indicators integration."""

    @patch('src.analysis.scorer.TechnicalAnalyzer')
    @patch('src.analysis.scorer.CoinGeckoClient')
    def test_get_technical_indicators_success(self, mock_cg_class, mock_tech_class):
        """Test successful technical indicators fetch."""
        # Mock CoinGecko for market data (needed for volume ratio)
        mock_cg = Mock()
        mock_cg.get_coin_data.return_value = {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "current_price": 50000.0,
            "market_cap": 1000000000000.0,
            "market_cap_rank": 1,
        }
        mock_cg_class.return_value = mock_cg

        # Mock TechnicalAnalyzer
        mock_tech = Mock()
        mock_tech.analyze.return_value = TechnicalIndicators(
            rsi=45.0,
            rsi_signal=3,
            ma_50=48000.0,
            ma_200=45000.0,
            ma_signal=4,
            support_levels=[45000.0, 46000.0],
            resistance_levels=[52000.0, 53000.0],
            trend="up",
            trend_signal=4,
            fibonacci_levels={"0.382": 47000.0, "0.5": 48500.0, "0.618": 50000.0},
            volume_ratio=0.05,
            volume_signal=3
        )
        mock_tech_class.return_value = mock_tech

        scorer = Scorer()
        result = scorer._get_technical_indicators("bitcoin")

        assert result is not None
        assert result.rsi == 45.0
        assert result.rsi_signal == 3
        assert result.trend == "up"
        assert result.trend_signal == 4

    @patch('src.analysis.scorer.TechnicalAnalyzer')
    @patch('src.analysis.scorer.CoinGeckoClient')
    def test_get_technical_indicators_failure(self, mock_cg_class, mock_tech_class):
        """Test handling of technical analysis failure."""
        mock_cg = Mock()
        mock_cg.get_coin_data.return_value = {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}
        mock_cg_class.return_value = mock_cg

        mock_tech = Mock()
        mock_tech.analyze.side_effect = Exception("Exchange error")
        mock_tech_class.return_value = mock_tech

        scorer = Scorer()
        result = scorer._get_technical_indicators("bitcoin")

        assert result is None


# =============================================================================
# Phase 3: Sentiment & Onchain Integration Tests
# =============================================================================

class TestSentimentIntegration:
    """Tests for sentiment data integration."""

    @patch('src.analysis.scorer.SentimentAnalyzer')
    @patch('src.analysis.scorer.CoinGeckoClient')
    def test_get_sentiment_data_success(self, mock_cg_class, mock_sent_class):
        """Test successful sentiment data fetch."""
        mock_cg = Mock()
        mock_cg_class.return_value = mock_cg

        mock_sent = Mock()
        mock_sent.analyze.return_value = SentimentData(
            google_trends_score=75,
            google_trends_change=0.1,
            fear_greed_index=45,
            social_sentiment="neutral",
            sentiment_signal=3
        )
        mock_sent_class.return_value = mock_sent

        scorer = Scorer()
        result = scorer._get_sentiment_data("bitcoin")

        assert result is not None
        assert result.fear_greed_index == 45
        assert result.sentiment_signal == 3

    @patch('src.analysis.scorer.SentimentAnalyzer')
    @patch('src.analysis.scorer.CoinGeckoClient')
    def test_get_sentiment_data_failure(self, mock_cg_class, mock_sent_class):
        """Test handling of sentiment analysis failure."""
        mock_cg = Mock()
        mock_cg_class.return_value = mock_cg

        mock_sent = Mock()
        mock_sent.analyze.side_effect = Exception("API error")
        mock_sent_class.return_value = mock_sent

        scorer = Scorer()
        result = scorer._get_sentiment_data("bitcoin")

        assert result is None


class TestOnchainIntegration:
    """Tests for onchain data integration."""

    @patch('src.analysis.scorer.OnchainAnalyzer')
    @patch('src.analysis.scorer.CoinGeckoClient')
    def test_get_onchain_data_bitcoin(self, mock_cg_class, mock_onchain_class):
        """Test successful onchain data fetch for Bitcoin."""
        mock_cg = Mock()
        mock_cg_class.return_value = mock_cg

        mock_onchain = Mock()
        mock_onchain.analyze.return_value = OnchainData(
            nupl=0.45,
            mvrv=1.8,
            active_addresses=1000000,
            transaction_count=300000,
            onchain_signal=4
        )
        mock_onchain_class.return_value = mock_onchain

        scorer = Scorer()
        result = scorer._get_onchain_data("bitcoin")

        assert result is not None
        assert result.onchain_signal == 4
        assert result.active_addresses == 1000000

    @patch('src.analysis.scorer.OnchainAnalyzer')
    @patch('src.analysis.scorer.CoinGeckoClient')
    def test_get_onchain_data_non_bitcoin(self, mock_cg_class, mock_onchain_class):
        """Test onchain data for non-Bitcoin coins (limited data)."""
        mock_cg = Mock()
        mock_cg_class.return_value = mock_cg

        mock_onchain = Mock()
        # Non-Bitcoin coins return default signal
        mock_onchain.analyze.return_value = OnchainData(onchain_signal=3)
        mock_onchain_class.return_value = mock_onchain

        scorer = Scorer()
        result = scorer._get_onchain_data("ethereum")

        assert result is not None
        assert result.onchain_signal == 3
