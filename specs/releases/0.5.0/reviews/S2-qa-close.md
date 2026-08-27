# S2 QA Close — release 0.5.0

**Task:** T-050-22 · **Reviewer:** qa-engineer · **Branch:** `feature/0.5.0` ·
**HEAD reviewed:** `f22dc7bd` (T-050-21A landed as `d33786cb`) · **Reviewed at:**
2026-08-27T15:20Z
**Scope:** T-050-16…T-050-21A (`[x]`) — SPEC A7–A12, A4.5/A4.7, A22.4/A22.10.
**Note:** an `ai-engineer` AI-surface sweep (persona citations + several skill files)
was landing concurrently in the working tree during this review — uncommitted, still
expanding between reads. This report evidences the **committed** state at `f22dc7bd`
(confirmed with `git stash`/`git stash pop` where it matters) and separately notes what
the in-flight sweep does and does not yet fix.

## Verdict: **REQUEST_CHANGES**

S2's design (dd-diagnose split, commit shapes, hook de-slopping, the `behavior-map.json`
canon, the `DADAIA.md`/skill rewrite, `ACTIVE.md` retirement) is sound and mostly
delivered with strong evidence (coverage tables, name-diffs, measured deltas). But the
segment's own acceptance gate — `pytest tests/contract/test_behavior_map.py` green
(V17/A10.2) — is **RED at committed HEAD**, A4.7's "zero-hit grep for `ACTIVE.md`
outside `_archive/`/history" is **not met** (one live dead-path citation, not a
provenance note), and the full suite surfaces **3 additional regressions** introduced by
T-050-21A that were outside its own narrower pre-commit test selection. None of these
are architecturally significant, all are small, but "APPROVE" on a segment whose own
named acceptance test is red would be exactly the kind of "tests green" rubber stamp
`DADAIA.md` §7/FR24 forbids.

---

## 1. Hook posture (A9.1–A9.3, A22.6) — **PASS**

Installed hooks are byte-identical to source (`diff .git/hooks/pre-commit
dadaia_workspace/public/scripts/pre-commit-presence-gate.sh` / same for pre-push: no
diff). Confirmed by reading both scripts end-to-end, not by trusting the diff alone:

- `pre-commit-presence-gate.sh`: `backlog doctor` BLOCK and its fail-closed runner
  resolution are **gone** — unresolved runner now WARNs and the script unconditionally
  `exit 0`s (`"${RUNNER[@]}" || true` then `exit 0`). **Zero blocking exits.**
- `pre-push-ci-gate.sh`: **kept** its fail-closed runner (`exit 1` with a clear message
  when unresolved) and refuses on exactly branch-name + denylist via `ci
  push-gate-check`. **Three fixtures, not two, as the task demanded.**
- `_run_backlog_doctor_gate` / `_staged_backlog_paths`: zero-hit grep across
  `dadaia_workspace/` and `tests/` (two residual mentions are historical comments in
  `tests/integration/test_repo_self_scan.py` and
  `tests/contract/test_hooks_publication_boundary.py`, both naming the deleted symbol as
  the negative case they assert against — not live use).
