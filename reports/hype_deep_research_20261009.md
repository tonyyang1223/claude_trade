# Hyperliquid (HYPE) 深度投研摘要

> 整理时间：2026-10-09 · 赛道：去中心化永续合约 DEX / 自研 L1 第一梯队
> 完整 HTML 报告：`reports/hype_deep_research_20261009.html`

---

## 一、核心指标快照（2026-10-09）

| 指标 | 数值 |
|---|---|
| 当前价格 | **~$85.30** |
| 市值 MC | **$18.98B** |
| FDV | **$81.52B**（DEX 赛道第一） |
| 流通量 / 上限 | 222.45M / 1,000M（**流通率 23.3%**） |
| ATH | $97.96（2026-09-23，距今仅 16 天），当前 **−12.9%** |
| ATL | ~$3.57（2024-11-29 genesis airdrop 开盘价） |
| TVL（DefiLlama） | **$7.04B**（去中心化永续赛道绝对龙头） |
| 24h 交易量 | ~$1.085B（链上现货+永续口径） |
| Staked HYPE | ~436–440M（占总量 ~44%） |
| Staking APR | **~2.1–2.37%**（400M staked 时） |
| 2025 协议收入 | **~$843M – $1.0B**（run-rate $3–3.5M/天） |
| 累计 Buyback | ~46M HYPE / $1.3B+（已永久烧毁） |

---

## 二、项目一句话定位

Hyperliquid 是一条**为高吞吐交易而生的自研 L1 区块链**（HyperBFT 共识，~1 秒出块），原生承载 **HyperCore 订单簿永续合约交易所**（CLOB 模型，非 AMM），并通过 2025-02 上线的 **HyperEVM** 兼容 Solidity 智能合约。它不是"在 Ethereum 上搭 DEX"，而是**自己做一条链 + 自己做撮合引擎**，以 ~11 人零 VC 团队吃下了链上永续 60–70% 的市场份额。

**关键标签**：零 VC · 无 ICO · 1B 硬顶 · 99% 手续费回流 buyback · 订单簿 CLOB · 团队 ex-HRT/Chameleon · Bitwise/21Shares HYPE ETF S-1 待批。

---

## 三、历史关键节点

| 日期 | 事件 | 意义 |
|---|---|---|
| 2022 | Jeff Yan（Harvard Math+CS，ex-HRT quant，Chameleon Trading 创始人）自筹创立 Hyperliquid Labs | 用做市利润 self-fund，零 VC |
| 2023 | **HyperCore 主网上线**（HyperBFT L1 + 永续订单簿） | 早期仅邀请制，积累交易数据 |
| 2024-11-29 | **Genesis Airdrop**：310M HYPE（31%）空投给 ~94,000 早期用户，无需申领自动到账 | 开盘价 ~$3.57，历史最大空投之一 |
| 2024-12-03 | 历史最大单日振幅 47.92% | 空投后早期投机剧烈波动 |
| 2024-12-23 | <span class="risk">MetaMask 安全研究员 Taylor Monahan 曝光 DPRK/Lazarus 关联钱包自 10 月起在平台交易</span> | 30 小时净撤资 $256M+，单日流出 $502.7M；团队否认被黑，强调"无安全漏洞" |
| 2025-02-18 | **HyperEVM 主网上线** | 从单币 DEX 升级为可编程金融生态（借贷/稳定币/LST） |
| 2025-03-26 | <span class="risk">JELLY 事件：攻击者用 ~$3M 在小盘 meme 上拉盘 400%+，制造 ~$13.5M HLP 亏损</span> | 团队手动冻结、delist JELLY 永续并强制按标记价结算——"去中心化"叙事受重创 |
| 2025-04-21 | Validator set 转为 permissionless | 任何足够质押的方可运行节点 |
| 2025-08-26 | 手续费 → Assistance Fund 比例从 97% **提升至 99%** | 协议收入几乎全部回流买币 |
| 2025-10 | **HIP-3** permissionless perps 上线 | 任何人可部署商品/股指永续市场 |
| 2025-11-29 | **核心贡献者 238M HYPE 开始 vesting**（1 年 cliff 后 24 个月线性解锁，每月 9.92M） | 抛压闸门正式打开 |
| 2025-12 | Hyperliquid Strategies Inc（HSTI）登陆 NASDAQ；验证者投票永久烧毁 Assistance Fund 持有的 ~37M HYPE | 上市公司敞口 + 通缩机制硬化 |
| 2026-02 | HIP-4 prediction markets 引入 | 预测市场赛道扩展 |
| 2026-03 | HIP-3 OI 达 $1.2B 纪录；合规 S&P 500 永续上线；**Bitwise / 21Shares 递交 HYPE ETF S-1** | 机构化管线启动 |
| 2026-05 | MC 短暂突破 $14B，进入 CMC Top 10，一度超越 Dogecoin | 代币市值进入主流视野 |
| 2026-08-26 | 单日涨 ~4%，周涨 43%，逼近前高 | 机构资金流入预期升温 |
| 2026-09-23 | **ATH $97.96–97.98**（FDV ~$98B） | 距当前仅 16 天 |
| 2026-09-28 | Gemini 上线 HYPE staking（2.1% APY） | 中心化托管质押渠道开放 |
| 2026-10 | Coinbase Derivatives 向 CFTC 递交 HYPE 永续期货认证 | 合规期货管道 |

