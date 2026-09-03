"""GoPlus Security 数据源（多链安全审计）。

覆盖：bnb(56) / solana(专属端点)。Robinhood Chain 为 Arbitrum Orbit 系，
GoPlus 未单列，返回 None，由编排层降级到链上 owner() 探测。

端点可通过 base_url 覆盖（缺省回落默认端点）；返回 (ContractSecurity, HolderStats)。
设计（skill_design.md §5.4）：补映射 lp_holders/launchpad_token/owner_balance 等
高价值字段（holder 集中的 LP 锁死 / four.meme 发射台信号）。
"""
from __future__ import annotations

from typing import Optional, Tuple

import requests

from ..types import Chain, ContractSecurity, HolderStats, LiquidityInfo

_DEFAULT_BASE = "https://api.gopluslabs.io/api/v1"
_EVM_CHAIN_ID = {Chain.BNB: 56}


def get_security(chain: Chain, address: str, timeout: int = 15,
                 base_url: Optional[str] = None
                 ) -> Optional[Tuple[ContractSecurity, HolderStats]]:
    """兼容包装：返回 (security, holders) 二元组（丢弃 LP 详情）。"""
    full = get_security_full(chain, address, timeout, base_url)
    return None if full is None else (full[0], full[1])


def get_security_full(chain: Chain, address: str, timeout: int = 15,
                      base_url: Optional[str] = None
                      ) -> Optional[Tuple[ContractSecurity, HolderStats, Optional[LiquidityInfo]]]:
    base = base_url or _DEFAULT_BASE
    if chain == Chain.SOL:
        url = f"{base}/solana/token_security/{address}"
    elif chain in _EVM_CHAIN_ID:
        url = f"{base}/token_security/{_EVM_CHAIN_ID[chain]}?contract_addresses={address}"
    else:
        return None  # Robinhood 不支持，降级

    try:
        r = requests.get(url, timeout=timeout).json()
    except Exception:  # noqa: BLE001
        return None
    result = r.get("result") or {}
    if isinstance(result, dict) and address.lower() in {k.lower() for k in result}:
        result = next(v for k, v in result.items() if k.lower() == address.lower())
    if not isinstance(result, dict):
        return None

    lp_liq = _lp_liquidity(result)
    sec, holders = _to_models(result)
    return sec, holders, lp_liq


def _to_models(result: dict) -> Tuple[ContractSecurity, HolderStats]:
    sec = ContractSecurity(
        is_verified=_as_bool(result.get("is_open_source")),
        can_take_back_ownership=_as_bool(result.get("can_take_back_ownership")),
        is_mintable=_as_bool(result.get("is_mintable")),
        hidden_honeypot=_as_bool(result.get("hidden_honeypot")),
        buy_tax_pct=_as_pct(result.get("buy_tax")),
        sell_tax_pct=_as_pct(result.get("sell_tax")),
        is_in_blacklist=_as_bool(result.get("is_honeypot")),
        is_proxy=_as_bool(result.get("is_proxy")),
        can_blacklist=_as_bool(result.get("is_blacklisted")),
        can_pause=_as_bool(result.get("transfer_pausable")),
        has_owner_fn=None,
        owner_renounced=_owner_renounced(result.get("owner_address")),
    )
    holders = HolderStats(
        total_holders=_as_int(result.get("holder_count")),
        top10_pct=_as_pct(result.get("top_10_holder_percent")),
        top50_pct=_as_pct(result.get("top_50_holder_percent")),
        creator_pct=_as_pct(result.get("creator_percent")),
        snipe_pct=None,
    )
    return sec, holders


def _lp_liquidity(result: dict) -> Optional[LiquidityInfo]:
    """从 GoPlus lp_holders 推导 LP 锁死状态（设计 §5.4 强信号）。

    lp_holders[].is_locked==1 或地址为 0xdead / 0x0000 → 视为 LP 已烧毁/锁定。
    注意：lp_total_supply 是 LP Token 数量（非美元），故不写入 total_liquidity_usd，
    该字段留给编排层用 DexScreener 美元报价填充。
    """
    lp_list = result.get("lp_holders") or []
    if not lp_list:
        return None
    dead = {"0x000000000000000000000000000000000000dead",
            "0x0000000000000000000000000000000000000000"}
    locked_share = sum(
        float(h.get("percent") or 0)
        for h in lp_list
        if (h.get("is_locked") in (1, "1", True) or str(h.get("address", "")).lower() in dead)
    )
    if not locked_share:
        return None
    return LiquidityInfo(
        total_liquidity_usd=None,          # LP token 数量 ≠ 美元，不误填
        locked_pct=round(locked_share * 100, 2) if locked_share else None,
        is_burned=locked_share >= 0.99,
        dex="goplus",
    )


def _owner_renounced(v) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, str) and v.lower() in {
        "0x0000000000000000000000000000000000000000",
        "0x000000000000000000000000000000000000dead",
    }:
        return True
    return False


def _as_bool(v) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, str):
        return v.lower() in ("true", "1", "yes")
    return bool(v)


def _as_pct(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _as_int(v) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None
