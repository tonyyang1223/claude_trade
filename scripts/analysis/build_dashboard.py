# -*- coding: utf-8 -*-
"""
build_dashboard.py — 生成加密货币多维度 HTML 看板

数据来源:
  - data/reports/daily_scan/<date>/top_800_light/all_coins.json   (800 币轻量快照)
  - data/reports/daily_scan/<date>/top_50_detailed/*.json         (深度研究)
  - data/reports/daily_scan/<date>/by_category/                   (板块分类)
  - data/reports/daily_scan/<date>/summary.json                   (汇总 KPI)
  - data/raw_server/<source>/<date>.parquet                       (原始采集)

输出: reports/crypto_dashboard.html (单文件, 内嵌 ECharts, 离线可看)

用法: python scripts/analysis/build_dashboard.py [--date 2026-08-26]
"""
import argparse
import glob
import json
import os
import sys
from collections import defaultdict

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fmt_mcap(v):
    """市值/金额格式化: 万亿/亿"""
    if v is None:
        return "-"
    if abs(v) >= 1e12:
        return f"${v/1e12:.2f}T"
    if abs(v) >= 1e9:
        return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"${v:,.0f}"


def collect_dashboard_data(date_str):
    scan_dir = os.path.join(ROOT, "data", "reports", "daily_scan")
    day_dir = os.path.join(scan_dir, date_str)

    # ---------- 1. 汇总 KPI ----------
    summary = load_json(os.path.join(day_dir, "summary.json"))
    ms = summary.get("market_stats", {})

    # ---------- 2. 800 币轻量快照 ----------
    coins = load_json(os.path.join(day_dir, "top_800_light", "all_coins.json"))
    # 按 id 去重 (源数据存在重复记录)
    seen = set()
    uniq = []
    for c in coins:
        if c.get("id") in seen or c.get("price_usd") is None:
            continue
        seen.add(c.get("id"))
        uniq.append(c)
    coins = uniq
    for c in coins:
        c["change_24h_pct"] = c.get("change_24h_pct") or 0
        c["change_7d_pct"] = c.get("change_7d_pct") or 0

    total_mcap = sum(c.get("market_cap") or 0 for c in coins)
    avg_chg = sum(c["change_24h_pct"] for c in coins) / len(coins)

    # 涨跌分布直方图 (2% 一档, 截断 ±20%)
    bins = list(range(-20, 22, 2))
    hist = defaultdict(int)
    for c in coins:
        b = max(-20, min(20, c["change_24h_pct"]))
        # 落到 [low, high) 区间
        idx = int((b + 20) // 2)
        hist[bins[min(idx, len(bins) - 2)]] += 1
    dist_labels = [f"{bins[i]:+d}%~{bins[i+1]:+d}%" for i in range(len(bins) - 1)]
    dist_values = [hist[bins[i]] for i in range(len(bins) - 1)]

    def coin_brief(c):
        return {
            "id": c["id"], "sym": c.get("symbol", ""), "name": c.get("name", ""),
            "rank": c.get("rank"), "price": c.get("price_usd"),
            "mcap": c.get("market_cap"), "vol": c.get("volume_24h"),
            "chg24": c["change_24h_pct"], "chg7d": c["change_7d_pct"],
        }

    gainers = sorted([c for c in coins if c["rank"] and c["rank"] <= 300],
                     key=lambda x: -x["change_24h_pct"])[:15]
    losers = sorted([c for c in coins if c["rank"] and c["rank"] <= 300],
                    key=lambda x: x["change_24h_pct"])[:15]
    top_mcap = sorted(coins, key=lambda x: -(x.get("market_cap") or 0))[:15]
    top_vol = sorted(coins, key=lambda x: -(x.get("volume_24h") or 0))[:15]

    # 散点: 24h vs 7d (成交额 top 120)
    scatter = sorted(coins, key=lambda x: -(x.get("volume_24h") or 0))[:120]

    # 涨跌家数统计
    up_cnt = sum(1 for c in coins if c["change_24h_pct"] > 0)
    down_cnt = sum(1 for c in coins if c["change_24h_pct"] < 0)

    # ---------- 3. 板块分析 (近7天内 by_category 覆盖币数最多的一天) ----------
    from datetime import datetime, timedelta
    cat_day = date_str
    cat_dir = os.path.join(day_dir, "by_category")
    best_cnt = -1
    min_day = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
    for d in sorted(os.listdir(scan_dir), reverse=True):
        if d < min_day:
            continue
        p = os.path.join(scan_dir, d, "by_category")
        if os.path.isdir(p):
            cnt = sum(len(files) for _, _, files in os.walk(p))
            if cnt > best_cnt:
                cat_dir, cat_day, best_cnt = p, d, cnt

    cat_stats = []
    cat_top_coins = []
    if os.path.isdir(cat_dir):
        for cat in sorted(os.listdir(cat_dir)):
            files = glob.glob(os.path.join(cat_dir, cat, "*.json"))
            members = []
            for fp in files:
                try:
                    j = load_json(fp)
                except Exception:
                    continue
                mkt = (j.get("sources", {}) or {}).get("market", {}).get("data", {}) or {}
                members.append({
                    "id": j.get("coin_id"),
                    "sym": mkt.get("symbol") or str(j.get("coin_id", "")).upper()[:8],
                    "name": mkt.get("name") or j.get("coin_id"),
                    "rank": mkt.get("market_cap_rank") or j.get("rank"),
                    "price": mkt.get("current_price"),
                    "mcap": mkt.get("market_cap"),
                    "chg24": mkt.get("price_change_percentage_24h") or 0,
                    "vol": mkt.get("total_volume"),
                })
            if not members:
                continue
            members.sort(key=lambda x: -(x.get("mcap") or 0))
            mcaps = [m["mcap"] for m in members if m.get("mcap")]
            chgs = [m["chg24"] for m in members if m.get("chg24") is not None]
            cat_stats.append({
                "cat": cat, "count": len(members),
                "mcap": sum(mcaps), "avg_chg": sum(chgs) / len(chgs) if chgs else 0,
            })
            for m in members[:3]:
                cat_top_coins.append({**m, "cat": cat})
    cat_stats.sort(key=lambda x: -x["count"])

    # ---------- 4. 深度研究表 (当日 + 前一日合并, 当日优先) ----------
    deep_coins = {}
    prev_day = None
    days = sorted(os.listdir(scan_dir), reverse=True)
    if date_str in days:
        i = days.index(date_str)
        prev_day = days[i + 1] if i + 1 < len(days) else None
    for d in ([prev_day, date_str] if prev_day else [date_str]):
        deep_dir = os.path.join(scan_dir, d, "top_50_detailed")
        if not os.path.isdir(deep_dir):
            continue
        for fp in glob.glob(os.path.join(deep_dir, "*.json")):
            try:
                j = load_json(fp)
            except Exception:
                continue
            cid = j.get("coin_id")
            if not cid:
                continue
            src = j.get("sources", {}) or {}
            mkt = (src.get("market", {}) or {}).get("data", {}) or {}
            soc = (src.get("social_stats", {}) or {}).get("data", {}) or {}
            cs = (src.get("community_score", {}) or {}).get("data", {}) or {}
            overall = soc.get("overall", {}) or {}
            reddit = soc.get("reddit", {}) or {}
            deep_coins[cid] = {
                "id": cid,
                "sym": mkt.get("symbol") or str(cid).upper()[:8],
                "name": mkt.get("name") or cid,
                "rank": mkt.get("market_cap_rank") or j.get("rank"),
                "date": d,
                "price": mkt.get("current_price"),
                "mcap": mkt.get("market_cap"),
                "vol": mkt.get("total_volume"),
                "chg24": mkt.get("price_change_percentage_24h") or 0,
                "ath": mkt.get("ath"),
                "ath_chg": mkt.get("ath_change_percentage"),
                "mentions": overall.get("mentions", 0) or 0,
                "upvotes": overall.get("upvotes", 0) or 0,
                "signal": overall.get("signal"),
                "reddit_sub": reddit.get("subscribers", 0) or 0,
                "cscore": cs.get("community_score"),
                "news": (cs.get("breakdown", {}).get("news", {}) or {}).get("mentions", 0) or 0,
                "bili": (cs.get("breakdown", {}).get("bilibili", {}) or {}).get("video_count", 0) or 0,
            }
    deep_list = sorted(deep_coins.values(), key=lambda x: (x.get("rank") or 9999))

    # ---------- 5. 稳定币 / 链上数据 ----------
    stablecoins = []
    eth_tvl = None
    gh_stars = None
    # 从深度研究取稳定币数据
    for dc in deep_list:
        j = None
        fp = os.path.join(scan_dir, dc["date"], "top_50_detailed", dc["id"] + ".json")
        if os.path.exists(fp):
            j = load_json(fp)
        if j:
            sf = (j.get("sources", {}).get("stablecoin_flows", {}) or {}).get("data", {}) or {}
            if sf.get("stablecoins"):
                stablecoins = sf["stablecoins"]
                break
    # parquet: defillama / github
    try:
        dl = pd.read_parquet(os.path.join(ROOT, "data", "raw_server", "defillama", f"{date_str}.parquet"))
        if len(dl):
            eth_tvl = float(dl.iloc[0]["tvl"])
    except Exception:
        pass
    try:
        gh = pd.read_parquet(os.path.join(ROOT, "data", "raw_server", "github", f"{date_str}.parquet"))
        if len(gh) and "stargazers_count" in gh.columns:
            gh_stars = {"repo": gh.iloc[0]["full_name"], "stars": int(gh.iloc[0]["stargazers_count"]),
                        "forks": int(gh.iloc[0].get("forks_count") or 0)}
    except Exception:
        pass

    # ---------- 6. 两日对比 (主流币) ----------
    day_cmp = []
    if prev_day:
        prev_coins = {}
        pfile = os.path.join(scan_dir, prev_day, "top_800_light", "all_coins.json")
        if os.path.exists(pfile):
            for c in load_json(pfile):
                prev_coins[c["id"]] = c
        for c in top_mcap[:10]:
            p = prev_coins.get(c["id"])
            if p and p.get("price_usd"):
                day_cmp.append({
                    "sym": c.get("symbol"), "name": c.get("name"),
                    "prev": p["price_usd"], "cur": c["price_usd"],
                    "pct": (c["price_usd"] - p["price_usd"]) / p["price_usd"] * 100,
                })

    return {
        "meta": {
            "date": date_str, "prevDay": prev_day, "catDay": cat_day,
            "scanTime": summary.get("scan_time"),
            "deepTotal": summary.get("deep_researched"),
            "lightTotal": summary.get("light_researched"),
            "queueLen": summary.get("state_stats", {}).get("queue_length"),
        },
        "kpi": {
            "totalMcap": total_mcap, "coinCnt": len(coins), "avgChg": avg_chg,
            "upCnt": up_cnt, "downCnt": down_cnt,
            "deepStudied": len(deep_list),
        },
        "dist": {"labels": dist_labels, "values": dist_values},
        "gainers": [coin_brief(c) for c in gainers],
        "losers": [coin_brief(c) for c in losers],
        "topMcap": [coin_brief(c) for c in top_mcap],
        "topVol": [coin_brief(c) for c in top_vol],
        "scatter": [coin_brief(c) for c in scatter],
        "cats": cat_stats,
        "catTop": cat_top_coins,
        "deep": deep_list,
        "stablecoins": stablecoins,
        "ethTvl": eth_tvl,
        "github": gh_stars,
        "dayCmp": day_cmp,
    }


HTML_TMPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>加密货币多维度看板 · __DATE__</title>
<script>__ECHARTS__</script>
<style>
:root{--bg:#0d1117;--panel:#161b22;--border:#30363d;--txt:#e6edf3;--sub:#8b949e;
--up:#f6465d;--down:#2ebd85;--accent:#58a6ff;--gold:#e2b203;}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--txt);font-family:"Segoe UI","Microsoft YaHei",sans-serif;padding:20px}
h1{font-size:22px;margin-bottom:4px}
.sub{color:var(--sub);font-size:12px;margin-bottom:18px}
.tabs{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.tab{padding:8px 18px;border:1px solid var(--border);border-radius:8px;cursor:pointer;
background:var(--panel);color:var(--sub);font-size:14px;transition:.15s}
.tab:hover{color:var(--txt);border-color:var(--accent)}
.tab.active{background:#1f6feb33;color:var(--accent);border-color:var(--accent)}
.panel{display:none}
.panel.active{display:block}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:16px}
.card{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.card .label{color:var(--sub);font-size:12px;margin-bottom:6px}
.card .val{font-size:22px;font-weight:600}
.card .delta{font-size:12px;margin-top:4px}
.grid{display:grid;gap:16px;margin-bottom:16px}
.g2{grid-template-columns:repeat(auto-fit,minmax(460px,1fr))}
.chart{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px}
.chart h3{font-size:14px;color:var(--sub);margin-bottom:8px;font-weight:500}
.chart .box{height:340px}
.chart .box.tall{height:420px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--sub);text-align:right;padding:8px 10px;border-bottom:1px solid var(--border);
cursor:pointer;user-select:none;white-space:nowrap;position:sticky;top:0;background:var(--panel)}
th:first-child,td:first-child{text-align:left}
th:hover{color:var(--accent)}
td{padding:7px 10px;text-align:right;border-bottom:1px solid #21262d;white-space:nowrap}
tr:hover td{background:#1c2129}
.tag{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;background:#30363d;color:var(--sub)}
.up{color:var(--up)}.down{color:var(--down)}
.src-note{color:var(--sub);font-size:11px;margin-top:24px;border-top:1px solid var(--border);padding-top:10px;line-height:1.8}
::-webkit-scrollbar{width:8px;height:8px}::-webkit-scrollbar-thumb{background:#30363d;border-radius:4px}
.tbl-wrap{max-height:560px;overflow:auto}
.badge{font-size:11px;padding:2px 8px;border-radius:4px;background:#1f6feb33;color:var(--accent);margin-left:8px}
</style>
</head>
<body>
<h1>加密货币多维度看板 <span class="badge">__DATE__</span></h1>
<div class="sub">数据来源: 服务器定时采集 (Coingecko / Coinglass / DefiLlama / GitHub / Reddit + 深度研究引擎) · 扫描时间: __SCANTIME__ · 深度研究 __DEEPTOTAL__ 币 / 轻量 __LIGHTTOTAL__ 币</div>

<div class="tabs">
<div class="tab active" data-p="p1">市场总览</div>
<div class="tab" data-p="p2">板块分析</div>
<div class="tab" data-p="p3">币种深度研究</div>
<div class="tab" data-p="p4">资金与生态</div>
</div>

<div class="panel active" id="p1">
  <div class="kpis" id="kpis"></div>
  <div class="grid g2">
    <div class="chart"><h3>24h 涨跌分布 (全部 __COINCNT__ 币)</h3><div class="box" id="c_dist"></div></div>
    <div class="chart"><h3>24h 涨跌 vs 7d 涨跌 (成交额 Top120, 气泡=成交额)</h3><div class="box" id="c_scatter"></div></div>
    <div class="chart"><h3>24h 涨幅榜 TOP15 (市值排名前300)</h3><div class="box" id="c_gain"></div></div>
    <div class="chart"><h3>24h 跌幅榜 TOP15 (市值排名前300)</h3><div class="box" id="c_lose"></div></div>
    <div class="chart"><h3>市值 TOP15</h3><div class="box" id="c_mcap"></div></div>
    <div class="chart"><h3>24h 成交额 TOP15</h3><div class="box" id="c_vol"></div></div>
  </div>
</div>

<div class="panel" id="p2">
  <div class="grid g2">
    <div class="chart"><h3>各板块币数 与 平均24h涨跌 (__CATDAY__)</h3><div class="box" id="c_cat"></div></div>
    <div class="chart"><h3>各板块总市值</h3><div class="box" id="c_catmcap"></div></div>
  </div>
  <div class="chart"><h3>板块代表币 (各板块市值前3)</h3>
    <div class="tbl-wrap"><table id="t_cat"></table></div>
  </div>
</div>

<div class="panel" id="p3">
  <div class="grid g2">
    <div class="chart"><h3>社区热度榜 TOP15 (社交提及数)</h3><div class="box" id="c_social"></div></div>
    <div class="chart"><h3>Reddit 订阅数 TOP15</h3><div class="box" id="c_reddit"></div></div>
  </div>
  <div class="chart"><h3>深度研究币种明细 (可点击表头排序 · __DEEPCNT__ 币, 含 __PREVDAY__ 与 __DATE__ 两批)</h3>
    <div class="tbl-wrap"><table id="t_deep"></table></div>
  </div>
</div>

<div class="panel" id="p4">
  <div class="kpis" id="kpis2"></div>
  <div class="grid g2">
    <div class="chart"><h3>稳定币供应量 与 24h 增减</h3><div class="box" id="c_stable"></div></div>
    <div class="chart"><h3>主流币价格两日对比 (__PREVDAY__ → __DATE__)</h3><div class="box" id="c_cmp"></div></div>
  </div>
</div>

<div class="src-note">
说明: 涨跌颜色遵循国内市场惯例 (红涨绿跌)。资金费率/持仓量维度因 Coinglass 免费接口受限暂缺, 数据积累后将补充。
原始数据: data/raw_server (服务器每日 00:05 UTC 采集) · 扫描报告: data/reports/daily_scan (每小时快照 + 每10分钟深度研究)。
</div>

<script>
// 渲染入口: 检查 echarts 是否就绪, 提供可见错误提示
function initDashboard(){
const D = __DATA__;
const UP='#f6465d', DOWN='#2ebd85', TXT='#e6edf3', SUB='#8b949e', SPLIT='#30363d';
const fm=v=>v==null?'-':(Math.abs(v)>=1e12?(v/1e12).toFixed(2)+'T':Math.abs(v)>=1e9?(v/1e9).toFixed(1)+'B':Math.abs(v)>=1e6?(v/1e6).toFixed(1)+'M':v.toLocaleString());
const fp=v=>v==null?'-':'$'+(Math.abs(v)>=1?v.toLocaleString(undefined,{maximumFractionDigits:Math.abs(v)>=100?0:4}):v.toFixed(6));
const pct=v=>v==null?'-':(v>0?'+':'')+v.toFixed(2)+'%';
const cls=v=>v>0?'up':(v<0?'down':'');
const base={backgroundColor:'transparent',textStyle:{color:TXT,colorSub:SUB}};
const charts=[];
function mk(id,opt){const el=document.getElementById(id);if(!el)return;const c=echarts.init(el);opt.tooltip=opt.tooltip||{trigger:'axis',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT}};c.setOption(Object.assign({},base,opt));charts.push(c);return c;}
window.addEventListener('resize',()=>charts.forEach(c=>c.resize()));

// Tab 切换后重绘
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
t.classList.add('active');document.getElementById(t.dataset.p).classList.add('active');
setTimeout(()=>charts.forEach(c=>c.resize()),30);});

// ============ KPI ============
const k=D.kpi;
document.getElementById('kpis').innerHTML=[
{l:'总市值',v:'$'+fm(k.totalMcap)},
{l:'监控币种数',v:k.coinCnt},
{l:'平均 24h 涨跌',v:pct(k.avgChg),c:cls(k.avgChg)},
{l:'上涨 / 下跌家数',v:'<span class="up">'+k.upCnt+'</span> / <span class="down">'+k.downCnt+'</span>'},
{l:'深度研究币种',v:k.deepStudied},
].map(x=>'<div class="card"><div class="label">'+x.l+'</div><div class="val '+(x.c||'')+'">'+x.v+'</div></div>').join('');

document.getElementById('kpis2').innerHTML=[
{l:'Ethereum TVL (DefiLlama)',v:D.ethTvl?'$'+fm(D.ethTvl):'-'},
{l:'USDT 供应量',v:D.stablecoins.length?'$'+fm(D.stablecoins[0].total_supply):'-'},
{l:'BTC 仓库 Stars (GitHub)',v:D.github?D.github.stars.toLocaleString():'-'},
{l:'深度研究队列剩余',v:D.meta.queueLen},
{l:'轻量监控总数',v:D.meta.lightTotal},
].map(x=>'<div class="card"><div class="label">'+x.l+'</div><div class="val">'+x.v+'</div></div>').join('');

// ============ 涨跌分布 ============
mk('c_dist',{grid:{left:50,right:20,top:20,bottom:60},xAxis:{type:'category',data:D.dist.labels,axisLabel:{color:SUB,rotate:45,fontSize:10}},yAxis:{type:'value',name:'币数',nameTextStyle:{color:SUB},axisLabel:{color:SUB},splitLine:{lineStyle:{color:'#21262d'}}},
series:[{type:'bar',data:D.dist.values.map((v,i)=>({value:v,itemStyle:{color:D.dist.labels[i].startsWith('+')?UP:(D.dist.labels[i].startsWith('0')||D.dist.labels[i].startsWith('-0'))?'#8b949e':DOWN}})),barCategoryGap:'20%'}],
tooltip:{trigger:'axis',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT}}});

// ============ 散点 ============
(function(){
const data=D.scatter.map(c=>({name:c.sym,value:[c.chg24,c.chg7d,c.vol]}));
const vmax=Math.max(...D.scatter.map(c=>c.vol||0))||1;
mk('c_scatter',{grid:{left:50,right:120,top:30,bottom:40},
xAxis:{type:'value',name:'24h %',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:'{value}%'},splitLine:{lineStyle:{color:'#21262d'}}},
yAxis:{type:'value',name:'7d %',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:'{value}%'},splitLine:{lineStyle:{color:'#21262d'}}},
series:[{type:'scatter',data:data,symbolSize:v=>8+30*Math.sqrt((v[2]||0)/vmax),
itemStyle:{color:p=>p.value[0]>=0?UP:DOWN,opacity:.75},
label:{show:true,formatter:p=>p.name,position:'top',color:SUB,fontSize:9},labelLayout:{hideOverlap:true}}],
tooltip:{trigger:'item',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT},
formatter:p=>p.name+'<br>24h: '+pct(p.value[0])+'<br>7d: '+pct(p.value[1])+'<br>成交额: $'+fm(p.value[2])}}});
})();

// ============ 横向 bar 工具 ============
function hbar(id,items,title){mk(id,{grid:{left:80,right:60,top:10,bottom:30},
xAxis:{type:'value',axisLabel:{color:SUB,formatter:v=>Math.abs(v)>=1e9?(v/1e9).toFixed(0)+'B':Math.abs(v)>=1e6?(v/1e6).toFixed(0)+'M':v},splitLine:{lineStyle:{color:'#21262d'}}},
yAxis:{type:'category',data:items.map(i=>i.sym).reverse(),axisLabel:{color:TXT}},
series:[{type:'bar',data:items.map(i=>({value:i.v,itemStyle:{color:i.c}})).reverse(),barWidth:'62%',label:{show:true,position:'right',color:SUB,fontSize:10,formatter:p=>p.value>=1e6?fm(p.value):pct(p.value)}}]});}

hbar('c_gain',D.gainers.map(c=>({sym:c.sym,v:c.chg24,c:UP})));
hbar('c_lose',D.losers.map(c=>({sym:c.sym,v:c.chg24,c:DOWN})));
hbar('c_mcap',D.topMcap.map(c=>({sym:c.sym,v:c.mcap,c:'#58a6ff'})));
hbar('c_vol',D.topVol.map(c=>({sym:c.sym,v:c.vol,c:'#e2b203'})));

// ============ 板块 ============
(function(){
if(!D.cats.length)return;
mk('c_cat',{grid:{left:60,right:60,top:40,bottom:40},
xAxis:{type:'category',data:D.cats.map(c=>c.cat),axisLabel:{color:SUB,rotate:20}},
yAxis:[{type:'value',name:'币数',nameTextStyle:{color:SUB},axisLabel:{color:SUB},splitLine:{lineStyle:{color:'#21262d'}}},
{type:'value',name:'平均涨跌%',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:'{value}%'},splitLine:{show:false}}],
series:[{type:'bar',data:D.cats.map(c=>c.count),itemStyle:{color:'#58a6ff'},barWidth:'45%'},
{type:'line',yAxisIndex:1,data:D.cats.map(c=>c.avg_chg),itemStyle:{color:'#e2b203'},lineStyle:{color:'#e2b203'},
symbolSize:6,label:{show:true,color:'#e2b203',fontSize:10,formatter:p=>pct(p.value)}}]});
mk('c_catmcap',{grid:{left:60,right:60,top:20,bottom:60},
xAxis:{type:'category',data:D.cats.map(c=>c.cat),axisLabel:{color:SUB,rotate:20}},
yAxis:{type:'value',axisLabel:{color:SUB,formatter:v=>fm(v)},splitLine:{lineStyle:{color:'#21262d'}}},
series:[{type:'bar',data:D.cats.map(c=>c.mcap),itemStyle:{color:'#a371f7'},barWidth:'45%',
label:{show:true,position:'top',color:SUB,fontSize:10,formatter:p=>'$'+fm(p.value)}}]});
// 表格
const t=document.getElementById('t_cat');
t.innerHTML='<tr><th>板块</th><th>币种</th><th>排名</th><th>价格</th><th>市值</th><th>24h涨跌</th></tr>'+
D.catTop.map(c=>'<tr><td><span class="tag">'+c.cat+'</span></td><td>'+c.name+' ('+c.sym+')</td><td>'+(c.rank||'-')+'</td><td>'+fp(c.price)+'</td><td>'+(c.mcap?'$'+fm(c.mcap):'-')+'</td><td class="'+cls(c.chg24)+'">'+pct(c.chg24)+'</td></tr>').join('');
})();

