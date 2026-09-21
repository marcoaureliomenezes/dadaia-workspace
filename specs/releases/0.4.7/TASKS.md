# TASKS — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-software-engineer

---

## Candidate 8 — bootstrap, lazy harness, three flows

- [x] T-047-71 — FR2: the harness record. `core/harness_registry.py` gains a frozen
  `HarnessRecord(name, directory, agent_transcode, hooks)` and a `HARNESS_RECORDS` table for
  `claude` (`.claude`, `claude-md-symlink`, `claude-settings`), `codex` (`.codex`, `codex-toml`,
  `codex-hooks`) and `kimi-code` (none, `none`, `kimi-hooks` — the user-level shims stay a hook derivation). `L1_ENTRY_HARNESSES`,
  `HARNESS_PROJECTION_DIRS`, `PROJECTION_TARGETS`, `INSTALL_TARGETS` and `parse_harness_set`
  derive from the table — no second literal. `infrastructure/projection_rules.py` drops the
  three `HarnessProjection` classes and `build_harnesses()`; `projection_rules()` iterates
  records and dispatches on `agent_transcode`/`hooks`, deleting the
  `if {"agents","codex","claude"} & set(...)` branch. Byte-identical output.
  Seam: the record's two enum fields replace a class per harness.
  RED: `tests/contract/test_harness_registry_records.py` — the rendered rule table for the
  three harnesses equals a golden captured before the refactor, and `projection_rules.py` source
  contains no harness-name string outside `harness_registry`.
  Write set: `dadaia_workspace/core/harness_registry.py`,
  `dadaia_workspace/infrastructure/projection_rules.py`,
  `dadaia_workspace/infrastructure/public_assets_common.py`,
  `tests/contract/test_harness_registry_records.py`, `tests/unit/infrastructure/**`.

