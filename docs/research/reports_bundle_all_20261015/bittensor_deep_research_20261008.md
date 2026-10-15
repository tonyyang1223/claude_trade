# Bittensor (TAO) 深度投研摘要

> 整理时间：2026-10-08 · 赛道：Decentralized AI / DeAI 第一梯队
> 完整 HTML 报告：`reports/bittensor_deep_research_20261008.html`

---

## 一、核心指标快照（2026-10-08）

| 指标 | 数值 |
|---|---|
| 当前价格 | **~$300**（区间 $288–$313） |
| 市值 MC | **$3.40B** |
| FDV | **$6.40B**（AI 赛道第一） |
| 流通量 / 上限 | 11.34M / 21M（**流通率 54%**） |
| ATH | $776（2024-04-11），当前 **−61%** |
| ATL | $30.25（2023-05-14） |
| Active Subnets | 89 / 128（2026-09 v441） |
| Root 网络质押 | 5.40M TAO（占发行 47.9%） |
| 首次 halving | 2025-12-12，日发行 7,200 → 3,600 TAO |

---

## 二、项目一句话定位

Bittensor 是基于 Substrate 的去中心化神经网络协议，通过 **Yuma 共识 + dTAO AMM** 让 128 个 Subnet 以市场竞争方式分配 TAO 奖励。它不直接出租 GPU，而是"协调智能本身"，叙事上是"对 OpenAI/Anthropic/Google 的结构性对冲"。

**关键标签**：Fair launch · 无 ICO/VC 份额 · 21M 硬顶 · 类 BTC 减半 · Grayscale GTAO S-1 待批。

---

## 三、历史关键节点

| 日期 | 事件 |
|---|---|
| 2020-03 | arXiv:2003.03917 技术论文发布（Steeves & Shaabana） |
| 2021-01-03 | 首个主网 Kusanagi 上线（无预挖/无 VC） |
| 2021-11 | 共识故障后重建为 Nakamoto 链 |
| 2023-03-20 | Nakamoto 分叉为 **Finney**（当前 Subtensor 主网）；同月 TAO 上 CEX，开盘 $91 |
| 2023-10-02 | **Subnet 框架激活**，首发 8 个 subnet |
| 2024-04-11 | **ATH $757–788**（FDV ~$16.3B） |
| 2024-07 | PyPI 假冒包窃 ~32,000 TAO（~$8M），链进 safe mode |
| 2025-02-13 | **dTAO 主网激活**（每 subnet 发 alpha + AMM）；7 天后 Coinbase 上线 |
| 2025-09 | Subnet slots 满 128，自动淘汰启用 |
| 2025-11 | **Taoflow**：emission 按净 staking 资金流分配 |
| 2025-12-12 | **首次 halving**，日发行砍半 |
| 2025-12-30 | Grayscale 递交 S-1 申请 NYSE Arca 上市 GTAO |
| 2026-04 | Covenant AI 退出砸盘 ~37,000 TAO（~$10M），单日 −18%~−27% |
| 2026-05 | Conviction Upgrade：owner emission timelock 锁定 |
| 2026-07 | V431/V440/V441 "Root Reborn" 连续升级；SN15/SN102 owner 钱包 drain |
| 2026-08 | V445（EVM precompile + multisig + Ledger）/ V446 |

---

## 四、最近情况（2025 – 2026-10）

- **外部收入开始出现**：Targon（Venice AI/Dippy AI）~$10.4M ARR；SCORE 签 PwC/AVIA/Reading FC；Vanta 月度净盈利 $48K；Manifold Labs 完成 $10.5M A 轮。
- **机构化加速**：GTAO Trust 在 OTCQX 交易（$9–12M AUM），S-1 待批；Polychain 累计 ~$200M 仓位；DCG 成立 Yuma 子公司并锚定 $10M；Safello STAO ETP 在瑞士/北欧/巴黎泛欧挂牌。
- **跨链封装**：wTAO（Wormhole）、vTAO（staking 封装）、TwTAO（合规版，2025-08）。
- **安全短板**：2026-03 wallet PyPI 后门、2026-07 subnet owner 钱包 drain——攻击面在工具/钱包层，v445/v446 正在补 multisig/Ledger/timelock 栈。
- **监管**：SEC 未对 TAO 本体执法；GTAO 上市是反向合规背书。

---

## 五、估值区间（三档情景）

基准价 $300 · MC $3.4B · FDV $6.4B · 当前处于历史 FDV 区间 **36.8% 分位**。

| 情景 | 目标价 | 对应 FDV | 对应 MC | 较当前 |
|---|---|---|---|---|
| 🔻 **悲观** | **$150 – $200** | $3.15B – $4.20B | $1.70B – $2.27B | **−50% ~ −33%** |
| 🟡 **中性** | **$380 – $520** | $8.0B – $10.9B | $4.31B – $5.90B | **+27% ~ +73%** |
| 🟢 **乐观** | **$750 – $950** | $15.8B – $20.0B | $8.51B – $10.77B | **+150% ~ +217%** |

**关键稀释算术**：3 年流通量 = 11.34 + 3,600×365×3/1e6 = **15.28M**（流通率 72.8%）。若 MC 不动，稀释 alone 把价格压到 **$222.5**（−26%）；想 3 年后守住 $300，MC 必须扩到 $4.58B（+35%）。

