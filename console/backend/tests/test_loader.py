"""data.loader.resolve_scan_date 单元测试（真实数据 + 受控 mock 双覆盖）。"""
from pathlib import Path

from core import paths
from data import loader


def test_resolve_scan_date_latest_uses_real_max_dir():
    # 真实数据：所有带 summary.json 的目录中字典序最大者为 2026-08-26
    assert loader.resolve_scan_date(None) == "2026-08-26"


def test_resolve_scan_date_explicit_existing_and_latest():
    assert loader.resolve_scan_date("2026-08-25") == "2026-08-25"
    assert loader.resolve_scan_date("latest") == "2026-08-26"


def test_resolve_scan_date_explicit_nonexistent_returns_as_is():
    # 实现不对显式日期做存在性校验（与 docstring 描述略有出入）；
    # 这里固定记录其实际行为，避免回归时静默改变语义。
    assert loader.resolve_scan_date("2099-01-01") == "2099-01-01"


def test_resolve_scan_date_with_mock_dirs(tmp_path):
    # 受控场景：构造若干带/不带 summary.json 的目录，验证「字典序最大且含 summary」。
    (tmp_path / "2024-01-01").mkdir()
    (tmp_path / "2024-01-01" / "x").write_text("no summary here")  # 无 summary.json
    (tmp_path / "2024-01-02").mkdir()
    (tmp_path / "2024-01-02" / "summary.json").write_text("{}")
    (tmp_path / "2024-01-05").mkdir()
    (tmp_path / "2024-01-05" / "summary.json").write_text("{}")
    (tmp_path / "2024-01-10").mkdir()
    (tmp_path / "2024-01-10" / "summary.json").write_text("{}")

    original = paths.DAILY_SCAN_DIR
    paths.DAILY_SCAN_DIR = tmp_path
    try:
        assert paths.resolve_scan_date(None) == "2024-01-10"
        assert paths.resolve_scan_date("latest") == "2024-01-10"
        # 显式存在的目录原样返回
        assert paths.resolve_scan_date("2024-01-05") == "2024-01-05"
        # 无 summary.json 的目录若被显式指定仍原样返回（实现不做存在性校验）
        assert paths.resolve_scan_date("2024-01-01") == "2024-01-01"
    finally:
        paths.DAILY_SCAN_DIR = original


def test_list_scan_dates_sorted_and_nonempty():
    dates = loader.list_scan_dates()
    assert dates, "应有可用扫描日期"
    assert dates == sorted(dates)
    assert "2026-08-26" in dates
