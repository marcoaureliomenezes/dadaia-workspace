import { defineConfig, devices } from '@playwright/test';
import * as path from 'path';

const REPO_ROOT = path.resolve(__dirname, '../../..');
const PANEL_PORT = parseInt(process.env.PANEL_TEST_PORT || '4999', 10);
const BASE_URL = `http://127.0.0.1:${PANEL_PORT}`;
const PANEL_WEB_SERVER_COMMAND =
  process.env.PANEL_WEB_SERVER_COMMAND ||
  `python -m dadaia_workspace.cli.main panel --port ${PANEL_PORT} --no-open`;

export default defineConfig({
  testDir: '.',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
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
