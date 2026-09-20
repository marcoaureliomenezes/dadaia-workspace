# specs/audits/ — Audit Rules

Scope: this file governs only `specs/audits/`.

This directory contains audit records for this Spec Context Project.

## 1. Authoring rules

- Each audit session produces a directory named `<YYYYMMDD>-<slug>/` holding its committed findings and summary.
- That directory holds `AUDIT.md` and, where the schema is in force, `FINDINGS.jsonl` (one record per finding, appended once).
- Required fields per audit: timestamp/window, agent(s), scope, findings, decisions.
- Audits are immutable after commit — do not edit historical records.
- A finding's disposition moves only by `dadaia audit disposition <dir> <finding-id> --disposition … --release <id>`; every other field stays byte-identical.
- An audit is never deleted while open.
- Once none is `open`: `dadaia audit close <dir> --sha <window-end>` appends the one `histo-record-v1` and deletes the directory, all-or-nothing.
- No per-audit archive directory — history survives in git and the histo record.

## 2. Relationship to releases

- An audit may be referenced by a release SPEC or `_RELEASE.json`'s `log` entries, by its directory name; the audit window is read from `_archive/audits_histo.jsonl`, never from a release milestone.
- Audit directories are created by `code-reviewer` (audit lens) or `project-manager`; audit paths are ADDITIVE, writable in any phase.
- One audit generates exactly one remediation release, which must disposition every finding before the audit archives.
