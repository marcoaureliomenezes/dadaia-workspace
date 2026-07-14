# Closure: Release - v0.2.3

> **Status:** Aprovado
> **Release ID:** v0.2.3
> **Owner:** product-engineer
> **Closed:** 2026-07-14

## Summary

v0.2.3 reduces dadaia-workspace to exactly four governed workflows: backlog definition,
release definition, implementation plus reviews, and audit. The release removes stale
workflow aliases and blocking workspace coordination, replaces it with advisory presence,
hardens immutable step handoffs and bounded correction, and adds the panel Games tab used
for real browser validation.

All four workflows completed with real Codex workers and with PI workers authenticated
through the Codex subscription. The campaign did not use OpenRouter; OpenRouter remains an
explicit optional provider supported by the product.

## Tasks completed

| Task ID | Description | Final commit |
|---|---|---|
| T01 | Consolidate workflow and CLI surface | `903f8b89810395d0369320878a73db93b2a628f5` |
| T02 | Harden immutable workflow handoffs | `903f8b89810395d0369320878a73db93b2a628f5` |
| T03 | Align panel, public assets, and memory | `903f8b89810395d0369320878a73db93b2a628f5` |
| T04 | Add and browser-validate Snake and Tetris | `903f8b89810395d0369320878a73db93b2a628f5` |
| T05 | Complete four real Codex and four real PI journeys | `903f8b89810395d0369320878a73db93b2a628f5` |
| T06 | Final verification, cleanup, and closure | `903f8b89810395d0369320878a73db93b2a628f5` |

## Validations

| Description | Command | Evidence |
|---|---|---|
| Full Python suite | `PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/python -m pytest -p no:cacheprovider -q` | `2647 passed, 9 skipped in 172.06s` |
| Focused no-lock and hook regression suite | same pytest command over the affected hook, context, chokepoint, and contract files | `103 passed in 6.79s` |
| Memory schema and headings | `.dadaia/.venv/bin/python dadaia_workspace/public/scripts/lint-memory-atoms.py --memory-dir specs/memory` | `30 OK, 0 WARN-only, 0 ERROR` |
| Public projection | `.dadaia/.venv/bin/dadaia public stage && ... public install --target all && ... public doctor` | `[ok] public-privacy; [ok] model-resolution; [ok] ai-surface; [ok] workflow-policy` |
| Workflow coherence | `.dadaia/.venv/bin/dadaia reports workflow-doctor --json` | `{"coherence": [], "findings": []}` |
| v0.2.3 handoff coherence | `.dadaia/.venv/bin/dadaia reports workflow-handoffs-doctor --context dadaia-workspace --release-id v0.2.3 --json` | `{"findings": [], "ok": true, "status": "ok"}` |
| Reports integrity | `.dadaia/.venv/bin/dadaia reports doctor --json` | `{"ok": true, "issue_count": 0, "issues": []}` |
| Bug ledger | `.dadaia/.venv/bin/dadaia bugs status` | `[ok] 0 open bug(s).` |
| Codex Layer-2 journeys | four real lifecycle commands with `--harness codex` | completed run IDs: `phantom-v026-backlog-codex1/2`, `phantom-v026-release-codex7`, `phantom-v026-impl-codex3`, `phantom-v026-audit-codex9`; model `gpt-5.5` |
| PI Layer-2 journeys | four real lifecycle commands with `--harness pi` | completed run IDs: `phantom-v027-backlog-pi-codexsub1`, `phantom-v027-release-pi-codexsub2`, `phantom-v027-impl-pi-codexsub4`, `phantom-v027-audit-pi-codexsub1`; model `openai-codex/gpt-5.5`; OpenRouter not used |
| Games browser journey | Playwright desktop `1440x900` and mobile `390x844` | `/home/ubuntu/workspace/.dadaia/tmp/root/20260713/games-browser/results.json`; both canvas digests changed after input, no overflow or substantive failed response |
| Workflow hygiene | `.dadaia/.venv/bin/dadaia reports workflow-hygiene-clean --apply --json` | `3575` eligible artifacts reclaimed; `129` protected; `0` unreclaimable |
| Source hygiene | `git diff --check` plus forbidden cache/state scan | clean; no repo-local cache, bytecode, runtime projection, or workspace state directory |

