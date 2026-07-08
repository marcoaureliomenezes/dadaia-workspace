# SPEC — Release v0.1.65 — L1 Agent Model Governance & Panel Sub-agents Tab

> **Status:** Aprovado
> **Release ID:** v0.1.65
> **Owner:** product-engineer
> **Branch:** `feature/v0.1.65`
> **Opened:** 2026-07-07
> **Grill:** mandatory session held 2026-07-07; rulings G-1..G-5 + inspection decisions
> D-1..D-8 recorded in
> `.dadaia/reports/dadaia-workspace/product-engineer/2026-07-07T193000Z-refine-v0165.html`

## Objective

Mirror the proven Layer-2 workflow model-governance architecture for the Layer-1 agent
roster: generic (model-agnostic) agent sources, a library-shipped template registry, an
operator overlay store, a single resolver, render-at-install for BOTH L1 projections
(`.claude/agents/*.md` + `.codex/agents/*.toml`), a policy-aware `public doctor`, and a
new panel **Sub-agents** tab with explicit Apply. Plus two open LOW bugs fixed
(bug-always-solved law).

## Picked set

| Item | Kind | Disposition in this release |
|---|---|---|
| `specs/backlog/l1-agent-model-governance-panel.md` | backlog (HIGH) | delivered — FR1..FR9 |
| `backlog-doctor-yaml-parse-misdiagnosis` (`specs/bugs/20260707T15Z-00.jsonl`) | bug LOW open | fixed — FR10 |
| `e2e-panel-harness-toggle-ci-flake` (`specs/bugs/20260707T18Z-00.jsonl`) | bug LOW open | fixed — FR11 |

No bug is superseded; both get `resolved` terminal events at CLOSURE.

## Operator rulings (settled — do not re-litigate)

- **G-1** — `balanced` has Fable 5 ONLY on project-manager + software-architect. Fable is
  **NEVER** assigned to security-reviewer (cyber-safety classifiers can refuse
  security-review-shaped work). Hard constraint in every template AND in overlay
  validation.
- **G-2** — Explicit Change→Apply: PUT saves the overlay + triggers re-render of both L1
  projections; post-apply pop-up gives per-harness instructions (Claude: live sessions
  auto-pick-up within seconds on next delegation — code.claude.com/docs/en/sub-agents;
  exception: a brand-new agents dir created mid-session needs restart. Codex: restart the
  session).
- **G-3** — ONE policy governs BOTH L1 projections; codex model id + reasoning effort
  derive from the SAME resolved config.
- **G-4** — Templates cover the 9 core agents only. Plugin agents get a pack-provided
  default (`claude-sonnet-5`) + override capability only when their pack is installed.
- **G-5** — Three templates: `balanced` (default), `subscription-saver`, `max-quality`
  (full rosters in FR2).

## Inspection decisions

- **D-1** — The 2026-07-06 hardcoded retier (5-Fable roster) is superseded by the
  `balanced` template as the no-overlay default; this instance's projections change at the
  propagation wave (operator-ratified via G-1/G-5).
- **D-2** — `claude-sonnet-5` registry entry: `codex_id="gpt-5.3-codex"`,
  `tier="plugin"`, pricing `(3.00, 15.00, 3.75, 0.30, effective 2026-07-01)`. Rationale:
  registry `Tier` is the model-cost axis; sonnet-5 shares sonnet-4-6's cost class, and any
  other tier violates `_codex_id_for_tier` / `codex_tier_views` invariants. The `plugin`
  tier-NAME mismatch is a backlog return, out of scope.
  **Addendum (review F-4):** `tier="plugin"` for sonnet-5 is a **forced cost-axis label,
  decoupled from dispatch-band and agent behavior** — core-agent codex effort comes from
  the D-3 clamp of the resolved policy effort, NOT from `codex_effort_for_tier`, so the
  tier label no longer drives core-agent effort. Flagged for a CLOSURE memory note
  (`tech-stack.md` + `agent-orchestration.md`) pending the tier-rename backlog return.
