# S5 — FR23 net-positive-diff firing ledger

One section per firing of the FR23 evidence gate in segment S5. Reviewer for all
sections: software-architect.

---

## Firing 1 — T-044-33 (commit `f3b95a4d`): backlog duplicate-section enforcement

**Date:** 2026-08-24 · **Trigger:** FR23 evidence gate (`evidence_diff` net-positive,
`bugs.jsonl` `resolved` event for
`backlog-doctor-silent-on-duplicate-top-level-sections`)

### Verdict: SOUND — the growth is the missing enforcement, at the owning seam

The diff (+52/-20, `dadaia_workspace/features/backlog/document.py` only) replaces a
silent-drop path (`dict.setdefault`, first-wins) with enforcement of an invariant the
module docstring already claimed ("exactly two top-level sections") and never checked.
Net-positive in lines, **net-negative in behaviors**: one silent-truncation path is
eliminated; no flag, no second code path, no special case is bolted onto working code.
The new `DocumentError` conforms to the parser's established non-throwing diagnostic
model — no new error-handling shape was introduced. Root-cause gate: **PASS** (cause =
first-wins `setdefault`; fixed where it lived). Architecture-fidelity gate: **PASS**
(parser owns grammar/schema, doctor owns semantic checks; boundary intact).

### Check (a) — one representation, not two shapes

`_top_level_sections` (document.py:253) now returns exactly one shape:
`dict[str, list[tuple[int, int]]]` — occurrence lists for every heading name, uniformly.
The old single-value shape is gone; no dual representation coexists. The function stays
private with a single consumer. (`top_level_heading_starts`, document.py:298, keeps its
first-wins `dict[str, int]` — that is a different contract, the writer's insertion-point
primitive, not a second section model; first-LEDGER insertion remains correct even for a
corrupt document the doctor now flags. Non-blocking observation, no action required.)

### Check (b) — consumer adaptation, not duplication

Grep over the package finds exactly one consumer: `load_document` (document.py:485). Its
adaptation is two `for start, end in sections.get(...)` loops that call the **same**
pre-existing `_parse_active` / `_parse_ledger` per occurrence and extend one result list.
No parsing logic was duplicated; no second reading path exists (the writer,
`backlog_new`, checks membership by calling `load_document` itself, unchanged).

### Check (c) — doctor.py remains single-owner of slug-duplicate detection

