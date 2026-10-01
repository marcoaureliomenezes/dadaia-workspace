# PLAN — Release: 0.5.0

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

Candidate 6 — W2: root canon, `.dadaiaignore`, DEC-11, one deleter (ADR 0140). SPEC AC2.1–AC2.17. Paths are relative to
`dadaia_workspace/` (`f/` = `features/`, `pub/` = `public/`) unless they start with `tests/`, `specs/`, `docs/`.
As-is read at `wt/0.5.0b-release` HEAD 71c1d27d (base `feature/0.5.0` bfaadba2; c19383a7 touches only `BACKLOG.json`).

## 1. As-is review

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `docs/bug-ledger-lessons.md` Lessons 2–4 | three `derived-from: QUALITY sha256:023d6844061c` markers predate ADR 0155's P-27 deletion (3ca0585a); `test_docs_derived_from_memory.py` is red on `feature/0.5.0` | 0 | UPDATE | re-record the markers; prose changes only where P-27's removal made it false |
| `pub/skills/dd-bug-resolution/scripts/_bugs_write.py:61` surface check | a regex `[a-z0-9_-]+` AND the tracked-directory set decide; the regex refuses `.github` that the fix line offers | 1 (`bugs-append-refuses-the-dot-directory-its-fix-offers` open) | DELETE | two deciders for one question; the tracked set (`bugs.py:116-121`) is the one decider |
| `hooks/venv_guard.py:13,41-42` pip arm | `pip`/`pip3` outside the venv BLOCKED, fix routes into the tool venv | 3 (`pip-guard-fix-routes-…` open; `sa-fix-lines-not-built-by-cli-line`; `sa-text-restates-rules-the-code-contradicts`) | DELETE | ADR 0134 |
| `f/spec_context/service.py:746` `dead` hold | `sweep.hold(...)`'s refusal string is discarded; the registry flips DEAD with the checkout still in `repos/` | 2 (`context-dead-ignores-the-hold-refusal` open; `sa-context-dead-removes-repos-outside-the-reaper`) | UPDATE | the refusal is the hold's return value; the caller raises it before the store write — no new path |
| `f/spec_context/doctor.py:505-513,586-597` `expire` / `_delete` | every TTL-expired entry, `handoff/` included, is deleted directly; `fix()` seeds missing core, `expire()` (the SessionStart lane) does not | 6 on `sweep`/expiry (`bug-proposal-handoff-reaped-without-a-hold` open; `sa-expiry-has-two-clocks`, `sa-reaper-destroys-its-own-hold-before-ttl`, `reaper-needs-many-runs-…`, `doctor-ttl-walk-quadratic-…`, `reaper-judges-ttl-by-walking-every-file`) | REBUILD | ≥ 2 bugs. One deleter: expiry outside `reaped/` is a hold, only `reaped/` expiry deletes; the core seed moves into `expire()`, which `fix()` already ends with — no content key, no zone flag |
| `f/workspace/service.py:63-65` init seed | `init` writes `.dadaiaignore` by hand; `prompt.md` is written by nobody | 0 | UPDATE | one level-1 seed table in `core/workspace_layout.py` read by `init` and the doctor seed (AC2.2, AC2.4) |
| `core/workspace_layout.py:204-230` `verdict` | judges the root and `.dadaia/` levels; `repos/` and `worktrees/` children are always `canon` | 3 (`sa-gate-allows-root-entries-the-reaper-moves`, `sa-seven-workspace-root-rules`, `root-whitelist-misses-nested-new-toplevel-writes`) | UPDATE | ADR 0132: two more judged levels in the same loop, the allow set being the registered (repos) and ALIVE (worktrees) slugs passed in; still the gate's and the doctor's one answer |
| `f/spec_context/doctor.py:417-447` `_scan_root`, `_scan_dadaia_top` | two walks over two of the four places | 1 (`sa-doctor-reaps-harness-owned-entries`) | REBUILD | one walk over the four places `verdict` judges; the two functions collapse |
| `hooks/root_whitelist.py` | asks `verdict` with the operator globs only | 5 (resolved chain, last `fenced-roots-env-disables-the-gate`) | KEEP | passes the slug sets `verdict` now needs; no new decision |
| `f/spec_context/gate_policy.py:101-112,129-139` PROTECTED | PROTECTED = `projected` (the ledger) ∪ `.dadaia/sessions/` ∪ `.dadaiaignore`; no ledger → the law files and hook wiring are writable | 9 (`gate-protects-nothing-without-install-ledger` open; `sa-gate-path-classes-diverge-from-the-law`, `instance-exceptions-file-writable-by-agents`, `repo-agents-md-law-gate-contradicts-template`, …) | REBUILD | ≥ 2 bugs: PROTECTED = code floor ∪ ledger ∪ protected-section match, one predicate, three messages (CLI state, operator, projected law) |
| `hooks/sdd_gate.py:33-36` projected set | built from the ledger alone | ″ | UPDATE | unions the floor and the harness hook-registration files read from `hook_documents` (existing function, no edit there) |
| `core/workspace_layout.py:161-177` `parse_dadaiaignore` | one section of root-relative globs | 0 | UPDATE | ADR 0133: a `[protected]` header starts the repo-relative section; the same grammar, the same invalid-line rule |
| `infrastructure/runtime_transforms/hook_wrappers.py:242-251` `VENV_PYTHON` | a missing venv: stderr line, exit 0 on every lane | 1 (`missing-venv-hook-disarms-the-gate-invisibly` open) | UPDATE | the SessionStart `doctor-expired` lane (registered once per session in every dialect) prints the message on its context channel; every other lane exits 0 silently; the stderr line is deleted |
| `infrastructure/runtime_config.py:68,86` Claude env merge | projects the tool-cache keys, keeps the operator's | 2 (`sa-tool-caches-land-outside-the-cache-zone`, `sa-hook-files-written-by-table-and-by-hand`) | UPDATE | ADR 0156: one more owned key, `PLAYWRIGHT_MCP_OUTPUT_DIR`, in the same merge |
| `pub/data/AGENTS.md` §3 lines 38, 40 | names `pip`; states the Bash path inline; "§7's CLI verbs own theirs"; no fail-open list; no protected rule | 1 (`gate-law-claims-out-of-scope-writes-blocked-but-bash-is-never-judged`) | UPDATE | AC2.6, AC2.8, AC2.9, AC2.13; the fourth fail-open gap (ADR 0116, grill Q5) stated in the same list |
| `pub/scaffold/{memory,ADRs}/AGENTS.md` | no ADR 0138 lane | 0 | UPDATE | AC2.16, one line each |
| `docs/quickstart.md:23-25`, `docs/getting-started.md:135-138` | `backlog.py new`/`release.py new` write `repos/<r>/specs/` directly | 0 | UPDATE | ADR 0154: run them in a `backlog` / `release` worktree after `context baseline` |
| `specs/memory/QUALITY.md` P-27 | already deleted by 3ca0585a (ADR 0155) | 0 | KEEP | AC2.15 holds; T-050-111 re-derives what it staled |

