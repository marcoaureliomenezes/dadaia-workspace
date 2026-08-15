# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.1] — 2026-08-15

Hotfix (Arm B, `hotfix/0.7.1`). No release ceremony.

### Fixed
- **`pyproject.toml`'s `[tool.mypy]` comment no longer claims `incremental = false`
  alone keeps `.mypy_cache/` out of the repo tree** (bug
  `mypy-strict-cache-dir-created-without-cache-dir-env-override`, LOW). False under
  mypy 2.1.0: the cache dir (`CACHEDIR.TAG` + a version subdir) is written at its
  resolved `cache_dir` regardless of `incremental`, so a bare local
  `mypy --strict dadaia_workspace/` polluted the checkout. No portable, crash-proof
  `cache_dir` value exists (`$MYPY_CONFIG_FILE_DIR/..` assumes this checkout's depth
  under a dadaia workspace root, and an unwritable resolved target crashes mypy with
  an INTERNAL ERROR — verified). The comment and `.github/PULL_REQUEST_TEMPLATE.md`'s
  mypy checklist line now require the `MYPY_CACHE_DIR` redirect mypy itself supports —
  the same one `ci.yml` already uses, and what `dadaia ci preflight` already does
  automatically. New integration/slow test
  `tests/integration/test_mypy_local_invocation_hygiene.py` runs the PR template's
  literal documented command against an isolated copy of the real `[tool.mypy]`
  config and asserts no pollution.
- **Context/session-resolution unit tests no longer depend on an ambient
  `WORKSPACE_ROOT`** (bug `specs-resolver-context-tests-flaky-under-xdist-full-suite`,
  LOW). `core.specs_resolver._authority_workspace_root()` honours `WORKSPACE_ROOT`
  unconditionally (by design, the hook-transport channel) — ahead of, and regardless
  of, any `monkeypatch.chdir()` a test performs. Every context-resolution test file's
  isolation fixture scrubbed only the harness session-id and `DADAIA_CONTEXT`/
  `DADAIA_SESSION_ID` vars, never `WORKSPACE_ROOT` (`tests/unit/test_container.py`'s
  three `resolve_context` seam tests scrubbed nothing at all), so an ambient
  `WORKSPACE_ROOT` — inherited from the shell that launched pytest, or left behind by
  a concurrent `dadaia context bind`/`context show` sharing the real
  `.dadaia/sessions/` tree during a full-suite `-n auto` run — silently overrode every
  synthetic `tmp_path` workspace under test. Same flake class already fixed for
  `panel-e2e-readiness-flaky-under-xdist-load` /
  `panel-command-readiness-flaky-under-xdist-load`, this time isolation hardening at
  the fixture level rather than a timing bound. Centralized the isolation set
  (`CONTEXT_RESOLUTION_ENV_VARS` / `scrub_context_resolution_env`) in
  `tests/fixtures/harness_env.py` and wired it into `test_specs_resolver_resolve_context.py`,
  `test_specs_resolution.py`, `test_container.py`, `test_context_show_reflects_bind.py`,
  and `test_codex_thread_id_bind.py`.

## [0.7.0] — 2026-08-15

Release v0.10.0 (`dd-lifecycle-skills-family`).

### Added
- **The `dd-` lifecycle skill family** — seven skills, one per SDD stage, zero
  overlap, measurable style budgets: `dd-backlog-definition` (backlog curation,
  the BACKLOG.md ACTIVE/LEDGER schema, the disposition-token vocabulary, and the
  operator-gated intake protocol), `dd-release-definition`, `dd-release-implement`
  (owns the gate-cadence table), `dd-release-closure`, `dd-audit-project` (full
  merge of drift-detection), `dd-bug-registration`, `dd-bug-fix` (Arm B
  end-to-end). Three former skills renamed/merged in place; four net-new.
- **Contract test for the Codex D-CX-7 skill-reference gate** proving the `dd-`
  prefix family is validated (the rename would otherwise have degraded the check
  to a silent no-op).

### Changed
- **Always-on law dehydrated**: stage protocol moved out of `DADAIA.md` into the
  stage skills (backlog schema, hotfix flow, bug registration, watch-CI
  checkpoint); the law keeps only always-on content and points at the family.
- **Operator-gated backlog intake** (operator ADR, 2026-08-15): only the operator
  creates demand; agents route residuals to a PM intake report for operator
  adjudication; all personas and orchestration surfaces updated.
- **`ai-engineer`'s declared write surface corrected** to the real law-source
  paths (`public/data/*.md`, scaffold/template AGENTS files) — the previous
  allowlist named a non-existent directory.

## [0.6.0] — 2026-08-14

Release v0.9.0 (`push-range-denylist-scan`).

### Added
- **Push-range denylist scan at the pre-push gate**: every non-deletion ref (tags
  included) has its newly published objects scanned against three additive term
  layers — operator denylist (when present), packaged structural baseline
  (now v4, with carve-outs for RFC-2606 reserved-TLD emails, the product's own
  synthetic `workspace.local` identity, and stdlib `Path.home` call forms), and
  foreign `repos/` slugs (word-boundary, case-insensitive, self-slug excluded).
  Object reads run through a single batched `git cat-file` conversation with a
  per-blob size cap. Fail-closed on git failure; binary/oversized blobs skipped
  and counted; masked, satisfiable refusal that never echoes the matched term or
  line; `git push --no-verify` remains the single traceable bypass.
