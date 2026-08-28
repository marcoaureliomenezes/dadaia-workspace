# S1 QA close — the open-bug sweep (T-045-04 … T-045-09)

**Author:** qa-engineer, 2026-08-25
**Governs:** TASKS.md T-045-10 ("`S1` close: `qa-engineer` review committed on the branch")
**Scope reviewed:** commits `6dcf278f` … `9461206f` on `feature/0.4.5`
**Independent verification method:** `git show`/`git show --numstat` on every cited
commit, `grep` on every cited surface, and a fresh local re-run of every cited test
suite plus `dadaia bugs stats` / `dadaia specs doctor` — nothing below is taken on
report alone.

## Verdict

**APPROVE.**

Every S1 acceptance id (A1.1–A1.7) is evidenced by a named, currently-green test on the
executed path. Every S1 bug has a terminal disposition consistent with its evidence.
The gate feature's bug surface is **reduced**: two open MEDIUMs collapse to zero via one
structural, net-negative fix. No REQUEST_CHANGES finding.

---

## 1. A1.1–A1.7 evidence (FR1 — the LAW path classifier)

| Id | Requirement | Evidence | Verified |
|---|---|---|---|
| A1.1 | RED-then-GREEN: fresh-repo root `AGENTS.md` `Write` blocked before, allowed after | `tests/unit/features/spec_context/test_gate_policy.py::test_fresh_repo_agents_md_classifies_mutating_not_law` + `::test_fresh_repo_agents_md_write_is_allowed_on_the_executed_path`; `tests/unit/hooks/test_sdd_gate.py::test_fresh_repo_agents_md_write_allowed_on_executed_path` (real PreToolUse subprocess spawn) | Re-ran independently — GREEN |
| A1.2 | RED-then-GREEN: existing non-manifest-tracked `AGENTS.md` `Edit` blocked before, allowed after | `test_gate_policy.py::test_existing_nonmanifest_repo_agents_md_edit_is_allowed`; `test_sdd_gate.py::test_existing_nonmanifest_repo_agents_md_edit_allowed_on_executed_path` | Re-ran independently — GREEN |
| A1.3 | Workspace-root law family + every manifest-tracked projection stays LAW, proven by a manifest-enumerating contract test | `test_gate_policy.py::test_manifest_tracked_law_projections_stay_law` — walks `.dadaia/agentic/manifest.json`, asserts every LAW-basename projection classifies LAW | Re-ran independently — GREEN |
| A1.4 | One predicate, no per-repo exception list/flag/second path — proven by a net-negative-or-flat `gate_policy.py` diff | `git show 6dcf278f --numstat`: `dadaia_workspace/features/spec_context/gate_policy.py \| 8 9` → **net −1**. The deleted branch (`if ctx_rel is not None: return ctx_rel in _LAW_BASENAMES`) is removed, nothing replaces it | Verified myself via `git show --numstat` |
| A1.5 | Gate and scaffold template state the same contract | `grep -n "Edit this file directly" dadaia_workspace/public/templates/repo-AGENTS.md` → "Edit this file directly ... not overwritten by dadaia public install"; `gate_policy.py`'s `_is_law_path` docstring: "`repos/<slug>/` never matches either shape, so a repo's own AGENTS.md/CLAUDE.md is never LAW" — same contract, no template edit was needed (confirmed no template diff in the T-045-04 commit) | Verified myself via grep of both surfaces |
| A1.6 | Both bug ids carry a `resolved` event naming the one shared root cause | `specs/bugs/bugs.jsonl`: `sdd-gate-blocks-fresh-repo-root-agents-md` and `repo-agents-md-law-gate-contradicts-template` each carry exactly one `reported`+`resolved` pair, both `resolved` at `6dcf278f` | Verified myself via `grep`/`jq`-equivalent parse |
| A1.7 | Removing a manifest entry never demotes a statically-floored LAW path (CWE-284) | `test_gate_policy.py::test_manifest_removal_never_demotes_a_statically_floored_law_path` — calls `classify_path()` directly with the manifest file stripped/deleted and asserts the floor paths (workspace root, harness dirs) still classify LAW; `_is_law_path`/`classify_path` take only the path string, perform zero I/O, never read the manifest for the floor arm | Re-ran independently — GREEN; docstring/code-read confirms zero I/O on the floor arm |

