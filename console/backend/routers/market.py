"""E3 /api/market/overview —— 市场总览（纯本地）。

板块统计已包含在 overview 的 ``sectors`` 字段内，故不单独提供 /api/sectors。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from core.envelope import success
from services.market_svc import build_overview

router = APIRouter(tags=["market"])


@router.get("/api/market/overview")
def market_overview(
    date: Optional[str] = Query(None, description="扫描日期 YYYY-MM-DD，缺省/ latest 取最新"),
) -> dict:
    data = build_overview(date)
    return success(data.model_dump())
