---
name: qa-engineer-test-architecture-audit
audit: test-architecture
date: 2026-06-30
surface: tests/ + specs/memory/quality-assurance.md
auditor: qa-engineer
mode: READ-ONLY + ADDITIVE
active_release: v0.1.41 (CLOSURE)
atom_release_origin: v0.1.34 (last_updated 2026-06-28)
---

# Test Architecture Audit — dadaia-workspace

READ-ONLY + ADDITIVE audit of the on-disk test suite vs. the
`specs/memory/quality-assurance.md` atom that constitution §13 names "the single source
of truth for quality architecture: test pyramid, layer taxonomy, CI job split, no-slop
policy."

**Headline:** The QA atom is in **good shape** and was maintained recently (its last edit,
commit `740a30af` "test: collapse suite to behavior budget", is the v0.1.34 collapse). The
suite is **healthy and correctly pyramid-shaped** — it is NOT inverted. The findings are
predominantly **documentation GAPS** (real architecture facts the atom omits) and **mild
budget drift** after 7 releases, not contradictions. One §13 concern: the atom carries a
v0.1.34 "collapse" history narrative that belongs in release evidence.

---

## 1. Real test-architecture map (verified by live collection)

Collected via `pytest --collect-only -p no:cacheprovider` against the workspace venv.

| Layer | Tests (collected) | Files | tests/file | Markers |
|---|---|---|---|---|
| `tests/unit/**` | **622** | 59 | 10.5 | `unit` |
| `tests/integration/**` | **555** | 82 | 6.8 | `integration` |
| `tests/contract/**` | **163** | 26 | 6.3 | `contract` |
| `tests/e2e/**` (Python) | **83** | 16 | 5.2 | `e2e` |
| `tests/performance/**` | **1** | 1 | — | `performance` (deselected by default) |
| **Total (pytest)** | **1424** (1423 default; 1 perf deselected) | 184 | — | |
| `tests/e2e/panel/*.spec.ts` (Playwright/TS) | 13 spec files | 13 | — | not pytest-collected |
| `slow` marker (cross-cutting) | 193 | — | — | `slow` |

**Marker mechanism (load-bearing, undocumented in atom):** `tests/conftest.py`
`pytest_collection_modifyitems` applies the layer marker **automatically by directory**.
A test's directory *is* its marker — there is no per-file `pytestmark` for layer. Consequence:
a file placed in the wrong directory silently inherits the wrong layer marker and CI profile.

**What each layer tests (from `tests/AGENTS.md` + sampling):**
- **unit** — pure/near-pure islands; no `CliRunner`, subprocess, server, public stage/install,
  workspace init, network, or sleeps. Heavily parametrized (10.5 tests/file).
- **contract** — public CLI output shape, API/schema, security boundary, projection privacy,
  governance invariants. Inventory in `tests/contract/README.md` (present).
- **integration** — the main behavior layer: tmp filesystem trees, Typer `CliRunner`, service
  composition, stores, panel routes, lifecycle commands, public projection, gate behavior.
  Sub-areas: `cli/`, `features/`, `gate/`, `infrastructure/`, `panel/`, `scripts/`, and
  live-harness dirs (`claude_live/`, `codex_live/`, `pi_live/`).
- **e2e (Python)** — named journeys, with strong **SDD-gate/lease/chokepoint** coverage:
  `test_pre_commit_lease_gate`, `test_push_gate_check`, `test_two_actor_lease`,
  `test_two_process_denial`, `test_short_heartbeat_triad`, `lease_rendezvous` helper, plus
  `test_lifecycle_engine_smoke`, `test_handoff_pipeline`, `test_public_pipeline`,
  `test_ctx_inject_bind_boundary`, `test_panel`, `test_backlog_*`, `test_branch_tracking`,
  `test_server_port_registry`, `test_academy`.
- **e2e (Playwright/TS)** — `tests/e2e/panel/` 13 `.spec.ts` files covering Panel browser
  journeys (agents/kanban/ops/servers/spec-context/workflows tabs, theme switcher,
  workflow-policy editor + harness toggle, api-contracts, response-guard, tab-navigation).
- **performance** — a single test `test_lifecycle_hygiene_scan.py` (437,724-file synthetic
  scan, `MAX_SCAN_SECONDS=90`, `MAX_PEAK_BYTES=96 MiB`), `pytest.mark.performance`,
  excluded from the default profile and from the pre-push gate.

**Conftest safety architecture (undocumented in atom):**
- `_no_real_venv_in_tests` (autouse) — monkeypatches venv ensure to a fake; prevents ~20
  integration/e2e `workspace.init()` fixtures from each building a real venv (historical
  disk-exhaustion backstop).
- `_repo_root_write_guard` (autouse) — blocks accidental repo-root writes during tests.
- Protected-directory snapshot guard (autouse, function-scope) — captures and restores
  entries of protected dirs around every test.
