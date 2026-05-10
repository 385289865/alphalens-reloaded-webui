import { test, expect } from '@playwright/test';

test.describe('Upload Flow - UI to Backend Communication', () => {
  test('upload factor CSV and verify data reaches backend', async ({ page }) => {
    // 1. Navigate to session upload page
    await page.goto('/sessions/new');

    // 2. Upload factor file via the upload zone
    await page.setInputFiles(
      '[data-testid="factor-upload-zone"] input[type="file"]',
      'e2e/fixtures/test_factor.csv'
    );

    // 3. Wait for upload to complete and verify success indicator
    await expect(page.locator('[data-testid="factor-upload-success"]'))
      .toBeVisible({ timeout: 10000 });

    // 4. Verify session_id is persisted in the page
    const sessionId = await page.getAttribute('body', 'data-session-id');
    expect(sessionId).toBeTruthy();

    // 5. Verify via API that the file was ingested
    const apiResp = await page.request.get(`/api/v1/upload/${sessionId}/files`);
    expect(apiResp.ok()).toBeTruthy();
    const files = await apiResp.json();
    expect(files.files.some((f: any) => f.file_type === 'factor')).toBeTruthy();
    expect(files.files.some((f: any) => f.file_type === 'factor' && f.row_count > 0)).toBeTruthy();
  });

  test('upload both factor and prices, then browse data', async ({ page }) => {
    // 1. Navigate to new session
    await page.goto('/sessions/new');

    // 2. Upload factor
    await page.setInputFiles(
      '[data-testid="factor-upload-zone"] input[type="file"]',
      'e2e/fixtures/test_factor.csv'
    );
    await expect(page.locator('[data-testid="factor-upload-success"]'))
      .toBeVisible({ timeout: 10000 });

    // 3. Upload prices
    await page.setInputFiles(
      '[data-testid="prices-upload-zone"] input[type="file"]',
      'e2e/fixtures/test_prices.csv'
    );
    await expect(page.locator('[data-testid="prices-upload-success"]'))
      .toBeVisible({ timeout: 10000 });

    // 4. Navigate to browse data page
    await page.click('[data-testid="btn-browse-data"]');

    // 5. Verify factor data table loads
    await expect(page.locator('[data-testid="factor-data-table"]'))
      .toBeVisible({ timeout: 10000 });

    // 6. Switch to prices tab and verify
    await page.click('[data-testid="tab-prices"]');
    await expect(page.locator('[data-testid="price-data-table"]'))
      .toBeVisible({ timeout: 5000 });

    // 7. Verify data rows are present via API
    const sessionId = await page.getAttribute('body', 'data-session-id');
    const factorResp = await page.request.get(
      `/api/v1/data/sessions/${sessionId}/factor?page=1&page_size=10`
    );
    expect(factorResp.ok()).toBeTruthy();
    const factorData = await factorResp.json();
    expect(factorData.total_rows).toBeGreaterThan(0);
  });

  test('preview CSV before uploading', async ({ page }) => {
    await page.goto('/sessions/new');

    // Trigger file selection on the preview input
    await page.setInputFiles(
      '[data-testid="factor-upload-zone"] input[type="file"]',
      'e2e/fixtures/test_factor.csv'
    );

    // Preview modal should show first 10 rows
    await expect(page.locator('[data-testid="preview-modal"]'))
      .toBeVisible({ timeout: 5000 });

    // Verify preview API call was made
    const previewResp = await page.request.post('/api/v1/data/preview', {
      multipart: {
        file: ['e2e/fixtures/test_factor.csv'],
      },
    });
    expect(previewResp.ok()).toBeTruthy();
    const preview = await previewResp.json();
    expect(preview.columns).toContain('date');
    expect(preview.columns).toContain('asset');
    expect(preview.columns).toContain('factor_value');
  });
});
