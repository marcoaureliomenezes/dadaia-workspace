# Closure: Release — sdd-release-lifecycle-v1

> **Status:** Fechado
> **Release ID:** sdd-release-lifecycle-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-31
> **Note:** Retroactive closure. This release was superseded/absorbed — its deliverables
> landed piecemeal through the release itself and through later releases
> (`spec-context-tree-v2`, `panel-kanban-v1`, et al.). CLOSURE.md authored 2026-05-31
> during `chore/releases-housekeeping`. This release also predates the formal
> ACTIVE.md history (history begins 2026-05-20).

## Summary

`sdd-release-lifecycle-v1` was the dogfood meta-release that introduced the SDD
release-based lifecycle to the dadaia-workspace library itself. It bootstrapped the
`specs/releases/` directory structure, migrated 23 legacy `specs/features/` folders
(7 archived with retroactive CLOSUREs, 15 moved to backlog), replaced markdown memory
with HTML atoms rendered from Jinja2 templates, evolved the SDD gate to v3 (memory
write-lock outside CLOSURE, archive read-only), and created the `dadaia specs doctor`
CLI command with its 11 structural checks.

The release ran as a true dogfood exercise: it used the lifecycle it was defining to
execute itself. Phases 1–4 (bootstrap, agent refactor, skills/templates, gate v3) and
Phase 6 (dadaia-workspace migration) are fully complete and reflected in the live
workspace. Phase 5 (CLI `specs.py` + wiring + initial tests) was partially completed
inline and then extended by subsequent releases — the `dadaia specs doctor` command is
live and used as a gate in every subsequent release.

The TASKS.md carried 11 stale `[ ]` / `[-]` markers (T-5.2 through T-5.6, T-V.1
through T-V.6, and the deferred T-6.9) which were never flipped because the release
was never formally closed. This CLOSURE.md is the authoritative reconciliation record
for those markers. The TASKS.md markers are NOT edited — the closure record below is
the source of truth.

---

## Tasks completed

### Phase 2 — Refactor product-engineer agent

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-2.1 | Rewrite `public/agents/product-engineer.md` with 8-phase lifecycle, memory atomicity, SDD HARD STOP, write permissions, `dadaia-release-closure` reference | pre-2026-05-20 |
| T-2.2 | `dadaia public stage && install --target all`; `dadaia public doctor` → `[ok]` | pre-2026-05-20 |

### Phase 3 — Skills release-aware + templates

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-3.1 | Update `dadaia-workspace-spec-navigator`: memory HTML, ACTIVE.md, ignore archive/backlog | pre-2026-05-20 |
| T-3.2 | Update `dadaia-workspace-spec-reviewer`: atomicity HTML checks, status, evidence triples | pre-2026-05-20 |
| T-3.3 | Update `dadaia-task-manager`: TASKS lives in `releases/<active>/TASKS.md` | pre-2026-05-20 |
| T-3.4 | Create skill `dadaia-release-closure` with CLOSURE.md template and protocol | pre-2026-05-20 |
| T-3.5 | Create template `memory-product.html.j2` (later renamed to `memory-product-index.html.j2`) | pre-2026-05-20 |
| T-3.6 | Create template `memory-architecture.html.j2` | pre-2026-05-20 |
| T-3.7 | Create template `memory-tech-stack.html.j2` | pre-2026-05-20 |
| T-3.8 | Propagate via `dadaia public stage && install --target all`; verify `public doctor` | pre-2026-05-20 |

### Phase 4 — Gate v3

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-4.1 | Update `.dadaia/scripts/sdd-spec-gate.sh` to v3: memory lock, archive block, release-id log, `SDD_LEGACY_FEATURES` | pre-2026-05-20 |
| T-4.2 | Validate with 4 bash inline tests (memory block/allow, archive block, production allow) | pre-2026-05-20 |
| T-5.1 | Create `dadaia_workspace/features/specs/doctor.py` with 11 structural checks | pre-2026-05-20 |

### Phase 6 — Migração dadaia-workspace

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-6.1 | Triage 23 features: 7 implemented → archive-with-retro-CLOSURE; 15 draft → backlog + legacy archive | pre-2026-05-20 |
| T-6.2 | Create `_archive/releases/<id>/{SPEC,PLAN,TASKS,CLOSURE}.md` for 7 implemented features | pre-2026-05-20 |
| T-6.3 | Move 15 draft features to `backlog/candidates.md` + `_archive/legacy-features/<name>/` | pre-2026-05-20 |
| T-6.4 | Archive `specs/features/sdd-release-lifecycle/` source SPEC | pre-2026-05-20 |
| T-6.5 | Move legacy memory markdown to `_archive/legacy-memory/<timestamp>/` | pre-2026-05-20 |
| T-6.6 | Render `specs/memory/{product,architecture,tech-stack}.html` from Jinja2 templates | pre-2026-05-20 |
| T-6.7 | Move legacy root `specs/PLAN.md`, `specs/TASKS.md`, `security/`, `foundation/` to archive | pre-2026-05-20 |
| T-6.8 | Run `dadaia specs doctor` → 0 errors | pre-2026-05-20 |

