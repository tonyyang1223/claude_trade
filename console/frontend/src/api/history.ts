import api, { ApiError } from './client';
import { ENDPOINTS } from './endpoints';
import type {
  CategoriesTimeline,
  CoinSeries,
  HealthOverview,
  HealthSources,
  HistoryDates,
  MacroHistorySeries,
  NewsTimeline,
  SearchResponse,
} from '../types/history';

/**
 * 历史数据库查询客户端（H1–H8）。
 *
 * 与 /api/meta 等其他端点共用同一 axios 实例与信封拦截器：
 * - `code === 0` 时拦截器已解包出 `data`；
 * - 其余 code 抛 `ApiError`，其 `.data` 仍携带**同结构的空对象**（后端「绝不 500」约定）。
 *
 * 因此本模块额外导出 {@link softMiss}：页面遇到「查询成功但无数据」类 code
 * （404/503）时，应把 `ApiError.data` 当作合法的空结构渲染空态，
 * 而不是显示成加载失败——这是后端刻意设计的语义。
 */

export interface HistoryRangeParams {
  from?: string;
  to?: string;
}

export interface NewsTimelineParams extends HistoryRangeParams {
  coin_id?: string;
  category?: string;
  source?: string;
  limit?: number;
  offset?: number;
}

export interface SearchParams extends HistoryRangeParams {
  coin_id?: string;
  source?: string;
  limit?: number;
  offset?: number;
}

export interface HealthSourcesParams extends HistoryRangeParams {
  source?: string;
}

/** 空值参数不下发（避免 `from=undefined` 被后端当成非法日期）。 */
function compact<T extends Record<string, any>>(params: T): Record<string, any> {
  const out: Record<string, any> = {};
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return;
    out[k] = v;
  });
  return out;
}

/**
 * 判断是否为「软未命中」：请求本身没问题，只是该条件下无数据。
 * 后端对 H2/H3/H4/H6 返回 404、H1/H7 返回 503 并附带完整空结构，
 * 页面应渲染空态而非报错。
 */
export function softMiss(e: unknown): boolean {
  return e instanceof ApiError && (e.code === 404 || e.code === 503);
}

// ---------------- H1 采集日历 ----------------
export async function getHistoryDates(): Promise<HistoryDates> {
  return api.get(ENDPOINTS.historyDates);
}

// ---------------- H2 单币多指标时序 ----------------
export async function getCoinSeries(
  coinId: string,
  params: HistoryRangeParams = {},
  metrics: string[] = [],
): Promise<CoinSeries> {
  return api.get(ENDPOINTS.historyCoinSeries(coinId), {
    params: compact({
      ...params,
      metrics: metrics.length ? metrics.join(',') : undefined,
    }),
  });
}

// ---------------- H3 板块时间线 ----------------
export async function getCategoriesTimeline(
  params: HistoryRangeParams & { category?: string } = {},
): Promise<CategoriesTimeline> {
  return api.get(ENDPOINTS.historyCategoriesTimeline, { params: compact(params) });
}

// ---------------- H4 新闻/内容时间线 ----------------
export async function getNewsTimeline(params: NewsTimelineParams = {}): Promise<NewsTimeline> {
  return api.get(ENDPOINTS.historyNewsTimeline, { params: compact(params) });
}

// ---------------- H5 全文检索 ----------------
export async function searchHistory(q: string, params: SearchParams = {}): Promise<SearchResponse> {
  return api.get(ENDPOINTS.historySearch, { params: compact({ q, ...params }) });
}

// ---------------- H6 逐源健康度 ----------------
export async function getHealthSources(params: HealthSourcesParams = {}): Promise<HealthSources> {
  return api.get(ENDPOINTS.historyHealthSources, { params: compact(params) });
}

// ---------------- H7 采集健康度总览 ----------------
export async function getHealthOverview(): Promise<HealthOverview> {
  return api.get(ENDPOINTS.historyHealthOverview);
}

// ---------------- H8 宏观指标时序 ----------------
export async function getMacroHistorySeries(
  metric: 'btc_dominance' | 'fear_greed',
  params: HistoryRangeParams = {},
): Promise<MacroHistorySeries> {
  return api.get(ENDPOINTS.historyMacroSeries, { params: compact({ metric, ...params }) });
}

export { ApiError };
