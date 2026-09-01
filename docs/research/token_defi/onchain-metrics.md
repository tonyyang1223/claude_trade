# 链上指标解读（onchain-metrics）

> 适用：解读链上数据（持有者分布 / 巨鲸 / 资金流向 / 估值分位）。
> 本项目相关代码：`src/analysis/onchain.py`、`src/factors/onchain.py`
> （因子层已有 `tvl_change_7d` 等链上因子）。

## 1. 估值类

- **MVRV（Market Value / Realized Value）**
  - 市值 / 已实现市值。≈1 常对应周期底部区；> 1.2~1.5 提示多数持有者浮盈、顶部风险；< 1 多数浮亏、磨底。
  - 滞后 1~2 天，适合中周期判断，不用于日内。
- **NVT（Network Value / Transactions）**
  - 市值 / 链上转账量。高 NVT = 价格相对实际使用偏贵（类似 P/E）。
  - 分链口径不同，跨链比要谨慎。

## 2. 参与者与活跃度

- **活跃地址数**：趋势比绝对值重要。上升 = 采用扩张；骤降 = 兴趣退潮。
- **新增地址 / 净新增**：用户增长质量。
- **链上交易量**：真实经济活动温度计，配合 NVT 用。

## 3. 资金流向（情绪温度计）

- **交易所净流入 / 流出**
  - 净流入（提币到 CEX）= 潜在抛压上升。
  - 净流出（从 CEX 提走自托管）= 长期持有 / 锁仓意愿，偏多。
- **稳定币流向**
  - USDT/USDC 大量进 CEX = 潜在买盘储备。
  - 稳定币离开 CEX 进 DeFi / 自托管 = 资金离场或生息。
  - 本项目：`DefiLlamaClient.get_stablecoin_flows()` / `get_chain_stablecoin_flows(chain)`
    （`src/api/defillama.py`）已封装稳定币流向。

## 4. 集中度与巨鲸

- **持有者集中度**：前 10 / 前 100 地址占比。极高 = 庄控 / 抛压集中风险。
- **巨鲸动向**：大额地址增持 / 减持、转入 CEX 行为。
  - 本项目已有 `src/collector/whale_monitor.py`（BTC ≥100、ETH ≥1000 阈值，WS 优先 + REST 备用），
    产物在 `data/raw/whale_alerts/`。
  - 识别"是谁"需 Nansen / Arkham 等标签服务（付费）。
- **休眠指标（dormant coins）**：长期不动的币突然移动 = 早期持有者松动，常是顶部信号。

## 5. 使用原则（避坑）

- **滞后性**：链上数据 1~2 天延迟，不用于日内交易。
- **口径一致**：跨链 / 跨资产比较前统一统计口径与币种。
- **多指标互证**：单一指标易误判；MVRV + 流向 + 活跃地址共振更可靠。
- **非确定性**：所有链上信号是概率，不是必然。
- **来源标注**：每条指标标来源（API / 区块浏览器）+ 数据截止时间。

## 6. 免费可得 vs 需 key

| 指标 | 免费无 key | 需 key |
|---|---|---|
| TVL 与变化 | ✅ DefiLlama | — |
| 稳定币流向 | ✅ DefiLlama | — |
| 巨鲸交易流 | ✅（本项目 whale_monitor） | 身份标签需付费 |
| 活跃地址 / 交易量趋势 | 部分 | Token Terminal / Artemis |
| 持有者集中度 | 单地址查（Etherscan） | 聚合 SQL 需 Dune |
| MVRV / NUPL | ❌ | Glassnode（付费） |

> 接入 key 时统一放环境变量（如 `ETHERSCAN_KEY`、`DUNE_KEY`），**不要写进代码或提交**。
