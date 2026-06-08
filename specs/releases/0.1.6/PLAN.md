# PLAN — Release 0.1.6 "Consolidation"

**Status:** Aprovado
**Release ID:** 0.1.6
**Owner:** product-engineer
**Date:** 2026-06-07

---

## 1. Strategy

Single `feature/0.1.6` branch. Six workstreams sequenced so each workstream's output is
trustworthy before the next depends on it. The branch matures through `alpha-N` segments
(qa-engineer commit gate only) and then `rc-N` segments (full ship trio: qa→commit,
security→push, code-review→PR).

**Implementer map (per agent):**

- `software-engineer` — all library Python code under `dadaia_workspace/features/`,
  `dadaia_workspace/core/`, `dadaia_workspace/infrastructure/`, `dadaia_workspace/cli/`,
  and all regression + unit tests under `tests/`.
- `ai-engineer` — all agentic-surface assets under `dadaia_workspace/public/**` (agents,
  skills, rules, scripts, scaffold); `.codex/` Starlark rules and projection fixes.
- `product-engineer` — `specs/constitution.md`, `specs/memory/**`, `specs/releases/**`,
  `specs/bugs/` frontmatter updates (re-stamping `adopted:` fields).
- `software-engineer + ai-engineer` — e2e tests under `tests/e2e/panel/` (shared surface:
  SE writes Playwright tests, AI-E reviews harness compliance).

---

## 2. Implementation Order

```
alpha-1: WS-PANEL (test gate first, then fixes)
  Step 1: FR-P06 — e2e global guard + CI workspace seed (makes the panel suite trustworthy)
  Step 2: FR-P07 — token file atomic create (tiny, low-risk, security)
  Step 3: FR-P01 — canonical memory-URL builder + chip/iframe fix
  Step 4: FR-P05 — wikilink renderer parameterized by slug (depends on FR-P01 builder)
  Step 5: FR-P03 — auth route unification
  Step 6: FR-P04 — WorkflowLauncher extract to infrastructure
  Step 7: FR-P02 — theme switcher functional fix
  Step 8: FR-P08 — tab consolidation (Agents+Workflows+Kanban → one tab)
  qa-engineer alpha-1 commit gate

alpha-2: WS-SANITIZATION
  Step 9:  FR-Z01 — init --workspace flag
  Step 10: FR-Z02 — SANITIZE-03/04/05 (canonical .dadaia layout, clean command, ROOT doctor)
  qa-engineer alpha-2 commit gate

alpha-3: WS-SPECS-EVOLUTION
  Step 11: FR-S06 — drift reconciliation (v0.2.1 T-021-15 — choose path a or b first)
  Step 12: FR-S01 — pattern version stamp in constitution.md frontmatter
  Step 13: FR-S02 — migration-chain registry
  Step 14: FR-S03 — backup-first implementation
  Step 15: FR-S04 — dadaia specs upgrade command
  Step 16: FR-S05 — doctor integration + wire create/alive
  qa-engineer alpha-3 commit gate

alpha-4: WS-CODEX (forks FORK-2/3/4 resolved — see SPEC §11)
  Step 17: FR-C01 — ctx-inject.sh idempotence fix (SessionStart + stdin session_id)
  Step 18: FR-C03 — Claude duplicate hook hygiene + OpenCode regression proof
  Step 19: FR-C02 — deterministic Codex workflow preflight (combination: PreToolUse + SessionStart + rules)
  Step 20: FR-C04 CX-1..CX-7 — full Codex compatibility (substantial; may span sub-alphas)
  qa-engineer alpha-4 commit gate

alpha-5: WS-SDD-LIFECYCLE (FORK-1 resolved — honest relabel, no new hooks)
  Step 21: FR-L01 — TTL-lease redesign (gate shrink, atomic migration)
  Step 22: FR-L02 — review-gate honest relabel (rename gate → coordinator-enforced checkpoint)
  Step 23: FR-L03 — session orchestration absorbed into FR-L01 (verify acceptance)
  qa-engineer alpha-5 commit gate

alpha-6: WS-AGENTS
  Step 24: FR-A01 — agent skill surface slop (strip dangling refs; ai-engineer strategy first)
  Step 25: FR-A03 — install prune + doctor orphan detection
  Step 26: FR-A02 — constitution/persona single-source drift fix (P1a..P1d, P2a..P2c)
  Step 27: FR-A04 — roster reduction 15→9 (ai-engineer strategy → PE authors tasks → SE+AI-E impl)
  qa-engineer alpha-6 commit gate

rc-1: Full ship trio (qa + security + code-review) → merge → CLOSURE
```

**Rationale for alpha ordering:**

