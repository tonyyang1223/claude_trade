"""E10 POST /api/tokens/{id}/research —— 实时网页研究（同步触发，超时容错）。

失败保留离线基线并提示，不阻塞首屏。返回 WebResearchResponse + message。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body

from core.envelope import failure, success
from services.web_research_svc import research

router = APIRouter(tags=["research"])


@router.post("/api/tokens/{coin_id}/research")
async def token_research(coin_id: str, payload: Optional[dict] = Body(default=None)) -> dict:
    force = bool((payload or {}).get("force", False)) if payload else False
    resp, message = research(coin_id, force=force)
    if message != "ok":
        return failure(503, message, resp.model_dump())
    return success(resp.model_dump(), message="ok")
