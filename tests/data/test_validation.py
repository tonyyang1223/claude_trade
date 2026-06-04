"""Tests for data validation module."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.data.validation import DataValidator, ValidationResult


class TestDataValidator:
    """Test DataValidator class."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return DataValidator()

    def test_validate_coingecko_valid_data(self, validator, mock_coingecko_response):
        """Test valid CoinGecko data passes validation."""
        result = validator.validate('coingecko', mock_coingecko_response)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_coingecko_missing_required_field(self, validator, mock_coingecko_response):
        """Test missing required field fails validation."""
        data = mock_coingecko_response.copy()
        del data['current_price']
        result = validator.validate('coingecko', data)
        assert result.is_valid is False
        assert 'current_price' in str(result.errors)

    def test_validate_negative_value(self, validator, mock_coingecko_response):
        """Test negative value for positive-only field fails validation."""
        data = mock_coingecko_response.copy()
        data['market_cap'] = -1000
        result = validator.validate('coingecko', data)
        assert result.is_valid is False
        assert 'market_cap' in str(result.errors)

    def test_validate_invalid_timestamp(self, validator, mock_coingecko_response):
        """Test invalid timestamp format fails validation."""
        data = mock_coingecko_response.copy()
        data['last_updated'] = 'invalid_timestamp'
        result = validator.validate('coingecko', data)
        assert result.is_valid is False
        assert 'last_updated' in str(result.errors)

    def test_validate_coinglass_funding_rate(self, validator, mock_coinglass_response):
        """Test CoinGlass funding rate validation."""
        result = validator.validate('coinglass', mock_coinglass_response)
        assert result.is_valid is True

    def test_validate_defillama_tvl(self, validator, mock_defillama_response):
        """Test DefiLlama TVL validation."""
        result = validator.validate('defillama', mock_defillama_response)
        assert result.is_valid is True

    def test_validate_github_valid_data(self, validator, mock_github_response):
        """Test GitHub data validation."""
        result = validator.validate('github', mock_github_response)
        assert result.is_valid is True

    def test_validate_reddit_valid_data(self, validator, mock_reddit_response):
        """Test Reddit data validation."""
        result = validator.validate('reddit', mock_reddit_response)
        assert result.is_valid is True

    def test_validate_unknown_source(self, validator):
        """Test unknown data source raises error."""
        with pytest.raises(ValueError, match="Unknown data source"):
            validator.validate('unknown_source', {})

    def test_validate_dataframe_with_nan(self, validator):
        """Test DataFrame with NaN values handles gracefully."""
        df = pd.DataFrame({
            'price': [100.0, np.nan, 105.0],
            'volume': [1000, 2000, 3000]
        })
        result = validator.validate_dataframe(df, {'price': 'positive', 'volume': 'positive'})
        assert result.is_valid is True  # NaN is allowed
        assert any('price' in w for w in result.warnings)  # Warning about NaN

    def test_validate_empty_data(self, validator):
        """Test empty data fails validation."""
        result = validator.validate('coingecko', {})
        assert result.is_valid is False