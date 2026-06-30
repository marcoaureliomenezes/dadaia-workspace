---
name: grill-and-oq-decisions-records-gitignored-not-version-controlled
status: Closed
severity: MEDIUM
reported: 2026-06-27
surface: .gitignore (specs/releases/*/* allowlist), release-governance grill gate
session_id: null
---

**Symptom:** A release's **mandatory** `GRILL.md` (and `OQ-DECISIONS.md`) is silently NOT
version-controlled. `.gitignore` ignores `specs/releases/*/*` (line 117) and then
re-includes ONLY `SPEC.md`, `PLAN.md`, `TASKS.md`, `CLOSURE.md` (lines 118-121) — `GRILL.md`
and `OQ-DECISIONS.md` are omitted from the allowlist, so `git add specs/releases/<id>/`
stages SPEC/PLAN/TASKS but quietly drops the grill record. The same omission exists for the
`alpha-*/` and `rc-*/` segment allowlists (lines 123-134).

**Repro:**
```
dadaia release new v0.1.31
# author SPEC.md, PLAN.md, TASKS.md, GRILL.md under specs/releases/v0.1.31/
git add specs/releases/v0.1.31/
git status --short            # SPEC/PLAN/TASKS staged; GRILL.md absent
git check-ignore -v specs/releases/v0.1.31/GRILL.md
#   .gitignore:117:/specs/releases/*/*   specs/releases/v0.1.31/GRILL.md
```

**Expected:** The grill is a **required gate** per the `release-governance` rule ("Grill is
mandatory … a `dadaia-grill-me` session on the picked set is required **before** the SPEC is
written"). Its record is governance evidence on par with SPEC/PLAN/TASKS and must be tracked
from DEFINITION, not lost. `GRILL.md` (and `OQ-DECISIONS.md`) should be in the gitignore
re-include allowlist alongside SPEC/PLAN/TASKS/CLOSURE, for the release root and the
`alpha-*/` / `rc-*/` segments.

**Impact (observed):** v0.1.30 lost its `GRILL.md` and `OQ-DECISIONS.md` from version control
until they were `git add -f`'d at archive time (see memory `project_v0130_super_release`
GOTCHAS). A grill record that exists only on a working-tree disk can be lost on a fresh
clone, a `git clean`, or a branch switch — defeating the mandatory-grill governance gate.

**Fix direction:** add `!/specs/releases/*/GRILL.md`, `!/specs/releases/*/OQ-DECISIONS.md`
(and the `alpha-*/` / `rc-*/` equivalents) to `.gitignore`. Consider whether the
release-scaffolding / doctor surface should warn when a release dir lacks a tracked
`GRILL.md` in DEFINITION+.

**Notes:** No secrets/operator-local paths. Worked around for v0.1.31 by `git add -f
specs/releases/v0.1.31/GRILL.md` so this release's grill is tracked from DEFINITION.
