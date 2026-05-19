/**
 * Temporary Playwright config for PR3-22 evidence capture.
 * This file is NOT part of the test spec set — it is a run artifact for QA.
 * Delete after PR3-22 evidence commit.
 */
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e/pr3-22-evidence',
  testMatch: 'pr3-22-capture.spec.ts',
  timeout: 45_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4999',
    headless: true,
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
