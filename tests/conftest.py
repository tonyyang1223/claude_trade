"""Shared pytest fixtures and mock data generators."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List


@pytest.fixture
def mock_coingecko_response() -> Dict[str, Any]:
    """Generate mock CoinGecko API response."""
    return {
        'id': 'bitcoin',
        'symbol': 'btc',
        'name': 'Bitcoin',
        'current_price': 45000.00,
        'market_cap': 850000000000,
        'market_cap_rank': 1,
        'total_volume': 25000000000,
        'price_change_24h': 1200.50,
        'price_change_percentage_24h': 2.74,
        'circulating_supply': 18800000,
        'total_supply': 21000000,
        'ath': 69000.00,
        'atl': 67.81,
        'last_updated': datetime.now().isoformat()
    }


@pytest.fixture
def mock_coinglass_response() -> Dict[str, Any]:
    """Generate mock CoinGlass API response for funding rate."""
    return {
        'symbol': 'BTC',
        'fundingRate': 0.0001,
        'fundingTime': int(datetime.now().timestamp() * 1000),
        'exchange': 'binance'
    }


@pytest.fixture
def mock_defillama_response() -> Dict[str, Any]:
    """Generate mock DefiLlama API response for TVL."""
    return {
        'chain': 'Ethereum',
        'tvl': 50000000000,
        'chainId': 'ethereum',
        'name': 'Ethereum',
        'tokenSymbol': 'ETH'
    }


@pytest.fixture
def mock_github_response() -> Dict[str, Any]:
    """Generate mock GitHub API response."""
    return {
        'id': 123456,
        'name': 'bitcoin',
        'full_name': 'bitcoin/bitcoin',
        'stargazers_count': 70000,
        'forks_count': 35000,
        'open_issues_count': 500,
        'watchers_count': 3500,
        'pushed_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }


@pytest.fixture
def mock_reddit_response() -> Dict[str, Any]:
    """Generate mock Reddit API response."""
    return {
        'kind': 'listing',
        'data': {
            'children': [
                {
                    'data': {
                        'subreddit': 'bitcoin',
                        'title': 'Bitcoin price discussion',
                        'score': 500,
                        'num_comments': 150,
                        'created_utc': datetime.now().timestamp()
                    }
                }
                for _ in range(10)
            ]
        }
    }


@pytest.fixture
def sample_factor_data() -> pd.DataFrame:
    """Generate sample factor data with 16 factors for 30 days."""
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')

    # 16 factors based on spec
    factors = {
        'funding_rate': np.random.uniform(-0.001, 0.001, 30),
        'open_interest': np.random.uniform(1e9, 5e9, 30),
        'tvl_change_7d': np.random.uniform(-10, 10, 30),
        'stablecoin_flow': np.random.uniform(-1e8, 1e8, 30),
        'github_commits': np.random.randint(10, 100, 30),
        'github_stars': np.random.randint(1000, 100000, 30),
        'reddit_mentions': np.random.randint(50, 500, 30),
        'reddit_sentiment': np.random.uniform(-1, 1, 30),
        'twitter_mentions': np.random.randint(100, 1000, 30),
        'price_momentum_7d': np.random.uniform(-15, 15, 30),
        'price_momentum_30d': np.random.uniform(-30, 30, 30),
        'volume_ratio': np.random.uniform(0.5, 2.0, 30),
        'btc_dominance_change': np.random.uniform(-2, 2, 30),
        'exchange_inflow': np.random.uniform(1000, 10000, 30),
        'exchange_outflow': np.random.uniform(1000, 10000, 30),
        'whale_activity': np.random.randint(0, 20, 30)
    }

    df = pd.DataFrame(factors, index=dates)
    df.index.name = 'date'
    return df


@pytest.fixture
def mock_all_api_responses(
    mock_coingecko_response,
    mock_coinglass_response,
    mock_defillama_response,
    mock_github_response,
    mock_reddit_response
) -> Dict[str, Dict[str, Any]]:
    """Combine all mock API responses."""
    return {
        'coingecko': mock_coingecko_response,
        'coinglass': mock_coinglass_response,
        'defillama': mock_defillama_response,
        'github': mock_github_response,
        'reddit': mock_reddit_response
    }


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory structure."""
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    raw_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary config file."""
    config_content = """
data:
  raw_dir: data/raw
  processed_dir: data/processed

collection:
  retry_attempts: 3
  retry_delay: 1

whale_monitor:
  enabled: true
  thresholds:
    btc: 100
    eth: 1000
  check_interval: 600
"""
    config_file = tmp_path / "settings.yaml"
    config_file.write_text(config_content)
    return config_file
