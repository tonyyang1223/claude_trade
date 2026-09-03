"""HTML 报告生成（自包含，深色科技风）。

render_html(result, decision) -> str 返回单文件 HTML，可直接落盘或内联预览。
图表用 Chart.js CDN（用户环境可联网时渲染；离线仅显示数据卡片）。
所有外部文本经 html.escape，防注入（代币名/符号可能含 HTML 字符）。
"""
from __future__ import annotations

import html
import json
from typing import Dict, Optional

from ..types import AnalysisResult

_DIM_LABEL = {
    "security": "欺诈/安全",
    "trend": "趋势强弱",
    "momentum": "多周期动量",
    "liquidity_health": "流动性健康",
    "sentiment": "社媒情绪",
    "innovation": "技术创新",
    "taxonomy": "类别清晰",
    "community": "社区基础",
}
_DIM_COLOR = {
    "security": "#ff5c7a",
    "trend": "#22d3ee",
    "momentum": "#f472b6",
    "liquidity_health": "#38bdf8",
    "sentiment": "#a78bfa",
    "innovation": "#34d399",
    "taxonomy": "#fbbf24",
    "community": "#facc15",
}


def _e(s) -> str:
    return html.escape("" if s is None else str(s))


def _fmt_usd(v) -> str:
    if v is None:
        return "—"
    if v >= 1e9:
        return f"${v / 1e9:.2f}B"
    if v >= 1e6:
        return f"${v / 1e6:.2f}M"
    if v >= 1e3:
        return f"${v / 1e3:.1f}K"
    return f"${v:,.0f}"


def _score_color(score: float) -> str:
    if score >= 7.5:
        return "#34d399"
    if score >= 6.0:
        return "#fbbf24"
    if score >= 5.0:
        return "#fb923c"
    return "#ff5c7a"


