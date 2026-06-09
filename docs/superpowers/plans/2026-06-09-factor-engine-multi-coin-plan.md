# 因子引擎多币种适配实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展因子计算引擎，为 TVL 和 stablecoin_flow 因子增加降级逻辑，添加 min_days/min_points 数据量检查

**Architecture:** 在现有因子系统中添加链解析逻辑（硬编码 + CoinGecko API），修改 onchain.py 增加降级逻辑，修改 engine.py 增加数据量检查

**Tech Stack:** Python 3.9+, pytest, logging

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `src/factors/models.py` | FactorMetadata 扩展，添加 min_days/min_points |
| `src/data/coin_mappings.py` | 扩展 COIN_TO_CHAIN，添加 CHAIN_TO_DEFILLAMA |
| `src/api/coingecko.py` | 添加 get_asset_platform 方法 |
| `src/factors/onchain.py` | 添加 resolve_chain 函数，修改 TVL/stablecoin_flow 计算 |
| `src/factors/engine.py` | 添加数据量检查逻辑 |
| `tests/test_factor_multi_coin.py` | 新建测试文件 |

---

## Task 1: 扩展 FactorMetadata

**Files:**
- Modify: `src/factors/models.py`

- [ ] **Step 1: 修改 FactorMetadata dataclass**

添加 `min_days` 和 `min_points` 属性到 `FactorMetadata` 类。

- [ ] **Step 2: 更新 to_dict 方法**

添加新属性到 `to_dict` 返回值。

- [ ] **Step 3: Commit**

```bash
git add src/factors/models.py
git commit -m "feat(factors): add min_days and min_points to FactorMetadata"
```

---

## Task 2: 扩展链映射

**Files:**
- Modify: `src/data/coin_mappings.py`

- [ ] **Step 1: 扩展 COIN_TO_CHAIN 映射**

添加更多 Layer 1 和 ERC-20 代币映射。

- [ ] **Step 2: 添加 CHAIN_TO_DEFILLAMA 映射**

添加链名称到 DefiLlama 链名称的映射。

- [ ] **Step 3: Commit**

```bash
git add src/data/coin_mappings.py
git commit -m "feat(mappings): expand COIN_TO_CHAIN and add CHAIN_TO_DEFILLAMA"
```

---

## Task 3: 添加 CoinGecko get_asset_platform 方法

**Files:**
- Modify: `src/api/coingecko.py`

- [ ] **Step 1: 添加 get_asset_platform 方法**

在 CoinGeckoClient 类中添加获取 asset_platform_id 的方法。

- [ ] **Step 2: Commit**

```bash
git add src/api/coingecko.py
git commit -m "feat(coingecko): add get_asset_platform method"
```

---

## Task 4: 添加 resolve_chain 函数

**Files:**
- Modify: `src/factors/onchain.py`

- [ ] **Step 1: 添加 imports 和 logger**

- [ ] **Step 2: 添加 resolve_chain 函数**

实现链解析逻辑（硬编码优先，CoinGecko API 备用）。

- [ ] **Step 3: Commit**

```bash
git add src/factors/onchain.py
git commit -m "feat(factors): add resolve_chain function"
```

---

## Task 5: 修改 compute_tvl_change_7d 添加降级逻辑

**Files:**
- Modify: `src/factors/onchain.py`

- [ ] **Step 1: 修改 compute_tvl_change_7d 函数**

添加协议 TVL → 链 TVL → NaN 降级逻辑。

- [ ] **Step 2: 修改 compute_protocol_tvl 函数**

添加相同降级逻辑。

- [ ] **Step 3: Commit**

```bash
git add src/factors/onchain.py
git commit -m "feat(factors): add fallback logic to TVL factors"
```

---

## Task 6: 修改 compute_stablecoin_net_flow 按链区分

**Files:**
- Modify: `src/factors/onchain.py`

- [ ] **Step 1: 修改 compute_stablecoin_net_flow 函数**

添加 coin_id 参数，返回链级数据。

- [ ] **Step 2: 修改 compute_stablecoin_total_supply 函数**

添加相同逻辑。

- [ ] **Step 3: Commit**

```bash
git add src/factors/onchain.py
git commit -m "feat(factors): make stablecoin_flow chain-specific"
```

---

## Task 7: 添加数据量检查逻辑

**Files:**
- Modify: `src/factors/engine.py`

- [ ] **Step 1: 添加 logging import**

- [ ] **Step 2: 修改 compute_factor 方法**

添加 min_days 和 min_points 检查，返回 NaN + confidence=0。

- [ ] **Step 3: Commit**

```bash
git add src/factors/engine.py
git commit -m "feat(factors): add data quantity validation"
```

---

## Task 8: 添加单元测试

**Files:**
- Create: `tests/test_factor_multi_coin.py`

- [ ] **Step 1: 创建测试文件**

包含 resolve_chain、TVL fallback、stablecoin_flow、metadata、data quantity 测试。

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/test_factor_multi_coin.py -v`

- [ ] **Step 3: Commit**

```bash
git add tests/test_factor_multi_coin.py
git commit -m "test: add unit tests for factor multi-coin adaptation"
```

---

## Task 9: 集成测试

- [ ] **Step 1: 测试链解析**

- [ ] **Step 2: 测试 TVL 计算**

- [ ] **Step 3: 测试 stablecoin_flow**

- [ ] **Step 4: 运行完整测试套件**

---

## 执行选择

**两种执行方式：**

1. **Subagent-Driven (推荐)** - 为每个任务派发新的 subagent，任务间审查，快速迭代

2. **Inline Execution** - 在当前会话中使用 executing-plans 批量执行，带检查点

**您选择哪种方式？**