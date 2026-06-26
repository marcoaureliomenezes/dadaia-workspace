# PLAN — Release: v0.1.24 — Two-Layer Redesign

**Status:** Aprovado
**Release ID:** v0.1.24
**Owner:** product-engineer

> Implementation strategy for the SPEC's eleven workstreams. Engineers own the *how*;
> this plan fixes order, layer boundaries, and validation so the work is unambiguous.
> Keep under 300 lines (specs doctor hard-errors above for new releases).

---

## 1. Strategy

Land in dependency order on a single `feature/v0.1.24` branch (off `feature/v0.1.23`),
segmented `alpha-1 → alpha-2 → rc-1`. The cut order is chosen so each wave leaves the tree
green (`ruff format --check`, `ruff check`, `mypy --strict`, `pytest`, `public doctor`):

1. **alpha-1 — Demolition + config seam.** Remove OpenCode (WS-1, mypy-guided) and add the
   discrete harness+model config (WS-2). These are the foundation; everything else builds
   on the reduced harness set + the model seam.
2. **alpha-2 — Fragment engine + first workflow.** Fragment library/loader (WS-3), context
   selector (WS-4), release-definition workflow on fragments (WS-5), fragment-suffix for
   implementation+one review step (WS-6), panel catalog (WS-8), prompt observability (WS-9).
3. **rc-1 — Dehydration + validation + closure.** AGENTS.md dehydration + AI-surface doctor
   (WS-7), operator live-validation (WS-10), closure (WS-11).

**Anti-slop discipline:** WS-1 is a pure deletion — no replacement scaffolding; resist
"while I'm here" refactors. WS-6's deferred workflows must fail loud, never silently no-op.

---

## 2. Layers affected

| Layer | Modules | Workstreams |
|------|---------|-------------|
| `core/models` | `lifecycle.py` (remove `OPENCODE_RUN`), `agent.py` (drop `opencode_model`) | WS-1, WS-2 |
| `core` | `model_registry.py` (source for the discrete catalog — no second table) | WS-2 |
| `infrastructure` | delete `opencode_runtime.py`; `codex_runtime.py` + `pi_runtime.py` (discrete model); `public_assets*.py`, `install_helpers.py`, `runtime_config.py`, `runtime_transforms/codex_assets.py` (opencode purge) | WS-1, WS-2 |
| `features/lifecycle` | `pipeline.py` (drop `"sonnet"/"opus"`), `prompt_builder.py` (fragment suffix), new `fragments/` loader + `context_selector` + workflow bodies | WS-3, WS-4, WS-5, WS-6, WS-9 |
| `features/workflows` + `features/panel` | `service.py` DTOs, `dag.py`, `handler.py`, catalog view/JS | WS-8 |
| `features/spec_context` + `hooks` | `doctor.py`, `root_whitelist.py` (drop `.opencode/`); new AI-surface doctor | WS-1, WS-7 |
| `cli/commands` | `lifecycle.py` (`_HARNESS_KINDS`, `--model`/`--step-model`, claude reject), `public.py`, `init.py` (target tuple) | WS-1, WS-2 |
| `public/` source | new `lifecycle_fragments/`; delete `plugins/sdd-gate.ts`; trim `data/AGENTS.md` + rules/skills; new doctor data | WS-3, WS-7, WS-8 |
| `tests/` | delete opencode tests; add model/fragment/selector/workflow/panel/observability/doctor tests | all |
| docs + projections | README, constitution, CHANGELOG, scoped AGENTS.md; restage + install + doctor | WS-1, WS-7 |

---

## 3. Execution order (per workstream)

### WS-1 — OpenCode removal (alpha-1, first)
1. Remove `AgentRuntimeKind.OPENCODE_RUN` from `core/models/lifecycle.py:49`.
2. Run `mypy --strict` — it enumerates every consumer. Fix each by deletion (not
   stubbing): `container.build_agent_runtime` branch; `cli/commands/lifecycle._HARNESS_KINDS`
   + help; `public_assets._install_opencode`/`_opencode_config`/install-tuple/`elif`;
   `public_assets_common._OPENCODE_DIRS`/`_VALID_TARGETS`/`copy_agents_for_opencode`/
   `opencode_config`/manifest; `runtime_transforms/codex_assets` opencode helpers+regexes;
   `core/models/agent.opencode_model` + `agents/reader` + `panel/views/api` serialization;
   `hooks/root_whitelist` + `spec_context/doctor` `_ROOT_ALLOWED_DIRS` (remove `.opencode/`);
   `import_/service` + `export/service`; `runtime_config.opencode_config`.
3. Delete files/dirs: `infrastructure/opencode_runtime.py`,
   `tests/unit/infrastructure/test_opencode_runtime.py`, `tests/integration/opencode_live/`,
   `tests/e2e/features/test_opencode_parity_hardening.py`, `public/plugins/sdd-gate.ts`,
   `features/academy/knowledge_basis/05_opencode/`.
