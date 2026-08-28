# Architecture metrics baseline — HEAD `974a045f` (`feature/0.4.5`), 2026-08-26

**Purpose.** Quantitative snapshot of `dadaia_workspace/` before release 0.5.0, so reviewers
can re-run the Appendix commands at closure and diff. Numbers are measured unless marked
*heuristic*. Venv tools used: radon 6.0.1, import-linter 2.13, pytest 9.1.1, ruff 0.15.20
(nothing installed). LOC = non-blank, non-comment, non-docstring lines (tokenize + ast).

## 1. Size

| Package | LOC | Files | Raw lines |
|---|---:|---:|---:|
| `infrastructure` | 5,786 | 37 | 9,652 |
| `features/panel` | 4,560 | 37 | 6,544 |
| `cli` | 3,708 | 28 | 5,412 |
| `features/specs` | 2,710 | 14 | 4,203 |
| `core` | 2,155 | 58 | 4,786 |
| `features/telemetry` | 2,087 | 17 | 3,470 |
| `features/spec_context` | 1,466 | 6 | 2,454 |
| `hooks` | 1,132 | 8 | 2,317 |
| `features/backlog` | 1,044 | 7 | 1,838 |
| `features/migrate` | 847 | 12 | 1,490 |
| `features/chokepoints` | 659 | 3 | 1,293 |
| `features/reports` | 640 | 4 | 922 |
| root (`container.py`, `__main__.py`, `__init__.py`) | 418 | 3 | 743 |
| `public/scripts` (py only) | 377 | 3 | 666 |
| 16 smaller feature packages (`certification` 358 … `repos` 8; each listed in Appendix output) | 2,578 | 37 | 4,222 |
| **Total** | **30,167** | **274** | **50,004** |

`features/` in aggregate: 16,591 LOC over 137 files in 25 feature packages (55% of prod
LOC). Two shell hook scripts (not counted above): `pre-commit-presence-gate.sh` 86 lines,
`pre-push-ci-gate.sh` 108 lines.

**Largest 15 modules (LOC / raw):** `infrastructure/public_assets.py` 1,048/1,401 ·
`cli/commands/context.py` 737/1,014 · `infrastructure/codex_doctor.py` 691/962 ·
`features/panel/views/assets/css/structure.py` 618/626 · `features/spec_context/service.py`
579/978 · `features/telemetry/aggregator/queries.py` 541/829 · `cli/commands/reports.py`
527/747 · `features/chokepoints/service.py` 503/950 · `infrastructure/install_helpers.py`
436/646 · `infrastructure/git_objects.py` 431/931 · `container.py` 415/737 ·
`features/panel/handler.py` 414/735 · `features/spec_context/doctor.py` 412/587 ·
`features/specs/doctor_release.py` 410/570 · `infrastructure/runtime_config.py` 388/620.

**Ceilings** (`tests/contract/test_module_size_ceiling.py`: `doctor*.py` ≤ 700 raw lines,
`panel/views/api*.py` ≤ 450): **0 modules over**. Headroom is thin only for
`doctor_release.py` (570) and `doctor_memory.py` (504); the panel `api*` max is
`api_agents.py` at 390. Note the ratchet covers only two globs — the top-5 largest modules
sit under no ceiling at all.

## 2. Complexity

radon `cc -s -j` over 1,975 callables (functions + methods; methods are counted once
under their class and once flat, so 13 rows are duplicates):
**mean 4.02, median 2, > 10: 131, > 20: 13, max 61.** The stdlib-`ast` fallback (1,473
plain functions) agrees: mean 4.41, median 3, > 10: 114, > 20: 16.

**Top 20 (radon CC · function · module:line):**

