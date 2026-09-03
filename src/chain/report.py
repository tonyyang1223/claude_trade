"""兼容层：历史 import `from src.chain.report import render_html` 继续可用。

新代码请从 `src.chain.renderers` 导入（html / markdown / json 三渲染器）。
"""
from __future__ import annotations

from .renderers.html import render_html
from .renderers.json import render_json
from .renderers.markdown import render_markdown

__all__ = ["render_html", "render_json", "render_markdown"]
