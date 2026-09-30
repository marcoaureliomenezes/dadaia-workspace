# PLAN — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

Candidate 5 — "priority: worktrees and bind" (ADR 0140). SPEC W1, AC1.1–AC1.16. Paths are relative to
`dadaia_workspace/` (`f/` = `features/`, `pub/` = `public/`, `wt.py` = `pub/skills/dd-gitflow-default/scripts/worktree.py`)
unless they start with `tests/`, `specs/`. As-is read at `feature/0.5.0` HEAD (package: 23,793 lines, `git grep -h '' HEAD -- 'dadaia_workspace/*.py' | wc -l`).

## 1. As-is review

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `hooks/sdd_gate.py:54-56` unbound ALLOW | a MUTATING write with no resolved context returns ALLOW before any scope check | 3 (`unbound-native-session-writes-freely-into-repos` open; `sa-bind-has-two-stores`; `sa-gate-path-classes-diverge-from-the-law`) | DELETE | the lease-era fail-open (`db7aecbe`) that overrides ADR 0072 |
| `hooks/sdd_gate.py:17-23` `_target_slug` | second path→repo decider beside `core/invocation.py:165` `repo_slug_under_repos` | ″ | DELETE | two deciders for one question |
| `hooks/sdd_gate.py:26-69` `_evaluate_target` | resolves Invocation, ledger, class, owner; passes 6 bind fields to policy | 5 (above + `sa-gate-blind-on-cursor-copilot-devin`, `fenced-roots-env-disables-the-gate` open) | REBUILD | ≥ 2 bugs; becomes `scope()` + one policy call |
| `f/spec_context/gate_policy.py:118-152` `_scope_block`, `:155-165` `evaluate(bound_*…, bound_by_env)` | refuses only a bound session writing another context's registered slug; `bound_by_env` (`inv.session_id is None`, `sdd_gate.py:68`) picks a second fix line | 4 (`sa-bind-has-two-stores`, `unbound-native-…`, `bind-lost-silently-after-five-idle-minutes`, `sa-fix-lines-not-built-by-cli-line`) | REBUILD | scope becomes path-derived (ADR 0103/0105); the session id leaves the decision except the one bound-or-not answer |
| `f/spec_context/gate_policy.py:76-93` `_is_specs_additive`, `_context_relative`; `:111` | `repos/<r>/specs/{backlog,bugs,audits}/*` + `_histo.jsonl` classified ADDITIVE (always writable) | 2 (`additive-globs-hand-kept-beside-the-canon` open; `sa-gate-path-classes-diverge-from-the-law`) | DELETE | ADR 0124: only `specs/audits/**` is direct |
| `core/workspace_layout.py:253-255` `SPECS_ADDITIVE_GLOBS` | hand-kept glob list beside the canon; readers `gate_policy.py:78`, `tests/contract/test_core_file_io_purity.py:170` | ″ | DELETE | ADR 0124 |
| `core/workspace_layout.py:262` `ROOT_ALLOWED_DIRS` | `{.dadaia,.git,repos}` + harness dirs; no `worktrees` | 2 (`sa-seven-workspace-root-rules`, `sa-gate-allows-root-entries-the-reaper-moves`) | UPDATE | + `worktrees` (AC1.6); doctor/reaper and root gate read it already |
| `core/invocation.py:165-177` `repo_slug_under_repos`; `:142` `repo_owner` | path→repo for `repos/<r>/` only | 3 (`sa-context-repo-mapping-falls-back-to-the-name`, `sa-seven-workspace-root-rules`, `sa-bind-has-two-stores`) | REBUILD | becomes `scope(target) -> (repo, zone)`, `worktrees/<r>/<name>/` included |
| `core/invocation.py:83-96` `resolve_session_id`; `cli/commands/context.py:110-115` `resolve_own_session_id(mint=True)` | the gate reads the payload id; bind reads the shell env and, finding none, MINTS `sess_*` | 3 (`bind-session-id-divergence`, `bind-alias-dual-record`, reverted `1a27ae1f`) | UPDATE | delete `mint`: bind refuses with the export fix (ADR 0116) — the id the gate sees is then the id bind wrote |
| `core/session_store.py:117` `stale_records` | "an unreadable record is never stale" | 1 (`corrupt-session-record-never-collected` open) | UPDATE | corrupt = one finding, held by `doctor --fix` (AC1.4) |
| `core/workspace_resolver.py:27` `FENCE_ENV` read by the gate root | a fenced root makes the gate resolve no root → fail-open, PROTECTED included | 1 (`fenced-roots-env-disables-the-gate` open) | UPDATE | PROTECTED judged before root fail-open (AC1.3) |
| `hooks/ctx_inject.py` bind injection | memory prefix only, no `constitution.md`; Cursor/Copilot no bind payload | 2 (`kimi-postcompact-omits-bound-context-bootstrap`, `sa-gate-blind-on-cursor-copilot-devin`) | UPDATE | + constitution, every harness (AC1.2, ADR 0103) |
| `f/spec_context/doctor.py:458-460` linked-worktree reap fix | a linked worktree under a TTL zone gets `git worktree remove` | 1 (`doctor-ttl-walk-quadratic-on-live-trees`) | UPDATE | no worktree under a TTL zone; doctor lists, never prunes (AC1.10) |
| `wt.py` | — (worktrees are hand-made under `.dadaia/tmp`, `/tmp`) | 0 | ADD | no unit creates/merges/cleans worktrees; stdlib script per ADR 0018, imports `_release_schema.extract_status` (0135) |
| `pub/skills/dd-bug-resolution/scripts/_bugs_write.py:41-51` surface check | refuses only `unknown`; free-text surface | 1 (F011) | UPDATE | enum + `--correlates` (AC1.12) |
| `pub/skills/dd-gitflow-default/SKILL.md` §3a table; `dd-bug-resolution` separate RED commit | shapes by write; RED commit separate | 0 (F053–F057, F008) | REBUILD | the kinds' allowed sets replace the table (AC1.13, 0136) |

