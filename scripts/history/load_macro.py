"""载入 macro：``macro_snapshot`` 主表 + 3 张列表子表（watchlist / anomaly / chain_tvl）。

映射依据：`docs/history-db/ARCHITECTURE.md` §4（映射策略）、§5（ETL 设计）。

数据源：``data/macro/<date>/<HHMM>.json``（实测 19 个日期、共 45 个快照）。

落表策略：
- 顶层标量 → ``macro_snapshot``；嵌套对象（``global/breadth/regime/diff_prev/thresholds``）存 JSON；
- 三个列表拆**独立子表**（``watchlist[14] / anomalies[10] / chain_tvl{6}``），便于 SQL 聚合；
- ``fear_greed`` 恒为 ``null`` → 存 ``NULL``，**不造数据**（§13-O4）；
- 子表按 ``(date, snapshot_time)`` 单元「事务内 DELETE + INSERT」，避免陈旧残留（§5.2 策略 B）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # 作为包导入
    from . import etl_common as ec
except ImportError:  # 直接以脚本运行
    import etl_common as ec  # type: ignore[no-redef]

SNAPSHOT_COLS = (
    "date", "snapshot_time", "fetched_at", "duration_s", "sources_used_json",
    "global_json", "breadth_json", "regime_json", "fear_greed_json", "diff_prev_json",
    "thresholds_json", "errors_json", "snapshot_file",
)
WATCHLIST_COLS = (
    "date", "snapshot_time", "coin_id", "symbol", "name", "rank", "price",
    "p1h", "p24h", "p7d", "market_cap", "total_volume",
)
ANOMALY_COLS = (
    "date", "snapshot_time", "row_idx", "symbol", "name", "rank", "price",
    "p1h", "p24h", "p7d", "turnover_pct", "reasons_json", "strength",
)
CHAIN_TVL_COLS = (
    "date", "snapshot_time", "chain", "tvl", "tvl_change_24h", "tvl_change_7d",
    "protocols_count", "confidence", "ts",
)

_SNAPSHOT_SQL = f"""
INSERT INTO macro_snapshot ({", ".join(SNAPSHOT_COLS)})
VALUES ({", ".join(["?"] * len(SNAPSHOT_COLS))})
ON CONFLICT (date, snapshot_time) DO UPDATE SET
    fetched_at=EXCLUDED.fetched_at, duration_s=EXCLUDED.duration_s,
    sources_used_json=EXCLUDED.sources_used_json, global_json=EXCLUDED.global_json,
    breadth_json=EXCLUDED.breadth_json, regime_json=EXCLUDED.regime_json,
    fear_greed_json=EXCLUDED.fear_greed_json, diff_prev_json=EXCLUDED.diff_prev_json,
    thresholds_json=EXCLUDED.thresholds_json, errors_json=EXCLUDED.errors_json,
    snapshot_file=EXCLUDED.snapshot_file
