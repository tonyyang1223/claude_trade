"""E9 GET /api/macro/btc-dominance —— BTC 占比与市场规模判断（best-effort）。"""
from __future__ import annotations

from fastapi import APIRouter

from core.envelope import failure, success
from services.macro_svc import btc_dominance

router = APIRouter(tags=["macro"])


@router.get("/api/macro/btc-dominance")
async def btc_dominance() -> dict:
    data = btc_dominance()
    if not data.currentDominance:
        return failure(503, "BTC 占比暂不可用（可能为网络受限）", data.model_dump())
    return success(data.model_dump(), message="ok")
