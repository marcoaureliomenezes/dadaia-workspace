# T-050-35 — Six-axis code review on the thawed tree (release 0.5.0)

**Task:** T-050-35 · **Reviewer:** `code-reviewer` · **Branch:** `feature/0.5.0` (unpushed,
no PR) · **Range reviewed:** `02eef219..d981855c` (155 commits at review start;
158 at write time — see §0 delta) · **Reviewed at:** 2026-08-27, thawed tree, pre-archive.

## Verdict: **REQUEST_CHANGES**

Two blocking findings (**H-1**, **H-2**). Both are small and textual/mechanical; neither
re-opens an FR, a ruling, or an architectural decision. Everything else in the delta is
sound, and on the release's three named questions the answer is **yes, yes, and one
qualified yes** (§7).

`APPROVE` is withheld because `DADAIA.md` — the always-on law, highest precedence,
projected into every workspace and read every session — still directs agents to an
artifact this release retired (**H-1**), and because the release's own new suite ratchet
made `dadaia ci preflight` non-deterministically red on the very growth it measures
(**H-2**), which is the `DADAIA.md` §7 push-green precondition for the `feature/0.5.0`
push this review gates.

---

## 0. Target, method, and the concurrency delta

| | |
|---|---|
| Base | `02eef219` |
| HEAD at review start | `b9ffaf77` |
| HEAD at write time | `343acc38` |
| Static checks | run against a pristine `git archive` export of the reviewed commit, never the live working tree (a concurrent session was mid-edit throughout) |

**Delta note (one line, per dispatch).** Three commits landed mid-review and are folded
into the findings below rather than chased further: `c01fe20f` (FR23 firing 1 — architect
verdict on `8f7b5356`, docs only), `d981855c` (the histo redaction fix — **closes** the
open `backlog-histo-writer-skips-write-time-denylist-redaction`, and introduces **M-5**),
and `343acc38` (another session registering the same V30 flake **H-2** independently
found here — so **H-2** is now a *registered* pass-on-retry, not an unregistered one).

**Evidence produced by this review** (not merely cited):

```
ruff check .                     -> All checks passed        (pristine HEAD export)
ruff format --check .            -> 1002 files formatted     (pristine HEAD export)
mypy --strict dadaia_workspace   -> no issues, 279 files     (pristine HEAD export)
lint-imports                     -> 9 kept, 0 broken         (329 files, 1532 deps)
pytest -q tests   run #1         -> 1 FAILED / 2977 passed / 4 skipped  (93.7 s)
pytest -q tests   run #2         -> 2978 passed / 4 skipped            (123.1 s)
pytest -q tests/contract/test_test_suite_ratchets.py (standalone) -> 5 passed (8.9 s)
pytest --collect-only -q tests   -> 2982 collected in 5.95 s (wall 7.1 s)
dadaia bugs stats                -> 515 total · 9 open · 488 resolved
```

Inputs consumed: the four QA closes (`S1`–`S4`) and the `S2` re-verdict, `S1-FR23-firing.md`
and its two amendments, `S1-AR1-ruling.md`, the canon-v6 first audit, the five coverage
tables (T-050-16/19/21/28/32), and T-050-34's invariants capture.

---

## 1. Findings

### HIGH — blocking

#### H-1 · Dead code / architecture · `dadaia_workspace/public/data/DADAIA.md:214`

The always-on law still reads:

> *"Changelog and history live in `CLOSURE.md` and `_archive/`."*

`CLOSURE.md` was retired as a going-forward artifact by FR4/T-050-21 and FR12, and the
projected skill states the retirement explicitly at
`dadaia_workspace/public/skills/dd-release-implement/RELEASE-EVENTS.md:46`
(*"`CLOSURE-TEMPLATE.md`/`CLOSURE.md` retire at T-050-21 (FR12)"*). Two live assets now
disagree about a going-forward artifact, and **the law wins by precedence** — an agent
following `DADAIA.md` authors the retired file.

