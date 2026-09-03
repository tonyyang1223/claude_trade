"""通用加权器（全仓唯一一份加权逻辑，对应 ADR-002）。

三条历史路径（legacy/typed/phase1）收敛为同一个 score()：
- 缺失维度显式跳过（score 返回 None 即不计入加权），绝不填 3
- 权重来自注册表或外部 profile（类别决定权重配置）
- 输出 0-10 综合分 + 各维度分 + 缺失清单
"""
from __future__ import annotations

from typing import Optional

from ..types import AnalysisResult
from .dimension import DimensionRegistry


def score(
    registry: DimensionRegistry,
    ctx: AnalysisResult,
    profile_weights: Optional[dict[str, float]] = None,
) -> tuple[float, dict[str, float], list[str]]:
    """对 ctx 跑全部维度，返回 (综合分 0-10, 各维度分, 缺失维度名)。"""
    scored: dict[str, float] = {}
    missing: list[str] = []
    for d in registry.all():
        raw = d.compute(ctx)
        if raw is None:
            missing.append(d.name)
            continue
        scored[d.name] = float(raw)

    weights = profile_weights or registry.weights()
    # 仅对「实际计分且有权重」的维度加权；缺失维度已排除，按剩余权重归一。
    # 各维度分均为 0-10、权重和为 1.0，加权均值本身即 0-10 尺度，无需再乘 10。
    active = {n: w for n, w in weights.items() if n in scored}
    w_sum = sum(active.values())
    if not w_sum:
        return 0.0, scored, missing
    total = sum(weights[n] * s for n, s in scored.items() if n in weights) / w_sum
    return round(total, 2), scored, missing