- **D-3** — Claude effort vocabulary is `low|medium|high|xhigh|max` (rendered
  frontmatter). Codex `model_reasoning_effort` derives from the RESOLVED per-agent effort
  via the fixed clamp map: `low→low, medium→medium, high→high, xhigh→high, max→high`.
  `CodexEffort` stays 3-valued.
- **D-4** — Layering: templates + pure resolver live in **core** (import-linter:
  `infrastructure-no-upper-layers` forbids infrastructure→features; the install pipeline
  must consume the resolver). Feature-facing service stays in `features/` with the store
  injected via DI (`features-no-infrastructure`).
- **D-5** — Plugin pack agent bodies keep authored frontmatter as the pack default
  (`model: claude-sonnet-5`, no effort); per-agent overlay overrides layer on top when the
  pack is installed.
- **D-6** — A single render seam `render(staged generic body, resolved (model, effort))`
  is shared by install-write, doctor-compare, and panel Apply. The staging manifest keeps
  hashing STAGED bytes (staging stays policy-free); only projection write/compare goes
  through the render seam.
- **D-7** — never-Fable-on-security-reviewer is enforced at three layers: template
  import-time assert, overlay store/parse validation, panel validate endpoint.
- **D-8** — FR11 is fixed test-side (deterministic PUT wait); a production fix is added
  only if implementation falsifies the test-side diagnosis (then documented as a drift).

---

## Functional Requirements

### FR1 — Generic agent sources

The 9 core `dadaia_workspace/public/agents/*.md` bodies drop their hardcoded `model:` and
`effort:` frontmatter and become model-agnostic templates (`name`, `description`,
`dispatch_band`, `tools`, `skills`, `paths`, etc. stay). The 3 plugin stubs are unchanged.
`features/agents/reader.py#read_canonical_agents` / `_raw_to_dto` and the frontmatter
allowlist tolerate a body carrying neither `model:` nor `effort:` (both remain allowlisted
keys — PROJECTED files still carry them). Does NOT touch the `_raw_to_dto` legacy `tier:`
fallback (owned by `dispatch-band-legacy-fallback-removal`).

**Acceptance:** no staged core agent body contains a `model:` or `effort:` frontmatter
line; reader unit tests cover the model-less body path; projected `.claude/agents/*.md`
DO carry both keys.

### FR2 — Built-in template registry (core)

New `core/agent_model_templates.py` — analog of
`features/lifecycle/model_profiles.py#_BUILT_IN`: a tuple of 3 named
`AgentModelTemplate`s, each a full 9-core-agent map of `(model, effort)`:

| agent | balanced (DEFAULT) | subscription-saver | max-quality |
|---|---|---|---|
| project-manager | claude-fable-5 / high | claude-opus-4-8 / high | claude-fable-5 / high |
| software-architect | claude-fable-5 / high | claude-opus-4-8 / high | claude-fable-5 / high |
| product-engineer | claude-opus-4-8 / high | claude-sonnet-5 / xhigh | claude-fable-5 / high |
| project-auditor | claude-opus-4-8 / xhigh | claude-sonnet-5 / xhigh | claude-fable-5 / high |
| security-reviewer | claude-opus-4-8 / xhigh | claude-opus-4-8 / high | claude-opus-4-8 / xhigh |
| code-reviewer | claude-opus-4-8 / high | claude-sonnet-5 / xhigh | claude-opus-4-8 / xhigh |
| ai-engineer | claude-sonnet-5 / high | claude-sonnet-5 / high | claude-opus-4-8 / medium |
| software-engineer | claude-sonnet-5 / xhigh | claude-sonnet-5 / xhigh | claude-sonnet-5 / xhigh |
| qa-engineer | claude-sonnet-5 / high | claude-sonnet-5 / high | claude-opus-4-8 / high |

