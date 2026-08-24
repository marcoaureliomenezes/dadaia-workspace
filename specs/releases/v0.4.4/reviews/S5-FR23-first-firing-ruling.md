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
