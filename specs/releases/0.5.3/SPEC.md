# SPEC — Release: 0.5.3

**Status:** Aprovado
**Release ID:** 0.5.3
**Owner:** product-engineer
**Opened:** 2026-08-31

> Approval provenance: operator order 2026-08-31 — "faça a release de remediação do audit
> 20260830 completa". §6.8 remediation lane for `20260830-design-bug-surface-audit`
> (17 open findings); grill satisfied by the audit's own evidence set + the operator's
> direct order (recorded deviation). Rides `feature/0.5.2` (0.5.2 archived pre-ship;
> one live branch, precedent 0.4.5/0.5.0/0.5.1).

**Consumes:** dissolve-container-feature-composition, session-binding-deep-module, specs-single-decider-folds, projection-finish-k3, specs-tree-model-rule-registry, design-audit-residue-hygiene, dadaia-codebase-design, dd-architecture-survey, dd-code-review, dadaia-glossary, dd-tasks-as-tracer-bullets, cli-help-architecture-and-session-injection, nine-skill-study-execution

---

## 1. Problem and context

- `20260830-design-bug-surface-audit`: 17 open findings — the residue where each prior
  consolidation (K1–K11, ADR 0001–0003, v0.3.0 demolition) stopped one file short.
- Measured thesis: additive fixes bred the 84-edge caused_by loop; deletion-shaped fixes
  ended families. Every fix below is a finishing move — net-deletion, no new machinery.
- Open bug `releases-agents-projection-stale-vs-scaffold-source` (picked, bug-always-solved).

## 2. Objective

Disposition ALL 17 findings fixed in-release — operator order 2026-08-31: no audit
finding and no audit backlog entry stays out. F010+F012 (SpecsTree parsed model + rule
registry) are T-053-16, sequenced after the single-decider folds per the audit's own
sequencing. The picked shipped-hashes bug is fixed (T-053-15). Definition follows
codebase-design/improve-codebase-architecture/domain-modeling: design-it-twice runs for
the two new deep interfaces (SessionBinding, SpecsTree); CONTEXT.md is updated as the
modules are named.

## 3. Scope (finding → task)

| Task | Findings | Work |
|---|---|---|
| T-053-01 | F003, F016(part) | hooks/container adopt Invocation fully: delete `sdd_gate._context_slug`; `ctx_inject`/`sdd_post_gate` read `inv.specs_dir`/`repo_slug` (no string-joins); collapse `resolve_context_specs_dir` re-derivations |
| T-053-02 | F007 | phase vocabulary one home in core; `release_state` validates the token |
| T-053-03 | F004 | release-identity fold into `core.specs_version` (shape + mint predicate + derived remedy text); canon composes it; segment-shape triplicate absorbed |
| T-053-04 | F005 | collapse TREE-6/SPEC-DOC-004 and 016/027 rule pairs to one implementation each |
| T-053-05 | F011 | required-memory-file list ×3 → canon.CANON; one forbidden-heading vocabulary; one wikilink regex |
| T-053-06 | F008 | one read-side registry accessor for `spec_contexts.json`; `ctx_inject`/`invocation` consume it |
| T-053-07 | F009 | `ctx_inject` decision table → pure `decide_injection()` in `features/spec_context`; hook = transport |
| T-053-08 | F002, F016(part) | `SessionBinding` deep module: record schema, mode tokens (delete dead `BOUND_READ`), minting, TTL/liveness; CLI verbs become adapters; 3 `gc_check` copies collapse |
| T-053-09 | F013 | `spec_context/service.py`: embedded secret-scan → privacy module; inline law-template writes → one projection home |
| T-053-10 | F006 | projection: delete dcx6 missing/drift half (keep LEAK); guardrail pair → discovery-produced ProjectionRules (provenance render); delete `[ok]/[skip]` string ledger parser |
| T-053-11 | F014 | relocate codex_doctor's harness-independent checks; delete `_compare_content` + the 25-name re-export block |
| T-053-12 | F015, F016(part) | ci.py first-parent → git_objects reader; python_env honest repack-install message; handoff_index docstring corrected |
| T-053-13 | F017 | bug-registration seam: component gains path-shaped validation/normalization (advisory, ADDITIVE stays writable) |
| T-053-14 | F001 | container dissolution: delete dead ancestry chain; `build_panel_views` → features/panel composition; collapse single-consumer pass-throughs citing the deleted contract; contract test "every container def has a non-container consumer" |
| T-053-15 | bug | shipped-hashes coverage for scoped scaffold AGENTS.md files + upgrade/doctor repair; refresh the two stale projections through the new mechanism (resolves releases-agents-projection-stale-vs-scaffold-source) |
| T-053-16 | F010, F012 | SpecsTree parsed model (walk once, parse once; validators become pure rules) + declarative rule registry (code → check → fix; `fix()` dispatch and `--fix` help derived) — interface chosen by design-it-twice |
| T-053-17 | — | disposition sweep (17 fixed), audit archived (histo + dir removal per source law) |
| T-053-18 | — | memory update (Part 2 reflects new homes), CONTEXT.md terms, closure log, CHANGELOG [0.5.3], pyproject 0.5.3, full preflight |

