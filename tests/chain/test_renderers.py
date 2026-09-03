"""P2 输出渲染层契约测试：html / markdown / json、转义、元数据、配置隔离。"""
from __future__ import annotations

import json

from src.chain.orchestrator import analyze
from src.chain.renderers import render_html, render_json, render_markdown
from src.chain.types import AnalysisResult, Chain


def _decision(total: float = 7.0) -> dict:
    return {
        "decision": "🟡 持有/观察", "risk": "中", "position": "3%-5%",
        "total": total, "scored": {}, "missing": ["sentiment"],
        "triggers": [], "disclaimer": "⚠️ 本分析仅供参考",
    }


class TestMarkdown:
    def test_contains_core_sections(self):
        ctx, dec = analyze("bnb", "CASHCAT", demo=True)
        md = render_markdown(ctx, dec)
        assert ctx.symbol in md
        assert "持有/观察" in md or "综合分" in md
        assert "欺诈红旗" in md
        assert "仅供参考" in md  # 强制免责声明
        assert "综合分" in md


class TestJson:
    def test_parseable_and_no_runtime_cfg(self):
        ctx, dec = analyze("sol", "DEMO", demo=True)
        s = render_json(ctx, dec)
        obj = json.loads(s)
        assert obj["analysis"]["chain"] == "sol"
        assert "cfg" not in obj["analysis"]          # 运行时配置不落盘
        assert obj["decision"]["total"] == dec["total"]
        assert obj["analysis"]["engine_version"]      # 元数据存在
        assert obj["analysis"]["fetched_at"]

    def test_flags_structured_in_dump(self):
        ctx, dec = analyze("bnb", "CASHCAT", demo=True)
        obj = json.loads(render_json(ctx, dec))
        for f in obj["analysis"]["flags"]:
            assert set(f) == {"level", "code", "msg"}


class TestHtml:
    def test_renders_and_escapes_injection(self):
        evil = AnalysisResult(
            chain=Chain.BNB, address="0x" + "4" * 40,
            symbol="<img src=x onerror=alert(1)>", name="<script>alert(1)</script>",
        )
        html = render_html(evil, _decision())
        assert "<script>alert(1)" not in html          # 名称被转义
        assert "&lt;script&gt;" in html
        assert "&lt;img src=x onerror=alert(1)&gt;" in html

    def test_demo_html_ok(self):
        ctx, dec = analyze("robinhood", "RHDEMO", demo=True)
        html = render_html(ctx, dec)
        assert html.startswith("<!DOCTYPE html>")
        assert "综合分" in html or "radar" in html
