# SPEC — Release: v0.1.42

**Status:** Aprovado
**Release ID:** v0.1.42
**Owner:** product-engineer
**Opened:** 2026-06-30

---

## 1. Problem and context

A full 5-auditor audit (2026-06-30, `specs/audits/20260630T021228Z-251bb5f3/`, overall
drift 7.2/10) found the **supreme governing doc is the most stale artifact in the tree**.
`specs/constitution.md` still encodes the removed **OpenCode** harness and a 5-member
`AgentRuntimeKind` as live law, contradicting the code (`core/models/lifecycle.py` →
`{FAKE, CODEX_EXEC, CLAUDE_SDK, PI_HEADLESS}`) and its own subordinate memory atoms
(which already match the code). It also asserts "ten allowed root entries" where the
enforced law is **nine** (contradicting `AGENTS.md`).

Two structural problems compound the drift:
1. The constitution is **~65% mechanism/vision/changelog** (§0 = 184 lines, §8 = 159,
   §11 = 80 — 64% of 663). SDD best practice (GitHub Spec-Kit) holds a constitution to a
   small set of immutable, *verifiable* principles; their own brownfield constitution is
   ~214 lines of principle+rationale with version history in a separate header.
2. The harness/runtime roster is **double-sourced** across constitution §0/§4/§5/§8 and
   ~10 memory atoms (§12.3 self-violation) — which is precisely why the copies diverged.

Source: backlog candidate `specs/backlog/specs-truth-realignment-constitution-memory.md`
+ the five audit reports.

## 2. Objective

Realign the specs with reality: rewrite the constitution to a lean, single-sourced,
OpenCode-free set of verifiable principles (~200 lines); de-stale the memory canon
against the live code; fix the one open bug; and add a doctor invariant so this class of
constitution↔code drift fails CI instead of silently rotting.

## 3. Scope

Acceptance is grouped into work-streams (full task list in `PLAN.md`/`TASKS.md`).

