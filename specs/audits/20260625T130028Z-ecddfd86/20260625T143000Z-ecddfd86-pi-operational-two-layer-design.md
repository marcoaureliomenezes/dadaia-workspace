# DESIGN — PI Operational at Both Agentic Layers (constitution amendment + `.pi/` projection shape)

- **Author:** software-architect (DRAFT mode, design-only — no production/spec/constitution edits)
- **Date (UTC):** 2026-06-25T14:30:00Z
- **Session discriminator:** ecddfd86
- **Branch:** `feature/pi-operational-v1`
- **Drives:** the PI/two-layer remediation release (audit `20260625T130028Z-ecddfd86/audit.md`, floor-breach agent-surface=3, findings F12 + G-1 + D-1..D-5 + G-2 + G-3)
- **Consumers of this doc:** product-engineer (applies the §0/§4/§8/§14 amendment text), ai-engineer (authors `.pi/` source + wiring), software-engineer (implements `_install_pi` + doctor line)
- **Status:** Draft — ready for product-engineer to apply Deliverable 1 verbatim and ai-engineer/software-engineer to build Deliverable 2.

---

## Core Workflow trail (architect-core-workflow — required before any recommendation)

### Step 1 — Understand the Problem

- **Core problem.** The constitution and the AI-entity surface define a closed 3-harness world; PI shipped as a real 4th worker runtime (`AgentRuntimeKind.PI_HEADLESS`, `PiHeadlessAdapter`, wired in `container.py`) and PI is a legitimate Layer-1 entry harness too — yet the **two-layer agentic model** (entry harness vs worker harness) is named **nowhere** in law or memory (audit G-1), and PI has **no first-layer projection tree** (`.pi/`). An agent grounding itself cannot learn PI exists or that any lifecycle step can run on any of four worker harnesses.
- **Constraints.**
  - Constitution is product law: amendment text must be operator-applicable verbatim, generic/public-safe (no operator-local paths, names, IPs), and must preserve the §4/§8 **honesty clause** (must not claim PI enforces hooks it does not).
  - PI's Ring-1 (pre-disk) is NOT available in the `pi` CLI today → PI's Layer-2 enforcement posture is Ring-2 + git chokepoints, identical to Codex-headless/OpenCode. The amendment must say this honestly.
  - `.pi/**` is **post-trust executable TS, no sandbox** — a real security boundary that must be documented, not hand-waved.
  - The `.pi/` surface must be **minimal**: AGENTS.md already carries the law (PI reads it natively up-tree). Duplicating the law into `.pi/SYSTEM.md` is slop — point at it.
  - Projection must mirror the existing per-target machinery (`_VALID_TARGETS`, `_install_opencode`, `runtime_expectations`, manifest, `public doctor`, privacy gate) — no new mechanism invented.
  - WS-PI-4 (Ring-1 `.pi/extensions/` SDD gate) is **out of scope** for this release.
- **Success criteria (testable).**
  1. After product-engineer applies Deliverable 1, `dadaia specs doctor` stays 0-error and SPEC-DOC-028 (constitution file-refs resolve) passes; the two-layer model + PI are named in §0/§4/§8/§14.
  2. After ai-engineer/software-engineer build Deliverable 2, `dadaia public install --target pi` and `--target all` project `public/pi/` → `.pi/`; `dadaia public doctor` emits `[ok] pi:` lines and exit 0; `[ok] public-privacy` stays green; `.pi/**` entries are manifest-tracked (lib-originated).
  3. A new PI Layer-1 session reads `AGENTS.md` natively and `.pi/SYSTEM.md` points it at the law + `dadaia` CLI without restating the law.
