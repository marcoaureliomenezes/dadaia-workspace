# SPEC — Release: 0.5.0, candidate 6 (W2: root canon, `.dadaiaignore`, DEC-11, one deleter)

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-09-30
**Origin:** backlog:dadaiaignore-and-root-core-canon,operator-protected-path-class,adr-0138-lane-in-memory-and-adrs-law
- Sources:
  - the W2 row, the "Decided at candidate 6's definition" row, open question Q3 and the risk seeds of rc-5's SPEC §Carried;
  - the rc-6 grill, Q1–Q6 (handoff `2026-09-30T235900Z-main-thread-grill-rc6`), answered by the operator on 2026-09-30.
- The header is the pick `backlog.py exit` reads: it names only this candidate's deliveries.
- This candidate registers one bug, the Q6 bug, before its PLAN (§Origin map).

## Objective

- Finish the two-level root canon: `.dadaiaignore` judges exactly its four places, `init` writes the level-1 root files, and core protection holds with or without the install ledger.
- Add DEC-11, an operator-protected section of `.dadaiaignore` that the one gate enforces under `repos/<r>/` and every `worktrees/<r>/<name>/`.
- Make every fail-open path visible and stated once. Delete the pip arm of the venv guard.
- Keep a no-operator bug proposal alive until the operator sees it, and make `context dead` fail when its hold fails.

## Terms

- `CONTEXT.md` holds the terms; **W2** is this candidate. **DEL** and **FR** keep rc-5's meaning.
- **Protected section**: the part of `.dadaiaignore` whose globs name repo-relative paths only the operator changes (ADR 0133). It is not the path class PROTECTED, which covers workspace law and state that no agent writes.
- **Onboarding write**: a direct write under `repos/<r>/specs/` by `context create` or the first `specs init` of a repo (ADR 0154).

## Decisions

- These ADRs decide: 0055, 0059, 0067, 0092–0096, 0103, 0114, 0118, 0124, 0132–0134, 0138, 0141, 0145, 0146, 0149, 0153.
- Proposed here, accepted only by the operator's ruling (ADR 0151 M4):
  - 0154 amends 0124 (Q2);
  - 0155 retires QUALITY P-27 (Q4).
- ADR 0145 left these parts of 0092–0096 and 0132–0133 for this candidate:
  - `repos/` and `worktrees/` first-level judging;
  - DEC-11;
  - `init` scaffolding `prompt.md`;
  - the SessionStart self-heal.
- ADR 0132 voids 0092's harness-directory clause, so inside a harness directory ADR 0059 holds (F076).
- F075 (ADR 0067 against 0096) is settled by the operator-confirmed `expected` of `missing-venv-hook-disarms-the-gate-invisibly`. Hooks stay fail-open (0067), and the loss of the gate reaches the agent once per session with its fix (§Open questions OQ2).

## Origin map — candidate 6

