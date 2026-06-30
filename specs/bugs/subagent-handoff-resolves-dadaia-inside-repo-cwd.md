---
name: subagent-handoff-resolves-dadaia-inside-repo-cwd
status: Closed
severity: MEDIUM
reported: 2026-06-24
surface: handoff emission / .dadaia root resolution when cwd is inside a repo
session_id: null
---

> **Recurrence + escalation (2026-06-27, v0.1.31 implementation).** Hit again: two
> `product-engineer` handoffs landed in `repos/dadaia-workspace/.dadaia/handoff/...`. This
> time the repo-internal `.dadaia/` actively **broke a test** — `resolve_mypy_cache_dir`
> walked up, found the stray in-repo `.dadaia/`, mistook the repo for the workspace root, and
> resolved the mypy cache to `repos/dadaia-workspace/.dadaia/tmp/ci-preflight/mypy-cache`
> (inside the repo), failing
> `tests/unit/features/ci_preflight/test_no_pollution.py::test_mypy_cache_dir_redirected_outside_repo`.
> So this is no longer a cosmetic stray dir: it corrupts cache-dir resolution and fails the
> repo-hygiene gate. Severity raised LOW → MEDIUM. Fix direction: subagents must resolve the
> handoff/`.dadaia` root by walking UP to the true workspace root (the dir whose parent is not
> itself a repo / that holds the canonical `.dadaia`), never cwd-relative; and
> `resolve_mypy_cache_dir` should ignore a repo-internal `.dadaia/` when locating the workspace.

**Symptom:** A subagent (qa-engineer) dispatched to operate inside
`repos/dadaia-workspace/` emitted its handoff to
`repos/dadaia-workspace/.dadaia/handoff/dadaia-workspace/<ts>-...handoff.json` — i.e. it
created a **`.dadaia/` directory INSIDE a repo**. Per the Workspace Root Law and the
repo-cleanliness rule, `.dadaia/` is workspace-level ONLY; a repo-internal `.dadaia/` is a
hard violation that corrupts workspace-vs-repo boundary detection. The earlier alpha-1 /
alpha-2 handoffs correctly landed at the workspace-root `.dadaia/handoff/`.

**Repro:** Dispatch any agent with its working directory set to `repos/<slug>/` and have it
emit a handoff using a cwd-relative `.dadaia/handoff/<context>/` path. The handoff lands in
`repos/<slug>/.dadaia/` instead of the workspace-root `.dadaia/`.

**Expected:** Handoff/report/`.dadaia` paths always resolve to the **workspace root**
(walk up until the directory containing `.dadaia/` / the workspace markers), never
cwd-relative when cwd is inside a repo. No `.dadaia/` is ever created inside a repo.

**Notes:** No deterministic guardrail catches this — the root-whitelist PreToolUse hook only
blocks new top-level *workspace-root* entries, and a `.dadaia/` nested under `repos/<slug>/`
is not a root entry; the repo-cleanliness rule is discipline-only. Mitigations to consider:
(a) the `dadaia-handoff-emitter` skill / agent guidance must resolve workspace root explicitly
(not cwd-relative); (b) a doctor/repo-hygiene check that fails on any `repos/*/.dadaia/`;
(c) optionally a PreToolUse guard blocking writes under `repos/*/.dadaia/`. Encountered during
release `multiharness-engine-v0116` alpha-3; handoff was relocated to the workspace-root
`.dadaia/handoff/dadaia-workspace/` and the stray repo-internal `.dadaia/` removed. No
operator-local paths/secrets in this record.

## Resolution

Fixed in v0.1.40 alpha-1 T7.

Root cause: runtime artifact code still had multiple cwd-relative workspace-state
resolvers. Codex had already gained a local helper after earlier Layer-2 fixes, but PI
still recovered handoffs from `self._config.cwd / ".dadaia"`, and fake review/bug paths
also wrote relative to `Path.cwd()`. That left the same root cause alive after related
Codex bugs were marked closed.

Fix:

- Added `infrastructure.headless_adapter_base.workspace_state_root()` as the shared
  resolver for Layer-2 runtime state. It walks upward to an initialized workspace marker
  and skips partial repo-local `.dadaia` directories.
- Replaced Codex's local helper with the shared helper.
- Updated PI written-handoff recovery to read from the workspace-root `.dadaia/handoff`
  and return workspace-relative refs.
- Updated fake runtime handoff/bug/create artifact writes to resolve through the same
  helper.

Evidence:

- Added PI and Codex contract tests that run from `repos/dadaia-workspace/` with a
  misleading repo-local `.dadaia/`; both recover the workspace-root handoff and do not
  create `repos/<slug>/.dadaia/handoff`.
- Focused 66-test validation run passed.
