"""
持续监控脚本
用法:
  python monitor.py              # 刷新所有项目
  python monitor.py ONDO HYPE    # 只刷新指定项目
"""
import sys
import json
import urllib.request
import urllib.parse
from db import *

CG = "https://api.coingecko.com/api/v3"

def cg_get(path):
    url = f"{CG}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def refresh_price(symbol):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT coin_gecko_id FROM projects WHERE symbol=?", (symbol,))
    row = c.fetchone()
    conn.close()
    if not row:
        print(f"  {symbol}: 未在数据库中，请先运行 research.py {symbol}")
        return
    cg_id = row[0]
    detail = cg_get(f"/coins/{cg_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false")
    md = detail.get("market_data", {})
    price = md.get("current_price", {}).get("usd", 0)
    change_24h = md.get("price_change_percentage_24h", 0)
    change_7d = md.get("price_change_percentage_7d", 0)
    change_30d = md.get("price_change_percentage_30d", 0)
    mcap = md.get("market_cap", {}).get("usd", 0)
    vol = md.get("total_volume", {}).get("usd", 0)
    ath = md.get("ath", {}).get("usd", 0)
    ath_date = md.get("ath_date", {}).get("usd", "")
    circ = md.get("circulating_supply", 0)
    total = md.get("total_supply", 0)
    max_s = md.get("max_supply", 0)
    fdv = md.get("fully_diluted_valuation", {}).get("usd", 0)

    save_price(symbol, {
        "price": price, "change_24h": change_24h, "change_7d": change_7d, "change_30d": change_30d,
        "market_cap": mcap, "volume_24h": vol, "ath": ath, "ath_date": ath_date,
        "circulating_supply": circ, "total_supply": total, "max_supply": max_s, "fdv": fdv
    })

    # 异动检测
    alert = ""
    if abs(change_24h) > 10:
        alert = f"  🚨 24h {'涨' if change_24h>0 else '跌'} {abs(change_24h):.1f}%!"
    if ath > 0 and price >= ath * 0.99:
        alert += "  🚨 接近ATH!"
    if abs(change_7d) > 30:
        alert += f"  🚨 7d {'涨' if change_7d>0 else '跌'} {abs(change_7d):.1f}%!"

    print(f"  {symbol}: ${price:.4f} ({change_24h:+.2f}% 24h, {change_7d:+.2f}% 7d){alert}")
    return price, change_24h

def show_dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT p.symbol, p.name, p.category,
        (SELECT price FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as price,
        (SELECT change_24h FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as chg24,
        (SELECT change_7d FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as chg7d,
        (SELECT COUNT(*) FROM events WHERE project=p.symbol) as event_cnt,
        (SELECT COUNT(*) FROM tweets WHERE project=p.symbol) as tweet_cnt
        FROM projects p ORDER BY p.symbol""")
    rows = c.fetchall()
    conn.close()
    print(f"\n{'='*80}")
    print(f"  监控仪表盘")
    print(f"{'='*80}")
    print(f"  {'Symbol':<8} {'名称':<15} {'价格':>10} {'24h%':>8} {'7d%':>8} {'事件':>5} {'推文':>5}")
    print(f"  {'-'*70}")
    for r in rows:
        sym, name, cat, price, chg24, chg7d, ev, tw = r
        price_s = f"${price:,.4f}" if price else "N/A"
        chg24_s = f"{chg24:+.1f}%" if chg24 else "N/A"
        chg7d_s = f"{chg7d:+.1f}%" if chg7d else "N/A"
        print(f"  {sym:<8} {name[:14]:<15} {price_s:>10} {chg24_s:>8} {chg7d_s:>8} {ev:>5} {tw:>5}")
    print()

if __name__ == '__main__':
    init_db()
    if len(sys.argv) > 1:
        projects = [s.upper() for s in sys.argv[1:]]
    else:
        rows = list_projects()
        projects = [r[0] for r in rows]
    print(f"刷新 {len(projects)} 个项目...")
    for p in projects:
        refresh_price(p)
    show_dashboard()
