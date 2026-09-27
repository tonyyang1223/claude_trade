"""服务层共享工具：币种简表映射与归一化。"""
from __future__ import annotations

from typing import Optional

from data.schemas import CoinBrief


def coin_brief_from_light(c: dict) -> CoinBrief:
    """从 top_800_light 原始记录构造 CoinBrief。"""
    return CoinBrief(
        id=c["id"],
        sym=c.get("symbol"),
        name=c.get("name"),
        rank=c.get("rank"),
        price=c.get("price_usd"),
        mcap=c.get("market_cap"),
        vol=c.get("volume_24h"),
        chg24=(c.get("change_24h_pct") or 0.0),
        chg7d=(c.get("change_7d_pct") or 0.0),
    )


def coin_brief_from_market(mkt: dict, coin_id: Optional[str] = None) -> CoinBrief:
    """从 by_category / top_50_detailed 的 market.data 构造 CoinBrief。"""
    return CoinBrief(
        id=mkt.get("id") or coin_id,
        sym=mkt.get("symbol"),
        name=mkt.get("name"),
        rank=mkt.get("market_cap_rank"),
        price=mkt.get("current_price"),
        mcap=mkt.get("market_cap"),
        vol=mkt.get("total_volume"),
        chg24=(mkt.get("price_change_percentage_24h") or 0.0),
        chg7d=0.0,
    )
