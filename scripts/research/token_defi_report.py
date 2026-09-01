#!/usr/bin/env python3
"""Generate token & DeFi protocol research reports.

Provides three report modes backed by :mod:`src.research.token_defi`:

1. ``--token``    : 单/多代币研究（代币经济、估值、涨跌）
2. ``--compare``  : DeFi 协议对比（TVL、费用、P/S、资本效率）
3. ``--unlock``   : 解锁抛压分析（流通率、稀释倍数、风险分档）

输出遵循项目约定：Plotly 交互式 HTML（或 JSON），落盘到 ``reports/``。

Examples:
    # 单个代币研究
    python scripts/research/token_defi_report.py --token ethena

    # 协议对比（slug[:coin_id]）
    python scripts/research/token_defi_report.py --compare uniswap:uniswap curve-dex:curve-dao-token

    # 解锁抛压
    python scripts/research/token_defi_report.py --unlock arbitrum ethena uniswap curve-dao-token
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import plotly.graph_objects as go

from src.research.token_defi import (
    ProtocolSnapshot,
    TokenDefiResearcher,
    TokenSnapshot,
    UnlockProfile,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = project_root / "reports"

# 深色科技风配色（与项目看板视觉一致）
COLORS = {
    "bg": "#0b1020",
    "panel": "#121a30",
    "text": "#e6ecf7",
    "muted": "#8ea0c0",
    "blue": "#4d7cff",
    "cyan": "#35e0e6",
    "purple": "#a978ff",
    "green": "#3ad29f",
    "red": "#ff6b81",
    "amber": "#ffcb6b",
}

DISCLAIMER = (
    "风险提示：以上内容仅为基于公开数据的研究框架与信息整理，不构成任何投资建议。"
    "加密货币波动剧烈、存在归零与监管风险，请独立判断并自担风险。"
)


# --------------------------------------------------------------------------
# 格式化工具
# --------------------------------------------------------------------------

def fmt_usd(value: Optional[float]) -> str:
    """将金额格式化为 B/M/K 简写。

    Args:
        value: 金额（USD）

    Returns:
        格式化字符串；None 时返回 'N/A'
    """
    if value is None:
        return "N/A"
    abs_value = abs(value)
    if abs_value >= 1e9:
        return f"${value / 1e9:,.2f}B"
    if abs_value >= 1e6:
        return f"${value / 1e6:,.2f}M"
    if abs_value >= 1e3:
        return f"${value / 1e3:,.1f}K"
    return f"${value:,.2f}"


def fmt_num(value: Optional[float]) -> str:
    """将代币数量格式化为 B/M 简写。

    Args:
        value: 代币数量

    Returns:
        格式化字符串；None 时返回 'N/A'
    """
    if value is None:
        return "N/A"
    if abs(value) >= 1e9:
        return f"{value / 1e9:,.2f}B"
    if abs(value) >= 1e6:
        return f"{value / 1e6:,.2f}M"
    return f"{value:,.0f}"


def fmt_pct(value: Optional[float], digits: int = 2) -> str:
    """将比率格式化为百分比字符串。

    Args:
        value: 比率（0~1）或已是百分数的数值
        digits: 小数位数

    Returns:
        格式化字符串；None 时返回 'N/A'
    """
    if value is None:
        return "N/A"
    return f"{value * 100:.{digits}f}%"


def fmt_pct_raw(value: Optional[float], digits: int = 2) -> str:
    """格式化已是百分数的值（如涨跌幅）。

    Args:
        value: 百分数（如 -6.9 表示 -6.9%）
        digits: 小数位数

    Returns:
        格式化字符串；None 时返回 'N/A'
    """
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}%"


def fmt_x(value: Optional[float], digits: int = 2) -> str:
    """格式化倍数（如 P/S、稀释倍数）。

    Args:
        value: 倍数
        digits: 小数位数

    Returns:
        格式化字符串；None 时返回 'N/A'
    """
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}×"


def change_class(value: Optional[float]) -> str:
    """按涨跌返回 CSS 颜色（涨绿跌红，遵循国内习惯的反向不适用：此处沿用项目看板约定）。

    Args:
        value: 涨跌幅（%）

    Returns:
        CSS 颜色值
    """
    if value is None:
        return COLORS["muted"]
    return COLORS["green"] if value >= 0 else COLORS["red"]


def _apply_dark_layout(fig: go.Figure, title: str, height: int = 360) -> go.Figure:
    """统一应用深色主题布局。

    Args:
        fig: Plotly 图形对象
        title: 图标题
        height: 图高度

    Returns:
        应用布局后的图形对象
    """
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=COLORS["text"]), x=0.01),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=50, r=30, t=50, b=40),
        font=dict(color=COLORS["text"], size=12),
        legend=dict(orientation="h", y=1.08, x=0),
    )
    return fig


# --------------------------------------------------------------------------
# 图表
# --------------------------------------------------------------------------

def supply_chart(snapshot: TokenSnapshot) -> go.Figure:
    """生成代币供应量结构环形图（流通 vs 待解锁）。

    Args:
        snapshot: 代币快照

    Returns:
        Plotly 图形对象
    """
    circulating = snapshot.circulating_supply or 0
    locked = snapshot.locked_supply or 0

    fig = go.Figure(
        data=[
            go.Pie(
                labels=["流通", "待解锁"],
                values=[circulating, locked],
                hole=0.55,
                marker=dict(colors=[COLORS["blue"], COLORS["purple"]]),
                textinfo="label+percent",
                hovertemplate="%{label}: %{value:,.0f} 枚 (%{percent})<extra></extra>",
            )
        ]
    )
    return _apply_dark_layout(fig, "供应量结构（流通 vs 待解锁）", 340)


def price_change_chart(snapshot: TokenSnapshot) -> go.Figure:
    """生成代币近期涨跌柱状图（24h / 7d / 30d）。

    Args:
        snapshot: 代币快照

    Returns:
        Plotly 图形对象
    """
    periods = ["24h", "7d", "30d"]
    values = [snapshot.change_24h, snapshot.change_7d, snapshot.change_30d]
    colors = [COLORS["green"] if (v or 0) >= 0 else COLORS["red"] for v in values]

    fig = go.Figure(
        data=[
            go.Bar(
                x=periods,
                y=values,
                marker=dict(color=colors),
                text=[fmt_pct_raw(v) for v in values],
                textposition="outside",
                hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
            )
        ]
    )
    fig.update_yaxes(title_text="涨跌幅 (%)", gridcolor="#1a2742")
    return _apply_dark_layout(fig, "近期涨跌", 340)


def protocol_scale_chart(snapshots: Sequence[ProtocolSnapshot]) -> go.Figure:
    """生成协议 TVL 与年化费用对比柱状图。

    Args:
        snapshots: 协议快照列表

    Returns:
        Plotly 图形对象
    """
    names = [s.name or s.slug for s in snapshots]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="TVL",
            x=names,
            y=[s.tvl for s in snapshots],
            marker=dict(color=COLORS["blue"]),
            hovertemplate="%{x} TVL: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="年化费用",
            x=names,
            y=[s.fees_annualized for s in snapshots],
            marker=dict(color=COLORS["cyan"]),
            hovertemplate="%{x} 年化费用: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="USD", gridcolor="#1a2742")
    return _apply_dark_layout(fig, "TVL 与年化费用对比")


def ps_chart(snapshots: Sequence[ProtocolSnapshot]) -> go.Figure:
    """生成协议 P/S（FDV 口径）对比柱状图。

    Args:
        snapshots: 协议快照列表

    Returns:
        Plotly 图形对象
    """
    names = [s.name or s.slug for s in snapshots]

    fig = go.Figure(
        data=[
            go.Bar(
                x=names,
                y=[s.ps_fdv for s in snapshots],
                marker=dict(color=[COLORS["purple"], COLORS["amber"]][: len(names)]),
                text=[fmt_x(s.ps_fdv) for s in snapshots],
                textposition="outside",
                hovertemplate="%{x} P/S: %{y:.2f}×<extra></extra>",
            )
        ]
    )
    fig.update_yaxes(title_text="P/S (FDV/年化费用)", gridcolor="#1a2742")
    return _apply_dark_layout(fig, "估值对比 P/S（FDV 口径，越低越便宜）")


def unlock_chart(profiles: Sequence[UnlockProfile]) -> go.Figure:
    """生成多代币待解锁占比柱状图（按风险着色）。

    Args:
        profiles: 解锁画像列表

    Returns:
        Plotly 图形对象
    """
    names = [p.symbol or p.coin_id for p in profiles]
    values = [(p.locked_ratio or 0) * 100 for p in profiles]

    risk_colors = {"高": COLORS["red"], "中": COLORS["amber"], "低": COLORS["green"]}
    colors = [risk_colors.get(p.risk_level, COLORS["muted"]) for p in profiles]

    fig = go.Figure(
        data=[
            go.Bar(
                x=names,
                y=values,
                marker=dict(color=colors),
                text=[f"{v:.1f}%" for v in values],
                textposition="outside",
                customdata=[p.risk_level for p in profiles],
                hovertemplate="%{x}: %{y:.1f}% 待解锁（风险 %{customdata}）<extra></extra>",
            )
        ]
    )
    fig.update_yaxes(title_text="待解锁占比 (%)", gridcolor="#1a2742")
    return _apply_dark_layout(fig, "解锁敞口（待解锁占比，越低越安全）")


# --------------------------------------------------------------------------
# HTML 渲染
# --------------------------------------------------------------------------

def render_html(
    title: str,
    subtitle: str,
    summary: str,
    sections: Sequence[Dict[str, Any]],
) -> str:
    """渲染深色主题研究报告 HTML。

    Args:
        title: 报告标题
        subtitle: 副标题（含数据时点）
        summary: 首屏结论
        sections: 区块列表，每项含 heading / body(HTML) / figure(可选)

    Returns:
        HTML 字符串
    """
    blocks: List[str] = []
    for section in sections:
        blocks.append(f"<section><h2>{section['heading']}</h2>")
        if section.get("body"):
            blocks.append(section["body"])
        if section.get("figure") is not None:
            blocks.append(section["figure"])
        blocks.append("</section>")

    body = "\n".join(blocks)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --bg: {COLORS['bg']}; --panel: {COLORS['panel']}; --line: #22304f;
    --text: {COLORS['text']}; --muted: {COLORS['muted']};
    --cyan: {COLORS['cyan']}; --blue: {COLORS['blue']}; --purple: {COLORS['purple']};
    --green: {COLORS['green']}; --red: {COLORS['red']}; --amber: {COLORS['amber']};
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: radial-gradient(1200px 600px at 20% -10%, #16224a 0%, var(--bg) 55%);
         color: var(--text); font-family: -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
         line-height: 1.6; }}
  .wrap {{ max-width: 1060px; margin: 0 auto; padding: 28px 22px 60px; }}
  header {{ border: 1px solid var(--line); border-radius: 16px; padding: 22px 24px;
            background: linear-gradient(135deg, rgba(77,124,255,.12), rgba(169,120,255,.10)); margin-bottom: 18px; }}
  h1 {{ margin: 0 0 6px; font-size: 26px; letter-spacing: .5px; }}
  .sub {{ color: var(--muted); font-size: 13px; }}
  h2 {{ font-size: 18px; margin: 26px 0 12px; padding-left: 10px; border-left: 3px solid var(--blue); }}
  .summary {{ border: 1px solid #2c3e63; border-radius: 14px; padding: 16px 18px; margin-bottom: 8px;
              background: linear-gradient(135deg, rgba(58,210,159,.08), rgba(53,224,230,.06)); }}
  .panel {{ background: #0e1626; border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; margin-top: 6px; }}
  th, td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: left; }}
  th {{ color: var(--muted); font-weight: 600; }}
  .src {{ font-size: 11.5px; color: #6b7da0; }}
  .risk {{ color: var(--amber); }}
  .disc {{ font-size: 12.5px; color: var(--muted); border-top: 1px dashed var(--line);
           margin-top: 24px; padding-top: 14px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{title}</h1>
    <div class="sub">{subtitle}</div>
  </header>
  <div class="summary">{summary}</div>
  {body}
  <div class="disc"><b>风险提示：</b>{DISCLAIMER}</div>
</div>
</body>
</html>"""


