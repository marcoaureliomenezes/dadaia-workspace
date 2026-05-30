# PLAN — Release: spec-context-tree-v2

**Status:** Aprovado
**Release ID:** spec-context-tree-v2
**Owner:** product-engineer
**Opened:** 2026-05-30

---

## 1. Dependencies (activation gate)

This release may NOT enter IMPLEMENTATION until:

1. **`go-open-source` phase = ARCHIVED** — gate in `ACTIVE.md` must be freed.
   R1 and `go-open-source` have disjoint write sets, so SPEC/PLAN authoring proceeds
   in parallel; implementation blocks until ACTIVE.md is free.
2. **Operator approval of SPEC.md** — `**Status:** Aprovado` required before PLAN.
3. **Operator approval of this PLAN.md** — `**Status:** Aprovado` required before TASKS.

**R1 is a hard prerequisite for Release 2 (`spec-context-session-locks-v1`).**
R2 implementation must NOT begin until R1 phase = ARCHIVED.

---

## 2. Strategy overview

The work is purely additive or cleanup (MINOR semver bump). No runtime state model
changes (those are R2). The implementation fits cleanly into three sequenced waves:

**Wave 1 — Foundation cleanup** (T-1, T-2, T-4, T-6, T-8a)
Remove legacy scaffold artifacts; add missing scaffold directories and HTML memory
stubs; clean the gate's dead fallback path. These tasks are independent of each other
and can be executed by `software-engineer-python` in any internal order within the wave.

**Wave 2 — New scaffold artifacts** (T-3, T-5, T-7)
Add product memory folder catalog (`memory/product/`), `specs/AGENTS.md`, and the three
new CLI commands (`release new`, `backlog new`, `bug new`, `memory product add`). T-3 and
T-5 require Wave 1 to be committed (they reference paths that Wave 1 establishes); T-7
also requires the `backlog/` and `releases/` directories from T-4.

**Wave 3 — Doctor TREE invariants + tests** (T-9, QA)
Doctor invariants reference all artifacts from Waves 1-2. `qa-engineer` runs the full
TREE test suite (14 tests, AC-D-1..D-16), gate integration tests (AC-G-1..G-8), and the
onboarding E2E (AC-O-1) only after Wave 2 is committed.

After Wave 3 passes, `devops-engineer` runs `dadaia public stage && dadaia public install
--target all` to propagate scaffold and script changes.

---

## 3. Layers affected

| Layer | Changed by |
|-------|-----------|
| `dadaia_workspace/public/scaffold/` | T-1, T-2, T-3, T-4, T-5, T-6 |
| `dadaia_workspace/public/templates/` | T-5 (new `specs-AGENTS.md` template) |
| `dadaia_workspace/features/spec_context/doctor.py` | T-9 |
| `dadaia_workspace/features/spec_context/service.py` | T-1 (line 119 fallback removal) |
| `dadaia_workspace/cli/commands/` | T-3, T-7 |
| `dadaia_workspace/public/scripts/sdd-spec-gate.sh` | T-8a |

No changes to `core/models/spec_context.py`, `infrastructure/json_context_store.py`,
`.dadaia/states/`, or any hook beyond the gate cleanup in T-8a.

---

## 4. OQ-4 resolution (static vs dynamic scaffold HTML)

Per SPEC §9 OQ-4 working assumption: scaffold HTML files are **static pre-rendered
stubs** committed to `public/scaffold/memory/`. `dadaia context create` performs a
simple file copy (no Jinja at creation time). `dadaia public stage` re-renders these
stubs from the canonical Jinja templates when the templates change.

`software-engineer-python` must confirm this is consistent with the existing `dadaia
public stage` pipeline before writing T-2/T-3. No new dependency; the Jinja2 rendering
step is already in the stage pipeline for other assets.

---

## 5. Execution order DAG

```
T-1 ─────────────────────────────────────┐
T-2 ──────────────────────────────────── ├─→ T-9 → QA Wave 3 → devops
T-4 ─┬─────────────────────────────────── ┘
     ├──→ T-3 ─────────────────────────────┤
     └──→ T-7 (needs backlog/, releases/)  ┤
T-5 ─────────────────────────────────────┤
T-6 ─────────────────────────────────────┤
T-8a ────────────────────────────────────┘
```

T-3 depends on T-4 (needs `releases/` directory in scaffold before creating
`memory/product/`). T-7's `dadaia bug new` and `dadaia backlog new` depend on T-4
providing the target directories. All other Wave 1 tasks are fully independent.

---

## 6. Technical risks and mitigations

| Risk | Mitigation |
|------|-----------|
| T-8a gate change breaks consumer with old tree | AC-G-2..G-8 gate tests gate the PR; fallback is dead code per ADR D-9 |
| Scaffold HTML diverges from Jinja templates over time | TREE-3/TREE-5 doctor invariants detect drift; doctor runs in CI |
| OQ-4 resolution conflicts with existing stage pipeline | Confirm in Wave 1 before T-2/T-3 start; no new PyPI dep |
| `dadaia migrate tree-v2` moves approved content | TREE-1/TREE-2 warn-only; explicit `--yes` required; AC-M-5 gates PR |

---

## 7. Validation plan

All acceptance criteria in SPEC §7 are validated before CLOSURE:

- **Unit + integration tests:** `poetry run pytest` must be green with coverage unchanged
  or improved.
- **TREE invariant tests (T-9):** 14 tests (AC-D-1..D-16), all on real `tmp_path`.
  Source of truth: QA strategy §5.
- **Gate tests (T-8a):** AC-G-1..G-8 per QA strategy §4.2.
- **Scaffold E2E (AC-O-1):** `dadaia init → context create → context activate` produces
  a tree that passes `dadaia specs doctor` with zero violations.
- **`dadaia specs doctor` on dadaia-workspace repo itself:** exit 0 (AC-D-16).
- **`dadaia public stage && dadaia public install --target all`:** devops-engineer runs
  post-implementation; `dadaia public doctor` must exit 0.

---

## 8. Rollback

All changes are additive (new files, new CLI commands) or cleanup (dead fallback
removal). Rollback = revert commits in reverse wave order. The gate cleanup (T-8a) is
safe to revert independently (legacy fallback was dead code). No database migrations
involved.

---

*Product Engineer — dadaia-workspace | 2026-05-30*
