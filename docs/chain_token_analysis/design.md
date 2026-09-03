# 链上新发代币分析子系统 · 设计文档

> 日期：2026-09-02 · 目标链：BNB Chain / Solana / Robinhood Chain
> 复用：`claude_trading` 既有 `src/`（api / data / research / analysis / report）与上一轮架构评审的「维度注册表 + 通用加权器 + band 打分器」模式（ADR-002）

---

## 0. 背景与定位

用户需要一套**自动化工具**：输入「链 + 代币符号」或「链地址」，自动完成数据抓取 → 多维度分析（欺诈 / 趋势 / 技术创新 / 类别）→ 投资决策建议 → 生成报告。

三条目标链的技术画像（决定适配器架构）：

| 链 | EVM 兼容 | 代币标准 | 生态特征 | 主数据源 |
|---|---|---|---|---|
| **BNB Chain** | 是 | BEP-20 (=ERC-20) | Meme / DeFi | BSCScan + DexScreener + PancakeSwap |
| **Robinhood Chain** | 是（Arbitrum Orbit L2，2026-07-01 主网） | ERC-20 | Meme（Noxa.fun）+ RWA（代币化股票） | Alchemy RPC + CoinGecko + Uniswap V3 |
| **Solana** | 否 | SPL Token | Meme（Pump.fun）/ DePIN | Solana RPC + Solscan + RugCheck |

**关键洞察**：BNB 与 Robinhood 同为 EVM，可共用 `EVMAdapter`；仅 RPC 端点、chain_id、区块浏览器 API 不同。Solana 必须独立实现（SPL Token、getProgramAccounts、不同 RPC 方法）。

---

## 1. 整体架构（分层 + 依赖方向）

```
scripts/chain/analyze_token.py        ← CLI 入口（链+符号 / 链地址）
        ↓
src/chain/orchestrator.py             ← 编排：解析→抓取→分析→评级→报告
        ↓
   ┌────────────┬────────────┐
   ↓            ↓            ↓
adapters/    sources/     (复用 src/api)
 链适配        DEX/安全       coingecko/twitter/reddit
   ↓            ↓
   └─────┬──────┘
         ↓
src/chain/{security, trend, momentum, liquidity_health, taxonomy, innovation, sentiment, community}
   八维分析 → 各产出 0-10 维度分 + 证据（缺失维度标记 missing）
         ↓
src/chain/scoring/{dimension, pipeline, band}   ← 通用加权器（ADR-002）
         ↓
src/chain/advisor.py                  ← 决策建议（复用 advice 框架 + 强制免责声明）
         ↓
src/chain/report.py                   ← 自包含 HTML 报告（Chart.js）
```

**依赖纪律**：`adapters` 与 `sources` 互不依赖，只被 `orchestrator` 与五维分析消费；五维分析只依赖 `src/chain/types.py`（数据模型）和 `scoring`；任何数据源失败 → 优雅降级（该维度标记 `missing`，不崩）。

---

## 2. 链适配器设计

### 2.1 抽象基类 `ChainAdapter`

```python
class ChainAdapter(ABC):
    chain: str                      # "bnb" | "sol" | "robinhood"
    def resolve(self, query: str) -> TokenRef: ...
        # query 可以是符号（如 "CASHCAT"）或地址；返回合约地址 + 基础信息
    def get_token_profile(self, address: str) -> TokenProfile: ...
        # 名称/符号/总量/持币地址数/流动性/创建时间
    def get_holders(self, address: str) -> HolderStats: ...
        # top10/top50 占比、creator 持仓、snipe 比例
    def get_contract_security(self, address: str) -> ContractSecurity: ...
        # 是否开源验证、owner renounce、mint 权限、买卖税、honeypot 嫌疑
    def get_liquidity(self, address: str) -> LiquidityInfo: ...
        # 总流动性、LP 锁定比例/期限、burned
```

### 2.2 EVM 适配器（BNB + Robinhood 共用）

