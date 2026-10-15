"""币种档案服务（离线基线，纯本地）。

读取 top_50_detailed / by_category 的原始记录，构造 TokenDetailResponse。
实时叙事/新闻由 web_research_svc（E10）独立提供并合并到前端。
"""
from __future__ import annotations

from typing import Optional

from data import loader
from data.schemas import TokenDetailResponse
from services.common import coin_brief_from_market, coin_brief_from_light


def build_detail(coin_id: str, date: Optional[str] = None) -> Optional[TokenDetailResponse]:
    date = loader.resolve_scan_date(date)
    if not date:
        return None

    raw = loader.find_coin_raw(date, coin_id)
    if not raw:
        # 兜底：币种仅存在于 top_800_light（如聚合币 memecoin-2，排名 51+），
        # 无 detailed/by_category 记录时，用 light 记录至少渲染基础行情，避免 404 白页。
        light = next(
            (c for c in (loader.load_all_coins(date) or []) if c.get("id") == coin_id),
            None,
        )
        if light:
            basic = coin_brief_from_light(light)
            return TokenDetailResponse(basic=basic, narrative={}, social={}, news=[])
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

    # 离线基线只填「扫描数据里真实存在」的字段：description / genesisDate / 官方与社区
    # 链接在 daily_scan 中并未落盘，由 E10 实时抓取补全，故此处不再预置恒为 None/{}
    # 的占位键（前端以可选链读取，缺键与空值等价）。
    narrative = {
        "categories": raw.get("categories") or [],
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
        # 离线基线 news 恒为空：新闻计数见 social.newsCount，实时列表由 E10 填充
        news=[],
    )
