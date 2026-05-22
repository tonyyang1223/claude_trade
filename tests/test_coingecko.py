"""Tests for CoinGecko API client."""
import pytest
import responses
from src.api.coingecko import CoinGeckoClient


class TestCoinGeckoClient:
    """Tests for CoinGeckoClient class."""

    def test_client_initialization(self):
        """Test client initializes without API key."""
        client = CoinGeckoClient()
        assert client is not None

    def test_client_with_api_key(self):
        """Test client initializes with API key."""
        client = CoinGeckoClient(api_key="test_key")
        assert client.api_key == "test_key"

    @responses.activate
    def test_get_coin_data(self):
        """Test getting single coin data."""
        mock_response = {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"usd": 50000},
                "market_cap": {"usd": 1000000000000},
                "market_cap_rank": 1,
                "total_volume": {"usd": 50000000000},
                "circulating_supply": 19000000,
                "total_supply": 21000000,
                "max_supply": 21000000,
                "price_change_24h": 1000,
                "price_change_percentage_24h": 2.0
            },
            "last_updated": "2024-01-01T12:00:00Z"
        }

        responses.add(
            responses.GET,
            "https://api.coingecko.com/api/v3/coins/bitcoin",
            json=mock_response,
            status=200
        )

        client = CoinGeckoClient()
        data = client.get_coin_data("bitcoin")

        assert data["id"] == "bitcoin"
        assert data["symbol"] == "BTC"

    @responses.activate
    def test_get_market_data(self):
        """Test getting market data."""
        mock_response = {
            "data": {
                "total_market_cap": {"usd": 2000000000000},
                "market_cap_percentage": {
                    "btc": 50.0,
                    "eth": 20.0
                }
            }
        }

        responses.add(
            responses.GET,
            "https://api.coingecko.com/api/v3/global",
            json=mock_response,
            status=200
        )

        client = CoinGeckoClient()
        data = client.get_market_data()

        assert "total_market_cap" in data
        assert "btc_dominance" in data

    @responses.activate
    def test_get_top_coins(self):
        """Test getting top coins list."""
        mock_response = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 50000,
                "market_cap": 1000000000000,
                "market_cap_rank": 1,
                "total_volume": 50000000000
            }
        ]

        responses.add(
            responses.GET,
            "https://api.coingecko.com/api/v3/coins/markets",
            json=mock_response,
            status=200
        )

        client = CoinGeckoClient()
        coins = client.get_top_coins(limit=1)

        assert len(coins) == 1
        assert coins[0]["id"] == "bitcoin"