# TASKS — Release: memory-structured-source-v1

**Status:** Aprovado
**Release ID:** memory-structured-source-v1
**Owner:** product-engineer
**Opened:** 2026-05-31

> Gate note: Foundation-first sequencing (D-3) is encoded as explicit preconditions below.
> Multi-`[-]` is only allowed when tasks have disjoint write sets (declared per task).
> C-6 is the absolute last task — gated on T-MSS-09 (qa gate) `[x]` AND `dadaia specs doctor` exit 0.
> `specs/memory/AGENTS.md` is NOT migrated in C-6 (directory contract, not an atom).

---

## Wave 1 — Foundation

### T-MSS-01 — Add `jsonschema` to pyproject.toml
- **Owner:** software-engineer-python
- **Cluster:** dependency prerequisite
- **Preconditions:** none
- **Write set:** `repos/dadaia-workspace/pyproject.toml`
- **AC ids:** (enables C-1 fixtures, C-2 renderer, C-3 doctor)
- **Done criterion:** `jsonschema` entry present in `[tool.poetry.dependencies]`; `poetry
  lock` runs without conflict; `pytest` suite still green.
- **Parallelism:** disjoint from all other W1 tasks; may run in parallel with T-MSS-02.
- **Marker:** `[x]`

### T-MSS-02 — Design 4 memory schemas (software-architect) + author JSON Schema files (se-python)
- **Owner:** software-architect (design) + software-engineer-python (authoring)
- **Cluster:** C-1
- **Preconditions:** T-MSS-01 `[x]`
- **Write set:**
  - `repos/dadaia-workspace/dadaia_workspace/public/schemas/memory/memory-architecture-v1.schema.json` (NEW)
  - `repos/dadaia-workspace/dadaia_workspace/public/schemas/memory/memory-tech-stack-v1.schema.json` (NEW)
  - `repos/dadaia-workspace/dadaia_workspace/public/schemas/memory/memory-product-index-v1.schema.json` (NEW)
  - `repos/dadaia-workspace/dadaia_workspace/public/schemas/memory/memory-product-feature-v1.schema.json` (NEW)
  - `repos/dadaia-workspace/tests/fixtures/memory/` (NEW — valid + invalid sample atoms per type)
- **AC ids:** AC-C1-1, AC-C1-2, AC-C1-3, AC-C1-4, AC-C1-5, AC-C1-6
- **Done criterion:** All 4 schema files exist under `dadaia_workspace/public/schemas/memory/`;
  each has `"additionalProperties": false`; `memory-product-feature-v1` has all 6 fields in
  `required`; `memory-product-index-v1` has `rank` + `keywords` as required catalog-entry
  fields; valid fixtures pass schema validation; invalid fixtures (with `changelog` key) fail
  schema validation; software-architect has reviewed and signed off.
- **Parallelism:** blocks all W2 tasks; single task only.
- **Marker:** `[x]`

---

## Wave 2 — Parallel (all precond T-MSS-02 `[x]`)

> Tasks T-MSS-03 through T-MSS-07 may run in parallel after T-MSS-02 is merged.
> They have disjoint write sets. Multi-`[-]` is declared safe across these tasks.

### T-MSS-03 — Implement renderer (`features/specs/renderer.py`) + `dadaia memory render` CLI
- **Owner:** software-engineer-python
- **Cluster:** C-2
- **Preconditions:** T-MSS-02 `[x]`
- **Write set:**
  - `repos/dadaia-workspace/dadaia_workspace/features/specs/renderer.py` (NEW)
  - `repos/dadaia-workspace/dadaia_workspace/cli/commands/memory.py` (additive `render` subcommand)
  - `repos/dadaia-workspace/tests/` (renderer unit tests + determinism fixture)
- **AC ids:** AC-C2-1, AC-C2-2, AC-C2-3, AC-C2-4, AC-C2-6
- **Done criterion:** `renderer.py` exists and is importable; rendering all 4 atom types
  produces expected HTML section IDs; diagram field produces `<pre class="mermaid">` +
  CDN script tag; double-render produces byte-identical output; `dadaia memory render
  <path.yaml>` exits 0 and writes adjacent `.html`; use `yaml.safe_load` throughout.
- **Parallelism:** disjoint from T-MSS-04, T-MSS-05, T-MSS-06, T-MSS-07.
- **Marker:** `[x]`

