"""AnalysisService - Wraps alphalens-reloaded library functions.

Key principle: src/alphalens/ is NEVER modified. We import alphalens
as a standard library and call its functions with data loaded from DuckDB.

Pipeline:
1. load_data → 2. compute_forward_returns → 3. clean_factor_data →
4. compute_ic → 5. mean_return_by_quantile → 6. alpha_beta →
7. quantile_turnover → 8. autocorrelation → 9. cumulative_returns →
10. save_results
"""

from typing import Optional, Callable, Dict, Any

import pandas as pd
from alphalens import utils, performance as perf

from backend.app.services.data_service import DataService
from backend.app.models.schemas import AnalysisConfig


class AnalysisService:
    """Wraps alphalens functions and stores results via DataService."""

    def __init__(self, data_service: DataService):
        self.data_service = data_service

    def run_full_analysis(
        self,
        analysis_id: str,
        session_id: str,
        config: AnalysisConfig,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """Orchestrate the complete alphalens analysis pipeline."""
        self._report(progress_callback, "loading_data", 5)

        # Step 1: Load raw data from DuckDB
        factor = self.data_service.get_factor_df(session_id)
        prices = self.data_service.get_prices_df(session_id)

        self._report(progress_callback, "computing_forward_returns", 15)

        # Step 2: Run get_clean_factor_and_forward_returns
        groupby = None
        if config.by_group:
            groupby = self.data_service.get_group_mappings(session_id)

        factor_data = utils.get_clean_factor_and_forward_returns(
            factor=factor,
            prices=prices,
            periods=config.periods,
            quantiles=config.quantiles,
            bins=config.bins,
            groupby=groupby,
            filter_zscore=config.filter_zscore,
            max_loss=config.max_loss,
            zero_aware=config.zero_aware,
            cumulative_returns=config.cumulative_returns,
        )

        self._report(progress_callback, "saving_factor_data", 25)
        self.data_service.save_factor_data(analysis_id, factor_data)

        self._report(progress_callback, "computing_ic", 30)

        # Step 3: Information Coefficient
        ic = perf.factor_information_coefficient(
            factor_data,
            group_adjust=config.group_neutral,
            by_group=config.by_group,
        )
        self.data_service.save_ic_results(analysis_id, ic)

        self._report(progress_callback, "computing_returns_by_quantile", 40)

        # Step 4: Mean return by quantile
        mean_ret, std_err = perf.mean_return_by_quantile(
            factor_data,
            by_date=False,
            demeaned=config.long_short,
            group_adjust=config.group_neutral,
            by_group=config.by_group,
        )
        self.data_service.save_mean_return_by_quantile(analysis_id, mean_ret, std_err)

        # Step 5: Mean return spread (top - bottom quantile)
        max_q = int(factor_data["factor_quantile"].max())
        min_q = int(factor_data["factor_quantile"].min())
        mean_ret_bydate, std_daily = perf.mean_return_by_quantile(
            factor_data,
            by_date=True,
            demeaned=config.long_short,
            group_adjust=config.group_neutral,
        )
        spread, spread_std = perf.compute_mean_returns_spread(
            mean_ret_bydate, max_q, min_q, std_err=std_daily,
        )
        self.data_service.save_mean_return_spread(analysis_id, spread, spread_std)

        self._report(progress_callback, "computing_alpha_beta", 55)

        # Step 6: Alpha/Beta
        alpha_beta = perf.factor_alpha_beta(
            factor_data,
            demeaned=config.long_short,
            group_adjust=config.group_neutral,
            equal_weight=False,
        )
        self.data_service.save_alpha_beta(analysis_id, alpha_beta)

        self._report(progress_callback, "computing_turnover", 65)

        # Step 7: Quantile turnover
        # factor_quantile is on the factor_data, get unique time periods
        periods = config.periods if config.periods else [1, 5, 10]
        for period in periods[:1]:  # turnover computed on factor_quantile assignment
            quantiles = sorted(factor_data["factor_quantile"].dropna().unique())
            turnover_dict = {}
            for q in quantiles:
                try:
                    q_turnover = perf.quantile_turnover(
                        factor_data["factor_quantile"], quantile=q, period=period,
                    )
                    turnover_dict[int(q)] = q_turnover
                except Exception:
                    pass
            self.data_service.save_quantile_turnover(analysis_id, turnover_dict)

        # Step 8: Factor rank autocorrelation
        for period in periods[:1]:
            autocorr = perf.factor_rank_autocorrelation(factor_data, period=period)
            self.data_service.save_autocorrelation(analysis_id, autocorr)

        self._report(progress_callback, "computing_cumulative_returns", 80)

        # Step 9: Factor returns + cumulative returns
        factor_returns = perf.factor_returns(
            factor_data,
            demeaned=config.long_short,
            group_adjust=config.group_neutral,
            equal_weight=False,
        )
        self.data_service.save_factor_returns(analysis_id, factor_returns)

        # Cumulative returns for each period
        from alphalens.utils import get_forward_returns_columns
        fr_cols = get_forward_returns_columns(factor_returns.columns)
        for col in fr_cols:
            cum_ret = perf.cumulative_returns(factor_returns[col])
            self.data_service.save_cumulative_returns(
                analysis_id,
                pd.Series({cum_ret.index[i]: cum_ret.iloc[i]
                          for i in range(len(cum_ret))}, name=str(col))
            )

        self._report(progress_callback, "saving_config", 90)

        # Step 10: Save analysis config
        self.data_service.save_analysis_config(analysis_id, config.model_dump())

        self._report(progress_callback, "completed", 100)

    def _report(self, callback: Optional[Callable], stage: str, pct: int):
        if callback:
            callback(stage, pct)
