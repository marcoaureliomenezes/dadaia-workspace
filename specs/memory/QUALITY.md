---
slug: QUALITY
title: quality-assurance
tldr: The measured quality principles, the test architecture (tiers, flake and quarantine policy) and the CI gate set with its slop ratchets.
summary: Canonical memory — statements and laws of testing and quality; a `### P-NN` principle changes with its accepted ADR, any other section under the ADR 0138 lane.
tags: [testing, pytest, ci, quality, test-architecture, flake, quarantine, privacy]
---

## Principles

### P-21 · We give every test a size tier with an enforced timeout applied at collection, and an explicit `@pytest.mark.timeout` is never overridden.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS tier-timeout`; `--planted` turns it red on a test without its tier timeout and on an overridden explicit timeout.
ADR: 0167 (accepted)
Rationale: a test needing more time than its tier is mis-tiered.

### P-22 · We gate quarantine on a registered bug: a `quarantine` mark without `bug=` refuses collection actionably, and every gating selector excludes the lane.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS quarantine-needs-bug`; `--planted` turns it red on a `quarantine` mark without `bug=` and on a gating selector in `.github/workflows` that keeps the lane.
ADR: 0167 (accepted)
Rationale: the registered id is what makes the lane temporary.

### P-23 · We ratchet private-symbol imports in `tests/**` downward only; a per-statement `# allow-private-import: <reason>` marker is the sole exception.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS private-import-ratchet` (AST-exact; `scripts/guards/suite.py` is the ceiling's numeric home).
ADR: 0167 (accepted)
Rationale: a test reaching into a private symbol turns a safe refactor red.

### P-28 · We keep the pytest marker set closed and single-sourced: `pyproject.toml`'s `markers` is the one list, and `flaky`/`quarantine` are always among them.
Measured by: `pytest --collect-only -q` exits 0 under `--strict-markers` in `pyproject.toml`'s `addopts`, which refuses any mark absent from `markers`.
ADR: 0167 (accepted)
Rationale: a marker known to one file and unknown to the other is a silent exclusion lane.

### P-29 · We derive every human- and agent-facing document from a named memory atom under a content hash: each `## ` section of `README.md`, `llms.txt` and every `docs/*.md` names its atom and the atom's current sha256, and `docs/cli.md` is the committed output of `dadaia help tree`.
Measured by: `pytest tests/contract/test_docs_derived_from_memory.py`.
ADR: 0012 (accepted)
Rationale: a document written beside memory rots; one that names its source is red the moment the source moves.

### P-33 · Only the library's own `.github/workflows/eval.yml` calls a model API, and only in `workflow_dispatch` or `schedule` jobs, reading the model secret at job level from the `evals` environment and scanning every upload first (ADR 0217); no other library workflow uses an `anthropics/*` action or references a model secret; the shipped law states no rule about a user's CI.
Measured by: `poetry run python scripts/guards/run.py` prints `PASS no-model-api-in-ci`.
ADR: 0217 (accepted, superseding 0177 and 0179)
Rationale: a model call on a PR path fails closed without the paid key and exposes it; evals measure what ships, from the repo that ships it.

## Test architecture

- Size tiers `small` (10 s: no process, no real git), `medium` (60 s: reaches a process or real git) and `e2e` (120 s: a journey in `tests/e2e/**` naming its `Owner:`), read from what a test reaches by `tests/conftest.py`, never from its folder; a small test that starts a process fails (`small-spawns-no-process`); live Codex-binary validation is opt-in outside CI.
- `tests/<p>/test_<m>.py` mirrors `dadaia_workspace/<p>/<m>.py`, a second file for a module is `test_<m>__<topic>.py` (`tests-mirror-the-package`).
- The suite is hermetic; `tests/conftest.py` blocks a real Codex call without its live flag and fakes `ensure_workspace_venv`.
- `tests/conftest.py` prepends this checkout to `PYTHONPATH` once for the whole session, so every spawned CLI/hook subprocess imports the worktree under test, never the venv's installed package.
- Every guard check enumerates one set — `scripts/guards/run.py`'s `tracked()` over `git ls-files` — so a scratch file another process writes is outside the measurement by construction.
- Output naming a foreign Spec Context is `--redact`ed before entering evidence.

