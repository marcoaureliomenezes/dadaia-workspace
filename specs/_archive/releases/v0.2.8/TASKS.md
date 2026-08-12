# TASKS — Release v0.2.8 — Kimi Code as a Layer-1 Entry Harness

> **Status:** Aprovado

**Release ID:** v0.2.8
**Owner:** product-engineer
**Source PLAN:** `specs/releases/v0.2.8/PLAN.md`
**Workflow:** release-definition / tasks_create

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Tasks

- [x] **T1 - Harness registry: add kimi-code as L1 entry harness**

**Owner role:** software-engineer

**Preconditions:** `SPEC.md` and `PLAN.md` for `v0.2.8` are `Aprovado`.

**Write set:**

- `dadaia_workspace/core/harness_registry.py`
- `tests/unit/core/test_harness_registry.py`

**Description:**

Update the registry contract tests first to expect `kimi-code` in `L1_ENTRY_HARNESSES`,
`PROJECTION_TARGETS`, and `INSTALL_TARGETS` (and NOT in `L2_WORKER_HARNESSES`), then add
`"kimi-code"` to `L1_ENTRY_HARNESSES` in
`dadaia_workspace/core/harness_registry.py`. Verify `parse_harness_set` accepts the new id
and that the no-duplicated-literal scan still passes. No L2 surface is touched.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_harness_registry.py`

---

- [x] **T2 - runtime_config: kimi managed hook block + shim generators**

**Owner role:** software-engineer

**Preconditions:** T1 is `[x]`.

**Write set:**

- `dadaia_workspace/infrastructure/runtime_config.py`
- `tests/unit/infrastructure/test_runtime_config_kimi.py`

**Description:**

Add to `dadaia_workspace/infrastructure/runtime_config.py`:

- `kimi_code_home(env=os.environ) -> Path` — `KIMI_CODE_HOME` override, default `~/.kimi-code`.
- `kimi_hooks_block(home: Path) -> str` — the exact managed TOML block of PLAN §3.1
  (four `[[hooks]]` rules between the marker comments, absolute shim paths).
- `kimi_hook_shims() -> dict[str, str]` — the four POSIX sh shim bodies of PLAN §3.2
  (`dadaia-kimi-pre-gate.sh`, `dadaia-kimi-post-gate.sh`, `dadaia-kimi-ctx-inject.sh`,
  `dadaia-kimi-post-compact.sh`): walk-up `.dadaia/.venv/bin/python` resolution, stdin
  forward, block→exit 2 translation for the pre-gate, fail-open everywhere.

New unit tests pin the block text (events, matchers, marker lines, absolute commands),
the shim set, and the fail-open/exit-code contract of the pre-gate shim logic.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/infrastructure/test_runtime_config_kimi.py`

---

- [x] **T3 - Projection source, installer, and doctor family for kimi-code**

**Owner role:** software-engineer

**Preconditions:** T1, T2 are `[x]`.

**Write set:**

- `dadaia_workspace/public/kimi-code/AGENTS.md`
- `dadaia_workspace/infrastructure/public_assets_common.py`
- `dadaia_workspace/infrastructure/public_assets.py`
- `dadaia_workspace/infrastructure/install_helpers.py`
- `tests/unit/infrastructure/test_public_assets_kimi.py`

**Description:**

- Create `public/kimi-code/AGENTS.md` (kimi-facing orientation: hook trust boundary,
  managed user-level block, bind ritual, `/skill:` and `.agents/skills/` usage).
- Add `"kimi-code"` to `_COPY_DIRS` and a `_KIMI_DIRS` tuple in
  `public_assets_common.py`; add `.kimi-code` to the legacy-dirs list in
  `install_helpers.py`.
- Implement `_install_kimi_code()` in `public_assets.py` (dispatch branch in `install()`):
  verbatim copy of staged `agentic/kimi-code/` → `.kimi-code/`, plus the user-global
  upsert of the managed `[[hooks]]` block (marker-delimited replace-or-append; never
  touch content outside markers; create the file if missing) and shim files (chmod 755)
  via `write_generated`-style idempotence.
