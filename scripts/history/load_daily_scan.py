"""载入 daily_scan：light 快照 + deep 研究 + 源状态 + 分类维度 + 非结构化正文。

映射依据：`docs/history-db/ARCHITECTURE.md` §4（映射策略）、§4.1（正文提取）、§5（ETL 设计）。

数据源与落表：
- ``top_800_light/all_coins.json``  → ``coin_daily_snapshot``（13 字段全列化；按 id 去重、``price_usd`` 非空）
- ``summary.json``                  → ``scan_day``（声明值与**实测落盘计数**分开存，健康度以落盘为准）
- ``top_50_detailed/<coin_id>.json``→ ``deep_research``（**canonical 载荷**，整条存 ``payload_json``）
                                     + ``source_status``（``sources`` → 稀疏长表，容纳 13/14 源漂移）
                                     + ``content_archive``（逐源抽取正文）
- ``by_category/<slug>/*.json`` → ``category_membership``（**每文件一行**的长表，忠实复现
  「一币多分类 + 大量无 ``coin_id`` 空壳」，仅抽 ``has_market/market_cap/chg24``；**不落载荷**）
  —— 同时作为 ``deep_research.category_slug`` 的**权威来源**（目录名即分类）
- ``dim_coin`` / ``dim_category``    → 维度表

硬约定（ARCHITECTURE §12，逐条落实）：
1. **幂等**：主表 ``ON CONFLICT DO UPDATE``；会缩水的子表（``source_status`` / ``content_archive``）
   按自然键单元 ``(date, coin_id)`` 做「事务内 DELETE + INSERT」。
2. **NULL 语义**：源缺失（如 ``max_supply``）原样存 ``NULL``，**不填 0**（不污染均值）。
3. **残缺日原样入库**（``is_partial`` 由 ``backfill_history.py`` 统一计算），不伪造不插值。
4. ``body_grams`` = CJK 字符 bigram + 英文整词（见 ``export_grams.make_grams``），仅供 FTS。
5. ``content_id = md5(date|coin_id|source|doc_hash)``，跨批次稳定、可对账。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # 作为包导入
    from . import etl_common as ec
    from .export_grams import make_grams
except ImportError:  # 直接以脚本运行
    import etl_common as ec  # type: ignore[no-redef]
    from export_grams import make_grams  # type: ignore[no-redef]

# --------------------------------------------------------------------------
# 常量
# --------------------------------------------------------------------------
LIGHT_FILENAME = "all_coins.json"
LIGHT_DIRNAME = "top_800_light"
DEEP_DIRNAME = "top_50_detailed"
CATEGORY_DIRNAME = "by_category"
SUMMARY_FILENAME = "summary.json"

# 非结构化正文来源 → doc_type（ARCHITECTURE §4.1）
CONTENT_SOURCE_DOC_TYPE: Dict[str, str] = {
    "crypto_news": "news",
    "rss": "article",
    "reddit": "post",
    "v2ex": "post",
    "bilibili": "video",
    "twitter": "profile",
}

# 分类 slug → 展示标签（最小集合 + 常见扩展；缺省回退为 slug 本身）
CATEGORY_LABELS: Dict[str, str] = {
    "layer-1": "公链 L1",
    "layer-2": "二层 L2",
    "defi": "DeFi",
    "meme": "Meme",
    "rwa": "RWA",
    "stablecoin": "稳定币",
    "exchange": "交易所",
    "ai": "AI",
    "unclassified": "未分类",
    "bridge": "跨链桥",
    "ecosystem": "生态",
    "gaming": "游戏",
    "nft": "NFT",
    "portfolio": "组合",
    "privacy": "隐私",
    "storage": "存储",
    "yield": "收益",
}

_URL_RE = re.compile(r"https?://[^\s\)\]\",'>]+")
_UNCLASSIFIED = "unclassified"

# --------------------------------------------------------------------------
# SQL 片段（列清单与 upsert 语句集中定义，避免多处漂移）
# --------------------------------------------------------------------------
SNAPSHOT_COLS = (
    "date", "coin_id", "symbol", "name", "rank", "price_usd", "market_cap",
    "volume_24h", "change_24h_pct", "change_7d_pct", "circulating_supply",
    "total_supply", "max_supply", "snapshot_ts",
)
SNAPSHOT_SQL = f"""
INSERT INTO coin_daily_snapshot ({", ".join(SNAPSHOT_COLS)})
VALUES ({", ".join(["?"] * len(SNAPSHOT_COLS))})
ON CONFLICT (date, coin_id) DO UPDATE SET
    symbol=EXCLUDED.symbol, name=EXCLUDED.name, rank=EXCLUDED.rank,
    price_usd=EXCLUDED.price_usd, market_cap=EXCLUDED.market_cap,
    volume_24h=EXCLUDED.volume_24h, change_24h_pct=EXCLUDED.change_24h_pct,
    change_7d_pct=EXCLUDED.change_7d_pct, circulating_supply=EXCLUDED.circulating_supply,
    total_supply=EXCLUDED.total_supply, max_supply=EXCLUDED.max_supply,
    snapshot_ts=EXCLUDED.snapshot_ts
