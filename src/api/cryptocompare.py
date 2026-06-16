"""CryptoCompare API client for social statistics.

CryptoCompare provides comprehensive social statistics including:
- Reddit subscribers, active users
- Twitter followers
- Facebook likes
- GitHub stars, forks, contributors
- Historical social data (up to 90 days)

Free tier: 100,000 calls/month
Requires API key (free registration at https://www.cryptocompare.com)
"""
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.data.cache import DataCache


class CryptoCompareClient:
    """Client for CryptoCompare social statistics API.

    Attributes:
        api_key: Optional API key for higher rate limits
        base_url: API base URL
        cache: DataCache instance for caching responses

    Example:
        >>> client = CryptoCompareClient(api_key="your_key")
        >>> social = client.get_social_stats("bitcoin")
        >>> print(social["reddit"]["subscribers"])
    """

    BASE_URL = "https://min-api.cryptocompare.com/data"

    # Coin ID mapping for popular cryptocurrencies
    COIN_IDS = {
        "bitcoin": 1182,
        "ethereum": 7605,
        "litecoin": 3808,
        "ripple": 5033,
        "cardano": 46436,
        "solana": 891632,
        "polkadot": 204789,
        "dogecoin": 4432,
        "chainlink": 28739,
        "avalanche": 55088,
        "uniswap": 5995,
        "polygon": 11818,
        "stellar": 1482,
        "cosmos": 23884,
        "filecoin": 27987,
        "arweave": 22567,
        "algorand": 5626,
        "tezos": 1998,
        "theta": 30978,
        "vechain": 29344,
        "monero": 3335,
        "eos": 3827,
        "tron": 3717,
        "neo": 3234,
        "iota": 1776,
        "zcash": 2449,
        "dash": 3807,
        "ethereum-classic": 3810,
        "maker": 6800,
        "aave": 10888,
        "compound": 10884,
        "yearn-finance": 10891,
        "sushi": 10892,
        "curve": 10893,
        "balancer": 10894,
        "synthetix": 2586,
        "ren": 2978,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Path = Path("data/cache")
    ):
        """Initialize CryptoCompare client.

        Args:
            api_key: Optional API key (free tier: 100K calls/month)
            cache_dir: Directory for caching data
        """
        import os
        self.api_key = api_key or os.getenv("CRYPTOCOMPARE_API_KEY")
        self.cache = DataCache(cache_dir, expire_hours=4)
        self.session = requests.Session()

        if self.api_key:
            self.session.params.update({"api_key": self.api_key})

    def _fetch_with_cache(
        self,
        url: str,
        cache_key: str,
        params: Dict = None,
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """Fetch data with caching support."""
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if data.get("Err"):
                print(f"Warning: CryptoCompare API error: {data['Err']}")
                return None

            self.cache.save(cache_key, data)
            return data

        except requests.exceptions.RequestException as e:
            print(f"Warning: CryptoCompare API request failed: {e}")
            return None

    def get_coin_id(self, coin_name: str) -> Optional[int]:
        """Get CryptoCompare coin ID from name.

        Args:
            coin_name: Coin name (e.g., 'bitcoin')

        Returns:
            Coin ID or None if not found
        """
        return self.COIN_IDS.get(coin_name.lower())

    def get_social_stats(self, coin_id: int) -> Dict[str, Any]:
        """Get latest social statistics for a coin.

        Args:
            coin_id: CryptoCompare coin ID

        Returns:
            Dictionary with social stats including:
            - reddit: subscribers, active_users, posts_per_hour
            - twitter: followers, tweets_per_day
            - facebook: likes
            - github: stars, forks, contributors, issues
        """
        cache_key = f"cryptocompare_social_{coin_id}"
        url = f"{self.BASE_URL}/social/coin/latest"

        params = {"coinId": coin_id}
        if self.api_key:
            params["api_key"] = self.api_key

        data = self._fetch_with_cache(url, cache_key, params)

        if not data or not data.get("Data"):
            return {}

        return self._parse_social_data(data.get("Data", {}))

    def get_social_history(
        self,
        coin_id: int,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get historical social statistics.

        Args:
            coin_id: CryptoCompare coin ID
            limit: Number of days (max 90)

        Returns:
            List of daily social stats
        """
        cache_key = f"cryptocompare_social_hist_{coin_id}_{limit}"
        url = f"{self.BASE_URL}/social/coin/histo/day"

        params = {"coinId": coin_id, "limit": min(limit, 90)}
        if self.api_key:
            params["api_key"] = self.api_key

        data = self._fetch_with_cache(url, cache_key, params)

        if not data or not data.get("Data"):
            return []

        return [
            self._parse_social_data(item)
            for item in data.get("Data", [])
        ]

    def _parse_social_data(self, raw_data: Dict) -> Dict[str, Any]:
        """Parse raw social data into structured format."""
        result = {
            "timestamp": raw_data.get("time", 0),
            "date": datetime.fromtimestamp(raw_data.get("time", 0)).isoformat() if raw_data.get("time") else None,
        }

        # Reddit data
        reddit = raw_data.get("Reddit", {})
        if reddit:
            result["reddit"] = {
                "subscribers": reddit.get("subscribers", 0),
                "active_users": reddit.get("active_users", 0),
                "posts_per_hour": reddit.get("posts_per_hour", 0),
                "comments_per_hour": reddit.get("comments_per_hour", 0),
                "points_per_hour": reddit.get("points_per_hour", 0),
            }

        # Twitter data
        twitter = raw_data.get("Twitter", {})
        if twitter:
            result["twitter"] = {
                "followers": twitter.get("followers", 0),
                "following": twitter.get("following", 0),
                "lists": twitter.get("lists", 0),
                "statuses": twitter.get("statuses", 0),
                "favourites": twitter.get("favourites", 0),
                "points_per_hour": twitter.get("points_per_hour", 0),
            }

        # Facebook data
        facebook = raw_data.get("Facebook", {})
        if facebook:
            result["facebook"] = {
                "likes": facebook.get("likes", 0),
                "talking_about": facebook.get("talking_about", 0),
            }

        # GitHub data
        github = raw_data.get("CodeRepository", {})
        if github:
            result["github"] = {
                "stars": github.get("stars", 0),
                "forks": github.get("forks", 0),
                "contributors": github.get("contributors", 0),
                "open_issues": github.get("open_issues", 0),
                "closed_issues": github.get("closed_issues", 0),
                "commits": github.get("commits", 0),
                "additions": github.get("additions", 0),
                "deletions": github.get("deletions", 0),
            }

        # Overall engagement score
        result["total_points"] = raw_data.get("Points", 0)

        return result

    def calculate_social_score(self, social_data: Dict[str, Any]) -> int:
        """Calculate social engagement score (1-5).

        Based on engagement metrics across all platforms.

        Args:
            social_data: Social statistics dictionary

        Returns:
            Score from 1 (low engagement) to 5 (high engagement)
        """
        if not social_data:
            return 3  # Default neutral

        total_points = social_data.get("total_points", 0)

        # Reddit engagement
        reddit = social_data.get("reddit", {})
        reddit_score = reddit.get("active_users", 0) + reddit.get("posts_per_hour", 0) * 10

        # Twitter engagement
        twitter = social_data.get("twitter", {})
        twitter_score = twitter.get("followers", 0) / 1000  # Normalize

        # GitHub engagement
        github = social_data.get("github", {})
        github_score = github.get("stars", 0) / 100 + github.get("forks", 0) / 50

        # Combined score
        combined = (reddit_score + twitter_score + github_score + total_points) / 100

        if combined > 50:
            return 5
        elif combined > 30:
            return 4
        elif combined > 10:
            return 3
        elif combined > 5:
            return 2
        else:
            return 1

    def is_available(self) -> bool:
        """Check if API is available (has API key or free tier works)."""
        # Try a simple request to check availability
        try:
            url = f"{self.BASE_URL}/social/coin/latest"
            params = {"coinId": 1182}  # Bitcoin
            if self.api_key:
                params["api_key"] = self.api_key

            response = self.session.get(url, params=params, timeout=10)
            data = response.json()

            return not data.get("Err")

        except Exception:
            return False
