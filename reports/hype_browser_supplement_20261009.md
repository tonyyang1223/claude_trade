# Hyperliquid (HYPE) 浏览器一手补充笔记

> 采集时间：2026-10-09（UTC+8）· 采集方式：GitHub REST API v3（无 token）、DefiLlama 公开 API、Hyperliquid 官方 info API、hypurrscan.io 浏览器实抓、已登录 X 时间线、alternative.me / CoinGecko / Coinglass 公开数据、公开网页间接采集 Reddit/Discord/治理信息。
> 本文件是对 `hype_deep_research_20261009.md/html` 的**补充**，**不改动原报告**；所有数据均附来源 URL，未取到的项明确标注"未获取成功"，不编造。
> 采集时现价快照：**HYPE ≈ $85.25–85.27（24h 约 −2.5%~−2.7%）**，与原报告基线 ~$85.30 基本持平。

---

## 一、GitHub 仓库与 Release 一手笔记

### 1.0 组织名勘误（重要，须修正原报告引用）

用户指定的 `hyperliquidxyz` 在 GitHub 上是一个 **User 账号而非 Organization**，且只有 2 个 0 星空仓库（`BacktestMySetup`、`backtest-my-setup`，均为 2026-06-06 创建），**不是官方组织**。经 GitHub search/users 与官方元数据交叉验证，**Hyperliquid 官方 GitHub 组织为 `hyperliquid-dex`**（blog=hyperfoundation.org，twitter=HyperliquidX，DefiLlama protocol 数据 github 字段亦指向它）。下文均以此为准。

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

> 注：GitHub 组织级 `/contributors` 聚合接口对该 org 返回 404（https://api.github.com/orgs/hyperliquid-dex/contributors ），贡献者总数未获取成功。

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

**(a) `node`（L1 节点，508★，pushed 2026-08-10）—— 无 GitHub Release**（运行时版本通过链上升级推进，不打 tag）。最近 8 条 commit（来源：https://api.github.com/repos/hyperliquid-dex/node/commits?per_page=8 ）：

| 日期 (UTC) | Commit 摘要 |
|---|---|
| 2026-08-10 | remove inactive root ips |
| 2026-07-30 | remove inactive root peer |
| 2026-07-01 | Merge PR #151 (TimEconometrics/patch-1) |
| 2026-06-10 | Update IP address for LiquidSpirit x Rekt Gang |
| 2026-05-20 | Merge PR #146 / #145（社区验证者 PR） |
| 2026-05-19 | Update sentry IP for Luganodes |
| 2026-05-09 | update spec |

> 观察：node 仓库近期改动几乎全是**验证者 root IP / sentry 地址维护**（社区 PR 合入），说明 L1 节点 P2P 拓扑在持续轮换，**没有功能性 runtime 版本号对外暴露在 GitHub**。

**(b) `order_book_server`（Rust，165★，pushed 2026-07-15）—— 无 GitHub Release**。该仓 2025-08 才新开；2026-07-15 仍在加 **RawBookDiff insertBefore** 优先级队列支持（撮合精度/性能演进）。来源：https://api.github.com/repos/hyperliquid-dex/order_book_server/commits?per_page=8

**(c) `hyperliquid-python-sdk`（1,846★，对外 SDK 主力）—— 有 Release**。最近 8 个 tag（来源：https://api.github.com/repos/hyperliquid-dex/hyperliquid-python-sdk/releases?per_page=10 ）：

