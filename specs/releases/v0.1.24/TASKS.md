# TASKS — Release: v0.1.24 — Two-Layer Redesign

**Status:** Aprovado
**Release ID:** v0.1.24
**Owner:** product-engineer

Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. At most one `[-]` per owner unless a
parallel block declares disjoint write sets. Implementer = `software-engineer` unless noted.
`human` tasks are operator-owned and block CLOSURE.

---

## alpha-1 — Demolition + config seam

### T-24-01 — Remove `AgentRuntimeKind.OPENCODE_RUN` + mypy-guided consumer purge (WS-1)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/models/lifecycle.py`, `dadaia_workspace/container.py`,
  `dadaia_workspace/cli/commands/lifecycle.py`, `dadaia_workspace/cli/commands/public.py`,
  `dadaia_workspace/cli/commands/init.py`, `dadaia_workspace/infrastructure/public_assets.py`,
  `dadaia_workspace/infrastructure/public_assets_common.py`,
  `dadaia_workspace/infrastructure/install_helpers.py`,
  `dadaia_workspace/infrastructure/runtime_config.py`,
  `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py`,
  `dadaia_workspace/core/models/agent.py`, `dadaia_workspace/features/agents/reader.py`,
  `dadaia_workspace/features/panel/views/api.py`,
  `dadaia_workspace/hooks/root_whitelist.py`,
  `dadaia_workspace/features/spec_context/doctor.py`,
  `dadaia_workspace/features/import_/service.py`,
  `dadaia_workspace/features/export/service.py`
- **Preconditions:** none (first task).
- **Description:** Remove the enum value first, then fix every site `mypy --strict` reveals
  by deletion (not stubbing): `build_agent_runtime` branch, `_HARNESS_KINDS`+help,
  `_install_opencode`/`_opencode_config`/install-tuple/`elif`, `_OPENCODE_DIRS`/`_VALID_TARGETS`/
  `copy_agents_for_opencode`/`opencode_config`/manifest, codex_assets opencode helpers+regexes,
  `agent.opencode_model` + reader + panel serialization, `.opencode/` from both
  `_ROOT_ALLOWED_DIRS`, import/export opencode refs.
- **Done when:** `mypy --strict` green; zero opencode references in the listed modules;
  `_VALID_TARGETS == {agents, claude, codex, pi}`.
- `[x]`

### T-24-02 — Delete OpenCode files/tests/academy + conftest/CI refs (WS-1)
- **Owner:** software-engineer
- **Write set:** delete `dadaia_workspace/infrastructure/opencode_runtime.py`,
  `tests/unit/infrastructure/test_opencode_runtime.py`, `tests/integration/opencode_live/`,
  `tests/e2e/features/test_opencode_parity_hardening.py`,
  `dadaia_workspace/public/plugins/sdd-gate.ts`,
  `dadaia_workspace/features/academy/knowledge_basis/05_opencode/`; edit `tests/conftest.py`,
  `.github/scripts/check_no_repo_local_claude.sh`
- **Preconditions:** T-24-01 (no live references remain).
- **Description:** Delete the OpenCode adapter, its tests, the live-test dir, the Layer-1
  parity test, the gate plugin source, and the academy module; remove opencode from conftest
  guarded dirs + the CI script.
- **Done when:** files gone; `grep -ri opencode dadaia_workspace/ tests/ .github/` clean;
  full `pytest` green (no orphaned imports).
- `[x]`

### T-24-03 — Purge OpenCode from docs + reproject (WS-1)
- **Owner:** software-engineer
- **Write set:** `README.md`, `dadaia_workspace/public/data/AGENTS.md`, `CHANGELOG.md`,
  scoped `AGENTS.md` files that name harnesses; (specs/constitution.md + scoped docs as
  needed — constitution edit needs operator confirmation if substantive)
- **Preconditions:** T-24-01, T-24-02.
- **Description:** State the supported harness set as exactly Claude Code, Codex, Pi
  everywhere. Then `dadaia public stage && dadaia public install --target all && dadaia public
  doctor`.
- **Done when:** `public doctor` exit 0; no `.opencode/` projection; no opencode manifest
  entry; `dadaia public install --target opencode` errors with unknown-target.
- `[x]`

