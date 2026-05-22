"""Data export utilities."""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd


class DataExporter:
    """Exports data to various formats.

    Attributes:
        output_dir: Directory for output files

    Example:
        >>> exporter = DataExporter(Path("data/processed"))
        >>> exporter.to_json(coins_data, "top_100_coins")
        >>> exporter.to_csv(market_data, "market_summary")
    """

    def __init__(self, output_dir: Path = Path("data/processed")):
        """Initialize exporter.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, prefix: str, extension: str) -> str:
        """Generate timestamped filename.

        Args:
            prefix: Filename prefix
            extension: File extension without dot

        Returns:
            Timestamped filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"

    def to_json(
        self,
        data: List[Dict[str, Any]],
        prefix: str,
        pretty: bool = True
    ) -> Path:
        """Export data to JSON file.

        Args:
            data: List of dictionaries to export
            prefix: Filename prefix
            pretty: Whether to format JSON with indentation

        Returns:
            Path to created file
        """
        filename = self._generate_filename(prefix, "json")
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            else:
                json.dump(data, f, ensure_ascii=False, default=str)

        return output_path

    def to_csv(
        self,
        data: List[Dict[str, Any]],
        prefix: str,
        index: bool = False
    ) -> Path:
        """Export data to CSV file.

        Args:
            data: List of dictionaries to export
            prefix: Filename prefix
            index: Whether to include DataFrame index

        Returns:
            Path to created file
        """
        filename = self._generate_filename(prefix, "csv")
        output_path = self.output_dir / filename

        df = pd.DataFrame(data)
        df.to_csv(output_path, index=index, encoding="utf-8")

        return output_path