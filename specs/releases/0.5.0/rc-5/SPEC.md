# SPEC — Release: 0.5.0, candidate 5 (priority: worktrees and bind)

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-product-engineer
**Opened:** 2026-09-30
**Origin:** backlog:canonical-worktrees,worktree-harness-mechanics-study,bind-scope-durable-on-every-harness,ctx-inject-on-cursor-copilot
- Sources:
  - audit `20260930-structural-convergence` (ADR 0121 as amended by 0140);
  - grill round 2 (ADRs 0121–0138, handoff `2026-09-30T022849Z-main-thread-remediation-grill-r2-adrs`);
  - ADR 0140.
  - Operator demand, 2026-09-30: ADR 0150 ("não é nem permitido pela minha lei criar uma release plana"); ADR 0151 ("crie mecanismos claros para isso nunca mais acontecer"; "Aprovo os 5"); ADR 0152 ("desfaça o que eu não pedi diretamente e agente criou como slop"; "sem teto rigido. soft teto. recomendação").
- Operator, 2026-09-30: "devemos implementar toda parte que toca worktrees e bind primeiro numa rc prioritária. e as seguintes garantir que já estamos usando worktrees plenamente, bem como o bind." Stop producing bugs; deliver the release.
- This candidate registers no bug and adds no backlog entry.
- The header is the pick `backlog.py exit` reads. It names only this candidate's deliveries; each later candidate's header names its own.
- The §Origin map and §Carried give each of the 33 open bugs, 23 active entries and 150 findings exactly one destination.

## Objective

- Build canonical worktrees and a bind that is context plus a path-derived write scope.
- Build them first, so that every later 0.5.0 change is defined, implemented, registered and merged inside worktrees by bound sessions (ADR 0140).
- Delete the per-session scope machinery these replace.

## Terms

- `CONTEXT.md` holds the terms.
- **W1** is this candidate.
- **W2–W7** are the target waves of candidates 6+ (§Carried), each gated per §Gate. Inside W6, `CONTEXT.md`'s harm-ordered sense of **Wave** applies.
- **DEL**: the bug is resolved by `bugs.py resolve` citing the commit that deleted its surface; a bug a task fixes resolves in a bug worktree (0148 (2)).
- **FR**: the item is delivered by ACs.

## Decisions

- These ADRs decide: 0097, 0099, 0100, 0103, 0105–0117, 0124–0131, 0135 (read path only), 0136, 0140, 0141, 0147, 0148, 0150, 0151, 0152.
- The PLAN carries the Parallel schedule of ADR 0141 from the task after `worktree.py merge`; closure logs planned against measured width, the critical path walked and every rebase conflict.
- A reader imports the owner script's read-only parser (0135): `worktree.py` imports `release.py`'s status parser, `backlog.py` imports `bugs.py`'s record reader. Running another script's verb stays forbidden (0018). ADR 0126's `measured_by` is repaired to match ("chore(adrs): repair 0126 measured_by").
- A backlog entry that is a contract break is delivered as an FR of the candidate owning its cause and exits `delivered`, with no new bug record (operator). `to-bug` (0137) stays for future cases.
- An ADR beats an audit proposal:
  - 0105 keeps 0072 (F070);
  - 0113 keeps one venv over the study's per-worktree venv;
  - 0140 moves 0114's library layer to DEC-11 in candidate 6.
- Bugs follow ADR 0123: shared causes are fixed together, and every still-open bug is re-evaluated at the close.
- A fix follows ADR 0136: one bug worktree, one commit, the RED run quoted in the body.

## Origin map — candidate 5

F019–F051 share the destination of the bug each cites. F090–F112 share the destination of the entry each cites. Every other id is listed once, here or in §Carried.

