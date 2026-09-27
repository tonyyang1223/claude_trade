"""币种档案服务（离线基线，纯本地）。

读取 top_50_detailed / by_category 的原始记录，构造 TokenDetailResponse。
实时叙事/新闻由 web_research_svc（E10）独立提供并合并到前端。
"""
from __future__ import annotations

from typing import Optional

from data import loader
from data.schemas import CoinBrief, NewsItem, TokenDetailResponse
from services.common import coin_brief_from_market


def _dig(raw: dict, *path, default=None):
    cur = raw
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur if cur is not None else default


def build_detail(coin_id: str, date: Optional[str] = None) -> Optional[TokenDetailResponse]:
    date = loader.resolve_scan_date(date)
    if not date:
        return None

    raw = loader.find_coin_raw(date, coin_id)
    if not raw:
        return None

    src = raw.get("sources", {}) or {}
    mkt = (src.get("market", {}) or {}).get("data", {}) or {}
    soc = (src.get("social_stats", {}) or {}).get("data", {}) or {}
    cs = (src.get("community_score", {}) or {}).get("data", {}) or {}
    sent = (src.get("sentiment", {}) or {}).get("data", {}) or {}

    overall = soc.get("overall", {}) or {}
    reddit = soc.get("reddit", {}) or {}
    cs_break = cs.get("breakdown", {}) or {}

    basic = coin_brief_from_market(
        mkt,
        coin_id=coin_id,
    )
    # 用顶层字段兜底（by_category 顶层有 symbol/name/rank）
    basic.sym = basic.sym or raw.get("symbol")
    basic.name = basic.name or raw.get("name")
    basic.rank = basic.rank or raw.get("rank")

    narrative = {
        "description": None,
        "categories": raw.get("categories") or [],
        "genesisDate": None,
        "officialLinks": {},
        "communityLinks": {},
    }

    social = {
        "mentions": overall.get("mentions") or 0,
        "upvotes": overall.get("upvotes") or 0,
        "redditSubs": reddit.get("subscribers") or 0,
        "communityScore": cs.get("community_score"),
        "newsCount": (cs_break.get("news", {}) or {}).get("mentions") or 0,
        "biliCount": (cs_break.get("bilibili", {}) or {}).get("video_count") or 0,
        "sentiment": {
            "overall": sent.get("overall_sentiment"),
            "fearGreed": (sent.get("fear_greed") or {}).get("value"),
            "combinedScore": sent.get("combined_score"),
        },
        "signal": overall.get("signal"),
    }

    return TokenDetailResponse(
        basic=basic,
        ath=mkt.get("ath"),
        athChg=mkt.get("ath_change_percentage"),
        narrative=narrative,
        social=social,
        news=[],  # 离线基线：新闻计数驱动在 social.newsCount；实时列表由 E10 填充
        scoresAvailable=False,
        onchainAvailable=False,
        dataSource="offline",
    )
