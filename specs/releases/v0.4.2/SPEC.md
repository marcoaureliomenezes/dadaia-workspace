# SPEC — Release v0.4.2 — residual-convergence

**Status:** Aprovado
**Approval provenance:** operator-delegated, 2026-08-16 (resolva todos — goal directive)
**Release ID:** v0.4.2
**Owner:** product-engineer
**Opened:** 2026-08-16
**Created:** 2026-08-16
**Branch:** `feature/0.4.2` (cut from `develop` at `36412845`; branch contract: `dadaia-gitflow`)
**Consumes:** backlog-grammar-single-writer-seam, denylist-masking-predicate-parity, derived-values-computed-not-stored, knowledge-duplication-doc-pass, flat-release-ship-task-evidence, intake-signal-calibration, amnesty-multi-path-blob-fail-closed, git-batch-epipe-swallow-width, self-scan-sentinel-archive-authored-blobs, document-parser-fence-filter-complexity, retire-dead-hotfix-surface, changelog-version-axis-reconciliation, spec-doc-031-citation-classes
**Picked set:** **14 entries** — the 13 declared above (full picks, purged from `## ACTIVE` in
the same commit as this SPEC) plus `baseline-carve-out-review-cadence` (#24) as an explicit
**partial pick** (§7). **No bug is picked, because there is no open bug**: the PM-curated
pick-precedence notice in `BACKLOG.md` (2026-08-15) records zero open bugs; confirmation is a
named task step (GRILL OD-3). **No audit is outstanding** — every audit lives under
`specs/audits/_archive/`, verified at pick time. Pick-time priority (`DADAIA.md` §5) is
satisfied with nothing outranking.
**Grill (mandatory, done):** `specs/releases/v0.4.2/GRILL.md` — 29 Phase-0 findings (P1–P29),
five operator pre-rulings ratified as **R1–R5**, ten grill decisions **D1–D10**, four open
decisions **OD-1…OD-4**. None of them is re-litigated here.

---

## 1. Problem and context

**The operator's law for this release, verbatim and binding:**

> "resolva de forma inteligente, retire complexidade, diminua superficie de bugs, o simples
> é sempre melhor se atente nossas funcionalidades"

> "Na proxima rodada não quero ver essa desgraça de erros e bugs residuais"

The last three release cycles each shipped clean and each produced a residual list longer than
the one before. Read one by one those residuals look like fourteen unrelated defects. Read as
a set they are **three root causes**, and every one of them is a *class* that will keep
manufacturing instances until it is fixed at the root:

**Class 1 — knowledge stated twice, drifting apart.** The backlog grammar is parsed in one
fence-aware place and *written* in three private regexes (GRILL P1). The push gate's masking
predicate is a second, narrower copy of its own detection predicate (P8). A derivable number —
`token_estimate` — is hand-maintained in atom frontmatter and faithfully copied by two catalog
generators, measured 37 % and 42 % wrong on consecutive releases (P21). Four skill/persona
surfaces still describe a backlog shape retired two releases ago (P24, P25, P26, P27). Nothing
here is a bug in the ordinary sense; each is the same defect — *a fact with more than one
writer*.

**Class 2 — a process order that freezes the artifact before it is reviewed.** Three
consecutive releases archived the release directory *before* the pre-PR six-axis review ran,
so the review's first reader hit a FROZEN closure and every finding cost a reopen (three paid
reopens). The same cadence never stated that a dispatcher relaying work for a shell-less
sub-agent must commit its reservation flips, so the marker trace kept going missing.

**Class 3 — a review pipeline that manufactures intake volume.** Reviews correctly record
everything they see. The routing doctrine then sends *everything* to the PM's intake report,
so INFO-grade, awareness-only and already-fixed-at-HEAD observations arrive at the operator's
desk as demand. The volume the operator objected to is produced by the routing, not by the
defects.

Around those three sit the correctness residuals of the v0.11.0/v0.12.0 ship reviews — an
amnesty that leaks across paths through a shared blob, a scan-path failure that degrades
silently, a self-scan sentinel blind to archive-authored content, a privacy pattern that
covers one operating system's home layout while the product declares three — plus a quadratic
parser filter, a dead CLI verb that nags every consumer workspace unconditionally, a CHANGELOG
whose version headers no longer state what any published package contains, and a doctor check
whose free-text matching generates its own twelve-warning backlog.

**Why now.** Every item above is already adjudicated by the operator. Deferring any of them
means the next round's review finds it again and the residual list grows a fifteenth entry.

---

## 2. Objective

Fix the three root-cause **classes** and the correctness residuals that ride with them, so the
next cycle's reviews have less to find and the intake report they feed carries only actionable
demand. Every fact in scope ends the release with exactly **one writer**; the release lifecycle
reviews before it freezes; and record-only observations terminate where they are recorded.

The release is measured as much by what it **deletes** as by what it adds (R5): a dead CLI
verb and two templates, a per-atom stored value, a second masking predicate, three private
grammar copies, a section-exclusion special case, and a 20 %-drift warning that existed only
because the value was stored by hand.

Ownership is split by artifact class (`DADAIA.md` §2): `software-engineer` owns production
Python, the CLI, the doctors and the tests; `ai-engineer` owns **every** skill, persona and
projected-rule edit; `project-manager` owns any backlog-file mechanics after this definition
commit; `qa-engineer` closes `alpha-1`; `code-reviewer` reviews the delta **before** the
archive move; `product-engineer` authors this definition, the memory window and the closure.
No agent writes outside its lane.

