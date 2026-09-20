# PLAN — Release: 0.4.7

**Status:** Aprovado
**Release ID:** 0.4.7
**Owner:** product-engineer

---

## Design (codebase-design vocabulary)

The README is the measured case: a document written beside its source rots at the
rate of the product (nine dead claims, two dead verbs in 15 KB). Candidate 4 does not
write better prose; it places a seam between memory and every document, and puts a
check at that seam.

- **Seam 1 — the memory atom as the docs' interface** (FR1, FR3, FR5, FR6). An atom
  is the one implementation of a product fact; a doc section is a caller. The
  `derived-from` marker makes the call explicit and the hash makes it checkable —
  the same shape `behavior-map.json` uses for skills (`hash_tuple`, re-recorded by
  review, the test naming what to re-read). Deletion test on the marker: remove it and
  the README of 2026-09-13 reappears — nothing else ties a sentence to its source.
  Deletion test on `derived-from: none`: allowing it reopens the side door every dead
  claim came through, so it does not exist. FR1 is the precondition: a doc derived
  from an unread atom derives a possibly false statement; the report is the atom's
  verified interface for this candidate, and the closure pass (RC-FLOW step 5) is where
  the atom itself is corrected — never a task write set (SPEC-DOC-047). The one
  transient the design accepts: between T-047-36 and closure a section may state the
  report's corrected truth against the hash of the uncorrected atom; the closure commit
  corrects the atom and re-records the hash, and the test is green on both sides.
- **Seam 2 — one command-tree walk** (FR2, FR3). `cli/help_digest.py` already walks
  the live Typer app for the injected digest; `test_behavior_map.py` walks it again
  for verb citations. `command_paths()` becomes the one walk; `render_digest()`, the
  test and the doctor root call it. `docs/cli.md` is `render_digest()`'s committed
  output, body-equal after the stamp line — a second renderer, or a generator hung on
  `public stage`, fails the deletion test (Q3 corrected).
- **Seam 3 — dead citations as one finder, two verdict classes** (FR2, FR3). The
  finders relocate from the test into `features/specs/citations.py` (relocation:
  the test shrinks by what the package grows). Two callers, two verdicts: over
  `specs/memory/**` the doctor reports `MEM-DRIFT-2` as a WARNING — QUALITY.md's own
  rule, memory drift is a closure finding because the implementer who deletes a verb
  cannot edit the atom; over `README.md`, `llms.txt`, `docs/**` the contract test is
  red, because the same implementer can and must regenerate `cli.md` and fix the doc
  in the deleting task. Layering: `features/specs` never imports `cli`; the doctor CLI
  root builds `command_paths()` and passes it as plain data, as `live_shas` travels.
- **Seam 4 — one home per metadata fact** (FR4). The tagline's home is `pyproject`
  `description`; README line 1, `llms.txt`'s `>` line and the GitHub description are
  equal to it (test-pinned where a file exists, log-recorded where settings state
  does). Topics are the keywords — no second list. `llms.txt` passes the deletion test
  only while every line is a link and none restates: an agent at the repository root
  gets the index and follows it to DADAIA.md, `docs/cli.md`, the memory catalog.
- **What dies.** `docs/01_medium_codex.md`; the hand-kept CLI table; the README's
  dead claims; the test-local finders and tree walk; `docs/vision.md` before it is
  born (Q6 corrected).

## Order of work (tracer bullets)

1. T-047-34 (FR1) and T-047-35 (FR2) run in parallel — disjoint write sets (a report
   under `.dadaia/tmp/` vs the package and its tests). After 35 the operator runs
   `dadaia doctor` and reads the first `MEM-DRIFT-2` lines, if any: the mechanical
   half of "zero drift" exists before any doc is written.
2. T-047-36 (FR3 core): `docs/cli.md`, `llms.txt`, the README rewrite, the
   derived-docs test, `01_medium_codex.md` deleted — slice: the PyPI long description
   is true and pinned.
3. T-047-37 (FR3 rest): `getting-started.md`, `concepts.md`; T-047-38 (FR4):
   pyproject urls + tagline test + `distribution.md`; T-047-39 (FR5): the closure
   protocol step — three tasks, disjoint write sets, all after 36.
4. T-047-40 (FR6) closure: the memory pass applies the report, re-derives, records.

## Verification

- Full preflight green; `lint-imports` shows no `features -> cli` edge (`command_paths`
  travels as data).
- `dadaia doctor` on this instance: `compliance(total)` 100 %, exit 0; before the
  closure pass the `MEM-DRIFT-2` lines equal the report's dead-citation corrections;
  after it, zero.
- `pytest tests/contract/test_docs_derived_from_memory.py` green; one deliberate atom
  byte change reddens exactly the sections derived from it (revert it); `dadaia help
  tree > docs/cli.md` is a no-op diff.
- `test_behavior_map.py` green with the imported finders; `test_every_cited_dadaia_
  verb_exists` unchanged in behavior.
- `wc -c README.md` ≤ 10240; `ls docs` = `cli.md concepts.md distribution.md
  getting-started.md`; `git ls-files docs` shows no `01_medium_codex.md`.
- PM: `gh repo view --json description,repositoryTopics,homepageUrl` matches
  pyproject `description`/`keywords` and Q10; the line is in the `log`.
- Closure `summary` applies the deletion test to each addition; ratchets untouched or
  down only.
