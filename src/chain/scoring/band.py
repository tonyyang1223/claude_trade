"""阈值打分器（band）。

把散落的 `if/elif` 阈值链收敛为可测试、可配置的数据表。
claude_trading 既有 tokenomics._band 的上位公共版本，全链上五维统一复用。
"""
from typing import Optional, Sequence, Tuple


def band(
    value: Optional[float],
    bands: Sequence[Tuple[float, int]],
    *,
    ascending: bool = True,
    default: Optional[int] = None,
) -> Optional[int]:
    """把连续值映射到离散分（通常 0-10）。

    bands: [(阈值, 分数), ...] 升序排列。
    - ascending=True  （默认）：值 <= 阈值 即落入该档（用于「越低越好」，如税率/集中度）
    - ascending=False：值 >= 阈值 即落入该档（用于「越高越好」，如流动性/持币数）

    例：税率越低越安全
        band(buy_tax, [(0,10),(5,7),(10,4),(20,1)], ascending=True)
        buy_tax=3 -> 7 分；buy_tax=15 -> 4 分

    返回 None 表示输入缺失，由评分引擎跳过（不计入加权）。
    """
    if value is None:
        return default
    if not bands:
        return default
    for threshold, score in bands:
        hit = (value <= threshold) if ascending else (value >= threshold)
        if hit:
            return score
    # 超出所有阈值：取最后一档
    return bands[-1][1]
