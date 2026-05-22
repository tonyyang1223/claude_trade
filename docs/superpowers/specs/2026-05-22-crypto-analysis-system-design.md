# 数字货币分析系统完整设计

> **目标：** 构建完整的数字货币分析系统，支持深度分析、批量筛选、交易决策三种用途

**用途：** A（个人投资研究）+ B（批量项目筛选）+ C（量化交易支持）

**预算：** 仅使用免费API

**输出：** 完整评分报告（HTML/PDF），包含详细数据来源、历史趋势图表、对比分析、投资建议

---

## 一、整体架构

```
src/
├── api/                          # ✅ 已完成
│   ├── base.py                   # API基类
│   ├── coingecko.py              # CoinGecko客户端
│   └── coinmarketcap.py          # CoinMarketCap客户端
├── data/                         # ✅ 部分完成，需扩展
│   ├── models.py                 # 数据模型（需扩展）
│   ├── cache.py                  # 缓存系统
│   └── exporters.py              # 数据导出
├── analysis/                     # 🆕 新增
│   ├── btc_dominance.py          # BTC主导地位分析
│   ├── technical.py              # 技术指标计算
│   ├── sentiment.py              # 情绪分析
│   ├── onchain.py                # 链上分析
│   ├── github_analyzer.py        # GitHub活动分析
│   ├── scorer.py                 # 自动评分系统
│   └── comparison.py             # 项目对比引擎
├── report/                       # 🆕 新增
│   ├── generator.py              # 报告生成器
│   ├── charts.py                 # 图表生成
│   └── templates/                # HTML模板
│       └── full_report.html      # 完整报告模板
└── collector/                    # ✅ 已完成
    └── market_collector.py       # 主采集器

scripts/
├── data_collection/              # ✅ 已完成
│   └── collect_market_data.py
├── analysis/                     # 🆕 新增
│   ├── analyze_btc_dominance.py
│   ├── analyze_technical.py
│   ├── analyze_sentiment.py
│   ├── analyze_onchain.py
│   └── analyze_github.py
├── scoring/                      # 🆕 新增
│   ├── score_project.py
│   └── compare_projects.py
└── report/                       # 🆕 新增
    └── generate_report.py
```

**核心数据流：**
```
采集数据 → 分析计算 → 评分 → 对比 → 生成报告
  ↑           ↑         ↑       ↑        ↑
CoinGecko   RSI/MA   1-5分   同赛道    HTML/PDF
Binance     趋势     加权    2-3项目   图表+数据
GitHub      情绪     总分    排名      投资建议
```

---

## 二、数据模型扩展

```python
# src/data/models.py 扩展内容

class TechnicalIndicators(BaseModel):
    """技术指标数据"""
    rsi: float                           # RSI值 (0-100)
    rsi_signal: int                      # RSI信号 (1-5分)
    ma_50: float                         # 50日均线
    ma_200: float                        # 200日均线
    ma_signal: int                       # 均线信号 (1-5分)
    support_levels: List[float]          # 支撑位列表
    resistance_levels: List[float]       # 阻力位列表
    trend: str                           # 趋势方向 (up/down/sideways)
    trend_signal: int                    # 趋势信号 (1-5分)
    fibonacci_levels: Dict[str, float]   # 斐波那契回撤位
    volume_ratio: float                  # 交易量/市值比率
    volume_signal: int                   # 量价信号 (1-5分)
    timestamp: datetime

class SentimentData(BaseModel):
    """情绪分析数据"""
    google_trends_score: int             # Google搜索热度 (0-100)
    google_trends_change: float          # 搜索热度变化率
    fear_greed_index: int                # 恐惧贪婪指数 (0-100)
    social_sentiment: str                # 社交情绪 (bullish/bearish/neutral)
    sentiment_signal: int                # 情绪信号 (1-5分)
    timestamp: datetime

class OnchainData(BaseModel):
    """链上数据（免费替代方案）"""
    nupl: Optional[float]                # 未实现净利润比
    mvrv: Optional[float]                # MVRV比率
    holder_distribution: Optional[Dict]  # 持有者分布
    active_addresses: Optional[int]      # 活跃地址数
    transaction_count: Optional[int]     # 交易数量
    onchain_signal: int                  # 链上信号 (1-5分)
    timestamp: datetime

class GithubData(BaseModel):
    """GitHub活动数据"""
    repo_url: str                        # 仓库地址
    commit_count_30d: int                # 30天提交数
    contributor_count: int               # 贡献者数量
    issue_count: int                     # Issue数量
    pr_count: int                        # PR数量
    last_commit_date: datetime           # 最后提交时间
    activity_score: int                  # 活跃度评分 (1-5分)
    timestamp: datetime

class BTCDominance(BaseModel):
    """BTC主导地位数据"""
    current_dominance: float             # 当前主导地位
    trend: str                           # 趋势 (rising/falling/stable)
    market_phase: str                    # 市场阶段
    altcoin_season: bool                 # 是否山寨币季节
    recommendation: str                  # 操作建议
    timestamp: datetime

class ProjectScore(BaseModel):
    """项目综合评分"""
    coin_id: str
    coin_name: str
    symbol: str

    # 各维度评分
    market_score: int                    # 市场数据评分 (权重20%)
    technical_score: int                 # 技术指标评分 (权重15%)
    onchain_score: int                   # 链上分析评分 (权重20%)
    sentiment_score: int                 # 情绪分析评分 (权重10%)
    github_score: int                    # GitHub活跃度评分 (权重10%)
    social_score: int                    # 社交媒体评分 (权重10%)
    risk_score: int                      # 风险评估 (权重15%)

    # 综合评分
    total_score: float                   # 加权总分 (满分100)
    rating: str                          # 评级 (A+/A/B/C/D/F)

    # 投资建议
    recommendation: str                  # 投资建议
    risk_level: str                      # 风险等级 (low/medium/high)
    entry_suggestion: Optional[str]      # 入场建议

    analyzed_at: datetime

class ComparisonReport(BaseModel):
    """项目对比报告"""
    projects: List[ProjectScore]
    comparison_matrix: Dict
    winner: str
    analysis_summary: str
    created_at: datetime
```