`doctor.py` is untouched. BL-DUP's `_check_duplicate_slugs` (doctor.py:247) remains the
only slug-duplicate detector in the package. The parser's new error is about a repeated
**section heading** (document schema, the parser's own contract), a distinct concern; the
fix works by finally delivering both occurrences' items to the doctor's already-correct
check instead of duplicating that check into the parser. Correct division of ownership,
and the implementer proved BL-DUP was already-correct by instrumentation before writing
code (`resolved` event, `evidence_diff` field).

### Bug-surface delta

**REDUCED.** Evidence: the `reported` event (bugs.jsonl, this slug) documents live
corruption passing `backlog doctor` clean — ~150 duplicated lines caught only by eye. The
fix closes that silent-acceptance surface at the single parsing seam both reader and
writer share; RED-to-GREEN seams
(`test_document.py::test_duplicate_top_level_active_heading_yields_document_error_and_parses_both_bodies`
+ LEDGER sibling + `test_backlog_doctor.py` integration) pin it. Prior fix chain on this
file (v0.4.2 fence-awareness M1, unclosed-fence diagnostic) shows no repetition of this
symptom and this fix follows the same structural pattern — capture as located
diagnostic, never drop, never throw. No puxadinho detected; full suite 2756 passed.

---

## Firing 2 — T-044-35 (commit `5af53a7c`): atomic-writer behavioural battery

**Date:** 2026-08-24 · **Trigger:** FR23 evidence gate (`evidence_diff` net-positive
+279/-15, `bugs.jsonl` `resolved` event for
`atomic-writer-drift-guard-is-brittle-and-covers-only-two-of-eight-writers`)

### Verdict: SOUND — test-coverage growth governed by stewardship, defect deletion at its root

The diff touches exactly one file,
`tests/unit/features/specs/test_migration_symlink_hardening.py`, and zero production
code. The −15 is a true deletion of the defect itself: the text-slicing comparator
(`inspect.getsource` + triple-quote split + stripped-line equality) whose four failure
modes the bug's repro names — false-fail on a reworded comment, silent degeneration on
an embedded triple-quoted literal, `IndexError` on a missing docstring, and a 2-of-8
coverage ceiling that passes when both copies are identically wrong. The replacement
does not repair the mechanism; it removes the mechanism class (source-text equality)
and pins the actual contract (behaviour) instead. Root-cause gate: **PASS** — the
`evidence_loop` replays the OLD algorithm against a comment-only reword and reproduces
the false failure before a line of the battery was written; the cause (text as proxy
for behaviour) is eliminated, not patched. Architecture-fidelity gate: **PASS** — every
one of the 8 cases calls the writer's real entry point in its owning module; the test
asserts observable filesystem behaviour (inode rebind, bytes on disk, mode, temp-file
survival), never internal structure; enumeration is closed against the package
(`grep ^def _*atomic` — exactly 8, matching the bug's count).

### Check (a) — is coverage-expansion growth in a TEST file the legitimate exception to prefer-deletion?

**YES, and this diff earns it.** The standing order's prefer-deletion doctrine targets
production **feature** growth — the puxadinho vocabulary (branch, flag, second code
path, cross-feature reach-in, new side effect) describes behavior added to a shipped
feature. A test diff adds zero production behaviors; its governing law is
`dadaia-test-stewardship`, whose bar is: declared intent and size at birth, and every
line earning its keep. The battery clears that bar on all counts:

- **Declared at birth:** module docstring carries `Intent: REGRESSION` (CWE-59/61/73/
  703/674 + the bug slug + T-044-35) and `Size: SMALL` — correct tier: all 32 items are
  `tmp_path`-scoped unit tests with no I/O beyond a temp dir.
- **Lines earned, not sprawled:** 4 behavioural dimensions × 8 writers = 32 items from
  **one** frozen dataclass table (`_ATOMIC_WRITER_CASES`) and 4 parametrized test
  functions — not 32 copy-pasted bodies. The per-case contract fields
  (`preserves_mode`, `cleans_up_on_failure`, `lf_bytes_guaranteed`) were empirically
  verified before being pinned (`resolved` event, `evidence_diff`), so the table is a
  measured contract, not an aspiration. This is exactly the shape the bug's `expected`
  field demanded.
- **Deletion inside the growth:** the brittle guard is gone, and with behaviour pinned
  directly at 8 seams, the bug's suggested AST-equality companion became redundant and
  was correctly **not** built — behavioural equivalence supersedes source equivalence.
  The diff is smaller than the bug's own remedy sketch.
- **Discipline held:** the write set stayed tests-only even when the battery found a
  production defect (see (b)) — the fix was routed to a bug, not smuggled into the task.

One standing caution so this exception never becomes a loophole: the exception is for
**coverage of existing contracts**. A test diff that added fixtures, helpers-of-helpers,
or scenario permutations without a named contract per line would still be slop under
stewardship. This one names its contract per dimension, per writer.

### Check (b) — does pinning a KNOWN-BAD behaviour green follow test-stewardship or hide a defect?

**FOLLOWS the law — this is characterization done correctly, and it is anti-hiding by
construction.** The chain of custody is complete:

1. The gap was **registered first**: bug
   `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` (`reported`
   2026-08-24T04:34:58Z, bugs.jsonl) names both leaking writers
   (`hooks/_common.py:atomic_write_text`,
   `infrastructure/public_assets_common.py:_atomic_write_text`), the repro, and the
   expected remedy.
2. The test pins the leak as **CURRENT** behaviour with the bug slug cited inline
   (twice: dataclass field comment and assertion message) — it never asserts the leak
   is *correct*.
3. The pin is **self-destructing in the right direction**:
   `test_atomic_writer_temp_file_on_injected_replace_failure` asserts `leftover` is
   non-empty for the two known-bad writers, with the message "if this now passes, the
   bug is fixed — flip cleans_up_on_failure=True and close it with this test as the
   regression evidence." A silent production fix therefore turns the suite RED and
   forces bug closure with evidence; a regression in any of the 6 clean writers also
   turns it RED. Both failure directions are loud. Compare the hiding alternatives —
   `pytest.skip`/`xfail` on the two cases (fix lands unnoticed, bug rots open) or an
   exclusion list (gap becomes invisible) — this construction dominates both.
4. Fixing the leak is production code, explicitly **out of T-044-35's tests-only write
   set** (`reported` event notes) — correct scope discipline, matching Firing 1's
   pattern of proving the adjacent component's state rather than quietly changing it.

Non-blocking ledger nit: the bug's `notes` field cites the pin as
`test_no_leftover_temp_file_on_injected_replace_failure`, but the committed name is
`test_atomic_writer_temp_file_on_injected_replace_failure`. Correct the reference in the
bug's next event (e.g., the `resolved` evidence) — no code action.

The Windows `skip`s are lawful, not evasions: the mode-dimension skip states a property
of the platform (no POSIX mode bits — non-preservation is unobservable there), and the
CRLF skip is scoped to the 3 writers whose divergence is documented as internal-state,
with companion bug T-044-36 cited. Each skip carries its reason in the message; none
gates a registered defect.

### Check (c) — the 8-writer landscape: consolidation as intake candidate

**Named, not executed.** The battery's own contract table is the indictment: 8
near-identical mkstemp/uuid-tmp + `os.replace` primitives across 7 modules
(`features/migrate/frontmatter_keys`, `features/specs/doctor_structural`,
`hooks/_common`, `infrastructure/public_assets_common`,
`features/spec_context/session_identity`, `features/spec_context/presence`,
`infrastructure/json_agent_model_policy_store` ×2) that have **already drifted** on
every measured axis — mode preservation 2/8, failure cleanup 6/8, LF-bytes guarantee
5/8. That drift is not hypothetical: it produced one registered production bug (the
temp-file leak) and one test-quality bug (the brittle guard existed only because the
duplication demanded a guard). Duplication that requires a drift guard is duplication
that should not exist; the correct endgame is one writer and **no guard at all**.

Proposed backlog entry, for PM intake (operator decides — severity HIGH on the
duplication-surface axis, effort MEDIUM):

> **atomic-write-primitive-consolidation** — Collapse the package's 8 atomic-writer
> primitives (7 modules) into one shared primitive with an explicit, parameterized
> contract: preserve-mode on/off, LF-bytes/binary always, temp-file cleanup on any
> failure always. Delete the 7 local copies; shrink the T-044-35 battery from 8 seams
> to the 1 that remains (net test deletion). Structurally closes bug
> `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` instead of
> patching two call sites. Constraints the release SPEC must adjudicate, both from bug
> history: (1) the features-no-cross-feature import contract and the core/ A9 I/O
> ratchet rule out `features/` and `core/` as the home — `infrastructure/` (which
> already hosts 2 of the 8) is the natural candidate; (2) the hooks-never-import-
> container latency law (v0.5.0) may require `hooks/_common` to keep an import-light
> copy — if so, that single sanctioned duplicate keeps a two-seam battery, and the SPEC
> must say so explicitly rather than let the exception regrow silently.

Per §6 (Backlog) this is a residual for the PM's intake report — this ruling
materializes no backlog entry.

### Bug-surface delta

**REDUCED.** Evidence chain: `reported` (2026-08-19, security-reviewer) documents a
guard that could not catch real drift and covered 2/8 writers; `resolved` (2026-08-24)
replaces it with 32 behaviour-pinning items over all 8. The battery's first run
**surfaced a live production defect** that four years of the text guard never could —
and routed it to the ledger instead of asserting it away. False confidence (a green
guard pinning nothing) is itself bug surface; it is gone. Fix-chain audit for this
surface: the guard was authored during the 0.4.3 mint, registered as defective the same
day by review, and now deleted at root — one generation, no repetition, no stacked
patch. No puxadinho detected: the production tree is untouched, and the one growth
artifact (the case table) carries its own retirement path via the consolidation
candidate above.

---

## Firing 3 — T-044-38 (commit `7d9e8382`, correction `d3346382`): frozen-clock aging ratchet

**Date:** 2026-08-24 · **Trigger:** FR23 evidence gate (`evidence_diff` net-positive
+294/-0, new file `tests/contract/test_frozen_clock_aging_ratchet.py`, `bugs.jsonl`
`resolved` event for
`no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock`)

### Verdict: SOUND — mechanism growth, a THIRD exception category, earned on four conditions

The diff is pure addition and zero production code: one contract test whose AST scan
fails any `tests/**` file that declares a module-level frozen datetime constant AND
calls the real clock (`time.time()` / `datetime.now()`), plus two in-memory mutation
fixtures proving the detector bites on both incident shapes and two negative controls
proving the AND-not-OR precision. Root-cause gate: **PASS** — the underlying defect was
already root-cause-fixed in v0.4.3 (`tmp-gc-tests-age-files-by-the-real-clock-against-
a-frozen-now`: every `os.utime` mtime now derives from the same frozen `_NOW` the
service is given); THIS bug's registered contract is explicitly the guard, not a fix
("Guard, not a fix … Recorded so the next date boundary does not have to teach this
twice" — `reported` event, 2026-08-19, security-reviewer), and the deliverable matches
the `expected` field verbatim. Architecture-fidelity gate: **PASS** — the ratchet lives
in `tests/contract/` beside the repo's established ratchet population; its scope is
`tests/**` only (production clock injection is a different contract, correctly out of
scope, and the retention-fixture boundary is reasoned explicitly in the docstring); the
AST-over-regex choice is structural, not stylistic, and was proven load-bearing before
commit (`evidence_seam`: the naive regex used during the site audit false-hit the tmp_gc
fix's own explanatory comment — a raw-text scan would refuse the very comment that
documents the fix, and refuse its own module docstring).

### Check (a) — same test-growth exception as Firing 2, or different?

**Different — and the ledger should name the difference so neither exception stretches
to cover the other.** Firing 2's exception was *coverage growth*: more test items
pinning contracts that production code already carries. This diff is *mechanism
growth*: the test IS a new enforcement mechanism — a lint in test clothing — guarding a
defect **class** across the whole `tests/**` tree, with its own detector logic (~90
lines of scanner: `_frozen_constants`, `_is_real_clock_call`, name-marker heuristics).
Pure addition is intrinsic to the category: a ratchet has nothing to delete, because
the defect it guards against was already deleted at its root one release earlier; its
`-0` is honest, not evasive. Under the prefer-deletion standing order an all-adding
diff must justify itself explicitly; this one does, on four conditions that together
define when mechanism growth is earned:

1. **The guarded class caused a real incident** — four tests red at a UTC midnight
   boundary with zero code change in between (the v0.4.3 time bomb), not a
   hypothetical.
2. **The class is behaviorally undetectable at test time** — the drift only crosses the
   assertion threshold at a future wall-clock instant, so Firing 2's own rule
   ("behavioural equivalence supersedes source equivalence") cannot apply: no
   behavioural test running today observes a failure scheduled for next month. A
   source scan is the *only* seam that catches the shape at authoring time. This is
   the inverse of Firing 2, where a source-text guard was deleted precisely because
   behaviour WAS observable — the two rulings compose into one doctrine: *pin
   behaviour when behaviour is observable; scan source only when it is not*.
3. **Precision is pinned by the test itself** — two mutation fixtures (both incident
   shapes, `time.time()` and `dt.datetime.now()`) prove RED; two negative controls
   prove a frozen constant alone and a real-clock call alone each stay green, so the
   false-positive direction (`_TIMEOUT_S = 60` beside an unrelated deadline poll) is
   structurally excluded, not hoped for.
4. **The recall boundary is documented, and every known site was hand-verified against
   it** — all 10 `os.utime` aging sites at HEAD enumerated in the docstring with the
   reason each stays green (`evidence_loop` cross-check).

**Is the scanner itself now a maintenance surface? Yes — bounded, and the bound should
be stated.** Precision drift is pinned (condition 3). Recall drift is the live residue:
the rule sees only module-level constants (a function-local frozen constant aging
fixtures by the real clock evades it), and `_trailing_name` misses an aliased import of
the class itself (`from datetime import datetime as d; d.now()` — trailing name `d`).
Both gaps are acceptable *today* because the docstring scopes the rule to this
codebase's actual conventions ("this codebase exposes no other `.time()` zero-arg call
convention") — a ratchet with a declared boundary beats no ratchet, and widening recall
speculatively would trade toward the false-positive failure mode the negative controls
exist to forbid. The maintenance contract this ruling sets: when a future frozen-clock
incident evades this scan, the fix is to *extend this detector* (with a new mutation
fixture pinning the evasion shape), never to author a second parallel scanner —
one class, one ratchet. Non-blocking stewardship nit: the docstring declares
`Intent: CONTRACT` but no `Size:`; 3 of ~30 `tests/contract/` modules carry `Size:`
while the tier is otherwise implied by `pytestmark = pytest.mark.contract` — an
inconsistency of the *population*, not this file; no individual action.

### Check (b) — scan-test proliferation: harness intake candidate, or premature abstraction?

**Counted: the population is real — 15 source-scan tests at HEAD.** Tree- or
package-walking scans: `test_frozen_clock_aging_ratchet.py`,
`test_harness_env_contract.py`, `test_no_local_helper_copies.py` (all over `tests/**`);
`test_core_file_io_purity.py` (core/), `test_release_semver_canon.py`,
`test_telemetry_connection_factory_allowlist.py`, `test_session_store_ownership.py`,
`test_no_gpt_only_claim.py` (package tree); `test_no_bearer_in_url.py` (panel).
Single-module source scans: `test_denylist_scan.py` (no-allowlist raw-text),
`test_rules_skills_map.py` (citation scan), `test_telemetry_chmod_source_guard.py`,
`test_public_scripts_thin_wrapper.py`, `test_bind_resolution_seam_dynamic_walk.py`,
`test_kernel_tunables.py` (AST).

**"One scan harness, N rules" — REJECTED as premature abstraction, on evidence.** The
shared surface across the 15 is only the walker: ~10–15 lines each of
`Path(__file__).resolve().parents[N]` + `rglob("*.py")` + `__pycache__` exclusion. The
detectors — the actual value — are rule-specific by nature (raw-text where prose can
never spell the forbidden construct, AST where it can; different scopes, different node
shapes, different violation grammars). A harness would save ~150 trivial lines at the
cost of coupling N independent ratchets to one framework, whose every change then
touches all rules — precisely the cross-cutting-helper coupling the standing order
forbids and the A9 keep-helpers-inside precedent already adjudicated. The bug ledger
seals it: zero registered bugs trace to walker duplication across these 15 tests (no
repetition, no fix chain, no drift incident), and Firing 2's rule — duplication that
*requires a drift guard* is the duplication that must die — does not fire here, because
the parallel walkers require no guard against each other. No harness candidate.

**One narrow candidate IS evidence-supported: vacuous-pass exposure.** Verified live in
three files this session — `test_frozen_clock_aging_ratchet.py`,
`test_harness_env_contract.py`, `test_core_file_io_purity.py` — none asserts its
enumerated population is non-empty. Each roots itself by parent-count arithmetic
(`parents[2]`, `parents[N]`); a file move one directory deeper mis-roots the walker,
`rglob` over the nonexistent path yields zero files, and the ratchet passes **vacuously
green forever** — the exact false-confidence class Firing 2 ruled is itself bug surface
(a green guard pinning nothing). The frozen-clock test's in-memory mutation fixtures do
NOT cover this: they prove the detector bites, not that the walker enumerates the live
tree. Proposed backlog entry, for PM intake (operator decides — severity LOW, effort
LOW, class-wide):

> **scan-test-vacuity-guard** — Every tree-walking source-scan test asserts its
> enumerated population is sane before scanning: non-empty, and containing one named
> sentinel file known to exist (e.g., the scan test itself for `tests/**` scans). A
> mis-rooted walker then fails loudly instead of passing vacuously. Applied per test as
> a two-line assertion inside each walker function — a convention, NOT a shared
> harness (see the rejection above); ~9 tree-walking scan files touched, no framework
> introduced.

Per §6 (Backlog) this is a residual for the PM's intake report — this ruling
materializes no backlog entry.

### Bug-surface delta

**REDUCED.** Ledger evidence, full chain: the incident — tmp_gc suite dead at a UTC
date boundary, four tests red with zero code change, frozen `_NOW` injected while
fixtures aged by `time.time()` — was root-cause-fixed in v0.4.3 (same-clock derivation,
bug `tmp-gc-tests-age-files-by-the-real-clock-against-a-frozen-now`); the
security-reviewer's audit of all 9-then-10 aging sites established the shape was a
singleton with two self-healing relatives (fixed-past-date and epoch-0.0 margins GROW
with time rather than erode) and registered THIS bug as the class guard (`reported`
2026-08-19). The `resolved` event (2026-08-24) closes it with the ratchet GREEN at HEAD
over 0 live violations, hand-cross-checked against every `os.utime` site. Surface
delta: the class of latent test time bombs moves from *unguarded* (failure surfaces
months later, at midnight, deterministically unrelated to any diff — the
hardest-to-diagnose failure mode a suite can carry) to *guarded at authoring time*
(deterministic RED on the commit that introduces the shape, with file, constant name,
and call line in the message). Fix-chain audit: incident → root fix (v0.4.3) → class
ratchet (this diff); no repetition of the symptom since the root fix; no stacked patch;
no production growth; no puxadinho. Residual surface, named honestly: the scanner's
documented recall gaps (check (a)) and the vacuity exposure it shares with its 8
tree-walking siblings (check (b)) — the latter routed to intake, the former to the
one-class-one-ratchet maintenance contract above.

---

## Firing 4 — T-044-40 (commit `d9bb8004`): symlinked explicit specs root refused at the resolver seam

**Date:** 2026-08-24 · **Trigger:** FR23 evidence gate (`evidence_diff` net-positive
+22/-2, `dadaia_workspace/core/specs_resolver.py` only, `bugs.jsonl` `resolved` event
for `symlinked-specs-root-is-followed-by-migration-and-repair`)

### Verdict: SOUND — Firing 1's category (missing enforcement at the owning seam), production growth earned by behavior deletion

The +20 is one `is_symlink()` guard in `resolve_specs_dir`'s explicit-input branch,
raising `typer.BadParameter` before the pre-existing `.resolve()` dereferences the
link. This is Firing 1's exception, exactly: the bug's `reported` event registered an
**undecided contract** ("either resolve knowingly, or refuse the way the inner walk
roots are refused — decided once, at the resolution seam, not duplicated in each write
site"), and the diff is that decision made enforceable at the seam that owns it. Like
Firing 1, it is net-positive in lines and **net-negative in behaviors**: the
silent-follow path — migration rewriting atoms behind a link, TREE-5 repair refreshing
a projection behind it, both with no note — is eliminated. No flag, no second code
path, no per-verb special case; refusal was chosen over resolve-knowingly, which is the
*smaller* doctrine (one uniform rule shared with the inner walk roots, versus a
documented asymmetry plus a warning surface per consumer), and the correct side of the
ledger's own precedent: blind `.resolve()` has already produced one incident in this
codebase (the symlinked-venv escape, v0.1.11). Root-cause gate: **PASS** — the
`evidence_loop` reproduced the silent follow on the executed path (upgrade dry-run
reporting the real tree's backup parent; doctor JSON echoing the dereferenced root),
then killed the per-layer hypothesis by instrumentation: `SpecsDoctor` stores whatever
path it is given unresolved, so the dereference happens at the resolver seam and
nowhere else — proving the seam is the cause's home, not merely a convenient
chokepoint. Architecture-fidelity gate: **PASS** — see (a) and (b).

### Check (a) — the one-seam claim, verified by enumeration

**HOLDS for the resolver lane — with one residual second path, named below.** Grep over
the package: every CLI module exposing `--specs-dir` for a *resolution* verb —
`cli/commands/specs.py:41`, `migrate.py:48`, `memory.py:34`, `bugs.py:60/73/95`,
`newartifacts.py:69` — funnels through `cli/_specs_resolution.py:112
resolve_specs_dir_for_cli`, which is a pure delegation (`return
_core_resolve_specs_dir(specs_dir)`) to the guarded core function. The bug's named
surfaces (`specs upgrade`, `specs doctor --fix`) and every sibling verb therefore share
the one guard; the CLI integration tests
(`tests/integration/cli/test_cli_specs_symlinked_root_refused.py`, both entry points)
plus the unit seam test (`tests/unit/core/test_specs_resolver.py:104`) pin exactly
that topology — no guard duplicated into any command module, confirmed by grep:
`is_symlink` appears in no `cli/commands/*` file. `specs doctor --context`
(specs.py:108) is not a second *explicit-path* lane: `--context` is a NAME resolved via
`container.resolve_context_specs_dir`, mutually exclusive with `--specs-dir`, and the
bug's contract is scoped to the root the operator *names as a path*.

**Residual — one second explicit-resolution site exists, outside the resolver lane:**
`specs init` (specs.py:324) resolves its explicit `--specs-dir` directly
(`Path(specs_dir).resolve()`), bypassing the seam by design — init *creates* a tree
rather than resolving a context, and its default is `cwd/specs`, not the resolution
authority. Consequence: `dadaia specs init --specs-dir <symlink>` still scaffolds
behind the link, silently — same CWE-59 class, different verb class (creation, not
migration/repair; blast radius is a fresh scaffold misplaced, never an existing tree
rewritten). This does NOT break the resolved bug's contract (its `expected` field
scopes the decision to "the context-resolution seam", which init never enters), so it
is not a REJECT — but under the uniform-refusal doctrine this diff just established,
init's divergence is now a *documented asymmetry*, the very shape the fix argued
against. Residual for PM intake (severity LOW, effort LOW):

> **specs-init-symlinked-target-refusal** — `specs init`'s explicit-path branch
> (cli/commands/specs.py:324) applies the same symlinked-root refusal the resolver
> seam now enforces, either by calling one shared predicate or by routing its explicit
> branch through it; one unit test mirroring
> `test_resolve_specs_dir_refuses_a_symlinked_explicit_root`. Closes the last
> explicit-path lane that follows a symlinked root silently.

Per §6 (Backlog) this is a residual for the PM's intake report — this ruling
materializes no backlog entry.

### Check (b) — the A9 core-purity ratchet: within the exemption, twice over

**NO VIOLATION — the new call is inside the authorized boundary by two independent
readings of the ratchet.** `tests/contract/test_core_file_io_purity.py` (the A9
disposition: GUARD, not relocation) authorizes exactly five core stems for file I/O,
and `specs_resolver` is one of them (`_AUTHORIZED_STEMS`, line 52-54, pinned in
`architecture.md`) — the boundary was crossed deliberately at the module's birth, not
by this diff: the module already stats the filesystem (`is_file` at lines 34/47,
`.resolve()` throughout), because walking the tree IS its architecture-sanctioned job.
Independently, `is_symlink` is not even in the ratchet's flagged attribute set
(`_PATH_IO_ATTRS` = read_text/write_text/mkdir/exists/glob/iterdir/rglob) — so the new
call is doubly within bounds: an unflagged read-only stat, in an authorized module.
The ratchet stays GREEN with zero exemption widening; no `_AUTHORIZED_STEMS` edit, no
architecture.md edit, was needed or made. One pre-existing debt noted for the record,
untouched by this diff and out of its scope: `core/specs_resolver.py` raising
`typer.BadParameter` couples a core module to the CLI framework's exception type. That
coupling predates T-044-40 (the terminal unresolved-specs error, lines 179-186, with
its documented hooks-hot-path deferred import, F-01 v0.5.0); the new guard reuses the
established pattern rather than inventing a second error shape — consistency was the
right call inside this diff, and re-homing the error type is an architecture question
for a release, not a fix. Non-blocking.

### Check (c) — bug-surface delta with ledger evidence

**REDUCED.** The CWE-59 fix chain across the ledger, read in order: the symlinked-venv
`.resolve()` escape (v0.1.11 — first incident of the class, taught "blind resolve is a
hazard"); the migration's symlinked `memory/` walk-root refusal and the TREE-5
projection-target refusal (inner roots, guarded); FR17's symlink doctrine A17.1
(deletion lanes never follow symlinked dirs); the T-044-35 battery pinning
symlink-adjacent writer behavior (CWE-59 tag). Against that chain, the *outer* named
root was the one unguarded rung — the security-reviewer's `reported` event
(2026-08-19) names precisely that gap and demands a single-seam decision. This diff
closes the last unguarded rung of the class with the same doctrine the inner rungs
already carry: uniform refusal, one rule, zero per-site copies. Surface accounting:
one silent-acceptance path deleted (containment breach — writes landing outside the
tree the operator believes is being modified, the same misplaced-write class as the
venv incident); zero behavior change for every non-symlinked root (the pre-existing
explicit-wins test unmodified and green, per the `resolved` event); three pinning
tests at two levels of the topology. Fix-chain audit for this surface: `reported` →
`picked` (v0.4.4) → `resolved`, first fix, no repetition, no prior symptom patch to
undo, no stacked branch. Residual surface, named honestly: (1) the `specs init` lane
(check (a), routed to intake); (2) the guard checks the named root itself, not a
symlinked *ancestor* component (`--specs-dir /real-dir-via-linked-parent/specs` still
dereferences via `.resolve()` silently) — consistent with the bug's declared contract
("the root the caller named") and with Firing 3's declared-recall-boundary doctrine:
a guard with a stated boundary beats speculative widening; if an ancestor-link
incident ever materializes, extend THIS guard at THIS seam, never a second check
elsewhere; (3) a theoretical TOCTOU window between `is_symlink()` and `resolve()` —
acceptable under the workspace's advisory, races-surfaced-not-prevented posture, and
strictly smaller than the prior surface (no check at all). No puxadinho detected.
