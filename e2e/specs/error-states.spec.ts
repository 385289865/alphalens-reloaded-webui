import { test, expect } from '@playwright/test';

test.describe('Error States - UI Resilience', () => {
  test('show error when uploading empty file', async ({ page }) => {
    await page.goto('/sessions/new');

    await page.setInputFiles(
      '[data-testid="factor-upload-zone"] input[type="file"]',
      'e2e/fixtures/empty.csv'
    );

    await expect(page.locator('[data-testid="upload-error-message"]'))
      .toBeVisible({ timeout: 10000 });
  });

  test('show error when triggering analysis without data', async ({ page }) => {
    // Create a session without uploading data
    const resp = await page.request.post('/api/v1/upload/csv', {
      multipart: {
        file: ['e2e/fixtures/test_factor.csv'],
        file_type: 'factor',
      },
    });
    const { session_id: sessionId } = await resp.json();

    // Navigate to configure page (no prices uploaded)
    await page.goto(`/sessions/${sessionId}/configure`);

    await expect(page.locator('[data-testid="error-missing-prices"]'))
      .toBeVisible();
  });

  test('show error when backend is unreachable', async ({ page }) => {
    // Mock network failure for API routes
    await page.route('/api/v1/**', (route) => route.abort('connectionrefused'));

    await page.goto('/sessions');

    await expect(page.locator('[data-testid="network-error-banner"]'))
      .toBeVisible({ timeout: 5000 });
  });

  test('show error when uploading non-CSV file', async ({ page }) => {
    await page.goto('/sessions/new');

    // Create a simple text file to simulate wrong format
    const fileContent = 'not a csv file';
    await page.setInputFiles(
      '[data-testid="factor-upload-zone"] input[type="file"]',
      {
        name: 'data.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from(fileContent),
      }
    );

    await expect(page.locator('[data-testid="upload-error-message"]'))
      .toBeVisible({ timeout: 10000 });
  });

  test('show 404 for nonexistent analysis', async ({ page }) => {
    await page.goto('/sessions/nonexistent-id/analysis/nonexistent/results');

    await expect(page.locator('[data-testid="error-404"]'))
      .toBeVisible({ timeout: 5000 });
  });

  test('handle analysis failure gracefully', async ({ page }) => {
    // Create session with minimal data that will fail analysis
    await page.goto('/sessions/new');
    await page.setInputFiles(
      '[data-testid="factor-upload-zone"] input[type="file"]',
      'e2e/fixtures/test_factor.csv'
    );
    await page.setInputFiles(
      '[data-testid="prices-upload-zone"] input[type="file"]',
      'e2e/fixtures/test_prices.csv'
    );
    await expect(page.locator('[data-testid="upload-complete"]'))
      .toBeVisible({ timeout: 10000 });

    // Configure and run
    await page.click('[data-testid="btn-configure-analysis"]');
    await page.click('[data-testid="btn-run-analysis"]');

    // Wait for either results or failure
    await page.waitForURL(/\/(results|error)/, { timeout: 60000 });

    // If on error page, verify retry button exists
    const errorVisible = await page.locator('[data-testid="analysis-error"]')
      .isVisible().catch(() => false);
    if (errorVisible) {
      await expect(page.locator('[data-testid="btn-retry-analysis"]'))
        .toBeVisible();
    }
  });
});
