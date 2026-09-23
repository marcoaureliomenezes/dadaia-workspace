# SPEC — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** project-manager
**Opened:** 2026-09-20
**Origin:** backlog:panel-demolition,delete-advisory-presence,doctor-drop-scores,verdict-as-required-check,roster-three-roles-review-lenses,persona-least-privilege,cli-stale-verbs
**Consumes:** panel-demolition, delete-advisory-presence, doctor-drop-scores, verdict-as-required-check, roster-three-roles-review-lenses, persona-least-privilege, cli-stale-verbs

---

## 1. Problem and context

Candidate 5 — "demolition" — is the first of four candidates cut by the 2026-09-18..20 grill
(rounds 1..3, Q1..Q37; ADRs 0016..0021). The operator's priority is a lighter library: delete
every surface the competitive report and the value scale ranked as no-value or negative-value
BEFORE the law is rewritten (candidate 6), the ledger verbs move into skill scripts (candidate
7) and the bootstrap/flows/launch land (candidate 8). Deleting first means nothing dead gets
translated, renamed or mapped. No bug is open (`BUGS.jsonl`: 0 `open`).

Measured today (`dadaia_workspace/`: 48,816 LOC; `tests/`: 464 files, 2,147 test functions):

- **Panel + telemetry.** `features/panel/` 4,947 LOC + `cli/commands/panel*.py` 317 LOC; 17 bugs,
  three redesigns. `features/telemetry/` (store, service, readers claude/codex/kimi) exists only
  for the panel and for the HANDEDIT rules (`LEDGER-*-HANDEDIT`, `RELEASE-TREE-HANDEDIT`), which
  read the governance-event table written by `cli/_governance_event.py` (74 LOC, 8 call sites).
  `mistune` is panel-only. The panel is the only writer of `.dadaia/states/agent_model_policy.json`.
- **Advisory presence.** `features/spec_context/presence.py` 509 LOC, imported by hooks, gate,
  reaper, `ci pre-commit-check`, `context heartbeat/release`; three presence bugs since NO-LOCKS;
  ADR 0002 makes one session per checkout operator practice, so presence guards a race the
  topology already removes (ADR 0016 amends 0002).
- **Server registry.** `features/server_registry/` 389 LOC + `cli/commands/server.py` 291 LOC,
  read by the CLI and the panel tab only. Operator ruling Q3: the JSON stays, the verbs become
  minimal scripts under one dd- skill, the CLI group dies.
- **Doctor scores.** `compliance(<section>) N/M (P%)` and `compliance(total)` in
  `cli/commands/doctor.py` and `core/doctor_rules.py`; nobody asks for a percentage, they ask
  "fail my CI when a rule cites a superseded decision".
- **Verdict machinery.** `features/chokepoints/verdict.py` 193 LOC, `ci verdict-check`,
  `.github/scripts/pr-verdict-check.sh`, jobs `verdict-gate` and `security-verdict-gate` in
  `.github/workflows/ci.yml`, SPEC-DOC-044, the `verdicts/` canon rows, the pre-push wiring
  (`push_gate.py` via `ci.py`); six verdict bugs; a stale verdict was deleted by `doctor --fix`
  on 2026-09-20. The official `anthropics/claude-code-security-review` Action (6.2k stars, updated
  2026-09-20) reviews the PR diff and posts a status check.
- **Roster.** Nine personas (73 KB), `CORE_AGENTS` in `core/agent_model_templates.py`, five
  tests pinning nine, behavior-map §2 owner rows, skill grants, `_FABLE_FORBIDDEN_AGENT =
  security-reviewer`, `dd-manager-orchestration` as a nine-persona router (5.4 KB). Operator
  verdict: PM, software-engineer, code-reviewer; every other role is a review lens.
- **`_ideas/`.** 9 lib files + 5 tests + behavior-map + shipped-hashes keep a directory redundant
  with the backlog; the live tree holds only its AGENTS.md.
- **Uncited verbs.** 22 of 55 verbs are cited by no skill, agent or law (audit 2026-09-20); the
  ones with no other entry: `context heartbeat`, `context release`, `repos list` (+ `openpyxl`,
  `public/data/repos.xlsx`, `infrastructure/excel_reader.py`), `public list`, `reports doctor`.

## 2. Objective

One candidate, one deletion pass, one CLOSURE: the surfaces above are gone, what they controlled
survives in its minimal form (a policy JSON, a registry JSON managed by a skill script, a
required status check), every ratchet is re-measured downward, and the live instance is clean
after `public stage` -> `public install` -> `doctor`. Deletion tests (RED before, absent after)
live under `tests/tmp/` (gitignored, operator ruling Q1); the permanent proof is the ratchet and
the contract tests named below.

## 3. Scope (candidate 5)

### FR1 — Panel, telemetry, HANDEDIT

