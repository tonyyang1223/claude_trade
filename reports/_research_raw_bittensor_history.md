# Bittensor (TAO) 研究素材笔记

> 用途：投研报告的原始素材整理，非最终交付物。
> 整理时间：2026-10-08。
> 说明：技术术语保留英文原名；每条关键事实后括号内标注来源。数字与日期均来自下列公开页面，未做交叉硬数据核对（另一路负责硬数据）。

---

## 一、项目历史（按时间线）

### 1. 起源与团队
- **核心创始人**：Jacob Robert Steeves（加拿大 Simon Fraser 大学数学与计算机科学毕业，前 Google 软件工程师）与 Ala Shaabana（前多伦多大学助理教授、滑铁卢大学博士后）。另有 Garrett Oetken 被早期资料列为联合创始人。运营主体为 **Opentensor Foundation**（OTF）。（来源：Khala Research "Bittensor: The Investment History", https://www.khala.io/bittensor-an-investment-history-from-genesis-to-dtao-tao-flow ；PANews, https://www.panewslab.com/zh-hant/articles/hnqzh6sk）
- **Alaïa Labs**：早期研究主体名（"Alaïa" 取自联合创始人 Ala Shaabana 的名），白皮书署名单位。（来源：NeurIPS DAO Workshop 2022 论文 "Incentivizing Intelligence: The Bittensor Approach", https://www.bittensor.com/pdfs/academia/NeurIPS_DAO_Workshop_2022_3_3.pdf）
- **白皮书/技术原点**：2020 年 3 月在 arXiv 发布 *BitTensor: An Intermodel Intelligence Measure*（arXiv:2003.03917），提出"用同行模型互评 + 数字账本来衡量智能"的核心思路，即后来 "decentralized neural brain / peer-to-peer intelligence market" 叙事。（来源：arXiv https://arxiv.org/pdf/2003.03917v1 ；官方白皮书 https://www.bittensor.com/whitepaper）
- **关键叙事点**：**Fair launch，无 ICO、无 VC 私募、无 pre-mine、无团队预留**。从 genesis 起所有 TAO 都靠矿工做 ML 工作赚取。早期团队 2021–2023 年通过 OTC 卖出约 60 万枚已挖出的 TAO 给 Firstmark、DCG、Polychain，均价约 $18，募资约 $10.8M 用于早期开发——这是"矿工卖币"而非"VC 投资份额"。（来源：Khala Research, 同上前述）

### 2. 早期网络与主网迭代时间线

| 日期 | 事件 |
|---|---|
| 2020-03 | arXiv 技术论文 BitTensor 发布。（arXiv:2003.03917） |
| 2021-01-03 | 首个主网 **Kusanagi** 上线，无预挖、无内部人分配。（Khala Research；SEC S-3 文件 https://www.sec.gov/Archives/edgar/data/1571934/000110465925110353/tm2530709d1_s3.htm） |
| 2021-05 | Kusanagi 因共识故障停止出块（分布式 miner/validator 负载下无法就区块有效性达成一致）。 |
| 2021-11 | 从 block 0 重建为 **Nakamoto** 链，将已挖出的 546,113 枚 TAO 全部迁移；同期 NeurIPS 论文称网络"officially launched November 2021"。（Khala Research；NeurIPS 2022 论文） |
| 2023-03-20 | Nakamoto 分叉升级为 **Finney** 链（当前 Subtensor 主网），基于 Substrate/Rust，引入 delegated staking。（SEC S-3 文件；AI Wiki https://aiwiki.ai/wiki/bittensor） |
| 2023-03 | TAO 首次上线交易所，开盘约 $91。 |
| 2023-05-14 | 历史最低点 ATL 约 $30–31。（CoinCodex https://coincodex.com/crypto/bittensor/） |
| 2023-10-02 | **Subnet 框架在 Finney 主网激活**，首发 8 个 subnet（SN0 Root、SN1 Text Prompting、SN2 Machine Translation、SN3 Multi-Modality、SN4 Image Generation 等）。（SEC S-3；bittensor.com "Subnets Dive" https://www.bittensor.com/content/subnets-dive） |
| 2024-01-09 | Jacob Steeves 发布 **BIT001: Dynamic TAO** 提案，提议用 AMM 市场价格替代 validator 委员会投票分配 emission。（Khala Research） |

