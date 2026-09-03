"""输出渲染层（设计文档 §4 L4）：只消费 AnalysisResult + Decision，永不触碰引擎。

- html.py     : render_html  （自包含深色报告）
- markdown.py : render_markdown（对话/文本摘要）
- json.py     : render_json   （结构化数据）
"""
from .html import render_html
from .json import render_json
from .markdown import render_markdown

__all__ = ["render_html", "render_json", "render_markdown"]
