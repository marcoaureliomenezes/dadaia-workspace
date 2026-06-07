# SPEC — Release v0.2.1 "Vision Fidelity Fold"

**Status:** Aprovado
**Release ID:** v0.2.1
**Owner:** product-engineer
**Branch:** `feature/0.2.1`
**Date:** 2026-06-07

---

## 1. Objective

v0.2.0 ("Soul & Correctness Fold") gave the workspace its identity: constitution §0, Spec
Context Project keystone, single TTL-lease, 9-core agent roster, rewritten architecture
memory. v0.2.1 closes the remaining **fidelity gaps against `docs/01_medium_codex.md`**
(the normative Product Vision): seven narrow, mostly-mechanical surfaces that are structurally
correct but not yet fully aligned with the vision's canonical shape. None is a redesign.

This is a **PATCH** release — conformance and cleanup work over the closed v0.2.0 baseline.
No new feature surface; no PyPI publish (operator-gated).

The release serves three goals:

1. The workspace's own spec tree and public assets must exactly reflect the vision's
   canonical scaffold (§3, §4, §6 of the vision).
2. Doctor and scaffold must enforce that canonical shape so future drift is caught
   automatically rather than discovered by audit.
3. Dead references, incorrect authority lines, and stale constitution wording must be
   eliminated so agents receive accurate instructions.

---

## 2. Grill Confirmation

The mandatory `dadaia-grill-me` session is **substantively satisfied** — three
cross-spec inconsistencies were resolved directly with the operator and verified
against official Claude Code documentation before this SPEC was authored. No
re-interview is required.

### Resolved decisions

**Decision 1 — `quality-assurance.md` path (locked)**
The quality-assurance memory atom moves to top-level `specs/memory/quality-assurance.md`.
The vision (§6) explicitly enumerates this path. The current location
`specs/memory/product/sdd/quality-assurance.md` is non-conformant. WS-1, WS-3, and WS-4
all reference the identical top-level path string — single source, no drift.

**Decision 2 — Root `CLAUDE.md` + `prompt.md` whitelisted (locked)**
Official Claude Code documentation: Claude Code does not read `AGENTS.md` natively; the
correct bridge is a `CLAUDE.md` at root that `@AGENTS.md`-imports. Both `CLAUDE.md` and
`prompt.md` are therefore legitimate root entries (vision §3 items 8 and 9). WS-5 whitelists
them in the root-whitelist gate, the tmp-file-guardrail rule, the root AGENTS.md, and the
scaffold. This closes T-SANI-02 (`backlog/workspace-sanitization.md`).

**Decision 3 — Handoffs never shown in the panel (locked)**
The panel serves only `.dadaia/reports/` HTML for human consumption. `.dadaia/handoff/`
JSON is the agent↔agent channel exclusively. Constitution §11 is corrected to state this
explicitly. No panel work is in this release.

---

## 3. Product Deltas

The release delivers seven workstreams (WS-1 through WS-7). Each is a conformance delta
against the vision; none changes the product's runtime behavior in a user-visible way
beyond fixing incorrect instruction text.

### WS-1 — Constitution & memory canonization

**FR-1.1** Constitution §0 references `docs/01_medium_codex.md` as the normative product
vision.

**FR-1.2** Constitution gains a scaffold/root-entry section enumerating allowed root
entries including `CLAUDE.md` and `prompt.md` (vision §3, items 8–9).

**FR-1.3** Constitution §13 QA path corrected to `specs/memory/quality-assurance.md`
(top-level, decision 1).

**FR-1.4** Constitution §11 corrected: the panel serves only `.dadaia/reports/` HTML;
handoffs (`.dadaia/handoff/`) are never served by the panel (decision 3).

**FR-1.5** A new memory atom `specs/memory/product/philosophy/product-vision.md` is
created as the current-truth distillation of the normative vision.

**FR-1.6** The non-conformant audit dir `specs/audits/2026-06-06T213731Z/` is renamed to a
conformant `<ts>-<session_id8>` form (no content loss).

**Acceptance:** `dadaia specs doctor` exit 0; constitution text matches all three locked
decisions; single-source lint clean.

### WS-2 — Scoped `AGENTS.md` completion (vision §4 — 8 surfaces)

**FR-2.1** Source `public/data/memory-AGENTS.md` created → projects to
`specs/memory/AGENTS.md` (the 8th scoped surface; currently missing).

**FR-2.2** `public/templates/specs-AGENTS.md` line 48 backlog-authority corrected:
`product-engineer` → `project-manager`.

