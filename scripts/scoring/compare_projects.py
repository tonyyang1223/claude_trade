#!/usr/bin/env python3
"""Compare multiple cryptocurrency projects.

This CLI tool generates comparison reports for 2-5 cryptocurrency projects,
analyzing them across multiple dimensions and providing investment recommendations.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.comparison import ProjectComparator
from src.data.models import ComparisonReport


def format_text_report(report: ComparisonReport) -> str:
    """Format comparison report as plain text.

    Args:
        report: ComparisonReport object

    Returns:
        Formatted text string
    """
    lines = []

    # Header
    lines.append("=" * 70)
    lines.append("项目对比分析报告".center(70))
    lines.append("=" * 70)
    lines.append(f"分析时间: {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Winner section
    winner_score = next(p for p in report.projects if p.coin_id == report.winner)
    lines.append("-" * 70)
    lines.append(f"推荐项目: {winner_score.coin_name} ({winner_score.symbol})")
    lines.append(f"综合评分: {winner_score.total_score:.1f} / 100")
    lines.append(f"评级: {winner_score.rating}")
    lines.append(f"风险等级: {winner_score.risk_level}")
    lines.append("-" * 70)
    lines.append("")

    # All projects summary
    lines.append("项目概览:")
    lines.append("")
    for project in report.projects:
        marker = " [推荐]" if project.coin_id == report.winner else ""
        lines.append(
            f"  {project.coin_name} ({project.symbol}): "
            f"{project.total_score:.1f}分 - {project.rating}{marker}"
        )
    lines.append("")

    # Comparison table
    lines.append("维度对比:")
    lines.append("")
    header = f"{'维度':<20}"
    for p in report.projects:
        header += f"{p.symbol:>10}"
    lines.append(header)
    lines.append("-" * 70)

    dimensions = [
        ('市场数据', 'market_score'),
        ('技术指标', 'technical_score'),
        ('链上分析', 'onchain_score'),
        ('市场情绪', 'sentiment_score'),
        ('GitHub活动', 'github_score'),
        ('社交媒体', 'social_score'),
        ('风险评估', 'risk_score'),
    ]

    for dim_name, attr in dimensions:
        row = f"{dim_name:<20}"
        for p in report.projects:
            score = getattr(p, attr)
            row += f"{score:>10}"
        lines.append(row)

    lines.append("-" * 70)

    # Total row
    total_row = f"{'总分':<20}"
    for p in report.projects:
        total_row += f"{p.total_score:>10.1f}"
    lines.append(total_row)
    lines.append("")

    # Analysis summary (strip HTML tags for text output)
    summary = report.analysis_summary
    summary = summary.replace('<strong>', '').replace('</strong>', '')
    lines.append("分析总结:")
    lines.append("")
    lines.append(summary)
    lines.append("")

    # Footer
    lines.append("=" * 70)
    lines.append("数据来源: CoinGecko, CoinMarketCap, Alternative.me, GitHub")
    lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    return "\n".join(lines)


def format_markdown_report(report: ComparisonReport) -> str:
    """Format comparison report as markdown.

    Args:
        report: ComparisonReport object

    Returns:
        Formatted markdown string
    """
    lines = []

    # Header
    lines.append("# 项目对比分析报告")
    lines.append("")
    lines.append(f"**分析时间**: {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Winner section
    winner_score = next(p for p in report.projects if p.coin_id == report.winner)
    lines.append("## 推荐项目")
    lines.append("")
    lines.append(f"**{winner_score.coin_name} ({winner_score.symbol})**")
    lines.append("")
    lines.append(f"- 综合评分: **{winner_score.total_score:.1f} / 100**")
    lines.append(f"- 评级: **{winner_score.rating}**")
    lines.append(f"- 风险等级: **{winner_score.risk_level}**")
    lines.append("")

    # Projects summary
    lines.append("## 项目概览")
    lines.append("")
    lines.append("| 项目 | 符号 | 总分 | 评级 | 状态 |")
    lines.append("|------|------|------|------|------|")

    for project in report.projects:
        status = "推荐" if project.coin_id == report.winner else ""
        lines.append(
            f"| {project.coin_name} | {project.symbol} | "
            f"{project.total_score:.1f} | {project.rating} | {status} |"
        )
    lines.append("")

    # Comparison table
    lines.append("## 维度对比")
    lines.append("")

    # Build header
    header = "| 维度 |"
    separator = "|------|"
    for p in report.projects:
        header += f" {p.symbol} |"
        separator += "------|"
    lines.append(header)
    lines.append(separator)

    # Dimension rows
    dimensions = [
        ('市场数据', 'market_score'),
        ('技术指标', 'technical_score'),
        ('链上分析', 'onchain_score'),
        ('市场情绪', 'sentiment_score'),
        ('GitHub活动', 'github_score'),
        ('社交媒体', 'social_score'),
        ('风险评估', 'risk_score'),
    ]

    for dim_name, attr in dimensions:
        row = f"| {dim_name} |"
        for p in report.projects:
            score = getattr(p, attr)
            row += f" {score} |"
        lines.append(row)

    # Total row
    total_row = "| **总分** |"
    for p in report.projects:
        total_row += f" **{p.total_score:.1f}** |"
    lines.append(total_row)
    lines.append("")

    # Analysis summary
    lines.append("## 分析总结")
    lines.append("")
    # Convert HTML to markdown
    summary = report.analysis_summary
    summary = summary.replace('<strong>', '**').replace('</strong>', '**')
    lines.append(summary)
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*数据来源: CoinGecko, CoinMarketCap, Alternative.me, GitHub*")
    lines.append("")
    lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Compare cryptocurrency projects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two projects
  python compare_projects.py --coins bitcoin ethereum

  # Compare three projects with markdown output
  python compare_projects.py --coins bitcoin ethereum cardano --output markdown

  # Save comparison to file
  python compare_projects.py --coins bitcoin ethereum --file comparison.txt
        """
    )

    # Required arguments
    parser.add_argument(
        '--coins',
        nargs='+',
        required=True,
        help='Cryptocurrency IDs to compare (2-5 projects)'
    )

    # Output format
    parser.add_argument(
        '--output',
        type=str,
        choices=['json', 'text', 'markdown'],
        default='text',
        help='Output format (default: text)'
    )

    # Output file
    parser.add_argument(
        '--file',
        type=str,
        help='Save output to file (optional)'
    )

    args = parser.parse_args()

    # Validate coin count
    if len(args.coins) < 2:
        print("错误: 至少需要2个项目进行对比")
        sys.exit(1)

    if len(args.coins) > 5:
        print("错误: 最多支持5个项目对比")
        sys.exit(1)

    # Perform comparison
    print(f"\n正在对比 {len(args.coins)} 个项目: {', '.join(args.coins)}\n")

    try:
        comparator = ProjectComparator()
        report = comparator.compare_projects(args.coins)
    except Exception as e:
        print(f"错误: 对比分析失败 - {e}")
        sys.exit(1)

    # Format output
    if args.output == 'json':
        output = report.model_dump_json(indent=2)
    elif args.output == 'markdown':
        output = format_markdown_report(report)
    else:
        output = format_text_report(report)

    # Output result
    if args.file:
        output_path = Path(args.file)
        output_path.write_text(output, encoding='utf-8')
        print(f"对比结果已保存到: {output_path}")
    else:
        print(output)


if __name__ == '__main__':
    main()
