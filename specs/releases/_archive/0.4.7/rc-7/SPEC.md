# SPEC — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-project-manager
**Opened:** 2026-09-20
**Origin:** backlog:sdd-verbs-to-skill-scripts,cli-stale-verbs
**Consumes:** sdd-verbs-to-skill-scripts, cli-stale-verbs

---

## 1. Problem and context

Candidate 7 — "ledger verbs to skill scripts" — is the third of the four candidates cut by
the 2026-09-18..20 grill (ADR 0018; rulings Q3, Q4, Q18, Q23, Q32, Q33). Candidates 5 and 6
deleted the dead surfaces and concentrated the law in the universal authored set; this
candidate moves every `specs/`-only write out of the CLI into the skill that instructs it,
so that a skill is self-sufficient (the gate for candidate 8's one-line bootstrap and
standalone skills) and each ledger contract lives in exactly one place.

Measured on the candidate 6 closure (e77ac0f5):

- **Every `specs/` ledger contract lives in three places** that drift separately — the CLI
  verb that writes, the doctor rule that validates, the skill that instructs. Bug history:
  `specs` 44 records, `backlog` 18, `bugs` 18; `doctor` in 102 titles, `release` in 56; the
  provenance bug `backlog-doctor-fix-names-missing-update-verb` (three `fix:` lines naming a
  deleted verb).
- **The CLI carries 50 verbs in 15 groups.** `bugs` (9 verbs, 440 CLI LOC over 459 feature
  LOC), `backlog` (3 verbs over 1,774 feature LOC), `release` (5), `audit` (2), `memory` (2),
  `specs` (2) touch only `specs/`; `context`, `init`, `public`, `ci`, `doctor`, `reports`,
  `certify`, `export`/`import`/`reconcile`, `migrate`, `capabilities`, `help` touch
  `.dadaia/` or the workspace. Every verb drags context resolution, the venv guard and session
  binding into a write of one JSON line.
- **One script exists today:** `dd-cli-library/scripts/registry.py` (server registry, stdlib,
  `--registry` path parameter, tested from `tests/unit/skills/`) — the shape this candidate
  generalises.
- **Uncited verbs (audit 2026-09-20):** `bugs defer|reject|supersede`, `memory catalog
  generate`, `memory product add` are cited by no skill, agent or law and become script
  subcommands; `specs init|upgrade`, `context create|baseline|update|repo|delete` stay as
  internals cited by `dd-cli-library`.
- **Doctor `ledgers` section** (`features/specs/ledgers.py`, 309 LOC) re-implements every
  ledger schema the writers already know; `LEDGER-<NAME>-SCHEMA` findings name a `fix:` that
  must keep resolving after the verbs move.

## 2. Objective

One candidate, one CLOSURE: every write that touches only `specs/` is a minimal stdlib
script under the owning dd- skill's `scripts/` — one file per ledger, `append|<transition>|
check` subcommands, parameterised by the `specs/` path, no `dadaia_workspace` import, exec bit
set, ≤ 150 lines each, tested by the library's pytest — and it is the ONE writer and the ONE
validator of its ledger; the doctor's `ledgers` section delegates to each script's `check`;
the CLI groups `bugs`, `backlog`, `release`, `audit`, `memory` retire; every `fix:` line of
every doctor names a script or verb that exists; the behavior-map hash tuple covers
`scripts/`; the skill corpus stays 18 dirs; the CLI shrinks to workspace operations and
`dd-cli-library` shrinks with it.

## 3. Scope (candidate 7)

### FR1 — The script contract

- Shape: `<skill>/scripts/<ledger>.py`, stdlib only, `#!/usr/bin/env python3`, exec bit,
  `--specs <path>` (default: the nearest `specs/` at or above the cwd whose parent holds
  `.git`, else refuse with the one `fix:` line), subcommands `check` (schema + invariants of
  the whole ledger, exit 1 on any finding, one `<CODE> error <message>` line each) plus the
  writes named per ledger; every write runs `check` on the result before replacing the file
  atomically; `--json` on read verbs. Scripts never call each other; a composition is a
  numbered step in the skill.
- The library tests scripts as subprocesses from `tests/unit/skills/test_<skill>_<ledger>_
  script.py` (the `registry.py` precedent); the schemas the scripts enforce are the shipped
  JSON schemas under `public/schemas/` read from the skill's own copy (`scripts/schemas/`
  symlink or copy at stage — decide in PLAN so the script has no import path into the lib).
- `tests/contract/test_public_scripts_thin_wrapper.py` (ADR 0018 measured_by): every script
  ≤ 150 lines, stdlib imports only, exec bit set, `--help` exits 0, `check` exists.
- **AC1.1** `find public/skills -path '*/scripts/*.py'` lists exactly the scripts of FR2 plus
  `registry.py`; each passes the contract test.

### FR2 — The ledgers move

