#!/usr/bin/env python3
"""Generate cryptocurrency analysis reports.

This CLI tool generates HTML reports for cryptocurrency projects
based on comprehensive analysis across multiple dimensions.
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.scorer import Scorer
from src.data.models import ProjectScore
from src.report.generator import ReportGenerator
from src.api.coingecko import CoinGeckoClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


def generate_top_n_report(
    top_n: int = 50,
    output_path: Optional[str] = None,
    scorer: Optional[Scorer] = None,
    generator: Optional[ReportGenerator] = None,
    coingecko: Optional[CoinGeckoClient] = None
) -> None:
    """Generate Top N coins comparison report.

    Args:
        top_n: Number of top coins to analyze (default: 50)
        output_path: Output file path (default: reports/top50_comparison.html)
        scorer: Scorer instance (optional)
        generator: ReportGenerator instance (optional)
        coingecko: CoinGeckoClient instance (optional)
    """
    # Try to import tqdm for progress bar
    try:
        from tqdm import tqdm
        has_tqdm = True
    except ImportError:
        has_tqdm = False
        logger.warning("tqdm not installed, progress bar disabled")

    # Initialize dependencies
    if scorer is None:
        scorer = Scorer()
    if generator is None:
        generator = ReportGenerator()
    if coingecko is None:
        coingecko = CoinGeckoClient()

    print(f"\n[开始] 获取市值排名 Top {top_n} 币种...")

    # Get top coins by market cap
    try:
        top_coins = coingecko.get_top_coins(limit=top_n)
        print(f"[成功] 获取到 {len(top_coins)} 个币种")
    except Exception as e:
        logger.error(f"获取Top币种失败: {e}")
        sys.exit(1)

    # Analyze each coin with error isolation
    results: List[ProjectScore] = []
    failed_coins: List[str] = []

    iterator = tqdm(top_coins, desc="分析币种", unit="coin") if has_tqdm else top_coins

    for idx, coin in enumerate(iterator):
        coin_id = coin['id']
        coin_name = coin.get('name', coin_id)

        if not has_tqdm:
            # Manual progress output
            print(f"[{idx + 1}/{len(top_coins)}] 正在分析: {coin_name} ({coin_id})")

        try:
            score = scorer.score_project(coin_id)
            results.append(score)
            logger.debug(f"{coin_id} 分析完成: {score.total_score:.1f}分")
        except Exception as e:
            logger.warning(f"{coin_id} 分析失败: {e}")
            failed_coins.append(coin_id)
            continue

    # Sort by total score (descending)
    results.sort(key=lambda x: x.total_score, reverse=True)

    print(f"\n[完成] 成功分析 {len(results)} 个币种")
    if failed_coins:
        print(f"[警告] {len(failed_coins)} 个币种分析失败: {', '.join(failed_coins[:5])}{'...' if len(failed_coins) > 5 else ''}")

    # Generate analysis summary
    analysis_summary = _generate_top_n_summary(results)

    # Set default output path
    if output_path is None:
        output_path = f"reports/top{top_n}_comparison.html"

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save report
    generator.save_top_n_report(results, analysis_summary, output_file)

    print(f"\n[完成] Top {top_n} 报告已保存: {output_file.absolute()}")

    # Print top 10 summary
    print("\n" + "="*60)
    print(f"Top 10 综合评分排名")
    print("="*60)
    for i, score in enumerate(results[:10], 1):
        print(f"{i}. {score.coin_name} ({score.symbol}): {score.total_score:.1f} 分 - {score.rating}")
    print("="*60)


def _generate_top_n_summary(scores: List[ProjectScore]) -> str:
    """Generate analysis summary for Top N report.

    Args:
        scores: List of ProjectScore objects (sorted by total_score desc)

    Returns:
        Analysis summary text
    """
    if not scores:
        return "无分析数据"

    summary_parts = []

    # Top performers
    top_1 = scores[0]
    summary_parts.append(
        f"<strong>{top_1.coin_name} ({top_1.symbol})</strong> "
        f"以 {top_1.total_score:.1f} 分位居榜首，评级为 {top_1.rating}，"
        f"风险等级为 {top_1.risk_level}。\n"
    )

    # High rated coins (A+ and A)
    high_rated = [s for s in scores if s.rating in ['A+', 'A']]
    if high_rated:
        coins_str = ', '.join([f"{s.coin_name} ({s.total_score:.1f})" for s in high_rated[:5]])
        summary_parts.append(f"\n<strong>高评级币种：</strong>{coins_str}")
        if len(high_rated) > 5:
            summary_parts.append(f" 等共 {len(high_rated)} 个")

    # Score distribution
    avg_score = sum(s.total_score for s in scores) / len(scores)
    summary_parts.append(f"\n\n<strong>评分分布：</strong>\n")
    summary_parts.append(f"- 平均分: {avg_score:.1f}\n")
    summary_parts.append(f"- 最高分: {scores[0].total_score:.1f} ({scores[0].coin_name})\n")
    summary_parts.append(f"- 最低分: {scores[-1].total_score:.1f} ({scores[-1].coin_name})\n")

    # Rating distribution
    rating_counts = {}
    for s in scores:
        rating_counts[s.rating] = rating_counts.get(s.rating, 0) + 1

    summary_parts.append(f"\n<strong>评级分布：</strong>\n")
    for rating in ['A+', 'A', 'B', 'C', 'D', 'F']:
        if rating in rating_counts:
            summary_parts.append(f"- {rating}: {rating_counts[rating]} 个项目\n")

    # Risk distribution
    risk_counts = {'low': 0, 'medium': 0, 'high': 0}
    for s in scores:
        risk_counts[s.risk_level] = risk_counts.get(s.risk_level, 0) + 1

    summary_parts.append(f"\n<strong>风险分布：</strong>\n")
    summary_parts.append(f"- 低风险: {risk_counts['low']} 个\n")
    summary_parts.append(f"- 中风险: {risk_counts['medium']} 个\n")
    summary_parts.append(f"- 高风险: {risk_counts['high']} 个\n")

    # Investment advice
    summary_parts.append(f"\n<strong>投资建议：</strong>\n")
    summary_parts.append(
        "本报告基于多维度量化分析生成，包括市场数据、技术指标、链上分析、"
        "市场情绪、GitHub活动、社交媒体和风险评估七个维度。"
        "高分项目通常具有较强的市场地位、良好的技术表现和较低的风险。"
        "建议投资者结合自身风险偏好和市场情况做出决策，注意分散投资。"
    )

    return ''.join(summary_parts)


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

  # Generate Top 50 coins report
  python generate_report.py --top-n 50

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

    # Top N option
    parser.add_argument(
        '--top-n',
        type=int,
        metavar='N',
        help='Generate report for top N coins by market cap'
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
    if not args.coin and not args.coins and not args.top_n:
        parser.print_help()
        print("\n错误: 必须指定 --coin, --coins 或 --top-n 参数")
        sys.exit(1)

    # Check for conflicting arguments
    provided_args = sum(1 for x in [args.coin, args.coins, args.top_n] if x is not None)
    if provided_args > 1:
        print("错误: --coin, --coins 和 --top-n 参数不能同时使用")
        sys.exit(1)

    # Handle Top N report
    if args.top_n:
        generate_top_n_report(
            top_n=args.top_n,
            output_path=f"reports/top{args.top_n}_comparison.html"
        )
        return

    # Create output directory for single/comparison reports
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