| 版本 | 发布日期 (UTC) | 核心改动 |
|---|---|---|
| **0.24.0** | 2026-06-04 | Support multisig userSetAbstraction (#299) |
| 0.23.0 | 2026-04-14 | 含 multisig convert-to-normal-user example |
| 0.22.0 | 2026-02-04 | Version 0.22.0 (#260) |
| 0.21.0 | 2025-11-18 | Version 0.21.0 (#230) |
| 0.20.1 | 2025-11-04 | Fix market orders for HIP-3 DEXs (#225) |
| 0.20.0 | 2025-10-17 | Version 0.20.0 (#219) |
| 0.19.0 | 2025-09-11 | — |
| 0.18.0 | 2025-08-12 | — |

> 观察：SDK 约 2–3 个月一个 minor 版本；最新 0.24.0（2026-06-04）加入 multisig userSetAbstraction，与链上钱包抽象/多签对齐。**注意：SDK 自 2026-06-04 起已约 4 个月无新 release**（截至 2026-10-09）。

---

## 二、链上数据 / 浏览器实时快照（2026-10-09）

### 2.1 价格与市值快照（对比原报告基线）

| 指标 | 当前值 | 原报告基线 | 增量变化 | 来源 |
|---|---|---|---|---|
| HYPE 现价（coins.llama.fi） | **$85.27**（confidence 0.99） | ~$85.30 | −$0.03（基本持平） | https://coins.llama.fi/prices/current/hyperliquid:0x0d01dc56dcaaca66ad901c959b4011ec |
| HYPE 现价（hypurrscan 前端交叉验证） | $85.29（24h −2.74%） | — | 与 API 一致 | https://hypurrscan.io/dashboard |
| HYPE 现价（CoinGecko 一手） | **$85.25**（24h −2.46%） | — | 与上一致 | https://api.coingecko.com/api/v3/simple/price?ids=hyperliquid |
| 流通市值 MC | **$18.997B** | $18.98B | +0.02B（+0.1%） | https://api.llama.fi/protocol/hyperliquid |
| FDV | **未获取成功**（protocol 接口 fdv 字段为空） | $81.52B | — | 同上 |

### 2.2 协议 TVL 与趋势

| 指标 | 当前值 (2026-10-09) | 7d 前 | 30d 前 | 90d 前 | 对比原报告基线 | 来源 |
|---|---|---|---|---|---|---|
| 协议总 TVL（parent#hyperliquid） | **$7.055B** | $7.286B | $6.840B | $5.996B | 基线 $7.04B → **+$0.015B（+0.2%，基本持平）** | https://api.llama.fi/protocol/hyperliquid |
| └─ Hyperliquid L1 链上部分 | $6.676B | — | — | — | 新拆分数据 | 同上 currentChainTvls |
| └─ Arbitrum 链上部分 | $379.14M | — | — | — | 新拆分数据 | 同上 |
| 7d TVL 变化 | **−3.17%** | — | — | — | 一周净流出约 $231M | 同上 tvl 序列 |
| 30d TVL 变化 | **+3.15%** | — | — | — | 一月净流入约 $216M | 同上 |
| 90d TVL 变化 | **+17.7%** | — | — | — | 季度净流入约 $1.06B | 同上 |

### 2.3 HyperEVM / 链层 TVL（DefiLlama chains 口径）—— 生态层失血信号

| 指标 | 当前值 (2026-10-08) | 7d 前 | 30d 前 | 来源 |
|---|---|---|---|---|
| Hyperliquid L1 链 TVL（部署在 L1/HyperEVM 上的 DeFi 总锁仓） | **$1.047B** | $1.179B | $1.470B | https://api.llama.fi/v2/chains ；https://api.llama.fi/v2/historicalChainTvl/Hyperliquid |
| 7d 变化 | **−11.3%** | — | — | 同上 |
| 30d 变化 | **−28.8%** | — | — | 同上 |

> **关键反差**：协议层 TVL（含 HLP/质押/做市商保证金）近 30 天 +3.15%，但**链上 DeFi TVL（HyperEVM 生态）近 30 天 −28.8%**——生态内应用层资金在撤，而 DEX 核心仓位仍稳。这是原报告未量化的新信号。

### 2.4 Fees / Revenue（区分口径）

来源：https://api.llama.fi/summary/fees/hyperliquid?dataType=dailyRevenue 与 `dailySupplySideRevenue`

| 口径 | 24h | 7d | 30d | TTM（近 1 年） | 对比原报告基线 |
|---|---|---|---|---|---|
| **Revenue（协议收入，归协议/Assistance Fund）** | **$2.45M** | $15.57M | $73.59M | **$706.8M** | 原报告 2025 日历年 ~$0.9B；当前 TTM $0.707B，**年化收入较 2025 峰值回落约 21%** |
| **Supply-side revenue（回流给 LP/staker）** | $0.67M | $3.81M | $17.24M | $161.5M | 新拆分数据 |
| **User fees（用户支付费用）** | — | — | — | — | **未获取成功**：DefiLlama 对 hyperliquid 未单独上报 userFees（接口返回占位值） |
| 24h fees（hypurrscan 前端交叉验证） | **$3.21M（+67.64%）** | — | — | — | https://hypurrscan.io/dashboard |

> 注：DefiLlama `dailyRevenue` = 用户手续费扣除 LP 分成后归协议部分；`supplySideRevenue` = 分给 LP/质押者部分。两者 $2.45M+$0.67M=$3.12M/24h，与 hypurrscan 24h fees $3.21M 基本吻合。

### 2.5 验证者与质押现状（hypurrscan 实抓，2026-10-09）

来源：https://hypurrscan.io/validators 与 https://hypurrscan.io/staking

| 指标 | 当前值 | 原报告基线 | 增量变化 |
|---|---|---|---|
| 活跃验证者数 | **27 / 35**（27 个出块，35 个槽位） | 未给具体数 | 新数据 |
| Active Stake | **439.94M HYPE（99.99% 质押率）** | ~436–440M | 基本持平（+约 4M HYPE） |
| 质押 APR | **未获取成功**（页面只显示各验证者佣金费率 0–5%，不显示链上 APR；官方 info API stakingSummary/delegations 端点 422） | ~2.17% | — |
| 现货稳定币 TVL | **$2.85B**（USDC $2.835B / USDE $5.58M / USDT $5.25M / USDH $5.87M） | 未给 | 新数据 |
| 24h 交易费 | $3.21M（+67.64%） | — | 新数据 |

**Top 5 验证者质押分布（2026-10-09）**：

| 验证者 | 质押量 | 占比 | 佣金费率 |
|---|---|---|---|
| Hyper Foundation 2 | 54.16M HYPE | 12.31% | 3.00% |
| Hyper Foundation 1 | 52.25M HYPE | 11.88% | 3.00% |
| Hyper Foundation 3 | 51.78M HYPE | 11.77% | 3.00% |
| Hyperliquid Strategies x Unit（Nasdaq: PURR 合作） | 37.88M HYPE | 8.61% | 2.00% |
| Hyper Foundation 4 | 34.48M HYPE | 7.84% | 3.00% |

> 观察：Hyper Foundation 自营 5 个验证者（HF 1–5）合计 54.16+52.25+51.78+34.48+15.16 = **207.83M HYPE，占全网质押 47.2%**——foundation 自营验证者仍接近全网一半质押，去中心化进度有限。

### 2.6 Assistance Fund Buyback / 烧毁（TWAP 实时在跑）

来源：https://hypurrscan.io/dashboard（Active TWAPs 面板，实抓 2026-10-09）

| 观察项 | 数值 | 备注 |
|---|---|---|
| 当前活跃 BUY HYPE-USD TWAP | **25,000 HYPE（约 $1.74M）**，地址 `0x3c66b4d4...ff89eab6`，3 小时后到期 | 与 Assistance Fund 常规 TWAP buyback 规模吻合 |
| 当前活跃 BUY HYPE TWAP | **10,000 HYPE（约 $788K）**，地址 `0x0682f4ee...f4e5b571`，6 天到期 | 第二笔 BUY HYPE |
| TWAP Buy Pressure NEXT 1H | $487K（ALL）/ $544K（SPOT）/ $57K（净流入） | hypurrscan 前端实时面板 |
| TWAP Buy Pressure NEXT 24H | $2.17M（ALL）/ $2.50M（SPOT）/ $332K（净流入） | 同上 |
| Active TWAP 总数 | 328 笔 | 含 PERPS/SPOT/HIP-3 |
| 累计烧毁 HYPE | 原报告 ~46M HYPE；**本次未获取到更新后的累计烧毁数**（burn 地址余额需查具体合约） | 建议下一轮补 hypurrscan HYPE holder / burn 页面 |

> 观察：dashboard 上同时存在两笔 **BUY HYPE** TWAP（合计 ~35,000 HYPE / $2.5M）在执行，与 Assistance Fund "用协议收入 TWAP 买入 HYPE 并烧毁"机制一致——**buyback 在 2026-10-09 当周仍在持续执行**。另据公开报道，2026-10-03 起 AF USDC 储备（Aave v2）开始产生利息，首笔 **$14.58M USDC** 收益到账 System Interest Address（待划转回购）；近期单笔销毁 112,580 HYPE（~$10.15M，10/5）。来源：https://cryptocurrency.com.tr/hyperliquid-secures-14-58m-in-usdc-for-hype-buybacks-400111

### 2.7 2026-10-06 团队解锁动向

- 基线：每月 6 号解锁 9.92M HYPE（2025-11 起 24 个月线性 vesting）；2026-10-06 为第 12 次解锁（累计解锁约 119M HYPE，含当期）。
- **链上转移 / Assistance Fund 地址动向：未获取成功**。原因：(1) 通用搜索引擎对 "Hyperliquid unlock" 相关查询返回受限；(2) hypurrscan 实时 Transfers 流只显示最近小额 USDC 转账，无当日大额 HYPE 转移被标出；(3) 官方 info API 的 `delegations`/`stakingSummary`/`validatorSet` 端点均返回 422。
- **旁证**：截至 2026-10-09，HYPE $85.27（24h −2.74%），未出现因解锁导致的异常暴跌；Active Stake 仍 439.94M（99.99%），说明解锁的 HYPE **没有大规模流出验证者**。
- **10-08 OTC 事件（合并分片 B/C 口径）**：2026-09-30 起 Hyperliquid Labs 解押 **3.75M HYPE（约 $330M）**，通过 OTC 卖给单一机构买家（市场猜测为 ICE/NYSE 母公司），**不在公开市场抛售**，10/7 分发给团队成员；消息在 10/8 传出当日 HYPE 跌约 **4% 至 ~$87**。来源：https://www.chaincatcher.com/en/article/2293316 ；https://crypto.news/hype-drops-4-to-87-as-team-starts-330m-token-deal/

---

## 三、Twitter / X 一手动态

> 浏览器已登录 X（账号 @tonyyang12231），@HyperliquidX 时间线为一手抓取。

### 3.1 官方账号基础信息

| 项目 | 数值 |
|---|---|
| 粉丝数 | **43 万（430K）** |
| 发帖总数 | **1,264 帖** |
| 加入时间 | 2022 年 5 月 |
| Bio | "容纳所有金融的基础设施。链上交易加密货币、商品、指数、外汇和现实世界资产，24/7。不针对英国人士。" |
| 官网 | hyperfoundation.org |
| 置顶推文 | **无置顶推文** |

> **重要观察**：@HyperliquidX 官方号自 **2026-09-30 后至 10-09 已 10 天未发推（静默期）**。10 月的重大事件（AQAv2 首笔 $14.58M 储备收益、$10.15M 销毁、$330M OTC 解锁、Token2049 演讲、Bloomberg Terminal 上线）均通过联合创始人 iliensinc 的 Discord 发言、@WuBlockchain 及加密媒体流出，官方 X 未直接官宣——与 9 月高频产品更新形成明显反差，团队本月重心在线下活动（KBW、Token2049 新加坡）与 OTC 安排。

### 3.2 近 2 周重要推文表（按时间倒序，一手时间线）

> 互动顺序：评论 / 转推 / 赞 / 浏览量（X UI 原生顺序）。单条 status ID 在未登录只读模式下未渲染独立 URL，链接统一指向账号主页。

| 日期 | 一句话内容 | 互动（评/转/赞/浏览） | 链接 |
|---|---|---|---|
| 2026-09-30 | **新加坡社区活动 Hyperliquid Community Event 2026 定于 10/5 晚**，已超额认购 | 241 / 207 / 1,371 / **16 万** | https://x.com/HyperliquidX |
| 2026-09-23 | **未平仓合约（OI）达历史新高 $180 亿** | 336 / 511 / 2,769 / **30 万** | https://x.com/HyperliquidX |
| 2026-09-23 | 补充说明：双边 OI = 多头+空头仓位之和（澄清 $18B 口径） | 44 / 7 / 160 / 3.5 万 | https://x.com/HyperliquidX |
| 2026-09-21 | **追踪止损（Trailing stops）正式上线永续市场** | 227 / 273 / 2,157 / 19 万 | https://x.com/HyperliquidX |
| 2026-09-18 | **手动借贷（Manual Borrows）上线**：首日 $2.69 亿资产被借出 | 302 / 469 / 1,914 / **55 万**（近期最高浏览） | https://x.com/HyperliquidX |
| 2026-09-09 | 应社区请求上线 $USELESS 永续，最高 3x 杠杆 | 227 / 224 / 1,503 / 25 万 | https://x.com/HyperliquidX |

### 3.3 核心团队 / KOL 围绕 HYPE 的重要发言（1–2 周内）

| 人物 / 账号 | 场合 / 日期 | 核心观点 | 来源 |
|---|---|---|---|
| **Jeff Yan**（联合创始人 / CEO） | Token2049 新加坡，2026-10-07/08 | 华尔街 pre-IPO 收益集中在少数人、对散户不可持续；Hyperliquid 使命是"金融开放"；**Options（期权）将成为 HyperCore 上下一个产品组件**，基于 HIP-4 继承现货/订单簿/组合保证金，用 Perps 对冲 Delta | https://www.digitaltoday.co.kr/en/view/112515/hyperliquid-ceo-says-few-capture-benefits-of-corporate-growth-criticises-wall-street ；https://coinpost.ai/en/topics/237330 |
| **iliensinc**（联合创始人） | 官方 Discord，2026-09-30 | Hyperliquid Labs 当日解押 **3.75M HYPE（~$330M）** OTC 卖给单一机构，公开市场不抛；10/7 分发团队 | https://www.chaincatcher.com/en/article/2293316 |
| **@WuBlockchain**（链上 KOL） | X，2026-10-03/05/08 | 连续跟踪：①首笔 AQAv2 USDC 储备收益 $14.58M 到账；②Hyperliquid Strategies 增持 1.9M HYPE，总持仓达 37M HYPE（~$3.26B）；③3.75M HYPE OTC 分配完成 | https://coinfomania.com/hyperliquid-labs-completes-330-million-hype-otc-distribution/ |

---

## 四、Reddit / Discord / 社区情绪

> Reddit 未登录态直连 `www.reddit.com/r/hyperliquid/about.json` 被网络安全层拦截，Discord 需登录无法读频道历史。本节用搜索引擎/第三方镜像（reddlx）间接采集，**拿不到的数字明确标注"未获取"，不编造**。

### 4.1 Reddit（r/hyperliquid）采集局限如实说明

| 指标 | 数值 | 状态 |
|---|---|---|
| 订阅数（subscribers） | **未获取** | about.json 直连被拦截，第三方统计接口本次无返回 |
| 本周访客（weekly visitors） | **未获取** | 同上 |
| 社区活跃度旁证 | 热门帖被大量 crosspost 到 r/CryptoCurrency / r/algorand / r/solana；u/applezoid、u/StevenVinyl 持续产出长帖/视频 | https://www.reddlx.com/author/applezoid ；https://www.reddlx.com/author/StevenVinyl |

### 4.2 本月热门帖 Top 5（经 reddlx 镜像 + 新闻交叉，赞/评论数未取到）

| # | 帖子标题 | 作者 | 时间 | 核心信号 |
|---|---|---|---|---|
| 1 | **SpaceX Just Proved Hyperliquid's Biggest Bull Case**（视频） | u/applezoid | ≈2026-09-18 | 把 SpaceX 上市叙事与 Hyperliquid RWA perps（无 CEX 也能交易"股票"）看多逻辑绑定——**RWA 叙事是当前社区第一多头论据** |
| 2 | **THIS Is How You Do a Hyperliquid Price Prediction**（视频） | u/applezoid | ≈2026-09-09 | 价格预测类内容，KOL 持续输出 |
| 3 | 监测 TSMC 晶圆厂附近地震站、自动做空半导体 perps 的 dashboard | u/StevenVinyl | 2026 年内 | 极客用户把 HIP-3 半导体 perps 接入地震传感器——**permissionless perps 已被用来做实物事件驱动策略**，degen 文化浓厚 |
| 4 | **How I run my Hyperliquid gambling AI quant**（自然语言 agent 自动交易） | u/StevenVinyl | 2026 年内 | 社区重心在自动化交易 agent / 量化 bot，而非 hodl 讨论 |
| 5 | （新闻外溢）**HYPE 跌至 $87，Hyperliquid Labs 启动约 $330M OTC 交易** | 非原帖，被广泛转引 | 2026-10-08 | 团队解锁/OTC 抛压是本月社区最大空头焦虑点 |

> 来源：https://reddlx.com/author/applezoid ；https://www.reddlx.com/author/StevenVinyl ；OTC 事件 https://crypto.news/hype-drops-4-to-87-as-team-starts-330m-token-deal/

### 4.3 社区核心话题与治理（HIP 系列）

| 话题 | 社区立场/要点 | 来源 |
|---|---|---|
| **多空争议** | 多头：RWA perps OI 纪录、占全 perp DEX OI 64%、ETF 上市；空头：238M HYPE 团队仓每月解锁 vs 月回购仅 ~60 万枚，10/8 $330M OTC 当日 HYPE 跌 4% 至 $87 | https://www.sec.gov/Archives/edgar/data/2078856/000119312526369668/purr-ex99_2.htm ；https://crypto.news/hype-drops-4-to-87-as-team-starts-330m-token-deal/ |
| **解锁抛压争论** | 白皮书口径每月 9.92M HYPE，但 Tokenomist 指出实际 claim 远小：4 月实际 claim ~33 万枚；**10/6 "纸面 9.9M、实际 3.75M 于 9/30 开始 unstake"**——解锁日历长期高估真实抛压，是近月争论最激烈的技术点 | https://www.tokenomist.ai/research/hype-tokenomics-330k-or-9-9m-hype-unlocks ；https://financefreedompath.com/2026/10/06/hyperliquids-october-6-unlock-9-9m-hype-on-paper-3-75m/ |
| **JELLY "validator put" 阴影** | 2025-03-26 JELLYJELLY 被恶意操纵时 validators 2 分钟内紧急投票下架、以攻击者开空价 $0.0095 强平所有仓位、HLP 反而"赚"$70 万——Blockworks 称 **"validator put"**；社区至今质疑"交易所可以且会推翻市场价格"的结算终局性；2026-08-24 又有 7 个资产（CASHCAT 等）被打 delist 推荐标签 | https://blockworks.com/news/hyperliquid-decentralization-validator-put ；https://rekt.news/hyperliquidate2 |
| **HIP-5 被否决** | HIP-5 提议从回购基金切一部分补贴 HyperEVM 生态项目币，**被社区压倒性否决/质疑**——社区认为回购现金流是 HYPE 唯一支撑，不能分流；说明当前 HYPE 价格完全靠 HyperCore 回购支撑、无余力反哺 HyperEVM | https://www.panewslab.com/en/articles/d9ed59b2-1003-462d-8585-f5d6c7bed144 |
| **10-08 销毁投票** | **Hyperliquid Foundation 发起：将 Assistance Fund 所持全部 HYPE 永久销毁**（而非继续回购），**2026-10-08 刚启动正式投票**（具体 HIP 编号待确认） | https://coinstats.app/news/6b05720a655a47f25a9569f87827a8cbef275081775a90c6e1cd891bff638445_HYPE-Tokens-Burn-The-Bold-Proposal-to-Permanently-Remove-Aid-Fund-Supply/ |

### 4.4 社区氛围对比（一句话）

> r/bittensor_ 是"研究型 hodler 小圈子"（周访客约 1.6K、热门帖仅十几赞、讨论治理叙事），而 r/hyperliquid 是**"交易员/量化 degen 大街"**——内容围绕 RWA perps 开单、自动交易 agent、解锁抛压和 OTC 博弈，帖子大量外溢到 r/CryptoCurrency 等大盘版，投机浓度和噪音显著更高。

---

## 五、KOL 与市场情绪指标

> 窗口：2026-09-19 至 2026-10-09。多空并陈。

### 5.1 恐惧贪婪指数（alternative.me API 一手拉取）

| 日期 | 值 | 分类 |
|---|---|---|
| **2026-10-09（今日）** | **59** | Greed |
| 2026-10-08 | 64 | Greed |
| 2026-10-07 | 71 | Greed |
| 2026-10-06 | 73 | Greed |
| 2026-10-05 | 70 | Greed |
| 2026-10-01 | 74 | Greed |
| 2026-09-22（近月峰值） | **78** | **Extreme Greed** |
| 2026-09-17 | 50 | Neutral（近月最低） |

- **趋势**：从 9/22 Extreme Greed **78 连续回落至今日 59（−19 点）**，10/7–10/9 三天内 71→64→59 加速降温，与 HYPE 从 $93 回落至 $85 同步。来源：https://api.alternative.me/fng/?limit=35

### 5.2 HYPE 衍生品硬指标

| 指标 | 数值 | 时间 / 来源 |
|---|---|---|
| 现价 | **$85.25**（24h −2.46%） | 2026-10-09，https://api.coingecko.com/api/v3/simple/price?ids=hyperliquid |
| 7d 涨跌 | **−3.83%** | Coinglass，2026-10-04，https://www.coinglass.com/zh/currencies/HYPE |
| ATH / 距 ATH 回调 | $97.96（2026-09-23）/ **~13–14%** | DefiLlama |
| **永续资金费率** | **+1.00 bps（年化 +10.95%）** | Hyperliquid，2026-10-08，AInvest 转述 |
| **HYPE Perp 未平仓量（OI）** | **$1.67B** | Hyperliquid，2026-10-08 |
| **24h 全平台清算** | **$179.75M** | DefiLlama，2026-10-08 |
| **7d 全平台清算** | **$369.61M** | DefiLlama |
| 鲸鱼持仓（全平台） | $9.108B，**多空比 0.87（偏空）** | Coinglass via CoinTime，https://www.cointime.ai/flash-news/data-22808 |
| 日手续费收入 | $2.71–3.43M（99% 流向 Assistance Fund 回购） | DefiLlama / CoinGlass |

> 注：用户指定的 DefiLlama prices API `coingecko:hyperliquid` slug 本次返回 **404**（已变更），现价改用 CoinGecko 官方 API + AInvest/HL oracle 交叉验证。

### 5.3 关键价位地图

| 类型 | 价位 | 依据 |
|---|---|---|
| **多空分水岭** | **$87.50** | AInvest：收复则重启上行 |
| 强支撑 | $84–85（此前买盘密集区）/ $82–83 / $80.54–81.25 | 破 $80.50 则看 $75 |
| 破位下行目标 | $75–76（EMA-100 / 楔形下轨） | CoinCodex/FXEmpire 模型均指向 −17% |
| 上方阻力 | $89.9–91（已跌破）/ $90–92 / $93.75 / $95 清算密集区 | Bybit TradeGPT |
| 心理目标 | $100（整数关）→ 通道上沿 $110–116 | Invezz / KryptoNews |

### 5.4 KOL / 模型观点表（多空并陈）

| # | 来源 | 一句话观点 | 关键价位 | 日期 | 链接 |
|---|---|---|---|---|---|
| 1 | **AInvest** | 中期谨慎看多，短期中性偏空；**$87.50 收复是多空分水岭**；$340M OTC 若机构长期锁仓则结构性利多 | 支撑 $82–83 / 阻力 $87.50、$90–92；突破 $110–116 | 10-08/09 | https://www.ainvest.com/news/hyperliquid-treasury-buybacks-340m-unlock-hype-flywheel-hold-october-9-2026-2610/ |
| 2 | **CoinCodex**（算法） | **短期看空**：预计 10/13 前跌至 $69.71（−17%），均值回归 | 目标 $69.71 | 10-08 | https://coincodex.com/article/93312/hyperliquid-prediction-october-08-2026/ |
| 3 | **Invezz** | 看多 $100；Bloomberg Terminal + $14.6M 回购燃料双催化；站上 20/50/100 EMA | 目标 $100；阻力 $97.70 | 10-06 | https://invezz.com/en-ae/news/2026/10/06/hype-eyes-dollar100-after-bloomberg-terminal-listing-and-fresh-dollar146m-buyback-fuel/ |
| 4 | **Bybit TradeGPT** | 短期偏空：解锁+OTC+获利盘致 7 天抛压；**已跌破 $89.9–91 支撑** | 支撑 $82 | 10-09 | https://www.bybitglobal.com/zh-MY/price/hyperliquid/ |
| 5 | **FXEmpire** | 宽楔形看跌：触及 $90 目标后回调，风险下行 −17% | 目标 $75–76；EMA-50 $83.75 | 10-08 | https://www.fxempire.it/forecasts/article/previsioni-prezzo-hype-hyperliquid-rischia-un-calo-del-17-dopo-il-raggiungimento-dellobiettivo-di-90-280031 |
| 6 | **528btc / 币界网** | 即时支撑 $87–88，关键支撑 $84–85；破 $84 看 $80–82，再下 $75 | 支撑 $84–85 / $80–82 / $75 | 10-08 | https://www.528btc.com/news/128409946.html |
| 7 | **DiarioBitcoin** | 价格跌破 SMA-7 与 SMA-15，短期趋势恶化；RSI 49.7，中性偏空 | 支撑 $87.52；阻力 $95.20 | 10-08 | https://www.diariobitcoin.com/analisis/hype-cae-607-el-8-de-octubre-de-2026-y-pone-a-prueba-soportes/ |
| 8 | **Aksel Kibar / Tech Charts**（新浪转引） | 日线"突破—回撤—续涨"形态，突破 $89 后进入无历史卖压的价格发现阶段 | 中期目标 $100.5；支撑 $76.6 | 09-19 | https://finance.sina.com.cn/stock/hkstock/hkstocknews/2026-09-19/doc-inisinhc2635733.shtml.md |
| 9 | **Brave New Coin / MetaTrader** | 多头结构在 $92 上方保持，有效突破后看 $100 | 阻力 $92–94；目标 $100 | 10-05 | https://www.metatrader.com/en/news/brave-new-coin/4315292-hyperliquid-hype-price-prediction-hype-eyes-100-as |
| 10 | **KryptoNews** | $10M 销毁 + 供应收缩叙事下看 $110 | 目标 $110 | 10-07 | https://forex.9xa.de/2026/10/07/hyperliquid-hype-price-targets-110-as-10m-burns-amid-supply-risk/ |

**多空汇总**：多头共识 $84–85 是需求密集区、$87.50 收复重启上行、回购飞轮年化 >$1B 构成结构性买盘；空头共识 $330M OTC（1.7% 流通盘）是近期最大供给悬顶、资金费率仅 +10.95% APY 无极端拥挤、鲸鱼多空比 0.87 偏空、模型指向 −17% 回调至 $75–76。

---

## 六、生态与机构化落地

### 6.1 HyperEVM / L1 主要 dApp（DefiLlama API 直拉，2026-10-09）

> 接口 `GET https://api.llama.fi/protocols`，过滤 chains 含 "Hyperliquid L1"，共命中 198 个协议。**口径提醒**：`/protocols` 返回跨链总 TVL，多链部署项目的数字被其他链放大，不能当作 HyperEVM 体量。

**（a）HyperEVM 原生 dApp Top（更可信）**：

| 排名 | 项目 | 类别 | TVL | 备注 |
|---|---|---|---|---|
| 1 | **Kinetiq kHYPE** | Liquid Staking | $946.2M | 最大 HYPE LST |
| 2 | **HyperLend Pooled** | Lending 借贷 | $361.4M | HyperEVM 原生借贷池 |
| 3 | **stHYPE** | Liquid Staking | $193.8M | 第二大 HYPE LST |
| 4 | Hyperliquid HLP | Derivatives 保险基金 | $179.8M | 协议自身 perp 保险池 |
| 5 | Hyperliquid Spot Orderbook | DEX 现货订单簿 | $163.7M | 官方现货 |
| 6 | Reservoir Protocol | CDP 稳定币 | $70.1M | HyperEVM 原生 CDP |
| 7 | Kinetiq kmHYPE | Liquid Staking | $44.3M | Kinetiq 衍生品 |
| 8 | Felix CDP | CDP | $29.2M | 原生 CDP |
| 9 | Hyperbeat LST | Liquid Staking | $12.8M | 新兴 LST |
| 10 | HypurrFi Pooled | Lending | $5.2M | 原生借贷 |

> 来源：https://api.llama.fi/protocols （2026-10-09 直拉）；链 TVL 口径 `/v2/chains` 显示 Hyperliquid L1 ≈ $1.047B。稳定币/CDP 赛道原生规模仍小——**HyperEVM 生态目前以 LST（HYPE 质押）+ 官方 perp/spot 为主，借贷与稳定币仍在早期**。

### 6.2 HIP-3 permissionless perps 与市占

| 指标 | 数值 / 进展 | 时间 | 来源 |
|---|---|---|---|
| 平台总 perp OI | **突破 $10B**（Talos 称 Hyperliquid 为 perp 第三大交易所）；10 月初约 $8.5B | 2026-06 / 10-02 | https://marketwirenews.com/stock/crcl/news/hyperliquid-open-interest-tops-10b-as-perps-move-int-5931291886229662.html |
| RWA perps OI | 2026-06 创纪录 **$3B**；全市场 RWA perps OI 10 月达 $5.78B，**Hyperliquid 一家份额约 80%** | 2026-06-02 / 10-07 | https://financefeeds.com/es/perps-rwa-interes-abierto-578b/ |
| 持仓数量 | **435,564 个 open positions**，2026 年翻倍创历史新高 | 2026-10-06 | https://www.cryptopolitan.com/es/hyperliquid-open-positions-record/ |
| 资产结构 | 2026 Q2 起 RWA perps 月成交量首次追平并超过加密 perps（$107.6B）；7 月黄金+股票占成交量 51% | 2026 全年 | https://coinmarketman.com/ru/blog/for-the-first-time-hyperliquid-traded-more-rwas-than-crypto/ |
| **市占** | Hyperliquid 占全部 perp DEX OI 的 **64%** | 2026-08 | https://www.sec.gov/Archives/edgar/data/2078856/000119312526369668/purr-ex99_2.htm |
| HIP-4 预测市场 | 2026-05 首个 CPI 宏观事件市场；2026-07-20 开放 permissionless 部署（50 万 HYPE 质押 + validator 模板审核） | 2026-05 / 07 | https://crypto.news/hyperliquid-debuts-cpi-prediction-market-with-hip-4-outcome-contracts/ |

### 6.3 机构化最新进展（聚焦 2026-09 ~ 10）—— 与原报告"S-1 待批"基线冲突

| 事项 | 状态 | 时间 | 来源 |
|---|---|---|---|
| **Bitwise 现货 HYPE ETF（BHYP）** | **已上线**（非"S-1 待批"）：Bitwise 2026-05-14 推出 Spot Hyperliquid ETF (BHYP)，含质押奖励；首发吸金量占流通盘 1.04%，为当年最强加密 ETF 首发 | 2026-05-14 | https://bitwiseinvestments.com/newsroom |
| **Grayscale HYPE 质押 ETF（HYPG）** | **已在 Nasdaq 挂牌**，被动跟踪 HYPE 并分配质押奖励 | 2026-06-18 | https://www.nasdaq.com/solutions/nasdaq-etf-listings |
| **Coinbase HYPE perp 期货** | Coinbase Derivatives 已按 CFTC Reg 40.2(a) 自我认证 **HYPE Perp Style Futures**，自 **2026-06-08** 起交易（提交编号 #2026-33）——**已上线，非"待批"** | 2026-06-08 | 背景见 https://www.willkie.com/-/media/files/publications/2026/06/cftcreleasesprioritizeusderivativesmarketdevelopmentincludingaccesstocryptoperpetuals.pdf |
| **Kraken / Bitnomial 美国合规 HIP-3 市场** | Grayscale 披露：Kraken 计划通过 Payward 旗下 CFTC 监管的 Bitnomial，向美国客户提供 permissioned Hyperliquid HIP-3 链上 perp（待监管批准） | 2026-09-21 | https://www.grayscale.com/the-stack/hyperliquid-coming-onshore-via-kraken |
| **Bloomberg Terminal** | Hyperliquid perp 合约数据已上线 Bloomberg Terminal，机构客户可直接监控 | 2026-10-05 | https://altcoingordon.com/hyperliquid-perpetual-contract-data-goes-live-bloomberg-terminal/ |
| **上市公司敞口（现代码 PURR）** | Hyperliquid Strategies Inc（**Nasdaq: PURR**；原报告"HSTI"为旧代码/笔误）：FY2026（截至 6/30）持仓 29.3M HYPE、现金 $149.9M、零负债；**2026-10-05 再买 1.9M HYPE（$167M），总持仓逼近 37M HYPE（≈$3.26B）**；机构持仓数一季度 +122% 至 202 家（BlackRock、State Street 为最大持有人）；已上线 Unit validator（全网第三大） | 2026-08-27 / 10-05 | https://www.sec.gov/Archives/edgar/data/2078856/000119312526369668/purr-ex99_2.htm |

---

## 七、对原报告的修正与补充

> 编号列出，每条标注【补充】/【修正】。原报告为 `hype_deep_research_20261009.md/html`，本节不改动原文，仅列差异。

1. **【修正】机构化进度：ETF 已获批上线，而非"S-1 待批"。** 原报告标签写"Bitwise/21Shares HYPE ETF S-1 待批"、时间线写"2026-03 递交 S-1"。一手数据显示：Bitwise 现货 HYPE ETF **BHYP 已于 2026-05-14 上线**（含质押奖励、当年最强加密 ETF 首发）；Grayscale 质押 ETF **HYPG 已于 2026-06-18 在 Nasdaq 挂牌**；Coinbase HYPE perp 期货**已于 2026-06-08 上线交易**（CFTC 自我认证 #2026-33）。原报告"待批"判断已过时。来源：https://bitwiseinvestments.com/newsroom ；https://www.nasdaq.com/solutions/nasdaq-etf-listings

2. **【修正】上市公司代码应为 PURR，而非 HSTI。** 原报告时间线写"Hyperliquid Strategies Inc（HSTI）登陆 NASDAQ"。现交易代码为 **PURR**（HSTI 应为旧代码/笔误）；截至 2026-10-05 总持仓逼近 **37M HYPE（≈$3.26B）**，机构持仓数一季度 +122% 至 202 家。来源：https://www.sec.gov/Archives/edgar/data/2078856/000119312526369668/purr-ex99_2.htm

3. **【补充】收入动能回落：TTM 协议收入 $706.8M，较 2025 日历年 ~$0.9B 回落约 21%。** 原报告基线"2025 协议收入 ~$843M–$1.0B、run-rate $3–3.5M/天"。本次 DefiLlama TTM Revenue 实测 **$706.8M**（24h $2.45M / 30d $73.59M），年化较峰值回落约 21%；AInvest 另指出 91% 收入来自 0.045% 竞争性 taker 费 + 流动性返佣，HIP-3 部署者抽走 18% 费用、分流约 50% 回购来源——**交易量纪录下收入质量在恶化**。来源：https://api.llama.fi/summary/fees/hyperliquid ；https://www.ainvest.com/news/hyperliquid-real-money-volume-record-hiding-revenue-problem-2609/

4. **【补充】生态层 TVL 失血：HyperEVM 链 TVL $1.047B，30 天 −28.8%。** 原报告只给协议总 TVL $7.04B。本次拆分：协议层 TVL 近 30 天 +3.15%，但**链上 DeFi TVL（HyperEVM 生态）近 30 天 −28.8%（7 天 −11.3%）**——生态应用层资金在撤，DEX 核心仓位仍稳。来源：https://api.llama.fi/v2/historicalChainTvl/Hyperliquid

5. **【修正】GitHub 官方组织名是 `hyperliquid-dex`，不是 `hyperliquidxyz`。** `hyperliquidxyz` 是一个非官方 User 账号（仅 2 个 0 星空仓）。官方组织 11 个 public repos、合计 3,137★、1,558 followers；对外主力 SDK `hyperliquid-python-sdk` 1,846★。来源：https://api.github.com/orgs/hyperliquid-dex

6. **【补充】SDK Release 已停滞约 4 个月。** 官方 Python SDK 最新版 **0.24.0 发布于 2026-06-04**（multisig userSetAbstraction），此后至 10-09 无新 release；node 与 order_book_server 均不打 GitHub Release（运行时靠链上升级）。来源：https://api.github.com/repos/hyperliquid-dex/hyperliquid-python-sdk/releases?per_page=10

7. **【补充】HIP-5 被社区否决 + 10-08 新销毁投票。** HIP-5（从回购基金切一部分补贴 HyperEVM 生态币）被社区压倒性否决——说明 HYPE 价格完全靠 HyperCore 回购支撑、无余力反哺生态。**2026-10-08 基金会新发起"将 Assistance Fund 全部持仓永久销毁"正式投票**（HIP 编号待确认），治理层正在调整回购/销毁框架。来源：https://www.panewslab.com/en/articles/d9ed59b2-1003-462d-8585-f5d6c7bed144 ；https://coinstats.app/news/6b05720a655a47f25a9569f87827a8cbef275081775a90c6e1cd891bff638445_HYPE-Tokens-Burn-The-Bold-Proposal-to-Permanently-Remove-Aid-Fund-Supply/

8. **【补充】Foundation 自营验证者集中度 47.2%。** Active Stake 439.94M HYPE（99.99% 质押率），活跃验证者 27/35；Hyper Foundation 自营 5 个验证者合计 **207.83M HYPE，占全网质押 47.2%**——去中心化进度有限。来源：https://hypurrscan.io/validators ；https://hypurrscan.io/staking

9. **【补充】Buyback TWAP 当周实时在跑 + 首笔 AQAv2 储备收益 $14.58M 到账。** 截至 10-09 dashboard 有两笔 BUY HYPE TWAP（合计 ~35,000 HYPE / $2.5M）执行中；2026-10-03 起 AF USDC 储备（Aave v2）首笔利息 **$14.58M USDC** 到账；近期单笔销毁 112,580 HYPE（~$10.15M，10/5）。来源：https://hypurrscan.io/dashboard

10. **【补充】10-08 OTC 抛压与官方号 10 天静默。** 9/30 起 Labs 解押 3.75M HYPE（~$330M）OTC 卖给单一机构（不在公开市场抛售），10/8 传出当日 HYPE 跌约 4% 至 ~$87；@HyperliquidX 官方号自 9/30 起至 10/9 **已 10 天未发推**，10 月事件均经 Discord/媒体流出。来源：https://crypto.news/hype-drops-4-to-87-as-team-starts-330m-token-deal/

11. **【补充】市场情绪降温 + $87.50 多空分水岭。** 恐惧贪婪从 9/22 Extreme Greed **78 回落至 10/9 的 59**；资金费率仅 +1.00 bps（年化 +10.95%，无极端多头拥挤）；鲸鱼多空比 0.87 偏空；24h 全平台清算 $179.75M。**$87.50 收复是多空分水岭，破 $80.50 看 $75**。来源：https://api.alternative.me/fng/?limit=35 ；https://www.ainvest.com/news/hyperliquid-treasury-buybacks-340m-unlock-hype-flywheel-hold-october-9-2026-2610/

12. **【补充】Jeff Yan 在 Token2049 放话 Options 是下一产品。** Jeff Yan（CEO）2026-10-07/08 在新加坡 Token2049 表示 **Options（期权）将成为 HyperCore 上下一个产品组件**，基于 HIP-4 继承现货/订单簿/组合保证金，用 Perps 对冲 Delta。来源：https://www.digitaltoday.co.kr/en/view/112515/hyperliquid-ceo-says-few-capture-benefits-of-corporate-growth-criticises-wall-street

### 7.1 未被推翻的原报告结论
- 99% 手续费回流 buyback、1B 硬顶、零 VC、CLOB 订单簿模型：无新反证。
- JELLY 事件与 "validator put" 中心化尾部风险：本次社区讨论仍持续，原报告判断成立。
- 团队 238M HYPE vesting 抛压：实际 claim 远小于纸面（4 月 ~33 万枚、10 月 3.75M OTC），但多空争论仍在，维持原风险框架。

---

## 八、待验证事项（分片遗留缺口，原样列出，不补写）

1. **r/hyperliquid 订阅数与本周访客数未拿到**：Reddit 未登录 about.json 被网络安全拦截，第三方统计接口本次无返回。
2. **Reddit 本月 Top5 热门帖的精确赞/评论数未拿到**（reddlx 镜像只显示标题与 crosspost 关系）。
3. **Discord 频道原始消息未读取**（需登录），治理结论均来自官方文章/媒体/SEC 文件间接交叉。
4. **2026-10-06 解锁当日具体链上转移哈希/金额未获取成功**：搜索受限 + 官方 info API 422 + 浏览器实时 transfers 流未捕获大额。
5. **累计 buyback 烧毁 HYPE 最新数未获取成功**：未定位 burn 地址并拉取余额；仅观测到当前在执行的 TWAP buyback（原报告 ~46M）。
6. **链上质押 APR 数值未获取成功**：hypurrscan 前端只显示佣金费率（0–5%），不显示 APR；官方 info API stakingSummary/delegations 端点 422。
7. **FDV 当前值未获取成功**：DefiLlama `/protocol/hyperliquid` 返回 fdv 字段为空（原报告 $81.52B）。
8. **GitHub 组织级贡献者总数未获取成功**：`/orgs/hyperliquid-dex/contributors` 返回 404。
9. **User fees 口径拆分未获取成功**：DefiLlama 对 hyperliquid 未单独上报 userFees（接口返回占位值）。
10. **HIP-5 之后是否存在 HIP-7/HIP-8 等更新编号提案**：公开报道中未检出；2026-10-08 的 Assistance Fund 销毁投票**具体 HIP 编号待确认**。
11. **Hyperliquid 专属钓鱼/安全专项社区共识未拿到具体官方 URL**。
12. **@HyperliquidX 单条推文 status ID 未提取**：未登录只读时间线未渲染独立 status 链接，表格 URL 统一指向账号主页。
13. **资金费率 / OI / 清算为转述口径**：未直接拉 Coinglass 付费 API，数据来自 AInvest/DefiLlama 公开页面转述（2026-10-08 时点），可能与实时值有偏差。

---

> 本文件为 `hype_deep_research_20261009.html` 的浏览器一手补充，**不改动原报告**。所有数字来自 2026-10-09 实时页面/API，未取到项已如实标注。加密货币波动剧烈，本文件**不构成投资建议**。
