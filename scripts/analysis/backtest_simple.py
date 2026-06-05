#!/usr/bin/env python3
"""Simple backtest framework adapted for cryptocurrency markets.

Key adaptations:
- UTC 00:00 as daily rebalance point (no traditional close)
- Configurable frequency: daily / weekly
- Handles 24/7 trading (no weekend gaps)
- Fee model for exchange costs
- Optional slippage model

Usage:
    python scripts/analysis/backtest_simple.py --days 30 --freq weekly
    python scripts/analysis/backtest_simple.py --top-pct 0.2 --fee 0.001
"""
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Plotly imports
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"])
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleBacktester:
    """Simple backtesting engine for crypto strategies.

    Supports:
    - UTC 00:00 daily rebalancing (no traditional close)
    - Configurable frequency: daily / weekly
    - Top N% coin selection by score
    - Equal weight portfolio
    - Fee and slippage costs

    Attributes:
        initial_capital: Starting capital in USDT
        fee_rate: Trading fee rate (e.g., 0.001 = 0.1%)
        slippage_rate: Optional slippage rate
        market_hours: '24/7' for crypto markets
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        fee_rate: float = 0.001,
        slippage_rate: float = 0.0
    ):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.market_hours = '24/7'
        self.capital = initial_capital
        self.reset()

    def reset(self):
        """Reset backtester state."""
        self.capital = self.initial_capital
        self.positions = {}  # {coin: quantity}
        self.trades = []  # List of trade records
        self.equity_curve = []  # List of (date, equity) tuples
        self.total_fees = 0.0
        self.daily_equity = {}  # {date: equity}

    def run(
        self,
        scores: pd.DataFrame,
        prices: pd.DataFrame,
        top_pct: float = 0.2,
        rebalance_freq: str = 'weekly',
        rebalance_time: str = '00:00',
        benchmark_coin: Optional[str] = None
    ) -> Dict:
        """Run backtest.

        Args:
            scores: DataFrame with dates as index, coins as columns, scores as values
            prices: DataFrame with dates as index, coins as columns, prices as values
            top_pct: Percentage of top coins to select (0.2 = 20%)
            rebalance_freq: 'daily' or 'weekly'
            rebalance_time: Time of rebalance (default '00:00' UTC)
            benchmark_coin: Coin to use as buy-and-hold benchmark

        Returns:
            Dict with performance metrics and trade history
        """
        self.reset()

        # Ensure dates are aligned
        common_dates = scores.index.intersection(prices.index)
        if len(common_dates) == 0:
            raise ValueError("No common dates between scores and prices")

        scores = scores.loc[common_dates]
        prices = prices.loc[common_dates]

        # Sort by date
        scores = scores.sort_index()
        prices = prices.sort_index()

        # Determine rebalance dates based on frequency
        if rebalance_freq == 'daily':
            rebalance_dates = scores.index.tolist()
        elif rebalance_freq == 'weekly':
            # Rebalance every 7 days starting from first date
            rebalance_dates = scores.index[::7].tolist()
        else:
            raise ValueError(f"Unknown rebalance_freq: {rebalance_freq}")

        logger.info(f"Backtest period: {scores.index[0]} to {scores.index[-1]}")
        logger.info(f"Rebalance frequency: {rebalance_freq}")
        logger.info(f"Total rebalance dates: {len(rebalance_dates)}")

        # Track portfolio value daily
        prev_positions = {}

        for i, date in enumerate(scores.index):
            # Get current prices (UTC 00:00)
            current_prices = prices.loc[date]

            # Check if this is a rebalance date
            if date in rebalance_dates:
                # Get scores for this date
                current_scores = scores.loc[date]

                # Select top N% coins by score
                valid_coins = current_scores.dropna()
                if len(valid_coins) == 0:
                    continue

                n_coins = max(1, int(len(valid_coins) * top_pct))
                top_coins = valid_coins.nlargest(n_coins).index.tolist()

                # Calculate new positions (equal weight)
                available_coins = [c for c in top_coins if c in current_prices and pd.notna(current_prices[c])]

                if len(available_coins) == 0:
                    continue

                # Calculate total portfolio value before rebalancing
                total_value = self.capital
                for coin, qty in self.positions.items():
                    if coin in current_prices and pd.notna(current_prices[coin]):
                        total_value += qty * current_prices[coin]

                # Calculate target allocation
                weight_per_coin = 1.0 / len(available_coins)
                target_value_per_coin = total_value * weight_per_coin

                # Execute trades with fees and slippage
                new_positions = {}
                total_trade_value = 0.0

                for coin in available_coins:
                    price = current_prices[coin]
                    # Apply slippage
                    effective_price = price * (1 + self.slippage_rate)

                    # Calculate quantity
                    quantity = target_value_per_coin / effective_price

                    # Apply fee (deduct from quantity)
                    fee = quantity * self.fee_rate
                    quantity_after_fee = quantity - fee

                    new_positions[coin] = quantity_after_fee
                    total_trade_value += target_value_per_coin
                    self.total_fees += fee * effective_price

                    # Record trade
                    prev_qty = self.positions.get(coin, 0)
                    trade_type = 'BUY' if quantity_after_fee > prev_qty else 'SELL'
                    if abs(quantity_after_fee - prev_qty) > 0.0001:
                        self.trades.append({
                            'date': date,
                            'coin': coin,
                            'type': trade_type,
                            'price': effective_price,
                            'quantity': abs(quantity_after_fee - prev_qty),
                            'fee': fee * effective_price
                        })

                # Update positions
                self.positions = new_positions
                self.capital = total_value - total_trade_value

            # Calculate daily equity
            equity = self.capital
            for coin, qty in self.positions.items():
                if coin in current_prices and pd.notna(current_prices[coin]):
                    equity += qty * current_prices[coin]

            self.equity_curve.append((date, equity))
            self.daily_equity[date] = equity

        # Calculate performance metrics
        metrics = self._calculate_metrics(prices, benchmark_coin)

        return metrics

    def _calculate_metrics(self, prices: pd.DataFrame, benchmark_coin: Optional[str] = None) -> Dict:
        """Calculate performance metrics.

        Returns:
            Dict with:
            - total_return: Total portfolio return
            - annual_return: Annualized return
            - sharpe_ratio: Risk-adjusted return
            - max_drawdown: Maximum drawdown
            - win_rate: Percentage of profitable trades
            - total_trades: Number of trades
            - total_fees: Total fees paid
            - trades: List of trade records
            - equity_curve: List of (date, equity) tuples
            - benchmark_return: Buy-and-hold benchmark return (if benchmark_coin provided)
        """
        if len(self.equity_curve) == 0:
            return {
                'total_return': 0.0,
                'annual_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'total_trades': 0,
                'total_fees': 0.0,
                'trades': [],
                'equity_curve': [],
                'benchmark_return': None
            }

        # Extract equity series
        dates = [e[0] for e in self.equity_curve]
        equity = [e[1] for e in self.equity_curve]
        equity_series = pd.Series(equity, index=dates)

        # Total return
        total_return = (equity[-1] - self.initial_capital) / self.initial_capital

        # Annual return
        days = (dates[-1] - dates[0]).days
        years = max(days / 365.0, 1/365)
        annual_return = (1 + total_return) ** (1 / years) - 1

        # Daily returns
        daily_returns = equity_series.pct_change().dropna()

        # Sharpe ratio (assuming 252 trading days, risk-free rate = 0)
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # Maximum drawdown
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax
        max_drawdown = drawdown.min()

        # Win rate
        if len(self.trades) > 0:
            # Calculate PnL for each trade (simplified)
            profitable_trades = 0
            total_trades_counted = 0

            for i, trade in enumerate(self.trades):
                if trade['type'] == 'SELL':
                    # Find corresponding buy trade
                    for j in range(i-1, -1, -1):
                        if self.trades[j]['type'] == 'BUY' and self.trades[j]['coin'] == trade['coin']:
                            if trade['price'] > self.trades[j]['price']:
                                profitable_trades += 1
                            total_trades_counted += 1
                            break

            win_rate = profitable_trades / max(total_trades_counted, 1)
        else:
            win_rate = 0.0

        # Benchmark comparison (BTC buy-and-hold)
        benchmark_return = None
        if benchmark_coin and benchmark_coin in prices.columns:
            first_date = prices.index[0]
            last_date = prices.index[-1]

            if first_date in prices.index and last_date in prices.index:
                start_price = prices.loc[first_date, benchmark_coin]
                end_price = prices.loc[last_date, benchmark_coin]

                if pd.notna(start_price) and pd.notna(end_price) and start_price > 0:
                    benchmark_return = (end_price - start_price) / start_price

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(self.trades),
            'total_fees': self.total_fees,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'benchmark_return': benchmark_return,
            'dates': dates,
            'equity': equity,
            'daily_returns': daily_returns.tolist() if len(daily_returns) > 0 else []
        }

    def generate_report(self, result: Dict, output_dir: Optional[str] = None) -> str:
        """Generate HTML report with charts.

        Args:
            result: Backtest result dict from run()
            output_dir: Output directory path

        Returns:
            Path to generated report
        """
        if output_dir is None:
            output_dir = 'reports'

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = output_path / f'backtest_report_{timestamp}.html'

        # Create equity curve chart
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('Portfolio Equity Curve', 'Drawdown', 'Daily Returns'),
            vertical_spacing=0.1,
            row_heights=[0.5, 0.25, 0.25]
        )

        dates = result.get('dates', [])
        equity = result.get('equity', [])

        if len(dates) > 0 and len(equity) > 0:
            # Equity curve
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=equity,
                    mode='lines',
                    name='Portfolio Value',
                    line=dict(color='#00D4AA', width=2)
                ),
                row=1, col=1
            )

            # Initial capital reference line
            fig.add_hline(
                y=self.initial_capital,
                line_dash="dash",
                line_color="gray",
                annotation_text="Initial Capital",
                row=1, col=1
            )

            # Drawdown chart
            equity_series = pd.Series(equity, index=dates)
            cummax = equity_series.cummax()
            drawdown = (equity_series - cummax) / cummax * 100

            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=drawdown,
                    mode='lines',
                    name='Drawdown',
                    fill='tozeroy',
                    line=dict(color='#FF6B6B', width=1),
                    fillcolor='rgba(255, 107, 107, 0.3)'
                ),
                row=2, col=1
            )

            # Daily returns histogram
            daily_returns = result.get('daily_returns', [])
            if len(daily_returns) > 0:
                fig.add_trace(
                    go.Histogram(
                        x=daily_returns,
                        name='Daily Returns',
                        marker_color='#4A90E2',
                        opacity=0.7,
                        nbinsx=50
                    ),
                    row=3, col=1
                )

        # Update layout
        fig.update_layout(
            title=dict(
                text='Crypto Strategy Backtest Report',
                font=dict(size=24, color='#333'),
                x=0.5
            ),
            showlegend=False,
            height=900,
            template='plotly_white',
            hovermode='x unified'
        )

        fig.update_xaxes(title_text='Date', row=1, col=1)
        fig.update_xaxes(title_text='Date', row=2, col=1)
        fig.update_xaxes(title_text='Daily Return', row=3, col=1)

        fig.update_yaxes(title_text='Portfolio Value (USDT)', row=1, col=1)
        fig.update_yaxes(title_text='Drawdown (%)', row=2, col=1)
        fig.update_yaxes(title_text='Count', row=3, col=1)

        # Generate HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Crypto Strategy Backtest Report</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    border-bottom: 3px solid #00D4AA;
                    padding-bottom: 10px;
                }}
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }}
                .metric-card {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                }}
                .metric-card.positive {{
                    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                }}
                .metric-card.negative {{
                    background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
                }}
                .metric-card.neutral {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .metric-label {{
                    font-size: 12px;
                    text-transform: uppercase;
                    opacity: 0.9;
                    margin-bottom: 5px;
                }}
                .metric-value {{
                    font-size: 28px;
                    font-weight: bold;
                }}
                .chart-container {{
                    margin: 30px 0;
                }}
                .trades-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                .trades-table th, .trades-table td {{
                    border: 1px solid #ddd;
                    padding: 10px;
                    text-align: left;
                }}
                .trades-table th {{
                    background-color: #4A90E2;
                    color: white;
                }}
                .trades-table tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                .config-section {{
                    background-color: #f9f9f9;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .config-item {{
                    display: inline-block;
                    margin-right: 20px;
                    margin-bottom: 10px;
                }}
                .config-label {{
                    font-weight: bold;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Crypto Strategy Backtest Report</h1>

                <div class="config-section">
                    <h3>Backtest Configuration</h3>
                    <div class="config-item">
                        <span class="config-label">Initial Capital:</span> ${self.initial_capital:,.2f}
                    </div>
                    <div class="config-item">
                        <span class="config-label">Fee Rate:</span> {self.fee_rate*100:.2f}%
                    </div>
                    <div class="config-item">
                        <span class="config-label">Slippage Rate:</span> {self.slippage_rate*100:.2f}%
                    </div>
                    <div class="config-item">
                        <span class="config-label">Market Hours:</span> {self.market_hours}
                    </div>
                </div>

                <h2>Performance Metrics</h2>
                <div class="metrics-grid">
                    <div class="metric-card {'positive' if result['total_return'] > 0 else 'negative'}">
                        <div class="metric-label">Total Return</div>
                        <div class="metric-value">{result['total_return']*100:+.2f}%</div>
                    </div>
                    <div class="metric-card {'positive' if result['annual_return'] > 0 else 'negative'}">
                        <div class="metric-label">Annual Return</div>
                        <div class="metric-value">{result['annual_return']*100:+.2f}%</div>
                    </div>
                    <div class="metric-card neutral">
                        <div class="metric-label">Sharpe Ratio</div>
                        <div class="metric-value">{result['sharpe_ratio']:.2f}</div>
                    </div>
                    <div class="metric-card negative">
                        <div class="metric-label">Max Drawdown</div>
                        <div class="metric-value">{result['max_drawdown']*100:.2f}%</div>
                    </div>
                    <div class="metric-card {'positive' if result['win_rate'] > 0.5 else 'neutral'}">
                        <div class="metric-label">Win Rate</div>
                        <div class="metric-value">{result['win_rate']*100:.1f}%</div>
                    </div>
                    <div class="metric-card neutral">
                        <div class="metric-label">Total Trades</div>
                        <div class="metric-value">{result['total_trades']}</div>
                    </div>
                    <div class="metric-card neutral">
                        <div class="metric-label">Total Fees</div>
                        <div class="metric-value">${result['total_fees']:.2f}</div>
                    </div>
                    {f'''<div class="metric-card {'positive' if result['benchmark_return'] > 0 else 'negative'}">
                        <div class="metric-label">Benchmark (BTC)</div>
                        <div class="metric-value">{result['benchmark_return']*100:+.2f}%</div>
                    </div>''' if result['benchmark_return'] is not None else ''}
                </div>

                <div class="chart-container">
                    {fig.to_html(full_html=False, include_plotlyjs='cdn')}
                </div>

                <h2>Trade History</h2>
                <p>Total trades: {len(result['trades'])}</p>

                {self._generate_trades_table(result['trades'][:50]) if len(result['trades']) > 0 else '<p>No trades executed</p>'}

                {f'<p><em>Showing first 50 of {len(result["trades"])} trades</em></p>' if len(result['trades']) > 50 else ''}

                <hr>
                <p style="text-align: center; color: #999; font-size: 12px;">
                    Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
                    Crypto-adapted backtest framework | Rebalance at UTC 00:00
                </p>
            </div>
        </body>
        </html>
        """

        # Write to file
        with open(report_file, 'w') as f:
            f.write(html_content)

        logger.info(f"Report generated: {report_file}")
        return str(report_file)

    def _generate_trades_table(self, trades: List[Dict]) -> str:
        """Generate HTML table for trades."""
        if not trades:
            return '<p>No trades to display</p>'

        rows = []
        for trade in trades:
            row = f"""
            <tr>
                <td>{trade.get('date', 'N/A')}</td>
                <td>{trade.get('coin', 'N/A')}</td>
                <td style="color: {'green' if trade.get('type') == 'BUY' else 'red'}">{trade.get('type', 'N/A')}</td>
                <td>${trade.get('price', 0):.2f}</td>
                <td>{trade.get('quantity', 0):.6f}</td>
                <td>${trade.get('fee', 0):.2f}</td>
            </tr>
            """
            rows.append(row)

        return f"""
        <table class="trades-table">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Coin</th>
                    <th>Type</th>
                    <th>Price</th>
                    <th>Quantity</th>
                    <th>Fee</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """


