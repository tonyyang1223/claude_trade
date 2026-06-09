"""Coin ID to trading symbol and GitHub repository mappings.

This module provides mappings from CoinGecko coin IDs to:
- Trading symbols (e.g., 'bitcoin' -> 'BTC/USDT')
- GitHub repositories (e.g., 'bitcoin' -> 'bitcoin/bitcoin')
- DefiLlama protocol slugs (e.g., 'uniswap' -> 'uniswap')

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
    # Phase 1: Additional mappings
    "aave": "AAVE/USDT",
    "compound": "COMP/USDT",
    "makerdao": "MKR/USDT",
    "curve": "CRV/USDT",
    "lido": "LDO/USDT",
    "rocket-pool": "RPL/USDT",
    "arbitrum": "ARB/USDT",
    "optimism": "OP/USDT",
    "the-open-network": "TON/USDT",
    "near": "NEAR/USDT",
    "flow": "FLOW/USDT",
    "tezos": "XTZ/USDT",
    "theta": "THETA/USDT",
    "filecoin": "FIL/USDT",
    "internet-computer": "ICP/USDT",
    "hedera-hashgraph": "HBAR/USDT",
    "elrond-erd-2": "EGLD/USDT",
    "thorchain": "RUNE/USDT",
    "fantom": "FTM/USDT",
    "kava": "KAVA/USDT",
    "harmony": "ONE/USDT",
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
    # Phase 1: Additional DeFi protocol repos
    "aave": "aave/aave-v3-core",
    "compound": "compound-finance/compound-protocol",
    "makerdao": "makerdao/dss",
    "curve": "curvefi/curve-contract",
    "lido": "lidofinance/lido-dapp",
    "rocket-pool": "rocket-pool/rocketpool",
    "near": "near/nearcore",
    "fantom": "Fantom-foundation/fantom-go",
    "arbitrum": "OffchainLabs/nitro",
    "optimism": "ethereum-optimism/optimism",
}

# Mapping from CoinGecko coin_id to DefiLlama protocol slug (Phase 1)
COIN_TO_DEFILLAMA = {
    "uniswap": "uniswap",
    "aave": "aave",
    "compound": "compound-finance",
    "makerdao": "makerdao",
    "curve": "curve-dex",
    "lido": "lido",
    "rocket-pool": "rocket-pool",
    # Ecosystem/Chain mappings
    "ethereum": "ethereum",
    "solana": "solana",
    "avalanche-2": "avalanche",
    "polygon": "polygon",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "cosmos": "cosmos",
    "fantom": "fantom",
    "binancecoin": "bsc",
    "cardano": "cardano",
}

# Mapping from CoinGecko coin_id to chain name for stablecoin flows
COIN_TO_CHAIN = {
    # Layer 1 链原生代币
    "ethereum": "Ethereum",
    "solana": "Solana",
    "avalanche-2": "Avalanche",
    "polygon": "Polygon",
    "binancecoin": "BSC",
    "arbitrum": "Arbitrum",
    "optimism": "Optimism",
    "cosmos": "Cosmos",
    "fantom": "Fantom",
    "cardano": "Cardano",
    "polkadot": "Polkadot",
    "near": "Near",
    "litecoin": "Litecoin",
    "dogecoin": "Dogecoin",
    # ERC-20 代币（Ethereum 链）
    "uniswap": "Ethereum",
    "aave": "Ethereum",
    "compound": "Ethereum",
    "makerdao": "Ethereum",
    "curve": "Ethereum",
    "lido": "Ethereum",
    "chainlink": "Ethereum",
    "rocket-pool": "Ethereum",
}

# Mapping from chain name to DefiLlama chain identifier
CHAIN_TO_DEFILLAMA = {
    "Ethereum": "Ethereum",
    "Solana": "Solana",
    "Avalanche": "Avalanche",
    "Polygon": "Polygon",
    "BSC": "BSC",
    "Arbitrum": "Arbitrum",
    "Optimism": "Optimism",
    "Cosmos": "Cosmos",
    "Fantom": "Fantom",
    "Cardano": "Cardano",
    "Polkadot": "Polkadot",
    "Near": "Near",
    "Litecoin": "Litecoin",
    "Dogecoin": "Dogecoin",
}