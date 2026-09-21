"""代币网页研究模块（Web Research）。

通过「CoinGecko API（结构化主干）+ 真实网页抓取（深度字段）」的混合方式，
为 crypto-token-defi-research 框架补充 API 给不了的关键信息：项目叙事、
官方/社媒链接、社区情绪、上线时间，以及 API 无法覆盖的 近期新闻动态、安全审计、团队融资。

设计约定（与 token_defi 一致）：
- 不编造数据：取不到的字段一律为 None / 空列表，由展示层决定呈现。
- 来源 + 时点：每条关键数据带来源（sources）与抓取时间（fetched_at）。
- 调用纪律：限流退避、失败隔离、单源失败不影响整体。

技术路线：混合（静态 bs4 为主 + 可选渲染钩子）。渲染钩子优先 Scrapling，
其次 Playwright，最后回退静态 requests——三者皆 lazy import，缺失不报错。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.api.coingecko import CoinGeckoClient
from src.api.reddit_free import RedditFreeClient
from src.data.cache import DataCache

# 已知审计/安全机构（用于官网文本命中识别，去重）
_KNOWN_AUDIT_FIRMS = [
    "CertiK", "SlowMist", "Hacken", "Quantstamp", "Trail of Bits",
    "OpenZeppelin", "PeckShield", "Consensys Diligence", "Zellic",
    "BlockSec", "Immunefi", "Sherlock",
]
KNOWN_AUDIT_FIRMS: List[str] = sorted(
    {f.lower(): f for f in _KNOWN_AUDIT_FIRMS}.values()
)

# 团队/融资关键词（官网文本 best-effort 识别）
_TEAM_FUNDING_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(raised|secured|completed|closed).{0,40}?\$?\s?[\d.]+\s?(million|billion|M\b|B\b|bn)", re.I),
     "融资额关键词"),
    (re.compile(r"(backed by|investors include|venture|founded by|our team|founders|co-?founder)", re.I),
     "团队/投资方关键词"),
]

SOURCE_COINGECKO = "CoinGecko"
SOURCE_WEB = "Official Site (web scrape)"
SOURCE_REDDIT = "Reddit (Free)"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass
class WebProfile:
    """单个代币的网页研究档案（全量深度字段）。

    Attributes:
        coin_id: CoinGecko 代币 ID
        symbol / name: 符号 / 名称
        description: 项目叙事 / 简介（英文）
        categories: 所属赛道 / 标签
        genesis_date: 上线时间（ISO）
        official_links: 官网 / 白皮书 / 浏览器 / 论坛 / GitHub
        community_links: Twitter / Facebook / Telegram / Reddit
        sentiment: 社区情绪投票 {up_pct, down_pct}
        watchlist_users: CoinGecko 关注人数
        news: 近期新闻 / 社区动态列表
        audit_info: 审计机构命中（best-effort）
        team_info: 团队 / 融资线索（best-effort）
        sources: 实际命中的数据源
        confidence: 综合置信度（0~1）
        fetched_at: 抓取时间（UTC ISO）
    """

    coin_id: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    genesis_date: Optional[str] = None
    official_links: Dict[str, Any] = field(default_factory=dict)
    community_links: Dict[str, Any] = field(default_factory=dict)
    sentiment: Dict[str, Optional[float]] = field(default_factory=dict)
    watchlist_users: Optional[int] = None
    news: List[Dict[str, Any]] = field(default_factory=list)
    audit_info: List[Dict[str, Any]] = field(default_factory=list)
    team_info: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    confidence: float = 0.0
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（便于 JSON 序列化）。"""
        return asdict(self)


