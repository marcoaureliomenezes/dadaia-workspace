---
title: codex-dispatched-agent-persona-not-propagated-to-sdd-gate
severity: Critical / Blocker
opened: 2026-06-09
session_id: null
status: Closed
resolved_in: 0.1.7 (rc-3, T-017-21..28)
closed: 2026-06-09
---

# Bug: codex-dispatched-agent-persona-not-propagated-to-sdd-gate

## Resolution (0.1.7 rc-3, 2026-06-09)

Closed by **removing the lock**, not by building a persona-propagation bridge. The
backlog-ownership persona gate was deleted from `sdd-spec-gate.sh` (backlog is now a plain
ADDITIVE-allow path); ownership is a coordination convention in the `backlog-ownership` rule;
`.dadaia/sessions/**` stays PROTECTED, re-justified on single-session lease `.ptr` integrity
(the sole deterministic lock). Verified: the previously-blocked backlog item
`harness-agentic-entities-and-determinism-parity.md` was registered through the normal flow via
the Write tool with no env var and no pointer (rc-3 end-to-end proof); gate tests assert
backlog ALLOW regardless of persona; `.dadaia/sessions/**` writes still blocked. The Claude
analog `backlog-ownership-gate-persona-unreachable-claude-code.md` is closed by the same fix.

## Escalation (2026-06-09)

**Severity escalated to maximum: Critical / Blocker.**

This is not a minor Codex inconvenience and not an operator setup issue. It is an
architectural blocker in the dadaia-workspace development lifecycle:

- The workflow says backlog is PM-owned.
- The lead Codex session can spawn a `project-manager`.
- The spawned `project-manager` still cannot satisfy the SDD gate.
- The gate suggests manual environment/pointer workarounds.
- The operator cannot proceed fluidly from backlog -> release -> implementation -> review.

Any design that requires the operator or lead agent to manually bind environment variables per
agent is invalid for dadaia-workspace. The root cause must be traced and replaced with a
proper dispatcher/session/persona authority model.

This bug blocks the backlog item that should track the broader harness architecture work:

- intended backlog path:
  `repos/dadaia-workspace/specs/backlog/harness-agentic-entities-and-determinism-parity.md`
- intended candidates entry:
  `repos/dadaia-workspace/specs/backlog/candidates.md`

That backlog could not be registered because the very mechanism that should route the write
through `project-manager` cannot propagate PM identity into the gate.

## Claude-side reproduction + definitive root cause (2026-06-09)

**This is NOT Codex-specific. It reproduces identically under Claude Code.** The operator
asked whether "the same happens to you" — it does. Live repro against the gate
(`dadaia_workspace/public/scripts/sdd-spec-gate.sh`), no harness changes:

```
# REPRO 1 — backlog write, no persona env (what EVERY agent looks like to the hook):
echo '{"tool_name":"Write","tool_input":{"file_path":".../specs/backlog/x.md",...}}' | bash sdd-spec-gate.sh
  -> {"decision":"block","reason":"[BACKLOG OWNERSHIP ERROR] writer persona unresolved ..."}

# REPRO 2 — the advertised remedy (`export DADAIA_AGENT_PERSONA` in a Bash tool subshell):
( export DADAIA_AGENT_PERSONA=project-manager ); <same write>
  -> STILL BLOCKED. The export died with the transient subshell; it never reached the hook process.

# REPRO 3 — persona genuinely in the hook process env (only the HARNESS can do this):
DADAIA_AGENT_PERSONA=project-manager bash sdd-spec-gate.sh  ->  ALLOWED.

# Does any `dadaia` CLI verb write the `.persona` pointer?  ->  NONE. The pointer is never populated.
```

**Root cause — the persona gate is a lock with no key.** The backlog-ownership branch trusts
persona only from (a) `*_AGENT_PERSONA` env vars read from the *hook process* environment, or
(b) a `.dadaia/sessions/runtime/<session>.persona` pointer. In every harness:

1. An agent cannot set an env var in the harness/hook process. A `Bash` tool `export` is a
   separate short-lived process (REPRO 2) — the value is gone before the next `PreToolUse` fires.
2. No `dadaia` CLI verb ever writes the `.persona` pointer (or the session-JSON `persona`
   field) for an active/dispatched agent — verified by source grep.
