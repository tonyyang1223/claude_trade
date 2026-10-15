"""导出数据库为JSON供HTML使用"""
import json
import sqlite3
import time
import os
from db import DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 所有项目+最新价格
c.execute("""
SELECT p.symbol, p.name, p.category, p.website, p.twitter, p.github, p.description,
  (SELECT price FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as price,
  (SELECT change_1h FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as chg1h,
  (SELECT change_24h FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as chg24h,
  (SELECT change_7d FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as chg7d,
  (SELECT change_30d FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as chg30d,
  (SELECT market_cap FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as mcap,
  (SELECT volume_24h FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as vol,
  (SELECT ath FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as ath,
  (SELECT circulating_supply FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as circ,
  (SELECT total_supply FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as total,
  (SELECT fdv FROM price_snapshots WHERE project=p.symbol ORDER BY snapshot_at DESC LIMIT 1) as fdv,
  (SELECT COUNT(*) FROM events WHERE project=p.symbol) as event_cnt,
  (SELECT COUNT(*) FROM tweets WHERE project=p.symbol) as tweet_cnt
FROM projects p ORDER BY mcap DESC
""")
projects = [dict(r) for r in c.fetchall()]

# 所有事件
c.execute("SELECT * FROM events ORDER BY event_date DESC")
events = [dict(r) for r in c.fetchall()]

# 所有推文
c.execute("SELECT * FROM tweets ORDER BY likes DESC")
tweets = [dict(r) for r in c.fetchall()]

conn.close()

output = {
    "projects": projects,
    "events": events,
    "tweets": tweets,
    "last_updated": time.strftime("%Y-%m-%d %H:%M")
}

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"Exported {len(projects)} projects, {len(events)} events, {len(tweets)} tweets to {out_path}")
