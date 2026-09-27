"""E5 /api/opportunity/radar —— 百倍币机会雷达（纯本地启发式）。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from core.envelope import success
from services.opportunity_svc import compute

router = APIRouter(tags=["opportunity"])


@router.get("/api/opportunity/radar")
async def opportunity_radar(
    date: Optional[str] = Query(None, description="扫描日期"),
    mcapMax: Optional[float] = Query(None, description="市值上限过滤（USD）"),
    sort: str = Query("composite", description="排序: composite|growth|community|mcapScale|narrative"),
) -> dict:
    data = compute(date, mcap_max=mcapMax, sort=sort)
    return success(data.model_dump())
