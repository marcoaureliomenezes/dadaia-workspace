# Closure: Release — v0.1.4.4

> **Status:** Aprovado
> **Release ID:** v0.1.4.4
> **Owner:** product-engineer
> **Closed:** 2026-06-04

## Summary

Release v0.1.4.4 (workspace-root-sanitization) eliminated workspace-root
pollution by codifying a strict root whitelist, wiring a deterministic
enforcement hook, relocating non-conforming artifacts into canonical `.dadaia/`
homes, redirecting tool caches off root via `pyproject.toml`, and surfacing
violations through four new `dadaia doctor` invariants.

The root whitelist law is now canonical in `public/data/AGENTS.md` (the fan-out
source for all consumer `AGENTS.md` files) and in `public/rules/tmp-file-guardrail.md`.
Six allowed directories (`.agents/`, `.claude/`, `.codex/`, `.dadaia/`, `.opencode/`,
`repos/`) and one allowed file (`AGENTS.md`) constitute the whitelist. Operator-created
files are always excepted and are never auto-deleted.

The live hook `public/scripts/root-whitelist-gate.sh` is installed via
`dadaia public install --target all` (no `--force`) into `.claude/settings.json`
(PreToolUse) and `.codex/hooks.json`. The hook was tested live: a non-whitelisted
root write was blocked; a write under `.dadaia/tmp/` was allowed.

Three tool configs (`CLAUDE.md`, `.mcp.json`, `opencode.json`) were researched and
confirmed as irremovable from root by their respective tools. They are documented in
`.dadaia/states/root_exceptions.txt` with reasoning in `RESEARCH-configs.md`.
`scripts/` was relocated to `.dadaia/scripts/`. All regenerated caches were deleted.
Ruff and coverage caches now write under `.dadaia/cache/` as of the `pyproject.toml`
update.

`dadaia doctor` exits 0 with no ROOT-* findings. The full pytest suite passes at
2143 tests, 0 failures, and leaves the repo root clean.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-SANI-01 | Root law in AGENTS.md + tighten tmp-file-guardrail + root-whitelist hook | `829206c` |
| T-SANI-02 | Relocate root crap + research tool configs | `829206c` |
| T-SANI-03 | Redirect ruff + coverage caches off root | `fc10f5e` |
| T-SANI-05 | `dadaia doctor` ROOT-1..4 invariants | `e52d0f0` |
| T-SANI-06 | QA verification | `829206c` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full pytest suite green | `pytest -q -p no:cacheprovider` | `2143 passed, 0 failed` |
| ROOT-1..4 doctor checks pass | `dadaia doctor` | exit 0, no ROOT-* findings |
| Ruff cache redirected off root | `ruff check .` | no `.ruff_cache` created at workspace root |
| Coverage file redirected off root | `pytest --cov .` | no `.coverage` created at workspace root (writes to `.dadaia/cache/coverage/`) |
| Hook blocks non-whitelisted root write | live hook invocation | write blocked; `.dadaia/tmp/` write allowed — confirmed by T-SANI-06 |
| Root contains only whitelisted entries + exceptions | `ls -a /home/marco/workspace/dadaia/` | only `.agents/`, `.claude/`, `.codex/`, `.dadaia/`, `.opencode/`, `repos/`, `AGENTS.md`, and documented exceptions remain |
| No repo pollution after test run | `ls repos/` + root inspection | no cache or output artifacts inside any repo working tree or at root |
| `dadaia public doctor` exit 0 after propagation | `dadaia public doctor` | exit 0 — hook and rule projections consistent |
| `dadaia public install` without `--force` succeeded | `dadaia public install --target all` | commit `829206c` — new hook and tightened rule installed |
| 32 new doctor unit tests green | `pytest tests/unit -k ROOT` | included in 2143 |

## Drifts

### sani-03-cache-regression

**Description:** The initial T-SANI-03 commit (`b524e6f`) redirected ruff to
`.dadaia/cache/ruff` but inadvertently wrote coverage data under `.dadaia/caches/`
(plural, non-canonical). A regression fix commit (`fc10f5e`) corrected the path to
`.dadaia/cache/coverage/` (singular, canonical) and verified the full suite stayed
green.

**Resolution:** `pyproject.toml` updated to `.dadaia/cache/coverage/.coverage`;
the non-canonical `.dadaia/caches/` path was never committed to the workspace root
state. The canonical `.dadaia/cache/` subtree is the accepted location for all
tool caches.

**Memory updates:** `specs/memory/architecture.md` — updated runtime state section
to document `.dadaia/cache/ruff/` and `.dadaia/cache/coverage/` as canonical tool
cache locations.

### sani-01-propagation-no-force

**Description:** During T-SANI-01 the operator's constraint was `dadaia public install --target all`
without `--force`. The new `root-whitelist-gate.sh` script and the tightened
`tmp-file-guardrail.md` are additions, not replacements; no hash collisions were
detected and the standard install path succeeded without requiring `--force`.

**Resolution:** No drift — propagation completed cleanly as planned.

**Memory updates:** None.

### sani-02-research-outcome

**Description:** SPEC assumed `CLAUDE.md`, `.mcp.json`, and `opencode.json` might
be relocatable. T-SANI-02 research found all three are tool-discovery-coupled to
root (Claude Code, opencode, and the MCP subsystem each read from a fixed root
path with no redirect mechanism). The relocation path in the SPEC was replaced by
a documented exception list.

**Resolution:** Documented in `RESEARCH-configs.md` under the release directory.
`.dadaia/states/root_exceptions.txt` lists all three with reasoning. The operator
action item for `.mcp.json` (migrate `mcpServers` into `.claude/settings.json`)
is captured there for a future release.

**Memory updates:** `specs/memory/architecture.md` — updated runtime state section
to document `.dadaia/states/root_exceptions.txt` and its purpose. Updated
`public/` section to reflect the new `root-whitelist-gate.sh` hook in the asset
chain.

## Memory updates

- `specs/memory/architecture.md` — updated: (1) runtime state table to add `.dadaia/cache/ruff/`, `.dadaia/cache/coverage/`, `.dadaia/states/root_exceptions.txt`, and `.dadaia/scripts/` as canonical locations; (2) public/ section to reference `root-whitelist-gate.sh` as a new canonical hook in the asset chain; (3) doctor section to list ROOT-1..4 invariants; (4) Gate section to note the root-whitelist PreToolUse hook.
- `specs/memory/tech-stack.md` — no change: release did not add or remove dependencies; `pyproject.toml` config changes are implementation detail, not a new approved technology.
- `specs/memory/product/index.md` — no change: root sanitization is an operator-facing enforcement mechanism, not a product feature in the catalog.

## Backlog returns

- `specs/backlog/candidates.md` ← operator action item: migrate `.mcp.json` `mcpServers` content into `.claude/settings.json` `mcpServers` key, then remove `.mcp.json` from root. Research in `RESEARCH-configs.md` confirms this is the correct path. Deferred because it requires testing MCP server connectivity after migration — not a one-line edit.

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/v0.1.4.4/` via
`git mv`. ACTIVE.md will be updated to `release: none` / `phase: none` once both
v0.1.4.3 and v0.1.4.4 are archived.
