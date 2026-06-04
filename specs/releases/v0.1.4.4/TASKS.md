# TASKS: v0.1.4.4 — workspace-root-sanitization

**Status:** Aprovado

Markers: `[ ]` open → `[-]` in progress → `[x]` done. Backlog: `specs/backlog/workspace-sanitization.md`.

---

### T-SANI-01 — Root law in AGENTS.md + tighten tmp-file-guardrail + deterministic hook
- **Owner:** ai-engineer
- **Status:** [-]
- Codify the root whitelist law (6 dirs + `AGENTS.md` + operator exception) in
  `public/data/AGENTS.md`. Tighten `public/rules/tmp-file-guardrail.md` so its root
  whitelist == the law (remove `CLAUDE.md`, `opencode.json`, `.mcp.json`, `scripts/`).
  Add a deterministic root-whitelist hook (block creation of non-whitelisted root entries;
  honor operator exception). Propagate: `dadaia public stage && dadaia public install --target all`
  (NO `--force`), then `dadaia public doctor`.
- **AC:** AGENTS.md states the law; rule whitelist matches; hook blocks a non-whitelisted root
  write and allows operator-tagged files; `public doctor` exit 0.

### T-SANI-03 — Redirect ruff + coverage caches off root
- **Owner:** software-engineer-python
- **Status:** [x]
- In `pyproject.toml`: set `[tool.ruff] cache-dir` under `.dadaia/` and coverage
  `data_file`/`COVERAGE_FILE` under `.dadaia/` (or disable). Confirm pytest/mypy already
  redirect. Verify a `ruff check` + `pytest --cov` run leaves no `.ruff_cache`/`.coverage` at root.
- **AC:** ruff + coverage create nothing at repo root; existing lint/test still pass.

### T-SANI-02 — Relocate root crap + research tool configs
- **Owner:** software-engineer-python
- **Status:** [ ]
- Relocate `scripts/` → `.dadaia/scripts/` (update any references). Redirect Playwright MCP
  output → `.dadaia/mcps/playwright/`; delete stray `.playwright-mcp/`. Delete regenerated
  caches at root. **Research** `.mcp.json` / `opencode.json` / `CLAUDE.md`: verify each tool's
  config-discovery support; relocate into `.dadaia/` where safe, else record a small documented
  root exception list (in AGENTS.md / the rule). NEVER delete operator-created files.
- **AC:** root holds only whitelisted entries + documented exceptions; research outcome recorded.

### T-SANI-05 — `dadaia doctor` ROOT-* invariants (additive)
- **Owner:** software-engineer-python
- **Status:** [ ]
- Add `ROOT-1` (only whitelisted root entries + operator-tagged), `ROOT-2` (no forbidden
  caches/outputs at root), `ROOT-3` (configs in canonical homes or exception list), `ROOT-4`
  (`.dadaia/` only canonical top-level subdirs). ADDITIVE — must not collide with v0.1.4.3
  `T-RET-05`. Unit tests for each. Actionable fix hints.
- **AC:** `dadaia doctor` reports ROOT-* status; tests green.

### T-SANI-06 — QA verification
- **Owner:** qa-engineer
- **Status:** [ ]
- Verify all ACs above; full unit+contract run leaves repo root clean; the root-whitelist hook
  blocks a planted non-whitelisted write and allows an operator-tagged file.
- **AC:** evidence captured; zero root pollution after the run.
