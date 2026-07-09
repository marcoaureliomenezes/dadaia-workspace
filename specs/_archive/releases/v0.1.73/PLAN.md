# PLAN: Release v0.1.73

**Status:** Aprovado
**Release ID:** v0.1.73
**Owner:** product-engineer

| FR | Surface |
|----|---------|
| FR1 | `infrastructure/jsonl_bug_store.py` (single-file append), `features/migrate/bugs_single_file.py` (new, v3→4), `registry.py`, `core/specs_version.py` (=4), doctor golden regen |
| FR2 | `specs/backlog/*` git mv renames + `candidates.md` rebuild (mechanical, in-release) |
| FR3 | `cli/commands/bugs.py` (--resolution-evidence required for resolved), bug-event schema `evidence` optional field |
| FR4 | `features/migrate/agent_tier_frontmatter.py` linear scan |
| FR5 | `features/migrate/upgrade.py` backup path resolution |
| FR6 | `features/specs/doctor*` REPO-DADAIA-1 + fix |

Pinned substrate: none. Tests: unit RED-first per FR; migration driven via the REAL CLI on
a copy of this repo's actual 52-file specs/bugs; mutation-sanity; full suite.
