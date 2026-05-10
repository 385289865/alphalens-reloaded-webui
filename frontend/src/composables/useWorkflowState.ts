import { watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAnalysisStore } from '@/stores/analysisStore';

export function useWorkflowState(sessionId: string) {
  const router = useRouter();
  const analysisStore = useAnalysisStore();

  watch(
    () => analysisStore.status,
    (status) => {
      if (status === 'completed' && analysisStore.currentAnalysisId) {
        router.push(
          `/sessions/${sessionId}/analysis/${analysisStore.currentAnalysisId}/results`,
        );
      }
    },
  );
}
