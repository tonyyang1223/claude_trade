"""评分与建议服务（薄封装 src.analysis.scorer + advice）。

GET /api/score/{id} 可能触网（CoinGecko/Coinglass/DefiLlama 等）。
失败时返回空结构 + 保留 coinId，不抛异常。
"""
from __future__ import annotations

from typing import Optional

from data.schemas import ScoreResponse


def score(coin_id: str, date: Optional[str] = None) -> ScoreResponse:
    """计算单币综合评分与建议（best-effort）。"""
    try:
        from src.analysis.scorer import Scorer
        from src.analysis import advice as advice_mod

        s = Scorer().score_project(coin_id)

        scores = {
            "market": getattr(s, "market_score", None),
            "technical": getattr(s, "technical_score", None),
            "onchain": getattr(s, "onchain_score", None),
            "sentiment": getattr(s, "sentiment_score", None),
            "github": getattr(s, "github_score", None),
            "social": getattr(s, "social_score", None),
            "risk": getattr(s, "risk_score", None),
        }
        scores = {k: float(v) for k, v in scores.items() if v is not None}

        # 建议：优先用 typed 路径自带字段，否则用 advice 框架重建
        if getattr(s, "action", None):
            advice = {
                "action": s.action,
                "positionRange": getattr(s, "position_range", ""),
                "horizon": "",
                "triggers": getattr(s, "advice_triggers", []) or [],
                "rationale": "",
                "disclaimer": getattr(s, "disclaimer", advice_mod.DISCLAIMER),
            }
        else:
            adv = advice_mod.build_advice(s.rating, s.risk_level, 1.0, profile=None)
            advice = {
                "action": adv.action,
                "positionRange": adv.position_range,
                "horizon": adv.horizon,
                "triggers": adv.triggers,
                "rationale": adv.rationale,
                "disclaimer": adv.disclaimer,
            }

        return ScoreResponse(
            coinId=coin_id,
            name=getattr(s, "coin_name", None),
            symbol=getattr(s, "symbol", None),
            scores=scores,
            totalScore=float(getattr(s, "total_score", 0.0) or 0.0),
            rating=getattr(s, "rating", ""),
            recommendation=getattr(s, "recommendation", ""),
            riskLevel=getattr(s, "risk_level", ""),
            advice=advice,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[score_svc] score 失败 {coin_id}: {exc}")
        return ScoreResponse(coinId=coin_id)