- **Assumptions (made explicit).**
  - PI reads `AGENTS.md`/`CLAUDE.md` up the directory tree natively (operator-confirmed; same posture as Codex/OpenCode). If false, `.pi/SYSTEM.md` would have to carry an explicit import bridge — flagged as a risk below.
  - `pi --mode json` is the shipped headless transport (`PiHeadlessAdapter`); RPC/SDK transports are deferred per harness.
  - The operator's normative vision doc (`docs/01_medium_codex.md`) stance on PI is **gated on operator confirmation** (audit decision (a)); this design does NOT amend product-vision.md — that is product-engineer + operator, downstream of this constitution amendment.

### Step 2 — Research Existing Solutions (prior art surveyed)

This is **not** a green-field design. The faithful prior art is the workspace's own OpenCode target — PI's enforcement posture (advisory + chokepoint-protected, no pre-disk Ring-1) is structurally identical to OpenCode, so OpenCode is the exact structural mirror.

| Candidate | Maturity | Fit | Integration | Cost | Risk | Verdict |
|---|---|---|---|---|---|---|
| **Mirror the OpenCode target** (`_install_opencode` / `_OPENCODE_DIRS` / `_build_opencode_config` / `runtime_expectations` / `_VALID_TARGETS`) | Proven in production across 4 releases; the install/stage/doctor/manifest/privacy chain is battle-tested | Solves ~95% — OpenCode is the closest analog (advisory + chokepoint, no Ring-1, native AGENTS.md) | Clean — same `targets` tuple, same `copy_tree`, same `runtime_expectations`, same `manifest.json`, same `public doctor` compare | Low — add one `_install_pi`, one `_OPENCODE_DIRS`-analog, one doctor line, one `_VALID_TARGETS` member | Low — established seam | **CHOSEN.** Build new only the PI-specific source tree; reuse all machinery. |
| Invent a bespoke PI projector | n/a | n/a | Would fork the projection contract | High | High — duplicate GC/drift/privacy logic = slop (anti-§12.2) | Rejected — no mature reason to diverge from the OpenCode seam. |
| Ship `.pi/` source only, no installer wiring | n/a | Fails criterion 2 — files never project, doctor blind | n/a | n/a | High — un-projected source is dead-on-arrival slop | Rejected. |

**Chosen direction:** project a NEW minimal `dadaia_workspace/public/pi/` source tree through a `_install_pi` that structurally mirrors `_install_opencode`; AGENTS.md carries the law, `.pi/` carries only PI-specific affordances. Trade-off: one new install branch + one doctor line + one `_VALID_TARGETS` member (small, additive, fully testable) vs. PI remaining invisible at Layer 1.

---

## Anti-slop gate verdicts (recorded explicitly)

- **Root-cause gate — PASS.** The root cause is documented honestly: PI's Layer-2 posture is Ring-2 + chokepoints because the `pi` CLI exposes no pre-disk hook (Ring-1), NOT a workaround. The amendment states this; it does not pretend PI enforces hooks. WS-PI-4 (Ring-1 via a `.pi/` extension) is named as the real fix and explicitly deferred — not silently patched.
- **Architecture-fidelity gate — PASS.** The amendment puts each fact in its correct layer: the two-layer model and `.pi/` layout go in §0 (declarative identity); the Layer-1 enforcement matrix stays in §4/§8 (PI gets a row honestly scoped to "advisory + chokepoint, no Ring-1 yet"); the Layer-2 worker-runtime set is named distinctly from the Layer-1 enforcement matrix so the two are never conflated. `AgentRuntimePort` is named as the Layer-2 seam — the abstraction that actually exists in `core/`/`container.py`. No abstraction is invented.
- **Anti-spaghetti / minimality — PASS.** `.pi/SYSTEM.md` points at AGENTS.md; it does not restate the law (no fact in two sources — §12.3). The projection reuses the OpenCode machinery; no parallel projector. Trust boundary is documented, not hand-waved.

---

# Deliverable 1 — Constitution amendment (exact, ready-to-apply text)