---

## 三、各分析模块详细设计

### 3.1 BTC主导地位分析 (`src/analysis/btc_dominance.py`)

**数据源：** CoinGecko global API

**功能：**
- 获取BTC主导地位当前值和趋势
- 判断市场状态：BTC主导上升期 / 山寨币季节 / 极端山寨币季节
- 判断资金流向方向
- 输出操作建议

**判断逻辑：**
| 主导地位 | 趋势 | 市场状态 | 操作建议 |
|----------|------|----------|----------|
| >50% | 上升 | BTC主导期 | 持有BTC |
| >50% | 下降 | 资金转向山寨 | 关注山寨币 |
| 40-50% | 下降 | 山寨币季节 | 转向山寨币 |
| <40% | 下降 | 极端山寨币季节 | 警惕回调 |
| <35% | - | 历史低点 | 高风险 |

### 3.2 技术指标计算 (`src/analysis/technical.py`)

**数据源：** ccxt (Binance免费API)

**功能：**
- RSI计算（14日）与信号判断
- 50日/200日移动平均线计算
- 支撑位/阻力位识别（局部极值算法）
- 趋势判断（价格与均线关系）
- 斐波那契回撤位计算（38.2%/50%/61.8%）
- 量价关系分析（交易量/市值比率）

**RSI评分规则：**
| RSI值 | 信号 | 评分 |
|-------|------|------|
| <30 | 超卖（买入机会） | 5 |
| 30-40 | 偏弱 | 4 |
| 40-60 | 中性 | 3 |
| 60-70 | 偏强 | 2 |
| ≥70 | 超买（谨慎） | 1 |

### 3.3 情绪分析 (`src/analysis/sentiment.py`)

**数据源：**
- Google Trends（pytrends库，免费）
- Fear & Greed Index（alternative.me免费API）
- CoinGecko community_data（免费）

**功能：**
- 搜索热度趋势获取
- 恐惧贪婪指数获取（0-100）
- 社交情绪综合判断
- 输出情绪信号

**恐惧贪婪评分规则：**
| 指数值 | 情绪 | 评分 |
|--------|------|------|
| 0-25 | 极度恐惧 | 5（买入机会） |
| 25-45 | 恐惧 | 4 |
| 45-55 | 中性 | 3 |
| 55-75 | 贪婪 | 2 |
| 75-100 | 极度贪婪 | 1（风险高） |

### 3.4 链上分析 (`src/analysis/onchain.py`)

**数据源（免费）：**
- Blockchain.com API（BTC基础链上数据）
- LookIntoBitcoin（爬虫获取NUPL等）
- CryptoCompare API（部分链上指标）

**功能：**
- NUPL获取与判断
- MVRV比率获取
- 活跃地址数/交易数量
- 持有者分布
- 链上信号综合判断

