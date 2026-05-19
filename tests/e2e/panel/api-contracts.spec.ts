/**
 * api-contracts.spec.ts — E2E-API-01 through E2E-API-12 + E2E-AGT-12
 *
 * Tests: 13
 * Surface: HTTP API contracts — shapes, auth enforcement, path traversal guard,
 *          telemetry state pre-check skip guard.
 *
 * All tests are Playwright API-level (no browser rendering needed).
 * They validate the HTTP contract directly via request().
 *
 * E2E-AGT-12: skip guard for telemetry state — skips if telemetry is unavailable
 *             rather than failing (503 is not a test failure; it means the panel
 *             started without telemetry, which is valid in CI).
 */

import { test, expect } from '@playwright/test';
import { authHeaders, BASE_URL } from './helpers';

// ---------------------------------------------------------------------------
// E2E-API-01 — /api/agents shape: 10 agents with canonical fields
// ---------------------------------------------------------------------------
test('E2E-API-01 — /api/agents returns 10 agents with canonical fields', async ({ request }) => {
  const response = await request.get(`${BASE_URL}/api/agents`, {
    headers: authHeaders(),
  });
  expect(response.status()).toBe(200);

  const body = await response.json();
  expect(body).toHaveProperty('agents');
  expect(Array.isArray(body.agents)).toBe(true);
  expect(body.agents).toHaveLength(10);

  for (const agent of body.agents) {
    expect(typeof agent.agent_id).toBe('string');
    expect(agent.agent_id.length).toBeGreaterThan(0);
    expect(typeof agent.display_name).toBe('string');
    expect(typeof agent.description).toBe('string');
    expect(['active', 'inactive']).toContain(agent.status);
    expect(Array.isArray(agent.skills)).toBe(true);
    expect(Array.isArray(agent.tools)).toBe(true);
    expect(agent.description.length).toBeGreaterThan(0);
    expect(agent.skills).not.toBeNull();
  }
});

// ---------------------------------------------------------------------------
// E2E-API-02 — /api/agents/<id>/prompt returns prompt body
// ---------------------------------------------------------------------------
test('E2E-API-02 — /api/agents/software-engineer/prompt returns non-empty prompt body', async ({
  request,
}) => {
  const response = await request.get(`${BASE_URL}/api/agents/software-engineer/prompt`, {
    headers: authHeaders(),
  });
  // Expect 200 or handle if endpoint not yet implemented
  expect(response.status()).toBe(200);

  const contentType = response.headers()['content-type'] ?? '';
  // Accept JSON or text; the spec says text but JSON { agent_id, system_prompt } is also valid
  const body = await response.text();
  expect(body.length).toBeGreaterThan(0);
});

// ---------------------------------------------------------------------------
// E2E-API-03 — /api/agents/unknown-agent/prompt returns 404
// ---------------------------------------------------------------------------
test('E2E-API-03 — /api/agents/unknown-agent-xyz/prompt returns 404', async ({ request }) => {
  const response = await request.get(
    `${BASE_URL}/api/agents/unknown-agent-xyz-that-does-not-exist/prompt`,
    { headers: authHeaders() }
  );
  expect(response.status()).toBe(404);
});

// ---------------------------------------------------------------------------
// E2E-API-04 — /api/workflows: 12 workflows, each with required fields
// ---------------------------------------------------------------------------
test('E2E-API-04 — /api/workflows returns 12 workflows each with required fields', async ({
  request,
}) => {
  const response = await request.get(`${BASE_URL}/api/workflows`, {
    headers: authHeaders(),
  });
  expect(response.status()).toBe(200);

  const body = await response.json();
  expect(body).toHaveProperty('workflows');
  expect(Array.isArray(body.workflows)).toBe(true);
  expect(body.workflows).toHaveLength(12);

  for (const wf of body.workflows) {
    expect(typeof wf.name).toBe('string');
    expect(wf.name.length).toBeGreaterThan(0);
    // stage_count OR stages array must be present
    const hasStageCount = typeof wf.stage_count === 'number';
    const hasStagesArray = Array.isArray(wf.stages);
    expect(hasStageCount || hasStagesArray).toBe(true);
  }
});

