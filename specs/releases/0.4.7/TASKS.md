# TASKS — Release: 0.4.7

**Status:** Approved
**Owner:** dd-software-engineer

## Candidate 11 — memory that cannot stack

> T-047-99..102 stay **uncommitted** in the working tree (`specs/memory/**` never in a `Write set:`,
> SPEC-DOC-047): the PM stages their code with the canonical hunk and the ADR 0023 line as ONE commit
> `docs(adr): accept 0023-memory-canon-v7`. Other tasks commit normally, explicit paths, never
> `git add -A`. Ratchets: V35 2,876, V36 31 files / 3,657 lines, doctor module 699 — breach = stop and escalate.

- [x] **T-047-94 — Delete `product add` and the skill-side atom validator (SPEC D5).**
  `_memory_add.py` and `product add` die (an atom generator is the stacking mechanism). `_memory_schema.py`
  keeps `parse`/`find_specs` and loses `validate`; `_memory_check.py` keeps only the generated-pair
  check; `_memory_index.py` folds into `_memory_catalog.py`. Pure deletion first, so V36 never breaches.
  `RED:` `test_slop_ratchets.py::test_v36…` re-pinned down; `tests/unit/skills/test_spec_navigator_memory_script.py`
  — `product add` is an unknown verb, `check` still refuses a catalog that disagrees with the atoms,
  `catalog generate` writes BOTH files.
  `Write set:` `dadaia_workspace/public/skills/dd-spec-navigator/scripts/{memory.py,_memory_schema.py,_memory_check.py,_memory_catalog.py}`,
  deletion of `…/scripts/{_memory_add.py,_memory_index.py}`, `tests/contract/test_slop_ratchets.py`,
  `tests/unit/skills/test_spec_navigator_memory_script.py`
  `blocked by:` — · `delivers:` FR2 (V36 paid)

- [x] **T-047-93 — `sources:` in the schema, the lint and the catalog.**
  `memory-frontmatter-v1` admits `sources` (repo-relative path globs); `features/specs/memory_lint.py`
  requires it on every `product/<area>/<slug>.md` and refuses a glob matching no file under the repo
  root (`Path.glob`, no git); `catalog generate` carries it per feature.
  `RED:` `test_memory_lint.py` — no `sources` errors; a no-match glob errors; a canonical file needs
  none. Catalog test — `sources` per feature.
  `Write set:` `dadaia_workspace/public/schemas/memory/memory-frontmatter-v1.schema.json`,
  `dadaia_workspace/features/specs/memory_lint.py`, `…/dd-spec-navigator/scripts/_memory_catalog.py`,
  `tests/unit/features/specs/test_memory_lint.py`, `tests/unit/skills/test_spec_navigator_memory_script.py`
  `blocked by:` T-047-94 · `delivers:` FR2 (atom sources)

- [x] **T-047-95 — `memory.py drift --since <sha> [--json]`.**
  New sibling `_memory_drift.py` (≤ 85 lines): a pure function of (`catalog.json`, `git diff
  --name-only <sha>..HEAD`, `git ls-files`) listing (a) every atom whose `sources` matched a changed
  path, with the matched paths, (b) every tracked `features/<pkg>/` package and `hooks/*.py` module no
  atom covers. Exit 1 when either list is non-empty. `--since` defaults to the live release's
  `implemented.sha` else `defined.sha`; neither → refusal with a `fix:` naming `--since`.
  `RED:` new `tests/unit/skills/test_memory_drift.py` over a fixture git repo — changed source lists its
  atom with the matched path; uncovered package listed; clean window exits 0; no milestone refuses.
  `Write set:` `…/dd-spec-navigator/scripts/{_memory_drift.py,memory.py}`,
  `tests/unit/skills/test_memory_drift.py`, `tests/contract/test_slop_ratchets.py`
  `blocked by:` T-047-93 · `delivers:` FR2 — **tracer: the operator SEES the live worklist here**

- [x] **T-047-96 — `release.py memory` — the one structured `kind: memory` entry.**
  `release.py memory --since <sha> --worklist <drift.json> --reviewed a,b --changed c,d` appends
  `{ts, agent, kind: "memory", text, since, reviewed, changed}` to the live `log`; refuses a worklist
  atom or package in neither list, a `changed` slug byte-identical to its state at `<sha>`, and any
  phase but `CLOSURE`. `release-state-v1` admits the three fields on a `memory` entry only (P-15). No
  new file (≤ 72 lines across `release.py`, `_release_check.py`, `_release_schema.py`); the worklist
  travels as JSON — scripts never call each other.
  `RED:` `test_release_implementation_release_script.py` — four refusals (uncovered entry, byte-identical
  `changed`, wrong phase, unknown field), one schema-valid append.
  `Write set:` `…/dd-release-implementation/scripts/{release.py,_release_check.py,_release_schema.py}`,
  `dadaia_workspace/public/schemas/releases/release-state-v1.schema.json`,
  `tests/unit/skills/test_release_implementation_release_script.py`, `tests/contract/test_slop_ratchets.py`
  `blocked by:` T-047-95 · `delivers:` FR3 (the entry)

