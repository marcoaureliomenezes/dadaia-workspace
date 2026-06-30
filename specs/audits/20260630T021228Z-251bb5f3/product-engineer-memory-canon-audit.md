---
name: product-engineer-memory-canon-audit
audit: memory-canon
date: 2026-06-30
surface: specs/memory/**
auditor: product-engineer (memory guardian)
scope: catalog integrity, per-atom staleness, feature coverage, constitution<->memory placement, §13 compliance
mode: READ-ONLY + ADDITIVE
---

# Memory Canon Audit — dadaia-workspace

## 0. Executive verdict

The memory canon is **structurally sound but partially stale**. Catalog/atom inventory is
1:1 consistent (27 product atoms, 27 catalog entries, all resolve). The two best-maintained
files (`architecture.md`, `tech-stack.md`, both `release_origin: v0.1.41`,
`last_updated: 2026-06-29`) are current and correctly reflect the **OpenCode removal
(v0.1.24)** and the 4-kind `AgentRuntimeKind`. Staleness clusters in **older atoms that
predate v0.1.24** — chiefly `product-vision.md` (v0.1.19), `harness-primitives.md` (v0.1.18),
`agent-orchestration.md`, `workspace-init.md`, `workspace-portability.md`,
`public-asset-distribution.md` — which still describe OpenCode as a live 4th harness, "five
AgentRuntimeKind", and "PI is the fourth harness".

The single most serious finding is **constitution↔memory conflict on the harness roster**:
memory (correctly, matching code) says OpenCode is removed and there are 4 runtime kinds;
the **constitution still encodes OpenCode as live law** in §0, §4, §5, §8 (incl. the §0
"five AgentRuntimeKinds … FAKE, CODEX_EXEC, CLAUDE_SDK, OPENCODE_RUN, PI_HEADLESS" line and
the §8 Layer-1 enforcement matrix OpenCode row). Durable law now contradicts current truth.

Two structural compliance gaps: (1) `product/index.md` is a **generated catalog table**, not
the §13-mandated structured entry point (vision/users/catalog/capability-map/limits are
absent); (2) the catalog `rank` order is by folder, not the §13-mandated daily-relevance order.

No forbidden changelog/history sections were found in any memory atom (§13 clean on that axis).

---

## 1. Catalog & inventory integrity — VERDICT: PASS (with 2 content-staleness leaks)

- **Atom count == catalog count == 27.** Every `catalog.json` slug resolves to an on-disk
  atom under `specs/memory/product/**`, and every on-disk atom appears in the catalog. No
  orphan atoms, no dangling catalog entries.
  - agents/ (8): agent-comms, agent-monitoring, agent-orchestration, agent-sdd-alignment,
    ai-context-engineering, ai-harness-claude-code, ai-harness-codex, harness-primitives
  - distribution/ (2): academy, public-asset-distribution
  - panel/ (2): brand-identity, panel
  - philosophy/ (3): product-vision, repos-catalog, spec-context-project
  - platform/ (7): context-management, cross-platform-portability, multi-platform-parity,
    server-registry, workspace-doctor, workspace-init, workspace-portability
  - sdd/ (5): lifecycle-foundation, sdd-bug-backlog-governance, sdd-gate-v3,
    sdd-hotfix-track, specs-doctor
- **`quality-assurance.md` correctly absent from the product catalog** — it is a top-level
  `memory/` file (§13 4th canonical area), not a `product/` atom. Consistent.
- **`generated_at: 2026-06-30T02:13:12Z`** is fresh; the catalog was regenerated for this
  cycle. Good — but it regenerated the stale tldrs verbatim (see below).
- **LEAK C1 (MEDIUM):** `catalog.json` + `index.md` carry two stale tldrs/summaries sourced
  from stale atom frontmatter:
  - `public-asset-distribution` tldr: "projected to Claude Code, Codex, **OpenCode**, and
    shared .agents roots" — OpenCode removed v0.1.24.
  - `agent-orchestration` summary: "the minimal **2-workflow** set" — see F-WORKFLOW below.
- **LEAK C2 (LOW):** catalog `rank` is grouped by folder (agents 1–8, distribution 9–10,
  panel 11–12, philosophy 13–15, platform 16–22, sdd 23–27), NOT the §13 "daily-relevance
  order (1 = most used by operator)". Functional ranking is missing.

---

## 2. Per-atom staleness — ranked

### 2a. `architecture.md` (v0.1.41, 2026-06-29) — CURRENT, but OVERSIZED
- token_estimate 13000; on disk ~93 KB / ~1000 lines. Correctly reflects OpenCode removal
  (lines 30, 485, 862–994), 4-kind `AgentRuntimeKind` (line 875), merged `pre_gate`, git
  chokepoints, TTL+PID lease, 7 governed workflows (line 760).
- **GAP/FOCUS (MEDIUM):** the file absorbs deep implementation narrative that duplicates
  dedicated atoms and bloats the architecture snapshot:
  - "Backlog-consistency subsystem" (lines 546–665, ~120 lines) duplicates depth that belongs
    in a backlog atom / `sdd-bug-backlog-governance.md`.
  - "Workflow control plane subsystem (v0.1.28+v0.1.29)" (665–778) and "Workflow-step handoff
    data plane (v0.1.30)" (778–824) duplicate `lifecycle-foundation.md` depth.
  - The `features/` paragraph (line 47) is a single ~600-word run-on listing every module —
    closer to a code index than an architecture contract.
  - **No forbidden changelog section**, but inline version tags ("v0.1.28 adds…", "v0.1.30
    ships…") read changelog-adjacent. Recommend de-versioning to current-state prose.
- **STALE (LOW):** line 756 mentions `claude`/`opencode` rejected on the workflow CLI — keep
  as "rejected harness" set, fine; but line 45 still says "22 subcommands" — verify (not
  blocking).

### 2b. `tech-stack.md` (v0.1.41, 2026-06-29) — CURRENT, BEST-MAINTAINED
- OpenCode explicitly marked REMOVED (lines 46, 150). PI runtime, model registry, handoff
  schema, deps all current. `AgentRuntimeKind` consistent with code.
- **MINOR (INFO):** line 146 says PI needs Node + `ANTHROPIC_API_KEY`, but the PI bullet
  (line 45) and MEMORY both state PI Layer-2 runs under the **operator's Codex subscription →
  GPT models** and auths via `~/.pi/agent/auth.json`, not `ANTHROPIC_API_KEY`. Internal
  inconsistency in the same file — reconcile the auth claim.
- **MINOR (LOW):** "Model assignments (9 core … all `claude-opus-4-8`)" + the reserved
  `claude-fable-5` note are current; no action.

### 2c. `quality-assurance.md` (v0.1.34, 2026-06-28) — CURRENT
- Behavior-first schema, layer taxonomy, budgets (1000–1500), profiles, no-slop law, ownership
  all coherent and §13-aligned (top-level memory file, single source for quality architecture).
- **No staleness, no forbidden sections.** Confirms §13 declaration. PASS.
- **INFO:** references `tests/`, `pyproject.toml`, `ci_preflight/service.py`, `.github/workflows`
  — all real. Solid.

### 2d. `product/index.md` — NON-COMPLIANT with §13 (HIGH)
- Current content is an **auto-generated catalog table** ("Generated automatically from
  `specs/memory/product/*.md` frontmatter … re-run `dadaia memory catalog generate`"),
  effectively a Markdown twin of `catalog.json`.
- **Missing every §13 / product-memory-content-contract required section:** `vision`,
  `users`, `catalog` (as a daily-relevance ordered list with links), `capability-map`
  (Mermaid), `limits` (non-goals). The entry point that should orient a human/agent to the
  product surface does not exist as specified.
- Carries the same OpenCode/2-workflow stale tldrs as the catalog (rows 22, 30).

### 2e. `product-vision.md` (v0.1.19, 2026-06-25) — STALE (HIGH)
Predates v0.1.24. Identity atom (rank 13) read for cross-cutting grounding, so staleness here
propagates widely.
- Line 44–47: "**four entry harnesses** (Claude Code, Codex, **OpenCode**, PI) and **five
  AgentRuntimeKind** worker runtimes … four real (Claude SDK, Codex headless, **OpenCode
  headless**, PI headless) plus FAKE". **Wrong on both counts** — 3 entry harnesses, 4 runtime
  kinds.
- Line 87: pillar 1 projects into "Claude Code, Codex, **OpenCode**, PI". Stale.
- Line 117–123: Layer-1 set "`claude`, `codex`, `opencode`, or `pi`"; Layer-2 "four worker
  runtimes … Claude SDK, Codex headless, **OpenCode headless**, PI headless"; "PI is an
  officially supported **fourth** harness". All stale (PI is third; OpenCode gone).

### 2f. `harness-primitives.md` (v0.1.18, 2026-06-25) — STALE (HIGH)
All-agents literacy skill (read by every core agent), so wrong facts here mislead the whole
fleet.
- Line 9 (summary/frontmatter): projection chain "…install -> .claude/.codex/**.opencode**/.agents".
- Line 36–38: Layer-2 set "`FAKE`, `CODEX_EXEC`, `CLAUDE_SDK`, **`OPENCODE_RUN`**, `PI_HEADLESS`";
  "**PI is the fourth harness** at both layers". Wrong: 4 kinds, no OPENCODE_RUN; PI is third.
