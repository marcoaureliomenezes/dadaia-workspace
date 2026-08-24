# S5 — FR23 first-firing ruling: T-044-33 net-positive diff

**Reviewer:** software-architect · **Date:** 2026-08-24 · **Trigger:** FR23 evidence gate
(`evidence_diff` net-positive, `bugs.jsonl` `resolved` event for
`backlog-doctor-silent-on-duplicate-top-level-sections`, commit `f3b95a4d`)

## Verdict: SOUND — the growth is the missing enforcement, at the owning seam

The diff (+52/-20, `dadaia_workspace/features/backlog/document.py` only) replaces a
silent-drop path (`dict.setdefault`, first-wins) with enforcement of an invariant the
module docstring already claimed ("exactly two top-level sections") and never checked.
Net-positive in lines, **net-negative in behaviors**: one silent-truncation path is
eliminated; no flag, no second code path, no special case is bolted onto working code.
The new `DocumentError` conforms to the parser's established non-throwing diagnostic
model — no new error-handling shape was introduced. Root-cause gate: **PASS** (cause =
first-wins `setdefault`; fixed where it lived). Architecture-fidelity gate: **PASS**
(parser owns grammar/schema, doctor owns semantic checks; boundary intact).

## Check (a) — one representation, not two shapes

`_top_level_sections` (document.py:253) now returns exactly one shape:
`dict[str, list[tuple[int, int]]]` — occurrence lists for every heading name, uniformly.
The old single-value shape is gone; no dual representation coexists. The function stays
private with a single consumer. (`top_level_heading_starts`, document.py:298, keeps its
first-wins `dict[str, int]` — that is a different contract, the writer's insertion-point
primitive, not a second section model; first-LEDGER insertion remains correct even for a
corrupt document the doctor now flags. Non-blocking observation, no action required.)

## Check (b) — consumer adaptation, not duplication

Grep over the package finds exactly one consumer: `load_document` (document.py:485). Its
adaptation is two `for start, end in sections.get(...)` loops that call the **same**
pre-existing `_parse_active` / `_parse_ledger` per occurrence and extend one result list.
No parsing logic was duplicated; no second reading path exists (the writer,
`backlog_new`, checks membership by calling `load_document` itself, unchanged).

## Check (c) — doctor.py remains single-owner of slug-duplicate detection

`doctor.py` is untouched. BL-DUP's `_check_duplicate_slugs` (doctor.py:247) remains the
only slug-duplicate detector in the package. The parser's new error is about a repeated
**section heading** (document schema, the parser's own contract), a distinct concern; the
fix works by finally delivering both occurrences' items to the doctor's already-correct
check instead of duplicating that check into the parser. Correct division of ownership,
and the implementer proved BL-DUP was already-correct by instrumentation before writing
code (`resolved` event, `evidence_diff` field).

## Bug-surface delta

**REDUCED.** Evidence: the `reported` event (bugs.jsonl, this slug) documents live
corruption passing `backlog doctor` clean — ~150 duplicated lines caught only by eye. The
fix closes that silent-acceptance surface at the single parsing seam both reader and
writer share; RED-to-GREEN seams
(`test_document.py::test_duplicate_top_level_active_heading_yields_document_error_and_parses_both_bodies`
+ LEDGER sibling + `test_backlog_doctor.py` integration) pin it. Prior fix chain on this
file (v0.4.2 fence-awareness M1, unclosed-fence diagnostic) shows no repetition of this
symptom and this fix follows the same structural pattern — capture as located
diagnostic, never drop, never throw. No puxadinho detected; full suite 2756 passed.