**NUPL评分规则：**
| NUPL值 | 状态 | 评分 |
|--------|------|------|
| <0 | 亏损 | 5（底部信号） |
| 0-0.25 | 希望/恐惧 | 4 |
| 0.25-0.5 | 乐观 | 3 |
| 0.5-0.75 | 信念/贪婪 | 2 |
| ≥0.75 | 相信/卖出 | 1 |

**注意：** 免费数据源主要覆盖BTC，其他币种部分指标可能为None

### 3.5 GitHub分析 (`src/analysis/github_analyzer.py`)

**数据源：** GitHub API（免费，5000次/小时）

**功能：**
- 通过CoinGecko links字段获取项目GitHub地址
- 统计30天提交频率
- 统计贡献者数量
- 统计Issue/PR数量
- 计算活跃度评分

**活跃度评分规则：**
| 30天提交数 | 评分 |
|------------|------|
| ≥100 | 5 |
| 50-99 | 4 |
| 20-49 | 3 |
| 5-19 | 2 |
| <5 | 1 |

### 3.6 评分系统 (`src/analysis/scorer.py`)

**功能：**
- 接收各维度数据，按规则自动打分（1-5分）
- 按权重计算加权总分（满分100）
- 生成评级（A+/A/B/C/D/F）
- 输出投资建议和风险等级
- 支持自定义权重配置
- 缺失数据时权重自动重分配

**权重配置（可自定义）：**
```yaml
weights:
  market: 0.20
  technical: 0.15
  onchain: 0.20
  sentiment: 0.10
  github: 0.10
  social: 0.10
  risk: 0.15
```

**评级规则：**
| 总分 | 评级 |
|------|------|
| 90-100 | A+ |
| 80-89 | A |
| 70-79 | B |
| 60-69 | C |
| 50-59 | D |
| <50 | F |

**投资建议规则：**
| 评级 | 建议 | 风险等级 |
|------|------|----------|
| A+/A | 建议关注 | 低 |
| B | 可考虑 | 中 |
| C | 谨慎观望 | 中高 |
| D/F | 不推荐 | 高 |

### 3.7 项目对比 (`src/analysis/comparison.py`)

**功能：**
- 输入2-3个同赛道项目
- 生成对比矩阵（各维度得分对比）
- 计算综合排名
- 输出推荐项目和分析总结

---

## 四、报告生成模块

### 4.1 报告生成器 (`src/report/generator.py`)

**功能：**
- 接收ProjectScore和各维度详细数据
- 使用Jinja2模板渲染HTML报告
- 生成雷达图、柱状图（matplotlib/plotly）
- 支持导出HTML文件

**输出路径：**
```
data/reports/
├── bitcoin_20260522_143052.html
├── ethereum_20260522_143105.html
└── comparison_20260522_143200.html
```

### 4.2 报告结构

```
┌─────────────────────────────────────────────────────┐
│  项目名称：Bitcoin (BTC)                             │
│  分析时间：2026-05-22 14:30                          │
│  综合评分：85/100  评级：A                            │
├─────────────────────────────────────────────────────┤
│  📊 综合概览                                         │
│  ├── 总分柱状图                                     │
│  ├── 各维度雷达图                                   │
│  └── 投资建议：建议关注 / 谨慎观望 / 不推荐          │
├─────────────────────────────────────────────────────┤
│  📈 市场数据 (权重20%)                              │
│  ├── 市值排名、当前价格、交易量、流通量             │
│  └── 评分：5/5                                      │
├─────────────────────────────────────────────────────┤
│  📉 技术指标 (权重15%)                              │
│  ├── RSI、MA、趋势、支撑阻力、斐波那契               │
│  └── 评分：4/5                                      │
├─────────────────────────────────────────────────────┤
│  🔗 链上分析 (权重20%)                              │
│  ├── NUPL、活跃地址、持有者分布                      │
│  └── 评分：4/5                                      │
├─────────────────────────────────────────────────────┤
│  😊 情绪分析 (权重10%)                              │
│  ├── Google趋势、恐惧贪婪指数                        │
│  └── 评分：4/5                                      │
├─────────────────────────────────────────────────────┤
│  💻 GitHub活跃度 (权重10%)                          │
│  ├── 提交数、贡献者、Issue/PR                        │
│  └── 评分：5/5                                      │
├─────────────────────────────────────────────────────┤
│  📱 社交媒体 (权重10%)                              │
│  ├── Twitter、Reddit粉丝数                          │
│  └── 评分：5/5                                      │
├─────────────────────────────────────────────────────┤
│  ⚠️ 风险评估 (权重15%)                              │
│  ├── 流动性、波动性、解锁压力                        │
│  └── 评分：4/5                                      │
├─────────────────────────────────────────────────────┤
│  📝 分析总结                                         │
│  ├── 优势、风险、建议                                │
├─────────────────────────────────────────────────────┤
│  📚 数据来源                                         │
│  CoinGecko | Binance | Google Trends | GitHub       │
└─────────────────────────────────────────────────────┘
```

