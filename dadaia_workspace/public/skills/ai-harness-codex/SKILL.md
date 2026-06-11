---
name: ai-harness-codex
description: >
  ai-engineer-only compiled mental model and decision protocols for the Codex
  (OpenAI) harness. Use when authoring or auditing Codex-facing AGENTS.md, Codex
  Rules (Starlark .rules), skills, subagent fan-out, config layers, hooks, or
  workflow/SDD integration. Disambiguates the "Rules" naming collision and the
  ~/.codex vs project .codex trust model. References official Codex docs as
  on-demand links only — never transcribed.
applyTo: "dadaia_workspace/public/**"
---

# ai-harness-codex — Compiled Decision Protocols for the Codex Harness

This is a reasoned protocol skill, not a documentation mirror. It encodes how to
*decide* when authoring the Codex-facing AI-entity surface. Read the official docs
(reference index at the end) on demand when you need primitive-level detail; this
skill tells you which primitive to reach for and where dadaia's runtime constraints
bend the official model.

Mental anchor: Codex assembles an instruction chain before working — global layer
in `CODEX_HOME` first, then the project from repo root down to the current
directory. Closer files appear later and win on conflict. Almost every decision
below is an application of "which layer owns this, and does it win where it must."

Current-doc corrections to keep active:
- Codex subagents are available in current Codex, but Codex spawns them only when
  explicitly asked for subagents, delegation, or parallel agent work. A custom-agent
  TOML file makes a role spawnable; it does not route prompts by itself.
- Codex Rules use documented Starlark `prefix_rule(...)` declarations. Treat any
  generated `command_allowed(cmd)` policy as compatibility debt unless a local Codex
  binary proves it still loads.
- Project `.codex/config.toml`, project hooks, and project rules load only when the
  project layer is trusted. Provider/auth/telemetry settings remain user/admin
  concerns and must not be emitted from dadaia public assets.
- Hook matchers are event-specific. `UserPromptSubmit` and `Stop` ignore matchers;
  command hooks are the only handler type that runs today.

---

## 1. AGENTS.md as scoped constitution — discovery + stacking

### Decision protocol: which AGENTS.md layer owns an instruction?

| If the instruction… | It belongs in… | Failure if misplaced |
|---|---|---|
| Changes every task | the prompt or the SPEC, **not** AGENTS.md | stale constitution; agents trust dead rules |
| Must always hold for the whole workspace | workspace-root `AGENTS.md` | heavy/private context taxes every agent |
| Governs only the library source repo | the source repo's `AGENTS.md` | editing generated projections; runtime artifacts in repo |
| Governs SPEC/PLAN/TASKS/memory/closure | `specs/AGENTS.md` | implementation without approval; memory rewritten outside CLOSURE |
| Governs the agent-to-agent contract | `.dadaia/handoff/AGENTS.md` | reviewers get prose, not a machine contract |

### Stacking and scope inheritance

- Discovery order is root → subdir. A subdir `AGENTS.md` **adds to and overrides**
  the inherited chain; it does not replace it. Put a rule at the *narrowest* scope
  where it is true everywhere beneath that point.
- Keep the root file a global *contract*, not an encyclopedia. The most common
  Codex AGENTS.md smell is a bloated root; push specifics down to the directory
  that owns them.
- When the same mistake recurs twice, update the correctly-scoped AGENTS.md — do
  not patch it in a one-off prompt.

### Authoring constraints (dadaia)

- `AGENTS.md` files at the workspace root and in every consumer repo are
  **lib-originated** (manifest-tracked). Never hand-edit. Author the source in
  `public/` and propagate via `dadaia public stage && dadaia public install`.
- Never put long repeatable workflow into AGENTS.md — that is a skill's job.

---

## 2. Naming-collision disambiguation (EXPLICIT — read code/logs correctly)

This is the single most error-prone area when reading Codex code, configs, or logs
in this workspace. The word "rule" means two unrelated things.

