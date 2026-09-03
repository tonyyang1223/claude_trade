"""Solana 适配器（独立实现，非 EVM，SPL Token 标准）。

通过 Solana JSON-RPC 读取：
- getTokenSupply：总量/精度
- getTokenLargestAccounts：持币分布（top accounts）
- getAccountInfo（可选）：metadata
安全维度走 RugCheck 专用 API；价格/流动性走 DexScreener（source 层）。
网络不可达时返回空模型，由编排层降级。
"""
from __future__ import annotations

import re

from ..types import (
    Chain,
    ContractSecurity,
    HolderStats,
    LiquidityInfo,
    TokenProfile,
    TokenRef,
)
from .base import ChainAdapter

_SOL_RPC = "https://api.mainnet-beta.solana.com"
_RUGCHECK = "https://api.rugcheck.xyz/v1/tokens/{mint}/report/summary"
_B58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class SolanaAdapter(ChainAdapter):
    chain = Chain.SOL

    def __init__(self, rpc: str | None = None, api_key: str | None = None, timeout: int = 12) -> None:
        super().__init__(rpc=rpc or _SOL_RPC, api_key=api_key, timeout=timeout)

    # ---------- 解析 ----------
    def resolve(self, query: str) -> TokenRef:
        q = query.strip()
        if _B58.match(q):
            return TokenRef(chain=self.chain, address=q)
        return TokenRef(chain=self.chain, address=q, symbol=q)

    # ---------- 链原生字段 ----------
    def get_token_profile(self, address: str) -> TokenProfile:
        def build():
            res = self._rpc("getTokenSupply", [address])
            val = (res or {}).get("value") or {}
            amt = int(val.get("amount") or 0)
            dec = int(val.get("decimals") or 0)
            total = amt / (10 ** dec) if dec else amt
            return TokenProfile(chain=self.chain, address=address, total_supply=total)
        return self._safe(build, TokenProfile(chain=self.chain, address=address))

    def get_contract_security(self, address: str) -> ContractSecurity:
        def build():
            r = self._http_get(_RUGCHECK.format(mint=address))
            if not r:
                return ContractSecurity()
            risks = r.get("risks") or []
            score = r.get("score") or 0
            # RugCheck 风险项转红旗（score 越高越危险，这里仅记录存在）
            flags = [x.get("name") for x in risks if x.get("level") in ("warn", "danger")]
            return ContractSecurity(
                is_in_blacklist=bool(r.get("risks") and any(
                    x.get("name", "").lower().startswith("frozen") for x in risks)),
            )
        return self._safe(build, ContractSecurity())

    def get_holders(self, address: str) -> HolderStats:
        def build():
            res = self._rpc("getTokenLargestAccounts", [address])
            accts = (res or {}).get("value") or []
            if not accts:
                return HolderStats()
            top10 = sum(int(a.get("uiAmount") or 0) for a in accts[:10])
            return HolderStats(
                total_holders=None,
                top10_pct=None,  # 需总量归一，编排层算
                creator_pct=None,
                snipe_pct=None,
            )
        return self._safe(build, HolderStats())

    def get_liquidity(self, address: str) -> LiquidityInfo:
        return LiquidityInfo()

    # ---------- 辅助 ----------
    def _http_get(self, url: str):
        import requests
        try:
            return requests.get(url, timeout=self.timeout).json()
        except Exception:  # noqa: BLE001
            return None
