"""历史库 ETL 公共工具：连接 / 批次 / 文件台账 / 时间与 JSON 归一。

设计依据：`docs/history-db/ARCHITECTURE.md` §5（回填 ETL 设计）、§12（共享知识）。

本模块只提供「无副作用」的公共设施，具体的表写入逻辑分别落在
``load_daily_scan.py`` / ``load_macro.py`` 中，由 ``backfill_history.py`` 编排。

关键约定（ARCHITECTURE §12）：
- 日期列一律 `DATE`（`YYYY-MM-DD`）；时间戳归一为「本地时间（Asia/Shanghai）朴素值」
  —— 带时区者（macro `fetched_at` 为 `+08:00`）先转本地再去时区，**不混 UTC**。
- `NULL` = 源确实缺失 → **原样存 NULL，不填 0**。
- 所有写入路径必须**幂等**：主表用 `ON CONFLICT (自然键) DO UPDATE`；
  会「缩水」的子表按自然键单元做「事务内 DELETE + INSERT」。
"""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

try:  # 沿用 src/research/database.py 的 HAS_DUCKDB guard 模式
    import duckdb

    HAS_DUCKDB = True
except ImportError:  # pragma: no cover - 环境未装 duckdb 时
    duckdb = None  # type: ignore[assignment]
    HAS_DUCKDB = False


# --------------------------------------------------------------------------
# 路径常量（scripts/history/<file>.py → 项目根 = parents[2]）
# --------------------------------------------------------------------------
HERE = Path(__file__).resolve()
PROJECT_ROOT: Path = HERE.parents[2]
DDL_PATH: Path = HERE.parent / "ddl.sql"
DB_PATH: Path = PROJECT_ROOT / "data" / "history" / "ct_history.duckdb"
DAILY_SCAN_DIR: Path = PROJECT_ROOT / "data" / "reports" / "daily_scan"
MACRO_DIR: Path = PROJECT_ROOT / "data" / "macro"

# 本地时区口径：全库统一 Asia/Shanghai（与采集端一致，避免跨日歧义）
LOCAL_TZ = timezone(timedelta(hours=8))

# 正文截断阈值（ARCHITECTURE §13-O2）：帖子 / 视频描述 8 KB，新闻 / RSS 不截断
BODY_TRUNCATE_DOC_TYPES = frozenset({"post", "video"})
BODY_TRUNCATE_LIMIT = 8000


def require_duckdb() -> None:
    """HAS_DUCKDB guard：缺失依赖时直接退出（契合 §5.1 步骤① 的「预检」）。

    Raises:
        SystemExit: 未安装 duckdb 时抛出，附带可执行的修复提示。
    """
    if not HAS_DUCKDB:
        raise SystemExit(
            "[history] 未检测到 duckdb 依赖，无法回填/建库。\n"
            "          修复：pip install 'duckdb>=1.1,<2.0'"
        )


def connect(db_path: Optional[Path] = None) -> "duckdb.DuckDBPyConnection":
    """打开（必要时创建）历史库连接，并尽力加载 FTS 扩展。

    Args:
        db_path: 库文件路径；默认 ``DB_PATH``（``data/history/ct_history.duckdb``）。

    Returns:
        duckdb 连接对象。

    Note:
        调用方负责 ``close()``。ETL 约定为「独立进程、独占写」，
        不做跨进程写并发协商（见 ARCHITECTURE §5.4）。
    """
    require_duckdb()
    target = Path(db_path) if db_path else DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(target))
    ensure_fts_extension(conn)
    return conn


def ensure_fts_extension(conn: "duckdb.DuckDBPyConnection") -> bool:
    """确保 fts 扩展已加载（扩展已本地缓存，无需联网）。

    Returns:
        True 表示扩展可用；False 表示加载失败（调用方应降级为 ILIKE 兜底检索）。
    """
    try:
        conn.execute("INSTALL fts")
        conn.execute("LOAD fts")
        return True
    except Exception as exc:  # noqa: BLE001 - 扩展不可用时降级，不阻断主流程
        print(f"[history] FTS 扩展加载失败，检索将降级为 ILIKE 兜底：{exc}")
        return False


