"""Historical Factor Store for persisting factor values.

Uses parquet files for efficient storage.
Factors are stored daily in data/factors/YYYY-MM-DD/ directory.
"""
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_PARQUET = True
except ImportError:
    HAS_PARQUET = False


class FactorStore:
    """Historical factor storage and retrieval.

    Stores factor values in parquet files organized by date.

    Directory structure:
        data/factors/YYYY-MM-DD/
            - factors.parquet
            - factors.json

    Example:
        >>> store = FactorStore()
        >>> store.save_factors('2026-05-29', {'funding_rate': {...}})
        >>> factors = store.load_factors('2026-05-29')
    """

    def __init__(self, base_dir: Path = Path("data/factors")):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_date_dir(self, date_str: str) -> Path:
        date_dir = self.base_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir

    def save_factors(
        self,
        date_str: str,
        factors: Dict[str, Dict[str, Any]],
        coin_id: Optional[str] = None
    ) -> None:
        """Save factors for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format
            factors: Dict of factor_name -> {raw_value, normalized, zscore, percentile, score, confidence}
            coin_id: Optional coin identifier
        """
        date_dir = self._get_date_dir(date_str)

        # Build records
        records = []
        for factor_name, factor_data in factors.items():
            record = {
                "factor_name": factor_name,
                "coin_id": coin_id or "global",
                "raw_value": factor_data.get("raw_value", 0.0),
                "normalized_value": factor_data.get("normalized_value"),
                "zscore": factor_data.get("zscore"),
                "percentile": factor_data.get("percentile"),
                "score": factor_data.get("score"),
                "confidence": factor_data.get("confidence", 0.9),
                "timestamp": factor_data.get("timestamp", datetime.now().isoformat()),
                "date": date_str
            }
            records.append(record)

        if HAS_PARQUET and records:
            table = pa.Table.from_pydict({
                "factor_name": [r["factor_name"] for r in records],
                "coin_id": [r["coin_id"] for r in records],
                "raw_value": [r["raw_value"] for r in records],
                "normalized_value": [r["normalized_value"] for r in records],
                "zscore": [r["zscore"] for r in records],
                "percentile": [r["percentile"] for r in records],
                "score": [r["score"] for r in records],
                "confidence": [r["confidence"] for r in records],
                "timestamp": [r["timestamp"] for r in records],
                "date": [r["date"] for r in records]
            })
            pq.write_table(table, date_dir / "factors.parquet")

        # JSON backup
        with open(date_dir / "factors.json", 'w') as f:
            json.dump({"date": date_str, "coin_id": coin_id, "factors": factors}, f, indent=2)

    def load_factors(self, date_str: str, coin_id: Optional[str] = None) -> Dict[str, Dict]:
        """Load factors for a specific date."""
        date_dir = self._get_date_dir(date_str)
        json_path = date_dir / "factors.json"

        if json_path.exists():
            with open(json_path, 'r') as f:
                data = json.load(f)
                if coin_id and data.get("coin_id") != coin_id:
                    return {}
                return data.get("factors", {})
        return {}

    def get_factor_history(self, factor_name: str, days: int = 30) -> List[Dict]:
        """Get historical values for a factor."""
        history = []
        today = date.today()

        for i in range(days):
            date_str = (today - timedelta(days=i)).isoformat()
            factors = self.load_factors(date_str)
            if factor_name in factors:
                history.append({"date": date_str, **factors[factor_name]})

        return history

    def list_available_dates(self) -> List[str]:
        """List all dates with stored data."""
        dates = []
        for d in self.base_dir.iterdir():
            if d.is_dir() and d.name.count('-') == 2:
                dates.append(d.name)
        return sorted(dates)

    def get_store_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        dates = self.list_available_dates()
        total = sum(len(self.load_factors(d)) for d in dates)
        return {
            "total_dates": len(dates),
            "total_records": total,
            "earliest": dates[0] if dates else None,
            "latest": dates[-1] if dates else None,
            "format": "parquet" if HAS_PARQUET else "json"
        }