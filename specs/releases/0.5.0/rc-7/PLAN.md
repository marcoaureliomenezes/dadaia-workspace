# PLAN — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

Candidate 7 — W3: one grammar owner; W4: one text renderer (ADR 0140). SPEC AC3.1–AC3.18, AC4.1–AC4.9, Approved at e4c651b9. Paths are relative to
`dadaia_workspace/` (`f/` = `features/`, `pub/` = `public/`, `S/` = `pub/skills/`) unless they start with `tests/`, `specs/`, `docs/`, `README.md` or `CONTEXT.md`.
As-is read at `wt/0.5.0a-release` e4c651b9; no code moved since 44d023e6, so the G1 baseline holds: 24,965 production lines / 1,193 test functions / 44,164 test lines.

## 1. As-is review

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `f/specs/doctor_release.py` SPEC-DOC-048 (`_ORIGIN_RE`, `_ORIGIN_VOCABULARY`, `_json_records`, `_known_backlog_ids`, `check_spec_origin`, `_origin_problem`); `rules.py:164-167`; `doctor_governance.known_bug_ids` | a second Origin parser: first line, one clause; `_json_records` splits ledgers with `splitlines()` | 13 on the unit, 2 open (`spec-origin-line-has-two-readers`, `task-line-grammar-accepts-a-malformed-open-marker`) | DELETE | 0161: `release.py check` judges Origin and already runs in the doctor (`RELEASE_SCRIPT`); the unit leaves whole |
| `f/specs/doctor_release.py` SPEC-DOC-047 (`_TASK_BLOCK_RE`, `_MEMORY_WRITE_SET_RE`, `check_no_memory_task`); `rules.py:159-162` | a third task-line reader (`-`/`*` only); matches `Write set:`, a key no TASKS writes since `W:` | ″ | DELETE | the rule moves into `release.py check`, reading `W:` through the one grammar |
| `S/dd-release-implementation/scripts/_release_schema.py` `UNFINISHED_RE` | `\]\s` misses `- [ ]**T-1**`; no marker order, no `W:` reader, no Origin parser | 11, 3 open | REBUILD | ≥ 2 bugs; becomes the task-line grammar (marker states in order, `W:`) and `release.py`'s Origin parser |
| `S/dd-gitflow-default/scripts/_worktree_end.py:17` `_MARK` | a fourth marker regex, `- [` only | rc-5 carry | DELETE | the replay ranks by `_release_schema.MARKS` |
| `S/dd-release-implementation/scripts/_release_plan.py:68` `W:` regex | `\([^)]*\)` breaks on nested parentheses; rc-6 T-050-117 parses right only through a stray backtick | 0 | DELETE | reads `W:` through `_release_schema` |
| `S/dd-release-implementation/scripts/_release_tree.py` `check`, `_directory_findings` | skips DEFINITION (`:48-50`); no Origin, trace or shipped check | 2 open (`release-check-accepts-done-tasks-in-definition`, `release-ship-accepts-what-release-check-refuses`) | REBUILD | ≥ 2 bugs; the one readiness judge in every phase |
| `S/dd-release-implementation/scripts/release.py:103-128` `_ship` | own readiness (phase, archive); sha and PR twice: `shipped{}` and the histo `summary` | 1 open, 11 prior on the ship path | REBUILD | asks `_release_tree` before any write; `summary` stops restating |
| `S/dd-release-implementation/scripts/_release_phase.py:120-127` stamps | `defined`/`implemented` overwritten per candidate; history only in prose notes | F058, F059, F061 | UPDATE | each move appends one structured `milestone` log entry in place of its prose note (§2.4) |
| `S/dd-backlog-definition/scripts/_backlog_exit.py` `_origin_cites`, `check_exit` | own Origin regex on any line; fixes hold `<release-id>` and `<the release whose Origin names …>`; the hint offers `rejected` to any entry | 6, 3 open | REBUILD | ≥ 2 bugs; imports `_release_schema.origin`; one evidence table drives disposition → flag → verifier, `to-bug` a row |
| JSONL line reads: `_release_new.py:63`, `_bugs_store.read_records`, `_audit_store.py:74` | three readers, one with `splitlines()` | 5 over time (4 fixes in 4 readers), 1 open | REBUILD | `_ledger.records` splits on `\n` once; the stores read through it; the checks KEEP their numbered split over the text the stores hand them |
| `f/specs/doctor_adr.py:30` `_superseded_ids`, `:86-95` `adr_record_issues` | `splitlines()` drops a U+2028 record; validates with the package `jsonschema` | 2, 1 open | REBUILD | reads and validates through the loaded `_ledger` |
| `f/specs/doctor_governance.py:44-52` `_bug_lines` | a package bug-ledger reader | 0 | UPDATE | reads through the loaded `_ledger.records` |
| `infrastructure/jsonl_record_store.py` | 61 lines, no production importer; one assertion (`#B43-5`) pins its missing write half | 1 resolved | DELETE | deletion test: nothing reappears (L6 confirmed, §1.2) |
| `f/specs/schemas.py` `validator_for`, `schema_errors`; `f/backlog/doctor.py:77-78` `_ITEM` | the package `jsonschema` engine for the ADR record and backlog `activeItem` | FR `ledger-schema-one-engine`; 12 prior | DELETE | 0018: `_ledger.validate` is the one engine; `load_schema` KEEP for memory frontmatter, not a ledger |
| `infrastructure/ledger_scripts.py` `_PACKAGE_SKILLS`, `_finding` | runs each `check`; the fallback prints "repair that line by hand" once per field | 7, 1 open | REBUILD | ≥ 2 bugs; gains the one owner loader (0157); the fallback leaves |
| `f/specs/memory_canon.py:46-52` `_atom_grammar` | a second exec-loader of a skill script, in `features` | 1 resolved | UPDATE | loads through the infrastructure loader (AC3.1) |
| `f/spec_context/gate_policy.py:70,88-91` `_kind_holding` | a third package loader: `runpy.run_path` of `_worktree_kinds.py`, `@cache`d, on the pre-gate path but run only when a `repos/<r>/` write is refused | 0 | UPDATE | loads through the infrastructure loader, still lazy and cached: the pre-gate pays it only on that BLOCK, as today; the SPEC Risks line holds because the loader adds no subprocess and no eager load |
| `S/dd-bug-resolution/scripts/_bugs_check.py:52` `schema_errors` | a third hand-rolled engine (`:107`, `:132`) | 3, 1 open | DELETE | `_ledger.validate` is the one engine (§1.1) |
| `f/migrate/state_v2.py:40,99` registry `json.loads` | reads the registry raw | 0 | KEEP | `migrate` rewrites the whole document, `schema_version` included, while `entries` returns only the list; the 0135 contract lists it as the grammar's upgrader |
| `_bugs_transition.py:58`, bug-record-v1 `diff_direction`, `_bugs_check`, `_bugs_write._VERB_OWNED` | 277 of 716 records store the direction `evidence_diff` already carries; 653–654 disagree; seams unverified; 2 `caused_by` cycles and 3 dangling targets pass; `update` refuses `caused_by`, which the schema marks `mutable-governance` | 3, 1 open; F002, F012, F013 | REBUILD | 0160; the `caused_by` row of `_VERB_OWNED` is deleted, so `update` is the governance verb F013 needs |
| `core/context_registry.py` `entries` | fail-soft `None`; `{}` reads as empty | 10, 2 open | REBUILD | 0162: the one parse; absent and `{}` are unreadable |
| `infrastructure/json_context_store.py:43-51` `_load` | its own `json.loads`; absent reads empty; corrupt raises a traceback | ″ | REBUILD | reads through `context_registry`; the absent branch leaves (M8) |
| `core/invocation.py:93-94` `_registry_contexts` | `or []`: unreadable reads as "no context" | ″ | DELETE | callers receive the unreadable answer |
| `f/spec_context/doctor.py:226-231,323-332` `check`, `_contexts` | REG-SCHEMA only on `SchemaVersionError`; `_contexts` swallows the rest | ″ | UPDATE | REG-SCHEMA on every unreadable registry; `--fix` lanes act on nothing |
| `hooks/ctx_inject.py:134`; `cli/commands/context.py` list, show, create | "create a context", or a traceback | ″ | UPDATE | print REG-SCHEMA with one fix line |
| `infrastructure/privacy_check.py:152-203` `_load_privacy_denylist` | a second loader; root from the cwd; list form raises | 26 denylist records, 3 open | DELETE | 0157 |
| `S/dd-bug-resolution/scripts/_ledger.py:115-130` `_terms` | walks up from the cwd | ″ | REBUILD | root given by the caller (§2.6); object form only |
| `f/workspace/service.py` `init` | no denylist migration | 1 open | UPDATE | list form converted once; `sweep.hold` injected by `container.py` |
| `infrastructure/data/privacy_baseline.json` secret-token | `gh[pousr]_`, `sk-…{32,}` | 9, 1 open | UPDATE | `github_pat_` and `sk-ant-` alternations |
| `S/dd-audit-project/scripts/_audit_verbs.py` `close` | `--sha` optional | F052 | UPDATE | required |
| `S/dd-bug-resolution/LINEAGE.md` | "no per-release `_RELEASE.json` survives archiving" | F058, F061 | UPDATE | ADR 0152 (1); the `git log -S` recovery line |
| `core/workspace_layout.py` `CORE_FLOOR`; `f/spec_context/gate_policy.py:156-165` | messages keyed on the literal `".dadaia/sessions"`; session fix `context bind '<ctx>'` | 14, 1 open | REBUILD | ≥ 2 bugs; one message per floor entry beside `CORE_FLOOR`, read by `evaluate` |
| `tests/contract/test_slop_ratchets.py:217-238` `_allowance_violations` | `len(allowance) > birth` only | c4 AC6.6 | UPDATE | closure keys ⊆ birth keys (b86bb65b) |
| `tests/contract/test_public_scripts_thin_wrapper.py` | owns the script side of 0018/0135; no package rule | 0 | UPDATE | becomes the 0135 contract (AC3.1) |
| `_backlog_schema.DISPOSITIONS`, `_backlog_check`, histo-record-v1, `_worktree_kinds.KINDS["backlog"]`, `pub/scaffold/backlog/AGENTS.md` | three dispositions; the backlog kind lacks `BUGS.jsonl` | F063, F102 | UPDATE | `to-bug` is a fourth row (0137) |
| `S/dd-gitflow-default/SKILL.md` §3a; `S/dd-release-definition/SKILL.md` §4 | "alone", `chore(adrs)`, "+ picked bugs"; no closure rows | 9, 1 open | REBUILD | ≥ 2 bugs; the staged set is the kind's allowed set |
| `DADAIA_BIN`: `pub/scripts/pre-push-ci-gate.sh:25,59-61,101-102`, `hooks/venv_guard.py:14,49`, `f/ci_preflight/service.py:71-75` | a second CLI spelling; nine test files use it as a stub seam | 1 open | DELETE | 0045; tests stub `<ws>/.dadaia/.venv/bin/dadaia`, the hook's rank-2 walk |
| `pub/scripts/pre-push-ci-gate.sh:15`; `docs/getting-started.md:166` | consumer guidance names `ci preflight` and release-please | FR | DELETE | F099 |
| `cli/commands/{context,reports,help,export,public,import_,capabilities}.py` | 14 hand-spelled bare `dadaia` examples | 8, 1 open | UPDATE | rendered by `cli_line` |
| fix sites: `hooks/root_whitelist.py:55`, `f/chokepoints/branch_policy.py:110-115`, `cli/commands/doctor.py`, `f/workspace/onboarding.py:101`, `f/spec_context/sweep.py:86-94`, `_specs.py:33-41` `_bound_tree` | mkdir of an existing dir; `<M.m.p>`; two lines for `--context nosuch`; a fixless skip; `repos/<r>/specs`, unwritable, or `repos/<context>/specs` | 17 fix-line records, 4 open | REBUILD | ≥ 2 bugs; each site renders one 0158 form with its real value |
| `core/cli_line.py` ↔ `_specs.quote/script/with_specs` | two renderers, no parity test | 0159 | KEEP | the pinned pair; one harness case holds it |
| `_ledger.validate` | no `allOf`, no `not`: decision-record-v1's accepted ⇒ `measured_by` + `ruling` and `ruling.words` ≠ `(?i)delega\|in session` would pass silently | ADR 0151 M1 | UPDATE | gains `allOf` (if/then) and `not` before `doctor_adr` moves onto it |
| `_ledger.finding`; each `_*_check.py` | findings without `fix` | 1 open | UPDATE | `fix` required; each check names its verb |
| three fix-line contract files, 804 lines, 14 functions | three site lists for one invariant | F017; `every-block-fix-push-refspec-flaky-under-xdist` open | REBUILD | one harness (§2.9) |
| `pub/scaffold/releases/AGENTS.md` §2–§3; `pub/agents/dd-software-engineer.md:79,127,146`; `S/dd-manager-orchestration/SKILL.md:65`; `S/dd-release-implementation/RC-FLOW.md:11-12,28,45,62-64` | two marker lifecycles; a compliance line the doctor never prints; `:20` cites SPEC-DOC-048 | 7, 4 open | REBUILD | ≥ 2 bugs; the lifecycle stated once, cited elsewhere |
| `pub/data/AGENTS.md` §3 | six fail-open paths; one fix form | F080 | UPDATE | seventh path and judged scope; the two 0158 forms; existing bullets edited (8,188 B source) |
| `docs/getting-started.md`, `README.md`, `docs/quickstart.md` doctor paragraphs | "absent" governs `.dadaiaignore` only; TTL expiry prose stale | F080 | UPDATE | zone-class wording |
| `S/dd-release-implementation/RELEASE-EVENTS.md`; release-state-v1 log `kind` | no milestone record | F059 | UPDATE | the `milestone` kind |
| `CONTEXT.md` | no Grammar terms | — | ADD | three terms no unit carries |

