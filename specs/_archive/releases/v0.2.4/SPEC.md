# Spec: Hotfix Release - v0.2.4

> **Status:** Aprovado
> **Release ID:** v0.2.4
> **Patches release:** v0.2.3
> **Severity:** HIGH
> **Owner:** product-engineer
> **Created:** 2026-07-14

## Incident summary

Projected Python hooks recreate `__pycache__` and `.pyc` files inside a managed repository
when the hook runs with that repository as its current directory. This violates the
repository hygiene contract during the act of enforcing it. Source event:
`hook-runtimes-create-repo-bytecode` in `specs/bugs/bugs.jsonl`.

## Affected memory features

- `public-asset-distribution.md` - projected hook launchers must be repository-clean.
- `harness-claude-code.md` - Claude Python hook command contract.
- `harness-codex.md` - Codex wrapper command contract.
- `harness-pi.md` - PI TypeScript subprocess command contract.

No memory update is required: all four atoms already prohibit repository-local generated
artifacts. The implementation is drifting from that current contract.

## Root cause

`runtime_config._hook_cmd()` and `WorkspaceService._canonical_hook_command()` emit
`<python> -m <module>`, generated Codex wrappers emit `exec "$PYTHON_BIN" -m <module>`,
and the PI extension invokes Python with `-m`. None uses Python's `-B` flag or an
equivalent bytecode suppression environment. Python therefore writes import bytecode
relative to the source package whenever the repository is first on `sys.path`.

## Fix scope

**PLAN.md:** Required - the fix spans the three cross-harness hook launch paths and their
projection/contract tests.

Add `-B` to every projected hook Python invocation, add an executed wrapper regression that
runs from a source-shaped repository and asserts no bytecode is created, update static
projection assertions, restage/install public assets, and verify all three harness surfaces.

## Rollback plan

Revert the v0.2.4 implementation commit. This restores the former launch commands without
changing hook payloads, state schemas, or gate semantics.

## Acceptance + smoke test

- [x] Claude hook commands contain `python -B -m`.
- [x] Every Codex hook wrapper executes `python -B -m`.
- [x] The PI extension invokes Python with `-B`, `-m`, and the same hook module.
- [x] Executing the Codex pre-gate wrapper from a source-shaped repo creates no
  `__pycache__` directory or `.pyc` file.
- [x] Focused projection tests, public doctor, and repository hygiene scans pass.
