---
name: dadaia-handoff-emitter
description: >
  Emit a machine-readable handoff JSON under .dadaia/handoff/<context>/ at the end of
  any agent task. Handoff-first: the default emission is handoff-only — the HTML report
  is added only when the operator asks or the next handoff target is human, and then the
  handoff also carries artifact.path + content_hash. Conforms to
  .dadaia/agentic/schemas/handoff-v1.schema.json; validated via `dadaia reports validate`.
  Also the single canonical location for the consumer-side rule: a consuming skill
  deletes the coordination handoff it consumed (ack-on-consume).
tldr: "Emit JSON handoff at task end (handoff-only default); add HTML report only if asked or next hop is human."
applyTo: ".dadaia/handoff/**/*.handoff.json"
---

# dadaia-handoff-emitter

## 1. When

- End of every completed agent task.
- A consuming skill has read and acted on a coordination handoff (ack-on-consume).

## 2. Steps

1. Resolve workspace root: walk up from cwd to the nearest ancestor already containing `.dadaia/`; never create a new one.
2. Default to handoff-only mode; switch to report mode only if asked, or `next_handoff.agent == "human"`.
3. Report mode: write the HTML report first, to `.dadaia/reports/<context>/<agent>/<UTC>-<slug>.html`.
4. Report mode: run `sha256sum <path-to-report.html>`; capture the hex digest as `artifact.content_hash`.
5. Assemble the handoff JSON field-by-field against `.dadaia/agentic/schemas/handoff-v1.schema.json`.
6. Never set `artifact.path` for a file that does not yet exist on disk.
7. Write via the Write tool: `.dadaia/handoff/<context>/<YYYY-MM-DDTHHMMSSZ>-<agent>-<slug>.handoff.json`, 2-space indent.
8. Run `dadaia reports validate <path>.handoff.json`; fix any non-zero exit before moving on.
9. Consuming a coordination handoff: after acting on it, resolve its real target path.
10. Refuse deletion if the resolved target falls outside `.dadaia/`; never follow a symlinked directory.
11. Delete only the one consumed coordination handoff file — never a directory sweep.
12. Never delete a handoff carrying `artifact.path` — it follows its report's own retention instead.

## 3. Done when

- The handoff file exists at the exact directory/filename/extension above.
- `dadaia reports validate` exits 0.
- Report mode: `artifact.content_hash` matches the file on disk.
- A consumed coordination handoff (no `artifact.path`) is gone; every other handoff still validates.

## 4. References

- `.dadaia/agentic/schemas/handoff-v1.schema.json` — field list, types, enums, patterns, `schema_version` posture.
- `DADAIA.md` §5 — emission-first law, output paths.
- FR17 / A17.1 — symlink doctrine the deletion lane guard inherits.
