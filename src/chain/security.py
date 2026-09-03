"""欺诈 / 安全维度分析（最高权重维度）。

聚合 GoPlus + 链上 contract security + holders + liquidity，产出 0-10 安全分
（越高越安全）与结构化红旗清单（Flag{level,code,msg}，写入 ctx.flags）。

设计（skill_design.md §5.2）：扣分、上限、集中度警戒线等可调策略从
ctx.cfg.security（SecurityPolicy）读取；未挂配置时回落 SecurityPolicy() 默认值，
保证直接调用 compute(ctx) 的旧路径行为不变。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from .config import SecurityPolicy
from .types import AnalysisResult, Flag, flag

# 红旗 code 全集（测试据此断言 schema 稳定）
FLAG_CODES = {
    "HONEYPOT", "BLACKLISTED", "MINTABLE", "OWNER_RECLAIMABLE", "PROXY",
    "CAN_BLACKLIST", "CAN_PAUSE", "UNVERIFIED", "TAX_OVER", "LP_LOW_LOCK",
    "LP_NOT_BURNED", "TOP10_CONCENTRATED", "CREATOR_CONCENTRATED",
    "SUPPLY_FIXED", "NO_OWNER_FN", "NOT_PROXY", "LOW_COVERAGE", "LP_UNVERIFIED",
}


def _pol(ctx: AnalysisResult) -> SecurityPolicy:
    return ctx.cfg.security if ctx.cfg is not None else SecurityPolicy()


def analyze_security(ctx: AnalysisResult) -> Tuple[Optional[float], List[Flag]]:
    pol = _pol(ctx)
    sec, holders, liq = ctx.security, ctx.holders, ctx.liquidity
    # 关键：适配器在无网络时返回「全字段 None 的空模型对象」，不能当成「无数据」。
    # 必须至少有一个真实信号（非全 None）才计分，否则视为缺失 → 排除出加权。
    has_sec = bool(sec) and any([
        sec.is_verified is not None, sec.is_mintable is not None,
        sec.can_take_back_ownership is not None, sec.buy_tax_pct is not None,
        sec.sell_tax_pct is not None, sec.hidden_honeypot is not None,
        sec.is_in_blacklist is not None,
        sec.is_proxy is not None, sec.can_blacklist is not None,
        sec.can_pause is not None, sec.has_owner_fn is not None,
    ])
    has_holders = bool(holders) and any([
        holders.total_holders is not None, holders.top10_pct is not None,
        holders.top50_pct is not None, holders.creator_pct is not None,
        holders.snipe_pct is not None,
    ])
    has_liq = bool(liq) and any([
        liq.total_liquidity_usd is not None, liq.locked_pct is not None,
        liq.is_burned is not None,
    ])
    if not (has_sec or has_holders or has_liq):
        return None, []
    pen = pol.penalties
    flags: List[Flag] = []
    score = 10.0

    # 致命
    if sec and sec.hidden_honeypot:
        flags.append(flag("bad", "HONEYPOT", "🚨 疑似 honeypot（买入后无法卖出）"))
        score = 0.0
    if sec and sec.is_in_blacklist:
        flags.append(flag("bad", "BLACKLISTED", "🚨 被列入风险/黑名单库"))
        score = 0.0

    # 高危
    if sec and sec.is_mintable:
        flags.append(flag("warn", "MINTABLE", "⚠️ 代币仍可被增发（mint 未禁用）"))
        score += pen.get("mint", -2.5)
    if sec and sec.can_take_back_ownership:
        flags.append(flag("warn", "OWNER_RECLAIMABLE", "⚠️ 可被收回所有权（owner 未放弃）"))
        score += pen.get("take_back", -2.5)
    if sec and max(sec.buy_tax_pct or 0, sec.sell_tax_pct or 0) > pol.tax_over_pct:
        flags.append(flag("warn", "TAX_OVER",
                          f"⚠️ 交易税异常（买 {sec.buy_tax_pct}%/卖 {sec.sell_tax_pct}%）"))
        score += pen.get("tax_over", -2.0)
    if sec and sec.is_verified is False:
        flags.append(flag("warn", "UNVERIFIED", "⚠️ 合约未开源验证"))
        score += pen.get("unverified", -1.5)
    # 字节码扫描特权函数风险（任意 EVM 链可读，不依赖索引器）
    if sec and sec.is_proxy:
        flags.append(flag("warn", "PROXY", "⚠️ 可升级代理合约（团队可替换实现 = 后门）"))
        score += pen.get("proxy", -2.5)
    if sec and sec.can_blacklist:
        flags.append(flag("warn", "CAN_BLACKLIST", "⚠️ 合约可拉黑地址（可阻止用户卖出）"))
        score += pen.get("blacklist_fn", -2.0)
    if sec and sec.can_pause:
        flags.append(flag("warn", "CAN_PAUSE", "⚠️ 合约可暂停交易（可冻结卖出）"))
        score += pen.get("pause", -1.5)
    # 正面证据（显式列出，避免「无红旗」被误读为「没检查」）
    if sec and sec.is_mintable is False:
        flags.append(flag("ok", "SUPPLY_FIXED", "✅ 未发现增发函数（供应量固定）"))
    if sec and sec.has_owner_fn is False:
        flags.append(flag("ok", "NO_OWNER_FN", "✅ 合约未实现 owner()（无管理员私钥）"))
    if sec and sec.is_proxy is False:
        flags.append(flag("ok", "NOT_PROXY", "✅ 非可升级代理（实现不可替换）"))
    if liq and liq.locked_pct is not None and liq.locked_pct < pol.lp_locked_min_pct:
        flags.append(flag("warn", "LP_LOW_LOCK", f"⚠️ LP 锁仓仅 {liq.locked_pct:.0f}%（ rug 风险）"))
        score += pen.get("lp_low_lock", -1.5)
    if liq and liq.is_burned is False:
        flags.append(flag("warn", "LP_NOT_BURNED", "⚠️ LP 未销毁（团队可撤池）"))
        score += pen.get("lp_not_burned", -1.0)

    # 中危
    if holders and holders.top10_pct is not None and holders.top10_pct > pol.top10_concentration_pct:
        flags.append(flag("warn", "TOP10_CONCENTRATED",
                          f"⚠️ 前 10 地址持仓 {holders.top10_pct:.0f}%（高度集中）"))
        score += pen.get("top10_concentrated", -1.5)
    if holders and holders.creator_pct is not None and holders.creator_pct > pol.creator_concentration_pct:
        flags.append(flag("warn", "CREATOR_CONCENTRATED",
                          f"⚠️ 创建者持仓 {holders.creator_pct:.0f}% 未披露锁定"))
        score += pen.get("creator_concentrated", -1.0)

    # 数据置信度折扣：无红旗但可核验字段极少 → 证据不足，不给满分
    known = [
        sec.is_verified, sec.owner_renounced, sec.is_mintable,
        sec.can_take_back_ownership, sec.buy_tax_pct, sec.sell_tax_pct,
        sec.hidden_honeypot, sec.is_in_blacklist,
        sec.is_proxy, sec.can_blacklist, sec.can_pause, sec.has_owner_fn,
    ] if sec else []
    coverage = sum(1 for v in known if v is not None)
    if holders and holders.total_holders is not None:
        coverage += 1
    if liq and liq.locked_pct is not None:
        coverage += 1
    if score >= 9.5 and coverage < pol.min_coverage_for_high:
        capped = pol.low_coverage_cap
        flags.append(flag("warn", "LOW_COVERAGE",
                          f"⚠️ 安全数据不完整（仅核验 {coverage} 项：owner/开源/mint/税率/"
                          f"honeypot/持币集中度/LP 锁仓多数未知），安全分按低置信度下调至 {capped:.1f}"))
        score = capped

    # 合约本身干净 ≠ 不会 rug：LP 锁仓与持币集中度仍是两个最大撤池/砸盘敞口。
    lp_unknown = (liq is None or liq.locked_pct is None)
    holders_unknown = (not has_holders) or (holders is None or holders.top10_pct is None)
    if lp_unknown and holders_unknown and score > pol.lp_unverified_cap:
        flags.append(flag("warn", "LP_UNVERIFIED",
                          "⚠️ LP 锁仓与持币集中度均未知：合约层面无后门，"
                          "但撤池（rug）与大户砸盘两大风险未经验证，"
                          f"安全分上限压至 {pol.lp_unverified_cap}"))
        score = pol.lp_unverified_cap

    return round(max(0.0, min(10.0, score)), 1), flags


def compute_security(ctx: AnalysisResult) -> Optional[float]:
    score, flags = analyze_security(ctx)
    if flags:
        ctx.flags.extend(flags)
        ctx.notes.setdefault("security", [f.msg for f in flags])
    return score
