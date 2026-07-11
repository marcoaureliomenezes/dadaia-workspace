# SPEC — Release v0.1.77 — Central bind-resolution seam

**Status:** Aprovado
**Source:** backlog `20260709-central-bind-resolution-seam` (P0, recurrence family F2:
8 reports, 5 partial per-command fixes v0.1.47→v0.1.71, median re-report <11h); release
definition + grill corrections in `specs/backlog/candidates.md`. Sequenced after
v0.1.76 (which deleted incumbent-pointer authority and made mode self-scoped).

## Problem

The contract "a successful `dadaia context bind` is visible to every resolver-driven
command" was never fixed centrally. A partial seam exists
(`cli/_specs_resolution.py#resolve_specs_dir_for_cli`, consumed by 5 command modules:
specs/bugs/memory/migrate/newartifacts) — but NOT on it: `context show`'s private
incumbent-pointer algorithm (`cli/commands/context.py:202-260`) and ~15 lifecycle
verbs whose `--context` Typer default is the hardcoded string `"dadaia-workspace"`
passed as if explicit — the bind is never consulted (masked in this self-hosting
workspace; wrong-context in every consumer workspace).

## FRs

- **FR1 — One canonical resolution order,** implemented once in the seam module and
  consumed by every resolver-driven verb: explicit `--context`/`--specs-dir` → env
  (`DADAIA_CONTEXT`) → the session's OWN record (harness-native id; consistent with
  v0.1.76 self-scoped mode) → ancestry marker → first-ALIVE fallback. `context show`'s
  no-arg default folds into the same seam (its former incumbent-pointer rung is
  presence/own-record-based post-v0.1.76; show-only display of other sessions'
  presence is unchanged).
- **FR2 — Lifecycle `--context` defaults retired (user-visible CLI change):** the ~15
  `typer.Option("dadaia-workspace", "--context")` defaults become unset-by-default
  (`None`); unset resolves through the seam. Explicit `--context` keeps absolute
  precedence. Release notes + `--help` text say what changed.
- **FR3 — Contract test with DYNAMIC enumeration:** a Typer-app walk discovers every
  resolver-driven subcommand (no static list — a future verb is caught automatically)
  and probes per-verb that after a bare `context bind <ctx>` the verb resolves `<ctx>`
  (read-only probe path for lifecycle verbs, or the test stops at the seam boundary
  with the seam call asserted). PLUS an import-boundary contract (import-linter):
  nothing outside the seam module imports the resolution internals
  (`resolve_bound_context_name`/session-record readers).
- **FR4 — Resolution law:** per the recurrence-audit resolution law, no further
  per-command patches are accepted for family F2 — removing the seam from any verb
  fails the contract test.

## Acceptance

- After a bare `context bind <ctx>`: every resolver-driven verb targets `<ctx>`
  (dynamic-walk executed-path test); `context show` no-arg agrees.
- Grep: zero `"dadaia-workspace"` hardcoded `--context` Typer defaults in cli/.
- Import-linter: new contract keeps; full suite green; mypy --strict; doctors green;
  per-sha security APPROVE.
