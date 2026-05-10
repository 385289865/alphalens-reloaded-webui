<template>
  <n-layout position="absolute">
    <n-layout-header bordered>
      <div class="analysis-header-inner">
        <router-link :to="`/sessions/${sessionId}`" class="back-link">
          <n-button quaternary>
            <template #icon><n-icon :component="ArrowBackOutline" /></template>
            Back to Session
          </n-button>
        </router-link>
        <n-gradient-text type="success" :size="18">Analysis: {{ analysisId }}</n-gradient-text>
        <n-tag v-if="analysisStore.isRunning" type="warning">Running</n-tag>
        <n-tag v-else-if="analysisStore.isCompleted" type="success">Completed</n-tag>
        <n-tag v-else-if="analysisStore.isFailed" type="error">Failed</n-tag>
      </div>
    </n-layout-header>
    <n-layout-content content-style="padding: 24px;">
      <router-view />
    </n-layout-content>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { ArrowBackOutline } from '@vicons/ionicons5';
import { useAnalysisStore } from '@/stores/analysisStore';

const route = useRoute();
const analysisStore = useAnalysisStore();
const sessionId = computed(() => route.params.sid as string);
const analysisId = computed(() => route.params.aid as string);

onMounted(() => {
  if (analysisId.value) {
    analysisStore.fetchStatus(analysisId.value);
    if (analysisStore.isRunning) {
      analysisStore.startPolling(analysisId.value);
    }
  }
});
</script>

<style scoped>
.analysis-header-inner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 24px;
  max-width: 1400px;
  margin: 0 auto;
}
.back-link {
  text-decoration: none;
}
</style>