Bug-history lessons (audit of the fix chain):
- `sa-gate-path-classes-diverge-from-the-law` (236b44aa) made the ledger the one PROTECTED source and deleted the basename rule; it was followed by `instance-exceptions-file-writable-by-agents` (a special-case `.dadaiaignore` row) and `gate-protects-nothing-without-install-ledger`. The ledger was right as a source, wrong as the only one: the floor returns as code data beside level 1, never as a basename branch.
- The expiry chain (`sa-expiry-has-two-clocks` → `sa-reaper-destroys-its-own-hold-before-ttl` → `reaper-needs-many-runs-…` → `doctor-ttl-walk-quadratic-…` → `reaper-judges-ttl-by-walking-every-file`) fixed how expiry is judged five times, never what expiry does. `bug-proposal-handoff-reaped-without-a-hold` is the same unit: rebuilding the act (hold, not delete) instead of adding a content branch ends the family.
- `sa-context-dead-removes-repos-outside-the-reaper` moved `dead` onto `sweep.hold` but dropped its return value; the fix reads it, it adds no path.
- `sa-fix-lines-not-built-by-cli-line` rewrote the pip fix line instead of asking whether pip belonged to the guard; ADR 0134 deletes the arm.

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| is a string a valid bug surface | the tracked-directory set built in `bugs.py` `_write` | `_bugs_write.append` | the surface regex |
| may this entry exist at the root, `.dadaia/`, `repos/` or `worktrees/` | `core/workspace_layout.py` `verdict` | `hooks/root_whitelist.py`, `f/spec_context/doctor.py` | — |
| which paths are PROTECTED | `f/spec_context/gate_policy.py` `classify_path` over floor ∪ ledger ∪ protected section | `hooks/sdd_gate.py` | ledger-only PROTECTED |
| which paths are core level 1 | `core/workspace_layout.py` core floor and seed table | gate, doctor seed, `init` | `init`'s hand-written `.dadaiaignore` seed |
| what `.dadaiaignore` says | `core/workspace_layout.py` `parse_dadaiaignore` | gate, doctor, root gate | — |
| what a TTL expiry does | `f/spec_context/doctor.py` `expire` (hold; delete in `reaped/` only) | `fix`, SessionStart lane | `_delete`'s direct delete outside `reaped/` |
| did a hold happen | `f/spec_context/sweep.py` `hold` return | `doctor._reap`, `service.dead` | `dead`'s discarded refusal |
| how a missing venv reaches the agent | `hook_wrappers.py` prologue on the SessionStart lane | every dialect | the stderr warning |
| which Claude env keys dadaia owns | `infrastructure/runtime_config.py` env merge | `public install`, `init` | — |
| which commands the venv guard judges | `hooks/venv_guard.py` (`dadaia`, `python -m dadaia_workspace`) | pre-gate | the pip arm |
| which paths fail open | root map §3, one list | every other law file points or is silent | line 38's inline Bash clause |

