#!/usr/bin/env python3
"""代币网页研究 CLI（Web Research）。

混合抓取单个代币的网页关键信息：CoinGecko API 主干（叙事/链接/情绪/上线时间）
+ 真实网页抓取（官网审计/团队、新闻/社区动态），支持可选 Scrapling/Playwright 渲染钩子。

示例：
    python scripts/research/token_web_research.py --token ethena
    python scripts/research/token_web_research.py --token bitcoin --format all
    python scripts/research/token_web_research.py --token solana --render --format html
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.research.web_research import TokenWebResearcher

DEFAULT_OUTPUT_DIR = project_root / "reports"


def render_markdown(p: "dict") -> str:
    lines = [
        f"# 代币网页研究档案：{p.get('name')} ({p.get('symbol')})",
        "",
        f"- CoinGecko ID: `{p.get('coin_id')}`",
        f"- 置信度: {p.get('confidence')}　数据源: {', '.join(p.get('sources') or [])}",
        f"- 抓取时间(UTC): {p.get('fetched_at')}",
        "",
    ]
    desc = p.get("description")
    if desc:
        lines += ["## 项目叙事 / 简介", "", desc[:2000], ""]
    cats = p.get("categories") or []
    if cats:
        lines += ["## 赛道 / 标签", "", ", ".join(cats), ""]
    gd = p.get("genesis_date")
    if gd:
        lines += ["## 上线时间", "", str(gd), ""]
    sent = p.get("sentiment") or {}
    if sent.get("up_pct") is not None:
        lines += [
            "## 社区情绪（CoinGecko 投票）",
            "",
            f"- 看涨: {sent.get('up_pct')}%　看跌: {sent.get('down_pct')}%",
            "",
        ]
    ol = p.get("official_links") or {}
    if ol:
        lines += ["## 官方链接", ""]
        if ol.get("website"):
            lines.append(f"- 官网: {ol['website']}")
        if ol.get("whitepaper"):
            lines.append(f"- 白皮书: {ol['whitepaper']}")
        if ol.get("explorers"):
            lines.append(f"- 浏览器: {', '.join(ol['explorers'][:3])}")
        if ol.get("github"):
            lines.append(f"- GitHub: {', '.join(ol['github'][:3])}")
        lines.append("")
    cl = p.get("community_links") or {}
    if cl:
        lines += ["## 社媒", ""]
        if cl.get("twitter"):
            lines.append(f"- Twitter: @{cl['twitter']}")
        if cl.get("telegram"):
            lines.append(f"- Telegram: {cl['telegram']}")
        if cl.get("reddit"):
            lines.append(f"- Reddit: {cl['reddit']}")
        lines.append("")
    ai = p.get("audit_info") or []
    if ai:
        lines += ["## 安全审计（官网命中，需人工核验）", ""]
        for a in ai:
            lines.append(f"- {a.get('firm')} — {a.get('note')}")
        lines.append("")
    ti = p.get("team_info") or {}
    if ti.get("hits"):
        lines += ["## 团队 / 融资线索", ""]
        for h in ti["hits"]:
            lines.append(f"- [{h.get('label')}] {h.get('snippet')}")
        lines.append("")
    news = p.get("news") or []
    if news:
        lines += [f"## 近期新闻 / 社区动态（{len(news)} 条）", ""]
        for n in news[:15]:
            title = n.get("title") or ""
            src = n.get("source") or ""
            lines.append(f"- [{src}] {title}")
        lines.append("")
    lines += [
        "---",
        "> 风险提示：以上仅为基于公开网页数据的整理，不构成任何投资建议。"
        "加密货币波动剧烈、存在归零与监管风险，请独立判断并自担风险。",
    ]
    return "\n".join(lines)


def render_html(p: "dict") -> str:
    name = p.get("name") or p.get("coin_id")
    sym = p.get("symbol") or ""
    rows = ""
    ol = p.get("official_links") or {}
    cl = p.get("community_links") or {}
    sent = p.get("sentiment") or {}
    ai = p.get("audit_info") or []
    ti = p.get("team_info") or {}
    news = p.get("news") or []

    def kv(k, v):
        return f"<tr><td class='k'>{k}</td><td>{v if v is not None else '—'}</td></tr>"

    rows += kv("CoinGecko ID", p.get("coin_id"))
    rows += kv("上线时间", p.get("genesis_date"))
    rows += kv("赛道/标签", ", ".join(p.get("categories") or []) or "—")
    rows += kv("社区情绪(看涨/看跌)",
               f"{sent.get('up_pct')}% / {sent.get('down_pct')}%" if sent.get("up_pct") is not None else "—")
    rows += kv("官网", ol.get("website") or "—")
    rows += kv("白皮书", ol.get("whitepaper") or "—")
    rows += kv("GitHub", ", ".join(ol.get("github") or []) or "—")
    rows += kv("Twitter", ("@" + cl["twitter"]) if cl.get("twitter") else "—")  # noqa
    rows += kv("Telegram", cl.get("telegram") or "—")
    rows += kv("Reddit", cl.get("reddit") or "—")
    rows += kv("审计机构命中", ", ".join(a["firm"] for a in ai) or "未命中（需人工核验）")
    rows += kv("团队/融资线索", "有" if ti.get("hits") else "—")
    rows += kv("新闻/动态条数", len(news))
    rows += kv("置信度", p.get("confidence"))
    rows += kv("数据源", ", ".join(p.get("sources") or []) or "—")

    desc = (p.get("description") or "")[:2000]
    news_html = "".join(
        f"<li><b>{n.get('source')}</b> {n.get('title') or ''}</li>" for n in news[:15]
    ) or "<li>当前环境未抓到（需渲染钩子或网络可达）。</li>"

    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>Web Research · {name}</title>
<style>
body{{background:#0b1020;color:#e6ecf7;font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:32px}}
h1{{color:#7cc4ff}} .sub{{color:#8aa0c2;margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;max-width:880px}} td{{border:1px solid #21304d;padding:8px 12px}}
td.k{{color:#9fb3d1;width:220px;background:#121a30}} .desc{{max-width:880px;background:#121a30;padding:14px;border-radius:8px;white-space:pre-wrap;line-height:1.6}}
.news{{max-width:880px}} .foot{{color:#6b7fa3;margin-top:24px;font-size:13px}}
</style></head><body>
<h1>{name} <span style="color:#8aa0c2">({sym})</span></h1>
<div class="sub">代币网页研究档案 · 抓取时间(UTC) {p.get('fetched_at')}</div>
<div class="desc">{desc}</div>
<p></p><table>{rows}</table>
<p></p><div class="news"><b>近期新闻 / 社区动态</b><ul>{news_html}</ul></div>
<div class="foot">风险提示：以上仅为基于公开网页数据的整理，不构成任何投资建议。</div>
</body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="代币网页研究（混合抓取）")
    parser.add_argument("--token", required=True, help="代币 id / 名称 / 符号（自由文本）")
    parser.add_argument("--format", choices=["json", "md", "html", "all"], default="json")
    parser.add_argument("--render", action="store_true", help="启用 Scrapling/Playwright 渲染钩子（抓 JS 重度页）")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT_DIR), help="输出目录（默认 reports/）")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    researcher = TokenWebResearcher(use_render=args.render)
    profile = researcher.analyze(args.token)
    data = profile.to_dict()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    written = []

    if args.format in ("json", "all"):
        jp = out_dir / f"web_research_{profile.coin_id}_{ts}.json"
        jp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        written.append(str(jp))
    if args.format in ("md", "all"):
        mp = out_dir / f"web_research_{profile.coin_id}_{ts}.md"
        mp.write_text(render_markdown(data), encoding="utf-8")
        written.append(str(mp))
    if args.format in ("html", "all"):
        hp = out_dir / f"web_research_{profile.coin_id}_{ts}.html"
        hp.write_text(render_html(data), encoding="utf-8")
        written.append(str(hp))

    # 终端摘要
    print(f"== 代币网页研究：{data.get('name')} ({data.get('symbol')}) ==")
    print(f"   CoinGecko ID : {data.get('coin_id')}")
    print(f"   置信度       : {data.get('confidence')}")
    print(f"   命中数据源   : {', '.join(data.get('sources') or []) or '无'}")
    print(f"   叙事长度     : {len(data.get('description') or '')} 字")
    print(f"   官方链接     : {data.get('official_links', {}).get('website') or '—'}")
    print(f"   审计机构命中 : {', '.join(a['firm'] for a in data.get('audit_info') or []) or '未命中'}")
    print(f"   新闻/动态    : {len(data.get('news') or [])} 条")
    print(f"   产出文件     : {', '.join(written)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
