"""E10 POST /api/tokens/{id}/research —— 实时网页研究（同步触发，超时容错）。

失败保留离线基线并提示，不阻塞首屏。返回 WebResearchResponse + message。
请求体为空（无 force 开关，见 services.web_research_svc 说明）。
"""
from __future__ import annotations

from fastapi import APIRouter

from core.envelope import failure, success
from services.web_research_svc import research

router = APIRouter(tags=["research"])


@router.post("/api/tokens/{coin_id}/research")
def token_research(coin_id: str) -> dict:
    resp, message = research(coin_id)
    if message != "ok":
        return failure(503, message, resp.model_dump())
    return success(resp.model_dump(), message="ok")