> Application note for product-engineer: this is a MUTATING constitution edit (operator sign-off required per audit recommendation 7). Apply in DEFINITION/CLOSURE of the remediation release. All text below is generic/public-safe. Each block states **WHERE** and **INSERT vs REPLACE**.

## 1.1 — NEW §0 subsection "The two agentic layers"

**WHERE:** in §0 "Identity & Core Concepts", insert a new subsection immediately **after** the `### Agent philosophy` subsection (current line ~104, before `### Value proposition`). The model is conceptually closest to agent philosophy and must precede the value proposition.

**INSERT (verbatim):**

```markdown
### The two agentic layers

dadaia-workspace runs its agents at **two distinct agentic layers**. Naming them is
load-bearing: enforcement, transport, and projection differ per layer, and conflating
them is the source of the harness-count confusion this section closes.

**Layer 1 — the entry harness (interactive).** A human opens a terminal and launches a
coding harness directly — `claude`, `codex`, `opencode`, or `pi`. That running harness
**is** the first agentic layer. It is governed by (a) the workspace-root `AGENTS.md` —
read natively up the directory tree by Codex, OpenCode, and PI, and via the
`CLAUDE.md` → `@AGENTS.md` bridge by Claude Code (§0 layout) — and (b) the per-harness
projected assets (`.claude/`, `.codex/`, `.opencode/`, `.pi/`). At Layer 1 the harness
may invoke the `dadaia` CLI. Layer-1 deterministic enforcement is the per-harness
PreToolUse + git-chokepoint matrix of §4/§8.

**Layer 2 — the worker harness (programmatic).** A `dadaia lifecycle` CLI verb runs a
procedural **Python workflow** (`LifecyclePhaseWorkflow` for a single step;
`LifecyclePipeline` for the IMPLEMENTATION → QA → SECURITY → CODE → CLOSURE ladder)
that drives bounded agent **workers**. Each worker is reached through the
**`AgentRuntimePort`** seam (the Layer-2 abstraction; concrete runtimes are built by
`build_agent_runtime(kind)`), selectable and mixable per step via `--harness` /
`--step-harness label=kind`. The worker is reached by the transport appropriate to its
harness:

- **SDK** — the Claude Agent SDK (`CLAUDE_SDK`), which enforces a real pre-disk (Ring-1)
  write boundary via `core/scope_match`.
- **CLI-headless** — `codex exec` (`CODEX_EXEC`), `opencode run` (`OPENCODE_RUN`), and
  `pi --mode json` (`PI_HEADLESS`); these have no pre-disk hook and are bounded by
  Ring-2 + the git chokepoints.
- **RPC** — reserved for future per-harness transports; none ship today.

The five `AgentRuntimeKind`s today are **FAKE, CODEX_EXEC, CLAUDE_SDK, OPENCODE_RUN,
PI_HEADLESS**. Layer 2 is where prompts-inside-workflows run; it is distinct from Layer 1.
The Layer-1 enforcement matrix (§4/§8) governs entry harnesses and their hooks; it does
**not** describe Layer-2 worker enforcement, which is the per-runtime ring posture above.
```

## 1.2 — §0 layout list: add `.pi/`

**WHERE:** §0 "Workspace root & operational layout", the numbered allowed-root-entries list (current lines 115-128). The list currently enumerates nine entries; `.pi/` is a new lib-originated projection directory and must be added in alphabetical position among the dot-dirs (after `.opencode/`).

**REPLACE** the list intro line and renumber. Current:

```markdown
The workspace root is not a git repo. The nine allowed root entries are:

1. `.agents/` — universal agent assets and shared skills.
2. `.claude/` — Claude Code projection.
3. `.codex/` — Codex projection.
4. `.dadaia/` — operational data for the workspace.
5. `.opencode/` — OpenCode projection.
6. `repos/` — alive repos associated with Spec Context Projects.
7. `AGENTS.md` — root workspace rules (the primary agent instruction file).
8. `CLAUDE.md` — required Claude Code bridge. ...
9. `prompt.md` — optional human-created long prompt file for operator use.
```

