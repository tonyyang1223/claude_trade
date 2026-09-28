"""历史数据库查询端点 H1–H8 —— 见 docs/history-db/ARCHITECTURE.md §8。

- 全部为**新增只读**端点，老 10 端点零改动；
- 统一信封 ``{code, message, data}``；数据缺失返回空结构 + 非 0 code，**绝不 500**；
- 处理函数一律**同步 ``def``**（Starlette 线程池），与现有 router 一致；
- 以模块方式导入服务层（``from services import history_svc``）避免处理函数与导入名冲突。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from core.envelope import failure, success
from services import history_svc

router = APIRouter(tags=["history"])


# --------------------------------------------------------------------------
# H1 采集日历
# --------------------------------------------------------------------------
@router.get("/api/history/dates")
def history_dates() -> dict:
    data = history_svc.list_dates()
    if not data.dates:
        return failure(503, "历史库不可用或暂无扫描数据", data.model_dump())
    return success(data.model_dump())


# --------------------------------------------------------------------------
# H2 单币多指标时序
# --------------------------------------------------------------------------
@router.get("/api/history/coin/{coin_id}/series")
def history_coin_series(
    coin_id: str,
    from_: Optional[str] = Query(None, alias="from", description="起始日 YYYY-MM-DD"),
    to: Optional[str] = Query(None, description="结束日 YYYY-MM-DD"),
    metrics: Optional[str] = Query(
        None, description="逗号分隔指标，如 price_usd,market_cap,rank"
    ),
) -> dict:
    data = history_svc.coin_series(coin_id, from_, to, metrics)
    if not any(p.present for p in data.series):
        return failure(404, f"所选区间无该币历史数据: {coin_id}（含显式 gaps）", data.model_dump())
    return success(data.model_dump())


# --------------------------------------------------------------------------
# H3 板块时间线
# --------------------------------------------------------------------------
@router.get("/api/history/categories/timeline")
def history_categories_timeline(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    category: Optional[str] = Query(None, description="板块 slug，缺省取全部"),
) -> dict:
    data = history_svc.categories_timeline(from_, to, category)
    if not data.series:
        return failure(404, "所选区间无板块统计数据", data.model_dump())
    return success(data.model_dump())


# --------------------------------------------------------------------------
# H4 新闻/内容时间线
# --------------------------------------------------------------------------
@router.get("/api/history/news/timeline")
def history_news_timeline(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    coin_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(history_svc.DEFAULT_LIMIT, ge=1, le=history_svc.MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> dict:
    data = history_svc.news_timeline(from_, to, coin_id, category, source, limit, offset)
    if not data.items:
        return failure(404, "所选条件下无归档内容", data.model_dump())
    return success(data.model_dump())


# --------------------------------------------------------------------------
# H5 全文检索（§8.1 规格：CJK bigram 化 → FTS(OR) → 0 命中回退 ILIKE）
# --------------------------------------------------------------------------
@router.get("/api/history/search")
def history_search(
    q: str = Query("", description="检索关键词（中英混合）"),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    coin_id: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(history_svc.DEFAULT_LIMIT, ge=1, le=history_svc.MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> dict:
    data = history_svc.search(q, from_, to, coin_id, source, limit, offset)
    # 「无结果」是合法搜索结局（§8.1 明确「不报错」）→ code=0 + 空 hits。
    if not data.hits:
        return success(data.model_dump(), message="无匹配结果")
    return success(data.model_dump())


# --------------------------------------------------------------------------
# H6 逐源健康度
# --------------------------------------------------------------------------
@router.get("/api/history/health/sources")
def history_health_sources(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
) -> dict:
    data = history_svc.health_sources(from_, to, source)
    if not data.by_date and not data.drift:
        return failure(404, "所选区间无逐源健康度数据", data.model_dump())
    return success(data.model_dump())


# --------------------------------------------------------------------------
# H7 采集健康度总览
# --------------------------------------------------------------------------
@router.get("/api/history/health/overview")
def history_health_overview() -> dict:
    data = history_svc.health_overview()
    if not data.collections:
        return failure(503, "历史库不可用", data.model_dump())
    return success(data.model_dump())


# --------------------------------------------------------------------------
# H8 宏观指标时序
# --------------------------------------------------------------------------
@router.get("/api/history/macro/series")
def history_macro_series(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    metric: str = Query("btc_dominance", description="btc_dominance|fear_greed"),
) -> dict:
    if metric not in history_svc.MACRO_METRICS:
        return failure(400, f"不支持的宏观指标: {metric}", {"metric": metric, "series": []})
    data = history_svc.macro_series(from_, to, metric)
    if not data.series:
        return failure(404, f"该宏观指标暂无数据: {metric}", data.model_dump())
    return success(data.model_dump())