**FR-2.3** All 8 scoped surfaces listed in vision §4 are present and projected on all
runtimes after `dadaia public stage && install --target all && doctor`.

**Acceptance:** `dadaia public doctor` exit 0; TREE-5 (missing `specs/AGENTS.md`) no longer
fires; all 8 surfaces present.

### WS-3 — Canonical scaffold completion (vision §5 and §6)

**FR-3.1** `public/scaffold/` gains: `audits/` directory stub, top-level
`quality-assurance.md`, and `memory/AGENTS.md` — so a fresh context scaffolds the full
canonical tree from vision §6.

**FR-3.2** `features/spec_context/service.py` `alive()` safely preserves a pre-existing
`specs/` (move/backup) before scaffolding, instead of skipping or silently overwriting
(vision §5).

**FR-3.3** Doctor TREE-4 auto-creates `audits/` when missing.

**Acceptance:** regression test: fresh scaffold yields full canonical tree including
`audits/`, `memory/AGENTS.md`, and top-level `quality-assurance.md`; a pre-existing
`specs/` is preserved, not clobbered.

### WS-4 — Doctor correctness / anti-slop

**FR-4.1** `features/specs/doctor.py` flat-glob bug fixed at lines 1626 (CAT-1) and 584
(SPEC-DOC-002): `glob` → `rglob` so nested atoms register and ~25 phantom CAT-1 warnings
per run stop.

