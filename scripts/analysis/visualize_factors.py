#!/usr/bin/env python3
"""Factor visualization generator with Plotly.

Usage:
    python scripts/analysis/visualize_factors.py --days 30
    python scripts/analysis/visualize_factors.py --output reports/figures/
"""
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import pandas as pd
import numpy as np

# Plotly imports
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
except ImportError:
    print("Installing plotly...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"])
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FactorVisualizer:
    """Generate interactive factor visualizations."""

    def __init__(self, data_path: str = "data/processed", output_dir: str = "reports/figures"):
        self.data_path = Path(data_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_factor_data(self, days: int = 30) -> pd.DataFrame:
        """Load or generate factor data."""
        # Try processed data first
        factor_file = self.data_path / "factors.parquet"

        if factor_file.exists():
            df = pd.read_parquet(factor_file)
            logger.info(f"Loaded {len(df)} rows from {factor_file}")
        else:
            # Try to build from raw data
            df = self._build_from_raw(days)
            if df is None or df.empty:
                logger.warning(f"No processed data at {factor_file}, generating sample data")
                df = self._generate_sample_factors(days)

        # Filter to last N days
        if isinstance(df.index, pd.DatetimeIndex):
            cutoff = df.index.max() - pd.Timedelta(days=days)
            df = df[df.index >= cutoff]

        logger.info(f"Loaded {len(df)} rows for last {days} days")
        return df

    def _build_from_raw(self, days: int) -> Optional[pd.DataFrame]:
        """Try to build factor data from raw sources."""
        try:
            raw_path = Path("data/raw")
            if not raw_path.exists():
                return None

            # Collect data from all raw sources
            dfs = []

            # Coinglass (funding rate, open interest)
            coinglass_path = raw_path / "coinglass"
            if coinglass_path.exists():
                funding_data = self._load_coinglass_data(coinglass_path, days)
                if funding_data is not None:
                    dfs.append(funding_data)

            # Defillama (TVL)
            defillama_path = raw_path / "defillama"
            if defillama_path.exists():
                tvl_data = self._load_defillama_data(defillama_path, days)
                if tvl_data is not None:
                    dfs.append(tvl_data)

            # CoinGecko (price, volume)
            coingecko_path = raw_path / "coingecko"
            if coingecko_path.exists():
                price_data = self._load_coingecko_data(coingecko_path, days)
                if price_data is not None:
                    dfs.append(price_data)

            # GitHub (commits, stars)
            github_path = raw_path / "github"
            if github_path.exists():
                github_data = self._load_github_data(github_path, days)
                if github_data is not None:
                    dfs.append(github_data)

            # Reddit (mentions, sentiment)
            reddit_path = raw_path / "reddit"
            if reddit_path.exists():
                reddit_data = self._load_reddit_data(reddit_path, days)
                if reddit_data is not None:
                    dfs.append(reddit_data)

            if not dfs:
                return None

            # Merge all dataframes
            result = dfs[0]
            for df in dfs[1:]:
                result = result.join(df, how='outer')

            return result.sort_index()

        except Exception as e:
            logger.warning(f"Failed to build from raw data: {e}")
            return None

    def _load_coinglass_data(self, path: Path, days: int) -> Optional[pd.DataFrame]:
        """Load funding rate data from Coinglass."""
        files = sorted(path.glob("*.parquet"), reverse=True)[:days]
        if not files:
            return None

        records = []
        for f in files:
            try:
                df = pd.read_parquet(f)
                if 'fundingRate' in df.columns and 'fundingTime' in df.columns:
                    # Get average funding rate across exchanges
                    avg_rate = df['fundingRate'].mean()
                    date_str = f.stem  # YYYY-MM-DD
                    records.append({
                        'date': pd.to_datetime(date_str),
                        'funding_rate': avg_rate
                    })
            except Exception as e:
                logger.debug(f"Error loading {f}: {e}")
                continue

        if not records:
            return None

        result = pd.DataFrame(records).set_index('date')
        return result

    def _load_defillama_data(self, path: Path, days: int) -> Optional[pd.DataFrame]:
        """Load TVL data from Defillama."""
        files = sorted(path.glob("*.parquet"), reverse=True)[:days]
        if not files:
            return None

        records = []
        for f in files:
            try:
                df = pd.read_parquet(f)
                if 'tvl' in df.columns:
                    total_tvl = df['tvl'].sum()
                    avg_tvl_change_7d = df['tvl_change_7d'].mean() if 'tvl_change_7d' in df.columns else 0
                    date_str = f.stem
                    records.append({
                        'date': pd.to_datetime(date_str),
                        'total_tvl': total_tvl,
                        'tvl_change_7d': avg_tvl_change_7d
                    })
            except Exception as e:
                logger.debug(f"Error loading {f}: {e}")
                continue

        if not records:
            return None

        result = pd.DataFrame(records).set_index('date')
        return result

    def _load_coingecko_data(self, path: Path, days: int) -> Optional[pd.DataFrame]:
        """Load price/volume data from CoinGecko."""
        files = sorted(path.glob("*.parquet"), reverse=True)[:days]
        if not files:
            return None

        records = []
        for f in files:
            try:
                df = pd.read_parquet(f)
                # Focus on BTC data
                btc = df[df['id'] == 'bitcoin'] if 'id' in df.columns else df.iloc[:1]
                if len(btc) > 0:
                    record = {'date': pd.to_datetime(f.stem)}
                    if 'price_change_percentage_24h' in btc.columns:
                        record['price_momentum_1d'] = btc['price_change_percentage_24h'].iloc[0]
                    if 'total_volume' in btc.columns:
                        record['volume'] = btc['total_volume'].iloc[0]
                    if 'market_cap' in btc.columns:
                        record['market_cap'] = btc['market_cap'].iloc[0]
                    records.append(record)
            except Exception as e:
                logger.debug(f"Error loading {f}: {e}")
                continue

        if not records:
            return None

        result = pd.DataFrame(records).set_index('date')

        # Calculate derived metrics
        if 'price_momentum_1d' in result.columns:
            result['price_momentum_7d'] = result['price_momentum_1d'].rolling(7, min_periods=1).mean()

        return result

    def _load_github_data(self, path: Path, days: int) -> Optional[pd.DataFrame]:
        """Load GitHub activity data."""
        files = sorted(path.glob("*.parquet"), reverse=True)[:days]
        if not files:
            return None

        records = []
        for f in files:
            try:
                df = pd.read_parquet(f)
                if 'stars' in df.columns:
                    record = {
                        'date': pd.to_datetime(f.stem),
                        'github_stars': df['stars'].sum(),
                        'github_commits': df['commits'].sum() if 'commits' in df.columns else 0
                    }
                    records.append(record)
            except Exception as e:
                logger.debug(f"Error loading {f}: {e}")
                continue

        if not records:
            return None

        return pd.DataFrame(records).set_index('date')

    def _load_reddit_data(self, path: Path, days: int) -> Optional[pd.DataFrame]:
        """Load Reddit sentiment data."""
        files = sorted(path.glob("*.parquet"), reverse=True)[:days]
        if not files:
            return None

        records = []
        for f in files:
            try:
                df = pd.read_parquet(f)
                record = {'date': pd.to_datetime(f.stem)}
                if 'sentiment' in df.columns:
                    record['reddit_sentiment'] = df['sentiment'].mean()
                record['reddit_mentions'] = len(df)
                records.append(record)
            except Exception as e:
                logger.debug(f"Error loading {f}: {e}")
                continue

        if not records:
            return None

        return pd.DataFrame(records).set_index('date')

    def _generate_sample_factors(self, days: int) -> pd.DataFrame:
        """Generate sample factor data for demonstration."""
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

        np.random.seed(42)  # For reproducibility

        factors = {
            'funding_rate': np.random.uniform(-0.001, 0.001, days),
            'open_interest': np.random.uniform(1e9, 5e9, days),
            'tvl_change_7d': np.random.uniform(-10, 10, days),
            'stablecoin_flow': np.random.uniform(-1e8, 1e8, days),
            'github_commits': np.random.randint(10, 100, days),
            'github_stars': np.cumsum(np.random.randint(5, 50, days)) + 10000,
            'reddit_mentions': np.random.randint(50, 500, days),
            'reddit_sentiment': np.random.uniform(-1, 1, days),
            'price_momentum_1d': np.random.uniform(-10, 10, days),
            'price_momentum_7d': np.random.uniform(-20, 20, days),
            'volume_ratio': np.random.uniform(0.5, 2.0, days),
            'btc_dominance_change': np.random.uniform(-2, 2, days),
        }

        df = pd.DataFrame(factors, index=dates)
        df.index.name = 'date'
        logger.info(f"Generated sample data for {days} days with {len(factors)} factors")
        return df

    def plot_factor_trends(self, df: pd.DataFrame) -> str:
        """Generate multi-subplot time series."""
        if df.empty:
            logger.warning("No data to plot trends")
            return ""

        # Select numeric columns only
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            logger.warning("No numeric columns found")
            return ""

        # Limit to reasonable number of subplots
        max_subplots = 12
        cols_to_plot = numeric_cols[:max_subplots]

        # Determine subplot grid
        n_cols = min(2, len(cols_to_plot))
        n_rows = (len(cols_to_plot) + n_cols - 1) // n_cols

        # Create figure with subplots
        fig = make_subplots(
            rows=n_rows,
            cols=n_cols,
            subplot_titles=cols_to_plot,
            vertical_spacing=0.08,
            horizontal_spacing=0.12
        )

        # Add traces for each factor
        colors = px.colors.qualitative.Plotly
        for idx, col in enumerate(cols_to_plot):
            row = idx // n_cols + 1
            col_idx = idx % n_cols + 1

            # Normalize values for display
            data = df[col].dropna()
            if len(data) > 0:
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=data.values,
                        mode='lines+markers',
                        name=col,
                        line=dict(color=colors[idx % len(colors)], width=2),
                        marker=dict(size=4),
                        showlegend=False
                    ),
                    row=row,
                    col=col_idx
                )

                # Add trend line
                if len(data) > 5:
                    z = np.polyfit(range(len(data)), data.values, 1)
                    p = np.poly1d(z)
                    fig.add_trace(
                        go.Scatter(
                            x=data.index,
                            y=p(range(len(data))),
                            mode='lines',
                            name=f'{col} trend',
                            line=dict(color='rgba(255,0,0,0.3)', width=1, dash='dash'),
                            showlegend=False
                        ),
                        row=row,
                        col=col_idx
                    )

        # Update layout
        fig.update_layout(
            height=200 * n_rows,
            title=dict(
                text=f"Factor Trends ({len(cols_to_plot)} factors)",
                x=0.5,
                font=dict(size=16)
            ),
            template='plotly_white',
            hovermode='x unified'
        )

        # Update axes
        fig.update_xaxes(title_text="Date", gridcolor='lightgray')
        fig.update_yaxes(gridcolor='lightgray')

        # Save
        output_path = self.output_dir / "factor_trends.html"
        fig.write_html(str(output_path), include_plotlyjs='cdn')
        logger.info(f"Saved factor trends to {output_path}")
        return str(output_path)

    def plot_correlation_heatmap(self, df: pd.DataFrame) -> Tuple[str, List[Dict]]:
        """Generate correlation heatmap with warnings."""
        if df.empty:
            logger.warning("No data for correlation heatmap")
            return "", []

        # Select numeric columns only
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            logger.warning("Need at least 2 numeric columns for correlation")
            return "", []

        # Calculate correlation matrix
        corr_matrix = df[numeric_cols].corr()

        # Find high correlation pairs
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                col1, col2 = corr_matrix.columns[i], corr_matrix.columns[j]
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.8:
                    high_corr_pairs.append({
                        'factor_1': col1,
                        'factor_2': col2,
                        'correlation': round(corr_val, 4)
                    })

        # Log warnings
        if high_corr_pairs:
            logger.warning(f"Found {len(high_corr_pairs)} high-correlation pairs (|r| > 0.8):")
            for pair in high_corr_pairs:
                logger.warning(f"  {pair['factor_1']} <-> {pair['factor_2']}: {pair['correlation']}")

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu_r',
            zmid=0,
            zmin=-1,
            zmax=1,
            hoverongaps=False,
            hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.3f}<extra></extra>'
        ))

        # Add annotations for correlation values
        annotations = []
        for i in range(len(corr_matrix.columns)):
            for j in range(len(corr_matrix.columns)):
                val = corr_matrix.values[i, j]
                color = 'white' if abs(val) > 0.5 else 'black'
                annotations.append(
                    dict(
                        x=corr_matrix.columns[j],
                        y=corr_matrix.columns[i],
                        text=f'{val:.2f}',
                        showarrow=False,
                        font=dict(color=color, size=9)
                    )
                )

        fig.update_layout(
            title=dict(
                text="Factor Correlation Matrix",
                x=0.5,
                font=dict(size=16)
            ),
            annotations=annotations,
            template='plotly_white',
            width=800 + len(numeric_cols) * 20,
            height=800 + len(numeric_cols) * 20,
            xaxis=dict(side='bottom', tickangle=45),
            yaxis=dict(autorange='reversed')
        )

        # Add warning text if high correlations found
        if high_corr_pairs:
            warning_text = "<b>High Correlation Warnings (|r| > 0.8):</b><br>"
            warning_text += "<br>".join([
                f"• {p['factor_1']} ↔ {p['factor_2']}: {p['correlation']}"
                for p in high_corr_pairs[:5]  # Limit display
            ])
            if len(high_corr_pairs) > 5:
                warning_text += f"<br>... and {len(high_corr_pairs) - 5} more"

            fig.add_annotation(
                dict(
                    x=1.0,
                    y=0.0,
                    xref="paper",
                    yref="paper",
                    text=warning_text,
                    showarrow=False,
                    font=dict(size=11, color='red'),
                    align='left',
                    bgcolor='rgba(255,255,255,0.9)',
                    bordercolor='red',
                    borderwidth=1
                )
            )

        # Save
        output_path = self.output_dir / "factor_correlation_heatmap.html"
        fig.write_html(str(output_path), include_plotlyjs='cdn')
        logger.info(f"Saved correlation heatmap to {output_path}")
        return str(output_path), high_corr_pairs

    def plot_factor_distributions(self, df: pd.DataFrame) -> str:
        """Generate distribution plots."""
        if df.empty:
            logger.warning("No data for distribution plots")
            return ""

        # Select numeric columns only
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            logger.warning("No numeric columns found")
            return ""

        # Limit number of factors
        max_factors = 9
        cols_to_plot = numeric_cols[:max_factors]

        # Create violin plots using Plotly Express
        # Reshape data for plotting
        plot_data = []
        for col in cols_to_plot:
            data = df[col].dropna()
            for val in data:
                plot_data.append({
                    'Factor': col,
                    'Value': val
                })

        plot_df = pd.DataFrame(plot_data)

        if plot_df.empty:
            logger.warning("No valid data for distributions")
            return ""

        # Create violin plot
        fig = px.violin(
            plot_df,
            x='Factor',
            y='Value',
            box=True,
            points='outliers',
            color='Factor',
            color_discrete_sequence=px.colors.qualitative.Plotly
        )

        fig.update_layout(
            title=dict(
                text="Factor Distributions (Violin Plots)",
                x=0.5,
                font=dict(size=16)
            ),
            template='plotly_white',
            showlegend=False,
            xaxis=dict(tickangle=45),
            yaxis=dict(title_text="Value"),
            height=600
        )

        # Save
        output_path = self.output_dir / "factor_distributions.html"
        fig.write_html(str(output_path), include_plotlyjs='cdn')
        logger.info(f"Saved distribution plots to {output_path}")
        return str(output_path)

    def generate_all(self, days: int = 30) -> Dict[str, str]:
        """Generate all visualizations."""
        logger.info(f"Generating visualizations for last {days} days...")

        df = self.load_factor_data(days)

        if df.empty:
            logger.error("No data available for visualization")
            return {}

        # Create date-specific output directory
        date_dir = self.output_dir / datetime.now().strftime('%Y-%m-%d')
        date_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = date_dir

        files = {}

        # Generate trends
        try:
            trends_path = self.plot_factor_trends(df)
            if trends_path:
                files['trends'] = trends_path
        except Exception as e:
            logger.error(f"Failed to generate trends: {e}")

        # Generate correlation heatmap
        try:
            corr_path, high_corr = self.plot_correlation_heatmap(df)
            if corr_path:
                files['correlation'] = corr_path
                files['high_correlations'] = high_corr
        except Exception as e:
            logger.error(f"Failed to generate correlation heatmap: {e}")

        # Generate distributions
        try:
            dist_path = self.plot_factor_distributions(df)
            if dist_path:
                files['distributions'] = dist_path
        except Exception as e:
            logger.error(f"Failed to generate distributions: {e}")

        logger.info(f"Generated {len(files)} visualizations")
        return files


def main():
    parser = argparse.ArgumentParser(
        description="Generate factor visualizations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/analysis/visualize_factors.py --days 30
    python scripts/analysis/visualize_factors.py --days 7 --output reports/figures/
        """
    )
    parser.add_argument('--days', '-d', type=int, default=30,
                        help="Number of days to visualize (default: 30)")
    parser.add_argument('--output', '-o', default='reports/figures',
                        help="Output directory (default: reports/figures)")
    args = parser.parse_args()

    visualizer = FactorVisualizer(output_dir=args.output)
    files = visualizer.generate_all(days=args.days)

    print("\n" + "="*60)
    print("FACTOR VISUALIZATION REPORT")
    print("="*60)

    print("\nGenerated files:")
    for name, path in files.items():
        if name != 'high_correlations':
            print(f"  {name}: {path}")

    if 'high_correlations' in files and files['high_correlations']:
        print("\n" + "-"*60)
        print("HIGH CORRELATION WARNINGS (|r| > 0.8):")
        print("-"*60)
        for pair in files['high_correlations']:
            print(f"  {pair['factor_1']} <-> {pair['factor_2']}: {pair['correlation']}")

    print("\n" + "="*60)


if __name__ == '__main__':
    main()