### T-MSS-04a — Doctor STRUCT-1..STRUCT-4 checks (schema validation of YAML atoms)
- **Owner:** software-engineer-python
- **Cluster:** C-3 (partial — STRUCT only)
- **Preconditions:** T-MSS-02 `[x]`
- **Write set:**
  - `repos/dadaia-workspace/dadaia_workspace/features/specs/doctor.py` (additive STRUCT-1..4 checks + YAML-absent guard)
  - `repos/dadaia-workspace/tests/` (doctor STRUCT unit tests)
- **AC ids:** AC-C3-1, AC-C3-2, AC-C3-4, AC-C3-5
- **Done criterion:** Doctor emits error on YAML atom with extra `changelog` field; doctor
  emits error on YAML atom missing required field; doctor emits WARN (not error) for HTML-
  only atom; doctor skips check #8 when valid YAML present; new check IDs do not collide
  with existing IDs or Phase-1 CAT-1; committed separately from Phase-1 CAT-1 (already
  shipped); uses `yaml.safe_load`; WARN message text includes `dadaia migrate memory-yaml`.
- **Parallelism:** disjoint from T-MSS-03, T-MSS-05, T-MSS-06, T-MSS-07.
- **Note:** T-MSS-04b (SYNC-1) is a separate task that depends on T-MSS-03.
- **Marker:** `[x]`

### T-MSS-05 — Gate RULE A extension for `.yaml`/`.yml` (C-4)
- **Owner:** ai-engineer
- **Cluster:** C-4
- **Preconditions:** T-MSS-02 `[x]`
- **Write set:**
  - `repos/dadaia-workspace/dadaia_workspace/public/scripts/sdd-spec-gate.sh` (additive RULE A path-pattern extension only)
- **AC ids:** AC-C4-1, AC-C4-2, AC-C4-3, AC-C4-4, AC-C4-5
- **Done criterion:** RULE A pattern extended with `*.yaml` / `*.yml` variants for both
  `specs/memory/` root and `specs/memory/product/`; existing HTML/md behaviour unchanged
  (regression); change is additive and does not modify RULE E or any other section;
  confirmed no collision with R2 session-locks RULE E (already shipped); `dadaia public
  stage && dadaia public install --target all` run; `dadaia public doctor` exits 0.
- **Parallelism:** disjoint from T-MSS-03, T-MSS-04a, T-MSS-06, T-MSS-07.
- **Marker:** `[x]`

### T-MSS-06 — Scaffold flip HTML→YAML stubs (C-5)
- **Owner:** ai-engineer (scaffold authoring) + software-architect (YAML stub validation)
- **Cluster:** C-5
- **Preconditions:** T-MSS-02 `[x]`
- **Write set:**
  - `repos/dadaia-workspace/dadaia_workspace/public/scaffold/memory/architecture.yaml` (NEW; replaces `architecture.html`)
  - `repos/dadaia-workspace/dadaia_workspace/public/scaffold/memory/tech-stack.yaml` (NEW; replaces `tech-stack.html`)
  - `repos/dadaia-workspace/dadaia_workspace/public/scaffold/memory/product/index.yaml` (NEW; replaces `product/index.html`)
  - (old HTML scaffold files removed)
- **AC ids:** AC-C5-1, AC-C5-2, AC-C5-3, AC-C5-4, AC-C5-5, AC-C5-6
- **Done criterion:** All 3 YAML stubs exist and validate against their respective C-1
  schemas (sw-arch sign-off); old HTML scaffold files are removed; `dadaia public stage &&
  dadaia public install --target all` run; `dadaia public doctor` exits 0.
- **Parallelism:** disjoint from T-MSS-03, T-MSS-04a, T-MSS-05, T-MSS-07.
- **Marker:** `[x]`

### T-MSS-07 — `dadaia migrate memory-yaml` guard (C-7)
- **Owner:** software-engineer-python
- **Cluster:** C-7
- **Preconditions:** T-MSS-02 `[x]`; coordinate with T-MSS-04a for WARN message text
  (same se-python owner — ensure text is consistent)
- **Write set:**
  - `repos/dadaia-workspace/dadaia_workspace/cli/commands/migrate.py` (additive `memory-yaml` subcommand)
  - `repos/dadaia-workspace/tests/` (migrate CLI unit tests)