def _fig_html(fig: go.Figure) -> str:
    """将 Plotly 图形转为可嵌入的 HTML 片段。

    Args:
        fig: Plotly 图形对象

    Returns:
        HTML 片段（CDN 引入 plotly.js）
    """
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def _token_table(snapshot: TokenSnapshot) -> str:
    """渲染单代币指标表。

    Args:
        snapshot: 代币快照

    Returns:
        HTML 表格片段
    """
    rows = [
        ("价格", fmt_usd(snapshot.price)),
        ("市值 MC", fmt_usd(snapshot.market_cap)),
        ("完全稀释 FDV", fmt_usd(snapshot.fdv)),
        ("流通量", fmt_num(snapshot.circulating_supply)),
        ("最大供应量", fmt_num(snapshot.max_supply or snapshot.total_supply)),
        ("流通率", fmt_pct(snapshot.circulating_ratio)),
        ("待解锁量", fmt_num(snapshot.locked_supply)),
        ("待解锁占比", fmt_pct(snapshot.locked_ratio)),
        ("稀释倍数", fmt_x(snapshot.dilution_multiple)),
        ("FDV/MC", fmt_x(snapshot.fdv_mc_ratio)),
        ("ATH", fmt_usd(snapshot.ath)),
        ("距 ATH", fmt_pct_raw(snapshot.ath_change_pct)),
    ]
    body = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
    return (
        f'<div class="panel"><table><tr><th>指标</th><th>数值</th></tr>{body}</table>'
        f'<p class="src">来源：{snapshot.source} · 数据时点：{snapshot.fetched_at}</p></div>'
    )


