"""Derivatives factors: Funding Rate and Open Interest."""
from typing import Optional

from src.factors import register_factor, FactorCategory, FactorSource
from src.factors.registry import registry
from src.api.coinglass import CoinglassClient


# ============================================================================
# Funding Rate Factor
# ============================================================================

@register_factor(
    name="funding_rate",
    display_name="Funding Rate",
    category=FactorCategory.DERIVATIVES,
    source=FactorSource.BINANCE,
    description="Perpetual futures funding rate. Negative = shorts pay longs (bullish), Positive = longs pay shorts (bearish)",
    confidence=0.98,
    version="1.0.0",
    tags=["derivatives", "sentiment", "binance"],
    higher_is_better=False,
    typical_range=(-0.1, 0.1)
)
def compute_funding_rate(coin_id: str) -> float:
    """Compute funding rate factor for a coin.

    Args:
        coin_id: CoinGecko coin ID (e.g., 'bitcoin')

    Returns:
        Funding rate as percentage (e.g., 0.01 for 0.01%)
    """
    client = CoinglassClient()
    data = client.get_funding_rate(coin_id)
    return data.get("avg_funding_rate", 0.0)


# ============================================================================
# Open Interest Factor
# ============================================================================

@register_factor(
    name="open_interest",
    display_name="Open Interest",
    category=FactorCategory.DERIVATIVES,
    source=FactorSource.BINANCE,
    description="Total open interest in perpetual futures. Higher OI indicates more market participation",
    confidence=0.98,
    version="1.0.0",
    tags=["derivatives", "participation", "binance"],
    higher_is_better=True,
    typical_range=(0, 1e9)
)
def compute_open_interest(coin_id: str) -> float:
    """Compute open interest factor for a coin.

    Args:
        coin_id: CoinGecko coin ID (e.g., 'bitcoin')

    Returns:
        Total open interest in USD
    """
    client = CoinglassClient()
    data = client.get_open_interest(coin_id)
    return data.get("total_open_interest", 0.0)


@register_factor(
    name="oi_change_24h",
    display_name="OI Change 24h",
    category=FactorCategory.DERIVATIVES,
    source=FactorSource.BINANCE,
    description="24-hour change in open interest. Positive = new positions, Negative = positions closing",
    confidence=0.98,
    version="1.0.0",
    tags=["derivatives", "momentum", "binance"],
    higher_is_better=True,
    typical_range=(-50, 50)
)
def compute_oi_change_24h(coin_id: str) -> float:
    """Compute 24h OI change factor.

    Args:
        coin_id: CoinGecko coin ID

    Returns:
        24h OI change percentage
    """
    client = CoinglassClient()
    data = client.get_open_interest(coin_id)
    return data.get("oi_change_24h", 0.0)


# ============================================================================
# Custom Normalizers
# ============================================================================

@registry.register_normalizer("funding_rate")
def normalize_funding_rate(raw_value: float) -> float:
    """Normalize funding rate to 0-1 scale.

    -0.1% -> 1.0 (extremely bullish)
     0.0% -> 0.5 (neutral)
     0.1% -> 0.0 (extremely bearish)
    """
    clamped = max(-0.1, min(0.1, raw_value))
    normalized = 0.5 - (clamped / 0.2)
    return max(0.0, min(1.0, normalized))


@registry.register_normalizer("oi_change_24h")
def normalize_oi_change(raw_value: float) -> float:
    """Normalize OI change to 0-1 scale.

    -50% -> 0.0
      0% -> 0.5
    +50% -> 1.0
    """
    clamped = max(-50, min(50, raw_value))
    normalized = 0.5 + (clamped / 100)
    return max(0.0, min(1.0, normalized))
