# -*- coding: utf-8 -*-
"""生成多 agent 辩证分析用浓缩简报 briefing.md"""
import json, os
from collections import defaultdict

BASE = r"D:/gitpro/claude_trading"
OUT = os.path.join(BASE, "docs/research/_work_20261015")
data = json.load(open(os.path.join(OUT, "parsed_projects.json"), encoding="utf-8"))
ps = data["projects"]
cats = data["category_stats"]

def f(x, d=2):
    return f"{x:.{d}f}" if isinstance(x, (int, float)) else "NA"

lines = []
lines.append("# 数字货币全景研究简报（2026-10-15）\n")
lines.append("数据源：269 份市值靠前项目深研报告（2026-10-08~15 采集）+ 2026-08-26 全市场扫描基线。\n")

# 市场总览
tot_mcap = sum(p["mcap_b"] or 0 for p in ps)
lines.append("## 一、市场总览\n")
lines.append(f"- 覆盖项目数：{len(ps)}，合计市值 ~${tot_mcap:,.0f}B")
lines.append("- BTC ~$82.3K（10 月 8 日一度 $80.4K，较 8/26 基线 $78.4K 仍高 ~5%），ETH ~$2.49K，BNB ~$742")
lines.append("- 市场状态：9 月强势反弹后，10 月第一周急跌（多数项目 7 日跌 5-15%），BTC 从 $86K 回调至 $80K 区间")
down = [p for p in ps if (p["chg7d"] or 0) < 0]
lines.append(f"- 7 日下跌项目占比：{len(down)}/{len([p for p in ps if p['chg7d'] is not None])}\n")

# 分类汇总
lines.append("## 二、赛道分类汇总（按总市值降序）\n")
lines.append("| 赛道 | 项目数 | 总市值($B) | 7日均涨跌 | 代表项目 |")
lines.append("|---|---|---|---|---|")
for c in cats:
    if c["category"] == "unclassified":
        continue
    reps = ", ".join([t["symbol"] for t in c["top10"][:6]])
    lines.append(f"| {c['name']} | {c['count']} | {c['total_mcap_b']:.2f} | {f(c['avg_chg7d'])}% | {reps} |")

# 市值分层
lines.append("\n## 三、市值分层\n")
tiers = [(1000, ">$100B 巨无霸"), (100, "$10B-100B 大盘"), (10, "$1B-10B 中盘"), (1, "$0.1B-1B 小盘"), (0, "<$0.1B 微盘")]
for t, name in tiers:
    sel = [p for p in ps if p["mcap_b"] is not None and (p["mcap_b"] >= t if t > 0 else p["mcap_b"] < 1)]
    if t == 1: sel = [p for p in ps if 0.1 <= (p["mcap_b"] or 0) < 1]
    if t == 0: sel = [p for p in ps if (p["mcap_b"] or 0) < 0.1]
    if sel:
        avg7 = [p["chg7d"] for p in sel if p["chg7d"] is not None]
        lines.append(f"- {name}：{len(sel)} 个，7 日均涨跌 {f(sum(avg7)/len(avg7) if avg7 else None)}%")

# 7 日涨跌
lines.append("\n## 四、7 日动量：涨幅 Top20 / 跌幅 Top20\n")
g = sorted([p for p in ps if p["chg7d"] is not None], key=lambda x: -x["chg7d"])
lines.append("**涨幅 Top20**：" + "; ".join([f"{p['symbol']}(#{p['rank']}, +{p['chg7d']:.0f}%, {data['cat_names'].get(p['category'], p['category'])})" for p in g[:20]]))
lines.append("\n**跌幅 Top20**：" + "; ".join([f"{p['symbol']}(#{p['rank']}, {p['chg7d']:.0f}%, {data['cat_names'].get(p['category'], p['category'])})" for p in g[-20:]]))

# Aug→Oct 市值变化
lines.append("\n## 五、Aug26 → Oct15 市值变化（约 7 周，反映中期资金流向）\n")
ch = []
for p in ps:
    if p.get("aug26_mcap_b") and p["mcap_b"] and p["aug26_mcap_b"] > 0.1:
        ch.append((p["symbol"], p["rank"], round(p["mcap_b"] / p["aug26_mcap_b"] * 100 - 100, 1),
                   p["aug26_mcap_b"], p["mcap_b"], p["category"]))
ch.sort(key=lambda x: -x[2])
lines.append("**增长 Top20**：" + "; ".join([f"{x[0]}(#{x[1]}, +{x[2]:.0f}%, ${x[3]}B→${x[4]}B, {data['cat_names'].get(x[5], x[5])})" for x in ch[:20]]))
lines.append("\n**萎缩 Top15**：" + "; ".join([f"{x[0]}(#{x[1]}, {x[2]:.0f}%, ${x[3]}B→${x[4]}B, {data['cat_names'].get(x[5], x[5])})" for x in ch[-15:]]))

# FDV/流通率分析
lines.append("\n## 六、解锁压力：FDV/MCap 比率 Top20（流通率低 = 未来抛压大）\n")
fdv = []
for p in ps:
    if p["mcap_b"] and p["fdv_b"] and p["mcap_b"] > 0.05:
        ratio = p["fdv_b"] / p["mcap_b"]
        fdv.append((p["symbol"], p["rank"], round(ratio, 2), round(100 / ratio, 1), p["category"], p["mcap_b"]))
fdv.sort(key=lambda x: -x[2])
lines.append("| 项目 | 排名 | FDV/MCap | 流通率% | 赛道 | 市值$B |")
lines.append("|---|---|---|---|---|---|")
for x in fdv[:20]:
    lines.append(f"| {x[0]} | #{x[1]} | {x[2]} | {x[3]} | {data['cat_names'].get(x[4], x[4])} | {x[5]:.3f} |")
low_fdv = sorted(fdv, key=lambda x: x[2])[:15]
lines.append("\n**全流通/接近全流通（解锁压力小）**：" + "; ".join([f"{x[0]}(流通{x[3]}%)" for x in low_fdv]))

# 关键项目近期变化摘录（各赛道挑代表性项目）
lines.append("\n## 七、代表性项目「近期关键变化」摘录\n")
pick = ["HYPE", "TAO", "ZEC", "RAIN", "ONDO", "BUIDL", "GRASS", "RENDER", "STRK", "ENA",
        "UNI", "AAVE", "LIT", "ASTER", "PUMP", "NIGHT", "VVV", "WLD", "KITE", "QRL",
        "BTW", "QNT", "NEAR", "RAY", "MSTRX", "CRCLB", "USDAI", "FDUSD", "XPL", "PLUME",
        "MORPHO", "EIGEN", "ETHFI", "JTO", "LDO", "TIA", "FIL", "HNT", "AIOZ", "GOMINING",
        "AXS", "PENGU", "BONK", "DOGE", "WLFI", "SKY", "MKR", "APXUSD", "APYUSD", "FDUSD"]
by_sym = {p["symbol"]: p for p in ps}
for s in pick:
    p = by_sym.get(s)
    if not p:
        continue
    chs = p.get("recent_changes", [])[:3]
    if chs:
        lines.append(f"\n**{s}** ({data['cat_names'].get(p['category'])}, #{p['rank']}, mcap ${p['mcap_b']}B, 7d {f(p['chg7d'])}%):")
        for c in chs:
            lines.append(f"  - {c}")

with open(os.path.join(OUT, "briefing.md"), "w", encoding="utf-8") as fp:
    fp.write("\n".join(lines))
print(f"briefing.md written, {len(lines)} lines, {os.path.getsize(os.path.join(OUT, 'briefing.md'))} bytes")
