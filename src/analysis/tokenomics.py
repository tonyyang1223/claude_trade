"""Pure scoring functions for the new evaluation dimensions.

Each function returns an ``int`` in 1-5, or ``None`` when the required data is
unavailable. **None means "not scored", never a default 3** — the caller
(type-aware Scorer) treats None as a structurally/transiently missing dimension
and redistributes weights accordingly, instead of silently padding the score.

Data is passed either as a snapshot-like object (duck-typed via ``getattr``) or
as explicit numbers, so the module has no network dependencies and is easy to
unit test.
"""

from __future__ import annotations

import math
from typing import Any, Optional, Tuple


# ── Tokenomics ──

def score_tokenomics(snapshot: Any) -> Optional[int]:
    """Score a token's supply/tokenomics health (1-5) or None.

    Considers circulating ratio (higher better), dilution multiple FDV/MC
    (lower better) and locked ratio (higher = more unlock risk).
    """
    cr = getattr(snapshot, "circulating_ratio", None)
    dm = getattr(snapshot, "dilution_multiple", None)
    lr = getattr(snapshot, "locked_ratio", None)
    if cr is None and dm is None and lr is None:
        return None
    scores = []
    if cr is not None:
        scores.append(_band(cr, [(0.9, 5), (0.7, 4), (0.5, 3), (0.3, 2)], 1))
    if dm is not None:
        scores.append(_band(dm, [(1.2, 5), (2.0, 4), (4.0, 3), (8.0, 2)], 1, ascending=False))
    if lr is not None:
        # locked ratio: low = good
        scores.append(_band(lr, [(0.10, 5), (0.30, 4), (0.50, 3), (0.70, 2)], 1, ascending=False))
    return int(round(sum(scores) / len(scores)))


def score_valuation(snapshot: Any, protocol: Any = None) -> Optional[int]:
    """Score valuation attractiveness (1-5) or None.

    Combines FDV/MC ratio (lower better) with protocol P/S (lower better when
    fee data is available).
    """
    fdv_mc = getattr(snapshot, "fdv_mc_ratio", None)
    scores = []
    if fdv_mc is not None:
        scores.append(_band(fdv_mc, [(1.2, 5), (2.0, 4), (4.0, 3), (8.0, 2)], 1, ascending=False))
    ps = None
    if protocol is not None:
        ps = getattr(protocol, "ps_fdv", None) or getattr(protocol, "ps_mcap", None)
    if ps is not None:
        scores.append(_band(ps, [(5.0, 5), (20.0, 4), (60.0, 3), (150.0, 2)], 1, ascending=False))
    if not scores:
        return None
    return int(round(sum(scores) / len(scores)))


# ── Peg stability (stablecoins) ──

def score_peg_stability(
    price: Optional[float],
    target: float = 1.0,
    peg_deviation_pct: Optional[float] = None,
    reserve_ratio: Optional[float] = None,
) -> Optional[int]:
    """Score a stablecoin's peg stability (1-5) or None.

    ``peg_deviation_pct`` (absolute %) takes precedence; otherwise it is derived
    from ``price`` vs ``target``. ``reserve_ratio`` (>=1 healthy) can downgrade
    an otherwise tight peg if reserves are thin.
    """
    if price is None and peg_deviation_pct is None:
        return None
    if peg_deviation_pct is None:
        peg_deviation_pct = abs(price - target) / target * 100 if target else 0.0
    score = _band(peg_deviation_pct, [(0.1, 5), (0.5, 4), (1.0, 3), (3.0, 2)], 1, ascending=False)
    if reserve_ratio is not None and reserve_ratio < 1.0:
        score = max(1, score - 1)
    return score


# ── Narrative heat (Meme / AI) ──

def score_narrative(
    reddit_mentions: Optional[int] = None,
    google_trends: Optional[float] = None,
) -> Optional[int]:
    """Score narrative/mindshare heat (1-5) or None.

    Uses an absolute level (not a coin-vs-coin comparison): Reddit mention count
    on a log scale, falling back to Google Trends index when available.
    """
    if reddit_mentions is None and google_trends is None:
        return None
    if reddit_mentions is not None and reddit_mentions > 0:
        level = math.log10(reddit_mentions + 1)
        return max(1, min(5, int(round(level)) + 1))
    if google_trends is not None:
        # 0-100 index -> 1-5
        return max(1, min(5, int(round(google_trends / 20.0))))
    return 1


# ── TVL momentum (DeFi) ──

def score_tvl_momentum(tvl_data: Any) -> Optional[int]:
    """Score 7d TVL momentum (1-5) or None."""
    chg = getattr(tvl_data, "tvl_change_7d", None)
    if chg is None:
        return None
    return _band(chg, [(15.0, 5), (5.0, 4), (0.0, 3), (-10.0, 2)], 1, ascending=True)


# ── Helpers ──

def _band(value: float, thresholds: list, default: int, ascending: bool = True) -> int:
    """Map ``value`` to a score using (threshold, score) breakpoints.

    ``ascending=True`` means higher value → higher score; ``False`` means higher
    value → lower score (so thresholds are "good up to X").
    """
    for threshold, score in thresholds:
        if ascending:
            if value >= threshold:
                return score
        else:
            if value <= threshold:
                return score
    return default
