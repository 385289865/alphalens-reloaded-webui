import { ref } from 'vue';
import { uploadCsv } from '@/api/upload';
import { previewCsv } from '@/api/data';

export function useFileUpload() {
  const uploading = ref(false);
  const progress = ref(0);
  const error = ref<string | null>(null);

  async function upload(
    file: File,
    fileType: string,
    sessionId?: string,
  ) {
    uploading.value = true;
    progress.value = 0;
    error.value = null;
    try {
      const resp = await uploadCsv(file, fileType, sessionId, (pct) => {
        progress.value = pct;
      });
      progress.value = 100;
      return resp;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      uploading.value = false;
    }
  }

  async function preview(file: File, rows = 10) {
    return previewCsv(file, rows);
  }

  return { uploading, progress, error, upload, preview };
}
