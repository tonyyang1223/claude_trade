"""Reddit data client using free, no-auth methods.

Complements the existing RedditClient (PRAW-based, requires API key)
with free alternatives that don't require authentication.

Inspired by Agent-Reach (github.com/Panniantong/Agent-Reach):
- Uses Jina Reader API for reading public posts (free)
- Uses old.reddit.com for search (no auth required)

Use this client when PRAW is not configured.
"""
import requests
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.data.cache import DataCache


class RedditFreeClient:
    """Client for Reddit data using free, no-auth methods.

    Example:
        >>> client = RedditFreeClient()
        >>> mentions = client.get_coin_mentions("ALLO")
        >>> print(mentions["total_mentions"])
    """

    JINA_READER = "https://r.jina.ai"
    OLD_REDDIT = "https://old.reddit.com"
    DEFAULT_SUBREDDITS = ["cryptocurrency", "CryptoMarkets", "defi", "altcoin"]

    def __init__(self, cache_dir: Path = Path("data/cache")):
        self.cache = DataCache(cache_dir, expire_hours=6)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; claude_trade/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        })

    def get_subreddit_info(self, subreddit: str) -> Dict[str, Any]:
        """Get subreddit info via Jina Reader."""
        cache_key = f"reddit_free_sub_{subreddit.lower()}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        result = {
            "name": subreddit, "subscribers": None, "active_users": None,
            "description": None, "source": "Jina Reader", "confidence": 0.6,
            "timestamp": datetime.now().isoformat()
        }

        try:
            url = f"{self.JINA_READER}/https://www.reddit.com/r/{subreddit}/about/"
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 200:
                text = resp.text
                result["subscribers"] = self._extract_count(text, ["member", "Member", "subscriber"])
                result["active_users"] = self._extract_count(text, ["online", "Online"])
                result["description"] = self._extract_desc(text)
        except Exception as e:
            print(f"Warning: Jina Reader failed for r/{subreddit}: {e}")

        self.cache.save(cache_key, result)
        return result

    def search_subreddit(self, subreddit: str, query: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Search posts in a subreddit."""
        cache_key = f"reddit_free_search_{subreddit}_{query}_{limit}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        results = []
        try:
            url = f"{self.JINA_READER}/https://old.reddit.com/r/{subreddit}/search/?q={query}&restrict_sr=1&sort=relevance"
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 200:
                results = self._parse_jina_search(resp.text, limit)
        except Exception as e:
            print(f"Warning: Reddit search failed: {e}")

        self.cache.save(cache_key, results)
        return results

    def get_coin_mentions(self, coin_name: str, subreddits: List[str] = None, limit: int = 25) -> Dict[str, Any]:
        """Get mentions of a coin across subreddits."""
        if subreddits is None:
            subreddits = self.DEFAULT_SUBREDDITS

        all_posts = []
        for sub in subreddits:
            posts = self.search_subreddit(sub, coin_name, limit)
            for p in posts:
                p["subreddit"] = sub
            all_posts.extend(posts)

        total = len(all_posts)
        unique_subs = len(set(p.get("subreddit", "") for p in all_posts))
        scores = [p.get("score", 0) for p in all_posts if p.get("score")]
        avg = sum(scores) / len(scores) if scores else 0

        return {
            "coin_name": coin_name,
            "total_mentions": total,
            "unique_subreddits": unique_subs,
            "avg_score": round(avg, 2),
            "subreddits": {s: len([p for p in all_posts if p.get("subreddit") == s]) for s in subreddits},
            "posts": all_posts[:20],
            "source": "Reddit (Free)", "confidence": 0.6,
            "timestamp": datetime.now().isoformat()
        }

    def calculate_reddit_score(self, data: Dict[str, Any]) -> int:
        """Calculate Reddit activity score (1-5)."""
        combined = data.get("total_mentions", 0) + data.get("unique_subreddits", 0) * 10
        if combined >= 100: return 5
        elif combined >= 50: return 4
        elif combined >= 20: return 3
        elif combined >= 5: return 2
        else: return 1

    def _extract_count(self, text: str, keywords: List[str]) -> Optional[int]:
        for kw in keywords:
            for pat in [rf'([\d,]+\.?\d*[KMB]?)\s*{kw}', rf'{kw}[\s:]*([\d,]+\.?\d*[KMB]?)']:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    return self._parse_num(m.group(1))
        return None

    def _parse_num(self, s: str) -> int:
        s = s.replace(',', '').strip()
        try:
            if s.upper().endswith('K'): return int(float(s[:-1]) * 1000)
            elif s.upper().endswith('M'): return int(float(s[:-1]) * 1000000)
            return int(float(s))
        except (ValueError, TypeError):
            return 0

    def _extract_desc(self, text: str) -> Optional[str]:
        for m in ["Description:", "About:", "About Community"]:
            idx = text.find(m)
            if idx >= 0:
                d = text[idx + len(m):idx + len(m) + 300].strip().split('\n')[0].strip()
                if len(d) > 10: return d[:200]
        return None

    def _parse_jina_search(self, text: str, limit: int) -> List[Dict]:
        results = []
        for block in text.split('\n\n')[:limit]:
            block = block.strip()
            if len(block) > 20:
                results.append({"title": block.split('\n')[0][:200], "content": block[:500], "source": "Jina Reader", "confidence": 0.5})
        return results