- `tmp_path_retention_policy = "failed"` — only failed tests retain tmp trees.

**CI job split (the real one):**
- `ci.yml` jobs: `importability-smoke` (Windows/macOS), `lint` (ruff + import-linter),
  `typecheck` (mypy --strict), `unit-fast` (`-m "unit and not slow" tests/unit`),
  `contract-coverage` (`-m "unit or contract" --cov-fail-under=80 tests/unit tests/contract`),
  `unit-fast-cross` + `contract-coverage-cross` (Windows/macOS matrix), `integration`
  (`-m integration tests/integration --durations=30`), `e2e-python`
  (`-m e2e tests/e2e/features --durations=30`), and **`E2E panel (Playwright)`** — a separate
  Node job: bootstraps a panel workspace, `npm ci`, `npx playwright install chromium`,
  `npm run test:e2e` over `tests/e2e/panel/`.
- `release.yml` mirrors the pytest + Playwright jobs and adds build/approve/publish/smoke.
- **Local pre-push gate** (`features/ci_preflight/service.py`): runs lint + `pytest -q -p
  no:cacheprovider -m "not performance"` (`--ignore=tests/e2e` in quick mode). **This matches
  the atom's documented pre-push profile.**

---

## 2. Pyramid-shape verdict

**HEALTHY — classic pyramid, NOT inverted.**

By test count: unit **622** > integration **555** > contract **163** > e2e **83** >
performance **1**. Unit is the broadest layer; e2e is a thin journey cap. This is the
correct shape.

The operator's "integration-heavy at 82 vs 59" observation is a **file-count** artifact:
integration has more *files* (82) than unit (59), but unit has more *tests* (622 vs 555)
because unit files are far more parametrized (10.5 vs 6.8 tests/file). There is **no real
inversion**. The integration layer being large is appropriate — the atom explicitly names
it "the main behavior layer for dadaia-workspace," which a CLI/engine/projection product
warrants.

---

## 3. quality-assurance.md vs reality — ranked

### Stale / contradicted

| # | Sev | Claim | Reality | Note |
|---|---|---|---|---|
| S1 | LOW | contract budget "100-150" | **163** collected | Over by 13; mild drift. |
| S2 | LOW | integration budget "450-550" | **555** collected | Over by 5; marginal. |
| S3 | LOW | "collected count … expected to stay near 1350" | **1424** | +74 after 7 releases. |
| S4 | LOW | "Coverage is a diagnostic, not the default" | CI **hard-gates** `--cov-fail-under=80` on the `contract-coverage` job | Coverage IS a blocking gate at unit+contract; atom understates this. |
| S5 | INFO | `release_origin: v0.1.34`, `last_updated 2026-06-28` | active release **v0.1.41 (CLOSURE)** | 7 releases of unreviewed drift; atom should be re-validated at this closure. |

### Gaps (real architecture facts the atom omits)

| # | Sev | Missing fact |
|---|---|---|
| G1 | MEDIUM | **Auto-marker-by-directory** — `conftest.pytest_collection_modifyitems` assigns the layer marker from the directory. Load-bearing: misfiled tests get the wrong marker/CI profile silently. `tests/AGENTS.md` states it; the memory atom does not. |
| G2 | MEDIUM | **Playwright/Node panel-e2e is a SEPARATE CI job** (`E2E panel (Playwright)`, in both ci.yml and release.yml: `npm ci` + `npx playwright` + `npm run test:e2e` over 13 `tests/e2e/panel/*.spec.ts`). The atom's "CI job split" responsibility (§13) does not describe it; "Runtime State Touched" only says workflows "may run broader CI profiles." |
| G3 | MEDIUM | **`tests/e2e/node_modules` (21 MB) is physically present in the working tree** (gitignored, 0 tracked). Repo-cleanliness rule: "gitignore is not a licence to create them." Needed for local Playwright runs; tension is unacknowledged anywhere. |
| G4 | LOW | **conftest safety guards** (`_no_real_venv_in_tests`, `_repo_root_write_guard`, protected-dir snapshot guard, `tmp_path_retention_policy="failed"`) — core disk/pollution defenses absent from "Runtime State Touched." |
| G5 | LOW | **Cross-platform CI matrix** (`importability-smoke`, `unit-fast-cross`, `contract-coverage-cross` on Windows/macOS) absent from the atom's CI split. |

### §13 forbidden-history check

- No `Changelog` / `History` / `Versions` / `Histórico` heading present. **Pass.**
- **MEDIUM concern:** the **"Retained Feature Coverage"** section is written as a past-event
  narrative — "Deleted private unit matrices…", "after the collapse", "The v0.1.34
  architecture keeps…". That is closure evidence of the v0.1.34 suite collapse, not
  present-tense current truth. The atom's own No-Slop Law forbids tests that "assert
  release/task/PR history"; the memory atom should hold itself to the same standard and
  state the current per-surface layer mapping in present tense, moving the "what we deleted"
  account to `v0.1.34/CLOSURE.md`.

