# PLAN: v0.1.7 — Constitution v2 + Development Lifecycle Law + Memory Canon

**Status:** Em revisão
**Release ID:** v0.1.7
**Parent program:** v0.2.0 — Agentic Development Lifecycle
**Owner:** product-engineer
**Created:** 2026-06-06

---

## T-017-PRE diagnosis

Performed before authoring any file. Read-only audit of `sdd-gate-v3.md`,
`sdd-bug-backlog-governance.md`, and all other `specs/memory/product/*.md` atoms.

### File → Violation → Fix

| File | Violation | Fix |
|------|-----------|-----|
| `sdd-gate-v3.md` | `summary:` frontmatter block is ~440 chars — exceeds `memory-frontmatter-v1` schema limit of 280 chars | Shorten to ≤280 chars, preserve meaning |
| `sdd-gate-v3.md` | Broken wikilink `[[semaphore-no-liveness-reclaim]]` at line 60 — slug has no corresponding `.md` under `specs/memory/product/`; it is a bug file in `specs/bugs/` | Replace `— ver [[semaphore-no-liveness-reclaim]] em \`specs/bugs/\`` with `— tracked in \`specs/bugs/\`` |
| `sdd-bug-backlog-governance.md` | `summary:` frontmatter block is ~370 chars — exceeds 280 char limit | Shorten to ≤280 chars, preserve meaning |

### Wikilink scan — all other atoms

Scanned all 25 atoms under `specs/memory/product/*.md` for `[[slug]]` wikilinks
that do not resolve to a real `.md` file. Result: **only the one broken link above**
(`[[semaphore-no-liveness-reclaim]]` in `sdd-gate-v3.md`). All other wikilinks in
all other atoms resolve to existing `.md` files in `specs/memory/product/`.

---

## Strategy

This milestone is document-only. No Python, no shell, no CI/CD. Three write targets in
execution order, plus one precondition audit. The strategy is authoring-sequenced:
constitution first (establishes all law), then quality-assurance.md (new memory atom, cites
the constitution it sits under), then index.md update, then doctor-error fixes on existing
atoms.

**Authoring constraint (binding):** `specs/constitution.md` §7 matrix, once committed,
IS the normative source. The consolidated roadmap §1 is supporting context (genesis
traceability), not an acceptance gate. The author must use the roadmap §1 matrix as the
starting point but may make it self-consistent with the rest of the SPEC (e.g. applying
Finding 2 generalization for self-host path). qa-engineer T-017-03 confirms the matrix
is internally self-consistent and that the operator confirms it matches the lived
workflow — not a verbatim diff against the roadmap.

**Gate write permission:** `specs/memory/**` writes in this milestone use the DEFINITION
phase permission established by v0.1.6 (OD-5 resolution). `specs/constitution.md` is not
under `specs/memory/**` and has no gate restriction.

---

## Execution order

```
T-017-PRE  (read-only audit)    → no gate restriction
      ↓
T-017-01   specs/constitution.md
      ↓
T-017-02   specs/memory/product/quality-assurance.md (NEW)
           specs/memory/product/index.md (catalog entry)
           specs/memory/product/test-suite-architecture.md (superseded annotation)
           specs/memory/product/sdd-gate-v3.md (LINT-1 fix)
           specs/memory/product/sdd-bug-backlog-governance.md (LINT-1 fix)
      ↓
T-017-03   qa-engineer gate + operator sign-off (ADDITIVE — evidence only)
```

T-017-PRE and T-017-01 have no inter-task dependency. T-017-02 depends on T-017-01
being committed (quality-assurance.md cites the §7 matrix and §14 roster; those sections
must be committed text before being cited). T-017-03 depends on T-017-01 and T-017-02.

---

## Layers affected

| Layer | File | Change type |
|-------|------|-------------|
| Constitution | `specs/constitution.md` | Major revision — add §7–§14 |
| Memory atom (new) | `specs/memory/product/quality-assurance.md` | Create |
| Memory index | `specs/memory/product/index.md` | Add catalog row |
| Memory atom (annotation) | `specs/memory/product/test-suite-architecture.md` | Add superseded header |
| Memory atom (fix) | `specs/memory/product/sdd-gate-v3.md` | LINT-1 doctor fix |
| Memory atom (fix) | `specs/memory/product/sdd-bug-backlog-governance.md` | LINT-1 doctor fix |
| Evidence (ADDITIVE) | `.dadaia/handoff/dadaia-workspace/` | qa-engineer handoff |