### T-24-04 — Discrete per-harness model catalog (WS-2, LAW 2)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/harness_models.py` (new), `tests/unit/core/test_harness_models.py` (new)
- **Preconditions:** T-24-01.
- **Description:** Typed catalog `harness → ordered discrete model options` (pi: 3, codex: 2),
  sourced from `model_registry.REGISTRY` (no second drifting table). Provide
  `validate(harness, model) -> resolved (model_id, effort?)`. Parameterize ids so confirming
  is a data change. **Confirmed catalog (operator 2026-06-26 — GPT-only at Layer 2):**
  pi = `(gpt-5.5, high)` / `(gpt-5.5, low)` / `(gpt-5.3-codex, medium)`;
  codex = `(gpt-5.5, high)` / `(gpt-5.5, medium)`. No `claude-*` id is ever a Layer-2 option.
- **Done when:** catalog present; valid pairs resolve, invalid pairs raise with the valid set;
  unit tests green.
- `[x]`

### T-24-05 — Thread discrete model through `build_agent_runtime` + PI + Codex (WS-2)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/container.py`,
  `dadaia_workspace/infrastructure/pi_runtime.py`,
  `dadaia_workspace/infrastructure/codex_runtime.py`,
  `dadaia_workspace/features/lifecycle/pipeline.py`,
  `tests/unit/infrastructure/test_pi_runtime.py`,
  `tests/unit/infrastructure/test_codex_runtime.py`,
  `tests/unit/features/lifecycle/test_pipeline.py`
- **Preconditions:** T-24-04.
- **Description:** `build_agent_runtime(kind, *, cwd, model=None)`; PI reads the effective
  model and passes `pi --model <id>`; Codex prefers the supplied discrete `(model, effort)`
  verbatim (tier path = fallback only); `implementation_ladder()` drops `"sonnet"/"opus"`,
  defaults model from the catalog.
- **Done when:** unit tests assert the discrete id reaches PI `--model` and Codex
  `(id, effort)`; pipeline default model comes from the catalog; `pytest` green.
- `[x]`

### T-24-06 — CLI `--model`/`--step-model` + Layer-2 harness = {pi,codex,fake}; reject claude (WS-2, LAW 1)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py`,
  `tests/integration/cli/test_lifecycle_cli.py` (or the existing lifecycle CLI test module)
- **Preconditions:** T-24-04, T-24-05.
- **Description:** Add `--model`/`--step-model`; restrict workflow `_HARNESS_KINDS` to
  `{fake, codex, pi}`; reject `claude` with a Layer-1 pointer; validate `(harness, model)`
  against the catalog. Keep `CLAUDE_SDK` adapter + enum value importable/tested.
- **Done when:** invalid `(harness, model)` errors with valid set; `--harness claude` rejected;
  a test asserts `ClaudeSdkAdapter` stays importable + unit-tested; `pytest` green.
- `[x]`

---

## alpha-2 — Fragment engine + first workflow + panel

### T-24-07 — Fragment library + loader + metadata + checks (WS-3)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/public/lifecycle_fragments/**` (new),
  `dadaia_workspace/features/lifecycle/fragments/loader.py` (new),
  `tests/unit/features/lifecycle/test_fragment_loader.py` (new),
  `dadaia_workspace/infrastructure/public_assets*.py` (project the new dir)
- **Preconditions:** T-24-03 (clean projection baseline).
- **Description:** Create `shared/` + `release_definition/` fragment bundles (others
  scaffolded as stubs) with frontmatter metadata (`id, role, workflow, step, static_inputs,
  dynamic_inputs, output_schema, max_context_policy`); a loader that validates + rejects
  malformed metadata; project + manifest-track via `public install`. **Harness-universal
  guarantee (PRIMARY — behavioral):** run each shipped fragment's `output_schema` through
  BOTH adapter parsers — PI (fenced-json / `message_end`) and Codex
  (`--output-last-message`) — via FAKE fixtures and assert **identical verdict
  extraction**; rely on WS-2's unified `model_profile` semantics (PI honors the discrete id,
  Codex takes `(id, effort)`). Keep the prose denylist of harness-specific tool tokens as a
  **secondary lint** only.
- **Done when:** every fragment referenced by a shipped workflow exists + loads; malformed
  metadata rejected; the dual-parser cross-extraction test asserts identical verdicts from
  both adapters; the secondary denylist lint fails on a forbidden token; `public doctor` exit
  0; tests green.
- `[ ]`

### T-24-08 — Dynamic context selector + max-context policies + run-record audit (WS-4)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/context_selector.py` (new),
  `tests/unit/features/lifecycle/test_context_selector.py` (new),
  `dadaia_workspace/features/lifecycle/agent_runner.py` (record injected refs, if that is the
  run-record seam)
- **Preconditions:** T-24-07.
- **Description:** Selectors (memory atoms, catalog, backlog, bugs, audits, release
  artifacts, source summaries, diffs, test outputs, prior handoffs) — full for WS-5's needs,
  typed+unit-tested otherwise; policies `exact-files-only`/`summary`/`catalog-only`/`diff-only`/
  `previous-handoff-only`; record selected fragments + dynamic files in the run record.
