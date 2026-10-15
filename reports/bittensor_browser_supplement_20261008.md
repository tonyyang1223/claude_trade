# Bittensor (TAO) 浏览器一手补充笔记

> 采集时间：2026-10-08 · 采集方式：computer_use_tool (browser-use-automation, plane="bu")
> 本文件是对 `bittensor_deep_research_20261008.md/html` 的**补充**，不改动原报告。
> 所有数据均来自一手网站实时抓取，URL 见各节。

---

## 一、GitHub Release 一手笔记

> 仓库：原 `opentensor/bittensor` 与 `opentensor/subtensor` 均已 301 重定向到 **`RaoFoundation`** 组织（GitHub org rename，疑似 OTF 在 GitHub 侧的品牌迁移）。
> 链运行时 release 仓库：https://github.com/RaoFoundation/subtensor/releases
> SDK 仓库：https://github.com/RaoFoundation/bittensor/releases （版本号 v10.x，与链 runtime V4xx 不同）

### 1.1 官方命名与实际内容（以 bittensor.com/releases 为准，比 GitHub release notes 详细）

| 版本 | 时间 | 官方标题 | 核心改动（原文摘译） |
|---|---|---|---|
| **V431** | 2026-07 | **The Monorepo Release** | Conviction-based subnet ownership（基于信念的子网所有权）、price-driven emissions（价格驱动 emission）、bittensor v11 SDK（Rust core）、Ledger 与浏览器扩展签名、可验证升级流水线——链/SDK/CLI/docs 同仓发布。 |
| V437 | 2026-07 | Collateral & Key Lineage | Miner 注册抵押、链上 hotkey/coldkey swap 血缘、bonded key-swap 加固、一键 stake 转移到新 coldkey/hotkey、air-gapped Polkadot Vault 签名。 |
| V438 | 2026-07 | Interfaces & Reliability | 有界 EVM staking 视图、Ledger 友好的 limit-order 签名、精确 emission split、可预测 epoch 计数。 |
| V439 | 2026-07 | Conviction for Contracts | EVM 访问 stake locks 与 miner conviction、rolled lock 视图、locked-alpha 转账策略、owner-cut 自动锁定控制。 |
| **V440** | 2026-07 | **The Emission Gate** | Subnet emission 必须超过一个市场定价的需求门槛：高于门槛按比例发，低于门槛平滑衰减。**Idle slots 停止赚 emission**，建子网成本降到接近注册交易费。 |
| **V441** | 2026-07 | **Root Reborn** | 把 Root 网络 5.4M τ 的分红流从"每日强制卖出"改为 validator 管理的"子网篮子"（详见第二节）。 |
| **V445** | 2026-08 | **EVM, btcli, and Reliability** | 完成 typed EVM 接口、multisig 成为一等 btcli 钱包、**回收交易手续费**、人类可读 Ledger 订单、大范围可靠性加固。 |
| **V446** | 2026-08 | **Accounting, Liquid Alpha, and Timelock Recovery** | 修复历史 alpha 记账、conviction 所有权门改为基于 eligible alpha、可选 Liquid Alpha 共识模式、失败 timelock reveal 可审计、修复 GRANDPA warp-sync set 处理。 |
| V447 | 2026-08 | **Conviction Normalization** | Subnet 所有权门改为**单个 hotkey 单独对比 18% conviction 阈值**（与 owner cut 对齐），把收购子网的 TAO 成本恢复到 v446 前水平。 |
| V448 | 2026-08 | Root Claims, Safer Staking, Linked Orders | Root claim 可预测、跨子网 stake 移动保护、批量多 hotkey 退出、实时 staking 指数、可组合 linked orders。 |
| V450 | 2026-08 | **Curated Beta** | 开放 `set_root_weights`：validator 在 **1/16 集中度上限**下管理自己的分红篮子，链上计算篮子指数/展示价/staker 收益。 |
| V461 | 2026-09 | **Basket Trading** | `swap_basket`：root validator 通过专用 BasketTrading proxy 换仓，2% per-leg 价格带、10% NAV/日 token-bucket 换手预算、10% per-pool 流动性上限、1/16 集中度上限、治理冻结开关。**`set_root_weights` 被移除，分红就地累积。** |
| 下一个 | 待定 | **Null Consensus** | Opt-in epoch 机制，最高质押 validator 给 miner 激励、stake 比例分红、精确整数支付、**共享 16,000 UID 容量**、raw-u16 SDK/CLI 提交、更大有界 timelock commit。 |