"""

DEEP_COLS = (
    "date", "coin_id", "symbol", "name", "rank", "research_time", "category_slug",
    "categories_json", "n_sources", "has_github", "payload_json", "source_file",
)
DEEP_SQL = f"""
INSERT INTO deep_research ({", ".join(DEEP_COLS)})
VALUES ({", ".join(["?"] * len(DEEP_COLS))})
ON CONFLICT (date, coin_id) DO UPDATE SET
    symbol=EXCLUDED.symbol, name=EXCLUDED.name, rank=EXCLUDED.rank,
    research_time=EXCLUDED.research_time, category_slug=EXCLUDED.category_slug,
    categories_json=EXCLUDED.categories_json, n_sources=EXCLUDED.n_sources,
    has_github=EXCLUDED.has_github, payload_json=EXCLUDED.payload_json,
    source_file=EXCLUDED.source_file
"""

SOURCE_STATUS_COLS = (
    "date", "coin_id", "source", "status", "error", "confidence", "source_timestamp",
)
SOURCE_STATUS_SQL = f"""
INSERT INTO source_status ({", ".join(SOURCE_STATUS_COLS)})
VALUES ({", ".join(["?"] * len(SOURCE_STATUS_COLS))})
"""

CONTENT_COLS = (
    "content_id", "date", "coin_id", "source", "doc_type", "title", "url", "author",
    "body_text", "published_ts", "score", "extra_json", "origin_path", "doc_hash",
    "body_grams", "ingested_batch_id",
)
CONTENT_SQL = f"""
INSERT INTO content_archive ({", ".join(CONTENT_COLS)})
VALUES ({", ".join(["?"] * len(CONTENT_COLS))})
"""

SCAN_DAY_COLS = (
    "date", "scan_time", "total_coins", "deep_researched_decl", "light_researched_decl",
    "deep_files_actual", "light_files_actual", "categories_json", "market_stats_json",
    "state_stats_json", "source_path", "ingested_batch_id",
)
SCAN_DAY_SQL = f"""
INSERT INTO scan_day ({", ".join(SCAN_DAY_COLS)})
VALUES ({", ".join(["?"] * len(SCAN_DAY_COLS))})
ON CONFLICT (date) DO UPDATE SET
    scan_time=EXCLUDED.scan_time, total_coins=EXCLUDED.total_coins,
    deep_researched_decl=EXCLUDED.deep_researched_decl,
    light_researched_decl=EXCLUDED.light_researched_decl,
    deep_files_actual=EXCLUDED.deep_files_actual,
    light_files_actual=EXCLUDED.light_files_actual,
    categories_json=EXCLUDED.categories_json,
    market_stats_json=EXCLUDED.market_stats_json,
    state_stats_json=EXCLUDED.state_stats_json,
    source_path=EXCLUDED.source_path,
    ingested_batch_id=EXCLUDED.ingested_batch_id
