# Hyperliquid (HYPE) 一手补充：GitHub 仓库 + 链上硬数据

> 采集时间：2026-10-09（UTC+8）
> 采集方式：GitHub REST API v3（无 token，60 次/小时限额）、DefiLlama 公开 API、Hyperliquid 官方 info API、hypurrscan.io 浏览器实抓。
> 本文件是对 `hyperliquid_deep_research_20261009.md` 的**增量补充**，不重复原报告已覆盖的基线数字。
> 每条数据后括注来源 URL；未取到的项明确标注。

---

## A1 GitHub 组织与 Release

### 1.0 组织名勘误（重要）

用户指定的 `hyperliquidxyz` 在 GitHub 上是一个 **User 账号而非 Organization**，且只有 2 个 0 星空仓库（`BacktestMySetup`、`backtest-my-setup`，均为 2026-06-06 创建），**不是官方组织**。

经 GitHub search/users 与官方元数据交叉验证，**Hyperliquid 官方 GitHub 组织为 `hyperliquid-dex`**（blog=hyperfoundation.org，twitter=HyperliquidX，description 与官网一致，DefiLlama protocol 数据中 github 字段也指向 `hyperliquid-dex`）。下文均以此为准。

- 官方组织主页：https://github.com/hyperliquid-dex
- 组织元数据：https://api.github.com/orgs/hyperliquid-dex
- 原指定账号 `hyperliquidxyz`（非官方）：https://github.com/hyperliquidxyz

### 1.1 组织总览

| 指标 | 数值 | 来源 |
|---|---|---|
| 组织名 | hyperliquid-dex | https://api.github.com/orgs/hyperliquid-dex |
| Public repos | **11** | 同上 |
| Followers | **1,558** | 同上 |
| 全部仓库星标合计 | **3,137 ★** | https://api.github.com/orgs/hyperliquid-dex/repos?per_page=100&sort=updated |
| 官方描述 | "Hyperliquid is a Layer 1 blockchain best known for perpetual futures and spot trading. The ecosystem supports borrowing, lending, RWAs, and a full-fledged EVM." | 同上 |

> 注：GitHub 组织级 `/contributors` 聚合接口对该 org 返回 404（https://api.github.com/orgs/hyperliquid-dex/contributors ），贡献者总数未获取成功；核心代码提交集中在少数 commit message 上的开发者（见 1.3）。

### 1.2 全部 11 个仓库清单（按最近 pushed_at 排序）

