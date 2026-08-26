"""Tests for src.research.classification (factor classification system)."""
from src.research.classification import FactorClassifier


def test_classifier_builds_nonempty():
    c = FactorClassifier()
    assert len(c._classifications) > 0


def test_get_classification_known_factor():
    c = FactorClassifier()
    cl = c.get_classification("funding_rate")
    assert cl is not None
    assert cl.category == "derivatives"
    assert cl.subcategory == "funding"
    assert cl.to_dict()["factor_name"] == "funding_rate"


def test_get_by_category():
    c = FactorClassifier()
    deriv = c.get_by_category("derivatives")
    names = {x.factor_name for x in deriv}
    assert "funding_rate" in names


def test_get_by_theme():
    c = FactorClassifier()
    dev = c.get_by_theme("developer")
    assert len(dev) > 0


def test_get_category_summary_counts_consistent():
    c = FactorClassifier()
    summary = c.get_category_summary()
    assert isinstance(summary, dict)
    assert "derivatives" in summary
    total = sum(summary["derivatives"].values())
    assert total == len(c.get_by_category("derivatives"))


def test_export_classification_table():
    c = FactorClassifier()
    table = c.export_classification_table()
    assert isinstance(table, list)
    assert len(table) == len(c._classifications)
    assert table[0]["factor_name"]
