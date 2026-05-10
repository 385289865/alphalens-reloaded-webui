import { onUnmounted, ref } from 'vue';
import { getAnalysisStatus } from '@/api/analysis';
import type { AnalysisStatusResponse } from '@/types/analysis';

export function useAnalysisPolling(intervalMs = 2000) {
  const status = ref<AnalysisStatusResponse | null>(null);
  const error = ref<string | null>(null);
  let timer: ReturnType<typeof setInterval> | null = null;

  function start(analysisId: string, onUpdate?: (s: AnalysisStatusResponse) => void) {
    stop();
    timer = setInterval(async () => {
      try {
        const resp = await getAnalysisStatus(analysisId);
        status.value = resp;
        onUpdate?.(resp);
        if (resp.status === 'completed' || resp.status === 'failed') {
          stop();
        }
      } catch (e: any) {
        error.value = e.message;
        stop();
      }
    }, intervalMs);
  }

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  onUnmounted(stop);

  return { status, error, start, stop };
}
