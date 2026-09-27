"""E8 GET /api/score/{id} —— 综合评分与建议（复用 src.analysis.scorer，可能触网）。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from core.envelope import failure, success
from services.score_svc import score

router = APIRouter(tags=["score"])


@router.get("/api/score/{coin_id}")
async def score_coin(
    coin_id: str,
    date: Optional[str] = Query(None, description="扫描日期（预留，评分主要走实时源）"),
) -> dict:
    data = score(coin_id, date)
    if not data.scores:
        return failure(503, "评分暂不可用（可能为网络受限，未取到数据）", data.model_dump())
    return success(data.model_dump(), message="ok")
