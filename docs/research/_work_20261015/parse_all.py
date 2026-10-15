# -*- coding: utf-8 -*-
"""解析 reports_bundle_all_20261015 全部 269 份 MD 报告 + 索引 CSV + Aug-26 基线
输出结构化 JSON：指标 / 近期变化 / 历史节点 / 多空论据 / 风险 / 三档估值 + 分类
"""
import csv, json, os, re, glob, sys
from collections import defaultdict

BASE = r"D:/gitpro/claude_trading"
BUNDLE = os.path.join(BASE, "docs/research/reports_bundle_all_20261015")
BASELINE = os.path.join(BASE, "data/reports/daily_scan/2026-08-26/top_800_light/all_coins.json")
OUT = os.path.join(BASE, "docs/research/_work_20261015")
os.makedirs(OUT, exist_ok=True)

# ---------------- 分类体系（投资视角，20 类） ----------------
CAT = {
    # 价值存储/比特币生态系
    "BTC": "btc", "BCH": "btc", "BSV": "btc", "LTC": "btc", "XEC": "btc", "KAS": "btc",
    "QTUM": "btc", "DCR": "btc", "GRX": "btc", "DOG": "btc", "STX": "btc_ecosystem",
    # 隐私币
    "XMR": "privacy", "ZEC": "privacy", "DASH": "privacy", "ZEN": "privacy", "BDX": "privacy",
    "RAIL": "privacy", "SCRT": "privacy",
    # 智能合约 L1
    "ETH": "l1_eth", "SOL": "l1", "BNB": "l1_exchange", "AVAX": "l1", "SUI": "l1", "APT": "l1",
    "TON": "l1", "ADA": "l1", "DOT": "l1", "ATOM": "l1", "NEAR": "l1", "HBAR": "l1",
    "ICP": "l1", "EGLD": "l1", "ALGO": "l1", "FLOW": "l1_gaming", "CSPR": "l1", "IOTA": "l1",
    "SEI": "l1", "KAIA": "l1", "XDC": "l1", "CFX": "l1", "VET": "l1", "NEO": "l1",
    "XTZ": "l1", "ETC": "l1", "CC": "l1", "QNT": "interop", "RUNE": "interop", "ZRO": "interop",
    "W": "interop", "DBR": "interop",
    # Layer2 / 扩容
    "ARB": "l2", "OP": "l2", "STRK": "l2", "ZK": "l2", "MNT": "l2", "METIS": "l2",
    "POL": "l2", "IMX": "gaming", "BOBA": "l2", "SONEI": "l2",
    # DeFi - DEX/交易/perp
    "UNI": "dex", "AERO": "dex", "RAY": "dex", "ORCA": "dex", "CAKE": "dex", "JUP": "dex",
    "MET": "dex", "1INCH": "dex", "ZRX": "dex", "DYDX": "dex_perp", "HYPE": "dex_perp",
    "ASTER": "dex_perp", "LIT": "dex_perp", "EDGE": "dex_perp", "DRV": "derivatives",
    "FLUID": "lending", "JST": "defi_misc", "SUN": "defi_misc", "SNX": "derivatives",
    "GMX": "derivatives",
    # DeFi - 借贷
    "AAVE": "lending", "COMP": "lending", "MORPHO": "lending", "KMNO": "lending",
    "SYRUP": "lending", "CAP": "stablecoin", "BR": "lending",
    # DeFi - 质押/再质押
    "LDO": "staking", "JTO": "staking", "ETHFI": "staking", "EIGEN": "staking",
    "SWELL": "staking",
    # DeFi - 收益/结构化
    "PENDLE": "yield", "ENA": "yield", "FF": "yield", "APYUSD": "yield", "OHM": "yield",
    "CRV": "dex", "CVX": "dex", "BAL": "dex", "SPELL": "lending",
    # 稳定币
    "FDUSD": "stablecoin", "USDAI": "stablecoin", "YLDS": "stablecoin", "CASH": "stablecoin",
    "U": "stablecoin", "AVUSD": "stablecoin", "APXUSD": "stablecoin", "SOFID": "stablecoin",
    "REUSD": "stablecoin", "JPYC": "stablecoin", "JPYSC": "stablecoin", "CHIP": "stablecoin",
    "USDE": "stablecoin", "USDX": "stablecoin", "A7A5": "stablecoin", "OZO": "stablecoin",
    "RSR": "stablecoin", "USDD": "stablecoin", "PYUSD": "stablecoin", "TUSD": "stablecoin",
    # RWA - 实物/黄金
    "PAXG": "rwa_gold", "XAUT": "rwa_gold", "KAU": "rwa_gold", "KAG": "rwa_gold",
    "ULTIMA": "rwa_gold",
    # RWA - 代币化基金/国债/信贷
    "BUIDL": "rwa_fund", "OUSG": "rwa_fund", "USTBL": "rwa_fund", "THBILL": "rwa_fund",
    "JTRSY": "rwa_fund", "SAFO": "rwa_fund", "MGLO": "rwa_fund", "STAC": "rwa_fund",
    "NOPAL": "rwa_fund", "ONYC": "rwa_fund", "PC0000031": "rwa_fund", "PC0000033": "rwa_fund",
    "PC0000023": "rwa_fund", "PC0000015": "rwa_fund", "PC0000085": "rwa_fund",
    "ONDO": "rwa_fund", "PLUME": "rwa_fund", "TRAC": "interop",
    # 代币化股票
    "MSTRX": "xstock", "CRCLB": "xstock", "STRCX": "xstock", "TSLAX": "xstock",
    # AI
    "TAO": "ai", "FET": "ai", "GRASS": "ai_depin", "SENT": "ai", "VIRTUAL": "ai",
    "WLD": "ai_identity", "RLC": "ai_depin", "NMR": "ai", "DGAI": "ai", "KITE": "ai",
    "GENIUS": "ai", "OPEN": "ai", "Q": "ai", "GLM": "ai_depin", "AI": "ai", "UB": "ai",
    "SN51": "ai", "SN64": "ai", "AIT": "ai",
    # DePIN
    "HNT": "depin", "ATH": "depin", "GEOD": "depin", "AIOZ": "depin", "THETA": "depin",
    "PEAQ": "depin", "GOMINING": "depin", "AWE": "depin", "JASMY": "depin", "XNET": "depin",
    "2Z": "depin", "SHX": "depin", "ZBCN": "payments",
    # 游戏 / NFT / 元宇宙
    "AXS": "gaming", "SAND": "gaming", "MANA": "gaming", "GALA": "gaming", "APE": "gaming",
    "PENGU": "gaming_nft", "BEAM": "gaming", "SUPER": "gaming_nft", "CHZ": "gaming",
    "M": "meme", "NFT": "gaming_nft", "CARDS": "gaming_nft", "SKR": "gaming",
    "TLM": "gaming", "ILV": "gaming", "YGG": "gaming", "MAGIC": "gaming",
    # Meme
    "DOGE": "meme", "SHIB": "meme", "PEPE": "meme", "BONK": "meme", "WIF": "meme",
    "FLOKI": "meme", "FARTCOIN": "meme", "SPX": "meme", "NPC": "meme", "USELESS": "meme",
    "CHEEMS": "meme", "APEPE": "meme", "COCO": "meme", "MELANIA": "meme", "TRUMP": "meme",
    "BIANRENSHENG": "meme", "BINANCELIFE": "meme", "BAN": "meme", "MOODENG": "meme",
    "POPCAT": "meme", "NEIRO": "meme", "TURBO": "meme", "BOME": "meme", "MEW": "meme",
    "MYRO": "meme", "WEN": "meme", "PONKE": "meme", "GIGA": "meme", "MOG": "meme",
    "RETARDIO": "meme", "LOCKIN": "meme",
    # 交易所平台币
    "LEO": "exchange", "WBT": "exchange", "OKB": "exchange", "KCS": "exchange",
    "BGB": "exchange", "GT": "exchange", "MX": "exchange", "HTX": "exchange",
    "CRO": "exchange", "BTSE": "exchange", "BC": "exchange", "RLB": "exchange",
    "SHFL": "exchange", "TWT": "wallet", "SFP": "wallet", "BP": "exchange",
    "KOGE": "exchange",
    # 钱包
    "SFP": "wallet", "TWT": "wallet",
    # 支付/跨境
    "XRP": "payments", "XLM": "payments", "TRX": "payments", "RAIN": "payments",
    "XCN": "payments",
    # 基础设施/中间件/预言机
    "LINK": "infra", "PYTH": "infra", "GRT": "infra", "API3": "infra", "TRAC": "infra",
    "BAND": "infra", "SOSO": "infra", "PIEVERSE": "infra", "BCAP": "infra",
    "SYN": "interop", "STG": "interop", "AXL": "interop", "CORE": "interop",
    # 存储
    "FIL": "storage", "AR": "storage", "BTT": "storage", "STORJ": "storage",
    "SC": "storage", "SIAC": "storage",
    # 保险/其他
    "NXM": "insurance", "SOSO": "infra",
    # 量子抗性
    "QRL": "quantum",
    # launchpad / 发射台
    "PUMP": "launchpad",
}
# 交易所生态 L1：BNB 同时是 L1 + 交易所代币，归入 l1_exchange；OKB/OKT 同理
CAT["BNB"] = "exchange_l1"
CAT["CRO"] = "exchange_l1"
CAT["OKB"] = "exchange_l1"
CAT["KAIA"] = "exchange_l1"  # Kakao/Line
CAT["GT"] = "exchange_l1"

