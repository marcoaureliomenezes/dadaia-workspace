---
name: backlog-definition-workflow-dedup-conflict-control
id: FEAT-BACKLOG-DEFINITION-WORKFLOW-01
reported: 2026-06-26
owner: project-manager (curates) -> product-engineer (release definition after MANDATORY grill)
priority: CRITICAL
status: delivered
delivered_in: v0.1.26
builds_on: lifecycle-prompt-fragments-ai-surface-dehydration (this SPLITS OUT + supersedes that epic's deferred `backlog_definition` workflow-body bullet — see §10)
delivered_note: |
  R1 (v0.1.25) shipped the engine slice; R2 (v0.1.26) shipped the §4 workflow body, the live
  classifier feed, the real fragments, the backlog_index selector, and the removal-on-release
  mechanism — exhausting the §11 R1+R2 scope. The one operationally-incomplete piece (the
  removal-on-release PRODUCER wiring at release-definition) was split out into the HIGH residual
  item `wire-consumed-ledger-producer-at-release-definition` rather than silently dropped.
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/workflows/backlog_definition.py#BacklogDefinitionWorkflow" }
    change: "R2: replace the fail-loud _deferred stub with the real §4 backlog_definition workflow body (intake_grill -> subject_bind -> existing_backlog_review -> reconcile_decision -> conflict_resolution_grill -> backlog_author -> backlog_review_gate)"
  - subject: { kind: cli, ref: "lifecycle backlog define" }
    change: "R2: wire the backlog_definition workflow behind `dadaia lifecycle backlog define` with scoped fragments + Python gates"
  - subject: { kind: code, ref: "dadaia_workspace/features/backlog/classifier.py#classify" }
    change: "R2: feed the deterministic set-intersection classifier into the existing_backlog_review workflow step (Python disposes; model only adjudicates same-anchor merges, fail-closed)"
---

# EPIC — `backlog_definition` dadaia-workflow: dedup + conflict + staleness control

## 0. One-line law
**The backlog is a deduplicated, conflict-free, non-stale SET.** No two items may
duplicate or *diverge* (touch the same subject with different intended targets), and no
item may survive after its content is shipped in a release. This is enforced by a
**Python-owned canonical-subject registry + deterministic classifier + doctor chokepoint** —
NOT by model judgment, and NOT by human/agent vigilance (both have already failed and
corrupted a project).

## 1. Problem (root cause, evidenced)
Backlog items are filed across time by a forgetful operator + agents; nothing compares a new
demand against the existing backlog. Three compounding failure modes:
1. **Duplication** — two files request the same change.
2. **Divergent conflict (the dangerous one)** — `transform A→B, C→D` filed day 1, then
   (forgotten) `transform A→B, C→E` filed day 2. Both touch **subject C** with **incompatible
   targets** (`D` vs `E`). Undetected, one becomes a release and silently contradicts the
   other → corrupted project. The defect was the **inconsistent backlog**, not the code.
3. **Staleness** — an item shipped via a release is never removed, accumulating as dead crap
   (cf. the 2026-06-26 cleanup that deleted 22 such files).

**Architect root-cause finding (binding):** the true root cause is **uncanonicalized
subjects**. Any design where `subject` is free text the model emits is theater — it fails on
exactly the naming drift ("the panel API" vs `/api/workflows` vs `WorkflowDetailDTO`) that
caused the incident. The fix below makes `subject` a Python-verified typed reference.

## 2. Backlog item shape + the CANONICAL-SUBJECT REGISTRY (the linchpin)
Every backlog item declares machine-readable **(subject → change)** intents in frontmatter:
```yaml
intents:
  - subject: { kind: code,    ref: "dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind" }
    change: "remove OPENCODE_RUN"
  - subject: { kind: api,     ref: "panel:/api/dadaia-workflows" }
    change: "add per-step model_options"
  - subject: { kind: doc,     ref: "memory/architecture.md#layer-2" }
    change: "..."
  - subject: { kind: invariant, ref: "INV-no-claude-at-L2" }
    change: "..."
```
**`subject` is a TYPED reference, not free text**, resolved against a Python-owned
**canonical-subject registry** (`features/backlog/subject_registry.py`): the union of
- `catalog.json` memory slugs + product-atom ids,
- code anchors (module path `#symbol`, validated to exist via AST/grep),
- panel/CLI/API surface ids,
- spec-doc ids and named invariants.

The registry is **recomputed from live truth on every doctor/workflow run** (AST/grep of code
symbols, `catalog.json`, panel/CLI/API ids) — it is **derived, never a stored file that can
itself go stale** (the meta-version of the bug we are fixing); a small operator-maintained
**alias map** (`.dadaia/states/backlog_subject_aliases.txt`) collapses known synonyms to one
canonical anchor (OQ-5, operator-resolved 2026-06-26).

The model **proposes** a subject string in step 1; Python **normalizes + binds** it to a
registry anchor and **rejects (HALT, not silent NEW) any intent whose subject resolves to no
known anchor or to an ambiguous set**. Naming drift is collapsed at bind time (aliases map to
one canonical anchor). **No unverified subject is ever written to a backlog item.** Without
this registry the entire mechanism is theater (architect finding #1).

Classes are then defined on the canonical anchors: items **duplicate** when anchor-set+change
match; **conflict** when they share an anchor with incompatible change; **overlap** when
anchor-sets intersect with compatible/additive changes.

## 3. Conflict classifier — Python disposes, model only adjudicates (fail-closed)
Deterministic boundary owned by Python (`features/backlog/classifier.py`); the model never
decides UNRELATED-vs-not:
1. **Python** computes canonical-anchor **set intersection** between the new intents and every
   existing item. Empty intersection → `UNRELATED` (final, no model call).
2. For each **shared-anchor** pair, Python checks change-equality → `DUPLICATE` if identical.
3. Only a shared-anchor pair with **differing** change is sent to a **model** step to adjudicate
   *compatible-merge vs incompatible*. **Fail-closed:** the result is `DIVERGENT_CONFLICT`
   UNLESS the model returns an explicit, structured compatible-merge (then `OVERLAP`/`SUPERSEDES`).
   The model can only *downgrade* a conflict with evidence; it can never *miss* one, because
   same-anchor+differing-change defaults to conflict.

| class | basis | required workflow action |
|---|---|---|
| `UNRELATED` | empty anchor intersection (Python) | none |
| `DUPLICATE` | same anchors + same change (Python) | UPDATE existing; merge new detail; never new file |
| `OVERLAP` | anchors intersect, model-proven compatible | UPDATE existing (fold scope) or explicit split w/ cross-refs |
| `SUPERSEDES` | new replaces old (model-proven) | rewrite existing to new intent (or remove if no surviving scope) |
| `DIVERGENT_CONFLICT` | shared anchor + differing change, not proven-compatible (DEFAULT) | HALT → operator grill → reconcile into ONE item |
| `DEPENDS_ON` | new needs old's outcome | record dependency edge in both |

**Python gate law:** emit a NEW file ONLY when every existing item is `UNRELATED`. Any other
class forces UPDATE/RECONCILE. `DIVERGENT_CONFLICT` blocks until an operator reconciliation is
captured.

## 4. The `backlog_definition` workflow — sequenced, scoped prompts (R2)
`dadaia lifecycle backlog define`; Python body, each step = role + scoped fragment + selected
context + output schema + Python gate. No generic "run the step" prompt.

| # | step | role / runtime | scoped fragment + injected context | output | gate |
|---|---|---|---|---|---|
| 1 | `intake_grill` | project-manager (MANDATORY grill) | `shared/grill-questionnaire` + demand + product-catalog summary + full backlog INDEX (anchors + status) | `backlog-demand-v1` (proposed intents) | grill reaches shared understanding |
| 1b| `subject_bind` | Python | the canonical-subject registry (§2) | `bound-intents-v1` | HALT on any unresolved/ambiguous subject |
| 2 | `existing_backlog_review` | Python (+ model only for shared-anchor change adjudication, §3) | bound intents + every existing item's bound intents | `overlap-report-v1` (Python classes + model merge-verdicts) | report total + every existing item classified |
| 3 | `reconcile_decision` | Python (+ product-engineer if ambiguous) | overlap report | `reconcile-plan-v1` (NEW \| UPDATE(t) \| MERGE(t..) \| SUPERSEDE(t)) | **blocks NEW if any non-UNRELATED class** |
| 4 | `conflict_resolution_grill` | project-manager (MANDATORY iff any DIVERGENT_CONFLICT) | `shared/grill-questionnaire` + each conflict rendered "you previously asked X@anchor; now Y@anchor" | `conflict-resolution-v1` | no unresolved divergence may pass |
| 5 | `backlog_author` | product-engineer | `backlog_definition/backlog-authoring` + plan + resolution | `backlog-item-v1` (bound intents, status, scope) | NEW file XOR edit EXISTING — never both, never a twin |
| 6 | `backlog_review_gate` | Python | the result + rest of backlog | `backlog-verdict-v1` | re-run classifier on RESULT: zero DUPLICATE/DIVERGENT_CONFLICT; valid metadata |

## 5. Why the `C→D` / `C→E` twin is now structurally impossible
Day-2 `C→E`: step 1b binds `C` to its canonical anchor; step 2 Python set-intersection finds
the day-1 `C→D` item shares anchor `C`; changes differ → model adjudication → no compatible
merge → `DIVERGENT_CONFLICT` (fail-closed); step 3 refuses NEW; step 4 surfaces "C→D vs C→E"
to the operator; step 5 writes ONE reconciled item. The twin never exists — and the decision
does not depend on the model noticing, because Python owns the anchor intersection.

## 6. Removal-on-release — safe, residual-aware, with a durable copy (R2)
**Law:** when an item's content is consumed by a release it leaves the **live working SET**
of `specs/backlog/`. Safeguards (Python-gated, not prose):
- The **release-definition** workflow writes a `consumed_backlog` ledger keyed by the **verified
  subject-anchor set actually shipped** in the release SPEC (not slug string alone).
- **Rewrite-down-to-residual is the DEFAULT.** Only intents whose anchors are in the shipped set
  are stripped; an item with surviving intents is rewritten to its residual (the 2026-06-26
  hand pattern), never deleted whole.
- **Full removal** happens only when zero residual intents remain. Before `rm`, the closure
  workflow **copies the file to `specs/_archive/<release>/consumed-backlog/<slug>.md`** — the
  live SET drops it (so it can never re-enter a future release), but a durable trace survives
  (backlog is gitignored → never delete the only copy of a CRITICAL safety record).

## 7. Doctor chokepoint — the ENFORCED backstop (honest about oriented-vs-enforced)
**Truthful posture (architect finding #5):** `specs/backlog/` is gitignored + ADDITIVE — the
PreToolUse/lease gate does NOT classify a hand-written backlog file as MUTATING, so the
**workflow is the ORIENTED happy-path, not an enforced one.** The real enforcement is a
deterministic doctor wired into the **git chokepoint**:
- `dadaia backlog doctor` (new, `features/backlog/doctor.py`) wired into **pre-commit** (and CI):
  - **BL-SCHEMA** — every item has bound `intents[]` (subjects resolve in the registry) + valid status.
  - **BL-DUP** — two items share anchor-set + change → ERROR.
  - **BL-CONFLICT** — two items share an anchor with incompatible change → ERROR (the divergent twin, caught even if hand-written).
  - **BL-STALE** — keyed on the `consumed_backlog` **ledger** (mechanical, not NLP): a slug listed in any archived release's `consumed_backlog` that still exists in `specs/backlog/` → ERROR. (Drops the infeasible "match intents against archived prose" ambition.)
- A hand-written divergent twin is therefore **rejected at commit**, closing the bypass.

## 8. Touched modules
- `features/backlog/subject_registry.py` (new) — canonical anchor registry + bind/normalize/verify.
- `features/backlog/classifier.py` (new) — deterministic set-intersection classifier (§3).
- `features/backlog/doctor.py` (new) — BL-SCHEMA/DUP/CONFLICT/STALE; wired into the pre-commit chokepoint + CI.
- `dadaia_workspace/public/lifecycle_fragments/backlog_definition/` — real fragments (`conflict-scan`, `backlog-authoring`), replacing the v0.1.24 `_README` stub.
- `features/lifecycle/workflows/backlog_definition.py` (new) — the §4 body, replacing the `_deferred.py` stub.
- `features/lifecycle/context_selector.py` — `backlog_index` selector (bound intents + status).
- release-definition + closure workflows — write the `consumed_backlog` ledger + the §6 removal hook.
- migration — backfill bound `intents[]` onto the 14 surviving backlog items.

## 9. Acceptance criteria
1. A demand whose subject resolves to no registry anchor HALTS (no silent NEW) — tested.
2. A duplicate demand UPDATEs the existing item (no new file) — tested.
3. The `C→D`-then-`C→E` divergence is classified `DIVERGENT_CONFLICT` by **Python set-intersection
   alone** (model offline), HALTs at step 4, resolves into ONE item — tested with a FAKE fixture.
4. A consumed item is rewritten-to-residual or (zero residual) removed-from-SET-with-archive-copy
   at closure, keyed on the verified shipped subject set — tested.
5. BL-SCHEMA/DUP/CONFLICT/STALE fail on planted violations + pass clean, and a hand-written
   divergent twin is rejected at **pre-commit** — tested.
6. The 14 surviving items carry valid bound `intents[]` after backfill; `backlog doctor` exit 0.

## 10. Reconciliation with existing backlog (practicing the law)
SPLITS OUT + supersedes the deferred `backlog_definition` bullet in
`lifecycle-prompt-fragments-ai-surface-dehydration.md` (now updated to delegate here + retain
only `audit`/`research`/`bug_report` + deep dehydration + ctx-inject). No divergent duplicate
created — the §3 OVERLAP→UPDATE path applied to our own authoring.

## 11. Release slicing (architect-recommended; ship BEFORE workflow-model-governance)
- **R1 (foundational — must ship first):** the item shape (`intents[]` schema) + the
  canonical-subject **registry** + the deterministic **classifier** + the **BL-* doctor wired
  into pre-commit/CI** + **backfill** of the 14 survivors. This makes the backlog mechanically
  consistent even before the workflow exists. Shipping R2 first would ship theater.
- **R2:** the `backlog_definition` **workflow body** (§4) + the **removal-on-release** closure
  hook (§6) + the real fragments.
- Both precede `workflow-model-governance-panel-control-plane` (operator-confirmed 2026-06-26).

## 12. Open decisions for the mandatory grill
| ID | question | leaning (post architect review) |
|---|---|---|
| OQ-1 | subject canonicalization scheme | RESOLVED → Python-owned typed registry; model proposes, Python binds, reject-on-unresolved (§2). |
| OQ-4 | conflict classification: prompt vs deterministic | RESOLVED → both, Python owns UNRELATED/CONFLICT boundary, model only adjudicates same-anchor merges, fail-closed (§3). |
| OQ-2 | removal-on-release safety | RESOLVED → remove from live SET + keep one copy under `specs/_archive/<release>/consumed-backlog/`; residual-aware (operator 2026-06-26). |
| OQ-3 | sequence vs workflow-model-governance | RESOLVED → backlog-definition first (operator 2026-06-26); R1 then R2. |
| OQ-5 | registry source-of-truth + alias policy | RESOLVED → auto-derived (recomputed from live truth each run) + operator-maintained alias map (operator 2026-06-26). All grill OQs now resolved → ready for SPEC. |