| CC | Function | Module |
|---:|---|---|
| 61 | `_list_agents_impl` | `features/telemetry/aggregator/queries.py:181` |
| 40 | `doctor` | `infrastructure/public_assets.py:802` |
| 40 | `_validate_node` | `infrastructure/stdlib_handoff_validator.py:93` |
| 37 | `validate` | `cli/commands/reports.py:319` |
| 35 | `read_session_file` | `features/telemetry/reader/claude.py:178` |
| 31 | `show` | `cli/commands/context.py:394` |
| 31 | `main` | `hooks/ctx_inject.py:396` |
| 30 | `doctor` | `cli/commands/specs.py:61` |
| 30 | `alive` | `features/spec_context/service.py:546` |
| 26 | `upgrade` | `cli/commands/specs.py:193` |
| 20 | `lint` | `cli/commands/reports.py:507` |
| 20 | `check_phase_markers_coherence` | `features/specs/doctor_release.py:348` |
| 20 | `_raw_to_dto` | `features/agents/reader.py:129` |
| 19 | `repack_installed_wheel` | `infrastructure/python_env.py:34` |
| 19 | `fix` | `features/spec_context/doctor.py:508` |
| 19 | `evaluate_payload` | `hooks/venv_guard.py:243` |
| 18+ | (ast-only) `make_handler_class` 58 | `features/panel/handler.py:330` (radon counts nested defs separately) |

**Ruff ceilings** (`pyproject.toml`): `max-complexity = 63`, `max-nested-blocks = 6`, both
"pinned at the measured maximum, ratchet down only". Functions within 20% of the CC
ceiling (≥ 51): **2** (both rows of `_list_agents_impl`). The ceiling is therefore
non-binding for 99.9% of the code. Re-running ruff at a conventional `max-complexity=10` /
`max-nested-blocks=3` reports **131 violations** (57 `C901`, 74 `PLR1702`) — the number a
reviewer should expect the release to lower, not raise. Functions at CC ≥ 8: 282 (14%).

## 3. Coupling

`lint-imports`: **9 contracts, 9 kept, 0 broken.** `ignore_imports` per contract (total
**15**, equal to `_RECORDED_IGNORE_EDGE_CAP = 15` and the per-family map in
`tests/contract/test_import_linter_ignore_cap.py`):

| Contract | Type | Ignored edges |
|---|---|---:|
| `features-no-infrastructure` | forbidden | 7 |
| `features-no-subprocess` | forbidden | 3 |
| `cli-no-infrastructure` | forbidden | 3 |
| `features-no-cross-feature` | independence | 2 |
| `core-no-os-primitives`, `core-no-upper-layers`, `infrastructure-no-upper-layers`, `kernel-tunables-is-a-leaf`, `bind-resolution-seam-is-a-single-home` | forbidden | 0 each |

**Package-level import graph** (ast, `from`/`import` edges resolved to package; 231
inbound edges to `core`):

| Package | fan-out | fan-in | Notes |
|---|---:|---:|---|
| `core` | 0 | 231 | bottom layer, clean |
| `infrastructure` | 54 | 36 | 53 → `core`, 1 → root (`container`) |
| `cli` | 117 | 1 | 46 → `core`, 17 → root, 3 → `infrastructure`, 51 → 19 feature packages |
| root (`container.py`) | 67 | 18 | composition root: 24 → `infrastructure`, 33 → 14 features |
| `hooks` | 21 | 0 | 15 → `core`, 4 → `features/spec_context`, 2 → `infrastructure` |
| `public/scripts` | 2 | 0 | 2 → `features/specs` |
| `features/spec_context` | 15 | 12 | most-imported feature (hooks + chokepoints + container) |
| `features/panel` | 10 | 17 | 14 edges from `container` |
| `features/specs` | 11 | 7 | 1 → `features/backlog` (sanctioned) |
| `features/backlog` | 4 | 9 | 8 from `cli` |
| `features/telemetry` | 9 | 9 | 2 → `infrastructure` |
| `features/migrate` | 10 | 5 | 2 from `features/reconcile` |
| `features/reconcile` | 3 | 1 | **all 3 out-edges are feature→feature** |
| `features/chokepoints` | 5 | 6 | 1 → `features/spec_context`, 1 → `infrastructure` |
| remaining 17 features | 1–8 | 1–3 | `core` only, plus 1 → `infrastructure` in `ci_preflight`, `import_`, `public`, `server_registry` |

**Cross-feature edges (should be 0): 5 module-level edges**, of which 2 are declared in
`ignore_imports` and 3 are invisible to the contract because `features.reconcile` and
`features.capabilities` are **not listed** in the independence contract's `modules =`:

