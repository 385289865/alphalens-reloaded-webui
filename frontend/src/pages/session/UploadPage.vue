<template>
  <div class="upload-page">
    <n-h2>Upload Data Files</n-h2>
    <n-p depth="3">Upload factor and pricing data CSV files to start an analysis.</n-p>

    <n-grid :cols="3" :x-gap="24" :y-gap="24">
      <n-gi>
        <n-card title="Factor Data" :segmented="true">
          <div
            class="upload-zone"
            :class="{ 'upload-zone-active': dragOverFactor }"
            @dragenter.prevent="dragOverFactor = true"
            @dragover.prevent="dragOverFactor = true"
            @dragleave.prevent="dragOverFactor = false"
            @drop.prevent="handleFactorDrop"
            data-testid="factor-upload-zone"
          >
            <template v-if="factorUploaded">
              <n-icon :component="CheckmarkCircleOutline" size="48" color="#22C55E" />
              <n-text style="margin-top: 8px;">{{ factorFileName }}</n-text>
              <n-button size="tiny" text type="error" @click="removeFactor">
                <template #icon><n-icon :component="CloseOutline" /></template>
                Remove
              </n-button>
            </template>
            <template v-else>
              <n-icon :component="CloudUploadOutline" size="48" depth="3" />
              <n-text depth="3" style="margin-top: 8px;">Drop factor CSV here or click to browse</n-text>
              <n-upload
                :show-file-list="false"
                accept=".csv"
                @before-upload="handleFactorUpload"
                style="margin-top: 8px;"
              >
                <n-button size="small">Select File</n-button>
              </n-upload>
            </template>
          </div>
          <div v-if="sessionStore.uploading && sessionStore.uploadProgress > 0" style="margin-top: 8px;">
            <n-progress type="line" :percentage="sessionStore.uploadProgress" />
          </div>
        </n-card>
      </n-gi>

      <n-gi>
        <n-card title="Price Data" :segmented="true">
          <div
            class="upload-zone"
            :class="{ 'upload-zone-active': dragOverPrices }"
            @dragenter.prevent="dragOverPrices = true"
            @dragover.prevent="dragOverPrices = true"
            @dragleave.prevent="dragOverPrices = false"
            @drop.prevent="handlePricesDrop"
            data-testid="prices-upload-zone"
          >
            <template v-if="pricesUploaded">
              <n-icon :component="CheckmarkCircleOutline" size="48" color="#22C55E" />
              <n-text style="margin-top: 8px;">{{ pricesFileName }}</n-text>
              <n-button size="tiny" text type="error" @click="removePrices">
                <template #icon><n-icon :component="CloseOutline" /></template>
                Remove
              </n-button>
            </template>
            <template v-else>
              <n-icon :component="CloudUploadOutline" size="48" depth="3" />
              <n-text depth="3" style="margin-top: 8px;">Drop prices CSV here or click to browse</n-text>
              <n-upload
                :show-file-list="false"
                accept=".csv"
                @before-upload="handlePricesUpload"
                style="margin-top: 8px;"
              >
                <n-button size="small">Select File</n-button>
              </n-upload>
            </template>
          </div>
          <div v-if="sessionStore.uploading" style="margin-top: 8px;">
            <n-progress type="line" :percentage="sessionStore.uploadProgress" />
          </div>
        </n-card>
      </n-gi>

      <n-gi>
        <n-card title="Group Data (Optional)" :segmented="true">
          <div
            class="upload-zone"
            :class="{ 'upload-zone-active': dragOverGroups }"
            @dragenter.prevent="dragOverGroups = true"
            @dragover.prevent="dragOverGroups = true"
            @dragleave.prevent="dragOverGroups = false"
            @drop.prevent="handleGroupsDrop"
          >
            <template v-if="groupsUploaded">
              <n-icon :component="CheckmarkCircleOutline" size="48" color="#22C55E" />
              <n-text style="margin-top: 8px;">{{ groupsFileName }}</n-text>
              <n-button size="tiny" text type="error" @click="removeGroups">
                <template #icon><n-icon :component="CloseOutline" /></template>
                Remove
              </n-button>
            </template>
            <template v-else>
              <n-icon :component="CloudUploadOutline" size="48" depth="3" />
              <n-text depth="3" style="margin-top: 8px;">Drop groups CSV here (optional)</n-text>
              <n-upload
                :show-file-list="false"
                accept=".csv"
                @before-upload="handleGroupsUpload"
                style="margin-top: 8px;"
              >
                <n-button size="small">Select File</n-button>
              </n-upload>
            </template>
          </div>
        </n-card>
      </n-gi>
    </n-grid>

    <div class="upload-actions" v-if="sessionStore.canConfigure">
      <n-alert type="success" :show-icon="false" data-testid="upload-complete">
        All required files uploaded. Proceed to configure your analysis.
      </n-alert>
      <n-button type="primary" size="large" @click="goToConfigure" data-testid="btn-configure-analysis">
        Configure Analysis
      </n-button>
    </div>

    <div v-if="sessionStore.error" class="error-message" data-testid="upload-error-message">
      <n-alert type="error" :title="sessionStore.error" closable @close="sessionStore.error = null" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { CloudUploadOutline, CheckmarkCircleOutline, CloseOutline } from '@vicons/ionicons5';
