import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { SessionSummary, SessionDetail, UploadFileInfo } from '@/types/session';
import * as uploadApi from '@/api/upload';
import * as dataApi from '@/api/data';

export const useSessionStore = defineStore('session', () => {
  // State
  const sessions = ref<SessionSummary[]>([]);
  const currentSession = ref<SessionDetail | null>(null);
  const loading = ref(false);
  const uploading = ref(false);
  const uploadProgress = ref(0);
  const error = ref<string | null>(null);

  // Getters
  const hasFactorData = computed(() =>
    currentSession.value?.files?.some((f) => f.file_type === 'factor') ?? false,
  );
  const hasPriceData = computed(() =>
    currentSession.value?.files?.some((f) => f.file_type === 'prices') ?? false,
  );
  const canConfigure = computed(() => hasFactorData.value && hasPriceData.value);

  // Actions
  async function fetchSessions() {
    loading.value = true;
    error.value = null;
    try {
      sessions.value = await dataApi.listSessions();
    } catch (e: any) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  }

  async function fetchSession(sid: string) {
    loading.value = true;
    error.value = null;
    try {
      currentSession.value = await dataApi.getSession(sid);
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createSession(name?: string) {
    loading.value = true;
    error.value = null;
    try {
      const resp = await uploadApi.uploadCsv(new File([], ''), 'factor');
      return resp.session_id;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function uploadFile(
    file: File,
    fileType: string,
    sessionId?: string,
  ): Promise<{ sessionId: string }> {
    uploading.value = true;
    uploadProgress.value = 0;
    error.value = null;
    try {
      const resp = await uploadApi.uploadCsv(file, fileType, sessionId, (pct) => {
        uploadProgress.value = pct;
      });
      uploadProgress.value = 100;
      if (currentSession.value && resp.session_id === currentSession.value.session_id) {
        await fetchSession(resp.session_id);
      }
      return { sessionId: resp.session_id };
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      uploading.value = false;
    }
  }

  async function deleteSessionAction(sid: string) {
    error.value = null;
    try {
      await uploadApi.deleteSession(sid);
      sessions.value = sessions.value.filter((s) => s.session_id !== sid);
      if (currentSession.value?.session_id === sid) {
        currentSession.value = null;
      }
    } catch (e: any) {
      error.value = e.message;
      throw e;
    }
  }

  return {
    sessions, currentSession, loading, uploading, uploadProgress, error,
    hasFactorData, hasPriceData, canConfigure,
    fetchSessions, fetchSession, createSession, uploadFile, deleteSession: deleteSessionAction,
  };
});
