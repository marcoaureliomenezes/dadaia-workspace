# CLOSURE — Release 0.1.6 "Consolidation"

**Status:** Aprovado
**Release ID:** 0.1.6 (patch over 0.1.5)
**Closed:** 2026-06-08
**Branch:** `feature/0.1.6` (unpushed — merge + PyPI publish are operator-gated)

---

## 1. Summary

0.1.6 compiled the entire open backlog + all open bugs into one patch release over the
published 0.1.5. It split into a **net-new** half (panel rework, specs-evolution migration
framework, software-architect specialization, Codex SessionStart injection) and a
**verify-and-reconcile** half — large tracts (lock subsystem, 15→9 roster, gate shrink,
Codex semantic projection, D-CX doctor suite) were already implemented in-tree (v0.1.7/v0.1.8
milestones on the branch base) and were validated against each task's done-criterion rather
than destructively re-done.

All 46 alpha tasks + the rc-1 ship trio are `[x]`. Full CI-equivalent suite green:
**2358 passed, 2 skipped** (env-benign), `ruff format --check` + `ruff check` + `mypy --strict`
clean.

## 2. What shipped (by workstream)

| WS | Tasks | Outcome |
|---|---|---|
| WS-PANEL | P01–P13 | memory-doc-link fix (canonical URL builder), token TOCTOU fix, WorkflowLauncher→infra, auth route unification, tab consolidation (Projects/Agentic renames, Kanban→Workflows→Agents order, 40%-smaller cards, §7 4-stage kanban), theme redesign. |
| WS-SANITIZATION | Z01–Z04 | `--workspace` flag honored; ROOT-1..4 doctor; `dadaia clean`; `_configure_hook` canonical nested hook schema (Z04 root-cause). |
| WS-SPECS-EVOLUTION | S01–S06 | **net-new** migration framework: `core/specs_version.py` + `core/specs_backup.py` (pure, stdlib-only), `features/migrate/{registry,upgrade}.py`, `dadaia specs upgrade` (backup-first→chain→re-stamp→doctor), SPECS-VERSION doctor warn, `alive()` safe-preserve (FR-S06 path a), constitution `specs_pattern_version: 1` stamp. |
| WS-CODEX | C01–C11 | **C01/C02** net-new: SessionStart context injection + stable session-id keying (env+stdin, no `$$`), per-prompt silence. **C03** fail-safe-block on empty persona for `specs/backlog/`. **C11** harness-skill cadence wording. C04/C05/C06/C07/C08/C09/C10 verified already-satisfied (codex.py + golden tests, Starlark `.rules` + D-CX-8, gate-block smoke test, TOML least-privilege mapping, memory truth, clean harness paths, D-CX-1..10). |
| WS-SDD-LIFECYCLE | L01–L04 | L01–L03 verified built (single TTL-lease, `is_stale` injectable clock, O_EXCL CAS, `dadaia lock steal`, doctor GC). L04 "coordinator-enforced checkpoint" relabel across reviewer/PM personas (mechanical "gate" preserved). |
| WS-AGENTS | A01–A08 | A01 roster-reduction strategy record; A02 prune+orphan verified; A03 dangling refs verified-clean; A04/A06 bug `adopted:` → 0.1.6; A05 constitution plugin-stub exemption (§14+§12.1); A07 9-core+3-stub verified. **A08** (operator focus): software-architect specialized as anti-slop/anti-spaghetti reviewer + root-cause & architecture-fidelity review gates + new `architect-core-workflow` skill + WebSearch grant. |
| rc-1 | R01–R04 | qa full-suite (R01), security-reviewer (R02), code-reviewer (R03), software-architect root-cause + architecture-fidelity gates — **all APPROVE**. This CLOSURE (R04). |

## 3. Review evidence (rc-1)

- **qa-engineer (R01):** full suite 2358 passed; ruff + mypy --strict clean. APPROVE.
- **security-reviewer (R02):** APPROVE. One LOW (CWE-22) — `SESSION_ID`/`DADAIA_SESSION_ID`
  unsanitized before filename use in `ctx-inject.sh` — **fixed** (`tr -cd 'a-zA-Z0-9_-'` +
  non-empty guard, mirroring `sdd-spec-gate.sh`).
- **code-reviewer (R03):** APPROVE (after re-verification — its two initial findings did not
  survive contact with the actual code).
- **software-architect (gates):** Root-cause gate **PASS** — Z04/C01/C03 are genuine
  root-cause fixes, no workarounds. Architecture-fidelity gate **PASS** — the `core/`
  placement of the migration primitives is the correct call (avoids the prohibited
  feature→feature import, architecture.md:163). Two LOW doc findings — **fixed** (SPEC §5 +
  PLAN write-set now list the `core/` modules with rationale).

## 4. Memory updated (CLOSURE phase, §13)

- `specs/memory/architecture.md` — ctx-inject.sh section: Codex `SessionStart` once-per-session
  injection, stable `SESSION_ID` resolution (env + stdin, no `$$`), per-prompt silence.
- `specs/memory/tech-stack.md` — Bash row: once-per-session injection + stable session-id keying.

## 5. Bug dispositions (root cause only — no workarounds)

- `configure-hook-writes-malformed-duplicate-userpromptsubmit` → Fixed (Z04, root cause).
- Codex session-key instability → Fixed (C01, root cause; `$$` removed).
- Backlog empty-persona fall-through → Fixed (C03, FORK-4 grilled decision).
- `agent-skill-surface-slop`, `constitution-persona-single-source-drift` → `adopted: 0.1.6`.
- `software-architect-workspace-specialization` (FEAT-SA-WORKSPACE-SPEC-01) → superseded by
  `software-architect-anti-slop-specialization` (FEAT-SA-ANTISLOP-01), implemented under A08.

## 6. Remaining backlog (deferred, not dropped)

- The 6 pre-existing memory-atom heading/token-estimate WARNs (curated-allowlist) — cosmetic.
- 8 pre-existing SPEC-DOC-016 SemVer-folder WARNs on legacy release dirs.

## 7. Operator-gated next steps (NOT performed)

1. `git mv specs/releases/0.1.6 specs/_archive/releases/0.1.6` after merge.
2. Merge `feature/0.1.6` → `main`; tag `v0.1.6`.
3. PyPI publish (deploy stays operator-gated, as in v0.2.0).