The contrast is the proof this is an oversight, not a decision: `ACTIVE.md` received the
complete sweep in the same release (`grep -c "ACTIVE\.md" public/data/DADAIA.md` → **0**;
line 42 now reads "the `RELEASE.jsonl` fold"), while `CLOSURE.md` did not. The same
residual is shipped to every consumer workspace at two more projection points:

- `dadaia_workspace/public/scaffold/constitution.md:122`
- `dadaia_workspace/public/scaffold/audits/AGENTS.md:22`

Projection is in sync (source and the installed root law are byte-identical), so this is
live in every session today, not latent.

**Fix direction.** Give `CLOSURE.md` the same one-sentence treatment `ACTIVE.md` got:
point line 214 at the `RELEASE.jsonl` `note` records (the surviving home
`RELEASE-EVENTS.md` §"note conventions" already enumerates) plus `_archive/` for
pre-canon history, and repoint the two scaffold lines. Re-stage and re-install. Do not
add a compatibility clause — the retirement is already complete in code; only the prose
lags.

#### H-2 · Tests / perf · `tests/contract/test_test_suite_ratchets.py:432`

V30's `test_v30_pyramid_shape_reported_from_collect_only` shells out to a nested
`pytest --collect-only -q -p no:cacheprovider tests` with a hardcoded `timeout=25`.

Observed, this session, at HEAD:

| Run | Result |
|---|---|
| full suite, run #1 | **FAILED** — `subprocess.TimeoutExpired … timed out after 25 seconds` |
| same file, standalone | 5 passed in 8.9 s |
| full suite, run #2 | 2978 passed |

Collection itself takes **5.95 s** unloaded. The failure is contention: a nested
whole-suite collection competing with the parent run (and, in CI, with `-n auto` xdist
workers) crosses 25 s. This is a **loud flake** in the `DADAIA.md` §7 sense, and it makes
`dadaia ci preflight` — the push-green precondition for the `feature/0.5.0` push this
review gates — non-deterministic.

It is also self-inflicted by this release's own scope: the A22.9 overshoot
(**+74 functions / +91 collected items**, T-050-34) is precisely what pushed the nested
collection's cost toward the ratchet's own wall clock. The test that measures the suite's
growth is the first casualty of it.

Now registered by a concurrent session as
`test-v30-pyramid-shape-collect-only-subprocess-times-out-under-nauto-contention`
(`343acc38`), which discharges §7's "unregistered pass-on-retry" clause — but the gate is
still non-deterministic, so the fix belongs to this release, not the next.

**Fix direction.** Remove the wall-clock timeout from a measurement that has no timing
contract, or replace the nested subprocess with an in-process collection (V26/V28 already
use AST inspection over the tree for exactly this reason — no subprocess, no clock). A
timeout raise is a symptom patch: the number would have to move again at the next suite
growth. Quarantining is available as a stopgap only, and it already carries its bug.

### MEDIUM

#### M-1 · Architecture · the `RELEASE.jsonl` reader count, and a docstring that asserts otherwise

