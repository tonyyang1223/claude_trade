"""Tests for technical analysis module."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch
from src.analysis.technical import TechnicalAnalyzer
from src.data.models import TechnicalIndicators


class TestRSI:
    """Tests for RSI calculation and scoring."""

    def test_calculate_rsi_normal(self):
        """Test RSI calculation with normal data."""
        # Create sample price data (uptrend)
        prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                           110, 111, 112, 113, 114, 115, 116, 117, 118, 119])
        analyzer = TechnicalAnalyzer()
        rsi = analyzer.calculate_rsi(prices, period=14)
        # Uptrend should have RSI > 50
        assert rsi > 50
        assert 0 <= rsi <= 100

    def test_calculate_rsi_downtrend(self):
        """Test RSI calculation with downtrend."""
        # Create sample price data (downtrend)
        prices = pd.Series([119, 118, 117, 116, 115, 114, 113, 112, 111, 110,
                           109, 108, 107, 106, 105, 104, 103, 102, 101, 100])
        analyzer = TechnicalAnalyzer()
        rsi = analyzer.calculate_rsi(prices, period=14)
        # Downtrend should have RSI < 50
        assert rsi < 50
        assert 0 <= rsi <= 100

    def test_score_rsi_oversold(self):
        """Test RSI scoring for oversold condition."""
        analyzer = TechnicalAnalyzer()
        assert analyzer.score_rsi(25) == 5  # Oversold, buy signal
        assert analyzer.score_rsi(15) == 5

    def test_score_rsi_overbought(self):
        """Test RSI scoring for overbought condition."""
        analyzer = TechnicalAnalyzer()
        assert analyzer.score_rsi(75) == 1  # Overbought, caution
        assert analyzer.score_rsi(85) == 1

    def test_score_rsi_neutral(self):
        """Test RSI scoring for neutral condition."""
        analyzer = TechnicalAnalyzer()
        assert analyzer.score_rsi(50) == 3  # Neutral
        assert analyzer.score_rsi(45) == 3
        assert analyzer.score_rsi(55) == 3


class TestMovingAverage:
    """Tests for moving average calculation and scoring."""

    def test_calculate_ma(self):
        """Test MA calculation."""
        prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        analyzer = TechnicalAnalyzer()
        ma = analyzer.calculate_ma(prices, period=5)
        # MA of last 5: (105+106+107+108+109)/5 = 107
        assert ma == pytest.approx(107.0)

    def test_score_ma_golden_cross(self):
        """Test MA scoring with golden cross (price > MA50 > MA200)."""
        analyzer = TechnicalAnalyzer()
        # Price above both MAs, bullish
        score = analyzer.score_ma(current_price=70000, ma_50=65000, ma_200=58000)
        assert score >= 4

    def test_score_ma_death_cross(self):
        """Test MA scoring with death cross (price < MA50 < MA200)."""
        analyzer = TechnicalAnalyzer()
        # Price below both MAs, bearish
        score = analyzer.score_ma(current_price=50000, ma_50=55000, ma_200=60000)
        assert score <= 2

    def test_score_ma_between(self):
        """Test MA scoring when price between MAs."""
        analyzer = TechnicalAnalyzer()
        # Price between MAs
        score = analyzer.score_ma(current_price=62000, ma_50=65000, ma_200=58000)
        assert 2 <= score <= 4


class TestSupportResistance:
    """Tests for support and resistance identification."""

    def test_identify_support_resistance(self):
        """Test support/resistance identification."""
        # Create price data with clear support and resistance
        data = {
            'high': [105, 110, 108, 115, 112, 118, 116, 120, 118, 122],
            'low': [95, 100, 98, 105, 102, 108, 106, 112, 110, 115],
            'close': [100, 105, 103, 110, 107, 113, 111, 116, 114, 118]
        }
        df = pd.DataFrame(data)
        analyzer = TechnicalAnalyzer()
        support, resistance = analyzer.identify_support_resistance(df, window=3)

        assert isinstance(support, list)
        assert isinstance(resistance, list)
        # Support levels should be lower than resistance
        if support and resistance:
            assert min(support) < max(resistance)

    def test_identify_support_resistance_empty(self):
        """Test with insufficient data."""
        df = pd.DataFrame({'high': [100], 'low': [90], 'close': [95]})
        analyzer = TechnicalAnalyzer()
        support, resistance = analyzer.identify_support_resistance(df, window=3)
        assert support == []
        assert resistance == []


class TestTrendAndFibonacci:
    """Tests for trend determination and Fibonacci levels."""

    def test_determine_trend_uptrend(self):
        """Test uptrend detection."""
        analyzer = TechnicalAnalyzer()
        # Price above both MAs
        trend, signal = analyzer.determine_trend(70000, 65000, 58000)
        assert trend == "up"
        assert signal >= 4

    def test_determine_trend_downtrend(self):
        """Test downtrend detection."""
        analyzer = TechnicalAnalyzer()
        # Price below both MAs
        trend, signal = analyzer.determine_trend(50000, 55000, 60000)
        assert trend == "down"
        assert signal <= 2

    def test_determine_trend_sideways(self):
        """Test sideways detection."""
        analyzer = TechnicalAnalyzer()
        # Price near MAs
        trend, signal = analyzer.determine_trend(65000, 64000, 62000)
        assert trend in ["up", "sideways"]

    def test_calculate_fibonacci(self):
        """Test Fibonacci retracement calculation."""
        analyzer = TechnicalAnalyzer()
        levels = analyzer.calculate_fibonacci(high=70000, low=50000)

        assert "23.6" in levels
        assert "38.2" in levels
        assert "50.0" in levels
        assert "61.8" in levels
        assert "78.6" in levels

        # Verify levels are between high and low
        for level_name, level_value in levels.items():
            assert 50000 <= level_value <= 70000

    def test_fibonacci_values(self):
        """Test Fibonacci level values are correct."""
        analyzer = TechnicalAnalyzer()
        high, low = 70000, 50000
        diff = high - low
        levels = analyzer.calculate_fibonacci(high, low)

        assert levels["50.0"] == pytest.approx(low + diff * 0.5)
        assert levels["38.2"] == pytest.approx(low + diff * 0.382)
        assert levels["61.8"] == pytest.approx(low + diff * 0.618)


class TestVolumeAnalysis:
    """Tests for volume analysis."""

    def test_calculate_volume_ratio(self):
        """Test volume ratio calculation."""
        analyzer = TechnicalAnalyzer()
        ratio = analyzer.calculate_volume_ratio(volume=50000000000, market_cap=1000000000000)
        assert ratio == 0.05

    def test_score_volume_high(self):
        """Test volume scoring with high volume."""
        analyzer = TechnicalAnalyzer()
        # High volume ratio indicates strong interest
        score = analyzer.score_volume(0.15)
        assert score >= 4

    def test_score_volume_low(self):
        """Test volume scoring with low volume."""
        analyzer = TechnicalAnalyzer()
        # Low volume ratio
        score = analyzer.score_volume(0.01)
        assert score <= 2

    def test_score_volume_normal(self):
        """Test volume scoring with normal volume."""
        analyzer = TechnicalAnalyzer()
        score = analyzer.score_volume(0.05)
        assert 2 <= score <= 4


class TestFullAnalysis:
    """Tests for full technical analysis."""

    def test_analyze_with_mock_data(self):
        """Test full analysis with mock OHLCV data."""
        analyzer = TechnicalAnalyzer()

        # Mock the fetch_ohlcv method
        mock_df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='D'),
            'open': [50000 + i * 10 for i in range(200)],
            'high': [50500 + i * 10 for i in range(200)],
            'low': [49500 + i * 10 for i in range(200)],
            'close': [50000 + i * 10 for i in range(200)],
            'volume': [1000000] * 200
        })

        analyzer.fetch_ohlcv = lambda *args, **kwargs: mock_df

        result = analyzer.analyze("BTC/USDT", days=200, market_cap=1000000000000)

        assert isinstance(result, TechnicalIndicators)
        assert 0 <= result.rsi <= 100
        assert 1 <= result.rsi_signal <= 5
        assert result.trend in ["up", "down", "sideways"]
        assert len(result.fibonacci_levels) == 5

    def test_analyze_returns_valid_indicators(self):
        """Test that analyze returns valid TechnicalIndicators."""
        analyzer = TechnicalAnalyzer()

        mock_df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='D'),
            'open': [100] * 200,
            'high': [105] * 200,
            'low': [95] * 200,
            'close': [100] * 200,
            'volume': [1000000] * 200
        })

        analyzer.fetch_ohlcv = lambda *args, **kwargs: mock_df

        result = analyzer.analyze("TEST/USDT", days=200)

        assert result.ma_50 is not None
        assert result.ma_200 is not None
        assert isinstance(result.support_levels, list)
        assert isinstance(result.resistance_levels, list)