| You see / hear | What it actually is | Executable? | Enforces? |
|---|---|---|---|
| Codex **"Rules"** | Starlark `.rules` files under `.codex/rules/*.rules` | Yes (Starlark) | Command approval / prompt policy |
| dadaia **"rules"** (`public/rules/*.md`) | Markdown workspace-protocol / agent-guidance docs | No | Nothing automatically — advisory text the model reads through projected guidance surfaces |

Disambiguation heuristics when reading:

- **File extension is the ground truth.** `.rules` = official Codex command policy.
  `.md` = dadaia advisory protocol. Current dadaia projection must not install Markdown
  protocols into `.codex/rules/`.
- A `.codex/rules/foo.md` file is projection drift. Report it and fix the source
  installer/doctor rather than treating it as enforcement.
- In logs: an `allow`/`prompt`/`forbidden` decision on a command = a real Starlark
  Rule fired. Plain instruction-following with no approval gate = a Markdown doc was
  merely in context.

dadaia audit reading: the Markdown-in-`rules/` naming scored low (5/10) precisely
because it misleads operators into believing enforcement exists. When you author,
do not deepen that confusion.

---

## 3. Codex Rules (Starlark `.rules`) — what they enforce, when to use

### Mental model

A Codex Rule decides whether a **command** may run, especially outside the sandbox.
Rules live in a `rules/` folder near an active config layer, are written in Starlark,
and emit one of three decisions.

```
prefix_rule(
    pattern = ["git", "push"],
    decision = "prompt",
    justification = "Publishing requires operator approval.",
    match = ["git push origin feature/x"],
    not_match = ["git status"],
)
```

### Resolution semantics (memorize these)

| Property | Behavior | Authoring consequence |
|---|---|---|
| Multiple matches | most restrictive decision wins | a `forbidden` cannot be downgraded by an `allow` elsewhere |
| Composite shell | Codex splits simple scripts; conservative on redirection, substitution, variables, control flow | do not rely on Rules to parse complex one-liners; gate the verb, not the pipeline |
| Decision values | `allow`, `prompt`, `forbidden` | `prompt` = human intent required; `forbidden` = hard stop |

### Claude Code rules vs Codex Rules

| Axis | Claude Code rule (`.md`, `always_on`/path-scoped) | Codex Rule (`.rules`, Starlark) |
|---|---|---|
| Medium | Markdown text injected into context | Executable Starlark |
| Governs | model behavior / instructions | command approval |
| Enforcement | advisory (model must comply) | mechanical (command gated) |
| Use when | you want durable guidance the model follows | you must *block or prompt* on a command |

### When to reach for a Codex Rule

Only for command policy. Candidate dadaia rules: `prompt` on `git push` (publishing
must follow QA/review), `prompt` on `dadaia context dead` and `dadaia public install`
(they mutate canonical workspace state / reproject all runtimes), `forbidden` on
destructive sweeps over `repos/` (user projects). If you want the model to *think*
differently, that is a skill or AGENTS.md, not a Rule.

Projection invariant: generated `.codex/rules/dadaia-command-policy.rules` must
contain `prefix_rule(` and must not contain `command_allowed(`. Keep a focused test
for that shape because it separates current documented Codex command policy from
older compatibility assumptions.

---

## 4. Skills in Codex — discovery, frontmatter deltas, cross-harness authoring

### Discovery and progressive disclosure

A skill is a folder with `SKILL.md`. Codex first sees only the frontmatter
(`name`, `description`) and opens the full body **only when it decides to use the
skill**. The description is the trigger surface — it must be short, verb-first, and
scenario-named ("Use when…" / "Use for…").

Codex scans repo `.agents/skills` directories from CWD upward to the repository
root, plus user/admin/system locations. Large skill inventories are listing-
budgeted, so descriptions must front-load trigger words; a skill omitted from the
initial list can still be used when explicitly mentioned.

### Frontmatter deltas vs Claude Code

