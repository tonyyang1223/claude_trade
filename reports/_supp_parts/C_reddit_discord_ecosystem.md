# C. Reddit 社区 / Discord 治理 / 生态与机构化补充采集

> 采集时间：2026-10-09（周五，UTC+8）
> 采集方式：general_search 公开网页 + DefiLlama 官方 API（`https://api.llama.fi/protocols`、`/v2/chains`）直连。
> 说明：Reddit 未登录态直连 `www.reddit.com/r/hyperliquid/about.json` 被网络安全层拦截（与 Bittensor 轮一致），Discord 需登录无法直接读频道历史；本节对这两部分均用搜索引擎/第三方镜像（reddlx）间接采集，**拿不到的数字明确标注"未获取"，不编造**。

---

## C1 Reddit（r/hyperliquid）

### C1.1 社区规模

| 指标 | 数值 | 状态 | 来源 |
|---|---|---|---|
| 订阅数（subscribers） | **未获取** | `reddit.com/r/hyperliquid/about.json` 直连被网络安全拦截；subredditstats 接口本次无返回。与 r/bittensor_（约 1.6K 周访客）相比，r/hyperliquid 帖文跨版（r/CryptoCurrency、r/algorand、r/solana）频率明显更高，估算体量显著大于 TAO 社区，但**无一手数字** | https://www.reddit.com/r/hyperliquid/ （被拦截） |
| 本周访客（weekly visitors） | **未获取** | 同上，未登录态看不到侧栏 | — |
| 社区活跃度旁证 | 热门帖被大量 crosspost 到 r/CryptoCurrency / r/algorand / r/solana / r/CryptoTradingBot；u/applezoid、u/StevenVinyl 等持续产出 Hyperliquid 主题长帖/视频 | reddlx 用户镜像页 | https://www.reddlx.com/author/applezoid ；https://www.reddlx.com/author/StevenVinyl |

### C1.2 本月（2026-09 中下旬 ~ 10 月初）热门帖 Top 5（经 reddlx 镜像 + 新闻交叉，赞/评论数未取到）

| # | 帖子标题（镜像可见） | 作者 | 时间 | 互动数据 | 核心信号 |
|---|---|---|---|---|---|
| 1 | **SpaceX Just Proved Hyperliquid's Biggest Bull Case**（视频帖） | u/applezoid | 约 21 天前（≈2026-09-18） | 未取到赞/评论数 | 把 SpaceX 上市/航天叙事与 Hyperliquid RWA perps（无中心化交易所也能交易"股票"）的看多逻辑绑定——**RWA 叙事是当前社区第一多头论据** |
| 2 | **THIS Is How You Do a Hyperliquid Price Prediction**（视频帖） | u/applezoid | 约 1 个月前（≈2026-09-09） | 未取到 | 价格预测类内容，KOL 持续输出 |
| 3 | **Dashboard that monitors seismograph stations near TSMC fabs and auto-shorts semiconductor perps on Hyperliquid** | u/StevenVinyl | 2026 年内（镜像页时间） | +1 crosspost 到 r/hyperliquid，另有 r/CryptoTradingBot 2 crosspost | 极客用户把 HIP-3 半导体 perps（NVDA/TSM/AMD）接入地震传感器自动做空——**permissionless perps 已被玩家用来做实物事件驱动策略**，社区"brainrot/degen"文化浓厚 |
| 4 | **How I run my Hyperliquid gambling AI quant**（自然语言 agent 自动交易） | u/StevenVinyl | 2026 年内 | crosspost r/CryptoTradingBot / r/algotradingcrypto | 社区重心在**自动化交易 agent / 量化 bot**，而非 hodl 讨论 |
| 5 | （新闻外溢热帖）**HYPE 跌至 $87，Hyperliquid Labs 启动约 $330M OTC 代币交易** | 非 Reddit 原帖，被广泛转引讨论 | 2026-10-08 | — | 团队解锁/OTC 抛压是本月社区最大空头焦虑点（见 C2.2） |

> 来源：https://reddlx.com/author/applezoid ；https://www.reddlx.com/author/StevenVinyl ；OTC 事件 https://crypto.news/hype-drops-4-to-87-as-team-starts-330m-token-deal/