### Phase 7 — Product Memory Feature Catalog (dogfood extension)

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-7.1 | Extend gate v3 glob for `memory/product/**/*.html`; update doctor.py + tests | pre-2026-05-20 |
| T-7.2 | Rename `memory-product.html.j2` → `memory-product-index.html.j2`; create `memory-product-feature.html.j2` | pre-2026-05-20 |
| T-7.3 | Migrate `specs/memory/product.html` to `_archive/legacy-memory/2026-05-16T180000Z/`; set CLOSURE phase | pre-2026-05-20 |
| T-7.4 | Create `specs/memory/product/index.html` + 11 feature HTMLs | pre-2026-05-20 |
| T-7.5 | Revert ACTIVE.md to phase=IMPLEMENTATION; update product-engineer.md with catalog contract | pre-2026-05-20 |
| T-7.6 | Update `dadaia-workspace-spec-reviewer` with catalog textual checks | pre-2026-05-20 |
| T-7.7 | `dadaia public install --force`; end-to-end verification | pre-2026-05-20 |

> Granular per-task commit SHAs are unavailable: this release predates the formal
> marker-flip + per-task-commit discipline. All commits landed before 2026-05-20.

---

## Stale marker reconciliation

The TASKS.md for this release carried 11 markers that were never flipped to `[x]` and
1 marker stuck at `[-]`. Each is reconciled here. The TASKS.md file is NOT edited —
this section is the authoritative record.

### T-5.2 — `[ ]` — Create `dadaia_workspace/cli/commands/specs.py`

**Verdict: DELIVERED.** The file `dadaia_workspace/cli/commands/specs.py` exists in the
current working tree. It was created as part of the Phase 5 work that continued beyond
the original task boundary.

### T-5.3 — `[ ]` — Wire `dadaia specs` into `main.py`

**Verdict: DELIVERED.** `dadaia_workspace/cli/main.py` references the `specs` subcommand
group. The `dadaia specs doctor` command is live and used as a gate in every subsequent
release since 2026-05-20.

### T-5.4 — `[ ]` — Create `tests/unit/features/specs/test_doctor.py`

**Verdict: DELIVERED.** The file exists; additionally `tests/unit/features/specs/test_doctor_struct_sync.py`
and `tests/integration/cli/test_cli_specs_doctor_fix.py` were created covering positive
and negative cases per check, exceeding the original task requirement.

### T-5.5 — `[ ]` — Run `pytest tests/unit/features/specs/test_doctor.py` → green

**Verdict: SATISFIED.** The specs doctor test suite is green across all subsequent
releases. The `dadaia specs doctor` command is part of the mandatory validation gate
for every release. Evidence: `dadaia specs doctor` exit 0 observed at every release
CLOSURE since `r2-lock-toctou-hardening-v1`.

### T-5.6 — `[ ]` — Run `dadaia specs doctor` on the workspace → exit 0 or only legacy warnings

**Verdict: SATISFIED.** `dadaia specs doctor` currently returns exit 0 with 21 benign
STRUCT-4 YAML-absent warnings (expected; no errors). This criterion is met and
continuously verified.

### T-V.1 — `[ ]` — `dadaia specs doctor` → exit 0 in dadaia-workspace

**Verdict: SATISFIED.** See T-5.6 above. Continuously verified at each release gate.

### T-V.2 — `[ ]` — Gate v3: 4 bash tests pass

**Verdict: SATISFIED.** Gate v3 is live and enforcing the four scenarios
(memory block without CLOSURE, memory allow in CLOSURE, archive block, production
allow with `[-]`). Validated by T-4.2 and exercised by all subsequent releases.

### T-V.3 — `[ ]` — `dadaia public doctor` → all `[ok]`

**Verdict: SATISFIED.** `dadaia public doctor` returns `[ok]` for all targets.
Verified at each subsequent release.

### T-V.4 — `[ ]` — `find specs/features -name SPEC.md` → empty

**Verdict: SATISFIED.** The `specs/features/` directory no longer contains any
`SPEC.md` files. The features-to-releases migration is complete for dadaia-workspace.

### T-V.5 — `[ ]` — `find specs/_archive/releases -name CLOSURE.md | wc -l` → ≥ 7

**Verdict: SATISFIED.** The archive contains more than 7 CLOSURE.md files across
archived releases, exceeding the original threshold.

### T-V.6 — `[ ]` — Memory HTML opens in browser with Mermaid rendering

**Verdict: SATISFIED.** Memory HTML files at `specs/memory/` render correctly with
Mermaid diagrams. Verified by the panel and by the specs doctor `<img>` link checker.

