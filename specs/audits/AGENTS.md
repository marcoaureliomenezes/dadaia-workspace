# specs/audits/ — Audit Rules

Scope: this file governs only `specs/audits/`. It replaces the retired
`audits/README.md` (v6 canon, FR1) — its content lives here now.

This directory contains audit records for this Spec Context Project.

## Authoring Rules

- Each audit session produces a directory named `<YYYYMMDD>-<slug>/` holding its
  committed findings and summary (`AUDIT.md` and, where the audit schema is in force,
  `FINDINGS.jsonl` — one record per finding, appended once).
- Required fields per audit: timestamp/window, agent(s), scope, findings, decisions.
- Audits are immutable after they are committed — do not edit historical records; a
  finding's disposition is updated in place by the remediation release only, every
  other field stays byte-identical.
- Never delete audit directories — they are the audit trail for the project.
  `specs/audits/_archive/` is the landing zone once an audit is fully dispositioned.

## Relationship to Releases

An audit may be referenced by a release SPEC or CLOSURE.md using its directory
name as the citation key. Audit directories are created by `project-auditor` or
`project-manager` during the DISCOVERY phase. One audit generates exactly one
remediation release, which must give every finding an explicit disposition before the
audit archives.
