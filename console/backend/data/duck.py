"""DuckDB 历史库连接管理（线程安全）—— 见 docs/history-db/ARCHITECTURE.md §7.6。

设计要点（为什么这样写）：
- 现有 router 全部是同步 ``def``，会被 Starlette 丢进线程池并发执行；而
  **DuckDB 的 Connection 不是线程安全的**，跨线程共享同一 Connection 会崩。
- 因此采用 DuckDB 官方推荐的「单进程基连接 + 每线程 ``cursor()``」模式：
  · ``get_base()``    —— 进程内**唯一**的基连接（double-checked locking 懒创建）；
  · ``read_conn()``   —— 每线程一个 ``cursor()``（``threading.local``），并发读互不阻塞；
  · 写操作          —— 全局 ``_write_lock`` 串行化（T03 只读，此处**预留**接口给 ETL）。
- 读连接一律以 ``read_only=True`` 打开：既避免与服务端/ETL 进程争写锁，也天然防止误写。
- 连接建立后尽力 ``LOAD fts;``（库内已有 FTS 索引时通常会自动加载，显式 LOAD 更稳）。

降级约定：本模块**绝不向上冒泡异常**（契合「绝不抛 500」）；``db_available()`` 只是
「能不能用 DB」的探针，任何失败一律返回 ``False``，由 ``get_repository()`` 回退文件直读。
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Optional

try:  # 沿用 src/research/database.py 的 HAS_DUCKDB guard 模式
    import duckdb  # type: ignore

    HAS_DUCKDB = True
except ImportError:  # pragma: no cover - 环境未装 duckdb 时
    duckdb = None  # type: ignore[assignment]
    HAS_DUCKDB = False

from core.config import HISTORY_DB_PATH

# --------------------------------------------------------------------------
# 模块级状态（进程内单例）
# --------------------------------------------------------------------------
_meta_lock = threading.RLock()      # 保护「基连接创建」与「写连接创建」
_write_lock = threading.Lock()      # 写操作全局串行（T03 无写，预留）
_local = threading.local()          # 每线程一个读 cursor
_base_conn: Optional[Any] = None    # 进程内唯一基连接（只读）
_base_key: Optional[tuple] = None   # 基连接对应的 (path, read_only)，用于路径变更时重建


def _try_load_fts(conn: Any) -> bool:
    """尽力加载 fts 扩展；失败不影响主流程（降级为 ILIKE 兜底由上层负责）。

    Returns:
        True 表示扩展已加载；False 表示不可用。
    """
    try:
        conn.execute("LOAD fts;")
        return True
    except Exception as exc:  # noqa: BLE001 - 扩展不可用时降级，不阻断读路径
        print(f"[duck] fts 扩展加载失败（检索将降级）：{exc}")
        return False


def _connect_read_only(db_path: Any) -> Any:
    """以只读方式打开历史库并尽力加载 fts；调用方负责异常兜底。"""
    conn = duckdb.connect(str(db_path), read_only=True)
    _try_load_fts(conn)
    return conn


def get_base() -> Any:
    """返回进程内唯一的**只读**基连接（double-checked locking 懒创建）。

    Raises:
        RuntimeError: 未安装 duckdb 时。
        duckdb.IOException: DB 文件缺失 / 无法只读打开时（由调用方决定回退）。
    """
    global _base_conn, _base_key
    if not HAS_DUCKDB:  # pragma: no cover - 受 get_repository 保护
        raise RuntimeError("未安装 duckdb 依赖，无法打开历史库")

    key = (str(HISTORY_DB_PATH), True)
    conn = _base_conn
    if conn is not None and _base_key == key:  # 快路径：无锁读取
        return conn

    with _meta_lock:  # 慢路径：二次检查后再创建
        if _base_conn is None or _base_key != key:
            _base_conn = _connect_read_only(HISTORY_DB_PATH)
            _base_key = key
        return _base_conn


def read_conn() -> Any:
    """返回**当前线程**的只读连接（基连接的 ``cursor()``，每线程一个）。

    DuckDB 约定：``connection.cursor()`` 返回指向同一数据库的全新连接，
    因此可安全地「一连接多线程各持一个 cursor」并发读。
    """
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = get_base().cursor()
        _local.conn = conn
    return conn


def write_lock() -> threading.Lock:
    """返回全局写锁（供 ETL 串行化写操作；T03 只读，仅预留）。"""
    return _write_lock


def open_write_connection() -> Any:
    """打开一个**读写**连接（供 ETL 使用）。

    T03 无写操作，此函数仅作预留：调用方须自行持有 ``write_lock()`` 以保证串行，
    且约定「服务端进程与 ETL 进程不同时打开同一 DB 的读写句柄」（§5.4）。
    """
    if not HAS_DUCKDB:  # pragma: no cover
        raise RuntimeError("未安装 duckdb 依赖，无法打开历史库")
    with _meta_lock:
        conn = duckdb.connect(str(HISTORY_DB_PATH), read_only=False)
        _try_load_fts(conn)
        return conn


def db_available() -> bool:
    """探针：DB 文件存在且可以只读打开、可执行查询时返回 True，否则 False。

    任何异常（文件缺失、只读打开失败、损坏）一律吞掉并返回 False，
    使 ``get_repository()`` 能无缝回退到文件直读。
    """
    if not HAS_DUCKDB:
        return False
    try:
        if not Path(HISTORY_DB_PATH).is_file():
            return False
        get_base().execute("SELECT 1").fetchone()
        return True
    except Exception as exc:  # noqa: BLE001 - 回退路径不得冒泡
        print(f"[duck] 历史库不可用（将回退文件直读）：{exc}")
        return False


def close_base() -> None:
    """关闭进程内基连接并清空当前线程的读 cursor（测试/优雅退出用）。"""
    global _base_conn, _base_key
    with _meta_lock:
        if _base_conn is not None:
            try:
                _base_conn.close()
            except Exception as exc:  # noqa: BLE001 - 关闭失败无需阻断
                print(f"[duck] 关闭基连接失败：{exc}")
        _base_conn = None
        _base_key = None
        _local.conn = None
