"""Google Trends client for cryptocurrency search interest analysis.

Uses pytrends library to fetch Google Trends data for crypto keywords.
Completely free with no API key required.

Provides:
- Search interest over time (weekly/monthly)
- Related queries analysis
- Regional interest breakdown
- Trending topics comparison
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import pandas as pd

try:
    from pytrends.request import TrendReq
    HAS_PYTRENDS = True
except ImportError:
    HAS_PYTRENDS = False
    TrendReq = None

from src.data.cache import DataCache


class GoogleTrendsClient:
    """Client for Google Trends cryptocurrency data.

    Uses pytrends to fetch search interest metrics for crypto keywords.

    Attributes:
        cache: DataCache instance for caching responses
        pytrends: TrendReq instance

    Example:
        >>> client = GoogleTrendsClient()
        >>> trends = client.get_search_trends("bitcoin", days=30)
        >>> print(trends["current_interest"])
    """

    # Common crypto keyword mappings
    CRYPTO_KEYWORDS = {
        "bitcoin": ["bitcoin", "btc"],
        "ethereum": ["ethereum", "eth"],
        "solana": ["solana", "sol"],
        "cardano": ["cardano", "ada"],
        "ripple": ["ripple", "xrp"],
        "polkadot": ["polkadot", "dot"],
        "dogecoin": ["dogecoin", "doge"],
        "chainlink": ["chainlink", "link"],
        "litecoin": ["litecoin", "ltc"],
        "avalanche": ["avalanche", "avax"],
        "polygon": ["polygon", "matic"],
        "uniswap": ["uniswap", "uni"],
        "stellar": ["stellar", "xlm"],
        "cosmos": ["cosmos", "atom"],
        "allora": ["allora network", "allo crypto"],
        "bittensor": ["bittensor", "tao crypto"],
        "render": ["render network", "rndr"],
    }

    def __init__(self, cache_dir: Path = Path("data/cache")):
        """Initialize Google Trends client.

        Args:
            cache_dir: Directory for caching data
        """
        self.cache = DataCache(cache_dir, expire_hours=12)
        self.pytrends = None

        if HAS_PYTRENDS:
            try:
                self.pytrends = TrendReq(hl='en-US', tz=360)
            except Exception as e:
                print(f"Warning: Failed to initialize pytrends: {e}")

    def is_available(self) -> bool:
        """Check if Google Trends is available."""
        return self.pytrends is not None

    def get_keywords(self, coin_name: str) -> List[str]:
        """Get search keywords for a coin.

        Args:
            coin_name: Coin name (e.g., 'bitcoin')

        Returns:
            List of search keywords
        """
        return self.CRYPTO_KEYWORDS.get(coin_name.lower(), [coin_name.lower()])

    def get_search_trends(
        self,
        coin_name: str,
        days: int = 90,
        compare_with: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get search interest trends for a cryptocurrency.

        Args:
            coin_name: Coin name (e.g., 'bitcoin')
            days: Number of days to analyze (default 90)
            compare_with: Other coins to compare (e.g., ['ethereum'])

        Returns:
            Dictionary with:
            - current_interest: Latest search interest (0-100)
            - interest_change: Change vs previous period
            - trend_direction: 'up', 'down', or 'stable'
            - historical_data: List of (date, value) tuples
            - peak_interest: Peak value and date
        """
        if not self.is_available():
            return self._empty_result(coin_name)

        # Build keywords
        keywords = self.get_keywords(coin_name)[:1]  # Use primary keyword

        if compare_with:
            for coin in compare_with[:4]:  # Max 5 keywords total
                keywords.extend(self.get_keywords(coin)[:1])

        cache_key = f"google_trends_{'_'.join(keywords)}_{days}"

        # Check cache
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            # Build payload
            timeframe = f'today {days}d' if days <= 365 else f'today {min(days, 365)}d'
            self.pytrends.build_payload(keywords, timeframe=timeframe)
            data = self.pytrends.interest_over_time()

            if data.empty:
                return self._empty_result(coin_name)

            result = self._parse_trends_data(data, keywords[0])

            # Cache result
            self.cache.save(cache_key, result)

            return result

        except Exception as e:
            print(f"Warning: Google Trends fetch failed: {e}")
            return self._empty_result(coin_name)

    def _parse_trends_data(self, data: pd.DataFrame, primary_keyword: str) -> Dict[str, Any]:
        """Parse pytrends data into structured format."""
        # Get primary keyword data
        primary_data = data[primary_keyword] if primary_keyword in data.columns else data.iloc[:, 0]

        # Current interest (last value)
        current_interest = int(primary_data.iloc[-1]) if len(primary_data) > 0 else 50

        # Historical data
        historical = []
        for idx, row in data.iterrows():
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
            value = int(row.get(primary_keyword, row.iloc[0])) if primary_keyword in row else int(row.iloc[0])
            historical.append({"date": date_str, "value": value})

        # Interest change
        if len(primary_data) >= 2:
            prev_avg = primary_data.iloc[:-7].mean() if len(primary_data) > 7 else primary_data.iloc[:-1].mean()
            curr_avg = primary_data.iloc[-7:].mean() if len(primary_data) > 7 else primary_data.iloc[-1]

            if prev_avg > 0:
                change_pct = ((curr_avg - prev_avg) / prev_avg) * 100
            else:
                change_pct = 0
        else:
            change_pct = 0

        # Trend direction
        if change_pct > 10:
            trend = "up"
        elif change_pct < -10:
            trend = "down"
        else:
            trend = "stable"

        # Peak interest
        peak_idx = primary_data.idxmax()
        peak_value = int(primary_data.max())
        peak_date = peak_idx.strftime('%Y-%m-%d') if hasattr(peak_idx, 'strftime') else str(peak_idx)

        return {
            "keyword": primary_keyword,
            "current_interest": current_interest,
            "interest_change_pct": round(change_pct, 2),
            "trend_direction": trend,
            "historical_data": historical[-30:],  # Last 30 data points
            "peak_interest": {
                "value": peak_value,
                "date": peak_date
            },
            "average_interest": round(primary_data.mean(), 2),
            "confidence": 0.85,
            "source": "Google Trends",
            "timestamp": datetime.now().isoformat()
        }

    def get_related_queries(self, coin_name: str) -> Dict[str, List[str]]:
        """Get related search queries for a coin.

        Args:
            coin_name: Coin name (e.g., 'bitcoin')

        Returns:
            Dictionary with 'top' and 'rising' queries
        """
        if not self.is_available():
            return {"top": [], "rising": []}

        keywords = self.get_keywords(coin_name)[:1]
        cache_key = f"google_trends_related_{keywords[0]}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            self.pytrends.build_payload(keywords)
            related = self.pytrends.related_queries()

            if not related or keywords[0] not in related:
                return {"top": [], "rising": []}

            data = related[keywords[0]]

            result = {
                "top": [],
                "rising": []
            }

            # Top queries
            if data.get("top") is not None and not data["top"].empty:
                result["top"] = data["top"]["query"].head(10).tolist()

            # Rising queries
            if data.get("rising") is not None and not data["rising"].empty:
                result["rising"] = data["rising"]["query"].head(10).tolist()

            self.cache.save(cache_key, result)
            return result

        except Exception as e:
            print(f"Warning: Related queries fetch failed: {e}")
            return {"top": [], "rising": []}

    def compare_coins(
        self,
        coins: List[str],
        days: int = 30
    ) -> Dict[str, Any]:
        """Compare search interest between multiple coins.

        Args:
            coins: List of coin names (max 5)
            days: Number of days to analyze

        Returns:
            Dictionary with comparison data
        """
        if not self.is_available() or len(coins) < 2:
            return {}

        # Get primary keyword for each coin
        keywords = []
        for coin in coins[:5]:
            kws = self.get_keywords(coin)
            if kws:
                keywords.append(kws[0])

        if len(keywords) < 2:
            return {}

        cache_key = f"google_trends_compare_{'_'.join(keywords)}_{days}"
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            timeframe = f'today {days}d'
            self.pytrends.build_payload(keywords, timeframe=timeframe)
            data = self.pytrends.interest_over_time()

            if data.empty:
                return {}

            # Calculate relative interest
            result = {
                "keywords": keywords,
                "comparison": {},
                "winner": None,
                "historical": []
            }

            # Get latest values
            latest = data.iloc[-1]
            for kw in keywords:
                if kw in latest:
                    result["comparison"][kw] = int(latest[kw])

            # Determine winner
            if result["comparison"]:
                result["winner"] = max(result["comparison"], key=result["comparison"].get)

            # Historical data
            for idx, row in data.iterrows():
                date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                entry = {"date": date_str}
                for kw in keywords:
                    if kw in row:
                        entry[kw] = int(row[kw])
                result["historical"].append(entry)

            self.cache.save(cache_key, result)
            return result

        except Exception as e:
            print(f"Warning: Coin comparison failed: {e}")
            return {}

    def calculate_trend_score(self, trends_data: Dict[str, Any]) -> int:
        """Calculate trend score (1-5) from trends data.

        Args:
            trends_data: Result from get_search_trends()

        Returns:
            Score from 1 (declining) to 5 (strong uptrend)
        """
        if not trends_data or trends_data.get("current_interest") is None:
            return 3

        current = trends_data["current_interest"]
        change = trends_data.get("interest_change_pct", 0)

        # High current interest + uptrend = high score
        if current >= 80 and change > 20:
            return 5
        elif current >= 60 and change > 10:
            return 4
        elif current >= 40 or -10 <= change <= 10:
            return 3
        elif current < 20 or change < -20:
            return 1
        else:
            return 2

    def _empty_result(self, coin_name: str) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "keyword": coin_name,
            "current_interest": 50,
            "interest_change_pct": 0,
            "trend_direction": "stable",
            "historical_data": [],
            "peak_interest": {"value": 50, "date": datetime.now().strftime('%Y-%m-%d')},
            "average_interest": 50,
            "confidence": 0.1,
            "source": "Fallback",
            "timestamp": datetime.now().isoformat()
        }
