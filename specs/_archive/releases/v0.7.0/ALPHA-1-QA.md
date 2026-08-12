# ALPHA-1 QA Review — Release v0.7.0 (Test stewardship)

**Task:** T-070-08 · **Owner role:** qa-engineer · **Reviewer:** qa-engineer
**Preconditions verified:** T-070-01..07 all `[x]` in `TASKS.md`.
**Validated from:** the live instance (branch `feature/v0.7.0`, worktree HEAD at
`85191d0c chore(tasks): T-070-07 done`), not the diff.

## Verdict

**PASS — APPROVE.** All nine checks pass with evidence. One noise finding
(homonym collisions in the relocation grep) and one soft-verification gap (CI
`timeout-minutes` ratio to the named baselines) are recorded below as
non-blocking observations, not defects.

---

## Per-check evidence

### 1. Projection integrity

- `sha256sum` of `DADAIA.md`, `.claude/rules/DADAIA.md`, `.codex/DADAIA.md`,
  `.kimi-code/DADAIA.md` — all four identical
  (`4084bef664208d...728417285ee`).
- `stat -c '%a'` on all four — all `444`.
- `dadaia-test-stewardship` present in `.claude/skills/dadaia-test-stewardship`
  and `.agents/skills/dadaia-test-stewardship` (the canonical universal-skill
  home per `public-asset-distribution`; Codex and Kimi Code read skills through
  the same shared `.agents/skills/` root rather than a duplicated per-harness
  copy — no drift).

**Result: PASS.**

### 2. A4.1 relocation grep, run independently

Command: `grep -rniE 'SENTINEL|SCAFFOLD|QUARANTINE|tombstone|demotion' public/
tests/AGENTS.md tests/README.md`.

Every doctrine-relevant hit resolves to one of the four authorized homes:
`dadaia-test-stewardship/SKILL.md` (the skill), `public/data/DADAIA.md` (the
law, the five-point block + two sentences), `tests/AGENTS.md` (the repo's
single owner), or an explicit reference/citation in `drift-detection/SKILL.md`
(Dimension E, scoring only), `dadaia-release-closure/SKILL.md` (the demotion +
disposition block, A4.4), `qa-engineer.md`/`software-engineer.md` (steward
verdict vs. execution split), `project-orchestration/SKILL.md` (citation
only), `constitution.md` (§8, PT-BR pointer), and
`templates/tests-AGENTS.md` (the authorized parameterized consumer copy,
T-070-03).

**Finding (INFO, non-blocking).** The same grep also surfaces pre-existing,
unrelated homonym uses of "scaffold"/"sentinel"/"quarantine" that predate this
release and belong to a different feature: workspace scaffolding
(`registry.json`, `scaffold/AGENTS.md`, `dadaia-cli/SKILL.md`,
`lint-memory-atoms.py`, `backlog/README.md`), the legacy-quarantine directory
feature (`dadaia-AGENTS.md`, `CONSUMER_VALIDATION_RECIPE.md`), a JSON-schema
"resolved: unknown" sentinel value (`bug-event-v1.schema.json`), and session
bootstrap sentinels (`ai-harness-codex/SKILL.md`,
`ai-harness-claude-code/SKILL.md`, `dadaia-step0-memory-bootstrap/SKILL.md`).
None of these carry test-doctrine content — they are a naming collision, not
scattered doctrine — but the grep as literally specified (case-insensitive,
whole-corpus) is noisy and will re-surface this list on every future run.
Recommend the skill note the collision so a future author doesn't chase it.

**Result: PASS** (relocation held; independent audit did not find drift).

### 3. Coverage grep (A7.1/A7.2), re-run independently

Command: `grep -rn 'cov-fail-under\|80%' public/ tests/AGENTS.md
tests/README.md .github/workflows/ci.yml`.

