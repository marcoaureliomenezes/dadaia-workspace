# SPEC — Release v0.12.0 — backlog-tooling-single-source

**Status:** Aprovado
**Approval provenance:** operator-delegated approval, 2026-08-15 (goal directive)
**Release ID:** v0.12.0
**Owner:** product-engineer
**Opened:** 2026-08-15
**Created:** 2026-08-15
**Branch:** `feature/v0.12.0` (cut from `develop` at `523f0d8d`; branch contract: `dadaia-gitflow`)
**Consumes:** backlog-tooling-reconciliation, backlog-md-physical-consolidation
**Picked set:** two backlog entries (#30, #31 in `specs/backlog/candidates.md`), both
**pre-approved intake** — the operator's D-A ratification at the v0.10.0 approval, recorded
as P-1/P-2 and materialized at the 2026-08-15 intake round (`candidates.md`, fifth-pass
addendum). Entry #30 additionally carries intake report #2 item **2-2**, approved **as a
merge** into it. **No bug is picked, because there is no open bug**: the ledger carries
**zero** open bugs (the two v0.9.0-window LOWs were closed by `hotfix/0.7.1`, merged at
`d15bdf4e`). **No audit is outstanding** — both 2026-07 audits were archived fully
dispositioned by v0.8.0. Pick-time priority (`DADAIA.md` §5) is satisfied with nothing
outranking.
**Grill (mandatory, done):** `specs/releases/v0.12.0/GRILL.md` — fifteen refinement problems
(P1–P15) resolved; ADRs **D1–D10** are binding and settled and are **not re-litigated here**.
Two open decisions are flagged there (**OD-1**, **OD-2**) and recorded in §7.

---

## 1. Problem and context

v0.10.0 shipped the ADR #14 doctrine: the backlog is one document,
`specs/backlog/BACKLOG.md`, with an `ACTIVE` section of live candidates and a `LEDGER`
section of one line per closed item. The law says it (`DADAIA.md` §5 Backlog), the canonical
skill says it (`dd-backlog-definition` §2), and the memory atom says it
(`sdd-bug-backlog-governance`). **None of it exists on disk, and none of the tooling
implements it.**

**The drift is now three-layered.**

*Layer one — the physical shape.* `specs/backlog/` holds 31 live per-entry `.md` files plus
a hand-maintained `candidates.md` index with 25 candidate rows, 5 idea rows, a 20-line
LEDGER, three terminal tables and a history table. Every curation touch pays a double
write, and the index has already drifted from the files it indexes: 31 files against 30 rows
(grill P6).

*Layer two — the tooling.* Five `features/backlog/*` modules, both `backlog` CLI verbs, the
pre-commit gate and the CI job read and write the per-entry model end to end. The skill that
defines the target schema has to carry a "tooling note" telling readers not to treat the
shipped CLI as schema authority. A validator that validates a retired model is not a
backstop; it is a second opinion nobody asked for.

*Layer three — a required protocol step with no executor (the folded intake item 2-2).*
`dd-release-definition` §5 requires a `**Consumes:**` declaration and ticks it on the
protocol checklist. Its producer, `features/backlog/removal_lifecycle.py`, has **no
production caller**: the former caller was the workflow engine deleted in v0.3.0, which
explicitly *kept* the module. Neither does `consumes.py`, `ledger_writer.py`,
`removal.py`, nor `container.build_backlog_removal_lifecycle` (grill P1). Worse, the
module's defined behaviour — rewrite an item down to its residual, or archive-then-unlink it
— **contradicts the never-delete law** it was built to serve: under the single-source model
an item never leaves the file, it moves `ACTIVE` → `LEDGER`.

**Why now.** R6 of the v0.10.0 SPEC named the risk when it deferred the work: the doctrine
outruns the tooling and every cycle widens the gap. Two cycles have passed. The consolidation
cannot happen first (the doctors would reject the new document); the tooling cannot be
pointed at a document that does not exist. The two entries are one piece of work, and the
operator ratified them as one release.

---

## 2. Objective

`specs/backlog/BACKLOG.md` becomes the physical single source of the backlog, and every
tool that reads or writes the backlog reads and writes **it** — validated by the same four
BL-* codes, gated by the same pre-commit chokepoint and the same CI job, with the same
severities. In the same pass the dead removal/consumption write side is deleted rather than
resurrected, and the one release-definition step that pointed at it is rewritten to the
mechanism that actually runs.

Ownership is split by artifact class (`DADAIA.md` §2): `software-engineer` owns the
production Python, the CLI, the doctors and the tests; `project-manager` owns the document
consolidation (curation judgment over `specs/backlog/**`); `ai-engineer` owns the two skill
files; `product-engineer` authors this definition and the closure. No agent writes outside
its lane.

---

## 3. Scope

**Standing scope rule for every zero-hit acceptance criterion in this SPEC (grill P13, the
2-8 lesson).** Every grep-based criterion is evaluated over the working tree **excluding**
`specs/_archive/**`, `specs/bugs/**`, `specs/backlog/_archive/**`, `CHANGELOG.md` and
`specs/releases/v0.12.0/**` — this release's own documents must quote the symbols they
retire.

**Standing green rule (ADR D1).** `dadaia backlog doctor` and `dadaia specs doctor` are
green at **every** commit of this release. The old shape is validated by the old tooling
before the cutover commit and the new shape by the new tooling after it; there is no
intermediate state and no dual-shape reader anywhere in the tree.

**Standing ownership rule.** A task's write set never crosses a lane boundary except in the
one dual-owner cutover task (T-120-08), which is sequenced inside a single commit precisely
so that no cross-lane *intermediate* state exists.

---

### FR1 — A pure document model for `BACKLOG.md`

A new pure module `dadaia_workspace/features/backlog/document.py` parses
`specs/backlog/BACKLOG.md` into a typed model, with all roots injected and no I/O outside
the supplied path (the `features/backlog/**` purity rule the package already holds).

The document has exactly two sections. `## ACTIVE` holds one `### <slug>` subsection per
live item, with the ratified `dd-backlog-definition` §2 keys —
`**Title:**`, `**Opened:**` (`YYYY-MM-DD`), `**Status:**`, `**Description:**`,
`**Provenance:**` — plus **one optional key**, `**Intents:**`, carrying the existing typed
YAML block in a fenced code span (ADR D7, grill P2). `## LEDGER` holds one line per closed
item in the §2 grammar `<slug> · <disposition> · <release-or-reason> · <date>`.

Parsing is diagnostic, never throwing: a malformed subsection, an unparseable intents block
and an ungrammatical LEDGER line are each **captured** on the model as a located error
(section, slug, line number), exactly as `preview.BacklogItem` captures `intents_error` /
`frontmatter_error` today, so the doctor reports instead of crashing.

**Acceptance**

- A1.1 A well-formed document with N ACTIVE subsections and M LEDGER lines parses to N items
  and M rows, preserving slug, title, opened, status, description, provenance and source line
  number for each.
- A1.2 An absent `BACKLOG.md` yields an empty model, not an error (a context with no backlog
  is legitimate — the consumer-scaffold case).
- A1.3 A subsection missing any of the five required keys yields a located error naming the
  slug and the missing key; parsing continues to the next subsection.
- A1.4 An `**Intents:**` block that is not valid YAML, or is structurally invalid as
  `intents[]`, yields a located error and leaves that item's intents empty — it never raises.
- A1.5 A LEDGER line that does not match the four-field `·` grammar, or whose disposition is
  outside the six canonical tokens (`DELIVERED`, `SUPERSEDED`, `RESOLVED`, `CONSUMED`,
  `DEFERRED`, `REJECTED`), yields a located error naming the line number.
- A1.6 The module imports nothing from `cli`, `infrastructure` or `hooks`
  (`lint-imports --config setup.cfg --no-cache` green).

### FR2 — `backlog doctor` validates the single source, with the four codes preserved

`features/backlog/doctor.py` keeps its parameterized check engine, its `Finding`/`Severity`
shapes, its CLI contract (`dadaia backlog doctor [--specs-dir] [--source-root]
[--alias-map] [--explain]`, exit non-zero on any ERROR, `backlog doctor: clean.` otherwise)
and its two wirings (the pre-commit staged-scope gate in `cli/commands/ci.py`, the CI job).
Only the surface it reads changes — from `specs/backlog/*.md` to the ACTIVE/LEDGER model.

The four codes over the new shape:

- **BL-SCHEMA** — a located parse error from FR1; an item at `candidate` or beyond with no
  bound `intents[]` or with an unresolvable subject (status gate unchanged: `idea` is
  exempt, `INTENTS_EXEMPT_STATUS`); an invalid `Status` token; a slug not matching
  `^[a-z][a-z0-9-]+$`.
- **BL-DUP** — two ACTIVE items sharing anchor-set + change (classifier `DUPLICATE`,
  unchanged), **and** the same slug appearing twice in `ACTIVE` or twice in `LEDGER`.
- **BL-CONFLICT** — two ACTIVE items sharing an anchor with an incompatible change
  (classifier `DIVERGENT_CONFLICT`, unchanged).
- **BL-STALE** (re-defined, ADR D8) — an ACTIVE item that is already consumed or
  dispositioned: its slug is recorded in an archived `consumed_backlog.json`
  (`ledger.read_consumed`, unchanged), **or** it also carries a LEDGER line, **or** its own
  `Status` is one of the six terminal disposition tokens.

**Acceptance**

- A2.1 A clean consolidated `BACKLOG.md` yields zero findings and exit 0.
- A2.2 A subsection missing a required key fires exactly one BL-SCHEMA ERROR naming the slug.
- A2.3 An item at `candidate` with no `**Intents:**` block fires BL-SCHEMA; the same item at
  `idea` does not (the v0.1.55 FR5 status gate is preserved bit for bit).
- A2.4 A malformed intents YAML block fires BL-SCHEMA at **any** status, including `idea`.
- A2.5 A slug repeated in ACTIVE fires BL-DUP; two items sharing an anchor with differing
  change text fire BL-CONFLICT — the anchor semantics and the classifier are unchanged, proven
  by the existing classifier tests passing untouched.
- A2.6 An ACTIVE item whose slug carries a LEDGER line fires BL-STALE; the same slug present
  **only** in LEDGER fires nothing.
- A2.7 An ACTIVE item whose slug appears in an archived `consumed_backlog.json` fires
  BL-STALE (the historical-sidecar path still works over the 18 real ledgers in
  `specs/_archive/`).
- A2.8 An absent `BACKLOG.md` yields zero findings and exit 0 (no false ERROR in a context
  without a backlog).
- A2.9 The pre-commit staged-scope behaviour is unchanged: a commit staging no
  `specs/backlog/` path skips the gate; a commit staging `BACKLOG.md` runs it and blocks on
  ERROR.

### FR3 — `backlog new` authors an ACTIVE subsection

`features/spec_artifacts/new_artifacts.backlog_new` writes into `BACKLOG.md` instead of
creating `specs/backlog/<slug>.md`: it appends a schema-conformant `### <slug>` subsection at
the end of `## ACTIVE`, born at `status: idea` with today's `Opened` date, the teaching
comment for the intents block preserved, and creates the document with both section headings
when it does not exist. The CLI contract (`dadaia backlog new <slug> [--specs-dir]`,
`[ok] created:` on success, exit 1 with `[error]` on refusal) is preserved.

**Acceptance**

- A3.1 `backlog new <slug>` on a tree with no `BACKLOG.md` creates the document with `##
  ACTIVE` and `## LEDGER` and one conformant subsection.
- A3.2 `backlog new <slug>` on an existing document appends one subsection and leaves every
  other byte of the file unchanged (byte-diff assertion).
- A3.3 A slug already present in `ACTIVE` **or** in `LEDGER` is refused (exit non-zero,
  nothing written) — the slug-uniqueness invariant that replaces file-level no-clobber
  (grill P11).
- A3.4 An invalid slug is refused with the unchanged `^[a-z][a-z0-9-]+$` message.
- A3.5 The freshly authored subsection is `backlog doctor`-clean **and** `specs doctor`-clean
  out of the box (the R-13 producer-passes-its-own-validator rule, both doctors agreeing).

### FR4 — The dead removal/consumption write side is retired (the folded 2-2)

Deleted, with their tests: `features/backlog/removal_lifecycle.py`,
`features/backlog/removal.py`, `features/backlog/ledger_writer.py`,
`features/backlog/consumes.py`, `container.build_backlog_removal_lifecycle` (and
`_backlog_context_roots` if it loses its last caller), and the dead driving-fake helpers
`container._fake_spec_stub` / `_FAKE_BACKLOG_CANARY_SLUG` / `_fake_backlog_canary_slug` /
`_fake_backlog_canary_ref` (grill P12).

**Kept:** `features/backlog/ledger.py` (`read_consumed`) — a pure reader over 18 real
archived sidecars and a live BL-STALE input (FR2). The sidecars themselves are under
`specs/_archive/**` (FROZEN) and are neither edited nor moved.

**Acceptance**

- A4.1 A tree-wide grep (standing exclusions) for `removal_lifecycle`,
  `BacklogRemovalLifecycle`, `consume_at_release_definition`, `remove_at_closure`,
  `apply_removal`, `write_consumed`, `parse_consumes_line`, `shipped_anchors_for`,
  `build_backlog_removal_lifecycle`, `_fake_spec_stub` and `_FAKE_BACKLOG_CANARY_SLUG`
  returns **zero** hits.
- A4.2 `read_consumed` and `LEDGER_FILENAME` survive with their behaviour unchanged, proven
  by `tests/unit/test_backlog_ledger.py` passing **unmodified**.
- A4.3 Nothing under `specs/_archive/**` is created, edited, moved or deleted.
- A4.4 The four superseded test modules (grill P14) are deleted **as recorded supersessions**
  in TASKS, each naming the deleted subject; no other test is deleted, skipped, quarantined or
  weakened in this release.
- A4.5 `dadaia --help` and `dadaia backlog --help` list the same verbs as before this
  release (`new`, `subjects`, `doctor`) — no CLI surface is added or removed by FR4.
- A4.6 `ruff check`, `ruff format --check`, `mypy --strict` and the full `pytest` suite are
  green after the deletion, with no import left dangling.

### FR5 — `specs doctor` governance is re-targeted at the single source

In `features/specs/doctor_governance.py`:

- **SPEC-DOC-031** iterates the ACTIVE subsections of `BACKLOG.md` instead of globbing
  per-entry files. Its evidence source (`_archive_consumption_hits`, the slug-mention scan
  over archived SPEC/CLOSURE excluding `## Backlog returns`), its non-terminal prefix set and
  its **WARNING-only** severity (ADR-6 false-positive class) are unchanged.
- **SPEC-DOC-035** becomes the **single-source invariant** (ADR D5/D9): any per-entry item
  `*.md` loose directly under `specs/backlog/` — anything other than `BACKLOG.md` and
  `README.md`, and excluding `_archive/` and `remote-bugs/` — is drift, **WARNING**.
- **`check_backlog_schema` retires** with `candidates.md`, taking SPEC-DOC-012 and, as a
  side effect, SPEC-DOC-022/023 (ADR D10; the entry #4 overlap is recorded in §7).
- `_BACKLOG_AGGREGATE_FILES` is retired or re-expressed for the new shape — no code path may
  read `BACKLOG.md` as if it were a per-slug entry (grill P4).

**Acceptance**

- A5.1 SPEC-DOC-031 fires on an ACTIVE item with a non-terminal Status whose slug is
  referenced by an archived release outside a `## Backlog returns` section, and does not fire
  on the same slug when referenced only inside one.
- A5.2 SPEC-DOC-031 does **not** fire on the document itself: no finding is ever emitted with
  slug `BACKLOG` or path `.../BACKLOG.md` treated as an entry.
- A5.3 SPEC-DOC-035 fires on a planted `specs/backlog/<slug>.md` and does not fire on
  `BACKLOG.md`, `README.md`, `_archive/**` or `remote-bugs/**`.
- A5.4 SPEC-DOC-012, SPEC-DOC-022 and SPEC-DOC-023 no longer exist in the check inventory; a
  tree-wide grep (standing exclusions) for `check_backlog_schema`, `BACKLOG_BULLET_RE`,
  `BACKLOG_HOTFIX_RE` and `_HOTFIX_STALE_HOURS` returns zero hits.
- A5.5 `dadaia specs doctor` on the consolidated tree reports **0 errors and 0 warnings**
  attributable to the backlog surface.
- A5.6 The two doctors agree on the same tree (R-13's gate-is-a-validator rule): every tree
  `backlog doctor` accepts, `specs doctor` accepts, and every planted violation of the ACTIVE
  schema is rejected by `backlog doctor` (ERROR) without `specs doctor` contradicting it.

### FR6 — The consumer-facing description matches the shipped model

- `public/scaffold/backlog/README.md` describes the single-source document: one `BACKLOG.md`
  with `ACTIVE` + `LEDGER`, the six required/optional subsection keys, the LEDGER grammar,
  the six terminal disposition tokens by reference to `dd-backlog-definition` §2, the
  `idea`-vs-`candidate` intents gate, and `dadaia backlog new` as the authoring path. The
  retired sentences — per-entry `<slug>.md` files, `release:` frontmatter promotion, "never
  delete … change `status`" — are replaced by the ACTIVE → LEDGER law.
- `public/data/CONSUMER_VALIDATION_RECIPE.md`: **F-10** plants its malformed item as an
  ACTIVE subsection; **R-02** drops the retired consumed-backlog-ledger clause (grill P10) and
  asserts instead that the declared `**Consumes:**` slug resolves to an ACTIVE subsection and
  that `specs doctor` accepts the SPEC; **R-13** keeps its gate-is-a-validator rule over the
  new shape.
- `.github/workflows/ci.yml`: the `backlog-doctor` job's comment stops claiming
  `specs/backlog/` is gitignored (false since v0.1.49 FR1 — `.gitignore:133-142`, grill P7);
  the job name, verb and arguments are unchanged. `cli/commands/newartifacts.py`'s
  `backlog doctor` docstring loses the same false clause.
- The projections are refreshed (`dadaia public stage` → `install --target all` →
  `doctor`).

**Acceptance**

- A6.1 A grep (standing exclusions) for `specs/backlog/<slug>.md`-shaped per-entry
  instructions across `public/**` returns zero hits.
- A6.2 A grep for "gitignored" within 3 lines of `backlog` in `.github/workflows/ci.yml` and
  `dadaia_workspace/cli/**` returns zero hits.
- A6.3 `dadaia public doctor` is green, including `[ok] public-privacy`, and the projected
  copies match the staged sources.
- A6.4 The CI job `Backlog consistency (BL-SCHEMA/DUP/CONFLICT/STALE)` runs the same command
  (`dadaia backlog doctor --specs-dir specs --source-root .`) and is green on the consolidated
  tree — the job's contract does not change, so **no new e2e test is added** (D6).
- A6.5 A reader following F-10/R-02/R-13 verbatim on a scaffolded context reaches a passing
  result with no manual repair.

### FR7 — The physical consolidation, with never-delete proven by count

`project-manager` folds every live per-entry file **and** `candidates.md` into
`specs/backlog/BACKLOG.md`:

- Every live candidate and idea becomes an `ACTIVE` subsection carrying its Provenance line
  (operator request, or intake-report item + approval date) and its `**Intents:**` block where
  the source file had one.
- Every terminal record — the 20 existing LEDGER lines, the terminal rows of `candidates.md`
  (terminal-at-materialization, rejected, intake-adjudication) and every file under
  `specs/backlog/_archive/` — becomes a `LEDGER` line with its disposition token.
- `tag-push-carve-out-reachability` resolves to **LEDGER only** (grill P6): its file is
  flipped to a terminal status and archived; it does not become an ACTIVE subsection.
- The two entries picked by this release stay ACTIVE at `status: picked` until the closure
  sweep flips them terminal.
- The superseded per-entry files and `candidates.md` leave `specs/backlog/` by **`git mv`**
  into `specs/backlog/_archive/` — archived, never deleted (ADR D5).
- The PM decision records inside `candidates.md` (the disposition-decision sections and the
  standing operator notices) travel with the file into `_archive/`; the standing notices that
  are still live are restated in `BACKLOG.md`.

**Acceptance**

- A7.1 `specs/backlog/BACKLOG.md` exists with exactly two top-level sections, `## ACTIVE` and
  `## LEDGER`, and parses clean under FR1.
- A7.2 **Countable never-delete (ADR D4).** The slug set discoverable before the
  consolidation — live entry files ∪ `candidates.md` candidate/idea rows ∪
  `specs/backlog/_archive/` files ∪ LEDGER lines ∪ terminal-table rows — equals the slug set
  in `BACKLOG.md` after it. Both set differences are empty; the two sorted sets and the
  difference computation are captured as evidence. Measured baseline at `feature/v0.12.0`:
  31 live files, 30 live rows, 46 archived files, 20 LEDGER lines.
- A7.3 Each slug appears **exactly once** in the document, and in exactly one of ACTIVE or
  LEDGER (no slug in both — BL-STALE would fire).
- A7.4 Every ACTIVE subsection carries a Provenance line traceable to an operator request or
  an intake-report item with its approval date.
- A7.5 After the cutover, `specs/backlog/` contains exactly `BACKLOG.md`, `README.md`,
  `_archive/` (and `remote-bugs/` if it exists) — `git status` shows the removals as renames,
  not deletions.
- A7.6 `dadaia backlog doctor` and `dadaia specs doctor` are both clean on the consolidated
  tree (A2.1, A5.5, A5.6).
- A7.7 The entry numbering used by cross-references (`#9 and #18`, `blocked on #2`) survives:
  either the numbers are carried into the subsections, or every surviving cross-reference is
  rewritten to the slug. No dangling numeric reference remains.

### FR8 — The two skills state the mechanism that runs

`ai-engineer` edits, at the canonical source under `dadaia_workspace/public/skills/`:

- **`dd-backlog-definition/SKILL.md` §2** — the "Tooling note" (the CLI reads per-entry
  files) is **deleted**, because it stops being true; the optional `**Intents:**` key is added
  to the ACTIVE schema with its status gate (ADR D7); §7's caveat that `backlog`-group verbs
  are not schema authority is removed.
- **`dd-release-definition/SKILL.md` §5** — the paragraph naming `removal_lifecycle.py` and
  the "until a CLI wrapper ships" hedge are replaced by the real mechanism (ADR D2): the
  `**Consumes:**` line is SPEC provenance; consumption is executed by the PM's purge-on-pick
  at definition and the `dd-release-closure` disposition sweep at closure, backstopped by
  `backlog doctor` BL-STALE and `specs doctor` SPEC-DOC-031. The full-slug-granularity and
  fail-loud rules are restated only where they still describe something that runs. The
  checklist item is rewritten to the executable step.

**Acceptance**

- A8.1 A grep (standing exclusions) for `removal_lifecycle` across
  `dadaia_workspace/public/**` and the projected skill trees returns zero hits.
- A8.2 `dd-backlog-definition` §2 documents six ACTIVE keys (five required + `Intents`
  optional) and carries no statement that the CLI implements a different model.
- A8.3 `dd-release-definition` §5's checklist item names a step an agent can execute today,
  and the skill's own checklist can be ticked truthfully by this very release.
- A8.4 `dadaia public stage` → `install --target all` → `doctor` green; every projection of
  both skills matches its staged source (no hand-edited projection).

### FR9 — The invariants this release must not break

1. **Never-delete.** No backlog record and no bug record is deleted, in the tree or in
   history. Every removal from `specs/backlog/` is a `git mv` into `_archive/`.
2. **`specs/_archive/**` is FROZEN.** Nothing under it is created, edited or moved except the
   `git mv` **into** `specs/backlog/_archive/`, which is not the release archive.
3. **Operator-gated intake (ADR #15).** This release materializes **no** backlog entry. Every
   residual it discovers is listed in `CLOSURE.md` for the PM's intake report.
4. **The anchor semantics are preserved (ADR D7).** `subject_registry.py`, `classifier.py`,
   `cli/anchors.py`, the alias map and the `backlog subjects` verb survive with unchanged
   behaviour; their tests pass **unmodified**.
5. **No new CLI verb, no new doctor code, no new hook, no new script, no new e2e test.** The
   four BL-* codes and the SPEC-DOC ids keep their identities; only their surfaces change.
6. **Green at every commit** (§3 standing green rule), including the pre-commit backlog gate
   on every commit that stages `specs/backlog/**`.

**Acceptance**

- A9.1 `git log --diff-filter=D -- specs/backlog/` over the release range shows only renames
  into `_archive/` (deletions paired with additions), never a bare deletion.
- A9.2 `git diff --stat` over the release range shows zero modified paths under
  `specs/_archive/`.
- A9.3 `CLOSURE.md` carries an `## Intake candidates` section and no new file exists under
  `specs/backlog/` other than `BACKLOG.md`.
- A9.4 `tests/unit/test_backlog_classifier.py`, `tests/unit/test_backlog_subject_registry.py`,
  `tests/unit/test_backlog_models.py` and `tests/unit/backlog/test_classifier_clamp.py` pass
  **unmodified**.
- A9.5 `dadaia backlog --help` lists exactly `new`, `subjects`, `doctor`; the four BL-* codes
  and the SPEC-DOC id set (minus the three retired by FR5) are unchanged.
- A9.6 Every commit of the release passes `dadaia ci preflight` (`ruff format --check`,
  `ruff check`, `mypy --strict`, `pytest`) and the backlog gate.

---

## 4. Out of scope (non-goals)

1. **Dropping `intents[]` from the backlog model.** The conservative reading is taken
   (ADR D7, OD-1): the binding is preserved as an optional key. The registry, classifier,
   alias map, `cli/anchors.py` and `backlog subjects` are untouched. If the operator later
   rules that the backlog carries no typed intents, that retirement is its own release.
2. **A CLI consumer for the removal lifecycle.** Evaluated and **declined** (ADR D2, grill
   P1): the module has no caller, and its defined behaviour contradicts the never-delete law.
   It is deleted, not wired.
3. **The rest of entry #4 `retire-dead-hotfix-surface` (not picked).** SPEC-DOC-022/023
   disappear as a side effect of retiring `check_backlog_schema`; the `cli/commands/specs.py`
   hotfix verb and the `release_hotfix`/`closure_hotfix` templates are **untouched** and #4
   stays live, to be rewritten down to that residual by the PM (OD-2, §7).
4. **`remote-bugs/` intake subtree.** It is empty at HEAD; the consolidation neither creates
   nor absorbs it, and SPEC-DOC-035 excludes it explicitly so a future subtree is not
   mis-flagged.
5. **`test-suite-remediation-stewardship` (#2, not picked).** The LARGE census is not
   addressed; this release adds zero e2e tests, so the census does not grow.
6. **Bug-ledger shape.** `specs/bugs/**` (JSONL, SPEC-DOC-032/033) is untouched; the backlog
   consolidation is a document change, not a ledger change. `bugs-jsonl-whole-blob-per-append`
   (idea, not picked) stays open.
7. **Law text.** `DADAIA.md` §5 already describes the single source correctly; nothing in the
   projected law changes, and no law file is edited by hand (`DADAIA.md` §7).
8. **Memory writes in the DEFINITION phase.** The `sdd-bug-backlog-governance` atom is
   currently *accurate* — it states plainly that the physical backlog has not been
   consolidated. This release changes the product, so every memory edit waits for CLOSURE (§5).
9. **Panel or reporting surfaces.** Nothing renders the backlog in the panel; no view changes.

---

## 5. Memory files affected at closure

| File | Change | When |
|---|---|---|
| `specs/memory/product/sdd/sdd-bug-backlog-governance.md` | §Backlog: the "doctrine is stated in the law and the skill; the physical backlog has not been consolidated yet" paragraph is **replaced** by the shipped truth — `BACKLOG.md` (ACTIVE + LEDGER) is the format of record, the `dadaia backlog` verbs read and write it, and BL-STALE means "an ACTIVE item that is already consumed/dispositioned"; §Runtime State: the per-entry-files line is dropped and `specs/backlog/_archive/` named as the historical store; the `**Consumes:**` mechanism stated once, as provenance + sweep | **CLOSURE** |
| `specs/memory/product/sdd/specs-doctor.md` | the governance-check inventory: SPEC-DOC-031/035 re-targeted, SPEC-DOC-012/022/023 retired | **CLOSURE** |
| `specs/memory/product/catalog.json` | regenerated **only** if a touched atom's `tldr`/`summary` frontmatter changed (`public/scripts/generate-memory-catalog.py`) | **CLOSURE** |
| `specs/memory/architecture.md` | no change — no layer rule, port or runtime-state entry changes (the alias map and `.dadaia/states/` layout are untouched) | — |
| `specs/memory/tech-stack.md` | no change — no dependency added or removed | — |
| `specs/memory/product/index.md` | no change — no product feature added or removed | — |
| `specs/memory/quality-assurance.md` | no change — the test-stewardship doctrine is applied, not amended | — |

### Closure obligations (not implementation FRs)

- **Disposition sweep.** Both picked entries reach `DELIVERED — v0.12.0` at closure per
  `dd-release-closure`; the `## Dispositions` table records each with its evidence pointer.
  Because the entries themselves are consolidated into `BACKLOG.md` by FR7, their terminal
  disposition is a **LEDGER line**, and their ACTIVE subsections are removed in the same
  commit — the first closure to exercise the new shape end to end.
- **Test dispositions.** The four supersessions of FR4 and every migrated module are recorded
  in `CLOSURE.md` › `## Test dispositions` with the replacement coverage named.
- **Intake candidates.** Residuals — including **OD-2** (entry #4's rewrite to its residual)
  and any drift found while folding 31 files — are **listed** for the PM's operator-facing
  intake report. The closer creates no backlog entry (ADR #15).
- **OD-1 restatement.** `CLOSURE.md` restates the open decision on `intents[]` so the
  operator's eventual ruling has a single, current reference point.

---

## 6. Dependencies and risks

| # | Item | Status / mitigation |
|---|---|---|
| D-1 | `product-engineer` has no shell | every git, CLI and measurement step is an explicit TASKS entry owned by the dispatcher, `software-engineer`, `project-manager` or `ai-engineer` |
| D-2 | ADR D1 — the cutover is atomic | encoded as T-120-08's dual-owner single-commit write set; every pure module lands before it (T-120-04…T-120-06) |
| D-3 | ADR D9 — the governance re-target must ride the cutover commit | grill P4 proves the spurious WARNING otherwise; T-120-08's write set includes `doctor_governance.py` |
| D-4 | FR7 needs FR1–FR3 shipped as code, and FR2's wiring needs FR7's document | resolved by the single commit; the PM's document is authored (T-120-07) but not committed until the cutover |
| R1 | **A commit lands with the doctors disagreeing**, blocking the pre-commit gate for every later commit | the standing green rule; T-120-08's done criterion runs both doctors before the commit is made, and A5.6 makes agreement an acceptance id |
| R2 | **A record is lost while folding 31 files + an index into one document** | A7.2's countable set equality with captured evidence; `git mv` (never delete); the archived copies remain byte-identical |
| R3 | **The cutover commit is too large to review** | every pure module and its tests land in earlier commits; the cutover carries wiring, deletions and document moves only, and its diff is dominated by renames |
| R4 | **The retirement takes a live control with it** | FR4's kept/deleted list is explicit; A4.2 pins `ledger.py` behaviour by an unmodified test; A9.4 pins the anchor machinery by four unmodified test modules |
| R5 | **The optional `Intents` key re-introduces the two-format hazard** by drifting from the skill schema | FR8 lands the schema in the canonical skill; A2.3/A2.4 pin the parser to it; the skill and the parser are reviewed against each other at QA |
| R6 | **`specs doctor` starts reading `BACKLOG.md` as an entry** and emits a phantom `BACKLOG` slug | A5.2 is a named acceptance id, not an implied one |
| R7 | **Consumer contexts break**: a scaffolded context with no `BACKLOG.md` starts erroring | A1.2 + A2.8 make absence a clean no-op; A6.5 walks the recipe end to end |
| R8 | **Entry cross-references (`#2`, `#9 and #18`) dangle** after numbering is dropped | A7.7 forces an explicit choice: carry the numbers or rewrite the references |
| R9 | **A migrated test is quietly weakened** to pass on the new shape | D6 + A4.4; every deletion is a recorded supersession and QA verifies no test was pruned to go green |
| R10 | **Package/CI drift**: the CI job or pre-commit path silently stops running | A6.4 (same command, green) + A2.9 (staged-scope behaviour unchanged) |

---

## 7. Traceability and provenance

| Entry (candidates.md #) | Provenance | Disposition in this release |
|---|---|---|
| `backlog-tooling-reconciliation` (#30) | **pre-approved intake P-1** — operator ratification D-A at the v0.10.0 approval (SPEC §4.5/§4.10), materialized 2026-08-15; **plus** intake report #2 item **2-2** approved **as a merge** (`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T152234Z-intake.html`) | **picked — v0.12.0** · FR1–FR6, FR8 · terminal `DELIVERED — v0.12.0` at closure |
| `backlog-md-physical-consolidation` (#31) | **pre-approved intake P-2** — operator ratification D-A at the v0.10.0 approval (SPEC §4.4/D5), materialized 2026-08-15 | **picked — v0.12.0** · FR7 · terminal `DELIVERED — v0.12.0` at closure |
| Intake item **2-2** (`Consumes` checklist without an executor) | code-review pre-PR `2026-08-15T145731Z` (LOW); approved as a merge into #30 | **delivered inside #30** · FR4 (retirement) + FR8 (checklist rewrite) |
| `retire-dead-hotfix-surface` (#4) | v0.6.0 law revocation residue | **not picked** (§4.3) — SPEC-DOC-022/023 disappear as a side effect of FR5; the CLI verb and templates are untouched. **OD-2:** the PM rewrites #4 down to that residual; PE does not edit an unpicked entry |
| `test-suite-remediation-stewardship` (#2) | ADR #6 | **not picked** (§4.5); zero new e2e tests here |
| `bugs-jsonl-whole-blob-per-append` (idea) | v0.9.0 CLOSURE | **not picked** (§4.6) |
| `spec-doc-031-citation-classes` (#10) | v0.8.0 CLOSURE return | **not picked** — SPEC-DOC-031's citation-class refinement is a *semantic* change; this release only re-points the check's iteration surface and leaves its false-positive class exactly as ADR-6 defined it |
| `tag-push-carve-out-reachability` (idea) | v0.7.0 CLOSURE, absorbed by v0.9.0 FR2 | **not picked** — but its file/index drift (grill P6) is reconciled by FR7 into a LEDGER-only record |
| Open bugs | `specs/bugs/bugs.jsonl` | **none** — the ledger carries zero open bugs at pick time; nothing outranks |
| Audits | `specs/audits/_archive/` | **none outstanding** — both 2026-07 audits archived fully dispositioned by v0.8.0 |

**Purge-on-pick (ADR #14).** `specs/backlog/**` is `project-manager` surface. This section is
the provenance record the doctrine requires. In this pick the two entry files are **flipped to
`status: picked` with a pick-provenance section rather than removed** — the v0.11.0 precedent
— because FR7 consolidates the whole directory inside this same release: deleting the two
files at definition would remove source material the consolidation is written from. They
become ACTIVE subsections at `status: picked` in `BACKLOG.md` at the cutover, and gain their
`DELIVERED — v0.12.0` LEDGER lines at closure. `specs/backlog/candidates.md` records the pick
in the same commit.

**Version axis (ADR D3, ADR-2 split unchanged).** The SDD release id is `v0.12.0`; the package
version is minted **0.9.0** at ship (`pyproject.toml`, currently `0.8.0`), following the
precedent v0.9.0→0.6.0, v0.10.0→0.7.0, v0.11.0→0.8.0. `CHANGELOG.md` gains the `[0.9.0]`
entry in the same commit as the bump.

---

## 8. Approval

**Approved by the operator on 2026-08-15** (operator-delegated approval, goal directive),
**as written** — no scope change. SPEC, PLAN and TASKS all carry `**Status:** Aprovado`;
milestone (a) of the `dadaia-gitflow` contract may fire once the definition commit
(T-120-01) lands.

Ratified with the approval:

- **D1–D6 as given** (the operator's pre-rulings): one release for both entries with an
  atomic cutover; the 2-2 fold resolved by retirement; release id `v0.12.0` / package
  `0.9.0`; countable never-delete; `git mv` archival with coherent SPEC-DOC-035 semantics;
  and the feature-focused test bar with recorded supersessions.
- **D7–D10** — the four refinements the grill added: the conservative `intents[]` preservation
  (OD-1), the BL-STALE re-definition, the same-commit governance re-target, and the
  `check_backlog_schema` retirement with the entry #4 overlap recorded (OD-2).

Both open decisions (OD-1, OD-2) are **recorded, not blocking**: neither changes this
release's scope, and both are restated at closure for the operator's ruling.
