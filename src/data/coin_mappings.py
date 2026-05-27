"""Coin ID to trading symbol and GitHub repository mappings.

This module provides mappings from CoinGecko coin IDs to:
- Trading symbols (e.g., 'bitcoin' -> 'BTC/USDT')
- GitHub repositories (e.g., 'bitcoin' -> 'bitcoin/bitcoin')

These mappings are used by the Scorer to fetch data from various sources.
"""

# Mapping from CoinGecko coin_id to exchange trading symbol (Binance format)
COIN_TO_SYMBOL = {
    "bitcoin": "BTC/USDT",
    "ethereum": "ETH/USDT",
    "binancecoin": "BNB/USDT",
    "ripple": "XRP/USDT",
    "cardano": "ADA/USDT",
    "solana": "SOL/USDT",
    "polkadot": "DOT/USDT",
    "dogecoin": "DOGE/USDT",
    "avalanche-2": "AVAX/USDT",
    "chainlink": "LINK/USDT",
    "polygon": "MATIC/USDT",
    "litecoin": "LTC/USDT",
    "uniswap": "UNI/USDT",
    "stellar": "XLM/USDT",
    "cosmos": "ATOM/USDT",
}

# Mapping from CoinGecko coin_id to GitHub repository (owner/repo format)
COIN_TO_REPO = {
    "bitcoin": "bitcoin/bitcoin",
    "ethereum": "ethereum/go-ethereum",
    "cardano": "IntersectMBO/cardano-node",
    "solana": "solana-labs/solana",
    "polkadot": "paritytech/polkadot-sdk",
    "chainlink": "smartcontractkit/chainlink",
    "uniswap": "Uniswap/v4-core",
    "cosmos": "cosmos/cosmos-sdk",
    "stellar": "stellar/stellar-core",
    "polygon": "maticnetwork/matic",
    "avalanche-2": "ava-labs/avalanchego",
    "dogecoin": "dogecoin/dogecoin",
    "litecoin": "litecoin-project/litecoin",
}