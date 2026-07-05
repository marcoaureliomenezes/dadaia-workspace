# SPEC — v0.1.60 — Capability Tail (plugin packs + Layer-1 model-tier efficiency)

**Status:** Aprovado
**Branch:** `feature/v0.1.60` (base: v0.1.59 closure — the orchestrator branches after `Aprovado`)
**Origin:** R12 of the operator-approved 12-release plan; **final** release of the operator's R9→R12 continuation
mandate (2026-07-04). Pure new capability, zero bug/audit debt: distribute the plugin packs behind a real
`dadaia plugin install <pack>` so the three stub plugin agents carry behavior, then assign Layer-1 model tiers off
uniform `claude-opus-4-8` where safe.
**Definition-time inspection** (product-engineer code read, 2026-07-04) — every claim below is a read fact from the
current post-v0.1.59 source, not a restatement of the backlog dossiers (several dossier premises are stale or a
Layer-2/Layer-1 category error and are corrected in §9).
**Release-definition grill** (mandatory, from-backlog) run on the picked set before this SPEC —
`.dadaia/reports/dadaia-workspace/product-engineer/2026-07-04T220000Z-refine-specs-v0160.html`.
**Consumes:** backlog `plugin-packs-and-install-command` (1 intent) + `model-tier-efficiency-and-fast-tier-utilization`
(2 intents) + **HIGH bug `public-install-clobbers-consumer-repo-agents-md`** (reopened into the pick while SPEC was
Draft — release-governance: bugs are always solved; see §0 + FR9 + ADR-9).
**Bug debt at pick:** one HIGH bug reopened mid-definition (`specs/bugs/20260704T19Z-00.jsonl`, reported
2026-07-04T19:02:47Z by another Layer-1 session) — picked and mapped to FR9. **Audit debt at pick:** none.
**DEFINITION-phase memory correction (PM ruling, done in this phase):** `specs/memory/architecture.md` L63 kanban
"remain served" claim corrected as a dated drift-fix (attributed to the v0.1.52 deletion; no v0.1.60 change implied) —
body-only, no catalog regen (`architecture.md` is a `core` atom absent from `catalog.json`).

## 0. Picked bug (reopened while SPEC Draft)

**Bug:** `public-install-clobbers-consumer-repo-agents-md` (HIGH, `specs/bugs/20260704T19Z-00.jsonl`, reported
2026-07-04T19:02:47Z, `claude-layer1`). PM reopened the pick into R12 while this SPEC was Draft (release-governance —
bugs are always solved).

**Symptom (source-grounded):** `dadaia public install --target all` overwrote a consumer game repo's **hand-authored,
repo-specific** root `AGENTS.md` with the generic workspace `data/AGENTS.md`, and dropped a `CLAUDE.md` `@AGENTS.md`
bridge at the repo root. The clobbered file is **not** in `.dadaia/agentic/manifest.json` (an untracked projection);
the bug reporter confirmed the writer was `public install` because the clobbered content carried the generated
`public/data/AGENTS.md` banner. This is a **data-loss class** (working tree only — recoverable via git, but HIGH).

**Root cause (read fact).** `infrastructure/workspace_guardrail.py#_install_guardrail_pair._write_one` (lines
219–227) treats **any** existing consumer `AGENTS.md` whose SHA differs from canonical as a "divergent workspace-law
copy" and overwrites it (`[updated] ... (overwrote divergent workspace-law copy)`), per v0.1.58 FR4 **Ruling L**
("the consumer-repo ROOT `AGENTS.md` is lib-owned canonical"). It has **no discriminator** between a *stale canonical
projection* and *hand-authored repo content* — both merely "differ from canonical". This conflicts with the workspace
law itself: the root `AGENTS.md` banner says project-specific instructions go in a scoped `AGENTS.md` inside the repo
they govern — i.e. `repos/<slug>/AGENTS.md` **IS** that scoped file, repo-owned, not lib-owned.

**Disposition intent (terminal event at CLOSURE, not now):** `resolved --release v0.1.60` once FR9 lands with its
RED-first test green. The bug maps 1:1 to FR9 + AC-14 + ADR-9. This SPEC records the intent; the JSONL `resolved`
event is appended at T-60-70.

## 0.1 PM binding rulings — dual-review fold (2026-07-04)

Dual DEFINITION review returned BOTH REJECT (software-architect ARCH-1..10 = 1 CRITICAL/6 HIGH/2 MED/1 LOW;
qa-engineer QA-1..8 = 2 HIGH/4 MED/2 LOW). PM binding rulings continuing the ruling sequence past ADR-9 (each folded
in place with greppable `<!-- AMEND:ARCH-n -->` / `<!-- AMEND:QA-n -->` markers). Reports:
`.dadaia/reports/dadaia-workspace/software-architect/2026-07-04T230000Z-v0160-definition-review.md`,
`.dadaia/reports/dadaia-workspace/qa-engineer/2026-07-04T230000Z-v0160-definition-review.md`.