- `features/specs/doctor_governance.py:19` → `features.backlog.document` (ignored)
- `features/chokepoints/service.py:49` → `features.spec_context` (ignored)
- `features/reconcile/service.py:12` → `features.capabilities` (unlisted — not checked)
- `features/reconcile/service.py:13` → `features.migrate.legacy_dadaia_dirs` (unlisted)
- `features/reconcile/service.py:14` → `features.migrate.state_v2` (unlisted)

Feature→`infrastructure` edges: 7 (all ignored). `hooks` → feature edges: 4, all into
`spec_context` (the SPEC's FR4 moves the phase read to `core/release_events.py`, which
should reduce this to 0 if `sdd_gate.py` stops importing `gate_policy`; verify).

## 4. Side effects

358 call sites matched (`open(`, `.write_text/bytes(`, `.mkdir(`, `.unlink(`,
`.rename/replace(`, `os.` mutators, `subprocess.`, `shutil.`, `json.dump(`; comment lines
excluded; *heuristic* — matches include reads via `open(` and `subprocess.run` wrappers).

| Package | total | subprocess | os.mut | mkdir | shutil | rename/replace | unlink | write_text/bytes | open |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `infrastructure` | 125 | 46 | 22 | 20 | 12 | 10 | 7 | 0 | 8 |
| `features/spec_context` | 34 | 0 | 5 | 5 | 10 | 5 | 7 | 1 | 1 |
| `core` | 32 | 1 | 15 | 3 | 3 | 3 | 2 | 4 | 1 |
| `features/migrate` | 24 | 0 | 1 | 5 | 6 | 5 | 3 | 2 | 2 |
| `features/specs` | 19 | 0 | 0 | 8 | 1 | 0 | 1 | 9 | 0 |
| `hooks` | 16 | 2 | 3 | 3 | 0 | 0 | 5 | 3 | 0 |
| `cli` | 15 | 4 | 0 | 3 | 1 | 3 | 1 | 2 | 1 |
| `features/telemetry` | 11 | 0 | 6 | 1 | 0 | 2 | 0 | 0 | 2 |
| 17 other packages | 82 | 10 | 2 | 22 | 13 | 20 | 9 | 10 | 5 |

`json.dump(` direct calls: 0 (all JSON writes route through `core/atomic_write.py`, which
alone holds 14 sites). **Edges** (top write-concentrating modules): `infrastructure/python_env.py` 18,
`infrastructure/install_helpers.py` 15, `core/atomic_write.py` 14, `features/spec_context/service.py`
12, then 9 each: `hooks/sdd_post_gate.py`, `infrastructure/public_assets.py`,
`infrastructure/process_probe_adapter.py`, `features/telemetry/service.py`.

**Mixed modules** (contain a writing function *and* ≥ 3 non-writing functions, one ≥ 5
lines): **53 of the 77 writer modules** (274 total). 35% of the feature-layer writer
modules are `service.py` files (`academy`, `tmp_gc`, `chokepoints`, `workspace`,
`reconcile`, `workspace_clean`, `ci_preflight`, `telemetry`, `import_`, `spec_context`,
`certification`, `export`) — compute and I/O live in one file. `features/spec_context` is
the worst case: 5 of its 6 modules are mixed.

## 5. Hand-kept truth

Module-level UPPER_CASE / `_UPPER` constants that are collections of ≥ 2 names/paths or a
compiled regex: **264** (112 `re.compile`, 152 tuple/list/set/frozenset/dict). By package:
`infrastructure` 47, `features/specs` 47, `core` 43, `features/backlog` 18,
`features/panel` 16, `hooks` 14, `features/spec_context` 11, `features/migrate` 10,
`features/telemetry` 9, `public/scripts` 8, `cli` 7, rest ≤ 6.

**Top 20 by cardinality (file:line):**

