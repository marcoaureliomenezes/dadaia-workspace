# Closure: Release - v0.1.41

> **Status:** Aprovado
> **Release ID:** v0.1.41
> **Owner:** product-engineer
> **Closed:** 2026-06-30

## Summary

v0.1.41 closes the true-open dadaia-workspace bug sweep. The shipped behavior makes report validation handoff-first and explicit for HTML inputs, restores persisted-bind resolution for specs/context commands, hardens SPEC-DOC-029 identity checks, blocks nested root-whitelist escapes, prevents hook bytecode residue, enforces import-linter locally and in CI, removes stale Codex config output, fixes context-dead upstream pushes, narrows memory heading lint to generic governance, and verifies the stale panel CSP bug as already fixed.

The release also updates memory so the current product truth matches the implementation. A separate bug was registered for the closure workflow fake-harness path because the official close workflow accepted `--harness fake` and then blocked on missing artifact evidence.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T1 | Align report validation docs and CLI UX | pending commit |
| T2 | Fix specs-dir persisted bind resolution | pending commit |
| T3 | Repair SPEC-DOC-029 identity and scoped-state behavior | pending commit |
| T4 | Harden root whitelist and repo hygiene | pending commit |
| T5 | Make import-linter green and CI-enforced | pending commit |
| T6 | Remove stale Codex config and fix context-dead push | pending commit |
| T7 | Make memory heading lint consumer-extensible | pending commit |
| T8 | Verify and close stale panel CSP bug | pending commit |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Reports validation contract | `pytest -p no:cacheprovider tests/contract/cli/test_cli_reports.py -q` | stdout: `11 passed` |
| Persisted bind resolver and context release | `pytest -p no:cacheprovider tests/unit/core/test_specs_resolver.py tests/unit/cli/commands/test_context_release_cmd.py -q` | stdout: `7 passed` |
| SPEC-DOC-029 coherence and scoped specs-dir isolation | `pytest -p no:cacheprovider tests/integration/test_specs_doctor_coherence_backstop.py tests/integration/cli/test_cli_specs_doctor_coherence.py -q` | stdout: `6 passed` |
| Root whitelist, runtime bytecode suppression, and release evidence gitignore | `pytest -p no:cacheprovider tests/unit/hooks/test_root_whitelist.py tests/unit/infrastructure/test_runtime_config.py tests/contract/test_release_evidence_gitignore.py -q` | stdout: `4 passed` |
| Import-linter contracts | `lint-imports` | stdout: `Contracts: 6 kept, 0 broken` |
| Import-linter integration tests | `pytest -p no:cacheprovider tests/integration/cli/test_lifecycle_policy_cli.py tests/integration/panel/test_workflow_policy_routes_e2e.py tests/integration/test_cli_backlog_subjects.py tests/contract/cli/test_cli_ci.py -q` | stdout: `38 passed` |
| Codex config and context-dead push tests | focused pytest slices for public assets, context CLI, and dead review gate | stdout: `4 passed, 34 deselected`; `2 passed, 38 deselected`; `1 passed, 6 deselected` |
| Memory heading lint | `pytest -p no:cacheprovider tests/unit/scripts/test_lint_memory_atoms.py -q` | stdout: `25 passed` |
| Memory atom lint over real specs | `python dadaia_workspace/public/scripts/lint-memory-atoms.py --memory-dir specs/memory` | stdout: `30 OK, 0 WARN-only, 0 ERROR` |
| Panel CSP and ops-tab regression slice | Playwright panel focused slice | stdout: `15 passed` |
| Specs doctor after implementation | `dadaia specs doctor --specs-dir specs` | stdout: `0 error(s), 16 warning(s)` |
| Official closure workflow attempted | `dadaia lifecycle close --context dadaia-workspace --release-id v0.1.41 --run-id close-v0141 --harness fake --json` | stdout: `"status": "BLOCKED", "reason": "agent result missing artifact evidence"` |
| Closure workflow bug registered | `dadaia lifecycle bug report --context dadaia-workspace --release-id v0.1.41 --run-id bug-close-fake-missing-artifact ... --harness fake --json` | stdout: `"completed": true, "status": "OK"` |