- **Ruling 10 (ARCH-7 + QA-3, FR7 abstraction).** FR7 rides the EXISTING workspace-doctor structured abstraction — a
  new `DoctorIssue(code="EFF-1", fixable=False, description=<staleness age + clearing command>)` (confirmed:
  `cli/commands/doctor.py:33-36` renders `{code} {[fixable]|[manual]} — {description}`, and the workspace doctor
  **never raises `Exit` on issues** → already always exits 0). **NO** new `[warn]` token; **NO** exit-code change.
  ADR-7 amended in place. Test matrix covers absent / fresh / stale / malformed marker; malformed = EFF-1 with a
  "malformed marker" description, never a crash. **PE decision (within the ruling):** *absent* marker ⇒ **no issue**
  (healthy — no baseline yet), so every existing fresh-workspace `dadaia doctor` happy-path test stays green (this is
  what makes QA-3's "existing checks unchanged" provable); EFF-1 fires only on *stale* or *malformed* markers.
- **Ruling 11 (ARCH-6, FR7 writer + cadence).** Cadence default **30 days**, a named constant
  (`EFFICIENCY_AUDIT_STALE_DAYS = 30`). Marker `.dadaia/states/last_efficiency_audit.json`, schema
  `{"schema_version":"1","last_efficiency_audit":"<RFC3339>","by":"<agent>","report":"<workspace-relative path>"}`. A
  deterministic CLI writer MUST exist: **`dadaia reports mark-efficiency-audit --report <workspace-relative-path>
  [--by <agent>]`** — smallest surface (one verb under the existing `reports` group; no new top-level group; the
  marker records that an efficiency report was produced). The warn is clearable in production by running it.
- **Ruling 12 (ARCH-5, FR4 ceiling).** Deliverables enumerated BY NAME with a hard ceiling: per pack — the full agent
  bodies (`frontend-design`: `frontend-engineer` + `design-specialist`; `devops`: `devops-engineer`) + **AT MOST ONE
  skill per pack** + **zero new rules** beyond the FR5 plugin-scope rewrite. **PE-chosen skill names** (grounded in the
  stub domains): `frontend-design` → skill **`browser-frontend-implementation`** (HTML/CSS/TS/React implementation +
  design-spec adherence + visual review; serves both pack agents); `devops` → skill **`github-actions-cicd`** (CI/CD
  pipeline authoring: GitHub Actions workflows, gitflow, deploy gates). Everything else → the already-planned
  `plugin-pack-content-libraries` backlog return.
- **Ruling 13 (ARCH-3 + QA-5, profile×pack).** Pack projection is **profile-scoped EXACTLY like core install** — a pack
  installs only into harnesses present in the active harness profile (absent profile ⇒ all targets, v0.1.58 back-compat);
  `installed_plugins.json` records the pack (**not per-harness**); a later profile change surfaces out-of-profile pack
  assets via the same v0.1.58 **A3 out-of-profile-on-disk never-silent** law. No orphan projections, no doctor split.
  Specified in FR3 with AC-15.
- **Ruling 14 (ARCH-4 + QA-2, goldens).** **TWO goldens**, each with a defined role, both carrying the v0.1.58
  three-leak-class platform normalization (host-state cwd-walk, directory-iteration order, OS-phrased exec text) **from
  day one**: (a) **golden (a)** — W0/W1 pre-change golden of the current doctor/install output captured BEFORE any
  descriptor or refactor lands — locks the pure-core surface through the `public_assets` internal changes; (b) **golden
  (b)** — the "descriptors-present, nothing-installed" golden captured AFTER the descriptors land — THIS is the
  absent-pack byte-lock baseline consumers see post-upgrade. The absent-pack AC is re-worded onto golden (b). **PE
  decision:** golden (a) is the **transient refactor-lock, retired at ship/closure** (its job ends once the machinery
  lands and golden (b) is the durable baseline).
- **Ruling 15 (QA-1, banner reference).** The discriminator is a **module constant** in `workspace_guardrail.py`
  (`_CANONICAL_AGENTS_BANNER`), asserted **byte-equal to the actual generated banner in `public/data/AGENTS.md` by a
  dedicated contract test** (drift in either side fails the contract test; **NO runtime file read of `public/data`**).
  The fate ledger is corrected per QA-1's blast-radius analysis: enumerate the synthetic bannerless-source guardrail
  tests that flip to `[foreign]` (each adjudicated amended-with-rationale), and fix the misattributed pin (the real
  `[updated]`-on-divergent *install* pin is `test_public_assets.py::TestInstallConsumerReposGuardrailPair::test_force_false_overwrites_divergent_consumer_with_updated_line`;
  `test_workspace_guardrail_pair.py` Case 6 `test_doctor_four_line_output` is a doctor-`[ok]`-parity flip, NOT an
  `[updated]` case).
- **Ruling 16 (ARCH-1, CRITICAL).** FR9 extends to the **PAIRED `CLAUDE.md` doctor line** — provenance-aware as a
  pair: hand-authored `AGENTS.md` (no banner) ⇒ **BOTH** lines report `[foreign]`, **no `[missing]`**, `public doctor`
  exit 0; stale-canonical ⇒ the pair is restored/updated as today. AC-14 re-worded to assert the **pair** + exit 0.
- **Ruling 17 (ARCH-9 + ARCH-10 + QA-8).** The tier-taxonomy contract check becomes **MANDATORY** (a named test
  `tests/contract/test_agent_tier_taxonomy.py` in TASKS); the two-"tier" **rename** files as a backlog return
  `tier-taxonomy-rename`; the numeric `tier:` value for the 3 plugin agents is **`3`** (leaf-worker band, consistent
  with the FR6 fix and the core leaf workers).

## 1. Problem

The three plugin agents (`frontend-engineer`, `design-specialist`, `devops-engineer`) ship as behavior-less stubs
(`public/agents/*.md` — `[PLUGIN REQUIRED]` body, `plugin: true` frontmatter, no `model:`), and the `plugin-scope` rule
says "no install command exists." Plugin-domain work therefore routes to the operator, and the v0.1.59
`panel-ux-overhaul` deviation authorized core agents to do browser/UX work only "because no install command exists."
Separately, all 9 core personas resolve to `claude-opus-4-8` (registry tier `dispatch`); the registry's cheaper tiers
are unused by any agent.

**Read facts (source, 2026-07-04):**

1. **The staging pipeline is pre-wired for plugins but dead-on-arrival.** `infrastructure/public_assets_common.py:25`
   `_COPY_DIRS` already contains `"plugins"`, so `stage()` would copy `public/plugins/` into
   `.dadaia/agentic/plugins/` — but `public/plugins/` **does not exist**, `install()`'s per-target loop
   (`public_assets.py:327`) routes nothing from `plugins` to any runtime projection, and `--only plugins`
   (`cli/commands/public.py:36` `_ONLY_CHOICES`) is a **dead option**.

2. **The registry already defines the `fast` and `plugin` tiers.** `core/model_registry.py:50`
   `Tier = Literal["deep","dispatch","fast","plugin"]`; `claude-sonnet-4-6` → `plugin`,
   `claude-haiku-4-5-20251001` → `fast`, `claude-opus-4-8` → `dispatch`, `claude-fable-5` → `deep`. The `fast`/`plugin`
   tiers are cost-priced and codex-effort-mapped (`_CODEX_TIER_EFFORT`), but **no agent is assigned** to them.

3. **The only Layer-1 tiering lever is persona-level `model:` assignment.** The backlog's "mechanical sub-task classes"
   (catalog regen, report validation, formatting, handoff emission) are — by inspection — **deterministic CLI calls
   that carry no model tier** (`dadaia memory catalog generate`, `dadaia reports validate`, `ruff format`) or a
   tail-step (`dadaia-handoff-emitter`) inside a whole-persona dispatch. Layer-1 sub-agents are dispatched as whole
   personas at one `model:`; there is no fine-grained sub-task tiering (that is a Layer-2 step-level concept). §9
   stale-claim correction.

4. **The efficiency-audit rubric exists; the recurring trigger does not.** `public/agents/ai-engineer.md:229`
   ("Prompt efficiency audit protocol") already defines the rubric incl. tier-move recommendations + an efficiency
   report path; it fires **only on demand**. There is **no** `last_efficiency_audit` marker/state anywhere (greenfield).

5. **Two "tier" vocabularies collide.** All 9 core agent frontmatters carry a numeric `tier: 1/2/3` (dispatch/priority
   band) **and** `model: claude-opus-4-8` (registry `Tier` = `dispatch`); the plugin stubs carry neither. The word
   "tier" names two different concepts — a real refinement hazard for the model-tier item.

6. **Constitution §14 is already forward-compatible.** `constitution.md:214` — "Plugins (stubs, behavior-less **until
   their pack installs**...)". No amendment is required.

7. **Layer-1 model flow to each harness.** For Claude the agent `model:` IS the run model; for Codex,
   `runtime_transforms/codex_assets.py` derives `model_reasoning_effort` from `model:` → `registry_by_claude_id()` →
   `codex_effort_for_tier()` (fallback `medium` when `model:` absent — the current stub case). Pack agent bodies must
   therefore carry a real `model:`+`tier:` frontmatter.

## 2. Goals

1. A real **`dadaia plugin install <pack>`** CLI (+ `list`, `doctor`) that distributes the in-package
   `frontend-design` and `devops` packs so the three stub agents carry behavior — **ports-and-adapters** following the
   v0.1.58 `harness_profile` precedent (core model + protocol port + infra JSON adapter + CLI).
2. **In-package pack storage** (`public/plugins/<pack>/`) riding the existing `_COPY_DIRS` "plugins" staging — no
   network, offline-safe, privacy-clean.
3. **Golden-first projection safety:** with no pack installed, core `public install` / `public doctor` stay
   **byte-identical** to today (the same absent-profile byte-lock law as v0.1.58).
4. **Minimal-viable pack content** (Ruling ADR-5): the 3 agents get real bodies + a small essential skill/rule set per
   pack; full skill corpora are a backlog return.
5. The `plugin-scope` rule + `[PLUGIN REQUIRED]` response become **install-gated wording**; the v0.1.59
   `panel-ux-overhaul` plugin-scope deviation class is **retired going forward** (documentation note).
6. Assign Layer-1 model tiers off uniform opus **where safe**: the 3 real plugin agents on the registry `plugin`
   (sonnet) tier (demonstrable off-opus assignment), the `tier: 1/2/3` vs registry-`Tier` divergence documented, and a
   **recurring efficiency-audit trigger** (deterministic staleness marker). The fast/haiku reasoning-persona downgrade
   is **deferred** to a backlog return (no live operator to validate "equal output quality" — Ruling ADR-6).

