"""
新项目研究脚本
用法: python research.py ONDO
输入代币symbol，自动从CoinGecko拉数据并存库
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

def search_coin(symbol):
    """在CoinGecko搜索代币"""
    data = cg_get(f"/search?query={urllib.parse.quote(symbol)}")
    coins = data.get("coins", [])
    # 找最匹配的
    for c in coins:
        if c["symbol"].upper() == symbol.upper():
            return c
    return coins[0] if coins else None

def get_coin_detail(cg_id):
    """拉完整详情"""
    return cg_get(f"/coins/{cg_id}?localization=false&tickers=false&market_data=true&community_data=true&developer_data=true")

def research(symbol):
    print(f"\n{'='*60}")
    print(f"  研究新项目: {symbol}")
    print(f"{'='*60}")

    # 1. 搜索
    print(f"\n[1/4] 在CoinGecko搜索 {symbol}...")
    coin = search_coin(symbol)
    if not coin:
        print(f"  未找到 {symbol}")
        return
    cg_id = coin["id"]
    name = coin["name"]
    print(f"  找到: {name} ({coin['symbol'].upper()}) - 排名 #{coin.get('market_cap_rank','?')}")

    # 2. 拉详情
    print(f"\n[2/4] 拉取详细数据...")
    detail = get_coin_detail(cg_id)
    md = detail.get("market_data", {})

    price = md.get("current_price", {}).get("usd", 0)
    mcap = md.get("market_cap", {}).get("usd", 0)
    vol = md.get("total_volume", {}).get("usd", 0)
    ath = md.get("ath", {}).get("usd", 0)
    ath_date = md.get("ath_date", {}).get("usd", "")
    change_24h = md.get("price_change_percentage_24h", 0)
    change_7d = md.get("price_change_percentage_7d", 0)
    change_30d = md.get("price_change_percentage_30d", 0)
    circ_supply = md.get("circulating_supply", 0)
    total_supply = md.get("total_supply", 0)
    max_supply = md.get("max_supply", 0)
    fdv = md.get("fully_diluted_valuation", {}).get("usd", 0)

    desc = detail.get("description", {}).get("en", "")[:500]
    website = detail.get("links", {}).get("homepage", [""])[0]
    gh_list = detail.get("links", {}).get("repos_url", {}).get("github", [])
    github = gh_list[0] if gh_list else ""
    tw_list = detail.get("links", {}).get("twitter_screen_name", "")
    twitter = f"https://twitter.com/{tw_list}" if tw_list else ""
    category = ", ".join(detail.get("categories", [])[:3])

    print(f"  价格: ${price}")
    print(f"  市值: ${mcap:,.0f}")
    print(f"  24h涨跌: {change_24h:.2f}%")
    print(f"  7d涨跌: {change_7d:.2f}%")
    print(f"  ATH: ${ath} ({ath_date[:10]})")
    if ath > 0:
        print(f"  距ATH: {(price/ath - 1)*100:.1f}%")
    print(f"  流通量: {circ_supply:,.0f}")
    print(f"  FDV: ${fdv:,.0f}")

    # GitHub数据
    dev = detail.get("developer_data", {})
    print(f"  GitHub stars: {dev.get('stars',0)}")
    print(f"  GitHub contributors: {dev.get('contributors',0)}")
    print(f"  GitHub commits (4w): {dev.get('commit_count_4_weeks',0)}")

    # 社区数据
    comm = detail.get("community_data", {})
    print(f"  Twitter followers: {comm.get('twitter_followers',0):,}")
    print(f"  Reddit subscribers: {comm.get('reddit_subscribers',0):,}")

    # 3. 存库
    print(f"\n[3/4] 存入数据库...")
    upsert_project(symbol.upper(), name, cg_id, category, desc, website, twitter, github)

    save_price(symbol.upper(), {
        "price": price, "change_24h": change_24h, "change_7d": change_7d, "change_30d": change_30d,
        "market_cap": mcap, "volume_24h": vol, "ath": ath, "ath_date": ath_date,
        "circulating_supply": circ_supply, "total_supply": total_supply,
        "max_supply": max_supply, "fdv": fdv
    })

    # 4. 输出分析框架
    print(f"\n[4/4] 六维分析框架:")
    print(f"  {'维度':<12} {'权重':>6} {'关键指标'}")
    print(f"  {'-'*50}")
    print(f"  {'叙事':<12} {'25%':>6} {category}")
    print(f"  {'技术':<12} {'15%':>6} GitHub {dev.get('commit_count_4_weeks',0)} commits/4w, {dev.get('contributors',0)} contributors")
    print(f"  {'代币经济':<10} {'20%':>6} 流通率:{(circ_supply/total_supply*100 if total_supply else 0):.0f}%, FDV/MCap:{(fdv/mcap if mcap else 0):.2f}")
    print(f"  {'竞争':<12} {'10%':>6} 市值排名#{coin.get('market_cap_rank','?')}")
    print(f"  {'风险':<12} {'15%':>6} 距ATH:{(price/ath-1)*100:.1f}%, 7d:{change_7d:.1f}%")
    print(f"  {'市场动量':<10} {'15%':>6} 24h量:${vol:,.0f}, TW粉丝:{comm.get('twitter_followers',0):,}")

    # 自动风险标记
    print(f"\n  ⚠️ 自动风险检查:")
    risks = []
    if ath > 0 and (price/ath - 1) < -0.8:
        risks.append(f"距ATH跌幅>{abs((price/ath-1)*100):.0f}%")
    if total_supply > 0 and circ_supply/total_supply < 0.3:
        risks.append(f"流通率低({circ_supply/total_supply*100:.0f}%)")
    if coin.get('market_cap_rank', 999) > 100:
        risks.append(f"排名>{coin.get('market_cap_rank','?')}")
    if change_24h < -10:
        risks.append(f"24h暴跌{abs(change_24h):.1f}%")
    if risks:
        for r in risks:
            print(f"    - {r}")
    else:
        print(f"    - 无显著风险信号")

    print(f"\n  ✅ {symbol} 研究完成，数据已存入数据库")
    print(f"  下一步: 运行 python monitor.py {symbol} 持续监控")
    print(f"  运行 python report.py {symbol} 生成完整分析报告\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python research.py <SYMBOL>")
        print("示例: python research.py ONDO")
        sys.exit(1)
    init_db()
    research(sys.argv[1].upper())
