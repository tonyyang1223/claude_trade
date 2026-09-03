"""链上分析技能 · 配置与策略层（设计文档 §5）。

所有影响分析结论的数字集中于此（权重 / 决策档位与护栏 / band 阈值 / 交易对
选择 / 价格校验 / 税与集中度惩罚 / 叙事词表 / 数据源端点）。代码只读 Config，
模块内部不再硬编码可调策略；未提供 Config 时各维度回落模块内现值（向后兼容）。

加载优先级：链级 YAML 覆盖 > 用户 YAML/字典 > 内嵌 DEFAULT。链级文件约定
位于 config/chain/ 下（chain.bnb.yaml 等），可选的顶层覆盖文件由调用方传入。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

ENGINE_VERSION = "2.0.0"


# ---------------------------------------------------------------------------
# 安全维度策略（security.py 扣分与上限）
# ---------------------------------------------------------------------------
class SecurityPolicy(BaseModel):
    honeypot_badge: str = "🚨 疑似 honeypot（买入后无法卖出）"
    blacklist_badge: str = "🚨 被列入风险/黑名单库"
    min_coverage_for_high: int = 3            # 高分(≥9.5)所需最少已核验信号数
    low_coverage_cap: float = 7.0             # 证据不足时安全分封顶
    lp_unverified_cap: float = 7.5            # LP+持币集中度双未知时封顶
    tax_over_pct: float = 10.0                # 超过即视为异常交易税
    lp_locked_min_pct: float = 50.0           # LP 锁仓低于此值视为 rug 风险
    top10_concentration_pct: float = 50.0     # 前10地址持仓占比警戒线
    creator_concentration_pct: float = 20.0   # 创建者持仓占比警戒线
    penalties: Dict[str, float] = Field(default_factory=lambda: {
        "mint": -2.5, "take_back": -2.5, "proxy": -2.5,
        "blacklist_fn": -2.0, "pause": -1.5, "unverified": -1.5,
        "tax_over": -2.0, "lp_low_lock": -1.5, "lp_not_burned": -1.0,
        "top10_concentrated": -1.5, "creator_concentrated": -1.0,
    })


# ---------------------------------------------------------------------------
# 决策档位与护栏（advisor.py）
# ---------------------------------------------------------------------------
class DecisionBand(BaseModel):
    min_total: float
    label: str
    position: str
    risk: str
    note: str = ""


class DecisionConfig(BaseModel):
    # 档位：min_total 降序匹配。index 含义：0 最激进，len(bands) = reject 兜底档
    bands: List[DecisionBand] = Field(default_factory=lambda: [
        DecisionBand(min_total=7.5, label="🟢 可关注 · 小仓试探",
                     position="5%-10%", risk="中", note="综合分较高，可小仓试探"),
        DecisionBand(min_total=6.0, label="🟡 持有/观察",
                     position="3%-5%", risk="中", note="综合分中等，持有观察"),
        DecisionBand(min_total=5.0, label="🟡 轻仓观察",
                     position="1%-3%", risk="中", note="综合分偏低，仅轻仓观察"),
    ])
    reject_label: str = "🔴 回避"
    reject_position: str = "0%"
    reject_risk: str = "高"
    reject_note: str = "综合分偏低，多项指标不支持"

    hard_block_security_lt: float = 4.0        # 安全分 < 此值 → 欺诈硬拦截
    hard_block_label: str = "🚫 高风险 · 不建议参与"
    hard_block_note: str = "安全分 < 4，疑似欺诈/rug 特征，禁止参与"
    soft_block_security_lt: float = 6.0        # 安全分 < 此值 → 观望
    soft_block_label: str = "⚠️ 观望 · 谨慎回避"
    soft_block_note: str = "安全分偏低，存在多重红旗，暂不介入"

    # 风险护栏（只降不升）触发后档位下限（0=最宽松，len(bands)=回避档）
    guard_age_days_lt: float = 1.0             # 护栏①：币龄 < 1 天
    guard_age_level: int = 2                   #   至少降到第 2 档（轻仓观察）
    guard_liquidity_health_lt: float = 3.0     # 护栏②：流动性健康分 < 3
    guard_liquidity_level: int = 2             #   至少降到第 2 档（轻仓观察）
    guard_newcoin_days_lt: float = 7.0         # 护栏③：<7 天且 LP 未知
    guard_newcoin_level: int = 3               #   至少降到第 3 档（回避）

    overheat_pct: float = 35.0                 # 24h 过热触发
    liq_min_usd: float = 50_000.0              # 流动性过薄触发


# ---------------------------------------------------------------------------
# 市场/动量/趋势/流动性阈值（dexscreener + orchestrator + 各 compute）
# ---------------------------------------------------------------------------
class MarketConfig(BaseModel):
    pair_floor_ratio: float = 0.10             # 交易对流动性门槛（最大池比值）
    stablecoin_bonus: float = 1.15             # 稳定币计价温和加成
    price_anomaly_ratio: float = 0.50          # price×supply 与 FDV 背离阈值
    newcoin_days: float = 1.0                  # 低于此币龄按「超新币」处理

    trend_band_healthy_hi: float = 15.0        # 温和上行上限
    trend_band_strong_hi: float = 35.0         # 强势但未过热上限
    trend_bsr_bull: float = 1.2
    trend_bsr_bear: float = 0.8
    trend_liq_good_usd: float = 100_000.0
    trend_liq_bad_usd: float = 10_000.0

    momentum_same_dir_count: int = 3           # 多周期同向判定所需数
    momentum_h24_overheat: float = 50.0        # 24h 极端拉升
    momentum_h24_deepdrop: float = -40.0       # 24h 深跌
    momentum_buy_dominance: float = 1.3        # 近1h 买盘占优倍数

    liq_mc_ratio_healthy: float = 0.15
    liq_mc_ratio_mid: float = 0.05
    liq_turnover_hot: float = 10.0             # 24h 换手异常高
    liq_turnover_active: float = 3.0
    liq_abs_good_usd: float = 500_000.0
    liq_abs_bad_usd: float = 50_000.0


# ---------------------------------------------------------------------------
# 维度权重（dimensions.py）
# ---------------------------------------------------------------------------
class WeightsConfig(BaseModel):
    default: Dict[str, float] = Field(default_factory=lambda: {
        "security": 0.28, "trend": 0.13, "momentum": 0.13,
        "liquidity_health": 0.10, "sentiment": 0.12,
        "innovation": 0.12, "taxonomy": 0.07, "community": 0.05,
    })
    categories: Dict[str, Dict[str, float]] = Field(default_factory=lambda: {
        "Meme": {"security": 0.25, "trend": 0.15, "momentum": 0.18,
                 "liquidity_health": 0.12, "sentiment": 0.12,
                 "innovation": 0.05, "taxonomy": 0.08, "community": 0.05},
        # 注意：历史代码 RWA/AI 权重和实为 1.15/1.10（笔误）。加权器按 active
        # 归一化故未暴露；此处按原相对比例归一至和=1（设计契约：权重和恒 1）。
        "RWA": {"security": 0.33, "trend": 0.10, "momentum": 0.07,
                "liquidity_health": 0.09, "sentiment": 0.09,
                "innovation": 0.19, "taxonomy": 0.09, "community": 0.04},
        "AI": {"security": 0.30, "trend": 0.11, "momentum": 0.07,
               "liquidity_health": 0.09, "sentiment": 0.11,
               "innovation": 0.23, "taxonomy": 0.05, "community": 0.04},
    })

    @model_validator(mode="after")
    def _sums_to_one(self):
        for name, ws in [("default", self.default), *self.categories.items()]:
            if abs(sum(ws.values()) - 1.0) > 1e-9:
                raise ValueError(f"权重和必须为 1.0（{name}: {sum(ws.values())}）")
        return self

    def for_category(self, category: str) -> Dict[str, float]:
        return dict(self.categories.get(category) or self.default)


# ---------------------------------------------------------------------------
# 类别识别（taxonomy.py）
# ---------------------------------------------------------------------------
class TaxonomyConfig(BaseModel):
    narratives: Dict[str, List[str]] = Field(default_factory=lambda: {
        "RWA": ["rwa", "realworld", "stock", "equity", "treasury", "gold", "美股", "股票"],
        "AI": ["ai", "agent", "gpt", "neural", "mind", "bot", "智能体", "人工"],
        "DePIN": ["depin", "infra", "node", "wireless", "compute", "基建"],
        "GameFi": ["game", "meta", "play", "nft", "pixel", "游戏"],
        "DeFi": ["swap", "farm", "yield", "lend", "vault", "dex", "流动性"],
        "Meme": ["pepe", "doge", "cat", "inu", "moon", "chad", "wojak", "cashcat",
                 "shiba", "floki", "elon", "马斯克", "牛", "bull", "龙", "dragon",
                 "狗", "dog", "猫", "蛙", "frog", "兔", "猪", "蛇", "马", "虎",
                 "羊", "猴", "鼠", "熊", "bear", "柴", "熊猫", "panda",
                 "蟹", "鱼", "鸟", "鸡"],
        "Infrastructure": ["bridge", "layer", "rollup", "chain", "orbit", "跨链"],
    })
    clarity: Dict[str, float] = Field(default_factory=lambda: {
        "RWA": 9.0, "AI": 8.5, "DePIN": 8.0, "Infrastructure": 8.5,
        "DeFi": 7.5, "GameFi": 6.5, "Meme": 5.0, "Uncategorized": 3.0,
    })
    innovation_base: Dict[str, float] = Field(default_factory=lambda: {
        "RWA": 8.0, "AI": 8.0, "DePIN": 7.5, "Infrastructure": 8.5,
        "DeFi": 7.0, "GameFi": 6.5, "Meme": 4.0, "Uncategorized": 4.0,
    })


# ---------------------------------------------------------------------------
# 数据源端点（sources/adapters 覆盖，缺省回落代码常量）
# ---------------------------------------------------------------------------
class SourceConfig(BaseModel):
    dexscreener_base: Optional[str] = None
    goplus_base: Optional[str] = "https://api.gopluslabs.io/api/v1"
    rpc: Dict[str, str] = Field(default_factory=dict)   # chain -> rpc url（可选覆盖）


# ---------------------------------------------------------------------------
# 聚合配置
# ---------------------------------------------------------------------------
class AnalysisConfig(BaseModel):
    engine_version: str = ENGINE_VERSION
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
    decision: DecisionConfig = Field(default_factory=DecisionConfig)
    security: SecurityPolicy = Field(default_factory=SecurityPolicy)
    market: MarketConfig = Field(default_factory=MarketConfig)
    taxonomy: TaxonomyConfig = Field(default_factory=TaxonomyConfig)
    sources: SourceConfig = Field(default_factory=SourceConfig)
    enabled_dims: List[str] = Field(default_factory=list)  # 空 = 全部启用

    @field_validator("enabled_dims")
    @classmethod
    def _known_dims(cls, v: List[str]):
        allowed = {"security", "trend", "momentum", "liquidity_health",
                   "sentiment", "innovation", "taxonomy", "community"}
        unknown = set(v) - allowed
        if unknown:
            raise ValueError(f"未知维度: {sorted(unknown)}")
        return v

    # ---- 工厂 ----
    @classmethod
    def load(cls, config: Optional[Any] = None) -> "AnalysisConfig":
        """合并顺序：内嵌默认 <- 字典/路径 YAML（后写优先覆盖前者）。"""
        merged: Dict[str, Any] = dict(_defaults_dump())
        if isinstance(config, AnalysisConfig):
            return config
        if isinstance(config, (dict, str, os.PathLike)) and config:
            data = _load_mapping(config)
            _deep_merge(merged, data)
        cfg = cls.model_validate(merged)
        if not cfg.sources.goplus_base:
            cfg.sources.goplus_base = "https://api.gopluslabs.io/api/v1"
        return cfg

    def weights_for(self, category: str) -> Dict[str, float]:
        return self.weights.for_category(category)


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------
def _defaults_dump() -> Dict[str, Any]:
    """内嵌默认 = 现值，作为最底层兜底。"""
    return AnalysisConfig(weights=WeightsConfig()).model_dump(exclude_none=True)


def _load_mapping(config: Any) -> Dict[str, Any]:
    if isinstance(config, dict):
        return config
    path = os.fspath(config)
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v


def weights_for_category(category: str, cfg: Optional[AnalysisConfig] = None) -> Dict[str, float]:
    """兼容入口：category 权重策略优先，否则默认；cfg 未提供时回落内置默认。"""
    if cfg is not None:
        return cfg.weights_for(category)
    return dict(WeightsConfig().for_category(category))
