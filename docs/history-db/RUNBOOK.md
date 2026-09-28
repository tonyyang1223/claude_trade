# 历史数据库 RUNBOOK（回填 / 重建 FTS / 增量 / 排障）

> 适用对象：`data/history/ct_history.duckdb`（DuckDB 单文件历史库）的运维与排障。
> 设计依据：`docs/history-db/ARCHITECTURE.md`（§5 ETL、§6 定时增量、§11-T05）。
> **所有命令均在项目根目录执行**（`claude_trading/`）。

---

## 0. TL;DR（最常用三条）

```bash
# ① 首次建库 + 全量回填（幂等，可反复跑）
python scripts/history/init_db.py
python scripts/history/backfill_history.py

# ② 增量入库（定时任务会调用的就是它；无新数据时秒级空跑）
python scripts/history/ingest_history.py --incremental

# ③ 只看将处理什么、不写库
python scripts/history/ingest_history.py --incremental --dry-run
```

自检 / 回归：

```bash
python -m pytest console/backend/tests -q
```

---

## 1. 关键概念（先读，避免踩坑）

### 1.1 FTS 是「静态索引」——增量后**必须重建**（⚠️ 头号坑）

`PRAGMA create_fts_index(...)` 只索引**建索引那一刻已存在的行**；此后的 `INSERT` **不会**自动进索引。
后果：若顺序写反（先重建 FTS 再写数据），会出现**「数据进了库却搜不到」的静默故障**（不报错）。

因此 ETL 顺序是**硬约束**：

```
… 先写完所有数据行 →（最后）create_fts_index(..., overwrite=1) 重建
```

- `backfill_history.py` / `ingest_history.py` 都已按此顺序实现，**无需人工干预**；
- 若你**手工** `INSERT` 过数据，或怀疑检索对不上，**必须手动重建**：

```bash
python -c "import sys; sys.path.insert(0,'scripts'); from history import etl_common as ec, init_db; \
c=ec.connect(); init_db.build_fts_index(c); c.close()"
```

### 1.2 中文查询必须 bigram 化（否则静默召回 0）

DuckDB `simple` 分词器**不切分中文**，把连续中文当**单个 token**。库内 `body_grams` 列已把中文拆成
**字符 bigram**（见 `scripts/history/export_grams.py`）。故：

- **查询侧**必须同样把中文 bigram 化——代码里统一走
  `services.history_svc.build_fts_query()`（内部复用 `export_grams.make_grams`，单一真源）；
- 手工用 SQL 调试 FTS 时，中文要自己拆：`'哔哩哔哩'` → 查 `'哔哩 哩哔'`。

> 实测：`'以太坊'` 在**当前语料里根本不存在**，FTS 与 ILIKE 均为 0——这是**正确**结果，不是 bug。
> 中文命中用 `'哔哩哔哩'`（应得 455）验证。

### 1.3 幂等（重复跑，行数不变）

| 场景 | batch_id | 理由 |
|---|---|---|
| 全量回填 | **确定性** `backfill-all` | `ingest_batch`(PK=batch_id) / `ingest_file_log`(PK=(batch_id,file_path)) 天然 upsert → 重跑行数不变 |
| 增量 | **确定性** `incremental-history` | 同上；使「重复跑两次各表行数完全不变」成立（偏离 §5.3 的时间戳批次，换取台账层可复跑幂等） |

> 数据层幂等另由「主表 UPSERT + 可缩小子表按自然键单元事务内 DELETE+INSERT」保证。

### 1.4 单写者（并发）+ 短事务

DuckDB 单文件**同一时刻只允许一个写连接**（写连接独占文件锁；即便只读连接也会与之互斥）。
`ingest_history.py` / `backfill_history.py` 都是**独立进程、独占写**：

- **入库与只读查询不可并发**：ETL 持写锁期间，后端只读查询会拿到
  `Could not set lock on file`（表现为接口 503）；反之若有人正只读，ETL 也开不了写连接。
  → **请让入库成为短事务**：本项目的回填/增量在**秒级~分钟内**完成并立即 `close()`；
  切勿在服务读写高峰跑全量回填；
- 若报 `IO Error: Cannot open file ... File is already open in ... (PID n)` →
  说明另一进程占着库（如 Web 服务、QA 校验、上一次未退出的 ETL）。**不要强杀**，
  等其释放或请其关闭连接后重试；**必要时停服执行**；
- 因此定时增量设计为「每 15 分钟一次、无新数据秒级空跑」，以最小化持锁窗口。

