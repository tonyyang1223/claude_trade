"""E3 /api/tokens（列表）、E4 /api/tokens/{id}（档案，离线基线）。

实时抓取（E10 /api/tokens/{id}/research）见 routers/research.py。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from core.envelope import failure, success
from data import loader
from data.schemas import CoinBrief, TokenDetailResponse
from services.common import coin_brief_from_light
from services.token_svc import build_detail

router = APIRouter(tags=["tokens"])


@router.get("/api/tokens")
async def list_tokens(
    date: Optional[str] = Query(None, description="扫描日期"),
    q: Optional[str] = Query(None, description="按 id/symbol/name 模糊搜索"),
    limit: int = Query(200, ge=1, le=800, description="返回条数"),
) -> dict:
    date = loader.resolve_scan_date(date)
    if not date:
        return success([], message="无可用扫描数据")
    coins = loader.load_all_coins(date)
    if q:
        ql = q.lower()
        coins = [c for c in coins if ql in str(c.get("id", "")).lower()
                 or ql in str(c.get("symbol", "")).lower()
                 or ql in str(c.get("name", "")).lower()]
    coins = sorted(coins, key=lambda x: (x.get("rank") or 999999))
    coins = coins[:limit]
    data = [coin_brief_from_light(c).model_dump() for c in coins]
    return success(data)


@router.get("/api/tokens/{coin_id}")
async def token_detail(
    coin_id: str,
    date: Optional[str] = Query(None, description="扫描日期"),
) -> dict:
    detail = build_detail(coin_id, date)
    if detail is None:
        empty = TokenDetailResponse(
            basic=CoinBrief(id=coin_id),
            narrative={}, social={},
        )
        return failure(404, f"未找到币种档案: {coin_id}", empty.model_dump())
    return success(detail.model_dump())
