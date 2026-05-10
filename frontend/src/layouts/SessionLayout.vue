<template>
  <n-layout has-sidebar position="absolute">
    <n-layout-sider
      bordered
      :width="260"
      :native-scrollbar="false"
      content-style="padding: 16px;"
    >
      <div v-if="sessionStore.loading" class="sider-loading">
        <n-skeleton text :repeat="4" />
      </div>
      <template v-else-if="sessionStore.currentSession">
        <div class="session-meta">
          <n-text strong>{{ sessionStore.currentSession.name || 'Untitled Session' }}</n-text>
          <n-text depth="3" style="font-size: 12px; display: block; margin-top: 4px;">
            {{ sessionId }}
          </n-text>
        </div>

        <n-divider />

        <div class="nav-steps">
          <n-step
            v-for="step in steps"
            :key="step.path"
            :title="step.label"
            :status="stepStatus(step)"
            style="cursor: pointer;"
            @click="navigateTo(step.path)"
          />
        </div>

        <n-divider />

        <div class="file-list">
          <n-text depth="3" style="font-size: 12px;">Uploaded Files</n-text>
          <n-thing
            v-for="f in sessionStore.currentSession.files"
            :key="f.file_id"
            :title="f.original_filename"
            :description="`${f.file_type} | ${f.row_count} rows`"
            style="margin-top: 8px;"
          />
          <n-empty v-if="!sessionStore.currentSession.files.length" description="No files" size="small" />
        </div>
      </template>
    </n-layout-sider>
    <n-layout-content content-style="padding: 24px;">
      <router-view />
    </n-layout-content>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useSessionStore } from '@/stores/sessionStore';

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();
const sessionId = computed(() => route.params.sid as string);

const steps = [
  { label: 'Upload Data', path: 'upload', key: 'upload' },
  { label: 'Browse Data', path: 'data', key: 'data' },
  { label: 'Configure Analysis', path: 'configure', key: 'configure' },
  { label: 'Results', path: 'results', key: 'results' },
];

function stepStatus(step: { key: string }) {
  const current = route.name as string;
  if (step.key === 'upload') return 'process';
  if (step.key === 'data' && (current === 'BrowseData' || current === 'Configure' || current === 'AnalysisProgress' || current === 'AnalysisResults')) return 'finish';
  if (step.key === 'configure' && (current === 'Configure' || current === 'AnalysisProgress' || current === 'AnalysisResults')) return 'finish';
  if (step.key === 'results' && (current === 'AnalysisResults')) return 'finish';
  if (route.path.includes(step.key)) return 'process';
  return 'wait';
}

function navigateTo(path: string) {
  router.push(`/sessions/${sessionId.value}/${path}`);
}

onMounted(() => {
  if (sessionId.value) {
    sessionStore.fetchSession(sessionId.value);
  }
});

watch(() => sessionId.value, (newId) => {
  if (newId) sessionStore.fetchSession(newId);
});
</script>

<style scoped>
.session-meta {
  padding: 8px 0;
}
.nav-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sider-loading {
  padding: 16px;
}
</style>