---

## 五、免费数据源汇总

| 模块 | 数据源 | 免费额度 | 备选方案 |
|------|--------|----------|----------|
| 市场数据 | CoinGecko | 50次/分钟 | CoinMarketCap |
| K线数据 | ccxt (Binance) | 无限制 | OKX/KuCoin |
| BTC主导 | CoinGecko global | 50次/分钟 | CMC global |
| 恐惧贪婪 | alternative.me | 免费 | - |
| Google趋势 | pytrends | 免费(限流) | - |
| 链上BTC | Blockchain.com | 免费 | - |
| 链上指标 | LookIntoBitcoin | 爬虫 | CryptoWatch |
| GitHub | GitHub API | 5000次/小时 | - |
| 社交粉丝 | CoinGecko | 50次/分钟 | - |

**缺失数据处理：** 使用 `Optional` 字段，权重自动重分配

---

## 六、CLI命令设计

```bash
# BTC主导地位分析
python scripts/analysis/analyze_btc_dominance.py

# 技术指标分析
python scripts/analysis/analyze_technical.py --coin bitcoin --days 200

# 情绪分析
python scripts/analysis/analyze_sentiment.py --coin bitcoin

# 链上分析
python scripts/analysis/analyze_onchain.py --coin bitcoin

# GitHub分析
python scripts/analysis/analyze_github.py --coin bitcoin

# 单项目评分
python scripts/scoring/score_project.py --coin bitcoin

# 项目对比
python scripts/scoring/compare_projects.py --coins bitcoin ethereum solana

# 生成报告
python scripts/report/generate_report.py --coin bitcoin --output html
python scripts/report/generate_report.py --coins bitcoin ethereum --compare
```

---

## 七、实施阶段与优先级

### 阶段1：技术指标分析（优先级最高）

| 模块 | 文件 |
|------|------|
| 技术指标 | `src/analysis/technical.py` |
| 数据模型 | `src/data/models.py` 扩展 |
| CLI | `scripts/analysis/analyze_technical.py` |

### 阶段2：BTC主导地位 + 情绪分析

| 模块 | 文件 |
|------|------|
| BTC主导 | `src/analysis/btc_dominance.py` |
| 情绪分析 | `src/analysis/sentiment.py` |
| 数据模型 | `src/data/models.py` 扩展 |
| CLI | `scripts/analysis/analyze_btc_dominance.py` |
| CLI | `scripts/analysis/analyze_sentiment.py` |

### 阶段3：链上分析 + GitHub分析

| 模块 | 文件 |
|------|------|
| 链上分析 | `src/analysis/onchain.py` |
| GitHub分析 | `src/analysis/github_analyzer.py` |
| 数据模型 | `src/data/models.py` 扩展 |
| CLI | `scripts/analysis/analyze_onchain.py` |
| CLI | `scripts/analysis/analyze_github.py` |

### 阶段4：评分系统 + 项目对比

| 模块 | 文件 |
|------|------|
| 评分系统 | `src/analysis/scorer.py` |
| 项目对比 | `src/analysis/comparison.py` |
| 数据模型 | `src/data/models.py` 扩展 |
| CLI | `scripts/scoring/score_project.py` |
| CLI | `scripts/scoring/compare_projects.py` |

### 阶段5：报告生成

| 模块 | 文件 |
|------|------|
| 报告生成 | `src/report/generator.py` |
| 图表 | `src/report/charts.py` |
| HTML模板 | `src/report/templates/full_report.html` |
| CLI | `scripts/report/generate_report.py` |

---

## 八、依赖库

```txt
# 已有
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0
pydantic>=2.0.0
ccxt>=4.0.0

# 新增
ta-lib>=0.4.28          # 技术指标计算
pandas-ta>=0.3.14b      # 备选技术分析
pytrends>=4.9.0         # Google Trends
PyGithub>=1.59.0        # GitHub API
jinja2>=3.1.2           # 模板渲染
matplotlib>=3.7.0       # 图表生成
plotly>=5.15.0          # 交互式图表
beautifulsoup4>=4.12.0  # 爬虫解析
lxml>=4.9.0             # HTML解析
```

---

*设计文档创建于 2026-05-22*