# SPEC — Release: v0.1.24 — Two-Layer Redesign: OpenCode removal + dadaia-workflows engine + prompt-fragment library + pi/codex-only Layer-2 + panel

**Status:** Aprovado
**Release ID:** v0.1.24
**Owner:** product-engineer
**Opened:** 2026-06-26
**Branches off:** `feature/v0.1.23` (supersedes v0.1.23 — see ADR-F)

---

## 1. Problem and context

dadaia-workspace completed an architecture shift (v0.1.16..v0.1.23): lifecycle authority
moved out of harness-native instruction surfaces (`AGENTS.md`, rules, skills, personas)
into a Python engine — `dadaia lifecycle` — that drives bounded workers behind
`AgentRuntimePort`. The shift is real but **incomplete and over-broad**, and the harness
surface has grown past what the operator wants to support. This release closes the
two-layer redesign per the operator's directive and removes a harness that is untested
and may be broken.

### Operator's two-layer model (the law for this release)

- **Layer 1 (entry):** the operator types `pi`/`codex`/`claude` in the terminal → binds a
  spec context. **Claude Code, Codex, and Pi are ALL fully supported at Layer 1.**
- **Layer 2 (dadaia-workflows):** a NEW first-class concept. A dadaia-workflow is a **CLI
  command the Layer-1 agent is oriented toward across the whole dev lifecycle, and
  safety-gate-enforced at the disk/commit boundary** (the SDD gate / git chokepoints
  enforce write-scope, lease, and phase on every write and commit — NOT that the workflow
  verb was invoked; a workflow-run-provenance token is a follow-up, see ADR-C). Each
  command runs a **Python workflow body** (loops, if/else, imports of
  text fragments) that calls **worker agents** and advances **Python-validated gates**.
  - **LAW 1 (harness):** the CLI call passes which harness to use; Layer-2 workers are
    **pi or codex ONLY** (plus `fake` for tests). **No Claude Code / Claude SDK in
    Layer 2** — running Claude as a Layer-2 worker spends credits outside the operator's
    subscription.
  - **LAW 2 (models):** discrete per-harness model options — **pi: 3 models, codex: 2
    models** — chosen on the CLI call (not a tier abstraction).
- **OpenCode: DELETE entirely** (both layers). Untested, possibly broken, must not ship.
  The supported harness set becomes exactly **Claude Code, Codex, Pi**.
- **Panel:** every dadaia-workflow must be **fully described in dadaia-panel** — purpose,
  the step sequence, which harness/model each step can use, a mermaid diagram, and
  availability. The operator must be able to open the panel and clearly understand each
  workflow.
- **Goal:** flexible multi-harness Layer-2 with **no lock-in**.

### Verified current-state facts (from source inspection — these are the problem statement)

These are confirmed against the on-disk tree at `feature/v0.1.23`. Engineers will rely on
them; cite the file:line when implementing.

**OpenCode is now a REAL adapter (v0.1.23 shipped it) — and must be deleted.** The
directive's earlier "OpenCode is a STUB" note is stale: v0.1.23 (T-23-06..08) replaced the
`NotImplementedError` stub with a working `opencode run --format json` adapter
(`container.py:338-341` wires `OpenCodeAdapter(cwd, git=GitSubprocessClient())`). v0.1.24
therefore **deletes a just-built adapter**, not a stub. Exhaustive deletion footprint:
- **Files to delete:** `infrastructure/opencode_runtime.py`,
  `tests/unit/infrastructure/test_opencode_runtime.py`, `tests/integration/opencode_live/`,
  `tests/e2e/features/test_opencode_parity_hardening.py`, `public/plugins/sdd-gate.ts`
  (the OpenCode Layer-1 gate plugin), `features/academy/knowledge_basis/05_opencode/`.
- **Enum-first cascade:** remove `AgentRuntimeKind.OPENCODE_RUN`
  (`core/models/lifecycle.py:49`) → let `mypy --strict` reveal every consumer:
  `container.py` `build_agent_runtime` branch (~338-341), `cli/commands/lifecycle.py`
  `_HARNESS_KINDS` (line 31) + help strings, `infrastructure/public_assets.py`
  (`_install_opencode` ~543, `_opencode_config` ~204, the `("agents","claude","codex","opencode","pi")`
  install tuple line 284, the `elif item == "opencode"` branch line 316),
  `infrastructure/public_assets_common.py` (`_OPENCODE_DIRS`, `_VALID_TARGETS`,
  `copy_agents_for_opencode`, `opencode_config`, manifest entry),
  `infrastructure/runtime_transforms/codex_assets.py` (`_prepare_agent_for_opencode`,
  `_opencode_permission_block`, opencode regexes), `core/models/agent.py` `opencode_model`
  field + `features/agents/reader.py` + `features/panel/views/api.py` serialization,
  `hooks/root_whitelist.py` + `features/spec_context/doctor.py` `_ROOT_ALLOWED_DIRS`
  (`.opencode/`), `features/import_/service.py` + `features/export/service.py`,
  conftest guarded dirs, `.github/scripts/check_no_repo_local_claude.sh`, and docs
  (README/constitution/AGENTS/CHANGELOG + the academy `05_opencode` references). Safe
  order: remove the enum value first; mypy enumerates the rest.

