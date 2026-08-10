# Audits

This directory contains audit records for this Spec Context Project.

## Authoring Rules

- Each audit session produces a directory named `<YYYY-MM-DDTHHMMSSZ>-<session_id8>/`
  where `<session_id8>` is the first 8 characters of the session identifier.
- The directory contains the audit findings as Markdown or JSON files.
- Required fields per audit: timestamp, agent(s), scope, findings, decisions.
- Audits are immutable after they are committed — do not edit historical records.
- Never delete audit directories — they are the audit trail for the project.

## Relationship to Releases

An audit may be referenced by a release SPEC or CLOSURE.md using its directory
name as the citation key. Audit directories are created by `project-auditor` or
`project-manager` during the DISCOVERY phase.
