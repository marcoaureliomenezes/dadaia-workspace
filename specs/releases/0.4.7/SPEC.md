# SPEC — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-project-manager
**Opened:** 2026-09-22
**Origin:** backlog:memory-canon-v7
**Consumes:** memory-canon-v7

---

## 1. Problem and context

Candidate 11 — "memory that cannot stack". Operator grill 2026-09-22 (Q1..Q11, frontier
empty; handoff `dd-project-manager-memory-canon-v7-grill`). Measured on 701117fb:

- **Product memory is stale by stacking, not neglect.** All 23 `product/**` atoms were touched
  at the c8, c9 and c10 closures, yet the 2026-09-22 audit found 15 contradicted by the code.
  `MEMORY-UPDATE.md` step 2 reads "apply the candidate's deltas" — an add instruction; no step
  deletes a claim the code no longer supports, none reads the code diff. 38 history-shaped
  lines (dates, candidate ids, "operator doctrine", "died", "closed as") sit inside product
  atoms; the lint forbids only a `History` heading.
- **git diff is nowhere in the mechanism.** `memory.py` has `catalog generate`, `product add`,
  `check`; no verb reads the window's code diff. `PILLAR-MEMORY.md` §3 cross-references atoms
  with code but is unscored and runs "every 5 releases, never mandatory".
- **The memory law contradicts the operator's law.** `specs/memory/AGENTS.md` §2 lets Part 2 of
  `ARCHITECTURE.md`/`TECHSTACK.md`/`QUALITY.md` change "freely at every DEFINITION/CLOSURE".
  `ARCHITECTURE.md` Part 2 is a 40-row table of module paths and a class diagram of one
  feature — the parts that drift every candidate. Ruling: the canonical files change only in
  the commit carrying an accepted ADR; an audit or an explicit operator order may rewrite their
  text, never their statements.