- **Done when:** each implemented selector + policy unit-tested; run record lists injected
  refs; `pytest` green.
- `[ ]`

### T-24-09 — Release-definition workflow body on fragments + gates (WS-5)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/workflows/release_definition.py` (new),
  `dadaia_workspace/cli/commands/lifecycle.py` (wire the verb),
  `dadaia_workspace/features/lifecycle/prompt_builder.py` (fragment suffix path)
- **Preconditions:** T-24-07, T-24-08.
- **Description:** Implement the SPEC §6.1 step sequence; Python owns order + gate decisions;
  each step = `role + fragment bundle + selected context + output schema + discrete (harness,
  model)`; remove the generic suffix for this workflow; block on missing/rejected handoffs;
  write SPEC/PLAN/TASKS only in-phase + in-write-set.
- **Done when:** the verb runs the fragment-driven sequence (no generic "Run the step" suffix
  for release-definition).
- `[ ]`

### T-24-10 — Release-definition workflow e2e (FAKE) + adjacent-harness seam (WS-5)
- **Owner:** software-engineer
- **Write set:** `tests/integration/cli/test_release_definition_workflow.py` (new)
- **Preconditions:** T-24-09.
- **Description:** FAKE e2e walks the full sequence to `definition_commit_gate`; assert a
  fragment id / non-generic content in the emitted prompt; assert a rejected review handoff
  blocks advancement; assert the adjacent-step different-harness seam (FAKE proves the seam).
- **Done when:** e2e asserts terminal commit gate + scoped prompt + blocked-on-rejection +
  seam; CI green.
- `[ ]`

### T-24-11 — Fragment suffix for implementation + one review step; scaffold deferred workflows (WS-6)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/pipeline.py`,
  `dadaia_workspace/features/lifecycle/workflows/__init__.py` (+ deferred stubs),
  `tests/unit/features/lifecycle/test_pipeline.py`
- **Preconditions:** T-24-07.
- **Description:** Replace the generic suffix with a fragment bundle for the `implementation`
  step + one review step; scaffold backlog/audit/research/bug-report workflow entry points
  that raise `NotImplementedError("deferred to follow-up release")`.
- **Done when:** the two pipeline steps emit fragment-sourced prompts; the deferred workflows
  fail loud when invoked (asserted); `pytest` green.
- `[ ]`

### T-24-12 — Panel workflow catalog: purpose + per-step harness/model + availability + mermaid (WS-8)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/workflows/service.py`,
  `dadaia_workspace/features/panel/handler.py`,
  `dadaia_workspace/features/panel/views/*` (catalog view/JS),
  `dadaia_workspace/public/workflows/*.workflow.md` (or successor source),
  `tests/integration/panel/test_workflows_api.py` (or existing panel test module)
- **Preconditions:** T-24-06 (model catalog), T-24-09 (a real workflow to describe).
- **Description:** Extend `WorkflowDetailDTO`/`StageDTO` with `purpose`, per-step
  `harness_options`+`model_options`, `availability`; keep `diagram_svg`; carry the data in the
  workflow source; render in the catalog view; `/api/workflows/<name>` returns the new fields.
- **Done when:** new fields additive (old shape + `diagram_svg` intact); deferred workflow
  shown unavailable; release-definition fully described; tests green.
- `[ ]`

### T-24-13 — Prompt observability: run-record fields + view + prefix byte-identity (WS-9)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/agent_runner.py` (or run-record store),
  `dadaia_workspace/features/panel/views/*` (or a report view),
  `tests/unit/features/lifecycle/test_prompt_observability.py` (new)
- **Preconditions:** T-24-09.
- **Description:** Persist per-step fragment ids, dynamic context refs, prefix hash, discrete
  model, runtime kind, output schema, gate result; add a panel/report view; test
  `PromptPrefix` byte-identity across shared-prefix steps + no whole-memory injection by
  default.
- **Done when:** run record carries prompt composition; prefix byte-identity asserted; tests
  green.
- `[ ]`

---

## rc-1 — Dehydration, validation, closure

### T-24-14 — AI-surface dehydration: AGENTS.md pointers + AI-surface doctor check (WS-7)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/public/data/AGENTS.md`, scoped `public/.../AGENTS.md`,
  `dadaia_workspace/features/spec_context/doctor.py` (or new
  `dadaia_workspace/features/ai_surface/doctor.py` + CLI wiring),
  `tests/unit/features/.../test_ai_surface_doctor.py` (new); relabel banners on old
  lifecycle skills/personas under `public/skills/**`, `public/agents/**`
