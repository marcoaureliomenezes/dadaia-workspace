---
slug: workspace-doctor
title: workspace-doctor
category: product
tldr: 'workspace-state diagnosis + repair; checks LOCK-NEW/LOCK-GC/LOCK-4/5/CTX-URL-1/INV-4/5/ROOT-1..4/VENV-1; --fix runs SENTINEL/PTR/GRAVEYARD-GC.'
summary: >-
  diagnosis + repair of workspace-state invariants with optional --fix.
  Emitted checks: context ALIVE/DEAD (INV-4, INV-5), invalid TTL-lease (LOCK-NEW),
  stale lease of a dead/unprobeable holder (LOCK-GC — never reclaims a live pid),
  production-write without task_id in the audit log (LOCK-4), BLOCKED_ATTEMPT in the
  audit log (LOCK-5, signal), ALIVE context with empty repo_url (CTX-URL-1), root
  whitelist + forbidden caches + tool configs + .dadaia/ subdirs (ROOT-1..4), venv
  health (VENV-1). Fix-only actions (appear only under --fix, not as issues):
  SENTINEL-GC, PTR-GC, GRAVEYARD-GC. Bind/session records decay by TTL against
  heartbeat-renewed last_seen_at. Known limitation: the command exits 0 even with
  issues.
tags:
- workspace
- doctor
- health
- repair
token_estimate: 1300
last_updated: '2026-07-02'
release_origin: v0.1.48
---

CLI surface: `dadaia doctor [--fix]`

## Purpose

Validates workspace-state invariants — consistency of `spec_contexts.json` (schema v2: ALIVE/DEAD, no global context flag), presence of expected files in `.dadaia/`, branch state of repos cloned in `repos/`, and TTL-lease health. When passed `--fix`, it applies automatic repairs for issues marked as fixable.

### Context-state invariants (INV-4, INV-5)

With the v2 model (ALIVE/DEAD), two invariants cover the context lifecycle:

  * **INV-4:** context with `state=ALIVE` and repo missing from `repos/` → WARN; suggestion: `dadaia context alive <name>`.
  * **INV-5:** context with `state=DEAD` and repo present in `repos/` → WARN; suggestion: `dadaia context dead <name>` or manual removal.

The old INV-1, INV-2, INV-3, INV-6 (guards for the legacy global context marker) were removed in v2.

### Lock/lease checks (v0.1.6+)

The TTL-lease uses a single-record JSON per context at `.dadaia/states/ctx_locks/<ctx>.lock.json`. The doctor verifies:

| Code | What it detects | Auto-fix |
|--------|---------------|----------|
| `LOCK-NEW` | `.lock.json` with invalid JSON or missing required fields — `_check_lease_records` | AUTO-FIX (`--fix`): deletes the invalid `.lock.json`. |
| `LOCK-GC` | TTL-expired lease whose holder is **dead** (pid probe, injected at the composition root via `container`) or is **unprobeable** (pre-`pid` record ⇒ TTL-only reclaimable) | AUTO-FIX (`--fix`): reclaim (deletes the record). A holder with a **live** pid is NEVER reclaimed, even past-TTL (no-steal invariant). |
| `CTX-URL-1` | Context with `state=ALIVE` and empty `repo_url` in the record (non-portable context) | Manual: `dadaia context update <name> --url <url>` — or automatic back-fill on `alive`/`dead` when the on-disk repo has an origin. |
| `INV-4` | Context with `state=ALIVE` and repo missing from `repos/` | Manual: `dadaia context alive <name>`. |
| `INV-5` | Context with `state=DEAD` and repo present in `repos/` | AUTO-FIX: `dadaia context dead <name>` or manual removal. |
| `LOCK-4` | Production-write event in `lock-events.jsonl` without a `task_id` field | Manual (discipline signal). |
| `LOCK-5` | `BLOCKED_ATTEMPT` event in `lock-events.jsonl` | Manual (signal — surfaced, no fix). |
| `ROOT-1` | Top-level entry at the workspace root outside the whitelist (+ `root_exceptions.txt`) | Manual. |
| `ROOT-2` | Forbidden cache/output at the root (e.g. `.pytest_cache/`, `coverage/`) | Manual. |
| `ROOT-3` | Tool config outside its canonical home and outside the exception list (WARN) | Manual. |
| `ROOT-4` | Unknown top-level subdir inside `.dadaia/` (allowlist includes `hooks/`) | Manual. |
| `VENV-1` | Workspace venv health: `.dadaia/.venv` missing, `bin/dadaia` missing or non-executable, or interpreter incoherent with the workspace venv (complements the `pre_gate` hook's venv-guard) | Manual: recreate/repair the venv (`dadaia init` or provisioning of `.dadaia/.venv`). |

**Fix-only actions** (executed by `--fix`, not emitted as `check()` issues):
`SENTINEL-GC` (deletes an orphan `.lock.sentinel` with mtime > 30s), `PTR-GC` (deletes an orphan
`.ptr` in `.dadaia/sessions/runtime/` without a live lease) and `GRAVEYARD-GC` (deletes expired
session files).

Bind/session records (`.dadaia/sessions/<id>.json`) are collected by TTL measured against
`last_seen_at`, which the PostToolUse heartbeat renews on every tool use — an active
session's bind never decays; a record without `last_seen_at` keeps TTL-from-creation; the record's pid
(bind-CLI, dead by construction) is not consulted.

`LOCK-NEW`/`LOCK-GC` messages include `context`, the holder's `session_id` and
`heartbeat`; the `LOCK-GC` message **names the remediations** (`dadaia doctor --fix`
or `dadaia lock steal <ctx>`) for a stale-dead lease that is safe to reclaim.

**Known limitation:** `dadaia doctor` prints the issues but **exits 0 even
when there are issues** (it only exits non-zero when the workspace is not initialized) — it does not
serve as a mechanical gate in pipelines without parsing the output.

## Usage flow

  1. `dadaia doctor` — runs the invariant checklist (LOCK-NEW, LOCK-GC, LOCK-4, LOCK-5, CTX-URL-1, INV-4, INV-5, ROOT-1..4, VENV-1) and lists issues flagged `[fixable]` or `[manual]`.
  2. The operator inspects the issues; if all are `[fixable]`, runs `dadaia doctor --fix`.
  3. The doctor applies the repairs and shows the list of actions performed.
  4. Re-running `dadaia doctor` must return "All invariants OK".

## Typical trigger

After an agent-session crash (check whether STALE leases exist), after upgrading the dadaia-workspace version (ensure schema v2), before demos, or when the gate blocks with a STALE/conflict lease message.

## Differentiator

Without this guardrail, abandoned implementation leases (session crash) would block future writers indefinitely and remain permanently unrecoverable (pre-`pid` records were un-reclaimable until v0.1.10). `LOCK-GC` reclaims those leases safely — the pid probe guarantees a live holder is never stolen; `LOCK-NEW` deletes invalid records; the operator is informed with evidence instead of having to edit JSON by hand. `SENTINEL-GC` guarantees that orphan sentinels (process dead between the O_EXCL CAS and the unlink) do not cause a permanent block. `CTX-URL-1` prevents non-portable ALIVE contexts (empty URL) from failing silently on an export/import.

## Runtime state touched

  * Read: `.dadaia/states/spec_contexts.json`, `.dadaia/states/ctx_locks/*.lock.json`, `.dadaia/states/ctx_locks/*.lock.sentinel`, `.dadaia/sessions/runtime/*.ptr`, `repos/`.
  * Write (only with `--fix`): repairs to lock files, sentinel files, ptr files; appends to `.dadaia/logs/lock-events.jsonl`.

## Dependencies

  * Standalone. Depends on no other feature beyond the structure created by [[workspace-init]].
  * Complementary to [[specs-doctor]] (this one validates workspace runtime state; specs-doctor validates SDD structure).
  * Related to [[context-management]] — the lock files the doctor inspects are created by the gate's inline acquire.
