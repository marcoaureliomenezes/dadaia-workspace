# SPEC: v0.1.20 — Residual drift/stale-doc polish

**Status:** Aprovado
**Release ID:** v0.1.20
**Owner:** product-engineer
**Created:** 2026-06-25
**Branch:** `feature/pi-operational-v1` (continues the unmerged stack)

## 1. Problem

The v0.1.19 final zero-drift re-audit returned **CONFIRMED — zero unresolved
memory↔implementation drift**, but flagged three residual polish items ("operator's
call") that fall under the operator's standing "no dead/stale code, documentation and
specs" mandate. They are pure documentation/severity-word corrections — zero behavior
change — but the workspace target is literal zero drift, so they are fixed here rather
than left.

## 2. Scope

- **D1 (LOW, memory):** `specs/memory/product/sdd/specs-doctor.md` TREE-4 row states
  severity `ERROR`; the code emits `Severity.WARNING`
  (`dadaia_workspace/features/specs/doctor.py:1987`). Correct the severity word
  (the `--fix`/auto-fix policy is already correct).
- **D2 (INFO, code docstring):** `dadaia_workspace/features/specs/doctor.py` `fix()`
  docstring (~:577) claims it "Resolves TREE-3 (render missing memory HTML from Jinja
  templates) and TREE-4". TREE-3 is no longer fixable and there is no Jinja/HTML path
  (`.md` is canonical source). Correct the docstring to reflect TREE-4-only auto-fix.
- **D3 (INFO, code comment):** `dadaia_workspace/container.py` `build_agent_runtime`
  docstring (~:316) calls Claude SDK and OpenCode "documented stubs" and predates PI.
  The Claude SDK adapter body is real (only its default `query_fn` transport is
  deferred); PI is a live adapter. Correct the comment to name the live adapters
  (Codex, PI, Claude-SDK-with-deferred-transport) vs the OpenCode stub.

Out of scope: anything behavioral; the deferred WS-PI-4 / RPC / SDK items.

## 3. Acceptance criteria

1. `dadaia specs doctor` exit 0; `lint-memory-atoms.py` 30 OK / 0 ERROR.
2. `dadaia ci preflight` green (no behavior change → tests unaffected; ruff/mypy pass).
3. `dadaia public doctor` exit 0 with `[ok] public-privacy`.
4. specs-doctor.md TREE-4 severity matches code (WARNING); the two code docstrings
   match their implementations.
5. Security APPROVE keyed to the pushed tip; CI green.

## 4. Non-goals

No behavior change, no test change, no dependency change.
