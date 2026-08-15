# PLAN — Release v0.11.0 — scan-v2: prior-published-term amnesty and push-gate hardening

**Status:** Aprovado — operator-delegated approval, 2026-08-15 (goal directive)
**Release ID:** v0.11.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.11.0/SPEC.md`
**Branch:** `feature/v0.11.0` (cut from `develop` at `d15bdf4e`; branch contract: `dadaia-gitflow`)
**Segment:** none — flat release; one implementation increment closed by a `qa-engineer`
review (the `alpha-1` close), then ship.

---

## 1. Strategy

Nine entries, one surface. Seven of them land inside a 190-line adapter
(`infrastructure/git_objects.py`) and a 170-line pure matcher
(`features/chokepoints/denylist_scan.py`), plus the decision module between them. That
concentration is the plan's central fact and produces four rules:

1. **Harden the floor before building on it.** FR7, FR8 and FR9 all restructure code
   FR1/FR2 then extend — so the amnesty lands on a parser that fails typed and a
   conversation whose memory is bounded, not the other way round.
2. **FR9 is a precondition, not a sibling (ADR D8).** The amnesty needs the prior content
   of each scanned path, doubling a peak already measured at ~277 MB on today's
   whole-range buffer. The chunk loop exists first; the prior-side lookup rides inside it.
3. **Ports carry the new data; the matcher gains no input.** The prior text arrives on
   `ScannedObject`, so `scan_objects` keeps its signature, `features/chokepoints/**` keeps
   its purity, and the composition root stays the only place that wires I/O.
4. **Co-deliver the pair that would otherwise regress each other.** FR4 makes the skip note
   name a path; FR6 masks it. FR4 alone opens a CWE-532 channel while closing a CWE-778 one.

**Ownership.** Every task is `software-engineer`'s except the git steps (dispatcher), the QA
close (`qa-engineer`) and the memory/CLOSURE authoring (`product-engineer`), who has no
shell and never implements.

---

## 2. Layers and surfaces affected

| Ring | File | Change |
|---|---|---|
| core | `core/protocols/git_object_reader.py` | `ScannedObject` gains the prior-text field (data only, zero I/O); docstring states the base-resolution contract and its fallback-shape boundary |
| core | `core/redaction.py` **(new)** | stdlib-pure masking primitive: word-boundary alternation, longest-first ordering, stable first-appearance ordinals |
| features | `features/chokepoints/denylist_scan.py` | FR1 suppression predicate; `ScanOutcome` grows structured oversized notes beside `skipped_binary_count` |
| features | `features/chokepoints/service.py` | FR7 sha validation in `parse_push_stdin`; FR4 note rendering in `_annotate_skip`; FR6 path masking in both renderers |
| infrastructure | `infrastructure/git_objects.py` | FR9 chunk loop; FR8 typed parse boundary + desync abort; FR4 bounded per-object prefix read; FR2 prior-side batched lookup; FR7 `--` and prefix check |
| cli | `cli/redact.py` | `ContextRedactor` becomes a thin consumer of `core/redaction.py`; behaviour byte-identical |
| cli | `cli/commands/ci.py` | FR5 registry-derived foreign-name set through the new container seam |
| composition | `container.py` | new registry-read seam mirroring `load_denylist_terms` / `load_denylist_baseline_patterns` |
| tests | 7 existing modules + at most 1 new unit module | see §8 |
| memory | 3 atoms + `catalog.json` | **CLOSURE only** (SPEC §5) |

**Untouched by design:** `infrastructure/data/privacy_baseline.json` (SPEC §4.3 — no version
bump), `infrastructure/privacy_check.py`, every `public/**` asset and projection tree,
`specs/_archive/**`, and the three `--redact` verbs' flag surface.

---

## 3. Execution order and why

```
01 definition commit ── 02 milestone (a): merge → security review → push
                               │
        ┌── floor hardening (git_objects + parse boundary) ──┐
        │ 03 FR7  sha validation + `--` + prefix check       │
        │ 04 FR8  typed parse boundary + desync abort        │
        │ 05 FR9  chunked conversation (bounds the peak)     │
        │ 06 FR4  oversized: bounded prefix read + counters  │
        └────────────────────────┬───────────────────────────┘
                                 │        ┌ 07 core/redaction.py extraction ┐
                                 │        └ (parallel-safe, disjoint set)   ┘
                          08 FR6 path masking in both renderers
                                 │
                          09 FR2 prior-side lookup inside the chunk loop
                                 │
                          10 FR1 matcher suppression predicate
                                 │
                          11 FR1 integration proof over a real range
                                 │
                          12 FR3 sentinel: tests/** + shrink-only baseline + marker
                                 │
                          13 FR5 registry-derived set (after the enumeration)
                                 │
                          14 A9.4/A9.5 real-content measurement (#28 evidence)
                                 │
                          15 qa-engineer review (alpha-1 close)
                                 │
                 16 memory (CLOSURE) ── 17 CLOSURE + archive + 0.8.0 bump
                                 │
                          18 milestone (b): ship
```

Why this order and not another:

- **03 before 04 before 05** — validation at the parse boundary means the parser 04 rewrites
  never sees an option-shaped sha; and 05 restructures the very loop 04 corrects, so reversed
  it would restructure code known to be wrong.
- **05 before 09** — ADR D8.
- **06 after 05** — the oversized path is decided inside the chunk loop (a blob is either a
  batch member or a bounded per-object read).
- **07 is the one sanctioned parallel task** — its write set (`core/redaction.py`,
  `cli/redact.py`, `tests/unit/cli/test_redact_output.py`) is disjoint from the
  `git_objects.py` / `service.py` chain.
- **12 after 11** — the sentinel's `tests/**` scope is only satisfiable once the amnesty
  exists and the fixture literals stop being push blockers.
- **13 last among the code tasks** — ADR D4; and its enumeration runs against a tree that
  already has the amnesty.
- **14 after 13** — the measurement must describe the shipped code, not a mid-flight state.

---

## 4. Design — FR1/FR2, the amnesty seam

**The seam is the `ScannedObject`, not a new parameter.** `scan_objects` keeps its four
arguments. Each object arrives carrying the prior published text of its own path, or an
explicit absence. `_first_match` gains one guard applied to every candidate before it is
appended:

```
suppress(candidate) ⇔ prior_text is not None
                      and candidate.matched_value.lower() in prior_text.lower()
```

`matched_value` already exists at each of the three candidate sites — `term`,
`match.group(0)`, `slug`. It feeds the predicate and is then discarded; only `masked_term`
leaves the module, so v0.9.0's A5.2 (no unmasked term in any `Hit` field) is unaffected. The
short-circuit property must survive: the guard filters candidates **within** a line, and a
line whose every candidate is suppressed continues to the next line rather than returning
`None` early.

**Adapter side.** `GitSubprocessObjectReader.new_objects` resolves a base once per call:

- `remote_sha` non-zero and resolvable ⇒ base = `remote_sha`;
- otherwise ⇒ **no base**, and every object carries an explicit absence (ADR D7).

With a base, each chunk performs two extra batched calls, on the same shape the content read
already uses:

1. `git cat-file --batch-check=%(objectname) %(objecttype) %(objectsize)` fed
   `<base>:<path>` lines — this both filters non-existent paths (git answers `missing`) and
   supplies the size, so the cap is applied before any prior content is fetched;
2. `git cat-file --batch` for the under-cap survivors.

Distinct paths are de-duplicated per chunk, so a path appearing twice costs one lookup.

**Fail-closed mapping (SPEC FR2's table).** A non-zero exit, timeout or missing `git` on
either call raises `GitObjectReadError` and the decision layer refuses, naming the failure. A
`missing` answer, an over-cap prior blob and an undecodable prior blob all map to *absence* —
never to an empty string, which would silently amnesty nothing but would also hide the
distinction from a future reader.

---

## 5. Design — FR9 chunking and FR4's bounded prefix read

**Chunking.** `_read_blobs` partitions `fetch_shas` into fixed-size chunks (a module
constant; 500 is the reviewer's suggested size and the plan's default) and runs the existing
`--batch` conversation per chunk, reusing `_run`'s `capture_output=True` and its
timeout/typed-error conversion unchanged — the bound comes from the chunk size, not from a
rewrite to `Popen`. This is the smaller of the two options the reviewer offered and it caps
the peak deterministically; a `Popen` incremental parser stays available if a measurement
ever demands it. Peak resident bytes become `chunk_size × cap` for content and, once §4's
prior side rides the same loop, `chunk_size × cap × 2` — constant in the range size.

**The oversized path.** An over-cap blob never enters a batch. It is read through
`git cat-file blob <sha>` with the stream read up to `_MAX_BLOB_BYTES` and then **closed**;
git stops producing, so the remainder is genuinely never fetched. Three implementation notes
are load-bearing:

- this call must **not** go through `_run` unchanged — the deliberate early close makes a
  non-zero exit / `EPIPE` expected, and `_run`'s contract is to convert failures into
  `GitObjectReadError`. Give it its own narrow helper whose docstring states why, and keep
  the timeout;
- the prefix is decoded with `errors="strict"`; a `UnicodeDecodeError` falls back to the
  binary class (SPEC A4.6);
- per-object spawning is confined to this path. A contract test asserts an under-cap range
  spawns none.

**Counters.** `ScanOutcome` keeps `skipped_binary_count` (undecodable only) and gains a tuple
of structured oversized notes (`path`, `size_bytes`, `scanned_bytes`). `_annotate_skip`
renders the two classes separately; the oversized wording names the file, its size, that only
its first 5 MB was scanned, that the remainder was **not** scanned, and that it needs a
by-hand check. Both classes are emitted on the allow and the refuse path, as today.

---

## 6. Design — FR8 typed boundary, FR7 argv hardening, FR5 registry seam

**FR8.** The header-parse pair inside the batch loop is wrapped:

```
try:
    newline_idx = out.index(b"\n", pos)
    ...
    content_size = int(size_str)
except ValueError as exc:
    raise GitObjectReadError(
        "git cat-file --batch stream desynchronised at object <sha>"
    ) from exc
```

and the existing `len(parts) != 3` branch **raises the same typed error instead of yielding a
fabricated object and continuing**. The rationale is in the SPEC: after a desync `pos` points
into content bytes, so continuing manufactures a stream of fake undecodable objects that are
then counted as binary skips — a gate reporting fiction.

**FR7.** A module-level compiled `^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$` (plus the existing
`ZERO_SHA` sentinel) is applied to both shas in `parse_push_stdin`; a violation increments
the existing `malformed` counter, so the fail-closed message and its `--no-verify` line are
reused verbatim. In the adapter, `_rev_list_candidates` appends `--` after the revision
arguments and `_is_resolvable_commit` applies the same shape check before interpolating.

**FR5.** `container.py` gains a seam returning the registry's `(name, repo_slug)` pairs,
built on `JsonContextStore(<workspace>/.dadaia/states).list_all()` and swallowing a missing,
empty or malformed registry into an empty result (A5.4 — a push hook never dies on registry
state). `cli/commands/ci.py#_foreign_repo_slugs` unions that with the `repos/` directory
names and subtracts **both** the pushing repo's own context name and its own repo slug. The
CLI still imports no `infrastructure` module.

---

## 7. Design — FR6, where the masking primitive lives

`features/chokepoints/**` imports `core` only. `ContextRedactor` lives in `cli/`. The
extension therefore cannot be an import in either direction, so the shared behaviour moves
**down** into `core/redaction.py`:

```
core/redaction.py        ← word-boundary alternation, longest-first, ordinal placeholders
   ↑                ↑
cli/redact.py     features/chokepoints/service.py
(ContextRedactor)  (_compose_denylist_refusal, _annotate_skip)
```

The gate renderers already receive the three term sources; masking a path means splitting it
on `/`, testing each segment against those sources, and replacing only the matching segments.
Line number, short sha and the non-matching segments are untouched, so the diagnostic stays
satisfiable — the property `quality-assurance.md` §"Satisfiable Diagnostics" requires.

`cli/redact.py`'s public behaviour must not move: `tests/unit/cli/test_redact_output.py`
passes with **no change to its assertions**, which is the regression proof that the extraction
was mechanical.

---

## 8. Test plan

**Reuse, do not multiply** (grill P15). The surface already owns seven modules; each new case
goes into the one that owns its seam:

| Seam | Module | Adds |
|---|---|---|
| matcher semantics | `tests/unit/features/chokepoints/test_denylist_scan.py` | FR1 suppression cases (A1.1–A1.4), FR4 counter split |
| decision layer | `tests/unit/features/chokepoints/test_push_denylist_scan.py` | FR7 malformed-sha cases, FR4 `decision.warn` allow+refuse (A4.5), FR6 masking (A6.1–A6.3) |
| adapter | `tests/unit/infrastructure/test_git_object_reader.py` | FR8 typed errors, FR9 chunk/invocation counts, FR4 byte-bound, FR2 prior-side cases |
| real git ranges | `tests/integration/test_push_gate_denylist.py` | A1.6 amnesty over a real remote, A2.3 forced failure, A5.1 DEAD-context fixture |
| repository sentinel | `tests/integration/test_repo_self_scan.py` | FR3 scope, baseline, shrink-only assertion, marker |
| redaction primitive | `tests/unit/cli/test_redact_output.py` | unchanged assertions + the primitive's own cases (new module only if it cannot host them) |
| e2e | `tests/e2e/test_push_denylist_journey.py` | **no new test** — the LARGE census stays at 56 |

Every test declares `Intent: CONTRACT — v0.11.0 <A-id>` or `Intent: SENTINEL — <seam>` at
birth; no SCAFFOLD, no test pruned to go green, and any deletion or skip requires a
`qa-engineer` verdict (`dadaia-test-stewardship`).

---

## 9. Validation plan

| id | What | Command | Acceptance |
|---|---|---|---|
| V1 | Full local gate | `.dadaia/.venv/bin/dadaia ci preflight` | A10.5 |
| V2 | Ring purity | `lint-imports --config setup.cfg --no-cache` | A1.5, A5.3, A10.3 |
| V3 | Matcher + decision suites | `python -m pytest tests/unit/features/chokepoints -p no:cacheprovider` | A1.1–A1.4, A4.4–A4.5, A6.1–A6.3, A7.1–A7.3 |
| V4 | Adapter suite | `python -m pytest tests/unit/infrastructure/test_git_object_reader.py -p no:cacheprovider` | A2.4–A2.5, A4.2, A8.1–A8.2, A9.2–A9.3 |
| V5 | Real-git ranges | `python -m pytest tests/integration/test_push_gate_denylist.py -p no:cacheprovider` | A1.6, A2.3, A5.1, A10.2 |
| V6 | Repository sentinel | `python -m pytest tests/integration/test_repo_self_scan.py -p no:cacheprovider` | A3.1–A3.5 |
| V7 | Sentinel marker reachability | `python -m pytest tests/integration/test_repo_self_scan.py -m integration --collect-only -q` | A3.5 |
| V8 | No amnesty list in the product | `grep -rn "AMNESTY\|SANCTIONED\|ALLOWLIST" dadaia_workspace/features/chokepoints/ dadaia_workspace/infrastructure/git_objects.py` (exclusions per SPEC §3) | A3.6, A10.1, A10.4 |
| V9 | Redaction regression | `python -m pytest tests/unit/cli/test_redact_output.py -p no:cacheprovider` | A6.4 |
| V10 | FR5 enumeration | one-off run of the widened term set over the pushable range and the tracked tree, hit list + disposition captured under `.dadaia/tmp/software-engineer/<YYYYMMDD>/` | A5.5 |
| V11 | Ordinary-range timing, before vs after | timed `push-gate-check` over `origin/develop..develop` at the base commit and at the tip | A9.5 |
| V12 | Fallback-range real-content measurement | timed run over the `--not --remotes` shape, capturing blobs, bytes, read s, match s, s/MB, peak RSS | A9.1, A9.4 |
| V13 | Specs health | `.dadaia/.venv/bin/dadaia specs doctor` | closure gate |
| V14 | Gate self-proof | the release's own `develop` push passes the modified gate with no `--no-verify` | FR10, R5 |

V10–V12 are measurements, not assertions; V12's figures evidence the #28 memory correction.

---

## 10. Technical risks and how the plan absorbs them

| Risk | How the plan absorbs it |
|---|---|
| The prior-side lookup multiplies git calls | Two extra batched calls **per chunk**, never per blob; A9.2's invocation-count test blocks a regression to per-object lookups |
| Chunk size is tuning, not contract | A named constant with its measured rationale in the comment; a test that depends on its value is mis-written |
| Case-insensitive substring over a prior blob is O(n·m) | It runs only for candidate hits, which are rare — the common path never touches the prior text; if V12 disagrees, A9.4's recorded decision is where it lands |
| The `ContextRedactor` extraction is the only refactor of working code | V9 with **unmodified** assertions is the safety net; if they cannot stay green, narrow the extraction — never edit the assertions |
| The sentinel baseline gets padded instead of shrunk | Growth is a visible diff in a SENTINEL module and a `qa-engineer` finding at the alpha close; A3.4 makes a stale row a failure |
