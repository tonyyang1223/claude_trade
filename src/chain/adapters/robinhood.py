"""Robinhood Chain 适配器（EVM 兼容，Arbitrum Orbit Nitro）。

官方网络参数（2026-09-03 实测确认，非文档猜测）：
- Chain ID: 4663（eth_chainId 实测返回 0x1237 = 4663 ✓）
- 公共 RPC: https://rpc.mainnet.chain.robinhood.com（实测可达，区块高度正常）
- 浏览器:   robinhoodchain.blockscout.com（Blockscout）
- Gas:      ETH（无独立 gas token）
- 主网上线: 2026-07-01

生态背景（影响 Meme 风险判读）：
- 代币创建峰值约 18,600 枚/日；DEX 成交量较 7/12 峰值回落约 72%
- 主导 DEX = Uniswap(v2/v3/v4) + Pleiades；主导稳定币 = USDG(Global Dollar)
- 无原生链代币、无官方空投（任何"官方空投"说法均为骗局）

浏览器 API 注意：Blockscout 的 /api/v2 对非浏览器客户端返回 403，
故开源验证仍不可用；安全证据依赖 eth_getCode 字节码扫描（见 EVMAdapter）。
"""
from __future__ import annotations

from typing import Optional

import yaml

from ..types import Chain
from .evm import EVMAdapter

_ROBINHOOD_CHAIN_ID = 4663
_DEFAULT_RPC = "https://rpc.mainnet.chain.robinhood.com"
_EXPLORER_BASE = "https://robinhoodchain.blockscout.com"


def _load_rh_rpc() -> Optional[str]:
    """settings.yaml 可覆盖默认公共 RPC（自建/专用节点）。"""
    try:
        with open("config/settings.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return (cfg.get("chains", {}).get("robinhood", {}).get("rpc")) or _DEFAULT_RPC
    except Exception:  # noqa: BLE001
        return _DEFAULT_RPC


class RobinhoodChainAdapter(EVMAdapter):
    chain = Chain.ROBINHOOD
    chain_id = _ROBINHOOD_CHAIN_ID
    explorer_api = None  # Blockscout /api/v2 对脚本客户端 403，改走字节码扫描

    def __init__(self, rpc: Optional[str] = None, api_key: Optional[str] = None,
                 timeout: int = 12) -> None:
        super().__init__(rpc=rpc or _load_rh_rpc(), api_key=api_key, timeout=timeout)
