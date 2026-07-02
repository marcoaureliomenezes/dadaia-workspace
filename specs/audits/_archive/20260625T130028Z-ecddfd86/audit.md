# Memory ↔ Implementation Drift Audit — dadaia-workspace

- **Auditor:** project-auditor
- **Date (UTC):** 2026-06-25T13:00:28Z
- **Session discriminator:** ecddfd86
- **Branch:** `feature/pi-operational-v1` (descends from `multiharness-engine-v0116` + `pi-fourth-harness-v1`, both shipped/archived)
- **Anchors:** `specs/constitution.md`, `specs/memory/**` (32 atoms), `specs/memory/product/catalog.json`
- **Evidence agents:** `software-engineer` (code-surface), `ai-engineer` (persona-surface)
- **Mandate:** "Is memory complete, representative of the current implementation, and free of drift?" — output drives a remediation release.

---

## Executive Summary

**Verdict: PARTIAL drift — the engine atoms are current, the surface atoms are not, and the model that the two shipped releases actually delivered is undocumented.** Consolidated score **6.2/10**.

The product-engineer who closed `pi-fourth-harness-v1` updated the three *engine* atoms accurately and deeply — `architecture.md`, `tech-stack.md`, and `lifecycle-foundation.md` correctly document `PiHeadlessAdapter`, `AgentRuntimeKind.PI_HEADLESS`, `GitSubprocessClient.diff_name_only`, `core/scope_match.py`, the `LifecyclePipeline` ladder, and `PromptPrefix`. Code verification confirms those claims are TRUE on disk.

But the update stopped at three atoms. **PI is invisible to the entire AI-entity surface** (0 references across all 12 personas, all 18 skills, all 8 rules, `data/AGENTS.md`), the **product-vision** and **multi-platform-parity** atoms still narrate a closed 3-harness world, and — most importantly — **the two-layer agentic model that is the conceptual core of both releases (Layer 1 = terminal entry harness; Layer 2 = per-step worker harnesses driven inside `dadaia lifecycle` behind `AgentRuntimePort`) is named and explained nowhere in memory or in `public/`.** A new agent grounding itself in memory cannot learn that PI exists or that the lifecycle engine can run any step on any of four worker harnesses.

`catalog.json` is in sync with the atoms (27 features, verified by regenerate-and-diff). `index.md` has exactly one stale row. `dadaia specs doctor` is clean of errors (0 errors / 22 warnings, all WARNING-class).

---

## Scope

**Audited:** all 32 memory atoms under `specs/memory/**`; `specs/constitution.md`; `catalog.json` ↔ atom-frontmatter sync; `index.md` ↔ catalog sync; wikilink integrity; image-ref integrity; memory-heading allowlist (LINT-1); `dadaia specs doctor`; code reality of the two shipped releases (`multiharness-engine-v0116`, `pi-fourth-harness-v1`) via file:line verification; the AI-entity surface in `dadaia_workspace/public/**`.

**Excluded:** security posture (no security-reviewer dispatched — out of mandate scope; security dimension scored INFO/not-assessed), browser/UI surfaces (no frontend plugin installed), live PI/Claude-SDK seam behavior (offline; opt-in `DADAIA_PI_LIVE` / `DADAIA_CODEX_LIVE` harnesses not run), archived releases.

---

## Compliance Scorecard

| Dimension       | Score (1-10) | Drift items | Notes |
|-----------------|-------------|-------------|-------|
| Architecture    | 7           | D-1, D-2, G-1 | Engine layer/module map is accurate and PI is present in prose; but the "Multi-harness runtime parity" table + "três runtimes" line frame a 3-harness world and never name the Layer-1/Layer-2 model. |
| Product         | 6           | D-3, G-1, G-2, M-2 | product-vision + multi-platform-parity stale to 3 harnesses; the two-layer model (the actual deliverable) is undocumented; index.md has 1 stale row. |
| Tech stack      | 9           | (none material) | tech-stack.md fully updated: PI runtime, `pi --mode json`, optional-external-binary constraint, offline-first. Token-estimate frontmatter drift only (M-3). |
| Security        | n/a (INFO)  | —           | Not assessed — no security-reviewer dispatched; out of this audit's mandate. No security-relevant drift observed incidentally. |
| Tests           | 8           | (informational) | quality-assurance.md clean (LINT-1 OK); engine/PI covered by fake-runtime CI + opt-in live harnesses per atoms. Not independently re-measured. |
| Agent-surface   | 3           | D-4, D-5, G-1, G-3 | FLOOR BREACH. PI = 0 references across all personas/skills/rules/AGENTS.md; ai-engineer ("the harness-owning persona") still says "two runtime harnesses"; no `ai-harness-pi` skill; harness-primitives presents a closed 3-harness world. |
| **Overall**     | **6.2**     | 5 DRIFT, 3 GAP, 4 MECHANICS | Weighted avg ≈ 6.2; floor (agent-surface = 3) caps at 5; reported as 6.2 with the floor-breach escalation noted below. Agent-surface < 5 ⇒ score-floor rule triggers a remediation-release recommendation to project-manager. |

