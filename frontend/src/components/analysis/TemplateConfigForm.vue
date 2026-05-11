<template>
  <n-form
    v-if="template"
    ref="formRef"
    :model="formValues"
    label-placement="left"
    label-width="180"
    @submit.prevent="handleSubmit"
  >
    <n-grid :cols="2" :x-gap="24">
      <n-gi>
        <n-card title="Template">
          <n-space vertical>
            <n-tag size="small">{{ template.template_id }}</n-tag>
            <n-p depth="3">{{ template.description }}</n-p>
          </n-space>
        </n-card>
      </n-gi>

      <n-gi>
        <n-card title="Steps Preview">
          <n-list>
            <n-list-item v-for="(step, idx) in template.steps" :key="idx">
              <n-thing :title="step.step_type">
                <template #description>
                  <n-tag size="tiny" v-for="dep in step.depends_on" :key="dep">
                    {{ dep }}
                  </n-tag>
                </template>
              </n-thing>
            </n-list-item>
          </n-list>
        </n-card>
      </n-gi>
    </n-grid>

    <n-card title="Parameters" style="margin-top: 16px">
      <n-grid :cols="2" :x-gap="24" :y-gap="16">
        <n-gi v-for="param in template.configurable_params" :key="param.name">
          <!-- list[int] type: tag buttons for periods -->
          <n-form-item v-if="param.type === 'list[int]'" :label="param.name">
            <n-space>
              <n-button
                v-for="opt in [1, 5, 10, 21]"
                :key="opt"
                size="tiny"
                :type="(formValues[param.name] || []).includes(opt) ? 'primary' : 'default'"
                @click="toggleListParam(param.name, opt)"
              >
                {{ opt }}
              </n-button>
            </n-space>
          </n-form-item>

          <!-- int type -->
          <n-form-item v-else-if="param.type === 'int'" :label="param.name">
            <n-input-number
              v-model:value="formValues[param.name]"
              :min="2"
              :max="100"
              style="width: 100%"
            />
          </n-form-item>

          <!-- float type -->
          <n-form-item v-else-if="param.type === 'float'" :label="param.name">
            <n-input-number
              v-model:value="formValues[param.name]"
              :min="param.name === 'max_loss' ? 0 : 0"
              :max="param.name === 'max_loss' ? 1 : 100"
              :step="0.1"
              style="width: 100%"
            />
          </n-form-item>

          <!-- bool type -->
          <n-form-item v-else-if="param.type === 'bool'" :label="param.name">
            <n-switch v-model:value="formValues[param.name]" />
          </n-form-item>

          <!-- fallback -->
          <n-form-item v-else :label="param.name">
            <n-input v-model:value="formValues[param.name]" />
          </n-form-item>
        </n-gi>
      </n-grid>
    </n-card>

    <n-space justify="end" style="margin-top: 20px">
      <n-button @click="$emit('cancel')">Cancel</n-button>
      <n-button type="primary" attr-type="submit" :loading="submitting">
        Run Analysis
      </n-button>
    </n-space>
  </n-form>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue';
import type { TemplateDetail } from '@/api/flowBuilder';

const props = defineProps<{
  template: TemplateDetail | null;
}>();

const emit = defineEmits<{
  submit: [params: Record<string, any>];
  cancel: [];
}>();

const formRef = ref<any>(null);
const submitting = ref(false);

const formValues = reactive<Record<string, any>>({});

onMounted(() => {
  initFormValues();
});

watch(() => props.template, () => {
  initFormValues();
});

function initFormValues() {
  if (!props.template) return;
  for (const param of props.template.configurable_params) {
    if (formValues[param.name] === undefined) {
      formValues[param.name] = param.default;
    }
  }
}

function toggleListParam(name: string, value: number) {
  if (!formValues[name]) {
    formValues[name] = [];
  }
  const idx = formValues[name].indexOf(value);
  if (idx >= 0) {
    formValues[name].splice(idx, 1);
  } else {
    formValues[name].push(value);
  }
}

async function handleSubmit() {
  submitting.value = true;
  try {
    const params: Record<string, any> = {};
    for (const key of Object.keys(formValues)) {
      params[key] = formValues[key];
    }
    emit('submit', params);
  } finally {
    submitting.value = false;
  }
}
</script>
