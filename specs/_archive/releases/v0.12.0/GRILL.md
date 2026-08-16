# GRILL — Release v0.12.0 — backlog-tooling-single-source

**Status:** Aprovado
**Approval provenance:** operator-delegated ruling, 2026-08-15 (goal directive)
**Release ID:** v0.12.0
**Owner:** product-engineer
**Generated:** 2026-08-15
**Scope:** the picked set — `backlog-tooling-reconciliation` (#30, incl. the folded intake
item 2-2) and `backlog-md-physical-consolidation` (#31)
**Protocol:** `dadaia-grill-me` (mandatory before the SPEC, `dd-release-definition` §3)
**Problems found:** 15 · **Resolved by inspection:** 13 · **Resolved by delegated ruling:** 2
· **Open decisions flagged:** 2 (OD-1, OD-2)

> **Method note.** Phase 0 inspection was run against the working tree at
> `feature/v0.12.0` (cut from `develop` at `523f0d8d`). Every factual claim below was read
> out of a file, not asked of the operator. The operator's pre-rulings D1–D6 (goal
> directive, 2026-08-15) are treated as answers already given; the grill's own additions
> are numbered D7–D10.

---

## 1. Problem summary

| # | Type | Surface | Status |
|---|---|---|---|
| P1 | Spec↔code drift | `dd-release-definition` §5 ↔ `features/backlog/removal_lifecycle.py` | Resolved — D2 verdict |
| P2 | Inconsistency between specs | `dd-backlog-definition` §2 schema ↔ entry #30 `intents[]` | Resolved conservatively — **OD-1** |
| P3 | Order dependency | tooling cutover ↔ physical consolidation | Resolved — D1 verdict |
| P4 | Spec↔code drift | both doctors mis-read `BACKLOG.md` as an item file | Resolved — D9 |
| P5 | Undeclared dependency | `check_backlog_schema` ↔ entry #4 (not picked) | Resolved — D10, **OD-2** |
| P6 | Inconsistency (live tree) | 31 live entry files vs 30 live index rows | Resolved by inspection |
| P7 | Stale documentation | CI job + two docstrings claim `specs/backlog/` is gitignored | Resolved by inspection |
| P8 | Unanswerable criterion | BL-STALE's premise is illegal under never-delete | Resolved — D8 |
| P9 | Ambiguous syntax | `**Consumes:**` prose vs the bare-slug grammar | Resolved by inspection |
| P10 | Spec↔code drift | consumer recipe R-02 describes the retired producer | Resolved by inspection |
| P11 | Divergent semantics | `backlog new` no-clobber: file-level vs slug-level | Resolved by inspection |
| P12 | Dead surface | `container._fake_spec_stub` / `_fake_backlog_canary_*` | Resolved by inspection |
| P13 | Scope hygiene | zero-hit grep criteria scoping (the 2-8 lesson) | Resolved — SPEC §3 standing rule |
| P14 | Test blast radius | 8 per-entry-model test modules | Resolved — D6 applied |
| P15 | Unanswerable criterion | "never-delete preserved" is not countable as written | Resolved — D4 applied |

---

## 2. Details per problem

### P1 — The `**Consumes:**` checklist item has no executor (the folded 2-2)

**Type:** Spec↔code drift · **Answered via inspection.**

`dd-release-definition/SKILL.md` §5 requires a `**Consumes:**` declaration and ticks it on
the protocol checklist. The producer it names is `features/backlog/removal_lifecycle.py`.
Inspection of every reference in the tree:

- `consume_at_release_definition` / `remove_at_closure` / `BacklogRemovalLifecycle` — no
  production caller. The only non-test reference is
  `container.build_backlog_removal_lifecycle`, which **itself has no caller**.
- `features/backlog/consumes.py` (`parse_consumes_line`, `shipped_anchors_for`) — no
  production caller; referenced only by `tests/unit/backlog/test_consumes.py`.
- `features/backlog/ledger_writer.py` (`write_consumed`) — called only from
  `removal_lifecycle.py`, i.e. from nothing.
