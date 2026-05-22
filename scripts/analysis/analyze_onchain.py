#!/usr/bin/env python3
"""Command-line interface for onchain analysis.

Usage:
    python scripts/analysis/analyze_onchain.py --coin bitcoin
    python scripts/analysis/analyze_onchain.py --coin bitcoin --output json
"""
import argparse
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.onchain import OnchainAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze onchain metrics")
    parser.add_argument("--coin", "-c", default="bitcoin", help="Coin name (default: bitcoin)")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        analyzer = OnchainAnalyzer()
        result = analyzer.analyze(args.coin)

        if args.output == "json":
            print(json.dumps(result.model_dump(), indent=2, default=str))
        else:
            print(f"\n{'='*50}")
            print(f"Onchain Analysis: {args.coin}")
            print(f"{'='*50}")

            if result.nupl is not None:
                print(f"\nNUPL: {result.nupl:.3f}")
            if result.mvrv is not None:
                print(f"MVRV: {result.mvrv:.2f}")
            if result.active_addresses:
                print(f"Active Addresses: {result.active_addresses:,}")
            if result.transaction_count:
                print(f"Transaction Count: {result.transaction_count:,}")

            print(f"\nOnchain Signal: {result.onchain_signal}/5")
            print(f"\nTimestamp: {result.timestamp}")
            print(f"{'='*50}\n")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