CAT_NAMES = {
    "btc": "比特币生态/价值存储", "btc_ecosystem": "比特币 L2/生态", "privacy": "隐私币",
    "l1": "智能合约 L1", "l1_eth": "以太坊 L1", "l2": "Layer2/扩容",
    "l1_exchange": "交易所公链", "exchange_l1": "交易所公链", "exchange": "交易所平台币",
    "wallet": "钱包",
    "dex": "DEX/AMM", "dex_perp": "Perp DEX/衍生品", "derivatives": "衍生品/合成资产",
    "lending": "借贷", "staking": "质押/再质押", "yield": "收益/结构化",
    "defi_misc": "其他 DeFi",
    "stablecoin": "稳定币", "rwa_gold": "RWA-黄金/实物", "rwa_fund": "RWA-代币化基金/国债",
    "xstock": "代币化股票",
    "ai": "AI", "ai_depin": "AI+DePIN 算力/数据", "ai_identity": "AI+身份",
    "depin": "DePIN 物理基础设施",
    "gaming": "GameFi", "gaming_nft": "NFT/IP", "meme": "Meme",
    "payments": "支付/跨境", "infra": "基础设施/预言机", "interop": "互操作/跨链",
    "storage": "存储", "insurance": "保险", "quantum": "量子抗性", "launchpad": "发射台",
}

