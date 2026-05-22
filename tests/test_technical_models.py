"""Tests for TechnicalIndicators model."""
import pytest
from datetime import datetime
from src.data.models import TechnicalIndicators


class TestTechnicalIndicators:
    """Tests for TechnicalIndicators model."""

    def test_create_technical_indicators(self):
        """Test creating TechnicalIndicators instance."""
        indicators = TechnicalIndicators(
            rsi=55.5,
            rsi_signal=3,
            ma_50=65000.0,
            ma_200=58000.0,
            ma_signal=4,
            support_levels=[60000.0, 58000.0],
            resistance_levels=[70000.0, 75000.0],
            trend="up",
            trend_signal=4,
            fibonacci_levels={"38.2": 62000.0, "50.0": 60000.0, "61.8": 58000.0},
            volume_ratio=0.05,
            volume_signal=3,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        assert indicators.rsi == 55.5
        assert indicators.rsi_signal == 3
        assert indicators.trend == "up"
        assert len(indicators.support_levels) == 2

    def test_rsi_signal_range(self):
        """Test RSI signal is in valid range."""
        indicators = TechnicalIndicators(
            rsi=50.0,
            rsi_signal=5,
            ma_50=100.0,
            ma_200=90.0,
            ma_signal=3,
            support_levels=[],
            resistance_levels=[],
            trend="sideways",
            trend_signal=3,
            fibonacci_levels={},
            volume_ratio=0.1,
            volume_signal=3
        )
        assert 1 <= indicators.rsi_signal <= 5

    def test_trend_valid_values(self):
        """Test trend is valid value."""
        for trend in ["up", "down", "sideways"]:
            indicators = TechnicalIndicators(
                rsi=50.0,
                rsi_signal=3,
                ma_50=100.0,
                ma_200=90.0,
                ma_signal=3,
                support_levels=[],
                resistance_levels=[],
                trend=trend,
                trend_signal=3,
                fibonacci_levels={},
                volume_ratio=0.1,
                volume_signal=3
            )
            assert indicators.trend == trend