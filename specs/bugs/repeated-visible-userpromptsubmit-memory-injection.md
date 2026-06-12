---
title: repeated-visible-userpromptsubmit-memory-injection
severity: Critical
opened: 2026-06-07
session_id: null
status: Closed
resolved_in: 0.1.7 (rc-4, T-017-30)
---

**Resolution (0.1.7 rc-4, T-017-30):** `ctx-inject.sh` restructured so the once-per-session sentinel (keyed on the harness-native session id — CLAUDE_CODE_SESSION_ID / Codex stdin-JSON session_id, no DADAIA_SESSION_ID dependency, ADR-2) guards the ENTIRE injection. First prompt injects context line + dispatcher preflight + memory once; every subsequent prompt in the same session emits NOTHING. Regression test `test_ctx_inject_injects_once_then_silent_same_session`.


# Bug: repeated-visible-userpromptsubmit-memory-injection

## Description

Every prompt in a Codex session visibly prints the full dadaia workspace memory bootstrap:

```text
UserPromptSubmit hook (completed)
hook context: [dadaia-workspace]

=== workspace memory (tech + catalog) ===
...
=== end memory bootstrap ===
```

This is a critical context-engineering and UX defect. The hook may fire on every
`UserPromptSubmit`, but the full memory bootstrap must not be emitted on every prompt.
The intended behavior is one deterministic bootstrap per logical session, then silent
or minimal per-prompt behavior.

## Impact

- Pollutes the operator transcript on every prompt.
- Wastes thousands of tokens per turn.
- Pushes static memory into recency repeatedly, competing with the current operator intent.
- Makes debugging and prompt reading noisy.
- Contradicts the product's own "first-message sentinel guard" claim.
- Creates distrust in the harness because hook output is visible when it should be quiet.

## Evidence

- `.codex/hooks.json:37-46` wires `UserPromptSubmit` to
  `DADAIA_HOOK_OUTPUT=codex-json .dadaia/scripts/ctx-inject.sh`.
- `dadaia_workspace/public/scripts/ctx-inject.sh:110-126` chooses
  `CLAUDE_CODE_SESSION_ID`, then `OPENCODE_SESSION_ID`, else `$$`.
- Codex does not populate either checked variable in the observed session, so the script
  falls back to the hook shell PID. Each prompt runs the hook in a new shell process, so
  the sentinel path changes each prompt.
- Observed sentinel files in `.dadaia/tmp/` include many PID-shaped files:
  `ctx-inject-fired-132423`, `ctx-inject-fired-133175`,
  `ctx-inject-fired-133564`, etc.
- `dadaia_workspace/public/scripts/ctx-inject.sh:83-87` writes the context line before
  the sentinel check, so even the "already fired" path is not fully silent.
- `specs/memory/tech-stack.md` describes a first-message sentinel guard, not repeated
  full bootstrap injection.

## Steps to reproduce

1. Start a Codex session inside the dadaia workspace with project hooks trusted.
2. Submit any prompt.
3. Observe visible `UserPromptSubmit hook (completed)` output containing the full
   workspace memory block.
4. Submit a second prompt in the same logical Codex conversation.
5. Observe the full memory block printed again.
6. List `.dadaia/tmp/ctx-inject-fired-*` and observe new PID-based sentinels.

## Root cause hypothesis

The script was designed around Claude/OpenCode session identifiers and uses `$$` as the
fallback sentinel key. In Codex, that fallback is per hook subprocess, not per logical
conversation. The hook is deterministic in the wrong dimension: it fires every prompt,
but the idempotence key is unstable.

There is also a design bug: the hook output channel is user-visible in this Codex UI.
Full bootstrap context should not be printed to the transcript after the first session
bootstrap, and possibly not visibly printed at all.

## Acceptance criteria for fix

- Codex: two consecutive prompts in one logical session produce the full memory bootstrap
  exactly once.
- Codex: second and later prompts produce no visible full hook dump and no repeated
  `=== workspace memory` block.
- `ctx-inject.sh` no longer falls back to raw `$$` for Codex logical-session idempotence.
- If Codex supports `SessionStart` for this project hook contract, full bootstrap moves
  there. If `UserPromptSubmit` remains the fallback, it uses a proven stable session key.
- The already-fired path emits empty output or a tiny non-visible/no-op JSON payload; it
  must not emit `[dadaia-workspace]` spam.
- Tests assert bootstrap markers appear at most once per session for Codex.
- Tests assert hook output is quiet/minimal on repeated prompts.
- Memory/docs distinguish "hook may fire every prompt" from "full memory payload injects
  once per logical session".

## Related

- `specs/backlog/codex-context-hook-and-workflow-enforcement-hotfix.md`
- `specs/bugs/codex-workflow-dispatch-not-deterministically-enforced.md`
- Existing broader backlog: `specs/backlog/full-codex-compatibility.md`