---

## 四、最近情况（2025 – 2026-10）

- **收入飞轮已跑通**：2025 年协议手续费 ~$843M（部分口径 $1.0B+），其中 99% 流入 Assistance Fund 持续 buyback HYPE，累计已买入并烧毁 ~46M HYPE（占初始供应 4.6%）。这是加密行业**规模最大、比例最激进的 buyback 机制**。
- **生态扩张**：HyperEVM（2025-02）+ HIP-3 permissionless perps（2025-10）+ HIP-4 prediction markets（2026-02）+ 合规 S&P 500 永续（2026-03）——从单一 BTC/ETH 永续扩展到股票指数、商品、预测市场。
- **机构化加速**：Bitwise/21Shares HYPE ETF S-1（2026-03）、Coinbase HYPE 期货 CFTC 认证（2026-10）、Gemini staking（2026-09）、HSTI 在 NASDAQ 上市（2025-12）、Hyperion DeFi 成为首个公开市场 HYPE 国库股。
- **垄断地位**：链上永续市场份额 60–70%，TVL $7B 是 GMX（~$178–240M）的 ~29 倍、dYdX（~$128M）的 ~55 倍；HYPE MC $19B 是 DYDX（$115M）+ GMX（$85M）总和的 ~100 倍。
- **监管阴云未散**：2024-12 DPRK 指控后，OFAC 对 DPRK 相关交易的执法是悬顶之剑；JELLY 事件暴露的"团队可手动 delist/强平"也与去中心化叙事相悖。

---

## 五、代币经济（Tokenomics）

| 维度 | 数值 / 说明 |
|---|---|
| 总量上限 | **1,000,000,000 HYPE**（硬顶，SEC 文件确认不再增发） |
| 当前流通 | ~222.45M（23.3%） |
| **分配** | ① **31% (310M)** Genesis airdrop，2024-11-29 一次性解锁；② **38.9% (388.9M)** 未来社区发行 / staking 奖励 / ecosystem；③ **23.8% (238M)** 核心贡献者；④ **6% (60M)** Hyper Foundation |
| 团队 vesting | 1 年 cliff（2024-11-29 → 2025-11-29），之后 **24 个月线性解锁，每月 9.92M HYPE**（每月 6 号），预计 2027-11 完成 |
| 已烧毁 | ~46M HYPE（Assistance Fund buyback + 2025-12 永久烧毁投票） |
| Staking | 委托给 24+ 验证者，奖励率 ∝ 1/√(总质押量)；400M staked 时 ~2.37% APR，2026-08 实测 436M staked 时 **2.17%**；奖励来自 future emissions reserve（非手续费） |
| Unbonding | 1 天 lock + 7 天 queue = 8 天 |
| 手续费回流 | **99% 协议手续费 → Assistance Fund → 市价 buyback HYPE**；2025-08-26 从 97% 提到 99% |
| 协议收入 | 2025 年 ~$843M–$1.0B；2025-10 run-rate $3–3.5M/天；年 buyback 规模 ~$479M（按当时价） |
| 治理 | 验证者链上投票（如 2025-12 烧毁 Assistance Fund 持仓即投票通过）；HYPE 质押者参与 |

**关键稀释算术**：
- 当前流通 222.45M。
- 团队解锁：从 2026-10 到 2027-11 还有 ~13 个月 × 9.92M = **~129M HYPE** 将解锁。
- Buyback burn：按当前价 ~$85 计算，年 buyback $1.0B ≈ **11.8M HYPE/年**，3 年 ~35M。
- Staking emissions：38.9% reserve 中持续释放，但主要被 440M staked 的人吃掉，净进入流通的增量有限。
- **3 年后流通量 ≈ 222 + 129（团队）− 35（burn）≈ 316M**（流通率从 23.3% → ~33%）。
- 若 MC 维持 $19B 不变，纯稀释 alone 把价格压到 **$60**（−29%）；想守住 $85，MC 必须扩到 $26.9B（+42%）。

---

## 六、估值区间（三档情景）