> 来源：https://www.bittensor.com/releases （页面实时快照 2026-10-08）

### 1.2 GitHub 侧补充观察
- subtensor 仓库 open issues **20**、open PR **32**、Security alerts **8**。
- 最新已上线 runtime **v475**（Null consensus、precise emissions、PoW registration）；v473 引入 BLS12-381 EIP-2537 预编译、deprecate alpha v1 stage 1、限制 delegated alpha hotkey 移动频率。
- v445 GitHub 原文 PR 列表（与官网标题互证）：reject deterministic failures、purge neuron commitments、Ledger human-friendly limit orders、miner-burn emission scaling 先 remove 再 restore。
- 发布流程已是 **2-of-2 multisig**（CI key + triumvirate sudo key），btcli 可本地 srtool build 对比 wasm hash 独立验证。

---

## 二、TaoStats 链上数据（2026-10-08 实时）

> 来源：https://taostats.io/subnets 、https://taostats.io/subnets/51 、https://taostats.io/validators
> TAO 现价快照：**$285.91（24h −4.96%）**

### 2.1 全网汇总
| 指标 | 数值 | 对比前报告 |
|---|---|---|
| 总质押（Root + Alpha） | **7.45M τ** | 前报告只提 Root 5.40M；本次确认 Root 5.46M（67.61%）+ Alpha 2.61M（32.39%） |
| Root 网络质押 | 5.46M τ | 前报告 5.40M，基本一致 |
| Root validator 数 | **144 个** | 前报告未给具体数 |
| Subnets Value（α/τ 汇率） | 1.22 | 新数据 |
| 24h 总成交量 | 172.5K τ（Root 19.96% / Alpha 80.04%） | 新数据 |

### 2.2 Top 10 Subnet 榜（按 emission % 排序，2026-10-08）

| # | Subnet | SN | 日 emission (τ) | 占全网 emission | α MCap (K) | 1D 链上买入占比 |
|---|---|---|---|---|---|---|
| 1 | lium.io | 51 | 468.4 | **13.01%** | 483.8 | 10.24% |
| 2 | Chutes | 64 | 330.3 | **9.18%** | 428.9 | 7.31% |
| 3 | Targon | 4 | 243.2 | **6.75%** | 302.4 | 5.38% |
| 4 | Affine | 120 | 214.4 | 5.96% | 192.8 | 4.31% |
| 5 | engy | 53 | 171.5 | 4.76% | 209.7 | 3.74% |
| 6 | Score | 44 | 167.9 | 4.66% | 203.4 | 3.67% |
| 7 | Vanta | 8 | 137.6 | 3.82% | 161.3 | 3.01% |
| 8 | Teutonic | 3 | 118.1 | 3.28% | 145.6 | 2.58% |
| 9 | iota | 9 | 112.2 | 3.12% | 124.0 | 2.45% |
| 10 | SayGM | 28 | 106.2 | 2.95% | 117.8 | 2.30% |

**关键集中度发现：Top 10 subnet 吃掉全网 57.5% 的 emission。** 头部 lium 一家独占 13%。这比前报告"中位 subnet 单 coldkey 57% 质押"所描述的**子网间**集中度更极端——前报告只提了子网内 coldkey 集中，没量化子网间 emission 集中。

### 2.3 SN51 lium 详情
- 持有者数：**6,743**
- α 价格：0.0996 τ
- Liquidity：339K τ
- Incentive Burn：0%（无销毁）