- [x] **T-047-97 — Doctor rule `RELEASE-TREE-MEMORY` (ERROR).**
  In `features/specs/release_tree.py` + its `rules.py` row: a live release in `CLOSURE` whose `log`
  has no `kind: memory` entry stamped after `implemented.ts`, or whose latest such entry lacks
  `since`/`reviewed`/`changed`, is non-conformant; `fix:` names `memory.py drift` then `release.py
  memory`. Reads the state document only — no git in a feature (P-02/P-03).
  `RED:` `test_release_tree.py` — CLOSURE with no entry ERRORs; prose-only entry ERRORs; complete entry
  clean; DEFINITION/IMPLEMENTATION clean.
  `Write set:` `dadaia_workspace/features/specs/{release_tree.py,rules.py}`, `tests/unit/features/specs/test_release_tree.py`
  `blocked by:` T-047-96 · `delivers:` FR3 (the gate)

- [ ] **T-047-98 — `MEM-NARRATIVE-1`: no history line in any memory file.**
  One regex table in `features/specs/memory_lint.py` (LINT-1; `doctor_memory.py` sits at 699): ERROR
  on a body line carrying an ISO date, a `M.m.p` release id, `c[0-9]+`/`rc-[0-9]+`, `T-[0-9]+-[0-9]+`
  or `FR[0-9]+` in ANY memory file, exempting a principle block's `ADR: NNNN (...)` line; and, in a
  product atom only, a history phrase (`operator doctrine|operator decision|operator ruling|closed
  as|died|was deleted|retired|no longer|formerly|previously`). Names the line; code fences exempt.
  `RED:` `tests/unit/features/specs/test_memory_lint.py` — exemptions first (`ADR:` line, code fence),
  then each token class and each phrase, asserting the reported line.
  `Write set:` `dadaia_workspace/features/specs/memory_lint.py`, `tests/unit/features/specs/test_memory_lint.py`
  `blocked by:` — · `delivers:` FR4

- [x] **T-047-99 — `TECHSTACK.md` dies from the canon; the shape test becomes v7.** *(uncommitted)*
  Drop `"TECHSTACK.md"` from `core/workspace_layout.MEMORY_TOPLEVEL_FILES`; follow through `canon.py`,
  `doctor_structural.py` (TREE-3), `memory_canon.py`, `doctor_memory.py`, the schema text. A present
  `memory/TECHSTACK.md` in a v7 tree is a structural finding, `fix:` `specs upgrade`. Rename
  `test_memory_two_tier_shape.py` → `test_memory_canonical_shape.py` and REWRITE it: the three v7
  headings per file in order, every `### P-NN ·` block complete, ids unique, no history heading, fixed blocks.
  `RED:` `tests/contract/test_memory_canonical_shape.py`; TREE-3/canon tests on a v7 tree carrying `TECHSTACK.md`.
  `Write set:` `dadaia_workspace/core/workspace_layout.py`,
  `dadaia_workspace/features/specs/{canon.py,doctor_structural.py,memory_canon.py,doctor_memory.py}`,
  `dadaia_workspace/public/schemas/memory/memory-frontmatter-v1.schema.json`,
  `tests/contract/test_memory_canonical_shape.py` (renamed), `tests/unit/features/specs/**`
  `blocked by:` PLAN A1 (the PM's canonical hunk in the tree) · `delivers:` FR1 (canon + shape)

- [x] **T-047-100 — The bootstrap injects the `## Tech Stack` section, not a digest.** *(uncommitted)*
  `hooks/ctx_inject._build_memory` extracts `ARCHITECTURE.md`'s `## Tech Stack` section (to the next
  `## `) verbatim. `_TECH_STACK_DIGEST_MAX_LINES`, `_digest_tech_stack`'s truncation branch and the
  self-pull pointer are DELETED. Catalog digest untouched; a missing section is fail-open.
  `RED:` `tests/unit/hooks/test_ctx_inject_digest.py` — section verbatim; no pointer string; missing
  section → empty part, no exception.
  `Write set:` `dadaia_workspace/hooks/ctx_inject.py`, `tests/unit/hooks/test_ctx_inject_digest.py`
  `blocked by:` T-047-99 · `delivers:` FR1 (bootstrap)

