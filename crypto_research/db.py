import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 项目基本信息
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        coin_gecko_id TEXT,
        category TEXT,
        description TEXT,
        website TEXT,
        twitter TEXT,
        github TEXT,
        contract TEXT,
        added_at TEXT,
        last_updated TEXT,
        notes TEXT
    )''')

    # 推文
    c.execute('''CREATE TABLE IF NOT EXISTS tweets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT NOT NULL,
        tweet_id TEXT UNIQUE,
        author TEXT,
        author_handle TEXT,
        text TEXT,
        created_at TEXT,
        likes INTEGER DEFAULT 0,
        retweets INTEGER DEFAULT 0,
        replies INTEGER DEFAULT 0,
        views TEXT,
        url TEXT,
        sentiment TEXT,
        scraped_at TEXT,
        raw_json TEXT
    )''')

    # 价格快照
    c.execute('''CREATE TABLE IF NOT EXISTS price_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT NOT NULL,
        price REAL,
        change_1h REAL,
        change_24h REAL,
        change_7d REAL,
        change_30d REAL,
        market_cap REAL,
        volume_24h REAL,
        ath REAL,
        ath_date TEXT,
        atl REAL,
        circulating_supply REAL,
        total_supply REAL,
        max_supply REAL,
        fdv REAL,
        snapshot_at TEXT
    )''')

    # 事件时间线
    c.execute('''CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT NOT NULL,
        event_type TEXT,
        title TEXT,
        description TEXT,
        source TEXT,
        url TEXT,
        event_date TEXT,
        impact TEXT,
        scraped_at TEXT
    )''')

    # 六维评分
    c.execute('''CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT NOT NULL,
        dimension TEXT,
        score INTEGER,
        weight REAL,
        notes TEXT,
        scored_at TEXT,
        UNIQUE(project, dimension)
    )''')

    # 竞品
    c.execute('''CREATE TABLE IF NOT EXISTS competitors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT NOT NULL,
        competitor_symbol TEXT,
        competitor_name TEXT,
        market_cap REAL,
        advantage TEXT,
        weakness TEXT,
        notes TEXT,
        updated_at TEXT,
        UNIQUE(project, competitor_symbol)
    )''')

    # AI分析报告
    c.execute('''CREATE TABLE IF NOT EXISTS ai_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT NOT NULL,
        report_type TEXT,
        bull_case TEXT,
        bear_case TEXT,
        catalysts TEXT,
        risks TEXT,
        rating TEXT,
        target_price TEXT,
        summary TEXT,
        created_at TEXT
    )''')

    conn.commit()
    conn.close()
    print(f"DB ready at {DB_PATH}")

# ===== Projects =====
def upsert_project(symbol, name="", coin_gecko_id="", category="", description="", website="", twitter="", github="", notes=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("SELECT added_at FROM projects WHERE symbol=?", (symbol,))
    row = c.fetchone()
    added_at = row[0] if row else now
    c.execute('''INSERT OR REPLACE INTO projects
        (symbol, name, coin_gecko_id, category, description, website, twitter, github, added_at, last_updated, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (symbol, name, coin_gecko_id, category, description, website, twitter, github, added_at, now, notes))
    conn.commit()
    conn.close()

# ===== Tweets =====
def save_tweets(project, tweets):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    saved = 0
    for t in tweets:
        try:
            c.execute('''INSERT OR IGNORE INTO tweets
                (project, tweet_id, author, author_handle, text, created_at, likes, retweets, replies, views, url, sentiment, scraped_at, raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (project, t.get('tweet_id',''), t.get('author',''), t.get('author_handle',''),
                 t.get('text',''), t.get('created_at',''), t.get('likes',0), t.get('retweets',0),
                 t.get('replies',0), t.get('views',''), t.get('url',''), t.get('sentiment',''),
                 datetime.now().isoformat(), json.dumps(t, ensure_ascii=False)))
            if c.rowcount > 0: saved += 1
        except: pass
    conn.commit()
    conn.close()
    print(f"  +{saved} tweets for {project}")

# ===== Price =====
def save_price(project, data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO price_snapshots
        (project, price, change_1h, change_24h, change_7d, change_30d, market_cap, volume_24h,
         ath, ath_date, atl, circulating_supply, total_supply, max_supply, fdv, snapshot_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (project, data.get('price'), data.get('change_1h'), data.get('change_24h'),
         data.get('change_7d'), data.get('change_30d'), data.get('market_cap'), data.get('volume_24h'),
         data.get('ath'), data.get('ath_date'), data.get('atl'),
         data.get('circulating_supply'), data.get('total_supply'), data.get('max_supply'),
         data.get('fdv'), datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ===== Events =====
def save_event(project, event_type, title, description, source="", url="", event_date="", impact=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO events (project, event_type, title, description, source, url, event_date, impact, scraped_at)
                  VALUES (?,?,?,?,?,?,?,?,?)''',
              (project, event_type, title, description, source, url, event_date, impact, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ===== Scores =====
def save_score(project, dimension, score, weight, notes=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO scores (project, dimension, score, weight, notes, scored_at)
                  VALUES (?,?,?,?,?,?)''',
              (project, dimension, score, weight, notes, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ===== Competitors =====
def save_competitor(project, comp_symbol, comp_name="", market_cap=0, advantage="", weakness="", notes=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO competitors
        (project, competitor_symbol, competitor_name, market_cap, advantage, weakness, notes, updated_at)
        VALUES (?,?,?,?,?,?,?,?)''',
        (project, comp_symbol, comp_name, market_cap, advantage, weakness, notes, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ===== AI Report =====
def save_report(project, report_type, bull, bear, catalysts, risks, rating, target_price, summary):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO ai_reports
        (project, report_type, bull_case, bear_case, catalysts, risks, rating, target_price, summary, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (project, report_type, bull, bear, catalysts, risks, rating, target_price, summary, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ===== Queries =====
def list_projects():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT symbol, name, category, added_at FROM projects ORDER BY added_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_project_data(symbol):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    result = {'project': {}, 'prices': [], 'events': [], 'scores': [], 'competitors': [], 'tweets': [], 'reports': []}
    c.execute("SELECT * FROM projects WHERE symbol=?", (symbol,))
    r = c.fetchone()
    if r: result['project'] = dict(r)
    c.execute("SELECT * FROM price_snapshots WHERE project=? ORDER BY snapshot_at DESC LIMIT 30", (symbol,))
    result['prices'] = [dict(x) for x in c.fetchall()]
    c.execute("SELECT * FROM events WHERE project=? ORDER BY event_date DESC", (symbol,))
    result['events'] = [dict(x) for x in c.fetchall()]
    c.execute("SELECT * FROM scores WHERE project=?", (symbol,))
    result['scores'] = [dict(x) for x in c.fetchall()]
    c.execute("SELECT * FROM competitors WHERE project=?", (symbol,))
    result['competitors'] = [dict(x) for x in c.fetchall()]
    c.execute("SELECT * FROM tweets WHERE project=? ORDER BY likes DESC LIMIT 20", (symbol,))
    result['tweets'] = [dict(x) for x in c.fetchall()]
    c.execute("SELECT * FROM ai_reports WHERE project=? ORDER BY created_at DESC LIMIT 3", (symbol,))
    result['reports'] = [dict(x) for x in c.fetchall()]
    conn.close()
    return result

if __name__ == '__main__':
    init_db()
    print("Projects:", list_projects())