**核心假设**：
- 悲观：AI 退潮、GTAO 延迟 12 月+、再现安全事件、市场认清零抽成硬伤。
- 中性：GTAO 6–12 月内获批、subnet ARR 两年内 $12M→$30–40M、机构化溢价 1.2x。
- 乐观：GTAO 复制 IBIT 行情（1.3–1.5x）、AI 主升、subnet ARR 复合到 $100M+、TAO 被列为 AI 蓝筹。

---

## 六、竞品对比

| 项目 | 代币 | 价格 | MC | FDV | 流通率 | 距 ATH | 价值捕获 | 贵贱判断 |
|---|---|---|---|---|---|---|---|---|
| **Bittensor** | **TAO** | $300 | $3.40B | **$6.40B** | 54% | **−61%** | 无抽成，靠 emission 稀缺 | **最贵一档**，溢价已 price-in |
| Fetch.ai / ASI | FET | $0.23 | $0.56B | $0.67B | ~84% | −93% | EVM agent 框架 | 叙事被合并稀释 |
| Render | RENDER | $1.55 | $1.00B | $1.00B | 80.5% | −89% | **BME 直接销毁** | 估值最扎实 |
| Worldcoin | WLD | $0.55 | $1.50B | $5.50B | 38.4% | −95.3% | World ID 身份 | FDV/MC=3.67，解锁抛压最重 |
| SingularityNET | AGIX | — | ~$0.05B | — | — | −95%+ | 已并入 ASI | 流动性枯竭 |
| Akash | AKT | $0.77 | $0.23B | ~$0.30B | 76.8% | −89% | BME + 部署池税 | **单位收入最便宜** |
| io.net | IO | $0.16 | $0.07B | $0.13B | 51.3% | −97.5% | Solana GPU 网络 | 微盘尾部对照 |

**关键观察**：TAO FDV 赛道第一、回撤最浅（−61% vs 同业 −89%~−97.5%），意味着 **GTAO 利好已大部分被 price-in**；而协议零抽成、P-S >1,000x 的硬伤并未被估值折让。

---

## 七、多空逻辑

**🟢 多头 3 条**：
1. Fair launch + 21M 硬顶 + 类 BTC 减半——机构能讲的"数字商品"稀缺故事在 AI 赛道里最干净。
2. 128 subnet / 89 live，Targon/SCORE/Vanta 已跑出 $10M+ 真实 ARR，不是 vaporware。
3. GTAO S-1 + Polychain $200M + Coinbase 上线，机构化管线领先所有 AI 代币。

**🔴 空头 3 条**：
1. 协议零抽成、P-S >1,000x，对比 RENDER/AKT 的直接销毁/池税，价值捕获路径最长最虚。
2. PoA + sudo key + 中位 subnet 单 coldkey 57% 质押，与"去中心化 AI"叙事自相矛盾。
3. FDV 赛道第一、回撤仅 −61%，一旦 GTAO 延迟或 AI 退潮，杀估值空间大于同业。

---

## 八、八大风险

1. **中心化**：PoA + sudo key，PoS 转型无时间表；中位 subnet 单 coldkey 占 57% 质押。
2. **安全事件频出**：2024-07 PyPI、2026-03 wallet 后门、2026-07 owner 钱包 drain。
3. **稀释**：仍有 46% 上限未发行，halving 后年通胀仍 6.2%。
4. **监管**：GTAO S-1 时点不可控；EU MiCA 对封装体的定性。
5. **竞争挤压**：ASI Alliance 合并后 agent 叙事集中；RENDER/AKT 价值捕获更短更硬。
6. **社区裂痕**：Covenant AI 退出事件后治理信任受损。
7. **补贴悬崖**：inference subnet emission-to-revenue 比 22:1–40:1，halving 后中小 subnet 经济模型可能坍塌。
8. **无直接收入**：$3.4B MC 对应可验证协议收入 ≈ $0，P-S 无法自洽。

---

## 九、最被低估 / 最被高估

- **最被低估**：halving 后的供给曲线。年化通胀已降到 6.2%，2029 年下次减半后趋近 BTC 级稀缺；这一供给侧事实在同业里没有对手（WLD 还在 38% 流通率解锁压制，RENDER/AKT 无减半叙事），但市场仍把 TAO 按"高通胀 AI 山寨"定价。
- **最被高估**：$6.4B FDV 的"机构化溢价"本身。TAO FDV 赛道第一、距 ATH 仅 −61%，GTAO 上市的利好已大部分被 price-in；协议零抽成、P-S >1,000x 的硬伤并未被折让。一旦 S-1 再延迟或 IBIT 式行情不复制，杀估值空间比 RENDER/AKT 都大。

---

## 十、资料来源

Bittensor 官方 releases / whitepaper、SEC EDGAR S-3 与 GTAO S-1、CoinGecko/CoinCodex/CryptoSlate/Bybit/MEXC/Revolut 2026-10 快照、Khala Research、Yellow.com 2026 thesis、Own Your Mind、canonical.cc、FalconX、SlowMist、Halborn、FinanceFeeds、TAO Daily。

---

> **免责声明**：本报告基于公开数据整理，所有数字与事件均标注来源，但部分 ATH 口径、内部人事件、OTF 注册地等待验证。加密货币波动剧烈，存在归零、监管、黑客等多重风险。本报告**不构成任何投资建议**，据此操作风险自担。
