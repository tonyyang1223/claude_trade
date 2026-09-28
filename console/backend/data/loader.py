"""本地数据读取层（facade）—— 委托到 ``data.repository`` 的仓储实现。

本模块是**唯一入口**（``services/*`` / ``routers/*`` 只认这里），公开函数名与签名
**逐字保持不变**，内部委托 ``get_repository()``，从而在「文件直读」与「DuckDB 读取」
之间无缝切换、产出同构数据（见 docs/history-db/ARCHITECTURE.md §7.5）。

- ``load_json`` 是纯文件工具，与仓储无关，原样保留。
- 其余函数一律 ``get_repository().<method>(...)``。

所有解析失败均返回 ``None`` / 空结构，由上层 service 决定是否兜底，绝不抛 500。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from data.repository import get_repository


# --------------------------------------------------------------------------
# 基础读取（纯文件工具，原样保留）
# --------------------------------------------------------------------------
def load_json(path: str) -> Optional[Any]:
    """读取 JSON 文件，失败返回 None。"""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001
        print(f"[loader] 读取 JSON 失败 {path}: {exc}")
        return None


# --------------------------------------------------------------------------
# 数据读取（委托仓储：文件直读 ↔ DuckDB）
# --------------------------------------------------------------------------
def resolve_scan_date(date: Optional[str] = None) -> Optional[str]:
    return get_repository().resolve_scan_date(date)


def list_scan_dates() -> List[str]:
    return get_repository().list_scan_dates()


def load_summary(date: str) -> Optional[dict]:
    return get_repository().load_summary(date)


def load_all_coins(date: str) -> List[dict]:
    """读取 top_800_light 全部币，按 id 去重（与 build_dashboard 口径一致）。"""
    return get_repository().load_all_coins(date)


def load_by_category_raw(date: str) -> Dict[str, List[dict]]:
    """读取 by_category：``{cat: [原始 json 记录...]}``（含 7 日窗口解析）。"""
    return get_repository().load_by_category_raw(date)


def load_deep_raw(date: str) -> Dict[str, dict]:
    """读取 top_50_detailed：``{coin_id: 原始 json}``，当日优先、合并次日。"""
    return get_repository().load_deep_raw(date)


def find_coin_raw(date: str, coin_id: str) -> Optional[dict]:
    """在 top_50_detailed 与 by_category 中定位某币原始记录。"""
    return get_repository().find_coin_raw(date, coin_id)