| 仓库名 | 星标 | 语言 | 最近 push (UTC) | Forks | Open Issues | 说明 |
|---|---|---|---|---|---|---|
| [node](https://github.com/hyperliquid-dex/node) | 508 | Dockerfile | 2026-08-10 | 191 | 80 | L1 节点运行时（镜像） |
| [order_book_server](https://github.com/hyperliquid-dex/order_book_server) | 165 | Rust | 2026-07-15 | 102 | 7 | 订单簿服务器 |
| [hyperliquid-python-sdk](https://github.com/hyperliquid-dex/hyperliquid-python-sdk) | **1,846** | Python | 2026-06-04 | 570 | 106 | 官方 Python SDK（最活跃对外 SDK） |
| [hyperliquid-rust-sdk](https://github.com/hyperliquid-dex/hyperliquid-rust-sdk) | 471 | Rust | 2025-10-21 | 266 | 59 | 官方 Rust SDK |
| [hyper-evm-sync](https://github.com/hyperliquid-dex/hyper-evm-sync) | 21 | Rust | 2025-07-15 | 17 | 2 | HyperEVM 同步工具 |
| [ts-examples](https://github.com/hyperliquid-dex/ts-examples) | 17 | — | 2025-02-11 | 11 | 1 | TypeScript 示例 |
| [hyperliquid-stats-web](https://github.com/hyperliquid-dex/hyperliquid-stats-web) | 39 | TypeScript | 2024-12-02 | 19 | 3 | 协议统计前端 |
| [contracts](https://github.com/hyperliquid-dex/contracts) | 47 | Rust | 2023-11-28 | 33 | 1 | 早期合约 |
| [historical_data](https://github.com/hyperliquid-dex/historical_data) | 11 | — | 2023-05-02 | 7 | 0 | 历史数据 |
| [hyperliquid-stats](https://github.com/hyperliquid-dex/hyperliquid-stats) | 10 | Python | 2023-10-16 | 5 | 0 | 统计脚本 |
| [block-importer](https://github.com/hyperliquid-dex/block-importer) | 2 | Rust | 2025-04-26 | 5 | 0 | HyperEVM block → hl-node 导入 |

来源：https://api.github.com/orgs/hyperliquid-dex/repos?per_page=100&sort=updated

### 1.3 最活跃 3 个仓库的 Release / Commit 时间线

#### (a) `node`（L1 节点，508★，pushed 2026-08-10）
- **无 GitHub Release**（该仓库不打 tag，运行时版本通过链上升级推进）。
- 最近 8 条 commit（来源：https://api.github.com/repos/hyperliquid-dex/node/commits?per_page=8 ）：

| 日期 (UTC) | Commit 摘要 |
|---|---|
| 2026-08-10 | remove inactive root ips |
| 2026-07-30 | remove inactive root peer |
| 2026-07-01 | Merge PR #151 (TimEconometrics/patch-1) |
| 2026-06-10 | Update IP address for LiquidSpirit x Rekt Gang |
| 2026-05-20 | Merge PR #146 (Frixoe/luganodes-patch-3) |
| 2026-05-20 | Merge PR #145 (IbrarMakaveli/main) |
| 2026-05-19 | Update sentry IP for Luganodes |
| 2026-05-09 | update spec |

> 观察：node 仓库近期改动几乎全是**验证者 root IP / sentry 地址维护**（社区 PR 合入），说明 L1 节点 P2P 拓扑在持续轮换，**没有功能性 runtime 版本号对外暴露在 GitHub**。

#### (b) `order_book_server`（Rust，165★，pushed 2026-07-15）
- **无 GitHub Release**。
- 最近 commit（来源：https://api.github.com/repos/hyperliquid-dex/order_book_server/commits?per_page=8 ）：

| 日期 (UTC) | Commit 摘要 |
|---|---|
| 2026-07-15 | Merge PR #12 (ben-supportAloPriority) |
| 2026-07-15 | address comments |
| 2026-07-15 | **Add support for insertBefore in RawBookDiff** |
| 2025-09-08 | Merge PR #4 (ifdario/yawc) |
| 2025-09-03 | use yawc as default WebSocket crate supporting compression |
| 2025-08-09 / 2025-08-08 | README / docs（initial commit 2025-08-08） |

> 观察：订单簿服务器是 2025-08 才新开的 Rust 仓，2026-07 仍在加 **RawBookDiff insertBefore** 优先级队列支持——属于性能/撮合精度演进，未发版。

#### (c) `hyperliquid-python-sdk`（1,846★，对外 SDK 主力，pushed 2026-06-04）
- **有 Release**。最近 8 个 tag（来源：https://api.github.com/repos/hyperliquid-dex/hyperliquid-python-sdk/releases?per_page=10 ）：

| 版本 | 发布日期 (UTC) | 核心改动（对应 commit） |
|---|---|---|
| **0.24.0** | 2026-06-04 | Support multisig userSetAbstraction (#299) |
| 0.23.0 | 2026-04-14 | Version 0.23.0 (#289)；含 multisig convert-to-normal-user example |
| 0.22.0 | 2026-02-04 | Version 0.22.0 (#260) |
| 0.21.0 | 2025-11-18 | Version 0.21.0 (#230) |
| 0.20.1 | 2025-11-04 | Fix market orders for HIP-3 DEXs (#225) |
| 0.20.0 | 2025-10-17 | Version 0.20.0 (#219) |
| 0.19.0 | 2025-09-11 | — |
| 0.18.0 | 2025-08-12 | — |

> 观察：SDK 约 2–3 个月一个 minor 版本；最新 0.24.0（2026-06-04）加入 **multisig userSetAbstraction**，与链上钱包抽象/多签功能对齐。**注意：SDK 自 2026-06-04 后已 4 个月无新 release**（截至 2026-10-09）。

---

## A2 DefiLlama 协议最新数据（对比基线）

### 2.1 价格与市值快照（2026-10-09）

| 指标 | 当前值 | 原报告基线 | 增量变化 | 来源 |
|---|---|---|---|---|
| HYPE 现价 | **$85.27**（confidence 0.99，ts 1791520202） | ~$85.30 | **−$0.03（基本持平）** | https://coins.llama.fi/prices/current/hyperliquid:0x0d01dc56dcaaca66ad901c959b4011ec |
| HYPE 现价（hypurrscan 前端交叉验证） | $85.29（24h −2.74%） | — | 与 API 一致 | https://hypurrscan.io/dashboard |
| 流通市值 MC | **$18.997B** | $18.98B | **+$0.02B（+0.1%）** | https://api.llama.fi/protocol/hyperliquid |
| FDV | 未在 protocol 接口返回（空） | $81.52B | 未获取成功（接口字段为空） | 同上 |

### 2.2 协议 TVL 与趋势

| 指标 | 当前值 (2026-10-09) | 7d 前 (2026-10-03) | 30d 前 (2026-09-10) | 90d 前 (2026-07-12) | 对比原报告基线 | 来源 |
|---|---|---|---|---|---|---|
| 协议总 TVL（parent#hyperliquid） | **$7.055B** | $7.286B | $6.840B | $5.996B | 基线 $7.04B → **+$0.015B（+0.2%，基本持平）** | https://api.llama.fi/protocol/hyperliquid |
| └─ Arbitrum 链上部分 | $379.14M | — | — | — | 新拆分数据 | 同上 currentChainTvls |
| └─ Hyperliquid L1 链上部分 | $6.676B | — | — | — | 新拆分数据 | 同上 |
| 7d TVL 变化 | **−3.17%** | — | — | — | 一周净流出约 $231M | 同上 tvl 序列计算 |
| 30d TVL 变化 | **+3.15%** | — | — | — | 一月净流入约 $216M | 同上 |
| 90d TVL 变化 | **+17.7%** | — | — | — | 季度净流入约 $1.06B | 同上 |

### 2.3 HyperEVM / 链层 TVL（DefiLlama chains 口径）

| 指标 | 当前值 (2026-10-08) | 7d 前 (2026-10-02) | 30d 前 (2026-09-09) | 来源 |
|---|---|---|---|---|
| Hyperliquid L1 链 TVL（即部署在 L1/HyperEVM 上的 DeFi 总锁仓） | **$1.047B** | $1.179B | $1.470B | https://api.llama.fi/v2/chains ；https://api.llama.fi/v2/historicalChainTvl/Hyperliquid |
| 7d 变化 | **−11.3%** | — | — | 同上 |
| 30d 变化 | **−28.8%** | — | — | 同上 |

> **关键反差**：协议层 TVL（含 HLP/质押/做市商保证金）近 30 天 +3.15%，但**链上 DeFi TVL（HyperEVM 生态）近 30 天 −28.8%**——说明生态内应用层资金在撤，而 DEX 核心仓位仍稳。

### 2.4 Fees / Revenue（区分口径）

来源：https://api.llama.fi/summary/fees/hyperliquid?dataType=dailyRevenue 与 `dailySupplySideRevenue`

| 口径 | 24h | 7d | 30d | TTM（近 1 年） | 对比原报告基线 |
|---|---|---|---|---|---|
| **Revenue（协议收入，归协议/Assistance Fund）** | **$2.45M** | $15.57M | $73.59M | **$706.8M** | 原报告 2025 日历年 ~$0.9B；当前 TTM $0.707B，**年化收入较 2025 峰值回落约 21%** |
| **Supply-side revenue（回流给 LP/staker）** | $0.67M | $3.81M | $17.24M | $161.5M | 新拆分数据 |
| **User fees（用户支付费用）** | — | — | — | — | **未获取成功**：DefiLlama 对 hyperliquid 未单独上报 userFees（接口返回占位值 $578/$1,287，明显非真实值） |
| 24h fees（hypurrscan 前端交叉验证） | **$3.21M（+67.64%）** | — | — | — | https://hypurrscan.io/dashboard |

> 注：DefiLlama 的 `dailyRevenue` = 用户手续费中扣除 LP 分成后归协议的部分；`supplySideRevenue` = 分给 LP/质押者的部分。两者之和 $2.45M+$0.67M = $3.12M/24h，与 hypurrscan 前端 24h fees $3.21M 基本吻合。

---

## A3 链上动态（验证者 / 质押 / 解锁 / Buyback）

### 3.1 验证者与质押现状（hypurrscan 实抓，2026-10-09）

来源：https://hypurrscan.io/validators 与 https://hypurrscan.io/staking

| 指标 | 当前值 | 原报告基线 | 增量变化 |
|---|---|---|---|
| 活跃验证者数 | **27 / 35**（27 个出块，35 个槽位） | 未给具体数 | 新数据 |
| Active Stake | **439.94M HYPE（99.99% 质押率）** | ~436–440M | **基本持平（+约 4M HYPE）** |
| 质押 APR | hypurrscan 前端未直接展示数值 | ~2.17% | 未获取成功（页面只显示各验证者佣金费率 0–5%，不显示链上 APR） |
| 现货稳定币 TVL | **$2.85B**（USDC $2.835B / USDH $5.87M / USDT $5.25M / USDE $5.58M） | 未给 | 新数据 |
| 24h 交易费 | $3.21M（+67.64%） | — | 新数据 |

**Top 5 验证者质押分布（2026-10-09）**：

| 验证者 | 质押量 | 占比 | 佣金费率 |
|---|---|---|---|
| Hyper Foundation 2 | 54.16M HYPE | 12.31% | 3.00% |
| Hyper Foundation 1 | 52.25M HYPE | 11.88% | 3.00% |
| Hyper Foundation 3 | 51.78M HYPE | 11.77% | 3.00% |
| Hyperliquid Strategies x Unit（NASDAQ: PURR 合作） | 37.88M HYPE | 8.61% | 2.00% |
| Hyper Foundation 4 | 34.48M HYPE | 7.84% | 3.00% |

> 观察：Hyper Foundation 自营 5 个验证者（HF 1–5）合计 54.16+52.25+51.78+34.48+15.16 = **207.83M HYPE，占全网质押 47.2%**——foundation 自营验证者仍接近全网一半质押，去中心化进度有限。

### 3.2 2026-10-06 团队解锁动向

- 基线：每月 6 号解锁 9.92M HYPE（2025-11 起 24 个月线性 vesting）；2026-10-06 为第 12 次解锁（累计解锁约 119M HYPE，含 2026-10-06 当期）。
- **链上转移 / Assistance Fund 地址动向：未获取成功**。
  - 原因：(1) 通用搜索引擎本次对 "Hyperliquid unlock" 相关查询返回 restricted/no results；(2) hypurrscan dashboard 的实时 Transfers 流只显示最近 466 笔小额 USDC 转账，无当日 9.92M HYPE 大额转移被标出；(3) 官方 info API 的 `delegations` / `stakingSummary` / `validatorSet` 端点均返回 422，无法按地址拉取 vesting 合约历史。
- **媒体/社区讨论：未获取成功**（搜索受限）。
- **旁证**：截至 2026-10-09，HYPE 现价 $85.27，24h −2.74%，未出现因解锁导致的异常暴跌；Active Stake 仍 439.94M（99.99%），说明解锁的 HYPE **没有大规模流出验证者**。

### 3.3 Assistance Fund Buyback / 烧毁

来源：https://hypurrscan.io/dashboard（Active TWAPs 面板，实抓 2026-10-09）

| 观察项 | 数值 | 备注 |
|---|---|---|
| 当前活跃 BUY HYPE-USD TWAP | **25,000 HYPE（约 $1.74M）**，地址 `0x3c66b4d4...ff89eab6`，3 小时后到期 | 金额与 Assistance Fund 常规 TWAP buyback 规模吻合 |
| 当前活跃 BUY HYPE TWAP | **10,000 HYPE（约 $788K）**，地址 `0x0682f4ee...f4e5b571`，6 天到期 | 第二笔 BUY HYPE |
| TWAP Buy Pressure NEXT 1H | $487K（ALL）/ $544K（SPOT）/ $57K（净流入） | hypurrscan 前端实时面板 |
| TWAP Buy Pressure NEXT 24H | $2.17M（ALL）/ $2.50M（SPOT）/ $332K（净流入） | 同上 |
| Active TWAP 总数 | 328 笔 | 含 PERPS/SPOT/HIP-3 |
| 累计烧毁 HYPE | 原报告 ~46M HYPE；**本次未获取到更新后的累计烧毁数** | 原因：burn 地址余额需查具体合约，本次未拿到；建议下一轮补 hypurrscan HYPE holder / burn 页面 |

> 观察：dashboard 上同时存在两笔 **BUY HYPE** TWAP（合计 ~35,000 HYPE / $2.5M）在执行，与 Assistance Fund "用协议收入 TWAP 买入 HYPE 并烧毁" 的机制一致——**buyback 在 2026-10-09 当周仍在持续执行**。

### 3.4 大额转账 / 链上异常

- hypurrscan Transfers 流（实时）：最近 15 笔均为 USDC $5–$800 级别的小额日常转账，**未见当日 >$1M 的异常大额 HYPE 转移**。
- HIP-3 拍卖：当前 HIP-3 token auction 价格 1,090.85 HYPE（~$93K），上一笔 para:SMH 用 571.86 HYPE 部署——生态新币发行节奏正常。

---

## 附：未获取成功项汇总（不编造）

| 数据项 | 失败原因 |
|---|---|
| FDV 当前值 | DefiLlama `/protocol/hyperliquid` 返回 fdv 字段为空 |
| 组织级贡献者总数 | GitHub `/orgs/hyperliquid-dex/contributors` 返回 404 |
| 链上质押 APR 数值 | hypurrscan 前端只显示佣金费率，不显示 APR；官方 info API stakingSummary/delegations 端点 422 |
| 2026-10-06 解锁当日具体链上转移哈希/金额 | 搜索受限 + 官方 API 422 + 浏览器实时 transfers 流未捕获大额 |
| 累计 buyback 烧毁 HYPE 最新数 | 未定位 burn 地址并拉取余额；仅观测到当前在执行的 TWAP buyback |
| User fees 口径拆分 | DefiLlama 对 hyperliquid 未单独上报 userFees（接口返回占位值） |