### C1.3 社区核心话题盘点

| 话题 | 社区立场/讨论要点 | 来源 |
|---|---|---|
| **多空争议** | 多头：RWA perps OI 纪录、平台 OI 破 $10B、占全 perp DEX OI 64%（2026-08）、ETF 上市；空头：238M HYPE 团队仓每月解锁 vs 月回购仅 ~60 万枚 HYPE，10 月 8 日 $330M OTC 交易 HYPE 当日跌 4% 至 $87 | https://www.sec.gov/Archives/edgar/data/2078856/000119312526369668/purr-ex99_2.htm ；https://crypto.news/hype-drops-4-to-87-as-team-starts-330m-token-deal/ |
| **团队解锁抛压** | 白皮书口径每月 9.92M HYPE（≈$9 亿@$94），但 Tokenomist 指出实际 claim 远小于此：4 月实际 claim ~33 万枚；**10 月 6 日"纸面 9.9M、实际 3.75M 于 9 月 30 日开始 unstake"**——解锁日历长期高估真实抛压，这是社区近一个月争论最激烈的技术点 | https://www.tokenomist.ai/research/hype-tokenomics-330k-or-9-9m-hype-unlocks ；https://financefreedompath.com/2026/10/06/hyperliquids-october-6-unlock-9-9m-hype-on-paper-3-75m/ |
| **JELLY 事件后续** | 2025-03-26 JELLYJELLY 被恶意操纵时 validators 2 分钟内紧急投票下架、以攻击者开空价 $0.0095 强平所有仓位、HLP 反而"赚" $70 万——Blockworks 称之为 **"validator put"**，社区至今仍质疑"交易所可以且会推翻市场价格"的结算终局性；2026-08-24 又有 7 个资产（CASHCAT 等）被打上 delist 推荐标签，手动 delist 的去中心化性质疑反复出现 | https://blockworks.com/news/hyperliquid-decentralization-validator-put ；https://rekt.news/hyperliquidate2 ；https://hyperliquidguide.com/guides/trading/hyperliquid-delisting-explained |
| **手续费分配（99% 给 Assistance Fund 回购）** | 2025-08-26 起 99% 手续费归 Assistance Fund 用于 HYPE 回购；社区共识偏向"回购托底"，但 **HIP-5（提议从回购基金中切一部分补贴生态项目币）被社区压倒性否决/质疑**，说明当前 HYPE 价格完全靠 HyperCore 回购支撑、没有余力反哺 HyperEVM | https://www.panewslab.com/en/articles/d9ed59b2-1003-462d-8585-f5d6c7bed144 ；https://www.tronweekly.com/hype-buybacks-surge-14-58m-added-tops-900m/ |
| **治理讨论** | HIP-6（Hy-CO 链上拍卖发行）、HIP-4 预测市场 permissionless 化、2026-10-08 Assistance Fund 全部持仓永久销毁投票 | 见 C2 |

### C1.4 与 r/bittensor_ 氛围对比（一句话）

> r/bittensor_ 是"研究型 hodler 小圈子"（周访客约 1.6K、热门帖仅 16-19 赞、讨论治理与 subnet 叙事），而 r/hyperliquid 是**"交易员/量化 degen 大街"**——内容围绕 RWA perps 开单、自动交易 agent、解锁抛压和 OTC 博弈，帖子大量外溢到 r/CryptoCurrency 等大盘版，投机浓度和噪音都显著高于 TAO 社区。

---

## C2 Discord / 治理（HIP 系列）

> Discord 需登录，无法直接读 #announcements / #governance 历史；以下来自官方文章、媒体报道与 SEC 文件间接采集。

### C2.1 HIP 提案时间线（HIP-3 之后，聚焦 2026 下半年）

