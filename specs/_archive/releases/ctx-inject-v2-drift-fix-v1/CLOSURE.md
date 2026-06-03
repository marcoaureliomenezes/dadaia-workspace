# Closure: Release — ctx-inject-v2-drift-fix-v1

> **Status:** Aprovado
> **Release ID:** ctx-inject-v2-drift-fix-v1
> **Owner:** product-engineer
> **Closed:** 2026-06-02

## Summary

This release delivered a content-only fix to two lib-originated `public/` assets that had
retained stale v1 CLI verbs after the context model migrated to v2 in
`spec-context-session-locks-v1`. The `context use` verb was removed in v2; both assets
continued referencing it, producing a hard error when operators followed the guidance.

In `public/scripts/ctx-inject.sh` the dead `primary_context.json` detection branch
(`STATE_FILE` variable + `elif [ -f "$STATE_FILE" ]` block) was removed — that file has
no writer in v2 — and the `[context: none]` message was rewritten to reference the correct
v2 verb (`context bind <name> --mode read`) and to include a `.dadaia/.venv/bin/dadaia`
PATH hint so operators can run the command without having to activate the venv manually.

In `public/skills/dadaia-workspace-manager/SKILL.md` the stale `dadaia context use <name>`
entry in the CLI reference table was replaced with the correct v2 form.

Both edited files were propagated to all agent runtime projections via the mandatory
`dadaia public stage && dadaia public install --target all` chain, and `dadaia public
doctor` confirmed exit 0 (SKILL.md required `--force` to clear a stale-projection drift;
devops-engineer was authorized). A set of 4 integration tests that had been asserting the
now-deleted `primary_context.json` detection branch were reconciled to use `DADAIA_CONTEXT`
env-var injection, restoring the full suite to green. QA approved all 9 acceptance criteria.

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-CIV-01 | Fix ctx-inject.sh: remove dead STATE_FILE branch + rewrite v2 [context: none] message | `ab960ae` |
| T-CIV-02 | Fix SKILL.md: replace stale `context use` with `context bind` | `2c25c55` |
| T-CIV-03 | Propagate: `dadaia public stage + install + doctor` exit 0 (--force for SKILL.md drift) | `96d1f86` / `b853d0a` |
| T-CIV-05 | Reconcile 4 stale integration tests in `tests/integration/test_hooks.py` | `34d9af1` |
| T-CIV-04 | QA gate: AC-1..AC-9 all pass; handoff report emitted | `69f6eb6` |

