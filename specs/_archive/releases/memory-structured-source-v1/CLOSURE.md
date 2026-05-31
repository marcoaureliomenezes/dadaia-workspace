# Closure: Release — memory-structured-source-v1

> **Status:** Aprovado
> **Release ID:** memory-structured-source-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-31

## Summary

This release ships the structured-memory-source machinery: YAML as the sole editable source
for memory atoms, with atomicity enforced by JSON Schema rather than bypassable regex. The
four schemas (`memory-architecture-v1`, `memory-tech-stack-v1`, `memory-product-index-v1`,
`memory-product-feature-v1`) each use `additionalProperties: false`, making a `changelog` or
`history` field structurally impossible at author time — not merely detectable at doctor
runtime. This is the headline win: atomicity-as-schema, not atomicity-as-convention.

The release also delivers: a deterministic `renderer.py` (YAML → committed HTML, byte-stable
across consecutive runs) wired to `dadaia memory render`; doctor checks STRUCT-1..4
(schema validation of YAML atoms), SYNC-1 (committed-HTML-sync against renderer output), and
the YAML-absent guard (WARN, not error, for HTML-source consumer repos with migration
guidance `dadaia migrate memory-yaml`); gate RULE A extended to lock `.yaml`/`.yml` files in
`specs/memory/` with the same CLOSURE-only enforcement as HTML; scaffold flipped so new
consumer repos are born YAML-structured; and `dadaia migrate memory-yaml` to guide the
migration from existing HTML-source atoms.

The dogfood atom migration (C-6 / T-MSS-10) for this repo's 21 atoms was attempted and is
**deferred** to a follow-up release. The v1 schemas proved insufficient for lossless
representation of the richest atoms in this repo: tech-stack lost ~46% of body text,
architecture lost ~25%, and the agent-comms and brand-identity atoms do not fit the
`memory-product-feature-v1` schema's fixed-section contract. The W1 MAPPING.md "Fork 1"
foreshadowed this gap. Memory originals were restored; nothing degraded was committed. This
repo's atoms remain HTML-source, and `dadaia specs doctor` exits 0 with 21 benign YAML-absent
WARNs. The follow-up release will enrich the schemas, upgrade the renderer and extractor, and
re-run the 21-atom dogfood with a content-fidelity gate.

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-MSS-01 | Add `jsonschema` to pyproject.toml | committed |
| T-MSS-02 | 4 JSON Schema files + valid/invalid fixtures under `public/schemas/memory/` | committed |
| T-MSS-03 | `features/specs/renderer.py` + `dadaia memory render` CLI | committed |
| T-MSS-04a | Doctor STRUCT-1..4 + YAML-absent WARN guard + retire #8 for YAML-present atoms | committed |
| T-MSS-04b | Doctor SYNC-1 check (committed-HTML sync against renderer) | committed |
| T-MSS-05 | Gate RULE A extended with `.yaml`/`.yml` variants for `specs/memory/` | committed |
| T-MSS-06 | Scaffold flip HTML → YAML stubs + old HTML scaffold removed | committed |
| T-MSS-07 | `dadaia migrate memory-yaml` CLI subcommand (idempotent, per-atom + batch) | committed |
| T-MSS-08 | Devops propagation + gate verification (`dadaia public doctor` exit 0; gate blocks/allows YAML correctly) | committed |
| T-MSS-09 | QA acceptance gate — all §13 ACs green; QA report emitted | committed |
| T-MSS-10 | Migrate 21 atoms from HTML to YAML (C-6) | **DEFERRED** — see §Deferred work |