class TokenWebResearcher:
    """代币网页研究器：混合抓取（API 主干 + 网页深度字段）。

    Attributes:
        coingecko: CoinGecko 客户端（结构化主干 + id 解析）
        reddit: Reddit 自由客户端（社区动态兜底）
        use_render: 是否启用渲染钩子（Scrapling/Playwright）抓取 JS 重度页
    """

    def __init__(
        self,
        coingecko: Optional[CoinGeckoClient] = None,
        reddit: Optional[RedditFreeClient] = None,
        cache_dir: Path = Path("data/cache"),
        use_render: bool = False,
    ) -> None:
        self.coingecko = coingecko or CoinGeckoClient()
        self.reddit = reddit or RedditFreeClient(cache_dir=cache_dir)
        self.cache = DataCache(cache_dir, expire_hours=24)
        self.use_render = use_render
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    # ------------------------------------------------------------------
    # id 解析
    # ------------------------------------------------------------------
    def resolve_coin_id(self, token: str) -> str:
        """将自由文本解析为 CoinGecko coin id（直接尝试 -> 搜索兜底）。"""
        token = (token or "").strip()
        if not token:
            return ""
        try:
            prof = self.coingecko.get_coin_profile(token.lower())
            if prof.get("id"):
                return prof["id"]
        except Exception:
            pass
        hits = self.coingecko.search_coins(token)
        if hits:
            return hits[0]["id"]
        return token.lower()

    # ------------------------------------------------------------------
    # 抓取调度
    # ------------------------------------------------------------------
    def _fetch_html(self, url: str, timeout: int = 25) -> Optional[str]:
        """获取页面 HTML：优先渲染钩子，回退静态 requests。"""
        html = self._try_render(url) if self.use_render else None
        if html:
            return html
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"Warning: fetch failed for {url}: {e}")
            return None

    def _try_render(self, url: str) -> Optional[str]:
        """渲染钩子：Scrapling -> Playwright -> None（lazy import，缺失不报错）。"""
        # 1) Scrapling（自适应 + 反爬，用户此前调研的框架）
        try:
            from scrapling import StealthyFetcher
            StealthyFetcher.adaptive = True
            page = StealthyFetcher.fetch(url, headless=True)
            html = getattr(page, "html", None) or getattr(page, "content", None)
            if html:
                return html
        except Exception:
            pass
        # 2) Playwright
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=25000)
                html = page.content()
                browser.close()
                return html
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # 新闻 / 动态（多源）
    # ------------------------------------------------------------------
    def get_news(
        self, coin_id: str, symbol: Optional[str], name: Optional[str]
    ) -> List[Dict[str, Any]]:
        """采集近期新闻 / 动态：CoinGecko 新闻页(抓取) -> Reddit 社区动态兜底。"""
        news: List[Dict[str, Any]] = []

        cg_news = self._scrape_cg_news(coin_id)
        if cg_news:
            news.extend(cg_news)

        query = name or symbol
        if query:
            try:
                mentions = self.reddit.get_coin_mentions(query, limit=15)
                for post in mentions.get("posts", [])[:10]:
                    sub = post.get("subreddit")
                    # Jina 解析的帖子无 url 字段，拼出可点击的 subreddit 搜索链接兜底
                    fall_url = (
                        f"https://www.reddit.com/r/{sub}/search/?q={query}&restrict_sr=1"
                        if sub else
                        f"https://www.reddit.com/search/?q={query}"
                    )
                    news.append({
                        "title": post.get("title"),
                        "url": post.get("url") or post.get("permalink") or fall_url,
                        "source": "Reddit" + (f" /r/{sub}" if sub else ""),
                        "date": None,
                        "kind": "community",
                    })
            except Exception as e:
                print(f"Warning: Reddit news fallback failed: {e}")
        return news

    def _scrape_cg_news(self, coin_id: str) -> List[Dict[str, Any]]:
        """抓取 CoinGecko 币页 news 标签（静态；403/JS 页需渲染钩子）。"""
        url = f"https://www.coingecko.com/en/coins/{coin_id}/news"
        html = self._fetch_html(url)
        if not html:
            return []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            items = []
            for a in soup.select("a[href*='/news/']")[:15]:
                title = a.get_text(strip=True)
                href = a.get("href")
                if title and href:
                    full = ("https://www.coingecko.com" + href) if href.startswith("/") else href
                    items.append({
                        "title": title[:200],
                        "url": full,
                        "source": "CoinGecko News",
                        "date": None,
                        "kind": "news",
                    })
            return items
        except Exception:
            return []

    # ------------------------------------------------------------------
    # 官网审计 / 团队抓取
    # ------------------------------------------------------------------
    def scrape_official_site(
        self, url: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """抓取官网首页文本，识别审计机构与团队/融资线索（best-effort）。"""
        html = self._fetch_html(url)
        if not html:
            return [], {}
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text(" ", strip=True)
            text_l = text.lower()
        except Exception:
            return [], {}

        audit_info: List[Dict[str, Any]] = []
        for firm in KNOWN_AUDIT_FIRMS:
            if firm.lower() in text_l:
                audit_info.append({
                    "firm": firm,
                    "note": "官网文本命中审计/安全机构名（best-effort，需人工核验）",
                    "confidence": 0.4,
                })

        team_info: Dict[str, Any] = {}
        for pat, label in _TEAM_FUNDING_PATTERNS:
            m = pat.search(text)
            if m:
                snippet = text[max(0, m.start() - 30):m.end() + 80]
                team_info.setdefault("hits", []).append({
                    "label": label,
                    "snippet": snippet[:160],
                })
        return audit_info, team_info

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    def analyze(self, token: str) -> WebProfile:
        """研究单个代币的网页关键信息（混合抓取，失败隔离，不编造）。

        Args:
            token: 代币 id / 名称 / 符号（自由文本）

        Returns:
            WebProfile；任何单源失败只跳过并告警，不中断整体、不填充占位值。
        """
        coin_id = self.resolve_coin_id(token)
        sources: List[str] = []
        confidence = 0.0

        # 主干：CoinGecko API（叙事/链接/情绪/分类/上线时间）
        try:
            prof = self.coingecko.get_coin_profile(coin_id)
            sources.append(SOURCE_COINGECKO)
            confidence = max(confidence, 0.8)
        except Exception as e:
            print(f"Warning: CoinGecko profile failed for {coin_id}: {e}")
            prof = {}

        # 深度字段：官网审计 / 团队
        audit_info: List[Dict[str, Any]] = []
        team_info: Dict[str, Any] = {}
        site = (prof.get("official_links") or {}).get("website")
        if site:
            audit_info, team_info = self.scrape_official_site(site)
            if audit_info or team_info:
                sources.append(SOURCE_WEB)
                confidence = max(confidence, 0.6)

        # 深度字段：新闻 / 动态
        news = self.get_news(coin_id, prof.get("symbol"), prof.get("name"))
        if news:
            sources.append("CoinGecko News / Reddit")

        if not sources:
            confidence = 0.1

        return WebProfile(
            coin_id=coin_id,
            symbol=prof.get("symbol"),
            name=prof.get("name"),
            description=prof.get("description"),
            categories=prof.get("categories") or [],
            genesis_date=prof.get("genesis_date"),
            official_links=prof.get("official_links") or {},
            community_links=prof.get("community_links") or {},
            sentiment=prof.get("sentiment") or {},
            watchlist_users=prof.get("watchlist_users"),
            news=news,
            audit_info=audit_info,
            team_info=team_info,
            sources=sources,
            confidence=round(confidence, 2),
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