def _protocol_table(snapshots: Sequence[ProtocolSnapshot]) -> str:
    """渲染协议对比表。

    Args:
        snapshots: 协议快照列表

    Returns:
        HTML 表格片段
    """
    headers = "".join(
        f"<th>{s.name or s.slug}</th>" for s in snapshots
    )
    metrics = [
        ("TVL", lambda s: fmt_usd(s.tvl)),
        ("年化费用", lambda s: fmt_usd(s.fees_annualized)),
        ("30d 费用", lambda s: fmt_usd(s.fees_30d)),
        ("资本效率(费用/TVL)", lambda s: fmt_pct(s.fee_to_tvl)),
        ("代币市值", lambda s: fmt_usd(s.token.market_cap) if s.token else "N/A"),
        ("代币 FDV", lambda s: fmt_usd(s.token.fdv) if s.token else "N/A"),
        ("P/S (FDV口径)", lambda s: fmt_x(s.ps_fdv)),
        ("P/S (市值口径)", lambda s: fmt_x(s.ps_mcap)),
        ("代币流通率", lambda s: fmt_pct(s.token.circulating_ratio) if s.token else "N/A"),
        ("覆盖链数", lambda s: str(len(s.chain_breakdown or {}))),
    ]

    rows = []
    for label, getter in metrics:
        cells = "".join(f"<td>{getter(s)}</td>" for s in snapshots)
        rows.append(f"<tr><td>{label}</td>{cells}</tr>")

    body = "".join(rows)
    return (
        f'<div class="panel"><table><tr><th>指标</th>{headers}</tr>{body}</table>'
        f'<p class="src">来源：DefiLlama（TVL/费用）+ CoinGecko（代币）· '
        f'数据时点：{datetime.now().strftime("%Y-%m-%d %H:%M")}</p></div>'
    )