- `features/backlog/removal.py` (`apply_removal`) — called only from
  `removal_lifecycle.py`.
- The former caller is named in the archived record: `specs/_archive/releases/v0.1.27/`
  wired the producer into a `dadaia lifecycle` post-step, and
  `specs/_archive/releases/v0.3.0/TASKS.md` deleted that engine while explicitly *keeping*
  `build_backlog_removal_lifecycle` and asserting `removal_lifecycle.py` "survives and must
  not match" the removal greps. The surface was preserved on purpose and never re-wired.

**Second, decisive finding:** `apply_removal`'s contract is to **rewrite an item down to its
residual or archive-then-unlink it**. Under the single-source model an item never leaves the
file — it moves `ACTIVE` → `LEDGER` (`DADAIA.md` §5, never-delete). Wiring a CLI verb to it
would ship an automation whose defined behaviour contradicts the law this release exists to
serve, over a document whose curation the entry itself calls "judgment, not a script".

**Resolution (ADR D2-verdict — RETIRE).** Delete the write side —
`removal_lifecycle.py`, `removal.py`, `ledger_writer.py`, `consumes.py`,
`container.build_backlog_removal_lifecycle` — with their tests. **Keep** `ledger.py`
(`read_consumed`): it is a pure reader over 18 real historical
`specs/_archive/**/consumed_backlog.json` sidecars and remains a live BL-STALE input (P8).
`dd-release-definition` §5 is rewritten to name the mechanism that actually runs: the
`**Consumes:**` line is SPEC provenance; consumption is executed by the PM's purge-on-pick
at definition and the `dd-release-closure` disposition sweep at closure, backstopped
mechanically by `backlog doctor` BL-STALE and `specs doctor` SPEC-DOC-031.

### P2 — The ratified ACTIVE schema has no `intents`, but the picked entry says to preserve them

**Type:** Inconsistency between specs · **Genuinely unanswerable → conservative option
taken, flagged as OD-1.**

`dd-backlog-definition` §2 (ratified in v0.10.0) fixes the ACTIVE subsection schema at five
keys — Title, Opened, Status, Description, Provenance. There is no `intents[]`. Entry #30's
own intent on `preview.py#load_backlog_items` says: "Load items from BACKLOG.md ACTIVE
subsections … **intents/anchor binding preserved**."

The two readings are incompatible and the difference is large: dropping intents retires
`subject_registry.py`, `classifier.py`, `cli/anchors.py`, the alias map, the
`backlog subjects` verb and the anchor semantics of BL-SCHEMA/BL-DUP/BL-CONFLICT —
roughly 2,000 lines of enforcement machinery with no replacement other than PM discipline.

**Resolution.** Take the conservative option: **preserve** the binding. The ACTIVE
subsection schema gains **one optional key**, `**Intents:**`, carrying the same typed YAML
block in a fenced code span, required at `candidate` and beyond exactly as today
(`status: idea` stays exempt — `core/models/backlog.INTENTS_EXEMPT_STATUS`). The ratified
five keys are unchanged; the extension is additive and the anchor semantics of the three
pairwise checks survive verbatim. Deleting a live mechanical control that the picked entry
explicitly asks to keep is not a decision a grill may take on the operator's behalf.

### P3 — Neither ordering is green; the cutover must be atomic

**Type:** Order dependency · **Answered via inspection; ratified by D1.**

- **Consolidation first** breaks immediately: `preview.load_backlog_items` globs
  `specs/backlog/*.md` and skips only `{ideas, candidates, README}` (`preview.py:41`), so
  `BACKLOG.md` is loaded as an item with slug `BACKLOG`, no intents, at a status parsed from
  the first subsection — a BL-SCHEMA **ERROR** in the pre-commit gate and the CI job.
- **Tooling first** is green but vacuous: a doctor pointed at a `BACKLOG.md` that does not
  exist yet validates nothing, and the 31 live per-entry files pass through a window with no
  validation at all.

