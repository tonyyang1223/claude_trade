"""Per-token-type scoring profiles (type-aware evaluation system).

Encodes differentiated weight allocations for all 27 token types so that a
Meme coin is not scored on GitHub activity and a stablecoin is not scored on
technical/volatility in the same way as a Layer-1.

Every profile's weights sum to 1.0. Only dimensions present in ``weights`` are
fetched and scored for that type (structural non-applicability), which prevents
the legacy distortion where inapplicable dimensions silently scored a default 3.

See plan: docs/research/token_scoring.md (generated) and the design notes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# All 12 evaluation dimensions.
DIMENSION_KEYS = [
    "market", "technical", "onchain", "sentiment", "github", "social",
    "risk", "tokenomics", "valuation", "narrative", "peg_stability", "tvl",
]

# Short aliases used in weight dicts.
MK, TE, OC, SE, GH, SO, RK, TK, VA, NA, PEG, TVL = DIMENSION_KEYS


# ── Family baselines (each sums to 1.0) ──
FAMILY_PROFILES: Dict[str, Dict[str, float]] = {
    # F1 公链
    "l1": {MK: .14, TE: .13, OC: .10, SE: .06, GH: .12, SO: .07, RK: .12, TK: .16, VA: .10},
    # F2 DeFi
    "defi": {MK: .12, TE: .12, SE: .05, GH: .08, SO: .06, RK: .12, TK: .13, VA: .17, TVL: .15},
    # F3 稳定币
    "stablecoin": {MK: .10, PEG: .40, VA: .12, RK: .28, SE: .10},
    # F4 Meme
    "meme": {MK: .12, TE: .22, NA: .20, SO: .18, RK: .18, TK: .10},
    # F5 RWA
    "rwa": {MK: .12, TE: .12, SE: .05, GH: .08, SO: .05, RK: .18, TK: .18, VA: .22},
    # F6 AI
    "ai": {MK: .12, TE: .15, NA: .16, SO: .10, GH: .12, RK: .14, TK: .11, VA: .10},
    # F7 基础设施
    "infra": {MK: .13, TE: .12, SE: .05, GH: .14, SO: .06, RK: .14, TK: .15, VA: .11, TVL: .10},
    # F8 GameFi & NFT
    "gaming": {MK: .12, TE: .15, NA: .15, SO: .16, GH: .08, RK: .14, TK: .12, VA: .08},
    # F9 通用
    "generic": {MK: .16, TE: .15, OC: .10, SE: .08, GH: .08, SO: .08, RK: .15, TK: .12, VA: .08},
}

# Family → volatility profile / max suggested position (% of portfolio)
FAMILY_RISK = {
    "l1": ("medium", 10),
    "defi": ("high", 8),
    "stablecoin": ("low", 25),
    "meme": ("high", 3),
    "rwa": ("medium", 10),
    "ai": ("high", 6),
    "infra": ("medium", 8),
    "gaming": ("high", 5),
    "generic": ("medium", 6),
}


# 27 token types → family
TYPE_FAMILY: Dict[str, str] = {
    "layer-1": "l1", "layer-2": "l1", "pos": "l1", "pow": "l1",
    "defi": "defi", "lending": "defi", "derivatives": "defi", "yield": "defi",
    "liquid-staking": "defi", "restaking": "defi", "prediction": "defi", "exchange": "defi",
    "stablecoin": "stablecoin",
    "meme": "meme",
    "rwa": "rwa", "etf": "rwa", "index": "rwa",
    "ai": "ai",
    "oracle": "infra", "storage": "infra", "bridge": "infra", "privacy": "infra",
    "gaming": "gaming", "nft": "gaming",
    "ecosystem": "generic", "regional": "generic", "portfolio": "generic", "unclassified": "generic",
}


# 27 explicit type profiles (each sums to 1.0)
TYPE_PROFILES: Dict[str, Dict[str, float]] = {
    # ── F1 公链 ──
    "layer-1": {MK: .14, TE: .13, OC: .06, SE: .06, GH: .12, SO: .07, RK: .12, TK: .16, VA: .14},
    "layer-2": {MK: .13, TE: .13, SE: .06, GH: .15, SO: .07, RK: .12, TK: .20, VA: .14},  # 无免费链上
    "pos": FAMILY_PROFILES["l1"],
    "pow": FAMILY_PROFILES["l1"],
    # ── F2 DeFi ──
    "defi": FAMILY_PROFILES["defi"],
    "lending": {MK: .12, TE: .12, SE: .05, GH: .08, SO: .06, RK: .15, TK: .13, VA: .14, TVL: .15},
    "derivatives": {MK: .12, TE: .15, SE: .05, GH: .06, SO: .06, RK: .14, TK: .12, VA: .15, TVL: .15},
    "yield": FAMILY_PROFILES["defi"],
    "liquid-staking": FAMILY_PROFILES["defi"],
    "restaking": {MK: .12, TE: .12, SE: .05, GH: .08, SO: .06, RK: .15, TK: .13, VA: .14, TVL: .15},
    "prediction": FAMILY_PROFILES["defi"],
    "exchange": FAMILY_PROFILES["defi"],
    # ── F3 稳定币 ──
    "stablecoin": FAMILY_PROFILES["stablecoin"],
    # ── F4 Meme ──
    "meme": FAMILY_PROFILES["meme"],
    # ── F5 RWA ──
    "rwa": FAMILY_PROFILES["rwa"],
    "etf": {MK: .12, TE: .20, SE: .04, GH: .04, SO: .04, RK: .18, TK: .08, VA: .30},
    "index": {MK: .12, TE: .20, SE: .04, GH: .04, SO: .04, RK: .18, TK: .08, VA: .30},
    # ── F6 AI ──
    "ai": FAMILY_PROFILES["ai"],
    # ── F7 基础设施 ──
    "oracle": FAMILY_PROFILES["infra"],
    "storage": FAMILY_PROFILES["infra"],
    "bridge": {MK: .12, TE: .12, SE: .05, GH: .12, SO: .05, RK: .20, TK: .14, VA: .10, TVL: .10},
    "privacy": FAMILY_PROFILES["infra"],
    # ── F8 GameFi & NFT ──
    "gaming": FAMILY_PROFILES["gaming"],
    "nft": {MK: .12, TE: .12, NA: .18, SO: .18, GH: .06, RK: .14, TK: .12, VA: .08},
    # ── F9 通用 ──
    "ecosystem": FAMILY_PROFILES["generic"],
    "regional": FAMILY_PROFILES["generic"],
    "portfolio": FAMILY_PROFILES["generic"],
    "unclassified": FAMILY_PROFILES["generic"],
}


@dataclass
class TypeProfile:
    """Scoring profile for a token type."""
    token_type: str
    family: str
    weights: Dict[str, float]
    volatility: str = "medium"
    max_position_pct: float = 6.0
    notes: str = ""

    @property
    def applicable_dims(self) -> List[str]:
        return list(self.weights.keys())

    def is_applicable(self, dim: str) -> bool:
        return dim in self.weights


def get_profile(token_type: str) -> TypeProfile:
    """Return the :class:`TypeProfile` for a token type slug.

    Unknown types fall back to the generic profile.
    """
    family = TYPE_FAMILY.get(token_type, "generic")
    weights = TYPE_PROFILES.get(token_type) or TYPE_PROFILES["unclassified"]
    volatility, max_pos = FAMILY_RISK[family]
    return TypeProfile(
        token_type=token_type,
        family=family,
        weights=dict(weights),
        volatility=volatility,
        max_position_pct=max_pos,
    )


# Backwards-compatible default (used when Scorer is constructed without a type).
DEFAULT_PROFILE = get_profile("unclassified")
