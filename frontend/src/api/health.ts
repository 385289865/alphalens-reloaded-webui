import client from './client';

export async function healthCheck() {
  const resp = await client.get('/health');
  return resp.data;
}