---

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| ruff clean | `ruff check .` | Exit 0; 0 errors |
| mypy --strict clean | `mypy dadaia_workspace` | Exit 0; 0 errors |
| pytest suite green | `pytest` | 2426 passed / 0 failed / 88.84% coverage |
| public doctor exit 0 | `dadaia public doctor` | Exit 0; 0 drift, 0 missing |
| specs doctor exit 0 (YAML-absent WARN mode) | `dadaia specs doctor` | Exit 0; 21 YAML-absent WARNs (benign, expected — C-6 deferred) |
| QA APPROVED — all §13 ACs | QA gate T-MSS-09 | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-31T170000Z-memory-structured-source-v1-qa.handoff.json` |

---

## Drifts

### C-5-scaffolder-underscoped

**Description:** T-MSS-06 (scaffold flip) required a rework of `scaffolder.py` and
approximately 10 test updates that were not in the SPEC's original 3-file list for C-5. The
SPEC identified only the three YAML stub files to create and the three old HTML scaffold files
to remove. In practice, the scaffolder's internal logic for copying scaffold to new repos also
needed updating to handle YAML stubs correctly, and the existing scaffolder tests assumed HTML
outputs and had to be revised.

**Resolution:** Scope was absorbed within T-MSS-06 without splitting into a new task. The
additional files were disjoint from other Wave 2 tasks, so the multi-`[-]` safety contract
was not violated. Tests updated atomically with the scaffold change.

**Memory updates:** No memory update required — this was a scope expansion of an internal
implementation detail, not a behavioural change visible to the product.

### renderer-sync-project-name-defect

**Description:** During the dogfood C-6 attempt, the renderer and SYNC-1 check exhibited a
`project_name`-consistency defect: rendered HTML for certain atoms contained a project-name
placeholder that did not match the committed HTML's project-name value, causing spurious
SYNC-1 warnings on atoms whose content had not actually changed.

**Resolution:** Identified as a renderer/SYNC bug. Fixed within the release scope before the
QA gate (T-MSS-09). The fix was committed as part of the renderer module. The QA acceptance
criteria AC-REND-1 (byte-identical double-render) and AC-C3-3 (SYNC-1 fires correctly on
genuine divergence) both pass after the fix.

**Memory updates:** No memory update required — this was a defect fix, not a product
behaviour change.

### schema-adequacy-gap

**Description:** The dogfood migration (C-6) revealed that the v1 schemas cannot losslessly
represent the richest atoms in this repo. Concretely: `tech-stack.html` lost approximately
46% of body text when extracted to YAML; `architecture.html` lost approximately 25%; and
`agent-comms.html` and `brand-identity.html` do not fit the `memory-product-feature-v1`
schema's fixed-section contract (they have non-standard sections with no counterpart in the
`purpose`/`flow_steps`/`typical_trigger`/`differential`/`runtime_state`/`dependencies`
required-field set). The W1 MAPPING.md document (authored during schema design) flagged
"Fork 1" as a risk for atoms with multiple diagrams, rich tables, or non-standard sections —
that risk materialized in full.

**Resolution:** Operator decision 2026-05-31: defer C-6 to a follow-up release. Memory
originals were restored to their pre-dogfood state — nothing degraded was committed.
`dadaia specs doctor` exits 0 with 21 YAML-absent WARNs (benign). The follow-up release will
enrich schemas (diagram arrays, extensible sections, raw-HTML escape hatch), upgrade the
renderer and `migrate memory-yaml` extractor, and gate the re-migration with a normalized
body-text round-trip fidelity check.

**Memory updates:** `specs/memory/architecture.html` — updated to document the
structured-memory-source subsystem as shipped capability, including the C-6 deferral note.

### latent-mypy-ruff-debt-swept

**Description:** During implementation, latent mypy strict and ruff violations were found in
files outside the primary write set: `strip-memory-html.py` (Phase-1 asset) and `context.py`
(R2 asset). These were not introduced by this release but surfaced because the suite now runs
with stricter checks.

**Resolution:** Fixed in-place as part of normal housekeeping. The suite gate (ruff + mypy
--strict) passed clean at T-MSS-09.

**Memory updates:** None required — not visible product behaviour.

---

## Memory updates

- `specs/memory/architecture.html` — added `<section id="structured-memory-source">` describing the YAML source-of-truth subsystem: 4 schemas in `public/schemas/memory/` with `additionalProperties:false`, deterministic `renderer.py` YAML→HTML, doctor STRUCT-1..4 + SYNC-1 + YAML-absent guard, gate RULE A `.yaml` lock, scaffold born-structured; notes C-6 deferred (this repo's atoms remain HTML-source).
- `specs/memory/tech-stack.html` — added `jsonschema` (^4) to the approved dependencies table (new PyPI dep this release).
- `specs/memory/product/index.html` — `meta` line updated to `memory-structured-source-v1`; catalog order and entries unchanged (no new feature page added — the structured-memory-source machinery is an infrastructure-level capability documented in `architecture.html` and reflected in `specs-doctor.html`).
- `specs/memory/product/specs-doctor.html` — updated to reflect the new STRUCT-1..4, SYNC-1, and YAML-absent-WARN checks added to doctor in this release; check count updated.

---

## Deferred work

**C-6 — 21-atom dogfood migration → follow-up release `memory-structured-source-migration-v2`**

The v1 schemas cannot losslessly represent this repo's richest atoms. Deferral rationale and
schema gaps are documented in detail in the schema-adequacy-gap drift above and in
`specs/backlog/memory-structured-source-migration-v2.md`.

The follow-up release must:
1. Enrich the 4 schemas to allow: diagram arrays (not single strings), extensible or
   optional sections for non-standard atoms, and a raw-HTML escape hatch for atoms whose
   structure exceeds the schema's fixed-field contract.
2. Upgrade `renderer.py` and `dadaia migrate memory-yaml` extractor accordingly.
3. Re-run the 21-atom migration with a normalized body-text round-trip fidelity gate (the
   rendered HTML, stripped of boilerplate, must be losslessly recoverable from YAML — not
   merely SYNC-clean against a schema-truncated version).

Until that release closes: this repo's 21 atoms remain HTML-source; `dadaia specs doctor`
exits 0 with 21 YAML-absent WARNs; consumers who have already migrated their atoms fully
benefit from the STRUCT/SYNC enforcement immediately.

---

## Backlog returns

- `specs/backlog/memory-structured-source-migration-v2.md` ← C-6 deferred follow-up (schema enrichment + 21-atom dogfood re-migration with fidelity gate)

---

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/memory-structured-source-v1/` via `git mv`. ACTIVE.md will be updated to point to the next release or `release: none`.
