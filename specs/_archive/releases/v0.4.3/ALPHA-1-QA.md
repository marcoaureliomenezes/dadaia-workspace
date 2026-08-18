# ALPHA-1-QA.md — `alpha-1` (WS-D, the AI surface) segment QA gate

**Task:** T-043-12 · **Reviewer:** qa-engineer · **First reviewed at commit:**
`ed94f5b0` · **Re-verified at commit:** `b7ad9123` (branch `feature/0.4.3`) ·
**Reviewed:** 2026-08-17

**Verdict: APPROVED**

The first pass (below, §0-§6 as originally written) found one actionable defect
blocking the segment's own PLAN §5 exit criterion ("V9 all `[ok]`"). `ai-engineer`
remediated it (handoff `2026-08-17T154703Z…reprojection-fix`, commit `b7ad9123`); §0
records this reviewer's independent re-verification of that fix. All eight FRs'
acceptance ids were verified on the executed path in the first pass and are unaffected
by the fix (whitespace-only re-projection, no logic or FR-substance change).

---

## 0. Re-verification (2026-08-17, commit `b7ad9123`)

- **Tip since first review:** `git log --oneline 97b825a4..HEAD` shows exactly one
  commit, `b7ad9123` ("chore(T-043-11): re-project the reformatted alpha-1 lint
  scripts") — a docs-only change to `specs/releases/v0.4.3/TASKS.md`'s T-043-11
  evidence line (the actual projection re-sync writes `.dadaia/agentic/**` and the
  workspace-root projected trees, none of which are tracked inside this repo's git).
  No other file changed; nothing outside the claimed fix landed on the branch.
- **`dadaia public doctor` (run independently by this reviewer, not taken on faith):**
  exit `0`; `183` `[ok]`, `0` `[error]`, `0` `[warn]`, `0` `[drift]` — matching
  T-043-11's original V9 capture exactly. `[ok] stage:scripts/lint-dadaia-cli-
  reachability.py`, `[ok] stage:scripts/lint-skill-collisions.py`, and their
  `dadaia:scripts/` counterparts confirmed `[ok]`; `[ok] public-privacy` present.
- **Byte-verification (independently re-run):** `cmp` of both scripts' source
  (`dadaia_workspace/public/scripts/*.py`) against both `.dadaia/agentic/scripts/*.py`
  and `.dadaia/scripts/*.py` — all four comparisons report identical bytes.
- **Self-tests (independently re-run):** both `lint-dadaia-cli-reachability.py
  --self-test` and `lint-skill-collisions.py --self-test` exit `0`, all branches PASS
  — confirms the `ruff format` + `SIM110` fix in `ed94f5b0` was behavior-preserving.
- **§1's blocking finding is resolved.** PLAN §5's `alpha-1` exit criterion ("one
  projection cycle run; V9 all `[ok]`") now holds at `b7ad9123`.
- **No new actionable or record-only finding** surfaced by this re-verification pass.

**Everything below this line is the original first-pass review, unedited, for the
audit trail.**

---

## 1. The blocking finding

**Projection drift reintroduced after T-043-11's clean V9 capture.**

- **Reproduction:** `.dadaia/.venv/bin/dadaia public doctor` at `ed94f5b0` (current
  tip) exits `1` and reports:
  ```
  [drift] stage:scripts/lint-dadaia-cli-reachability.py
  [drift] stage:scripts/lint-skill-collisions.py
  ```
  181 `[ok]` (down from T-043-11's captured 183), 2 `[drift]`, 0 `[error]`.
- **Expected:** PLAN §5's `alpha-1` exit criterion reads "one projection cycle run; V9
  all `[ok]`". T-043-11 (`e9b3434a`) captured exactly that: 183 `[ok]`, 0 `[error]`,
  0 `[warn]`.
- **Root cause:** the tip commit `ed94f5b0` ("style(alpha-1): format the two new lint
  scripts") ran `ruff format` + one manual `SIM110` fix on
  `public/scripts/lint-dadaia-cli-reachability.py` and
  `public/scripts/lint-skill-collisions.py` **after** T-043-11's projection cycle
  (`e9b3434a`) and **without** re-running `dadaia public stage && dadaia public
  install --target all`. The staged/projected copies of those two files therefore
  still carry the pre-format bytes; `public doctor` correctly flags the byte
  mismatch — the tool is working as designed (not a product bug; classify-first
  table: "a validation the tool is designed to emit").
  Confirmed by diff: the drift is exactly `ruff format`'s whitespace changes (list
  comprehension line-wrap, multi-line `print()` calls) — no logic change, both
  scripts' `--self-test` still pass at either byte version.
- **Not caused by, and does not implicate:** any of FR1–FR8's substance, the goldens
  regen (§3 below, which ran *before* `ed94f5b0` and is scoped correctly), or
  T-043-10/FR8.
- **Severity:** MEDIUM — blocks the segment's stated exit criterion; trivially
  resolved (one projection cycle: `dadaia public stage && dadaia public install
  --target all && dadaia public doctor`, then a commit), no data loss, no security
  surface, no behavioral regression in the two scripts themselves.
- **Fix recommendation:** `ai-engineer` (or `software-engineer` under the
  ai-engineer-owns-projected-assets lane rule) re-runs the projection cycle and
  commits the refreshed `.claude/`/`.codex/`/`.kimi-code/`/`.agents/` trees plus
  `.dadaia/agentic/**` staging, then re-captures V9. This QA gate does not write to
  those paths itself (write allowlist excludes lib-originated projected assets).
- **Not registered as a bug** — per the classify-first table, `public doctor`
  correctly emitting a validation it is designed to emit is not a product-bug
  contract violation; it is a release-process gap (a commit landed without its
  mandatory follow-up cycle), routed here as an actionable QA finding instead.

---

## 2. Per-FR acceptance verification (executed-path evidence)

| FR | Acceptance ids | Verified? | Evidence |
|---|---|---|---|
| FR1 — pinned installs | A1.1, A1.2, A1.4 | **Verified** | All 5 prescribed installs pinned exactly (`vulture==2.14`, `ts-prune@0.10.3`, `knip@5.36.3`, `depcheck@1.4.7`, `pydeps==3.0.1`); pinning rule stated once at `dd-audit-project/SKILL.md:103-105`, worded to cover "this skill or any quality tooling"; tree-wide grep found only two other `pip install`/`npx` hits, both out of FR1's third-party-tool scope (`dadaia-workspace-manager`'s self-editable `pip install -e dadaia-workspace/` and a placeholder wheel path in `CONSUMER_VALIDATION_RECIPE.md`). A1.3 (memory doctrine line) is explicitly deferred to the `rc-1` memory window per T-043-03's own done criterion — correctly unverified now. |
| FR2 — duplicate `dd-` claims | A2.1–A2.4 | **Verified** | `dd-backlog-definition` narrowed to `specs/backlog/**`, `dd-release-definition` to `specs/releases/*/SPEC.md`; `dd-bug-registration` to `specs/bugs/*.jsonl`, `dd-bug-fix` stays `specs/bugs/**` (declared narrower/broader pair). Precedence rule + declared-overlaps table present at `dd-backlog-definition/SKILL.md:139-150`. `lint-skill-collisions.py`: green (`exit 0`, "No undeclared applyTo overlap"); `--self-test` both branches pass (universal-glob silent; undeclared duplicate fires). |
| FR3 — pointer loop | A3.1, A3.2 | **Verified** | `dd-release-definition/SKILL.md` no longer references `project-orchestration` at all (grep: 0 hits); only `project-orchestration` and `dd-backlog-definition` still mention it, and neither pair is mutual-reference-only. |
| FR4 — redaction sentence | A4.1–A4.3 | **Verified** | Exactly one new sentence at `DADAIA.md:235-236` ("Absolute local paths, IPs, hostnames, private names and secrets never enter an event field."); appears exactly once across `public/`; `dd-bug-registration/SKILL.md` §3 unedited since T-043-04. Byte-identity confirmed: workspace-root `DADAIA.md`, `.claude/rules/`, `.codex/`, `.kimi-code/` all sha256 `eb5a30f5…` = source `public/data/DADAIA.md`. |
| FR5 — `dadaia-cli` grant/description | A5.1–A5.3 | **Verified** | Exactly the 7 shell-capable agents (`ai-engineer`, `code-reviewer`, `project-auditor`, `project-manager`, `qa-engineer`, `security-reviewer`, `software-engineer`) carry the grant; `product-engineer`/`software-architect` (no `Bash` in `tools:`) do not. `lint-dadaia-cli-reachability.py`: green (exit 0, "Every agent's dadaia-cli grant agrees with its Bash-capability"); `--self-test` proves both drift directions (missing grant on Bash agent; inert grant on shell-less agent). |
| FR6 — reconciliation-merge mechanic | A6.1, A6.2 | **Verified** | `dadaia-gitflow/SKILL.md:57-63` states the mechanic and the resurrected-copy resolution rule, citing v0.4.2's `84a66d13` as the worked example; the statement exists exactly once across `public/`. |
| FR7 — stewardship homonym note | A7.1, A7.2 | **Verified** | `dadaia-test-stewardship/SKILL.md:17-24` names all three homonyms (`scaffold`, `sentinel`, `quarantine`) and their unrelated homes. A7.2: `TASKS.md:591` (T-043-24's own description) already cites the note as an input — the citation exists in the task's authored text; T-043-24 itself is `alpha-3` scope and has not executed yet (correctly out of scope here). |
| FR8 — `AGENTS-PLACEHOLDER-1` | A8.1–A8.3 | **Verified** | 6 new tests in `test_scaffold_placeholder_repair.py` (module section `Intent: CONTRACT — asserts SPEC.md FR8 / A8.1-A8.3` at :162-166) all pass: warns on an unfilled installed `tests/AGENTS.md` (A8.1), silent on a filled one (A8.3) and when absent, silent on the canonical template (A8.2), and — the dedicated false-positive guard — silent on the template's own `` `Intent: <KIND> — <AC id \| ...>` `` docstring-syntax example (tight single-backtick-span match, never a bare `<[A-Z_]+>` scan). `dadaia specs doctor --context dadaia-workspace` on this repo's own filled `tests/AGENTS.md`: 0 errors, 5 pre-existing warnings (LINT-1 headings + legacy archive-naming, none FR8-related, all correctly deferred to T-043-17/T-043-51). **Minor discrepancy (record-only):** the commit message and the SE handoff both state "7 new tests"; the diff shows 6 new `test_*` functions (plus 2 helper functions) — a metrics-count slip, not a coverage gap. |

**A32.2 (this segment's slice of "projection cycle evidence"): NOT currently held** —
see §1. T-043-11's own capture (183/0/0) was correct *at that commit*; it does not
survive the later `ed94f5b0` commit.

---

## 3. In-segment Arm-B rider evidence

Only one bug was registered and resolved inside `alpha-1`'s timeframe:
`install-target-doctor-goldens-stale-after-v043-skill-additions` (MEDIUM, reported
`15:28:50Z`, resolved `15:34:48Z`, both `2026-08-17`).

- **Golden diff scope — verified.** `git show 1830f8b0` touches exactly
  `specs/bugs/bugs.jsonl` + the two golden JSON files. The added lines in
  `doctor_all_four_v0158.json` and `install_target_resolution_v0158.json` are
  exclusively the two alpha-1 script entries (`lint-dadaia-cli-reachability.py`,
  `lint-skill-collisions.py`); `panel_runtime_validation_v0158.json` is untouched, as
  claimed. Regenerated *before* `ed94f5b0`, so it does not carry §1's drift.
- **The "T-043-10 false-positive guard"** referenced in the dispatch brief is not a
  second registered bug — it is
  `test_agents_placeholder1_ignores_a_token_shape_inside_a_longer_code_span`
  (`test_scaffold_placeholder_repair.py:216-230`), a dedicated unit test proving the
  AGENTS-PLACEHOLDER-1 check's tight single-backtick-span design decision (documented
  in commit `91c5d831`'s message) actually holds behaviorally. Verified passing
  (§2, FR8 row). Recorded here as record-only — no second Arm-B bug exists for
  `alpha-1`; the segment's only rider is the goldens regen above.

---

## 4. Full suite

```
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider -m "not quarantine" -n auto -q
2312 passed, 3 skipped, 0 failed in 41.33s
```
Matches the expected line exactly (3 skips are the documented Windows-only/no-LAN-IPv4
environment skips, unrelated to this segment).

---

## 5. Test-pyramid audit of the `alpha-1` delta

- **New tests:** 6, all `tests/unit/features/specs/test_scaffold_placeholder_repair.py`
  (T-043-10/FR8), `pytestmark = pytest.mark.unit`. Intent declared once at the section
  header (`Intent: CONTRACT — asserts SPEC.md FR8 / A8.1-A8.3`, :162-166) covering all
  six — matches the declared shape (module/section `Intent:` header) per this release's
  standing rule.
- **Zero new `tests/e2e/**`** — confirmed (`git diff --stat cab4e6c1..HEAD --
  'tests/e2e/**'` empty).
- **No quarantine/skip/xfail markers** introduced (grep clean).
- **No slope/mock-inflation/copy-paste smell:** each test asserts a distinct
  observable outcome (WARN fires / stays silent under 4 distinct input shapes); no
  magic-mock scaffolding — `SpecsDoctor.check()` runs against a real scaffolded
  `specs/` tree per test, not a stub.
- **Fixture-only changes** (2 golden JSON files) are evidence artifacts for the Arm-B
  rider, not new test cases — correctly not counted against the pyramid.

No stewardship verdict required this segment (no deletion, skip or disable proposed
or executed).

---

## 6. Record-only vs actionable summary (first pass)

- **Actionable, now resolved:** 1 — §1's projection drift, fixed by `ai-engineer` at
  commit `b7ad9123` and independently re-verified in §0 above. 0 actionable findings
  remain open.
- **Record-only (terminate in this report):** 2 — the "7 vs 6 new tests" metrics slip
  (§2, FR8 row) and the false-positive-guard clarification (§3). Neither carries a fix
  surface beyond what already ships; no intake entry warranted.

---

## 7. Disposition

`T-043-12` flips `[-]` → `[x]`. PLAN §5's `alpha-1` exit criteria are met at
`b7ad9123`: FR1–FR8 `[x]`, one projection cycle run (re-run after `ed94f5b0`, per §0),
V9 all `[ok]` (183/0/0/0, independently confirmed), this `qa-engineer` review
committed to the branch.