Score semantics: 10 = fully conformant; 7-9 = minor drift; 4-6 = moderate drift, some blockers; 1-3 = critical drift, immediate action.

**Floor-breach escalation (rule: any dimension < 5):** agent-surface = 3 mandates a remediation release recommendation via `project-manager`. The PI releases shipped functional code but left the surface that orients the agent fleet unaware the feature exists.

---

## Drift inventory (memory says X; code says Y)

### D-1 — architecture "Multi-harness runtime parity" table omits PI / no layer framing — MEDIUM
- **Memory:** `specs/memory/architecture.md:536-543` "## Multi-harness runtime parity (constitution §4)" — table lists exactly Claude Code, Codex interativo, Codex headless, OpenCode. No PI row; no statement that this table is *Layer-1 entry-harness* parity.
- **Code reality:** `core/models/lifecycle.py:45-50` `AgentRuntimeKind` has 5 members incl. `PI_HEADLESS = "pi_headless"`; `container.py:340-349` wires a real `PI_HEADLESS` branch. PI is a real 4th worker runtime.
- **Why it is still partially TRUE:** the table is about *PreToolUse-hook enforcement per entry harness* — PI is a headless worker with no harness hooks, so it legitimately does not belong in a hook-enforcement table. The drift is the missing *frame*: the table is never labeled "Layer-1 entry harnesses" and there is no companion "Layer-2 worker harnesses (incl. PI)" table.
- **Fix:** add a sentence above the table scoping it to Layer-1 entry harnesses, and add a Layer-2 worker-harness table (FAKE / CODEX_EXEC / CLAUDE_SDK / OPENCODE_RUN / PI_HEADLESS) cross-referencing `lifecycle-foundation.md`.
- **Owner:** product-engineer (CLOSURE/DEFINITION).

### D-2 — architecture "Opera em três runtimes" is stale framing — LOW
- **Memory:** `specs/memory/architecture.md:475` "O subsistema garante que agentes nunca iniciam trabalho sem contexto de produto. **Opera em três runtimes (Claude Code, OpenCode, Codex).**"
- **Code reality:** the *injection* subsystem (`hooks/ctx_inject.py`) genuinely runs in 3 entry harnesses — so the literal claim is TRUE for injection. But the phrasing "três runtimes" reinforces a closed-3 mental model now that PI is a 4th *worker* runtime.
- **Fix:** clarify "três runtimes de entrada (Layer 1)" to disambiguate from the 4 Layer-2 worker harnesses.
- **Owner:** product-engineer.

### D-3 — product-vision declares closed 3-harness support — MEDIUM
- **Memory:** `specs/memory/product/philosophy/product-vision.md:44` "Multi-harness support: Claude Code, Codex, and OpenCode." and `:82-84` pillar 1 "...projects ... into Claude Code, Codex, OpenCode, and generic agent surfaces."
- **Code reality:** 4 worker runtimes ship (`AgentRuntimeKind`, `container.build_agent_runtime`). The vision atom (release_origin v0.2.1, last_updated 2026-06-07) predates both PI releases and was not revisited.
- **Caveat:** product-vision distills the operator-authored `docs/01_medium_codex.md`. If that doc still says 3, the atom is faithful to its source and the *vision doc* is the real drift root — flag for operator. Memory must not unilaterally invent a 4th harness the vision doc omits.
- **Fix:** product-engineer updates the atom to reflect the two-layer model AND the 4-worker-harness reality, but only after the operator confirms the vision doc's stance (raise as a decision).
- **Owner:** product-engineer + operator decision.