| n | Name | Location |
|---:|---|---|
| 25 | `_HEADING_GROUP_G` | `features/specs/memory_lint.py:180` |
| 25 | `_HEADING_GROUP_D` | `features/specs/memory_lint.py:126` |
| 22 | `_HEADING_GROUP_C` | `features/specs/memory_lint.py:97` |
| 21 | `_ASSETS` | `features/panel/views/static.py:57` |
| 19 | `_ROUTE_TABLE` | `features/panel/handler.py:176` |
| 18 | `DADAIA_ALLOWED_SUBDIRS` | `core/workspace_layout.py:42` |
| 18 | `_SECRET_SCAN_TEXT_SUFFIXES` | `features/spec_context/service.py:126` |
| 16 | `_OPTIONAL_STR_FIELDS` | `core/models/bugs.py:204` |
| 15 | `_ALLOWED_FIELDS` | `features/agents/reader.py:72` |
| 14 | `SUPPORTED_KEYWORDS` | `infrastructure/stdlib_handoff_validator.py:44` |
| 13 | `_HEADING_GROUP_B` | `features/specs/memory_lint.py:77` |
| 13 | `_PUBLIC_PRIVACY_TEXT_SUFFIXES` | `infrastructure/privacy_check.py:32` |
| 12 | `_WANTED_COLUMNS` | `features/telemetry/reader/codex.py:56` |
| 12 | `_CONTENT_TYPES` | `features/panel/views/memory.py:55` |
| 12 | `_COPY_DIRS` | `infrastructure/public_assets_common.py:53` |
| 11 | `ALLOWED_TOP_LEVEL_KEYS` | `features/telemetry/reader/allowlist.py:22` |
| 10 | `_KNOWN_STATUSES` | `features/backlog/doctor.py:78` |
| 10 | `_RELEASE_KEYS` | `features/migrate/bugs_jsonl.py:48` |
| 10 | `_CODEX_SKILL_REF_PREFIXES` | `infrastructure/runtime_transforms/codex_assets.py:50` |
| 9 | `RELEASE_NAMING_LEGACY_ALLOWLIST` | `features/specs/doctor_release.py:67` |

Two mirrors are directly in 0.5.0's path: `_OPTIONAL_STR_FIELDS` (mirrors
`bug-event-v1.schema.json`; FR2 says the field set "derives from" the new record schema)
and the four `memory_lint.py` heading groups (85 hand-listed headings; FR17 restructures
the memory trio). Prose-parsing regexes on release documents — the class FR15 deletes —
are counted in `features/specs`: `doctor_closure_audit.py` 2, `doctor_governance.py` 6,
`doctor_release.py` 1, `doctor_common.py` 1, `memory_lint.py` 3, `backlog/document.py` 7,
`hooks/sdd_gate.py` 2 (`_active_field`). `CLOSURE`-literal references inside `features/specs`:
30 across 7 modules; modules reading `ACTIVE.md`: 10; reading `CLOSURE.md`: 4.

## 6. Tests

- **Test functions: 1,859** (`def test_*` in 396 files); `pytest --collect-only -q`
  collects **2,873** items (parametrization). By directory: `unit` 1,376 · `integration`
  241 · `contract` 200 · `e2e` 42.
- **Tier markers** are module-level (`pytestmark`): `unit` 56 files, `contract` 31,
  `integration` 34 (15 also `slow`), `e2e` 5 files (+1 with `e2e` in a list) — 15 test
  functions carry the `e2e` marker although 42 live under `tests/e2e/` (27 are marked
  `integration`/unmarked). Per-function markers: `parametrize` 251, `skipif` 20,
  `timeout` 5, `slow` 2.
- **Tests per 100 prod LOC: 6.2** (1,859 / 30,167).
- **Implementation-pinning tests** (import of a `_private` symbol from `dadaia_workspace`):
  24 import statements in 14 files; 35 files import at least one underscore name
  (*heuristic*).
- **Exact user-facing-string assertions** (*heuristic*: `assert ... == "..."` or
  `"Sentence case" in output`): **117** functions.
- **skip / xfail / quarantine**: 28 (all `skipif`, platform-conditional; 0 `xfail`,
  0 `quarantine`, 0 `flaky`).
- **Declared intent** (`dadaia-test-stewardship` §A: `Intent: <KIND>` in the *module*
  docstring): **94 of 396 files** — CONTRACT 84, REGRESSION 6, SENTINEL 4; explicit
  `Size:` line in 12 files. **302 files (76%) are undeclared** and therefore SCAFFOLD by
  §A ("an undeclared test is SCAFFOLD — the default is to die"). Declared SCAFFOLD: 0.
- **LARGE census**: `PARAMETERS.md` declares the LARGE (E2E) cap at **30** and records
  "current ~84"; measured today: 42 functions under `tests/e2e/`, 15 `e2e`-marked. The
  task's "100 ratchet" does not exist in the repo; the declared cap is 30 (WARN-only).
