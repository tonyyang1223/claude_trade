"""E7 GET /api/onchain —— 链上分析（复用 src.chain，可能触网或走 demo）。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from core.envelope import failure, success
from services.chain_svc import analyze

router = APIRouter(tags=["onchain"])


@router.get("/api/onchain")
async def onchain(
    chain: str = Query(..., description="链名: bnb / sol / robinhood"),
    query: str = Query(..., description="代币符号或合约地址"),
    demo: bool = Query(False, description="离线样例模式（不触网）"),
) -> dict:
    data = analyze(chain, query, demo=demo)
    if not data.decision:
        return failure(503, data.disclaimer or "链上分析暂不可用（可能为网络受限或地址无法解析）", data.model_dump())
    return success(data.model_dump(), message="ok")
