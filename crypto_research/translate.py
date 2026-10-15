"""批量翻译推文为中文"""
import sqlite3, re

DB = r"C:\Users\P52S\DoubaoWork\chats\2026-09-25\new-chat\twitter_monitor\research.db"

# 核心翻译映射
T = {
    # 行情术语
    "bullish": "看涨", "bearish": "看跌", "pump": "拉盘", "dump": "砸盘",
    "long": "做多", "short": "做空", "ath": "历史新高", "support": "支撑位",
    "resistance": "阻力位", "breakout": "突破", "breakdown": "破位",
    "liquidation": "爆仓", "volume": "成交量", "whale": "巨鲸",
    "adoption": "采用", "partnership": "合作", "listing": "上币",
    "upgrade": "升级", "mainnet": "主网", "testnet": "测试网",
    "staking": "质押", "reward": "奖励", "burn": "销毁", "buyback": "回购",
    "token": "代币", "chain": "链", "wallet": "钱包", "exchange": "交易所",
    "futures": "合约", "spot": "现货", "leverage": "杠杆",
    "entry": "入场", "target": "目标价", "stop loss": "止损", "take profit": "止盈",
    "market cap": "市值", "circulating": "流通", "supply": "供应量",
    "bitcoin": "比特币", "ethereum": "以太坊", "solana": "索拉纳",
    "golden cross": "金叉", "death cross": "死叉",
    "RWA": "真实世界资产", "DeFi": "去中心化金融", "DEX": "去中心化交易所",
    "L1": "一层链", "L2": "二层链", "zk": "零知识证明",
    "TVL": "锁仓价值", "APY": "年化收益率",
    "etf": "ETF基金", "institutional": "机构",
    "grayscale": "灰度", "blackrock": "贝莱德",
    "altcoin": "山寨币", "memecoin": "迷因币",
    "airdrop": "空投", "testnet": "测试网",
    "dormant": "沉睡", "waking up": "醒来",
    "accumulation": "吸筹", "distribution": "派发",
    "consolidation": "盘整", "trend": "趋势",
    "sideways": "横盘", "volatile": "波动大",
    "overbought": "超买", "oversold": "超卖",
    "divergence": "背离", "confirmation": "确认",
    "candle": "K线", "timeframe": "时间周期",
    "1h": "1小时", "4h": "4小时", "1d": "日线", "1w": "周线",
    "bull pennant": "看涨旗形", "head and shoulders": "头肩顶",
    "buy the dip": "抄底", "sell the rally": "反弹减仓",
    "diamond hands": "钻石手", "paper hands": "纸手",
    "to the moon": "上月球", "ngmi": "不行", "wagmi": "我们行",
    "ser": "兄弟", "gm": "早上好", "gn": "晚安",
    "fine": "好吧", "cope": "自欺", "hopium": "希望毒",
    "maximalist": "极端主义者", "maxi": "极端主义者",
    "degen": "赌徒", "based": "有道理", "cope": "意淫",
    "szn": "季节", "fomo": "害怕错过", "fud": "恐惧不确定怀疑",
    "blue chip": "蓝筹", "frontier": "前沿",
    "narrative": "叙事", "story": "故事",
    "utility": "实用价值", "governance": "治理",
    "decentralized": "去中心化", "permissionless": "无需许可",
    "immutable": "不可篡改", "secure": "安全",
    "scalable": "可扩展", "interoperable": "可互操作",
}

def translate(text):
    result = text
    for en, zh in sorted(T.items(), key=lambda x: -len(x[0])):
        result = re.sub(rf'\b{re.escape(en)}\b', zh, result, flags=re.IGNORECASE)
    return result

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("SELECT id, text FROM tweets")
rows = c.fetchall()
for tid, text in rows:
    translated = translate(text)
    c.execute("UPDATE tweets SET text=? WHERE id=?", (translated, tid))
conn.commit()
print(f"Translated {len(rows)} tweets")
conn.close()
