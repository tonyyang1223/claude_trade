#!/usr/bin/env python3
"""Check data collection status and health.

Usage:
    python scripts/check_collection_status.py
    python scripts/check_collection_status.py --alerts

Checks:
1. Crontab status - Is the job configured?
2. Last run time - When did collection last run?
3. Data freshness - Is data within 24 hours?
4. Error count - Any recent errors in logs?
5. Data integrity - Are parquet files valid?
"""
import argparse
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass
import json
import yaml
import requests

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class AlertConfig:
    """Alert configuration from settings.yaml"""
    webhook_url: str = ""
    webhook_type: str = "slack"  # slack or telegram


class CollectionStatusChecker:
    """Check data collection status and health."""

    def __init__(self):
        self.project_dir = project_root
        self.log_dir = self.project_dir / "logs"
        self.data_dir = self.project_dir / "data" / "raw"
        self.alert_config = self._load_alert_config()
        self.results = {}

    def _load_alert_config(self) -> AlertConfig:
        """Load alert configuration from settings.yaml"""
        settings_path = self.project_dir / "config" / "settings.yaml"

        if not settings_path.exists():
            return AlertConfig()

        try:
            with open(settings_path, 'r') as f:
                settings = yaml.safe_load(f) or {}

            alert = settings.get('notification', {}).get('alert', {})
            return AlertConfig(
                webhook_url=alert.get('webhook_url', ''),
                webhook_type=alert.get('webhook_type', 'slack')
            )
        except Exception:
            return AlertConfig()

    def check_all(self) -> Dict[str, Any]:
        """Run all status checks."""
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }

        # 1. Check crontab
        self.results['checks']['crontab'] = self._check_crontab()

        # 2. Check last run time
        self.results['checks']['last_run'] = self._check_last_run()

        # 3. Check data freshness
        self.results['checks']['data_freshness'] = self._check_data_freshness()

        # 4. Check error count
        self.results['checks']['errors'] = self._check_errors()

        # 5. Check data integrity
        self.results['checks']['integrity'] = self._check_data_integrity()

        # Calculate overall health
        self.results['healthy'] = all(
            c.get('healthy', True) for c in self.results['checks'].values()
        )

        return self.results

    def _check_crontab(self) -> Dict[str, Any]:
        """Check if crontab is configured."""
        try:
            result = subprocess.run(
                ['crontab', '-l'],
                capture_output=True,
                text=True
            )

            crontab = result.stdout

            if 'daily_collector.py' in crontab:
                # Extract schedule
                for line in crontab.split('\n'):
                    if 'daily_collector.py' in line and not line.startswith('#'):
                        return {
                            'healthy': True,
                            'configured': True,
                            'entry': line.strip()
                        }

            return {
                'healthy': False,
                'configured': False,
                'message': 'Crontab entry not found'
            }

        except Exception as e:
            return {
                'healthy': False,
                'configured': False,
                'error': str(e)
            }

    def _check_last_run(self) -> Dict[str, Any]:
        """Check when collection last ran."""
        log_file = self.log_dir / 'collector.log'

        if not log_file.exists():
            return {
                'healthy': False,
                'last_run': None,
                'message': 'No log file found'
            }

        try:
            # Read last lines
            with open(log_file, 'r') as f:
                lines = f.readlines()

            # Find last "Daily collection completed" line
            last_run_time = None
            for line in reversed(lines):
                if 'Daily collection completed' in line:
                    # Parse timestamp from log line
                    try:
                        ts_str = line.split(' - ')[0]
                        last_run_time = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S,%f')
                    except:
                        pass
                    break

            if last_run_time:
                age = datetime.now() - last_run_time
                return {
                    'healthy': age < timedelta(hours=26),
                    'last_run': last_run_time.isoformat(),
                    'age_hours': round(age.total_seconds() / 3600, 1)
                }

            return {
                'healthy': False,
                'last_run': None,
                'message': 'No completed run found in logs'
            }

        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_data_freshness(self) -> Dict[str, Any]:
        """Check if data files are fresh."""
        sources = ['coingecko', 'coinglass', 'defillama', 'github', 'reddit']
        freshness = {}
        all_fresh = True

        for source in sources:
            source_dir = self.data_dir / source

            if not source_dir.exists():
                freshness[source] = {
                    'healthy': False,
                    'message': 'No data directory'
                }
                all_fresh = False
                continue

            files = list(source_dir.glob('*.parquet'))

            if not files:
                freshness[source] = {
                    'healthy': False,
                    'message': 'No data files'
                }
                all_fresh = False
                continue

            newest = max(files, key=lambda f: f.stat().st_mtime)
            mtime = datetime.fromtimestamp(newest.stat().st_mtime)
            age = datetime.now() - mtime

            is_fresh = age < timedelta(hours=26)
            if not is_fresh:
                all_fresh = False

            freshness[source] = {
                'healthy': is_fresh,
                'file': newest.name,
                'age_hours': round(age.total_seconds() / 3600, 1)
            }

        return {
            'healthy': all_fresh,
            'sources': freshness
        }

    def _check_errors(self) -> Dict[str, Any]:
        """Check for recent errors in logs."""
        log_file = self.log_dir / 'collector.log'

        if not log_file.exists():
            return {
                'healthy': True,
                'error_count': 0,
                'message': 'No log file'
            }

        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()[-100:]

            error_count = sum(1 for l in lines if 'ERROR' in l or 'CRITICAL' in l)
            warning_count = sum(1 for l in lines if 'WARNING' in l)

            errors = []
            for line in lines:
                if 'ERROR' in line:
                    errors.append(line.strip()[:200])

            return {
                'healthy': error_count == 0,
                'error_count': error_count,
                'warning_count': warning_count,
                'recent_errors': errors[-5:]
            }

        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_data_integrity(self) -> Dict[str, Any]:
        """Check if parquet files are valid."""
        import pandas as pd

        sources = ['coingecko', 'coinglass', 'defillama', 'github', 'reddit']
        integrity = {}
        all_valid = True

        for source in sources:
            source_dir = self.data_dir / source

            if not source_dir.exists():
                continue

            files = list(source_dir.glob('*.parquet'))
            if not files:
                continue

            newest = max(files, key=lambda f: f.stat().st_mtime)

            try:
                df = pd.read_parquet(newest)
                integrity[source] = {
                    'healthy': True,
                    'file': newest.name,
                    'rows': len(df),
                    'columns': list(df.columns)
                }
            except Exception as e:
                integrity[source] = {
                    'healthy': False,
                    'file': newest.name,
                    'error': str(e)
                }
                all_valid = False

        return {
            'healthy': all_valid,
            'sources': integrity
        }

    def print_report(self):
        """Print status report."""
        print("=" * 60)
        print("DATA COLLECTION STATUS REPORT")
        print(f"Timestamp: {self.results['timestamp']}")
        print("=" * 60)

        status = "✅ HEALTHY" if self.results['healthy'] else "❌ UNHEALTHY"
        print(f"\nOverall Status: {status}")

        for check_name, check_result in self.results['checks'].items():
            print(f"\n--- {check_name.upper().replace('_', ' ')} ---")
            if check_result.get('healthy'):
                print("  Status: ✅ OK")
            else:
                print("  Status: ❌ ISSUE")

            for key, value in check_result.items():
                if key != 'healthy':
                    if key == 'sources':
                        for src, details in value.items():
                            src_status = "✅" if details.get('healthy') else "❌"
                            print(f"    {src_status} {src}: {details}")
                    elif key == 'recent_errors' and value:
                        print(f"    {key}:")
                        for err in value:
                            print(f"      - {err}")
                    else:
                        print(f"    {key}: {value}")

        print("\n" + "=" * 60)

    def get_alerts(self) -> List[str]:
        """Get list of issues that need attention."""
        alerts = []

        if not self.results['checks']['crontab'].get('configured'):
            alerts.append("⚠️ Crontab not configured - run scripts/setup_cron.sh")

        last_run = self.results['checks']['last_run']
        if last_run.get('age_hours', 0) > 26:
            alerts.append(f"⚠️ Last run was {last_run.get('age_hours')} hours ago")

        errors = self.results['checks']['errors']
        if errors.get('error_count', 0) > 0:
            alerts.append(f"⚠️ {errors['error_count']} errors in recent logs")

        freshness = self.results['checks']['data_freshness']
        for source, details in freshness.get('sources', {}).items():
            if not details.get('healthy'):
                alerts.append(f"⚠️ {source} data is stale or missing")

        return alerts


def main():
    parser = argparse.ArgumentParser(description="Check data collection status")

    parser.add_argument('--alerts', '-a', action='store_true', help="Only show alerts")
    parser.add_argument('--json', '-j', action='store_true', help="Output as JSON")

    args = parser.parse_args()

    checker = CollectionStatusChecker()
    results = checker.check_all()

    if args.alerts:
        alerts = checker.get_alerts()
        if alerts:
            print("\n".join(alerts))
            sys.exit(1)
        else:
            print("✅ All checks passed")
            sys.exit(0)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        checker.print_report()

    sys.exit(0 if results['healthy'] else 1)


if __name__ == '__main__':
    main()
