# PLAN — Release: memory-structured-source-v1

**Status:** Aprovado
**Release ID:** memory-structured-source-v1
**Owner:** product-engineer
**Opened:** 2026-05-31

---

## 1. Strategy

Invert memory atom authoring from HTML-first to YAML-first in three additive layers:
schemas (C-1) → renderer (C-2) → doctor rework (C-3). Parallel hardening clusters (C-4
gate, C-5 scaffold, C-7 migrate-guard) can start after C-1 is merged. The 21-atom dogfood
migration (C-6) is strictly last — CLOSURE-only, gated on all prior clusters merged and
`dadaia specs doctor` exit 0.

**Foundation-first hard rule (D-3, locked):** No atom is migrated until the schema
validator and renderer are in production. Migrating before the foundation exists requires
re-migration and creates a window where atoms are YAML but no toolchain supports them.

### Wave structure

```
W1 (foundation):
  C-1 schemas (software-architect design + se-python author)
    └─► W2 starts only after C-1 merged

W2 (parallel after C-1 merged):
  C-2  renderer + dadaia memory render CLI        [se-python]
  C-3a doctor STRUCT-1..STRUCT-4 checks           [se-python, precond C-1]
  C-4  gate RULE A .yaml/.yml extension           [ai-engineer, precond C-1]
  C-5  scaffold HTML→YAML flip                    [ai-engineer + sw-arch validates]
  C-7  dadaia migrate memory-yaml guard           [se-python, precond C-3 WARN text]
  T-DEP jsonschema pyproject.toml add             [se-python]

W3 (after C-2 merged, within W2):
  C-3b doctor SYNC-1 check                        [se-python, precond C-2]

W4 (barrier — all W2+W3 merged):
  devops propagation + gate verification          [devops-engineer]
  qa acceptance gate                              [qa-engineer]

CLOSURE (product-engineer only, after W4 green):
  C-6  21-atom migration                          [product-engineer]
```

Note: C-3 has two internal phases — STRUCT checks (precond C-1, can start W2) and SYNC-1
(precond C-2, sequential within W2). They may be committed separately.

---

## 2. Per-cluster technical approach

### C-1 — Schemas (`dadaia_workspace/public/schemas/memory/`)

Software-architect designs the 4 JSON Schema documents; software-engineer-python authors
the final JSON Schema files + fixtures. Draft-07 is the working assumption (OQ-1; sw-arch
confirms at implementation time for broadest `jsonschema` Python library support).

Key design constraints:
- All 4 schemas: `"additionalProperties": false` at top-level object (D-5 atomicity).
- `memory-product-feature-v1`: all 6 fields in `required` array — `purpose`, `flow_steps`,
  `typical_trigger`, `differential`, `runtime_state`, `dependencies`.
- `memory-product-index-v1`: catalog entry objects carry `rank` (integer, required) and
  `keywords` (array of strings, required) to align with Phase-1 `catalog.json` semantics.
- Fixtures: one valid sample YAML atom per schema type (AC-C1-6) + one invalid atom
  containing `changelog` key per schema type (AC-C1-5). Fixtures live in
  `tests/fixtures/memory/` alongside test files.

Files: `dadaia_workspace/public/schemas/memory/memory-architecture-v1.schema.json`,
`memory-tech-stack-v1.schema.json`, `memory-product-index-v1.schema.json`,
`memory-product-feature-v1.schema.json` (all NEW).

### C-2 — Renderer (`dadaia_workspace/dadaia_workspace/features/specs/renderer.py`)

New module alongside `doctor.py` and `scaffolder.py`. Contract:
- Input: path to `.yaml` atom file + schema type identifier.
- Output: deterministic HTML string from `public/templates/memory-*.html.j2` (4 existing
  templates; templates are NOT modified).
- Must use `yaml.safe_load` (security; SPEC §8).
- `diagram` field in YAML → wrapped in `<pre class="mermaid">…</pre>` + CDN `<script>`.
- Determinism check: same YAML → byte-identical HTML on every run (no timestamps, no
  random values).

CLI: `dadaia memory render <path-to-atom.yaml>` writes adjacent `.html` (same directory,
same stem). Wired via `dadaia_workspace/cli/commands/memory.py` (additive `render`
subcommand; existing `product add` command untouched).

