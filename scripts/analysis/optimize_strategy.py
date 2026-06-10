#!/usr/bin/env python3
"""Strategy Parameter Optimization via Grid Search."""
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import pandas as pd
import numpy as np

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.analysis.backtest_simple import SimpleBacktester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_mock_data(days: int = 30) -> tuple:
    """Generate mock data for demonstration."""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    coins = ['bitcoin', 'ethereum', 'solana', 'avalanche-2', 'polygon']

    scores = pd.DataFrame(
        np.random.uniform(20, 80, (len(dates), len(coins))),
        index=dates, columns=coins
    )

    prices_data = {}
    for coin in coins:
        base = {'bitcoin': 45000, 'ethereum': 3000, 'solana': 100}.get(coin, 50)
        prices_data[coin] = base * np.cumprod(1 + np.random.normal(0.001, 0.03, len(dates)))

    prices = pd.DataFrame(prices_data, index=dates)
    return scores, prices


def run_optimization(
    scores: pd.DataFrame,
    prices: pd.DataFrame,
    periods: List[int],
    top_pcts: List[float],
    fee_rate: float
) -> List[Dict]:
    """Run grid search."""
    results = []
    for period in periods:
        for top_pct in top_pcts:
            freq = 'weekly' if period > 1 else 'daily'
            backtester = SimpleBacktester(fee_rate=fee_rate)
            metrics = backtester.run(scores, prices, top_pct, freq)
            results.append({
                'period': period,
                'top_pct': f"{top_pct:.0%}",
                'sharpe': metrics['sharpe_ratio'],
                'max_dd': metrics['max_drawdown'],
                'total_return': metrics['total_return'],
                'annual_return': metrics['annual_return'],
                'win_rate': metrics['win_rate'],
                'total_trades': metrics['total_trades']
            })
    return sorted(results, key=lambda x: x['sharpe'], reverse=True)


def generate_report(results: List[Dict], output_path: str) -> str:
    """Generate HTML report."""
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / 'optimization_result.html'

    rows = '\n'.join([
        f"<tr><td>{r['period']}</td><td>{r['top_pct']}</td><td>{r['sharpe']:.2f}</td>"
        f"<td>{r['max_dd']*100:.2f}%</td><td>{r['total_return']*100:+.2f}%</td>"
        f"<td>{r['annual_return']*100:+.2f}%</td><td>{r['win_rate']*100:.1f}%</td>"
        f"<td>{r['total_trades']}</td></tr>"
        for r in results
    ])

    html = f"""
<!DOCTYPE html>
<html><head><title>Optimization Results</title>
<style>
body{{font-family:Arial;margin:20px;background:#f5f5f5}}
.container{{max-width:1000px;margin:auto;background:white;padding:20px;border-radius:10px}}
table{{width:100%;border-collapse:collapse;margin-top:20px}}
th,td{{border:1px solid #ddd;padding:10px;text-align:center}}
th{{background:#4A90E2;color:white}}
tr:nth-child(even){{background:#f9f9f9}}
tr:first-child{{background:#e8f5e9;font-weight:bold}}
</style></head>
<body><div class="container">
<h1>📊 Strategy Parameter Optimization</h1>
<p>Best: Period={results[0]['period']}d, Top={results[0]['top_pct']}, Sharpe={results[0]['sharpe']:.2f}</p>
<table><thead><tr>
<th>周期</th><th>比例</th><th>夏普</th><th>回撤</th><th>收益</th><th>年化</th><th>胜率</th><th>交易</th>
</tr></thead><tbody>{rows}</tbody></table>
<p style="color:#999;font-size:12px;text-align:center">{datetime.now()}</p>
</div></body></html>"""

    with open(report_file, 'w') as f:
        f.write(html)
    return str(report_file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fee', type=float, default=0.001)
    parser.add_argument('--output', default='reports')
    parser.add_argument('--mock', action='store_true')
    args = parser.parse_args()

    periods = [3, 5, 7, 10, 14]
    top_pcts = [0.10, 0.20, 0.30]

    print("\n" + "="*60)
    print("Strategy Parameter Optimization")
    print(f"Periods: {periods} | Top%: {top_pcts} | Fee: {args.fee}")
    print("="*60)

    scores, prices = generate_mock_data(30)
    results = run_optimization(scores, prices, periods, top_pcts, args.fee)
    report = generate_report(results, args.output)

    print(f"\nBest: Period={results[0]['period']}d, Sharpe={results[0]['sharpe']:.2f}")
    print(f"Report: {report}\n")


if __name__ == '__main__':
    main()