### 1.5 批次生命周期与「悬挂批次」

`ingest_batch` 是**入库任务的生命周期台账**；H7 `/api/history/health/overview` 的 `batches`
直接暴露它最近 10 行。**若一行永远停在 `running`，工作台就会显示「有任务正在跑」的假信号。**

生命周期由代码两层保证（`etl_common`）：

1. **写入侧 `running_batch`**：`try/finally` 兜底 —— 正常→`success`；普通异常→`failed`
   （并原样上抛）；`KeyboardInterrupt`/`SystemExit`→`interrupted`。连接若已断，
   `finally` 会放弃并交由第 2 层处理。
2. **启动侧 `reap_stale_batches`**：进程被**强杀**（SIGKILL / SIGTERM 默认行为）时不执行任何
   Python 收尾 → 下次 ETL 启动、**在已持有写锁的前提下**，把残留的 `running` 行回收为
   `interrupted`（此时任何 `running` 行都不可能是活跃进程，因为活跃写者会占住文件锁）。

> `interrupted` 行的 `finished_at` **保持 NULL** —— 进程被强杀时其真实结束时刻无自证来源，
> **不伪造时间**；只要 `status` 不再是 `running`，假信号即消除。

### 1.6 单列 ART 二级索引损坏会让等值查找返回错值（静默；ARCHITECTURE §12）

**现象**：某些 **`col = <字面量>` 等值谓词的计数偏小甚至为 0**，而全表扫才是真值。
实测过：`content_archive.source='bilibili'` 得 **286**（真值 **455**）；
`content_archive.coin_id='bitcoin'` 得 **322**（真值 **670**）；
`category_membership.date='2026-06-27'` 得 **0**（真值 **1241**）；
`source_status.source='github'` 得 **58**（真值 **97**）。**与并发无关**（库副本上亦复现）。

**根因**：**单列 ART 二级索引损坏/陈旧**（索引项缺失）——**不是数据损坏**（全表扫始终正确）。
实测本库**恰好 5 个**索引损坏：`idx_content_source` / `idx_content_coin` / `idx_catmem_date` /
`idx_srcstat_date` / `idx_srcstat_source`（其中 **3 个非 `date` 列**，见下「假绿」）。

**为什么危险**：应用层 `DuckDBRepository.load_by_category_raw` 用 `WHERE date = ?::DATE`
取数，命中损坏索引得到 0 行 → 触发「**请求级回退文件**」，老端点表面正常、实则**多日静默走文件回退**。

**修复 = 自愈索引**（唯一入口 `etl_common.heal_indexes`，`--fix` 与 ETL 收尾共用），**按故障分两种**：
- **存在但算错**（等值计数 ≠ 物化全表扫真值）→ **重建**（`DROP INDEX` + `CREATE INDEX`）；
- **缺失**（预期索引不在库）→ **按 `ddl.sql` 原语句 `CREATE INDEX IF NOT EXISTS` 补建**（DDL 单一真源）；
另：**冗余** date 索引（PK 首列 = `date`）→ **清理**；**未知**多余索引 → **仅告警、不自动删**。
（以上**幂等、不动数据、不碰 FTS**；自愈流程详见 §5.2。）
⚠️ **严禁物理重写整表**（`CTAS→DROP→RENAME` 会连带删掉该表全部索引，放大风险，见 §12）。

**⚠️ 假绿警告（务必遵守）**：**只查 `date` 列的检测必漏报**非 `date` 列
（`content_archive.source` / `content_archive.coin_id` / `source_status.source`）。
检测**必须覆盖全部单列索引列**，且**真值必须「物化 + 纯全表扫」**（temp 表无索引），
否则普通 `GROUP BY` / 把等值下推进子查询会被坏索引一并答复而**一起算错**。
见 §5.2 / `scripts/history/check_integrity.py`。

> 除「等值计数一致性」外，自检还会**断言 `ddl.sql` 声明的 6 个具名索引全部存在**
> （`etl_common.audit_expected_indexes`）——这样**任何一次意外丢索引**（误 `DROP`、物理重写）
> 都会被抓住，而不只是「重建过程中不丢」（§5.2）。**缺失即自愈**：`--fix` 与 ETL 收尾
> 会按 `ddl.sql` 的原语句**自动补建**缺失索引（DDL 单一真源，§5.2）。

> 另有**冗余单列 date 索引**（`idx_catmem_date` / `idx_srcstat_date` / `idx_snap_date`，PK 首列即该列）
> 已从 `ddl.sql` 移除并由 `init_db.apply_schema` 幂等清理——它们对查询无增益（PK 已覆盖其前缀查找）。


