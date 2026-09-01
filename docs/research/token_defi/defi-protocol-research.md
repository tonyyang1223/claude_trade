# DeFi 协议研究方法论（defi-protocol-research）

> 适用：研究某个 DeFi 协议（DEX / 借贷 / LSD / 衍生品 / 收益聚合）。
> 代码入口：`src/research/token_defi.py` 的 `analyze_protocol()` / `compare_protocols()`；
> 报告：`scripts/research/token_defi_report.py --compare uniswap:uniswap curve-dex:curve-dao-token`。

## 0. 核心指标（所有协议必看）

| 指标 | 含义 | 怎么用 |
|---|---|---|
| **TVL** | 锁仓总价值 | 规模与信任度；但高 TVL ≠ 好，要看质量 |
| **TVL 趋势** | 24h / 7d 变化 | 流入 = 增长，流出 = 信任流失 |
| **费用（Fees）** | 协议收取的总费用 | 真实需求的温度计 |
| **协议收入（Revenue）** | 费用中归属代币持有人的部分 | 很多协议 revenue = 0（费用全给 LP） |
| **P/S ≈ FDV / 年化费用** | 估值便宜度 | 同赛道横比，**口径要一致** |
| **资本效率 = 年化费用 / TVL** | 周转效率 | DEX 之间尤其可比 |

### 本项目可用的字段

`DefiLlamaClient.get_protocol_tvl(slug)` → `tvl` / `tvl_change_24h` / `tvl_change_7d` / `chain_breakdown`

`DefiLlamaClient.get_protocol_fees(slug)` → `fees_24h` / `fees_7d` / `fees_30d` /
`fees_annualized` / `fees_all_time` / `included_slugs`

> **注意（踩坑记录）**：`/protocol/{slug}` 端点**不返回 fees/revenue**，
> 且 Uniswap 在 DefiLlama 里只有 `uniswap-v1`~`v4` 子项、没有父协议费用行。
> `get_protocol_fees()` 已内置 `-v<N>` 子版本聚合（见 `included_slugs`），
> 对比时务必用聚合值，否则会严重低估。

## 1. 赛道模板（按类别套用）

- **DEX（Uniswap / Curve / PancakeSwap）**
  - 看：交易量、资本效率（费用/TVL）、LP 手续费 APR、**手续费开关（fee switch）是否开启**。
  - 护城河：流动性深度、长尾资产覆盖、ve 模型锁仓。
- **借贷（Aave / Compound / Morpho）**
  - 看：TVL、利用率（utilization）、坏账率（bad debt）、清算机制、隔离市场。
  - 风险：抵押品质量、预言机、清算连锁（参考 2022 多家暴雷）。
- **LSD（Lido / Rocket Pool）**
  - 看：质押量、市占率、脱锚历史、节点运营商去中心化、提款队列。
  - 风险：中心化（单一协议占比过高引去中心化争议）。
- **衍生品（dYdX / GMX / Hyperliquid）**
  - 看：未平仓量 OI、交易量、手续费、费用/TVL。
  - 风险：资金费率、预言机滑点；本项目 `src/api/coinglass.py` 可提供资金费率。
- **收益聚合（Yearn / Convex）**
  - 看：策略收益来源是否可持续、TVL 集中度、可组合性风险。

## 2. 安全（DeFi 生命线）

- **审计**：审计机构（Trail of Bits / OpenZeppelin / CertiK 等）与最近一次时间。
  > 本项目客户端目前**不返回审计字段**，需人工查证后写入研究结论，不要留空也不要编造。
- **TVL 集中度**：看 `chain_breakdown`，是否集中在单一链 / 桥（跨链桥是历史重灾区）。
- **权限 / 管理**：admin key 是否多签、是否有 timelock、能否无条件提取资金。
- **历史 exploit**：搜 Rekt Database / 官方 post-mortem，看是否赔付、是否重复犯错。
- **预言机**：喂价来源（Chainlink？自建？）决定操纵风险。

## 3. 治理

- **代币分布**：团队 / VC / 社区占比；前几地址集中度。
- **提案活跃度**：近期提案数、投票参与率、是否实质去中心化。
- **金库（Treasury）**：能否支撑长期开发、熊市存活。

## 4. 可比与护城河

- 同赛道按**量化指标排序**（TVL / 费用 / P/S / 资本效率），写清排序依据。
- 护城河来源：网络效应（流动性）、不可分叉的数据 / 品牌、代币激励飞轮、合规先发。

### 对比实例（本次实测数据，2026-08-31）

| 指标 | Uniswap | Curve |
|---|---|---|
| TVL | $3.46B | $1.32B |
| 年化费用（聚合 v1–v4） | $838.5M | $60.3M |
| 资本效率（费用/TVL） | 24.2% | 4.6% |
| P/S（FDV 口径） | ≈5.3× | ≈12.0× |
| 代币协议收入 | ≈$0（费用开关未开） | veCRV 锁仓者分成 |

**关键洞察**：Uniswap 费用规模与资本效率全面领先，但其代币 UNI **不捕获协议收入**；
Curve 增长更慢却有向 veCRV 的现金流。因此"Uniswap P/S 更低 = 更便宜"是**有口径局限**的，
真正决定 UNI 估值重估的单一变量是**费用开关是否开启**。

## 5. 输出规范

- 首屏结论：赛道 + 规模 + 收入质量 + 最大风险 + 同类位置。
- 表格：TVL / 费用 / P/S / 资本效率 / 覆盖链，标来源 + 时点。
- 深度版 HTML：TVL 与费用对比柱状图 + P/S 对比图（报告脚本已内置）。
- 不写买卖建议；附免责声明（模板已内置）。
