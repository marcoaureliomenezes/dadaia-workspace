---
release: v0.1.73
phase: IMPLEMENTATION
---

# Active release: v0.1.73 — Governance hygiene: single bug ledger, timestamped backlog, blocking resolution gate

Operator-mandated governance cleanup + all 4 open ledger bugs (open work outranks backlog):

- FR1 (HIGH) `bugs-store-fragments-into-hourly-files` — ONE append-only `specs/bugs/bugs.jsonl`
  (operator contract; per-hour rotation was implementation drift) + `specs upgrade` step
  v3→4 consolidating hourly files chronologically and collapsing `specs/bugs/_archive/*.md`
  into one `_archive/archive.jsonl` (content preserved per line).
- FR2 backlog hygiene — `YYYYMMDD-` timestamp prefixes on kept entries (real first-commit
  dates), archive the terminal-REJECTED `fast-tier-persona-validation`, rebuild `candidates.md`.
- FR3 blocking resolution gate — `dadaia bugs append --event resolved` REQUIRES
  `--resolution-evidence` (reporter-artifact repro + surfaces covered); CLI rejects without.
- FR4 (MEDIUM) `migrate-agent-tier-frontmatter-redos-on-unterminated-block` — linear-time
  frontmatter scan (no backtracking regex).
- FR5 (MEDIUM) `specs-upgrade-backup-trips-preflight-dirty-gate` — upgrade backup lands
  OUTSIDE the repo worktree (workspace `.dadaia/tmp/specs-upgrade-backups/…`).
- FR6 (MEDIUM) `stray-dadaia-tmp-inside-repo` — doctor invariant flags an in-repo
  `.dadaia/`; clean reclaims it.

F2 central bind-resolution seam → timestamped backlog entry (next release; too large to
bundle honestly here).
