---
name: dadaia-handoff-emitter
description: >
  Standalone skill that instructs an agent to emit a machine-readable handoff sidecar
  (<stem>.handoff.json) adjacent to any HTML report it just produced under
  .dadaia/reports/. The sidecar conforms to the schema at
  .dadaia/agentic/schemas/handoff-v1.schema.json and enables downstream CLI validation
  via `dadaia reports validate`. Invoke this skill once per HTML report, immediately
  after the Write tool call that finalises the report.
applyTo: ".dadaia/reports/**/*.html"
---

# dadaia-handoff-emitter

## Purpose

After an agent finalises an HTML report in `.dadaia/reports/`, it must emit a
structured JSON sidecar so that other agents and the `dadaia reports validate`
CLI can verify the report's origin, content hash, and conformance to the
handoff contract.

The sidecar schema lives at:

```
.dadaia/agentic/schemas/handoff-v1.schema.json
```

Do **not** reproduce the schema content here — always reference it by that path.

---

## 3-Step Protocol

Invoke this skill immediately after the `Write` tool call that finalises the HTML
report. Complete all three steps in sequence before moving to any other work.

### Step 1 — Compute the SHA-256 hash of the HTML report

Run the following Bash command, substituting the actual path of the report you just wrote:

```bash
sha256sum <absolute-path-to-report.html>
```

Capture the hex digest (the first field). This is the value for `artifact.content_hash`.

Example:
```bash
sha256sum .dadaia/reports/dadaia-workspace/software-engineer-python/2026-05-16T120000Z-task-green.html
# → a3f8c2... .dadaia/reports/.../task-green.html
```

### Step 2 — Assemble the handoff JSON dictionary

Construct a JSON object with the required fields and any applicable optional fields
listed below. All field semantics match the schema at
`.dadaia/agentic/schemas/handoff-v1.schema.json`.

#### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string (literal) | Always `"handoff-v1"` |
| `agent` | string | The `name` from your own frontmatter (e.g. `"software-engineer-python"`) |
| `context` | string | Active Spec Context Project name (e.g. `"dadaia-workspace"`) |
| `produced_at` | string (ISO 8601) | UTC timestamp when the report was finalised, e.g. `"2026-05-16T12:00:00Z"` |
| `artifact.type` | string | One of `"report"`, `"spec"`, `"plan"`, `"tasks"`, `"closure"` |
| `artifact.path` | string | Logical path to the HTML report, relative to workspace root, e.g. `.dadaia/reports/dadaia-workspace/software-engineer-python/2026-05-16T120000Z-task-green.html` |
| `artifact.content_hash` | string | `sha256:<hex>` — prefix the hex digest from Step 1 with `sha256:` |

#### Optional fields (include when applicable)

| Field | Type | Description |
|-------|------|-------------|
| `release_id` | string | Active release identifier, e.g. `"agent-comms-v1"`. Include whenever the report relates to a named release. |
| `findings` | array | Zero or more finding objects, each with `severity` (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, or `INFO`) and `summary` (string). Include when the report surfaces structured findings. |
| `decisions_required` | array of strings | List of decision items that a downstream agent or operator must resolve. |
| `next_handoff` | object | Expected next handoff: `{ "agent": "<name>", "input": "<description>" }`. Include when the workflow has a clear next recipient. |

#### Example minimal handoff

```json
{
  "schema_version": "handoff-v1",
  "agent": "software-engineer-python",
  "context": "dadaia-workspace",
  "produced_at": "2026-05-16T12:00:00Z",
  "artifact": {
    "type": "report",
    "path": ".dadaia/reports/dadaia-workspace/software-engineer-python/2026-05-16T120000Z-task-green.html",
    "content_hash": "sha256:a3f8c2d1e4b5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1"
  }
}
```

#### Example full handoff

```json
{
  "schema_version": "handoff-v1",
  "agent": "software-engineer-python",
  "context": "dadaia-workspace",
  "produced_at": "2026-05-16T12:00:00Z",
  "release_id": "agent-comms-v1",
  "artifact": {
    "type": "report",
    "path": ".dadaia/reports/dadaia-workspace/software-engineer-python/2026-05-16T120000Z-T-AC-09-green.html",
    "content_hash": "sha256:a3f8c2d1e4b5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1"
  },
  "findings": [
    { "severity": "INFO", "summary": "All acceptance checks passed." }
  ],
  "decisions_required": [],
  "next_handoff": {
    "agent": "qa-engineer",
    "input": "Green implementation report for T-AC-09; please run E2E validation."
  }
}
```

### Step 3 — Emit the sidecar file using the Write tool

The sidecar filename is derived from the HTML report's stem by replacing `.html`
with `.handoff.json`. It lives in the **same directory** as the HTML report.

Rules:
- Same directory as the HTML report.
- Same stem as the HTML report.
- Extension: `.handoff.json`.

Example:

```
HTML report:  .dadaia/reports/dadaia-workspace/software-engineer-python/2026-05-16T120000Z-task-green.html
Sidecar:      .dadaia/reports/dadaia-workspace/software-engineer-python/2026-05-16T120000Z-task-green.handoff.json
```

Use the `Write` tool with the assembled JSON as content:

```
Write(
  file_path = "<same-dir-as-html>/<stem>.handoff.json",
  content   = <JSON string from Step 2>
)
```

Emit the JSON with 2-space indentation for human readability.

---

## Validation

After emitting the sidecar, optionally verify it with:

```bash
dadaia reports validate <path-to-sidecar.handoff.json>
```

Exit 0 confirms the sidecar is valid against the schema. A non-zero exit
indicates a structural error — fix the sidecar before proceeding.

---

## Guardrails

- Never duplicate the schema content inside the handoff JSON or this skill file.
- Never omit the `sha256:` prefix from `artifact.content_hash`.
- Never emit a sidecar for a report that does not yet exist on disk.
- The sidecar must be adjacent to the HTML (same directory, same stem) — no exceptions.
- `produced_at` must be a valid ISO 8601 UTC timestamp ending in `Z`.
