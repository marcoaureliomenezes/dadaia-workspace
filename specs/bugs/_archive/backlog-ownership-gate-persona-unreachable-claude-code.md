---
name: backlog-ownership-gate-persona-unreachable-claude-code
status: Closed
resolved_in: 0.1.7 (rc-3, T-017-21..28)
closed: 2026-06-09
severity: HIGH
reported: 2026-06-08
surface: sdd-spec-gate.sh (backlog-ownership branch) + dadaia backlog CLI
session_id: null
---

**Resolution (0.1.7 rc-3, 2026-06-09):** Closed by removing the backlog-ownership persona gate
entirely. The persona requirement was unsatisfiable by the legitimate owner in *every* harness
(this Claude-Code analog confirmed the sibling Codex bug's root cause via live REPRO 1–3), so
rather than add a reachable persona channel, rc-3 makes `specs/backlog/**` a plain
ADDITIVE-allow path and re-expresses ownership as a PM coordination convention (rule:
`backlog-ownership`). The legitimate owner — and any agent — can now author backlog with the
Write tool, no env var, no pointer. The only deterministic lock is the single-session lease.
Sibling: `codex-dispatched-agent-persona-not-propagated-to-sdd-gate.md` (same fix).

**Symptom:** Under Claude Code, `project-manager` — the *sole authorized backlog
author* (rule: `backlog-ownership`) — cannot write or edit any `specs/backlog/**`
file. Every Write/Edit is blocked with:

```
[BACKLOG OWNERSHIP ERROR] writer persona unresolved — only project-manager may
write specs/backlog/. Set DADAIA_AGENT_PERSONA=project-manager (the owning role),
or record it in the session pointer .dadaia/sessions/runtime/<session>.persona,
and retry (rule: backlog-ownership).
```

Both escape hatches the error advertises are **unreachable** by an agent running
under Claude Code:

1. **`DADAIA_AGENT_PERSONA` env var** — the gate (`sdd-spec-gate.sh:133`) reads it
   from the environment of the process that spawns the PreToolUse hook (the Claude
   Code harness). An agent can only `export` it inside a transient `Bash` *tool*
   subshell, which is a separate short-lived process; the value never reaches the
   harness process, so the hook never sees it.
2. **`.persona` session pointer** — no `dadaia` CLI verb writes
   `.dadaia/sessions/runtime/<session>.persona` (verified: the only reference to
   `.persona` in the package is the gate reader itself; `context bind`, `backlog new`,
   etc. do not write it). The agent writing it itself is — correctly — blocked: it is
   the exact SEC-01 confused-deputy persona-pointer forgery the gate is designed to
   prevent (`sdd-spec-gate.sh:122`), and Claude Code's auto classifier also denies it.

Net effect: the persona requirement is **un-satisfiable** by the legitimate owner
in this harness. `dadaia backlog new <slug>` succeeds (the CLI is gate-trusted and
creates the stub), but the agent then cannot fill the stub — every follow-up
Write/Edit re-trips the same persona gate. The backlog becomes effectively
read-only for everyone, including its sole owner.

**Repro:**
1. In a Claude Code session acting as `project-manager`, no `DADAIA_AGENT_PERSONA`
   pre-set in the harness env, no bound session.
2. `dadaia backlog new my-epic --specs-dir repos/<ctx>/specs` → `[ok] created`.
3. Write/Edit any content into `specs/backlog/my-epic.md`.
4. Blocked with `[BACKLOG OWNERSHIP ERROR] writer persona unresolved`.
5. Try the advertised remedies: exporting `DADAIA_AGENT_PERSONA` in a Bash tool call
   does not affect the hook; writing the `.persona` pointer is blocked (SEC-01 +
   auto-classifier deny).

**Expected:** The sole authorized backlog owner must have at least one
agent-reachable, non-forging way to author backlog content. Candidate fixes:
- (a) `dadaia backlog new` (and/or a new `dadaia backlog write/set`/`context bind
  --persona`) records the persona pointer atomically via the gate-trusted CLI, so a
  follow-up agent Write is authorized; OR
- (b) `dadaia backlog new`/`edit` accepts a `--content`/`--from-file` flag and writes
  the full body through the CLI (gate-trusted path), so the agent never needs the
  Write tool on `specs/backlog/**`; OR
- (c) the harness propagates `DADAIA_AGENT_PERSONA` into the hook environment.
Whatever the fix, the gate's error message must point only at a path the owner can
actually take.

**Notes:** Sibling bug `codex-dispatched-agent-persona-not-propagated-to-sdd-gate.md`
covers the Codex dispatch analog; this is the Claude-Code backlog-ownership analog and
is broader (it blocks the *legitimate owner*, not just a dispatched sub-agent).
Environment: self-hosting dadaia-workspace instance, context `dd-chain-capture`,
Claude Code 2.1.169. No operator-local secrets involved.
