"""类别维度分析（叙事识别）。

链上代币无 CoinGecko 分类，用符号/名称关键词匹配主流叙事。词表与分值表
从 ctx.cfg.taxonomy（TaxonomyConfig）读取；未挂配置时回落模块内默认。
返回 0-10「类别可识别度」分，并把识别结果写入 ctx.notes["taxonomy"]。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .types import AnalysisResult

# 默认叙事词表（= 现值，作为无 Config 时的回退）
_NARRATIVES = {
    "RWA": ["rwa", "realworld", "stock", "equity", "treasury", "gold", "美股", "股票"],
    "AI": ["ai", "agent", "gpt", "neural", "mind", "bot", "智能体", "人工"],
    "DePIN": ["depin", "infra", "node", "wireless", "compute", "基建"],
    "GameFi": ["game", "meta", "play", "nft", "pixel", "游戏"],
    "DeFi": ["swap", "farm", "yield", "lend", "vault", "dex", "流动性"],
    "Meme": [
        "pepe", "doge", "cat", "inu", "moon", "chad", "wojak", "cashcat",
        "shiba", "floki", "elon", "马斯克",
        # 中文动物/吉祥物（生肖 + 常见 Meme 意象）
        "牛", "bull", "龙", "dragon", "狗", "dog", "猫", "蛙", "frog",
        "兔", "猪", "蛇", "马", "虎", "羊", "猴", "鼠", "熊", "bear",
        "柴", "熊猫", "panda", "蟹", "鱼", "鸟", "鸡",
    ],
    "Infrastructure": ["bridge", "layer", "rollup", "chain", "orbit", "跨链"],
}

# 叙事清晰度默认分值表
_CLARITY = {
    "RWA": 9.0, "AI": 8.5, "DePIN": 8.0, "Infrastructure": 8.5,
    "DeFi": 7.5, "GameFi": 6.5, "Meme": 5.0, "Uncategorized": 3.0,
}


def _narratives(ctx: AnalysisResult) -> Dict[str, List[str]]:
    if ctx.cfg is not None:
        return ctx.cfg.taxonomy.narratives
    return _NARRATIVES


def classify(ctx: AnalysisResult) -> str:
    # 名称可能位于顶层 symbol/name 或 profile（地址查询时），两者都看
    sym = (ctx.symbol or (ctx.profile.symbol if ctx.profile else "")) or ""
    nm = (ctx.name or (ctx.profile.name if ctx.profile else "")) or ""
    text = f"{sym} {nm}".lower()
    narr = _narratives(ctx)
    # 优先精确命中（避免 moon/cat 误判 AI）
    hits = {n: sum(k in text for k in kws) for n, kws in narr.items()}
    best = max(hits, key=hits.get)
    return best if hits[best] > 0 else "Uncategorized"


def _clarity(ctx: AnalysisResult) -> Dict[str, float]:
    if ctx.cfg is not None:
        return ctx.cfg.taxonomy.clarity
    return _CLARITY


def compute_taxonomy(ctx: AnalysisResult) -> Optional[float]:
    cat = classify(ctx)
    ctx.notes.setdefault("taxonomy", [f"识别类别：{cat}"])
    return _clarity(ctx).get(cat, 5.0)
