"""Social sentiment API client using free sources (no API key required).

Primary data source: socialtickers.com (free, no auth)
- Reddit mentions from multiple subreddits
- 4chan /biz, StockTwits activity
- News aggregation
- Signal scores (0-100)

Secondary data source: alternative.me Fear & Greed Index (free)

Alternative to CryptoCompare social stats API (which now requires paid key).
"""
import requests
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.data.cache import DataCache


class SocialSentimentClient:
    """Client for free social sentiment APIs.

    Uses socialtickers.com as primary source (free, no API key).
    Provides social mentions, sentiment signals, and news aggregation.

    Example:
        >>> client = SocialSentimentClient()
        >>> btc = client.get_asset_social("BTC")
        >>> print(btc["mentions"])  # Reddit/StockTwits mentions
        >>> print(btc["signal"])    # 0-100 sentiment signal
    """

    # Primary: socialtickers (free, no auth)
    SOCIALTICKERS_URL = "https://socialtickers.com/api/v1"

    # Secondary: alternative.me Fear & Greed (free)
    FEAR_GREED_URL = "https://api.alternative.me/fng"

    def __init__(
        self,
        cache_dir: Path = Path("data/cache"),
        timeout: int = 30,
    ):
        """Initialize social sentiment client.

        Args:
            cache_dir: Directory for caching responses
            timeout: Request timeout in seconds
        """
        self.cache = DataCache(cache_dir, expire_hours=1)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "claude_trade/1.0 (social-sentiment)",
            "Accept": "application/json",
        })

    def _get(
        self,
        url: str,
        params: Dict = None,
        cache_key: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch data with caching."""
        if cache_key:
            cached = self.cache.load(cache_key)
            if cached:
                return cached

        try:
            response = self.session.get(url, params=params or {}, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if cache_key:
                self.cache.save(cache_key, data)
            return data

        except requests.exceptions.RequestException as e:
            print(f"Warning: Social sentiment API request failed: {e}")
            return None

    # ── socialtickers endpoints ──

    def get_leaderboard(
        self,
        sort: str = "trending",
        window: str = "24h",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get crypto social leaderboard.

        Args:
            sort: Sort method (trending, active, heating, signal, mcap)
            window: Time window (1h, 24h, 7d)
            limit: Max results

        Returns:
            List of coins with social metrics:
            - mentions: Reddit/StockTwits mention count
            - signal: 0-100 sentiment score
            - upvotes: Reddit upvotes
            - news: related news items
            - priceChg: 24h price change
        """
        cache_key = f"leaderboard_{sort}_{window}"
        data = self._get(
            f"{self.SOCIALTICKERS_URL}/leaderboard",
            params={"class": "crypto", "sort": sort, "win": window},
            cache_key=cache_key,
        )

        if not data:
            return []

        results = data.get("results", [])
        return results[:limit]

    def get_asset_social(
        self,
        ticker: str,
    ) -> Dict[str, Any]:
        """Get social metrics for a single asset.

        Args:
            ticker: Asset ticker (BTC, ETH, SOL, etc.)

        Returns:
            Dictionary with:
            - mentions: Total social mentions
            - upvotes: Reddit upvotes
            - signal: Sentiment signal (0-100)
            - price: Current price
            - change24: 24h price change
            - news: Recent news items
            - history: Mention history (time series)
        """
        cache_key = f"asset_social_{ticker.upper()}"
        return self._get(
            f"{self.SOCIALTICKERS_URL}/asset/{ticker.upper()}",
            cache_key=cache_key,
        ) or {}

    # ── Fear & Greed Index ──

    def get_fear_greed_index(self) -> Dict[str, Any]:
        """Get Crypto Fear & Greed Index.

        Returns:
            Dictionary with:
            - value: 0-100 (0=Extreme Fear, 100=Extreme Greed)
            - classification: Text label
            - timestamp: Unix timestamp
        """
        cache_key = "fear_greed"
        data = self._get(self.FEAR_GREED_URL, cache_key=cache_key)

        if not data or not data.get("data"):
            return {}

        item = data["data"][0]
        return {
            "value": int(item.get("value", 0)),
            "classification": item.get("value_classification", "Unknown"),
            "timestamp": item.get("timestamp"),
        }

    # ── CryptoCompare replacement interface ──

    def get_coin_social_stats(
        self,
        coin_id: str,
    ) -> Dict[str, Any]:
        """Get social stats for a coin (CryptoCompare replacement).

        Mirrors CryptoCompare's get_social_stats() interface.

        Args:
            coin_id: Coin ID (e.g., 'bitcoin', 'ethereum')

        Returns:
            Dictionary with reddit, twitter-equivalent metrics
        """
        ticker = self._coin_to_ticker(coin_id)
        data = self.get_asset_social(ticker)

        if not data:
            return {}

        # Transform to CryptoCompare-like structure
        result = {
            "coin": coin_id,
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "overall": {
                "mentions": data.get("mentions", 0),
                "upvotes": data.get("upvotes", 0),
                "signal": data.get("signal", 50),
                "buzz": data.get("buzz", 0),  # Change in mentions
                "intensity": data.get("intensity", 0),  # Mentions per hour
            },
        }

        # News items
        news = data.get("news", {})
        if news.get("items"):
            result["news"] = [
                {
                    "title": item.get("t", ""),
                    "source": item.get("src", ""),
                    "sentiment": item.get("lean", "neutral"),
                }
                for item in news.get("items", [])[:5]
            ]

        # Reddit-style metrics (from socialtickers Reddit data)
        result["reddit"] = {
            "subscribers": data.get("mentions", 0) * 100,  # Rough estimate
            "active_users": data.get("mentions", 0) // 10,
            "posts_per_hour": data.get("intensity", 0),
            "upvotes": data.get("upvotes", 0),
        }

        # Price context
        result["price"] = {
            "current": data.get("price", 0),
            "change_24h_pct": data.get("change24", 0),
        }

        # History trend
        history = data.get("history", [])
        if history:
            recent = history[-10:]  # Last 10 data points
            result["trend"] = {
                "direction": "up" if recent[-1][1] > recent[0][1] else "down",
                "mention_history": [[h[0], h[1]] for h in recent],
            }

        return result

    def calculate_social_score(
        self,
        social_data: Dict[str, Any],
    ) -> int:
        """Calculate social engagement score (1-5).

        Mirrors CryptoCompare's calculate_social_score() interface.

        Args:
            social_data: Social statistics dictionary

        Returns:
            Score from 1 (low engagement) to 5 (high engagement)
        """
        if not social_data:
            return 3

        overall = social_data.get("overall", {})
        signal = overall.get("signal", 50)
        mentions = overall.get("mentions", 0)
        upvotes = overall.get("upvotes", 0)

        # Combine signal strength and volume
        signal_weight = (signal - 50) / 25  # -2 to +2
        volume_score = mentions / 50 + upvotes / 200

        combined = abs(signal_weight) + volume_score

        if combined > 3:
            return 5
        elif combined > 2:
            return 4
        elif combined > 1:
            return 3
        elif combined > 0.5:
            return 2
        else:
            return 1

    def is_available(self) -> bool:
        """Check if primary API is available."""
        try:
            response = self.session.get(
                f"{self.SOCIALTICKERS_URL}/leaderboard?class=crypto&sort=trending",
                timeout=10,
            )
            return response.status_code == 200
        except Exception:
            return False

    # ── Helpers ──

    def _coin_to_ticker(self, coin_id: str) -> str:
        """Convert CoinGecko ID to ticker symbol.

        Args:
            coin_id: CoinGecko-style ID (e.g., 'bitcoin', 'ethereum')

        Returns:
            Ticker symbol (e.g., 'BTC', 'ETH')
        """
        mappings = {
            "bitcoin": "BTC",
            "ethereum": "ETH",
            "solana": "SOL",
            "ripple": "XRP",
            "cardano": "ADA",
            "dogecoin": "DOGE",
            "polkadot": "DOT",
            "polygon": "MATIC",
            "chainlink": "LINK",
            "uniswap": "UNI",
            "binancecoin": "BNB",
            "tron": "TRX",
            "litecoin": "LTC",
            "avalanche-2": "AVAX",
            "cosmos": "ATOM",
            "fantom": "FTM",
            "near": "NEAR",
            "algorand": "ALGO",
            "vechain": "VET",
            "hedera-hashgraph": "HBAR",
            "filecoin": "FIL",
            "aptos": "APT",
            "arbitrum": "ARB",
            "optimism": "OP",
            "stellar": "XLM",
            "aave": "AAVE",
            "maker": "MKR",
            "the-graph": "GRT",
            "render-token": "RNDR",
            "pepe": "PEPE",
            "shiba-inu": "SHIB",
            "usd-coin": "USDC",
            "tether": "USDT",
            "usdd": "USDD",
            "ethena-usde": "USDE",
            "ondo-finance": "ONDO",
            "hyperliquid": "HYPE",
            "sui": "SUI",
            "sei": "SEI",
            "world-liberty-financial": "WLFI",
        }
        return mappings.get(coin_id.lower(), coin_id.upper()[:4])