- `flaky` marks a pass-and-fail on identical code; `quarantine` leaves every gating selector, is bug-gated by P-22, and the lane is empty.
- Growth past the per-job wall-clock budget frozen by ADR 0119 is a budget breach, judged by `dd-code-reviewer` reading the CI job durations (`gh run view`, per job; ADR 0166).
- Curation is a `code-reviewer` verdict (QA lens); `software-engineer` executes.
- Mutation evidence is operator tooling, outside the repo (ADR 0166).

## Gates

- CI runs ruff and `lint-imports`, mypy `--strict`, the guards (`scripts/guards/run.py`, plain and `--planted`), the small tier on Linux, the `not e2e` coverage run on Linux, Windows and macOS, the small tier again on Windows and macOS with an importability smoke, the medium tier, Python E2E, repo hygiene, `dadaia doctor` over the checked-out tree, PR governance and gitleaks — every PR job a required status check listed in `.github/required-checks.json` (`required-checks-listed`), gitleaks included; no job calls a model API (P-33) except `.github/workflows/eval.yml`, the one exception (ADR 0217).
- Push triggers are `main`, `develop`, `feature/**` and `wt/**`; PRs to `develop` or `main` run the same matrix.
- `pr-source-guard` is fail-closed; the security review of both PR edges is the `dd-code-reviewer` security lens on the PR head, run by the main thread before the PR.
- Every review verdict states the bug-surface delta from `bugs.py stats`, and no deploy is approved without the consumer-side matrix.
- Caches redirect by configuration, never by a remembered flag: `[tool.pytest.ini_options] addopts` (`-p no:cacheprovider`), hypothesis `database = None`, and ruff and mypy write to the absolute `.dadaia/tmp/<tool>-cache` that every harness env exports (`workspace_layout.TOOL_CACHE_ENV`); a bare `pytest`, `ruff check`, `ruff format --check`, `mypy --strict` from any cwd leaves the tree clean (`tests/infrastructure/test_runtime_config__tool_caches_stay_in_the_tmp_zone.py`).
- The forbidden repo-local set is `core/workspace_layout.REPO_TREE_EXCLUDED`, measured here by `ci.yml`'s `repo-hygiene` job and swept at every ALIVE repo by `dadaia doctor`.
- Memory-vs-code drift is a `dadaia doctor` `specs`-section WARNING (`MEM-DRIFT-1` for the features package map, `MEM-DRIFT-2` for a dead `dadaia <verb>` or path an atom cites), never a push-gated test: a package added or a verb deleted mid-implementation is memory drift to fix at the next closure, not a red build.
- A citation of a superseded decision is an ERROR (`ADR-SUPERSEDED-CITATION`): a rule pointing at a dead ADR fails the build.
- A doctor fix is proven on the executed path: `tests/cli/commands/test_doctor.py` executes every specs rule's fix line against a planted finding and re-runs the rule, which must then emit nothing, never the fixer's return value; the `ledgers` section delegates to each ledger's skill script (`tests/infrastructure/test_ledger_scripts__doctor_ledgers_delegate_to_scripts.py`); a schema drop ships with its repair and its test in the same change.
- The closed pytest marker set is seven — e2e, small, medium, slow, tmp, flaky, quarantine (P-28).
- Every `ci.yml` checkout fetches full history (`ci-checkout-history`); `release.yml`'s build and `secret-scan.yml` fetch full history; no job fetches history for a bug record's sake.

