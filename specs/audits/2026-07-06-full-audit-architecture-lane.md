# Full Audit 2026-07-06 — ARCHITECTURE + CODE + TESTS Compliance Lane

**Auditor:** project-auditor (lane report)
**Repo:** dadaia-workspace @ `4a433063` (main, clean; post-v0.1.60 / post-PyPI-0.2.1 / post-fable-5-retier)
**Date:** 2026-07-06
**Toolchain:** `.dadaia/.venv` (editable install resolving to repo source); pytest `-p no:cacheprovider`, ruff `--no-cache`, `lint-imports --no-cache`, `COVERAGE_FILE` redirected outside the repo. No cache dir left in the tree at finish (`git status` clean).

---

## 1. Import-boundary + layering compliance

### Run evidence

- `lint-imports --no-cache`: **8 contracts kept, 0 broken** (360 files, 1831 dependencies analyzed; exit 0). Matches `specs/memory/architecture.md` §"Enforcement (actual state)" exactly.
- Ignore-cap contract: hand-verified against `setup.cfg` — **26 edges = 9 (features-no-infrastructure, lines 55-58/67-70/76) / 4 (features-no-subprocess, lines 92-95) / 13 (features-no-cross-feature, lines 211-238)**, equal to the pinned `_RECORDED_PER_FAMILY_CAP` in `tests/contract/test_import_linter_ignore_cap.py:69-73`; the stale-above-reality and per-family tests make the pin falsifiable both directions.
- Core file-I/O AST ratchet: `tests/contract/test_core_file_io_purity.py:49-50` pins exactly `{specs_backup, specs_version, specs_resolver, workspace_resolver}`; includes a ratchet-down test flagging stale authorized stems. Holds.
- v0.1.60 plugin seam: `core/models/plugin_pack.py` (stdlib-only imports), `core/protocols/plugin_store.py:19` (imports only the core model), `infrastructure/json_plugin_store.py:24-25` (core model + infra sibling `public_assets_common`). **No feature imports — seam module hygiene clean.**
- Newest-modules spot-read (5): `cli/commands/plugin.py`, `core/harness_registry.py` (zero internal imports — pure), `features/lifecycle/fragment_coherence_doctor.py`, `features/lifecycle/role_atoms.py`, `features/lifecycle/workflows/_fragment_gate.py` — all imports stay within core + own-feature boundaries.

### Findings

| ID | Sev | Finding | Evidence | Remediation direction |
|----|-----|---------|----------|----------------------|
| A-1 | MEDIUM | **`PluginStore` port is dead-on-arrival.** `core/protocols/plugin_store.py` has ZERO importers in production and tests (grep for `protocols.plugin_store` across `dadaia_workspace/` + `tests/`: no hits). Both consumers construct the concrete adapter directly (`cli/commands/plugin.py:26,81` — `JsonPluginStore()`; `infrastructure/public_assets.py:50`), and `container.py` has no plugin factory. Memory drift: `plugin-packs` atom + `architecture.md` (core/ paragraph) present "PluginStore port + JsonPluginStore adapter" as a live ports-and-adapters seam — the port half is decorative. | `core/protocols/plugin_store.py` (whole module); `cli/commands/plugin.py:26`; `dadaia_workspace/container.py` (no `plugin` reference) | Either wire the port through `container.build_*` DI (software-engineer) or delete the protocol and correct the memory claim (product-engineer at next DEFINITION/CLOSURE). |
| A-2 | MEDIUM | **`cli → infrastructure` direct imports are unguarded (×11 sites, 8 modules).** The declared dependency graph (`architecture.md` §Dependency rules mermaid) has no `cli → infrastructure` edge and names `container.py` "sole composition root", yet: `cli/main.py:37`, `cli/commands/lock.py:13`, `ci.py:113`, `public.py:47`, `bugs.py:26`, `context.py:39`, `specs.py:21,25`, `plugin.py:26-27` (new in v0.1.60), `lifecycle.py:1361`. No import-linter contract has `cli` as a source module, so this erosion class grows silently (v0.1.60 added 2 new edges). | `setup.cfg` (no cli-source contract); sites listed | Add a `cli-no-infrastructure` contract with the 11 documented edges as capped ignores (mirrors the F10 pattern), or amend `architecture.md` to declare the cli→infra edge legal. software-architect to adjudicate; ai/software-engineer to wire. |
| A-3 | LOW | Aged transitional `sys.platform` TODO guards in features: `features/telemetry/service.py:60`, `features/spec_context/locking.py:76,94` ("Replace with PLATFORM.has_fcntl once WS-1/T-018-05 lands" — v0.1.8 era, ~50 releases ago). Documented as ADR-1 lazy defaults in `setup.cfg:54` and tracked in backlog `features-import-infrastructure-direct-debt` (present in `specs/backlog/candidates.md`). | file:line above | Fold into the tracked container-DI cleanup release. |

