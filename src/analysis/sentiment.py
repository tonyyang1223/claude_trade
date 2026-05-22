"""Sentiment analysis module."""
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from src.data.models import SentimentData
from src.data.cache import DataCache


class SentimentAnalyzer:
    """Analyzes market sentiment from multiple sources.

    Uses free APIs:
    - alternative.me Fear & Greed Index
    - Google Trends (via pytrends, optional)

    Attributes:
        cache: DataCache for caching data

    Example:
        >>> analyzer = SentimentAnalyzer()
        >>> sentiment = analyzer.analyze("bitcoin")
    """

    FEAR_GREED_API = "https://api.alternative.me/fng/"

    def __init__(self, cache_dir: Path = Path("data/cache")):
        """Initialize sentiment analyzer.

        Args:
            cache_dir: Directory for caching data
        """
        self.cache = DataCache(cache_dir, expire_hours=1)

    def fetch_fear_greed_index(self) -> Dict[str, Any]:
        """Fetch Fear & Greed Index from alternative.me.

        Returns:
            Dictionary with index data
        """
        cache_key = "fear_greed_index"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        response = requests.get(self.FEAR_GREED_API, params={"limit": 2}, timeout=30)
        response.raise_for_status()

        data = response.json()
        self.cache.save(cache_key, data)

        return data

    def fetch_google_trends(self, keyword: str) -> Dict[str, Any]:
        """Fetch Google Trends data (simplified, without pytrends).

        Note: Full Google Trends requires pytrends library.
        This is a placeholder that returns mock data.

        Args:
            keyword: Search keyword

        Returns:
            Dictionary with trends data
        """
        # Placeholder - in production would use pytrends
        # pytrends = TrendReq()
        # pytrends.build_payload([keyword])
        # data = pytrends.interest_over_time()

        # Return default values for now
        return {
            "score": 50,  # Default neutral score
            "change": 0.0  # No change
        }

    def score_fear_greed(self, index: int) -> int:
        """Score Fear & Greed Index.

        Scoring rules:
        - 0-25: Extreme Fear -> 5 (buy opportunity)
        - 25-45: Fear -> 4
        - 45-55: Neutral -> 3
        - 55-75: Greed -> 2
        - 75-100: Extreme Greed -> 1 (risk high)

        Args:
            index: Fear & Greed Index value

        Returns:
            Score (1-5)
        """
        if index <= 25:
            return 5
        elif index <= 45:
            return 4
        elif index <= 55:
            return 3
        elif index <= 75:
            return 2
        else:
            return 1

    def determine_social_sentiment(self, fear_greed: int, trends_score: int) -> str:
        """Determine overall social sentiment.

        Args:
            fear_greed: Fear & Greed Index
            trends_score: Google Trends score

        Returns:
            Sentiment string (bullish/bearish/neutral)
        """
        # Combine metrics for overall sentiment
        combined = (fear_greed + trends_score) / 2

        if combined > 60:
            return "greedy"
        elif combined < 40:
            return "fearful"
        else:
            return "neutral"

    def score_sentiment(self, fear_greed: int, trends_score: int) -> int:
        """Score overall sentiment.

        Args:
            fear_greed: Fear & Greed Index
            trends_score: Google Trends score

        Returns:
            Sentiment signal (1-5)
        """
        # Use Fear & Greed as primary indicator
        return self.score_fear_greed(fear_greed)

    def analyze(self, coin_name: str = "bitcoin") -> SentimentData:
        """Perform full sentiment analysis.

        Args:
            coin_name: Coin name for trends analysis

        Returns:
            SentimentData instance
        """
        # Fetch Fear & Greed Index
        fg_data = self.fetch_fear_greed_index()
        fg_value = int(fg_data.get("data", [{}])[0].get("value", 50))

        # Fetch Google Trends (placeholder)
        trends_data = self.fetch_google_trends(coin_name)
        trends_score = trends_data.get("score", 50)
        trends_change = trends_data.get("change", 0.0)

        # Determine sentiment
        social_sentiment = self.determine_social_sentiment(fg_value, trends_score)
        sentiment_signal = self.score_sentiment(fg_value, trends_score)

        return SentimentData(
            google_trends_score=trends_score,
            google_trends_change=trends_change,
            fear_greed_index=fg_value,
            social_sentiment=social_sentiment,
            sentiment_signal=sentiment_signal
        )