"""ChartService - Generates matplotlib charts and converts to base64.

Uses Agg backend (non-interactive). Wraps alphalens plotting functions
and returns base64-encoded PNG images for the API response.
"""

import io
import base64
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from alphalens import plotting
from alphalens.utils import get_forward_returns_columns

from backend.app.services.data_service import DataService


class ChartService:
    """Generates matplotlib charts from analysis results stored in DuckDB."""

    def __init__(self, data_service: DataService):
        self.data_service = data_service

    def generate_ic_time_series(self, analysis_id: str) -> Optional[str]:
        """Generate IC time series chart."""
        try:
            ic_df = self._load_ic_as_wide(analysis_id)
            if ic_df is None or ic_df.empty:
                return None
            columns = get_forward_returns_columns(ic_df.columns)
            n_cols = len(columns)
            fig, axes = plt.subplots(n_cols, 1, figsize=(18, n_cols * 5))
            if n_cols == 1:
                axes = [axes]
            plotting.plot_ic_ts(ic_df, ax=axes)
            return self._fig_to_base64(fig)
        except Exception:
            return None

    def generate_ic_hist(self, analysis_id: str) -> Optional[str]:
        """Generate IC histogram chart."""
        try:
            ic_df = self._load_ic_as_wide(analysis_id)
            if ic_df is None or ic_df.empty:
                return None
            fig, axes = plt.subplots(1, len(ic_df.columns),
                                     figsize=(18, 5))
            if len(ic_df.columns) == 1:
                axes = [axes]
            for i, col in enumerate(ic_df.columns):
                plotting.plot_ic_hist(ic_df[[col]], ax=axes[i])
            return self._fig_to_base64(fig)
        except Exception:
            return None

    def generate_ic_qq(self, analysis_id: str) -> Optional[str]:
        """Generate IC Q-Q plot."""
        try:
            ic_df = self._load_ic_as_wide(analysis_id)
            if ic_df is None or ic_df.empty:
                return None
            fig, axes = plt.subplots(1, len(ic_df.columns),
                                     figsize=(18, 5))
            if len(ic_df.columns) == 1:
                axes = [axes]
            for i, col in enumerate(ic_df.columns):
                plotting.plot_ic_qq(ic_df[[col]], ax=axes[i])
            return self._fig_to_base64(fig)
        except Exception:
            return None

    def generate_quantile_returns_bar(self, analysis_id: str) -> Optional[str]:
        """Generate quantile returns bar chart."""
        try:
            mean_ret = self._load_mean_returns_as_table(analysis_id)
            if mean_ret is None or mean_ret.empty:
                return None
            fig, ax = plt.subplots(figsize=(18, 6))
            plotting.plot_quantile_returns_bar(mean_ret, ax=ax)
            return self._fig_to_base64(fig)
        except Exception:
            return None

    def generate_cumulative_returns(self, analysis_id: str) -> Optional[str]:
        """Generate cumulative returns chart."""
        try:
            factor_returns = self._load_factor_returns_as_wide(analysis_id)
            if factor_returns is None or factor_returns.empty:
                return None
            fig, ax = plt.subplots(figsize=(18, 6))
            plotting.plot_cumulative_returns(factor_returns, ax=ax)
            return self._fig_to_base64(fig)
        except Exception:
            return None

    def generate_mean_quantile_spread(self, analysis_id: str) -> Optional[str]:
        """Generate mean quantile returns spread time series."""
        try:
            spread = self.data_service.get_mean_return_spread(analysis_id)
            if spread.empty:
                return None
            # Pivot to wide format for alphalens
            spread_wide = spread.pivot(index="date", columns="period",
                                        values="spread")
            fig, ax = plt.subplots(figsize=(18, 6))
            plotting.plot_mean_quantile_returns_spread_time_series(
                spread_wide, ax=ax
            )
            return self._fig_to_base64(fig)
        except Exception:
            return None

    def generate_quantile_turnover(self, analysis_id: str) -> Optional[str]:
        """Generate top/bottom quantile turnover chart."""
        try:
            turnover = self.data_service.get_turnover_results(analysis_id)
            if turnover.empty:
                return None
            # Alphalens expects a dict of quantile -> Series
            turnover_dict = {}
            for q in turnover["quantile"].unique():
                qdata = turnover[turnover["quantile"] == q]
                turnover_dict[q] = pd.Series(
                    qdata["turnover"].values,
                    index=pd.to_datetime(qdata["date"].values)
                )
            fig, ax = plt.subplots(figsize=(18, 6))
            plotting.plot_top_bottom_quantile_turnover(turnover_dict, ax=ax)
            return self._fig_to_base64(fig)
        except Exception:
            return None

    def generate_autocorrelation(self, analysis_id: str) -> Optional[str]:
        """Generate factor rank autocorrelation chart."""
        try:
            autocorr = self.data_service.get_autocorrelation_results(analysis_id)
            if autocorr.empty:
                return None
            series = pd.Series(
                autocorr["autocorrelation"].values,
                index=pd.to_datetime(autocorr["date"].values)
            )
            fig, ax = plt.subplots(figsize=(18, 6))
            plotting.plot_factor_rank_auto_correlation(series, ax=ax)
            return self._fig_to_base64(fig)
        except Exception:
            return None

    def generate_all_charts(self, analysis_id: str) -> dict:
        """Generate all available charts for an analysis."""
        generators = {
            "ic_time_series": self.generate_ic_time_series,
            "ic_histogram": self.generate_ic_hist,
            "ic_qq_plot": self.generate_ic_qq,
            "quantile_returns_bar": self.generate_quantile_returns_bar,
            "cumulative_returns": self.generate_cumulative_returns,
            "mean_quantile_spread": self.generate_mean_quantile_spread,
            "quantile_turnover": self.generate_quantile_turnover,
            "rank_autocorrelation": self.generate_autocorrelation,
        }
        charts = {}
        for name, gen in generators.items():
            try:
                result = gen(analysis_id)
                if result:
                    charts[name] = result
            except Exception:
                charts[name] = None
        return charts

    # ============================================================
    # Internal helpers
    # ============================================================

    def _load_ic_as_wide(self, analysis_id: str) -> Optional[pd.DataFrame]:
        """Load IC results and pivot to wide format (date x period)."""
        ic = self.data_service.get_ic_results(analysis_id)
        if ic.empty:
            return None
        return ic.pivot(index="date", columns="period", values="ic_value")

    def _load_mean_returns_as_table(self, analysis_id: str) -> Optional[pd.DataFrame]:
        """Load mean returns as (quantile x period) table for alphalens."""
        data = self.data_service.get_returns_by_quantile(analysis_id)
        if data.empty:
            return None
        return data.pivot(index="factor_quantile", columns="period",
                           values="mean_return")

    def _load_factor_returns_as_wide(self, analysis_id: str) -> Optional[pd.DataFrame]:
        """Load factor returns and pivot to wide format."""
        returns = self.data_service.get_factor_returns(analysis_id)
        if returns.empty:
            return None
        return returns.pivot(index="date", columns="period",
                              values="return_value")

    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 data URI."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
        plt.close(fig)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{img_base64}"
