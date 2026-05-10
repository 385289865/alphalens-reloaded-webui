export interface UploadResponse {
  session_id: string;
  file_id: string;
  file_type: string;
  rows_ingested: number;
  columns: string[];
}

export interface PreviewResponse {
  columns: string[];
  dtypes: Record<string, string>;
  rows: Record<string, any>[];
  total_rows_preview: number;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string;
  progress_pct: number | null;
  current_stage: string | null;
  message: string | null;
}

export interface TaskSummary {
  task_id: string;
  analysis_id: string | null;
  status: string;
  created_at: string | null;
}

export interface HealthResponse {
  status: string;
  version: string;
}

export type FileType = 'factor' | 'prices' | 'groups';

export interface ApiError {
  detail: string;
}
