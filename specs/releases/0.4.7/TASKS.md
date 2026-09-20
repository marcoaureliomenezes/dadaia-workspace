# TASKS — Release: 0.4.7

**Status:** Aprovado
**Release ID:** 0.4.7
**Owner:** software-engineer

---

## Candidate 5 — demolition

- [ ] T-047-41 — FR2a: reaper owns the throttle marker (`features/workspace/sweep.py`); presence
  keeps working through it. Write set: `features/workspace/sweep.py`, `hooks/sdd_post_gate.py`,
  `tests/unit/features/workspace/**`.
- [ ] T-047-42 — FR2b: delete `features/spec_context/presence.py`, the presence zone row,
  `PRESENCE-GC`, `PRESENCE_TTL_SECONDS`, `pre_commit.py` + `pre-commit-presence-gate.sh` + the
  `INSTALLED_GIT_HOOKS` row, `ci pre-commit-check`, `context heartbeat`, `context release`; fix
  the 33 importers (an allowed MUTATING write records nothing); `HOOKS-DRIFT-1` pre-push only.
  Write set: `hooks/**`, `cli/commands/{ci,context,doctor}.py`, `cli/redact.py`,
  `cli/_specs_resolution.py`, `features/chokepoints/**`, `features/spec_context/**`,
  `features/specs/**`, `features/backlog/document.py`, `infrastructure/**`, `core/**`,
  `public/scripts/**`, `public/skills/dd-cli-library/**`, `public/data/DADAIA.md` (§3.2, §3.3,
  §8.5 presence sentences only), `tests/**`.
- [ ] T-047-43 — FR1a: delete `features/telemetry/`, `cli/_governance_event.py` + 8 call sites,
  the HANDEDIT rules, `container.py` wiring. Write set: `container.py`, `cli/**`,
  `features/specs/{ledgers,rules,doctor,release_tree}.py`, `core/models/telemetry.py`,
  `public/data/DADAIA.md` (§8.5 HANDEDIT lines), `public/scaffold/**/AGENTS.md` (HANDEDIT
  mentions), `tests/**`.
- [ ] T-047-44 — FR1b: delete `features/panel/`, `cli/commands/panel*.py`, `dadaia panel`,
  `mistune`; rehome `load_registry` consumers onto `public/entities/registry.json`; two default
  templates with per-harness `(model, effort)` in `core/agent_model_templates.py`; `public
  doctor` validates the policy JSON. Write set: `features/panel/**`, `cli/**`, `pyproject.toml`,
  `poetry.lock`, `core/agent_model_templates.py`, `infrastructure/install_helpers.py`,
  `public/data/DADAIA.md` (§10.1 `dadaia panel`), `public/skills/dd-cli-library/**`,
  `specs/memory/product/{agents,platform}/**`, `tests/**`.
- [ ] T-047-45 — FR3: `public/skills/dd-dev-server/` (SKILL.md, `scripts/registry.py`:
  register/list/next/release/scan/clean over `.dadaia/states/server_registry.json`); delete
  `features/server_registry/`, `cli/commands/server.py`, the `server` group, panel
  self-registration, `certify` `panel_check`; behavior map + hash tuple cover `scripts/`. Write
  set: `public/skills/dd-dev-server/**`, `public/entities/behavior-map.json`,
  `public/templates/shipped-hashes.json`, `features/server_registry/**`, `features/
  certification/**`, `cli/**`, `core/workspace_layout.py` (zone owner), `public/data/DADAIA.md`
  (§8.4, §10.1 server lines), `public/skills/dd-cli-library/**`, `tests/**`.
- [ ] T-047-46 — FR5: `security-review` job (`anthropics/claude-code-security-review@<sha>`,
  `ANTHROPIC_API_KEY`); delete `features/chokepoints/verdict.py`, `ci verdict-check`,
  `.github/scripts/pr-verdict-check.sh`, jobs `verdict-gate` + `security-verdict-gate`,
  SPEC-DOC-044, the `verdicts/` canon rows, pre-push verdict wiring, the handoff verdict
  emission in `dd-code-review`/`dd-release-implementation`/`dd-gitflow-default`; DADAIA §4.2 +
  glossary `verdict` -> required check. Write set: `.github/**`, `features/chokepoints/**`,
  `features/specs/**`, `core/workspace_layout.py`, `cli/commands/ci.py`, `public/skills/
  {dd-code-review,dd-release-implementation,dd-gitflow-default}/**`, `public/data/DADAIA.md`
  (§4.2, §10.2), `public/scaffold/releases/AGENTS.md`, `tests/**`.
- [ ] T-047-47 — FR6: delete the six persona files; `CORE_AGENTS` = 3; behavior-map owner rows,
  grants, dispatch bands; `dd-manager-orchestration` three-role dispatch; six lens checklists in
  `dd-code-review`; `_FABLE_FORBIDDEN_AGENT = code-reviewer`; least-privilege render from
  `activity_class` (Claude + Codex); owner rows in DADAIA §2 and `specs/AGENTS.md`; `dd-ai-eng-
  knowhow` and `dd-audit-project` lose their persona-dispatch lines. Write set:
  `public/agents/**`, `public/entities/**`, `public/skills/**`, `public/data/DADAIA.md` (§2),
  `public/scaffold/AGENTS.md`, `core/agent_model_templates.py`, `infrastructure/
  install_helpers.py`, `infrastructure/codex_*.py`, `public/runtime/codex/**`, `tests/**`.
- [ ] T-047-48 — FR4: scores out of `cli/commands/doctor.py`, `core/doctor_rules.py`,
  `core/models/doctor_report.py`, `--json`; `ADR-SUPERSEDED-CITATION` error rule; DADAIA §8.5
  score sentence deleted. Write set: `cli/commands/doctor.py`, `core/doctor_rules.py`,
  `core/models/doctor_report.py`, `features/specs/doctor_memory.py`, `public/data/DADAIA.md`
  (§8.5), `docs/**`, `tests/**`.
- [ ] T-047-49 — FR7: `_ideas/` out of canon, release tree, workspace layout, doctor_common,
  release_state, specs_version, behavior map, shipped hashes, scaffold, `dd-release-definition`,
  5 tests; `specs upgrade` repair lane removes an empty live `_ideas/`; delete `repos list` (+
  `features/repos/`, `excel_reader.py`, `repos.xlsx`, `openpyxl`), `public list`, `reports
  doctor`; citations purged; `docs/cli.md` regenerated. Write set: `features/specs/**`,
  `features/repos/**`, `core/**`, `cli/**`, `infrastructure/excel_reader.py`, `public/**`,
  `pyproject.toml`, `poetry.lock`, `docs/cli.md`, `tests/**`.
- [ ] T-047-50 — FR8 closure: ratchets re-pinned; LOC/test counts in `_RELEASE.json` log;
  `CHANGELOG.md`; memory pass (atoms retired/corrected per SPEC FR8); stage -> install ->
  public doctor -> doctor on the live instance; preflight; push; CI green; `dd-code-review`
  three-axis pass; `feature -> develop` merge; gate. Write set: `tests/contract/**`,
  `CHANGELOG.md`, `specs/memory/**`, `specs/releases/0.4.7/_RELEASE.json`.
