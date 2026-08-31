# specs/audits/ — Audit Rules

Scope: this file governs only `specs/audits/`. Replaces the retired `audits/README.md` (v6 canon, FR1).

This directory contains audit records for this Spec Context Project.

## 1. Authoring rules

- Each audit session produces a directory named `<YYYYMMDD>-<slug>/` holding its committed findings and summary.
- That directory holds `AUDIT.md` and, where the schema is in force, `FINDINGS.jsonl` (one record per finding, appended once).
- Required fields per audit: timestamp/window, agent(s), scope, findings, decisions.
- Audits are immutable after commit — do not edit historical records.
- A finding's disposition is updated in place by the remediation release only; every other field stays byte-identical.
- An audit is never deleted while open.
- Once fully dispositioned: append one summary record to `_archive/audits_histo.jsonl`, delete the audit directory.
- No per-audit archive directory — history survives in git and the histo record.

## 2. Relationship to releases

- An audit may be referenced by a release SPEC or `_RELEASE.json`'s `log` entries, by its directory name.
- Audit directories are created by `project-auditor` or `project-manager` during the DISCOVERY phase.
- One audit generates exactly one remediation release, which must disposition every finding before the audit archives.
