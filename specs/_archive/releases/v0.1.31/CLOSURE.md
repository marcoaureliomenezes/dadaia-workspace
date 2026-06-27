# Closure: Release — v0.1.31 — make the dadaia-workflows actually run on a real Layer-2 worker

> **Status:** Aprovado
> **Release ID:** v0.1.31
> **Owner:** product-engineer
> **Closed:** 2026-06-27

## Summary

v0.1.31 closes the gap between "the workflow engine dispatches a real Layer-2 worker" and
"a real Layer-2 worker completes a workflow step under the typed gate." Before this release,
every lifecycle-workflow test ran the **fake** runtime (a canned `{"verdict":"APPROVED"}`),
and that fake masked two HIGH worker-contract bugs end-to-end: a malformed PI headless command
(`pi … -p -`) that BLOCKed every `--harness pi` step at step 1, and a verdict gate that
required a self-reported `APPROVED` from **every** model step — including *create* steps that
produce an artifact rather than approve anything. No real worker run had ever advanced past
step 1.

The release restores the workflow's own documented design — the verdict gate is **review-only**:
review steps gate on `verdict == APPROVED` + evidence + in-scope paths (unchanged); create steps
gate on a schema-valid/structural payload + populated `artifact_refs` + in-scope paths, and the
`verdict` field is ignored for them. The fix lands once in `agent_runner._blocked_result` (branch
on a threaded `is_review` signal) and is threaded through all seven runner call sites; crucially
`PipelineStep` gained an `is_review` field so the qa/security/code review gates that protect the
push boundary keep their `verdict == APPROVED` requirement. The single existing
`shared.output_handoff` contract is bundled into every producing create step so a real worker is
told to emit its schema'd payload. The already-landed `c8513fa5` PI command fix is adopted +
re-verified + hardened with a real `pi` smoke. Finally, an **anti-fake** env-gated real-worker
e2e drives a real `pi` worker through `release_scope → spec_create` — the exact shipped-failure
path — so a fake can never again mask a worker-contract break.

