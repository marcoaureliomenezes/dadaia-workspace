# Publish-gate baseline 20260930-050-publish-gate-baseline

The 0.5.0 publish gate's BASELINE: six reports compiled into one record. It is not a three-pillar audit.
The gate's own run is recorded as a NEW record beside this one, never as an edit of it.

- **Timestamp:** 2026-09-30T13:15Z.
- **Window:** `v0.4.7` (`2d1f4351`, PyPI 2026-09-23) to `feature/0.5.0` @ `16a72c4e`. The six reports measured snapshots from 2026-09-17 to 2026-09-29 (§1).
- **Agents:** the main thread (six claude.ai report artifacts); three read-only digest agents (baseline, ambiguity, competitive); `dd-product-engineer` (this record; ids spot-checked against the ledgers at `16a72c4e`).
- **Scope:** context `dadaia-workspace`, the 0.5.0 publish gate: the 0.4.7 → 0.5.0 changelog, E2E, main-feature bugs, systemic ambiguities, worktree resilience, onboarding, docs and adoption.
- **Origin:** the operator, 2026-09-30: the reports "precisam ser persistidos para compararmos ao final. Vai ser um gate para deployar a versão 0.5.0 … analisarmos o changelog entre 0.4.7 e 0.5.0, avaliar testes E2E, verificar se features principais apresentam bugs para somente se aprovado deployarmos a 0.5.0 no pypi … não pegue lixo".
- **Findings:** none. `FINDINGS.jsonl` is empty (`audit.py check` requires the file). Every item maps to an existing record (§4) or is a gate check (§6).
- **Decisions:** none taken. §5 lists conflicts for an operator ruling.
- **Lifecycle:** closes by `audit.py close specs/audits/20260930-050-publish-gate-baseline --sha <promote head>` once the gate's record exists.
- **Durability:** the six artifacts may be deleted; this file is their record.

## 1. Provenance

| Tag | Artifact | Date | What it measured | Snapshot |
|---|---|---|---|---|
| C | `VMa5RniNgEfYz6JFgWvUWP` | 09-17, update 09-23 | Positioning, competitor map, adoption levers; 0.4.7 install checked in a clean container | `v0.4.7` wheel; digest re-checked @`5a543366` |
| A | `PL7z1Uk317iiVQng1NQXSi` | 09-26 verify, 09-27 tests | Ambiguity hunt: 109 findings adversarially verified; test-layer mirroring | `f20183a4`; tests `2c1faf65` |
| I | `TCxCwZsTyaBUfKs1FiRES8` | 09-26, plan 09-27 | Ambiguity impact: journeys, features, PyPI exposure, 49 fix packages, D1–D10 on 0.4.7 | `f20183a4`; `v0.4.7` |
| M | `SW3Pbb6JSfroRUZKJGLxTs` | 09-29 | Midway accounting against the order base | `4b55c2df` vs `9cd5fbf4` (candidate start `f61be1a0`) |
| F | `51yr1URhC8PernmTqPzLTp` | 09-29 | Full 0.5.0 audit: 10 fronts in containers vs 0.4.7 | `4b55c2df` vs `2d1f4351` |
| R | `Rn1Dn9aHCw9KgCqQkzjJNS` | 09-29 | rc1 release audit: 8 fronts plus 3 adversarial checks vs 0.4.7 | `000b4cd0` vs `2d1f4351` |

Later checkpoint (not a report): candidate 4 closure, `_RELEASE.json` log @`0d31a5f2`.

## 2. Baseline scorecard

Source tags are from §1. Where two sources disagree, both values are shown.

### 2.1 Product and journeys