Bug-history lessons (audit of the fix chain):
- `1a27ae1f` (unbound-native refusal) was reverted by `3a279529`: the gate answered "native id" from the hook payload while `context bind` binds the shell-visible id; on Kimi (payload-only) its own fix line could not clear the refusal — a Stall. Structural cause: two id sources and a bind that mints. This plan deletes the mint (bind refuses without a shell-visible id, ADR 0116) in the SAME task as the refusal, so the gate's bound-or-not answer and bind's write use `resolve_session_id` with an env id first.
- `sa-bind-has-two-stores` (prod +122/−183) was followed on the same surface by `bind-lost-silently-after-five-idle-minutes` and the reopened `unbound-native-…`: the store was unified but the decision kept `bound_*` plumbing; this rebuild removes it.
- `sa-gate-path-classes-diverge-from-the-law` (+27/−59) was followed by `additive-globs-hand-kept-beside-the-canon`: it narrowed the globs instead of deleting them; ADR 0124 deletes them.
- `sa-gate-blind-on-cursor-copilot-devin` was net-positive (+48/−37) and followed by `fenced-roots-env-disables-the-gate` on the gate root: judge PROTECTED before any root fail-open.
- `sdd-gate-memory-phase-resolves-empty-when-cwd-is-a-linked-worktree-outside-repos`: worktrees outside `repos/` broke resolution before; `scope()` makes `worktrees/<r>/` first-class.

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| which repo and zone a path is in | `core/invocation.py` `scope(target)` | `hooks/sdd_gate.py`, `f/spec_context/doctor.py`, `cli/commands/context.py` | `hooks/sdd_gate.py` `_target_slug`, `gate_policy._context_relative`, `repo_slug_under_repos` |
| may this file-tool write land | `f/spec_context/gate_policy.py` `evaluate(rel, scope, bind)` | `hooks/sdd_gate.py` | `_scope_block`, `bound_by_env`, `sdd_gate.py:54-56` unbound ALLOW |
| which paths are always writable under `repos/<r>/` | `gate_policy.evaluate` (`specs/audits/**` only) | — | `SPECS_ADDITIVE_GLOBS`, `_is_specs_additive` |
| which worktree kind holds a path | `wt.py` `KINDS` / `kind_for(rel)` | `gate_policy` (import, 0135), `wt.py merge` | `dd-gitflow-default` §3a table |
| which session id this session is | `core/invocation.py` `resolve_session_id` | gate, `context bind` | `resolve_own_session_id(mint=True)` minting |
| is a worktree open, how old, ahead, dirty | git (`worktree list --porcelain`, `refs/heads/wt/*`, reflog) read by `wt.py list` | doctor, `release.py` closure, `context dead` | `doctor.py:458-460` TTL-zone worktree reap |
| is the trio Approved | `_release_schema.extract_status` | `wt.py new` (import) | — |
| root entries allowed | `core/workspace_layout.ROOT_ALLOWED_DIRS` | root gate, doctor | — |

