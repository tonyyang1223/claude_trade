"""评分与建议服务（薄封装 src.analysis.scorer + advice）。

GET /api/score/{id} 可能触网（CoinGecko/Coinglass/DefiLlama 等）。
失败时返回空结构 + 保留 coinId，不抛异常。
"""
from __future__ import annotations

from data.schemas import ScoreResponse

# Scorer 的 7 个 legacy 维度（typed 路径的额外维度由 dimension_scores 携带）
_DIMS = ("market", "technical", "onchain", "sentiment", "github", "social", "risk")


def score(coin_id: str) -> ScoreResponse:
    """计算单币综合评分与建议（best-effort）。"""
    try:
        from src.analysis import advice as advice_mod
        from src.analysis.scorer import Scorer

        # Scorer() 无 token_type → 走 legacy 7 维路径（全维恒有值，缺数据以中性 3 兜底）。
        s = Scorer().score_project(coin_id)

        # typed 路径下 *_score 字段会被 core(dim, default=3) 填成 3，直接读属性会把
        # 「无数据」误报为真实评分；dimension_scores 只含真实取到的维度，故优先取它。
        dims = s.dimension_scores or {d: getattr(s, f"{d}_score", None) for d in _DIMS}
        scores = {k: float(v) for k, v in dims.items() if v is not None}

        # coverage 契约（见 advice.apply_coverage_cap）：「已评分维度的权重和」，不是维度
        # 个数占比。按个数折算会高估覆盖率（如 github+social+sentiment 真实 0.30、
        # 按个数 0.43），从而松开评级上限、放大样本不足下的过度自信。权重口径只有
        # 评分器自己知道，故优先复用其算出的 data_coverage；legacy 路径未统计该值，
        # 但 7 维恒有值（权重和=1.0），取 1.0 语义等价。
        coverage = s.data_coverage if s.data_coverage is not None else 1.0
        adv = advice_mod.build_advice(s.rating, s.risk_level, coverage, profile=None)

        return ScoreResponse(
            coinId=coin_id,
            name=getattr(s, "coin_name", None),
            symbol=getattr(s, "symbol", None),
            scores=scores,
            totalScore=float(getattr(s, "total_score", 0.0) or 0.0),
            rating=getattr(s, "rating", "") or "",
            recommendation=getattr(s, "recommendation", "") or "",
            riskLevel=getattr(s, "risk_level", "") or "",
            advice={
                "action": adv.action,
                "positionRange": adv.position_range,
                "horizon": adv.horizon,
                "triggers": adv.triggers,
                "rationale": adv.rationale,
                "disclaimer": adv.disclaimer,
            },
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[score_svc] score 失败 {coin_id}: {exc}")
        return ScoreResponse(coinId=coin_id)