**Layer-2 internals (the engine the laws extend).** `cli/commands/lifecycle.py` verbs
call `_run_phase_step`/pipeline → `container.build_lifecycle_phase_workflow` /
`build_lifecycle_pipeline` → `features/lifecycle/{pipeline,phase_workflow,agent_runner,state_machine,prompt_builder}.py`
→ `AgentRuntimePort` adapters. Confirmed gaps to close for the laws:
- **No discrete-model CLI seam.** `_HARNESS_KINDS` maps name→`AgentRuntimeKind`; there is
  `--harness`/`--step-harness` but **no `--model`/`--step-model`**. `build_agent_runtime(kind, *, cwd)`
  (`container.py:303`) takes **no model**.
- **PI ignores the requested model.** `PiHeadlessConfig.model` exists
  (`pi_runtime.py:59`) and the command appends `--model` when set (`pi_runtime.py:143-144`),
  but the adapter **never reads `request.model_profile`** — a per-step model choice does
  not reach PI.
- **Codex uses a tier, not a discrete model.** `CodexExecConfig` carries `model` +
  `reasoning_effort` (`codex_runtime.py:43-49`), but `build_agent_runtime` constructs it
  with neither, so Codex resolves `(model, effort)` from `request.model_profile` via
  `codex_tier_views()` (`codex_runtime.py:153-162`) — a tier abstraction, not LAW-2's
  discrete-id choice.
- **Generic worker prompt.** `prompt_builder.PromptScope`/`PipelineStep` carry
  `model_profile` (`pipeline.py:53`), and `implementation_ladder()` hardcodes
  `model_profile="sonnet"/"opus"` (`pipeline.py:187,195,203,211`). The worker prompt is
  the generic string `"Run the {label} step for release {id}… emit APPROVED/REJECTED
  handoff"`. **This generic suffix is what the fragment library replaces.**
  `prompt_builder.PromptPrefix` (sha256-cacheable stable prefix) already exists and is
  retained.
- Model identifiers live in `core/model_registry.py` (`REGISTRY` of
  `ModelEntry{claude_id, codex_id, tier}`, `codex_tier_views()`). PI selects via
  `pi --model <id>`; Codex via `-m <id> -c model_reasoning_effort=<effort>`.

**Panel.** Regex-dispatch HTTP handler (`features/panel/handler.py`); endpoints
`/api/workflows` (list) and `/api/workflows/<name>` (detail, including server-rendered
`diagram_svg` from `features/workflows/dag.py::render_dag_svg`). Workflow data flows from
`*.workflow.md` via `infrastructure/markdown_workflow_store.py` →
`features/workflows/service.py` (`WorkflowSummaryDTO` / `WorkflowDetailDTO` (`service.py:73`,
with `diagram_svg` at `:87`) / `StageDTO` (`:61`)). Mermaid already renders for memory
atoms via mistune (`panel/views/_md_render.py`). To show per-step harness/model + purpose
+ availability + mermaid, extend `WorkflowDetailDTO`/`StageDTO` + the workflow source +
the catalog view/JS.

**Epic design spine.** `specs/backlog/lifecycle-prompt-fragments-ai-surface-dehydration.md`
defines the fragment library shape (§5), per-workflow prompt designs (§6), the WS-1..WS-10
breakdown (§7), acceptance (§8), and the mandatory grill questions (§10, OQ-1..7). This
SPEC operationalizes that epic under the new harness constraints (pi/codex-only Layer-2,
OpenCode gone).

---

## 2. Objective

Make the operator's two-layer model real: delete OpenCode entirely; enforce LAW 1 (Layer-2
workers = pi/codex/fake) and LAW 2 (discrete pi-3 / codex-2 model selection on the CLI);
introduce a library-owned prompt-fragment system consumed by Python "dadaia-workflows";
migrate the release-definition workflow onto fragments end-to-end as the first proof; and
make every dadaia-workflow fully self-describing in the panel (purpose, steps,
harness/model per step, mermaid, availability) — delivering a coherent, testable increment
while explicitly staging the broader fragment/dehydration migration into follow-up.

