# -*- coding: utf-8 -*-
"""补全分类：融合报告内「赛道」标签 + 人工校正，重算分类统计"""
import json, os, re
from collections import defaultdict

BASE = r"D:/gitpro/claude_trading"
BUNDLE = os.path.join(BASE, "docs/research/reports_bundle_all_20261015")
OUT = os.path.join(BASE, "docs/research/_work_20261015")
data = json.load(open(os.path.join(OUT, "parsed_projects.json"), encoding="utf-8"))

# 赛道标签 → 类别
TAG2CAT = [
    (r"稳定币|Yield-Bearing|收益型美元", "stablecoin"),
    (r"代币化股票|权证代币", "xstock"),
    (r"RWA.*信贷|结构化信用|私募信贷", "rwa_credit"),
    (r"RWA|美债基金|AAA CLO|再保险|代币化投资产品", "rwa_fund"),
    (r"Layer 1|L1 公链|智能合约公链|Web3 公链|公链", "l1"),
    (r"ZK 轻量级", "l2"), (r"Layer 2|L2", "l2"),
    (r"GameFi|链游|游戏|GambleFi|赌场|SportFi|Play-to-Earn", "gaming"),
    (r"NFT", "gaming_nft"), (r"Meme", "meme"),
    (r"抗量子|后量子", "quantum"), (r"隐私计算|FHE", "privacy_infra"),
    (r"隐私币|PoW 隐私|隐私 DeFi", "privacy"),
    (r"DePIN", "depin"), (r"AI.*DePIN|DePIN.*AI|AI.*算力|去中心化计算", "ai_depin"),
    (r"Bittensor 子网|AI", "ai"),
    (r"DEX|流动性聚合", "dex"), (r"跨链", "interop"),
    (r"硬件钱包|钱包", "wallet"), (r"CEX|交易所平台币", "exchange"),
    (r"支付", "payments"), (r"挖矿 / 质押", "staking"),
    (r"去中心化身份|DID", "ai_identity"), (r"DeFi 抵押品|借贷", "lending"),
    (r"DeFi 衍生品|合成", "dex_perp"), (r"DeFi.*保险", "insurance"),
    (r"DAO / 治理", "dao"), (r"BTC 分叉", "btc"), (r"比特币生态", "btc_ecosystem"),
    (r"BTC Rune", "btc_ecosystem"), (r"比特币挖矿", "depin"),
    (r"去中心化稳定币", "cdp"), (r"广告", "infra"), (r"知识图谱", "ai"),
    (r"CeFi", "cefi"), (r"企业级区块链", "l1"), (r"数据货币化|Agent 基础设施", "ai"),
    (r"DeFi", "defi_misc"), (r"L2 / 基础设施", "l2"),
]
def tag2cat(tag):
    for pat, c in TAG2CAT:
        if re.search(pat, tag):
            return c
    return None

