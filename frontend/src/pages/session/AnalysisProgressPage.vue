<template>
  <div class="progress-page">
    <n-h2>Analysis Progress</n-h2>

    <n-card>
      <div class="progress-main">
        <n-progress
          type="circle"
          :percentage="analysisStore.progressPct"
          :stroke-width="8"
          :rail-color="progressRailColor"
          :fill-color="progressFillColor"
          :size="120"
        >
          <div class="progress-pct">{{ analysisStore.progressPct }}%</div>
        </n-progress>

        <div class="progress-info">
          <n-thing>
            <template #description>
              <n-space vertical>
                <n-text v-if="analysisStore.stage">Stage: {{ analysisStore.stage }}</n-text>
                <n-text v-if="analysisStore.message">{{ analysisStore.message }}</n-text>
                <n-text v-if="elapsed" depth="3">Elapsed: {{ elapsed }}</n-text>
              </n-space>
            </template>
          </n-thing>
        </div>
      </div>

      <n-divider />

      <div class="pipeline-steps" data-testid="progress-tracker">
        <n-steps :current="currentStep" status="process">
          <n-step
            v-for="step in pipelineSteps"
            :key="step.key"
            :title="step.label"
            :description="step.desc"
          />
        </n-steps>
      </div>

      <div v-if="analysisStore.isFailed" class="error-card" data-testid="analysis-error">
        <n-alert type="error" title="Analysis Failed" :description="analysisStore.errorMessage || 'Unknown error'">
          <template #footer>
            <n-button @click="retry" data-testid="btn-retry-analysis">Retry</n-button>
          </template>
        </n-alert>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAnalysisStore } from '@/stores/analysisStore';
import { useThemeStore } from '@/stores/themeStore';

const route = useRoute();
const router = useRouter();
const analysisStore = useAnalysisStore();
const themeStore = useThemeStore();

const sessionId = computed(() => route.params.sid as string);
const analysisId = computed(() => route.params.aid as string);
const startTime = ref(Date.now());
const elapsed = ref('');

const progressRailColor = computed(() => themeStore.darkMode ? '#1E293B' : '#E2E8F0');
const progressFillColor = computed(() => {
  if (analysisStore.isFailed) return '#EF4444';
  if (analysisStore.isCompleted) return '#22C55E';
  return '#22C55E';
});

const pipelineSteps = [
  { key: 'validate', label: 'Validate', desc: 'Checking input data' },
  { key: 'load', label: 'Load Data', desc: 'Loading factor & prices' },
  { key: 'forward_returns', label: 'Forward Returns', desc: 'Computing forward returns' },
  { key: 'quantile', label: 'Quantile', desc: 'Binning into quantiles' },
  { key: 'ic', label: 'IC Analysis', desc: 'Information Coefficient' },
  { key: 'returns', label: 'Returns', desc: 'Factor returns' },
  { key: 'alpha_beta', label: 'Alpha/Beta', desc: 'Risk metrics' },
  { key: 'charts', label: 'Charts', desc: 'Generating charts' },
];

const stageToStep: Record<string, number> = {
  validate: 0, load: 1, forward_returns: 2, quantile: 3,
  ic: 4, returns: 5, alpha_beta: 6, charts: 7,
};

const currentStep = computed(() => {
  if (analysisStore.isCompleted) return pipelineSteps.length;
  if (analysisStore.stage && stageToStep[analysisStore.stage] !== undefined) {
    return stageToStep[analysisStore.stage];
  }
  if (analysisStore.isRunning) return 1;
  return 0;
});

function retry() {
  analysisStore.reset();
  router.push(`/sessions/${sessionId.value}/configure`);
}

let timer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  startTime.value = Date.now();
  timer = setInterval(() => {
    const secs = Math.floor((Date.now() - startTime.value) / 1000);
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    elapsed.value = `${m}m ${s}s`;
  }, 1000);

  analysisStore.startPolling(analysisId.value, (status: any) => {
    if (status.status === 'completed') {
      router.push(`/sessions/${sessionId.value}/analysis/${analysisId.value}/results`);
    }
  });
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped>
.progress-page {
  max-width: 800px;
  margin: 0 auto;
}
.progress-main {
  display: flex;
  align-items: center;
  gap: 32px;
}
.progress-pct {
  font-size: 24px;
  font-weight: 700;
  font-family: 'Fira Code', monospace;
}
.progress-info {
  flex: 1;
}
.pipeline-steps {
  margin-top: 16px;
}
.error-card {
  margin-top: 16px;
}
</style>
