# TASKS: Release v0.1.73

**Status:** Aprovado
**Release ID:** v0.1.73
**Owner:** product-engineer

### T-1.1 — FR4 ReDoS linear scan `[-]`
- **Write set:** `dadaia_workspace/features/migrate/agent_tier_frontmatter.py`,
  `tests/unit/features/migrate/test_agent_tier_frontmatter.py`

```
[x] T-1.1
```

### T-2.1 — FR5 backup outside worktree `[ ]`
- **Write set:** `dadaia_workspace/features/migrate/upgrade.py`,
  `tests/unit/features/migrate/test_specs_evolution.py` (or new)

```
[x] T-2.1
```

### T-3.1 — FR6 REPO-DADAIA-1 doctor invariant `[ ]`
- **Write set:** `dadaia_workspace/features/specs/doctor*.py`,
  `tests/unit/features/specs/` (new test)

```
[x] T-3.1
```

### T-4.1 — FR3 blocking resolution evidence `[ ]`
- **Write set:** `dadaia_workspace/cli/commands/bugs.py`,
  `dadaia_workspace/public/schemas/` (bug-event evidence field),
  `tests/` (CLI test)

```
[x] T-4.1
```

### T-5.1 — FR1 single bugs.jsonl store + v3→4 consolidation `[ ]`
- **Write set:** `dadaia_workspace/infrastructure/jsonl_bug_store.py`,
  `dadaia_workspace/features/migrate/bugs_single_file.py`,
  `dadaia_workspace/features/migrate/registry.py`,
  `dadaia_workspace/core/specs_version.py`, doctor goldens,
  `tests/unit/features/migrate/test_bugs_single_file.py`,
  `tests/unit/infrastructure/` (store test)

```
[x] T-5.1
```

### T-6.1 — FR2 backlog timestamps + archive + candidates rebuild `[ ]`
- **Write set:** `specs/backlog/**` (renames, archive move, candidates.md)

```
[x] T-6.1
```

### T-7.1 — Self-application: run the v3→4 upgrade on THIS repo's specs/bugs `[ ]`
- **Write set:** `specs/bugs/**` (consolidated by the real CLI), `specs/constitution.md` (stamp)

```
[x] T-7.1
```
