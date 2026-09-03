"""链上新发代币分析子系统。

输入「链 + 代币符号」或「链地址」，自动完成：
  适配器解析 → 数据源抓取 → 多维分析（欺诈/趋势/动量/流动性/情绪/创新/类别/社区）
  → 评分 → 决策建议 → 渲染报告（html/md/json）。

配置化：analyze(..., config=...) 支持 dict / YAML / AnalysisConfig；
默认配置见 config.py（内嵌现值），所有影响结论的阈值/权重/档位均可覆盖。

设计见 docs/chain_token_analysis/skill_design.md。
"""
from __future__ import annotations

from .config import AnalysisConfig, ENGINE_VERSION
from .orchestrator import analyze
from .renderers import render_html, render_json, render_markdown
from .types import Chain, TokenRef

__version__ = ENGINE_VERSION

__all__ = [
    "analyze", "Chain", "TokenRef", "AnalysisConfig", "ENGINE_VERSION",
    "render_html", "render_json", "render_markdown",
]
