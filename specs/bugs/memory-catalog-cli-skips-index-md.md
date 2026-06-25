---
name: memory-catalog-cli-skips-index-md
status: Resolved
severity: MEDIUM
reported: 2026-06-25
surface: dadaia memory catalog generate (features/specs/catalog.py)
session_id: null
---

**Symptom:** `dadaia memory catalog generate` regenerates `specs/memory/product/catalog.json` but does NOT regenerate `specs/memory/product/index.md`. As a result, `index.md` silently drifts from the atom frontmatter whenever the CLI path is used at CLOSURE. Observed: after the `pi-fourth-harness-v1` release, `index.md`'s `lifecycle-foundation` row still read "Deterministic Codex lifecycle foundation ... scoped Codex exec." while the atom's frontmatter `tldr` (and the freshly regenerated `catalog.json`) correctly read "Multi-harness procedural lifecycle engine...". Exactly one stale row, undetected by `dadaia specs doctor` (CAT-1 only checks catalog↔atom slug-set parity, not index↔catalog tldr parity).

**Repro:**
1. Edit an atom's `tldr` frontmatter under `specs/memory/product/`.
2. Run `dadaia memory catalog generate --specs-dir specs`.
3. Observe `catalog.json` updates but `index.md` does not.
4. Diff `index.md` table rows against `catalog.json` tldr fields — the edited atom's row is stale.

**Expected:** The canonical CLI catalog command should keep `index.md` in sync with the atoms, the same way the standalone `generate-memory-catalog.py --index-out` script does (`generate_index_md`, lines ~256 and ~340-345). Either the CLI emits `index.md` alongside `catalog.json`, or CLOSURE has a documented step that regenerates `index.md`. Today the standalone script can emit index.md but the CLI (`features/specs/catalog.py`) cannot — divergent surfaces, so the canonical path drifts.

**Notes:**
- Blast radius is human-facing only: the session bootstrap (`hooks/ctx_inject.py`) reads `catalog.json` first and falls back to `index.md` only when catalog is absent, so a stale `index.md` does not poison agent injection — it only misleads humans reading the panel/index.
- Suggested fix surfaces: (a) `features/specs/catalog.py` emits `index.md` from the catalog; and/or (b) add a `dadaia specs doctor` check (e.g. CAT-2) that flags index↔catalog tldr divergence so the drift cannot pass silently.
- Found during the 2026-06-25 memory↔implementation drift audit (`specs/audits/20260625T130028Z-ecddfd86/audit.md`, finding M-4 / M-1).
