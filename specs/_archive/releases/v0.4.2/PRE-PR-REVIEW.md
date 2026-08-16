# PRE-PR-REVIEW — Release v0.4.2 — residual-convergence (T-042-18)

> **Renamed from `CODE-REVIEW.md`** (CR-4, LOW): T-042-18 declares its artifact as
> `PRE-PR-REVIEW.md` (`TASKS.md:500,505`); this file is that same review, renamed to
> the TASKS-declared canonical name by the CR-0/CR-1/CR-2/CR-3 remediation pass
> (`software-engineer` lane) — content below is unchanged from the original review.

**Reviewer:** code-reviewer
**Task:** T-042-18 — six-axis pre-PR review of the delta, run **before** the archive move
(FR5 / ADR R3 — this release is the canon's first executor)
**Reviewed range:** `741f2294..c8847288` (`feature/0.4.2`; `c8847288` is the commit
`qa-engineer` approved at T-042-17)
**Reviewed on:** 2026-08-16
**Verdict (round 1, 2026-08-16):** REQUEST-CHANGES — 2 HIGH, 2 MEDIUM, 2 LOW actionable; 9 record-only
**Verdict (round 2 — FINAL, after remediation): APPROVE** — see [Re-review](#re-review-round-2--remediation-verification) at the end of this document

> Per FR5/R3 this review lands on a **thawed** tree: every finding below is remediable in
> place and re-reviewable without reopening any archived artifact. That is the whole point
> of the ordering this release makes canon, and it is working as designed on its first run.

---

## Target

| | |
|---|---|
| Base | `741f2294` (milestone (a) merge of the definition into `develop`) |
| Target | `c8847288` (`docs(T-042-17): re-verify QA-1/QA-2 remediation, flip alpha-1 to APPROVED`) |
| Branch | `feature/0.4.2` (local-only, per `dadaia-gitflow`) |
| Files changed | 53 |
| Commits in range | 34 (17 `chore(tasks): start …` reservation flips + work commits) |

### LOC delta (R5 — "measured as much by what it deletes")

| Surface | Added | Deleted | Net |
|---|---:|---:|---:|
| Production Python (`dadaia_workspace/`, excl. `public/`) | 669 | 500 | **+169** |
| Public assets (`dadaia_workspace/public/`) | 118 | 181 | **−63** |
| Tests | 1182 | 316 | +866 |
| Specs / CHANGELOG | 485 | 18 | +467 |
| **Total** | **2454** | **1015** | **+1439** |

Production is **net +169, not net-negative**. The deletions R5 promised are all real and
land in three files — `new_artifacts.py` −136, `scaffolder.py` −132, `cli/commands/specs.py`
−112 (**−380 combined**) — but they are outweighed by `document.py` +240 (the FR1 move's
landing site, of which ~136 is relocated rather than new), `git_objects.py` +96 (FR7+FR8),
and `doctor_governance.py` +65 (FR14). Netting the FR1 relocation out, genuinely *new*
production logic is roughly +305 against −380 deleted. This is not a finding — SPEC §2's
deletion list is delivered item by item — but the closure should state the measured number
rather than claim a net-negative release.

## CI status

All gates green at the reviewed commit, run by this review:

| Check | Result |
|---|---|
| `dadaia ci preflight` (`ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`, `pytest`) | **5/5 PASS** |
| `dadaia specs doctor` | `[ok] overall: 0 error(s), 5 warning(s)` — all 5 pre-existing (2× SPEC-DOC-027 legacy dir names, 2× SPEC-DOC-036 archived audits, 1× heading allowlist); **SPEC-DOC-031 count = 0** (A14.4 holds) |
| `dadaia backlog doctor` | `clean` |
| `dadaia public doctor` | green incl. `[ok] public-privacy`, `[ok] entities-derivation`, `[ok] model-resolution` |
| `setup.cfg` | **unchanged** in range — A1.6's no-new-import-edge claim verified by diff |
| `core/redaction.py`, `cli/redact.py` | **zero-diff** in range — A4.3 verified by diff |
| `specs/_archive/**` | **untouched** in range — A15.1 verified by diff |

---

## Findings

### CR-0 — `HIGH` — Axis 6 (dead/blocked surface) / Axis 4: the artifact this new canon requires is **gitignored** — the review-before-archive law is silently defeated at its first execution

**Location:** `.gitignore:155` (`/specs/releases/*/*`) and the whitelist block at
`.gitignore:159-166`

FR5 / ADR R3 makes it canon that the pre-PR six-axis review "runs **before** the `git mv`
archive step" and rides the branch, and T-042-18 declares its artifact as a tracked write
set. The repository's own `.gitignore` denies it:

```
$ git check-ignore -v specs/releases/v0.4.2/CODE-REVIEW.md
.gitignore:155:/specs/releases/*/*    specs/releases/v0.4.2/CODE-REVIEW.md

$ git check-ignore -v specs/releases/v0.4.2/PRE-PR-REVIEW.md
.gitignore:155:/specs/releases/*/*    specs/releases/v0.4.2/PRE-PR-REVIEW.md
```

Both candidate names are denied — the one this review was dispatched to write **and** the
one TASKS declares (CR-4). The whitelist that follows the deny rule enumerates
`ALPHA-*-QA.md`, `SPEC.md`, `PLAN.md`, `TASKS.md`, `CLOSURE.md`, `GRILL.md` and
`OQ-DECISIONS.md`; there is no line for the code-review artifact. Committing it requires
`git add -f`, which this review had to use.

This is a **recurrence of an already-registered class**. The comment sitting directly above
the `ALPHA-*-QA.md` whitelist line records the previous instance verbatim:

> `# Bug gitignore-alpha-qa-review-untrackable: each alpha-N closes with a`
> `# qa-engineer review committed to the branch (DADAIA.md §5) — the whitelist`
> `# must include it or the law is silently defeated (v0.5.0's ALPHA-1-QA.md`
> `# needed git add -f).`

That fix added exactly one artifact class and left the deny-by-default rule to catch the
next one. FR5 then introduced a new law-mandated artifact class without extending the
whitelist, so the same defect reappeared on the very first release that ships the canon —
precisely the "a fact with more than one writer" / "the next round finds it again" pattern
SPEC §1 exists to break.

Registered as bug `gitignore-code-review-artifact-untrackable` (HIGH,
`specs/bugs/bugs.jsonl`).

**Fix direction:** `software-engineer` lane — add the whitelist line for the code-review
artifact next to `!/specs/releases/*/ALPHA-*-QA.md`, using whichever filename CR-4 settles
on, and the matching `!/specs/releases/*/alpha-*/…` line if the artifact can appear inside a
segment directory. Then verify with `git check-ignore -v` returning non-zero and a plain
`git add` succeeding. Worth considering the structural form instead of a seventh literal:
the deny rule `/specs/releases/*/*` combined with an enumerated allowlist will keep
manufacturing this bug every time the SDD lifecycle gains an artifact — the same
literal-by-literal treadmill entry #24 already names for the privacy baseline carve-outs.

---

### CR-1 — `HIGH` — Axis 2 (patterns) / Axis 4 (correctness): the FR8 row-shape narrowing refuses legitimate pushes for paths containing two or more spaces

**Location:** `dadaia_workspace/infrastructure/git_objects.py:270-277` (`_resolve_prior_texts`)

`git cat-file --batch-check` answers a *missing* lookup by echoing **the whole input**
followed by ` missing` — i.e. `<base>:<path> missing`. The new code classifies that row by
**field count** on a whitespace split:

```python
if len(parts) == 2 and parts[1] == "missing":
    continue  # the documented "<base>:<path> missing" row -> absence, not an error.
if len(parts) != 3:
    raise GitObjectReadError(
        "git cat-file --batch-check: unexpected row shape resolving prior content",
        path=path,
    )
```

A path with **no** spaces yields 2 fields (absence — correct). A path with **one** space
yields 3 fields and slips through the `!= 3` guard into the blob-type branch, where
`obj_type` is a path fragment, fails the `!= "blob"` test, and is treated as absence
(correct by accident). A path with **two or more** spaces yields ≥4 fields and **raises**.

`features/chokepoints/service.py:_run_denylist_scan` catches `GitObjectReadError` and
returns `allowed=False`, so the outcome is a **blocked push** carrying a diagnostic that
says the opposite of what happened — the docstring calls this shape "git answering
something git only ever answers on internal inconsistency", when in fact the repository is
healthy and the operator merely added a new file whose name contains two spaces.

**This is a regression introduced by this release.** At `741f2294` the same line read
`continue  # "<base>:<path> missing" (or any non-3-field line) -> absence` and the push
proceeded.

**Reproduced** against the real code path (throwaway repo, base commit + one commit adding
`docs/my other file.md`, calling `GitSubprocessObjectReader.new_objects`):

```
RAISED: GitObjectReadError -> git cat-file --batch-check: unexpected row shape
        resolving prior content | path attr: docs/my other file.md
```

and directly against git:

```
$ printf 'HEAD:my other file.md\n' | git cat-file --batch-check
HEAD:my other file.md missing
```

Likelihood is not theoretical: FR10 in this same release declares macOS and Windows as
supported platforms, and both routinely produce filenames with several spaces (screenshot
captures being the canonical case). The operator's only escape is `--no-verify`, which
`DADAIA.md` §6 forbids.

**Fix direction:** classify the missing row by **suffix**, not by field count — the row is
`<echoed input> missing`, so `line.endswith(" missing")` (or an `rsplit(None, 1)` on the
trailing token) identifies it for any path. Keep the ≥4-field raise only for rows that do
**not** end in ` missing`. A RED test on a new path with two spaces belongs with the
existing A8.4 cases in `tests/unit/infrastructure/test_git_object_reader.py`. Verify the
same reasoning against `_blob_info` (`git_objects.py:195-208`) — that call feeds shas, not
paths, so it is not affected, but the fix should say so.

---

### CR-2 — `MEDIUM` — Axis 4 (security/evidence fidelity): the new `windows-users-path` baseline pattern does not fire in prose, and its fixture cannot see the gap

**Location:** `dadaia_workspace/infrastructure/data/privacy_baseline.json:55-59`;
fixture `tests/fixtures/privacy_baseline/windows_home_path.txt:3`

The three home-path patterns do not have the parity FR10 claims for them:

| id | trailing lookahead |
|---|---|
| `home-abs-path` | `(?=/\|\b)` |
| `users-abs-path` | `(?=/\|\b)` |
| `windows-users-path` | `(?=\\\|$)` |

The Windows pattern fires **only** when the path is followed by a backslash or ends the
line. Measured against the shipped baseline (placeholder names used here, which the
carve-outs exclude by design):

```
HIT   home-abs-path        '/home/username and more prose'
HIT   users-abs-path       '/Users/username and more prose'
MISS  windows-users-path   'C:\Users\username and more prose'
MISS  windows-users-path   'see C:\Users\username, then'
HIT   windows-users-path   'C:\Users\username\Documents'
```

The most common way an operator-local Windows path leaks into a document — inline in a
sentence — is exactly the form that does not fire. A10.1 passes anyway because the fixture
writes `…\Users\zz-fixture-user\Documents`, whose trailing `\Documents` satisfies the
lookahead; the fixture was chosen on the one form that works.

**Fix direction:** widen the lookahead to include a word boundary and end-of-line
(`(?=\\|\b|$)`), or replace it with a negative lookahead over the name charset, then add a
second fixture line carrying the **prose** form so the gap is provable. Re-run
`dadaia public doctor` (`[ok] public-privacy`) and the self-scan sentinel; note that any
new fixture row must be declared in `_TESTS_SCOPE_BASELINE` per D9, as T-042-11 did for the
two rows it added.

---

### CR-3 — `MEDIUM` — Axis 1 (architecture) / Axis 2: FR7's multi-path amnesty is scoped to the tip tree, while SPEC FR7/A7.1 specify the pushed range

**Location:** `dadaia_workspace/infrastructure/git_objects.py:130-160` (`_multi_path_shas`),
called from `GitSubprocessObjectReader.new_objects:582`

The adapter-only implementation is exactly right in shape — D4/R1 honoured, the matcher and
its amnesty predicate are untouched (verified: `denylist_scan.py`'s diff in this range is
FR4's matcher export only, no amnesty edit), the decision is made in one place, and the
tree-order-independence fixture is real. The **scope** is narrower than specified:

```python
result = _run(["git", "ls-tree", "-r", "--full-tree", local_sha, "--"], repo)
```

`git ls-tree -r <local_sha>` enumerates the entries of the **tip tree only**. SPEC FR7 and
A7.1 both say "reachable at **more than one path in the range**". `_rev_list_candidates`
walks the whole range, so `blob_info` legitimately contains blobs that exist at two paths in
an intermediate commit but at one path (or none) at the tip — those are still published by
the push, yet `_multi_path_shas` cannot see their second path and the amnesty is **not**
withheld. The docstring is honest ("within *local_sha*'s tree"), so this is a
specification-versus-implementation divergence rather than a hidden one.

Note this is materially load-bearing for the closure: SPEC §5 requires T-042-19 to record
"the **multi-path amnesty** semantics (FR7)" in `sdd-gate-v3.md` so that atom's "a new path
still refuses" sentence becomes true again. Writing "reachable at more than one path in the
range" into memory would make the atom assert something the code does not do.

**Fix direction:** decide and record, do not leave it implicit. Either (a) widen the
enumeration to the range (each commit's tree, or `git ls-tree` over the range's trees) if
the cost is acceptable, or (b) keep the tip-tree scope as the deliberate, cheaper form and
state it verbatim in the closure and in the `sdd-gate-v3` atom T-042-19 writes — "reachable
at more than one path **in the pushed tip's tree**". Option (b) is consistent with R5 and
costs one sentence; it just must not be silent.

---

### CR-4 — `LOW` — Axis 4 (evidence fidelity): this review's artifact filename does not match the one TASKS declares

**Location:** `specs/releases/v0.4.2/TASKS.md:500` and `:505` (T-042-18 header and write set)

T-042-18 declares its artifact as `specs/releases/v0.4.2/PRE-PR-REVIEW.md`, in both the
commit line and the write set. This review was dispatched to write
`specs/releases/v0.4.2/CODE-REVIEW.md`, and does so. The evidence map row (`TASKS.md:79`)
points at "`code-reviewer` APPROVED artifact on a **thawed** tree" without a filename, so
nothing else depends on the name — but the closure's evidence pointer will resolve to a
file that TASKS does not name.

**Fix direction:** reconcile in one direction before closure — either rename this artifact
to `PRE-PR-REVIEW.md`, or amend T-042-18's two references to `CODE-REVIEW.md`. Either is a
one-line edit on the thawed tree.

---

### CR-5 — `LOW` — Axis 4 (evidence fidelity): BACKLOG.md #24's partial-pick note was never revised after the definition-push LOW, and cites a path that does not yet exist

**Location:** `specs/backlog/BACKLOG.md`, entry `baseline-carve-out-review-cadence` (#24),
Description field

The definition-push security review raised a LOW that this entry asserts FR10 as already
delivered in the past tense. `specs/backlog/BACKLOG.md` has **not been touched since
`01a938dd`** (the definition commit) — `git log 741f2294..HEAD -- specs/backlog/BACKLOG.md`
is empty — so the wording was not revised. It reads:

> "**partially picked by release v0.4.2** (`specs/_archive/releases/v0.4.2/SPEC.md` FR10
> delivered the cross-platform half: …)"

Two halves, different status now. The **tense** has become true — FR10 did ship at
T-042-11, so at the reviewed commit the past tense is accurate. The **path** is still
forward-looking: `specs/_archive/releases/v0.4.2/SPEC.md` does not exist and will not until
T-042-20 performs the `git mv`.

**Fix direction:** T-042-20 already writes `BACKLOG.md` (13 `DELIVERED — v0.4.2` LEDGER
lines) and performs the archive move in the same task. Add an explicit verification step
there: after the `git mv`, confirm the cited path resolves. If for any reason the move
lands elsewhere, repoint the citation in the same commit. This must not be assumed — it
must be checked, because nothing else in the release re-reads that string.

---

## Record-only observations

*Per FR6/R4 these terminate here and in the reviewer handoff. They are recorded — never
silent, zero observations lost — but they carry no concrete fix surface worth operator
adjudication and must **not** enter a PM intake report.*

| # | Axis | Observation |
|---|---|---|
| RO-1 | 2 | `backlog_new`'s write-then-verify raises **after** `target.write_text` has already mutated the file; there is no rollback. Declined deliberately — SPEC §4 non-goal 1 (D2) rejects `atomic_write_text` because it would add file I/O to `core/` or break `features/` layering. The message opens with "wrote `<name>` but a re-parse …", so the operator is told the file changed. Honest as shipped. |
| RO-2 | 2 | `backlog_new`'s slug-uniqueness check now runs through `load_document`, so an unterminated fence in `BACKLOG.md` (which shadows everything after it) can hide an existing slug from the check. It fails **closed**, not open: the same shadow hides the freshly-written slug, so write-then-verify raises. No action. |
| RO-3 | 1 | `fenced_ranges` and `top_level_heading_starts` were promoted into `__all__`, but both consumers (`_top_level_sections`, `_append_active_subsection`) live in the same module — verified: zero references outside `features/backlog/document.py`. Public surface widened with no external consumer, a mild tension with R5. Harmless; the docstrings justify the promotion as intent-revealing. |
| RO-4 | 4 | `specs/memory/product/catalog.json` at the reviewed commit is stale relative to the now-computed values: **24 of 26 atoms differ**, worst cases `sdd-gate-v3` 1600→3814 (**138%**) and `context-management` 470→1021 (**117%**). This is the declared FR2 intermediate state (A2.5 green at both phases) and T-042-19 regenerates it — recorded here because it independently substantiates FR2's own premise (the SPEC cited 37% and 42%; the real figures are worse). |
| RO-5 | 1 | `estimate_tokens` is duplicated verbatim in `public/scripts/generate-memory-catalog.py` — a second writer of exactly the Class-1 kind this release exists to remove. Structurally unavoidable (the projected script is importless) and explicitly out of scope: SPEC §4 non-goal 6 leaves it to entry #6 `thin-wrapper-projected-scripts`. Pinned to byte-identical output by `tests/contract/test_memory_catalog_render_contract.py`. |
| RO-6 | 2 | `_dispositions_tokens` (`doctor_governance.py`) tracks `## ` headings without fence-awareness, so a `## Dispositions` heading quoted inside a fenced block of an archived CLOSURE would be read as structure. No archived document has that shape, and SPEC-DOC-031 is WARN by design (R3 accepts false negatives). |
| RO-7 | 6 | `git_objects.py:477` writes `proc.returncode not in (0,)` where `!= 0` would read plainly. Cosmetic. |
| RO-8 | 3 | The `[-]`→`[x]` completion flips for T-042-03…16 were normalized in one commit (`44ec8efb`) rather than inside each task's own commit. The FR5 obligation this release ships concerns the **reservation** flip, and that was honoured individually — all 17 `chore(tasks): start …` commits are present, so the marker trace A5.3 depends on is complete and observable. |
| RO-9 | 3 | Test **size** is declared by directory placement (`unit/`, `integration/`, `contract/`) plus module- and section-level `Intent:` headers rather than a per-test size token. All 32 newly added test functions fall under a module- or section-level `Intent:` declaration; none is undeclared. Consistent with the TASKS standing rule, which specifies the `Intent:` format only. |

---

## Axis-by-axis result

### Axis 1 — Architecture conformance — **PASS with CR-3**

- **FR1's single-seam move is the real thing.** `backlog_new` moved into
  `features/backlog/`, `setup.cfg` is byte-unchanged, `lint-imports` is green, and the
  cross-feature edge that GRILL P2 said could not exist was removed by relocation rather
  than by exception. `new_artifacts.py` is left coherent (`release_new` only, its own
  `_SLUG_RE`/`_today` retained for that verb). This is D1 executed exactly as designed.
- **FR4's zero-diff constraint held by construction**, not by promise: `core/redaction.py`
  and `cli/redact.py` are untouched in the range, and the masker reaches parity by
  consuming `denylist_scan`'s own exported matchers. `service.py` dropped its
  `core.redaction` import entirely.
- **FR3's import direction is fixed**: `_format_yaml_error` → `format_yaml_error`, and
  `git grep 'import _' -- features/backlog/**` returns zero (A3.2).
- **FR2 phase 1 is genuinely generator-computed** — `token_estimate` is dropped from
  `_REQUIRED_FIELDS` in both generators and computed from the body; the schema keeps it in
  `properties` as optional-and-ignored for the transition window, exactly as A2.5 requires.
- CR-3 is the one divergence: FR7's scope is the tip tree where the SPEC says the range.

### Axis 2 — Design patterns — **PASS with CR-1**

- **FR7 is adapter-only, as ruled.** The matcher and its amnesty predicate are untouched;
  the fail-closed decision lives at exactly one line (`prior_text = None if sha in
  multi_path_shas else prior_texts.get(path)`). The `git ls-tree -r` choice is correctly
  justified — `rev-list --objects` reports each object once and cannot answer the question.
- **The bisect fence filter is correct at the boundaries.** `fenced_ranges` pairs each
  opening marker with a *later* closing marker in a single left-to-right scan, and appends
  the unclosed-fence range last, so the ranges are sorted and non-overlapping — the exact
  invariant `bisect_right(starts, offset) - 1` needs. The retained containment test
  `ranges[idx][0] <= offset < ranges[idx][1]` is byte-for-byte the old `any(...)`
  predicate, so the half-open boundary semantics are preserved. No behavioural change.
- **The EPIPE narrowing is exact.** `len(outcome) < _MAX_BLOB_BYTES and returncode != 0`
  leaves the intentional early-close (full cap delivered, git killed) as the only swallowed
  shape, and the docstring states precisely why a full-cap read can never trip it.
- CR-1 is a defect in the third FR8 narrowing, not in the class of the change.

### Axis 3 — Test coverage — **PASS**

- 32 new test functions, all covered by a module- or section-level `Intent:` declaration
  (RO-9). Supersessions recorded: T-042-03's hotfix scaffolder cases are the only deletions,
  named in TASKS with "behaviour removed, not moved".
- **The `test_repo_self_scan` runtime-composed fixture literal is sound.**
  `_archive_fixture_literal()` builds its match by concatenation so the module's own tracked
  source never contains the substring contiguously — which is exactly what keeps FR9 from
  forcing a `_TESTS_SCOPE_BASELINE` row that A9.4 forbids. The docstring explains the
  reasoning, the composed text lands only in an ephemeral `tmp_path` repo, and the three
  FR9 fixtures (authored-into-archive fails, `git mv` stays excluded, missing `HEAD^`
  degrades) drive throwaway repos rather than this repo's HEAD. Self-catch verified.
- `_TESTS_SCOPE_BASELINE` grew by **exactly 2 rows**, both the FR10 fixtures, matching
  D9/A10.3 and documented in place with the reason (one hit per scanned object means a
  literal added to an already-hit-bearing module would be masked).
- The FR8 RED cases (nonexistent oid, tree sha) and the FR7 tree-order-independence fixture
  are present and named.

### Axis 4 — Security smells / evidence fidelity — **CR-2, CR-4, CR-5**

- No hardcoded credentials, no shell interpolation, no raw SQL. Every new subprocess uses a
  fixed argv list with `_run`; `local_sha` retains its shape check before reaching argv.
- **`GitObjectReadError.path` is a genuine structural improvement.** The raise sites compose
  path-free messages and pass the path as a field; `_render_git_read_error` is the single
  render boundary and masks through the same `_PathMasker`. No `repr(exc)` anywhere. A4.2's
  intent is met.
- **Baseline v5 carve-outs are literal-anchored** as the definition-push LOW asked: each new
  `exclude_regex` is a `^`-anchored alternation over named placeholder/system forms
  (`user|username|youruser|<user>|runner|ci|Shared` and `…|Public|Default`), and each is
  documented in `_header.excludes` with its rationale, including the `/root` exclusion
  boundary (D10). `version` reads `5`. Both new patterns are single-line. A10.2/A10.4 hold.
  CR-2 is about one pattern's trailing lookahead, not about the carve-out discipline.
- **TASKS evidence columns check out against git.** Every task row's claimed commit exists
  in the range; T-042-17's REQUEST_CHANGES → APPROVED cycle is traceable through
  `a42c4514` → `978bb850` (PE persona hotfix template names, 3 lines) → `34e71ca7` (Intent
  declarations on four contract tests) → `c8847288`. The three implementer/AI handoffs'
  metrics match the diff: `ai-engineer` claimed 10 files / 6 skills / 5 personas across
  T-042-14+15, and the range shows exactly 6 `public/skills/**` and 5 `public/agents/**`
  modified. QA's re-verify handoff reports 90/90 acceptance ids and 0 failed.
- **`CHANGELOG.md` reconciliation is honest and measured** (A13.1/A13.2): the preamble
  reports the package index reading with its capture timestamp and evidence path, no
  existing `## [x.y.z]` heading is renamed, renumbered or removed anywhere in the diff, and
  the preamble volunteers the pre-existing `[0.1.x]` discrepancies it deliberately does not
  touch. That last paragraph is the right instinct — it records a gap without silently
  widening scope.

### Axis 5 — Performance smells — **PASS**

- **The FR11 budget test is honest.** `_synthetic_backlog_document(565)` builds 565
  subsections each carrying its own fenced example — the precise O(headings × fences) shape
  GRILL P5 measured, not a fence-free document that would short-circuit on
  `if not ranges`. It asserts the fixture size band (120–160 KB), full parse correctness
  (`doc.errors == ()`, 565 items) and only then the 1.0 s budget, so it cannot pass
  trivially. Measured at **0.14 s** for the whole test — ample headroom, not a flake
  generator.
- No doctor-path regression: `dadaia specs doctor` is green and FR14 made
  `_archive_consumption_hits` strictly cheaper — it now reads two targeted regions per
  archived release and `continue`s on the first hit, replacing a full line-by-line
  substring scan of every archived SPEC and CLOSURE.
- `_multi_path_shas` adds exactly one bounded subprocess per push, guarded by an empty-set
  early return. `_outside_fences` rebuilds its `starts` list per call (2–3 calls per
  document) — O(F) against the O(M log F) it saves; not worth changing.

### Axis 6 — Dead code — **PASS on dead code; CR-0 on blocked surface**

- **The hotfix surface is completely gone.** The A12.1 grep for `hotfix_app`, `hotfix_open`,
  `scaffold_hotfix_release`, `_HOTFIX_TASKS_STUB`, `release_hotfix.md.j2`,
  `closure_hotfix.md.j2` and `Hotfixes pendentes` returns **zero hits** under the standing
  exclusions. The golden `doctor_all_four_v0158.json` lost exactly the two
  `stage:templates/*_hotfix.md.j2` rows — regenerated, not hand-edited, and nothing else
  moved in it.
- `candidates.md` survives only in two `features/specs/doctor.py` comments that name it as
  retired — the class A3.1 explicitly permits. Zero hits under `cli/**` (A12.3).
- `_BACKLOG_RETURNS_HEADING_RE` and its branch are gone (A14.5), and the check is shorter in
  logic even where the file grew in documentation.
- **No orphans from the moves.** Every symbol introduced or promoted
  (`compile_slug_patterns`, `operator_terms_match`, `format_yaml_error`, `backlog_new`,
  `BacklogNewResult`, `estimate_tokens`, `RegistryContextIdentities`, `_multi_path_shas`,
  `_render_git_read_error`) has live references. Zero commented-out code blocks added.

---

## Summary

| Severity | Actionable | Record-only |
|---|---:|---:|
| CRITICAL | 0 | 0 |
| HIGH | 2 | 0 |
| MEDIUM | 2 | 0 |
| LOW | 2 | 0 |
| INFO | 0 | 9 |
| **Total** | **6** | **9** |

Fifteen observations recorded, zero lost. Six carry a concrete fix surface and are routed
as findings; nine terminate in this artifact and the reviewer handoff, per FR6/R4.

One finding (CR-0) is additionally registered as a bug — `DADAIA.md` §6 requires
registration of any behavior that breaks the tool's own contract, independently of the
release's routing.

## Recommendation

**REQUEST-CHANGES.**

Two HIGH findings block. **CR-0** is the sharper one in governance terms: the artifact
this very task must produce is denied by the repo's own `.gitignore`, so the
review-before-archive canon FR5 makes law is defeated at its first execution and this
review had to be committed with `git add -f`. It is a recurrence of a class already
registered and already "fixed" once, by adding a single literal.

**CR-1** is a HIGH: the pre-push gate refuses a legitimate push for ordinary content and
explains the refusal as internal git inconsistency. It is a regression introduced inside
this release, it is reproducible on the executed path, and the workaround it forces
(`--no-verify`) is forbidden by `DADAIA.md` §6. CR-2 and CR-3 are MEDIUM and should ride
the same remediation: CR-2 leaves one of the three declared platforms effectively uncovered
in the most common prose form, and CR-3 must be resolved before T-042-19 writes the
multi-path semantics into `sdd-gate-v3.md`, since the atom would otherwise assert a
guarantee the code does not provide. CR-4 and CR-5 are LOW and cost one edit each.

Everything else in this release is strong work. The three root-cause classes are addressed
at the root rather than patched at their instances: FR1 leaves one grammar with one reader
and one writer that verifies itself; FR4 makes masker/detector parity structural instead of
conventional; FR14 replaces substring conversation with consumption assertion and takes the
SPEC-DOC-031 count to zero. The deletions promised by R5 are all real. The marker trace FR5
demanded is complete and observable across all 17 reservation commits.

**Route after remediation:** `software-engineer` fixes CR-0, CR-1 and CR-2 on this thawed
tree,
and the operator or `product-engineer` rules on CR-3's option (a) or (b); CR-4 and CR-5 are
closure mechanics. Then re-run this six-axis review against the remediated commit — no
archived artifact is reopened, which is precisely the property ADR R3 exists to produce.
T-042-18 stays `[-]` until that re-review returns APPROVE.

**Record-only observations RO-1…RO-9 must be carried into `CLOSURE.md`'s
`Record-only observations` section** (A6.3 proves the FR6 calibration by comparing reviewer
handoff finding counts against the closure's two sections; this artifact's counts are
5 actionable / 9 record-only, and the handoff carries all 14).

---

# Re-review (round 2) — remediation verification

**Re-reviewed:** 2026-08-16
**Remediation range:** `934e6cf3..85ac7ab7` — 3 commits, 9 files, +260/−33
**Implementer handoff:** `2026-08-16T184331Z-software-engineer-t-042-18-cr-remediation`
**Final verdict: APPROVE**

Every fix below was verified against **my own round-1 reproductions**, re-run on the
remediated tree — not against the implementer's claims. Two new regression tests carrying
`Intent:` declarations arrived with the fixes (CR-1 and CR-3), which is the right shape:
the repro becomes the guard.

## Per-finding re-verification

### CR-0 — `HIGH` → **FIXED (verified)**

`.gitignore` gains `!/specs/releases/*/PRE-PR-REVIEW.md`, carrying a comment that names the
bug and the class. Re-ran my round-1 repro:

```
$ git check-ignore -v specs/releases/v0.4.2/PRE-PR-REVIEW.md
  -> not ignored (exit 1)
$ git ls-files --error-unmatch specs/releases/v0.4.2/PRE-PR-REVIEW.md
  specs/releases/v0.4.2/PRE-PR-REVIEW.md   # tracked without -f
```

Better than the minimum asked: `tests/contract/test_source_repo_hygiene.py` gained
`specs/releases/v9.9.9/PRE-PR-REVIEW.md` to its visibility set, so the whitelist is now
**guarded by a contract test** rather than by a comment alone. That is the difference
between fixing the instance and fixing the recurrence — the previous instance
(`ALPHA-*-QA.md`) had the comment but no test, which is why the class reappeared.

Bug `gitignore-code-review-artifact-untrackable` carries its `resolved` event;
`dadaia bugs status` reports `[ok] 0 open bug(s)`.

### CR-1 — `HIGH` → **FIXED (verified)**

`git_objects.py:_resolve_prior_texts` now classifies the absence row by **suffix**
(`if line.endswith(" missing"): continue`) **before** any field-count reasoning — exactly
the fix direction round 1 recommended. Re-ran my round-1 repro plus three adversarial cases
I had not run before:

| Case | Result |
|---|---|
| Round-1 repro — new path `docs/my other file.md` (2 spaces) | **no raise**; `prior_text=None` (absence) |
| New path `d/one two three four.md` (4 tokens) | **no raise**; absence |
| New path literally named `d/x missing` | absence — correct, not a desync |
| Existing path `a.md` at base | `{'a.md': 'base\n'}` — prior text still resolves, amnesty path intact |

The last row matters: the fix had to widen absence detection **without** breaking the
amnesty lookup it guards, and it does not. The docstring correctly records that
`_blob_info`'s own field-count classifier is unaffected because that call is fed shas, never
paths — I verified that reasoning holds.

### CR-2 — `MEDIUM` → **FIXED (verified)**

Lookahead widened to `(?=\\|\b|$)`, giving the parity with `home-abs-path` /
`users-abs-path` that FR10 claimed. Re-ran my round-1 measurement matrix, plus the
carve-out cases:

| Input | Round 1 | Round 2 |
|---|---|---|
| `…\Users\<name> and more prose` | **MISS** | **HIT** |
| `see …\Users\<name>, then` | **MISS** | **HIT** |
| `…\Users\<name>\Documents` | HIT | HIT |
| `…\Users\username and prose` (placeholder) | miss | miss (carve-out holds) |
| `…\Users\Public\Desktop` (system dir) | miss | miss (carve-out holds) |

The fixture gained the prose form, so the gap is now provable rather than invisible —
round 1's specific objection was that the fixture only exercised the one shape that worked.
`dadaia public doctor` stays `[ok] public-privacy`.

### CR-3 — `MEDIUM` → **FIXED (verified), per the operator ruling that SPEC wins**

`_multi_path_shas` now takes `base` and unions the `(sha → paths)` mapping across **every
commit in the range** (`_range_commit_shas`), with `local_sha` always included as a floor.
I verified the two range walkers agree on range shape — `_rev_list_candidates` and
`_range_commit_shas` use identical `--not base` / `--not --remotes` forms with the same
`--` end-of-options marker, differing only by `--objects`.

Constructed the precise scenario the tip-tree form could not see: a **new** blob published
at two paths in an intermediate commit, with the second path deleted before the tip, and
the surviving path carrying prior content at base (a live amnesty source):

```
tip tree        p1.md -> a43c10cc                    (single-pathed — what the old code saw)
intermediate    p1.md -> a43c10cc, p2.md -> a43c10cc (multi-pathed — what it missed)

range commits detected: 2
multi-path shas detected: {a43c10cc}
p1.md prior_text = None      -> AMNESTY WITHHELD (fail-closed, correct)
```

Pre-fix this blob would have received `prior_text="old content\n"` and been amnestied. The
new property is commit-order-independence across the range, on top of the tree-order
independence the release already had. The cost note is honest and bounded (one `ls-tree` per
commit, not per object), and it names the chunking escape hatch without pre-building it —
correct under R5.

### CR-4 — `LOW` → **FIXED (verified)**

Renamed to the TASKS-declared `PRE-PR-REVIEW.md`. I diffed the rename with `-M` to confirm
the remediation did **not** alter this review's content: 98% similarity, the only change
being the title line plus an added provenance note stating the content is unchanged. My
findings, severities and verdict text were left intact — the correct handling of another
agent's review artifact.

### CR-5 — `LOW` → **OPEN, deferred to T-042-20. The routing is correct and I accept it.**

Asked to decide whether deferral satisfies me: **it does, and deferring is not merely
tolerable here — it is the only correct sequencing.** BACKLOG.md #24 cites
`specs/_archive/releases/v0.4.2/SPEC.md`. That path becomes valid *by the very act*
T-042-20 performs (`git mv` of the release directory), and T-042-20 already writes
BACKLOG.md in the same commit for the 13 `DELIVERED — v0.4.2` LEDGER lines. "Fixing" it now
by repointing the citation at the live path would make the reference wrong again the moment
the archive move lands.

What I require instead of a code change is that the obligation be **carried, not
remembered**: T-042-20 must, after the `git mv`, confirm the cited path resolves and
repoint it in the same commit if it does not. This is recorded as a named precondition in
the round-2 handoff's `decisions_required` so the closure agent receives it as an explicit
obligation rather than inheriting it from prose. With that carried, CR-5 does not block.

### CR-6 — `LOW` — **NEW, pre-existing, non-blocking**

While re-running CR-2's matrix I found a narrow carve-out escape in the same pattern, which
I record for completeness because it sits on the surface I was re-verifying:

```
'…\Users\username.'       -> FALSE POSITIVE (placeholder should be excluded)
'see …\Users\username.'   -> FALSE POSITIVE
'…\Users\Public.'         -> FALSE POSITIVE
'…\Users\username, ok'    -> clean
```

The Windows name charset `[A-Za-z0-9_.-]+` includes `.`, so a placeholder path ending a
sentence swallows the trailing period into the match; the `^`-anchored `exclude_regex` then
fails, because it expects `$` or `\` immediately after the name. The `/home` and `/Users`
peers do not have this because their charsets exclude `.`.

**Not introduced by the CR-2 remediation** — I confirmed the pre-fix `(?=\\|$)` form
false-positives identically on these inputs, so this dates from T-042-11. It errs toward
**over**-firing on placeholder documentation, so it costs friction, never privacy, and
`dadaia public doctor` is green. **Non-blocking.**

**Routing (FR15.3 / ADR #15):** no new backlog entry is materialized. This belongs to the
residual of entry #24 `baseline-carve-out-review-cadence`, which stays ACTIVE and already
names exactly this class — "carve-outs are literal-by-literal" and "a doctor check flagging
baseline patterns lacking a documented carve-out rationale". Recorded here and in the
handoff for the closure to fold into that entry's existing residual text.

## Gates at the remediated tip (`85ac7ab7`)

| Check | Result |
|---|---|
| `dadaia ci preflight` | **5/5 PASS** (`ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`, `pytest`) |
| `dadaia specs doctor` | `0 error(s), 5 warning(s)` — same 5 pre-existing as round 1; SPEC-DOC-031 still 0 |
| `dadaia backlog doctor` | `clean` |
| `dadaia public doctor` | green incl. `[ok] public-privacy`, `[ok] entities-derivation`, `[ok] model-resolution` |
| `dadaia bugs status` | `[ok] 0 open bug(s)` |

Release-wide invariants re-checked across the **full** range `741f2294..85ac7ab7`, not just
the remediation delta — remediation is exactly where a zero-diff constraint gets broken by
accident:

- `setup.cfg` — zero-diff (A1.6 holds; no new import edge)
- `core/redaction.py`, `cli/redact.py` — zero-diff (A4.3 holds)
- `specs/_archive/**` — untouched (A15.1 holds)
- `features/chokepoints/**` — untouched by the remediation, so FR7's "matcher and amnesty
  predicate not edited" (A7.3) survives the CR-3 widening; the fix stayed entirely in the
  adapter, exactly as D4/R1 require

## Final recommendation

**APPROVE.**

Both HIGH findings are fixed at the root and guarded by tests, both MEDIUMs are fixed and
verified against the original reproductions, and the two LOWs are resolved or correctly
sequenced. Nothing regressed: every zero-diff and untouched-surface invariant the release
depends on still holds after the remediation, and all five gates are green.

The remediation also did the thing this release exists to do. CR-0 was not closed by adding
one more literal to an allowlist — it added the contract test that makes the *class* visible
next time, which is precisely the "a fact with more than one writer / the next round finds
it again" pattern SPEC §1 names. CR-1 and CR-3 each shipped the reproduction as a permanent
regression test. That is root-cause work, not symptom patching.

T-042-18 is complete: **APPROVED on `85ac7ab7`**, the commit the remediation produced, with
`qa-engineer`'s alpha-1 APPROVAL standing on the implementation it re-verified.

**Carried forward to T-042-20 (closure), non-blocking:**

1. **CR-5** — after the `git mv`, confirm BACKLOG.md #24's cited archive path resolves;
   repoint in the same commit if not.
2. **CR-6** — fold into entry #24's existing ACTIVE residual. No new entry.
3. **RO-1…RO-9** — carry into `CLOSURE.md`'s **Record-only observations** section. A6.3's
   count reconciliation for this reviewer: **16 observations total — 6 actionable
   (CR-0…CR-5) + 1 new non-blocking actionable (CR-6) + 9 record-only**, of which 5 are
   closed by remediation and 2 (CR-5, CR-6) route forward. Zero observations lost.