| HIP | 内容 | 时间 / 状态 | 来源 |
|---|---|---|---|
| HIP-3 | permissionless perps：任何人质押 50 万 HYPE（≈$30M）即可自建股票/商品/指数/FX perp 市场，部署者负责 oracle；恶意操作可被 slashing | 2025-10 上线；2026 持续每月 OI 新高 | https://hyperliquid.xyz/article/hip-3 ；https://coinpost.ai/en/topics/112121 |
| HIP-4 | outcome contracts（全抵押、到期 0/1 USDC 结算、无杠杆无清算）——预测市场/二元期权原语；先 canonical（validator 审核 sector），后 permissionless（同 HIP-3 质押门槛 50 万 HYPE，但需模板审核，validator 直布市场每年 ≤10 个） | 2026-05 首个 CPI 宏观事件市场；**2026-07-20 官方宣布 permissionless 部署规范** | https://crypto.news/hyperliquid-debuts-cpi-prediction-market-with-hip-4-outcome-contracts/ ；https://global.foresightnews.pro/article/16793 |
| **HIP-5** | 第三方提议：从 HYPE 回购基金中切一部分资金补贴 HyperEVM 生态项目币 | **被社区压倒性否决/质疑**（2026-05 前后）——社区认为回购现金流是 HYPE 唯一支撑，不能分流 | https://www.panewslab.com/en/articles/d9ed59b2-1003-462d-8585-f5d6c7bed144 |
| HIP-6 | **Hy-CO**：把 Uniswap 式拍卖搬到 HyperCore 订单簿，HIP-1 资产可在链上原生募资，募资款原子注入 HIP-2 流动性；50bp 协议费归 Aid Fund，代币分块释放防抢跑 | 2026-02-25 提交投票；2026-03 落地 | https://news.wikibit.com/en/202602279934406519.html ；https://www.panewslab.com/en/articles/019cacc0-87e6-73b8-a908-60c47d2c6b20 |
| （新投票，编号待确认） | **Hyperliquid Foundation 发起：将 Assistance Fund 所持全部 HYPE 永久销毁**（而非继续用于回购） | **2026-10-08 刚启动正式投票** | https://coinstats.app/news/6b05720a655a47f25a9569f87827a8cbef275081775a90c6e1cd891bff638445_HYPE-Tokens-Burn-The-Bold-Proposal-to-Permanently-Remove-Aid-Fund-Supply/ |

### C2.2 三大社区争议点

| 争议 | 事实与社区论点 | 来源 |
|---|---|---|
| **团队 238M vesting、每月 9.92M 解锁抛压** | Core Contributors 分配 238M HYPE（占 1B 上限 23.8%），1 年 cliff（2025-11 结束）后线性解锁 24 个月，白皮书口径 **9,916,667 HYPE/月**（@$94 ≈ $9.3 亿/月名义抛压）。Multicoin 报告称这是"主要稀释担忧"。**但实际 claim 远小于纸面**：4 月实际 claim ~33 万枚（$12M），10 月 6 日周期实际仅 375 万枚 unstake（9 月 30 日开始），因大量解锁币被重新质押而非卖出。月回购约 60 万枚 HYPE vs 月解锁 990 万枚纸面——飞轮能否对冲是多空核心 | https://cryptodaily.co.uk/2026/06/hype-june-6-unlock-absorb-supply ；https://members.delphidigital.io/reports/the-year-ahead-for-markets-2026 ；https://www.tokenomist.ai/research/hype-tokenomics-330k-or-9-9m-hype-unlocks ；https://financefreedompath.com/2026/10/06/hyperliquids-october-6-unlock-9-9m-hype-on-paper-3-75m/ ；https://m.jinse.com.cn/blockchain/3734906.html |
| **Assistance Fund 99% 手续费分配是否合理** | 2025-08-26 起手续费分配提至 99% 给 AF；截至 2026-10 累计回购已超 $9 亿；2026-10-03 起 AF USDC 储备（Aave v2）开始产生利息，首期 ~$14.58M USDC 利息划给回购。AInvest 指出隐患：**91% 收入来自 0.045% 竞争性 taker 费 + 流动性返佣，HIP-3 让部署者抽走 18% 费用、分流了 50% 的回购来源**——交易量纪录下收入质量在恶化。2026-10-08 进一步提议直接把 AF 持仓永久销毁，说明治理层也在调整回购/销毁框架 | https://www.ainvest.com/news/hyperliquid-real-money-volume-record-hiding-revenue-problem-2609/ ；https://cryptobriefing.com/hyperliquid-usdc-yield-hype-buybacks-2/ ；https://www.tronweekly.com/hype-buybacks-surge-14-58m-added-tops-900m/ |
| **JELLY 后"手动 delist"的去中心化性质疑** | JELLY 事件中 validators 2 分钟紧急投票下架、以非市价 $0.0095 强平，Blockworks 直接标题"A perp too far: Hyperliquid's 'validator put'"；Rekt 复盘称"Swift consensus in two minutes revealed who truly holds the power"。2025-03 起上线链上 delist 投票（质押权重 quorum 通过即自动下架），2026-08-24 又有 7 个资产被打 delist 推荐标签，并引用独立分析师 stalequant 的公开评分法——社区一边认可安全兜底，一边持续质疑结算终局性与"交易所可推翻市价"的中心化尾部风险 | https://blockworks.com/news/hyperliquid-decentralization-validator-put ；https://rekt.news/hyperliquidate2 ；https://hyperliquidguide.com/guides/trading/hyperliquid-delisting-explained |