- Line 76: projection "relevant Codex/**OpenCode** paths".

### 2g. `agent-orchestration.md` — STALE (MEDIUM/HIGH)
- Line 132: "**OpenCode** uses its own agent and plugin projection." Stale.
- Line 133: "**PI** … the **fourth** harness". Stale (third).
- §"Workflows (2 default)" (lines 104–112): describes only the 2 legacy reference-only
  `.workflow.md` docs (release-ship, audit-fanout) and is **silent on the 7 fragment-driven
  dadaia-workflows** that are now the real workflow surface (architecture.md:760,
  lifecycle-foundation.md:228 both say "7 workflows"; panel shows 12 workflow cards). The
  "minimal 2-workflow set" framing (also in tldr/summary/catalog) is **stale relative to the
  lifecycle engine**. See F-WORKFLOW.

### 2h. `multi-platform-parity.md` — MOSTLY CURRENT, terminology drift (MEDIUM)
- Correctly and repeatedly states OpenCode removed v0.1.24 (lines 14, 39, 51, 58, 136, 162, 166).
- **But tldr/summary assert "2 workflows"** (lines 5, 18) — same stale-vs-engine framing as
  agent-orchestration. The "18 skills / 9 agents" counts are **verified correct** (12 public
  agent files = 9 core + 3 plugin stubs; 18 SKILL.md files). Only the workflow count is
  misleading.