- A ≥ 2-bug unit that leaves whole is DELETE (nothing remains to rebuild); a surviving one is REBUILD.

Bug-history lessons (audit of the fix chain):
- One cause behind all W3/W4 open bugs: a grammar or a command spelling with more than one reader, each fix patching the reader it was filed against. The U+2028 family shows it: four fixes in four readers, the fifth reader open.
- `sa-denylist-file-has-three-shapes` collapsed shapes and kept two loaders; `privacy-denylist-has-two-loaders` and `list-form-…` followed. The fix deletes a loader.
- `ledger-fix-lines-drop-specs` patched the fallback's spelling; the fallback is the defect.
- `migrate-and-reconcile-crash-on-a-schema-3-…` hardened the store and left `invocation`'s fail-soft twin; the corrupt registry now crashes one caller and misleads another.
- `sa-fix-lines-not-built-by-cli-line` built one builder; `_specs` and the placeholders stayed outside it, and four bugs followed.
- Verdict: every touched unit shrinks or holds, except the ADDs §2.10 names; the bug surface per grammar goes from N readers to one.

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| what a SPEC Origin line says | `_release_schema.origin` (`release.py`) | `_release_tree.check`, `_backlog_exit.check_exit`, the doctor via `RELEASE_SCRIPT` | SPEC-DOC-048, `_backlog_exit._origin_cites` |
| what a task line says (marker, order, `W:`) | `_release_schema` `MARKS`, `UNFINISHED_RE`, `writes` | `_release_phase`, `_release_tree`, `_release_plan`, `_worktree_end` replay | `_MARK`, `_TASK_BLOCK_RE`, `_release_plan`'s `W:` regex |
| what a Status token says | `core/spec_status.extract_status` ⇄ `_release_schema.extract_status`, pinned by `tests/unit/core/test_spec_status.py` | the doctor, `_release_phase`, `_worktree_new` | — |
| is a release ready, in any phase and at ship | `_release_tree.check` | `_ship`, `_release_phase`, the doctor | `_ship`'s own judgement; the DEFINITION skip |
| how a JSONL ledger splits into records | `_ledger.records` | every script store, `_release_new`, the package via the loader | `jsonl_record_store`, the `splitlines()` reads |
| is a bug record valid | `bugs.py` (`_bugs_check`) | `_release_tree` trace, `_backlog_exit` `to-bug`, `doctor_governance._bug_lines`, the doctor via `BUGS_SCRIPT` | `doctor_governance.known_bug_ids` |
| is a `BACKLOG.json` entry valid | `backlog.py` (`_backlog_check`) | `f/backlog/doctor.py` binding, the doctor via `BACKLOG_SCRIPT` | `_ITEM` |
| is a backlog histo record valid | `backlog.py` (`_backlog_check`) | `_release_tree` trace | — |
| is a release state or releases histo record valid | `release.py` (`_release_check`) | the doctor via `RELEASE_SCRIPT` | — |
| is an audit finding record valid | `audit.py` (`_audit_check`) | `_release_tree` trace, the doctor via `AUDIT_SCRIPT` | — |
| is an audit histo record valid | `audit.py` (`_audit_check`) | the doctor via `AUDIT_SCRIPT` | — |
| is an ADR decisions record valid | `f/specs/doctor_adr.py` over the loaded `_ledger` | `tests/contract/test_adr_canon.py` | `schemas.schema_errors` |
| which engine validates a ledger record | `_ledger.validate` | every `check`, `doctor_adr`, `f/backlog/doctor.py` | `schemas.validator_for`, `_ITEM`, `_bugs_check.schema_errors` |
| how the package loads an owner script | `infrastructure/ledger_scripts.py` loader (0157) | `privacy_check`, `doctor_adr`, `doctor_governance`, `f/backlog/doctor.py`, `memory_canon`, `gate_policy._kind_holding` | `memory_canon`'s `exec`, `gate_policy`'s `runpy.run_path` |
| which terms the privacy denylist holds | `_ledger.terms` (0157) | `privacy_check`, `_bugs_store`, `_backlog_store` | `privacy_check._load_privacy_denylist` |
| which secret shapes are refused | `infrastructure/data/privacy_baseline.json` | `privacy_check`, `_ledger._baseline` | — |
| what the context registry holds | `core/context_registry.entries` (0162); `f/migrate/state_v2.py` upgrades pre-v2 rows only | `JsonContextStore`, `invocation`, `sdd_gate`, the doctor, `ctx_inject`, `context` CLI | `JsonContextStore`'s parse, `_registry_contexts`'s `or []` |
| what fixes a ledger finding | each script's `check` | `ledger_scripts.script_findings` | `_finding`'s hand-edit fallback |
| how a command is printed | `core/cli_line.py` ⇄ `_specs.py` (0159) | every fix site, `--help` | `DADAIA_BIN`, hand-spelled examples, `_bound_tree`'s placeholder |
| which forms a fix line takes | root map §3 (0158) | every BLOCK and refusal; the AC4.1 harness measures | the three contract files |
| what a core-floor refusal says | `core/workspace_layout.py` beside `CORE_FLOOR` | `gate_policy.evaluate` | the literal-keyed branches |
| what a commit stages | `_worktree_kinds.KINDS` | `dd-gitflow-default` §3a, `dd-release-definition` §4 | "alone", `chore(adrs)`, "+ picked bugs" |
| how a task marker moves | `pub/scaffold/releases/AGENTS.md` §3 | persona, orchestration skill, RC-FLOW | RC-FLOW's second lifecycle |
| which paths fail open | root map §3 | every other law file is silent | — |
| who deletes a file | `f/spec_context/sweep.py` (V38) | — | — |
| when a candidate was defined and implemented | `_release_phase`: the live slots and, per candidate, its `milestone` log entry | `window_start`, `_memory_record_error`, `PILLAR-SPECS.md` | the prose stamp note |