---

## T-017-PRE — Diagnose doctor errors before authoring

This is a prerequisite audit, not a formal task with a marker. The product-engineer reads
the current `dadaia specs doctor` output to identify the exact LINT-1 violations in
`sdd-gate-v3.md` and `sdd-bug-backlog-governance.md` before writing anything. The diagnosis
informs what fixes T-017-02 must apply.

**Method:** read both atom files; inspect frontmatter for missing required fields or extra
fields not in `memory-frontmatter-v1.schema.json`; check `##` headings against the
allowlist; check `[[slug]]` wikilinks for resolution to real `.md` files in
`specs/memory/`. The `lint-memory-atoms.py` script output is the authoritative error list.

**Known issues (from SPEC §3.5 — exact fixes pre-diagnosed):**
- `sdd-gate-v3.md` — two violations:
  1. `summary:` frontmatter too long — shorten to ≤ 280 characters.
  2. Broken wikilink `[[semaphore-no-liveness-reclaim]]` in body — remove and replace
     with plain text `tracked in specs/bugs/`.
- `sdd-bug-backlog-governance.md` — one violation:
  1. `summary:` frontmatter too long — shorten to ≤ 280 characters.
- No other wikilinks in these atoms are broken.

The diagnosis output is used directly in T-017-02's fix. No commit required for this step.

---

## T-017-01 — `specs/constitution.md` authoring approach

**Write target:** `specs/constitution.md` (in-place revision; the file exists).

The author reads the current constitution (6 laws, §1–§6), then appends the 8 new laws
(§7–§14) defined in SPEC §3.1. The existing §1–§6 are NOT changed except:
- §4 Runtime Parity Must Be Honest — update the cross-harness honesty sentence to reflect
  the v0.1.6 gate model (Claude Code = real block; Codex = guardrail trusted-workspace;
  opencode = advisory only). This is a one-sentence update within §4.

**Section authoring order for §7–§14:**

1. §7 Canonical Development Lifecycle — author the 8-row table using consolidated
   roadmap §1 as starting point, incorporating the self-host generalization (Finding 2:
   row 6 "Writes to" covers `repos/<ctx>/` for consumer repos and `dadaia_workspace/**`
   when dadaia-workspace is the bound context). Add the governing-rule sentence below it.
   Add the umbrella-reconciliation sentence (Finding 3: 4-row umbrella maps to phases
   {1-2}/{3-4}/{5,6,8}/{7}). The constitution §7, once committed, is the normative source;
   the roadmap is supporting context only.
2. §8 Concurrency Model — two subsections: ADDITIVE class (paths + behavior), MUTATING
   class (paths + behavior + lease schema from v0.1.6 OQ-1..4).
3. §9 Coordinator + Sub-Agent Architecture — state the PM-holds-one-lease model; PE and
   SE as sub-agents; no second lock; how this prevents cross-phase deadlock.
4. §10 Backlog-Definition Process — 6-step numbered sequence (PM owns; dispatch PE; PE
   sanitizes; PE picks; grill mandatory; SPEC written).
5. §11 Review-Gate Sequence — rc-N: qa→commit, security→push, code-review→PR, PE memory
   after code-review. alpha-N: qa→commit only. Evidence paths. Reject flow.
6. §12 Anti-Slop Law — the three hard rules (phase ownership, GC requirement, single source).
7. §13 Memory Canon — 4 files named explicitly. PE authorship. DEFINITION + CLOSURE write
   permission. No changelog sections. Memory describes current state only.
8. §14 Agent Roster — 9-row table (agent, phase, activity class, lease relationship).
   Plugins paragraph. Persona existence rule.

**Authoring discipline:** each section cites ratified decisions only. If a decision was
not in OQ-1..4 or the v0.2.0/SPEC.md §5 resolved decisions table, it does not go into
the constitution. When in doubt, omit and flag as a decision for the operator.

