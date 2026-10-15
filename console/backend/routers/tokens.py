"""E4 /api/tokens/{id} —— 币种档案（离线基线，纯本地）。

实时抓取（E10 /api/tokens/{id}/research）见 routers/research.py。
说明：早期设计的「币种列表 /api/tokens」端点已移除——前端无任何消费者
（币种检索由「百倍币雷达」排行榜与档案页路由承担），保留即死代码。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from core.envelope import failure, success
from data.schemas import CoinBrief, TokenDetailResponse
from services import history_svc
from services.token_svc import build_detail

router = APIRouter(tags=["tokens"])


@router.get("/api/tokens/{coin_id}")
def token_detail(
    coin_id: str,
    date: Optional[str] = Query(None, description="扫描日期 YYYY-MM-DD，缺省/ latest 取最新"),
) -> dict:
    detail = build_detail(coin_id, date)
    if detail is None:
        empty = TokenDetailResponse(basic=CoinBrief(id=coin_id), narrative={}, social={})
        return failure(404, f"未找到币种档案: {coin_id}", empty.model_dump())
    return success(detail.model_dump())


@router.get("/api/tokens/{coin_id}/twitter")
def token_twitter(
    coin_id: str,
    limit: int = Query(30, ge=1, le=100, description="返回条数上限"),
) -> dict:
    """E4-T Twitter 舆情：返回该币的推文 + 事件（来自豆包爬取的 Twitter 数据，已入库 content_archive）。

    库不可用 / 无数据 → 返回空列表（code=0），前端以空态降级，绝不 500。
    """
    posts = history_svc.query_twitter_content(coin_id, limit)
    return success({"coinId": coin_id, "count": len(posts), "posts": posts})