### 1.2 Facts the SPEC defers here

- M6, AC4.9 fail-open set (each row of the law test reads its code):
  - policy raise: `hooks/pre_gate.evaluate_payload`'s `except` → ALLOW;
  - unreadable payload: `hooks/_common.read_stdin_json` returns `{}` → ALLOW;
  - Bash write: `sdd_gate.evaluate_payload` (`is_write_tool`) → ALLOW;
  - id-less unbound session: `gate_policy.evaluate(has_id=False, context=None)` under `worktrees/<r>/` → ALLOW;
  - unreadable registry: `context_registry.registered_slugs` → `{"*"}`;
  - pre-gate timeout: `infrastructure/runtime_transforms/hook_wrappers.TOOL_TIMEOUT_S` (10);
  - missing venv: `tests/integration/gate/test_hook_interpreter.py::test_missing_venv_is_loud_and_fails_open_on_every_harness`.
- M6, AC4.6 marker states and order: `_release_schema` holds none today (`UNFINISHED_RE` knows `[ ]`/`[-]`; the order lives in `_worktree_end._MARK`). T-050-137 adds `MARKS = (" ", "-", "x")`, the one ordered tuple `UNFINISHED_RE` and the replay derive from; the law test reads it.
- M9, AC4.4 agent segment: no dialect carries an agent identity. `hooks/_common.claude_payload` reads only `tool_name`/`toolName`/`tool`, `tool_input`/`toolArgs`; `core/harness_registry.py` holds no payload field; the recorded payloads under `tests/fixtures/hook_payloads/{claude,codex,copilot,cursor,devin,kimi-code}/` carry none. The fixed segment is `main-thread`: both `main` and `main-thread` exist under `.dadaia/tmp/`; `main-thread` is the shipped law's name for that actor (`handoff-AGENTS.md:8`, `dd-grill-me` §6, the personas' `concurrency_relationship`), and `main` reads as a branch name. No live PreToolUse payload is recorded on this instance (`.dadaia/tmp/hooks/` holds only ctx-inject markers; `.dadaia/sessions/` holds none with an agent field), so T-050-146's RED starts with one live subagent-payload probe before it fixes `main-thread`.
- M8: only tests rely on `JsonContextStore`'s absent branch. Every production constructor is behind `container._guard_initialized` or the resolver's sentinel (`hooks/ctx_inject.py:149`). The tests: `tests/fixtures/stores.py:15` (its docstring's "as `init` creates it" is false: no file), `tests/unit/test_json_context_store.py:40,91`, `tests/unit/infrastructure/test_io_encoding.py:44`, `tests/integration/test_context_baseline.py:77`. The fixture seeds init's document; the four sites use the fixture.
- AC3.3, the rc-6 `W:` conflict: rc-6 impl commits widened their own `W:` lines (T-050-113 `1b0d9685`, T-050-117 `a386efc7`, as `specs/releases/AGENTS.md` §3 allows). T-050-113 put written fixtures in parentheses, so the checker reads them as named; T-050-117's nested `classify_path(...)` parentheses parse right only by a stray backtick. AC3.3 decides the parse: T-050-117's line yields its ten written paths. Who may widen stays as §3 states.
- L6: `infrastructure/jsonl_record_store.py` has no other reader: `git grep jsonl_record_store` outside `specs/` hits only `tests/unit/skills/test_audit_project_audit_script.py:207`.

## 2. Design

### 2.1 One JSONL reader; one owner loader (AC3.5, AC3.6, AC3.1 code)
- `_ledger.records(path)`: `\n` split, non-blank, JSON objects; `_bugs_store.read_records`, `_audit_store` and `_release_new.seeded_scope` read through it.
- `ledger_scripts.load_owner(skill, module)`: execs `_PACKAGE_SKILLS/<skill>/scripts/<module>.py` into a module (the `memory_canon` mechanism, moved), cached; the one package path into `public/skills`.
- `_ledger.validate` gains `allOf` (each member an `if`/`then`) and `not`, so decision-record-v1 keeps ADR 0151 M1: every `0151-M1-*` row of `test_adr_canon.py:71-93` keeps its meaning, messages change only citing its statement id.
- `doctor_adr`, `doctor_governance._bug_lines`, `f/backlog/doctor.py` read and validate through the loaded `_ledger`; `memory_canon` loads `_memory_schema` through it; `schemas.validator_for`/`schema_errors` and `jsonl_record_store.py` leave; `test_audit_project_audit_script.py:212` (`#B43-5`'s store half) leaves, its `features/specs` half stays.
- AC3.1 (main-thread ruling on Q2): no package module but the loader execs or imports a `public/skills` script. Reading Markdown is not loading (`citations.py:193,205`, `doctor_adr.py:53`); `core/cli_line._SHIPPED_SKILLS` renders a path.
- `gate_policy._kind_holding` moves onto the loader in T-050-143 (after 136 and 141): lazy and cached, so the pre-gate cost is unchanged.
- Δ prod ≈ −93, tests ≈ +10.

### 2.2 Origin and traceability (AC3.2, AC3.12 report, AC3.17 scaffold)
- `_release_schema.origin(text) -> dict[str, list[str]]`: the first `**Origin:**` line only; `operator-demand`, or `; `-joined `backlog:`/`bugs:`/`findings:` clauses, each kind once; a one-clause line is its one-clause case.
- `_release_tree.check` judges presence, grammar, existence, and the trace: an entry's `delivered` exit naming the release, a bug's `resolved_release` or rejection, a finding's disposition `release`, a `to-bug` target never rejected. Before the live candidate's `dispositions` log entry and before `ship`, a missing pointer is listed, not a finding.
- `_backlog_exit` imports `origin` (`backlog.py` gains the release scripts dir); the `--release` fix names the release it found.
- SPEC-DOC-048, its rule row and `known_bug_ids` leave; `test_spec_doc_048_origin.py` re-homes by name into `test_release_script.py` (`sa-spec-doc-033-duplicates-bugs-check#B4` included).
- Δ prod ≈ −43, tests ≈ −100.

### 2.3 Task line (AC3.3)
- `_release_schema`: `MARKS = (" ", "-", "x")`; `UNFINISHED_RE` = `^\s*(?:[-*+]\s*)?\[( |-)\]`; `writes(line)` = the backticked paths of `W:` up to the first `·`, a parenthesized span (nesting counted) named, not written.
- `_release_plan` and `_worktree_end`'s replay read them; `_MARK` leaves; "the most advanced state wins" stays in the replay.
- SPEC-DOC-047 re-homes into `check`: a `W:` naming `specs/memory` is a finding; `test_doctor_memory_task.py` re-homes by name into `test_release_implementation_release_script.py`; RC-FLOW `:45` names `release.py check`.
- Δ prod ≈ −37, tests ≈ −50.

### 2.4 Readiness, ship, archive, milestones (AC3.4, AC3.14, AC3.15)
- `_release_tree.ship_findings(specs)` = `check` + "phase is not CLOSURE" + "`_archive/<id>` already exists"; `_ship` raises its first finding and fix before any write; its own branches leave.
- `check` under DEFINITION: a `[-]`/`[x]` marker, or a closure-kind log entry after the live candidate's birth note, is a finding; `_directory_findings`' phase guard leaves.
- The histo `summary` is `null`; `shipped{sha, pr, ts}` is the one field; `check` verifies it in each `_archive/<v>/_RELEASE.json` from 0.5.0 on.
- Milestones: `phase` appends `{"kind": "milestone", "candidate": "rc-<N>", "milestone": "defined"|"implemented", "sha", "ts", "text"}` in place of its prose note; the `defined`/`implemented` slots KEEP the live candidate's values, because `window_start`, `_memory_record_error` and audit pillar 2 read them; the `milestone` entries are the history. The schema gains the kind and two optional fields, so the live document stays valid. Earlier stamps are the prose notes "Candidate defined at …", which `RELEASE-EVENTS.md` names as their record.
- `audit.py close` requires `--sha`; `LINEAGE.md` states ADR 0152 (1) and the `git log -S <audit-id> -- specs/audits` recovery.
- Δ prod ≈ +5, tests ≈ +20.

### 2.5 Bugs evidence and lineage (AC3.7, AC3.8), one `bug` worktree
- Commit 1, shape 3: `diff_direction` leaves the schema and `_bugs_transition`; `check` and `stats` derive the direction from the `evidence_diff` prefix; `resolve` refuses an `--evidence-seam` whose file or `def <name>` is missing; `_VERB_OWNED` loses `caused_by`; `_bugs_check.schema_errors` leaves for `_ledger.validate`; the commit cites ADR 0160 for SKILL.md:72; the strip of every record runs through `_bugs_store.commit`, its command quoted in the body.
- Shape-4 commits: F012/F013's 2 cycles, 3 dangling targets and 3 nulls set by `bugs.py update --set caused_by=…`.
- Last commit: `check` refuses a `caused_by` cycle or dangling target; `check` exits 0.
- No other `bug` worktree is open while it runs (SPEC Risks); it merges before T-050-139 widens the secret patterns. Its TASKS markers ride the release worktree: the bug kind holds no `TASKS.md`.
- Every resolve tail of another task's DEL bug (131, 132, 134 …) waits for its merge, or batches at G3: with `*.jsonl merge=union`, a resolve rebased across the strip doubles records.
- Δ prod ≈ +20, tests ≈ +25.

### 2.6 Registry and denylist (AC3.9, AC3.10, AC3.11)
- `context_registry.entries(root)` raises `SchemaVersionError(problem, fix)` (the registry's existing typed refusal) for absent, unparseable or non-`{"contexts": [...]}` content, `{}` included; fix `Operator action: rewrite <abs path> as one {"contexts": [...]} object`. `registered_slugs` maps it to `{"*"}`; `JsonContextStore._load` reads through `entries`; `_registry_contexts`' `or []` leaves; the doctor's `check` and `_contexts`, `ctx_inject` and `context list|show|create` render REG-SCHEMA. The gate rule: an unreadable registry is no bind. The two pre-gate registry reads outside `_evaluate_target` are deleted, not caught: `sdd_gate.evaluate_payload:73` and `root_whitelist.py:26` use `invocation.resolve` only for `.workspace_root`, so both call the one root decider, `invocation._resolve_root` made public (`own_workspace_root() or acting_root(cwd)`, never raises; `workspace_resolver.resolve_workspace_root()` would raise and fail open). The one gate-path registry read left is in `_evaluate_target`, under one catch that maps the bind and `owner` to none and keeps `scope()`'s path-derived `repo`; `gate_policy.evaluate` still judges the floor, PROTECTED, the root, `.dadaia/`, the closed-canon zones, and merge-only `repos/<r>/` (ADR 0105), as today. The seventh path's `{"*"}` is the layout check's answer (`registered_slugs`), which AC4.9 measures. The policy-raise path is never the route.
- `_ledger.terms(root)`: `$DADAIA_PRIVACY_DENYLIST`, else `<root>/.dadaia/states/privacy_denylist.json`, object form only. Scripts pass the nearest ancestor of `--specs` holding the sentinel; `privacy_check` passes `resolve_workspace_root()` and loads `_ledger` through the loader.
- `init` rewrites a list-form file once in object form after `sweep.hold` keeps the original; `container.py` injects `hold` (features stay independent).
- Two secret-token alternations; fixtures compose the prefixes at runtime.
- Δ prod ≈ −37, tests ≈ +40.

### 2.7 `to-bug`, shapes, terms (AC3.12, AC3.13, AC3.17)
- `REQUIRED_EVIDENCE` and one verifier table: `delivered`/`superseded` → release Origin; `rejected` → reason; `to-bug` → reason naming a `BUGS.jsonl` record, read through the imported `_bugs_store.read_records`. The hint offers a disposition the entry can take.
- `KINDS["backlog"]` gains `specs/bugs/BUGS.jsonl`; the scaffold backlog law lists four dispositions; histo-record-v1's enum gains `to-bug`.
- §3a's staged column becomes the kind's allowed set; ADR message `docs(adr): propose|accept <slug>`; rows for `chore(tasks)`, `docs(memory)`, `docs(specs)`, `chore(release)`; the law test asserts §3a = `KINDS`.
- Δ prod ≈ +14, tests ≈ +23.

### 2.8 Renderer sites (AC3.18, AC4.2–AC4.5)
- Floor messages: a mapping beside `CORE_FLOOR`; `evaluate` reads it; the session fix is `context bind <bound context>`, unbound `context list`; `classify_path`'s docstring states projected → floor → glob.
- `DADAIA_BIN` and the `ci preflight` advice leave the hook; `venv_guard` and `ci_preflight` lose their arms; release-please leaves getting-started.
- `--help`: each example renders through `cli_line`.
- Sites: root BLOCK `mkdir_line(<ws>/.dadaia/tmp/main-thread/<YYYYMMDD>)`; pre-push names the live work branch; `doctor --context nosuch` one `context list`; onboarding Next `Operator action:` with real values; `sweep.guarded` names the owner and `Operator action: remove <real path>`; `_bound_tree` names the open worktree of the ledger's kind, else `worktree.py new <r> --kind <kind>`.
- `_ledger.finding(…, fix)` required; each check passes its governance verb; `_finding`'s fallback leaves.
- Δ prod ≈ +4, tests ≈ +30.

### 2.9 One harness (AC4.1, AC4.7 fixture, AC4.8)
- `tests/contract/test_every_block_carries_a_fix.py` keeps its name (0018 and 0073 `measured_by` stay true) and absorbs the other two files by case name; inventory measured at 1b524a9e, unchanged since:

| # | case today | after | Δ lines |
|---|---|---|---|
| A1 | `every_block:82` the real doctor prints one runnable line per fix | KEEP, row `doctor-printer` | 0 |
| A2 | `every_block:224` `_BLOCKS`, 13 rows | KEEP, the one site table; + DEC-11, missing-venv, root-whitelist and the AC4.4 sites | +12 |
| A3 | `every_block:234` root BLOCK fix runs from `repos/demo` | MERGED with C1: runs verbatim per host shell | −15 |
| A4 | `every_block:432` every ledger fix runs its script | KEEP | 0 |
| A5 | `every_block:440` the bug script is one ledger row | DELETED, A4 covers it once each check emits its fix | −10 |
| A6 | `every_block:451` every fix target resolves | KEEP; + the no-`<…>` column; the placeholder-tolerant prefix walk leaves | −7 |
| A7 | `every_block:482` the path rule bites | MERGED: one "the scans bite" control over planted samples | −8 |
| A8 | `every_block:527` each script fix names its entry script | KEEP | 0 |
| A9 | `every_block:546-573` no law names a retired release verb | MERGED: its vocabulary (`rc-archive`, `release.py (fold\|archive)`, `rc-N`, `resolve` carrying) and roots (`public/`, `specs/memory`, `CONTEXT.md`) become rows of the merged scan | −20 |
| A10 | `every_block:582` `memory.py check` is no done criterion | KEEP | 0 |
| B1+B3 | `builder:118,155` AST scans | MERGED into one walk with the Markdown scan | −88 |
| B2 | `builder:122` hand-built fix control | MERGED into A7 | −8 |
| C1 | `shell:41` runs verbatim in each shell | MERGED into A3 | −34 |
| new | AC4.7 consumer-repo fixture; AC4.8 `pub/**/*.md` command lines; 0159 pinned-pair argv; no `<…>` | ADD as rows and columns | +38 |

- After: one file, 9 functions; 804 → ≈ 664 lines. `push-refspec` keeps its name and bug id. Each merge's commit body maps old → new.

### 2.10 Law and ratchets (AC3.1 measure, AC3.16, AC4.6, AC4.9)
- The marker lifecycle once in the scaffold §3; persona, orchestration and RC-FLOW cite it; RC-FLOW loses "marker stays `[-]`", "no per-task reviewer gate", the "two simultaneous `[-]`" recovery and the compliance line.
- Root map §3: the seventh path, the judged scope and the two fix forms, in existing bullets; getting-started, README and quickstart follow.
- `test_law_states_what_the_code_does.py`: one row per fail-open path read from §1.2's code; the stated transitions equal `MARKS`; no sentence pinned.
- `_allowance_violations`: closure keys ⊆ the birth keys read from b86bb65b; V38 today: 11 sites outside `sweep.py`, all allowed.
- The 0135 contract (`test_public_scripts_thin_wrapper.py`): no package module but the loader execs, imports or `runpy.run_path`s a `public/skills` script; no package module parses a grammar outside §1.1's owners and pinned twins; each owner's location pinned; a planted second parser bites.
- ADDs, each after its deletions: the trace walk, the lineage refusals, the shipped check, the `milestone` kind, the 0135 contract, the Grammar terms.

### 2.11 Delta summary
- Prod ≈ −160 lines; test lines ≈ −50; test functions ≈ −1. End readout ≈ 24,805 / 1,192 / 44,115. A readout, never a limit (ADR 0142).

## 3. Test strategy

- RED first, in the file that owns the behavior (ADR 0146 (5)); no new test file. Every new or rewritten test carries `Intent: CONTRACT — <AC | bug-id>`.
- A commit adding a test names, in its body, the tests it deleted or rewrote; a DEL's dead tests leave in its commit (G5).
- Owners: AC3.1 `tests/contract/test_public_scripts_thin_wrapper.py`, `tests/unit/core/test_spec_status.py`; AC3.2 `tests/contract/test_release_script.py`, `tests/unit/skills/test_backlog_definition_backlog_script.py`; AC3.3 `tests/unit/skills/test_release_implementation_release_script.py`, `tests/integration/test_worktree_lifecycle.py`; AC3.4, AC3.14 `tests/unit/skills/test_release_implementation_release_script.py`; AC3.5 that file and `tests/unit/features/specs/test_doctor_adr_citations.py`; AC3.6 `tests/integration/test_backlog_doctor.py`, `tests/integration/test_workspace_fix_lines_clear_their_finding.py` (LEDGER-BUGS-SCHEMA); AC3.7, AC3.8 `tests/unit/skills/test_bug_resolution_bugs_script.py`; AC3.9 `tests/integration/cli/test_registry_version_grammar.py`; AC3.10 `tests/unit/features/chokepoints/test_push_denylist_scan.py`, `tests/integration/test_cli_init.py`; AC3.11 `tests/unit/test_one_secret_matcher.py`; AC3.12 the backlog script file; AC3.13, AC4.6, AC4.9 `tests/contract/test_law_states_what_the_code_does.py`; AC3.15 `tests/unit/skills/test_audit_project_audit_script.py`; AC3.16 `tests/contract/test_slop_ratchets.py`; AC3.18 `tests/unit/features/spec_context/test_gate_policy.py`; AC4.1, AC4.4, AC4.7, AC4.8 `tests/contract/test_every_block_carries_a_fix.py`; AC4.2 `tests/unit/hooks/test_venv_guard.py`; AC4.3 `tests/contract/test_cli_help_quality.py`; AC4.5 `tests/integration/test_workspace_fix_lines_clear_their_finding.py`.

## 4. Bootstrap, risks, G4 baseline

- rc-7 opens on `feature/0.5.0` after this definition merges; rc-6 is merged, so no rc-6 write set collides.
- The editable install makes `privacy_check` and gate changes live at once: T-050-139 runs a push scan from its worktree before merge.
- T-050-133 strips every `BUGS.jsonl` line; a parallel `bug` worktree would double records by union, so none opens while it runs.
- ADR 0019's `measured_by` (main-thread ruling on Q1): the impl kind holds no `specs/ADRs/decisions.jsonl`, so right after T-050-132 merges one `docs(adr)` commit in the serial release worktree sets `measured_by` = `pytest tests/contract/test_release_script.py`, citing T-050-132's sha. The closure logs the deviation from SPEC:36's "in the commit that deletes its unit" as a drift.
- G4 baseline, run 36813899731 (seconds): Integration 134, E2E Python 99, Unit fast 54, Unit fast windows 163, Unit fast macos 98, Contract coverage 73, Contract windows 264, Contract macos 87, Typecheck 18, Lint 22, Compliance 15, Importability windows 32, Importability macos 17, Repo hygiene 8. The closure logs each job against it and the tolerance applied.

## 5. Parallel schedule

| step | tasks open together | width | how |
|---|---|---|---|
| 1 | T-050-131, T-050-132, T-050-133, T-050-134, T-050-141 | 5 | one impl worktree each; T-050-133 is the one `bug` worktree |
| 2 | T-050-136, T-050-137, T-050-138, T-050-144, T-050-145 | 5 | one impl worktree each |
| 3 | T-050-135, T-050-139, T-050-140, T-050-142, T-050-146 | 5 | one impl worktree each |
| 4 | T-050-143, T-050-147, T-050-148 | 3 | one impl worktree each |
| 5 | T-050-149 | 1 | one impl worktree |
| 6 | T-050-150 | 1 | measure; closure in the release worktree |

- True edges:
  - 136 needs 131 (`_ledger.records`) and 132 (`doctor_governance.py`);
  - 137 needs 131 (the release unit test file) and 132 (`_release_schema.py`, `_release_tree.py`, `doctor_release.py`, `rules.py`);
  - 138 needs 132 (`_backlog_exit.py`, `backlog.py`, the backlog test, the 0135 test);
  - 139 needs 131 (`_ledger.py`, `_bugs_store.py`), 133 (strip before widened patterns), 136 (the loader);
  - 140 needs 136 (the audit test) and 137 (`_release_tree.py`, the release unit test);
  - 142 needs 138 (`KINDS`); 144 and 145 need 134 (`test_context_baseline.py`, `cli/commands/context.py`); 146 needs 133 (the bugs test);
  - 146 needs 134 (`hooks/root_whitelist.py`, its test);
  - 143 needs 134, 136, 137, 138, 139 (final owners) and 141 (`gate_policy.py`); 147 needs 133, 136, 138, 139, 140 (every check, `_ledger.py`, `ledger_scripts.py`);
  - 148 needs 132, 137, 142, 144 (scaffold releases, RC-FLOW, the law test, getting-started);
  - 149 needs 141, 144, 145, 146, 147, 148 (the sites and the shipped text it judges); 150 needs all.
- Critical path: T-050-132 → T-050-137 → T-050-140 → T-050-147 → T-050-149 → T-050-150 = 6 steps.
- Overlap check: disjoint in every step except `TASKS.md`, the `*.jsonl` ledgers and the derived `pub/entities/behavior-map.json`.
- `bug` worktrees: none opens while T-050-133 runs; every DEL resolve tail opens after T-050-133 merges or batches at G3.
- Merge order inside a step: ready order; after each merge every open sibling rebases onto `feature/0.5.0`.
