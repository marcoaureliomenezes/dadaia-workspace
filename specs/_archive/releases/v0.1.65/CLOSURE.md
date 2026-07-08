# Closure: Release — v0.1.65 — L1 Agent Model Governance & Panel Sub-agents Tab

> **Status:** Aprovado
> **Release ID:** v0.1.65
> **Owner:** product-engineer
> **Closed:** 2026-07-08
> **Branch:** `feature/v0.1.65` · **Definition commit:** `e52879e1` · **Merged:** `962a23da` (PR #124, squash of `feature/v0.1.65`, 2026-07-08, all CI green incl. the in-flight fix commit `9a77abc3`) · **Closure branch:** `chore/v0.1.65-closure`
> **Ship gates:** qa-engineer **APPROVED** (ship-gate handoff — full gate battery green; hermetic panel-e2e harness verified; T-65-15 golden triage at merge-base `d2b94585` with zero silent re-baselining) · security-reviewer **APPROVED ×2** (push-gate keyed to the pushed ref sha `45f65df1`, re-keyed to `9a77abc3` after the hermetic-harness CI fix) · CI **all checks green** on `962a23da` (PR #124) including the E2E panel (Playwright) leg on the new hermetic harness.
> **Mandate:** first release after the v0.1.61→v0.1.64 queue completed; picked set = the HIGH backlog centerpiece `l1-agent-model-governance-panel` + the two open LOW bugs that outranked plain backlog at pick (release-governance).

## Summary

v0.1.65 gives the **Layer-1 agent roster the same panel-managed model governance Layer-2
workflows already had**. The 9 core agent bodies are now **model-agnostic sources**: their
hardcoded `model:`/`effort:` frontmatter is gone, and the concrete `(model, effort)` pair is
**composed at install time** from a policy, not authored in the body. A library-shipped
registry of **three named templates** — `balanced` (default), `subscription-saver`,
`max-quality` — plus an operator **overlay** (`.dadaia/states/agent_model_policy.json`, schema
`agent-model-policy-v1`) feed a **single resolver** whose precedence is per-agent override >
applied template > library default. The resolver is the only precedence implementation:
install-write, `public doctor`, the codex projection, and the panel all consume it. One policy
governs **both** Layer-1 projections in lockstep — `.claude/agents/*.md` gets rendered
`model:`/`effort:` lines, and `.codex/agents/*.toml` gets the mapped codex model id plus a
`model_reasoning_effort` derived from the SAME resolved effort via a fixed clamp.

The operator now retiers any sub-agent **live from the panel**: a new **Sub-agents** tab (the
7th, beside Workflows) exposes a roster table with per-agent model + effort pickers and a
template selector, an explicit **Apply** that validates → saves the overlay → re-renders both
projections, and a post-apply pop-up with per-harness pick-up instructions (Claude sessions
pick up the new definition automatically on the next delegation; Codex sessions restart). A
hard, three-layer constraint bakes in the **never-Fable-on-security-reviewer** law (its
cyber-safety classifiers can refuse security-review-shaped work). `public doctor` became
policy-aware: it compares each projected `.claude/agents/*.md` against `render(staged generic +
resolved policy)`, so an operator policy change reads `[ok]` while a hand-edited projection
reads `[drift]`. On **this** instance the no-overlay `balanced` default supersedes the
2026-07-06 hardcoded 5-Fable retier: **`claude-fable-5` now runs only on `project-manager` +
`software-architect`** (D-1 live retier, operator-ratified via G-1/G-5).

Two open LOW bugs shipped fixed alongside (bug-always-solved): the backlog doctor no longer
misdiagnoses a **frontmatter YAML parse failure** as a missing-`intents[]` finding (it now
emits a dedicated parse-error diagnostic naming line/column and suppresses the downstream
findings), and the **e2e harness-toggle spec** is deterministic (armed `waitForResponse` on the
save PUT before clicking).

## Tasks completed

All implementation landed on `feature/v0.1.65` and merged as squash `962a23da` (PR #124); the
`9a77abc3` fix commit is folded into the same PR. Per-task RED-first evidence and write sets are
in `TASKS.md` completion notes.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| — | W0 definition — SPEC/PLAN/TASKS after the mandatory grill (G-1..G-5, D-1..D-8); architect REVISE fold (F-1..F-7) | `e52879e1` |
| T-65-01 | FR6 — `claude-sonnet-5` registry entry (D-2: `gpt-5.3-codex`, tier `plugin`, pricing 3.00/15.00/3.75/0.30 eff 2026-07-01) | `962a23da` |
| T-65-02 | FR2/FR4/D-3/D-4 — core policy model + 3-template registry + single resolver (precedence, never-Fable-on-security, D-3 clamp) | `962a23da` |
| T-65-03 | FR3/D-7 — `agent-model-policy-v1` schema + overlay store (atomic + `.last-good.json`; missing→None ≠ invalid→typed error) | `962a23da` |
| T-65-04 | FR10 — backlog doctor YAML-parse misdiagnosis fix (`frontmatter_error` capture + dedicated BL-SCHEMA finding) | `962a23da` |
| T-65-05 | FR11/D-8 — e2e harness-toggle flake hardening (armed `waitForResponse` on the save PUT; 20/20) | `962a23da` |
| T-65-06 | FR1/D-5 — generic (model-less) core agent sources; plugin bodies → `claude-sonnet-5` | `962a23da` |
| T-65-07 | FR1 — reader tolerance for model-/effort-less generic bodies (`effort` allowlisted) | `962a23da` |
| T-65-08 | FR5/D-3/D-6 — `render_claude_agent` seam + render-at-install both harnesses; fail-closed core codex render (F-3); `--force` re-renders (F-5); plugin effort asymmetry (F-6) | `962a23da` |
| T-65-09 | FR7/D-6 — policy-aware doctor (claude-md render-compare, F-1/F-2) + resolved-roster model-resolution rework | `962a23da` |
| T-65-10 | FR8 — feature service + container wiring (resolved-roster source tagging; apply = validate → save → re-render) | `962a23da` |
| T-65-11 | FR8 — API endpoints (GET/PUT `/api/agent-model-policy`, GET `/api/agent-model-templates`, POST validate; 415/413/400 pipeline) | `962a23da` |
| T-65-12 | FR8/G-2 — Sub-agents tab UI (roster pickers, template selector, Apply, post-apply pop-up); 7-tab DOM contract | `962a23da` |
| T-65-13 | FR9/AC-7 — contract-test rework (template pinning a–g; mutation-sanity verified) | `962a23da` |
| T-65-14 | AC-6 — panel e2e `agent-policy.spec.ts` (4 journeys, 20/20 stability) + hermetic-harness CI fix (amendment) | `962a23da` (fix `9a77abc3`) |
| T-65-15 | AC-1..AC-10 — golden + AC re-verification sweep at merge-base `d2b94585`; 7-tab `tab-navigation.spec.ts` truth update | `962a23da` |
| T-65-16 | AC-11/D-1 — propagate to this instance (`stage`/`install --target all`/`doctor` exit 0) + live panel check; D-1 live retier | (instance-only, CLI) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path).
Gate evidence captured on the ship tree and merged as PR #124 (`962a23da`).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-10 full suite green | `pytest -p no:cacheprovider -q` (unpiped, real exit) | **4941 passed, 0 failed, 18 skipped** — T-65-15, `962a23da` |
| AC-10 format + lint clean | `ruff format --check .` · `ruff check --no-cache .` | 842 files formatted (0 diff); all checks passed — T-65-15 |
| AC-10 types clean | `mypy --strict dadaia_workspace/` | Success, no issues in 319 source files — T-65-15 |
| AC-10 import contracts | `lint-imports --config setup.cfg --no-cache` | **9 kept / 0 broken** (no features→infrastructure edge; core additions pure) — T-65-15 |
| AC-1 generic core sources | `grep -rn "^model:\|^effort:" dadaia_workspace/public/agents/` | 0 hits (core bodies model-agnostic); projected `.claude/agents/*.md` carry both keys post-install — T-65-15 |
| AC-2 balanced default renders in lockstep | `test_install_with_no_overlay_renders_balanced_roster_in_lockstep` | PASS — both projections render the exact `balanced` roster; codex efforts follow D-3 |
| AC-3 overlay precedence (per-field merge) | `test_overlay_change_moves_claude_md_and_codex_toml_in_lockstep` + resolver unit + e2e override journey | PASS ×3 — SE model from override, effort from template |
| AC-4 validation rejects (5 classes) | `test_api_agent_policy.py` (validate) + `test_json_agent_model_policy_store.py` (parse) | PASS — unknown agent/model/effort/template + Fable-on-security each a distinct message, at store parse AND `POST /validate` |
| AC-5 policy-aware doctor (3 directions + F-2) | `test_doctor_ok_after_policy_rerender_drift_on_hand_edit_nonagent_untouched` | PASS — `[ok]` after Apply; `[drift]` on hand-edited `.claude/agents/*.md`; non-agent stage/runtime lines untouched; ERROR on invalid overlay, `[ok]` on missing |
| AC-6 panel Sub-agents tab | `agent-policy.spec.ts` (Playwright, isolated port) | 4/4 journeys PASS; `--repeat-each=5` → 20/20; mutation-sanity RED (Apply-PUT sabotage → 2 fails) captured then reverted |
| AC-7 mutation-sanity | resolver-precedence flip + one-entry `balanced` mutation | resolver flip → 5 unit fails incl. the AC-3 merge test; `balanced` one-entry mutation → contract test fails — T-65-13, re-confirmed via T-65-14 |
| AC-8 FR10 acceptance | `test_frontmatter_yaml_parse_error.py` | PASS (4 tests) — parse-error diagnostic names line/column; no misdiagnosis; valid files byte-identical findings |
| AC-9 FR11 acceptance | `workflow-policy-harness-toggle.spec.ts --repeat-each=10` | 20/20 PASS — deterministic save wait |
| Frozen v0.1.50 no-steal suite | `git diff` vs merge-base on the lease/gate test files | **zero-diff** — no lease/steal test touched — T-65-15 |
| Golden triage at merge-base | `git diff` every `tests/**/_golden` vs `d2b94585` | only genuine truth: `doctor_all_four_v0158.json` + `plugin_doctor_report_golden_{a,b}_v0160.json` each +1 line (`[ok] stage:schemas/agent-model-policy-v1.schema.json`); api/panel/install goldens byte-identical — no silent re-baseline — T-65-15 |
| AC-11 instance propagation | `dadaia public stage` · `install --target all` · `public doctor` | all exit 0 incl. `[ok] public-privacy` + `[ok] model-resolution`, no agent `[drift]` post-render; balanced roster live on `.claude/agents` + `.codex/agents` — T-65-16 |
| AC-11 live panel check | `dadaia panel` (registered on 4999) | Sub-agents tab live; `/api/agent-model-templates` + `/api/agent-model-policy` verified (`applied_template=balanced`, resolved sources=template) — T-65-16 |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVED** — full battery green; hermetic harness verified |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED ×2** — sha `45f65df1`, re-keyed `9a77abc3` after the CI fix |
| CI (PR #124) | GitHub Actions | all checks green on `962a23da` incl. the E2E panel leg on the hermetic harness |

## Drifts

### hermetic-panel-e2e-harness-and-instance-mutation-footgun (T-65-14 CI-fix)

**Description:** the GHA `E2E panel (Playwright)` job on PR #124 failed all 4
`agent-policy.spec.ts` journeys with HTTP 500 on their seed/Apply PUT. The Apply path re-renders
L1 projections (`public install(..., only="agents")`); the panel resolves `workspace_root` by
walking up from its own process cwd at startup. The e2e harness launched the panel with
`webServer.cwd: REPO_ROOT` paired with `.github/scripts/bootstrap-panel-ws.sh`, which wrote
`.dadaia/states/spec_contexts.json` **at that same checkout root** — making `workspace_root ==
the source-repo root`, which the `_is_source_repo_root` production guard correctly refuses.
Production behavior was **CORRECT**; the harness was not hermetic. The dual symptom was worse
locally: the same walk-up escaped the (unpolluted) checkout and found the developer's own
enclosing real dadaia-workspace instance, silently re-rendering its live `.claude/agents/*.md`.

**Resolution:** hermetic harness, root cause, **no production Python touched** (and
`DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL=1` was considered and rejected — it would keep polluting
the source checkout and hide the local instance-mutation footgun). New
`tests/e2e/panel/run-panel-e2e-server.sh` builds a disposable temp workspace (never the repo
root, never an enclosing real workspace), inits it, symlinks `repos/dadaia-workspace` to THIS
checkout (read-only self-repo consumption), stages+installs a real projection INTO the temp
workspace, and execs the panel there. `playwright.config.ts`'s `webServer.command` now runs this
script (env-overridable); default port moved 4999 → **5065** (4999 is the conventional
operator-local live panel port, kept in lockstep in `helpers.ts`). `ci.yml`/`release.yml`
e2e-panel legs dropped the "Bootstrap panel workspace" step and the hardcoded `--port 4999`
override; the now-dead `.github/scripts/bootstrap-panel-ws.sh` was **deleted** (both workflows
were its only callers), and `tests/contract/test_ci_workflow_hygiene.py` was repointed to the
new anti-duplication invariant (neither workflow may override `PANEL_WEB_SERVER_COMMAND`; the
single `playwright.config.ts` default is the only place naming the harness script). RED was
reproduced honestly outside CI (a directory satisfying the exact `_is_source_repo_root`
predicate → HTTP 500 with the guard message); GET/PUT verified 500→200 against the new harness;
full local `pytest` green; full panel e2e **58/58** (incl. `spec-context-operation-journey`
running for real under a pinned `PANEL_E2E_WS`/`PANEL_TEST_REGISTRY`). Confirmed the operator's
live workspace was never touched (`find .claude/agents .codex/agents .dadaia/agentic -newermt
<session-start>` returned zero across the whole session).

**Memory updates:** `specs/memory/quality-assurance.md` (the e2e-panel bootstrap description
now names the hermetic `tests/e2e/panel/run-panel-e2e-server.sh` + the temp-workspace/self-repo
model + the `test_ci_workflow_hygiene.py` anti-duplication invariant; `bootstrap-panel-ws.sh`
references removed; the clickAndAwaitPut / armed-`waitForResponse` deterministic-PUT law
recorded).

### tab-navigation-truth-update-7-tabs (T-65-12/T-65-15)

**Description:** the pre-FR8 panel had 6 tabs; `test_index_dom_contract.py`,
`test_views_index.py`, `tab-navigation.spec.ts` (E2E-TAB-01/03/04) and `helpers.ts`'s tab union
pinned that 6-tab list, and `E2E-TAB-01` failed once the Sub-agents tab landed.

**Resolution:** genuine rendered-truth change, not a re-baseline: the DOM contract `_SECTIONS`,
the tablist/tabpanel contracts, the E2E tab-list pins, and `helpers.ts activateTab` were all
updated to the 7-tab truth (`Sub-agents` beside `Workflows`). Each change reflects the FR8 tab
actually existing — the never-re-baseline-to-hide-a-bug rule holds.

**Memory updates:** `specs/memory/product/panel/panel.md` (6 tabs → 7 tabs; Sub-agents tab +
endpoints; hash-routing/nav notes).

### spec-doctor-schema-asset-golden-line (T-65-09/T-65-15)

**Description:** the new FR3 schema asset `public/schemas/agent-model-policy-v1.schema.json`
stages, so three doctor goldens each gained exactly one `[ok] stage:` line.

**Resolution:** genuine truth from the added asset (multiset diff = exactly one added line per
golden), regenerated deliberately; all other goldens byte-identical at merge-base.

**Memory updates:** none — golden bytes, not product truth.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in `_archive/`.
All edits landed in this CLOSURE phase (MEMORY gate open), **rebased on the v0.1.64 closed
state** (each atom read before editing; no sibling truth reverted — the dispatch_band rename,
handoff v1.2 family, and `--harness auto` default all preserved). `release_origin: v0.1.65` +
`last_updated: 2026-07-08` set on every edited atom. **Catalog regen required** (PM follow-up:
`dadaia memory catalog generate`) — `tldr` changed on `panel`.

- `specs/memory/product/agents/agent-orchestration.md` — **primary.** NEW "Layer-1 agent model
  governance" section: model-agnostic sources, the 3 built-in templates (`balanced` default /
  `subscription-saver` / `max-quality`), overlay `agent-model-policy-v1` + single resolver
  precedence (override > template > default), render-at-install both harnesses, the D-7
  never-Fable-on-security law (three enforcement layers), and the D-1 live retier (this instance
  runs `balanced`: `claude-fable-5` now only on `project-manager` + `software-architect`). The
  two-tier-axes section updated: plugin default `claude-sonnet-4-6` → `claude-sonnet-5`; the
  F-4 note that registry `Tier` is a model-cost-axis label **decoupled from dispatch-band and
  agent behavior** (core-agent codex effort now comes from the D-3 clamp of the resolved policy
  effort, not from `codex_effort_for_tier`); the contract-test pointer now pins template
  contents, not a per-file roster.
- `specs/memory/tech-stack.md` — **primary.** "Model assignments" rewritten to the
  template+overlay+resolver model with `balanced` as the no-overlay default (roster table
  updated: fable-5 only PM+architect; opus on PE/auditor/security/code-reviewer; sonnet-5 on
  ai-engineer/software-engineer/qa-engineer), the codex `model_reasoning_effort` now from the
  resolved per-agent effort via the D-3 clamp (`low→low, medium→medium, high→high, xhigh→high,
  max→high`), and the `claude-sonnet-5` registry entry (`gpt-5.3-codex`, tier `plugin`, pricing
  3.00/15.00/3.75/0.30 eff 2026-07-01) with the F-4 forced-cost-class note; plugin agents
  `claude-sonnet-4-6` → `claude-sonnet-5`.
- `specs/memory/product/panel/panel.md` — **7th tab (Sub-agents)**: roster with per-agent
  model+effort pickers + template selector + explicit Apply (validate → save overlay →
  re-render both L1 projections) + post-apply pop-up; endpoints `GET/PUT /api/agent-model-policy`,
  `GET /api/agent-model-templates`, `POST /api/agent-model-policy/validate`; tab count 6 → 7 in
  tldr/summary/Purpose/usage-flow; hash-routing `#subagents`.
- `specs/memory/product/distribution/public-asset-distribution.md` — install is now
  **render, not copy** for core agents: `render(staged generic body + resolved policy)` →
  `.claude/agents/<name>.md`, same resolved config feeds the codex projection; `public doctor`
  is policy-aware (claude-md render-compare against the resolved policy; missing overlay →
  `balanced`, invalid → ERROR); the staging manifest still hashes staged (policy-free) bytes;
  new staged asset type entry `agent-model-policy-v1.schema.json`.
- `specs/memory/quality-assurance.md` — the e2e-panel bootstrap now names the hermetic
  `tests/e2e/panel/run-panel-e2e-server.sh` (temp-workspace + self-repo symlink) replacing the
  deleted `.github/scripts/bootstrap-panel-ws.sh`; the `test_ci_workflow_hygiene.py`
  anti-duplication invariant; the deterministic-PUT `waitForResponse`/`clickAndAwaitPut` law
  for panel mutation e2e; live-scale bracket refreshed (4,941 passed + 18 skipped at ship).
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` — the backlog doctor BL-SCHEMA note
  gains the frontmatter-YAML-parse-error diagnostic (names line/column and suppresses the
  downstream no-`intents[]`/unresolved findings for the unparseable item) — FR10.
- `specs/memory/architecture.md` — **no change: assessed.** No layer edge, port, or
  module-roster change (lint-imports 9/0 unchanged; the new core template/resolver modules are
  pure `core/` leaves; the store is `infrastructure/`; the panel service takes the store via
  DI). No structural design change to record.
- `specs/memory/product/catalog.json` — PM regen (`dadaia memory catalog generate`) picks up
  the `panel` tldr delta.

## Dispositions

Disposition sweep per the ADR-11 vocabulary — the one consumed backlog item (SPEC §6) + the two
picked LOW bugs. **Bug-always-solved honored**: both bugs shipped fixed (FR10/FR11), neither
superseded; each received a `resolved` terminal event stamped `v0.1.65`.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/l1-agent-model-governance-panel.md` | backlog | `delivered` (`delivered_in: v0.1.65`) | FR1..FR9, `962a23da`; flipped this closure; PM `git mv` → `specs/_archive/releases/v0.1.65/consumed-backlog/` |
| `backlog-doctor-yaml-parse-misdiagnosis` (`specs/bugs/20260707T15Z-00.jsonl`) | bug LOW | `resolved --release v0.1.65` | FR10, `962a23da`; AC-8 `test_frontmatter_yaml_parse_error.py` (4 tests); terminal event appended `v0.1.65` |
| `e2e-panel-harness-toggle-ci-flake` (`specs/bugs/20260707T18Z-00.jsonl`) | bug LOW | `resolved --release v0.1.65` | FR11, `962a23da`; AC-9 `workflow-policy-harness-toggle.spec.ts` 20/20; terminal event appended `v0.1.65` |

**Consumed-backlog ledger** written at `specs/releases/v0.1.65/consumed-backlog/consumed_backlog.json`
(PE writes it under the live release dir; PM `git mv`s the whole dir to `_archive` at archive).
Per the v0.1.60+ precedent the ledger carries **delivered items only** — the two bug
dispositions live in this CLOSURE + their JSONL terminal events, never in the ledger.

## Backlog returns

No new backlog items were discovered during implementation that required filing this closure.
The next-pick debt recorded in `ACTIVE.md` (`dispatch-band-legacy-fallback-removal`,
`platform-seam-todo-retirement`, `specs-doctor-partial-archive-invariant`) is unchanged by this
release. Two forward pointers from the SPEC/grill stay tracked as out-of-scope:

- The registry `plugin` **Tier-NAME** mismatch for `claude-sonnet-5` (D-2/F-4: the `plugin`
  literal is a forced cost-class label decoupled from dispatch-band and behavior) — the
  tier-rename remains a backlog return, unfiled here (assessed: not yet valuable enough to file
  as a standalone item; the F-4 memory note in `tech-stack.md` + `agent-orchestration.md`
  records the decoupling so no reader misreads the label).
- `dispatch-band-legacy-fallback-removal` (already a candidate from v0.1.64) still owns the
  `_raw_to_dto` legacy `tier:` fallback strip — untouched by this release per SPEC out-of-scope.

## Deviations

**None.** No plugin-scope deviation applies: this release touched no plugin-domain surface that
required an uninstalled pack's agent (the `frontend-design`/`devops` packs remain stubs;
`plugin-scope` routing is unchanged, and G-4 handled plugin agents via a pack-provided
`claude-sonnet-5` default + override capability without needing the packs installed). The
retired plugin-scope deviation class (pre-`dadaia plugin install`) does not arise.

## Archive decision

**MOVE** — `specs/releases/v0.1.65/` moves to `specs/_archive/releases/v0.1.65/` via `git mv`
(PM/operator; PE issues no git mutations and runs no shell). PM then executes, in order:

1. `git mv` the delivered backlog file `l1-agent-model-governance-panel.md` →
   `specs/_archive/releases/v0.1.65/consumed-backlog/` (the `consumed_backlog.json` PE wrote
   under `specs/releases/v0.1.65/consumed-backlog/` moves with the release dir).
2. append the two `resolved --release v0.1.65` bug terminal events (if not already appended by
   the implementation waves) via `dadaia bugs append`.
3. `dadaia memory catalog generate` (**required** — `tldr` changed on `panel`).
4. `dadaia specs doctor` + `dadaia backlog doctor` (both must exit 0).
5. the release-dir `git mv specs/releases/v0.1.65 specs/_archive/releases/v0.1.65`.
6. advance `ACTIVE.md` → `release: none`, `phase: none`, noting the next-pick debt
   (`dispatch-band-legacy-fallback-removal`, `platform-seam-todo-retirement`,
   `specs-doctor-partial-archive-invariant`).

**Order law honored: the memory rebase + this disposition sweep land BEFORE `ACTIVE.md` leaves
CLOSURE; the catalog regen (step 3) runs BEFORE the ACTIVE advance (step 6).**
