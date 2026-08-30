# AUDIT — 20260830-design-bug-surface-audit

**Auditor:** `claude-code` (operator-dispatched, 2026-08-30) · **Method:** `improve-codebase-architecture` + `domain-modeling` + `codebase-design` (deep-module vocabulary), 5 parallel cluster deep-dives, every finding evidence-verified at HEAD.
**Window:** since the `20260827-canon-v6-first-audit` head → HEAD `17390c19` (feature/0.5.2; main `2f6b95c4` = shipped 0.5.0). No `audited` milestone exists anywhere (0 in `releases_histo.jsonl`), so the bug-history pillar reads the whole 539-record ledger.
**Question asked by the operator:** why did fixing bugs breed bugs — find the implementation/design causes.

---

## 1. The bug loop, measured

- Ledger: 539 records; 519 resolved, 13 superseded, 4 rejected, 3 deferred, 0 open.
- **84 fix-induced edges** (`caused_by` naming a prior bug — ~16% of the ledger). Longest chain depth 5 (`scaffold-artifacts-fail-own-workflow-gates` → … → `r5c-backlog-gate-accepts-preexisting-candidate-without-intents`); three depth-4; seven depth-3.
- Velocity: 2026-06 = 89, **2026-07 = 311 (peak)**, 2026-08 = 139 and falling.
- File recurrence (normalized): `container.py` 12, `lifecycle/release_definition.py` 10, `lifecycle/pipeline.py` 10, `lifecycle/agent_runner.py` 8, `cli/lifecycle.py` 8, `cli/context.py` 6.
- Cluster sizes: lifecycle 184 records (34% of ledger), specs doctors 26, gate/hooks 19, spec_context 18, container 17, projection 15, cli context 12, python_env 9.
- Feature→feature import matrix at HEAD: only 4 edges — the spaghetti is **not** at the import layer anymore.

## 2. The verdict — three eras, one law

**Era 1 (accretion — the loop the operator named).** Fixes added mechanism. The demolished `pipeline.py` constructor is the diary: **24 keyword params, five injected gate callables each annotated with the bug that added it**; each close-state bug got a compensating filesystem pseudo-transaction (`_snapshot_close_zone`/`_restore_close_zone`), and the compensation machinery bred its own bugs (`rerun-of-run-id-collides-with-immutable-payload-zone`). Task-marker grammar was decided in 9 modules; two of its parsers broke each other (`write-scope-parser-*` pair). 28 `caused_by` chains in that cluster alone, including one mutual cycle.

**Era 2 (deletion — what worked).** Every fix that ended a bug family was deletion-shaped: the v0.3.0 workflow-engine demolition (`b94aede3`, −14,591 LOC — **zero bugs in that surface since 2026-08-11**), K1 Invocation (context-resolution family stopped), K2 presence GC, K3 ProjectionRule fold, K4 canon fold, K7 chokepoints split, ADR 0001 protocol purge, the bugs transition seam (`models/bugs.py` — no bugs-component record since). The deletion test, applied literally, is the only fix shape with zero recurrence.

**Era 3 (residue — where the next bugs are).** Each consolidation **stopped one file short of its own rule**. The resolve is one but hooks still re-derive paths; the rule table decides projections but dcx6 re-decides one file; canon is one table but re-forks `_SEMVER`; the store is the only parser but the registry has three. The 17 findings below are that residue — every one is a *finishing* move, net-deletion, no new machinery.

## 3. Cluster verdicts (did prior fixes reduce or grow the surface?)

| Cluster | Verdict | Evidence |
|---|---|---|
| lifecycle (demolished) | Era-1 fixes GREW it; demolition REDUCED structurally | 24-param constructor; 28 chains; 0 bugs since deletion |
| gate/spec_context | REDUCED (K1/K2/K7, `_is_law_path` floor) — consolidation stopped at resolver's edge | no recurrence in lease/bind-epoch/law-gate families; `context.py`+`ctx_inject` remain convention-held |
| specs doctors | REDUCED (K4/K5 folds) — two remainders grew by patching | segment-router bug fixed TWICE (mirrored blocks); release-id re-forked in canon.py |
| container/core | core REDUCED (`invocation`, `models/bugs` deep); container is the remaining amplifier | orphaned-factory class at 3rd occurrence; 34 commits/2 months |
| infrastructure/projection | REDUCED decisively (DoctorStatus, ProjectionRule, idempotent venv) | residue = dcx6, guardrail pair, string ledger parser |