## 4. Out of scope

- The 9 pre-existing `candidate` backlog entries (skills/design lane, different provenance) — not this audit's material; stated interpretation, operator may override.
- rc PR, trio verdicts, ship, publication — operator-gated.

## 5. Dependencies and risks

- Order matters: T-053-01..06 (folds) before T-053-07..09 (extractions) before T-053-14 (container).
- Every task: TDD, targeted tests per task, full preflight at closure; each diff justified
  net-negative/neutral or explicitly argued against the permanent-architecture-review rule.
- Refactors touch high-fan-in core files — full suite is the integration gate.

---

## Extension — AI-surface backlog consumption (operator order 2026-08-31)

Conclusion criterion: **0 bugs, 0 active backlog, 0 audit findings.** The 9 remaining
candidates were reviewed against current reality; 7 picked, 2 rejected (grill with the
operator, 4 rulings recorded in RELEASE.json).

| Task | Entry | Work (obsolescence review folded in) |
|---|---|---|
| T-053-19 | dadaia-codebase-design (+ nine-skill Fuse×1) | New public reference skill: the design vocabulary (seam, deep module, deletion test, adapter, locality, replace-don't-layer) + DEEPENING + DESIGN-IT-TWICE companions; retire `architect-core-workflow` (fuse); repoint software-architect persona; behavior-map row |
| T-053-20 | dd-architecture-survey | New user-invoked skill (disable-model-invocation): bugs stats × git churn → architecture cards + ONE top candidate → grill; ADDITIVE-only; behavior-map row |
| T-053-21 | dd-code-review | New skill, three axes (Standards+12-Fowler baseline, Spec, Bug-surface); code-reviewer persona invokes it and thins; behavior-map row |
| T-053-22 | dadaia-glossary | Small skill: sharpen-inline over the repo CONTEXT.md; seed the five homonyms (scaffold, sentinel, quarantine, context, workflow) into CONTEXT.md. ADR-format half SUPERSEDED by the specs/ADRs JSONL canon (recorded in histo) |
| T-053-23 | dd-tasks-as-tracer-bullets | As a SECTION of dd-release-definition (grill lean honored): every task carries `blocked by:` + `delivers:`; demolitions follow expand–contract |
| T-053-24 | cli-help-architecture-and-session-injection (A/B/C) | (A) docker-style help: rich_markup_mode, no_args_is_help, Common/Management panels at root, epilogs on high-traffic leaves, help-quality contract test; (B) derived digest verb (`dadaia help tree --digest`, ≤4k tokens, version-stamped under .dadaia/agentic/, regenerated at install/reconcile — never at hook fire); (C) ctx_inject attaches the digest bind-independent; Claude gains SessionStart `startup|resume` matchers. Item (D) decommission: ALREADY DELIVERED by evolution (`dadaia-cli` → `dd-cli-library`, cache-not-transcription); residual sweep rides T-053-25's merges |
| T-053-26 | (closure) | Extension closure: disposition rewrite of the 7 histo records to terminal, memory/CHANGELOG addenda, re-close |

T-053-25 | nine-skill-study-execution | Execute the ratified dispositions (handoff 2026-08-24T015304Z): Update×5 (dadaia-task-manager, dadaia-handoff-emitter, dadaia-step0-memory-bootstrap, dadaia-test-stewardship, dadaia-workspace-spec-navigator — staleness/sediment fixes), Merge dadaia-workspace-spec-reviewer→dd-audit-project, Merge dadaia-workspace-manager→CLI-help surface, Merge dev-server-registry→CLI-help surface, Fuse architect-core-workflow→dadaia-codebase-design (rides T-053-19); behavior-map + persona allowlists updated.

Rejected with recorded reasons (histo): **dadaia-router** (superseded — DADAIA.md-in-statements + behavior-map already answer "where am I, which skill next"), **dadaia-wizard** (speculative — no concrete human-only runbook in hand; re-enter on value).
