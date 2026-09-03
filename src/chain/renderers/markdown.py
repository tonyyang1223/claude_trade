"""Markdown 渲染器：AnalysisResult + Decision → 对话摘要 / 文本报告。

所有数据来自 result/decision，不含任何引擎逻辑。
"""
from __future__ import annotations

from typing import Dict, Optional

from ..types import AnalysisResult

_DIM_LABEL = {
    "security": "欺诈/安全", "trend": "趋势强弱", "momentum": "多周期动量",
    "liquidity_health": "流动性健康", "sentiment": "社媒情绪",
    "innovation": "技术创新", "taxonomy": "类别清晰", "community": "社区基础",
}


def _usd(v) -> str:
    if v is None:
        return "—"
    if v >= 1e9:
        return f"${v / 1e9:.2f}B"
    if v >= 1e6:
        return f"${v / 1e6:.2f}M"
    if v >= 1e3:
        return f"${v / 1e3:.1f}K"
    return f"${v:,.0f}"


def render_markdown(result: AnalysisResult, decision: Dict,
                    *, title: Optional[str] = None) -> str:
    sym = result.symbol or "—"
    name = result.name or "—"
    chain = result.chain.value.upper()
    total = decision.get("total") or 0.0
    scored = decision.get("scored") or {}
    d = result.dex
    h = result.holders

    rows = []
    if d and d.price_usd is not None:
        q = f"（计价 {d.quote_symbol.upper()}）" if d.quote_symbol else ""
        rows.append(("当前价格", f"${d.price_usd:,.6f}{q}"))
    if d and d.liquidity_usd is not None:
        rows.append(("流动性", _usd(d.liquidity_usd)))
    if d and d.volume_24h is not None:
        rows.append(("24h 成交量", _usd(d.volume_24h)))
    if d and d.price_change_24h is not None:
        rows.append(("24h 涨跌", f"{d.price_change_24h:+.1f}%"))
    if d and d.age_days is not None:
        rows.append(("币龄", f"{d.age_days:.1f} 天"))
    if d and d.buy_sell_ratio is not None:
        rows.append(("买卖比(笔数)", str(d.buy_sell_ratio)))
    if h and h.total_holders is not None:
        rows.append(("持币地址数", f"{h.total_holders:,}"))
    if result.liquidity and result.liquidity.locked_pct is not None:
        rows.append(("LP 锁仓", f"{result.liquidity.locked_pct:.0f}%"))
    meta_rows = "\n".join(f"| {k} | {v} |" for k, v in rows) or "| — | — |"

    dim_lines = []
    for k, label in _DIM_LABEL.items():
        sc = scored.get(k)
        if sc is None:
            dim_lines.append(f"- {label}: _缺失（已排除加权）_")
        else:
            notes = (result.notes.get(k) or [])
            tail = f" — {notes[0]}" if notes else ""
            dim_lines.append(f"- {label}: **{sc:.1f}/10**{tail}")
    dims = "\n".join(dim_lines) or "- _无_"

    flag_lines = "\n".join(f"- {f.msg}" for f in (result.flags or [])) or "- _未发现明显欺诈红旗_"
    miss = decision.get("missing") or []
    miss_txt = f"\n\n> ⚠️ 缺失维度（已排除加权）：{', '.join(miss)}" if miss else ""

    header = title or f"{sym}（{name}）· {chain} 链上代币分析"
    disclaimer = decision.get("disclaimer", "")

    return f"""# {header}

**综合分 {total:.1f}/10** · **{decision.get('decision', '—')}** · 风险 {decision.get('risk', '—')} · 建议仓位 {decision.get('position', '—')}

## 市场数据
| 指标 | 值 |
|------|-----|
{meta_rows}

## 多维评分
{dims}

## 欺诈红旗
{flag_lines}

## 决策与触发条件
{chr(10).join(f'- {t}' for t in (decision.get('triggers') or []))}
{miss_txt}

---
{disclaimer}
"""
