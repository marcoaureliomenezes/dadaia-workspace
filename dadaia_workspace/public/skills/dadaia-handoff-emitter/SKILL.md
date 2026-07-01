---
name: dadaia-handoff-emitter
description: >
  Emit a machine-readable handoff JSON under .dadaia/handoff/<context>/ at the end of
  any agent task. Handoff-first: the default emission carries no HTML report — emit the
  handoff alone. Only when an HTML report exists (operator asked, or the next handoff
  target is human) does the handoff also carry artifact.path + content_hash. Conforms to
  .dadaia/agentic/schemas/handoff-v1.schema.json; validated via `dadaia reports validate`.
applyTo: ".dadaia/handoff/**/*.handoff.json"
---

# dadaia-handoff-emitter

## Purpose

Every completed agent task ends with a structured JSON handoff under
`.dadaia/handoff/<context>/` so downstream agents, the panel, and
`dadaia reports validate` can consume the result as a machine contract.

Emission is **handoff-first** (`workspace-protocol` rule §4):

| Mode | When | What the handoff carries |
|---|---|---|
| Handoff-only (default) | Normal agent-to-agent flow | No `artifact.path`, no `content_hash` — findings, metrics, scope, verdict |
| Handoff + HTML report | Operator explicitly requested a report, OR `next_handoff.agent == "human"` | `artifact.path` to the HTML report + its `content_hash` |

The handoff schema lives at:

```
.dadaia/agentic/schemas/handoff-v1.schema.json
```

Do **not** reproduce the schema content here — always reference it by that path.
The schema requires only `artifact.type` inside `artifact`; `path` and `content_hash`
are the report-mode pair. **Whenever `artifact.path` is present, `content_hash` must be
present and correct** — `dadaia reports validate` recomputes the file's SHA-256 and
fails on a mismatch or a missing file.

---

## Protocol

### Step 0 — Resolve the workspace root (before composing any path)

Handoff and report paths are **workspace-root-relative**, never cwd-relative. A sub-agent
frequently runs with its cwd inside a repo (`repos/<slug>/…`); composing
`.dadaia/handoff/…` from there would create a stray `.dadaia/` **inside the repo**, which
corrupts workspace-vs-repo boundary detection and hides the handoff from the panel.

Before composing any `.dadaia/handoff/…` or `.dadaia/reports/…` path, resolve the
workspace root: starting at the current working directory, walk up parent by parent and
stop at the first ancestor that **already contains** a `.dadaia/` directory. That ancestor
is the workspace root — compose every handoff and report path under it. Never create a new
`.dadaia/`: if no ancestor already contains one, stop and report the missing workspace
root rather than materializing `.dadaia/` inside a repo working tree.

### Step 1 — Determine the mode

Default to handoff-only. Switch to report mode only if the operator asked for an HTML
report or your `next_handoff.agent` is `"human"`. In report mode, write the HTML report
under `.dadaia/reports/<context>/<agent>/<UTC>-<slug>.html` **before** emitting the
handoff.

### Step 2 — (report mode only) Compute the report's SHA-256

```bash
sha256sum <absolute-path-to-report.html>
```

Capture the hex digest (first field) — the value for `artifact.content_hash`.
Skip this step entirely in handoff-only mode.

### Step 3 — Assemble the handoff JSON

Construct a JSON object with the required fields and any applicable optional fields.
All field semantics match the schema at `.dadaia/agentic/schemas/handoff-v1.schema.json`.

#### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string (literal) | Always `"handoff-v1.1"` |
| `agent` | string | The `name` from your own frontmatter (e.g. `"software-engineer"`) |
| `context` | string | Active Spec Context Project name (e.g. `"dadaia-workspace"`) |
| `produced_at` | string (ISO 8601) | UTC timestamp of emission, e.g. `"2026-06-10T12:00:00Z"` |
| `scope` | string | Scope descriptor (e.g. task id, file path, module, component) |
| `metrics` | object | Key quantitative metrics (e.g. `{"files_changed": 3, "lines_added": 42}`) |
| `artifact.type` | string | One of `"report"`, `"spec"`, `"plan"`, `"tasks"`, `"closure"`, `"memory"`, `"other"` |