- Add the `kimi:` doctor block mirroring the pi block (tree compare), generated-block
  currency checks for config block + shims, and the out-of-profile warning.
- New tests cover: install creates `.kimi-code/AGENTS.md`; block upsert is idempotent and
  preserves foreign config content; doctor flags drift and passes on a fresh install;
  profile scoping excludes kimi when absent from `harness_profile.json`.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/infrastructure/test_public_assets_kimi.py tests/unit/infrastructure/test_public_assets_install.py tests/unit/infrastructure/test_public_assets_doctor.py`

---

- [x] **T4 - ctx_inject: PostCompact marker + compact-epoch re-injection**

**Owner role:** software-engineer

**Preconditions:** T1 is `[x]` (independent of T2/T3).

**Write set:**

- `dadaia_workspace/hooks/ctx_inject.py`
- `tests/unit/hooks/test_ctx_inject_compact.py`

**Description:**

In `dadaia_workspace/hooks/ctx_inject.py`:

- When the resolved hook event is `PostCompact`, write
  `.dadaia/tmp/ctx-compact-<session_id>` (workspace-resolved, fail-open) and exit 0 with
  no stdout.
- Extend the fire predicate: fire iff bind-epoch marker is newer than the sentinel **or**
  the compact marker is newer than the sentinel; reuse the existing sentinel write and
  24 h GC. Default behavior (no compact marker) is byte-identical to today.

New tests: PostCompact writes marker + no output; first UserPromptSubmit after a compact
re-injects once; second prompt does not re-fire; pre-existing bind-epoch tests keep
passing.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/hooks/`

---

- [x] **T5 - Root law, init scaffolding, capabilities**

**Owner role:** software-engineer

**Preconditions:** T1 is `[x]`.

**Write set:**

- `dadaia_workspace/hooks/root_whitelist.py`
- `dadaia_workspace/features/spec_context/doctor.py`
- `dadaia_workspace/features/workspace/service.py`
- `dadaia_workspace/core/models/workspace.py`
- `dadaia_workspace/features/capabilities/service.py`
- `dadaia_workspace/cli/commands/init.py`
- `dadaia_workspace/cli/commands/public.py`
- `tests/unit/hooks/test_root_whitelist.py`
- `tests/unit/test_spec_context_doctor_root.py`
- `tests/unit/features/workspace/test_service_harness_profile.py`
- `tests/unit/cli/test_init_harness.py`

**Description:**