## 3. Functional requirements

### FR1 — In-package plugin pack storage + layout

- **Layout.** NEW `public/plugins/<pack>/` for two packs: `frontend-design` (agents `frontend-engineer`,
  `design-specialist`) and `devops` (agent `devops-engineer`). Each pack: `agents/<name>.md`, optional `skills/**`,
  optional `rules/*.md`, and a `pack.json` descriptor (`name`, `agents[]`, `skills[]`, `rules[]`, `schema_version`).
  Staged by the existing `_COPY_DIRS` "plugins" entry into `.dadaia/agentic/plugins/<pack>/`.
- **Content owner.** Pack **content** (agents/skills/rules) is authored by `ai-engineer` (exclusive `public/**`
  agent/skill/rule surface); the CLI/machinery is `software-engineer`.
- **Public-privacy law.** Pack content is generic (no operator-local names/paths/IPs) — `public doctor`
  `[ok] public-privacy` must hold.

### FR2 — `dadaia plugin` CLI command group (ports-and-adapters)

- **CLI.** NEW `cli/commands/plugin.py` registered in `cli/main.py`: `install <pack>`, `list` (available + installed),
  `doctor`. `install <bogus>` raises a Click `BadParameter` (**width-independent stderr** — message in
  `result.stderr`, `exit_code == 2`, empty `result.stdout`; no `mix_stderr` kwarg, v0.1.57 QA-atom law).
- **Persistence seam — ports-and-adapters, layer-pinned (v0.1.58 precedent, blocking).**
  (a) a **pure typed `PluginPack` core model** (`core/models/plugin_pack.py`: `name` + `agents`/`skills`/`rules`
  tuples + `schema_version`) — **NO I/O in `core`** (mirrors `HarnessProfile`); (b) a **`PluginStore` protocol port**
  (`core/protocols/plugin_store.py`, read/write the installed-plugins ledger); (c) a **JSON adapter**
  (`infrastructure/json_plugin_store.py`, mirroring `json_harness_profile_store.py`), consumed same-layer by
  `public_assets`. **Forbidden:** any new `features → infrastructure` edge or `infrastructure → features` edge
  (lint-imports ignore-cap UNCHANGED).
- **Install ledger.** `install` records the enabled packs at `.dadaia/states/installed_plugins.json`
  (`{"schema_version":"1","plugins":["frontend-design"]}`); idempotent (re-install same pack = no-op).

### FR3 — Pack projection + manifest + doctor + idempotency + projection precedence

- **Projection.** `dadaia plugin install <pack>` projects the pack's agents/skills/rules from
  `.dadaia/agentic/plugins/<pack>/` into the runtime projections (`.claude/agents|skills|rules`,
  `.codex/agents|skills|rules`, shared `.agents/skills`), hash-compare overwrite (mirrors `public install`).
- **Profile-scoped projection (Ruling 13 / ARCH-3, blocking).** <!-- AMEND:ARCH-3 --> Pack projection, precedence, AND
  plugin doctor scope to the workspace **harness profile** EXACTLY like core `public install --target all` (via the
  same `_profile_harnesses` seam already in `public_assets`): a pack installs only into harnesses present in the
  profile (absent profile ⇒ all targets, v0.1.58 back-compat) — a claude-only workspace projects only the claude agent,
  **never** a `.codex/` orphan. `installed_plugins.json` records the **pack** (not per-harness). A later profile change
  that leaves an out-of-profile pack asset on disk surfaces it via the same v0.1.58 **A3 out-of-profile-on-disk
  never-silent** law (`[warn]`/`[drift]`, never zero lines). No orphan projections; no core-vs-plugin doctor split.
  Asserted by AC-15.
- **Stub replacement (Ruling ADR-4).** A pack agent body **overwrites** the projected core stub
  (`.claude/agents/<name>.md`, `.codex/agents/<name>.toml`) with the pack's real body. The core stub survives in
  `public/agents/` as the un-installed default.
- **Projection precedence (clobber-safety, blocking).** Core `public install` reads `installed_plugins.json` and
  projects the **pack body** (not the core stub) for any installed plugin — so a later `dadaia public install` never
  silently reverts an installed pack agent back to its stub. RED-first: pre-fix, a core `public install` after a plugin
  install re-writes the stub over the real body.
- **Manifest tracking.** Pack-projected files are manifest-tracked (added to the agents manifest or an equivalent
  ledger) so `public doctor` sees them as lib-originated (not stray).
- **Doctor integration + absent-pack byte-lock (golden-first, blocking).** <!-- AMEND:ARCH-4 --> `dadaia plugin doctor`
  (or a folded `public doctor` section) reports `[ok]`/`[drift]`/`[missing]` per installed pack file. **Two goldens
  (Ruling 14 / ARCH-4 / QA-2):** golden (a) locks the pre-descriptor doctor/install surface through the `public_assets`
  refactor (retired at ship); golden (b), the **"descriptors-present, zero-plugin-installed" byte-lock**, is the durable
  post-upgrade baseline — with the pack descriptor source present but no pack installed, `public install` (all targets)
  and `public doctor`'s runtime surface replay byte-identical to golden (b). NOTE: adding the descriptor **source**
  (`public/plugins/**/pack.json`) legitimately adds `stage:plugins/...` parity lines — those are captured **into**
  golden (b) (golden (b) is taken AFTER descriptors land), so they are not a violation; the "installing zero plugins
  changes nothing" claim is scoped to the **runtime-projection + install-set** lines. An installed pack's
  out-of-manifest/stale files are never silent.
- **No uninstall this release (Ruling ADR-2).** Additive-only (mirrors v0.1.58 no-removal). Uninstall → backlog return.

### FR4 — Minimal-viable pack content (Ruling ADR-5)

- **Enumerated deliverable with a HARD CEILING (Ruling 12 / ARCH-5).** <!-- AMEND:ARCH-5 --> Per pack, the deliverable
  is a FIXED list, not a size-open invitation:
  - **`frontend-design` pack:** agent bodies `frontend-engineer` + `design-specialist`; **exactly one** new skill
    **`browser-frontend-implementation`** (HTML/CSS/TS/React implementation + design-spec adherence + visual review;
    serves both pack agents); **zero** new rules.
  - **`devops` pack:** agent body `devops-engineer`; **exactly one** new skill **`github-actions-cicd`** (CI/CD pipeline
    authoring: GitHub Actions workflows, gitflow, deploy gates); **zero** new rules.
  - The only rule change in the release is the FR5 `plugin-scope.md` rewrite. Everything beyond this named list →
    `plugin-pack-content-libraries` backlog return.
- **3 real agent bodies** replacing the stubs, at `public/plugins/<pack>/agents/<name>.md`, each carrying full
  frontmatter (`name`, `description`, numeric `tier: 3` (leaf-worker band — Ruling 17 / ARCH-10), `model:
  claude-sonnet-4-6`, tools) + a real SDD-role body (browser HTML/CSS/JS/TS/React for `frontend-engineer`; UX/UI +
  visual review for `design-specialist`; CI/CD + GitHub Actions + gitflow + deploy for `devops-engineer`).
- **Reuse, don't duplicate.** The existing codex runtime adapters
  `public/runtime/codex/{frontend-ctx,design-ctx}/SKILL.md` are reused (referenced), NOT duplicated by the new pack
  skills.
- **Plugin-agent tier (FR8 / Ruling ADR-8).** Each real plugin agent carries `model: claude-sonnet-4-6` (registry
  `plugin` tier).

### FR5 — plugin-scope rule + `[PLUGIN REQUIRED]` response rewrite (install-gated)

