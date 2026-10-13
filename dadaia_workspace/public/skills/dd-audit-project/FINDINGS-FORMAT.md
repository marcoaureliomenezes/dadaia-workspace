# FINDINGS-FORMAT — one record per finding

Disclosed sibling of `SKILL.md`. Every claim becomes one line in
`specs/audits/<YYYYMMDD>-<slug>/FINDINGS.jsonl`, validated by
`.agents/skills/dd-audit-project/scripts/schemas/finding-record-v1.schema.json`. The schema owns
field semantics.

## Writes

An append authors the immutable core. Every later change uses the disposition verb.

## Evidence

- Record the reproducible command and its redacted one-line result.
- Example: `git show <sha> --stat -- <module> -> 2 files changed, old path deleted`.
- A `.dadaia/tmp/**` capture may accompany that evidence, but it expires and is never the
  sole citation.
- Remove runner-absolute paths and private data before writing the line.

## Append, disposition and close

1. Append one schema-valid JSON object as one line.
2. Move a finding with:

   ```bash
   python3 .agents/skills/dd-audit-project/scripts/audit.py disposition \
     <audit> <finding-id> --disposition <terminal-disposition> \
     [--release <id>] [--reason <reason>]
   ```

3. The finding schema defines dispositions and their required evidence. A later
   disposition replaces only the finding's governance triple; its immutable fields
   remain unchanged.
4. `audit.py close <audit> --sha <window-end>` refuses while any finding is `open`, then
   appends one audit-history record and deletes the live directory atomically.
