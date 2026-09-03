"""流动性健康维度（Meme 专项）。

新发 Meme 的最大归零风险来自「薄流动性 + 高控盘」。指标阈值从
ctx.cfg.market 读取（MarketConfig），未挂配置回落默认值。
"""
from __future__ import annotations

from typing import List, Optional

from .config import MarketConfig
from .types import AnalysisResult


def _mk(ctx: AnalysisResult) -> MarketConfig:
    return ctx.cfg.market if ctx.cfg is not None else MarketConfig()


def compute_liquidity_health(ctx: AnalysisResult) -> Optional[float]:
    dex = ctx.dex
    if not dex or dex.liquidity_usd is None:
        return None
    mk = _mk(ctx)
    liq = dex.liquidity_usd
    mc = dex.market_cap or dex.fdv
    vol = dex.volume_24h
    notes: List[str] = []
    score = 5.0

    if mc:
        ratio = liq / mc
        if ratio > mk.liq_mc_ratio_healthy:
            notes.append(f"流动性/市值 {ratio:.0%}，深度健康、难操控"); score += 2.0
        elif ratio > mk.liq_mc_ratio_mid:
            notes.append(f"流动性/市值 {ratio:.0%}，中等"); score += 0.5
        else:
            notes.append(f"流动性/市值仅 {ratio:.0%}，易被大额砸盘操控"); score -= 2.0

    if vol and liq:
        turn = vol / liq
        if turn > mk.liq_turnover_hot:
            notes.append(f"24h 换手 {turn:.0f}x，异常高（疑似对敲/纯短线）"); score -= 1.5
        elif turn > mk.liq_turnover_active:
            notes.append(f"24h 换手 {turn:.0f}x，交易活跃"); score += 0.5
        else:
            notes.append(f"24h 换手 {turn:.1f}x，相对平稳"); score += 0.3

    if liq >= mk.liq_abs_good_usd:
        notes.append("流动性 >$500K，滑点可控"); score += 1.0
    elif liq < mk.liq_abs_bad_usd:
        notes.append("流动性 <$50K，滑点高、易被扫"); score -= 2.0

    ctx.notes.setdefault("liquidity_health", notes)
    return round(max(0.0, min(10.0, score)), 1)
