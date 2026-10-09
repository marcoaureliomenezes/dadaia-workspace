---
name: dd-handoff-emitter
description: >
  Emit the machine-readable handoff JSON at the end of any agent task (handoff-only by
  default; HTML report added only when the operator asks or the next hop is human), and
  delete a consumed coordination handoff (ack-on-consume). Use at task completion and
  after acting on a handoff addressed to you.
---

# dd-handoff-emitter

Handoff-first emission: the JSON handoff is the default output of a
completed agent task; the HTML report is the exception, not the rule.

## Emitting

1. Open `.dadaia/handoff/AGENTS.md` (the area's scoped law) and follow it.
2. Resolve the workspace root: walk up from cwd to the nearest ancestor holding
   `.dadaia/states/spec_contexts.json` — write under that root only, since a second `.dadaia/` splits workspace state.
3. Report mode only per `.dadaia/handoff/AGENTS.md`.
4. Report mode first writes the HTML to
   `.dadaia/reports/<context>/<UTC>-<agent>-<slug>.html`, then captures
   `sha256sum <report>` as `artifact.content_hash`.
5. Assemble the handoff field-by-field against
   `.dadaia/agentic/schemas/handoff-v1.schema.json`; set `artifact.path` only for a
   file already on disk.
6. Write `.dadaia/handoff/<context>/<YYYY-MM-DDTHHMMSSZ>-<agent>-<slug>.handoff.json`
   (2-space indent) and run `.dadaia/.venv/bin/dadaia reports validate <path>` — fix any non-zero exit
   before moving on.
7. A reviewer verdict is written only by `python3 .agents/skills/dd-handoff-emitter/scripts/verdict.py <worktree> --sha <sha> --context <ctx>
   --slug <slug> --verdict APPROVED|REJECTED --reason "<line>"`, the rest of the body as one JSON
   object on stdin; it binds the verdict to the diff it judged. Then run `reports validate` on the
   path it prints.

**Done when** the handoff file exists at that exact path shape, `.dadaia/.venv/bin/dadaia reports
validate` exits 0, and (report mode) `artifact.content_hash` matches the file on disk, and for a verdict, `reports validate` exits 0 on the path `verdict.py` printed.

## Consuming (ack-on-consume)

After reading and acting on a coordination handoff addressed to you:

1. Resolve its real target path; act only when the resolved path stays inside `.dadaia/`, since a
   symlinked directory can point the delete elsewhere.
2. Delete only that one consumed handoff file; every other handoff is reaped on the
   schedule in `.dadaia/AGENTS.md`'s zone table.

**Done when** the consumed coordination handoff is gone and every other handoff still
validates.

## References

- `.dadaia/agentic/schemas/handoff-v1.schema.json` — field list, types, enums,
  patterns, `schema_version` posture.
- `python3 .agents/skills/dd-handoff-emitter/scripts/verdict.py --help` — the verdict writer's flags.