| Metric | 0.4.7 | 0.5.0 (value @sha [src]) | Method |
|---|---|---|---|
| First-run rubric D1–D10 /100 | 40 [F]; 44 [I] | 74 @`4b55c2df` [F,M]; 80 @`0d31a5f2` [c4 log] | Vague prompt, container agent; weights: onboarding 15, daily flow 35, security 20, parity 15, law=behaviour 15 |
| Claude / other harnesses | 47/37 [F]; 50/40 [I] | 78/71 [F] vs 77/69 [M], both @`4b55c2df` | Same run, split by harness |
| D1..D10 (0–10 each) | 5.5 4 5 3 5 4.5 3.5 4 4 3 | 9 8.5 8.5 9 8.5 8 7.5 5 7 8.5 @`4b55c2df` [F] | install, next step, first project, specs+memory, daily flow, git/push, doctor converges, security (capped by unjudged Bash), parity, law=behaviour |
| Onboarding OB /100 | 54 (38/70) | 69 (55/80) @`000b4cd0` [R] | 8 phases × 0–10, agent with no prior knowledge |
| L1+L2: commands / errors / dead ends / guesses | 11/4/3/6 [F]; 7 cmds, 3 guesses [R] | 3/0/0/2 @`4b55c2df` [F]; 4 cmds, 1 guess @`000b4cd0` [R] | Literal first-time agent, printed output only |
| `init` output lines | 162 [F]; 176–189 [R] | 6 @`4b55c2df` [F], @`000b4cd0` [R] | stdout of `uvx … init` |
| Quickstart blocks passing | 2/7 [F] | 7/7 @`4b55c2df` [F]; README and getting-started also run whole | README, quickstart, getting-started, run literally |
| CLI commands / hooks per event | 39 / 8 | 39 / 8 @`4b55c2df` [F], @`000b4cd0` [R] | recursive `--help`; projected hook table |
| Wheel KB / runtime deps / pip-audit | 788 / 15 / 0 | 584 / 13 / 0 @`000b4cd0` [R] | build; metadata; pip-audit |
| Law corpus / root map words | 41,035 / 911 | 37,778 / 1,114 @`000b4cd0` [R] | word count of shipped law |
| Confirmed behaviour regressions | — | 0 of 184 failures, 79 files @`4b55c2df` [F]; 0 of 316 files @`000b4cd0` [R] | 0.4.7 test files run on the head; each failure re-proved via CLI/hooks |
| Upgrade 0.4.7 → head, stateful | — | 0 state diff @`4b55c2df` [F]; project specs red @`000b4cd0` [R] | re-run `init` on a real 0.4.7 workspace; byte diff |
| Secret shapes blocked by a real push | 4 of the 7 tested | all 7 tested @`4b55c2df`; `github_pat_` and `sk-ant-` were outside the set and pass (bug `secret-scan-misses-github-pat-and-anthropic-keys`) | push to a local remote |
| CI jobs | — | 3 OSes green, 14 jobs (2 PR-only skipped) @`4b55c2df` [M]; Windows/macOS run unit + contract only | GitHub Actions on the pushed head |

### 2.2 Code, tests, runtime

| Metric | 0.4.7 | 0.5.0 | Method |
|---|---|---|---|
| Production LOC | 36,333 | 23,865 @`4b55c2df`; 23,777 @`000b4cd0`; 23,793 @`0d31a5f2` | `git grep -h '' <sha> -- 'dadaia_workspace/*.py' \| wc -l` |
| Test LOC | 61,681 [F]; 61,706 [C] | 43,382; 43,224; 43,232 (same shas) | same formula over `tests/*.py` |
| Test functions | 1,858 | 1,178 [F] vs 1,179 [M] @`4b55c2df`; 1,172; 1,168 | count of `def test_` |
| Test files / collected | 316 / 2,759 | 277 @`000b4cd0` / 2,737 @`4b55c2df` | `find`; pytest collect |
| Coverage line / branch | 87.0 / 80.0 | 88.5 / 79.8 @`4b55c2df` | full suite with coverage |
| Suite with coverage, loaded host | 269 s | 1,009 s @`4b55c2df` | same host, same run |
| Suite, idle host | 81.1 s | 178.1 s @`000b4cd0` | `env -i`, `-n 3 -p no:randomly` |
| Mutants killed, 7 gate modules | not measured | 72/82 (87.8%) @`4b55c2df`; reaper linked-worktree guard survived | 82 hand-planted mutants |
| Flaky tests | not measured | 0 flips in 2,313 ids @`4b55c2df` [F] | unit + contract, seeds 1111, 2222 |
| Tool hooks, hostile workspace | 0.2 s (peak 15.5 s) | 0.2 s flat @`000b4cd0` | median of 3 per payload |
| SessionStart fresh → hostile | 0.69 → 39.5 s | 0.62 → 5.2–6.3 s @`000b4cd0` (before the reaper fixes) | same fixture |
| SessionStart 7 days after a 51k-file hold | 8.4 s | 10.3 s @`000b4cd0` | expired 150k tree + DEAD 51k checkout |
| doctor, hostile: seconds / lines after DEAD hold | 20.4 s / 51,029 | 3.1 s / 52,057 @`000b4cd0` | same fixture |
| Memory bullets checked | — | ~290: 24 stale, 7 missing @`000b4cd0` | bullet by bullet vs code |

