// 后端端点路径常量（与后端 routers 一致；路径已含 /api 前缀）。
export const ENDPOINTS = {
  meta: '/api/meta',
  marketOverview: '/api/market/overview',
  tokenDetail: (id: string) => `/api/tokens/${id}`,
  tokenResearch: (id: string) => `/api/tokens/${id}/research`,
  opportunityRadar: '/api/opportunity/radar',
  comparison: '/api/comparison',
  onchain: '/api/onchain',
  score: (id: string) => `/api/score/${id}`,
  macroBtcDominance: '/api/macro/btc-dominance',
} as const;
