"""Tests for src.research.web_research (token web research module).

Fixture-based tests run offline (mocked clients / injected HTML).
A live smoke test for the CoinGecko profile method is skipped when the
network is unavailable.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.research.web_research import TokenWebResearcher, WebProfile  # noqa: E402


# ---------------------------------------------------------------------------
# Fake clients (no network)
# ---------------------------------------------------------------------------
class FakeCoinGecko:
    def __init__(self, profile):
        self._profile = profile

    def get_coin_profile(self, coin_id):
        return dict(self._profile, id=coin_id)

    def search_coins(self, query):
        return [{"id": "ethena", "name": "Ethena", "symbol": "ENA", "thumb": ""}]


SAMPLE_PROFILE = {
    "symbol": "ENA",
    "name": "Ethena",
    "description": "Ethena is a synthetic dollar protocol.",
    "categories": ["DeFi", "Stablecoins"],
    "genesis_date": "2024-02-01",
    "watchlist_users": 12345,
    "sentiment": {"up_pct": 65.0, "down_pct": 35.0},
    "market_cap_rank": 80,
    "official_links": {
        "website": "https://ethena.fi",
        "whitepaper": "https://ethena.fi/whitepaper",
        "explorers": ["https://etherscan.io/token/0x..."],
        "forum": None,
        "github": ["https://github.com/ethena-labs"],
    },
    "community_links": {
        "twitter": "ethena_labs",
        "facebook": None,
        "telegram": "ethena_labs",
        "reddit": None,
    },
    "source": "CoinGecko",
    "fetched_at": "2026-09-21T00:00:00+00:00",
}


class FakeReddit:
    def get_coin_mentions(self, coin_name, subreddits=None, limit=25):
        return {
            "coin_name": coin_name,
            "total_mentions": 0,
            "posts": [],
        }


def make_researcher(profile=SAMPLE_PROFILE, reddit=None):
    return TokenWebResearcher(
        coingecko=FakeCoinGecko(profile),
        reddit=reddit or FakeReddit(),
        use_render=False,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_web_profile_to_dict():
    p = WebProfile(coin_id="bitcoin")
    d = p.to_dict()
    assert d["coin_id"] == "bitcoin"
    assert d["categories"] == []
    assert d["news"] == []
    assert d["sources"] == []
    assert 0.0 <= d["confidence"] <= 1.0


def test_analyze_populates_from_profile():
    r = make_researcher()
    prof = r.analyze("ethena")
    assert prof.coin_id == "ethena"
    assert prof.symbol == "ENA"
    assert "synthetic dollar" in (prof.description or "")
    assert prof.genesis_date == "2024-02-01"
    assert prof.sentiment["up_pct"] == 65.0
    assert prof.official_links["website"] == "https://ethena.fi"
    assert "CoinGecko" in prof.sources
    assert prof.confidence >= 0.8


def test_scrape_official_site_detects_audit_and_team():
    r = make_researcher()
    html = (
        "<html><body>"
        "Our contracts are audited by CertiK and SlowMist. "
        "We raised $14 million in our Series A backed by top venture firms. "
        "</body></html>"
    )
    r._fetch_html = lambda url, timeout=25: html  # type: ignore[assignment]
    audit_info, team_info = r.scrape_official_site("https://example.com")
    firms = {a["firm"] for a in audit_info}
    assert "CertiK" in firms
    assert "SlowMist" in firms
    assert team_info.get("hits")


def test_scrape_cg_news_parses_links():
    r = make_researcher()
    html = (
        "<html><body>"
        "<a href='/en/coins/btc/news/123'>Bitcoin ETF inflows surge</a>"
        "<a href='/en/coins/btc/news/124'>Miners hold steady</a>"
        "</body></html>"
    )
    r._fetch_html = lambda url, timeout=25: html  # type: ignore[assignment]
    news = r._scrape_cg_news("btc")
    assert len(news) == 2
    assert news[0]["source"] == "CoinGecko News"
    assert news[0]["url"].startswith("https://www.coingecko.com")


def test_analyze_isolation_on_profile_failure():
    class BrokenCG:
        def get_coin_profile(self, coin_id):
            raise RuntimeError("network down")

        def search_coins(self, query):
            return []

    r = TokenWebResearcher(coingecko=BrokenCG(), reddit=FakeReddit())
    prof = r.analyze("ghostcoin")
    assert prof.confidence == 0.1
    assert prof.sources == []
    # no exception propagated


def test_live_get_coin_profile():
    from src.api.coingecko import CoinGeckoClient

    try:
        data = CoinGeckoClient().get_coin_profile("bitcoin")
    except Exception as e:  # network / 429 etc.
        pytest.skip(f"live CoinGecko unavailable: {e}")
    assert data["id"] == "bitcoin"
    assert data["description"]
    assert data["official_links"]["website"]
