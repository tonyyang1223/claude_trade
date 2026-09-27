"""E2 /api/market/overview、/api/sectors —— 市场总览与板块（纯本地）。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from core.envelope import success
from services.market_svc import build_overview, build_sectors

router = APIRouter(tags=["market"])


@router.get("/api/market/overview")
async def market_overview(date: Optional[str] = Query(None, description="扫描日期 YYYY-MM-DD，缺省/ latest 取最新")) -> dict:
    data = build_overview(date)
    return success(data.model_dump())


@router.get("/api/sectors")
async def sectors(date: Optional[str] = Query(None, description="扫描日期 YYYY-MM-DD，缺省/ latest 取最新")) -> dict:
    data = build_sectors(date)
    return success([s.model_dump() for s in data])