| Field | Claude Code | Codex | Cross-harness authoring rule |
|---|---|---|---|
| `name` | required | required | keep identical across both |
| `description` | required (trigger) | required (trigger) | one description that triggers in both — verb-first |
| `applyTo` | path glob, honored | not a Codex primitive | safe to include; Codex ignores it gracefully |
| richer CC-only keys | may exist | unknown keys ignored | never *depend* on a CC-only key for correctness |

### Cross-harness degradation constraint (HARD)

dadaia projects one canonical `public/skills/<name>/SKILL.md` into both `.claude/`
and `.codex`/`.agents`. Therefore:

- A skill must remain correct when read by either harness. Never write a step that
  only works because a Claude-Code-only frontmatter key was honored.
- Body content is shared; do not hardcode harness-specific file paths or tool names
  as load-bearing instructions. Express behavior in terms both harnesses share.
- Description must trigger appropriately in both — it is read identically.

### Good vs bad skill (Codex framing)

| Good | Bad |
|---|---|
| Encodes a repeatable execution protocol (reserve TASKS.md, validate SDD gate, emit handoff, OWASP review) | Tries to replace the SPEC |
| One focused job; says when *not* to use if collision risk | Hides a decision that belongs in PLAN |
| Prefers instructions; uses scripts only when validation must be deterministic | Carries permanent global policy that belongs in AGENTS.md |

---

## 5. Subagents and fan-out — concurrency, deltas, guard conditions

### Mental model (and the key delta vs Claude Code)

Codex has native subagent workflows and custom-agent TOML, but it does **not**
spawn subagents automatically. The operator (or a dispatcher running in the main
thread) must explicitly request delegation or parallel work. Each subagent does
its own read/execute/synthesize; the primary consolidates. This is the central
audit correction: a declarative workflow YAML/topology does **not** equal a
running subagent — it does not execute parallelism by itself.

| Axis | Claude Code dispatch | Codex fan-out |
|---|---|---|
| Trigger | dispatcher agent with dispatch authority | explicit operator/dispatcher request for real spawn |
| Declarative topology | maps toward dispatch | does NOT auto-execute; needs explicit spawn, a real executor, or manual handoff |
| Safest pattern | task tool to a subagent | parallel **read** (explore, review, triage, logs, tests, compare) |

Current Codex custom-agent schema requires `name`, `description`, and
`developer_instructions`. Optional `model`, `model_reasoning_effort`,
`sandbox_mode`, `mcp_servers`, and skill config inherit when omitted. Use
`sandbox_mode` as a real role-boundary signal: evidence-only reviewers should not
be projected as general workspace writers unless their role explicitly writes
artifacts.

### Guard conditions for fan-out correctness

| Guard | Rule |
|---|---|
| Read vs write | Parallel read is the safe default. Parallel write requires **disjoint allowlists** + rigorous coordination. |
| Same path family | Never let two implementers write the same path family without a lock and separate TASKS. |
| SPEC ambiguity | Never fan out to resolve SPEC ambiguity — that is operator refinement, not parallel work. |
| Recursion depth | A subagent should not spawn another subagent except in exceptional cases. |
| Output contract | Each subagent returns findings with severity, evidence, and a verdict; primary consolidates to Approve / Request Changes / Needs Discussion via handoff JSON. |

dadaia mapping: `project-manager` = primary orchestrator (splits work, defines
inputs, awaits handoffs, consolidates verdict); `project-auditor` = audit
orchestrator; narrow roles (`qa-engineer`, `security-reviewer`, etc.) = candidate
custom agents with scoped tools.

---

## 6. Config layers and trust model (EXPLICIT — what must NOT be project-local)

### Layered resolution and the trust boundary

Codex reads config in layers: personal config in `~/.codex/config.toml`; project
config in `.codex/config.toml` **loaded only when the project is trusted**; closer
files may override earlier values. Some sensitive keys are ignored from project-
local config and must remain user/admin-global.

### Trust classification (decision table)