`EVMAdapter` 封装：JSON-RPC（`eth_call` / `eth_getCode` / `eth_call` 读 ERC-20 标准函数）、
`getContractSourceCode`（浏览器 API 验开源）、持币分布通过 `eth_getBalance` + `balanceOf` 抽样或浏览器 API。
- `BnbChainAdapter(EVMAdapter)`：chain_id=56, explorer=BSCScan API
- `RobinhoodChainAdapter(EVMAdapter)`：chain_id=待填（Arbitrum Orbit 系），RPC=Alchemy/公共端点，explorer 待接入

> Robinhood Chain 的 chain_id / 公共 RPC / 浏览器 API 文档未明示，在 adapter 中留 `TODO` 配置位（读 `config/settings.yaml` 的 `chains.robinhood.rpc`），默认降级到 CoinGecko「Robinhood Chain」分类兜底。

### 2.3 Solana 适配器

独立实现：`getAccountInfo` / `getTokenSupply` / `getProgramAccounts`（SPL Token Program）、
持币分布经 `getTokenLargestAccounts`。安全维度走 `RugCheck` 专用 API。

---

## 3. 数据源

| 数据 | 来源 | 失败降级 |
|---|---|---|
| DEX 价格/流动性/买卖比/多周期涨跌/买卖笔数 | DexScreener API（按地址自动识别链） | 链上 RPC 估算 / 标记 missing |
| 安全审计（owner/mint/税/honeypot/集中度） | GoPlus Security API（多链） | 链上 `get_contract_security` 兜底 |
| 价格/市值/类别标签 | CoinGecko（复用 `src/api/coingecko`） | 仅链上数据 |
| 社媒情绪 | Twitter / Reddit（复用 `src/api`） | 无社媒维度 |
| 合约新颖性/文档 | GitHub（复用 `src/analysis/github_analyzer`） | 无创新维度 |

所有 source 统一 `safe_call`：`try/except` → 返回 `(data, None)` 或 `(None, error)`，绝不抛栈。

**DexScreener 取数铁律（实战踩坑后写入）**：
- **计价币优先**：多交易对中优先选「稳定币/主流币（USDT/USDC/BNB/ETH/SOL）计价」的对，再按流动性排序。不能直接取"最高流动性 pair"——否则会选到 obscure 计价币（如 QQQB）导致价格/涨跌字段全部错乱。
- **价格异常校验**：`price_usd × total_supply` 与 DexScreener 返回的 `fdv` 背离 > 50% 时，判定报价不可信，打 `price_anomaly` 标，改用 `fdv / total_supply` 反推单价（见 orchestrator 装配逻辑）。
- **全字段抓取**：`price_changes{m5,h1,h6,h24}`、`txns{h1,h24}` 买卖笔数、`market_cap`、`pairCreatedAt`（→ 币龄）、`socials`、`image`。

---

## 4. 八维分析模型（Meme 场景从 5 维扩展到 8 维）

> 原设计 5 维（security/trend/innovation/taxonomy/sentiment）在实战中无法刻画新发 Meme 的核心风险。
> 2026-09-02 审计真实案例后新增 3 个 Meme 专项维度：**momentum（多周期动量）/ liquidity_health（流动性健康）/ community（社区基础）**，并对 security 增加「数据完整度折扣」。

### 4.1 欺诈检测（Security）—最核心、权重最高

聚合 `GoPlus` + `get_contract_security` + `get_holders`，输出 0-10 安全分（越高越安全）及红旗清单：

**数据完整度折扣（诚实性修正）**：当仅能从链上 RPC 拿到「owner 是否已放弃」这一条证据（GoPlus 不索引该币时常见），而 `mint/税率/honeypot/持币集中度/LP锁仓` 全部未知时，不得给满分 10。满足「已知字段数 < 3 且无红旗」时，安全分上限压到 **7.0** 并输出告警，避免"单证据虚高"。