// ============ 社区热度 / Reddit ============
(function(){
const byM=[...D.deep].sort((a,b)=>(b.mentions||0)-(a.mentions||0)).slice(0,15).filter(c=>c.mentions>0);
if(byM.length)hbar('c_social',byM.map(c=>({sym:c.sym,v:c.mentions,c:'#f0883e'})));
else document.getElementById('c_social').innerHTML='<div style="color:#8b949e;padding:40px;text-align:center">暂无社交提及数据</div>';
const byR=[...D.deep].sort((a,b)=>(b.reddit_sub||0)-(a.reddit_sub||0)).slice(0,15).filter(c=>c.reddit_sub>0);
if(byR.length)hbar('c_reddit',byR.map(c=>({sym:c.sym,v:c.reddit_sub,c:'#ff7b72'})));
else document.getElementById('c_reddit').innerHTML='<div style="color:#8b949e;padding:40px;text-align:center">暂无 Reddit 数据</div>';
})();

// ============ 深度研究表 ============
(function(){
const cols=[['rank','排名',true],['name','币种',false],['price','价格',true],['mcap','市值',true],
['chg24','24h',true],['mentions','提及',true],['upvotes','点赞',true],['reddit_sub','Reddit订阅',true],
['cscore','社区分',true],['news','新闻',true],['bili','B站视频',true],['date','研究日期',false]];
const t=document.getElementById('t_deep');
function render(rows){t.innerHTML='<tr>'+cols.map(c=>'<th data-k="'+c[0]+'" data-n="'+(c[2]?1:0)+'">'+c[1]+'</th>').join('')+'</tr>'+
rows.map(r=>'<tr><td>'+(r.rank||'-')+'</td><td>'+r.name+' <b style="color:#8b949e">'+r.sym+'</b></td><td>'+fp(r.price)+'</td><td>'+(r.mcap?'$'+fm(r.mcap):'-')+'</td><td class="'+cls(r.chg24)+'">'+pct(r.chg24)+'</td><td>'+(r.mentions||0)+'</td><td>'+(r.upvotes||0).toLocaleString()+'</td><td>'+(r.reddit_sub||0).toLocaleString()+'</td><td>'+(r.cscore==null?'-':r.cscore)+'</td><td>'+(r.news||0)+'</td><td>'+(r.bili||0)+'</td><td><span class="tag">'+r.date.slice(5)+'</span></td></tr>').join('');
t.querySelectorAll('th').forEach(th=>th.onclick=()=>{
const k=th.dataset.k,num=th.dataset.n==='1';const asc=th.dataset.asc!=='1';
t.querySelectorAll('th').forEach(x=>x.dataset.asc='0');th.dataset.asc=asc?'1':'0';
const rows=[...D.deep].sort((a,b)=>{const av=a[k]??(num?-Infinity:''),bv=b[k]??(num?-Infinity:'');
return (num?(bv||0)-(av||0):(String(bv).localeCompare(String(av))))*(asc?-1:1);});
render(rows);});}
render(D.deep);
})();

