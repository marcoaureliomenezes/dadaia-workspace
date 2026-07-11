---
id: bug_report.bug_write
role: product-engineer
workflow: bug_report
step: bug_write
static_inputs: []
dynamic_inputs: [open_bugs]
output_schema: bug-record-handoff-v1
max_context_policy: summary
---

# Bug write — file the additive bug record

You write the bug record. This step's only write is an **additive** bug file under the
bug channel — it never edits, moves, or deletes any other file. The bug channel is
additive by construction: a new file appears, nothing else changes.

## Inputs you reason over

| Input | Use |
|---|---|
| `open_bugs` | The existing bugs, so the new record's slug and framing stay consistent. |

## Procedure

1. **Write only to the bug channel.** Produce exactly one additive bug record for the
   bug channel (the store is event-sourced: a single `reported` event, appended by the
   Python gate — you produce the content, never the write). Do not touch memory,
   specs, source, or any existing bug.
2. **Carry the normalized fields.** The record carries the symptom, repro,
   expected/actual, severity, surface, and the reported date from the intake step.
3. **Stay redaction-clean.** No operator-local absolute path, IP, hostname, private
   repo name, or secret in the committed record.

## Output

A record handoff naming the new bug file's slug and the fields it carries. The write
is additive — no lock is taken and the write is never blocked; the bug channel only
grew by one file.