## 2. Design

### 2.1 `scope(target) -> Scope(repo, zone)` (AC1.1, AC1.6)
- `core/invocation.py`: `scope(root, path)` returns `(repo, zone)` with zone ∈ `repo` (under `repos/<r>/`), `audit` (`repos/<r>/specs/audits/**`), `worktree` (`worktrees/<r>/<name>/**`), `root` (anything else); symlinks resolved, slug sanitized (CWE-22/59). `repo_slug_under_repos` and `_target_slug` fold into it.
- `gate_policy.evaluate(rel, *, root, projected, scope, bind)`: PROTECTED → BLOCK (unchanged messages); `root` zone → ADDITIVE/MUTATING as today (ALLOW); `repo`/`worktree`/`audit` of a repo outside `bind.repos` → BLOCK `context bind <owner>` when unbound-with-id, scope message when bound elsewhere; bound + `repo` → BLOCK `fix: worktree.py new <r> --kind <kind_for(rel)>`; bound + `worktree`/`audit` → ALLOW. One fix line per refusal via `fix_line`.
- The session id enters once: `inv.bind` (resolved by `resolve_bind` from `resolve_session_id`) and `inv.session_id is not None` for the SPEC's "with a native id" clause. `bind` refuses when `resolve_session_id(None, env)` is empty (no mint) — the gate and bind then read the same env-first id (the 1a27ae1f lesson).
- `workspace_layout`: `SPECS_ADDITIVE_GLOBS` deleted; `ROOT_ALLOWED_DIRS` gains `worktrees`; the zone registry marks it never-reaped.
- Deletion test: `_scope_block` + `bound_*` + `_is_specs_additive` + `_context_relative` + `_target_slug` vanish; complexity does not reappear (one decider, one policy branch table).
- Δ prod ≈ −45 (del ≈ −85, add ≈ +40).

