---
name: specs-truth-realignment-constitution-memory
title: Specs Truth Realignment — lean the constitution, single-source the runtime roster, de-stale memory
status: candidate
opened: 2026-06-30
owner: project-manager (curates) → product-engineer (authors under PM release lease)
source: full audit 2026-06-30 — specs/audits/20260630T021228Z-251bb5f3/ (5 specialist reports + 00-INDEX)
intents:
  - subject: { kind: doc, ref: "memory/tech-stack.md#agent-runtimes" }
    change: "WS-A2/B6 (root-cause single-source): make tech-stack#agent-runtimes the ONE home for the harness/runtime roster — {claude,codex,pi} + AgentRuntimeKind {FAKE,CODEX_EXEC,CLAUDE_SDK,PI_HEADLESS}; drop OpenCode/OPENCODE_RUN; fix the PI auth contradiction (Codex subscription / ~/.pi/agent/auth.json, not ANTHROPIC_API_KEY). Constitution then cites this, enumerates nothing"
  - subject: { kind: doc, ref: "memory/architecture.md#camadas" }
    change: "WS-B7: de-narrate architecture.md (remove inline (v0.1.NN)/'replaced'/'collapse removed' changelog prose) and slim by extracting subsystem depth to owning atoms via citation; fix stale lines (OPENCODE_SESSION_ID L501, import-linter '6 contracts/17 edges' L344, '23 subcommands' L45); re-stamp token_estimate"
  - subject: { kind: doc, ref: "memory/quality-assurance.md#Propósito" }
    change: "WS-C: re-validate test budgets vs 1424 live tests; document auto-marker-by-directory, the separate Playwright/Node panel-e2e job + cross-platform matrix, and conftest safety guards; move the v0.1.34 collapse narrative to that release's CLOSURE; reconcile the coverage statement with the hard 80% CI gate; bump last_updated/release_origin"
  - subject: { kind: catalog, ref: "product-vision" }
    change: "WS-B1: de-stale to 3 entry harnesses / 4 AgentRuntimeKind / PI-is-third (currently asserts four harnesses incl OpenCode, five kinds incl OPENCODE_RUN)"
  - subject: { kind: catalog, ref: "harness-primitives" }
    change: "WS-B1: de-stale the all-agent literacy atom — runtime set drop OPENCODE_RUN, PI third not fourth, remove .opencode/ projection"
  - subject: { kind: catalog, ref: "public-asset-distribution" }
    change: "WS-B2: drop OpenCode / .opencode/agents / opencode.json projection targets (install targets are {agents,claude,codex,pi})"
  - subject: { kind: catalog, ref: "multi-platform-parity" }
    change: "WS-B2: fix the residual '2 workflows' tldr; confirm OpenCode-removed throughout"
  - subject: { kind: catalog, ref: "workspace-init" }
    change: "WS-B2: bootstraps no longer create .opencode/ — drop the 'quatro tools' / .opencode bootstrap claim"
  - subject: { kind: catalog, ref: "workspace-portability" }
    change: "WS-B2: export paths no longer include opencode config / .opencode/ / opencode.json"
  - subject: { kind: catalog, ref: "lifecycle-foundation" }
    change: "WS-B4: single-source the workflow count to the 7 dadaia-workflows; add/extend a dadaia-workflows feature atom; reframe the legacy '2 workflows' framing"
  - subject: { kind: catalog, ref: "sdd-gate-v3" }
    change: "WS-A3 target: receive the §8 gate/lease/chokepoint mechanism extracted from the constitution (lease schema, 4-step mode chain, pre_gate order, chokepoint probe chains, enforcement matrices); drop residual OpenCode row. (context-management also receives the lease-mode mechanism — tracked in body, not double-bound here)"
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/fake_runtime.py#FakeAgentRuntime" }
    change: "WS-D: fix open bug lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence — the FAKE closure runtime must emit valid artifact evidence or reject/warn `--harness fake` up front instead of accepting then blocking"
  - subject: { kind: code, ref: "dadaia_workspace/features/specs/doctor.py#SpecsDoctorIssue" }
    change: "WS-E (recurrence prevention): add a doctor invariant asserting the constitution hard-codes no AgentRuntimeKind members / harness enumeration (must cite memory), so this class of constitution↔code drift fails CI instead of silently rotting"
---