4. Prune `conftest` guarded dirs + `.github/scripts/check_no_repo_local_claude.sh` opencode
   refs.
5. Edit docs: README, constitution, root + scoped AGENTS.md, CHANGELOG → harness set =
   {Claude Code, Codex, Pi}.
6. `dadaia public stage && dadaia public install --target all && dadaia public doctor`
   (exit 0, no `.opencode/` projection, no opencode manifest entry).
7. Validate: full `pytest`; `grep -ri opencode dadaia_workspace/ tests/` clean;
   `dadaia public install --target opencode` errors.

### WS-2 — Discrete harness + model config (alpha-1, after WS-1)
1. Add a discrete model catalog (e.g. `core/harness_models.py` or a registry view): a typed
   map `harness → ordered tuple of discrete model options`. Source ids from
   `model_registry.REGISTRY`; **pi: 3, codex: 2** (ids per ADR-B / OD-1+OD-2 — parameterize
   so confirming ids is a one-line data change). Provide a `validate(harness, model)` →
   resolved `(model_id, effort?)` helper.
2. `build_agent_runtime(kind, *, cwd, model=None)`: thread `model` into `PiHeadlessConfig.model`
   and into `CodexExecConfig.model`+`reasoning_effort`.
3. PI: in `pi_runtime.py`, read the effective model (request/config) and ensure `--model`
   carries it; if needed honor `request.model_profile` as the discrete id.
4. Codex: in `codex_runtime.py`, prefer the supplied discrete `(model, effort)` verbatim;
   keep the `codex_tier_views()` path only as the no-discrete-model fallback.
5. `pipeline.implementation_ladder()`: drop hardcoded `"sonnet"/"opus"`; default each step's
   model from the chosen harness catalog.
6. CLI (`cli/commands/lifecycle.py`): add `--model`/`--step-model`; restrict `_HARNESS_KINDS`
   to `{fake, codex, pi}` for workflows; reject `claude` with a Layer-1 pointer; validate
   `(harness, model)` against the catalog, erroring with the valid set.
7. Keep `CLAUDE_SDK` adapter + enum value (do NOT delete) — only remove from workflow
   choices.
8. Tests: catalog validation (valid/invalid pairs); `build_agent_runtime` model threading;
   PI passes `--model <id>`; Codex passes discrete `(id, effort)`; `claude` rejected as a
   workflow harness while `ClaudeSdkAdapter` stays importable + unit-tested.

### WS-3 — Fragment library + loader (alpha-2, first)
1. Create `dadaia_workspace/public/lifecycle_fragments/` with `shared/` +
   `release_definition/` bundles (others scaffolded as stubs). Each fragment = Markdown +
   frontmatter metadata (`id, role, workflow, step, static_inputs, dynamic_inputs,
   output_schema, max_context_policy`).
2. Add a loader (`features/lifecycle/fragments/loader.py`): load + validate metadata; reject
   malformed/missing fields; a check that no universal fragment names a Codex-only/Claude-only
   tool.
3. Project fragments via `public install` (stage + manifest); `public doctor` exit 0.
4. Tests: every fragment referenced by a shipped workflow exists + loads; malformed metadata
   rejected; harness-universal check fails on a forbidden tool token.

### WS-4 — Dynamic context selector (alpha-2, after WS-3)
1. Add `features/lifecycle/context_selector.py`: selector functions for memory atoms,
   catalog entries, backlog, bugs, audits, release artifacts, source summaries, diffs, test
   outputs, prior handoffs. Implement fully those WS-5 uses; others typed + unit-tested.
2. Max-context policies enum: `exact-files-only`, `summary`, `catalog-only`, `diff-only`,
   `previous-handoff-only`.
3. Record selected fragments + dynamic files in the run record (feeds WS-9).
4. Tests per selector + per policy; auditability (run record lists injected refs).

### WS-5 — Release-definition workflow body (alpha-2, after WS-3+WS-4)
1. Add `features/lifecycle/workflows/release_definition.py`: the §6.1 step sequence; Python
   owns order + gate decisions; each step = `role + fragment bundle + selected context +
   output schema + discrete (harness, model)`.
2. Wire the CLI verb (`dadaia lifecycle release define`) to this body; remove the generic
   "Run the step" suffix path for this workflow.
3. Python blocks on missing/rejected handoffs; writes SPEC/PLAN/TASKS only in-phase +
   in-write-set.
4. Tests: FAKE e2e walks the full sequence to `definition_commit_gate`; assert a fragment id
   / non-generic content in the emitted prompt; assert a rejected review handoff blocks
   advancement; assert adjacent-step different-harness seam (FAKE proves the seam; live is
   WS-10).

### WS-6 — Remaining workflow bodies (alpha-2)
1. Replace the generic prompt suffix with a fragment bundle for the `implementation` step +
   one review step on the existing pipeline (proves the pattern beyond release-definition).
