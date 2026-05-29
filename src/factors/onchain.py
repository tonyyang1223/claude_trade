"""On-chain factors: Stablecoin flows and TVL."""
from src.factors import register_factor, FactorCategory, FactorSource
from src.factors.registry import registry
from src.api.defillama import DefiLlamaClient


# ============================================================================
# Stablecoin Flow Factors
# ============================================================================

@register_factor(
    name="stablecoin_net_flow",
    display_name="Stablecoin Net Flow",
    category=FactorCategory.ONCHAIN,
    source=FactorSource.DEFILLAMA,
    description="24h net flow of stablecoins. Positive = capital entering, Negative = capital leaving",
    confidence=0.9,
    version="1.0.0",
    tags=["onchain", "capital_flow", "stablecoins"],
    higher_is_better=True,
    typical_range=(-5e9, 5e9)
)
def compute_stablecoin_net_flow() -> float:
    """Compute global stablecoin net flow."""
    client = DefiLlamaClient()
    data = client.get_stablecoin_flows()
    return data.get("net_flows_24h", 0.0)


@register_factor(
    name="stablecoin_total_supply",
    display_name="Stablecoin Total Supply",
    category=FactorCategory.ONCHAIN,
    source=FactorSource.DEFILLAMA,
    description="Total stablecoin supply across all chains",
    confidence=0.9,
    version="1.0.0",
    tags=["onchain", "liquidity", "stablecoins"],
    higher_is_better=True,
    typical_range=(0, 500e9)
)
def compute_stablecoin_total_supply() -> float:
    """Compute total stablecoin supply."""
    client = DefiLlamaClient()
    data = client.get_stablecoin_flows()
    return data.get("total_supply", 0.0)


# ============================================================================
# TVL Factors
# ============================================================================

@register_factor(
    name="protocol_tvl",
    display_name="Protocol TVL",
    category=FactorCategory.ONCHAIN,
    source=FactorSource.DEFILLAMA,
    description="Total Value Locked in a DeFi protocol",
    confidence=0.9,
    version="1.0.0",
    tags=["onchain", "tvl", "defi"],
    higher_is_better=True,
    typical_range=(0, 50e9)
)
def compute_protocol_tvl(protocol_slug: str) -> float:
    """Compute TVL for a specific protocol."""
    client = DefiLlamaClient()
    data = client.get_protocol_tvl(protocol_slug)
    return data.get("tvl", 0.0)


@register_factor(
    name="tvl_change_7d",
    display_name="TVL Change 7d",
    category=FactorCategory.ONCHAIN,
    source=FactorSource.DEFILLAMA,
    description="7-day change in protocol TVL",
    confidence=0.9,
    version="1.0.0",
    tags=["onchain", "tvl", "momentum"],
    higher_is_better=True,
    typical_range=(-50, 100)
)
def compute_tvl_change_7d(protocol_slug: str) -> float:
    """Compute 7d TVL change for a protocol."""
    client = DefiLlamaClient()
    data = client.get_protocol_tvl(protocol_slug)
    return data.get("tvl_change_7d", 0.0)


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