Ruff and mypy were not rerun because those executables are absent from the workspace
virtual environment and Poetry is not installed. Their covered Python behavior is exercised
by the full pytest suite; CI remains the authoritative lint/type gate.

## Drifts

### No-lock remediation expanded

**Description:** The original consolidation exposed that repairing lease identity would
retain the operator-facing freeze risk. The accepted resolution removed workspace lease,
adoption, steal, and incumbent-pointer authority rather than patching them.

**Resolution:** Mutating writes now upsert best-effort presence and may emit an advisory.
Caller-local READ mode, frozen paths, memory phase, and security push review remain quality
or self-protection gates, not concurrency locks.

**Memory updates:** `specs/memory/architecture.md`, context management, workspace doctor,
SDD gate, product vision, orchestration, and quality assurance atoms.

### PI campaign provider

**Description:** Early PI profiles could route GPT-shaped names through OpenRouter, which
spent the wrong provider budget and made the test provenance ambiguous.

**Resolution:** All PI campaign reruns used the provider-qualified
`openai-codex/gpt-5.5` model through Codex subscription authentication. Optional OpenRouter
support remains available but was not exercised in this release campaign.

**Memory updates:** `specs/memory/tech-stack.md` and
`specs/memory/product/harness/harness-pi.md`.

### Retired-test cleanup

**Description:** The first green full suite still contained tests that recreated deleted
lease and pointer mechanics only to prove they were ignored.

**Resolution:** Retired-invariant tests and stale fixture wording were removed. Current
coverage remains on advisory presence, caller-local mode, migration cleanup, doctor repair,
and bounded telemetry serialization. The final suite count is therefore lower than the
earlier pre-cleanup run.

**Memory updates:** no additional atom; current memory already describes the final behavior.

## Memory updates

