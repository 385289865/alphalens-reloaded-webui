"""Predefined workflow templates for alphalens analysis.

Each template defines:
- steps: ordered list of atomic steps with dependencies
- configurable_params: what the frontend can adjust
"""

TEMPLATES: dict = {
    "full_analysis": {
        "template_id": "full_analysis",
        "name": "Complete Factor Analysis",
        "description": "Runs the entire alphalens pipeline: data prep, IC, returns, turnover, event study, and all charts",
        "version": "1.0.0",
        "steps": [
            {
                "step_type": "get_clean_factor_and_forward_returns",
                "depends_on": [],
                "output_key": "factor_data",
                "parameters": {"load_method": "from_session"},
            },
            {
                "step_type": "factor_information_coefficient",
                "depends_on": ["factor_data"],
                "output_key": "ic_df",
                "parameters": {},
            },
            {
                "step_type": "mean_information_coefficient",
                "depends_on": ["factor_data"],
                "output_key": "mean_ic",
                "parameters": {},
            },
            {
                "step_type": "factor_returns",
                "depends_on": ["factor_data"],
                "output_key": "factor_returns_df",
                "parameters": {},
            },
            {
                "step_type": "factor_alpha_beta",
                "depends_on": ["factor_data", "factor_returns_df"],
                "output_key": "alpha_beta_df",
                "parameters": {},
            },
            {
                "step_type": "mean_return_by_quantile",
                "depends_on": ["factor_data"],
                "output_key": "mean_returns",
                "parameters": {"by_date": False},
            },
            {
                "step_type": "compute_mean_returns_spread",
                "depends_on": ["mean_returns"],
                "output_key": "spread_df",
                "parameters": {},
            },
            {
                "step_type": "quantile_turnover",
                "depends_on": ["factor_data"],
                "output_key": "turnover",
                "parameters": {},
            },
            {
                "step_type": "factor_rank_autocorrelation",
                "depends_on": ["factor_data"],
                "output_key": "autocorrelation",
                "parameters": {},
            },
            {
                "step_type": "average_cumulative_return_by_quantile",
                "depends_on": ["factor_data"],
                "output_key": "event_study",
                "parameters": {},
            },
            {
                "step_type": "chart_ic_time_series",
                "depends_on": ["ic_df"],
                "output_key": "chart_ic_ts",
                "parameters": {},
            },
            {
                "step_type": "chart_ic_histogram",
                "depends_on": ["ic_df"],
                "output_key": "chart_ic_hist",
                "parameters": {},
            },
            {
                "step_type": "chart_ic_qq",
                "depends_on": ["ic_df"],
                "output_key": "chart_ic_qq",
                "parameters": {},
            },
            {
                "step_type": "chart_quantile_returns_bar",
                "depends_on": ["mean_returns"],
                "output_key": "chart_quantile_returns_bar",
                "parameters": {},
            },
            {
                "step_type": "chart_cumulative_returns",
                "depends_on": ["factor_returns_df"],
                "output_key": "chart_cumulative_returns",
                "parameters": {},
            },
            {
                "step_type": "chart_mean_quantile_spread",
                "depends_on": ["spread_df"],
                "output_key": "chart_mean_quantile_spread",
                "parameters": {},
            },
            {
                "step_type": "chart_quantile_turnover",
                "depends_on": ["turnover"],
                "output_key": "chart_quantile_turnover",
                "parameters": {},
            },
            {
                "step_type": "chart_rank_autocorrelation",
                "depends_on": ["autocorrelation"],
                "output_key": "chart_rank_autocorrelation",
                "parameters": {},
            },
        ],
        "configurable_params": [
            {"name": "periods", "type": "list[int]", "default": [1, 5, 10]},
            {"name": "quantiles", "type": "int", "default": 5},
            {"name": "long_short", "type": "bool", "default": True},
            {"name": "group_neutral", "type": "bool", "default": False},
            {"name": "filter_zscore", "type": "float", "default": 20.0},
            {"name": "max_loss", "type": "float", "default": 0.35},
        ],
    },

    "ic_only": {
        "template_id": "ic_only",
        "name": "IC Analysis Only",
        "description": "Only compute factor information coefficient and IC charts (fastest path)",
        "version": "1.0.0",
        "steps": [
            {
                "step_type": "get_clean_factor_and_forward_returns",
                "depends_on": [],
                "output_key": "factor_data",
                "parameters": {"load_method": "from_session"},
            },
            {
                "step_type": "factor_information_coefficient",
                "depends_on": ["factor_data"],
                "output_key": "ic_df",
                "parameters": {},
            },
            {
                "step_type": "chart_ic_time_series",
                "depends_on": ["ic_df"],
                "output_key": "chart_ic_ts",
                "parameters": {},
            },
            {
                "step_type": "chart_ic_histogram",
                "depends_on": ["ic_df"],
                "output_key": "chart_ic_hist",
                "parameters": {},
            },
            {
                "step_type": "chart_ic_qq",
                "depends_on": ["ic_df"],
                "output_key": "chart_ic_qq",
                "parameters": {},
            },
        ],
        "configurable_params": [
            {"name": "periods", "type": "list[int]", "default": [1, 5, 10]},
            {"name": "group_neutral", "type": "bool", "default": False},
        ],
    },

    "returns_only": {
        "template_id": "returns_only",
        "name": "Returns Analysis Only",
        "description": "Factor returns, alpha/beta, quantile analysis and charts",
        "version": "1.0.0",
        "steps": [
            {
                "step_type": "get_clean_factor_and_forward_returns",
                "depends_on": [],
                "output_key": "factor_data",
                "parameters": {"load_method": "from_session"},
            },
            {
                "step_type": "factor_returns",
                "depends_on": ["factor_data"],
                "output_key": "factor_returns_df",
                "parameters": {},
            },
            {
                "step_type": "factor_alpha_beta",
                "depends_on": ["factor_data", "factor_returns_df"],
                "output_key": "alpha_beta_df",
                "parameters": {},
            },
            {
                "step_type": "mean_return_by_quantile",
                "depends_on": ["factor_data"],
                "output_key": "mean_returns",
                "parameters": {"by_date": False},
            },
            {
                "step_type": "chart_cumulative_returns",
                "depends_on": ["factor_returns_df"],
                "output_key": "chart_cumulative_returns",
                "parameters": {},
            },
            {
                "step_type": "chart_quantile_returns_bar",
                "depends_on": ["mean_returns"],
                "output_key": "chart_quantile_returns_bar",
                "parameters": {},
            },
        ],
        "configurable_params": [
            {"name": "periods", "type": "list[int]", "default": [1, 5, 10]},
            {"name": "quantiles", "type": "int", "default": 5},
            {"name": "long_short", "type": "bool", "default": True},
            {"name": "group_neutral", "type": "bool", "default": False},
        ],
    },

    "event_study_only": {
        "template_id": "event_study_only",
        "name": "Event Study Only",
        "description": "Average cumulative return by quantile over event window",
        "version": "1.0.0",
        "steps": [
            {
                "step_type": "get_clean_factor_and_forward_returns",
                "depends_on": [],
                "output_key": "factor_data",
                "parameters": {"load_method": "from_session"},
            },
            {
                "step_type": "average_cumulative_return_by_quantile",
                "depends_on": ["factor_data"],
                "output_key": "event_study",
                "parameters": {},
            },
        ],
        "configurable_params": [
            {"name": "periods", "type": "list[int]", "default": [1, 5, 10]},
            {"name": "periods_before", "type": "int", "default": 10},
            {"name": "periods_after", "type": "int", "default": 15},
        ],
    },

    "turnover_only": {
        "template_id": "turnover_only",
        "name": "Turnover & Stability",
        "description": "Quantile turnover and rank autocorrelation analysis",
        "version": "1.0.0",
        "steps": [
            {
                "step_type": "get_clean_factor_and_forward_returns",
                "depends_on": [],
                "output_key": "factor_data",
                "parameters": {"load_method": "from_session"},
            },
            {
                "step_type": "quantile_turnover",
                "depends_on": ["factor_data"],
                "output_key": "turnover",
                "parameters": {},
            },
            {
                "step_type": "factor_rank_autocorrelation",
                "depends_on": ["factor_data"],
                "output_key": "autocorrelation",
                "parameters": {},
            },
            {
                "step_type": "chart_quantile_turnover",
                "depends_on": ["turnover"],
                "output_key": "chart_quantile_turnover",
                "parameters": {},
            },
            {
                "step_type": "chart_rank_autocorrelation",
                "depends_on": ["autocorrelation"],
                "output_key": "chart_rank_autocorrelation",
                "parameters": {},
            },
        ],
        "configurable_params": [
            {"name": "periods", "type": "list[int]", "default": [1, 5, 10]},
            {"name": "quantiles", "type": "int", "default": 5},
        ],
    },
}
