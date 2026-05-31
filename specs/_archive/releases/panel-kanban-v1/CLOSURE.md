# Closure: Release — panel-kanban-v1

> **Status:** Aprovado
> **Release ID:** panel-kanban-v1
> **Owner:** product-engineer
> **Closed:** 2026-05-31

## Summary

This release delivers the Kanban tab on the Dadaia Workspace Panel, a read-only swimlane
board that surfaces the current multi-agent state at a glance. The board organises active
sessions into one swimlane per Spec Context Project and four phase columns (Research,
Definition, Implementation, Review), drawing exclusively from the R2 session files at
`.dadaia/sessions/*.json`. Cards move autonomously as session modes change — no manual
drag, no action buttons in v1. The Implementation ↔ Review mutual-exclusion visual (XOR
lock dim + lock badge) gives the operator an immediate read on which contexts are in a
locked phase. Empty states at the column, lane, and board level are fully handled.

The release also hardens the handoff contract: the `verdict` field (`APPROVED` | `REJECTED`)
and `verdict_reason` were added to the handoff-v1.1 schema as optional, backward-compatible
fields. This enables the dual-approval gate (qa-engineer AND security-reviewer) to be
machine-checked at release CLOSURE via `jq '.verdict'` on each handoff sidecar. The CI
YAML gained a `verdict-gate` job that asserts both verdicts equal `APPROVED` on
`workflow_dispatch` CLOSURE runs, with a no-op on normal PR/push (sidecars are
gitignored/ephemeral and absent in CI checkout — by design, documented in the CI comments).

Pytest passed 2458 tests with 88.87% coverage (gate: ≥ 80%). All six Playwright board
scenarios (PW-KAN-01..05 plus the `verdict`-sidecar AC-4.3 end-to-end) ran on real
Chromium and passed. `dadaia specs doctor` and `dadaia public doctor` both exit 0.

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| K-1 | `/api/kanban` GET endpoint + `views/kanban.py` view: session-file glob, mode→column map, `is_stale` recomputed at read, missing/empty dir → 200, POST → 405, bearer + loopback auth; 18 tests (AC-1.1..1.14) | commits around 3537bba / 520bf16 area on release/panel-kanban-v1 |
| K-3 | Handoff-v1.1 schema: optional `verdict` (APPROVED/REJECTED) + `verdict_reason`; backward-compatible; schema tests AC-4.1..4.3; `dadaia public doctor` exit 0 after propagation | release/panel-kanban-v1 |
| K-2 | Kanban frontend: `assets/css/kanban.py` (KANBAN_CSS) + `assets/js/kanban.js`; swimlane × 4-column board; Impl ↔ Review XOR lock visual; empty states; WCAG AA + ARIA; `prefers-reduced-motion`; tab wired via `static.py/_ASSETS` + `index.py` + `core.js`; Playwright PW-KAN-01..05 | release/panel-kanban-v1 |
| K-QA-RACE | Impl-XOR-Review lock-conflict tests AC-3.1..3.6 + barrier-based race tests AC-3.7..3.8; real `JsonContextStore` on `tmp_path`; no `time.sleep`; all threads joined timeout=5 | release/panel-kanban-v1 |
| K-QA-PW | Playwright sign-off: PW-KAN-01..05 ran on real Chromium, 6/6 passed; screenshots in `.dadaia/tmp/qa-engineer/panel-kanban-v1/`; QA handoff sidecar emitted with `verdict: "APPROVED"` | release/panel-kanban-v1 |
| K-CI | `ci.yml` `verdict-gate` job + `scripts/check-verdict.sh`; no-op on push/PR; asserts qa + security `verdict == APPROVED` on `workflow_dispatch` CLOSURE | release/panel-kanban-v1 |

---

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| ruff clean | `ruff check .` | Exit 0; 0 errors (161 source files) |
| mypy --strict clean | `mypy --strict dadaia_workspace` | Exit 0; 0 errors (161 source files) |
| pytest suite green | `poetry run pytest` | 2458 passed, 0 failed, 1 skipped, 1 xpassed; 88.87% coverage (≥ 80% gate met) |
| specs doctor exit 0 | `dadaia specs doctor` | Exit 0; expected benign STRUCT-4 YAML-absent WARNs carried from memory-structured-source-v1 deferred migration — NOT a regression |
| public doctor exit 0 | `dadaia public doctor` | Exit 0; handoff-v1.1 schema with `verdict` propagated |
| Playwright board scenarios | `pytest -m playwright` (PW-KAN-01..05 on real Chromium) | 6/6 passed; screenshots in `.dadaia/tmp/qa-engineer/panel-kanban-v1/` (6 PNGs) |
| QA handoff verdict APPROVED | `jq '.verdict' <qa-handoff.json>` | `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-31T175040Z-panel-kanban-v1-qa.handoff.json`; `dadaia reports validate` exit 0 |

---

## Drifts

### asset-layout-drift

**Description:** SPEC §3 K-2 named the frontend CSS and tokens files as `kanban.css` and
`tokens.py` (literal filenames), but the panel repository actually serves CSS as Python
module string constants via `static.py` `_ASSETS` dict, with constants named `KANBAN_CSS`
rather than a raw `.css` file. The design tokens also live in `assets/css/tokens.py` as a
Python module, not as a standalone file. This is the established panel pattern (not a
new invention by this release).

