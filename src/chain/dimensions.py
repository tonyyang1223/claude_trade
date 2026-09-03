"""维度注册表装配（ADR-002 落地）。

所有分析维度在此集中注册；新增维度 = 加一行 register，不动流水线。
维度权重可随类别调整（见 CATEGORY_WEIGHTS）。

维度清单（8 个）：
  security          欺诈/安全（最高权重）
  trend             趋势强弱（结构面：24h 涨跌 + 流动性深度 + 净买卖压）
  momentum          多周期动量（Meme 核心：m5/h1/h6/h24 + 近1h 净流入）
  liquidity_health  流动性健康（流动性/市值、换手率、绝对深度）
  sentiment         社媒情绪（需 Twitter/Reddit 凭证，当前多缺失→排除加权）
  innovation        技术创新（叙事技术含量基准）
  taxonomy          类别清晰度（叙事可识别度）
  community         社区基础（官方渠道弱信号）
"""
from __future__ import annotations

from .scoring.dimension import Dimension, DimensionRegistry
from .community import compute_community
from .innovation import compute_innovation
from .liquidity_health import compute_liquidity_health
from .momentum import compute_momentum
from .security import compute_security
from .sentiment import compute_sentiment
from .taxonomy import compute_taxonomy
from .trend import compute_trend

# 默认权重（类别无关基线），权重和为 1.0
DEFAULT_WEIGHTS = {
    "security": 0.28,
    "trend": 0.13,
    "momentum": 0.13,
    "liquidity_health": 0.10,
    "sentiment": 0.12,
    "innovation": 0.12,
    "taxonomy": 0.07,
    "community": 0.05,
}

# 类别权重策略：Meme 重动量/趋势/流动性，轻创新；RWA/AI 重安全/创新、轻情绪
CATEGORY_WEIGHTS = {
    "Meme": {"security": 0.25, "trend": 0.15, "momentum": 0.18, "liquidity_health": 0.12,
             "sentiment": 0.12, "innovation": 0.05, "taxonomy": 0.08, "community": 0.05},
    "RWA": {"security": 0.38, "trend": 0.12, "momentum": 0.08, "liquidity_health": 0.10,
            "sentiment": 0.10, "innovation": 0.22, "taxonomy": 0.10, "community": 0.05},
    "AI": {"security": 0.33, "trend": 0.12, "momentum": 0.08, "liquidity_health": 0.10,
           "sentiment": 0.12, "innovation": 0.25, "taxonomy": 0.05, "community": 0.05},
}


def build_registry() -> DimensionRegistry:
    reg = DimensionRegistry()
    reg.register(Dimension("security", DEFAULT_WEIGHTS["security"], compute_security, desc="欺诈/安全"))
    reg.register(Dimension("trend", DEFAULT_WEIGHTS["trend"], compute_trend, desc="趋势强弱"))
    reg.register(Dimension("momentum", DEFAULT_WEIGHTS["momentum"], compute_momentum, desc="多周期动量"))
    reg.register(Dimension("liquidity_health", DEFAULT_WEIGHTS["liquidity_health"],
                           compute_liquidity_health, desc="流动性健康"))
    reg.register(Dimension("sentiment", DEFAULT_WEIGHTS["sentiment"], compute_sentiment, desc="社媒情绪"))
    reg.register(Dimension("innovation", DEFAULT_WEIGHTS["innovation"], compute_innovation, desc="技术创新"))
    reg.register(Dimension("taxonomy", DEFAULT_WEIGHTS["taxonomy"], compute_taxonomy, desc="类别清晰度"))
    reg.register(Dimension("community", DEFAULT_WEIGHTS["community"], compute_community, desc="社区基础"))
    return reg


def weights_for(category: str) -> dict:
    """按识别类别返回权重配置（类别权重策略优先，否则默认）。"""
    return dict(CATEGORY_WEIGHTS.get(category, DEFAULT_WEIGHTS))