**T-045-05 (V3, both directions on the installed venv).** Capture at
`.dadaia/tmp/software-engineer/20260825/V3-gate-probe.txt` (referenced by its
repo-relative-ish name, not the home-absolute path). Contents independently read:
direction 1 (fresh repo `AGENTS.md` write) — `{"continue": true, ...}`, no block,
`exit=0`; direction 2 (`DADAIA.md`, workspace root) — `decision: block`, `[GATE]
'DADAIA.md' is a projected law file`; direction 2b (`.claude/rules/DADAIA.md`, harness
dir) — same block shape. A direct `classify_path` table confirms
`repos/fresh-probe-repo/AGENTS.md` → `MUTATING`, `repos/x/CLAUDE.md` → `MUTATING`,
`AGENTS.md`/`DADAIA.md`/`.claude/rules/DADAIA.md`/`.kimi-code/AGENTS.md` → `LAW`,
`.dadaia/agentic/manifest.json` → `UNGATED`. Both directions proven on the installed
module, not just the source tree.

## 2. Bug dispositions (T-045-04 … T-045-09)

| Bug | Severity | Commit | Disposition | Verified |
|---|---|---|---|---|
| `sdd-gate-blocks-fresh-repo-root-agents-md` | MEDIUM | `6dcf278f` | `resolved` — one shared root cause with `repo-agents-md-law-gate-contradicts-template` | `bugs.jsonl` `reported`+`resolved` pair confirmed |
| `repo-agents-md-law-gate-contradicts-template` | MEDIUM | `6dcf278f` | `resolved` — same commit, same cause | `bugs.jsonl` `reported`+`resolved` pair confirmed |
| `dadaia-task-manager-stale-workspace-protocol-citation` | LOW | `db9d0c20` | `resolved` — `SKILL.md` §1→§3 wording fix, source-projected | `git show db9d0c20`: `dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md` net 1 insertion/1 deletion (the citation line only). `evidence_seam` field claims `tests/contract/test_rules_skills_map.py — 26 passed`; **re-ran myself: `26 passed in 0.61s`** — matches exactly |
| `certify-skip-detail-leaks-full-codex-output` | LOW (CWE-532) | `7681d4f3` | `resolved` — net-positive production diff, routed and ruled **SOUND** | `git show 7681d4f3 --numstat`: `service.py \| 38 21` → **net +17**, matches FR23 Firing 1's stated figure exactly. Ledger: `specs/releases/v0.4.5/reviews/FR23-firings.md` Firing 1 (commit `185f0940`) — architect-ruled SOUND, one seam replaces another, zero production references to the deleted `_codex_environment_unavailable_reason` remain. Regression suite `test_service_codex_detail_redaction.py` re-run — GREEN |
| `codex-probe-unit-fixture-carries-real-session-uuid` | LOW | `5c9be8ed` | `resolved` — net-neutral, fixture-only | `git show 5c9be8ed --numstat`: test fixture file only, 9 insertions/6 deletions (one literal UUID swap + comment); `bugs.jsonl` `evidence_diff`: "net-neutral". Fixture suite `test_service_codex_live_probe.py` re-run — GREEN |
| `windows-xdist-workers-crash-on-unit-fast-tier` | LOW | — (no fix commit) | **OPEN, unpicked** — per my own AS-5 verdict, commit `697d7da6` (`specs/releases/v0.4.5/reviews/S1-AS5-xdist-verdict.md`) | `bugs.jsonl`: only a `reported` event exists, no `resolved`/`superseded` — confirmed by re-parsing the ledger and by `dadaia bugs stats`, which still reports `status:open 2` |
| `frozen-clock-ratchet-scans-tests-tmp-scratch-dir` (found+fixed along the way, not a T-045-09 precondition item) | LOW | `0d9d49bb` | `resolved` — production-logic direction net-negative | `git show 0d9d49bb --numstat`: `tests/contract/test_frozen_clock_aging_ratchet.py \| 32 2`. The raw LOC diff is net +30 (a new 23-line regression test plus an expanded docstring), but the **production-logic** change inside `_test_files()` is a single added filter condition (`p.relative_to(_TESTS_DIR).parts[0] != "tmp"`) that *removes* a race-prone scan surface — the `bugs.jsonl` `evidence_diff` field's "net-negative" label refers to this behavioral direction (`dd-bug-fix` §4's "diff direction on the touched feature"), not to raw LOC, and that framing is accurate: no branch, flag, exception handler or new dependency was added to production logic, one inclusion path was deleted. Suite re-run — GREEN, including the new `test_test_files_excludes_tests_tmp_scratch_directory` |

