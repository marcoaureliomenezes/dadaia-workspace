import { defineConfig, devices } from '@playwright/test';
import * as os from 'os';
import * as path from 'path';

const REPO_ROOT = path.resolve(__dirname, '../../..');
const PANEL_PORT = parseInt(process.env.PANEL_TEST_PORT || '4999', 10);
const BASE_URL = `http://127.0.0.1:${PANEL_PORT}`;
const PANEL_WEB_SERVER_COMMAND =
  process.env.PANEL_WEB_SERVER_COMMAND ||
  `python -m dadaia_workspace.cli.main panel --port ${PANEL_PORT} --no-open`;

// Keep test-results and playwright-report OUTSIDE the repo to avoid polluting
// the working tree.  Use env override (PLAYWRIGHT_OUTPUT_DIR /
// PLAYWRIGHT_REPORT_DIR) so CI can redirect to a known artifacts path; fall
// back to the OS temp directory for local runs.
const OUTPUT_DIR = process.env.PLAYWRIGHT_OUTPUT_DIR || path.join(os.tmpdir(), 'dadaia-pw-test-results');
const REPORT_DIR = process.env.PLAYWRIGHT_REPORT_DIR || path.join(os.tmpdir(), 'dadaia-pw-report');

export default defineConfig({
  testDir: '.',
  outputDir: OUTPUT_DIR,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: REPORT_DIR }]],
  webServer: {
    command: PANEL_WEB_SERVER_COMMAND,
    cwd: REPO_ROOT,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },

  use: {
    baseURL: BASE_URL,
    headless: true,
    screenshot: 'only-on-failure',
    video: 'off',
    extraHTTPHeaders: {},
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