基准价 $85.30 · MC $18.98B · FDV $81.52B · 2025 收入 ~$0.9B · **P/S (MC) ≈ 21x，P/S (FDV) ≈ 90x**。

| 情景 | 目标价 | 对应 MC | 对应 FDV | 较当前 |
|---|---|---|---|---|
| 🔻 **悲观** | **$25 – $45** | $7.9B – $14.2B | $25B – $45B | **−71% ~ −47%** |
| 🟡 **中性** | **$80 – $130** | $25.3B – $41.1B | $80B – $130B | **−6% ~ +52%** |
| 🟢 **乐观** | **$180 – $260** | $57B – $82B | $180B – $260B | **+111% ~ +205%** |

**核心假设**：

- **悲观**：DPRK/OFAC 执法落地（Coinbase/Binance 被迫 delist 美国用户访问）；2027-11 前每月 9.92M 团队解锁抛压持续；DEX 永续赛道被 CEX（Binance/OKX）+ Starknet edgeX 等新竞争者分流；协议收入从 $0.9B 腰斩到 $0.4B；P/S 杀到 15–20x。
- **中性**：HYPE ETF 12–18 个月内获批（参考 IBIT 温和版溢价 1.2x）；协议收入维持 $1.0–1.2B；buyback 持续抵消团队解锁；P/S (MC) 维持 20–25x。
- **乐观**：ETF 获批并复制 IBIT 式资金流入；HyperEVM + HIP-3 生态收入复合到 $2B+；永续垄断地位延续；FDV P/S 维持 40–50x（对标高成长 SaaS 而非 CEX）；机构将 HYPE 列为"加密蓝筹"与 SOL/AVAX 并列。

**对比锚点**：
- Binance 2024 收入 ~$4.5B，P/S ~5x；Coinbase 2024 收入 ~$6.6B，P/S ~12x。
- HYPE 当前 P/S (MC) 21x 已经高于 Coinbase，P/S (FDV) 90x 是 Binance 的 18 倍——估值靠"高增长 + 通缩 buyback + ETF 预期"支撑。

---

## 七、竞品对比（去中心化永续赛道）

| 项目 | 代币 | 价格 | MC | FDV | 流通率 | 距 ATH | TVL | 30d 量 | 价值捕获 | 贵贱判断 |
|---|---|---|---|---|---|---|---|---|---|---|
| **Hyperliquid** | **HYPE** | **$85.30** | **$18.98B** | **$81.52B** | **23.3%** | **−13%** | **$7.04B** | **~$300B+** | **99% 手续费 buyback & burn** | **赛道绝对龙头，P/S 21x (MC) 已 price-in 垄断溢价** |
| dYdX | DYDX | $0.1355 | $114.6M | $129.8M | 88.3% | −97% | $128M | ~$1.2–2.7B | 75% 净费用 buyback DYDX | 流通率高但量缩到 <3% 份额，边缘化 |
| GMX | GMX | $8.16 | $85.4M | $85.4M | 100% | −91% | $178–240M | ~$2.5B | 30% 费用分给 GMX/GLP 质押者 | 价值捕获路径清晰但量级差 100 倍 |
| Aevo | AEVO | — | ~$50M | — | — | −90%+ | $15.2M | $1–2B | 手续费回购 AEVE | 流动性弱，仅作尾部对照 |
| Vertex | VRTX | — | ~$80M | — | — | −85%+ | $83.9M | $0.5–1B | 手续费分成 | Arbitrum 原生，份额 <2% |
| Kwenta | KWENTA | — | ~$20M | — | — | −95%+ | ~$10M | <$0.5B | Synthetix 生态衍生品 | Optimism 生态，边缘化 |

**关键观察**：HYPE 一家占链上永续 60–70% 份额，其余所有竞品加起来不到 30%。这是一个**"赢家通吃"的垄断叙事**，但反过来也意味着：一旦有竞争者（Starknet edgeX、Binance 合规化、zkSync 永续）切入，HYPE 的份额回撤会被估值放大。

---

## 八、多空逻辑

**🟢 多头 3 条**：
1. **真实收入 + 激进通缩**：2025 年 ~$0.9B 手续费、99% 回流 buyback、已烧毁 4.6% 供应——这是加密行业**唯一接近"上市公司回购"逻辑**的代币，P/S 虽高但飞轮可验证。
2. **垄断地位 + 技术护城河**：自研 L1 + CLOB 订单簿做到亚秒撮合，11 人团队吃下 60–70% 链上永续份额，TVL 是第二名的 29 倍。
3. **机构化管线密集**：Bitwise/21Shares ETF S-1、Coinbase 期货 CFTC 认证、Gemini staking、NASDAQ 上市公司 HSTI——进度领先所有 DEX 代币。