**WITH:**

```markdown
The workspace root is not a git repo. The ten allowed root entries are:

1. `.agents/` — universal agent assets and shared skills.
2. `.claude/` — Claude Code projection.
3. `.codex/` — Codex projection.
4. `.dadaia/` — operational data for the workspace.
5. `.opencode/` — OpenCode projection.
6. `.pi/` — PI (`pi-coding-agent`) Layer-1 projection: PI-specific entry-harness assets
   (`SYSTEM.md`, `settings.json`, and optional `prompts`/`skills`). **Trust boundary:**
   `.pi/**` assets are loaded by PI only **after the operator grants trust**, and PI
   executes them as TypeScript **without a sandbox**. Treat `.pi/**` as post-trust
   executable code: it is lib-originated (manifest-tracked), never carries secrets or
   operator-local paths, and is a deliberate privilege grant — not inert config.
7. `repos/` — alive repos associated with Spec Context Projects.
8. `AGENTS.md` — root workspace rules (the primary agent instruction file).
9. `CLAUDE.md` — required Claude Code bridge. Claude Code does not read `AGENTS.md`
   natively (per official Claude Code documentation); a root `CLAUDE.md` containing
   `@AGENTS.md` is the correct import bridge. This entry is therefore mandatory
   for Claude Code users and is authorized as a permanent root entry.
10. `prompt.md` — optional human-created long prompt file for operator use.
```

> Note for product-engineer: the root-whitelist policy (`pre_gate`) and the
> `tmp-file-guardrail` rule's root whitelist also enumerate the allowed root dirs. Those
> are **library-surface** (public/ assets + hook code), owned by ai-engineer/software-engineer,
> not constitution edits — but they MUST be updated in the same release so `.pi/` is not
> blocked at root by the very gate that protects it. Flagged in the Risks section.

## 1.3 — §0 identity line: widen the harness set + name the layers

**WHERE:** §0 "What dadaia-workspace is", current lines 27-29.

**REPLACE:**

```markdown
one AI coding harness (Claude Code, Codex, and — when installed — OpenCode), over
more than one software project at once, under Spec-Driven Development, coordinated
```

**WITH:**

```markdown
one AI coding harness — at Layer 1 (entry harness) the operator may launch Claude Code,
Codex, OpenCode, or PI (`pi-coding-agent`); at Layer 2 (worker harness) the lifecycle
engine drives bounded workers on any of these behind `AgentRuntimePort` (§0 "The two
agentic layers") — over more than one software project at once, under Spec-Driven
Development, coordinated
```

## 1.4 — §4 Runtime Parity: add the PI row + scope the matrix to Layer 1

**WHERE:** §4 "Runtime Parity Must Be Honest", current lines 173-187 (the prose enumerating the per-harness matrix). The §4 prose currently lists Claude/Codex-interactive/Codex-headless/OpenCode.

**REPLACE** the §4 first paragraph and the per-harness enforcement sentence. Current:

```markdown
Claude Code, Codex, and OpenCode projections must describe what each runtime
actually supports. Runtime adapters may differ, but doctor output and AGENTS.md
instructions must not claim behavior that the runtime does not enforce.

Enforcement per harness follows §8's per-harness enforcement matrix (normative):
Claude Code = deterministic (PreToolUse hooks + git chokepoints); Codex
interactive = deterministic (PreToolUse hooks + git chokepoints); Codex headless
(`codex exec`) = chokepoints only (exec hooks do not fire — upstream codex-cli
defect); OpenCode = advisory + chokepoint-protected (ADR-G3).
```

**WITH:**

```markdown
Claude Code, Codex, OpenCode, and PI projections must describe what each runtime
actually supports. Runtime adapters may differ, but doctor output and AGENTS.md
instructions must not claim behavior that the runtime does not enforce.

This honesty clause is scoped to **Layer-1 entry-harness enforcement** (§0 "The two
agentic layers"). Enforcement per Layer-1 harness follows §8's per-harness enforcement
matrix (normative): Claude Code = deterministic (PreToolUse hooks + git chokepoints);
Codex interactive = deterministic (PreToolUse hooks + git chokepoints); Codex headless
(`codex exec`) = chokepoints only (exec hooks do not fire — upstream codex-cli defect);
OpenCode = advisory + chokepoint-protected (ADR-G3); PI = advisory + chokepoint-protected
(PI exposes no pre-disk hook in its CLI, so Layer-1 PI has no PreToolUse enforcement; its
`.pi/` assets are post-trust executable and a Ring-1 PreToolUse extension is deferred —
see §8). The Layer-2 worker-runtime ring posture is governed separately in §8 and is not
described by this matrix.
```

## 1.5 — §8 enforcement matrix: add the PI Layer-1 row + a Layer-2 worker note

**WHERE:** §8 "Concurrency Model", the `**Per-harness enforcement matrix:**` table (current lines 378-386).

**REPLACE** the table. Current:

```markdown
| Harness | PreToolUse hooks (`pre_gate`) | Git chokepoints | Posture |
|---|---|---|---|
| Claude Code | yes | yes | deterministic: hooks + chokepoints |
| Codex interactive | yes | yes | deterministic: hooks + chokepoints |
| Codex headless (`codex exec`) | **no — exec hooks do not fire** (upstream codex-cli defect) | yes | chokepoints only |
| OpenCode | no | yes | advisory + chokepoint-protected (ADR-G3) |
```

**WITH:**

```markdown
**Layer-1 entry-harness enforcement matrix** (governs the harness a human launches in a
terminal; see §0 "The two agentic layers"):

| Harness | PreToolUse hooks (`pre_gate`) | Git chokepoints | Posture |
|---|---|---|---|
| Claude Code | yes | yes | deterministic: hooks + chokepoints |
| Codex interactive | yes | yes | deterministic: hooks + chokepoints |
| Codex headless (`codex exec`) | **no — exec hooks do not fire** (upstream codex-cli defect) | yes | chokepoints only |
| OpenCode | no | yes | advisory + chokepoint-protected (ADR-G3) |
| PI (`pi-coding-agent`) | **no — PI CLI exposes no pre-disk hook (no Ring-1)** | yes | advisory + chokepoint-protected; `.pi/**` is post-trust executable; a Ring-1 PreToolUse extension is deferred |

**Layer-2 worker-runtime posture** (governs bounded workers driven by `dadaia lifecycle`
behind `AgentRuntimePort`; this is NOT the entry-harness matrix above): the worker
runtimes are FAKE, CODEX_EXEC, CLAUDE_SDK, OPENCODE_RUN, PI_HEADLESS. Only CLAUDE_SDK
enforces a real pre-disk (Ring-1) write boundary, via `core/scope_match`; CODEX_EXEC,
OPENCODE_RUN, and PI_HEADLESS are CLI-headless and bounded by Ring-2 + the git
chokepoints. A Ring-1 boundary for the headless worker runtimes is deferred. The honesty
clause of §4 applies to both layers: no projection or doctor line may claim enforcement a
runtime does not perform.
```

## 1.6 — §14 / persona-roster harness-count touch

**WHERE:** §14 "Agent Roster". The roster table itself does not enumerate harnesses, so no row changes. The only touch is the `ai-engineer` line's surface scope. **No constitution table edit is strictly required by §14**; the harness-count fix lives in the `ai-engineer` *persona* (a public-surface edit owned by ai-engineer — audit F6/D-4), not in the constitution roster. 

**RECOMMENDATION (product-engineer):** add ONE clarifying clause to the `ai-engineer` row of §0 "Agent philosophy" (line ~92), which currently reads:

```markdown
- **ai-engineer** — the multi-harness AI-entity surface: agent personas, skills,
  rules, workflows, hooks, and the context-engineering that drives them.
```

**REPLACE WITH:**

```markdown
- **ai-engineer** — the multi-harness AI-entity surface (the four harnesses: Claude Code,
  Codex, OpenCode, PI): agent personas, skills, rules, workflows, hooks, and the
  context-engineering that drives them, across both agentic layers (§0 "The two agentic
  layers").
```

This is the single normative place to anchor "ai-engineer owns the now-4-harness surface";
the persona-file fix (D-4) inherits from it.

## 1.7 — Scaffold stub recommendation (`public/scaffold/constitution.md`)

**Recommendation: NO two-layer / 4-harness mention in the scaffold stub. Leave it unchanged.**

Rationale (architecture-fidelity + minimality): the 62-line scaffold stub
(`dadaia_workspace/public/scaffold/constitution.md`) is the **template for a consumer
project's own product law** — it describes *that project's* stack, architecture, and SDD
workflow, NOT the dadaia-workspace harness/layer model. The two-layer model and the
4-harness set are **workspace-level facts**, already carried by the root `AGENTS.md` (which
a consumer workspace projects) and by this constitution (the dadaia-workspace source law).
Injecting a dadaia-internal harness/layer narrative into a *consumer project constitution
template* would be a fact in two sources (§12.3 violation) and would leak workspace-engine
concepts into a place meant for project-domain law. The scaffold stub stays generic and
project-scoped. (If the operator later wants the template to *reference* that the workspace
runs multiple harnesses, the correct minimal text is a one-line pointer — "harness/layer
model is defined at the workspace root `AGENTS.md`" — not a restatement; but the default
recommendation is to add nothing.)

---

# Deliverable 2 — Minimal `.pi/` first-layer projection shape (WS-PI-3)

**Design principle:** AGENTS.md already carries the law and PI reads it natively up-tree.
`.pi/` carries ONLY PI-specific entry-harness affordances. The smallest faithful surface:

## 2.1 — Source tree (NEW) `dadaia_workspace/public/pi/`

```
dadaia_workspace/public/pi/
├── settings.json          # PI harness settings (minimal, PI-native schema)
├── SYSTEM.md              # PI Layer-1 system note — POINTS AT the law, does not restate it
└── prompts/               # OPTIONAL — dadaia-affordance slash-prompts (only if PI prompt schema warrants)
    └── dadaia-context.md  # e.g. a "show active context + lifecycle" affordance
```

Projected to `.pi/` at the workspace root. **No `.pi/skills/` and no `.pi/extensions/` in
this release** (skills are covered by the universal `.agents/` shared skill surface if PI
consumes it; extensions = Ring-1 = WS-PI-4, deferred).

### File contents (high-level only — full authoring is ai-engineer at implement time)

- **`.pi/SYSTEM.md`** — a short PI-native system preamble that:
  - States PI is operating inside a dadaia-workspace SDD workspace.
  - **Points at** the law: "Read the workspace-root `AGENTS.md` (loaded natively up-tree) — it is the binding contract." It does **not** copy any AGENTS.md content (anti-§12.3).
  - Names the `dadaia` CLI as the operational surface (`dadaia context show --json`,
    `dadaia specs doctor`, `dadaia lifecycle ...`) and the SDD discipline in one line each,
    by reference — not by restating the gate/lease/phase rules.
  - Documents the trust boundary inline: "These `.pi/` assets run post-trust as
    unsandboxed TS; they carry no secrets and no operator-local paths."
  - **Hard cap: ~30-50 lines.** Anything longer means law is being duplicated — reject.
- **`.pi/settings.json`** — the minimal PI-native settings object (model/tool defaults as
  PI's schema requires). Generic only; no operator-local values. If PI's settings schema is
  not yet pinned, ship the smallest valid object and let ai-engineer expand at implement
  time. (Mirror of how `opencode.json` is a generated minimal config.)
- **`.pi/prompts/` (OPTIONAL)** — include ONLY if PI's prompt/slash schema gives real
  affordance value (e.g. a `dadaia-context` prompt). If it adds nothing over the CLI, omit
  it — minimality wins. Recommendation: ship one small `dadaia-context.md` affordance,
  defer the rest.

## 2.2 — Trust-boundary documentation requirement (non-negotiable)

`.pi/**` is **post-trust, unsandboxed, executable TypeScript** — a real privilege grant.
The release MUST document this in three places (no hand-waving):

1. The §0 layout entry (Deliverable 1.2 above) — done.
2. `.pi/SYSTEM.md` inline note (above).
3. A line in the `public-asset-distribution` memory atom / the `multi-platform-parity`
   atom's Layer-2 note (product-engineer, CLOSURE) distinguishing PI's post-trust executable
   surface from the inert-config surfaces of other targets.

## 2.3 — `dadaia public install --target pi` wiring contract

Mirror the OpenCode target exactly (`infrastructure/public_assets.py` + `_common.py`).
The structural mirror points (verified on disk):

| Mechanism | OpenCode reference | PI change (software-engineer) |
|---|---|---|
| Valid targets | `_VALID_TARGETS = {"all","agents","claude","codex","opencode"}` (`public_assets_common.py:20`) | add `"pi"` → `{..., "pi"}` |
| Per-target dirs | `_OPENCODE_DIRS = ("commands","skills","agents","plugins","workflows")` (`:36`) | add `_PI_DIRS = ("prompts",)` (only the dir(s) that exist in `public/pi/`) — keep minimal |
| install branch | `_install_opencode(...)` (`public_assets.py:533`) | add `_install_pi(...)`: copy `public/pi/` tree → `.pi/`; write generated `.pi/settings.json` via `write_generated` (mirror of `opencode.json`) |
| `targets` tuple | `("agents","claude","codex","opencode")` for `target=="all"` (`:283`) | add `"pi"` → `(..., "pi")` so `--target all` includes PI |
| install dispatch | `elif item == "opencode": self._install_opencode(...)` (`:315`) | add `elif item == "pi": self._install_pi(...)` |
| doctor compare | `runtime_expectations(...)` + `_build_opencode_config` compare (`:347`, `:401`) | add `.pi/` files to the doctor compare set so it emits `[ok] pi:SYSTEM.md`, `[ok] pi:settings.json`, etc.; persists `[drift]`/`[missing]` like every other target |
| manifest | staged assets recorded in `.dadaia/agentic/manifest.json` with SHA256 (lib-originated) | `public/pi/**` staged → manifest-tracked automatically by `stage()`; confirm `.pi/**` projections are listed so the lib-guardrail (non-edit) applies |
| privacy gate | `self._check_public_privacy()` must stay `[ok] public-privacy` (`:413`) | `public/pi/**` MUST contain no private names/paths/IPs — keeps the gate green |
| root-whitelist | `.pi/` must be an allowed root dir | update the `pre_gate` root-whitelist policy + `tmp-file-guardrail` whitelist (see Risks) |

**Acceptance:** `dadaia public stage && dadaia public install --target all && dadaia public doctor`
exits 0 with `[ok] pi:` lines and `[ok] public-privacy`; `dadaia public install --target pi`
projects `.pi/` standalone; `.pi/**` is manifest-tracked.

## 2.4 — Explicitly OUT of scope (WS-PI-4 deferred)

The Ring-1 `.pi/extensions/dadaia-sdd-gate.ts` (a pre-disk PreToolUse-equivalent extension
that would lift PI Layer-1 from advisory to deterministic) is **OUT of this release**.
WS-PI-3 ships the projection scaffold only. The constitution amendment (1.4/1.5) states PI's
Layer-1 posture as advisory + chokepoint with the Ring-1 extension deferred — so the law and
the shipped surface agree, and shipping the scaffold does not over-claim enforcement.

---

# Risks & notes for product-engineer / ai-engineer / software-engineer (before implement)

1. **[HIGH — software-engineer + ai-engineer] Root-whitelist will block `.pi/` if not updated in the same release.** The §0 layout amendment authorizes `.pi/` as a root entry, but the *mechanical* root-whitelist (the `pre_gate` root-whitelist policy and the `tmp-file-guardrail` rule's root whitelist) is the thing that actually blocks new root dirs. If `.pi/` is not added there in the same release, `dadaia public install --target pi` (a file-tool write creating `.pi/`) is blocked by the gate that protects root cleanliness. These are library-surface edits (hook code + the projected rule), NOT constitution edits — sequence them with the projection work.
2. **[MEDIUM — ai-engineer] AGENTS.md native-read assumption.** This design assumes PI reads `AGENTS.md` up-tree natively (operator-confirmed, same as Codex/OpenCode). If PI requires an explicit import bridge (like Claude's `CLAUDE.md`→`@AGENTS.md`), `.pi/SYSTEM.md` must carry a one-line pointer-bridge — still a pointer, never a restatement. Verify PI's AGENTS.md-discovery behavior at implement time before finalizing `SYSTEM.md`.
3. **[MEDIUM — product-engineer + operator] product-vision.md / `docs/01_medium_codex.md` gate (audit D-3).** This design does NOT touch product-vision.md. The two-layer/4-harness reality can only land in product-vision after the operator confirms the normative vision doc's stance. The constitution amendment here is independently applyable (it documents implemented reality + names the deferred Ring-1), but product-vision follows the vision-doc decision. Do not let the constitution amendment imply product-vision is already updated.
4. **[MEDIUM — product-engineer] SPEC-DOC-028 (constitution file-refs resolve).** The amendment introduces no new file references that could break the doctor check; `core/scope_match`, `AgentRuntimePort`, `pi --mode json` are concept/symbol references, not file paths. Confirm `dadaia specs doctor` stays 0-error post-edit.
5. **[LOW — ai-engineer] `.pi/skills/` decision.** Audit G-3 raises whether PI gets a dedicated `ai-harness-pi` deep skill or a `harness-primitives` section. That is a *surface skill* decision separate from the `.pi/` *projection*; do not couple them. This design ships the projection scaffold (`SYSTEM.md`/`settings.json`/optional `prompts`) and defers the skill-authoring decision to the audit's open question (b).
6. **[LOW — software-engineer] `--harness` help text (audit M-4).** The CLI help omits `pi` though `_HARNESS_KINDS["pi"]` is wired. Trivial stale-text fix to fold into the same release for surface honesty.

---

## Summary for the dispatcher

- **Design doc:** this file (`specs/audits/20260625T130028Z-ecddfd86/20260625T143000Z-ecddfd86-pi-operational-two-layer-design.md`).
- **Deliverable 1:** §0 (new "two agentic layers" subsection + layout `.pi/` entry + widened identity line + ai-engineer philosophy clause), §4 (Layer-1-scoped honesty clause + PI row), §8 (split matrix into Layer-1 enforcement + Layer-2 worker posture, PI rows in both). Scaffold stub: **no change recommended**.
- **Deliverable 2:** new `public/pi/` source = `settings.json` + `SYSTEM.md` (points at AGENTS.md, ~30-50 lines) + optional `prompts/`; `_install_pi` mirroring `_install_opencode`; `"pi"` added to `_VALID_TARGETS` + the `all` targets tuple; `[ok] pi:` doctor lines; manifest-tracked; privacy gate green. Ring-1 `.pi/extensions/` = WS-PI-4 deferred.
- **Both anti-slop gates: PASS.** Root cause (no Ring-1 in pi CLI) documented honestly, not worked around; every fact placed in its correct layer.
```