- Delete `features/panel/`, `cli/commands/panel.py`, `cli/commands/panel_composition.py`, the
  `dadaia panel` verb, `features/telemetry/` (store, service, readers, adapters), the
  `TelemetryStore` wiring in `container.py`, `cli/_governance_event.py` and its 8 call sites,
  the HANDEDIT rules (`LEDGER-<NAME>-HANDEDIT`, `RELEASE-TREE-HANDEDIT`) in `features/specs/
  {ledgers,rules,doctor,release_tree}.py` and `cli/commands/doctor.py`, `mistune` from
  `pyproject.toml`, the `panel` and `agent-monitoring` catalog atoms, and every test under
  `tests/**/panel*`, `tests/**/telemetry*`, `tests/**/*governance_event*`.
- `.dadaia/states/agent_model_policy.json` is the interface (Q4): `public install --target
  agents` keeps reading it; `core/agent_model_templates.py` ships exactly two default templates
  with per-harness `(model, effort)`; `public doctor` keeps validating the schema. No verb.
- `features/panel/entities.py::load_registry` consumers (`tests/contract/
  test_agentic_entities_derivation.py`) rehome onto `public/entities/registry.json` directly.

### FR2 — Advisory presence and its verbs

- Delete `features/spec_context/presence.py`, the `presence` zone row (`core/workspace_layout.
  DADAIA_ZONES`), `PRESENCE-GC`, `PRESENCE_TTL_SECONDS` (`core/kernel_tunables.py`), the
  pre-commit presence hook (`features/chokepoints/pre_commit.py`, `pre-commit-presence-gate.sh`,
  the `INSTALLED_GIT_HOOKS` row), `ci pre-commit-check`, `context heartbeat`, `context release`,
  and every presence read in the 33 importing modules (an allowed MUTATING write records
  nothing; `sdd_post_gate` keeps only the reaper throttle).
- The throttle-marker idiom moves into the reaper (`features/workspace/sweep.py`); marker GC is
  the reaper's. `HOOKS-DRIFT-1` checks `pre-push` only.
- ADR 0002 is amended by ADR 0016: measured by "no module imports presence, no presence zone".

### FR3 — Server registry as a skill script

- `dd-cli-library/scripts/registry.py` (the V35 skill-corpus ratchet forbids a 19th skill dir)
  (stdlib, `--registry <path>` defaulting to `.dadaia/states/server_registry.json`): subcommands
  `register`, `list`, `next`, `release`, `scan`, `clean`, same JSON shape, ports and TTL as today.
- Delete `features/server_registry/`, `cli/commands/server.py`, the `dadaia server` group, the
  panel self-registration and `certify`'s `panel_check`. The `server-registry` catalog atom
  points at the skill. The behavior map maps the skill; the hash tuple covers `scripts/`.

### FR4 — Doctor without scores

- Delete `compliance(<section>)`, `compliance(total)`, per-section canonical counts and
  `total_compliance` from `cli/commands/doctor.py`, `core/doctor_rules.py`, `core/models/
  doctor_report.py` and the `--json` shape; output is findings + exit code.
- One new error rule `ADR-SUPERSEDED-CITATION`: a memory atom, rule file or skill citing an ADR
  id whose record is `superseded`. Dead path/symbol citations stay `MEM-DRIFT-2`.
- DADAIA §8.5 loses its score sentence (the section is rewritten in candidate 6; only the dead
  sentence and dead verbs leave now).

### FR5 — Security verdict as a required check

- Delete `features/chokepoints/verdict.py` (`covering_verdict`, `live_verdict_shas`,
  `ShaSource`, `GITFLOW_EDGES`), `ci verdict-check`, `.github/scripts/pr-verdict-check.sh`, the
  `verdict-gate` and `security-verdict-gate` jobs, SPEC-DOC-044, the `verdicts/` rows of the
  releases canon (`canon.py`, `release_tree.py`, `workspace_layout.py`), the pre-push verdict
  wiring (`push_gate.py`, `ci.py`), the handoff `verdict` emission in `dd-code-review` and
  `dd-release-implementation`, and every test naming them.
- Add job `security-review` to `ci.yml`: `uses: anthropics/claude-code-security-review@<pinned
  sha>` on `pull_request`, `CLAUDE_API_KEY` from repo secrets. Required checks for `develop`
  and `main` = `security-review` + the existing lint/typecheck/test/doctor jobs. The operator
  sets the secret and the branch ruleset (dependency D1).
- DADAIA §4.2 verdict sentences and the glossary `verdict` entry change to "both PRs need the
  `security-review` required check green on the PR head" (full §4 rewrite is candidate 6).

### FR6 — Roster 9 -> 3, lenses, least privilege

