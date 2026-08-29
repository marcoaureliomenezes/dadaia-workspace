# PLAN — Release 0.5.1 — Deepening simplification K1–K11

**Status:** Aprovado
**Release ID:** 0.5.1
**Owner:** product-engineer
**Source SPEC:** `specs/releases/0.5.1/SPEC.md`
**Branch:** `feature/0.5.1`, cut from `main` at the shipped `0.5.0`
(`DADAIA.md` §4; mechanics `dd-gitflow-default`).
**Segments:** `alpha-1 … alpha-4` — the audit's four waves (ruling R2), each closed by a
`qa-engineer` stewardship verdict **committed on the branch**: no push-gated merge, no PR,
no `rc` burned (`RC-FLOW.md` step 3).
**Candidates:** `rc-1 … rc-N`. `rc-1` burns when the whole scope is implemented, gate-green and
QA-closed, and merges into `develop`; `rc-2 … rc-N` are adjustment rounds on that same scope; the
final `rc` carries memory → closure → archive and ships. If nothing is found, the final `rc`
**is** `rc-1`.

---

## 0. Terms, defined once

| Term | Meaning here |
|---|---|
| **module / interface / seam / adapter** | `codebase-design` SKILL vocabulary. A *deep* module hides a lot behind a small interface; a *shallow* one exposes nearly as much as it hides. |
| **decider** | A code path that answers a fact ("which context am I in"). The release's unit of work: N deciders → 1. |
| **deletion test** | If a module's whole contribution vanishes when its callers are inlined, it is not a module. Applied to `sdd_post_gate`'s reaper (2 of ~470 LOC survive). |
| **replace-don't-layer** | Write the test at the deepened interface, then delete the mirrored unit files. Never keep both shapes. |
| **leverage / locality** | *Leverage*: one fix serves many callers. *Locality*: the fix has one place to go. Both are why K1 leads. |
| **`alpha-N`** | A work boundary inside the release, closed by a committed QA verdict. Burns no `rc`, opens no PR. |
| **puxadinho** | A lean-to bolted onto a house: a branch, flag, special case, second code path, cross-feature reach-in or new side effect added instead of fixing the structure. Refused by standing order. |
| **proposed / accepted** | ADR statuses in `specs/ADRs/decisions.jsonl`. Any agent proposes; **only the operator** flips to `accepted` (`DADAIA.md` §6.5). |

---

## 1. Strategy

One ordering principle: **name the facts, then give each one owner, deepest dependency first.**

This release is the inverse of 0.5.0. That one *added* a canon and closed net-positive; this one
is a subtraction: eleven candidates, ~6,000 production LOC deleted, and a test corpus that shrinks
by the same order because 250 unit files mirror 240 modules one-to-one. Four constraints hold it:

1. **Nothing is renamed before it is named.** `CONTEXT.md` is task 1 (R4). Sixteen terms carry two
   or more meanings today; a deepened module named out of the old vocabulary would encode the
   ambiguity it exists to remove.
2. **The deepest dependency lands first.** K1 sits under the largest bug family (28+ records, one
   open) and is pure `core` with no new dependency. K2 and K7 become small once the sid and the
   context are decided once — so they wait for it rather than re-deriving it.
3. **Every task is net-negative and deletes at least one decider** (R3). A task whose diff only
   adds is rejected at review, whatever the tests say.
4. **A deletion never precedes its replacement.** Table-driven test at the new interface first,
   green, then the mirrored files die under a `qa-engineer` verdict — never pruned to go green.