- [x] T-047-72 — FR2: `harness add` in, `public install --target` out. New `cli/commands/
  harness.py` with `add <name>` (stage if needed, install that record's set, append the name to
  `.dadaia/states/harness_profile.json` through `JsonHarnessProfileStore.write` — the one writer)
  and `list` (the profile's roster). `cli/commands/public.py` loses `--target` entirely;
  `public install` projects the shared authored set plus every harness already in the profile;
  `public doctor` scopes to the same roster. `main.py` registers the new group.
  Seam: the profile file is the roster of record; `install` reads it instead of a flag.
  RED: `tests/integration/test_harness_add.py` — on a Claude-only workspace, `harness add codex`
  yields the `.codex/` set, `harness list` shows both, `public doctor` exits 0; and `--target` is
  absent from `public install --help` (AC2.1).
  Write set: `dadaia_workspace/cli/commands/harness.py`,
  `dadaia_workspace/cli/commands/public.py`, `dadaia_workspace/cli/main.py`,
  `dadaia_workspace/infrastructure/public_assets.py`,
  `tests/integration/test_harness_add.py`, `tests/contract/test_cli_help_quality.py`.

- [x] T-047-73 — FR1: `init <dir> --harness <name>`. `cli/commands/init.py` takes a required
  positional `<dir>` (validated as a directory name; created if absent; refused with one `fix:`
  line if it holds a foreign tree) replacing the `--workspace/-w` resolution, and a required
  `--harness <name>` accepting exactly one registered record — `all` and the comma-subset form
  die with `parse_harness_set`'s meta-value. The ancestor-walk warning goes with the resolver
  call it guarded. Idempotent on re-run: a second `init` on the same dir changes nothing.
  Seam: argv — the directory is a parameter, never resolved from cwd.
  RED: `tests/unit/cli/test_init_requires_dir_and_harness.py` — `init demo` without `--harness`
  exits 2 with one `fix:` line; `init demo --harness all` exits 2; `init demo --harness claude`
  twice leaves an identical tree (AC2.1 first clause).
  Write set: `dadaia_workspace/cli/commands/init.py`,
  `dadaia_workspace/core/harness_registry.py` (`parse_harness_set` -> single-name parse),
  `dadaia_workspace/features/workspace/**`, `tests/unit/cli/test_init_requires_dir_and_harness.py`.

- [ ] T-047-74 — FR1: `--repo <url>` and the closing notes. With `--repo`, `init` clones into
  `repos/<slug>/`, then calls the existing `context create --main-repo <slug>`, `context alive`
  and `context bind` implementations in `features/spec_context/` (composition, never a second
  implementation), prints the `--print-env` line, and installs the pre-push hook via the
  existing `ci install-hook` path. Without `--repo`, the closing notes keep candidate 6's two
  lines and gain one: where projects live and the single `dadaia context create` command that
  makes the first one. No other context verb is named.
  Seam: `init` is a caller of the context lifecycle; the lifecycle keeps its own interface.
  RED: `tests/integration/test_init_with_repo.py` — `init demo --harness claude --repo
  <tmp bare repo path>` leaves `repos/<slug>/` cloned, the context ALIVE and bound, the pre-push
  hook installed, and `dadaia doctor` exit 0; the no-`--repo` run prints exactly three closing
  lines.
  Write set: `dadaia_workspace/cli/commands/init.py`,
  `dadaia_workspace/features/workspace/**`, `tests/integration/test_init_with_repo.py`.

- [ ] T-047-75 — FR3: cursor, devin, copilot records and agent transcodes. Three rows added to
  `HARNESS_RECORDS`: `cursor` (`.cursor`, `cursor-md`, `cursor-hooks`), `devin` (`.devin`,
  `devin-md`, `devin-hooks`), `copilot` (`.github`, `copilot-agent-md`, `copilot-hooks`). The
  `cursor-md` and `devin-md` builders project `.cursor/agents/<name>.md` and (Devin reads
  `.agents/agents` natively) no duplicate persona copy; `copilot-agent-md` renders
  `.github/agents/<name>.agent.md` from the same `_agents_agent_rules` authored set. All reuse
  `_link_rule`'s hash-verified copy fallback — no new rule kind. `public/entities/registry.json`
  gains a `cursor`/`devin`/`copilot` implementation string for every Behavior and Rule.
  `public/data/CONTEXT-MAP.md` §1 rows already describe these harnesses and are re-verified.
  Seam: the record table — three data rows, zero new adapter classes.
  RED: `tests/contract/test_agentic_entities_derivation.py` extended — every Behavior/Rule has an
  implementation for all six registered harnesses; plus a projection-golden test per new harness
  asserting the directory, the agent files and no unexpected extras (AC3.1).
  Write set: `dadaia_workspace/core/harness_registry.py`,
  `dadaia_workspace/infrastructure/projection_rules.py`,
  `dadaia_workspace/public/entities/registry.json`,
  `dadaia_workspace/public/data/CONTEXT-MAP.md`,
  `tests/contract/test_agentic_entities_derivation.py`, `tests/contract/test_context_map.py`,
  `tests/unit/infrastructure/**`.

- [ ] T-047-76 — FR3: the four behaviours in three hook formats, plus live probes. Each new
  record's `hooks` value derives the SAME four deterministic behaviours — root whitelist, venv
  guard, SDD gate (one `pre_gate` entrypoint) and the session-start reaper — into that harness's
  file: `cursor` -> `.cursor/hooks.json`; `devin` -> `.devin/hooks.v1.json`; `copilot` ->
  `.github/hooks/pre-tool-use.json` + `.github/hooks/session-start.json`. The wrapper-script
  rule (`_codex_hook_wrapper_rules`) generalises to any record whose hooks need an on-disk
  executable. `features/certification/service.py` gains `<harness>-live-probe` per record,
  UNVERIFIED when the binary is absent, no version floor.
  Seam: the `hooks` enum value; no harness invents a fifth behaviour.
  RED: `tests/contract/test_hook_behaviour_coverage.py` — for every record with hooks, the
  projected files reference exactly the four behaviours' entrypoints, and no file exists for a
  behaviour the workspace does not define; `tests/unit/features/certification/` asserts the probe
  is UNVERIFIED with the binary absent.
  Write set: `dadaia_workspace/infrastructure/projection_rules.py`,
  `dadaia_workspace/infrastructure/runtime_config.py`,
  `dadaia_workspace/infrastructure/runtime_transforms/**`,
  `dadaia_workspace/features/certification/**`,
  `tests/contract/test_hook_behaviour_coverage.py`, `tests/unit/features/certification/**`.

- [ ] T-047-77 — FR4: `SPEC-DOC-048`, `--origin`, flow weights. `features/specs/rules.py` +
  `doctor_release.py` gain `SPEC-DOC-048`: every live and rc-N SPEC carries
  `**Origin:** operator-demand | backlog:<slug>[,..] | bugs:<id>[,..]`, parsed like
  `_extract_status`; `backlog:` slugs must resolve in `BACKLOG.json` or `backlog_histo.jsonl`,
  `bugs:` ids must be open `BUGS.jsonl` records; the finding carries one `fix:` naming the line.
  `public/skills/dd-release-implementation/scripts/_release_new.py` gains `--origin`, written
  into `SPEC_STUB`; with `bugs:<ids>` the stub seeds one FR per bug (title + repro line).
  `public/scaffold/releases/AGENTS.md` states the three flow weights (Flow 1 default, Flow 2
  surgical memory, Flow 3 heaviest) once; `dd-release-definition/SKILL.md` step 1 names the
  origin — one line, not a section (V35).
  Seam: the SPEC header is the flow's only machine-read input.
  RED: `tests/unit/features/specs/test_spec_doc_048_origin.py` — a SPEC without `Origin` is an
  error with the `fix:` line, an unknown `backlog:` slug and a closed `bugs:` id each error, and
  this repo's live + rc-N SPECs pass (AC4.1).
  Write set: `dadaia_workspace/features/specs/rules.py`,
  `dadaia_workspace/features/specs/doctor_release.py`,
  `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_new.py`,
  `dadaia_workspace/public/scaffold/releases/AGENTS.md`,
  `dadaia_workspace/public/skills/dd-release-definition/SKILL.md`,
  `tests/unit/features/specs/test_spec_doc_048_origin.py`, `tests/contract/test_slop_ratchets.py`.

- [ ] T-047-78 — FR5: CLI audit, docs, dead-branch deletions. Every verb in `dadaia help tree`
  is cited by a skill, agent or the root map, or dies; the surviving groups are `init`,
  `harness`, `context`, `public`, `ci`, `doctor`, `reports`, `certify`, `export`, `import`,
  `reconcile`, `migrate`, `capabilities`, `help`, `specs`; total verb count <= 30.
  `features/spec_context/doctor.py` loses `_orphan_claude_bridge`, its
  `_RETIRED_CLAUDE_BRIDGE_STUB` constant and its test (AC5.1). Candidate 7 review F5 folds in
  here: `public/skills/dd-cli-library/scripts/registry.py` splits by responsibility (registry
  I/O vs the verb surface) under the V36 script ceilings. `docs/cli.md` re-rendered against the
  live tree; `tests/contract/test_cli_help_quality.py` verb pin lowered, never raised.
  Seam: `help tree` is the audited interface; a verb with no citation is slop.
  RED: `tests/contract/test_cli_help_quality.py` — the verb count is <= 30, every verb appears in
  at least one `public/` skill/agent/map file, and `docs/cli.md` matches `help tree`.
  Write set: `dadaia_workspace/cli/**`, `dadaia_workspace/features/spec_context/doctor.py`,
  `dadaia_workspace/public/skills/dd-cli-library/scripts/registry.py`, `docs/cli.md`,
  `tests/contract/test_cli_help_quality.py`, `tests/contract/test_slop_ratchets.py`,
  `tests/unit/features/spec_context/**`.

- [ ] T-047-79 — FR5: the bootstrap e2e and closure. `tests/e2e/test_one_line_bootstrap.py`
  (LARGE, justified inline): a `tmp_path` workspace, a **local bare git repo** as `--repo` (no
  network, no container), the package installed from source into a tmp venv, then `dadaia init
  demo --harness claude --repo <bare>`, `cd demo && dadaia doctor` exit 0 and `dadaia context
  show --json` reporting the repo as `main_repo` ALIVE (AC1.1). Then: CHANGELOG "Candidate 8",
  `_RELEASE.json` `log` entry and `release phase` milestones, the live instance re-projected
  (`public stage` -> `public install` -> `public doctor` exit 0, `dadaia doctor` exit 0),
  `.github/workflows/ci.yml` jobs touching init/install updated to the new flags, dd-code-review
  dispatched, PR #260 updated and watched to green (AC5.1). The memory pass is the PM's.
  Seam: the e2e is the only test that exercises the installed console script.
  RED: `tests/e2e/test_one_line_bootstrap.py` fails on the current `init` signature before
  T-047-73/74 land, and passes end to end after.
  Write set: `tests/e2e/test_one_line_bootstrap.py`, `CHANGELOG.md`,
  `specs/releases/0.4.7/_RELEASE.json`, `.github/workflows/ci.yml`.
