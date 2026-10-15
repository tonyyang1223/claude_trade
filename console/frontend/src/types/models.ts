// 前端类型定义 —— 与后端 data/schemas.py（Pydantic）一一对应。

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
  /** 离线基线仅含 categories；description/officialLinks/communityLinks 由实时抓取补全 */
  narrative: Record<string, any>;
  social: Record<string, any>;
  /** 离线基线恒为空列表（计数见 social.newsCount），实时列表由 research 返回 */
  news: NewsItem[];
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

/** Twitter 舆情条目（来自豆包爬取的 Twitter 数据，已入库历史库 content_archive）。 */
export interface TwitterPost {
  coinId: string;
  docType: 'tweet' | 'event';
  title?: string;
  url?: string;
  author?: string;
  text?: string;
  publishedTs?: string;
  score?: number;
  likes?: number;
  retweets?: number;
  replies?: number;
  sentiment?: string;
  tweetId?: string;
  eventType?: string;
}

export interface TwitterFeed {
  coinId: string;
  count: number;
  posts: TwitterPost[];
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
  scanTime?: string;
  deepTotal?: number;
  lightTotal?: number;
  coinCnt?: number;
  availableDates: string[];
  weights: Record<string, number>;
}