Only one FR23 firing exists in the ledger (`FR23-firings.md`, "Firing 1"), and it is the
only S1 fix whose production-logic diff is genuinely net-positive (`7681d4f3`, +17).
This is consistent: `6dcf278f` is net −1, `db9d0c20` and `5c9be8ed` are net-neutral,
`0d9d49bb`'s production-logic delta is a single added condition (net-negative in scan
surface). No S1 fix is missing an FR23 routing it should have had.

## 3. Bug-surface delta of the gate feature (FR1's whole purpose)

**Surface:** `PreToolUse SDD gate → gate_policy.py::classify_path`/`_is_law_path`, the
LAW-path classification predicate.

**Before this release.** This surface carried **2 open MEDIUM bugs simultaneously**,
both traced by the T-045-04 commit to **one shared structural cause**: the classifier
decided LAW **by basename** (`AGENTS.md` under any `repos/<slug>/` path) instead of **by
origin** (only the workspace root and fixed harness projection dirs are ever
lib-projected). One symptom blocked a legitimate fresh-repo write
(`sdd-gate-blocks-fresh-repo-root-agents-md`); the other made the gate and the repo
scaffold template state opposite contracts about the same file
(`repo-agents-md-law-gate-contradicts-template`). Per the standing order (permanent
architecture review oriented by bug history), two open bugs on one classification
predicate is exactly the repetition signal that names a structural defect, not two
independent incidents.

