#!/usr/bin/env python
"""每小时宏观市场扫描框架 (Hourly Macro Scan)。

用途
----
定时（每小时）采集加密市场宏观数据并生成分析报告：
  1. CoinGecko 全局：总市值 / 总成交量 / BTC·ETH 占比 / 市值 24h 变化
  2. CoinGecko Top N：市场宽度（涨跌家数）、多周期涨跌（1h/24h/7d）
  3. 重点币种 watchlist：价格快照 + 与上一小时快照环比
  4. DefiLlama：配置链的 TVL 与稳定币总量
  5. 异动检测：1h/24h 阈值突破、成交量过热
  6. 市场状态判定：risk-on / neutral / risk-off

产出
----
  data/macro/YYYY-MM-DD/HHMM.json      # 时序快照（供回溯与环比）
  reports/macro/latest.html            # 最新报告（覆盖）
  reports/macro/archive/YYYY-MM-DD_HHMM.html  # 归档
  logs/macro.log                       # 运行日志

用法
----
  python scripts/macro/hourly_macro_scan.py                 # 默认配置
  python scripts/macro/hourly_macro_scan.py --config config/macro/watchlist.yaml
  python scripts/macro/hourly_macro_scan.py --quiet         # 静默（cron 用）

设计约定
--------
  * 单次执行、幂等退出（由外部调度器按小时触发）
  * 任一数据源失败只记录 errors 不中断整体（exit 0）；
    全部核心数据源失败才 exit 1
  * 不写入 .workbuddy/，不触碰敏感配置
"""
from __future__ import annotations

import argparse
import html
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.api.coingecko import CoinGeckoClient  # noqa: E402
from src.api.defillama import DefiLlamaClient  # noqa: E402

DEFAULT_CONFIG = PROJECT_ROOT / "config" / "macro" / "watchlist.yaml"
SNAPSHOT_DIR = PROJECT_ROOT / "data" / "macro"
REPORT_DIR = PROJECT_ROOT / "reports" / "macro"
LOG_FILE = PROJECT_ROOT / "logs" / "macro.log"

# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #


def setup_logging(quiet: bool) -> logging.Logger:
    logger = logging.getLogger("macro_scan")
    logger.setLevel(logging.INFO)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
    if not quiet:
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(sh)
    return logger


def fmt_usd(v: Optional[float]) -> str:
    if v is None:
        return "—"
    for div, suf in ((1e12, "万亿"), (1e8, "亿"), (1e4, "万")):
        if abs(v) >= div:
            return f"${v / div:,.2f}{suf}"
    return f"${v:,.0f}"


def fmt_pct(v: Optional[float], sign: bool = True) -> str:
    if v is None:
        return "—"
    return f"{v:+.2f}%" if sign else f"{v:.2f}%"


def esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


# --------------------------------------------------------------------------- #
# 数据采集（每一步独立容错）
# --------------------------------------------------------------------------- #


def fetch_global(cg: CoinGeckoClient, errors: List[str]) -> Dict[str, Any]:
    try:
        return cg.get_market_data() or {}
    except Exception as e:  # noqa: BLE001
        errors.append(f"coingecko/global: {type(e).__name__}: {e}")
        return {}


def fetch_top_coins(cg: CoinGeckoClient, top_n: int,
                    errors: List[str]) -> List[Dict[str, Any]]:
    try:
        return cg.get_top_coins(limit=min(top_n, 250),
                                price_change_percentage="1h,24h,7d") or []
    except Exception as e:  # noqa: BLE001
        errors.append(f"coingecko/markets: {type(e).__name__}: {e}")
        return []


