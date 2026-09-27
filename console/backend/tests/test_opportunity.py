"""services.opportunity_svc.compute 单元测试（基于真实 2026-08-26 数据）。

覆盖：返回模型结构、composite 边界与维度键合法性、权重归一（仅对非空维度加权）、
``mcapMax`` 市值过滤、``sort`` 排序（含非法排序回退）、无数据日期优雅返回空结构。
"""
from core.config import RADAR_WEIGHTS
from services.opportunity_svc import compute

REAL_DATE = "2026-08-26"


def test_compute_real_returns_envelope_model():
    res = compute(REAL_DATE)
    assert res.meta["date"] == REAL_DATE
    assert isinstance(res.rankings, list)
    assert len(res.rankings) > 0
    assert res.meta["count"] == len(res.rankings)


def test_composite_bounds_and_dims_keys():
    res = compute(REAL_DATE)
    for item in res.rankings:
        # composite 在 [0,100] 区间（无维度时为 0）
        assert 0.0 <= item.composite <= 100.0
        # 维度键必须是权重表中的键
        for k in item.dims:
            assert k in RADAR_WEIGHTS


def test_weight_normalization_only_present_dims():
    res = compute(REAL_DATE)
    for item in res.rankings:
        present = {k: v for k, v in item.dims.items() if k in RADAR_WEIGHTS}
        if not present:
            assert item.composite == 0.0
            continue
        w_sum = sum(RADAR_WEIGHTS[k] for k in present)
        expected = round(
            sum(RADAR_WEIGHTS[k] * present[k] for k in present) / w_sum, 2
        )
        # 容差：权重归一后的 composite 仅做浮点 round 取舍，半厘边界可能与重算
        # 结果差 0.01，属浮点取整误差而非逻辑错误（权重写错会差数个百分点）。
        assert abs(item.composite - expected) <= 0.011


def test_mcap_max_filter():
    full = compute(REAL_DATE)
    filtered = compute(REAL_DATE, mcap_max=1_000_000)
    assert len(filtered.rankings) <= len(full.rankings)
    for item in filtered.rankings:
        assert item.mcap is None or item.mcap <= 1_000_000


def test_sort_growth_desc():
    res = compute(REAL_DATE, sort="growth")
    vals = [it.dims.get("growth", 0.0) for it in res.rankings]
    assert vals == sorted(vals, reverse=True)


def test_sort_invalid_falls_back_to_composite():
    res = compute(REAL_DATE, sort="not_a_real_field")
    vals = [it.composite for it in res.rankings]
    assert vals == sorted(vals, reverse=True)
    assert res.meta["sort"] == "composite"


def test_empty_date_graceful():
    res = compute("2099-01-01")
    assert res.meta["date"] == "2099-01-01"
    assert res.rankings == []
    assert res.meta["count"] == 0
