import { test, expect } from '@playwright/test';
import { authHeaders, BASE_URL } from './helpers';

test('Panel APIs expose a non-empty agents catalog', async ({ request }) => {
  const agentsResponse = await request.get(`${BASE_URL}/api/agents`, { headers: authHeaders() });
  expect(agentsResponse.status()).toBe(200);
  const agentsBody = await agentsResponse.json();
  expect(Array.isArray(agentsBody.agents)).toBe(true);
  expect(agentsBody.agents.length).toBeGreaterThan(0);
});

// The workflow engine was demolished, so its routes were removed from the table. A
// removed route must read as ABSENT (404), never as a registered name whose view is
// gone (500) — bug panel-dead-workflow-routes-500-after-demolition.
test('A demolished workflow route is absent, not broken', async ({ request }) => {
  const gone = await request.get(`${BASE_URL}/api/workflow-catalog`, { headers: authHeaders() });
  expect(gone.status()).toBe(404);
});

test('Prompt and workflow detail endpoints handle unknown names safely', async ({ request }) => {
  const prompt = await request.get(
    `${BASE_URL}/api/agents/unknown-agent-xyz-that-does-not-exist/prompt`,
    { headers: authHeaders() }
  );
  expect(prompt.status()).toBe(404);

  const workflow = await request.get(
    `${BASE_URL}/api/workflow-catalog/unknown-workflow-xyz-that-does-not-exist`,
    { headers: authHeaders() }
  );
  expect(workflow.status()).toBe(404);
});

test('Prompt endpoint rejects traversal-like names', async ({ request }) => {
  for (const id of [
    '../../etc/passwd',
    '../../../etc/passwd',
    '..%2F..%2Fetc%2Fpasswd',
    '%2F..%2F..%2Fetc%2Fpasswd',
  ]) {
    const response = await request.get(`${BASE_URL}/api/agents/${id}/prompt`, {
      headers: authHeaders(),
    });
    expect([400, 403, 404]).toContain(response.status());
  }
});
