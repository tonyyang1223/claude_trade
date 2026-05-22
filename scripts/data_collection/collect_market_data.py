#!/usr/bin/env python3
"""Command-line interface for market data collection.

Usage:
    # Collect top 100 coins using CoinGecko (free)
    python scripts/data_collection/collect_market_data.py --source coingecko --top 100

    # Collect market data using CoinMarketCap (requires API key)
    python scripts/data_collection/collect_market_data.py --source coinmarketcap --api-key YOUR_KEY

    # Collect specific coin data
    python scripts/data_collection/collect_market_data.py --coin bitcoin --source coingecko

    # Export to CSV
    python scripts/data_collection/collect_market_data.py --source coingecko --format csv
"""
import argparse
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.collector.market_collector import MarketCollector


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect cryptocurrency market data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --source coingecko --top 100
  %(prog)s --source coinmarketcap --api-key YOUR_KEY
  %(prog)s --coin bitcoin ethereum
  %(prog)s --source coingecko --format csv --no-cache
        """
    )

    parser.add_argument(
        "--source", "-s",
        choices=["coingecko", "coinmarketcap"],
        default="coingecko",
        help="API source to use (default: coingecko)"
    )

    parser.add_argument(
        "--api-key", "-k",
        help="API key for the selected source"
    )

    parser.add_argument(
        "--top", "-t",
        type=int,
        default=100,
        help="Number of top coins to collect (default: 100)"
    )

    parser.add_argument(
        "--coin", "-c",
        nargs="+",
        help="Specific coin(s) to collect (space-separated)"
    )

    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("data/processed"),
        help="Output directory (default: data/processed)"
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/cache"),
        help="Cache directory (default: data/cache)"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching"
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

    # Load environment variables
    load_dotenv()

    # Get API key from args or environment
    api_key = args.api_key
    if not api_key and args.source == "coinmarketcap":
        api_key = os.getenv("CMC_API_KEY")
    elif not api_key and args.source == "coingecko":
        api_key = os.getenv("COINGECKO_API_KEY")

    # Initialize collector
    if args.verbose:
        print(f"Initializing {args.source} collector...")

    try:
        collector = MarketCollector(
            api_source=args.source,
            api_key=api_key,
            cache_dir=args.cache_dir,
            output_dir=args.output
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Collect data
    if args.coin:
        # Collect specific coins
        coins = []
        for coin_id in args.coin:
            if args.verbose:
                print(f"Collecting data for {coin_id}...")
            try:
                coin_data = collector.collect_coin_data(
                    coin_id,
                    use_cache=not args.no_cache
                )
                coins.append(coin_data)
                if args.verbose:
                    print(f"  {coin_data.name}: ${coin_data.current_price:,.2f}")
            except Exception as e:
                print(f"Error collecting {coin_id}: {e}")

        # Export
        if coins:
            from src.data.models import MarketData
            from datetime import datetime

            market_data = MarketData(
                timestamp=datetime.now(),
                total_market_cap=0,
                btc_dominance=0,
                coins=coins
            )
            output_path = collector.export_data(
                market_data,
                format=args.format,
                prefix="selected_coins"
            )
            print(f"Exported to: {output_path}")

    else:
        # Collect market data
        if args.verbose:
            print(f"Collecting top {args.top} coins...")

        try:
            market_data = collector.collect_market_data(
                top_n=args.top,
                use_cache=not args.no_cache
            )

            if args.verbose:
                print(f"Total market cap: ${market_data.total_market_cap:,.0f}")
                print(f"BTC dominance: {market_data.btc_dominance:.1f}%")
                print(f"Coins collected: {len(market_data.coins)}")

            # Export
            output_path = collector.export_data(
                market_data,
                format=args.format,
                prefix="market_data"
            )
            print(f"Exported to: {output_path}")

        except Exception as e:
            print(f"Error collecting market data: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()