"""本地数据读取层（daily_scan JSON）。

集中封装：
- 最新扫描日期解析（委托 core.paths.resolve_scan_date）
- 读取 summary.json / top_800_light / top_50_detailed / by_category

所有解析失败均返回 None / 空结构，由上层 service 决定是否兜底，绝不抛 500。
复用 build_dashboard.collect_dashboard_data 的数据口径（见 scripts/analysis/build_dashboard.py）。
"""
from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core import paths


# --------------------------------------------------------------------------
# 基础读取
# --------------------------------------------------------------------------
def load_json(path: str) -> Optional[Any]:
    """读取 JSON 文件，失败返回 None。"""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001
        print(f"[loader] 读取 JSON 失败 {path}: {exc}")
        return None


def resolve_scan_date(date: Optional[str] = None) -> Optional[str]:
    return paths.resolve_scan_date(date)


def list_scan_dates() -> List[str]:
    return paths.list_scan_dates()


def _day_dir(date: str) -> str:
    return str(paths.DAILY_SCAN_DIR / date)


def _scan_days() -> List[str]:
    """扫描目录下的日期目录名（升序）。目录不存在时返回空列表。

    ``DAILY_SCAN_DIR`` 缺失或不可读（未采集 / 权限）时返回空而非抛异常，
    避免 ``?date=`` 等外部输入把一次普通读数据请求放大成 500 信封。
    """
    try:
        return sorted(os.listdir(paths.DAILY_SCAN_DIR))
    except OSError as exc:  # noqa: BLE001
        print(f"[loader] 扫描目录不可读 {paths.DAILY_SCAN_DIR}: {exc}")
        return []


def _is_valid_date(date: str) -> bool:
    """date 是否为可解析的 YYYY-MM-DD（外部入参未做存在性/格式校验）。"""
    try:
        datetime.strptime(date, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------
# summary / 800 轻量快照 / 板块 / 深度研究
# --------------------------------------------------------------------------
def load_summary(date: str) -> Optional[dict]:
    return load_json(os.path.join(_day_dir(date), "summary.json"))


def load_all_coins(date: str) -> List[dict]:
    """读取 top_800_light 全部币，按 id 去重（与 build_dashboard 口径一致）。"""
    fp = os.path.join(_day_dir(date), "top_800_light", "all_coins.json")
    coins = load_json(fp)
    if not coins:
        return []
    seen: set = set()
    out: List[dict] = []
    for c in coins:
        cid = c.get("id")
        if not cid or c.get("price_usd") is None or cid in seen:
            continue
        seen.add(cid)
        c["change_24h_pct"] = c.get("change_24h_pct") or 0.0
        c["change_7d_pct"] = c.get("change_7d_pct") or 0.0
        out.append(c)
    return out


def load_by_category_raw(date: str) -> Dict[str, List[dict]]:
    """读取 by_category：{cat: [原始 json 记录...]}。

    按 build_dashboard 口径：优先取近 7 天内覆盖币数最多的一天。
    ``date`` 非法（非 YYYY-MM-DD）时跳过该窗口扫描，直接用 ``date`` 当日目录。
    """
    cat_dir = os.path.join(_day_dir(date), "by_category")

    if _is_valid_date(date):
        best_cnt = -1
        min_day = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
        for d in reversed(_scan_days()):
            if d < min_day:
                continue
            p = os.path.join(str(paths.DAILY_SCAN_DIR), d, "by_category")
            if os.path.isdir(p):
                cnt = sum(len(files) for _, _, files in os.walk(p))
                if cnt > best_cnt:
                    cat_dir, best_cnt = p, cnt
    else:
        print(f"[loader] 非法日期 {date!r}，跳过 by_category 7 日窗口扫描")

    result: Dict[str, List[dict]] = {}
    if not os.path.isdir(cat_dir):
        return result
    for cat in sorted(os.listdir(cat_dir)):
        files = glob.glob(os.path.join(cat_dir, cat, "*.json"))
        members: List[dict] = []
        for fp in files:
            j = load_json(fp)
            if j:
                members.append(j)
        if members:
            result[cat] = members
    return result


def load_deep_raw(date: str) -> Dict[str, dict]:
    """读取 top_50_detailed：{coin_id: 原始 json}，当日优先、合并前一日。"""
    root = str(paths.DAILY_SCAN_DIR)
    days = _scan_days()
    prev_day: Optional[str] = None
    if date in days:
        i = days.index(date)
        prev_day = days[i + 1] if i + 1 < len(days) else None

    deep: Dict[str, dict] = {}
    for d in ([prev_day, date] if prev_day else [date]):
        dd = os.path.join(root, d, "top_50_detailed")
        if not os.path.isdir(dd):
            continue
        for fp in glob.glob(os.path.join(dd, "*.json")):
            j = load_json(fp)
            if not j:
                continue
            cid = j.get("coin_id")
            if cid:
                deep[cid] = j  # 当日覆盖前一日
    return deep


def find_coin_raw(date: str, coin_id: str) -> Optional[dict]:
    """在 top_50_detailed 与 by_category 中定位某币原始记录。"""
    # 1) top_50_detailed/<id>.json
    fp = os.path.join(_day_dir(date), "top_50_detailed", f"{coin_id}.json")
    j = load_json(fp)
    if j:
        return j
    # 2) 在 by_category 各文件里找 coin_id 匹配
    raw = load_by_category_raw(date)
    for members in raw.values():
        for m in members:
            if m.get("coin_id") == coin_id:
                return m
    return None
