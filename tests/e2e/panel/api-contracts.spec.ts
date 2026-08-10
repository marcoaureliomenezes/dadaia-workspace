import { test, expect } from '@playwright/test';
import { authHeaders, BASE_URL } from './helpers';

test('Panel APIs expose a non-empty agents catalog', async ({ request }) => {
  const agentsResponse = await request.get(`${BASE_URL}/api/agents`, { headers: authHeaders() });
  expect(agentsResponse.status()).toBe(200);
  const agentsBody = await agentsResponse.json();
  expect(Array.isArray(agentsBody.agents)).toBe(true);
  expect(agentsBody.agents.length).toBeGreaterThan(0);
});

test('Prompt endpoint handles unknown names safely', async ({ request }) => {
  const prompt = await request.get(
    `${BASE_URL}/api/agents/unknown-agent-xyz-that-does-not-exist/prompt`,
    { headers: authHeaders() }
  );
  expect(prompt.status()).toBe(404);

  // The workflow catalog died with the engine (v0.3.0): the route must be gone.
  const workflow = await request.get(
    `${BASE_URL}/api/workflow-catalog`,
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