**Resolution:** Implementation correctly followed the real repo pattern (`KANBAN_CSS`
constant in a Python module, registered in `_ASSETS`). No scope change was introduced;
the functional contract from the SPEC (swimlane board, XOR lock visual, WCAG AA compliance)
was fully delivered. The SPEC's file-name references were illustrative rather than
prescriptive for this layer.

**Memory updates:** No memory update required for this drift — the panel's CSS-as-Python-module
pattern was already documented in `architecture.html` and `panel.html`. The Kanban tab
entry simply follows the same pattern.

### k1-touched-container-py

**Description:** SPEC §3 K-1 listed only `handler.py` and `views/kanban.py` as affected
files, but the implementation also required touching `container.py` to wire the new
`api_kanban` view callable into `build_panel_views()`. This is analogous to how
`api_contexts`, `api_agents`, and other views are wired — every new view callable
requires a corresponding entry in the composition root.

**Resolution:** Scope expansion was benign and necessary. The `container.py` change is
fully disjoint from all other release tasks. No contract was violated. Documented here
for traceability.

**Memory updates:** `specs/memory/architecture.html` was updated to reflect the new
`views/kanban.py` view in the panel layer's view composition description and the
`build_panel_views()` composition root note.

### r2-lock-defects-surfaced

**Description:** The K-QA-RACE tests (AC-3.1..3.8) were written against the real
`JsonContextStore` lock layer (R2, `spec-context-session-locks-v1`). This testing exposed
three pre-existing defects in R2's locking implementation that were NOT introduced by this
release (R3 only reads session files for display, it does not modify the lock layer):

1. A STALE impl lock does NOT block a review bind — only a HELD lock does. The XOR check
   in `check_impl_xor_review` reads lock state, but STALE does not produce
   `ReviewBlockedByImplementationError`.
2. `check_impl_xor_review` is a check-then-act with a TOCTOU window: a concurrent
   impl + review race can allow BOTH to succeed if both threads pass the check before
   either acquires.
3. `create_impl_lock` uses a shared `.tmp` filename for atomic rename, so the losing
   thread in a same-release impl race raises `FileNotFoundError` rather than
   `LockHeldError`.

The K-QA-RACE tests assert the REAL observed behaviour and document these defects with
inline comments. They are passing tests that accurately describe the current (imperfect)
lock semantics, not tests that assert ideal semantics.

**Resolution:** These defects are in R2's domain and out of scope for R3. They are
documented here and a dedicated backlog candidate has been filed:
`specs/backlog/r2-lock-toctou-hardening-v1.md`. The three defects are named, the
affected functions are identified (`locking.py:check_impl_xor_review` and
`create_impl_lock`), and a remediation approach (workspace-flock wrapping of the XOR
check-then-act + per-thread tmp names) is proposed.

**Memory updates:** None required — these are pre-existing R2 defects. R3 memory atoms
describe the Kanban feature and the handoff schema extension; the lock layer semantics
are R2's domain.

### k-ci-verdict-gate-no-op-design

**Description:** The `verdict-gate` CI job is a no-op on normal PR/push runs. Handoff
sidecars are gitignored and ephemeral — they are absent in CI checkout. This means the
`check-verdict.sh` script cannot find them on a standard push/PR run and exits 0 (no-op).
The gate only fires on `workflow_dispatch` with explicit CLOSURE inputs.

**Resolution:** This is by design, matching the SPEC's intent (§9 "Dual-approval CI
integration"). The CI YAML comments document the no-op behaviour explicitly. No scope
change.

**Memory updates:** None required.

---

## Memory updates

- `specs/memory/architecture.html` — added `views/kanban.py` to the panel layer's view composition notes; noted it as a read-only board view that reads `.dadaia/sessions/*.json` without touching `TelemetryDao`.
- `specs/memory/product/panel.html` — added Kanban tab (read-only swimlane board over session files; Impl ↔ Review XOR lock visual; v1 = no drag/actions) to the feature description and flow steps; noted `verdict` field in handoff-v1.1 + CI dual-approval gate.
- `specs/memory/product/index.html` — updated panel feature entry in the catalog `<span class="desc">` to mention the new Kanban tab; bumped meta date to 2026-05-31 and closure to panel-kanban-v1.
- `specs/memory/tech-stack.html` — no change: this release introduced no new PyPI dependencies. All implementation uses Python stdlib (backend) + vanilla JS/CSS (frontend), consistent with the existing panel stack.

---

## Backlog returns

- `specs/backlog/candidates.md` ← `r2-lock-toctou-hardening-v1` — three pre-existing defects in `spec-context-session-locks-v1` locking layer surfaced by K-QA-RACE: (a) STALE impl lock does not block review bind, (b) `check_impl_xor_review` TOCTOU race window, (c) `create_impl_lock` shared `.tmp` name raises `FileNotFoundError` instead of `LockHeldError` on same-release race. Proposal: workspace-flock wrapping of XOR check-then-act + per-thread `.tmp` names in `dadaia_workspace/features/spec_context/locking.py`. (owner: software-engineer-python)
- `specs/backlog/r2-lock-toctou-hardening-v1.md` ← detailed candidate file with defect descriptions and remediation proposal (created in this CLOSURE phase).

---

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/panel-kanban-v1/`
via `git mv`. ACTIVE.md will be updated to point to the next release or `release: none`.
