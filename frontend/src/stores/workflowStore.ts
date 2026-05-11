import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import * as flowBuilderApi from '@/api/flowBuilder';
import type { Template, WorkflowCreateResponse } from '@/api/flowBuilder';

export const useWorkflowStore = defineStore('workflow', () => {
  const templates = ref<Template[]>([]);
  const selectedTemplate = ref<string | null>(null);
  const currentJobId = ref<string | null>(null);
  const currentWorkflowId = ref<string | null>(null);
  const job = ref<any>(null);
  const tasks = ref<any[]>([]);
  const loading = ref(false);

  const isRunning = computed(() =>
    ['pending', 'running'].includes(job.value?.job?.status ?? ''),
  );
  const isCompleted = computed(() => job.value?.job?.status === 'completed');
  const isFailed = computed(() => job.value?.job?.status === 'failed');
  const progressPct = computed(() => {
    if (!job.value?.job) return 0;
    const j = job.value.job;
    if (j.total_steps === 0) return 0;
    return Math.round((j.completed_steps / j.total_steps) * 100);
  });

  async function fetchTemplates() {
    loading.value = true;
    try {
      templates.value = await flowBuilderApi.listTemplates();
    } finally {
      loading.value = false;
    }
  }

  async function createAndRunWorkflow(
    templateId: string,
    sessionId: string,
    parameters: Record<string, any>,
  ): Promise<WorkflowCreateResponse> {
    loading.value = true;
    try {
      const result = await flowBuilderApi.createWorkflow(
        templateId, sessionId, parameters,
      );
      currentWorkflowId.value = result.workflow_id;
      currentJobId.value = result.job_id;
      return result;
    } finally {
      loading.value = false;
    }
  }

  async function pollJob() {
    if (!currentJobId.value) return;
    try {
      const resp = await flowBuilderApi.getJob(currentJobId.value);
      job.value = resp;
      tasks.value = resp.tasks || [];
    } catch {
      // Silently handle polling errors
    }
  }

  function reset() {
    selectedTemplate.value = null;
    currentJobId.value = null;
    currentWorkflowId.value = null;
    job.value = null;
    tasks.value = [];
    loading.value = false;
  }

  return {
    templates, selectedTemplate, currentJobId, currentWorkflowId,
    job, tasks, loading,
    isRunning, isCompleted, isFailed, progressPct,
    fetchTemplates, createAndRunWorkflow, pollJob, reset,
  };
});