## 2. Dead / stale code

### Sweep evidence

- **Zero-importer sweep** over 264 production modules (dotted-path + relative-import grep across source + tests): exactly **1 true orphan** — `core/protocols/plugin_store.py` (finding A-1). All other candidates (`cli/commands/*`, `__main__.py`, `core/protocols/{harness_profile_store, shutdown_handler}.py`) verified as false positives (registered via `cli/main.py:7-27`; protocols consumed by `features/workspace/service.py`, `container.py`, `features/panel/server.py`).
- **TODO/FIXME/XXX:** 6 total in production code, all one family (the A-3 `PLATFORM.has_fcntl` transition). No FIXME/XXX at all.
- **Deprecation-expiry law:** one soft-expired promise found (D-1 below). Fulfilled promises verified: hooks standalone `main()`s (promised v0.1.14, removed v0.1.53 — `hooks/pre_gate.py:14-15`); `--model` flag (removed v0.1.57 — `cli/commands/lifecycle.py:371`).
- **noqa inventory:** 5× `F401` (4 documented facade re-exports in `infrastructure/public_assets.py:55,64,90,100`; 1 msvcrt probe `file_lock_windows.py:64`; 1 annotated re-export `spec_context/locking.py:37`) — none is the W4B dead-import shape. ~40× `BLE001`, every one carrying a fail-open/fail-safe rationale comment. No naked suppression bulk.
- **Commented-out code:** ruff `ERA001` → 6 hits, all benign documentation (CSP-hash recipe `features/panel/handler.py:104-105`; budget labels `features/telemetry/reader/claude.py:249,258`; step label `features/workspace/service.py:97`; schema-keyword caption `infrastructure/stdlib_handoff_validator.py:178`). `F401/F811/F841` via ruff: zero un-noqa'd hits.

### Findings

| ID | Sev | Finding | Evidence | Remediation direction |
|----|-----|---------|----------|----------------------|
| D-1 | LOW | **`agent_tier` schema property past its expiry.** Deprecated v0.1.53 ("A later release drops this property entirely" — `public/schemas/memory/memory-frontmatter-v1.schema.json:52-55`); 7 releases later it survives, and its stated retention rationale is empty: zero atoms under `specs/memory/` carry the key. Partially anchored by backlog `tier-taxonomy-rename.md`. | schema line 52; grep of `specs/memory/**` frontmatter (0 carriers) | Drop the property (ai-engineer via public-asset flow) in the release that consumes `tier-taxonomy-rename`. |
| D-2 | LOW | **Stale local `dist/` artifact masquerading as 0.2.1.** `dist/dadaia_workspace-0.2.1-py3-none-any.whl` + `.tar.gz` are dated 2026-06-07, their metadata still says "…Claude Code, Codex and **OpenCode**" (OpenCode was deleted in v0.1.24), and `public/plugins/` inside them holds two extinct `.ts` files instead of the v0.1.60 packs. Gitignored, but name-collides with the genuinely published PyPI 0.2.1 (which is correct — see §6). | `dist/` mtimes; PKG-INFO `Summary` line; wheel listing | Operator: delete the stale `dist/` contents. |
| D-3 | INFO | Working-tree cache pollution observed mid-audit: `.mypy_cache/` + `.ruff_cache/` appeared at repo root at 10:45 local (this lane's own invocations all used `--no-cache`/redirected caches; the preflight's argv-level cache redirection is unit-pinned in `tests/unit/features/ci_preflight/test_no_pollution.py`). Most probable origin: a concurrent audit-lane/tooling invocation of bare `mypy`/`ruff`. Removed before finish per the repo-cleanliness law. | stat timestamps (2026-07-06 10:45:38/53) | Discipline reminder for all lanes: `ruff --no-cache`, `mypy --cache-dir` outside the repo. |

## 3. Test posture

### Run evidence

- Full unpiped suite: `pytest -p no:cacheprovider -q` → **4674 passed, 17 skipped, 0 failed, 1 warning, exit 0** in 418.07s.
- **All 17 skips enumerated and classified — zero rot:**
  - 6× Windows-runner-only (legit-conditional): `test_file_lock_windows.py:49,67,88,102`, `test_file_permission_windows.py:195`, `test_telemetry_lock_windows.py:129`.
  - 10× opt-in live credit-spenders (legit-conditional env gates): `DADAIA_CODEX_LIVE` ×4 (`codex_live/…:70,99,131,82`), `DADAIA_PI_LIVE`/`DADAIA_E2E_REAL_WORKER` ×4 (`pi_live/…:76,93,270,331`), `DADAIA_CLAUDE_LIVE` ×2 (`claude_live/…:91,108`).
  - 1× environment probe (legit-conditional): no non-loopback IPv4 (`tests/e2e/features/test_panel.py:345`).
