"""CoinGecko API client implementation."""
import requests
from typing import List, Dict, Any, Optional
from src.api.base import BaseAPIClient


class CoinGeckoClient(BaseAPIClient):
    """Client for CoinGecko API.

    Free tier: 50 calls/minute
    API key increases rate limit significantly.

    Attributes:
        api_key: Optional API key for higher rate limits
        base_url: API base URL

    Example:
        >>> client = CoinGeckoClient()
        >>> btc_data = client.get_coin_data("bitcoin")
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize CoinGecko client.

        Args:
            api_key: Optional API key for higher rate limits
        """
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers.update({"x-api-key": api_key})

    def get_coin_data(self, coin_id: str) -> Dict[str, Any]:
        """Get detailed data for a single coin.

        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin')

        Returns:
            Dictionary with coin data
        """
        url = f"{self.BASE_URL}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false"
        }

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        market_data = data.get("market_data", {})

        return {
            "id": data.get("id"),
            "symbol": data.get("symbol", "").upper(),
            "name": data.get("name"),
            "current_price": market_data.get("current_price", {}).get("usd"),
            "market_cap": market_data.get("market_cap", {}).get("usd"),
            "market_cap_rank": data.get("market_cap_rank"),
            "total_volume": market_data.get("total_volume", {}).get("usd"),
            "circulating_supply": market_data.get("circulating_supply"),
            "total_supply": market_data.get("total_supply"),
            "max_supply": market_data.get("max_supply"),
            "price_change_24h": market_data.get("price_change_24h"),
            "price_change_percentage_24h": market_data.get("price_change_percentage_24h"),
            "last_updated": data.get("last_updated")
        }

    def get_market_data(self) -> Dict[str, Any]:
        """Get global market data.

        Returns:
            Dictionary with market data including dominance
        """
        url = f"{self.BASE_URL}/global"

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        data = response.json().get("data", {})
        market_cap_percentage = data.get("market_cap_percentage", {})

        return {
            "total_market_cap": data.get("total_market_cap", {}).get("usd"),
            "total_volume": data.get("total_volume", {}).get("usd"),
            "btc_dominance": market_cap_percentage.get("btc"),
            "eth_dominance": market_cap_percentage.get("eth"),
            "market_cap_percentage": market_cap_percentage,
            "active_cryptocurrencies": data.get("active_cryptocurrencies"),
            "markets": data.get("markets")
        }

    def get_top_coins(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get top coins by market cap.

        Args:
            limit: Number of coins to retrieve (max 250)

        Returns:
            List of coin data dictionaries
        """
        url = f"{self.BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": min(limit, 250),
            "page": 1,
            "sparkline": "false"
        }

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        coins = response.json()

        return [
            {
                "id": coin.get("id"),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name"),
                "current_price": coin.get("current_price"),
                "market_cap": coin.get("market_cap"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "total_volume": coin.get("total_volume"),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "max_supply": coin.get("max_supply"),
                "price_change_24h": coin.get("price_change_24h"),
                "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
                "last_updated": coin.get("last_updated")
            }
            for coin in coins
        ]