- Repo-pure ratchets move only downward and run as `scripts/guards/run.py` checks: `suite.py` holds `private-import-ratchet` (V26, P-23); `slop.py` holds V32 (governance ids in production comments and docstrings), V33 (`PREFIX-NN` families without a mechanical reader) and `ignore-cap` (suppressed layering edges, P-10) as pinned counts, V37 (one home per definition), V38 (deletes only in `features/spec_context/sweep.py`) and V39 (every doctor code has a fix-clears case) as keyed allowances whose keys stay within their birth keys, and V40 (every JSONL ledger read through the one reader) at zero; no check pins a file's line or byte count (`no-size-pin`, ADR 0143).
- The derived-docs contract `tests/contract/test_docs_derived_from_memory.py` (P-29) checks every `<!-- derived-from: <slug> sha256:<12 hex> -->` marker's slug and hash over `README.md`, `llms.txt` and `docs/*.md`, the `docs/cli.md` body against `render_digest()`, the one tagline across `README.md`, `pyproject.toml` and `llms.txt`, the five `[tool.poetry.urls]` keys, and runs `dead_citations` over the same set; a red row is closure work — after the memory merge, in an `impl` worktree (the `release` kind holds no `docs/`), re-read the atom, re-derive the section and re-record the hash (`dd-release-implementation` MEMORY-UPDATE).
- Stale handoffs and scratch are a closure readout, never a ratchet: `dd-release-implementation` RC-FLOW step 8 runs `dadaia doctor` dry, then `dadaia doctor --fix` (slop moved to `reaped/`, expired entries deleted), and the `kind: artifact-gc` log entry records the `compliance(total)` line and what the reaper holds.
- `dd-audit-project` pillar 2 re-measures the ratchets over the audit window and applies `dd-code-review` SLOP.md S1–S10 to a commit sample; the fixed law sections are kept byte-exact by `dadaia doctor` FIXED-1/2.

Related: [[ARCHITECTURE]]

<!-- dadaia:fixed slop-tests -->
### Slop — tests (fixed)
- A test follows the root `AGENTS.md` map §1 test basics; an own module is tested through its interface.
- A test name states current behavior; a tombstone (a test of an absence) dies with its target.
- Pruning is a `dd-code-reviewer` verdict executed by `dd-software-engineer`; a deletion cites its criterion and its replacement `file:line`.
- Detection: `dd-code-review` SLOP.md S3.
<!-- /dadaia:fixed slop-tests -->

## Bugs

```text
Bug balance from BUGS.jsonl: 914 records (882 live, 32 archived).
surface                                            records  recurrences  fix-induced  archived  rcs  correlates  settled
.github/dependabot.yml                             1        0            0            0         0    0           yes
.github/workflows/release.yml                      1        0            0            0         0    0           yes
backlog                                            22       21           3            1         0    0           no
bugs                                               21       20           6            0         2    1           no
certification                                      7        6            2            0         0    0           no
chokepoints                                        27       26           11           1         1    2           no
ci                                                 1        0            0            0         0    0           no
ci_preflight                                       14       13           0            2         0    0           no
cli                                                27       26           8            0         0    0           no
core                                               28       27           4            0         0    0           no
dadaia context dead                                1        0            1            0         0    0           no
dadaia doctor --fix                                1        0            0            0         0    0           yes
dadaia specs init / doctor TREE-1,TREE-2 messages  1        0            0            0         0    0           yes
dadaia_workspace                                   86       85           50           0         5    36          no
dd-bug-resolution                                  1        0            1            0         1    4           no
docs                                               1        0            0            0         0    0           yes
doctor                                             3        2            2            0         0    0           no
features                                           6        5            2            0         0    0           no
hooks                                              27       26           4            2         0    0           no
import_                                            1        0            1            0         0    0           yes
infrastructure                                     33       32           9            0         1    2           no
migrate                                            4        3            0            0         0    0           no
onboarding                                         1        0            1            0         0    0           no
panel                                              6        5            1            3         0    0           yes
public                                             27       26           10           0         2    3           no
public-assets                                      28       27           2            0         0    0           no
reconcile                                          3        2            0            0         0    0           no
release-ledger                                     3        2            2            0         0    0           no
reports                                            3        2            1            0         0    0           yes
repos                                              1        0            0            0         0    0           yes
schemas                                            1        0            0            0         1    1           no
sdd                                                1        0            0            0         0    0           no
shipped text (CONTEXT.md, docs/, public/)          1        0            1            0         0    0           no
skills                                             3        2            2            0         1    0           no
spec_context                                       74       73           18           7         1    2           no
specs                                              62       61           9            0         2    0           no
specs-doctor                                       1        0            0            0         0    0           no
telemetry                                          1        0            0            0         0    0           yes
unknown                                            268      -            32           16        0    0           -
workspace                                          13       12           1            0         0    0           no
dev-tooling:
.github                                            3        2            0            0         3    2           no
scripts                                            8        7            2            0         4    6           no
tests                                              92       91           34           0         4    15          no
Laplace trend (days), window 0.4.5..0.5.0, T = 42 days: u = 13.67, diverging
  counted 397 of 914 records; apart: 452 release unknown, 65 no found_in, 0 outside the window
  records found on an already settled surface: 6
Defective-fix rate per rc (caused_by set over found in the rc):
0.5.0/rc-6  2/8  25%
0.5.0/rc-7  6/23  26%
0.5.0/rc-8  20/26  76%
0.5.0/rc-9  4/7  57%
0.5.0/rc-10  50/72  69%
```