WS-PANEL first so the e2e global guard exists before any other panel-touching workstream
ships — the guard is the safety net for the entire release. WS-SANITIZATION second because it
is low-blast-radius and closes the `init --workspace` footgun quickly. WS-SPECS-EVOLUTION third
because it depends on the clean workspace invariants from WS-SANITIZATION. WS-CODEX fourth
because the four open forks must be resolved in the grill before code can start; it is
self-contained. WS-SDD-LIFECYCLE fifth because FR-L01 (gate rewrite) is the highest integration
risk and should land after the test suite is maximally trustworthy. WS-AGENTS last because the
roster reduction requires an ai-engineer strategy step, which is a planning phase, and must land
on a stable gate base.

---

## 3. WS-PANEL (software-engineer + ai-engineer, alpha-1)

**Write set (software-engineer):**
- `dadaia_workspace/features/panel/handler.py`
- `dadaia_workspace/features/panel/auth.py`
- `dadaia_workspace/features/panel/views/index.py`
- `dadaia_workspace/features/panel/views/wrapper.py`
- `dadaia_workspace/features/panel/views/_md_render.py`
- `dadaia_workspace/features/panel/views/assets/js/themes.js`
- `dadaia_workspace/features/panel/views/` (tab consolidation views)
- `dadaia_workspace/features/panel/service.py`
- `dadaia_workspace/core/protocols/` (WorkflowLauncher — new)
- `dadaia_workspace/infrastructure/` (WorkflowLauncher impl — new)
- `tests/e2e/panel/` (new and revised e2e tests)
- `tests/unit/` (auth, token, WorkflowLauncher unit tests)

**Write set (ai-engineer, CSS/JS overhaul for theme + tab consolidation):**
Any browser-facing CSS constants or panel asset template changes that ai-engineer owns as
agentic-surface (confirm boundary with software-engineer at task start; no duplicate write-set).

Gate: qa-engineer commit gate at end of alpha-1.

---

## 4. WS-SANITIZATION (software-engineer, alpha-2)

**Write set:**
- `dadaia_workspace/core/workspace_resolver.py`
- `dadaia_workspace/features/specs/doctor.py` (ROOT-1..ROOT-4)
- `dadaia_workspace/cli/main.py` (`dadaia clean` command)
- `tests/unit/` (workspace-resolver fix, clean command, ROOT doctor invariants)

Gate: qa-engineer commit gate at end of alpha-2.

---

## 5. WS-SPECS-EVOLUTION (software-engineer + product-engineer, alpha-3)

**Write set (software-engineer):**
- `dadaia_workspace/features/spec_context/service.py`
- `dadaia_workspace/features/migrate/` (chain registry)
- `dadaia_workspace/features/specs/doctor.py` (pattern-version check, upgrade recommendation)
- `dadaia_workspace/cli/main.py` (`dadaia specs upgrade` subcommand)
- `tests/unit/` (migration chain, backup-first, idempotence, upgrade command)

**Write set (product-engineer):**
- `specs/constitution.md` (frontmatter version stamp — FR-S01)
- `specs/bugs/` (v0.2.1 drift reconciliation annotations, if path b is chosen)

Note on FR-S06 drift reconciliation: the PLAN must state which path (a) or (b) is chosen for
the v0.2.1 T-021-15 claim before this workstream begins. Path (a) = implement the backup (the
natural resolution; FR-S03 delivers it). Path (b) = correct the comment + annotate the archived
record. The SPEC recommends path (a) because FR-S03 already delivers backup-first as a first-class
feature — the v0.2.1 claim then becomes retroactively satisfied. The operator confirms at grill.

Gate: qa-engineer commit gate at end of alpha-3. `dadaia specs doctor` must exit 0.

---

## 6. WS-CODEX (ai-engineer + software-engineer, alpha-4)

**Prerequisite:** Forks FORK-2/3/4 resolved (SPEC §11). SessionStart + stdin `session_id`
is the Codex bootstrap mechanism; already-fired path emits nothing + exit 0; combination
PreToolUse + SessionStart routing + rules + advisory is the preflight mechanism.

**Write set (ai-engineer):**
- `dadaia_workspace/public/scripts/ctx-inject.sh`
- `.codex/hooks.json`
- `dadaia_workspace/public/` (CX-1 semantic projection source)
- Starlark `.rules` sources for CX-2

**Write set (software-engineer):**
- `dadaia_workspace/` projector code for CX-1 (`runtime_transforms/codex.py` and related)
- `tests/` (CX-3 smoke test, CX-7 doctor + CI gate tests, golden tests for CX-1)
- `dadaia_workspace/features/specs/doctor.py` or `features/public/doctor.py` (CX-7 semantic checks)

Gate: qa-engineer commit gate at end of alpha-4. `dadaia public doctor` must exit 0.