Import-time asserts (mirror `_assert_profiles_resolve`, fail loud): every template covers
exactly the 9 core agents; every model is registry-known (`core/model_registry`); every
effort is in `low|medium|high|xhigh|max`; **no template assigns `claude-fable-5` to
security-reviewer** (G-1); no duplicate template id; `balanced` exists and is the default.

### FR3 — Overlay store + schema `agent-model-policy-v1`

New JSON Schema `dadaia_workspace/public/schemas/agent-model-policy-v1.schema.json` and
store `infrastructure/json_agent_model_policy_store.py` at
`.dadaia/states/agent_model_policy.json`, mirroring
`json_workflow_model_policy_store.py`: atomic temp+rename write, `.last-good.json`
backup of the prior valid file, **missing ⇒ `None` (defaults) ≠ invalid ⇒ typed error**.
Document shape:

```json
{
  "schema_version": "agent-model-policy-v1",
  "applied_template": "balanced",
  "overrides": { "<agent-name>": { "model": "<claude-id>", "effort": "<effort>" } }
}
```

Parse validation (hard errors): unknown top-level/override keys; unknown
`applied_template` id; unknown agent name (valid names = 9 core + installed plugin
agents); model not in REGISTRY; effort outside the vocabulary; `security-reviewer` +
`claude-fable-5` in any combination that resolves Fable onto security-reviewer (D-7). An
override may carry `model`, `effort`, or both (per-field).

### FR4 — Single resolver + precedence (core)

Pure function in `core/agent_model_templates.py` (or `core/models/agent_model_policy.py`):
`resolve_agent_model(agent_name, overlay) -> ResolvedAgentModel(model, effort, source)`.
Per-field precedence: **per-agent overlay override > applied template > library default
template (`balanced`)**. Plugin agents (not in templates): **override > pack-provided
default** (staged pack frontmatter, D-5). The resolver is the ONLY precedence
implementation — install, doctor, codex projection, and the panel all consume it.

### FR5 — Render-at-install, both harnesses

`PublicAssetService.install` / `infrastructure/public_assets.py` compose, per core agent:
staged generic body + resolved `(model, effort)` → projected `.claude/agents/<name>.md`
(deterministic frontmatter injection: `model:` then `effort:` appended as the last lines
of the frontmatter block), via `write_generated`-style hash-compare. The codex projection
(`install_codex_agents` + `runtime_transforms/codex_assets.py`) consumes the SAME resolved
config: `model` via the registry codex mapping, `model_reasoning_effort` from the resolved
effort via the D-3 clamp map (replacing tier-only derivation for agents). Installed plugin
pack agents render with override-over-pack-default resolution. No overlay present ⇒
render with `balanced` — deterministic and byte-stable across repeated installs.

Render-contract details (architect review fold):

- **Fail-closed core codex render (F-3).** For a core (non-plugin) agent,
  `install_codex_agents` / `_codex_toml_from_md` MUST raise a loud typed error when
  neither a staged `model:` nor a resolved policy model is supplied — the silent
  `.get("model", "claude-sonnet-4-6")` default is REMOVED for core agents (it survives
  only where a plugin agent legitimately authors `model:` in its pack body). A wiring
  miss must never ship wrong codex models under green tests.
- **`--force` re-renders (F-5).** `--force` clobbers a locally-diverged agent projection
  back to the RENDER output (staged generic + resolved policy) — never to raw staged
  bytes.
- **Plugin effort asymmetry (F-6).** `model:` is ALWAYS emitted. `effort:` is emitted
  only when resolved: core agents always have one (template/override); a plugin agent
  gets `effort:` only when an override supplies it — otherwise the key is OMITTED
  entirely (never empty or placeholder), keeping render output deterministic for the
  doctor render-compare.

### FR6 — `claude-sonnet-5` registry entry

Add to `core/model_registry.py#REGISTRY` per D-2. All existing registry invariants
(`registry_by_claude_id`, `_codex_id_for_tier`, `codex_tier_views`) must keep passing;
`MODEL_MAP` / `PRICING_TABLE` derived views pick it up automatically.