# 人工校正（symbol → category）
MANUAL = {
    "GRAM": "l1", "SKY": "cdp", "MKR": "cdp", "WLFI": "defi_misc", "VVV": "ai",
    "RENDER": "ai_depin", "NEXO": "cefi", "NIGHT": "privacy", "INJ": "l1",
    "AKE": "gaming", "FLR": "infra", "TIA": "infra", "PRL": "ai_depin",
    "XPL": "stablecoin", "GNO": "l1", "MON": "l1", "LUNC": "meme", "ENS": "infra",
    "ZAMA": "privacy_infra", "A": "ai", "BAT": "infra", "BORG": "cefi", "S": "l1",
    "VSN": "wallet", "B": "btc_ecosystem", "H": "ai_identity", "META": "dao",
    "STONK": "meme", "ALFW": "xstock", "SOON": "l2", "FORM": "gaming",
    "ANVL": "lending", "MINA": "l2", "PROM": "ai", "FUN": "gaming",
    "BTW": "btc_ecosystem", "GRX": "btc_ecosystem", "DOG": "meme", "GT": "exchange",
    "ATH": "ai_depin", "PONS": "launchpad", "BITTENSOR": "ai", "KITE": "ai",
    "CC": "l1", "QNT": "interop", "RUNE": "interop", "ZRO": "interop", "W": "interop",
    "DBR": "interop", "SNX": "dex_perp", "DRV": "dex_perp", "DYDX": "dex_perp",
    "JST": "defi_misc", "SUN": "defi_misc", "CAP": "stablecoin", "BR": "lending",
    "OZO": "stablecoin", "RSR": "stablecoin", "PLUME": "rwa_fund", "ONDO": "rwa_fund",
    "ZBCN": "payments", "XCN": "payments", "2Z": "depin", "SHX": "depin",
    "JASMY": "depin", "PEAQ": "depin", "AWE": "depin", "GOMINING": "depin",
    "GEOD": "depin", "AIOZ": "depin", "THETA": "depin", "HNT": "depin",
    "RAY": "dex", "ORCA": "dex", "MET": "dex", "JUP": "dex", "CAKE": "dex",
    "1INCH": "dex", "ZRX": "dex", "CRV": "dex", "CVX": "dex",
    "M": "meme", "SKR": "gaming", "IMX": "gaming", "FLOW": "gaming",
    "BP": "exchange", "KOGE": "exchange", "BC": "exchange", "RLB": "exchange",
    "SHFL": "exchange", "HTX": "exchange", "BTSE": "exchange", "MX": "exchange",
    "TWT": "wallet", "SFP": "wallet", "PENGU": "gaming_nft", "NFT": "gaming_nft",
    "CARDS": "gaming_nft", "SUPER": "gaming_nft", "PIEVERSE": "infra",
    "BCAP": "infra", "SOSO": "infra", "TRAC": "infra", "BAT": "infra",
    "UB": "ai", "SN51": "ai", "SN64": "ai", "Q": "ai", "GENIUS": "ai",
    "OPEN": "ai", "DGAI": "ai", "NMR": "ai", "GLM": "ai_depin", "GRASS": "ai_depin",
    "RLC": "ai_depin", "ETHFI": "staking", "EIGEN": "staking", "LDO": "staking",
    "JTO": "staking", "ENA": "yield", "FF": "yield", "APYUSD": "yield",
    "OHM": "yield", "PENDLE": "yield", "KMNO": "lending", "SYRUP": "lending",
    "FLUID": "lending", "MORPHO": "lending", "COMP": "lending", "AAVE": "lending",
    "USDAI": "stablecoin", "YLDS": "stablecoin", "CASH": "stablecoin",
    "U": "stablecoin", "AVUSD": "stablecoin", "APXUSD": "stablecoin",
    "SOFID": "stablecoin", "REUSD": "stablecoin", "JPYC": "stablecoin",
    "JPYSC": "stablecoin", "CHIP": "stablecoin", "A7A5": "stablecoin",
    "FDUSD": "stablecoin", "KAIA": "exchange_l1", "CRO": "exchange_l1",
    "OKB": "exchange_l1", "BNB": "exchange_l1", "STRK": "l2", "ZK": "l2",
    "MNT": "l2", "POL": "l2", "ARB": "l2", "OP": "l2", "HYPE": "dex_perp",
    "ASTER": "dex_perp", "LIT": "dex_perp", "EDGE": "dex_perp",
    "PUMP": "launchpad", "WLD": "ai_identity", "VIRTUAL": "ai", "SENT": "ai",
    "TAO": "ai", "FET": "ai", "NEXO": "cefi", "QRL": "quantum", "NXM": "insurance",
    "FIL": "storage", "AR": "storage", "BTT": "storage", "LINK": "infra",
    "PYTH": "infra", "GRT": "infra", "API3": "infra", "XMR": "privacy",
    "ZEC": "privacy", "DASH": "privacy", "ZEN": "privacy", "BDX": "privacy",
    "RAIL": "privacy", "PAXG": "rwa_gold", "XAUT": "rwa_gold", "KAU": "rwa_gold",
    "KAG": "rwa_gold", "ULTIMA": "rwa_gold", "MSTRX": "xstock", "CRCLB": "xstock",
    "STRCX": "xstock", "BUIDL": "rwa_fund", "OUSG": "rwa_fund", "USTBL": "rwa_fund",
    "THBILL": "rwa_fund", "JTRSY": "rwa_fund", "SAFO": "rwa_fund", "MGLO": "rwa_fund",
    "STAC": "rwa_fund", "NOPAL": "rwa_fund", "ONYC": "rwa_fund", "PC0000031": "rwa_fund",
    "PC0000033": "rwa_fund", "PC0000023": "rwa_fund", "PC0000015": "rwa_fund",
    "PC0000085": "rwa_fund", "XRP": "payments", "XLM": "payments", "TRX": "payments",
    "RAIN": "payments", "STX": "btc_ecosystem", "BTC": "btc", "BCH": "btc",
    "BSV": "btc", "LTC": "btc", "XEC": "btc", "KAS": "btc", "QTUM": "btc",
    "DCR": "btc", "ETH": "l1_eth", "SOL": "l1", "AVAX": "l1", "SUI": "l1",
    "APT": "l1", "ADA": "l1", "DOT": "l1", "ATOM": "l1", "NEAR": "l1",
    "HBAR": "l1", "ICP": "l1", "EGLD": "l1", "ALGO": "l1", "CSPR": "l1",
    "IOTA": "l1", "SEI": "l1", "XDC": "l1", "CFX": "l1", "VET": "l1", "NEO": "l1",
    "XTZ": "l1", "ETC": "l1", "DOGE": "meme", "SHIB": "meme", "PEPE": "meme",
    "BONK": "meme", "WIF": "meme", "FLOKI": "meme", "FARTCOIN": "meme",
    "SPX": "meme", "NPC": "meme", "USELESS": "meme", "CHEEMS": "meme",
    "APEPE": "meme", "COCO": "meme", "MELANIA": "meme", "TRUMP": "meme",
    "BIANRENSHENG": "meme", "BINANCELIFE": "meme", "BAN": "meme",
    "AXS": "gaming", "SAND": "gaming", "MANA": "gaming", "GALA": "gaming",
    "APE": "gaming", "BEAM": "gaming", "CHZ": "gaming", "LEO": "exchange",
    "WBT": "exchange", "KCS": "exchange", "BGB": "exchange",
}

