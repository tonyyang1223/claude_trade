"""评分引擎：维度注册表 + band 阈值打分器 + 通用加权器。

对应架构评审 ADR-002 的落地。维度即数据对象，新增维度只需 register，
不动流水线；缺失维度由 score() 显式跳过（绝不填 3）。
"""
from .band import band
from .dimension import Context, Dimension, DimensionRegistry
from .pipeline import score

__all__ = ["band", "Context", "Dimension", "DimensionRegistry", "score"]
