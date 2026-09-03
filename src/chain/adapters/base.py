"""链适配器抽象基类。

定义「链原生能拿到的数据」接口。注意职责边界：
- 适配器 = 链原生 RPC / 区块浏览器（无需第三方）
- 第三方聚合（DEX 价格、GoPlus 安全）在 src/chain/sources/*

任意方法失败都不抛异常，返回对应模型（字段全 None），由编排层聚合与降级。
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Optional

import requests

from ..types import (
    Chain,
    ContractSecurity,
    HolderStats,
    LiquidityInfo,
    TokenProfile,
    TokenRef,
)


class ChainAdapter(ABC):
    chain: Chain

    def __init__(self, rpc: Optional[str] = None, api_key: Optional[str] = None,
                 timeout: int = 12) -> None:
        self.rpc = rpc
        self.api_key = api_key
        self.timeout = timeout

    # ---- 子类必须实现 ----
    @abstractmethod
    def resolve(self, query: str) -> TokenRef:
        """query 可以是地址或符号，返回链上 TokenRef。"""

    @abstractmethod
    def get_token_profile(self, address: str) -> TokenProfile:
        """名称/符号/总量等链原生字段。"""

    @abstractmethod
    def get_contract_security(self, address: str) -> ContractSecurity:
        """合约开源状态、owner 放弃、可否 mint 等。"""

    @abstractmethod
    def get_holders(self, address: str) -> HolderStats:
        """持币分布（链原生可达时）。"""

    @abstractmethod
    def get_liquidity(self, address: str) -> LiquidityInfo:
        """流动性/LP 锁仓（链原生可达时）。"""

    # ---- 通用工具 ----
    def _safe(self, fn, default):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - 适配器层永不向外抛
            return default

    def _rpc(self, method: str, params: list, result_key: str = "result") -> Any:
        """通用 JSON-RPC 调用（EVM / Solana 风格统一）。失败抛 RuntimeError。"""
        if not self.rpc:
            raise RuntimeError("未配置 RPC 端点")
        resp = requests.post(
            self.rpc,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        if "error" in payload:
            raise RuntimeError(f"RPC error: {payload['error']}")
        return payload.get(result_key)

    @staticmethod
    def _now_iso() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