n_tag, n_manual = 0, 0
for p in data["projects"]:
    sym = p["symbol"]
    # 1) 报告赛道标签
    tag = p.get("track_tag")
    if tag:
        c = tag2cat(tag)
        if c:
            p["category"] = c; p["cat_source"] = "tag"; n_tag += 1
    # 2) 人工校正优先
    if sym in MANUAL:
        p["category"] = MANUAL[sym]; p["cat_source"] = "manual"; n_manual += 1

# RWA 信贷类（有明确标签的）
for p in data["projects"]:
    tag = p.get("track_tag") or ""
    if re.search(r"私募信贷|代币化信贷|结构化信用", tag):
        p["category"] = "rwa_credit"; p["cat_source"] = "tag"

CAT_NAMES = {
    "btc": "比特币生态/价值存储", "btc_ecosystem": "比特币 L2/生态", "privacy": "隐私币",
    "l1": "智能合约 L1", "l1_eth": "以太坊 L1", "l2": "Layer2/ZK 扩容",
    "exchange_l1": "交易所公链", "exchange": "交易所平台币", "wallet": "钱包",
    "dex": "DEX/AMM", "dex_perp": "Perp DEX/衍生品", "lending": "借贷",
    "staking": "质押/再质押", "yield": "收益/结构化", "cdp": "去中心化稳定币/CDP",
    "defi_misc": "其他 DeFi", "stablecoin": "稳定币", "rwa_gold": "RWA-黄金/实物",
    "rwa_fund": "RWA-代币化基金/国债", "rwa_credit": "RWA-代币化信贷", "xstock": "代币化股票",
    "ai": "AI", "ai_depin": "AI 算力/数据网络", "ai_identity": "AI/去中心化身份",
    "depin": "DePIN 物理基础设施", "gaming": "GameFi/iGaming", "gaming_nft": "NFT/IP",
    "meme": "Meme", "payments": "支付/跨境", "infra": "基础设施/预言机",
    "interop": "互操作/跨链", "storage": "存储", "insurance": "保险",
    "quantum": "量子抗性", "launchpad": "发射台/Launchpad", "cefi": "CeFi/资管",
    "privacy_infra": "隐私计算/FHE", "dao": "DAO/治理", "unclassified": "未分类",
}

by_cat = defaultdict(list)
for p in data["projects"]:
    by_cat[p["category"]].append(p)

cat_stats = []
for c, ps in by_cat.items():
    ps_sorted = sorted(ps, key=lambda x: x["rank"] or 9999)
    total_mcap = sum(x["mcap_b"] or 0 for x in ps)
    avg7d = [x["chg7d"] for x in ps if x["chg7d"] is not None]
    cat_stats.append({
        "category": c, "name": CAT_NAMES.get(c, c), "count": len(ps),
        "total_mcap_b": round(total_mcap, 2),
        "symbols": [x["symbol"] for x in ps_sorted],
        "top10": [{"symbol": x["symbol"], "rank": x["rank"], "mcap_b": x["mcap_b"],
                   "chg7d": x["chg7d"]} for x in ps_sorted[:10]],
        "avg_chg7d": round(sum(avg7d) / len(avg7d), 2) if avg7d else None,
    })
cat_stats.sort(key=lambda x: -x["total_mcap_b"])
data["category_stats"] = cat_stats
data["cat_names"] = CAT_NAMES

with open(os.path.join(OUT, "parsed_projects.json"), "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

print(f"tag-based: {n_tag}, manual: {n_manual}")
print(f"未分类残留: {[p['symbol'] for p in by_cat.get('unclassified', [])]}")
print("\n=== 最终分类汇总 ===")
for c in cat_stats:
    print(f"{c['name']:<20} n={c['count']:<4} mcap=${c['total_mcap_b']:>9.2f}B avg7d={c['avg_chg7d']}%")
    print(f"    {', '.join(c['symbols'][:18])}")
