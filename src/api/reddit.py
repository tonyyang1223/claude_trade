"""Reddit API Client for cryptocurrency sentiment analysis.

Uses praw library for Reddit API access.
Target subreddits: CryptoCurrency, bitcoin, ethfinance, solana

Setup:
1. Go to https://www.reddit.com/prefs/apps
2. Create a "script" type app
3. Copy client_id (under app name) and client_secret
4. Set env vars: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
   OR add to config/settings.yaml under social_apis.reddit
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    import praw
    from prawcore.exceptions import PrawcoreException
    HAS_PRAW = True
except ImportError:
    HAS_PRAW = False
    PrawcoreException = Exception

from src.data.cache import DataCache
from src.utils.config_loader import get_reddit_credentials


class RedditClient:
    """Reddit API client for crypto sentiment analysis.

    Target subreddits:
        - r/CryptoCurrency (general crypto discussion)
        - r/bitcoin (Bitcoin focused)
        - r/ethfinance (Ethereum focused)
        - r/solana (Solana focused)

    Metrics collected:
        - mention_count: Number of mentions in 24h
        - mention_growth: Growth rate vs previous period
        - sentiment_score: Sentiment analysis (bullish/bearish)
        - hot_post_score: Engagement score for top posts

    Example:
        >>> client = RedditClient()
        >>> data = client.get_coin_mentions("bitcoin")
        >>> print(data["mention_count"])
    """

    TARGET_SUBREDDITS = ["CryptoCurrency", "bitcoin", "ethfinance", "solana"]

    def __init__(
        self,
        cache_dir: Path = Path("data/cache"),
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: str = "claude_trade:v1.0"
    ):
        """Initialize Reddit client.

        Args:
            cache_dir: Directory for caching data
            client_id: Reddit API client ID (optional, auto-loaded from config)
            client_secret: Reddit API client secret (optional, auto-loaded from config)
            user_agent: Reddit API user agent string
        """
        self.cache = DataCache(cache_dir, expire_hours=4)
        self.user_agent = user_agent

        # Initialize praw if available
        self.reddit = None
        if HAS_PRAW:
            # Use provided credentials, or auto-load from config
            if not client_id or not client_secret:
                creds = get_reddit_credentials()
                client_id = client_id or creds["client_id"]
                client_secret = client_secret or creds["client_secret"]
                user_agent = creds.get("user_agent") or user_agent

            if client_id and client_secret:
                try:
                    self.reddit = praw.Reddit(
                        client_id=client_id,
                        client_secret=client_secret,
                        user_agent=user_agent
                    )
                    print(f"Reddit API initialized successfully")
                except Exception as e:
                    print(f"Warning: Reddit API init failed: {e}")
            else:
                print("Warning: Reddit credentials not found. Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET env vars, or add to config/settings.yaml")

    def is_available(self) -> bool:
        """Check if Reddit API is available."""
        return self.reddit is not None

    def search_mentions(
        self,
        coin_name: str,
        subreddits: List[str] = None,
        time_filter: str = "day",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for coin mentions across subreddits.

        Args:
            coin_name: Coin name to search (e.g., "bitcoin", "ethereum")
            subreddits: List of subreddit names (default: TARGET_SUBREDDITS)
            time_filter: Time filter (day/week/month/year/all)
            limit: Maximum results per subreddit

        Returns:
            List of mention data dictionaries
        """
        if not self.is_available():
            return []

        subreddits = subreddits or self.TARGET_SUBREDDITS
        mentions = []

        # Build search query
        query = self._build_search_query(coin_name)

        for subreddit_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                cache_key = f"reddit_search_{subreddit_name}_{coin_name}_{time_filter}"

                # Check cache
                cached = self.cache.load(cache_key)
                if cached:
                    mentions.extend(cached)
                    continue

                # Search posts
                results = []
                for submission in subreddit.search(query, time_filter=time_filter, limit=limit):
                    results.append(self._extract_submission_data(submission))

                # Cache results
                if results:
                    self.cache.save(cache_key, results)
                    mentions.extend(results)

            except PrawcoreException as e:
                print(f"Warning: Reddit search failed for {subreddit_name}: {e}")
                continue

        return mentions

    def get_hot_posts(
        self,
        subreddit_name: str,
        limit: int = 25,
        coin_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get hot posts from a subreddit.

        Args:
            subreddit_name: Subreddit name
            limit: Maximum posts to fetch
            coin_filter: Optional coin name to filter posts

        Returns:
            List of hot post data
        """
        if not self.is_available():
            return []

        cache_key = f"reddit_hot_{subreddit_name}_{limit}"

        # Check cache
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []

            for submission in subreddit.hot(limit=limit):
                post_data = self._extract_submission_data(submission)

                # Filter by coin if specified
                if coin_filter:
                    if not self._contains_coin_reference(submission, coin_filter):
                        continue

                posts.append(post_data)

            # Cache
            if posts:
                self.cache.save(cache_key, posts)

            return posts

        except PrawcoreException as e:
            print(f"Warning: Failed to get hot posts: {e}")
            return []

    def get_coin_mentions(self, coin_name: str) -> Dict[str, Any]:
        """Get comprehensive mention data for a coin.

        Args:
            coin_name: Coin name (e.g., "bitcoin", "ethereum")

        Returns:
            Dictionary with mention metrics:
                - mention_count: Total mentions in 24h
                - mention_growth: Growth rate vs 7d average
                - sentiment_score: Sentiment score (0-100)
                - hot_post_score: Hot post engagement score
                - subreddits: Breakdown by subreddit
                - confidence: Data confidence
        """
        # Get current mentions
        current_mentions = self.search_mentions(coin_name, time_filter="day")
        historical_mentions = self.search_mentions(coin_name, time_filter="week")

        # Calculate metrics
        mention_count = len(current_mentions)
        historical_count = len(historical_mentions) // 7  # Daily average

        # Growth rate
        if historical_count > 0:
            mention_growth = ((mention_count - historical_count) / historical_count) * 100
        else:
            mention_growth = 0.0

        # Sentiment analysis
        sentiment_score = self._analyze_sentiment(current_mentions)

        # Hot post score
        hot_posts = self.get_hot_posts("CryptoCurrency", limit=50, coin_filter=coin_name)
        hot_post_score = self._calculate_hot_score(hot_posts)

        # Subreddit breakdown
        subreddit_breakdown = {}
        for sub in self.TARGET_SUBREDDITS:
            sub_mentions = [m for m in current_mentions if m.get("subreddit") == sub]
            subreddit_breakdown[sub] = len(sub_mentions)

        # Confidence
        confidence = 0.9 if self.is_available() else 0.1

        return {
            "mention_count": mention_count,
            "mention_growth": mention_growth,
            "sentiment_score": sentiment_score,
            "hot_post_score": hot_post_score,
            "subreddits": subreddit_breakdown,
            "total_engagement": sum(m.get("score", 0) for m in current_mentions),
            "confidence": confidence,
            "source": "Reddit API" if self.is_available() else "Fallback",
            "timestamp": datetime.now().isoformat()
        }

    def _build_search_query(self, coin_name: str) -> str:
        """Build search query for coin mentions."""
        # Common aliases
        aliases = {
            "bitcoin": ["bitcoin", "btc"],
            "ethereum": ["ethereum", "eth", "ether"],
            "solana": ["solana", "sol"],
            "cardano": ["cardano", "ada"],
            "polkadot": ["polkadot", "dot"],
        }

        terms = aliases.get(coin_name.lower(), [coin_name.lower()])
        return " OR ".join(terms)

    def _extract_submission_data(self, submission) -> Dict[str, Any]:
        """Extract relevant data from a submission."""
        return {
            "id": submission.id,
            "title": submission.title,
            "score": submission.score,
            "upvote_ratio": submission.upvote_ratio,
            "num_comments": submission.num_comments,
            "created_utc": datetime.fromtimestamp(submission.created_utc).isoformat(),
            "subreddit": str(submission.subreddit),
            "author": str(submission.author) if submission.author else "[deleted]",
            "url": submission.url,
            "selftext": submission.selftext[:500] if submission.selftext else "",
            "is_hot": submission.score > 100
        }

    def _contains_coin_reference(self, submission, coin_name: str) -> bool:
        """Check if submission contains coin reference."""
        text = f"{submission.title} {submission.selftext}".lower()
        query = self._build_search_query(coin_name)
        terms = query.split(" OR ")

        return any(term in text for term in terms)

    def _analyze_sentiment(self, mentions: List[Dict]) -> float:
        """Analyze sentiment from mentions.

        Simple heuristic-based sentiment analysis:
        - Positive keywords: bullish, buy, moon, gain, rise, good
        - Negative keywords: bearish, sell, dump, crash, lose, bad

        Returns:
            Sentiment score (0-100, 50=neutral)
        """
        if not mentions:
            return 50.0

        positive_keywords = [
            "bullish", "buy", "moon", "gain", "rise", "good", "great",
            "opportunity", "hold", "accumulate", "bull", "positive"
        ]
        negative_keywords = [
            "bearish", "sell", "dump", "crash", "lose", "bad", "terrible",
            "risk", "warning", "bear", "negative", "scam"
        ]

        positive_count = 0
        negative_count = 0

        for mention in mentions:
            text = f"{mention.get('title', '')} {mention.get('selftext', '')}".lower()

            positive_count += sum(1 for kw in positive_keywords if kw in text)
            negative_count += sum(1 for kw in negative_keywords if kw in text)

        # Calculate sentiment
        total = positive_count + negative_count
        if total == 0:
            return 50.0

        sentiment = (positive_count / total) * 100
        return round(sentiment, 2)

    def _calculate_hot_score(self, posts: List[Dict]) -> float:
        """Calculate hot post engagement score.

        Score based on:
        - Post score (upvotes)
        - Comment count
        - Upvote ratio

        Returns:
            Hot score (0-100)
        """
        if not posts:
            return 0.0

        total_score = 0.0
        for post in posts:
            engagement = (
                post.get("score", 0) * 0.4 +
                post.get("num_comments", 0) * 0.3 +
                post.get("upvote_ratio", 0.5) * 100 * 0.3
            )
            total_score += engagement

        avg_score = total_score / len(posts)
        # Normalize to 0-100
        return min(100.0, avg_score / 10)
