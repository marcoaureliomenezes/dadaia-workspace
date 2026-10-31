# Job 3 — the eval's Codex leg trusts what the eval generates (FR1, AC1.3, AC1.4)

**Status:** Draft

| task | who | AC | `W:` | owner test | outcome |
|---|---|---|---|---|---|
| J3.T1 | sr | AC1.3, AC1.4, AC1.5 | `.github/workflows/eval.yml` | none: the run on E (PLAN section 3) | harbor pinned to 0.24.0; the two trust kwargs on the Codex rows only |

Wave 2, with Jobs 1 and 2. There is no RED task: `eval.yml` has no unit seam, and its test is the proof step, which is the main thread's act. Definition of done: `python scripts/ci.py job` (it runs the eval-shape guards over the real file) and `tests/scripts/guards`.

## J3.T1

- `pipx install harbor==0.23.0` becomes `harbor==0.24.0` (the pre-mortem: the only 0.24.x; 0.25.0 changes `CODEX_HOME`, auth, the skills dir and its deps). No other `0.23` string remains in the file.
- In the `Run the task` step, before `harbor run`, build the kwargs for Codex only, then splice them. Shape, to be checked:

  ```
  extra=(); if [ "$HARNESS" = codex ]; then extra=(--ak dangerously_bypass_hook_trust=true --ak 'config={"projects":{"/workspace":{"trust_level":"trusted"}}}'); fi
  harbor run ... --ak version="$VERSION" "${extra[@]}" -k 3 -n 3 ...
  ```

  Both kwargs ride the Codex rows only: `ClaudeCodeOptions` is `extra=forbid` and Claude's `native_config=True` turns `config=` into its settings file, so a leak breaks every Claude trial.
- Verify the quoting in bash before committing: expand the array with `printf '%s\n' "${extra[@]}"` for `HARNESS=codex` (the JSON is one element, quotes intact) and for `HARNESS=claude-code` (nothing printed, and `harbor run` gets no stray empty argument). Report the output in the hand-back; no script is committed.
- Unchanged: the prune line, the eight `--retry-include` names, `--max-retries 2`, `-k 3 -n 3`, the scan and the upload steps.
- Sweep for the hand-back: `rg -n 'trust_level|dangerously_bypass_hook_trust' dadaia_workspace/` prints nothing (AC1.5); the only hits in the tree are in `eval.yml`.
- Net growth is about 3 lines, justified as the precondition ADR 0282's flip lacked.