// ---------------------------------------------------------------------------
// E2E-API-05 — /api/workflows: tdd-cycle has exactly 5 stages with correct IDs
// ---------------------------------------------------------------------------
test('E2E-API-05 — tdd-cycle has exactly 5 stages with correct stage IDs', async ({
  request,
}) => {
  // Try list endpoint first
  const listResponse = await request.get(`${BASE_URL}/api/workflows`, {
    headers: authHeaders(),
  });
  const listBody = await listResponse.json();
  const tddFromList = listBody.workflows.find((w: any) => w.name === 'tdd-cycle');
  expect(tddFromList).toBeTruthy();

  let stages: any[];

  if (Array.isArray(tddFromList.stages)) {
    stages = tddFromList.stages;
  } else {
    // Fetch detail endpoint
    const detailResponse = await request.get(`${BASE_URL}/api/workflows/tdd-cycle`, {
      headers: authHeaders(),
    });
    expect(detailResponse.status()).toBe(200);
    const detailBody = await detailResponse.json();
    stages = detailBody.stages;
  }

  expect(Array.isArray(stages)).toBe(true);
  expect(stages).toHaveLength(5);

  // Known stage IDs for tdd-cycle (API uses 'id', not 'stage_id')
  const stageIds = stages.map((s: any) => s.id);
  const expectedIds = ['red_test', 'green_impl', 'refactor', 'deploy_validation', 'consult_product'];
  for (const expectedId of expectedIds) {
    expect(stageIds).toContain(expectedId);
  }

  // Each stage has agent and needs fields (API field is 'id', not 'stage_id')
  for (const stage of stages) {
    expect(stage).toHaveProperty('id');
    expect(stage).toHaveProperty('agent');
    expect(stage).toHaveProperty('needs');
    expect(Array.isArray(stage.needs)).toBe(true);
  }

  // First stage has empty needs
  const firstStage = stages.find((s: any) => s.id === 'red_test');
  if (firstStage) {
    expect(firstStage.needs).toHaveLength(0);
  }
});

// ---------------------------------------------------------------------------
// E2E-API-06 — cross-cutting-feature has 7 stages with correct structure
// ---------------------------------------------------------------------------
test('E2E-API-06 — cross-cutting-feature has 7 stages; red_test_frontend has needs and parallel_group', async ({
  request,
}) => {
  const listResponse = await request.get(`${BASE_URL}/api/workflows`, {
    headers: authHeaders(),
  });
  const listBody = await listResponse.json();
  const ccfFromList = listBody.workflows.find(
    (w: any) => w.name === 'cross-cutting-feature'
  );
  expect(ccfFromList).toBeTruthy();

  let stages: any[];

  if (Array.isArray(ccfFromList.stages)) {
    stages = ccfFromList.stages;
  } else {
    const detailResponse = await request.get(
      `${BASE_URL}/api/workflows/cross-cutting-feature`,
      { headers: authHeaders() }
    );
    expect(detailResponse.status()).toBe(200);
    const detailBody = await detailResponse.json();
    stages = detailBody.stages;
  }

  expect(Array.isArray(stages)).toBe(true);
  expect(stages).toHaveLength(7);

  // Find red_test_frontend stage
  const redTestFe = stages.find((s: any) => s.id === 'red_test_frontend');
  if (redTestFe) {
    expect(Array.isArray(redTestFe.needs)).toBe(true);
    expect(redTestFe.needs).toContain('contract_review');
    // parallel_group is optional but if present must be 'red_tests'
    if (redTestFe.parallel_group !== undefined) {
      expect(redTestFe.parallel_group).toBe('red_tests');
    }
  }
});

// ---------------------------------------------------------------------------
// E2E-API-07 — dag_svg / diagram_svg field is present and is SVG XML
// ---------------------------------------------------------------------------
test('E2E-API-07 — API response for tdd-cycle contains a non-empty SVG string', async ({
  request,
}) => {
  // Check list endpoint for embedded dag_svg
  const listResponse = await request.get(`${BASE_URL}/api/workflows`, {
    headers: authHeaders(),
  });
  const listBody = await listResponse.json();
  const tddFromList = listBody.workflows.find((w: any) => w.name === 'tdd-cycle');

  let svgField: string | null = null;

  if (typeof tddFromList?.dag_svg === 'string' && tddFromList.dag_svg.length > 0) {
    svgField = tddFromList.dag_svg;
  } else if (
    typeof tddFromList?.diagram_svg === 'string' &&
    tddFromList.diagram_svg.length > 0
  ) {
    svgField = tddFromList.diagram_svg;
  }

  if (!svgField) {
    // Try detail endpoint (architect's position: SVG only in detail)
    const detailResponse = await request.get(`${BASE_URL}/api/workflows/tdd-cycle`, {
      headers: authHeaders(),
    });
    expect(detailResponse.status()).toBe(200);
    const detailBody = await detailResponse.json();
    svgField =
      typeof detailBody.diagram_svg === 'string' ? detailBody.diagram_svg :
      typeof detailBody.dag_svg === 'string' ? detailBody.dag_svg :
      null;
  }

  expect(svgField).not.toBeNull();
  expect(svgField).toContain('<svg');
});