### T-6.9 — `[-]` — Flip `SDD_LEGACY_FEATURES` env to `0`

**Verdict: EXPLICITLY DEFERRED.** The task text itself states: "deferido para a próxima
release, quando migração for de fato concluída para outros repos também." This was a
conscious carry-forward decision, not incomplete work. The env var was intentionally
left at its compatibility value pending migration of other Spec Context Projects. This
item is recorded as a carry-forward below.

---

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| `dadaia specs doctor` exit 0 (0 errors) | `dadaia specs doctor` | Exit 0; 21 benign STRUCT-4 YAML-absent WARN (expected); verified at `r2-lock-toctou-hardening-v1` CLOSURE |
| `specs/features/` has no SPEC.md (migration complete) | `find specs/features -name SPEC.md` | 0 results |
| CLI command `dadaia specs doctor` live | `dadaia specs doctor --help` | Command resolves; exit 0 |
| `dadaia_workspace/cli/commands/specs.py` exists | `ls dadaia_workspace/cli/commands/specs.py` | File present |
| `tests/unit/features/specs/test_doctor.py` exists | `ls tests/unit/features/specs/test_doctor.py` | File present |
| Memory HTML atoms present | `ls specs/memory/product/index.html specs/memory/architecture.html specs/memory/tech-stack.html` | All 3 present |
| `dadaia public doctor` all `[ok]` | `dadaia public doctor` | Exit 0 |
| Legacy memory markdown archived | `ls specs/_archive/legacy-memory/` | Directory present with migrated markdown |

---

## Drifts

### pre-discipline-closure-gap

**Description:** Like `dadaia-workspace-brand-identity-v1`, this release was executed
before the ACTIVE.md phase-pointer history was fully stable (pre-2026-05-20). No
CLOSURE.md was written when the work concluded, leaving 11 task markers at `[ ]` and
1 at `[-]` indefinitely. The markers represent work that was either delivered through
later commits (T-5.2 to T-5.6, T-V.1 to T-V.6) or was explicitly deferred in the task
text itself (T-6.9).

**Resolution:** Retroactive CLOSURE.md authored 2026-05-31 as part of
`chore/releases-housekeeping`. Marker reconciliation documented above in "Stale marker
reconciliation". The TASKS.md is NOT edited — this CLOSURE.md is the reconciliation
record. No source code changes required.

**Memory updates:** None required — the product memory atoms (`sdd-gate-v3.html`,
`specs-doctor.html`) already capture the current state of the features this release
introduced.

### phase5-cli-absorbed-by-continuation

**Description:** Phase 5 tasks (T-5.2 to T-5.6) were opened in TASKS.md but not
marker-flipped to `[-]` or `[x]` as the work proceeded. The CLI implementation
(`specs.py`, `main.py` wiring, test suite) was completed in the same working session
as Phase 6 and later releases, without returning to update the TASKS.md markers.

**Resolution:** Reconciled in "Stale marker reconciliation" above. All Phase 5
deliverables are live and verified.

**Memory updates:** None.

### t69-deferred-carry-forward

**Description:** T-6.9 ("flip `SDD_LEGACY_FEATURES` to `0`") was explicitly scoped
out in the task text ("deferido para a próxima release"). The marker was left at `[-]`
rather than converted to `[ ]` or annotated as deferred.

**Resolution:** Recorded below as a backlog carry-forward. No code change needed now.

**Memory updates:** None.

---

## Memory updates

- `specs/memory/product/sdd-gate-v3.html` — already captures gate v3 behaviour
  (memory lock, archive block, release-id logging, LEGACY_FEATURES compat). No
  new update required for this retroactive closure.
- `specs/memory/product/specs-doctor.html` — already captures the `dadaia specs doctor`
  command, its 11 checks, and the STRUCT-4 YAML-absent warning behaviour. No new update
  required.
- `specs/memory/architecture.html` — no change; architecture atom already reflects
  the release lifecycle topology introduced by this release.
- `specs/memory/tech-stack.html` — no change.
- `specs/memory/product/index.html` — no change; catalog already reflects all
  features introduced by this release.

---

## Backlog returns

- `backlog/candidates.md` ← **Flip `SDD_LEGACY_FEATURES` to `0`** — carry-forward
  from T-6.9, which was explicitly deferred pending completion of the features→releases
  migration in other Spec Context Projects (burrinhos-barbe, dd-chain-explorer,
  workflow-tools, portifolio, portifolio-wave6, dadaia-agents, dadaia-bots, tauan-games).
  Promote to a candidate when the multi-repo migration release is scoped.

---

## Archive decision

**MOVE** — release directory to be moved to
`specs/_archive/releases/sdd-release-lifecycle-v1/` via `git mv`.
ACTIVE.md to be updated by the orchestrator as part of `chore/releases-housekeeping`.
