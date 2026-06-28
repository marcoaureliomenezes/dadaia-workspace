# Closure: Release — v0.1.35 alpha-1 — dadaia-workflows operational hardening

> **Status:** Aprovado
> **Release ID:** v0.1.35
> **Segment:** alpha-1
> **Owner:** product-engineer
> **Closed:** 2026-06-28

## Summary

v0.1.35 alpha-1 makes `dadaia lifecycle release define` safe enough to keep dogfooding
with Codex/PI Layer-2 workers. The release-definition workflow now receives explicit
operator scope, treats `run_id` as an operational id, and blocks create steps unless the
canonical SPEC/PLAN/TASKS artifact exists with path/hash evidence.

The release also closes the Codex/PI worker-startup residuals found while trying to run
real dadaia-workflows: Codex workers use the supported `codex exec` startup surface with a
writable workflow sandbox and workspace-root trust bypass, and PI headless failures without
a terminal `message_end` surface as adapter failures instead of misleading artifact-gate
blocks. The segment was reviewed with live Codex Layer-2 QA, security, code-review, and
close workflow steps.

## Tasks completed

All tasks in `TASKS.md` are `[x]`. The final closure commit is this commit; previous
supporting implementation commits on the branch include `d13402ef`, `3cbdccf8`,
`220441c5`, `09ae4699`, and `6f1d33f2`.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-35-01 | Add explicit release-definition scope inputs | `d13402ef` |
| T-35-02 | Gate create steps on canonical artifacts | `3cbdccf8` / `6f1d33f2` |
| T-35-03 | Dogfood bug-report workflow and inspect transcript noise | this commit |
| T-35-04 | Verify and push/readiness evidence | this commit |
| T-35-05 | Pin Layer-2 worker startup failure contracts | this commit |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Focused headless runtime contract tests | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py` | `10 passed` |
| Focused release-definition workflow tests | `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py` | `8 passed` |
| Runtime lint for touched contract test | `.dadaia/.venv/bin/python -m ruff check --no-cache repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py` | `All checks passed!` |
| Backlog consistency | `.dadaia/.venv/bin/dadaia backlog doctor --specs-dir repos/dadaia-workspace/specs` | `backlog doctor: clean.` |
| Specs structural doctor | `.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs` | `0 error(s), 18 warning(s)`; warnings are legacy/pre-existing spec-memory and archived-release warnings |
| Live release-definition workflow smoke with Codex Layer-2 scope step | `dadaia lifecycle release define --release-id v9.9.9 --run-id codex-live-release-scope-smoke --harness fake --step-harness release_scope=codex --json` | `status: OK`, `final_phase: implementation`, `release_scope.runtime: codex_exec` |
| Codex QA review gate | `dadaia lifecycle review qa --context dadaia-workspace --release-id v0.1.35 --run-id v0135-qa-codex-r2 --harness codex --json` | `.dadaia/handoff/dadaia-workspace/2026-06-28T202711Z-qa-engineer-v0135-qa-codex-r2.handoff.json` |
| Codex security review gate | `dadaia lifecycle review security --context dadaia-workspace --release-id v0.1.35 --run-id v0135-security-codex --harness codex --json` | `.dadaia/handoff/dadaia-workspace/2026-06-28T203047Z-security-reviewer-v0135-security-codex.handoff.json` |
| Codex code review gate | `dadaia lifecycle review code --context dadaia-workspace --release-id v0.1.35 --run-id v0135-code-codex --harness codex --json` | `.dadaia/handoff/dadaia-workspace/2026-06-28T203411Z-code-reviewer-v0135-code-codex.handoff.json` |
| Codex close workflow gate | `dadaia lifecycle close --context dadaia-workspace --release-id v0.1.35 --run-id v0135-close-codex --harness codex --json` | `.dadaia/handoff/dadaia-workspace/2026-06-28T203615Z-product-engineer-v0135-close-codex.handoff.json` |

## Drifts

### codex-qa-caught-lint-before-closure

**Description:** The first Codex QA workflow rejected the candidate because the newly
touched `tests/contract/test_headless_runtime_security.py` had Ruff `I001` import-order
drift.

**Resolution:** The import order was fixed, the exact Ruff command passed, the focused
contract suite still passed, and the Codex QA workflow was rerun successfully.

**Memory updates:** none — this was a local test-file formatting drift, not product truth.

### close-workflow-is-handoff-only

**Description:** `dadaia lifecycle close` accepted the close step and returned
`phase: closure`, but the worker prompt allowed only `.dadaia/handoff/**` writes, so the
close worker deliberately did not write `ACTIVE.md`, `CLOSURE.md`, memory, bug records, or
archive paths.

**Resolution:** Treat the workflow close step as the semantic close gate and perform the
documented product-engineer closure protocol manually: set `ACTIVE.md` to `CLOSURE`, write
this `CLOSURE.md`, update memory, and record dispositions. This matches the close handoff's
own recommendation to use a product-engineer closure step with spec write scope for full
SDD closure mutations.

**Memory updates:** none — this is current workflow closure behavior, already captured by
the lifecycle-foundation memory as a handoff-gated lifecycle step.

## Memory updates

Files written during this CLOSURE phase:

- `specs/memory/product/sdd/lifecycle-foundation.md` — current Codex worker startup
  behavior now names the supported `codex exec` flags and writable workflow sandbox; current
  PI failure mapping now distinguishes valid terminal `message_end` success from non-zero
  exits without terminal message, which fail with redacted stderr/stdout.
- `specs/memory/architecture.md` — no change: the high-level architecture already records
  the shared adapter base and Layer-2 worker boundary; the v0.1.35 delta is specific to the
  lifecycle memory atom.
- `specs/memory/tech-stack.md` — no change: no dependency or approved toolchain change.
- `specs/memory/product/index.md` and `specs/memory/product/catalog.json` — no change: no
  feature atom was added or removed.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/release-definition-lacks-operator-intent-channel-and-infers-scope-from-run-id.md` | bug | `Closed` | T-35-01; release-definition workflow tests |
| `specs/bugs/release-definition-spec-create-accepts-handoff-only-without-spec-file.md` | bug | `Closed` | T-35-02; create-step artifact-gate tests |
| `specs/bugs/agents-bypass-bug-report-workflow-and-handwrite-bug-files.md` | bug | `Closed` | T-35-03; bug-report workflow path inspected/documented |
| `specs/bugs/lifecycle-codex-exec-ask-for-approval-invalid.md` | bug | `Closed` | T-35-03/T-35-05; Codex command contract + live Codex workflow gates |
| `specs/bugs/codex-lifecycle-read-only-sandbox-blocks-layer2-worker-init.md` | bug | `Closed` | T-35-03/T-35-05; writable `workspace-write` adapter default + live Codex workflow gates |
| `specs/bugs/codex-lifecycle-workspace-root-requires-skip-git-repo-check.md` | bug | `Closed` | T-35-03/T-35-05; `--skip-git-repo-check` command contract + live Codex workflow gates |
| `specs/bugs/pi-headless-masks-nonzero-auth-failure-as-missing-artifact.md` | bug | `Closed` | T-35-05; PI non-zero/no-`message_end` contract test |
| `specs/bugs/codex-bind-context-injection-visible-transcript-noise.md` | bug | `Closed` | T-35-03; inspected and dispositioned as resolved/no blocking residual for this release |

## Backlog returns

Open backlog was reviewed. No additional backlog item is fully consumed by this alpha.
The stale `workflow-model-governance-operator-profiles-and-context-overlays` consumed marker
was removed from `SPEC.md` because the release does not actually deliver that backlog item.

- `workflow-model-governance-panel-control-plane` remains the operator-elected next release.
- `backlog-definition-workflow-dedup-conflict-control` remains critical and should be picked
  when the next release targets backlog hygiene.
- `workflow-step-handoff-data-plane-cleanup` remains critical and adjacent to lifecycle
  workflow hardening.
- `sdd-governance-v2-agents-lifecycle` remains open but was clarified as **partially
  consumed**; remaining scope is taxonomy/archive classes, JSONL bug telemetry, and
  audit-disposition law.

Open bugs not picked by this release remain in `specs/bugs/` for future planning. The
workflow-related open set includes backlog doctor/schema conflicts, reports validation
contract drift, lifecycle model override collapse, specs-doctor persisted-bind resolution,
subagent handoff cwd resolution, gate self-blocking, and Codex generated-command policy
residue; none blocks the v0.1.35 alpha acceptance proven above.

## Archive decision

**KEEP** — this is a segmented `alpha-1` closure. The segment is closeable and ready to
commit, but the release directory should remain under `specs/releases/v0.1.35/alpha-1/`
until the coordinator opens the next segment or makes an explicit ship/archive decision.
