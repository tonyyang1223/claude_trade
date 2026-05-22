"""Tests for CoinMarketCap API client."""
import pytest
import responses
from src.api.coinmarketcap import CoinMarketCapClient


class TestCoinMarketCapClient:
    """Tests for CoinMarketCapClient class."""

    def test_client_requires_api_key(self):
        """Test that client requires API key."""
        with pytest.raises(ValueError):
            CoinMarketCapClient()

    def test_client_with_api_key(self):
        """Test client initializes with API key."""
        client = CoinMarketCapClient(api_key="test_key")
        assert client.api_key == "test_key"

    @responses.activate
    def test_get_coin_data(self):
        """Test getting single coin data."""
        mock_response = {
            "data": {
                "1": {
                    "id": 1,
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "quote": {
                        "USD": {
                            "price": 50000.0,
                            "market_cap": 1000000000000.0,
                            "volume_24h": 50000000000.0,
                            "percent_change_24h": 2.0
                        }
                    },
                    "circulating_supply": 19000000,
                    "total_supply": 21000000,
                    "max_supply": 21000000,
                    "cmc_rank": 1
                }
            }
        }

        responses.add(
            responses.GET,
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
            json=mock_response,
            status=200
        )

        client = CoinMarketCapClient(api_key="test_key")
        data = client.get_coin_data("bitcoin")

        assert data["symbol"] == "BTC"

    @responses.activate
    def test_get_market_data(self):
        """Test getting market data."""
        mock_response = {
            "data": {
                "total_market_cap": {"USD": 2000000000000},
                "btc_dominance": 50.0,
                "eth_dominance": 20.0
            }
        }

        responses.add(
            responses.GET,
            "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest",
            json=mock_response,
            status=200
        )

        client = CoinMarketCapClient(api_key="test_key")
        data = client.get_market_data()

        assert data["btc_dominance"] == 50.0

    @responses.activate
    def test_get_top_coins(self):
        """Test getting top coins."""
        mock_response = {
            "data": [
                {
                    "id": 1,
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "cmc_rank": 1,
                    "quote": {
                        "USD": {
                            "price": 50000.0,
                            "market_cap": 1000000000000.0,
                            "volume_24h": 50000000000.0,
                            "percent_change_24h": 2.0
                        }
                    },
                    "circulating_supply": 19000000,
                    "total_supply": 21000000
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
            json=mock_response,
            status=200
        )

        client = CoinMarketCapClient(api_key="test_key")
        coins = client.get_top_coins(limit=1)

        assert len(coins) == 1
        assert coins[0]["symbol"] == "BTC"