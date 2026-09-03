# 架构评审报告 · claude_trading

> 评审日期：2026-09-02 · 代码规模 28,563 行 / 80 源文件 / 433 测试
> 方法：AST 依赖解析 + 跨文件重复度扫描 + 全量测试实测，结论均带文件行号

---

## 0. 一句话结论

**这是一个"研究流水线"，却按"平台"的规模在组织。**

真正的生产逻辑集中在 4 个文件里（`scorer.py` 934 行 + `token_defi_report.py` 782 行 + `backtest_simple.py` 753 行 + `visualize_factors.py` 643 行 ≈ 3,112 行，占 11%），
其余 89% 是围绕它们的**三套并行体系**与**各自的横切实现**。
架构优化的方向不是"拆分"，而是**收敛**。

---

## 1. 现状诊断

### P0-1 核心断裂：通用因子框架与生产评分器互不往来

`src/factors/` 是一套设计良好的框架（registry 212 行 / engine 143 行 / store 139 行 / normalization），`src/research/` 的 13 个文件都规规矩矩依赖它。
**但承载生产评分的 `src/analysis/scorer.py` 与 `src/factors` 之间没有任何依赖边**（AST 解析确认），它在 934 行里硬编码了 7 个维度。

```
scorer.py  ✗(无依赖)  factors/  ←  research/ (17 文件)
```

代价：新增一个评分维度要改 `scorer.py` 内部，而不是注册一个因子。付了抽象的税，没享受抽象的好处。

### P0-2 `scorer.py` 内部裂成三条路径

| 路径 | 入口 | 权重表 | 缺失维度语义 |
|---|---|---|---|
| legacy 7 维 | `_score_project_legacy` **337-386** | `DEFAULT_WEIGHTS` **39-47** | 硬编码填 **3** |
| typed 12 维 | `_score_project_typed` **388-466** | `TYPE_PROFILES` **profiles.py:82-120** | 返回 **None** |
| phase1 | `score_project_with_phase1` **903-935** | `PHASE1_WEIGHTS` **50-62** | — |

重复的不仅是分支，是同一份逻辑写了两遍：

- 加权平均：`calculate_weighted_score` **211-245** + `_redistribute_weights` **293-317** vs typed 内联 **422-428**
- 因子贡献：`calculate_factor_contributions` **247-291** vs typed 内联 **454-457**（且字段不对齐，legacy 有 `contribution_pct`，typed 没有）
- TVL 抓取：`_get_tvl` **868-901** vs typed tvl 分支 **515-530**，同为 `get_protocol_slug → get_protocol_tvl → TVLData`

**语义冲突已发生**：`_score_market` **535-538**、`_score_technical` **555-558** 仍 `return 3`，把 legacy 的"缺失即平庸"漏进了声明用 `None` 的 typed 路径。
数据缺失和"打 3 分"在 typed 语义下必须可区分，现在区分不了。

### P0-3 工程化断裂：433 个测试实际一个都跑不起来

实测结果：

```
$ pytest tests/ -q
ERROR tests/test_coingecko.py
ERROR tests/test_coinmarketcap.py
Interrupted: 2 errors during collection      ← 收集阶段中断，0 个测试执行
ModuleNotFoundError: No module named 'responses'
```

`responses` 确实写在 `requirements.txt` 里，但环境没装 —— 而**两个模块的 ImportError 会让整个测试套件拒绝执行**。
绕过这两个模块后 433 个测试全部通过，但耗时 **4 分 53 秒**（大量触达真实网络，被墙域名 30s 超时）。

即：这个项目当前**没有可用的回归防线**。任何重构都是在无保护状态下进行。

### P1-4 数据源层：12 个客户端，10 个不走基类

继承 `BaseAPIClient` 的只有 `coingecko.py:8`、`coinmarketcap.py:7`。
未继承 10 个：`coinglass` `community` `cryptocompare` `defillama` `github` `google_trends` `reddit` `reddit_free` `sentiment_api` `social_sentiment` `twitter`。

`src/api/base.py:6-45` 只声明 3 个抽象业务方法，对 HTTP / 重试 / 缓存 / 限流零约束，基类形同虚设。后果：

- 重试：仅 `coingecko.py:44-51` 用了 `urllib3.Retry + HTTPAdapter`，其余裸 `timeout=30`
- 缓存 TTL 各写各的：`coinglass:42` 0.1h / `defillama:46` 0.5h / `community:53` 4h / `reddit_free:35` 6h
- `scan_top_800.py` 硬编码 8 处 `time.sleep`（190/232/243/247/253/267/325/542）手动绕开限流

