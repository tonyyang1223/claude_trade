# -*- coding: utf-8 -*-
"""
build_static_pages.py — 生成多个纯静态 HTML 看板页面 (无 JS 依赖)

复用 build_dashboard.collect_dashboard_data 提取数据, 输出到 reports/dashboard_pages/
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "analysis"))
from build_dashboard import collect_dashboard_data  # noqa: E402

OUT_DIR = os.path.join(ROOT, "reports", "dashboard_pages")

# ============ 通用 CSS / 头尾 ============
HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--border:#30363d;--txt:#e6edf3;--sub:#8b949e;
--up:#f6465d;--down:#2ebd85;--accent:#58a6ff;--gold:#e2b033;--purple:#a371f7;--orange:#f0883e;}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--txt);font-family:"Segoe UI","Microsoft YaHei",sans-serif;padding:20px;max-width:1400px;margin:0 auto}
h1{font-size:22px;margin-bottom:4px}
.sub{color:var(--sub);font-size:12px;margin-bottom:18px}
.nav{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap;border-bottom:1px solid var(--border);padding-bottom:14px}
.nav a{padding:7px 14px;border:1px solid var(--border);border-radius:8px;color:var(--sub);text-decoration:none;font-size:13px;background:var(--panel)}
.nav a:hover{color:var(--accent);border-color:var(--accent)}
.nav a.cur{background:#1f6feb33;color:var(--accent);border-color:var(--accent)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:20px}
.card{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.card .label{color:var(--sub);font-size:12px;margin-bottom:6px}
.card .val{font-size:22px;font-weight:600}
.grid{display:grid;gap:16px;margin-bottom:20px}
.g2{grid-template-columns:repeat(auto-fit,minmax(540px,1fr))}
@media(max-width:1180px){.g2{grid-template-columns:1fr}}
.panel{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:16px}
.panel h3{font-size:14px;color:var(--sub);margin-bottom:12px;font-weight:500}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--sub);text-align:right;padding:9px 10px;border-bottom:1px solid var(--border);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
td{padding:8px 10px;text-align:right;border-bottom:1px solid #21262d;white-space:nowrap}
tr:hover td{background:#1c2129}
.up{color:var(--up)}.down{color:var(--down)}
.tag{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;background:#30363d;color:var(--sub)}
/* 条形图: 用 div 宽度比例 */
.bar-row{display:flex;align-items:center;gap:8px;margin-bottom:7px;font-size:13px}
.bar-row .name{width:70px;text-align:right;color:var(--sub);flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar-row .track{flex:1;height:22px;background:#21262d;border-radius:4px;position:relative;overflow:hidden}
.bar-row .fill{height:100%;border-radius:4px;transition:width .4s}
.bar-row .val{width:80px;color:var(--txt);flex-shrink:0;font-size:12px}
.note{color:var(--sub);font-size:11px;margin-top:24px;border-top:1px solid var(--border);padding-top:10px;line-height:1.8}
</style>
</head>
<body>
<div class="nav">
<a href="index.html">首页</a>
<a href="page1_市场总览.html" __C1__>市场总览</a>
<a href="page2_板块分析.html" __C2__>板块分析</a>
<a href="page3_深度研究.html" __C3__>深度研究</a>
<a href="page4_资金与生态.html" __C4__>资金与生态</a>
</div>
"""
FOOT = """
<div class="note">
说明: 涨跌颜色遵循国内市场惯例 (红涨绿跌) · 纯静态页面, 无 JS 依赖 · 数据来源: 服务器定时采集 (Coingecko/DefiLlama/GitHub/Reddit + 深度研究引擎) ·
原始数据 data/raw_server · 扫描报告 data/reports/daily_scan (每小时快照 + 每10分钟深度研究)
</div>
</body></html>
"""


def fmt(v):
    if v is None:
        return "-"
    a = abs(v)
    if a >= 1e12:
        return f"${v/1e12:.2f}T"
    if a >= 1e9:
        return f"${v/1e9:.1f}B"
    if a >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"${v:,.0f}"