- **Golden/snapshot/fixture data files**: 25 non-Python files under `tests/fixtures/`,
  1,233 lines total.
- **Wall-clock**: no recorded `unit-fast` duration in the repo (`release.yml` job timeout
  2 min; collection alone 5.1 s locally).

## 7. Governance-cycle surface

| Surface | Count |
|---|---:|
| CLI leaf commands (`dadaia --help` recursive) | **71** in 20 groups |
| Harness hooks (projected `settings.json`): `PreToolUse` 1 (`pre_gate`), `PostToolUse` 1, `SessionStart` 2, `UserPromptSubmit` 1 | **5** registrations over 3 hook modules (+`_common`, `root_whitelist`, `venv_guard`, `sdd_gate` = 8 files, 1,132 LOC) |
| Git hooks (shell) | **2** (`pre-commit-presence-gate.sh` 1 hard exit; `pre-push-ci-gate.sh` 1 hard exit + `ci preflight --quick` call) |
| Skills (`public/skills/`) | 21 |
| Personas (`public/agents/`) | 9 |
| Scoped `AGENTS.md` shipped by the library | 4 (`data/`, `scaffold/`, `scaffold/memory/`, `kimi-code/`) |
| Doctor check codes (`SPEC-DOC-|TREE-|INV-|ROOT-|CAT-|LINT-|BL-|EFF-`) | **47** — SPEC-DOC 25, TREE 8, BL 4, ROOT 4, INV 3, CAT 1, EFF 1, LINT 1 |
| Public schemas / entity maps | 6 schemas (`bug-event-v1` among them) + `rules-skills-map.json` |
| Scaffold `README.md` files | 4 |
| Always-on tokens (T-045-27 after-capture, Claude Code) | **21,511** (law chain 3,692 · 9 personas 16,344 · 21 skill descriptions 1,475); negations 254; target 3.5k missed ~6.15× |

## 8. Delta projection for 0.5.0 — claims to verify against this baseline

From the SPEC's 19 `Bug-surface direction` lines and its named deletion lists. Columns
are the *claim*; the reviewer fills the *measured* column at closure.

