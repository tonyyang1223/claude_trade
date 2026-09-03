"""动量维度（Meme 专项核心维度）。

基于 DexScreener 多时间框架涨跌幅（m5/h1/h6/h24）与近 1h 买卖笔数净流入，
刻画短期动能方向与强度。阈值从 ctx.cfg.market 读取（MarketConfig），未挂配置
时回落模块默认值，直接调用 compute(ctx) 行为不变。
"""
from __future__ import annotations

from typing import List, Optional

from .config import MarketConfig
from .types import AnalysisResult


def _mk(ctx: AnalysisResult) -> MarketConfig:
    return ctx.cfg.market if ctx.cfg is not None else MarketConfig()


def compute_momentum(ctx: AnalysisResult) -> Optional[float]:
    dex = ctx.dex
    if not dex or not dex.price_changes:
        return None
    mk = _mk(ctx)
    pc = dex.price_changes
    notes: List[str] = []
    score = 5.0

    # 超新币（<1 天）：h24 以「发行价」为基数（实测出现 +9499%），不具动能参考性。
    fresh = dex.age_days is not None and dex.age_days < mk.newcoin_days
    keys = ("m5", "h1", "h6") if fresh else ("m5", "h1", "h6", "h24")
    if fresh:
        notes.append(
            f"⚠️ 币龄仅 {dex.age_days:.2f} 天（<{mk.newcoin_days:.0f} 天）：h24 涨跌幅"
            f"以发行价为基数、不代表动能，方向判定改用 m5/h1/h6")

    frames = [pc.get(k) for k in keys]
    known = [v for v in frames if v is not None]
    if not known:
        return None
    up = sum(1 for v in known if v > 0)
    down = sum(1 for v in known if v < 0)
    need = mk.momentum_same_dir_count

    if up >= need:
        notes.append(f"近 {len(known)} 周期普涨，动能向上"); score += 2.0
    elif down >= need:
        notes.append(f"近 {len(known)} 周期普跌，动能向下"); score -= 2.5
    elif up == len(known) and len(known) >= 2:
        notes.append(f"近 {len(known)} 个已知周期全涨，动能向上"); score += 1.5
    elif down == len(known) and len(known) >= 2:
        notes.append(f"近 {len(known)} 个已知周期全跌，动能向下"); score -= 2.0
    else:
        notes.append("多周期涨跌分化，动能不明")

    h24 = pc.get("h24")
    if h24 is not None:
        if h24 > mk.momentum_h24_overheat:
            tag = "（新币上线即暴涨，此时追高=接盘风险极高）" if fresh else "（追高/逃顶风险）"
            notes.append(f"24h +{h24:.0f}%{tag}"); score -= 1.0
        elif h24 < mk.momentum_h24_deepdrop:
            tag = "（新币破发深跌，非买入信号）" if fresh else "（超卖，反弹机会但非买入信号）"
            notes.append(f"24h {h24:.0f}%{tag}"); score += 0.5
        elif h24 > 0:
            score += 0.5

    tx = (dex.txns or {}).get("h1") or {}
    b, s = tx.get("buys"), tx.get("sells")
    if b and s:
        if b > s * mk.momentum_buy_dominance:
            notes.append(f"近 1h 买盘占优（{b}/{s}）"); score += 1.0
        elif s > b * mk.momentum_buy_dominance:
            notes.append(f"近 1h 卖盘占优（{b}/{s}）"); score -= 1.0

    ctx.notes.setdefault("momentum", notes)
    return round(max(0.0, min(10.0, score)), 1)