**Commit:** single commit containing only `specs/constitution.md`. No other files.
Convention: `feat(constitution): v2 — lifecycle law + anti-slop + roster (T-017-01)`.

---

## T-017-02 — Memory atom authoring

Five write targets in one commit (they are logically cohesive and have no ordering
dependency among themselves):

### quality-assurance.md (new)

Author against the 6-section memory atom contract exactly:

**`## Propósito`** — describe the five-layer pytest architecture (unit/contract/integration/
e2e/tmp), the CI 7-job split, and the no-slop policy. State that this atom is the
design-of-record for implementers and qa-engineer. Note that it absorbs
`test-suite-architecture.md`.

**`## Fluxo de uso`** — 5-step numbered sequence:
1. Developer picks the test layer based on what the test exercises.
2. Test receives `@pytest.mark.<layer>` decorator.
3. Local fast path: `pytest -q -m "unit and not slow" tests/unit`.
4. CI runs 7 jobs: lint, typecheck, unit-fast, contract-coverage, integration, e2e-python,
   e2e-panel — each with explicit timeout.
5. One-off debugging goes to `tests/tmp/` with an expiry note.

**`## Trigger típico`** — single sentence: used when implementing a new feature, refactoring
a public contract, reproducing a CI failure, or reviewing test coverage before a gate.

**`## Diferencial`** — without the layer taxonomy: no boundary between fast and slow tests,
local runs slow, coverage inflation hides weak contracts, release-history tests accumulate.
The three failure modes and how the architecture closes each.

**`## Estado runtime tocado`** — list: `pyproject.toml` (pytest config, marker declarations,
coverage redirect), `tests/unit/**`, `tests/contract/**`, `tests/integration/**`,
`tests/e2e/**`, `tests/tmp/**`, `.github/workflows/ci.yml`, `tests/conftest.py`.

**`## Dependências`** — `[[specs-doctor]]`, `[[public-asset-distribution]]`,
`[[agent-comms]]`, `[[sdd-gate-v3]]`.

**Frontmatter:** slug `quality-assurance`, title `quality-assurance`, category `product`,
tldr (one sentence, ≤120 chars), summary (2–3 sentences), tags
`[testing, pytest, ci, quality, test-architecture]`, `agent_tier: self-pull`,
`token_estimate` (estimate from word count × 1.35), `last_updated: 2026-06-06`,
`release_origin: v0.1.7`.

**Forbidden:** no `## Changelog`, `## History`, `## Histórico`, `## Versions`. No
narrative of past versions.

### index.md update

Add a row for `quality-assurance` in the catalog table (or the catalog list, depending
on the current format). The entry must have:
- `slug: quality-assurance`
- `title: quality-assurance`
- `tldr:` matching the atom frontmatter tldr exactly

The entry goes in daily-relevance order. For developers who implement features and run
tests, the quality-assurance atom is high-daily-relevance — insert it near
`test-suite-architecture` (which it supersedes) or in the appropriate position in the
ordered list.

### test-suite-architecture.md annotation

Add a superseded-warning header at the top of the file body (after frontmatter), before
all existing content:

```
> **SUPERSEDED** — Content absorbed into `quality-assurance.md` (v0.1.7).
> This file will be moved to `specs/_archive/legacy-memory/` at v0.2.0 CLOSURE.
> Do not edit. Read `quality-assurance.md` instead.
```

Do NOT change the frontmatter. Do NOT delete the file. Do NOT remove any existing content.

### sdd-gate-v3.md fix

Two mechanical repairs (pre-diagnosed in SPEC §3.5; no T-017-PRE runtime check needed):

1. Shorten the `summary:` frontmatter block to ≤ 280 characters. Current summary is
   a multi-line block that exceeds the `memory-frontmatter-v1` schema limit.
2. In the body (the "Context semaphore" paragraph), find the text
   `— ver [[semaphore-no-liveness-reclaim]] em \`specs/bugs/\`` and replace with
   `— tracked in \`specs/bugs/\``. The slug `semaphore-no-liveness-reclaim` is a
   bug file, not a memory atom; the wikilink is categorically invalid and must be
   removed, not repointed. No content meaning changes.

### sdd-bug-backlog-governance.md fix

One mechanical repair (pre-diagnosed in SPEC §3.5):