"""

CATMEM_COLS = (
    "date", "category_slug", "member_key", "coin_id", "has_market", "market_cap", "chg24",
)
CATMEM_SQL = f"""
INSERT INTO category_membership ({", ".join(CATMEM_COLS)})
VALUES ({", ".join(["?"] * len(CATMEM_COLS))})
"""

DIM_COIN_SQL = """
INSERT INTO dim_coin (coin_id, symbol, name, first_seen_date, last_seen_date)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT (coin_id) DO UPDATE SET
    symbol=EXCLUDED.symbol, name=EXCLUDED.name,
    first_seen_date=LEAST(dim_coin.first_seen_date, EXCLUDED.first_seen_date),
    last_seen_date=GREATEST(dim_coin.last_seen_date, EXCLUDED.last_seen_date)
"""

DIM_CATEGORY_SQL = """
INSERT INTO dim_category (category_slug, label)
VALUES (?, ?)
ON CONFLICT (category_slug) DO UPDATE SET label=EXCLUDED.label
"""


# --------------------------------------------------------------------------
# 读取与清洗辅助
# --------------------------------------------------------------------------
def read_json(path: Path) -> Optional[Any]:
    """读取 JSON（失败返回 None，绝不抛异常）。"""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[load_daily_scan] 读取 JSON 失败 {path}: {exc}")
        return None


def list_scan_dates(daily_dir: Optional[Path] = None) -> List[str]:
    """列出扫描日目录名（升序，仅 ``YYYY-MM-DD`` 形态）。"""
    root = daily_dir or ec.DAILY_SCAN_DIR
    if not root.is_dir():
        return []
    dates: List[str] = []
    for name in sorted(p.name for p in root.iterdir() if p.is_dir()):
        if ec.parse_date(name) is not None:
            dates.append(name)
    return dates


def _clean_light_rows(payload: Any) -> List[dict]:
    """轻量快照清洗：按 ``id`` 去重、``price_usd`` 非空（与 loader 口径一致）。

    注意**不**对缺失字段填 0 —— 缺失即缺失（NULL 语义，§12）。
    """
    if not isinstance(payload, list):
        return []
    seen: set = set()
    rows: List[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        coin_id = item.get("id")
        if not coin_id or item.get("price_usd") is None or coin_id in seen:
            continue
        seen.add(coin_id)
        rows.append(item)
    return rows


def load_category_membership(
    cat_dir: Path, date: str
) -> Tuple[List[List[Any]], Dict[str, str], set]:
    """遍历 ``by_category/<slug>/*.json`` → ``category_membership`` 行 + 权威分类映射。

    忠实复现 ``by_category`` 的真实结构（见 `ARCHITECTURE.md §0 验证5`）：

    - **每文件一行**（``member_key`` = 文件名），保住 1,241 这类**文件级**计数；
    - 大量成员**无 ``coin_id``**（06-27 的 1,241 个文件中仅 99 个含该字段）→ 写 ``coin_id=NULL``；
      **空壳成员也必须入库**——`load_by_category_raw` 的「7 日窗口取文件数最多的一天」依赖文件总数；
    - 一币可属**多个 slug**（实测恒为 ``{真实分类, unclassified}`` 两态）→ 故不可用 ``(date, coin_id)`` 作键；
    - ``has_market`` = ``sources.market.data`` 非空（仅这些成员参与 `build_sectors` 的 `sectors` 计数）；
      ``market_cap`` / ``chg24`` 仅在 market 源成功时取值，否则 ``NULL``（不填 0）。

    Args:
        cat_dir: ``daily_scan/<date>/by_category`` 目录。
        date: 该扫描日（``YYYY-MM-DD``）。

    Returns:
        ``(rows, coin_slug_map, slugs)``

        - ``rows``：``category_membership`` 参数行（列序同 ``CATMEM_COLS``）；
        - ``coin_slug_map``：``{coin_id: 权威 slug}``（同币多 slug 时**优先非 unclassified**），
          供 ``deep_research.category_slug`` 覆盖 payload 内的值；
        - ``slugs``：观测到的全部目录名（登记 ``dim_category``）。
    """
    rows: List[List[Any]] = []
    coin_slug: Dict[str, str] = {}
    slugs: set = set()
    if not cat_dir.is_dir():
        return rows, coin_slug, slugs

    for slug_dir in sorted(p for p in cat_dir.iterdir() if p.is_dir()):
        slug = slug_dir.name
        slugs.add(slug)  # 目录名即权威 slug；所有出现过的 slug 都登记进 dim_category
        for member in sorted(slug_dir.glob("*.json")):
            payload = read_json(member)
            coin_id: Optional[str] = None
            has_market = False
            market_cap: Optional[float] = None
            chg24: Optional[float] = None
            if isinstance(payload, dict):
                raw_coin_id = payload.get("coin_id")
                coin_id = raw_coin_id if isinstance(raw_coin_id, str) and raw_coin_id else None
                sources = payload.get("sources")
                market = sources.get("market") if isinstance(sources, dict) else None
                data = market.get("data") if isinstance(market, dict) else None
                if isinstance(data, dict) and data:
                    has_market = True
                    market_cap = _as_float(data.get("market_cap"))
                    chg24 = _as_float(data.get("price_change_percentage_24h"))
            rows.append([date, slug, member.stem, coin_id, has_market, market_cap, chg24])
            if coin_id:
                existing = coin_slug.get(coin_id)
                if existing is None or (existing == _UNCLASSIFIED and slug != _UNCLASSIFIED):
                    coin_slug[coin_id] = slug
    return rows, coin_slug, slugs


def _unwrap_content_list(value: Any) -> List[Any]:
    """把 ``sources.<name>.data`` 解包为列表。

    实测两种形态：直接为 ``list``；或为 ``{"data": [...]}`` 包装（多数如此）。
    逐层下钻至多 6 层，找不到列表则返回空列表（空安全）。
    """
    depth = 0
    current = value
    while isinstance(current, dict) and depth < 6:
        if "data" not in current:
            break
        current = current["data"]
        depth += 1
    return current if isinstance(current, list) else []


def _extract_url_from_text(title: Optional[str], body: Optional[str]) -> Optional[str]:
    """从标题/正文里尽力抽取 http(s) 链接（crypto_news 无独立 url 字段）。"""
    for text in (title, body):
        if text:
            found = _URL_RE.search(text)
            if found:
                return found.group(0).rstrip(".,;)")
    return None


def _first_nonempty(*values: Any) -> Optional[str]:
    """返回首个「去空白后非空」的字符串值；全部为空返回 None。"""
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


# --------------------------------------------------------------------------
# 源状态 / 正文 抽取
# --------------------------------------------------------------------------
def _source_register(payload: dict) -> List[List[Any]]:
    """``sources{}`` → ``source_status`` 稀疏长表行（随源集合 13/14 漂移自动伸缩）。

    返回 7 列：``date, coin_id, source, status, error, confidence, source_timestamp``
    —— 与 ``SOURCE_STATUS_COLS`` 顺序严格一致。
    """
    date = payload["__date"]
    coin_id = payload["__coin_id"]
    rows: List[List[Any]] = []
    for source, sv in sorted((payload.get("sources") or {}).items()):
        if not isinstance(sv, dict):
            sv = {"status": "unknown", "data": sv}
        data = sv.get("data")
        raw_status = sv.get("status")
        status = str(raw_status) if raw_status not in (None, "") else "unknown"
        error = sv.get("error")
        if error is None and isinstance(data, dict):
            error = data.get("error")
        confidence = sv.get("confidence")
        if confidence is None and isinstance(data, dict):
            confidence = data.get("confidence")
        ts_raw = sv.get("timestamp")
        if ts_raw is None and isinstance(data, dict):
            ts_raw = data.get("timestamp")
        rows.append(
            [
                date,
                coin_id,
                source,
                status,
                None if error is None else str(error),
                _as_float(confidence),
                ec.parse_ts(ts_raw),
            ]
        )
    return rows


def _as_float(value: Any) -> Optional[float]:
    """尽力转 float；``None``/无法转换 → ``None``（不填 0）。"""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _content_rows(
    payload: dict,
    batch_id: str,
    origin_path: str,
) -> List[List[Any]]:
    """逐源抽取非结构化正文 → ``content_archive`` 行。

    抽取规则见 ARCHITECTURE §4.1：不同源的 ``body_text`` / ``url`` / ``author`` 取值不同，
    并遵循「空则不产行」（``twitter.bio`` 为空不入库）与「帖子/视频描述 8 KB 截断」。
    """
    date = payload["__date"]
    coin_id = payload["__coin_id"]
    sources = payload.get("sources") or {}
    rows: List[List[Any]] = []
    seen_ids: set = set()

    for source, doc_type in CONTENT_SOURCE_DOC_TYPE.items():
        sv = sources.get(source)
        if not isinstance(sv, dict):
            continue
        data = sv.get("data")
        items = _extract_content_items(source, data)
        for item in items:
            row = _build_content_row(item, source, doc_type, date, coin_id, origin_path, batch_id)
            if row is None:
                continue
            if row[0] in seen_ids:  # 同一单元内去重（content_id 冲突会破坏幂等）
                continue
            seen_ids.add(row[0])
            rows.append(row)
    return rows


def _extract_content_items(source: str, data: Any) -> List[dict]:
    """把某源的 ``data`` 归一为「条目 dict 列表」（空安全）。"""
    if source == "reddit":
        posting = (data or {}).get("posts") if isinstance(data, dict) else None
        return [x for x in (posting or []) if isinstance(x, dict)]
    if source == "twitter":
        return [data] if isinstance(data, dict) else []
    items = _unwrap_content_list(data)
    return [x for x in items if isinstance(x, dict)]


def _build_content_row(
    item: dict,
    source: str,
    doc_type: str,
    date: str,
    coin_id: str,
    origin_path: str,
    batch_id: str,
) -> Optional[List[Any]]:
    """把单个条目构造成 ``content_archive`` 参数行；无可归档内容返回 None。"""
    body_full, title, url, author, score, published_ts = _content_fields(item, source)

    # 空则不入库：twitter 必须 bio 非空（§13-O3），其余需标题或正文任一非空
    if source == "twitter":
        if not _first_nonempty(body_full):
            return None
    elif not (_first_nonempty(body_full) or _first_nonempty(title)):
        return None

    body_text = body_full or ""
    title_text = title or None

    # doc_hash 基于「未截断」正文 + 身份字段 → 跨运行稳定；content_id 为确定性代理键
    identity = {
        "source": source,
        "title": title_text,
        "url": url,
        "author": author,
        "published": str(published_ts) if published_ts else "",
        "body": body_text,
    }
    doc_hash = ec.md5_hex(json.dumps(identity, ensure_ascii=False, sort_keys=True))
    content_id = ec.md5_hex(f"{date}|{coin_id}|{source}|{doc_hash}")

    stored_body = ec.truncate_text(body_text, doc_type)
    # FTS 辅助列：**标题 + 正文** 一并纳入（PRD Q2 / ARCHITECTURE §9-Q2「标题 + 正文全文」）。
    # DDL 的索引签名固定为 (body_text, body_grams)，故标题只能经由辅助列 grams 参与检索；
    # make_grams 内部跨段去重，故「标题 + 正文」合并成一次调用即可。
    # （实测必要性：rss 有 7,920 行、bilibili 全部 455 行正文为空，仅标题含有效信息。）
    grams_source = f"{title_text or ''}\n{stored_body or ''}"
    body_grams = make_grams(grams_source)
    extra = {
        "source": source,
        "confidence": item.get("confidence"),
    }
    for key in ("subreddit", "node", "replies", "play", "followers", "following", "tweets_count"):
        if key in item and item.get(key) is not None:
            extra[key] = item[key]

    return [
        content_id,
        date,
        coin_id,
        source,
        doc_type,
        title_text,
        url,
        author,
        stored_body,
        published_ts,
        score,
        ec.json_or_none(extra),
        origin_path,
        doc_hash,
        body_grams,
        batch_id,
    ]


def _content_fields(item: dict, source: str) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[float], Optional[Any]]:
    """按源返回 ``(body, title, url, author, score, published_ts)``（ARCHITECTURE §4.1）。"""
    title = item.get("title")
    if source == "crypto_news":
        body = _first_nonempty(item.get("content"), item.get("title")) or ""
        url = item.get("url") or _extract_url_from_text(title, body)
        author = item.get("author")
        score = _as_float(item.get("score"))
        published = item.get("published") or item.get("timestamp")
    elif source == "rss":
        body = _first_nonempty(item.get("content"), item.get("summary")) or ""
        url = item.get("link") or item.get("url")
        author = item.get("author")
        score = _as_float(item.get("score"))
        published = item.get("published") or item.get("pubDate")
    elif source == "reddit":
        body = item.get("content") or ""
        url = item.get("url")
        author = item.get("author")
        score = _as_float(item.get("score"))
        published = item.get("published") or item.get("created_utc")
    elif source == "v2ex":
        body = item.get("content") or ""
        url = item.get("url")
        author = item.get("member")
        score = _as_float(item.get("replies"))
        published = item.get("created") or item.get("published")
    elif source == "bilibili":
        body = item.get("description") or ""
        bvid = item.get("bvid")
        url = f"https://b23.tv/{bvid}" if bvid else item.get("url")
        author = item.get("author")
        score = _as_float(item.get("play"))
        published = item.get("published") or item.get("created")
    elif source == "twitter":
        body = item.get("bio") or ""
        username = item.get("username")
        url = f"https://x.com/{username}" if username else None
        author = item.get("name") or username
        score = _as_float(item.get("followers"))
        published = item.get("timestamp")
    else:  # pragma: no cover - 常量表已枚举，兜底防御
        body = item.get("content") or ""
        url = item.get("url")
        author = item.get("author")
        score = _as_float(item.get("score"))
        published = item.get("timestamp")

    return body, title, url, author, score, ec.parse_ts(published)


# --------------------------------------------------------------------------
# 单元写入（幂等：DELETE + INSERT）
# --------------------------------------------------------------------------
def _replace_category_unit(conn: Any, date: str, rows: List[List[Any]]) -> None:
    """以「日」为单元替换 ``category_membership``（事务内 DELETE + INSERT）。

    自然键单元是 ``(date, category_slug, member_key)``；**按日整体替换**是其超集且更简单可靠：
    重跑时若某 slug / 成员消失也不会留下陈旧行（`§5.2 策略 B`）。单日失败仅回滚该日。
    """
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute("DELETE FROM category_membership WHERE date = ?", [date])
        if rows:
            conn.executemany(CATMEM_SQL, rows)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _replace_content_unit(
    conn: Any,
    date: str,
    coin_id: str,
    source_rows: List[List[Any]],
    content_rows: List[List[Any]],
) -> None:
    """以 ``(date, coin_id)`` 为事务边界，替换该单元的 ``source_status`` 与 ``content_archive``。

    采用「事务内 DELETE + INSERT」而非 UPSERT：重跑时若源数减少 / 新闻变少，
    UPSERT 会留下陈旧残留行（ARCHITECTURE §5.2 策略 B）。单单元失败仅回滚该单元。
    """
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute("DELETE FROM source_status WHERE date = ? AND coin_id = ?", [date, coin_id])
        conn.execute("DELETE FROM content_archive WHERE date = ? AND coin_id = ?", [date, coin_id])
        if source_rows:
            conn.executemany(SOURCE_STATUS_SQL, source_rows)
        if content_rows:
            conn.executemany(CONTENT_SQL, content_rows)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def load_daily_scan(
    conn: Any,
    batch_id: str,
    daily_dir: Optional[Path] = None,
    verbose: bool = True,
) -> Dict[str, int]:
    """载入全部扫描日（幂等）。

    Returns:
        各表写入行数统计（``scan_day`` / ``coin_daily_snapshot`` / ``deep_research`` /
        ``source_status`` / ``category_membership`` / ``content_archive`` / ``dim_coin`` /
        ``dim_category``），供编排层累计 ``ingest_batch.rows_loaded``。
    """
    root = daily_dir or ec.DAILY_SCAN_DIR
    dates = list_scan_dates(root)
    counts: Dict[str, int] = {
        "scan_day": 0,
        "coin_daily_snapshot": 0,
        "deep_research": 0,
        "source_status": 0,
        "category_membership": 0,
        "content_archive": 0,
        "dim_coin": 0,
        "dim_category": 0,
    }
    # 维度表聚合：coin_id → [symbol, name, first_seen, last_seen]
    coin_facts: Dict[str, List[Any]] = {}
    observed_slugs: set = set()

    for day_index, date in enumerate(dates, start=1):
        day_dir = root / date
        if verbose:
            print(f"[load_daily_scan] [{day_index}/{len(dates)}] 处理扫描日 {date}")

        # ---- B2. summary → scan_day（声明值 + 实测落盘计数） ----
        summary_path = day_dir / SUMMARY_FILENAME
        summary = read_json(summary_path) or {}

        # ---- A/B1. light 快照 → coin_daily_snapshot ----
        light_path = day_dir / LIGHT_DIRNAME / LIGHT_FILENAME
        light_rows = _clean_light_rows(read_json(light_path))
        snapshot_params: List[List[Any]] = []
        for item in light_rows:
            coin_id = item["id"]
            snapshot_params.append(
                [
                    date,
                    coin_id,
                    item.get("symbol"),
                    item.get("name"),
                    _as_int(item.get("rank")),
                    _as_float(item.get("price_usd")),
                    _as_float(item.get("market_cap")),
                    _as_float(item.get("volume_24h")),
                    _as_float(item.get("change_24h_pct")),
                    _as_float(item.get("change_7d_pct")),
                    _as_float(item.get("circulating_supply")),
                    _as_float(item.get("total_supply")),
                    _as_float(item.get("max_supply")),
                    ec.parse_ts(item.get("timestamp")),
                ]
            )
            _accumulate_coin(coin_facts, coin_id, item.get("symbol"), item.get("name"), date)
        if snapshot_params:
            conn.executemany(SNAPSHOT_SQL, snapshot_params)
        counts["coin_daily_snapshot"] += len(snapshot_params)

        # ---- C1. deep 研究（canonical）+ C2 源状态 + D 正文 + 分类成员 ----
        deep_dir = day_dir / DEEP_DIRNAME
        cat_dir = day_dir / CATEGORY_DIRNAME
        # B′. by_category 成员（忠实长表；同时产出 deep_research 的权威 category_slug 映射）
        catmem_rows, coin_slug_map, cat_slugs = load_category_membership(cat_dir, date)
        observed_slugs |= cat_slugs
        if catmem_rows:
            _replace_category_unit(conn, date, catmem_rows)
            for member_file in sorted(cat_dir.glob("*/*.json")):
                ec.record_file(conn, batch_id, member_file, 1, status="ok")
        counts["category_membership"] += len(catmem_rows)

        deep_rows: List[List[Any]] = []
        day_sources = 0
        day_content = 0
        deep_files = sorted(deep_dir.glob("*.json")) if deep_dir.is_dir() else []
        for deep_file in deep_files:
            payload = read_json(deep_file)
            if not isinstance(payload, dict):
                ec.record_file(conn, batch_id, deep_file, 0, status="error")
                continue
            coin_id = payload.get("coin_id") or deep_file.stem
            payload["__date"] = date
            payload["__coin_id"] = coin_id
            origin_path = ec.to_rel(deep_file)

            slug = coin_slug_map.get(coin_id) or payload.get("category_slug") or _UNCLASSIFIED
            observed_slugs.add(slug)
            sources = payload.get("sources") or {}
            deep_rows.append(
                [
                    date,
                    coin_id,
                    payload.get("symbol"),
                    payload.get("name"),
                    _as_int(payload.get("rank")),
                    ec.parse_ts(payload.get("research_time")),
                    slug,
                    ec.json_or_none(payload.get("categories")),
                    len(sources),
                    bool("github" in sources),
                    ec.json_or_none(_strip_internal(payload)),
                    origin_path,
                ]
            )
            _accumulate_coin(
                coin_facts, coin_id, payload.get("symbol"), payload.get("name"), date
            )

            source_rows = _source_register(payload)
            content_rows = _content_rows(payload, batch_id, origin_path)
            _replace_content_unit(conn, date, coin_id, source_rows, content_rows)
            day_sources += len(source_rows)
            day_content += len(content_rows)

            ec.record_file(conn, batch_id, deep_file, 1, status="ok")

        if deep_rows:
            conn.executemany(DEEP_SQL, deep_rows)
        counts["deep_research"] += len(deep_rows)
        counts["source_status"] += day_sources
        counts["content_archive"] += day_content

        # ---- scan_day（light_files_actual 取「去重后有效币数」实测值） ----
        conn.execute(
            SCAN_DAY_SQL,
            [
                date,
                ec.parse_ts(summary.get("scan_time")),
                _as_int(summary.get("total_coins")),
                _as_int(summary.get("deep_researched")),
                _as_int(summary.get("light_researched")),
                len(deep_rows),
                len(snapshot_params),
                ec.json_or_none(summary.get("categories")),
                ec.json_or_none(summary.get("market_stats")),
                ec.json_or_none(summary.get("state_stats")),
                ec.to_rel(summary_path),
                batch_id,
            ],
        )
        counts["scan_day"] += 1

        if summary_path.exists():
            ec.record_file(conn, batch_id, summary_path, 1, status="ok")
        if light_path.exists():
            ec.record_file(conn, batch_id, light_path, len(snapshot_params), status="ok")

    # ---- A. dim_coin / dim_category ----
    counts["dim_coin"] = _upsert_dim_coin(conn, coin_facts)
    counts["dim_category"] = _upsert_dim_category(conn, observed_slugs)
    if verbose:
        print(
            "[load_daily_scan] 完成："
            + ", ".join(f"{k}={v}" for k, v in counts.items())
        )
    return counts


