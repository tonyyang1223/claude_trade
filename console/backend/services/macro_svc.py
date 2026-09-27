"""宏观 BTC 占比服务（薄封装 src.analysis.btc_dominance）。

GET /api/macro/btc-dominance 可能触网（CoinGecko global）。
失败时返回空结构，不抛异常。
"""
from __future__ import annotations

from data.schemas import MacroResponse


def btc_dominance() -> MacroResponse:
    """获取 BTC  dominance 与市场规模判断（best-effort）。"""
    try:
        from src.analysis.btc_dominance import BTCDominanceAnalyzer

        d = BTCDominanceAnalyzer().analyze()
        return MacroResponse(
            currentDominance=float(getattr(d, "current_dominance", 0.0) or 0.0),
            trend=getattr(d, "trend", "") or "",
            marketPhase=getattr(d, "market_phase", "") or "",
            altcoinSeason=bool(getattr(d, "altcoin_season", False)),
            recommendation=getattr(d, "recommendation", "") or "",
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[macro_svc] btc_dominance 失败: {exc}")
        return MacroResponse()
