# 数字货币量化投研平台

> **项目定位**: 数字货币市场研究、分析和投资机会发现的完整量化投研平台
> 
> **核心能力**: 多源数据采集 → 因子分析 → 回测验证 → 监控预警

---

## 项目简介

本项目构建了完整的数字货币量化投研体系，包含：

- **数据采集层**: 10+ 个API数据源自动采集，每日定时运行
- **因子分析层**: 16个量化因子计算、归一化、评分系统
- **回测框架**: 适配数字货币市场的回测引擎（UTC 00:00调仓）
- **监控系统**: 鲸鱼交易监控、多币种对比分析
- **研究报告**: 自动生成HTML交互式报告

---

## 核心功能

### 1. 数据采集系统 ✅

| 数据源 | 内容 | 采集频率 | 状态 |
|--------|------|----------|------|
| CoinGecko | 价格、市值、交易量 | 每日 | ✅ 运行中 |
| CoinGlass | 资金费率、持仓量 | 每日 | ✅ 运行中 |
| DefiLlama | TVL、稳定币数据 | 每日 | ✅ 运行中 |
| GitHub | 开发活跃度 | 每日 | ✅ 运行中 |
| Reddit | 社区情绪 | 每日 | ✅ 运行中 |

**核心文件**:
- `scripts/data_collection/daily_collector.py` - 主采集器
- `src/data/validation.py` - 数据校验模块
- `scripts/check_collection_status.py` - 健康检查

**定时任务**: 每日 UTC 00:05 (北京时间 08:05)

### 2. 因子分析系统 ✅

**16个量化因子**:

| 类别 | 因子 | 数据源 |
|------|------|--------|
| 衍生品 | funding_rate, open_interest | CoinGlass |
| 链上 | tvl_change_7d, stablecoin_flow | DefiLlama |
| 开发 | github_commits, github_stars | GitHub |
| 社交 | reddit_mentions, reddit_sentiment | Reddit |
| 市场 | price_momentum_7d/30d, volume_ratio | CoinGecko |
| 其他 | btc_dominance, exchange_flow, whale_activity | 混合 |

**核心文件**:
- `src/factors/engine.py` - 因子计算引擎
- `src/factors/normalization.py` - 归一化管道
- `src/analysis/scorer.py` - 7维度评分系统

### 3. 回测框架 ✅

**特点**:
- UTC 00:00 调仓（适应加密货币24/7交易）
- 可配置频率: daily / weekly
- 手续费模型: 默认 0.1%
- 策略: 单向做多 Top 20%

**核心文件**:
- `scripts/analysis/backtest_simple.py`
- 输出: HTML报告（收益曲线、回撤图）

### 4. 可视化系统 ✅

**核心文件**:
- `scripts/analysis/visualize_factors.py`
- 输出: `reports/figures/*.html`
  - 因子趋势图
  - 相关性热力图
  - 分布图

### 5. 鲸鱼监控 ✅

**功能**:
- WebSocket 优先 + REST 轮询备用
- BTC ≥ 100 BTC, ETH ≥ 1000 ETH
- 10分钟检查间隔（可配置）
- CSV 输出: `data/raw/whale_alerts/`

**核心文件**:
- `src/collector/whale_monitor.py`
- `scripts/data_collection/run_whale_monitor.py`

### 6. 多币种分析 ✅

**功能**:
- Top N 币种对比分析
- 顺序执行 + 进度条
- 错误隔离（单币种失败不影响整体）
- Plotly 交互式热力图

**核心文件**:
- `scripts/report/generate_report.py`
- 输出: `reports/top{N}_comparison.html`

---

## 目录结构

