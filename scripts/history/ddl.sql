-- ============================================================================
-- claude_trading 历史数据库层 —— 完整 DDL
-- ============================================================================
-- 权威依据：docs/history-db/ARCHITECTURE.md §2「完整 DDL（可直接执行）」
-- 本文件为 §2 的逐字落盘（14 张基表 + 5 个业务视图 + 双列 FTS 索引）。
--
-- 命名规范（见 ARCHITECTURE §12）：
--   表名单数 snake_case；维度表前缀 dim_；逐日事实表后缀 _daily；
--   日期列统一叫 date（DATE）；时间戳 TIMESTAMP；JSON 列后缀 _json。
--
-- 执行约定（重要，见 ARCHITECTURE §2 尾注）：
--   建表语句与 FTS 建索引语句【必须分开执行】——若混在同一次 execute(整段) 里，
--   DuckDB 会在绑定阶段报 `Table with name content_archive does not exist`。
--   init_db.py 采用「逐条语句分别 execute」的方式，天然满足该约束；
--   且 FTS 索引为静态索引，必须在所有数据行写完之后再建/重建。
-- ============================================================================

-- ============================================================
-- A. 维度表
-- ============================================================
CREATE TABLE IF NOT EXISTS dim_coin (
    coin_id         VARCHAR PRIMARY KEY,
    symbol          VARCHAR,
    name            VARCHAR,
    first_seen_date DATE,
    last_seen_date  DATE
);

-- 分类/叙事标签（slug 即目录名，最小集合 + 允许后续扩展）
CREATE TABLE IF NOT EXISTS dim_category (
    category_slug VARCHAR PRIMARY KEY,   -- layer-1/defi/meme/rwa/stablecoin/layer-2/exchange/ai/unclassified
    label         VARCHAR
);

-- 分类成员事实表：忠实复现 by_category 的 (date × slug × member) 稀疏多分类结构
-- 语义要点（见 §0 验证5）：
--   · 一币可属多个 slug（多分类），故 PK 不能是 (date,coin_id)
--   · 大量成员无 coin_id（1241 文件中仅 116 含 coin_id），以 member_key（文件名）保唯一
--   · 仅 has_market=TRUE 的成员参与 build_sectors
--   · 本表同时充当 R12「只入一份」的权威分类来源，代替旧的 coin_category_daily
CREATE TABLE IF NOT EXISTS category_membership (
    date          DATE    NOT NULL,
    category_slug VARCHAR NOT NULL,      -- 目录名即权威 slug
    member_key    VARCHAR NOT NULL,      -- by_category/<slug>/<member_key>.json 的文件名
    coin_id       VARCHAR,               -- 可空
    has_market    BOOLEAN NOT NULL,      -- sources.market.data 是否非空（决定是否进 sectors）
    market_cap    DOUBLE,
    chg24         DOUBLE,                -- sources.market.data.price_change_percentage_24h
    PRIMARY KEY (date, category_slug, member_key)
);
-- ⚠️ 不再为 date 单独建二级索引（原 idx_catmem_date 已移除，见文末「冗余 date 索引移除」说明）：
--    PK 首列即 date，其 ART 索引已覆盖 `date = ?` / `date BETWEEN ? AND ?` 的前缀查找，
--    单列 date 索引属纯冗余；且它会在 DELETE+INSERT（本表按日整替）后变「陈旧」，
--    被优化器选中做等值查找时返回错误行数（P0-1：06-27~06-30 等值查 0，全表扫却是 1241）。

-- ============================================================
-- B. 结构化时间序列
-- ============================================================
-- B1. 轻量行情快照（top_800_light/all_coins.json），13 字段
CREATE TABLE IF NOT EXISTS coin_daily_snapshot (
    date              DATE    NOT NULL,
    coin_id           VARCHAR NOT NULL,
    symbol            VARCHAR,
    name              VARCHAR,
    rank              INTEGER,
    price_usd         DOUBLE,
    market_cap        DOUBLE,
    volume_24h        DOUBLE,
    change_24h_pct    DOUBLE,
    change_7d_pct     DOUBLE,
    circulating_supply DOUBLE,
    total_supply      DOUBLE,
    max_supply        DOUBLE,
    snapshot_ts       TIMESTAMP,          -- 源 timestamp
    PRIMARY KEY (date, coin_id)
);
CREATE INDEX IF NOT EXISTS idx_snap_coin ON coin_daily_snapshot(coin_id);
-- ⚠️ 原 idx_snap_date 已移除：同属「PK 首列即 date」的冗余单列索引（见 file 末说明）。
--    coin_daily_snapshot 走 UPSERT（无 DELETE），故当前未暴露陈旧问题，但冗余索引属同一隐患类别，一并移除。

