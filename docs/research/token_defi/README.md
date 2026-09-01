# 代币与 DeFi 协议研究框架（token_defi）

> 把「代币经济 / 估值 / 解锁抛压 / 协议对比」这套研究方法论落地为本项目可复用代码。
> 复用既有 `src/api/coingecko.py` 与 `src/api/defillama.py`，不重复实现 HTTP 请求层。

## 1. 代码入口

| 位置 | 作用 |
|---|---|
| `src/research/token_defi.py` | 核心模块：指标计算 + `TokenDefiResearcher` 取数封装 |
| `scripts/research/token_defi_report.py` | CLI：生成 Plotly HTML 报告（或 JSON） |
| `.workbuddy/skills/crypto-token-defi-research/SKILL.md` | WorkBuddy 项目级技能，在本仓库内自动触发 |

## 2. 快速开始

```bash
# 代币研究（代币经济 + 估值 + 涨跌）
python scripts/research/token_defi_report.py --token ethena

# 协议对比（写法 slug 或 slug:coin_id）
python scripts/research/token_defi_report.py --compare uniswap:uniswap curve-dex:curve-dao-token

# 解锁抛压分析
python scripts/research/token_defi_report.py --unlock arbitrum ethena uniswap curve-dao-token

# 输出 JSON（便于程序化消费）
python scripts/research/token_defi_report.py --token ethena --format json
```

产物落盘 `reports/`：`token_research_<ts>.html`、`protocol_compare_<ts>.html`、`unlock_pressure_<ts>.html`。

## 3. Python API 用法

```python
from src.research.token_defi import TokenDefiResearcher

researcher = TokenDefiResearcher()

# 单代币
token = researcher.analyze_token("ethena")
print(token.circulating_ratio, token.dilution_multiple, token.fdv_mc_ratio)

# 协议对比（可带关联治理代币以计算 P/S）
protocols = researcher.compare_protocols([
    {"slug": "uniswap", "coin_id": "uniswap"},
    {"slug": "curve-dex", "coin_id": "curve-dao-token"},
])
for p in protocols:
    print(p.name, p.tvl, p.fees_annualized, p.ps_fdv)

# 解锁抛压
profiles = researcher.unlock_profiles(["arbitrum", "ethena"])
for p in profiles:
    print(p.symbol, p.locked_ratio, p.risk_level)
```

## 4. 核心指标与口径

| 指标 | 公式 | 解读 |
|---|---|---|
| 流通率 | 流通量 / (最大供应量 or 总供应量) | 越低 → 未来解锁抛压越大 |
| 稀释倍数 | (最大供应量 or 总供应量) / 流通量 | 1.5× 即还有 50% 增量供给 |
| FDV/MC | 完全稀释估值 / 市值 | 数学上等于稀释倍数（价格是同一变量），属同一信号 |
| P/S | 估值 / 年化费用 | 需**统一口径**（FDV 或市值），只在同赛道横比 |
| 资本效率 | 年化费用 / TVL | 每单位锁仓创造的费用，DEX 周转效率 |
| 解锁风险分档 | 待解锁占比 ≥50% 高 / ≥30% 中 / <30% 低 | 供应量硬数据，不含 cliff 日期 |

> **口径提醒**：`FDV/MC` 与 `稀释倍数` 在数学上恒等（分子分母同乘价格），
> 报告里同时展示是为可读性，不要当成两个独立信号使用。

## 5. 设计约定

- **纯函数与取数分离**：`circulating_ratio`、`dilution_multiple`、`price_to_sales`、
  `unlock_risk_level` 等均为无网络依赖的纯函数，可直接单测；网络调用只在
  `TokenDefiResearcher` 内。
- **不编造数据**：取不到的一律 `None`，由展示层决定呈现，绝不填占位数字。
- **失败隔离**：`unlock_profiles()` 内单个代币取数失败只跳过并告警，不中断整体。

## 6. 子文档

- [`token-research.md`](token-research.md) — 代币研究方法论（基本面 / 代币经济 / 估值 / 风险）
- [`defi-protocol-research.md`](defi-protocol-research.md) — DeFi 协议方法论（TVL / 收入 / 安全 / 治理 / 赛道模板）
- [`onchain-metrics.md`](onchain-metrics.md) — 链上指标解读（MVRV / NVT / 流向 / 巨鲸）
- [`data-sources.md`](data-sources.md) — 数据源、新增客户端方法与限流约定

## 7. 与其他模块边界

- 本模块只做**研究框架与数据呈现**，不产出交易信号；量化因子见 `src/factors/`。
- 加密**衍生品**（永续 / 资金费率 / 爆仓）不在本模块范围，见 `src/api/coinglass.py` 与 `src/factors/derivatives.py`。
- 评分系统（7 维度）见 `src/analysis/scorer.py`；本模块可作为其输入补充。
