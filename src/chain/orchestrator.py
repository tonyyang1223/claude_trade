"""编排层：把「链 + 查询」变成完整分析结果（设计文档 §3 执行 DAG）。

流程：解析地址 → 适配器/数据源抓取 → 八维评分（按类别权重） → 决策建议。
任意数据源失败都已降级，不会中断；缺失维度由 score() 排除出加权。
配置：analyze(..., config=None) 支持 dict / YAML 路径 / AnalysisConfig 对象；
缺省回落 config.py 内嵌默认（= 重构前现值，行为不变）。
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional, Tuple

from .adapters import get_adapter
from .advisor import decide
from .config import AnalysisConfig
from .dimensions import build_registry
from .scoring.pipeline import score
from .sources import get_quote, get_security_full, search_token
from .taxonomy import classify
from .types import AnalysisResult, Chain, LiquidityInfo, TokenProfile, TokenRef


def analyze(chain: str, query: str, *, rpc: Optional[str] = None,
            api_key: Optional[str] = None, demo: bool = False,
            config: object = None) -> Tuple[AnalysisResult, dict]:
    """入口：config 可为 AnalysisConfig / 配置 dict / YAML 路径 / None。"""
    cfg = AnalysisConfig.load(config)
    c = Chain.parse(chain)
    ctx = _demo(c, query, cfg) if demo else _live(c, query, rpc, api_key, cfg)
    ctx.cfg = cfg

    reg = build_registry()
    cat = classify(ctx)
    weights = cfg.weights_for(cat)
    total, scored, missing = score(reg, ctx, weights)
    ctx.missing = missing
    decision = decide(ctx, total, scored, missing)

    # 元数据（设计 §1.2 meta）：时间戳 / 引擎版本
    if ctx.fetched_at is None:
        ctx.fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return ctx, decision


def _live(c: Chain, query: str, rpc, api_key, cfg: AnalysisConfig) -> AnalysisResult:
    adapter = get_adapter(c.value, rpc, api_key)
    ref = adapter.resolve(query)
    addr = ref.address

    if not _looks_like_address(c, addr):
        found = search_token(c, query)
        if found and found.address:
            addr = found.address
            ref.symbol = ref.symbol or found.symbol
            ref.name = found.name
        else:
            ctx = AnalysisResult(chain=c, address=addr, symbol=ref.symbol, name=ref.name)
            ctx.error = "无法通过符号解析链上地址（DexScreener 未覆盖该链或代币）。请提供合约地址。"
            return ctx

    ctx = AnalysisResult(chain=c, address=addr, symbol=ref.symbol, name=ref.name,
                         sources_used=["rpc"])
    ctx.profile = adapter.get_token_profile(addr)
    ctx.dex = get_quote(
        c, addr,
        base_url=cfg.sources.dexscreener_base,
        floor_ratio=cfg.market.pair_floor_ratio,
        stable_bonus=cfg.market.stablecoin_bonus,
    )
    if ctx.dex:
        ctx.sources_used.append("dexscreener")

    # --- 身份回填：链上 profile → DEX 返回 ---
    if ctx.profile:
        ctx.symbol = ctx.symbol or ctx.profile.symbol
        ctx.name = ctx.name or ctx.profile.name
    if ctx.dex:
        ctx.symbol = ctx.symbol or ctx.dex.base_symbol
        ctx.name = ctx.name or ctx.dex.base_name

    # 价格一致性校验：price_usd × 总量 与 fdv 严重背离时，
    # 说明所选交易对计价币/报价异常，改用 fdv 反推的单价并打标。
    # 只使用链上真实 total_supply，不能用反推值（否则恒等于 fdv，循环论证）。
    if ctx.dex and ctx.profile and ctx.profile.total_supply:
        sup = ctx.profile.total_supply
        if ctx.dex.price_usd and ctx.dex.fdv:
            implied = ctx.dex.price_usd * sup
            if abs(implied - ctx.dex.fdv) / ctx.dex.fdv > cfg.market.price_anomaly_ratio:
                ctx.dex.price_anomaly = True
                ctx.dex.price_usd = round(ctx.dex.fdv / sup, 10)

    # --- profile 兜底：无 RPC 的链用 DEX 数据补全（仅展示）---
    if ctx.dex:
        derived_supply = (ctx.dex.fdv / ctx.dex.price_usd
                          if (ctx.dex.fdv and ctx.dex.price_usd) else None)
        if ctx.profile:
            ctx.profile.symbol = ctx.profile.symbol or ctx.dex.base_symbol
            ctx.profile.name = ctx.profile.name or ctx.dex.base_name
            ctx.profile.price_usd = ctx.profile.price_usd or ctx.dex.price_usd
            ctx.profile.market_cap = ctx.profile.market_cap or ctx.dex.market_cap
            ctx.profile.fdv = ctx.profile.fdv or ctx.dex.fdv
            ctx.profile.volume_24h = ctx.profile.volume_24h or ctx.dex.volume_24h
            if ctx.profile.age_days is None:
                ctx.profile.age_days = ctx.dex.age_days
            if ctx.profile.total_supply is None:
                ctx.profile.total_supply = derived_supply
        else:
            ctx.profile = TokenProfile(
                chain=c, address=addr,
                symbol=ctx.dex.base_symbol, name=ctx.dex.base_name,
                price_usd=ctx.dex.price_usd, market_cap=ctx.dex.market_cap,
                fdv=ctx.dex.fdv, volume_24h=ctx.dex.volume_24h,
                age_days=ctx.dex.age_days, total_supply=derived_supply,
            )
    gosec = get_security_full(c, addr, base_url=cfg.sources.goplus_base)
    if gosec:
        ctx.security, ctx.holders, lp = gosec
        ctx.sources_used.append("goplus")
        if lp and (lp.locked_pct is not None or lp.is_burned is not None):
            ctx.liquidity = lp
    else:
        ctx.security = adapter.get_contract_security(addr)
        ctx.holders = adapter.get_holders(addr)
    # LP 数据合并：GoPlus 无 LP 详情时用 DEX 报价填充流动性总额
    if ctx.liquidity is None and ctx.dex:
        ctx.liquidity = LiquidityInfo(
            total_liquidity_usd=ctx.dex.liquidity_usd, dex=ctx.dex.source)
    elif ctx.liquidity is not None and ctx.dex and ctx.liquidity.total_liquidity_usd is None:
        ctx.liquidity.total_liquidity_usd = ctx.dex.liquidity_usd
    return ctx


def _looks_like_address(c: Chain, addr: str) -> bool:
    if c == Chain.SOL:
        return bool(re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", addr or ""))
    return bool(addr) and addr.lower().startswith("0x") and len(addr) == 42


def _demo(c: Chain, query: str, cfg: AnalysisConfig) -> AnalysisResult:
    """内置样例（中等风险 Meme），让框架在无网络时也能端到端跑通。"""
    sym = (query or "CASHCAT").upper()
    ctx = AnalysisResult(
        chain=c,
        address="0xDemo0000000000000000000000000000000000",
        symbol=sym,
        name="Demo Cat",
        profile=_profile(c, sym),
        dex=_dex(),
        security=_sec(),
        holders=_holders(),
        liquidity=_liq(),
        sources_used=["demo"],
    )
    return ctx


def _profile(c, sym):
    return TokenProfile(chain=c, address="0xDemo", symbol=sym, name="Demo Cat",
                        total_supply=1e9, price_usd=0.045, market_cap=45e6,
                        volume_24h=8e6, fdv=45e6, age_days=40)


def _dex():
    from .types import DexQuote
    return DexQuote(price_usd=0.045, liquidity_usd=2_100_000, volume_24h=8_000_000,
                    buy_sell_ratio=1.15, price_change_24h=12.0, fdv=45e6,
                    source="dexscreener(demo)")


def _sec():
    from .types import ContractSecurity
    return ContractSecurity(is_verified=True, owner_renounced=True, is_mintable=False,
                            can_take_back_ownership=False, buy_tax_pct=0.0, sell_tax_pct=0.0,
                            hidden_honeypot=False, is_in_blacklist=False)


def _holders():
    from .types import HolderStats
    return HolderStats(total_holders=29_300, top10_pct=38.0, creator_pct=2.0, snipe_pct=8.0)


def _liq():
    return LiquidityInfo(total_liquidity_usd=2_100_000, locked_pct=82.0,
                         locked_until="2027-01-01", is_burned=False, dex="PancakeSwap")
