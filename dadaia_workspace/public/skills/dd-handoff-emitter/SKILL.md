---
name: dd-handoff-emitter
description: >
  Emit the machine-readable handoff JSON at the end of any agent task (handoff-only by
  default; HTML report added only when the operator asks or the next hop is human), and
  delete a consumed coordination handoff (ack-on-consume). Use at task completion and
  after acting on a handoff addressed to you.
---

# dd-handoff-emitter

Handoff-first emission (`DADAIA.md` §5): the JSON handoff is the default output of a
completed agent task; the HTML report is the exception, not the rule.

## Emitting

1. Resolve the workspace root: walk up from cwd to the nearest ancestor already
   containing `.dadaia/` — never create a new one.
2. Default to handoff-only; switch to report mode only when the operator asked or
   `next_handoff.agent == "human"`.
3. Report mode first writes the HTML to
   `repos/<slug>/reports/<agent>/<UTC>-<slug>.html`, then captures
   `sha256sum <report>` as `artifact.content_hash`.
4. Assemble the handoff field-by-field against
   `.dadaia/agentic/schemas/handoff-v1.schema.json`; set `artifact.path` only for a
   file already on disk.
5. Write `.dadaia/handoff/<context>/<YYYY-MM-DDTHHMMSSZ>-<agent>-<slug>.handoff.json`
   (2-space indent) and run `dadaia reports validate <path>` — fix any non-zero exit
   before moving on.

**Done when** the handoff file exists at that exact path shape, `dadaia reports
validate` exits 0, and (report mode) `artifact.content_hash` matches the file on disk.

## Consuming (ack-on-consume)

After reading and acting on a coordination handoff addressed to you:

1. Resolve its real target path; act only on a path inside `.dadaia/`, and never
   follow a symlinked directory.
2. Delete only that one consumed handoff file; every other handoff expires one day
   after its mtime and `dadaia doctor` reaps it, `artifact.path` or not.

**Done when** the consumed coordination handoff is gone and every other handoff still
validates.

## References

- `.dadaia/agentic/schemas/handoff-v1.schema.json` — field list, types, enums,
  patterns, `schema_version` posture.
- `DADAIA.md` §5 — emission law, output paths, the 30 KB report split rule.
