import client from './client';
import type { AnalysisConfig } from '@/types/analysis';

export async function runAnalysis(sessionId: string, config: AnalysisConfig) {
  const resp = await client.post('/analysis/run', { session_id: sessionId, config });
  return resp.data;
}

export async function getAnalysisStatus(analysisId: string) {
  const resp = await client.get(`/analysis/${analysisId}/status`);
  return resp.data;
}

export async function getAllResults(analysisId: string) {
  const resp = await client.get(`/analysis/${analysisId}/results`);
  return resp.data;
}

export async function getIcResults(analysisId: string) {
  const resp = await client.get(`/analysis/${analysisId}/results/ic`);
  return resp.data;
}

export async function getReturnsResults(analysisId: string) {
  const resp = await client.get(`/analysis/${analysisId}/results/returns`);
  return resp.data;
}

export async function getAlphaBeta(analysisId: string) {
  const resp = await client.get(`/analysis/${analysisId}/results/alpha-beta`);
  return resp.data;
}

export async function getTurnoverResults(analysisId: string) {
  const resp = await client.get(`/analysis/${analysisId}/results/turnover`);
  return resp.data;
}

export async function getSummaryTables(analysisId: string) {
  const resp = await client.get(`/analysis/${analysisId}/results/summary-tables`);
  return resp.data;
}

export async function getChart(analysisId: string, chartType: string) {
  const resp = await client.get(`/analysis/${analysisId}/results/charts/${chartType}`);
  return resp.data;
}