| Ledger | Script | Writes | Retired CLI |
|---|---|---|---|
| `bugs/BUGS.jsonl` | `dd-bug-resolution/scripts/bugs.py` | `append resolve defer reject supersede update archive status stats` | `dadaia bugs *` |
| `backlog/BACKLOG.json` + histo | `dd-backlog-definition/scripts/backlog.py` | `new exit subjects` | `dadaia backlog *` |
| `releases/<id>/_RELEASE.json` + trio + histo | `dd-release-implementation/scripts/release.py` | `new phase rc-archive archive fold` | `dadaia release *` |
| `audits/<dir>/FINDINGS.jsonl` + histo | `dd-audit-project/scripts/audit.py` | `disposition close` | `dadaia audit *` |
| `memory/product/index.md`, `catalog.json` | `dd-spec-navigator/scripts/memory.py` | `catalog generate`, `product add` | `dadaia memory *` |

- `dd-bug-registration` cites `bugs.py append`; `dd-release-definition` cites `release.py
  new`; `dd-release-implementation` cites `phase|rc-archive|archive`; every skill's step that
  named a `dadaia <group>` verb now names the script; `dd-cli-library` drops the five groups.
- The feature packages behind the retired groups (`features/bugs`, `features/backlog`,
  `features/specs/{candidate,release_*,catalog}` and the `cli/commands/{bugs,backlog,audit,
  memory}.py` modules, the release verbs inside `specs.py`) are deleted once the scripts and
  their tests are green; whatever the doctor still needs from them (readers for `SPEC-DOC-*`
  and `RELEASE-TREE-*`) stays as a reader only. `RETIRED_FEATURE_PACKAGES` gains the names
  that leave (F7 from candidate 5 owes its retirement path in candidate 8).
- The scaffolded `specs/*/AGENTS.md` and the law name the scripts, never the verbs; `docs/
  cli.md` regenerated; CHANGELOG.
- **AC2.1** `dadaia --help` lists no `bugs`, `backlog`, `release`, `audit`, `memory` group;
  `dadaia help tree` has ≤ 30 verbs.
- **AC2.2** This repo's ledgers pass every script's `check`; `dadaia bugs status` is replaced
  in every skill, agent and law by `bugs.py status` and the grep for `dadaia bugs` under
  `public/` returns nothing.

### FR3 — The doctor delegates

- `dadaia doctor`'s `ledgers` section runs each script's `check --specs <dir>` as a subprocess
  (the ONE validator) and re-emits its lines under `LEDGER-<NAME>-SCHEMA`; the schema
  re-implementation in `features/specs/ledgers.py` is deleted. `RELEASE-TREE-*`, `SPEC-DOC-*`,
  `BL-*` rules that read ledgers for cross-checks stay readers.
- Every `fix:` line of every doctor rule names a script invocation or a surviving verb;
  `tests/contract/test_every_block_carries_a_fix.py` resolves each fix target on disk.
- **AC3.1** `dadaia doctor --specs-dir specs` exit 0 on this repo; a hand-corrupted ledger in
  a tmp tree yields one `LEDGER-*` line whose `fix:` names the script.

### FR4 — Behavior map, ratchets, corpus

- `public/entities/behavior-map.json` `hash_tuple` covers the skill folder (SKILL.md + every
  file under `scripts/`); `test_behavior_map.py` red on a script changed without its hash.
- V35 stays ≤ 18 dirs / 2881 Markdown lines (scripts are `.py`, outside V35); a new ratchet
  pins the script corpus (files, lines) downward; `lint-dadaia-cli-reachability.py` learns
  the script paths; `import-linter` contracts follow the deleted packages.
- The seven generic skills (`dd-grill-me`, `dd-codebase-design`, `dd-code-review`,
  `dd-domain-modeling`, `dd-test-stewardship`, `dd-architecture-survey`, `dd-ai-eng-knowhow`)
  STAY in `public/` this candidate (Q14: marketplaces in candidate 8).
- **AC4.1** ratchets re-pinned downward; LOC of `dadaia_workspace/` below 36,315.

### FR5 — Closure

- Memory pass (`sdd-bug-backlog-governance`, `workspace-doctor`, `agentic-entities`,
  `cli-*` atoms, ARCHITECTURE/TECHSTACK Part 2), CHANGELOG "Candidate 7 — ledger verbs to
  skill scripts", `_RELEASE.json` log, live instance reflected, push, dd-code-review, PR
  #260 updated.
- **AC5.1** Every CI job green; review APPROVED; `dadaia doctor` exit 0 on the live instance.

## 4. Out of scope

- `harness add`, `init <dir>`, release-please, marketplaces, new harnesses — candidate 8.
- Moving `context`, `public`, `ci`, `doctor`, `init`, `certify`, `export/import/reconcile`,
  `migrate` (they touch `.dadaia/`).
- Rewriting `releases/_archive/**` or any histo.

## 5. Decisions and constraints

- ADR 0018 (accepted 2026-09-20) governs; a new verb enters only when an old one leaves.
- D1 (operator): `CLAUDE_API_KEY` + required check — still open; PR #260 red on that check.
- Bug policy: a script that breaks its own `--help` contract is Arm B, fixed at once.

## 6. Traceability

| Requirement | Tasks |
|---|---|
| FR1 | T-047-63 |
| FR2 | T-047-64, T-047-65, T-047-66, T-047-67 |
| FR3 | T-047-68 |
| FR4 | T-047-69 |
| FR5 | T-047-70 |
