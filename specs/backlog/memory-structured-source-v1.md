# Backlog Candidate — memory-structured-source-v1

> **Status:** Candidate (não autoriza implementação)
> **Phase:** 2 of 2 — **depends on `memory-context-enforcement-v1` (Phase 1)**
> **Suggested owner:** software-architect (schema + renderer + migration), product-engineer (atom migration in CLOSURE)
> **Co-owners:** software-engineer-python (doctor rework + renderer), ai-engineer (catalog regen tie-in)
> **Source:** `.dadaia/reports/dadaia-workspace/software-architect/2026-05-30T153000Z-memory-source-of-truth-architecture.html` + master analysis `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-30T154500Z-memory-context-engineering-analysis.html`

## Problem

Memory's **source of truth is its presentation format** (23 hand-authored HTML atoms). This inverts
data/presentation: agents pay a 23–47% markup tax per read, atomicity is enforced by a *bypassable regex*
(grep for the word "Changelog"), and new dadaia-workspace users inherit an HTML-authoring burden via the
scaffold. The structured-source idea (operator proposal): a structured editable source → generated HTML
for the panel; agents consume the structured thing.

## Intent

Make the memory source of truth **structured and schema-validated**, with HTML retained everywhere as a
**generated** panel artifact. The primary win is **atomicity-as-schema** + authoring ergonomics + the
templates/structure new users inherit — NOT tokens or blindness (those are Phase 1).

## Scope (Phase 2 — foundation-first migration)

1. **Source-of-truth architecture.** YAML (editable, gate-locked, schema-validated) → renderer
   (`features/specs/renderer.py`, new) → committed HTML (panel `memory.py` unchanged, serves byte-identical).
2. **Format = YAML, one file per atom.** Decisive factors: multi-line prose (block scalars), git-diff
   ergonomics for the CLOSURE review gate, inline comments documenting the atomicity contract. Mermaid
   lives fine in a block scalar (renderer wraps it). JSON loses on prose/diffs; the catalog stays JSON.
3. **Schema design (4 types).** `memory-architecture-v1`, `memory-tech-stack-v1`, `memory-product-index-v1`,
   `memory-product-feature-v1`. Atomicity encoded as `additionalProperties: false` → a changelog field is
   **structurally impossible**, not regex-bypassable. Product-feature required fields:
   `purpose`/`flow_steps`/`typical_trigger`/`differential`. Index entries carry `rank` + `keywords` (what
   Phase 1's `catalog.json` consumes).
4. **Doctor rework.** Replace HTML-parse heuristics with schema validation + committed-HTML-sync check +
   catalog completeness. A migration guard skips the new checks when YAML is absent (existing HTML-source
   consumer repos get WARN, not error).
5. **Scaffold + templates for new users.** `public/scaffold/memory/` ships YAML; new consumer repos are
   born structured. The j2 templates flip to consuming structured data instead of being authored directly.
6. **Migrate this repo's 23 atoms** HTML→YAML (product-engineer CLOSURE deliverable) — dogfood.
7. **`dadaia migrate` guard** + consumer deprecation window for ecosystem-wide adoption.

## Locked decisions (operator, grill-me 2026-05-30)

- HTML retained but **generated** (panel unchanged); structured file is the sole editable source.
- **Foundation-first (hard rule):** schemas (2A) + renderer (2B) ship as additive phases BEFORE migrating
  any atom (2E). Migrating before the foundation exists = build-on-stale-layers (migrate twice). The
  architect's single strongest recommendation.
- Catalog stays JSON (Phase 1); only content source moves to YAML here.

## Dependencies

- **`memory-context-enforcement-v1` (Phase 1)** — the catalog + injection consume the `rank`/`keywords`
  this phase formalizes into schema; Phase 1 ships first on HTML content, Phase 2 swaps the source format
  underneath without changing the injection contract.
- Touches consumer-facing scaffold → must ship behind a migration guard (same discipline as spec-context v2).

## Acceptance shape (to formalize at SPEC time)

- 4 schemas exist in `core/`; renderer in `features/specs/` produces byte-stable HTML from YAML.
- Atomicity violation is impossible by construction (no changelog field in schema).
- `specs doctor` validates YAML against schema + HTML-sync; migration guard protects HTML-source repos.
- Scaffold ships YAML; new repos born structured; this repo's 23 atoms migrated.
- Panel renders unchanged (byte-identity preserved).

## Biggest gain

Atomicity becomes a structural guarantee instead of a regex — the real reason to change format, and the
operator's explicit "consolidate memory atomically" goal.