- **Rewrite `public/rules/plugin-scope.md`** (ai-engineer): drop "not yet distributed / no install command exists";
  state that packs are distributed in-package and enabled per workspace with `dadaia plugin install <pack>`; until
  installed in **this** workspace the agents remain stubs and plugin-domain work routes to the operator (or, once
  installed, to the now-real plugin agent). The `[PLUGIN REQUIRED]` response text updates to name the install command.
- **Retire the deviation class (documentation note).** Record that once `dadaia plugin install` ships, the v0.1.59
  `panel-ux-overhaul` plugin-scope deviation is no longer needed for future releases (the past deviation stands as
  recorded). No code change.

### FR6 — Tier-taxonomy divergence fix (INCONSISTENCY)

- **Document the two axes** so the word "tier" stops colliding: the numeric frontmatter `tier: 1/2/3` = agent
  dispatch/priority band; the registry `Tier` literal (`deep`/`dispatch`/`fast`/`plugin`) = model-cost class resolved
  from `model:`. Captured in `specs/memory/tech-stack.md` + `specs/memory/architecture.md` at CLOSURE.
- **MANDATORY machine guard (Ruling 17 / ARCH-9 / QA-8a).** <!-- AMEND:ARCH-9 --> <!-- AMEND:QA-8 --> A **non-optional**
  contract test `tests/contract/test_agent_tier_taxonomy.py` asserts every non-plugin core agent carries **both** a
  numeric frontmatter `tier` **and** a registry-known `model` (and the 3 plugin agents carry `tier: 3` +
  `model: claude-sonnet-4-6`). The collision is machine-enforced NOW, not merely documented.
- **No frontmatter renaming this release** (avoids churn on all 9 agents), but the eventual source-level fix is
  **tracked**: file backlog return **`tier-taxonomy-rename`** (e.g. `tier:` → `dispatch_band:`) so the collision is
  resolved at source in a future release, not forgotten.

### FR7 — Recurring efficiency-audit trigger (Ruling ADR-7 / Rulings 10-11)

<!-- AMEND:ARCH-6 --> <!-- AMEND:ARCH-7 --> <!-- AMEND:QA-3 -->
- **Rides the EXISTING workspace-doctor abstraction — NO new surface (Ruling 10 / ARCH-7 / QA-3).** The workspace
  `DoctorService` renders `DoctorIssue(code, description, fixable)` as `{code} {[fixable]|[manual]} — {description}`
  under a `Found N issue(s):` header, and **never raises `Exit` on issues** (bare `dadaia doctor` already always exits
  0 — `cli/commands/doctor.py:29-45`). FR7 adds a new `DoctorIssue(code="EFF-1", fixable=False, description=...)` — NOT
  a `[warn]` token, NOT an exit-code change. The description carries the staleness age and the clearing command.
- **Marker + schema (Ruling 11 / ARCH-6).** `.dadaia/states/last_efficiency_audit.json`, schema
  `{"schema_version":"1","last_efficiency_audit":"<RFC3339>","by":"<agent>","report":"<workspace-relative path>"}`.
- **Cadence — named constant (Ruling 11 / ARCH-6).** `EFFICIENCY_AUDIT_STALE_DAYS = 30`. EFF-1 fires when the marker's
  `last_efficiency_audit` is older than 30 days.
- **Writer — deterministic CLI (Ruling 11 / ARCH-6).** `dadaia reports mark-efficiency-audit --report
  <workspace-relative-path> [--by <agent>]` writes the marker with the current RFC3339 timestamp (smallest surface: one
  verb under the existing `reports` group, no new group). This is how the EFF-1 issue is **cleared in production** — a
  fresh marker means no EFF-1.
- **Behaviour matrix (Ruling 10 / QA-3, axis-8 completeness):** *absent* marker ⇒ **no issue** (healthy — no baseline
  yet; this preserves every existing fresh-workspace `dadaia doctor` happy-path test); *fresh* (≤ 30 days) ⇒ no issue;
  *stale* (> 30 days) ⇒ EFF-1; *malformed* (invalid JSON / missing `last_efficiency_audit`) ⇒ EFF-1 with a "malformed
  marker" description (**never a crash**). RED-first: pre-fix there is no `DoctorService` staleness check at all.

### FR8 — Demonstrable off-uniform-opus Layer-1 assignment (Ruling ADR-6/ADR-8)

- The 3 real plugin agents run on the registry `plugin` (sonnet) tier (delivered via FR4) — a real, safe, non-opus
  Layer-1 model assignment, demonstrated end-to-end.
- **Discriminate on the Codex `model` field, NOT `model_reasoning_effort` (ARCH-2).** <!-- AMEND:ARCH-2 --> The Codex
  `model_reasoning_effort` is `medium` for the `plugin` tier, the `dispatch` tier AND the no-model fallback
  (`_CODEX_TIER_EFFORT["plugin"] == "dispatch"` effort `== "medium"` == `_CODEX_DEFAULT_EFFORT`) — it is
  **non-discriminating** and cannot distinguish plugin-tier from opus. The demonstrable observable is the Codex
  **`model` field** — `gpt-5.3-codex` for `claude-sonnet-4-6` (plugin) vs `gpt-5.5` for `claude-opus-4-8` — and the
  Claude frontmatter `model: claude-sonnet-4-6` line. FR8/AC-6/AC-11(f) assert those, not the effort.
- The **fast/haiku reasoning-persona downgrade is DEFERRED** — no code this release. File
  `fast-tier-persona-validation` at CLOSURE (needs operator-live equal-quality validation of any SDD-role persona on
  the cheaper tier).

### FR9 — Provenance-gated consumer-repo AGENTS.md fan-out (HIGH bug fix; AMENDS v0.1.58 Ruling L)

