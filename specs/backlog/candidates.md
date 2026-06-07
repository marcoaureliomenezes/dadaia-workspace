# Backlog candidates

Surfaced issues awaiting triage into a release. Newest first.

---

## FEAT-CODEX-COMPAT-100 — Full Codex Compatibility (CRITICAL)

**Reported:** 2026-06-07 (operator directive after Codex operability audit).

**Surface:** Codex runtime projection and compatibility across agents, hooks, skills,
rules, workflows, AGENTS.md, public doctor, and tests.

**Core defect:** dadaia-workspace has real Codex projection files, but they are not yet
100% first-class Codex-compatible. The audit found a critical generated-agent corruption
(`ai-harness-claude-code` → fake `ai-harness-gpt-5.3-codex`), Markdown protocol docs
projected under a path that looks like executable Codex Rules, stale Claude path references
inside generated Codex personas, stale subagent/orchestration memory, and no live Codex hook
smoke test.

**Full source:** `specs/backlog/full-codex-compatibility.md`.

**Evidence:** `.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-07T152643Z-codex-operability-audit.html`
and `.dadaia/handoff/dadaia-workspace/2026-06-07T152643Z-ai-engineer-codex-operability-audit.handoff.json`.

**Status:** OPEN — should become a dedicated release after PM/product-engineer grill and
SPEC/PLAN/TASKS approval.

---

## Priority index (2026-06-06 — consolidated)

| # | Item | State |
|---|---|---|
| **1** | **FEAT-AGENTIC-LIFECYCLE-V020-01** — v0.2.0 "Agentic Development Lifecycle", four phases **P1→P2→P3→P4** (`v0.2.0-agentic-lifecycle.md`) | **PICKED — single active initiative.** P1 state model → P2 constitution v2/law (the freeze) → P3 agent roster 15→9 → P4 surface cleanup. Architect: GO-WITH-CHANGES (2 criticals resolved). |
| — | ↳ folds in: `sdd-state-model-redesign.md` (→ **P1**), `dadaia-agent-specialization.md` R3 (→ **P3**) / R4 (→ **P4**), `session-orchestration-semaphore.md` (intent → §1/§2), `agent-skill-surface-slop` bug (→ P3/P4) | absorbed, annotated, not deleted |
| **Track 0** | **v0.1.5 ship** — independent good work, **minus the semaphore** (RULE E disabled via `SDD_RULE_E_DISABLED=1`) | **Ships FIRST, separate.** PR #38 (`feature/0.1.5`) OPEN/green/mergeable, NOT merged. Delivers backlog-ownership D5, T-PROP install/doctor fixes, panel fixes, persona specializations, semaphore-liveness. v0.2.0 P1 then builds the TTL-lease FRESH from this semaphore-free base. |

**Ship order:** Track 0 (v0.1.5-minus-semaphore) ships once -> v0.2.0 P1 -> P2 -> P3 -> P4 (one
`feature/0.2.0` branch, one tag; per `release-governance` alpha-N/rc-N maturity).

**Design of record:** roadmap `2026-06-06T045436Z-consolidated-roadmap.md` + architect validation
`2026-06-06T060000Z-roadmap-validation.md`. The pick/contract is `v0.2.0-agentic-lifecycle.md`.

---

## Bug C (deferred from v0.1.4.5): `dadaia context heartbeat` does not renew session file

**Reported:** 2026-06-04 (SPEC v0.1.4.5 §3 Bug C deferred note).

**Surface:** `dadaia context heartbeat` CLI command + `sdd-spec-gate.sh` RULE E session
staleness check.

**Defect:** `dadaia context heartbeat` renews the implementation lock (`last_seen_at`)
but NOT the session file. RULE E checks session file staleness (`last_seen_at + TTL`),
so the documented idle keep-alive cannot keep a long session alive on its own. Mitigated
for active work by the gate's inline heartbeat (SCOPE-02, v0.1.4.5: renews both session
file and lock on every allowed write).

**Full fix:** make every renewal point renew both session file and lock, or unify on a
single liveness record.

**Adopted:** v0.1.5/rc-1 (2026-06-05) — folded into R1, tracked as T-R1-03. Reference to `r2-lock-toctou-hardening-v1` retired (phantom backlog — no file existed). **Note (2026-06-06):** the single-liveness-record fix is now v0.2.0 P1 (the TTL-lease unifies session+lock liveness).

---

## Multi-lock edge case in env-free lock adoption (deferred from v0.1.4.5)

**Reported:** 2026-06-04 (code-reviewer INFO finding in
`.dadaia/handoff/dadaia-workspace/2026-06-04T225316Z-code-reviewer-v0.1.4.5-gate-fix.handoff.json`).

**Surface:** `dadaia_workspace/public/scripts/sdd-spec-gate.sh` RULE E env-free fallback.

