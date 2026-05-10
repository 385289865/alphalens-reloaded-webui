import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './specs',
  timeout: 120000,
  retries: 1,
  use: {
    baseURL: 'http://localhost:5173',
    extraHTTPHeaders: { 'Content-Type': 'application/json' },
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: 'python manage.py start --test',
      port: 8000,
      timeout: 30000,
      reuseExistingServer: true,
    },
  ],
});
