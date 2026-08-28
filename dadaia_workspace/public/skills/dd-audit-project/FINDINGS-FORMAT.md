# FINDINGS-FORMAT — one record per finding

Disclosed sibling of `SKILL.md`. Every claim any pillar makes becomes exactly one line appended to
`specs/audits/<YYYYMMDDTHHMMSSZ>-<session_id_8chars>/FINDINGS.jsonl`, validating
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
| `disposition` | mutable-governance | `open` at append; rewritten by the remediation release |
| `release` | mutable-governance | `null` until dispositioned |
| `reason` | mutable-governance | `null` until dispositioned |

- There is no CLI writer for `specs/audits/**` (D15/A14.5) — the auditor appends and later rewrites with file tools.
- That absence of a write-time seam is why the evidence rule below is a hand discipline, not a mechanical guarantee.

## The evidence rule (A13.5) — reproducible command, never a path

- `evidence` is always the reproducible command plus a redacted one-line result.
- Example: `git show <sha> --stat -- <module> -> 2 files changed, second render path added`.
- Never a bare pointer like `see .dadaia/tmp/project-auditor/20261020/transcript.txt` — the lane GCs at 3 days.
- A `.dadaia/tmp/**` capture may accompany the command+result as a convenience pointer, never the sole citation.
- Strip runner-absolute paths from a tool's raw output (`lint-imports`, `pytest`, ratchet scripts) by hand before writing the line.

## Appending

1. Append with ordinary file tools: read the existing file, add one line, write.
2. Before the S3-equivalent close of any audit, run the folder through the push-time detector (`dadaia ci push-gate-check` over the range).
3. Record a zero-hit result from that detector run.

## Disposition, at the remediation release

- The three mutable-governance fields are rewritten in place, in the remediation release that gives this record its disposition.
- Every immutable field stays byte-identical.
- `disposition` takes exactly one of `fixed | superseded | deferred | rejected` — never a second `open` line for the same record.
- Never rewrite `id`/`pillar`/`severity`/`refs`/`claim`/`evidence`.
- Lifecycle (one audit -> one remediation release -> archive): `DADAIA.md` §6 (Audits).
