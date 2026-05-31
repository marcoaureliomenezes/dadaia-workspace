# Backlog Candidate — memory-structured-source-migration-v2

> **Status:** Candidate (não autoriza implementação)
> **Phase:** 3 of 3 — **depends on `memory-structured-source-v1` (Phase 2) being CLOSED**
> **Suggested owner:** product-engineer (atom migration in CLOSURE), software-engineer-python (schema enrichment + renderer + extractor upgrade), software-architect (schema design review)
> **Origin release:** `memory-structured-source-v1` — CLOSURE drift `schema-adequacy-gap`; see `specs/_archive/releases/memory-structured-source-v1/CLOSURE.md`

## Problem

The v1 schemas shipped in `memory-structured-source-v1` cannot losslessly represent this repo's richest
atoms. The dogfood migration (C-6, T-MSS-10) was attempted and produced unacceptable body-text loss:

- `tech-stack.html` — approx. 46% body-text loss when extracted to YAML
- `architecture.html` — approx. 25% body-text loss
- `agent-comms.html` — does not fit `memory-product-feature-v1` fixed-section contract (non-standard
  sections; no mapping to `purpose`/`flow_steps`/`typical_trigger`/`differential`/`runtime_state`/`dependencies`)
- `brand-identity.html` — same: non-standard structure (palette tokens, CSS variables) that doesn't map
  to the feature schema's fixed six fields

Root cause: the v1 schemas use single-value fields for diagrams (`diagram: str`) and a fixed-section
contract for feature atoms. Atoms with multiple diagrams, rich tables, or non-standard sections exceed
what these fields can represent without truncation.

The W1 MAPPING.md document authored during schema design (Phase 2) flagged "Fork 1" as the risk path
for rich atoms. That risk materialized in full during the dogfood.

## Intent

Enrich the 4 schemas to allow lossless representation of all 21 atoms in this repo, then re-run the
21-atom dogfood migration with a content-fidelity gate that prevents truncated YAML from being committed.

## Scope

### 1. Schema enrichment (4 schemas in `dadaia_workspace/public/schemas/memory/`)

- **Diagram arrays** — replace the single `diagram: str` field with `diagrams: [str]` (or equivalent)
  so atoms with multiple Mermaid diagrams can be represented without truncation.
- **Extensible / optional sections for non-standard atoms** — for `memory-product-feature-v1`, add an
  optional `extra_sections` map or equivalent escape mechanism so atoms like `agent-comms` and
  `brand-identity` can carry sections that don't fit the standard six fields.
- **Raw-HTML escape hatch** — a `raw_html_sections: {id: str, content: str}` or similar field to
  allow verbatim HTML fragments for atoms whose richness (e.g. rich tables, nested lists) cannot be
  expressed as flat YAML scalars without losing fidelity.
- **`memory-architecture-v1` and `memory-tech-stack-v1`** — allow multi-section content beyond what
  the current single-value fields support (both atoms contain dense tables and prose that overflow a
  simple string field).
- All changes must remain `additionalProperties: false` at the top level (the D-5 atomicity guarantee
  must hold) while permitting structured extension within the schema.

### 2. Renderer upgrade (`features/specs/renderer.py`)

- Update the renderer to handle diagram arrays (emit multiple `<pre class="mermaid">` blocks), extra
  sections (render as `<section id="..."><h2>...</h2>...</section>`), and raw-HTML escapes.
- Maintain determinism: same YAML → same HTML on every run.

### 3. Extractor upgrade (`dadaia migrate memory-yaml`)

- Upgrade the extractor to produce valid YAML for the enriched schemas when running on rich atoms.
- The extractor must handle: multiple Mermaid blocks (produce an array); rich tables (either reproduce
  as YAML or fall back to raw-HTML escape); non-standard section headings (map to `extra_sections`).

### 4. Content-fidelity gate

A new acceptance criterion is required before any atom migration commit is accepted:

**Normalized body-text round-trip must be lossless.** The criterion: for each atom, strip the committed
HTML (pre-migration) of boilerplate (head, style, meta) using `strip-memory-html.py`; render the YAML
back to HTML; strip the rendered HTML the same way; compare. The normalized bodies must be equal (or
differ only in whitespace/ordering that is semantically neutral).

This gate must be machine-checked — not just a visual panel review. `dadaia specs doctor` should
include it as a new check (e.g. `FIDELITY-1`) that fires when a YAML atom's round-trip produces a
normalized-body mismatch against the last committed HTML.

### 5. 21-atom dogfood migration (C-6 re-run)

With the enriched schemas, upgraded renderer, and content-fidelity gate in place:
- Migrate all 21 atoms in `repos/dadaia-workspace/specs/memory/` from HTML-source to YAML-source.
- Run `dadaia memory render` on each atom; commit the reformat baseline.
- Verify `dadaia specs doctor` exits 0 with 0 STRUCT errors, 0 SYNC-1 warnings, 0 FIDELITY-1 errors.
- Product-engineer visual/DOM equivalence review in panel for all 21 atoms.

### 6. Doctor update

- Add `FIDELITY-1` check to doctor: fires when a YAML atom's normalized body-text round-trip diverges
  from the pre-migration committed HTML. Severity: ERROR (blocks exit 0).
- Retire the YAML-absent WARNs for this repo's atoms once migration is complete.

## Foundation required

- `memory-structured-source-v1` must be CLOSED (schemas, renderer, doctor STRUCT/SYNC, gate RULE A,
  scaffold, `dadaia migrate memory-yaml` all shipped and in production).

## Acceptance shape (to formalize at SPEC time)

- All 4 schemas enriched with diagram arrays, extensible sections, raw-HTML escape hatch; `additionalProperties: false` preserved.
- Renderer handles enriched schema fields (diagram arrays, extra_sections, raw-HTML).
- `dadaia migrate memory-yaml` extractor produces valid enriched YAML from all 21 atoms without body-text loss.
- FIDELITY-1 check added to doctor; all 21 atoms pass it (round-trip lossless).
- All 21 atoms migrated to YAML-source; `dadaia specs doctor` exits 0 with 0 errors, 0 YAML-absent WARNs.
- Panel renders all 21 atoms without visual regression (product-engineer sign-off).

## Biggest gain

This repo's own memory atoms finally benefit from the atomicity-as-schema guarantee that the v1 machinery
introduced for all new consumer repos. The dogfood is complete; the product eats its own cooking.
