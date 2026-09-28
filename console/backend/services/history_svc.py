"""历史数据库查询服务（H1–H8）—— 见 docs/history-db/ARCHITECTURE.md §8。

定位：
- 本模块服务于**新增只读端点**（H1–H8），数据源是 DuckDB 历史库
  （``data/history/ct_history.duckdb``）。老 10 端点仍走 ``data.loader`` 仓储，二者互不影响。
- 无论 ``CT_HISTORY_SOURCE=files|duckdb``，历史端点都直连历史库（历史数据只在库里），
  因此两种数据源下**行为一致**。

约定（与既有服务层一致）：
- 只读、参数化 SQL（严禁拼接外部输入）；
- 数据缺失/库不可用 → 返回**空结构**（由 router 转成非 0 code），**绝不抛 500**；
- ``gaps`` 一律**显式列出、绝不插值**（§8 / PRD Q3）。
"""
from __future__ import annotations

import json
import math
import re
import time
from datetime import date, datetime
from typing import Iterator, List, Optional, Tuple

from data.repository import HistoryDBError, history_db_available, history_query
from data.schemas import (
    CategoriesTimelineResponse,
    CategoryTimelinePoint,
    CoinSeriesResponse,
    CollectionStatus,
    HealthOverviewResponse,
    HealthSourcesResponse,
    HistoryDatesResponse,
    HistoryDateRow,
    MacroHistorySeriesResponse,
    MacroSeriesPoint,
    NewsTimelineItem,
    NewsTimelineResponse,
    SearchHit,
    SearchResponse,
    SeriesPoint,
    SourceDriftRow,
    SourceHealthDay,
)

# 采集视为「新鲜」的最大间隔天数；超过则 status=stale（暴露 scan 停更，§6/US-3）
STALE_DAYS = 2
# H4 分页上限（防止一次性拉爆）
MAX_LIMIT = 500
DEFAULT_LIMIT = 50

# H2 支持的指标 → ``coin_daily_snapshot`` 列名（白名单，杜绝任意列注入）。
# 说明：架构 §8 示例里的 ``score`` / ``social_heat`` 在历史库中**无对应列**
# （无评分表；deep_research 的 social_stats.data 为空），故请求它们会进入
# ``unavailable``，不会伪造数据。
SERIES_METRICS = {
    "price_usd": "price_usd",
    "market_cap": "market_cap",
    "rank": "rank",
    "volume_24h": "volume_24h",
    "change_24h_pct": "change_24h_pct",
    "change_7d_pct": "change_7d_pct",
}
DEFAULT_METRICS: List[str] = ["price_usd", "market_cap", "rank"]

# H8 支持的宏观指标 → 取值路径
MACRO_METRICS = {
    "btc_dominance": ("global_json", "btc_dominance"),
    "fear_greed": ("fear_greed_json", "value"),
}

# --------------------------------------------------------------------------
# CJK 分词区间（复用 scripts/history/export_grams.py，保证与入库侧 grams 口径一致）
# —— 见 ARCHITECTURE.md §8.1（1）；导入失败时用等价内联常量兜底，避免整个 app 起不来。
# --------------------------------------------------------------------------
try:
    from scripts.history.export_grams import _CJK_RANGES, _WORD  # noqa: E402
except Exception:  # pragma: no cover - 部署未含 scripts/ 时的兜底
    _CJK_RANGES = (
        (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF),
        (0x3040, 0x30FF), (0xAC00, 0xD7AF),
    )
    _WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]*")

# CJK 连续段匹配（与 export_grams 同一组区间）
_CJK_CHAR = re.compile("[" + "".join(chr(lo) + "-" + chr(hi) for lo, hi in _CJK_RANGES) + "]+")
# 非 CJK 段的英文/数字整词（以字母开头，**不切碎**，如 Solana 保持整词）
_QUERY_WORD = _WORD


def _is_cjk_char(ch: str) -> bool:
    """单字符是否属于 CJK/假名/谚文区间。"""
    code = ord(ch)
    return any(lo <= code <= hi for lo, hi in _CJK_RANGES)