---

## 2. 全量回填

```bash
python scripts/history/init_db.py            # 建库建表 + 建/重建双列 FTS（幂等）
python scripts/history/init_db.py --rebuild  # ⚠️ 先删库文件再重建（清空历史数据！）
python scripts/history/backfill_history.py   # 载 daily_scan + macro → 算残缺日 → 末步建 FTS
```

回填末尾会打印**状态报告**（各表行数 / 视图 / FTS 状态）。验收：14 张基表 + 5 个业务视图 +
双列 FTS 就绪。

---

## 3. 增量入库（`ingest_history.py`）

```
python scripts/history/ingest_history.py --incremental [--dry-run] [--stats] [--quiet]
                                         [--db PATH] [--scan-dir PATH] [--macro-dir PATH]
```

行为：

1. **水位线**：`scan` = `MAX(scan_day.date)`、`macro` = `MAX(macro_snapshot.date)`；
   只考虑 `date >= 水位线` 的候选（用 `>=` 以免漏掉**水位当日新增的 macro 快照**——macro 一天多个 `HHMM`）。
2. **跳未变更文件**：按 `ingest_file_log` 的 **md5/mtime** 判断；未变 → 跳过（无新数据时近乎零成本）。
   - 先用 `mtime` 快路径（不读文件），`mtime` 变了再比 `md5`。
3. **写数据**（复用 `load_daily_scan` / `load_macro`，只处理候选子集）。
4. **末步重建双列 FTS**（顺序硬约束）；**无写入且索引已在则跳过重建**（省算力）。
5. **FTS 复验**：`Solana` 与 `哔哩哔哩` 的命中数须 **≥ 基线**（`Solana>=869`、`哔哩哔哩>=455`）；
   不足 → 打印 `FAIL` 且**退出码 2**（便于 cron 日志告警）。

退出码：`0` 成功；`2` FTS 复验失败；`1` 参数/库缺失等致命错误。

> 依赖：库须已 `init_db` + `backfill`（否则脚本给出明确提示并退出）。

---

## 4. 定时接入（复用现有调度，不新增常驻进程）

裁决见 ARCHITECTURE §6（**Q1**）：**复用现有 cron/定时器，每 15 分钟调一次增量**，不新增常驻进程；
增量幂等 + 跳未变更文件使其空跑近零成本。

### 4.1 推荐：独立 cron（每 15 分钟）

crontab 行（按实际路径替换）：

```cron
*/15 * * * * cd /home/ubuntu/project/claude_trade && /usr/bin/python3 scripts/history/ingest_history.py --incremental >> logs/history_ingest.log 2>&1
```

可用随附脚本**幂等**注册（默认只**预览**，不落盘；`--install` 才写入；带 marker 便于安全移除）：

```bash
bash scripts/history/register_cron.sh            # 预览将写入的 cron 行
bash scripts/history/register_cron.sh --install  # 写入当前用户 crontab
bash scripts/history/register_cron.sh --remove   # 移除本项目的该条
```

可用环境变量覆盖：`PROJECT_DIR` / `PYTHON_BIN` / `LOG_DIR` / `INTERVAL_MIN`。

> ⚠️ 本脚本**只操作当前用户的 crontab**，且以 `# claude-history-ingest` marker 精确定位自身条目，
> **不触碰** `scripts/setup_cron.sh` 管理的采集任务。生产环境的实际部署方式以其运维约定为准。

### 4.2 可选：挂到 scan 一轮结束

在 `scripts/scan/run_daemon.sh` 的 `--once` 之后追加一行：

```bash
python scripts/history/ingest_history.py --incremental >> logs/history_ingest.log 2>&1 || true
```

零额外调度，但**耦合采集脚本**；且 scan 当前已停更，**不能只依赖它**。

---

## 5. 验证与自检

```bash
# 单元/同构测试（含文件仓储 ↔ DuckDB 仓储同构、H5 检索、H1/H7 等）
python -m pytest console/backend/tests -q

# 库状态报告（各表行数 / 视图 / FTS 状态 / 体积）
python scripts/history/ingest_history.py --incremental --stats
```

FTS 手工冒烟（注意中文 bigram 化）：

```python
import sys; sys.path.insert(0,'scripts')
import duckdb
from history.export_grams import make_grams
c = duckdb.connect('data/history/ct_history.duckdb', read_only=True)
for q in ('Solana', make_grams('哔哩哔哩')):   # -> 869 / 455
    n = c.execute("SELECT COUNT(*) FROM content_archive a WHERE "
                  "fts_main_content_archive.match_bm25(a.content_id, ?, conjunctive:=false) IS NOT NULL",
                  [q]).fetchone()[0]
    print(q, n)
```