| Where | Bugs | Backlog | Findings |
|---|---|---|---|
| Resolved by records already made; dispositioned at this closure | — | — | F006 (meets target), F062, F064 (`0d31a5f2`), F065, F066, F077, F078, F081; F086, F087 (`8af81e07`) |
| W1 | DEL `unbound-native-session-writes-freely-into-repos` (HIGH), `additive-globs-hand-kept-beside-the-canon`; FR `fenced-roots-env-disables-the-gate`, `corrupt-session-record-never-collected` | FR `canonical-worktrees`, `worktree-harness-mechanics-study`, `bind-scope-durable-on-every-harness`, `ctx-inject-on-cursor-copilot`; exit `rejected` `gate-judges-bash-writes` (0096, 0103) | F008, F011, F014, F053–F057, F068, F070–F074, F079, F083–F085 |
| W1 closure memory pass | — | — | F150, with F117, F118, F122 folded in |

## Gate — this candidate, and every later wave

- G1 Principles, never a line-count limit (ADR 0142):
  - Every unit walks DELETE → REBUILD → UPDATE → KEEP → ADD, and an ADD names what it could not delete or rebuild.
  - No question gets a second decider, and no rule contradicts another (the review's bug-surface axis judges it).
  - Modules keep clean, narrow boundaries.
  - Production and test line counts at `<start>` and `<end>` are logged in `_RELEASE.json` as a readout, `worktree.py` apart.
- G2 `bugs.py status` lists no open record whose `caused_by` names a record or a commit of the wave.
- G3 Every still-open bug is re-run at `<end>`. One that no longer reproduces is resolved, citing the commit that removed its cause. The count is logged.
- G4 CI is green on the three OSes. `.dadaia/.venv/bin/dadaia doctor --context dadaia-workspace` exits 0. The per-job wall-clock stays within ADR 0119.
- G5 A test that a DEL leaves dead leaves in the same commit; a new test states its intent and passes `dd-test-stewardship`'s admission.

## W1 — scope, bind, worktrees

### Scope and bind

- AC1.1 One decider, `scope(target) -> (repo, zone)`, zone ∈ root|repo|audit|worktree (never "kind", which names the four worktree kinds); a path under `worktrees/<r>/` belongs to `r`.
  - A bound file-tool write under `repos/<r>/` outside `specs/audits/**` is refused with `fix: worktree.py new <r> --kind <kind>`, the kind from `kind_holding()` in `_worktree_kinds.py`; a path no kind holds gets an `Operator action:` fix.
  - The same write is allowed under `worktrees/<r>/<name>/` and under `repos/<r>/specs/audits/` (0124).
  - An unbound session with a native id is refused under both, with the `context bind` fix (0072).
  - An unbound session with no native id and no `DADAIA_SESSION_ID` is not refused under `worktrees/<r>/`. This is a declared gap: refusing it would be a Stall, because the harness process env is not the shell env (0116). A write under `repos/<r>/` is refused for every session (0105).
  - `pytest tests/unit/features/spec_context/test_gate_policy.py tests/unit/hooks/test_sdd_gate.py` passes.
  - The row `unbound-session-never-scope-blocked` (`test_gate_policy.py:83`) and the always-writable ledger rows are rewritten to the refusals above. Restoring the unbound ALLOW fails them (F070).
  - `git grep -nE 'SPECS_ADDITIVE_GLOBS|_is_specs_additive|_scope_block' -- dadaia_workspace` prints nothing. One path-to-repo decider remains: `core/invocation.py` and `hooks/sdd_gate.py` today.
- AC1.2 The bound injection carries `constitution.md` on every harness, Cursor and Copilot included (0103).
  - With no native id and no `DADAIA_SESSION_ID`, bind exits non-zero with the export fix (0116).
  - Gate and bind read the session id from the environment only; `context bind --print-env` is deleted (0148 (4)).
  - `pytest tests/integration/test_one_bind.py tests/e2e/features/test_ctx_inject_bind_boundary.py tests/contract/cli/test_cli_context.py tests/unit/core/test_invocation.py` passes.
  - `.dadaia/.venv/bin/dadaia public doctor` is clean.
- AC1.3 With `DADAIA_FENCED_ROOTS` naming the workspace, a PROTECTED write is still refused (F079).
- AC1.4 A corrupt `.dadaia/sessions/<id>.json` is reported once, and `doctor --fix` holds it.
- AC1.5 The root map §3 states the always-on rule: no out-of-scope and no protected-path write by any tool, Bash included, and Bash is never judged by the gate (0103) (F074).
- AC1.6 `worktrees/` is a level-1 root entry in `core/workspace_layout.py` (the slice of 0094 this candidate needs).
  - The gate allows a scoped file-tool write under it.
  - `doctor --fix` never moves anything under it.
  - The root map §4 lists it.

### Worktrees

- AC1.7 `worktree.py new` (0107, 0125, 0129):
  - It branches `wt/<M.m.p><letter>-<kind>` from the HEAD of `feature/<M.m.p>`. Without a work branch it refuses with a fix that creates one. At a promote, gitflow step 11 cuts the next work branch, by default the next patch.
  - It refuses `impl` unless the trio reads Approved, judged by `release.py`'s status parser, imported (0135).
  - It caps `impl` at 5 per repo and release, `release` at 1 per repo and version, and letters past `z` (F083). Each refusal's fix names an existing worktree's merge or clean.
  - It locks the worktree with `dadaia:<kind>:<id>`.
  - It writes the JSONL union lines to `.git/info/attributes` idempotently.
  - It refuses a symlinked `worktrees/` component and rolls back a half-created worktree.
  - Command: `pytest tests/integration/test_worktree_new.py`.
- AC1.8 `worktree.py merge|clean` (0109, 0110, 0126, 0130):
  - `merge` refuses, each time with one executable `fix:`:
    - a dirty tree;
    - a file outside the kind's allowed set (0106; the backlog set is `specs/backlog/**`, `_archive` included, per 0124);
    - a conflicting rebase;
    - a missing or other-sha APPROVED handoff (`reports validate <handoff>`);
    - a failed fast-forward;
    - an ignored file outside the disposable list (`--keep`/`--drop`).
  - The merge runs fast-forward, then remove, then `branch -d`. Never `--force` or `-D`, and it re-runs after an interruption.
  - `clean` removes only a merged or commit-less `dadaia:`-locked worktree.
  - `worktree.py` runs no other script's verb. It imports only owner parsers (0135).
  - Command: `pytest tests/integration/test_worktree_lifecycle.py` (the owner file, ADR 0146 (5)).
- AC1.9 Parallel worktrees (0111):
  - JSONL ledgers merge by union, and the ledger check refuses a duplicate id.
  - TASKS markers replay, and the most advanced state wins.
  - Command: `pytest tests/integration/test_worktree_lifecycle.py`.
- AC1.10 Hygiene, read from git alone (0108, 0112, 0128, 0100):
  - At SessionStart and compaction, the doctor lists the context's open worktrees: kind, age, commits ahead, dirty or clean.
  - A ready worktree carries `fix: worktree.py merge <path>`. One older than a day gets a WARN.
  - An orphan `wt/*`, an unregistered worktree and a harness-native worktree in conflict are findings, never touched.
  - One authority: `worktree.py`'s rows carry each state and its one exit (`merge`, or `clean` when nothing is ahead); the doctor and `context dead` read them through the package reader, and closure imports the row builder (0135), never running another script's verb (0018).
  - Release closure and `context dead` are refused while any `wt/*` exists; closure excludes the one it runs in (0148 (3)). No Stop hook.
  - Nothing is written under `.dadaia/states/`.
  - Command: `pytest tests/integration/test_context_dead_holds.py tests/integration/test_reaper_spares_linked_worktrees.py`, plus a closure-refusal test.
- AC1.11 One venv (0113): a subprocess test, run by `repos/dadaia-workspace/AGENTS.md`'s worktree command, imports `dadaia_workspace` from the worktree (asserted on `__file__`). `find worktrees -name .venv` prints nothing.
- AC1.12 Correlation at registration (0127, bug and backlog clauses):
  - `bugs.py append` enforces the `surface` enum (F011).
  - It lists open records on the same surface and those resolved there in the last 30 days.
  - It refuses a record without `--correlates <ids>|none`.
  - `backlog.py new` requires the entries it updates, obsoletes or relates to.
  - `dd-code-review` holds one checklist row per worktree kind.
  - These clauses read no Origin line. The release-traceability clause is carried to W3, after the Origin grammar has one owner.

### Law, bootstrap, migration

- AC1.13 One home per rule (0115, 0136):
  - `public install` projects `worktrees/AGENTS.md`, the one home of the worktree rules (ADR 0146 (4)). The root map gains the `worktrees/` lines in §3, §4 and §5.
  - Only `worktrees/AGENTS.md` and `dd-gitflow-default` name `scripts/worktree.py`; the seven skills carry one pointer line each to `worktrees/AGENTS.md` (contract test).
  - The §3a shape table becomes the kinds' allowed sets. A bug worktree holds one fix commit (code, test, resolve lines, RED quoted), or, for a bug a task fixed, one resolve commit (0148 (2)); §3a row 4 is rewritten to it. `dd-bug-resolution`'s separate RED commit is deleted (F053–F057, F008).
  - HTML reports live in `.dadaia/reports/<ctx>/`, an OUTPUT zone never reaped that the gate allows (0147 (1)); `.dadaia/mcps/` is an operator zone (0148 (6)); `tests/contract/test_zone_registry.py` passes and `git grep -nE 'reports/<agent>|reports/dd-' -- dadaia_workspace/public` prints nothing.
  - No law or recipe calls a `repos/<r>/specs/` path ADDITIVE (0124); audits are written directly by a bound session. Measured by `tests/contract/test_law_states_what_the_code_does.py`.
  - `CONTEXT.md` gains **Worktree**, **Worktree kind** and **Zone**, and its **Scope** and **Bind** entries are rewritten.
  - `dd-release-definition` §5 and `specs/releases/AGENTS.md` §3 state ADR 0141: one impl worktree per task, true `blocked by:` edges, exact `W:`, and a PLAN "Parallel schedule" (steps, width, critical path). `release.py check` refuses a PLAN without it, and two tasks in one step whose `W:` overlap outside the union/replay files and the derived `behavior-map.json` (0148 (5)).
- AC1.14 Bootstrap (0140): once the `new` and `merge` tasks land, every later task of this candidate is made in a worktree. Every `git -C repos/dadaia-workspace reflog feature/0.5.0` entry after that commit reads `merge wt/…: Fast-forward`, except T-050-106 and its two CI test fixes, the by-hand bootstrap of ADR 0145 that made `worktrees/` canon first.
- AC1.15 Migration, after AC1.14, in ADR 0131's order:
  - `git -C repos/<r> worktree list --porcelain` names only `worktrees/<r>/<name>`. The three worktrees in another session's `/tmp` are excepted until the operator confirms.
  - `git ls-remote --tags origin 'archive/*'` names each discarded branch (F068, F085).
  - A consumer worktree's protected folder is checked first. A dirty one stays the operator's.
- AC1.16 Closure (0140):
  - The main-thread session is bound: `context show --json` names `dadaia-workspace`.
  - The memory pass, the `_RELEASE.json` log and the ledger dispositions each land through their kind's worktree; audit dispositions land directly (0124).
  - Closure's release worktree is the one that writes candidate 6's SPEC (cap 1). It also copies `public/scaffold/*/AGENTS.md` over the `specs/*/AGENTS.md` copies inside that worktree after T-050-103 (0148 (7); the doctor only measures) and repairs ADR 0027's title in place (F084); `dadaia doctor --context dadaia-workspace` then shows no template drift.
  - `release.py check` passes.
  - Candidate 6's SPEC is written in `worktrees/dadaia-workspace/0.5.0<letter>-release` and lands by `worktree.py merge`; its reflog line proves it.

### Amendments 3–5 (ADRs 0150, 0151, 0152)

- AC1.17 Every candidate in `rc-<N>/` (0150, 0152; T-050-109):
  - (1) `release.py new` writes the trio into `releases/<v>/rc-<N+1>/`. No verb rewrites a closed `rc-<N>/`; the one move is (5)'s promote archive.
  - (2) Only `_RELEASE.json` sits at the release root; the canon and pre-push refuse a flat trio (0151 M5).
  - (3) The live candidate (highest open `rc-<N>/`) is resolved by the PINNED PAIR `_release_store.live_ids` (stdlib scripts) ↔ `core/gitflow.py` `resolve_live_release_id` (package); one contract test in `tests/contract/test_release_script.py` sends the same trees to both and asserts equal answers.
  - (4) Data: `rc-1`..`rc-4` equal `git show` of the trio at f61be1a0, acd8443a, 96d8f9ee, 47858cf8; the live trio is `git mv`-ed to `rc-5/`.
  - (5) At promote, `release.py ship` moves the whole release folder (`_RELEASE.json`, `rc-1`..`rc-<n>`) to `releases/_archive/<v>/` and deletes nothing: after it, `git ls-tree -r HEAD specs/releases/_archive/<v>/` lists every file the folder held (0152 (1)).
  - (6) SPEC/TASKS size is a recommendation: no check refuses an oversized trio, and `pub/scaffold/releases/AGENTS.md` says past it the next work opens `rc-<N+1>/` (0152 (2)).
  - (7) A live `releases/<v>/RELEASE.json` gets the WARNING SPEC-DOC-046 with one `fix:` line, and `doctor --fix` renames it to `_RELEASE.json` (ADR 0007, restored by 0152 (4); deleted by f7cc8621).
  - Command: `pytest tests/contract/test_release_script.py tests/unit/skills/test_release_implementation_release_script.py tests/unit/features/specs/test_release_tree.py tests/unit/features/specs/test_doctor.py tests/unit/core/test_release_state_filename.py`; `release.py check` passes.
- AC1.18 Only the operator accepts (0151; T-050-110):
  - M1 LEDGER-ADR-SCHEMA refuses an `accepted` record without `ruling: {date, words}`, or whose `ruling.words` reads delegated or "in session"; it judges `ruling.words` only, never `context`.
  - M2 It refuses a non-`rejected` record superseding or amending an accepted one unless itself accepted with a ruling; a `rejected` record is not judged.
  - M3 pre-push refuses a pushed commit deleting an `AGENTS.md`/`SKILL.md` line whose message cites no `ADR NNNN`, with one `fix:`.
  - M4 The three role personas and the root map point to `specs/ADRs/AGENTS.md` §2: no role agent writes `accepted` or `ruling`.
  - Data: the 12 records accepted without the operator's order are `rejected` (1894ab74, 0152 (3)). Before the batch push, each still-`accepted` record gets `ruling.words` = the operator's verbatim quote, or his recorded grill answer id, taken from its own `context`; never composed. An accepted record whose `context` holds neither returns to `proposed` until the operator rules; 0007 is the known case.
  - Command: `pytest tests/contract/test_adr_canon.py tests/unit/features/chokepoints/test_push_specs_canon_scan.py`; `doctor --context dadaia-workspace` exits 0.

Study conclusions carried (ADR 0100; the scratch copy is ephemeral):
- A `wt/` branch is always named, never a detached HEAD.
- A worktree is destroyed only after a verified fast-forward: never by TTL or count.
- The doctor reports and never prunes.
- No worktree lives under a TTL zone.
- Hooks resolve from the workspace root.
- `GIT_*` variables are scrubbed before any tool-driven git.

## Replaces

- `sdd_gate`'s unbound ALLOW.
- `gate_policy` `bound_*` and `_scope_block`.
- The second path-to-repo decider.
- `SPECS_ADDITIVE_GLOBS` and its always-writable ledgers under `repos/<r>/`.
- The second session-id reader: the gate and bind read one id, environment first (the 1a27ae1f lesson; bind no longer invents a `sess_*` id).
- "One `[-]` at a time unless TASKS declares disjoint write sets" (`specs/releases/AGENTS.md` §3), replaced by ADR 0141's schedule.
- ADR 0098's split.
- Worktrees under `.dadaia/tmp` and `/tmp`.
- The §3a shape table.
- The separate RED commit.
- `session_store`'s "an unreadable record is never stale".
- `context bind --print-env` (0148 (4): an env-only id leaves it nothing to print).
- The flat trio each candidate overwrote (0150); acceptance by an agent (0151).

## Risk registers

**ADR 0125 — base, impl precondition, caps**

| Weakness | Mitigation |
|---|---|
| A bug found between a promote and the next definition has no work branch. | Gitflow step 11 cuts the next work branch at the promote, by default the next patch. |
| A long-lived worktree drifts. | The WARN after one day and the same-session merge law (0128). Conflicts are resolved inside the worktree. |
| A trio amended after approval leaves impl worktrees on an older SPEC. | The rebase brings in the new SPEC. The impl review row judges the whole SPEC as merged (0127). |
| A cap refusal when no worktree is ready risks a Stall. | The fix names the oldest worktree's exit: `clean` when nothing is ahead, else `merge`, whose refusal names `reports validate <handoff>`. Review is the one step that is not a command (0126). |
| An associated repo's version differs from the release's. | Its own work branch names the worktree. The impl precondition reads the main repo's trio. |
| The precondition needs `release.py`'s Status parser. | It is imported read-only (0135); there is no second reader and no script runs another's verb. |

**ADR 0127 — correlation at registration**

| Weakness | Mitigation |
|---|---|
| `--correlates none` can be written blindly. | `append` prints the candidates first. The bug review row judges them at merge. |
| A free-text surface defeats "same surface". | The enum is enforced first (AC1.12, F011). |
| The 30-day window is arbitrary. | It is a starting value, tuned by the next audit. |
| The release clause needs the Origin grammar, whose second reader is an M3 bug. | The clause is carried to W3. The header stays `backlog:` only until then. |
| A backlog exit writes `backlog_histo.jsonl`. | The backlog set is `specs/backlog/**`, `_archive` included (0124). |

**Cross-candidate:**
- Worktrees open before DEC-11. Until candidate 6, the instance `permissions.deny` is the only layer protecting operator paths under `worktrees/` (0114, 0140).
- The root canon beyond AC1.6 waits too, so a stray entry under `worktrees/` goes unjudged until 0132 lands.

## Carried to candidates 6+ (ADR 0140; specified by their own SPECs)

Each item is listed once, at its target wave.

| Target | Bugs | Backlog | Findings, carry-overs |
|---|---|---|---|
| W2 root canon, `.dadaiaignore`, DEC-11 and 0114's library layer, one deleter (0092–0096, 0132–0134) | DEL `instance-exceptions-file-writable-by-agents`, `gate-protects-nothing-without-install-ledger`, `pip-guard-fix-routes-project-installs-into-the-tool-venv`; FR `bug-proposal-handoff-reaped-without-a-hold`, `context-dead-ignores-the-hold-refusal`, `missing-venv-hook-disarms-the-gate-invisibly` | `dadaiaignore-and-root-core-canon`, `operator-protected-path-class` | F015, F075, F076, F080, F082 |
| W3 one grammar owner (0135, 0137, 0127 release-traceability clause) | DEL `spec-origin-line-has-two-readers`, `task-line-grammar-accepts-a-malformed-open-marker`, `privacy-denylist-has-two-loaders`, `release-ship-accepts-what-release-check-refuses`, `bugs-check-trusts-evidence-fields-unverified`, `release-new-crashes-on-a-unicode-line-separator-in-the-bug-ledger`, `corrupt-context-registry-crashes-doctor-and-next-step`; FR `list-form-privacy-denylist-errors-without-migration`, `secret-scan-misses-github-pat-and-anthropic-keys` | `ledger-schema-one-engine`; exit `to-bug` `task-line-grammar-one-reader` → `task-line-grammar-accepts-a-malformed-open-marker` | F002, F010, F012, F013, F016, F052, F058, F059, F061, F063; c4 AC6.3, AC6.6 (V38) |
| W4 one text renderer | DEL `dadaia-bin-still-honoured-after-adr-0045`, `help-examples-spell-the-blocked-bare-cli`, `fix-lines-are-not-one-runnable-command`, `ledger-finding-fix-line-orders-a-hand-edit-the-law-forbids`, `implementer-persona-states-a-second-task-marker-lifecycle` | `consumer-guidance-names-no-library-toolchain` | F007, F017 |
| W5 one test child-env builder | DEL `test-suite-writes-outside-tmp`; FR `ci-preflight-writes-coverage-into-the-repo`, `default-suite-calls-a-real-model-through-codex`, `hook-entrypoints-invisible-to-coverage` | `preflight-ci-parity-derived`, `test-intent-docstring-backfill` | F018, F130 (restore P-27's measure or retire it by ADR: decided at candidate 6's definition), F135, F136; c4 AC9.5, AC9.11 |
| W6 local fixes in severity groups (0123) | FR `onboarding-next-step-names-another-context`, `init-on-a-copied-workspace-leaves-a-cli-bound-to-the-original`, `pre-push-warns-no-gitflow-block-for-an-absent-specs-tree`, `upgrade-leaves-reconcile-scratch-behind` | `doctor-context-ignores-other-contexts`, `release-memory-idempotent`, `guidance-messages-name-the-right-target`, `init-announces-codex-trust`, `tests-agents-scaffold-without-placeholders` (each an FR, exit `delivered`, no new bug record) | — |
| W7 docs site (0039), clone detection as V37 rebuilt to catch divergent copies, launch-act preparation D3–D6, truth-only lane (0138), memory drift | FR `removals-shipped-without-recorded-authority` | `docs-site-zensical-pages`, `clone-detection`, `launch-operator-acts` | F001, F003–F005, F009, F060, F069, F088, F089, F113–F116, F119–F121, F123–F129, F131–F134, F137, F139–F149; c4 AC10.1 and AC10.2 (production +313 lines, tests +3,459) |
| Decided at candidate 6's definition | — | `gitflow-trunk-based-model` (0037), `consumer-gitflow-server-side-enforcement` (0040), `associated-repo-gitflow-override` (0046): `rejected` proposed, no demand vs 0122's "everything stays" | F138: `rejected` proposed (`ADR: none` is legal by format) |
| Promote PR (0122) | `bugs.py status` → `[ok] 0 open bug(s).` | `active[]` is `[]`, and `backlog.py check` passes | F067: `audit.py check` shows no `open` finding and the audit is closed; the fenced rubric D1–D10 is logged as a readout |

Risk seeds for candidate 6, so they are not lost:
- ADR 0135:
  - **Subprocess cost.** Keep owners off the pre-gate path.
  - **Import path.** The package imports its own `public/skills` copy, never the projected one.
  - **Script crashes.** A crash fails soft into one finding (F024).
  - **Pin the location.** A contract test pins where each owner script lives.
- ADR 0137:
  - **Pairing.** The registration and the exit share one backlog worktree; the set is `specs/backlog/**` plus the appended `BUGS.jsonl` line.
  - **Reading the bug id.** `backlog.py` imports `bugs.py`'s record reader (0135).
  - **Rejected targets.** A target bug that is later rejected is reported by `release.py check`.

## Open questions

None for candidate 5.
