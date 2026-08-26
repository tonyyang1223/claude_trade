"""Tests for src.research.accumulation (data gap assessment)."""
from src.research.accumulation import DataAccumulationPlanner


def test_assess_data_gap_critical(store_dir, write_history):
    write_history("acc_factor", [1.0] * 10)
    a = DataAccumulationPlanner(store_dir=store_dir)
    res = a.assess_data_gap("acc_factor")
    assert res["status"] == "CRITICAL"
    assert res["priority"] == "CRITICAL"
    assert res["current_days"] == 10


def test_assess_data_gap_insufficient(store_dir, write_history):
    write_history("acc_factor", [1.0] * 200)
    a = DataAccumulationPlanner(store_dir=store_dir)
    res = a.assess_data_gap("acc_factor")
    assert res["status"] == "INSUFFICIENT"
    assert res["priority"] == "HIGH"


def test_assess_data_gap_adequate(store_dir, write_history):
    write_history("acc_factor", [1.0] * 300)
    a = DataAccumulationPlanner(store_dir=store_dir)
    res = a.assess_data_gap("acc_factor")
    assert res["status"] == "ADEQUATE"
    assert res["priority"] == "MEDIUM"