**同功能双实现**：`reddit.py` vs `reddit_free.py`，`get_coin_mentions` 一个返回 `mention_count`(**reddit.py:201**)，另一个返回 `total_mentions`(**reddit_free.py:88**)，
而 `scorer.py:412` 直接把结果喂给 `tokenomics.score_narrative`（期望 int）。

### P1-5 `scripts/` 是影子架构

4 个大脚本**零 `src` 依赖**，业务逻辑完全内联：`backtest_simple.py`(753) `visualize_factors.py`(643) `check_collection_status.py`(527) `json_to_md.py`(461)。

三份几乎逐字相同的 CSS + 导航（同一套深色主题、同一组 5 个导航项）：

| 文件 | CSS | 导航 |
|---|---|---|
| `build_dashboard.py` | **285-324** | 内联 |
| `build_dashboard_pages.py` | **21-54** | **55-62** |
| `build_static_pages.py` | **24-58** | **61-67** |

金额格式化也三份：`json_to_md.py:22` `token_defi_report.py:75` `build_dashboard.py:33`。

**正面样板**：`scripts/research/token_defi_report.py:36-41` 正确 import `src.research.token_defi`，纯展示层，职责干净 —— 这是其余脚本应该长成的样子。

### P1-6 依赖与配置声称了不存在的能力

`requirements.txt` 声明但实际 0 引用：`ta-lib`（需 C 编译，安装杀手）、`pandas-ta`、`yfinance`、`pycoingecko`、`jupyter`、`matplotlib`。

`config/settings.yaml` 配置了 `exchange.binance.api_key` 与 `exchange.okx`，但全仓 `grep -ril "place_order|execute_trade|ccxt"` 只有 `technical.py` 一个误命中 ——
**没有任何交易执行代码**。README 宣称"回测框架"，实际只有 `backtest_simple.py` 一个脚本。

文档与实现的落差会让新接手的人按错误的心智模型改代码。

### P2-7 命名撞车与常量两份

- `research/classification.py` = **因子**分类；`research/token_classification.py` = **代币**分类。领域不同但名字撞车，且后者未导出到 `research/__init__.py`
- 代币 27 类清单硬编码两份：`profiles.py:67-78 TYPE_FAMILY` vs `token_classification.py:55-62 CATEGORY_PRIORITY`
- 阈值打分 `if/elif` 链散落 9 处（scorer 4 处 / technical 3 处 / onchain / github_analyzer / sentiment / coinglass / defillama）。唯一抽象 `tokenomics._band`(**121-134**) 只有 typed 路径在用

---

## 2. 目标架构

### 2.1 形态选择：模块化单体（Modular Monolith）

**不做微服务。** 理由：单人/小团队维护、无独立伸缩需求、无多语言诉求。
微服务带来的一致性、部署、可观测成本在这个规模上远超收益。
正确做法是**先修模块边界**，把"分布式单体"的风险扼杀在进程内。

| 决策 | 选择 | 放弃的 |
|---|---|---|
| 部署形态 | 单体进程 + CLI 子命令 | 独立伸缩、按模块发版 |
| 维度扩展 | 注册表 + 配置外置 | 编译期类型检查、IDE 跳转 |
| 配置载体 | YAML | 配置的类型安全与重构支持 |
| 数据源抽象 | 基类收口横切 + 模板方法 | 完全的客户端实现自由 |

### 2.2 目标分层

```
cli/                    入口（原 29 脚本 → 子命令），只编排 + 渲染
  ↓
scoring/                单一流水线  ← 原 scorer.py 934 行 → ~200 行
  ├── registry.py       维度注册表（声明式，可增删）
  ├── pipeline.py       通用加权器（全仓唯一一份）
  └── band.py           阈值打分器（收敛 9 处 if/elif）
  ↓
profiles.yaml           权重与类型配置外置（四份权重表合一）
  ↓
sources/                统一基类收口：重试/缓存/限流/超时/指标
  ↓
domain/                 数据模型（Pydantic，已存在，保持不变）
```

### 2.3 关键代码骨架

**① 维度即数据，评分即 fold**

