"""
Hyperliquid HYPE + DEX-perp 竞品硬数据采集：CoinGecko + DefiLlama。
输出 JSON 到 reports/_raw_hype_data.json
"""
import json
import ssl
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

# CoinGecko coin_id 映射（DEX 永续赛道）
COINS = {
    "HYPE": "hyperliquid",
    "DYDX": "dydx-chain",
    "GMX": "gmx",
    "AEVO": "aevo",
    "VX": "vertex-protocol",
    "KWENTA": "kwenta",
}

CG = "https://api.coingecko.com/api/v3"
DL = "https://api.llama.fi"


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def cg_get(path, params=None):
    url = f"{CG}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return http_get(url)


def fetch_coin(cg_id):
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


def fetch_tvl():
    """DefiLlama 各协议 TVL。"""
    protocols = {
        "HYPE": "hyperliquid",
        "GMX": "gmx",
        "DYDX": "dydx",
        "AEVO": "aevo",
        "VERTEX": "vertex",
        "KWENTA": "kwenta",
    }
    out = {}
    for sym, slug in protocols.items():
        try:
            d = http_get(f"{DL}/protocol/{slug}")
            out[sym] = {
                "name": d.get("name"),
                "tvl": d.get("tvl"),
                "chain": d.get("chain"),
                "category": d.get("category"),
                "listedAt": d.get("listedAt"),
                "tvlPrev1DayAgo": d.get("tvlPrev1DayAgo"),
                "tvlPrev1WeekAgo": d.get("tvlPrev1WeekAgo"),
            }
        except Exception as e:
            out[sym] = {"error": str(e), "slug": slug}
        time.sleep(1.5)
    return out


def main():
    out = {"coins": {}, "tvl": {}}
    for sym, cg_id in COINS.items():
        print(f"[+] CG fetching {sym} ({cg_id}) ...", flush=True)
        try:
            out["coins"][sym] = fetch_coin(cg_id)
        except Exception as e:
            print(f"    !! failed: {e}", flush=True)
            out["coins"][sym] = {"error": str(e), "id": cg_id}
        time.sleep(2.5)

    print("[+] DefiLlama TVL ...", flush=True)
    try:
        out["tvl"] = fetch_tvl()
    except Exception as e:
        out["tvl"] = {"error": str(e)}

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = Path(r"D:\gitpro\claude_trading\reports") / f"_raw_hype_data_{ts}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[ok] saved -> {out_path}", flush=True)

    print("\n=== CoinGecko 简表 ===")
    hdr = f"{'SYM':<8}{'PRICE':>12}{'MCAP':>14}{'FDV':>14}{'CIRC%':>10}{'ATH%':>10}{'VOL24h':>14}{'7d%':>9}{'30d%':>9}"
    print(hdr)
    for sym, d in out["coins"].items():
        if "error" in d:
            print(f"{sym:<8}  ERROR: {d['error']}")
            continue
        circ = d.get("circulating_supply")
        total = d.get("total_supply") or d.get("max_supply")
        circ_pct = (circ / total * 100) if (circ and total) else None
        def f(v, w=12, p=2):
            if v is None:
                return "N/A".rjust(w)
            return f"{v:>{w},.{p}f}"
        print(f"{sym:<8}{f(d.get('current_price_usd'),12,4)}{f(d.get('market_cap_usd'),14,0)}{f(d.get('fully_diluted_valuation_usd'),14,0)}"
              f"{(f'{circ_pct:.1f}%'.rjust(10) if circ_pct else 'N/A'.rjust(10))}"
              f"{f(d.get('ath_change_pct'),10,1)}{f(d.get('total_volume_usd'),14,0)}{f(d.get('price_change_pct_7d'),9,1)}{f(d.get('price_change_pct_30d'),9,1)}")

    print("\n=== TVL 简表 ===")
    for sym, d in out.get("tvl", {}).items():
        if "error" in d:
            print(f"{sym:<8} ERROR: {d['error']}")
        else:
            tvl = d.get("tvl")
            print(f"{sym:<8} TVL=${tvl:,.0f}  chain={d.get('chain')}  cat={d.get('category')}")


if __name__ == "__main__":
    main()
