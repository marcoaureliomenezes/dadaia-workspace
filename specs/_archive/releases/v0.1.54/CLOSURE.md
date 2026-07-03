# Closure: Release — v0.1.54 — Import Boundaries

> **Status:** Aprovado
> **Release ID:** v0.1.54
> **Owner:** product-engineer
> **Closed:** 2026-07-03
> **Branch:** `feature/v0.1.54` · **Base:** `d48ef6db` (v0.1.53 closure) · **Merged:** `aeaa3c66` (PR #97, squash of `feature/v0.1.54`) · **Closure branch:** `chore/v0.1.54-closure`
> **Ship gates:** qa-engineer **APPROVE** (10/10) · security-reviewer **APPROVED** (r1 `338fadfa` feature push; the closure push takes its own verdict) · CI 38 checks, 0 failures.

## Summary

v0.1.54 is R6 of the operator's R6→R8 continuation mandate — the release that turns the
import-linter layering law from *defined-but-unenforced-and-partly-red* into a green,
CI-enforced, ratcheted contract set, so every later structural refactor (R7 decomposition,
R8 verb governance, R9 injection canon) lands under enforcement. The five red import
chains (four edges) are gone, both previously-broken contracts are KEPT, and two new
contracts pin the structure: a directed `lifecycle-no-workflows` guard that breaks the
`workflows ↔ lifecycle` cycle, and a `features-no-cross-feature` independence contract that
freezes the surviving cross-feature surface as thirteen documented module-pair ignores so
no new edge can be added silently. `lint-imports` now runs in the GitHub `Lint (ruff)` job
**and** inside `dadaia ci preflight` with a fail-closed tool resolver, so the pre-push hook
enforces the contracts on every push. The `features → infrastructure` direct-import debt is
completed via dependency injection (the two `markdown_*_store` edges removed), the
`_build_pid_probe` private hook seam is collapsed into one public
`infrastructure.process_probe_adapter.build_pid_probe` builder with the no-steal invariant
preserved, and `core/` file-I/O purity is dispositioned as an AST ratchet guard over four
authorized modules. The change is behavior-preserving throughout — the governed-catalog
relocation is proven byte-identical by a golden test, and the frozen no-steal suite is
honored (adjudicated at the QA ship gate). This CLOSURE records the enforcement-state truth
into memory, corrects the stale "17 edges" claim to the live cap of 26 (9 infra / 4
subprocess / 13 cross-feature), and dispositions the three consumed backlog entries.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-54-01 | W0 definition (SPEC/PLAN/TASKS from the 2026-07-03 inspection dossier; dual definition review software-architect REJECT + qa-engineer REJECT → all amendments folded → `Aprovado`) | definition commit on `feature/v0.1.54` |
| T-54-10 | W1 FR1 — red-chain remediation: relocate `json_wmp_store` data types to `core/models/workflow_execution.py` + lean `load/parse/save` port injected into `policy_doctor` + `panel.views.workflow_policy`; `cli_anchors` composition seam (`cli/anchors.py`) threaded across the six `build_registry` sites | `2c304dbb` (reservation) + FR1 rewire |
| T-54-11 | W2 FR2 + FR3 — `governed_catalog` seam breaks the cycle (`lifecycle-no-workflows` contract, RED-first) + golden byte-identical test; `features-no-cross-feature` independence contract with the exact 13 ignores (RED-first); cap → 28 | RED `f3a968a0` → fix `05578415` · RED `cd852932` → fix `60e43c09` |
| T-54-12 | W3 FR5 + FR7 — `WorkflowProvider`/`AgentsProvider` DI (2 `markdown_*_store` edges removed, cap 28 → 26, stale "(still 17)" comment corrected); core file-I/O AST ratchet guard (RED-first) | `56a51148` (FR5) · `735950e1` (FR7) |
| T-54-13 | W4 FR6 — one public `infrastructure.process_probe_adapter.build_pid_probe`; 6 sites repointed (lease stays dynamic); 3 private wrappers deleted; extended grep all-zero; positive `lease._main_pid_probe` live-probe test in a new sibling file; frozen-suite partition honored | `d5e21494` (feat) · `1a9a0fd2` (test) |
| T-54-20 | W5 FR4 CI wiring + gates + ship — ci.yml `lint-imports` step; preflight 5th check fail-closed; wiring contract test (AC-7(d)); consumed-backlog archival at SHIP; QA ship gate APPROVE 10/10; security push gate; push; PR #97; merge | FR4 `ff883f99` · archival `d1f7e988` · merge `aeaa3c66` |
| T-54-30 | W6 closure — this CLOSURE.md + memory truth updates (`architecture.md` enforcement-state + "17 edges" → 26; `quality-assurance.md` FR6 frozen-suite precedent) + candidates R6 row shipped + disposition sweep | (this commit) + `dea098bc` (stale-narrative retirement) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-1 contracts green (per-chain) | `lint-imports --config setup.cfg --no-cache` | `8 kept, 0 broken`; the 4 red edges verified GONE (`subject_registry ⊬ cli.main`; `policy_resolver`/`policy_doctor`/`panel.views.workflow_policy` ⊬ `infrastructure.json_workflow_model_policy_store`) — QA ship gate |
| AC-6 full suite green (unpiped, real exit) | `pytest tests/` (no pipe) | `4333 passed, 17 skipped, exit 0` — QA ship-gate handoff `2026-07-03T171013Z` |
| AC-6 format + lint + types clean | `ruff format --check` · `ruff check --no-cache` · `mypy --strict dadaia_workspace` (288 files) | all exit 0 — QA ship gate |
| AC-6 SDD + projection doctors | `dadaia specs doctor` · `dadaia public doctor` | specs doctor exit 0 (12 pre-existing SPEC-DOC-031 WARNs, dispositioned at closure); `[ok] public-privacy`, exit 0 — W5 `ff883f99` |
| AC-6 preflight enforces lint-imports | `dadaia ci preflight` | `Running 5 preflight check(s)… [PASS] ruff format --check / ruff check / mypy --strict / lint-imports / pytest` → exit 0; `_resolve_tool` fail-closed when the tool is absent — W5 `ff883f99` |
| AC-5 ignore-cap equation + per-family | `pytest tests/contract/test_import_linter_ignore_cap.py` | `_RECORDED_IGNORE_EDGE_CAP = 26` = `15 + 13 − 2`; per-family self-counted infra **9** / subprocess **4** / cross-feature **13**; `test_recorded_cap_is_not_stale_above_reality` GREEN — W3 `56a51148` |
| AC-3 RED-first per new contract | branch-history RED ancestor + captured tail | `lifecycle-no-workflows` RED `f3a968a0` → GREEN `05578415`; `features-no-cross-feature` RED `cd852932` → GREEN `60e43c09`; core AST guard RED (AC-7(c) plant) → GREEN `735950e1` — RED ancestry genuine ×3, QA-verified |
| AC-2 golden byte-identical | `pytest tests/unit/features/workflows/test_dadaia_catalog_golden.py` | `list_dadaia_workflows()` output + all 7 diagram SVGs (30464 SVG bytes) byte-identical before/after the seam split — 101 KB fixture `_golden/dadaia_catalog_v0154.json` — W2 |
| AC-7 mutation-sanity ×4 (sabotage → FAIL → revert) | one-line plant per new contract/test | (a) `lifecycle-no-workflows` FAILED on planted `policy_doctor → dadaia_catalog`; (b) `features-no-cross-feature` FAILED on planted `subject_registry → spec_context.lease`; (c) core AST guard FAILED on `_io_sabotage_probe.py`; (d) preflight-wiring test FAILED on deleted `lint-imports` Check — all reverted, zero residue — QA gate |
| AC-4 pid-probe single builder + extended grep | grep (incl. `tests/`) for the 4 forbidden forms | zero hits of `hooks.sdd_gate._build_pid_probe`, `import_module("…hooks.sdd_gate")` for the probe, `sdd_gate._build_pid_probe` attr access, and bare `_build_pid_probe` outside `hooks/sdd_gate.py` — the private name is extinct — W4 `d5e21494` |
| AC-4 positive lease probe test | `pytest tests/unit/features/spec_context/test_lease_pid_probe_public_builder.py` | 4 tests: resolves the public builder, `probe(os.getpid()) is True`, `None ⇒ TTL-only` degrade, builder-raises fail-open; RED pre-retarget `3 failed, 1 passed` → GREEN `4 passed` — W4 `1a9a0fd2` |
| FR6 frozen no-steal suite honored | `git diff <base> -- <frozen files>` + QA adjudication | `test_two_actor_lease.py` + `test_doctor_lock_gc.py` zero-diff; `test_lease_main_probe.py` zero-diff; `test_lock_steal.py` monkeypatch-target rename (`_build_pid_probe` → `build_pid_probe`) + docstring only, every assertion / TTL / seed byte-identical; 50-test no-steal suite green — **FROZEN SUITE ADJUDICATED HONORED**, QA ship gate |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVE** 10/10 — handoff `2026-07-03T171013Z-qa-engineer-v0154-ship-gate` (validated exit 0) |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED**, 0 findings ≥ LOW — keyed to the pushed feature sha `338fadfa` (the closure push takes its own verdict) |
| CI (PR #97) | GitHub Actions | 38 checks, 0 failures — merge gate `aeaa3c66` |

## Drifts

### cap-arithmetic-corrected-in-dual-review-to-module-pair-counting

**Description:** The SPEC's cross-feature cap arithmetic was corrected during the dual
definition review from **feature-pair** counting (an earlier "8/21" framing that mixed the
A-5 audit's "8 relationships" with a 21 count) to **module-pair** counting — the granularity
`import-linter` actually operates at. The settled numbers are the exact **13** post-FR2
cross-feature module-pair edges and the ignore-cap of **26** (`15 + 13 − 2`).

**Resolution:** Recorded as a definition-process lesson, not a code drift: the cap test
(`test_import_linter_ignore_cap.py`) counts `ignore_imports` **module-pair** lines, so every
cap figure in a SPEC/PLAN/TASKS must be stated in module-pairs to be verifiable against the
test. The FR3 RED commit pinned the exact 13-edge set; the tree matched SPEC FR3 #1–#13
exactly (0 missing, 0 extra). No behavior change — the correction was folded before `Aprovado`.

**Memory updates:** `specs/memory/architecture.md` — the Enforcement section now states the
cap as 26 in module-pairs with the three-family breakdown (9/4/13).

### five-implementation-deviations-adjudicated-sound-at-qa-gate

**Description:** Five places where the literal SPEC wording could not be satisfied as
written; the implementer chose the semantically-correct alternative and recorded each. All
five were adjudicated **sound root-cause fixes** at the QA ship gate.

**Resolution:**
- **(W1) `core/models/workflow_execution.py` already existed.** The SPEC said "NEW"; the
  module was already the exact semantic home for the relocated
  `WorkflowModelPolicyOverlay`/`WorkflowModelPolicyStoreError`/`DEFAULT_CONTEXT` types, so
  the types were added to it rather than to a new file.
- **(W1) `cli_anchors` REPLACES `cli_app`; the "TYPE_CHECKING typer" clause was
  unsatisfiable.** Moving `_derive_cli_anchors` out of `subject_registry` into
  `cli/anchors.py` (the feature-layering law) makes the SPEC's "keeps only a `TYPE_CHECKING`
  `typer` import" clause impossible — the import became unused and was dropped. The feature
  now receives a pre-derived `cli_anchors: frozenset[str]` at the composition boundary.
- **(W2) `DadaiaWorkflowDTO` is defined lifecycle-side and re-exported.** The cycle
  constraint is absolute (`governed_catalog` cannot import `features/workflows`), so the
  shared DTO lives in `features/lifecycle/governed_catalog.py`; the public path
  `features.workflows.dadaia_catalog.DadaiaWorkflowDTO` is preserved by re-export (zero
  importer edits — 9 test importers unchanged).
- **(W2) `resolve_default_model_id` seam avoids a 14th edge.** `_node_meta_for_steps` stays
  in `dadaia_catalog` but resolves model ids through a `governed_catalog` seam helper instead
  of a direct `lifecycle.model_profiles` import — a direct import would have leaked a 14th
  cross-feature edge.
- **(W3) feature-local consumer-owned store protocols.** The existing
  `core/protocols/workflow_provider.py`/`agents_provider.py` ports describe the panel-facing
  **service** surface (`list_summaries` / `read_canonical_agents`), NOT the **store** surface
  (`list`/`get`, `list_raw`) the feature injects. Per DIP (consumer-owned interface) the store
  Protocols were defined feature-locally; the existing core ports are untouched. Result: zero
  infra edge, no `core/protocols/` edit, no new ignore.

**Memory updates:** `specs/memory/architecture.md` — `json_workflow_model_policy_store` types
now in `core/models` + lean port; the `cli_anchors` seam; `governed_catalog` as the catalog
definition home. `specs/memory/product/sdd/lifecycle-foundation.md` +
`specs/memory/product/sdd/dadaia-workflows.md` — the governed-catalog home relocation.

### fr3-contract-type-forbidden-to-independence

**Description:** FR3's cross-feature guard was specified as a `forbidden` contract
(`features ⊬ features`), but `import-linter` 2.11 rejects a self-referential `forbidden` with
"Modules have shared descendants".

**Resolution:** Changed to an `independence` contract at the QA re-review — the canonical
`import-linter` mechanism for mutual sibling independence, which accepts `ignore_imports`.
QA-verified by isolated probe (with the 13 ignores: `1 kept, 0 broken`; with none: BROKEN,
RED-first preserved). Every ignored edge still has a `dadaia_workspace.features` source, so
the existing cap-test layering assertion holds.

**Memory updates:** `specs/memory/architecture.md` — the Enforcement section names
`features-no-cross-feature` as an `independence` contract.

### cross-feature-edges-eroded-8-to-9-to-21-between-audit-and-definition

**Description:** The cross-feature edge count had silently grown from the A-5 audit's stated
"8 relationships" to a real **21 module-pair** edges at definition inspection (2026-07-03) —
the exact silent erosion this release exists to stop. After FR2's cycle-break the surviving
set is the 13 module-pairs now frozen as `features-no-cross-feature` ignores.

**Resolution:** The erosion is halted mechanically: no new cross-feature edge can be added
without breaking `features-no-cross-feature`, which is now CI-enforced and pre-push-gated.
Fixing (as opposed to documenting) the surviving 13 edges is explicit R7/R8/R9 scope, not
this release. This drift is the release's own thesis, proven.

**Memory updates:** `specs/memory/architecture.md` — the erosion-stop contract is recorded in
the Enforcement section.

### stale-enforcement-narratives-retired-in-closure

**Description:** Two stale enforcement narratives remained after the code went green: the
`setup.cfg` header count and the `import_linter_cache` hygiene-test docstring still described
a pre-v0.1.54 world (the "(still 17)" comment lineage and a cache-hygiene docstring that
narrated the unenforced state).

**Resolution:** Both retired in the closure commit `dea098bc`. The `setup.cfg` header was
corrected to 26 (9/4/13) inside W3 (`56a51148`); the residual narrative text and the
cache-hygiene test docstring were brought to the enforced-state truth in `dea098bc`. Not a
tool bug — the collateral-narrative class the v0.1.53 CLOSURE already flagged; caught and
cleared before archive.

**Memory updates:** none — both are source/test comments, not memory atoms.

### two-open-bugs-registered-mid-release-routed-to-r7

**Description:** Two bugs were reported while operating the tooling during the release and
registered as ADDITIVE `specs/bugs/*.jsonl` events (never blocked, never lease-gated):
`bugs-append-ignores-persisted-bind` (`dadaia bugs append` did not honor the persisted bind
when resolving the target context) and `backlog-new-stub-readme-lag-intents-schema` (a
`backlog new` stub README lagging the intents schema).

**Resolution:** Neither is in v0.1.54's picked scope — both are recorded, not silently
dropped, and routed to the **R7 (v0.1.55) pick's open-bug debt** (open bugs and open audits
outrank plain backlog at release-definition pick, per `release-governance`). No terminal
event appended; they remain `reported`/Open for R7 to disposition.

**Memory updates:** none — bug telemetry lives in `specs/bugs/`, not in memory atoms.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in
`_archive/`. Written this CLOSURE (phase = CLOSURE, MEMORY gate open):

- `specs/memory/architecture.md` — **Enforcement (actual state)** rewritten to the v0.1.54
  truth: `lint-imports` is now CI-wired (the `Lint (ruff)` job step + `dadaia ci preflight`
  fail-closed + pre-push hook); the contract set is **8** (adds `lifecycle-no-workflows`
  directed-forbidden + `features-no-cross-feature` independence); the `ignore_imports` cap
  is **26** with the three-family breakdown 9 infra / 4 subprocess / 13 cross-feature,
  per-family-asserted — fixes the stale "17 edges" claim. The `workflows` layer bullet now
  names `features/lifecycle/governed_catalog.py` as the governed-catalog definition home
  (`workflows/dadaia_catalog.py` is the presentation layer re-exporting it). The
  `json_workflow_model_policy_store` data types now live in `core/models/workflow_execution.py`
  behind a lean `core/protocols/workflow_model_policy_store.py` port (`policy_resolver` needs
  none). The hooks declared-exception and infrastructure bullets record the single public
  `infrastructure.process_probe_adapter.build_pid_probe` seam (the private hook builder
  extinct). The `core/` file-I/O authorized-exception set is now pinned by an AST ratchet
  guard — the "pending the `import-boundary-enforcement` backlog" qualifier dropped in both
  the Layers→core/ and Layering-invariant statements. The `cli/`→`cli_anchors` composition
  seam recorded. `last_updated`/`release_origin` → 2026-07-03 / v0.1.54.
- `specs/memory/quality-assurance.md` — the frozen no-steal suite paragraph gains the R6
  precedent: a **symbol-forced monkeypatch-target repoint** adjudicates the same as an import
  repoint (v0.1.54: `test_lock_steal.py` `_build_pid_probe` → `build_pid_probe` target rename,
  all assertions byte-identical), and **new coverage goes in a new sibling file, never
  expanding a frozen file** (v0.1.54 added `test_lease_pid_probe_public_builder.py` as a
  sibling to the frozen `test_lease_main_probe.py`). The CI-lint line updated: the `Lint
  (ruff)` job now runs ruff **and** `lint-imports` (import contracts enforced).
  `last_updated`/`release_origin` → 2026-07-03 / v0.1.54.
- `specs/memory/product/philosophy/product-vision.md` — the now-false "Known limits" bullet
  ("import-linter contracts exist but do not run in CI") **deleted** (the limitation is gone).
  `last_updated`/`release_origin` → 2026-07-03 / v0.1.54.
- `specs/memory/product/sdd/dadaia-workflows.md` — the governed-catalog home reference updated
  to `features/lifecycle/governed_catalog.py` (`dadaia_catalog.py` re-exports for
  presentation). `last_updated`/`release_origin` → 2026-07-03 / v0.1.54.
- `specs/memory/product/sdd/lifecycle-foundation.md` — the "Governed catalog (Wave B)" home
  moved to `features/lifecycle/governed_catalog.py`; `core/models/workflow_execution.py` now
  also holds the relocated `WorkflowModelPolicyOverlay`/`WorkflowModelPolicyStoreError`/
  `DEFAULT_CONTEXT`; the `json_workflow_model_policy_store` bullet notes the types relocated to
  `core/models` behind a lean store port. `last_updated`/`release_origin` → 2026-07-03 / v0.1.54.
- `specs/memory/tech-stack.md` — **no change**: `import-linter` (`>=2.11`, dev) was already the
  approved tool and its enforcement-status statement is single-sourced in
  `[[architecture]] §Enforcement`, which carries the v0.1.54 truth. No dependency added or bumped.
- `specs/memory/product/catalog.json` + `index.md` — **no hand-edit**: no atom's `tldr` or
  `summary` changed (only body content + `last_updated`/`release_origin` frontmatter, which the
  catalog does not carry). Authoritative regeneration + `lint-memory-atoms` exit-0 confirmation
  is a pending orchestrator shell step (PE has no shell tool; exact commands surfaced in the
  handoff).

## Dispositions

The three consumed backlog entries were archived at SHIP (durable copies + ledger in the
atomic archival commit `d1f7e988`), per the R4 dead-anchor process law — v0.1.54 deletes its
own consuming entries' anchors (`hooks/sdd_gate.py#_build_pid_probe` and
`container.py#_build_pid_probe`), so no implementation-wave commit staged any `specs/backlog/**`
path.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/_archive/v0.1.54/consumed-backlog/import-boundary-enforcement.md` | backlog | `DELIVERED — v0.1.54` | archival `d1f7e988`; `consumed_backlog.json` |
| `specs/_archive/v0.1.54/consumed-backlog/features-import-infrastructure-direct-debt.md` | backlog | `DELIVERED — v0.1.54` | archival `d1f7e988`; `consumed_backlog.json` |
| `specs/_archive/v0.1.54/consumed-backlog/pid-probe-seam-consolidation.md` | backlog | `DELIVERED — v0.1.54` | archival `d1f7e988`; `consumed_backlog.json` |

No bugs were **picked** into this release (open-bug debt was zero at pick — `candidates.md`).
No bug terminal events were appended. Two bugs registered **mid-release** are recorded (not
dropped) and routed forward to the R7 pick's open-bug debt:
`bugs-append-ignores-persisted-bind` and `backlog-new-stub-readme-lag-intents-schema` (both
remain `reported`/Open — see Drifts §two-open-bugs-registered-mid-release-routed-to-r7).

## Backlog returns

None to `ideas.md`/`candidates.md`. All three consumed entries shipped in full; their
out-of-scope tails are already tracked as SEPARATE debt in the entries themselves (the 4
`subprocess_runner` lazy-fallback edges and 4 ADR-1 lock/telemetry edges; the re-scoped
`features-no-hooks` contract + `slop_scan → hooks` decoupling). The R7–R12 conversion
sequence continues unchanged in `specs/backlog/candidates.md` (R6 row now marked
**SHIPPED — v0.1.54**).

## Archive decision

**MOVE** — `specs/releases/v0.1.54/` will be moved to
`specs/_archive/releases/v0.1.54/` via `git mv` (by the orchestrator / devops-engineer; PE
issues no git mutations). `specs/releases/ACTIVE.md` will then be advanced to the next
release per the operator's R6→R8 mandate (R7 = v0.1.55, architecture decomposition).