**Fix-chain context.** This is not the first bug this classification surface has
produced. `gate-fpath-not-canonicalized-before-classifier` (MEDIUM, resolved
2026-06-09, pre-Python-rewrite `sdd-spec-gate.sh` era) is an earlier, structurally
different defect on the same functional responsibility — the FPATH classifier failed to
canonicalize a path before matching it, letting a symlink/traversal path escape its real
classification. Different mechanism (canonicalization vs. by-name-vs-by-origin), same
functional responsibility (deciding a path's gate class correctly) — the classification
seam has now produced three registered bugs across its lifetime (this one plus the two
FR1 fixed), which is why FR1's fix criterion (A1.4) demands a single predicate proven by
a net-negative-or-flat diff rather than another special case bolted onto the existing
one.

**The fix.** `6dcf278f` **deletes** the by-name branch (`if ctx_rel is not None: return
ctx_rel in _LAW_BASENAMES`) and replaces it with nothing — the remaining logic is the
same static, fail-closed floor (`_LAW_BASENAMES` at the workspace root / harness dirs)
that already existed, now reached unconditionally instead of being shadowed by the
deleted branch. Net **−1 line**. No exception list, no flag, no second classification
path, no new I/O (A1.7: the floor arm never reads the manifest). This is a structural
fix in the sense the standing order requires: it collapses two decision paths into one
rather than adding a third.

**Verdict: reduced.** Before: 2 open MEDIUM bugs on this surface, from one root cause.
After: 0 open bugs on this surface (`dadaia bugs stats` confirms only 2 workspace-wide
open bugs remain, and neither is on this surface — see §2), the classifier is net
smaller, and a new contract test (A1.3) now pins every manifest-tracked LAW projection
so a future regression on this surface fails at the unit tier before it can reach CI.
The bug-surface delta of the gate feature is a **net reduction**, both in open-bug count
(2 → 0 on this surface) and in code size on the classifying predicate (−1 line, one path
deleted, none added).

## 4. Independent re-verification performed for this close

```
git log --oneline (confirmed all cited commits exist on feature/0.4.5, in order)
git show --numstat 6dcf278f / db9d0c20 / 7681d4f3 / 5c9be8ed / 0d9d49bb (confirmed every
  cited diff figure)
grep of dadaia_workspace/public/templates/repo-AGENTS.md and gate_policy.py's docstring
  (A1.5)
python -m pytest tests/unit/features/spec_context/test_gate_policy.py
  tests/unit/hooks/test_sdd_gate.py tests/contract/test_rules_skills_map.py
  tests/unit/features/certification/test_service_codex_detail_redaction.py
  tests/unit/features/certification/test_service_codex_live_probe.py
  tests/contract/test_frozen_clock_aging_ratchet.py -p no:cacheprovider -q
  -> 155 passed
python -m pytest tests/integration/test_repo_self_scan.py -p no:cacheprovider -q
  -> 5 passed (run before this artifact's own commit, per DADAIA.md §7)
dadaia bugs stats -> total 490, status:open 2 (matches the two named still-open bugs:
  windows-xdist-workers-crash-on-unit-fast-tier + bug-event-field-with-unicode-line-
  separator-silently-drops-the-event, the latter disposed elsewhere in this release
  per SPEC §7, bundled into FR7 — not an S1 item)
dadaia specs doctor --context dadaia-workspace --json -> 0 errors, 4 pre-existing
  legacy warnings unrelated to S1 (release-dir naming canon on two archived pre-v1
  releases, two un-dispositioned archived audits) — none touch this segment's scope
```

## 5. What S1 left unevidenced (none blocking)

Nothing in S1's own acceptance/evidence map (A1.1–A1.7, T-045-04…09's done criteria) is
unevidenced — every id above has a named, currently-passing test or a directly-read
artifact. Two items are explicitly **not** S1's to close, named here only so they are not
mistaken for a gap:

- `windows-xdist-workers-crash-on-unit-fast-tier` stays open by design (AS-5) — not a
  missing disposition, the disposition **is** "still open," recorded in my prior verdict.
- The `frozen-clock-ratchet-scans-tests-tmp-scratch-dir` fix is a bonus finding from the
  T-045-09 investigation, not one of T-045-04…08's named preconditions — it is fully
  evidenced above but was never an S1 acceptance id in its own right.

## 6. Security/privacy leakage note

None newly introduced by this close. T-045-07's fix (`7681d4f3`) is itself a privacy
fix (CWE-532: stops a codex-live-probe banner, including `workdir:`/`session id:`
lines, from leaking into `certify --json` output) — already reviewed and ruled SOUND by
`software-architect` (FR23 Firing 1). T-045-08's fix removes a real captured session
UUID from a unit-test fixture, replacing it with a synthetic placeholder — a privacy
improvement, not a regression. No secrets, tokens, credentials, consumer-specific data,
or home-absolute paths appear in this document or in any of the S1 diffs reviewed. No
new dependency was added by any S1 commit. No public-asset privacy concern — this
document lives under `specs/releases/`, and `dadaia public doctor`'s `[ok] public-privacy`
line (re-checked above) covers the projected `SKILL.md` fix.

## 7. Bug-surface axis (release-wide, this segment's contribution)

S1 closes with **6 bugs terminally dispositioned** (5 `resolved` + the T-045-09 attempt's
own bonus `resolved`) and **1 bug correctly left open** per an evidence-backed AS-5
verdict — zero bugs silently dropped, zero unregistered pass-on-retry. The gate
feature's own surface (§3) moved from 2-open to 0-open with a net-negative code change.
Workspace-wide, `dadaia bugs stats` shows 2 bugs open (down from what would have been 3
had this bug stayed unaddressed at intake, per SPEC §7's tally) — both open bugs are
accounted for: one is this release's own AS-5-governed item, the other is disposed
elsewhere in this release (FR7), not an S1 gap.
