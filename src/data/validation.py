"""Data validation module for API responses and collected data."""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import re


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, error: str):
        """Add validation error."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        """Add validation warning."""
        self.warnings.append(warning)


class DataValidator:
    """Validate data from various API sources."""

    # Required fields per data source
    REQUIRED_FIELDS = {
        'coingecko': {
            'required': ['id', 'symbol', 'current_price', 'market_cap', 'market_cap_rank'],
            'positive': ['current_price', 'market_cap', 'total_volume', 'circulating_supply'],
            'timestamp': ['last_updated']
        },
        'coinglass': {
            'required': ['symbol', 'fundingRate', 'fundingTime'],
            'positive': [],  # funding rate can be negative
            'timestamp': ['fundingTime']
        },
        'defillama': {
            'required': ['chain', 'tvl'],
            'positive': ['tvl'],
            'timestamp': []
        },
        'github': {
            'required': ['id', 'name', 'full_name'],
            'positive': ['stargazers_count', 'forks_count', 'open_issues_count'],
            'timestamp': ['pushed_at', 'updated_at']
        },
        'reddit': {
            'required': ['kind', 'data'],
            'positive': [],
            'timestamp': []
        }
    }

    # Timestamp format patterns
    TIMESTAMP_PATTERNS = [
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO format
        r'\d{4}-\d{2}-\d{2}',  # Date only
    ]

    def validate(self, source: str, data: Dict[str, Any]) -> ValidationResult:
        """Validate data from a specific source.

        Args:
            source: Data source name (coingecko, coinglass, etc.)
            data: Data dictionary to validate

        Returns:
            ValidationResult with is_valid, errors, and warnings
        """
        result = ValidationResult(is_valid=True)

        if source not in self.REQUIRED_FIELDS:
            raise ValueError(f"Unknown data source: {source}")

        schema = self.REQUIRED_FIELDS[source]

        # Check required fields
        for field_name in schema['required']:
            if field_name not in data:
                result.add_error(f"Missing required field: {field_name}")

        # Check positive-only fields
        for field_name in schema['positive']:
            if field_name in data:
                value = data[field_name]
                if isinstance(value, (int, float)) and value < 0:
                    result.add_error(f"Field {field_name} must be non-negative, got: {value}")

        # Validate timestamp fields
        for field_name in schema['timestamp']:
            if field_name in data:
                if not self._validate_timestamp(data[field_name]):
                    result.add_error(f"Invalid timestamp format for {field_name}: {data[field_name]}")

        return result

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        field_rules: Dict[str, str]
    ) -> ValidationResult:
        """Validate a DataFrame based on field rules.

        Args:
            df: DataFrame to validate
            field_rules: Dict mapping column names to validation rules
                         Rules: 'positive', 'required', 'timestamp'

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        for column, rule in field_rules.items():
            if column not in df.columns:
                if rule == 'required':
                    result.add_error(f"Missing required column: {column}")
                continue

            # Check for NaN values
            nan_count = df[column].isna().sum()
            if nan_count > 0:
                result.add_warning(f"Column {column} has {nan_count} NaN values")

            # Check positive constraint
            if rule == 'positive':
                valid_values = df[column].dropna()
                if (valid_values < 0).any():
                    result.add_error(f"Column {column} contains negative values")

        return result

    def _validate_timestamp(self, value: Any) -> bool:
        """Validate timestamp format.

        Args:
            value: Timestamp value (string or numeric)

        Returns:
            True if valid, False otherwise
        """
        if isinstance(value, (int, float)):
            # Unix timestamp (seconds or milliseconds)
            try:
                # Assume milliseconds if > 1e12
                if value > 1e12:
                    datetime.fromtimestamp(value / 1000)
                else:
                    datetime.fromtimestamp(value)
                return True
            except (OSError, OverflowError):
                return False

        if isinstance(value, str):
            # Check against patterns
            for pattern in self.TIMESTAMP_PATTERNS:
                if re.match(pattern, value):
                    return True
            return False

        return False