| 红旗 | 检测方式 | 权重 |
|---|---|---|
| 合约未开源 | 浏览器 API `is_verified` | 高 |
| Owner 未放弃且可 mint | GoPlus `can_take_back_ownership` / `is_mintable` | 高 |
| 买卖税异常（>10% 或买≠卖） | GoPlus `buy_tax`/`sell_tax` | 高 |
| Honeypot（无法卖出） | GoPlus `hidden_honeypot` / 模拟卖出 | 致命 |
| LP 未锁定/未 burn | `get_liquidity` 锁仓比例 | 高 |
| 持币集中度过高（top10>50%） | `get_holders` | 中 |
| 创建者/团队大额持仓未披露 | creator 占比 | 中 |
| 早期 snipe 比例过高 | 前 N 块买入占比 | 中 |
| 被列入钓鱼/黑名单库 | GoPlus `is_in_dex` / 黑名单 | 高 |

### 4.2 趋势（Trend）

复用 `src/analysis/technical.py` 的 RSI/MA 逻辑，输入来自 DEX 历史 + 链上：价格斜率、成交量/流动性增长、买卖比净流入、巨鲸动向（复用 `whale_monitor`）。输出趋势强度 0-10 + 阶段性（吸筹/拉升/出货）。

### 4.3 技术创新（Innovation）

- 合约机制新颖性：标准 ERC-20/SPL vs 自定义逻辑（如 rebase、税改、hook）
- 叙事契合度：AI / RWA / DePIN / Meme / GameFi（复用 `token_classification` 27 类映射）
- 工程成熟度：GitHub 活跃度（复用 `github_analyzer`）、文档、路线图、审计披露

### 4.4 类别（Taxonomy）

复用 `src/research/token_classification.py` 的 27 类 → 8 大族权重，叠加链上标签（Meme/DeFi/RWA/Infra），决定该代币适用的维度权重配置。

**中文 Meme 识别（实战补强）**：原词表仅覆盖英文（pepe/doge/inu…）。真实案例「牛来」含"牛"被判 `Uncategorized`，已扩展中文动物/情绪词表（牛/龙/狗/猫/蛙/猪/虎/蛇/羊/熊/兔/鼠/马/鸡/猴/鱼/蟹/熊猫/佛/财/福/喜/涨/富/宇宙/火箭/moon/elon…）。且 `classify()` 回退读取 `ctx.profile.name`（地址查询时顶层 symbol/name 为空）。

### 4.5 情绪（Sentiment）

复用 `src/api/twitter.py` + `reddit_free.py`：社交提及增长、情绪极性、KOL 转向。Meme 币情绪权重显著高于 RWA。
**当前状态**：需 Twitter/Reddit 凭证，本环境未接入 → 维度恒为 `missing`、排除加权（不阻塞流程）。

### 4.6 多周期动量（Momentum）— Meme 专项

基于 DexScreener `price_changes{m5,h1,h6,h24}` 与近 1h 买卖笔数净流入，刻画短期动能方向与强度。新发 Meme 价格几乎完全由动量驱动，故该维度在 Meme 权重最高（0.18）。

| 信号 | 处理 |
|---|---|
| 多周期同向（≥3 周期涨/跌） | 动能明确向上 +2.0 / 向下 −2.5 |
| 24h 极端拉升 >50% | 逃顶/追高风险 −1.0 |
| 24h 深跌 <−40% | 超卖、反弹机会但非买入信号 +0.5 |
| 近 1h 买盘 > 卖盘 ×1.3 | 动能加分 +1.0；反之 −1.0 |

### 4.7 流动性健康（LiquidityHealth）— Meme 专项

新发 Meme 最大归零风险来自「薄流动性 + 高控盘」。用三个可达指标刻画（全部来自 DexScreener，无需额外授权）：

| 指标 | 健康阈 | 风险阈 |
|---|---|---|
| 流动性 / 市值（或 FDV） | >15% 难操控(+2) | <5% 易被砸盘操控(−2) |
| 24h 换手率（成交量/流动性） | 3–10x 活跃(+0.5) | >10x 疑似对敲/纯短线(−1.5) |
| 绝对流动性深度 | >$500K 滑点可控(+1) | <$50K 易被扫(−2) |

