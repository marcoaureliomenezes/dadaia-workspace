# SPEC: Release v0.1.73 — Governance hygiene

**Status:** Aprovado
**Release ID:** v0.1.73
**Owner:** product-engineer

## Context
Operator contract violations + all 4 open ledger bugs. The bug store fragmented into 52
hourly JSONL files where the operator specified ONE append-only file; the backlog carries
no age signal; the recurrence audit's resolution law needs its blocking form.

## FRs
- **FR1 (HIGH, `bugs-store-fragments-into-hourly-files`)** — `JsonlBugStore` appends to the
  single canonical `specs/bugs/bugs.jsonl` (no hour bucketing). Readers keep consuming every
  `*.jsonl` (back-compat). New `specs upgrade` step `bugs-single-file` (v3→4): concatenate
  all legacy `<hour>Z-<n>.jsonl` files in chronological order into `bugs.jsonl` and remove
  them; collapse `specs/bugs/_archive/*.md` into ONE `_archive/archive.jsonl` (one JSON
  object per legacy bug: slug + frontmatter + full markdown body — content preserved, then
  the `.md` sources removed). Idempotent, dry-run capable.
  AC: after upgrade, `specs/bugs/` contains exactly `bugs.jsonl` (+ `_archive/archive.jsonl`,
  README/.gitkeep); `dadaia bugs status/stats` results unchanged pre/post.
- **FR2 (operator contract)** — backlog entries carry `YYYYMMDD-<slug>.md` prefixes from
  each file's REAL first-commit date (git log --follow --diff-filter=A). Archive
  `fast-tier-persona-validation.md` (terminal REJECTED v0.1.64). Rebuild `candidates.md`
  to index the 7 kept entries. AC: every non-index file in `specs/backlog/` matches
  `^\d{8}-`; backlog doctor green.
- **FR3 (resolution law, blocking)** — `dadaia bugs append --event resolved` REQUIRES
  `--resolution-evidence "<text>"` (min 20 chars); the CLI exits non-zero without it and
  the text lands in the event as `evidence`. Other events unaffected.
- **FR4 (MEDIUM, ReDoS)** — `agent_tier_frontmatter._strip_agent_tier` uses a linear
  splitlines scan for the frontmatter block (no `.*?` DOTALL backtracking). AC: the
  security reviewer's adversarial input (fence + 50k blank lines, no close) completes <1s.
- **FR5 (MEDIUM, `specs-upgrade-backup-trips-preflight-dirty-gate`)** — the upgrade backup
  lands OUTSIDE the repo worktree: `<workspace>/.dadaia/tmp/specs-upgrade-backups/<slug>/<from>to<to>-<ts>/`
  when a workspace root is resolvable; sibling fallback otherwise. AC: post-upgrade
  `git status` of the consumer repo shows only the migrated specs (no specs_bkp).
- **FR6 (MEDIUM, `stray-dadaia-tmp-inside-repo`)** — `dadaia specs doctor` invariant
  REPO-DADAIA-1 flags a `.dadaia/` directory inside a context repo; `--fix` removes it
  when it contains only tmp/empty dirs (never with states/).

## Non-goals
F2 central bind-resolution seam (timestamped backlog entry `20260709-central-bind-resolution-seam`).

## Red lines
RED-first; real-artifact fixtures (the actual 52-file layout); never lose a byte of bug
history (consolidation, not deletion).
