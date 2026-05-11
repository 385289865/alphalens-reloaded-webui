<template>
  <div class="workflow-progress-page">
    <n-h2>Analysis Progress</n-h2>

    <!-- Overall progress bar -->
    <n-card style="margin-bottom: 16px">
      <n-space align="center" style="margin-bottom: 12px">
        <n-progress
          type="circle"
          :percentage="workflowStore.progressPct"
          :status="workflowStore.isFailed ? 'error' : workflowStore.isCompleted ? 'success' : undefined"
          :stroke-width="10"
          :size="80"
        />
        <n-space vertical style="margin-left: 16px">
          <n-text strong>Status: {{ jobStatus }}</n-text>
          <n-text depth="3" v-if="workflowStore.job?.job?.completed_steps !== undefined">
            {{ workflowStore.job.job.completed_steps }} / {{ workflowStore.job.job.total_steps }} steps completed
          </n-text>
        </n-space>
      </n-space>
    </n-card>

    <!-- Error display -->
    <n-alert
      v-if="workflowStore.job?.job?.error_message"
      type="error"
      closable
      style="margin-bottom: 16px"
    >
      <template #header>Error</template>
      {{ workflowStore.job.job.error_message }}
    </n-alert>

    <!-- Step timeline -->
    <n-card title="Steps">
      <n-timeline>
        <n-timeline-item
          v-for="task in workflowStore.tasks"
          :key="task.task_id"
          :type="getTimelineType(task)"
          :title="task.step_type"
          :time="getTimeLabel(task)"
          :content="task.error_message || ''"
        />
      </n-timeline>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useWorkflowStore } from '@/stores/workflowStore';

const workflowStore = useWorkflowStore();
const route = useRoute();
const router = useRouter();

const jobId = computed(() => route.params.aid as string);
const sessionId = computed(() => route.params.sid as string);

const jobStatus = computed(() => {
  if (workflowStore.isCompleted) return 'Completed';
  if (workflowStore.isFailed) return 'Failed';
  if (workflowStore.job?.job?.status === 'running') return 'Running';
  return 'Pending';
});

let pollTimer: ReturnType<typeof setInterval> | null = null;

onMounted(async () => {
  // Set the job ID from URL params
  workflowStore.currentJobId = jobId.value;
  // Start polling
  await fetchJob();
  pollTimer = setInterval(fetchJob, 2000);
});

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  workflowStore.reset();
});

// Auto-navigate to results when completed
watch(
  () => workflowStore.isCompleted,
  (completed) => {
    if (completed) {
      setTimeout(() => {
        router.replace(
          `/sessions/${sessionId.value}/analysis/${jobId.value}/results`,
        );
      }, 1000);
    }
  },
);

async function fetchJob() {
  await workflowStore.pollJob();
}

function getTimelineType(task: any): 'success' | 'error' | 'warning' | 'info' | 'default' {
  if (task.status === 'completed') return 'success';
  if (task.status === 'failed') return 'error';
  if (task.status === 'running') return 'info';
  if (task.status === 'skipped') return 'warning';
  return 'default';
}

function getTimeLabel(task: any): string | undefined {
  if (task.started_at && task.completed_at) {
    const start = new Date(task.started_at);
    const end = new Date(task.completed_at);
    const elapsed = Math.round((end.getTime() - start.getTime()) / 1000);
    return `${elapsed}s`;
  }
  if (task.started_at) {
    return 'Running...';
  }
  return undefined;
}
</script>
