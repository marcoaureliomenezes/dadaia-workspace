# SLOP.md — detection signals

Disclosed sibling of [`SKILL.md`](SKILL.md), read inside Axis 1 (Standards). The definition
is one line: slop is what passes the deletion test without loss. Each signal is a
labelled judgement call with the command that makes it verifiable in the diff.

## Signals

| # | Signal | Verify in the diff | Severity | Fix direction |
|---|---|---|---|---|
| S1 | Comment or skill text narrating the what, the change or an id | `git diff -U0 \| grep -E '^\+\s*#.*(FR[0-9]\|T-[0-9]{3}\|ADR\|v[0-9]\.[0-9]\|added\|fixed\|changed)'`; a comment paraphrasing the next line; "renamed from", "formerly", `v0.` in a `SKILL.md` | LOW; MEDIUM above 5 hits | Delete; the why moves to the commit body or the ledger |
| S2 | Docstring over 3 lines carrying history | `git diff \| grep -c '"""'`, then read; the words bug, release, resolved, previously | LOW | Reduce to the contract |
| S3 | Test slop: tautology, own-module mock, tombstone | §Tests below, one check each | HIGH (b); MEDIUM (c, d) | Literal from an independent source; mock at the frontier; delete at closure |
| S4 | Stub, unread parameter, port with one adapter | `grep -nE 'NotImplementedError\|^\s+pass$'`; the linter's unused-argument rule; a Protocol with one implementer | HIGH | Delete until the second caller appears |
| S5 | Layer over the old path; a second path | `--stat` adds only; `_v2\|_legacy\|_old`; `if legacy`; a swallowing `try/except`; a wrapper that delegates | HIGH (bug-surface) | Replace, don't layer; delete the old path in the same diff |
| S6 | Codes outside FR/AC/T- | the V33 family check of `scripts/guards/slop.py`, families outside FR/AC/T-; SPEC/TASKS size is a recommendation, never a finding (`specs/releases/AGENTS.md`) | MEDIUM | Rename to glossary terms |
| S7 | Acronym or generic name | a term outside the repo's `CONTEXT.md`; `Manager\|Helper\|Utils\|data\|result\|temp` in a new name | LOW | A domain name |
| S8 | File outside the canon | `git diff --name-status \| grep '^A'` against the root whitelist, the specs canon, the `.dadaia/` canon; `*.bak`, `SUMMARY.md`, `NOTES.md`; `find .dadaia/handoff -mtime +1` | HIGH | Delete, or move to its home |
| S9 | Commit outside the §3a shapes; surviving branch | `git log --stat` against `dd-gitflow-default` §3a; `git branch -r --merged` | MEDIUM | Rewrite the series before the push; tag and delete |
| S10 | Second authority: a question answered in two places | a symbol, command or rule answering a PLAN §1.1 question beside its authority; a ratchet allowance key added; an identical paragraph in two files (read — the behavior-map hashes, it never reads prose) | HIGH | Consult the authority; delete the second |

## Tests (S3)

- S3b — tautology: expected computed by the code's own expression, `assert f(x) == f(x)`, a constant vs itself; HIGH; an independent literal.
- S3c — own-module mock: `patch\(.dadaia_workspace\.|MagicMock\(\)` in the diff, `assert_called` on own code; MEDIUM; mock at the frontier.
- S3d — tombstone/change-detector: a `removed|retired|no_longer|legacy` name, an absence assertion, a grep over source; MEDIUM; dies at closure.

## Lifecycle

- The deletion test applies to a file, line, comment, test, spec sentence, acronym, branch, release, rule or handoff alike.
- Slop dies in the change that finds it — never commented out, marked, archived or deferred.
- The writer proves the artifact fails the test, the reviewer applies it, the auditor measures the balance.

## Verdict rule

- A diff that adds an S4, S5, S8 or S10 finding, or a ratchet allowance key, grows the bug surface: Axis 3 answers "increased" until it is gone.