### 2i. `workspace-init.md` — STALE (MEDIUM)
- Line 25: bootstraps "os diretórios de runtime dos **quatro** tools agentic (`.claude/`,
  `.agents/`, `.codex/`, **`.opencode/`**)". Stale — no `.opencode/` is created post-v0.1.24;
  `.pi/` is the current 4th projection dir.

### 2j. `workspace-portability.md` — STALE (MEDIUM)
- Lines 24, 30, 49: export/import bundles "**opencode config**", "**.opencode/**",
  "**opencode.json**". Stale — these paths no longer exist; PI's `.pi/` should be the
  portable surface if any.

### 2k. `public-asset-distribution.md` — STALE (MEDIUM)
- Line 5 (tldr): "projected to Claude Code, Codex, **OpenCode**, and shared .agents roots".
- Line 28, 72, 85: lists `.opencode/`, `opencode.json`, "OpenCode: `.opencode/agents`,
  plugins/hooks, config, skills" as projection targets. Stale — install targets are
  `{agents, claude, codex, pi}` (architecture.md:78, tech-stack.md). This atom feeds the
  catalog tldr leak C1.

### 2l. `sdd-gate-v3.md` — STALE ROW (LOW/MEDIUM)
- Line 260: enforcement table still carries an "**OpenCode** | Plugin TS chama os hooks
  Python via subprocess …" row. The matching `public/plugins/sdd-gate.ts` was deleted
  (architecture.md:78). Drop or mark removed.

