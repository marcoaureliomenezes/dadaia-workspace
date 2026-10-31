# Re-seed the Codex login secret

Audience: the operator. Every step that touches the secret is yours, from a real terminal. Agents never create, copy, print or persist it.

## When it is due

The `eval` Codex leg went red at the secret preflight, or printed an authentication error. The leg logs in with the ChatGPT login stored in the GitHub Environment secret `CODEX_AUTH_JSON` (Environment `evals`). Its refresh token rotates, so the stored copy goes stale. A dedicated login, used by nothing but CI, keeps your own Codex session out of that rotation.

## Steps

1. Log in with a dedicated `CODEX_HOME` outside the workspace, then check it: `CODEX_HOME=<dir> codex login`, `CODEX_HOME=<dir> codex login status`.
2. Set the secret from `<dir>/auth.json`, read from standard input so the value never shows on a command line:

   `gh secret set CODEX_AUTH_JSON --env evals -R marcoaureliomenezes/dadaia-workspace < <dir>/auth.json`

3. Verify (names and dates only): `gh secret list --env evals -R marcoaureliomenezes/dadaia-workspace`. The `CODEX_AUTH_JSON` date must be new.
4. Re-run only the red legs: `gh run rerun <run-id> --failed -R marcoaureliomenezes/dadaia-workspace`, or dispatch again: `gh workflow run eval.yml --ref <work-branch> -R marcoaureliomenezes/dadaia-workspace`.

## Never

Print the file, paste it in an issue or a commit, upload it, or log in with the same account in a tool that refreshes it.