**FR-4.2** TREE-3 check enforces top-level `specs/memory/quality-assurance.md` (aligned
with decision 1 / WS-1 #3).

**FR-4.3** New check for `specs/memory/AGENTS.md` presence (aligned with WS-2).

**Acceptance:** regression tests — phantom-warning count == 0 on a healthy tree; TREE-3 and
the new AGENTS.md check fail on a tree missing the respective file; `dadaia specs doctor`
exit 0 on the live workspace after WS-1 through WS-3 complete.

### WS-5 — Root-whitelist + `CLAUDE.md` bridge (closes T-SANI-02)

**FR-5.1** `CLAUDE.md` and `prompt.md` are whitelisted in all three sources:
`public/scripts/root-whitelist-gate.sh`, `public/rules/tmp-file-guardrail.md`, and
`public/data/AGENTS.md`.

**FR-5.2** Scaffold emits a root `CLAUDE.md` containing `@AGENTS.md` (the native Claude
Code bridge).

**FR-5.3** The live workspace `CLAUDE.md` is upgraded from stub to `@AGENTS.md` bridge
form.

**Acceptance:** `dadaia public stage && install --target all && doctor` exit 0;
root-whitelist gate no longer flags `CLAUDE.md` or `prompt.md`; T-SANI-02 is marked
closed in `backlog/workspace-sanitization.md` by PM.

### WS-6 — Dead write-allowlist + asset hygiene

**FR-6.1** `public/agents/ai-engineer.md` `write_allowlist` corrected: `public/hooks/**`
and `public/commands/**` do not exist → replaced with `public/scripts/**` and
`public/plugins/**`; `public/commands/**` dropped.

**FR-6.2** `public/agents/qa-engineer.md` "pair with" wording tightened per dispatch-purity
(constitution §9 — workers route via PM, not worker→worker).

**FR-6.3** `public/agents/software-architect.md` dead report-template path fixed.

**Acceptance:** `dadaia public doctor` exit 0; no `write_allowlist` glob resolves to a
non-existent path; no dead persona references.

### WS-7 — Lifecycle hygiene

**FR-7.1** Closed release `specs/releases/v0.1.5/` is moved to
`specs/_archive/releases/v0.1.5/` via `git mv` (v0.1.5 is closed; only active releases
belong under `specs/releases/`).

**FR-7.2** `specs/bugs/semaphore-no-liveness-reclaim.md` gains `status: resolved` in its
frontmatter (currently missing; the body already has `resolved_in` and `superseded_by`).

**Acceptance:** `dadaia specs doctor` exit 0; no closed release lingers under live
`specs/releases/` after the move; bug frontmatter is complete.

---

## 4. Architecture Deltas

No new modules, no new CLI commands, no new harness primitives. Affected paths:

- `dadaia_workspace/features/specs/doctor.py` — bug fix (glob → rglob), new checks
- `dadaia_workspace/features/spec_context/service.py` — safe preserve-existing-specs on alive()
- `dadaia_workspace/public/agents/` — ai-engineer.md, qa-engineer.md, software-architect.md
- `dadaia_workspace/public/data/` — AGENTS.md (root), memory-AGENTS.md (new)
- `dadaia_workspace/public/rules/` — tmp-file-guardrail.md
- `dadaia_workspace/public/scripts/` — root-whitelist-gate.sh
- `dadaia_workspace/public/scaffold/` — audits/ stub, quality-assurance.md, memory/AGENTS.md
- `dadaia_workspace/public/templates/` — specs-AGENTS.md (backlog-authority line)
- `specs/constitution.md` — §0 vision ref, root-entry section, §11 panel/handoff, §13 QA path
- `specs/memory/` — new product-vision.md atom; quality-assurance.md moved to top-level
- `specs/audits/` — directory rename (conformant naming)
- `specs/releases/` — v0.1.5 archived
- `specs/bugs/semaphore-no-liveness-reclaim.md` — frontmatter addition

---

## 5. Tech-Stack Deltas

None. No new dependencies, no version bumps, no runtime changes.

---

## 6. Security / Operations Deltas

The root-whitelist gate (WS-5) is made less restrictive in exactly the two entries
(`CLAUDE.md`, `prompt.md`) the vision explicitly allows. No other gate relaxation.
No new network surface, no secrets change, no auth change.

---

## 7. Memory Files Affected at Closure

- `specs/memory/constitution.md` — indirect (constitution changes reflected in memory narrative if needed)
- `specs/memory/product/sdd/specs-doctor.md` — updated to reflect new checks (TREE-3 top-level QA, AGENTS.md check, rglob fix)
- `specs/memory/product/philosophy/product-vision.md` — new atom (created in WS-1)
- `specs/memory/quality-assurance.md` — moved from `product/sdd/` to top-level (WS-1/WS-3/WS-4 coordinate)
- `specs/memory/product/index.md` — catalog updated to reflect moved QA atom path and new product-vision atom
- `specs/memory/product/catalog.json` — regenerated after path changes

---

## 8. Acceptance Criteria (release-level)

1. `dadaia specs doctor` exits 0 on the live workspace after all workstreams complete.
2. `dadaia public doctor` exits 0 after WS-2/WS-5/WS-6 asset changes are staged and
   installed.
3. The pytest suite passes (≥ 2209 tests, zero red) including all WS-3/WS-4 regression
   tests.
4. All 8 scoped `AGENTS.md` surfaces listed in vision §4 are present and projected.
5. Root-whitelist gate no longer flags `CLAUDE.md` or `prompt.md`.
6. No phantom CAT-1 warnings on a healthy tree.
7. TREE-3 check fires on a tree missing `specs/memory/quality-assurance.md` (top-level).
8. `specs/releases/v0.1.5/` is absent from `specs/releases/` (moved to `_archive/`).
9. The three locked grill decisions are encoded in their respective files.

---

## 9. Out of Scope

- PyPI publish — operator-gated; not in this release.
- Panel changes — no panel work; handoff channel is not a panel concern.
- `bugs/doctor-blind-to-projected-drift.md`, `bugs/install-skips-existing-files.md`,
  `bugs/install-does-not-prune-orphan-projections.md` — a different doctor surface
  (projection drift, not spec-tree globs); deferred.
- Any feature surface addition (new CLI commands, new harness primitives, new agents).
- Memory edits beyond the directly-affected atoms listed in §7.

---

## 10. Dependencies and Risks

**Dependencies:**
- WS-4 (doctor fix) must complete before `dadaia specs doctor` is trusted as a green gate
  for other workstreams.
- WS-1 (constitution + QA path) must complete before WS-3 (scaffold) and WS-4 (TREE-3
  check) — the canonical path string originates here.
- WS-5 (root-whitelist) depends on WS-1 §3 root-entry law being authored first.

**Risks:**
- `alive()` preserve-existing-specs (WS-3 FR-3.2): existing code path may have callers
  that assume skip behavior. Regression test required before merging.
- Audit dir rename (WS-1 FR-1.6): must be a `git mv` to preserve history; plain `mv`
  loses git tracking.
- `quality-assurance.md` path move (decision 1): catalog.json and index.md must be updated
  atomically in CLOSURE to avoid broken references between the regeneration and the memory
  update.

**Deploy model:** single `feature/0.2.1` branch. Gate sequence per workstream:
`qa-engineer` commit gate → `security-reviewer` push gate → `code-reviewer` PR gate.
Final merge/PR per ship trio. No PyPI publish.
