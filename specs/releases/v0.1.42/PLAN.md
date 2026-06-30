# PLAN — Release: v0.1.42

**Status:** Aprovado
**Release ID:** v0.1.42

---

## Approach

Specs/memory truth-realignment + two small code changes. The drift is one-directional
(memory & code already agree; the constitution lagged the v0.1.24 OpenCode sweep and
accreted mechanism/changelog), so the plan corrects the **law** first, single-sources the
runtime roster, then reconciles memory against the corrected law, and adds a doctor
invariant to prevent recurrence.

## Single-source decision (root-cause fix)

The harness/runtime roster has **one** canonical home: `specs/memory/tech-stack.md`
(`## Agent runtimes` heading). The constitution states the *invariant/concept* and cites
that atom; it enumerates **zero** concrete `AgentRuntimeKind` members. The §8 lease/gate
*mechanism* lives in `sdd-gate-v3.md` (gate/chokepoints) + `context-management.md`
(lease/mode); the constitution holds only the binding invariants and cites them. WS-E adds
a `specs doctor` invariant enforcing this.

## Ground truth (code, verified 2026-06-30)

- `core/models/lifecycle.py::AgentRuntimeKind` = `{FAKE, CODEX_EXEC, CLAUDE_SDK, PI_HEADLESS}` (4).
- Layer-1 entry harnesses = `{claude, codex, pi}` (PI is the **third**).
- `public install` targets = `{agents, claude, codex, pi}`.
- Workspace root = **nine** entries (`.agents .claude .codex .dadaia .pi repos` + `AGENTS.md CLAUDE.md prompt.md`).
- The 7 dadaia-workflows (release_definition, backlog_definition, audit, research, bug_report, implementation pipeline, closure).
- ~1424 tests (unit 622 / integration 555 / contract 163 / e2e 83 / perf 1).

## Work breakdown & ownership

| WS | Files (disjoint write sets) | Owner |
|----|------|-------|
| A — constitution rewrite + A2 single-source + B1/B6 home atoms | `specs/constitution.md`, `specs/memory/tech-stack.md`, `specs/memory/product/philosophy/product-vision.md` | coordinator (this session) |
| B-de-stale — OpenCode purge + §8 mechanism receivers + index | `harness-primitives`, `agent-orchestration`, `public-asset-distribution`, `multi-platform-parity`, `workspace-init`, `workspace-portability`, `lifecycle-foundation`, `agent-comms`, `agent-sdd-alignment`, `cross-platform-portability`, `sdd-gate-v3`, `context-management`, `product/index.md` | product-engineer #1 |
| B7 + C — architecture de-narrate + QA memory | `specs/memory/architecture.md`, `specs/memory/quality-assurance.md` | product-engineer #2 |
| D + E — code | `infrastructure/fake_runtime.py` (+close path), `features/specs/doctor.py`, tests | software-engineer |
| B8 — catalog regen + validation | `specs/memory/product/catalog.json`, `product/index.md` stamp | coordinator (last) |

Parallel because write sets are disjoint. Coordinator authors WS-A (law + single-source
home) so the canonical roster + citations are coherent; the de-stale atoms cite, never
re-enumerate.

## Validation gates (coordinator, after integration)

1. `grep -ric opencode specs/constitution.md` == 0; OpenCode in memory only as removed/historical.
2. `dadaia specs doctor` — 0 errors (warnings triaged).
3. `dadaia public doctor` — `[ok]` privacy / ai-surface / workflow-policy; no new drift.
4. `dadaia backlog doctor` — no NEW errors from this release.
5. WS-E doctor invariant: red on a roster-enumerating constitution, green on the rewrite.
6. `ruff format --check` + `ruff check --no-cache` + `mypy` + `pytest -p no:cacheprovider -m "not performance"` all green.
7. QA-engineer review of `quality-assurance.md`; software-architect review of the constitution rewrite (architecture-fidelity gate must flip to PASS).

## Risks

- **Normative loss** in the constitution rewrite → mitigated by the per-section migration
  map (`ai-engineer-constitution-audit.md`) + architect review; every binding "must" retained.
- **Concurrent memory writes** → disjoint file sets per owner; catalog regen + full pytest
  run only at the end (no test run mid-write — conftest snapshot guard).
- **architecture.md slim** kept conservative (de-narrate + targeted stale-line fixes +
  re-stamp); deep atom-splitting deferred to avoid breaking citations under time pressure.