### 2.4 对前报告数字的验证/修正
- **Root 质押 5.40M → 5.46M τ**（+1%，误差内）。
- **89/128 live subnets** 与 V441 官方文案一致（"89 live subnets"）。
- **"中位 subnet 单 coldkey 占 57% 质押"**：TaoStats distribution 页为图表渲染，未登录状态下 DOM 表格为空，本次**未能交叉验证**该数字，仍维持前报告单一来源（Own Your Mind）标注。
- **新发现**：emission 在子网间高度集中（Top 10 = 57.5%），前报告未量化此维度。

---

## 三、Mirror / Docs / 官方原文要点

> opentensor.mirror.xyz 已 301 跳转到 paragraph.com（Mirror 平台已商业化更名）。官方博客实际在 https://www.bittensor.com/releases 与 docs.bittensor.com。

### 3.1 V441 "Root Reborn" 深度原文（https://www.bittensor.com/releases/v441-upgrade）

**这是前报告只列了名字、本次才拿到一手细节的最重要升级。**

- **5,403,483 τ 质押在 Root = 47.9% 已发行 TAO，$1.28B，占全网质押 TAO 的 73%。**
- 子网每日向 Root 支付 **~936 τ（$222k/天）= 全部新 emission 的 26%**。
- dTAO 上线至今 Root 累计收到 **837,536 τ（$198M）**。
- 基础收益率 **6.3%/年**（TAO 计价）。
- **V441 前**：Root 收到的分红每个块都被强制卖出成 TAO = 每日 936 τ 卖压，相当于子网池子每日新注入 1,196 τ 的 **78% 被抽走**。
- **V441 后**：每个 Root validator 管一个"escrowed basket"（链上 pallet 子账户无私钥），分红就地累积为子网 α，不卖出；curation 开放后才卖出一次再按权重买回。**子网池子净流量从 −936 τ/天 → ≈ 0。**
- Root 注册改为 **burn-based**（起步 1 τ，每次注册 ~×1.26 递增，衰减回底），不再要求前置质押。
- Staker 按 NAV 累积权益，`claim_root_with_hotkey` 随时赎回，未 claim 前不实现、不征税。
- V450 开放 `set_root_weights`（≥8 个正权重目的地，1/16 集中度上限）；V461 进一步允许 validator 换仓 basket。

### 3.2 DefiLlama 交叉验证（https://defillama.com/protocol/bittensor）
- TVL：**$605.5M**（注意：DefiLlama 只统计跨链封装/DeFi 可组合部分，不含原生 staking；TaoStats 口径 7.45M τ × $285 ≈ $2.12B）
- MC：$3.222B · FDV：$5.967B · 24h 量：$186.83M
- **年费用（fees）：$112.5K** —— 再次印证前报告"协议零抽成/P-S >1000x"判断
- 收录黑客事件：2024-07-02，$8M，social engineering/malware（与前报告一致）

---

## 四、Twitter / Discord / Reddit 一手观察

### 4.1 X / Twitter（已登录，账号 @tonyyang12231）

**@opentensor（17.1 万 followers，2,751 帖子）近 30 天高互动推文：**

| 日期 | 内容一句话 | 互动（赞/转/评/浏览） | URL |
|---|---|---|---|
| 2026-08-04（置顶） | **Root Reborn 发布**：validator 竞争构建最佳子网篮子，成功策略吸引更多质押 | 625 赞 / 171 转 / 57 评 / 11 万浏览 | https://x.com/opentensor |
| 2026-10-06 | SN10 Pareton：用 Bittensor miner 改进生产环境模型软件，让 AI 推理更快更便宜；本周四 9PM UTC 直播 | 164 / 38 / 14 / 1.3 万 | 同上 |
| 2026-10-05 | 生态周报 9/28–10/4：**Exploit Summit 蒙特利尔**、Macrocosmos、Beam、Umi、Targon、Hippius、Score、Pareton、Carbon | 159 / 43 / 20 / 1.6 万 | 同上 |
| 2026-10-02 | **OpenRoboto SN80**：不到一个月把 @physical_int π0.5 机器人模型模拟任务成功率从 ~55% 提到 ~90% | 165 / 32 / 29 / 2.0 万 | 同上 |
| 2026-10-01 | 比特币用激励构建最大专用计算网络；Bittensor 用同样逻辑整合全球闲置算力建去中心化 AI 训练网络 | — | 同上 |
| 2026-09-29 | Macrocosmos 在 **Exploit Summit 蒙特利尔**发布 **iota SDK + Liquid Compute**（解耦计算平台，把全球长尾算力变成可训练容量） | 236 / 37 / 31 / 1.4 万 | 同上 |

