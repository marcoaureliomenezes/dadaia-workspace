# SPEC: v0.1.19 — Drift Elimination, Memory Diagrams, PI E2E Parity, User README

**Status:** Aprovado
**Release ID:** v0.1.19
**Owner:** product-engineer
**Created:** 2026-06-25
**Branch:** `feature/pi-operational-v1` (continues the unmerged stack; operator holds merges)

## 1. Problem

After v0.1.18 shipped PI as the fourth harness and the two-layer agentic model,
an operator-commissioned four-lens audit (project-auditor + qa-engineer +
security-reviewer + software-architect) found the implementation **sound** but
surfaced a concentrated set of **documentation/memory drift** plus a **stale
user-facing README** and **missing PI end-to-end tests at parity with the other
harnesses**. The workspace contract is "no drift between memory and
implementation"; this release closes the gap.

Audit verdicts (evidence on file):
- **Security:** APPROVED-WITH-FINDINGS — no CRITICAL/HIGH/MED; PI adapter clean
  (no shell, prompt on stdin, redaction correct, Ring-2 git-diff boundary sound,
  `.pi/` inert, 0 repo-lockfile CVEs, root-whitelist opens no hole).
- **Architecture:** APPROVED — "zero engine-spine changes" holds; PI is a true
  structural twin of `CodexExecAdapter`; both layers wired and reachable; 2 LOW
  nits.
- **QA:** QUALIFIED YES — 55–60 PI tests pass; PI is the best-covered non-fake
  harness; genuine gaps (no full-CLI `--harness pi` e2e; untested
  `build_agent_runtime(PI_HEADLESS)` factory branch) are **shared by all four
  harnesses**.
- **Drift:** memory is high-fidelity post-v0.1.18 **except** a fictional
  `claude-fable-5` two-tier model table in `tech-stack.md` (injected into every
  session), a stale `agent-orchestration.md` atom, and several frontmatter
  tldr/summary fields that omit PI and have propagated into the injected catalog.

## 2. Scope

In scope (all driven by audit findings):

### A. Memory drift elimination (MEMORY class — DEFINITION/CLOSURE)
- **MD-1/MD-3 (HIGH):** `tech-stack.md` — purge the fictional `claude-fable-5`
  two-tier model table; state the single real tier (all 9 core agents
  `claude-opus-4-8`); document `claude-fable-5`/`deep` as a reserved-but-unused
  registry entry (no agent resolves to it; region-restricted per operator rule).
- **MD-2 (HIGH):** `agent-orchestration.md` — gate enforces path-class × lease ×
  phase × mode only; it does NOT validate write-allowlists/task-markers/Aprovado
  (RULE-D removed in 0.1.7 rc-3).
- **MD-4 (MED):** `agent-orchestration.md` — 8 public rules, not 5.
- **MD-5 (MED):** `agent-orchestration.md` — add PI to runtime-dispatch honesty;
  re-date the atom to v0.1.19.
- **MD-6 (MED):** `multi-platform-parity.md` — tldr/summary must include PI;
  regenerate `catalog.json` + `index.md`.
- **MD-7 (MED):** `multi-platform-parity.md` — OpenCode plugins invoke the Python
  governance hook via subprocess, not "the same shell scripts".
- **MD-8 (LOW):** `product-vision.md` — five `AgentRuntimeKind`s (four real worker
  runtimes + FAKE), not "four".
- **MD-9 (LOW):** `architecture.md` — `orchestrate` retains inert `run/status/
  resume` compat stubs; execution moved to `dadaia lifecycle`.

### B. Memory mermaid diagrams (MEMORY class) — human-readable, well-designed
- **DG-1 (HIGH):** `lifecycle-foundation.md` — two-layer + pipeline-ladder diagram.
- **DG-2 (HIGH):** `architecture.md` — the two-layer agentic model diagram.
- **DG-3 (MED):** `agent-orchestration.md` — 9-core agent topology / dispatch graph.
- **DG-6 (MED):** `quality-assurance.md` — five-layer test pyramid + CI jobs.
- **DG-4/DG-5 (LOW):** `tech-stack.md` dependency-by-ring diagram; verify
  `specs-doctor.md` has an invariant-flow diagram (add if missing).

