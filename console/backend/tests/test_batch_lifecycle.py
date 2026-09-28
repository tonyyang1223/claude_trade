"""批次生命周期回归测试：异常 / 中断 / 强杀后，``ingest_batch`` 不得残留 ``status='running'``。

背景（真实缺陷）：批次开始后进程被 kill / 中断，收尾 ``finish_batch`` 未执行 →
``status`` 永久停在 ``running`` → H7 健康度总览把**早已结束**的批次显示成「正在跑」的假信号。

修复（两层）：
1. 写入侧 ``etl_common.running_batch``：``try/finally`` 兜底，异常/中断也落终态；
2. 启动侧 ``etl_common.reap_stale_batches``：持写锁时把历史 ``running`` 行回收为 ``interrupted``。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core import paths  # noqa: F401  确保项目根入 sys.path（scripts 属于命名空间包）
from scripts.history import etl_common as ec
from scripts.history.init_db import apply_schema


@pytest.fixture
def conn(tmp_path: Path):
    """独立临时库 + 完整 schema（不触碰真实历史库）。"""
    c = ec.connect(tmp_path / "lifecycle.duckdb")
    apply_schema(c, verbose=False)
    try:
        yield c
    finally:
        c.close()


def _batch(conn, batch_id: str):
    """返回 ``(status, finished_at, rows_loaded)``；不存在返回 ``None``。"""
    rows = conn.execute(
        "SELECT status, finished_at, rows_loaded FROM ingest_batch WHERE batch_id = ?",
        [batch_id],
    ).fetchall()
    return rows[0] if rows else None


# --------------------------------------------------------------------------
# 1) running_batch：正常 / 异常 / 中断 三种收尾
# --------------------------------------------------------------------------
def test_running_batch_success_on_normal_exit(conn):
    with ec.running_batch(conn, "b-ok", "test", "t") as box:
        box["rows"] = 7
    status, finished, rows = _batch(conn, "b-ok")
    assert status == "success"
    assert finished is not None
    assert rows == 7


def test_running_batch_failed_on_exception(conn):
    with pytest.raises(RuntimeError):
        with ec.running_batch(conn, "b-fail", "test", "t") as box:
            box["rows"] = 3
            raise RuntimeError("boom")
    status, finished, rows = _batch(conn, "b-fail")
    assert status == "failed"          # 普通异常 → failed，且异常原样向上抛
    assert finished is not None
    assert rows == 3


def test_running_batch_interrupted_on_keyboard_interrupt(conn):
    with pytest.raises(KeyboardInterrupt):
        with ec.running_batch(conn, "b-int", "test", "t") as box:
            box["rows"] = 1
            raise KeyboardInterrupt()
    status, finished, _ = _batch(conn, "b-int")
    assert status == "interrupted"     # Ctrl-C → interrupted（不是 failed）
    assert finished is not None


# --------------------------------------------------------------------------
# 2) reap_stale_batches：回收悬挂批次
# --------------------------------------------------------------------------
def test_reap_stale_batches_marks_interrupted(conn):
    ec.start_batch(conn, "b-hung", "test", "t")   # 模拟被强杀：只有 started，无 finish
    assert _batch(conn, "b-hung")[0] == "running"

    reaped = ec.reap_stale_batches(conn)
    assert "b-hung" in reaped

    status, finished, _ = _batch(conn, "b-hung")
    assert status == "interrupted"
    assert finished is None            # 不伪造结束时间
    # 幂等：再回收不会重复命中
    assert ec.reap_stale_batches(conn) == []


def test_reap_leaves_terminal_batches_untouched(conn):
    with ec.running_batch(conn, "b-done", "test", "t"):
        pass
    assert ec.reap_stale_batches(conn) == []
    assert _batch(conn, "b-done")[0] == "success"


def test_reap_respects_stale_threshold(conn):
    ec.start_batch(conn, "b-recent", "test", "t")
    # 阈值很大 → 视为「刚开、可能仍活跃」→ 不回收
    assert ec.reap_stale_batches(conn, stale_seconds=10 ** 6) == []
    assert _batch(conn, "b-recent")[0] == "running"


# --------------------------------------------------------------------------
# 3) 端到端：一次增量运行后，库中不残留任何 running 批次
# --------------------------------------------------------------------------
def test_ingest_run_leaves_no_running_batch(tmp_path: Path):
    db_path = tmp_path / "ct.duckdb"
    setup = ec.connect(db_path)
    apply_schema(setup, verbose=False)
    ec.start_batch(setup, "b-hung", "test", "t")   # 预置悬挂批次
    setup.close()

    scan_dir = tmp_path / "scan"
    macro_dir = tmp_path / "macro"
    scan_dir.mkdir()
    macro_dir.mkdir()

    from scripts.history.ingest_history import run_incremental

    run_incremental(db_path=db_path, scan_dir=scan_dir, macro_dir=macro_dir, verbose=False)

    check = ec.connect(db_path)
    try:
        running = check.execute(
            "SELECT COUNT(*) FROM ingest_batch WHERE status = 'running'"
        ).fetchone()[0]
        hung = check.execute(
            "SELECT status FROM ingest_batch WHERE batch_id = 'b-hung'"
        ).fetchone()[0]
        inc = check.execute(
            "SELECT status FROM ingest_batch WHERE batch_id = 'incremental-history'"
        ).fetchone()[0]
    finally:
        check.close()

    assert running == 0, "增量运行后不得残留 running 批次"
    assert hung == "interrupted", "悬挂批次应被启动时的回收逻辑置为 interrupted"
    assert inc == "success", "本次增量批次应以 success 收尾"