> **This FR AMENDS v0.1.58 FR4 Ruling L** ("the consumer-repo ROOT `AGENTS.md` is lib-owned canonical; a divergent copy
> is restored to canonical with an `[updated]` line"). Ruling L is **narrowed**: only a consumer `AGENTS.md` that is a
> *provable* canonical projection (carries the generated provenance banner) is lib-owned and eligible for restore; a
> hand-authored consumer root `AGENTS.md` is **repo-owned** and is **never** overwritten. Reviewers must see the ruling
> lineage — this is a deliberate reversal of the "all divergent copies are stale-canonical" assumption Ruling L made.

- **Provenance discriminator = a MODULE CONSTANT, contract-tested (Ruling 15 / QA-1 / ADR-9).** <!-- AMEND:QA-1 -->
  The fan-out (`workspace_guardrail.py#_install_guardrail_pair._write_one`) writes/overwrites a consumer-repo
  `AGENTS.md` **only** when its leading provenance banner matches a **module constant** `_CANONICAL_AGENTS_BANNER`
  (the canonical `public/data/AGENTS.md` generated banner — `> **AI agent rules.** This file is generated from
  `dadaia_workspace/public/data/AGENTS.md` by `dadaia public install`. ...`). The constant is a **fixed literal, NOT a
  runtime read of `public/data`**; a dedicated contract test `test_agents_banner_constant_matches_public_data` asserts
  it is **byte-equal** to the actual banner in `public/data/AGENTS.md` (drift on either side fails the contract test).
  Only `public install` emits that banner, so its presence is deterministic provenance.
- **Three cases per consumer `AGENTS.md`:**
  1. **Existing, banner matches canonical provenance** → stale canonical → restore + the existing DISTINCT
     `[updated] <path> (overwrote divergent workspace-law copy)` line (Ruling L behaviour preserved for provably-ours
     files).
  2. **Existing, no canonical banner** → **FOREIGN** (hand-authored / repo-owned) → **never overwritten**; report
     `[foreign] <path> — left untouched` (non-silent, mirroring the A3 never-silent law). This is the bug fix.
  3. **Absent** → create + `[ok]` (no data loss — an empty slot has nothing to clobber; preserves the v0.1.58 fill
     behaviour).
- **CLAUDE.md bridge follows its sibling's fate.** The `CLAUDE.md` `@AGENTS.md` stub is written **only** when its
  sibling `AGENTS.md` is created or restored in the same pass; when `AGENTS.md` is `[foreign]` (untouched), **no**
  `CLAUDE.md` is dropped (the orphan-drop the bug flags). A foreign (non-stub) existing `CLAUDE.md` is `[foreign]`,
  untouched.
- **Doctor is provenance-aware on the PAIR (Ruling 16 / ARCH-1 — CRITICAL).** <!-- AMEND:ARCH-1 --> `public doctor`
  raises `Exit(1)` on **any** `[missing]`/`[drift]` report line (`cli/commands/public.py:161-172`), and
  `_doctor_guardrail_pair` emits a **paired** `AGENTS.md` + `CLAUDE.md` line per consumer. Making only the `AGENTS.md`
  line `[foreign]` leaves the paired `CLAUDE.md` line `[missing]` (the hand-authored fixture has no `CLAUDE.md` —
  the bug never created one, and post-fix none is created) ⇒ **exit 1**, so AC-14's "exits 0" would be unsatisfiable.
  Therefore both lines are provenance-aware **as a pair**: when the consumer `AGENTS.md` is `[foreign]` (no banner),
  the `CLAUDE.md` line for that repo is **also `[foreign]`** (non-`Exit(1)`) — **whether the `CLAUDE.md` is absent OR a
  foreign non-stub** — never `[missing]`/`[drift]`. A banner-bearing (canonical) consumer copy keeps
  `[ok]`/`[drift]`/`[missing]` on both lines (restored/updated as today). Net: `public doctor` **exits 0** for a
  hand-authored consumer repo instead of perpetually red.
- **Self-repo skip retained** (the dadaia-workspace source tree keeps its hand-synced `AGENTS.md`).
- **Residual risk recorded (ARCH-8) — see §7 + ADR-9:** a consumer `AGENTS.md` that *carries* the canonical banner but
  has an edited body is classified canonical and **overwritten** (same data-loss class). The banner asserts
  generated-and-overwritable status; a consumer wanting repo-owned content MUST remove the banner. The match is the
  **full canonical banner block, byte-exact**, to minimize accidental collision.
- **Owner:** software-engineer (`infrastructure/workspace_guardrail.py`).

## 4. Non-goals

- **No Layer-2 catalog change.** `core/harness_models.py`, the `WorkflowModelProfile` registry/overlay, and the
  per-harness GPT model catalog are untouched — this release is the **Layer-1** axis only.
- **No REGISTRY model change.** The `fast`/`plugin` tiers and their model ids already exist; we only *assign* them (the
  v0.1.44 REGISTRY-untouched precedent holds). No new model id.
- **No network distribution.** Packs are in-package only.
- **No plugin uninstall** (additive-only; Ruling ADR-2) → backlog return.
- **No fast/haiku downgrade of the 9 reasoning-heavy core personas** (Ruling ADR-6) → backlog return.
- **No full plugin skill corpora** (Ruling ADR-5) → backlog return `plugin-pack-content-libraries`.
- **No constitution amendment** (§14 already forward-compatible) and **no roster change** (still 9 core + 3 plugin).
- **No agent-frontmatter `tier` renaming** (FR6 documents, does not rename).
- **No lease/gate/spec_context change.** This release lives in NEW `cli/commands/plugin.py`,
  `core/models/plugin_pack.py`, `core/protocols/plugin_store.py`, `infrastructure/json_plugin_store.py`, EDITs to
  `infrastructure/public_assets.py` (+ `public_assets_common.py`), `infrastructure/workspace_guardrail.py` (FR9),
  `cli/main.py`, workspace `doctor`, plus `public/**` content — it enters no `spec_context`/lease/gate path. The
  v0.1.50 frozen no-steal suite is expected **zero-diff**.

## 5. Acceptance criteria

- **AC-1 (golden-first — TWO goldens, three-leak normalization — RED-safe):** <!-- AMEND:ARCH-4 --> <!-- AMEND:QA-2 -->
  **golden (a)** — captured BEFORE any descriptor/refactor lands — locks the current `public_assets.install()`
  (all targets) + `public_assets.doctor()` full report list through the `public_assets` internal refactor (transient
  refactor-lock, retired at ship). **golden (b)** — captured AFTER the pack descriptors land (`public/plugins/**/pack.json`
  present) but BEFORE any projection/precedence code — is the durable **"descriptors-present, zero-plugin-installed"
  byte-lock baseline** consumers see post-upgrade. Both captured under `FileSystemPublicAssetManager` + `tmp_path`. **Both
  goldens carry the consolidated v0.1.58 platform-invariance normalization FROM DAY ONE — the three leak classes the
  `public_assets.doctor()` surface carries:** (1) host-state cwd-walk (`_check_public_privacy` denylist walk) →
  host-state canonicalization; (2) directory-iteration order (`.pi/` projection lines) → sorted-multiset lock; (3)
  OS-phrased exec-probe text → OS-phrase canonicalization — **in addition to** v0.1.55 path/version normalization +
  clock-freeze. Fix-the-consumer-never-the-golden.
- **AC-2 (ports-and-adapters seam — layer-pinned):** `core/models/plugin_pack.py` (`PluginPack`) is an import-linter-
  clean `core` leaf with **no I/O**; `core/protocols/plugin_store.py` (`PluginStore`) is the port;
  `infrastructure/json_plugin_store.py` (`JsonPluginStore`) round-trips `installed_plugins.json`. `lint-imports
  --no-cache` = `8 kept / 0 broken`, ignore-cap **UNCHANGED** (no new features→infra / infra→features edge).
- **AC-3 (`dadaia plugin install` writes the real body — RED-first):** `dadaia plugin install frontend-design` in a
  `tmp_path` workspace projects the `frontend-engineer` + `design-specialist` **real** bodies over the stubs
  (`.claude/agents/frontend-engineer.md` contains the pack body, NOT `[PLUGIN REQUIRED]`) and records `frontend-design`
  in `installed_plugins.json`; re-install is idempotent. `dadaia plugin install devops` enables `devops-engineer`.
  `dadaia plugin install bogus` → `exit_code == 2`, `"bogus"`/`"plugin"` in `result.stderr`, empty `result.stdout`.
  <!-- AMEND:QA-7 --> The `result.stderr` substring check is performed **after** normalizing via the shared
  `_norm_stderr`-style helper (ANSI-strip + Rich box-drawing collapse) — mandatory default before any stderr assert
  (v0.1.57 QA-atom law; Rich box-wrap passes locally, fails on the CI width). RED-first: pre-fix there is no `plugin`
  command.
- **AC-4 (projection precedence / clobber-safety — RED-first):** after `dadaia plugin install frontend-design`, a
  subsequent core `dadaia public install --target all` leaves `.claude/agents/frontend-engineer.md` as the **pack
  body** (not re-clobbered to the stub) because install consults `installed_plugins.json`. RED-first: pre-fix a core
  install re-writes the stub.
- **AC-5 (descriptors-present, zero-plugin byte-lock — Q2/A4-style):** <!-- AMEND:ARCH-4 --> with the pack descriptors
  present but no plugin installed, `test_absent_plugin_doctor_byte_equals_golden` asserts `public_assets.doctor()`'s
  runtime-projection + install-set lines == **golden (b)** (the descriptors-present baseline, three-leak-normalized);
  the added `stage:plugins/...` descriptor-source parity lines are captured into golden (b) and are NOT a violation. A
  stale/out-of-manifest installed-pack file is **non-silent** (`[drift]`/`[missing]`, never zero lines).
- **AC-6 (enumerated content is generic + tiered — Codex `model` discriminator):** <!-- AMEND:ARCH-2 -->
  <!-- AMEND:ARCH-5 --> each pack agent body carries `name`/`description`/`tier: 3`/`model: claude-sonnet-4-6`/tools + a
  real role body; `public doctor` `[ok] public-privacy` holds. The demonstrable off-opus assertion is on the **Codex
  `model` field** — an installed plugin agent's `.codex/agents/<name>.toml` renders `model = "gpt-5.3-codex"` (the
  sonnet/plugin mapping), NOT `gpt-5.5` (opus) — and the Claude frontmatter `model: claude-sonnet-4-6` line. (The
  `model_reasoning_effort` is `medium` for plugin AND opus AND fallback — it is explicitly NOT the discriminator,
  ARCH-2.) The **exact enumerated skill set** ships and no more: `frontend-design` → skill
  `browser-frontend-implementation`; `devops` → skill `github-actions-cicd`; zero new rules beyond the FR5
  `plugin-scope.md` rewrite. The codex `frontend-ctx`/`design-ctx` adapters are reused (not duplicated).