def classify(symbol, name):
    s = (symbol or "").upper()
    if s in CAT:
        return CAT[s]
    # 名称兜底规则
    n = (name or "").lower()
    rules = [
        (r"stable|usd|dollar", "stablecoin"), (r"gold|silver", "rwa_gold"),
        (r"treasury|fund|bill|bond|money market", "rwa_fund"),
        (r"xstock|tokenized stock", "xstock"), (r"meme|inu|dog|cat|pepe", "meme"),
        (r"ai |artificial|agent", "ai"), (r"staking|restak", "staking"),
        (r"swap|dex|exchange", "dex"), (r"chain|l1|network", "l1"),
    ]
    for pat, c in rules:
        if re.search(pat, n):
            return c
    return "unclassified"

# ---------------- 解析索引 ----------------
rows = []
with open(os.path.join(BUNDLE, "_index_by_mcap.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if not r.get("symbol"):
            continue
        rows.append(r)
print(f"index rows: {len(rows)}")

def parse_md(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    d = {"md_file": os.path.basename(path)}
    m = re.search(r"^#\s+(.+?)\s*$", text, re.M)
    d["title"] = m.group(1).strip() if m else ""
    m = re.search(r"追踪时间：([\d\-]+)", text)
    d["track_date"] = m.group(1) if m else None
    m = re.search(r"整理时间：([\d\-]+)", text)
    if m and not d["track_date"]:
        d["track_date"] = m.group(1)
    m = re.search(r"排名\s*#?([\d\-–]+)", text)
    d["rank_in_report"] = m.group(1) if m else None
    m = re.search(r"赛道：(.+)", text)
    d["track_tag"] = m.group(1).strip() if m else None
    # 近期变化 / 事件 bullet 列表
    bullets = []
    m = re.search(r"##\s*(?:二、)?近期关键变化(.+?)(?=\n##\s|\Z)", text, re.S)
    sec = m.group(1) if m else ""
    if not sec:
        m = re.search(r"##\s*(?:四、)?最近重要事件(.+?)(?=\n##\s|\Z)", text, re.S)
        sec = m.group(1) if m else ""
    for line in sec.splitlines():
        line = line.strip()
        if line.startswith("- "):
            bullets.append(line[2:].strip())
    d["recent_changes"] = bullets
    # 历史节点表
    hist = []
    m = re.search(r"##\s*历史关键节点(.+?)(?=\n##\s|\Z)", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r"\|\s*(\d{4}[\-年][\d\-]+)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|", line)
            if mm:
                hist.append({"date": mm.group(1), "event": mm.group(2), "note": mm.group(3)})
    d["history"] = hist
    # 多空论据
    bull, bear = [], []
    m = re.search(r"\*\*多头\*\*[：:]\s*(.+)", text)
    if m:
        bull = [x.strip() for x in re.split(r"[；;]", m.group(1)) if x.strip()]
    m = re.search(r"\*\*空头\*\*[：:]\s*(.+)", text)
    if m:
        bear = [x.strip() for x in re.split(r"[；;]", m.group(1)) if x.strip()]
    if not bull:
        m = re.search(r"###\s*多头(.+?)(?=###|\n##\s|\Z)", text, re.S)
        if m:
            for line in m.group(1).splitlines():
                mm = re.match(r"\d+\.\s*\*\*(.+?)\*\*", line.strip())
                if mm:
                    bull.append(mm.group(1))
    if not bear:
        m = re.search(r"###\s*空头(.+?)(?=###|\n##\s|\Z)", text, re.S)
        if m:
            for line in m.group(1).splitlines():
                mm = re.match(r"\d+\.\s*\*\*(.+?)\*\*", line.strip())
                if mm:
                    bear.append(mm.group(1))
    d["bull"], d["bear"] = bull, bear
    # 风险
    risks = []
    m = re.search(r"##\s*(?:六、)?关键风险(.+?)(?=\n##\s|\n---|\Z)", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r"[-|]\s*(?:\*\*)?([^|：:*\-]+?)(?:\*\*)?[：:]\s*(.+)", line.strip())
            if mm:
                risks.append(f"{mm.group(1).strip()}: {mm.group(2).strip()}")
            elif line.strip().startswith("- "):
                risks.append(line.strip()[2:])
    d["risks"] = risks
    # 三档估值
    val = {}
    for line in text.splitlines():
        if "悲观" in line and "|" in line:
            mm = re.findall(r"\$([\d,\.]+)", line)
            if mm: val["bear"] = mm
        if "中性" in line and "|" in line:
            mm = re.findall(r"\$([\d,\.]+)", line)
            if mm: val["base"] = mm
        if "乐观" in line and "|" in line:
            mm = re.findall(r"\$([\d,\.]+)", line)
            if mm: val["bull"] = mm
    d["valuation"] = val
    return d

projects = []
for r in rows:
    p = {
        "rank": int(r["rank"]) if r["rank"] else None,
        "symbol": r["symbol"], "name": r["name"],
        "price": float(r["price"]) if r["price"] else None,
        "mcap_b": float(r["mcap_billion"]) if r["mcap_billion"] else None,
        "fdv_b": float(r["fdv_billion"]) if r["fdv_billion"] else None,
        "chg24h": float(r["chg24h_pct"]) if r["chg24h_pct"] else None,
        "chg7d": float(r["chg7d_pct"]) if r["chg7d_pct"] else None,
        "report_date": r["report_date"],
    }
    md = os.path.join(BUNDLE, r["md_file"])
    if os.path.exists(md):
        p.update(parse_md(md))
    p["category"] = classify(p["symbol"], p["name"])
    projects.append(p)

# ---------------- Aug-26 基线 ----------------
with open(BASELINE, encoding="utf-8") as f:
    base = {b["symbol"]: b for b in json.load(f)}
for p in projects:
    b = base.get(p["symbol"])
    if b:
        p["aug26_mcap_b"] = round(b["market_cap"] / 1e9, 4)
        p["aug26_rank"] = b["rank"]
        p["aug26_chg7d"] = b.get("change_7d_pct")

# ---------------- 聚合统计 ----------------
by_cat = defaultdict(list)
for p in projects:
    by_cat[p["category"]].append(p)

cat_stats = []
for c, ps in by_cat.items():
    ps_sorted = sorted(ps, key=lambda x: x["rank"] or 9999)
    total_mcap = sum(x["mcap_b"] or 0 for x in ps)
    avg7d = [x["chg7d"] for x in ps if x["chg7d"] is not None]
    cat_stats.append({
        "category": c, "name": CAT_NAMES.get(c, c), "count": len(ps),
        "total_mcap_b": round(total_mcap, 2),
        "top10": [{"symbol": x["symbol"], "rank": x["rank"], "mcap_b": x["mcap_b"],
                   "chg7d": x["chg7d"]} for x in ps_sorted[:10]],
        "avg_chg7d": round(sum(avg7d) / len(avg7d), 2) if avg7d else None,
    })
cat_stats.sort(key=lambda x: -x["total_mcap_b"])

out = {
    "generated": "2026-10-15",
    "n_projects": len(projects),
    "projects": projects,
    "category_stats": cat_stats,
}
with open(os.path.join(OUT, "parsed_projects.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# 汇总输出
print("\n=== 分类汇总（按总市值） ===")
for c in cat_stats:
    print(f"{c['name']:<22} n={c['count']:<4} mcap=${c['total_mcap_b']:>9.2f}B  avg7d={c['avg_chg7d']}%")
print("\n=== 未分类 ===")
print([p["symbol"] for p in by_cat.get("unclassified", [])])
print("\n=== 7 日涨幅 Top15 ===")
g = sorted([p for p in projects if p["chg7d"] is not None], key=lambda x: -x["chg7d"])[:15]
for p in g:
    print(f"  {p['symbol']:<10} rank#{p['rank']:<4} 7d={p['chg7d']:>8.2f}%  mcap=${p['mcap_b']}B  [{p['category']}]")
print("\n=== 7 日跌幅 Top15 ===")
l = sorted([p for p in projects if p["chg7d"] is not None], key=lambda x: x["chg7d"])[:15]
for p in l:
    print(f"  {p['symbol']:<10} rank#{p['rank']:<4} 7d={p['chg7d']:>8.2f}%  mcap=${p['mcap_b']}B  [{p['category']}]")
print("\n=== Aug26 → Oct15 市值变化 Top15（有基线的） ===")
ch = []
for p in projects:
    if p.get("aug26_mcap_b") and p["mcap_b"] and p["aug26_mcap_b"] > 0.1:
        ch.append((p["symbol"], p["rank"], round(p["mcap_b"] / p["aug26_mcap_b"] * 100 - 100, 1),
                   p["aug26_mcap_b"], p["mcap_b"], p["category"]))
ch.sort(key=lambda x: -x[2])
for x in ch[:15]:
    print(f"  {x[0]:<10} rank#{x[1]:<4} mcap变化={x[2]:>8.1f}%  (${x[3]}B → ${x[4]}B) [{x[5]}]")
print("\n=== Aug26 → Oct15 市值跌幅 Top10 ===")
for x in ch[-10:]:
    print(f"  {x[0]:<10} rank#{x[1]:<4} mcap变化={x[2]:>8.1f}%  (${x[3]}B → ${x[4]}B) [{x[5]}]")
print(f"\n输出: {OUT}/parsed_projects.json")
