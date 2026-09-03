"""DexScreener 数据源（跨链 DEX 价格 / 流动性 / 买卖比 / Meme 多周期动量）。

- get_quote(chain, address)：按地址取「最可信」交易对报价
- search_token(chain, symbol)：符号搜索 → 最佳匹配 TokenRef（含地址）

链选择策略（修复「无脑取最高流动性 pair 导致价格错乱」）：
  优先选择以稳定币 / 主流币（USDC/USDT/BUSD/WBNB/BNB/ETH/SOL…）计价的交易对，
  其次按流动性排序。这样价格/涨跌/买卖比都来自同一可信计价对，避免被 obscure 计价币污染。
  同时记录 quote_symbol，并在报告中明示「价格以 X 计价」。

注意：DexScreener 已确认覆盖 robinhood 链（2026-09-03 实测 STRATTON 返回 30 个交易对）。
未覆盖的链会返回空 pairs，由编排层提示用户改用链地址。
"""
from __future__ import annotations

import time
from typing import Dict, Optional

import requests

from ..types import Chain, DexQuote, TokenRef

_BASE = "https://api.dexscreener.com/latest/dex"
_CHAIN_LABEL = {Chain.BNB: "bsc", Chain.SOL: "solana", Chain.ROBINHOOD: "robinhood"}

# 可信计价币白名单（价格/USD 换算可靠）
# 含主流稳定币与公链原生币；Robinhood 链上的 USDG(Global Dollar) 亦为稳定币
_STABLE = {
    "usdc", "usdt", "busd", "dai", "usde", "fdusd", "tusd", "usdc.e",
    "wbnbb", "wbnb", "bnb", "eth", "weth", "sol", "wsol",
    "usdg", "usds", "usd+", "gho", "lusd", "susd", "frax", "pyusd", "usdf",
}


def _ranked_pairs(pairs: list, *, floor_ratio: float = 0.10,
                  stable_bonus: float = 1.15) -> list:
    """主盘识别：流动性门槛过滤 → 成交量主排序 → 稳定币温和加成 → 流动性次之。

    修复要点（2026-09-03 实测 Robinhood STRATTON）：
    旧实现给稳定/主流计价对 +1e12 硬加成，导致「只要计价币是 ETH/USDT，
    哪怕流动性只有主盘 14% 的死对也会被选中」。规则改为：

      1) 先按「>= 最大流动性 floor_ratio」过滤掉尘埃边缘对；
      2) 以 24h 成交量为主排序（成交量 = 真实成交发生地）；
      3) 稳定币计价仅作 stable_bonus(1.15x) 温和加成（质量偏好，非硬覆盖）；
      4) 流动性作为附加项参与排序。

    floor_ratio / stable_bonus 可由配置覆盖（MarketConfig.pair_*）。
    """
    liqs = [((p.get("liquidity") or {}).get("usd") or 0) for p in pairs]
    max_liq = max(liqs) if liqs else 0
    floor = max_liq * floor_ratio
    eligible = [p for p in pairs if ((p.get("liquidity") or {}).get("usd") or 0) >= floor]
    if not eligible:
        eligible = pairs

    def score(p):
        vol = (p.get("volume") or {}).get("h24") or 0
        liq = (p.get("liquidity") or {}).get("usd") or 0
        stable = stable_bonus if _quote_sym(p) in _STABLE else 1.0
        return vol * stable + liq

    return sorted(eligible, key=score, reverse=True)


def _quote_sym(pair: dict) -> str:
    return (pair.get("quoteToken") or {}).get("symbol", "").lower()


def _bsr(pair: dict) -> Optional[float]:
    txns = (pair.get("txns") or {}).get("h24") or {}
    buys = txns.get("buys") or 0
    sells = txns.get("sells") or 0
    if not sells:
        return None
    return round(buys / sells, 3)


def get_quote(chain: Chain, address: str, timeout: int = 15, *,
              base_url: Optional[str] = None,
              floor_ratio: Optional[float] = None,
              stable_bonus: Optional[float] = None) -> Optional[DexQuote]:
    base = base_url or _BASE
    try:
        r = requests.get(f"{base}/tokens/{address}", timeout=timeout).json()
    except Exception:  # noqa: BLE001
        return None
    pairs = r.get("pairs") or []
    if not pairs:
        return None
    pairs = _ranked_pairs(pairs,
                          floor_ratio=floor_ratio if floor_ratio is not None else 0.10,
                          stable_bonus=stable_bonus if stable_bonus is not None else 1.15)
    p = pairs[0]
    qsym = _quote_sym(p)

    pc = p.get("priceChange") or {}
    price_changes = {
        k: pc.get(k) for k in ("m5", "h1", "h6", "h24") if pc.get(k) is not None
    }
    raw_txns = p.get("txns") or {}
    txns = {
        k: {"buys": (raw_txns.get(k) or {}).get("buys"),
            "sells": (raw_txns.get(k) or {}).get("sells")}
        for k in ("m5", "h1", "h6", "h24")
    }
    created = p.get("pairCreatedAt")
    age_days = round((time.time() * 1000 - created) / 86_400_000, 1) if created else None

    info = p.get("info") or {}
    socials = [s.get("url") for s in (info.get("socials") or []) if s.get("url")]

    return DexQuote(
        price_usd=float(p.get("priceUsd") or 0) or None,
        liquidity_usd=(p.get("liquidity") or {}).get("usd"),
        volume_24h=(p.get("volume") or {}).get("h24"),
        buy_sell_ratio=_bsr(p),
        price_change_24h=pc.get("h24"),
        fdv=p.get("fdv"),
        market_cap=p.get("marketCap"),
        pair_address=p.get("pairAddress"),
        quote_symbol=qsym or None,
        base_symbol=(p.get("baseToken") or {}).get("symbol"),
        base_name=(p.get("baseToken") or {}).get("name"),
        source="dexscreener",
        price_changes=price_changes,
        txns=txns,
        age_days=age_days,
        socials=socials,
        image_url=info.get("imageUrl"),
    )


def search_token(chain: Chain, symbol: str, timeout: int = 15, *,
                 base_url: Optional[str] = None) -> Optional[TokenRef]:
    label = _CHAIN_LABEL.get(chain)
    if not label:
        return None  # Robinhood 未覆盖
    base = base_url or _BASE
    try:
        r = requests.get(f"{base}/search", params={"q": symbol}, timeout=timeout).json()
    except Exception:  # noqa: BLE001
        return None
    pairs = r.get("pairs") or []
    cands = [
        p for p in pairs
        if p.get("chainId") == label
        and (p.get("baseToken") or {}).get("symbol", "").upper() == symbol.upper()
    ]
    if not cands:
        return None
    cands = _ranked_pairs(cands)
    best = cands[0]
    return TokenRef(
        chain=chain,
        address=(best.get("baseToken") or {}).get("address") or "",
        symbol=(best.get("baseToken") or {}).get("symbol"),
        name=(best.get("baseToken") or {}).get("name"),
    )
