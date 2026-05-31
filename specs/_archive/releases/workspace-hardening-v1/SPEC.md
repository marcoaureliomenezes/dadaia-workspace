---
release: workspace-hardening-v1
phase: IMPLEMENTATION
---

# SPEC — workspace-hardening-v1

**Status:** Aprovado

## Problem Statement

Four related issues require a single coordinated release:

1. **Panel auth UX bug** — `sessionStorage` is cleared on tab close; re-opening `localhost:4999` shows "Authentication required" on all tabs despite a valid panel session.

2. **Agent definition drift (critical)** — `code-reviewer` and `security-reviewer` body text references skills (`architect-code-audit`, `architect-design-patterns`, `architecture-code-review`, `security-audit-protocol`) that were removed from `public/skills/` in `token-cost-bigbang-v1` without updating the agent bodies. No validator catches this. Five additional agents have routing ambiguities or body/frontmatter inconsistencies.

3. **CLI asset granularity missing** — `dadaia public` has no way to enumerate installed assets and no way to install a single asset type, forcing full re-install for single-type changes.

4. **Panel workflows are read-only** — The Workflows tab shows workflows but cannot invoke them, breaking the observe→act loop.

## Root Cause (agents drift)

Three-step failure chain discovered in git history:
1. `agents-r1-v1` (c48d49a) authored agents with forward references to skills that were never created.
2. `token-cost-bigbang-v1` (a2e1fee) removed those skills from `public/` and agent frontmatter but left orphaned body text.
3. `dadaia public doctor` has no validator that cross-references agent `skills:` fields against `public/skills/` contents.

## Scope

### FR-01 — Panel auth persistence
Switch `panel_token` storage from `sessionStorage` to `localStorage` so it survives tab close.

### FR-02 — Fix orphaned skill references
Remove references to non-existent skills from `code-reviewer` and `security-reviewer` body text; rewrite as built-in methodology descriptions.

### FR-03 — D-CX-SKILLS doctor check
Add a new `dadaia public doctor` invariant that validates every skill name in agent frontmatter `skills:` lists against the presence of `public/skills/<name>/`. Emit `[drift]` on mismatch.

### FR-04 — Agent routing clarifications
Fix five additional agents: `design-specialist` (duplicate plugin rule), `project-manager` (Node/frontend routing ambiguity), `project-auditor` (data-analyst dispatch contradiction), `product-engineer` (Read vs shell clarification), `researcher` (dispatch condition).

### FR-05 — `dadaia public list`
New CLI command: `dadaia public list [--format table|json]` listing all asset categories with counts and names.

### FR-06 — `dadaia public install --only <type>`
New flag: `--only <type>` on `dadaia public install` restricting installation to one asset category.

### FR-07 — Panel workflow dispatcher
New `POST /api/workflows/<name>/run` endpoint + "Run" button on the Workflows tab. Security: Bearer auth + name validation + workflow existence check before spawn.

## Out of Scope

- New skill files for removed skills (`architect-*`, `security-audit-protocol`) — deliberate removal in `token-cost-bigbang-v1` stands.
- `reports-next-cli` and `reports-mcp-server` — deferred to next release.
- `panel-workflow-run-dispatcher` with dry-run mode — post-MVP.
