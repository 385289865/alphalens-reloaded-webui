export const CHART_TYPES = [
  'ic_time_series',
  'ic_histogram',
  'ic_qq_plot',
  'quantile_returns_bar',
  'cumulative_returns',
  'mean_quantile_spread',
  'quantile_turnover',
  'rank_autocorrelation',
] as const;

export const CHART_LABELS: Record<string, string> = {
  ic_time_series: 'IC Time Series',
  ic_histogram: 'IC Histogram',
  ic_qq_plot: 'IC Q-Q Plot',
  quantile_returns_bar: 'Quantile Returns Bar',
  cumulative_returns: 'Cumulative Returns',
  mean_quantile_spread: 'Mean Quantile Spread',
  quantile_turnover: 'Quantile Turnover',
  rank_autocorrelation: 'Rank Autocorrelation',
};

export const FILE_TYPE_LABELS: Record<string, string> = {
  factor: 'Factor Data',
  prices: 'Price Data',
  groups: 'Group Data',
};

export const PIPELINE_STEPS = [
  'validate',
  'load',
  'forward_returns',
  'quantile',
  'ic',
  'returns',
  'alpha_beta',
  'charts',
];

export const DEFAULT_PAGE_SIZE = 50;
export const ANALYSIS_POLL_INTERVAL = 2000;
