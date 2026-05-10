import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { AnalysisConfig, AnalysisStatus } from '@/types/analysis';
import * as analysisApi from '@/api/analysis';

const DEFAULT_CONFIG: AnalysisConfig = {
  periods: [1, 5, 10],
  quantiles: 5,
  bins: null,
  filter_zscore: 20,
  max_loss: 0.35,
  zero_aware: false,
  cumulative_returns: true,
  long_short: true,
  group_neutral: false,
  by_group: false,
  groupby_column: null,
};

export const useAnalysisStore = defineStore('analysis', () => {
  // State
  const currentAnalysisId = ref<string | null>(null);
  const currentTaskId = ref<string | null>(null);
  const config = ref<AnalysisConfig>({ ...DEFAULT_CONFIG });
  const status = ref<AnalysisStatus>('idle');
  const stage = ref<string | null>(null);
  const progressPct = ref(0);
  const message = ref<string | null>(null);
  const errorMessage = ref<string | null>(null);
  const startedAt = ref<string | null>(null);
  const completedAt = ref<string | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  let pollingTimer: ReturnType<typeof setInterval> | null = null;

  // Getters
  const isRunning = computed(() => status.value === 'running' || status.value === 'pending');
  const isCompleted = computed(() => status.value === 'completed');
  const isFailed = computed(() => status.value === 'failed');

  // Actions
  function setConfig(partial: Partial<AnalysisConfig>) {
    config.value = { ...config.value, ...partial };
  }

  function resetConfig() {
    config.value = { ...DEFAULT_CONFIG };
  }

  async function runAnalysis(sessionId: string) {
    loading.value = true;
    error.value = null;
    status.value = 'pending';
    try {
      const resp = await analysisApi.runAnalysis(sessionId, config.value);
      currentAnalysisId.value = resp.analysis_id;
      currentTaskId.value = resp.task_id;
      status.value = 'running';
      return resp;
    } catch (e: any) {
      error.value = e.message;
      status.value = 'failed';
      errorMessage.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchStatus(aid: string) {
    try {
      const resp = await analysisApi.getAnalysisStatus(aid);
      currentAnalysisId.value = resp.analysis_id;
      currentTaskId.value = resp.task_id;
      status.value = resp.status;
      stage.value = resp.current_stage;
      progressPct.value = resp.progress_pct;
      message.value = resp.message;
      startedAt.value = resp.started_at;
      completedAt.value = resp.completed_at;
      errorMessage.value = resp.error_message;
      return resp;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    }
  }

  function startPolling(aid: string, onUpdate?: (status: any) => void) {
    stopPolling();
    pollingTimer = setInterval(async () => {
      try {
        const resp = await analysisApi.getAnalysisStatus(aid);
        currentAnalysisId.value = resp.analysis_id;
        status.value = resp.status;
        stage.value = resp.current_stage;
        progressPct.value = resp.progress_pct;
        message.value = resp.message;
        startedAt.value = resp.started_at;
        completedAt.value = resp.completed_at;
        errorMessage.value = resp.error_message;
        onUpdate?.(resp);
        if (resp.status === 'completed' || resp.status === 'failed') {
          stopPolling();
        }
      } catch {
        stopPolling();
      }
    }, 2000);
  }

  function stopPolling() {
    if (pollingTimer) {
      clearInterval(pollingTimer);
      pollingTimer = null;
    }
  }

  function reset() {
    stopPolling();
    currentAnalysisId.value = null;
    currentTaskId.value = null;
    status.value = 'idle';
    stage.value = null;
    progressPct.value = 0;
    message.value = null;
    errorMessage.value = null;
    startedAt.value = null;
    completedAt.value = null;
    loading.value = false;
    error.value = null;
  }

  return {
    currentAnalysisId, currentTaskId, config, status, stage, progressPct,
    message, errorMessage, startedAt, completedAt, loading, error,
    isRunning, isCompleted, isFailed,
    setConfig, resetConfig, runAnalysis, fetchStatus,
    startPolling, stopPolling, reset,
  };
});
