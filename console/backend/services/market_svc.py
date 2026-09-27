"""市场总览聚合服务（纯本地，零网络依赖）。

聚合 KPI / 涨跌分布 / 涨跌榜 / 市值榜 / 板块统计，并提供 /api/meta 元信息。
BTC 占比不在此处获取（避免总览触网），由 ``/api/macro/btc-dominance`` 单独提供。
"""
from __future__ import annotations

from collections import defaultdict
from typing import List, Optional

from data import loader
from data.schemas import MarketOverviewResponse, SectorStat
from services.common import coin_brief_from_light


def build_meta(date: Optional[str] = None) -> dict:
    """构造 /api/meta 的数据元信息（纯本地）。"""
    date = loader.resolve_scan_date(date)
    summary = loader.load_summary(date) if date else None
    coins = loader.load_all_coins(date) if date else []
    return {
        "date": date,
        "scanTime": (summary or {}).get("scan_time"),
        "deepTotal": (summary or {}).get("deep_researched"),
        "lightTotal": (summary or {}).get("light_researched"),
        "coinCnt": len(coins) or None,
    }


def build_overview(date: Optional[str] = None) -> MarketOverviewResponse:
    date = loader.resolve_scan_date(date)
    if not date:
        return MarketOverviewResponse(
            meta={"date": None, "note": "无可用扫描数据"},
            kpi={},
            distribution={"labels": [], "values": []},
        )

    summary = loader.load_summary(date)

    coins = loader.load_all_coins(date)
    if not coins:
        return MarketOverviewResponse(
            meta={"date": date, "note": "该日期无币种快照"},
            kpi={},
            distribution={"labels": [], "values": []},
        )

    total_mcap = sum((c.get("market_cap") or 0) for c in coins)
    avg_chg = sum((c.get("change_24h_pct") or 0) for c in coins) / len(coins)
    up_cnt = sum(1 for c in coins if (c.get("change_24h_pct") or 0) > 0)
    down_cnt = sum(1 for c in coins if (c.get("change_24h_pct") or 0) < 0)

    # 涨跌分布直方图（2% 一档，截断 ±20%）
    bins = list(range(-20, 22, 2))
    hist = defaultdict(int)
    for c in coins:
        b = max(-20, min(20, c["change_24h_pct"]))
        idx = int((b + 20) // 2)
        hist[bins[min(idx, len(bins) - 2)]] += 1
    dist_labels = [f"{bins[i]:+d}%~{bins[i+1]:+d}%" for i in range(len(bins) - 1)]
    dist_values = [hist[bins[i]] for i in range(len(bins) - 1)]

    gainers = sorted([c for c in coins if c.get("rank") and c["rank"] <= 300],
                     key=lambda x: -(x.get("change_24h_pct") or 0))[:15]
    losers = sorted([c for c in coins if c.get("rank") and c["rank"] <= 300],
                    key=lambda x: (x.get("change_24h_pct") or 0))[:15]
    top_by_mcap = sorted(coins, key=lambda x: -(x.get("market_cap") or 0))[:15]

    # 不提供 fearGreed：summary.market_stats.fear_greed_index 在全部已采集日期恒为
    # null（采集端未落盘），前端亦无该卡位；BTC 占比由 /api/macro 单独提供。
    kpi = {
        "totalMcap": total_mcap,
        "coinCnt": len(coins),
        "avgChg": round(avg_chg, 4),
        "upCnt": up_cnt,
        "downCnt": down_cnt,
        "deepTotal": (summary or {}).get("deep_researched"),
    }

    meta = {
        "date": date,
        "scanTime": (summary or {}).get("scan_time"),
        "deepTotal": (summary or {}).get("deep_researched"),
        "lightTotal": (summary or {}).get("light_researched"),
    }

    return MarketOverviewResponse(
        meta=meta,
        kpi=kpi,
        distribution={"labels": dist_labels, "values": dist_values},
        gainers=[coin_brief_from_light(c) for c in gainers],
        losers=[coin_brief_from_light(c) for c in losers],
        topByMcap=[coin_brief_from_light(c) for c in top_by_mcap],
        sectors=build_sectors(date),
    )


def build_sectors(date: Optional[str] = None) -> List[SectorStat]:
    """板块统计（币数 / 总市值 / 平均24h涨跌）。"""
    date = loader.resolve_scan_date(date)
    if not date:
        return []
    raw = loader.load_by_category_raw(date)
    out: List[SectorStat] = []
    for cat, members in raw.items():
        parsed = []
        for j in members:
            src = (j.get("sources") or {}).get("market", {}) or {}
            mkt = src.get("data", {}) or {}
            if not mkt:
                continue
            parsed.append({
                "mcap": mkt.get("market_cap"),
                "chg24": mkt.get("price_change_percentage_24h") or 0,
            })
        if not parsed:
            continue
        mcaps = [p["mcap"] for p in parsed if p.get("mcap")]
        chgs = [p["chg24"] for p in parsed if p["chg24"] is not None]
        out.append(SectorStat(
            cat=cat,
            count=len(parsed),
            mcap=sum(mcaps) if mcaps else None,
            avgChg=round(sum(chgs) / len(chgs), 4) if chgs else 0.0,
        ))
    out.sort(key=lambda x: -x.count)
    return out