### 2.2 `wt.py` (AC1.7–AC1.9), stdlib, ADR 0018
- Verbs `new <repo> --kind K`, `merge <path> [--keep P… | --drop]`, `clean <path>`, `list [--json]`; `KINDS` allowed sets (0106, 0124) and `kind_for(rel)` are module data the gate imports.
- `new`: base = HEAD of `feature/<M.m.p>` (the repo's only `feature/*` work branch; none → refuse, fix `git -C repos/<r> branch feature/<next> <principal>`); impl needs Approved trio (import `extract_status`); caps impl 5, release 1, letters a–z; lowest free letter; `git worktree add -b wt/<v><l>-<k> worktrees/<r>/<v><l>-<k>`; `git worktree lock --reason dadaia:<k>:<v><l>`; `.git/info/attributes` JSONL `merge=union` lines idempotent; refuse a symlinked `worktrees/` component; roll back (`worktree remove` + `branch -d`) on failure; scrub `GIT_*`.
- `merge`: clean tree → allowed set (`git diff --name-only <base>...HEAD`) → `rebase feature/<v>` (conflict → `rebase --abort`, refuse) → APPROVED handoff naming HEAD sha (validated by schema read, not by running `dadaia reports validate` — 0018; the refusal's fix names that command) → ignored-file check (`--keep`/`--drop`) → `merge --ff-only` in `repos/<r>` → `worktree unlock` + `remove` → `branch -d`. Re-runnable: each step detects done state. TASKS.md conflict: markers replay, most advanced state wins (AC1.9).
- `clean`: only `dadaia:`-locked, merged or commit-less.
- Size (reported separately, SPEC G1): ≈ +380 lines.

### 2.3 Doctor listing and holds (AC1.10)
- `f/spec_context/doctor.py`: per bound context, `wt.py list --json` rows as findings (kind, age, ahead, dirty); ready → `fix: worktree.py merge <path>`; > 1 day WARN; orphan `wt/*`, unregistered, harness-native conflicts = findings, never touched; the TTL-zone reap fix (`:458-460`) deleted. SessionStart/compaction print via `ctx_inject`.
- `release.py` closure step and `context dead` refuse while `refs/heads/wt/*` exists.
- Δ prod ≈ +35 package (doctor, `context dead`) / −10 (reap fix).

### 2.4 Bind, injection, session store (AC1.2–AC1.4)
- `ctx_inject`: bound prefix gains `constitution.md` on every harness. `context bind` mint deleted (in 2.1). Fenced roots: PROTECTED classification runs on the target's own root before the fence. `session_store`: an unreadable record is reported once and held by `doctor --fix`.
- Δ prod ≈ +10.

### 2.5 Correlation (AC1.12)
- `bugs.py append`: surface enum, prints same-surface open + resolved-in-30-days, requires `--correlates <ids>|none`. `backlog.py new`: requires `--relates`/`--updates`/`--obsoletes` (or `none`). Script lines ≈ +45 (package-counted, under `pub/`).

### 2.6 Law (AC1.5, AC1.13) and venv (AC1.11)
- Root map §3/§4/§5 `worktrees/` lines + always-on rule; `pub/scaffold/worktrees/AGENTS.md` (init); `dd-gitflow-default` owns the mechanics and names `scripts/worktree.py` (only it); seven skills one line each (contract test); §3a table → kinds' allowed sets; `dd-bug-resolution` separate RED commit deleted; `dd-code-review` one checklist row per kind; ADR 0027 title repaired in place (in a backlog-kind worktree); `CONTEXT.md` Worktree, Worktree kind, Scope, Bind. Repo `AGENTS.md` names the worktree test command. No `.py` delta.

### 2.7 Delta summary
- Package excluding `wt.py`: ≈ −45 (2.1) + 25 (2.3) + 10 (2.4) + 45 (2.5) = **≈ +35**.
- `wt.py`: **≈ +380**. Candidate 5 total ≈ **+415**: a readout, never a limit (ADR 0142); the gate is G1's principles — every ADD above names what could not be deleted or rebuilt.
- Order per unit: DELETE (2.1 losers) → REBUILD (`scope`, `evaluate`) → UPDATE (layout, bind, session store, doctor, scripts) → KEEP (PROTECTED messages, root gate) → ADD (`wt.py`).

## 3. Test strategy

- RED first per task; the RED command is named on each task line.
- DEL leaves dead tests in the same commit: `test_gate_policy.py` ADDITIVE-ledger rows and `unbound-session-never-scope-blocked` (`:83`) are REWRITTEN to the refusals (F070); `test_core_file_io_purity.py:170` drops `SPECS_ADDITIVE_GLOBS`; `test_sdd_gate.py` rows on `_target_slug`/`bound_by_env` deleted — tests net ≤ 0 on 2.1.
- New files the ACs cite: `tests/integration/test_worktree_new.py` (`new`, `list`, the one-venv `__file__` case) and `test_worktree_lifecycle.py` (`merge`, `clean`, parallel merges); every other RED lands in the file that owns the behavior (ADR 0146 (5)): the closure refusal in `tests/unit/skills/test_release_implementation_release_script.py`, correlation in `test_bug_resolution_bugs_script.py` / `test_backlog_definition_backlog_script.py`. Existing: `test_gate_policy.py`, `test_sdd_gate.py`, `test_one_bind.py`, `test_ctx_inject_bind_boundary.py`, `test_context_dead_holds.py`, `test_reaper_spares_linked_worktrees.py`.
- Worktree tests use a `tmp_path` git repo (real git, no venv, fenced root); every test carries `Intent: CONTRACT — AC1.x`.

## 4. Bootstrap and risks

- Order: `worktree.py new`+`list` (T-050-95), then `merge`+`clean` (T-050-96), both written by hand on the work branch with no gate dependency (`KINDS`/`kind_for` live in `wt.py`). Only then T-050-97 rewrites the gate: the editable install makes a gate change live at once for every session, so the refusal never names a tool that does not exist yet.
- T-050-97 itself is made in a `wt.py new` worktree and lands by `wt.py merge`; from it on every task does (AC1.14).
- Declared gap (SPEC AC1.1): an unbound session with no native id and no `DADAIA_SESSION_ID` is not refused under `worktrees/` — refusing it would be a Stall, since the harness env is not the shell env; ADR 0116 carries it to candidate 6.
- Defects found here map to open records: `unbound-native-…`, `additive-globs-…`, `fenced-roots-…`, `corrupt-session-record-…` (DEL/FR here); no new record.

## 5. Parallel schedule (ADR 0141)

| step | tasks open together | width | how |
|---|---|---|---|
| 1 | T-050-95 | 1 | by hand on `feature/0.5.0` (bootstrap) |
| 2 | T-050-96 | 1 | by hand on `feature/0.5.0` (bootstrap) |
| 2b | T-050-106 | 1 | by hand on `feature/0.5.0` (bootstrap: `worktrees/` canon before the first worktree, ADR 0145); the trio amendment of ADR 0146 in the first `release` worktree |
| 3 | T-050-97, T-050-107, T-050-108, T-050-99, T-050-101 | 5 | one impl worktree each |
| 4 | T-050-98, T-050-100, T-050-102, T-050-103, T-050-104 | 5 | one impl worktree each; T-050-104 writes git refs only |
| 5 | T-050-109 | 1 | first, operator 2026-09-30; data rc-1..rc-5 already in the release worktree (6e2bfebc, b71bc354) |
| 5b | T-050-99, T-050-102, T-050-103, T-050-98, T-050-110 | — | each rebases onto T-050-109, in edge order; the ADR 0151 ledger backfill in the release worktree before the batch push |
| 6 | T-050-105 | 1 | measure |

- Operator order 2026-09-30, the ADR 0149 (1) exception: "não é para existir PLAN, SPEC e TASKS na raiz porra, é so dentro de release candidates … é lei". Merge order: the release worktree 0.5.0c (data rc-1..rc-5) → T-050-109 (rebased onto it) → T-050-99, T-050-102, T-050-103, each rebased onto T-050-109. T-050-99/102/103 were already open when T-050-109 was ordered first, so their worktrees overlap its `W:` until they rebase. T-050-98 follows T-050-99; T-050-103 follows T-050-102 (its skill lines teach `--correlates`/`--relates`); T-050-110 follows T-050-103.

- True edges only: a worktree task needs T-050-106 merged (`worktrees/` canon); T-050-100 also needs T-050-97 (`hooks/sdd_gate.py`) and T-050-99 (`hooks/ctx_inject.py`, `f/spec_context/doctor.py`); T-050-98 needs T-050-108 (`test_worktree_lifecycle.py`); T-050-103 needs T-050-107 (`pub/data/AGENTS.md`); T-050-98 needs T-050-99 (`tests/integration/test_worktree_new.py`, the gitflow scripts). T-050-102 needs T-050-99 (`tests/unit/skills/test_release_implementation_release_script.py`, `_release_phase.py`: its one PLAN judge is called by the IMPLEMENTATION transition; widenings, 0147 (2)). Parallel worktrees open only as this schedule places them (0149). `behavior-map.json` hash tuples are derived and re-recorded on rebase, like the union and replay files (0148 (5)). T-050-102 and T-050-104 are ready at step 3 but wait for the 5-worktree cap. T-050-109 (ADR 0150) needs T-050-98 (`_worktree_kinds.py`, `_worktree_new.py`, `test_worktree_new.py`), T-050-99 (`_release_phase.py`, `test_release_implementation_release_script.py`), T-050-102 (`test_release_script.py`, the PLAN judge's path) and T-050-103 (`pub/scaffold/releases/AGENTS.md`, the skills, `core/workspace_layout.py`): it alone moves every trio path, so CI never sees code and data out of step. T-050-110 (ADR 0151) needs T-050-103 (`pub/agents/dd-*.md`, `pub/data/AGENTS.md`); its `W:` is disjoint from T-050-109's except the derived `behavior-map.json`.
- Overlap check: every task in one step has a `W:` set disjoint from its siblings', except `TASKS.md` markers (replay), the JSONL ledgers (union) and the derived `behavior-map.json` hash tuples (re-recorded, 0148 (5)), ADR 0111. `release.py` writers: T-050-99 (`_release_phase.py`, step 3), then T-050-102 (`_release_check.py`, the PLAN judge, and the `_release_phase.py` call to it; after T-050-99); no task writes `release.py` itself. T-050-102 ships `--relates` alone: the obsolete→exit pairing is judged by the backlog review row (0127); `exit` checks its own evidence.
- Critical path: T-050-95 → 96 → 106 → 109 → 102 → 103 → 110 → 105 = 8 steps (amendment 6).
- Merge order inside a step: ready order, true edges only (0148 (1)); step 3 merged T-050-107, 97, 108, 101 and two T-050-97 test fixes (T-050-105 logs them); T-050-99 is in rework. After each merge every open sibling worktree rebases onto `feature/0.5.0`; a conflict outside union/replay files means this PLAN's `W:` sets were wrong and the PLAN is corrected before the next merge.
- T-050-105 logs planned vs measured width per step, the critical path walked and every rebase conflict.