| Concern | Layer | Project-local? | Why |
|---|---|---|---|
| Personal model / verbosity preference | `~/.codex/config.toml` | No — user-global | personal, not a product artifact |
| dadaia projected agents | `.codex/agents/*.toml` | Yes (generated) | runtime projection from `public/` |
| Skill search paths | `.codex` skills config | Yes (generated) | `[skills] paths = [".agents/skills", ".codex/skills"]` |
| SDD-gate / hook wiring | `.codex/hooks.json` | Yes, but must point to **trusted workspace-level scripts** | hooks run host commands |
| Provider / base URL / auth / telemetry | user or admin config | **NEVER project-local** | a repo must not change credentials or host-owned behavior |
| Sandbox / approval level | profile or per-command | escalate cautiously | stricter for review; permissive only in a trusted workspace |

Project-local config must not emit `openai_base_url`, `chatgpt_base_url`,
`model_provider`, `model_providers`, `profile`, `profiles`, `notify`, or `otel`.
Those keys redirect credentials, host-owned behavior, or telemetry and belong to
the operator/admin.

### dadaia audit findings — what must NOT be project-local (apply as constraints)

- **Provider/auth/telemetry stay user/admin-global.** Never emit these into any
  `public/`-projected `.codex/` config. A trusted-project escalation must never be
  the path by which a repo silently rewrites credentials.
- **No runtime projections committed inside the source repo.** `.codex/` projections
  belong at the workspace runtime root, not inside the library source repo — repo
  hygiene forbids generated runtime inside the repo. (Cross-check: sub-repo
  isolation rule.)
- **No absolute paths / local-projection leakage into public packages.** Hooks and
  configs must use portable paths; absolute, machine-specific, or consumer-specific
  paths must never reach a public asset.
- **Trust is escalation, not a default.** Treat enabling project-local config/hooks
  as a privileged review step (pair with security-reviewer), because it expands what
  the project can execute.

---

## 7. Customization decision table — goal → layer + file type

For each customization goal, pick exactly one layer. Reaching for the wrong layer
is the most common Codex authoring error.

| Goal | Layer / primitive | File type |
|---|---|---|
| One-off task, temporary context, operator decision | Prompt | (ephemeral) |
| Durable behavior, scoped | `AGENTS.md` (narrowest scope) | Markdown |
| Current product truth | Memory | `specs/memory/*.md` (write in DEFINITION + CLOSURE, §13) |
| Repeatable procedure | Skill | `SKILL.md` |
| External system / context source | MCP | MCP server config |
| Mechanical invariant on a session event | Hook | hook script + `.codex/hooks.json` |
| Block / prompt on a command | **Codex Rule** | Starlark `.rules` |
| Explicit parallel read / review | Subagent (explicit spawn) | dispatch contract |

Practical ladder: one-time → prompt; permanent rule → scoped AGENTS.md; repeated
procedure → skill; command block/approval → Codex Rule; must run on a session event
→ hook; parallelize read/review → subagent with an output contract.

---

## 8. Workflow / SDD phase integration

Codex works best with explicit objective, context, constraints, and definition of
done — exactly the SDD shape. Map Codex workflow expectations onto dadaia's gates:

| SDD phase | Primary agent | Gate | Output |
|---|---|---|---|
| Intake | `project-manager` | clear scope | backlog candidate / bug |
| Specs | `product-engineer` + specialists | SPEC/PLAN/TASKS **Aprovado** | release with test criteria, reviewers agreeing pre-impl |
| Reserve | implementer | TASKS.md marker `[-]` | clear write set, locked session |
| Implementation | specialist by path family | unit/integration tests | implementation handoff (task NOT done if review pending) |
| QA / review | `qa-engineer`, `security-reviewer`, `code-reviewer` | all approve | consolidated verdict |
| Closure | `product-engineer` | triple evidence | CLOSURE + memory update + archived release |

Authoring consequences:
- Hooks/workflow files enforce *mechanics* of these gates; they must never decide
  product scope, rewrite the SPEC to justify code, or hide human approval.
- For difficult tasks, plan before implementing (reduces rework). For bugs,
  reproduction + verification matter more than a vague description.