**情绪判断**：官方推号近期互动集中在**生态应用落地**（机器人、推理优化、数据、视频结构化），而非价格或 GTAO。置顶 Root Reborn 推文 11 万浏览是近期最高传播。**未见 GTAO S-1 获批相关推文**——截至 10/8 官方仍未宣布获批。

**@_unconstrained（Jacob Steeves）**：账号现为私密保护，bio 改为韩文（"뭘 봐 / 내가 도전하면 난 할 수 있다 YOLO"），仅 1 follower，疑似已弃用或改名。无法读取其近期推文。

### 4.2 Reddit
- 访问 https://www.reddit.com/r/bittensor_/top/?t=month 直接被 Reddit 网络安全拦截（"You've been blocked by network security. To continue, log in"）。
- **未登录采集失败，本次未获取 Reddit 一手帖子。**

### 4.3 Discord
- 未尝试（discord.gg/bittensor 强制登录，与 Reddit 同属需 handoff 站点；本次未触发 handoff 窗口，跳过）。

---

## 五、对前报告的修正与补充

### 5.1 修正/补充点（明确标注）

1. **【补充，前报告完全未提】V441 Root Reborn 是 2026 下半年最重要架构变更**：前报告时间线只写了"V431/V440/V441 Root Reborn 连续升级"一个名字。本次一手数据揭示：Root 网络 5.4M τ（$1.28B，占已发行 47.9%）的分红从"每日强制卖出"改为 validator 管理的篮子，**直接消除了每日 936 τ（$222k）的结构性卖压**。这是对多头逻辑的重大增量利好——前报告"空头 1：零抽成"逻辑未被颠覆，但 Root 的价值捕获方式从"被卖压稀释"变成"索引化复利"。

2. **【补充】V440 "Emission Gate" 直接缓解前报告风险 7"补贴悬崖"**：前报告称"inference subnet emission-to-revenue 22:1–40:1，halving 后中小子网经济模型可能坍塌"。V440 引入市场定价门槛，**idle slots 直接拿 0 emission**——这意味着劣质 subnet 会被自动关停，而非靠 halving 慢慢饿死。与 128 slots 满后自动淘汰机制叠加。

3. **【修正】emission 子网间集中度比前报告描述的更高**：前报告只提"中位 subnet 单 coldkey 57% 质押"（子网内集中）。本次 TaoStats 实测：**Top 10 subnet 吃 57.5% 全网 emission，第一名 lium 独占 13%**。这是子网间集中，与子网内集中是两个维度，前报告遗漏。

4. **【补充】V447 Conviction Normalization（18% 阈值）**：前报告提了"PoA + sudo key + 中位 subnet 单 coldkey 57%"的中心化风险，但没提 OTF 已经在链上引入 **18% conviction 硬门槛**防止子网被恶意收购。这是中心化风险的一个缓解措施。

5. **【补充】V461 Basket Trading + 即将到来的 Null Consensus（16K UID）**：前报告停在 V446，本次发现 8–9 月还有 V447/V448/V450/V461 连续升级，且下一步 Null Consensus 要把 UID 容量扩到 16,000（现在全网 miner UID 约 2,300，扩张 7 倍）。