### FR7 — Policy-aware public doctor + model-resolution rework

`dadaia public doctor` validates each projected **`.claude/agents/*.md`** file against
**render(staged generic + resolved policy)** — never raw staged bytes — so an operator
policy change is `[ok]`, and a hand-edited claude projection is `[drift]`.

**Scope narrowing (review F-1 — do not overclaim).** The doctor render-compare guarantee
is **claude-md-only**. Codex agent TOMLs are projected-only (not staged / not
manifest-hashed) and `check_codex_drift` performs structural checks only (presence,
config entries, claude-string leak, empty instructions, boundaries) — it does NOT
byte-compare TOML content, and this release adds NO codex doctor byte-compare (no
`codex_doctor.py` work). Codex-side model/effort correctness is asserted
**install-time** by the T-65-08 lockstep integration test (AC-2/AC-3): a policy change
moves `.claude` md and `.codex` toml together at install, and that is where the codex
projection is verified.
`features/public/model_resolution.py#check_model_resolution` validates the RESOLVED
(model, effort) per core agent against REGISTRY + effort vocabulary (templates assert at
import; a present overlay is loaded and validated — an invalid overlay is a doctor ERROR,
a missing one is not), plus plugin staged frontmatter models; key-set coherence check
unchanged. Manifest contract per D-6: staging manifest hashes staged bytes; the doctor's
projected comparison for agent assets goes exclusively through the render seam.

### FR8 — Panel Sub-agents tab

New tab **Sub-agents** alongside Workflows (nav button + section in
`features/panel/views/index.py`, view module `features/panel/views/agent_policy.py`,
routes in `handler.py`, JS `assets/js/agent_policy.js`, scoped CSS). Endpoints mirror the
L2 workflow-policy views incl. their 415/413/400 validation pipeline and loopback/Host
guards:

- `GET /api/agent-model-policy` → `{exists, policy, resolved}` where `resolved` is the
  full roster of `{agent: {model, effort, source: override|template|default|pack}}`.
- `GET /api/agent-model-templates` → the 3 templates (id, label, default flag, full
  roster) + the selectable model ids (REGISTRY claude ids) + effort vocabulary.
- `POST /api/agent-model-policy/validate` → dry-run, no write.
- `PUT /api/agent-model-policy` → validate → save overlay (atomic + last-good) →
  **trigger re-render of BOTH L1 projections** (agents-only install path) → response
  carries the re-render summary.

UI: roster table (9 core + installed plugin agents) with per-agent model picker + effort
picker (`low|medium|high|xhigh|max`), template selector, explicit **Apply** button
(validate-before-save), and a post-apply pop-up with the G-2 per-harness instructions.
Inline-script changes require recomputing the `_CSP_SCRIPT_HASH_*` sha256 values in
`handler.py` (known trap).

### FR9 — Contract-test rework

`tests/contract/test_agent_tier_taxonomy.py` stops pinning per-file frontmatter roster and
instead pins: (a) the full contents of the 3 built-in templates (the FR2 table, verbatim);
(b) `balanced` is the default; (c) no template assigns Fable to security-reviewer; (d)
every template model resolves in REGISTRY with the expected tier; (e) staged core bodies
carry NO `model:`/`effort:`; (f) plugin pack bodies carry `dispatch_band: 3` +
`model: claude-sonnet-5` (tier `plugin`); (g) roster counts (9 core / 3 plugin) unchanged.

### FR10 — Bug fix: backlog doctor YAML parse misdiagnosis

`features/backlog/preview.py`: `_parse_frontmatter` no longer swallows `yaml.YAMLError` —
the loader captures the parse failure (message + problem-mark line/column when available)
in a new `frontmatter_error` field on `BacklogItem`. `features/backlog/doctor.py`
`_check_schema` emits a dedicated BL-SCHEMA ERROR
`frontmatter YAML parse error: <msg> (line <L>, column <C>)` for such an item and
SUPPRESSES the "no intents[] declared" / unresolved-subject findings for it (they are
downstream of the parse failure). Any other consumer of `load_backlog_items` keeps its
current not-crash behavior.

