<template>
  <div class="session-list-page">
    <div class="page-header">
      <n-h2>Analysis Sessions</n-h2>
      <n-button type="primary" @click="showCreateDialog = true">
        <template #icon><n-icon :component="AddOutline" /></template>
        New Session
      </n-button>
    </div>

    <n-spin :show="sessionStore.loading">
      <div v-if="sessionStore.sessions.length === 0 && !sessionStore.loading" class="empty-state">
        <n-empty description="No sessions yet. Create your first analysis session." size="large">
          <template #extra>
            <n-button type="primary" @click="showCreateDialog = true">Upload Data</n-button>
          </template>
        </n-empty>
      </div>

      <n-grid v-else :cols="3" :x-gap="16" :y-gap="16">
        <n-gi v-for="s in sessionStore.sessions" :key="s.session_id">
          <n-card
            :title="s.name || 'Untitled'"
            hoverable
            @click="$router.push(`/sessions/${s.session_id}/upload`)"
            class="session-card"
          >
            <n-thing>
              <template #description>
                <n-space vertical size="small">
                  <n-text depth="3">{{ s.asset_count }} assets</n-text>
                  <n-text depth="3">Analyses: {{ s.analysis_count }}</n-text>
                  <n-text v-if="s.date_range_start" depth="3" style="font-size: 12px;">
                    {{ s.date_range_start }} ~ {{ s.date_range_end }}
                  </n-text>
                </n-space>
              </template>
            </n-thing>
            <template #action>
              <n-button text type="error" size="small" @click.stop="confirmDelete(s)">
                <template #icon><n-icon :component="TrashOutline" /></template>
                Delete
              </n-button>
            </template>
          </n-card>
        </n-gi>
      </n-grid>
    </n-spin>

    <n-modal v-model:show="showCreateDialog" title="New Session" preset="card" style="width: 400px;">
      <n-form>
        <n-form-item label="Session Name">
          <n-input v-model:value="newSessionName" placeholder="Optional session name" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="showCreateDialog = false">Cancel</n-button>
        <n-button type="primary" @click="createSession">Create</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { AddOutline, TrashOutline } from '@vicons/ionicons5';
import { useSessionStore } from '@/stores/sessionStore';
import { useDialog } from 'naive-ui';

const router = useRouter();
const sessionStore = useSessionStore();
const dialog = useDialog();

const showCreateDialog = ref(false);
const newSessionName = ref('');

async function createSession() {
  try {
    const sid = await sessionStore.createSession(newSessionName.value || undefined);
    showCreateDialog.value = false;
    newSessionName.value = '';
    router.push(`/sessions/${sid}/upload`);
  } catch {
    // error handled by store
  }
}

function confirmDelete(s: any) {
  dialog.warning({
    title: 'Delete Session',
    content: `Delete session "${s.name || 'Untitled'}"? This cannot be undone.`,
    positiveText: 'Delete',
    negativeText: 'Cancel',
    onPositiveClick: () => sessionStore.deleteSession(s.session_id),
  });
}

onMounted(() => {
  sessionStore.fetchSessions();
});
</script>

<style scoped>
.session-list-page {
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.empty-state {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}
.session-card {
  cursor: pointer;
}
</style>
