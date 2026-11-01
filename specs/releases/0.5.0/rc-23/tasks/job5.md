# Job 5 — docs: the Codex re-seed procedure (FR6, AC6.2)

**Status:** Draft

Paths are repository-relative to `repos/dadaia-workspace/`. Design and evidence: PLAN section 1 (R10) and section 5 (H5). Wave 2, beside Jobs 3 and 4 (disjoint `W:`); the doc is wave 2 because the preflight error of Job 3 names its path and Job 6's leg points at it.

**Contract.** `evals/RESEED.md` is the one doc home. It states, in this order:

1. When a re-seed is due: the Codex leg's preflight failed, or a leg printed an authentication error. The cause is a rotated refresh token (SPEC section 5; measured: `last_refresh` renewed by age after 8 days).
2. How to make a dedicated login that no other tool shares: a separate `CODEX_HOME` directory outside the workspace, then the `codex login` flow in it, so the operator's own login never rotates the CI copy.
3. How to set the secret from a real terminal, never printed and never passed on a command line: `gh secret set CODEX_AUTH_JSON --env evals` reading the dedicated `auth.json` from standard input (the `gh secret set` help documents `--env` and standard input).
4. How to re-run only the red legs: `gh run rerun <run-id> --failed`, or a new dispatch of `eval.yml` on the work branch.
5. What never to do: print the file, paste it in an issue or a commit, upload it, or log in with the same account in a tool that refreshes it.

The file path appears in the Job 3 preflight error text (`evals/RESEED.md`), so the name is fixed.

**Definition of done.** Each command line in the doc was run with `--help` or `--version` against the live binary in the task's session and the result named in the commit body (a claim about a binary is checked before it is written); the doc holds no secret value, no account id and no real path of the operator; `python scripts/ci.py job` passes (about 73 s); no test reaches the file (AC6.2 has none).

| task | who | AC | `W:` | waits on | tests | outcome |
|---|---|---|---|---|---|---|
| J5.T1 | sr | AC6.2 | `evals/RESEED.md` | - | none: doc text (AC6.2) | ADD `evals/RESEED.md` per the contract; sr because every command is checked against the live `gh` and `codex` binaries before it is written |