def fetch_watchlist_extra(cg: CoinGeckoClient, missing_ids: List[str],
                          errors: List[str]) -> List[Dict[str, Any]]:
    """watchlist 中不在 Top N 的币种，按 ids 批量补抓。"""
    if not missing_ids:
        return []
    try:
        r = cg.session.get(
            f"{cg.BASE_URL}/coins/markets",
            params={
                "vs_currency": "usd",
                "ids": ",".join(missing_ids),
                "order": "market_cap_desc",
                "sparkline": "false",
                "price_change_percentage": "1h,24h,7d",
            },
            timeout=30,
        )
        r.raise_for_status()
        coins = r.json() or []
        return [
            {
                "id": c.get("id"),
                "symbol": (c.get("symbol") or "").upper(),
                "name": c.get("name"),
                "current_price": c.get("current_price"),
                "market_cap": c.get("market_cap"),
                "market_cap_rank": c.get("market_cap_rank"),
                "total_volume": c.get("total_volume"),
                "price_change_percentage_1h": c.get("price_change_percentage_1h_in_currency"),
                "price_change_percentage_24h": c.get("price_change_percentage_24h_in_currency"),
                "price_change_percentage_7d": c.get("price_change_percentage_7d_in_currency"),
                "ath_change_percentage": c.get("ath_change_percentage"),
            }
            for c in coins
        ]
    except Exception as e:  # noqa: BLE001
        errors.append(f"coingecko/watchlist: {type(e).__name__}: {e}")
        return []


def fetch_chain_tvl(dl: DefiLlamaClient, chains: List[str],
                    errors: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for chain in chains:
        try:
            out[chain] = dl.get_chain_tvl(chain)
        except Exception as e:  # noqa: BLE001
            errors.append(f"defillama/tvl/{chain}: {type(e).__name__}: {e}")
    return out


def fetch_fear_greed(errors: List[str], timeout: int = 6) -> Optional[Dict[str, Any]]:
    """alternative.me 恐惧贪婪指数（受限网络常不可达，容错跳过）。"""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=timeout)
        r.raise_for_status()
        data = (r.json().get("data") or [None])[0]
        if data:
            return {"value": int(data.get("value", 0)),
                    "label": data.get("value_classification")}
        return None
    except Exception as e:  # noqa: BLE001
        errors.append(f"fear_greed: {type(e).__name__}: {e}")
        return None


# --------------------------------------------------------------------------- #
# 分析
# --------------------------------------------------------------------------- #


def analyze_breadth(coins: List[Dict[str, Any]]) -> Dict[str, Any]:
    up24 = [c for c in coins if (c.get("price_change_percentage_24h_currency")
                                 or c.get("price_change_percentage_24h") or 0) > 0]
    up1h = [c for c in coins if (c.get("price_change_percentage_1h") or 0) > 0]
    n = len(coins) or 1
    return {
        "sample": len(coins),
        "up_24h": len(up24),
        "down_24h": len(coins) - len(up24),
        "up_pct_24h": round(len(up24) / n * 100, 1),
        "up_1h": len(up1h),
        "up_pct_1h": round(len(up1h) / n * 100, 1),
    }


def detect_anomalies(coins: List[Dict[str, Any]], thr: Dict[str, Any],
                     limit: int = 12) -> List[Dict[str, Any]]:
    """异动：1h/24h 阈值突破 + 成交过热，按异动强度排序。"""
    items: List[Dict[str, Any]] = []
    for c in coins:
        p1 = c.get("price_change_percentage_1h")
        p24 = c.get("price_change_percentage_24h_currency") \
            or c.get("price_change_percentage_24h")
        vol = c.get("total_volume") or 0
        mcap = c.get("market_cap") or 0
        turnover = (vol / mcap * 100) if mcap else None
        reasons = []
        if p1 is not None and abs(p1) >= thr.get("h1_pct", 3.0):
            reasons.append(f"1h {fmt_pct(p1)}")
        if p24 is not None and abs(p24) >= thr.get("h24_pct", 10.0):
            reasons.append(f"24h {fmt_pct(p24)}")
        if turnover is not None and turnover >= thr.get("turnover_x", 0.15) * 100:
            reasons.append(f"换手 {turnover:.0f}%")
        if reasons:
            items.append({
                "symbol": c.get("symbol"),
                "name": c.get("name"),
                "rank": c.get("market_cap_rank"),
                "price": c.get("current_price"),
                "p1h": p1, "p24h": p24, "p7d": c.get("price_change_percentage_7d"),
                "turnover_pct": round(turnover, 1) if turnover else None,
                "reasons": reasons,
                "strength": max(abs(p1 or 0), abs(p24 or 0) / 2),
            })
    items.sort(key=lambda x: -(x["strength"] or 0))
    return items[:limit]


