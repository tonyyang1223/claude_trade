"""Factor Correlation Analysis.

Computes correlation matrices for factor values:
- Pearson: Linear correlation
- Spearman: Rank correlation (more robust to outliers)

Supports:
- Rolling windows: 30d, 90d
- Multiple coins comparison
- Category-level aggregation
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy import stats

from src.factors import registry
from src.factors.store import FactorStore


class FactorCorrelationAnalyzer:
    """Analyzes correlations between factors.
    
    Example:
        >>> analyzer = FactorCorrelationAnalyzer()
        >>> matrix = analyzer.compute_correlation_matrix(days=30)
        >>> high_corr = analyzer.find_high_correlations(threshold=0.85)
    """
    
    def __init__(self, store_dir: Path = Path("data/factors")):
        self.store = FactorStore(store_dir)
        self._factor_data: Optional[pd.DataFrame] = None
    
    def load_factor_history(
        self,
        days: int = 90,
        factor_names: List[str] = None
    ) -> pd.DataFrame:
        """Load historical factor values into DataFrame.
        
        Args:
            days: Number of days to load
            factor_names: Specific factors to load (None = all)
        
        Returns:
            DataFrame with columns: date, factor_name, value
        """
        # Discover factors
        registry.discover_factors()
        
        if factor_names is None:
            factor_names = list(registry._factors.keys())
        
        # Load data from store
        records = []
        dates = self.store.list_available_dates()[-days:] if days else self.store.list_available_dates()
        
        for date_str in dates:
            factors = self.store.load_factors(date_str)
            for factor_name, factor_data in factors.items():
                if factor_name in factor_names:
                    records.append({
                        "date": date_str,
                        "factor_name": factor_name,
                        "raw_value": factor_data.get("raw_value", 0),
                        "normalized_value": factor_data.get("normalized_value"),
                        "score": factor_data.get("score")
                    })
        
        self._factor_data = pd.DataFrame(records)
        return self._factor_data
    
    def compute_correlation_matrix(
        self,
        days: int = 30,
        method: str = "pearson",
        value_column: str = "normalized_value"
    ) -> pd.DataFrame:
        """Compute factor correlation matrix.
        
        Args:
            days: Lookback period in days
            method: 'pearson' or 'spearman'
            value_column: Which value to use ('raw_value', 'normalized_value', 'score')
        
        Returns:
            Correlation matrix DataFrame
        """
        if self._factor_data is None:
            self.load_factor_history(days=days)
        
        # Filter to recent days
        recent_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        recent_data = self._factor_data[
            self._factor_data["date"] >= recent_date
        ].copy()
        
        # Pivot to wide format
        pivot = recent_data.pivot_table(
            index="date",
            columns="factor_name",
            values=value_column,
            aggfunc="first"
        )
        
        # Compute correlation
        if method == "pearson":
            corr_matrix = pivot.corr(method="pearson")
        elif method == "spearman":
            corr_matrix = pivot.corr(method="spearman")
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return corr_matrix
    
    def compute_rolling_correlation(
        self,
        factor1: str,
        factor2: str,
        window: int = 30
    ) -> pd.Series:
        """Compute rolling correlation between two factors.
        
        Args:
            factor1: First factor name
            factor2: Second factor name
            window: Rolling window size
        
        Returns:
            Series of rolling correlations
        """
        if self._factor_data is None:
            self.load_factor_history()
        
        pivot = self._factor_data.pivot_table(
            index="date",
            columns="factor_name",
            values="normalized_value",
            aggfunc="first"
        )
        
        if factor1 not in pivot.columns or factor2 not in pivot.columns:
            return pd.Series()
        
        rolling_corr = pivot[factor1].rolling(window).corr(pivot[factor2])
        return rolling_corr
    
    def find_high_correlations(
        self,
        threshold: float = 0.85,
        days: int = 30,
        method: str = "pearson"
    ) -> List[Dict[str, Any]]:
        """Find factor pairs with correlation above threshold.
        
        Args:
            threshold: Correlation threshold (default 0.85)
            days: Lookback period
            method: 'pearson' or 'spearman'
        
        Returns:
            List of {factor1, factor2, correlation} dicts
        """
        corr_matrix = self.compute_correlation_matrix(days=days, method=method)
        
        high_corr = []
        factors = list(corr_matrix.columns)
        
        for i, f1 in enumerate(factors):
            for j, f2 in enumerate(factors):
                if i < j:  # Upper triangle only
                    corr = corr_matrix.loc[f1, f2]
                    if pd.notna(corr) and abs(corr) >= threshold:
                        high_corr.append({
                            "factor1": f1,
                            "factor2": f2,
                            "correlation": round(corr, 4),
                            "abs_correlation": round(abs(corr), 4)
                        })
        
        return sorted(high_corr, key=lambda x: -x["abs_correlation"])
    
    def compute_category_correlation(
        self,
        days: int = 30,
        method: str = "pearson"
    ) -> pd.DataFrame:
        """Compute average correlation by category.
        
        Returns:
            Category-level correlation matrix
        """
        registry.discover_factors()
        
        # Get factor categories
        factor_categories = {}
        for name, meta in registry._factors.items():
            factor_categories[name] = meta.category.value
        
        # Compute factor correlation
        corr_matrix = self.compute_correlation_matrix(days=days, method=method)
        
        # Aggregate to category level
        categories = list(set(factor_categories.values()))
        cat_corr = pd.DataFrame(index=categories, columns=categories, dtype=float)
        
        for cat1 in categories:
            for cat2 in categories:
                factors1 = [f for f, c in factor_categories.items() if c == cat1 and f in corr_matrix.columns]
                factors2 = [f for f, c in factor_categories.items() if c == cat2 and f in corr_matrix.columns]
                
                if factors1 and factors2:
                    submatrix = corr_matrix.loc[factors1, factors2]
                    avg_corr = submatrix.values[np.triu_indices(min(len(factors1), len(factors2)), k=1)]
                    if len(avg_corr) > 0:
                        cat_corr.loc[cat1, cat2] = np.nanmean(avg_corr)
                    else:
                        cat_corr.loc[cat1, cat2] = 1.0
                else:
                    cat_corr.loc[cat1, cat2] = np.nan
        
        return cat_corr
    
    def export_correlation_report(
        self,
        output_path: Path = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate comprehensive correlation report.
        
        Args:
            output_path: Path to save report (None = return only)
            days: Lookback period
        
        Returns:
            Report dictionary
        """
        # Compute all correlations
        pearson = self.compute_correlation_matrix(days=days, method="pearson")
        spearman = self.compute_correlation_matrix(days=days, method="spearman")
        high_corr = self.find_high_correlations(threshold=0.85, days=days)
        cat_corr = self.compute_category_correlation(days=days)
        
        report = {
            "report_date": datetime.now().isoformat(),
            "lookback_days": days,
            "num_factors": len(pearson.columns),
            "summary": {
                "avg_pearson_correlation": float(pearson.values[np.triu_indices(len(pearson), k=1)].mean()),
                "max_correlation": float(pearson.values.max()),
                "min_correlation": float(pearson.values.min()),
                "high_correlation_pairs": len(high_corr)
            },
            "high_correlations": high_corr,
            "category_correlation": cat_corr.to_dict(),
            "pearson_matrix": pearson.to_dict(),
            "spearman_matrix": spearman.to_dict()
        }
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
        
        return report