-- B2. 扫描日元信息（summary.json + 实测落盘计数）
CREATE TABLE IF NOT EXISTS scan_day (
    date                 DATE PRIMARY KEY,
    scan_time            TIMESTAMP,
    total_coins          INTEGER,
    deep_researched_decl INTEGER,        -- summary 声明值（可能虚高，如 08-25 报 69）
    light_researched_decl INTEGER,
    deep_files_actual    INTEGER,        -- 实测落盘 top_50_detailed/*.json 数（健康度以此为准）
    light_files_actual   INTEGER,        -- 实测 top_800_light 内币数
    categories_json      JSON,
    market_stats_json    JSON,
    state_stats_json     JSON,
    source_path          VARCHAR,
    is_partial           BOOLEAN DEFAULT FALSE,   -- 残缺日判定结果（见 §3 / R7）
    ingested_batch_id    VARCHAR
);

-- B3. 宏观小时快照（data/macro/<date>/<HHMM>.json）
CREATE TABLE IF NOT EXISTS macro_snapshot (
    date           DATE    NOT NULL,
    snapshot_time  VARCHAR NOT NULL,      -- 'HHMM'，如 '2201'
    fetched_at     TIMESTAMP,
    duration_s     DOUBLE,
    sources_used_json JSON,
    global_json    JSON,
    breadth_json   JSON,
    regime_json    JSON,
    fear_greed_json JSON,
    diff_prev_json JSON,
    thresholds_json JSON,
    errors_json    JSON,
    snapshot_file  VARCHAR,
    PRIMARY KEY (date, snapshot_time)
);

CREATE TABLE IF NOT EXISTS macro_watchlist (
    date          DATE    NOT NULL,
    snapshot_time VARCHAR NOT NULL,
    coin_id       VARCHAR NOT NULL,
    symbol        VARCHAR, name VARCHAR, rank INTEGER,
    price         DOUBLE,
    p1h DOUBLE, p24h DOUBLE, p7d DOUBLE,
    market_cap    DOUBLE,
    total_volume  DOUBLE,
    PRIMARY KEY (date, snapshot_time, coin_id)
);

CREATE TABLE IF NOT EXISTS macro_anomaly (
    date          DATE    NOT NULL,
    snapshot_time VARCHAR NOT NULL,
    row_idx       INTEGER NOT NULL,       -- 列表内位置，兜底唯一键
    symbol        VARCHAR, name VARCHAR, rank INTEGER,
    price         DOUBLE, p1h DOUBLE, p24h DOUBLE, p7d DOUBLE,
    turnover_pct  DOUBLE,
    reasons_json  JSON,
    strength      DOUBLE,
    PRIMARY KEY (date, snapshot_time, row_idx)
);

CREATE TABLE IF NOT EXISTS macro_chain_tvl (
    date           DATE    NOT NULL,
    snapshot_time  VARCHAR NOT NULL,
    chain          VARCHAR NOT NULL,
    tvl            DOUBLE,
    tvl_change_24h DOUBLE,
    tvl_change_7d  DOUBLE,
    protocols_count INTEGER,
    confidence     DOUBLE,
    ts             TIMESTAMP,
    PRIMARY KEY (date, snapshot_time, chain)
);

-- ============================================================
-- C. 半结构化深度研究
-- ============================================================
-- C1. 深度研究主表（canonical = top_50_detailed，一币一日一行）
--     payload_json 保留完整原始记录 → 保证 R8 老端点（token/opportunity）可 1:1 复现
CREATE TABLE IF NOT EXISTS deep_research (
    date            DATE    NOT NULL,
    coin_id         VARCHAR NOT NULL,
    symbol          VARCHAR,
    name            VARCHAR,
    rank            INTEGER,
    research_time   TIMESTAMP,
    category_slug   VARCHAR,             -- 权威分类来自 by_category（覆盖 payload 内可能为 unclassified 的值）
    categories_json JSON,
    n_sources       INTEGER,
    has_github      BOOLEAN,             -- 源漂移探针
    payload_json    JSON,                -- 原始 top_50_detailed/<coin_id>.json 全文
    source_file     VARCHAR,
    PRIMARY KEY (date, coin_id)
);
CREATE INDEX IF NOT EXISTS idx_deep_coin ON deep_research(coin_id);

-- C2. 逐源状态事实表（稀疏长表，天然容纳 13/14 源漂移）
CREATE TABLE IF NOT EXISTS source_status (
    date             DATE    NOT NULL,
    coin_id          VARCHAR NOT NULL,
    source           VARCHAR NOT NULL,   -- market/github/crypto_news/reddit/... （14 项并集）
    status           VARCHAR NOT NULL,   -- ok | error
    error            VARCHAR,
    confidence       DOUBLE,
    source_timestamp TIMESTAMP,          -- 从 data.timestamp 提取（存在时）
    PRIMARY KEY (date, coin_id, source)
);
CREATE INDEX IF NOT EXISTS idx_srcstat_source ON source_status(source);
-- ⚠️ 原 idx_srcstat_date 已移除：同上，PK 首列即 date ⇒ 冗余（P0-2：2026-06-30 等值查 618，全表扫 871）。

-- ============================================================
-- D. 非结构化内容归档（原文留档 + 全文检索）
-- ============================================================
CREATE TABLE IF NOT EXISTS content_archive (
    content_id   VARCHAR PRIMARY KEY,    -- 确定性 hash(date|coin_id|source|doc_hash)，幂等键
    date         DATE    NOT NULL,
    coin_id      VARCHAR NOT NULL,
    source       VARCHAR NOT NULL,       -- crypto_news|rss|reddit|v2ex|bilibili|twitter
    doc_type     VARCHAR,                -- news|post|video|tweet|... 
    title        VARCHAR,
    url          VARCHAR,
    author       VARCHAR,
    body_text    VARCHAR,                -- 正文/描述（留档主体）
    published_ts TIMESTAMP,
    score        DOUBLE,                 -- reddit score / bilibili play 等
    extra_json   JSON,                   -- 其余字段（source/confidence/...）
    origin_path  VARCHAR,                -- 原始文件相对路径（US-5「原文回溯」）
    doc_hash     VARCHAR NOT NULL,       -- 单条内容指纹（去重键成分）
    body_grams   VARCHAR,                -- CJK 字符 bigram + 英文整词（FTS 辅助列，见 §0 验证1；不返回前端）
    UNIQUE (date, coin_id, source, doc_hash),
    ingested_batch_id VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_content_date   ON content_archive(date);
CREATE INDEX IF NOT EXISTS idx_content_coin   ON content_archive(coin_id);
CREATE INDEX IF NOT EXISTS idx_content_source ON content_archive(source);

-- ============================================================
-- E. 入库批次日志（幂等与监控）
-- ============================================================
CREATE TABLE IF NOT EXISTS ingest_batch (
    batch_id       VARCHAR PRIMARY KEY,  -- 如 20260928T101500Z-backfill
    started_at     TIMESTAMP,
    finished_at    TIMESTAMP,
    mode           VARCHAR,              -- backfill | incremental
    scope          VARCHAR,              -- all | daily_scan | macro | content
    status         VARCHAR,              -- running|success|partial|failed
    rows_loaded    BIGINT DEFAULT 0,
    rows_rejected  BIGINT DEFAULT 0,
    error_msg      VARCHAR
);

-- 逐文件处理台账：支持断点续跑 + 跳过未变更文件（幂等第二重）
CREATE TABLE IF NOT EXISTS ingest_file_log (
    batch_id     VARCHAR NOT NULL,
    file_path    VARCHAR NOT NULL,       -- 相对项目根
    file_md5     VARCHAR,
    file_mtime   TIMESTAMP,
    rows         INTEGER,
    status       VARCHAR,                -- ok|skipped|error
    processed_at TIMESTAMP,
    PRIMARY KEY (batch_id, file_path)
);

-- ============================================================
-- F. 缺口/健康度视图（R7 / US-3）
-- ============================================================
-- F1. 采集日历（应有日期 vs 实际落盘），暴露 33 天断更与残缺日
CREATE OR REPLACE VIEW v_collection_calendar AS
WITH bounds AS (SELECT MIN(date) lo, MAX(date) hi FROM scan_day),
cal AS (SELECT UNNEST(generate_series(bounds.lo, bounds.hi, INTERVAL 1 DAY))::DATE AS date FROM bounds)
SELECT cal.date,
       CASE WHEN s.date IS NULL THEN FALSE ELSE TRUE END AS has_scan,
       s.deep_files_actual,
       s.is_partial,
       m.macro_snapshots,
       CASE WHEN s.date IS NULL THEN 'scan_gap'
            WHEN s.is_partial THEN 'partial' ELSE 'ok' END AS scan_state
FROM cal
LEFT JOIN scan_day s USING (date)
LEFT JOIN (SELECT date, COUNT(*) macro_snapshots FROM macro_snapshot GROUP BY date) m USING (date)
ORDER BY cal.date;

-- F2. 逐源逐日健康度（US-3 单日 + 趋势）
CREATE OR REPLACE VIEW v_source_health_daily AS
SELECT date, source,
       COUNT(*)                                   AS total,
       SUM(CASE WHEN status='ok'    THEN 1 ELSE 0 END) AS ok_cnt,
       SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) AS err_cnt,
       ROUND(AVG(CASE WHEN status='ok' THEN 1 ELSE 0 END), 4) AS success_rate,
       ROUND(AVG(confidence), 4)                  AS avg_confidence
FROM source_status
GROUP BY date, source;

-- F3. 源集合漂移（13 vs 14，github 时有时无）
CREATE OR REPLACE VIEW v_source_drift AS
SELECT date, COUNT(DISTINCT source) AS n_sources,
       LIST(DISTINCT source ORDER BY source) AS sources
FROM source_status GROUP BY date ORDER BY date;

-- F4. 分源断更（scan 停更 vs macro 正常，US-3 异常 B）
CREATE OR REPLACE VIEW v_collection_freshness AS
SELECT 'scan'  AS collection, MAX(date) AS last_date FROM scan_day
UNION ALL
SELECT 'macro' AS collection, MAX(date) AS last_date FROM macro_snapshot;

-- F5. 最新完整扫描日（R7：latest 跳过残缺日）
CREATE OR REPLACE VIEW v_latest_complete_date AS
SELECT MAX(date) AS date FROM scan_day WHERE COALESCE(is_partial, FALSE) = FALSE;

-- ============================================================================
-- FTS 索引（⚠️ 必须在上方所有 CREATE TABLE 之后、作为独立语句执行）
-- ============================================================================
-- 实测坑：INSTALL/LOAD/create_fts_index 若与建表语句混在同一次 execute(整段) 里，
-- DuckDB 会在绑定阶段报 `Table with name content_archive does not exist`。
-- 正确做法：建表批次与 FTS 批次分开执行（init_db.py 逐条 execute，天然分离）。
-- ⚠️ FTS 为静态索引：建索引后新增的行检索不到，必须 overwrite=1 重建。
INSTALL fts;
LOAD fts;
-- ✅ 双列单索引：body_text（英文整词/中文全词）+ body_grams（中文子串）→ 两种粒度全覆盖
-- ❌ 禁止只索引 body_grams（会致英文关键词全部失效，见 §0 验证1 / §12）
PRAGMA create_fts_index('content_archive', 'content_id', 'body_text', 'body_grams',
    stemmer='none', lower=1, strip_accents=0, overwrite=1);

-- ============================================================================
-- 冗余 date 索引移除（P0-1 / P0-2 根因修复）
-- ============================================================================
-- 已移除三处「PK 首列即 date」的**纯冗余**单列索引：
--     idx_catmem_date (category_membership.date)
--     idx_srcstat_date(source_status.date)
--     idx_snap_date   (coin_daily_snapshot.date)
--
-- 为什么移除（实测根因）：
--   1. **冗余**：三表 PK 均以 date 为首列，其 ART 索引天然支持 `date = ?` /
--      `date BETWEEN ? AND ?` 的前缀查找，单列 date 索引不带来任何查询能力增益。
--   2. **陈旧即灾难**：这些表按「自然键单元 DELETE + INSERT」重写（category_membership
--      按日、source_status 按 (date, coin_id)），冗余二级索引会在重写后**变陈旧**；
--      而优化器会优先挑「更窄的单列索引」做**等值查找**（ART equality lookup）→
--      返回错误行数：category_membership 2026-06-27 等值查得 0（真值 1241）、
--      source_status 2026-06-30 等值查得 618（真值 871）。
--      （同时验证：PK 索引本身是**正确**的——按完整 PK 点查正常；
--       仅冗余的 date 单列索引陈旧并「遮蔽」了 PK 索引。范围查/BETWEEN 不受影响，
--       故 `disabled_optimizers='filter_pushdown'` 或 DROP 该索引即恢复正确。）
--   3. **静默**：应用层 `DuckDBRepository.load_by_category_raw` 用 `WHERE date = ?::DATE`
--      取数，命中索引返回 0 行 → 触发「请求级回退文件」，老端点表面正常、实则 7/9 日期
--      静默走文件回退（长期未被发现），故必须从源头移除该隐患。
--
-- 兼容旧库：`init_db.apply_schema` 会幂等地执行 `DROP INDEX IF EXISTS`
-- 清理上述遗留索引（见 init_db.LEGACY_REDUNDANT_INDEXES）。

