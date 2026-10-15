"""
轻量代币硬数据采集：直接调 CoinGecko / DefiLlama，绕开项目 factor 栈。
输出 JSON 到 reports/_raw_hard_data.json
"""
import json
import ssl
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

# CoinGecko coin_id 映射
COINS = {
    "TAO": "bittensor",
    "FET": "fetch-ai",
    "RENDER": "render-token",
    "WLD": "worldcoin-wld",
    "AGIX": "singularitynet",
    "REI": "origin-trail",  # placeholder, will be removed if not needed
}
# 只保留真正的 AI 竞品
COINS = {
    "TAO": "bittensor",
    "FET": "fetch-ai",
    "RENDER": "render-token",
    "WLD": "worldcoin-wld",
    "AGIX": "singularitynet",
    "AKT": "akash-network",
}

CG = "https://api.coingecko.com/api/v3"


def cg_get(path, params=None):
    url = f"{CG}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_coin(cg_id):
    """拉单币种市场数据。"""
    data = cg_get(f"/coins/{cg_id}", params={
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false",
    })
    md = data.get("market_data", {})
    return {
        "id": data.get("id"),
        "symbol": (data.get("symbol") or "").upper(),
        "name": data.get("name"),
        "market_cap_rank": data.get("market_cap_rank"),
        "current_price_usd": md.get("current_price", {}).get("usd"),
        "market_cap_usd": md.get("market_cap", {}).get("usd"),
        "fully_diluted_valuation_usd": md.get("fully_diluted_valuation", {}).get("usd"),
        "total_volume_usd": md.get("total_volume", {}).get("usd"),
        "high_24h_usd": md.get("high_24h", {}).get("usd"),
        "low_24h_usd": md.get("low_24h", {}).get("usd"),
        "price_change_pct_1h": md.get("price_change_percentage_1h_in_currency", {}).get("usd"),
        "price_change_pct_24h": md.get("price_change_percentage_24h"),
        "price_change_pct_7d": md.get("price_change_percentage_7d"),
        "price_change_pct_30d": md.get("price_change_percentage_30d"),
        "price_change_pct_1y": md.get("price_change_percentage_1y"),
        "ath_usd": md.get("ath", {}).get("usd"),
        "ath_date": md.get("ath_date", {}).get("usd"),
        "ath_change_pct": md.get("ath_change_percentage", {}).get("usd"),
        "atl_usd": md.get("atl", {}).get("usd"),
        "atl_date": md.get("atl_date", {}).get("usd"),
        "circulating_supply": md.get("circulating_supply"),
        "total_supply": md.get("total_supply"),
        "max_supply": md.get("max_supply"),
        "last_updated": md.get("last_updated"),
    }


def main():
    out = {}
    for sym, cg_id in COINS.items():
        print(f"[+] fetching {sym} ({cg_id}) ...", flush=True)
        try:
            out[sym] = fetch_coin(cg_id)
        except Exception as e:
            print(f"    !! failed: {e}", flush=True)
            out[sym] = {"error": str(e), "id": cg_id}
        time.sleep(2.5)  # 避免 rate limit

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = Path(r"D:\gitpro\claude_trading\reports") / f"_raw_hard_data_{ts}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[ok] saved -> {out_path}", flush=True)

    # 打印简表
    print("\n=== 简表 ===")
    print(f"{'SYM':<8}{'PRICE':>12}{'MCAP':>14}{'FDV':>14}{'CIRC%':>10}{'ATH%':>10}{'7d%':>10}{'30d%':>10}{'1y%':>10}")
    for sym, d in out.items():
        if "error" in d:
            print(f"{sym:<8}  ERROR")
            continue
        circ = d.get("circulating_supply")
        total = d.get("total_supply") or d.get("max_supply")
        circ_pct = (circ / total * 100) if (circ and total) else None
        def f(v, w=12, p=2):
            if v is None: return "N/A".rjust(w)
            return f"{v:>{w},.{p}f}" if abs(v) >= 1 else f"{v:>{w},.{p}f}"
        print(f"{sym:<8}{f(d.get('current_price_usd'),12,4)}{f(d.get('market_cap_usd'),14,0)}{f(d.get('fully_diluted_valuation_usd'),14,0)}"
              f"{(f'{circ_pct:.1f}%'.rjust(10) if circ_pct else 'N/A'.rjust(10))}"
              f"{f(d.get('ath_change_pct'),10,1)}{f(d.get('price_change_pct_7d'),10,1)}{f(d.get('price_change_pct_30d'),10,1)}{f(d.get('price_change_pct_1y'),10,1)}")


if __name__ == "__main__":
    main()