- **AC-7 (plugin-scope rule install-gated — RED-first):** `public/rules/plugin-scope.md` and the `[PLUGIN REQUIRED]`
  response no longer contain "no install command exists"/"not yet distributed" and DO name `dadaia plugin install`.
  RED-first: pre-fix the rule says "no install command exists". A grep asserts the retired wording is gone from the
  projected `.claude/rules/plugin-scope.md`.
- **AC-8 (efficiency-audit `DoctorIssue` EFF-1 — RED-first, 4-case matrix):** <!-- AMEND:ARCH-6 --> <!-- AMEND:ARCH-7 -->
  <!-- AMEND:QA-3 --> `dadaia doctor` renders a `DoctorIssue(code="EFF-1", fixable=False, description=...)` — NOT a
  `[warn]` token, and the bare `dadaia doctor` exit stays 0 (it already never exits non-zero on issues). Matrix:
  *absent* marker ⇒ **no EFF-1** (so existing fresh-workspace doctor tests keep `All invariants OK`); *fresh*
  (≤ `EFFICIENCY_AUDIT_STALE_DAYS = 30` days) ⇒ no EFF-1; *stale* (> 30 days) ⇒ EFF-1 rendered
  `EFF-1 [manual] — <staleness age + "run: dadaia reports mark-efficiency-audit ...">`; *malformed* (invalid JSON /
  missing `last_efficiency_audit`) ⇒ EFF-1 "malformed marker", never a crash. Writer `dadaia reports
  mark-efficiency-audit --report <path>` clears it (fresh marker ⇒ no EFF-1). RED-first: pre-fix there is no
  `DoctorService` EFF-1 check.
- **AC-9 (tier-taxonomy — MANDATORY machine guard):** <!-- AMEND:ARCH-9 --> <!-- AMEND:QA-8 --> the **non-optional**
  contract test `tests/contract/test_agent_tier_taxonomy.py` asserts every non-plugin core agent carries **both** a
  numeric frontmatter `tier` **and** a registry-known `model`, the 9 core agents keep `claude-opus-4-8` (`dispatch`),
  and the 3 plugin agents carry `tier: 3` + `model: claude-sonnet-4-6` (registry `plugin` tier). `tech-stack.md` +
  `architecture.md` state the two "tier" axes distinctly at CLOSURE; the eventual rename is tracked as backlog return
  `tier-taxonomy-rename`.
- **AC-10 (per-pack E2E — operator acceptance bar):** <!-- AMEND:QA-4 --> <!-- AMEND:QA-5 --> a sandboxed E2E scaffolds
  a workspace in-process via `CliRunner.invoke` and asserts: (a) fresh install (no pack) → the 3 agents are stubs +
  descriptors-present-zero-plugin doctor green + byte-lock (golden b); (b) `plugin install frontend-design` → both
  agents real, `installed_plugins.json` correct, doctor green; (c) `plugin install devops` → `devops-engineer` real;
  (d) a following core `public install --target all` keeps the pack bodies (AC-4); **(e/FR9)** a **registered**
  (in `spec_contexts.json`, schema-v2, via `_register_context`/`_write_registry`) consumer repo with a hand-authored
  root `AGENTS.md` survives `public install --target all` byte-identical (**both** its `AGENTS.md` and `CLAUDE.md`
  doctor lines `[foreign]`), and running `dadaia public doctor` **exits 0** (the v0.1.58 perpetual-`[drift]`+exit-1
  regression guard) while a stale-canonical (banner-bearing) fixture gets `[updated]`; **(f)** **double** `plugin
  install frontend-design` is a no-op (`installed_plugins.json` unchanged — ledger idempotency); **(g)**
  `installed_plugins.json` **coexists** with the `harness_profile.json` / overlay state without interference
  (profile×pack). `tmp_path` isolation + `-p no:cacheprovider`; **wall-time budget ≤ ~10s** (v0.1.58 in-process
  `CliRunner` ~6s precedent).
- **AC-11 (mutation-sanity per new test — sabotage → FAIL → revert):** <!-- AMEND:ARCH-2 --> <!-- AMEND:QA-6 -->
  **Every new test class is born falsifiable, including W1 (QA-6):** (0a/W1) make `plugin install` accept any pack
  (skip validation) ⇒ the AC-3 bad-value `exit_code == 2` test FAILS; (0b/W1) drop a ledger field in `JsonPluginStore`
  ⇒ the adapter round-trip test FAILS — both captured on the T-60-11 line (not deferred). (a) make `plugin install`
  skip the projection ⇒ AC-3 real-body test FAILS; (b) make core `public install` ignore `installed_plugins.json` ⇒
  AC-4 clobber-safety test FAILS (stub re-written); (c) make the doctor emit zero lines for a stale installed-pack file
  ⇒ AC-5 non-silent test FAILS; (d) leave the retired wording in `plugin-scope.md` ⇒ AC-7 grep test FAILS; (e) make
  `dadaia doctor` skip the EFF-1 staleness check ⇒ AC-8 stale-marker test FAILS; **(f)** give a plugin agent
  `model: claude-opus-4-8` ⇒ the AC-6 **Codex `model`-field** test FAILS (`.codex/agents/<name>.toml` renders
  `gpt-5.5` instead of `gpt-5.3-codex`); **(g/FR9)** drop the provenance-banner discriminator (overwrite any divergent
  consumer `AGENTS.md`) ⇒ the AC-14 hand-authored-survives test FAILS against a **registered** fixture (the foreign
  file is clobbered). Each captured on its task line, then reverted.
- **AC-12 (full gates):** `ruff format --check`, `ruff check --no-cache`, `mypy --strict`, the full **unpiped**
  `pytest` (real exit), `lint-imports --no-cache` (`8 kept / 0 broken`; ignore-cap UNCHANGED — the new `core` leaf +
  ports-and-adapters seam add no edge), `dadaia specs doctor` (exit 0), `dadaia backlog doctor` (exit 0). The ship wave
  runs `dadaia public stage` → `dadaia public doctor` → `dadaia public install --target all` → confirming
  `dadaia public doctor` (`[ok] public-privacy`, exit 0). The v0.1.50 frozen no-steal suite is **zero-diff**. Public
  assets stay GENERIC. *(PE runs no shell — surfaces the stage/doctor/install/doctor + git commands to PM/operator or
  requests devops-engineer.)*
- **AC-13 (surviving/dead behavior ledger, per wave — file-enumerated):** each wave records a ledger naming concrete
  files + fates; every move/repoint grep includes `tests/` AND non-import textual references. No implementation-wave
  commit stages any `specs/backlog/**` (dispositioned at CLOSURE).
