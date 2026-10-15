import axios, { AxiosError } from 'axios';
import { ENDPOINTS } from './endpoints';
import type {
  Comparison,
  Macro,
  MarketOverview,
  MetaInfo,
  Onchain,
  OpportunityRadar,
  Score,
  TokenDetail,
  WebResearch,
  TwitterFeed,
} from '../types/models';

/**
 * 统一 API 客户端。
 * - 后端所有响应均为信封 {code, message, data}（HTTP 状态恒为 200）。
 * - 拦截器：code===0 直接解包 data；否则抛出 ApiError（携带 code/message/data），
 *   由页面层以「错误态 + 空结构」友好呈现，绝不白屏。
 */

export class ApiError extends Error {
  code: number;
  data: unknown;
  constructor(code: number, message: string, data: unknown) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.data = data;
  }
}

const api = axios.create({
  // 端点路径已含 /api 前缀（与 Vite dev proxy 转发的 /api 一一对应），
  // 故 baseURL 留空，避免拼接成 /api/api/... 导致 404。
  baseURL: '',
  timeout: 60000, // 纯本地端点（overview/meta/radar/token）实测 < 1s，60s 已是宽松上限
});

/**
 * 分析类端点的超时预算（毫秒）。
 *
 * 这些端点由用户显式点击触发，后端薄封装 src 的多维分析（每个维度各发一轮网络
 * 请求，受限网络下带重试），实测：score 单币 ≈ 30s、compare 2 币 ≈ 149s。
 * 沿用默认 60s 会让「后端已成功」的请求在客户端被判失败，故单独放宽。
 */
const HEAVY_TIMEOUT = 300000;

api.interceptors.response.use(
  (resp) => {
    const env = resp.data;
    if (env && typeof env === 'object' && 'code' in env) {
      if (env.code === 0) return env.data;
      return Promise.reject(new ApiError(env.code, env.message, env.data));
    }
    return env;
  },
  (err: AxiosError) => Promise.reject(err),
);

function withDate(date?: string): { date?: string } {
  return date && date !== 'latest' ? { date } : {};
}

// ---------------- 元信息 ----------------
export async function getMeta(): Promise<MetaInfo> {
  return api.get(ENDPOINTS.meta);
}

// ---------------- 市场总览 ----------------
export async function getMarketOverview(date?: string): Promise<MarketOverview> {
  return api.get(ENDPOINTS.marketOverview, { params: withDate(date) });
}

// ---------------- 币种档案 / 实时抓取 ----------------
export async function getTokenDetail(id: string, date?: string): Promise<TokenDetail> {
  return api.get(ENDPOINTS.tokenDetail(id), { params: withDate(date) });
}

export async function postTokenResearch(id: string): Promise<WebResearch> {
  return api.post(ENDPOINTS.tokenResearch(id));
}

export async function getTokenTwitter(id: string, limit = 30): Promise<TwitterFeed> {
  return api.get(ENDPOINTS.tokenTwitter(id), { params: { limit } });
}

// ---------------- 百倍币雷达 ----------------
export async function getOpportunityRadar(
  date?: string,
  mcapMax?: number,
  sort = 'composite',
): Promise<OpportunityRadar> {
  return api.get(ENDPOINTS.opportunityRadar, {
    params: { ...withDate(date), mcapMax, sort },
  });
}

// ---------------- 竞品对比 ----------------
export async function postComparison(coinIds: string[]): Promise<Comparison> {
  return api.post(ENDPOINTS.comparison, coinIds, { timeout: HEAVY_TIMEOUT });
}

// ---------------- 链上分析 ----------------
export async function getOnchain(chain: string, query: string, demo = false): Promise<Onchain> {
  return api.get(ENDPOINTS.onchain, { params: { chain, query, demo }, timeout: HEAVY_TIMEOUT });
}

// ---------------- 评分与建议 ----------------
export async function getScore(id: string): Promise<Score> {
  return api.get(ENDPOINTS.score(id), { timeout: HEAVY_TIMEOUT });
}

// ---------------- 宏观 BTC 占比 ----------------
export async function getMacroBtcDominance(): Promise<Macro> {
  return api.get(ENDPOINTS.macroBtcDominance);
}

export default api;
