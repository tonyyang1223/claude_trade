"""Tests for src.research.readiness (assessment orchestration)."""
from src.research.readiness import AlphaReadinessAssessor, ReadinessLevel


def test_check_factor_count_structure(store_dir):
    a = AlphaReadinessAssessor(store_dir=store_dir)
    r = a.check_factor_count()
    assert r["check"] == "factor_count"
    assert r["status"] in ("PASS", "FAIL")
    assert r["passed"] in (True, False)


def test_generate_recommendations_ready(store_dir):
    a = AlphaReadinessAssessor(store_dir=store_dir)
    recs = a._generate_recommendations([], ReadinessLevel.READY)
    assert "ready for alpha" in recs[0]


def test_generate_recommendations_blocker(store_dir):
    a = AlphaReadinessAssessor(store_dir=store_dir)
    recs = a._generate_recommendations([{"check": "factor_count"}], ReadinessLevel.NOT_READY)
    assert any("Add more factors" in r for r in recs)


def test_assess_readiness_all_pass(store_dir, monkeypatch):
    a = AlphaReadinessAssessor(store_dir=store_dir)
    checks = [
        "check_factor_count",
        "check_data_coverage",
        "check_discrimination",
        "check_correlation",
        "check_effective_count",
        "check_history_depth",
    ]
    for name in checks:
        monkeypatch.setattr(a, name, lambda: {"check": name, "passed": True, "status": "PASS"})
    res = a.assess_readiness()
    assert res["readiness_level"] == "READY"
    assert res["passed_checks"] == 6
