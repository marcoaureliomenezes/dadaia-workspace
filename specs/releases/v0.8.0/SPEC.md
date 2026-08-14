# SPEC — Release v0.8.0 — Audit disposition

**Status:** Aprovado
**Release ID:** v0.8.0
**Owner:** product-engineer
**Opened:** 2026-08-14
**Created:** 2026-08-14
**Branch:** `feature/v0.8.0` (cut from `develop` at `d3e05d19`; branch contract: `dadaia-gitflow`)
**Consumes:** the two undispositioned audits
`specs/audits/2026-07-15-consumer-dadaia-integration.md` (12 findings) and
`specs/audits/2026-07-18-architecture-resilience-review.md` (W1–W6). **No backlog entry and
no bug is picked into this release.**
**Grill (mandatory, done):**
`.dadaia/reports/dadaia-workspace/product-engineer/2026-08-14T130830Z-refine-specs.html`
— ADRs #1, #2, #3b are binding for this release.
**Triage evidence:**
`.dadaia/reports/dadaia-workspace/product-engineer/2026-08-14T041500Z-deep-triage.html`
— finding-by-finding verification of both audits against HEAD `8a8f4f80`.

---

## 1. Problem and context

Two audits sit loose in `specs/audits/`, neither dispositioned:

| Audit | Findings | Named remediation release | State |
|---|---|---|---|
| `2026-07-15-consumer-dadaia-integration.md` | 12 (1 CRITICAL, 5 HIGH, 6 MEDIUM) | `v0.2.5` | v0.2.5 shipped and archived, but its CLOSURE contains **no finding-by-finding disposition** of this audit (grep `2026-07-15` / `consumer-dadaia-integration` in `specs/_archive/releases/v0.2.5/CLOSURE.md` → 0 matches) |
| `2026-07-18-architecture-resilience-review.md` | W1–W6 (over a 25-bug dataset) | none | the audited object — the lifecycle workflow engine — was demolished in v0.3.0 (`specs/_archive/releases/v0.3.0/CLOSURE.md:10-17`; net **−60 108** lines, `:38`) |

Two consequences follow from the law:

1. **§5 precedence** — "at pick time, open bugs and undispositioned audits outrank fresh
   backlog". While these two audits stay undispositioned they outrank *every* backlog entry
   in *every* future pick. The queue cannot advance honestly around them.
2. **§5 audits** — "One audit generates exactly one remediation release, and that release
   gives **every** finding an explicit disposition… An audit archives to
   `specs/audits/_archive/` only once fully dispositioned by an approved release, and names
   that release."

The triage established that the remaining *work* behind both audits is near zero: 8 of the
12 consumer-audit findings are fixed at HEAD with verifiable evidence, and W1–W5 of the
resilience audit have no object left to fix. What is missing is not code — it is **the
disposition record**. This release writes that record and archives both audits.

---

## 2. Objective

Give every finding of both audits an explicit, evidenced disposition; archive both audits to
`specs/audits/_archive/` naming **v0.8.0** as the disposing release; and leave the memory
atom that describes audit governance truthful about the contract this release executes.
Ship no product code.

---

## 3. Scope

### FR1 — Disposition record for the consumer-integration audit (2026-07-15)

The audit file receives an **additive-only** edit: its findings text is never altered (the
`specs/audits/README.md` immutability rule), and the file gains (a) frontmatter disposition
markers and (b) one `## Disposition — release v0.8.0` section carrying the table below,
verbatim. Findings are identified `F-01…F-12` in the file's own table order.

