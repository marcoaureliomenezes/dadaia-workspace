# SLOP.md — detection signals

Disclosed sibling of [`SKILL.md`](SKILL.md), read inside Axis 1 (Standards). The definition
is `DADAIA.md` §7.6 — slop is what passes the deletion test without loss. Each signal is a
labelled judgement call with the command that makes it verifiable in the diff.

## Signals

| # | Signal | Verify in the diff | Severity | Fix direction |
|---|---|---|---|---|
| S1 | Comment narrating the what, the change or an id | `git diff -U0 \| grep -E '^\+\s*#.*(FR[0-9]\|T-[0-9]{3}\|ADR\|v[0-9]\.[0-9]\|added\|fixed\|changed)'`; a comment paraphrasing the next line | LOW; MEDIUM above 5 hits | Delete; the why moves to the commit body or the ledger |
| S2 | Docstring over 3 lines carrying history | `git diff \| grep -c '"""'`, then read; the words bug, release, resolved, previously | LOW | Reduce to the contract |
| S3 | Test slop: no `Intent:`, tautology, own-module mock, tombstone | §Tests below, one check each | HIGH (a, b); MEDIUM (c, d) | Declare; literal from an independent source; mock at the frontier; delete at closure |
| S4 | Stub, unread parameter, port with one adapter | `grep -nE 'NotImplementedError\|^\s+pass$'`; ruff `ARG`; a Protocol with one implementer (`test_protocols_have_two_adapters`) | HIGH | Delete until the second caller appears |
| S5 | Layer over the old path; a second path | `--stat` adds only; `_v2\|_legacy\|_old`; `if legacy`; a swallowing `try/except`; a wrapper that delegates | HIGH (bug-surface) | Replace, don't layer; delete the old path in the same diff |
| S6 | SPEC/TASKS over the ceiling, or codes outside FR/AC/T- | `wc -c SPEC.md TASKS.md` against `DADAIA.md` §6.7; `grep -oE '\b[A-Z]{1,4}-?[0-9]{1,3}\b' \| sort -u` | MEDIUM | Split the candidate; rename to glossary terms |
| S7 | Acronym or generic name | a term outside the repo's `CONTEXT.md`; `Manager\|Helper\|Utils\|data\|result\|temp` in a new name | LOW | A domain name |
| S8 | File outside the canon | `git diff --name-status \| grep '^A'` against the root whitelist, the specs canon, the `.dadaia/` canon; `*.bak`, `SUMMARY.md`, `NOTES.md` | HIGH | Delete, or move to its home |
| S9 | Commit outside the six shapes; surviving branch | `git log --stat` against `dd-gitflow-default` §3a; `git branch -r --merged` | MEDIUM | Rewrite the series before the push; tag and delete |
| S10 | Duplicated rule; surviving handoff; provenance in a skill | an identical paragraph in two files (read — the behavior-map hashes, it never reads prose); `find .dadaia/handoff -mtime +30`; "renamed from", "formerly", `v0.` in a `SKILL.md` | MEDIUM | One home; delete |

## Tests (S3)

- S3a — no `Intent:`: `git diff --name-only -- tests | xargs grep -L 'Intent:'`; HIGH; declare, or refuse admission.
- S3b — tautology: expected computed by the code's own expression, `assert f(x) == f(x)`, a constant vs itself; HIGH; an independent literal.
- S3c — own-module mock: `patch\(.dadaia_workspace\.|MagicMock\(\)` in the diff, `assert_called` on an own collaborator; MEDIUM; mock at the frontier.
- S3d — tombstone/change-detector: a `removed|retired|no_longer|legacy` name, an absence assertion, a grep over source text; MEDIUM; dies at closure.

## Verdict rule

- A diff that adds an S4, S5 or S8 finding grows the bug surface: Axis 3 answers "increased" until the finding is gone.

## Reporting

- One finding per signal hit: `file:line`, the signal id, the fix direction — never code.

## Readers

- `code-reviewer` — all ten, on every review.
- `qa-engineer` — §Tests (S3), for curation verdicts.
- `software-architect` — S4/S5, for the root-cause and fidelity gates.
- `project-auditor` — all ten over the audit window (`dd-audit-project`, pillar 2, "Slop readout").
- Ratchets: V31-V34 pin the counts (`tests/contract/test_test_suite_ratchets.py`, `tests/contract/test_slop_ratchets.py`); V35 is the audit readout.
