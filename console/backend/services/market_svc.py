"""市场总览聚合服务（纯本地，零网络依赖）。

聚合 KPI / 涨跌分布 / 涨跌榜 / 市值榜 / 板块统计。
btcDominance 由 macro 服务 best-effort 填充，可能为空，不阻塞总览。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from data import loader
from data.schemas import CoinBrief, MarketOverviewResponse, SectorStat
from services.common import coin_brief_from_light


def build_meta(date: Optional[str] = None) -> dict:
    date = loader.resolve_scan_date(date)
    summary = loader.load_summary(date) if date else None
    ms = (summary or {}).get("market_stats", {}) or {}
    state = (summary or {}).get("state_stats", {}) or {}
    cats = (summary or {}).get("categories", {}) or {}
    return {
        "date": date,
        "prevDay": None,  # 由 overview 统一计算
        "scanTime": (summary or {}).get("scan_time"),
        "deepTotal": (summary or {}).get("deep_researched"),
        "lightTotal": (summary or {}).get("light_researched"),
        "coinCnt": ms.get("total_market_cap") and (summary or {}).get("total_coins"),
        "queueLen": state.get("queue_length"),
        "categoryCnt": len(cats) if isinstance(cats, dict) else None,
    }


def _btc_dominance_best_effort() -> Optional[float]:
    """best-effort 获取 BTC 占比（可能触网，失败返回 None，不阻塞）。"""
    try:
        from src.analysis.btc_dominance import BTCDominanceAnalyzer

        return float(BTCDominanceAnalyzer().analyze().current_dominance)
    except Exception as exc:  # noqa: BLE001
        print(f"[market_svc] BTC 占比获取失败（忽略）: {exc}")
        return None


def build_overview(date: Optional[str] = None) -> MarketOverviewResponse:
    date = loader.resolve_scan_date(date)
    if not date:
        return MarketOverviewResponse(
            meta={"date": None, "note": "无可用扫描数据"},
            kpi={},
            distribution={"labels": [], "values": []},
        )

    summary = loader.load_summary(date)
    ms = (summary or {}).get("market_stats", {}) or {}
    state = (summary or {}).get("state_stats", {}) or {}

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

    kpi = {
        "totalMcap": total_mcap,
        "coinCnt": len(coins),
        "avgChg": round(avg_chg, 4),
        "upCnt": up_cnt,
        "downCnt": down_cnt,
        "fearGreed": ms.get("fear_greed_index"),
        "btcDominance": _btc_dominance_best_effort(),
        "deepTotal": (summary or {}).get("deep_researched"),
    }

    meta = {
        "date": date,
        "prevDay": None,
        "scanTime": (summary or {}).get("scan_time"),
        "deepTotal": (summary or {}).get("deep_researched"),
        "lightTotal": (summary or {}).get("light_researched"),
        "queueLen": state.get("queue_length"),
        "categoryCnt": len((summary or {}).get("categories", {}) or {}),
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
        chgs = [p["chg24"] for p in parsed if p.get("chg24") is not None]
        out.append(SectorStat(
            cat=cat,
            count=len(parsed),
            mcap=sum(mcaps) if mcaps else None,
            avgChg=round(sum(chgs) / len(chgs), 4) if chgs else 0.0,
        ))
    out.sort(key=lambda x: -x.count)
    return out
