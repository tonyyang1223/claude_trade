#!/usr/bin/env python
"""Batch token evaluation + single-token research report (type-aware).

Uses the type-aware :class:`src.analysis.scorer.Scorer` to evaluate the
highest market-cap tokens (or a single coin) and renders a dark-themed HTML
report with per-dimension scores, a research rating, a suggested position band
and a mandatory disclaimer.

Usage:
    # Top 20 by market cap
    python scripts/research/batch_evaluate.py --top 20

    # Deep-dive a single coin
    python scripts/research/batch_evaluate.py --coin binancecoin

    # JSON instead of HTML
    python scripts/research/batch_evaluate.py --top 15 --format json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Allow running from repo root or anywhere
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.api.coingecko import CoinGeckoClient
from src.api.defillama import DefiLlamaClient
from src.research.token_classification import classify_coin, label_of
from src.research.token_defi import TokenDefiResearcher
from src.analysis.scorer import Scorer

try:
    from src.api.reddit_free import RedditFreeClient
except Exception:  # reddit client optional
    RedditFreeClient = None

from src.analysis.advice import DISCLAIMER

REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)

COLORS = {
    "bg": "#0b1020", "panel": "#121a30", "text": "#e6ecf7", "muted": "#8ea0c0",
    "blue": "#4d7cff", "cyan": "#35e0e6", "purple": "#a978ff", "green": "#3ad29f",
    "red": "#ff6b81", "amber": "#ffcb6b",
}

DIM_ZH = {
    "market": "市场", "technical": "技术", "onchain": "链上", "sentiment": "情绪",
    "github": "开发", "social": "社交", "risk": "风险", "tokenomics": "代币经济",
    "valuation": "估值", "narrative": "叙事", "peg_stability": "锚定", "tvl": "TVL",
}


def build_scorer(token_type: str, tr, rc, defillama: Optional[DefiLlamaClient] = None, coingecko=None) -> Scorer:
    # In this restricted network, external hosts (api.github.com, alternative.me,
    # api.binance.com, blockchain.info) are blocked and their calls hang on the
    # socket timeout. The Scorer's typed path now treats a None analyzer as a
    # skipped dimension (excluded from coverage), so passing None keeps the run
    # fast and reliable. Only CoinGecko-based dims (market/social/risk/
    # tokenomics/valuation/peg) plus an optional short-timeout TVL are evaluated.
    # A single CoinGecko client is shared so the rate-limit throttle is coordinated
    # across evaluate()/scorer/researcher and we never burst past the free tier.
    return Scorer(
        token_type=token_type,
        token_researcher=tr,
        coingecko_client=coingecko,
        technical_analyzer=None,
        onchain_analyzer=None,
        sentiment_analyzer=None,
        github_analyzer=None,
        reddit_client=None,
        defillama_client=defillama or DefiLlamaClient(timeout=8),
    )


def evaluate(cg: CoinGeckoClient, tr: TokenDefiResearcher, rc, coin_id: str, defillama=None) -> Dict:
    """Classify + score a single coin. Returns a result dict (never raises)."""
    try:
        research = cg.get_coin_research_data(coin_id)
        categories = research.get("categories") or []
        token_type = classify_coin(categories)
        scorer = build_scorer(token_type, tr, rc, defillama, coingecko=cg)
        ps = scorer.score_project(coin_id)
        return {
            "ok": True,
            "coin_id": coin_id,
            "name": ps.coin_name,
            "symbol": ps.symbol,
            "token_type": token_type,
            "type_label": label_of(token_type),
            "categories": categories,
            "total_score": round(ps.total_score, 1),
            "rating": ps.rating,
            "risk_level": ps.risk_level,
            "action": ps.action,
            "position_range": ps.position_range,
            "coverage": ps.data_coverage,
            "dimension_scores": ps.dimension_scores,
            "triggers": ps.advice_triggers,
            "disclaimer": ps.disclaimer,
            "price": research.get("price"),
            "market_cap": research.get("market_cap"),
            "fdv": research.get("fdv"),
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "coin_id": coin_id, "error": str(e)}


def dim_bar(dim: str, score: int) -> str:
    pct = score / 5.0 * 100
    color = COLORS["green"] if score >= 4 else COLORS["amber"] if score >= 3 else COLORS["red"]
    return f"""
    <div style="margin:6px 0">
      <div style="display:flex;justify-content:space-between;font-size:13px;color:{COLORS['muted']}">
        <span>{DIM_ZH.get(dim, dim)}</span><span>{score}/5</span></div>
      <div style="background:{COLORS['panel']};border-radius:6px;height:8px;overflow:hidden">
        <div style="width:{pct:.0f}%;height:100%;background:{color}"></div></div>
    </div>"""


def rating_color(rating: str) -> str:
    return {
        "A+": COLORS["green"], "A": COLORS["green"], "B": COLORS["cyan"],
        "C": COLORS["amber"], "D": COLORS["red"], "F": COLORS["red"],
    }.get(rating, COLORS["muted"])


def render_html(results: List[Dict], meta: Dict) -> str:
    good = [r for r in results if r.get("ok")]
    good.sort(key=lambda r: r["total_score"], reverse=True)

    rows = ""
    for r in good:
        rows += f"""<tr>
          <td style="color:{COLORS['muted']}">{r['symbol']}</td>
          <td>{r['name']}</td>
          <td>{r['type_label']}</td>
          <td style="color:{rating_color(r['rating'])};font-weight:700">{r['rating']}</td>
          <td>{r['total_score']}</td>
          <td>{r['action']}</td>
          <td>{r['position_range']}</td>
          <td style="color:{COLORS['muted']}">{r['coverage']}</td>
        </tr>"""

    details = ""
    for r in good:
        bars = "".join(dim_bar(d, s) for d, s in r["dimension_scores"].items())
        triggers = "".join(f"<li style='margin:4px 0'>{t}</li>" for t in r.get("triggers", []))
        details += f"""
        <div style="background:{COLORS['panel']};border-radius:12px;padding:18px;margin:14px 0">
          <div style="display:flex;justify-content:space-between;align-items:baseline">
            <h3 style="margin:0;color:{COLORS['text']}">{r['name']} ({r['symbol']})</h3>
            <span style="color:{rating_color(r['rating'])};font-weight:700;font-size:20px">{r['rating']} · {r['total_score']}</span>
          </div>
          <div style="color:{COLORS['muted']};font-size:13px;margin:2px 0 12px">
            类型 {r['type_label']} · 风险 {r['risk_level']} · 建议仓位 {r['position_range']} · 数据覆盖 {r['coverage']}
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
            <div>{bars}</div>
            <div>
              <div style="color:{COLORS['cyan']};font-size:13px;margin-bottom:4px">触发/关注条件</div>
              <ul style="margin:0;padding-left:18px;color:{COLORS['text']};font-size:13px">{triggers}</ul>
            </div>
          </div>
        </div>"""

    failed = [r for r in results if not r.get("ok")]
    fail_html = ""
    if failed:
        items = "".join(f"<li>{r['coin_id']}: {r.get('error','?')}</li>" for r in failed)
        fail_html = f"""<div style="background:{COLORS['panel']};border-radius:12px;padding:14px;margin-top:18px">
          <div style="color:{COLORS['red']}">未成功评估 {len(failed)} 个标的:</div>
          <ul style="color:{COLORS['muted']};font-size:12px">{items}</ul></div>"""

    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>代币类型化评估 · {meta['title']}</title></head>
<body style="margin:0;background:{COLORS['bg']};color:{COLORS['text']};font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
<div style="max-width:1080px;margin:0 auto;padding:28px">
  <h1 style="margin:0 0 4px;color:{COLORS['text']}">代币类型化评估</h1>
  <div style="color:{COLORS['muted']};font-size:14px">{meta['title']} · 生成于 {meta['generated']} · 共评估 {len(good)} 个标的</div>

  <div style="background:{COLORS['panel']};border-radius:12px;padding:8px 14px;margin:18px 0;overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <thead><tr style="color:{COLORS['muted']};text-align:left">
        <th>符号</th><th>名称</th><th>类型</th><th>评级</th><th>总分</th><th>倾向</th><th>仓位</th><th>覆盖</th>
      </tr></thead><tbody>{rows}</tbody>
    </table>
  </div>

  <h2 style="color:{COLORS['text']}">逐标的明细</h2>
  {details}
  {fail_html}

  <div style="background:{COLORS['panel']};border-radius:12px;padding:14px;margin-top:22px;color:{COLORS['amber']};font-size:13px;line-height:1.6">
    {DISCLAIMER}
  </div>
</div></body></html>"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Type-aware batch token evaluation")
    ap.add_argument("--top", type=int, default=20, help="评估市值前 N 的代币")
    ap.add_argument("--coin", type=str, default=None, help="单独深度研究某个 coin id")
    ap.add_argument("--format", choices=["html", "json"], default="html")
    ap.add_argument("--out", type=str, default=None, help="输出文件路径")
    args = ap.parse_args(argv)

    cg = CoinGeckoClient()
    tr = TokenDefiResearcher(coingecko=cg)
    rc = RedditFreeClient() if RedditFreeClient else None
    dl = DefiLlamaClient(timeout=8)

    results: List[Dict] = []
    if args.coin:
        results.append(evaluate(cg, tr, rc, args.coin, dl))
        title = f"单币研究 · {args.coin}"
    else:
        top = cg.get_top_coins(limit=args.top)
        ids = [c["id"] for c in top if c.get("id")]
        print(f"批量评估市值前 {len(ids)} 个代币 …", file=sys.stderr)
        for i, cid in enumerate(ids, 1):
            print(f"  [{i}/{len(ids)}] {cid}", file=sys.stderr)
            results.append(evaluate(cg, tr, rc, cid, dl))
        title = f"市值前 {len(ids)} 代币"

    meta = {"title": title, "generated": datetime.now().strftime("%Y-%m-%d %H:%M")}

    if args.format == "json":
        out = args.out or f"reports/batch_eval_{datetime.now():%Y%m%d_%H%M%S}.json"
        Path(out).write_text(json.dumps({"meta": meta, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"written: {out}")
        return 0

    html = render_html(results, meta)
    out = args.out or f"reports/batch_eval_{datetime.now():%Y%m%d_%H%M%S}.html"
    Path(out).write_text(html, encoding="utf-8")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
