#!/usr/bin/env python
"""链上代币分析 CLI 入口（设计文档 L1 编排入口）。

用法：
  # 按「链 + 合约地址」分析
  python scripts/chain/analyze_token.py bnb 0x… [--config x.yaml] [--format html,md,json]

  # 按「链 + 代币符号」分析（自动联网解析地址）
  python scripts/chain/analyze_token.py sol CAKE

  # 离线跑通框架（内置样例，不触网）
  python scripts/chain/analyze_token.py --demo --chain bnb --symbol CASHCAT

支持链：bnb / sol / robinhood（robinhood 为 EVM 兼容 Arbitrum Orbit 链）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 允许从仓库根目录直接运行
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.chain.orchestrator import analyze      # noqa: E402
from src.chain.renderers import render_html, render_markdown, render_json  # noqa: E402
from src.chain.types import Chain               # noqa: E402

_FORMATS = ("html", "md", "json")


def _print_summary(chain: str, result, decision: dict) -> None:
    sym = result.symbol or "—"
    print("=" * 60)
    print(f"  链: {chain.upper()}   代币: {sym}   ({result.name or '—'})")
    print(f"  地址: {result.address}")
    print(f"  综合分: {decision['total']:.1f}/10")
    print(f"  决策: {decision['decision']}")
    print(f"  风险: {decision['risk']}   建议仓位: {decision['position']}")
    for f in result.flags:
        print(f"  [{f.level.upper():4s}] {f.msg}")
    if decision["missing"]:
        print(f"  缺失维度(已排除加权): {', '.join(decision['missing'])}")
    if result.error:
        print(f"  ⚠ 注意: {result.error}")
    print("=" * 60)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="链上代币多维分析工具（可配置引擎）")
    ap.add_argument("chain_pos", nargs="?", help="链名(bnb/sol/robinhood)")
    ap.add_argument("query_pos", nargs="?", help="代币符号或合约地址")
    ap.add_argument("--chain", help="链名")
    ap.add_argument("--symbol", help="代币符号")
    ap.add_argument("--address", help="合约地址")
    ap.add_argument("--demo", action="store_true", help="离线样例模式(不触网)")
    ap.add_argument("--rpc", help="自定义 RPC 端点(覆盖默认)")
    ap.add_argument("--api-key", help="浏览器 API key(如 bscscan)")
    ap.add_argument("--config", help="分析配置 YAML 路径(覆盖内置默认)")
    ap.add_argument("--format", default="html",
                    help=f"输出格式: {','.join(_FORMATS)} 或 all（默认 html）")
    ap.add_argument("--out", help="输出路径前缀（自动补 .html/.md/.json）")
    args = ap.parse_args(argv)

    chain = args.chain or args.chain_pos
    if not chain:
        ap.error("必须指定链：--chain bnb|sol|robinhood，或位置参数 链 查询")
    query = args.address or args.symbol or args.query_pos
    if not query and not args.demo:
        ap.error("必须指定代币符号(--symbol)或合约地址(--address)，或位置参数 查询")

    try:
        Chain.parse(chain)
    except ValueError as e:
        ap.error(str(e))

    result, decision = analyze(
        chain, query or "", rpc=args.rpc, api_key=args.api_key, demo=args.demo,
        config=args.config,
    )
    _print_summary(chain, result, decision)

    fmts = [f.strip().lower() for f in args.format.split(",") if f.strip()]
    if "all" in fmts:
        fmts = list(_FORMATS)
    unknown = set(fmts) - set(_FORMATS)
    if unknown:
        ap.error(f"未知格式: {sorted(unknown)}（支持 html/md/json/all）")

    out = args.out or str(ROOT / "reports" / "chain_token_analysis"
                          / f"{chain}_{(result.symbol or 'token')}")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    saved = []
    for fmt in fmts:
        if fmt == "html":
            p = f"{out}.html"
            Path(p).write_text(render_html(result, decision), encoding="utf-8")
        elif fmt == "md":
            p = f"{out}.md"
            Path(p).write_text(render_markdown(result, decision), encoding="utf-8")
        elif fmt == "json":
            p = f"{out}.json"
            Path(p).write_text(render_json(result, decision), encoding="utf-8")
        saved.append(p)
        print(f"  ✅ {fmt} 报告已生成: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