3. An agent writing the pointer itself is correctly blocked: `.dadaia/sessions/**` is
   `PROTECTED` (SEC-01 / CWE-284) precisely to stop persona-pointer forgery.

So there is **no legitimate path** for any agent — lead or dispatched, Codex or Claude — to
satisfy `persona == project-manager`. The "owner-only" backlog gate locks out the owner in
all harnesses. **Codex is not architecturally different here**; its dispatch flow merely
surfaced the defect first. The Claude-Code analog is tracked at
`backlog-ownership-gate-persona-unreachable-claude-code.md` and is now confirmed by the repro
above.

**Why the persona model is wrong in principle.** Backlog ownership is a *coordination
convention* (PM curates the backlog), not a security boundary against an adversary — every
agent in this workspace is operator-spawned and equally trusted. Encoding a coordination norm
as a deterministic, key-less file-write **lock** is a category error: it cannot be satisfied
and it freezes the whole backlog → release → implementation → review flow.

**Operator ruling (2026-06-09):** *This kind of lock is not tolerated in the product.* No
workflow (research, backlog-definition, release-definition, implementation+review, audits) may
ever be lock-blocked, and `project-manager` must always spawn and write freely. The **only**
tolerated deterministic lock is the single-session-per-context **lease** (release-definition /
implementation+review), which is keyed by `.dadaia/sessions/runtime/<ctx>.ptr` — that is the
real reason `.dadaia/sessions/**` stays `PROTECTED` (lease-identity integrity, not persona).

**Fix:** removed via release **0.1.7 rc-3** ("Unlock the Workflow", tasks T-017-21..28) — the
backlog-ownership persona hard-block is deleted from the gate; backlog becomes a plain
ADDITIVE-allow path; ownership is re-expressed as a PM coordination convention in the
`backlog-ownership` rule (no gate); the single-session lease is documented as the sole lock.
Acceptance: backlog writes flow from any session; the lease still serializes a Spec Context
Project to one binding session. See `specs/releases/0.1.7/SPEC.md` (rc-3 scope addition). This
bug closes when rc-3 lands and the previously-blocked
`harness-agentic-entities-and-determinism-parity` backlog item is registered through the
normal (now-unblocked) flow.

## Claude Code handoff note (2026-06-09)

This bug is ready for Claude Code or another correctly-authorized harness to pick up.

What failed in this Codex session:

1. The operator requested a backlog entry for cross-harness agentic entity architecture and
   deterministic enforcement.
2. The lead Codex agent created the required analysis reports:
   - `.dadaia/reports/dadaia-workspace/software-architect/2026-06-09T012255Z-scaffold-agentic-entities-supported-harnesses.html`
   - `.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-09T012255Z-dadaia-workspace-determinism-enforcements.html`
3. The lead Codex agent correctly identified `specs/backlog/**` as `project-manager`-owned.
4. The lead Codex agent spawned a `project-manager` subagent.
5. The spawned `project-manager` could not write backlog because `sdd-spec-gate.sh` still saw
   `writer persona unresolved`.
6. The lead Codex agent retried a minimal backlog placeholder without forging persona; the gate
   blocked it again with the same error.
7. Therefore the backlog item was **not created** and the production fix was **not implemented**.

The intended backlog that remains blocked:

- `repos/dadaia-workspace/specs/backlog/harness-agentic-entities-and-determinism-parity.md`
- an entry at the top of `repos/dadaia-workspace/specs/backlog/candidates.md`

The `project-manager` subagent returned a complete patch for those backlog files in the Codex
conversation, but applying it from the current Codex lead session would require either:

- forging/setting `DADAIA_AGENT_PERSONA=project-manager`, or
- writing a `.dadaia/sessions/runtime/<session>.persona` pointer manually.

Both are invalid as product workflow solutions. They may be useful diagnostic facts, but must
not be accepted as the normal architecture.

Claude Code should investigate the cause root-to-leaf:

1. How Codex subagents/custom agents are spawned in this harness.
2. Whether the spawned agent identity is available to hooks at all.
3. Why `CODEX_AGENT_PERSONA` or an equivalent trusted marker is not set for spawned dadaia
   agents.
4. Whether `.dadaia/sessions/runtime/<session>.persona` is the right authority bridge or
   whether a safer dispatcher-owned session protocol is needed.
5. How to preserve the security property that ordinary Write/Edit tools cannot forge persona
   authority while still allowing legitimate dispatched owner agents to pass the gate.
