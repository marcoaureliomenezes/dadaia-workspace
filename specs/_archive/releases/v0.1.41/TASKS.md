# TASKS: v0.1.41 - Open bug root-cause sweep

**Status:** Aprovado
**Release ID:** v0.1.41
**Owner:** product-engineer
**Created:** 2026-06-29

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

### T1 - Align report validation docs and CLI UX

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/reports.py`, `dadaia_workspace/features/reports_validation/**`, `dadaia_workspace/public/data/AGENTS.md`, `dadaia_workspace/public/data/handoff-AGENTS.md`, `dadaia_workspace/public/skills/dadaia-handoff-emitter/SKILL.md`, report-validation tests, picked report-validation bug files
- **Acceptance:** HTML report input no longer surfaces raw JSON parse noise; docs point validation at handoff JSON; both duplicate report-validation bugs are closed from shared evidence.
- **Validation:** `pytest -p no:cacheprovider tests/contract/cli/test_cli_reports.py -q` -> `11 passed`.

### T2 - Fix specs-dir persisted bind resolution

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/specs_resolver.py`, `dadaia_workspace/cli/commands/specs.py`, context release command/resolver surfaces, specs/context CLI tests, picked persisted-bind bug files
- **Acceptance:** Bare `dadaia specs doctor` resolves the persisted `dadaia-workspace` bind from workspace root without `DADAIA_CONTEXT`/`DADAIA_SESSION_ID` env; plain `dadaia context release` releases the persisted bound session after bind; legacy env, explicit `--session`, and explicit `--specs-dir` still work.
- **Validation:** `pytest -p no:cacheprovider tests/unit/core/test_specs_resolver.py tests/unit/cli/commands/test_context_release_cmd.py -q` -> `7 passed`.

### T3 - Repair SPEC-DOC-029 identity and scoped-state behavior

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/specs/doctor.py`, identity helper/protocol files if needed, SPEC-DOC-029 integration tests, picked SPEC-DOC-029 bug file
- **Acceptance:** Normal harness UUID/session-record id pairing does not produce false forgery; real incoherence still errors; temp `--specs-dir` runs do not read unrelated live locks.
- **Validation:** `pytest -p no:cacheprovider tests/integration/test_specs_doctor_coherence_backstop.py tests/integration/cli/test_cli_specs_doctor_coherence.py -q` -> `6 passed`.

### T4 - Harden root whitelist and repo hygiene

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/hooks/root_whitelist.py`, hook tests, hook/CLI bytecode suppression surfaces, `.gitignore`, repo-hygiene tests, picked root-whitelist/layer1-pycache/grill-gitignore bug files
- **Acceptance:** Nested forbidden root writes block; repo-local `__pycache__/` is not recreated by hooks/CLI; `GRILL.md` and `OQ-DECISIONS.md` are trackable in release root and segment dirs.
- **Validation:** `pytest -p no:cacheprovider tests/unit/hooks/test_root_whitelist.py tests/unit/infrastructure/test_runtime_config.py tests/contract/test_release_evidence_gitignore.py -q` -> `4 passed`.

### T5 - Make import-linter green and CI-enforced

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** lifecycle policy feature modules, panel workflow-policy view, backlog subject registry, `core/protocols/**`, `container.py`, `dadaia_workspace/cli/commands/ci.py`, `.github/workflows/**`, import-linter tests, picked import-linter bug file
- **Acceptance:** No feature imports infrastructure concrete stores; no feature reaches subprocess through CLI transitive imports; import-linter runs in local preflight and CI.
- **Validation:** `lint-imports` -> `Contracts: 6 kept, 0 broken`; `pytest -p no:cacheprovider tests/integration/cli/test_lifecycle_policy_cli.py tests/integration/panel/test_workflow_policy_routes_e2e.py tests/integration/test_cli_backlog_subjects.py tests/contract/cli/test_cli_ci.py -q` -> `38 passed`; `ruff check --no-cache <changed T5 files>` -> `All checks passed`.

### T6 - Remove stale Codex config and fix context-dead push

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/runtime_config.py`, public asset projection tests, `dadaia_workspace/features/spec_context/service.py`, context lifecycle git tests, picked Codex/context-dead bug files
- **Acceptance:** Generated Codex config contains no `approved_commands`; `context dead` handles mismatched local/upstream branch names deterministically.
- **Validation:** `pytest -p no:cacheprovider tests/integration/test_public_assets.py -q -k "codex_config"` -> `4 passed, 34 deselected`; `pytest -p no:cacheprovider tests/contract/cli/test_cli_context.py -q -k "push_uses"` -> `2 passed, 38 deselected`; `pytest -p no:cacheprovider tests/integration/test_dead_review_gate.py -q -k "different_upstream_name"` -> `1 passed, 6 deselected`; `ruff check --no-cache <changed T6 files>` -> `All checks passed`.

### T7 - Make memory heading lint consumer-extensible

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/public/scripts/lint-memory-atoms.py`, specs doctor memory-lint tests/fixtures, picked memory-heading bug file
- **Acceptance:** Consumer-specific H2 headings can be allowed without library source edits or are no longer warned unless they violate generic memory law; scaffolded memory has no permanent allowlist noise.
- **Validation:** `pytest -p no:cacheprovider tests/unit/scripts/test_lint_memory_atoms.py -q` -> `25 passed`; `python dadaia_workspace/public/scripts/lint-memory-atoms.py --memory-dir specs/memory` -> `30 OK, 0 WARN-only, 0 ERROR`; `dadaia specs doctor --specs-dir specs` -> `0 error(s), 16 warning(s)` (warnings are existing unrelated SPEC-DOC/TREE/backlog warnings); `ruff check --no-cache <changed T7 files>` -> `All checks passed`.

### T8 - Verify and close stale panel CSP bug

- **Status:** [x] DONE
- **Owner:** qa-engineer
- **Write set:** panel E2E tests or QA docs if guard is missing, picked panel CSP bug file
- **Acceptance:** Current panel has no mermaid CDN import, no CSP console errors, and correct ops subsection order; bug status is closed with validation evidence. If verification fails, add the missing guard before closing.
- **Validation:** `PANEL_TEST_PORT=3212 PANEL_WEB_SERVER_COMMAND="<venv>/python -m dadaia_workspace.cli.main panel --port 3212 --no-open" ./node_modules/.bin/playwright test panel/ops-tab.spec.ts panel/tab-navigation.spec.ts panel/response-guard.spec.ts panel/servers-tab.spec.ts -c panel/playwright.config.ts --reporter=list` -> `15 passed`.