**Defect:** The glob `${CONTEXT_SLUG}__*.json` matches any release-lock for the context.
In a multi-lock scenario (abandoned + active non-stale locks for different releases of the
same context), the loop adopts the first match by filesystem-traversal order (non-deterministic).

**Suggested fix:** Narrow glob to `${CONTEXT_SLUG}__${ACTIVE_RELEASE}.json` (exact match
on active release).

**Adopted:** v0.1.5/rc-1 (2026-06-05) — folded into R1, tracked as T-R1-04. **Note (2026-06-06):** moot under v0.2.0 P1 (single lease record per context — no per-release lock glob).

---

## CONTEXT_SLUG not sanitized before lock glob (deferred from v0.1.4.5)

**Reported:** 2026-06-04 (security-reviewer LOW finding, CWE-22, pre-existing, in
`.dadaia/handoff/dadaia-workspace/2026-06-04T225204Z-security-reviewer-v0.1.4.5-gate-fix.handoff.json`).

**Surface:** `dadaia_workspace/public/scripts/sdd-spec-gate.sh` RULE E lock directory glob.

**Defect:** `CONTEXT_SLUG` derived from `DADAIA_CONTEXT` env var, `spec_contexts.json`, or
session file is not sanitized before use in `.dadaia/locks/implementation/${CONTEXT_SLUG}__*.json`
path construction. All sources are operator-controlled workspace state (not network input);
LOW severity. Pre-existing across the gate.

**Suggested fix:** Strip non-alphanumeric except `-_` from `CONTEXT_SLUG` before use in path
construction.

**Adopted:** v0.1.5/rc-1 (2026-06-05) — folded into R1, tracked as T-R1-04. **Note (2026-06-06):** carries into v0.2.0 P1 — apply `[A-Za-z0-9_-]` allowlist at the Python path-construction site for both `context` and `session_id`.

---

## ai-harness-opencode skill (deferred from v0.1.4.6)

ai-harness-opencode skill — compiled mental model + decision protocols for opencode runtime
(deferred from v0.1.4.6 pending opencode runtime stability).

---

## FEAT-DADAIA-AGENTS-01 — dadaia-agent specialization + backlog/release/review process enforcement (HIGH)

**Reported:** 2026-06-04 (operator directive + PM-owned grill session).

**Surface:** AI-entity surface only (personas, skills, rules). Agents: `product-engineer`,
`project-manager`, `project-auditor` specialization; `ai-engineer` leads the design.
Plus: process-flow rules encoding (backlog ownership, release-definition flow, review gate).
R4 audit of the remaining generic agents follows after R3 is CLOSED.

**Full source:** `specs/backlog/dadaia-agent-specialization.md`.

**Consolidated (2026-06-06):** R3 → **v0.2.0 P3** (roster 15→9), R4 → **v0.2.0 P4** (surface
cleanup). Persona-specialization slice already shipped into v0.1.5/rc-1 (Track 0). See
`v0.2.0-agentic-lifecycle.md`.

---

## FEAT-SESSION-SEMAPHORE-01 — Per-context implement+review semaphore + automated phase binding (CRITICAL / deploy-blocker)

