# FINDINGS-FORMAT — one record per finding

Disclosed sibling of `SKILL.md`. Every claim becomes one line in
`specs/audits/<YYYYMMDD>-<slug>/FINDINGS.jsonl`, validated by
`dadaia_workspace/public/schemas/audits/finding-record-v1.schema.json`. The schema owns
field semantics.

## Fields

| Field | Mutability | Set by |
|---|---|---|
| `id` | immutable-core | `<audit-slug>-F<nnn>`, appended once |
| `pillar` | immutable-core | `bugs` \| `specs` \| `memory` |
| `severity` | immutable-core | `LOW` \| `MEDIUM` \| `HIGH` \| `CRITICAL` |
| `refs` | immutable-core | file:line, bug ids, commit shas and/or release ids |
| `claim` | immutable-core | one sentence stating the finding |
| `evidence` | immutable-core | reproducible command plus a redacted one-line result |
| `disposition` | mutable-governance | `open` at append; later moved by `audit.py disposition` |
| `release` | mutable-governance | remediation release for `resolved` or `superseded` |
| `reason` | mutable-governance | rationale for `rejected` |

An append authors the immutable core. Every later change uses the disposition verb.

## Evidence

- Record the reproducible command and its redacted one-line result.
- Example: `git show <sha> --stat -- <module> -> 2 files changed, old path deleted`.
- A `.dadaia/tmp/**` capture may accompany that evidence, but it expires and is never the
  sole citation.
- Remove runner-absolute paths and private data before writing the line.

## Append, disposition and close

1. Append one schema-valid JSON object as one line.
2. Before publishing the audit, run the push-time privacy detector over its range and
   record the zero-hit result.
3. Move a finding with:

   ```bash
   python3 .agents/skills/dd-audit-project/scripts/audit.py disposition \
     <audit> <finding-id> --disposition resolved|superseded|rejected \
     [--release <id>] [--reason <reason>]
   ```

4. `resolved` and `superseded` require the remediation release; `rejected` requires a
   reason. A later disposition replaces only the finding's governance triple; its
   immutable fields remain unchanged.
5. `audit.py close <audit> --sha <window-end>` refuses while any finding is `open`, then
   appends one audit-history record and deletes the live directory atomically.