The review below is rewritten at every closure, never appended; the block above is `bugs.py balance --write` and nothing else.

- **The balance.** The numbers (found, resolved, defective-fix rate, trend, settled-surface records) are the block above's and are not restated here. In words: a candidate closes only with no open bug, and a deferred record counts as open, so it is fixed inside the candidate that found it. The trend says the ledger grows faster than it settles, so every cause below is read as a structure to rebuild, not a bug to patch.
- **Standing cause 1 — one platform seam skipped.** `J7.S2.T2` is the culprit of 8 records of the last candidate, all Windows-only test or fixture bugs (a POSIX `bin/` path, a bare `python`, a `bash` spawn, a read-only `.git` rmtree). Verdict: the fixes are KEEP; the structure is `core/platform.py` as the one home of platform facts, and a test reaching past it is the defect.
- **Standing cause 2 — the merge gate and the worktree verbs.** `J1.S3.T1` is the culprit of 4 records (worktree removal leaving its parent and remote branch, a job merge accepting any CI run URL, a job merge requiring a remote CI run, a rebase laundering the stray check) and `J1.S2.T1` of 2 more (task fix lineage, rebase orphaning fix links cited by sha). The records show the chain: each gate fix left a second reader of the same fact. Verdict: REBUILD on any further hit; the judged party must never be able to supply its own evidence.
- **Standing cause 3 — a closed id grammar.** `freeze-reads-only-numbered-job-ids` and `bugs-check-reads-no-jb-task-ids` are one family: a task id reader written for `J<n>` and later widened one prefix at a time. Verdict: one id grammar, read in one place.
- **Lessons.** A bug fixed at the caller it was caught in breeds the next caller's bug; a measurement with its own exclusion breeds the next measurement's bug; a cached derived fact breeds a bug per environment that derives it differently. Each family ended only by a deletion-shaped fix. Read the ledger before every fix and rebuild a unit with two prior fixes; every review verdict states the bug-surface delta, read from `bugs.py stats`.
- **Evals.** An eval run judges the candidate against the previous release on two scenarios, three trials per side. Three runs happened. The first (run 37629005413) ended BLOCK: `t1-cold-onboarding` 3/3 against 3/3, `t2-block-list-bug` 3/3 baseline against 0/3 candidate, because the candidate gate refused direct writes under `repos/demo/` and `worktree.py new` had no `hotfix/<bug-id>` tree outside an rc. The second (run 37652269562) ended BLOCK again on `t2-block-list-bug` (0/3 against 3/3); its cause was an onboarding that wrote no tests line (ADR 0216's onboarding half unbuilt, bug `onboarding-writes-no-tests-line`); the review found three more on the way: `freeze-cannot-see-a-red-amendment-stage`, `skill-git-output-decodes-with-the-locale`, `declared-echo-rereads-the-law`. The third (run 37673898303, `workflow_dispatch`, success) ended non-blocking: `t1-cold-onboarding` 3/3 against 3/3 (3 found each side), `t2-block-list-bug` 3/3 against 3/3, both readout. Lesson: a BLOCK that names a missing tree or an unbuilt half of an ADR is a bug to register and fix at its cause, then rerun; the verdict is never waived.