### C. Constitution (MUTATING)
- **CONST-1 (LOW):** §11 — the "gate ladder law-deferred to v0.1.15" phrasing reads
  as stale-future at v0.1.18+; correct the tense to a past/shipped reference.

### D. Code (MUTATING)
- **PKG-1:** `pyproject.toml` `description` must include PI (currently "Claude
  Code, Codex and OpenCode").
- **ARCH-NIT-1:** rename `_GitDiffPort.diff_name_only` parameter `cwd` → `path` to
  match its sole implementer `GitSubprocessClient.diff_name_only(path)`.

### E. Tests — PI E2E parity (MUTATING)
- **QA-1 (HIGH):** factory wiring — `build_agent_runtime(PI_HEADLESS)` returns a
  `PiHeadlessAdapter` carrying a real git seam.
- **QA-2 (HIGH):** Layer-2 CLI e2e — `dadaia lifecycle` selecting `--harness pi`
  end-to-end against an injected fake `pi --mode json` stream; assert the step
  runtime is `pi_headless` and the engine honors the verdict.
- **QA-3 (MED):** Layer-1 projection through the real CLI — `dadaia public install
  --target pi` + `dadaia public doctor` against a temp workspace.
- **QA-4 (MED):** Layer-1 governance-content assertion — projected
  `.pi/SYSTEM.md` / `prompts/dadaia-context.md` carry the workspace-law/SDD
  governance markers.

### F. User README (MUTATING)
- Full rewrite to the current architecture: four supported harnesses **including
  PI**; the **two agentic layers**; the **workflow** concept (`dadaia lifecycle`
  pipeline implement→qa→security→code); the **development lifecycle phases**
  (DEFINITION→IMPLEMENTATION→reviews→CLOSURE); the current CLI command surface;
  remove stale claims (retired `sdd-spec-gate.sh`, hardcoded panel version
  `0.1.2`, the stale 3-harness table, the stale CLI table).

Out of scope (deferred, recorded): WS-PI-4 Ring-1 `.pi/extensions/` gate; RPC/SDK
transports; WS-PI-6 telemetry; removal (vs documentation) of the reserved
`claude-fable-5`/`deep` registry tier; formal `dadaia-pi-workspace` context
DEAD-mark; the stale `specs/releases/v0.1.12` un-archived dir (PM/PE decision).

## 3. Acceptance criteria

1. `dadaia specs doctor` exits 0 (no new errors).
2. `dadaia public doctor` exits 0 with `[ok] public-privacy`.
3. `dadaia ci preflight` green (ruff format/check + mypy --strict + pytest).
4. `poetry build` produces a wheel (the project "compiles").
5. No memory atom asserts a fact contradicted by code; a fresh drift re-audit
   reports zero unresolved drift.
6. Targeted memory atoms (`architecture`, `tech-stack`, `quality-assurance`,
   `lifecycle-foundation`, `agent-orchestration`) carry well-designed mermaid
   diagrams; `catalog.json`/`index.md` regenerated.
7. New PI tests added (QA-1..QA-4) and passing; PI E2E parity achieved at both
   agentic layers.
8. README accurately describes: 4 harnesses incl PI, the two agentic layers,
   workflows, the lifecycle phases, and the real CLI surface.
9. Full review gate ladder run on the closing tip: QA + code-review + security,
   each APPROVED; push gated by a security APPROVE handoff keyed to the pushed sha.

## 4. Non-goals

No engine-spine refactor, no new runtime transport, no harness behavior change.
This is a documentation/memory/test/README fidelity release on top of the
already-shipped, already-reviewed v0.1.18 implementation.