def fp(v):
    if v is None:
        return "-"
    return "$" + (v.toLocaleString() if False else f"{v:,.{0 if abs(v) >= 100 else (2 if abs(v) >= 1 else 6)}f}")


def pct(v):
    if v is None:
        return "-"
    return ("+" if v > 0 else "") + f"{v:.2f}%"


def cls(v):
    return "up" if v > 0 else ("down" if v < 0 else "")


def bar(name, value, max_v, color, val_text):
    w = max(0, min(100, abs(value) / max(max_v, 1e-9) * 100))
    return f'<div class="bar-row"><div class="name" title="{name}">{name}</div><div class="track"><div class="fill" style="width:{w:.1f}%;background:{color}"></div></div><div class="val">{val_text}</div></div>'


# ============ 页面 1: 市场总览 ============
def page1(d):
    k = d["kpi"]
    kpis = [
        ("总市值", fmt(k["totalMcap"])),
        ("监控币种数", str(k["coinCnt"])),
        ("平均 24h 涨跌", f'<span class="{cls(k["avgChg"])}">{pct(k["avgChg"])}</span>'),
        ("上涨家数", f'<span class="up">{k["upCnt"]}</span>'),
        ("下跌家数", f'<span class="down">{k["downCnt"]}</span>'),
        ("深度研究币种", str(k["deepStudied"])),
    ]
    kpi_html = "".join(f'<div class="card"><div class="label">{l}</div><div class="val">{v}</div></div>' for l, v in kpis)

    # 涨跌分布
    max_d = max(d["dist"]["values"]) or 1
    dist_html = "".join(
        bar(lbl, v, max_d, "#f6465d" if lbl.startswith("+") else ("#2ebd85" if lbl.startswith("-") else "#8b949e"), str(v))
        for lbl, v in zip(d["dist"]["labels"], d["dist"]["values"])
    )

    def top_bar(items, color, val_key, fmt_fn):
        mx = max(abs(i.get(val_key) or 0) for i in items) or 1
        return "".join(bar(i["sym"], i.get(val_key) or 0, mx, color, fmt_fn(i.get(val_key))) for i in items)

    gain_html = top_bar(d["gainers"], "#f6465d", "chg24", pct)
    lose_html = top_bar(d["losers"], "#2ebd85", "chg24", pct)
    mcap_html = top_bar(d["topMcap"], "#58a6ff", "mcap", fmt)
    vol_html = top_bar(d["topVol"], "#e2b033", "vol", fmt)

    return (HEAD.replace("__TITLE__", "市场总览").replace("__C1__", "class=cur")
            + f"""<h1>市场总览 <span class="tag">{d['meta']['date']}</span></h1>
<div class="sub">扫描时间: {d['meta']['scanTime']} · 涨跌家数比: <span class="up">{k['upCnt']}</span> / <span class="down">{k['downCnt']}</span></div>
<div class="kpis">{kpi_html}</div>
<div class="grid g2">
<div class="panel"><h3>24h 涨跌分布 (全部 {k['coinCnt']} 币)</h3>{dist_html}</div>
<div class="panel"><h3>24h 涨幅榜 TOP15</h3>{gain_html}</div>
<div class="panel"><h3>24h 跌幅榜 TOP15</h3>{lose_html}</div>
<div class="panel"><h3>市值 TOP15</h3>{mcap_html}</div>
<div class="panel"><h3>24h 成交额 TOP15</h3>{vol_html}</div>
</div>"""
            + FOOT)


