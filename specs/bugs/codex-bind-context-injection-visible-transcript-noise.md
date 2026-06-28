---
name: codex-bind-context-injection-visible-transcript-noise
status: Closed
severity: MEDIUM
reported: 2026-06-27
session_id: sess_5aabaf1d
surface: Codex hooks ctx_inject / bind-triggered memory bootstrap
---

**Symptom:** After binding `dadaia-workspace`, Codex surfaces a large injected context block
in the conversation/developer stream, including dispatcher preflight and the memory catalog
digest with ranked entries:

```text
[dadaia-workspace]

=== dispatcher preflight (SDD routing) ===
...
=== workspace memory (tech + catalog) ===
...
"features": [
  { "rank": 1, ... },
  ...
]
=== end memory bootstrap ===
```

The operator experiences this as prompt noise: lots of text printed into the transcript,
with rank fields that look like unexplained output rather than hidden model context.

**Expected:** Codex context injection should be operator-quiet or visibly minimal. If a
bind-triggered memory bootstrap is needed for model behavior, it should not flood the
human transcript with the full dispatcher preflight plus catalog digest. A short status
line such as "dadaia context loaded: dadaia-workspace" would be acceptable; the detailed
memory catalog should remain model-internal or be pulled on demand.

**Root cause:** The projected Codex hooks wire both `SessionStart` and `UserPromptSubmit`
to `dadaia_workspace.hooks.ctx_inject` through `.codex/hooks.json`. The wrapper sets
`DADAIA_HOOK_OUTPUT=codex-json`, and `ctx_inject._emit()` returns the full bootstrap as
`hookSpecificOutput.additionalContext`. In this Codex UI/runtime, that additional context
is visible in the conversation/developer stream, so a mechanism intended as model context
becomes human-visible transcript spam. The catalog rank fields come from
`specs/memory/product/catalog.json` and are intentionally retained by
`ctx_inject._digest_catalog()` as part of the lean digest; they are not runtime ranking
diagnostics, but the injected JSON makes them look like unexplained prompt output.

**Important distinction:** The older bug `repeated-visible-userpromptsubmit-memory-injection`
covered full bootstrap emission on every prompt due to unstable sentinel keys. That is not
what reproduced in this session: `.dadaia/tmp/ctx-inject-fired-019f0b68-058a-7772-8370-dcc407c3d7dd`
currently records `ctx=dadaia-workspace`, and manually rerunning
`.dadaia/hooks/codex-ctx-inject` with that same `session_id` emits nothing. The live defect
here is the first bind/session bootstrap being too large and visible, not a confirmed
per-prompt sentinel failure.

**Impact:**

- Pollutes the operator transcript immediately after bind/session bootstrap.
- Makes normal task prompts hard to read and reason about.
- Spends recency/context budget on generic ranked catalog data even when the current task
  only needs one or two atoms.
- Creates confusion about whether the ranked feature catalog is a command result, agent
  output, or hidden context.

**Fix direction:** Split model context from human-visible hook status for Codex. Options to
evaluate:

1. Keep `additionalContext` tiny and make agents self-pull memory via the existing
   `memory-ctx`/Step-0 protocol.
2. Move detailed memory to a non-visible mechanism if Codex supports one for hooks.
3. Retain bind-triggered injection but compress it to context slug + 1-line memory pointer,
   with no catalog JSON in the visible transcript.

Whichever option is chosen, tests should assert that repeat prompts remain silent and that
the first post-bind visible payload is bounded and operator-readable.

## Resolution

Fixed before `v0.1.35`; verified and closed in `v0.1.35`.

Root cause: Codex displays `hookSpecificOutput.additionalContext` in the human-visible
transcript. The hook emitted the full bind-time bootstrap into that field, so dispatcher
preflight and ranked catalog JSON were visible to the operator.

Fix present in code: `ctx_inject._emit()` now routes `DADAIA_HOOK_OUTPUT=codex-json`
through `_codex_visible_payload()`, which keeps only a bounded context-loaded message and
self-pull pointers. Repeat prompts remain silent via the existing sentinel.

Evidence:

- `tests/e2e/features/test_ctx_inject_bind_boundary.py::test_codex_json_bind_injection_is_transcript_bounded_and_repeat_silent`
- `python -m pytest -q -p no:cacheprovider tests/e2e/features/test_ctx_inject_bind_boundary.py::test_codex_json_bind_injection_is_transcript_bounded_and_repeat_silent`
