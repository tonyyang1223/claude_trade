# 因子计算引擎适配更多币种设计

> **创建日期**: 2026-06-09
> **状态**: 待审核

---

## 1. 概述

### 1.1 目标

扩展因子计算引擎，支持更多币种：
- 为链上因子（TVL、稳定币流动）增加降级逻辑，使用链数据作为代理
- 为所有因子增加数据量要求属性，数据不足时返回 NaN 而非报错

### 1.2 背景

当前因子计算主要针对 BTC/ETH 等主流资产：
- `COIN_TO_DEFILLAMA` 仅映射约 20 个币种
- 大量小币种无 TVL 数据 → 返回 0 或计算失败
- 无数据量检查 → 新币种可能因历史数据不足导致异常值

### 1.3 范围

- TVL 因子降级逻辑（协议 → 链 → NaN）
- stablecoin_flow 按链区分
- 数据量检查（min_days, min_points）
- 链解析逻辑（硬编码 + CoinGecko API）

---

## 2. 详细设计

### 2.1 FactorMetadata 扩展

**文件**: `src/factors/models.py`

在 `FactorMetadata` 中添加属性：

```python
@dataclass
class FactorMetadata:
    # ... 现有属性 ...
    min_days: int = 0          # 最小历史天数要求（0 表示无要求）
    min_points: int = 0        # 最小数据点数量要求（0 表示无要求）
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `min_days` | int | 0 | 需要 X 天历史数据才能计算 |
| `min_points` | int | 0 | 需要 X 个数据点才能计算 |

### 2.2 链解析逻辑

**文件**: `src/data/coin_mappings.py`

**扩展 COIN_TO_CHAIN 映射**：

```python
COIN_TO_CHAIN = {
    # Layer 1 链原生代币
    "ethereum": "Ethereum",
    "solana": "Solana",
    "avalanche-2": "Avalanche",
    "polygon": "Polygon",
    "binancecoin": "BSC",
    "arbitrum": "Arbitrum",
    "optimism": "Optimism",
    "cosmos": "Cosmos",
    "fantom": "Fantom",
    "cardano": "Cardano",
    "polkadot": "Polkadot",
    "near": "Near",
    # ERC-20 代币（Ethereum 链）
    "uniswap": "Ethereum",
    "aave": "Ethereum",
    "compound": "Ethereum",
    "makerdao": "Ethereum",
    "curve": "Ethereum",
    "lido": "Ethereum",
    "chainlink": "Ethereum",
    "rocket-pool": "Ethereum",
}

# 链名称到 DefiLlama 链名称的映射
CHAIN_TO_DEFILLAMA = {
    "Ethereum": "Ethereum",
    "Solana": "Solana",
    "Avalanche": "Avalanche",
    "Polygon": "Polygon",
    "BSC": "BSC",
    "Arbitrum": "Arbitrum",
    "Optimism": "Optimism",
    "Cosmos": "Cosmos",
    "Fantom": "Fantom",
    "Cardano": "Cardano",
    "Polkadot": "Polkadot",
    "Near": "Near",
}
```

**文件**: `src/api/coingecko.py`

**添加获取 asset_platform_id 方法**：

```python
def get_asset_platform(self, coin_id: str) -> Optional[str]:
    """获取代币所在的链平台ID"""
    # 调用 /coins/{id} 接口，返回 asset_platform_id
```

**链解析函数**（放在 `src/factors/onchain.py`）：

```python
def resolve_chain(coin_id: str) -> Optional[str]:
    """解析币种所在的链
    
    优先级:
    1. COIN_TO_CHAIN 硬编码映射
    2. CoinGecko asset_platform_id API
    
    Returns:
        DefiLlama 链名称或 None
    """
```

### 2.3 TVL 降级逻辑

**文件**: `src/factors/onchain.py`

**compute_tvl_change_7d 降级链**：

1. 协议 TVL（如果 `COIN_TO_DEFILLAMA` 有映射）
2. 链 TVL（如果 `resolve_chain` 能解析）
3. NaN（无数据时）

### 2.4 stablecoin_flow 按链区分

**文件**: `src/factors/onchain.py`

**compute_stablecoin_net_flow**：

- 如果有 `coin_id` 参数，返回该链的稳定币流动
- 如果无 `coin_id` 或无法解析链，返回全局数据

### 2.5 数据量检查逻辑

**文件**: `src/factors/engine.py`

**compute_factor 方法**：

1. 检查 `historical_values` 的数据点数量
2. 检查 `historical_values` 的唯一天数
3. 不满足要求时返回 NaN + confidence=0 + debug 日志

---

## 3. 实现方案

**方案**: 最小改动，修改现有文件（方案 A）

**改动文件**:
| 文件 | 改动内容 |
|------|----------|
| `src/factors/models.py` | 添加 `min_days`, `min_points` 属性 |
| `src/factors/onchain.py` | TVL/stablecoin_flow 降级逻辑，添加 `resolve_chain` 函数 |
| `src/factors/engine.py` | 数据量检查逻辑 |
| `src/data/coin_mappings.py` | 扩展 `COIN_TO_CHAIN`，添加 `CHAIN_TO_DEFILLAMA` |
| `src/api/coingecko.py` | 添加 `get_asset_platform` 方法 |

---

## 4. 测试计划

| 测试场景 | 验证点 |
|----------|--------|
| 有协议映射的币种 | 返回协议 TVL |
| 无协议但有链映射的币种 | 返回链 TVL |
| 无任何映射的币种 | 返回 NaN，confidence=0 |
| CoinGecko asset_platform_id | 正确解析链 |
| 数据量不足 | 返回 NaN，debug 日志记录 |
| 数据量充足 | 正常计算 |

---

## 5. 风险与约束

| 风险 | 缓解措施 |
|------|----------|
| CoinGecko API 调用增加延迟 | 缓存 asset_platform_id 结果 |
| NaN 影响评分计算 | 评分器需处理 NaN 值 |