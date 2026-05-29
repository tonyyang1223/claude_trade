"""Historical Research Dataset - DuckDB database for factor research.

Supports SQL queries on historical factor data.
Example: SELECT factor_name, value FROM factors WHERE symbol='BTC'
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

from src.factors import registry
from src.factors.store import FactorStore


class FactorDatabase:
    """DuckDB research database for factor data."""

    def __init__(self, db_path: Path = Path("data/research/factors.duckdb")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = FactorStore()
        
        if HAS_DUCKDB:
            self.conn = duckdb.connect(str(db_path))
            self._create_tables()
        else:
            self.conn = None

    def _create_tables(self):
        if not self.conn: return
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS factors (
                date VARCHAR,
                factor_name VARCHAR,
                coin_id VARCHAR,
                raw_value DOUBLE,
                normalized_value DOUBLE,
                zscore DOUBLE,
                percentile DOUBLE,
                score INTEGER,
                confidence DOUBLE,
                timestamp VARCHAR
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON factors(date)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_factor ON factors(factor_name)")

    def load_from_store(self, days: int = 90) -> int:
        if not self.conn: return 0
        registry.discover_factors()
        dates = self.store.list_available_dates()[-days:]
        
        total = 0
        for date_str in dates:
            factors = self.store.load_factors(date_str)
            for name, data in factors.items():
                self.conn.execute("""
                    INSERT INTO factors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    date_str, name, data.get("coin_id", "global"),
                    data.get("raw_value", 0), data.get("normalized_value"),
                    data.get("zscore"), data.get("percentile"),
                    data.get("score"), data.get("confidence", 0.9),
                    data.get("timestamp", "")
                ])
                total += 1
        return total

    def query(self, sql: str) -> List[Dict]:
        if not self.conn: return []
        result = self.conn.execute(sql).fetchall()
        columns = [desc[0] for desc in self.conn.execute(sql).description]
        return [dict(zip(columns, row)) for row in result]

    def get_factor_series(self, factor_name: str, coin_id: str = None) -> List[Dict]:
        sql = f"SELECT date, raw_value, normalized_value, score FROM factors WHERE factor_name='{factor_name}'"
        if coin_id:
            sql += f" AND coin_id='{coin_id}'"
        sql += " ORDER BY date"
        return self.query(sql)

    def get_latest_factors(self, coin_id: str = None) -> Dict[str, Dict]:
        sql = "SELECT factor_name, raw_value, normalized_value, score FROM factors WHERE date = (SELECT MAX(date) FROM factors)"
        if coin_id:
            sql += f" AND coin_id='{coin_id}'"
        results = self.query(sql)
        return {r["factor_name"]: r for r in results}

    def export_to_parquet(self, output_path: Path):
        if not self.conn: return
        self.conn.execute(f"COPY factors TO '{output_path}' (FORMAT PARQUET)")

    def get_stats(self) -> Dict[str, Any]:
        if not self.conn: return {"status": "duckdb_not_available"}
        count = self.conn.execute("SELECT COUNT(*) FROM factors").fetchone()[0]
        dates = self.conn.execute("SELECT MIN(date), MAX(date) FROM factors").fetchone()
        return {"total_records": count, "date_range": dates, "db_path": str(self.db_path)}

    def close(self):
        if self.conn: self.conn.close()