### 5.1 悬挂批次（`running` 残留）自查与回收（需持写锁）

识别——列出所有悬挂批次（应为空）：

```sql
SELECT batch_id, mode, scope, started_at, finished_at, status
FROM ingest_batch
WHERE status = 'running' AND finished_at IS NULL;
```

回收——把上面的行置为 `interrupted`（**不伪造 `finished_at`**）：

```python
import sys; sys.path.insert(0, 'scripts')
from history import etl_common as ec
c = ec.connect()                        # 独占写；若被占用会报 "File is already open ..."
print("回收:", ec.reap_stale_batches(c))  # 返回被回收的 batch_id 列表
c.close()
```

> 通常**无需手工执行**：下次 `ingest_history.py --incremental` 或 `backfill_history.py`
> 启动时会**自动回收**（见 §1.5）。仅当你想立刻消除「正在跑」的假信号、且当下无人占用库时手动跑。

### 5.2 索引完整性自检 / 自愈（单列 ART 二级索引，见 §1.6）

一条命令做**两件事**：(A) 自检「**每个单列索引列**的 `col = ?` 等值计数 是否等于 **物化全表扫真值**」；
(B) **断言 `ddl.sql` 声明的 6 个具名索引全部存在**（防「意外丢索引」，独立于重建流程）：

```bash
python scripts/history/check_integrity.py          # 只读自检；有损坏/缺索引 → 退出码 1
python scripts/history/check_integrity.py --fix    # 索引**自愈**（需写锁）
```

`--fix` 执行**同一个自愈例程**（`etl_common.heal_indexes`，与 ETL 收尾**共用**），覆盖两种故障：

1. **缺失**（预期索引不在库）→ **按 `ddl.sql` 的原语句 `CREATE INDEX IF NOT EXISTS` 补齐**
   （DDL 单一真源，不另写定义）；
2. **存在但算错**（等值计数 ≠ 物化全表扫真值）→ `DROP INDEX` + `CREATE INDEX` **重建**；
3. `unexpected`（预期外多出的索引）里**冗余 date 索引**（PK 首列 = date）→ **清理**；
   **未知**多余索引 → **只告警、不自动删**（避免误删他人索引）。

- **健康库**：`✅ 预期索引集合完整（6 个具名索引全部存在）` +
  `✅ 全部单列索引：等值计数 == 物化全表扫真值（0 处不一致）`，退出码 0；
- **有损坏/缺索引**：`--fix` 补齐缺失 + 重建损坏 + 清理冗余后**复检**；退出码 1（若无可自愈项）或 0（自愈后通过）。

> ⚠️ 检测**覆盖全部单列索引列**（含非 `date` 的 `content_archive.source` / `coin_id`、
> `source_status.source`），且真值**先物化**（temp 表）——否则会「假绿」（见 §1.6 / ARCHITECTURE §12）。
> 预期索引口径与补建语句**均取自 `ddl.sql`**（`etl_common.expected_indexes` /
> `expected_index_statements`），不硬编码，避免与 DDL 漂移。
> `--fix` 需要**写连接**（DuckDB 单写者，勿与只读/其它 ETL 并发）。

`ingest_history.py` / `backfill_history.py` 收尾也会自动跑**同一自愈**（ARCHITECTURE §13-O11）；
自愈后仍有「缺索引 / 算错 / 重建期丢索引」时 **ingest/backfill 退出码 2**
（结果字段 `integrity_created` / `integrity_rebuilt` / `missing_indexes`）。


---

## 6. 排障（Troubleshooting）