### WS-A — Constitution lean rewrite (`specs/constitution.md`)
- **A1 (CRITICAL):** Purge OpenCode / `OPENCODE_RUN` / `.opencode` / "five
  AgentRuntimeKinds" / "ten root entries". **AC:** `grep -ci opencode
  specs/constitution.md` == 0; runtime statements set-equal to `AgentRuntimeKind`; root
  layout lists nine entries; no OpenCode matrix row.
- **A2 (root-cause):** Single-source the roster — constitution enumerates zero concrete
  `AgentRuntimeKind` members; states the invariant and cites memory. **AC:** the concrete
  set appears in exactly one memory atom; constitution cites it.
- **A3:** Collapse §8 (159 lines) to a ≤ ~20-line binding-invariant block; move mechanism
  (lease schema, O_EXCL CAS, 4-step mode chain, chokepoint probe steps, TTL literal,
  enforcement matrices) to `sdd-gate-v3` / `context-management`. **AC:** §8 successor ≤ 20
  lines holding only invariants; mechanism present in exactly one memory atom.
- **A4:** Move §0 vision/value-prop → `product-vision`; two-agentic-layers/root-layout →
  `architecture`; keep a ~18-line normative Definitions section; "ten" → "nine". **AC:**
  §0 successor ≤ ~20 lines; no normative loss.
- **A5:** Strip embedded dated amendments/changelog; add a Governance + version-header
  section (constitution semver + amendment log). **AC:** no dated "Amendment / codified in
  vN / supersedes / maps to vN" strings inside articles.
- **A6:** De-pin tunable literals (`LEASE_TTL_SECONDS=120`) to a pointer. **Target:** ≈ 200
  lines, principle+rationale, each principle verifiable.

### WS-B — Memory realignment (`specs/memory/**`)
- **B1 (HIGH):** De-stale `product-vision`, `harness-primitives` (3 entry harnesses, 4
  runtime kinds, PI third). **AC:** no "four/fourth harness"/`OPENCODE_RUN`/`.opencode`.
- **B2:** De-stale the projection/runtime atoms naming OpenCode live (`agent-orchestration`,
  `workspace-init`, `workspace-portability`, `public-asset-distribution`,
  `multi-platform-parity`, + residue in `sdd-gate-v3`, `cross-platform-portability`,
  `agent-comms`, `agent-sdd-alignment`). **AC:** OpenCode only as removed/historical.
- **B3:** Author a §13-compliant `product/index.md` (vision/users/ordered-catalog/
  capability-map/limits). **AC:** all five present.
- **B4:** Single-source the workflow count to the 7 dadaia-workflows; reframe the legacy
  "2 workflows" framing. **AC:** the 7 documented in one atom; no stale "2 workflows".
- **B6:** Fix the `tech-stack` PI-auth contradiction (Codex subscription /
  `~/.pi/agent/auth.json`, not `ANTHROPIC_API_KEY`). **AC:** one auth statement.
- **B7 (HIGH):** De-narrate + slim `architecture.md` (remove inline `(v0.1.NN)`/"replaced"/
  "collapse removed"); fix stale lines (`OPENCODE_SESSION_ID`, import-linter "6 contracts/
  17 edges", "23 subcommands"); re-stamp `token_estimate`. **AC:** no changelog prose; core
  atom materially smaller; doctor green.
- **B8:** Regenerate `catalog.json` + `index.md`. **AC:** no OpenCode/"2-workflow" tldr; 1:1
  atom↔entry.

### WS-C — Quality-assurance memory (`specs/memory/quality-assurance.md`)
- Re-validate budgets vs ~1424 live tests; document auto-marker-by-directory, the separate
  Playwright/Node panel-e2e job + cross-platform matrix, conftest safety guards; move the
  v0.1.34 collapse narrative → that release CLOSURE; reconcile coverage prose with the 80%
  CI gate; bump `last_updated`/`release_origin`. **AC:** every budget bracket contains the
  live count; no collapse-narrative; QA APPROVE.

### WS-D — Open bug (`dadaia_workspace/infrastructure/fake_runtime.py`)
- Fix `lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence` (MEDIUM): the FAKE
  closure path emits valid evidence or rejects/warns `--harness fake` up front. **AC:** a
  `lifecycle close --harness fake` smoke advances or fails fast with an actionable message;
  regression test; bug → Closed.

### WS-E — Recurrence prevention (`dadaia_workspace/features/specs/doctor.py`)
- Add a doctor invariant: the constitution hard-codes no `AgentRuntimeKind` member /
  harness enumeration (must cite memory). **AC:** the check fails on a constitution that
  enumerates runtime kinds; green on the rewrite; covered by a test.

## 4. Out of scope

- The `sdd-governance-v2-agents-lifecycle` epic (bug-telemetry JSONL + audit-disposition
  law) — separate release.
- Panel UX overhaul, model-tier-efficiency, plugin-packs, and other VALID-PICK backlog
  debt not required for specs compliance.
- No production behavior change beyond WS-D/WS-E; this is primarily a specs/memory
  truth-realignment release.

## 5. Dependencies and risks

- **Sequencing:** WS-A1+A2 land first (corrected, single-sourced law) → WS-B/WS-C reconcile
  memory against it → WS-B8 regenerate catalog last → WS-D/WS-E (code) in parallel.
- **Risk — normative loss:** the constitution is LAW; the rewrite must preserve every
  binding "must". Mitigation: per-section migration map in the audit; QA/architect review.
- **Risk — single-source home:** pick exactly one atom for the runtime roster
  (`tech-stack#agent-runtimes`) and have all others cite it; the WS-E doctor invariant
  guards recurrence.
- **Lease note:** this is a MUTATING release; it runs under one implementation lease for
  the dadaia-workspace context (acquired this session after the prior archived-release
  lease was released — see bug `lease-pid-veto-ignores-archived-release-blocks-next-release`).