**Acceptance:** the bug's repro (unquoted `source: text (note: more text)` + valid
`intents[]`) yields the parse-error diagnostic naming line/column and NOT the
no-intents message; well-formed files produce byte-identical findings to today.

### FR11 — Bug fix: e2e harness-toggle CI flake

`tests/e2e/panel/workflow-policy-harness-toggle.spec.ts` becomes deterministic: (a) the
save step arms `page.waitForResponse` for the `PUT /api/workflow-model-policy` (status
200) BEFORE clicking save and awaits it before any GET; (b) `restoreEmptyOverlay` asserts
its PUT returns 200; (c) assertions tolerate the serialized empty-overlay shape (absent
`workflows` key). The stale-validate-banner ambiguity must no longer be the only save
signal. If implementation proves a server-side cause instead, fix it and record the drift.

**Acceptance:** the spec passes 20/20 consecutive local runs; no assertion depends on a
banner class shared between validate and save outcomes.

## Non-Functional Requirements

- **NFR-1 Atomicity:** all overlay writes are temp+rename atomic with `.last-good.json`
  backup; a failed write never corrupts the prior valid overlay.
- **NFR-2 Privacy:** the overlay and schema contain no secrets, no operator-local absolute
  paths, no hostnames; `public/` assets stay generic.
- **NFR-3 Panel posture unchanged:** loopback-only bind + Host-header allowlist + strict
  CSP + nosniff; no auth added; mutations guarded exactly like the existing PUT routes.
- **NFR-4 Determinism:** install with the same (staging, policy) input is byte-stable;
  missing overlay ≠ invalid overlay (missing → `balanced`; invalid → loud typed error,
  never a silent fallback).
- **NFR-5 Layering:** all import-linter contracts in `setup.cfg` keep passing; no
  features→infrastructure edge; core stays I/O-free.

## Acceptance Criteria

- **AC-1** Staged generic sources: `grep -rn "^model:" dadaia_workspace/public/agents/`
  and `grep -rn "^effort:"` return no core-agent hits; projected `.claude/agents/*.md`
  carry both keys after install.
- **AC-2** With no overlay file, install renders the `balanced` roster exactly (FR2
  table) into both projections; `.codex/agents/*.toml` efforts follow D-3.
- **AC-3** Overlay precedence: an overlay with `applied_template: subscription-saver` +
  override `{software-engineer: {model: claude-opus-4-8}}` renders SE=opus-4-8/xhigh
  (model from override, effort from template) and all others per subscription-saver.
- **AC-4** Validation rejects: unknown agent, unknown model, bad effort, unknown
  template, and Fable-on-security-reviewer — each with a distinct actionable message, at
  store parse AND at `POST /validate`.
- **AC-5** `dadaia public doctor` is `[ok]` end-to-end immediately after a policy Apply
  (no false `[drift]`); `[drift]` when a projected `.claude/agents/*.md` is hand-edited;
  and non-agent stage/runtime compare lines stay `[ok]` (untouched by the render seam —
  F-2). The doctor render-compare claim is claude-md-only (F-1): codex TOML correctness
  is asserted install-time by the T-65-08 lockstep integration test, not by a doctor
  byte-compare.
- **AC-6** Panel: template select + Apply persists the overlay, re-renders both
  projections, and shows the post-apply pop-up with the G-2 per-harness text; covered by
  a Playwright e2e spec (roster renders, override round-trips through PUT/GET, pop-up
  appears).
- **AC-7 (mutation-sanity)** With a deliberate local mutation of the resolver precedence
  (template consulted before override) the unit suite FAILS; with a deliberate one-entry
  mutation of the `balanced` template the contract test FAILS. Verified once during the
  contract-test task and recorded in its completion notes — proves the tests exercise the
  production path, not a copy.
- **AC-8** FR10 acceptance (parse-error diagnostic, no misdiagnosis, no regression on
  valid files).
