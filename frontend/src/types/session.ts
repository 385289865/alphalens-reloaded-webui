export interface SessionSummary {
  session_id: string;
  name: string | null;
  created_at: string;
  status: string;
  asset_count: number;
  date_range_start: string | null;
  date_range_end: string | null;
  analysis_count: number;
}

export interface SessionDetail {
  session_id: string;
  name: string | null;
  description: string | null;
  created_at: string;
  status: string;
  files: UploadFileInfo[];
  analysis_runs: string[];
  date_range_start: string | null;
  date_range_end: string | null;
  asset_count: number;
}

export interface UploadFileInfo {
  file_id: string;
  file_type: string;
  original_filename: string;
  file_size_bytes: number;
  row_count: number;
  uploaded_at: string;
}

export interface SessionFilesResponse {
  session_id: string;
  files: UploadFileInfo[];
}
