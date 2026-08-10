# RE-AUDIT — Memory ↔ Implementation Drift VERIFICATION — dadaia-workspace v0.1.18

- **Auditor:** project-auditor
- **Date (UTC):** 2026-06-25T15:18:58Z
- **Session discriminator:** ecddfd86
- **Mandate (operator closure gate):** "Memory must be complete, representative of the current implementation, and have NO drift." This re-audit verifies the first audit's findings are ELIMINATED.
- **Prior audit:** `specs/audits/20260625T130028Z-ecddfd86/audit.md` (consolidated 6.2/10; agent-surface FLOOR BREACH 3/10).
- **Anchors:** `specs/constitution.md`, `specs/memory/**` (27 atoms), `catalog.json`.
- **Evidence agents (read-only):** `software-engineer` (code-surface), `ai-engineer` (persona-surface). Memory-atom + constitution + doctor + catalog/index verification done firsthand by the auditor.
- **Discipline:** ADDITIVE evidence only. Nothing edited, staged, installed, or committed.

---

## Executive Summary

**Verdict: ALL prior findings RESOLVED. Memory is now complete, representative of the shipped implementation, and drift-free** (modulo the transient SPEC-DOC-024 closure-sequencing artifact, which is NOT memory drift). Consolidated memory-fidelity score **9.4/10**; agent-surface lifted from **3 → 9**. The score floor (any dimension < 5 ⇒ remediation release) is cleared.

The two-layer agentic model is now named and explained across `architecture.md`, `product-vision.md`, `multi-platform-parity.md`, and `constitution.md §0/§4/§8`, with honest Layer-1 (entry/PreToolUse) vs Layer-2 (worker/`AgentRuntimePort`) framing. PI is a first-class fourth harness at both layers across memory and the entire AI-entity surface (0 → 14 surface references). The `dadaia memory catalog generate` CLI now emits index.md (bug `memory-catalog-cli-skips-index-md` Resolved), index.md is in sync, and the LINT-1 token_estimate WARNs are gone.

---

## Per-finding verdicts

| Prior finding | Severity | Verdict | Evidence |
|---|---|---|---|
| **G-1** two-layer model documented NOWHERE | HIGH | **RESOLVED** | `architecture.md:538-590` dedicated "Two-layer agentic model" section + a Layer-1 enforcement-parity table (`:568-576`) + a Layer-2 worker-runtime posture table with all 5 kinds incl `PI_HEADLESS` (`:580-588`). Summary in `product-vision.md:112-122`; cross-refs in `multi-platform-parity.md:36-54` and constitution `§0`. Surface: 8 public files now carry the model (see Item-2 below). |
| **D-1** parity table omits PI / no layer framing | MEDIUM | **RESOLVED** | `architecture.md:549-550` scopes the parity table to "Layer-1 entry-harness"; the companion Layer-2 table (`:580-588`) lists FAKE/CODEX_EXEC/CLAUDE_SDK/OPENCODE_RUN/PI_HEADLESS. |
| **D-2** "Opera em três runtimes" stale framing | LOW | **RESOLVED** | `architecture.md:475` now reads "três runtimes de entrada — Layer 1 … o quarto harness PI (`pi`) é um worker de Layer 2 headless…". |
| **D-3** product-vision closed 3-harness | MEDIUM | **RESOLVED** | `product-vision.md:44-45` "four entry harnesses (Claude Code, Codex, OpenCode, PI) and four worker harnesses"; `:112-122` two-layer summary. |
| **D-4** ai-engineer.md "two runtime harnesses" | HIGH | **RESOLVED** | `public/agents/ai-engineer.md:138` now "four runtime harnesses across two agentic layers"; PI row in harness table (`:157`); two-layer block + 5 `AgentRuntimeKind`s (`:143-150`). |
| **D-5** harness-primitives closed-3 + "15 agents" | MEDIUM | **RESOLVED** | `public/skills/harness-primitives/SKILL.md:16,22-28,62-65,132` 4-harness + two-layer + PI; the stale "15 agents" claim is removed entirely (grep: 0 matches for `15 `/`agents`). |
| **G-2** multi-platform-parity silent on PI/Layer-2 | MEDIUM | **RESOLVED** | `multi-platform-parity.md:36-54` "Two-layer scope: projection-parity vs worker-runtime parity" — Layer 1 = this atom's projection parity; Layer 2 = worker runtimes (incl `PI_HEADLESS`) with "no projection tree"; "PI shipped here first". |
| **G-3** no PI in skills/rules/AGENTS.md | MEDIUM | **RESOLVED** | `rules/bug-registration-guardrail.md:3` now "Layer-1 entry harness (Claude, Codex, OpenCode, PI)"; `rules/tmp-file-guardrail.md:42,52-53` + `data/AGENTS.md:27-36` add `.pi/` as a post-trust-executable Layer-1 projection. 14 PI surface references total (prior 0). |
| **Agent-surface floor breach (3/10)** | — | **RESOLVED** | Surface lifted to 9. PI represented across agents/skills/rules/AGENTS.md; `plugins/sdd-gate.ts:6-9` references PI **honestly** — scopes PreToolUse to Claude/Codex/OpenCode and states PI exposes no pre-disk hook (advisory + git-chokepoint), no false Ring-1 claim. |
| **Constitution (F12) §0/§4/§8** | MEDIUM | **RESOLVED + HONEST** | §0 two-layer model `:29-30,:116-144` (Layer-2 runtimes incl PI_HEADLESS `:142`); §4 honesty clause Layer-1-scoped `:222-234` (PI = advisory + chokepoint, Ring-1 deferred); §8 Layer-1 matrix with PI row `:439` ("no Ring-1") + Layer-2 posture `:441-446`. PI Layer-2 = Ring-2 + chokepoints, NO Ring-1 — honest. |
| **M-1** index.md "Codex lifecycle foundation" stale row | MEDIUM | **RESOLVED** | `index.md:35` lifecycle-foundation row now "Multi-harness procedural lifecycle engine…". Regenerate-and-diff: CLI-regenerated index.md is byte-identical (modulo context-name title line). |
| **M-4** CLI skips index.md (product bug) | MEDIUM | **RESOLVED** | `features/specs/catalog.py:262 render_index_md`, `:298-309 write_index`; wired in CLI `cli/commands/memory.py:15,116` (`[ok] index.md written`). Bug file frontmatter `status: Resolved`. Confirmed live: `dadaia memory catalog generate` emitted both `catalog.json` and `index.md`. |
| **LINT-1** token_estimate drift (4 atoms) | LOW | **RESOLVED** | `dadaia specs doctor --json` shows ZERO LINT-1 issues. Declared vs computed now within threshold (tech-stack 1800/~1810, lifecycle-foundation 1500/~1660, multi-platform-parity 1300/~1376, spec-context-project 885/~977). |
| **M-5** heading-allowlist WARNs | LOW | **RESOLVED** | No LINT-class warnings in doctor output. |