# --------------------------------------------------------------------------
# 批次（ingest_batch）
# --------------------------------------------------------------------------
def new_batch_id(mode: str, now: Optional[datetime] = None) -> str:
    """生成**带时间戳**的批次号，形如 ``20260928T101500Z-backfill``（UTC 紧凑时间戳 + 模式）。

    用于**增量**入库（§6 / T05）：每次增量都应有独立、可追溯的批次行。
    """
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return f"{stamp.strftime('%Y%m%dT%H%M%SZ')}-{mode}"


def stable_batch_id(mode: str, scope: str) -> str:
    """生成**确定性**批次号：``<mode>-<scope>``，如 ``backfill-all``。

    用于**全量回填**：同一操作重跑时复用同一 ``batch_id``，使 ``ingest_batch``（PK=batch_id）
    与 ``ingest_file_log``（PK=batch_id,file_path）**主键天然幂等**——无需任何清理逻辑，
    就能满足「连续执行两次、各表行数不增」的硬约定（§12）。
    增量批次仍用 ``new_batch_id``（时间戳），保留每次增量的历史。
    """
    return f"{mode}-{scope}"


def start_batch(conn: "duckdb.DuckDBPyConnection", batch_id: str, mode: str, scope: str) -> None:
    """开批次：写入 ``ingest_batch``（status=running）。重跑同名批次时覆盖。"""
    conn.execute(
        """
        INSERT INTO ingest_batch (batch_id, started_at, mode, scope, status, rows_loaded, rows_rejected)
        VALUES (?, ?, ?, ?, 'running', 0, 0)
        ON CONFLICT (batch_id) DO UPDATE SET
            started_at=EXCLUDED.started_at,
            finished_at=NULL,
            mode=EXCLUDED.mode,
            scope=EXCLUDED.scope,
            status='running',
            rows_loaded=0,
            rows_rejected=0,
            error_msg=NULL
        """,
        [batch_id, local_now(), mode, scope],
    )


def finish_batch(
    conn: "duckdb.DuckDBPyConnection",
    batch_id: str,
    status: str,
    rows_loaded: int,
    rows_rejected: int = 0,
    error_msg: Optional[str] = None,
) -> None:
    """关批次：更新状态、完成时间与累计行数。``status`` ∈ running|success|partial|failed。"""
    conn.execute(
        """
        UPDATE ingest_batch
           SET finished_at=?, status=?, rows_loaded=?, rows_rejected=?, error_msg=?
         WHERE batch_id=?
        """,
        [local_now(), status, int(rows_loaded), int(rows_rejected), error_msg, batch_id],
    )


@contextmanager
def running_batch(
    conn: "duckdb.DuckDBPyConnection",
    batch_id: str,
    mode: str,
    scope: str,
) -> Iterator[Dict[str, int]]:
    """批次生命周期上下文：**开批次 → 业务 → 落终态**，异常/中断也不残留 ``running``。

    用法::

        with running_batch(conn, bid, "incremental", "history") as box:
            box["rows"] += load_something()
        # 正常退出 → 该批次 status=success

    ``box`` 为可变计数盒 ``{"rows": int, "rows_rejected": int}``，调用方按需累加；
    退出时自动写终态：

    - 正常返回 → ``success``；
    - ``KeyboardInterrupt`` / ``SystemExit`` → ``interrupted``；
    - 其它异常 → ``failed``（并**原样向上抛**，保持调用方的错误处理语义）；
    - ``finally`` 兜底：若异常路径里连 ``finish_batch`` 也失败了，再补一次
      落 ``interrupted``；若**连接已断**则放弃（届时由下次启动的
      :func:`reap_stale_batches` 回收）。

    Note:
        本上下文兜住的是**可捕获**的终止（异常 / Ctrl-C）。**进程被强杀**
        （SIGKILL；SIGTERM 默认行为）不会执行任何 Python 收尾，属另一层，
        由 :func:`reap_stale_batches` 兜底。
    """
    box: Dict[str, int] = {"rows": 0, "rows_rejected": 0}
    start_batch(conn, batch_id, mode, scope)
    terminal = False
    try:
        yield box
        finish_batch(conn, batch_id, "success", box["rows"], box["rows_rejected"])
        terminal = True
    except BaseException as exc:  # noqa: BLE001 - 含 KeyboardInterrupt / SystemExit
        status = "interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed"
        try:
            finish_batch(
                conn, batch_id, status, box["rows"], box["rows_rejected"], error_msg=str(exc)[:500]
            )
            terminal = True
        except Exception as inner:  # noqa: BLE001 - 收尾本身失败，交由 finally / reaper 兜底
            print(f"[etl_common] ⚠️ 批次 {batch_id} 落终态({status})失败：{inner}")
        raise
    finally:
        if not terminal:
            try:
                finish_batch(
                    conn, batch_id, "interrupted", box["rows"], box["rows_rejected"],
                    error_msg="进程中断/被 kill，finally 兜底落终态",
                )
            except Exception as inner:  # noqa: BLE001 - 连接可能已断，放弃并留给 reaper
                print(
                    f"[etl_common] ⚠️ 批次 {batch_id} finally 兜底失败（连接可能已断，"
                    f"交由下次 reap_stale_batches 回收）：{inner}"
                )


