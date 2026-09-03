"""Investment-advice layer for the type-aware evaluation system.

Produces a *research-oriented* recommendation: a propensity code, a suggested
position band (as % of portfolio), a horizon, and trigger conditions. This is
NOT a buy/sell order. Per the crypto-token-defi-research skill red line, any
mention of inclination must carry a disclaimer — :data:`DISCLAIMER` is therefore
attached to every :class:`Advice` and rendered in all output paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


DISCLAIMER = (
    "⚠️ 本研究为量化模型输出的研究参考，不构成任何投资建议或买卖指令。"
    "加密资产波动剧烈，可能造成全部本金损失。请自行研究并谨慎决策，风险自担。"
)


@dataclass
class Advice:
    """Research-oriented recommendation for a scored token."""
    action_code: str = "hold_off"
    action: str = "观望"
    position_min_pct: float = 0.0
    position_max_pct: float = 0.0
    position_range: str = "0%"
    horizon: str = ""
    triggers: list = field(default_factory=list)
    rationale: str = ""
    disclaimer: str = DISCLAIMER

    @property
    def position_band_text(self) -> str:
        return self.position_range


# rating -> action propensity
_ACTION = {
    "A+": ("watch", "重点关注"),
    "A": ("watch", "建议关注"),
    "B": ("small", "小仓试探"),
    "C": ("hold_off", "观望"),
    "D": ("avoid", "回避"),
    "F": ("avoid", "回避"),
}

# (rating, volatility) -> (min%, max%) suggested position band
_POSITION_BAND = {
    ("A+", "low"): (8, 12), ("A+", "medium"): (5, 8), ("A+", "high"): (3, 5),
    ("A", "low"): (5, 8), ("A", "medium"): (3, 5), ("A", "high"): (2, 3),
    ("B", "low"): (3, 5), ("B", "medium"): (2, 3), ("B", "high"): (1, 2),
    ("C", "low"): (0, 2), ("C", "medium"): (0, 1), ("C", "high"): (0, 0),
    ("D", "low"): (0, 0), ("D", "medium"): (0, 0), ("D", "high"): (0, 0),
    ("F", "low"): (0, 0), ("F", "medium"): (0, 0), ("F", "high"): (0, 0),
}

_HORIZON = {
    "A+": "6-12 个月", "A": "3-6 个月", "B": "1-3 个月",
    "C": "短线/事件驱动", "D": "—", "F": "—",
}


def position_band(rating: str, volatility: str) -> Tuple[float, float]:
    """Return the suggested (min, max) position band in % for a rating/volatility."""
    return _POSITION_BAND.get((rating, volatility), (0.0, 0.0))


def apply_coverage_cap(rating: str, coverage: float) -> str:
    """Cap a rating when data coverage is low (guards against over-confidence).

    coverage = sum of weights of dimensions actually scored. Low coverage means
    few dimensions contributed, so the score is less trustworthy.
    """
    if coverage < 0.40:
        cap = "C"
    elif coverage < 0.60:
        cap = "B"
    else:
        return rating
    order = ["F", "D", "C", "B", "A", "A+"]
    if order.index(rating) > order.index(cap):
        return cap
    return rating


def build_advice(
    rating: str,
    risk_level: str,
    coverage: float,
    profile=None,
    context: Optional[dict] = None,
) -> Advice:
    """Build an :class:`Advice` for a scored token.

    Args:
        rating: Raw rating (A+/A/B/C/D/F) before coverage cap.
        risk_level: 'low' / 'medium' / 'high'.
        coverage: Sum of weights of dimensions actually scored (0-1).
        profile: Optional :class:`~src.analysis.profiles.TypeProfile`.
        context: Optional dict with extra rationale/triggers.
    """
    capped = apply_coverage_cap(rating, coverage)
    vol = profile.volatility if profile else "medium"
    max_pos = profile.max_position_pct if profile else 6.0

    code, action = _ACTION.get(capped, ("hold_off", "观望"))
    lo, hi = position_band(capped, vol)
    # never exceed the type's max position ceiling
    hi = min(hi, max_pos)
    lo = min(lo, hi)

    if hi <= 0:
        band = "0%"
    elif lo == hi:
        band = f"{hi:.0f}%"
    else:
        band = f"{lo:.0f}–{hi:.0f}%"

    triggers = (context or {}).get("triggers", []) or _default_triggers(capped, profile)
    rationale = (context or {}).get("rationale", "") or _default_rationale(capped, coverage, profile)

    return Advice(
        action_code=code,
        action=action,
        position_min_pct=lo,
        position_max_pct=hi,
        position_range=band,
        horizon=_HORIZON.get(capped, ""),
        triggers=triggers,
        rationale=rationale,
        disclaimer=DISCLAIMER,
    )


def _default_triggers(rating: str, profile) -> list:
    out = []
    if rating in ("A+", "A", "B"):
        out.append("价格站稳 200 日均线且量能放大 → 可分批建仓")
        out.append("所属赛道消息面转暖（如 ETF/监管利好）→ 上修评级")
    else:
        out.append("评级低于 B 前维持观望，避免左侧抄底")
    if profile and profile.volatility == "high":
        out.append("高波动品种：单笔仓位与止损需严格，事件驱动为主")
    return out


def _default_rationale(rating: str, coverage: float, profile) -> str:
    parts = []
    if profile:
        parts.append(f"类型={profile.token_type}（波动率{profile.volatility}）")
    parts.append(f"综合评级 {rating}")
    if coverage < 0.60:
        parts.append(f"数据覆盖率 {coverage:.0%}，仓位建议已折让，结论仅供参考")
    return "；".join(parts)