### 2m. `cross-platform-portability.md` — STALE ROW (LOW)
- Line 137: "**OpenCode** (`sdd-gate.ts` + `ctx-inject.ts`) chama os Python hooks via
  subprocess." Stale — those plugin assets were removed.

### 2n. `agent-comms.md` — STALE PROJECTION LIST (LOW)
- Lines 38, 64: list `.opencode/` among projection targets for schema/skill. Minor; update
  the projection enumeration to `{.claude, .codex, .pi, .agents}`.

### 2o. `agent-sdd-alignment.md` — STALE (LOW)
- Line 84: "runtime-accurate for Claude Code, Codex, and **OpenCode**." → "…Codex, and PI".

---

## 3. Feature coverage

- **Coverage is broadly complete** for the real product surfaces: context/lease, SDD gate,
  specs-doctor, panel, lifecycle engine, telemetry/monitoring, public distribution, academy,
  server registry, portability, backlog/bug governance, hotfix track, brand identity, and the
  harness-literacy skills each have an atom.
- **GAP F-COV-1 (MEDIUM): PI Layer-1 entry harness has no dedicated atom.** PI is now a
  first-class entry harness with a post-trust Ring-1 `.pi/extensions/dadaia-sdd-gate.ts`
  boundary, but it is described only in scattered paragraphs (architecture, tech-stack,
  multi-platform-parity, sdd-gate). Given there are deep atoms for the Claude Code and Codex
  harnesses (`ai-harness-claude-code`, `ai-harness-codex`), the absence of an equivalent
  `ai-harness-pi` (or a PI section consolidation) is an asymmetry worth a decision.
- **GAP F-COV-2 (MEDIUM): the 7 dadaia-workflows are under-documented as a feature.** They
  exist as fragment bundles (backlog_definition, release_definition, implementation, closure,
  audit, research, bug_report) and are the product's real automation surface, but no atom
  presents the 7-workflow catalog as a feature; `agent-orchestration` still frames "2
  workflows". The panel "Workflows" tab (12 cards) has no memory-side feature description.
- **No atom describes a removed/renamed feature wholesale** — OpenCode staleness is per-line,
  not a whole orphan atom (the dedicated OpenCode concept was never given its own atom, so
  none needs archiving). Good.
- **Over-thin atoms (INFO):** `repos-catalog` (212 tok), `brand-identity` (338),
  `workspace-portability` (336) are thin but each owns a real surface — acceptable.

---

## 4. Constitution ↔ memory placement / duplication map