def _iter_segments(text: str) -> Iterator[Tuple[str, bool]]:
    """把文本切成「CJK 段 / 非 CJK 段」交替序列，产出 ``(段, 是否CJK)``。"""
    i, n = 0, len(text)
    while i < n:
        cjk = _is_cjk_char(text[i])
        j = i
        while j < n and _is_cjk_char(text[j]) == cjk:
            j += 1
        yield text[i:j], cjk
        i = j


def build_fts_query(q: str) -> Optional[str]:
    """查询串预处理：CJK → 字符 bigram（单字原样），英文 → 整词（小写）。

    与入库侧 ``export_grams.make_grams`` 同口径，使 ``match_bm25``（simple 分词器）
    能命中 ``body_grams``（连续中文被当作整 token，不做 bigram 则召回 0）。

    Args:
        q: 用户原始关键词（可含中英/空格/标点）。

    Returns:
        空格分隔的 token 串；``q`` 为空或切分后无 token 时返回 ``None``。

    Examples:
        >>> build_fts_query("哔哩哔哩 ETF")
        '哔哩 哩哔 etf'
        >>> build_fts_query("Solana 生态")
        'solana 生态'
        >>> build_fts_query("以太坊")
        '以太 太坊'
    """
    if not q or not q.strip():
        return None
    text = q.strip()

    out: List[str] = []
    seen: set = set()

    def _add(token: str) -> None:
        if token and token not in seen:  # 同 token 去重，保留首次出现
            seen.add(token)
            out.append(token)

    for seg, is_cjk in _iter_segments(text):
        if is_cjk:
            if len(seg) == 1:
                _add(seg)  # 单字 best-effort（大概率 0 命中 → ILIKE 兜底）
            else:
                for i in range(len(seg) - 1):
                    _add(seg[i : i + 2])  # 相邻字符 bigram
        else:
            for word in _QUERY_WORD.findall(seg):
                _add(word.lower())  # 英文整词小写

    return " ".join(out) or None


def _today() -> date:
    """参照「今日」的**唯一**入口（H7 新鲜度判断用；单测可注入固定日期）。

    注入方式（两种，任选其一）：
    1. 单测 monkeypatch：``monkeypatch.setattr(history_svc, "_today", lambda: date(2026, 8, 28))``；
    2. 直接传参：``history_svc.health_overview(today=date(2026, 8, 28))``。
    """
    return date.today()


# --------------------------------------------------------------------------
# 通用工具
# --------------------------------------------------------------------------
def db_ready() -> bool:
    """历史库是否可用（router 据此决定非 0 code）。"""
    return history_db_available()