### C2.3 钓鱼/安全提醒类社区共识

- **未检索到 Hyperliquid 专属的、2026 年下半年新发酵的钓鱼专项提醒**。通用共识（"公共频道支持、私信 DM 都是诈骗；官方不会主动 DM"）在 Discord/Telegram 各链社区一致，但本次采集未拿到 Hyperliquid 官方安全公告的具体 URL，**标注为未获取**。
- 旁证：HYPE 生态侧 2026-10 仍有大量"假客服/假充值"外溢风险（见 Propr 等 prop trading 社区反复强调只信公共频道）。来源：https://communityone.io/en/servers/1111607533883367535/propr/news/propr-hyperliquid-prop-trading-interview-2026-06-01/

---

## C3 生态与机构化

### C3.1 HyperEVM / Hyperliquid L1 上主要 dApp（DefiLlama API 直拉，2026-10-09）

> 接口：`GET https://api.llama.fi/protocols`，过滤 `chains` 含 "Hyperliquid L1"，共命中 198 个协议。
> **重要口径提醒**：`/protocols` 返回的是每个协议**跨链总 TVL**，不是 HyperEVM 单链 TVL。下表区分"HyperEVM 原生"与"多链部署"——后者（Morpho/Curve/Pendle/Euler/Cex/Bridge）的 TVL 数字被其他链放大，不能当作 HyperEVM 体量。

**（a）HyperEVM 原生 dApp Top（更可信）**

| 排名 | 项目 | 类别 | TVL（USDT，API 返回总值） | 备注 |
|---|---|---|---|---|
| 1 | **Kinetiq kHYPE** | Liquid Staking（HYPE 流动性质押） | $946.2M | 最大 HYPE LST |
| 2 | **HyperLend Pooled** | Lending 借贷 | $361.4M | HyperEVM 原生借贷池 |
| 3 | **stHYPE** | Liquid Staking | $193.8M | 第二大 HYPE LST |
| 4 | **Hyperliquid HLP** | Derivatives（保险基金） | $179.8M | 协议自身 perp 保险池 |
| 5 | **Hyperliquid Spot Orderbook** | DEX 现货订单簿 | $163.7M | 官方现货 |
| 6 | **Reservoir Protocol** | CDP 稳定币 | $70.1M | HyperEVM 原生 CDP |
| 7 | **Kinetiq kmHYPE** | Liquid Staking（流动版） | $44.3M | Kinetiq 衍生品 |
| 8 | **Hyperbeat LST** | Liquid Staking | $12.8M | 新兴 LST |
| 9 | **Felix CDP** | CDP | $29.2M | 原生 CDP |
| 10 | **HypurrFi Pooled** | Lending | $5.2M | 原生借贷 |

来源：https://api.llama.fi/protocols （2026-10-09 直拉）；链 TVL 口径：`/v2/chains` 显示 "Hyperliquid L1" 链 TVL ≈ **$1.047B**。

