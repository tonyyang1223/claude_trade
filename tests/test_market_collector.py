"""Tests for MarketCollector."""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from src.collector.market_collector import MarketCollector
from src.data.models import CoinData, MarketData


class TestMarketCollector:
    """Tests for MarketCollector class."""

    def test_initialization_with_coingecko(self, tmp_path):
        """Test initializing with CoinGecko client."""
        with patch('src.collector.market_collector.CoinGeckoClient') as mock_client:
            collector = MarketCollector(
                api_source="coingecko",
                cache_dir=tmp_path
            )
            assert collector.api_source == "coingecko"

    def test_collect_market_data(self, tmp_path):
        """Test collecting market data."""
        mock_api = Mock()
        mock_api.get_market_data.return_value = {
            "total_market_cap": 2000000000000.0,
            "btc_dominance": 50.0,
            "eth_dominance": 20.0
        }
        mock_api.get_top_coins.return_value = [
            {
                "id": "bitcoin",
                "symbol": "BTC",
                "name": "Bitcoin",
                "current_price": 50000.0,
                "market_cap": 1000000000000.0,
                "market_cap_rank": 1
            }
        ]

        with patch('src.collector.market_collector.CoinGeckoClient', return_value=mock_api):
            collector = MarketCollector(
                api_source="coingecko",
                cache_dir=tmp_path
            )
            market_data = collector.collect_market_data(top_n=10)

            assert market_data is not None
            assert market_data.btc_dominance == 50.0
            assert len(market_data.coins) == 1

    def test_collect_single_coin(self, tmp_path):
        """Test collecting single coin data."""
        mock_api = Mock()
        mock_api.get_coin_data.return_value = {
            "id": "bitcoin",
            "symbol": "BTC",
            "name": "Bitcoin",
            "current_price": 50000.0,
            "market_cap": 1000000000000.0,
            "market_cap_rank": 1
        }

        with patch('src.collector.market_collector.CoinGeckoClient', return_value=mock_api):
            collector = MarketCollector(
                api_source="coingecko",
                cache_dir=tmp_path
            )
            coin_data = collector.collect_coin_data("bitcoin")

            assert coin_data.id == "bitcoin"
            assert coin_data.symbol == "BTC"

    def test_export_collected_data(self, tmp_path):
        """Test exporting collected data."""
        mock_api = Mock()
        mock_api.get_market_data.return_value = {
            "total_market_cap": 2000000000000.0,
            "btc_dominance": 50.0
        }
        mock_api.get_top_coins.return_value = []

        with patch('src.collector.market_collector.CoinGeckoClient', return_value=mock_api):
            collector = MarketCollector(
                api_source="coingecko",
                cache_dir=tmp_path,
                output_dir=tmp_path
            )
            market_data = collector.collect_market_data()

            json_path = collector.export_data(market_data, format="json")
            csv_path = collector.export_data(market_data, format="csv")

            assert json_path.exists()
            assert csv_path.exists()