The wave order is a dependency chain, not a preference. **`alpha-1`** creates the vocabulary and
the one value every other segment reads, and holds the pure-deletion work (K9's deletion half)
that needs no design. **`alpha-2`** is everything that becomes trivial once the sid exists (K2,
K7) plus K5, which is independent and can run in parallel. **`alpha-3`** is the three big
independent tables (projection rules, canon, handoff). **`alpha-4`** is the read-side/CLI tail
(K8, K10), the K11 ruling, and the two standalone bug fixes that belong to no candidate.

Then, and only then, the `rc` lane: a segment never reaches `develop` on its own — the four close
on the branch and the release integrates **once**, whole, as `rc-1`.

---

## 2. Layers affected

| Layer | Modules / paths | FRs |
|---|---|---|
| `core` | **`invocation.py` (new)** — `resolve()` + `Invocation` + the session-record owner moved from `features/spec_context/session_identity.py`; **one frontmatter parser (new)**; `models/handoff.py`, `models/adr.py`, `specs_resolver.py` **deleted** | FR-1, FR-6, FR-10 |
| `container.py` | dead lifecycle closures, `resolve_context`, `_context_specs_dir`, `_try_build_telemetry` composition — deleted or shrunk to wiring | FR-1, FR-8, FR-9 |
| `hooks/` | `sdd_gate.py`, `sdd_post_gate.py`, `ctx_inject.py`, `pre_gate.py`, `root_whitelist.py` — each becomes a policy over `Invocation`; the post-gate reaper deleted | FR-1, FR-2 |
| `features/spec_context` | `presence.py` (`gc` + `is_stale` — the only reaper and predicate), `doctor.py`, `gate_policy.py`, `session_identity.py` (moves to `core`) | FR-1, FR-2 |
| `features/public` + `infrastructure/public_assets.py` | `ProjectionRule` table, `projection_rules()`, `HarnessProjection` + three adapters; `install_helpers.py`, `workspace_guardrail.py`, `runtime_config.py`, `codex_doctor.py` collapse | FR-3 |
| `features/specs` | `canon/` (the `CANON` table), `scaffolder.py`, `doctor_structural.py`, `doctor_governance.py`, `doctor_release.py`, `catalog.py`; **`features/spec_artifacts` deleted** | FR-4, FR-5, FR-6, FR-10 |
| `features/bugs` + `core/models/bugs.py` | transition methods, `BugService.transition`, `migrate_v5.py` **deleted** | FR-5, FR-10 |
| `features/backlog` | `document.py`, `doctor.py` — four checkers become one | FR-5 |
| `features/handoff` (**new**) + `features/reports` + `panel/` | `HandoffIndex`, `Handoff`; `panel/reports_doctor.py` and `api_reports` re-derivations deleted | FR-6 |
| `features/chokepoints` | split into `branch_policy.py`, `pre_commit.py`, `push_gate.py`, `verdict.py`; `service.py` deleted | FR-7 |
| `features/telemetry` + `features/panel` | `TelemetryStore`, `Reader.ingest`, table-driven routes; `AuthClass` deleted | FR-8 |
| `features/migrate` + `features/repos` | six pre-v6 modules and the whole `repos` feature deleted | FR-9, FR-10 |
| `cli/commands` | `context.py`, `reports.py`, `bugs.py`, `backlog.py`, `panel.py`, `ci.py` — verbs stop resolving state themselves | FR-1, FR-5, FR-6, FR-7, FR-8 |
| `dadaia_workspace/public/` | `scaffold/releases/AGENTS.md` (R7 law drift), `scripts/generate-memory-catalog.py` **deleted** | FR-4, FR-10 |
| `.github/` | `workflows/ci.yml` (secret-scan on develop PRs), `scripts/pr-verdict-check.sh` (Python-backed `covering_verdict`) | FR-7, FR-12 |
| `pyproject.toml` / `setup.cfg` | `openpyxl` removed; the import-linter ignore cap **18 → 15** | FR-7, FR-9 |
| `tests/` | ~40 mirrored unit files deleted; ~10 table-driven interface tests added | all |
| repo root | **`CONTEXT.md` (new)** | FR-11 |
| `specs/` (this repo's own) | `ADRs/decisions.jsonl` (two `proposed` records), `memory/**` at closure, `releases/0.5.1/RELEASE.json` | FR-1, FR-9, closure |

**Layer rules hold unchanged.** `core` stays the bottom ring and stdlib-pure (`core/invocation.py`
does file I/O over session records — it joins the authorized set of P-11 in the same commit, with
its stem added to `test_core_file_io_purity.py`). Hooks import `core`, never the container (P-12).
`lint-imports` green with **no new accepted edge**; the cap moves down only.

---

## 3. Execution order

```
W0    definition commit (SPEC+PLAN+TASKS Aprovado + backlog purge-on-pick, one commit)
      -> RELEASE.json `defined` milestone at that sha
      -> T-051-02 baselines: LOC/module counts, decider counts, collect-only per tier,
         lint-imports edges, radon ceiling

alpha-1  T-051-01 CONTEXT.md (16 terms)            [naming gate for every later task]
      -> T-051-03 K1 core.invocation + bug 1       [deepest dependency]
      -> T-051-04 K9 deletion half                 [serial after K1: shares container.py]
      -> T-051-05 ADR proposals (P-01/P-08, P-09)  [software-architect]
      -> T-051-06 qa close alpha-1

alpha-2  T-051-07 K2 presence GC        \
         T-051-08 K7 chokepoints split   |  disjoint write sets — parallel worktrees
         T-051-09 K5 bug transitions    /
      -> T-051-10 qa close alpha-2

alpha-3  T-051-11 K3 projection rules   \
         T-051-12 K4 canon table (+R7)   |  disjoint write sets — parallel worktrees
         T-051-13 K6 handoff            /
      -> T-051-14 qa close alpha-3

alpha-4  T-051-15 K8 telemetry/panel    \
         T-051-16 K10 migration purge    |  disjoint write sets — parallel worktrees
         T-051-17 K11 ruling + ADR       |
         T-051-18 bug: mutation baseline |
         T-051-19 bug: secret-scan CI   /
      -> T-051-20 qa close alpha-4

scope complete  T-051-21 invariants measured (A-0.1 … A-0.5)
             -> T-051-22 trio review on one commit (code + security + qa)
rc-1            T-051-23 PR feature/0.5.1 -> develop, watch every job to green, merge
rc-2 … rc-N     T-051-24 adjustment rounds on this scope only
final rc        T-051-25 memory update -> T-051-26 closure narrative + disposition sweep
                + artifact GC -> T-051-27 archive (histo record + directory deletion)
             -> T-051-28 ship PR develop -> main, `shipped` milestone, branch cut
```

---

## 4. Approach per segment

### `alpha-1` — the vocabulary, the value, and the free deletion

`CONTEXT.md` is written before any code, because the whole release is a renaming exercise
disguised as a deletion: `Invocation`, `context_name`, `repo_slug`, `session_id`, `harness`,
`record`, `histo` and `canon` are all terms that currently mean two things. It is authored by
`product-engineer` (no shell needed) and is the naming authority every later QA close checks
against (A-11.2).

K1 is the release's highest-stakes task and runs alone. Its corpus of ~14 mirrored test files
becomes **rows in one table test written first**; only when that test is green over
`(env, cwd, payload, records)` do the eight ladders die. The open bug
`sdd-gate-memory-phase-resolves-empty-when-cwd-is-a-linked-worktree-outside-repos` is its RED
case — root-from-cwd versus context-from-`target_path` is exactly the seam the value object
removes, so the fix is structural, not a branch.

K9's deletion half needs no design: six dead closures (including a `git add -A` committer, dead
since `b94aede3`), `features/repos` with `openpyxl`, and single-consumer infrastructure filed
inside its feature wherever no lint contract breaks. It is **serial after K1** because both edit
`container.py` — the only non-disjoint pair in the release, declared here and in both task rows.
The protocol-retirement half does **not** run: `software-architect` appends the P-01/P-08 ADR as
`proposed` and stops. P-09's home rename (`core.specs_resolver` → `core.invocation`) rides the
same record.

### `alpha-2` — everything the sid unblocks, plus the independent K5

K2 and K7 both read the session id and both currently re-derive it; with `Invocation` in place
they are subtractions. K2's post-gate reaper fails the deletion test outright — only `renew` and
`touch` survive of ~470 LOC — and its "own record" guard is wrong today precisely because `bind`
mints a different sid than the harness. K7 is a file that is already four modules glued together;
each of its three suppressed import-linter edges marks one of the boundaries, so the split lets
the cap fall 18 → 15 in the same commit that removes them.

K5 is independent of K1 and runs in parallel. Its structural cause is that "status" and "the
fields that make that status true" are set by different calls, so completeness became a detector
bolted on after the write — 488 records incomplete, the same split fixed in the store on 08-24 and
in the doctor on 08-27. Transitions as methods make the invalid state unreachable; the doctor
receives the store it already injects for findings. The backlog's four checkers collapse in the
same task because they are the same shape.

### `alpha-3` — the three big tables

K3, K4 and K6 are independent of each other and of everything before them. K3 is the largest diff
and the riskiest surface (29 records, 13/13 fix commits added code), so it switches one fold at a
time — `install`, then `doctor`, then the ledger — each independently green with `public doctor`
clean between steps, and per-harness goldens as the safety net. K4's acceptance is a *property*:
`scaffold(t) ⇒ doctor(t) == []`, one test replacing six regressions of the same violated law; the
`spec_artifacts` package dies because it exists only to dodge the cross-feature lint. R7's law
drift (`public/scaffold/releases/AGENTS.md` still describing `RELEASE.jsonl` and `reviews/`) is
fixed in K4's task, since the scaffold source is the canon's renderer. K6 replaces ten readers
that each re-decide artifact-path resolution and schema-version routing with one index, and
carries the open `reports validate` bug as its RED case.

### `alpha-4` — the read-side tail, the ruling, and two standalone bugs

K8 gives the user-global sqlite an owner — the reason its corruption bug was deferred — and turns
a 100-line dispatch ladder into a route table; the open radon/C901 bug is `superseded` because the
factory it measures is deleted. K10 is pure subtraction: ~1,700 LOC of pre-v6 migrations, a
duplicate catalog script policed by a contract test that exists only to police it, an unreferenced
`AdrRecord`, and seven copies of one frontmatter regex; no bug has touched migration steps 1–5
since 2026-07-09. K11 is a **ruling only** — both options grow a feature, so `software-architect`
DRAFTs the two and appends a `proposed` ADR; code lands in this release only if the operator
accepts inside it, otherwise the two concurrency bugs stay open and are re-picked. The two
standalone bug fixes (mutation-baseline scope, secret-scan on develop PRs) belong to no candidate
and close here.

---

## 5. Parallelism

- Within `alpha-2`, `alpha-3` and `alpha-4` every task's write set is **disjoint**, so tasks may
  run concurrently in separate worktrees, each holding its own `[-]` — the exception
  `dadaia-task-manager` allows when TASKS declares disjoint write sets. TASKS.md declares them.
- `alpha-1` is **strictly serial**: T-051-01 → T-051-03 → T-051-04 → T-051-05. T-051-03 and
  T-051-04 share `container.py`; T-051-01 gates naming for both.
- Cross-segment parallelism is forbidden: a segment opens only after the previous segment's QA
  verdict is committed.
- Concurrent worktrees share one git index (open bugs 9, 10). Mitigation until K11 rules: stage
  exactly the task's write set, never `git add -A`, and re-check `git status` before every commit.

---

## 6. Test strategy

**Replace, don't layer — per K, in this order:** (1) write the table-driven test at the deepened
interface; (2) prove it green *and* prove it RED for each behaviour it inherits (bug cases first);
(3) delete the mirrored unit files named on the card, in the same commit, under the QA verdict.

| K | Mirrored files deleted | Added at the interface |
|---|---|---|
| K1 | ~14: `test_specs_resolver*`, `test_specs_resolution`, `test_common_sid_precedence`, `test_bind_resolution_seam_*`, `test_cli_bound_session_resolution`, `test_codex_thread_id_bind`, `test_context_name_differs_from_repo_slug`, ladder halves of `test_ctx_inject*`, `test_sdd_gate` | `tests/unit/core/test_invocation.py` — table over `(env, cwd, payload, records) -> Invocation` |
| K2 | `test_post_gate_reap`, `test_doctor_presence_sweep`, `test_doctor_gc`, the `tmp_gc` marker tests | `test_presence_gc.py` — records/markers/sentinels/empty dirs × TTL |
| K3 | `test_public_assets_{install,doctor,profile,kimi,hooks,render}`, `test_install_target_goldens`, `test_consumer_fanout*`, `test_codex_*` (5) | one "rule set per profile" table test + one write/compare pair + golden renders per harness adapter |
| K4 | the six scaffold-vs-doctor regressions, `check_tree4/8` unit tests, `spec_artifacts` tests | one property test `scaffold(t) ⇒ doctor(t) == []` |
| K5 | the completeness-detector tests, the `bugs/*.md` regex tests, the duplicated backlog checker tests | transition table test (each verb × missing-field matrix) + one malformed-line test |
| K6 | 12 reports test files (**2,162 LOC**) + panel sidecar fixtures | `HandoffIndex` tests; CLI tests become exit-code tests |
| K7 | `service.py`'s monolithic tests split with the module | one test per new module + one `covering_verdict` table test |
| K8 | `_dispatch_telemetry` ladder tests, `AuthClass` tests, duplicate model tests | route-table test + `TelemetryStore` lifecycle test (incl. `integrity_check`) |
| K10 | the six migration modules' tests, the catalog-duplicate contract test, `AdrRecord` tests | one frontmatter-parser table test; registry "stamp v6 or refuse" test |

**Rules.** Test intent and size declared at birth (`dadaia-test-stewardship` §A/§B). Zero new
`tests/e2e/**` without a named `qa-engineer` exception in that segment's verdict. No test dies
except under a `qa-engineer` verdict carrying the `file:line` map of superseding coverage,
executed by `software-engineer`. Expect a **net-negative** suite in files and functions (A-0.5) —
measured by `pytest --collect-only -q` against T-051-02's baseline, not estimated.

---

## 7. Validation and review plan

| Boundary | Who | What must be true |
|---|---|---|
| Per task | implementer | RED for the real reason; suite green; `ci preflight` green; handoff emitted; marker stays `[-]` |
| End of each `alpha-N` | `qa-engineer` only | every acceptance id of that segment evidenced; decider counts fell (A-0.2); deletion evidence with the coverage map; the **bug-surface delta** per touched feature; verdict **committed on the branch** — no push-merge, no PR, no closure |
| `alpha-1` head | `software-architect` | the `Invocation` interface ruled before the ladders die; the two ADR records appended `proposed` |
| `alpha-4` | `software-architect` | the K11 two-option DRAFT + its proposed ADR |
| K11 accept | **operator** only | no agent flips an ADR to `accepted`; without the accept, bugs 9/10 stay `open` |
| Scope complete | `qa-engineer` + `code-reviewer` + `security-reviewer` | all three `APPROVE` the **same** commit, on a thawed tree; each states the bug-surface delta with bug-history evidence |
| `rc-1` · `rc-N ≥ 2` | CI + `security-reviewer`, then `qa-engineer` | APPROVED verdict covering the PR head sha; **every** CI job green, not most; later rounds carry fixes on this scope only |
| Final `rc` | `product-engineer` + trio | memory → closure narrative → disposition sweep → artifact GC → archive, one commit, in that order, before the ship PR |

**Every push is watched to green on all jobs** — 0.5.0's rc-1 burned five portability fixes before
merging; a red job stops the segment rather than accruing to the `rc`.

---

## 8. Definition of done

- Every acceptance id in SPEC §5 evidenced, or dispositioned by an operator ruling in closure.
- **A-0.1 … A-0.6** hold: production LOC net-negative, decider counts fallen, ignore cap not
  raised (18 → 15), doctors clean, suite net-negative, QA verdict per segment with the bug-surface
  delta.
- All 12 picked bugs terminal, except bugs 9/10 which stay `open` with their stated reason if the
  K11 ADR is not accepted; the two `superseded` records carry
  `superseded_by=deepening-simplification-k1-k11`.
- `deepening-simplification-k1-k11` rewritten to its terminal token in
  `backlog/_archive/backlog_histo.jsonl` — one record, updated in place, never a second line.
- Two ADR records exist `proposed` (P-01/P-08 + P-09 home; K11 options); none flipped by an agent.
- `CONTEXT.md` at the repo root, and no module, class or field in the release's diff using a
  non-canonical term.
- Memory atoms updated at closure to the post-release truth; closure narrative in `RELEASE.json`
  `log`; `releases_histo.jsonl` summary appended; the release directory deleted in the same commit.
