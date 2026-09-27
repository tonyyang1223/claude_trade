"""E6 POST /api/comparison —— 竞品对比（复用 src.analysis.comparison，可能触网）。"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Body

from core.envelope import failure, success
from services.compare_svc import compare

router = APIRouter(tags=["comparison"])


@router.post("/api/comparison")
def comparison(coin_ids: List[str] = Body(...)) -> dict:
    if not coin_ids or len(coin_ids) < 2:
        return failure(400, "至少需要 2 个币种进行对比")
    if len(coin_ids) > 5:
        return failure(400, "最多对比 5 个币种")
    data = compare(coin_ids)
    if not data.projects:
        return failure(503, data.summary or "对比分析暂不可用（可能为网络受限）", data.model_dump())
    return success(data.model_dump(), message="ok")
