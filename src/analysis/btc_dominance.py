"""BTC dominance analysis module."""
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from src.data.models import BTCDominance
from src.data.cache import DataCache
from src.api.coingecko import CoinGeckoClient


class BTCDominanceAnalyzer:
    """Analyzes BTC dominance and market phases.

    Uses CoinGecko global API to get dominance data.

    Attributes:
        client: CoinGecko API client
        cache: DataCache for caching data

    Example:
        >>> analyzer = BTCDominanceAnalyzer()
        >>> dominance = analyzer.analyze()
    """

    def __init__(self, cache_dir: Path = Path("data/cache"), api_key: Optional[str] = None):
        """Initialize BTC dominance analyzer.

        Args:
            cache_dir: Directory for caching data
            api_key: Optional CoinGecko API key
        """
        self.client = CoinGeckoClient(api_key=api_key)
        self.cache = DataCache(cache_dir, expire_hours=1)

    def fetch_dominance_data(self) -> Dict[str, Any]:
        """Fetch current dominance data.

        Returns:
            Dictionary with dominance data
        """
        cache_key = "btc_dominance_current"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        market_data = self.client.get_market_data()
        self.cache.save(cache_key, market_data)

        return market_data

    def fetch_dominance_history(self, days: int = 30) -> Dict[str, Any]:
        """Fetch dominance history for trend analysis.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with historical dominance data
        """
        cache_key = f"btc_dominance_history_{days}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        # CoinGecko doesn't have direct dominance history API
        # We'll use multiple calls to get snapshots (simplified approach)
        # In production, would use external source like TradingView

        data = {"current": self.fetch_dominance_data()}
        self.cache.save(cache_key, data)

        return data

    def determine_trend(self, current: float) -> str:
        """Determine dominance trend.

        Args:
            current: Current dominance value

        Returns:
            Trend direction (rising/falling/stable)
        """
        # Simplified: would compare with historical data
        # For now, use thresholds based on typical ranges
        if current > 52:
            return "rising"
        elif current < 38:
            return "falling"
        else:
            return "stable"

    def determine_market_phase(self, dominance: float, trend: str) -> str:
        """Determine market phase based on dominance.

        Args:
            dominance: Current dominance value
            trend: Trend direction

        Returns:
            Market phase description
        """
        if dominance > 50 and trend == "rising":
            return "BTC主导期 - 资金流向比特币"
        elif dominance > 50 and trend == "falling":
            return "资金转向山寨币 - 关注山寨币机会"
        elif dominance >= 40 and dominance <= 50 and trend == "falling":
            return "山寨币季节 - 可转向山寨币"
        elif dominance < 40 and trend == "falling":
            return "极端山寨币季节 - 警惕回调风险"
        elif dominance < 35:
            return "历史低点 - 高风险区域"
        else:
            return "震荡期 - 观望"

    def is_altcoin_season(self, dominance: float) -> bool:
        """Check if it's altcoin season.

        Args:
            dominance: Current dominance value

        Returns:
            True if altcoin season
        """
        return dominance < 45

    def get_recommendation(self, dominance: float, trend: str) -> str:
        """Get action recommendation.

        Args:
            dominance: Current dominance value
            trend: Trend direction

        Returns:
            Recommendation string
        """
        if dominance > 50 and trend in ["rising", "stable"]:
            return "持有BTC，等待资金转向信号"
        elif dominance > 50 and trend == "falling":
            return "关注山寨币，资金开始流出BTC"
        elif dominance >= 40 and dominance <= 50:
            return "可配置山寨币，但仍保持BTC仓位"
        elif dominance < 40:
            return "山寨币为主，但警惕回调风险"
        else:
            return "观望，等待明确信号"

    def analyze(self) -> BTCDominance:
        """Perform full BTC dominance analysis.

        Returns:
            BTCDominance instance
        """
        data = self.fetch_dominance_data()
        dominance = data.get("btc_dominance", 50.0)

        trend = self.determine_trend(dominance)
        market_phase = self.determine_market_phase(dominance, trend)
        altcoin_season = self.is_altcoin_season(dominance)
        recommendation = self.get_recommendation(dominance, trend)

        return BTCDominance(
            current_dominance=dominance,
            trend=trend,
            market_phase=market_phase,
            altcoin_season=altcoin_season,
            recommendation=recommendation
        )