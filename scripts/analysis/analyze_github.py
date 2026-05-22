#!/usr/bin/env python3
"""Command-line interface for GitHub activity analysis.

Usage:
    python scripts/analysis/analyze_github.py --repo bitcoin/bitcoin
    python scripts/analysis/analyze_github.py --repo ethereum/go-ethereum --output json
"""
import argparse
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.github_analyzer import GithubAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze GitHub activity")
    parser.add_argument("--repo", "-r", required=True, help="Repository path (owner/repo)")
    parser.add_argument("--coin", "-c", default="", help="Coin name (optional)")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--token", "-t", help="GitHub API token (optional)")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        analyzer = GithubAnalyzer(api_token=args.token)
        result = analyzer.analyze(args.coin or args.repo.split("/")[1], args.repo)

        if args.output == "json":
            print(json.dumps(result.model_dump(), indent=2, default=str))
        else:
            print(f"\n{'='*50}")
            print(f"GitHub Activity Analysis: {args.repo}")
            print(f"{'='*50}")
            print(f"\nRepository: {result.repo_url}")
            print(f"Commits (30d): {result.commit_count_30d}")
            print(f"Contributors: {result.contributor_count}")
            print(f"Open Issues: {result.issue_count}")
            print(f"Open PRs: {result.pr_count}")
            print(f"Last Commit: {result.last_commit_date}")
            print(f"\nActivity Score: {result.activity_score}/5")
            print(f"\nTimestamp: {result.timestamp}")
            print(f"{'='*50}\n")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