- `specs/memory/architecture.md` - current three-ring architecture, four-workflow control plane, no-lock boundary, and runtime state.
- `specs/memory/tech-stack.md` - Codex/PI models, optional OpenRouter profile, and current toolchain.
- `specs/memory/quality-assurance.md` - current validation and release-gate truth.
- `specs/memory/product/agents/agent-orchestration.md` - nine Layer-1 roles, eight Layer-2 personas, and advisory concurrency.
- `specs/memory/product/harness/harness-codex.md` - current Codex entry and worker behavior.
- `specs/memory/product/harness/harness-pi.md` - Codex-subscription and optional OpenRouter provider contracts.
- `specs/memory/product/panel/panel.md` - seven tabs including Games.
- `specs/memory/product/philosophy/product-vision.md` - four reliable workflows and anti-slop boundary.
- `specs/memory/product/philosophy/spec-context-project.md` - caller-local binding and advisory presence.
- `specs/memory/product/platform/context-management.md` - no-lock bind/session model.
- `specs/memory/product/platform/cross-platform-portability.md` - current cross-platform adapters.
- `specs/memory/product/platform/multi-platform-parity.md` - Claude, Codex, and PI projection parity.
- `specs/memory/product/platform/workspace-doctor.md` - stale presence and retired-state cleanup.
- `specs/memory/product/platform/workspace-init.md` - current workspace bootstrap.
- `specs/memory/product/sdd/dadaia-workflows.md` - exactly four governed workflows.
- `specs/memory/product/sdd/lifecycle-foundation.md` - fragment-scoped engine and immutable payloads.
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` - workflow intake and terminal disposition behavior.
- `specs/memory/product/sdd/sdd-gate-v3.md` - path, phase, caller-mode, presence, and push gates.
- `specs/memory/product/sdd/specs-doctor.md` - current structural and governance checks.
- `specs/memory/product/catalog.json` and `specs/memory/product/index.md` - regenerated 27-feature catalog.

## Dispositions

All rows below are terminal `resolved` events in `specs/bugs/bugs.jsonl` with
`release: v0.2.3`.

| Bug ID | Kind | Terminal status | Evidence |
|---|---|---|---|
| `approved-review-never-flips-artifact-status` | bug | `resolved` | v0.2.3 bug event |
| `artifact-path-discarded-when-refs-list-present` | bug | `resolved` | v0.2.3 bug event |
| `audit-drift-found-blocks-triage` | bug | `resolved` | v0.2.3 bug event |
| `audit-drift-scan-injects-unbounded-source-context` | bug | `resolved` | v0.2.3 bug event |
| `audit-findings-digest-drops-stable-identities` | bug | `resolved` | v0.2.3 bug event |
| `audit-scope-handoff-digest-drops-scope-contract` | bug | `resolved` | v0.2.3 bug event |
| `audit-workflow-accepts-empty-scope-and-triage` | bug | `resolved` | v0.2.3 bug event |
| `audit-workflow-creates-repo-bytecode-artifacts` | bug | `resolved` | v0.2.3 bug event |
| `backlog-author-write-scope-excludes-backlog` | bug | `resolved` | v0.2.3 bug event |
| `backlog-define-has-no-demand-input-channel` | bug | `resolved` | v0.2.3 bug event |
| `backlog-definition-omits-step-ledger` | bug | `resolved` | v0.2.3 bug event |
| `blocked-definition-run-cannot-resume-from-step` | bug | `resolved` | v0.2.3 bug event |
| `blocked-reason-misreports-rejected-verdict-as-missing` | bug | `resolved` | v0.2.3 bug event |
| `bugs-append-ledger-ignores-context-flag` | bug | `resolved` | v0.2.3 bug event |
| `close-step-accepts-not-closeable-refusal` | bug | `resolved` | v0.2.3 bug event |
| `codex-adapter-drops-top-level-verdict` | bug | `resolved` | v0.2.3 bug event |
| `codex-noncompliant-output-lacks-diagnostic` | bug | `resolved` | v0.2.3 bug event |
| `context-relative-spec-ref-blocks-correct-deliverable` | bug | `resolved` | v0.2.3 bug event |
| `create-step-gate-accepts-refusal-handoff-as-success` | bug | `resolved` | v0.2.3 bug event |
| `definition-commit-gate-never-repoints-active-md` | bug | `resolved` | v0.2.3 bug event |
| `doctor-016-errors-archived-legacy-release-027-tolerates` | bug | `resolved` | v0.2.3 bug event |
| `doctor-fix-skips-graveyard-gc-when-check-clean` | bug | `resolved` | v0.2.3 bug event |
| `doctor-ptr-gc-deletes-valid-lock-free-bind` | bug | `resolved` | v0.2.3 bug event |
| `doctor-root-whitelist-contradicts-root-law` | bug | `resolved` | v0.2.3 bug event |
| `durable-step-payload-drops-domain-handoff` | bug | `resolved` | v0.2.3 bug event |
| `exact-handoff-written-but-last-message-unparseable` | bug | `resolved` | v0.2.3 bug event |
| `fragment-workflows-drop-worker-diagnostics` | bug | `resolved` | v0.2.3 bug event |
| `fragment-workflows-never-persist-step-handoffs` | bug | `resolved` | v0.2.3 bug event |
| `gate-accepts-phantom-artifact-evidence` | bug | `resolved` | v0.2.3 bug event |
| `headless-worker-prompt-omits-execution-root` | bug | `resolved` | v0.2.3 bug event |
| `implement-verb-never-derives-task-write-scope` | bug | `resolved` | v0.2.3 bug event |
| `implementation-workflow-closes-release-with-open-task-markers` | bug | `resolved` | v0.2.3 bug event |
| `implementation-workflow-does-not-own-task-markers` | bug | `resolved` | v0.2.3 bug event |
| `init-venv-never-installs-dadaia-workspace` | bug | `resolved` | v0.2.3 bug event |
| `legacy-dadaia-bugs-sink-duplicates-doctor-findings` | bug | `resolved` | v0.2.3 bug event |
| `lifecycle-preflight-uses-foreign-incumbent-mode` | bug | `resolved` | v0.2.3 bug event |
| `lifecycle-restart-retains-stale-worker-output` | bug | `resolved` | v0.2.3 bug event |
| `malformed-handoff-classifier-rejects-non-report-artifacts` | bug | `resolved` | v0.2.3 bug event |
| `no-locks-doctrine-retains-blocking-context-locks` | bug | `resolved` | v0.2.3 bug event |
| `obsolete-src-and-legacy-runtime-bugs-still-scaffolded` | bug | `resolved` | v0.2.3 bug event |
| `pi-gpt-profiles-ambiguously-resolve-to-openrouter` | bug | `resolved` | v0.2.3 bug event |
| `pi-headless-loads-foreign-context-files` | bug | `resolved` | v0.2.3 bug event |
| `pi-implementation-profile-targets-unavailable-codex-subscription-model` | bug | `resolved` | v0.2.3 bug event |
| `pi-openrouter-gpt-profiles-bypass-codex-subscription` | bug | `resolved` | v0.2.3 bug event |
| `pipeline-close-scope-placeholders-not-expanded` | bug | `resolved` | v0.2.3 bug event |
| `pipeline-retries-overwrite-external-handoff-path` | bug | `resolved` | v0.2.3 bug event |
| `plan-dependency-gate-rejects-numbered-heading` | bug | `resolved` | v0.2.3 bug event |
| `preflight-hygiene-gate-demands-root-owned-deletions` | bug | `resolved` | v0.2.3 bug event |
| `preflight-references-removed-lifecycle-hygiene-command` | bug | `resolved` | v0.2.3 bug event |
| `prose-worker-with-valid-handoff-loses-verdict` | bug | `resolved` | v0.2.3 bug event |
| `release-create-scope-allows-wrong-specs-tree` | bug | `resolved` | v0.2.3 bug event |
| `release-definition-allows-validation-dependency-inversion` | bug | `resolved` | v0.2.3 bug event |
| `release-definition-approves-cache-producing-pytest-commands` | bug | `resolved` | v0.2.3 bug event |
| `release-definition-approves-plan-with-unbound-public-api-contract` | bug | `resolved` | v0.2.3 bug event |
| `release-definition-completes-with-noncanonical-spec-status` | bug | `resolved` | v0.2.3 bug event |
| `release-definition-create-steps-cannot-write-specs` | bug | `resolved` | v0.2.3 bug event |
| `release-definition-ignores-backlog-workflow-output` | bug | `resolved` | v0.2.3 bug event |
| `release-definition-yaml-status-never-approved` | bug | `resolved` | v0.2.3 bug event |
| `release-for-session-misses-unindexed-cross-context-lease` | bug | `resolved` | v0.2.3 bug event |
| `release-spec-authoring-allows-unverifiable-internal-acceptance` | bug | `resolved` | v0.2.3 bug event |
| `rerun-of-run-id-collides-with-immutable-payload-zone` | bug | `resolved` | v0.2.3 bug event |
| `result-contract-drops-singular-artifact-ref-and-changed-paths-list` | bug | `resolved` | v0.2.3 bug event |
| `resumed-definition-step-blind-to-rejecting-review-feedback` | bug | `resolved` | v0.2.3 bug event |
| `retention-sweep-crashes-on-permission-denied` | bug | `resolved` | v0.2.3 bug event |
| `review-step-out-of-scope-blocks-cited-reviewed-artifact` | bug | `resolved` | v0.2.3 bug event |
| `shaped-result-missing-artifact-has-no-diagnostic` | bug | `resolved` | v0.2.3 bug event |
| `step-payload-drops-worker-findings` | bug | `resolved` | v0.2.3 bug event |
| `structural-worker-noop-has-no-bounded-correction` | bug | `resolved` | v0.2.3 bug event |
| `worker-artifact-ref-not-materialized` | bug | `resolved` | v0.2.3 bug event |
| `worker-handoff-path-left-to-model-invention` | bug | `resolved` | v0.2.3 bug event |
| `worker-step-output-pollutes-public-handoff-namespace` | bug | `resolved` | v0.2.3 bug event |
| `write-scope-parser-blind-to-own-tasks-create-checklist-grammar` | bug | `resolved` | v0.2.3 bug event |
| `write-scope-parser-drops-nested-path-bullets` | bug | `resolved` | v0.2.3 bug event |
| `write-scope-parser-rejects-own-tasks-grammar` | bug | `resolved` | v0.2.3 bug event |

No backlog item was consumed by this release; the canonical
`specs/_archive/v0.2.3/consumed_backlog.json` sidecar records an empty set.

## Backlog returns

None. Every workflow defect encountered during the campaign was registered and resolved
inside v0.2.3.

## Archive decision

**MOVE** - move this release directory to `specs/_archive/releases/v0.2.3/` and set
`specs/releases/ACTIVE.md` to `release: none`.
