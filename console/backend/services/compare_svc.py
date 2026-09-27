"""竞品对比服务（薄封装 src.analysis.comparison）。

POST /api/comparison 可能触网（复用 Scorer 的多维评分）。
失败时返回空结构 + message，不抛异常。
"""
from __future__ import annotations

from typing import List

from data.schemas import ComparisonProject, ComparisonResponse


def compare(coin_ids: List[str]) -> ComparisonResponse:
    """对比多个项目（best-effort）。"""
    if not coin_ids or len(coin_ids) < 2:
        return ComparisonResponse(summary="至少需要 2 个币种进行对比")

    try:
        from src.analysis.comparison import ProjectComparator

        report = ProjectComparator().compare_projects(coin_ids)

        projects = []
        for p in report.projects:
            projects.append(ComparisonProject(
                coin_id=p.coin_id,
                coin_name=getattr(p, "coin_name", None),
                symbol=getattr(p, "symbol", None),
                total_score=getattr(p, "total_score", None),
                rating=getattr(p, "rating", None),
                risk_level=getattr(p, "risk_level", None),
                recommendation=getattr(p, "recommendation", None),
                market_score=getattr(p, "market_score", None),
                technical_score=getattr(p, "technical_score", None),
                onchain_score=getattr(p, "onchain_score", None),
                sentiment_score=getattr(p, "sentiment_score", None),
                github_score=getattr(p, "github_score", None),
                social_score=getattr(p, "social_score", None),
                risk_score=getattr(p, "risk_score", None),
            ).model_dump())

        return ComparisonResponse(
            projects=projects,
            matrix=report.comparison_matrix or {},
            winner=report.winner or "",
            summary=report.analysis_summary or "",
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[compare_svc] compare 失败 {coin_ids}: {exc}")
        return ComparisonResponse(summary=f"对比分析失败：{exc}")
