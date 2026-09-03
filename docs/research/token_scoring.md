# 代币类型化评估体系 (Type-Aware Token Scoring)

> 配套代码：`src/analysis/`（scorer / profiles / tokenomics / advice）、
> `src/research/`（token_classification / token_defi）、
> `scripts/research/batch_evaluate.py`。

## 1. 设计目标

对多类型代币（CoinGecko 27 个分类）给出**差异化、类型感知**的研究评级，
而不是用同一套 7 维权重去套所有币。核心原则：

- **结构性不适用 ≠ 缺失默认分**：某类型根本没有的维度（如 Meme 不做 GitHub
  活跃度、稳定币不做技术面波动）直接**不评分**，权重按比例重新分配，而不是
  默默给个 3 分污染总分。
- **暂时性缺失 = None，剔除出覆盖**：数据源取不到（网络受限、字段缺失）的维度
  返回 `None`，不计入加权总分，也不计入数据覆盖率。
- **覆盖率封顶**：实际打分维度权重之和（coverage）过低时，下调评级，避免过度自信。
- **研究导向、非投资建议**：任何倾向性结论都必须附带免责声明（红线）。

## 2. 12 个评估维度

| 维度 | key | 说明 | 典型适用类型 |
|------|-----|------|--------------|
| 市场 | `market` | 市值排名 | 全部 |
| 技术 | `technical` | 均线/RSI/趋势/量能 | L1/L2/ETF/AI/Meme… |
| 链上 | `onchain` | NVT/MVRV/活跃地址 | L1/PoS/PoW |
| 情绪 | `sentiment` | 恐惧贪婪/社媒情绪 | 多数 |
| 开发 | `github` | 仓库活跃度 | L1/DeFi/AI/基础设施 |
| 社交 | `social` | Twitter/Reddit 粉丝 | 多数 |
| 风险 | `risk` | 波动/流动性/成熟度 | 全部 |
| 代币经济 | `tokenomics` | 流通率/稀释/解锁 | L1/DeFi/Meme/RWA/ETF |
| 估值 | `valuation` | FDV/MC、P/S | 全部（有快照时） |
| 叙事 | `narrative` | 社媒热度/谷歌趋势 | Meme/AI/GameFi |
| 锚定 | `peg_stability` | 与 $1 偏离 | 稳定币 |
| TVL | `tvl` | 7d TVL 动量 | DeFi/基础设施 |

纯打分函数集中在 `src/analysis/tokenomics.py`，全部返回 `int 1-5` 或 `None`，
**无网络依赖**，便于单测。

## 3. 27 种类型 → 8 大族 (families)

```
l1 (公链) | defi | stablecoin | meme | rwa | ai | infra (基础设施) | gaming (GameFi&NFT) | generic (通用)
```

- `TYPE_FAMILY`：27 种类型 → 族。
- `TYPE_PROFILES`：27 份显式权重表，**每份权重之和严格 = 1.0**。
- `FAMILY_RISK`：每族的基准波动率与单币最大仓位上限（%）。

获取：`get_profile(token_type) -> TypeProfile`，含 `weights`、
`applicable_dims`、`volatility`、`max_position_pct`。

## 4. Scorer 双路径

```
score_project(coin_id, token_type=None)
   ├─ profile 为 None 且未给 token_type  → _score_project_legacy   (原 7 维，byte-for-byte 兼容)
   └─ 否则                              → _score_project_typed    (类型感知，扩展维度)
```

**关键修复（受限网络）**：`Scorer.__init__` 在 **legacy 模式**仍按需创建默认
analyzer；在 **typed 模式**则**原样保存**传入的 analyzer，因此可传 `None` 来
*跳过*被墙的外部数据源（Binance / blockchain.info / alternative.me / GitHub）。
被跳过的 analyzer 对应维度返回 `None`，剔除出总分与覆盖率，而非伪造 3 分。

`_score_typed_dim` 对每个维度：
- `None` analyzer → 直接返回 `None`（跳过）；
- 取数失败（异常/默认对象）→ 返回 `None`（暂时性缺失，同样剔除）。

## 5. 研究建议层 (`src/analysis/advice.py`)

`build_advice(rating, risk_level, coverage, profile)` 产出：

- `action` / `action_code`：重点关注 / 建议关注 / 小仓试探 / 观望 / 回避（研究倾向，非买卖指令）；
- `position_range`：建议仓位区间（占组合 %），由 `(rating, volatility)` 矩阵给出，并受
  `profile.max_position_pct` 封顶；
- `triggers`：触发/关注条件；
- `disclaimer`：固定免责声明，**每次输出必附**。

`apply_coverage_cap`：coverage < 0.40 → 封顶 C；< 0.60 → 封顶 B。

## 6. 使用方法

```bash
# 市值前 N 代币批量评估（默认 20）
python scripts/research/batch_evaluate.py --top 20 --out reports/batch_eval_top20.html

# 单个币深度研究
python scripts/research/batch_evaluate.py --coin binancecoin

# 输出 JSON
python scripts/research/batch_evaluate.py --top 15 --format json
```

受限网络下 `batch_evaluate.py` 默认禁用会卡顿的外部 analyzer，仅评估
CoinGecko 可取的维度（市场/社交/风险/代币经济/估值/锚定），DefiLlama TVL 使用
短超时（8s）失败即跳过。

## 7. 测试

`tests/analysis/` 与 `tests/research/` 下 8 个新增文件覆盖：分类（含 Chainlink
`ai` bug 回归）、profile 权重=1、advice 封顶、tokenomics 纯函数、typed/legacy
双路径、模型新字段、golden 类型映射。全部离线、mock 驱动。