| Where | Bugs | Backlog | Findings |
|---|---|---|---|
| Already resolved; not carried | `instance-exceptions-file-writable-by-agents`, resolved at 1d59ac9b by 7e7d84e1 (T-050-106) | — | F020 |
| W2 | DEL `gate-protects-nothing-without-install-ledger`, `pip-guard-fix-routes-project-installs-into-the-tool-venv`; FR `bug-proposal-handoff-reaped-without-a-hold`, `context-dead-ignores-the-hold-refusal`, `missing-venv-hook-disarms-the-gate-invisibly`, and the Q6 bug (proposed id `bugs-append-refuses-the-dot-directory-its-fix-offers`, registered in a `bug` worktree before the PLAN) | FR `dadaiaignore-and-root-core-canon`, `operator-protected-path-class`, `adr-0138-lane-in-memory-and-adrs-law`; each exits `delivered` | F015, F075, F076, F080, F082; F105 with its entry; F130 by ADR 0155 |
| W2 closure memory pass | — | — | F149: the `workspace-doctor`, `sdd-gate-v3`, `agentic-entities` and `workspace-init` atoms, rewritten once |
| Decided at this definition (grill Q1, Q5); written by the main thread after this SPEC merges | — | exit `rejected`: `gitflow-trunk-based-model`, `consumer-gitflow-server-side-enforcement`, `associated-repo-gitflow-override` (no demand); `idless-unbound-session-writes-worktrees` (ADR 0116's "only if it works well"; the gap stays stated in the law) | F138 `rejected` (`ADR: none` is legal by format) |

## Gate — rc-5's G1–G6, applied to W2

- G1 Principles, never a line-count limit (ADR 0142):
  - Every unit walks DELETE → REBUILD → UPDATE → KEEP → ADD.
  - No question gets a second decider, and no rule contradicts another.
  - Production and test line counts at `<start>` and `<end>` are logged as a readout.
- G2 `bugs.py status` lists no open record whose `caused_by` names a record or a commit of W2.
- G3 Every still-open bug is re-run at `<end>`. One that no longer reproduces is resolved, citing the commit that removed its cause. The count is logged.
- G4 CI is green on the three OSes. `.dadaia/.venv/bin/dadaia doctor --context dadaia-workspace` exits 0. The per-job wall-clock stays within ADR 0119.
- G5 A test a DEL leaves dead leaves in the same commit. A new test states its intent and passes `dd-test-stewardship`'s admission.
- G6 At closure, the open findings of `20260930-structural-convergence` and `active[]` are re-audited against the merged wave. rc-7's SPEC is re-scoped before its PLAN, and one `dispositions` log entry records the counts: open before, resolved with a commit, open after.

## W2 — acceptance

### Root canon and `.dadaiaignore`

- AC2.1 `.dadaiaignore` judges four places, and only these (0132):
  - The places are the workspace root's top level, the `.dadaia/` top level, `repos/` at its first level and `worktrees/`.
  - Only a registered context's repo is canon under `repos/`. Under `worktrees/`, only `worktrees/<r>/<name>` of an ALIVE context's repo is canon.
  - Any other entry at those places is a finding unless a `.dadaiaignore` glob names it.
  - An entry inside `.claude/`, `.codex/`, `.agents/` or another harness directory that the install ledger does not own is never judged (0059).
  - Command: `pytest tests/unit/hooks/test_root_whitelist.py tests/unit/test_spec_context_doctor_root.py`. The cases are a stray entry at each place, the same entry named by a glob, an unledgered file inside `.claude/`, and a worktree of a DEAD context's repo.
- AC2.2 `uvx dadaia-workspace init` and its re-run create `prompt.md`, `AGENTS.md` and `.dadaiaignore` at the root when they are absent, and never overwrite an existing one (0095).
  - Command: `pytest tests/integration/test_cli_init.py`, the three-file case.
- AC2.3 Core protection holds without the install ledger (DEL `gate-protects-nothing-without-install-ledger`; 0055, 0096).
  - With `.dadaia/states/install_ledger.json` absent or unreadable, an agent file-tool write is still refused to each of: the root `AGENTS.md`, `.dadaiaignore`, a harness's hook wiring (`.claude/settings.json`), a `.dadaia/hooks/` wrapper and a `.dadaia/states/` file.
  - The floor of core paths lives in code, next to level 1. The ledger adds the projected paths.
  - Command: `pytest tests/unit/features/spec_context/test_gate_policy.py tests/unit/hooks/test_pre_gate.py`.
- AC2.4 The SessionStart lane re-creates a missing level-1 core entry (`.dadaiaignore`, `prompt.md`, a provisioned `.dadaia/` zone) and rewrites no present one (0096).
  - Command: `pytest tests/integration/test_doctor_fix_lines_clear_their_finding.py`, the core case.

### DEC-11 — the protected section

- AC2.5 `.dadaiaignore` carries a protected section in its own grammar (0093, 0133):
  - Each glob is repo-relative, and an invalid line is a doctor finding.
  - The pre-gate refuses a `Write`, `Edit` or `apply_patch` to a match under `repos/<r>/` and under every `worktrees/<r>/<name>/` (0114), in each harness dialect.
  - The refusal names the operator as owner, and its `fix:` line points to `.dadaia/tmp/<agent>/<date>/`.
  - An unprotected sibling path is allowed.
  - Command: `pytest tests/unit/hooks/test_pre_gate.py tests/unit/features/spec_context/test_gate_policy.py`.
  - F082: 0114 is realized through DEC-11.
- AC2.6 The root map §3 states that no tool, Bash included, writes a protected path, and that the rule is not enforced for Bash (0096, 0133).

### Fail-open, stated and seen

- AC2.7 With `.dadaia/.venv` absent (FR `missing-venv-hook-disarms-the-gate-invisibly`; 0067):
  - Every hook still lets the action through.
  - Once per session, the first hook that fires sends the agent, through the harness's context channel and not stderr alone, one message naming the gate's absence and `fix: uvx dadaia-workspace init <ws>`.
  - Command: `pytest tests/contract/test_hook_behaviour_coverage.py`, the missing-venv case, per harness.
- AC2.8 One statement of the three fail-open paths (F080):
  - The paths are a missing venv (0067), a pre-gate past its 10 s timeout (0118) and a Bash write (0096, 0103).
  - They are listed in one place in the law, and no other law file restates them.
  - Command: `pytest tests/contract/test_law_states_what_the_code_does.py`.
- AC2.9 The venv guard judges only the dadaia CLI (DEL `pip-guard-fix-routes-project-installs-into-the-tool-venv`; 0134):
  - `pip install requests` is allowed.
  - `dadaia doctor` run outside `.dadaia/.venv/bin/` is refused, naming the venv path.
  - The root map §3 names no `pip`.
  - Command: `pytest tests/unit/hooks/test_pre_gate.py`.

### One deleter

- AC2.10 A no-operator bug proposal survives until it is seen (FR `bug-proposal-handoff-reaped-without-a-hold`):
  - Setup: a handoff whose finding `message` starts `bug-proposal:`.
  - After `doctor --fix --expired-only` runs past the handoff TTL, the file still exists, either at its handoff path or held under `.dadaia/reaped/`.
  - `doctor` names it in one finding until it is consumed.
  - No reaper branch keys on a handoff's content (G1). The as-is review picks the structural shape.
- AC2.11 `context dead` exits non-zero with the refusal `sweep.hold` returns when the hold of a repo does not happen, and the context stays ALIVE (FR `context-dead-ignores-the-hold-refusal`).
  - Command: `pytest tests/integration/test_context_dead_holds.py`.
- AC2.12 F015 is resolved by AC2.1–AC2.11. `doctor --fix`, the SessionStart lane and `context dead` remove a live entry only through `sweep.hold`, and a TTL expiry is the only direct deletion.

### Grill rulings (Q2–Q4, Q6) and the ADR 0138 lane

- AC2.13 Onboarding writes (ADR 0154, once accepted):
  - The root map §3 names `context create` and the first `specs init` as the only direct writers of a repo's `specs/` beside `specs/audits/**`, in place of "§7's CLI verbs own theirs".
  - `docs/quickstart.md` and `docs/getting-started.md` run the first `backlog.py new` and `release.py new` inside a `backlog` and a `release` worktree, after `context baseline`.
  - Command: `pytest tests/contract/test_law_states_what_the_code_does.py`.
- AC2.14 Playwright MCP output leaves the root (Q3):
  - For the `claude` harness, `public install` and `init` project `PLAYWRIGHT_MCP_OUTPUT_DIR=<absolute ws>/.dadaia/mcps/playwright` into `.claude/settings.json` `env`, beside the cache keys.
  - Keys the operator set there are kept.
  - Command: the owner test of `infrastructure/runtime_config.py`'s env merge, which the PLAN names (ADR 0146 (5)). Today `tests/integration/test_tool_caches_stay_in_the_tmp_zone.py` asserts the projected cache keys.
- AC2.15 QUALITY P-27 is gone (ADR 0155, once accepted). `grep -c '^### P-27' specs/memory/QUALITY.md` prints 0, in the commit that accepts 0155, and no pyramid-share test returns (F130).
- AC2.16 The ADR 0138 lane is stated in law (backlog `adr-0138-lane-in-memory-and-adrs-law`):
  - `public/scaffold/memory/AGENTS.md` §1 and `public/scaffold/ADRs/AGENTS.md` §2 each state it: a commit that changes a non-principle section of `ARCHITECTURE.md` or `QUALITY.md` only to state what the code is needs no ADR and names its code evidence, while a `### P-NN` principle still needs its accepted ADR.
  - At closure, the `specs/*/AGENTS.md` copies are re-rendered in the release worktree (0148 (7)), and the doctor shows no template drift.
- AC2.17 `bugs.py append` admits a tracked dot-directory (the Q6 bug):
  - In a repo that tracks `.github/`, `append --surface .github` succeeds.
  - A name that is no tracked directory is still refused, naming close matches.
  - The set of tracked directory names is the one decider, and the separate name regex is deleted.
  - Command: `pytest tests/unit/skills/test_bug_resolution_bugs_script.py`.

## Operator acts (recorded, not tasks)

- Q3:
  - Move the AWS-docs MCP server to Claude's local scope (`claude mcp add --scope local …`), then delete `.mcp.json`.
  - Drop the `.mcp.json`, `.playwright-mcp` and `QUESTIORNARY.md` lines from `.dadaiaignore`.
  - Rule on `.vscode`: add a line for it, or let `doctor --fix` hold it.
  - Once AC2.14 lands and the line is gone, `doctor --fix` holds the existing `.playwright-mcp/`.
- ADRs 0154 and 0155: the operator's ruling, transcribed by the main thread.

## Replaces

- PROTECTED derived only from the install ledger (the ledger stays a source; the floor moves to code).
- The venv guard's pip arm, and the pip clause of the root map §3.
- The hook wrappers' stderr-only warning about a missing venv.
- The reaper's direct deletion of an expired bug-proposal handoff.
- `context dead`'s discarded hold refusal.
- `bugs.py append`'s surface regex (`^[a-z0-9_-]+$`).
- The root map's "§7's CLI verbs own theirs", and the quickstart's direct `backlog.py new`/`release.py new` writes.
- QUALITY P-27.
- ADR 0092's harness-directory clause (void by 0132).

## Risks

| Weakness | Mitigation |
|---|---|
| Core paths listed in code drift from what `public install` projects. | The code floor is a subset that the ledger extends. A contract test checks that every floor path is one that `install` writes or that `init` creates. |
| A protected glob matches too wide and refuses the agent's real work. | The fix line routes the draft to `.dadaia/tmp/`. The doctor names every glob together with the paths it matches. |
| The once-per-session venv message needs a session id, and there is no venv to read one with. | The wrapper's prologue decides with no Python. The as-is review measures each harness's context channel before the PLAN. |
| Holding expired handoffs grows `.dadaia/reaped/`. | The reaped TTL (7 days) bounds it. The G1 readout logs the size. |
| The quickstart's worktree path needs the work branch before the first backlog entry. | `context baseline` publishes every gitflow branch, and the quickstart runs it first. |

## Carried to candidates 7+ (ADR 0140; specified by their own SPECs)

Candidate map (soft size, ADR 0152 (2)); the main thread's proposal, not an operator ruling on the grouping:

| candidate | contents |
|---|---|
| rc-7 | W3 + W4 |
| rc-8 | W5 + W6 |
| rc-9 | W7 + Promote PR |

| Target | Bugs | Backlog | Findings, carry-overs |
|---|---|---|---|
| W3 one grammar owner (0135, 0137, 0127 release-traceability clause) | DEL `spec-origin-line-has-two-readers`, `task-line-grammar-accepts-a-malformed-open-marker`, `privacy-denylist-has-two-loaders`, `release-ship-accepts-what-release-check-refuses`, `bugs-check-trusts-evidence-fields-unverified`, `release-new-crashes-on-a-unicode-line-separator-in-the-bug-ledger`, `corrupt-context-registry-crashes-doctor-and-next-step`; FR `list-form-privacy-denylist-errors-without-migration`, `secret-scan-misses-github-pat-and-anthropic-keys` | `ledger-schema-one-engine`, `structural-convergence-f053-f054-f057`; exit `to-bug` `task-line-grammar-one-reader` → `task-line-grammar-accepts-a-malformed-open-marker` | F002, F010, F012, F013, F016, F052, F058, F059, F061, F063; c4 AC6.3, AC6.6 (V38) |
| W4 one text renderer | DEL `dadaia-bin-still-honoured-after-adr-0045`, `help-examples-spell-the-blocked-bare-cli`, `fix-lines-are-not-one-runnable-command`, `ledger-finding-fix-line-orders-a-hand-edit-the-law-forbids`, `implementer-persona-states-a-second-task-marker-lifecycle` | `consumer-guidance-names-no-library-toolchain` | F007, F017 |
| W5 one test child-env builder | DEL `test-suite-writes-outside-tmp`; FR `ci-preflight-writes-coverage-into-the-repo`, `default-suite-calls-a-real-model-through-codex`, `hook-entrypoints-invisible-to-coverage` | `preflight-ci-parity-derived`, `test-intent-docstring-backfill` | F018, F135, F136; c4 AC9.5, AC9.11 |
| W6 local fixes in severity groups (0123) | FR `onboarding-next-step-names-another-context`, `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original`, `pre-push-warns-no-gitflow-block-for-an-absent-specs-tree`, `upgrade-leaves-reconcile-scratch-behind` | `doctor-context-ignores-other-contexts`, `release-memory-idempotent`, `guidance-messages-name-the-right-target`, `init-announces-codex-trust`, `tests-agents-scaffold-without-placeholders` (each an FR, exit `delivered`, no new bug record) | — |
| W7 docs site (0039), clone detection as V37 rebuilt, launch-act preparation D3–D6, truth-only lane (0138), memory drift | FR `removals-shipped-without-recorded-authority` | `docs-site-zensical-pages`, `clone-detection`, `launch-operator-acts` | F001, F003–F005, F009, F060, F069, F084, F088, F089, F113–F116, F119–F121, F123–F129, F131–F134, F137, F139–F148; c4 AC10.1, AC10.2 |
| Promote PR (0122) | `bugs.py status` → `[ok] 0 open bug(s).` | `active[]` is `[]`, and `backlog.py check` passes | F067: `audit.py check` shows no `open` finding and the audit is closed; the rubric D1–D10 logged as a readout |

Risk seeds for W3 (from rc-5), so they are not lost:
- ADR 0135:
  - Keep owner scripts off the pre-gate path.
  - The package imports its own `public/skills` copy.
  - A script crash fails soft into one finding (F024).
  - A contract test pins where each owner script lives.
- ADR 0137:
  - The registration and the exit share one backlog worktree.
  - `backlog.py` imports `bugs.py`'s record reader.
  - A rejected target bug is reported by `release.py check`.

## Open questions for the operator

- OQ1 (Q3 against ADR 0146 (3)): 0146 (3) says the library keeps MCP config out and "only says MCP lives in `.dadaia/mcps/`". AC2.14 makes the library project one MCP server's output directory. Should a record amending 0146 (3) be proposed, or does the Q3 answer stand as that amendment?
- OQ2 (F075, Q10(a) of the audit, never ruled on its own): AC2.7 follows the operator-confirmed `expected` of `missing-venv-hook-disarms-the-gate-invisibly` (fail-open, visible once per session, fix `uvx dadaia-workspace init <ws>`) rather than failing closed. Confirm.