def judge_regime(g: Dict[str, Any], breadth: Dict[str, Any],
                 thr: Dict[str, Any]) -> Dict[str, Any]:
    """市场状态：全局市值变化 × 宽度 交叉判定。"""
    mcap_chg = g.get("market_cap_change_percentage_24h")
    up_pct = breadth.get("up_pct_24h")
    score, votes = 0, []
    if mcap_chg is not None:
        if mcap_chg >= thr.get("mcap_change_gte", 1.0):
            score += 1; votes.append(f"市值24h {fmt_pct(mcap_chg)} → 偏多")
        elif mcap_chg <= thr.get("mcap_change_lte", -1.0):
            score -= 1; votes.append(f"市值24h {fmt_pct(mcap_chg)} → 偏空")
    if up_pct is not None:
        if up_pct >= thr.get("breadth_up_pct_gte", 60):
            score += 1; votes.append(f"宽度 {up_pct}% 上涨 → 偏多")
        elif up_pct <= thr.get("breadth_up_pct_lte", 40):
            score -= 1; votes.append(f"宽度 {up_pct}% 上涨 → 偏空")
    label = "🟢 Risk-On" if score >= 1 else ("🔴 Risk-Off" if score <= -1 else "⚪ Neutral")
    return {"label": label, "score": score, "votes": votes}


