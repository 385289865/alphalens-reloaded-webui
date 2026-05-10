import client from './client';
import type { UploadResponse } from '@/types/api';

export async function uploadCsv(
  file: File,
  fileType: string,
  sessionId?: string,
  onProgress?: (pct: number) => void,
): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('file_type', fileType);
  if (sessionId) form.append('session_id', sessionId);

  const resp = await client.post('/upload/csv', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return resp.data;
}

export async function listSessionFiles(sessionId: string) {
  const resp = await client.get(`/upload/${sessionId}/files`);
  return resp.data;
}

export async function deleteSession(sessionId: string) {
  await client.delete(`/upload/${sessionId}`);
}
