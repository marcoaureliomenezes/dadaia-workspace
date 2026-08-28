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
applyTo: ".dadaia/handoff/**/*.handoff.json"
---

# dadaia-handoff-emitter

## Purpose

Every completed agent task ends with a structured JSON handoff under
`.dadaia/handoff/<context>/` so downstream agents, the panel, and
`dadaia reports validate` can consume the result as a machine contract.

Emission is **handoff-first** (`DADAIA.md` §5 (Emission is handoff-first)):

| Mode | When |
|---|---|
| Handoff-only (default) | Normal agent-to-agent flow — no `artifact.path`, no `content_hash` |
| Handoff + HTML report | Operator explicitly requested a report, OR `next_handoff.agent == "human"` |

**The schema is the one source of field semantics — read it, never transcribe it here:**

```
.dadaia/agentic/schemas/handoff-v1.schema.json
```

It declares every required/optional field, its type, enum, and pattern, including the
report-mode pairing (`artifact.path` requires `artifact.content_hash`, recomputed and
verified by `dadaia reports validate`) and the `schema_version` transition posture
(new handoffs use `"handoff-v1.2"`; a session that read zero memory atoms emits
`"handoff-v1.1"` with no `self_pull` rather than fabricate refs).

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

### Step 3 — Assemble the handoff JSON against the schema

Construct the JSON object field-by-field against
`.dadaia/agentic/schemas/handoff-v1.schema.json` — do not reproduce its field list or
enums here, and do not include `artifact.path` for a file that does not exist on disk
(write the HTML report first, in report mode).

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

## Consuming a handoff (ack-on-consume — FR23)

This is the **one** place this rule is stated. Every skill whose input contract is "read
a handoff" (a dispatcher relaying a sub-agent's result, a reviewer picking up an
implementer's handoff, any consumer reading `.dadaia/handoff/<context>/…`) follows this
rule and never restates it — reference this section instead.

**The rule.** Once a consuming skill has read and acted on a coordination handoff, it
deletes that handoff file. A handoff carrying `artifact.path` is **exempt** — it is
artifact-bearing, not purely coordination, and its retention instead follows its
referenced report's retention (`DADAIA.md` §5 (Where things are written)). Never delete
an artifact-bearing handoff under this rule.

**The deletion lane guard (AG.1 — inherits FR17's symlink doctrine (A17.1) by
reference, not restated here).** Before deleting a consumed coordination handoff:

1. Resolve the handoff's real target path.
2. Refuse the deletion if the resolved target falls outside `.dadaia/`.
3. Never follow a symlinked directory while resolving or walking to the target.

**Never break a surviving handoff.** Deleting a consumed coordination handoff must never
break `dadaia reports validate` on any other handoff still on disk — deletion is scoped
to exactly the one consumed file, never a directory sweep.

---

## Guardrails

- Never duplicate the schema content inside the handoff JSON or this skill file.
- Never include `artifact.path` without its matching `content_hash` — the validator
  recomputes it and fails on mismatch.
- Never write handoff JSON under `.dadaia/reports/`.
- Resolve the workspace root first (the nearest ancestor already containing `.dadaia/`);
  never create a `.dadaia/` directory inside a repo working tree.
