# SPEC — Release: memory-structured-source-v1

**Status:** Aprovado
**Release ID:** memory-structured-source-v1
**Owner:** product-engineer
**Opened:** 2026-05-30
**Semver target:** minor (additive; YAML source + renderer ship as additive layers; HTML
output retained; migration guard protects existing HTML-source consumer repos from hard
errors. Rationale: touches the consumer scaffold but behind a migration guard — additive-
with-guard, not a major break. Same discipline as spec-context-tree-v2's `schema_version`
guard.)
**Sequencing:** Phase 2 of 2. **HARD DEPENDENCY on `memory-context-enforcement-v1` (Phase 1)
being CLOSED first.** Specifically: Phase 1's `catalog.json` and the CAT-1 doctor check must
exist before this release formalizes `rank`/`keywords` into the `memory-product-index-v1`
schema. Phase 1 ships on HTML content; Phase 2 swaps the source format underneath without
changing Phase 1's injection contract.

---

## 1. Problem and context — source inverts data and presentation

dadaia-workspace stores its 21 memory atoms as **hand-authored HTML files**. This inverts
the data/presentation boundary: the format that is inherently a presentation artifact (HTML
for the panel's `memory.py` view) is also the sole editable source. The consequences are
concrete and measurable:

**Atomicity enforcement is bypassable.** `specs doctor` check #8 searches memory HTML files
for `<h2>` headings or `<section>` classes matching "Changelog", "History", "Histórico",
"Versions". This is a heuristic grep. A product-engineer authoring a new atom can bypass it
by using a different heading label, a nested element, or inline text. The atomicity contract
is convention plus a fragile regex — not a structural guarantee.

**Authoring burden is high.** New dadaia-workspace users inherit via `public/scaffold/memory/`
HTML files they must hand-author. HTML is not ergonomic for multi-paragraph prose, ordered
lists, or Mermaid diagrams embedded in text. The j2 templates in `public/templates/` exist
as scaffolding aids but are not enforced on the authoring path; atoms drift from the template
structure silently.

**Doctor heuristics accumulate.** Checks #8, #10, #11 each parse HTML to detect structure
problems that would be impossible if the source were schema-validated. Each heuristic carries
a false-positive risk and a maintenance surface.

**The format the panel cares about (HTML) and the format humans and agents care about for
authoring (structured text with schema guarantees) are the same file.** When they should not
be.

**The fix:** invert the layering. A schema-validated YAML file becomes the sole editable
source. A deterministic renderer (`features/specs/renderer.py`) converts YAML → committed
HTML. The panel (`features/panel/views/memory.py`) continues serving the committed HTML
unchanged. Memory read-side (injection, catalog, agents) continues using the committed HTML
unchanged. Phase 1's injection contract is not touched.

**Primary sources consumed:**

- Backlog candidate: `specs/backlog/memory-structured-source-v1.md`
- Phase-1 backlog (boundary): `specs/backlog/memory-context-enforcement-v1.md`
- Operator grill-me session 2026-05-30 (5 locked decisions — see §3)

---

## 2. Objective

Make memory atom authoring **structured, schema-validated, and ergonomic** by:

1. Defining 4 JSON Schema files for the 4 atom types — atomicity is encoded as
   `additionalProperties: false`, making a changelog field **structurally impossible**, not
   bypassable by heuristic.
2. Shipping a deterministic Python renderer (`features/specs/renderer.py`) that converts YAML
   atoms to HTML byte-stably, so committed HTML stays current and `git diff` across a CLOSURE
   is meaningful.
3. Reworking `specs doctor` to validate YAML against schema and to check that committed HTML
   is in sync with the current YAML — replacing the heuristic checks that become redundant
   once the source is structured.
4. Extending RULE A in `sdd-spec-gate.sh` to also lock `.yaml` and `.yml` files under
   `specs/memory/` — the gate must protect the new editable source format at the same level
   it protects HTML.
5. Flipping `public/scaffold/memory/` to ship YAML so new consumer repos are born structured
   rather than inheriting the HTML-authoring burden.
6. Migrating this repo's 21 atoms from HTML to YAML as a dogfood CLOSURE deliverable
   (product-engineer only, CLOSURE phase, after C-1..C-5 are complete).
7. Adding a `dadaia migrate` guard so the 1000+ existing consumer installs encounter a loud
   warning (WARN not error) rather than silent breakage when they first encounter the new
   checks.

All deliverables are sequenced behind a **foundation-first hard rule (D-3)**: schemas and
renderer ship before any atom migration occurs.

---

## 3. Locked operator decisions (grill-me 2026-05-30 — do not re-open)

| # | Decision | Rationale |
|---|----------|-----------|
| D-1 | **HTML retained as a generated artifact.** The structured YAML file is the sole editable source. The panel (`features/panel/views/memory.py`) stays unchanged and serves the committed generated HTML. | Panel serving is a solved problem; replacing it would widen the blast radius with zero user-visible gain. HTML stays committed for git browsability and panel parity. |
| D-2 | **Format = YAML, one file per atom.** Decisive factors: multi-line prose via block scalars, git-diff ergonomics for the CLOSURE review gate, inline comments documenting the atomicity contract. JSON loses on prose/diffs. The catalog stays JSON (Phase 1 owns it). | Operator made this call directly. YAML block scalars handle multi-paragraph prose and Mermaid diagram sources without escaping; JSON does not. The catalog (`catalog.json`) is machine-generated and stays JSON. |
| D-3 | **Foundation-first (hard rule).** Schemas + renderer ship as additive phases BEFORE migrating any atom. Migrating before the foundation exists = build-on-stale-layers (migrate twice). This is an explicit sequencing constraint enforced in TASKS.md ordering. | Architect's single strongest recommendation. If atom migration (C-6) runs without a working renderer, atoms must be re-migrated after C-1/C-2 land. The cost is not just rework — it is a period where atoms are YAML but no validator or renderer exists, causing `specs doctor` failures. |
| D-4 | **Renderer acceptance bar = visual/DOM equivalence, not strict byte-identity against hand-authored HTML.** The renderer emits clean canonical HTML. Migration accepts a one-time whitespace-only git diff across migrated atoms (a "reformat baseline" commit). Acceptance is validated as rendered-DOM/visual equivalence in the panel, not `diff == empty`. Going forward the deterministic renderer keeps committed HTML byte-stable across subsequent CLOSURE runs. The backlog's loose phrase "byte-identity preserved" is refined here: it means the renderer is deterministic (same YAML → same HTML on every run), not that the initial migration produces zero diff against hand-authored HTML, which is brittle and infeasible. | Operator decision, grill-me 2026-05-30. Hand-authored HTML has accumulated inconsistent whitespace, attribute ordering, and style variations. Requiring zero diff against that baseline would force the renderer to replicate formatting bugs. |
| D-5 | **Atomicity becomes a structural guarantee, not a regex.** All 4 schemas use `additionalProperties: false` so a `changelog` / `history` / `versions` field is structurally impossible to author — replacing the current bypassable `specs doctor` grep-for-"Changelog" heuristic. This is the headline win of Phase 2. | Operator's explicit consolidation goal. A schema rejection is a hard author-time error; a grep check fires at doctor runtime and can be bypassed. Structural enforcement is categorically stronger. |

---

## 4. Scope clusters

### C-1 — Schema design (4 atom types)

**What this is:** Four JSON Schema files defining the structure and required fields of each
memory atom type. Schemas live in `dadaia_workspace/public/schemas/` alongside the existing
`handoff-v1.schema.json` (confirmed: this is the only schema in that directory today).

**Proposed location:** `dadaia_workspace/public/schemas/memory/` (new subdirectory;
implementation-confirmed by software-architect before creating).

**Four schema files:**

| Schema ID | File | Governs |
|-----------|------|---------|
| `memory-architecture-v1` | `memory-architecture-v1.schema.json` | `specs/memory/architecture.yaml` |
| `memory-tech-stack-v1` | `memory-tech-stack-v1.schema.json` | `specs/memory/tech-stack.yaml` |
| `memory-product-index-v1` | `memory-product-index-v1.schema.json` | `specs/memory/product/index.yaml` |
| `memory-product-feature-v1` | `memory-product-feature-v1.schema.json` | `specs/memory/product/<slug>.yaml` |

**Schema design constraints:**

- `additionalProperties: false` on all four schemas — this is D-5 (atomicity structural
  guarantee). A YAML atom cannot contain a `changelog`, `history`, or `versions` field;
  the schema rejects it at validation time.
- `memory-product-feature-v1` required fields introduce **structural completeness
  enforcement (net-new)**: `specs doctor` today enforces atomicity via check #8
  (`FORBIDDEN_MEMORY_H2_RE` changelog grep) but does NOT check for section completeness.
  The schema adds that guarantee — all 6 fields below are `required`, making a missing
  section a schema-validation error rather than a silent omission. Additionally,
  `additionalProperties: false` replaces the check #8 heuristic for YAML-source atoms (D-5):
  - `purpose` — maps to `<h2>Propósito</h2>` (`#purpose`)
  - `flow_steps` — maps to `<h2>Fluxo de uso</h2>` (`#flow`); typed as an array of strings
  - `typical_trigger` — maps to `<h2>Trigger típico</h2>` (`#trigger`)
  - `differential` — maps to `<h2>Diferencial</h2>` (`#differential`)
  - `runtime_state` — maps to `<h2>Estado runtime tocado</h2>` (`#runtime-state`)
  - `dependencies` — maps to `<h2>Dependências</h2>` (`#dependencies`)
- `memory-product-index-v1` catalog entries carry `rank` (integer, required) and `keywords`
  (string array, required). These are the fields Phase 1's `catalog.json` generator consumes
  from `product/index.html` today — formalizing them in the schema closes the loop between
  Phase 1 and Phase 2. The `rank` field encodes daily-relevance ordering (same semantics as
  Phase 1's `catalog.json` `rank` field).

**Files changed (lib-originated — edit source, then `dadaia public stage && dadaia public install`):**

| File | Change |
|------|--------|
| `dadaia_workspace/public/schemas/memory/memory-architecture-v1.schema.json` | **NEW** |
| `dadaia_workspace/public/schemas/memory/memory-tech-stack-v1.schema.json` | **NEW** |
| `dadaia_workspace/public/schemas/memory/memory-product-index-v1.schema.json` | **NEW** |
| `dadaia_workspace/public/schemas/memory/memory-product-feature-v1.schema.json` | **NEW** |

**Owner:** software-architect (schema design) + software-engineer-python (JSON Schema
authoring, format validation, cross-check against existing doctor checks).

**Acceptance criteria:**

- AC-C1-1: All 4 schema files exist under `dadaia_workspace/public/schemas/memory/`.
- AC-C1-2: Each schema has `"additionalProperties": false` at the top-level object definition.
- AC-C1-3: `memory-product-feature-v1` schema has all 6 fields as `required`: `purpose`, `flow_steps`, `typical_trigger`, `differential`, `runtime_state`, `dependencies`.
- AC-C1-4: `memory-product-index-v1` schema has `rank` (integer) and `keywords` (array of strings) as `required` fields on each catalog entry object.
- AC-C1-5: A YAML atom with a `changelog` or `history` key fails schema validation when validated against its corresponding schema.
- AC-C1-6: A valid sample YAML atom for each of the 4 types passes schema validation (regression fixture provided by software-architect alongside schema files).

---

### C-2 — Renderer (`features/specs/renderer.py`)

**What this is:** A new Python module `dadaia_workspace/dadaia_workspace/features/specs/renderer.py`
that converts a YAML memory atom (validated against its schema) into the committed HTML file
served by the panel. This module joins the existing `features/specs/doctor.py` and
`features/specs/scaffolder.py` (both confirmed present at that path).

**Renderer contract:**

- Input: path to a `.yaml` atom file + its schema type identifier.
- Output: deterministic HTML string rendered from the canonical j2 templates in
  `dadaia_workspace/public/templates/memory-*.html.j2` (confirmed present:
  `memory-architecture.html.j2`, `memory-tech-stack.html.j2`,
  `memory-product-index.html.j2`, `memory-product-feature.html.j2`).
- **Deterministic:** same YAML → same HTML on every invocation. No timestamps, no random
  UUIDs, no environment-dependent output. This is the guarantee that keeps committed HTML
  byte-stable after the initial migration baseline commit.
- **Mermaid support:** a YAML atom may contain a `diagram` field with a Mermaid diagram
  source (block scalar). The renderer wraps it in `<pre class="mermaid">…</pre>` and
  ensures the CDN `<script>` tag is present in the rendered HTML. This replaces the
  current manual Mermaid embedding in hand-authored HTML.
- Acceptance per D-4: rendered-DOM / visual equivalence in the panel, not zero diff
  against hand-authored source.

**CLI wiring:** A `dadaia memory render` command (or equivalent — exact CLI design is
implementation-led) invokes the renderer on a given YAML atom and writes the committed
HTML adjacent to it. Product-engineer calls this during CLOSURE after editing a YAML atom.

**Files changed:**

| File | Change |
|------|--------|
| `dadaia_workspace/dadaia_workspace/features/specs/renderer.py` | **NEW** |
| `dadaia_workspace/cli/commands/memory.py` | Add `render` subcommand wiring (additive; existing `product add` command unchanged) |

**Owner:** software-engineer-python.

**Acceptance criteria:**

- AC-C2-1: `dadaia_workspace/dadaia_workspace/features/specs/renderer.py` exists and is importable.
- AC-C2-2: Rendering a valid `memory-product-feature-v1` YAML atom produces HTML containing `<section id="purpose">`, `<section id="flow">`, `<section id="trigger">`, `<section id="differential">`, `<section id="runtime-state">`, `<section id="dependencies">`.
- AC-C2-3: Rendering a YAML atom containing a `diagram` field produces HTML with `<pre class="mermaid">` wrapping the diagram source and a `<script src=` CDN tag in the output.
- AC-C2-4: Rendering the same YAML atom twice produces byte-identical HTML output (determinism check).
- AC-C2-5: The rendered HTML for each of the 4 atom types passes visual/DOM equivalence review in the panel (product-engineer sign-off at CLOSURE).
- AC-C2-6: `dadaia memory render <path-to-atom.yaml>` exits 0 and writes/updates the adjacent `.html` file.

---

### C-3 — Doctor rework

**What this is:** Replace the heuristic HTML-parse checks in `dadaia_workspace/dadaia_workspace/features/specs/doctor.py`
with schema-based validation and a committed-HTML-sync check. Three concrete changes:

**(a) Schema validation of YAML atoms (new check STRUCT-1..STRUCT-4):**
When a YAML atom is present at `specs/memory/<type>.yaml` or `specs/memory/product/<slug>.yaml`,
the doctor validates it against the corresponding schema. A schema violation is an **error**
(blocks `dadaia specs doctor` exit 0). Field missing = error; extra field = error (because
`additionalProperties: false`).

**(b) Committed-HTML-sync check (new check SYNC-1):**
When a YAML source exists, the doctor runs the renderer on the YAML and compares the output
to the committed HTML (`specs/memory/<type>.html` or `specs/memory/product/<slug>.html`).
If they differ, doctor warns (WARN not error, because the product-engineer may be mid-edit
between running the renderer and committing). The SYNC-1 message must identify the specific
atom(s) out of sync. This check catches stale committed HTML — the scenario where a YAML
atom is edited but `dadaia memory render` is not run before commit.

**(c) Migration guard (YAML-absent fallback):**
When NO YAML source exists for an atom (the atom is still in the HTML-source state, as is
true for all existing consumer repos at the time Phase 2 ships), the new STRUCT and SYNC
checks are **skipped with a WARN** (not an error). The WARN message reads: `[WARN] YAML
source absent for <atom-path>; schema validation skipped. Migrate with: dadaia migrate
memory-yaml`. This is the same fail-safe discipline as spec-context-tree-v2's
`schema_version: 1` guard. HTML-source consumer repos continue operating with their existing
doctor checks (check #8 remains for HTML-only repos); they get deprecation warnings, not
hard errors.

**(d) Retire heuristics when YAML present:**
When a YAML source exists and passes STRUCT validation, check #8 (the grep-for-changelog
heuristic on the HTML) is redundant — the schema already enforces it structurally. Doctor
will skip #8 for atoms that have a corresponding valid YAML source.

**Files changed:**

| File | Change |
|------|--------|
| `dadaia_workspace/dadaia_workspace/features/specs/doctor.py` | Add STRUCT-1..STRUCT-4 + SYNC-1 checks; add YAML-absent guard; retire #8 for YAML-present atoms |

**Owner:** software-engineer-python.

**Acceptance criteria:**

- AC-C3-1: `dadaia specs doctor` emits an error on a YAML atom with an extra `changelog` field (schema validation fires: `additionalProperties: false`).
- AC-C3-2: `dadaia specs doctor` emits an error on a YAML atom missing a required field (e.g. `purpose` absent from a `memory-product-feature-v1` atom).
- AC-C3-3: `dadaia specs doctor` emits SYNC-1 warn when committed HTML diverges from renderer output for a YAML atom that passes schema validation.
- AC-C3-4: `dadaia specs doctor` emits a WARN (not error) for an atom where no YAML source exists — HTML-source consumer repos do not break.
- AC-C3-5: `dadaia specs doctor` skips check #8 (changelog grep) for atoms where a valid YAML source is present (redundancy elimination).
- AC-C3-6: `dadaia specs doctor` exits 0 on a fully-migrated repo where all YAML atoms are valid and all committed HTML files are in sync with their YAML source.

---

### C-4 — Gate + write-lock extension (RULE A)

**What this is:** Extend RULE A in `dadaia_workspace/public/scripts/sdd-spec-gate.sh` to
also lock `specs/memory/**/*.yaml` and `specs/memory/**/*.yml` files. When YAML becomes the
editable source (C-6 migration), the gate must protect it with the same CLOSURE-only
restriction it applies to HTML atoms. Without this extension, a non-PE agent could edit a
YAML source outside CLOSURE, bypassing the atomicity contract on the source side.

**Scope of change (additive only):** RULE A's current pattern (confirmed in source):
```
*/specs/memory/*.html|*/specs/memory/*.md|*/specs/memory/product/*.html|*/specs/memory/product/*.md
```
The extension adds `*.yaml` and `*.yml` variants to both memory root and product/ subfolder.
Generated HTML stays committed AND write-locked (build artifact; only the renderer writes it
in CLOSURE via `dadaia memory render`). The logic inside the RULE A block is unchanged;
only the path pattern gains two new glob alternatives.

**Cross-owner flag:** `sdd-spec-gate.sh` lives in `dadaia_workspace/public/scripts/`, which
is ai-engineer's exclusive domain (lib-originated assets). This cluster is the only place in
this release where software-engineer-python's deliverables (C-1..C-3) require a corresponding
change owned by ai-engineer. This must be explicitly coordinated at PLAN time — ai-engineer
implements C-4; software-engineer-python implements C-1..C-3.

**Files changed (lib-originated):**

| File | Change |
|------|--------|
| `dadaia_workspace/public/scripts/sdd-spec-gate.sh` | Extend RULE A path pattern with `*.yaml` / `*.yml` for both `specs/memory/` root and `specs/memory/product/` |

After authoring:
```
dadaia public stage && dadaia public install --target all
dadaia public doctor   # must exit 0
```

**Owner:** ai-engineer (exclusive owner of `public/scripts/`).

**Acceptance criteria:**

- AC-C4-1: A Write attempt on `specs/memory/architecture.yaml` outside CLOSURE phase is blocked by the gate with the same `[SDD GATE] memory/ é atômico…` message as HTML edits.
- AC-C4-2: A Write attempt on `specs/memory/product/some-feature.yaml` outside CLOSURE phase is blocked.
- AC-C4-3: RULE A allows `specs/memory/architecture.yaml` writes when `ACTIVE.md` phase = `CLOSURE`.
- AC-C4-4: Existing RULE A behaviour for `*.html` and `*.md` files is unchanged (regression: blocked outside CLOSURE, allowed in CLOSURE).
- AC-C4-5: `dadaia public doctor` exits 0 after propagation (no drift, no missing).

---

### C-5 — Scaffold + templates flip

**What this is:** Two coordinated changes so new consumer repos are born structured:

**(a) Scaffold flip (`public/scaffold/memory/`):**
Replace the three existing HTML scaffold files with YAML equivalents:
- `public/scaffold/memory/architecture.html` → `public/scaffold/memory/architecture.yaml`
  (minimal valid `memory-architecture-v1` atom stub)
- `public/scaffold/memory/tech-stack.html` → `public/scaffold/memory/tech-stack.yaml`
  (minimal valid `memory-tech-stack-v1` atom stub)
- `public/scaffold/memory/product/index.html` → `public/scaffold/memory/product/index.yaml`
  (minimal valid `memory-product-index-v1` atom stub)
New consumer repos initialized via `dadaia init` or `dadaia context create` receive YAML
stubs. They use `dadaia memory render` to generate their first committed HTML.

**(b) Templates now consumed by renderer:**
The j2 templates in `public/templates/memory-*.html.j2` (confirmed present: 4 files) do not
change their content. What changes is the authoritative consumer: previously, product-engineer
was guided to "render from canonical templates" manually; now the renderer (`features/specs/renderer.py`)
is the canonical consumer. The templates remain in `public/templates/` unchanged; the
scaffold is what ships to new repos.

**Files changed (lib-originated):**

| File | Change |
|------|--------|
| `dadaia_workspace/public/scaffold/memory/architecture.html` | **REPLACE** with `architecture.yaml` stub |
| `dadaia_workspace/public/scaffold/memory/tech-stack.html` | **REPLACE** with `tech-stack.yaml` stub |
| `dadaia_workspace/public/scaffold/memory/product/index.html` | **REPLACE** with `index.yaml` stub |

**Owner:** ai-engineer (lib-originated scaffold) + software-architect (validates YAML stub
structure against C-1 schemas).

**Acceptance criteria:**

- AC-C5-1: `dadaia_workspace/public/scaffold/memory/architecture.yaml` exists and is valid against `memory-architecture-v1` schema.
- AC-C5-2: `dadaia_workspace/public/scaffold/memory/tech-stack.yaml` exists and is valid against `memory-tech-stack-v1` schema.
- AC-C5-3: `dadaia_workspace/public/scaffold/memory/product/index.yaml` exists and is valid against `memory-product-index-v1` schema.
- AC-C5-4: The old `architecture.html`, `tech-stack.html`, `product/index.html` scaffold files are removed (not merely accompanied by YAML; the REPLACE is complete).
- AC-C5-5: `dadaia public doctor` exits 0 after propagation.
- AC-C5-6: A new workspace initialized with `dadaia init` (or equivalent scaffolding) receives YAML atoms, not HTML scaffold files, in `specs/memory/`.

---

### C-6 — Migrate this repo's 21 atoms (dogfood, CLOSURE deliverable)

**What this is:** The product-engineer CLOSURE deliverable for this release. Convert all 21
memory atoms in `repos/dadaia-workspace/specs/memory/` from hand-authored HTML to YAML
source, then run the renderer to produce the new committed HTML baseline. This cluster
**MUST** happen after C-1..C-5 are complete (foundation-first, D-3).

**Note:** `specs/memory/AGENTS.md` is a directory contract for agents (not a memory atom)
and is **excluded from migration**. `dadaia specs doctor` exempts it from SPEC-DOC-002L and
it does not require a YAML counterpart.

**Migration sequence:**
1. For each atom, author the YAML source file (e.g. `architecture.yaml` alongside
   `architecture.html`). Validate against the corresponding schema (STRUCT check passes).
2. Run `dadaia memory render <atom.yaml>` to regenerate the committed HTML.
3. Review the one-time whitespace diff (reformat baseline per D-4). The panel renders
   correctly (visual/DOM equivalence review by product-engineer).
4. Remove the hand-authored HTML source (keep only the renderer-generated HTML as the
   committed artifact). The YAML is now the sole editable source.

**Atom inventory (21 atoms — confirmed by Phase-1 inventory):**

| Location | Type |
|----------|------|
| `specs/memory/architecture.yaml` | `memory-architecture-v1` |
| `specs/memory/tech-stack.yaml` | `memory-tech-stack-v1` |
| `specs/memory/product/index.yaml` | `memory-product-index-v1` |
| `specs/memory/product/<slug>.yaml` (18 feature atoms) | `memory-product-feature-v1` |

`specs/memory/AGENTS.md` is NOT in this inventory — it is a directory contract, not an atom.

**Reformat baseline commit:** A single commit containing all 21 YAML sources + all 21
regenerated HTML files is acceptable (D-4). The commit message convention:
`chore(memory): migration baseline — YAML source + renderer-generated HTML (Phase 2 dogfood)`.

**Owner:** product-engineer (CLOSURE phase only; write gate enforces this).

**Acceptance criteria:**

- AC-C6-1: `specs/memory/architecture.yaml` and `specs/memory/tech-stack.yaml` exist and pass STRUCT-1/STRUCT-2 validation.
- AC-C6-2: `specs/memory/product/index.yaml` exists and passes STRUCT-3 validation.
- AC-C6-3: All 18 feature YAML atoms exist and pass STRUCT-4 validation.
- AC-C6-4: All 21 committed HTML files are regenerated from YAML via the renderer (SYNC-1 check passes for all atoms).
- AC-C6-5: `dadaia specs doctor` exits 0 with no STRUCT errors and no SYNC-1 warnings.
- AC-C6-6: The panel renders all 21 atoms without visual regressions (product-engineer sign-off, visual equivalence per D-4).
- AC-C6-7: No changelog/history content exists in any of the 23 migrated YAML atoms (structural guarantee D-5).

---

### C-7 — `dadaia migrate` guard + consumer deprecation window

**What this is:** A loud, visible guard for the 1000+ existing consumer installs so they
encounter a WARN with actionable instructions rather than silent breakage when they first
upgrade to a version of dadaia-workspace that ships the new YAML checks. Mirrors the
`spec-context-tree-v2` / `session-locks` `schema_version` guard discipline.

**Guard design:**
- The `dadaia migrate memory-yaml` CLI command (implemented in the existing
  `dadaia_workspace/cli/commands/migrate.py` — confirmed present) guides existing consumers
  through the per-atom HTML → YAML migration.
- The guard message (WARN, not error) that doctor emits when YAML is absent (C-3 item c)
  includes the exact command: `dadaia migrate memory-yaml`. This is actionable.
- Deprecation timeline: 3 release cycles (approximately 3 months from this release's
  CLOSURE). After that, the WARN may be promoted to an error in a separate release (not
  this one).
- Consumer documentation: `public/scaffold/memory/AGENTS.md` or a `migrate.md` note — exact
  form is implementation-led.

**Files changed:**

| File | Change |
|------|--------|
| `dadaia_workspace/cli/commands/migrate.py` | Add `memory-yaml` subcommand: guided HTML→YAML migration per-atom |
| `dadaia_workspace/dadaia_workspace/features/specs/doctor.py` | (already covered in C-3) YAML-absent guard emits `dadaia migrate memory-yaml` in WARN message |

**Owner:** software-engineer-python + devops-engineer (consumer communication).

**Acceptance criteria:**

- AC-C7-1: `dadaia migrate memory-yaml` exists as a CLI command and exits 0 on a help invocation.
- AC-C7-2: Running `dadaia migrate memory-yaml` on an HTML-source atom produces a valid YAML file (passes schema validation) in the same directory as the HTML file.
- AC-C7-3: The WARN message emitted by doctor (C-3 item c) includes the text `dadaia migrate memory-yaml` to guide operators.
- AC-C7-4: The migration command does not overwrite an existing `.yaml` file (idempotent guard — run twice, second run is a no-op with a warning).

---

## 5. Out of scope

The following are explicitly NOT in scope for this release:

**Phase 1 deliverables (owned by `memory-context-enforcement-v1`):**
- Memory injection / blindness fix (`ctx-inject.sh` payload extension)
- `catalog.json` generation and the CAT-1 doctor check
- "Step 0 — Memory bootstrap" block in agent personas
- `specs/memory/AGENTS.md`
- Codex `memory-ctx` universal adapter

**Content changes:**
- No new memory content is authored in this release. C-6 migrates existing atoms to YAML
  but does not change their content (propósito, fluxo, trigger, diferencial, etc. are
  unchanged; they are transcribed from HTML to YAML verbatim).

**Panel UI:**
- No changes to `features/panel/views/memory.py` or any panel view. The panel serves the
  committed generated HTML unchanged.

**Catalog format:**
- `catalog.json` stays JSON. Phase 1 owns it. Phase 2 does not change the catalog format.

**Breaking changes:**
- No breaking changes to any consumer. The migration guard (C-7) ensures existing HTML-
  source repos get WARN, not error. A future major version may promote WARN to error.

---

## 6. Architecture deltas

All changes are additive or guarded replacements. No existing public assets are removed
without replacement.

| Asset type | Path | Change |
|-----------|------|--------|
| JSON Schema (lib-originated) | `dadaia_workspace/public/schemas/memory/memory-architecture-v1.schema.json` | **NEW** |
| JSON Schema (lib-originated) | `dadaia_workspace/public/schemas/memory/memory-tech-stack-v1.schema.json` | **NEW** |
| JSON Schema (lib-originated) | `dadaia_workspace/public/schemas/memory/memory-product-index-v1.schema.json` | **NEW** |
| JSON Schema (lib-originated) | `dadaia_workspace/public/schemas/memory/memory-product-feature-v1.schema.json` | **NEW** |
| Python module | `dadaia_workspace/dadaia_workspace/features/specs/renderer.py` | **NEW** |
| Python CLI | `dadaia_workspace/cli/commands/memory.py` | Add `render` subcommand (additive) |
| Python CLI | `dadaia_workspace/cli/commands/migrate.py` | Add `memory-yaml` subcommand (additive) |
| Python doctor | `dadaia_workspace/dadaia_workspace/features/specs/doctor.py` | Add STRUCT-1..STRUCT-4 + SYNC-1; YAML-absent guard; retire #8 for YAML-present atoms |
| Shell script (lib-originated) | `dadaia_workspace/public/scripts/sdd-spec-gate.sh` | Extend RULE A pattern with `.yaml` / `.yml` variants |
| Scaffold (lib-originated) | `dadaia_workspace/public/scaffold/memory/architecture.html` | **REPLACED** by `architecture.yaml` |
| Scaffold (lib-originated) | `dadaia_workspace/public/scaffold/memory/tech-stack.html` | **REPLACED** by `tech-stack.yaml` |
| Scaffold (lib-originated) | `dadaia_workspace/public/scaffold/memory/product/index.html` | **REPLACED** by `index.yaml` |
| Consumer memory (CLOSURE) | `repos/dadaia-workspace/specs/memory/architecture.yaml` | **NEW** (PE, CLOSURE) |
| Consumer memory (CLOSURE) | `repos/dadaia-workspace/specs/memory/tech-stack.yaml` | **NEW** (PE, CLOSURE) |
| Consumer memory (CLOSURE) | `repos/dadaia-workspace/specs/memory/product/index.yaml` | **NEW** (PE, CLOSURE) |
| Consumer memory (CLOSURE) | `repos/dadaia-workspace/specs/memory/product/<slug>.yaml` (×18) | **NEW** (PE, CLOSURE) |
| Consumer memory (CLOSURE) | All 21 `specs/memory/**/*.html` | **REGENERATED** from YAML via renderer (PE, CLOSURE) |
| Manifest | `.dadaia/agentic/manifest.json` | Updated by `dadaia public stage` to track new lib-originated assets |

**No changes to:**
- `public/templates/memory-*.html.j2` (templates unchanged; renderer consumes them as-is)
- `public/plugins/ctx-inject.ts` (Phase 1 asset, not touched)
- `public/scripts/ctx-inject.sh` (Phase 1 asset, not touched)
- `public/agents/*.md` (agent personas not touched in Phase 2)
- `features/panel/views/memory.py` (panel serving unchanged)
- `catalog.json` format or generation (Phase 1 asset, not touched)
- `spec_contexts.json` schema (no state model changes)

---

## 7. Tech-stack deltas

| Item | Delta |
|------|-------|
| Python `jsonschema` (PyPI) | Required by `features/specs/renderer.py` and doctor STRUCT checks for JSON Schema validation of YAML atoms. **This is the only new PyPI dependency.** software-architect must verify it is not already present in `pyproject.toml` before adding it; if already present, no change. |
| Python `pyyaml` (PyPI) | Required for YAML parsing in renderer + doctor. Verify presence in `pyproject.toml` before adding (likely already present given the stack). |
| Python `jinja2` (already used by `features/specs/doctor.py` — confirmed in import list) | Renderer uses Jinja2 to render `memory-*.html.j2` templates. No new dependency. |
| JSON Schema (draft-07 or 2020-12) | Schema files use a stable draft. software-architect selects the draft version at implementation time (recommendation: draft-07 for broadest tooling compatibility). |
| Shell (bash) | Gate RULE A pattern extension. No new shell tools required. |
| No other new PyPI dependencies | All other implementation in Python + Bash (existing stack). |

---

## 8. Security and operations deltas

- **No security surface change.** This release adds schema validation of YAML files and a
  YAML→HTML renderer. Neither introduces network access, credential handling, or new
  execution surfaces.
- **YAML parsing and `yaml.safe_load`:** The renderer and doctor must use `yaml.safe_load`
  (PyYAML), not `yaml.load` (unsafe). This is a standard Python security practice that
  prevents arbitrary object deserialisation from YAML inputs. software-engineer-python must
  enforce this in implementation.
- **Scaffold replacement:** The scaffold HTML files are replaced by YAML stubs. Consumer
  repos running `dadaia init` after this release ships will receive YAML stubs. This is a
  forward-only change; existing consumer repos are unaffected by the scaffold change (the
  migration guard handles their transition).
- **Gate extension (C-4):** Extending RULE A to cover `.yaml` and `.yml` files narrows the
  write surface (additional protection), not widens it. No new security exposure.

---

## 9. Memory files affected at CLOSURE

At CLOSURE of this release, the following memory atoms must be updated. C-6 covers all
content migrations; the list below identifies the atoms whose textual content changes in
this release:

- `specs/memory/architecture.yaml` → `specs/memory/architecture.html` (REGENERATED) — add
  description of the YAML source-of-truth layer: schemas, renderer, migration guard, RULE A
  extension.
- `specs/memory/tech-stack.yaml` → `specs/memory/tech-stack.html` (REGENERATED) — add
  `jsonschema` and `pyyaml` to the approved dependencies section if they are new additions.
- `specs/memory/product/index.yaml` → `specs/memory/product/index.html` (REGENERATED) —
  update catalog to include a new feature entry for the memory-structured-source capability
  if the operator decides it warrants a standalone feature page; update `rank` ordering if
  changed.
- All 18 feature YAML atoms → regenerated HTML (content unchanged; format migrated).

Files that need no CLOSURE content update (structural migration only):
- All 18 feature HTML atoms: content is transcribed verbatim from HTML to YAML and back
  through the renderer. The content does not change; only the source format does.

---

## 10. Implementer ownership

| Cluster | Implementer | Work |
|---------|-------------|------|
| C-1 Schema design | **software-architect** (design) + **software-engineer-python** (JSON Schema authoring + fixtures) | 4 schema files + validation fixtures |
| C-2 Renderer | **software-engineer-python** | `renderer.py` + `dadaia memory render` CLI subcommand |
| C-3 Doctor rework | **software-engineer-python** | STRUCT-1..STRUCT-4 + SYNC-1 checks; YAML-absent guard; retire #8 for YAML-present atoms |
| C-4 Gate extension | **ai-engineer** (EXCLUSIVE owner of `public/scripts/`) | RULE A pattern extension in `sdd-spec-gate.sh` |
| C-5 Scaffold + templates | **ai-engineer** (scaffold, lib-originated) + **software-architect** (YAML stub validation) | Replace HTML scaffold with YAML stubs |
| C-6 Atom migration (dogfood) | **product-engineer** (CLOSURE phase only) | YAML authoring for 21 atoms; renderer execution; reformat baseline commit |
| C-7 Migrate guard | **software-engineer-python** (`migrate.py`) + **devops-engineer** (consumer communication) | `dadaia migrate memory-yaml` command |
| Propagation verification | **devops-engineer** | Verify lib-originated changes propagated (`dadaia public doctor` exit 0); confirm gate blocks YAML edits outside CLOSURE |
| Acceptance validation | **qa-engineer** | Schema fixtures pass/fail validation; renderer determinism; gate regression; doctor checks; visual panel review of migrated atoms |

**Sequencing within the release (hard — D-3 enforcement):**

1. C-1 (schemas) must be complete and merged before C-2 (renderer) begins. Renderer
   references schema IDs; authoring without schemas creates an untestable target.
2. C-2 (renderer) must be complete before C-3 (doctor SYNC-1 check) can be implemented.
   The SYNC-1 check invokes the renderer internally.
3. C-3, C-4, C-5, C-7 can run in parallel after C-1 is complete.
4. C-6 (atom migration) is the final step. It requires ALL of C-1..C-5 to be merged and
   `dadaia specs doctor` to exit 0 before product-engineer begins migration in CLOSURE.
5. devops-engineer propagation verification runs after all ai-engineer work is committed
   and staged (C-4, C-5).

---

## 11. Dependencies and sequencing

### 11.1 Release dependencies

**Hard dependency (external):** `memory-context-enforcement-v1` (Phase 1) MUST be CLOSED
before this release enters the IMPLEMENTATION phase. The specific requirement:
- Phase 1's `catalog.json` generator must exist (`features/specs/catalog.py`) because
  Phase 2's `memory-product-index-v1` schema formalizes the `rank` and `keywords` fields
  that Phase 1 consumes from HTML today. Implementing Phase 2 schemas without Phase 1's
  catalog code would leave the field semantics unverified against the real consumer.
- Phase 1's CAT-1 doctor check must be in production so that Phase 2's SYNC-1 and STRUCT
  checks build on a doctor baseline that already validates catalog coherence.

**No other blocking external dependencies.** Phase 2 is otherwise self-contained.

### 11.2 Internal sequencing (foundation-first, D-3)

```
C-1 (schemas)
  └─► C-2 (renderer)  ─► C-6 (atom migration — CLOSURE only)
       └─► C-3 (doctor SYNC-1)
C-1 ─► C-3 (doctor STRUCT checks — parallel to C-2)
C-1 ─► C-4 (gate extension — parallel)
C-1 ─► C-5 (scaffold stubs — parallel)
C-7 (migrate guard) — depends on C-3 WARN message text; otherwise parallel
```

No atom migration (C-6) until C-1..C-5 are all complete. This is the foundation-first
constraint. It is enforced in TASKS.md ordering.

### 11.3 Write-set disjointness from other active releases

At the time of SPEC authoring, other in-flight or recently active releases include
`spec-context-session-locks-v1`, `panel-kanban-v1`, `go-open-source`. The write sets are:

- `spec-context-session-locks-v1` — `core/models/`, `infrastructure/`, `features/spec_context/service.py`, `sdd-spec-gate.sh` (session enforcement sections only), `sdd-post-gate.sh`. **Potential conflict on `sdd-spec-gate.sh`**: both this release (C-4, RULE A extension) and session-locks (RULE E authoring) touch `sdd-spec-gate.sh`. These are strictly additive, non-overlapping sections of the file. They must not land in the same commit; ordering is: session-locks section first (already likely shipped), then RULE A extension. Sequencing responsibility: software-architect or project-manager at PLAN time.
- `panel-kanban-v1` — panel frontend assets only. Zero overlap.
- `go-open-source` — all code complete. Zero overlap.
- Shared `features/specs/doctor.py` surface: C-3 adds STRUCT-1..STRUCT-4 + SYNC-1 checks; Phase 1 (C-2) adds CAT-1 check. These are strictly additive. Must not land in the same commit; ordering: Phase 1 CAT-1 first (enforced by the Phase 1 CLOSURE dependency), then Phase 2 STRUCT/SYNC.

---

## 12. Open questions

### OQ-1 — JSON Schema draft version

**Question:** Should the 4 memory schemas use JSON Schema draft-07 (broadest `jsonschema`
Python library support) or JSON Schema 2020-12 (latest standard)?

**Working assumption:** draft-07, for maximum compatibility with the Python `jsonschema`
library without requiring the `jsonschema[format-annotations]` extra. software-architect
confirms at C-1 implementation time.

**Impact if changed:** Schema files are internal to the library; draft version is not
consumer-visible beyond the `$schema` URI in each file. Low impact.

### OQ-2 — Renderer output: write-adjacent or write-to-committed-path?

**Question:** When `dadaia memory render <atom.yaml>` runs, should it write the HTML
to the same directory as the YAML (adjacent: `specs/memory/architecture.yaml` →
`specs/memory/architecture.html`) or should the HTML path be configurable?

**Working assumption:** adjacent (same directory, same stem, `.html` extension). This
matches the existing HTML atom locations and keeps the renderer invocation simple. The CLI
design is implementation-led; devops-engineer confirms the exact output path convention.

### OQ-3 — `dadaia migrate memory-yaml` scope: per-atom or batch?

**Question:** Should `dadaia migrate memory-yaml` operate on one atom at a time (pass a
path argument) or batch-migrate all atoms in a `specs/memory/` directory?

**Working assumption:** both modes — path argument for single-atom, `--all` flag for
directory-wide batch. Implementation detail is software-engineer-python's call. AC-C7-2 is
satisfied by single-atom mode; batch mode is a convenience.

### OQ-4 — Feature atom count (23 vs actual) — **RESOLVED**

**Resolved:** 21 total (3 structural: `architecture`, `tech-stack`, `product/index` + 18
feature). Confirmed by Phase-1 inventory via `ls specs/memory/product/*.html` (excludes
`index.html`) = 18 files. `specs/memory/AGENTS.md` is a directory contract, NOT an atom
(doctor exempts it from SPEC-DOC-002L; not migrated to YAML).

---

## 13. Acceptance criteria summary

### 13.1 Structural guarantee (primary operator bar — D-5)

- AC-STRUCT-1: A YAML atom containing a `changelog` field fails schema validation. `dadaia specs doctor` exits non-zero. Atomicity is structurally enforced.
- AC-STRUCT-2: All 4 schema files exist in `dadaia_workspace/public/schemas/memory/` and are valid JSON Schema documents.
- AC-STRUCT-3: All 21 migrated YAML atoms in this repo pass schema validation (no STRUCT errors in `dadaia specs doctor`).

### 13.2 Renderer determinism

- AC-REND-1: `dadaia memory render <atom.yaml>` produces byte-identical output on two consecutive runs (determinism).
- AC-REND-2: Mermaid diagram source in a YAML atom is wrapped in `<pre class="mermaid">` in rendered HTML with CDN script tag present.
- AC-REND-3: Visual/DOM equivalence in the panel confirmed by product-engineer for all 21 migrated atoms (D-4 sign-off).

### 13.3 Doctor health

- AC-DOC-1: SYNC-1 triggers when committed HTML diverges from renderer output for a YAML atom.
- AC-DOC-2: STRUCT checks trigger on invalid YAML (missing required field, extra field).
- AC-DOC-3: YAML-absent guard emits WARN (not error) for HTML-source repos — `dadaia specs doctor` exits 0 for an unmigraded consumer repo.
- AC-DOC-4: `dadaia specs doctor` exits 0 on this repo after C-6 is complete.

### 13.4 Gate enforcement

- AC-GATE-1: RULE A blocks `specs/memory/architecture.yaml` write outside CLOSURE.
- AC-GATE-2: RULE A allows `specs/memory/architecture.yaml` write in CLOSURE phase.
- AC-GATE-3: Existing RULE A HTML behaviour is unchanged (regression).

### 13.5 Scaffold

- AC-SCAF-1: New consumer repo initialized after this release ships has `specs/memory/architecture.yaml` (not `architecture.html`) from scaffold.
- AC-SCAF-2: Scaffold YAML stubs pass schema validation for their respective types.

### 13.6 Migration guard

- AC-MIG-1: `dadaia migrate memory-yaml` exists and produces a valid YAML atom from an existing HTML atom.
- AC-MIG-2: The WARN message in `dadaia specs doctor` for YAML-absent atoms includes `dadaia migrate memory-yaml`.

---

*Product Engineer — dadaia-workspace | 2026-05-30*