# ============ 页面 2: 板块分析 ============
def page2(d):
    cats = d["cats"]
    max_cnt = max(c["count"] for c in cats) or 1
    max_mcap = max(c["mcap"] for c in cats) or 1
    cnt_html = "".join(bar(c["cat"], c["count"], max_cnt, "#58a6ff", str(c["count"])) for c in cats)
    mcap_html = "".join(bar(c["cat"], c["mcap"], max_mcap, "#a371f7", fmt(c["mcap"])) for c in cats)
    chg_html = "".join(
        f'<div class="bar-row"><div class="name" title="{c["cat"]}">{c["cat"]}</div>'
        f'<div class="track"><div class="fill" style="width:{abs(c["avg_chg"])*20:.1f}%;background:{"#f6465d" if c["avg_chg"]>0 else "#2ebd85"}"></div></div>'
        f'<div class="val {cls(c["avg_chg"])}">{pct(c["avg_chg"])}</div></div>'
        for c in cats
    )
    cat_rows = "".join(
        f'<tr><td><span class="tag">{c["cat"]}</span></td><td>{c["count"]}</td><td>{fmt(c["mcap"])}</td>'
        f'<td class="{cls(c["avg_chg"])}">{pct(c["avg_chg"])}</td></tr>'
        for c in sorted(cats, key=lambda x: -x["mcap"])
    )
    top_rows = "".join(
        f'<tr><td><span class="tag">{c["cat"]}</span></td><td>{c["name"]} <b style="color:var(--sub)">{c["sym"]}</b></td>'
        f'<td>{c["rank"] or "-"}</td><td>{fp(c["price"])}</td><td>{fmt(c["mcap"])}</td>'
        f'<td class="{cls(c["chg24"])}">{pct(c["chg24"])}</td></tr>'
        for c in d["catTop"]
    )
    return (HEAD.replace("__TITLE__", "板块分析").replace("__C2__", "class=cur")
            + f"""<h1>板块分析 <span class="tag">{d['meta']['catDay']}</span></h1>
<div class="sub">共 {len(cats)} 个板块, 依据深度研究分类 (市值前50币)</div>
<div class="grid g2">
<div class="panel"><h3>各板块币数</h3>{cnt_html}</div>
<div class="panel"><h3>各板块平均 24h 涨跌</h3>{chg_html}</div>
<div class="panel"><h3>各板块总市值</h3>{mcap_html}</div>
<div class="panel"><h3>板块汇总表</h3>
<table><tr><th>板块</th><th>币数</th><th>总市值</th><th>平均涨跌</th></tr>{cat_rows}</table></div>
</div>
<div class="panel"><h3>板块代表币 (各板块市值前3)</h3>
<table><tr><th>板块</th><th>币种</th><th>排名</th><th>价格</th><th>市值</th><th>24h涨跌</th></tr>{top_rows}</table></div>
"""
            + FOOT)


# ============ 页面 3: 深度研究 ============
def page3(d):
    deep = d["deep"]
    # 社区热度榜 (提及数 top15, 过滤0)
    by_m = sorted([c for c in deep if c.get("mentions", 0) > 0], key=lambda x: -x["mentions"])[:15]
    max_m = (max(c["mentions"] for c in by_m) if by_m else 1) or 1
    social_html = "".join(bar(c["sym"], c["mentions"], max_m, "#f0883e", str(c["mentions"])) for c in by_m) if by_m else '<div style="color:var(--sub);padding:20px">暂无社交提及数据</div>'

    by_r = sorted([c for c in deep if c.get("reddit_sub", 0) > 0], key=lambda x: -x["reddit_sub"])[:15]
    max_r = (max(c["reddit_sub"] for c in by_r) if by_r else 1) or 1
    reddit_html = "".join(bar(c["sym"], c["reddit_sub"], max_r, "#ff7b72", f"{c['reddit_sub']:,}") for c in by_r) if by_r else '<div style="color:var(--sub);padding:20px">暂无 Reddit 数据</div>'

    # 明细表
    rows = "".join(
        f'<tr><td>{c["rank"] or "-"}</td><td>{c["name"]} <b style="color:var(--sub)">{c["sym"]}</b></td>'
        f'<td>{fp(c["price"])}</td><td>{fmt(c["mcap"])}</td>'
        f'<td class="{cls(c["chg24"])}">{pct(c["chg24"])}</td>'
        f'<td>{c.get("mentions",0)}</td><td>{c.get("upvotes",0):,}</td>'
        f'<td>{c.get("reddit_sub",0):,}</td><td>{c.get("cscore") if c.get("cscore") is not None else "-"}</td>'
        f'<td>{c.get("news",0)}</td><td>{c.get("bili",0)}</td>'
        f'<td><span class="tag">{c["date"][5:]}</span></td></tr>'
        for c in deep
    )
    return (HEAD.replace("__TITLE__", "深度研究").replace("__C3__", "class=cur")
            + f"""<h1>币种深度研究 <span class="tag">{d['meta']['date']}</span></h1>
<div class="sub">共 {len(deep)} 币深度研究 (合并 {d['meta']['prevDay']} 与 {d['meta']['date']} 两批)</div>
<div class="grid g2">
<div class="panel"><h3>社区热度榜 TOP15 (社交提及数)</h3>{social_html}</div>
<div class="panel"><h3>Reddit 订阅数 TOP15</h3>{reddit_html}</div>
</div>
<div class="panel"><h3>深度研究明细表 (按市值排名)</h3>
<table>
<tr><th>排名</th><th>币种</th><th>价格</th><th>市值</th><th>24h涨跌</th><th>提及</th><th>点赞</th><th>Reddit订阅</th><th>社区分</th><th>新闻</th><th>B站</th><th>日期</th></tr>
{rows}</table></div>
"""
            + FOOT)


