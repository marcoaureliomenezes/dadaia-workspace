---
slug: workspace-doctor
title: workspace-doctor
tldr: dadaia doctor is the one compliance check — workspace, specs and ledgers sections, one line per finding, exit 1 with a fix line; --fix moves slop, TTL deletes.
summary: dadaia doctor runs three sections (workspace walk, specs rules, ledger checks) from one rule record, prints each non-canonical finding as one line with a runnable fix, exits 1 on any error-class finding and reports no score; --fix is the reaper, moving slop into a held zone and deleting only what a TTL expired.
tags: [workspace, doctor, health, repair, zones, specs, ledgers, compliance, privacy]
sources:
  - dadaia_workspace/cli/commands/doctor.py
  - dadaia_workspace/core/doctor_rules.py
  - dadaia_workspace/core/workspace_layout.py
  - dadaia_workspace/features/specs/**
  - dadaia_workspace/features/spec_context/doctor.py
  - dadaia_workspace/features/spec_context/sweep.py
  - dadaia_workspace/features/backlog/doctor.py
  - dadaia_workspace/infrastructure/ledger_scripts.py
  - dadaia_workspace/features/reconcile/**
  - dadaia_workspace/cli/commands/reconcile.py
---

## The command

- `dadaia doctor` is the one instance validator; `dadaia public doctor` (library vs projection) is the only other doctor and touches no instance file ([[public-asset-distribution]]).
- Three sections run in fixed order: `workspace` (root, harness dirs, `.dadaia/` zones, ALIVE repo trees, installed git hook), `specs` (the rules over one `specs/` tree), `ledgers` (the backlog document, the ADR ledger and the skill-script ledgers).
- One rule record, `dadaia_workspace/core/doctor_rules.py` (`Rule`: codes, section, run, fix, fix_help); `dadaia_workspace/cli/commands/doctor.py` is the only place the sections meet. A run is its findings and its exit code — there is no score.
- A printed finding is one line `<CODE> <verdict> <message>`: `canon|operator|reaped|slop|expired|missing` for the walk, `error|warning|info` for `specs` and `ledgers`; canonical entries are not printed.
- Every error-class finding carries one `fix: <command>` line; exit 1 on any error-class finding in any section.
- `--json` emits `{"specs_dir", "sections": {<name>: {"findings": [...]}}, "fixed"}`; `--quiet` prints only what `--fix` did; `--redact` masks every foreign context name and repo slug ([[context-management]]).
- The `specs`/`ledgers` tree resolves from `--context <name>`, `--specs-dir <path>`, else the bound context; with none, those sections are empty and `workspace` still runs. With no instance around (CI over a checkout) `workspace` is empty and an explicit tree still gets its two sections. `--public-dir` enables template drift checks; `--source-root`/`--alias-map` feed the backlog anchor derivation.
- The CI job runs `dadaia doctor --specs-dir specs --source-root .` over the checked-out tree ([[QUALITY]]).

## The `workspace` section

- The walk covers the root, `.agents` plus each registered harness's projection directory, the `.dadaia/` top level, the top of every ALIVE repo (main plus associated), the closed-canon zones and the TTL zones; `references/` and `.venv/` are never walked and a symlink is never followed.
- Every filesystem act of the walk and the reaper goes through `dadaia_workspace/features/spec_context/sweep.py`: a vanished entry is absent, a location outside the workspace is skipped, an `OSError` is one `skipped` action.
- Verdicts: `canon`, `operator` (matches an instance exception), `slop`, `expired` (older than the zone's TTL), `missing` (an init/install zone or the harness profile absent), `reaped` (held in `reaped/`, listed with days left).
- Canon per level is a view of `dadaia_workspace/core/workspace_layout.py`: the root law's entries, the install ledger's harness entries, the zone names, `STATES_CANON` for `states/`, `spec-contexts.json` for `dist/`, `*.json` for `sessions/`.
- A repo tree: only a `REPO_TREE_EXCLUDED` name (`.dadaia` and tool caches) is a finding (`WS-repos-slop`); `.git`, `.venv` and `node_modules` end the descent, so source is never judged.
- Instance exceptions live in `.dadaia/states/instance_exceptions.txt`, one glob per line; the root-whitelist hook reads the same file ([[sdd-gate-v3]]).
- Codes are `WS-<zone>-<verdict>`. Context invariants ride the same section, error-class: `INV-4`/`INV-5`/`CTX-URL-1` (ALIVE/DEAD repo and URL coherence), `INV-6` (a repo slug owned by two contexts, report-only), `VENV-1` (venv entrypoint health, never auto-fixed).
- `HOOKS-DRIFT-1`: an ALIVE repo's installed `.git/hooks/pre-push` differing from the shipped `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`, `fix: dadaia ci install-hook --force`; a checkout without `.git/hooks/` is never a finding.
- `--expired-only` scopes the report to expired entries and keeps the specs repairs off `--fix`; it never narrows the reaper.

## The `specs` section

- `RULES` in `dadaia_workspace/features/specs/rules.py` is the one ordered registry of check order, fix dispatch and the `--fix` help text; each run parses the tree once.
- Tree: `TREE-*` checks the canon rows of `SPECS_CANON`; `TREE-5` compares every scaffolded law file against its source and `shipped-hashes.json` — a shipped version is refreshed by `--fix`, an edited one is reported and never overwritten.
- Release: `SPEC-DOC-003/009` (live release resolvable), `SPEC-DOC-004` (trio `**Status:**` token), `SPEC-DOC-005` (PLAN length, warning), `SPEC-DOC-024` (phase vs task markers), `SPEC-DOC-026/027` (ids and naming), `SPEC-DOC-046` (legacy state filename, renamed by `--fix`), `SPEC-DOC-047` (a task whose write set names `specs/memory`), `SPEC-DOC-048` (a SPEC without `**Origin:**`).
- `RELEASE-TREE-*` validates `_RELEASE.json` (`STATE-MISSING`, `SCHEMA`, `PARSE`, `TS-ORDER`, `PHASE`, `ARCHIVED`, `TRIO`); `RELEASE-TREE-MEMORY` keeps a CLOSURE release red until its memory reconciliation entry exists ([[release-lifecycle]]).
- Memory: `SPEC-DOC-002/002L/008/010`, `MEM-PLACEHOLDER-1` (removed by `--fix`), `AGENTS-PLACEHOLDER-1`, `CAT-1` (catalog equals atom files), `LINT-1` (frontmatter, headings, wikilinks, `sources` globs, `MEM-NARRATIVE-1` history lines), `MEM-DRIFT-1` (features package map vs the live tree), `MEM-DRIFT-2` (warning: a cited `dadaia` verb or repo path that does not exist), `ADR-SUPERSEDED-CITATION`, `FIXED-1/2` (fixed law sections, refreshed by `--fix`).
- Governance and coherence: `SPEC-DOC-033/041` (bug ledger), `SPEC-DOC-035` (loose backlog files), `SPEC-DOC-030/036/038` (audit shape and state), `SPEC-DOC-034` (missing `_archive/`, created by `--fix`), `SPEC-DOC-007` (orphans), `SPEC-DOC-001/028/037`, `SPECS-VERSION` (warning below the canonical pattern version, see [[specs-migration]]).

## The `ledgers` section

- `BL-SCHEMA`, `BL-CONFLICT`, `BL-STALE` over `BACKLOG.json` (`dadaia_workspace/features/backlog/doctor.py`); `LEDGER-ADR-SCHEMA` over `decisions.jsonl`.
- Each ledger script (`bugs.py`, `backlog.py`, `release.py`, `audit.py`, `memory.py`) runs its own `check --specs <dir> --json`; each line re-emits as `LEDGER-<NAME>-SCHEMA` with a `fix:` naming the script. A script that cannot run is a finding whose fix is `dadaia public install`. The doctor keeps no ledger schema of its own and repairs no ledger.

## The reaper

- `--fix` runs one lane: marker GC, stale session records, the `root_exceptions.txt` to `instance_exceptions.txt` move, seed missing zones and the harness profile, move every `slop` entry, move a DEAD context's leftover repo (`INV-5`), delete expired; then, unless `--expired-only`, the specs fixes (`MEM-PLACEHOLDER-1`, `TREE-4`, `TREE-5`, `TREE-8`, `FIXED-1/2`, `SPEC-DOC-034`, `SPEC-DOC-046`).
- Nothing is deleted directly: slop moves to `.dadaia/reaped/<YYYYMMDD>/<workspace-relative-path>` (7-day TTL from the move); deletion happens only when a TTL zone's entry expires.
- The lane runs at SessionStart (`dadaia doctor --fix --expired-only --quiet` from each harness's runtime config) and on the PostToolUse hook's throttle; it judges by registry, never by liveness.
- A fix invents no approval, completion, evidence or disposition, and every step reports what it did or skipped.
- Never touched: `references/`, `.venv/`, repo source, install-ledger entries, `agentic/` and `hooks/` contents (drift belongs to `public doctor`), a zone's `AGENTS.md`, exception matches, unexpired files.

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[workspace-init]], [[public-asset-distribution]], [[release-lifecycle]], [[audits-canon]].
