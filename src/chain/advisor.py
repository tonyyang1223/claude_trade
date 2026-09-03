"""投资决策建议（复用 claude_trading advice 框架思路 + 强制免责声明）。

输入综合分与各维度分，输出决策、风险等级、建议仓位、触发条件。
欺诈拦截优先：安全分过低直接判「高风险-不评级」，无论其他维度多高。
档位/护栏阈值从 ctx.cfg.decision（DecisionConfig）读取；未挂配置回落默认，
直接调用 decide(...) 的旧路径行为不变。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .config import DecisionConfig
from .types import AnalysisResult

DISCLAIMER = (
    "⚠️ 本分析由 AI 基于公开链上数据自动生成，仅供参考，不构成任何投资建议或个股推荐。"
    "加密资产（尤其新发 Meme/链上代币）风险极高，可能存在归零、rug、流动性枯竭等情形，决策需谨慎。"
)


def _dcfg(ctx: AnalysisResult) -> DecisionConfig:
    return ctx.cfg.decision if ctx.cfg is not None else DecisionConfig()


def _ladder(dc: DecisionConfig):
    """档位表（降序）；末位 = reject 兜底档。返回 (list[(label,pos,risk)], n)"""
    bands = sorted(dc.bands, key=lambda b: b.min_total, reverse=True)
    ladder = [(b.label, b.position, b.risk, b.note) for b in bands]
    ladder.append((dc.reject_label, dc.reject_position, dc.reject_risk, dc.reject_note))
    return ladder


def decide(ctx: AnalysisResult, total: float, scored: Dict[str, float],
           missing: List[str]) -> Dict:
    dc = _dcfg(ctx)
    sec = scored.get("security")
    ladder = _ladder(dc)
    flags = ctx.flags

    # 欺诈拦截（决策与档位体系解耦：直接定档）
    if sec is not None and sec < dc.hard_block_security_lt:
        decision, risk, position, triggers = (dc.hard_block_label, "高", "0%",
                                              [dc.hard_block_note])
    elif sec is not None and sec < dc.soft_block_security_lt:
        decision, risk, position, triggers = (dc.soft_block_label, "高", "0%",
                                              [dc.soft_block_note])
    else:
        # 档位匹配（bands 降序，取第一个 total >= min_total；否则 reject）
        idx = next((i for i, b in enumerate(sorted(dc.bands, key=lambda b: b.min_total,
                                                   reverse=True))
                    if total >= b.min_total), len(dc.bands))
        label, position, risk, note = ladder[idx]
        decision, triggers = label, [_trig(total, ctx, dc) or note]

    # ---- 风险护栏：只降不升 ----
    age = None
    if ctx.profile and ctx.profile.age_days is not None:
        age = ctx.profile.age_days
    elif ctx.dex and ctx.dex.age_days is not None:
        age = ctx.dex.age_days

    lp_unknown = (ctx.liquidity is None or ctx.liquidity.locked_pct is None)
    lh = scored.get("liquidity_health")

    cur = _idx_of(ladder, decision)
    guards: List[str] = []
    if age is not None and age < dc.guard_age_days_lt:
        cur = max(cur, dc.guard_age_level)
        guards.append(f"币龄仅 {age:.2f} 天（<{dc.guard_age_days_lt:.0f} 天）：无充分历史与流动性记录，"
                      f"且 h24 涨跌幅为「自发行价」口径")
    if lh is not None and lh < dc.guard_liquidity_health_lt:
        cur = max(cur, dc.guard_liquidity_level)
        guards.append(f"流动性健康仅 {lh:.1f}/10（换手异常高 / 深度不足），价格易被操控")
    if age is not None and age < dc.guard_newcoin_days_lt and lp_unknown:
        cur = max(cur, dc.guard_newcoin_level)
        guards.append(f"新币（{age:.2f} 天）且 LP 锁仓状态未知：无法排除撤池（rug）风险")

    if guards:
        decision, position, risk, _ = ladder[cur]
        triggers = [_trig(total, ctx, dc) or f"综合分 {total:.1f}"]
        triggers.extend(f"⚠️ 风险护栏：{g}" for g in guards)
        triggers.append(f"→ 受护栏约束，最终建议降档为：{decision}（仓位 {position}）")

    if missing:
        triggers.append(f"以下维度数据缺失（已排除出加权）：{', '.join(missing)}")

    return {
        "decision": decision,
        "risk": risk,
        "position": position,
        "total": total,
        "scored": scored,
        "missing": missing,
        "triggers": triggers,
        "disclaimer": DISCLAIMER,
    }


def _idx_of(ladder, decision: str) -> int:
    for i, (label, _, _, _) in enumerate(ladder):
        if label == decision:
            return i
    return len(ladder) - 1


def _trig(total: float, ctx: AnalysisResult, dc: DecisionConfig) -> Optional[str]:
    dex = ctx.dex
    if dex and dex.price_change_24h is not None and dex.price_change_24h > dc.overheat_pct:
        return f"触发：24h 涨幅 >{dc.overheat_pct:.0f}% 已过热，回调至均线再考虑"
    if dex and dex.liquidity_usd and dex.liquidity_usd < dc.liq_min_usd:
        return f"触发：流动性偏低（<${dc.liq_min_usd:,.0f}），仅可在深度改善后小仓"
    return None