---

## True zero-drift checks over SHIPPED code (firsthand + software-engineer evidence)

- **5 AgentRuntimeKinds** — CONFIRMED `core/models/lifecycle.py:45-50` (FAKE/CODEX_EXEC/CLAUDE_SDK/OPENCODE_RUN/PI_HEADLESS).
- **`infrastructure/pi_runtime.py`** — CONFIRMED `PiHeadlessConfig:53` / `PiHeadlessAdapter:65`; argv `pi --mode json --tools … -p -` (`:135-146`); `changed_paths` from injected git diff seam, not model self-report — a real Ring-2 boundary.
- **container PI_HEADLESS branch** — CONFIRMED `container.py:340-349` (factory total over the enum).
- **CLI `pi` harness** — CONFIRMED `cli/commands/lifecycle.py:32 _HARNESS_KINDS["pi"]`.
- **`.pi/` Layer-1 projection + `pi` install target** — CONFIRMED PRESENT (WS-PI-3/4 landed): `_VALID_TARGETS` incl `pi` (`public_assets_common.py:20`); `_install_pi` (`public_assets.py:582-599`) stages `public/pi/{SYSTEM.md,settings.json,prompts/}` → `.pi/`; root-whitelist allows `.pi` (`hooks/root_whitelist.py:31`). Memory's "`.pi/` (Layer-1 PI, target `pi`)" claim (`architecture.md:29`) is TRUE.
- **Dead code** — NONE introduced. `pi_runtime.py` reachable via container factory; index-emission reachable via CLI. `features/orchestration` retirement remains honest read-only (no change).
- **Projection consistency** — `dadaia public doctor` exit 0; zero `[drift]`/`[missing]`; PI assets project cleanly; `[ok] public-privacy`.
- **catalog ↔ atoms** — IN SYNC (regenerate-and-diff: identical feature set, 27 features, only `context`/`path`-prefix differ due to scratch-copy). All 27 catalog paths exist on disk. No orphan/missing atoms.
- **Wikilinks** — `[[architecture]]`, `[[lifecycle-foundation]]` etc. resolve.

---

## `dadaia specs doctor --specs-dir specs --json` result

- **1 error:** `SPEC-DOC-024` — ACTIVE.md phase=CLOSURE but release v0.1.18 has 1 unfinished task marker. **Classified TRANSIENT / NON-DRIFT** — expected closure-sequencing artifact; the coordinator clears it by archiving (git mv + ACTIVE→none). NOT memory↔implementation drift.
- **23 warnings, none memory-drift:** SPEC-DOC-016 (8, legacy archive SemVer names) · SPEC-DOC-027 (2, legacy archived release names) · SPEC-DOC-029 (3, stale leases in OTHER contexts — dadaia-pi-workspace/sample-consumer/sample-explorer) · SPEC-DOC-030 (1, old audit-dir name) · SPEC-DOC-031 (5, backlog non-terminal status referenced by archived releases — ADR-6 false-positive class) · SPEC-DOC-032 (3, bug `status: Resolved` outside the {Open,Closed} canon — incl. the M-4 bug) · TREE-5 (1, `specs/AGENTS.md` template drift). **Zero LINT-1; zero CAT-1; zero memory-atomicity errors.**