// ============ 稳定币 ============
(function(){
if(!D.stablecoins.length){document.getElementById('c_stable').innerHTML='<div style="color:#8b949e;padding:40px;text-align:center">暂无数据</div>';return;}
const s=D.stablecoins;
mk('c_stable',{grid:{left:60,right:70,top:40,bottom:40},
xAxis:{type:'category',data:s.map(x=>x.symbol),axisLabel:{color:TXT}},
yAxis:[{type:'value',name:'供应量',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:v=>fm(v)},splitLine:{lineStyle:{color:'#21262d'}}},
{type:'value',name:'24h增减',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:v=>fm(v)},splitLine:{show:false}}],
series:[{type:'bar',data:s.map(x=>x.total_supply),itemStyle:{color:'#58a6ff'},barWidth:'45%',label:{show:true,position:'top',color:SUB,fontSize:10,formatter:p=>'$'+fm(p.value)}},
{type:'scatter',yAxisIndex:1,data:s.map(x=>x.mint_change_24h),symbolSize:12,itemStyle:{color:p=>p.value>=0?UP:DOWN},
label:{show:true,position:'right',color:SUB,fontSize:9,formatter:p=>(p.value>=0?'+':'')+'$'+fm(p.value)}}]});
})();

// ============ 两日对比 ============
(function(){
if(!D.dayCmp.length){document.getElementById('c_cmp').innerHTML='<div style="color:#8b949e;padding:40px;text-align:center">暂无前一日快照</div>';return;}
mk('c_cmp',{grid:{left:70,right:60,top:40,bottom:40},
xAxis:{type:'category',data:D.dayCmp.map(x=>x.sym),axisLabel:{color:TXT}},
yAxis:{type:'value',name:'价格',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:v=>'$'+fm(v)},splitLine:{lineStyle:{color:'#21262d'}}},
series:[{type:'bar',name:'当前价',data:D.dayCmp.map(x=>({value:x.cur,itemStyle:{color:x.pct>=0?UP:DOWN}})),barWidth:'50%',
label:{show:true,position:'top',color:SUB,fontSize:10,formatter:p=>'$'+fm(p.value)}},
{type:'scatter',name:'前一日',data:D.dayCmp.map(x=>x.prev),symbol:'diamond',symbolSize:10,itemStyle:{color:'#8b949e'}}],
legend:{data:[{name:'当前价'},{name:'前一日'}],textStyle:{color:SUB},top:5}});
})();
} // end initDashboard

