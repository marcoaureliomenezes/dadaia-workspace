---
name: pi-headless-does-not-recover-written-handoff-without-artifact-refs
status: Closed
severity: HIGH
reported: 2026-06-29
resolved: 2026-06-29
release: v0.1.37
surface: PiHeadlessAdapter / lifecycle review gates
session_id: codex-goal-v0.1.37-pi-smoke
---

# PI headless does not recover a written handoff when final output omits `artifact_refs`

**Symptom:** A real PI Layer-2 security-review worker wrote a valid APPROVED handoff, but
the lifecycle review gate blocked with `agent result missing artifact evidence`.

**Repro:**

```bash
timeout 420 .dadaia/.venv/bin/dadaia lifecycle review security \
  --context dadaia-workspace \
  --release-id v0.1.37 \
  --run-id v0137-security-pi-smoke-9d60ed63 \
  --harness pi \
  --model gpt-5.3-codex-spark:medium \
  --json
```

Result:

```json
{"accepted": false, "blocked": {"reason": "agent result missing artifact evidence"}}
```

But PI wrote:

```text
.dadaia/handoff/dadaia-workspace/2026-06-28T190000Z-security-reviewer-v0137-security-pi-smoke-9d60ed63.handoff.json
```

The handoff contains `verdict: APPROVED`, `release_id: v0.1.37`, and
`metrics.commit_sha: 9d60ed63efbfbb156ca200aac94771bb8a97cae5`.

**Expected:** PI should behave like the Codex headless adapter: if the final assistant
message is prose or omits artifact refs, recover a newly written matching handoff from the
allowed handoff directory and surface it as artifact evidence.

**Actual:** PI parsing returned no `artifact_refs`, so `LifecycleAgentRunner` blocked even
though the handoff existed on disk.

**Root cause hypothesis:** `PiHeadlessAdapter` parses only the final message payload and
lacks the written-handoff recovery path already present in `CodexExecAdapter`.

**Impact:** PI review workflows can do the right filesystem work and still fail the Python
gate, making PI unreliable as a Layer-2 review worker.

## Resolution

Closed in `v0.1.37/alpha-1`.

Root cause: `PiHeadlessAdapter` parsed the final PI `message_end` text but did not recover
matching handoff files written during the run when that final text omitted the
`agent-run-result-v1` artifact refs. `CodexExecAdapter` already had this recovery path.

Fix: `PiHeadlessAdapter` now records the subprocess start time and, when the parsed result
lacks artifact evidence/verdict, recovers the newest matching handoff written for the same
role/context/release during the run. The recovered handoff supplies `artifact_refs`,
`verdict`, `verdict_reason`, and `commit_sha` to the Python gate.

Validation:

- `pytest -p no:cacheprovider tests/contract/test_headless_runtime_security.py -q` -> `14 passed`.