def _unlock_table(profiles: Sequence[UnlockProfile]) -> str:
    """渲染解锁抛压对比表。

    Args:
        profiles: 解锁画像列表

    Returns:
        HTML 表格片段
    """
    rows = []
    for p in profiles:
        risk_style = (
            COLORS["red"] if p.risk_level == "高"
            else COLORS["amber"] if p.risk_level == "中"
            else COLORS["green"]
        )
        rows.append(
            f"<tr><td>{p.symbol or p.coin_id}</td>"
            f"<td>{fmt_pct(p.circulating_ratio)}</td>"
            f"<td>{fmt_pct(p.locked_ratio)}</td>"
            f"<td>{fmt_num(p.locked_supply)}</td>"
            f"<td>{fmt_x(p.dilution_multiple)}</td>"
            f'<td style="color:{risk_style}">{p.risk_level}</td>'
            f"<td>{fmt_usd(p.market_cap)}</td></tr>"
        )

    body = "".join(rows)
    return (
        f'<div class="panel"><table><tr><th>代币</th><th>流通率</th><th>待解锁占比</th>'
        f"<th>待解锁量</th><th>稀释倍数</th><th>风险分档</th><th>市值</th></tr>{body}</table>"
        f'<p class="src">来源：CoinGecko 供应量数据 · 风险分档阈值：待解锁≥50% 高，≥30% 中，&lt;30% 低。'
        f"精确解锁日历需 TokenUnlocks（需 key）或项目公告核对。</p></div>"
    )


