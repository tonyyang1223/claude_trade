#!/usr/bin/env python3
"""Gradual cryptocurrency scanner - 10 minutes per coin.

Strategy:
  - Market snapshot: hourly refresh for all 800 coins (light data)
  - Deep research: 1 coin per 10-minute cycle, gradual accumulation
  - Priority queue: Top 10 (4h refresh), Top 11-50 (12h), Top 51-200 (24h), Top 201-800 (once)
  - Interruptible: state file tracks progress, resume from last position

Usage:
  python scripts/scan/scan_top_800.py                    # Daemon mode (recommended)
  python scripts/scan/scan_top_800.py --once             # Single cycle
  python scripts/scan/scan_top_800.py --market-only      # Just market snapshot
  python scripts/scan/scan_top_800.py --deep-next        # Process next deep research coin
  python scripts/scan/scan_top_800.py --status           # Show current state
"""
import argparse
import json
import signal
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.api.coingecko import CoinGeckoClient
from src.api.coinglass import CoinglassClient
from src.api.defillama import DefiLlamaClient
from src.api.social_sentiment import SocialSentimentClient
from src.api.github import GithubClient
from src.api.sentiment_api import SentimentAPIClient
from src.api.twitter import TwitterClient
from src.api.reddit_free import RedditFreeClient
from src.api.community import CommunityClient
from src.data.cache import DataCache
# Reuse the type-aware classifier (single source of truth, fixes the old
# substring bug e.g. 'Chainlink' -> 'ai' via word-boundary matching).
from src.research.token_classification import classify_coin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scan")

# ── Configuration ──

MARKET_REFRESH_INTERVAL = 3600  # 1 hour
DEEP_RESEARCH_INTERVAL = 600    # 10 minutes
TOP_LIMIT = 800
COINGECKO_DELAY = 3.0           # Seconds between CoinGecko calls (avoid 429)

# Refresh intervals by rank tier (in hours)
REFRESH_HOURS = {
    (1, 10): 4,      # Top 10: refresh every 4 hours
    (11, 50): 12,    # Top 11-50: refresh every 12 hours
    (51, 200): 24,   # Top 51-200: refresh every 24 hours
    (201, 800): 168, # Top 201-800: refresh once per week (essentially "once")
}


# ── State management ──