def render_html(result: AnalysisResult, decision: Dict, *, title: Optional[str] = None) -> str:
    sym = _e(result.symbol or "—")
    name = _e(result.name or "—")
    addr = _e(result.address)
    chain = _e(result.chain.value)
    total = decision.get("total") or 0.0
    scored: Dict[str, float] = decision.get("scored") or {}
    missing: list[str] = decision.get("missing") or []

    # ---- 数据卡片 ----
    p = result.profile
    d = result.dex
    liq = result.liquidity
    h = result.holders
    cards = []
    if d and d.price_usd is not None:
        q = f" (计价：{d.quote_symbol.upper()})" if d.quote_symbol else ""
        cards.append(("价格", f"${d.price_usd:,.6f}{q}"))
    if p and p.market_cap is not None:
        cards.append(("市值 MC", _fmt_usd(p.market_cap)))
    if p and p.fdv is not None:
        cards.append(("完全稀释 FDV", _fmt_usd(p.fdv)))
    if d and d.liquidity_usd is not None:
        cards.append(("流动性", _fmt_usd(d.liquidity_usd)))
    if d and d.volume_24h is not None:
        cards.append(("24h 成交量", _fmt_usd(d.volume_24h)))
    if d and d.price_change_24h is not None:
        cards.append(("24h 涨跌", f"{d.price_change_24h:+.1f}%"))
    if d and d.age_days is not None:
        cards.append(("币龄", f"{d.age_days:.0f} 天"))
    if d and d.buy_sell_ratio is not None:
        cards.append(("买卖比(笔数)", f"{d.buy_sell_ratio}"))
    tx24 = (d.txns or {}).get("h24") if d else None
    if tx24 and tx24.get("buys") is not None:
        cards.append(("24h 买卖笔数", f"{tx24['buys']}/{tx24['sells']}"))
    if h and h.total_holders is not None:
        cards.append(("持币地址数", f"{h.total_holders:,}"))
    if liq and liq.locked_pct is not None:
        cards.append(("LP 锁仓", f"{liq.locked_pct:.0f}%"))
    if d and d.socials:
        cards.append(("官方渠道", f"{len(d.socials)} 个"))
    cards_html = "".join(
        f'<div class="card"><div class="card-v">{_e(v)}</div><div class="card-k">{_e(k)}</div></div>'
        for k, v in cards
    ) or '<div class="card"><div class="card-v">—</div><div class="card-k">无可用数据</div></div>'

    # ---- 价格异常横幅 ----
    anomaly_html = ""
    if d and d.price_anomaly:
        anomaly_html = ('<div class="anomaly">⚠️ 检测到价格异常：原始报价单价 × 总量 与 FDV 严重背离，'
                         '已自动改用 FDV 反推单价。请以 FDV/市值 为真实估值基准。</div>')

    # ---- 多周期涨跌 + 买卖笔数表（Meme 关键）----
    mt_html = ""
    if d and d.price_changes:
        rows = "".join(
            f"<tr><td>{k}</td><td class=\"{'up' if v >= 0 else 'dn'}\">{v:+.1f}%</td></tr>"
            for k, v in d.price_changes.items()
        )
        mt_html = (f'<div class="section"><h2>多周期涨跌（Meme 动量）</h2>'
                   f'<table class="mt"><tr><th>周期</th><th>涨跌幅</th></tr>{rows}</table></div>')

    # ---- 维度明细 ----
    dim_rows = []
    for key, label in _DIM_LABEL.items():
        sc = scored.get(key)
        if sc is None:
            bar = '<span class="na">缺失（已排除加权）</span>'
        else:
            pct = max(0, min(100, sc * 10))
            col = _DIM_COLOR.get(key, "#22d3ee")
            bar = (f'<div class="bar"><div class="bar-fill" style="width:{pct:.0f}%;'
                   f'background:{col}"></div></div><span class="sc">{sc:.1f}/10</span>')
        notes = result.notes.get(key) or []
        note_html = "".join(f"<li>{_e(n)}</li>" for n in notes)
        dim_rows.append(
            f'<div class="dim"><div class="dim-head"><span class="dim-name">{_e(label)}</span>'
            f'{bar}</div>'
            f'<ul class="dim-notes">{note_html}</ul></div>'
        )
    dims_html = "\n".join(dim_rows)

    # ---- 红旗 ----
    flags = result.flags or []
    flags_html = (
        "".join(f'<li class="flag">{_e(f.msg)}</li>' for f in flags)
        or '<li class="ok">未发现明显欺诈红旗</li>'
    )

    # ---- 决策 ----
    dec = _e(decision.get("decision", "—"))
    risk = _e(decision.get("risk", "—"))
    position = _e(decision.get("position", "—"))
    triggers = decision.get("triggers") or []
    triggers_html = "".join(f"<li>{_e(t)}</li>" for t in triggers)
    disclaim = _e(decision.get("disclaimer", ""))
    miss_html = f'<p class="miss">缺失维度：{_e(", ".join(missing))}</p>' if missing else ""

    radar_labels = json.dumps([_DIM_LABEL[k] for k in _DIM_LABEL], ensure_ascii=False)
    radar_data = json.dumps([round(scored.get(k, 0) or 0, 1) for k in _DIM_LABEL])

    engine = _e(getattr(result, 'engine_version', '') or '')
    fetched = _e(result.fetched_at or '')
    sources = _e(', '.join(result.sources_used) or '公开链上数据')
    doc_title = _e(title or f"{(result.symbol or '—')} · {chain.upper()} 链上代币分析报告")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{doc_title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root{{--bg:#0b1020;--panel:#121a33;--panel2:#0f1730;--line:#22305c;--txt:#e6edff;--muted:#8aa0c8;--cyan:#22d3ee;--purple:#a78bfa;}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:radial-gradient(1200px 600px at 70% -10%,#16224a 0%,var(--bg) 55%);color:var(--txt);font-family:-apple-system,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;padding:28px}}
  .wrap{{max-width:960px;margin:0 auto}}
  h1{{font-size:24px;margin:0 0 4px}}
  .sub{{color:var(--muted);font-size:13px;margin-bottom:18px}}
  .addr{{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--cyan);word-break:break-all}}
  .hero{{display:flex;gap:18px;align-items:center;background:linear-gradient(135deg,#15224a,#0f1730);border:1px solid var(--line);border-radius:16px;padding:20px 22px;margin-bottom:18px}}
  .gauge{{--c:{_score_color(total)};width:120px;height:120px;border-radius:50%;flex:0 0 auto;display:grid;place-items:center;background:conic-gradient(var(--c) {total*36:.0f}deg,#1c2748 0);position:relative}}
  .gauge::after{{content:"";position:absolute;inset:12px;border-radius:50%;background:var(--panel2)}}
  .gauge .gv{{position:relative;font-size:30px;font-weight:700;color:var(--c)}}
  .gauge .gl{{position:relative;font-size:11px;color:var(--muted)}}
  .hero .meta{{flex:1}}
  .badge{{display:inline-block;padding:6px 12px;border-radius:999px;font-weight:700;font-size:15px;background:{_score_color(total)}22;color:{_score_color(total)};border:1px solid {_score_color(total)}66}}
  .kv{{margin-top:10px;display:flex;gap:22px;flex-wrap:wrap;color:var(--muted);font-size:13px}}
  .kv b{{color:var(--txt)}}
  .cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px;margin-bottom:18px}}
  .card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px}}
  .card-v{{font-size:18px;font-weight:700}}
  .card-k{{font-size:12px;color:var(--muted);margin-top:2px}}
  .section{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:16px}}
  .section h2{{font-size:16px;margin:0 0 12px;color:var(--cyan)}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
  @media(max-width:720px){{.grid2{{grid-template-columns:1fr}}}}
  .dim{{margin-bottom:14px}}
  .dim-head{{display:flex;align-items:center;gap:10px}}
  .dim-name{{width:96px;color:var(--muted);font-size:13px}}
  .bar{{flex:1;height:10px;background:#1c2748;border-radius:6px;overflow:hidden}}
  .bar-fill{{height:100%;border-radius:6px}}
  .sc{{width:54px;text-align:right;font-size:13px;font-weight:600}}
  .na{{color:var(--muted);font-size:12px}}
  .dim-notes{{margin:6px 0 0 106px;padding:0;list-style:none;font-size:12px;color:var(--muted)}}
  .dim-notes li{{margin:2px 0}}
  ul.flags{{margin:0;padding-left:18px}} ul.flags li{{margin:5px 0;font-size:13px}}
  .flag{{color:#ff8fa3}} .ok{{color:#7ee2b8;list-style:none;margin-left:-18px}}
  .trig{{margin:8px 0 0;padding-left:18px;font-size:13px}} .trig li{{margin:4px 0}}
  .disclaim{{margin-top:14px;font-size:11px;color:var(--muted);border-top:1px dashed var(--line);padding-top:10px;line-height:1.5}}
  .miss{{font-size:12px;color:#fbbf24}}
  .anomaly{{margin:12px 0;padding:10px 14px;border-radius:10px;font-size:13px;line-height:1.5;
    background:#3a2a12;border:1px solid #fbbf2466;color:#ffd98a}}
  table.mt{{width:100%;border-collapse:collapse;font-size:13px;margin-top:4px}}
  table.mt th{{text-align:left;color:var(--muted);font-weight:500;padding:4px 8px;border-bottom:1px solid var(--line)}}
  table.mt td{{padding:4px 8px;border-bottom:1px solid #1a2547}}
  table.mt td.up{{color:#34d399}} table.mt td.dn{{color:#ff8fa3}}
  canvas{{max-height:300px}}
</style></head>
<body><div class="wrap">
  <h1>{doc_title}</h1>
  <div class="sub">链上代币多维分析 · 自动生成于本地 · 仅基于公开数据</div>
  <div class="addr">{addr}</div>

  <div class="hero">
    <div class="gauge"><div><div class="gv">{total:.1f}</div><div class="gl">综合分/10</div></div></div>
    <div class="meta">
      <span class="badge">{dec}</span>
      <div class="kv">
        <span>风险等级：<b>{risk}</b></span>
        <span>建议仓位：<b>{position}</b></span>
        <span>链：<b>{chain.upper()}</b></span>
        <span>名称：<b>{name}</b></span>
      </div>
    </div>
  </div>

  <div class="cards">{cards_html}</div>

  {anomaly_html}

  <div class="grid2">
    <div class="section">
      <h2>多维评分（{len([k for k in _DIM_LABEL if scored.get(k) is not None])} 项已计）</h2>
      <canvas id="radar"></canvas>
      <div style="margin-top:12px">{dims_html}</div>
    </div>
    <div class="section">
      <h2>欺诈红旗</h2>
      <ul class="flags">{flags_html}</ul>
    </div>
  </div>

  {mt_html}

  <div class="section">
    <h2>决策与触发条件</h2>
    <ul class="trig">{triggers_html}</ul>
    {miss_html}
    <div class="disclaim">{disclaim}</div>
    <div style="margin-top:8px;font-size:11px;color:var(--muted)">引擎 v{engine} · 数据来源：{sources} · 抓取于 {fetched}</div>
  </div>
</div>
<script>
var ctx=document.getElementById('radar');
if(ctx){{new Chart(ctx,{{type:'radar',data:{{labels:{radar_labels},datasets:[{{data:{radar_data},
backgroundColor:'rgba(34,211,238,.18)',borderColor:'#22d3ee',pointBackgroundColor:'#a78bfa',borderWidth:2}}]}},
options:{{scales:{{r:{{min:0,max:10,grid:{{color:'#22305c'}},angleLines:{{color:'#22305c'}},
pointLabels:{{color:'#cdd9ff',font:{{size:12}}}},ticks:{{color:'#5f74a3',backdropColor:'transparent'}}}}}},
plugins:{{legend:{{display:false}}}}}}}});}}
</script>
</body></html>"""
