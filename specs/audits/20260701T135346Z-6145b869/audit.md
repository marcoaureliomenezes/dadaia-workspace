# SPECS Compliance Audit — dadaia-workspace

> Auditor: project-auditor · Date: 2026-07-01 · Session: 6145b869
> Trigger: operator escalation ("specs totally out of compliance"; bugs created as
> Markdown when JSONL was mandated). Read-only audit. Active release at audit time: v0.1.45.

## Scorecard (1-10)

| Dimension | Score | Verdict |
|---|:---:|---|
| Bug-format (JSONL mandate vs `.md` reality) | **2** | JSONL mandated v0.1.14→v0.1.15, never delivered. 99 `.md` (76 Closed, 22 Open, 1 off-canon Resolved), 0 JSONL. Guardrail rule still says Markdown. |
| architecture.md fidelity | **8** | Current through v0.1.43 incl. model governance + `LAYER2_EXTRA_MODEL_IDS`. Cosmetic + not-yet-due v0.1.44/45 only. |
| product/ memory fidelity | **3** | Widespread stale OpenCode-as-live across ~11 atoms, 5+ releases after v0.1.24 removal. |
| doctor-cleanliness | **7** | 0 errors / 10 warnings (mostly benign/grandfathered). |
| disposition-hygiene | **3** | 76 closed bugs unarchived; ~14 audits undisposed; EPIC mis-statused; redundant bug cluster. |
| **OVERALL** | **4** | Moderate-to-critical drift → dedicated remediation release (v0.1.46) warranted. |

## Findings

- **DRIFT-1 (CRITICAL) — Bug-format:** JSONL mandated (`specs/_archive/releases/v0.1.14/SPEC.md:308-310`) for v0.1.15, never shipped. `specs/bugs/*.md` = 99 files, `specs/bugs/_archive/` empty (migration never ran). The `bug-registration-guardrail` rule still prescribes Markdown, so agents correctly filed `.md` — the rule-rewrite half of the mandate was never done. Home: `specs/backlog/sdd-governance-v2-agents-lifecycle.md` (FEAT-GOV-V2-01) §2 — implementable as-is (format `specs/bugs/<YYYYMMDDTHH>Z.jsonl` append-only + rotation; event schema `reported|resolved|superseded|deferred|rejected|archived`; `dadaia bugs append|status|stats`; doctor invariant; one-time migration; guardrail rewrite).
- **DRIFT-2 (HIGH) — product/ OpenCode drift:** OpenCode presented as a live target across ~11 atoms (workspace-init.md:25, product-vision.md:45-46,87, public-asset-distribution.md:5,28,72, harness-primitives.md:9,34,37, cross-platform-portability.md:137, workspace-portability.md:24,49, agent-sdd-alignment.md:84, agent-comms.md:38,63, agent-orchestration.md:132) + generated index.md/catalog.json. OpenCode removed v0.1.24. Fix atoms then `dadaia memory catalog generate`.
- **DRIFT-3 (MEDIUM) — disposition-hygiene:** 76 closed bugs never archived (`specs/bugs/_archive/` empty); ~14 audits undisposed (`specs/audits/_archive/` empty); redundant HTML-report bug cluster (1 Closed + 2 Open on one defect).
- **DRIFT-4 (MEDIUM) — EPIC mis-statused (SPEC-DOC-031):** `sdd-governance-v2-agents-lifecycle.md` frontmatter `status: candidate` but body says PARTIALLY CONSUMED, referenced by shipped v0.1.14/15/30. Same class: `panel-ux-overhaul.md`, `features-import-infrastructure-direct-debt.md`.
- **DRIFT-5 (LOW) — real doctor debt:** SPEC-DOC-032 (`v0145-t4506` bug Resolved→Closed — now fixed), LINT-1 token drift (`lifecycle-foundation.md` token_estimate 4100 vs ≈5576), SPEC-DOC-030 (`specs/audits/2026-06-12T001813Z` missing session-id suffix), LINT-1 4 unknown headings. Benign/grandfathered (do NOT action): SPEC-DOC-027 ×2 legacy archive names, SPEC-DOC-029 stale tauan-games lease, TREE-5 template drift, SPEC-DOC-016 archives grandfathered v0.1.45.

## Pattern (what went wrong)
Agents obeyed a stale rule to the letter (fault = the un-shipped rule-rewrite half of the JSONL mandate; the mandate and enforced rule diverged 5+ releases). Memory swept narrowly (OpenCode removed but the product long-tail left claiming it live). No archive/disposition discipline because the law mandating it is unshipped. Backlog status left bare (prose "PARTIALLY CONSUMED" not in machine `status:`).

## Recommended remediation — v0.1.46 (routes to project-manager)
Confirm `sdd-governance-v2-agents-lifecycle` (FEAT-GOV-V2-01) as the backbone (§2/§3/§4 implementable as written):
1. JSONL bug telemetry (§2) — software-engineer: `dadaia bugs append|status|stats`, event schema under `.dadaia/agentic/schemas/`, doctor invariant, one-time `*.md → *.jsonl` migration + `git mv` to `specs/bugs/_archive/`.
2. Guardrail-rule rewrite (§2 "Law") — ai-engineer: rewrite `public/rules/bug-registration-guardrail.md` for JSONL events; **must ship in the same release** or the drift regrows.
3. OpenCode memory sweep (DRIFT-2) — product-engineer (DEFINITION/CLOSURE): purge stale atoms, `dadaia memory catalog generate`.
4. Disposition cleanup (DRIFT-3/4) — PE + PM: archive 76 closed bugs, disposition ~14 audits, normalize statuses, dedupe HTML-report cluster; ship the `_archive` FROZEN gate-class + audit-disposition law (§3/§4).
5. Minor doctor debt (DRIFT-5) — PE.

architecture.md needs no rewrite now (8/10); touch it when v0.1.44/45 close.