**（b）多链协议在 HyperEVM 有部署（TVL 为全链口径，仅作生态存在性参考）**

| 项目 | 类别 | API 显示 TVL（全链） |
|---|---|---|
| Morpho Blue | Lending | $11.11B（全链，非 HyperEVM 专属） |
| Curve DEX | Dexs | $1.24B（全链） |
| Pendle V2 | Yield | $1.21B（全链） |
| Euler V2 | Lending | $0.30B（全链） |
| LayerZero V2 / CCIP / Hyperliquid Bridge | Bridge | 桥 TVL 重复计入，不代表生态活跃度 |

> 稳定币/CDP 赛道原生规模仍小（Reservoir $70M、Felix $29M、Parallel/Delpho/Hyperstable 等均 <$1M 量级）——**HyperEVM 生态目前以 LST（HYPE 质押）+ 官方 perp/spot 为主，借贷与稳定币仍在早期**。

### C3.2 HIP-3 permissionless perps 新市场进展与 OI

| 指标 | 数值 / 进展 | 时间 | 来源 |
|---|---|---|---|
| 平台总 perp OI | **突破 $10B**（Talos 报告称 Hyperliquid 为 perp 第三大交易所）；10 月初约 $8.5B | 2026-06 / 2026-10-02 | https://marketwirenews.com/stock/crcl/news/hyperliquid-open-interest-tops-10b-as-perps-move-int-5931291886229662.html ；https://www.cryptela.com/en/crypto-news/420949/ |
| RWA perps OI | 2026-06 创纪录 **$3B**，HIP-3 上线后每月 OI 都创新高；全市场 RWA perps OI 10 月达 $5.78B，Hyperliquid 一家份额约 80% | 2026-06-02 / 2026-10-07 | https://coinpost.ai/en/topics/112121 ；https://financefeeds.com/es/perps-rwa-interes-abierto-578b/ |
| 持仓数量 | **435,564 个 open positions**，2026 年翻倍创历史新高 | 2026-10-06 | https://www.cryptopolitan.com/es/hyperliquid-open-positions-record/ ；https://www.altbtc.cc/story/hyperliquid-open-positions-double-in-2026-to-over-435k-ssSueW7 |
| 资产结构 | 上线后先股指、后贵金属领跑；2026-01-28 黄金 perp 跟到 $5,266/oz 历史价；7 月黄金+股票占 Hyperliquid 成交量 51%；**2026 Q2 起 RWA perps 月成交量首次追平并超过加密 perps**（$107.6B vs 加密下滑）；原油合约单日成交曾逼近 $20 亿 | 2026 全年 | https://static.pharosnetwork.xyz/doc/Perps_for_Everything_The_Ultimate_RWA_Liquidity_Solution_V1.pdf ；https://finyear.com/wp-content/uploads/2026/09/real-world-assets-caught-up-to-bitcoin.pdf ；https://coinmarketman.com/ru/blog/for-the-first-time-hyperliquid-traded-more-rwas-than-crypto/ |
| 市占 | Hyperliquid 占全部 perp DEX OI 的 **64%**（2026-08） | 2026-08 | https://www.sec.gov/Archives/edgar/data/2078856/000119312526369668/purr-ex99_2.htm |
| HIP-4 预测市场 | 2026-05 首个 CPI 宏观事件市场；2026-07-20 开放 permissionless 部署（50 万 HYPE 质押 + validator 模板审核，validator 直布 ≤10 个/年） | 2026-05 / 2026-07 | https://crypto.news/hyperliquid-debuts-cpi-prediction-market-with-hip-4-outcome-contracts/ ；https://global.foresightnews.pro/article/16793 |

### C3.3 机构化最新进展（聚焦 2026-09 ~ 10）