### 2.3 Systemic ambiguity

| Metric | Value | Snapshot [src] | Method |
|---|---|---|---|
| Findings verified: confirmed / partial / refuted / bug-not-ambiguity | 109: 57 / 31 / 8 / 13; +24 new; 15 of 24 claimed HIGH held | `f20183a4` [A] | 11 verifiers each tried to refute a finding with an executed repro on a frozen copy |
| Item universe / fix packages | 149 items; 140 in 49 packages WP-01..49, 9 dropped | `f20183a4` [A,I] | one question → one authority per package |
| Test layer | 69/133 mirrored; 130/133 with no cross-check; per-test classes: keep 261, rewrite 157, delete-loser 152, dup 24, hollow 27, missing 239 | `2c1faf65` [A] | each test touching a question classified against a behaviour written first |
| Suite shape | 65,089 test lines / 1,997 fns vs 30,836 prod; 20% enter via CLI/hooks; 10.3% cross a real process; 238 `monkeypatch.setattr` | `2c1faf65` [A] | syntactic sweep of every test |
| Forced-green commits | 35 | history to `2c1faf65` [A] | assertion weakened or re-pinned in the prod-change commit, no behaviour cited |
| PyPI exposure (141 items) | 109 shipped identical in 0.4.7, 22 in another form, 10 only in 0.5.0; 23/23 HIGH shipped | `v0.4.7` vs `f20183a4` [I] | per-item code comparison |
| Journeys / features hit | 16/16 break (3 lose data, 3 leak, 10 stall or mislead); 28 features | `f20183a4` [I] | each journey mapped to its findings |
| Packages re-probed | 24 zero / 25 residue (2 HIGH) / 0 open | `4b55c2df` [F] | each package re-probed in a sandbox |
| New ambiguities introduced by 0.5.0 | 7 (1 HIGH, 5 MED, 1 LOW) | `4b55c2df` [F] | one question, one authority, per question |
| Deleted tests that looked like lost coverage (95) | 44 still covered, 8 authorized, 3 lost, 40 unadjudicated | `4b55c2df` [F] | break-the-code adjudication |
| Ratchets V37 / V38 / V39 (keys / birth size) | 0/65, 12/16, 2/52 | `5a543366` | allowances read in `tests/contract/test_slop_ratchets.py` |
| Same-surface re-bug 3d/14d; fix-induced | 71% / 82%; 37/189 | `3a279529` | `20260930-structural-convergence` F004, F009 |

## 3. Method to re-measure at the gate