### D-4 — ai-engineer persona scoped to "two runtime harnesses" — HIGH
- **Memory/surface:** `dadaia_workspace/public/agents/ai-engineer.md:138` "the AI-entity surface for **two runtime harnesses**"; table `:142-146` = Claude Code (Active), Codex (Active), opencode (Future). No PI row; skill table `:152-156` has no `ai-harness-pi`.
- **Code reality:** PI shipped as a real 4th runtime; the persona that OWNS harness mastery is unaware of it and even undercounts the existing harnesses ("two" while listing three).
- **Fix:** ai-engineer updates its own persona (recursive-bootstrap / ai-entity-refinement) to reflect the 4-worker-harness world and the two-layer model; add a PI row.
- **Owner:** ai-engineer (surface owner; `dadaia public stage && install && doctor`).

### D-5 — harness-primitives skill presents a closed 3-harness world — MEDIUM
- **Surface:** `public/skills/harness-primitives/SKILL.md:15-16` "The harness (Claude Code, Codex, OpenCode) is not the model"; `:52-54` "(OpenCode is a third projection target...)". The corresponding atom `specs/memory/product/agents/harness-primitives.md:27` also still says "**all 15 default agents**" (stale to the 9-core+3-plugin roster since v0.1.8 — a *separate* pre-existing staleness, not PI-related).
- **Code reality:** 9 core agents (constitution §14); 4 worker harnesses.
- **Fix:** ai-engineer updates the skill to a 4-harness-aware, two-layer-aware literacy framing AND fixes the "15 agents" → "9 core" staleness; product-engineer fixes the same in the atom.
- **Owner:** ai-engineer (skill) + product-engineer (atom).

---

## Completeness GAPs (code has X; memory is silent)

### G-1 — The two-layer agentic model is documented NOWHERE — HIGH (top finding)
- **Code reality:** Layer 1 = the terminal entry harness (Claude Code / Codex / OpenCode the operator launches); Layer 2 = bounded agent workers driven inside python lifecycle workflows by `dadaia lifecycle` behind `AgentRuntimePort`, harness-selectable per step: `CLAUDE_SDK` (`claude_sdk_runtime.py`), `CODEX_EXEC` (`codex_runtime.py`), `OPENCODE_RUN` (`opencode_runtime.py`, stub), `PI_HEADLESS` (`pi_runtime.py`), `FAKE`. Selection via `--harness` / `--step-harness` (`cli/commands/lifecycle.py:27-33 _HARNESS_KINDS`).
- **Memory/surface reality:** the phrase "two-layer agentic model" / "Layer 1 / Layer 2 / entry vs worker harness" appears in **0** memory atoms and **0** public/ files. `AgentRuntimePort` appears in `architecture.md` and `lifecycle-foundation.md` but is never tied to an explicit Layer-1/Layer-2 conceptual model an agent can reason from. Closest near-miss: `public/skills/project-orchestration/SKILL.md:108-109` mentions "per-step harness" without explaining selectability or naming the model.
- **Impact:** this is the conceptual core of BOTH shipped releases. Its absence is why every other surface finding exists.
- **Fix:** add a dedicated section to `architecture.md` (and a summary in `product-vision.md`) naming the two-layer model explicitly, with the Layer-2 worker-harness table; cross-reference from `lifecycle-foundation.md`, `multi-platform-parity.md`, and `agent-orchestration`/`harness-primitives`.
- **Owner:** product-engineer (memory) + ai-engineer (surface skills/personas).

### G-2 — multi-platform-parity atom silent on PI / Layer-2 — MEDIUM
- **Code reality:** 4 worker harnesses; PI is headless-only with no first-layer projection tree yet (WS-PI-3 deferred — confirmed in `lifecycle-foundation.md:60`).
- **Memory:** `specs/memory/product/platform/multi-platform-parity.md` (release_origin v0.1.14) describes only Claude/Codex/OpenCode *projections*. PI legitimately has no projection tree, but the atom should at minimum note PI as a Layer-2 worker that projection-parity does not (yet) cover, so the closed-3 list is explicitly scoped to Layer-1 projection.
- **Fix:** add a short "Layer-2 worker harnesses (no projection tree)" note distinguishing projection-parity (Layer 1) from worker-runtime parity (Layer 2).
- **Owner:** product-engineer.

### G-3 — no `ai-harness-pi` skill; PI absent from all skills/rules/AGENTS.md — MEDIUM
- **Surface reality:** skill inventory has `ai-harness-claude-code`, `ai-harness-codex`, `harness-primitives`, `ai-context-engineering` — no `ai-harness-pi` (and no `ai-harness-opencode`). `public/data/AGENTS.md`, all 8 rules: 0 PI references. `rules/bug-registration-guardrail.md:3` "for every runtime (Claude, Codex, OpenCode)" enumerates a closed 3-set.
- **Fix:** decide (ai-engineer + operator) whether PI warrants its own deep harness skill or a section in `harness-primitives`; at minimum update the closed-3 runtime enumerations to be 4-aware or explicitly Layer-1-scoped.
- **Owner:** ai-engineer.