def reap_stale_batches(
    conn: "duckdb.DuckDBPyConnection",
    stale_seconds: int = 0,
    now: Optional[datetime] = None,
) -> List[str]:
    """把**悬挂批次**（``status='running' AND finished_at IS NULL``）回收为 ``interrupted``。

    成因：批次开始后进程被 **kill / SIGTERM / 断电**，收尾 ``finish_batch`` 未执行，
    ``status`` 永久停在 ``running`` —— 会让 H7 健康度总览把一行**早已结束**的批次
    显示成「正在跑」，误导运维（假信号）。

    Args:
        stale_seconds: 只回收 ``started_at`` 早于 ``now - stale_seconds`` 的行；
            ``0``（默认）= 回收**全部** ``running`` 行。默认值适用于「调用方已持有写锁」
            的 ETL 场景——此时任何 ``running`` 行都不可能属于活跃进程（活跃写进程会占住
            文件锁，别的进程连写连接都开不了）；若在**不持锁**的巡检场景调用，
            请传入合理阈值（如 ``3600``）。
        now: 参照时刻（缺省 :func:`local_now`）。

    Returns:
        被回收的 ``batch_id`` 列表（空表示无悬挂批次）。

    Note:
        ``finished_at`` 保持 ``NULL`` —— 进程被强杀时其真实结束时刻**无自证来源**，
        不伪造时间；仅把 ``status`` 落为 ``interrupted`` 即可消除「正在跑」的假信号。
    """
    cutoff = now or local_now()
    where = "status = 'running' AND finished_at IS NULL"
    params: List[Any] = []
    if stale_seconds and stale_seconds > 0:
        where += " AND started_at < ?"
        params.append(cutoff - timedelta(seconds=stale_seconds))
    rows = conn.execute(f"SELECT batch_id FROM ingest_batch WHERE {where}", params).fetchall()
    reaped: List[str] = [r[0] for r in rows]
    if reaped:
        conn.execute(
            "UPDATE ingest_batch SET status = 'interrupted', "
            "error_msg = COALESCE(error_msg, '进程中断/被 kill，收尾未执行（自动回收）') "
            f"WHERE {where}",
            params,
        )
    return reaped


def local_now() -> datetime:
    """当前本地（Asia/Shanghai）朴素时间，用于批次/台账时间戳。"""
    return datetime.now(LOCAL_TZ).replace(tzinfo=None, microsecond=0)


# --------------------------------------------------------------------------
# 逐文件台账（ingest_file_log）
# --------------------------------------------------------------------------
def file_md5(path: Path) -> str:
    """计算文件 md5（分块读取，避免大文件一次性入内存）。失败返回空串。"""
    try:
        digest = hashlib.md5()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as exc:  # noqa: BLE001
        print(f"[history] 计算 md5 失败 {path}: {exc}")
        return ""


