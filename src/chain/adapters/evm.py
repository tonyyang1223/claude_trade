"""通用 EVM 适配器（BNB / Robinhood 共用）。

通过 JSON-RPC 读取 ERC-20 标准字段（name/symbol/decimals/totalSupply），
通过区块浏览器 API 查合约是否开源验证，通过 owner() 探测是否放弃权限。
网络不可达时各方法返回空模型，由 source 层（DexScreener/GoPlus）降级补充。
"""
from __future__ import annotations

from typing import Optional

import requests

from ..types import (
    Chain,
    ContractSecurity,
    HolderStats,
    LiquidityInfo,
    TokenProfile,
    TokenRef,
)
from .base import ChainAdapter

# ERC-20 标准函数 selector（无需 web3 依赖，手动 ABI 解码）
_SEL = {
    "name": "0x06fdde03",
    "symbol": "0x95d89b41",
    "decimals": "0x313ce567",
    "totalSupply": "0x18160ddd",
    "owner": "0x8da5cb5b",
}

_ZERO_ADDR = "0x0000000000000000000000000000000000000000"

# 危险/特权函数选择器 —— 通过 eth_getCode 扫描字节码，任意 EVM 链通用，
# 不依赖区块浏览器 API、索引器或 GoPlus 覆盖（GoPlus 对新链常不索引）。
# 语义：命中 = 存在该函数；未命中 = 未发现（不等于 100% 不存在，如库函数内部调用）。
_RISK_SELECTORS = {
    # mint(address,uint256) / mint(uint256) / mint(address)
    "mint": ["40c10f19", "a0712d68", "6a627842"],
    # upgradeTo(address) / upgradeToAndCall / implementation() / changeAdmin(address)
    "proxy": ["3659cfe6", "4f1ef286", "5c60da1b", "8f283970"],
    # blacklist(address) / addBlackList(address)
    "blacklist": ["fe575a87", "ec7d41a3"],
    # pause() / unpause()
    "pause": ["8456cb59", "3f4ba83a"],
    # setFeePercent... / excludeFromFee(address)
    "tax": ["f2a7180e", "0a5df6bf"],
}


class EVMAdapter(ChainAdapter):
    # 子类覆盖
    chain_id: int = 0
    explorer_api: Optional[str] = None  # 如 https://api.bscscan.com/api

    # ---------- 解析 ----------
    def resolve(self, query: str) -> TokenRef:
        q = query.strip()
        if q.lower().startswith("0x") and len(q) == 42:
            return TokenRef(chain=self.chain, address=q)
        # 非地址：交给编排层的 DexScreener 符号搜索兜底
        return TokenRef(chain=self.chain, address=q, symbol=q)

    # ---------- 链原生字段 ----------
    def get_token_profile(self, address: str) -> TokenProfile:
        def build():
            name = self._call_str(address, "name")
            sym = self._call_str(address, "symbol")
            dec = self._call_uint(address, "decimals") or 18
            supply = self._call_uint(address, "totalSupply")
            total = (supply / (10 ** dec)) if supply is not None else None
            return TokenProfile(
                chain=self.chain, address=address,
                symbol=sym, name=name, total_supply=total,
            )
        return self._safe(build, TokenProfile(chain=self.chain, address=address))

    def get_contract_security(self, address: str) -> ContractSecurity:
        def build():
            sec = ContractSecurity()
            # 浏览器开源验证
            if self.explorer_api:
                try:
                    r = requests.get(
                        self.explorer_api,
                        params={"module": "contract", "action": "getsourcecode",
                                "address": address, "apikey": self.api_key or ""},
                        timeout=self.timeout,
                    ).json()
                    src = (r.get("result") or [{}])[0]
                    sec.is_verified = bool(src.get("SourceCode") and src.get("ContractName"))
                except Exception:  # noqa: BLE001
                    sec.is_verified = None
            # owner 是否放弃
            owner = self._safe(lambda: self._call_addr(address, "owner"), None)
            sec.has_owner_fn = owner is not None
            if owner is not None:
                sec.owner_renounced = (owner.lower() == _ZERO_ADDR)
            # 字节码特权函数扫描（无浏览器 API 时唯一可用的硬证据）
            code = self._safe(lambda: self._get_code(address), None)
            if code:
                low = code.lower()
                hits = {k: any(s in low for s in sels)
                        for k, sels in _RISK_SELECTORS.items()}
                sec.is_mintable = hits["mint"]
                sec.is_proxy = hits["proxy"]
                sec.can_blacklist = hits["blacklist"]
                sec.can_pause = hits["pause"]
            return sec
        return self._safe(build, ContractSecurity())

    def get_holders(self, address: str) -> HolderStats:
        # EVM 链上持币分布需索引，交给 GoPlus/DexScreener；此处返回空
        return HolderStats()

    def get_liquidity(self, address: str) -> LiquidityInfo:
        return LiquidityInfo()

    # ---------- RPC 辅助 ----------
    def _call(self, address: str, selector: str) -> Optional[str]:
        try:
            hexdata = self._rpc(
                "eth_call",
                [{"to": address, "data": selector}, "latest"],
            )
            return hexdata
        except Exception:  # noqa: BLE001
            return None

    def _call_uint(self, address: str, fn: str) -> Optional[int]:
        h = self._call(address, _SEL[fn])
        if not h or h == "0x":
            return None
        return int(h, 16)

    def _call_str(self, address: str, fn: str) -> Optional[str]:
        h = self._call(address, _SEL[fn])
        if not h or h == "0x":
            return None

        def _decode_string(hexdata: str) -> str:
            b = bytes.fromhex(hexdata[2:])
            if len(b) < 64:
                return ""
            length = int.from_bytes(b[32:64], "big")
            return b[64:64 + length].decode("utf-8", errors="ignore")

        return _decode_string(h) or None

    def _call_addr(self, address: str, fn: str) -> Optional[str]:
        h = self._call(address, _SEL[fn])
        if not h or h == "0x":
            return None
        return "0x" + h[2:][-40:]

    def _get_code(self, address: str) -> Optional[str]:
        """取合约字节码，用于特权函数扫描。"""
        try:
            code = self._rpc("eth_getCode", [address, "latest"])
        except Exception:  # noqa: BLE001
            return None
        return code if code and code not in ("0x", "0X") else None