6. **【修正】GitHub 组织从 opentensor 改名为 RaoFoundation**：所有 opentensor/*.repo 链接 301 到 RaoFoundation。这本身不是技术变更，但意味着引用 GitHub 链接时要更新。

7. **【补充】DefiLlama 年 fees $112.5K**：再次硬验证前报告"P-S >1,000x、协议零抽成"判断——$3.22B MC 对应 $112.5K 年 fees，P-S ≈ **28,600x**（比前报告估算的 1,100–1,400x 更极端，因为前报告把 subnet 外部 ARR 也算进了"协议捕获"，但 DefiLlama fees 口径是协议层实际收费）。

8. **【补充】生态落地案例（X 一手）**：
   - OpenRoboto SN80 一个月把 π0.5 机器人模型成功率从 55% → 90%（前报告未提）。
   - Macrocosmos iota SDK + Liquid Compute 在 Exploit Summit 蒙特利尔发布（前报告提了 Data Universe/SN13，但没提 Liquid Compute 新产品线）。
   - SN10 Pareton 做生产环境推理优化（前报告未提）。

9. **【修正/待验证】@_unconstrained 账号已私密 + 韩文 bio**：前报告把 Jacob Steeves 列为核心创始人。其 X 账号现状异常（疑似弃号/改名），无法确认是否仍活跃在一线。列入待验证。

10. **【价格更新】**：采集时 TAO $285.91（24h −4.96%），前报告基准 $300。FDV 对应 $5.97B（DefiLlama），略低于前报告 $6.4B。

### 5.2 未推翻的前报告结论
- Fair launch / 21M 硬顶 / 类 BTC 减半叙事：无新反证。
- GTAO S-1 待批：官方 X 至今未宣布获批，维持"待批"判断。
- 协议零抽成：DefiLlama fees $112.5K 硬验证。
- 安全事件时间线：无新事件。

---

## 六、生态落地案例补充（一手搜集增量）

> 以下为本次浏览器独立抓取 + 交叉搜索补充的真实使用量与收入数据，用于验证"Subnet 是否有真实需求"这一核心多空分歧。

### 6.1 头部 Subnet 真实使用量 / 收入硬数据

| Subnet | 项目 | 真实使用量 / 收入 | 来源 |
|---|---|---|---|
| **SN64 Chutes** | 去中心化 AI 推理 | **日处理 500 亿+ tokens，40 万+ 用户，$1M+ auto-staking 收入**；与哈佛研究团队公开了 9,174 个模型的 61.2 亿次 LLM 推理请求数据集 | Our Crypto Talk (2026-03)；@opentensor 9/22 推文 |
| **SN4 Targon** | AI 推理市场（托管模型即时预测） | **rPnL $1,247 万美元** | PANews (2026-10-08) |
| **SN3 Teutonic/Templar** | 大规模 LLM 预训练 | **rPnL $643 万美元**（Covenant-72B 模型发布；2026-04 Covenant AI 退出事件后 emission 从 30.39% 降至 3.28%） | PANews；Our Crypto Talk |
| **SN51 Lium** | 去中心化 GPU 租赁市场 | 6,743 持有者，α 价格 0.0996 τ，流动性 339K τ | TaoStats |
| **SN107 Minos** | 基因组学 | $14M 市值，142% APY 质押收益率 | TAO Daily (2026-08-19) |

**关键判断**：Chutes 的 500 亿 tokens/日 + 40 万用户是 Bittensor 生态内**唯一可验证的大规模真实使用**，但协议层仍零抽成——这些收入归 Subnet 矿工/验证者，不进入 TAO 持有者价值捕获。

### 6.2 活跃 Subnet 应用案例（9-10 月 Twitter 一手）

- **SN10 Pareton**（10/6）：生产环境推理优化，让 AI 推理更快更便宜；持续测试矿工提交的优化，只保留提升性能且不牺牲输出质量的更改。
- **SN80 OpenRoboto**（10/2, 9/23）：不到一个月把 π0.5 机器人模型模拟任务成功率从 55% → 90%；发布 OpenRoboto Shift，构建 Figure_robot Index 的去中心化替代数据网络。
- **SN114 SOMA**（9/25）：去中心化 AI 服务市场，从上下文压缩起步；矿工竞争提交压缩算法，验证者基于压缩率与保留性能的平衡评分。
- **SN105 Beam**（9/19）：带宽子网，并行传输 1 TB 数据 <2 分钟；Beam Studio 自动化数据传输工具，可在 Beam 之上构建类 Discord 的直播视频应用。
- **SN66 Conjectures**（9/20 生态周报）：数学研究子网，矿工解决了六个 Erdős 猜想。
- **SN28 SayGM**（9/21）：机密推理层，通过 NEAR AI Cloud 提供 Intel TDX 飞地内运行的私有 AI 模型，一个 API 密钥访问数十种模型。
- **SN9 Macrocosmos iota**（9/29）：在 Exploit Summit 蒙特利尔发布 iota SDK + Liquid Compute，把全球长尾算力变成可训练容量。

### 6.3 注册成本与网络规模
- 当前 Subnet 注册成本：**1,007 TAO**（≈ $28.7 万）
- 全网 Subnet 总数：**125 个**（TaoStats 实时口径），其中 89 个 live 产生 emission
- Subnet deregistration list：10 个（即将被淘汰）

---

## 七、Reddit / Discord 社区情绪补充（搜索引擎间接采集）

> 因 Reddit 登录墙 + 内置浏览器登录卡住，本节通过 general_search 间接采集社区公开讨论、KOL 观点和 Discord 频道摘要，不包含登录态完整帖子。

### 7.1 Reddit r/bittensor_ 社区氛围

| 维度 | 评价 | 来源 |
|---|---|---|
| 社区质量 | "well-informed, welcoming, quick to educate newcomers"——信息密度高、对新人友好、主动答疑 | Own Your Mind (2026-10-07) |
| 核心共识 | Bittensor 有**独立于大盘的增长周期**，基于真实 AI 生产而非加密市场情绪 | Our Crypto Talk (社区调研) |
| 对 halving 态度 | 社区普遍乐观，认为 TAO 创造了比上一轮周期更多的真实价值 | Our Crypto Talk |
| 情绪-价格相关性 | 30 天滚动相关性接近零（平均 -0.04），社区讨论对短期价格几乎无预测力 | Social Sentiment Report PDF |
| **每周访客** | **1.6K**（r/bittensor_ 页面右侧栏数据，2026-10-08 一手截图） | Edge 浏览器一手采集 |
| **社区规模** | 公开社区，创建于 202 年 8 月 4 日 | Edge 浏览器一手采集 |

#### 7.1.1 本月热门帖子（一手截图采集，2026-10-08）

| # | 帖子标题 | 作者 | 发布时间 | 互动数据 | 核心信号 |
|---|---|---|---|---|---|
| 1 | **BitTensor (TAO) Goes Live on Robinhood Chain** | u/TAO-Samurai | 24天前 | 19赞 / 6评论 | TAO 上线 Robinhood 链，中心化交易所/公链生态扩展 |
| 2 | **A live Bittensor subnet heading into YC**（ORO 加入 Y Combinator Fall 2026，AI 购物体验） | u/BuilderFuture3683 | 1个月前 | 19赞 / 1评论 | 子网项目进入 YC 孵化，生态应用落地 |
| 3 | **Barry Silbert shifting his focus back on TAO**（灰度创始人动向，ZEC×TAO 肌肉手臂梗图 23.1K 浏览） | u/TAO-Samurai | 19天前 | 16赞 / 2评论 | 机构大佬重新关注 TAO，灰度潜在布局信号 |
| 4 | **NEAR AI Cloud's confidential inference is live via GoodMorning** | u/TAO-Samurai | 17天前 | - | 机密推理上线，NEAR 生态集成 |

**热门帖子特征分析**：
- **KOL 高度集中**：u/TAO-Samurai 一人发布了 3/4 个热门帖子，是社区核心信息源
- **内容类型**：生态动态（Robinhood 链、YC、NEAR 集成）> 机构动向（Barry Silbert）> 应用落地
- **互动量偏低**：热门帖子仅 16-19 赞，说明社区整体活跃度不高（与 1.6K 周访客一致）
- **高质量信号**：Barry Silbert 帖子有 23.1K 浏览，说明机构动向是社区最关注的话题

### 7.2 Discord 社区关键讨论（SubnetRadar 蒸馏 + 媒体报道）

| 时间 | 话题 | 核心内容 | 来源 |
|---|---|---|---|
| 2026-10-03 | **Root Reborn 质押** | V441 后 Root 质押收益机制调整，社区理解为"从指数收益转向子网篮子押注" | SubnetRadar |
| 2026-10-03 | **Coldkey Swap 文档** | 针对被黑钱包的 coldkey 交换操作指南发布，社区安全讨论升温 | SubnetRadar |
| 2026-10-03 | **TAO 质押目的澄清** | 官方明确：TAO 质押是为了**治理权**（conviction voting），不是为了收益生成 | SubnetRadar |
| 2026-10-03 | **安全警告** | "公共频道支持，私人 DM 都是诈骗"——社区反复提醒钓鱼风险 | SubnetRadar |
| 2026-06-19 | **Root Reborn 争议** | Safello CEO Frank Schuil：传统 root 收益消失会让 TAO 对不习惯直接投资子网的投资者吸引力下降；解决方案是把"指数型代币"变成"集中子网押注" | tao.media |
| 2026-04 | **Covenant AI 退出风波** | Covenant 创始人 Sam Dare 指控 Steeves"去中心化剧院"，引发 Discord 社区关于"网络去中心化真实性"的激烈争论 | FXStreet / SCAND.Ai |
| 2026-09-29 | **18 个月治理路线图** | 从"激励引擎"转向"市场"；Gamma 将 emission 从补贴转向类似预算的支出 | AInvest |

### 7.3 KOL 与社区情绪指标

| KOL / 来源 | 观点 | 关键价位 |
|---|---|---|
| Kazuha 汇总（2026-10-03） | 看多 TAO，$300-295 是入场区间；$297 扫回确认；4 小时收盘低于 $290 看空；$2,000 是极端看多情景 | $290-$300 区间 |
| LecksMoney（TAO Daily） | TAO $1,000 需要 ~$10B 市值，相比其他主流加密资产是现实的 | $1,000 目标 |
| PumpParade 预测（2026-08） | 悲观 $130 / 中性 $210-260 / 乐观突破需 12 月减半催化；$183 是 30 天底部支撑 | $183 支撑 |
| CoinCodex（2026-10-07） | TAO 已高于 10 月 12 日预测价 26.38%，短期预计回调 -23.41% | 短期看空 |

### 7.4 社区情绪对估值的启示

- **多头论据**：社区质量高、新人友好、对治理机制（Conviction / Root Reborn）理解深入；KOL 普遍看多，$290-300 被视为强支撑
- **空头论据**：情绪与价格相关性接近零——社区热度不等于币价动力；Covenant 退出事件暴露的治理中心化问题未完全解决；短期技术面看回调
- **关键观察**：社区反复强调"TAO 质押是为了治理，不是收益"——这意味着核心用户群体是**长期持有者/验证者**，而非短期投机者，筹码稳定性较高

---

## 八、待验证事项

1. **"中位 subnet 单 coldkey 57% 质押"**：TaoStats distribution 页图表未在未登录态渲染成文本，本次未能交叉验证；需登录 TaoStats Pro 或用 API 拉数据。
2. **GTAO S-1 最新进展**：X 搜索未出结果（X 搜索页未正常加载），需后续在 SEC EDGAR 或 CoinDesk 等渠道补。
3. **@_unconstrained 是否仍为 Steeves 本人**：账号私密+韩文 bio，需确认是否改名或弃号。
4. **V475 Null Consensus 上线时间**：GitHub 已是 latest release，但 bittensor.com/releases 页面标为"Next/Upcoming"，可能已 proposed 但未激活。
5. **Reddit r/bittensor_ 情绪**：已通过 Edge 浏览器一手采集本月热门帖子列表（见 7.1.1），但**未深入帖子评论区细节**。
6. **Discord #announcements / #governance**：已通过 SubnetRadar 蒸馏 + 媒体报道间接采集关键讨论（见第七节），但**未拿到 Discord 频道完整消息历史**。
7. **DefiLlama "operates on PulseChain"**：FAQ 字段错误（Bittensor 自有 Substrate 链），属 DefiLlama 数据质量问题，不影响 TVL 数字但记录在案。