def file_mtime(path: Path) -> Optional[datetime]:
    """文件修改时间（本地朴素），失败返回 None。"""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, LOCAL_TZ).replace(tzinfo=None)
    except OSError:
        return None


def to_rel(path: Path) -> str:
    """把绝对路径转成相对项目根的路径（正斜杠），用于 ``origin_path`` / ``file_path``。"""
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def record_file(
    conn: "duckdb.DuckDBPyConnection",
    batch_id: str,
    path: Path,
    rows: int,
    status: str = "ok",
    compute_md5: bool = True,
    processed_at: Optional[datetime] = None,
) -> None:
    """登记单个文件的处理结果（``ingest_file_log`` 幂等 upsert）。

    Args:
        status: ``ok`` | ``skipped`` | ``error``。
        compute_md5: 大文件（如 deep 单币 JSON）可按需关闭以省 IO。
        processed_at: 该文件的处理时间。**同一批次应传入同一个时间戳**
            （在批次开始时取一次 :func:`local_now`，批次内所有 ``record_file`` 复用），
            使 ``ingest_file_log`` 的「批次时间」语义可靠、可作次级排序键；
            缺省取当前时刻（每次调用各自取，仅适用于「单次单文件」的临时登记）。
    """
    conn.execute(
        """
        INSERT INTO ingest_file_log (batch_id, file_path, file_md5, file_mtime, rows, status, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (batch_id, file_path) DO UPDATE SET
            file_md5=EXCLUDED.file_md5,
            file_mtime=EXCLUDED.file_mtime,
            rows=EXCLUDED.rows,
            status=EXCLUDED.status,
            processed_at=EXCLUDED.processed_at
        """,
        [batch_id, to_rel(path), file_md5(path) if compute_md5 else "", file_mtime(path), int(rows), status, processed_at or local_now()],
    )


def _file_state_row(row: tuple) -> Dict[str, Any]:
    """``(file_path, md5, mtime, status, processed_at)`` → 状态 dict（去掉冗余 file_path）。"""
    return {"md5": row[1], "mtime": row[2], "status": row[3], "processed_at": row[4]}


