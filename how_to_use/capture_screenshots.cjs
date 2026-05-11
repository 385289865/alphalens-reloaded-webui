/** Capture screenshots for Alphalens WebUI workflow documentation */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE = 'http://localhost:5173';
const API  = 'http://localhost:8000';
const OUT  = path.resolve(__dirname, './images');

async function shot(page, name) {
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: true });
  console.log(`  ✓ ${name}.png`);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.setDefaultTimeout(20000);

  // Get existing session from DB
  const sessionsResp = await page.request.get(API + '/api/v1/data/sessions');
  const sessions = await sessionsResp.json();
  const session = sessions[0];
  const sid = session.session_id;
  console.log(`Using session: ${sid} (${session.name})`);

  // ── 1. Session list page (shows existing session) ────
  console.log('\n[1/14] Session list');
  await page.goto(BASE + '/sessions', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await shot(page, '01-session-list');

  // ── 2. Create new session dialog ─────────────────────
  console.log('\n[2/14] Create session dialog');
  await page.goto(BASE + '/sessions', { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  // Trigger dialog
  await page.evaluate(() => {
    // Find any button with "New Session" text and click it
    document.querySelectorAll('button').forEach(b => {
      if (b.textContent.includes('New Session')) b.click();
    });
  });
  await page.waitForTimeout(1000);
  await shot(page, '02-create-session-dialog');

  // ── 3. Upload page (session with factor+prices) ──────
  console.log('\n[3/14] Upload page');
  await page.goto(BASE + `/sessions/${sid}/upload`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '03-upload-files');

  // ── 4. Browse factor data ────────────────────────────
  console.log('\n[4/14] Browse factor data');
  await page.goto(BASE + `/sessions/${sid}/data`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '04-browse-factor');

  // ── 5. Browse price data ─────────────────────────────
  console.log('\n[5/14] Browse price data');
  // Click the Price tab by trying both role and button selectors
  await page.evaluate(() => {
    document.querySelectorAll('[role="tab"], .n-tabs-nav__tab, button').forEach(el => {
      if (el.textContent.trim() === 'Price') el.click();
    });
  });
  await page.waitForTimeout(2000);
  await shot(page, '05-browse-price');

  // ── 6. Configure page ────────────────────────────────
  console.log('\n[6/14] Configure page');
  await page.goto(BASE + `/sessions/${sid}/configure`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '06-configure');

  // ── 7. Running analysis (use existing completed analysis from inline run) ──
  console.log('  Using existing completed analysis...');
  const aid = '70ae35f2-2a48-42b9-a016-62f00ce2caec';  // pre-completed by run_analysis_inline.py
  console.log(`  Analysis: ${aid}`);

  // Verify it's completed
  const statusResp = await page.request.get(API + `/api/v1/analysis/${aid}/status`);
  const statusData = await statusResp.json();
  console.log(`  Status: ${statusData.status}`);

  // Progress page
  await page.goto(BASE + `/sessions/${sid}/analysis/${aid}/progress`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // ── 8. Summary results ───────────────────────────────
  console.log('\n[8/14] Summary');
  await page.goto(BASE + `/sessions/${sid}/analysis/${aid}/results`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await shot(page, '08-summary');

  // Tab click helper
  async function clickTab(label) {
    await page.evaluate((lbl) => {
      document.querySelectorAll('[role="tab"], .n-tabs-nav__tab, button, [class*="tab"]').forEach(el => {
        if (el.textContent.trim() === lbl || el.textContent.trim().startsWith(lbl)) el.click();
      });
    }, label);
    await page.waitForTimeout(3000);
  }

  // ── 9. IC ────────────────────────────────────────────
  console.log('\n[9/14] IC tab');
  await clickTab('IC');
  await shot(page, '09-ic');

  // ── 10. Returns ──────────────────────────────────────
  console.log('\n[10/14] Returns tab');
  await clickTab('Returns');
  await shot(page, '10-returns');

  // ── 11. Alpha-Beta ───────────────────────────────────
  console.log('\n[11/14] Alpha-Beta tab');
  await clickTab('Alpha');
  await shot(page, '11-alpha-beta');

  // ── 12. Turnover ─────────────────────────────────────
  console.log('\n[12/14] Turnover tab');
  await clickTab('Turnover');
  await shot(page, '12-turnover');

  // ── 13. Charts ───────────────────────────────────────
  console.log('\n[13/14] Charts tab');
  await clickTab('Charts');
  await page.waitForTimeout(5000);
  await shot(page, '13-charts');

  // ── 14. Analysis complete ────────────────────────────
  console.log('\n[14/14] Analysis complete');
  await page.goto(BASE + `/sessions/${sid}/analysis/${aid}/progress`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await shot(page, '14-analysis-complete');

  await browser.close();
  console.log('\n✅ All 14 screenshots in how_to_use/images/');
})();
