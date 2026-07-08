"""Community data client using Agent-Reach powered free sources.

Provides community & social data from multiple platforms:
- Jina Reader: Read any public webpage (free, no auth)
- V2EX: Tech community hot topics (free, no auth)
- Xueqiu (雪球): Financial community stocks & discussions (free, no auth)
- Bilibili search: Video search (free, no auth)
- RSS: Any RSS/Atom feed (free, no auth)
- CoinDesk / Cointelegraph: Crypto news via Jina Reader (free, no auth)

Requires: agent-reach (pip install git+https://github.com/Panniantong/Agent-Reach.git)
Optional: twitter-cli (for full Twitter access), rdt-cli (for full Reddit access)
"""
import json
import re
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.data.cache import DataCache


class CommunityClient:
    """Client for community & social data from Agent-Reach sources.

    Example:
        >>> client = CommunityClient()
        >>> news = client.get_crypto_news()
        >>> hot = client.get_v2ex_hot()
        >>> xueqiu = client.get_xueqiu_hot("crypto")
    """

    JINA_READER = "https://r.jina.ai"
    V2EX_API = "https://www.v2ex.com/api"
    XUEQIU_API = "https://xueqiu.com"
    BILIBILI_API = "https://api.bilibili.com"

    CRYPTO_NEWS_SITES = {
        "coindesk": "https://www.coindesk.com/",
        "cointelegraph": "https://cointelegraph.com/",
        "decrypt": "https://decrypt.co/",
        "theblock": "https://www.theblock.co/",
    }

    CRYPTO_RSS_FEEDS = {
        "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "cointelegraph": "https://cointelegraph.com/rss",
        "decrypt": "https://decrypt.co/feed",
    }

    def __init__(self, cache_dir: Path = Path("data/cache")):
        self.cache = DataCache(cache_dir, expire_hours=4)
        self.session = __import__("requests").Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; claude_trade/1.0)",
            "Accept": "text/plain",
        })

    # ── Jina Reader (通用网页读取) ──

    def read_url(self, url: str) -> Dict[str, Any]:
        """Read any public webpage via Jina Reader."""
        cache_key = f"jina_{hash(url)}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        result = {"url": url, "content": None, "title": None,
                  "source": "Jina Reader", "confidence": 0.7,
                  "timestamp": datetime.now().isoformat()}

        try:
            resp = self.session.get(f"{self.JINA_READER}/{url}", timeout=30)
            if resp.status_code == 200:
                text = resp.text
                result["title"] = self._extract_title(text)
                result["content"] = text[:5000]
        except Exception as e:
            result["error"] = str(e)

        self.cache.save(cache_key, result)
        return result

    # ── Crypto News (Jina Reader) ──

    def get_crypto_news(self, source: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get crypto news headlines from major outlets.

        Args:
            source: Specific source key (e.g. "coindesk") or None for all
            limit: Max articles per source
        """
        cache_key = f"crypto_news_{source or 'all'}_{limit}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        sources = {source: self.CRYPTO_NEWS_SITES[source]} if source else self.CRYPTO_NEWS_SITES
        articles = []

        for name, url in sources.items():
            try:
                resp = self.session.get(f"{self.JINA_READER}/{url}", timeout=30)
                if resp.status_code == 200:
                    parsed = self._parse_news_page(resp.text, name, limit)
                    articles.extend(parsed)
            except Exception:
                continue

        self.cache.save(cache_key, articles)
        return articles

    # ── RSS Feeds ──

    def get_rss_feed(self, feed_key: str = None) -> List[Dict[str, Any]]:
        """Read crypto RSS feeds.

        Args:
            feed_key: Specific feed key or None for all
        """
        cache_key = f"rss_{feed_key or 'all'}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        feeds = {feed_key: self.CRYPTO_RSS_FEEDS[feed_key]} if feed_key else self.CRYPTO_RSS_FEEDS
        entries = []

        try:
            import feedparser
        except ImportError:
            return entries

        for name, url in feeds.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:20]:
                    entries.append({
                        "title": getattr(entry, "title", ""),
                        "link": getattr(entry, "link", ""),
                        "summary": getattr(entry, "summary", "")[:500],
                        "published": getattr(entry, "published", ""),
                        "source": name,
                        "confidence": 0.8,
                    })
            except Exception:
                continue

        self.cache.save(cache_key, entries)
        return entries

    # ── V2EX ──

    def get_v2ex_hot(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get V2EX hot topics."""
        cache_key = f"v2ex_hot_{limit}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        topics = []
        try:
            resp = self.session.get(f"{self.V2EX_API}/topics/hot.json", timeout=15)
            if resp.status_code == 200:
                for t in resp.json()[:limit]:
                    topics.append({
                        "id": t.get("id"),
                        "title": t.get("title", ""),
                        "content": (t.get("content") or "")[:500],
                        "node": t.get("node", {}).get("name", ""),
                        "replies": t.get("replies", 0),
                        "member": t.get("member", {}).get("username", ""),
                        "created": t.get("created"),
                        "url": t.get("url", ""),
                        "source": "V2EX",
                        "confidence": 0.9,
                    })
        except Exception:
            pass

        self.cache.save(cache_key, topics)
        return topics

    def get_v2ex_node(self, node_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get topics from a V2EX node."""
        cache_key = f"v2ex_node_{node_name}_{limit}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        topics = []
        try:
            resp = self.session.get(
                f"{self.V2EX_API}/topics/show.json?node_name={node_name}",
                timeout=15,
            )
            if resp.status_code == 200:
                for t in resp.json()[:limit]:
                    topics.append({
                        "id": t.get("id"),
                        "title": t.get("title", ""),
                        "replies": t.get("replies", 0),
                        "member": t.get("member", {}).get("username", ""),
                        "created": t.get("created"),
                        "url": f"https://www.v2ex.com/t/{t.get('id')}",
                        "source": "V2EX",
                        "confidence": 0.9,
                    })
        except Exception:
            pass

        self.cache.save(cache_key, topics)
        return topics

    # ── Xueqiu (雪球) ──

    def get_xueqiu_hot(self, category: str = "crypto", limit: int = 20) -> List[Dict[str, Any]]:
        """Get Xueqiu hot stocks/posts via Jina Reader (bypasses WAF).

        Args:
            category: "crypto" for crypto-related, "all" for general
            limit: Max items
        """
        cache_key = f"xueqiu_hot_{category}_{limit}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        posts = []

        # Method 1: Jina Reader (bypasses WAF)
        try:
            resp = self.session.get(
                f"{self.JINA_READER}/https://xueqiu.com/hq",
                timeout=30,
            )
            if resp.status_code == 200:
                text = resp.text
                # Parse stock mentions from the rendered page
                stock_pattern = re.compile(r'([A-Z]{2}\d{6})\s*.*?([一-鿿]{2,10})')
                for m in stock_pattern.finditer(text[:10000]):
                    posts.append({
                        "id": None,
                        "title": f"{m.group(2)} ({m.group(1)})",
                        "text": "",
                        "symbol": m.group(1),
                        "source": "Xueqiu (Jina)",
                        "confidence": 0.6,
                    })
        except Exception:
            pass

        # Method 2: Direct API (requires session cookie, may fail due to WAF)
        if not posts:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                    "Referer": "https://xueqiu.com/",
                }
                # First get session cookie
                self.session.get(f"{self.XUEQIU_API}/", headers=headers, timeout=10)
                resp = self.session.get(
                    f"{self.XUEQIU_API}/statuses/hot/listV2.json?since_id=-1&max_id=-1&size={limit}",
                    headers=headers, timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    for item in items[:limit]:
                        post = item.get("original_status") or item.get("retweeted_status") or item
                        text = post.get("text", "")
                        title = post.get("title", "") or self._strip_html(text)[:100]
                        posts.append({
                            "id": post.get("id"),
                            "title": title,
                            "text": self._strip_html(text)[:500],
                            "user": post.get("user", {}).get("screen_name", ""),
                            "retweet_count": post.get("retweet_count", 0),
                            "reply_count": post.get("reply_count", 0),
                            "like_count": post.get("like_count", 0),
                            "target": post.get("target"),
                            "source": "Xueqiu",
                            "confidence": 0.8,
                        })
            except Exception:
                pass

        # Filter for crypto if requested
        if category == "crypto":
            crypto_kw = {"btc", "eth", "bitcoin", "ethereum", "crypto", "defi",
                         "token", "blockchain", "web3", "sol", "solana", "bnb"}
            posts = [p for p in posts
                     if crypto_kw & set(re.findall(r'\b\w+\b', p.get("title", "").lower()))
                     or crypto_kw & set(re.findall(r'\b\w+\b', p.get("text", "").lower()))]

        self.cache.save(cache_key, posts)
        return posts

    def get_xueqiu_stock(self, symbol: str) -> Dict[str, Any]:
        """Get stock/coin quote from Xueqiu.

        Args:
            symbol: Xueqiu symbol (e.g. "SZ000001")
        """
        cache_key = f"xueqiu_stock_{symbol}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        result = {"symbol": symbol, "name": None, "price": None,
                  "change_pct": None, "volume": None,
                  "source": "Xueqiu", "confidence": 0.8,
                  "timestamp": datetime.now().isoformat()}

        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        try:
            resp = self.session.get(
                f"{self.XUEQIU_API}/v5/stock/quote.json?symbol={symbol}&extend=detail",
                headers=headers, timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {}).get("quote", {})
                result["name"] = data.get("name")
                result["price"] = data.get("current")
                result["change_pct"] = data.get("percent")
                result["volume"] = data.get("volume")
        except Exception:
            pass

        self.cache.save(cache_key, result)
        return result

    # ── Bilibili Search ──

    def search_bilibili(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Bilibili videos via Jina Reader (bypasses API restrictions).

        Args:
            query: Search keyword
            limit: Max results
        """
        cache_key = f"bili_search_{query}_{limit}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        results = []

        # Method 1: Jina Reader on search page (bypasses API key requirement)
        try:
            search_url = f"https://search.bilibili.com/all?keyword={query}"
            resp = self.session.get(f"{self.JINA_READER}/{search_url}", timeout=30)
            if resp.status_code == 200:
                text = resp.text
                # Parse video titles from search results
                title_blocks = re.findall(r'(?:Title|标题)[：:]\s*(.+?)(?:\n|$)', text)
                for i, title in enumerate(title_blocks[:limit]):
                    results.append({
                        "bvid": None,
                        "title": title.strip()[:200],
                        "description": "",
                        "author": None,
                        "play": None,
                        "source": "Bilibili (Jina)",
                        "confidence": 0.6,
                    })
        except Exception:
            pass

        # Method 2: Direct API (may fail due to anti-scraping)
        if not results:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                    "Referer": "https://www.bilibili.com",
                }
                resp = self.session.get(
                    f"{self.BILIBILI_API}/x/web-interface/search/type",
                    params={"keyword": query, "search_type": "video", "page_size": limit},
                    headers=headers, timeout=15,
                )
                if resp.status_code == 200:
                    items = resp.json().get("data", {}).get("result", [])
                    for v in items[:limit]:
                        results.append({
                            "bvid": v.get("bvid"),
                            "title": self._strip_html(v.get("title", "")),
                            "description": v.get("description", "")[:300],
                            "author": v.get("author", ""),
                            "play": v.get("play", 0),
                            "danmaku": v.get("video_review", 0),
                            "duration": v.get("duration", ""),
                            "pubdate": v.get("pubdate"),
                            "url": f"https://www.bilibili.com/video/{v.get('bvid', '')}",
                            "source": "Bilibili",
                            "confidence": 0.8,
                        })
            except Exception:
                pass

        self.cache.save(cache_key, results)
        return results

    # ── YouTube Subtitles (yt-dlp) ──

    def get_youtube_subtitles(self, url: str, lang: str = "en") -> Dict[str, Any]:
        """Extract YouTube video subtitles.

        Args:
            url: YouTube video URL
            lang: Subtitle language code
        """
        cache_key = f"yt_sub_{hash(url)}_{lang}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        result = {"url": url, "subtitles": None, "title": None,
                  "source": "yt-dlp", "confidence": 0.9,
                  "timestamp": datetime.now().isoformat()}

        try:
            cmd = ["yt-dlp", "--write-sub", "--sub-lang", lang,
                   "--skip-download", "--print-json", "-q", url]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0 and proc.stdout:
                meta = json.loads(proc.stdout)
                result["title"] = meta.get("title")
                result["duration"] = meta.get("duration")
        except Exception as e:
            result["error"] = str(e)

        self.cache.save(cache_key, result)
        return result

    # ── Twitter (via twitter-cli, optional auth) ──

    def search_twitter(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Twitter/X via twitter-cli (requires cookie auth).

        Falls back to Jina Reader + Nitter if no auth.
        """
        cache_key = f"twitter_cli_search_{query}_{limit}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        results = []
        try:
            cmd = ["twitter", "search", query, "--json", "-n", str(limit)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                tweets = data if isinstance(data, list) else data.get("tweets", [])
                for t in tweets[:limit]:
                    results.append({
                        "id": t.get("id"),
                        "text": t.get("text", "")[:500],
                        "author": t.get("author", {}).get("screen_name", ""),
                        "likes": t.get("favorite_count", 0),
                        "retweets": t.get("retweet_count", 0),
                        "created_at": t.get("created_at", ""),
                        "source": "twitter-cli",
                        "confidence": 0.9,
                    })
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass

        if not results:
            try:
                resp = self.session.get(
                    f"{self.JINA_READER}/https://nitter.privacydev.net/search?f=tweets&q={query}",
                    timeout=30,
                )
                if resp.status_code == 200:
                    results = self._parse_jina_tweets(resp.text, limit)
            except Exception:
                pass

        self.cache.save(cache_key, results)
        return results

    # ── Reddit (via rdt-cli, optional auth) ──

    def search_reddit(self, query: str, subreddit: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Reddit via rdt-cli (requires cookie auth)."""
        cache_key = f"rdt_search_{subreddit or 'all'}_{query}_{limit}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        results = []
        try:
            cmd = ["rdt", "search", query, "--json", "-n", str(limit)]
            if subreddit:
                cmd.extend(["--subreddit", subreddit])
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                posts = data if isinstance(data, list) else data.get("posts", [])
                for p in posts[:limit]:
                    results.append({
                        "id": p.get("id"),
                        "title": p.get("title", ""),
                        "content": (p.get("selftext") or "")[:500],
                        "subreddit": p.get("subreddit", ""),
                        "score": p.get("score", 0),
                        "comments": p.get("num_comments", 0),
                        "author": p.get("author", ""),
                        "url": p.get("url", ""),
                        "source": "rdt-cli",
                        "confidence": 0.9,
                    })
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass

        self.cache.save(cache_key, results)
        return results

    # ── Aggregated Community Score ──

    def get_community_score(self, coin_name: str) -> Dict[str, Any]:
        """Get aggregated community presence score for a coin.

        Checks multiple platforms for mentions and activity.

        Args:
            coin_name: Coin name/symbol to search
        """
        cache_key = f"community_score_{coin_name.lower()}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        breakdown = {}

        # V2EX mentions (free)
        v2ex = self.get_v2ex_hot()
        v2ex_mentions = [t for t in v2ex
                         if coin_name.lower() in t.get("title", "").lower()
                         or coin_name.lower() in t.get("content", "").lower()]
        breakdown["v2ex"] = {"mentions": len(v2ex_mentions), "source": "V2EX"}

        # Bilibili videos (free)
        bili = self.search_bilibili(coin_name)
        breakdown["bilibili"] = {"video_count": len(bili), "source": "Bilibili"}

        # Crypto news mentions (free)
        news = self.get_crypto_news()
        news_mentions = [a for a in news
                         if coin_name.lower() in a.get("title", "").lower()]
        breakdown["news"] = {"mentions": len(news_mentions), "source": "Crypto News"}

        # Twitter (optional auth)
        tweets = self.search_twitter(coin_name)
        breakdown["twitter"] = {"tweets": len(tweets), "source": "Twitter"}

        # Reddit (optional auth)
        reddit = self.search_reddit(coin_name)
        breakdown["reddit"] = {"posts": len(reddit), "source": "Reddit"}

        # Calculate overall score (1-5)
        total_signals = sum(
            v.get("mentions", 0) + v.get("video_count", 0) + v.get("tweets", 0) + v.get("posts", 0)
            for v in breakdown.values()
        )
        if total_signals >= 50:
            score = 5
        elif total_signals >= 20:
            score = 4
        elif total_signals >= 10:
            score = 3
        elif total_signals >= 3:
            score = 2
        else:
            score = 1

        result = {
            "coin": coin_name,
            "community_score": score,
            "total_signals": total_signals,
            "breakdown": breakdown,
            "source": "CommunityClient",
            "timestamp": datetime.now().isoformat(),
        }

        self.cache.save(cache_key, result)
        return result

    # ── Helpers ──

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove HTML tags from text."""
        return re.sub(r'<[^>]+>', '', text).strip()

    @staticmethod
    def _extract_title(text: str) -> Optional[str]:
        """Extract title from Jina Reader output."""
        for line in text.split('\n')[:5]:
            if line.startswith('Title:'):
                return line.replace('Title:', '').strip()
        return None

    def _parse_news_page(self, text: str, source: str, limit: int) -> List[Dict]:
        """Parse news headlines from Jina Reader output."""
        articles = []
        blocks = re.split(r'\n{2,}', text)
        for block in blocks[:limit * 3]:
            block = block.strip()
            if len(block) > 50 and len(block) < 2000:
                title = block.split('\n')[0][:200]
                articles.append({
                    "title": title,
                    "content": block[:500],
                    "source": source,
                    "confidence": 0.7,
                })
        return articles[:limit]

    def _parse_jina_tweets(self, text: str, limit: int) -> List[Dict]:
        """Parse tweet content from Jina Reader output."""
        tweets = []
        for block in text.split('---')[:limit]:
            block = block.strip()
            if len(block) > 20:
                tweets.append({
                    "content": block[:500],
                    "source": "Jina Reader (Nitter)",
                    "confidence": 0.6,
                })
        return tweets
