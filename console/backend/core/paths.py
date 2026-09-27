"""路径常量集中管理 + 项目根注入 sys.path。

所有后端模块在导入本文件时会自动把「项目根」(claude_trading) 注入
``sys.path``，从而可以 ``import src`` 复用项目既有分析模块，严禁重写核心逻辑。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 目录推导:
#   console/backend/core/paths.py
#     parents[0] = console/backend/core
#     parents[1] = console/backend
#     parents[2] = console
#     parents[3] = claude_trading  <-- 项目根
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# 注入项目根到 sys.path（最靠前，确保优先命中 src）
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 扫描数据目录：data/reports/daily_scan/<YYYY-MM-DD>/
DAILY_SCAN_DIR = PROJECT_ROOT / "data" / "reports" / "daily_scan"


def resolve_scan_date(date: str | None = None) -> str | None:
    """解析扫描日期。

    - 传入非空且非 ``latest`` 的日期 → **原样返回**（不校验目录是否存在，
      读取失败时由上层按「数据缺失」兜底）；
    - 缺省或 ``latest`` → 取 ``DAILY_SCAN_DIR`` 下字典序最大、且含 ``summary.json`` 的目录；
    - 无可用目录 → 返回 ``None``。
    """
    if date and date != "latest":
        return date

    if not DAILY_SCAN_DIR.exists():
        return None

    candidates: list[str] = []
    for name in os.listdir(DAILY_SCAN_DIR):
        p = DAILY_SCAN_DIR / name
        if p.is_dir() and (p / "summary.json").exists():
            candidates.append(name)

    if not candidates:
        return None
    return sorted(candidates)[-1]


def list_scan_dates() -> list[str]:
    """返回所有可用扫描日期（字典序升序）。"""
    if not DAILY_SCAN_DIR.exists():
        return []
    out: list[str] = []
    for name in os.listdir(DAILY_SCAN_DIR):
        p = DAILY_SCAN_DIR / name
        if p.is_dir() and (p / "summary.json").exists():
            out.append(name)
    return sorted(out)