- **TECHSTACK.md is a third canonical file with 12 readers** (`workspace_layout`, `canon`,
  `doctor_structural` TREE-3, `doctor_memory`, `memory_canon`, the frontmatter schema, the
  scaffold, `ctx_inject`'s 24-line digest, three skill/persona documents). Its two principles
  belong elsewhere (P-28 is a test rule, P-30 a release rule); its Part 2 is stack + CI + packaging
  prose.
- **The `kind: memory` closure entry is free prose** — five exist, none names the atoms it
  reviewed in a machine-readable way, so nothing can refuse a closure that reconciled nothing.

## 2. Objective

Make product memory reconcile from the code diff at every closure — delete, update, then add —
under a gate that turns the candidate PR red until it happened; make canonical memory two
ADR-gated files that hold statements, diagrams and laws only.

## 3. Scope (candidate 11)

### FR1 — Memory canon v7: two canonical files, ADR-gated whole

- `specs/memory/` top level is `AGENTS.md`, `ARCHITECTURE.md`, `QUALITY.md`, `product/`.
  `TECHSTACK.md` dies from the canon (`core/workspace_layout.MEMORY_TOPLEVEL_FILES`,
  `features/specs/canon.py`, TREE-3, `memory_canon`, the frontmatter schema text, the scaffold).
- `ARCHITECTURE.md` sections: `## Principles` (every `### P-NN ·` block exactly as today:
  statement, `Measured by:`, `ADR:`, `Rationale:`), `## Tech Stack`, `## Structure`.
  `QUALITY.md` sections: `## Principles`, `## Test architecture`, `## Gates`. The fixed
  `<!-- dadaia:fixed slop-* -->` blocks stay where they are. `tests/contract/test_memory_two_tier_shape.py` is renamed
  `test_memory_canonical_shape.py` and becomes the shape test of this layout (headings, order, every
  principle block complete, ids unique across both files, no history heading).
- `## Tech Stack` is one line per technology, 8 to 15 lines (a soft ceiling: a consumer project
  with a larger stack may exceed it, never with prose): language and build, the runtime
  dependency set, the "everything else is stdlib, no database" statement, external harness
  CLIs never dependencies, the quality toolchain, packaging, and the canonical command block.
- Row map of `TECHSTACK.md` (§2.2 of the memory law: never silently): P-28 → `QUALITY.md
  ## Principles`; P-30 → `ARCHITECTURE.md ## Principles`; Snapshot → `## Tech Stack`; CI fetch
  depth, cache redirection and the closed marker count → `QUALITY.md ## Gates`; packaging and
  the capabilities payload → the `pypi-distribution` atom; the `Dependencies` wikilink line and
  everything else → deleted.
- `ARCHITECTURE.md ## Structure` keeps the layer/ring statements and the `features` package map
  (MEM-DRIFT-1 keeps measuring it; the heading count matches the diagram — 13 packages today);
  the "One decider per fact" table and the SpecsDoctor class diagram are deleted. A row of that
  table survives only as a `P-NN` principle with a real `Measured by:`.
- `hooks/ctx_inject.py` injects the `## Tech Stack` section of `ARCHITECTURE.md` (section
  extraction to the next `## `), never a line-capped digest: `_TECH_STACK_DIGEST_MAX_LINES`,
  the truncation branch and the self-pull pointer are deleted; the catalog digest is unchanged.
- `specs_pattern_version` becomes 7 (`core/specs_version.CANONICAL_SPECS_VERSION`); the
  `specs upgrade` lane for 6 → 7 appends a consumer's `TECHSTACK.md` body under a new
  `## Tech Stack` heading at the end of `ARCHITECTURE.md` and deletes the file (an
  `ARCHITECTURE.md` still carrying `## Part 1 — Principles`/`## Part 2 — Implementation` is
  left for the operator: the doctor names it, the lane never rewrites operator prose). In a v7
  tree a present `memory/TECHSTACK.md` is a structural finding whose fix is `specs upgrade`.
- `specs/memory/AGENTS.md` (scaffold source, projected) states the two tiers: canonical memory
  (the two files, ADR-gated whole; an audit or an explicit operator order may rewrite text
  without changing a statement) and product memory (`product/**`, the only tier a closure
  changes, reconciled delete → update → add). `specs/ADRs/AGENTS.md` §5 says "canonical
  memory statement" where it says "Part-1 principle".
- ADR 0023 is appended `accepted` (grill-born, ruling date 2026-09-22 in `context`) in the same
  commit as the canonical-memory hunk and the code that measures the new shape; the hunk adds
  `P-32` (canonical memory ADR-gated, product memory reconciled delete → update → add) measured
  by the shape test, `RELEASE-TREE-MEMORY` and `MEM-NARRATIVE-1`. The PM hands the engineer the
  two drafted canonical files and the ADR line (scratchpad); the engineer lands them with the code.

### FR2 — Atom sources and the drift worklist

- Every product atom's frontmatter carries `sources:` — a list of repo-relative path globs
  (`dadaia_workspace/features/specs/**`, `dadaia_workspace/hooks/ctx_inject.py`) naming the
  code it describes. `memory-frontmatter-v1` admits the field; the library lint
  (`features/specs/memory_lint.py`, the doctor's LINT-1) requires it on every
  `product/<area>/<slug>.md` and refuses a glob that matches no file under the repo root.
  `catalog.json` carries `sources` per feature (`catalog generate`).
- One validator per fact (D5): the skill script's hand-rolled frontmatter validator
  (`_memory_schema.py` validate half, `_memory_check.py` atom half) is deleted — the library lint
  already owns atom validation; `memory.py check` keeps only the generated-pair check
  (`catalog.json` and `index.md` say what the atoms say).
- `memory.py drift --since <sha> [--json]` (new sibling `_memory_drift.py`) lists, over
  `git diff --name-only <sha>..HEAD` and `git ls-files`: (a) every atom at least one of whose
  sources matched a changed path, with the matched paths; (b) every tracked
  `dadaia_workspace/features/<pkg>/` package and `dadaia_workspace/hooks/*.py` module no atom's
  sources cover. Exit 1 when either list is non-empty. `--since` defaults to the live release's
  latest milestone sha (`implemented.sha`, else `defined.sha`).
- `memory.py product add` is deleted (the add step of a reconciliation writes the atom file;
  the lint validates it); with D5 this pays the V36 lines the drift sibling needs; V36 stays at or
  below 31 files / 3657 lines and is re-pinned down at the end.

### FR3 — The closure gate: one structured `kind: memory` entry

- `release.py memory --since <sha> --worklist <drift.json> --reviewed a,b --changed c,d`
  appends `{ts, agent, kind: "memory", text, since, reviewed: [...], changed: [...]}` to the
  live release's `log` and refuses when any atom or uncovered package of the worklist is in
  neither list, when a `changed` slug's file is byte-identical to its state at `<sha>`, or when
  the release is not in `CLOSURE`. `release-state-v1` admits the three fields on a `memory`
  entry and nothing else (the log-entry shape stays closed, P-15).
- `dadaia doctor` rule `RELEASE-TREE-MEMORY` (ERROR): a live release in phase `CLOSURE` whose
  `log` has no `kind: memory` entry stamped after `implemented.ts`, or whose latest such entry
  lacks `since`/`reviewed`/`changed`, is non-conformant; `fix:` names `memory.py drift` then
  `release.py memory`. The doctor runs in CI on every push and PR, so the candidate PR is red
  until the entry exists.
- SPEC-DOC-047 stays: memory is closure procedure, never a task.

### FR4 — `MEM-NARRATIVE-1`: no history in memory

- `features/specs/memory_lint.py` (the lint the doctor runs in-process as LINT-1) emits ERROR
  `MEM-NARRATIVE-1` on a body line that carries a history token — an ISO date, a `M.m.p`
  release id, a candidate token (`c[0-9]+`, `rc-[0-9]+`), a task id (`T-[0-9]+-[0-9]+`), an
  `FR[0-9]+` id — in ANY memory file, exempting only the `ADR: NNNN (...)` line of a principle
  block; and, in a product atom only, on a line carrying a history phrase (`operator
  doctrine|operator decision|operator ruling|closed as|died|was deleted|retired|no longer|
  formerly|previously`). One regex table, one home; the finding names the line.
- The 38 lines measured on 701117fb are deleted by the closure reconciliation (FR6); the rule is
  green on the closure commit.

### FR5 — Law, skills and audit follow

- `dd-release-implementation/MEMORY-UPDATE.md` is rewritten as the reconciliation protocol:
  `memory.py drift` → per atom, read the matched paths' `git diff` → delete → update → add →
  new atom per uncovered package → `catalog generate` → derived docs re-recorded in the same
  commit → `release.py memory`. `RC-FLOW.md` step 5 names it. `RELEASE-EVENTS.md` documents the
  `memory` entry shape.
- `dd-audit-project/PILLAR-MEMORY.md` §1–§3 are rewritten: §1 runs every principle's check
  over both canonical files; §2 pairs every canonical-file hunk in the window with an accepted
  ADR or an audit text-rewrite commit; §3 is scored — `memory.py drift --since <window start>`
  over the window, every listed atom not named by a `kind: memory` entry is HIGH, every
  functional claim without implementation evidence is HIGH. §3 is also the only place a
  canonical file's text is rewritten, delivered as a statement-by-statement coverage table.
- `dd-spec-navigator/SKILL.md`, `agents/dd-software-engineer.md`, `docs/*.md`, `README.md`,
  `llms.txt` and every other `TECHSTACK` citation follow (`dead_citations` + the derived-docs
  test are the oracle). `CONTEXT.md` carries the six terms (done at the grill).

### FR6 — Acceptance: the candidate's own closure is the first reconciliation

- At closure the protocol of FR5 runs for real over the window `v0.4.6..HEAD`: all 23 atoms
  reconciled delete → update → add against their sources' diff; `brand-identity` deleted; one
  new atom per package the drift verb reports uncovered (today: `capabilities`,
  `certification`, `ci_preflight`, `export`, `import_`, `migrate`, `public` by name-grep — the
  verb decides); `server-registry` describes the live `dd-cli-library/scripts/registry.py`;
  `agent-orchestration`'s tldr names three roles, `workspace-doctor`'s no scores;
  `sdd-bug-backlog-governance` splits by ledger; `context-management` loses its bug history.
- Done when: the `kind: memory` entry covers every worklist entry (drift's exit 1 means
  "there is work"), `dadaia doctor` is clean (`RELEASE-TREE-MEMORY`, `MEM-DRIFT-*`, LINT-1
  with its `MEM-NARRATIVE-1:` history lines), the derived-docs test is green, and `dd-code-reviewer` is `APPROVED` on the sha.

## 4. Out of scope

- The dev-server registry's future (operator decision, separate backlog item).
- Any other product change; onboarding improvements (report §7 candidate "bootstrap que se
  prova"); the promote and PyPI publication.
- Rewriting any consumer workspace's `ARCHITECTURE.md` prose (the upgrade lane moves bytes).

## 5. Decisions and constraints

- D1 ruled 2026-09-22 (Q1–Q11), ADR 0023 grill-born: accepted at append, in FR1's commit.
- D2: no new CLI verb — the mechanism is two skill-script verbs (`memory.py drift`,
  `release.py memory`) and one doctor rule; scripts never call each other, the worklist travels
  as JSON.
- D3: ratchets down only — V34 (SPEC ≤ 24 KiB, TASKS ≤ 12 KiB), V35, V36 paid by `product add`'s
  deletion, doctor module ceiling 699.
- D4: the bug `release-new-refuses-the-stacked-candidate-the-law-requires` is hotfixed outside
  the candidate; candidate 11 is the first born by the verb.
- D5 (PM, from PLAN §5): the skill-script frontmatter validator is a second decider of a fact the
  library lint owns; it dies, the lint gains `sources`, and `memory.py check` validates only the
  generated pair.
- D6 (PM, review H1): release.py memory imports the pure drift function from the sibling skill —
  one decider for the worklist; importing a pure function is not a script calling a script.

## 6. Traceability

| Requirement | Tasks |
|---|---|
| FR1 | T-047-99, T-047-100, T-047-101, T-047-102 |
| FR2 | T-047-93, T-047-94, T-047-95 |
| FR3 | T-047-96, T-047-97 |
| FR4 | T-047-98 |
| FR5 | T-047-103, T-047-104, T-047-105 |
| FR6 | closure procedure, no task (SPEC-DOC-047) |