- Delete `public/agents/{ai-engineer,product-engineer,project-auditor,qa-engineer,
  security-reviewer,software-architect}.md`; `CORE_AGENTS` = `project-manager`,
  `software-engineer`, `code-reviewer`; the five tests pinning nine; behavior-map §2 owner rows,
  grants and `dispatch` bands of the six; `dd-manager-orchestration` shrinks to the three-role
  dispatch (router table deleted); `dd-ai-eng-knowhow`'s "only ai-engineer reads the depth
  siblings" rule and `dd-audit-project`'s dispatch of evidence agents go.
- `dd-code-review` gains six lens checklists (architecture, security, QA, product, audit, AI
  surface), each <= 15 lines, applied by code-reviewer and by software-engineer before handoff;
  the reviewer's one handoff carries the lens findings.
- `_FABLE_FORBIDDEN_AGENT = "code-reviewer"` (the model is never Fable when the security lens
  runs; Q9). `render_claude_agent` derives `disallowedTools` and `permissionMode` from
  `activity_class` (ADDITIVE -> no Edit/Write, default; MUTATING -> acceptEdits), the same
  source as the Codex `sandbox_mode` render (Q10). The `.codex/agents/*.toml` set follows.
- Owner rows in DADAIA §2.1 and `specs/AGENTS.md` name the three roles (PM: backlog, intake,
  dispatch, SPEC, memory; engineer: PLAN, TASKS, code, tests; reviewer: the verdict and the
  lenses). The `product-engineer` owner row dies.

### FR7 — `_ideas/` and the uncited verbs

- Delete `releases/_ideas/` from `canon.py`, `release_tree.py`, `workspace_layout.py`,
  `doctor_common.py`, `release_state.py`, `specs_version.py`, `behavior-map.json`,
  `shipped-hashes.json`, `public/scaffold/releases/_ideas/`, `dd-release-definition`'s
  `_ideas` step, and the 5 tests; `specs upgrade`'s unconditional repair lane removes an
  existing empty `_ideas/` (only its AGENTS.md) from a live tree.
- Delete `repos list` (`features/repos/`, `cli/commands/repos.py`, `infrastructure/
  excel_reader.py`, `public/data/repos.xlsx`, `openpyxl`), `public list`, `reports doctor`, and
  every citation of the deleted verbs in skills, law and `docs/cli.md`
  (`test_every_cited_dadaia_verb_exists` stays green).

### FR8 — Closure

- Ratchets re-measured and pinned downward (`tests/contract/test_slop_ratchets.py`,
  `test_test_suite_ratchets.py`, module-size ceiling); LOC and test counts recorded in
  `_RELEASE.json` log; `CHANGELOG.md [0.4.7]` candidate 5; memory pass (atoms retired: `panel`,
  `agent-monitoring`; corrected: `server-registry`, `agent-orchestration`, `agent-comms`,
  `agentic-entities`, `sdd-gate-v3`, `context-management`, `workspace-doctor`,
  `sdd-bug-backlog-governance`); `public stage` -> `public install --target all` ->
  `public doctor [ok] public-privacy` -> `dadaia doctor` clean on the live instance;
  `dadaia ci preflight` green; push; CI green; `dd-code-review` three-axis pass with the
  bug-surface verdict; `feature -> develop` merge; promote-or-continue gate.

## 4. Out of scope

- The law rewrite (root AGENTS.md map, scoped AGENTS.md, CONTEXT-MAP, no CLAUDE.md/DADAIA.md,
  `.kimi-code/` and mirrors, `.agents/*` symlinks): candidate 6 (ADR 0017).
- Ledger verbs to skill scripts (`bugs`, `backlog`, `release`, `audit`, ADR, `memory`),
  `bugs defer|reject|supersede`: candidate 7 (ADR 0018).
- `init <dir> [--repo] --harness`, `harness add`, three flows, `Origin` doctor rule,
  release-please, standalone skills repo, launch: candidate 8 (ADRs 0019, 0020, 0021).
- The seven generic skills stay in `public/` until `standalone-skills-distribution` publishes
  them (Q14). English-only surface and the main-repo/associated-repos rename: candidate 6.

## 5. Dependencies, risks, questions

- **D1 (operator, before FR5 closes):** `CLAUDE_API_KEY` repo secret and the branch ruleset
  naming `security-review` as required on `develop` and `main`.
- **R1:** the presence deletion touches 33 modules; the reaper must own the throttle marker
  before `presence.py` is deleted (order of work, PLAN).
- **R2:** removing verbs while skills cite them turns `test_every_cited_dadaia_verb_exists` red;
  each FR deletes the citations in the same task.
- **R3:** the live instance still carries `.kimi-code/` and the DADAIA.md mirrors until
  candidate 6; `public install` must not regenerate the deleted `server`/`panel` surfaces.
- **Q (open, operator):** ADR 0015 (`proposed`) is ratified by Q17; accept it at candidate 8's
  definition together with ADR 0021.
