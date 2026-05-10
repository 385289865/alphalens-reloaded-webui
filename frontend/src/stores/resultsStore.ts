import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { AnalysisResults } from '@/types/results';
import * as analysisApi from '@/api/analysis';

export const useResultsStore = defineStore('results', () => {
  // State
  const analysisId = ref<string | null>(null);
  const results = ref<AnalysisResults | null>(null);
  const config = ref<Record<string, any> | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Per-tab loading state
  const icLoading = ref(false);
  const returnsLoading = ref(false);
  const alphaBetaLoading = ref(false);
  const turnoverLoading = ref(false);
  const summaryLoading = ref(false);
  const chartLoading = ref(false);

  // Actions
  async function fetchAllResults(aid: string) {
    loading.value = true;
    error.value = null;
    analysisId.value = aid;
    try {
      const data = await analysisApi.getAllResults(aid);
      results.value = data;
      config.value = data.config;
      return results.value;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchIc(aid: string) {
    icLoading.value = true;
    try {
      return await analysisApi.getIcResults(aid);
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      icLoading.value = false;
    }
  }

  async function fetchReturns(aid: string) {
    returnsLoading.value = true;
    try {
      return await analysisApi.getReturnsResults(aid);
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      returnsLoading.value = false;
    }
  }

  async function fetchAlphaBeta(aid: string) {
    alphaBetaLoading.value = true;
    try {
      return await analysisApi.getAlphaBeta(aid);
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      alphaBetaLoading.value = false;
    }
  }

  async function fetchTurnover(aid: string) {
    turnoverLoading.value = true;
    try {
      return await analysisApi.getTurnoverResults(aid);
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      turnoverLoading.value = false;
    }
  }

  async function fetchSummaryTables(aid: string) {
    summaryLoading.value = true;
    try {
      return await analysisApi.getSummaryTables(aid);
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      summaryLoading.value = false;
    }
  }

  async function fetchChart(aid: string, chartType: string) {
    chartLoading.value = true;
    try {
      return await analysisApi.getChart(aid, chartType);
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      chartLoading.value = false;
    }
  }

  async function fetchAllCharts(aid: string): Promise<Record<string, string>> {
    const chartTypes = [
      'ic_time_series', 'ic_histogram', 'ic_qq_plot',
      'quantile_returns_bar', 'cumulative_returns',
      'mean_quantile_spread', 'quantile_turnover', 'rank_autocorrelation',
    ];
    const chartMap: Record<string, string> = {};
    for (const ct of chartTypes) {
      try {
        const resp = await analysisApi.getChart(aid, ct);
        chartMap[ct] = resp.image;
      } catch {
        // chart may not be available
      }
    }
    return chartMap;
  }

  function clearResults() {
    analysisId.value = null;
    results.value = null;
    config.value = null;
    loading.value = false;
    error.value = null;
  }

  return {
    analysisId, results, config, loading, error,
    icLoading, returnsLoading, alphaBetaLoading, turnoverLoading, summaryLoading, chartLoading,
    fetchAllResults, fetchIc, fetchReturns, fetchAlphaBeta, fetchTurnover,
    fetchSummaryTables, fetchChart, fetchAllCharts, clearResults,
  };
});
