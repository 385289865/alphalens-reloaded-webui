<template>
  <div class="template-select-page">
    <n-h2>Select Analysis Template</n-h2>
    <n-p depth="3">
      Choose an analysis template to run against your uploaded data.
      Each template runs a specific subset of the alphalens pipeline.
    </n-p>

    <div v-if="loading" style="text-align: center; padding: 40px">
      <n-spin size="large" />
    </div>

    <template v-else>
      <!-- Template selection cards -->
      <n-space vertical size="large">
        <n-card
          v-for="tpl in workflowStore.templates"
          :key="tpl.template_id"
          :title="tpl.name"
          hoverable
          :class="{ selected: selectedTemplate === tpl.template_id }"
          style="cursor: pointer; transition: all 0.2s"
          :style="selectedTemplate === tpl.template_id ? { borderColor: '#18a058' } : {}"
          @click="selectedTemplate = tpl.template_id"
        >
          <template #header-extra>
            <n-tag>{{ tpl.template_id }}</n-tag>
          </template>

          <p>{{ tpl.description }}</p>

          <n-space style="margin-top: 12px">
            <n-tag v-for="p in tpl.configurable_params" :key="p.name" size="small" type="info">
              {{ p.name }}: {{ p.type }}
            </n-tag>
          </n-space>

          <template #footer>
            <n-button
              type="primary"
              @click.stop="selectAndConfigure(tpl.template_id)"
            >
              Use This Template
            </n-button>
          </template>
        </n-card>
      </n-space>

      <!-- Config form for selected template -->
      <n-card v-if="selectedTemplateDetail" title="Configure Parameters" style="margin-top: 24px">
        <TemplateConfigForm
          :template="selectedTemplateDetail"
          @submit="handleSubmit"
          @cancel="selectedTemplateDetail = null"
        />
      </n-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useWorkflowStore } from '@/stores/workflowStore';
import { getTemplate } from '@/api/flowBuilder';
import type { TemplateDetail } from '@/api/flowBuilder';
import TemplateConfigForm from '@/components/analysis/TemplateConfigForm.vue';

const workflowStore = useWorkflowStore();
const router = useRouter();
const route = useRoute();

const sessionId = computed(() => route.params.sid as string);
const selectedTemplate = ref<string | null>(null);
const selectedTemplateDetail = ref<TemplateDetail | null>(null);
const loading = ref(false);

onMounted(async () => {
  loading.value = true;
  try {
    await workflowStore.fetchTemplates();
  } finally {
    loading.value = false;
  }
});

async function selectAndConfigure(templateId: string) {
  selectedTemplate.value = templateId;
  try {
    selectedTemplateDetail.value = await getTemplate(templateId);
  } catch (err) {
    console.error('Failed to load template detail:', err);
  }
}

async function handleSubmit(params: Record<string, any>) {
  if (!selectedTemplate.value) return;

  try {
    const result = await workflowStore.createAndRunWorkflow(
      selectedTemplate.value,
      sessionId.value,
      params,
    );
    // Navigate to progress page
    router.push(
      `/sessions/${sessionId.value}/analysis/${result.workflow_id}/workflow-progress`,
    );
  } catch (err) {
    console.error('Failed to create workflow:', err);
  }
}
</script>

<style scoped>
.selected {
  border: 2px solid #18a058;
}
</style>
