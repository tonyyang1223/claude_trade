#!/usr/bin/env python3
"""Command-line interface for BTC dominance analysis.

Usage:
    python scripts/analysis/analyze_btc_dominance.py
    python scripts/analysis/analyze_btc_dominance.py --output json
"""
import argparse
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.btc_dominance import BTCDominanceAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze BTC dominance and market phase")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--api-key", "-k", help="CoinGecko API key (optional)")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        analyzer = BTCDominanceAnalyzer(api_key=args.api_key)
        result = analyzer.analyze()

        if args.output == "json":
            print(json.dumps(result.model_dump(), indent=2, default=str))
        else:
            print(f"\n{'='*50}")
            print(f"BTC Dominance Analysis")
            print(f"{'='*50}")
            print(f"\nCurrent Dominance: {result.current_dominance:.1f}%")
            print(f"Trend: {result.trend.upper()}")
            print(f"Market Phase: {result.market_phase}")
            print(f"Altcoin Season: {'Yes' if result.altcoin_season else 'No'}")
            print(f"\nRecommendation: {result.recommendation}")
            print(f"\nTimestamp: {result.timestamp}")
            print(f"{'='*50}\n")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()