def read_file_log(
    conn: "duckdb.DuckDBPyConnection",
    batch_id: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """读取**指定批次**的逐文件台账：``{file_path: {"md5","mtime","status","processed_at"}}``。

    ⚠️ 与旧实现的关键区别（可靠性修复）：
    旧实现用 ``WHERE processed_at = (SELECT MAX(processed_at) FROM ingest_file_log)``——
    把「全表最大 ``processed_at``」当作隐式批次键。但 ``processed_at`` 由 ``local_now()``
    **秒级截断**，其值取决于「该死循环里各文件分别调用的时刻」：同批次多文件恰好落在同一秒时
    「碰巧」能整批命中，一旦有**两个批次落在同一秒**（增量每 15 分钟一次，长跑/并发补跑时
    完全可能）就会**串批**取到错误行。现改为以稳定键 ``batch_id``（``ingest_file_log``
    复合主键首列）作键，**不再依赖任何时间戳**，彻底消除该隐患。

    Args:
        batch_id: 目标批次；``None`` 时取 ``ingest_batch`` 中 ``started_at`` 最新者
            （以 ``batch_id`` 兜底并列），而非 ``MAX(processed_at)``。

    Returns:
        ``{file_path: {"md5":..,"mtime":..,"status":..,"processed_at":..}}``；无数据返回 ``{}``。
    """
    if batch_id is None:
        picked = conn.execute(
            "SELECT batch_id FROM ingest_batch "
            "ORDER BY started_at DESC NULLS LAST, batch_id DESC LIMIT 1"
        ).fetchone()
        if not picked:
            return {}
        batch_id = picked[0]
    rows = conn.execute(
        "SELECT file_path, file_md5, file_mtime, status, processed_at "
        "FROM ingest_file_log WHERE batch_id = ?",
        [batch_id],
    ).fetchall()
    return {r[0]: _file_state_row(r) for r in rows}


def latest_file_states(conn: "duckdb.DuckDBPyConnection") -> Dict[str, Dict[str, Any]]:
    """**跨批次**取每个文件的最新状态：``{file_path: {"md5","mtime","status","processed_at"}}``。

    供增量入库（T05）判断「文件未变更 → 跳过」：同一文件可能先后被 ``backfill-all`` 与
    若干增量批次处理，故按 ``file_path`` 分区取 ``processed_at`` 最大的一行
    （并列时以 ``batch_id`` 大者为准），而非仅看「最近一个批次」。

    Note:
        采用窗口函数而非「全表 MAX 时间戳」自连接，保证在「多批次同秒」时结果仍确定。
    """
    rows = conn.execute(
        """
        SELECT file_path, file_md5, file_mtime, status, processed_at
        FROM (
            SELECT file_path, file_md5, file_mtime, status, processed_at,
                   ROW_NUMBER() OVER (
                       PARTITION BY file_path ORDER BY processed_at DESC, batch_id DESC
                   ) AS rn
            FROM ingest_file_log
        ) WHERE rn = 1
        """
    ).fetchall()
    return {r[0]: _file_state_row(r) for r in rows}


# --------------------------------------------------------------------------
# 类型归一：JSON / 时间戳 / 日期 / 文本
# --------------------------------------------------------------------------
def json_or_none(obj: Any) -> Optional[str]:
    """把 Python 对象序列化为 JSON 文本；``None`` 保持 ``None``（存 SQL NULL）。

    源缺失（如 macro ``fear_greed`` 恒为 null）一律落 ``NULL``，**不造数据**（§13-O4）。
    """
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def parse_ts(value: Any) -> Optional[datetime]:
    """把源里的各种时间表示归一为**本地朴素** ``datetime``。

    支持：ISO8601 字符串（含 ``+08:00`` 偏移）、RFC822（RSS ``published``）、
    Unix 秒级数值、``datetime`` 对象。无法解析返回 ``None``（原样留空，不猜测）。

    口径（§12 日期格式）：带时区者先转 ``Asia/Shanghai`` 再去时区；不混 UTC。
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return _to_local_naive(value)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), LOCAL_TZ).replace(tzinfo=None)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return _to_local_naive(datetime.fromisoformat(text.replace("Z", "+00:00")))
        except ValueError:
            pass
        try:  # RSS / HTTP 日期
            return _to_local_naive(parsedate_to_datetime(text))
        except (TypeError, ValueError):
            return None
    return None


def _to_local_naive(dt: datetime) -> datetime:
    """带时区的 datetime → 本地（Asia/Shanghai）朴素 datetime；朴素输入按本地原样返回。

    精度口径（§12）：**保留源时间的微秒，不做秒级截断**。DuckDB 1.5.5 的 TIMESTAMP
    本身为微秒精度（实测参数绑定与字面量均精确保留），若在此清零会导致 ``scan_day.scan_time``
    等源时间戳与文件态（FileRepository）不一致，破坏 R8 双模式等价（scaleTime 亚秒位差异）。

    注意：批次/台账时间戳（``local_now()``）仍走秒级截断，那是**操作时间**不是源时间，
    不参与 R8 比对，且秒级可避免台账粒度被放大。
    """
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(LOCAL_TZ).replace(tzinfo=None)


def parse_date(value: Any) -> Optional[date]:
    """把 ``YYYY-MM-DD`` 字符串（或 ``date``/``datetime``）解析为 ``date``。失败返回 None。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def truncate_text(text: Optional[str], doc_type: Optional[str]) -> Optional[str]:
    """按 doc_type 截断正文（ARCHITECTURE §13-O2）。

    帖子 / 视频描述截断到 8 KB（按字符数近似，避免按字节切断多字节字符）；
    新闻 / RSS 等不截断。``None`` 原样返回。
    """
    if text is None:
        return None
    if doc_type in BODY_TRUNCATE_DOC_TYPES and len(text) > BODY_TRUNCATE_LIMIT:
        return text[:BODY_TRUNCATE_LIMIT]
    return text


def md5_hex(text: str) -> str:
    """``md5`` 十六进制摘要（用于 doc_hash / content_id 等确定性代理键）。"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()