| # | Sev | Finding (audit text, short) | Disposition | Evidence |
|---|-----|------|------|------|
| F-01 | CRITICAL | No versioned provider↔consumer compatibility contract exists | `fixed` | `dadaia_workspace/public/schemas/dadaia-capabilities-v2.schema.json`; `features/capabilities/service.py:11` (`CAPABILITY_SCHEMA_VERSION`); enforced at `features/certification/service.py:137` and `features/reconcile/service.py:142` (both reject `schema_version != "dadaia-capabilities-v2"`) |
| F-02 | HIGH | Consumer upgrades only the persistent wheel | `fixed` | `features/reconcile/service.py:1` ("Post-install **transaction** for state, projections, doctors, and capabilities"), `_snapshot_state` `:37`, `_restore_state` `:55`, `rollback_required` `:24`, permission preflight `:90` |
| F-03 | HIGH | Consumer prompt and tests preserve removed lifecycle commands | `deferred` | Not provable from this tree (target is the external consumer repo). Inherited in full as acceptance criteria by `specs/backlog/consumer-side-validation-round.md` (grill ADR #1). Premise also shifted: v0.3.0 removed the whole `dadaia lifecycle` verb group (`specs/_archive/releases/v0.3.0/CLOSURE.md:10-17`) |
| F-04 | HIGH | Fresh root-level `codex exec` misses target-repository context | `fixed` | `dadaia_workspace/hooks/ctx_inject.py` (bind-driven context-memory injection) + single resolution authority with PATH-first `target_path` at `hooks/sdd_gate.py:9-16`; contract stated in law §3 |
| F-05 | HIGH | Existing E2E does not certify the assembled consumer journey | `fixed` | `public/data/CONSUMER_VALIDATION_RECIPE.md` + `specs/memory/product/platform/consumer-agent-support.md:20-44`: the deterministic matrix F-01…F-26 is "necessary, never sufficient alone" and the real-use matrix R-01…R-08 is mandatory for every candidate. Resolved more strongly than requested — the release gate became the consumer-side validation agent, not an internal E2E |
| F-06 | HIGH | The consumer owning repository is governance-incoherent | `deferred` | Not provable from this tree (external repo; no file here attests its marker/memory state). Inherited in full as acceptance criteria by `specs/backlog/consumer-side-validation-round.md` (grill ADR #1) |
| F-07 | MEDIUM | `context list --json` documented but unsupported | `fixed` | `cli/commands/context.py:201-226` — `--json` flag, stable 8-field-per-context contract |
| F-08 | MEDIUM | `context heartbeat` ignores the persisted bind | `fixed` | `cli/commands/context.py:649-665` — resolves the caller-owned session from the explicit override **or** the harness-native session id persisted by `context bind`; actionable error when no identity exists |
| F-09 | MEDIUM | Unbound context resolution selects the first ALIVE context | `fixed` | Single authority `container.resolve_context`; `hooks/sdd_gate.py:88-91` binds a target under `repos/<slug>/` to `<slug>` "regardless of `DADAIA_CONTEXT` or which context is first-ALIVE in the registry"; `first.?alive` grep in `core/specs_resolver.py` → 0 matches; ratified as law §3 |
| F-10 | MEDIUM | Empty-repository onboarding has no explicit baseline contract | `superseded` by bug `context-alive-sweeps-unrelated-worktree-changes` | The baseline itself exists — `features/spec_context/service.py:360-420` (scaffold merge preserving a pre-existing tree, `repo-AGENTS.md`, conditional `tests/AGENTS.md`, baseline commit). The residue the audit asked for — *operator-consented* initialization — is exactly the open bug's object: the baseline commit stages `git add -u` over the whole worktree (`infrastructure/git_subprocess.py:43`, called from `service.py:416-420`). The residue is therefore carried by a registered open bug, fixed Arm B on `hotfix/{M.m.p}` (§1), never dropped |
| F-11 | MEDIUM | Telegram delivery truncates diagnostic output | `rejected` — obsolete in this repository | The surface is gone: `telegram` appears **once** in `dadaia_workspace/`, at `public/data/CONSUMER_VALIDATION_RECIPE.md:498-499`, and it is the *solution* (a one-line bounded "Verdict line (Telegram-short)" ending in `evidência: <path>`), not the defect. The transport itself belongs to the operator's private environment, declared out of this library's scope by `specs/memory/product/platform/consumer-agent-support.md:56-61` |
| F-12 | MEDIUM | Academy notes mistaken for executable agent knowledge | `fixed` | Versioned operational knowledge ships as **skills** inside the wheel (`specs/memory/tech-stack.md:41-44`); Academy is a read-only browse surface over `knowledge_basis` (memory atom `academy`, catalog rank 5) |

**Score:** 8 `fixed` · 1 `superseded` · 1 `rejected` · 2 `deferred`. Twelve of twelve
dispositioned; nothing dropped.

**Acceptance**

- A1.1 The audit file carries a `## Disposition — release v0.8.0` section whose table has
  exactly 12 rows, one per audit finding, each with a disposition token from
  {`fixed`, `superseded`, `deferred`, `rejected`} and a non-empty evidence cell.
- A1.2 Every original line of the audit's `## Verdict`, `## Findings and required
  dispositions` and `## Acceptance boundary` sections is byte-identical to its pre-release
  content (`git diff` shows additions only).
- A1.3 The file carries a disposing-release pointer matching SPEC-DOC-036
  (`disposing_release: v0.8.0` in frontmatter and a `**Disposition:** v0.8.0 …` line).
- A1.4 Both `deferred` rows name `specs/backlog/consumer-side-validation-round.md`, and that
  file exists and carries both findings as acceptance criteria.
- A1.5 The `superseded` row names the bug slug `context-alive-sweeps-unrelated-worktree-changes`,
  and that bug is present and open in `specs/bugs/bugs.jsonl`.

### FR2 — Disposition record for the architecture-resilience audit (2026-07-18)

Same additive-only contract. **The unit of disposition for this audit is W1–W6** — the
"five structural weaknesses" of §2 plus W6 — and the four proposals of §4 map onto rows
W4/W5/W6 plus the W1–W3 "DONE" statement. The 25-row dataset of §1 is the audit's
*evidence*, not its findings, and is not separately dispositioned; the SPEC states this
so the count is auditable rather than implicit.

| # | Finding | Audit's own status | Disposition | Evidence |
|---|---------|--------------------|-------------|----------|
| W1 | Implicit worker↔gate contract | "Now enforced" | `rejected` — moot by removal | Declared DONE by the audit itself (`:102`); the workers and envelopes it governed were deleted in v0.3.0. `run_store\|AgentRunResult\|domain_payload\|emit_progress\|fragment_gate\|WorkflowEngine` → **0 matches in production code** at HEAD |
| W2 | Model steps held state-mutation power | "Now enforced" | `rejected` — moot by removal | DONE + object removed. The surviving sentence ("workers produce artifacts; Python produces effects") is an architecture principle, not an open item |
| W3 | Gates validated reports, not reality | "Now enforced" | `rejected` — moot by removal | DONE + object removed. The living equivalent is the diff-based push gate (`features/chokepoints/service.py:309`), which validates a real sha |
| W4 | Three parallel engines → proposed `workflow-engine-unification` | "Remaining (proposed, next release) — the single highest-leverage simplification left" | `rejected` — superseded by demolition | The three engines were deleted, not unified: `specs/_archive/releases/v0.3.0/CLOSURE.md:10-17`, net −60 108 lines (`:38`), ≈ −25 419 LOC of production code. A strictly larger simplification than the one proposed |
| W5 | No canonical path convention → proposed `normalize_zone()` | "Remaining (proposed)" | `rejected` — premise dead | The "zone" concept (a TASKS write-set inside the engine) no longer exists: `normalize_zone\|write_scope` in `dadaia_workspace/` → 0 matches; the only surviving `zone` is the unrelated `HygieneZone` (`core/models/hygiene.py:72`) |
| W6 | Projected assets duplicate package logic → proposed thin wrappers | "Remaining (proposed)" | `superseded` by `specs/backlog/thin-wrapper-projected-scripts.md` | The concern survived the demolition because the projected scripts did: `public/scripts/lint-memory-atoms.py` is still a standalone re-implementation, and the direction is today **inverted** — the package shells out to the script (`features/specs/doctor_memory.py:38-40,357`). Extracted as a backlog entry written against HEAD with the corrected direction (grill ADR #2) |

**Acceptance**

- A2.1 The audit file carries a `## Disposition — release v0.8.0` section with exactly 6 rows
  (W1–W6), each with a disposition token and non-empty evidence.
- A2.2 The section states explicitly that §1's 25-row dataset is evidence, not findings, and
  that §4's four proposals map onto W4/W5/W6 + the W1–W3 DONE statement.
- A2.3 Original audit content is byte-identical (`git diff` shows additions only).
- A2.4 The file carries the SPEC-DOC-036 disposing-release pointer (`v0.8.0`).
- A2.5 The `superseded` row names `specs/backlog/thin-wrapper-projected-scripts.md`, and that
  file exists and carries W6's concern with the corrected direction.

### FR3 — Both audits archived, naming v0.8.0

Both files move to `specs/audits/_archive/` with the established suffix
(`--dispositioned-v0.1.61`, `--dispositioned-v0.1.76` precedent):

```
specs/audits/_archive/2026-07-15-consumer-dadaia-integration--dispositioned-v0.8.0.md
specs/audits/_archive/2026-07-18-architecture-resilience-review--dispositioned-v0.8.0.md
```

The move is a `git mv` — `specs/audits/_archive/` is FROZEN (law §3), so **the file content
must be final before the move**. This ordering is a hard precondition in TASKS, not a
preference: after the move the file cannot be edited to repair an incomplete table.

**Acceptance**

- A3.1 Both paths above exist after the move; neither audit remains loose in `specs/audits/`.
- A3.2 The move preserves history (`git log --follow` resolves the pre-move path).
- A3.3 `dadaia specs doctor` reports **no** SPEC-DOC-036 issue for either archived file.

### FR4 — Memory reflects the audit-governance contract

`specs/memory/product/sdd/sdd-bug-backlog-governance.md` describes audit disposition without
the 1:1 release mapping and without the archived-audit pointer that
`dadaia specs doctor` (SPEC-DOC-036) enforces today. Both are current product truth,
independent of this release; the atom is corrected in the DEFINITION phase (law §5: memory is
`product-engineer`-writable in `DEFINITION` and `CLOSURE`).

**Acceptance**

- A4.1 The atom's `## Release And Audit` section states (i) one audit generates exactly one
  remediation release, (ii) that release dispositions every finding as `fixed`/`superseded`/
  `deferred`/`rejected`, (iii) the archived audit names its disposing release.
- A4.2 The edit adds no changelog/history/version section and no narrative of past versions
  (memory atomicity, `specs/AGENTS.md`).
- A4.3 `dadaia specs doctor` stays green on memory checks (LINT-1, CAT-1, SPEC-DOC-008); the
  atom's slug is unchanged so `catalog.json` needs no regeneration.

### FR5 — Evidence of a clean disposition

**Acceptance**

- A5.1 `dadaia specs doctor` output is captured **before** and **after** the archive move, and
  both are recorded in `CLOSURE.md` as validation evidence.
- A5.2 The post-move run shows no new ERROR/WARNING attributable to this release.
- A5.3 `CLOSURE.md` carries a `## Dispositions` table listing the two audits (kind `audit`,
  terminal status `ARCHIVED — dispositioned v0.8.0`) and stating explicitly that **no backlog
  entry and no bug was picked**, so no backlog/bug status is flipped by this closure.

---

## 4. Out of scope (non-goals)

1. **No product code.** No file under `dadaia_workspace/` is modified. This release writes
   disposition records, memory prose, and moves two files.
2. **Nothing from grill release 2** — `push-range-denylist-scan` (range scope, tag coverage,
   FROZEN↔scan invariant, redaction-at-authoring FR) is a separate release.
3. **Nothing from grill release 3** — `dd-lifecycle-skills-family` (7 skills, dehydration
   cuts, Scenario-1 rename, F-0 persona fix, `BACKLOG.md` consolidation, §5 amendments) is a
   separate release.
4. **No bug-ledger write.** No `bugs append` event is emitted by this release —
   `panel-telemetry-sqlite-corrupts-under-concurrent-access` stays `deferred` (operator
   decision pending, recorded in the PM handoff), and the dangling
   `panel-runtime-reliability` pointer noted by the triage is **not** repaired here.
5. **No Arm B fix.** `context-alive-sweeps-unrelated-worktree-changes` is a bug: it runs Arm B
   on `hotfix/{M.m.p}`, outside this release (§1). F-10's `superseded` disposition points at
   it; it does not import it.
6. **No backlog authoring or curation.** `specs/backlog/**` belongs to `project-manager`.
   This release *reads* `consumer-side-validation-round.md` and
   `thin-wrapper-projected-scripts.md` and cites them; it does not create, edit, or
   disposition them — both stay `candidate`.
7. **No repair of the two stale live release directories** (`specs/releases/v0.2.6/`,
   `specs/releases/v0.2.9/`) observed during definition. Recorded as a closure observation for
   the PM, not picked.
8. **No audit re-verification.** Evidence is inherited from the deep-triage report, which
   verified all 18 findings against HEAD `8a8f4f80` file-by-file. This release does not re-run
   that verification; it records it.

---

## 5. Memory files affected at closure

| File | Change | When |
|---|---|---|
| `specs/memory/product/sdd/sdd-bug-backlog-governance.md` | `## Release And Audit` gains the 1:1 audit→release contract and the archived-audit disposing-release pointer; `## Runtime State` gains the `_archive` audit path | **DEFINITION** (FR4), recorded again in CLOSURE |
| `specs/memory/product/index.md`, `catalog.json` | no change — no feature added, removed or re-ranked | — |
| `specs/memory/architecture.md`, `tech-stack.md` | no change — no layer, dependency or command touched | — |

---

## 6. Dependencies and risks

| # | Item | Status |
|---|---|---|
| D1 | `specs/backlog/consumer-side-validation-round.md` must exist before F-03/F-06 can be `deferred` | **satisfied** — created by PM (commit `095311dc`) |
| D2 | `specs/backlog/thin-wrapper-projected-scripts.md` must exist before W6 can be `superseded` | **satisfied** — created by PM (commit `2df01e56`) |
| D3 | The `git mv` of two audit files and every commit require an agent with shell access | product-engineer has none; every git step is an explicit TASKS entry owned by the dispatcher/`software-engineer` |
| R1 | **Irreversible ordering** — `_archive/` is FROZEN; a table archived incomplete cannot be repaired in place | Mitigated by A1.1/A2.1 completeness verification as a task that *precedes* the move task |
| R2 | A future reader treats the resilience audit's 25-row dataset as 25 undispositioned findings | Mitigated by A2.2: the disposition section states the unit of disposition explicitly |
| R3 | The two `deferred` findings look like a silent drop | Mitigated by A1.4: both are inherited as acceptance criteria of a live backlog candidate, and the audit names it |
| R4 | Disposition tokens drift from the closure vocabulary | Tokens used here are exactly `fixed` / `superseded` / `deferred` / `rejected` (law §5, `dadaia-release-closure`) |

---

## 7. Approval

This SPEC is `Draft`. Approval is the operator's: SPEC → PLAN → TASKS, each to
`**Status:** Aprovado`, before milestone (a) of the `dadaia-gitflow` contract fires.
