# ALPHA-6-QA.md — `alpha-6` (WS-F, consumer round + published lineage) segment QA gate

**Task:** T-043-49 · **Reviewer:** qa-engineer · **Segment range:** `429e8258` (alpha-5
close) `..` `e323ed9f` (T-043-48, last alpha-6 commit) · **Reviewed at:** `47dee4bd`
(reservation commit, `feature/0.4.3`) · **Reviewed:** 2026-08-18

**Verdict: APPROVED** — every `alpha-6` acceptance id in scope (A30.1–A30.6, A31.1–A31.4)
is verified. A30.1–A30.4 and A30.6 are re-confirmed by independently re-reading
T-043-46's consumer-round artifact against the preserved throwaway-workspace evidence
trail and cross-checking its GC-touchpoint table against `ALPHA-5-QA.md` §6.3's own
pre-named list — no discrepancy found. A30.5 is re-verified live: the segment's one bug
(`ancestor-walk-workspace-root-silent-mistarget`) carries a complete
`reported`→`resolved` pair, and its 6 cited RED-then-GREEN reproducing/regression tests
all pass live, re-run by this review. A31.1–A31.4 are re-verified live: 4 of the 10
retroactive CHANGELOG sections spot-checked commit-by-commit against `git log` on their
stated tag ranges (exceeds the 3 required), the 3 unpublished-internal annotations are
present and correctly worded, and the `e2eb28f8..e323ed9f` diff is confirmed additions-only
(zero deletion lines beyond the diff's own `---` file header). PLAN §5's `alpha-6` exit
criteria are met. Full suite 2582 passed / 3 skipped / 0 failed — unchanged from
T-043-47's own baseline (T-043-48 touched only `CHANGELOG.md`). `dadaia ci preflight`
5/5 PASS. `dadaia doctor` healthy. `dadaia specs doctor` 0 errors / 5 pre-existing
unrelated legacy warnings (same 5 as `alpha-5`'s baseline — no new warning introduced).
`dadaia public doctor` all `[ok]` (`public-privacy`, `entities-derivation`,
`model-resolution`). Bug ledger: `dadaia bugs status` → 0 open. Worktree clean at every
checkpoint.

---

## 1. Scope and method

Task delta (7 commits): T-043-46 reservation `5495fd16`, bug-register `8ca8ac41`,
round-commit `41f427d1`; T-043-47 reservation `1c67bbaf`, fix commit `e2eb28f8`;
T-043-48 reservation `c6d09e9a`, CHANGELOG commit `e323ed9f`. `git log --oneline
429e8258..e323ed9f` confirms exactly these 7 commits, no more, no less — the declared
scope is exact.

Every load-bearing claim in this review is independently re-run or re-derived against
the live tree at HEAD (`47dee4bd`, the T-043-49 reservation commit) rather than trusted
from prior-session prose: the bug's regression tests are re-executed, the CHANGELOG
sections are re-checked against `git log` on their own stated ranges, the diff shape is
re-diffed, and the full suite/doctor/preflight numbers are re-run fresh, not copied from
T-043-47's evidence block.

Memory bootstrap (step 0) self-pulled `specs/memory/product/catalog.json` and
`specs/memory/quality-assurance.md` (this segment's own domain: test layers, the
anti-slop/redaction posture, and the flake/quarantine pipeline that the segment's one bug
regression suite must respect) — neither atom is stale relative to this segment's scope;
memory update is `rc-1`/T-043-51 territory (MEMORY-class, phase-gated to
DEFINITION/CLOSURE; current phase is IMPLEMENTATION).

---

## 2. Per-acceptance-id table

| id | Requirement (abridged) | Evidence | Verdict |
|---|---|---|---|
| A30.1 | Consumer surface consumes the installed, version-matched skill surface; canonical verbs only | T-043-46 artifact §2/A30.1: `public doctor` all `[ok]` in the throwaway workspace; 29/29 extracted `dadaia <verb…>` skill references cross-checked live against `dadaia --help`; the one apparent "removed command" hit is the skill's own negative documentation, confirmed by reading the surrounding sentence. Re-read by this review directly against the artifact's cited evidence lines — internally consistent, no gap | PASS |
| A30.2 | Consumer's owning repo is governance-coherent: one `[-]` at a time, valid memory/schema state, immutable release evidence | T-043-46 artifact §2/A30.2: fresh `valproj` consumer context proves the full `[ ] → [-] → [x]` marker cycle with clean worktree at each commit; `SPEC-DOC-024`/`SPEC-DOC-004` proven to fire correctly and fold to 0/0 after remediation; the throwaway workspace's own projected `codex-pre-gate` hook invoked directly, confirms FROZEN-path block + ADDITIVE-path allow live in the consumer's own repo. Re-read against the artifact's cited command sequence — coherent | PASS |
| A30.3 | Pre-v0.12.0 workspace upgraded in place surfaces its un-migrated backlog state, then folds clean | T-043-46 artifact §2/A30.3: seeded 3 loose per-entry backlog files → `specs doctor` reports exactly 3 `SPEC-DOC-035` WARNs (WARN count == loose-file count) while `backlog doctor` reports clean on absent `BACKLOG.md`; migration via `backlog new` × 3 + archive move folds both doctors to fully clean. Re-read against the artifact's cited command sequence — the WARN-count-equals-loose-file-count invariant and the post-migration clean fold both hold as claimed | PASS |
| A30.4 | Every environment limit recorded honestly; unexercised criteria never reported as passed | T-043-46 artifact §4: 4 limits recorded (system `python3` interpreter version constraint — resolved, no verdict impact; FR24 push-verdict GC no live caller — A30.6 touchpoint 2 recorded not-exercised, not passed; FR25 release-closure sweep out of round scope — A30.6 touchpoint 3 recorded not-exercised, not passed; `reports validate` no `--workspace` override at discovery time — registered as F-1, not silently absorbed). No criterion anywhere in the artifact is marked PASS/exercised without a cited evidence line — verified by re-reading every acceptance-id and GC-touchpoint row in §2/§3 | PASS |
| A30.5 | One remediation cycle budgeted inside the segment; a finding is fixed here, not deferred | T-043-47: one finding (F-1, bug `ancestor-walk-workspace-root-silent-mistarget`, HIGH), root-caused and fixed within the segment's own budget, `resolved` event appended (§4 below, bug-ledger status). RED-then-GREEN re-run live by this review, §3 below: all 6 cited tests pass | PASS |
| A30.6 | Round's scope explicitly includes the `alpha-5` GC surface; artifact names which capabilities were exercised | T-043-46 artifact §3: 7-row table cross-checked by this review against `ALPHA-5-QA.md` §6.3's own pre-named 7-touchpoint list — exact match, same 5 exercised (ack-on-consume, reconciler reap, log rotation, cache guard, `dadaia tmp gc` dry-run+destructive) and same 2 not-exercisable (push-verdict GC, release-closure sweep), for the exact reasons §6.3 itself pre-warned. No touchpoint is claimed exercised without its own evidence line | PASS |
| A31.1 | Every published version in the PyPI lineage has a section; each is traceable to commits | All 10 sections present, one each, confirmed by `grep -c "^## \[<v>\]"` for every version in the required list (§5 below). 4 of the 10 spot-checked commit-by-commit against `git log <tag>..<tag>` on the section's own stated range — exact sha and count match in all 4 (§5 below) | PASS |
| A31.2 | No section asserts a change git history does not show; every line is reviewer-checkable against a range | Every retroactive section's prose states its exact `git log` range and commit count inline, letting a reviewer re-run the identical command; this review did so for 4 sections and found the sha, count, and quoted commit subjects to match exactly, with no invented or embellished content beyond the verbatim commit subject | PASS |
| A31.3 | The three phantom headings carry an unpublished-internal annotation; none removed or renamed | `[0.1.24]`, `[0.1.7]`, `[0.1.3]` all present, all three carry an explicit "Unpublished-internal (T-043-48/FR31, SPEC A31.3)" annotation, confirmed by direct grep against `CHANGELOG.md` | PASS |
| A31.4 | One-axis rule (v0.4.2 FR13) still holds: the release id is the package version | Unchanged by this segment — `CHANGELOG.md`'s "Versioning note" preamble (authored in the `v0.4.2` section, untouched by T-043-48) still states the one-axis rule verbatim; T-043-48's own diff is additions-only (§6 below) so nothing that established A31.4 was touched | PASS |

---

## 3. A30.5 remediation — re-run of the bug's RED-then-GREEN evidence

Bug: `ancestor-walk-workspace-root-silent-mistarget` (HIGH). Both cited root-cause
reproductions (`dadaia init`'s bare ancestor-walk mistargeting a nested throwaway
workspace's ancestor; `dadaia reports validate`'s lack of a workspace override
producing a false `missing_artifact`) and their fix's regression coverage were re-run
live by this review, not trusted from T-043-47's prose:

```
tests/unit/core/test_workspace_resolver.py::test_bare_init_nested_inside_ancestor_dotdadaia_targets_cwd_not_ancestor PASSED
tests/unit/core/test_workspace_resolver.py::test_bare_init_nested_one_level_inside_dotdadaia_targets_cwd PASSED
tests/unit/core/test_workspace_resolver.py::test_bare_init_sub_repo_not_inside_dotdadaia_still_walks_up PASSED
tests/integration/test_cli_init.py::test_bare_init_nested_inside_ancestor_dotdadaia_targets_cwd PASSED
tests/contract/cli/test_cli_reports.py::test_reports_validate_workspace_override_fixes_false_invalid PASSED
tests/contract/cli/test_cli_reports.py::test_reports_validate_always_emits_resolved_workspace_root_json_mode PASSED

6 passed in 0.86s
```

All 6 pass. A30.5 holds.

---

## 4. Bug ledger

`dadaia bugs status` → `[ok] 0 open bug(s).` at review time.

The segment's one Arm-B rider, `ancestor-walk-workspace-root-silent-mistarget`, carries
a complete event pair in `specs/bugs/bugs.jsonl`: `reported` (commit `8ca8ac41`, during
T-043-46), `resolved` (folded into T-043-47's fix commit `e2eb28f8`). Full-ledger scan
(443 bug ids total across the repo's history) confirms every stream opens with
`reported` and closes with a terminal event (`resolved`/`rejected`/`superseded`); the one
stream with an out-of-order `resolved, reported, resolved` shape
(`closure-catalog-references-missing-memory-atom`) is a documented, pre-existing v0.5.0
FR2 ledger-repair compensating event unrelated to this segment, and it too folds to a
terminal `resolved`. No open, orphaned, or incomplete pair exists anywhere in the ledger.

---

## 5. A31 — CHANGELOG spot-check (4 of 10 retroactive sections, exceeds the required 3)

| Section | Stated range | Live `git log` re-run | Match |
|---|---|---|---|
| `[0.4.1]` | `v0.4.0..v0.4.1` (1 commit, `bd6c9f2a`) | 1 commit, `bd6c9f2a`, subject matches verbatim | Exact |
| `[0.3.0]` | `v0.2.3..v0.3.0` (2 commits, `86f4cd99`..`f20e4492`) | 2 commits, same two shas, subjects match verbatim | Exact |
| `[0.2.1]` | `v0.2.0..v0.2.1` (1 commit, `b1cb28dc`) | 1 commit, `b1cb28dc`, subject matches verbatim | Exact |
| `[0.1.6]` | `v0.1.5..v0.1.6` (5 commits, `8b80090e`..`6b637427`, "all 5 commits listed") | 5 commits, same 5 shas, all 5 subjects present in the section, verbatim | Exact |

No invented content found in any spot-checked section. The three unpublished-internal
annotations (`[0.1.24]`, `[0.1.7]`, `[0.1.3]`) are present and correctly worded, each
citing SPEC A31.3 by id. All 10 required published versions (`0.1.2`, `0.1.5`, `0.1.6`,
`0.2.0`–`0.2.3`, `0.3.0`, `0.4.0`, `0.4.1`) have exactly one section each, confirmed by
direct count.

**Diff shape (additions-only):** `git diff e2eb28f8..e323ed9f -- CHANGELOG.md` →
`1 file changed, 138 insertions(+)`, zero deletion lines beyond the diff's own `---`
file-header marker. Nothing was deleted or renamed, exactly as A31.3's "nothing is
deleted or renamed" and TASKS.md's own instruction require.

---

## 6. Carried forward for CLOSURE (verbatim — T-043-51/52 consume these statements)

Per TASKS.md T-043-49's own done criterion, the following are the **exact carried-forward
statements**, unmodified from their source:

**A30.4 environment limits (4 items, from T-043-46 §4):**

1. System default `python3` interpreter (3.10.12) does not satisfy the package's
   `>=3.12,<4.0` requirement; `python3.12` had to be explicitly selected to build the
   round's runner venv. Not a product defect — a documented `Requires-Python` constraint
   working as intended — recorded as an environment fact per A30.4. No verdict impact.
2. FR24 (push-verdict GC) has no live caller on the real push path yet (per
   `ALPHA-5-QA.md` §6.1: a correct, tested pure action function exists, but nothing
   wires it in). Could not be exercised as a live end-to-end behavior through any
   supported interface in a throwaway, non-pushable local workspace. Already routed by
   the `alpha-5` review to `rc-1` CLOSURE memory + backlog intake — not re-litigated in
   this segment.
3. FR25 (release-closure sweep) is out of the consumer round's scope: the round's own
   scripted `valproj` journey opened one release segment (for the A30.2 marker-discipline
   demo) but never drove it to closure — reaching closure was not needed to prove A30.2's
   coherence checks and would have consumed budget better spent on the GC surface.
4. `dadaia reports validate` had no `--workspace` override at the time of discovery
   (Findings F-1 in the T-043-46 artifact); discovered live and registered as the bug
   `ancestor-walk-workspace-root-silent-mistarget`, remediated within this segment's own
   budget by T-043-47 (A30.5). The override now exists — this is a **historical** limit
   record for the round's own timeline, not a currently-standing gap.

**GC coverage statement (A30.6, from T-043-46 §3):** 5 of 7 `ALPHA-5-QA.md` §6.3 GC
touchpoints live-exercised with evidence — ack-on-consume (FR23), reconciler reap
(FR26), log rotation (FR27), cache guard (FR28), `dadaia tmp gc` dry-run + destructive
(FR29). 2 touchpoints explicitly recorded not-exercisable, both for the exact reasons
`ALPHA-5-QA.md` §6.3 itself pre-warned: push-verdict GC (FR24) has no live caller yet;
release-closure sweep (FR25) was out of the round's scope. No touchpoint is reported
exercised without a cited evidence line.

Both statements are re-confirmed accurate by this review (§2 table, A30.4/A30.6 rows) and
are handed to T-043-51 (memory window) and T-043-52 (CLOSURE) verbatim as quoted above.

---

## 7. Suite, preflight, and doctor evidence (live re-run by this review)

- **`pytest -p no:cacheprovider -m 'not quarantine' -n auto`:** 2582 passed, 3 skipped, 0
  failed, in 51.39s (8 xdist workers). Identical pass/skip/fail counts to T-043-47's own
  cited baseline — expected, since T-043-48 touched only `CHANGELOG.md` (a MUTATING
  documentation path outside `tests/`), so no test-suite delta is expected or found.
- **`tests/integration/test_repo_self_scan.py`** (pre-artifact-write check, per this
  task's own instruction): 5 passed, run before this artifact was written.
- **`dadaia ci preflight`:** 5/5 PASS — `ruff format --check`, `ruff check`,
  `mypy --strict`, `lint-imports`, `pytest`.
- **`dadaia doctor`:** "All invariants OK — workspace is healthy."
- **`dadaia specs doctor --context dadaia-workspace`:** 0 errors, 5 warnings — all 5 are
  pre-existing, unrelated to this segment (memory-atom heading-allowlist WARNs on atoms
  untouched by `alpha-6`; two legacy-named archived release dirs; two archived audits
  naming no disposing release). Same warning count and same warning identities as
  `alpha-5`'s own reviewed baseline — no new warning introduced by this segment.
- **`dadaia public doctor`:** every projection `[ok]`; `public-privacy` `[ok]`;
  `entities-derivation` `[ok]`; `model-resolution` `[ok]`. One pre-existing `[info]`
  advisory (Codex CLI version drift ahead of the last live-certified version) — informational
  only, not a segment finding, unrelated to `alpha-6`'s write set.

---

## 8. Findings

No CRITICAL, HIGH, or MEDIUM findings against this segment's own delta. No LOW findings
requiring intake beyond what T-043-46/T-043-47 already routed and closed within budget
(§6 above). The pre-existing `specs doctor` warnings and the Codex-version `[info]`
advisory are record-only — pre-existing, unrelated to this segment's write set, already
carried at `alpha-5`'s own review, and not actionable within `alpha-6`'s scope.

---

## 9. Disposition

- PLAN §5's `alpha-6` exit criteria are met: FR30 round complete with limits and
  exercised GC capabilities recorded (A30.6); remediation cycle spent (A30.5); FR31
  `[x]`; this `qa-engineer` review committed.
- A30.1–A30.6 and A31.1–A31.4 all PASS, independently re-verified against the live tree
  by this review, not merely re-stated from prior-session prose.
- The A30.4 environment-limits record and the A30.6 GC-coverage statement are carried
  forward verbatim in §6 above for T-043-51 (memory window) and T-043-52 (CLOSURE).
- Bug ledger: 0 open; the segment's one bug closed with a complete pair and re-verified
  RED-then-GREEN regression coverage.
- Worktree clean at every checkpoint of this review.

**Verdict: APPROVED.**