**Resolution (ADR D1-verdict — ATOMIC).** One cutover commit carries: the CLI/pre-commit/CI
wiring flip, the deletion of the per-entry loaders, the governance re-target (P4), the new
`BACKLOG.md`, and the `git mv` of the per-entry files and `candidates.md` into
`specs/backlog/_archive/`. Before the commit the old shape is validated by the old tooling;
after it the new shape is validated by the new tooling; no intermediate state exists. Every
new pure module (parser, checks, writer) lands **before** the cutover against fixtures, so
the cutover commit is wiring, deletions and document moves — not new logic.

### P4 — Both doctors mis-read `BACKLOG.md` as an entry file

**Type:** Spec↔code drift · **Answered via inspection.**

`doctor_governance._BACKLOG_AGGREGATE_FILES` is `{candidates.md, ideas.md, README.md}`;
`BACKLOG.md` is not in it. SPEC-DOC-031 and SPEC-DOC-035 therefore glob it as a per-slug
entry, read a Status via `_BACKLOG_STATUS_RE` (which matches the first
`- **Status:** candidate` line inside the first ACTIVE subsection), and SPEC-DOC-031 then
asks `_archive_consumption_hits("BACKLOG")` — a raw substring scan over every archived
SPEC/CLOSURE, which matches on the many archived documents containing the string
`BACKLOG`. Result: a spurious WARNING keyed to a slug that does not exist.

**Resolution (ADR D9).** The governance re-target rides the **same** cutover commit as the
document, not a follow-up: SPEC-DOC-031 iterates ACTIVE subsections of `BACKLOG.md`
(keeping its archived-mention evidence source and its WARN-only severity, ADR-6 unchanged),
and SPEC-DOC-035 becomes the **single-source invariant** — any per-entry item `*.md` loose
directly under `specs/backlog/` (i.e. not `BACKLOG.md`, not `README.md`, not under
`_archive/` or `remote-bugs/`) is drift, WARNING. That keeps the code alive and truthful
instead of leaving a check that polices a model the product no longer has.

### P5 — `check_backlog_schema` dies with `candidates.md`, and takes entry #4's checks with it

**Type:** Undeclared dependency · **Answered via inspection; flagged as OD-2.**

`GovernanceValidator.check_backlog_schema` validates exactly one file — `candidates.md` —
in two sections: `## Candidatas ativas` (SPEC-DOC-012) and `## Hotfixes pendentes`
(SPEC-DOC-022/023). Once `candidates.md` is archived the function is dead code that
no-ops silently, which entry #30's own acceptance forbids ("zero stale checks against
per-entry files remain"). But SPEC-DOC-022/023 are the queued scope of entry **#4**
`retire-dead-hotfix-surface`, which is **not** picked.

**Resolution (ADR D10).** Retire the whole function with the cutover. This delivers the
SPEC-DOC-022/023 half of #4 as a side effect; #4's remaining surface (the
`cli/commands/specs.py` hotfix verb and the `release_hotfix`/`closure_hotfix` templates) is
untouched and #4 stays live. **OD-2:** rewriting #4 down to that residual is PM curation
work — `product-engineer` does not edit a backlog entry outside the picked set. It is
recorded in SPEC §7 and listed as a closure obligation for the PM's disposition pass.

### P6 — 31 live entry files vs 30 live index rows

**Type:** Inconsistency (live tree) · **Answered via inspection.**

`specs/backlog/candidates.md` counts 25 live candidates + 5 live ideas = **30**. The
directory holds **31** live item files. The extra is
`specs/backlog/tag-push-carve-out-reachability.md`: its frontmatter still reads
`status: idea`, its ledger row reads `tag-push-carve-out-reachability · DELIVERED · v0.9.0`,
and the index claims the file was "flipped `status: delivered` and archived at `03ddd0b2`".
It was not — it is loose in `specs/backlog/` at HEAD.

**Resolution.** At consolidation the slug resolves to **LEDGER only** (its DELIVERED row
already exists); the file is flipped to a terminal status and `git mv`'d into
`specs/backlog/_archive/`. Recorded in the consolidation task's write set so the count
reconciles instead of silently absorbing a drift.