```
claude_trade/
├── config/                     # 配置文件
│   ├── settings.yaml          # 主配置（需创建）
│   └── settings.example.yaml  # 配置模板
│
├── data/                       # 数据存储
│   ├── raw/                   # 原始数据
│   │   ├── coingecko/         # 价格数据
│   │   ├── coinglass/         # 衍生品数据
│   │   ├── defillama/         # 链上数据
│   │   ├── github/            # 开发数据
│   │   ├── reddit/            # 社交数据
│   │   └── whale_alerts/      # 鲸鱼交易
│   ├── processed/             # 处理后数据
│   └── cache/                 # 缓存数据
│
├── reports/                    # 研究报告
│   └── figures/               # 可视化图表
│
├── scripts/                    # 脚本
│   ├── data_collection/       # 数据采集
│   ├── analysis/              # 分析脚本
│   ├── report/                # 报告生成
│   └── scoring/               # 评分脚本
│
├── src/                        # 核心模块
│   ├── api/                   # API客户端 (5个)
│   ├── analysis/              # 分析模块
│   ├── factors/               # 因子系统
│   ├── collector/             # 采集器
│   ├── report/                # 报告生成
│   ├── data/                  # 数据处理
│   ├── research/              # Alpha研究
│   └── utils/                 # 工具函数
│
├── tests/                      # 测试（240+ 个，含 src/research 新增 91 个）
│   ├── conftest.py            # 共享fixtures
│   ├── analysis/              # 分析测试
│   ├── data_collection/       # 采集测试
│   ├── report/                # 报告测试
│   └── research/              # Alpha 研究模块测试（新增）
│
├── docs/                       # 文档
│   └── superpowers/           # 设计规范
│
└── logs/                       # 日志
    ├── collector.log          # 采集日志
    └── cron.log               # 定时任务日志
```

---

## 快速开始

### 1. 安装依赖

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置 API

```bash
cp config/settings.example.yaml config/settings.yaml
# 编辑 settings.yaml 填入 API 密钥
```

### 3. 检查数据采集状态

```bash
python scripts/check_collection_status.py
```

### 4. 生成报告

```bash
# 单币种分析
python scripts/report/generate_report.py --coin bitcoin

# Top 50 币种对比
python scripts/report/generate_report.py --top-n 50
```

### 5. 可视化因子

```bash
python scripts/analysis/visualize_factors.py --days 30
```

---

## 测试

```bash
# 运行所有测试
pytest tests/

# 测试覆盖率
pytest --cov=src tests/
```

**测试统计**: 240+ 个测试用例（含 `src/research/` 新增 91 个）

---

## 定时任务

```bash
# 查看当前配置
crontab -l

# 输出示例：
# 5 0 * * * cd /home/ubuntu/project/claude_trade && python3 scripts/data_collection/daily_collector.py
```

---

## 数据积累进度

| 里程碑 | 目标日期 | 状态 |
|--------|----------|------|
| Day 0 数据入库 | 2026-06-05 | ✅ 完成 |
| Day 30 因子分析可用 | 2026-07-05 | ✅ 完成 |
| Day 90 回测有样本 | 2026-09-05 | ⏳ 待积累（数据曾断档 8 周，已于 2026-08-25 恢复采集） |
| Day 252 Alpha研究就绪 | 2027-02-15 | ⏳ 待积累 |

---

## 技术栈

- **语言**: Python 3.9+
- **数据处理**: pandas, pyarrow (Parquet)
- **可视化**: Plotly (交互式HTML)
- **测试**: pytest, pytest-mock

---

## 项目统计

- **代码行数**: ~14,000 行
- **测试用例**: 205 个
- **数据源**: 10+ 个
- **量化因子**: 16 个
- **评分维度**: 7 个

---

## 注意事项

- API 密钥等敏感信息请勿提交到 Git
- 数据文件已通过 .gitignore 排除（原始数据每日由服务器 `163.61.30.46` 采集，本地需 scp 拉取到 `data/raw_server/` 或读取 `data/reports/daily_scan/`）
- 建议先在测试网验证策略
- 量化投资有风险，请谨慎决策

## 测试说明（补充）

- `src/research/`（最大模块，17 个文件）此前无测试覆盖，现已补充 `tests/research/` 共 **91 个测试用例**，覆盖：因子判别、有效因子数、层级权重、分类、冗余检测、漂移、稳定性、缺失率、相关性、覆盖率、退役建议、健康看板、就绪度评估、生命周期、数据积累规划、因子排名、DuckDB 研究库及整包导入冒烟测试。
- 运行测试需安装项目依赖（至少 `pytest scipy pandas numpy duckdb requests pydantic pyyaml`）。专用分析环境位于 `C:/Users/P52S/.workbuddy-ai/binaries/python/envs/default`。
- 看板相关脚本（`scripts/analysis/build_dashboard.py` 等）依赖 `data/reports/daily_scan/` 与 `data/raw_server/` 的真实产物，仅在有数据后生成 `reports/crypto_dashboard.html` 等看板。