> **Note on subjects.** The centerpiece — the `specs/constitution.md` lean rewrite
> (WS-A1..A6) — is described in the body below, not as a bound `intents[]` subject:
> the canonical-subject registry derives `doc` anchors only from `specs/memory/**`
> headings + `SPEC-DOC-*` ids, so `constitution.md` is not auto-bindable (it would
> need an operator alias-map entry). The bound intents above cover the memory + code
> surfaces; WS-A is owned in full by the body. (This binding gap is itself a minor
> finding — consider an alias for `constitution.md` or a governing `SPEC-DOC-*`.)

# Specs Truth Realignment — constitution lean + runtime single-source + memory de-stale

**Status:** CANDIDATE — not picked into any release. PM-curated. Pick AFTER v0.1.41
ships (a live v0.1.41 CLOSURE MUTATING lease currently holds the context; this release
is MUTATING and must run as the next release under the PM lease). A `dadaia-grill-me`
session on the picked set is **mandatory before SPEC** (constitution §10).

## Why (root finding)

A full 5-auditor audit (2026-06-30, `specs/audits/20260630T021228Z-251bb5f3/`,
overall drift 7.2/10 — healthy) found the **supreme governing doc is the most stale
artifact in the tree**: `constitution.md` still encodes the removed OpenCode harness and
a 5-member runtime enum as live law, contradicting the code (`AgentRuntimeKind` = 4
members) and its own subordinate memory atoms (which already match the code). The drift
is **orphaned** — no existing backlog item owns it (`sdd-governance-v2-agents-lifecycle`
is a different epic). Two structural problems compound it: the constitution is ~65%
mechanism/vision/changelog (inverted vs the SDD best-practice "small set of immutable,
verifiable principles" — GitHub Spec-Kit's own constitution is ~214 lines of
principle+rationale with version history in a separate header), and the harness/runtime
roster is **double-sourced** across constitution §0/§4/§5/§8 and ~10 memory atoms
(§12.3 self-violation) — which is exactly why the copies diverged.

**Architecture-fidelity gate (software-architect): REJECTED** until WS-A1+WS-A2 land.
The fix is not just string-deletion; without single-sourcing the enum (WS-A2) the defect
recurs.

## Work-streams, owners, acceptance

### WS-A — Constitution lean rewrite — `product-engineer` (MUTATING, DEFINITION; operator confirmation required for constitution change)
- **A1 (CRITICAL)** Purge OpenCode/5-kind/`.opencode`/"ten". **Accept:** `grep -ci opencode specs/constitution.md` == 0; harness/runtime statements set-equal to `core/models/lifecycle.py::AgentRuntimeKind` and `public` install targets; root layout lists nine entries; no OpenCode enforcement-matrix row.
- **A2 (root-cause)** Single-source the roster. **Accept:** constitution enumerates zero concrete `AgentRuntimeKind` members; states the invariant and cites `[[architecture]]`; the concrete set lives in exactly one memory atom.
- **A3** Collapse §8 → invariant. **Accept:** §8 successor ≤ ~20 lines, holds only binding invariants (one MUTATING lease/context; live-foreign never stolen; ADDITIVE never leased; READ non-acquiring; fail-open except PROTECTED); no schema/TTL/probe-steps; mechanism present in exactly one memory atom; `specs doctor` green.
- **A4** Move §0 vision→`[[product-vision]]`, layers/layout→`[[architecture]]`; keep ~18-line Definitions; "ten"→"nine". **Accept:** §0 successor ≤ ~20 lines; no normative loss (every retained "must" still present).
- **A5** Strip inline changelog; add Governance + version header (constitution semver + amendment log). **Accept:** no dated "Amendment/codified in vN/supersedes/maps to vN" strings in articles; a Governance section defines amendment + versioning.
- **A6** De-pin constants. **Accept:** no tunable literal in the law; pointer to `core/kernel_tunables.py`. **Target:** constitution ≈ 200 lines, principle+rationale, each principle verifiable.

