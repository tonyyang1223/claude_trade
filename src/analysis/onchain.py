"""Onchain analysis module."""
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from src.data.models import OnchainData
from src.data.cache import DataCache


class OnchainAnalyzer:
    """Analyzes onchain data for cryptocurrencies.

    Uses free APIs:
    - Blockchain.com API (BTC only, free)
    - CryptoCompare API (free tier)

    Attributes:
        cache: DataCache for caching data

    Example:
        >>> analyzer = OnchainAnalyzer()
        >>> onchain = analyzer.analyze("bitcoin")
    """

    BLOCKCHAIN_API = "https://api.blockchain.info"
    CRYPTOCOMPARE_API = "https://min-api.cryptocompare.com/data"

    def __init__(self, cache_dir: Path = Path("data/cache")):
        """Initialize onchain analyzer.

        Args:
            cache_dir: Directory for caching data
        """
        self.cache = DataCache(cache_dir, expire_hours=1)

    def fetch_btc_stats(self) -> Dict[str, Any]:
        """Fetch BTC onchain stats from Blockchain.com.

        Returns:
            Dictionary with BTC statistics
        """
        cache_key = "btc_onchain_stats"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            # Fetch blockchain stats
            response = requests.get(
                f"{self.BLOCKCHAIN_API}/stats",
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.cache.save(cache_key, data)

            return data
        except Exception as e:
            print(f"Warning: Failed to fetch BTC stats: {e}")
            return {}

    def fetch_btc_address_count(self) -> int:
        """Fetch number of BTC addresses.

        Returns:
            Number of unique addresses
        """
        cache_key = "btc_address_count"

        cached = self.cache.load(cache_key)
        if cached:
            return cached.get("count", 0)

        try:
            response = requests.get(
                f"{self.BLOCKCHAIN_API}/charts/n-unique-addresses?timespan=1days&format=json",
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            if data.get("values"):
                count = data["values"][-1].get("y", 0)
                self.cache.save(cache_key, {"count": count})
                return count
            return 0
        except Exception:
            return 0

    def calculate_nupl_proxy(self, price: float, mvrv: Optional[float] = None) -> Optional[float]:
        """Calculate NUPL proxy based on price and market conditions.

        Since accurate NUPL requires historical cost basis data not available
        through free APIs, we use a proxy based on price position.

        Args:
            price: Current BTC price
            mvrv: MVRV ratio (if available)

        Returns:
            NUPL proxy value (-1 to 1)
        """
        if mvrv:
            # Use MVRV as a proxy for NUPL
            # MVRV > 3 typically indicates market top (NUPL ~0.7)
            # MVRV < 1 indicates market bottom (NUPL ~-0.2)
            if mvrv > 3:
                return 0.7
            elif mvrv < 1:
                return -0.2
            else:
                # Linear interpolation
                return (mvrv - 1) / 2.0 - 0.2

        return None

    def estimate_mvrv(self, market_cap: float, realized_cap: Optional[float] = None) -> Optional[float]:
        """Estimate MVRV ratio.

        Since free APIs don't provide realized cap, we use a simplified estimation.

        Args:
            market_cap: Current market capitalization
            realized_cap: Realized capitalization (if available)

        Returns:
            MVRV ratio or None
        """
        if realized_cap and realized_cap > 0:
            return market_cap / realized_cap

        return None

    def score_onchain(self, nupl: Optional[float], active_addresses: Optional[int]) -> int:
        """Score onchain metrics.

        Scoring rules (based on NUPL):
        - NUPL < 0: Extreme fear -> 5 (accumulation phase)
        - NUPL 0-0.25: Optimism -> 4
        - NUPL 0.25-0.5: Belief -> 3
        - NUPL 0.5-0.75: Greed -> 2
        - NUPL > 0.75: Euphoria -> 1 (risk high)

        Args:
            nupl: NUPL value
            active_addresses: Active addresses count

        Returns:
            Score (1-5)
        """
        if nupl is None:
            return 3  # Neutral if no data

        if nupl < 0:
            return 5
        elif nupl <= 0.25:
            return 4
        elif nupl <= 0.5:
            return 3
        elif nupl <= 0.75:
            return 2
        else:
            return 1

    def analyze(self, coin_name: str = "bitcoin") -> OnchainData:
        """Perform full onchain analysis.

        Args:
            coin_name: Coin name (currently only bitcoin supported)

        Returns:
            OnchainData instance
        """
        # Currently only BTC has reliable free onchain data
        if coin_name.lower() != "bitcoin":
            return OnchainData(
                onchain_signal=3
            )

        # Fetch BTC stats
        stats = self.fetch_btc_stats()

        # Extract data
        price = stats.get("market_price_usd", 0)
        transaction_count = stats.get("n_tx", 0)
        active_addresses = self.fetch_btc_address_count()

        # Calculate metrics (simplified for free API)
        nupl = self.calculate_nupl_proxy(price)
        mvrv = self.estimate_mvrv(stats.get("market_cap_usd", 0))

        # Score onchain
        onchain_signal = self.score_onchain(nupl, active_addresses)

        return OnchainData(
            nupl=nupl,
            mvrv=mvrv,
            active_addresses=active_addresses,
            transaction_count=transaction_count,
            onchain_signal=onchain_signal
        )
