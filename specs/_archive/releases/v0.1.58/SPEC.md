# SPEC — v0.1.58 — Harness & Projection Distribution

**Status:** Aprovado
**Branch:** `feature/v0.1.58` (base: v0.1.57 closure — the orchestrator branches after `Aprovado`)
**Origin:** R10 of the operator-approved 12-release plan; **second** release of the operator's R9→R12
continuation mandate (2026-07-04). The projection/install machinery matures after the structural chain
(R6 import-boundaries → R7 decomposition → R8 verb-governance → R9 injection-canon). This release makes
**harness isolation** — documented as a first-class concept in the `memory/product/harness/` atoms since
v0.1.47 — mechanical at `init` time, and repairs the consumer-repo `AGENTS.md` fan-out that is dead by
construction.
**Definition-time inspection** (product-engineer code read, 2026-07-04) — every claim below is a read fact
from the current post-v0.1.57 source, not a restatement of the backlog dossiers (several dossier claims are
stale or imprecise and are corrected in §9).
**Release-definition grill** (mandatory, from-backlog) run on the picked set before this SPEC —
`.dadaia/reports/dadaia-workspace/product-engineer/2026-07-04T143000Z-refine-specs-v0158.html`.
**Consumes:** backlog `harness-isolation-profiles` (2 intents) + `consumer-agents-md-fanout-redesign` (1).
**Bug debt at pick:** none (ledger 0).
**Dual definition review 2026-07-04 (qa-engineer REJECT Q1–Q7 + software-architect REJECT A1–A7 — folded):** all
amendments are folded into this Draft with grep-able `(Q#)`/`(A#)` reconciliation markers. PM binding rulings on
the architect's three decision points are recorded in §9 (Ruling K = A2 REPOINT, Ruling L = A5 LIB-OWNED,
Ruling M = A6 DOCTOR-BEFORE-INSTALL). QA/architect re-verify before `Aprovado`.

## 1. Problem

Harness isolation is a first-class *documentation* concept (the `memory/product/harness/` atoms describe
"what a claude-only / codex-only / pi-only workspace installation contains") but it is not *mechanical*:
`dadaia init` has no way to scaffold a single-harness workspace, harness identity is scattered as bare
string literals with no typed Layer-1/Layer-2 capability model, and the consumer-repo `AGENTS.md` fan-out
that should keep repo copies fresh never fires because its trigger contradicts the repo-cleanliness law.

**Read facts (source, 2026-07-04):**

1. **No typed L1/L2 harness capability model.** `core/harness_models.py#harnesses()` returns ONLY the
   Layer-2 *model-catalog* harness names `(pi, codex)` — it does not know `claude` and carries no L1/L2
   capability typing. `AgentRuntimeKind` (`core/models/lifecycle.py`) is the runtime-*adapter* roster
   `{FAKE, CODEX_EXEC, CLAUDE_SDK, PI_HEADLESS}`, not the entry-harness set. The L1 entry-harness roster
   `{claude, codex, pi}` is encoded as bare literals — the tuple/set `("claude","codex","pi")` appears at
   `features/panel/views/api_workflows.py:70`, `api_agents.py:161`,
   `infrastructure/public_assets_common.py:20` (`_VALID_TARGETS`), `infrastructure/public_assets.py:275`,
   and JS `views/assets/js/runtime.js:22`. (Raw grep: 103 `"claude"/"codex"/"pi"` occurrences across 35
   files — most are *legitimate per-harness code*, see §9 for the stale-count correction.) **(A2)** The L2
   worker roster `{"codex","pi"}` is ALSO forked as three bare `_LAYER2_HARNESSES` Python literals at
   `features/lifecycle/policy_doctor.py:77`, `features/lifecycle/policy_resolver.py:136`, and
   `infrastructure/json_workflow_model_policy_store.py:54` — Python-importable, in FR1 scope by Ruling B's own
   criterion, and missed by the PE's original enumeration. A **fourth** occurrence,
   `features/lifecycle/model_profiles.py:112`, is NOT a bare literal — it already *derives* from
   `harness_models.CODEX_HARNESS`/`PI_HARNESS` (the L2 model-catalog constants); it is reconciled by a
   contract test rather than repointed (FR1).

2. **`dadaia init` cannot scaffold a single harness.** `cli/commands/init.py` exposes only `--workspace` /
   `--skip-assets`; it calls `WorkspaceService.init` → `public_assets.install(target="all")`.
   `WorkspaceService.init` (`features/workspace/service.py`) unconditionally creates `.claude/` + `.codex/`
   and configures the Claude `settings.json` ctx-inject hook. There is no per-harness selectivity anywhere.

