"""E8 GET /api/score/{id} —— 综合评分与建议（复用 src.analysis.scorer，可能触网）。"""
from __future__ import annotations

from fastapi import APIRouter

from core.envelope import failure, success
from services.score_svc import score

router = APIRouter(tags=["score"])


@router.get("/api/score/{coin_id}")
def score_coin(coin_id: str) -> dict:
    data = score(coin_id)
    if not data.scores:
        return failure(503, "评分暂不可用（可能为网络受限，未取到数据）", data.model_dump())
    return success(data.model_dump(), message="ok")