6. How to test this with one positive and one negative case:
   - dispatched `project-manager` writes backlog successfully;
   - non-PM write to backlog remains blocked.

This is not fixed by documenting a workaround. This is only fixed when the normal PM-owned
backlog workflow works fluidly from Codex without operator env manipulation.

## Blocked backlog content preserved here (because backlog registration is broken)

The following backlog item is intentionally recorded inside this bug because the normal
PM-owned backlog path is blocked by this same catastrophic Codex lock/ownership issue.

This is not the desired final location. After the root cause is fixed, a correctly
authorized `project-manager` workflow must move or recreate this content under:

- `repos/dadaia-workspace/specs/backlog/harness-agentic-entities-and-determinism-parity.md`
- `repos/dadaia-workspace/specs/backlog/candidates.md`

Until then, this bug is the durable record so the work is not lost.

### Backlog title

Harness Agentic Entities and Determinism Parity

### Backlog ID

`FEAT-HARNESS-AGENTIC-ENTITIES-DETERMINISM-100`

### Priority

CRITICAL

### Backlog thesis

dadaia-workspace must treat agentic entities and deterministic enforcement as a
first-class multi-harness architecture, not as an incidental side effect of
`dadaia public install --target all`.

The product supports three harnesses: Claude Code, Codex, and OpenCode. Each one has
different native primitives for instructions, agents/subagents, skills, rules, hooks,
commands, permissions, and plugins. The architecture must preserve one semantic
dadaia-workspace lifecycle while projecting the best available harness-specific
implementation for each runtime.

The release that picks this backlog item must make two things explicit and testable:

1. **Entity projection:** universal entities and harness-specific entities can be staged,
   installed, updated, and doctored independently.
2. **Deterministic enforcement:** lifecycle laws such as context injection, SDD write gates,
   backlog ownership, release definition, implementation task reservation, review gates,
   bug registration, and public asset parity are mapped per harness with honest strength
   labels: hard block, best-effort block, advisory, unsupported.

This backlog must become a dedicated SDD release or a short sequence of releases. It must not
be implemented directly from this bug text without SPEC/PLAN/TASKS approval.

### Required source reports

- Scaffold architecture report:
  `.dadaia/reports/dadaia-workspace/software-architect/2026-06-09T012255Z-scaffold-agentic-entities-supported-harnesses.html`
- Determinism enforcement report:
  `.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-09T012255Z-dadaia-workspace-determinism-enforcements.html`
- Handoffs:
  `.dadaia/handoff/dadaia-workspace/2026-06-09T012255Z-software-architect-scaffold-agentic-entities-supported-harnesses.handoff.json`
  and
  `.dadaia/handoff/dadaia-workspace/2026-06-09T012255Z-ai-engineer-dadaia-workspace-determinism-enforcements.handoff.json`

### Related existing backlog

- `specs/backlog/full-codex-compatibility.md`
- `specs/backlog/codex-context-hook-and-workflow-enforcement-hotfix.md`
- `specs/backlog/v0.2.0-agentic-lifecycle.md`

### Workstream A - Entity projection architecture

Create a clear architecture and CLI surface for updating agentic entities by scope:
`universal`, `claude`, `codex`, `opencode`, and `full`.

The existing `dadaia public install --target all|claude|codex|opencode|agents --only ...`
is a functional base, but the product vocabulary is wrong. Operators need to reason about
"universal entities", "Claude Code entities", "Codex entities", "OpenCode entities", and
"full projection", not low-level public asset plumbing.

Acceptance:

- A documented entity taxonomy exists: universal entities vs harness-specific entities.
- A user-facing CLI exists for updating entity scopes, or `dadaia public install` gains a
  clearly documented alias/subcommand exposing this vocabulary.
- `universal` updates only the confirmed universal surface.
- `claude`, `codex`, and `opencode` update only the selected harness adapter surface plus
  required shared scripts where applicable.
- `full` preserves today's full install behavior.
- `dadaia public doctor` or an equivalent doctor mode can validate one scope at a time and
  the full projection.
- Source/stage/projection hash semantics remain intact.

### Workstream B - Harness capability catalog and truth table

Create a maintained catalog of harness primitives and dadaia projections for Claude Code,
Codex, and OpenCode.

The catalog must record, for each harness:

