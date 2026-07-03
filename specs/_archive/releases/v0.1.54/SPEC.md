# SPEC — v0.1.54 — Import Boundaries

**Status:** Aprovado
**Branch:** `feature/v0.1.54` (base: `d48ef6db`, v0.1.53 closure — the orchestrator branches after `Aprovado`)
**Origin:** R6 of the operator-approved 12-release plan (grill 2026-07-02); first release
of the operator's R6→R8 continuation mandate (2026-07-03). Definition-time inspection
verified by the orchestrator 2026-07-03 (GRILL INSPECTION DOSSIER — cited as inspection
facts). **Dual definition review 2026-07-03: software-architect REJECT (FR1 type
relocation + lean port + policy_resolver-needs-no-port; subject_registry cli_anchors seam;
FR2 seam split w/ re-export; exact 13-edge cap arithmetic; FR6 infra-home for hot-path;
strike features-no-hooks; FR7 AST guard; container.py W1-W4 sharing; FR4 fail-closed
resolver) + qa-engineer REJECT (zero-edit test importers via re-export; per-family cap
assertions; FR6 forced-repoint partition; exact AC-7 sabotage targets; CI lint-job naming;
"5 chains" clarification) — ALL amendments folded.**
**Consumes:** `import-boundary-enforcement`, `features-import-infrastructure-direct-debt`,
`pid-probe-seam-consolidation`.

## 1. Problem

The import-linter layering law is **defined but unenforced and partly red**. Verified at
definition (2026-07-03):

1. **Contracts red, CI-unwired.** `lint-imports` reports **6 contracts, 4 kept, 2
   broken**, and `lint-imports` appears **nowhere** in `.github/workflows/*.yml` nor in
   `features/ci_preflight/` — the contracts are entirely unenforced. The two broken
   contracts are `features-no-infrastructure` and `features-no-subprocess`, red on **5
   chains**:
   - `features.backlog.subject_registry -> cli.main` (l.391, a local
     `from dadaia_workspace.cli.main import app`) — breaks BOTH broken contracts
     transitively (`cli.main -> infrastructure.bug_reporter` l.36; and
     `cli.main -> cli.commands.ci -> subprocess` l.7).
   - `features.lifecycle.policy_resolver -> infrastructure.json_workflow_model_policy_store` (l.48).
   - `features.lifecycle.policy_doctor -> infrastructure.json_workflow_model_policy_store` (l.68).
   - `features.panel.views.workflow_policy -> infrastructure.json_workflow_model_policy_store` (l.55).

   > **§1.1 note (QA A6) — "5 chains" = 5 contract×edge pairs from 4 distinct edges.**
   > `subject_registry → cli.main` breaks BOTH broken contracts (2 pairs from 1 edge); the
   > 3 `json_workflow_model_policy_store` edges each break `features-no-infrastructure` (3
   > pairs). 2 + 3 = 5 contract×edge pairs across 4 distinct import edges. FR1 fixes all 4
   > edges.
2. **`workflows ↔ lifecycle` import cycle (bidirectional).**
   `workflows/dadaia_catalog.py` imports lifecycle symbols at l.49-69 (`model_profiles`,
   `pipeline.implementation_ladder`, the `policy_resolver` catalog types, and the
   `_SEQUENCE` constants of `workflows/{audit,backlog_definition,bug_report,`
   `release_definition,research}`); `lifecycle/policy_doctor.py:405` lazily imports
   `workflows.dadaia_catalog.governed_workflow_catalog` back. Confirmed bidirectional.