- **Setup.** One host, one run, two installs: `dadaia-workspace==0.4.7` from PyPI, and a wheel built from the promote head. Everything that writes runs in `ghcr.io/astral-sh/uv:python3.12-bookworm`, `-u 1000:1000`, `HOME=/work/home`, mounting only the work dir. Do not rely on `DADAIA_FENCED_ROOTS`. Pin the promote-head sha beside every number.
- **Rubric.** D1–D10 with the same vague prompt ("install and start organizing my project"), the same journeys and the same weights, on Claude and non-Claude. Also run R's 8-phase OB. Both are logged as readouts (ADR 0122).
- **Onboarding, fresh agent.** `uvx dadaia-workspace init` in an empty dir. Then loop `doctor` → the printed `Next:` `fix:` line through `context create`, `context bind`, `specs init`, the first pass and `context baseline`. Count commands, errors, dead ends, guesses and `init` lines. Every printed `fix:` and help example runs verbatim. Pass: no metric worse than 0.4.7 (§2.1).
- **Docs walk.** Run every README, quickstart and getting-started block literally. Resolve every PyPI/README/`docs/` link. Diff each command against `--help`. Claims carry the Bash exception and name no skills repo, marketplace, score or panel.
- **Static counts.** The §2.2 LOC formula, `def test_`, wheel size, runtime deps, pip-audit, recursive `--help`, hooks per event.
- **Suite.** `env -i` with HOME, TMPDIR and COVERAGE_FILE outside the clone, `-n 3 -p no:randomly`, idle host. Line/branch coverage, seeds 1111/2222, the same 82 mutants over the same 7 modules. Per-job budgets per ADR 0119.
- **Runtime.** Fresh vs hostile workspace: 10 ALIVE contexts × 1,000-file repos, 201 sessions, 500 handoffs, 150k tmp files, plus the expired-150k and DEAD-51k case. Median of 3 per hook payload, plus doctor seconds and lines.
- **Regression and upgrade.** Run the 316 0.4.7 test files on the head and re-prove each failure via CLI/hooks. Upgrade a stateful 0.4.7 workspace on each harness and with a DEAD context, then byte-diff it. Run `codex execpolicy check` on the `sed`/`rg` forms. Prove each secret shape with a real push.
- **Ambiguity re-count.**
  1. Agreement probe: send one input to every reader of each of the 49 WP questions plus the 27 non-WP `sa-*` folds. Repro shapes: each `sa-*` record's `repro`. Zero = no question has two live deciders that disagree.
  2. Ratchets: V37 and V39 empty; each V38 key is a declared parity owner; the ADR 0135 one-parser-per-grammar contract holds.
  3. Test layer (ADR 0071): recount the 133 as mirrored vs cross-checked. Zero mirrored.
  4. Ledger: no open record names a resolved `sa-*` id (F010/F013). Re-run metric 4 and F009 over the `sa-*` fix chains.
  5. Exposure: recompute the 141 buckets against the promote head.
- **Worktree resilience** (0.4.7 has no worktree feature; baseline = absent). Probe on the promote-head wheel, in the container:
  1. `new`: caps (5 impl, 1 release, letters past `z`), each with a `fix:`; a refused `impl` without an Approved trio; a symlinked `worktrees/` component refused; a half-created worktree rolled back (AC1.7).
  2. `merge`: each of AC1.8's six refusals with one executable `fix:`. An interrupted merge (kill between fast-forward, remove and `branch -d`) re-runs clean. Never `--force`/`-D`.
  3. Parallel: two worktrees appending the same JSONL ledger merge by union; a duplicate id is refused; TASKS markers replay (AC1.9).
  4. Hygiene: doctor lists and never prunes; the reaper spares linked worktrees (kill the surviving mutant); `context dead` and closure are refused while a `wt/*` exists; nothing lands under `.dadaia/states/` (AC1.10).
  5. Environment: `find worktrees -name .venv` empty; `GIT_*` scrubbed; hooks resolve from the workspace root inside a worktree (AC1.11).
  6. Real use: the `feature/0.5.0` reflog after the bootstrap reads only `merge wt/…: Fast-forward` (AC1.14). T-050-105 logs planned vs measured width and every rebase conflict.

## 4. Trace: idea → record → status at `16a72c4e`