- [x] **T-047-101 — `specs_pattern_version` 7 and the 6 → 7 upgrade lane.** *(uncommitted)*
  `core.specs_version.CANONICAL_SPECS_VERSION = 7` plus ONE hop in `features/migrate/{registry.py,
  upgrade.py}` (the registry refuses `current < goal` today; never a resurrected chain). The lane
  appends a consumer's `memory/TECHSTACK.md` body under `## Tech Stack` at the end of
  `ARCHITECTURE.md` and deletes the file; a tree still carrying `## Part 1 — Principles` is left
  alone and named by the doctor. P-20 pins `upgrade.py`: re-pin the sha256 in the SAME commit with
  the FR1 justification.
  `RED:` `tests/e2e/features/test_specs_upgrade_e2e.py` — v6 → 7 with the body moved and the file
  gone; a `## Part 1` tree untouched and reported; `tests/contract/test_specs_cli_complexity_ratchet.py`.
  `Write set:` `dadaia_workspace/core/specs_version.py`, `dadaia_workspace/features/migrate/{registry.py,upgrade.py}`,
  `tests/e2e/features/test_specs_upgrade_e2e.py`, `tests/contract/test_specs_cli_complexity_ratchet.py`
  `blocked by:` T-047-99 · `delivers:` FR1 (version + lane)

- [x] **T-047-102 — The scaffold memory law states the two tiers.** *(uncommitted)*
  `public/scaffold/memory/AGENTS.md` becomes the PM's v7 law (3,657 B, cap 4,096); the scaffold drops
  `memory/TECHSTACK.md`; `scaffold/specs/ADRs/AGENTS.md` §5 says "canonical memory statement".
  `RED:` scaffold/canon test — no `TECHSTACK.md` shipped, the projected law states both tiers; `dadaia
  public doctor` clean after `stage`/`install`.
  `Write set:` `dadaia_workspace/public/scaffold/memory/**`, `dadaia_workspace/public/scaffold/specs/ADRs/AGENTS.md`,
  `tests/unit/features/specs/**`
  `blocked by:` T-047-99 · `delivers:` FR1 (scaffold law)

- [x] **T-047-103 — `MEMORY-UPDATE.md` is the reconciliation protocol.**
  Replace wholesale with the PM's draft: drift → per-atom `git diff` → DELETE → UPDATE → ADD → atom
  per uncovered package → `catalog generate` → derived docs in the SAME commit → `release.py memory`.
  `RC-FLOW.md` step 5 names it; `RELEASE-EVENTS.md` documents the `memory` entry shape.
  `RED:` `test_slop_ratchets.py::test_v35…` and the skill cross-reference test — both verbs named, no dangling reference.
  `Write set:` `…/dd-release-implementation/{MEMORY-UPDATE.md,RC-FLOW.md,RELEASE-EVENTS.md}`, `tests/contract/test_slop_ratchets.py`
  `blocked by:` T-047-96, T-047-97 · `delivers:` FR5 (closure law)

- [-] **T-047-104 — `PILLAR-MEMORY.md` §1–§3 rewritten; §3 becomes scored.**
  The PM's draft (66 → 53 lines): §1 every principle's own check over both canonical files; §2 every
  canonical hunk paired with an accepted ADR or an audit text-rewrite commit; §3 scored over
  `memory.py drift` — an atom no `kind: memory` entry names is HIGH, a claim without implementation
  evidence is HIGH — and the only place a canonical file's text is rewritten.
  `RED:` V35 at its re-pinned value; the audit-skill reference test.
  `Write set:` `…/dd-audit-project/PILLAR-MEMORY.md`, `tests/contract/test_slop_ratchets.py`
  `blocked by:` T-047-95 · `delivers:` FR5 (audit pillar)

- [ ] **T-047-105 — Citations follow; V35/V36 re-pinned to measured.**
  Every live `TECHSTACK` citation (skills, personas, `docs/*.md`, `README.md`, `llms.txt`) moves to
  `ARCHITECTURE.md`'s `## Tech Stack`; `dead_citations` and the derived-docs test are the oracle.
  Re-pin V35 and V36 DOWN to measured, arithmetic in the commit body.
  `RED:` `tests/contract/test_docs_derived_from_memory.py`; citation tests; `test_slop_ratchets.py` at the new pins.
  `Write set:` `…/dd-spec-navigator/SKILL.md`, `dadaia_workspace/public/agents/dd-software-engineer.md`, `docs/*.md`,
  `README.md`, `llms.txt`, `dadaia_workspace/features/specs/citations.py`, `tests/contract/test_slop_ratchets.py`,
  `tests/contract/test_docs_derived_from_memory.py`
  `blocked by:` T-047-99, T-047-103, T-047-104 · `delivers:` FR5 (citations + ratchets)

| FR | Tasks |
|---|---|
| FR1 | T-047-99..102 · FR2 | T-047-94, 93, 95 · FR3 | T-047-96, 97 · FR4 | T-047-98 · FR5 | T-047-103..105 · FR6 | closure, no task |
