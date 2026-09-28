"""Pydantic 响应模型（与前端 TS 类型一一对应，见前端 src/types/models.ts）。

字段命名采用「短名 + camelCase 风格的小写下划线」以贴合既有数据口径，与前端
models.ts 完全对齐：前端用 chg24 / mcap / vol 等短字段，避免大改。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------
# 公共模型
# --------------------------------------------------------------------------
class CoinBrief(BaseModel):
    id: str
    sym: Optional[str] = None
    name: Optional[str] = None
    rank: Optional[int] = None
    price: Optional[float] = None
    mcap: Optional[float] = None
    vol: Optional[float] = None
    chg24: float = 0.0
    chg7d: float = 0.0


class NewsItem(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None
    kind: Optional[str] = None


class SectorStat(BaseModel):
    cat: str
    count: int
    mcap: Optional[float] = None
    avgChg: float = 0.0


# --------------------------------------------------------------------------
# 市场总览 E2
# --------------------------------------------------------------------------
class MarketOverviewResponse(BaseModel):
    meta: dict = Field(default_factory=dict)
    kpi: dict = Field(default_factory=dict)
    distribution: dict = Field(default_factory=dict)  # {labels:[...], values:[...]}
    gainers: List[CoinBrief] = Field(default_factory=list)
    losers: List[CoinBrief] = Field(default_factory=list)
    topByMcap: List[CoinBrief] = Field(default_factory=list)
    sectors: List[SectorStat] = Field(default_factory=list)


# --------------------------------------------------------------------------
# 百倍币雷达 E5
# --------------------------------------------------------------------------
class OpportunityItem(BaseModel):
    id: str
    sym: Optional[str] = None
    name: Optional[str] = None
    rank: Optional[int] = None
    mcap: Optional[float] = None
    composite: float = 0.0
    dims: Dict[str, float] = Field(default_factory=dict)  # {mcapScale,growth,narrative,community,onchain}
    category: Optional[str] = None


class OpportunityRadarResponse(BaseModel):
    meta: dict = Field(default_factory=dict)  # {date, count, weights}
    rankings: List[OpportunityItem] = Field(default_factory=list)


# --------------------------------------------------------------------------
# 币种档案 E4 + 实时抓取 E10
# --------------------------------------------------------------------------
class TokenDetailResponse(BaseModel):
    basic: CoinBrief
    ath: Optional[float] = None
    athChg: Optional[float] = None
    # 离线基线仅含 {categories}；{description, officialLinks, communityLinks} 由 E10 实时抓取补全
    narrative: dict = Field(default_factory=dict)
    # {mentions, upvotes, redditSubs, communityScore, newsCount, biliCount, sentiment, signal}
    social: dict = Field(default_factory=dict)
    # 离线基线恒为空列表：新闻计数见 social.newsCount，实时列表由 E10 填充
    news: List[NewsItem] = Field(default_factory=list)


class WebResearchResponse(BaseModel):
    coinId: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    officialLinks: dict = Field(default_factory=dict)
    communityLinks: dict = Field(default_factory=dict)
    sentiment: dict = Field(default_factory=dict)
    watchlistUsers: Optional[int] = None
    news: List[NewsItem] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    fetchedAt: Optional[str] = None


# --------------------------------------------------------------------------
# 竞品对比 E6
# --------------------------------------------------------------------------
class ComparisonProject(BaseModel):
    coin_id: str
    coin_name: Optional[str] = None
    symbol: Optional[str] = None
    total_score: Optional[float] = None
    rating: Optional[str] = None
    risk_level: Optional[str] = None
    recommendation: Optional[str] = None
    market_score: Optional[float] = None
    technical_score: Optional[float] = None
    onchain_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    github_score: Optional[float] = None
    social_score: Optional[float] = None
    risk_score: Optional[float] = None


class ComparisonResponse(BaseModel):
    projects: List[ComparisonProject] = Field(default_factory=list)
    matrix: dict = Field(default_factory=dict)
    winner: str = ""
    summary: str = ""


# --------------------------------------------------------------------------
# 链上分析 E7
# --------------------------------------------------------------------------
class OnchainResponse(BaseModel):
    chain: str = ""
    address: str = ""
    symbol: Optional[str] = None
    name: Optional[str] = None
    dims: Dict[str, float] = Field(default_factory=dict)  # 各维 0-10
    total: float = 0.0
    decision: str = ""
    risk: str = ""
    position: str = ""
    triggers: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    flags: List[dict] = Field(default_factory=list)
    disclaimer: str = ""


# --------------------------------------------------------------------------
# 评分与建议 E8
# --------------------------------------------------------------------------
class ScoreResponse(BaseModel):
    coinId: str
    name: Optional[str] = None
    symbol: Optional[str] = None
    scores: Dict[str, float] = Field(default_factory=dict)  # 各维 0-5
    totalScore: float = 0.0
    rating: str = ""
    recommendation: str = ""
    riskLevel: str = ""
    advice: dict = Field(default_factory=dict)  # {action,positionRange,horizon,triggers,rationale,disclaimer}


# --------------------------------------------------------------------------
# 宏观 BTC 占比 E9
# --------------------------------------------------------------------------
class MacroResponse(BaseModel):
    currentDominance: float = 0.0
    trend: str = ""
    marketPhase: str = ""
    altcoinSeason: bool = False
    recommendation: str = ""


# --------------------------------------------------------------------------
# meta / health
# --------------------------------------------------------------------------
class MetaResponse(BaseModel):
    date: Optional[str] = None
    scanTime: Optional[str] = None
    deepTotal: Optional[int] = None
    lightTotal: Optional[int] = None
    coinCnt: Optional[int] = None
    availableDates: List[str] = Field(default_factory=list)
    weights: dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    dataDate: Optional[str] = None


# --------------------------------------------------------------------------
# 历史数据库查询端点 H1–H8（只读，见 ARCHITECTURE.md §8）
# --------------------------------------------------------------------------
class HistoryDateRow(BaseModel):
    """H1 单日采集概要。``is_partial`` 为 None 表示该日只有 macro、无 scan。"""

    date: str
    is_partial: Optional[bool] = None
    deep_count: int = 0          # scan_day.deep_files_actual（残缺日以落盘为准）
    light_count: int = 0         # scan_day.light_files_actual
    macro_count: int = 0         # 该日 macro_snapshot 数


class HistoryDatesResponse(BaseModel):
    """H1 GET /api/history/dates。"""

    dates: List[HistoryDateRow] = Field(default_factory=list)
    latest: Optional[str] = None            # 最新扫描日（含残缺日）
    latest_complete: Optional[str] = None   # 最新完整扫描日（跳过残缺日）
    latest_macro: Optional[str] = None      # 最新宏观快照日


class SeriesPoint(BaseModel):
    """H2 单日数据点；``present=False`` 表示该日缺该币（**不插值**）。

    具体指标键（如 price_usd / market_cap / rank）通过 extra 动态附加。
    """

    model_config = ConfigDict(extra="allow")

    date: str
    present: bool = False


class CoinSeriesResponse(BaseModel):
    """H2 GET /api/history/coin/{coin_id}/series。"""

    coin_id: str = ""
    metrics: List[str] = Field(default_factory=list)      # 实际返回的指标（已支持）
    unavailable: List[str] = Field(default_factory=list)  # 请求但历史库无此指标
    series: List[SeriesPoint] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)         # 缺失日（显式，不插值）


class CategoryTimelinePoint(BaseModel):
    """H3 单日单板块统计点。"""

    date: str
    category: str
    coin_count: int = 0
    total_mcap: Optional[float] = None
    avg_chg: Optional[float] = None


class CategoriesTimelineResponse(BaseModel):
    """H3 GET /api/history/categories/timeline。"""

    series: List[CategoryTimelinePoint] = Field(default_factory=list)


class NewsTimelineItem(BaseModel):
    """H4 单条新闻/内容归档项。"""

    date: str
    coin_id: str
    source: str
    title: Optional[str] = None
    url: Optional[str] = None
    ts: Optional[str] = None
    origin_path: Optional[str] = None


class NewsTimelineResponse(BaseModel):
    """H4 GET /api/history/news/timeline。"""

    items: List[NewsTimelineItem] = Field(default_factory=list)
    total: int = 0


class SearchHit(BaseModel):
    """H5 单条检索命中（本轮未实现，见 history_svc.search）。"""

    content_id: str = ""
    date: Optional[str] = None
    coin_id: Optional[str] = None
    source: Optional[str] = None
    title: Optional[str] = None
    snippet: Optional[str] = None
    url: Optional[str] = None
    origin_path: Optional[str] = None
    score: Optional[float] = None


class SearchResponse(BaseModel):
    """H5 GET /api/history/search（占位）。"""

    query: str = ""
    hits: List[SearchHit] = Field(default_factory=list)
    total: int = 0
    took_ms: float = 0.0


class SourceHealthDay(BaseModel):
    """H6 单日单源健康度。"""

    date: str
    source: str
    ok: int = 0
    error: int = 0
    success_rate: Optional[float] = None
    avg_confidence: Optional[float] = None


class SourceDriftRow(BaseModel):
    """H6 单日源集合规模（漂移探针：13 vs 14）。"""

    date: str
    n_sources: int = 0


class HealthSourcesResponse(BaseModel):
    """H6 GET /api/history/health/sources。"""

    by_date: List[SourceHealthDay] = Field(default_factory=list)
    drift: List[SourceDriftRow] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)


class CollectionStatus(BaseModel):
    """H7 单个采集链路的新鲜度。"""

    last_date: Optional[str] = None
    gap_days: Optional[int] = None
    status: str = "unknown"   # ok | stale | empty


class HealthOverviewResponse(BaseModel):
    """H7 GET /api/history/health/overview。"""

    collections: Dict[str, CollectionStatus] = Field(default_factory=dict)
    anomalies: List[dict] = Field(default_factory=list)
    batches: List[dict] = Field(default_factory=list)


class MacroSeriesPoint(BaseModel):
    """H8 单个宏观快照数据点。"""

    snapshot_at: Optional[str] = None
    value: Optional[float] = None


class MacroHistorySeriesResponse(BaseModel):
    """H8 GET /api/history/macro/series。"""

    metric: str = ""
    series: List[MacroSeriesPoint] = Field(default_factory=list)