---

## 4. Slop / health risks

| # | Sev | Risk |
|---|---|---|
| H1 | MEDIUM | **Panel browser coverage is operationally brittle.** The Panel critical surface's only browser coverage is 13 Playwright specs that depend on a 21 MB in-tree `node_modules` and a bootstrapped panel workspace. Memory history flags recurring "stale panel E2E nav tests" and a GH-only panel job. Coverage exists but is fragile and easy to skip locally. |
| H2 | LOW | **Single performance test, narrow scope.** Only `test_lifecycle_hygiene_scan` exists; it covers the hygiene metadata scan and nothing else. Critical paths (SDD gate, lease contention, lifecycle-engine throughput, panel route latency) have **no** performance coverage. Correctly opt-in/excluded from pre-push (good — the historically load-sensitive 437k-file flake is properly quarantined), but the layer is thin by design. |
| H3 | LOW | Absence/residue-style assertions found in `tests/e2e/features/test_panel.py` ("no longer exists"-style). Verify each names a current boundary with a retirement condition per the atom's residue rule; otherwise rewrite to assert present behavior. |
| H4 | INFO | No test files are genuinely named after a version/PR/task. The 4 grep hits (`test_release_*`, `test_context_release_cmd`) name the **release feature**, not release history — not slop. |
| — | GOOD | **SDD gate / lease / chokepoint e2e coverage is strong and NOT thin** (6+ dedicated journeys + rendezvous helper). The most safety-critical surface is well covered. |
| — | GOOD | **No in-repo pytest/mypy/ruff cache pollution** observed; `node_modules` is the only artifact dir in-tree, and it is gitignored. |

---

## 5. Prioritized release-scope items (for synthesis)

Memory atoms are writable only by `product-engineer` in DEFINITION/CLOSURE (constitution
§13); all items below target that owner.

| Pri | Change | File | Acceptance criterion |
|---|---|---|---|
| P1 | Re-validate budgets against live collection (1424). Raise contract `100-150 → 100-170`, integration `450-550 → 450-560`, total estimate `~1350 → ~1425`. | `specs/memory/quality-assurance.md` (Budgets) | Every budget bracket contains the current collected count; bump `last_updated`/`release_origin` to the active release. |
| P2 | Document the **auto-marker-by-directory** mechanism. | `quality-assurance.md` (Layer Schema) | Atom states "layer markers are applied automatically by directory via `tests/conftest.py`; a file's directory IS its marker — misfiled tests get the wrong CI profile." |
| P3 | Document the **Playwright/Node panel-e2e CI job** and cross-platform matrix in the CI-split responsibility. | `quality-assurance.md` (Critical Surfaces / Runtime State Touched) | Atom names the pytest jobs + the separate `E2E panel (Playwright)` Node job (`npm run test:e2e`, `tests/e2e/panel/`) + Windows/macOS matrix. |
| P4 | Resolve/acknowledge **`tests/e2e/node_modules`** (21 MB in-tree). | `tests/AGENTS.md` + `.dadaia/states/root_exceptions.txt`-style note, or remove from tree | Either an explicit "Playwright local-run exception" is documented, or the dir is absent from the working tree (CI already runs `npm ci`). |
| P5 | Move the **v0.1.34 "collapse" history** out of memory into release evidence; restate per-surface coverage in present tense. | `quality-assurance.md` (Retained Feature Coverage) → `releases/v0.1.34/CLOSURE.md` | Atom contains no "Deleted…/after the collapse" narrative; states current layer mapping per critical surface. |
| P6 | Document **conftest safety guards** as load-bearing test-architecture state. | `quality-assurance.md` (Runtime State Touched) | Atom lists `_no_real_venv_in_tests`, `_repo_root_write_guard`, snapshot guard, `tmp_path_retention_policy="failed"`. |
| P7 | Reconcile the **coverage statement** with the CI 80% gate. | `quality-assurance.md` (Profiles) | Atom acknowledges `--cov-fail-under=80` is a blocking CI gate on the unit+contract job (coverage is diagnostic locally, gated in CI). |

---

## Appendix — commands run

```
pytest --collect-only -q -p no:cacheprovider                 → 1423/1424 (1 perf deselected)
pytest --collect-only -q -p no:cacheprovider -m <marker>     → unit 622, contract 163,
                                                                integration 555, e2e 83,
                                                                slow 193, performance 1
grep -rniE 'playwright|npx|npm' .github/workflows/           → E2E panel job in ci.yml+release.yml
git log -1 -- specs/memory/quality-assurance.md              → 740a30af 2026-06-27 collapse
```
