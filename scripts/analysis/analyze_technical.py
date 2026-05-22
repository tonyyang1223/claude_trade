#!/usr/bin/env python3
"""Command-line interface for technical analysis.

Usage:
    python scripts/analysis/analyze_technical.py --symbol BTC/USDT --days 200
    python scripts/analysis/analyze_technical.py --symbol ETH/USDT --market-cap 400000000000
"""
import argparse
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.technical import TechnicalAnalyzer


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Perform technical analysis on a cryptocurrency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --symbol BTC/USDT --days 200
  %(prog)s --symbol ETH/USDT --market-cap 400000000000
  %(prog)s --symbol SOL/USDT --output json
        """
    )

    parser.add_argument(
        "--symbol", "-s",
        required=True,
        help="Trading pair (e.g., BTC/USDT)"
    )

    parser.add_argument(
        "--days", "-d",
        type=int,
        default=200,
        help="Number of days to analyze (default: 200)"
    )

    parser.add_argument(
        "--market-cap", "-m",
        type=float,
        help="Market cap for volume ratio calculation"
    )

    parser.add_argument(
        "--output", "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    if args.verbose:
        print(f"Analyzing {args.symbol} with {args.days} days of data...")

    try:
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(
            symbol=args.symbol,
            days=args.days,
            market_cap=args.market_cap
        )

        if args.output == "json":
            print(json.dumps(result.model_dump(), indent=2, default=str))
        else:
            print(f"\n{'='*50}")
            print(f"Technical Analysis: {args.symbol}")
            print(f"{'='*50}")
            print(f"\nRSI: {result.rsi:.2f} (Signal: {result.rsi_signal}/5)")
            print(f"50-day MA: ${result.ma_50:,.2f}")
            print(f"200-day MA: ${result.ma_200:,.2f}")
            print(f"MA Signal: {result.ma_signal}/5")
            print(f"\nTrend: {result.trend.upper()} (Signal: {result.trend_signal}/5)")
            print(f"\nSupport Levels: {[f'${x:,.2f}' for x in result.support_levels]}")
            print(f"Resistance Levels: {[f'${x:,.2f}' for x in result.resistance_levels]}")
            print(f"\nFibonacci Levels:")
            for level, value in result.fibonacci_levels.items():
                print(f"  {level}%: ${value:,.2f}")
            print(f"\nVolume Ratio: {result.volume_ratio:.4f} (Signal: {result.volume_signal}/5)")
            print(f"\nTimestamp: {result.timestamp}")
            print(f"{'='*50}\n")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()