---

## Dead code

No dead/unreachable code attributable to the two releases was found. Specifically verified live and wired:
- `features/orchestration/` dispatch path was retired in WS-3 but is NOT dead — it survives as honest read-only listing + no-op `start_run`/`resume_run` returning `dispatched=False` with `EXECUTION_MOVED_MESSAGE` (`features/orchestration/service.py:70-93`). Correctly documented in `architecture.md:46`.
- `PI_HEADLESS` adapter, `scope_match.py`, `diff_name_only`, `PromptPrefix`, `antislop/{slop_scan,retention}.py`, `LifecyclePipeline` — all reachable and wired (container factory, CLI `_HARNESS_KINDS`, pipeline ladder). No orphans.

Minor non-blocking code-surface observations (not memory drift; for software-engineer awareness only): (a) `_GitDiffPort.diff_name_only(self, cwd)` in `pi_runtime.py:50` vs concrete `GitSubprocessClient.diff_name_only(self, path)` — param-name divergence, works via positional call; (b) `antislop/__init__.py` re-exports only the slop-scan metric, not `RetentionSweep`; (c) `cli/commands/lifecycle.py` `--harness` help strings read "fake|codex|claude|opencode" omitting `pi`, though `_HARNESS_KINDS["pi"]` is wired — stale help text (MECHANICS, see M-4).

---

## Spec consistency

- **ACTIVE.md / release dirs:** no ACTIVE.md pointing at a non-existent release directory detected. Both PI releases are archived under `specs/_archive/releases/`.
- **catalog.json ↔ atoms:** IN SYNC — regenerate-and-diff in a scratch copy produced an identical catalog (27 features); only `generated_at`/`context` fields differ (expected). CAT-1 healthy: no orphan atoms, no missing atoms.
- **index.md ↔ catalog:** exactly **1** stale row (M-1 below).
- **Wikilinks:** all real `[[slug]]` links resolve (the lone `[[slug]]` hit in `specs/memory/AGENTS.md` is a literal placeholder in scoped-rule documentation, not a link).
- **Image refs:** none in memory; nothing to break.
- **`dadaia specs doctor`:** 0 errors, 22 warnings (all WARNING-class; none block). Memory-relevant subset mapped in MECHANICS below.

---

## MECHANICS findings (catalog / index / lint / generator)

### M-1 — index.md stale: lifecycle-foundation row still says "Codex lifecycle foundation" — MEDIUM
- `specs/memory/product/index.md:35` tldr = "Deterministic **Codex** lifecycle foundation ... scoped **Codex exec**." The atom's actual frontmatter tldr (and catalog.json) = "Multi-harness procedural lifecycle engine...". Verified: this is the ONLY index↔catalog mismatch.
- **Root cause:** see M-4 — the `dadaia memory catalog generate` CLI does not regenerate index.md.
- **Fix:** regenerate index.md from catalog (see M-4) during CLOSURE, or fix the row.
- **Owner:** product-engineer (regenerate), plus M-4 product bug fix.

### M-2 — lifecycle-foundation catalog.json/index tldr divergence is masked by injection source — INFO
- The injected session bootstrap reads `catalog.json` first (`hooks/ctx_inject.py:226-228`), falling back to `index.md` only if catalog is absent. Because catalog.json is current, the stale `index.md` does NOT poison agent injection — it only misleads humans reading the panel/index. Lowers the blast radius of M-1 to human-facing.

### M-3 — token_estimate frontmatter drift (LINT-1 WARN) — LOW
- `dadaia specs doctor` LINT-1 flags computed-vs-declared `token_estimate` drift >20% in: `tech-stack.md` (1200 vs ~1802), `lifecycle-foundation.md` (760 vs ~1503, 98% — the PI/engine content grew the atom far beyond its stale estimate), `multi-platform-parity.md` (606 vs ~921), `spec-context-project.md` (700 vs ~886).
- **Fix:** product-engineer refreshes `token_estimate` to computed values during CLOSURE.
- **Owner:** product-engineer.

