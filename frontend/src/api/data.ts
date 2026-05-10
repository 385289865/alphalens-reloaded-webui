import client from './client';
import type { SessionSummary } from '@/types/session';

export async function listSessions(): Promise<SessionSummary[]> {
  const resp = await client.get('/data/sessions');
  return resp.data;
}

export async function getSession(sessionId: string) {
  const resp = await client.get(`/data/sessions/${sessionId}`);
  return resp.data;
}

export async function getFactorData(
  sessionId: string,
  params: { page?: number; page_size?: number; asset?: string; date_from?: string; date_to?: string } = {},
) {
  const resp = await client.get(`/data/sessions/${sessionId}/factor`, { params });
  return resp.data;
}

export async function getPriceData(
  sessionId: string,
  params: { page?: number; page_size?: number; asset?: string; date_from?: string; date_to?: string } = {},
) {
  const resp = await client.get(`/data/sessions/${sessionId}/prices`, { params });
  return resp.data;
}

export async function previewCsv(file: File, rows = 10) {
  const form = new FormData();
  form.append('file', file);
  const resp = await client.post('/data/preview', form, {
    params: { rows },
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return resp.data;
}
