---
name: subagent-handoff-resolves-dadaia-inside-repo-cwd
status: Open
severity: LOW
reported: 2026-06-24
surface: handoff emission / .dadaia root resolution when cwd is inside a repo
session_id: null
---

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
