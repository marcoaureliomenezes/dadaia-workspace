# Re-seed the Codex login secret

Audience: the operator. Every step that touches the secret is yours, from a real terminal. Agents never create, copy, print or persist it.

## When it is due

The `eval` Codex leg went red at the secret preflight, or printed an authentication error. The Codex leg logs in with the ChatGPT login stored in the GitHub Environment secret `CODEX_AUTH_JSON` (Environment `evals`). The login's refresh token rotates, so the stored copy goes stale.

Consequence: a CI refresh can rotate the token and log your local Codex out. Recovery is two steps: log in again locally, then re-seed.

## Steps

1. Log in again locally, then check it: `codex login`, `codex login status`.
2. Set the secret from `~/.codex/auth.json`, read from standard input so the value never shows on a command line:

   `gh secret set CODEX_AUTH_JSON --env evals -R marcoaureliomenezes/dadaia-workspace < ~/.codex/auth.json`

3. Verify (names and dates only): `gh secret list --env evals -R marcoaureliomenezes/dadaia-workspace`. The `CODEX_AUTH_JSON` date must be new.
4. Re-run only the red legs: `gh run rerun <run-id> --failed -R marcoaureliomenezes/dadaia-workspace`, or dispatch again: `gh workflow run eval.yml --ref <work-branch> -R marcoaureliomenezes/dadaia-workspace`.

To keep your own login out of CI's reach, log in with a separate `CODEX_HOME` directory outside the workspace (`CODEX_HOME=<dir> codex login`) and read that directory's `auth.json` in step 2.

## How the leg uses it

Harbor reads the file through `CODEX_AUTH_JSON_PATH` (or `CODEX_FORCE_AUTH_JSON=1` for `~/.codex/auth.json`) and writes it to `/tmp/codex-secrets` in the container, outside `/logs`.

## Never

Print the file, paste it in an issue or a commit, upload it, or log in with the same account in a tool that refreshes it unless you accept the logout above.