```python
# src/scoring/dimension.py
@dataclass(frozen=True)
class Dimension:
    name: str
    compute: Callable[[Context], float | None]      # 返回 None = 数据缺失
    bands: tuple[tuple[float, int], ...] | None = None
    applies_to: frozenset[str] = ALL_TYPES

# src/scoring/pipeline.py —— 三条路径合一后的唯一实现
def score(ctx: Context, profile: Profile, dims: Sequence[Dimension]) -> ScoreResult:
    scored: dict[str, float] = {}
    missing: list[str] = []
    for d in dims:
        if not profile.is_applicable(d.name, ctx.token_type):
            continue
        raw = d.compute(ctx)
        if raw is None:                     # 缺失显式跳过，绝不填 3
            missing.append(d.name)
            continue
        scored[d.name] = band(raw, d.bands) if d.bands else raw
    w_sum = sum(profile.weights[d] for d in scored)
    total = sum(profile.weights[d] * s for d, s in scored.items()) / w_sum * 20 if w_sum else 0.0
    return ScoreResult(total, scored, missing, contributions(scored, profile))
```

收益：新增维度 = 注册一个 `Dimension`，**不动流水线**；legacy/typed/phase1 退化为同一函数的不同 `profile` 入参。

**② 阈值打分唯一化**（提升现有 `tokenomics._band:121-134` 为公共函数）

```python
# src/scoring/band.py
def band(value: float, bands: Sequence[tuple[float, int]], *,
         ascending: bool = True, default: int | None = None) -> int | None: ...
```
9 处手写阈值链全部改为传入 `bands` 表，阈值变成可测试、可配置的数据。

**③ 权重外置**

```yaml
# config/profiles.yaml
families:
  l1:      { tokenomics: .20, valuation: .15, tvl_momentum: .15, developer: .15, narrative: .10, technical: .15, risk: .10 }
  stablecoin: { peg_stability: .40, reserve: .20, ... }
```
改权重不再改代码、不再需要发版；四份权重表（`DEFAULT_WEIGHTS` / `PHASE1_WEIGHTS` / `FAMILY_PROFILES` / `TYPE_PROFILES`）合一。

**④ 数据源基类收口横切**

```python
class BaseSource:
    def __init__(self, *, cache: Cache, limiter: RateLimiter, retry: RetryPolicy): ...
    def _get(self, path: str, *, ttl_hours: float, params=None) -> dict:
        # 唯一 HTTP 出口：重试 + 限流 + 缓存 + 超时 + 指标 全部在此
        ...
    # 子类只实现解析
    def fetch(self, coin_id: str) -> DomainModel: ...
```
12 个客户端从"各写各的 HTTP"变成"只写解析"，`scan_top_800.py` 的 8 处 `time.sleep` 自然消失。

---

## 3. 迁移路径

原则：**每阶段独立可交付、可回滚、都有测试兜底**。阶段 0 必须先做完，否则后续重构无保护。

### 阶段 0 · 止血（0.5 天，无风险，先做）

1. 装 `responses` 或给两个测试模块加 `pytest.importorskip("responses")`，**让 433 个测试恢复执行**
2. 加 `pytest.ini`：`testpaths`、`--strict-markers`，并给触网测试打 `@pytest.mark.network` 默认跳过 → 4m53s 降到秒级
3. 删除 0 引用的依赖：`ta-lib` `pandas-ta` `yfinance` `pycoingecko` `jupyter` `matplotlib`
4. 删 `settings.yaml` 里不存在的 `exchange.*` 配置；README 的"回测框架"改为"回测脚本（实验性）"

> 这一步不改动任何业务逻辑，纯粹恢复工程防线。**在此之前不要动 scorer。**

### 阶段 1 · 三路径合一（3-5 天，收益最大）

目标：`scorer.py` 934 行 → ~200 行，行为可由现有 golden 测试锁定。

1. 提取 `src/scoring/band.py`（复用现有 `_band`），把 9 处阈值链改为数据表
2. 把 legacy / typed / phase1 三份权重表迁到 `config/profiles.yaml`，`profiles.py` 改为加载器（保留 `get_profile` 签名，内部换实现）
3. 用 §2.3① 的 `score()` 替换三条路径；`score_project` / `score_project_with_phase1` 保留为薄兼容壳
4. **修复语义污染**：`_score_market` / `_score_technical` 的 `return 3` 改 `return None`
5. **验收**：`tests/analysis/test_scorer_legacy_golden.py` + `test_scorer_typed.py` + `test_golden_types.py` 全绿，且输出逐字节不变（除 `missing` 字段）

> 取舍：配置外置后，权重的类型安全由 Pydantic schema 校验兜底，放弃编译期检查。

### 阶段 2 · 数据源收口（1 周，可并行）

