"""情绪维度分析（接入点）。

真实实现需调用 src/api/twitter.py / reddit_free.py（需凭证且触网），
新发 Meme 币情绪主要来自 Twitter / Telegram。当前作为「缺失维度」优雅跳过：
返回 None，评分引擎不计入加权（权重在综合分中归一）。
后续阶段接入：传入 symbol → 社媒提及增长 + 情绪极性 → 0-10 分。
"""
from __future__ import annotations

from typing import Optional

from .types import AnalysisResult


def compute_sentiment(ctx: AnalysisResult) -> Optional[float]:
    # 扩展点：mentions = src.api.reddit_free / twitter.search(ctx.symbol)
    #   增长正向 + 极性正向 → 7-9；负向/骤降 → 2-4
    return None