Ledgers at `16a72c4e`: 31 open bugs; 23 active backlog entries; `20260930-structural-convergence` has 133 open and 17 resolved findings. Each open id has one destination in the candidate 5 SPEC (§Origin map, §Carried).

| Idea (source) | Record(s) | Status |
|---|---|---|
| 49 ambiguity packages [A,I,F] | WP-01 → c3 T-050-22; WP-02..49 plus 27 folds → 75 `sa-*` bugs; thesis ADRs 0041, 0050, 0052, 0070, 0071, 0123, 0135, 0142; F010 | WP-01 done; 75/75 `sa-*` resolved. Successors bred by WP 03, 08, 11, 13, 20, 24, 30, 36; the open ones are in the rows below |
| 0.5.0 audit blockers [F,R] | `codex-policy-allows-sed-and-rg-exec-and-write-forms`, `reaper-judges-ttl-by-walking-every-file`, `doctor-ttl-walk-quadratic-on-live-trees`, `post-gate-runs-the-reaper-on-the-tool-hot-path`, `bind-lost-silently-after-five-idle-minutes`, `projected-hooks-carry-no-timeout` (ADR 0118), `test-suite-wall-clock-doubled-past-its-frozen-budget` (ADR 0119), `upgrade-leaves-project-specs-unmigrated-and-silent`, `reinit-with-unchanged-version-label-mixes-venv-and-projection`, `upgrade-refuses-a-prerelease-label-as-a-downgrade`, `unbound-native-session-writes-freely-into-repos`, `additive-globs-hand-kept-beside-the-canon` | resolved; re-measure at the gate (§3) |
| Scope, bind, fence [F,R,C] | W1: `fenced-roots-env-disables-the-gate` (F023, F079, AC1.3), `corrupt-session-record-never-collected` (AC1.4); backlog `bind-scope-durable-on-every-harness`, `ctx-inject-on-cursor-copilot` (AC1.2), `canonical-worktrees`, `worktree-harness-mechanics-study`, `doctor-context-ignores-other-contexts` | open / active; T-050-99, T-050-100 |
| Root canon, protection [F,R] | W2: `instance-exceptions-file-writable-by-agents`, `gate-protects-nothing-without-install-ledger`, `missing-venv-hook-disarms-the-gate-invisibly`, `bug-proposal-handoff-reaped-without-a-hold`, `pip-guard-fix-routes-project-installs-into-the-tool-venv`, `context-dead-ignores-the-hold-refusal`; backlog `dadaiaignore-and-root-core-canon`, `operator-protected-path-class` | open / active |
| One grammar owner, privacy [F,R] | W3: `spec-origin-line-has-two-readers`, `task-line-grammar-accepts-a-malformed-open-marker`, `privacy-denylist-has-two-loaders`, `release-ship-accepts-what-release-check-refuses`, `bugs-check-trusts-evidence-fields-unverified`, `release-new-crashes-on-a-unicode-line-separator-in-the-bug-ledger`, `corrupt-context-registry-crashes-doctor-and-next-step`, `list-form-privacy-denylist-errors-without-migration`, `secret-scan-misses-github-pat-and-anthropic-keys`; backlog `ledger-schema-one-engine`, `task-line-grammar-one-reader` | open / active |
| Fix lines, text [F,C] | W4: `dadaia-bin-still-honoured-after-adr-0045`, `help-examples-spell-the-blocked-bare-cli`, `fix-lines-are-not-one-runnable-command`, `ledger-finding-fix-line-orders-a-hand-edit-the-law-forbids`, `implementer-persona-states-a-second-task-marker-lifecycle`; backlog `consumer-guidance-names-no-library-toolchain` | open / active |
| Test harness [F,R] | W5: `test-suite-writes-outside-tmp`, `ci-preflight-writes-coverage-into-the-repo`, `default-suite-calls-a-real-model-through-codex`, `hook-entrypoints-invisible-to-coverage`; backlog `preflight-ci-parity-derived`, `test-intent-docstring-backfill` | open / active |
| Onboarding, upgrade [F,R,C] | W6: `onboarding-next-step-names-another-context`, `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original`, `pre-push-warns-no-gitflow-block-for-an-absent-specs-tree`, `upgrade-leaves-reconcile-scratch-behind`; backlog `guidance-messages-name-the-right-target`, `init-announces-codex-trust`, `release-memory-idempotent`, `tests-agents-scaffold-without-placeholders` | open / active |
| Removals, docs, launch [F,C] | W7: `removals-shipped-without-recorded-authority` (F047, F069); backlog `docs-site-zensical-pages` (ADR 0039), `clone-detection`, `launch-operator-acts` (F111) | open / active |
| Gitflow ideas | backlog `gitflow-trunk-based-model`, `consumer-gitflow-server-side-enforcement`, `associated-repo-gitflow-override` | active; `rejected` proposed, decided at candidate 6's definition |
| Bash never judged (D8 cap) [F,C] | backlog `gate-judges-bash-writes`; ADRs 0096, 0103; F074, F093 | active; W1 plans exit `rejected` (see §5.2) |
| c4 closure [F,M] | F064, F065 (resolved), F066 (open); SPEC §Gate G3 | c4 closed @`0d31a5f2` APPROVED; G3 re-runs every open bug at each wave end |
| Memory drift [R] | F133 (resolved); F139–F148; F150 (W1 closure); ADR 0138 | open |
| Reports home [F] | ADR 0147 (1); F060; T-050-103 | `reports/` still untracked in the repo |
| Promote rule [I,F] | ADR 0122; F067; SPEC §Carried "Promote PR" row | 31 bugs, 23 entries, 133 findings open |
| Skills repo, marketplace [C] | `release-publishes-an-unordered-dadaia-skills-repository` (resolved, reverted); `plugin-packaging-and-skill-evals` rejected (Q13/Q14); `launch-operator-acts` D3 | conflict, §5.1 |
| Onboarding as three levels plus a derived next step [C] | 0.5.0 c1/c3; ADRs 0027–0031, 0033, 0038; `tests/e2e/test_onboarding_journey.py` | delivered; re-measure at the gate (§3) |
| Harness breadth, gate blind on 3 of 6 [C] | `sa-gate-blind-on-cursor-copilot-devin` (resolved); W1 and W6 backlog above | resolved; open: backlog `bind-scope-durable-on-every-harness`, `ctx-inject-on-cursor-copilot`, `init-announces-codex-trust` |

