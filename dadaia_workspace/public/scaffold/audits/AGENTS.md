# specs/audits/ — Audit Rules

Scope: this file governs only `specs/audits/`.

- The main thread writes an audit directory from the reviewer's (`dd-code-reviewer`, audit lens) returned report, directly in any phase, with no worktree; the reviewer is read-only and writes only its verdict.
- An audit runs three pillars together — bug history, spec compliance, memory drift — over the window `dd-bug-resolution/LINEAGE.md` defines.
- Suggested every 5 releases, never mandatory.

## 1. Authoring rules

- Each audit session produces a directory named `<YYYYMMDD>-<slug>/` holding its committed findings and summary.
- That directory holds `AUDIT.md` and `FINDINGS.jsonl` (one record per finding, appended once).
- A committed audit changes only by `audit.py disposition`.
- A finding's disposition moves only by `python3 .agents/skills/dd-audit-project/scripts/audit.py disposition <dir> <finding-id> ...` (`--help` lists the dispositions); every other field stays byte-identical.
- Once none is `open`: `python3 .agents/skills/dd-audit-project/scripts/audit.py close <dir> --sha <window-end>` appends the one `histo-record-v1` and deletes the directory.

## 2. Relationship to releases

- A SPEC cites a finding in its Origin as `findings:<audit-id>-F<nnn>` (`specs/releases/AGENTS.md` §2).
- One audit generates at most one remediation release, which must disposition every finding before the audit archives; a zero-finding audit generates none.
