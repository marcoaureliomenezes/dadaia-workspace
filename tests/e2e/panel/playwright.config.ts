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
  // Bug test-suite-real-venv-and-ci-longpole: workers was 1, serialising 11 spec
  // files that mostly only READ the shared panel. Files parallelise across workers
  // (fullyParallel stays false, so tests within a file keep their order); the two
  // specs that MUTATE shared panel state run in their own dependent projects below,
  // one at a time, after the read-only pass.
  workers: process.env.CI ? 2 : 4,
  // Bug panel-e2e-artifacts-no-consumer: in CI the HTML report was written to the
  // runner tmpdir and discarded every run, even on failure. CI now runs list-only
  // (failure evidence = only-on-failure screenshots + first-retry traces in
  // outputDir, uploaded by the workflow on failure); the HTML report stays a
  // local-only convenience, overwritten in place each run.
  // PLAYWRIGHT_JSON_REPORT (v0.7.0 FR5, loud flake): when set, a JSON report is
  // written OUTSIDE the repo so CI can fail on an unregistered pass-on-retry —
  // retries stay at 1; what changes is that the retry stops being invisible.
  reporter: process.env.CI
    ? process.env.PLAYWRIGHT_JSON_REPORT
      ? [['list'], ['json', { outputFile: process.env.PLAYWRIGHT_JSON_REPORT }]]
      : [['list']]
    : [['list'], ['html', { open: 'never', outputFolder: REPORT_DIR }]],
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
    // 60 s validity fix (bug test-suite-real-venv-and-ci-longpole): the hermetic
    // bootstrap (init + stage + install + panel start) measured ~24 s unloaded with
    // the venv stub; 30 s made the whole suite fail ERR_CONNECTION_REFUSED on any
    // loaded host — the server was still bootstrapping when playwright gave up.
    timeout: 60_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },

  use: {
    baseURL: BASE_URL,
    headless: true,
    screenshot: 'only-on-failure',
    // Free on green runs (CI retries=1, local retries=0 → never recorded); a CI
    // failure's retry captures a full trace into outputDir for the evidence upload.
    trace: 'on-first-retry',
    video: 'off',
    extraHTTPHeaders: {},
  },

  // Shared-state isolation: agent-policy.spec.ts (Apply PUT re-renders the temp
  // workspace's projections) and spec-context-operation-journey.spec.ts (drives real
  // context alive/dead transitions through the registry) mutate state every other
  // spec reads. They run AFTER the read-only pass, serially — each in its own
  // single-file project, chained via `dependencies`.
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: ['**/agent-policy.spec.ts', '**/spec-context-operation-journey.spec.ts'],
    },
    {
      name: 'chromium-agent-policy',
      use: { ...devices['Desktop Chrome'] },
      testMatch: '**/agent-policy.spec.ts',
      dependencies: ['chromium'],
    },
    {
      name: 'chromium-context-journey',
      use: { ...devices['Desktop Chrome'] },
      testMatch: '**/spec-context-operation-journey.spec.ts',
      dependencies: ['chromium-agent-policy'],
    },
  ],
});
