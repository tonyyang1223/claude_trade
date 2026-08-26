"""Tests for src.research.lifecycle (stage transition action mapping)."""
from src.research.lifecycle import FactorLifecycleManager, FactorStage


def test_get_action_no_change(store_dir):
    a = FactorLifecycleManager(store_dir=store_dir)
    assert a._get_action(FactorStage.ACTIVE, FactorStage.ACTIVE) == "No action needed"


def test_get_action_graduate(store_dir):
    a = FactorLifecycleManager(store_dir=store_dir)
    assert a._get_action(FactorStage.INCUBATING, FactorStage.ACTIVE) == "Graduate to active status"


def test_get_action_retire(store_dir):
    a = FactorLifecycleManager(store_dir=store_dir)
    assert a._get_action(FactorStage.DEPRECATED, FactorStage.RETIRED) == "Retire factor completely"


def test_get_action_default(store_dir):
    a = FactorLifecycleManager(store_dir=store_dir)
    act = a._get_action(FactorStage.NEW, FactorStage.RETIRED)
    assert act.startswith("Transition from")