- instruction roots;
- agents/subagents;
- skills;
- rules;
- hooks;
- commands;
- permissions/sandbox policy;
- plugins;
- workflows;
- deterministic enforcement surfaces;
- known unsupported or advisory-only surfaces.

Acceptance:

- The catalog lists every current public agentic entity class and canonical source path.
- The catalog lists every projection target used by Claude Code, Codex, and OpenCode.
- Each row has an enforcement strength label: `hard`, `best-effort`, `advisory`,
  `reference-only`, or `unsupported`.
- Doctor output can surface catalog/projection drift.
- Official documentation references gathered in the reports are carried into SPEC research
  notes or appendix, without overstating runtime guarantees.

### Workstream C - Deterministic law table

Define one semantic law table for the dadaia-workspace development lifecycle, then map each
law to the strongest available enforcement adapter per harness.

The table must include at least:

- active Spec Context resolution;
- memory bootstrap/injection once per stable session;
- root whitelist;
- SDD write classifier: ADDITIVE, MEMORY, FROZEN, MUTATING, UNGATED;
- one MUTATING lease per context;
- backlog ownership by `project-manager`;
- bug registration for dadaia tooling bugs;
- release definition by `product-engineer`;
- implementation by `software-engineer` with task reservation and write set discipline;
- AI-surface ownership by `ai-engineer`;
- review gates: qa, security, code review, and product-engineer closure/memory update;
- report and handoff validity;
- audit fan-out;
- public asset privacy/drift;
- server registry discipline for dev servers.

Acceptance:

- A single law table exists in SPEC or a generated artifact owned by the release.
- No law claims hard enforcement unless a hook, plugin, permission, command policy, or
  equivalent runtime mechanism proves it.
- Workflow files are explicitly labeled reference-only unless converted into runtime
  commands/entrypoints.
- The law table identifies which behavior is currently instruction-only and must remain
  honest in AGENTS/memory until a hard gate exists.

### Workstream D - Per-harness enforcement adapters

Bring Claude Code, Codex, and OpenCode as close as possible to the same deterministic
dadaia lifecycle while preserving honest differences between runtimes.

Claude Code acceptance:

- Confirm native `CLAUDE.md`, `.claude/agents`, `.claude/skills`, `.claude/settings.json`,
  hooks, rules, and workflows are correctly projected.
- Add Claude-specific doctor checks if the release defines CCL-style parity checks.
- Ensure duplicate hook wiring and context-injection idempotence remain covered.

Codex acceptance:

- Preserve native `AGENTS.md`, `.codex/config.toml`, custom-agent TOML, skills paths,
  `.codex/hooks.json`, and `.codex/rules/*.rules`.
- Keep workflow Markdown honest as reference-only unless a generated Codex entrypoint is
  introduced.
- Add smoke tests for hook liveness, context injection, blocked writes, agent projection,
  skill discovery, and dispatcher preflight.
- Coordinate with `full-codex-compatibility.md` and
  `codex-context-hook-and-workflow-enforcement-hotfix.md`.

OpenCode acceptance:

- Make OpenCode plugin projection first-class.
- Validate `public/plugins/sdd-gate.ts` and `public/plugins/ctx-inject.ts` against the
  supported OpenCode plugin API.
- Replace unsupported hook expectations with plugin/permission/command expectations.
- Add OC doctor checks and smoke tests for write blocking, context injection, agent
  projection, skill discovery, and command entrypoints.
- Review generated `opencode.json`, especially broad `permission: allow`, and replace with
  least-privilege policy where OpenCode supports it.

### Workstream E - Workflow dispatch entrypoints

Make natural lifecycle requests route through the correct dadaia dispatcher path where each
harness supports it.

The release should define generated entrypoints for:

- backlog intake: `project-manager`;
- research/deep study: `project-manager` or `project-auditor`;
- bug report: any agent can file, with additive path semantics;
- release definition from backlog/bugs: `product-engineer` under `project-manager`
  coordination;
- implementation: `software-engineer` under approved release/task gate;
- review trio: `qa-engineer`, `security-reviewer`, `code-reviewer`;
- audit fan-out: `project-auditor`;
- AI-surface work: `ai-engineer` review/audit before changes to agents, skills, rules,
  workflows, hooks, or harness adapters.

Acceptance:

- Workflow files remain canonical DAG/reference docs unless the release explicitly turns them
  into generated commands.
