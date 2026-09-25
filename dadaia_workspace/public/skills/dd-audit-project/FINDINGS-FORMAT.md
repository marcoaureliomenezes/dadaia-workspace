# FINDINGS-FORMAT — one record per finding

Disclosed sibling of `SKILL.md`. Every claim any pillar makes becomes exactly one line appended to
`specs/audits/<YYYYMMDD>-<slug>/FINDINGS.jsonl`, validating
`dadaia_workspace/public/schemas/audits/finding-record-v1.schema.json` — the schema is the source of field semantics.

## Fields

| Field | Mutability | Set by |
|---|---|---|
| `id` | immutable-core | `<audit-slug>-F<nnn>`, appended once |
| `pillar` | immutable-core | `bugs` \| `specs` \| `memory` |
| `severity` | immutable-core | `LOW` \| `MEDIUM` \| `HIGH` \| `CRITICAL` |
| `refs` | immutable-core | file:line, bug ids, commit shas, and/or release ids the claim is anchored to |
| `claim` | immutable-core | one sentence stating what the record asserts |
| `evidence` | immutable-core | the reproducible command plus a redacted one-line result — never a path alone |
| `disposition` | mutable-governance | `open` at append; rewritten by `python3 .agents/skills/dd-audit-project/scripts/audit.py disposition` |
| `release` | mutable-governance | `null` until dispositioned |
| `reason` | mutable-governance | `null` until dispositioned |

- An append is file-tool authoring (the immutable core, like an ADR); every later change is a verb.
- No write-time seam guards the append, so the evidence rule below is a hand discipline.

## The evidence rule — reproducible command, never a path

- `evidence` is always the reproducible command plus a redacted one-line result.
- Example: `git show <sha> --stat -- <module> -> 2 files changed, second render path added`.
- Never a bare pointer into `.dadaia/tmp/**` — that lane expires one day after its mtime.
- A `.dadaia/tmp/**` capture may accompany the command+result as a convenience pointer, never the sole citation.
- Strip runner-absolute paths from a tool's raw output (`lint-imports`, `pytest`, ratchet scripts) by hand before writing the line.

## Appending

1. Append with ordinary file tools: read the existing file, add one line, write.
2. Before the S3-equivalent close of any audit, run the folder through the push-time detector (`.dadaia/.venv/bin/dadaia ci push-gate-check` over the range).
3. Record a zero-hit result from that detector run.

## Disposition and close — by verb

- `python3 .agents/skills/dd-audit-project/scripts/audit.py disposition <dir> <finding-id> --disposition resolved|superseded|deferred|rejected --release <id> [--reason]` rewrites the three governance fields in place; every immutable field stays byte-identical.
- `--reason` is required for `deferred` and `rejected`; a second disposition of the same finding is refused.
- `python3 .agents/skills/dd-audit-project/scripts/audit.py close <dir> --sha <window-end>` refuses while any finding is `open`, appends the one `audits_histo.jsonl` record and deletes the directory — all-or-nothing.