- **`--redact` output mode** on `dadaia doctor`, `dadaia context list` and
  `dadaia context show` (table and `--json`): foreign context names and repo
  slugs become stable ordinal placeholders; default output byte-for-byte
  unchanged.
- **Redaction-at-authoring doctrine** in the QA agent surface: diagnostic output
  transcribed into authored documents is captured with `--redact` or masked.

### Changed
- Packaging author email switched to the GitHub noreply form (operator decision
  during the release's own pre-PR review, whose scan refused the prior form).

## [0.5.2] — 2026-08-14

Hotfix (Arm B, `hotfix/v0.5.2`). No release ceremony.

### Fixed
- **`dadaia context alive` no longer sweeps pre-existing unrelated dirty tracked files
  into its scaffold commit** (bug `context-alive-sweeps-unrelated-worktree-changes`,
  MEDIUM). The `chore(scaffold): dadaia context alive specs baseline` commit called
  `GitClient.commit_all`, whose staging (`git add -u` + untracked sweep) is a blanket
  operation over the whole working tree — any pre-existing operator WIP on tracked files
  (e.g. a dirty `docker-compose.yml`/`supervisord.conf`) got silently folded into the
  tool-authored commit with no consent, and `git status` came back clean afterwards.
  `alive()` now tracks exactly which repo-relative paths the scaffold step itself
  created/modified (`specs/**` newly written, the individual files a merge into a
  pre-existing `specs/` actually added, `AGENTS.md`, `tests/AGENTS.md`) and stages only
  those via a new explicit-path `GitClient.commit_paths` — never `-A`/`-u` over a shared
  tree. Pre-existing unrelated worktree modifications now stay dirty and uncommitted.
  Closes the `architecture-resilience` audit finding F-10 lineage (superseded by this
  bug).

## [0.5.1] — 2026-08-14

Hotfix (Arm B, `hotfix/v0.5.1`). No release ceremony.

### Fixed
- **`ensure_workspace_venv` no longer inherits a degraded base-interpreter resolution
  for a freshly created workspace venv** (bug
  `init-venv-bootstrap-inherits-degraded-base-python`, HIGH). stdlib `venv.create()`
  resolved a NEW venv's base interpreter through `sys._base_executable` of the calling
  process; on a `--copies` venv (this workspace's own `.dadaia/.venv`), CPython's
  getpath.c re-derives that value via a landmark search for the OS-level *unversioned*
  `python3` name inside the recorded `home` directory — not the version-pinned
  `executable` its own `pyvenv.cfg` records. On a host where `/usr/bin/python3`
  symlinks to an older interpreter than the one actually running, every child venv
  silently degraded and `dadaia init` failed opaquely with "requires a different
  Python". `ensure_workspace_venv` now resolves an interpreter explicitly (its own
  `_base_executable` if it satisfies Requires-Python, else the running venv's own
  `pyvenv.cfg` `executable`, else a version-pinned `pythonX.Y` on PATH), verifies it by
  executing it, and creates the child venv via subprocess instead of the implicit
  `venv.create()`. A new pre-install post-condition also rejects an
  interpreter-mismatched venv (fresh or pre-existing/doctor-repaired) with an
  actionable message naming both versions, before ever reaching pip's bare error.

## [Unreleased] — spec release v0.7.0

Test stewardship. Lands in the same unreleased `0.5.0` package version as the spec releases
below — one dev-only dependency, no production dependency, no Python version and no
packaging contract change.

### Added
- **`dadaia-test-stewardship`, the single operational home of the test lifecycle.** A new
  universal skill carrying the intent taxonomy (CONTRACT / SENTINEL / SCAFFOLD /
  QUARANTINE, declared in the module docstring — never as a pytest marker, since the marker
  namespace already binds `contract` to a layer), the admission filter, the size tiers with
  their timeout table and the LARGE owner rule, demotion-at-closure, the deletion criteria
  with the tombstone ban and the separation of powers, the flake/quarantine pipeline,
  artifact hygiene, the health metrics with a trigger-based audit, and a parameter table
  carried as **declared adjustable defaults** so a consumer re-parameterizes without forking
  the doctrine. Projected to the canonical `.agents/skills/` home plus `.claude/skills/`;
  read natively by Codex and Kimi Code, so no per-harness derivation and no registry entry.
- **`## 8. Disciplina de Testes` in the scaffold constitution** and the new public template
  `templates/tests-AGENTS.md`, so the doctrine reaches a scaffolded workspace at law level
  and as a scoped rule file. The template is parameterized (`<ANGLE-BRACKET>` placeholders
  for the tier timeouts, the LARGE cap and the wall-clock baseline) and carries zero
  workspace-specific literals. No existing constitution section was renumbered.
- **Consumer repos receive `tests/AGENTS.md` at `alive()`** — copied only when `<repo>/tests/`
  is a real directory (a symlinked `tests/` is refused) and no `tests/AGENTS.md` exists. The
  copy never creates the directory and never overwrites an operator file.
- **Per-test timeouts by tier** via the new dev dependency `pytest-timeout`: unit 10 s,
  contract 30 s, integration 60 s, e2e 120 s, applied at collection and never overriding an
  explicit `@pytest.mark.timeout`. A test that needs more time is mis-tiered — the tier is
  what gets fixed.
- **Two markers, `flaky` and `quarantine`**, moved across all six marker surfaces in one
  change. A `quarantine` mark without `bug="<bug-slug>"` **refuses collection**, with the
  actionable message printed to stderr before the raise so it survives an xdist worker
  crash; a contract test pins `pyproject.toml`'s marker set against `conftest.py`'s so the
  surfaces cannot drift apart silently.
- **The panel E2E retry became loud.** A Playwright JSON reporter writes outside the repo
  tree and a CI step fails the job on any `passed`-after-retry result unless the test is
  registered as quarantined, naming the offending spec. The step is fail-closed: a missing,
  empty, malformed or non-numeric report exits 1. Demonstrated once on the branch with a
  deliberately flaky throwaway spec, removed in the same task.

### Changed
- **`DADAIA.md` §6 states the test lifecycle once**: intent and size declared at birth (an
  undeclared test is SCAFFOLD and expires); demotion is a step of release closure; the
  implementer never prunes to go green — pruning is a `qa-engineer` verdict with `file:line`
  evidence, executed by `software-engineer`; tombstone tests and expired SCAFFOLD are slop;
  test-artifact capture is failure-gated. Plus two sentences elsewhere: the never-delete law
  is **scoped to bugs and backlog only** (tests are prunable under the criteria), and a
  quarantine carve-out inside *Push green* — a green run with quarantined tests is green, an
  **unregistered pass-on-retry is a failure**. The law names no number and no marker; those
  live in the skill and in the repo. Always-on cost +221 tokens against a +400 cap.
- **One coverage stance, four sites.** The 80 % floor on `unit or contract` is a CI gate and
  a by-product metric — never an acceptance target, never a reason to write a test, never a
  score anchor. `drift-detection`'s Dimension E is rewritten off line-coverage anchors onto
  detection quality (intent declared, demotion performed, flake within ceiling, quarantine
  within cap and unexpired, LARGE owned). The gate itself is byte-unchanged.
- **Every gating selector excludes the quarantine lane** — six in `ci.yml`, four in
  `release.yml`, and the pre-push preflight's base arguments — so a quarantined test runs
  only under an explicit `-m quarantine` diagnosis invocation. `--durations=25` on the unit
  and unit+contract coverage jobs, and every pytest job carries a `timeout-minutes` ceiling
  ratcheted against the frozen baselines, so a budget change is a reviewable diff.
- **`qa-engineer` is verdict-only on curation** and its `write_allowlist` narrows from
  `tests/**` to `tests/e2e/**` plus the `alpha-N` review file, reports and handoffs, ending
  a standing contradiction between its frontmatter and its body. `software-engineer`
  **executes** curation verdicts, quoting the evidence in the commit message.
  `dadaia-release-closure` gained the demotion + disposition block, so demotion-at-closure
  finally has somewhere to land; `tests/README.md` collapsed to `## Commands` plus one
  pointer, ending its duplication of `tests/AGENTS.md`.

### Removed
- The dead `--ignore=tests/performance` in the CI preflight and the unit assertion pinning
  it — the directory no longer exists.

### Fixed
- Memory told the truth again: the stale "~2,100 collected tests" is now the measured
  2,123 collected / 55 LARGE, and `pytest-xdist` / `pytest-randomly` are documented in the
  tech stack, having been in use through `-n auto` without ever being listed.

## [Unreleased] — spec release v0.6.0

Gitflow standardization. Lands in the same unreleased `0.5.0` package version as the spec
releases below — this release changes no dependency, no Python version and no packaging
contract.

### Added
- **`dadaia-gitflow`, the single operational home of the git contract.** A new universal
  skill (89 lines) carrying the four-branch table, a seven-row stage table mapping every
  lifecycle stage to its branch, commit cadence, merge target and push trigger, the two
  merge milestones with their mandatory post-merge sequence, the hotfix PATCH-mint rule, and
  an explicit split between what is mechanically enforced and what is discipline. Projected
  to the canonical `.agents/skills/` home plus `.claude/skills/`; read natively by Codex and
  Kimi Code, so no per-harness derivation and no registry entry.
- **`pr-source-guard`**, a required check on `main`: any pull request targeting `main` whose
  head is not exactly `develop` fails and is mechanically unmergeable. The fork-controlled
  head ref is bound through `env:` and compared as a quoted literal, never interpolated into
  a shell string.

### Changed
- **`DADAIA.md` §5/§6 state one git contract.** Four branch patterns and no fifth — `main`,
  `develop`, `feature/{M.m.p}`, `hotfix/{M.m.p}` with PATCH ≥ 1; `develop` is the only
  pushable branch, feature and hotfix branches are local-only, and `main` advances only via
  a PR from `develop`. Stage placement, the two-milestone merge cadence
  (definition-trio `Aprovado` and ship, each followed by a diff-based security review of
  `origin/develop..develop` and a push of `develop`) and the finalization order
  memory → CLOSURE → archive are stated once at law level; every other skill and agent
  references the skill instead of restating it. Always-on cost +389 tokens against a +400
  cap.
- **BREAKING — the pre-push chokepoint enforces branch policy.** Any pushed ref other than
  `refs/heads/develop` is refused, branch names are validated against the four patterns, a
  refspec aiming local `develop` at another remote ref is refused, a local ref that is not a
  branch head gets its own diagnosis, and an unparseable stdin line now fails **closed**
  (the one traceable bypass, `git push --no-verify`, is named in the message). Tag pushes and
  branch deletions keep their carve-out, so publishing is unaffected. *Consumer workspaces
  with no `develop` branch, or with `release/*`-style branch names, will get hard push
  refusals after upgrading; bootstrap a `develop` branch first.*
- **The push-gate security verdict is keyed to the develop delta** — an APPROVED
  `security-reviewer` handoff covering `origin/develop..develop` — instead of a bare per-ref
  sha match. `security-reviewer` admits exactly one push-gate scan target, the diff; a
  full-tree scan survives only in the audit lane.
- CI push triggers are `main` and `develop` only. The `feature/**` and `hotfix/v*` triggers
  and the push-triggered `hotfix-branch-name` job are retired — those branches are
  local-only, and the PATCH ≥ 1 pattern now lives in the chokepoint validator, at the
  boundary that actually exists.

### Removed
- **The hotfix *release* ceremony is revoked.** A bug fix is Arm B in full, run on
  `hotfix/{M.m.p}`; at merge into `develop` the same commit bumps `pyproject.toml` and adds
  the `CHANGELOG.md` entry. No hotfix SPEC, PLAN, TASKS or CLOSURE, and no
  `specs/releases/<id>/` directory. The record is the bug ledger's `resolved` event plus
  that CHANGELOG entry. `product-engineer` states the revocation explicitly so the ceremony
  is not restored as a perceived regression; removal of the now-dead verb and templates is
  queued in the backlog.
- The operational restatements of the branch model across four skills and seven agents —
  relocated to `dadaia-gitflow`, proven by a relocation grep run independently by the author
  and by QA.

### Fixed
- The four dangling `release-governance` citations (two skills, two package modules) now
  cite `DADAIA.md` §5 or `dadaia-gitflow`.
- The scaffold constitution gained `## 11. Checkpoints de Revisão` and
  `## 13. Propriedade da Memória`, so every `constitution §N` citation across the shipped
  agents resolves.
- `scaffold/releases/README.md` states the canon release-directory regex
  `^v\d+\.\d+\.\d+$` — the previous expression rejected `v0.6.0` itself — and its `ACTIVE.md`
  block matches the v2 schema including the optional `segment:` line.
- `ai-engineer` inventories the real `public/scripts/` contents (5 files, 3 shell) instead
  of claiming `pre-push-ci-gate.sh` is the only asset there.

## [Unreleased] — spec release v0.5.0

Lands in the same unreleased `0.5.0` package version as spec release v0.3.0 below.

### Removed
- **The four competing context-resolution ladders and the bind-epoch marker
  subsystem.** `core.specs_resolver.resolve_context()` is now the single authority
  implementing the `DADAIA.md` §3 rung law verbatim (rung 0 caller input / explicit write
  target, rung 1 `DADAIA_CONTEXT`, rung 2 this session's own live record keyed by the
  harness-native session id, rung 3 the repo containing the cwd). The CLI seam, the SDD
  gate, `container` and the ctx-inject hook all consume it. Deleted with the ladders: all
  three marker-attribution algorithms, the `session_identity` marker writers/readers,
  `sdd_post_gate._adopt_attributed_bind`, `.dadaia/states/bind_epoch/`, and
  `cli._specs_resolution.current_ancestry_pids` — 132 occurrences across 18 files → 0.
  `core/specs_resolver.py` went 369 → 202 lines; the production package is net −194 lines
  across the release.
- The `DADAIA_SESSION_ID` **resolution** channel (it survives only as a session identity
  for the CLI/hook heartbeat), the dead `DADAIA_AGENT_RUNTIME` alias (zero writers), the
  hardcoded self-hosting-slug rung, the env pop/restore workaround, and the `cwd/specs`
  fallback in `resolve_specs_dir`. Resolution now reads one environment variable:
  `DADAIA_CONTEXT`.

### Changed
- **Context-memory injection triggers on the session record's `bound_at`** instead of a
  marker mtime. One intended behavior difference: a **same-context re-bind now
  re-injects**, so a mode or release change reaches a live session.
- **Kimi Code binds through `DADAIA_CONTEXT` exported at harness launch** (rung 1) — the
  harness exposes no session-id environment variable. `dadaia context bind` now prints a
  loud warning when it can neither key a harness-native record nor see `DADAIA_CONTEXT`,
  so a binding can never become a silent no-op.
- `DADAIA.md` §3 amended for precision and re-projected; the skills and
  `CONSUMER_VALIDATION_RECIPE.md` teach the three rungs, the plain-shell path and the kimi
  launch-env profile.
- The import-linter contract `bind-resolution-seam-is-a-single-home` rewritten for the new
  seam: exactly three sanctioned direct importers (`cli._specs_resolution`, `container`,
  `hooks`), still zero `ignore_imports`. Hooks import the authority directly by law — no
  hook imports `container`, pinned by a new attesting import-surface test (hook write-path
  latency 2.25 s → 0.46 s).

### Fixed
- **`dadaia specs doctor` is satisfiable again.** A bug-ledger coherence violation is now
  reported only while no later compensating `reported` event exists for the same `bug_id` —
  the append-only store's own vocabulary heals its history, while per-event enforcement is
  unchanged and a fresh uncompensated violation still ERRORs. Two legal appends healed the
  one historical row; the doctor exits 0 on the self-hosting context for the first time.
- Install-ledger relpaths are validated in `LedgerEntry.__post_init__` — empty, absolute,
  `..`-bearing, backslashed and non-normalized POSIX forms are rejected at the one
  construction authority, covering both the prune loop and the foreign-projection scan
  (CWE-22 class).
- `DoctorLine.render()` escapes control characters, so no producer can forge a second
  physical doctor line (CWE-117).
- The `entities-derivation` verifier emits a typed `ENT-DERIVE-1` error line for
  malformed-but-valid JSON shapes instead of letting `AttributeError`/`TypeError` escape.
- The kimi telemetry reader contains `sessionDir` lexically against the index parent before
  `stat`, degrading through its existing `OSError` branch; ships with the reader's first
  test file.
- A new `remove_legacy_bind_epoch_state` install migration sweeps orphan
  `.dadaia/states/bind_epoch/` markers left by earlier releases (retained one release).

## [0.5.0] — Unreleased (spec release v0.3.0)

### Removed
- **Removed the dadaia-workflows engine entirely.** The four `dadaia lifecycle`
  Python workflows (backlog-definition, release-definition, implementation-reviews,
  audit), the Layer-2 worker runtimes (codex/pi/claude-sdk/fake adapters,
  headless adapter base), workflow model policy + profiles, lifecycle fragments and
  personas assets, the lifecycle run store, workflow handoff models/doctors, the
  panel Workflows and Model-policy tabs, the `dadaia reports workflow-*` verbs, the
  certification `workflow-*` checks, `features/ai_surface`, and every related test
  (~52k LOC total). The SDD flow (Arm A) is now agent-dispatched and
  document-governed — SPEC/PLAN/TASKS + ACTIVE.md + the deterministic gate and git
  chokepoints are unchanged. Rationale: the bug-ledger audit measured 200/416 bugs
  (48%) in this subsystem with a 96% additive-fix ratio and 0.48-day median
  family recurrence; deleted surface goes quiet, patched surface does not.
- `dadaia-capabilities-v1` schema replaced by **`dadaia-capabilities-v2`** (breaking):
  the required `workflows` key and the certification `deterministic_fake_workflows` /
  `live_harness_canaries_required_for_release` constants are gone.

### Changed
- **`public_assets` install de-flagged**: `install()` now resolves its arguments once
  into an immutable `InstallPlan` and runs an ordered, flag-free step pipeline
  (`OverwritePolicy` replaces `force: bool` internally; `scope`/`only` select steps).
  Public port signatures and install output are byte-identical.

## [0.1.24] — Unreleased

### Removed
- **Removed OpenCode support entirely (both agentic layers).** The OpenCode entry
  harness, the `OPENCODE_RUN` Layer-2 worker kind and its adapter, the `.opencode/`
  projection target, `opencode.json`, the OpenCode gate plugin, and all OpenCode
  references across code, tests, docs, and the AI surface are gone. The supported
  harness set is now exactly **Claude Code, Codex, and PI**.

## [0.1.7] — 2026-06-13

Consolidated release: the single published version after `0.1.5`. It folds in all
work from the never-tagged `0.1.6`–`0.1.10` development line — cross-platform
support, the process-execution layering law, spec/memory fidelity, the full
workspace-audit remediation, and panel/scaffolder/git security hardening — shipped
under one version through the release-candidate gate rather than as a string of
per-fix releases.

### Added
- **Cross-platform support (Linux / macOS / Windows).** `core/platform.py`
  platform-detection seam (sole `sys.platform` call site) + a port/adapter boundary
  for OS-sensitive domains: file locks (fcntl / msvcrt), telemetry refresh lock, file
  permissions (chmod / `icacls`), process probe, and signals/shutdown. New
  `dadaia_workspace/hooks/` Python governance package replaces the bash hooks so SDD
  governance is enforced on stock Windows (no Git Bash required). 3-tier resilience
  contract (fail-loud security / degrade-with-log / unsupported-at-construction).
  `import-linter` contracts enforce the layering law in CI.
- Phased 3-OS CI matrix: an importability-smoke job (Windows + macOS) plus
  Windows/macOS unit and contract legs (Ubuntu remains the hard gate).

### Changed
- **Model strategy unified on the registry single source** (`core/model_registry`):
  `MODEL_MAP` / `PRICING_TABLE` are derived views; public doctor validates agent
  `model:` frontmatter + key-set sync. Deep-tier personas (product-engineer,
  qa-engineer, ai-engineer, software-architect, project-auditor) and the
  dispatch-tier personas (software-engineer, security-reviewer, code-reviewer) all
  run `claude-opus-4-8`.
- Process-execution layering law completed: `features/` modules no longer import
  `subprocess` directly. New `ProcessRunner` Protocol
  (`core/protocols/process_runner.py`) with production adapter
  (`infrastructure/subprocess_runner.py`), consumed via DI by `import_`,
  `ci_preflight`, `specs/doctor`, and `server_registry`; `import-linter` contract
  `features-no-subprocess` enforces it. `container.py` platform branching reads the
  `PLATFORM` capability singleton.
- Bash hook quartet retired; Python hooks are the sole gate surface (PreToolUse
  scoped to write tools; Bash-tool writes documented out of the determinism envelope
  with doctor backstops).
- AI surface (AGENTS.md, rules, skills, personas) rewritten to describe real
  enforcement vs discipline (14 contradictions fixed); memory + constitution §8
  rewritten to the merged kernel. Agent persona parity pass: `[SCOPE ERROR]` redirect
  block in all 9 core personas; report-emission prose deduplicated to
  `workspace-protocol §4`; vestigial `opencode_model` frontmatter keys removed.
- `Operating System :: OS Independent` classifier corrected to
  `Operating System :: POSIX :: Linux` until the 3-OS CI matrix graduates to a hard
  gate.
- All text I/O specifies `encoding="utf-8"` (Windows cp1252 corruption fix); JSON
  stores route through a single `_atomic_write_text` chokepoint using `os.replace`.
  venv executable paths resolved via the platform seam (`Scripts/python.exe` on
  Windows).
- Test architecture: harness-env fixture contract (hook behavior tests run as real
  subprocesses; `DADAIA_*` setenv + hook-import ratchets at zero baseline), two-actor
  concurrency e2e asserting on lock-file history, drift-ratifying tests killed,
  consistency-contract + lifecycle-asymmetry policies.

### Fixed
- SDD gate classifier re-rooted context-relatively: ADDITIVE/MEMORY/FROZEN classes
  now live inside `repos/<slug>/` (unmatched in-repo ⇒ MUTATING, never UNGATED);
  symlinks canonicalized before classification. Kills the
  lease-theft-by-additive-write CRITICAL.
- Lease liveness = TTL + PID veto: holder records a long-lived harness pid
  (payload/getppid); TTL-stale + alive ⇒ yield (no takeover), dead ⇒ takeover; renew
  runs inside the same O_EXCL CAS (race fixed); heartbeat renews on every PostToolUse
  from the harness-native session id (Claude `*` matcher, Codex match-all).
- Session identity consolidated into a single owner module (`session_identity`); bind
  `--mode` optional (default read), persisted in the session record + context
  incumbent pointer; gate mode resolution env → record → live-incumbent →
  IMPLEMENTATION; READ binds are non-acquiring.
- `dadaia ci preflight` no longer self-pollutes (ruff `--no-cache`, mypy cache
  redirected, pollution guard = session snapshot diff) — the pre-push gate passes
  end-to-end; pre-push hook probes the workspace venv (`$DADAIA_BIN` → walk-up →
  poetry → repo venv, fail-closed).
- specs doctor ledger invariants (SPEC-DOC-024..029): phase↔markers,
  CLOSURE-before-archive, unique release ids, naming canon, constitution ref
  resolution, lease↔session coherence.
- Spec/memory fidelity: all 34 confirmed findings of the drift audit resolved —
  memory atoms document the real doctor check codes, the Python-hook SDD gate, the
  hard-gated 3-OS CI matrix, the full CLI/protocol inventory, and a roster without the
  phantom `researcher` agent.
- The CLI is now importable on Windows: the unconditional top-level `import fcntl` in
  the locking and telemetry modules (which crashed every `dadaia` invocation at
  import) is removed and delegated to platform adapters.
- Windows security no-ops closed: the panel auth token is owner-only via `icacls` or
  the panel refuses to start (CWE-732); `/proc` scans and `os.getuid` degrade safely
  off-Linux.

### Security
- Panel HTTP handler: enforce Bearer auth on workspace-sensitive routes that were
  previously served by the unauthenticated dispatch loop — `/reports/<path>`,
  `/api/panel-status`, `/api/contexts`, `/memory/<slug>/<path>`,
  `/memory-view/<slug>/<path>` — whenever the panel is NOT loopback-bound (defense in
  depth; loopback keeps the zero-friction local default). (F-01/F-02/F-04)
- Scaffolder renders templates with a Jinja2 `SandboxedEnvironment`, blocking template
  access to Python internals. (F-03)
- `GitSubprocessClient.clone` refuses unsafe URLs (`ext::` transport and
  option-injection via a leading `-`) before invoking git. (F-05)
- Panel loopback auth bypass removed (tokenless sensitive API ⇒ 401 even on
  127.0.0.1; tokenized-URL handoff, token file modes re-tightened to 0o600).
- `context dead` refuses untracked files without `--commit`; `--commit` runs a
  structural secret scan (incl. cert/key file suffixes) before any push.
- public-privacy gate fails closed: packaged baseline structural denylist scans even
  without an operator denylist.

## [0.1.4] — 2026-06-03

### Added
- Executable pytest taxonomy (`unit`/`contract`/`integration`/`e2e`/`slow`/`tmp` markers), a `tests/contract/**` public-contract layer, and a `tests/tmp/**` quarantine excluded from default collection (`test-suite-architecture`).

### Changed
- Coverage instrumentation removed from default pytest `addopts` (fast local default); coverage now enforced only by an explicit CI job. CI split into per-layer jobs (lint, typecheck, unit-fast, contract-coverage, integration, e2e-python, e2e-panel).

### Security
- Removed the last hardcoded private identifiers from shipped source: the public-privacy denylist no longer embeds operator-specific values. Terms are now loaded at runtime from outside the published package (`$DADAIA_PRIVACY_DENYLIST` or `<repo_root>/.dadaia/states/privacy_denylist.json`); the library ships with an empty default (dev-guardrail rule #4).
- Purged residual private identifiers from the full git history and genericized changelog entries that previously enumerated them.

## [0.1.3] — 2026-06-03

### Security
- Removed two private academy modules (12 files) from the published wheel — they contained private-infrastructure operational docs.
- Purged private project identifiers (admin IP, hostname, and internal project/infrastructure slugs) from library source, tests, and fixtures; replaced with generic placeholders throughout.
- Removed hardcoded personal absolute paths (`/home/<user>/…`) from tests and fixtures.
- Re-seeded `sessions_seeded.sqlite` telemetry fixture to strip private session data.
- Genericized a private example in `core/workspace_resolver.py` docstring (shipped source).
- Neutralized canonical assets for open-source consumers: `public/data/AGENTS.md` language default changed to language-neutral; removed leaked operator-infra examples from the `dadaia-grill-me` skill.
- Trimmed bloated canonical rules to concise imperative form: `dadaia-workspace-dev-guardrail` 134→63 lines, `tmp-file-guardrail` 79→47 lines, `plugin-scope` 35→17 lines (removed dangling `ADR-X7` reference).
- Verified: built wheel + sdist contain zero private-identifier leaks; full test suite green (2404 passed, 88.69% coverage).

### Added
- Markdown-memory source (`memory-markdown-source-v1`): product memory is now `.md` atoms with YAML frontmatter; panel renders via `mistune`; deleted renderer/schemas/HTML templates from the old YAML/HTML memory approach.
- Panel Kanban tab: task-state board (`[ ]`/`[-]`/`[x]`) with `/api/kanban` endpoint; handoff verdict gate enforced at panel level (`panel-kanban-v1`).
- Spec-context tree-v2: `ALIVE`/`DEAD` context states, new verbs (`bind`/`unbind`), per-release session locks with `acquire`/`release` semantics (`spec-context-tree-v2`).
- Per-release TOCTOU-hardened session locks: `Impl-XOR-Review` lock enforcement with stale-lock detection and temp-race fixes (`r2-lock-toctou-hardening-v1`).
- `ctx-inject v2`: `context use` → `bind` rename; `primary_context.json` retired from hook; `ctx-inject.sh` updated to v2 context resolution.
- `dadaia public stage` sanitization: defaults for new workspaces scrubbed of private agentic config.

### Changed
- `specs/` carved out of the public repository: marked untracked + added to `.gitignore`; private infra paths and project slugs that had leaked via the specs tree are now excluded from the wheel and sdist.
- `public/data/AGENTS.md` language default is now language-neutral (was "Portuguese (BR) by default").
- GitHub Actions SHA pins corrected: malformed `actions/download-artifact` SHA in `release.yml` fixed; all action pins refreshed.

### Fixed
- `release.yml`: corrected malformed `actions/download-artifact` SHA pin that broke the trusted-publishing release job.

### Removed
- Two private academy modules removed from the `dadaia_workspace/` package tree (private infra docs; 12 files).

## [0.1.1] — 2026-05-23

### Added
- 21-agent universal topology: ai-engineer, software-engineer-python, software-engineer-node, data-engineer, data-analyst, data-architect (6 new personas since 0.1.0); all agents carry TOML projections for Codex.
- Codex orchestration parity: `_install_codex_agents()` generates `.codex/agents/*.toml` per agent with model mapping (Claude→Codex identifiers); `_install_codex_rules()` projects only frontmatter-bearing rules; `CodexAgentDispatcher` with parallel best-effort dispatch; doctor checks D-CX-1..5 for Codex drift.
- Handoff schema v1.1: `scope`, `metrics`, `findings[].detail_md`, `findings[].fix_recommendation` fields; CLI hard-error on missing `findings[]`; `dadaia reports lint` subcommand for orphan/oversized/missing-fields detection.
- Bug reporting infrastructure: `bug_reporter.py`, `.dadaia/bugs/reported.json` persistent store, CLI exception handler via `_safe_app()`, doctor persistence via `report_doctor_finding()`, open-bug surface during `dadaia specs` release creation.
- Doctor `[warn] git-dirty` check: detects uncommitted edits in `public/` working tree (blind spot for the doctor diff).
- Workspace panel r5: 7-tab canonical order (Projects, Agents, Workflows, Sessions, Reports, Academy, Settings), Projects tab redesign, Reports tab, Academy tab (infrastructure), logo redesign, dark-mode token coverage.
- DEV workspace self-reference section in `dadaia-workspace-dev-guardrail.md` (4 invariants for the editable-install loop).
- Spec-refinement workflow v0.3.0: `research_evidence` stage (researcher) added before `discovery`; `spec_write` stage post-synthesis.
- `dadaia public doctor`: `[not-applicable]` status for logical type mismatches (e.g. workflows in Codex runtime); codex rules filter (behavioral prose rules excluded).
- Runtime codex adapter skills (`runtime/codex/design-ctx/SKILL.md`, `runtime/codex/frontend-ctx/SKILL.md`) for plugin-scoped Codex surface.
- Shared skills: `frontend-design`, `frontend-implementation-quality`, `design-report-quality-gate`, `design-reference-research`, `ux-ui-review`.

### Fixed
- CLAUDE.md is now a 1-line stub delegating to AGENTS.md (T-41); no longer a source copy — reduces noise in consumer repos.
- 19 pre-existing test failures resolved: schema v1.1 fixture gaps, stale model identifiers in test fixtures (`claude-sonnet-4-5`→`claude-sonnet-4-6`), T-41 CLAUDE.md stub invariant, stale EXPECTED_SKILLS set, `commands/` staging dir removal, behavioral-prose rule excluded from `.codex/rules/` projection, workflow v0.3.0 stage ordering in e2e test.
- 4 `dadaia context deactivate` bugs: git subprocess upstream tracking, service layer error handling.
- Init legacy resolver replaced with `resolve_workspace_root_for_init`; no longer errors on un-initialized workspaces.
- CSP `script-src` unsafe-inline replaced with SHA-256 hash in panel server.
- SQLite dead tables dropped via migration 6; telemetry service hardened.
- Exit code 3 on uninitialized workspace for `dadaia reports validate` (workspace resolver moved inside try).

### Changed
- All agents default to `claude-sonnet-4-6` (ADR-X4); ai-engineer moved from Opus to Sonnet; researcher uses `claude-haiku-4-5-20251001`.
- `AGENTS.md` is the canonical guardrail file; CLAUDE.md is a 1-line pointer (Option C / T-41).
- Skills split: 16 universal skills after removing game-*, devops-gitflow-governance, devops-deploy-strategies, architect-*, github-actions-pipelines, security-audit-protocol.

## [0.1.0] — 2026-05-14

### Added
- `dadaia` CLI: `init`, `context {create, list, show, activate, deactivate, promote, delete, use}`, `repos`, `public {stage, install, doctor}`, `doctor`, `academy`, `export`, `import`, `orchestrate {list, show, run, status, resume}`.
- Spec Context Project model (v4.0): multi-active contexts, single `is_primary` flag, JSON-backed state.
- Universal agentic assets: 6 agents (`product-engineer`, `software-architect`, `software-engineer`, `qa-engineer`, `devops-engineer`, `game-developer`), 17 skills, 4 commands, 2 rules.
- Cross-tool parity for Claude Code, OpenCode, Codex, and `.agents/`.
- Workspace portability: `dadaia export` / `dadaia import` with branch tracking.
- Multi-Agent Orchestration v0.1 — `workflows/` first-class asset type, durable run state (`manifest.json` + `events.jsonl`), 4 dispatchers (Claude/CLI/OpenCode/Codex), 2 seed workflows (`spec-refinement`, `tdd-cycle`).
- `input_contract` block in every agent frontmatter (Handoff Schema v1).
- `[partial]`/`[unsupported]` doctor status classification per runtime.
- CI workflow (`.github/workflows/ci.yml`) with lint, typecheck, test, pr-title jobs.
- Release workflow (`.github/workflows/release.yml`) with OIDC trusted publishing to PyPI.
- SDD Gate v2 (`sdd-spec-gate.sh`): gates edits to `repos/<primary_slug>/` (active Spec Context), requires `[-]` IN PROGRESS task marker in TASKS.md, meta-edit bypass for spec files (TASKS.md, PLAN.md, SPEC.md), fail-open on any internal error.
- Task State Contract (RF-CONV-006): 3-marker convention `[ ]`/`[-]`/`[x]` with `dadaia-task-manager` skill propagated to all 6 agents.
- Coverage gate: `--cov-fail-under=80`; current coverage 82%+ across unit + integration tests.

### Fixed
- BUG-002: `ctx-inject.sh` and `sdd-spec-gate.sh` now resolve `WORKSPACE_ROOT` via their own script path; no longer depend on git rev-parse or `$HOME`.
- BUG-003: `dadaia import` now rewrites absolute workspace paths in `.claude/settings.json`, `.codex/hooks.json`, and `.opencode/opencode.json` after extraction (`patch_json_paths` phase).