- Path contract is part of UX: every agent writes handoff to
  `.dadaia/handoff/<context>/` and human report to
  `.dadaia/reports/<context>/<agent>/`. Divergent paths make the panel look broken
  even when work exists.

---

## 9. Hooks in Codex — types and lifecycle deltas

### Event surface

Codex hooks can fire on: `SessionStart`, `UserPromptSubmit`, `PreToolUse`,
`PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, `Stop`.
Only command hook handlers run today; `prompt` and `agent` handlers are parsed but
skipped. `UserPromptSubmit` and `Stop` do not honor matchers, so never depend on a
matcher there for selective behavior.

> **Inject full context once per session, not every prompt.** Wire the full static
> context bootstrap on `SessionStart` (matcher `startup|resume`), keyed on the
> `session_id` Codex passes on stdin. `UserPromptSubmit` hooks may fire every prompt,
> but the bootstrap must stay a silent no-op after the first injection (session-keyed
> sentinel). Re-injecting the whole bootstrap per prompt is token waste and drift.

### Lifecycle deltas vs Claude Code (authoring-relevant)

| Property | Consequence for authoring |
|---|---|
| Project-local hooks run **only when the project layer is trusted** | never assume a project hook fires in an untrusted clone; gate-critical logic needs a trusted workspace |
| Unmanaged command hooks must be reviewed and trusted | treat any new hook as privileged-code review (pair with security-reviewer) |
| Multiple hooks can match one event and run **in parallel** | a hook must NOT assume it is the sole guardian of its event; make it idempotent and side-effect-safe |
| Codex adds compaction + subagent lifecycle events | richer surface than Claude Code's PreToolUse/PostToolUse/Stop/Notification — use them for context injection and subagent bookkeeping |

### Hook do / don't

| Should | Should not |
|---|---|
| Validate SDD gate before write | Decide product scope |
| Block forbidden repo artifacts | Rewrite SPEC to justify code |
| Validate handoff/report format | Hide human approval |
| Update session heartbeat after every tool call | Depend on fragile state with no timeout or clear message |

dadaia reference wiring (live shape, v0.1.10): `PreToolUse apply_patch|Edit|Write →
python -m dadaia_workspace.hooks.sdd_gate` and `→ …hooks.root_whitelist`;
`PostToolUse → …hooks.sdd_post_gate` with the matcher **omitted** — Codex's canonical
match-all form — so the lease heartbeat fires after every tool;
`SessionStart → …hooks.ctx_inject`. The legacy bash hook
quartet was retired in v0.1.10 (Decision D-1) — the hooks are production Python owned
by software-engineer. Risk to guard against: absolute paths and local projections
leaking into public packages.

---

## 10. Official reference index (links only — no content copied)

Consult on demand. URLs sourced from the academy lessons; not transcribed content.

| Topic | Official URL |
|---|---|
| AGENTS.md | https://developers.openai.com/codex/guides/agents-md |
| Rules (Starlark `.rules`) | https://developers.openai.com/codex/rules |
| Skills | https://developers.openai.com/codex/skills |
| Subagents | https://developers.openai.com/codex/subagents |
| Advanced config | https://developers.openai.com/codex/config-advanced |
| Customization | https://developers.openai.com/codex/concepts/customization |
| Workflows | https://developers.openai.com/codex/workflows |
| Hooks | https://developers.openai.com/codex/hooks |

---

## Authoring guardrails (apply every time)

- This skill is restricted to `ai-engineer` (`harness-skill-scope` rule). General
  agents use `harness-primitives`.
- All authoring targets are `dadaia_workspace/public/...` source. Never hand-edit
  `.codex/`, `.claude/`, `.agents/`, `.opencode/` projections; propagate via
  `dadaia public stage && dadaia public install`.
- No consumer-specific names, hostnames, IPs, private repo slugs, secrets, or
  operator-private data in any authored asset.
- Tables over prose for enumerable rules. Compiled protocol over doc transcription.