# --------------------------------------------------------------------------
# 报告模式
# --------------------------------------------------------------------------

def build_token_report(
    snapshots: Sequence[TokenSnapshot],
) -> str:
    """构建代币研究报告 HTML。

    Args:
        snapshots: 代币快照列表

    Returns:
        HTML 字符串
    """
    sections: List[Dict[str, Any]] = []
    for snapshot in snapshots:
        label = f"{snapshot.name or snapshot.coin_id} ({snapshot.symbol})"
        sections.append(
            {
                "heading": label,
                "body": _token_table(snapshot),
                "figure": (
                    '<div class="panel">' + _fig_html(supply_chart(snapshot))
                    + _fig_html(price_change_chart(snapshot)) + "</div>"
                ),
            }
        )

    first = snapshots[0]
    summary = (
        f"<b>研究标的：</b>{', '.join(s.name or s.coin_id for s in snapshots)}。"
        f"核心关注点为<b>流通率 {fmt_pct(first.circulating_ratio)}</b> 与"
        f"<b>稀释倍数 {fmt_x(first.dilution_multiple)}</b>——"
        f"二者共同决定未来解锁抛压；估值侧看 FDV/MC {fmt_x(first.fdv_mc_ratio)}。"
    )

    return render_html(
        title="代币研究报告",
        subtitle=f"基于公开数据的研究框架 · 生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M')} · 来源 CoinGecko",
        summary=summary,
        sections=sections,
    )


def build_compare_report(snapshots: Sequence[ProtocolSnapshot]) -> str:
    """构建协议对比报告 HTML。

    Args:
        snapshots: 协议快照列表

    Returns:
        HTML 字符串
    """
    names = " vs ".join(s.name or s.slug for s in snapshots)
    sections = [
        {"heading": "核心指标对比", "body": _protocol_table(snapshots)},
        {
            "heading": "规模与费用",
            "figure": f'<div class="panel">{_fig_html(protocol_scale_chart(snapshots))}</div>',
        },
        {
            "heading": "估值对比",
            "figure": f'<div class="panel">{_fig_html(ps_chart(snapshots))}</div>',
        },
    ]

    leader = max(snapshots, key=lambda s: s.fees_annualized or 0)
    summary = (
        f"<b>{names}</b>：费用规模领先者为 <b>{leader.name or leader.slug}</b>"
        f"（年化费用 {fmt_usd(leader.fees_annualized)}，"
        f"资本效率 {fmt_pct(leader.fee_to_tvl)}）。"
        f"估值需按<b>同一口径</b>横比（本表同时给出 FDV 与市值两种 P/S）；"
        f"<span class='risk'>注意：费用全给 LP 的协议，其代币本身可能零协议收入。"
        f"</span>"
    )

    return render_html(
        title=f"{names} — DeFi 协议对比",
        subtitle=f"DeFi 协议研究方法论 · 生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M')} · 来源 DefiLlama + CoinGecko",
        summary=summary,
        sections=sections,
    )