| 现象 | 可能原因 | 处置 |
|---|---|---|
| **数据进了库，但 FTS 搜不到** | 静态索引未重建（顺序写反 / 手工 INSERT） | 手动重建 FTS（见 §1.1） |
| **中文关键词召回 0，英文正常** | 查询侧未 bigram 化 | 走 `build_fts_query`（复用 `make_grams`）；手工 SQL 时自行拆 bigram（§1.2） |
| **`'以太坊'` 查到 0 条** | **正常**：语料里没有该词 | 用 `'哔哩哔哩'` 验证中文命中（应 455） |
| `database is locked` / `Could not set lock` | 另一写进程在写（DuckDB 单写者） | 稍后重试；必要时**停服执行**（§1.4） |
| `IO Error: Cannot open file ... File is already open in <path> (PID n)` | 另一进程（只读或写）占着库 | 入库与只读查询**不可并发**（§1.4）；等其释放或停服执行，**勿强杀** |
| 健康度页**永远显示一个 `running` 批次** | 批次进程被强杀，收尾未执行 → 悬挂批次（假信号） | 见 §1.5；下次 ETL 启动自动回收，或手动 `reap_stale_batches`（§5.1） |
| **某 `col = ?` 等值计数比全表扫少/为 0**（含 `source`/`coin_id` 等非 `date` 列） | **单列 ART 二级索引损坏**（索引项缺失），非数据问题 | 跑 `check_integrity.py --fix`（§5.2 / §1.6）；**重建**该索引，勿物理重写整表 |
| **自检报 `🔴 缺失预期索引`**（`ddl.sql` 声明的 6 个里少了某几个） | 某索引被误 `DROP` / 物理重写整表导致丢索引 | `check_integrity.py --fix`（或下次 ingest/backfill）会**按 `ddl.sql` 自动补建**（§5.2）；勿物理重写整表（§1.6） |
| **自检报 `⚠️ 未知多余索引`** | 库中多出预期外的索引（非「PK 首列=date」的冗余） | **不会自动删**；请人工确认归属后再处置（§5.2） |
| **老端点某 `date` 静默走文件回退**（DB 查询返回 0 行） | 同上（`date = ?` 命中损坏索引返回 0 → 触发请求级回退） | 见 §1.6；`check_integrity.py` 可复现并修复 |
| 增量「什么也没做」 | 无新数据（水位线之后无变更文件） | **预期行为**（幂等空跑）；用 `--dry-run` 确认候选 |
| 增量退出码 **2** | FTS 复验低于基线 | 检查索引是否被破坏，手动重建 FTS（§1.1） |
| `scan_day` 停更多日（08-26 之后无新） | **采集端**（scan）已停更，非历史库问题 | 健康度视图已暴露（`v_collection_calendar`/`v_collection_freshness`）；修复归采集侧 |
| `macro_snapshot.fear_greed_json` 恒为 `NULL` | 采集端未产出 `fear_greed` | **不造数据**（§13-O4）；H8 该指标返回空 series + 404 |
| `init_db.py` 建 FTS 报「表不存在」 | DDL 建表与 FTS 未分开执行 | 用 `init_db.apply_schema()`（逐条执行），勿整段执行 ddl.sql |
| 早期扫描日（06-27/06-28）字段名不同 | 源 `summary.json` 用了旧字段（`top_50_detailed`/`top_800_light`） | 已入库的 `scan_day` 统一为 `deep/light_researched`；下游消费不受影响 |

---

## 7. 数据口径速查（写入方不可违反）

- **`NULL` = 源确实缺失**，一律存 `NULL`，**不填 0**（不污染均值）。
- 日期列 `DATE`（`YYYY-MM-DD`）；时间戳归一为**本地（Asia/Shanghai）朴素值**，保留源微秒。
- **残缺日**（`scan_day.is_partial=TRUE`）原样入库 + 标记，**绝不插值/伪造**。
- `body_text`（截断：post/video 8KB）、`body_grams`（CJK bigram + 英文整词，**仅索引，不返前端**）。
- 正文检索覆盖 **标题 + 正文**（合并进 `body_grams`）。

---

## 8. 相关文件

| 文件 | 作用 |
|---|---|
| `scripts/history/init_db.py` | 建库建表 / 重建 FTS / 状态报告 |
| `scripts/history/backfill_history.py` | 全量回填编排（末步建 FTS） |
| `scripts/history/ingest_history.py` | **增量入库**（水位线 + 跳文件 + 末步重建 FTS） |
| `scripts/history/etl_common.py` | 连接 / 批次 / 文件台账 / 归一 |
| `scripts/history/load_daily_scan.py` `load_macro.py` | 分表装载逻辑 |
| `scripts/history/export_grams.py` | `make_grams`（入库与查询的 **bigram 单一真源**） |
| `scripts/history/check_integrity.py` | **索引完整性自检/自愈**（等值查找一致性 + 预期索引存在性断言 + 补齐缺失/重建/冗余清理，P0-1/P0-2） |
| `scripts/history/ddl.sql` | 表/视图/FTS 定义 |
| `console/backend/services/history_svc.py` | H1–H8 只读端点服务层 |
| `console/backend/tests/test_repository_parity.py` | 文件 ↔ DuckDB 同构性测试 |
