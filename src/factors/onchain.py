"""On-chain factors: Stablecoin flows and TVL."""
from typing import Optional
from src.factors import register_factor, FactorCategory, FactorSource
from src.factors.registry import registry
from src.api.defillama import DefiLlamaClient
from src.data.coin_mappings import COIN_TO_CHAIN, CHAIN_TO_DEFILLAMA, COIN_TO_DEFILLAMA
from src.api.coingecko import CoinGeckoClient
import logging

logger = logging.getLogger(__name__)


def resolve_chain(coin_id: str) -> Optional[str]:
    """Resolve the chain for a coin.

    Priority:
    1. COIN_TO_CHAIN hardcoded mapping
    2. CoinGecko asset_platform_id API

    Args:
        coin_id: CoinGecko coin ID

    Returns:
        DefiLlama chain name or None
    """
    # 1. Check hardcoded mapping
    chain_name = COIN_TO_CHAIN.get(coin_id)
    if chain_name:
        defillama_chain = CHAIN_TO_DEFILLAMA.get(chain_name)
        if defillama_chain:
            return defillama_chain
        return chain_name

    # 2. Query CoinGecko API
    try:
        client = CoinGeckoClient()
        platform_id = client.get_asset_platform(coin_id)

        if platform_id:
            defillama_chain = CHAIN_TO_DEFILLAMA.get(platform_id.capitalize())
            if defillama_chain:
                return defillama_chain
            return platform_id.capitalize()
    except Exception as e:
        logger.debug(f"Failed to resolve chain for {coin_id}: {e}")

    return None


# ============================================================================
# Stablecoin Flow Factors
# ============================================================================

@register_factor(
    name="stablecoin_net_flow",
    display_name="Stablecoin Net Flow",
    category=FactorCategory.ONCHAIN,
    source=FactorSource.DEFILLAMA,
    description="24h net flow of stablecoins. Chain-specific if coin_id provided.",
    confidence=0.9,
    version="1.1.0",
    tags=["onchain", "capital_flow", "stablecoins"],
    higher_is_better=True,
    typical_range=(-5e9, 5e9),
    min_days=1,
    min_points=7
)
def compute_stablecoin_net_flow(coin_id: str = None) -> float:
    """Compute stablecoin net flow, chain-specific if available."""
    client = DefiLlamaClient()

    # 1. If coin specified, try chain-level data
    if coin_id:
        chain = resolve_chain(coin_id)
        if chain:
            chain_data = client.get_chain_stablecoin_flows(chain)
            net_flow = chain_data.get("net_flows_24h", 0.0)
            logger.debug(f"Using chain stablecoin flow for {coin_id}: {chain}")
            return net_flow

    # 2. Fallback: global data
    global_data = client.get_stablecoin_flows()
    return global_data.get("net_flows_24h", 0.0)


@register_factor(
    name="stablecoin_total_supply",
    display_name="Stablecoin Total Supply",
    category=FactorCategory.ONCHAIN,
    source=FactorSource.DEFILLAMA,
    description="Total stablecoin supply. Chain-specific if coin_id provided.",
    confidence=0.9,
    version="1.1.0",
    tags=["onchain", "liquidity", "stablecoins"],
    higher_is_better=True,
    typical_range=(0, 500e9),
    min_days=1,
    min_points=7
)
def compute_stablecoin_total_supply(coin_id: str = None) -> float:
    """Compute stablecoin total supply, chain-specific if available."""
    client = DefiLlamaClient()

    # 1. If coin specified, try chain-level data
    if coin_id:
        chain = resolve_chain(coin_id)
        if chain:
            chain_data = client.get_chain_stablecoin_flows(chain)
            total_supply = chain_data.get("total_supply", 0.0)
            logger.debug(f"Using chain stablecoin supply for {coin_id}: {chain}")
            return total_supply

    # 2. Fallback: global data
    global_data = client.get_stablecoin_flows()
    return global_data.get("total_supply", 0.0)


# ============================================================================
# TVL Factors
# ============================================================================

@register_factor(
    name="protocol_tvl",
    display_name="Protocol TVL",
    category=FactorCategory.ONCHAIN,
    source=FactorSource.DEFILLAMA,
    description="Total Value Locked. Falls back to chain TVL if protocol unavailable.",
    confidence=0.9,
    version="1.1.0",
    tags=["onchain", "tvl", "defi"],
    higher_is_better=True,
    typical_range=(0, 50e9),
    min_days=1,
    min_points=7
)
def compute_protocol_tvl(coin_id: str) -> float:
    """Compute TVL with fallback logic."""
    client = DefiLlamaClient()

    # 1. Try protocol TVL
    protocol_slug = COIN_TO_DEFILLAMA.get(coin_id)
    if protocol_slug:
        data = client.get_protocol_tvl(protocol_slug)
        if data.get("tvl", 0) > 0:
            return data.get("tvl", 0.0)

    # 2. Fallback: chain TVL
    chain = resolve_chain(coin_id)
    if chain:
        chain_data = client.get_chain_tvl(chain)
        if chain_data.get("tvl", 0) > 0:
            logger.debug(f"Using chain TVL for {coin_id}: {chain}")
            return chain_data.get("tvl", 0.0)

    # 3. No data
    logger.debug(f"No TVL data available for {coin_id}")
    return float('nan')


@register_factor(
    name="tvl_change_7d",
    display_name="TVL Change 7d",
    category=FactorCategory.ONCHAIN,
    source=FactorSource.DEFILLAMA,
    description="7-day change in TVL. Falls back to chain TVL if protocol unavailable.",
    confidence=0.9,
    version="1.1.0",
    tags=["onchain", "tvl", "momentum"],
    higher_is_better=True,
    typical_range=(-50, 100),
    min_days=7,
    min_points=30
)
def compute_tvl_change_7d(coin_id: str) -> float:
    """Compute 7d TVL change with fallback logic."""
    client = DefiLlamaClient()

    # 1. Try protocol TVL
    protocol_slug = COIN_TO_DEFILLAMA.get(coin_id)
    if protocol_slug:
        data = client.get_protocol_tvl(protocol_slug)
        if data.get("tvl", 0) > 0:
            return data.get("tvl_change_7d", 0.0)

    # 2. Fallback: chain TVL
    chain = resolve_chain(coin_id)
    if chain:
        chain_data = client.get_chain_tvl(chain)
        if chain_data.get("tvl", 0) > 0:
            logger.debug(f"Using chain TVL for {coin_id}: {chain}")
            return chain_data.get("tvl_change_7d", 0.0)

    # 3. No data
    logger.debug(f"No TVL data available for {coin_id}")
    return float('nan')


# ============================================================================
# Normalizers
# ============================================================================

@registry.register_normalizer("stablecoin_net_flow")
def normalize_stablecoin_net_flow(raw_value: float) -> float:
    """Normalize stablecoin net flow to 0-1 scale."""
    clamped = max(-5e9, min(5e9, raw_value))
    normalized = 0.5 + (clamped / 10e9)
    return max(0.0, min(1.0, normalized))


@registry.register_normalizer("tvl_change_7d")
def normalize_tvl_change(raw_value: float) -> float:
    """Normalize TVL change to 0-1 scale."""
    clamped = max(-50, min(50, raw_value))
    normalized = 0.5 + (clamped / 100)
    return max(0.0, min(1.0, normalized))