### 3. 关键技术里程碑
- **Yuma Consensus**：Bittensor 自己的奖励共识机制，由 validator 设置权重对 miner 评分，按 epoch（默认约 360 区块 = 1 个 tempo）分配 emission。链本身的出块共识仍是 **PoA（Aura + GRANDPA）**，与 Yuma 是两层。已演进到 Yuma v2 / v3（per-subnet 可开关，fixed-point bond 计算）。（来源：bittensor.com "Chain consensus" https://www.bittensor.com/docs/concepts/chain-consensus ；"Emissions" https://www.bittensor.com/docs/concepts/emissions）
- **Subnet 数量节奏**：2023-10 首发 8 个 → 2025-04 约 82 个 → 2025-09 达到硬顶 **128 个**（满 slots 后自动淘汰 EWMA 价格最低、已过 4 个月保护期的 subnet）。截至 2026-09（v441 升级公告），128 个注册 subnet 中 89 个 live 且在产生 emission。（来源：Khala Research；bittensor.com v441 release https://www.bittensor.com/releases/v441-upgrade）
- **dTAO（Dynamic TAO）**：2025-02-13 主网激活，每个 subnet 发行自己的 alpha token 并与 TAO 组成 Constant Product AMM 池，emission 按市场对 alpha 的需求分配，取代 64 个大 validator 的委员会投票。（来源：arXiv:2603.29751 https://arxiv.org/pdf/2603.29751 ；bittensor.com dTAO 白皮书 https://www.bittensor.com/dtao-whitepaper）
- **Taoflow 升级**：2025-11 激活，把 emission 分配从"alpha 价格"改为"净 staking 资金流"，持续净流出的 subnet 直接拿 0 emission。（来源：FinanceFeeds https://financefeeds.com/bittensor-just-upended-how-tao-rewards-work/ ；CryptoNews https://cryptonews.net/news/altcoins/32922397/）
- **治理结构**：Triumvirate（OTF 三名核心员工）起草升级 → Senate（12 名由大 staker 选举的代表）投票。注意：链目前是 PoA + sudo key，仍高度中心化。（来源：SEC S-3；Own Your Mind https://ownyourmind.ai/why-deai/how-deai-actually-competes/）
- **跨链桥 / EVM 集成**：
  - **wTAO**：通过 Wormhole 跨链到 Ethereum、Arbitrum、Avalanche、Base。（来源：Wormhole 合约地址页 https://wormhole.com/docs/ai/pages/reference-contract-addresses.md）
  - **vTAO**：staking 封装版本（类似 wstETH），存入 TAO 铸造 vTAO 并累积质押收益，可在支持的 EVM 链间桥转。（来源：learnbittensor.org https://guides.learnbittensor.org/evm-tutorials/bridge-vtao）
  - **TwTAO**：2025-08-04 推出的"受监管版"封装 TAO，1:1 抵押，主打合规 DeFi 通道。（来源：GlobeNewswire/Barchart, 2025-08-04）
  - **Subtensor 原生 EVM runtime**：v445（2026-08）在 Subtensor 链上直接跑 EVM，新增 5 个 Bittensor precompile、31 个 Solidity 函数，MetaMask/Hardhat/Remix 直连。（来源：bittensor.com v445 release https://www.bittensor.com/releases/v445-upgrade ；EVM guide https://www.bittensor.com/docs/guides/evm）

