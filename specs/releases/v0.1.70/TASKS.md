# TASKS — Release v0.1.70 — Contract & Repo-Hygiene Drift

> **Status:** Aprovado
> **Release ID:** v0.1.70
> **Owner:** product-engineer

Marker contract: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. RED-first: commit the
failing proof, confirm it fails on current code, THEN implement the fix.

---

## Wave A — FR1: agent_tier doc↔schema truth

### T-70-01 — RED: doc-consistency test (docs lie about the schema) `[x]`
- **Owner:** software-engineer
- **Write set:** `tests/unit/scripts/test_memory_agents_doc_schema_consistency.py` (new)
- **Task:** Executed-path test over the real files covering **all four surfaces**
  (architect F1): assert "schema tolerates it" does NOT appear in
  `public/scaffold/memory/AGENTS.md`, `public/data/memory-AGENTS.md`,
  `specs/memory/AGENTS.md`; assert "retains a deprecated optional `agent_tier`" does NOT
  appear in `specs/memory/architecture.md`; and assert each states `agent_tier` is
  rejected/removed. CONFIRM RED (all four lie today).
- **AC:** SPEC AC1(repro) RED half, AC1.1.

### T-70-02 — GREEN: correct the four agent_tier surfaces + re-project `[x]`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/public/scaffold/memory/AGENTS.md`,
  `dadaia_workspace/public/data/memory-AGENTS.md`,
  `specs/memory/AGENTS.md`, `specs/memory/architecture.md`
- **Preconditions:** T-70-01 `[x]`
- **Task:** Rewrite the false "schema tolerates it / retains … agent_tier" claim in all
  four surfaces to state `agent_tier` was removed in v0.1.61 and is rejected by the
  schema (`additionalProperties: false`) — authors must not include it. Then re-project:
  `dadaia public stage && dadaia public install --target all && dadaia public doctor`
  (must exit 0 with `[ok] public-privacy`). Do NOT touch the schema. Do NOT hand-edit
  projected instance files at the workspace root. Re-run T-70-01 → GREEN; confirm
  `test_agent_tier_property_absent_from_schema` still green. (The `specs/memory/*` edits
  are MEMORY-class — permitted in this DEFINITION/CLOSURE window.)
- **AC:** SPEC AC1.1, AC1.2, AC1.3, AC1(repro) GREEN half.

## Wave B — FR2: gitignore intake

### T-70-03 — RED: remote-bugs intake is git-ignored `[x]`
- **Owner:** software-engineer
- **Write set:** `tests/integration/test_governance_intake_not_gitignored.py` (new)
- **Task:** Executed-path repo-hygiene test: write a probe `*.md` under
  `specs/backlog/remote-bugs/` (and `_archive/`) in the repo and assert `git
  check-ignore` returns non-zero (not ignored) — plus the same for `specs/bugs/` and
  `specs/backlog/` as controls. CONFIRM RED for the `remote-bugs/` probe today.
- **AC:** SPEC AC2(repro) RED half.

### T-70-04 — GREEN: add remote-bugs negation to .gitignore `[-]`
- **Owner:** software-engineer
- **Write set:** `.gitignore`
- **Preconditions:** T-70-03 `[x]`
- **Task:** After the `specs/backlog/_archive` block, add the `remote-bugs/` subtree
  negation (re-declare dir, re-exclude contents, opt `*.md` back in for the subtree and
  its `_archive/`), mirroring the existing idiom. Re-run T-70-03 → GREEN. Confirm no
  over-un-ignoring (non-`.md` intake artifacts stay ignored).
- **AC:** SPEC AC2.1, AC2(repro) GREEN half.

## Wave C — FR3: validation

### T-70-05 — QA validation + gate green `[ ]`
- **Owner:** qa-engineer
- **Write set:** none (ADDITIVE handoff only)
- **Preconditions:** T-70-02, T-70-04 `[x]`
- **Task:** Full `pytest -p no:cacheprovider`, ruff format+check, `mypy --strict`,
  `lint-imports` (9), `dadaia public doctor` (exit 0, `[ok] public-privacy`). Confirm no
  pre-existing test weakened (schema-absent pin + digest-strip tests green). Mutation-
  sanity on the FR1 doc-consistency + FR2 hygiene tests. Emit QA handoff.
- **AC:** SPEC AC-FR3.1, FR3.2.
