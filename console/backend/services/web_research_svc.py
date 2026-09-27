"""实时网页研究服务（薄封装 src.research.web_research）。

POST /api/tokens/{id}/research 同步触发；带超时（默认 25s），失败保留离线基线并提示，
不阻塞首屏。返回的 WebResearchResponse 由前端合并到币种档案。
"""
from __future__ import annotations

import threading
from typing import Optional, Tuple

from core.config import WEB_RESEARCH_TIMEOUT
from data.schemas import NewsItem, WebResearchResponse


def _run_with_timeout(func, timeout: float) -> Tuple[bool, object]:
    """在线程中运行 func，超时返回 (False, None)。"""
    box: dict = {"result": None, "done": False}

    def _target():
        try:
            box["result"] = func()
        except Exception as exc:  # noqa: BLE001
            box["result"] = exc
        box["done"] = True

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout)
    if not box["done"]:
        return False, None
    return True, box["result"]


def research(coin_id: str, force: bool = False, timeout: float = WEB_RESEARCH_TIMEOUT) -> Tuple[WebResearchResponse, str]:
    """执行实时网页研究。

    Returns:
        (WebResearchResponse, message)：message 在失败时给出说明，调用方据此向用户提示。
    """
    def _do():
        from src.research.web_research import TokenWebResearcher

        researcher = TokenWebResearcher()
        return researcher.analyze(coin_id)

    ok, result = _run_with_timeout(_do, timeout)
    if not ok:
        empty = WebResearchResponse(coinId=coin_id)
        return empty, f"实时抓取超时（>{timeout:.0f}s），已保留离线基线"

    if isinstance(result, Exception):
        empty = WebResearchResponse(coinId=coin_id)
        return empty, f"实时抓取失败：{result}，已保留离线基线"

    try:
        p = result
        news = [NewsItem(**n).model_dump() for n in (p.news or [])]
        resp = WebResearchResponse(
            coinId=p.coin_id,
            symbol=p.symbol,
            name=p.name,
            description=p.description,
            categories=p.categories or [],
            officialLinks=p.official_links or {},
            communityLinks=p.community_links or {},
            sentiment=p.sentiment or {},
            watchlistUsers=p.watchlist_users,
            news=news,
            sources=p.sources or [],
            confidence=p.confidence or 0.0,
            fetchedAt=p.fetched_at,
        )
        return resp, "ok"
    except Exception as exc:  # noqa: BLE001
        empty = WebResearchResponse(coinId=coin_id)
        return empty, f"实时抓取结果解析失败：{exc}，已保留离线基线"
