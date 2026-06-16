"""Configuration loader for API credentials and settings.

Loads from multiple sources in priority order:
1. Environment variables (highest priority)
2. settings.yaml file
3. settings.example.yaml defaults
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def load_settings(settings_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load settings from YAML file.

    Args:
        settings_path: Path to settings.yaml (default: config/settings.yaml)

    Returns:
        Dictionary with all settings
    """
    if settings_path is None:
        settings_path = Path("config/settings.yaml")

    # Try to load settings.yaml
    if settings_path.exists():
        with open(settings_path, 'r') as f:
            return yaml.safe_load(f) or {}

    # Fall back to example
    example_path = Path("config/settings.example.yaml")
    if example_path.exists():
        with open(example_path, 'r') as f:
            return yaml.safe_load(f) or {}

    return {}


def get_reddit_credentials() -> Dict[str, str]:
    """Get Reddit API credentials from env or config.

    Priority:
    1. REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET env vars
    2. config/settings.yaml social_apis.reddit section

    Returns:
        Dictionary with client_id, client_secret, user_agent
    """
    # Check environment variables first
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")

    # If not in env, check config file
    if not client_id or not client_secret:
        settings = load_settings()
        reddit_config = settings.get("social_apis", {}).get("reddit", {})

        if not client_id:
            client_id = reddit_config.get("client_id")
        if not client_secret:
            client_secret = reddit_config.get("client_secret")

    return {
        "client_id": client_id or "",
        "client_secret": client_secret or "",
        "user_agent": os.getenv("REDDIT_USER_AGENT") or "claude_trade:v1.0"
    }


def get_cryptocompare_key() -> str:
    """Get CryptoCompare API key from env or config."""
    key = os.getenv("CRYPTOCOMPARE_API_KEY")
    if not key:
        settings = load_settings()
        key = settings.get("social_apis", {}).get("cryptocompare", {}).get("api_key", "")
    return key or ""


def get_coinmarketcap_key() -> str:
    """Get CoinMarketCap API key from env or config."""
    key = os.getenv("COINMARKETCAP_API_KEY")
    if not key:
        settings = load_settings()
        key = settings.get("social_apis", {}).get("coinmarketcap", {}).get("api_key", "")
    return key or ""


def get_binance_credentials() -> Dict[str, str]:
    """Get Binance API credentials from env or config."""
    settings = load_settings()

    return {
        "api_key": os.getenv("BINANCE_API_KEY") or
                   settings.get("exchange", {}).get("binance", {}).get("api_key", ""),
        "api_secret": os.getenv("BINANCE_API_SECRET") or
                      settings.get("exchange", {}).get("binance", {}).get("api_secret", ""),
        "testnet": settings.get("exchange", {}).get("binance", {}).get("testnet", True)
    }