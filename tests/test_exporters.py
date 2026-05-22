"""Tests for data exporters."""
import pytest
import json
import pandas as pd
from pathlib import Path
from src.data.exporters import DataExporter
from src.data.models import CoinData, MarketData
from datetime import datetime


class TestDataExporter:
    """Tests for DataExporter class."""

    def test_export_to_json(self, tmp_path):
        """Test exporting to JSON file."""
        exporter = DataExporter(output_dir=tmp_path)

        coin = CoinData(
            id="bitcoin",
            symbol="BTC",
            name="Bitcoin",
            current_price=50000.0,
            market_cap=1000000000000.0,
            market_cap_rank=1
        )

        output_file = exporter.to_json([coin.model_dump()], "test_output")

        assert output_file.exists()
        assert output_file.suffix == ".json"

        with open(output_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["id"] == "bitcoin"

    def test_export_to_csv(self, tmp_path):
        """Test exporting to CSV file."""
        exporter = DataExporter(output_dir=tmp_path)

        coin = CoinData(
            id="bitcoin",
            symbol="BTC",
            name="Bitcoin",
            current_price=50000.0,
            market_cap=1000000000000.0,
            market_cap_rank=1
        )

        output_file = exporter.to_csv([coin.model_dump()], "test_output")

        assert output_file.exists()
        assert output_file.suffix == ".csv"

        df = pd.read_csv(output_file)
        assert len(df) == 1
        assert df.iloc[0]["id"] == "bitcoin"

    def test_export_market_data_to_json(self, tmp_path):
        """Test exporting market data to JSON."""
        exporter = DataExporter(output_dir=tmp_path)

        market = MarketData(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            total_market_cap=2000000000000.0,
            btc_dominance=50.0
        )

        output_file = exporter.to_json([market.model_dump()], "market_data")

        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)
        assert data[0]["btc_dominance"] == 50.0

    def test_generate_timestamped_filename(self, tmp_path):
        """Test generating timestamped filename."""
        exporter = DataExporter(output_dir=tmp_path)
        filename = exporter._generate_filename("test", "json")

        assert filename.startswith("test_")
        assert filename.endswith(".json")
        assert len(filename) > 10  # Should have timestamp