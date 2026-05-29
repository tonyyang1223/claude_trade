"""Timestamp utility for unified time handling.

All timestamps in this system should:
1. Be stored in UTC
2. Use ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
3. Have millisecond precision when available

This module provides utilities to:
- Convert various timestamp formats to unified format
- Ensure UTC consistency
- Handle timezone conversions
"""
from datetime import datetime, timezone
from typing import Union, Optional


class TimestampUtil:
    """Unified timestamp handling utility.

    All timestamps in the system should use this utility for:
    - Converting API timestamps to unified format
    - Ensuring UTC consistency
    - Formatting timestamps for storage and display

    Example:
        >>> ts = TimestampUtil()
        >>> ts.now_iso()  # '2026-05-28T03:00:00Z'
        >>> ts.from_unix_ms(1779926400001)  # datetime object
    """

    ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

    @staticmethod
    def now_utc() -> datetime:
        """Get current UTC datetime."""
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def now_iso() -> str:
        """Get current UTC time in ISO format."""
        return TimestampUtil.now_utc().strftime(TimestampUtil.ISO_FORMAT)

    @staticmethod
    def from_unix_ms(timestamp_ms: Union[int, float, str]) -> datetime:
        """Convert Unix millisecond timestamp to datetime."""
        ts = int(timestamp_ms)
        return datetime.utcfromtimestamp(ts / 1000)

    @staticmethod
    def to_iso(dt: datetime) -> str:
        """Convert datetime to ISO format string."""
        return dt.strftime(TimestampUtil.ISO_FORMAT)

    @staticmethod
    def from_iso(iso_string: str) -> datetime:
        """Parse ISO format string to datetime."""
        # Remove Z suffix if present
        iso_string = iso_string.replace('Z', '')
        # Handle both formats: with and without seconds
        if 'T' in iso_string:
            return datetime.strptime(iso_string, TimestampUtil.ISO_FORMAT.rstrip('Z'))
        return datetime.strptime(iso_string, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def age_seconds(timestamp: Union[datetime, str]) -> float:
        """Calculate age of timestamp in seconds."""
        if isinstance(timestamp, str):
            dt = TimestampUtil.from_iso(timestamp)
        else:
            dt = timestamp
        now = TimestampUtil.now_utc()
        return (now - dt).total_seconds()