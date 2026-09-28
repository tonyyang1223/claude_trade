// 历史数据库查询端点 H1–H8 的前端类型定义。
// 与后端 console/backend/data/schemas.py 的 History* 系列 Pydantic 模型一一对应，
// 字段名保持 snake_case 原样（不做驼峰转换），避免与后端契约漂移。

/** H1 单日采集概要。`isPartial === null` 表示该日只有 macro、无 scan。 */
export interface HistoryDateRow {
  date: string;
  is_partial?: boolean | null;
  deep_count: number;
  light_count: number;
  macro_count: number;
}

/** H1 GET /api/history/dates */
export interface HistoryDates {
  dates: HistoryDateRow[];
  latest?: string | null;
  latest_complete?: string | null;
  latest_macro?: string | null;
}

/**
 * H2 单日数据点。`present === false` 表示该日缺该币 —— **不插值**，
 * 图表须断开而非补 0（见 ARCHITECTURE.md §8 H2）。
 * 具体指标键（price_usd / market_cap / rank …）动态附加。
 */
export interface SeriesPoint {
  date: string;
  present: boolean;
  [metric: string]: string | number | boolean | null | undefined;
}

/** H2 GET /api/history/coin/{coin_id}/series */
export interface CoinSeries {
  coin_id: string;
  metrics: string[];
  /** 请求但历史库无此列的指标（如 score / social_heat），绝不伪造 */
  unavailable: string[];
  series: SeriesPoint[];
  /** 缺失日（显式列出，便于界面提示「非 0 而是缺」） */
  gaps: string[];
}

/** H3 单日单板块统计点 */
export interface CategoryTimelinePoint {
  date: string;
  category: string;
  coin_count: number;
  total_mcap?: number | null;
  avg_chg?: number | null;
}

/** H3 GET /api/history/categories/timeline */
export interface CategoriesTimeline {
  series: CategoryTimelinePoint[];
}

/** H4 单条新闻/内容归档项 */
export interface NewsTimelineItem {
  date: string;
  coin_id: string;
  source: string;
  title?: string | null;
  url?: string | null;
  ts?: string | null;
  origin_path?: string | null;
}

/** H4 GET /api/history/news/timeline */
export interface NewsTimeline {
  items: NewsTimelineItem[];
  total: number;
}

/**
 * H5 单条检索命中。
 * `score` 为 FTS match_bm25 打分；走 ILIKE 兜底路径时**无打分** → null。
 * 界面据此标注命中来源，不要伪造分值。
 */
export interface SearchHit {
  content_id: string;
  date?: string | null;
  coin_id?: string | null;
  source?: string | null;
  title?: string | null;
  snippet?: string | null;
  url?: string | null;
  origin_path?: string | null;
  score?: number | null;
}

/** H5 GET /api/history/search */
export interface SearchResponse {
  query: string;
  hits: SearchHit[];
  total: number;
  took_ms: number;
}

/** H6 单日单源健康度 */
export interface SourceHealthDay {
  date: string;
  source: string;
  ok: number;
  error: number;
  success_rate?: number | null;
  avg_confidence?: number | null;
}

/** H6 单日源集合规模（漂移探针） */
export interface SourceDriftRow {
  date: string;
  n_sources: number;
}

/** H6 GET /api/history/health/sources */
export interface HealthSources {
  by_date: SourceHealthDay[];
  drift: SourceDriftRow[];
  gaps: string[];
}

/** H7 单个采集链路的新鲜度。status: ok | stale | empty | unknown */
export interface CollectionStatus {
  last_date?: string | null;
  gap_days?: number | null;
  status: string;
}

/** H7 GET /api/history/health/overview */
export interface HealthOverview {
  collections: Record<string, CollectionStatus>;
  anomalies: Record<string, any>[];
  batches: Record<string, any>[];
}

/** H8 单个宏观快照数据点 */
export interface MacroSeriesPoint {
  snapshot_at?: string | null;
  value?: number | null;
}

/** H8 GET /api/history/macro/series */
export interface MacroHistorySeries {
  metric: string;
  series: MacroSeriesPoint[];
}

/** H2 可用指标白名单（与后端 history_svc.SERIES_METRICS 同步；仅用于界面提示）。 */
export const SERIES_METRIC_LABELS: Record<string, string> = {
  price_usd: '价格',
  market_cap: '市值',
  rank: '市值排名',
  volume_24h: '24h 成交额',
  change_24h_pct: '24h 涨跌',
  change_7d_pct: '7d 涨跌',
};
