"""百倍币机会雷达服务（启发式打分，纯本地）。

维度（均归一 0-100）：mcapScale / growth / narrative / community / onchain。
权重见 config.RADAR_WEIGHTS（初值，可调）。
composite = Σ(weightᵢ × dimᵢ) / Σ(weightᵢ) 仅对非空维度加权并归一到 0-100。
onchain 维在离线模式下置空（雷达不画该轴）。
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from core.config import RADAR_MCAP_CAP, RADAR_WEIGHTS
from data import loader
from data.schemas import OpportunityItem, OpportunityRadarResponse


def _deep_fields(coin_id: str, deep: Dict[str, dict]) -> dict:
    """从 top_50_detailed 提取叙事/社区相关计数。"""
    raw = deep.get(coin_id)
    if not raw:
        return {}
    src = raw.get("sources", {}) or {}
    soc = (src.get("social_stats", {}) or {}).get("data", {}) or {}
    cs = (src.get("community_score", {}) or {}).get("data", {}) or {}
    overall = soc.get("overall", {}) or {}
    reddit = soc.get("reddit", {}) or {}
    cs_break = cs.get("breakdown", {}) or {}
    return {
        "mentions": overall.get("mentions") or 0,
        "upvotes": overall.get("upvotes") or 0,
        "redditSubs": reddit.get("subscribers") or 0,
        "cscore": cs.get("community_score"),
        "newsCount": (cs_break.get("news", {}) or {}).get("mentions") or 0,
        "hasCategory": bool(raw.get("categories")),
    }


def compute(
    date: Optional[str] = None,
    mcap_max: Optional[float] = None,
    sort: str = "composite",
) -> OpportunityRadarResponse:
    date = loader.resolve_scan_date(date)
    if not date:
        return OpportunityRadarResponse(
            meta={"date": None, "count": 0, "weights": RADAR_WEIGHTS, "note": "无可用扫描数据"},
            rankings=[],
        )

    coins = loader.load_all_coins(date)
    if mcap_max is not None:
        coins = [c for c in coins if (c.get("market_cap") or 0) <= mcap_max]
    if not coins:
        return OpportunityRadarResponse(
            meta={"date": date, "count": 0, "weights": RADAR_WEIGHTS},
            rankings=[],
        )

    deep = loader.load_deep_raw(date)
    by_cat = loader.load_by_category_raw(date)
    cat_map: Dict[str, str] = {}
    for cat, members in by_cat.items():
        for m in members:
            cid = m.get("coin_id")
            if cid and cid not in cat_map:
                cat_map[cid] = cat

    max_mcap = max((c.get("market_cap") or 0) for c in coins) or 1.0

    # ---- 收集各维度原始值用于归一 ----
    raw_rows = []
    for c in coins:
        mcap = c.get("market_cap")
        chg7 = c.get("change_7d_pct") or 0.0
        vol = c.get("volume_24h") or 0.0
        vol_mcap = (vol / mcap) if mcap else 0.0
        df = _deep_fields(c["id"], deep)
        raw_rows.append({
            "id": c["id"],
            "sym": c.get("symbol"),
            "name": c.get("name"),
            "rank": c.get("rank"),
            "mcap": mcap,
            "chg7": chg7,
            "vol_mcap": vol_mcap,
            "df": df,
            "category": cat_map.get(c["id"]),
        })

    def _minmax(key):
        vals = [r[key] for r in raw_rows if r[key] is not None]
        return (min(vals), max(vals)) if vals else (0, 0)

    def _minmax_df(key):
        vals = [r["df"].get(key) for r in raw_rows if r["df"].get(key) is not None]
        return (min(vals), max(vals)) if vals else (0, 0)

    mm_chg7 = _minmax("chg7")
    mm_vm = _minmax("vol_mcap")
    mm_ment = _minmax_df("mentions")
    mm_news = _minmax_df("newsCount")
    mm_reddit = _minmax_df("redditSubs")
    mm_cscore = _minmax_df("cscore")

    def _norm(v, mm):
        lo, hi = mm
        if v is None or hi <= lo:
            return None
        return max(0.0, min(100.0, (v - lo) / (hi - lo) * 100.0))

    items: List[OpportunityItem] = []
    for r in raw_rows:
        dims: Dict[str, float] = {}
        df = r["df"]

        # mcapScale：小市值加分；>= 阈值或缺失则空
        if r["mcap"] and r["mcap"] < RADAR_MCAP_CAP and max_mcap > 1:
            try:
                ratio = math.log10(r["mcap"]) / math.log10(max_mcap)
            except ValueError:
                ratio = 1.0
            dims["mcapScale"] = max(0.0, min(100.0, 100.0 * (1.0 - ratio)))

        # growth：7d 涨跌 + 量额比
        n_chg = _norm(r["chg7"], mm_chg7)
        n_vm = _norm(r["vol_mcap"], mm_vm)
        if n_chg is not None or n_vm is not None:
            parts = [v for v in (n_chg, n_vm) if v is not None]
            dims["growth"] = sum(parts) / len(parts)

        # narrative：有分类 + 新闻/提及
        if df:
            n_news = _norm(df.get("newsCount"), mm_news)
            n_ment = _norm(df.get("mentions"), mm_ment)
            val = 40.0 if df.get("hasCategory") else 0.0
            val += 30.0 * (n_news if n_news is not None else 0.0) / 100.0
            val += 30.0 * (n_ment if n_ment is not None else 0.0) / 100.0
            dims["narrative"] = max(0.0, min(100.0, val))

        # community：reddit 订阅 + 社区分
        if df:
            n_red = _norm(df.get("redditSubs"), mm_reddit)
            n_csc = _norm(df.get("cscore"), mm_cscore)
            cparts = [v for v in (n_red, n_csc) if v is not None]
            if cparts:
                dims["community"] = sum(cparts) / len(cparts)

        # onchain：离线无链上数据 → 留空（雷达不画该轴）
        # composite：仅对非空维度加权并归一
        present = {k: v for k, v in dims.items() if k in RADAR_WEIGHTS}
        if not present:
            composite = 0.0
        else:
            w_sum = sum(RADAR_WEIGHTS[k] for k in present)
            composite = sum(RADAR_WEIGHTS[k] * present[k] for k in present) / w_sum if w_sum else 0.0

        items.append(OpportunityItem(
            id=r["id"],
            sym=r["sym"],
            name=r["name"],
            rank=r["rank"],
            mcap=r["mcap"],
            composite=round(composite, 2),
            dims={k: round(v, 2) for k, v in dims.items()},
            category=r["category"],
        ))

    sort_key = sort if sort in ("composite", "growth", "community", "mcapScale", "narrative") else "composite"
    items.sort(key=lambda x: x.dims.get(sort_key, 0.0) if sort_key != "composite" else x.composite, reverse=True)

    return OpportunityRadarResponse(
        meta={
            "date": date,
            "count": len(items),
            "weights": RADAR_WEIGHTS,
            "mcapCap": RADAR_MCAP_CAP,
            "sort": sort_key,
            "mcapMax": mcap_max,
        },
        rankings=items,
    )
