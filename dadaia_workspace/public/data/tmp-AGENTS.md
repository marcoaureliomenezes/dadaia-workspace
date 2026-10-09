# .dadaia/tmp/AGENTS.md — Temporary Files

Scope: this file governs `.dadaia/tmp/**`.

## 1. Rules

- Path: the root `AGENTS.md` map §4, one `<slug>/` per task beneath it.
- A dated dir expires one day after its own mtime, whatever it holds; work that outlives the day continues in today's dir.
- If a temporary artifact is required for traceability, move the evidence reference into the reports home (the root `AGENTS.md` map §4).
- Release documents, source, tests and state live in their repo or zone; this zone holds evidence only.

## 2. Cleanup

- Set the handoff's `artifact.path` (with its `content_hash`) to the moved file.
