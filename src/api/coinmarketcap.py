"""CoinMarketCap API client implementation."""
import requests
from typing import List, Dict, Any, Optional
from src.api.base import BaseAPIClient


class CoinMarketCapClient(BaseAPIClient):
    """Client for CoinMarketCap API.

    Requires API key (free tier: 333 calls/day).

    Attributes:
        api_key: CMC API key (required)
        base_url: API base URL

    Example:
        >>> client = CoinMarketCapClient(api_key="your_key")
        >>> btc_data = client.get_coin_data("bitcoin")
    """

    BASE_URL = "https://pro-api.coinmarketcap.com/v1"

    def __init__(self, api_key: str):
        """Initialize CMC client.

        Args:
            api_key: CoinMarketCap API key (required)

        Raises:
            ValueError: If api_key is not provided
        """
        if not api_key:
            raise ValueError("CoinMarketCap API key is required")

        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-CMC_PRO_API_KEY": api_key,
            "Accept": "application/json"
        })

    def get_coin_data(self, coin_id: str) -> Dict[str, Any]:
        """Get data for a single coin.

        Args:
            coin_id: CMC coin ID or symbol (e.g., 'bitcoin' or 'BTC')

        Returns:
            Dictionary with coin data
        """
        url = f"{self.BASE_URL}/cryptocurrency/quotes/latest"
        params = {"symbol": coin_id.upper()}

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json().get("data", {})

        # Get first coin from response
        coin_data = list(data.values())[0] if data else {}
        quote = coin_data.get("quote", {}).get("USD", {})

        return {
            "id": coin_data.get("id"),
            "symbol": coin_data.get("symbol"),
            "name": coin_data.get("name"),
            "current_price": quote.get("price"),
            "market_cap": quote.get("market_cap"),
            "market_cap_rank": coin_data.get("cmc_rank"),
            "total_volume": quote.get("volume_24h"),
            "circulating_supply": coin_data.get("circulating_supply"),
            "total_supply": coin_data.get("total_supply"),
            "max_supply": coin_data.get("max_supply"),
            "price_change_24h": quote.get("price_change_24h"),
            "price_change_percentage_24h": quote.get("percent_change_24h"),
            "last_updated": quote.get("last_updated")
        }

    def get_market_data(self) -> Dict[str, Any]:
        """Get global market data.

        Returns:
            Dictionary with market data
        """
        url = f"{self.BASE_URL}/global-metrics/quotes/latest"

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        data = response.json().get("data", {})

        return {
            "total_market_cap": data.get("total_market_cap", {}).get("USD"),
            "total_volume": data.get("total_volume_24h", {}).get("USD"),
            "btc_dominance": data.get("btc_dominance"),
            "eth_dominance": data.get("eth_dominance"),
            "active_cryptocurrencies": data.get("active_cryptocurrencies"),
            "markets": data.get("active_market_pairs")
        }

    def get_top_coins(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get top coins by market cap.

        Args:
            limit: Number of coins to retrieve (max 5000)

        Returns:
            List of coin data dictionaries
        """
        url = f"{self.BASE_URL}/cryptocurrency/listings/latest"
        params = {
            "limit": min(limit, 5000),
            "sort": "market_cap",
            "sort_dir": "desc"
        }

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        coins = response.json().get("data", [])

        return [
            {
                "id": coin.get("id"),
                "symbol": coin.get("symbol"),
                "name": coin.get("name"),
                "current_price": coin.get("quote", {}).get("USD", {}).get("price"),
                "market_cap": coin.get("quote", {}).get("USD", {}).get("market_cap"),
                "market_cap_rank": coin.get("cmc_rank"),
                "total_volume": coin.get("quote", {}).get("USD", {}).get("volume_24h"),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "max_supply": coin.get("max_supply"),
                "price_change_24h": coin.get("quote", {}).get("USD", {}).get("price_change_24h"),
                "price_change_percentage_24h": coin.get("quote", {}).get("USD", {}).get("percent_change_24h"),
                "last_updated": coin.get("quote", {}).get("USD", {}).get("last_updated")
            }
            for coin in coins
        ]