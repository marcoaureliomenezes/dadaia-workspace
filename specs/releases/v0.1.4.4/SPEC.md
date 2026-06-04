# SPEC: v0.1.4.4 — workspace-root-sanitization

**Status:** Aprovado
**Release ID:** v0.1.4.4
**Owner:** product-engineer
**Created:** 2026-06-04

> Staging release-id (4-segment). `pyproject` stays at `0.1.4`; no version bump.
> Scope deliberately EXCLUDES report/handoff cleanup, the Reports tab, and report
> retention — those are owned by **v0.1.4.3 (report-retention)**. This release is the
> **prevention** half only. Source backlog: `specs/backlog/workspace-sanitization.md`.

---

## 1. Objective

Make workspace-**root** pollution impossible by codifying a strict whitelist law,
relocating every non-conforming artifact into a canonical `.dadaia/` home, redirecting
tool caches off root, and asserting the law with deterministic enforcement
(`AGENTS.md` + rule + hook + `dadaia doctor`).

## 2. The Law — root whitelist

The workspace root may contain ONLY:
- Directories: `.agents/`, `.claude/`, `.codex/`, `.dadaia/`, `.opencode/`, `repos/`
- File: `AGENTS.md`
- **Operator exception:** any file/dir created by the human operator is always allowed and
  MUST never be auto-deleted (e.g. `prompt.md`, screenshots).

Everything else at root is forbidden; a regenerating process must redirect its output into a
canonical `.dadaia/<subdir>`.

## 3. Scope (in)

- **SANITIZE-01** — codify the law in `public/data/AGENTS.md`; tighten
  `public/rules/tmp-file-guardrail.md` so its root whitelist matches the law exactly
  (remove `CLAUDE.md`, `opencode.json`, `.mcp.json`, `scripts/` from the whitelist); add a
  deterministic root-whitelist hook; propagate (`stage` + `install`, no `--force`).
- **SANITIZE-02** — relocate current root crap per the origin table: `scripts/` →
  `.dadaia/scripts/`, redirect Playwright MCP output → `.dadaia/mcps/playwright/`, delete
  regenerated caches. **Research-first** for `.mcp.json` / `opencode.json` / `CLAUDE.md`:
  verify each tool's config-discovery support, then relocate where safe, else add to a small
  documented root exception list. Never delete operator-created files.
- **SANITIZE-03** — redirect remaining tool caches off root: `ruff` `cache-dir`, coverage
  `COVERAGE_FILE`/`data_file` under `.dadaia/`. (pytest `-p no:cacheprovider` and mypy
  `cache_dir=/dev/null` already in place.)
- **SANITIZE-05 (doctor part)** — add `ROOT-1..4` invariants to `dadaia doctor`
  (root whitelist; no forbidden caches at root; configs in canonical homes or exception list;
  `.dadaia/` only canonical top-level subdirs). ADDITIVE checks — must not collide with
  v0.1.4.3 `T-RET-05` doctor work.

## 4. Out of scope (owned elsewhere / deferred)

- Report/handoff cleanup, `dadaia clean`, retention, Reports-tab API+UI, reports rendering
  → **v0.1.4.3 (report-retention)** + the reports-tab fix (`reports.js` iframe).
- Root `.gitignore` — operator-owned; not modified by this release.
- Scheduled cron/timer cleanup routines (SANITIZE-04) → deferred / v0.1.4.3.

## 5. Constraints

- Do NOT touch `specs/releases/ACTIVE.md` (live: `v0.1.4.3 / IMPLEMENTATION`).
- Do NOT bump `pyproject.toml` version (stays `0.1.4`).
- Do NOT touch `v0.1.4.3` / `v0.1.5` release dirs or their code surfaces.
- No `--force` on `dadaia public install` without operator authorization.

## 6. Acceptance

- Root contains only whitelisted entries after a full test run; `dadaia doctor` `ROOT-*` pass.
- `tmp-file-guardrail` whitelist == the law; `AGENTS.md` states the law explicitly.
- A non-whitelisted root write is blocked deterministically by the hook.
- Unit + contract tests green; repo root clean (no `.ruff_cache`/`.coverage`/`.pytest_cache`/
  `.mypy_cache`/`.playwright-mcp`).