## 2. Design

### 2.1 One deleter, one level-1 seed (AC2.2, AC2.4, AC2.10, AC2.12)
- `core/workspace_layout.py`: `LEVEL1_SEEDS` maps `.dadaiaignore` → `dadaiaignore_seed`, `prompt.md` → empty; `AGENTS.md` stays the projection's (ledger). `init` and the doctor seed read it (AC2.2).
- `doctor.expire()`: seeds missing core (`.dadaiaignore`, `prompt.md`, provisioned zones) first, then stale sessions, then TTL: an expired entry in `reaped/` is removed, any other is `sweep.hold`. `fix()`'s seed loop becomes that one seed step, called first by both lanes (idempotent when `fix()`'s closing `expire()` re-runs it), so the reap still judges after the seed. An expired bug-proposal handoff is held and listed as a `REAPED` finding (`Nd left`) — no content key (AC2.10).
- Deletion test: `_delete(…, verdict)` collapses into the expiry act; the seed loop leaves `fix()`.
- Δ prod ≈ +5, tests ≈ +6.

### 2.2 Four judged places (AC2.1)
- `verdict(rel, is_dir, globs, repos=frozenset(), alive=frozenset())`: depth 1 under `repos/` allows the registered slugs; depth 1 under `worktrees/` the ALIVE slugs plus `AGENTS.md`; depth 2 under `worktrees/<r>/` any name; inside a harness directory nothing is judged (ADR 0059, already true — pinned by a row).
- `doctor`: one walk over the four places replaces `_scan_root` + `_scan_dadaia_top`; slug sets from `_contexts()`. Root gate: the same sets from the registry store.
- Risk: an unregistered clone under `repos/` becomes slop and `doctor --fix` holds it (7 days, reversible).
- Δ prod ≈ +10, tests ≈ +12.

### 2.3 PROTECTED floor and DEC-11 (AC2.3, AC2.5)
- `workspace_layout.CORE_FLOOR`: `AGENTS.md`, `.dadaiaignore`, `.dadaia/states/`, `.dadaia/hooks/`, `.dadaia/sessions/`. `sdd_gate` unions the floor, each harness's hook-registration files (`hook_documents` keys under the record's directory) and the ledger.
- `parse_dadaiaignore` returns `(globs, protected, invalid)`; a line `[protected]` opens the repo-relative section (same glob rules).
- `classify_path` PROTECTED when the path is in floor ∪ ledger, or its repo-relative tail (`repos/<r>/…`, `worktrees/<r>/<name>/…`) has a prefix matching a protected glob. Messages: CLI state (`.dadaia/sessions/`), operator (`.dadaiaignore`, protected section; fix `mkdir -p <ws>/.dadaia/tmp/<agent>/<date>`), projected law.
- Contract row (SPEC risk): every floor path is one `init` creates or `public install` writes.
- Not built: a doctor listing of each protected glob with its matches (a SPEC risk mitigation with no AC; it would grow the doctor).
- Δ prod ≈ +20, tests ≈ +15.

### 2.4 Missing venv seen once per session (AC2.7)
- The prologue keeps exit 0. On the `doctor-expired` lane (SessionStart in every dialect) it prints `dadaia: no workspace venv at <ws>/.dadaia/.venv — the gate is off. fix: uvx dadaia-workspace init <ws>` on stdout in the dialect's SessionStart context shape (a `HookDialect` column; plain text where stdout is the channel). Other lanes are silent. The task first measures each dialect's SessionStart channel against the envelopes `hooks/ctx_inject.py` already uses; a dialect with none is named in the AC2.8 list.
- Δ prod ≈ +8, tests ≈ 0 (the existing missing-venv case is rewritten).

### 2.5 Small units (AC2.9, AC2.11, AC2.14, AC2.17)
- `venv_guard`: pip arm and `_PIP_NAMES` deleted. Δ ≈ −6 / tests ≈ −10.
- `service.dead`: a hold that returns anything but `moved …` raises `ContextStateError` with it before `store.update`. Δ ≈ +4 / tests ≈ +8.
- `runtime_config`: `PLAYWRIGHT_MCP_OUTPUT_DIR` = `<ws>/.dadaia/mcps/playwright` merged with the cache keys, Claude only. Δ ≈ +2 / tests ≈ +3.
- `_bugs_write.append`: regex deleted. Δ ≈ −1 / tests ≈ +3 (one row rewritten, one added).

