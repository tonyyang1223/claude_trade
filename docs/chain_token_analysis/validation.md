# 链上代币分析子系统 · 验证报告

> 验证时间：2026-09-02 ｜ 环境：`C:/Users/P52S/.workbuddy-ai/binaries/python/envs/default/`（已装 pydantic/requests）
> 范围：src/chain/** 全部模块 + scripts/chain/analyze_token.py 端到端

## 一、验证项与结果

| # | 验证项 | 方式 | 结果 |
|---|---|---|---|
| 1 | 全模块编译 | `py_compile src/chain/**` | ✅ |
| 2 | 导入全链路（无循环 import / 缺失依赖） | import orchestrator+report+dimensions | ✅ |
| 3 | 三链 demo 跑通（bnb/sol/robinhood） | `--demo` | ✅ total 7.7 |
| 4 | CLI 端到端产出 HTML+JSON | `analyze_token.py --demo --json` | ✅ |
| 5 | 欺诈拦截（honeypot/未放弃/高税/集中） | 构造恶意 AnalysisResult | ✅ → 🚫 不建议参与，仓位 0% |
| 6 | 全维度缺失（无链上数据） | 空 AnalysisResult | ✅ → 🔴 回避，不崩溃 |
| 7 | 优质币高分 | 开源+锁池+分散+温和趋势 | ✅ total 8.2 → 小仓试探 |
| 8 | 真实地址直查降级（无 RPC/网络） | 42 位 BNB 地址，超时 3s | ✅ 优雅降级，不抛异常 |
| 9 | HTML 渲染正确性 | 检查 gauge 角度/radar 数据/免责声明 | ✅ 277°（7.7×36），无模板残留 |

## 二、验证中发现并修复的 4 个缺陷

### 缺陷 1（致命）：类型模块相对导入层级错误
- **现象**：`src/chain/*.py`（advisor/security/trend/innovation/sentiment/taxonomy）写 `from ..types import`，
  但 `types.py` 物理位于 `src/chain/types.py`，`..types` 指向不存在的 `src.types` → 整个子系统 import 失败。
- **修复**：6 个浅层模块改为 `from .types import`（`scoring/`、`adapters/`、`sources/` 子包内的 `..types` 已正确指向 `src.chain.types`，未动）。

### 缺陷 2（严重）：综合分尺度错误（×10 越界）
- **现象**：`pipeline.py` 在已归一化的加权均值上又乘 `* 10.0`，综合分算出 77.0（应为 0-10）。
- **原因**：权重和为 1.0、各维度分已为 0-10，加权均值本身就是 0-10 尺度，多乘 10 越界。
- **修复**：删除 `* 10.0`，仅按剩余权重归一。

### 缺陷 3（中等）：空模型对象虚高安全分
- **现象**：无网络时适配器返回"全字段 None 的空 ContractSecurity 对象"（非 None），
  `analyze_security` 因 `any([sec, ...])` 把空对象当真值，给了满分 10，虚高综合分。
- **修复**：新增真实信号检测（至少有一个非 None 字段才计分），否则判缺失、排除出加权。

### 缺陷 4（低级）：两处隐患清理
- `solana.py`：删除未使用的 `import base58`（避免无该包时 ImportError）。
- `goplus.py`：修正 `is_in_blacklist` 反逻辑表达式（`_as_bool(...is False or None`）→ 改用 `is_honeypot` 字段，避免误判致命红旗。

另：`advisor.decide()` 返回值补上 `missing` 字段（CLI 与 report 都依赖）。

## 三、已知限制（非缺陷，属设计取舍）

1. **`sentiment` 维度当前恒为缺失**：真实社媒情绪需 Twitter/Reddit 凭证且触网，
   设计为优雅跳过（返回 None，排除出加权），不阻塞流程。后续阶段接入 `src/api/twitter.py` 等。
2. **Robinhood Chain 适配**：EVM 兼容（Arbitrum Orbit），复用 EVM 适配器；但主网 chain_id / 公共 RPC /
   浏览器 API 官方未明示，当前 `chain_id=0`、`explorer_api=None`，需 `config/settings.yaml` 注入
   `chains.robinhood.rpc`。DexScreener/GoPlus 暂未索引该链，按地址直查 + 链上 RPC 降级。
3. **趋势维度**基于 DEX 24h 报价（无历史 K 线时为 best-effort）；完整 K 线技术指标需复用
   `src/analysis/technical.py`，留待后续阶段接入 OHLC 历史。

## 四、实战审计与二次修复（2026-09-02 晚，真实 BNB 合约 0xbeea…7777「牛来」）

首轮验证（demo 全绿）后，用真实链上合约跑了端到端分析，发现**初版报告存在 4 处实质性错误**——根因是 DexScreener「无脑取最高流动性交易对、且不校验计价币」。

### 审计发现（报告错在哪）

| 字段 | 初版（错） | 抓取原始返回后（真实） | 根因 |
|---|---|---|---|
| 价格 | $703.81 | **$0.0734（USDT 计价）** | 选了 obscure 计价币 QQQB 的交易对（最高流动性），报价单位错乱 |
| 24h 涨跌 | −1.0% | **−19.71%** | 同上，选错交易对导致涨跌取自错误池 |
| 买卖比 | 0.656（卖方占优） | **1.26（买方笔数占优，21683 买 vs 17193 卖）** | 24h 笔数未抓取，用 1h 近似反推且方向反了 |
| 类别 | Uncategorized | **Meme** | "牛来"含"牛"，原词表只有英文 Meme 词 |

另两类**诚实性问题**：
- 安全维度仅凭 `owner 已放弃` 一项证据就给 10 分（GoPlus 对该币返回 404 不索引，mint/税率/honeypot 全未知）；
- 未抓取币龄（真实仅 **17.5 天**新发币，Meme 关键风险信号）。

### 二次修复（已落地）

| # | 修复 | 文件 | 效果 |
|---|---|---|---|
| R1 | DexScreener 选对逻辑：稳定币/主流币计价优先 + 流动性排序；记录 `quote_symbol`；全字段抓取（m5/h1/h6/h24 涨跌、买卖笔数、MC、币龄、社媒、图标） | `sources/dexscreener.py`（重写） | 价格/涨跌/买卖比正确，新增计价币与币龄展示 |
| R2 | 价格一致性校验：orchestrator 装配时 `price_usd×总量` 与 `fdv` 背离 >50% → 打 `price_anomaly` 标并改用 FDV 反推单价 | `orchestrator.py` | 报价异常可识别、不污染估值 |
| R3 | 安全维度「数据完整度折扣」：已知字段数 <3 且无红旗 → 安全分上限压到 7.0 并告警 | `security.py` | 单证据不再虚高满分 |
| R4 | 中文 Meme 词表 + `classify()` 回退读 `ctx.profile`；orchestrator 用 profile 回填顶层 symbol/name | `taxonomy.py` / `orchestrator.py` | 地址查询也能正确归类 |

### 新增 3 个 Meme 专项维度（权重表扩到 8 维）

| 维度 | 文件 | 本案例得分 | 关键证据 |
|---|---|---|---|
| 多周期动量 momentum | `momentum.py` | 3.5 | 近 4 周期普跌（m5 −3.85 / h1 −9.36 / h6 −12.69 / h24 −19.71），动能向下 |
| 流动性健康 liquidity_health | `liquidity_health.py` | 2.5 | 流动性/市值仅 2%（易被砸盘）、24h 换手 22x（疑似对敲） |
| 社区基础 community | `community.py` | 5.5 | DexScreener 渠道数弱信号 |

修复后重跑：类别 = **Meme**，综合分 **5.1/10 → 🟡 轻仓观察 · 1%–3%**（初版误判为 6.5 → 🟡 持有/观察 3%–5%）。

### 二次验证结果（编译 + 端到端）

- ✅ `py_compile src/chain/**` 全过
- ✅ demo 路径回归：CASHCAT 正确归类 Meme，8 维评分齐全
- ✅ 真实合约重跑：价格/涨跌/买卖比/类别全部校正，安全分因数据不完整从 10 降到 7 并告警
- ✅ 8 维雷达 / 计价币标注 / 币龄 / 买卖笔数 / 多周期表 / 价格异常横幅 均正确渲染

## 五、三次修复（2026-09-03，Robinhood 链 STRATTON `0xb7ea…b8360` 实战审计）

BNB 案例验证的是 EVM+GoPlus 覆盖的成熟链；Robinhood 是一条**官方参数未沉淀、GoPlus 未索引、计价币非标**的新链，暴露了一批新缺陷。

### 关键事实更正

- **DexScreener 已索引 robinhood 链**（此前设计文档/记忆写"未覆盖"，错）。实测返回 30 个交易对。
- **Robinhood Chain 官方参数实测确认**（`eth_chainId` 返回 `0x1237` = 4663）：
  公共 RPC `https://rpc.mainnet.chain.robinhood.com`（本机可达）；浏览器 `robinhoodchain.blockscout.com`（Blockscout，但 `/api/v2` 对脚本客户端 **403**）。已固化进 `adapters/robinhood.py`。

### 审计发现（v1 报告错在哪）

代币 **STRATTON / Stratton Market**，上线约 9 小时，多交易对（SPY/USDG/ETH 计价混合）：

| 字段 | v1（错） | 真实主盘 | 根因 |
|---|---|---|---|
| 交易对 | `STRATTON/ETH`（$22.8K / $2万量 / -7.66%） | `STRATTON/SPY`（$165K / **$944万量** / +9499%） | `_ranked_pairs` 给稳定币 +1e12 硬加成，选中流动性仅主盘 14% 的死对 |
| 代币名 | `—`（Uncategorized） | **STRATTON / Stratton Market** | Robinhood 无浏览器 API → profile 空 → 顶层 symbol/name 为空 |
| 换手率 | "0.9x 相对平稳" | **60x 异常高（疑似对敲）** | 选错死对导致成交量字段只取到 $2万 |
| 安全 | 0 项证据 → 上限 7.0 | 链上可证：**无 mint / 无 owner / 无 proxy / 无 pause** | 适配器未做字节码扫描，白白浪费可达的 RPC |

### 三次修复（已落地）

| # | 修复 | 文件 | 效果 |
|---|---|---|---|
| R5 | 交易对选择：流动性门槛(>=最大流动性10%) → 24h 成交量主排序 → 稳定币 1.15x 温和加成 → 流动性次之 | `sources/dexscreener.py` | 选中真实主盘；价格/涨跌/换手率全部校正 |
| R6 | 代币身份回填：`DexQuote` 加 base_symbol/base_name，orchestrator 用 DEX 数据回填 symbol/name；并用 fdv/price 反推 total_supply（仅展示，不进价格校验，避免循环论证） | `types.py` / `orchestrator.py` | 无 RPC 的链也能显示代币名、不再 Uncategorized |
| R7 | 超新币 h24 失真：age<1 天时 h24 实为「自发行价」涨幅（+9499%），方向判定改用 m5/h1/h6；trend 维度改用 h6 并标注口径 | `momentum.py` / `trend.py` | 动能/趋势不再被上线基数效应污染 |
| R8 | 链上字节码特权函数扫描：`_RISK_SELECTORS` 扫 mint/proxy/blacklist/pause/tax 选择器，任意 EVM 链通用、不依赖 GoPlus/浏览器 API | `adapters/evm.py` / `types.ContractSecurity` | GoPlus 404 的链也能拿到「无增发/无后门」硬证据 |
| R9 | Robinhood 适配器接入官方 RPC（chain_id=4663）；USDG 加入 _STABLE 白名单 | `adapters/robinhood.py` / `sources/dexscreener.py` | Robinhood 走真链上数据，不再降级空模型 |
| R10 | 安全分诚实性 + 风险护栏：① LP 锁仓与持币集中度均未知 → 安全分上限压至 7.5（旧版仅扣 0.5）；② advisor 加护栏（age<1天 / liquidity_health<3 / age<7天且LP未知）只降不升 | `security.py` / `advisor.py` | 修复 STRATTON 由误判「持有/观察 3-5%」纠正为「🔴 回避 0%」 |

### 三次验证结果

- ✅ 编译全过；demo 三链回归一致（CASHCAT/DEMO/RHDEMO 均 7.02 → 持有/观察）
- ✅ STRATTON：链上 totalSupply = **10 亿枚**（直读）；字节码扫描 **无 mint/无 owner/无 proxy/无 pause**；
  综合分 **4.95 → 🔴 回避 · 0%**；安全 7.5 / trend 4.0 / momentum 5.0 / liquidity_health 1.5
- ✅ BNB 牛来回归：5.5 → 🟡 轻仓观察 1-3%（与二次验证结论一致，未回归；且新增字节码证据）
- ⚠️ Blockscout `/api/v2` 403 → 持币集中度/LP 锁仓仍不可得（后续可改 RPC 扫 Transfer 事件）

## 六、如何运行

```bash
# 离线跑通框架（不触网，内置样例）
python scripts/chain/analyze_token.py --demo --chain bnb --symbol CASHCAT --out reports/chain_token_analysis/bnb_CASHCAT_demo.html --json

# 按「链 + 代币符号」联网分析
python scripts/chain/analyze_token.py --chain bnb --symbol CAKE

# 按「链 + 合约地址」
python scripts/chain/analyze_token.py --chain sol --address <mint地址>

# 一条命令：先链后查询
python scripts/chain/analyze_token.py bnb CAKE
python scripts/chain/analyze_token.py sol <mint地址>
```

支持链：`bnb`(bsc) / `sol`(solana) / `robinhood`(Arbitrum Orbit EVM)。
