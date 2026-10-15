"""
批量拉取市值前100项目数据
用法: python fetch_top100.py
"""
import json
import time
import urllib.request
import urllib.parse
from db import *

CG = "https://api.coingecko.com/api/v3"

def cg_get(path, retries=3):
    url = f"{CG}{path}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt < retries - 1:
                print(f"  重试 {attempt+1}/{retries}... ({e})")
                time.sleep(3)
            else:
                raise

def fetch_top100():
    print("拉取市值前100项目...")
    # 分两批拉
    all_coins = []
    for page in [1, 2]:
        data = cg_get(f"/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page={page}&price_change_percentage=1h,24h,7d,30d")
        all_coins.extend(data)
        print(f"  第{page}页: {len(data)}个")
        time.sleep(2)
    data = all_coins[:100]
    print(f"共拿到 {len(data)} 个项目")

    for i, coin in enumerate(data):
        symbol = coin["symbol"].upper()
        name = coin["name"]
        cg_id = coin["id"]

        price = coin.get("current_price", 0)
        mcap = coin.get("market_cap", 0)
        vol = coin.get("total_volume", 0)
        change_1h = coin.get("price_change_percentage_1h_in_currency", 0)
        change_24h = coin.get("price_change_percentage_24h", 0)
        change_7d = coin.get("price_change_percentage_7d", 0)
        change_30d = coin.get("price_change_percentage_30d_in_currency", 0)
        ath = coin.get("ath", 0)
        ath_date = coin.get("ath_date", "")
        atl = coin.get("atl", 0)
        circ = coin.get("circulating_supply", 0)
        total = coin.get("total_supply", 0)
        max_s = coin.get("max_supply", 0)
        fdv = coin.get("fully_diluted_valuation", 0)

        upsert_project(symbol, name, cg_id, category="", description="", website="", twitter="", github="")
        save_price(symbol, {
            "price": price, "change_1h": change_1h, "change_24h": change_24h,
            "change_7d": change_7d, "change_30d": change_30d,
            "market_cap": mcap, "volume_24h": vol, "ath": ath, "ath_date": ath_date,
            "atl": atl, "circulating_supply": circ, "total_supply": total,
            "max_supply": max_s, "fdv": fdv
        })

        if (i+1) % 20 == 0:
            print(f"  进度: {i+1}/100")

    print(f"\n完成！前100项目已全部入库")

    # 输出概览
    print(f"\n{'='*80}")
    print(f"  市值前100概览 (按市值排序)")
    print(f"{'='*80}")
    print(f"  {'#':>3} {'Symbol':<8} {'名称':<18} {'价格':>12} {'市值(B)':>10} {'24h%':>7} {'7d%':>7} {'距ATH%':>8}")
    print(f"  {'-'*75}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT p.symbol, p.name,
        (SELECT price FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1),
        (SELECT market_cap FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1),
        (SELECT change_24h FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1),
        (SELECT change_7d FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1),
        (SELECT ath FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1)
        FROM projects p ORDER BY (SELECT market_cap FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) DESC""")
    for rank, row in enumerate(c.fetchall(), 1):
        sym, name, price, mcap, chg24, chg7d, ath = row
        if price is None: continue
        mcap_b = mcap / 1e9 if mcap else 0
        ath_pct = (price/ath - 1)*100 if ath and ath > 0 else 0
        print(f"  {rank:>3} {sym:<8} {name[:16]:<18} ${price:>11,.4f} {mcap_b:>9.1f}B {chg24:>+6.1f}% {chg7d:>+6.1f}% {ath_pct:>+7.1f}%")
    conn.close()

if __name__ == '__main__':
    init_db()
    fetch_top100()
