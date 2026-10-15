import sqlite3
import sys
from datetime import datetime

DB_PATH = r"C:\Users\P52S\DoubaoWork\chats\2026-09-25\new-chat\twitter_monitor\tweets.db"

def query_tweets(project=None, keyword=None, limit=20):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    sql = "SELECT project, author, author_handle, text, created_at, likes, retweets FROM tweets WHERE 1=1"
    params = []
    if project:
        sql += " AND project=?"
        params.append(project)
    if keyword:
        sql += " AND text LIKE ?"
        params.append(f"%{keyword}%")
    sql += " ORDER BY scraped_at DESC LIMIT ?"
    params.append(limit)
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    return rows

def query_events(project=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if project:
        c.execute("SELECT project, event_type, title, description, event_date, source FROM events WHERE project=? ORDER BY event_date DESC", (project,))
    else:
        c.execute("SELECT project, event_type, title, description, event_date, source FROM events ORDER BY event_date DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def query_prices(project=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if project:
        c.execute("SELECT project, price, change_24h, market_cap, snapshot_at FROM price_snapshots WHERE project=? ORDER BY snapshot_at", (project,))
    else:
        c.execute("SELECT project, price, change_24h, market_cap, snapshot_at FROM price_snapshots ORDER BY snapshot_at")
    rows = c.fetchall()
    conn.close()
    return rows

def stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT project, COUNT(*) FROM tweets GROUP BY project")
    tweet_counts = c.fetchall()
    c.execute("SELECT project, COUNT(*) FROM events GROUP BY project")
    event_counts = c.fetchall()
    conn.close()
    return tweet_counts, event_counts

if __name__ == '__main__':
    print("=" * 60)
    print("CRYPTO TWITTER MONITOR - DATA QUERY")
    print("=" * 60)
    
    tc, ec = stats()
    print("\n[数据库统计]")
    for p, cnt in tc:
        print(f"  {p}: {cnt} 条推文")
    for p, cnt in ec:
        print(f"  {p}: {cnt} 个事件")
    
    print("\n" + "=" * 60)
    print("[关键事件时间线]")
    print("=" * 60)
    for row in query_events():
        proj, etype, title, desc, date, source = row
        print(f"\n  [{date}] {proj} ({etype})")
        print(f"    {title}")
        print(f"    {desc}")
        print(f"    来源: {source}")
    
    print("\n" + "=" * 60)
    print("[最新价格快照]")
    print("=" * 60)
    for row in query_prices():
        proj, price, chg, mcap, ts = row
        print(f"  {proj}: ${price} ({chg}%) 市值:{mcap} @ {ts}")
    
    print("\n" + "=" * 60)
    print("[高互动推文 TOP 10]")
    print("=" * 60)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT project, author, text, likes FROM tweets ORDER BY likes DESC LIMIT 10")
    for proj, author, text, likes in c.fetchall():
        print(f"\n  [{proj}] @{author} ({likes} likes)")
        print(f"    {text[:200]}")
    conn.close()