class ScanState:
    """Track scanning progress with JSON state file."""

    def __init__(self, state_path: Path):
        self.state_path = state_path
        self.state = self._load()

    def _load(self) -> Dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "last_market_snapshot": None,
            "coins": {},
            "deep_queue": [],
            "total_coins": 0,
            "version": 1,
        }

    def save(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        log.info(f"State saved: {self.state_path}")

    def get_refresh_hours(self, rank: int) -> int:
        """Get refresh interval for a coin by its rank."""
        for (start, end), hours in REFRESH_HOURS.items():
            if start <= rank <= end:
                return hours
        return 168  # Default: weekly

    def needs_deep_research(self, coin_id: str, rank: int) -> bool:
        """Check if coin needs deep research based on staleness."""
        coin_info = self.state["coins"].get(coin_id)
        if not coin_info:
            return True  # Never researched

        last_deep = coin_info.get("last_deep")
        if not last_deep:
            return True

        try:
            last_time = datetime.fromisoformat(last_deep)
            refresh_hours = self.get_refresh_hours(rank)
            threshold = timedelta(hours=refresh_hours)
            return datetime.now() - last_time > threshold
        except Exception:
            return True

    def update_coin(self, coin_id: str, rank: int, depth: str = "light"):
        """Update coin state after processing."""
        if coin_id not in self.state["coins"]:
            self.state["coins"][coin_id] = {"rank": rank, "depth": "none"}

        self.state["coins"][coin_id]["rank"] = rank
        if depth == "deep":
            self.state["coins"][coin_id]["last_deep"] = datetime.now().isoformat()
            self.state["coins"][coin_id]["depth"] = "deep"
        elif depth == "light":
            self.state["coins"][coin_id]["last_light"] = datetime.now().isoformat()
            if self.state["coins"][coin_id]["depth"] == "none":
                self.state["coins"][coin_id]["depth"] = "light"

    def update_market_snapshot_time(self):
        self.state["last_market_snapshot"] = datetime.now().isoformat()

    def build_deep_queue(self, coins: List[Dict]) -> List[str]:
        """Build priority queue of coins needing deep research."""
        queue = []
        for coin in coins:
            coin_id = coin.get("id")
            rank = coin.get("market_cap_rank") or 999
            if rank <= 200 and self.needs_deep_research(coin_id, rank):
                queue.append((rank, coin_id))

        # Sort by rank (priority)
        queue.sort(key=lambda x: x[0])
        return [c[1] for c in queue]

    def get_stats(self) -> Dict:
        """Get summary statistics."""
        deep_count = sum(1 for c in self.state["coins"].values() if c.get("depth") == "deep")
        light_count = sum(1 for c in self.state["coins"].values() if c.get("depth") in ("light", "deep"))
        return {
            "total_coins_known": len(self.state["coins"]),
            "deep_researched": deep_count,
            "light_researched": light_count,
            "last_market_snapshot": self.state.get("last_market_snapshot"),
            "queue_length": len(self.state.get("deep_queue", [])),
        }


# ── API fetchers ──

def fetch_market_snapshot(cg: CoinGeckoClient, limit: int = TOP_LIMIT) -> List[Dict]:
    """Fetch light market data for all top coins (1 API call per page)."""
    all_coins = []
    pages = (limit + 249) // 250
    for page in range(1, pages + 1):
        per_page = min(250, limit - len(all_coins))
        if per_page <= 0:
            break
        try:
            url = f"{cg.BASE_URL}/coins/markets"
            params = {
                "vs_currency": "usd", "order": "market_cap_desc",
                "per_page": per_page, "page": page,
                "sparkline": "false", "price_change_percentage": "24h,7d",
            }
            resp = cg.session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                batch = resp.json()
                all_coins.extend(batch)
                log.info(f"  Market page {page}/{pages}: +{len(batch)} (total: {len(all_coins)})")
        except Exception as e:
            log.warning(f"  Market page {page} error: {e}")
        time.sleep(1.5)  # CoinGecko rate limit
    return all_coins[:limit]


def light_research(coin: Dict) -> Dict[str, Any]:
    """Extract light market data from CoinGecko response."""
    return {
        "id": coin.get("id"),
        "symbol": coin.get("symbol", "").upper(),
        "name": coin.get("name"),
        "rank": coin.get("market_cap_rank"),
        "price_usd": coin.get("current_price"),
        "market_cap": coin.get("market_cap"),
        "volume_24h": coin.get("total_volume"),
        "change_24h_pct": coin.get("price_change_percentage_24h"),
        "change_7d_pct": coin.get("price_change_percentage_7d_in_currency"),
        "circulating_supply": coin.get("circulating_supply"),
        "total_supply": coin.get("total_supply"),
        "max_supply": coin.get("max_supply"),
        "timestamp": datetime.now().isoformat(),
    }


def deep_research(coin_id: str, cg: CoinGeckoClient) -> Dict[str, Any]:
    """Full multi-source research for a single coin."""
    report = {
        "coin_id": coin_id,
        "research_time": datetime.now().isoformat(),
        "sources": {},
    }

    def step(name: str, func, key: str):
        try:
            data = func()
            report["sources"][key] = {"status": "ok", "data": data}
            log.info(f"    {name}: ok")
        except Exception as e:
            report["sources"][key] = {"status": "error", "error": str(e)}
            log.warning(f"    {name}: error ({e})")

    # Sequential API calls with natural spacing
    step("CoinGecko market", lambda: cg.get_coin_data(coin_id), "market")
    time.sleep(COINGECKO_DELAY)  # Avoid 429 rate limit

    # Funding & OI (Binance - unlimited)
    cgl = CoinglassClient()
    step("Funding rate", lambda: cgl.get_funding_rate(coin_id.upper() + "USDT"), "funding_rate")
    step("Open interest", lambda: cgl.get_open_interest(coin_id.upper() + "USDT"), "open_interest")

    # DefiLlama (unlimited)
    step("Stablecoin flows", lambda: DefiLlamaClient().get_stablecoin_flows(), "stablecoin_flows")

    # CryptoCompare (rate limited - be careful)
    time.sleep(2)
    step("Social stats", lambda: SocialSentimentClient().get_coin_social_stats(coin_id), "social_stats")

    # Twitter/Reddit via Jina (free but don't abuse)
    time.sleep(1)
    step("Twitter", lambda: TwitterClient().get_profile(coin_id), "twitter")
    step("Reddit", lambda: RedditFreeClient().get_coin_mentions(coin_id.upper()), "reddit")

    # Community sources
    comm = CommunityClient()
    time.sleep(1)
    step("Crypto news", lambda: comm.get_crypto_news(limit=5), "crypto_news")
    step("RSS feed", lambda: comm.get_rss_feed(), "rss")
    step("V2EX", lambda: comm.get_v2ex_hot(limit=5), "v2ex")
    step("Bilibili", lambda: comm.search_bilibili(coin_id, limit=3), "bilibili")
    step("Community score", lambda: comm.get_community_score(coin_id), "community_score")

    # GitHub (if repo mapping exists)
    try:
        from src.data.coin_mappings import COIN_TO_REPO
        repo = COIN_TO_REPO.get(coin_id)
        if repo:
            parts = repo.split("/")
            if len(parts) == 2:
                time.sleep(1)
                step("GitHub", lambda: GithubClient().get_repo_info(parts[0], parts[1]), "github")
    except ImportError:
        pass

    # Sentiment (unlimited)
    step("Sentiment", lambda: SentimentAPIClient().get_combined_sentiment(), "sentiment")

    return report


def get_coin_categories(cg: CoinGeckoClient, coin_id: str) -> List[str]:
    """Fetch categories for a coin."""
    try:
        url = f"{cg.BASE_URL}/coins/{coin_id}"
        resp = cg.session.get(url, params={
            "localization": "false", "tickers": "false",
            "market_data": "false", "community_data": "false",
            "developer_data": "false",
        }, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("categories", [])
    except Exception:
        pass
    return []


# ── Save functions ──

def save_light_data(base_dir: Path, coins: List[Dict], state: ScanState):
    """Save light market snapshot."""
    light_dir = base_dir / "top_800_light"
    light_dir.mkdir(parents=True, exist_ok=True)

    light_data = []
    for coin in coins:
        ld = light_research(coin)
        light_data.append(ld)
        state.update_coin(coin.get("id"), coin.get("market_cap_rank", 999), "light")

    (light_dir / "all_coins.json").write_text(
        json.dumps(light_data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )
    log.info(f"  Saved {len(light_data)} light coins")


def save_deep_data(base_dir: Path, coin_id: str, report: Dict, coin_meta: Dict, state: ScanState):
    """Save deep research report."""
    detailed_dir = base_dir / "top_50_detailed"
    detailed_dir.mkdir(parents=True, exist_ok=True)

    # Add metadata
    report["symbol"] = coin_meta.get("symbol", "").upper()
    report["name"] = coin_meta.get("name", coin_id)
    report["rank"] = coin_meta.get("market_cap_rank")

    # Get categories (with delay to avoid rate limit)
    time.sleep(COINGECKO_DELAY)
    cg = CoinGeckoClient()
    cats = get_coin_categories(cg, coin_id)
    slug = classify_coin(cats)
    report["categories"] = cats
    report["category_slug"] = slug

    # Save files
    (detailed_dir / f"{coin_id}.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )
    save_by_category(base_dir, coin_id, slug, report)

    # Update state
    state.update_coin(coin_id, coin_meta.get("market_cap_rank", 999), "deep")
    log.info(f"  Deep research saved: {coin_id} (rank {report['rank']})")


def save_by_category(base_dir: Path, coin_id: str, category_slug: str, data: Dict):
    """Save coin data organized by category."""
    cat_dir = base_dir / "by_category" / category_slug
    cat_dir.mkdir(parents=True, exist_ok=True)
    (cat_dir / f"{coin_id}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )


def save_summary(base_dir: Path, state: ScanState, coins: List[Dict]):
    """Update summary file."""
    total_mcap = sum(c.get("market_cap", 0) or 0 for c in coins)
    avg_chg = sum(c.get("price_change_percentage_24h", 0) or 0 for c in coins) / max(len(coins), 1)

    # Count categories
    category_counts = {}
    cat_base = base_dir / "by_category"
    if cat_base.exists():
        for cat_dir in cat_base.iterdir():
            if cat_dir.is_dir():
                category_counts[cat_dir.name] = len(list(cat_dir.glob("*.json")))

    # Fear & Greed
    try:
        fg_data = SentimentAPIClient().get_fear_greed_index()
        fg_val = fg_data.get("data", [{}])[0].get("value") if isinstance(fg_data.get("data"), list) else None
    except Exception:
        fg_val = None

    stats = state.get_stats()

    summary = {
        "scan_time": datetime.now().isoformat(),
        "total_coins": len(coins),
        "deep_researched": stats["deep_researched"],
        "light_researched": stats["light_researched"],
        "categories": category_counts,
        "market_stats": {
            "total_market_cap": total_mcap,
            "avg_change_24h_pct": round(avg_chg, 2),
            "fear_greed_index": fg_val,
        },
        "state_stats": stats,
    }
    (base_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )


# ── Main operations ──

def run_market_snapshot(state: ScanState, output_base: Path = None):
    """Run market snapshot for all top coins."""
    start = time.time()
    today = datetime.now().strftime("%Y-%m-%d")
    base_dir = (output_base or project_root / "data" / "reports" / "daily_scan") / today
    base_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("MARKET SNAPSHOT START")

    cg = CoinGeckoClient()
    coins = fetch_market_snapshot(cg, limit=TOP_LIMIT)

    if coins:
        state.state["total_coins"] = len(coins)
        save_light_data(base_dir, coins, state)

        # Light data doesn't need per-coin categorization (too slow)
        # Categorization happens during deep research only
        log.info("  Light data saved (categorization deferred to deep research)")

        state.update_market_snapshot_time()
        save_summary(base_dir, state, coins)
        state.save()

    elapsed = time.time() - start
    log.info(f"MARKET SNAPSHOT DONE | {len(coins)} coins | {elapsed:.1f}s")
    log.info("=" * 60)
    return coins


def light_data_from_file(base_dir: Path) -> List[Dict]:
    """Load light data from file."""
    light_file = base_dir / "top_800_light" / "all_coins.json"
    if light_file.exists():
        return json.loads(light_file.read_text(encoding="utf-8"))
    return []


def run_deep_research_one(state: ScanState, output_base: Path = None) -> Optional[str]:
    """Process next coin in deep research queue."""
    today = datetime.now().strftime("%Y-%m-%d")
    base_dir = (output_base or project_root / "data" / "reports" / "daily_scan") / today
    base_dir.mkdir(parents=True, exist_ok=True)

    # Get next coin from queue
    queue = state.state.get("deep_queue", [])
    if not queue:
        log.info("Deep queue empty, nothing to process")
        return None

    coin_id = queue[0]
    log.info("=" * 60)
    log.info(f"DEEP RESEARCH: {coin_id}")

    # Find coin metadata from state
    coin_info = state.state["coins"].get(coin_id, {})
    coin_meta = {
        "id": coin_id,
        "rank": coin_info.get("rank", 999),
        "symbol": "",
        "name": coin_id,
    }

    # Run deep research
    cg = CoinGeckoClient()
    start = time.time()
    report = deep_research(coin_id, cg)

    # Save results
    save_deep_data(base_dir, coin_id, report, coin_meta, state)

    # Remove from queue
    state.state["deep_queue"] = queue[1:]
    state.save()

    elapsed = time.time() - start
    log.info(f"DEEP RESEARCH DONE | {coin_id} | {elapsed:.1f}s")
    log.info("=" * 60)
    return coin_id


def rebuild_deep_queue(state: ScanState, coins: List[Dict]):
    """Rebuild deep research queue based on current coins and staleness."""
    queue = state.build_deep_queue(coins)
    state.state["deep_queue"] = queue
    state.save()
    log.info(f"Deep queue rebuilt: {len(queue)} coins need research")


# ── Daemon loop ──

class GracefulExit:
    shutdown = False

    @classmethod
    def install(cls):
        signal.signal(signal.SIGINT, cls._handler)
        signal.signal(signal.SIGTERM, cls._handler)

    @classmethod
    def _handler(cls, signum, frame):
        log.info(f"Received signal {signum}, shutting down...")
        cls.shutdown = True


def daemon_loop(state: ScanState, output_base: Path = None):
    """Main daemon loop - market snapshot hourly, deep research every 10 min."""
    GracefulExit.install()

    log.info("=" * 60)
    log.info("GRADUAL SCAN DAEMON STARTED")
    log.info(f"  Market snapshot: every {MARKET_REFRESH_INTERVAL}s")
    log.info(f"  Deep research: every {DEEP_RESEARCH_INTERVAL}s")
    log.info("=" * 60)

    last_market_time = 0
    cycle_count = 0

    while not GracefulExit.shutdown:
        cycle_count += 1
        now = time.time()

        log.info(f"\n--- Cycle #{cycle_count} ---")

        # Market snapshot (hourly)
        if now - last_market_time >= MARKET_REFRESH_INTERVAL:
            log.info("Time for market snapshot...")
            coins = run_market_snapshot(state, output_base)
            if coins:
                rebuild_deep_queue(state, coins)
            last_market_time = now

        # Deep research (one coin per cycle)
        coin_processed = run_deep_research_one(state, output_base)

        if not coin_processed:
            if state.state.get("total_coins", 0) > 0:
                log.info("Queue empty, waiting for next market snapshot to rebuild")

        # Sleep until next cycle
        log.info(f"Next cycle in {DEEP_RESEARCH_INTERVAL}s...")
        for _ in range(DEEP_RESEARCH_INTERVAL):
            if GracefulExit.shutdown:
                break
            time.sleep(1)

    log.info("Daemon stopped gracefully")


# ── CLI ──

def show_status(state: ScanState):
    """Display current state."""
    stats = state.get_stats()
    log.info("=" * 60)
    log.info("SCAN STATE STATUS")
    log.info("=" * 60)
    log.info(f"  Total coins known: {stats['total_coins_known']}")
    log.info(f"  Deep researched: {stats['deep_researched']}")
    log.info(f"  Light researched: {stats['light_researched']}")
    log.info(f"  Last market snapshot: {stats['last_market_snapshot']}")
    log.info(f"  Deep queue length: {stats['queue_length']}")

    if stats['queue_length'] > 0:
        queue = state.state.get("deep_queue", [])
        log.info(f"  Next coins to research: {queue[:10]}")
    log.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Gradual cryptocurrency scanner")
    parser.add_argument("--once", action="store_true", help="Run single cycle and exit")
    parser.add_argument("--market-only", action="store_true", help="Run market snapshot only")
    parser.add_argument("--deep-next", action="store_true", help="Process next deep research coin")
    parser.add_argument("--status", action="store_true", help="Show current state")
    parser.add_argument("--output", type=str, default=None, help="Output base directory")
    parser.add_argument("--init", action="store_true", help="Initialize state with fresh market snapshot")
    args = parser.parse_args()

    output_base = Path(args.output) if args.output else None
    state_path = project_root / "data" / "reports" / "daily_scan" / "scan_state.json"
    state = ScanState(state_path)

    if args.status:
        show_status(state)
        return

    if args.init:
        log.info("Initializing state with fresh market snapshot...")
        coins = run_market_snapshot(state, output_base)
        if coins:
            rebuild_deep_queue(state, coins)
        show_status(state)
        return

    if args.market_only:
        coins = run_market_snapshot(state, output_base)
        if coins:
            rebuild_deep_queue(state, coins)
        show_status(state)
        return

    if args.deep_next:
        coin = run_deep_research_one(state, output_base)
        if coin:
            log.info(f"Processed: {coin}")
        show_status(state)
        return

    if args.once:
        # Single cycle: market if needed, then one deep
        coins = run_market_snapshot(state, output_base)
        if coins:
            rebuild_deep_queue(state, coins)
        run_deep_research_one(state, output_base)
        show_status(state)
        return

    # Default: daemon mode
    daemon_loop(state, output_base)


if __name__ == "__main__":
    main()