import { useSessionStore } from '@/stores/sessionStore';

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();

const sessionId = computed(() => route.params.sid as string);

const dragOverFactor = ref(false);
const dragOverPrices = ref(false);
const dragOverGroups = ref(false);

const factorUploaded = ref(false);
const pricesUploaded = ref(false);
const groupsUploaded = ref(false);
const factorFileName = ref('');
const pricesFileName = ref('');
const groupsFileName = ref('');

function getFileFromUpload(uploadData: any): File {
  return uploadData.file || uploadData;
}

async function handleFactorUpload(uploadData: any) {
  const file = getFileFromUpload(uploadData);
  factorUploaded.value = false;
  try {
    await sessionStore.uploadFile(file, 'factor', sessionId.value);
    factorUploaded.value = true;
    factorFileName.value = file.name;
  } catch {
    // store has error
  }
  return false;
}

async function handlePricesUpload(uploadData: any) {
  const file = getFileFromUpload(uploadData);
  pricesUploaded.value = false;
  try {
    await sessionStore.uploadFile(file, 'prices', sessionId.value);
    pricesUploaded.value = true;
    pricesFileName.value = file.name;
  } catch {
    // store has error
  }
  return false;
}

async function handleGroupsUpload(uploadData: any) {
  const file = getFileFromUpload(uploadData);
  groupsUploaded.value = false;
  try {
    await sessionStore.uploadFile(file, 'groups', sessionId.value);
    groupsUploaded.value = true;
    groupsFileName.value = file.name;
  } catch {
    // store has error
  }
  return false;
}

async function handleFactorDrop(e: DragEvent) {
  dragOverFactor.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (file) await sessionStore.uploadFile(file, 'factor', sessionId.value);
}

async function handlePricesDrop(e: DragEvent) {
  dragOverPrices.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (file) await sessionStore.uploadFile(file, 'prices', sessionId.value);
}

async function handleGroupsDrop(e: DragEvent) {
  dragOverGroups.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (file) await sessionStore.uploadFile(file, 'groups', sessionId.value);
}

function removeFactor() {
  factorUploaded.value = false;
  factorFileName.value = '';
}

function removePrices() {
  pricesUploaded.value = false;
  pricesFileName.value = '';
}

function removeGroups() {
  groupsUploaded.value = false;
  groupsFileName.value = '';
}

function goToConfigure() {
  router.push(`/sessions/${sessionId.value}/configure`);
}
</script>

<style scoped>
.upload-page {
  max-width: 1200px;
  margin: 0 auto;
}
.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 180px;
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 24px;
  transition: all 0.2s;
  cursor: pointer;
}
.upload-zone:hover,
.upload-zone-active {
  border-color: #22C55E;
  background: rgba(34, 197, 94, 0.05);
}
.upload-actions {
  margin-top: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.error-message {
  margin-top: 16px;
}
</style>
