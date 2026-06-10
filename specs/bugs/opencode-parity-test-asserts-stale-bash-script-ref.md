---
title: opencode-parity-test-asserts-stale-bash-script-ref
severity: Medium
opened: 2026-06-09
session_id: null
status: Closed
superseded_by: v0.1.8
surface: tests/e2e/features/test_opencode_parity_hardening.py
related_release: 0.1.8
related_task: T-018-19
---

**Resolution (T-010-01, 2026-06-09):** Already fixed by v0.1.8 — line 129 now reads
`assert "sdd-spec-gate.sh" not in text` and `test_sdd_gate_plugin_projected` passes
(`pytest -p no:cacheprovider -q ...::test_sdd_gate_plugin_projected` → `1 passed in 0.39s`).


**Symptom:** After T-018-19 migrated `public/plugins/sdd-gate.ts` to call the Python
governance hook (`python -m dadaia_workspace.hooks.sdd_gate`) and removed the `bash
<script>.sh` dependency (ADR-7, non-deferrable), the e2e test
`TestPluginProjection::test_sdd_gate_plugin_projected` fails on a stale assertion:

```
assert "sdd-spec-gate.sh" in text
```

The projected `sdd-gate.ts` no longer references `sdd-spec-gate.sh` by design — that is
exactly the bash dependency ADR-7 mandates removing. The assertion encodes the
pre-0.1.8 (v0.2.0) contract and contradicts the approved 0.1.8 SPEC.

**Repro:**
```
.dadaia/.venv/bin/pytest -p no:cacheprovider -q \
  tests/e2e/features/test_opencode_parity_hardening.py::TestPluginProjection::test_sdd_gate_plugin_projected
```

**Expected:** the test should assert the NEW Python-hook invocation contract, e.g.
that the projected `sdd-gate.ts` invokes `dadaia_workspace.hooks.sdd_gate` and does NOT
contain `bash ` / `sdd-spec-gate.sh`. (Mirror of the supersede-not-append assertion
software-engineer added for the Claude/Codex configs in T-018-17's
`test_public_assets.py`.)

**Scope / ownership note:** `tests/**` is owned by `software-engineer` / `qa-engineer`,
not `ai-engineer`. T-018-19's write set is the two `.ts` plugins only and does not
include this test, so ai-engineer did not edit it. This is a planning gap: no 0.1.8
task assigns updating this stale assertion. It must be fixed by `software-engineer`
(suggest folding into T-018-22 or a small follow-up task) before the alpha/rc suite
can be green and before any push (`never push red`).

**Notes:** Sibling test `test_ctx_inject_uses_migrated_signature` (asserts
`chat.message` + `output.parts`) still passes — `ctx-inject.ts` retained both. Only the
`sdd-spec-gate.sh` assertion is stale. Single failing test; rest of the suite green
(2504 passed, 1 failed).