### M-4 — `dadaia memory catalog generate` CLI cannot emit index.md (product bug) — MEDIUM
- The standalone `generate-memory-catalog.py --index-out` regenerates index.md (`:256 generate_index_md`, `:340-345`), but the `dadaia memory catalog generate` CLI command (`features/specs/catalog.py`) writes **only** catalog.json — it has no index emission. So any CLOSURE that uses the CLI (the canonical path) leaves index.md to silently drift (root cause of M-1).
- **Filed as workspace bug** `memory-catalog-cli-skips-index-md` in `specs/bugs/`.
- **Owner:** software-engineer (CLI surface), via a release.

### M-5 — LINT-1 heading-allowlist WARNs — LOW (curated-allowlist coverage, not content drift)
- 7+ atoms carry `##` headings not in `lint-memory-atoms.py`'s curated allowlist (e.g. architecture's "Multi-harness runtime parity", "Topologia de agentes (9 core + 3 plugins)"; lifecycle-foundation's "Purpose"/"Core services"/"Harness runtime boundary"; etc.). These are legitimate headings the allowlist hasn't caught up to.
- **Fix:** ai-engineer/software-engineer extend the curated allowlist in `lint-memory-atoms.py` (a tooling edit, not memory). Several headings are also English where the allowlist expects Portuguese canon — normalize or allowlist.
- **Owner:** software-engineer (script) — surfaced to PM.

---

## Constitution consistency (`specs/constitution.md`)

The constitution is NOT a memory atom (it is MUTATING-class, product-engineer-owned), but the mandate asked for it. Findings:

- **§0 "What dadaia-workspace is" (lines 27-35):** "runs the same agent fleet across more than one AI coding harness (Claude Code, Codex, and — when installed — OpenCode)" — closed 3-set, no PI, no two-layer model. **DRIFT (MEDIUM).** This is the *entry-harness* sense, so partly defensible, but it is the constitution's identity statement and should acknowledge the Layer-2 worker harnesses.
- **§4 "Runtime Parity Must Be Honest" + the per-harness matrix (lines 173-187, mirrored in §8 lines 378-386):** the enforcement matrix lists Claude Code / Codex interactive / Codex headless / OpenCode. This is *correct* for hook-enforcement (PI runs no harness hooks), but the constitution never names PI as a Layer-2 worker runtime anywhere. **GAP (MEDIUM)** — the constitution defines the harness world and omits the 4th worker harness entirely.
- **Recommendation:** a constitution amendment (product-engineer, operator-confirmed) that (a) names the two-layer model in §0, and (b) adds a normative statement distinguishing Layer-1 entry-harness enforcement (the existing matrix) from the Layer-2 worker-harness set. This requires operator sign-off because the constitution is product law and product-vision's source doc (`docs/01_medium_codex.md`) may also need updating (see D-3).

---

## Recommended actions (priority-ordered; each names the acting agent — auditor never fixes)

1. **[HIGH] Open a remediation release** (floor-breach: agent-surface = 3). → **project-manager** scopes a "PI/two-layer memory fidelity" release; **product-engineer** picks it. Addresses G-1, D-1..D-5, G-2, G-3, M-1, M-3.
2. **[HIGH] Document the two-layer agentic model (G-1)** in `architecture.md` + a `product-vision.md` summary, with the Layer-2 worker-harness table. → **product-engineer** (CLOSURE/DEFINITION memory write).
3. **[HIGH] Update `ai-engineer.md` persona (D-4)** — fix "two runtime harnesses", add PI row, reflect the two-layer model. → **ai-engineer** (ai-entity-refinement; `dadaia public stage && install --target all && doctor`).
4. **[MEDIUM] Update surface skills/rules (D-5, G-3, M-5)** — `harness-primitives` (4-harness + "9 core" fix), closed-3 enumerations in rules/AGENTS.md, extend `lint-memory-atoms.py` allowlist. → **ai-engineer** (skills/rules) + **software-engineer** (lint script).
5. **[MEDIUM] Refresh stale memory atoms (D-2, D-3, G-2, M-3)** — architecture "três runtimes" framing, multi-platform-parity Layer-2 note, token_estimate values; **gate D-3/product-vision on operator confirmation of `docs/01_medium_codex.md`**. → **product-engineer** + operator decision.
6. **[MEDIUM] Fix the index.md generator gap (M-4)** — make `dadaia memory catalog generate` also emit index.md (or have CLOSURE invoke `--index-out`), then regenerate index.md (M-1). → **software-engineer** (CLI) via the release.
7. **[MEDIUM] Constitution amendment** — name the two-layer model in §0 + distinguish Layer-1 enforcement from the Layer-2 worker set. → **product-engineer** + **operator** sign-off.

