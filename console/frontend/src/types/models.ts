// 前端类型定义 —— 与后端 data/schemas.py（Pydantic）一一对应。

export interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
}

export interface ApiError {
  code: number;
  message: string;
  data: unknown;
}

export interface CoinBrief {
  id: string;
  sym?: string;
  name?: string;
  rank?: number;
  price?: number;
  mcap?: number;
  vol?: number;
  chg24?: number;
  chg7d?: number;
}

export interface NewsItem {
  title?: string;
  url?: string;
  source?: string;
  date?: string;
  kind?: string;
}

export interface SectorStat {
  cat: string;
  count: number;
  mcap?: number;
  avgChg: number;
}

export interface MarketOverview {
  meta: Record<string, any>;
  kpi: Record<string, any>;
  distribution: { labels: string[]; values: number[] };
  gainers: CoinBrief[];
  losers: CoinBrief[];
  topByMcap: CoinBrief[];
  sectors: SectorStat[];
}

export interface OpportunityItem {
  id: string;
  sym?: string;
  name?: string;
  rank?: number;
  mcap?: number;
  composite: number;
  dims: Record<string, number>;
  category?: string;
}

export interface OpportunityRadar {
  meta: Record<string, any>;
  rankings: OpportunityItem[];
}

export interface TokenDetail {
  basic: CoinBrief;
  ath?: number;
  athChg?: number;
  narrative: Record<string, any>;
  social: Record<string, any>;
  news: NewsItem[];
  scoresAvailable: boolean;
  onchainAvailable: boolean;
  dataSource: string;
}

export interface WebResearch {
  coinId: string;
  symbol?: string;
  name?: string;
  description?: string;
  categories: string[];
  officialLinks: Record<string, any>;
  communityLinks: Record<string, any>;
  sentiment: Record<string, any>;
  watchlistUsers?: number;
  news: NewsItem[];
  sources: string[];
  confidence: number;
  fetchedAt?: string;
}

export interface ComparisonProject {
  coin_id: string;
  coin_name?: string;
  symbol?: string;
  total_score?: number;
  rating?: string;
  risk_level?: string;
  recommendation?: string;
  market_score?: number;
  technical_score?: number;
  onchain_score?: number;
  sentiment_score?: number;
  github_score?: number;
  social_score?: number;
  risk_score?: number;
  unlock?: Record<string, any>;
}

export interface Comparison {
  projects: ComparisonProject[];
  matrix: Record<string, any>;
  winner: string;
  summary: string;
}

export interface Onchain {
  chain: string;
  address: string;
  symbol?: string;
  name?: string;
  dims: Record<string, number>;
  total: number;
  decision: string;
  risk: string;
  position: string;
  triggers: string[];
  missing: string[];
  flags: any[];
  disclaimer: string;
}

export interface Score {
  coinId: string;
  name?: string;
  symbol?: string;
  scores: Record<string, number>;
  totalScore: number;
  rating: string;
  recommendation: string;
  riskLevel: string;
  advice: Record<string, any>;
}

export interface Macro {
  currentDominance: number;
  trend: string;
  marketPhase: string;
  altcoinSeason: boolean;
  recommendation: string;
}

export interface MetaInfo {
  date?: string;
  prevDay?: string;
  scanTime?: string;
  deepTotal?: number;
  lightTotal?: number;
  coinCnt?: number;
  availableDates: string[];
  weights: Record<string, number>;
}

export interface HealthInfo {
  status: string;
  version: string;
  dataDate?: string;
}
