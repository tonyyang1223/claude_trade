"""Report generation utilities."""
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.data.models import ProjectScore, ComparisonReport
from src.report.charts import ChartGenerator


class ReportGenerator:
    """Generate HTML reports for cryptocurrency analysis."""

    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize report generator with template directory.

        Args:
            template_dir: Path to templates directory (defaults to src/report/templates)
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"

        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        self.chart_generator = ChartGenerator()

    def generate_html_report(self, score: ProjectScore) -> str:
        """Generate HTML report for a single project.

        Args:
            score: ProjectScore object containing all scoring data

        Returns:
            Complete HTML string for the report
        """
        # Generate charts
        radar_chart = self.chart_generator.generate_radar_chart(score)
        bar_chart = self.chart_generator.generate_bar_chart(score)

        # Load template
        template = self.env.get_template('full_report.html')

        # Render report
        html = template.render(
            score=score,
            radar_chart=radar_chart,
            bar_chart=bar_chart,
            generated_at=datetime.now()
        )

        return html

    def generate_comparison_report(self, report: ComparisonReport) -> str:
        """Generate HTML report for project comparison.

        Args:
            report: ComparisonReport object containing comparison data

        Returns:
            Complete HTML string for the comparison report
        """
        # Generate comparison chart
        comparison_chart = self.chart_generator.generate_comparison_chart(report.projects)

        # Load template
        template = self.env.get_template('comparison_report.html')

        # Render report
        html = template.render(
            projects=report.projects,
            comparison_matrix=report.comparison_matrix,
            winner=report.winner,
            analysis_summary=report.analysis_summary,
            created_at=report.created_at,
            comparison_chart=comparison_chart,
            generated_at=datetime.now()
        )

        return html

    def save_report(self, score: ProjectScore, output_path: Path) -> None:
        """Save HTML report to file.

        Args:
            score: ProjectScore object containing all scoring data
            output_path: Path where the report should be saved
        """
        output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate and save report
        html = self.generate_html_report(score)
        output_path.write_text(html, encoding='utf-8')

    def save_comparison_report(self, report: ComparisonReport, output_path: Path) -> None:
        """Save comparison report to file.

        Args:
            report: ComparisonReport object containing comparison data
            output_path: Path where the report should be saved
        """
        output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate and save report
        html = self.generate_comparison_report(report)
        output_path.write_text(html, encoding='utf-8')

    def generate_top_n_report(self, scores: list, analysis_summary: str) -> str:
        """Generate HTML report for Top N coins analysis.

        Args:
            scores: List of ProjectScore objects
            analysis_summary: Summary text for the analysis

        Returns:
            Complete HTML string for the report
        """
        # Generate heatmap
        heatmap = self.chart_generator.generate_heatmap(scores)

        # Load template
        template = self.env.get_template('top_n_report.html')

        # Render report
        html = template.render(
            scores=scores,
            heatmap=heatmap,
            analysis_summary=analysis_summary,
            generated_at=datetime.now()
        )

        return html

    def save_top_n_report(self, scores: list, analysis_summary: str, output_path: Path) -> None:
        """Save Top N report to file.

        Args:
            scores: List of ProjectScore objects
            analysis_summary: Summary text for the analysis
            output_path: Path where the report should be saved
        """
        output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate and save report
        html = self.generate_top_n_report(scores, analysis_summary)
        output_path.write_text(html, encoding='utf-8')
