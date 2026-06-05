#!/usr/bin/env python3
"""Daily data collector with validation and retry logic.

Usage:
    # Collect all sources
    python scripts/data_collection/daily_collector.py

    # Collect specific sources
    python scripts/data_collection/daily_collector.py --sources coingecko,defillama

    # Dry run (no save)
    python scripts/data_collection/daily_collector.py --dry-run
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.api.coingecko import CoinGeckoClient
from src.api.coinglass import CoinglassClient
from src.api.defillama import DefiLlamaClient
from src.api.github import GithubClient
from src.api.reddit import RedditClient
from src.data.validation import DataValidator, ValidationResult


class DailyCollector:
    """Daily data collector with validation and retry logic.

    Collects data from multiple API sources, validates it, and saves
    to partitioned Parquet files.

    Attributes:
        clients: Dict of API client instances
        raw_dir: Directory for raw data storage
        rejected_dir: Directory for rejected data
        validator: DataValidator instance
        logger: Logger instance
        retry_attempts: Number of retry attempts per source
        retry_delay: Base delay between retries (exponential backoff)
        dry_run: If True, skip saving data
    """

    # Default coin parameters for each source (configurable via subclassing or config)
    DEFAULT_COINS = {
        'coingecko': 'bitcoin',
        'coinglass': 'BTC',
        'defillama': 'Ethereum',
        'github': ('bitcoin', 'bitcoin'),
        'reddit': 'bitcoin'
    }

    def __init__(self, config_path: str = "config/settings.yaml", dry_run: bool = False):
        """Initialize collector with config.

        Args:
            config_path: Path to configuration file
            dry_run: If True, skip saving data (only validate and log)
        """
        self.dry_run = dry_run
        self._load_config(config_path)
        self._setup_logging()
        self._init_clients()
        self.validator = DataValidator()

    def _load_config(self, config_path: str):
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
        else:
            config = {}

        self.raw_dir = Path(config.get('data', {}).get('raw_dir', 'data/raw'))
        self.rejected_dir = self.raw_dir / '_rejected'
        self.retry_attempts = config.get('collection', {}).get('retry_attempts', 3)
        self.retry_delay = config.get('collection', {}).get('retry_delay', 1)

    def _setup_logging(self):
        """Configure logging to file and console."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        # Create logger
        self.logger = logging.getLogger('DailyCollector')
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers
        self.logger.handlers = []

        # File handler
        file_handler = logging.FileHandler(
            log_dir / 'collector.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _init_clients(self):
        """Initialize API clients."""
        load_dotenv()

        self.clients = {
            'coingecko': CoinGeckoClient(),
            'coinglass': CoinglassClient(),
            'defillama': DefiLlamaClient(),
            'github': GithubClient(),
            'reddit': RedditClient()
        }

    def collect_single(self, source: str) -> Dict[str, Any]:
        """Collect data from a single source with retry logic.

        Args:
            source: Source name (coingecko, coinglass, etc.)

        Returns:
            Dict with success status and optional path/error
        """
        if source not in self.clients:
            return {'success': False, 'error': f'Unknown source: {source}'}

        client = self.clients[source]
        data = None

        # Retry loop with exponential backoff
        for attempt in range(self.retry_attempts):
            try:
                self.logger.info(f"Collecting {source} (attempt {attempt + 1}/{self.retry_attempts})")
                start_time = time.time()

                data = self._fetch_from_client(client, source)

                if data is None:
                    raise ValueError("No data returned from client")

                elapsed = time.time() - start_time

                # Validate data
                validation_result = self.validator.validate(source, data)

                if not validation_result.is_valid:
                    self.logger.warning(
                        f"{source} validation failed: {validation_result.errors}"
                    )
                    self._save_rejected(source, data, validation_result.errors)
                    return {
                        'success': False,
                        'error': f"Validation failed: {validation_result.errors}"
                    }

                # Save valid data
                path = self._save_parquet(source, data)

                self.logger.info(
                    f"{source}: success ({elapsed:.2f}s) -> {path}"
                )

                return {'success': True, 'path': str(path)}

            except Exception as e:
                self.logger.warning(
                    f"{source} attempt {attempt + 1} failed: {e}"
                )
                if attempt < self.retry_attempts - 1:
                    sleep_time = self.retry_delay * (2 ** attempt)
                    self.logger.info(f"Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    self.logger.error(f"{source}: all retries exhausted")
                    return {'success': False, 'error': str(e)}

        return {'success': False, 'error': 'Unknown error'}

    def _fetch_from_client(self, client: Any, source: str) -> Dict[str, Any]:
        """Fetch data using client-specific methods.

        Args:
            client: API client instance
            source: Source name

        Returns:
            Data dictionary from the client
        """
        defaults = self.DEFAULT_COINS.get(source)

        if source == 'coingecko':
            return client.get_coin_data(defaults)
        elif source == 'coinglass':
            return client.get_funding_rate(defaults)
        elif source == 'defillama':
            return client.get_chain_tvl(defaults)
        elif source == 'github':
            return client.get_repo_info(*defaults)
        elif source == 'reddit':
            return client.get_coin_mentions(defaults)
        else:
            raise ValueError(f"No fetch method for source: {source}")

    def _save_parquet(self, source: str, data: Dict[str, Any]) -> Path:
        """Save data to partitioned Parquet file.

        Args:
            source: Source name
            data: Data dictionary

        Returns:
            Path to saved file (or would-be path in dry run)
        """
        # Create directory
        dir_path = self.raw_dir / source
        dir_path.mkdir(parents=True, exist_ok=True)

        # Generate filename with date
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"{today}.parquet"
        file_path = dir_path / filename

        # Dry run: skip actual save
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would save to {file_path}")
            return file_path

        # Convert to DataFrame and save
        df = pd.DataFrame([data])
        df.to_parquet(file_path, index=False)

        return file_path

    def _save_rejected(self, source: str, data: Dict[str, Any], errors: List[str]):
        """Save rejected data to _rejected directory.

        Args:
            source: Source name
            data: Rejected data
            errors: List of validation errors
        """
        self.rejected_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"{today}_{source}.json"
        file_path = self.rejected_dir / filename

        # Save with errors
        output = {
            'data': data,
            'errors': errors,
            'timestamp': datetime.now().isoformat()
        }

        with open(file_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)

        self.logger.info(f"Rejected data saved to {file_path}")

    def collect_all(self) -> Dict[str, Dict[str, Any]]:
        """Collect data from all sources.

        Returns:
            Dict mapping source names to result dicts
        """
        self.logger.info("Starting daily collection for all sources")
        results = {}

        for source in self.clients.keys():
            results[source] = self.collect_single(source)

        # Summary
        successful = sum(1 for r in results.values() if r['success'])
        total = len(results)
        self.logger.info(
            f"Daily collection completed: {successful}/{total} sources successful"
        )

        return results

    def collect_sources(self, sources: List[str]) -> Dict[str, Dict[str, Any]]:
        """Collect data from specified sources only.

        Args:
            sources: List of source names to collect

        Returns:
            Dict mapping source names to result dicts
        """
        self.logger.info(f"Starting collection for sources: {sources}")
        results = {}

        for source in sources:
            if source in self.clients:
                results[source] = self.collect_single(source)
            else:
                self.logger.warning(f"Unknown source: {source}")
                results[source] = {'success': False, 'error': 'Unknown source'}

        return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Daily data collector for quantitative analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--sources', '-s',
        help="Comma-separated list of sources to collect (default: all)"
    )

    parser.add_argument(
        '--config', '-c',
        default='config/settings.yaml',
        help="Path to config file (default: config/settings.yaml)"
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Run without saving data"
    )

    args = parser.parse_args()

    try:
        collector = DailyCollector(config_path=args.config, dry_run=args.dry_run)

        if args.sources:
            sources = [s.strip() for s in args.sources.split(',')]
            results = collector.collect_sources(sources)
        else:
            results = collector.collect_all()

        # Print summary
        print("\nCollection Results:")
        for source, result in results.items():
            status = "OK" if result['success'] else "FAIL"
            print(f"  {status} {source}: {result.get('path', result.get('error', 'unknown'))}")

        # Exit with error code if any source failed
        if not all(r['success'] for r in results.values()):
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
