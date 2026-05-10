export interface AnalysisConfig {
  periods: number[];
  quantiles: number;
  bins: number | null;
  filter_zscore: number;
  max_loss: number;
  zero_aware: boolean;
  cumulative_returns: boolean;
  long_short: boolean;
  group_neutral: boolean;
  by_group: boolean;
  groupby_column: string | null;
}

export interface AnalysisRunRequest {
  session_id: string;
  config: AnalysisConfig;
}

export interface AnalysisRunResponse {
  analysis_id: string;
  task_id: string;
  status: string;
}

export interface AnalysisStatusResponse {
  analysis_id: string;
  task_id: string;
  status: string;
  current_stage: string | null;
  progress_pct: number;
  message: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export type AnalysisStatus = 'idle' | 'pending' | 'running' | 'completed' | 'failed';