---

## 3. Scope

**Standing scope rule for every zero-hit acceptance criterion.** Each grep-based criterion is
evaluated over the working tree **excluding** `specs/_archive/**`, `specs/bugs/**`,
`specs/backlog/_archive/**`, `CHANGELOG.md` and `specs/releases/v0.4.2/**` — this release's own
documents must be able to quote the symbols they retire.

**Standing green rule.** `dadaia ci preflight` (`ruff format --check`, `ruff check`,
`mypy --strict`, `pytest`), `dadaia backlog doctor`, `dadaia specs doctor` and
`dadaia public doctor` are green at **every** commit. No `--no-verify`, ever.

**Standing simplicity rule (R5).** Where a fix can be made by deleting, it is made by deleting.
No new module, no new CLI verb, no new doctor code, no second parse path, and no new e2e test
enters this release.

---

### FR1 — One backlog grammar, one writer, verified by re-parse

*(entry `backlog-grammar-single-writer-seam` #38; GRILL P1–P4, D1, D2)*

The ACTIVE/LEDGER grammar gets exactly one owner. `backlog_new` **moves** out of
`features/spec_artifacts/new_artifacts.py` into `features/backlog/` (D1 — the feature that
already owns `document.py`), where it locates its insertion point through the parser's
**fence-aware** structure rather than a private `## LEDGER` regex, and its slug-membership
check through the parsed document rather than two more private regexes.

Every write verifies itself: after writing, the writer **re-parses its own output** and raises
if the fresh slug is absent from `ACTIVE` (write-then-verify). Riders: `_SLUG_RE.fullmatch`
(a trailing newline stops being accepted) and a **redacted** path in the unreadable-document
diagnostic. `new_artifacts.py` keeps `release_new` only; the CLI wiring moves with the
function and the `[ok] created:` / `[error]` contract is byte-identical.

**Acceptance**

- A1.1 A `BACKLOG.md` whose Description quotes a fenced example containing a `## LEDGER` line
  receives a new entry **after** the real `## LEDGER`-anchored insertion point — i.e. inside
  `## ACTIVE` — and `load_document` finds the fresh slug. RED first: the pre-fix writer places
  it inside the fenced example.
- A1.2 The writer raises (non-zero CLI exit, nothing silently reported as created) when a
  re-parse of its own output does not contain the fresh slug.
- A1.3 A tree-wide grep (standing exclusions) shows **no** module outside
  `features/backlog/document.py` compiling a regex over `^###`, `^##[ \t]+LEDGER` or the
  `·`-separated LEDGER row shape.
- A1.4 `dadaia backlog new <slug>\n` — a slug argument carrying a trailing newline — is
  **refused** with the unchanged `^[a-z][a-z0-9-]+$` message.
- A1.5 An unreadable `BACKLOG.md` produces a diagnostic carrying no absolute filesystem path.
- A1.6 `lint-imports --config setup.cfg --no-cache` is green with **no new** accepted import
  edge added to `setup.cfg` (D1's whole point).
- A1.7 `dadaia backlog new` on an existing document still leaves every other byte unchanged
  (the v0.12.0 A3.2 byte-diff assertion passes unmodified) and still refuses a slug present in
  `ACTIVE` **or** `LEDGER`.

### FR2 — A derived value has zero stored copies

*(entry `derived-values-computed-not-stored` #43; GRILL P21–P23, D5)*

`token_estimate` stops being stored in atom frontmatter and becomes a value the catalog
**computes** from the atom body. The computation exists once, in the package, and the second
catalog generator (`public/scripts/generate-memory-catalog.py`) is pinned to produce an
identical catalog for the same tree. The lint drift check (`lint-memory-atoms.py`'s 20 %
warning) is **deleted** — with no stored copy there is nothing to drift.

Execution is two-phase and phase-forced (P22/P23): the code half rides IMPLEMENTATION (catalog
computes; the frontmatter key becomes **optional** in `memory-frontmatter-v1`; the drift check
goes); the memory half rides **CLOSURE** (the key is stripped from every atom, removed from
the schema's `properties`, and `catalog.json` is regenerated).

**Acceptance**

- A2.1 The catalog generator's `token_estimate` for every atom equals the computed value from
  that atom's body, regardless of what the frontmatter says — proven by a fixture atom whose
  frontmatter declares a deliberately wrong number.
- A2.2 The package generator and `public/scripts/generate-memory-catalog.py` produce
  **byte-identical** catalogs for the same fixture tree (parity test).
- A2.3 `token_estimate` no longer appears in `memory-frontmatter-v1.schema.json` (neither
  `required` nor `properties`) and no atom under `specs/memory/**` carries the key — a
  zero-hit grep — after the closure half.
- A2.4 `lint-memory-atoms.py` contains no drift check and no `_estimate_tokens` duplicate; a
  grep for `token_estimate` across `dadaia_workspace/public/scripts/**` returns only catalog
  emission.
- A2.5 `dadaia specs doctor` is green at **both** phases — with the key present and optional
  (after the code half) and with the key absent (after the memory half).

### FR3 — One authoritative statement per fact (the knowledge-duplication pass)

*(entry `knowledge-duplication-doc-pass` #44; GRILL P7, P24–P27, D6 ordering)*

Six surfaces state the same facts as their owners state them:

1. **`dd-release-closure`** — the `## Dispositions` template row stops naming a per-entry
   `specs/backlog/<slug>.md`; a disposition **adds** a LEDGER line and **removes** the ACTIVE
   subsection. The standing note is folded in: a closure's archive move adds one SPEC-DOC-031
   per non-terminal slug the archived documents name **under the FR14 semantics**, so the next
   closer measures *after* the move. *(ai-engineer)*
2. **`dd-release-definition` §5** — "Flips each fully-consumed slug's `## LEDGER` line" is
   replaced by the shipped mechanism (adds a LEDGER line, removes the ACTIVE subsection), and
   the SPEC-DOC-031 paraphrase is rewritten to what FR14 ships. *(ai-engineer, after FR14)*
3. **`public/agents/product-engineer.md`** — the file-hierarchy tree drops `candidates.md`
   and states the single-source `BACKLOG.md` (P25). *(ai-engineer)*
4. **`features/backlog/preview.py`** — `_format_yaml_error` stops being an underscore-private
   symbol imported by a sibling leaf: it is exported as API (or lifted to a shared leaf), and
   `document.py` imports a public name. *(software-engineer)*
5. **`features/telemetry/store/schema.py:93,102`** — the two DEAD markers stop pointing at the
   archived `backlog/candidates.md`. *(software-engineer)*
6. **`specs/assets/architecture/doctor-decomposition.md`** and the `sdd-gate-v3` atom wording
   are **memory-window** work and are listed in §5, not here.

**Acceptance**

- A3.1 A grep (standing exclusions) for `candidates.md` across `dadaia_workspace/public/**`
  and `dadaia_workspace/features/**` returns zero hits outside historical code comments that
  name it as *retired*.
- A3.2 No module imports an underscore-prefixed symbol from a sibling module inside
  `features/backlog/` — grep for `import _` across that package returns zero hits.
- A3.3 `dd-release-closure` and `dd-release-definition` describe the ACTIVE→LEDGER mechanism
  in the same terms as `sdd-bug-backlog-governance`; a reviewer following either skill
  literally executes the shipped sweep.
- A3.4 `dadaia public stage` → `install --target all` → `doctor` green, including
  `[ok] public-privacy`; every projection matches its staged source.

### FR4 — The masker never renders what the detector would catch

*(entry `denylist-masking-predicate-parity` #39; GRILL P8, P9, D3)*

The gate-side path masker consumes the **detector's own compiled matchers** rather than a
second, narrower predicate (D3): case-insensitivity and word-boundary treatment become
identical by construction. `core/redaction.compile_candidates` and `cli/redact.py` are
**untouched**, so the CLI's `--redact` output stays byte-identical by design.

`GitObjectReadError` carries the offending path as a **structured field** instead of embedding
it in the message, and every refusal channel masks it at the single render boundary — neither
the git-failure refusal nor the prior-side desync error interpolates a raw exception string or
a raw blob path.

**Acceptance**

- A4.1 Paired fixtures: for a denylist term `acme`, a path segment `Acme-Corp` (upper-cased
  **and** hyphenated) that the detector matches is **masked** in the rendered refusal.
  Detector-hit implies masker-hit for every fixture in the pair set.
- A4.2 A `GitObjectReadError` raised while reading a blob at a denylisted path produces a
  refusal in which that path is masked; the message contains no raw path and no raw
  `repr(exception)`.
- A4.3 `cli/redact.py`'s existing tests pass **unmodified**, and `core/redaction.py` is
  unchanged in this release (`git diff` empty for that file).
- A4.4 The one-hit-per-object refusal shape, the `first…last` term masking and the
  `[REDACTED-PATH-n]` placeholder contract are unchanged.

### FR5 — Review before archive; a reservation is committed before the next relay

*(entry `flat-release-ship-task-evidence`; GRILL P16, D8; ADR R3)*

The release-finalization order becomes canon in the skill surface (D8 — `release_new` emits no
TASKS template to reorder):

- the pre-PR **six-axis code review of the delta runs before** the `git mv` archive step; only
  ship steps follow it, so a finding lands on a thawed tree;
- a dispatcher relaying work for a **shell-less sub-agent** (e.g. `product-engineer`) commits
  that sub-agent's TASKS reservation flip **before** relaying the next work item, so the marker
  trace stays observable.

Both statements land once each: the ordering in `dd-release-implement` §4 and
`dd-release-closure`'s finalization-order paragraph; the reservation obligation in
`dadaia-task-manager`. `sdd-bug-backlog-governance` records the cadence at **closure** (§5).

**This release dogfoods the canon**: its own `TASKS.md` places the code-review task before the
closure/archive task, with only ship steps after.

**Acceptance**

- A5.1 `dd-release-implement` §4's `rc-N` ship row and `dd-release-closure`'s finalization
  paragraph state the same order — review → closure → archive → ship — with no third,
  contradicting statement anywhere in `public/**` (grep for "archive" near "review").
- A5.2 `dadaia-task-manager` states the shell-less-dispatcher reservation obligation exactly
  once.
- A5.3 This release's `TASKS.md` order matches the canon, and its code-review task is `[x]`
  before its closure task is started — verifiable from the marker trace in git history.
- A5.4 Projections refreshed and `dadaia public doctor` green.

### FR6 — Only actionable defects reach intake; record-only observations terminate in CLOSURE

*(entry `intake-signal-calibration`; ADR R4)*

The residual-routing doctrine gains one distinction, stated identically in three places:

- reviews still find and record **everything** — never-silent holds, zero observations lost;
- **record-only** observations (INFO-grade, awareness-only, already-fixed-at-HEAD) terminate in
  the release CLOSURE record or the reviewer handoff and **never** enter a PM intake report;
- only **actionable defects** (LOW+ with a concrete fix surface) are compiled for operator
  adjudication.

Surfaces: `dd-release-closure`'s `## Intake candidates` section contract (which gains a
**Record-only observations** heading that terminates there), `dd-backlog-definition` §5's
intake protocol, and the reviewer personas' routing guidance (`code-reviewer`,
`security-reviewer`, `qa-engineer`, `project-auditor`). All `ai-engineer` lane.

**Acceptance**

- A6.1 The three surfaces state the same three-way routing; a grep finds no surface still
  instructing that *every* observation becomes an intake item.
- A6.2 The reviewer personas keep their never-silent obligation explicitly — the findings array
  still carries every observation.
- A6.3 **This release's own closure** exercises the calibration: `CLOSURE.md` carries a
  populated **Record-only observations** section, and its `## Intake candidates` list contains
  only actionable defects. Zero observations lost is provable by comparing the reviewer
  handoffs' finding counts against the closure's two sections.

### FR7 — No amnesty for a multi-path blob (fail-closed)

*(entry `amnesty-multi-path-blob-fail-closed` #40; ADR R1; GRILL P10, D4)*

Prior-published-term amnesty stops leaking across paths through a shared blob. The object
reader surfaces multi-path reachability inside the pushed range, and a blob reachable at **more
than one path** receives **no prior text at all** — fail-closed, per R1 and D4, implemented
entirely in the adapter with **zero** change to the matcher or its amnesty predicate. Never a
per-sha amnesty.

**Acceptance**

- A7.1 A blob reachable at two paths in the range, whose value is amnestied at one of them,
  **refuses** — and the outcome is identical when the two paths' names are swapped so the tree
  sort order inverts (the tree-order-independence fixture).
- A7.2 A single-path blob's amnesty behaviour is unchanged: every v0.11.0 amnesty test passes
  **unmodified**.
- A7.3 `denylist_scan.py` is unchanged in this release except where FR4 requires it (`git diff`
  shows no amnesty-predicate edit), and the module still contains no amnesty/allowlist list
  (the v0.11.0 A4.1 source-scan contract test passes unmodified).
- A7.4 The gate atom records the semantics at closure (§5), restoring the truth of its "a new
  path still refuses" sentence.

### FR8 — A scan-path degradation is never silent

*(entry `git-batch-epipe-swallow-width` #41; GRILL P11–P13, anchor correction P12)*

Three narrowings, one class — *the gate never reports coverage it did not achieve*:

1. `_read_oversized_blob_prefix` inspects the `git cat-file blob` exit status and raises the
   typed read error when the process **failed and fewer than cap bytes arrived**. The
   intentional early close (EPIPE after the cap) stays the **only** swallowed shape.
2. A malformed context registry no longer shrinks the foreign-name layer silently: exactly one
   stderr note names the degradation, and the scan still proceeds.
3. An unparseable `--batch-check` row is typed-or-counted, never invisible — at its real sites
   (`_blob_info`, `_resolve_prior_texts`; P12), consistent with the FR8 abort-on-desync
   philosophy already shipped for `_read_blob_chunk`. A legitimately non-blob row (a tree) and
   a documented `<spec> missing` row stay ordinary filtered outcomes, not errors.

**Acceptance**

- A8.1 RED tests on a **nonexistent oid** and on a **tree sha** prove the typed error is raised
  rather than a 0-byte "partially scanned" prefix returned.
- A8.2 An oversized blob read that delivers the full cap still succeeds and still reports its
  honest partial coverage — the EPIPE path is not broken (existing v0.11.0 FR4 tests pass
  unmodified).
- A8.3 A malformed registry file produces exactly one stderr note naming the degradation; a
  healthy registry produces none; neither crashes the push hook.
- A8.4 A malformed `--batch-check` row in `_blob_info` raises the typed read error naming the
  row; a `missing` row in `_resolve_prior_texts` is still treated as absence.

### FR9 — The self-scan sentinel sees archive-authored blobs

*(entry `self-scan-sentinel-archive-authored-blobs` #45; GRILL P14)*

The repo self-scan sentinel stops excluding `specs/_archive/**` wholesale. A path under an
archive prefix is scanned **iff its blob is new at HEAD** — precisely: its blob sha is absent
from `HEAD^`'s tree. A rename/relocation into the archive republishes an existing sha and stays
excluded (the FROZEN↔scan invariant is preserved); a CLOSURE or QA document **authored**
directly into the archive is scanned like any other new blob. An unavailable `HEAD^` (shallow
or initial commit) degrades to today's behaviour and never to a failure.

**Acceptance**

- A9.1 A file planted under `specs/_archive/` carrying a baseline-matching literal **fails**
  the sentinel.
- A9.2 A `git mv` of an existing file into `specs/_archive/` does **not** fail the sentinel.
- A9.3 With `HEAD^` unavailable the sentinel behaves exactly as before this release.
- A9.4 The `tests/**` shrink-only baseline is unaffected by this FR (its row count changes only
  by FR10's declared fixtures, D9).

### FR10 — The privacy baseline covers every declared-support platform

*(entry `baseline-carve-out-review-cadence` #24 — **partial pick**, cross-platform half only;
GRILL P15, D9, D10)*

`home-abs-path` covers `/home/<user>` while the product declares Linux, macOS and Windows
support, so on macOS and Windows the layer that should catch an operator's local path never
fires. The baseline gains pattern variants for `/Users/<name>` and `C:\Users\<name>`, each with
the same placeholder carve-outs the `/home` pattern already documents, each **single-line**
(the push scan matches line by line), and each with a **paired fixture proving it fires**. The
baseline is bumped to `version: 5` with its `_header.excludes` rationale extended.

`/root` is **evaluated and excluded** (D10): it carries no user-identifying segment and would
false-positive on container documentation.

**Acceptance**

- A10.1 A positive fixture per new pattern fires; a placeholder form (`/Users/username`,
  `C:\Users\username`) does not.
- A10.2 Every baseline pattern remains a single line and `dadaia public doctor` stays green
  including `[ok] public-privacy`.
- A10.3 `_TESTS_SCOPE_BASELINE` grows by **exactly** the rows this release's new fixtures
  require, each row named in TASKS; QA verifies the delta is that set and nothing else (D9).
- A10.4 The `version` field reads `5` and `_header.excludes` documents the new carve-outs and
  the `/root` boundary.

### FR11 — The parser stops being quadratic, and pays PyYAML once

*(entry `document-parser-fence-filter-complexity` #42; GRILL P5, P6, D7)*

`_outside_fences` replaces its per-marker linear `any()` rescan with a **bisect** over sorted
fenced-range starts, and `load_document` uses `yaml.CSafeLoader` when available (falling back
to the pure-Python loader otherwise). The slug/status-only second parse mode is **declined**
(D7) — a second reader of the grammar is the class this release exists to remove.

**Acceptance**

- A11.1 A 140 KB synthetic document parses in **well under one second** (budget regression
  test, generous headroom so it is not a flake generator).
- A11.2 `load_document`'s output is unchanged on every existing fixture — the whole parser test
  module passes unmodified.
- A11.3 `CSafeLoader` absence is exercised (a test forcing the fallback) and produces identical
  results.
- A11.4 Exactly one parse path exists: a grep shows no second slug/status-only reader.

### FR12 — The dead hotfix-release surface is deleted

*(entry `retire-dead-hotfix-surface` #4; GRILL P17)*

The hotfix-*release* lifecycle was revoked by operator ruling D4 at v0.6.0; a bug fix is Arm B
run on `hotfix/{M.m.p}` with no ceremony. What survives on disk is dead surface that actively
misleads: the `dadaia specs hotfix open` verb whose `candidates.md` pre-condition block now
prints a WARNING **unconditionally in every workspace**, advising the creation of a file class
that trips SPEC-DOC-035.

Deleted, with their tests: `hotfix_app` and `hotfix_open` (`cli/commands/specs.py`),
`scaffold_hotfix_release` and `_HOTFIX_TASKS_STUB` (`features/specs/scaffolder.py`),
`public/templates/release_hotfix.md.j2`, `public/templates/closure_hotfix.md.j2`, and the
affected golden (`tests/unit/infrastructure/_golden/doctor_all_four_v0158.json`) is
regenerated.

**Acceptance**

- A12.1 A tree-wide grep (standing exclusions) for `hotfix_app`, `hotfix_open`,
  `scaffold_hotfix_release`, `_HOTFIX_TASKS_STUB`, `release_hotfix.md.j2`,
  `closure_hotfix.md.j2` and `Hotfixes pendentes` returns **zero** hits.
- A12.2 `dadaia specs --help` no longer lists a `hotfix` group; `dadaia specs hotfix open`
  exits non-zero with an unknown-command error.
- A12.3 No workspace command prints a `candidates.md` warning any more — grep for
  `candidates.md` across `dadaia_workspace/cli/**` returns zero hits.
- A12.4 `dadaia public stage` / `install --target all` / `doctor` are green with the two
  templates absent, and the regenerated golden matches the shipped asset set.
- A12.5 `dadaia specs release open`, `specs scaffold` and every other `specs` verb behave
  exactly as before (their tests pass unmodified).

### FR13 — One version axis: the PyPI lineage

*(entry `changelog-version-axis-reconciliation` #11; ADR R2; GRILL P20, OD-3)*

Per R2 the **PyPI lineage is the only axis**: the package is minted **0.4.2** at ship
(`pyproject.toml` already reads `0.4.2` at the branch cut) and the release id **is** the minted
version — `v0.4.2`. ADR-2's two-axis split is retired.

`CHANGELOG.md` is reconciled **without rewriting history**: one clarifying preamble, placed
directly under the file header, states that the `[0.5.0]`–`[0.9.0]` headers were minted
internally and **never published to PyPI**, maps them to their internal spec-release ids, and
declares that from `0.4.2` onward one section corresponds to one published package version. No
existing section is renamed, renumbered or deleted. The `[0.4.2]` section is added at ship.

**Acceptance**

- A13.1 The preamble states **measured** fact: the published version list is read from the
  package index at implementation time and captured as evidence (OD-3).
- A13.2 No existing `## [x.y.z]` heading is renamed, renumbered or removed —
  `git diff CHANGELOG.md` shows only the added preamble and the added `[0.4.2]` section.
- A13.3 `pyproject.toml` reads `0.4.2` at ship and the release directory archived is `v0.4.2`.
- A13.4 The `pypi-distribution` atom retires the two-axis claim at closure (§5).

### FR14 — SPEC-DOC-031 counts consumption, not conversation

*(entry `spec-doc-031-citation-classes` #10; GRILL P18, P19, D6)*

`_archive_consumption_hits` stops scanning every line of every archived SPEC and CLOSURE for a
slug substring. A mention counts as consumption evidence only when it **asserts** consumption:

- an archived **SPEC's `**Consumes:**` declaration**, including its wrapped continuation lines
  (P19: slug-shaped tokens, backticks and prose tolerated); and
- an archived **CLOSURE's `## Dispositions` rows**.

The `## Backlog returns` exclusion is **deleted** as subsumed — a returns section is not a
`**Consumes:**` declaration. No new section-exclusion list is introduced (D6). Severity stays
**WARNING**; the check's id, its message shape and its ACTIVE-subsection iteration surface are
unchanged.

**Acceptance**

- A14.1 A planted archived SPEC whose `**Consumes:**` names a still-non-terminal ACTIVE slug
  **fires** SPEC-DOC-031; the same slug mentioned only in prose (non-goal, inheritance,
  provenance, backlog-returns) fires **nothing**.
- A14.2 A `**Consumes:**` declaration wrapped across two lines is read in full.
- A14.3 A CLOSURE `## Dispositions` row naming a non-terminal ACTIVE slug fires.
- A14.4 On the tree at HEAD, `dadaia specs doctor`'s SPEC-DOC-031 count drops to the
  genuinely-unconsumed set — the twelve documented false positives are gone, and the count is
  captured as evidence before and after.
- A14.5 `_BACKLOG_RETURNS_HEADING_RE` and its special-case branch no longer exist (zero-hit
  grep), and the check is measurably **shorter** than before.

### FR15 — The invariants this release must not break

1. **Never-delete** for records: no backlog entry and no bug is deleted. The 13 fully-consumed
   entries leave `ACTIVE` at this definition commit and gain `DELIVERED — v0.4.2` LEDGER lines
   at closure; #24 stays ACTIVE rewritten to its residual.
2. **`specs/_archive/**` is FROZEN.** Nothing under it is created, edited or moved by this
   release (FR9 only *reads* it).
3. **Operator-gated intake (ADR #15).** This release materializes **no** backlog entry. Every
   residual is listed in `CLOSURE.md` under FR6's two headings.
4. **No new surface.** No new CLI verb, no new doctor code, no new hook, no new script, no new
   e2e test. Every BL-* and SPEC-DOC id keeps its identity — FR12 deletes a CLI verb and two
   templates, never a check id, and FR14 changes SPEC-DOC-031's evidence surface without
   touching its id or severity.
5. **Test stewardship.** Every added test declares intent and size at birth; no test is
   deleted, skipped, quarantined or weakened outside a recorded supersession named in TASKS
   with a `qa-engineer` verdict.
6. **Green at every commit** (§3), including the pre-commit backlog gate on every commit that
   stages `specs/backlog/**`.
7. **Lane discipline.** `ai-engineer` performs **every** skill and persona edit; `PM` performs
   any backlog-file mechanics after this commit; `PE` writes only specs and memory.

**Acceptance**

- A15.1 `git diff --stat` over the release range shows zero modified paths under
  `specs/_archive/`.
- A15.2 No file is created under `specs/backlog/` other than the edited `BACKLOG.md`.
- A15.3 Every commit passes `dadaia ci preflight` and both doctors.
- A15.4 `dadaia backlog --help` and the BL-*/SPEC-DOC id sets are unchanged.
- A15.5 Test intents are declared for every added test; QA confirms no test was pruned to go
  green.

---

## 4. Out of scope (non-goals)

1. **`atomic_write_text` for the backlog writer** (D2). Landing it means adding file I/O to
   `core/` or breaking the `features/` layering; write-then-verify already closes the
   silent-loss class. Evaluated and declined — not forgotten.
2. **A slug/status-only second parse mode** for the backlog document (D7). A second grammar
   reader is the very class this release removes.
3. **The "suppress only if every path amnesties" amnesty form** (D4/R1). Not equally simple;
   the conservative fail-closed form ships.
4. **`/root` in the privacy baseline** (D10) — no user-identifying segment, real false-positive
   cost.
5. **The rest of `baseline-carve-out-review-cadence` (#24)**: the review cadence, the
   per-carve-out rationale check, and the internal-hostname dotted-chain structural fix stay
   ACTIVE as that entry's residual.
6. **`thin-wrapper-projected-scripts` (#6, not picked).** FR2 pins the two catalog generators to
   byte-identical output but does **not** restructure the script↔package relationship; the
   structural fix stays that entry's.
7. **`test-suite-remediation-stewardship` (#2, not picked).** The LARGE census is untouched;
   this release adds zero e2e tests, so it does not grow.
8. **`bug-picked-ledger-event` (#7), `commit-message-scanning-residual` (#21),
   `bugs-jsonl-whole-blob-per-append` (idea) and every other unpicked entry** — untouched and
   still ACTIVE.
9. **Law text.** `DADAIA.md` already describes the flow correctly; no projected law file is
   edited by hand (`DADAIA.md` §7).
10. **Memory writes during DEFINITION.** Every memory edit this release needs waits for CLOSURE
    (§5), except nothing — no memory atom is written at definition.

---

## 5. Memory files affected at closure

| File | Change | When |
|---|---|---|
| `specs/memory/product/sdd/sdd-gate-v3.md` | the post-M1 per-layer suppression sentence made exact; the **oversized-CURRENT-object never-amnestied** boundary stated; the FROZEN↔rename invariant generalized to content-addressed byte-identical copies; the **multi-path amnesty** semantics (FR7) recorded so "a new path still refuses" is true again; the FR6 masking-class sentence aligned to the shipped predicate (FR4); the baseline described as `version 5` with the cross-platform home patterns (FR10); the self-scan sentinel's archive-authored coverage (FR9) | **CLOSURE** |
| `specs/memory/product/sdd/sdd-bug-backlog-governance.md` | §Release And Audit gains the intake signal-class routing (FR6); §Merge Cadence gains the review-before-archive order and the shell-less-dispatcher reservation obligation (FR5) | **CLOSURE** |
| `specs/memory/product/sdd/specs-doctor.md` | SPEC-DOC-031's evidence surface restated as consumption-asserting (FR14) | **CLOSURE** |
| `specs/memory/product/distribution/pypi-distribution.md` | the ADR-2 two-axis split is **retired**: one axis, the PyPI lineage; the package/release-id identity recorded (FR13) | **CLOSURE** |
| `specs/memory/architecture.md` | the doctor-decomposition reference refreshed with the diagram | **CLOSURE** |
| `specs/assets/architecture/doctor-decomposition.md` | `check_backlog_schema()` box removed; the SPEC-DOC-029 / `spec_context.lease` staleness corrected in the same touch (FR3 item 6) | **CLOSURE** |
| every `specs/memory/**/*.md` atom | `token_estimate:` frontmatter key removed (FR2 memory half) | **CLOSURE** |
| `specs/memory/product/catalog.json` | regenerated with computed estimates | **CLOSURE** |
| `specs/memory/tech-stack.md` | no change — no dependency added or removed | — |
| `specs/memory/product/index.md` | no change — no product feature added or removed | — |
| `specs/memory/quality-assurance.md` | no change — the stewardship doctrine is applied, not amended | — |

### Closure obligations (not implementation FRs)

- **Disposition sweep.** The 13 fully-consumed entries reach `DELIVERED — v0.4.2` as `LEDGER`
  lines (their ACTIVE subsections left at this definition commit); `## Dispositions` records
  each with its evidence pointer, and states explicitly that **no bug and no audit** was picked.
- **Test dispositions.** Every deletion in FR12 and every migrated test module is recorded as a
  named supersession.
- **Intake candidates, calibrated (FR6/R4).** `CLOSURE.md` carries two sections: **Record-only
  observations** (terminating there) and **Intake candidates** (actionable defects only). This
  is the release that proves the calibration.
- **OD restatement.** OD-1…OD-4 are restated for the operator's ruling.

---

## 6. Dependencies and risks

| # | Item | Status / mitigation |
|---|---|---|
| D-1 | `product-engineer` has no shell | every git, CLI and measurement step is an explicit TASKS entry owned by the dispatcher, `software-engineer`, `ai-engineer` or `qa-engineer` |
| D-2 | FR14 must land **before** FR3's skill pass restates SPEC-DOC-031 | encoded as a TASKS precondition |
| D-3 | FR2's memory half and FR3's memory half both need the CLOSURE phase (P22) | both ride the single memory task, after `ACTIVE.md` reads `CLOSURE` |
| D-4 | FR1 moves a function across features | one commit, CLI wiring included; `lint-imports` green with no new edge (A1.6) |
| R1 | **The `backlog_new` move breaks the CLI contract** consumers depend on | A1.7 pins the byte-diff and refusal behaviour; the v0.12.0 A3.x tests ride along unmodified |
| R2 | **FR2's two-phase split leaves the tree red between phases** | the intermediate state is *optional-but-present*, valid under both schema and doctor (A2.5) |
| R3 | **FR14 under-detects** a genuinely consumed slug whose SPEC never declared it | accepted and recorded: `backlog doctor` BL-STALE covers the ledger side; the check is a WARN backstop, and false negatives cost less than the twelve false positives it removes |
| R4 | **FR10's new patterns generate false positives** in the repo's own content | A10.1's placeholder fixtures plus the self-scan sentinel run prove the delta; D9 bounds the baseline rows |
| R5 | **FR9 makes the sentinel fail on every archived file** if "new" is defined loosely | A9.2's rename fixture is the guard; the definition is sha-absent-from-`HEAD^`, not path-based |
| R6 | **FR12's deletion takes a live control with it** | A12.5 pins every other `specs` verb by unmodified tests; the golden is regenerated, not hand-edited |
| R7 | **FR4's shared matchers change the CLI's redaction output** | A4.3 makes `core/redaction.py` a zero-diff file and keeps the CLI tests unmodified |
| R8 | **FR7 suppresses a legitimate amnesty** and forces a rewrite of published content | fail-closed is the operator's ruling (R1); the refusal's healing action is unchanged and the case is rare (a blob at two paths in one range) |
| R9 | **The review-before-archive canon is stated but not followed** by this very release | A5.3 makes the marker trace the evidence; QA and the code reviewer both check it |
| R10 | **The intake calibration silently loses an observation** | A6.3's count comparison between reviewer handoffs and the closure's two sections |
| R11 | **Zero-open-bugs is asserted, not measured** (OD-3) | a named task step runs `dadaia bugs status` and captures the output before the definition commit is pushed |

---

## 7. Traceability and provenance

| Entry | Provenance | Disposition in this release |
|---|---|---|
| `backlog-grammar-single-writer-seam` (#38) | intake-report #3 item 3-19 — operator adjudication, 2026-08-16 | **picked** · FR1 · `DELIVERED — v0.4.2` at closure |
| `denylist-masking-predicate-parity` (#39) | intake-report #3 item 3-6 — operator adjudication, 2026-08-16 | **picked** · FR4 (+ §5 atom wording) |
| `derived-values-computed-not-stored` (#43) | intake-report #3 item 3-16 — operator adjudication, 2026-08-16 | **picked** · FR2 |
| `knowledge-duplication-doc-pass` (#44) | intake-report #3 items 3-11/3-3/3-14/3-15/3-17 — operator adjudication, 2026-08-16 | **picked** · FR3 (+ §5 memory items) |
| `flat-release-ship-task-evidence` | v0.8.0 + v0.9.0 CLOSURE returns; intake #3 item 3-4 — operator adjudication, 2026-08-16 | **picked** · FR5 · dogfooded by this release's TASKS |
| `intake-signal-calibration` | operator demand, 2026-08-16 (root-cause class 3) | **picked** · FR6 · acceptance governs this release's own closure |
| `amnesty-multi-path-blob-fail-closed` (#40) | intake #3 item 3-5, semantics ruled fail-closed — operator, 2026-08-16 | **picked** · FR7 (ADR R1) |
| `git-batch-epipe-swallow-width` (#41) | intake #3 items 3-7 + 3-8 — operator adjudication, 2026-08-16 | **picked** · FR8 |
| `self-scan-sentinel-archive-authored-blobs` (#45) | intake #3 item 3-9 — operator adjudication, 2026-08-16 | **picked** · FR9 |
| `document-parser-fence-filter-complexity` (#42) | intake #3 item 3-18 — operator adjudication, 2026-08-16 | **picked** · FR11 |
| `retire-dead-hotfix-surface` (#4) | v0.6.0 law revocation residual; OD-2 rewrite executed at intake #3 | **picked** · FR12 |
| `changelog-version-axis-reconciliation` (#11) | v0.8.0 CLOSURE return, promoted by operator mandate | **picked** · FR13 (ADR R2) |
| `spec-doc-031-citation-classes` (#10) | v0.8.0 CLOSURE return; 12-slug debt folded at intake #3 item 3-10 | **picked** · FR14 · discharges the debt at the root |
| `baseline-carve-out-review-cadence` (#24) | v0.9.0 CLOSURE return; intake #3 item 3-1 folded | **PARTIAL pick** · FR10 delivers the cross-platform half; the cadence + dotted-chain half **stays ACTIVE**, rewritten to that residual (§4.5). **Not** declared in `**Consumes:**` (`dd-release-definition` §5 full-slug rule) |
| Open bugs | `specs/bugs/bugs.jsonl` | **none** — zero open bugs at pick time (PM notice 2026-08-15; confirmed by a task step, OD-3). No bug is superseded or dropped |
| Audits | `specs/audits/_archive/` | **none outstanding** — every audit archived and dispositioned |

**Purge-on-pick (`dd-backlog-definition` §2).** The 13 fully-consumed entries were removed from
`specs/backlog/BACKLOG.md` `## ACTIVE` in the **same commit** that creates this SPEC; this
section is the provenance record that removal requires. Their `LEDGER` lines are written by the
closure disposition sweep. Entry #24 remains ACTIVE, rewritten to its residual with a
partial-pick note naming this release.

**Version axis (ADR R2).** One axis: the release id `v0.4.2` **is** the minted package version
`0.4.2`. `pyproject.toml` already reads `0.4.2` at the branch cut; `CHANGELOG.md` gains its
`[0.4.2]` section at ship, above the reconciling preamble's explanation of the never-published
`0.5.0`–`0.9.0` headers.

---

## 8. Approval

**Approved by the operator on 2026-08-16** (operator-delegated, goal directive — "resolva
todos"), **as written**. SPEC, PLAN and TASKS all carry `**Status:** Aprovado`; milestone (a)
of the `dadaia-gitflow` contract may fire once the definition commit lands.

Ratified with the approval:

- **R1–R5 as given** — fail-closed multi-path amnesty; the PyPI lineage as the only version
  axis; review-before-archive as canon; the intake calibration contract; and the simplicity law
  that decides every remaining tie.
- **D1–D10** — the ten refinements this grill added, each recorded in `GRILL.md` §3 with the
  inspection finding that forced it.

Both classes of open item (**OD-1…OD-4**) are **recorded, not blocking**: none changes this
release's scope, and all four are restated at closure for the operator's ruling.