## Drifts

### manual-closure-after-workflow-block

**Description:** The governed `dadaia lifecycle close` path was attempted first, but the fake harness path blocked at the closure step because the agent result had no artifact evidence.

**Resolution:** The workflow failure was registered as `specs/bugs/lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence.md`. Closure then followed the manual closure protocol allowed by the release-closure skill after a workflow failure.

**Memory updates:** No memory change was needed for this bug because the fake-harness closure failure is not desired product truth; it remains an open bug.

### memory-truth-expanded

**Description:** Implementation changed durable product behavior in several subsystems, while the implementation phase cannot write memory.

**Resolution:** Memory was updated during CLOSURE only, using current-state descriptions without changelog sections.

**Memory updates:** `architecture.md`, `tech-stack.md`, `product/agents/agent-comms.md`, `product/platform/context-management.md`, `product/sdd/specs-doctor.md`, `product/sdd/sdd-gate-v3.md`, `product/distribution/public-asset-distribution.md`, `product/catalog.json`, and `product/index.md`.

## Memory updates

- `specs/memory/architecture.md` - updated current architecture for workflow model policy port/adapter ownership, context-dead upstream push behavior, and import-linter preflight coverage.
- `specs/memory/tech-stack.md` - updated import-linter command surface to include local preflight and CI.
- `specs/memory/product/agents/agent-comms.md` - clarified that report validation validates handoff JSON and gives explicit guidance for HTML report paths.
- `specs/memory/product/platform/context-management.md` - documented persisted bind resolution for specs doctor and context release.
- `specs/memory/product/sdd/specs-doctor.md` - documented coherent harness UUID plus `sess_*` identity handling and generic memory heading lint.
- `specs/memory/product/sdd/sdd-gate-v3.md` - documented first-root-component root whitelist behavior.
- `specs/memory/product/distribution/public-asset-distribution.md` - documented that Codex config omits unsupported `approved_commands`.
- `specs/memory/product/catalog.json` - regenerated from product atom frontmatter.
- `specs/memory/product/index.md` - regenerated from product atom frontmatter.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/agents-md-says-validate-html-reports-with-json-only-validator.md` | bug | `Closed` | T1 validation |
| `specs/bugs/reports-validate-rejects-html-despite-agents-md-contract.md` | bug | `Closed` | T1 validation |
| `specs/bugs/specs-doctor-does-not-resolve-persisted-bound-context.md` | bug | `Closed` | T2 validation |
| `specs/bugs/specs-doctor-ignores-persisted-context-bind.md` | bug | `Closed` | T2 validation |
| `specs/bugs/context-release-ignores-persisted-bind-and-requires-dadaia_session_id-env.md` | bug | `Closed` | T2 validation |
| `specs/bugs/spec-doc-029-false-forgery-harness-uuid-vs-session-record-id.md` | bug | `Closed` | T3 validation |
| `specs/bugs/root-whitelist-misses-nested-new-toplevel-writes.md` | bug | `Closed` | T4 validation |
| `specs/bugs/layer1-hooks-create-repo-pycache.md` | bug | `Closed` | T4 validation |
| `specs/bugs/grill-and-oq-decisions-records-gitignored-not-version-controlled.md` | bug | `Closed` | T4 validation |
| `specs/bugs/import-linter-contracts-red-but-not-ci-enforced.md` | bug | `Closed` | T5 validation |
| `specs/bugs/codex-config-emits-invalid-approved-commands.md` | bug | `Closed` | T6 validation |
| `specs/bugs/context-dead-plain-git-push-fails-mismatched-upstream.md` | bug | `Closed` | T6 validation |
| `specs/bugs/memory-heading-allowlist-not-consumer-extensible.md` | bug | `Closed` | T7 validation |
| `specs/bugs/panel-csp-blocks-mermaid-cdn-script-and-stale-ops-subsection-test.md` | bug | `Closed` | T8 validation |

## Backlog returns

- `specs/bugs/lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence.md` remains open as follow-up tooling work.

## Archive decision

**MOVE** - release directory will be moved to `specs/_archive/releases/v0.1.41/` via `git mv`. `ACTIVE.md` will be updated to `release: none`.