1. 重写 `BaseSource`：承担重试 / 限流 / 缓存 / 超时 / 指标
2. 按"改动风险"顺序迁移 10 个裸客户端，每迁一个跑对应测试
3. 合并 `reddit.py` 与 `reddit_free.py` 为单一 `RedditSource`，统一返回 `mention_count`（调用方 `scorer.py:412` 同步修正）
4. 删掉 `scan_top_800.py` 的 8 处 `time.sleep`

> 取舍：统一基类会牺牲个别数据源的特殊优化空间（如 coingecko 的自定义 Retry 策略）。折中：允许子类覆写 `_retry_policy`。

### 阶段 3 · scripts 瘦身（1 周）

1. 抽 `src/report/theme.py` 承载三份重复的 CSS + 导航 + 格式化函数
2. 4 个零依赖大脚本的业务逻辑下沉到 `src/`，脚本退化为 CLI 子命令
3. 统一入口：`python -m claude_trading scan|evaluate|collect|report`

### 阶段 4 · 因子框架融合（可选，风险最高）

让 `scoring/` 消费 `factors/registry`，评分维度即注册因子 —— 彻底消除 P0-1 的断裂。

> 建议：阶段 1-3 完成后再评估。若 `factors/` 的 `store`（DuckDB 时序）与评分的实时路径诉求不匹配，
> **保持两套反而更合理** —— 此时应做的是删掉 `factors/` 里没被消费的部分，而不是强行融合。

---

## 4. 架构决策记录

### ADR-001：采用模块化单体，不拆分微服务

- **状态**：Accepted
- **上下文**：28.5K 行、单人维护、无独立伸缩需求、无多语言诉求。
- **决策**：保留单体进程，通过模块边界与依赖方向治理复杂度。
- **后果**：✅ 部署与调试成本不变，重构可增量进行；❌ 无法按模块独立伸缩或发版，模块间隔离靠约定而非进程边界（建议后续用 import-linter 强制）。

### ADR-002：评分维度声明式注册 + 权重外置 YAML

- **状态**：Proposed（阶段 1 实施）
- **上下文**：`scorer.py` 三条评分路径、四份权重表、9 处阈值链，新增维度须改核心文件。
- **决策**：维度注册为 `Dimension` 数据对象，权重与阈值外置 `profiles.yaml`，流水线只做加权 fold。
- **后果**：✅ 新增维度不改流水线；改权重不发版；阈值可单测。❌ 失去配置的类型安全与 IDE 跳转，需 Pydantic schema 校验兜底；调试时需在 yaml 与代码间跳转。

### ADR-003：数据源横切关注点由基类统一承担

- **状态**：Proposed（阶段 2 实施）
- **上下文**：12 个客户端 10 个裸实现，重试仅 1 处有，TTL 四个数量级不一致。
- **决策**：`BaseSource._get()` 作为唯一 HTTP 出口，子类只实现解析逻辑。
- **后果**：✅ 限流/重试/缓存行为一致，新数据源接入成本从"复制一个客户端"降为"写一个解析函数"。❌ 个别数据源的特殊策略需要预留覆写钩子（已设计 `_retry_policy`）。

### ADR-004：暂不融合 `factors/` 与 `scoring/`

- **状态**：Proposed（阶段 4 再评估）
- **上下文**：`factors/` 框架完善但未被生产评分消费，形成断裂。
- **决策**：阶段 1-3 先收敛各自内部复杂度，融合推迟评估。
- **后果**：✅ 避免在两套语义尚未理清时强行抽象；阶段 1 的声明式维度本身就是融合的前置准备。❌ 短期内"两套体系"的认知负担仍在。需在阶段 4 明确结论：要么融合，要么删掉 `factors/` 未被消费的部分。

---

## 5. 落地检查清单

- [ ] **阶段 0**：433 测试恢复执行（当前处于中断状态）
- [ ] **阶段 0**：测试耗时 4m53s → < 30s（网络标记隔离）
- [ ] **阶段 0**：删除 6 个 0 引用依赖 + 不存在的交易所配置
- [ ] **阶段 1**：`scorer.py` < 250 行，golden 测试输出不变
- [ ] **阶段 1**：`_score_market` / `_score_technical` 不再 `return 3`
- [ ] **阶段 2**：12/12 客户端继承 `BaseSource`，TTL 集中配置
- [ ] **阶段 2**：`reddit` 双实现合并，`scan_top_800` 无硬编码 sleep
- [ ] **阶段 3**：CSS / 导航 / 格式化各只有一份
- [ ] **全阶段**：引入 `import-linter` 固化分层依赖方向，防止债务复发
