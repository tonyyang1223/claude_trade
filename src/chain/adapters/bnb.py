"""BNB Chain 适配器（EVM 兼容，chain_id=56）。

默认使用公共 RPC 与 BSCScan 浏览器 API。API key 从 config/settings.yaml 读取
（api_keys.bscscan），缺失时开源验证降级为 None。
"""
from __future__ import annotations

from typing import Optional

from ..types import Chain
from .evm import EVMAdapter

_BSC_RPC = "https://bsc-dataseed.binance.org/"
_BSC_EXPLORER = "https://api.bscscan.com/api"


class BnbChainAdapter(EVMAdapter):
    chain = Chain.BNB
    chain_id = 56
    explorer_api = _BSC_EXPLORER

    def __init__(self, rpc: Optional[str] = None, api_key: Optional[str] = None,
                 timeout: int = 12) -> None:
        super().__init__(rpc=rpc or _BSC_RPC, api_key=api_key, timeout=timeout)