#### Optional fields (include when applicable)

| Field | Type | Description |
|-------|------|-------------|
| `artifact.path` | string | Report mode only: workspace-relative path to the HTML report. |
| `artifact.content_hash` | string | Report mode only: bare 64-char lowercase hex SHA-256 from Step 2. Mandatory whenever `artifact.path` is present. |
| `release_id` | string | Active release identifier. Include whenever the work relates to a named release. |
| `findings` | array | Finding objects: `severity` (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`/`INFO`), `message`, `detail_md`, `fix_recommendation`. |
| `decisions_required` | array of strings | Decisions a downstream agent or operator must resolve. |
| `next_handoff` | object | Expected next handoff: `agent`, `context`, `expected_artifact_type`. |
| `verdict` | string | `"APPROVED"` or `"REJECTED"` — emitted by reviewers. |
| `verdict_reason` | string | Human-readable explanation of the verdict. |

#### Example — handoff-only (the default)

```json
{
  "schema_version": "handoff-v1.1",
  "agent": "software-engineer",
  "context": "dadaia-workspace",
  "produced_at": "2026-06-10T12:00:00Z",
  "scope": "T-128 implementation — run.resume idempotency",
  "metrics": {"files_changed": 2, "tests_added": 4},
  "artifact": {"type": "other"},
  "release_id": "v0.1.10",
  "next_handoff": {
    "agent": "qa-engineer",
    "context": "dadaia-workspace",
    "expected_artifact_type": "report"
  }
}
```

#### Example — with HTML report (operator-requested / human-facing)

```json
{
  "schema_version": "handoff-v1.1",
  "agent": "qa-engineer",
  "context": "dadaia-workspace",
  "produced_at": "2026-06-10T12:00:00Z",
  "scope": "T-128 acceptance validation",
  "metrics": {"checks_run": 12, "checks_passed": 12},
  "release_id": "v0.1.10",
  "artifact": {
    "type": "report",
    "path": ".dadaia/reports/dadaia-workspace/qa-engineer/2026-06-10T120000Z-T-128-validation.html",
    "content_hash": "a3f8c2d1e4b5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1"
  },
  "findings": [
    {
      "severity": "INFO",
      "message": "All acceptance checks passed.",
      "detail_md": "Ran full pytest suite; 0 failures.",
      "fix_recommendation": "No action required."
    }
  ],
  "verdict": "APPROVED",
  "verdict_reason": "Acceptance criteria satisfied.",
  "next_handoff": {
    "agent": "human",
    "context": "dadaia-workspace",
    "expected_artifact_type": "other"
  }
}
```

### Step 4 — Emit the handoff file using the Write tool

Rules:
- Directory: `.dadaia/handoff/<context>/`.
- Filename: `<YYYY-MM-DDTHHMMSSZ>-<agent>-<slug>.handoff.json`.
- Extension: `.handoff.json`.
- 2-space indentation for human readability.

Example:

```
Handoff:      .dadaia/handoff/dadaia-workspace/2026-06-10T120000Z-qa-engineer-T-128-validation.handoff.json
HTML report (report mode only):
              .dadaia/reports/dadaia-workspace/qa-engineer/2026-06-10T120000Z-T-128-validation.html
```

---

## Validation

After emitting the handoff, verify it:

```bash
dadaia reports validate <path-to-handoff.handoff.json>
```

Exit 0 confirms the handoff is structurally valid; in report mode it also confirms the
referenced report exists and its hash matches. Fix any non-zero exit before proceeding.

---

## Guardrails

- Never duplicate the schema content inside the handoff JSON or this skill file.
- Never include `artifact.path` for a file that does not exist on disk — in report
  mode, write the HTML report first.
- Never include `artifact.path` without its matching `content_hash` (the validator
  recomputes and fails on mismatch).
- Never write handoff JSON under `.dadaia/reports/`.
- Resolve the workspace root first (the nearest ancestor already containing `.dadaia/`);
  never create a `.dadaia/` directory inside a repo working tree.
- `produced_at` must be a valid ISO 8601 UTC timestamp ending in `Z`.
- `artifact.content_hash`, when present, is a bare 64-character lowercase hex string —
  no prefix.
