# 数字货币量化投研平台实施设计

> **设计日期**: 2026-06-02
> **架构方案**: 模块化分层架构
> **执行策略**: 按优先级顺序执行（P0 → P1 → P2）

---

## 一、设计决策总结

### 1.1 执行优先级
- **阶段1（P0）**: 数据采集自动化 + 单元测试
- **阶段2（P1）**: 因子可视化 + 回测框架
- **阶段3（P2）**: 鲸鱼监控 + 多币种分析

### 1.2 关键决策
| 模块 | 决策 | 原因 |
|------|------|------|
| 数据采集 | 本地cron定时任务 | 开发阶段便于调试，零成本 |
| 单元测试 | 全面测试（≥70%覆盖率） | 量化系统精度要求高，边界情况易隐藏bug |
| 可视化 | HTML交互式（Plotly） | 可缩放筛选，便于深度分析 |
| 回测策略 | 单向做多Top 20% | 原型阶段验证核心逻辑，适用性广 |
| 鲸鱼监控 | 仅日志记录+CSV | P2任务保持简单，避免外部依赖 |
| 多币种分析 | 顺序执行+进度条 | 避免API速率限制，稳定性高 |

---

## 二、架构设计

### 2.1 模块化分层架构图

```
┌─────────────────────────────────────────────┐
│                 CLI Scripts                  │
│  daily_collector.py | visualize_factors.py  │
│  backtest_simple.py | whale_monitor.py      │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│              Core Modules                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Collector│ │ Analysis │ │ Backtest │   │
│  │ (采集层)  │ │ (分析层)  │ │ (回测层)  │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘   │
│       │            │            │          │
│  ┌────▼────────────▼────────────▼─────┐    │
│  │         Factor Engine              │    │
│  │  (因子计算 + 归一化 + 存储)         │    │
│  └────────────────┬───────────────────┘    │
│                   │                         │
│  ┌────────────────▼───────────────────┐    │
│  │         Data Store (Parquet)        │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

---

## 三、阶段1：数据采集自动化 + 单元测试

### 3.1 数据采集自动化

**核心文件**: `scripts/data_collection/daily_collector.py`

**类设计**:
```python
class DailyCollector:
    """每日数据采集器"""

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.clients = {
            'coingecko': CoinGeckoClient(config),
            'coinglass': CoinGlassClient(config),
            'defillama': DefiLlamaClient(config),
            'reddit': RedditClient(config),
            'github': GitHubClient(config)
        }
        self.raw_dir = Path("data/raw")
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.logger = self._setup_logging()

    def collect_all(self) -> Dict[str, bool]:
        """采集所有数据源，返回成功/失败状态"""
        results = {}
        for name, client in self.clients.items():
            data = self.collect_with_retry(name, client.fetch_data)
            if data:
                self._save_parquet(name, f"{self.today}.parquet", data)
                results[name] = True
            else:
                results[name] = False
        return results

    def collect_with_retry(self, name: str, func: Callable, **kwargs) -> Any:
        """带重试机制的采集（最多3次，指数退避）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                data = func(**kwargs)
                self.logger.info(f"{name}: success")
                return data
            except Exception as e:
                self.logger.warning(f"{name} attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 1s, 2s, 4s
        self.logger.error(f"{name}: all retries exhausted")
        return None

    def _save_parquet(self, source: str, filename: str, data: dict):
        """保存为日期分区Parquet文件"""
        dir_path = self.raw_dir / source
        dir_path.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([data]).to_parquet(dir_path / filename)
```

**数据存储结构**:
```
data/raw/
├── coingecko/
│   └── 2026-06-02.parquet
├── coinglass/
│   └── 2026-06-02.parquet
├── defillama/
│   └── 2026-06-02.parquet
├── reddit/
│   └── 2026-06-02.parquet
└── github/
    └── 2026-06-02.parquet
```

**错误处理**:
- API失败: 重试3次（指数退避），记录失败日志
- 数据验证: 检查关键字段，异常数据标记但不中断
- 部分失败: 继续采集其他源，最终报告状态

**日志输出示例**:
```
logs/collector.log
2026-06-02 08:00:01 - INFO - coingecko_btc: success (1.2s)
2026-06-02 08:00:08 - WARNING - reddit_mentions attempt 1 failed: 429
2026-06-02 08:00:12 - INFO - reddit_mentions: success (retry 2)
2026-06-02 08:00:20 - INFO - Daily collection completed: 5/5 sources successful
```

**Cron配置**:
```bash
# 编辑 crontab
crontab -e

# 添加每日8点执行
0 8 * * * cd /home/ubuntu/project/claude_trade && /usr/bin/python3 scripts/data_collection/daily_collector.py >> logs/cron.log 2>&1
```

---

### 3.2 单元测试设计

**测试文件结构**:
```
tests/
├── analysis/
│   ├── test_factor_engine.py      # 因子计算测试
│   ├── test_normalization.py      # 归一化管道测试
│   └── test_scorer.py             # 评分系统测试
├── data_collection/
│   └── test_daily_collector.py    # 数据采集测试
└── conftest.py                    # 共享fixtures
```

**测试覆盖矩阵**:
| 模块 | 正常路径 | 边界情况 | 异常处理 |
|------|---------|---------|---------|
| FactorEngine | 多因子计算 | 空数据、单一因子 | 无效因子名 |
| NormalizationPipeline | MinMax/Z-score | 全相同值、NaN | 空数组 |
| Scorer | 评分生成 | 权重归一化 | 权重和≠1 |
| DailyCollector | 全源采集 | API超时 | 网络错误 |

**边界情况测试示例**:
```python
def test_normalization_all_same_values():
    """测试所有值相同时的归一化"""
    pipeline = NormalizationPipeline()
    data = pd.DataFrame({'factor_a': [5.0, 5.0, 5.0, 5.0]})
    result = pipeline.normalize(data)
    assert result['factor_a'].std() == 0
    assert all(result['factor_a'] == 0.5)

def test_normalization_with_nan():
    """测试含NaN值的归一化"""
    pipeline = NormalizationPipeline()
    data = pd.DataFrame({'factor_b': [1.0, np.nan, 3.0, 4.0]})
    result = pipeline.normalize(data)
    assert not result['factor_b'].isna().all()

def test_scorer_weight_redistribution():
    """测试缺失维度时的权重重分配"""
    scorer = Scorer()
    scores = {'market': 5, 'technical': 4, 'onchain': 4}  # 缺失4个维度
    total = scorer.calculate_weighted_score(scores)
    assert total > 0
    assert total <= 100
```

---

## 四、阶段2：因子可视化 + 回测框架

### 4.1 因子可视化

**核心文件**: `scripts/analysis/visualize_factors.py`

**类设计**:
```python
class FactorVisualizer:
    """因子可视化生成器（Plotly交互式）"""

    def __init__(self, data_path: str = "data/processed/"):
        self.data_path = Path(data_path)
        self.output_dir = Path("reports/figures/")

    def generate_all(self, days: int = 30) -> Dict[str, str]:
        """生成所有图表，返回HTML文件路径字典"""
        df = self._load_factor_data(days)

        files = {
            'trends': self.plot_factor_trends(df),
            'correlation': self.plot_correlation_heatmap(df),
            'distributions': self.plot_factor_distributions(df)
        }

        # 生成整合仪表盘
        dashboard = self._create_dashboard(files)
        files['dashboard'] = dashboard
        return files

    def plot_factor_trends(self, df: pd.DataFrame) -> str:
        """因子时间序列折线图（可缩放、筛选）"""
        fig = go.Figure()
        for col in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col],
                name=col, mode='lines+markers'
            ))
        fig.update_layout(
            title='因子历史趋势',
            xaxis_title='日期',
            yaxis_title='因子值',
            hovermode='x unified'
        )
        return self._save_html(fig, 'factor_trends.html')

    def plot_correlation_heatmap(self, df: pd.DataFrame) -> str:
        """因子相关系数热力图"""
        corr = df.corr()
        fig = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.index,
            colorscale='RdBu',
            zmid=0
        ))
        fig.update_layout(title='因子相关性矩阵')
        return self._save_html(fig, 'factor_correlation_heatmap.html')
```

**输出文件**:
```
reports/figures/
├── factor_trends.html
├── factor_correlation_heatmap.html
├── factor_distributions.html
└── factor_dashboard.html
```

**图表特性**:
| 图表 | 交互功能 | 颜色方案 |
|------|---------|---------|
| 时间序列 | 缩放、平移、图例筛选、范围选择器 | 每因子独立颜色 |
| 热力图 | 悬停显示相关系数 | 红蓝渐变（-1到1） |
| 分布图 | 悬停显示统计值 | 统一配色，透明叠加 |

---

### 4.2 回测框架

**核心文件**: `scripts/analysis/backtest_simple.py`

**类设计**:
```python
class SimpleBacktester:
    """简易回测引擎（单向做多）"""

    def __init__(self, initial_capital: float = 10000.0, fee_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate  # 0.1%手续费
        self.capital = initial_capital

    def run(self, scores: pd.DataFrame, prices: pd.DataFrame, top_pct: float = 0.2) -> BacktestResult:
        """执行回测"""
        daily_returns = []

        for date in scores.index:
            # 选择Top 20%币种
            daily_scores = scores.loc[date]
            n_positions = int(len(daily_scores) * top_pct)
            positions = daily_scores.nlargest(n_positions).index.tolist()

            # 计算当日收益
            if date in prices.index:
                daily_return = self._calculate_daily_return(
                    positions, prices.loc[date], prices.loc[date - timedelta(days=1)]
                )
                daily_returns.append(daily_return)
                self.capital *= (1 + daily_return)

        return self._generate_result(daily_returns)

    def _calculate_daily_return(self, positions: List[str], today_prices: pd.Series, yesterday_prices: pd.Series) -> float:
        """计算等权组合收益"""
        returns = []
        for coin in positions:
            if coin in today_prices and coin in yesterday_prices:
                ret = (today_prices[coin] / yesterday_prices[coin] - 1)
                returns.append(ret)

        # 扣除手续费
        avg_return = sum(returns) / len(returns) if returns else 0
        fee_cost = self.fee_rate * 2  # 买入+卖出
        return avg_return - fee_cost
```

**策略逻辑**:
```
每日收盘后：
1. 获取当日所有币种综合评分
2. 选择Top 20%币种（50币种选10个）
3. 等权分配资金（$10000 → 每币种$1000）
4. 次日开盘买入，持有1天，收盘卖出
5. 扣除0.1%手续费，计算收益
6. 更新总资金，进入下一日
```

**性能指标**:
- 累计收益率 = (最终资金 / 初始资金) - 1
- 年化收益率 = 累计收益率 × (365 / 交易天数)
- 夏普比率 = (日均收益率 - 无风险利率) / 日收益率标准差 × √365
- 最大回撤 = max(峰值到谷值的跌幅)

---

## 五、阶段3：鲸鱼监控 + 多币种分析

### 5.1 鲸鱼交易监控

**核心文件**: `scripts/data_collection/whale_monitor.py`

**类设计**:
```python
class WhaleMonitor:
    """鲸鱼交易监控器"""

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.thresholds = {'btc': 100, 'eth': 1000}
        self.check_interval = 600  # 10分钟
        self.output_dir = Path("data/raw/whale_alerts/")
        self.logger = self._setup_logging()

    def start_monitoring(self):
        """启动持续监控循环"""
        while True:
            for chain in ['BTC', 'ETH']:
                transactions = self.check_large_transactions(chain)
                if transactions:
                    self.logger.info(f"发现{len(transactions)}笔{chain}大额交易")
                    self._save_to_csv(transactions)
            time.sleep(self.check_interval)

    def check_large_transactions(self, chain: str) -> List[WhaleTransaction]:
        """检查指定链的大额交易"""
        txs = self._fetch_transactions(chain)
        large_txs = []
        for tx in txs:
            if tx['amount'] >= self.thresholds[chain.lower()]:
                large_txs.append(WhaleTransaction(
                    timestamp=tx['timestamp'],
                    chain=chain,
                    tx_hash=tx['hash'],
                    amount_usd=tx['amount_usd'],
                    amount_native=tx['amount']
                ))
        return large_txs
```

**数据源**:
- BTC: Blockchain.com API（免费）
- ETH: Etherscan API（需API密钥）

**CSV输出格式**:
```csv
timestamp,chain,tx_hash,amount_usd,amount_native,from_address,to_address,type
2026-06-02T08:15:32,BTC,abc123...,$5,200,000,100.5,3FZbgi...,1A1zP1...,transfer
```

**配置扩展**:
```yaml
whale_monitor:
  enabled: true
  thresholds:
    btc: 100
    eth: 1000
  check_interval: 600
  etherscan_api_key: "YOUR_API_KEY"
```

---

### 5.2 多币种并行分析

**核心文件**: `scripts/report/generate_report.py`（扩展）

**新增函数**:
```python
def generate_top_n_report(top_n: int = 50, output_path: str = None):
    """生成Top N币种对比报告"""

    # 1. 获取市值排名Top N
    coins = get_top_coins_by_market_cap(top_n)

    # 2. 顺序分析（配合进度条）
    results = []
    for coin in tqdm(coins, desc="分析币种", unit="coin"):
        try:
            score = analyze_single_coin(coin['id'])
            results.append(score)
        except Exception as e:
            logger.warning(f"{coin['id']} 分析失败: {e}")
            continue  # 错误隔离

    # 3. 生成报告
    report = ComparisonReport(
        projects=results,
        comparison_matrix=build_comparison_matrix(results),
        winner=results[0].coin_id,
        analysis_summary=generate_summary(results)
    )

    save_html_report(report, output_path or "reports/top50_comparison.html")
```

**报告HTML结构**:
```
=== Top 50 数字货币综合评分报告 ===

【综合排名表】
| 排名 | 名称 | 评分 | 评级 | 建议 |
| 1    | Bitcoin | 85 | A | 建议关注 |

【各维度得分热力图】
[Plotly交互式热力图]

【推荐列表】
强烈建议关注: Bitcoin, Solana, Chainlink
```

---

## 六、里程碑与预期成果

### 6.1 时间规划
| 阶段 | 时间 | 目标 |
|------|------|------|
| Day 0 (今天) | 启动自动采集 | 首次数据入库 |
| Day 30 | 因子稳定性分析首次可用 | 可视化图表有参考价值 |
| Day 90 | 回测框架有足够样本 | 初步验证因子有效性 |
| Day 252 | Alpha研究就绪 | 达到最低历史深度要求 |

### 6.2 交付物清单
**阶段1**:
- `scripts/data_collection/daily_collector.py`
- `tests/analysis/test_factor_engine.py`
- `tests/analysis/test_normalization.py`
- 测试覆盖率≥70%

**阶段2**:
- `scripts/analysis/visualize_factors.py`
- `scripts/analysis/backtest_simple.py`
- `reports/figures/*.html`

**阶段3**:
- `scripts/data_collection/whale_monitor.py`
- 扩展 `scripts/report/generate_report.py`
- `data/raw/whale_alerts/*.csv`

---

## 七、风险与缓解策略

| 风险 | 缓解策略 |
|------|---------|
| API速率限制 | 顺序执行+指数退避重试 |
| 数据缺失 | 权重自动重分配，继续计算 |
| 测试数据不足 | Mock数据+模拟场景 |
| 可视化性能 | Plotly大数据集降采样 |

---

**设计状态**: 已完成用户确认
**下一步**: 调用 writing-plans skill 生成详细实施计划