- **Frozen v0.1.50 no-steal suite:** `test_lease_self_recognition.py`, `test_lease_by_session_index.py`, `test_session_coherence_confirmation.py`, `test_common_sid_precedence.py` — zero commits since `7b198d49` (v0.1.50). The two adjacent files touched later (`test_lease_pid_liveness.py`, `test_two_actor_lease.py`, both in `d3f46360` v0.1.53) were behavior-preserving driver repoints (`hooks.sdd_gate` → `hooks.pre_gate` after the standalone `main()` deletion) explicitly flagged and adjudicated at the QA ship-gate in the v0.1.53 commit message. **Invariant preserved; no silent drift.**
- **Contract inventory (28 files under `tests/contract/`):** assert-density sweep + full read of the lowest-assert files. `test_lease_probe_residue.py` (1 assert) is a real AST walk over every production `lease.acquire/steal` call site; `test_core_file_io_purity.py` and `test_import_linter_ignore_cap.py` carry bidirectional (cap + stale-cap) assertions. **No tautologies found in the sampled set; zero `assert True` patterns anywhere in `tests/contract/`.**
- **Hygiene:** `tests/conftest.py` carries the autouse per-function root-write backstop guard + session pollution guard. All 14 test files added since v0.1.58 (`b0bd8217..HEAD`) contain **zero** `Path.home()/os.getcwd()/Path.cwd()/expanduser` reads (three-leak-class law clean). Older `Path.home()` uses are monkeypatched (`test_runtime_adapters.py:271,285,304`) or confined to opt-in live probes.

### Findings

| ID | Sev | Finding | Evidence | Remediation direction |
|----|-----|---------|----------|----------------------|
| T-1 | LOW | The suite's single warning is a `PytestRemovedIn10Warning`: class-scoped fixture defined as instance method in `tests/integration/test_telemetry_corrupt_db.py` (`TestHandlerDegradedResponses`). Breaks outright under pytest 10 (dep range allows `pytest <10`), and the instance-attribute semantics are already a latent trap. | warnings summary of the full-suite log; `pyproject.toml` (`pytest = ">=8,<10"`) | software-engineer: convert to `@classmethod` fixture per the pytest deprecation doc. |

## 4. Coverage reality

- CI-equivalent command run locally: `pytest -q -m "unit or contract" --cov=dadaia_workspace --cov-report=term-missing --cov-fail-under=80 tests/unit tests/contract` → **TOTAL 83.83% (22,000 stmts / 3,557 miss), gate 80% PASSED, exit 0** (3987 passed, 6 skipped, 344s).
- **5 worst-covered production modules (>30 stmts, within the gated unit+contract scope):**

| % | Module | Size | Note |
|---|--------|------|------|
| 0% | `features/backlog/doctor.py` | 98 stmts | covered by `tests/integration/test_backlog_doctor.py` — outside the gate scope |
| 0% | `features/backlog/removal_lifecycle.py` | 33 stmts | covered by `tests/integration/test_backlog_removal_loop.py` — outside the gate scope |
| 12% | `infrastructure/file_lock_windows.py` | 57 stmts | Windows-runner-only paths (legit on POSIX) |
| 15% | `cli/commands/migrate.py` | 103 stmts | thin CLI over `features/migrate` |
| 18% | `cli/commands/newartifacts.py` | 115 stmts | thin CLI over `features/spec_artifacts` |

- Finding C-1 (INFO): the 80% gate measures only unit+contract, so integration-covered modules (backlog doctor/removal — CI-enforced behavior!) appear as 0% and the true product coverage is higher than the gated figure. Not a defect; recorded so nobody "fixes" the 0% rows with slop unit tests.

## 5. CI workflow health

- **Pins:** every action SHA-pinned with version comments (checkout v7.0.0, setup-python v6.3.0, cache v6.1.0, upload v7.0.1 / download v8.0.1, pypi-publish v1.14.0, gitleaks-action v2.3.9); `poetry==1.8.3` pinned in all 12 install sites. Nothing stale enough to flag.
- **5-check parity (local pre-push gate vs CI):** `features/ci_preflight/service.py` runs `ruff format --check --no-cache` + `ruff check --no-cache` + `mypy --strict --cache-dir <outside>` + `lint-imports --config setup.cfg --no-cache` (fail-closed via `require=True`, service.py:224-229) + `pytest` (full minus `tests/performance`; service.py:250). CI mirrors: `ci.yml` lint job (format:84 / check:87 / lint-imports:92), typecheck job (mypy:117), and the pytest jobs. **Parity holds.**
- **Jobs that can never run:** none mis-wired. `verdict-gate` (ci.yml:420) no-ops on push/PR **by documented design** (handoffs gitignored; asserts only on `workflow_dispatch` sidecars). `hotfix-branch-name` fires only on `hotfix/v*` pushes, consistent with its trigger.
- **release.yml smoke matrix vs supported Pythons:** smoke-test = single ubuntu + Python 3.12 leg (release.yml:221-243). `pyproject.toml` declares `python = "^3.12"` (accepts 3.13/3.14) while only 3.12 is classifier-listed and CI-tested. Cross-OS is covered pre-publish by ci.yml's hard-gated Windows/macOS legs, not re-smoked post-publish. INFO-level: acceptable, but `^3.12` oversells the tested range.

