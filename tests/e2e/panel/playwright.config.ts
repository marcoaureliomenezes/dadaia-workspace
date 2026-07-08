import { defineConfig, devices } from '@playwright/test';
import * as os from 'os';
import * as path from 'path';

const REPO_ROOT = path.resolve(__dirname, '../../..');
// 4999 is the conventional operator-local live panel port — the e2e webServer
// must never collide with it (T-65-14 CI-fix amendment).
const PANEL_PORT = parseInt(process.env.PANEL_TEST_PORT || '5065', 10);
const BASE_URL = `http://127.0.0.1:${PANEL_PORT}`;
// Default command: the hermetic bootstrap script (T-65-14 amendment). It
// builds a disposable temp workspace — NEVER the repo checkout root, NEVER an
// enclosing real operator workspace — so `public install` re-renders (agent-
// policy Apply) never hit the `_is_source_repo_root` guard and never mutate
// a live operator workspace. See run-panel-e2e-server.sh for the full
// root-cause writeup. PANEL_WEB_SERVER_COMMAND still overrides wholesale for
// exceptional local debugging.
const RUN_SERVER_SCRIPT = path.join(__dirname, 'run-panel-e2e-server.sh');
const PANEL_WEB_SERVER_COMMAND =
  process.env.PANEL_WEB_SERVER_COMMAND || `bash "${RUN_SERVER_SCRIPT}"`;

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
    // PANEL_TEST_PORT is normalized here so the script and BASE_URL always
    // agree, even when the caller left it unset (PANEL_PORT's own '5065'
    // fallback applies). PANEL_E2E_PYTHON / PANEL_E2E_WS pass through only
    // when the caller set them.
    env: {
      PANEL_TEST_PORT: String(PANEL_PORT),
      ...(process.env.PANEL_E2E_PYTHON ? { PANEL_E2E_PYTHON: process.env.PANEL_E2E_PYTHON } : {}),
      ...(process.env.PANEL_E2E_WS ? { PANEL_E2E_WS: process.env.PANEL_E2E_WS } : {}),
    },
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