# ============ 页面 4: 资金与生态 ============
def page4(d):
    # KPI
    kpis = [
        ("Ethereum TVL", fmt(d["ethTvl"]) if d["ethTvl"] else "-"),
        ("USDT 供应量", fmt(d["stablecoins"][0]["total_supply"]) if d["stablecoins"] else "-"),
        ("BTC 仓库 Stars", f"{d['github']['stars']:,}" if d.get("github") else "-"),
        ("深度研究队列剩余", str(d["meta"]["queueLen"])),
        ("轻量监控总数", str(d["meta"]["lightTotal"])),
    ]
    kpi_html = "".join(f'<div class="card"><div class="label">{l}</div><div class="val">{v}</div></div>' for l, v in kpis)

    # 稳定币
    sc = d["stablecoins"]
    max_sc = max(s["total_supply"] for s in sc) if sc else 1
    stable_html = "".join(
        bar(s["symbol"], s["total_supply"], max_sc, "#58a6ff", fmt(s["total_supply"]))
        for s in sc
    ) if sc else '<div style="color:var(--sub);padding:20px">暂无数据</div>'

    # 24h 增减 (正负条)
    max_chg = max(abs(s["mint_change_24h"]) for s in sc) if sc else 1
    flow_html = "".join(
        bar(s["symbol"], s["mint_change_24h"], max_chg,
            "#f6465d" if s["mint_change_24h"] >= 0 else "#2ebd85",
            ("+" if s["mint_change_24h"] >= 0 else "") + fmt(s["mint_change_24h"]))
        for s in sc
    ) if sc else ""

    # 两日对比
    cmp_rows = "".join(
        f'<tr><td>{c["sym"]}</td><td>{c["name"]}</td><td>{fp(c["prev"])}</td><td>{fp(c["cur"])}</td>'
        f'<td class="{cls(c["pct"])}">{pct(c["pct"])}</td></tr>'
        for c in d["dayCmp"]
    )
    cmp_html = f'<table><tr><th>币种</th><th>名称</th><th>前一日</th><th>当前</th><th>变化</th></tr>{cmp_rows}</table>' if d["dayCmp"] else '<div style="color:var(--sub);padding:20px">暂无前一日快照</div>'

    return (HEAD.replace("__TITLE__", "资金与生态").replace("__C4__", "class=cur")
            + f"""<h1>资金与生态 <span class="tag">{d['meta']['date']}</span></h1>
<div class="sub">稳定币供应 / 链上 TVL / 开发者活跃度 / 主流币两日对比</div>
<div class="kpis">{kpi_html}</div>
<div class="grid g2">
<div class="panel"><h3>稳定币供应量 TOP (共 {len(sc)} 种)</h3>{stable_html}</div>
<div class="panel"><h3>稳定币 24h 增减 (铸币/销毁)</h3>{flow_html}</div>
<div class="panel"><h3>主流币价格两日对比 ({d['meta']['prevDay']} → {d['meta']['date']})</h3>{cmp_html}</div>
</div>
"""
            + FOOT)