**🔴 空头 3 条**：
1. **估值极度拉伸**：P/S (FDV) 90x、P/S (MC) 21x，已经高于 Coinbase（12x）、远高于 Binance（5x）；距 ATH 仅 −13%，回撤最浅，杀估值空间最大。
2. **团队解锁抛压未出清**：238M HYPE 从 2025-11 开始每月解锁 9.92M（~$850M/月），直到 2027-11——当前流通率仅 23.3%，未来 2 年流通量将翻倍。
3. **中心化悖论 + 监管悬剑**：JELLY 事件证明团队可手动 delist/强平；DPRK/Lazarus 关联交易暴露后，OFAC 执法风险是达摩克利斯之剑。

---

## 九、八大风险

1. **监管 / OFAC**：2024-12 DPRK 指控虽未直接处罚，但 Lazarus Group 在 Hyperliquid 上的交易行为已被美国财政部关注；一旦 OFAC 直接点名或 Coinbase/Binance 被迫屏蔽美国 IP，流动性会骤降。
2. **团队解锁抛压**：每月 9.92M HYPE（~$850M）从 2025-11 持续到 2027-11，累计 238M——相当于当前流通量的 107%。
3. **估值拉伸**：FDV P/S 90x，远超 CEX 同业；ETF 延迟或收入增速放缓都会触发杀估值。
4. **中心化争议**：JELLY 事件中团队手动冻结/delist/强制结算，与"去中心化 DEX"叙事自相矛盾；4 个验证者早期被批评集中度高（2025-04 才 permissionless）。
5. **安全/操纵风险**：JELLY、POPCAT 等小盘 meme 操纵事件反复出现——协议本身无漏洞，但"小市值 + 高杠杆 + 单国库 HLP"结构易被规则内攻击。
6. **竞争挤压**：Starknet edgeX（2026-03 峰值 26.6% 份额）、dYdX v4、Vertex、Aevo 都在抢份额；CEX 永续仍是链上的 10–20 倍体量。
7. **收入周期性**：永续交易量与 BTC 波动率高度相关；熊市交易量骤降会直接砍 buyback 规模。
8. **机构化不及预期**：Bitwise/21Shares ETF S-1 时点不可控；CFTC 对 HYPE 期货的认证也可能延迟或拒绝。

---

## 十、最被低估 / 最被高估

- **最被低估**：**通缩 buyback 的复利效应**。99% 手续费回流、年 buyback ~$1B、已烧毁 4.6% 供应——这在加密行业是独一档的价值捕获机制，比 GMX 的"30% 费用分给质押者"更激进、比 dYdX 的"75% 回购"更彻底。市场仍按"DEX 代币"给它估值，但它的现金流结构更像**一家高成长的交易所上市公司 + 回购股票**。
- **最被高估**：**$81.5B FDV 的"永续垄断溢价"**。HYPE MC $19B 是 DYDX+GMX 总和的 100 倍，P/S (FDV) 90x 是 Coinbase 的 7.5 倍、Binance 的 18 倍；距 ATH 仅 −13%，意味着 ETF 利好和垄断叙事已大部分被 price-in。一旦 ETF 延迟、OFAC 执法或团队解锁砸盘，杀估值空间比所有竞品都大。

---

## 十一、资料来源

- **官方 / SEC 文件**：Hyperliquid GitBook docs、SEC S-3（tm2531328d1_s3.htm）、SEC 424B3（Chardan 承销 HYPE 产品）、Hyperion DeFi 10-K（2025 财年）、CFTC Regulation 40.2(a) Coinbase HYPE 期货认证提交
- **数据快照**：CoinGecko、DefiLlama、CoinGlass、CoinCodex、Artemis Analytics（2026-10-01~09）
- **研究观点**：Multicoin《HYPE 有 5 倍上涨空间》、Delphi Digital《The Year Ahead for Markets 2026》、Yellow.com《Who Really Controls Crypto's $300B Perpetuals Market》、ODAILY 万字深度、ChainCatcher、PANews
- **安全事件**：SlowMist、Halborn、FinTelegram Compliance Report Dec 2025、Deshittify event timeline、PANews JELLY 分析
- **团队背景**：ht.xyz/team、The BlockBeats Jeff Yan 专访、Habr 人物稿、systematiccryptoresearch.com 技术架构分析

---

> **免责声明**：本报告基于 2026-10-09 前后公开数据整理，所有数字与事件均标注来源，但部分收入口径、Assistance Fund 持仓、团队实际卖出比例等待验证。加密货币波动剧烈，存在归零、监管、黑客、智能合约漏洞等多重风险；HYPE 当前估值高度依赖"垄断地位 + buyback 通缩 + ETF 预期"三要素，任一破裂都会触发显著回撤。本报告**不构成任何投资建议**，据此操作风险自担。