---

## 3. Scope (workstreams)

Eleven workstreams. Each carries verifiable acceptance. Implementer = `software-engineer`
unless noted; `human` tasks are operator-owned and gate CLOSURE. **What ships in v0.1.24
vs what is explicitly deferred is stated in §3.12.**

### WS-1 — OpenCode removal (the full footprint)

Delete OpenCode from both layers per the verified footprint in §1.

**Acceptance:**
- `AgentRuntimeKind.OPENCODE_RUN` no longer exists; `mypy --strict` is green with zero
  OpenCode references in `dadaia_workspace/`.
- All listed files/dirs deleted; `grep -ri "opencode" dadaia_workspace/ tests/` returns
  only intentional historical mentions in `_archive`/CLOSURE (none in live code, docs, or
  the academy).
- `_VALID_TARGETS` and the `public install` target tuple are exactly
  `{agents, claude, codex, pi}` (+`all`); `dadaia public install --target opencode` errors
  with an unknown-target message.
- `.opencode/` is removed from `root_whitelist._ROOT_ALLOWED_DIRS` and
  `spec_context/doctor._ROOT_ALLOWED_DIRS`; a `.opencode/` dir at root is now flagged by
  doctor / blocked by the root-whitelist hook.
- `dadaia public stage && dadaia public install --target all && dadaia public doctor` exits
  0 with no `.opencode/` projection and no opencode manifest entry.
- README/constitution/root+scoped AGENTS/CHANGELOG state the supported harness set as
  exactly Claude Code, Codex, Pi.
- Full `pytest` green after pruning the opencode tests (no orphaned imports).

### WS-2 — Discrete harness + model config (LAW 1 & LAW 2)

Make harness + discrete model selectable per CLI call and per pipeline step, with Layer-2
harness choices = `{pi, codex, fake}`.

**Acceptance:**
- A per-harness **discrete model catalog** exists as an explicit registry: **pi → 3
  models, codex → 2 models** (concrete ids confirmed in ADR-B — GPT-only at Layer 2: pi =
  `(gpt-5.5,high)`/`(gpt-5.5,low)`/`(gpt-5.3-codex,medium)`, codex =
  `(gpt-5.5,high)`/`(gpt-5.5,medium)`). The catalog is the single source of truth for
  validation and panel display, and is derived from / consistent with
  `core/model_registry.py` (no second drifting table). `claude-*` is never a Layer-2
  catalog entry.
- `build_agent_runtime(kind, *, cwd, model=None)` accepts a discrete model id; `cwd`
  semantics unchanged.
- PI honors the model: the adapter reads the resolved model (request or config) and passes
  `pi --model <id>`; a unit test asserts the chosen id reaches the command.
- Codex accepts a **discrete model id (+ its effort)** rather than only a tier: when a
  discrete model is supplied it is used verbatim; the tier fallback remains only when no
  discrete model is given. Unit test asserts the discrete id + effort reach the TOML/args.
- CLI: `--harness {pi|codex|fake}` + `--model <choice>`; pipeline `--step-harness label=harness`
  + `--step-model label=model`. An invalid `(harness, model)` pair is rejected with an
  actionable message listing the harness's valid models. `claude` is **not** an accepted
  Layer-2 `--harness` value (LAW 1) — selecting it errors with a message pointing to
  Layer-1 use.
- The `CLAUDE_SDK` adapter and its `AgentRuntimeKind.CLAUDE_SDK` enum value are **kept in
  code** (tested; Layer-1 claude is unaffected) but `claude` is removed from
  `_HARNESS_KINDS` workflow choices. A test asserts `claude` is rejected as a workflow
  harness while the adapter remains importable and unit-tested.
