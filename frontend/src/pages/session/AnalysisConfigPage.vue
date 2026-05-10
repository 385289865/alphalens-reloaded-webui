<template>
  <div class="config-page">
    <n-h2>Configure Analysis</n-h2>
    <n-p depth="3">Set parameters for the factor analysis pipeline.</n-p>

    <n-alert v-if="!sessionStore.canConfigure" type="warning" data-testid="error-missing-data" style="margin-bottom: 16px;">
      Both factor and price data must be uploaded before configuring an analysis.
      <template #footer>
        <n-button size="small" @click="$router.push(`/sessions/${sessionId}/upload`)">Go to Upload</n-button>
      </template>
    </n-alert>

    <n-form v-else :model="analysisStore.config" label-placement="left" label-width="180">
      <n-grid :cols="2" :x-gap="24">
        <n-gi>
          <n-card title="Forward Returns">
            <n-form-item label="Periods (days)" data-testid="periods-selector">
              <n-space>
                <n-button
                  v-for="p in [1, 5, 10, 21]"
                  :key="p"
                  :type="isPeriodSelected(p) ? 'primary' : 'default'"
                  size="small"
                  @click="togglePeriod(p)"
                >{{ p }}</n-button>
              </n-space>
            </n-form-item>

            <n-form-item label="Quantiles">
              <n-slider
                v-model:value="analysisStore.config.quantiles"
                :min="2"
                :max="100"
                :step="1"
                style="width: 200px;"
              />
              <n-text style="margin-left: 12px;">{{ analysisStore.config.quantiles }}</n-text>
            </n-form-item>
          </n-card>
        </n-gi>

        <n-gi>
          <n-card title="Filters">
            <n-form-item label="Z-Score Filter">
              <n-input-number v-model:value="analysisStore.config.filter_zscore" :min="0" :step="0.5" style="width: 120px;" />
            </n-form-item>

            <n-form-item label="Max Loss">
              <n-input-number v-model:value="analysisStore.config.max_loss" :min="0" :max="1" :step="0.05" style="width: 120px;" />
            </n-form-item>
          </n-card>
        </n-gi>

        <n-gi>
          <n-card title="Options">
            <n-form-item label="Long/Short">
              <n-switch v-model:value="analysisStore.config.long_short" data-testid="toggle-long-short" />
            </n-form-item>

            <n-form-item label="Group Neutral">
              <n-switch v-model:value="analysisStore.config.group_neutral" />
            </n-form-item>

            <n-form-item label="Zero Aware">
              <n-switch v-model:value="analysisStore.config.zero_aware" />
            </n-form-item>
          </n-card>
        </n-gi>

        <n-gi>
          <n-card title="Display">
            <n-form-item label="Cumulative Returns">
              <n-switch v-model:value="analysisStore.config.cumulative_returns" />
            </n-form-item>

            <n-form-item label="By Group">
              <n-switch v-model:value="analysisStore.config.by_group" />
            </n-form-item>
          </n-card>
        </n-gi>
      </n-grid>

      <div class="config-actions">
        <n-button @click="resetConfig">Reset to Defaults</n-button>
        <n-button
          type="primary"
          size="large"
          :loading="analysisStore.loading"
          @click="runAnalysis"
          data-testid="btn-run-analysis"
        >
          Run Analysis
        </n-button>
      </div>
    </n-form>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useSessionStore } from '@/stores/sessionStore';
import { useAnalysisStore } from '@/stores/analysisStore';

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();
const analysisStore = useAnalysisStore();

const sessionId = computed(() => route.params.sid as string);

function isPeriodSelected(p: number) {
  return analysisStore.config.periods.includes(p);
}

function togglePeriod(p: number) {
  const periods = [...analysisStore.config.periods];
  const idx = periods.indexOf(p);
  if (idx >= 0) {
    periods.splice(idx, 1);
  } else {
    periods.push(p);
    periods.sort((a, b) => a - b);
  }
  analysisStore.setConfig({ periods });
}

async function runAnalysis() {
  try {
    const resp = await analysisStore.runAnalysis(sessionId.value);
    router.push(`/sessions/${sessionId.value}/analysis/${resp.analysis_id}/progress`);
  } catch {
    // store has error
  }
}

function resetConfig() {
  analysisStore.resetConfig();
}
</script>

<style scoped>
.config-page {
  max-width: 1200px;
  margin: 0 auto;
}
.config-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}
</style>
