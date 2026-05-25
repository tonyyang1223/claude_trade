"""Tests for the scoring system."""
import pytest
from src.analysis.scorer import Scorer


def test_default_weights():
    """Test default weight configuration."""
    scorer = Scorer()
    assert scorer.weights == {
        'market': 0.20,
        'technical': 0.15,
        'onchain': 0.20,
        'sentiment': 0.10,
        'github': 0.10,
        'social': 0.10,
        'risk': 0.15
    }


def test_weights_sum_to_one():
    """Test that weights sum to 1.0."""
    scorer = Scorer()
    assert sum(scorer.weights.values()) == 1.0


def test_custom_weights():
    """Test custom weight configuration."""
    custom_weights = {
        'market': 0.30,
        'technical': 0.20,
        'onchain': 0.15,
        'sentiment': 0.10,
        'github': 0.05,
        'social': 0.10,
        'risk': 0.10
    }
    scorer = Scorer(custom_weights=custom_weights)
    assert scorer.weights == custom_weights
    assert scorer.weights['market'] == 0.30


def test_invalid_weights_raises_error():
    """Test that invalid weights raise ValueError."""
    invalid_weights = {
        'market': 0.50,
        'technical': 0.50,
        'onchain': 0.50,
        'sentiment': 0.10,
        'github': 0.10,
        'social': 0.10,
        'risk': 0.10
    }
    with pytest.raises(ValueError, match="Weights must sum to 1.0"):
        Scorer(custom_weights=invalid_weights)


def test_weights_do_not_modify_defaults():
    """Test that modifying instance weights doesn't affect defaults."""
    scorer = Scorer()
    scorer.weights['market'] = 0.99
    scorer2 = Scorer()
    assert scorer2.weights['market'] == 0.20


def test_generate_rating():
    """Test rating generation based on total score."""
    scorer = Scorer()

    assert scorer.generate_rating(95) == 'A+'
    assert scorer.generate_rating(85) == 'A'
    assert scorer.generate_rating(75) == 'B'
    assert scorer.generate_rating(65) == 'C'
    assert scorer.generate_rating(55) == 'D'
    assert scorer.generate_rating(45) == 'F'


def test_rating_boundary_values():
    """Test rating at boundary values."""
    scorer = Scorer()

    # A+ boundary (90-100)
    assert scorer.generate_rating(90) == 'A+'
    assert scorer.generate_rating(89.99) == 'A'

    # A boundary (80-89)
    assert scorer.generate_rating(80) == 'A'
    assert scorer.generate_rating(79.99) == 'B'

    # B boundary (70-79)
    assert scorer.generate_rating(70) == 'B'
    assert scorer.generate_rating(69.99) == 'C'

    # C boundary (60-69)
    assert scorer.generate_rating(60) == 'C'
    assert scorer.generate_rating(59.99) == 'D'

    # D boundary (50-59)
    assert scorer.generate_rating(50) == 'D'
    assert scorer.generate_rating(49.99) == 'F'
