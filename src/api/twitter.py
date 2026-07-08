"""Twitter/X data client using free, no-auth methods.

Inspired by Agent-Reach (github.com/Panniantong/Agent-Reach):
- Uses Jina Reader API for reading public tweets (free, no auth)
- Uses Nitter instances as fallback for tweet search
- Cookie-based twitter-cli integration (optional, requires setup)

Free tier: All methods work without API keys.
For full search/timeline access, configure twitter-cli with cookies.
"""
import requests
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.data.cache import DataCache


class TwitterClient:
    """Client for Twitter/X data using free methods.

    Data sources (in priority order):
    1. Jina Reader API - Read any public tweet URL (free, no auth)
    2. Nitter instances - Search tweets (free, no auth)
    3. twitter-cli - Full access with cookie auth (optional)

    Example:
        >>> client = TwitterClient()
        >>> profile = client.get_profile("AlloraNetwork")
        >>> print(profile["followers"])
    """

    JINA_READER = "https://r.jina.ai"
    NITTER_INSTANCES = [
        "https://nitter.privacydev.net",
        "https://nitter.poast.org",
        "https://nitter.cz",
    ]

    def __init__(self, cache_dir: Path = Path("data/cache")):
        """Initialize Twitter client.

        Args:
            cache_dir: Directory for caching data
        """
        self.cache = DataCache(cache_dir, expire_hours=6)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; claude_trade/1.0)",
            "Accept": "text/plain",
        })

    def get_profile(self, username: str) -> Dict[str, Any]:
        """Get Twitter/X profile data for a user.

        Uses Jina Reader to read the public profile page.

        Args:
            username: Twitter username (without @)

        Returns:
            Dictionary with profile data
        """
        cache_key = f"twitter_profile_{username.lower()}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        result = {
            "username": username,
            "name": None,
            "bio": None,
            "followers": None,
            "following": None,
            "tweets_count": None,
            "source": "Jina Reader",
            "confidence": 0.7,
            "timestamp": datetime.now().isoformat()
        }

        # Try Jina Reader on the profile page
        try:
            url = f"{self.JINA_READER}/https://x.com/{username}"
            resp = self.session.get(url, timeout=30)

            if resp.status_code == 200:
                text = resp.text

                result["name"] = self._extract_name(text, username)
                result["bio"] = self._extract_bio(text)
                result["followers"] = self._extract_count(text, ["follower", "Followers"])
                result["following"] = self._extract_count(text, ["following", "Following"])
                result["tweets_count"] = self._extract_count(text, ["post", "Posts"])

                result["source"] = "Jina Reader"
                result["confidence"] = 0.7

        except Exception as e:
            print(f"Warning: Jina Reader failed for @{username}: {e}")

        # Try Nitter as fallback
        if result["followers"] is None:
            result = self._get_profile_nitter(username, result)

        self.cache.save(cache_key, result)
        return result

    def _get_profile_nitter(self, username: str, result: Dict) -> Dict:
        """Try to get profile from Nitter instances."""
        for instance in self.NITTER_INSTANCES:
            try:
                url = f"{instance}/{username}"
                resp = self.session.get(url, timeout=15)

                if resp.status_code == 200:
                    text = resp.text

                    if result["followers"] is None:
                        result["followers"] = self._extract_count(text, ["Followers", "follower"])
                    if result["following"] is None:
                        result["following"] = self._extract_count(text, ["Following", "following"])
                    if result["bio"] is None:
                        result["bio"] = self._extract_bio(text)

                    if result["followers"] is not None:
                        result["source"] = f"Nitter ({instance})"
                        result["confidence"] = 0.6
                        break

            except Exception:
                continue

        return result

    def search_tweets(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for tweets using free methods.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of tweet data dictionaries
        """
        cache_key = f"twitter_search_{query}_{limit}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        results = []

        # Try Nitter search via Jina Reader
        try:
            url = f"{self.JINA_READER}/https://nitter.privacydev.net/search?f=tweets&q={query}"
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 200:
                results = self._parse_jina_tweets(resp.text, limit)

        except Exception:
            pass

        self.cache.save(cache_key, results)
        return results

    def read_tweet(self, tweet_url: str) -> Dict[str, Any]:
        """Read a specific tweet using Jina Reader.

        Args:
            tweet_url: Full tweet URL (https://x.com/user/status/123)

        Returns:
            Dictionary with tweet content
        """
        cache_key = f"twitter_tweet_{tweet_url}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        result = {
            "url": tweet_url,
            "content": None,
            "author": None,
            "likes": None,
            "retweets": None,
            "source": "Jina Reader",
            "confidence": 0.7,
            "timestamp": datetime.now().isoformat()
        }

        try:
            url = f"{self.JINA_READER}/{tweet_url}"
            resp = self.session.get(url, timeout=30)

            if resp.status_code == 200:
                text = resp.text
                result["content"] = text[:2000]
                result["likes"] = self._extract_count(text, ["like", "Like"])
                result["retweets"] = self._extract_count(text, ["repost", "Repost"])

        except Exception as e:
            print(f"Warning: Failed to read tweet: {e}")

        self.cache.save(cache_key, result)
        return result

    def calculate_social_score(self, profile: Dict[str, Any]) -> int:
        """Calculate social score (1-5) from profile data.

        Args:
            profile: Result from get_profile()

        Returns:
            Score from 1 (tiny) to 5 (massive following)
        """
        followers = profile.get("followers")

        if followers is None:
            return 3

        if followers >= 500000:
            return 5
        elif followers >= 100000:
            return 4
        elif followers >= 10000:
            return 3
        elif followers >= 1000:
            return 2
        else:
            return 1

    def _extract_count(self, text: str, keywords: List[str]) -> Optional[int]:
        """Extract a count number from text near keywords."""
        for kw in keywords:
            patterns = [
                rf'([\d,]+\.?\d*[KMB]?)\s*{kw}',
                rf'{kw}[\s:]*([\d,]+\.?\d*[KMB]?)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return self._parse_count_str(match.group(1))
        return None

    def _parse_count_str(self, s: str) -> int:
        """Parse count string like '1.5K', '23,456', '2M'."""
        s = s.replace(',', '').strip()
        try:
            if s.upper().endswith('K'):
                return int(float(s[:-1]) * 1000)
            elif s.upper().endswith('M'):
                return int(float(s[:-1]) * 1000000)
            elif s.upper().endswith('B'):
                return int(float(s[:-1]) * 1000000000)
            return int(float(s))
        except (ValueError, TypeError):
            return 0

    def _extract_name(self, text: str, username: str) -> Optional[str]:
        """Extract display name from profile text."""
        patterns = [
            rf'(@{username})\s*\n?\s*([^\n@]+)',
            rf'([^\n]{2,50})\s*@\s*{username}',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(2 if match.lastindex == 2 else 1).strip()
                if 1 < len(name) < 50:
                    return name
        return None

    def _extract_bio(self, text: str) -> Optional[str]:
        """Extract bio/description from profile text."""
        for marker in ["Bio:", "About:", "Description:"]:
            idx = text.find(marker)
            if idx >= 0:
                bio = text[idx + len(marker):idx + len(marker) + 200].strip()
                bio = bio.split('\n')[0].strip()
                if len(bio) > 10:
                    return bio[:300]
        return None

    def _parse_jina_tweets(self, text: str, limit: int) -> List[Dict]:
        """Parse tweet content from Jina Reader output."""
        tweets = []
        blocks = text.split('---')
        for block in blocks[:limit]:
            block = block.strip()
            if len(block) > 20:
                tweets.append({
                    "content": block[:500],
                    "source": "Jina Reader",
                    "confidence": 0.6
                })
        return tweets