---

## 7. WS-SDD-LIFECYCLE (software-engineer + product-engineer, alpha-5)

**Prerequisite:** FORK-1 resolved (SPEC §11): honest relabel, no new git hooks. T-016-L04
is a text-only change in constitution + reviewer/PM personas.

**Write set (software-engineer):**
- `dadaia_workspace/public/scripts/sdd-spec-gate.sh` (gate shrink, TTL-lease)
- New `core/` module for the single TTL-lease record + `is_stale` predicate
- `dadaia_workspace/features/locking.py` (delete Lock-3 surface)
- `dadaia_workspace/features/semaphore.py` (retire)
- `tests/unit/` (injectable clock seam, CAS test, gate shrink regression)

**Write set (product-engineer):**
- `specs/constitution.md` (honest relabel: "gate" → "coordinator-enforced checkpoint" in
  §11 and reviewer/PM persona wording)
- `dadaia_workspace/public/agents/` (reviewer + PM persona wording updates — FORK-1 option b)

Gate: qa-engineer commit gate at end of alpha-5.
MUST-NOT-SHIP red line: gate shrink must migrate atomically — old lock path and new lock path
must change in ONE commit so no MUTATING write silently breaks during migration.

---

## 8. WS-AGENTS (ai-engineer + product-engineer, alpha-6)

**Prerequisite:** ai-engineer produces a roster-reduction strategy document reviewed by PM
before this workstream begins.

**Write set (ai-engineer):**
- `dadaia_workspace/public/agents/` (roster reduction, persona deepening)
- `dadaia_workspace/public/skills/` (prune to 17 skills)
- `dadaia_workspace/public/` (stage + install --force --target all)
- Manifest update

**Write set (software-engineer):**
- `dadaia_workspace/features/public/install.py` or equivalent (prune logic — FR-A03)
- `dadaia_workspace/features/specs/doctor.py` (orphan-projection check — FR-A03)
- `tests/` (orphan detection regression test)

**Write set (product-engineer):**
- `specs/constitution.md` (P1a–P1d, P2a–P2c single-source fixes; §14 plugin-stub exemption)
- `specs/bugs/agent-skill-surface-slop.md` (update `adopted:` to `0.1.6`)
- `specs/bugs/constitution-persona-single-source-drift.md` (update `adopted:` to `0.1.6`)

Gate: qa-engineer commit gate at end of alpha-6.
`dadaia public install --force --target all && dadaia public doctor` must exit 0.
Roster count assertion: exactly 9 core personas in `public/agents/`.

---

## 9. Technical Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| FR-L01 gate shrink breaks MUTATING path silently | Atomic migration in one commit; integration test before merge; MUST-NOT-SHIP red line in SPEC |
| FR-C04 Codex compatibility is broad (7 sub-items) | CX-7 doctor + CI gate written first; no CX-1..CX-6 lands without CX-7 as backstop |
| FR-A04 roster reduction cascades across all runtimes | `install --prune` (FR-A03) delivered before FR-A04 starts; `doctor` orphan check as gate |
| FR-P08 tab consolidation regresses Sessions tab | Sessions tab content is read-only for this task; e2e regression test covers Sessions tab behavior |
| FR-S03 backup-first fills disk on large specs/ | `--dry-run` required before any destructive step; backup dir gitignored and doctor-tolerated |
| Open forks unresolved block WS-CODEX/WS-SDD-LIFECYCLE | alphas are ordered so these workstreams start only after the grill resolves the forks |
| Scope is very large for one release | alpha-N segments isolate blast radius per workstream; each alpha has its own qa-engineer gate |

---

## 10. Validation Plan

1. `pytest -p no:cacheprovider tests/` passes (zero red) after each workstream's tasks complete.
2. `dadaia specs doctor` exits 0 on the live workspace after WS-PANEL/WS-SANITIZATION/WS-SPECS-EVOLUTION.
3. `dadaia public doctor` exits 0 after each `public/` change is staged and installed.
4. Panel e2e suite passes with E2E-GUARD-01/02 active (alpha-1 gate).
5. Two consecutive Codex prompts produce bootstrap exactly once (alpha-4 gate).
6. `dadaia specs upgrade --dry-run` on a synthetic workspace produces the correct plan (alpha-3 gate).
7. Roster count: `ls dadaia_workspace/public/agents/ | wc -l` == 9 after alpha-6.
8. `dadaia public install --prune --target all && dadaia public doctor` exit 0 with no orphans
   after alpha-6 (FR-A03 regression test).
9. Manual: ROOT-1..ROOT-4 doctor invariants pass on the live workspace.
10. rc-1 ship trio: qa-engineer + security-reviewer + code-reviewer all `APPROVED` before merge.