- **AC ids:** AC-C7-1, AC-C7-2, AC-C7-3, AC-C7-4
- **Done criterion:** `dadaia migrate memory-yaml` exists and exits 0 on `--help`; running
  it on an HTML-source atom produces a valid YAML file (passes schema validation); WARN
  message in doctor (T-MSS-04a) includes `dadaia migrate memory-yaml`; second run on same
  atom is a no-op with warning (idempotent guard).
- **Parallelism:** disjoint from T-MSS-03, T-MSS-04a, T-MSS-05, T-MSS-06.
- **Marker:** `[x]`

---

## Wave 2 continuation — SYNC-1 (after C-2 merged)

### T-MSS-04b — Doctor SYNC-1 check (committed-HTML sync against renderer)
- **Owner:** software-engineer-python
- **Cluster:** C-3 (SYNC-1 only)
- **Preconditions:** T-MSS-03 `[x]` (renderer must exist before SYNC-1 can invoke it) + T-MSS-04a `[x]`
- **Write set:**
  - `repos/dadaia-workspace/dadaia_workspace/features/specs/doctor.py` (additive SYNC-1 check)
  - `repos/dadaia-workspace/tests/` (SYNC-1 unit tests)
- **AC ids:** AC-C3-3, AC-C3-6
- **Done criterion:** Doctor emits SYNC-1 warn when committed HTML diverges from renderer
  output for a YAML atom that passes STRUCT validation; SYNC-1 names the specific atom(s)
  out of sync; doctor exits 0 when all YAML atoms pass STRUCT + SYNC (no out-of-sync atoms).
- **Parallelism:** single task; sequential after T-MSS-03 + T-MSS-04a.
- **Marker:** `[x]`

---

## Wave 3 — Barrier (all W2 tasks `[x]`)

### T-MSS-08 — Devops propagation + gate verification
- **Owner:** devops-engineer
- **Cluster:** propagation
- **Preconditions:** T-MSS-04b `[x]`, T-MSS-05 `[x]`, T-MSS-06 `[x]` (all lib-originated
  changes committed); T-MSS-03 `[x]`, T-MSS-07 `[x]`
- **Write set:** none (verification only; staging/install commands generate `.dadaia/agentic/`)
- **AC ids:** AC-C4-5, AC-C5-5, AC-GATE-1, AC-GATE-2, AC-GATE-3
- **Done criterion:**
  - `dadaia public stage && dadaia public install --target all` exits 0.
  - `dadaia public doctor` exits 0 (0 drift, 0 missing).
  - Gate blocks a test write to `specs/memory/architecture.yaml` outside CLOSURE phase.
  - Gate allows a test write to `specs/memory/architecture.yaml` in CLOSURE phase.
  - Existing gate HTML behaviour confirmed unchanged (regression check).
  - `git diff HEAD -- dadaia_workspace/public/` shows no uncommitted working-tree drift.
- **Parallelism:** single barrier task.
- **Marker:** `[x]`

### T-MSS-09 — QA acceptance gate
- **Owner:** qa-engineer
- **Cluster:** acceptance
- **Preconditions:** T-MSS-08 `[x]`
- **Write set:** `.dadaia/reports/dadaia-workspace/qa-engineer/` (QA report HTML)
- **AC ids:** all §13 ACs (AC-C1-*, AC-C2-*, AC-C3-*, AC-C4-*, AC-C5-*, AC-C7-*,
  AC-STRUCT-1/2, AC-REND-1/2, AC-DOC-1/2/3, AC-GATE-1/2/3, AC-SCAF-1/2, AC-MIG-1/2)
- **Done criterion:**
  - All schema fixture tests pass (valid atoms pass, `changelog`-field atoms fail).
  - Renderer determinism confirmed (double-render byte-identical output, AC-REND-1).
  - Mermaid diagram field renders correctly (AC-REND-2).
  - Doctor STRUCT/SYNC/WARN checks fire correctly per §13.3 matrix.
  - Gate regression: YAML blocked outside CLOSURE, HTML unchanged (§13.4).
  - Scaffold YAML stubs validate (§13.5).
  - `dadaia migrate memory-yaml` command works end-to-end (§13.6).
  - `dadaia specs doctor` exits 0 on a clean repo (AC-DOC-3 / YAML-absent WARN mode).
  - QA report HTML written to `.dadaia/reports/dadaia-workspace/qa-engineer/`.
