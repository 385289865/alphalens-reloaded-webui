"""Atomic operation definitions wrapping alphalens functions.

Each operation wraps exactly one alphalens core function. Operations are
registered in OPERATION_REGISTRY and executed by SerialExecutor.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import io
import base64

import pandas as pd
from alphalens import utils, performance as perf, plotting


def _fig_to_base64(fig) -> str:
    """Convert a matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return f"data:image/png;base64,{b64}"


class AtomicOperation(ABC):
    """Base class for all atomic operations."""

    def __init__(self, data_service=None):
        self.data_service = data_service

    @property
    @abstractmethod
    def step_type(self) -> str:
        ...

    @abstractmethod
    def execute(
        self,
        inputs: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------

class GetCleanFactorOperation(AtomicOperation):
    step_type = "get_clean_factor_and_forward_returns"

    def execute(self, inputs, parameters):
        session_id = parameters.get("session_id")
        if not session_id or not self.data_service:
            raise ValueError("session_id and data_service required for data loading")

        factor = self.data_service.get_factor_df(session_id)
        prices = self.data_service.get_prices_df(session_id)

        groupby = None
        if parameters.get("by_group", False):
            groupby = self.data_service.get_group_mappings(session_id)

        factor_data = utils.get_clean_factor_and_forward_returns(
            factor=factor,
            prices=prices,
            periods=parameters.get("periods", [1, 5, 10]),
            quantiles=parameters.get("quantiles", 5),
            bins=parameters.get("bins"),
            groupby=groupby,
            filter_zscore=parameters.get("filter_zscore", 20.0),
            max_loss=parameters.get("max_loss", 0.35),
            zero_aware=parameters.get("zero_aware", False),
            cumulative_returns=parameters.get("cumulative_returns", True),
        )
        return {"factor_data": factor_data}


# ---------------------------------------------------------------------------
# IC computations
# ---------------------------------------------------------------------------

class FactorICOperation(AtomicOperation):
    step_type = "factor_information_coefficient"

    def execute(self, inputs, parameters):
        factor_data = inputs["factor_data"]
        ic = perf.factor_information_coefficient(
            factor_data,
            group_adjust=parameters.get("group_adjust", False),
            by_group=parameters.get("by_group", False),
        )
        return {"ic_df": ic}


class MeanICOperation(AtomicOperation):
    step_type = "mean_information_coefficient"

    def execute(self, inputs, parameters):
        factor_data = inputs["factor_data"]
        mean_ic = perf.mean_information_coefficient(
            factor_data,
            group_adjust=parameters.get("group_adjust", False),
            by_group=parameters.get("by_group", False),
        )
        return {"mean_ic": mean_ic}


# ---------------------------------------------------------------------------
# Returns analysis
# ---------------------------------------------------------------------------

class FactorReturnsOperation(AtomicOperation):
    step_type = "factor_returns"

    def execute(self, inputs, parameters):
        factor_data = inputs["factor_data"]
        returns = perf.factor_returns(
            factor_data,
            demeaned=parameters.get("demeaned", True),
            group_adjust=parameters.get("group_adjust", False),
            equal_weight=parameters.get("equal_weight", False),
        )
        return {"factor_returns_df": returns}


class FactorAlphaBetaOperation(AtomicOperation):
    step_type = "factor_alpha_beta"

    def execute(self, inputs, parameters):
        factor_data = inputs["factor_data"]
        factor_returns_df = inputs.get("factor_returns_df")
        alpha_beta = perf.factor_alpha_beta(
            factor_data,
            returns=factor_returns_df,
            demeaned=parameters.get("demeaned", True),
            group_adjust=parameters.get("group_adjust", False),
            equal_weight=parameters.get("equal_weight", False),
        )
        return {"alpha_beta_df": alpha_beta}


class MeanReturnByQuantileOperation(AtomicOperation):
    step_type = "mean_return_by_quantile"

    def execute(self, inputs, parameters):
        factor_data = inputs["factor_data"]
        mean_ret, std_err = perf.mean_return_by_quantile(
            factor_data,
            by_date=parameters.get("by_date", False),
            by_group=parameters.get("by_group", False),
            demeaned=parameters.get("demeaned", True),
            group_adjust=parameters.get("group_adjust", False),
        )
        return {"mean_returns": mean_ret, "std_err": std_err}


class ComputeSpreadOperation(AtomicOperation):
    step_type = "compute_mean_returns_spread"

    def execute(self, inputs, parameters):
        mean_returns = inputs["mean_returns"]
        std_err = inputs.get("std_err")
        quantile_levels = mean_returns.index.get_level_values("factor_quantile")
        max_q = int(quantile_levels.max())
        min_q = int(quantile_levels.min())
        spread, spread_std = perf.compute_mean_returns_spread(
            mean_returns, max_q, min_q, std_err=std_err,
        )
        return {"spread_df": spread, "spread_std": spread_std}


# ---------------------------------------------------------------------------
# Turnover / stability
# ---------------------------------------------------------------------------

class QuantileTurnoverOperation(AtomicOperation):
    step_type = "quantile_turnover"

    def execute(self, inputs, parameters):
        factor_data = inputs["factor_data"]
        quantiles = sorted(factor_data["factor_quantile"].dropna().unique())
        turnover_dict = {}
        for q in quantiles:
            q_turnover = perf.quantile_turnover(
                factor_data["factor_quantile"], quantile=q, period=1,
            )
            turnover_dict[int(q)] = q_turnover
        return {"turnover": turnover_dict}


class RankAutocorrelationOperation(AtomicOperation):
    step_type = "factor_rank_autocorrelation"

    def execute(self, inputs, parameters):
        factor_data = inputs["factor_data"]
        autocorr = perf.factor_rank_autocorrelation(factor_data, period=1)
        return {"autocorrelation": autocorr}


# ---------------------------------------------------------------------------
# Event study
# ---------------------------------------------------------------------------

class AverageCumulativeReturnOperation(AtomicOperation):
    step_type = "average_cumulative_return_by_quantile"

    def execute(self, inputs, parameters):
        factor_data = inputs["factor_data"]
        prices = inputs.get("prices")
        if prices is None:
            session_id = parameters.get("session_id")
            if session_id and self.data_service:
                prices = self.data_service.get_prices_df(session_id)
            else:
                raise ValueError("prices required for event study, provide in inputs or session_id")

        avg_cum = perf.average_cumulative_return_by_quantile(
            factor_data,
            prices,
            periods_before=parameters.get("periods_before", 10),
            periods_after=parameters.get("periods_after", 15),
            demeaned=parameters.get("demeaned", True),
            group_adjust=parameters.get("group_adjust", False),
            by_group=parameters.get("by_group", False),
        )
        return {"event_study": avg_cum}


# ---------------------------------------------------------------------------
# Chart operations
# ---------------------------------------------------------------------------

class ChartICTimeSeries(AtomicOperation):
    step_type = "chart_ic_time_series"

    def execute(self, inputs, parameters):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ic_df = inputs["ic_df"]
        fig, axes = plt.subplots(nrows=len(ic_df.columns), ncols=1, figsize=(10, 3 * len(ic_df.columns)))
        if len(ic_df.columns) == 1:
            axes = [axes]
        for ax, col in zip(axes, ic_df.columns):
            ax.set_title(col)
        plotting.plot_ic_ts(ic_df, ax=axes)
        return {"chart_ic_ts": _fig_to_base64(fig)}


class ChartICHistogram(AtomicOperation):
    step_type = "chart_ic_histogram"

    def execute(self, inputs, parameters):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ic_df = inputs["ic_df"]
        fig, axes = plt.subplots(nrows=len(ic_df.columns), ncols=1, figsize=(10, 3 * len(ic_df.columns)))
        if len(ic_df.columns) == 1:
            axes = [axes]
        for ax, col in zip(axes, ic_df.columns):
            ax.set_title(col)
        plotting.plot_ic_hist(ic_df, ax=axes)
        return {"chart_ic_hist": _fig_to_base64(fig)}


class ChartICQQ(AtomicOperation):
    step_type = "chart_ic_qq"

    def execute(self, inputs, parameters):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from scipy import stats
        ic_df = inputs["ic_df"]
        fig, axes = plt.subplots(nrows=len(ic_df.columns), ncols=1, figsize=(10, 3 * len(ic_df.columns)))
        if len(ic_df.columns) == 1:
            axes = [axes]
        for ax, col in zip(axes, ic_df.columns):
            ax.set_title(col)
        plotting.plot_ic_qq(ic_df, theoretical_dist=stats.norm, ax=axes)
        return {"chart_ic_qq": _fig_to_base64(fig)}


class ChartQuantileReturnsBar(AtomicOperation):
    step_type = "chart_quantile_returns_bar"

    def execute(self, inputs, parameters):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        mean_returns = inputs["mean_returns"]
        fig, ax = plt.subplots(figsize=(10, 5))
        plotting.plot_quantile_returns_bar(mean_returns, ax=ax)
        return {"chart_quantile_returns_bar": _fig_to_base64(fig)}


class ChartCumulativeReturns(AtomicOperation):
    step_type = "chart_cumulative_returns"

    def execute(self, inputs, parameters):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        factor_returns_df = inputs["factor_returns_df"]
        fr_cols = utils.get_forward_returns_columns(factor_returns_df.columns)
        fig, axes = plt.subplots(nrows=len(fr_cols), ncols=1, figsize=(10, 3 * len(fr_cols)))
        if len(fr_cols) == 1:
            axes = [axes]
        for ax, col in zip(axes, fr_cols):
            cum_ret = perf.cumulative_returns(factor_returns_df[col])
            plotting.plot_cumulative_returns(
                cum_ret, period=str(col), ax=ax,
            )
        return {"chart_cumulative_returns": _fig_to_base64(fig)}


class ChartMeanQuantileSpread(AtomicOperation):
    step_type = "chart_mean_quantile_spread"

    def execute(self, inputs, parameters):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        spread_df = inputs["spread_df"]
        spread_std = inputs.get("spread_std")
        fig, ax = plt.subplots(figsize=(10, 5))
        plotting.plot_mean_quantile_returns_spread_time_series(
            spread_df, std_err=spread_std, ax=ax,
        )
        return {"chart_mean_quantile_spread": _fig_to_base64(fig)}


class ChartQuantileTurnover(AtomicOperation):
    step_type = "chart_quantile_turnover"

    def execute(self, inputs, parameters):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        turnover = inputs["turnover"]
        fig, ax = plt.subplots(figsize=(10, 5))
        plotting.plot_top_bottom_quantile_turnover(turnover, ax=ax)
        return {"chart_quantile_turnover": _fig_to_base64(fig)}


class ChartRankAutocorrelation(AtomicOperation):
    step_type = "chart_rank_autocorrelation"

    def execute(self, inputs, parameters):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        autocorrelation = inputs["autocorrelation"]
        fig, ax = plt.subplots(figsize=(10, 5))
        plotting.plot_factor_rank_auto_correlation(autocorrelation, ax=ax)
        return {"chart_rank_autocorrelation": _fig_to_base64(fig)}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

OPERATION_REGISTRY: Dict[str, type] = {
    "get_clean_factor_and_forward_returns": GetCleanFactorOperation,
    "factor_information_coefficient": FactorICOperation,
    "mean_information_coefficient": MeanICOperation,
    "factor_returns": FactorReturnsOperation,
    "factor_alpha_beta": FactorAlphaBetaOperation,
    "mean_return_by_quantile": MeanReturnByQuantileOperation,
    "compute_mean_returns_spread": ComputeSpreadOperation,
    "quantile_turnover": QuantileTurnoverOperation,
    "factor_rank_autocorrelation": RankAutocorrelationOperation,
    "average_cumulative_return_by_quantile": AverageCumulativeReturnOperation,
    "chart_ic_time_series": ChartICTimeSeries,
    "chart_ic_histogram": ChartICHistogram,
    "chart_ic_qq": ChartICQQ,
    "chart_quantile_returns_bar": ChartQuantileReturnsBar,
    "chart_cumulative_returns": ChartCumulativeReturns,
    "chart_mean_quantile_spread": ChartMeanQuantileSpread,
    "chart_quantile_turnover": ChartQuantileTurnover,
    "chart_rank_autocorrelation": ChartRankAutocorrelation,
}