---

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| No `context use` in source script | `grep "context use" dadaia_workspace/public/scripts/ctx-inject.sh` | Empty output (AC-1) |
| No `STATE_FILE` in source script | `grep "STATE_FILE" dadaia_workspace/public/scripts/ctx-inject.sh` | Empty output (AC-2) |
| Correct v2 verb + PATH hint in source script | `grep "context bind" dadaia_workspace/public/scripts/ctx-inject.sh` | Line with `context bind <name> --mode read` and `.dadaia/.venv` hint (AC-3) |
| Correct v2 verb in SKILL.md | `grep "context bind" dadaia_workspace/public/skills/dadaia-workspace-manager/SKILL.md` | Line with `eval $(.dadaia/.venv/bin/dadaia context bind <name> --mode read)` (AC-4) |
| Propagation succeeded | `.dadaia/.venv/bin/dadaia public stage && dadaia public install --target all` | Exit 0 (T-CIV-03; `96d1f86` / `b853d0a`) |
| Public doctor clean | `.dadaia/.venv/bin/dadaia public doctor` | Exit 0; all assets `[ok]` (AC-6) |
| Projection matches source | `grep "context use" .dadaia/scripts/ctx-inject.sh; grep "STATE_FILE" .dadaia/scripts/ctx-inject.sh` | Both empty; `grep "context bind"` returns new guidance line (AC-7) |
| Lint + type check clean | `ruff check . && ruff format --check . && mypy dadaia_workspace` | Exit 0; 161 files (AC-8) |
| Full test suite green | `pytest --tb=short -q` | 2399 passed / 0 failed / 2 skipped / 1 xpassed, 88.71% coverage (AC-9) |
| QA handoff APPROVED | QA report | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-06-02T120000Z-ctx-inject-v2-drift-fix-v1-qa.handoff.json` |

---

## Drifts

### t-civ-05-added-in-flight

**Description:** T-CIV-04 (QA gate) failed AC-9 on first run because removing the
`primary_context.json` detection branch in T-CIV-01 broke 4 integration tests in
`tests/integration/test_hooks.py` that asserted the deleted branch. These tests used a
`primary_context.json` fixture to exercise the now-deleted `elif` path.

**Resolution:** T-CIV-05 was scoped and added in-flight as an in-scope remediation task.
The 4 tests were rewritten to use `DADAIA_CONTEXT` env-var injection, mirroring the
existing passing test `test_ctx_inject_honors_dadaia_context_env`. T-CIV-04 was reset
to `[ ]` OPEN and re-run after T-CIV-05 completed, passing all 9 ACs on the second run.
The execution order in TASKS.md was updated to reflect the amended sequence:
`T-CIV-01 → T-CIV-02 → T-CIV-03 → T-CIV-05 → T-CIV-04`.

**Memory updates:** None. The drift affected the test suite only; no memory atom describes
integration test fixture patterns.

### skill-md-stale-projection-drift

**Description:** After T-CIV-03 ran `dadaia public install --target all`, `dadaia public
doctor` still reported `[drift]` for the SKILL.md projection. The staged SHA did not
match the projection.

**Resolution:** devops-engineer re-ran `dadaia public install --force --target all`
(authorized per TASKS.md T-CIV-03 instructions). Doctor then reported exit 0 for all
assets. This is a known behavior when a file projection had been independently modified
outside the standard pipeline; `--force` is the documented repair path.

**Memory updates:** None. `public-asset-distribution.md` already documents `--force` as
the drift-repair path.

---

## Memory updates

- `specs/memory/product/context-management.md` — **no change**. The atom already
  correctly documents v2: `primary_context.json` is explicitly marked "Removido em v2"
  and the ctx-inject hook description references the `eval $(dadaia context bind ...)`
  binding pattern. The bugs were in `public/` Bash source and a SKILL.md, neither of
  which is a memory atom.
- `specs/memory/tech-stack.md` — **no change**. The atom does not reference `context use`
  or `primary_context.json` detection logic. No stale content present.
- `specs/memory/product/index.md` (catalog) — **no change**. No feature added, removed,
  or reordered; catalog order unchanged.
- All other memory atoms — **no change**. Release scope was limited to two `public/`
  content files and their test reconciliation; no memory atom described the affected
  behavior incorrectly.

---

## Backlog returns

The QA engineer flagged one ergonomic improvement that was explicitly assessed as
acceptable per approved SPEC AC-3 (not a defect) and deferred:

- `specs/backlog/candidates.md` ← **ctx-inject-path-aware-message-v1** — PATH-aware
  variant of the `[context: none]` message in `ctx-inject.sh`: detect at runtime whether
  `dadaia` is on PATH (via `command -v dadaia`) before emitting the full
  `.dadaia/.venv/bin/dadaia` path hint; emit the short form `dadaia context bind ...`
  when the binary is already on PATH, and the full-path form otherwise. QA assessed the
  hardcoded `.dadaia/.venv` path as acceptable for this release (AC-3 satisfied); the
  improvement is ergonomic, not a correctness defect.

---

## Archive decision

**MOVE** — release directory to be moved to `specs/_archive/releases/ctx-inject-v2-drift-fix-v1/`
via `git mv`. ACTIVE.md will be updated to `release: none / phase: none` after move.
