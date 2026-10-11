# Job 5 — every refusal prints Error: and one fix: line: the raising error carries its remedy (FR15, bug <fix-line-bug>)

**Status:** Draft

Wave 1. Operator-confirmed (2026-10-11, "Registrar e corrigir no Job 5 (Recommended)"): ONE bug grouped by cause, `<fix-line-bug>` (placeholder until the main thread registers it; it correlates `context-repo-refusals-carry-no-fix-line`), fixed at every site below by the structural fix: `DadaiaError(message, fix='')` stores `.fix` and renders `message + '\nfix: ' + fix` (the pattern `SchemaVersionError` already uses, so every existing `str(error)` assert holds); `cli/_fail.fail(error, fix='')` prints the caller's `fix` only when the error carries none; the per-site `f"{e}\nfix: ..."` concatenations collapse into it; the raisers in `service.py` that embed `\nfix:` in their text pass `fix=` instead (same output). SPEC FR15/AC15.1 names three refusals; this job covers the measured set, so the main thread widens FR15 to name the grouped bug.

Measured no-fix sites (in-process CliRunner on temp workspaces, the define tree's code, never the live instance; 40 `fail(` calls in `cli/`, 28 always print a fix line):
- `context.py:397` `context repo add` with an invalid slug (`InvalidContextNameError`); with a different URL and with a slug owned by another context (`AssociatedRepoConflictError`); with the context's own main slug (becomes the idempotent no-op, AC15.2).
- `context.py:433` `context repo remove` of an unregistered slug (`AssociatedRepoNotFoundError`).
- `context.py:316` `context baseline` and `:331` `context dead` when git fails (`GitSyncError`, raised by `git_subprocess.py`); `:300` `context alive` has the same raiser class.
- `import_.py:35` `dadaia import` of a missing file, a file that is not JSON, and one without the export schema (plain `ValueError`s; the remedy is to run `export`, which sits in the text, not on a `fix:` line).
- `reports.py:90` bare `reports validate`; `reports.py:114` a missing file.
- `init.py:164` `WorkspaceVenvBootstrapError` (8 raisers in `python_env.py`, one remedy: re-run init).
- `specs.py:58` the two-tier `ARCHITECTURE.md` refusal (`UpgradeRefused`); `specs.py:163` prints `Operator action:` without the `fix:` label.
- `_specs_resolution.py:89` "Could not resolve specs_dir" (reached by `specs init`, `upgrade`, `doctor`).
- Also, `create`'s associated-repo conflict maps to `context list` through `create_fix` (a fix line that clears nothing, AC15.1).

Because the remedy of a git failure or a venv failure is the verb's own retry, those sites pass the caller `fix` (`fail(e, fix_line(...))`); the repo-registry errors carry theirs at the raiser.

- Test-side first: T1, T2, T3 in parallel; then T4; then T5, T6, T7, T8 in parallel (disjoint `W:`).
- T3 edits the one existing case that the operator's ruling contradicts (`A17.3-main-repo-slug`, refusal → no-op); the commit body says so, and no other assert is rewritten.
- Commit bodies carry `git grep -n -E 'fail\((e|exc|f?\")' -- dadaia_workspace/cli` with the hit counts before and after, and the final list of sites that still pass no fix with the reason each one cannot (target: none).
- Net production lines ≤ 0 for the job.
- Ledger transitions of this job's bugs (`bugs.py resolve`) are made at the Reconciliation, which owns `specs/bugs/BUGS.jsonl`; this job's fix commits echo the Phase 0 block.

Tasks: 8 (1 jr, 7 sr). `who` names the dispatched role (SPEC FR5 of rc-13, `dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J5.T1 | sr | AC15.1 | `tests/cli/commands/test_cli_refusals_carry_a_fix.py` | RED, integration: one parametrised case per measured site above (17 repros on temp workspaces, one of them a fix that clears nothing): exit 1, `Error:` first, exactly one `fix:` line, and for the `create` conflict a fix naming the right recovery. New file, owner `test_cli_refusals_carry_a_fix.py` |
| J5.T2 | sr | AC15.1 | `tests/core/test_exceptions__fix.py` | RED, unit: `DadaiaError('m', fix='f')` has `.fix == 'f'` and `str()` equal to `m` + newline + `fix: f`; without `fix` the text is `m`; `SchemaVersionError` keeps its two fields and text; `fail(error, 'x')` prints `x` only when the error has no `fix`. New file, owner `test_exceptions__fix.py` |
| J5.T3 | sr | AC15.2 | `tests/cli/commands/test_context__cli_context_repo_verbs.py` | RED, integration: `context repo add foo foo-repo` (the context's own main slug) exits 0 and leaves the record unchanged; the `A17.3-main-repo-slug` refusal case becomes the no-op case, by the operator's ruling; the other refusal cases keep their asserts. Owner that file |
| J5.T4 | sr | AC15.1 | `dadaia_workspace/core/exceptions.py`, `dadaia_workspace/cli/_fail.py` | REBUILD: `DadaiaError.__init__(message, fix='')`, `SchemaVersionError` through it; `fail(error, fix='')`; `AssociatedRepoNotFoundError` and `AssociatedRepoConflictError` carry `fix` at their raisers. Owner T2 |
| J5.T5 | sr | AC15.1, AC15.2 | `dadaia_workspace/features/spec_context/service.py` | every raiser that embeds `\nfix:` passes `fix=` (output unchanged); the repo-registry raisers carry their remedy (different URL: `context repo remove`; unregistered slug: `context show`; foreign owner and invalid slug: `Operator action:` naming the allowlist or the owning context); delete the own-main refusal in `add_repo` (re-adding the main slug returns the context unchanged). Owners T1, T3. After T4 |
| J5.T6 | sr | AC15.1 | `dadaia_workspace/cli/commands/context.py` | collapse the `f"{e}\nfix: …"` sites into `fail(e, fix)`; `create_fix` keeps only the cases the raiser cannot know (the clone URL, the name taken) and drops its `AssociatedRepoConflictError` branch; `alive`, `baseline` and `dead` pass the verb's retry line for a git failure. Owner T1. After T4, T5 |
| J5.T7 | sr | AC15.1 | `dadaia_workspace/cli/commands/init.py`, `dadaia_workspace/cli/commands/specs.py`, `dadaia_workspace/cli/commands/reports.py`, `dadaia_workspace/cli/commands/ci.py`, `dadaia_workspace/cli/commands/import_.py`, `dadaia_workspace/cli/_specs_resolution.py` | the same collapse in the six other files; `import_.py` passes `fix_line(root, 'export')` for the three `ValueError` refusals; `init.py:164` passes `fix_line(root, 'init', …)`; `specs.py:163` and `_specs_resolution.py:89` print the `fix:` label; `reports validate` bare call and missing file pass their fix. Owner T1. After T4 |
| J5.T8 | jr | AC15.1 | `dadaia_workspace/features/migrate/upgrade.py` | `UpgradeRefused` derives `DadaiaError` and its two-tier refusal passes a `fix` (rewrite the heading, then re-run); the first refusal passes its existing fix as `fix=`. Owner T1; the upgrade tests stay green unedited. After T4 |
