# 数据源与 API 调用约定（data-sources）

> 本模块（`src/research/token_defi.py`）复用了项目已有的两个 API 客户端，
> 并为研究场景补充了两个方法。本文档记录可用数据源、新增方法、限流与调用纪律。

## 1. 免 key 数据源（当前使用）

### CoinGecko —— 代币行情 / 供应 / 估值

- 端点：`https://api.coingecko.com/api/v3`（`src/api/coingecko.py`）
- 限流：匿名约 5~15 次/分；客户端内置 `MIN_CALL_INTERVAL = 1.2s` 节流。
- 可用于研究的方法：
  - `get_coin_data(coin_id)` — 既有方法：价格 / 市值 / 供应 / 24h 涨跌。
  - **`get_coin_research_data(coin_id)`** — 本次新增：补充 FDV、ATH、7d/30d 涨跌、categories。
- coin id 不确定时先用 `GET /api/v3/search?query=<名称>` 查正确 id。

### DefiLlama —— 协议 TVL / 费用 / 稳定币流向

- 端点：`https://api.llama.fi`（`src/api/defillama.py`）
- 免 key、无硬限流（但短时间内高频调用会触发 Cloudflare 400，需退避重试）。
- 可用于研究的方法：
  - `get_protocol_tvl(slug)` — 既有方法：TVL、24h/7d 变化、各链分布。
  - **`get_protocol_fees(slug, aggregate_versions=True)`** — 本次新增：
    从 `/overview/fees` 取费用，并自动聚合 `<slug>-v<N>` 子版本。
  - `get_stablecoin_flows()` / `get_chain_stablecoin_flows(chain)` — 稳定币流向。
  - `get_protocol_slug(coin_id)` — 代币 id → 协议 slug 映射。

## 2. 新增方法说明（本次整合加入）

| 方法 | 所属客户端 | 为什么需要 |
|---|---|---|
| `get_coin_research_data()` | `CoinGeckoClient` | 原 `get_coin_data()` 无 FDV / ATH / 30d 涨跌，研究估值必需 |
| `get_protocol_fees()` | `DefiLlamaClient` | `/protocol/{slug}` 不返回费用；Uniswap 只有 v1–v4 子项，需聚合 |

两者均为**纯新增方法**，不修改既有方法的返回契约，对现有调用方无破坏性变更。

### 父协议费用聚合规则

`get_protocol_fees(slug, aggregate_versions=True)` 会把形如 `<slug>-v<数字>` 的条目一并求和，
结果中的 `included_slugs` 列出实际参与聚合的子项，便于核对口径。
例：`get_protocol_fees("uniswap")` → `included_slugs: [uniswap-v1, uniswap-v2, uniswap-v3, uniswap-v4]`。

关闭聚合（`aggregate_versions=False`）则只取精确 slug。

## 3. 缓存

- `DefiLlamaClient` 使用 `data/cache` 目录做结果缓存（默认 `Path("data/cache")`），
  缓存键含方法维度（如 `protocol_fees_uniswap_True`），避免重复打 API。
- 调试时若需强制刷新，清掉对应缓存文件或临时改用 `aggregate_versions` 之外的参数键。

## 4. 需 key 的增强源（按需接入）

| 源 | 用途 | 接入方式 |
|---|---|---|
| **Etherscan API** | 地址余额 / 交易 / 合约校验 / 持有者 | `ETHERSCAN_KEY` 环境变量 |
| **Dune Analytics** | 自定义链上 SQL 看板 / 持有者分布 | `DUNE_KEY` |
| **Token Terminal / Artemis** | 协议收入 / P/S / 现金流（订阅制） | 官方 API key |
| **Nansen / Arkham** | 巨鲸身份标签 / 资金流向身份 | 付费 SaaS + API |
| **Glassnode** | MVRV / NUPL 等链上指标 | 付费 API |
| **TokenUnlocks** | **精确解锁日历与 cliff 日期** | 需 key；本模块当前只用供应量硬数据算稀释，未接入 |

> 接入规范：key 一律从 `os.environ` 读取，**不写进代码、不提交到 Git**。

## 5. 调用纪律

- **标注来源 + 时点**：输出每个数字时附来源与数据时点（报告模板已内置 `fetched_at` 与来源标注）。
- **延迟声明**：免费 API 多为准实时（分钟~小时级），链上指标滞后 1~2 天。
- **限流退避**：遇到 429 / Cloudflare 400，退避重试，不要死循环狂打。
- **失败兜底**：客户端返回 fallback 结构且 `confidence` 低（0.1）；研究模块对缺失字段一律置 `None`，
  **不编造数字**。
- **跨源交叉校验**：TVL / 市值这类关键数，能交叉就用两个源核对，分歧时标注。

## 6. 常见 coin id / protocol slug

- 代币 id：bitcoin, ethereum, solana, uniswap(UNI), curve-dao-token(CRV), ethena(ENA), arbitrum(ARB)
- 协议 slug：uniswap, curve-dex, aave, lido, makerdao, gmx, convex, yearn-finance
- 注意：**slug 与代币 id 不同**（如 Uniswap 协议 slug=`uniswap`、代币 id 也=`uniswap`；
  但 Curve 协议 slug=`curve-dex`、代币 id=`curve-dao-token`）。
