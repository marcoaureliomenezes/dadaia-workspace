# TASKS: v0.1.4.3 - handoff-directory-contract

**Status:** Aprovado
**Release ID:** v0.1.4.3
**Owner:** product-engineer
**Created:** 2026-06-04

---

## Execution Order

Maximum one `[-]` at a time unless this file is amended with explicit disjoint
write sets.

```text
T-HANDOFF-01 -> T-HANDOFF-02 -> T-HANDOFF-03 -> T-HANDOFF-04
```

---

## Tasks

### T-HANDOFF-01 - Add canonical handoff scoped rule projection

- **Status:** [-]
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/public/data/**`, `dadaia_workspace/infrastructure/public_assets.py`, public asset tests

Add the `.dadaia/handoff/AGENTS.md` source and ensure public staging,
installation, and doctor treat it as a managed scoped rule.

### T-HANDOFF-02 - Move handoff instructions out of reports adjacency

- **Status:** [ ]
- **Owner:** product-engineer + software-engineer-python
- **Target files:** `dadaia_workspace/public/**`, `AGENTS.md`, tests that assert public instructions

Update public root/scoped rules, handoff emitter skill, orchestration
instructions, and agent write contracts so handoff JSON is emitted under
`.dadaia/handoff/<context>/` instead of beside reports.

### T-HANDOFF-03 - Update reports validation discovery and hash resolution

- **Status:** [ ]
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/features/reports_validation/**`, `dadaia_workspace/cli/commands/reports.py`, `scripts/check-verdict.sh`, reports validation tests

Make `--all` default to `.dadaia/handoff/`, keep explicit paths supported, and
resolve workspace-relative artifact paths correctly for hash checks.

### T-HANDOFF-04 - Verify handoff contract end to end

- **Status:** [ ]
- **Owner:** qa-engineer + code-reviewer + security-reviewer
- **Target files:** `tests/**`, `.github/workflows/ci.yml` if needed

Add or update focused tests for the new directory contract. Run verification
for public assets, schema/model validation, CLI validation, and hash validation.