Add `.kimi-code` to the root whitelist and the spec-context doctor allowed root dirs;
scaffold `.kimi-code/` in `dadaia init` (mkdir branch + profile acceptance); add the
optional `kimi_dir` workspace field; list `kimi-code` in the capabilities `layer_1`
descriptor; refresh the `--target` / `--harness` help strings that enumerate harnesses.
Update the affected tests.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/unit/hooks/test_root_whitelist.py tests/unit/test_spec_context_doctor_root.py tests/unit/features/workspace/ tests/unit/cli/test_init_harness.py`

---

- [x] **T6 - Harness fixtures, contract tests, goldens, enumeration sweeps**

**Owner role:** qa-engineer

**Preconditions:** T1–T5 are `[x]`.

**Write set:**

- `tests/fixtures/harness_env.py`
- `tests/contract/test_harness_env_contract.py`
- `tests/unit/infrastructure/test_install_target_goldens.py`
- `tests/unit/infrastructure/_golden/install_target_resolution_v0158.json`
- `tests/unit/infrastructure/_golden/doctor_all_four_v0158.json`
- `tests/unit/infrastructure/_golden/panel_runtime_validation_v0158.json`
- `tests/e2e/features/test_public_pipeline.py`
- `tests/integration/test_plugin_projection.py`
- `tests/integration/test_public_install_e2e.py`

**Description:**

Add `kimi_hook_env()` to the harness-env fixture and register the kimi hook modules in
the contract lists; regenerate the install-target goldens
(`UPDATE_INSTALL_GOLDENS=1`) so `{all, agents, claude, codex, pi, kimi-code}` are pinned;
update every hardcoded harness enumeration (e2e pipeline profile lists, plugin projection
targets, consumer fan-out, json store profile tests) to include kimi-code where the
roster derives from L1.

**Validation:**

- `cd /home/ubuntu/workspace/repos/dadaia-workspace && ../../.dadaia/.venv/bin/python -m pytest -p no:cacheprovider tests/contract/ tests/unit/infrastructure/test_install_target_goldens.py tests/e2e/features/test_public_pipeline.py`

---

- [x] **T7 - Smoke validation: temp consumer workspace + shim replay**

**Owner role:** qa-engineer

**Preconditions:** T1–T6 are `[x]`.

**Write set:**

- `.dadaia/tmp/kimi-smoke/` (landing zone only; no repo files)

**Description:**

In a throwaway workspace under `.dadaia/tmp/`: run `dadaia public stage &&
dadaia public install --target all` with `KIMI_CODE_HOME` pointed at a sandbox dir;
assert `.kimi-code/AGENTS.md` lands, the managed block appears in the sandbox
`config.toml`, and the four shims are executable; then replay synthetic kimi payloads
(stdin JSON with `session_id`, `cwd`, tool fields) through the installed shims asserting:
pre-gate allows a normal write (exit 0), blocks a root-law violation (exit 2 + stderr
reason), ctx-inject prints context for a bound session, post-compact writes the marker
and the next prompt re-injects. Finish with `dadaia public doctor` and
`dadaia specs doctor` clean. Remove nothing outside `.dadaia/tmp/`.

**Validation:**

- Smoke script exits 0; both doctors clean; `git status --short` shows only intentional
  source/test changes.

---

- [x] **T8 - Operator-facing docs: README, pyproject, AGENTS.md templates**

**Owner role:** product-engineer

**Preconditions:** T1–T7 are `[x]`.

**Write set:**

- `README.md`
- `pyproject.toml`
- `dadaia_workspace/public/data/AGENTS.md`
- `AGENTS.md`

**Description:**

Add kimi-code to the README supported-harness table (Layer-1, with the user-level hook
block caveat), to the `pyproject.toml` description/keywords, and to both AGENTS.md
surfaces (root-law directory whitelist gains `.kimi-code/`; Layer-1 roster names four
harnesses). Run `dadaia public stage && dadaia public install --target all &&
dadaia public doctor` in this workspace afterward so the regenerated projections pick up
the template change, and confirm `[ok] public-privacy`.

**Validation:**

- `cd /home/ubuntu/workspace && .dadaia/.venv/bin/dadaia public doctor` (includes
  `[ok] public-privacy`); README table renders four Layer-1 harnesses.

---

- [x] **T9 - Product memory update (CLOSURE phase)**

**Owner role:** product-engineer

**Preconditions:** T1–T8 are `[x]`; ACTIVE.md phase is `CLOSURE`.

**Write set:**

- `specs/memory/tech-stack.md`
- `specs/memory/architecture.md`
- `specs/memory/product/harness/harness-kimi-code.md`
- `specs/memory/product/catalog.json`
- `specs/memory/product/index.md`

**Description:**

Create `harness-kimi-code.md` (mirroring `harness-pi.md` structure: surfaces, hook wiring,
trust boundary, out-of-scope L2), register it in `catalog.json` and the `index.md`
harness table, and update `tech-stack.md` / `architecture.md` harness rosters
(four Layer-1 harnesses; kimi user-global hook block seam; FR4 compact-epoch as a
kimi-first mechanism). Memory writes happen only in the CLOSURE phase per the phase gate.

**Validation:**

- `cd /home/ubuntu/workspace && .dadaia/.venv/bin/dadaia specs doctor` clean; catalog
  JSON parses and lists `harness-kimi-code`.
