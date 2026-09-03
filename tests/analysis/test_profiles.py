"""Tests for per-token-type scoring profiles (src.analysis.profiles)."""
import pytest

from src.analysis.profiles import (
    get_profile,
    DEFAULT_PROFILE,
    TYPE_PROFILES,
    FAMILY_RISK,
    TypeProfile,
)


def test_all_profiles_sum_to_one():
    for token_type, weights in TYPE_PROFILES.items():
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9, f"{token_type} weights sum to {total}"


def test_no_zero_or_negative_weights():
    for token_type, weights in TYPE_PROFILES.items():
        for dim, w in weights.items():
            assert w > 0, f"{token_type}.{dim} has non-positive weight {w}"


def test_get_profile_returns_typed_profile():
    p = get_profile("layer-1")
    assert isinstance(p, TypeProfile)
    assert p.token_type == "layer-1"
    assert p.family == "l1"
    assert "market" in p.weights
    assert p.applicable_dims == list(p.weights.keys())


def test_get_profile_unknown_falls_back_to_generic():
    p = get_profile("some-unknown-type")
    assert p.token_type == "some-unknown-type"
    assert p.family == "generic"
    assert p.weights == dict(TYPE_PROFILES["unclassified"])


def test_is_applicable():
    l1 = get_profile("layer-1")
    assert l1.is_applicable("market")
    assert not l1.is_applicable("peg_stability")  # L1 has no peg dim
    stable = get_profile("stablecoin")
    assert stable.is_applicable("peg_stability")
    assert not stable.is_applicable("technical")


def test_default_profile_is_unclassified():
    assert DEFAULT_PROFILE.token_type == "unclassified"
    assert DEFAULT_PROFILE.family == "generic"


def test_family_risk_keys_match_families():
    # Every family referenced by TYPE_FAMILY must have FAMILY_RISK data.
    from src.analysis.profiles import TYPE_FAMILY
    families = set(TYPE_FAMILY.values())
    assert families.issubset(set(FAMILY_RISK.keys()))


def test_family_risk_shape():
    for fam, (vol, max_pos) in FAMILY_RISK.items():
        assert vol in ("low", "medium", "high")
        assert 0 < max_pos <= 100
