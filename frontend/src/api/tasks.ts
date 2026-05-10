import client from './client';

export async function getTaskStatus(taskId: string) {
  const resp = await client.get(`/tasks/${taskId}`);
  return resp.data;
}

export async function revokeTask(taskId: string) {
  const resp = await client.post(`/tasks/${taskId}/revoke`);
  return resp.data;
}