1. Shorten the `summary:` frontmatter block to ≤ 280 characters. Current summary is
   a multi-line block that exceeds the `memory-frontmatter-v1` schema limit. Preserve
   the meaning; reduce the word count by tightening phrasing.

**Commit:** single commit containing all five write targets. Convention:
`feat(memory): quality-assurance.md atom + LINT-1 fixes + superseded annotation (T-017-02)`.

---

## T-017-03 — qa-engineer gate + operator validation

**Who:** qa-engineer (ADDITIVE — evidence only; no write to any spec file).

qa-engineer reviews T-017-01 and T-017-02 commits and checks:

1. §7 matrix in constitution is internally self-consistent (8 rows, correct columns,
   self-host path generalization present, umbrella-reconciliation sentence present);
   operator confirms it matches the lived workflow. (The roadmap is supporting context,
   not the gate; no side-by-side diff required.)
2. No new lease mechanics beyond OQ-1..4 ratified in v0.1.6.
3. 9-agent roster is named in §14; each agent has activity class + lease relationship.
4. Sub-agent model stated explicitly: PE and SE do not independently acquire.
5. Evidence convention stated: `.dadaia/handoff/` + `.dadaia/reports/` only; no
   `specs/releases/<id>/evidence/` subtree.
6. `quality-assurance.md` has all 6 required sections with correct names.
7. `quality-assurance.md` frontmatter is valid; no forbidden headings.
8. `dadaia specs doctor` exits 0 (including LINT-1 checks on the fixed atoms).
9. `index.md` catalog entry for `quality-assurance` present and correct.
10. Anti-slop law present and states the three hard rules.
11. Memory canon section names all 4 canon memory AREAS including `quality-assurance.md`.
12. Cross-harness honesty in §4 is updated and accurate.

If any check fails, qa-engineer records the finding in the handoff JSON and the
implementation task is re-opened. The gate must be re-run after the fix.

**Operator validation:** operator reads `specs/constitution.md` and confirms:
- The 8 lifecycle phases match how work actually flows on this instance.
- The 9-agent roster is correct.
- The gate sequence (qa→commit, security→push, code-review→PR) matches how gates run.
- The backlog-definition process matches PM's actual workflow.

Operator sign-off is recorded in the T-017-03 handoff or as a comment in TASKS.md.

**Commit:** `chore(gate): v0.1.7 qa-engineer approval + operator sign-off (T-017-03)`.

---

## Technical risks and mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| §7 matrix introduces internal inconsistency (e.g. missing self-host path, umbrella mismatch) | MEDIUM | qa-engineer confirms internal consistency + operator confirms lived-workflow match; constitution §7 is normative once committed |
| Constitution author adds speculative lease mechanics | HIGH | OQ-1..4 is the hard bound; any addition is flagged by qa-engineer |
| quality-assurance.md frontmatter fails LINT-1 | MEDIUM | Author uses `memory-frontmatter-v1.schema.json` as checklist; LINT-1 is the done criterion |
| Existing atom LINT-1 fixes break atom content | LOW | Fixes are minimum-viable (only the violating element); content meaning unchanged |
| index.md catalog format diverges from existing format | LOW | Author copies the format of an existing entry exactly |
| Constitution §8 cites lease TTL/schema that v0.1.6 changed from design | MEDIUM | Author reads v0.1.6 committed lease.py before writing §8; cites the implementation, not the design proposal |

---

## Validation plan

| Step | Validation | Evidence |
|------|------------|---------|
| T-017-01 commit | `git show HEAD -- specs/constitution.md` shows §7–§14 present | commit SHA |
| T-017-01 commit | §7 matrix rows = 8, self-host path present, umbrella-reconciliation sentence present; §14 roster rows = 9 | qa-engineer count + operator confirmation |
| T-017-02 commit | `dadaia specs doctor` exits 0 | doctor stdout |
| T-017-02 commit | `quality-assurance.md` has all 6 `##` section headings | qa-engineer grep |
| T-017-03 | qa-engineer handoff JSON with `"verdict": "APPROVED"` | `.dadaia/handoff/dadaia-workspace/T-017-03-qa-gate.handoff.json` |
| T-017-03 | Operator sign-off recorded | Comment in TASKS.md or handoff |
