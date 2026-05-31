# PLAN — panel-kanban-v1

**Status:** Aprovado
**Release ID:** panel-kanban-v1
**Owner:** product-engineer
**Opened:** 2026-05-30

---

## Activation gate (hard — no exceptions)

Implementation must NOT begin until ALL of the following are true:

1. `spec-context-session-locks-v1` (R2) ACTIVE.md phase = `ARCHIVED`
   — The Kanban backend reads `.dadaia/sessions/*.json`. These files only exist after R2
   ships. No code may be merged before R2 closes.
2. `panel-ux-fix-v1` task T-PUX-06 (loopback auth bypass) is merged.
   — The `/api/kanban` endpoint's auth behaviour on loopback binds depends on it.
3. SPEC.md and this PLAN.md both have `**Status:** Aprovado`.

SPEC and PLAN authoring are unblocked now. TASKS.md may also be authored now.

---

## 1. Strategy

The release delivers three disjoint units of work that can be parallelised after R2 closes:

- **K-1 (backend):** A new Python view `kanban.py` reads `.dadaia/sessions/*.json`, maps
  session modes to Kanban columns, and serves the JSON response. The handler gains the
  `/api/kanban` route and a new Kanban HTML tab route.
- **K-2 (frontend):** A new JS + CSS pair renders the Kanban board in the panel. The nav
  is extended with a Kanban tab. All design tokens are added to `tokens.py`.
- **K-3 (schema):** The `handoff-v1.schema.json` gains an optional `verdict` field (additive,
  non-breaking). This task is fully disjoint from K-1 and K-2 and can proceed in parallel
  once R2 closes.

K-2 depends on the K-1 `/api/kanban` response contract being stable but NOT on K-1 being
merged — the frontend-engineer can work against the documented schema from the SPEC. K-1
must be merged before the Playwright E2E suite (K-QA-PW) runs.

---

## 2. Layers affected

| Layer | File(s) | Owner |
|-------|---------|-------|
| Backend view | `dadaia_workspace/features/panel/views/kanban.py` (new) | software-engineer-python |
| Backend handler | `dadaia_workspace/features/panel/handler.py` | software-engineer-python |
| Frontend tab nav | `dadaia_workspace/features/panel/views/index.py` | frontend-engineer |
| Frontend JS | `dadaia_workspace/features/panel/views/assets/js/kanban.js` (new) | frontend-engineer |
| Frontend CSS | `dadaia_workspace/features/panel/views/assets/css/kanban.css` (new) | frontend-engineer |
| Design tokens | `dadaia_workspace/features/panel/views/tokens.py` (existing — add tokens) | frontend-engineer |
| Handoff schema | `dadaia_workspace/public/schemas/handoff-v1.schema.json` | software-engineer-python |
| Contract tests | `tests/` (new test file for kanban endpoint + verdict schema) | software-engineer-python |
| Lock-conflict tests | `tests/` (race tests for Impl-XOR-Review) | software-engineer-python |
| E2E Playwright | `tests/` or qa-engineer test directory | qa-engineer |
| CI gate | `.github/workflows/*.yml` | devops-engineer |

---

## 3. Execution waves

### Wave 0 — Gate satisfied (pre-implementation, unblocked now)

- PLAN and TASKS authored and approved (product-engineer).
- `spec-context-session-locks-v1` (R2) reaches ARCHIVED phase.
- `panel-ux-fix-v1` T-PUX-06 merged.
- No code written in this wave.

### Wave 1 — Backend + schema (parallel, after Wave 0)

Tasks K-1 and K-3 are independent write sets and can run in parallel.

**K-1 (software-engineer-python):**
- Implement `kanban.py` view: glob `.dadaia/sessions/*.json`; parse each file; skip
  malformed files; compute `is_stale` from `last_seen_at` vs `ttl_seconds`; group cards
  by context; map modes to columns using the SPEC §3 K-1 map table (unknown → research,
  not dropped); handle missing/empty sessions dir gracefully (200 with empty swimlanes).
- Update `handler.py`: add `(r"^/api/kanban$", "api_kanban")` to `_RAW_ROUTES`; add
  `api_kanban` to `_BEARER_AUTH_ROUTE_NAMES` / `_BEARER_ONLY_ROUTES`; add POST → 405;
  add HTML tab route for the Kanban page.
- Write unit + integration tests covering AC-1.1 through AC-1.14.

**K-3 (software-engineer-python):**
- Add optional `verdict: "APPROVED" | "REJECTED"` and optional `verdict_reason: string`
  to `dadaia_workspace/public/schemas/handoff-v1.schema.json`.
- Verify existing sidecars without `verdict` still validate (field is optional).
- Write schema tests covering AC-4.1 through AC-4.3.
- Run `dadaia public stage && dadaia public install --target all` after schema edit
  (lib-originated asset — must be propagated). This is a devops-engineer action; SE-Python
  flags it on task completion.

### Wave 2 — Frontend (after K-1 API contract is stable)