- `implementation_ladder()` no longer hardcodes `"sonnet"/"opus"` profiles; step model is
  a discrete choice (defaulted from the chosen harness's catalog).
- Full `pytest` green.

### WS-3 — Fragment library + loader + metadata

Implement the epic's fragment library (§5) and a loader, projected and versionable
(ADR-D / OQ-1 resolved to the projected public path).

**Acceptance:**
- Fragment source lives at `dadaia_workspace/public/lifecycle_fragments/` with the §5
  directory shape (at minimum the `shared/` and `release_definition/` bundles needed by
  WS-5; other workflow dirs may be scaffolded as stubs — see §3.12).
- Each fragment carries machine-readable metadata (frontmatter or sidecar) with at least:
  `id`, `role`, `workflow`, `step`, `static_inputs`, `dynamic_inputs`, `output_schema`,
  `max_context_policy` (per §5 example).
- A loader API loads + validates fragment metadata and rejects malformed/missing fields.
- Fragments are projected by `public install` (staged + manifest-tracked) and survive
  `public doctor` (exit 0). They are versionable (file-based, hashed).
- A test proves **every fragment referenced by a shipped workflow exists and is loadable**;
  a doctor/test check fails if a workflow references a fragment id with no source.
- **Harness-universal guarantee (PRIMARY — behavioral, not prose).** Each shipped
  fragment's declared `output_schema` is run through **BOTH** adapter parsers — PI
  (fenced-json / `message_end`) and Codex (`--output-last-message`) — via **FAKE
  fixtures**, and the test asserts **identical verdict extraction** from both. The
  `model_profile` semantics are unified in WS-2 so the same fragment bundle resolves
  consistently per harness: PI honors the discrete id, Codex takes `(id, effort)`. This
  behavioral cross-parser test is the guarantee that a fragment is genuinely
  harness-universal. A prose **denylist** of Codex-only / Claude-only tool tokens is
  retained only as a **secondary lint** (a loader/test check), not the primary guarantee.

### WS-4 — Dynamic context selector

Implement the per-step context selector (epic §7 WS-3) with auditability.

**Acceptance:**
- Selectors exist for: memory atoms, product catalog entries, backlog items, bug records,
  audit reports, active-release artifacts (SPEC/PLAN/TASKS/CLOSURE), source summaries, git
  diffs, test outputs, and prior handoffs — at the granularity the shipped
  release-definition workflow (WS-5) actually uses; selectors not exercised by WS-5 may be
  scaffolded with a typed interface + unit test (see §3.12).
- Max-context policies are explicit: at minimum `exact-files-only`, `summary`,
  `catalog-only`, `diff-only`, `previous-handoff-only`.
- Each run records (in the run record) which fragments and which dynamic files were
  injected — auditable per epic §8.8.
- Unit tests cover each implemented selector + each policy.

### WS-5 — Release-definition workflow body (first migrated workflow)

Implement the epic §6.1 release-definition sequence on fragments + Python gates as the
**first end-to-end migrated dadaia-workflow** (ADR-D / OQ-5 → release-definition first).

**Acceptance:**
- `dadaia lifecycle release define` (or its successor verb) runs the §6.1 step sequence
  (`release_scope → spec_create → spec_arch_review → spec_qa_review → plan_create →
  plan_review → tasks_create → tasks_implementability_review → definition_commit_gate`)
  with **scoped per-step prompts assembled from fragments**, not the generic "Run the step"
  suffix.
- Python owns step order and **blocks on missing/rejected handoffs**; the model recommends,
  Python decides transition legality (epic §3).
- Each step's prompt is `role + fragment bundle + dynamic context (WS-4) + output schema`;
  the worker harness/model is the discrete `(harness, model)` selected per WS-2.
- The workflow writes SPEC/PLAN/TASKS only in the correct phase and declared write set.
- An e2e on `--harness fake` runs the full sequence to the `definition_commit_gate`, proves
  scoped prompts are emitted (assert a fragment id / non-generic content in the prompt
  payload), and proves a rejected review handoff blocks advancement.
- Acceptance §8.5 demonstrated for this workflow: at least two **adjacent** steps can run
  on **different harnesses** (e.g. pi then codex) using the same fragment bundle and
  passing the same gates (env-gated live, auto-SKIP in CI; the FAKE e2e proves the seam).

### WS-6 — Remaining workflow bodies (staged / partially deferred)

Implementation/review/closure, backlog, audit, research, bug-report workflows (epic
§6.2-6.7).

**Acceptance:**
- **In v0.1.24:** the implementation/review/closure workflow bodies are extended to consume
  fragments for the prompt suffix where they already run on the pipeline (replace the
  generic suffix with a fragment bundle for at least the `implementation` and one review
  step), proving the pattern beyond release-definition.
- **Deferred (explicit):** full backlog/audit/research/bug-report workflow bodies are
  scaffolded (fragment dirs + a documented design stub + a Python entry point that raises
  `NotImplementedError` with a "deferred to follow-up release" message) — they do not ship
  as runnable workflows in v0.1.24. §3.12 states this.
- A test asserts the scaffolded-but-deferred workflows fail loudly (not silently) when
  invoked, so the deferral is honest.

### WS-7 — AI-surface dehydration (staged conservatively)

Shrink the projected AI surface toward Layer-1 safety + manual entry (epic §7 WS-7),
within a migration window.

**Acceptance:**
- Root + scoped `AGENTS.md` are trimmed so that **mandatory ordered lifecycle ritual**
  (e.g. "before editing, read SPEC/PLAN/TASKS and reserve a task", release-phase rituals)
  is represented as a pointer to the dadaia-workflows, not as the authoritative procedure —
  while **Layer-1 safety law stays verbatim** (root whitelist, repo hygiene, venv guard,
  lib-originated non-edit, memory atomicity, bug-filing emergency pointer).
- An **AI-surface doctor check** (`dadaia public doctor` extension or a new
  `dadaia ai-surface doctor`) **fails** when a mandatory ordered lifecycle ritual is
  reintroduced into a persona/rule/skill body (epic §8.6). The check has a documented,
  testable rule-set (what counts as "reintroduced ritual") and unit tests for pass/fail.
- Old skills/personas are **kept installed but relabelled non-authoritative** for the
  migration window (ADR resolves OQ-2/OQ-4 to "retain with banner, do not delete this
  release"); the dehydration of any single surface beyond AGENTS.md + the doctor check is
  explicitly conservative — see §3.12 for what ships vs defers.
- `dadaia public doctor` exits 0 after projection.

### WS-8 — Panel workflow catalog (per-workflow self-description)

Make every dadaia-workflow fully described in the panel (operator directive).

**Acceptance:**
- `WorkflowDetailDTO` / `StageDTO` are extended with: workflow **purpose**, per-step
  **harness options** + **model options** (from the WS-2 discrete catalog), **availability**
  (runnable vs deferred/scaffolded), and the existing server-rendered **mermaid `diagram_svg`**.
- The workflow source (`*.workflow.md` or its successor) carries this data; the catalog
  view + JS render it so the operator opening the panel sees, per workflow: purpose, the
  ordered step sequence, which harness/model each step can use, the mermaid diagram, and
  whether it is available.
- `/api/workflows/<name>` returns the new fields; a unit/integration test asserts the DTO +
  endpoint shape and that a deferred workflow is shown as unavailable.
- The release-definition workflow (WS-5) is fully and correctly described in the panel as
  the reference example.

### WS-9 — Prompt observability

Persist prompt composition in run records + a panel/report view (epic §7 WS-9, §8.8).

**Acceptance:**
- Each lifecycle run record persists, per step: fragment ids, dynamic context refs, prefix
  hash, the discrete model, the runtime kind, the output schema, and the gate result.
- A panel or report view surfaces prompt composition for a run.
- A test asserts `PromptPrefix` byte-identity across steps that share a prefix (cacheable
  stable prefix invariant).
- A test asserts no whole-memory injection by default (context selection is scoped).

### WS-10 — Operator live-validation gate (owner: `human`)

A blocking checklist the operator personally runs before CLOSURE. **The release does not
close until every item is confirmed.**

**Acceptance (operator-confirmed):**
- `dadaia lifecycle release define --harness pi --model <pi-model>` runs the
  release-definition workflow end-to-end against a real PI worker and produces scoped
  (non-generic) prompts + typed gate results.
- The same workflow runs with `--harness codex --model <codex-model>` and with at least one
  step on PI and an adjacent step on Codex (acceptance §8.5, live).
- An invalid `(harness, model)` pair and a `--harness claude` workflow call are both
  rejected with actionable messages.
- The panel shows every workflow with purpose, per-step harness/model, mermaid, and
  availability; the operator confirms each workflow is clearly understandable.
- A `.opencode/` write is now blocked by the root-whitelist hook in a real session (OpenCode
  is gone from the allowed root dirs).

### WS-11 — Closure (owner: product-engineer)

**Acceptance:**
- After WS-10 sign-off and ACTIVE.md phase = CLOSURE: write `CLOSURE.md` (summary,
  tasks+SHAs, validations incl. WS-10 evidence, drifts, memory updates, disposition sweep,
  archive decision); update memory atoms (`architecture.md` two-layer + harness set +
  Layer-2 worker matrix pi/codex-only + fragment system; `tech-stack.md` drop opencode,
  record verified pi/codex versions; affected product atoms). Carry the v0.1.23 disposition
  forward (see ADR-F).
- `dadaia specs doctor` green; `git mv` release to `_archive/`; ACTIVE.md updated.

### §3.12 — What ships in v0.1.24 vs what is deferred

**Ships (the coherent, testable minimum + the operator's hard requirements):**
- WS-1 OpenCode fully removed (both layers).
- WS-2 LAW 1 + LAW 2 working: discrete pi-3 / codex-2 model selection on the CLI, PI honors
  the model, Codex takes a discrete model, claude rejected as a Layer-2 harness.
- WS-3 fragment library + loader + metadata + referenced-fragment-exists check.
- WS-4 dynamic context selector for what release-definition needs (other selectors typed +
  unit-tested but not all exercised end-to-end).
- WS-5 release-definition workflow fully migrated onto fragments + gates (the first
  end-to-end proof; satisfies acceptance §8.2 and §8.5).
- WS-6 fragment-suffix proven for `implementation` + one review step on the pipeline.
- WS-7 AGENTS.md dehydration to pointers + the AI-surface doctor check (conservative).
- WS-8 panel catalog with purpose + per-step harness/model + mermaid + availability.
- WS-9 prompt observability run-record fields + prefix-byte-identity test.
- WS-10 operator live-validation; WS-11 closure.

**Deferred to a follow-up release (explicitly, honestly):**
- Full runnable backlog / audit / research / bug-report workflow bodies (WS-6) — scaffolded
  + fail-loud only in v0.1.24.
- Deep dehydration of every rule/skill/persona beyond AGENTS.md + the doctor check (WS-7) —
  old surfaces retained-with-banner for the migration window (OQ-2/OQ-4 → retain).
- Hook/ctx-inject reduction (epic WS-8) — out of scope this release; ctx-inject stays as
  a Layer-1 safety injector. (See §4.)
- Independent fragment versioning for archived-release replay (OQ-6) — fragments are
  file-hashed/versionable but per-release replay snapshotting is deferred.

This minimum still delivers a coherent increment: **OpenCode gone + LAWs 1&2 working +
fragment library + release-definition workflow on fragments + panel catalog**, exactly the
operator's stated floor.

---

## 4. Out of scope

- Deleting all Layer-1 hooks, personas, or skills at once. Safety hooks
  (root-whitelist, venv-guard, pre_gate, git chokepoints) and Layer-1 personas stay; this
  is a staged migration, not a purge.
- Adding any new harness or new `AgentRuntimeKind`. Supported harnesses become exactly
  Claude Code, Codex, Pi (OpenCode removed); LAW 1 limits Layer-2 to pi/codex/fake.
- Reducing/replacing ctx-inject or the broad session memory injection hook (epic WS-8) —
  deferred.
- Plugin packs / plugin-domain workflows (frontend-design, devops) — still undistributed.
- Changing the SDD specs folder format, the canonical lifecycle phase graph, or the
  `pre_gate` enforcement logic (beyond removing the opencode plugin).
- Implementing RPC or any networked harness transport (RPC stays dropped per v0.1.23
  ADR-23-1; the two supported transports remain CLI-headless and SDK, now with
  claude-SDK Layer-2-disallowed by LAW 1).
- Authoring memory atoms now — that is CLOSURE-phase product work (WS-11).

---

## 5. Architecture decision records (ADRs — fixed for this release)

### ADR-A — Harness set: claude/codex/pi at Layer 1; pi/codex/fake at Layer 2; OpenCode deleted
Layer-1 entry = `{claude, codex, pi}` (all fully supported). Layer-2 workflow workers =
`{pi, codex, fake}` only (LAW 1). **OpenCode is deleted entirely** (both layers, full
footprint §1/WS-1). The `CLAUDE_SDK` adapter and `AgentRuntimeKind.CLAUDE_SDK` are **kept
in code** (tested; Layer-1 claude unaffected) but `claude` is **removed from the workflow
`--harness` choices**. Documented: Layer-2 harness options = `{pi, codex, fake}`.
*Rationale:* OpenCode is untested/possibly broken and must not ship; Claude as a Layer-2
worker spends credits outside the operator's subscription.

### ADR-B — Discrete per-harness model catalog (LAW 2): pi-3 / codex-2 — GPT-only at Layer 2
Introduce an explicit discrete model catalog: **pi → 3 models, codex → 2 models**, derived
from / consistent with `core/model_registry.py` (no second drifting table). The CLI takes
`--harness` + `--model` (and `--step-harness`/`--step-model`), validated against the
chosen harness's set. `build_agent_runtime(kind, *, cwd, model)` carries the discrete id;
PI honors it (`pi --model <id>`); Codex takes a discrete `(id, effort)` rather than only a
tier.

**CONFIRMED catalog (operator, 2026-06-26).** PI runs on the operator's **Codex
subscription**, so PI's Layer-2 models are **GPT / codex model ids**, NOT Claude ids. Both
the pi and codex Layer-2 catalogs are therefore **GPT-only**:
- **pi (3):** `(gpt-5.5, high)`, `(gpt-5.5, low)`, `(gpt-5.3-codex, medium)` — GPT ids
  selected via `pi --model <id>` against PI's Codex subscription.
- **codex (2):** `(gpt-5.5, high)`, `(gpt-5.5, medium)` — two `(model, effort)` profiles of
  the one model `gpt-5.5` (OD-1 resolved to model+effort profiles, not two distinct models).

**Invariant (replaces the prior model-catalog risk).** `claude-*` is **NEVER** selectable
at Layer 2: no Claude id (including the region-restricted `claude-fable-5`) can appear in
either L2 catalog, because both catalogs are GPT-only by construction. The catalog is
explicit GPT data keyed by harness, parameterized so any future id change is a data edit —
it is NOT derived from a registry tier. Layer-1 Claude (the `CLAUDE_SDK` adapter) is
unaffected; this invariant governs Layer-2 worker selection only.

### ADR-C — dadaia-workflows are the canonical Layer-2 verbs; Layer-1 oriented toward them, safety-gate-enforced at the disk/commit boundary
The lifecycle CLI verbs are formalized as the canonical "dadaia-workflows": each a Python
body that imports fragments, selects dynamic context, calls workers, and advances
Python-validated gates. The Layer-1 agent is **oriented toward, and safety-gate-enforced at
the disk/commit boundary** — AGENTS.md is dehydrated to point at the workflows (WS-7) and
the SDD gate / git chokepoints enforce **write-scope, lease, and phase** on every disk
write and commit (NOT "you invoked the workflow"). There is no procedural enforcement that
a given workflow verb was actually run; the safety gate constrains *what* may be written,
not *how* it was produced. *Rationale:* lifecycle correctness must live in Python, not in
probabilistically-read instruction surfaces (epic §2/§3).

> **Note (follow-up, not this release):** a workflow-run-provenance gate token — proving a
> mutation originated from a real dadaia-workflow run — is a FOLLOW-UP, not v0.1.24. This
> release relies on the disk/commit safety gate, not procedural workflow enforcement.

### ADR-D — Fragment library at `public/lifecycle_fragments/`, projected + versionable; release-definition first
Fragments live under `dadaia_workspace/public/lifecycle_fragments/` (OQ-1 → projected
public path, so they ship with the wheel, are manifest-tracked, hash-versionable, and
survive `public doctor`). Each fragment has machine-readable metadata + a loader + the
dynamic context selector. The **release-definition workflow is migrated first** (OQ-5),
because it produces the artifacts every later workflow consumes.

### ADR-E — Panel describes every workflow fully
Extend `WorkflowDetailDTO`/`StageDTO` + the workflow source + the catalog view with
per-workflow purpose, per-step harness/model options, availability, and the existing
server-side mermaid SVG DAG. The operator must be able to open the panel and understand
each workflow without reading code.

### ADR-F — v0.1.24 supersedes v0.1.23
v0.1.24 branches off `feature/v0.1.23` and **keeps its still-valid parts**:
- SemVer release-id discipline; RPC dropped as a stated transport (ADR-23-1 carried
  forward); Codex Ring-2 git-diff `changed_paths` parity (T-23-05); the
  IMPLEMENTATION→CLOSURE + backtrack pipeline e2e (T-23-02/03); the Claude SDK
  `_default_query_fn` binding + tests (T-23-09/10/11 — Layer-1/SDK code retained, just
  removed from Layer-2 `--harness` choices); any security/redaction fixes.
And **reverses its OpenCode work**: deletes the `OpenCodeAdapter` built by T-23-06..08, the
opencode live test, and the opencode Layer-1 parity test (T-23-04) — OpenCode is gone.
v0.1.23's open human gate (T-23-13/14/15: live-validation, CLOSURE, deploy) was **never
confirmed/shipped**; that release is **not deployed**. Action: mark v0.1.23's SPEC
frontmatter `superseded_by: v0.1.24` with a note, and **do not** independently close/deploy
v0.1.23 — v0.1.24 carries its surviving acceptance forward and is the shipping release.
*Rationale:* the operator redesigned the harness model after v0.1.23 was defined; shipping
v0.1.23's OpenCode adapter would ship exactly what the operator now wants deleted.

---

## 6. Dependencies and risks

### Sequencing
- WS-1 (OpenCode removal) lands early and independently (enum-first; mypy-guided).
- WS-2 (discrete model config) is foundational for WS-5/WS-8/WS-10 and lands before them.
- WS-3 (fragment library/loader) blocks WS-5/WS-6.
- WS-4 (context selector) blocks WS-5.
- WS-5 (release-definition workflow) depends on WS-2/WS-3/WS-4.
- WS-8/WS-9 depend on WS-2 (model catalog) + WS-5 (a real workflow to describe/observe).
- WS-7 (dehydration + doctor) is independent but lands after WS-5 exists to point at.
- WS-10 (live gate) depends on WS-1..WS-9; WS-11 (closure) depends strictly on WS-10.

### Risk table
| Risk | Severity | Mitigation |
|------|----------|------------|
| **Large surface change** (OpenCode removal touches ~30 modules + docs + projections). | HIGH | Stage it: remove the enum first and let `mypy --strict` enumerate every consumer; prune tests alongside; verify with `public doctor` + full `pytest` before moving on. |
| ~~The exact pi-3 / codex-2 model ids are unconfirmed (ADR-B).~~ **RESOLVED** (operator-confirmed 2026-06-26). | HIGH → RESOLVED | Catalog confirmed GPT-only and parameterized as data: pi = `(gpt-5.5,high)`/`(gpt-5.5,low)`/`(gpt-5.3-codex,medium)`, codex = `(gpt-5.5,high)`/`(gpt-5.5,medium)`. The model-catalog-vs-tier concern is resolved because the catalog is explicit GPT data keyed by harness, **not** derived from any registry tier; and because both L2 catalogs are GPT-only, no `claude-*` id (incl. region-restricted `claude-fable-5`) can ever be selected at Layer 2. |
| **Fragment migration is iterative** — only release-definition ships end-to-end; the broad dehydration is conservative. | MEDIUM | Scope is explicit (§3.12): one workflow fully migrated, others scaffolded + fail-loud; the AI-surface doctor prevents silent regression of ritual back into personas. |
| PI/Codex live behavior (model honoring, discrete codex model+effort) is upstream-CLI-owned. | MEDIUM | Unit tests assert the args reach the command; WS-10 operator live run confirms real behavior (mocked tests cannot prove upstream CLI contracts). |
| Removing `claude` from Layer-2 while keeping the SDK adapter could confuse callers. | LOW | A test asserts `claude` is rejected as a workflow harness AND the adapter stays importable/tested; the rejection message points to Layer-1 use. |
| Deleting the OpenCode Layer-1 gate plugin weakens a (removed) harness only. | LOW | OpenCode is gone; no remaining harness loses its gate. Root-whitelist now blocks `.opencode/` rather than allowing it. |
| Panel DTO extension could break the existing `/api/workflows` contract. | LOW | New fields are additive; existing fields/`diagram_svg` unchanged; test asserts both old and new shape. |

### Memory files affected at closure (WS-11, CLOSURE phase only)
- `specs/memory/architecture.md` — two-layer model; harness set (drop OpenCode); Layer-2
  worker matrix (pi/codex/fake only, claude-SDK kept-but-Layer-2-disallowed); the
  dadaia-workflows + fragment system; discrete model catalog.
- `specs/memory/tech-stack.md` — drop opencode; record verified pi/codex CLI versions.
- `specs/memory/product/<lifecycle/harness atoms>.md` — only atoms that state the
  harness/transport/workflow surface.

### Open decisions (grill output)
- **OD-1 — RESOLVED** (operator, 2026-06-26): the codex-2 pair is **two `(model, effort)`
  profiles of one model** — `(gpt-5.5, high)` + `(gpt-5.5, medium)`. (ADR-B.)
- **OD-2 — RESOLVED** (operator, 2026-06-26): pi-3 = `(gpt-5.5, high)`, `(gpt-5.5, low)`,
  `(gpt-5.3-codex, medium)` — **GPT ids, not Claude** (PI runs on the operator's Codex
  subscription). The earlier Claude proposal is withdrawn. (ADR-B.)
- **OD-3 — CONFIRMED:** removing `claude` from Layer-2 `--harness` choices is enforcement by
  validation, no exception (directive confirmed). Layer-1 Claude is unaffected.
- **OD-4:** Is the WS-7 conservative dehydration scope (AGENTS.md pointers + doctor check
  only, old surfaces retained-with-banner) acceptable for this release, with deep
  dehydration deferred? (§3.12.)