### 4.8 社区基础（Community）— Meme 专项

DexScreener `socials` 里的官方渠道数（Twitter/Telegram/网站）做弱信号：0 渠道 → 无社区基础(3.0)；1 → 4.5；≥2 → 6.0。这是当前 `sentiment` 缺位时的廉价替代信号。


---

## 5. 评级与决策模型

沿用 ADR-002「维度注册表 + 通用加权器 + band」：

```python
# 8 维注册表（权重和为 1.0）
DIMENSIONS = {
  "security":          Dimension(weight=0.28, ...),   # 欺诈权重最高
  "trend":             Dimension(weight=0.13, ...),
  "momentum":          Dimension(weight=0.13, ...),   # 多周期动量
  "liquidity_health":  Dimension(weight=0.10, ...),   # 流动性健康
  "sentiment":         Dimension(weight=0.12, ...),   # 社媒情绪（当前多缺失）
  "innovation":        Dimension(weight=0.12, ...),
  "taxonomy":          Dimension(weight=0.07, ...),   # 类别清晰度，决定权重配置
  "community":         Dimension(weight=0.05, ...),   # 社区基础（弱信号）
}
# 类别权重策略（CATEGORY_WEIGHTS）
Meme = {security 0.25, trend 0.15, momentum 0.18, liquidity_health 0.12,
        sentiment 0.12, innovation 0.05, taxonomy 0.08, community 0.05}
score = weighted_fold(dims, profile)             # 缺失维度显式跳过，不填 3
```

- **综合分** → 风险等级（安全分<4 直接判「高危/欺诈嫌疑」，无论其他维度多高）
- **决策**：BUY / HOLD / SELL（或「不评级-欺诈嫌疑」）
- **建议仓位**：由综合分 + 波动率推导区间
- **触发条件**：如「LP 锁定期<30 天告警」「持币集中度骤升」
- **强制免责声明**：复用 `src/analysis/advice.py` 的免责条款

---

## 6. 报告结构（自包含 HTML，Chart.js）

1. 决策卡（BUY/HOLD/SELL + 风险等级 + 仓位 + 入场/目标/止损）
2. 八维雷达图（security/trend/momentum/liquidity_health/innovation/taxonomy/sentiment/community）
3. 数据卡片：**计价币（如 USDT）标注**、币龄（链上 `pairCreatedAt` 推算）、24h 买卖笔数、价格、市值/FDV、流动性、成交量、24h 涨跌、持币地址数、LP 锁仓、买卖比
4. **价格异常横幅**：`price_anomaly` 触发时高亮提示"DexScreener 报价不可信，已改用 FDV 反推"
5. **多周期涨跌表**：m5 / h1 / h6 / h24 涨跌幅 + 24h 买卖笔数（买 买/卖 卖）
6. 欺诈红旗清单（逐项 + 严重度）+ 安全数据完整度告警
7. 多空/决策理由文本（逐维度证据）
8. 关键催化剂 & 风险事件 + 数据来源 + 强制免责声明

---

## 7. 分阶段实现路线（对应任务）

| 任务 | 内容 | 产物 |
|---|---|---|
| #1 | 本设计文档 | `docs/chain_token_analysis/design.md` |
| #2 | 链适配器层 | `src/chain/adapters/*` |
| #3 | 数据源接入 | `src/chain/sources/*` |
| #4 | 评分引擎 + 五维分析 | `src/chain/scoring/*` + `security/trend/taxonomy/innovation/advisor` |
| #5 | CLI + HTML 报告 | `scripts/chain/analyze_token.py` + `src/chain/report.py` |
| #6 | 端到端验证 | demo 跑通 + 真实降级 |

**验收**：`python scripts/chain/analyze_token.py --chain bnb --symbol <X>` 或 `--address <0x..>` 自动出报告；
`--demo` 用样例数据跑通全流程以便离线验证框架。新增模块独立、不改现有 433 测试。