### WS-B — Memory realignment — `product-engineer` (MEMORY, DEFINITION/CLOSURE)
- **B1 (HIGH)** De-stale `product-vision.md` + `harness-primitives.md` (3 harnesses, 4 kinds, PI third). **Accept:** no "four harness"/"fourth harness"/`OPENCODE_RUN`/`.opencode` strings; counts match code.
- **B2** De-stale the 8 projection/runtime atoms naming OpenCode live (`agent-orchestration`, `workspace-init`, `workspace-portability`, `public-asset-distribution`, `multi-platform-parity`, + residue in `sdd-gate-v3`, `cross-platform-portability`, `agent-comms`, `agent-sdd-alignment`). **Accept:** OpenCode mentioned only as removed/historical; doctor green.
- **B3** Author §13-compliant `product/index.md` (vision/users/ordered-catalog/capability-map/limits). **Accept:** index has all five; is not merely the generated table.
- **B4** Single-source workflow count → 7 dadaia-workflows; add/extend a dadaia-workflows atom (closes F-COV-2). **Accept:** "2 workflows" framing removed or marked legacy-reference; the 7 workflows documented in one atom.
- **B5** Decide PI Layer-1 harness atom (F-COV-1 asymmetry vs `ai-harness-claude-code`/`ai-harness-codex`). **Accept:** explicit decision recorded (author atom, or document why not).
- **B6** Fix `tech-stack.md` PI-auth contradiction. **Accept:** one auth statement (Codex subscription / `~/.pi/agent/auth.json`); no `ANTHROPIC_API_KEY` claim for PI.
- **B7 (HIGH)** De-narrate + slim `architecture.md`: extract lease/concurrency→`[[context-management]]`/`[[sdd-gate-v3]]`, workflow engine/control-plane/handoff-data-plane→`[[lifecycle-foundation]]`, backlog-consistency→`[[sdd-bug-backlog-governance]]` via citation; fix L501/L344/L45; remove changelog prose; re-stamp `token_estimate`. **Accept:** no `(v0.1.NN)`/"replaced"/"collapse removed" clauses; core atom ≤ ~6–8k tokens; `specs doctor` LINT-1/CAT-1 green.
- **B8** Regenerate `catalog.json`/`index.md`. **Accept:** no OpenCode/"2-workflow" tldr; 1:1 atom↔entry; (optional) daily-relevance ranking.

### WS-C — Quality-assurance memory — `product-engineer`
- Re-validate budgets vs **1424** tests (contract→100–170, integration→450–560, total→~1425); document auto-marker-by-directory, the **separate Playwright/Node `npm run test:e2e` panel-e2e job** + cross-platform matrix, and conftest safety guards (`_no_real_venv`, repo-root-write guard, snapshot guard, tmp retention); move the v0.1.34 "collapse" narrative → `releases/v0.1.34/CLOSURE.md`; reconcile coverage prose with the hard 80% CI gate; bump `last_updated`/`release_origin`. **Accept:** every budget bracket contains the live count; the four named facts documented; no collapse-narrative in the atom; QA APPROVE.

### WS-D — Open bug — `software-engineer` (IMPLEMENTATION)
- Fix `lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence` (MEDIUM): FAKE closure path emits valid evidence or rejects/warns `--harness fake` up front. **Accept:** a `lifecycle close --harness fake` smoke advances (or fails fast with an actionable message); regression test; bug → Closed with resolution block.

### WS-E — Recurrence prevention — `software-engineer` (IMPLEMENTATION)
- Add a doctor invariant: the constitution must hard-code no `AgentRuntimeKind` member / harness enumeration (must cite memory). **Accept:** a new SPEC-DOC / public-doctor check fails when constitution enumerates runtime kinds; green on the rewritten constitution; covered by a test.

## Sequencing
1. **WS-A1 + WS-A2 first** (corrected, single-sourced law) → 2. **WS-B/WS-C** reconcile memory against the corrected law → 3. **WS-B8** regenerate catalog last → 4. **WS-D/WS-E** in parallel (code, independent) → 5. **WS-E** guards the result.
Low-risk text fixes (A1,A4-fix,B-stale-strings, architecture L501/L344/L45) batch first; the architecture.md split (B7) and the §8 collapse (A3) are the larger refactors; grill should resolve open questions before SPEC.

## Hygiene NOT in this release (fold into v0.1.41 CLOSURE)
Archive closed releases v0.1.35–v0.1.40 → `_archive/releases/`; flip terminal
SPEC-DOC-031 status tokens; commit dirty `public/` + `dadaia public install --target all`
to clear the Codex-hook projection drift. These are v0.1.41-CLOSURE hygiene, not this
release's scope.

## Grill seeds (resolve before SPEC)
- Constitution target size — hard ~200-line cap, or principle-count cap?
- Single-source home for the runtime roster — `architecture.md` vs `multi-platform-parity.md` (pick one).
- `architecture.md` — split into child atoms, or de-narrate-in-place only?
- PI Layer-1 atom — author now (B5) or defer?
- Does WS-E (doctor invariant) belong here or in `sdd-governance-v2`'s audit-disposition pillar?
