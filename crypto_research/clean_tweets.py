"""清洗推文并翻译成中文摘要"""
import sqlite3
import re

DB = r"C:\Users\P52S\DoubaoWork\chats\2026-09-25\new-chat\twitter_monitor\research.db"

# 简单翻译映射
translations = {
    "bullish": "看多", "bearish": "看空", "pump": "拉盘", "dump": "砸盘",
    "long": "做多", "short": "做空", "ath": "历史新高", "support": "支撑",
    "resistance": "阻力", "breakout": "突破", "liquidation": "爆仓",
    "volume": "成交量", "whale": "巨鲸", "adoption": "采用", "partnership": "合作",
    "listing": "上币", "upgrade": "升级", "mainnet": "主网", "testnet": "测试网",
    "staking": "质押", "reward": "奖励", "burn": "销毁", "buyback": "回购",
    "token": "代币", "chain": "链", "wallet": "钱包", "exchange": "交易所",
    "futures": "合约", "options": "期权", "spot": "现货", "leverage": "杠杆",
    "entry": "入场", "target": "目标", "stop loss": "止损", "take profit": "止盈",
    "market cap": "市值", "circulating": "流通", "supply": "供应量",
    "bitcoin": "比特币", "ethereum": "以太坊", "solana": "索拉纳",
}

def clean_tweet(text):
    """清洗推文文本"""
    # 去掉多余空行
    text = re.sub(r'\n+', '\n', text)
    # 去掉开头的作者信息行
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line: continue
        if line in ['显示更多', '显示原文', '翻译自 英语', '翻译自 韩语', '翻译自 土耳其语']: continue
        if line.startswith('回复 @'): continue
        cleaned.append(line)
    return ' '.join(cleaned)[:300]

def simple_translate(text):
    """简单关键词翻译"""
    result = text
    for en, zh in translations.items():
        result = re.sub(rf'\b{en}\b', zh, result, flags=re.IGNORECASE)
    return result

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("SELECT id, text FROM tweets")
rows = c.fetchall()
for tid, text in rows:
    cleaned = clean_tweet(text)
    translated = simple_translate(cleaned)
    c.execute("UPDATE tweets SET text=? WHERE id=?", (translated, tid))
conn.commit()
print(f"Cleaned {len(rows)} tweets")

# 统计
c.execute("SELECT project, COUNT(*) FROM tweets GROUP BY project")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]} tweets")
conn.close()