def _strip_internal(payload: dict) -> dict:
    """剔除 ETL 注入的 ``__date`` / ``__coin_id`` 内部键，保证 ``payload_json`` 与源文件一致。"""
    return {k: v for k, v in payload.items() if not k.startswith("__")}


def _as_int(value: Any) -> Optional[int]:
    """尽力转 int；``None``/无法转换 → ``None``（不填 0）。"""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _accumulate_coin(
    facts: Dict[str, List[Any]],
    coin_id: str,
    symbol: Any,
    name: Any,
    date: str,
) -> None:
    """累计 dim_coin 的 first/last_seen_date（取 min/max），symbol/name 取非空值。"""
    if not coin_id:
        return
    current = facts.get(coin_id)
    if current is None:
        facts[coin_id] = [symbol, name, date, date]
        return
    if not current[0] and symbol:
        current[0] = symbol
    if not current[1] and name:
        current[1] = name
    if date < current[2]:
        current[2] = date
    if date > current[3]:
        current[3] = date


def _upsert_dim_coin(conn: Any, facts: Dict[str, List[Any]]) -> int:
    """把累计结果写入 ``dim_coin``（幂等 upsert，first/last 取 LEAST/GREATEST）。"""
    if not facts:
        return 0
    params = [
        [coin_id, fact[0], fact[1], ec.parse_date(fact[2]), ec.parse_date(fact[3])]
        for coin_id, fact in sorted(facts.items())
    ]
    conn.executemany(DIM_COIN_SQL, params)
    return len(params)


def _upsert_dim_category(conn: Any, slugs: set) -> int:
    """把观测到的分类 slug 写入 ``dim_category``（label 优先取映射表，缺省回退 slug）。"""
    if not slugs:
        return 0
    params = [[slug, CATEGORY_LABELS.get(slug, slug)] for slug in sorted(slugs)]
    conn.executemany(DIM_CATEGORY_SQL, params)
    return len(params)
