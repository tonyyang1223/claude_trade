# Scorer拆分设计方案

**日期**: 2026-05-28
**状态**: 设计阶段 (不实施)
**优先级**: P2 (中期重构)

---

## 1. 当前问题分析

### 1.1 架构问题

| 问题 | 影响 | 严重度 |
|------|------|--------|
| 神对象 | 684行, 22方法, 难以维护 | HIGH |
| 过度耦合 | 数据获取、评分、权重混在一起 | HIGH |
| 职责不清 | 一个类做太多事 | MEDIUM |
| 难以测试 | 方法互相依赖 | MEDIUM |

### 1.2 当前职责

`Scorer` 类当前承担以下职责：

1. **数据获取** (11个方法)
   - `_get_market_data()` - 市场数据
   - `_get_technical_indicators()` - 技术指标
   - `_get_onchain_data()` - 链上数据
   - `_get_sentiment_data()` - 情绪数据
   - `_get_github_data()` - GitHub活动
   - `_get_social_data()` - 社交数据
   - `_get_risk_data()` - 风险数据
   - `_get_funding_rate()` - 资金费率 (Phase 1)
   - `_get_open_interest()` - 持仓量 (Phase 1)
   - `_get_stablecoin_flow()` - 稳定币流向 (Phase 1)
   - `_get_tvl()` - TVL数据 (Phase 1)

2. **评分计算** (7个方法)
   - `_score_market()` - 市场评分
   - `_score_technical()` - 技术评分
   - `_score_sentiment()` - 情绪评分
   - `_score_github()` - GitHub评分
   - `_score_social()` - 社交评分
   - `_score_risk()` - 风险评分
   - `calculate_weighted_score()` - 加权总分

3. **结果生成** (4个方法)
   - `generate_rating()` - 生成评级
   - `generate_recommendation()` - 生成建议
   - `determine_risk_level()` - 确定风险等级
   - `score_project()` - 主入口

---

## 2. 拆分设计方案

### 2.1 新架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Scoring Pipeline                             │
│  src/scoring/pipeline.py                                            │
│  - orchestrates the scoring process                                 │
│  - coordinates data collection and scoring                          │
└─────────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
┌─────────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│  Data Collectors     │ │  Factor Scorers │ │  Score Aggregator   │
│  src/scoring/data/  │ │ src/scoring/    │ │ src/scoring/        │
│                     │ │ factors/        │ │ aggregator.py       │
│  - MarketCollector  │ │                │ │                     │
│  - TechnicalCollector│ │ - MarketScorer │ │ - weighted_average  │
│  - OnchainCollector │ │ - TechScorer   │ │ - rating_generator  │
│  - SentimentCollector│ │ - OnchainScorer│ │ - recommendation    │
│  - GithubCollector  │ │ - SentimentScorer│                     │
│  - SocialCollector  │ │ - GithubScorer │ │                     │
│  - RiskCollector     │ │ - SocialScorer │ │                     │
│  - FundingCollector │ │ - RiskScorer   │ │                     │
│  - OICollector      │ │                │ │                     │
│  - StablecoinCollector│────────────────│──────────────────────│
│  - TVLCollector     │ │                │                      │
└─────────────────────┘ └─────────────────┘ └─────────────────────┘
```

### 2.2 目录结构

```
src/
├── scoring/
│   ├── __init__.py
│   ├── pipeline.py          # ScoringPipeline 主类
│   ├── aggregator.py        # ScoreAggregator
│   ├── data/
│   │   ├── __init__.py
│   │   ├── base.py          # BaseCollector 基类
│   │   ├── market.py        # MarketCollector
│   │   ├── technical.py     # TechnicalCollector
│   │   ├── onchain.py       # OnchainCollector
│   │   ├── sentiment.py    # SentimentCollector
│   │   ├── github.py        # GithubCollector
│   │   ├── social.py        # SocialCollector
│   │   ├── risk.py          # RiskCollector
│   │   ├── funding.py       # FundingCollector
│   │   ├── open_interest.py # OICollector
│   │   ├── stablecoin.py    # StablecoinCollector
│   │   └── tvl.py           # TVLCollector
│   └── factors/
│       ├── __init__.py
│       ├── base.py          # BaseScorer 基类
│       ├── market.py        # MarketScorer
│       ├── technical.py     # TechnicalScorer
│       ├── onchain.py       # OnchainScorer
│       ├── sentiment.py     # SentimentScorer
│       ├── github.py        # GithubScorer
│       ├── social.py        # SocialScorer
│       └── risk.py          # RiskScorer
```

### 2.3 核心类设计

#### 2.3.1 BaseCollector (数据收集器基类)

```python
# src/scoring/data/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path