### 4. 代表性核心 Subnet（挑选 8 个）
- **SN1 Finney / Text Prompting**：OTF 自己的首个 LLM 补全子网，证明激励层可协调推理工作。
- **SN4 Targon**：机密 GPU 市场（TEE 可信执行环境），为 Venice AI 训练 Uncensored 1.2、为 Dippy AI 提供算力；约 $10.4M ARR，alpha 市值约 $59M。
- **SN8 Vanta**：去中心化 prop trading 网络，矿工提交方向性信号，validator 按风险调整收益评分；2026-03 首次实现月度净盈利 $48K。
- **SN11 TrajectoryRL / Dippy**：去中心化 prompt 优化 / agent policy 训练（Covenant AI 曾运营，后退出）。
- **SN13 Data Universe（Macrocosmos）**：去中心化数据采集，主要爬取 X/Twitter 与 Reddit 实时数据。
- **SN44 SCORE**：把实时视频流转成结构化企业数据，签约 Reading FC、AVIA（15 国 3000 个加油站）、Lavance（7000 个洗车点）、PwC France。
- **SN64 Chutes（Rayon Labs）**：开源权重模型的 serverless 推理（跑 DeepSeek、Qwen、Kimi），网络最大 alpha 市值约 $76M。
- **SN51 lium**：去中心化 GPU 租赁市场，alpha 市值约 $50M。
（来源：Khala Research 同前；subnetalpha.ai 目录 https://subnetalpha.ai/ ；AI Wiki https://aiwiki.ai/wiki/bittensor/edit）

### 5. 价格周期与重大事件
- **ATH**：**2024-04-11** 约 $757–$788（各交易所口径略有差异：CoinCodex $776.03、TradingView/Kucoin $788.44、Investing.com $757.60）。（来源：CoinCodex；TradingView；Investing.com 2024-04-11 报道 https://uk.investing.com/news/stock-market-news/cryptocurrency-bittensor-rises-more-than-22-in-24-hours-3429938）
- **ATL**：2023-05-14 约 $30–31。
- **2024-07-02/03 供应链攻击**：PyPI 上出现假冒 bittensor 6.12.2 包，窃取 coldkey 私钥，被盗约 **32,000 TAO（约 $8M）**。OTF 将链进入 safe mode 暂停出块。链本身未被攻破，攻击面在开发者工具。（来源：SlowMist https://hacked.slowmist.io/en/?c=Wallet ；Halborn https://www.halborn.com/blog/post/explained-the-bittensor-hack-july-2024 ；IQ.wiki https://iq.wiki/wiki/bittensor-tao）
- **2024 年中"内部人"争议**：有第三方研究称前 OTF 员工造成约 $28–30M 损失（来源：ownyourmind.ai https://ownyourmind.ai/projects/bittensor/ ，未独立核实，列入待验证）。
- **2026-03**：再次发生 PyPI 供应链攻击，针对 bittensor-wallet v4.0.2 后门窃私钥。（来源：qrindex.org https://qrindex.org/projects/bittensor/）
- **2026-04 Covenant AI 退出事件**：Covenant AI（运营 Templar/Basilica/Grail，SN3 后更名 Teutonic）公开指责 Steeves 中心化控制，砸盘约 **37,000 TAO（约 $10M）**，引发 TAO 下跌 18–27%、超 $9M 多单爆仓。链未停。（来源：Khala Research；FalconX https://www.falconx.io/newsroom/state-of-bittensor-subnet-adoption-trends-network-mechanics-and-covenants-departure）
- **2026-07-13**：同日两个 subnet owner 钱包被 drain：SN15 ORO 约 $285K、SN102 ConnitoAI 约 2,500 TAO（约 $510K）；SN24 Quasar、SN46 也有 owner 钱包妥协事件。（来源：TAO Daily https://taodaily.io/bittensor-ships-the-security-stack-its-subnet-owners-have-been-begging-for/）
- **监管**：SEC 未对 Bittensor 本体采取执法；反向动态是 **Grayscale Bittensor Trust (GTAO)**——2024-04-30 在特拉华成立、2024-06-10 开始运营、2025-12-11 登陆 OTCQX、**2025-12-30 向 SEC 提交 S-1 申请在 NYSE Arca 上市**（ticker GTAO），截至 2026 年中仍待 SEC 批准。（来源：SEC EDGAR https://www.sec.gov/Archives/edgar/data/2029297/000119312526140409/gtao_s-1_amendment_1.htm ；Cointelegraph 2025-12-30 https://cointelegraph.com/news/grayscale-bittensor-etp-filing-sec）