The **fold semantics** are genuinely single-owner: `core/release_events.py` is the one
parse+fold, and it is a real reduction — the base commit had **three** independent
hand-parsers of `ACTIVE.md` (`doctor_common.read_active_md`, `hooks/sdd_gate._active_field`,
`features/reports/next.py`'s own read). That consolidation is the release's best structural
work and it holds.

What did **not** consolidate is the *discovery + disk read* shim. Four sites call
`parse_release_events` and three of them do their own `read_text` behind their own copy of
the same live-release-directory predicate:

| Site | Discovery scan | Own `read_text` | Ambiguity behaviour |
|---|---|---|---|
| `hooks/sdd_gate.py:165-183` | yes | yes | returns `("none","")` |
| `features/specs/doctor_common.py:65-113` | yes | yes (the declared "ONE" reader) | returns an error string |
| `features/reports/next.py:113-136` | yes | yes | raises `NoActiveReleaseError` |
| `features/specs/doctor_release.py:630-636` | glob | yes | skips on `OSError` |

Two of the three copies are **forced** by contracts this release should not break —
`hooks/**` may not import `features/**` (import budget, `test_hook_import_surface.py`), and
`features/reports` may not import `features/specs` (the 24/24 independence contract). So
the duplication is not itself a design error. **The defect is that the code claims
otherwise.** `doctor_common.py:85-95` states:

> *"every reader of these bytes goes through this one function … its only two (thin)
> callers … so the tri-state disk read is never duplicated"*

That is false at HEAD, in the same docstring that (correctly) names "N readers of one file"
as the defect AR-1 §4 exists to retire. Nothing pins the count: `grep -rl "ONE reader" tests`
returns zero hits.

The concrete drift risk is the exclusion set `("_archive", "_ideas")`, hand-written in three
places. FR6/T-050-14 is still `[ ]` and operator-pending; a fourth reserved directory name
means three edits, and a miss is silent.

**Fix direction.** Correct the docstring to state what is true (one *fold*; three
layer-mandated *reads*), and move the one thing that must agree — the live-release-directory
name predicate — into `core/` as a pure `str -> bool` (no I/O, so the core purity ratchet
holds; every layer already imports `core`). Then pin the count with a contract test, the way
`test_import_linter_ignore_cap.py` pins its own.

#### M-2 · Dead code · an uncalled container seam whose docstring names a caller that does not exist

`container.build_git_history_reader()` (`container.py:216`) has **zero** production callers:

```
grep -rn "build_git_history_reader\|history_reader=" dadaia_workspace/**/*.py   -> definition + 3 docstrings, no call
grep -rn "\.resolved_commit(" dadaia_workspace/**/*.py                          -> 0 hits
```

Its docstring (`container.py:227-233`) asserts:

> *"**T-050-17 (FR8/AS-1) is the first permanent, ongoing caller**: `BugService.resolved_commit`
> … the CLI composition root threads this exact adapter into `BugService(…)`"*

No composition root threads it. `BugService.resolved_commit` (`service.py:228`) is likewise
uncalled outside tests. This is the mirror of the defect A13.4 caught on the write side
("a store instance exists only where a writer exists") — S1's QA close verified A13.4 for
stores and the same rule was never applied to the reader port.

**Fix direction.** Either wire the caller the docstring promises, or delete the seam and the
public method and let `migrate_v5.py` keep the port it actually uses — and in both cases stop
the docstring from asserting a wiring that grep refutes. Prefer deletion: the port survives
in `core/protocols/git_history_reader.py` and `migrate_v5` constructs the adapter directly.

#### M-3 · Perf · latent N+1 in `BugService.resolved_commit`

`service.py:257-263` derives one record's commit by running a **whole-history** walk:

```python
provenance = derive_commit_provenance(
    self._history_reader.log_added_lines(self._repo_root, "specs/bugs/"),
    classify_ledger_line,
)
derived = provenance.get(record.id)
```

`log_added_lines` is documented at `git_subprocess.py:414-424` as **`≈2N+1` subprocess
calls** — accepted there for "the one-shot migration this port serves (AR-1 §3.4)". The
per-record wrapper then discards every entry of the map but one. Any batch caller — the
audit's pillar 1 stamps `resolved_commit` across the ledger, **515 records today** — pays
`records × (2N+1)` git subprocesses for a walk whose result was already complete on the
first pass.

Latent only because M-2 means there is no caller yet. It becomes real the moment the seam
is wired, and it is cheapest to fix before that.

**Fix direction.** Expose the batch shape the pure function already returns (a `Mapping`
over the whole ledger), or memoize the walk per service instance. Do not add a second
derivation path.

#### M-4 · Patterns · a second hand-kept canon map, new this release

`_CANON_SINGLE_FILENAMES` — the three-entry v6 slug→filename map — is written **twice**:

- `dadaia_workspace/features/specs/memory_lint.py:307`
- `dadaia_workspace/features/panel/views/_md_render.py:139`

Both are new (`git grep _CANON_SINGLE_FILENAMES 02eef219` → zero hits). The panel copy
documents its own duplication (*"kept here too since panel and specs are sibling features
that may not import one another"*), while the memory_lint copy's comment says it exists
*"instead of adding a second slug-resolution mechanism"* — and a second one was added
anyway, eleven lines of identical literal apart.

This is the "second map" T-050-35 asks about. The cross-feature import ban is real; the
correct home for a pure, domain-agnostic name map that two features need is `core/`, which
both already import.

**Fix direction.** One `core/` constant, imported by both. Three entries is exactly the size
at which a duplicate looks harmless and drifts silently.

#### M-5 · Patterns · a third copy of `_dataclass_field_names` (landed mid-review)

At HEAD-at-start the pure introspection helper existed twice: `core/models/findings.py:42`
and `core/models/bugs.py:102`. `d981855c` added a **third** at `core/models/backlog.py`, with
a docstring justifying it:

> *"Duplicated here rather than imported from either sibling: every `core/models/*.py` domain
> model stays self-contained, importing no OTHER `core/models` module (only the shared,
> domain-agnostic `core.redaction`/stdlib)."*

The rule is sound; the conclusion does not follow. `_dataclass_field_names` is a pure
`dataclasses.fields()` walk with **no domain content at all** — the same category as
`core.redaction`, which the very same commit correctly promoted to the shared home and which
all three models now import. The self-containment rule points at extracting the helper, not
at a third copy of it.

The rest of `d981855c` is good work and closes a real open bug: the histo writer now derives
its redactable field set from its own field metadata and masks through the one
`core.redaction.redact_text` primitive.

**Fix direction.** Move the helper next to `redact_text` in the shared domain-agnostic home;
delete all three copies.

#### M-6 · Security · redaction coverage is asymmetric across the four committed JSONL artifacts

| Artifact | Write path | Write-time redaction seam |
|---|---|---|
| `specs/bugs/BUGS.jsonl` | `BugService` → `JsonlRecordStore` | **yes** — `BugRecord.redact()`, schema-derived (A2.6) |
| `specs/backlog/_archive/backlog_histo.jsonl` | store | **yes, as of `d981855c`** — `BacklogHistoRecord.redact()` |
| `specs/audits/<slug>/FINDINGS.jsonl` | **agent file tools** (`core/models/findings.py:19`) | **no** — `grep -c redact findings.py` → 0 |
| `specs/releases/<id>/RELEASE.jsonl` | **agent file tools** | **no** |

The two seams that exist were each built *after* the same defect fired on that artifact
(BugRecord: three firings, T-043-23 → T-044-62 → T-045-19; histo: one, this release).
`FindingRecord` is the next member of the class by construction, and its `evidence` field is
the **highest-risk free text in the system** — audit evidence is command output, the natural
carrier of absolute paths.

The compensating control is real and S3 verified it (A13.5/V24, the push-gate denylist scan
over the audit folder). But it is *range-scoped to a `feature/*` push*, and this branch has
never been pushed — so it has not yet run over any of the 158 commits.

**Fix direction.** Non-blocking, because the control exists and the push will exercise it.
Record the asymmetry as an explicit decision rather than an implicit one — "FINDINGS/RELEASE
are agent-authored; the push gate is their sole control" belongs in the closure record or an
ADR, so the fourth firing of this class is a known accepted risk rather than a surprise.

#### M-7 · Patterns · the U+2028 fix is held by discipline across seven read sites

`read_text().split("\n")` (never `splitlines()`) is the root-cause fix for
`specs-doctor-bug-lane-splits-ledger-on-unicode-line-separators`. It is now hand-repeated in
four modules / seven sites:

```
core/release_events.py             1
features/bugs/migrate_v5.py        1
features/specs/doctor_governance.py 2   (two independent reads of BUGS.jsonl in one module)
infrastructure/jsonl_record_store.py 3
```

All seven are correct today — verified individually. Nothing enforces the eighth. This repo
already has the right pattern for exactly this (`test_atomic_write_census.py` is cited by
T-050-34 as the census precedent); it was not applied to the reader that motivated it.

**Fix direction.** One AST census test: no `splitlines()` on a path that reads a `.jsonl`.

### LOW

| id | Axis | Location | Finding |
|---|---|---|---|
| L-1 | Tests | `tests/contract/test_specs_cli_complexity_ratchet.py:60` | Docstring says "`#doctor` <= 30"; the pin at line 47 is `_DOCTOR_CEILING = 10`. The pin is right (T-050-34 measured `doctor` at 10, down from 30) — the prose is stale and understates the ratchet by 3×. |
| L-2 | Perf | `pyproject.toml` `max-complexity` | Held at 63 rather than ratcheted to radon's 61. **Correct call** — T-050-34 proved the literal ratchet breaks `ruff check` outright (`make_handler_class` is 63 under C901, 6 under radon), registered the tooling divergence as a bug, and documented it inline instead of pinning a number that breaks its own gate. A22.5 ("unchanged or lowered") holds. Recorded as a finding only so the next release does not re-attempt it blind. |
| L-3 | Architecture | FR15 (`T-050-25`, `T-050-25A`) | Declared "net-negative, ≈−200 LOC"; measured **+42** across the two task commits and **+236** across every FR15-named file over the full range (T-050-34 §V19). A22.3: *"a positive net inside an FR that declared itself net-negative is a defect."* Needs an operator disposition at closure — either the declaration was wrong (likely: a regex→structured-fold conversion adds dataclass/helper code the estimate did not anticipate) or the deletion is incomplete. The FR's other two claims (−59% regex count, −4 SPEC-DOC codes) were not re-measured and may well hold. |
| L-4 | Tests | A22.9 | The +74/+91 overshoot itself — see §3 for demotion candidates and the honest arithmetic. |

---

## 2. Axis-by-axis summary

| Axis | Verdict | Notes |
|---|---|---|
| 1 · Architecture conformance | **PASS with M-1** | `lint-imports` 9 kept / 0 broken over 329 files; `features/**` imports no `cli`/`infrastructure`/`hooks`; `core/**` stdlib-pure; independence contract 24/24 packages, ignore-edge cap 17. The generic `JsonlRecordStore[T]` with five container-composed instances is genuinely one mechanism, not five. |
| 2 · Design patterns | **M-4, M-5, M-7** | New module-level collections are overwhelmingly *derived*, not hand-kept (`frozenset(k.value for k in ReleaseEventKind)`, the `dataclasses.field(metadata=…)` mechanism) — this is the right direction and it is the release's second-best structural win. The three findings are the exceptions. |
| 3 · Test coverage | **H-2, L-1, L-4** | 2978 passing / 4 skipped; 29 test files added, 15 deleted; contract tier +120 functions. Coverage tracks the new public surface well (every new schema, model, fold and doctor code has a test). The problem is size and one flake, not gaps. |
| 4 · Security smells | **M-6** | Zero hardcoded credentials, zero raw SQL, zero unvalidated shell input in the delta. `redact_text` correctly masks IPv4, POSIX and Windows home paths, plus denylist terms. `specs/**` scanned for home paths, e-mail addresses and consumer slugs: none introduced by this release's own artifacts. |
| 5 · Performance | **M-3, H-2** | Hook import budget intact (`test_hook_import_surface.py`: no hook imports the container; the `sdd_gate` release read is a deliberate, tested exception). `specs.py#doctor` CC **30 → 10** — a large, real reduction. The `≈2N+1` history walk is documented and ruled acceptable for its one-shot use; only the per-record wrapper (M-3) turns it into an N+1. |
| 6 · Dead code | **M-2, H-1** | `ACTIVE.md` production residuals are provenance comments only — correct and useful. `migrate_v5.py` is *intentionally* deletable scaffolding, and its non-import by permanent consumers is pinned by a contract test — this is the model to copy, not a finding. `_fold_v5_events` lives inside that same scaffold, correctly. The genuine dead surface is the container seam (M-2). |
| 7 · Bug surface (FR24) | **mixed — §5** | |

---

## 3. The A22.9 overshoot — demotion candidates, with evidence

Measured: **+74 functions / +91 collected items / +12 files** over the T-050-03 baseline,
against a gate of "after ≤ before". The declared per-FR roll-up predicts +26, so **48
functions are unattributed**; T-050-34's reconciliation attributes them to bug-fix commits
(shape 3 = code + regression test), which by construction appear in no FR's `Tests:` line.
The contract tier's +120 supports that reading.

Candidates below are named on **structural evidence** — duplicated shape, or an already-declared
expiry. None is proposed to make a number look better, and none is a coverage reduction.

**Available now (≈ −4 functions):**

| Candidate | Evidence |
|---|---|
| `tests/contract/test_finding_record_schema.py` (3 fn) + `tests/contract/test_release_event_schema.py` (1 fn) + the in-flight `test_bug_record_schema.py` | Structurally identical: same `_SCHEMA_PATH` construction, same `Draft202012Validator.check_schema`, same `additionalProperties is False`, then per-property keyword assertions. One parametrized contract test over the `(schema, expectations)` triple keeps every assertion, collapses ~5 functions to 1–2, and gives the *next* packaged schema one home instead of a fourth copy. This is a merge, not a deletion. |

**Already scheduled (−6, on their own triggers — not this release's to take):**

| File | Fn | Expiry |
|---|---|---|
| `tests/unit/features/bugs/test_migrate_v5_provenance_scaffold.py` | 1 | `expires: 0.6.0`, dies with `migrate_v5.py` |
| `tests/integration/test_consumed_backlog_relocation.py` | 3 | `expires: 0.6.0`, retired at T-050-14 |
| `tests/contract/test_specs_cli_complexity_ratchet.py` | 2 | `expires: 0.6.0` (S1 FR23 amendment A7) |

Every `SCAFFOLD` in the tree carries a valid `expires:`, and V28 proves none names an
archived release — the expiry discipline is working.

**Census hygiene (0 functions, 1 double-count):** `tests/e2e/features/test_bound_context_visible_to_cli.py`
carries `pytestmark = [pytest.mark.integration]` *and* the directory auto-applied `e2e`
marker, so one function is counted in two tiers of every census (S4 §5.2).

**The honest arithmetic: −4 now and −6 later do not close +74.** A22.9's own protocol is
therefore the applicable one — the operator's **explicit, numbered acceptance recorded in the
closure record**, with the reconciliation naming bug-fix regression tests as the unattributed
source. Manufacturing deletions to reach a paper number is the accounting defect A22.9 was
written to prevent. **Recommendation: accept +74 explicitly, and carry the FR-attribution
gap (bug-fix commits contribute tests to no FR line) as an intake candidate — the roll-up
mechanism, not this release's test count, is what under-reports.**

---

## 4. CI status

No CI run exists: `feature/0.5.0` is unpushed for the entire release window, so the
`feature/**` matrix, `pr-source-guard` and the verdict-gate job have never fired on this
scope. Local preflight is the only gate exercised to date, and it is the one **H-2** makes
non-deterministic. The Windows xdist observation (`windows-xdist-workers-crash-on-unit-fast-tier`,
LOW, open) is trivially "no recurrence" by construction, not by fix — correctly stated as such
by T-050-34.

`dadaia specs doctor` carries 1 tolerated error (SPEC-DOC-024, `TASKS.md` legitimately
`Em revisão` during IMPLEMENTATION) and 493 warnings, **483 of which are SPEC-DOC-033** —
legacy pre-v6 bug records missing the new governance fields. WARN-only by design (D15) and
pre-existing, but 483 is large enough that it hides any new instance in the noise. Worth a
closure note and a bulk-backfill intake candidate; not a finding against this release.

---

## 5. Bug-surface delta, per touched feature (FR24)

Ledger evidence: `dadaia bugs stats` → **515 total · 9 open · 488 resolved · 13 superseded ·
4 rejected · 1 deferred**.

| Feature | Direction | Evidence |
|---|---|---|
| **bugs** (record model, FR2) | **reduced** | The record model replaced the event fold: one record per bug, write-once fields enforced in the model, governance mutation through one seam. The class that fired nine times — "N readers/writers of one ledger, each with its own parse" — now has one store, one model, one redaction seam. The `8f7b5356` CAS fix landed **inside the one primitive** rather than beside it (architect firing 1: SOUND), which is the shape that ends a loop rather than extending it. |
| **release phase / `RELEASE.jsonl`** (FR4) | **reduced, partially** | Three hand-parsers of `ACTIVE.md` → one pure fold in `core/`. That is a genuine collapse. But the *discovery + read* shim went from a fixed path to three copies of a directory predicate (**M-1**), and the docstring asserting single-ownership is false. Net: the semantic surface shrank, the coordination surface grew slightly. Not a regression; an incomplete consolidation. |
| **backlog** (FR5) | **reduced** | Single-section live photo + append-only histo retires the in-document `## LEDGER` dual-writer. `d981855c` closed the one open bug this feature carried, structurally (derived field set, shared primitive) rather than with a special case. |
| **hooks / chokepoints** (FR9) | **reduced** | Two blocking mechanisms removed, zero added; the pre-push fail-closed runner survives with its refusal asserted. Net −63 LOC — the only FR whose declared net-negative direction the measurement confirmed. `precommit-backlog-doctor-blocks-unrelated-commits` resolved; no new bug registered against this surface. |
| **specs doctor** (FR15) | **increased, mildly** | `doctor` CC 30 → 10 and four regex-prose checkers deleted — both real wins. Against that: LOC went **+236** where −200 was declared (**L-3**), and `doctor_governance` now carries two independent reads of `BUGS.jsonl` in one module (**M-7**). The feature is better structured and slightly larger than promised. |
| **AI surface** (FR11/FR12) | **reduced, with H-1** | `−347` net inside `public/`, `ACTIVE.md` swept to zero live citations. `CLOSURE.md` was not (**H-1**) — the retirement is complete in code and incomplete in the law that governs it, which is the highest-cost place for a residual to sit. |
| **test suite** (FR22) | **increased** | +74 functions, and the new V30 ratchet is itself the release's newest flake (**H-2**). Five ratchets landed and four of them are cheap AST checks that will keep paying; V30 is the one that bought its property with a subprocess. |

**Release-level answer.** The bug surface of the *core artifacts* (bugs, backlog, release
phase, hooks) went **down**, and it went down structurally — by deleting readers, collapsing
parsers and moving fixes into single primitives, not by adding branches. Two exceptions run
the other way and both are recoverable in this release: the doctor feature grew where it
declared shrinkage (L-3), and the test suite grew by 4 % while acquiring a flake (H-2).

**Nine open bugs, none introduced by this scope as a design defect:** two are concurrency /
git-index contention between agent sessions (an operating-model issue, not this release's),
two are measurement-tooling gaps found *by* this release's own honest measurement (mutmut
scope, radon-vs-C901), two are documentation staleness, one is the Windows xdist LOW, one is
the V30 flake (**H-2**), one is a bug-record evidence-field edge case. That distribution —
mostly *discovered by measuring*, not *caused by patching* — is the healthy shape.

---

## 6. The single-owner rule (SPEC D-B) — the direct answer

> *"Is there **any** place where a second code path was added — a second map, a second
> symlink check, a second denylist reader, a second record-update seam — that the
> single-owner rule was supposed to prevent?"*

**Yes, four, all small, none load-bearing on correctness today:**

1. **A second map** — `_CANON_SINGLE_FILENAMES`, twice, both new this release (**M-4**).
2. **A third copy of a pure helper** — `_dataclass_field_names`, now in three `core/models/`
   modules (**M-5**).
3. **A third `RELEASE.jsonl` read shim** — layer-mandated, but undocumented as such and
   asserted not to exist (**M-1**).
4. **A second hand-repeated fix** — `split("\n")`-not-`splitlines()`, seven sites, no census
   (**M-7**).

**And, importantly, several places where the answer is no:** there is exactly one denylist
masking primitive (`core.redaction.redact_text`, and `d981855c` moved the second candidate
*into* it rather than beside it); one record-update seam (`apply_governance_update` on both
record models, both deriving their field categories from their own metadata); one
`JsonlRecordStore` mechanism serving five artifacts; one symlink doctrine (A17.1, referenced
rather than restated); one fold for `RELEASE.jsonl`. The rule mostly held.

**Answers to the other two questions:**

- *Did the record model leave the bugs feature smaller than the event fold did?* **Yes** —
  smaller in concept (one record, no fold, no event vocabulary) even though +1338 LOC, which
  is canon-adding and expected under A22.3. The retired surface is the whole event-shape
  reader plus five test files' worth of fold semantics.
- *Did FR9 delete two blockers without weakening the publication boundary?* **Yes** —
  exactly two blocks removed, the pre-push fail-closed runner survives with its refusal
  asserted by a third fixture, `test_hooks_publication_boundary.py` 3/3 and
  `test_cli_output_stability.py` 8/8 green, zero new non-zero exits.

---

## 7. Summary

| Severity | Count | Ids |
|---|---:|---|
| CRITICAL | 0 | — |
| **HIGH** | **2** | **H-1**, **H-2** |
| MEDIUM | 7 | M-1 … M-7 |
| LOW | 4 | L-1 … L-4 |
| INFO | — | §3 demotion candidates, §4 CI/doctor notes |

## 8. Recommendation

**REQUEST_CHANGES.**

**Blocking list — both must land before the `feature/0.5.0` push and the `develop` PR:**

1. **H-1** — sweep `CLOSURE.md` out of `public/data/DADAIA.md:214` and the two scaffold
   projections, exactly as `ACTIVE.md` was swept; re-stage, re-install, `public doctor`.
2. **H-2** — make `test_v30_pyramid_shape_reported_from_collect_only` deterministic
   (drop the wall-clock timeout or move the measurement in-process), so `dadaia ci preflight`
   is reliably green before the push.

**Recommended in this release (not blocking):** M-1's docstring correction and predicate
extraction, M-2's deletion-or-wiring, M-4 and M-5's single-home collapse. Each is a
*deletion*, each shrinks the feature it touches, and each closes a duplication this release
created — which is the direction the standing order asks for.

**Route to closure / intake, not to code:** L-3's FR15 accounting divergence and L-4's
A22.9 overshoot both need the operator's explicit numbered disposition in the closure
record; M-6's redaction asymmetry needs to become a written decision; the 483 SPEC-DOC-033
warnings and the FR-attribution gap for bug-fix regression tests are intake candidates.

**Re-review scope on rework:** H-1 and H-2 only, plus a re-run of `dadaia ci preflight`
twice (a single green run does not disprove a contention flake).

---

*Evidence artifacts:* `.dadaia/tmp/software-engineer/20260827/T-050-34-invariants.md`;
`specs/releases/0.5.0/reviews/` (`S1`–`S4` QA closes + `S2` re-verdict, `S1-FR23-firing.md`,
`S1-AR1-ruling.md`, `FR23-firings.md`, the five coverage tables);
`specs/audits/20260827-canon-v6-first-audit/`. Commit reviewed: `d981855c`
(delta through `343acc38`, §0).