### P7 — Three surfaces claim `specs/backlog/` is gitignored; it has not been since v0.1.49

**Type:** Stale documentation · **Answered via inspection.**

`.gitignore:133-142` opts `specs/backlog/*.md`, `_archive/*.md` and `remote-bugs/*.md`
back in ("so the BL-* pre-commit scope and the CI backlog-doctor job exercise the real
committed tree"). Three surfaces still assert the opposite:
`.github/workflows/ci.yml:426-429` ("specs/backlog/ is gitignored in this source repo, so
the check runs over whatever survivors are tracked — an empty backlog is trivially clean"),
`cli/commands/newartifacts.py:234` and `features/backlog/removal.py:11-12`, whose
copy-before-unlink safety argument is *founded* on the false claim ("`specs/backlog/` is
gitignored, so the archive copy is the only surviving copy"). The third is additional
evidence for P1's retirement verdict.

**Resolution.** The CI job comment and the CLI docstring are corrected with the wiring
change (FR6); the third disappears with `removal.py`.

### P8 — BL-STALE's premise is illegal under never-delete

**Type:** Unanswerable acceptance criterion · **Answered via inspection.**

BL-STALE fires when a slug recorded in an archived `consumed_backlog.json` "still exists in
`specs/backlog/`" (`doctor.py:220-237`). Under the single-source model the slug **always**
still exists — never-delete guarantees it, and the LEDGER is where it lives. As written the
check would fire on every delivered item forever.

**Resolution (ADR D8).** BL-STALE is re-defined over the new shape, preserving its intent
("a consumed item is still being treated as live") and losing its retired mechanism:
an **ACTIVE** subsection whose slug is either (a) recorded in an archived
`consumed_backlog.json` (`ledger.read_consumed`, unchanged), or (b) already carries a
`LEDGER` line in the same document, or (c) itself carries a terminal disposition token in
its `Status`. The code and its severity (ERROR) are unchanged; only the surface it reads
changes.

### P9 — `**Consumes:**` is prose in practice, and no mechanical consumer may be built on it

**Type:** Ambiguous syntax · **Answered via inspection.**

`consumes.parse_consumes_line` expects bare comma-separated slugs. The archived corpus is
mostly prose: ``**Consumes:** backlog `context-injection-role-phase-canon` (3 intents) +
`fragment-workflow-base-dedup` `` (v0.1.57), `**Consumes:** the two undispositioned audits`
(v0.8.0), `**Consumes:** none` (v0.1.29). Of 26 archived declarations only a minority parse
cleanly.

**Resolution.** No new mechanical consumer is built on the line, which independently
confirms P1's verdict. It remains a human/agent-readable provenance convention; this SPEC
declares it in the strict bare-slug form.

### P10 — The consumer validation recipe describes the retired producer

**Type:** Spec↔code drift · **Answered via inspection.**

`public/data/CONSUMER_VALIDATION_RECIPE.md` R-02 passes only if "a release SPEC naming the
item under `**Consumes:**` is accepted by `specs doctor`, **with the consumed-backlog ledger
recording the item's canonical `specs/backlog/<slug>.md` path**" — a producer that has not
run since v0.3.0 and is deleted by this release. F-10 and R-13 likewise instruct the
validator to "add a backlog item … under `repos/valproj/specs/backlog/`" as a file.

**Resolution.** FR6 rewrites F-10, R-02 and R-13 against the shipped model. R-13's standing
rule — "a GATE is a validator too … the two must never hold two opinions" — is promoted to
an acceptance criterion of this release: what `backlog doctor` accepts, `specs doctor` must
also accept, on the same tree, in the new shape.

### P11 — `backlog new`'s no-clobber semantics change kind

**Type:** Divergent semantics · **Answered via inspection.**

Today `backlog_new` raises `FileExistsError` on an existing path. With one document there is
no path to collide; the invariant that must survive is **slug uniqueness across
`ACTIVE ∪ LEDGER`** (a re-opened delivered slug is a real authoring mistake). The CLI's exit
code and message class are preserved so the consumer recipe's assertions stay meaningful.

### P12 — Dead driving-fake helpers in `container.py`

**Type:** Dead surface · **Answered via inspection.**

`container._fake_spec_stub`, `_FAKE_BACKLOG_CANARY_SLUG`, `_fake_backlog_canary_slug`,
`_fake_backlog_canary_ref` (`container.py:716-786`) have **zero** references outside their
own definitions. They synthesise a `**Consumes:**` SPEC stub and per-entry canary files for
the deleted fake-agent harness, and they are the last per-entry-file *writer* outside
`backlog new`.

**Resolution.** Deleted with the write-side retirement (FR4), under a zero-hit grep
criterion.

### P13 — Zero-hit grep criteria must be scoped (the 2-8 lesson)

**Type:** Scope hygiene. SPEC §3 carries one standing exclusion set —
`specs/_archive/**`, `specs/bugs/**`, `specs/backlog/_archive/**`, `CHANGELOG.md` and
`specs/releases/v0.12.0/**` — inherited by every zero-hit criterion, since this release's
own documents must quote the symbols they retire.

### P14 — Test blast radius

**Type:** Order dependency / stewardship · **D6 applied.** Modules touching the per-entry
model, and their disposition:

| Module | Disposition |
|---|---|
| `tests/unit/test_backlog_removal.py` | **superseded** — subject deleted (FR4) |
| `tests/unit/test_backlog_ledger_writer.py` | **superseded** — subject deleted (FR4) |
| `tests/integration/test_backlog_removal_loop.py` | **superseded** — subject deleted (FR4) |
| `tests/unit/backlog/test_consumes.py` | **superseded** — subject deleted (FR4) |
| `tests/unit/test_backlog_preview.py` | **migrated** — item loading moves to the document parser |
| `tests/unit/features/backlog/test_frontmatter_yaml_parse_error.py` | **migrated** — malformed-block diagnostics over a subsection |
| `tests/integration/test_backlog_doctor.py` | **migrated** — four codes over the new shape |
| `tests/integration/cli/test_cli_newartifacts.py`, `tests/unit/features/spec_artifacts/test_new_artifacts.py` | **migrated** — `backlog new` authors a subsection |
| `tests/e2e/features/test_backlog_precommit.py`, `tests/integration/test_precommit_backlog_scoping.py` | **adjusted in place** — same gate, new fixture shape; no new e2e |
| `tests/unit/features/specs/test_doctor.py`, `test_doctor_taxonomy_disposition.py`, `_golden/fixture_specs/backlog/candidates.md` | **migrated** — SPEC-DOC-031/035 fixtures |
| `tests/integration/test_governance_intake_not_gitignored.py` | **adjusted in place** — asserts `BACKLOG.md` is tracked |
| `tests/unit/test_backlog_classifier.py`, `test_backlog_subject_registry.py`, `test_backlog_models.py`, `tests/unit/backlog/test_classifier_clamp.py` | **untouched** — anchor semantics preserved (P2) |

No test is deleted to go green; every deletion above is a **supersession recorded in
TASKS** and dispositioned at closure (`dd-release-closure` › Test dispositions). Zero new
e2e tests — the CI backlog job's contract does not change (same verb, same exit codes).

### P15 — "Never-delete preserved" was not countable

**Type:** Unanswerable acceptance criterion · **D4 applied.**

The entry says "no record is lost", which no reviewer can verify. Measured baseline at
`feature/v0.12.0`: **31** live item files, **30** live index rows (25 candidates + 5 ideas,
the delta being P6), **46** files under `specs/backlog/_archive/`, **20** LEDGER lines,
plus three terminal tables in `candidates.md` (terminal-at-materialization, rejected,
intake-adjudication) and one history table.

**Resolution.** The criterion becomes a set equality proven mechanically: the slug set
discoverable **before** the consolidation (live files ∪ index rows ∪ archived files ∪
LEDGER lines ∪ terminal-table rows) equals the slug set in `BACKLOG.md` after it, each slug
appearing exactly once and in exactly one of `ACTIVE` / `LEDGER`. Both set differences must
be empty, captured as evidence.

---

## 3. Synthesis

**Core problem resolved:** the doctrine shipped in v0.10.0 and the tooling never followed,
so the law describes a file that does not exist while the CLI validates a model the law
retired — and one required protocol step points at a producer whose caller was deleted two
releases ago.

**Post-refinement status:** ready for approval. One release, two owners, one atomic cutover
commit.

**Declared dependencies:** #31 sequences with/after #30 inside this release (D1). Nothing
outranks at pick time: the bug ledger carries **zero** open bugs and both 2026-07 audits are
archived fully dispositioned by v0.8.0.

## ADRs recorded in this session

| ADR | Decision | Provenance |
|---|---|---|
| **D1** | One release covers both entries; the tooling/consolidation cutover is **atomic** (one commit), not dual-shape — bug-surface reduction outranks transitional compatibility | operator-delegated ruling, 2026-08-15 (goal directive); mechanism chosen by grill P3 |
| **D2** | The dead removal/consumption **write side is retired** (modules + container builder + tests); the reader survives; the `dd-release-definition` §5 checklist is rewritten to the mechanism that runs | operator-delegated ruling, 2026-08-15 (goal directive); verdict from grill P1 |
| **D3** | Release id `v0.12.0`; package version minted **0.9.0** at ship (from 0.8.0) | operator-delegated ruling, 2026-08-15 (goal directive) |
| **D4** | Never-delete is proven by a **countable** criterion (N_in = N_out, no record lost) | operator-delegated ruling, 2026-08-15 (goal directive); form fixed by grill P15 |
| **D5** | Per-entry files **and** `candidates.md` leave `specs/backlog/` by `git mv` into `_archive/` — archived, never deleted; SPEC-DOC-035 is re-pointed at the single-source invariant | operator-delegated ruling, 2026-08-15 (goal directive); shape chosen by grill P4 |
| **D6** | Feature-focused tests only; obsoleted per-entry-model tests are **listed as supersessions**, never silently pruned; zero new e2e | operator-delegated ruling, 2026-08-15 (goal directive) |
| **D7** | `intents[]`/anchor binding is **preserved**; the ACTIVE subsection gains one optional `**Intents:**` key, status gate unchanged | grill P2 — conservative option, **OD-1** |
| **D8** | BL-STALE is re-defined as "an ACTIVE item that is already consumed/dispositioned", reading the archived ledger, the LEDGER section and terminal Status tokens | grill P8 |
| **D9** | The governance re-target rides the **same commit** as the document; SPEC-DOC-035 becomes the single-source invariant | grill P4 |
| **D10** | `check_backlog_schema` (SPEC-DOC-012/022/023) retires with `candidates.md`; entry #4's residual is recorded, not edited by PE | grill P5, **OD-2** |

## Open decisions flagged

- **OD-1 — `intents[]` in the canonical ACTIVE schema.** The ratified
  `dd-backlog-definition` §2 has five keys and no intents; entry #30 asks for the binding to
  be preserved. The conservative option (preserve, as an optional sixth key) is taken here.
  If the operator instead rules that the backlog carries no typed intents, a follow-up
  retires `subject_registry.py`, `classifier.py`, `cli/anchors.py`, the alias map and the
  `backlog subjects` verb, and BL-DUP/BL-CONFLICT collapse to slug-level checks. **The
  decision is reversible in that direction only** — which is why it is taken this way.
- **OD-2 — entry #4 `retire-dead-hotfix-surface` is partially delivered as a side effect.**
  SPEC-DOC-022/023 disappear with `check_backlog_schema`; the CLI hotfix verb and templates
  remain. #4 must be rewritten down to that residual by `project-manager` (backlog curation
  surface). Recorded in SPEC §7 and as a closure obligation.

## Next steps

1. SPEC → PLAN → TASKS authored from this refinement (done in the same session).
2. Definition commit on `feature/v0.12.0` (T-120-01), then `dadaia-gitflow` milestone (a).
3. Implementation per TASKS, with the atomic cutover at T-120-08.
