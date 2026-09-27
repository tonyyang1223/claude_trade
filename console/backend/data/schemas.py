"""Pydantic 响应模型（与前端 TS 类型一一对应，见前端 src/types/models.ts）。

字段命名采用「短名 + camelCase 风格的小写下划线」以贴合既有数据口径，与前端
models.ts 完全对齐：前端用 chg24 / mcap / vol 等短字段，避免大改。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
    narrative: dict = Field(default_factory=dict)  # {description,categories,genesisDate,officialLinks,communityLinks}
    social: dict = Field(default_factory=dict)  # {mentions,upvotes,redditSubs,communityScore,newsCount,sentiment,signal}
    news: List[NewsItem] = Field(default_factory=list)
    scoresAvailable: bool = False
    onchainAvailable: bool = False
    dataSource: str = "offline"  # offline | live


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
    disclaimer: Optional[str] = None


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
    prevDay: Optional[str] = None
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
