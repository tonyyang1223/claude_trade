"""CoinGecko API client implementation."""
import requests
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from src.api.base import BaseAPIClient


class CoinGeckoClient(BaseAPIClient):
    """Client for CoinGecko API.

    Free tier: 50 calls/minute
    API key increases rate limit significantly.

    Rate limiting: Enforces minimum 1.2s interval between calls
    to stay under 50 calls/minute limit.

    Attributes:
        api_key: Optional API key for higher rate limits
        base_url: API base URL
        last_call_time: Timestamp of last API call

    Example:
        >>> client = CoinGeckoClient()
        >>> btc_data = client.get_coin_data("bitcoin")
    """

    BASE_URL = "https://api.coingecko.com/api/v3"
    MIN_CALL_INTERVAL = 3.0  # ~20 calls/min, stays under keyless free-tier limit

    def __init__(self, api_key: Optional[str] = None):
        """Initialize CoinGecko client.

        Args:
            api_key: Optional API key for higher rate limits
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.last_call_time = 0

        # Retry on rate-limit / transient errors with exponential backoff so a
        # 429 from the keyless free tier is retried instead of failing the run.
        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            retry = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET"],
            )
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)
        except Exception:
            pass

        if api_key:
            self.session.headers.update({"x-api-key": api_key})

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limit."""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.MIN_CALL_INTERVAL:
            wait_time = self.MIN_CALL_INTERVAL - elapsed
            time.sleep(wait_time)
        self.last_call_time = time.time()

    def get_coin_data(self, coin_id: str) -> Dict[str, Any]:
        """Get detailed data for a single coin.

        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin')

        Returns:
            Dictionary with coin data
        """
        self._wait_for_rate_limit()
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

    def get_coin_research_data(self, coin_id: str) -> Dict[str, Any]:
        """Get extended market data for token research (tokenomics / valuation).

        Complements ``get_coin_data`` with the fields needed by
        :mod:`src.research.token_defi`: fully diluted valuation, ATH and
        7d/30d price changes. Existing clients are unaffected.

        Args:
            coin_id: CoinGecko coin ID (e.g., 'ethena')

        Returns:
            Dictionary with research-grade market data, including:
            - price / market_cap / fdv
            - circulating_supply / total_supply / max_supply
            - ath, ath_change_pct
            - change_24h / change_7d / change_30d
            - categories, last_updated
        """
        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        }

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        market_data = data.get("market_data", {})

        def usd(key: str) -> Optional[float]:
            value = market_data.get(key, {})
            return value.get("usd") if isinstance(value, dict) else None

        return {
            "id": data.get("id"),
            "symbol": (data.get("symbol") or "").upper(),
            "name": data.get("name"),
            "categories": data.get("categories") or [],
            "price": usd("current_price"),
            "market_cap": usd("market_cap"),
            "fdv": usd("fully_diluted_valuation"),
            "circulating_supply": market_data.get("circulating_supply"),
            "total_supply": market_data.get("total_supply"),
            "max_supply": market_data.get("max_supply"),
            "total_volume": usd("total_volume"),
            "ath": usd("ath"),
            "ath_change_pct": usd("ath_change_percentage"),
            "change_24h": market_data.get("price_change_percentage_24h"),
            "change_7d": market_data.get("price_change_percentage_7d"),
            "change_30d": market_data.get("price_change_percentage_30d"),
            "last_updated": data.get("last_updated"),
        }

    def get_market_data(self) -> Dict[str, Any]:
        """Get global market data.

        Returns:
            Dictionary with market data including dominance
        """
        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/global"

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        data = response.json().get("data", {})
        market_cap_percentage = data.get("market_cap_percentage", {})

        return {
            "total_market_cap": data.get("total_market_cap", {}).get("usd"),
            "total_volume": data.get("total_volume", {}).get("usd"),
            "market_cap_change_percentage_24h": data.get("market_cap_change_percentage_24h_usd"),
            "btc_dominance": market_cap_percentage.get("btc"),
            "eth_dominance": market_cap_percentage.get("eth"),
            "market_cap_percentage": market_cap_percentage,
            "active_cryptocurrencies": data.get("active_cryptocurrencies"),
            "markets": data.get("markets")
        }

    def get_coin_community_data(self, coin_id: str) -> Dict[str, Any]:
        """Get community and social data for a coin.

        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin')

        Returns:
            Dictionary with social media metrics
        """
        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "true",
            "developer_data": "false"
        }

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        community = data.get("community_data", {})

        return {
            "twitter_followers": community.get("twitter_followers"),
            "reddit_subscribers": community.get("reddit_subscribers"),
            "telegram_users": community.get("telegram_channel_user_count"),
            "github_forks": community.get("forks"),
            "github_stars": community.get("stars")
        }

    def get_top_coins(self, limit: int = 100,
                      price_change_percentage: str = "24h") -> List[Dict[str, Any]]:
        """Get top coins by market cap.

        Args:
            limit: Number of coins to retrieve (max 250)
            price_change_percentage: Comma-separated periods to request,
                e.g. "1h,24h,7d". Fields are returned as
                price_change_percentage_<p>_in_currency (None if absent).

        Returns:
            List of coin data dictionaries
        """
        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": min(limit, 250),
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": price_change_percentage,
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
                "price_change_percentage_1h": coin.get("price_change_percentage_1h_in_currency"),
                "price_change_percentage_24h_currency": coin.get("price_change_percentage_24h_in_currency"),
                "price_change_percentage_7d": coin.get("price_change_percentage_7d_in_currency"),
                "ath": coin.get("ath"),
                "ath_change_percentage": coin.get("ath_change_percentage"),
                "last_updated": coin.get("last_updated")
            }
            for coin in coins
        ]

    def get_asset_platform(self, coin_id: str) -> Optional[str]:
        """Get asset platform (chain) for a token.

        Args:
            coin_id: CoinGecko coin ID

        Returns:
            Platform ID (e.g., 'ethereum', 'solana') or None
        """
        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "false",
            "community_data": "false",
            "developer_data": "false"
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            platform_id = data.get("asset_platform_id")

            return platform_id if platform_id else None

        except Exception as e:
            print(f"Warning: Failed to get asset platform for {coin_id}: {e}")
            return None

    def search_coins(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search coins by name/symbol to resolve a CoinGecko coin id.

        Used by web research to turn a free-text token query (e.g. "Ethena")
        into the canonical coin id.

        Args:
            query: Search term (name or symbol)
            limit: Max number of results to return

        Returns:
            List of dicts: {"id", "name", "symbol", "thumb"}
        """
        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/search"
        params = {"query": query}

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            coins = response.json().get("coins", [])
            return [
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "symbol": (c.get("symbol") or "").upper(),
                    "thumb": c.get("thumb"),
                }
                for c in coins[:limit]
            ]
        except Exception as e:
            print(f"Warning: CoinGecko search failed for '{query}': {e}")
            return []

    def get_coin_profile(self, coin_id: str) -> Dict[str, Any]:
        """Get web-research-grade profile for a coin (narrative, links, sentiment).

        Complements ``get_coin_data`` / ``get_coin_research_data`` with the fields
        that power the token web-research module: project description, official &
        community links, categories, launch date, community sentiment votes and
        CoinGecko watchlist size. Existing methods are unaffected.

        Args:
            coin_id: CoinGecko coin ID (e.g. 'bitcoin', 'ethena')

        Returns:
            Normalized dict with:
            - id, symbol, name
            - description (project narrative, English)
            - categories (list)
            - genesis_date (launch date, ISO) / watchlist_users
            - sentiment: {up_pct, down_pct}
            - official_links: {website, whitepaper, explorers, forum, github}
            - community_links: {twitter, facebook, telegram, reddit}
            - source, fetched_at
        """
        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "false",
            "community_data": "true",
            "developer_data": "false",
            "sparkline": "false",
        }

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        links = data.get("links", {}) or {}

        def _first(items: Any) -> Optional[str]:
            if isinstance(items, list):
                return next((x for x in items if x), None)
            return items or None

        def _clean_list(items: Any) -> List[str]:
            if not isinstance(items, list):
                return []
            return [x for x in items if x]

        return {
            "id": data.get("id"),
            "symbol": (data.get("symbol") or "").upper(),
            "name": data.get("name"),
            "description": (data.get("description") or {}).get("en"),
            "categories": data.get("categories") or [],
            "genesis_date": data.get("genesis_date"),
            "watchlist_users": data.get("watchlist_portfolio_users"),
            "sentiment": {
                "up_pct": data.get("sentiment_votes_up_percentage"),
                "down_pct": data.get("sentiment_votes_down_percentage"),
            },
            "market_cap_rank": data.get("market_cap_rank"),
            "official_links": {
                "website": _first(links.get("homepage")),
                "whitepaper": links.get("whitepaper") or None,
                "explorers": _clean_list(links.get("blockchain_site")),
                "forum": _first(links.get("official_forum_url")),
                "github": _clean_list(links.get("repos_url", {}).get("github")),
            },
            "community_links": {
                "twitter": links.get("twitter_screen_name") or None,
                "facebook": links.get("facebook_username") or None,
                "telegram": links.get("telegram_channel_identifier") or None,
                "reddit": links.get("subreddit_url") or None,
            },
            "source": "CoinGecko",
            "fetched_at": data.get("last_updated")
            or datetime.now(timezone.utc).isoformat(),
        }