- `tests/integration/test_precommit_backlog_scoping.py` and
  `tests/e2e/features/test_backlog_precommit.py`: **both confirmed deleted** (A9.3,
  QA-4's pre-committed DELETE verdict executed).
- `PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider -q
  tests/contract/test_hooks_publication_boundary.py`: **3 passed** — the three fixtures
  this task's own done criterion names.

**This confirms exactly one thing added zero blocking exits and removed exactly two**,
matching A9.2/A22.6 to the letter.

## 2. Nine-check name-diff (A10.6) — **content PASS, live-green FAILS (see §4)**

`T-050-19-enforcer-name-diff.md`'s residue check accounts for all 25 old
`test_rules_skills_map.py` functions (1 schema + 6 modes + 6 mode-fixtures + 2 self-tests
+ 7 FR27 + 4 FR28 = 25, zero unaccounted); the two functions with no direct counterpart
(`test_shared_topics_carry_a_justification` and its mutation fixture) are justified as
structurally obviated by the new one-row-per-member schema, not silently dropped. The
five new D14 fixtures are net-new coverage, correctly separated from the port. **As a
table this is correct and complete.** Whether the ported tests actually run green today
is answered in §4 — they do not, for reasons unrelated to the port's correctness.

## 3. `ACTIVE.md` retirement (A4.1/A4.5/A4.7) — **FAIL** (one live dead-path citation)

- `specs/releases/ACTIVE.md` is **deleted** — confirmed, file absent.
- Every "ACTIVE.md" mention remaining in `dadaia_workspace/{hooks,cli,features,core}/**`
  (9 files) is a **docstring/comment provenance note** explaining the retirement
  (`# ACTIVE.md retired (v0.5.0 FR4/T-050-21A, A4.1)`), never a functional read — verified
  by reading each hit in context.
- T-050-21A's own commit message discloses the realised test census (22 files / 83
  occurrences at HEAD, not the SPEC's pre-fold 26/84 estimate — T-050-21's own commit
  already touched some in between) with a per-file disposition: **2 DELETED** (matching
  the SPEC's inspected −3 floor exactly, including the fixture file), the rest
  **REWRITTEN IN PLACE**. `-3` test-function delta confirmed.
- **But**: `tests/contract/test_behavior_map.py::test_every_cited_path_exists` — the
  release's own citation enforcer — reports one **dead path citation** at
  `dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md:43`, citing
  `specs/releases/ACTIVE.md`. Re-read in full: that line is **operative**, not
  historical — "Flip `[ ]`→`[-]`… (pointed at by the RELEASE.jsonl fold, dual-written to
  `<specs_dir>/releases/ACTIVE.md`)". This is not a provenance note; it instructs a
  future reader that the file still exists and is dual-written, which is false as of
  `d33786cb`. Same skill also still says at lines 116/145: "dual-written to
  `<specs_dir>/releases/ACTIVE.md`" / "(dual-written to `ACTIVE.md`'s `segment:` line)".
  This is the same "stale citation" bug class the SPEC itself names as bug-history
  evidence for FR10 (`dadaia-task-manager-stale-workspace-protocol-citation` — the exact
  same file, previously fired for the exact same reason).
- Five persona files (project-manager, code-reviewer, project-auditor, product-engineer,
  ai-engineer) had the same class of stale/operative `ACTIVE.md` text at HEAD;
  `product-engineer.md` in particular instructed "append `phase: PLAN`, dual-write
  `ACTIVE.md`" as a **live action step** in five places, plus a write-permission table row
  granting `specs/releases/ACTIVE.md` as writable. **These five persona files were fixed
  in the working tree during this review** (uncommitted at the time of writing) — but
  `dadaia-task-manager/SKILL.md` and eight further skill files
  (`dadaia-workspace-spec-navigator/SKILL.md`, `dd-release-implement/{SKILL,RC-FLOW,
  RELEASE-EVENTS,MEMORY-UPDATE}.md`, `dd-release-definition/SKILL.md`,
  `dadaia-workspace-spec-reviewer/SKILL.md`, `dd-manager-orchestration/SKILL.md`) still
  carry the stale text as of this review, per T-050-21A's own commit message ("Residual
  ACTIVE.md mentions left for ai-engineer… these are skill-body prose, not this task's
  write set").

**A4.7 requires "a zero-hit grep for `ACTIVE.md` outside `_archive/` and git history…
recorded at the contract step."** That grep is not zero-hit today for reasons that are
not provenance notes. **This is the review's primary blocking finding.** The fix is
small (finish the ai-engineer sweep already in flight across the remaining skill files)
but it is not done, and `dadaia-task-manager/SKILL.md` is the skill every agent —
including this review — loads every session, so the stale citation is live, not
theoretical.

## 4. `test_behavior_map.py` green (V17/A10.2) — **FAIL at committed HEAD**

`git stash` (removing the in-flight ai-engineer sweep) then
`PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider -q tests/contract/test_behavior_map.py`
against pure `f22dc7bd`: **2 failed, 28 passed**.

- `test_every_cited_path_exists` — the dead-path citation from §3, present at HEAD
  independent of the in-flight sweep.
- `test_every_hash_tuple_is_current` — **3** stale `hash_tuple` entries already present
  at HEAD (`dd-release-implement`'s skill + `scaffold/releases/AGENTS.md` scoped hash,
  `dadaia-workspace-spec-navigator`'s skill + `templates/specs-AGENTS.md` scoped hash,
  and the `scaffold/AGENTS.md` scoped hash with no named skill) — meaning the content of
  those files changed after the corresponding row's hash was last recorded, without a
  re-record. Re-running with the working tree restored (in-flight sweep present) shows
  this list only growing (up to 9 stale rows across the run), because the sweep is
  actively editing those same files without yet re-recording their hashes — expected of
  unfinished work, but it means **A10.4's "deliberate re-recording obligation"** is not
  yet discharged either.
- The other **28 of 30** checks pass, including both of D14's cardinality directions
  (`test_no_member_maps_to_two_sections`, `test_every_law_section_has_an_owner` — **A10.1
  confirmed**) and all five new D14 mutation fixtures.

**V17's stated acceptance is "`pytest tests/contract/test_behavior_map.py` green."** It
is not, at the reviewed HEAD. The map/schema/enforcer design is correct (§2); the failure
is entirely citation/hash bookkeeping left behind by T-050-21/T-050-21A's own writes, not
a defect in the enforcer or the map shape.

## 5. V11 / V12 — AI-surface and always-on token deltas

**V12 (always-on tokens, ceiling ≤ 22,011):** re-verified against
`T-050-20-v12.md`. Highest harness (kimi-code) AFTER = **21,093.8 ≤ 22,011** —
**PASS**, 917.2 tokens headroom. Per-section attribution sums to 278.0 of a measured
283.2–283.3 whole-file delta (≈5-token residue is unbudgeted word-for-word citation
swaps, explicitly named, not hidden). `grep -n "ACTIVE.md"
dadaia_workspace/public/data/DADAIA.md` — confirmed zero hits directly (not just via the
task's own report). Tier-1 single-writer property (A11.1) holds: exactly one task
(T-050-20) names `DADAIA.md` in a write-set block.

**V11 (AI-surface line count, `public/{agents,skills,data,entities}/**`):**
`T-050-21-v11.md` reports baseline 7,930 → 8,474 at T-050-21 (**whole-segment delta
+544**). FR7+FR11+FR12 scoped sum (A22.4's actual textual scope) = **+178 (FR7) + 26
(FR11) − 1 (FR12) = +203**.

**A12.5, read literally ("AI-surface LOC net for `S2` is negative… measured"), FAILS
under every reading measured so far:**
- Whole-segment S2 total: **+544** (positive).
- The narrower FR7+FR11+FR12 scope A22.4 actually names: **+203** (still positive).
- Only FR12 in isolation (T-050-21's own diff, `git diff --shortstat b4ae686b`) is
  negative: **−1**.

The T-050-21 coverage table's own cross-reference resolves A12.5 by silently narrowing
its subject to "FR12's own net," which is the one number that is actually negative — but
that is a **different claim** than the acceptance text as written ("AI-surface LOC net
for `S2`"). This is exactly the class of risk this same task's own description warns
about — "a law relocated into nothing" — inverted: here an acceptance criterion's literal
scope is quietly narrowed at evidence time rather than at spec-authoring time. The
reasoning for *why* +203/+544 is honest and unavoidable (FR7 and FR11 sit outside FR12's
write authority per Tier-1 single-writer and T-050-16's own closed task boundary) is
sound and well-argued — but that is an argument for **amending A12.5's wording** (the
same way A22.9 explicitly names and accepts a declared test-count overshoot with an
operator sign-off), not for reading the current text as satisfied. **Recorded here as
required; disposition (reword A12.5, or have the operator sign an explicit accepted
overshoot the way A22.9 does) is a `product-engineer`/operator decision, not a QA
verdict I can substitute.**

## 6. D14 cardinality (A10.1) — **PASS**

Confirmed via the live enforcer (§4, 28/30 green including both cardinality checks):
every skill and every scoped `AGENTS.md` on disk maps to exactly one row (no
double-mapping), and every `DADAIA.md` `## N. Title` section has at least one owning row
(zero-owner sections would fire `test_every_law_section_has_an_owner`, which passes).

## 7. Zero new `tests/e2e/**` files — **PASS**

`git diff --diff-filter=A --name-only 7de7c48c..HEAD -- tests/e2e/` (S1-close commit to
HEAD): **empty**. No exception needed.

## 8. Full suite (once) — 10 failed / 2,948 passed / 4 skipped

`PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider -q -n auto tests`:

| Failure | Classification |
|---|---|
| `test_tree5_shipped_history.py::test_shipped_history_records_the_current_canonical_template` | **Pre-existing**, disclosed by T-050-21A's own commit message, caused by the already-landed T-050-23/25 findings-store rewrite of `doctor_closure_audit.py` — out of this segment's scope, tracked for T-050-25A. |
| `test_doctor_taxonomy_disposition.py::test_silent_and_exempt_matrix[doc036-with-disposition-clean]` | Same as above (disclosed pre-existing). |
| `test_doctor_taxonomy_disposition.py::test_sad_path_matrix[doc038-single-loose-audit]` | Same as above (disclosed pre-existing). |
| `test_doctor_taxonomy_disposition.py::test_sad_path_matrix[doc038-multiple-loose-audits]` | Same as above (disclosed pre-existing) — these 4 exactly match T-050-21A's own disclosed "4 failed, all pre-existing" count. |
| `test_behavior_map.py::test_every_cited_path_exists` | **New, this segment (§3/§4)** — dead `ACTIVE.md` citation, `dadaia-task-manager/SKILL.md:43`. |
| `test_behavior_map.py::test_every_hash_tuple_is_current` | **New, this segment (§4)** — stale hash tuples, present at committed HEAD, growing under the in-flight sweep. |
| `test_ruff_format_repo_tree_green.py::test_ruff_format_check_is_green_over_the_real_tracked_tree` | **New regression, T-050-21A.** `dadaia_workspace/cli/commands/specs.py:404` needs `ruff format`. Not caught by T-050-21A's own narrower pre-commit selector (which never ran the whole-tree ruff-format contract test). Blocks `DADAIA.md` §7's "push green" preflight today. |
| `test_cli_reports_next.py::test_next_json_text_all_completed_no_active_release_and_plan_without_owners` | **New regression, T-050-21A.** This test lives at `tests/integration/test_cli_reports_next.py` — inside the 26/22-file `ACTIVE.md` census, but **outside** T-050-21A's own narrower dry-run selector (`tests/integration/cli`, not `tests/integration/`). Its fixture was not repointed to write a `RELEASE.jsonl`; `reports next` now correctly refuses ("No active release: no directory under releases/ carries a RELEASE.jsonl") but the test still asserts the old success path. Test-side staleness, not a production defect — the CLI's refusal is the *correct* new behavior. |
| `test_one_place_of_control_associated_repo.py::test_gate_memory_write_inside_associated_repo_is_governed_by_the_main_repos_phase` | **New regression, T-050-21A.** Also outside the narrower dry-run selector. The fixture still seeds phase state the new resolver does not read, so the MAIN repo's phase folds to **empty string** instead of the fixture's intended `IMPLEMENTATION`. `RULE A` still blocks (fails closed on empty phase, so there is no live security regression), but the test's actual assertion — that the block cites the *correct* resolved phase — is unproven. The census disposition for this file ("rewritten in place") is incomplete in substance. |

Two further failures share the same root cause as the row above:
`test_classifier_symlink_canonicalization.py::test_symlink_into_in_repo_memory_classifies_memory_block_and_definition_allows`
also resolves an empty phase from a fixture not yet repointed to `RELEASE.jsonl`,
observed in the `-n auto` run (see the raw pytest transcript captured for this review).

**Net: 4 pre-existing (disclosed, out of scope) + 2 §3/§4 findings (already detailed
above) + 3 previously-undisclosed T-050-21A regressions, all census-adjacent and all
outside T-050-21A's own narrower test selection.** None indicate a security or
architectural regression — the gate fails closed in every case — but three census files
this segment claimed as "rewritten in place" are not actually correct yet, and A4.7's own
acceptance ("a zero-hit grep… recorded at the contract step") cannot be signed off while
the citation and the two associated-repo/symlink fixtures remain wrong.

## 9. Bug-surface delta

**Hook feature, specifically (FR9):** net **negative**. The bug that motivated FR9 —
`precommit-backlog-doctor-blocks-unrelated-commits` — is **resolved**
(`dadaia bugs status` confirms it is not in the open list). Zero new hook bugs were
registered against pre-commit/pre-push this segment. Two blocking mechanisms removed,
zero replacements, matching the SPEC's own "net-negative, unambiguously, −≈60 LOC"
claim (§1 above independently confirms the mechanism).

**Concurrency / git-index, release-wide (not caused by S2, but surfaced across it):**
`dadaia bugs status` lists **5 open** bugs; three carry the "shared git index across
concurrent sessions" shape this release's own multi-agent parallelism produces:
- `concurrent-sessions-share-git-index-commit-boundary-contamination` — **open**, MEDIUM.
- `concurrent-agent-git-add-clobbers-other-sessions-staged-files-into-unrelated-commit`
  — **open**, MEDIUM.
- `mutation-baseline-wiring-test-flakes-under-concurrent-additive-writes` — **resolved**
  this release (same class: a test flaking when a concurrent live session writes ADDITIVE
  content during the test window).

The other two open bugs are unrelated to S2's own scope:
`backlog-cli-help-cites-retired-ledger-and-bl-dup` (LOW) and
`bug-record-write-once-evidence-fields-can-embed-selfscan-triggering-literal-with-no-correction-path`
(MEDIUM), plus `windows-xdist-workers-crash-on-unit-fast-tier` (LOW, cross-platform,
pre-existing).

## 10. Security/privacy leakage note

No credentials, tokens, hostnames, IPs, or consumer-specific slugs appear in any file
touched or read for this review. `dadaia bugs stats` and the census/coverage tables were
read, not authored, and nothing in them required redaction on transcription into this
report. No new CLI verb, no new hook block, no new dependency was introduced by S2 (A9.5,
A7.5, A10.5 all independently confirmed above) — no elevated attack surface. Not escalated
to `security-reviewer`; no suspected leakage found.

---

## Required before S2 can close (APPROVE)

1. Finish the in-flight `ai-engineer` AI-surface sweep across the remaining skill files
   named in T-050-21A's own commit message (`dadaia-task-manager/SKILL.md` above all —
   it is the dead-path citation `test_every_cited_path_exists` fails on), and
   re-record the now-stale hash tuples (`test_every_hash_tuple_is_current`). Commit it.
2. `ruff format dadaia_workspace/cli/commands/specs.py` (one file, one function) and
   commit.
3. Repoint `test_cli_reports_next.py`'s and
   `test_one_place_of_control_associated_repo.py`'s / the symlink-classifier test's
   fixtures to write a real `RELEASE.jsonl` instead of the pre-fold state they still
   seed, so their assertions test what they claim to test again.
4. `product-engineer`/operator disposition on A12.5's literal wording vs. the honestly
   reported +203/+544 AI-surface deltas (§5) — either reword the acceptance criterion to
   match A22.4's per-FR framing, or record an explicit accepted-overshoot ruling the way
   A22.9 already does for the test-function count.

None of these are large — items 1–3 are mechanical, already half-done in the working
tree at review time. Re-run this review once they land; `dadaia-task-manager`'s own
staleness (item 1) directly touches every agent's session, so it is the one to close
first.

## Evidence commands (reproducible)

```bash
diff .git/hooks/pre-commit dadaia_workspace/public/scripts/pre-commit-presence-gate.sh
diff .git/hooks/pre-push dadaia_workspace/public/scripts/pre-push-ci-gate.sh
PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider -q tests/contract/test_hooks_publication_boundary.py
PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider -q tests/contract/test_behavior_map.py
grep -rn "ACTIVE\.md" dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md
git diff --diff-filter=A --name-only 7de7c48c..HEAD -- tests/e2e/
dadaia bugs status
PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider -q -n auto tests
```
