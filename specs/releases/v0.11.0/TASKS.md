# TASKS — Release v0.11.0 — scan-v2: prior-published-term amnesty and push-gate hardening

**Status:** Aprovado — operator-delegated approval, 2026-08-15 (goal directive)
**Release ID:** v0.11.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.11.0/SPEC.md`
**Source PLAN:** `specs/releases/v0.11.0/PLAN.md`
**Branch:** `feature/v0.11.0` (cut from `develop` at `d15bdf4e`; branch contract: `dadaia-gitflow`)
**Segment:** none — flat release; one implementation increment closed by T-110-15
(the `alpha-1` close), then ship.

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Standing rules for this release

- **`product-engineer` has no shell.** Every task marked **[git]** or carrying a measurement
  is executed by the dispatcher or `software-engineer`. `product-engineer` authors text only.
- **RED before GREEN.** Every behavioural task writes its failing test first and observes it
  failing **for the real reason** before the fix lands (`DADAIA.md` §6, root cause always).
- **Test intent at birth.** Every added test declares
  `Intent: CONTRACT — v0.11.0 <A-id>` or `Intent: SENTINEL — <seam>`. An undeclared test is
  SCAFFOLD and is slop here. **Zero new e2e tests** — the LARGE census stays at 56.
- **Reuse the seven existing modules** (PLAN §8). A new test module is authorized only where
  no existing module owns the seam, and at most one is expected.
- **Never prune to go green.** Deleting, skipping or disabling a test is a `qa-engineer`
  verdict with evidence, executed by `software-engineer` — never an implementer's shortcut.
- **No private term enters the repository.** Synthetic literals only: no foreign context
  name, repo slug, hostname, IP, email or absolute local path in any test, code comment or
  spec file — including this one. The gate this release modifies will refuse the push
  otherwise, and after T-110-12 the sentinel covers `tests/**` too.
- **One `[-]` at a time**, with exactly one sanctioned parallel pair: **T-110-07** may run
  concurrently with any single task in the T-110-03…T-110-06 chain — its write set
  (`core/redaction.py`, `cli/redact.py`, `tests/unit/cli/test_redact_output.py`) is disjoint
  from `infrastructure/git_objects.py` and `features/chokepoints/service.py`. No other pair
  is safe.
- **A group of completed work is one commit** — not one commit per file. Stage exactly the
  task's write set; never `-A` over a shared tree.
- **Reservation is observable.** Flip `[ ]` → `[-]` and commit `chore(tasks): start <id>`
  before the work, per `dadaia-task-manager`.

## Acceptance and evidence map

| Task | Entry | Acceptance ids | Evidence |
|---|---|---|---|
| T-110-01 | — | — | definition commit sha; `ACTIVE.md` reads `IMPLEMENTATION` |
| T-110-02 | — | — | pushed `develop` sha + APPROVED security handoff path |
| T-110-03 | #25 | A7.1–A7.5 | V3 output, commit sha |
| T-110-04 | #26 | A8.1–A8.4 | V4 output, commit sha |
| T-110-05 | #27 | A9.1–A9.3 | V4 output + peak-bound measurement path |
| T-110-06 | #20 | A4.1–A4.6 | V3 + V4 output, commit sha |
| T-110-07 | #23 (a) | A6.4, A6.5 | V9 output with unmodified assertions |
| T-110-08 | #23 (b) | A6.1–A6.3, A6.6 | V3 output, before/after refusal fixtures |
| T-110-09 | #19 (a) | A2.1–A2.6 | V4 output, invocation-count assertion |
| T-110-10 | #19 (b) | A1.1–A1.5 | V3 output, commit sha |
| T-110-11 | #19 (c) | A1.6, A2.3, A10.2 | V5 output over a real remote |
| T-110-12 | #19 (d) + #29 | A3.1–A3.6 | V6 + V7 output, baseline size |
| T-110-13 | #22 | A5.1–A5.6 | V5 output + V10 enumeration capture |
| T-110-14 | #28 evidence | A9.4, A9.5 | V11 + V12 captures under `.dadaia/tmp/` |
| T-110-15 | all | every id above + A10.1–A10.5 | `qa-engineer` APPROVED handoff |
| T-110-16 | #19, #28 | SPEC §5 | memory diff; `dadaia specs doctor` green |
| T-110-17 | all nine | closure obligations | `CLOSURE.md` under `_archive/`; `0.8.0` bump |
| T-110-18 | — | — | PR merged to `main`; CI green |

---

- [x] **T-110-01 — [git] Commit the definition content on `feature/v0.11.0`** (commit `11aad989`; phase flip landed one commit later, `chore(tasks)` follow-up — drift recorded)

**Owner role:** software-engineer (or dispatcher) · **Commit:**
`docs(T-110-01): v0.11.0 definition — scan-v2 amnesty and push-gate hardening`

**Preconditions:** `SPEC.md`, `PLAN.md` and `TASKS.md` all carry `**Status:** Aprovado`.
Working tree on `feature/v0.11.0`.

**Write set (staging only — content already authored by `product-engineer`):**
`specs/releases/ACTIVE.md`, `specs/releases/v0.11.0/{SPEC,PLAN,TASKS}.md`, the nine picked
`specs/backlog/*.md` status flips and `specs/backlog/candidates.md`.

**Description:** Stage exactly those paths and commit — the pick and the SPEC ride one commit
per `DADAIA.md` §5. Set `ACTIVE.md` phase from `DEFINITION` to `IMPLEMENTATION` in the same
commit.

**Done criterion:** one commit containing exactly those paths; `ACTIVE.md` reads
`release: v0.11.0` / `phase: IMPLEMENTATION`.

**Parallelism:** none — first task.

---

- [x] **T-110-02 — [git] Milestone (a): merge, security review, push** (merge `89a703b8`; APPROVED handoff `2026-08-15T173153Z-security-reviewer-v0.11.0-definition-push`; pushed, gate exit 0)

**Owner role:** dispatcher + `security-reviewer` · **Commit:** merge commit on `develop`

**Preconditions:** T-110-01 `[x]`.

**Write set:** git refs only (`develop`), plus the security-reviewer handoff under
`.dadaia/handoff/dadaia-workspace/`.

**Description:** Per `dadaia-gitflow` milestone (a), in order: merge `feature/v0.11.0` into
local `develop`; run a **diff-based** `security-reviewer` review of
`origin/develop..develop`; push `develop`. The push gate requires an APPROVED handoff keyed to
the pushed tip plus the CI preflight.

**Done criterion:** `develop` pushed; APPROVED handoff covering the pushed delta; CI green.

**Parallelism:** none.

---

- [x] **T-110-03 — FR7: pre-push sha validation and git argv hardening (#25)**

**Owner role:** software-engineer · **Commit:**
`fix(T-110-03): validate pre-push shas and close the git argv interpolation sites`

**Preconditions:** T-110-02 `[x]`.

**Write set:** `dadaia_workspace/features/chokepoints/service.py`,
`dadaia_workspace/infrastructure/git_objects.py`,
`tests/unit/features/chokepoints/test_push_denylist_scan.py`,
`tests/unit/infrastructure/test_git_object_reader.py`.

**Description:** RED first — a test feeding `--glob=refs/nonexistent` and `--branches=zzz` as
`local_sha` must fail because the gate currently produces a successful **empty** rev-list and
silently no-ops the scan. Then validate both shas in `parse_push_stdin` against
`^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$` plus the all-zero deletion sentinel, counting a
violation as a malformed line (reusing the existing fail-closed message — write no new one).
In the adapter, append `--` after the revisions in `_rev_list_candidates` and prefix-check the
sha in `_is_resolvable_commit`.

**Done criterion:** SPEC A7.1–A7.5 satisfied; `dadaia ci preflight` green.

**Acceptance / evidence:** A7.1–A7.5 · V3 output + commit sha.

**Parallelism:** T-110-07 only.

---

- [x] **T-110-04 — FR8: typed parse boundary and desync abort (#26)**

**Owner role:** software-engineer · **Commit:**
`fix(T-110-04): surface batch-stream desync as GitObjectReadError instead of fabricating`

**Preconditions:** T-110-03 `[x]`.

**Write set:** `dadaia_workspace/infrastructure/git_objects.py`,
`tests/unit/infrastructure/test_git_object_reader.py`.

**Description:** RED first — feed a truncated batch stream and a non-numeric size field
through the real adapter and observe a raw `ValueError` escaping the module's typed contract.
Then wrap the `out.index` / `int(size_str)` pair and raise
`GitObjectReadError("git cat-file --batch stream desynchronised at object <sha>")`. Change the
existing `len(parts) != 3` branch to raise the same typed error **instead of** yielding a
fabricated `decodable=False` object and continuing — after a desync `pos` points into content
bytes and every later header parse is garbage.

**Done criterion:** SPEC A8.1–A8.4 satisfied; no raw `ValueError` escapes the module and no
fabricated object can reach a skip count.

**Acceptance / evidence:** A8.1–A8.4 · V4 output + commit sha.

**Parallelism:** T-110-07 only.

---

- [x] **T-110-05 — FR9: bound the batch conversation's resident set (#27)** (peak-bound capture: `.dadaia/tmp/software-engineer/20260815/t-110-05-peak-bound-measurement.txt`)

**Owner role:** software-engineer · **Commit:**
`perf(T-110-05): chunk the cat-file --batch conversation to a constant resident bound`

**Preconditions:** T-110-04 `[x]`. **This is the precondition of T-110-09 (ADR D8) — do not
reorder.**

**Write set:** `dadaia_workspace/infrastructure/git_objects.py`,
`tests/unit/infrastructure/test_git_object_reader.py`.

**Description:** Partition `fetch_shas` into fixed-size chunks (named module constant,
default 500) and run the existing `--batch` conversation per chunk, reusing `_run` with its
timeout and typed-error conversion. Preserve the single-conversation win: **no per-blob
subprocess returns.** Add the contract assertion that subprocess invocations grow with the
number of chunks, not of blobs. Capture a peak-bound measurement over a multi-thousand-blob
synthetic range under `.dadaia/tmp/software-engineer/<YYYYMMDD>/`.

**Done criterion:** SPEC A9.1–A9.3 satisfied; existing adapter tests pass without weakening.

**Acceptance / evidence:** A9.1–A9.3 · V4 output + the peak-bound capture path.

**Parallelism:** T-110-07 only.

---

- [x] **T-110-06 — FR4: oversized blobs partially scanned and honestly reported (#20)**

**Owner role:** software-engineer · **Commit:**
`fix(T-110-06): scan the first 5 MB of an oversized blob and stop calling it binary`

**Preconditions:** T-110-05 `[x]`.

**Write set:** `dadaia_workspace/infrastructure/git_objects.py`,
`dadaia_workspace/core/protocols/git_object_reader.py`,
`dadaia_workspace/features/chokepoints/denylist_scan.py`,
`dadaia_workspace/features/chokepoints/service.py`,
`tests/unit/infrastructure/test_git_object_reader.py`,
`tests/unit/features/chokepoints/test_denylist_scan.py`,
`tests/unit/features/chokepoints/test_push_denylist_scan.py`.

**Description:** Read an over-cap blob through a **separate bounded** per-object stream
(`git cat-file blob <sha>`), reading at most the cap and closing the stream early so the
remainder is never fetched. That call gets its own narrow helper: its non-zero exit / `EPIPE`
is **expected** and must not become `GitObjectReadError` — document why in the docstring, and
keep the timeout. Keep `skipped_binary_count` for undecodable blobs only; carry oversized
blobs as structured notes (`path`, `size_bytes`, `scanned_bytes`). Render them in
`_annotate_skip` as what they are — file, size, first 5 MB scanned, remainder **NOT** scanned,
verify by hand — with today's wording retained for genuinely binary blobs, on the allow and
refuse paths alike. QA-1 closure: unit tests asserting `decision.warn` carries the note on an
allow case and on a refuse case.

**Done criterion:** SPEC A4.1–A4.6 satisfied; the byte-count assertion proves the remainder is
never read; the note's path is masked once T-110-08 lands (A6.3).

**Acceptance / evidence:** A4.1–A4.6 · V3 + V4 output + commit sha.

**Parallelism:** T-110-07 only.

---

- [x] **T-110-07 — FR6(a): extract the masking primitive into `core/redaction.py`**

**Owner role:** software-engineer · **Commit:**
`refactor(T-110-07): extract the redaction primitive into core for shared use`

**Preconditions:** T-110-02 `[x]`. **Sanctioned parallel task** — may run concurrently with
any single task of T-110-03…T-110-06.

**Write set:** `dadaia_workspace/core/redaction.py` (new),
`dadaia_workspace/cli/redact.py`, `tests/unit/cli/test_redact_output.py`.

**Description:** Move the word-boundary alternation, longest-first ordering and stable
first-appearance ordinal map into a new stdlib-pure `core/redaction.py`.
`cli/redact.py#ContextRedactor` becomes a thin consumer. The extraction is **mechanical**: its
proof is that `tests/unit/cli/test_redact_output.py` passes with **no change to its
assertions**. If they cannot stay green, narrow the extraction — never edit the assertions.
`core/` performs no I/O here, so the file-I/O authorized-set contract is unaffected.

**Done criterion:** SPEC A6.4–A6.5 satisfied; `lint-imports` green.

**Acceptance / evidence:** A6.4, A6.5 · V9 output with unmodified assertions.

**Parallelism:** the one sanctioned pair — see the standing rules.

---

- [x] **T-110-08 — FR6(b): mask path segments in both gate renderers (#23, resolution A)**

**Owner role:** software-engineer · **Commit:**
`fix(T-110-08): mask private-name-bearing path segments in every gate refusal and note`

**Preconditions:** T-110-06 `[x]` **and** T-110-07 `[x]`.

**Write set:** `dadaia_workspace/features/chokepoints/service.py`,
`tests/unit/features/chokepoints/test_push_denylist_scan.py`.

**Description:** `_compose_denylist_refusal` and `_annotate_skip` mask the offending path's
segments through `core/redaction.py`, using the three term sources the decision function
already receives. Split the path on `/`, test each segment, replace only matching segments —
line number, short sha and non-matching segments are untouched, so the operator can still
locate the file (satisfiable diagnostics). Where nothing matches, output must be
**byte-identical** to today (regression fixture). Cover the FR4 oversized note separately: it
began naming a path in T-110-06 and is the second channel of the same CWE-532 class.

**Done criterion:** SPEC A6.1–A6.3 and A6.6 satisfied; no unmasked private segment appears in
any emitted string.

**Acceptance / evidence:** A6.1–A6.3, A6.6 · V3 output + before/after refusal fixtures.

**Parallelism:** none.

---

- [x] **T-110-09 — FR2: prior-side same-path blob lookup inside the chunk loop (#19a)**

**Owner role:** software-engineer · **Commit:**
`feat(T-110-09): resolve each scanned path's published prior blob in the same conversation`

**Preconditions:** T-110-08 `[x]`. T-110-05 `[x]` is a hard precondition (ADR D8).

**Write set:** `dadaia_workspace/core/protocols/git_object_reader.py`,
`dadaia_workspace/infrastructure/git_objects.py`,
`tests/unit/infrastructure/test_git_object_reader.py`.

**Description:** Add the prior-text field to `ScannedObject` (data only; absence is explicit
and is the default, so every existing construction site keeps compiling). Resolve the base
once per call: `remote_sha` resolvable ⇒ base; otherwise **no base and no prior content
anywhere** (ADR D7 — the fallback shape stays byte-identical to v0.9.0). With a base, each
chunk performs two extra batched calls on `<base>:<path>` lines — `--batch-check` for
existence and size (so the cap applies before any prior content is fetched), then `--batch`
for the under-cap survivors — de-duplicating paths per chunk. Map failures per SPEC FR2's
table: a git failure raises the typed error and the decision refuses; a `missing` path, an
over-cap prior blob and an undecodable prior blob all map to **absence**, never to an empty
string.

**Done criterion:** SPEC A2.1–A2.6 satisfied; per-chunk subprocess invocations are a constant
independent of blob count.

**Acceptance / evidence:** A2.1–A2.6 · V4 output + the invocation-count assertion.

**Parallelism:** none.

---

- [ ] **T-110-10 — FR1: the amnesty suppression predicate (#19b)**

**Owner role:** software-engineer · **Commit:**
`feat(T-110-10): suppress a hit whose matched value the same path already published`

**Preconditions:** T-110-09 `[x]`.

**Write set:** `dadaia_workspace/features/chokepoints/denylist_scan.py`,
`tests/unit/features/chokepoints/test_denylist_scan.py`.

**Description:** RED first, with the three cases that define the semantics. Then add **one**
guard in `_first_match`, applied to every candidate before it is appended: suppress iff the
candidate's **matched value** occurs case-insensitively in the object's prior text. Key on the
matched value — `match.group(0)` for a baseline pattern, the literal for an operator term or a
foreign name — **never** on the pattern id, or a prior email address would amnesty a brand-new
one. The matched value is used for the predicate and discarded; only `masked_term` leaves the
module. Preserve the short-circuit: a line whose every candidate is suppressed continues to
the next line. `scan_objects` gains no parameter, so `features/chokepoints/**` stays pure and
acquires no new input source. **No list, constant, dict or set of sanctioned terms is
introduced** — A4.1's contract test must stay unmodified and green.

**Done criterion:** SPEC A1.1–A1.5 satisfied; `lint-imports` green.

**Acceptance / evidence:** A1.1–A1.5 · V3 output + commit sha.

**Parallelism:** none.

---

- [ ] **T-110-11 — FR1: integration proof over a real range with a real remote (#19c)**

**Owner role:** software-engineer · **Commit:**
`test(T-110-11): pin the amnesty over real git ranges`

**Preconditions:** T-110-10 `[x]`.

**Write set:** `tests/integration/test_push_gate_denylist.py`.

**Description:** Extend the existing module — do not spawn a parallel one. Three real-git
cases: (a) editing a file that already published the matched value at the base no longer
refuses; (b) the same value introduced into a new path still refuses; (c) a forced git
failure on the prior-side lookup refuses, naming the failure and `--no-verify`. Verify the
`git mv`-into-archive FROZEN↔scan test still passes **unmodified** — the invariant is untouched
by the amnesty.

**Done criterion:** SPEC A1.6, A2.3 and A10.2 satisfied.

**Acceptance / evidence:** A1.6, A2.3, A10.2 · V5 output over a real remote.

**Parallelism:** none.

---

- [ ] **T-110-12 — FR3: sentinel covers `tests/**` behind a shrink-only baseline, plus the marker (#19d, #29)**

**Owner role:** software-engineer · **Commit:**
`test(T-110-12): extend the self-scan sentinel to tests/ with a shrink-only baseline`

**Preconditions:** T-110-11 `[x]` — the scope is only satisfiable once the amnesty exists.

**Write set:** `tests/integration/test_repo_self_scan.py`.

**Description:** Add `tests` to `_SCAN_SCOPE`, keeping the `specs/_archive/**` and
`specs/audits/_archive/**` exclusions and the deterministic empty foreign-slug set unchanged.
Enumerate the surviving fixture literals as a literal baseline of `(path, pattern id)` rows
and assert both directions: **no hit outside the baseline**, and **every baseline row still
produces a hit** — so a cleaned file fails the test until its row is deleted and the count can
only shrink. State in the module docstring that this baseline is a **test assertion, never a
scan suppression**: the production matcher and adapter never read it, and A4.1's source scan
of `denylist_scan.py` is unchanged. Record the measured baseline size for `CLOSURE.md`. Fold
in #29: `pytestmark` gains `pytest.mark.integration` alongside `slow`, matching the six
sibling modules.

**Done criterion:** SPEC A3.1–A3.6 satisfied; the sentinel is collected under `-m integration`,
`-m slow` and `-m "not quarantine"`.

**Acceptance / evidence:** A3.1–A3.6 · V6 + V7 output + the recorded baseline size.

**Parallelism:** none.

---

- [ ] **T-110-13 — FR5: registry-derived foreign-name set, after the enumeration (#22)**

**Owner role:** software-engineer · **Commit:**
`fix(T-110-13): derive the foreign-name layer from the registry so a DEAD context still protects its name`

**Preconditions:** T-110-12 `[x]` (ADR D4 — the layer grows strictly larger and lands after
the amnesty). **The enumeration runs first, inside this task, before the widened layer is
committed.**

**Write set:** `dadaia_workspace/container.py`,
`dadaia_workspace/cli/commands/ci.py`,
`tests/unit/features/chokepoints/test_push_denylist_scan.py`,
`tests/integration/test_push_gate_denylist.py`.

**Description:** Step 1 — run the widened term set over the pushable range and the tracked
tree, capture the hit list and disposition every hit (amnestied by FR1, or explicitly
accepted with a reason) under `.dadaia/tmp/software-engineer/<YYYYMMDD>/`. Redact the capture
per the authoring doctrine. Step 2 — add a `container.py` seam returning the registry's
`(name, repo_slug)` pairs via `JsonContextStore(...).list_all()`, swallowing a missing, empty
or malformed registry into an empty result so the push hook never dies on registry state.
Step 3 — widen `_foreign_repo_slugs` to
`{registry names} ∪ {registry repo_slugs} ∪ {repos/ dir names} − {own context name, own repo
slug}`. Subtract **both** self-identities: `name` and `repo_slug` are separate fields and may
differ, and subtracting only the slug re-opens the A3.2 regression. The CLI still imports no
`infrastructure` module and no new `ignore_imports` entry is added.

**Done criterion:** SPEC A5.1–A5.6 satisfied; the enumeration capture exists and every hit
carries a disposition.

**Acceptance / evidence:** A5.1–A5.6 · V5 output + the V10 enumeration capture path.

**Parallelism:** none.

---

- [ ] **T-110-14 — Real-content performance measurement (#28 evidence)**

**Owner role:** software-engineer · **Commit:**
`chore(T-110-14): measure the shipped scan on real content, ordinary and fallback ranges`

**Preconditions:** T-110-13 `[x]` — the measurement must describe the shipped code.

**Write set:** `.dadaia/tmp/software-engineer/<YYYYMMDD>/` only (no repository file).

**Description:** Two measurements with their exact commands. (a) **Ordinary range** —
`origin/develop..develop` timed at the release base and at the tip, proving no regression
from chunking or the prior-side lookup (A9.5). (b) **Fallback shape** — the `--not --remotes`
range, capturing blob count, bytes, read seconds, match seconds, s/MB and peak RSS (A9.4).
Then record the decision on match-throughput optimisation: adopt it with before/after
real-content numbers, or reject it with a reason. These figures are the evidence for the #28
memory forward correction and are quoted verbatim in `CLOSURE.md` and in the atom.

**Done criterion:** both captures exist with their commands; the match-throughput decision is
recorded in writing.

**Acceptance / evidence:** A9.4, A9.5 · the two capture paths under `.dadaia/tmp/`.

**Parallelism:** none.

---

- [ ] **T-110-15 — `qa-engineer` review of the increment (alpha-1 close)**

**Owner role:** qa-engineer · **Commit:** review artifact committed to the branch

**Preconditions:** T-110-14 `[x]`.

**Write set:** `.dadaia/handoff/dadaia-workspace/` (+ `.dadaia/tmp/qa-engineer/<YYYYMMDD>/`
for captures); the review artifact committed to `feature/v0.11.0`.

**Description:** Verify the increment against SPEC FR1–FR10 acceptance ids one by one. Run
PLAN §9's V1–V14 and capture every command's output. Give particular weight to: the amnesty's
three semantic cases (A1.1–A1.3) — attack the smuggling path deliberately, since a predicate
keyed on the pattern instead of the matched value would pass a careless review; the
fail-closed table (A2.3–A2.4); the byte-bound on oversized reads (A4.2); the masking
regression fixture (A6.2); and the FR10 invariants, especially that A4.1's contract test and
the FROZEN↔scan test are **unmodified**. Confirm every added test declares its intent and size
at birth and that no test was pruned, skipped or weakened to go green. Apply the
redaction-at-authoring doctrine to this artifact.

**Done criterion:** APPROVED verdict enumerating every acceptance id, or REJECTED returning
named defects to the implementer.

**Acceptance / evidence:** all ids + A10.1–A10.5 · the APPROVED `qa-engineer` handoff.

**Parallelism:** none.

---

- [ ] **T-110-16 — Memory update (CLOSURE phase)**

**Owner role:** product-engineer · **Commit:**
`docs(T-110-16): memory — amnesty semantics, registry-derived layer, real-content perf`

**Preconditions:** T-110-15 `[x]` with APPROVED. `ACTIVE.md` phase set to `CLOSURE`
**before writing** — the gate allows `specs/memory/**` writes in `DEFINITION` and `CLOSURE`
only.

**Write set:** `specs/memory/product/sdd/sdd-gate-v3.md`,
`specs/memory/architecture.md`, `specs/memory/quality-assurance.md`,
`specs/memory/product/catalog.json` (regenerated **only** if a touched atom's `tldr`/`summary`
frontmatter changed, via `dadaia_workspace/public/scripts/generate-memory-catalog.py`).

**Description:** State the product as it is **now**, per SPEC §5 — no changelog, no history,
no version narrative. In `sdd-gate-v3`, one pass covering both bound items: the amnesty
semantics (same-path prior-published values never refuse; a new path or a new value still
refuses; no amnesty in the fallback shape), the **surviving** invariants stated explicitly
(no sanctioned-terms list anywhere; FROZEN↔rename unchanged), the term layer as
registry-derived, the oversized row rewritten from "skipped" to "first 5 MB scanned, remainder
never fetched", the new fail-closed rows, the chunk-bounded conversation, and **#28's forward
performance correction** with T-110-14's real figures explicitly superseding the archived V14
synthetic figure. In `architecture.md`, the widened `GitObjectReader` contract and the new
`core/redaction.py` primitive. In `quality-assurance.md`, that the by-hand masking branch is
no longer the only one, and the amnesty's effect on refusal clearability.

**Done criterion:** `dadaia specs doctor` green on memory checks; no forbidden section added;
SPEC §5 satisfied file by file.

**Acceptance / evidence:** SPEC §5 · memory diff + `specs doctor` output.

**Parallelism:** none.

---

- [ ] **T-110-17 — CLOSURE, dispositions, archive, version bump**

**Owner role:** product-engineer (text) + software-engineer/dispatcher (**[git]** steps) ·
**Commit:** `docs(T-110-17): close release v0.11.0`

**Preconditions:** T-110-16 `[x]`.

**Write set:** `specs/releases/v0.11.0/CLOSURE.md` (new), `specs/releases/ACTIVE.md`,
`specs/backlog/*.md` (the nine terminal dispositions) and `specs/backlog/candidates.md`,
`pyproject.toml` (version), `CHANGELOG.md`, plus the release-directory move.

**Description:** In the finalization order **memory → CLOSURE → archive**:

1. Record the T-110-16 memory writes under `## Memory updates`.
2. Write `CLOSURE.md` per `dd-release-closure`: summary, tasks + commit SHAs, validations
   V1–V14 with evidence, drifts, `## Dispositions` (all nine picked entries →
   `DELIVERED — v0.11.0`; state explicitly that **no bug and no audit** was picked) and
   `## Test dispositions`. Carry the measured sentinel baseline size, the V10 enumeration
   dispositions, T-110-14's real-content figures, and the recorded match-throughput decision.
   Residuals go under **`## Intake candidates`** — compiled for the PM's operator-facing
   intake report, **never materialized as backlog entries** (ADR #15).
3. **[git]** `git mv specs/releases/v0.11.0 specs/_archive/releases/v0.11.0`; set `ACTIVE.md`
   to the next release or `release: none` / `phase: none`.
4. **[git]** Bump `pyproject.toml` to **0.8.0** (ADR D5; currently `0.7.1`) and add the
   `[0.8.0]` `CHANGELOG.md` entry in the same commit.

**Done criterion:** `CLOSURE.md` complete under `specs/_archive/releases/v0.11.0/`;
`ACTIVE.md` no longer points at `v0.11.0`; `dadaia specs doctor` green.

**Acceptance / evidence:** closure obligations (SPEC §5) · `CLOSURE.md` path + bump commit sha.

**Parallelism:** none.

---

- [ ] **T-110-18 — [git] Milestone (b): ship**

**Owner role:** dispatcher + `code-reviewer` + `security-reviewer` · **Commit:** merge commit
+ PR

**Preconditions:** T-110-17 `[x]`.

**Write set:** git refs only, plus the reviewer handoffs.

**Description:** Per `dadaia-gitflow` milestone (b), in order: `code-reviewer` six-axis pass
over the release delta; merge `feature/v0.11.0` into local `develop`; diff-based
`security-reviewer` review of `origin/develop..develop` — this review is asked explicitly to
verify that the amnesty **cannot** be abused to smuggle a new value through an edited path
(entry #19's own ownership note) and that CWE-778, CWE-532, CWE-88/20, CWE-755 and CWE-400 are
each closed; push `develop` — **with no `--no-verify`**, which is itself the release's
self-proof (V14); open PR `develop` → `main`; watch CI until every job is green; merge.

**Done criterion:** PR merged to `main`; CI green; `feature/v0.11.0` no longer needed.

**Acceptance / evidence:** — · PR number + green CI run.

**Parallelism:** none — last task.