def main():
    parser = argparse.ArgumentParser(
        description="Simple backtest framework for crypto",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/analysis/backtest_simple.py --days 30 --freq weekly
    python scripts/analysis/backtest_simple.py --days 60 --freq daily --top-pct 0.3
    python scripts/analysis/backtest_simple.py --capital 50000 --fee 0.0005
        """
    )
    parser.add_argument('--days', '-d', type=int, default=30,
                        help="Days to backtest (default: 30)")
    parser.add_argument('--freq', '-f', choices=['daily', 'weekly'], default='weekly',
                        help="Rebalance frequency (default: weekly)")
    parser.add_argument('--top-pct', type=float, default=0.2,
                        help="Top percentage of coins to select (default: 0.2 = 20%%)")
    parser.add_argument('--fee', type=float, default=0.001,
                        help="Trading fee rate (default: 0.001 = 0.1%%)")
    parser.add_argument('--slippage', type=float, default=0.0,
                        help="Slippage rate (default: 0.0)")
    parser.add_argument('--capital', type=float, default=10000,
                        help="Initial capital in USDT (default: 10000)")
    parser.add_argument('--output', '-o', default='reports',
                        help="Output directory for reports (default: reports)")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("Crypto Strategy Backtest")
    print("="*60)
    print(f"Period: {args.days} days")
    print(f"Frequency: {args.freq}")
    print(f"Top coins: {args.top_pct*100:.0f}%")
    print(f"Fee rate: {args.fee*100:.2f}%")
    print(f"Initial capital: ${args.capital:,.2f}")
    print("="*60 + "\n")

    # Generate sample data for demonstration
    # In practice, load from collected data
    np.random.seed(42)  # For reproducible results

    dates = pd.date_range(end=datetime.now(), periods=args.days, freq='D')
    coins = ['BTC', 'ETH', 'SOL', 'AVAX', 'MATIC', 'DOT', 'LINK', 'ADA', 'ATOM', 'UNI']

    # Generate scores (higher = better)
    scores = pd.DataFrame(
        np.random.uniform(20, 80, (len(dates), len(coins))),
        index=dates,
        columns=coins
    )

    # Generate realistic price movements
    base_prices = {
        'BTC': 45000, 'ETH': 3000, 'SOL': 100, 'AVAX': 80,
        'MATIC': 1.5, 'DOT': 25, 'LINK': 15, 'ADA': 0.5,
        'ATOM': 20, 'UNI': 10
    }

    prices_data = {}
    for coin in coins:
        base = base_prices.get(coin, 100)
        # Random walk with slight upward trend
        daily_returns = np.random.normal(0.001, 0.03, len(dates))
        prices_data[coin] = base * np.cumprod(1 + daily_returns)

    prices = pd.DataFrame(prices_data, index=dates)

    # Run backtest
    backtester = SimpleBacktester(
        initial_capital=args.capital,
        fee_rate=args.fee,
        slippage_rate=args.slippage
    )

    result = backtester.run(
        scores=scores,
        prices=prices,
        top_pct=args.top_pct,
        rebalance_freq=args.freq,
        benchmark_coin='BTC'
    )

    # Generate report
    report_path = backtester.generate_report(result, output_dir=args.output)

    # Print summary
    print("\n" + "="*60)
    print("Backtest Results")
    print("="*60)
    print(f"Total Return:      {result['total_return']*100:+.2f}%")
    print(f"Annual Return:     {result['annual_return']*100:+.2f}%")
    print(f"Sharpe Ratio:      {result['sharpe_ratio']:.2f}")
    print(f"Max Drawdown:      {result['max_drawdown']*100:.2f}%")
    print(f"Win Rate:          {result['win_rate']*100:.1f}%")
    print(f"Total Trades:      {result['total_trades']}")
    print(f"Total Fees:        ${result['total_fees']:.2f}")

    if result['benchmark_return'] is not None:
        print(f"\nBenchmark (BTC):   {result['benchmark_return']*100:+.2f}%")
        excess = result['total_return'] - result['benchmark_return']
        print(f"Excess Return:     {excess*100:+.2f}%")

    print("\n" + "="*60)
    print(f"Report: {report_path}")
    print("="*60 + "\n")

    return result


if __name__ == '__main__':
    main()