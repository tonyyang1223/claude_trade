"""Chart generation utilities using plotly."""
from typing import List
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.data.models import ProjectScore


class ChartGenerator:
    """Generate charts for cryptocurrency analysis reports."""

    DIMENSIONS = ['Market', 'Technical', 'Onchain', 'Sentiment', 'GitHub', 'Social', 'Risk']
    DIMENSION_FIELDS = [
        'market_score', 'technical_score', 'onchain_score',
        'sentiment_score', 'github_score', 'social_score', 'risk_score'
    ]

    def generate_radar_chart(self, score: ProjectScore) -> str:
        """Generate radar chart for project scores.

        Args:
            score: ProjectScore object containing dimension scores

        Returns:
            HTML string with embedded SVG chart
        """
        values = [
            score.market_score,
            score.technical_score,
            score.onchain_score,
            score.sentiment_score,
            score.github_score,
            score.social_score,
            score.risk_score
        ]
        # Close the radar chart by repeating the first value
        values_closed = values + [values[0]]
        dimensions_closed = self.DIMENSIONS + [self.DIMENSIONS[0]]

        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=dimensions_closed,
            fill='toself',
            name=f'{score.coin_name}',
            line=dict(color='#1f77b4', width=2),
            fillcolor='rgba(31, 119, 180, 0.3)'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 5],
                    tickmode='linear',
                    tick0=0,
                    dtick=1
                )
            ),
            showlegend=True,
            title=dict(
                text=f'{score.coin_name} ({score.symbol}) - Multi-dimensional Score',
                x=0.5,
                font=dict(size=16)
            ),
            width=600,
            height=500
        )

        return fig.to_html(include_plotlyjs='cdn', full_html=False)

    def generate_bar_chart(self, score: ProjectScore) -> str:
        """Generate bar chart for project scores.

        Color encoding:
        - Green: score >= 4
        - Yellow: score >= 3 and < 4
        - Red: score < 3

        Args:
            score: ProjectScore object containing dimension scores

        Returns:
            HTML string with bar chart
        """
        values = [
            score.market_score,
            score.technical_score,
            score.onchain_score,
            score.sentiment_score,
            score.github_score,
            score.social_score,
            score.risk_score
        ]

        colors = []
        for v in values:
            if v >= 4:
                colors.append('#2ecc71')  # Green
            elif v >= 3:
                colors.append('#f39c12')  # Yellow
            else:
                colors.append('#e74c3c')  # Red

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=self.DIMENSIONS,
            y=values,
            marker_color=colors,
            text=values,
            textposition='outside',
            name='Score'
        ))

        fig.update_layout(
            title=dict(
                text=f'{score.coin_name} ({score.symbol}) - Dimension Scores',
                x=0.5,
                font=dict(size=16)
            ),
            xaxis_title='Dimension',
            yaxis_title='Score',
            yaxis=dict(range=[0, 5.5], tickmode='linear', tick0=0, dtick=1),
            showlegend=False,
            width=700,
            height=450,
            margin=dict(t=80, b=60, l=60, r=40)
        )

        return fig.to_html(include_plotlyjs='cdn', full_html=False)

    def generate_comparison_chart(self, scores: List[ProjectScore]) -> str:
        """Generate grouped bar chart for project comparison.

        Args:
            scores: List of ProjectScore objects (2-3 projects recommended)

        Returns:
            HTML string with grouped bar chart
        """
        if not scores:
            raise ValueError("scores list cannot be empty")

        if len(scores) > 5:
            raise ValueError("Maximum 5 projects can be compared")

        # Color palette for different projects
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

        fig = go.Figure()

        for idx, score in enumerate(scores):
            values = [
                score.market_score,
                score.technical_score,
                score.onchain_score,
                score.sentiment_score,
                score.github_score,
                score.social_score,
                score.risk_score
            ]

            fig.add_trace(go.Bar(
                name=f'{score.coin_name} ({score.symbol})',
                x=self.DIMENSIONS,
                y=values,
                marker_color=colors[idx % len(colors)],
                text=values,
                textposition='outside'
            ))

        fig.update_layout(
            title=dict(
                text='Project Comparison - Dimension Scores',
                x=0.5,
                font=dict(size=16)
            ),
            xaxis_title='Dimension',
            yaxis_title='Score',
            yaxis=dict(range=[0, 5.5], tickmode='linear', tick0=0, dtick=1),
            barmode='group',
            bargap=0.15,
            bargroupgap=0.1,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            width=900,
            height=500,
            margin=dict(t=100, b=60, l=60, r=40)
        )

        return fig.to_html(include_plotlyjs='cdn', full_html=False)

    def generate_heatmap(self, scores: List[ProjectScore]) -> str:
        """Generate interactive heatmap for multi-coin analysis.

        Args:
            scores: List of ProjectScore objects

        Returns:
            HTML string with interactive heatmap
        """
        if not scores:
            raise ValueError("scores list cannot be empty")

        # Build matrix: rows = coins, columns = dimensions
        coin_names = [f"{s.coin_name} ({s.symbol})" for s in scores]

        z_values = []
        for score in scores:
            z_values.append([
                score.market_score,
                score.technical_score,
                score.onchain_score,
                score.sentiment_score,
                score.github_score,
                score.social_score,
                score.risk_score
            ])

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=z_values,
            x=self.DIMENSIONS,
            y=coin_names,
            colorscale=[
                [0, '#e74c3c'],      # Red for low scores
                [0.4, '#f39c12'],    # Yellow for medium scores
                [0.7, '#2ecc71'],    # Green for high scores
                [1, '#27ae60']       # Dark green for very high
            ],
            zmin=1,
            zmax=5,
            colorbar=dict(
                title='Score',
                tickmode='linear',
                tick0=1,
                dtick=1
            ),
            hoverongaps=False,
            hovertemplate='%{y}<br>%{x}: %{z}<extra></extra>'
        ))

        # Add text annotations
        for i, coin in enumerate(coin_names):
            for j, dim in enumerate(self.DIMENSIONS):
                fig.add_annotation(
                    x=j,
                    y=i,
                    text=str(z_values[i][j]),
                    showarrow=False,
                    font=dict(color='white', size=12, weight='bold')
                )

        fig.update_layout(
            title=dict(
                text='Multi-dimensional Score Heatmap',
                x=0.5,
                font=dict(size=18)
            ),
            xaxis_title='Dimension',
            yaxis_title='Cryptocurrency',
            width=900,
            height=max(600, len(scores) * 40 + 200),
            margin=dict(t=80, b=60, l=150, r=60),
            yaxis=dict(autorange='reversed')  # Top coin at top
        )

        return fig.to_html(include_plotlyjs='cdn', full_html=False)
