import { test, expect } from '@playwright/test';

test.describe('Full Analysis Flow - UI to Backend Pipeline', () => {
  test('upload, configure, run, and view results', async ({ page }) => {
    // Step 1: Create session and upload factor + prices
    await page.goto('/sessions/new');

    await page.setInputFiles(
      '[data-testid="factor-upload-zone"] input[type="file"]',
      'e2e/fixtures/test_factor.csv'
    );
    await expect(page.locator('[data-testid="factor-upload-success"]'))
      .toBeVisible({ timeout: 10000 });

    await page.setInputFiles(
      '[data-testid="prices-upload-zone"] input[type="file"]',
      'e2e/fixtures/test_prices.csv'
    );
    await expect(page.locator('[data-testid="prices-upload-success"]'))
      .toBeVisible({ timeout: 10000 });

    await expect(page.locator('[data-testid="upload-complete"]'))
      .toBeVisible({ timeout: 5000 });

    // Step 2: Navigate to configure page
    await page.click('[data-testid="btn-configure-analysis"]');

    // Step 3: Verify default config values are loaded
    await expect(page.locator('[data-testid="periods-selector"]'))
      .toContainText('1, 5, 10');

    // Step 4: Modify config — add period 21, set long_short
    await page.click('[data-testid="period-btn-21"]');
    await page.click('[data-testid="toggle-long-short"]');

    // Step 5: Submit analysis
    await page.click('[data-testid="btn-run-analysis"]');

    // Step 6: Verify redirect to progress page and polling starts
    await expect(page).toHaveURL(/\/analysis\/.*\/progress/);
    await expect(page.locator('[data-testid="progress-tracker"]'))
      .toBeVisible();

    // Step 7: Wait for analysis to complete (polling auto-navigates)
    await expect(page).toHaveURL(/\/analysis\/.*\/results/, { timeout: 60000 });

    // Step 8: Verify results loaded
    await expect(page.locator('[data-testid="summary-metrics"]'))
      .toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="config-summary-bar"]'))
      .toBeVisible();

    // Step 9: Navigate to IC tab
    await page.click('[data-testid="tab-ic"]');
    await expect(page.locator('[data-testid="ic-detail-table"]'))
      .toBeVisible();

    // Step 10: Navigate to charts tab
    await page.click('[data-testid="tab-charts"]');
    await expect(page.locator('[data-testid="chart-card"]').first())
      .toBeVisible();

    // Step 11: Verify via API that results exist in DuckDB
    const analysisId = page.url().match(/analysis\/([^/]+)\/results/)?.[1];
    expect(analysisId).toBeTruthy();

    const statusResp = await page.request
      .get(`/api/v1/analysis/${analysisId}/status`);
    expect(statusResp.ok()).toBeTruthy();
    const status = await statusResp.json();
    expect(status.status).toBe('completed');

    // Verify chart can be fetched
    const chartResp = await page.request
      .get(`/api/v1/analysis/${analysisId}/results/charts/ic_time_series`);
    expect(chartResp.ok()).toBeTruthy();
    const chart = await chartResp.json();
    expect(chart.image).toContain('data:image/png;base64,');
  });

  test('re-run analysis with different config', async ({ page }) => {
    // Create session and upload data
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

    // Run first analysis
    await page.click('[data-testid="btn-configure-analysis"]');
    await page.click('[data-testid="btn-run-analysis"]');
    await expect(page).toHaveURL(/\/analysis\/.*\/results/, { timeout: 60000 });

    // Get first analysis ID
    const firstAnalysisId = page.url().match(/analysis\/([^/]+)\/results/)?.[1];

    // Click re-run
    await page.click('[data-testid="btn-rerun-analysis"]');
    await expect(page).toHaveURL(/\/analysis\/.*\/progress/);

    // Wait for second completion
    await expect(page).toHaveURL(/\/analysis\/.*\/results/, { timeout: 60000 });

    // Should be a different analysis ID
    const secondAnalysisId = page.url().match(/analysis\/([^/]+)\/results/)?.[1];
    expect(secondAnalysisId).not.toBe(firstAnalysisId);
  });
});
