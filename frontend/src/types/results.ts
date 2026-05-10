export interface AnalysisResults {
  analysis_id: string;
  status: string;
  config: Record<string, any> | null;
  ic: { data: IcRecord[] } | null;
  returns: ReturnsData | null;
  alpha_beta: { data: AlphaBetaRecord[] } | null;
  turnover: TurnoverData | null;
  summary_tables: SummaryTables | null;
  charts: Record<string, string> | null;
}

export interface IcRecord {
  date: string;
  period: string;
  ic_value: number;
}

export interface ReturnsData {
  analysis_id?: string;
  factor_returns: Record<string, any>[];
  returns_by_quantile: Record<string, any>[];
  cumulative_returns: Record<string, any>[];
}

export interface AlphaBetaRecord {
  metric: string;
  period: string;
  value: number;
}

export interface TurnoverData {
  analysis_id?: string;
  turnover: Record<string, any>[];
  autocorrelation: Record<string, any>[];
}

export interface SummaryTables {
  analysis_id?: string;
  alpha_beta: Record<string, any>[];
  returns_by_quantile: Record<string, any>[];
  ic: Record<string, any>[];
}

export interface ChartResponse {
  chart_type: string;
  image: string;
  format: string;
}

export interface PaginatedData {
  session_id: string;
  data: Record<string, any>[];
  page: number;
  page_size: number;
  total_rows: number;
}