def build_unlock_report(profiles: Sequence[UnlockProfile]) -> str:
    """构建解锁抛压报告 HTML。

    Args:
        profiles: 解锁画像列表

    Returns:
        HTML 字符串
    """
    sections = [
        {"heading": "解锁敞口对比", "body": _unlock_table(profiles)},
        {
            "heading": "待解锁占比可视化",
            "figure": f'<div class="panel">{_fig_html(unlock_chart(profiles))}</div>',
        },
        {
            "heading": "解锁抛压五步法",
            "body": (
                '<div class="panel"><ol>'
                "<li><b>拆分配套桶</b>：团队 / 投资人 / 国库 / 空投 / 生态激励各占多少，集中在大户=抛压集中。</li>"
                "<li><b>判释放节奏</b>：cliff（一次性）比线性释放危险得多。</li>"
                "<li><b>算成本差</b>：解锁方成本 vs 现价；现价远低于成本则抛售动机弱。</li>"
                "<li><b>量化稀释</b>：稀释倍数 = 最大供应量 / 流通量（本表已给出）。</li>"
                "<li><b>看承接</b>：CEX+DEX 深度与稳定币净流入能否吸收解锁量。</li>"
                "</ol></div>"
            ),
        },
    ]

    worst = max(profiles, key=lambda p: p.locked_ratio or 0)
    summary = (
        f"共分析 <b>{len(profiles)}</b> 个代币的解锁敞口。"
        f"待解锁占比最高的是 <b>{worst.symbol or worst.coin_id}</b>"
        f"（{fmt_pct(worst.locked_ratio)}，稀释 {fmt_x(worst.dilution_multiple)}，风险 <span class='risk'>{worst.risk_level}</span>）。"
        f"本表仅用供应量硬数据；<b>精确 cliff 日期需 TokenUnlocks 或项目公告核对</b>。"
    )

    return render_html(
        title="代币解锁抛压分析",
        subtitle=f"解锁抛压研究框架 · 生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M')} · 来源 CoinGecko",
        summary=summary,
        sections=sections,
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def parse_compare_targets(raw: Sequence[str]) -> List[Dict[str, str]]:
    """解析 ``--compare`` 参数，支持 ``slug`` 或 ``slug:coin_id`` 两种写法。

    Args:
        raw: 原始参数列表

    Returns:
        解析后的目标列表
    """
    targets: List[Dict[str, str]] = []
    for item in raw:
        if ":" in item:
            slug, coin_id = item.split(":", 1)
            targets.append({"slug": slug.strip(), "coin_id": coin_id.strip()})
        else:
            targets.append({"slug": item.strip()})
    return targets


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 入口。

    Args:
        argv: 命令行参数（默认取 sys.argv）

    Returns:
        退出码（0 成功，1 参数错误）
    """
    parser = argparse.ArgumentParser(
        description="Generate token & DeFi protocol research reports"
    )
    parser.add_argument("--token", nargs="+", help="CoinGecko coin IDs (e.g. ethena)")
    parser.add_argument(
        "--compare",
        nargs="+",
        help="DefiLlama protocol slugs, optionally slug:coin_id (e.g. uniswap:uniswap)",
    )
    parser.add_argument("--unlock", nargs="+", help="CoinGecko coin IDs for unlock analysis")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: reports/)",
    )
    parser.add_argument(
        "--format", choices=["html", "json"], default="html", help="Output format"
    )

    args = parser.parse_args(argv)

    if not any([args.token, args.compare, args.unlock]):
        parser.error("至少需要一个模式参数：--token / --compare / --unlock")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    researcher = TokenDefiResearcher()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.token:
        snapshots = [researcher.analyze_token(cid) for cid in args.token]
        logger.info(f"已分析 {len(snapshots)} 个代币")
        if args.format == "json":
            payload = [s.to_dict() for s in snapshots]
            out = args.output_dir / f"token_research_{timestamp}.json"
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            html = build_token_report(snapshots)
            out = args.output_dir / f"token_research_{timestamp}.html"
            out.write_text(html, encoding="utf-8")
        print(f"[完成] 报告已保存: {out}")

    if args.compare:
        targets = parse_compare_targets(args.compare)
        snapshots = researcher.compare_protocols(targets)
        logger.info(f"已对比 {len(snapshots)} 个协议")
        if args.format == "json":
            payload = [s.to_dict() for s in snapshots]
            out = args.output_dir / f"protocol_compare_{timestamp}.json"
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            html = build_compare_report(snapshots)
            out = args.output_dir / f"protocol_compare_{timestamp}.html"
            out.write_text(html, encoding="utf-8")
        print(f"[完成] 报告已保存: {out}")

    if args.unlock:
        profiles = researcher.unlock_profiles(args.unlock)
        logger.info(f"已分析 {len(profiles)} 个代币的解锁敞口")
        if args.format == "json":
            payload = [p.to_dict() for p in profiles]
            out = args.output_dir / f"unlock_pressure_{timestamp}.json"
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            html = build_unlock_report(profiles)
            out = args.output_dir / f"unlock_pressure_{timestamp}.html"
            out.write_text(html, encoding="utf-8")
        print(f"[完成] 报告已保存: {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