**Reported:** 2026-06-04 (operator: "we change every time how the session is bound… is
very bad… we must not stop the flow… project-manager owns the complete workflow as a
maestro/coordinator… a semaphore [to] disable any other session to implement + review if
we already have a session implementing/reviewing some work, per spec context… The way it
is now, we cannot even deploy it as it breaks the workflow totally").

**Surface:** SDD gate (`sdd-spec-gate.sh` RULE E), session model, `dadaia context bind`,
project-manager orchestration.

**Core defect:** production writes are gated on a `DADAIA_SESSION_ID` env var that the
runtime cannot self-inject and that changes per phase, forcing a relaunch to advance
phases. Intended design is the opposite: a **per-spec-context semaphore** (single
implement+review holder, coordinated by project-manager) with **automated, env-free phase
binding** so the flow never stops. Reproduced today on release v0.1.4.6 — bind created a
valid session on disk, runtime env stayed empty, gate failed closed, only escape was
relaunch.

**Full source + design direction + acceptance:** `specs/backlog/session-orchestration-semaphore.md`.

**Consolidated (2026-06-06):** mechanism SUPERSEDED. Intent absorbed into the v0.2.0 roadmap
§1/§2 (one TTL-lease serializes MUTATING; ADDITIVE always parallel). Built FRESH in v0.2.0 P1
from a semaphore-free base (Track 0 disables RULE E). Not deleted — retained for intent + evidence.

Cross-refs: `r2-lock-toctou-hardening-v1` (3 reproduced lock races), dev/test/review audit
2026-06-04 (gate fail-open, Kanban blind to locks), Spec Context v2 + session-locks memory.

---

## BUG-PANEL-REPORTS-01 — Reports tab is a mess + active regression (HIGH)

**Resolved:** resolved_in: v0.1.5/rc-2, verified by T-PANEL-01 (qa-engineer, 2026-06-05), commit `028ffd5` ("fix(panel): index reports from artifacts and handoffs"). RC#1-RC#4 confirmed fixed. Residual: time-sensitive test repair + RPT-1 invariant in T-PANEL-02.

**Reported:** 2026-06-04 (operator-confirmed: "the reports on the panel are a total mess", "I did not see any report from 2026-06-04", "It's backlog to fix this tab. very ugly, a big mess").

**Surface:** Panel → Reports tab. Endpoint `GET /api/reports` → `render_api_reports` in
`dadaia_workspace/features/panel/views/api.py:836`.

### Symptoms the user sees
- Reports list is cluttered and ugly: titles show a double extension (e.g. `2026-06-04T021947Z-T-HARD-04.handoff`), entries with 0/0/0/0 findings, and rows that link to non-report files.
- Today's HTML reports do not appear at all.
- Mix of `.handoff.json`, `.html`, `.md` with no de-duplication and no clear "this is the human-readable report" affordance.

### Root causes (each independently a defect)
1. **Discovery is 100% sidecar-driven.** The list is built by globbing `*.handoff.json` and reading `artifact.path`; an HTML/MD report with **no** sidecar is invisible. Today ~half the historical corpus has no adjacent sidecar, and any sidecar-less HTML (e.g. the 2026-06-04 review report) never shows. *(api.py:862-878)*
2. **Self-referential / garbage `artifact.path`.** Many sidecars are "sidecar-only" handoffs whose `artifact.path` points at the `.handoff.json` itself (`content_hash: "sidecar-only"`), or at a **source file** (observed: `dadaia_workspace/public/scripts/sdd-spec-gate.sh`). Result: ugly `.handoff` titles and links that 404/403 because `serve_report_file` only serves under `.dadaia/reports/`. *(api.py:866-868, 888-892, 908-919)*
3. **Active regression — sidecar location drift (T-HANDOFF-04, commit `6f7e70f`, 2026-06-04 02:53).** The list was repointed from `.dadaia/reports/` → **`.dadaia/handoff/`** (api.py:859), but only **1 of 225** sidecars actually live in `.dadaia/handoff/`; the other 224 remain adjacent under `.dadaia/reports/<ctx>/<agent>/` (per workspace-protocol §4 "sidecar, adjacent") and the dadaia-handoff-emitter skill. **OBSERVED 2026-06-04: the panel was restarted and the Reports tab collapsed from 224 → 2** (only the two sidecars that happen to live in `.dadaia/handoff/`). Regression confirmed live, not theoretical. The code (`.dadaia/handoff/`) and the data + protocol + emitter skill (`.dadaia/reports/.../adjacent`) disagree.
4. **No de-duplication.** An HTML report + its sidecar + a `.md` variant are listed as separate rows.
5. **Boot-time coupling (shared with sessions/kanban).** Panel assets are read once at import; report-list behaviour changes require a process restart, which is how this regression stays hidden.

### Suggested fix direction (for the eventual release)
- Decide ONE canonical sidecar location and migrate; make `dadaia-handoff-emitter`, workspace-protocol §4, and `render_api_reports` agree. (Recommend keeping sidecars **adjacent** under `.dadaia/reports/` — that's where 224 of 225 already are and where `serve_report_file` resolves — and reverting the T-HANDOFF-04 path change, or add a migration that moves all sidecars to `.dadaia/handoff/`.)
- Discover reports by the **rendered artifacts** (`*.html`, `*.md`) and enrich with the sidecar when present, instead of being sidecar-driven. A report with no sidecar should still list (findings_summary empty), so nothing is invisible.
- Skip/repair self-referential `artifact.path` (never point a report row at a `.handoff.json` or a source file); derive the display title from the artifact filename minus the report extension (no `.handoff`).
- De-dup html/sidecar/md into one row per report; show a findings badge only when a sidecar exists.
- Add a `dadaia reports doctor` (or extend the existing doctor) invariant: every report has at most one sidecar in the canonical location, no dangling `artifact.path`.
- Consider request-time asset/report serving (ETag) so the tab reflects disk without a restart.

### Evidence
- Live `GET /api/reports`: 224 rows from `.dadaia/reports/`; one row title `sdd-spec-gate` → path `dadaia_workspace/public/scripts/sdd-spec-gate.sh` (a source file).
- `.dadaia/handoff/` contains 1 sidecar; `.dadaia/reports/**` contains 225.
- Full system review (incl. this surface, score 6.0/10 for panel visibility):
  `.dadaia/reports/dadaia-workspace/architecture-review/2026-06-04T154728Z-dev-test-review.html`.

**Workaround applied 2026-06-04:** emitted a proper sidecar for the review report in both
`.dadaia/reports/.../architecture-review/` and `.dadaia/handoff/dadaia-workspace/` so it is visible
in both the running panel and post-restart HEAD code. This does not fix the underlying tab.
