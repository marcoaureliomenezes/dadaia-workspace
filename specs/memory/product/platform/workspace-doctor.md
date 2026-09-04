---
slug: workspace-doctor
title: workspace-doctor
category: product
tldr: The one scan and reaper of the workspace instance — WS-<zone>-<verdict> findings against the zone registry, a compliance score, --fix deleting expired and slop.
summary: dadaia doctor classifies every entry of the root, the harness dirs, .dadaia/ and states/ with one finding verdict derived from the zone registry, reports the context invariants, and is the only cleanup engine.
tags: [workspace, doctor, health, repair, zones, privacy]
---

## The scan

- `dadaia doctor` walks the instance in one fixed order — root, the harness dirs (`agents` plus the profile's `claude codex kimi-code`), the `.dadaia/` top level, the closed-canon zones `states dist sessions`, the TTL zones `handoff tmp mcps .cache`; `references/` and `.venv/` are never walked, symlinks never followed.
- Every entry gets one finding verdict: `canon`, `operator` (matches an instance exception), `slop`, `expired` (a file older than the zone's one-day TTL by mtime, or a directory emptied by expiry) or `missing` (an init/install zone or `states/harness_profile.json` absent); `canon` + `operator` count as canonical.
- Canon per level: root — the root law's directories and files (`.env` and `.gitignore` included); harness dirs — an entry the install ledger names, a directory holding one being descended, not judged; `.dadaia/` — the zone names plus `AGENTS.md` and `.gitignore`; `states/` — `spec_contexts.json server_registry.json install_ledger.json agent_model_policy.json agent_model_policy.json.last-good.json privacy_denylist.json instance_exceptions.txt backlog_subject_aliases.txt harness_profile.json presence/ AGENTS.md`; `dist/` — `spec-contexts.json`; `sessions/` — `*.json`; a TTL zone's own `AGENTS.md` — canon by projection, never a TTL candidate.
- Instance exceptions are `.dadaia/states/instance_exceptions.txt`: one glob per line, `#` comments, deduplicated, order kept, matched against the entry name and its root-relative path at root and inside the harness dirs; the root-whitelist hook reads the same file ([[sdd-gate-v3]]).
- Output is one line per non-canonical entry, `WS-<zone>-<verdict>  <path>  (<detail>)` — `<zone>` is `root`, the harness dir, `dadaia`, or the zone name without its leading dot — then the score line `compliance: N/M entries canonical (P%)`, M every entry classified.
- The context invariants ride the same run: `INV-4`/`INV-5`/`CTX-URL-1` (ALIVE/DEAD repo and URL coherence), `INV-6` (a repo slug owned by two contexts, report-only, [[context-management]]), `PRESENCE-GC` (stale advisory presence), `VENV-1` (venv entrypoint health, manual).
- Exit 1 on any slop, expired or missing finding or any invariant issue; `--json` mirrors the run as `{"issues", "findings": [{code, path, verdict, fixable, detail}], "compliance": {canonical, total, percent}, "fixed"}`; `--expired-only` narrows the listing to expired entries; `--redact` masks every foreign context name and repo slug at the render boundary.

## The reaper

- `--fix` runs in order: `presence.gc` -> stale session records -> migrate `states/root_exceptions.txt` into `instance_exceptions.txt` (parsed once, old file unlinked) -> seed missing (a zone directory; the harness profile from the L1 harnesses whose projection dir exists at root, through the profile store's one writer) -> delete expired -> delete slop -> remove a DEAD context's leftover repo.
- `--fix --expired-only` stops after "delete expired" and is the SessionStart lane: every projected harness runtime config runs `<venv>/dadaia doctor --fix --expired-only --quiet` at startup and resume, a CLI process rather than a hook module; `--quiet` prints only what changed, nothing on a compliant instance.
- Structural slop dies only by an explicit `dadaia doctor --fix`; nothing is quarantined or moved, and a deletion target is removed only when its own location resolves inside the workspace, a symlink unlinked and never followed.
- Never touched: `references/` and `.venv/`, entries the install ledger names and the contents of `agentic/` and `hooks/` (hash drift belongs to `public doctor`, [[public-asset-distribution]]), a zone's `AGENTS.md`, entries matching an instance exception, unexpired files, a live session's own presence record.
- `dadaia doctor` is the only cleanup engine; `specs doctor`, `backlog doctor`, `public doctor` and `reports doctor` diagnose their own trees and delete no instance file.

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[workspace-init]], [[public-asset-distribution]].