def _d(value) -> Optional[str]:
    """``date``/``datetime`` → ``YYYY-MM-DD``。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _ts(value) -> Optional[str]:
    """时间戳 → ISO 字符串；``None`` 原样返回。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _as_float(value) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _month_range(table: str, from_: Optional[str], to: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """取 ``table`` 的日期边界，并用外部 ``from_``/``to`` 收窄（缺省即全量）。

    仅接受 ``YYYY-MM-DD`` 形态的外部入参（非法则忽略，退回边界），避免把坏输入放大成错误。
    """
    lo = hi = None
    try:
        rows = history_query(f"SELECT MIN(date) AS lo, MAX(date) AS hi FROM {table}")
        if rows:
            lo, hi = _d(rows[0]["lo"]), _d(rows[0]["hi"])
    except HistoryDBError:
        return None, None
    if from_ and _is_date(from_):
        lo = max(lo, from_) if lo else from_
    if to and _is_date(to):
        hi = min(hi, to) if hi else to
    return lo, hi


def _is_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def _parse_csv(value: Optional[str]) -> List[str]:
    """逗号分隔参数 → 去空、去重、保序的列表。"""
    if not value:
        return []
    out: List[str] = []
    for item in value.split(","):
        key = item.strip()
        if key and key not in out:
            out.append(key)
    return out


def _empty(model_cls):
    """构造某响应模型的空实例（数据缺失时返回）。"""
    return model_cls()


# --------------------------------------------------------------------------
# H1 GET /api/history/dates
# --------------------------------------------------------------------------
def list_dates() -> HistoryDatesResponse:
    """采集日历：每日 scan 概要 + 最新（含残缺）与最新完整扫描日、最新宏观日。"""
    try:
        scan_rows = history_query(
            "SELECT date, is_partial, deep_files_actual, light_files_actual "
            "FROM scan_day ORDER BY date"
        )
        macro_rows = history_query(
            "SELECT date, COUNT(*) AS n FROM macro_snapshot GROUP BY date"
        )
        complete = history_query("SELECT date FROM v_latest_complete_date")
    except Exception:  # noqa: BLE001 - 只读查询失败一律返回空结构
        return _empty(HistoryDatesResponse)

    macro_cnt = {}
    for r in macro_rows:
        key = _d(r["date"])
        macro_cnt[key] = int(r["n"] or 0)

    dates: List[HistoryDateRow] = []
    for r in scan_rows:
        key = _d(r["date"])
        dates.append(
            HistoryDateRow(
                date=key,
                is_partial=bool(r["is_partial"]) if r["is_partial"] is not None else None,
                deep_count=int(r["deep_files_actual"] or 0),
                light_count=int(r["light_files_actual"] or 0),
                macro_count=macro_cnt.pop(key, 0),
            )
        )
    # 仅有宏观、无 scan 的日期也纳入日历（is_partial=None）
    for key in sorted(macro_cnt):
        dates.append(HistoryDateRow(date=key, is_partial=None, macro_count=macro_cnt[key]))
    dates.sort(key=lambda x: x.date)

    scan_latest = _d(scan_rows[-1]["date"]) if scan_rows else None
    latest_macro = max([d for d in dates if d.macro_count], key=lambda x: x.date, default=None)
    return HistoryDatesResponse(
        dates=dates,
        latest=scan_latest,
        latest_complete=_d(complete[0]["date"]) if complete else None,
        latest_macro=latest_macro.date if latest_macro else None,
    )


# --------------------------------------------------------------------------
# H2 GET /api/history/coin/{coin_id}/series
# --------------------------------------------------------------------------
def coin_series(
    coin_id: str,
    from_: Optional[str] = None,
    to: Optional[str] = None,
    metrics: Optional[str] = None,
) -> CoinSeriesResponse:
    """单币多指标时序：升序、缺失日 ``present:false``，**不插值**，``gaps`` 显式。"""
    requested = _parse_csv(metrics) or list(DEFAULT_METRICS)
    supported = [m for m in requested if m in SERIES_METRICS]
    unavailable = [m for m in requested if m not in SERIES_METRICS]
    if not supported:
        supported = [m for m in DEFAULT_METRICS if m in SERIES_METRICS]

    lo, hi = _month_range("scan_day", from_, to)
    if not lo or not hi:
        return CoinSeriesResponse(coin_id=coin_id, metrics=supported, unavailable=unavailable)

    try:
        rows = history_query(
            "SELECT date, " + ", ".join(SERIES_METRICS[m] for m in supported)
            + " FROM coin_daily_snapshot WHERE coin_id = ? AND date BETWEEN ? AND ? ORDER BY date",
            [coin_id, lo, hi],
        )
        days = history_query(
            "SELECT date FROM scan_day WHERE date BETWEEN ? AND ? ORDER BY date", [lo, hi]
        )
    except Exception:  # noqa: BLE001 - 只读查询失败一律降级为空结构
        return CoinSeriesResponse(coin_id=coin_id, metrics=supported, unavailable=unavailable)

    by_day = {_d(r["date"]): r for r in rows}
    series: List[SeriesPoint] = []
    gaps: List[str] = []
    for r in days:
        key = _d(r["date"])
        rec = by_day.get(key)
        if rec is None:
            gaps.append(key)
            series.append(SeriesPoint(date=key, present=False))
        else:
            vals = {m: (rec[m] if m == "rank" else _as_float(rec[m])) for m in supported}
            series.append(SeriesPoint(date=key, present=True, **vals))
    return CoinSeriesResponse(
        coin_id=coin_id,
        metrics=supported,
        unavailable=unavailable,
        series=series,
        gaps=gaps,
    )


# --------------------------------------------------------------------------
# H3 GET /api/history/categories/timeline
# --------------------------------------------------------------------------
def categories_timeline(
    from_: Optional[str] = None,
    to: Optional[str] = None,
    category: Optional[str] = None,
) -> CategoriesTimelineResponse:
    """板块时间线：每 (date, category) 的币数 / 总市值 / 平均 24h 涨跌。

    口径与 ``build_sectors`` 一致：仅统计 ``has_market=TRUE`` 的成员（带市场数据的成员）。
    """
    lo, hi = _month_range("category_membership", from_, to)
    if not lo or not hi:
        return CategoriesTimelineResponse()

    params: List = [lo, hi]
    sql = (
        "SELECT date, category_slug, COUNT(*) AS coin_count, "
        "SUM(market_cap) AS total_mcap, AVG(chg24) AS avg_chg "
        "FROM category_membership WHERE has_market = TRUE AND date BETWEEN ? AND ?"
    )
    if category:
        sql += " AND category_slug = ?"
        params.append(category)
    sql += " GROUP BY date, category_slug ORDER BY date, category_slug"

    try:
        rows = history_query(sql, params)
    except Exception:  # noqa: BLE001 - 只读查询失败一律降级为空结构
        return CategoriesTimelineResponse()

    series = [
        CategoryTimelinePoint(
            date=_d(r["date"]),
            category=r["category_slug"],
            coin_count=int(r["coin_count"] or 0),
            total_mcap=_as_float(r["total_mcap"]),
            avg_chg=round(_as_float(r["avg_chg"]) or 0.0, 4),
        )
        for r in rows
    ]
    return CategoriesTimelineResponse(series=series)


# --------------------------------------------------------------------------
# H4 GET /api/history/news/timeline
# --------------------------------------------------------------------------
def news_timeline(
    from_: Optional[str] = None,
    to: Optional[str] = None,
    coin_id: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> NewsTimelineResponse:
    """新闻/内容时间线（按 ``content_archive``），支持币种/分类/来源过滤 + 分页。"""
    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
    offset = max(0, int(offset or 0))
    lo, hi = _month_range("content_archive", from_, to)
    if not lo or not hi:
        return NewsTimelineResponse()

    alias = "c"
    where = f"{alias}.date BETWEEN ? AND ?"
    params: List = [lo, hi]
    if coin_id:
        where += f" AND {alias}.coin_id = ?"
        params.append(coin_id)
    if source:
        where += f" AND {alias}.source = ?"
        params.append(source)
    if category:
        where += (
            f" AND EXISTS (SELECT 1 FROM category_membership cm "
            f"WHERE cm.date = {alias}.date AND cm.coin_id = {alias}.coin_id AND cm.category_slug = ?)"
        )
        params.append(category)

    try:
        total_rows = history_query(
            f"SELECT COUNT(*) AS n FROM content_archive {alias} WHERE {where}", params
        )
        rows = history_query(
            f"SELECT {alias}.date, {alias}.coin_id, {alias}.source, {alias}.title, "
            f"{alias}.url, {alias}.published_ts, {alias}.origin_path "
            f"FROM content_archive {alias} WHERE {where} "
            f"ORDER BY {alias}.date DESC, {alias}.published_ts DESC NULLS LAST "
            f"LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
    except Exception:  # noqa: BLE001 - 只读查询失败一律降级为空结构
        return NewsTimelineResponse()

    items = [
        NewsTimelineItem(
            date=_d(r["date"]),
            coin_id=r["coin_id"],
            source=r["source"],
            title=r["title"],
            url=r["url"],
            ts=_ts(r["published_ts"]),
            origin_path=r["origin_path"],
        )
        for r in rows
    ]
    total = int(total_rows[0]["n"] or 0) if total_rows else len(items)
    return NewsTimelineResponse(items=items, total=total)


# --------------------------------------------------------------------------
# H5 GET /api/history/search —— 全文检索（§8.1 精确规格）
# --------------------------------------------------------------------------
def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 3)


def _make_snippet(text: Optional[str], tokens: List[str], width: int = 180) -> str:
    """取 ``body_text`` 中命中关键词附近的片段（无命中则取开头）。"""
    if not text:
        return ""
    lowered = text.lower()
    best = -1
    best_len = 0
    for tok in tokens:
        if not tok:
            continue
        idx = lowered.find(tok.lower())
        if idx != -1 and (best == -1 or idx < best):
            best, best_len = idx, len(tok)
    if best == -1:
        return text[:width]
    start = max(0, best - 40)
    end = min(len(text), best + best_len + 120)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def _row_to_hit(row: dict, tokens: List[str]) -> SearchHit:
    return SearchHit(
        content_id=row.get("content_id") or "",
        date=_d(row.get("date")),
        coin_id=row.get("coin_id"),
        source=row.get("source"),
        title=row.get("title"),
        snippet=_make_snippet(row.get("body_text"), tokens),
        url=row.get("url"),
        origin_path=row.get("origin_path"),
        score=_as_float(row.get("score")),
    )


def _fts_search(fts_query: str, where: List[str], filt: List, limit: int, offset: int) -> Tuple[List[SearchHit], int]:
    """FTS（OR 语义）主查询：``match_bm25`` 在 SELECT 与 WHERE 各调一次（不能引用别名）。"""
    base = " AND ".join(where)
    count = history_query(
        "SELECT COUNT(*) AS n FROM content_archive c "
        "WHERE fts_main_content_archive.match_bm25(c.content_id, ?, conjunctive := false) IS NOT NULL "
        f"AND {base}",
        [fts_query] + filt,
    )
    total = int(count[0]["n"] or 0)
    rows = history_query(
        "SELECT c.content_id, c.date, c.coin_id, c.source, c.doc_type, c.title, c.url, "
        "c.origin_path, c.body_text, "
        "fts_main_content_archive.match_bm25(c.content_id, ?, conjunctive := false) AS score "
        "FROM content_archive c "
        "WHERE fts_main_content_archive.match_bm25(c.content_id, ?, conjunctive := false) IS NOT NULL "
        f"AND {base} ORDER BY score DESC LIMIT ? OFFSET ?",
        [fts_query, fts_query] + filt + [limit, offset],
    )
    tokens = fts_query.split(" ")
    return [_row_to_hit(r, tokens) for r in rows], total


def _ilike_search(keyword: str, where: List[str], filt: List, limit: int, offset: int) -> Tuple[List[SearchHit], int]:
    """ILIKE 兜底列扫（FTS 0 命中 / 扩展不可用时）；复用同一 date/coin/source 过滤。"""
    base = " AND ".join(where)
    like = "(c.title ILIKE '%' || ? || '%' OR c.body_text ILIKE '%' || ? || '%')"
    count = history_query(
        f"SELECT COUNT(*) AS n FROM content_archive c WHERE {like} AND {base}",
        [keyword, keyword] + filt,
    )
    total = int(count[0]["n"] or 0)
    rows = history_query(
        "SELECT c.content_id, c.date, c.coin_id, c.source, c.doc_type, c.title, c.url, "
        "c.origin_path, c.body_text, NULL AS score "
        f"FROM content_archive c WHERE {like} AND {base} "
        "ORDER BY c.date DESC, c.content_id LIMIT ? OFFSET ?",
        [keyword, keyword] + filt + [limit, offset],
    )
    tokens = [keyword]
    return [_row_to_hit(r, tokens) for r in rows], total


def search(
    q: str = "",
    from_: Optional[str] = None,
    to: Optional[str] = None,
    coin_id: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> SearchResponse:
    """全文检索（H5）：CJK bigram 化 → FTS(OR, conjunctive=false) → 0 命中回退 ILIKE。

    - ``build_fts_query(q)`` 为 ``None``（空查询）→ 返回空结果（不报错）；
    - FTS 命中 0（含「语料确无该词」如 ``'以太坊'``、单字符查询）→ 回退 ILIKE 列扫；
    - FTS 扩展不可用（查询抛错）→ 同样回退 ILIKE；
    - ``body_grams`` 仅索引辅助列，绝不返回前端。
    """
    start = time.perf_counter()
    keyword = (q or "").strip()
    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
    offset = max(0, int(offset or 0))

    fts_query = build_fts_query(keyword)
    lo, hi = _month_range("content_archive", from_, to)
    if not fts_query or not lo or not hi:
        return SearchResponse(query=keyword, hits=[], total=0, took_ms=_elapsed_ms(start))

    where = ["c.date BETWEEN ? AND ?"]
    filt: List = [lo, hi]
    if coin_id:
        where.append("c.coin_id = ?")
        filt.append(coin_id)
    if source:
        where.append("c.source = ?")
        filt.append(source)

    hits: List[SearchHit] = []
    total = 0
    try:
        hits, total = _fts_search(fts_query, where, filt, limit, offset)
    except Exception as exc:  # noqa: BLE001 - FTS 扩展不可用 → 直接 ILIKE
        print(f"[history_svc] FTS 检索不可用，回退 ILIKE：{exc}")
        hits, total = [], 0

    if total == 0:  # 语料确无该词 / 单字符 → ILIKE 兜底（硬要求，不得返回空）
        try:
            hits, total = _ilike_search(keyword, where, filt, limit, offset)
        except Exception as exc:  # noqa: BLE001
            print(f"[history_svc] ILIKE 兜底失败：{exc}")
            hits, total = [], 0

    return SearchResponse(query=keyword, hits=hits, total=total, took_ms=_elapsed_ms(start))


# --------------------------------------------------------------------------
# H6 GET /api/history/health/sources
# --------------------------------------------------------------------------
def health_sources(
    from_: Optional[str] = None,
    to: Optional[str] = None,
    source: Optional[str] = None,
) -> HealthSourcesResponse:
    """逐源逐日健康度 + 源集合漂移 + 缺口。"""
    lo, hi = _month_range("source_status", from_, to)
    if not lo or not hi:
        return HealthSourcesResponse()

    params: List = [lo, hi]
    src_clause = ""
    if source:
        src_clause = " AND source = ?"
        params.append(source)

    try:
        by_rows = history_query(
            "SELECT date, source, ok_cnt, err_cnt, success_rate, avg_confidence "
            "FROM v_source_health_daily WHERE date BETWEEN ? AND ?" + src_clause
            + " ORDER BY date, source",
            params,
        )
        drift_rows = history_query(
            "SELECT date, n_sources FROM v_source_drift WHERE date BETWEEN ? AND ? ORDER BY date",
            [lo, hi],
        )
        gap_rows = history_query(
            "SELECT s.date FROM scan_day s WHERE s.date BETWEEN ? AND ? "
            "AND NOT EXISTS (SELECT 1 FROM source_status ss WHERE ss.date = s.date) ORDER BY s.date",
            [lo, hi],
        )
    except Exception:  # noqa: BLE001 - 只读查询失败一律降级为空结构
        return HealthSourcesResponse()

    by_date = [
        SourceHealthDay(
            date=_d(r["date"]),
            source=r["source"],
            ok=int(r["ok_cnt"] or 0),
            error=int(r["err_cnt"] or 0),
            success_rate=_as_float(r["success_rate"]),
            avg_confidence=_as_float(r["avg_confidence"]),
        )
        for r in by_rows
    ]
    drift = [SourceDriftRow(date=_d(r["date"]), n_sources=int(r["n_sources"] or 0)) for r in drift_rows]
    gaps = [_d(r["date"]) for r in gap_rows]
    return HealthSourcesResponse(by_date=by_date, drift=drift, gaps=gaps)


# --------------------------------------------------------------------------
# H7 GET /api/history/health/overview
# --------------------------------------------------------------------------
def health_overview(today: Optional[date] = None) -> HealthOverviewResponse:
    """采集健康度总览：各链路新鲜度 + 异常 + 批次。

    Args:
        today: 参照日（缺省取 :func:`_today`，即系统今日）。
            显式注入以便单测固定日期、避免测试随时间漂移。
    """
    ref = today or _today()
    try:
        scan_last = history_query("SELECT MAX(date) AS d FROM scan_day")
        macro_last = history_query("SELECT MAX(date) AS d FROM macro_snapshot")
        partial_rows = history_query(
            "SELECT date, deep_files_actual FROM scan_day WHERE is_partial = TRUE ORDER BY date"
        )
        gap_rows = history_query(
            "SELECT COUNT(*) AS n, MIN(date) AS lo, MAX(date) AS hi "
            "FROM v_collection_calendar WHERE has_scan = FALSE"
        )
        batch_rows = history_query(
            "SELECT batch_id, started_at, finished_at, mode, scope, status, rows_loaded, rows_rejected "
            "FROM ingest_batch ORDER BY started_at DESC LIMIT 10"
        )
    except Exception:  # noqa: BLE001 - 只读查询失败一律降级为空结构
        return _empty(HealthOverviewResponse)

    def _status(last) -> CollectionStatus:
        if last is None:
            return CollectionStatus(last_date=None, gap_days=None, status="empty")
        gap = (ref - last).days
        return CollectionStatus(
            last_date=_d(last), gap_days=gap, status="ok" if gap <= STALE_DAYS else "stale"
        )

    scan_last_date = scan_last[0]["d"] if scan_last else None
    macro_last_date = macro_last[0]["d"] if macro_last else None
    collections = {"scan": _status(scan_last_date), "macro": _status(macro_last_date)}

    anomalies: List[dict] = []
    for r in partial_rows:
        anomalies.append(
            {
                "kind": "partial_day",
                "date": _d(r["date"]),
                "detail": f"deep_files_actual={int(r['deep_files_actual'] or 0)}（残缺日，latest 跳过）",
            }
        )
    for name, st in collections.items():
        if st.status == "stale":
            anomalies.append(
                {
                    "kind": "stale_collection",
                    "collection": name,
                    "last_date": st.last_date,
                    "gap_days": st.gap_days,
                }
            )
    if gap_rows and int(gap_rows[0]["n"] or 0) > 0:
        anomalies.append(
            {
                "kind": "scan_gap",
                "window": [_d(gap_rows[0]["lo"]), _d(gap_rows[0]["hi"])],
                "missing_days": int(gap_rows[0]["n"] or 0),
            }
        )

    batches = [
        {
            "batch_id": r["batch_id"],
            "started_at": _ts(r["started_at"]),
            "finished_at": _ts(r["finished_at"]),
            "mode": r["mode"],
            "scope": r["scope"],
            "status": r["status"],
            "rows_loaded": int(r["rows_loaded"] or 0),
            "rows_rejected": int(r["rows_rejected"] or 0),
        }
        for r in batch_rows
    ]
    return HealthOverviewResponse(collections=collections, anomalies=anomalies, batches=batches)


# --------------------------------------------------------------------------
# H8 GET /api/history/macro/series
# --------------------------------------------------------------------------
def macro_series(
    from_: Optional[str] = None,
    to: Optional[str] = None,
    metric: str = "btc_dominance",
) -> MacroHistorySeriesResponse:
    """宏观指标时序（btc_dominance / fear_greed）。

    只输出**取值非空**的快照点（``fear_greed`` 在采集端恒缺失 → 返回空 series，
    由 router 转成 404，而非伪造 null 点）。
    """
    metric = (metric or "btc_dominance").strip()
    lo, hi = _month_range("macro_snapshot", from_, to)
    if not lo or not hi:
        return MacroHistorySeriesResponse(metric=metric)
    if metric not in MACRO_METRICS:
        return MacroHistorySeriesResponse(metric=metric)

    json_col, path = MACRO_METRICS[metric]
    try:
        rows = history_query(
            f"SELECT date, snapshot_time, {json_col} AS payload FROM macro_snapshot "
            f"WHERE date BETWEEN ? AND ? ORDER BY date, snapshot_time",
            [lo, hi],
        )
    except Exception:  # noqa: BLE001 - 只读查询失败一律降级为空结构
        return MacroHistorySeriesResponse(metric=metric)

    series: List[MacroSeriesPoint] = []
    for r in rows:
        payload = r["payload"]
        value = None
        if payload is not None:
            try:
                obj = json.loads(payload) if isinstance(payload, str) else payload
            except (ValueError, TypeError):
                obj = None
            if isinstance(obj, dict):
                value = _as_float(obj.get(path))
        if value is None:  # 该快照无此指标 → 跳过（不伪造 null 点）
            continue
        st = str(r["snapshot_time"] or "")
        snapshot_at = f"{_d(r['date'])}T{st[:2]}:{st[2:4]}" if len(st) >= 4 else _d(r["date"])
        series.append(MacroSeriesPoint(snapshot_at=snapshot_at, value=value))
    return MacroHistorySeriesResponse(metric=metric, series=series)
