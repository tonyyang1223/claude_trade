"""chain-forensic 一键 CLI（跨项目，设计文档 §7）。

pip install 后任意目录执行:
    chain-forensic --chain bnb --address 0x… [--config path.yaml] [--format md,html,json]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import analyze, render

_FORMATS = ("html", "md", "json")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="chain-forensic",
                                 description="链上代币取证分析（可配置引擎）")
    ap.add_argument("--chain", required=True, help="bnb | sol | robinhood")
    ap.add_argument("--address", help="合约地址")
    ap.add_argument("--symbol", help="代币符号")
    ap.add_argument("--query", help="地址或符号（与 --address/--symbol 等价）")
    ap.add_argument("--demo", action="store_true", help="离线样例模式")
    ap.add_argument("--config", help="分析配置 YAML（覆盖内置默认）")
    ap.add_argument("--format", default="html", help="html|md|json|all（默认 html）")
    ap.add_argument("--out", help="输出路径前缀（默认 ./chain_reports/<chain>_<sym>）")
    ap.add_argument("--rpc", help="自定义 RPC")
    args = ap.parse_args(argv)

    query = args.address or args.symbol or args.query
    if not query and not args.demo:
        ap.error("必须提供 --address 或 --symbol 或 --query（或用 --demo）")

    try:
        ctx, dec = analyze(args.chain, query or "", rpc=args.rpc,
                           demo=args.demo, config=args.config)
    except Exception as exc:  # noqa: BLE001
        print(f"[chain-forensic] 分析失败: {exc}", file=sys.stderr)
        return 2

    sym = ctx.symbol or "token"
    print("=" * 56)
    print(f"  {args.chain.upper()} · {sym} · {dec.get('decision')}")
    print(f"  综合分 {dec.get('total', 0):.1f}/10 · 风险 {dec.get('risk')}"
          f" · 建议仓位 {dec.get('position')}")
    for f in ctx.flags:
        print(f"  [{f.level.upper():4s}] {f.msg}")
    if dec.get("missing"):
        print(f"  缺失维度: {', '.join(dec['missing'])}")
    if ctx.error:
        print(f"  ⚠ {ctx.error}")
    print("=" * 56)

    fmts = list(_FORMATS) if "all" in args.format else \
        [f.strip().lower() for f in args.format.split(",") if f.strip()]
    unknown = set(fmts) - set(_FORMATS)
    if unknown:
        ap.error(f"未知格式: {sorted(unknown)}")
    out = Path(args.out) if args.out else Path("chain_reports") / f"{args.chain}_{sym}"
    out.parent.mkdir(parents=True, exist_ok=True)
    ext = {"html": "html", "md": "md", "json": "json"}
    for fmt in fmts:
        p = out.with_suffix(f".{ext[fmt]}")
        p.write_text(render(ctx, dec, fmt), encoding="utf-8")
        print(f"  ✅ {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
