"""把豆包(Doubao)爬取的 Twitter 舆情数据接入历史库 content_archive。

数据源：``DoubaoWork/chats/2026-09-25/new-chat/twitter_monitor/research.db``（SQLite）
  - ``projects``：symbol → coin_gecko_id 映射（100 条全部带 gecko id）
  - ``tweets``：推文（text / author / likes / retweets / sentiment / scraped_at）
  - ``events``：项目事件（partnership / buyback / listing ...）

落表：``ct_history.duckdb`` 的 ``content_archive``
  - 推文：source='twitter', doc_type='tweet'
  - 事件：source='twitter', doc_type='event'

严格复用 load_daily_scan 的 content_archive 契约，保证与既有数据同构、可被
check_integrity 识别、可被 FTS 检索、可被 H4 归档时间线消费：
  - content_id = md5(f"{date}|{coin_id}|{source}|{doc_hash}")
  - doc_hash   = md5(json.dumps(identity, sort_keys=True))
  - body_grams = make_grams(f"{title}\\n{body}")   （CJK bigram + 英文整词，双列 FTS 索引）

幂等：以 ``content_id`` 主键 ``ON CONFLICT DO NOTHING``，可重复运行。

注意：推文抓取于 2026-09-28，晚于控制台数据截止日 2026-08-26。
  - 按日过滤的 H4 时间线（用控制台选定日期）不会显示它们；
  - 但 FTS 全文检索（跨日期）+ 新增的「Twitter 舆情」币页卡片（按 coin_id 过滤）均可见。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # 作为包导入
    from . import etl_common as ec
    from .export_grams import make_grams
except ImportError:  # 直接以脚本运行
    import etl_common as ec  # type: ignore[no-redef]
    from export_grams import make_grams  # type: ignore[no-redef]

SOURCE_DB_DEFAULT = (
    Path.home()
    / "DoubaoWork"
    / "chats"
    / "2026-09-25"
    / "new-chat"
    / "twitter_monitor"
    / "research.db"
)

BATCH_ID = f"twitter_doubao_{date.today():%Y%m%d}"
ORIGIN_PATH = "DoubaoWork/chats/2026-09-25/new-chat/twitter_monitor/research.db"

CONTENT_COLS = (
    "content_id", "date", "coin_id", "source", "doc_type", "title", "url", "author",
    "body_text", "published_ts", "score", "extra_json", "origin_path", "doc_hash",
    "body_grams", "ingested_batch_id",
)
CONTENT_SQL = f"""
INSERT INTO content_archive ({", ".join(CONTENT_COLS)})
VALUES ({", ".join(["?"] * len(CONTENT_COLS))})
ON CONFLICT (content_id) DO NOTHING
"""


def _build_identity(source: str, title: Optional[str], url: Optional[str],
                    author: Optional[str], published: Optional[datetime],
                    body: str) -> dict:
    return {
        "source": source,
        "title": title,
        "url": url,
        "author": author,
        "published": str(published) if published else "",
        "body": body,
    }


def _build_content_row(
    source: str,
    doc_type: str,
    date_str: str,
    coin_id: str,
    title: Optional[str],
    url: Optional[str],
    author: Optional[str],
    body: str,
    published_ts: Optional[datetime],
    score: Optional[float],
    extra: dict,
) -> List[Any]:
    """与 load_daily_scan._build_content_row 同口径构造 content_archive 行。"""
    body_text = body or ""
    title_text = title or None
    identity = _build_identity(source, title_text, url, author, published_ts, body_text)
    doc_hash = ec.md5_hex(json.dumps(identity, ensure_ascii=False, sort_keys=True))
    content_id = ec.md5_hex(f"{date_str}|{coin_id}|{source}|{doc_hash}")
    grams_source = f"{title_text or ''}\n{body_text or ''}"
    body_grams = make_grams(grams_source)
    return [
        content_id, date_str, coin_id, source, doc_type, title_text, url, author,
        body_text, published_ts, score, ec.json_or_none(extra),
        ORIGIN_PATH, doc_hash, body_grams, BATCH_ID,
    ]


def _load_symbol_map(conn_sql: sqlite3.Connection) -> Dict[str, str]:
    """symbol → coin_gecko_id（仅保留有 gecko id 的）。"""
    out: Dict[str, str] = {}
    for sym, gid in conn_sql.execute(
        "SELECT symbol, coin_gecko_id FROM projects WHERE coin_gecko_id IS NOT NULL AND coin_gecko_id <> ''"
    ):
        out[sym] = gid
    return out


def _rows_from_tweets(conn_sql: sqlite3.Connection, sym_map: Dict[str, str]) -> Tuple[List[List[Any]], int, int]:
    rows: List[List[Any]] = []
    mapped = skipped = 0
    for (project, tweet_id, author, handle, text, created_at, likes, retweets,
         replies, url, sentiment, scraped_at) in conn_sql.execute(
        "SELECT project, tweet_id, author, author_handle, text, created_at, "
        "likes, retweets, replies, url, sentiment, scraped_at FROM tweets"
    ):
        gid = sym_map.get(project)
        if not gid:
            skipped += 1
            continue
        mapped += 1
        published = ec.parse_ts(created_at) or ec.parse_ts(scraped_at)
        date_str = (published or ec.parse_ts(scraped_at) or datetime.now()).strftime("%Y-%m-%d")
        title = handle or author or None
        extra = {
            "source": "twitter",
            "tweet_id": tweet_id,
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "sentiment": sentiment,
        }
        rows.append(_build_content_row(
            source="twitter", doc_type="tweet", date_str=date_str, coin_id=gid,
            title=title, url=url or None, author=author or handle or None,
            body=text or "", published_ts=published,
            score=float((likes or 0) + (retweets or 0)), extra=extra,
        ))
    return rows, mapped, skipped


def _rows_from_events(conn_sql: sqlite3.Connection, sym_map: Dict[str, str]) -> Tuple[List[List[Any]], int, int]:
    rows: List[List[Any]] = []
    mapped = skipped = 0
    for (project, event_type, title, description, source, url, event_date,
         impact) in conn_sql.execute(
        "SELECT project, event_type, title, description, source, url, event_date, impact "
        "FROM events"
    ):
        gid = sym_map.get(project)
        if not gid:
            skipped += 1
            continue
        mapped += 1
        published = ec.parse_ts(event_date)
        date_str = (published or datetime.now()).strftime("%Y-%m-%d")
        extra = {"source": "twitter", "event_type": event_type, "impact": impact}
        rows.append(_build_content_row(
            source="twitter", doc_type="event", date_str=date_str, coin_id=gid,
            title=title or None, url=url or None, author=None,
            body=description or "", published_ts=published, score=None, extra=extra,
        ))
    return rows, mapped, skipped


def load_twitter(db_path: Optional[Path] = None, source_db: Optional[Path] = None,
                 verbose: bool = True) -> Dict[str, int]:
    """执行 Twitter 数据入库。返回各阶段计数。"""
    source_db = source_db or SOURCE_DB_DEFAULT
    if not Path(source_db).exists():
        raise FileNotFoundError(f"源库不存在: {source_db}")
    conn_sql = sqlite3.connect(str(source_db))
    conn_sql.row_factory = None

    target = ec.connect(db_path)
    stats: Dict[str, int] = {"tweets_mapped": 0, "tweets_skipped": 0,
                             "events_mapped": 0, "events_skipped": 0,
                             "inserted": 0}

    try:
        sym_map = _load_symbol_map(conn_sql)
        if verbose:
            print(f"[load_twitter] symbol→gecko 映射 {len(sym_map)} 条")

        tweet_rows, tm, ts = _rows_from_tweets(conn_sql, sym_map)
        event_rows, em, es = _rows_from_events(conn_sql, sym_map)
        stats["tweets_mapped"] = tm
        stats["tweets_skipped"] = ts
        stats["events_mapped"] = em
        stats["events_skipped"] = es

        all_rows = tweet_rows + event_rows
        if all_rows:
            target.execute("BEGIN TRANSACTION")
            try:
                target.executemany(CONTENT_SQL, all_rows)
                target.execute("COMMIT")
            except Exception:
                target.execute("ROLLBACK")
                raise
            stats["inserted"] = len(all_rows)
            # FTS 索引是静态的（见 init_db.build_fts_index）：任何 INSERT 后必须 overwrite=1 重建才可见。
            # 否则新推文无法被 /api/history/search 检索到。
            ec.ensure_fts_extension(target)
            target.execute(
                "PRAGMA create_fts_index('content_archive', 'content_id', 'body_text', 'body_grams', "
                "stemmer='none', lower=1, strip_accents=0, overwrite=1)"
            )
            if verbose:
                print("[load_twitter] 已重建双列 FTS 索引（含本次 twitter 内容）")
        if verbose:
            print(f"[load_twitter] 推文 {tm} 入库 / {ts} 跳过(无映射)；"
                  f"事件 {em} 入库 / {es} 跳过；合计写入 {stats['inserted']} 行")
    finally:
        conn_sql.close()
        try:
            target.close()
        except Exception:
            pass
    return stats


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="把豆包 Twitter 舆情数据接入历史库 content_archive")
    p.add_argument("--source", default=str(SOURCE_DB_DEFAULT), help="源 SQLite 路径")
    p.add_argument("--db", default=str(ec.DB_PATH), help="目标 DuckDB 路径")
    args = p.parse_args(argv)
    try:
        stats = load_twitter(db_path=Path(args.db), source_db=Path(args.source))
    except Exception as e:  # noqa: BLE001
        print(f"[load_twitter] 失败: {e}")
        return 1
    print("OK", json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