### C-3 — Doctor rework (`dadaia_workspace/dadaia_workspace/features/specs/doctor.py`)

Four additive check IDs (STRUCT-1..STRUCT-4) and one new sync check (SYNC-1). All are
strictly additive — Phase-1's CAT-1 check is already shipped; these new IDs must not
collide with it or any existing check ID. Commit separately from Phase-1 CAT-1 (already in
production).

- **STRUCT-1..STRUCT-4:** When YAML atom present, validate against corresponding schema via
  `jsonschema`. Schema violation = error (exit non-zero). Use `yaml.safe_load`.
- **SYNC-1:** When YAML atom present and passes STRUCT, run renderer and diff output against
  committed HTML. Divergence = WARN (not error; PE may be mid-edit). Must name the specific
  out-of-sync atom(s) in the message.
- **YAML-absent guard:** When no YAML source exists for an atom, skip STRUCT + SYNC with
  WARN: `[WARN] YAML source absent for <atom-path>; schema validation skipped. Migrate
  with: dadaia migrate memory-yaml`. HTML-source consumer repos continue operating; exit 0
  unaffected.
- **Retire check #8 for YAML-present atoms:** When YAML source exists and passes STRUCT,
  skip the `FORBIDDEN_MEMORY_H2_RE` grep on the HTML (structural guarantee supersedes it).
  Check #8 is retained for HTML-only atoms.

### C-4 — Gate extension (`dadaia_workspace/public/scripts/sdd-spec-gate.sh`)

Owner: ai-engineer (exclusive domain of `public/scripts/`). Additive path-pattern only —
no logic change inside the RULE A block. Current pattern:
```
*/specs/memory/*.html|*/specs/memory/*.md|*/specs/memory/product/*.html|*/specs/memory/product/*.md
```
Add `.yaml` and `.yml` variants to both root and `product/` subfolder.

**Cross-owner coordination:** This is the only place where se-python's deliverables (C-1
through C-3) require a corresponding change owned by ai-engineer. Coordinate at TASKS
assignment time. The change must be additive and must NOT collide with R2's RULE E sections
(already shipped in `spec-context-session-locks-v1`) — additive path-pattern only, no
modification of existing conditions.

After authoring: `dadaia public stage && dadaia public install --target all && dadaia public
doctor` (exit 0 required before TASKS for C-4 can be marked `[x]`).

### C-5 — Scaffold flip (`dadaia_workspace/public/scaffold/memory/`)

Owner: ai-engineer (lib-originated scaffold). Software-architect validates YAML stub
content against C-1 schemas before marking `[x]`.

Replace 3 HTML scaffold files with minimal valid YAML stubs:
- `architecture.html` → `architecture.yaml` (valid against `memory-architecture-v1`)
- `tech-stack.html` → `tech-stack.yaml` (valid against `memory-tech-stack-v1`)
- `product/index.html` → `product/index.yaml` (valid against `memory-product-index-v1`)

The HTML files are removed (not merely accompanied). Templates in `public/templates/` are
unchanged. After authoring: propagation + `dadaia public doctor` exit 0.

### C-7 — Migrate guard (`dadaia_workspace/cli/commands/migrate.py`)

Add `memory-yaml` subcommand: guided HTML→YAML per-atom migration. Single-atom mode
(path argument) satisfies AC-C7-2; `--all` batch mode is a convenience (implementation
detail for se-python). Idempotent: second run on same atom is a no-op with warning (AC-C7-4).

The WARN message text from C-3 must include `dadaia migrate memory-yaml` — coordinate C-3
and C-7 implementations so the message text is consistent.

### jsonschema dependency

`jsonschema` must be added to `pyproject.toml` `[tool.poetry.dependencies]`. Confirmed
absent from `pyproject.toml` today — this is the ONLY new PyPI dependency for this release.
`pyyaml` and `jinja2` are already present (verified). Software-engineer-python adds this
before any C-2 or C-3 implementation that imports it.

---

## 3. Dependency map (internal)

```
T-DEP (jsonschema add)
  └─► C-1 (schemas)
        └─► C-2 (renderer)
        │     └─► C-3b (SYNC-1 check)
        └─► C-3a (STRUCT-1..4 checks)
        └─► C-4 (gate RULE A extension)   [ai-engineer]
        └─► C-5 (scaffold flip)           [ai-engineer]
        └─► C-7 (migrate guard, loosely — WARN text from C-3)
              [C-7 depends on C-3 WARN message text being defined]

All of above merged → W4 (devops propagation + qa gate)
W4 green → C-6 (21-atom migration, CLOSURE, product-engineer)
```