// DOM 就绪后启动渲染
(function(){
function start(){
  if (typeof echarts === 'undefined') {
    document.body.insertAdjacentHTML('afterbegin',
      '<div style="background:#f6465d;color:#fff;padding:12px;margin-bottom:12px;border-radius:8px">'+
      'ECharts 加载失败, 图表无法渲染。请检查网络或确认 reports/assets/echarts.min.js 存在。</div>');
    return;
  }
  try { initDashboard(); }
  catch(e){
    document.body.insertAdjacentHTML('afterbegin',
      '<div style="background:#f6465d;color:#fff;padding:12px;margin-bottom:12px;border-radius:8px">'+
      '渲染异常: '+e.message+'</div>');
    console.error(e);
  }
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
else start();
})();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="看板日期 YYYY-MM-DD, 默认取最新扫描日")
    args = ap.parse_args()

    scan_dir = os.path.join(ROOT, "data", "reports", "daily_scan")
    if not args.date:
        days = sorted(d for d in os.listdir(scan_dir)
                      if os.path.isdir(os.path.join(scan_dir, d)))
        if not days:
            sys.exit("无扫描数据")
        args.date = days[-1]

    data = collect_dashboard_data(args.date)

    echarts_path = os.path.join(ROOT, "reports", "assets", "echarts.min.js")
    with open(echarts_path, encoding="utf-8") as f:
        echarts_js = f.read()

    # 内嵌数据时, 转义 </script> 防止提前结束脚本块
    data_json = json.dumps(data, ensure_ascii=False).replace("</script>", "<\\/script>")

    html = (HTML_TMPL
            .replace("__ECHARTS__", echarts_js)
            .replace("__DATA__", data_json)
            .replace("__DATE__", args.date)
            .replace("__PREVDAY__", str(data["meta"]["prevDay"] or "-"))
            .replace("__CATDAY__", data["meta"]["catDay"])
            .replace("__SCANTIME__", str(data["meta"]["scanTime"] or "-"))
            .replace("__DEEPTOTAL__", str(data["meta"]["deepTotal"]))
            .replace("__LIGHTTOTAL__", str(data["meta"]["lightTotal"]))
            .replace("__COINCNT__", str(data["kpi"]["coinCnt"]))
            .replace("__DEEPCNT__", str(data["kpi"]["deepStudied"])))

    out = os.path.join(ROOT, "reports", "crypto_dashboard.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"看板已生成: {out} ({os.path.getsize(out)/1024:.0f} KB)")
    print(f"  日期: {args.date} | 币种: {data['kpi']['coinCnt']} | 深度研究: {data['kpi']['deepStudied']} | 板块: {len(data['cats'])}")


if __name__ == "__main__":
    main()
