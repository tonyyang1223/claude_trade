"""JSON 渲染器：AnalysisResult + Decision → 结构化 JSON 字符串。"""
from __future__ import annotations

import json
from typing import Dict, Optional

from ..types import AnalysisResult


def render_json(result: AnalysisResult, decision: Dict,
                *, indent: int = 2) -> str:
    payload = {
        "analysis": result.model_dump(),
        "decision": decision,
    }
    return json.dumps(payload, ensure_ascii=False, indent=indent)
