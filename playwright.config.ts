import { defineConfig, devices } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// Read the panel Bearer token from the canonical token path.
// The panel server must already be running before the test suite is invoked.
function readPanelToken(): string {
  const tokenPath = path.join(process.env.HOME || '~', '.dadaia', 'state', 'panel.token');
  try {
    return fs.readFileSync(tokenPath, 'utf-8').trim();
  } catch {
    // Return an empty string; tests that require auth will receive 401.
    return '';
  }
}

const PANEL_PORT = parseInt(process.env.PANEL_TEST_PORT || '4999', 10);
const BASE_URL = `http://127.0.0.1:${PANEL_PORT}`;
const PANEL_TOKEN = readPanelToken();

export default defineConfig({
  testDir: './tests/e2e/panel',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],

  use: {
    baseURL: BASE_URL,
    headless: true,
    screenshot: 'only-on-failure',
    video: 'off',
    // Extra HTTP headers so the panel receives the Bearer token
    // for browser-initiated API requests from within the page.
    // Tests that do direct API calls will add the header via request().
    extraHTTPHeaders: {},
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Expose the token and base URL as globals accessible in test files.
  globalSetup: undefined,
});

// Re-export for use in test helpers.
export { BASE_URL, PANEL_TOKEN };