2. Scaffold backlog/audit/research/bug-report workflow dirs + a Python entry point that
   raises `NotImplementedError("deferred to follow-up release")`.
3. Tests: the scaffolded workflows fail loud when invoked; the migrated pipeline steps emit
   fragment-sourced prompts.

### WS-7 — AI-surface dehydration (rc-1)
1. Trim `public/data/AGENTS.md` (+ scoped AGENTS.md) so mandatory ordered lifecycle ritual
   becomes a pointer to dadaia-workflows; keep Layer-1 safety law verbatim.
2. Add an AI-surface doctor check (`dadaia public doctor` extension or new
   `dadaia ai-surface doctor`): fails when mandatory ordered lifecycle ritual reappears in a
   persona/rule/skill body. Document + unit-test the rule-set (pass + fail cases).
3. Relabel (banner) old lifecycle skills/personas as non-authoritative; do NOT delete this
   release (OQ-2/OQ-4 → retain).
4. Restage + install + `public doctor` exit 0.

### WS-8 — Panel workflow catalog (alpha-2, after WS-2+WS-5)
1. Extend `WorkflowDetailDTO`/`StageDTO` (`features/workflows/service.py`): `purpose`,
   per-step `harness_options` + `model_options` (from WS-2 catalog), `availability`, keep
   `diagram_svg`.
2. Carry the data in the workflow source (`*.workflow.md` or successor) + render it in the
   catalog view/JS; `/api/workflows/<name>` returns the new fields.
3. Tests: DTO + endpoint shape; deferred workflow shown unavailable; release-definition
   workflow fully described as the reference.

### WS-9 — Prompt observability (alpha-2, after WS-5)
1. Persist per-step: fragment ids, dynamic context refs, prefix hash, discrete model,
   runtime kind, output schema, gate result in the run record.
2. Panel/report view for prompt composition.
3. Tests: `PromptPrefix` byte-identity across shared-prefix steps; no whole-memory injection
   by default.

### WS-10 — Operator live-validation (rc-1, human) → §SPEC WS-10 checklist.
### WS-11 — Closure (rc-1, product-engineer) → `dadaia-release-closure` skill.

---

## 4. Technical risks (implementation-level)

- **mypy cascade depth (WS-1):** the enum removal touches ~30 sites; do it in one focused
  pass and lean on `mypy --strict` — do not hand-hunt. Commit WS-1 atomically so a partial
  removal never lands.
- **Model id confirmation (WS-2):** parameterize the catalog; an unconfirmed id must not be
  hardcoded across call sites. Block WS-2's `[x]` on OD-1/OD-2 operator confirmation.
- **Fragment/projection coupling (WS-3):** fragments are projected assets — every fragment
  edit needs `public stage && install && doctor`; a missing manifest entry fails doctor.
- **Panel contract additivity (WS-8):** new DTO fields must be optional/defaulted so the
  existing `/api/workflows` consumers and `diagram_svg` path are untouched.

---

## 5. Validation plan

| Workstream | Validation command(s) | Pass criterion |
|------------|----------------------|----------------|
| WS-1 | `mypy --strict`; `pytest`; `grep -ri opencode dadaia_workspace/ tests/`; `dadaia public doctor` | green; clean grep; exit 0; no `.opencode/` |
| WS-2 | `pytest tests/unit/.../test_*model*`, `test_codex_runtime`, `test_pi_runtime`, CLI tests | discrete model reaches PI `--model` + Codex `(id,effort)`; claude rejected as workflow harness |
| WS-3 | `pytest` fragment loader tests; `dadaia public doctor` | referenced fragments exist + load; metadata validated; exit 0 |
| WS-4 | `pytest` selector + policy tests | each selector + policy covered; run record lists injected refs |
| WS-5 | `pytest` FAKE e2e | full sequence reaches commit gate; scoped prompt asserted; rejected handoff blocks |
| WS-6 | `pytest` | implementation + one review step emit fragment prompts; deferred workflows fail loud |
| WS-7 | `pytest` doctor tests; `dadaia public doctor` (or `ai-surface doctor`) | ritual-reintroduction fails the check; exit 0 on clean surface |
| WS-8 | `pytest` panel/workflow tests | new DTO/endpoint fields; deferred shown unavailable |
| WS-9 | `pytest` observability tests | run record carries prompt composition; prefix byte-identity |
| WS-10 | operator live runs (PI + Codex + adjacent-harness + invalid-pair + panel + `.opencode/` block) | every checklist item operator-confirmed |
| WS-11 | `dadaia specs doctor` | green; CLOSURE evidence complete; archive moved |

Pre-push: the standard CI gate (`ruff format --check`, `ruff check`, `mypy --strict`,
`pytest`) must pass before any push; live tests stay opt-in/auto-SKIP and never CI-gate.