def diff_prev_snapshot(snapshot: Dict[str, Any],
                       watch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """与上一份快照环比（watchlist 价格变化）。

    watch 行的字段为 {"symbol", "price", ...}（本引擎的快照结构）。
    """
    prev_prices = {
        w.get("symbol"): w.get("price")
        for w in (snapshot.get("watchlist") or [])
    }
    rows, changed = [], 0
    for c in watch:
        sym = c.get("symbol")
        prev = prev_prices.get(sym)
        cur = c.get("price")
        delta = round((cur - prev) / prev * 100, 2) if (prev and cur) else None
        if delta is not None:
            changed += 1
        rows.append({"symbol": sym, "prev": prev, "cur": cur, "delta_pct": delta})
    return {"since": snapshot.get("fetched_at"), "rows": rows,
            "tracked": changed}


def find_prev_snapshot() -> Optional[Path]:
    """定位最近一份快照（不含当前小时已写入的）。"""
    if not SNAPSHOT_DIR.exists():
        return None
    files = sorted(SNAPSHOT_DIR.glob("*/*.json"))
    return files[-1] if files else None


# --------------------------------------------------------------------------- #
# 渲染（深色自包含 HTML）
# --------------------------------------------------------------------------- #

_CSS = """
:root{--bg:#0b1020;--panel:#121a33;--panel2:#0e1529;--line:#233156;
--txt:#dbe4ff;--muted:#8b9bc4;--up:#ff5d5d;--down:#3ddc97;--acc:#4da3ff}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font:14px/1.6 "Segoe UI",
"Microsoft YaHei",sans-serif;padding:28px}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:22px;background:linear-gradient(90deg,#4da3ff,#8f6bff);
-webkit-background-clip:text;background-clip:text;color:transparent;margin-bottom:4px}
.meta{color:var(--muted);font-size:12px;margin-bottom:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:14px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card .k{color:var(--muted);font-size:12px}
.card .v{font-size:20px;font-weight:600;margin-top:4px}
.card .s{font-size:12px;color:var(--muted);margin-top:2px}
h2{font-size:15px;color:var(--acc);margin:22px 0 8px;border-left:3px solid var(--acc);
padding-left:8px}
table{width:100%;border-collapse:collapse;background:var(--panel);
border-radius:10px;overflow:hidden;font-size:13px}
th{background:var(--panel2);color:var(--muted);font-weight:500;text-align:right;
padding:8px 10px;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
td{padding:7px 10px;border-top:1px solid var(--line);text-align:right;
font-variant-numeric:tabular-nums}
.up{color:var(--up)}.down{color:var(--down)}.muted{color:var(--muted)}
.tag{display:inline-block;background:var(--panel2);border:1px solid var(--line);
border-radius:6px;padding:1px 8px;font-size:12px;margin:2px 4px 2px 0}
.flag{background:var(--panel2);border:1px solid var(--line);border-radius:8px;
padding:8px 12px;margin:6px 0;font-size:13px}
.regime{font-size:18px;font-weight:700}
.disclaim{margin-top:26px;color:var(--muted);font-size:11px;border-top:1px solid var(--line);
padding-top:10px}
"""


def _pct_cell(v: Optional[float]) -> str:
    if v is None:
        return '<td class="muted">—</td>'
    cls = "up" if v > 0 else ("down" if v < 0 else "")
    return f'<td class="{cls}">{fmt_pct(v)}</td>'


def _fmt_price(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"${v:,.6f}" if v < 1 else f"${v:,.2f}"


def render_html(snap: Dict[str, Any]) -> str:
    g = snap.get("global") or {}
    b = snap.get("breadth") or {}
    reg = snap.get("regime") or {}
    fg = snap.get("fear_greed") or {}
    prev = snap.get("diff_prev") or {}
    mcap_chg = g.get("market_cap_change_percentage_24h")

    mcap_chg_html = (
        f'<span class="{"up" if mcap_chg > 0 else "down"}">{fmt_pct(mcap_chg)}</span>'
        if mcap_chg is not None else "—")

    cards = f"""
    <div class="card"><div class="k">总市值</div><div class="v">{fmt_usd(g.get('total_market_cap'))}</div>
      <div class="s">24h {mcap_chg_html}</div></div>
    <div class="card"><div class="k">24h 总成交</div><div class="v">{fmt_usd(g.get('total_volume'))}</div>
      <div class="s">活跃币种 {g.get('active_cryptocurrencies') or '—'}</div></div>
    <div class="card"><div class="k">BTC / ETH 占比</div><div class="v">
      {fmt_pct(g.get('btc_dominance'), False)} / {fmt_pct(g.get('eth_dominance'), False)}</div></div>
    <div class="card"><div class="k">市场宽度 (Top {b.get('sample')})</div>
      <div class="v">{b.get('up_pct_24h', 0)}% <span style="font-size:12px">上涨</span></div>
      <div class="s">1h 上涨 {b.get('up_pct_1h', 0)}% · 上涨 {b.get('up_24h')} / 下跌 {b.get('down_24h')}</div></div>"""

    regime_html = f"""
    <div class="card" style="grid-column:1/-1">
      <div class="k">市场状态判定</div>
      <div class="v regime">{esc(reg.get('label', '—'))}</div>
      <div class="s">{' · '.join(esc(v) for v in reg.get('votes', [])) or '无显著信号'}</div>
      <div class="s">恐惧贪婪指数：{esc(fg.get('label', '—'))} ({fg.get('value', '—')})</div>
    </div>"""

    watch_rows = ""
    for c in snap.get("watchlist") or []:
        vol = c.get("total_volume") or 0
        mcap = c.get("market_cap") or 0
        turn = f"{vol / mcap * 100:.0f}%" if mcap else "—"
        watch_rows += (
            f"<tr><td>{esc(c.get('symbol'))}<span class='muted'> #{c.get('rank') or '—'}</span></td>"
            f"<td>{esc(c.get('name') or '')}</td>"
            f"<td>{_fmt_price(c.get('price'))}</td>"
            + _pct_cell(c.get("p1h")) + _pct_cell(c.get("p24h"))
            + _pct_cell(c.get("p7d"))
            + f"<td class='muted'>{fmt_usd(mcap)}</td><td class='muted'>{turn}</td></tr>")

    prev_rows = ""
    if prev.get("rows"):
        for r in prev["rows"]:
            if r.get("prev") is None:
                prev_rows += (f"<tr><td>{esc(r.get('symbol'))}</td>"
                              f"<td class='muted'>—</td><td class='muted'>—</td>"
                              f"<td class='muted'>新跟踪</td></tr>")
            else:
                prev_rows += (f"<tr><td>{esc(r.get('symbol'))}</td>"
                              f"<td class='muted'>{_fmt_price(r.get('prev'))}</td>"
                              f"<td>{_fmt_price(r.get('cur'))}</td>"
                              + _pct_cell(r.get("delta_pct")) + "</tr>")

    anomaly_rows = ""
    for a in snap.get("anomalies") or []:
        anomaly_rows += (
            f"<tr><td>{esc(a['symbol'])}<span class='muted'> #{a.get('rank') or '—'}</span></td>"
            f"<td>{_fmt_price(a.get('price'))}</td>"
            + _pct_cell(a.get("p1h")) + _pct_cell(a.get("p24h"))
            + _pct_cell(a.get("p7d"))
            + f"<td class='muted'>{a.get('turnover_pct') or '—'}%</td>"
            + f"<td>{esc(' / '.join(a['reasons']))}</td></tr>")

    tvl_rows = ""
    for chain, d in (snap.get("chain_tvl") or {}).items():
        tvl = d.get("tvl") if isinstance(d, dict) else d
        chg = d.get("change_24h") if isinstance(d, dict) else None
        tvl_rows += (f"<tr><td>{esc(chain)}</td><td>{fmt_usd(tvl)}</td>"
                     + _pct_cell(chg) + "</tr>")

    errors_html = ""
    if snap.get("errors"):
        errors_html = "<h2>⚠️ 数据源异常</h2>" + "".join(
            f'<div class="flag">{esc(e)}</div>' for e in snap["errors"])

    title = f"宏观市场扫描 · {snap.get('fetched_at', '')[:16]}"
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>{esc(title)}</title><style>{_CSS}</style></head><body><div class="wrap">
<h1>{esc(title)}</h1>
<div class="meta">引擎 macro-scan v1.0 · 数据源：{esc(', '.join(snap.get('sources_used') or []))}
 · 快照：data/macro/{esc(snap.get('snapshot_file', ''))}</div>
<div class="grid">{cards}{regime_html}</div>
<h2>重点币种 (Watchlist · {len(snap.get('watchlist') or [])})</h2>
<table><tr><th>币种</th><th>名称</th><th>价格</th><th>1h</th><th>24h</th><th>7d</th>
<th>市值</th><th>换手</th></tr>{watch_rows}</table>
{f"<h2>环比上一快照（{esc(prev.get('since', '')[:16])} · 追踪 {prev.get('tracked', 0)} 币）</h2><table><tr><th>币种</th><th>前值</th><th>现值</th><th>Δ%</th></tr>{prev_rows}</table>" if prev_rows else ""}
{f"<h2>🚨 异动检测（阈值 1h ±{snap['thresholds'].get('h1_pct')}% / 24h ±{snap['thresholds'].get('h24_pct')}%）</h2><table><tr><th>币种</th><th>价格</th><th>1h</th><th>24h</th><th>7d</th><th>换手</th><th>触发</th></tr>{anomaly_rows}</table>" if anomaly_rows else "<h2>🚨 异动检测</h2><div class='flag'>Top 币种未触发异动阈值</div>"}
{f"<h2>链 TVL (DefiLlama)</h2><table><tr><th>链</th><th>TVL</th><th>24h</th></tr>{tvl_rows}</table>" if tvl_rows else ""}
{errors_html}
<div class="disclaim">本报告由定时任务自动生成，仅供研究参考，不构成投资建议。
历史快照：data/macro/ · 归档：reports/macro/archive/</div>
</div></body></html>"""


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #


def run(config_path: Path, quiet: bool) -> int:
    logger = setup_logging(quiet)
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    top_n = int(cfg.get("top_n", 100))
    watch_ids = list(cfg.get("watchlist") or [])
    chains = list(cfg.get("chains") or [])
    thr = cfg.get("anomaly") or {}
    regime_thr = cfg.get("regime") or {}
    src_on = cfg.get("sources") or {}

    errors: List[str] = []
    sources_used: List[str] = []
    now = datetime.now(timezone.utc).astimezone()
    t0 = time.time()
    logger.info("macro scan start (top_n=%d watchlist=%d chains=%d)",
                top_n, len(watch_ids), len(chains))

    # ---- 采集 ----
    cg = CoinGeckoClient()
    dl = DefiLlamaClient()

    g = fetch_global(cg, errors)
    if g:
        sources_used.append("coingecko/global")
    coins = fetch_top_coins(cg, top_n, errors)
    if coins:
        sources_used.append("coingecko/markets")

    # watchlist：优先从 Top N 取，缺的补抓
    by_id = {c.get("id"): c for c in coins}
    missing = [i for i in watch_ids if i not in by_id]
    extra = fetch_watchlist_extra(cg, missing, errors)
    for c in extra:
        by_id[c["id"]] = c
    watch_raw = [by_id[i] for i in watch_ids if i in by_id]
    if missing and extra:
        sources_used.append("coingecko/watchlist")

    chain_tvl: Dict[str, Any] = {}
    if src_on.get("defillama", True) and chains:
        chain_tvl = fetch_chain_tvl(dl, chains, errors)
        if chain_tvl:
            sources_used.append("defillama/tvl")

    fg = None
    if src_on.get("fear_greed", False):
        fg = fetch_fear_greed(errors)
        if fg:
            sources_used.append("alternative.me/fng")

    if not coins and not g:
        logger.error("所有核心数据源失败: %s", errors)
        return 1

    # ---- 分析 ----
    breadth = analyze_breadth(coins)
    regime = judge_regime(g, breadth, regime_thr)
    anomalies = detect_anomalies(coins, thr)
    watch = [{
        "id": c.get("id"), "symbol": c.get("symbol"), "name": c.get("name"),
        "rank": c.get("market_cap_rank"), "price": c.get("current_price"),
        "p1h": c.get("price_change_percentage_1h"),
        "p24h": c.get("price_change_percentage_24h_currency")
        or c.get("price_change_percentage_24h"),
        "p7d": c.get("price_change_percentage_7d"),
        "market_cap": c.get("market_cap"),
        "total_volume": c.get("total_volume"),
    } for c in watch_raw]

    # ---- 环比上一快照 ----
    prev_path = find_prev_snapshot()
    diff = {}
    if prev_path:
        try:
            prev_snap = json.loads(prev_path.read_text(encoding="utf-8"))
            diff = diff_prev_snapshot(prev_snap, watch)
        except Exception as e:  # noqa: BLE001
            errors.append(f"prev_snapshot/{prev_path.name}: {e}")

    # ---- 快照落盘 ----
    stamp = now.strftime("%Y%m%dT%H%M")
    day_dir = SNAPSHOT_DIR / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    snap_file = day_dir / f"{now.strftime('%H%M')}.json"
    snap = {
        "fetched_at": now.isoformat(timespec="seconds"),
        "snapshot_file": f"{now.strftime('%Y-%m-%d')}/{snap_file.name}",
        "duration_s": round(time.time() - t0, 1),
        "sources_used": sources_used,
        "global": g,
        "breadth": breadth,
        "regime": regime,
        "fear_greed": fg,
        "watchlist": watch,
        "anomalies": anomalies,
        "chain_tvl": chain_tvl,
        "diff_prev": diff,
        "thresholds": thr,
        "errors": errors,
    }
    snap_file.write_text(
        json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- 报告 ----
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "latest.html").write_text(render_html(snap),
                                             encoding="utf-8")
    arch = REPORT_DIR / "archive"
    arch.mkdir(exist_ok=True)
    (arch / f"{now.strftime('%Y-%m-%d_%H%M')}.html").write_text(
        render_html(snap), encoding="utf-8")

    # ---- 控制台摘要 ----
    logger.info("regime=%s breadth_up=%.1f%% mcap24h=%s anomalies=%d "
                "watch=%d tvl_chains=%d errors=%d (%.1fs) -> %s",
                regime["label"], breadth.get("up_pct_24h", 0),
                fmt_pct(g.get("market_cap_change_percentage_24h")),
                len(anomalies), len(watch), len(chain_tvl), len(errors),
                snap["duration_s"], snap_file)
    if anomalies and not quiet:
        for a in anomalies[:5]:
            logger.info("  异动 %s: %s", a["symbol"], " / ".join(a["reasons"]))
    logger.info("macro scan done")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="每小时宏观市场扫描")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    return run(Path(args.config), args.quiet)


if __name__ == "__main__":
    sys.exit(main())