## 5. Open conflicts needing an operator ruling (listed, not decided)

1. **Skills repo.** ADR 0122 keeps "the launch acts D3–D6" in 0.5.0, and `launch-operator-acts` D3 is "create the public skills repo". Against it: F111 proposes EXIT(rejected); the operator's Q13/Q14 grill rejected `plugin-packaging-and-skill-evals`; and the skills-repo job was reverted after bug `release-publishes-an-unordered-dadaia-skills-repository`.
2. **Bash never judged.** ADR 0103 and root map §3 say the gate never judges Bash. Backlog `gate-judges-bash-writes` (active) asks that it does. SPEC W1 plans its exit as `rejected` (0096, 0103). The D8 security score stays capped until this is ruled.
3. **Windows/macOS scope.** Integration and E2E never run on Windows/macOS; ADR 0119 budgets unit + contract only. Does the gate require them?

## 6. The 0.5.0 publish-gate checklist

| # | Check | Pass criterion |
|---|---|---|
| 1 | Bugs | `bugs.py status` → `[ok] 0 open bug(s).` (ADR 0122) |
| 2 | Backlog | `BACKLOG.json` `active[]` is `[]`; `backlog.py check` passes |
| 3 | Findings | `audit.py check` passes; no `open` finding in any audit; `20260930-structural-convergence` closed |
| 4 | Candidates | every 0.5.0 candidate closed; `release.py check` passes; §5 ruled |
| 5 | Changelog 0.4.7 → 0.5.0 | written from the content diff `2d1f4351..<promote head>` and read by the operator; one `[0.5.0]` heading in `CHANGELOG.md`; the 0.4.7 section no longer lists D1 (`CLAUDE_API_KEY`, removed by ADR 0025) or the skills repo as pending (today L357, L389) |
| 6 | Removals and lost coverage | every removal vs 0.4.7 (commands, SPEC-DOC rules, flags, deps, the Codex "UNVERIFIED" warning, the silent tier collapse) carries a SPEC `Replaces` line or an ADR; the 3 lost tests (`init` writes nothing under `~/.claude`, `dadaia -V`, `public install` without `--target`) and the 40 unadjudicated deleted tests each have a test or a `Replaces` line |
| 7 | Rejected records (0152 (4)) | the code and principles behind rejected ADRs 0001–0004, 0010–0013, 0024, 0026, 0091 (memory: `ARCHITECTURE.md` P-01, P-09, P-14, P-15; `QUALITY.md` P-29) are listed, path by path, for the operator, and he rules on each; until he rules, those five principles still cite their rejected records |
| 8 | E2E and CI | every CI job green on 3 OSes on the PR to develop and on the release PR; `tests/e2e` green from the built wheel; a `dd-code-reviewer` APPROVED verdict on each PR head |
| 9 | Main features | §3 regression run: 0 confirmed regressions across the 316 0.4.7 test files; stateful upgrade on every harness and with a DEAD context: operator files byte-identical, both doctors clean; a v1/v1.1 handoff and a list-form denylist migrate or refuse with one `fix:`; `specs upgrade` on a symlinked specs tree refuses with an empty byte diff |
| 10 | Six harnesses | on each harness: the gate verdict is honoured (a Kimi `WriteFile`/`StrReplaceFile` out-of-scope payload BLOCKs), the bind survives 10 idle minutes (`context show --json` still names the context), the session transcript carries the ctx-inject `constitution.md` prefix |
| 11 | Systemic ambiguity | §3 re-count: 0 questions with disagreeing deciders; V37/V39 empty; 0 mirrored findings; no open bug names a resolved `sa-*` |
| 12 | Security | fence case refused (AC1.3); `sed`/`rg` forms refused by `codex execpolicy check`; `github_pat_` and `sk-ant-` refused by a real push; the privacy denylist scan over `specs/` and the unpacked wheel reports 0 hits |
| 13 | Mutation | the same 82 mutants over the same 7 modules: ≥ 72 killed, the reaper linked-worktree guard mutant killed |
| 14 | Worktree resilience | every §3 worktree probe passes; the AC1.7–AC1.11 and AC1.14 commands green |
| 15 | Runtime | §3 hostile fixture, median of 3, both versions in one run: SessionStart ≤ 5.0 s, and ≤ 5.0 s after the 51k-file hold; each tool-hook payload ≤ its 0.4.7 median; `pytest tests/unit/infrastructure/test_runtime_config_session_start.py` passes (every hook carries a timeout, ADR 0118); `gh run view <id> --json jobs` shows every job inside its `timeout-minutes` in `.github/workflows/ci.yml` (ADR 0119) |
| 16 | Onboarding | fresh-agent `uvx` journey completes by `Next:` lines alone; commands, errors, dead ends, guesses and `init` lines each ≤ the 0.4.7 value of the same run; D1–D10 and OB logged as readouts |
| 17 | Docs walk | every block runs; every link resolves; commands match `--help`; no demolished feature claimed |
| 18 | Version | release-please mints 0.5.0 (`pyproject.toml`); PR #269 closed; publish only through CI, on the operator's order |
| 19 | Memory | `python3 .agents/skills/dd-spec-navigator/scripts/memory.py check --specs specs` exits 0; every atom `memory.py drift --since 2d1f4351 --specs specs` lists is changed or reviewed in a 0.5.0 closure memory entry |