The convergence proof is live: with `DADAIA_E2E_REAL_WORKER=1` a real `pi` worker
(gpt-5.5, on the operator's OpenAI Codex subscription) drove the workflow **past step 1** under
the review-only gate. The live run also surfaced — and the release resolved — a worker-compliance
residual: real GPT/Codex workers do **not** reliably emit the fenced/labelled payload, so the PI
extractor was hardened to accept fenced-or-bare JSON plus a structural acceptance path. Default
`pytest` / CI stay fully faked + green (the three live tests skip by default). This CLOSURE was
authored CLOSURE-ONLY per the operator's decision — no push, no PR, no `git mv` to `_archive`
(the coordinator performs the archive/repoint mechanics after this document, the memory atoms,
and the disposition sweep are written).

## Tasks completed

All Wave A/B/C implementation tasks are `[x]`. T-31-C-03 (optional codex second case) was
deliberately SKIPPED — `pi` alone satisfies the core deliverable and a codex live contract test
already exists. T-31-Z-01 is this CLOSURE task. Commit SHAs are on `feature/v0.1.31`
(range `8c66700f..HEAD`).

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-31-A-01 | Failing review-only gate-distinction tests (TDD) | `e87d54e7` |
| T-31-A-02 | Thread `is_review` into `AgentRunnerInput` + branch `_blocked_result` | `e87d54e7` |
| T-31-A-03 | Thread `is_review=step.is_review` at the four review-capable workflows + fix comment | `e87d54e7` |
| T-31-A-04 | Thread `is_review=False` at `backlog_definition` (`backlog_author` create step) | `e87d54e7` |
| T-31-A-05 | C1 fix: add `is_review` to `PipelineStep` + thread pipeline review steps | `e87d54e7` |
| T-31-A-06 | C1 fix: thread `phase_workflow` review-phase steps | `e87d54e7` |
| T-31-A-07 | Failing fragment-bundle test (derives producing-step set from `_SEQUENCE`) | `e87d54e7` |
| T-31-A-08 | Bundle `shared.output_handoff` into every producing create step | `e87d54e7` |
| T-31-B-01 | Re-verify the PI argv unit assertion (`argv[-1] == "-p"`, no trailing `-`) | `ce77d9a6` |
| T-31-B-02 | Real `pi` smoke (env-gated, skipped by default) | `ce77d9a6` |
| T-31-C-01 | Anti-fake real-worker e2e: `release_scope → spec_create` chain | `ce77d9a6` |
| T-31-C-02 | Harden PI result extraction (worker-compliance residual) | `beba502c` |
| T-31-C-03 | (Optional) codex real-worker second case | SKIPPED — optional; `pi` satisfies the deliverable; codex live contract test already exists |
| T-31-Z-01 | Release closure + memory atoms + disposition sweep | this commit |

Supporting on-branch commits: `c8513fa5` (adopted PI `-p -`→`-p` command fix, predates this
release on-branch), `8359a3e9` (DEFINITION: SPEC/PLAN/TASKS/GRILL), `1baffe50` / `9c653aab`
(chore/marker commits).

## Validations

Each validation is a triple: description, command, evidence.

| Description | Command | Evidence |
|-------------|---------|----------|
| Full faked suite green (3 real-worker live tests skip by default) | `pytest -p no:cacheprovider` | `4068 passed, 16 skipped` |
| Strict type-check clean | `mypy --strict dadaia_workspace` | `Success` — 288 files |
| Format clean | `ruff format --check .` | clean |
| Lint clean | `ruff check --no-cache .` | clean |
| **LIVE anti-fake real-worker e2e** — real `pi` (gpt-5.5, OpenAI Codex subscription) drives `release_scope → spec_create` past step 1 under the review-only gate | `DADAIA_E2E_REAL_WORKER=1 PI_BIN=$(command -v pi) pytest tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py` | **PASSED** (245s) — not blocked, no `"agent result missing APPROVED verdict"` BlockedState, advanced beyond `release_scope`, parsed SUCCEEDED result |
| **LIVE PI command smoke** — real `pi` command executes without "Unknown option: -" | `DADAIA_E2E_REAL_WORKER=1 PI_BIN=$(command -v pi) pytest tests/integration/pi_live/test_pi_command_smoke.py` | **PASSED** |
| Code review | code-reviewer | APPROVE |
| Security review (0 CRITICAL/HIGH/MEDIUM, 0 secrets) | security-reviewer | APPROVE |
| Acceptance review (A1–A18 covered) | qa-engineer | APPROVE |

## Drifts

### real-gpt-codex-workers-emit-bare-or-inconsistently-labelled-payload

**Description:** The Wave-C anti-fake e2e was designed to PROVE that a real `pi`/`codex` worker
reliably emits the fenced, schema-labelled structured payload the create-step gate consumes (SPEC
A16 / R4 named this as the reason the e2e is mandatory). The live run disproved the "reliably
emits" assumption: across two runs the real gpt-5.5 worker produced inconsistent output —
**run 1** emitted **bare (unfenced) JSON** carrying a top-level `schema: agent-run-result-v1`;
**run 2** emitted bare JSON with **no top-level `schema`** (a nested `output_schema:
release-scope-handoff-v1` instead). A strict fenced + exact-`schema`-label extractor would have
returned `None` → empty `artifact_refs` → the create step would have BLOCKed even though the
worker did its job.

**Resolution:** Took the C-02 "harden + record residual" path. `pi_runtime._verdict_payload` was
hardened to extract a payload from (1) a fenced ```` ```json ```` block, (2) the whole bare
message, or (3) the outermost `{…}` slice, and to accept a payload **structurally** — non-empty
`artifact_refs` plus `status`/`summary`/`structured_output` — when the `schema` label is absent or
mismatched. The hardened path keeps the create-step contract honest (a no-op worker that emits no
payload still produces empty `artifact_refs` and still BLOCKs — A4/L2 unchanged); it only tolerates
real workers labelling their valid payload imperfectly. The live e2e is GREEN through the hardened
path. The prompt-side root cause (the lifecycle prompt names two schemas, which confuses real
workers into emitting the wrong/absent label) is **out of scope to fix now** and tracked as a
follow-up bug `lifecycle-prompt-names-two-schemas-confusing-real-workers` — the hardening tolerates
the imperfection; the bug tracks fixing the prompt so workers emit the canonical label.

**Memory updates:** `specs/memory/product/sdd/lifecycle-foundation.md` (the review-only gate
contract + the hardened PI extractor accepting fenced-or-bare + structural payloads);
`specs/memory/architecture.md` (the typed gate's create-vs-review distinction).

## Memory updates

Memory describes the product as it is **after** v0.1.31 (atomic snapshot, not a changelog).
Files written during this CLOSURE phase:

- `specs/memory/architecture.md` — the typed gate is now **review-only**: review steps gate on
  `verdict == APPROVED` + evidence + in-scope paths; create steps gate on a schema-valid/structural
  payload + `artifact_refs` + in-scope paths (the `verdict` field is ignored for create steps). The
  dadaia-workflows now run on a real Layer-2 worker end-to-end (validated live on pi/gpt-5.5),
  guarded by an env-gated anti-fake real-worker e2e.
- `specs/memory/product/sdd/lifecycle-foundation.md` — replaced the stale "uniform APPROVED-verdict
  gate" note with the review-only gate contract (`is_review` threaded through all seven runner call
  sites; `PipelineStep.is_review`); recorded that the dadaia-workflows are now proven end-to-end on
  a real Layer-2 worker via the env-gated anti-fake e2e; recorded that real GPT/Codex workers emit
  bare/inconsistently-labelled JSON so the PI extractor accepts fenced-or-bare + structural
  payloads. Removed the corresponding "deferred" items from `## Current limits`.
- `specs/memory/tech-stack.md` — recorded the live-verified pinned `pi` build (0.79.3, provider
  openai-codex, model gpt-5.5) and removed the "version not captured this cycle" TODO for `pi`. No
  new locked dependency (`pi` remains an optional external CLI runtime).
- `specs/memory/product/index.md` — no change: no catalog reorder, no feature added/removed (all
  touched features already cataloged).
- `specs/memory/product/catalog.json` — no slug add/remove; regenerate via the catalog generator
  only if the coordinator wants the per-atom `last_updated` reflected in the index.

## Dispositions

Disposition-sweep ledger. Both picked bugs are solved by this release and flipped to
`status: Closed` with an evidence pointer; neither is deleted (never-delete law, L7). Two
follow-up bugs surfaced this release stay Open and are recorded under "Backlog returns".

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/pi-headless-command-trailing-dash-breaks-layer2.md` | bug | `Closed` | `c8513fa5` (adopted `-p -`→`-p` fix) + live `test_pi_command_smoke.py` PASS (A12/A13); CLOSURE Validations |
| `specs/bugs/lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate.md` | bug | `Closed` | `e87d54e7` (review-only gate + create-step payload bundle) + `beba502c` (hardened extractor) + live real-worker e2e PASS advancing past step 1 (A14/A15); CLOSURE Validations |

## Backlog returns

Two follow-up bugs surfaced during this release. They are out of scope to fix now and stay
`Open` (never-delete law); they are not promoted to backlog candidates — they are filed bugs:

- `specs/bugs/lifecycle-prompt-names-two-schemas-confusing-real-workers.md` (**Open**) — the C-02
  residual root cause: the lifecycle prompt names two schemas, confusing real GPT/Codex workers into
  emitting the wrong/absent payload label. The hardened extractor tolerates it; this bug tracks
  fixing the prompt so workers emit the canonical label.
- `specs/bugs/subagent-handoff-resolves-dadaia-inside-repo-cwd.md` (**Open**) — escalated to MEDIUM
  this session; carried forward.

No new backlog candidates or ideas beyond the above filed bugs.

## Archive decision

**MOVE** — the release directory will be moved to `specs/_archive/releases/v0.1.31/` via `git mv`,
and `ACTIVE.md` repointed to the next release (or `release: none`), **by the coordinator** (the
operator's CLOSURE-ONLY decision defers the archive/repoint mechanics to the coordinator after this
document, the memory atoms, and the disposition sweep are written). Product-engineer does not push,
open a PR, or `git mv` in this turn.