class BaseCollector(ABC):
    """Base class for data collectors."""

    def __init__(self, cache_dir: Path = Path("data/cache")):
        self.cache = DataCache(cache_dir)

    @abstractmethod
    def collect(self, coin_id: str) -> Optional[Dict[str, Any]]:
        """Collect data for a coin."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Collector name for identification."""
        pass
```

#### 2.3.2 BaseScorer (评分器基类)

```python
# src/scoring/factors/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseScorer(ABC):
    """Base class for factor scorers."""

    @abstractmethod
    def score(self, data: Optional[Dict[str, Any]]) -> int:
        """Calculate score from data. Returns score (1-5)."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Scorer name for identification."""
        pass

    @property
    @abstractmethod
    def weight(self) -> float:
        """Default weight for this factor."""
        pass
```

#### 2.3.3 ScoreAggregator (分数聚合器)

```python
# src/scoring/aggregator.py
from typing import Dict
from src.data.models import ProjectScore

class ScoreAggregator:
    """Aggregates factor scores into final project score."""

    def __init__(self, weights: Dict[str, float]):
        self.weights = weights

    def aggregate(self, scores: Dict[str, int], coin_info: Dict) -> ProjectScore:
        """Aggregate scores into ProjectScore."""
        total_score = self._calculate_weighted(scores)
        rating = self._generate_rating(total_score)
        recommendation = self._generate_recommendation(rating)
        risk_level = self._determine_risk_level(rating)
        factor_contributions = self._calculate_contributions(scores)

        return ProjectScore(
            coin_id=coin_info['id'],
            coin_name=coin_info['name'],
            symbol=coin_info['symbol'],
            # ... all scores
            total_score=total_score,
            rating=rating,
            recommendation=recommendation,
            risk_level=risk_level,
            factor_contributions=factor_contributions
        )
```

#### 2.3.4 ScoringPipeline (主入口)

```python
# src/scoring/pipeline.py
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

class ScoringPipeline:
    """Main scoring pipeline orchestrator."""

    def __init__(
        self,
        collectors: List[BaseCollector],
        scorers: List[BaseScorer],
        aggregator: ScoreAggregator,
        max_workers: int = 5
    ):
        self.collectors = {c.name: c for c in collectors}
        self.scorers = {s.name: s for s in scorers}
        self.aggregator = aggregator
        self.max_workers = max_workers

    def score_project(self, coin_id: str) -> ProjectScore:
        """Score a project."""
        # 1. Collect data in parallel
        collected_data = self._collect_all(coin_id)

        # 2. Score each factor
        scores = {name: scorer.score(collected_data.get(name))
                  for name, scorer in self.scorers.items()}

        # 3. Aggregate into final score
        coin_info = self._extract_coin_info(collected_data, coin_id)
        return self.aggregator.aggregate(scores, coin_info)

    def _collect_all(self, coin_id: str) -> Dict[str, any]:
        """Collect data from all collectors in parallel."""
        # ThreadPoolExecutor for parallel collection
        ...
```

---

## 3. 迁移策略

| 阶段 | 内容 | 时间 |
|------|------|------|
| Phase 1 | 创建目录结构和基类 | 1天 |
| Phase 2 | 迁移数据收集器 (11个) | 2天 |
| Phase 3 | 迁移评分器 (7个) | 1天 |
| Phase 4 | 实现Pipeline和Aggregator | 1天 |
| Phase 5 | 集成测试和旧代码删除 | 1天 |

### 向后兼容

迁移期间保持 `Scorer` 类作为门面(Facade)，内部委托给新Pipeline。

---

## 4. 收益

| 收益 | 说明 |
|------|------|
| 可测试性 | 每个Collector/Scorer可独立测试 |
| 可扩展性 | 新增数据源只需添加Collector |
| 可维护性 | 单一职责，代码清晰 |
| 性能 | 并行数据收集提升速度 |

---

**设计完成日期**: 2026-05-28
**建议实施时间**: Phase 2完成后 (预估3-5天)
