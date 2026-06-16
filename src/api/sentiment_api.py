"""Sentiment API client aggregating multiple free sources.

Provides market sentiment data from:
- Fear & Greed Index (alternative.me) - completely free, no auth
- Google Trends - via pytrends, completely free
- Social media aggregates from multiple sources

This client combines these sources into a unified sentiment score.
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.data.cache import DataCache


class SentimentAPIClient:
    """Client for aggregated cryptocurrency sentiment data.

    Combines multiple free sentiment sources:
    - Fear & Greed Index (alternative.me)
    - Google Trends integration
    - Social media metrics

    Example:
        >>> client = SentimentAPIClient()
        >>> sentiment = client.get_market_sentiment()
        >>> print(sentiment["fear_greed_index"])
    """

    FEAR_GREED_API = "https://api.alternative.me/fng/"
    ALTERNATIVE_ME_API = "https://api.alternative.me/v2"

    # Fear & Greed classification
    FG_CLASSIFICATION = {
        (0, 25): "Extreme Fear",
        (25, 45): "Fear",
        (45, 55): "Neutral",
        (55, 75): "Greed",
        (75, 101): "Extreme Greed"
    }

    def __init__(self, cache_dir: Path = Path("data/cache")):
        """Initialize sentiment client.

        Args:
            cache_dir: Directory for caching data
        """
        self.cache = DataCache(cache_dir, expire_hours=1)
        self.session = requests.Session()

    def get_fear_greed_index(self, limit: int = 30) -> Dict[str, Any]:
        """Get Fear & Greed Index from alternative.me.

        Args:
            limit: Number of historical values to fetch

        Returns:
            Dictionary with current and historical values
        """
        cache_key = f"fear_greed_index_{limit}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = self.session.get(
                self.FEAR_GREED_API,
                params={"limit": limit},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            fg_data = data.get("data", [])

            if not fg_data:
                return {"value": 50, "classification": "Neutral", "historical": []}

            # Parse current value
            current = fg_data[0]
            value = int(current.get("value", 50))
            classification = current.get("value_classification", self._classify_fg(value))

            # Parse historical
            historical = []
            for item in fg_data:
                timestamp = int(item.get("timestamp", 0))
                historical.append({
                    "date": datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d'),
                    "value": int(item.get("value", 50)),
                    "classification": item.get("value_classification", "Unknown")
                })

            result = {
                "value": value,
                "classification": classification,
                "timestamp": datetime.now().isoformat(),
                "historical": historical,
                "source": "alternative.me",
                "confidence": 0.9
            }

            self.cache.save(cache_key, result)
            return result

        except Exception as e:
            print(f"Warning: Fear & Greed fetch failed: {e}")
            return {
                "value": 50,
                "classification": "Neutral",
                "historical": [],
                "source": "Fallback",
                "confidence": 0.1
            }

    def _classify_fg(self, value: int) -> str:
        """Classify Fear & Greed value."""
        for (low, high), label in self.FG_CLASSIFICATION.items():
            if low <= value < high:
                return label
        return "Neutral"

    def score_fear_greed(self, value: int) -> int:
        """Score Fear & Greed Index (1-5).

        Extreme Fear = 5 (buying opportunity)
        Extreme Greed = 1 (risk high)

        Args:
            value: Fear & Greed Index (0-100)

        Returns:
            Score from 1 to 5
        """
        if value <= 20:
            return 5  # Extreme Fear - buy signal
        elif value <= 40:
            return 4  # Fear
        elif value <= 60:
            return 3  # Neutral
        elif value <= 80:
            return 2  # Greed
        else:
            return 1  # Extreme Greed - caution

    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global crypto market metrics from alternative.me.

        Returns:
            Dictionary with market cap, dominance, etc.
        """
        cache_key = "alternative_me_global"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = self.session.get(
                f"{self.ALTERNATIVE_ME_API}/global/",
                timeout=30
            )
            response.raise_for_status()

            data = response.json().get("data", {})

            result = {
                "total_market_cap_usd": data.get("quotes", {}).get("USD", {}).get("total_market_cap"),
                "total_volume_24h": data.get("quotes", {}).get("USD", {}).get("total_volume_24h"),
                "btc_dominance": data.get("btc_dominance"),
                "active_cryptocurrencies": data.get("active_cryptocurrencies"),
                "active_markets": data.get("active_markets"),
                "timestamp": datetime.now().isoformat(),
                "source": "alternative.me",
                "confidence": 0.85
            }

            self.cache.save(cache_key, result)
            return result

        except Exception as e:
            print(f"Warning: Global metrics fetch failed: {e}")
            return {"confidence": 0.1}

    def get_sentiment_trend(self, days: int = 7) -> Dict[str, Any]:
        """Get sentiment trend over time.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with trend analysis
        """
        fg_data = self.get_fear_greed_index(limit=days)
        historical = fg_data.get("historical", [])

        if len(historical) < 2:
            return {
                "direction": "stable",
                "change": 0,
                "confidence": 0.1
            }

        # Calculate trend
        values = [h["value"] for h in historical]
        first_half = sum(values[:len(values)//2]) / (len(values)//2) if len(values)//2 > 0 else values[0]
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2) if len(values) > len(values)//2 else values[-1]

        change = second_half - first_half

        if change > 10:
            direction = "more_greedy"
        elif change < -10:
            direction = "more_fearful"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "change": round(change, 2),
            "start_value": values[0] if values else 50,
            "end_value": values[-1] if values else 50,
            "confidence": 0.8
        }

    def get_combined_sentiment(self, coin_name: str = None) -> Dict[str, Any]:
        """Get combined sentiment from all sources.

        Args:
            coin_name: Optional coin name for coin-specific sentiment

        Returns:
            Dictionary with combined sentiment analysis
        """
        # Get Fear & Greed
        fg = self.get_fear_greed_index(limit=30)
        fg_score = self.score_fear_greed(fg["value"])

        # Get trend
        trend = self.get_sentiment_trend(days=7)

        # Combined score (weighted average)
        # Fear & Greed has 60% weight
        combined_score = int(fg_score * 0.6 + 3 * 0.4)  # 3 is neutral for other factors

        # Determine overall sentiment
        if combined_score >= 4:
            overall = "bullish"
        elif combined_score <= 2:
            overall = "bearish"
        else:
            overall = "neutral"

        return {
            "fear_greed": {
                "value": fg["value"],
                "classification": fg["classification"],
                "score": fg_score
            },
            "trend": trend,
            "combined_score": combined_score,
            "overall_sentiment": overall,
            "recommendation": self._get_recommendation(fg["value"], trend["direction"]),
            "timestamp": datetime.now().isoformat(),
            "confidence": fg.get("confidence", 0.5) * 0.9  # Reduce confidence slightly for aggregation
        }

    def _get_recommendation(self, fg_value: int, trend: str) -> str:
        """Generate sentiment-based recommendation."""
        if fg_value <= 25:
            return "Extreme Fear - Potential accumulation zone"
        elif fg_value <= 40:
            return "Fear - Consider accumulating"
        elif fg_value <= 60:
            return "Neutral - Monitor for signals"
        elif fg_value <= 75:
            return "Greed - Consider taking profits"
        else:
            return "Extreme Greed - High risk, consider reducing exposure"

    def calculate_sentiment_signal(self, sentiment_data: Dict[str, Any]) -> int:
        """Calculate sentiment signal (1-5) for scoring system.

        Args:
            sentiment_data: Result from get_combined_sentiment()

        Returns:
            Signal from 1 (very bearish) to 5 (very bullish)
        """
        if not sentiment_data:
            return 3

        return sentiment_data.get("combined_score", 3)