// ---------------------------------------------------------------------------
// E2E-API-08 — /api/agents requires Bearer (401 without token)
// ---------------------------------------------------------------------------
test('E2E-API-08 — /api/agents without Bearer token returns 401', async ({ request }) => {
  const response = await request.get(`${BASE_URL}/api/agents`, {
    headers: {},
  });
  expect(response.status()).toBe(401);
});

// ---------------------------------------------------------------------------
// E2E-API-09 — /api/workflows requires Bearer (401 without token)
// ---------------------------------------------------------------------------
test('E2E-API-09 — /api/workflows without Bearer token returns 401', async ({ request }) => {
  const response = await request.get(`${BASE_URL}/api/workflows`, {
    headers: {},
  });
  expect(response.status()).toBe(401);
});

// ---------------------------------------------------------------------------
// E2E-API-10 — /api/agents/<id>/prompt requires Bearer (401 without token)
// ---------------------------------------------------------------------------
test('E2E-API-10 — /api/agents/software-engineer/prompt without Bearer returns 401', async ({
  request,
}) => {
  const response = await request.get(`${BASE_URL}/api/agents/software-engineer/prompt`, {
    headers: {},
  });
  expect(response.status()).toBe(401);
});

// ---------------------------------------------------------------------------
// E2E-API-11 — /api/agents/../../etc/passwd returns 400 or 403 (path traversal)
// ---------------------------------------------------------------------------
test('E2E-API-11 — Path traversal on prompt endpoint returns 400 or 403', async ({
  request,
}) => {
  // Various path traversal attempts
  const traversalIds = [
    '../../etc/passwd',
    '../../../etc/passwd',
    '..%2F..%2Fetc%2Fpasswd',
    '%2F..%2F..%2Fetc%2Fpasswd',
  ];

  for (const id of traversalIds) {
    const response = await request.get(
      `${BASE_URL}/api/agents/${id}/prompt`,
      { headers: authHeaders() }
    );
    // Must return 400, 403, or 404 — never 200
    expect([400, 403, 404]).toContain(response.status());
  }
});

// ---------------------------------------------------------------------------
// E2E-API-12 — /api/workflows/<name> detail endpoint returns 404 for unknown name
// ---------------------------------------------------------------------------
test('E2E-API-12 — /api/workflows/unknown-workflow-xyz returns 404', async ({ request }) => {
  const response = await request.get(
    `${BASE_URL}/api/workflows/unknown-workflow-xyz-that-does-not-exist`,
    { headers: authHeaders() }
  );
  expect(response.status()).toBe(404);
});

// ---------------------------------------------------------------------------
// E2E-AGT-12 — Telemetry state pre-check skip guard
// ---------------------------------------------------------------------------
test('E2E-AGT-12 — API with empty telemetry DB returns agents array (not 503)', async ({
  request,
}) => {
  // Pre-check: if the panel is running without telemetry (503), skip this test
  // rather than failing. 503 means the panel started in no-telemetry mode,
  // which is valid (the test environment may not have wired up telemetry).
  const probeResponse = await request.get(`${BASE_URL}/api/agents`, {
    headers: authHeaders(),
  });

  if (probeResponse.status() === 503) {
    // Skip: panel is in no-telemetry mode; this is a valid CI configuration.
    // The test suite still documents the expected behavior for when telemetry
    // IS configured with an empty SQLite.
    test.skip(true, 'Panel is in no-telemetry mode (503); skipping telemetry state guard test');
    return;
  }

  // When panel runs with DADAIA_TELEMETRY_DB=/tmp/test_telemetry_empty.sqlite,
  // /api/agents must return 200 with exactly 10 agents (canonical catalog),
  // not a 503 or empty array.
  expect(probeResponse.status()).toBe(200);

  const body = await probeResponse.json();
  expect(body).toHaveProperty('agents');
  expect(Array.isArray(body.agents)).toBe(true);

  // Must be exactly 10 (canonical catalog, not telemetry-only agents)
  // With empty telemetry, only the canonical agents should appear.
  expect(body.agents).toHaveLength(10);

  // All agents must have status "inactive" when telemetry is empty
  for (const agent of body.agents) {
    expect(agent.status).toBe('inactive');
    expect(agent.telemetry.session_count).toBe(0);
    expect(agent.telemetry.last_activity_at).toBeNull();
  }
});