---

## 4. Cross-owner coordination

| Coordination point | Who | What |
|---|---|---|
| C-1 schema design | sw-arch → se-python | SW-arch documents field types/constraints; se-python authors JSON Schema files. Handoff: sw-arch signs off fixtures before C-1 merged. |
| C-3 / C-7 WARN text | se-python (C-3) + se-python (C-7) | Same owner; ensure WARN message in doctor matches C-7 command name `dadaia migrate memory-yaml`. |
| C-4 gate + R2 non-collision | ai-engineer + project-manager | C-4 edits RULE A section only. R2's RULE E (session-locks; already shipped) is a different section. PM confirms no overlap at task assignment. |
| C-5 scaffold stubs | ai-engineer + sw-arch | Sw-arch validates YAML stubs against C-1 schemas before C-5 marked `[x]`. |
| C-4 / C-5 propagation | ai-engineer → devops-engineer | After ai-engineer commits C-4 + C-5, devops runs `dadaia public stage && dadaia public install --target all`. W4 devops task wraps this. |

---

## 5. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Renderer non-determinism (timestamps, dict ordering) | Medium | High | AC-C2-4 double-render byte-identity test; use `sort_keys=True` in any serialization. |
| D-4 reformat-baseline one-time diff confuses reviewers | Medium | Low | Document in CLOSURE.md that whitespace-only diff is expected per D-4; one-time baseline commit. |
| C-4 gate change collides with future R2 edits | Low | Medium | R2 (session-locks) is already shipped; no active concurrent RULE E edits. Additive path-pattern mitigates. |
| `jsonschema` version incompatibility with existing Python version | Low | Medium | Pin to `>=4.0` in `pyproject.toml`; run tests before merge. |
| Migration guard WARN promotes false sense of safety for 1000+ consumers | Low | Medium | WARN message includes exact command and deprecation window (3 release cycles). |
| 4 j2 templates already exist — accidental modification | Low | High | SPEC §5 / §6 explicit: templates are NOT modified. Test by checking git diff on `public/templates/` during W4. |
| C-6 migration produces subtle content drift (not just whitespace) | Medium | High | Product-engineer does visual/DOM equivalence review per D-4 before CLOSURE sign-off. |

---

## 6. Validation strategy (→ SPEC §13)

| Gate | What | When |
|------|------|------|
| Schema fixtures | AC-C1-5 (changelog field rejected) + AC-C1-6 (valid atom passes) per all 4 types | C-1 merged |
| Renderer determinism | AC-C2-4: render twice, assert byte-identical | C-2 merged |
| Doctor STRUCT | AC-C3-1/C3-2: invalid YAML → error | C-3a merged |
| Doctor SYNC-1 | AC-C3-3: stale HTML → WARN | C-3b merged |
| Doctor YAML-absent | AC-C3-4: HTML-only atom → WARN not error | C-3a merged |
| Gate regression | AC-C4-1/C4-2/C4-3/C4-4: YAML blocked outside CLOSURE, HTML unchanged | C-4 merged + propagated |
| Scaffold validity | AC-C5-1/C5-2/C5-3: stubs pass schema | C-5 merged + propagated |
| Migrate guard | AC-C7-1/C7-2/C7-3/C7-4 | C-7 merged |
| Full `dadaia specs doctor` exit 0 | AC-DOC-4 / AC-STRUCT-3 | W4 qa gate |
| Panel visual review | AC-C2-5 / AC-C6-6 / AC-REND-3 (D-4) | CLOSURE, product-engineer |

---

## 7. Out of scope (PLAN level)

- Panel view changes (`features/panel/views/memory.py`): no edits.
- `public/templates/memory-*.html.j2`: no edits (renderer consumes as-is).
- `public/plugins/ctx-inject.ts`, `public/scripts/ctx-inject.sh`: Phase-1 assets, not touched.
- `catalog.json` format or generation: Phase-1 asset.
- Agent persona files (`public/agents/*.md`): not touched.

---

*Product Engineer — dadaia-workspace | 2026-05-31*