- **Parallelism:** single gate task.
- **Marker:** `[x]`

---

## CLOSURE — Product-engineer only

### T-MSS-10 — Migrate 21 atoms from HTML to YAML (C-6) — **DEFERRED** (operator 2026-05-31)

> **DEFERRED to a follow-up release.** The C-6 dogfood revealed the v1 schemas cannot losslessly
> represent this repo's richest atoms (architecture −25%, tech-stack −46% body-text loss; multiple
> diagrams / rich tables / non-standard sections exceed single-value fields). Migrating would corrupt
> memory. Follow-up: enrich schemas → re-extract → migrate. See `specs/backlog/`. Original task spec below.

### T-MSS-10 (original spec) — Migrate 21 atoms from HTML to YAML (C-6) — CLOSURE-ONLY
- **Owner:** product-engineer
- **Cluster:** C-6
- **Preconditions:** T-MSS-09 `[x]` AND `dadaia specs doctor` exits 0 AND ACTIVE.md phase = CLOSURE.
  **This is the absolute last task. It may not start until all prior tasks are `[x]`.**
- **Write set (CLOSURE gate-enforced):**
  - `repos/dadaia-workspace/specs/memory/architecture.yaml` (NEW)
  - `repos/dadaia-workspace/specs/memory/tech-stack.yaml` (NEW)
  - `repos/dadaia-workspace/specs/memory/product/index.yaml` (NEW)
  - `repos/dadaia-workspace/specs/memory/product/<slug>.yaml` × 18 (NEW — all 18 feature atoms)
  - All 21 `specs/memory/**/*.html` (REGENERATED from YAML via `dadaia memory render`)
  - `specs/memory/AGENTS.md` is NOT in scope (directory contract, not an atom; excluded)
- **AC ids:** AC-C6-1, AC-C6-2, AC-C6-3, AC-C6-4, AC-C6-5, AC-C6-6, AC-C6-7,
  AC-STRUCT-3, AC-REND-3, AC-DOC-4
- **Done criterion:**
  - All 21 YAML source files authored and present.
  - All 21 YAML atoms pass STRUCT-1..4 schema validation (no errors).
  - All 21 HTML files regenerated via `dadaia memory render`; SYNC-1 check passes (no
    out-of-sync warnings).
  - `dadaia specs doctor` exits 0 with 0 STRUCT errors and 0 SYNC-1 warnings.
  - Product-engineer visual/DOM equivalence review in panel passed for all 21 atoms (D-4).
  - No YAML atom contains `changelog`, `history`, or `versions` field (D-5 structural
    guarantee confirmed by schema validation).
  - Reformat baseline commit message:
    `chore(memory): migration baseline — YAML source + renderer-generated HTML (Phase 2 dogfood)`
- **Parallelism:** none. Sequential final task. CLOSURE phase only.
- **Marker:** `[ ]`

---

## Task summary

| Task ID | Owner | Cluster | Wave | Marker |
|---------|-------|---------|------|--------|
| T-MSS-01 | se-python | dep | W1 | `[x]` |
| T-MSS-02 | sw-arch + se-python | C-1 | W1 | `[x]` |
| T-MSS-03 | se-python | C-2 | W2 | `[x]` |
| T-MSS-04a | se-python | C-3 STRUCT | W2 | `[x]` |
| T-MSS-04b | se-python | C-3 SYNC-1 | W2 cont | `[x]` |
| T-MSS-05 | ai-engineer | C-4 | W2 | `[x]` |
| T-MSS-06 | ai-engineer + sw-arch | C-5 | W2 | `[x]` |
| T-MSS-07 | se-python | C-7 | W2 | `[x]` |
| T-MSS-08 | devops-engineer | propagation | W3 | `[x]` |
| T-MSS-09 | qa-engineer | acceptance | W3 | `[x]` |
| T-MSS-10 | product-engineer | C-6 | CLOSURE | DEFERRED |

**Total: 11 tasks** — 7 se-python, 2 ai-engineer, 1 devops-engineer, 1 qa-engineer,
1 product-engineer (CLOSURE). (T-MSS-02 is shared sw-arch + se-python.)

---

*Product Engineer — dadaia-workspace | 2026-05-31*
