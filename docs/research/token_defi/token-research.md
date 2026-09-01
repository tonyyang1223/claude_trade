# 代币研究方法论（token-research）

> 适用：研究某个代币（BTC / ETH / 山寨币 / 协议治理币）。
> 代码入口：`src/research/token_defi.py` 的 `TokenDefiResearcher.analyze_token()`；
> 报告：`scripts/research/token_defi_report.py --token <coin_id>`。

## 0. 研究分层

- **快速初探**：价格 / 市值 / FDV / 24h 涨跌 / 流通率 / 赛道 / 一句话定位。
- **深度研究**：基本面 + 代币经济 + 估值 + 链上 + 风险，产出 HTML 报告。

## 1. 基本面（项目本身）

| 维度 | 看什么 | 去哪看 |
|---|---|---|
| 定位 | 解决什么问题、对标谁 | 官网 / 白皮书 / CoinGecko categories |
| 团队 | 实名 or 匿名、过往战绩 | 官网 team、Twitter、LinkedIn |
| 融资 | 轮次 / 金额 / 参投 VC | Crunchbase、Messari、官方公告 |
| 路线图 | 交付节奏、是否跳票 | 官方 roadmap、`src/api/github.py` 提交活跃度 |
| 采用 | 活跃用户 / TVS / 集成数 | DappRadar、协议仪表板 |

> 本项目的 `src/api/github.py`、`src/analysis/github_analyzer.py` 可量化开发活跃度，
> 作为「交付节奏」的客观代理指标。

## 2. 代币经济（Tokenomics）—— 重点

- **总量结构**：`max_supply`（硬顶）vs `total_supply`（已生成）vs `circulating_supply`（流通）。
  - **流通率 = 流通 / (max or total)**。低流通率（< 20%）意味未来解锁抛压大，是核心风险信号。
- **通胀 / 通缩**：增发机制（PoS 质押释放？）vs 销毁（burn / buyback）。净通胀率要算。
- **分配与释放曲线**：
  - 团队 / 投资人 / 社区 / 国库 各占多少？
  - **解锁日历**：未来 6/12 个月释放量、线性还是 cliff？cliff 到期常伴随抛压。
  - **VC 成本价 vs 现价**：现价远低于 VC 成本 → 解锁即亏损，抛售概率低；远高于成本 → 抛压强。
- **效用（utility）**：gas / 治理 / 质押生息 / 手续费分成？效用弱 = 纯投机盘。
  - 治理型代币要额外确认：**费用开关是否开启**（未开启 = 代币零协议收入，见 DeFi 协议文档）。

### 代码可算 vs 需人工/付费源

| 项目 | 代码可算 | 说明 |
|---|---|---|
| 流通率、稀释倍数、FDV/MC | ✅ | `circulating_ratio()` / `dilution_multiple()` |
| 待解锁量、风险分档 | ✅ | `locked_supply()` / `unlock_risk_level()` |
| 逐日解锁日历、cliff 日期 | ❌ | 需 TokenUnlocks（需 key）或项目公告 |
| VC 成本价 | ❌ | 需融资公告人工核对 |

## 3. 供需与估值

- **FDV vs MC**：`FDV = 价格 × 总量`，`MC = 价格 × 流通量`。
  - 注意：`FDV/MC` 在数学上**恒等于稀释倍数**（价格是同一变量），是同一信号，不要重复计入。
- **P/S**：`P/S = FDV（或市值） / 年化协议收入`。横向比同类协议，**口径必须一致**。
- **可比估值**：同赛道按 MC / FDV / 收入排序，注明排序依据（收入、TVL、用户数），
  不写"行业领先"这类空话。
- **MVRV**：判断持有者整体盈亏，辅助估值分位（见 `onchain-metrics.md`）。

## 4. 链上指标

至少看：持有者集中度（前 N 地址占比）、交易所净流入（流入 = 抛压信号）、巨鲸动向、活跃地址趋势。
详见 [`onchain-metrics.md`](onchain-metrics.md)。

## 5. 风险清单（每条研究必点至少一类）

- **解锁抛压**：低流通率 + 近期 cliff 解锁。
- **合约 / 审计**：是否开源、被审计几家、有无历史 exploit。
- **流动性**：CEX + DEX 深度，小币在极端行情流动性枯竭。
- **中心化**：团队多签占比、可冻结 / 增发权限是否未放弃。
- **监管**：证券属性争议、所在司法辖区。
- **叙事 / 竞争**：是否赛道红海、有无更强替代。

## 6. 输出规范

- 首屏给结论（一句话定位 + 最大风险）。
- 表格列：价格 / MC / FDV / 流通率 / 24h / 赛道，**标注来源 + 时点**。
- 深度版 HTML：供应量结构环形图 + 涨跌柱状图（`scripts/research/token_defi_report.py` 已内置）。
- 不写买卖建议；涉高风险标的附免责声明（报告模板已内置）。