### Findings

| ID | Sev | Finding | Evidence | Remediation direction |
|----|-----|---------|----------|----------------------|
| CI-1 | LOW | **e2e-panel bootstrap writes the legacy v1 state file `primary_context.json`.** Its only production references are the v1→v2 migration *deleter* (`cli/commands/migrate.py:71-72`, `features/migrate/state_v2.py:54`); the panel never reads it, and `architecture.md` §Runtime state does not list it. Pure cruft that keeps a dead concept alive in CI. | `.github/workflows/ci.yml:314-320`; `release.yml:135-141` | devops surface (plugin not installed → operator or software-engineer under release scope): drop the heredoc block from both workflows. |
| CI-2 | LOW | **The 39-line e2e-panel bootstrap block is duplicated verbatim** between `ci.yml:291-329` and `release.yml:112-150` (same hand-synced-copy failure family as the tri-copy gotcha). A future bootstrap fix applied to one file silently skews the other. | both ranges | Extract to a composite action or a `.github/scripts/bootstrap-panel-ws.sh` called from both. |

## 6. Public-package hygiene

- `pyproject.toml:7,10`: `packages = [{include = "dadaia_workspace"}]`, `exclude = ["**/__pycache__", "**/*.pyc", "**/*.pyo"]` — package scope is exactly the library tree.
- **Published PyPI 0.2.1 wheel downloaded and inspected** (the artifact users actually get, built fresh by release.yml): 513 entries, **all** under `dadaia_workspace/` + dist-info; **all 9 `public/plugins/` pack files present** (frontend-design: pack.json + 2 agents + 1 skill + rules/.gitkeep; devops: pack.json + 1 agent + 1 skill + rules/.gitkeep) — the v0.1.60 packs-ship-in-package intent is REAL in the shipped artifact; **zero** `test_*`/`conftest.py`/`.pyc`/`specs/` leaks; METADATA summary current ("Claude Code, Codex and PI").
- No test or spec file exists inside `dadaia_workspace/` in source (find: 0 hits).
- The only blemish is the stale local `dist/` (finding D-2), which is *not* what PyPI serves.

---

## Lane scorecard

| Area | Score (0-10) | Basis |
|------|-------------|-------|
| 1. Import boundaries / layering | 8 | 8/8 contracts kept, cap 26=9/4/13 exact, ratchets live; minus the dead PluginStore port and the unguarded 11-edge cli→infra surface |
| 2. Dead / stale code | 8 | 1 orphan module in 264; 6 TODOs all one tracked family; noqa fully rationalized; expired agent_tier promise + stale dist/ |
| 3. Test posture | 9 | 4674/0-fail; 17/17 skips legit; frozen suite intact with adjudicated-only touches; no contract tautologies; 1 pytest-10 landmine |
| 4. Coverage | 9 | 83.83% vs 80 gate, honest scope; blind spot documented, integration covers it |
| 5. CI workflow health | 8 | SHA pins + 5-check parity hold; legacy primary_context write + duplicated bootstrap block |
| 6. Package hygiene | 9 | Shipped wheel verified clean and pack-complete; only a stale local artifact |
| **Lane overall** | **8.5** | No CRITICAL/HIGH; drift is confined to seam-decoration, cruft, and unguarded-but-clean layers |

## Severity counts

CRITICAL 0 · HIGH 0 · MEDIUM 2 (A-1, A-2) · LOW 7 (A-3, D-1, D-2, T-1, CI-1, CI-2, + D-3-as-discipline) · INFO 3 (C-1, smoke-matrix range, ERA001/noqa inventory)

## Disposition reminder (audit-disposition law)

Every finding above requires an explicit disposition (`fixed`/`superseded`/`deferred`+reason/`rejected`+reason) in the first release following this audit. Recommended routing: A-1, A-2 → software-architect adjudication + software-engineer; D-1 → ai-engineer (public schema); T-1, CI-1, CI-2 → software-engineer; D-2 → operator; memory corrections (plugin seam claim) → product-engineer at DEFINITION/CLOSURE.
