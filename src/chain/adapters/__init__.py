"""链适配器包。

- EVMAdapter：BNB / Robinhood 共用（同为 EVM），仅 RPC/chain_id/浏览器不同
- SolanaAdapter：独立实现（SPL Token）
- get_adapter(chain)：工厂
"""
from .base import ChainAdapter
from .bnb import BnbChainAdapter
from .evm import EVMAdapter
from .robinhood import RobinhoodChainAdapter
from .solana import SolanaAdapter

_REGISTRY = {
    "bnb": BnbChainAdapter,
    "sol": SolanaAdapter,
    "robinhood": RobinhoodChainAdapter,
}


def get_adapter(chain: str, rpc: str | None = None, api_key: str | None = None) -> ChainAdapter:
    cls = _REGISTRY.get(chain.lower())
    if not cls:
        raise ValueError(f"未支持的链适配器: {chain}")
    return cls(rpc=rpc, api_key=api_key)


__all__ = [
    "ChainAdapter", "EVMAdapter", "BnbChainAdapter",
    "RobinhoodChainAdapter", "SolanaAdapter", "get_adapter",
]
