# SLOP.md — the slop definition and its detection signals

Disclosed sibling of [`SKILL.md`](SKILL.md), read inside Axis 1 (Standards).

Slop is any artifact — code, test, text, record, claim or classification — that has the shape of finished work without the evidence of it: made to look right, not shown to be right. Two tests:

- The deletion test: delete the unit; does complexity vanish or reappear across callers? It applies to a file, line, comment, spec sentence, acronym, branch, release, rule or handoff alike.
- The evidence test: is the claimed result shown by a run, a `path:line` or a sha?

Each signal is a labelled judgement call with the command that makes it verifiable in the diff.

## Signals

| # | Signal | Verify in the diff | Severity | Fix direction |
|---|---|---|---|---|
| S1 | Comment or skill text narrating the what, the change or an id (the root map §1 docstring sentence) | added comments carrying an id or a narration verb (command below); a comment paraphrasing the next line; "renamed from", "formerly", `v0.` in a `SKILL.md` | LOW; MEDIUM above 5 hits | Delete; the why moves to the commit body or the ledger |
| S2 | A docstring past the root map §1 docstring sentence | quote count in the diff (command below), then read; the words bug, release, resolved, previously | LOW | Reduce to the contract |
| S3 | Test slop: tautology, own-module mock, tombstone, test smells | §Tests below, one check each | HIGH (b); MEDIUM (c, d, e-h) | Literal from an independent source; mock at the frontier; root map §1 for removal |
| S4 | Stub, unread parameter, port with one adapter | stubs and bare `pass` bodies (command below); the linter's unused-argument rule; a Protocol with one implementer | HIGH | Delete until the second caller appears |
| S5 | Layer over the old path; a second path | `--stat` adds only; legacy names (command below); `if legacy`; a swallowing `try/except`; a wrapper that delegates | HIGH (bug-surface) | Replace, don't layer; delete the old path in the same diff |
| S6 | Codes outside FR/AC/`J<n>.T<k>` | numbered families outside FR/AC/`J<n>.T<k>` in the diff; SPEC/job-file size is a recommendation, never a finding (`specs/releases/AGENTS.md`) | MEDIUM | Rename to glossary terms |
| S7 | Acronym or generic name | a term outside the domain names the repo's specs already use; generic words in a new name (command below) | LOW | A domain name |
| S8 | File outside the canon | added files (command below) against the root whitelist, the specs canon, the `.dadaia/` canon; `*.bak`, `SUMMARY.md`, `NOTES.md`; stale handoffs (command below) | HIGH | Delete, or move to its home |
| S9 | Commit outside the §3a shapes; surviving branch | `git log --stat` against `dd-gitflow-default` §3a; `git branch -r --merged` | MEDIUM | Rewrite the series before the push; tag and delete |
| S10 | Second authority: a question answered in two places | a symbol, command or rule answering a PLAN §1.1 question beside its authority; a ratchet allowance key added; an identical paragraph in two files | HIGH | Consult the authority; delete the second |
| S11 | Unverified claim: "fixed", "unused", "pre-existing", "done" or a count with no run, `path:line`, grep or sha beside it | read each claim in the diff, commit body and report; the evidence named is re-run or opened | HIGH | Run it and cite the output, or delete the claim |
| S12 | Symptom fit: the fix covers the reported case and leaves the siblings of its pattern unswept | grep the fixed pattern across the repo; each leftover hit; a special case on the reported value | HIGH (bug-surface) | Fix the shared cause once; sweep every hit |
| S13 | Dishonest label: a REBUILD that is an iteration on the old unit, a "structural" fix that is a patch, a KEEP that grew | compare the commit label and the PLAN verdict with `--stat` and the old unit's surviving lines | HIGH | Relabel to what the diff does, or do the rebuild |
| S14 | Eval tuned until it passes: the prompt, threshold, fixture or expected value edited after a red run | `git log -p` on the eval and its expected values; a loosened threshold; a case dropped or reworded | HIGH | Restore the eval; fix the artifact it judges |

## Verify commands

`<base>` is the base of the reviewed range; the diff is committed, so a bare `git diff` prints nothing.

```
S1: git diff -U0 <base>...HEAD | grep -E '^\+\s*#.*(FR[0-9]|J[0-9]+\.T[0-9]+|ADR|v[0-9]\.[0-9]|added|fixed|changed)'
S2: git diff <base>...HEAD | grep -c '^\+.*"""'
S4: git diff -U0 <base>...HEAD | grep -nE '^\+.*NotImplementedError|^\+\s+pass$'
S5: git diff -U0 <base>...HEAD | grep -nE '^\+.*(_v2|_legacy|_old)'
S7: git diff -U0 <base>...HEAD | grep -nE '^\+.*(Manager|Helper|Utils|data|result|temp)'
S8: git diff --name-status <base>...HEAD | grep '^A'
S8: find .dadaia/handoff -mtime +1
```

## Tests (S3)

- S3b — tautology: expected computed by the code's own expression, `assert f(x) == f(x)`, a constant vs itself; HIGH; an independent literal.
- S3c — own-module mock: a patch target inside the repo's own package or a bare `MagicMock()`, `assert_called` on own code; MEDIUM; mock at the frontier.
- S3d — tombstone/change-detector: a `removed|retired|no_longer|legacy` name, an absence assertion, a grep over source; MEDIUM; root map §1.
- S3e — conditional logic in a test: `if`, `for` or `try` steering which assert runs; MEDIUM; one case per branch.
- S3f — assertion roulette: several unrelated asserts in one test, no message to tell which failed; MEDIUM; one behavior per test.
- S3g — mystery guest: the test reads a file the test does not show; MEDIUM; a live repo file is policy, a guard case.
- S3h — assert on law text: the wording of a law or skill file; MEDIUM; assert behavior.

## Lifecycle

- Slop dies in the change that finds it — never commented out, marked, archived or deferred.
- The writer proves the artifact fails either test, the reviewer applies it, the auditor measures the balance.

## Verdict rule

- A diff that adds an S4, S5, S8, S10 or S12 finding, or a ratchet allowance key, grows the bug surface: Axis 3 answers "increased" until it is gone.