"""
_WATCHLIST_SQL = (
    f"INSERT INTO macro_watchlist ({', '.join(WATCHLIST_COLS)}) "
    f"VALUES ({', '.join(['?'] * len(WATCHLIST_COLS))})"
)
_ANOMALY_SQL = (
    f"INSERT INTO macro_anomaly ({', '.join(ANOMALY_COLS)}) "
    f"VALUES ({', '.join(['?'] * len(ANOMALY_COLS))})"
)
_CHAIN_TVL_SQL = (
    f"INSERT INTO macro_chain_tvl ({', '.join(CHAIN_TVL_COLS)}) "
    f"VALUES ({', '.join(['?'] * len(CHAIN_TVL_COLS))})"
)


def _as_float(value: Any) -> Optional[float]:
    """尽力转 float；``None``/无法转换 → ``None``（不填 0）。"""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
    """尽力转 int；``None``/无法转换 → ``None``（不填 0）。"""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def list_macro_snapshots(macro_dir: Optional[Path] = None) -> List[Tuple[str, str, Path]]:
    """列出全部宏观快照，返回按 ``(date, HHMM)`` 升序的 ``(date, snapshot_time, path)``。"""
    root = macro_dir or ec.MACRO_DIR
    if not root.is_dir():
        return []
    found: List[Tuple[str, str, Path]] = []
    for day_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        date = ec.parse_date(day_dir.name)
        if date is None:
            continue
        for snap in sorted(day_dir.glob("*.json")):
            found.append((day_dir.name, snap.stem, snap))
    return found


def _replace_macro_unit(
    conn: Any,
    date: str,
    snapshot_time: str,
    watch_rows: List[List[Any]],
    anomaly_rows: List[List[Any]],
    chain_rows: List[List[Any]],
) -> None:
    """以 ``(date, snapshot_time)`` 为事务边界替换三张子表（DELETE + INSERT）。"""
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(
            "DELETE FROM macro_watchlist WHERE date = ? AND snapshot_time = ?",
            [date, snapshot_time],
        )
        conn.execute(
            "DELETE FROM macro_anomaly WHERE date = ? AND snapshot_time = ?",
            [date, snapshot_time],
        )
        conn.execute(
            "DELETE FROM macro_chain_tvl WHERE date = ? AND snapshot_time = ?",
            [date, snapshot_time],
        )
        if watch_rows:
            conn.executemany(_WATCHLIST_SQL, watch_rows)
        if anomaly_rows:
            conn.executemany(_ANOMALY_SQL, anomaly_rows)
        if chain_rows:
            conn.executemany(_CHAIN_TVL_SQL, chain_rows)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def load_macro(
    conn: Any,
    batch_id: str,
    macro_dir: Optional[Path] = None,
    verbose: bool = True,
) -> Dict[str, int]:
    """载入全部宏观快照（幂等）。

    Returns:
        各表写入行数统计（``macro_snapshot`` / ``macro_watchlist`` / ``macro_anomaly`` /
        ``macro_chain_tvl``）。
    """
    snapshots = list_macro_snapshots(macro_dir)
    counts: Dict[str, int] = {
        "macro_snapshot": 0,
        "macro_watchlist": 0,
        "macro_anomaly": 0,
        "macro_chain_tvl": 0,
    }
    if verbose:
        print(f"[load_macro] 待处理宏观快照 {len(snapshots)} 个")

    for date, snapshot_time, path in snapshots:
        payload = _read_json(path)
        if not isinstance(payload, dict):
            ec.record_file(conn, batch_id, path, 0, status="error")
            continue

        conn.execute(
            _SNAPSHOT_SQL,
            [
                date,
                snapshot_time,
                ec.parse_ts(payload.get("fetched_at")),
                _as_float(payload.get("duration_s")),
                ec.json_or_none(payload.get("sources_used")),
                ec.json_or_none(payload.get("global")),
                ec.json_or_none(payload.get("breadth")),
                ec.json_or_none(payload.get("regime")),
                # fear_greed 源恒为 null → 原样存 NULL（§13-O4）
                ec.json_or_none(payload.get("fear_greed")),
                ec.json_or_none(payload.get("diff_prev")),
                ec.json_or_none(payload.get("thresholds")),
                ec.json_or_none(payload.get("errors")),
                ec.to_rel(path),
            ],
        )
        counts["macro_snapshot"] += 1

        watch_rows = _watchlist_rows(date, snapshot_time, payload.get("watchlist"))
        anomaly_rows = _anomaly_rows(date, snapshot_time, payload.get("anomalies"))
        chain_rows = _chain_tvl_rows(date, snapshot_time, payload.get("chain_tvl"))
        _replace_macro_unit(conn, date, snapshot_time, watch_rows, anomaly_rows, chain_rows)
        counts["macro_watchlist"] += len(watch_rows)
        counts["macro_anomaly"] += len(anomaly_rows)
        counts["macro_chain_tvl"] += len(chain_rows)

        ec.record_file(conn, batch_id, path, 1, status="ok")

    if verbose:
        print("[load_macro] 完成：" + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return counts


def _read_json(path: Path) -> Optional[Any]:
    """读取宏观快照 JSON（失败返回 None，不抛异常）。"""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[load_macro] 读取 JSON 失败 {path}: {exc}")
        return None


def _watchlist_rows(date: str, snapshot_time: str, watchlist: Any) -> List[List[Any]]:
    """``watchlist[14]`` → ``macro_watchlist`` 参数行。"""
    rows: List[List[Any]] = []
    for item in watchlist or []:
        if not isinstance(item, dict):
            continue
        coin_id = item.get("id") or item.get("coin_id")
        if not coin_id:
            continue
        rows.append(
            [
                date,
                snapshot_time,
                coin_id,
                item.get("symbol"),
                item.get("name"),
                _as_int(item.get("rank")),
                _as_float(item.get("price")),
                _as_float(item.get("p1h")),
                _as_float(item.get("p24h")),
                _as_float(item.get("p7d")),
                _as_float(item.get("market_cap")),
                _as_float(item.get("total_volume")),
            ]
        )
    return rows


def _anomaly_rows(date: str, snapshot_time: str, anomalies: Any) -> List[List[Any]]:
    """``anomalies[10]`` → ``macro_anomaly`` 参数行（``row_idx`` 为列表内位置，兜底唯一键）。"""
    rows: List[List[Any]] = []
    for idx, item in enumerate(anomalies or []):
        if not isinstance(item, dict):
            continue
        rows.append(
            [
                date,
                snapshot_time,
                idx,
                item.get("symbol"),
                item.get("name"),
                _as_int(item.get("rank")),
                _as_float(item.get("price")),
                _as_float(item.get("p1h")),
                _as_float(item.get("p24h")),
                _as_float(item.get("p7d")),
                _as_float(item.get("turnover_pct")),
                ec.json_or_none(item.get("reasons")),
                _as_float(item.get("strength")),
            ]
        )
    return rows


def _chain_tvl_rows(date: str, snapshot_time: str, chain_tvl: Any) -> List[List[Any]]:
    """``chain_tvl{6}``（dict[chain → obj]）→ ``macro_chain_tvl`` 参数行。"""
    rows: List[List[Any]] = []
    if not isinstance(chain_tvl, dict):
        return rows
    for key, item in sorted(chain_tvl.items()):
        if not isinstance(item, dict):
            continue
        rows.append(
            [
                date,
                snapshot_time,
                item.get("chain") or key,
                _as_float(item.get("tvl")),
                _as_float(item.get("tvl_change_24h")),
                _as_float(item.get("tvl_change_7d")),
                _as_int(item.get("protocols_count")),
                _as_float(item.get("confidence")),
                ec.parse_ts(item.get("timestamp")),
            ]
        )
    return rows
