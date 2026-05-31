# CLOSURE — workspace-hardening-v1

**Status:** Fechado
**Closed at:** 2026-05-28T13:21:35Z
**Commit:** cd1f814

---

## What shipped

### Phase A — Panel Auth Fix
- `core.js`: `sessionStorage` → `localStorage` for `panel_token`. Token now survives tab close/reopen; users no longer see "Authentication required" when reopening `localhost:4999` directly.

### Phase B — Agent Boundary Hardening + D-CX-SKILLS
- Removed orphaned skill references from **code-reviewer**, **security-reviewer**, **project-auditor** bodies. Replaced with "Built-in methodology" sections so intent is clear without implying invocable skills.
- Tightened dispatch conditions for **design-specialist**, **project-manager** (Node vs frontend routing table), **product-engineer** (Read tool vs shell clarification), **researcher** (web-only vs codebase dispatch guidance).
- **D-CX-SKILLS validator** added to `dadaia public doctor`: emits `[drift]` when any agent's frontmatter `skills:` list references a directory that doesn't exist in `public/skills/`; emits `[warn]` for best-effort body-text matches. Root cause guard — prevents the 3-step failure chain from recurring silently.

### Phase C — CLI Asset Granularity
- `dadaia public list [--format table|json]` — lists all asset categories and names.
- `dadaia public install --only <type>` — installs a single asset category instead of all.

### Phase D — Panel Workflow Dispatcher
- POST `/api/workflows/<name>/run` — Bearer-authed, name-guarded (`^[a-zA-Z0-9\-]+$`).
- `PanelService.run_workflow()` — spawns `dadaia orchestrate <name>` via `Popen`; tracks running PIDs; 409 guard via `os.kill`.
- "Run" button per workflow card — spinner → "Started (PID: X)" / "Already running" / "Failed" badges.

---

## Validation

- `dadaia public doctor` → exit 0, no `[drift]`, D-CX-SKILLS passes.
- `pytest` → 1711 passed, coverage 86.07%.

---

## Root cause closed

The 3-step failure chain (specs promised skills → big-bang removed them without updating body text → no validator caught it) is now structurally prevented by D-CX-SKILLS. Future `dadaia public doctor` runs will catch any recurrence immediately.