**K-2 (frontend-engineer):**
- Add Kanban design tokens to `tokens.py` per SPEC §3 K-2 token list.
- Create `kanban.css`: swimlane × 4-column grid; horizontal scroll below 800px; card
  anatomy (font-mono session ID, status dot, model, runtime+age); locked column styling
  (opacity 0.40, `kanban-column--locked` class, `data-locked="true"`); empty state
  placeholder; card appear animation (opacity 0→1, suppressed under
  `prefers-reduced-motion`); WCAG AA compliance per SPEC §3 K-2 audit notes.
- Create `kanban.js`: fetch `/api/kanban`; render swimlanes and cards; implement XOR lock
  visual (Implementation ↔ Review mutual-exclusion dim + lock badge); poll for updates;
  all ARIA roles per SPEC §3 K-2 (card `role="article"`, `tabindex="0"`, lane
  `aria-labelledby`, column `role="group"` with `aria-labelledby`).
- Update `index.py`: add `#tab-kanban` to nav and tab panel sections.
- Write Playwright tests PW-KAN-01 through PW-KAN-05 (AC-2.1 through AC-2.5).

### Wave 3 — Race / lock-conflict tests (after Wave 1)

**K-QA-RACE (software-engineer-python):**
- Write Impl-XOR-Review lock-conflict and race tests AC-3.1 through AC-3.8 using
  `threading.Barrier(2)` (no `time.sleep`; real `JsonContextStore` on `tmp_path`).
- These tests exercise the R2 lock layer; they depend on R2 being ARCHIVED (Wave 0).
- CI grep gate: `grep -rn "time\.sleep" tests/ | grep -v "# allowed-sleep"` must exit
  non-zero (no unapproved sleeps).

### Wave 4 — CI dual-approval gate (after K-3 merged)

**K-CI (devops-engineer):**
- Wire the `jq '.verdict'` checks for qa-engineer and security-reviewer handoff sidecars
  into the CI YAML. Gate: if either sidecar is missing or `verdict != "APPROVED"`,
  the release CLOSURE check fails.
- Verify `dadaia public doctor` exits 0 after K-3 schema propagation.

### Wave 5 — QA sign-off

**K-QA (qa-engineer):**
- Review and ratify all test results.
- Playwright board scenarios: PW-KAN-01..05 (AC-2.1..2.5).
- Confirm coverage and no `time.sleep` in race tests.
- Emit green QA handoff sidecar (with `verdict: "APPROVED"` per handoff-v1.1).

---

## 4. Technical risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| R2 closes later than expected, delaying Wave 1 | Medium | High | PLAN + TASKS are authored now; implementation starts immediately when R2 is ARCHIVED |
| `panel-ux-fix-v1` T-PUX-06 not yet merged when Wave 1 starts | Low | Medium | K-1 backend tests can mock loopback bypass; T-PUX-06 is a precondition for integration tests only |
| Session file schema from R2 differs from what K-1 expects | Low | High | K-1 must import or mirror the R2 session schema constants; cross-check at Wave 1 start |
| WCAG AA audit finds contrast failures in kanban.css tokens | Low | Medium | Ratios are pre-computed in SPEC §3 K-2 audit table; tokens are prescribed; risk is transcription error only |
| OpenCode post-tool hook gap (carried from R2 OQ-3) | Low | Low | K-3 does not use post-tool hooks; R2 resolves OQ-3 before K-1/K-2 start |

---

## 5. Validation plan

| What | How | Evidence |
|------|-----|---------|
| `/api/kanban` endpoint contract | `pytest tests/test_kanban_*.py` (AC-1.1..1.14) | Green pytest output |
| Playwright board scenarios | `pytest -m playwright` (PW-KAN-01..05) | Screenshots in `.dadaia/tmp/qa-engineer/panel-kanban-v1/` |
| Impl-XOR-Review lock conflict tests | `pytest tests/test_kanban_lock_*.py` (AC-3.1..3.8) | Green pytest output |
| No `time.sleep` in race tests | `grep -rn "time\.sleep" tests/ \| grep -v "# allowed-sleep"` | Exit non-zero |
| Handoff schema accepts `verdict` | `pytest tests/test_handoff_schema.py` (AC-4.1..4.3) | Green pytest output |
| `dadaia public doctor` clean after K-3 | `dadaia public doctor` | Exit 0 |
| WCAG AA compliance | Design-specialist or frontend-engineer manual audit + Playwright axe scan | axe report or manual checklist |

---

## 6. Memory files to update at CLOSURE

Per SPEC §7:

- `specs/memory/product/index.html` — add Kanban tab entry to panel feature in catalog.
- `specs/memory/product/<panel-slug>.html` — update panel feature page to include Kanban
  tab description and handoff-v1.1 `verdict` field.
- `specs/memory/architecture.html` — note new `views/kanban.py` in panel layer.
- `specs/memory/tech-stack.html` — no change expected (no new PyPI dependencies).

---

## 7. Out of scope (explicit)

Per SPEC §9: unbind/session-termination, per-card click/detail drawer, drag/manual
reorder, cost tracking on the board, mobile stacked layout, SPEC-mode session file
creation, dual-approval CI YAML (that is devops-engineer task K-CI listed in Wave 4).

---

*Product Engineer — dadaia-workspace | 2026-05-30*