3. **`public doctor` would false-fail a partial install.** `public_assets.doctor()` unconditionally checks
   the Claude `settings.json`, the Codex `hooks.json`/`config.toml`/rules + `.dadaia/hooks/codex-*`
   wrappers, and every `.pi/` file. A claude-only workspace that omits `.codex/`/`.pi/` (the acceptance
   bar's exact structure) would make its own `public doctor` report `[missing]` — the isolation feature is
   internally incoherent without a persisted harness profile that scopes the doctor.

4. **The consumer `AGENTS.md` fan-out is dead by construction.**
   `infrastructure/workspace_guardrail.py#_consumer_repos_for_root` selects a consumer repo only when BOTH
   `<repo>/.dadaia/` AND `<repo>/.dadaia/agentic/` markers exist. The repo-cleanliness law forbids
   `.dadaia/` inside any repo working tree (it corrupts workspace-vs-repo boundary detection), so in a
   compliant workspace the set is always **empty** and the fan-out never fires. `_doctor_guardrail_pair`
   iterates the same function, so marker-less consumer repos are `[skip]`ped — a stale consumer `AGENTS.md`
   is never checked for drift. (v0.1.47 hand-synced `repos/dadaia-workspace/AGENTS.md` once as a sanctioned
   exception precisely because the mechanism was dead.)

5. **The workspace registry is the clean detection source.** `.dadaia/states/spec_contexts.json` (schema
   v2) lists every context with a `repo_slug` + alive/dead state at the workspace level — no in-repo marker
   needed. Deriving `repos/<repo_slug>/` from the registry fixes fact 4 without violating repo-cleanliness.

## 2. Goals

1. A **typed core harness registry** (`core/harness_registry.py`) owning the L1 entry-harness set
   `{claude, codex, pi}`, the L2 worker set `{codex, pi}`, capability typing, and the projection-target
   vocabulary — consumed by the roster-encoding Python literals, under **golden-first** discipline (the
   install/target-resolution behaviour byte-locked before the refactor).
2. `dadaia init --harness <set>` **profiles** that scaffold ONLY the chosen harness projections + register
   hooks per chosen harness (claude-only / codex-only / pi-only / any combination / all).
3. A **persisted harness profile** that makes `public install`-all and `public doctor` **profile-aware** so
   a single-harness workspace is internally coherent (no false `[missing]`).
4. A **consumer `AGENTS.md` fan-out redesign** that detects Spec Context repos via `spec_contexts.json`
   instead of the forbidden in-repo marker, and makes `public doctor` **flag** stale/missing consumer
   copies instead of `[skip]`ping them — the memory/scaffold tri-copy left untouched, the self-repo skip
   retained.
5. **Per-profile sandboxed E2E** (claude-only / codex-only / pi-only / all) asserting the EXACT default
   structure per the operator acceptance bar, extending `tests/e2e/features/test_public_pipeline.py`
   rather than duplicating it, scaffolding via the real CLI.
6. **Defer** the workflow-spawn entry-harness auto-default to a backlog return (the detection seam is
   incomplete for PI — Ruling F).

## 3. Functional requirements

### FR1 — Typed core harness registry (golden-first)

- **Golden capture FIRST (behaviour lock).** Before any refactor, capture goldens of the
  behaviour-bearing surfaces FR1 touches: `public_assets.install()` target resolution for each `--target`
  in `{all, agents, claude, codex, pi}` (the produced `installed` list, path-normalized), and the panel
  runtime-validation outputs (`api_workflows` / `api_agents` accept/reject for `claude`/`codex`/`pi` and a
  bogus value). **(Q2/A4) ALSO capture + commit a golden of `public_assets.doctor()`'s full report list on
  a fully-installed all-four (no-profile) tree** under `tmp_path` + `FileSystemPublicAssetManager`,
  path/version-normalized (v0.1.55), with any clock the output depends on frozen — this is the FR3
  absent-profile back-compat lock (AC-5 asserts byte-equality against it). Commit the goldens.
  Platform-invariant path normalization (v0.1.55 law) applies to every golden carrying `.dadaia/` or
  `repos/` refs. **Fix-the-consumer-never-the-golden.**
- **New registry.** Add `dadaia_workspace/core/harness_registry.py` — a pure `core` leaf (stdlib only, no
  upward import, import-linter clean). It owns:
  - `L1_ENTRY_HARNESSES: tuple[str, ...] = ("claude", "codex", "pi")` — the entry-harness roster.
  - `L2_WORKER_HARNESSES: tuple[str, ...] = ("codex", "pi")` — claude is never L2 (cost bound).
  - `PROJECTION_TARGETS` / `INSTALL_TARGETS` — the `{agents, claude, codex, pi}` + `all` install vocabulary
    (`_VALID_TARGETS` moves here as the single source; `public_assets_common` re-exports for back-compat).
  - Capability typing: a small typed model (e.g. a frozen dataclass or `StrEnum` + capability predicates
    `is_l1(harness) / is_l2(harness) / can_be_workflow_worker(harness)`) so the prose-only "claude is
    L1-only" distinction becomes a typed lookup.
  - `parse_harness_set(value) -> tuple[str, ...]` — parse a comma set / `all` into a validated ordered
    tuple of L1 harnesses, raising a clear error on an unknown name (consumed by FR2).
- **Consume in the roster-encoding literals — L1 AND L2 (Ruling B + Ruling K/A2).** Replace the tuple/set
  literals at the **4 L1 Python sites** in §1 fact 1 + the `public_assets.install` target list with
  registry lookups. **(A2 / Ruling K — REPOINT, PM binding)** ALSO repoint the **3 bare-literal
  `_LAYER2_HARNESSES` L2 sites** — `policy_doctor.py:77`, `policy_resolver.py:136`,
  `json_workflow_model_policy_store.py:54` — to `harness_registry.L2_WORKER_HARNESSES`, making the constant
  genuinely load-bearing NOW (that is FR1's whole point) and killing the L2-roster fork. This is why the L2
  capability surface (`L2_WORKER_HARNESSES`/`is_l2`/`can_be_workflow_worker`) is NOT dead-on-introduction:
  it has real production consumers this release. **The 4th `_LAYER2_HARNESSES` (`model_profiles.py:112`) is
  NOT repointed** — it already derives from `harness_models.CODEX_HARNESS`/`PI_HARNESS`; instead a **contract
  test** asserts `frozenset(harness_registry.L2_WORKER_HARNESSES) == frozenset(harness_models.harnesses())` — ORDER-INDEPENDENT set agreement, since `harnesses()` returns PI-first while `L2_WORKER_HARNESSES` keeps canonical order `("codex", "pi")` (R1) — (the
  model-catalog view), so the identity roster and the model catalog can never silently diverge (the
  `model_registry` key-equality-contract pattern). **OUT of scope (documented residual):** per-harness
  telemetry reader modules (`reader/{claude,codex,pi}.py`), panel display strings, CSS tokens, JS
  (`runtime.js` — cannot import a Python registry; its `VALID_VALUES` array is left as-is), and JSON schema
  enums. FR1's AC-11 ledger enumerates exactly which literals were centralized (7 sites: 4 L1 + 3 L2), the
  model_profiles derived-site reconciliation, and which residual literals remain and why.
- **Single-source law preserved.** `tech-stack.md` "Agent runtimes" remains the roster *doc* single source
  (SPEC-DOC-037); `harness_registry.py` is its *code* embodiment, not a competing doc. `harness_models.py`
  (L2 model catalog) and `AgentRuntimeKind` (runtime-adapter kinds) are unchanged (the contract test locks
  `L2_WORKER_HARNESSES` ⇔ `harness_models.harnesses()` so the two coincident encodings never fork).
- **Anchor note.** `harness_models.py#harnesses` **survives** untouched (it is the L2 model catalog, not
  the identity registry — §9 stale-claim correction) → archival at CLOSURE.

### FR2 — `dadaia init --harness <set>` profiles + persisted profile + harness-aware scaffolding

- **CLI.** Add `--harness <set>` to `dadaia init` (`cli/commands/init.py`). Accepts a comma set of L1
  harnesses (`claude`, `codex`, `pi`) or `all`; default when omitted = `all` (back-compat with the current
  install-everything behaviour). Parsed via `harness_registry.parse_harness_set`; an unknown name raises a
  Click `BadParameter` (**width-independent stderr assert** — the message lands in `result.stderr` with
  exit_code 2; no `mix_stderr` kwarg, per the v0.1.57 QA-atom law).
- **Harness-aware `WorkspaceService.init`.** Thread the chosen harness set into `init`. It creates only the
  chosen harnesses' scaffold: for `claude` — `.claude/` + the `settings.json` ctx-inject hook; for `codex`
  — `.codex/` (+ the `.dadaia/hooks/codex-*` wrappers projected by the install path); for `pi` — the
  `.pi/` projection. Harnesses NOT in the set get no directory and no hook registration.
  `_configure_hook` (the Claude `settings.json` hook) runs only when `claude` is in the set.
- **Persisted profile.** Write the selected set to `.dadaia/states/harness_profile.json`
  (e.g. `{"schema_version": "1", "harnesses": ["claude"]}`). Idempotent; `init` re-run with the same set is
  a no-op. The git chokepoint scripts (`.dadaia/scripts/*` — installed for `{all, claude, codex}` targets)
  follow the existing rule; the profile does not remove the chokepoints (they are harness-independent).
- **Persistence seam — ports-and-adapters, layer-pinned (A1, blocking).** Mirror the `spec_contexts.json`
  precedent exactly, NOT a state-file helper in `core`: (a) a **pure typed model** in `core`
  (`HarnessProfile`: `schema_version` + `harnesses` tuple) plus `parse_harness_set` — **NO I/O in `core`**
  (the `core-no-os-primitives` contract does not ban `json`/`pathlib`, so this discipline is a precedent, not
  a lint catch); (b) the **JSON read/write ADAPTER in `infrastructure/`**, mirroring `json_context_store.py`,
  consumed same-layer by `public_assets.install`/`doctor` (FR3); (c) the **init-time WRITE in
  `features/workspace/service.py`** via an injected `core.protocols` port (the DI pattern the codebase
  mandates) OR inline like the existing `_init_json_file` bootstrap. **Explicitly forbidden:** a new
  `features → infrastructure` import (would push the `features-no-infrastructure` ignore-cap 9→10 and FAIL
  AC-10 "ignore-cap unchanged") and any `infrastructure → features` import (hard `infrastructure-no-upper-layers`
  break). The phrase "core/models/state helper for the profile file" is deleted from the PLAN write-set.
- **Install target derivation.** `WorkspaceService.init` calls `install` once per chosen harness target (or
  passes the profile set to a profile-aware install — FR3), never `target="all"` when a subset is chosen.

### FR3 — Profile-aware `public install`-all + `public doctor`

- **Install-all reads the profile (Ruling D).** `public_assets.install` with no `--target` (and
  `--target all`) installs the **profile set** when `.dadaia/states/harness_profile.json` exists; absent
  profile ⇒ all-four (back-compat, current behaviour preserved). An explicit
  `--target claude|codex|pi|agents` always overrides for that single target regardless of profile.
- **Doctor scopes runtime expectations to the profile.** `public_assets.doctor()` reads the profile and
  checks only the chosen harnesses' runtime expectations: the inline `_compare` projection block — claude
  `settings.json` only when `claude` in profile; codex `hooks.json`/`config.toml`/rules/`.dadaia/hooks/codex-*`
  only when `codex` in profile; the `.pi/` tree only when `pi` in profile. **(Q1, BLOCKING) The codex-parity
  block ALSO gates on `codex in profile`:** `check_codex_drift` (D-CX-1..D-CX-10 — which emits
  `[missing] codex:agents/<name>.toml (D-CX-1)` ×12 for ANY codex-absent tree because it iterates the staged
  `agentic/agents/*.md`, staged regardless of harness) **and** `codex_trust_boundary_info` run only when
  `codex` in profile (absent profile ⇒ run, all-four back-compat). Without this gate a claude-only/pi-only
  `public doctor` emits `[missing] codex:agents/*.toml` and the CLI exits 1 — the operator acceptance bar
  (AC-5/AC-8) would be mechanically UNACHIEVABLE. **Stay unconditional (harness-independent):**
  `check_codex_rule_corpus_reachable` (safe — it early-returns on absent `.codex/agents`), `classify_workflows`,
  `check_agent_skill_refs`, `check_memory_phase_single_source`, the `agents`/`.agents` shared skills, the
  AGENTS.md guardrail pair, the git chokepoint scripts, `_check_public_privacy` (`[ok] public-privacy`), and
  the git-dirty check. Absent profile ⇒ all-four (back-compat, byte-identical to the Q2/A4 doctor golden).
- **(A3, blocking) Out-of-profile runtime present on disk is NEVER silent.** When a runtime directory OUTSIDE
  the profile physically EXISTS on disk (an operator hand-installed `.codex/`, or an all-four workspace was
  later re-profiled), the doctor must emit a non-silent line — minimum `[warn] <harness>: out-of-profile
  runtime present (drift unchecked)`, or (preferred) still run the drift comparison and emit `[drift]`/`[ok]`
  while noting it is out-of-profile. Pure silence (zero lines) is reserved ONLY for a harness whose directory
  is genuinely absent. This closes the trade-a-false-`[missing]`-for-a-hidden-`[drift]` hole: a stale
  out-of-profile `.codex/` must not read green.
- **Coherence + the "green" definition (Q7).** "Green" is mechanically: the `doctor()` **report list contains
  no `[missing]`/`[drift]`/`[fail]` line for the profile's out-of-scope harnesses** AND, when asserted via the
  CLI, `dadaia public doctor` **exits 0**. A claude-only workspace's `public doctor` reports `[ok]` for the
  claude projection, emits NO `[missing] codex:agents/*.toml (D-CX-1)` line, and exits 0 (the F5 blocker fix).
  Each AC states which surface it asserts (report list vs CLI exit).

### FR4 — Consumer `AGENTS.md` fan-out redesign (spec_contexts.json detection)

- **Detect via the registry (Ruling G).** `_consumer_repos_for_root` is **KEPT BY NAME** and reimplemented:
  it reads `.dadaia/states/spec_contexts.json`, derives `repos/<repo_slug>/` for each context whose
  directory exists on disk (alive OR dead — Ruling H), and drops the in-repo `.dadaia/agentic/` marker
  requirement entirely. Contexts listed in the registry but absent under `repos/` are skipped silently (no
  error). The `_is_self_repo` skip is **RETAINED** — the dadaia-workspace source tree keeps its hand-synced
  `AGENTS.md` (the v0.1.47 exception persists).
- **Fan-out fires.** `_install_guardrail_pair` (`scope="all"` / `"repos-only"`) now writes the workspace-law
  `AGENTS.md` + 1-line `CLAUDE.md` stub to each detected on-disk consumer repo root, hash-compare
  (overwrite only on SHA mismatch). Behaviour for the workspace root is unchanged.
- **(A5 / Ruling L — LIB-OWNED, PM binding) The consumer-repo ROOT `AGENTS.md` is lib-originated canonical.**
  This merely restates the existing root-`AGENTS.md` header law ("Do not put project-specific instructions
  here — put them in a scoped `AGENTS.md`/`CLAUDE.md`"). Operator/repo customization lives ONLY in nested
  subtree `AGENTS.md` (e.g. `repos/<slug>/src/AGENTS.md`), which the fan-out **never touches**. A divergent
  (hand-edited) consumer root `AGENTS.md` is **restored to canonical** — but the restoration must be
  **visible, never a silent `[ok]`**: `_write_pair` emits a DISTINCT line for an overwrite-of-divergent
  (e.g. `[updated] <path> (overwrote divergent workspace-law copy)`), separate from the `[ok]` fresh-create
  line, so the operator always sees a restoration happened. The root file is git-tracked (recoverable), and
  the safe first write is tied to the doctor-before-install ship ordering (Ruling M / A6).
- **Doctor flags stale/missing (Ruling J).** `_doctor_guardrail_pair` iterates the same registry-derived
  on-disk repos and emits `[drift]`/`[missing]`/`[ok]` per consumer `AGENTS.md`/`CLAUDE.md` — never
  `[skip]` for a real consumer repo. Labels stay `repos/<slug>:AGENTS.md` / `repos/<slug>:CLAUDE.md`.
- **Tri-copy untouched (Ruling I).** This FR touches ONLY the root workspace-law fan-out
  (`public/data/AGENTS.md` → root + `repos/<slug>/AGENTS.md`). `specs/AGENTS.md`, `specs/memory/AGENTS.md`,
  and their `public/scaffold/**` sources are not touched (the v0.1.48 tri-copy trap).
- **Root-law wording NOT reworded.** The "governs production source" doctrine (§9 F6) is a law-text edit
  needing operator approval; this release preserves current fan-out semantics (repo-root = workspace-law
  copy; repo-specific rules live in nested subtree `AGENTS.md`).
- **Anchor note.** `_consumer_repos_for_root` **survives** (kept by name, reimplemented) → archival at
  CLOSURE.

### FR5 — Per-profile sandboxed E2E (operator acceptance bar)

- Extend `tests/e2e/features/test_public_pipeline.py` (or a sibling module reusing its helpers +
  `FileSystemPublicAssetManager`) with per-profile E2Es that **scaffold via the real CLI**. **(Q4 — pinned
  mechanism)** scaffold **in-process** via `CliRunner.invoke(app, ["init", "--harness", X, "--workspace",
  tmp])` — **NOT a subprocess** (keeps width-independent stderr, no `shutil.which('dadaia')` console-script
  resolution across 3 OSes, no env-isolation cost). Stage the asset set **ONCE** and reuse it across the 4
  profiles via a shared fixture (avoid re-staging ×4). **Wall-time budget:** the 4-profile matrix stays under
  ~30s combined (a stated budget the reviewer can hold the suite to); `tmp_path` isolation from the repo (no
  `.dadaia/` inside any repo) + `pytest -p no:cacheprovider`. Assert the EXACT default structure:
  - **claude-only** — `.claude/` present with agents/skills/rules + the ctx-inject hook in
    `settings.json`; NO `.codex/`, NO `.pi/`; `public doctor` green under the persisted profile.
  - **codex-only** — `.codex/` present (agents/config/rules/hooks.json) + `.dadaia/hooks/codex-*` wrappers;
    NO `.claude/` agents projection, NO `.pi/`; `public doctor` green.
  - **pi-only** — `.pi/` post-trust projection present; NO `.claude/` agents, NO `.codex/`; `public doctor`
    green.
  - **all-harness default** — the existing all-harness structure (the current E2E, retained), asserting the
    default (no `--harness`) is still all-four and its `public doctor` green.
- The E2E asserts the persisted `.dadaia/states/harness_profile.json` matches the requested set and that
  the profile-scoped `public doctor` is coherent for each profile.

### FR6 — Defer the workflow-spawn entry-harness auto-default (backlog return)

- No code delivered this release. File `workflow-spawn-entry-harness-autodefault` at CLOSURE (via PM
  curation). Rationale (Ruling F): clean entry-harness detection is incomplete — there is no PI session env
  var (`core/session_env.py` carries only `CLAUDE_CODE_SESSION_ID` + `CODEX_SESSION_ID`), and Claude is
  L1-only so never a valid `--harness`; a correct default needs its own design.

## 4. Non-goals

- **No harness removal / re-scaffold-drop (Ruling E).** Re-scaffolding an existing workspace to DELETE a
  harness's projection (`.codex/` etc.) is deferred — this release delivers additive init-time selection
  only.
- **No workflow-spawn auto-default (FR6 / Ruling F).** Deferred to a backlog return.
- **No wider literal sweep (Ruling B).** Per-harness telemetry readers, panel display, CSS/JS, and JSON
  schema enums keep their harness strings; only the roster-encoding Python literals are centralized.
- **No tri-copy change (Ruling I).** The memory/scaffold `AGENTS.md` copies are untouched.
- **No root-law rewording (F6).** The "governs production source" doctrine is not edited.
- **No lease/gate/spec_context change.** This release lives in `core/harness_registry.py` (new),
  `cli/commands/init.py`, `features/workspace/service.py`, `infrastructure/public_assets.py` +
  `public_assets_common.py` + `workspace_guardrail.py`, the 2 panel view modules, and their tests. It does
  NOT enter `spec_context`/lease/gate. The v0.1.50 frozen no-steal suite is expected **zero-diff** (§6).
- **No constitution change; no roster change.** The roster `{claude, codex, pi}` / `{codex, pi}` is
  unchanged — FR1 only *types* it. No `constitution.md` edit.
- **No new dependency.** Registry + profile are stdlib JSON + typed data.

## 5. Acceptance criteria

- **AC-1 (golden-first behaviour lock — RED-safe):** goldens of `public_assets.install()` per-target
  resolution (`{all, agents, claude, codex, pi}`, the produced `installed` list path-normalized) + the
  panel runtime-validation accept/reject outputs + **(Q2/A4) `public_assets.doctor()`'s full report list on
  a fully-installed all-four (no-profile) tree** are captured and committed **before** the FR1 registry
  refactor (the doctor golden also precedes the FR3 refactor). After the FR1 refactor the install/panel
  goldens are **byte-identical** (registry lookups reproduce every literal's behaviour); the doctor golden is
  the FR3 absent-profile back-compat lock. Platform/version-invariant normalization (v0.1.55) on every
  path-bearing golden, with any clock the doctor output depends on frozen.
- **AC-2 (typed registry is the single source — L1 AND L2):** `core/harness_registry.py` exists as an
  import-linter-clean `core` leaf; `L1_ENTRY_HARNESSES == ("claude","codex","pi")`,
  `L2_WORKER_HARNESSES == ("codex","pi")`; `is_l2("claude")` is False and `can_be_workflow_worker("claude")`
  is False; the **4 L1** roster-encoding Python literals + `public_assets` target list resolve through the
  registry, and **(A2/Ruling K) the 3 L2 `_LAYER2_HARNESSES` sites** (`policy_doctor.py:77`,
  `policy_resolver.py:136`, `json_workflow_model_policy_store.py:54`) resolve through
  `harness_registry.L2_WORKER_HARNESSES` — a grep proves the tuple/set literals are gone from all 7 sites, so
  `L2_WORKER_HARNESSES` has real production consumers (not dead-on-introduction). A **contract test** asserts
  `frozenset(L2_WORKER_HARNESSES) == frozenset(harness_models.harnesses())` — order-independent; `L2_WORKER_HARNESSES` keeps canonical order `("codex", "pi")` (R1) — (reconciling the derived 4th site
  `model_profiles.py:112`). `parse_harness_set("codex,pi")` and `parse_harness_set("all")` return the
  validated ordered tuples and `parse_harness_set("bogus")` raises with a listing message.
- **AC-3 (`init --harness` scaffolds exactly the chosen set — RED-first):** `dadaia init --harness claude`
  in a `tmp_path` produces `.claude/` + the ctx-inject hook in `settings.json` and **no** `.codex/`/`.pi/`;
  `--harness codex,pi` produces `.codex/` (+ `.dadaia/hooks/codex-*`) + `.pi/` and **no** `.claude/`
  agents; `--harness` omitted produces all-four (back-compat). RED-first: pre-fix `init` always produced
  all-four regardless. A bad `--harness zzz` exits `exit_code == 2` with `"zzz"`/`"harness"` in
  `result.stderr` and empty `result.stdout` (width-independent; no `mix_stderr` kwarg).
- **AC-4 (persisted profile):** after `init --harness codex`, `.dadaia/states/harness_profile.json` records
  `["codex"]`; re-running `init --harness codex` is idempotent (no spurious rewrite / no second hook entry).
  Absent profile file (a pre-v0.1.58 workspace) is treated as all-four.
- **AC-5 (profile-aware install-all + doctor — RED-first):** in a claude-only workspace,
  `public install` (no target) installs only the claude projection (a codex/pi projection is NOT written),
  and `public doctor` is **green** (Q7 definition: report list has no `[missing]`/`[drift]`/`[fail]` line for
  the out-of-profile harnesses AND CLI exits 0) with `[ok]` for the claude projection. **(Q1)** the report
  list contains **NO `[missing] codex:agents/*.toml (D-CX-1)` line** and no `[missing]` for `.codex/`/`.pi/`.
  RED-first: pre-fix `public doctor` reports `[missing]` codex/pi lines (incl. the D-CX-1 ×12 `codex:agents`
  lines) for a claude-only tree and the CLI exits 1. **(Q2/A4)** the **absent-profile** doctor path asserts
  **byte-equality against the AC-1 all-four doctor golden** (not merely "all-four checked" prose), proving
  back-compat for every pre-v0.1.58 workspace. **(A3)** a claude-only profile with a **stale `.codex/hooks.json`
  physically on disk** produces a **non-silent line** (`[warn] codex: out-of-profile runtime present` or a
  `[drift]`), never green-with-zero-lines. An explicit `--target codex` in the same workspace still installs
  codex (override), asserted.
- **AC-6 (consumer fan-out fires via registry — RED-first):** with a fixture workspace whose
  `spec_contexts.json` names a context `demo` and a real `repos/demo/` dir (no in-repo `.dadaia/` marker),
  `install` (scope="all") writes `repos/demo/AGENTS.md` (workspace-law) + `repos/demo/CLAUDE.md` (stub).
  RED-first: pre-fix (marker-based) the fan-out writes nothing (marker-less repo `[skip]`ped). A context in
  the registry with no on-disk `repos/<slug>/` is skipped without error. The self-repo (dadaia-workspace
  source) is skipped. `specs/memory/AGENTS.md` and `specs/AGENTS.md` are NOT written by the fan-out.
  **(A5/Ruling L)** a **divergent (hand-edited) `repos/demo/AGENTS.md`** is **restored to canonical** and
  `_write_pair` emits the **DISTINCT** `[updated] ... (overwrote divergent workspace-law copy)` line (not a
  silent `[ok]`); a **nested subtree `repos/demo/src/AGENTS.md` is left UNTOUCHED** (operator customization
  is confined to nested scoped files).
- **AC-7 (doctor flags stale/missing consumer copies — RED-first):** `public doctor` on the AC-6 fixture,
  with `repos/demo/AGENTS.md` deliberately stale, the returned `doctor()` **report list** contains
  `[drift] repos/demo:AGENTS.md`; with it absent, `[missing] repos/demo:AGENTS.md`; with it fresh,
  `[ok] repos/demo:AGENTS.md`. **(Q5 — anchor corrected)** RED-first: pre-fix, the returned doctor **report
  list contains NO `repos/demo:AGENTS.md` line at all** — the marker-less repo is dropped by
  `_consumer_repos_for_root` (`workspace_guardrail.py:49`), which writes only a **stderr `[skip]`** line that
  never enters the persisted report list (`_doctor_guardrail_pair` itself never emits `[skip]`). The
  post-fix registry-based `_consumer_repos_for_root` includes `repos/demo`, so the `[drift]`/`[missing]`/`[ok]`
  line appears in the report list.
- **AC-8 (per-profile E2E — operator acceptance bar):** the sandboxed E2E scaffolds **(Q4)** in-process via
  `CliRunner.invoke(app, ["init","--harness",X,"--workspace",tmp])` (no subprocess) for each of claude-only /
  codex-only / pi-only / all, staging the asset set ONCE via a shared fixture reused ×4, under the stated
  ~30s wall-time budget + `tmp_path` isolation + `pytest -p no:cacheprovider`. It asserts the EXACT default
  structure (FR5 bullet list) + the persisted `.dadaia/states/harness_profile.json` matching the requested
  set + a profile-scoped **green** `public doctor` **(Q7:** no `[missing]`/`[drift]`/`[fail]` for
  out-of-profile harnesses AND CLI exit 0**)**. It extends `test_public_pipeline.py` (reuses
  `FileSystemPublicAssetManager` / its helpers), it does not duplicate the all-harness pipeline test.
- **AC-9 (mutation-sanity per new test — sabotage → FAIL → revert):** (a) point one L1 roster-encoding
  literal back at a hard-coded tuple that omits `pi` ⇒ AC-2 registry-consumption grep/behaviour test FAILS;
  **(a′/A2)** point one repointed L2 site (`policy_resolver.py:136`) back at a bare `{"codex","pi"}` literal ⇒
  the AC-2 L2-consumption grep test FAILS; (b) make `WorkspaceService.init` ignore the harness set (always
  all-four) ⇒ AC-3 claude-only test FAILS; (c) make `public_assets.doctor()` ignore the profile (always
  check all-four inline block) ⇒ AC-5 claude-only green test FAILS with a `[missing]` codex line;
  **(c′/Q1)** leave `check_codex_drift` unconditional (not gated on `codex in profile`) ⇒ AC-5 claude-only
  green test FAILS with a `[missing] codex:agents/*.toml (D-CX-1)` line; **(c″/A3)** make the doctor emit
  ZERO lines for an out-of-profile runtime that exists on disk ⇒ the AC-5 stale-`.codex/`-on-disk non-silent
  test FAILS (reads green); (d) restore the in-repo `.dadaia/agentic/` marker requirement in
  `_consumer_repos_for_root` ⇒ AC-6 fan-out-fires test FAILS (nothing written); **(e/Q5 — corrected)**
  restore the in-repo-marker filter in `_consumer_repos_for_root` ⇒ AC-7 `[drift]` test FAILS (the
  `repos/demo:AGENTS.md` line disappears from the report list); **(f/Q6)** with the (b) init sabotage active
  (init ignores the harness set), the **claude-only E2E (AC-8) FAILS** (its "NO `.codex/`, NO `.pi/`"
  assertions break). Each captured on its task line, then reverted.
- **AC-10 (full gates):** `ruff format --check`, `ruff check --no-cache`, `mypy --strict`, the full
  **unpiped** `pytest` (real exit), `lint-imports --no-cache` (`8 kept, 0 broken`; ignore-cap UNCHANGED
  unless a justified edge is added and documented — the new `core/harness_registry.py` is a `core` leaf and
  must add **no** new import edge), `dadaia specs doctor` (exit 0), `dadaia backlog doctor` (exit 0). The
  ship wave runs `dadaia public stage` → `dadaia public doctor` (surfaces every consumer write target, recorded) → `dadaia public install --target all` → confirming `dadaia public doctor` (doctor-before-install, Ruling M) (R2)
  (`[ok] public-privacy`, exit 0). Public assets must stay GENERIC (no operator-local data —
  public-privacy law).
- **AC-11 (surviving/dead behavior ledger, per wave — file-enumerated, Q3):** each wave records a ledger on
  its task line that names **concrete files + fates** (not a generic description); every move/rename/repoint
  grep includes `tests/` **and** non-import textual references. **No** implementation-wave commit stages any
  `specs/backlog/**` (dead/surviving anchors are dispositioned at CLOSURE, but the discipline holds).
  **(A2)** the FR1 ledger enumerates the **7 centralized sites** (4 L1 + 3 L2: `policy_doctor.py:77`,
  `policy_resolver.py:136`, `json_workflow_model_policy_store.py:54`), the `model_profiles.py:112`
  derived-site contract-test reconciliation, and the residual literals kept (Ruling B). **(Q3)** the
  file-enumerated fate ledger MUST name at least: W1 — `tests/unit/features/panel/test_api_golden.py` +
  `_golden/api_golden_v0155.json` (**SURVIVE byte-identical, INVARIANT** — reproduced from the registry-backed
  views; a byte diff is **adjudicated as INVARIANT, never regenerated to mask a behaviour change**),
  `test_api_workflows.py` + `test_api_agents.py` (SURVIVE), `test_public_assets.py` `_VALID_TARGETS` import
  (SURVIVE via re-export); W3 — `test_public_doctor_parity.py`, `test_doctor_projected_drift.py`,
  `test_public_assets.py` doctor cases (SURVIVE byte-identical on the absent-profile path via the Q2/A4
  doctor golden); W4 — `test_workspace_guardrail_pair.py` + `test_public_doctor_parity.py`'s
  `test_doctor_emits_four_labels_with_one_consumer` (**INVERT** the marker-bearing consumer fixture → a
  registry-listed marker-less consumer, keep the `[ok]`×4 assertions).
- **AC-12 (self-hosting drift reconciled — doctor-before-install, A6/A7):** because this release changes the
  projection *package code* (not a `public/**` asset — the fan-out/registry/doctor logic lives in
  `dadaia_workspace/`), the ship wave runs **(A6/Ruling M — surface-before-write)** `stage` → **`public
  doctor`** (which enumerates every `repos/<slug>:AGENTS.md` `[drift]`/`[missing]` write target across the
  **(A7) alive OR dead on-disk context repos minus the self-repo `dadaia-workspace`**) → PM records the
  surfaced consumer write set in the ship evidence (an in-session checkpoint, not an operator halt) →
  **`install`** → confirming `public doctor`. AC-12 asserts the **PRE-install doctor surfaced every consumer
  target** and that no divergent consumer repo was overwritten without first appearing in that pre-install
  surface (an overwrite emits the distinct `[updated]` line, A5). Confirms `[ok] public-privacy`, the
  v0.1.50 frozen no-steal suite zero-diff. Instance files are never hand-edited — drift is reconciled only
  via stage/doctor/install/doctor.

## 6. Consumed backlog

| Item | Kind | Priority | Consumed → FR | Anchor fate |
|---|---|---|---|---|
| `harness-isolation-profiles` | backlog (candidate) | MEDIUM | typed registry → FR1; `init --harness` profiles + persisted profile + harness-aware scaffold → FR2; profile-aware install/doctor → FR3; per-profile E2E → FR5; workflow-spawn auto-default → FR6 (deferred) | Anchors `harness_models.py#harnesses` (survives, untouched — §9), `init` (survives, gains `--harness`) → **CLOSURE** |
| `consumer-agents-md-fanout-redesign` | backlog (candidate) | MEDIUM | registry-based detection + doctor flagging → FR4 | Anchors `workspace_guardrail.py#_consumer_repos_for_root` (survives, reimplemented, KEPT BY NAME — Ruling G) → **CLOSURE** |

**Archival timing.** Both consumed anchors SURVIVE (kept by name / untouched) → dispositioned + archived at
CLOSURE. No dead anchor this release → no SHIP-time archival. Discipline: **no `specs/backlog/**` staged in
W1–W6** (AC-11).

**Frozen-suite check — NO interaction.** The v0.1.50 no-steal lease/gate suite
(`tests/unit/features/spec_context/test_lease_*`, `test_gate_policy.py`) is untouched: this release lives in
`core/harness_registry.py` (new), `cli/commands/init.py`, `features/workspace/service.py`,
`infrastructure/public_assets*.py`, `infrastructure/workspace_guardrail.py`, the 2 panel views, and their
tests — it enters no `spec_context`/lease/gate path. Expect **zero** frozen-file diff. `init`/scaffolding
tests do not overlap the frozen suite; if any init test is found to touch a gate-adjacent fixture, flag it
for adjudication in the wave ledger.

## 7. Risks

- **Golden brittleness / over-normalization (FR1).** A golden capturing a host path would false-fail the
  refactor. Mitigation: v0.1.55 platform-invariant normalization on every path-bearing golden; capture
  under a fixed `tmp_path` + `FileSystemPublicAssetManager`.
- **`public doctor` false-fail regression (FR3).** The doctor is a wide, unconditional check today; making it
  profile-aware risks masking a genuine drift. Mitigation: absent profile ⇒ all-four (no behaviour change
  for existing workspaces); AC-5 asserts both the claude-only green path AND the explicit-`--target`
  override; the shared surfaces (agents/skills, AGENTS.md pair, chokepoint scripts, public-privacy) stay
  unconditional.
- **Fan-out clobbers a custom consumer root `AGENTS.md` (FR4 / A5 / Ruling L).** Broadening WHICH repos get
  the workspace-law copy could overwrite a hand-authored root `AGENTS.md`. Resolution (A5/Ruling L, PM
  binding): the consumer-repo ROOT `AGENTS.md` is **lib-owned canonical** (restating the root-`AGENTS.md`
  header law); operator customization lives ONLY in nested subtree `AGENTS.md` (never touched); a divergent
  root copy is **restored to canonical** but the overwrite emits a **distinct `[updated]` line** (never a
  silent `[ok]`), tested by an AC; fan out ONLY to registered Spec Context repos; the self-repo skip is
  retained; the doctor-before-install ordering (A6) surfaces every write target before the first write.
- **Self-hosting instance write at ship (AC-12 / A6 / A7).** After merge, the live instance's `public install`
  will fan the workspace-law `AGENTS.md` to **alive OR dead on-disk context repos minus the self-repo**
  (~12 real repos per the live `spec_contexts.json`) — a mechanism that was DEAD until this release.
  Mitigation (Ruling M): the ship wave runs `stage` → `public doctor` **BEFORE** `install` to surface every
  `repos/<slug>` write target for PM review, then `install`, then a confirming doctor; the self-repo
  `dadaia-workspace` is skipped; a divergent consumer overwrite emits the distinct `[updated]` line (A5);
  instance files are reconciled via stage/doctor/install/doctor, never hand-edited.
- **Entry-harness detection incompleteness (FR6).** Deferring is the honest call because PI has no session
  env var. Mitigation: recorded ruling + backlog return; no speculative seam shipped.
- **lint-imports edge from the new `core` module (FR1).** A `core` leaf that imports upward would break the
  contract. Mitigation: `harness_registry.py` is stdlib-only, imported by `infrastructure`/`features`/`cli`
  downward; AC-10 asserts `8 kept / 0 broken`, ignore-cap unchanged.

## 8. Memory files affected at CLOSURE

- `specs/memory/product/distribution/public-asset-distribution.md` — **primary edit.** The install/doctor
  chain becomes harness-profile-aware; the consumer `AGENTS.md` fan-out detects via `spec_contexts.json`
  and doctor flags stale/missing consumer copies (no more `[skip]`). Assess `tldr`/`summary`/`area`
  (regenerate `catalog.json` + `index.md` only if they change; keep the regenerated `tldr` within the
  established length cap). `release_origin` → v0.1.58.
- `specs/memory/product/platform/workspace-init.md` — **edit.** `dadaia init --harness <set>` profiles +
  the persisted `.dadaia/states/harness_profile.json`; init is now harness-selective. `release_origin` →
  v0.1.58.
- `specs/memory/product/harness/harness-claude-code.md` / `harness-codex.md` / `harness-pi.md` — **edit.**
  The "what a X-only workspace installation contains" descriptions become mechanically real via
  `init --harness` + the profile; add a one-line note that isolation is now enforced at init, not just
  documented. `release_origin` → v0.1.58 on each edited atom.
- `specs/memory/product/platform/multi-platform-parity.md` — **assess/edit.** The L1 entry-harness set
  `{claude, codex, pi}` is now typed in `core/harness_registry.py`; note the registry as the code
  embodiment of the roster. Confirm the tech-stack single-source law is preserved.
- `specs/memory/architecture.md` — **edit.** The module map gains `core/harness_registry.py` (typed L1/L2
  roster, consumed by the 4 L1 + 3 L2 sites), the `HarnessProfile` core model, and the infrastructure JSON
  profile adapter (mirroring `json_context_store.py`); the workspace/init + public_assets + workspace_guardrail
  descriptions update (profile-aware install/doctor, registry-based consumer detection). Note the persistence
  seam is ports-and-adapters (no new features→infra / infra→features edge; ignore-cap unchanged). Feature
  count unchanged. `release_origin` → v0.1.58 if edited.
- `specs/memory/tech-stack.md` — **assess.** "Agent runtimes" stays the roster doc single source; add a
  pointer to `core/harness_registry.py` as its typed code embodiment ONLY if it clarifies (keep the
  roster wording canonical). Likely a small pointer edit or no-change-confirm.
- `specs/memory/quality-assurance.md` — **assess.** FR1 introduces install/target-resolution goldens + the
  per-profile E2E law; if the golden-authoring / real-CLI-scaffold E2E pattern needs a note, add it.
  Confirm.

## 9. Definition rulings (grill, operator-unavailable — OPERATOR-OVERRIDABLE)

The operator is unavailable mid-flow; the code-unanswerable decisions are pre-ruled here with rationale and
marked overridable. Full evidence: the grill report cited in the header.

- **Ruling A — NEW `core/harness_registry.py`, not an edit to `harness_models.harnesses()`.** Identity lives
  in a new typed core leaf; `harness_models.py` (L2 model catalog) + `AgentRuntimeKind` (adapter kinds) are
  unchanged. **Override:** fold identity into `harness_models.py`.
- **Ruling B — FR1 is scoped to the roster-encoding Python literals** (4 tuple/set sites + the install
  target list); per-harness readers, panel display, CSS/JS, and schema enums keep their strings (documented
  residual). **Override:** wider sweep in a follow-up.
- **Ruling C — `init --harness <set>` is a flag accepting a comma set / `all`** (default all); the chosen
  set is persisted at `.dadaia/states/harness_profile.json`. No separate config-file source this release.
  **Override:** also honor a `pyproject`/config source.
- **Ruling D — the persisted profile is the source of truth for install-all + doctor scope;** explicit
  `--target X` overrides; absent profile ⇒ all-four (back-compat). **Override:** keep `--target all`
  literally all.
- **Ruling E — harness removal / re-scaffold-drop is OUT of scope** (additive init-time selection only).
  **Override:** pull removal into scope.
- **Ruling F — the workflow-spawn entry-harness auto-default is DEFERRED to a backlog return**
  (`workflow-spawn-entry-harness-autodefault`); PI has no session env var, Claude is L1-only. **Override:**
  a codex-only best-effort default now.
- **Ruling G — fan-out detects via `spec_contexts.json`; `_consumer_repos_for_root` KEPT BY NAME,
  reimplemented** (anchor survives → CLOSURE, no mid-branch dead-anchor). **Override:** rename it.
- **Ruling H — fan to every on-disk context repo (alive OR dead) minus the self-repo;** the self-repo skip
  is retained. **Override:** alive-only.
- **Ruling I — the memory/scaffold `AGENTS.md` tri-copy is OUT of scope;** FR4 touches only the root
  workspace-law fan-out.
- **Ruling J — `public doctor` flags stale/missing consumer copies (never `[skip]`);** root-law wording is
  not reworded this release. **Override:** clarify the law.

- **Ruling K — A2 REPOINT (PM binding, 2026-07-04).** The 3 bare-literal `_LAYER2_HARNESSES` sites
  (`policy_doctor.py:77`, `policy_resolver.py:136`, `json_workflow_model_policy_store.py:54`) repoint to
  `harness_registry.L2_WORKER_HARNESSES`, making the constant load-bearing NOW (that is FR1's whole point);
  the 4th derived site (`model_profiles.py:112`) is reconciled by a contract test, not repointed. Rationale:
  a single load-bearing L2 source kills the fork and removes the "typed surface introduced only to be tested"
  anti-slop concern. Operator-overridable (the alternative — defer the whole L2 capability surface to the
  FR6 backlog-return — was rejected by PM).

- **Ruling L — A5 LIB-OWNED (PM binding, 2026-07-04).** The consumer-repo ROOT `AGENTS.md` is lib-owned
  canonical (restating the existing root-`AGENTS.md` header law); operator customization lives in nested
  scoped `AGENTS.md`, never touched by the fan-out; a divergent root copy is restored to canonical with a
  DISTINCT visible output line (`[updated]`, not silent `[ok]`); tested by an AC. Operator-overridable at PR
  review.

- **Ruling M — A6 DOCTOR-BEFORE-INSTALL (PM binding, 2026-07-04).** The W6 self-hosting ship order is
  `stage` → `public doctor` (surfaces every `repos/<slug>` write target) → PM reviews the surfaced list
  in-session and records it in the ship evidence → `install` → confirming `public doctor`. The review is an
  in-session recorded checkpoint, NOT an operator halt (flow never stops; the operator can override at PR
  review).

- **A1/A3/A4/A7 folded (not decision points — architect-required corrections).** A1: the persistence seam is
  pinned to ports-and-adapters (core model + `parse_harness_set` NO-IO; infrastructure JSON adapter; service
  write via port/inline; no new features→infra or infra→features edge) — FR2. A3: an out-of-profile runtime
  present on disk is never silent (`[warn]`/`[drift]`) — FR3 + AC-5. A4: the FR3 absent-profile doctor
  back-compat is byte-locked against the Q2/A4 doctor golden, not prose — AC-1/AC-5. A7: the blast radius is
  "alive OR dead on-disk context repos minus self-repo" — AC-12 + Risk.

- **Stale-claim corrections (dossier vs source).** (1) `harness-isolation-profiles` cites
  `harness_models.py#harnesses` as the harness-identity seam — it is the Layer-2 *model catalog* (pi,
  codex), unaware of claude; the fix is a NEW registry, not an edit to that function. (2) "61+ scattered
  literals ... replace with typed lookups" — raw count is 103 across 35 files, but most are legitimate
  per-harness code (telemetry readers, panel display, CSS/JS, schema enums); FR1 centralizes only the
  roster-encoding Python literals — **7 sites: 4 L1 + 3 L2** (the PE's original count missed the 3 L2
  `_LAYER2_HARNESSES` sites; corrected via A2/Ruling K) plus the `model_profiles.py:112` contract-test
  reconciliation (Ruling B). (3) The dispatch hint that `core/session_env.py` (v0.1.55) is
  a harness-identity seam is imprecise — it resolves harness-native *session-id* env vars, and is relevant
  only as evidence that PI has no entry-harness env signal (Ruling F). (4) The `consumer-agents-md-fanout`
  entry is otherwise accurate — every claim in it is verified against source (§1 fact 4/5). (5) Neither
  entry surfaces the `public doctor` false-fail blocker (F5) — FR3 resolves it.
