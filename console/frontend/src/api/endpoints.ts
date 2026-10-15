// 后端端点路径常量（与后端 routers 一致；路径已含 /api 前缀）。
export const ENDPOINTS = {
  meta: '/api/meta',
  marketOverview: '/api/market/overview',
  tokenDetail: (id: string) => `/api/tokens/${id}`,
  tokenResearch: (id: string) => `/api/tokens/${id}/research`,
  tokenTwitter: (id: string) => `/api/tokens/${id}/twitter`,
  opportunityRadar: '/api/opportunity/radar',
  comparison: '/api/comparison',
  onchain: '/api/onchain',
  score: (id: string) => `/api/score/${id}`,
  macroBtcDominance: '/api/macro/btc-dominance',

  // ---------------- 历史数据库 H1–H8（只读，见 docs/history-db/ARCHITECTURE.md §8）----------------
  historyDates: '/api/history/dates',
  historyCoinSeries: (coinId: string) => `/api/history/coin/${coinId}/series`,
  historyCategoriesTimeline: '/api/history/categories/timeline',
  historyNewsTimeline: '/api/history/news/timeline',
  historySearch: '/api/history/search',
  historyHealthSources: '/api/history/health/sources',
  historyHealthOverview: '/api/history/health/overview',
  historyMacroSeries: '/api/history/macro/series',
} as const;