| 事项 | 状态 | 时间 | 来源 |
|---|---|---|---|
| **Bitwise 现货 HYPE ETF（BHYP）** | **已上线**（非"S-1 待批"）：Bitwise 于 2026-05-14 推出 Spot Hyperliquid ETF (BHYP)，含质押奖励；HYPE 现货 ETF 首发吸金量占流通盘 1.04%，为当年最强加密 ETF 首发（超过 BTC/ETH 首发） | 2026-05-14 | https://bitwiseinvestments.com/newsroom ；https://yellow.com/zh-tw/tag/hyperliquid?page=3 |
| **Grayscale HYPE 质押 ETF（HYPG）** | 已在 Nasdaq 挂牌，被动跟踪 HYPE 并分配质押奖励 | 2026-06-18 | https://www.nasdaq.com/solutions/nasdaq-etf-listings |
| **21Shares** | 与 Bitwise 合作 KEYS ETP（Top10 组合）；21Shares 全球研究主管 Ndinga 公开点评 Hyperliquid 生态（非单独 HYPE ETP 新进展） | 2026-09-30 | https://www.21shares.com/en-row/product/keys ；https://www.diariobitcoin.com/criptomonedas/hyperliquid-strategies-desafia-la-crisis-de-los-dat-con-ingresos-y-recompensas-en-hype/ |
| **Coinbase HYPE perp 期货** | Coinbase Derivatives 已按 CFTC Reg 40.2(a) 自我认证 **HYPE Perp Style Futures**，自 **2026-06-08** 起交易（提交编号 #2026-33）；即已上线，非"待批" | 2026-06-08 上线 | CFTC Portal 提交文件（无公开 URL，编号 #2026-33）；背景见 https://www.willkie.com/-/media/files/publications/2026/06/cftcreleasesprioritizeusderivativesmarketdevelopmentincludingaccesstocryptoperpetuals.pdf |
| **Kraken / Bitnomial 美国合规 HIP-3 市场** | Grayscale 披露：Kraken 计划通过 Payward 旗下 CFTC 监管的 Bitnomial 交易所，向美国客户提供 permissioned Hyperliquid HIP-3 链上 perp（待监管批准） | 2026-09-21 | https://www.grayscale.com/the-stack/hyperliquid-coming-onshore-via-kraken?partnerref=homepagehero |
| **Bloomberg Terminal** | Hyperliquid perp 合约数据已上线 Bloomberg Terminal，机构客户可直接监控价格与活动 | 2026-10-05 | https://altcoingordon.com/hyperliquid-perpetual-contract-data-goes-live-bloomberg-terminal/ |
| **上市公司敞口（HSTI → 现代码 PURR）** | Hyperliquid Strategies Inc（**Nasdaq: PURR**；基线"HSTI"应为旧代码/笔误，现交易代码为 PURR）：FY2026（截至 6/30）持仓从 12.5M 增至 **29.3M HYPE**、现金 $149.9M、零负债；2026-09-01 披露 29.4M HYPE + $133M 现金；**2026-10-05 再买 1.9M HYPE（$167M），总持仓逼近 37M HYPE（≈$3.26B）**；机构持仓数一季度 +122% 至 202 家（BlackRock、State Street 为最大持有人）；已上线 Unit validator（全网第三大验证者） | 2026-08-27 / 2026-10-05 | https://www.tmcnet.com/usubmit/2026/08/27/10436299.htm ；https://www.sec.gov/Archives/edgar/data/2078856/000119312526369668/purr-ex99_2.htm ；https://pulseofnations.lol/hyperliquid-strategies-3/ ；https://www.nasdaq.com/articles/institutional-investors-are-buying-hyperliquid-strategies-should-you |

---

## 采集缺口（诚实声明）

1. r/hyperliquid **订阅数与本周访客数未拿到**：Reddit 未登录 about.json 被网络安全拦截，第三方统计接口本次无返回。
2. Reddit 本月 Top5 热门帖的**精确赞/评论数未拿到**（reddlx 镜像只显示标题与 crosspost 关系）。
3. Discord 频道原始消息未读取（需登录），治理结论均来自官方文章/媒体/SEC 文件间接交叉。
4. HIP-5 之后是否存在 HIP-7/HIP-8 等更新编号提案，公开报道中未检出；2026-10-08 的 Assistance Fund 销毁投票**具体 HIP 编号待确认**。
5. Hyperliquid 专属钓鱼/安全专项社区共识未拿到具体官方 URL。
