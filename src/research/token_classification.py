"""Token type classification (moved to src layer).

Ports the CoinGecko category → slug mapping previously buried in
``scripts/scan/scan_top_800.py`` so the analysis layer can reuse it.

Fixes the legacy substring bug: ``'Chainlink'`` previously matched ``ai``
because ``'ai' in 'chainlink'`` is True and ``ai`` had higher priority than
``oracle``. Matching now requires a **word boundary**, so ``ai`` only fires
when it is a standalone token (e.g. category ``"AI"`` or ``"AI & Data"``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ── Category mapping (CoinGecko category string → internal slug) ──
# Longest / most-specific keys first within groups so exact matches win.
CATEGORY_MAP = {
    "decentralized finance (defi)": "defi", "defi": "defi",
    "layer 1": "layer-1", "layer 1 (l1)": "layer-1", "l1": "layer-1",
    "layer 2": "layer-2", "layer 2 (l2)": "layer-2", "l2": "layer-2",
    "smart contract platform": "layer-1",
    "meme": "meme", "memes": "meme",
    "gaming": "gaming", "gamefi": "gaming",
    "nft": "nft", "non-fungible-tokens": "nft",
    "exchange": "exchange", "centralized exchange": "exchange", "dex": "exchange",
    "stablecoin": "stablecoin", "stablecoins": "stablecoin",
    "privacy": "privacy",
    "real world assets": "rwa", "rwa": "rwa", "tokenized": "rwa",
    "artificial intelligence": "ai", "ai": "ai",
    "oracle": "oracle", "oracles": "oracle",
    "storage": "storage", "bridge": "bridge", "bridges": "bridge",
    "yield aggregator": "yield", "yield": "yield",
    "lending": "lending", "borrowing": "lending",
    "derivatives": "derivatives",
    "prediction market": "prediction",
    "liquid staking": "liquid-staking", "restaking": "restaking",
    "proof of stake": "pos", "proof of work": "pow",
    "ecosystem": "ecosystem",
    "portfolio": "portfolio",
    "index": "index",
    "made in usa": "regional",
    "etf": "etf",
}

# Priority order when a coin matches multiple categories.
# ``stablecoin`` is placed first on purpose: a coin that is a stablecoin must
# always be scored as a stablecoin (peg stability is its defining risk), even
# if CoinGecko also tags it with a network-layer or DeFi category. This also
# fixes the USDC bug where ``"Morph L2 Ecosystem"`` previously won over
# ``"Stablecoins"`` because ``layer-2`` outranked ``stablecoin``.
CATEGORY_PRIORITY = [
    "stablecoin", "defi", "layer-1", "layer-2", "meme", "gaming", "nft",
    "rwa", "ai", "oracle", "exchange", "lending", "derivatives",
    "liquid-staking", "restaking", "yield", "prediction", "privacy",
    "bridge", "storage", "etf", "pos", "pow", "ecosystem",
    "regional", "portfolio", "index", "unclassified",
]

# All 27 distinguishable token types (priority minus the fallback).
ALL_TOKEN_TYPES = [p for p in CATEGORY_PRIORITY if p != "unclassified"]

# Human-readable labels for reports (zh / en).
TYPE_LABELS = {
    "defi": ("DeFi", "DeFi"),
    "layer-1": ("Layer-1 公链", "Layer-1"),
    "layer-2": ("Layer-2 扩容", "Layer-2"),
    "meme": ("Meme 币", "Meme"),
    "gaming": ("GameFi", "Gaming"),
    "nft": ("NFT", "NFT"),
    "exchange": ("交易所平台币", "Exchange"),
    "stablecoin": ("稳定币", "Stablecoin"),
    "rwa": ("RWA 真实资产", "RWA"),
    "ai": ("AI 概念", "AI"),
    "oracle": ("预言机", "Oracle"),
    "privacy": ("隐私币", "Privacy"),
    "storage": ("存储", "Storage"),
    "bridge": ("跨链桥", "Bridge"),
    "yield": ("收益聚合", "Yield"),
    "lending": ("借贷", "Lending"),
    "derivatives": ("衍生品", "Derivatives"),
    "prediction": ("预测市场", "Prediction"),
    "liquid-staking": ("流动性质押", "Liquid Staking"),
    "restaking": ("再质押", "Restaking"),
    "pos": ("PoS", "PoS"),
    "pow": ("PoW", "PoW"),
    "ecosystem": ("生态基金", "Ecosystem"),
    "regional": ("区域概念", "Regional"),
    "portfolio": ("投资组合", "Portfolio"),
    "index": ("指数", "Index"),
    "etf": ("ETF", "ETF"),
    "unclassified": ("未分类", "Unclassified"),
}


@dataclass
class TokenTypeMatch:
    """Detailed classification result."""
    primary: str
    all_matched: List[str] = field(default_factory=list)
    raw_categories: List[str] = field(default_factory=list)
    is_fallback: bool = False

    @property
    def label(self) -> str:
        return TYPE_LABELS.get(self.primary, (self.primary, self.primary))[0]


def classify_coin(categories: Optional[List[str]]) -> str:
    """Return the primary token type slug for a coin's CoinGecko categories.

    Args:
        categories: List of CoinGecko category strings (may be empty/None).

    Returns:
        One of :data:`ALL_TOKEN_TYPES` or ``"unclassified"``.
    """
    match = classify_coin_detailed(categories)
    return match.primary


def classify_coin_detailed(categories: Optional[List[str]]) -> TokenTypeMatch:
    """Return a detailed classification result.

    Uses exact match first, then word-boundary substring match. The
    word-boundary requirement prevents false positives such as
    ``'Chainlink' -> 'ai'``.
    """
    matched: set = set()
    raw = list(categories or [])
    for cat in raw:
        lower = (cat or "").lower().strip()
        if not lower:
            continue
        # Ecosystem-membership tags (e.g. "BNB Chain Ecosystem",
        # "Morph L2 Ecosystem", "Solana Ecosystem") are noise: they describe
        # which ecosystem a token belongs to, not what the token *is*. Skip
        # them so they cannot pull in a network-layer slug such as ``layer-2``
        # via a substring like "L2". The bare "Ecosystem" category (exact
        # match) is still allowed through as a real type signal.
        if "ecosystem" in lower and lower != "ecosystem":
            continue
        if lower in CATEGORY_MAP:
            matched.add(CATEGORY_MAP[lower])
            continue
        for key, slug in CATEGORY_MAP.items():
            # Word-boundary match: key must be a standalone token.
            if re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", lower):
                matched.add(slug)
                break

    for priority_cat in CATEGORY_PRIORITY:
        if priority_cat in matched:
            return TokenTypeMatch(
                primary=priority_cat,
                all_matched=sorted(matched),
                raw_categories=raw,
                is_fallback=False,
            )
    return TokenTypeMatch(
        primary="unclassified",
        all_matched=sorted(matched),
        raw_categories=raw,
        is_fallback=True,
    )


def label_of(token_type: str) -> str:
    """Return the Chinese label for a token type slug."""
    return TYPE_LABELS.get(token_type, (token_type, token_type))[0]
