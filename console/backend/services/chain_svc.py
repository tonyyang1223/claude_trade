"""链上分析服务（薄封装 src.chain.orchestrator.analyze）。

GET /api/onchain?chain=&query= 可能触网（RPC/DexScreener/GoPlus）或走 demo 模式。
失败时返回空结构 + message，不抛异常。
"""
from __future__ import annotations

from data.schemas import OnchainResponse


def analyze(chain: str, query: str, demo: bool = False) -> OnchainResponse:
    """分析某链上代币，返回 OnchainResponse（best-effort）。"""
    try:
        from src.chain.orchestrator import analyze as chain_analyze

        result, decision = chain_analyze(chain, query or "", demo=demo)

        scored = decision.get("scored") or {}
        dims = {k: float(v) for k, v in scored.items() if v is not None}

        flags = []
        for f in (getattr(result, "flags", None) or []):
            if hasattr(f, "model_dump"):
                flags.append(f.model_dump())
            elif isinstance(f, dict):
                flags.append(f)
            else:
                flags.append({"level": "warn", "code": "unknown", "msg": str(f)})

        chain_val = getattr(result.chain, "value", None) or str(getattr(result.chain, "", "")) or chain
        address = getattr(result, "address", "") or query or ""

        return OnchainResponse(
            chain=str(chain_val),
            address=address,
            symbol=result.symbol,
            name=result.name,
            dims=dims,
            total=float(decision.get("total", 0.0) or 0.0),
            decision=decision.get("decision", ""),
            risk=decision.get("risk", ""),
            position=decision.get("position", ""),
            triggers=decision.get("triggers", []) or [],
            missing=decision.get("missing", []) or [],
            flags=flags,
            disclaimer=decision.get("disclaimer", ""),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[chain_svc] analyze 失败 chain={chain} query={query}: {exc}")
        return OnchainResponse(
            chain=chain,
            address=query or "",
            disclaimer="链上分析暂不可用，可能为网络受限或地址无法解析。",
        )
