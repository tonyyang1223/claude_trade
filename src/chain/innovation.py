"""技术创新维度分析。

链上代币的技术创新性难以仅从链上数据判定，采用启发式：
- 类别为 RWA/AI/DePIN/Infrastructure → 叙事具技术/实体重（较高分）
- 合约是否开源验证（is_verified）→ 工程透明度加分
- 标准 ERC-20/SPL 无自定义机制 → 中性；有自定义逻辑（未验证/代理）→ 提示
返回 0-10 并写入证据。
"""
from __future__ import annotations

from typing import List, Optional

from .types import AnalysisResult

from .taxonomy import classify


# 默认叙事基准分（= 现值，作为无 Config 时的回退）
_BASE = {
    "RWA": 8.0, "AI": 8.0, "DePIN": 7.5, "Infrastructure": 8.5,
    "DeFi": 7.0, "GameFi": 6.5, "Meme": 4.0, "Uncategorized": 4.0,
}


def compute_innovation(ctx: AnalysisResult) -> Optional[float]:
    cat = classify(ctx)
    base_table = (ctx.cfg.taxonomy.innovation_base if ctx.cfg is not None else _BASE)
    notes: List[str] = []
    base = base_table.get(cat, 4.0)
    score = base
    notes.append(f"叙事「{cat}」技术含量基准分 {base:.1f}")

    sec = ctx.security
    if sec and sec.is_verified is True:
        notes.append("合约已开源验证，工程透明度高"); score += 1.0
    elif sec and sec.is_verified is False:
        notes.append("合约未开源，机制不可审计"); score -= 1.5

    ctx.notes.setdefault("innovation", notes)
    return round(max(0.0, min(10.0, score)), 1)