**Decisions required:** (a) Does `docs/01_medium_codex.md` (the normative vision) acknowledge PI / 4 worker harnesses? If not, operator must decide whether to amend it before memory/product-vision can faithfully follow. (b) Does PI warrant a dedicated `ai-harness-pi` deep skill, or a section in `harness-primitives`?

---

## "Fix set" to reach zero memory ↔ implementation drift

| # | Artifact | Change | Class | Owner |
|---|----------|--------|-------|-------|
| F1 | `architecture.md` | Add "Two-layer agentic model" section + Layer-2 worker-harness table (5 kinds); scope the parity table to Layer-1; fix "três runtimes" framing | MEMORY (CLOSURE/DEFINITION) | product-engineer |
| F2 | `product-vision.md` | Two-layer summary; 4-worker-harness reality (gated on vision-doc confirm) | MEMORY | product-engineer + operator |
| F3 | `multi-platform-parity.md` | Layer-2 worker-harness note distinguishing projection-parity from worker-runtime parity | MEMORY | product-engineer |
| F4 | `harness-primitives.md` (atom) | "15 agents" → "9 core"; 4-harness + two-layer awareness | MEMORY | product-engineer |
| F5 | token_estimate frontmatter (tech-stack, lifecycle-foundation, multi-platform-parity, spec-context-project) | Refresh to computed values | MEMORY | product-engineer |
| F6 | `public/agents/ai-engineer.md` | Fix "two runtime harnesses"; add PI row; two-layer model; PI skill ref | public surface | ai-engineer |
| F7 | `public/skills/harness-primitives/SKILL.md` | 4-harness + two-layer; "9 core" | public surface | ai-engineer |
| F8 | closed-3 enumerations: `rules/bug-registration-guardrail.md`, `data/AGENTS.md`, `plugins/sdd-gate.ts`, `project-orchestration` | Make 4-aware or explicitly Layer-1-scoped | public surface | ai-engineer |
| F9 | `lint-memory-atoms.py` curated allowlist | Add legitimate headings; resolve EN/PT canon | tooling | software-engineer |
| F10 | `features/specs/catalog.py` (CLI) | Emit index.md alongside catalog.json (bug `memory-catalog-cli-skips-index-md`) | code | software-engineer |
| F11 | `index.md` | Regenerate (depends on F10) — fixes the lifecycle-foundation stale row | MEMORY/generated | product-engineer (via F10) |
| F12 | `specs/constitution.md` §0/§4/§8 | Name two-layer model; distinguish Layer-1 enforcement from Layer-2 worker set | MUTATING | product-engineer + operator |

When F1-F12 are applied: PI and the two-layer model are represented across memory + surface, index.md regenerates from a single source, token estimates and the lint allowlist stop warning, and the constitution's harness identity matches the 4-worker-harness implementation. Re-audit at the remediation release's CLOSURE.

---

## Evidence sources

- **Code-surface evidence** (software-engineer sub-agent): verified TRUE on disk with file:line — `core/scope_match.py` (3 fns), `infrastructure/pi_runtime.py:53-146` (`PiHeadlessConfig`/`PiHeadlessAdapter`, argv `pi --mode json --tools ... -p -`), `core/models/lifecycle.py:45-50` (5-member `AgentRuntimeKind` incl. `PI_HEADLESS`), `container.py:303-350` (factory, `PI_HEADLESS` branch), `git_subprocess.py:158-175` (`diff_name_only`), `cli/commands/lifecycle.py:27-33` (`_HARNESS_KINDS` incl `"pi"`), `features/lifecycle/pipeline.py:173-213` (ladder impl=sonnet/reviews=opus), `prompt_builder.py:21-101` (`PromptPrefix`), `antislop/{slop_scan,retention}.py`, `features/orchestration/service.py:70-93` (WS-3 retirement).
- **Persona-surface evidence** (ai-engineer sub-agent): 0 PI references across all 12 personas / 18 skills / 8 rules / `data/AGENTS.md`; `AgentRuntimePort` 0 hits in public/; `ai-engineer.md:138-146` "two runtime harnesses"; `harness-primitives/SKILL.md:15-16,52-54` closed-3; `bug-registration-guardrail.md:3` closed-3.
- **Tooling:** `dadaia specs doctor --specs-dir specs --json` (0 errors / 22 warnings); catalog regenerate-and-diff in scratch (27 features, in sync); index↔catalog tldr diff (1 stale row); wikilink + image-ref integrity scan (clean).
