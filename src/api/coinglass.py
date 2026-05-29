"""Coinglass API client for Funding Rate and Open Interest data.

Coinglass provides free access to funding rate and open interest data
from major exchanges including Binance, OKX, Bybit, etc.

API Documentation: https://coinglass.com/API
Free tier: No API key required for basic data.
"""
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from src.data.cache import DataCache
from src.data.coin_mappings import COIN_TO_SYMBOL


class CoinglassClient:
    """Client for Coinglass API.

    Fetches funding rate and open interest data from major exchanges.

    Attributes:
        cache: DataCache for caching responses
        session: requests.Session for connection pooling

    Example:
        >>> client = CoinglassClient()
        >>> funding = client.get_funding_rate("BTC")
        >>> oi = client.get_open_interest("BTC")
    """

    BASE_URL = "https://fapi.binance.com"  # Binance Futures API (free, unlimited)

    def __init__(self, cache_dir: Path = Path("data/cache"), api_key: Optional[str] = None):
        """Initialize Coinglass client.

        Args:
            cache_dir: Directory for caching data
            api_key: Optional API key (not required for basic data)
        """
        self.cache = DataCache(cache_dir, expire_hours=0.1)  # 6 minutes TTL
        self.session = requests.Session()
        self.api_key = api_key

        if api_key:
            self.session.headers.update({"api_key": api_key})

    def _get_exchange_symbol(self, coin_id: str) -> str:
        """Convert CoinGecko ID to exchange symbol.

        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin')

        Returns:
            Exchange symbol (e.g., 'BTC')
        """
        trading_pair = COIN_TO_SYMBOL.get(coin_id, f"{coin_id.upper()}/USDT")
        # Strip /USDT suffix to get base symbol
        return trading_pair.replace("/USDT", "")

    def get_funding_rate(self, coin_id: str) -> Dict[str, Any]:
        """Get funding rate from Binance (free, unlimited).

        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin')

        Returns:
            Dictionary with funding rate data including:
            - symbol: Exchange symbol
            - avg_funding_rate: Current funding rate
            - funding_rate_change: Recent change (estimated)
        """
        symbol = self._get_exchange_symbol(coin_id)
        binance_symbol = f"{symbol}USDT"
        cache_key = f"funding_rate_{symbol}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            # Binance Futures API - free, no key required
            response = self.session.get(
                f"{self.BASE_URL}/fapi/v1/fundingRate",
                params={"symbol": binance_symbol, "limit": 100},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                if data and len(data) > 0:
                    # Get latest funding rate
                    latest = data[-1]
                    current_rate = float(latest.get("fundingRate", 0))

                    # Calculate change from previous rate
                    prev_rate = float(data[-2].get("fundingRate", 0)) if len(data) > 1 else current_rate
                    rate_change = (current_rate - prev_rate) if prev_rate else 0

                    result = {
                        "symbol": symbol,
                        "coin_id": coin_id,
                        "exchanges": [{"exchange": "Binance", "rate": current_rate}],
                        "avg_funding_rate": current_rate * 100,  # Convert to percentage
                        "funding_rate_change": rate_change * 100,
                        "confidence": 0.98,  # Binance direct API, high confidence
                        "timestamp": datetime.now().isoformat()
                    }

                    self.cache.save(cache_key, result)
                    return result

            return self._get_funding_rate_fallback(symbol, coin_id)

        except Exception as e:
            print(f"Warning: Failed to fetch funding rate for {coin_id}: {e}")
            return self._get_funding_rate_fallback(symbol, coin_id)

    def _get_funding_rate_fallback(self, symbol: str, coin_id: str) -> Dict[str, Any]:
        """Fallback funding rate data when API fails.

        Args:
            symbol: Exchange symbol
            coin_id: CoinGecko coin ID

        Returns:
            Default funding rate data
        """
        return {
            "symbol": symbol,
            "coin_id": coin_id,
            "exchanges": [],
            "avg_funding_rate": 0.0,
            "funding_rate_change": 0.0,
            "confidence": 0.1,  # Fallback data, low confidence
            "timestamp": datetime.now().isoformat(),
            "error": "API unavailable"
        }

    def get_open_interest(self, coin_id: str) -> Dict[str, Any]:
        """Get open interest from Binance (free, unlimited).

        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin')

        Returns:
            Dictionary with open interest data including:
            - symbol: Exchange symbol
            - total_open_interest: Current OI in contracts
            - oi_change_24h: Estimated 24h change percentage
            - oi_change_7d: Estimated 7d change percentage
        """
        symbol = self._get_exchange_symbol(coin_id)
        binance_symbol = f"{symbol}USDT"
        cache_key = f"open_interest_{symbol}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            # Binance Futures Open Interest API
            response = self.session.get(
                f"{self.BASE_URL}/fapi/v1/openInterest",
                params={"symbol": binance_symbol},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                open_interest = float(data.get("openInterest", 0))

                # Get historical OI for change calculation
                hist_response = self.session.get(
                    f"{self.BASE_URL}/fapi/v1/openInterestHist",
                    params={"symbol": binance_symbol, "limit": 8, "period": "1d"},
                    timeout=30
                )

                oi_change_24h = 0
                oi_change_7d = 0

                if hist_response.status_code == 200:
                    hist_data = hist_response.json()
                    if hist_data and len(hist_data) > 1:
                        prev_oi = float(hist_data[-2].get("openInterest", open_interest))
                        oi_change_24h = ((open_interest - prev_oi) / prev_oi * 100) if prev_oi else 0

                        if len(hist_data) > 7:
                            week_ago_oi = float(hist_data[-8].get("openInterest", open_interest))
                            oi_change_7d = ((open_interest - week_ago_oi) / week_ago_oi * 100) if week_ago_oi else 0

                result = {
                    "symbol": symbol,
                    "coin_id": coin_id,
                    "total_open_interest": open_interest,
                    "oi_change_24h": oi_change_24h,
                    "oi_change_7d": oi_change_7d,
                    "exchanges": [{"exchange": "Binance", "open_interest": open_interest}],
                    "confidence": 0.98,  # Binance direct API, high confidence
                    "timestamp": datetime.now().isoformat()
                }

                self.cache.save(cache_key, result)
                return result

            return self._get_open_interest_fallback(symbol, coin_id)

        except Exception as e:
            print(f"Warning: Failed to fetch open interest for {coin_id}: {e}")
            return self._get_open_interest_fallback(symbol, coin_id)

    def _get_open_interest_fallback(self, symbol: str, coin_id: str) -> Dict[str, Any]:
        """Fallback open interest data when API fails.

        Args:
            symbol: Exchange symbol
            coin_id: CoinGecko coin ID

        Returns:
            Default open interest data
        """
        return {
            "symbol": symbol,
            "coin_id": coin_id,
            "total_open_interest": 0.0,
            "oi_change_24h": 0.0,
            "oi_change_7d": 0.0,
            "exchanges": [],
            "confidence": 0.1,  # Fallback data, low confidence
            "timestamp": datetime.now().isoformat(),
            "error": "API unavailable"
        }

    def score_funding_rate(self, avg_funding_rate: float) -> int:
        """Score funding rate (1-5).

        Interpretation:
        - Negative funding: Shorts pay longs (bearish sentiment, potential reversal)
        - Positive funding: Longs pay shorts (bullish sentiment, but may be overextended)

        Args:
            avg_funding_rate: Average funding rate (percentage)

        Returns:
            Score (1-5)
        """
        # Funding rate is typically in percentage format
        # -0.05% = shorts paying 0.05% to longs
        # +0.05% = longs paying 0.05% to shorts

        if avg_funding_rate < -0.05:  # Extremely negative, shorts crowded
            return 5  # Strong bullish reversal signal
        elif avg_funding_rate < -0.02:
            return 4  # Moderately bullish
        elif abs(avg_funding_rate) < 0.01:  # Neutral
            return 3
        elif avg_funding_rate > 0.05:  # Extremely positive, longs crowded
            return 1  # Risk of long squeeze
        else:
            return 2  # Moderately bearish

    def score_open_interest(self, oi_change_24h: float) -> int:
        """Score open interest change (1-5).

        Interpretation:
        - OI increasing + price up = New money entering (genuine uptrend)
        - OI decreasing + price up = Shorts closing (potential reversal)
        - OI increasing + price down = New shorts opening (genuine downtrend)
        - OI decreasing + price down = Longs closing (potential reversal)

        Args:
            oi_change_24h: 24h OI change percentage

        Returns:
            Score (1-5)
        """
        if oi_change_24h > 20:  # Strong increase in OI
            return 5  # Strong conviction
        elif oi_change_24h > 10:
            return 4  # Growing interest
        elif abs(oi_change_24h) < 5:  # Stable OI
            return 3  # Neutral
        elif oi_change_24h < -20:  # Strong decrease
            return 1  # Losing interest/positions closing
        else:
            return 2  # Moderately declining