- **AC-9** FR11 acceptance (deterministic save wait; 20/20 local runs).
- **AC-10** Full gates green: `ruff format --check`, `ruff check`, `mypy --strict`,
  `pytest` (unit + contract + integration), `lint-imports`, e2e panel suite; goldens
  referencing agent model frontmatter re-verified (they must reflect rendered-projection
  truth, never re-baselined to hide a behavior change).
- **AC-11** Propagation on THIS instance: `dadaia public stage` + `dadaia public install
  --target all` + `dadaia public doctor` exit 0, and the panel Sub-agents tab is manually
  verified live.

## Out of scope

- Removing the `_raw_to_dto` legacy `tier:` fallback (`dispatch-band-legacy-fallback-removal`).
- Renaming the registry `plugin` Tier literal (backlog return).
- Layer-2 workflow policy changes; per-context `extends` inheritance for the L1 overlay
  (single flat policy this release).
- Operator-authored custom templates (built-in only, like L2 D-2 first release).
- Any change to dispatch bands, personas, or the L2 harness roster.

## Dependencies & risks

- FR5/FR7 depend on FR2/FR3/FR4/FR6. FR8 depends on FR3/FR4/FR5. FR9 depends on FR1/FR2.
- **Risk (highest):** the doctor/manifest seam — a miss produces false `[drift]` on every
  policy change or blinds doctor to hand-edits. Mitigated by D-6 single render seam + AC-5
  both-directions test.
- **Risk:** golden churn (`api_golden_v0155.json`, `panel_runtime_validation_v0158.json`,
  install-target goldens reference `claude-fable-5`/`claude-opus-4-8`) — goldens are
  updated only for genuinely changed rendered truth (platform-invariant normalization law).
- **Risk:** CSP hash trap on panel inline-script edits.
- **Risk:** D-1 changes this instance's live agent tiers at propagation — operator-ratified.

## Memory files affected at closure

- `specs/memory/product/agents/agent-orchestration.md` (L1 model governance, templates,
  never-Fable-on-security law; F-4 note: registry `Tier` is a cost-axis label decoupled
  from dispatch-band and agent behavior)
- `specs/memory/product/panel/panel.md` (7th tab: Sub-agents; new endpoints)
- `specs/memory/product/distribution/public-asset-distribution.md` (render-at-install,
  policy-aware doctor, manifest contract)
- `specs/memory/tech-stack.md` (claude-sonnet-5 registry entry; F-4 note: sonnet-5's
  `plugin` tier is a forced cost-class grouping pending the tier-rename backlog return)
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md` (only if FR10 changes the
  BL-SCHEMA taxonomy description)
- catalog regen (`dadaia memory catalog generate`) before ACTIVE → none.

## Open Questions

None. All spec-time unknowns were resolved by operator ruling (G-1..G-5) or inspection
default (D-2, D-3, D-4, D-5, D-8) as recorded above.

## Revision log

- 2026-07-07 — Definition authored after the mandatory grill (G-1..G-5, D-1..D-8);
  `**Status:** Aprovado`.
- 2026-07-07 — Architect review REVISE folded (report:
  `.dadaia/reports/dadaia-workspace/software-architect/2026-07-07T200000Z-review-v0165-definition.md`).
  F-1 (HIGH): FR7/AC-5 narrowed — doctor render-compare is claude-md-only; codex TOML is
  install-time-asserted (option (a), no new `codex_doctor.py` work). F-2 (MED): doctor
  interception site pinned in TASKS T-65-09 + AC-5 non-agent-lines assertion. F-3 (MED):
  FR5 fail-closed core codex render. F-4 (LOW): D-2 addendum + CLOSURE memory-note flags.
  F-5 (LOW): FR5 `--force` re-renders. F-6 (LOW): FR5 plugin effort asymmetry. F-7
  (LOW/INFO): RED-window push discipline note in TASKS. Status remains Aprovado — this
  revision is the fold of an approved review, no scope change.
