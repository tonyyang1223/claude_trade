"""Tests for data models."""
import pytest
from datetime import datetime
from src.data.models import CoinData, MarketData


class TestCoinData:
    """Tests for CoinData model."""

    def test_create_coin_data(self):
        """Test creating a CoinData instance."""
        coin = CoinData(
            id="bitcoin",
            symbol="BTC",
            name="Bitcoin",
            current_price=50000.0,
            market_cap=1000000000000.0,
            market_cap_rank=1,
            total_volume=50000000000.0,
            circulating_supply=19000000.0,
            total_supply=21000000.0,
            max_supply=21000000.0,
            price_change_24h=1000.0,
            price_change_percentage_24h=2.0,
            last_updated=datetime(2024, 1, 1, 12, 0, 0)
        )
        assert coin.id == "bitcoin"
        assert coin.symbol == "BTC"
        assert coin.current_price == 50000.0
        assert coin.market_cap_rank == 1

    def test_coin_data_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):
            CoinData()  # Should raise validation error

    def test_coin_data_optional_fields(self):
        """Test optional fields have defaults."""
        coin = CoinData(
            id="test-coin",
            symbol="TEST",
            name="Test Coin",
            current_price=1.0,
            market_cap=1000.0,
            market_cap_rank=100
        )
        assert coin.total_volume is None
        assert coin.max_supply is None


class TestMarketData:
    """Tests for MarketData model."""

    def test_create_market_data(self):
        """Test creating a MarketData instance."""
        coin = CoinData(
            id="bitcoin",
            symbol="BTC",
            name="Bitcoin",
            current_price=50000.0,
            market_cap=1000000000000.0,
            market_cap_rank=1
        )
        market = MarketData(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            total_market_cap=2000000000000.0,
            btc_dominance=50.0,
            eth_dominance=20.0,
            coins=[coin]
        )
        assert market.btc_dominance == 50.0
        assert len(market.coins) == 1

    def test_market_data_default_timestamp(self):
        """Test that timestamp defaults to now."""
        market = MarketData(
            total_market_cap=1000000000000.0,
            btc_dominance=50.0
        )
        assert market.timestamp is not None
