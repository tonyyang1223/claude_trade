"""维度注册表与维度数据对象。

维度是纯声明：name + weight + compute(返回 0-10 分或 None)。
新增一个分析维度 = 注册一个 Dimension，不改变 score() 流水线，
也不改变其他维度 —— 这是 ADR-002「维度注册表」的核心。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence

from ..types import AnalysisResult


# compute 接收 AnalysisResult，返回 0-10 分或 None（缺失）
ComputeFn = Callable[[AnalysisResult], Optional[float]]


@dataclass(frozen=True)
class Dimension:
    name: str
    weight: float
    compute: ComputeFn
    bands: Optional[Sequence[tuple[float, int]]] = None  # 预留：部分维度可用 band 派生
    desc: str = ""


class DimensionRegistry:
    def __init__(self) -> None:
        self._dims: dict[str, Dimension] = {}

    def register(self, d: Dimension) -> Dimension:
        if d.weight < 0:
            raise ValueError(f"权重必须 >=0: {d.name}")
        self._dims[d.name] = d
        return d

    def get(self, name: str) -> Optional[Dimension]:
        return self._dims.get(name)

    def all(self) -> list[Dimension]:
        return list(self._dims.values())

    def weights(self) -> dict[str, float]:
        return {d.name: d.weight for d in self._dims.values()}

    def names(self) -> list[str]:
        return list(self._dims.keys())


# 兼容类型注解：Context 即完整分析结果
Context = AnalysisResult