3. **Cross-feature erosion, unguarded.** At the module-pair granularity import-linter
   counts, the tree has **21** cross-feature module-pair edges TODAY (the A-5 audit's "8
   relationships" understated it; the silent-erosion thesis is re-proven). No contract
   forbids features importing features. After FR2's cycle-break the surviving set is
   exactly **13** module-pair edges (enumerated in FR3).
4. **`_build_pid_probe` is a de-facto shared seam under a private hook name.** THREE
   private builders exist — `hooks/sdd_gate.py:38` (the real one; lazily imports the
   `OsProcessProbe` adapter), `container.py:237` (wrapper), `cli/commands/specs.py:69`
   (wrapper) — plus consumers `cli/commands/lock.py:12`
   (`from hooks.sdd_gate import _build_pid_probe`), `cli/commands/context.py:514`
   (`container._build_pid_probe`), and `features/spec_context/lease._main_pid_probe`
   (l.883-894 — a **dynamic `importlib.import_module("dadaia_workspace.hooks.sdd_gate")`**
   lookup to `sdd_gate._build_pid_probe`; deliberately dynamic so the static graph carries
   zero `features → hooks`/`features → infrastructure` edge — the "uncontracted upward
   import" the dossier names).
5. **`features → infrastructure` DI debt (2 remaining ignores).**
   `features.workflows.service -> infrastructure.markdown_workflow_store` and
   `features.agents.reader -> infrastructure.markdown_agent_store` are still in
   `setup.cfg`'s `ignore_imports`, despite the `WorkflowProvider`/`AgentsProvider` core
   ports already existing (`container.py:474` already wires `FileSystemAgentsProvider`) —
   the fix is completing DI wiring, not creating ports. (The entry's third edge,
   `panel.service -> workflow_launcher_adapter`, was **consumed by v0.1.53** — not redone.)
6. **`core/` file-I/O purity is undecided.** `core/specs_version.py` does write-I/O
   (`read_text` l.63/l.80, `write_text` l.86/l.95); `core/specs_backup.py` does write-I/O
   (`shutil.copytree`, `mkdir`); `core/specs_resolver.py` + `core/workspace_resolver.py`
   walk the filesystem. `architecture.md` names all four "authorized exceptions pending the
   `import-boundary-enforcement` backlog". The `core-no-upper-layers` and
   `core-no-os-primitives` contracts are **KEPT** — this is a file-I/O purity decision, not
   a broken contract.

**Stale-reference inspection contradiction (recorded, corrected in this release):**
`setup.cfg` line 112 comment says the ignore-edge cap is "still 17", contradicting the
header (l.27, "Current count = 15") and the cap test (`_RECORDED_IGNORE_EDGE_CAP = 15`).
`specs/memory/architecture.md` line 139 likewise says "(17 edges)". Both are stale — a
v0.1.53 collateral miss when the cap was lowered 17→15 (the test-/comment-side class the
v0.1.53 CLOSURE Drifts flagged). The comment is corrected in-release (FR3/FR5 touch
`setup.cfg`); the memory line is corrected at CLOSURE.

## 2. Goals

1. The 5 red chains (4 edges) are **fixed** — `features-no-infrastructure` and
   `features-no-subprocess` become GREEN (0 broken among the 6 existing contracts).
2. The `workflows ↔ lifecycle` cycle is **broken** and pinned by a directed contract, so
   later structure (R7 decomposition, R8 verb governance, R9 injection canon) lands under
   enforcement.
3. Cross-feature erosion is **stopped**: a `features-no-cross-feature` contract documents
   the surviving 13 module-pair edges as ignores; no new cross-feature edge can be added
   silently.
4. `lint-imports` is **CI-wired** — in the GitHub Actions `Lint (ruff)` job AND in
   `dadaia ci preflight` (so the pre-push hook enforces it) — wiring an already-green state.
5. The two `markdown_*_store` `ignore_imports` edges are **removed** via DI completion; the
   ignore-cap is re-pinned exactly (26).
6. `_build_pid_probe` is **one public composition-root builder** in the infrastructure
   adapter; the private hook seam is gone; the no-steal invariant is preserved.
7. `core/` file-I/O purity is **dispositioned** with an AST-based ratchet guard.

## 3. Functional requirements

### FR1 — Red-chain remediation (green the 2 broken contracts)

**Architecture (dual-review A1 + A2). Two mechanisms, not one port for all:**

**(a) `json_workflow_model_policy_store` — relocate types, port only the store behavior.**
- **Relocate the pure data types** `WorkflowModelPolicyOverlay`, `WorkflowModelPolicyStoreError`,
  and `DEFAULT_CONTEXT` from `infrastructure/json_workflow_model_policy_store.py` to
  **`core/models/workflow_execution.py`**. **No re-export shim.** Repoint every importer to
  the new core home, **including `container.py:33` (the `TYPE_CHECKING` import)**.
- `features.lifecycle.policy_resolver` imported the store module **only for those types** —
  after relocation it imports them from `core/models` (a legal `features → core` edge) and
  **needs no port** (its red chain is fixed by the relocation, not by injection).
- Add a **lean Protocol** `core/protocols/workflow_model_policy_store.py` with **exactly**
  `load` / `parse` / `save`. Inject the concrete `JsonWorkflowModelPolicyStore` via
  `container.build_workflow_model_policy_store` into **`policy_doctor` and
  `panel.views.workflow_policy` ONLY** (the two that use the store's I/O behavior). Remove
  `policy_doctor`'s default store construction at **l.288**; the CLI caller
  **`cli/commands/lifecycle.py:1285`** injects `container.build_workflow_model_policy_store`.

**(b) `subject_registry → cli.main` — derive `cli_anchors` at the composition boundary.**
- Move `_derive_cli_anchors` **out of the feature** into a **`cli/`-composition helper**;
  derive a `cli_anchors` `frozenset` at each composition boundary and **thread it into**
  `build_registry`, `run_backlog_doctor`, and `ContextSelector.sel_backlog_index`.
- Enumerate and update the **six `build_registry` call sites**: `container.py:1069`,
  `container.py:1139`, `newartifacts.py:186`, `newartifacts.py:281`, `backlog/doctor.py:240`,
  `context_selector.py:428`. `subject_registry` keeps only a `TYPE_CHECKING` `typer` import
  (no runtime `cli.main` edge).

Outcome: the existing 6 contracts are all KEPT. FR1 changes **no** `ignore_imports` and
**no** cap value (red chains are un-ignored violations, fixed by removing the imports).

### FR2 — Break the `workflows ↔ lifecycle` cycle (the seam — dual-review R-1)

- **Create the seam `features/lifecycle/governed_catalog.py`** containing:
  `DadaiaWorkflowStepDTO`, the purpose/display dicts, every `_*_steps` builder, the
  SVG-free `_all_workflows`, `_governed_step`, `governed_workflow_catalog`,
  `_assert_catalog_defaults_resolve`, and the availability constants. It imports **only
  lifecycle internals + core** (no `features/workflows` import).
- **`features/workflows/dadaia_catalog.py` keeps** `DadaiaWorkflowDTO`, `_build_workflow`,
  `_steps_to_stage_dtos`, `_node_meta_for_steps`, `list_dadaia_workflows`,
  `get_dadaia_workflow`, and imports **EXACTLY ONE** lifecycle module — `governed_catalog`.
  That **genuine** import (not a gratuitous shim) **re-exports `governed_workflow_catalog`
  from the stable public path `features.workflows.dadaia_catalog`**, so the **9 test
  importers need ZERO edits** (QA A2 satisfied without a shim — stated explicitly).
- **Repoints:** production **`container.py:735`** points at the canonical lifecycle home
  (`lifecycle.governed_catalog`); **`policy_doctor.py:405`** imports the catalog
  **intra-lifecycle** (`from dadaia_workspace.features.lifecycle.governed_catalog import
  governed_workflow_catalog`), removing the `lifecycle → workflows` edge.
- Add a **NEW** directed `forbidden` contract `lifecycle-no-workflows`
  (`dadaia_workspace.features.lifecycle` ⊬ `dadaia_workspace.features.workflows`) — the
  falsifiable cycle-break guard. **RED-first:** it FAILS today (QA-verified: the contract
  builds and is RED); note pre-FR1 import-linter reports the shortest chain (the
  transitive `context_selector → subject_registry → cli.main → … → features.workflows`) —
  the direct `policy_doctor → dadaia_catalog` edge becomes the visible violation once
  FR1 (W1) removes `subject_registry → cli.main`; W1→W2 ordering means the FR2 RED
  commit correctly captures the direct edge. GREEN only after the seam extraction.
- **Golden byte-identical test** on `list_dadaia_workflows()` output and the diagram SVG
  before/after (architect A4) — the relocation is behavior-preserving.

### FR3 — `features-no-cross-feature` contract (13 documented edges — dual-review R-2)

- Add a **NEW** `independence` contract `features-no-cross-feature` — import-linter
  2.11 rejects a self-referential `forbidden` (`features ⊬ features`) with "Modules
  have shared descendants"; `independence` is the canonical mechanism for mutual
  sibling independence and accepts `ignore_imports` (both QA-verified by isolated
  probe: `independence` with the ignores returns `1 kept, 0 broken`; with no ignores
  it is BROKEN — RED-first preserved). List **every** `dadaia_workspace.features.<pkg>`
  sub-package under `modules =` (so a new edge from any currently-clean feature is
  also caught), with the **post-FR2** cross-feature edge list as documented
  `ignore_imports` — the **exact 13 module-pair edges**, full `dadaia_workspace.`
  prefixes, **no wildcards**, each with a rationale comment:
  1. `...features.lifecycle.report_workflow -> ...features.reports_validation.service`
  2. `...features.lifecycle.context_selector -> ...features.backlog.preview`
  3. `...features.lifecycle.context_selector -> ...features.backlog.subject_registry`
  4. `...features.lifecycle.workflows.backlog_definition -> ...features.backlog.classifier`
  5. `...features.lifecycle.workflows.backlog_definition -> ...features.backlog.subject_registry`
  6. `...features.panel.views.workflow_policy -> ...features.lifecycle.model_profiles`
  7. `...features.panel.views.workflow_policy -> ...features.lifecycle.fragments.loader`
  8. `...features.panel.views.workflow_policy -> ...features.lifecycle.policy_resolver`
  9. `...features.panel.views.workflows -> ...features.lifecycle.model_profiles`
  10. `...features.panel.views.workflows -> ...features.workflows.dadaia_catalog`
  11. `...features.specs.doctor -> ...features.spec_context.lease`
  12. `...features.specs.doctor -> ...features.spec_context.session_identity`
  13. `...features.workflows.dadaia_catalog -> ...features.lifecycle.governed_catalog`
- **RED-first:** before the ignores are added, the contract FAILS on the real cross-feature
  edges (proving it catches them).
- Update `tests/contract/test_import_linter_ignore_cap.py`: the recorded cap and its
  three-family breakdown (see FR5/AC-5), and broaden the docstring of
  `test_every_ignored_edge_is_a_features_layering_exception` — sanctioned exceptions now
  include cross-feature composition debt, not only `features → adapter` reach (every ignored
  edge still has a `dadaia_workspace.features` **source**, so the existing assertion holds).

### FR4 — CI wiring (lands LAST — wires an already-green state — dual-review A5/A10)

- Add a step to the existing **`Lint (ruff)`** job in `.github/workflows/ci.yml` (l.62-63):
  `poetry run lint-imports --config setup.cfg --no-cache` — **no extra install** (the job
  already runs `poetry install --with dev`, which provides import-linter). Fails the job on
  any broken contract; `--no-cache` respects the repo-cleanliness law and
  `test_import_linter_cache_hygiene.py`.
- Add a `lint-imports --no-cache` check to `features/ci_preflight/service.py` (`checks_for()`,
  executable resolved via the existing `_resolve_tool` seam) so the pre-push hook's
  `dadaia ci preflight` enforces it alongside ruff/mypy/pytest. **`_resolve_tool` must fail
  closed** when `lint-imports` is absent from the pre-push env (matching the CI-gate
  resolver posture) — a missing tool is a hard error, never a silent skip.
- Add a **preflight-wiring contract test** asserting the preflight check set contains a
  `lint-imports --no-cache` invocation **and** covers the `_resolve_tool` fail-closed
  behavior when the tool is absent. This wave lands **after** the green tree so the first
  enforced run is green.

### FR5 — `features → infrastructure` direct-debt DI completion

- Complete DI for the two remaining `markdown_*_store` edges: inject `WorkflowProvider`
  into `WorkflowsService` and `AgentsProvider` into `read_canonical_agents` via
  `container.py` (the `agents_provider=FileSystemAgentsProvider()` wiring already exists at
  `container.py:474`), and delete the direct
  `from dadaia_workspace.infrastructure.markdown_workflow_store import ...` /
  `...markdown_agent_store import ...` imports.
- Remove the two corresponding `ignore_imports` edges from `setup.cfg`'s
  `features-no-infrastructure` contract and **lower the cap in the same commit**.
- The panel launcher edge is **consumed-elsewhere** (v0.1.53) — no work.
- Out of scope (SEPARATE tracked debt, non-goals): the 4 `subprocess_runner` lazy-fallback
  edges and the 4 ADR-1 lock/telemetry edges.

### FR6 — `_build_pid_probe` single public builder (infra home — dual-review R-3/A8)

- **Home: `infrastructure/process_probe_adapter.build_pid_probe()`** — a public factory in
  the adapter module, **NOT `container.build_pid_probe`**: the hook (`sdd_gate`, PreToolUse
  hot path) and `lease._main` (lease side-door hot path) must reach the builder without
  importing the heavy composition root.
- **Repoint the consumers, delete the private wrappers:** `hooks/sdd_gate.py` (calls the
  infra factory — `hooks → infrastructure` is the existing declared exception);
  **delete** `container.py:237` and `cli/commands/specs.py:69` wrappers;
  `cli/commands/lock.py:12` repoints `_build_pid_probe` to the infra factory (keep
  `_active_field`); `cli/commands/context.py:514` calls the infra factory;
  `features/spec_context/lease._main_pid_probe` (l.883-894) **retargets its dynamic
  `importlib.import_module` lookup** from `dadaia_workspace.hooks.sdd_gate` to
  `dadaia_workspace.infrastructure.process_probe_adapter` and its `build_pid_probe` — it
  **stays dynamic**, so the static graph keeps **zero** `features → infrastructure` edge and
  **no new ignore** is added (the cap-26 arithmetic holds).
- **Grep acceptance (extended — architect A8):** zero occurrences, **including under
  `tests/`**, of (i) `hooks.sdd_gate._build_pid_probe`, (ii)
  `import_module("dadaia_workspace.hooks.sdd_gate")` for the probe, (iii) `sdd_gate._build_pid_probe`
  attribute access, and (iv) bare `_build_pid_probe` outside `hooks/sdd_gate.py`. **ADD a
  positive unit test** that `lease._main_pid_probe` resolves the new public builder and
  returns a live probe.
- **Invariants preserved (non-negotiable):** default `None ⇒ TTL-only degradation`; the
  no-steal invariant unchanged.
- **FROZEN-SUITE partition (QA A1, adapted by R-3) — mandatory:**
  - **Frozen, adjudication required:** `tests/unit/cli/test_lock_steal.py:63` +
    `test_lease_main_probe.py` — symbol-forced repoints; QA-gate adjudication with byte-level
    no-steal invariant evidence (v0.1.53 precedent, `specs/memory/quality-assurance.md`).
  - **Frozen, invariant-only (no symbol repoint expected):** `test_two_actor_lease.py` +
    `test_doctor_lock_gc.py` — confirm untouched.
  - **Non-frozen forced repoints:** `tests/unit/cli/commands/test_context_release_cmd.py:61`
    (monkeypatch retargets the infra factory **as bound in `cli/commands/context.py`'s module
    namespace** post-repoint) + `tests/unit/test_container.py:126` (comment update).
- **No `features-no-hooks` contract (dual-review R-4).** A real `features → hooks` static
  edge exists at `slop_scan.py:23`, so a `features-no-hooks` contract would be RED and force
  a new ignore — against the ratchet theme. The contract is **struck** (the SPEC's earlier
  "0 ignores" claim is withdrawn); decoupling `slop_scan` from `hooks` is **re-scoped to a
  future release**.

### FR7 — `core/` file-I/O purity disposition (AST guard — architect A9)

- **Decision: GUARD (an AST-based walker), not relocation.** Relocating `specs_version`
  (canon consumers) or `specs_backup` (migrate consumers) out of `core/` is structural churn
  belonging to R7. Add a contract test (`tests/contract/test_core_file_io_purity.py`) whose
  **AST-based walker over `core/*.py`** flags any of `open`, `Path.read_text`,
  `Path.write_text`, `Path.mkdir`, `Path.exists`, `Path.glob`, `Path.iterdir`,
  `Path.rglob`, `shutil.copy*`, `shutil.copytree`, `shutil.move` outside the **authorized
  set** `{specs_backup, specs_version, specs_resolver, workspace_resolver}`. `platform.py`
  stays covered by the separate `sys`-platform exception note (it does no file-I/O).
- The `core-no-upper-layers` and `core-no-os-primitives` import-linter contracts are
  unchanged (KEPT). At CLOSURE, `architecture.md` drops the "pending the
  `import-boundary-enforcement` backlog" qualifier for the named exceptions.

## 4. Non-goals

- The **4 `subprocess_runner` lazy-fallback** and **4 ADR-1 lock/telemetry**
  `ignore_imports` edges — SEPARATE tracked debt.
- **Relocating** any `core/` file-I/O module out of `core/` (FR7 chooses the AST guard).
- **A `features-no-hooks` contract** and the `slop_scan → hooks` decoupling — re-scoped
  (R-4).
- **R7 architecture decomposition** (SpecsDoctor / `panel/api.py` splits, `reports_*` merge)
  — lands under the now-enforced contracts next, not here.
- Fixing (as opposed to documenting) any surviving cross-feature edge — R7/R8/R9 work.
- No new deprecations; no memory changes outside the CLOSURE list in §8.

## 5. Acceptance criteria

- **AC-1 (contracts green — "6+N kept, 0 broken", per-chain):** `lint-imports --no-cache`
  reports `8 kept, 0 broken` (N = 2 new contracts: `lifecycle-no-workflows`,
  `features-no-cross-feature`). Per-chain: each of the 5 red chains / 4 edges is verified
  GONE — `subject_registry` no longer imports `cli.main`;
  `policy_resolver`/`policy_doctor`/`panel.views.workflow_policy` no longer import
  `infrastructure.json_workflow_model_policy_store`. `features-no-infrastructure` and
  `features-no-subprocess` are KEPT.
- **AC-2 (cycle broken, falsifiable):** the `lifecycle-no-workflows` contract is GREEN;
  `governed_workflow_catalog` resolves from `features.lifecycle.governed_catalog` (and stays
  re-exported from `features.workflows.dadaia_catalog` — 9 test importers unchanged); the
  golden byte-identical test on `list_dadaia_workflows()` + diagram SVG passes before/after.
- **AC-3 (RED-first per new contract):** for `lifecycle-no-workflows` (FR2),
  `features-no-cross-feature` (FR3), and the `core/` AST guard (FR7), a RED commit precedes
  the fix commit — `lint-imports`/the test FAILS against the pre-fix tree (RED tail captured
  on the task line; RED ancestor verifiable in branch history).
- **AC-4 (pid-probe single builder + extended grep + invariant):** exactly one public
  builder `infrastructure.process_probe_adapter.build_pid_probe`; the **extended grep** (A8:
  the four forms in FR6, **including `tests/`**) returns **zero** hits outside
  `hooks/sdd_gate.py`; the **positive unit test** proves `lease._main_pid_probe` resolves the
  new builder and returns a live probe; the no-steal invariant is byte-identical (frozen-suite
  adjudication PASS handoff cited); `None ⇒ TTL-only` degrade preserved (unit test).
- **AC-5 (ignore-cap equation + per-family — removed edges → new cap):**
  `15 (start) + 13 (FR3 cross-feature) − 2 (FR5 markdown) = 26`.
  `_RECORDED_IGNORE_EDGE_CAP = 26`; the cap test verifies **both** the total (`== 26`,
  `test_recorded_cap_is_not_stale_above_reality`) **and** the per-family split via
  **per-contract-section assertions** — `features-no-infrastructure = 9`,
  `features-no-subprocess = 4`, `features-no-cross-feature = 13`. The exact 13-edge set is
  pinned at the FR3 RED commit. The stale `setup.cfg` "(still 17)" comment is corrected in
  the same edit.
- **AC-6 (full gates incl. public doctor):** `ruff format --check`, `ruff check`,
  `mypy --strict`, and the full `pytest` (unpiped, real exit) are green locally and in CI;
  `lint-imports --no-cache` is GREEN in the `Lint (ruff)` CI job AND inside
  `dadaia ci preflight`; `dadaia specs doctor` and `dadaia public doctor` exit 0.
- **AC-7 (mutation-sanity — exact sabotage targets, QA A4):** each captured on its task
  line, then reverted —
  (a) plant `from dadaia_workspace.features.workflows import dadaia_catalog` atop
  `features/lifecycle/policy_doctor.py` ⇒ `lifecycle-no-workflows` FAILS;
  (b) plant `from dadaia_workspace.features.spec_context import lease` atop
  `features/backlog/subject_registry.py` ⇒ `features-no-cross-feature` FAILS;
  (c) create `dadaia_workspace/core/_io_sabotage_probe.py` with `Path(...).read_text()` ⇒ the
  core-purity AST guard FAILS;
  (d) delete the `lint-imports` Check from `checks_for()` in
  `features/ci_preflight/service.py` ⇒ the preflight-wiring test FAILS.
- **AC-8 (surviving/dead behavior ledger, per wave):** each wave records a two-column ledger
  on its task line — surviving behaviors (with the test now asserting them) vs
  intentionally-changed/removed. Every deletion/rename/repoint grep **includes `tests/`**
  (the v0.1.53 CLOSURE lesson: two collateral misses last release were test-side).

## 6. Consumed backlog

| Backlog entry | Priority | Intents consumed → FR | Note |
|---|---|---|---|
| `import-boundary-enforcement` | HIGH | red chains → FR1; cycle break → FR2; cross-feature contract → FR3; CI wiring → FR4; core-purity → FR7 | Anchor `policy_resolver#WorkflowExecutionPolicyResolver` SURVIVES (rewired, not deleted). |
| `features-import-infrastructure-direct-debt` | LOW | `markdown_workflow_store` + `markdown_agent_store` DI → FR5 | Third edge `panel.service → workflow_launcher_adapter` **CONSUMED-ELSEWHERE by v0.1.53** (launcher chain deleted) — not redone. |
| `pid-probe-seam-consolidation` | LOW | single public builder (infra home) → FR6 | Anchors `hooks/sdd_gate.py#_build_pid_probe` **and** `container.py#_build_pid_probe` are **KILLED** (deleted) by this release ⇒ consumed-backlog archival is a **single atomic commit AT SHIP** (R4/R5 process law). |

**Archival-at-ship (R4/R5 process law, applies because this release kills its own anchors):**
no implementation-wave commit stages any `specs/backlog/**` path. The three consumed entries
are moved to `specs/_archive/<release-id>/consumed-backlog/` with a `consumed_backlog.json`
ledger in **one atomic commit at SHIP**, before the single push, after all pid-probe anchors
are killed — so `dadaia backlog doctor` never sees a live entry referencing a dead anchor.

## 7. Risks

- **Frozen no-steal suite (FR6).** Symbol-forced repoints of `test_lock_steal.py:63` +
  `test_lease_main_probe.py` require QA adjudication with byte-level invariant evidence; the
  other two frozen tests must stay untouched (invariant-only). A naive repoint that silently
  changes an assertion is the exact v0.1.53-class regression to avoid.
- **Type relocation ripple (FR1a).** Relocating `WorkflowModelPolicyOverlay` /
  `WorkflowModelPolicyStoreError` / `DEFAULT_CONTEXT` to `core/models` with **no shim**
  requires repointing **every** importer, incl. `container.py:33` `TYPE_CHECKING` and
  `cli/commands/lifecycle.py:1285` — a missed importer is a mypy/import error caught by AC-6.
- **`cli_anchors` threading (FR1b).** All six `build_registry` sites must pass the derived
  `frozenset`; a missed site leaves `subject_registry` deriving anchors itself (the removed
  behavior) — the per-chain grep + AC-6 catch it.
- **Cap-equation ordering.** FR3 (+13) and FR5 (−2) both edit `setup.cfg` + the cap test;
  `setup.cfg` is shared (sequential). Each commit re-pins the cap to match live reality
  (`test_recorded_cap_is_not_stale_above_reality`): W2 → 28, W3 → 26.
- **CI-first-run redness (FR4).** FR4 lands LAST; the wave order guarantees an already-green
  tree before wiring, so the first enforced CI run passes.
- **Stale-reference collateral.** `setup.cfg` "(still 17)" and `architecture.md` "(17
  edges)" are stale; corrected in-release (comment) and at CLOSURE (memory) → 26.

## 8. Memory files affected at closure

- `specs/memory/architecture.md` — update **Enforcement (actual state)**: `lint-imports` now
  CI-wired (`Lint (ruff)` job + preflight); the `lifecycle-no-workflows` +
  `features-no-cross-feature` contracts; **ignore-cap corrected to 26** with the three-family
  breakdown (9/4/13) — fixes the stale "17 edges"; `json_workflow_model_policy_store` types now
  in `core/models` + a lean core port (policy_resolver needs none); the single
  `infrastructure.process_probe_adapter.build_pid_probe` seam; `core/` file-I/O
  authorized-exception set now pinned by an AST guard — drop the "pending backlog" qualifier.
  Atomic (no changelog).
- `specs/memory/quality-assurance.md` — record the FR6 frozen-suite adjudication outcome
  (v0.1.53 precedent), covering the two forced-repoint frozen tests.
- `specs/memory/tech-stack.md` — **no change expected** (import-linter already approved);
  confirmed or noted at CLOSURE.
- No product-feature atom changes (internal architecture; no user-facing surface).
