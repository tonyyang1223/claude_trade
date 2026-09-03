"""社区基础维度（Meme 专项，弱信号）。

仅用 DexScreener 已暴露的官方渠道（Twitter/Telegram/网站等）数量做**弱**信号：
官方渠道越齐全，rug 后"找不到人"的成本越高，是 Meme 少有的可量化透明度指标。
注意：这只是「存在渠道」，不等于「渠道活跃/真实」，故上限不高（约 6.5），
真实社媒情绪仍需 Twitter/Reddit 凭证（后续接入 src/api/）。
"""
from __future__ import annotations

from typing import List, Optional

from .types import AnalysisResult


def compute_community(ctx: AnalysisResult) -> Optional[float]:
    dex = ctx.dex
    socials = dex.socials if dex else None
    if not socials:
        return None
    notes: List[str] = []
    score = 5.0
    n = len(socials)
    if n >= 2:
        notes.append(f"有 {n} 个官方社媒/渠道（{', '.join(socials[:3])}）"); score += 1.5
    elif n == 1:
        notes.append(f"仅有 1 个社媒渠道：{socials[0]}"); score += 0.5
    ctx.notes.setdefault("community", notes)
    return round(max(0.0, min(10.0, score)), 1)