# ============ 首页 index ============
def index(d):
    k = d["kpi"]
    cards = [
        ("市场总览", "page1_市场总览.html", f"总市值 {fmt(k['totalMcap'])} · {k['coinCnt']} 币 · 涨跌 {k['upCnt']}/{k['downCnt']}", "#58a6ff"),
        ("板块分析", "page2_板块分析.html", f"{len(d['cats'])} 大板块 · {len(d['catTop'])} 代表币", "#a371f7"),
        ("深度研究", "page3_深度研究.html", f"{k['deepStudied']} 币深度研究 · 社区/Reddit/新闻", "#f0883e"),
        ("资金与生态", "page4_资金与生态.html", f"{len(d['stablecoins'])} 种稳定币 · ETH TVL · GitHub", "#e2b033"),
    ]
    card_html = "".join(
        f'<a href="{href}" style="text-decoration:none"><div class="card" style="border-color:{color}44;cursor:pointer"><div class="label" style="color:{color}">{title}</div><div class="val" style="font-size:14px;color:var(--sub)">{desc}</div></div></a>'
        for title, href, desc, color in cards
    )
    return (HEAD.replace("__TITLE__", "加密货币看板")
            + f"""<h1>加密货币多维度看板 <span class="tag">{d['meta']['date']}</span></h1>
<div class="sub">扫描时间: {d['meta']['scanTime']} · 深度研究 {d['meta']['deepTotal']} 币 · 轻量 {d['meta']['lightTotal']} 币 · 队列剩余 {d['meta']['queueLen']}</div>
<div class="kpis">{card_html}</div>
<div class="panel"><h3>数据来源与说明</h3>
<table>
<tr><th>数据源</th><th>用途</th><th>采集频率</th></tr>
<tr><td>Coingecko</td><td>市值/价格/涨跌/成交额 (800币)</td><td>每日 00:05 UTC</td></tr>
<tr><td>Coinglass</td><td>资金费率/持仓量 (免费接口受限)</td><td>每日 00:05 UTC</td></tr>
<tr><td>DefiLlama</td><td>链上 TVL</td><td>每日 00:05 UTC</td></tr>
<tr><td>GitHub</td><td>开发者仓库活跃度</td><td>每日 00:05 UTC</td></tr>
<tr><td>Reddit</td><td>社区提及/情绪</td><td>每日 00:05 UTC</td></tr>
<tr><td>深度研究引擎</td><td>社交/B站/新闻/RSS/V2EX 综合分析</td><td>每10分钟1币</td></tr>
</table></div>
"""
            + FOOT)


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else None
    if not date:
        scan_dir = os.path.join(ROOT, "data", "reports", "daily_scan")
        days = sorted(x for x in os.listdir(scan_dir) if os.path.isdir(os.path.join(scan_dir, x)))
        date = days[-1] if days else None
    if not date:
        sys.exit("无扫描数据")

    d = collect_dashboard_data(date)
    os.makedirs(OUT_DIR, exist_ok=True)

    pages = {
        "index.html": index(d),
        "page1_市场总览.html": page1(d),
        "page2_板块分析.html": page2(d),
        "page3_深度研究.html": page3(d),
        "page4_资金与生态.html": page4(d),
    }
    for name, content in pages.items():
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  {name}: {os.path.getsize(path)/1024:.1f} KB")
    print(f"\n共生成 {len(pages)} 个静态页面于 {OUT_DIR}")


if __name__ == "__main__":
    main()