- Each generated command/entrypoint names the owning dispatcher and expected handoff/report
  behavior.
- Codex docs/personas no longer imply workflow files auto-execute.
- OpenCode commands are generated from the same semantic workflow source or a clearly
  documented adapter.
- Smoke evidence proves at least one lifecycle route:
  operator request -> project-manager intake -> correct worker dispatch/required handoff,
  or an honest "dispatch unsupported in this harness" failure.

### Release-definition questions

`product-engineer` must grill and resolve:

1. Whether to introduce a new `dadaia entities ...` command or make `dadaia public install`
   expose an entity-oriented subcommand/alias.
2. Whether the harness capability catalog is source, generated metadata, memory, doctor
   output, or a combination.
3. Which deterministic laws move into constitution vs memory vs generated catalog.
4. Which harness gets first implementation priority if the release must be split.
5. Whether Codex-specific work is merged with `FEAT-CODEX-COMPAT-100` or kept as a
   dependency.
6. Which OpenCode version/API is the supported test target.
7. Which workflow entrypoints are mandatory for MVP: backlog intake, release definition,
   implementation, review, audit, or all of them.

### Suggested release shape

This is only an intake suggestion; product-engineer owns final SPEC/PLAN/TASKS.

1. **Catalog and projection architecture**
   - Entity projection plan layer.
   - CLI vocabulary for universal/claude/codex/opencode/full.
   - Harness capability catalog.
   - Scope-aware doctor checks.

2. **Enforcement parity and OpenCode proof**
   - Semantic deterministic law table.
   - Claude/Codex/OpenCode adapter matrix.
   - OpenCode OC doctor checks.
   - Harness smoke tests.

3. **Workflow dispatcher entrypoints**
   - Generated commands/entrypoints per harness.
   - Dispatcher contract for natural lifecycle requests.
   - Smoke proving PM -> PE/SE/review routing where the harness supports dispatch.

## Description

In a Codex session, the operator asked to define a backlog item from two reports. The lead
agent correctly identified that `specs/backlog/**` is owned by `project-manager` and spawned a
`project-manager` subagent. The workflow still failed: both the lead agent and the spawned
`project-manager` were blocked by `sdd-spec-gate.sh` with `writer persona unresolved`.

This is a critical workflow/enforcement bug. The correct user experience is not to ask the
operator to export `DADAIA_AGENT_PERSONA=project-manager` or manually create a runtime persona
pointer. If the harness can spawn the owning agent, the dadaia runtime must propagate a
machine-readable persona/authority identity that the gate can verify. Manual environment
binding per agent is not a viable architecture.

## Impact

- PM-owned backlog intake cannot flow naturally from a Codex conversation.
- A correct dispatch to `project-manager` does not satisfy the SDD gate.
- The operator is forced into low-level runtime workarounds (`DADAIA_AGENT_PERSONA` or
  `.dadaia/sessions/runtime/<session>.persona`), which contradicts the dadaia-workspace
  workflow model.
- The product claim that owner-only artifacts can be routed through the owning agent is only
  partially true in Codex: dispatch exists, but ownership identity is not propagated to the
  deterministic gate.
- This blocks backlog -> release -> implementation -> review flow and undermines
  multi-agent SDD orchestration.

## Evidence

Observed on 2026-06-09 in a Codex session:

1. The operator asked to consume reports and create an explicit backlog item.
2. The lead agent spawned a `project-manager` subagent for the PM-owned backlog write.
3. The lead agent attempted a direct backlog write and was blocked:

```text
[BACKLOG OWNERSHIP ERROR] writer persona unresolved — only project-manager may write
specs/backlog/. Set DADAIA_AGENT_PERSONA=project-manager (the owning role), or record it in
the session pointer .dadaia/sessions/runtime/<session>.persona, and retry
(rule: backlog-ownership).
```

4. The spawned `project-manager` was redirected to write the backlog directly.
5. The spawned `project-manager` also reported the same gate failure:

```text
[BACKLOG OWNERSHIP ERROR] writer persona unresolved — only project-manager may write
specs/backlog/.
```

6. The subagent returned a patch instead of completing the backlog write.

7. A later controlled retry attempted to create even a minimal backlog placeholder at
   `repos/dadaia-workspace/specs/backlog/harness-agentic-entities-and-determinism-parity.md`
   without forging persona identity. It was blocked again with the same error:

```text
[BACKLOG OWNERSHIP ERROR] writer persona unresolved — only project-manager may write
specs/backlog/. Set DADAIA_AGENT_PERSONA=project-manager (the owning role), or record it in
the session pointer .dadaia/sessions/runtime/<session>.persona, and retry
(rule: backlog-ownership).
```

Related reports that triggered the backlog request:

- `.dadaia/reports/dadaia-workspace/software-architect/2026-06-09T012255Z-scaffold-agentic-entities-supported-harnesses.html`
- `.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-09T012255Z-dadaia-workspace-determinism-enforcements.html`

## Steps to reproduce

1. Start a Codex session in the dadaia workspace with an active Spec Context Project.
2. Ask the lead agent to create a backlog item from reports.
3. Ensure the lead agent dispatches/spawns `project-manager`.
4. Ask the spawned `project-manager` to write `repos/dadaia-workspace/specs/backlog/<slug>.md`
   and update `repos/dadaia-workspace/specs/backlog/candidates.md`.
5. Observe that `sdd-spec-gate.sh` blocks the write because the runtime persona is unresolved.

## Expected behavior

- Dispatching the `project-manager` agent should create a verifiable runtime identity that the
  SDD gate recognizes as `project-manager`.
- The `project-manager` should be able to write `specs/backlog/**` without operator-provided
  environment variables.
- The lead agent should not need to ask the operator to bind a persona manually.
- The gate should continue to block non-PM backlog writes, but allow PM writes from a genuine
  PM-dispatched session.

## Actual behavior

- The gate blocks the spawned `project-manager` because no recognized persona reaches the gate.
- The system suggests manual env/pointer workarounds.
- The backlog flow stops and returns a patch instead of producing the backlog artifact.

## Root cause hypothesis

The gate's backlog ownership rule trusts these identity channels:

- `DADAIA_AGENT_PERSONA`
- `CLAUDE_AGENT_PERSONA`
- `CODEX_AGENT_PERSONA`
- `OPENCODE_AGENT_PERSONA`
- `.dadaia/sessions/runtime/<session>.persona`
- the `persona` field in `.dadaia/sessions/<session>.json`

Codex subagent dispatch in the current harness does not automatically set any of those
channels for a spawned dadaia agent. The static `project-manager` persona exists as an
instruction/config surface, but it is not bridged into the deterministic gate's runtime
identity model.

There is also a broader architectural gap: the workflow layer can request/perform dispatch,
but the SDD gate only sees environment/session identity. These two systems must be connected
by a trusted dispatcher/session protocol.

## Acceptance criteria for fix

- This bug is not closed by documentation, advice, or manual environment setup. It is closed
  only by a working architecture where dispatched owner agents carry trusted, gate-visible
  authority.
- A Codex-dispatched `project-manager` can write `specs/backlog/**` without manual operator
  env vars.
- A Codex-dispatched non-PM agent remains blocked from `specs/backlog/**`.
- The dispatch mechanism writes or propagates a trusted persona marker that
  `sdd-spec-gate.sh` can verify.
- The persona marker cannot be forged by ordinary agent Write/Edit operations; the existing
  `.dadaia/sessions/**` protected-path rule remains intact or is replaced by an equally safe
  mechanism.
- There is a smoke/integration test for:
  operator request -> Codex lead -> `project-manager` dispatch -> backlog write allowed.
- There is a negative test for:
  operator request -> Codex lead/non-PM -> backlog write blocked.
- Documentation and memory stop suggesting manual env binding as the normal operational path
  for multi-agent ownership. Manual env binding may remain a diagnostic escape hatch only.
- If a harness cannot provide trustworthy subagent persona propagation, the workflow must fail
  with a product-level error and a registered bug, not with an operator-facing workaround.
- The previously blocked backlog item
  `specs/backlog/harness-agentic-entities-and-determinism-parity.md` can be registered
  through the normal PM-owned workflow after the fix.

## Related

- `specs/bugs/codex-workflow-dispatch-not-deterministically-enforced.md` — previously closed
  as fixed to the maximum deterministic extent, but this incident shows the dispatch-to-gate
  identity bridge is still missing.
- `specs/backlog/codex-context-hook-and-workflow-enforcement-hotfix.md`
- `specs/backlog/full-codex-compatibility.md`
- `.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-09T012255Z-dadaia-workspace-determinism-enforcements.html`