- **Preconditions:** T-24-09 (workflows exist to point at).
- **Description:** Trim AGENTS.md so mandatory ordered lifecycle ritual becomes a pointer to
  dadaia-workflows (keep Layer-1 safety law verbatim); add a doctor check that fails when
  mandatory ritual reappears in a persona/rule/skill body (documented rule-set + pass/fail
  tests); banner old surfaces non-authoritative (do NOT delete — OQ-2/OQ-4 retain). Restage +
  install + `public doctor`.
- **Done when:** ritual-reintroduction fails the check; clean surface exits 0; `public doctor`
  exit 0; tests green.
- `[ ]`

### T-24-15 — Mark v0.1.23 superseded; carry-forward note (WS-11 prep, ADR-F)
- **Owner:** product-engineer
- **Write set:** `specs/releases/v0.1.23/SPEC.md` (frontmatter `superseded_by: v0.1.24` + note)
- **Preconditions:** none (additive spec edit; DEFINITION phase).
- **Description:** Add `superseded_by: v0.1.24` to v0.1.23's SPEC frontmatter + a note that
  v0.1.24 supersedes it (keeps surviving acceptance, deletes the OpenCode work, ships in its
  place; v0.1.23 was never deployed). Do NOT close/deploy v0.1.23 independently.
- **Done when:** v0.1.23 SPEC carries the supersede marker + note.
- `[ ]`

### T-24-16 — Operator live-validation acceptance gate (WS-10) [HARD GATE]
- **Owner:** human (operator)
- **Write set:** none (sign-off; captured in CLOSURE.md)
- **Preconditions:** T-24-01..T-24-14 complete + merged-to-feature.
- **Description:** Operator personally confirms each:
  - `[ ]` `release define --harness pi --model <pi-model>` runs the workflow end-to-end with
    scoped (non-generic) prompts + typed gates against a real PI worker.
  - `[ ]` Same with `--harness codex --model <codex-model>`, incl. one step on PI + adjacent
    step on Codex (acceptance §8.5 live).
  - `[ ]` Invalid `(harness, model)` and `--harness claude` are both rejected with actionable
    messages.
  - `[ ]` Panel shows every workflow with purpose, per-step harness/model, mermaid, and
    availability; operator confirms each is clearly understandable.
  - `[ ]` A `.opencode/` write is blocked by the root-whitelist hook in a real session.
- **Done when:** every sub-item operator-confirmed. **Blocks CLOSURE.**
- `[ ]`

### T-24-17 — CLOSURE: write CLOSURE.md + update memory atoms (WS-11)
- **Owner:** product-engineer
- **Write set:** `specs/releases/v0.1.24/CLOSURE.md`, `specs/memory/architecture.md`,
  `specs/memory/tech-stack.md`, affected `specs/memory/product/*.md`,
  `specs/releases/ACTIVE.md`
- **Preconditions:** T-24-16 confirmed; ACTIVE.md phase = CLOSURE.
- **Description:** Write CLOSURE.md (summary, tasks+SHAs, validations incl. WS-10 evidence,
  drifts, memory updates, disposition sweep, archive decision). Update memory: two-layer model
  + harness set (drop OpenCode) + Layer-2 worker matrix (pi/codex/fake; claude-SDK
  kept-but-Layer-2-disallowed) + dadaia-workflows/fragment system + discrete model catalog;
  drop opencode from `tech-stack.md` + record verified pi/codex versions. Disposition the epic
  backlog item + carry v0.1.23's disposition forward.
- **Done when:** `dadaia specs doctor` green; CLOSURE evidence complete.
- `[ ]`

### T-24-18 — Archive release + advance ACTIVE.md (WS-11) [LAST]
- **Owner:** product-engineer (git mv delegated to devops-engineer / operator)
- **Write set:** `specs/releases/ACTIVE.md`; request `git mv specs/releases/v0.1.24
  specs/_archive/releases/v0.1.24`
- **Preconditions:** T-24-17 complete; `dadaia specs doctor` green.
- **Description:** Set ACTIVE.md phase ARCHIVED, request the `git mv` to `_archive/`, then
  point ACTIVE.md at the next release (or `release: none`).
- **Done when:** release archived; ACTIVE.md updated.
- `[ ]`

---

> **Note on version bump / deploy:** unlike v0.1.23 (which had an explicit deploy task),
> the version bump + publish is intentionally NOT a task here pending operator direction on
> shipping cadence (the directive does not request a deploy). If the operator wants
> v0.1.24 published, add a `human`-owned `pyproject.toml` bump + tag task gated by T-24-16.