## 4. Findings

17 findings in `FINDINGS.jsonl`, all `disposition: open`. Index (severity-ranked):

| id | sev | one line |
|---|---|---|
| F001 | HIGH | `container.py` is a change-amplifier; orphaned-factory class at 3rd occurrence (`build_process_ancestry` dead at HEAD); panel composition lives in the composition root |
| F002 | HIGH | session/bind state machine has no owning module — CLI authors the record schema; liveness predicate hand-copied ×3 |
| F003 | HIGH | ADR 0003 half-adopted — hooks re-derive `repos/<name>/specs` by string-join ×5; `_context_slug` dead; specs_dir recomputed past `inv.specs_dir` |
| F004 | HIGH | release-identity fact has 3 divergent deciders; SPEC-DOC-016/027 print a remedy `release new` refuses — the `release-new-rejects-semver` loop is live at HEAD |
| F005 | HIGH | TREE-6/SPEC-DOC-004 and 016/027 are one rule as two implementations — `segment-router-silent-skip` was fixed twice, once per site |
| F006 | HIGH | projection residue: dcx6 second decider; consumer-guardrail install/doctor parallel pair; `[ok] `/`[skip] ` string ledger parser drops `[updated]`/`[foreign]` lines |
| F007 | MED | phase vocabulary decided in 3 modules, no single home; `release_state` never validates the token |
| F008 | MED | `spec_contexts.json` has 3 read-parsers with divergent fallbacks (Store glossary: "the only parser") |
| F009 | MED | `ctx_inject.py` = 469-line policy in a transport; 4-branch state machine, 3 near-duplicate blocks; each past fix added a branch |
| F010 | MED | no parsed SpecsTree model — RELEASE.json read 5×/check, atoms parsed 4×, two full-tree sweeps; rules re-derive shared facts |
| F011 | MED | required-memory-files ×3 lists; forbidden-heading vocabulary ×2 already divergent; wikilink regex ×3 |
| F012 | MED | no doctor rule registry; `--fix` help is wrong at HEAD (claims TREE-3 fixable, omits 6 fixable codes) |
| F013 | MED | `spec_context/service.py` embeds a second secret-scan engine and inline projection writes — two homes per concern |
| F014 | LOW | modules split by line-count lint, not seam — `codex_doctor.py` carries ~340 harness-independent lines; `public_assets` re-exports ~25 underscore names; `_compare_content` dead |
| F015 | LOW | "first parent of a sha" implemented twice (`ci.py` raw subprocess vs `git_objects` reader) |
| F016 | LOW | three false claims at HEAD: python_env re-narrated failure; `handoff_index` docstring names a nonexistent facade file; `BOUND_READ` token read but never written |
| F017 | LOW | bug-ledger `component` is free text — same file spelled 3+ ways, 114/539 records unparseable — blunting the recurrence analysis this law depends on |

## 5. Relationship to the prior audit

`20260827-canon-v6-first-audit` holds **32 findings still `open`** (undispositioned — they outrank fresh backlog at pick time, §6.7). Its axis is governance conformance (commit shapes, milestones, ADR pairing); this audit's axis is implementation design. Overlap: its F006 (gitignore class never named) and the `spec-doc-030` family are instances of this audit's "same fact, two hand-kept deciders" class (F004/F011). One remediation lane can disposition both sets.

## 6. Remediation

One remediation release (per §6.8). Backlog intake (operator-ordered 2026-08-30): 6 entries, each net-deletion-shaped, mapped in `FINDINGS.jsonl` refs — see `specs/backlog/BACKLOG.json` ids `dissolve-container-feature-composition`, `session-binding-deep-module`, `specs-single-decider-folds`, `projection-finish-k3`, `specs-tree-model-rule-registry`, `design-audit-residue-hygiene`.

**Architecture invariant this audit re-states (the one lesson of 539 bugs):** a fix that adds a branch, flag, param, or compensating mechanism to a surface grew it and will breed the next bug; a fix that deletes a decider ends the family. Measured, not asserted — §2.
