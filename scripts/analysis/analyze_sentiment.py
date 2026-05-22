#!/usr/bin/env python3
"""Command-line interface for sentiment analysis.

Usage:
    python scripts/analysis/analyze_sentiment.py --coin bitcoin
    python scripts/analysis/analyze_sentiment.py --coin ethereum --output json
"""
import argparse
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.sentiment import SentimentAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze market sentiment")
    parser.add_argument("--coin", "-c", default="bitcoin", help="Coin name (default: bitcoin)")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(args.coin)

        if args.output == "json":
            print(json.dumps(result.model_dump(), indent=2, default=str))
        else:
            print(f"\n{'='*50}")
            print(f"Sentiment Analysis: {args.coin}")
            print(f"{'='*50}")
            print(f"\nFear & Greed Index: {result.fear_greed_index} (Signal: {result.sentiment_signal}/5)")
            print(f"Google Trends Score: {result.google_trends_score}")
            print(f"Google Trends Change: {result.google_trends_change:+.1f}%")
            print(f"Social Sentiment: {result.social_sentiment.upper()}")
            print(f"\nTimestamp: {result.timestamp}")
            print(f"{'='*50}\n")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()