- **AC-14 (FR9 provenance-gated fan-out — RED-first; resolves the HIGH bug):** <!-- AMEND:ARCH-1 --> <!-- AMEND:QA-4 -->
  a **registered** (in `spec_contexts.json`, schema-v2, via `_register_context`/`_write_registry` — so the fan-out
  actually reaches it; QA-4) consumer repo whose root `AGENTS.md` is **hand-authored** (no canonical banner)
  **survives `dadaia public install --target all` byte-identical**, the install output contains
  `[foreign] repos/<slug>/AGENTS.md — left untouched`, and **no** `CLAUDE.md` is dropped beside it. **`public doctor`
  reports `[foreign]` on BOTH the paired lines — `repos/<slug>:AGENTS.md` AND `repos/<slug>:CLAUDE.md` (no `[missing]`
  on the CLAUDE.md line) — and the full `dadaia public doctor` run EXITS 0** (Ruling 16 / ARCH-1 — the pair must be
  provenance-aware, else the `[missing]` CLAUDE.md forces exit 1 and this AC is unsatisfiable). A **stale canonical
  copy** (banner + older content) is **restored to canonical with the `[updated]` line** (pair restored); an
  **absent** consumer `AGENTS.md` is created (`[ok]`). **RED-first:** against the pre-fix `workspace_guardrail.py`, the
  registered hand-authored file is overwritten with the generic workspace `AGENTS.md` (`[updated] ... (overwrote
  divergent workspace-law copy)`). Mutation-sanity AC-11(g) against the registered fixture.
- **AC-15 (profile×pack projection scope — Ruling 13 / ARCH-3):** <!-- AMEND:ARCH-3 --> `dadaia plugin install
  frontend-design` in a **claude-only-profile** workspace projects only the `.claude/` agent (NO `.codex/` orphan);
  `installed_plugins.json` records the pack (not per-harness); core `public install --target all`'s projection
  precedence honors the same profile scope; a later profile change leaving an out-of-profile pack asset on disk is
  surfaced non-silently by `public doctor` (the v0.1.58 A3 law). Absent profile ⇒ all targets (back-compat).

## 6. Consumed backlog

| Item | Kind | Priority | Consumed → FR | Anchor fate |
|---|---|---|---|---|
| `plugin-packs-and-install-command` | backlog (candidate) | MEDIUM | in-package pack storage → FR1; `dadaia plugin` CLI (ports-and-adapters) → FR2; projection + ledger + doctor + precedence → FR3; minimal-viable content → FR4; plugin-scope rewrite → FR5 | Anchors `public_assets` (survives, gains plugin projection), the 3 stub agents (survive as un-installed default) → **CLOSURE** |
| `model-tier-efficiency-and-fast-tier-utilization` | backlog (candidate) | P2 | tier-taxonomy fix → FR6; efficiency-audit trigger → FR7; demonstrable off-opus (plugin tier) → FR8; fast/haiku persona downgrade DEFERRED (backlog return) | Anchors `model_registry.Tier` (survives, `fast`/`plugin` now assigned) → **CLOSURE** |

**Picked bug (reopened mid-definition — §0):**

| Bug | Severity | Mapped → | Disposition (terminal event at CLOSURE) |
|---|---|---|---|
| `public-install-clobbers-consumer-repo-agents-md` (`specs/bugs/20260704T19Z-00.jsonl`) | HIGH | FR9 + AC-14 + ADR-9 (amends v0.1.58 Ruling L) | `dadaia bugs append --event resolved --release v0.1.60` at T-60-70 (never dropped; solved this release) |

**Archival timing.** Both consumed anchors SURVIVE → dispositioned + archived at CLOSURE (`DELIVERED — v0.1.60`); no
dead anchor → no SHIP-time archival. Discipline: **no `specs/backlog/**` staged in W1–W6** (AC-13). Backlog returns
(filed at CLOSURE): `plugin-pack-content-libraries`, `plugin-uninstall`, `fast-tier-persona-validation`,
**`tier-taxonomy-rename`** (Ruling 17 / ARCH-9 — the eventual `tier:` → `dispatch_band:` frontmatter rename).

**Frozen-suite check — NO interaction.** The v0.1.50 no-steal lease/gate suite is untouched: this release enters no
`spec_context`/lease/gate path. Expect **zero** frozen-file diff.

## 7. Risks

- **Golden brittleness / over-normalization (FR3).** A no-plugin golden capturing a host path would false-fail.
  Mitigation: v0.1.55 platform-invariant normalization on every path-bearing golden; capture under fixed `tmp_path` +
  `FileSystemPublicAssetManager`.
- **Core install clobbers an installed pack (FR3 precedence).** Without the ledger read, a routine `public install`
  reverts a pack agent to its stub. Mitigation: AC-4 clobber-safety test + AC-11(b) sabotage; `installed_plugins.json`
  is the source of truth for projection precedence.
- **Pack content unbounded (FR4).** Full frontend/devops/design skill corpora could balloon the release. Mitigation:
  Ruling ADR-5 — minimal-viable content only; full corpora → backlog return; reuse the existing codex ctx adapters.
- **Public-privacy leak in pack content (FR1/FR4).** Pack agents/skills must stay generic. Mitigation: `public doctor`
  `[ok] public-privacy` is an AC; ai-engineer authors under the public-privacy law.
- **Silent quality regression from a fast-tier persona (FR8).** Downgrading an SDD-role persona to haiku with no live
  operator to validate is reckless. Mitigation: Ruling ADR-6 defers it; the demonstrable off-opus assignment is the
  plugin agents on the `plugin`/sonnet tier only.
- **lint-imports edge from the new seam (FR2).** A new `core`/`features`/`infra` edge would break the contract.
  Mitigation: `plugin_pack.py` is a stdlib-only `core` leaf; the adapter mirrors `json_harness_profile_store` (no new
  edge); AC-12 asserts `8 kept / 0 broken`, ignore-cap unchanged.
- **Self-hosting instance write at ship (AC-12).** `public install` on the live instance re-projects. Mitigation:
  stage → doctor → install → confirming doctor; instance files reconciled only via the pipeline, never hand-edited.
- **FR9 residual — banner-bearing but body-edited consumer `AGENTS.md` (ARCH-8).** <!-- AMEND:ARCH-8 --> A consumer that
  scaffolded from the generic projection (banner + generic body) then customized the body **while keeping the banner**
  is classified case 1 (canonical) and **overwritten** — a residual instance of the same HIGH data-loss class. This is
  an **accepted, recorded** residual: the banner is a "do not edit — generated" contract, so overwriting a
  banner-bearing file is working-as-designed. **Operator guidance:** a consumer wanting repo-owned root `AGENTS.md`
  content MUST remove the canonical banner block. Mitigation: the match is the **full canonical banner block,
  byte-exact** (minimizes accidental collision); ADR-9's ledger-hash alternative remains available as belt-and-suspenders
  defense-in-depth if the operator wants edited-body protection too.

## 8. Memory files affected at CLOSURE

- `specs/memory/product/distribution/public-asset-distribution.md` — **primary edit.** Plugin pack staging
  (`public/plugins/`) + `dadaia plugin install/list/doctor` + `installed_plugins.json` ledger + projection precedence
  + doctor integration + absent-pack byte-lock. **FR9:** the consumer `AGENTS.md` fan-out is now
  **provenance-gated** — only a banner-bearing (canonical) consumer copy is restored (`[updated]`); a hand-authored
  copy is `[foreign]`/untouched (amends the v0.1.58 lib-owned-canonical description). Assess `tldr`/`summary`/`area`
  (regen `catalog.json` + `index.md` only if they change; keep the regenerated `tldr` within the length cap).
  `release_origin` → v0.1.60.
- `specs/memory/product/agents/agent-orchestration.md` — **edit.** The 3 plugin agents carry behavior once their pack
  is installed; they run on the registry `plugin` (sonnet) tier; the two "tier" axes are distinguished.
  `release_origin` → v0.1.60.
