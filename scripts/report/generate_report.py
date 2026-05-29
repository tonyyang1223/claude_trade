#!/usr/bin/env python3
"""Generate cryptocurrency analysis reports.

This CLI tool generates HTML reports for cryptocurrency projects
based on comprehensive analysis across multiple dimensions.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.scorer import Scorer
from src.data.models import ProjectScore
from src.report.generator import ReportGenerator


def generate_single_report(
    coin_id: str,
    output_dir: Path,
    output_format: str = 'html',
    scorer: Optional[Scorer] = None,
    generator: Optional[ReportGenerator] = None
) -> None:
    """Generate report for a single project.

    Args:
        coin_id: Cryptocurrency ID (e.g., 'bitcoin')
        output_dir: Output directory path
        output_format: Output format ('html' or 'json')
        scorer: Scorer instance (optional)
        generator: ReportGenerator instance (optional)
    """
    if scorer is None:
        scorer = Scorer()
    if generator is None:
        generator = ReportGenerator()

    print(f"\n[分析] 正在分析项目: {coin_id}")

    # Generate score
    score = scorer.score_project(coin_id)

    # Create output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{coin_id}_report_{timestamp}.{output_format}"
    output_path = output_dir / filename

    # Generate output based on format
    if output_format == 'html':
        generator.save_report(score, output_path)
        print(f"[完成] HTML报告已保存: {output_path}")
    else:
        # JSON format
        output_path.write_text(
            score.model_dump_json(indent=2),
            encoding='utf-8'
        )
        print(f"[完成] JSON报告已保存: {output_path}")

    # Print summary
    print("\n" + "="*60)
    print(f"项目: {score.coin_name} ({score.symbol})")
    print(f"总分: {score.total_score:.1f} / 100")
    print(f"评级: {score.rating}")
    print(f"风险等级: {score.risk_level}")
    print(f"建议: {score.recommendation}")
    print("="*60)


def generate_comparison_report(
    coin_ids: list,
    output_dir: Path,
    output_format: str = 'html',
    scorer: Optional[Scorer] = None,
    generator: Optional[ReportGenerator] = None
) -> None:
    """Generate comparison report for multiple projects.

    Args:
        coin_ids: List of cryptocurrency IDs (2-5 projects)
        output_dir: Output directory path
        output_format: Output format ('html' or 'json')
        scorer: Scorer instance (optional)
        generator: ReportGenerator instance (optional)
    """
    from src.analysis.comparison import ProjectComparator

    if len(coin_ids) < 2:
        print("错误: 对比报告至少需要2个项目")
        sys.exit(1)

    if len(coin_ids) > 5:
        print("错误: 最多支持5个项目对比")
        sys.exit(1)

    if scorer is None:
        scorer = Scorer()
    if generator is None:
        generator = ReportGenerator()

    # Use ProjectComparator for proper comparison logic
    comparator = ProjectComparator(scorer=scorer)
    report = comparator.compare_projects(coin_ids)

    # Create output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    project_names = "_vs_".join(coin_ids)
    filename = f"comparison_{project_names}_{timestamp}.{output_format}"
    output_path = output_dir / filename

    # Generate output based on format
    if output_format == 'html':
        generator.save_comparison_report(report, output_path)
        print(f"\n[完成] 对比报告已保存: {output_path}")
    else:
        # JSON format
        output_path.write_text(
            report.model_dump_json(indent=2),
            encoding='utf-8'
        )
        print(f"\n[完成] JSON对比报告已保存: {output_path}")

    # Print summary
    print("\n" + "="*60)
    print("项目对比结果")
    print("="*60)
    for score in report.projects:
        marker = " [推荐]" if score.coin_id == report.winner else ""
        print(f"{score.coin_name} ({score.symbol}): {score.total_score:.1f} 分 - {score.rating}{marker}")
    print("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate cryptocurrency analysis reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate single project report
  python generate_report.py --coin bitcoin

  # Generate comparison report
  python generate_report.py --coins bitcoin ethereum cardano

  # Specify output directory and format
  python generate_report.py --coin bitcoin --output ./reports --format json
        """
    )

    # Single project option
    parser.add_argument(
        '--coin',
        type=str,
        help='Single cryptocurrency ID (e.g., bitcoin)'
    )

    # Multiple projects option
    parser.add_argument(
        '--coins',
        nargs='+',
        help='Multiple cryptocurrency IDs for comparison (2-5 projects)'
    )

    # Output directory
    parser.add_argument(
        '--output',
        type=str,
        default='data/reports',
        help='Output directory (default: data/reports)'
    )

    # Output format
    parser.add_argument(
        '--format',
        type=str,
        choices=['html', 'json'],
        default='html',
        help='Output format (default: html)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.coin and not args.coins:
        parser.print_help()
        print("\n错误: 必须指定 --coin 或 --coins 参数")
        sys.exit(1)

    if args.coin and args.coins:
        print("错误: --coin 和 --coins 参数不能同时使用")
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate report
    if args.coin:
        generate_single_report(
            coin_id=args.coin,
            output_dir=output_dir,
            output_format=args.format
        )
    else:
        generate_comparison_report(
            coin_ids=args.coins,
            output_dir=output_dir,
            output_format=args.format
        )


if __name__ == '__main__':
    main()
