# PLAN: v0.1.41 - Open bug root-cause sweep

**Status:** Aprovado
**Release ID:** v0.1.41
**Owner:** product-engineer
**Created:** 2026-06-29

## Strategy

Fix root causes by subsystem, not one bug at a time. The release is deliberately broad but
bounded to open `dadaia-workspace` bug records and their directly implicated tests.

## Workstreams

### WS1 - Reports contract cleanup

Files:

- `dadaia_workspace/cli/commands/reports.py`
- `dadaia_workspace/features/reports_validation/**`
- `dadaia_workspace/public/data/AGENTS.md`
- `dadaia_workspace/public/data/handoff-AGENTS.md`
- `dadaia_workspace/public/skills/dadaia-handoff-emitter/SKILL.md`
- report-validation CLI tests

Approach:

1. Decide the narrowest contract: handoff JSON validation is canonical; HTML report integrity
   is validated through the handoff `artifact.path` + `content_hash`.
2. Add file-type detection so HTML input receives an explicit actionable message.
3. Update projected instructions to say "validate the handoff JSON", not "validate the HTML".
4. Close both report-validation duplicate bugs from the same evidence.

### WS2 - Specs resolver and SPEC-DOC-029

Files:

- `dadaia_workspace/core/specs_resolver.py`
- `dadaia_workspace/cli/commands/specs.py`
- `dadaia_workspace/features/specs/doctor.py`
- `dadaia_workspace/features/spec_context/session_identity.py` if a reusable identity reader is needed
- integration tests for bind resolution and coherence backstop

Approach:

1. Extend specs-dir resolution to read the persisted bind pointer/session state without
   requiring env exports.
2. Update error text to describe bind persistence accurately.
3. Make SPEC-DOC-029 compare resolved identities in a single namespace.
4. Keep scoped `--specs-dir` doctor runs isolated from unrelated live workspace locks.

### WS3 - Guardrail and repo hygiene hardening

Files:

- `dadaia_workspace/hooks/root_whitelist.py`
- hook/root-whitelist tests
- hook/CLI launch paths that need bytecode suppression
- `.gitignore`
- repo-hygiene tests

Approach:

1. Change root whitelist detection from immediate-parent check to first-root-component check.
2. Add nested forbidden-root regression tests.
3. Ensure hook/CLI Python execution cannot write bytecode into repo source trees.
4. Re-include `GRILL.md` and `OQ-DECISIONS.md` in release root and segment gitignore allowlists.

### WS4 - Architecture contract enforcement

Files:

- `dadaia_workspace/features/lifecycle/policy_doctor.py`
- `dadaia_workspace/features/lifecycle/policy_resolver.py`
- `dadaia_workspace/features/panel/views/workflow_policy.py`
- `dadaia_workspace/features/backlog/subject_registry.py`
- `dadaia_workspace/core/protocols/**`
- `dadaia_workspace/container.py`
- `dadaia_workspace/cli/commands/ci.py`
- `.github/workflows/**`
- import-linter contract tests

Approach:

1. Introduce or reuse a core protocol for workflow-model policy store access.
2. Route features through ports injected from the container instead of importing JSON store
   implementations.
3. Break the `subject_registry -> cli.main -> infrastructure -> subprocess` transitive edge.
4. Add import-linter to local preflight and CI.

### WS5 - Runtime/config correctness

Files:

- `dadaia_workspace/infrastructure/runtime_config.py`
- Codex projection tests
- `dadaia_workspace/features/spec_context/service.py`
- git/context lifecycle tests

Approach:

1. Remove `approved_commands` from generated Codex config.
2. Add a contract test for absent invalid Codex keys.
3. Replace plain `git push` in `context dead` with explicit upstream push or already-contained
   detection.

### WS6 - Memory lint extensibility

Files:

- `dadaia_workspace/public/scripts/lint-memory-atoms.py`
- specs doctor integration around memory lint
- scaffold memory fixtures

Approach:

1. Prefer a workspace-owned extension file under `specs/memory/` for local headings.
2. Keep forbidden-history/changelog checks generic and fail-loud.
3. Add consumer-style fixture coverage so domain headings do not produce permanent warnings.

### WS7 - Panel stale bug verification

Files:

- `dadaia_workspace/features/panel/views/index.py`
- `tests/e2e/panel/**`
- `dadaia_workspace/cli/commands/ci.py` or QA docs if preflight cannot run Playwright reliably
- panel bug record

Approach:

1. Verify no inline CDN mermaid hydration remains.
2. Verify ops-tab order and CSP E2E expectations.
3. Close the stale bug with evidence, or add the missing guard if verification fails.

## Validation

Required before closure:

- `dadaia specs doctor --specs-dir specs`
- `dadaia specs doctor` from workspace root after `dadaia context bind dadaia-workspace`
- `lint-imports`
- `dadaia ci preflight`
- focused pytest suites for reports, specs resolver/coherence, root whitelist, repo hygiene,
  public assets/Codex config, context lifecycle, and memory lint
- panel E2E slice if Playwright dependencies are available locally

## Risk

The largest risk is touching shared resolution code (`core/specs_resolver.py`) and specs doctor
state wiring. Keep compatibility tests for explicit `--specs-dir`, env-based bind, and persisted
bind so the fix does not regress older operator flows.