| Fact | Constitution home | Memory home | Status / correct home |
|------|-------------------|-------------|-----------------------|
| Harness roster (entry harnesses) | §0 "claude, codex, opencode, or pi"; §0 agent-philosophy "the four harnesses"; §4 "Claude Code, Codex, OpenCode, and PI"; §8 Layer-1 matrix OpenCode row | architecture.md, multi-platform-parity.md say `{claude, codex, pi}` (OpenCode removed) | **CONFLICT (CRITICAL).** Code = 3 entry harnesses. Constitution is stale law. Constitution is the durable home for the *set*; it must be amended to drop OpenCode. Memory is correct. |
| `AgentRuntimeKind` set | §0 "five … FAKE, CODEX_EXEC, CLAUDE_SDK, OPENCODE_RUN, PI_HEADLESS"; §8 Layer-2 posture repeats it | architecture.md:875, tech-stack, lifecycle-foundation, multi-platform-parity = 4 kinds (no OPENCODE_RUN) | **CONFLICT (CRITICAL).** Code = 4 kinds. Constitution stale. Amend constitution; memory correct. |
| Allowed root entries incl. `.opencode/` | §0 layout item 5; §5 lists `.opencode/`, `opencode.json` | tech-stack:150 says `.opencode/` no longer exists | **CONFLICT (HIGH).** `.opencode/` should be struck from the §0 ten-entry list / §5 clean-repo list (PI's `.pi/` is the current 4th projection). |
| 8-phase lifecycle / activity classes | §7 (normative table) | product-vision, agent-sdd-alignment, agent-orchestration cite it | **OK — correct citation, no duplication.** Memory summarizes and cites §7; no conflict. |
| 9-core roster + phases | §14 (normative) | agent-orchestration, agent-sdd-alignment, architecture topology section | **OK — cited not duplicated.** Counts verified (9 core + 3 plugin). |
| Anti-slop law | §12 | product-vision pillar 5, quality-assurance no-slop | **OK — cited.** |
| Memory canon definition (4 areas) | §13 | the files themselves | **OK**, but index.md non-compliance (F-§13) means the *declared* `product/**` "index.md entry point" is not as §13 describes. |
| Workflow count | not in constitution | "2 workflows" (orchestration/parity) vs "7 workflows" (architecture/lifecycle) | **INTERNAL memory conflict (MEDIUM).** Single-source the count; see F-WORKFLOW. |
| Two agentic layers | §0 "The two agentic layers" (normative) | architecture "Two-layer agentic model", product-vision, harness-primitives | **OK structurally; but memory copies carry the stale OpenCode/4th-harness numbers.** Align to constitution once constitution itself is corrected. |

**Duplication note (§12.3 single-source):** memory generally cites constitution rather than
duplicating, which is good. The harness/runtime enumerations are the exception — the *same
roster fact* is stated independently in constitution §0/§4/§5/§8 AND in ~10 memory atoms, and
the two sources have now **drifted apart**. This is exactly the §12.3 failure mode. Correct
home: the constitution owns the normative roster *set*; memory atoms should cite it, not
re-list it — and certainly not re-list a now-different set.

---

## 5. §13 memory-canon compliance

- `architecture.md` — present, current. PASS.
- `product/**` (index + atoms) — present; **index.md fails the §13 structured-entry-point
  contract** (FAIL on form; atoms PASS individually subject to staleness above).
- `tech-stack.md` — present, current. PASS.
- `quality-assurance.md` — present, current, top-level. PASS.
- Forbidden sections (`Changelog`/`History`/`Histórico`/`Versions`) — **none found**. PASS.
- Markdown source (no committed `.html`/`.yaml` memory) — PASS (all atoms `.md`).
- Inline version-tag prose ("vX.Y adds…") in architecture.md and lifecycle-foundation.md is
  **changelog-adjacent** but not a forbidden section; recommend de-versioning to current-state.

---

## 6. Prioritized release-scope items (for release-definition synthesis)

Severity key: P0 = correctness/law conflict; P1 = high-traffic staleness; P2 = focus/coverage.

| # | Pri | Change | File(s) | Acceptance criterion |
|---|-----|--------|---------|----------------------|
| R1 | P0 | Amend constitution to drop OpenCode from the harness roster + runtime-kind set + root layout. (Requires explicit operator confirmation — constitution edit.) | `specs/constitution.md` §0, §4, §5, §8 | §0 lists entry harnesses `{Claude Code, Codex, PI}`; §0 says "four AgentRuntimeKinds: FAKE, CODEX_EXEC, CLAUDE_SDK, PI_HEADLESS"; §5/§0 layout no longer lists `.opencode/`/`opencode.json`; §8 Layer-1 matrix has no OpenCode row. No remaining `OPENCODE_RUN` / "five runtimes" / "four harnesses incl OpenCode" in constitution. |
| R2 | P1 | De-stale `product-vision.md`: 3 entry harnesses, 4 runtime kinds, PI is third (not "fourth"), remove OpenCode from pillars/layers. | `memory/product/philosophy/product-vision.md` | grep for `opencode`/`OpenCode`/`OPENCODE`/"five AgentRuntimeKind"/"fourth harness" returns 0 in the atom; counts match code. |
| R3 | P1 | De-stale `harness-primitives.md`: runtime set = 4 kinds, PI third, drop `.opencode/` projection refs. | `memory/product/agents/harness-primitives.md` | 0 OpenCode/OPENCODE_RUN refs; "PI is the fourth" removed; projection chain `.claude/.codex/.pi/.agents`. |
| R4 | P1 | Author the §13-compliant `product/index.md` (vision, users, daily-relevance catalog with links, capability-map Mermaid, limits) — replace the generated table. | `memory/product/index.md` | File contains the 5 required sections; catalog list is link-bearing and relevance-ordered; passes `dadaia specs doctor`. |
| R5 | P1 | Single-source the workflow count: present the 7 dadaia-workflows as the real surface; reframe the "2 default workflows" as legacy reference docs. | `agent-orchestration.md`, `multi-platform-parity.md` (+ regenerate catalog/index) | Atoms state "7 dadaia-workflows" (or cite the engine) and do not assert "minimal 2-workflow set" as the product's workflow surface. |
| R6 | P1 | De-stale projection/runtime atoms (OpenCode → removed; targets `{agents, claude, codex, pi}`). | `public-asset-distribution.md`, `workspace-init.md`, `workspace-portability.md`, `agent-orchestration.md`, `agent-sdd-alignment.md`, `agent-comms.md`, `sdd-gate-v3.md`, `cross-platform-portability.md` | grep `opencode` across `memory/product/**` returns only explicit "removed in v0.1.24" historical mentions, none describing a live surface. |
| R7 | P1 | Regenerate `catalog.json` + `index.md` after R2–R6 so stale tldrs (public-asset-distribution OpenCode; "2 workflows") are gone. | `memory/product/catalog.json`, `index.md` | catalog tldrs contain no OpenCode-as-live or "2-workflow set"; `generated_at` refreshed. |
| R8 | P2 | Reconcile PI auth claim in tech-stack (Codex subscription / `~/.pi/agent/auth.json`, not `ANTHROPIC_API_KEY`). | `memory/tech-stack.md` line 146 | The PI restriction bullet matches the PI runtime bullet; no `ANTHROPIC_API_KEY` claim for PI Layer-2 GPT path. |
| R9 | P2 | Decide PI harness coverage: either add `ai-harness-pi` atom or consolidate a PI section, for symmetry with claude/codex harness atoms. | `memory/product/agents/` (new) or existing | Operator decision recorded; if added, atom + catalog entry exist and resolve. |
| R10 | P2 | Slim `architecture.md`: move backlog-consistency + workflow-control-plane + workflow-step-handoff implementation depth into their owning atoms; de-version inline "vX.Y adds…" prose to current-state. | `architecture.md` (+ `sdd-bug-backlog-governance.md`, `lifecycle-foundation.md`) | architecture.md drops below ~current size meaningfully; no duplicated subsystem narrative; no changelog-adjacent version tags. |
| R11 | P2 | Add daily-relevance ranking to the catalog (§13 ordering) instead of folder grouping. | catalog generation + `index.md` | `rank` reflects operator daily-relevance; rationale documented. |

**Note for synthesis:** R1 is a **constitution** change (durable law) requiring explicit
operator confirmation and is technically outside the memory canon, but it is the *root* of
the largest drift — memory cannot be made fully consistent with the constitution until the
constitution itself stops asserting OpenCode as live law. Sequence R1 first (or in lockstep),
then R2–R7 align memory, then R8–R11 are focus/coverage polish. R2–R7 are all DEFINITION/CLOSURE
memory writes ownable by product-engineer under a release lease.
