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
BACKEND_DIR = Path(__file__).resolve().parents[1]       # console/backend
APP_DIR = Path(__file__).resolve().parents[2]          # console
PROJECT_ROOT = Path(__file__).resolve().parents[3]      # claude_trading

# 注入项目根到 sys.path（最靠前，确保优先命中 src）
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def ensure_project_root() -> None:
    """幂等地确保项目根在 sys.path 中（供其他模块显式调用）。"""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))


# --------------------------------------------------------------------------
# 数据与缓存目录
# --------------------------------------------------------------------------
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
DAILY_SCAN_DIR = DATA_DIR / "reports" / "daily_scan"
RAW_SERVER_DIR = DATA_DIR / "raw_server"
CACHE_DIR = APP_DIR / "backend" / "cache"

for _d in (CACHE_DIR,):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def resolve_scan_date(date: str | None = None) -> str | None:
    """解析最新扫描日期。

    - 传入合法 ``YYYY-MM-DD`` 且对应目录存在 → 原样返回；
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