### 6. 融资与机构动态
- DCG（Barry Silbert）自称 2021 年即早期 OTC 买入 TAO；**2024-11 成立 Yuma 子公司**做 subnet 孵化加速器；2025-09-04 推出 Yuma Composite fund（追踪一篮子 subnet token）；2025-10 DCG 锚定 $10M 给 Yuma 资管板块。（来源：AI Wiki；Khala Research）
- Polychain Capital 据披露累计买入约 **$200M** TAO；Multicoin、Pantera、a16z 被披露在 subnet 层有布局。（来源：Crypto Valley Journal https://cryptovalleyjournal.com/education/basics/bittensor-and-tao-how-the-decentralized-ai-network-works/ ；Yellow.com https://yellow.com/research/bittensor-tao-decentralized-ai-investment-thesis-2026）
- OTF 本身累计融资约 **$8.5M**（最近一轮 2025-08-07 公司轮 $8M），员工约 38 人。（来源：LeadIQ https://leadiq.com/c/opentensor-foundation/6231fb53af7fcf88535e152c ；NeuronFeed https://neuronfeed.com/startups/bittensor）
- 机构产品矩阵（截至 2026-06）：Grayscale GTAO（$9–12M AUM）、Safello STAO 质押 ETP（2025-11 登陆瑞士 SIX，后跨斯德哥尔摩/巴黎泛欧，约 $3M）、TrustedStake 非托管指数（$4.7M）、Yuma Asset Management（Subnet Composite / Large Cap）。（来源：Khala Research）

---

## 二、最近情况（2025–2026-10）

### 1. 网络规模（量级）
- 注册 subnet 硬顶 128，2026-09 v441 公告时 89 个 live 且产生 emission。
- 已铸造 TAO 约 **11,270,409 τ**（2026-09 v441 数据），Root 网络质押约 540 万 τ（占已发行 47.9%）。
- Miner UID 数：2026-06 约 **2,300 个**持有 UID；另有第三方称全网 1 万+ miner 账户（口径不同，需核对）。（来源：Khala Research；opentau.ai https://opentau.ai/）
- Validator：dTAO 之前由 top 64 validator by stake 决定 emission；dTAO 后改为 AMM 价格主导，root 网络仍有 staking 权重机制。

### 2. 2025–2026 核心升级节奏
| 时间 | 升级 | 要点 |
|---|---|---|
| 2025-02-13 | **dTAO 主网激活** | 每 subnet 发 alpha + AMM，emission 市场化 |
| 2025-02-20 | Coinbase 上线 TAO | dTAO 后 7 天 |
| 2025-09 | Subnet slots 满 128 | 自动淘汰机制启用 |
| 2025-11 | **Taoflow** | emission 按净 staking 资金流，净流出 subnet 拿 0 |
| 2025-12-11 | GTAO 登陆 OTCQX | |
| 2025-12-12 | **首次 TAO halving**（block 7,103,976） | 日发行 7,200 → 3,600 TAO |
| 2025-12-30 | Grayscale 递交 S-1 | 申请 NYSE Arca 上市 |
| 2026-05 | **Conviction Upgrade** | subnet owner emission 自动锁定，退出需公开 timelock 解锁（回应 Covenant 砸盘） |
| 2026-07 | V431（monorepo，bittensor v11 Rust SDK，conviction 所有权竞争）、V440（emission bar/gate）、V441 "Root Reborn"（root TAO 质押分成机制） | |
| 2026-08 | V445（EVM precompile、multisig、Ledger）、V446（会计修复、liquid alpha、timelock recovery） | |
| 2026-09（计划） | **Null Consensus** | opt-in epoch 机制，最高质押 validator 主导、stake-proportional 分红、16,000 UID 容量 |

（来源：bittensor.com releases 列表 https://www.bittensor.com/releases ；FinanceFeeds；Khala Research）

