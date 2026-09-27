"""代币与 DeFi 研究服务（薄封装 src.research.token_defi）。

提供：单币代币经济快照、批量解锁抛压画像（竞品对比页可选 enrichment）。
全部 best-effort 容错，失败返回 None / 空列表，不抛异常。
"""
from __future__ import annotations

from typing import Dict, List, Optional


def analyze_token(coin_id: str) -> Optional[dict]:
    """分析单币代币经济/估值（可能触网）。失败返回 None。"""
    try:
        from src.research.token_defi import TokenDefiResearcher

        snap = TokenDefiResearcher().analyze_token(coin_id)
        return snap.to_dict()
    except Exception as exc:  # noqa: BLE001
        print(f"[token_defi_svc] analyze_token 失败 {coin_id}: {exc}")
        return None


def unlock_profiles(coin_ids: List[str]) -> List[dict]:
    """批量解锁抛压画像。失败整体返回空列表。"""
    try:
        from src.research.token_defi import TokenDefiResearcher

        profs = TokenDefiResearcher().unlock_profiles(coin_ids)
        return [p.to_dict() for p in profs]
    except Exception as exc:  # noqa: BLE001
        print(f"[token_defi_svc] unlock_profiles 失败: {exc}")
        return []