| FR | Claimed direction | Concrete deletions / additions (SPEC text) | Baseline anchor |
|---|---|---|---|
| FR1 | LOC +, surface − | `specs/assets/`, `backlog/remote-bugs/`, root `specs/_archive/`, 4 scaffold `README.md` deleted; TREE-8 added (WARN); `RELEASE_SEMVER_RE` flip (3 prod consumers) | 4 READMEs; 8 TREE codes; `_FROZEN_PREFIX` at `gate_policy.py:73` |
| FR2 | net − | `bug-event-v1.schema.json` retires; `BugEvent` + fold logic deleted; `jsonl_bug_store.py` (`_BUG_LOG_RE`, `_sorted_files`, `ROWS_PER_FILE`) and `core/protocols/bug_store.py` deleted | 134 + 27 + 404 (`models/bugs.py`) + 146 (`bugs/service.py`) lines; `_OPTIONAL_STR_FIELDS` (16) |
| FR3 | net + (migration module, deletable after) | `features/bugs/migrate_v5.py` **new**; `migrate/bugs_jsonl.py` v3→v4 logic deleted | 322 lines; 2 regexes |
| FR4 | surface −, LOC + | `ACTIVE.md`/`CLOSURE.md` retire; `_active_field` + regex in `sdd_gate.py` deleted; `core/release_events.py` **new**; 10 `ACTIVE.md` readers repointed | `sdd_gate.py` 281 lines, 2 regexes; hooks→spec_context edges 4 |
| FR5 | net − | in-file `## LEDGER` retires; BL-DUP rule deleted (`backlog/doctor.py:98`); `backlog_histo.jsonl` | 4 BL codes; `document.py` 674 lines, 7 regexes |
| FR6 | (operator) | root `specs/_archive/` tagged then deleted; FROZEN prefix 1 deletion + 1 addition | `_FROZEN_PREFIX` single string |
| FR7 | AI +, code 0 | `dd-diagnose` skill **new**; A7.5: zero files under `cli/`, `hooks/` | 71 CLI leaves; 8 hook files |
| FR8 | code −, rule + | one resolver function; shape 3b (follow-up ledger commit) deleted; no CLI/hook change | — |
| FR9 | **net −, unambiguous** | `_run_backlog_doctor_gate` (`ci.py:181`) + `_staged_backlog_paths` (`ci.py:159`) deleted; pre-commit advisory-only; preflight leaves pre-push; V10: `git diff --stat` negative | `ci.py` 455 lines; hook scripts 86 + 108 lines; 2 hard exits → 1 |
| FR10 | tests +, unmapped − | `behavior-map.json` supersedes `rules-skills-map.json` (one map at end); no runtime reader | 1 entity map + 1 schema |
| FR11 | tokens + (governed by V12) | `DADAIA.md` anchors + 3 short sections | 21,511 always-on tokens |
| FR12 | AI lines − (V11) | `CLOSURE-TEMPLATE.md`, `CLOSURE-CHECKS.md` deleted; `dd-bug-fix` → `dd-bug-resolution`; `dd-release-implement` rebuilt | 21 skills |
| FR13 | net + (schema + folder) | `finding-record` schema **new**; `specs/audits/README.md` deleted | 6 schemas |
| FR14 | AI +, code − | `dd-audit-project` skill; A14.5 zero CLI verbs, zero hook changes | 71 / 5 / 2 |
| FR15 | **net −** | every `CLOSURE.md` parser deleted: `AUDIT_DIR_NAME_RE`, `RELEASE_ARTIFACTS`, disposition regexes in `doctor_closure_audit.py`, `doctor_release.py`, `doctor_common.py` | 312 + 570 + 116 lines; 4 regexes; 30 CLOSURE refs |
| FR16 | neutral | data only | — |
| FR17–18 | neutral in code | memory trio split; unmeasured rules deleted or demoted | `memory_lint.py` 545 lines, 85 hand-listed headings |
| FR19–21 | docs +, code 0 | `specs/ADRs/`; `constitution.md` restatement deleted | — |
| FR22 | invariants | A22.6: **0 new CLI verbs, 0 new hook blocks, exactly 2 blocks removed**; layer rules hold; ignore cap ≤ 15 | 71 leaves; 2 hard exits; cap 15 |

**Net expectations the architect can check at closure:** CLI leaves 71 → **71**; git-hook
hard exits 2 → **1** (pre-push branch/denylist only); harness hook registrations 5 → 5;
doctor codes 47 → ≤ 47 (+TREE-8, −BL-DUP, −CLOSURE-parsing SPEC-DOC codes); `re.compile`
in `features/specs` + `hooks/sdd_gate.py` 14 → lower; hand-kept collections 152 → lower
(`_OPTIONAL_STR_FIELDS` derived from schema); `hooks → features/spec_context` edges 4 →
lower; ignore-cap 15 → ≤ 15; schemas: `bug-event-v1` out, `bug-record-v1` +
`finding-record-v1` in; always-on tokens 21,511 → measured by V12; CC > 10 count 131 and
the two functions ≥ 51 unchanged unless the release touches them (none listed).

## Appendix — commands (repo root; `$V` = workspace venv `bin/`)

```
$V/python .dadaia/tmp/claude-code/20260826/metrics/m1.py   # §1,2(ast),3(graph),4,5: tokenize+ast script
$V/radon cc -s -j dadaia_workspace > radon.json              # §2
$V/ruff check --no-cache --select C90,PLR1702 --config "lint.mccabe.max-complexity=10" \
  --config "lint.pylint.max-nested-blocks=3" dadaia_workspace --statistics
$V/lint-imports                                              # §3 (+configparser count of ignore_imports lines)
$V/python -m pytest --collect-only -q -p no:cacheprovider tests | tail -1   # §6
grep -rlE "^\s*Intent:" tests --include=test_*.py | wc -l ; grep -rhoE "pytestmark\s*=.*" tests | sort | uniq -c
$V/dadaia --help   # §7, recursed over every "Commands:" entry with COLUMNS=200
grep -rhoE '"(SPEC-DOC|TREE|INV|ROOT|CAT|LINT|BL|EFF)-[0-9A-Z]+' dadaia_workspace | sort -u | wc -l
grep -nE "^\*\*Bug-surface direction" specs/releases/_ideas/0.5.0/SPEC.md   # §8
```
