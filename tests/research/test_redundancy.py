"""Tests for src.research.redundancy (pure redundancy classification helpers)."""
from types import SimpleNamespace

from src.research.redundancy import RedundancyDetector


def test_classify_near_duplicate(store_dir):
    d = RedundancyDetector(store_dir=store_dir)
    assert d._classify_redundancy_type(0.99, None, None) == "near_duplicate"


def test_classify_high_redundancy(store_dir):
    d = RedundancyDetector(store_dir=store_dir)
    assert d._classify_redundancy_type(0.9, None, None) == "high_redundancy"


def test_classify_moderate(store_dir):
    d = RedundancyDetector(store_dir=store_dir)
    assert d._classify_redundancy_type(0.5, None, None) == "moderate_redundancy"


def test_classify_intra_subcategory(store_dir):
    d = RedundancyDetector(store_dir=store_dir)
    c1 = SimpleNamespace(subcategory="x")
    c2 = SimpleNamespace(subcategory="x")
    assert d._classify_redundancy_type(0.5, c1, c2) == "intra_subcategory"


def test_determine_keep_higher_confidence(store_dir):
    d = RedundancyDetector(store_dir=store_dir)
    m1 = SimpleNamespace(confidence=0.9)
    m2 = SimpleNamespace(confidence=0.5)
    keep, reason = d._determine_keep_factor("f1", "f2", m1, m2, None, None)
    assert keep == "f1"
    assert "Higher confidence" in reason


def test_determine_keep_higher_frequency(store_dir):
    d = RedundancyDetector(store_dir=store_dir)
    c1 = SimpleNamespace(data_frequency="hourly")
    c2 = SimpleNamespace(data_frequency="daily")
    keep, reason = d._determine_keep_factor("f1", "f2", None, None, c1, c2)
    assert keep == "f1"
    assert "More frequent" in reason


def test_determine_keep_alphabetical(store_dir):
    d = RedundancyDetector(store_dir=store_dir)
    keep, reason = d._determine_keep_factor("aaa", "bbb", None, None, None, None)
    assert keep == "aaa"
    assert "Alphabetical" in reason
