# SPEC: ctx-inject-v2-drift-fix-v1

**Status:** Aprovado
**Release ID:** ctx-inject-v2-drift-fix-v1
**Owner:** product-engineer
**Created:** 2026-06-02

---

## 1. Objective

Fix two confirmed regressions and one usability defect in the `UserPromptSubmit` hook
(`public/scripts/ctx-inject.sh`) and one correlated stale verb in
`public/skills/dadaia-workspace-manager/SKILL.md`, both introduced when the context model
migrated from v1 (`context use`) to v2 (`context bind`).

The hook is lib-originated (tracked by `manifest.json`). All edits go to the `public/`
source; propagation to `.dadaia/scripts/`, `.dadaia/agentic/scripts/`, and all agent
runtime projections is mandatory and is part of this release.

---

## 2. Product deltas

### BUG 1 — Stale CLI verb in hook (confirmed regression)

**File:** `public/scripts/ctx-inject.sh`, lines 26 and 32.

Both `[context: none]` branches emit:

```
[context: none] — run: eval $(dadaia context use <name>)
```

`dadaia context use` was removed in v2. Running it produces a hard error
(`'use' was removed in v2`, `context.py:623`). The correct v2 verb is
`dadaia context bind <name> --mode read`.

**Fix:** replace both occurrences of `context use <name>` with
`context bind <name> --mode read`.

### BUG 2 — Dead detection branch (message-only fix, operator-locked scope)

**File:** `public/scripts/ctx-inject.sh`, lines 9 and 23–33 (`STATE_FILE` var +
`elif [ -f "$STATE_FILE" ]` block).

In v2, `primary_context.json` has no writer (`context.py:622` `[REMOVED]` for `promote`);
the file is absent on disk. The `elif` branch can never fire. v2 read-mode `bind` exports
`DADAIA_CONTEXT` into the launching shell but writes no state file. Detection is possible
only via `$DADAIA_CONTEXT`.

**Operator-locked scope (message-only, NO CLI changes, NO new resolver):**
- Remove the dead `elif [ -f "$STATE_FILE" ] ... fi` block including the now-unused
  `STATE_FILE` variable at line 9.
- Rewrite the `[context: none]` message (consolidated after BUG 1 fix) to give correct,
  actionable v2 guidance: bind a context AND export `DADAIA_CONTEXT` in the launching
  shell. No new resolver logic.

### BUG 3 — `dadaia` not on PATH (folded into BUG 2 message)

The hook itself works (uses `python3`). The guidance tells users to run `dadaia …` but
the binary lives at `.dadaia/.venv/bin/dadaia`. Fold a PATH-aware hint into the rewritten
`[context: none]` message (e.g. reference activating `.dadaia/.venv` or the binary path).
No separate task.

### BUG 4 — Stale CLI verb in SKILL.md

**File:** `public/skills/dadaia-workspace-manager/SKILL.md`, line 74.

```
dadaia context use <name>    # eval $(dadaia context use <name>) — session isolation
```

The `use` verb is removed in v2. Replace with the correct v2 form:

```
eval $(dadaia context bind <name> --mode read)   # export DADAIA_CONTEXT into launching shell
```

---

## 3. Architecture deltas

None. No new modules, no new layers, no schema changes. This is a pure content fix in two
lib-originated asset files.

---

## 4. Tech-stack deltas

None. No new dependencies.

---

## 5. Security / operations deltas

None.

---

## 6. Memory files affected at closure

- `specs/memory/tech-stack.md` — no change expected (ctx-inject mechanism unchanged).
- Feature atom `specs/memory/product/ctx-inject.md` (or equivalent) — update if exists
  and references the old verb. Inspect at CLOSURE; update only if stale guidance is present.

---

## 7. Acceptance criteria

| AC | Description |
|----|-------------|
| AC-1 | `public/scripts/ctx-inject.sh` contains no occurrence of `context use` |
| AC-2 | `public/scripts/ctx-inject.sh` contains no `STATE_FILE` variable and no `elif [ -f "$STATE_FILE"` block |
| AC-3 | The `[context: none]` message in `public/scripts/ctx-inject.sh` references `context bind <name> --mode read` and includes a hint about the `.dadaia/.venv` PATH |
| AC-4 | `public/skills/dadaia-workspace-manager/SKILL.md` line in the CLI reference table references `context bind` instead of `context use` |
| AC-5 | `dadaia public stage && dadaia public install --target all` completes without error |
| AC-6 | `dadaia public doctor` exits 0 after propagation |
| AC-7 | Projection `.dadaia/scripts/ctx-inject.sh` matches source (no `context use`, no `STATE_FILE`) |
| AC-8 | `ruff check . && ruff format . && mypy dadaia_workspace` pass (no regressions from Bash-only changes — verify Python pipeline is unaffected) |
| AC-9 | `pytest` passes with no regressions (no Python was changed; confirm test count unchanged) |

---

## 8. Out of scope

- Any new context resolver logic (e.g. reading `spec_contexts.json` directly, new env var)
- CLI changes to `context.py`
- Changes to the SDD gate (`sdd-spec-gate.sh`)
- New tests for the Bash hook (no test harness exists for Bash; manual verification in AC-7 suffices)
- Memory atom edits for any feature not impacted by stale verb

---

## 9. Dependencies and risks

**Dependencies:** None. This release has no hard prerequisite on any other active or queued
release. It can run immediately from `release: none`.

**Risks:**

| Risk | Mitigation |
|------|-----------|
| Public doctor drift visible between T-CIV-01/T-CIV-02 (source edit) and T-CIV-03 (propagation) | Expected and documented; devops-engineer runs stage+install as T-CIV-03 |
| Bash hook test gap | No automated test harness for `.sh` hooks; AC-7 manual spot-check by qa-engineer |
| `context bind` not available in some consumers | `context bind` shipped in v2 (`spec-context-session-locks-v1`); this workspace runs v2+ |