Exactly four sites, one stance ("the 80% floor is a CI gate, not an acceptance
target"):

| Site | Text |
|---|---|
| `tests/AGENTS.md:94` | `--cov-fail-under=80` in the coverage command |
| `tests/README.md:11` | `--cov-fail-under=80` in the coverage command |
| `.github/workflows/ci.yml:174` | `--cov-fail-under=80` in the coverage job |
| `public/scaffold/constitution.md:44` | "O piso de **80%** de cobertura é um **gate de CI**, não uma meta de aceitação" |

No fifth stance. `drift-detection/SKILL.md:187` reinforces the same stance in
prose ("checked separately as a pass/fail gate, never scored here") without
restating the number — consistent, not a competing site.
`architect-core-workflow/SKILL.md:53`'s "80%+" is an unrelated "Fit" heuristic,
correctly excluded.

`ci.yml`'s `--cov-fail-under=80` — byte-unchanged versus the pre-release value
(same literal at the same call site; no numeric or flag drift).

**Result: PASS.**

### 4. Citation check (A3.2), re-run independently

Constitution headings present: `{1,2,3,4,5,6,7,8,9,11,13,14}` (no renumbering;
§10/§12 absent as before this release).

`constitution §N` citations found across `public/agents/**` +
`public/skills/**`: `§6, §7, §9, §11, §13, §14` — every one resolves to a
present heading. Empty difference.

**Result: PASS.**

### 5. Mechanical checks

- **Tiered timeouts active.** `tests/conftest.py`'s `_TIER_TIMEOUTS = {"unit":
  10, "contract": 30, "integration": 60, "e2e": 120}` is applied in
  `pytest_collection_modifyitems` via `item.add_marker(pytest.mark.timeout(N))`
  only `if item.get_closest_marker("timeout") is None` — confirmed by reading
  the function body directly (mechanical enforcement, not documentation-only).
  `tests/contract/test_stewardship_mechanics.py::test_tier_timeout_table_covers_all_four_layers`
  and `::test_contract_tier_carries_30s_timeout` assert this and pass (7/7 in
  that file, see §8 below).
- **Bug-less quarantine refused at collection.** `_validate_quarantine_markers`
  raises `pytest.UsageError` when a `quarantine`-marked item has no
  string `bug=` kwarg. `test_quarantine_without_bug_id_refuses_collection` /
  `test_quarantine_with_bug_id_is_accepted` in the same contract file cover
  both branches and pass.
- **Quarantined sample excluded from every gating selector.** All six gating
  `-m` selectors in `.github/workflows/ci.yml` (unit fast ×2 OS legs, unit+
  contract coverage ×2 OS legs, integration, e2e) carry `and not quarantine`.
  No test in the current suite is actually marked `quarantine` (the mechanism
  is proven by the contract tests above and the T-070-06 flake demonstration
  below, not by a live quarantined sample sitting in the tree — correct, since
  a permanently quarantined sample would itself violate the 30-day escalation
  rule).
- **Flake-gate demonstration output — credibility judgment.** The captured
  evidence (`STEP-FAILS: 1 test(s) passed only on retry — unregistered
  pass-on-retry` / `detection-exit=1`) is thin as a standalone artifact — two
  lines, no test name, no CI run URL — but it is consistent with the actual
  `.github/workflows/ci.yml` step ("Fail on unregistered pass-on-retry (loud
  flake)", lines 358-371): that step parses `${{ runner.temp }}/pw-flake.json`
  for `passed`-after-`retry>0` results and exits 1 with the exact "passed only
  on retry" wording used in the captured line. The evidence is **credible as a
  same-shape match to the real step**, though CLOSURE should attach the full
  job log (not just the two summary lines) for a durable record — recorded as
  a **finding (LOW)**, not a blocker, since T-070-06 is `[x]` and the mechanism
  itself (the CI step) is verified directly and independently here.
- **`--durations` and `timeout-minutes`.** `--durations=25` on both unit-fast
  and unit+contract-coverage jobs (both OS legs); `--durations=30` already on
  integration/e2e (unchanged, as required). Every pytest job in `ci.yml`
  carries `timeout-minutes`.
  **Finding (INFO, non-blocking).** TASKS.md names the ratchet source as
  "preflight quick 2:38, preflight full ~5:30, panel E2E 1:10" (the local
  pre-push preflight, not 1:1 with individual `ci.yml` jobs). No comment in
  `ci.yml` or `ci_preflight/service.py` embeds those literal baseline figures,
  so the exact 1.5× arithmetic per job could not be independently re-derived
  from repository text alone in this review; the *shape* of the ratchet
  (every job bounded, none unbounded) is verified.
- **Dead `--ignore=tests/performance` gone.** No hit anywhere in
  `dadaia_workspace/`, `tests/`, `.github/` except the pinning assertion
  itself (`tests/contract/test_stewardship_mechanics.py:117`, which asserts
  the string is **absent** from the preflight command — the correct polarity).

**Result: PASS**, two non-blocking findings recorded (flake-evidence
thinness, ratchet re-derivation gap).

### 6. Consumer landing

- The three scaffolder cases (`tests/unit/features/spec_context/
  test_tests_agents_scaffold.py`) all pass: `tests/` exists + no `AGENTS.md` →
  created byte-identical from `templates/tests-AGENTS.md`; `tests/AGENTS.md`
  exists → untouched; no `tests/` → no directory created, no file written
  (3 passed).
- Read `public/templates/tests-AGENTS.md` end to end: placeholders
  `<UNIT_TIMEOUT_S>`, `<CONTRACT_TIMEOUT_S>`, `<INTEGRATION_TIMEOUT_S>`,
  `<E2E_TIMEOUT_S>`, `<LARGE_CAP>`, `<WALL_CLOCK_BASELINE>` are present and
  correctly positioned (tier timeout line, LARGE-cap line, wall-clock line);
  the declared LARGE default is the **abstract** "12-15 per module", not this
  repo's 30. `grep -n 'dadaia_workspace\|2:38\|\b30\b'` against the template
  returns nothing — zero dadaia-workspace-specific literals.

**Result: PASS.**

### 7. Doctors

- `dadaia doctor` — exit 0. One fixable, unrelated advisory item (stale
  presence record for a different Spec Context Project,
  reclaimable with `--fix`) — not a v0.7.0 regression.
- `dadaia specs doctor` — `[ok] overall: 0 error(s), 6 warning(s)`. Warnings
  are pre-existing token-estimate drift and unrecognized headings on
  unrelated `sdd-*` memory atoms, plus legacy `_archive` naming — none touch
  v0.7.0's write set.
- `dadaia public doctor` — all `[ok]`/`[info]`/`[foreign]`, zero errors;
  `public-privacy` and `entities-derivation` both green.

**Result: PASS (exit 0 on all three).**

### 8. Full quality ladder

| Command | Result |
|---|---|
| `pytest -p no:cacheprovider -q tests/ -m "not quarantine" -n auto` | **2120 passed, 3 skipped** (2 Windows-only skips, 1 no-LAN-IPv4 skip — both environment-conditional, not failures), 0 failed, wall **277.68s (4:37)** |
| `ruff format --check .` | 647 files already formatted — clean |
| `ruff check .` | All checks passed! |
| `MYPY_CACHE_DIR=/tmp/... mypy --strict dadaia_workspace/` | Success: no issues found in 261 source files |
| `lint-imports --config setup.cfg --no-cache` | 9 contracts kept, 0 broken |
| `tests/contract/test_stewardship_mechanics.py` (the RED→GREEN pin) | 7/7 passed in isolation |

**Result: PASS.**

### 9. Frozen baselines (for CLOSURE / FR6)

| Metric | Value | Source |
|---|---|---|
| Collected tests (gating set, `-m "not quarantine"`) | **2123** | `pytest --collect-only -q tests/ -m "not quarantine"` |
| LARGE (e2e-tier) test count | **55** | `pytest --collect-only -q tests/e2e` |
| Full-suite wall clock (parallel, `-n auto`, this run) | **277.68 s (4:37)** | this session's ladder run |
| `DADAIA.md` tokens (chars/4 approx, T-070-02's own measurement) | before **3983** → after **4204** (Δ+221, within the +400 cap) | commit `7611ffea` message; current file is byte-identical to that "after" state (unchanged since) |

RED-before-GREEN evidence re-confirmed present and credible for both TDD
tasks:
- T-070-05: 6 failed / 1 passed before the GREEN commit, each failure an
  `ImportError`/`AttributeError` on the not-yet-built symbol
  (`_validate_quarantine_markers`, `_KNOWN_MARKERS`, `_TIER_TIMEOUTS`,
  `Check.command`) — the right reason, not an unrelated crash.
- T-070-07: 1 failed / 2 passed before the GREEN commit
  (`test_tests_dir_without_agents_receives_the_template_byte_identical`) — the
  one case that needed the new copy-on-alive behavior; the other two
  (existing-file no-op, no-`tests/`-no-op) already passed, correctly, since
  they describe "nothing happens" states.

**Result: PASS, baselines captured.**

---

## Explicit-timeout justification review (S-09/S-10 bar)

Two tests carry an explicit `@pytest.mark.timeout` above their tier default,
each with an inline justification citing a measured wall-clock and a queued
structural remediation:

- `tests/integration/cli/test_context_name_differs_from_repo_slug.py::
  test_create_refuses_a_name_no_other_verb_can_use` — `timeout(180)`. Cites
  "measured ~20 s solo / >60 s under full-suite xdist load — above the 60 s
  integration ceiling" and points at
  `specs/backlog/test-suite-remediation-stewardship.md`.
- `tests/e2e/features/test_handoff_pipeline.py::
  test_full_handoff_emit_and_validate` — `timeout(300)`. Cites "measured 71 s
  solo — a full bootstrap + emit + validate pipeline over real subprocesses,
  above the 120 s e2e ceiling under xdist load" and points at the same
  backlog file.

Both justifications carry the three elements the bar requires: a **measured**
number (not a guess), the **specific ceiling** exceeded and **why** (real
subprocess/CliRunner cost, amplified under parallel load), and a **named,
existing** remediation backlog entry (`specs/backlog/
test-suite-remediation-stewardship.md`, confirmed present on disk) rather than
an open-ended "TODO". Neither raises a *default* — both are per-test,
explicit, and justified. **Meets the S-09/S-10 bar.**

---

## Findings summary

| # | Severity | Area | Finding | Blocking? |
|---|---|---|---|---|
| F1 | INFO | A4.1 relocation grep | Grep as literally specified also matches pre-existing, unrelated homonym uses of "scaffold"/"sentinel"/"quarantine" (workspace scaffolding, legacy-quarantine dir, schema sentinel, session sentinel) that carry no test doctrine | No |
| F2 | LOW | Flake-gate evidence | Captured demonstration output is two summary lines, not a full job log; shape matches the real CI step but CLOSURE should attach the fuller artifact | No |
| F3 | INFO | Budget ratchet | The named baseline figures (2:38 / 5:30 / 1:10) are not embedded in repo text, so the exact 1.5× per-job arithmetic could not be independently re-derived from the repository alone in this review; every job is bounded, which is the load-bearing property | No |

No CRITICAL, HIGH, or MEDIUM findings. No task returns to `[-]`.

## Security/privacy leakage note

Reviewed for observable risk surfaces in this segment's diff-adjacent surface
(test tiering, quarantine gate, scaffolder copy, flake-gate CI step):
- The flake-gate CI step writes its JSON report to `${{ runner.temp }}`
  (outside the repo tree), matching the `DADAIA.md` §4 artifact-location rule
  — no new repo-local artifact.
- The scaffolder copy (`spec_context/service.py`) only writes
  `tests/AGENTS.md` when `tests/` exists and the file is absent — verified by
  the three-case test; it cannot overwrite an operator file or create a
  directory.
- `templates/tests-AGENTS.md` carries no dadaia-workspace-specific literal,
  path, or credential-shaped string.
- No new dependency, secret, token, or credential surface touched by this
  segment. No consumer-specific data present in any evidence file cited above.
No suspected leakage found; nothing surfaced to `security-reviewer` beyond the
standing T-070-09 diff-based review already scheduled next.

## Accepted deviations

None required — all nine checks pass without a deviation from TASKS.md's
Done criterion.

## Marker note

This review folds the `T-070-08` reservation and completion transitions
(`[ ]` → `[-]` → `[x]`) into a single commit alongside this file, per the
operator's explicit economy directive for this task — the ordinary two-commit
reserve/complete discipline (`dadaia-task-manager`) is intentionally
shortened here and is recorded as such for audit trail continuity.