### 3. 生态项目进展
- **外部收入开始出现**：Targon（Venice AI/Dippy AI，$10.4M ARR）、SCORE（PwC/AVIA/Reading FC 企业合同）、Vanta（月度 $48K 净盈利）、MetaNova SN68（药物发现，筛 1100 万分子，与 OnePot 合作）。Manifold Labs 完成 $10.5M A 轮（投资人含 Ram Shriram、Tobi Lütke 及 Bittensor 联合创始人）。（来源：Khala Research）
- **与 OpenAI/Anthropic/Google 的关系**：没有官方合作。叙事上是"对三大闭源实验室的结构性对冲"——Khala、Yellow 等研究均把 Bittensor 定位为"公开市场上唯一在生产环境跑的开放 AI 基础设施"。（来源：Khala Research；Yellow.com https://yellow.com/research/bittensor-tao-decentralized-ai-investment-thesis-2026）
- **上线 CE​​X**：Coinbase（2025-02-20）、Kraken、Binance 等主流所早已上线；subnet alpha token 多在去中心化 AMM 内交易，少数上 CEX。

### 4. 基金会动态
- Opentensor Foundation 位于新加坡/瑞士相关法域（公开资料，具体注册地待核），员工约 38 人；Triumvirate 三人组负责技术升级起草；资金来自早期 OTC 卖币与 2025-08 公司轮 $8M。
- 多轮 **subnet grant program** 直接向新 subnet 团队分发 TAO。（来源：Yellow.com）

### 5. 社区情绪与 KOL
- Twitter/X、Discord 活跃，Reddit r/bittensor 对 dTAO / Taoflow / Conviction 升级讨论热烈；2026-04 Covenant 退出事件后出现一波"中心化 vs 去中心"大辩论。
- 看多方（Khala、Unsupervised Capital、Yellow、Grayscale 报告）：把 TAO 叙事为"第三大生态（继 Bitcoin、Ethereum 之后）"、"AI 时代的数字商品"；黄仁勋（Jensen Huang）与 Chamath Palihapitiya 被引用为公开背书者（来源：NeuronFeed）。
- 看空/质疑方：Own Your Mind 等指出 OTF 仍持 sudo key、中位 subnet 单 coldkey 占 57% 质押（2026-09-18 数据）、inference subnet emission-to-revenue 比高达 22:1–40:1，补贴悬崖明显；Dec 2025 halving 后供给砍半，但外部收入远跟不上 emission 规模。（来源：canonical.cc https://www.canonical.cc/labs/decentralized-ai/ ；Own Your Mind https://ownyourmind.ai/projects/bittensor/）
- 社区核心讨论点：(a) GTAO ETF 何时获批；(b) subnet alpha 市场能否在 halving 后留住资金；(c) OTF sudo key 何时交还社区（PoS 转型无时间表）。

### 6. 监管与安全近况
- SEC：未对 TAO 本体执法；动态是 Grayscale 推 GTAO 上市，反向背书。
- 安全：2026-03 与 2026-07 连续出现钱包/subnet owner 钱包被 drain 事件，均指向密钥管理与软件供应链，而非协议层漏洞。v445/v446 后基金会补了 multisig、Ledger、timelock recovery 等安全栈。

### 7. 在 DeAI 板块中的相对位置
- 对标矩阵：Fetch.ai / ASI Alliance（2024-06-13 由 Fetch.ai + SingularityNET + Ocean Protocol 合并而成，主打 agent）、Render（渲染 + GPU）、Akash（GPU 云市场，600+ GPU）、Gensyn、Grass、io.net、Qubic。
- 市场共识（2026）：Bittensor 不直接出租 GPU，而是"协调智能本身"——它与 Akash/Render 在算力层是互补，与 ASI Alliance 在 agent/市场层是直接对标。多数行业盘点把 TAO 列为 DeAI 板块市值第一梯队（$2–3B 市值），但同时批评其 PoA + sudo 中心化。（来源：crawlux https://www.crawlux.com/blog/best-decentralized-ai-infrastructure/ ；cointribune https://www.cointribune.com/en/best-decentralized-ai-platforms-in-2026/ ；Own Your Mind 评分）