- **NEW atom assessment** — assess whether the plugin-install capability warrants a new
  `specs/memory/product/distribution/plugin-packs.md` feature atom (adds to catalog + `index.md`) vs folding into
  `public-asset-distribution.md`. Recommend fold unless it clearly warrants its own atom.
- `specs/memory/tech-stack.md` — **edit.** Document the two "tier" axes (numeric frontmatter `tier` vs registry
  `Tier`) + the machine-guard contract test + the tracked `tier-taxonomy-rename` return; the plugin-tier assignment
  (Codex `gpt-5.3-codex`); the efficiency-audit marker schema + `EFFICIENCY_AUDIT_STALE_DAYS = 30` cadence + the
  `dadaia reports mark-efficiency-audit` writer verb + the EFF-1 `DoctorIssue`. Layer-2 catalog wording unchanged.
- `specs/memory/architecture.md` — **edit (CLOSURE).** Module map gains `cli/commands/plugin.py`,
  `core/models/plugin_pack.py`, `core/protocols/plugin_store.py`, `infrastructure/json_plugin_store.py`; `public/`
  gains `plugins/`; `public_assets` gains plugin projection + precedence; workspace `doctor` gains the efficiency-audit
  staleness check. **FR9:** update the `workspace_guardrail.py`/`_consumer_repos_for_root` line (public/** summary) —
  the fan-out is provenance-gated (banner-match; hand-authored consumer `AGENTS.md` is `[foreign]`, never clobbered;
  doctor emits `[foreign]` not `[drift]`). Feature count assessed. `release_origin` → v0.1.60. *(The L63 kanban
  drift-correction was already applied in DEFINITION — not a v0.1.60 change.)*
- `specs/memory/quality-assurance.md` — **assess.** The absent-pack golden law + the plugin-install E2E pattern; add a
  note if the pattern needs one. Confirm.

## 9. Definition rulings (grill, operator-unavailable — OPERATOR-OVERRIDABLE)

The operator is unavailable mid-flow; code-unanswerable decisions are pre-ruled here with rationale and marked
overridable. Full evidence: the grill report cited in the header.

- **ADR-1 — Pack storage = IN-PACKAGE `public/plugins/<pack>/`, no network.** Two packs (`frontend-design`, `devops`)
  ride the existing `_COPY_DIRS` "plugins" staging. Rationale: mirrors every other public asset; offline-safe;
  privacy-clean. **Override:** external/network registry.
- **ADR-2 — Install command = `dadaia plugin install/list/doctor`; per-workspace `installed_plugins.json` ledger;
  manifest-tracked; idempotent; NO uninstall this release** (additive-only, mirrors v0.1.58 no-removal). **Override:**
  add uninstall now / drop the ledger.
- **ADR-3 — plugin-scope rule + `[PLUGIN REQUIRED]` become install-gated wording** (ai-engineer). **Override:** keep
  stub language, gate only the CLI.
- **ADR-4 — Pack install OVERWRITES the projected stub with the real body; the core stub survives as the un-installed
  default; core `public install` respects `installed_plugins.json` (projection precedence).** **Override:** side-by-side
  under distinct names.
- **ADR-5 — SCOPE SIZING: machinery + minimal-viable content** (3 real agent bodies + minimal essential skills/rules);
  full corpora → backlog `plugin-pack-content-libraries`. Rationale: the headline deliverable is a working
  `dadaia plugin install`; full content is unbounded; keeps the mandate-tail release shippable. **Override:** author
  full content now.
- **ADR-6 — Fast-tier: DEFER the reasoning-persona downgrade.** deep tier (`claude-fable-5`) is region-restricted
  (v0.1.7) forcing all 9 to opus; the 9 roles are reasoning-heavy; no live operator to validate "equal output
  quality". Do NOT downgrade a core persona to haiku on-spec; file `fast-tier-persona-validation`. The demonstrable
  off-opus assignment is the plugin agents on the `plugin` (sonnet) tier (ADR-8). **Override:** operator names one
  persona safe on haiku now.
- **ADR-7 — Efficiency-audit trigger = a `DoctorIssue(code="EFF-1")` on the EXISTING workspace-`doctor` abstraction
  (amended by Ruling 10/11 / ARCH-6/7).** <!-- AMEND:ARCH-7 --> NOT a `[warn]` token (that surface does not exist; the
  workspace doctor renders structured `DoctorIssue` and already always exits 0). Cadence `EFFICIENCY_AUDIT_STALE_DAYS =
  30`; marker schema `{schema_version, last_efficiency_audit, by, report}`; writer `dadaia reports mark-efficiency-audit`;
  absent ⇒ no issue, stale/malformed ⇒ EFF-1. Cheaper + self-surfacing vs a CLOSURE checkpoint. **Override:**
  CLOSURE-phase checkpoint item instead.
- **ADR-8 — Plugin agents carry `model: claude-sonnet-4-6` (registry `plugin` tier).** The demonstrable off-uniform-opus
  Layer-1 assignment. **Override:** opus for plugin agents.

- **ADR-9 — Provenance discriminator for the consumer-repo fan-out = BANNER-MATCH (content-intrinsic).** The fan-out
  restores/overwrites a consumer `AGENTS.md` **only** when its leading provenance banner matches the canonical
  `public/data/AGENTS.md` generated banner (only `public install` emits it); a no-banner file is FOREIGN and left
  untouched (`[foreign]`, non-silent). **This AMENDS v0.1.58 FR4 Ruling L** (which assumed every divergent consumer
  copy is stale-canonical). **Rationale:** banner-match is deterministic, content-intrinsic, needs no new state, works
  on first contact, and satisfies both acceptance halves — a hand-authored file survives byte-identical AND a stale
  canonical copy still gets `[updated]`. The **ledger-hash alternative** (`.dadaia/states/fanout_ledger.json` mapping
  consumer path → last-written canonical SHA; overwrite only a previously-written SHA) is rejected as the primary
  discriminator: it needs new state and FAILS the "stale canonical on a never-before-seen repo still gets `[updated]`"
  case (no ledger entry ⇒ treated foreign ⇒ never updated). **Implementation (Ruling 15 / QA-1):** <!-- AMEND:QA-1 -->
  the banner is a **module constant** `_CANONICAL_AGENTS_BANNER` in `workspace_guardrail.py`, byte-equal-asserted to
  `public/data/AGENTS.md` by the contract test `test_agents_banner_constant_matches_public_data` (no runtime read of
  `public/data`). **Recorded residual (ARCH-8):** <!-- AMEND:ARCH-8 --> a banner-bearing consumer copy with an edited
  body is treated as canonical and overwritten (working-as-designed — the banner asserts generated status; remove the
  banner for repo-owned content); the match is the full canonical banner block, byte-exact. **Override:** the operator
  selects ledger-hash instead, or banner-match + ledger-hash as belt-and-suspenders (defense-in-depth, also covering
  the edited-body residual), or reverts the amendment (rejected — the bug is a HIGH data-loss class).

- **Stale-claim corrections (dossier vs source).** (1) The `model-tier` dossier frames "mechanical sub-task classes →
  fast tier" as a Layer-1 action — by inspection those classes are deterministic CLI (no model) or a persona tail-step;
  Layer-1 has no sub-task tiering (only whole-persona `model:`), so FR6–FR8 reframe the item to persona-level +
  efficiency-trigger + taxonomy. (2) "The `fast` Layer-1 tier has zero agent assignments" is about *assignment* — the
  tier already exists and is cost-priced in the registry (P2); no REGISTRY change. (3) The `plugin-packs` dossier's
  premise is accurate; the staging pipeline is already pre-wired (`_COPY_DIRS` "plugins") but dead-on-arrival (no
  projection/ledger). (4) Constitution §14 already says "until their pack installs" — no amendment needed.
