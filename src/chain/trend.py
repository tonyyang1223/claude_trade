"""趋势维度分析。

基于 DEX 报价（24h 涨跌、买卖比、流动性）给出 0-10 趋势强度分。
band 阈值从 ctx.cfg.market 读取（MarketConfig），未挂配置回落默认值。
"""
from __future__ import annotations

from typing import List, Optional

from .config import MarketConfig
from .types import AnalysisResult


def _mk(ctx: AnalysisResult) -> MarketConfig:
    return ctx.cfg.market if ctx.cfg is not None else MarketConfig()


def compute_trend(ctx: AnalysisResult) -> Optional[float]:
    dex = ctx.dex
    if not dex:
        return None
    mk = _mk(ctx)
    notes: List[str] = []
    score = 5.0
    chg = dex.price_change_24h
    bsr = dex.buy_sell_ratio
    liq = dex.liquidity_usd or 0

    # 超新币（<1 天）：h24 实为「自发行价以来」涨幅，改用 h6（其次 h1/m5）。
    fresh = dex.age_days is not None and dex.age_days < mk.newcoin_days
    eff = chg
    if fresh:
        pc = dex.price_changes or {}
        eff = pc.get("h6")
        if eff is None:
            eff = pc.get("h1")
        if eff is None:
            eff = pc.get("m5")
        notes.append(
            f"⚠️ 币龄 {dex.age_days:.2f} 天：24h 涨跌 {chg:+.1f}% 实为「自发行价以来」涨幅，"
            f"不代表日内趋势，本维度改用 h6 {eff:+.1f}%" if eff is not None else
            f"⚠️ 币龄 {dex.age_days:.2f} 天：24h 涨跌 {chg:+.1f}% 实为「自发行价以来」涨幅，不可比")
        score -= 1.0

    lbl = "h6" if fresh else "24h"
    healthy_hi, strong_hi = mk.trend_band_healthy_hi, mk.trend_band_strong_hi
    if eff is not None:
        if 0 <= eff <= healthy_hi:
            notes.append(f"{lbl} 涨幅 +{eff:.1f}%，温和上行"); score += 1.5
        elif healthy_hi < eff <= strong_hi:
            notes.append(f"{lbl} 涨幅 +{eff:.1f}%，强势但未过热"); score += 1.0
        elif eff > strong_hi:
            notes.append(f"{lbl} 涨幅 +{eff:.1f}%，短期过热/获利盘重"); score -= 1.5
        else:
            notes.append(f"{lbl} 跌幅 {eff:.1f}%"); score -= 1.0

    if bsr is not None:
        if bsr >= mk.trend_bsr_bull:
            notes.append(f"买卖比 {bsr}（买方占优）"); score += 1.0
        elif bsr <= mk.trend_bsr_bear:
            notes.append(f"买卖比 {bsr}（卖方占优）"); score -= 1.0

    if liq >= mk.trend_liq_good_usd:
        notes.append(f"流动性 ${liq:,.0f}，深度充足"); score += 1.0
    elif liq < mk.trend_liq_bad_usd:
        notes.append(f"流动性仅 ${liq:,.0f}，滑点风险高"); score -= 2.0

    ctx.notes.setdefault("trend", notes)
    return round(max(0.0, min(10.0, score)), 1)