### 2.6 Law (AC2.6, AC2.8, AC2.9, AC2.13, AC2.16)
- Root map §3: the pip clause leaves; one bullet lists the fail-open paths — missing venv (0067), pre-gate past 10 s (0118), a Bash write (0096, 0103; protected paths included, 0133), an id-less unbound session under `worktrees/<r>/` (0116, grill Q5); line 40 names `context create` and the first `specs init` (0154). `pub/scaffold/{memory,ADRs}/AGENTS.md` one line each (0138). Quickstart and getting-started run the births in worktrees. No `.py` delta.

### 2.7 Delta summary
- Prod ≈ +5 + 10 + 20 + 8 − 6 + 4 + 2 − 1 = **≈ +42**; tests ≈ **+43**. A readout, never a limit (ADR 0142). Net-positive because DEC-11 and the floor are new behavior no unit carried; each ADD above names what was deleted or rebuilt first.
- Order: DELETE (pip arm, surface regex) → REBUILD (expiry, PROTECTED, the doctor walk) → UPDATE (verdict, dead, wrappers, env, law) → KEEP (root gate) → ADD (floor, protected section).

## 3. Test strategy

- RED first per task, in the file that owns the behavior (ADR 0146 (5)); no new test file. Every new or rewritten test carries `Intent: CONTRACT — AC2.x`.
- DEL tests leave in the same commit: the pip rows of `test_venv_guard.py` and `test_pre_gate.py:96` are rewritten to ALLOW; the stderr assertion of `test_hook_interpreter.py:70` is rewritten to the context-channel message.
- Owners: AC2.1 `test_root_whitelist.py`, `test_spec_context_doctor_root.py`; AC2.2 `test_cli_init.py`; AC2.3/AC2.5 `test_gate_policy.py`, `test_pre_gate.py`; AC2.4 `test_doctor_fix_lines_clear_their_finding.py`; AC2.7 `tests/integration/gate/test_hook_interpreter.py` (the executable case `test_hook_behaviour_coverage.py` points to); AC2.8/AC2.13 `test_law_states_what_the_code_does.py`; AC2.9 `test_venv_guard.py`, `test_pre_gate.py`; AC2.10 `test_doctor_gc.py`; AC2.11 `test_context_dead_holds.py`; AC2.14 `test_tool_caches_stay_in_the_tmp_zone.py`; AC2.17 `test_bug_resolution_bugs_script.py`.

## 4. Bootstrap and risks

- T-050-111 lands first: `feature/0.5.0` is red on `test_docs_derived_from_memory.py` until it does, and every later worktree rebases onto a green base.
- The editable install makes a gate change live at once: T-050-117 lands after the floor's contract row is green in its worktree, never with a floor path the instance lacks.
- Carried (rc-5 closure INFO; each grows W2, so none rides here; the main thread records the backlog entries):
  - constructor injection of `worktree_rows` into `SpecContextService`/`DoctorService` → rc-8 W6;
  - the Windows integration coverage gap → rc-8 W5 (one test child-env builder);
  - doctor in a fresh worktree lacking the rendered `specs/AGENTS.md` (TREE-5) → rc-8 W6.

## 5. Parallel schedule

| step | tasks open together | width | how |
|---|---|---|---|
| 1 | T-050-111 | 1 | one impl worktree (the derived-docs re-record); turns `feature/0.5.0` green |
| 2 | T-050-112, T-050-113, T-050-114, T-050-115, T-050-118 | 5 | one impl worktree each (the impl cap) |
| 3 | T-050-116, T-050-119 | 2 | one impl worktree each |
| 4 | T-050-117 | 1 | one impl worktree |
| 5 | T-050-120 | 1 | one impl worktree |
| 6 | T-050-121 | 1 | measure; closure in the release worktree |

- True edges: T-050-116 needs T-050-115 (`core/workspace_layout.py`, `f/spec_context/doctor.py`); T-050-117 needs T-050-116 (the same two files) and T-050-113 (`tests/unit/hooks/test_pre_gate.py`); T-050-120 needs T-050-113, T-050-117 and T-050-118 (the law states what they built). Every other step boundary is the cap or the green base.
- Critical path: T-050-111 → T-050-115 → T-050-116 → T-050-117 → T-050-120 → T-050-121 = 6 steps.
- Overlap check: disjoint in every step except `TASKS.md`, the `*.jsonl` ledgers and the derived `pub/entities/behavior-map.json`.
- Merge order inside a step: ready order; after each merge every open sibling rebases onto `feature/0.5.0`.