Two residual NON-MEMORY cosmetic code observations (software-engineer evidence; not drift, for software-engineer awareness only): `cli/commands/lifecycle.py --harness` help strings and `cli/commands/public.py:20 --target` help omit `pi` though both validators accept it. These are operator-facing help-text staleness, not memory drift — recommend a backlog/hotfix note via project-manager. (Minor SPEC-DOC-032 normalization of the three `Resolved` bug statuses → `Closed` is a doctor-canon hygiene item, also non-drift.)

---

## Updated scorecard

| Dimension | Prior | Now | Notes |
|---|---|---|---|
| Architecture | 7 | 9 | Two-layer model + Layer-1/Layer-2 tables present; PI in module map (`.pi/` projection, `pi` target). |
| Product | 6 | 9 | product-vision + multi-platform-parity carry two-layer + 4-harness reality; index.md in sync. |
| Tech stack | 9 | 10 | token_estimate refreshed; LINT-1 clean. |
| Security | n/a | n/a | Not re-assessed (out of mandate; no incidental drift). |
| Tests | 8 | 8 | Not independently re-measured; engine/PI fake-runtime + opt-in live harnesses per atoms. |
| Agent-surface | **3** | **9** | FLOOR BREACH CLEARED. PI 0→14 surface refs; ai-engineer 4-harness/two-layer; sdd-gate.ts honest; no projection drift. |
| **Overall memory-fidelity** | **6.2** | **9.4** | Floor (min over scored dims, ignoring n/a) = 8 (Tests). Weighted ≈ 9.4. No floor breach. |

---

## Plain verdict

**Memory for v0.1.18 is COMPLETE, REPRESENTATIVE of the current implementation, and DRIFT-FREE** — every prior finding (G-1, D-1..D-5, G-2, G-3, M-1, M-4, LINT-1, M-5, constitution F12) is RESOLVED with file:line evidence; the two-layer model and the 4th PI harness are honestly represented across memory, the constitution, and the entire AI-entity surface; index.md regenerates from a single source and is in sync; the score floor is cleared. The lone `dadaia specs doctor` error (SPEC-DOC-024) is the transient CLOSURE-in-progress artifact, NOT drift — it clears when the coordinator archives the release. **The operator closure gate is satisfied (modulo archiving the release to clear SPEC-DOC-024).**

No remediation release recommended. Recommended NON-blocking follow-ups for project-manager (backlog, not closure-blocking): (a) update `--harness`/`--target` CLI help strings to list `pi`; (b) normalize the three `status: Resolved` bug files to `Closed` (SPEC-DOC-032 canon).

---

## Evidence sources

- **Code-surface (software-engineer sub-agent, read-only):** `core/models/lifecycle.py:45-50`, `infrastructure/pi_runtime.py:53-146`, `container.py:340-349`, `cli/commands/lifecycle.py:27-33`, `features/specs/catalog.py:262,298-309`, `cli/commands/memory.py:15,116`, `infrastructure/public_assets.py:284,318-319,582-599`, `public_assets_common.py:20`, `public/plugins/sdd-gate.ts:6-9`, `hooks/root_whitelist.py:31`.
- **Persona-surface (ai-engineer sub-agent, read-only):** `public/agents/ai-engineer.md:138,143-157`, `public/skills/harness-primitives/SKILL.md:16,22-28,62-65,132`, `public/skills/project-orchestration/SKILL.md:111`, `public/rules/bug-registration-guardrail.md:3`, `public/rules/tmp-file-guardrail.md:42,52-53`, `public/data/AGENTS.md:27-36`, `public/plugins/sdd-gate.ts:6-9`; `dadaia public doctor` exit 0, 14 PI refs.
- **Auditor firsthand:** `specs/memory/architecture.md:29,475,538-595`; `specs/memory/product/philosophy/product-vision.md:44-45,112-122`; `specs/memory/product/platform/multi-platform-parity.md:32-54`; `specs/constitution.md:29-30,96,116-144,222-234,430-446`; `specs/memory/product/index.md:35`; `specs/bugs/memory-catalog-cli-skips-index-md.md` (status Resolved); catalog regenerate-and-diff (scratch, 27 features in sync); `dadaia specs doctor --specs-dir specs --json` (1 error SPEC-DOC-024 transient / 23 non-memory warnings / 0 LINT-1).