---

## 三、代币经济与解锁（定性）

- **总量上限**：21,000,000 TAO（对标 Bitcoin）。
- **当前流通**：截至 2026-09 已发行约 11.27M（约占上限 53.7%）；首次 halving 后日发行 3,600 TAO。（来源：bittensor.com v441 release；tao.media https://www.tao.media/tao-supply-and-emissions-how-bittensors-21-million-cap-and-halving-schedule-work/）
- **释放节奏**：按已发行量阈值触发减半——0–10.5M 区间 1 TAO/block（~7,200/天）；10.5M–15.75M 区间 0.5 TAO/block（~3,600/天，当前所处区间，首次减半发生在 2025-12-12）；15.75M 后 0.25 TAO/block（预计 ~2029）。约每 4 年减半一次。
- **分配比例**：每个 subnet 的 emission 按 epoch 分给 owner 18% / miner 41% / validator+staker 41%。（来源：learnbittensor.org https://guides.learnbittensor.org/learn/emissions）
- **团队/Foundation 预留**：**没有 pre-mine、没有 team allocation、没有 VC 份额**——这是与绝大多数加密项目最大的差异。早期团队 60 万 TAO 是"挖矿所得"，已通过 OTC 卖出约 $10.8M。
- **未来抛压讨论**：
  - 一级抛压来自 subnet owner emission（Conviction Upgrade 后已改为 timelock 解锁）。
  - 早期 OTC 持有者（DCG、Polychain、Firstmark）持仓仍大，但锁定期不公开。
  - dTAO 后每个 subnet 的 alpha token 本身有独立释放节奏，且可通过 TAO↔alpha 兑换形成抛压传导。
  - 市场对"未来 12 个月解锁"的讨论焦点不是团队 vesting（不存在），而是 **halving 后供给下降 + GTAO 上市后买盘**这一对力量。

---

## 四、待验证 / 不确定事项

1. **ATH 具体日期与价格**：多数源（CoinCodex、TradingView、CryptoSlate）指向 2024-04-11，价格在 $757–$788 区间；但 Decrypt / Coinspeaker 写 2024-03-07。需用 TradingView 日线核实。
2. **"内部人 $28–30M 黑客事件"**：仅见 ownyourmind.ai 一处提及，未见主流媒体报道，可能与 2024-07 PyPI 事件混淆，需进一步核实。
3. **用户问题中提到的 Subnet 编号映射可能已过时**：用户写"SN11 数据、SN13 推理、SN21 去中心化 RAG"，但当前公开目录显示 SN11=TrajectoryRL/Dippy（prompt 优化）、SN13=Data Universe（数据）、SN21=AdTao（PPC 广告）。早期 SN21 是否曾是 RAG subnet、后被 deregister 替换，需查 subnet 历史。
4. **OTF 注册地**：公开资料多称 Opentensor Foundation，具体法律实体注册国（新加坡？瑞士？开曼？）未在本次检索中确认。
5. **"1 万+ miner" vs "2,300 UID"**：两个口径差异大，需区分"持 UID 的活跃 miner"与"注册过账户总数"。
6. **Jacob Steeves 公开身份**：前 Google 工程师、SFU 毕业来自二手研究（Khala），未见本人 LinkedIn/官方 bio 直接确认。
7. **vTAO / wTAO / TwTAO 三者关系**：vTAO 是 staking 封装（数量随质押收益增长），wTAO 是 Wormhole 1:1 跨链封装，TwTAO 是合规版；三者是否已统一、当前哪个是主流，需再核实。
8. **Null Consensus 升级状态**：bittensor.com releases 页标注 "next September 2026"，当前已是 2026-10-08，是否已激活未确认。
9. **Triumvirate / Senate 具体成员姓名**：SEC 文件提到 Triumvirate 是 OTF 员工，但未列名；本次未挖到具体姓名。
10. **Covenant AI 退出后 SN3 现状**：仅见"更名 Teutonic"与"1T 参数训练"描述，其 alpha token 是否已被淘汰、当前 emission 份额多少未确认。
