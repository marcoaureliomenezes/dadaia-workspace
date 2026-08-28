# CODEX.md — Compiled Decision Protocols for the Codex Harness

Sibling of [`SKILL.md`](SKILL.md) (`dd-ai-eng-knowhow`, `ai-engineer`-only depth).
A protocol reference, not a doc mirror — read official docs (§8) on demand for primitive-level detail.

- Mental anchor: Codex assembles an instruction chain before working.
- Global layer in `CODEX_HOME` first, then project root down to the current directory.
- Closer files appear later and win on conflict.

Current-doc corrections to keep active:

- Codex spawns subagents only when explicitly asked for subagents, delegation, or parallel agent work.
- A custom-agent TOML file makes a role spawnable; it does not route prompts by itself.
- Codex Rules use documented Starlark `prefix_rule(...)` declarations.
- Treat a generated `command_allowed(cmd)` policy as compatibility debt unless a live Codex binary proves it loads.
- Project `.codex/config.toml`, project hooks, and project rules load only when the project layer is trusted.
- Provider/auth/telemetry settings remain user/admin concerns; never emit them from dadaia public assets.
- Hook matchers are event-specific; `UserPromptSubmit` and `Stop` ignore matchers.
- Command hooks are the only handler type that runs today.

---

## 1. AGENTS.md as scoped constitution — discovery + stacking

| If the instruction... | It belongs in... | Failure if misplaced |
|---|---|---|
| Changes every task | the prompt or the SPEC, not AGENTS.md | stale constitution; agents trust dead rules |
| Must always hold, whole workspace | workspace-root `AGENTS.md` | heavy/private context taxes every agent |
| Governs only the library source repo | the source repo's `AGENTS.md` | editing generated projections |
| Governs SPEC/PLAN/TASKS/memory/closure | `specs/AGENTS.md` | implementation without approval |
| Governs the agent-to-agent contract | `.dadaia/handoff/AGENTS.md` | reviewers get prose, not a machine contract |

- Discovery order is root -> subdir; a subdir `AGENTS.md` adds to and overrides the inherited chain.
- Put a rule at the narrowest scope where it is true everywhere beneath that point.
- Keep the root file a global contract, not an encyclopedia — push specifics to the owning directory.
- When the same mistake recurs twice, update the correctly-scoped AGENTS.md, not a one-off prompt.
- `AGENTS.md` at the workspace root and every consumer repo is lib-originated (manifest-tracked); never hand-edit.
- Author the source in `public/` and propagate via `dadaia public stage && dadaia public install`.
- Never put long repeatable workflow into AGENTS.md — that is a skill's job.

---

## 2. Naming-collision disambiguation (EXPLICIT — read code/logs correctly)

| You see / hear | What it actually is | Executable? | Enforces? |
|---|---|---|---|
| Codex "Rules" | Starlark `.rules` files under `.codex/rules/*.rules` | Yes (Starlark) | Command approval / prompt policy |
| dadaia's rule-law corpus | Single consolidated `DADAIA.md`, projected byte-identically | No | Advisory text read via native discovery |

- File extension is the ground truth: `.rules` = official Codex command policy, `.md` = dadaia's advisory law.
- Current dadaia projection must not install Markdown law content into `.codex/rules/`.
- A `.codex/rules/foo.md` file is projection drift — report it, fix the source installer/doctor.
- In logs: an `allow`/`prompt`/`forbidden` decision on a command = a real Starlark Rule fired.
- Plain instruction-following with no approval gate = the Markdown law was merely in context.
- There is no `public/rules/` directory in this workspace — the former per-topic files consolidated into `DADAIA.md`.
- Never document or project a `public/rules/*.md` taxonomy against a directory that does not exist.

---

## 3. Codex Rules (Starlark `.rules`) — what they enforce, when to use

- A Codex Rule decides whether a command may run, especially outside the sandbox.
- Rules live in a `rules/` folder near an active config layer, written in Starlark.
- Each rule emits one of three decisions: `allow`, `prompt`, `forbidden`.

```
prefix_rule(
    pattern = ["git", "push"],
    decision = "prompt",
    justification = "Publishing requires operator approval.",
    match = ["git push origin feature/x"],
    not_match = ["git status"],
)
```

| Property | Behavior | Authoring consequence |
|---|---|---|
| Multiple matches | most restrictive decision wins | a `forbidden` cannot be downgraded by an `allow` elsewhere |
| Composite shell | conservative on redirection, substitution, variables, control flow | gate the verb, not the pipeline |
| Decision values | `allow`, `prompt`, `forbidden` | `prompt` = human intent required; `forbidden` = hard stop |

| Axis | Claude Code rule (`.md`) | Codex Rule (`.rules`, Starlark) |
|---|---|---|
| Medium | Markdown text injected into context | Executable Starlark |
| Governs | model behavior / instructions | command approval |
| Enforcement | advisory (model must comply) | mechanical (command gated) |
| Use when | durable guidance the model follows | must block or prompt on a command |

- Reach for a Codex Rule only for command policy, never to make the model "think" differently.
- Candidate dadaia rules: `prompt` on `git push` (publishing follows QA/review).
- Candidate dadaia rules: `prompt` on `dadaia context dead` and `dadaia public install` (they mutate canonical state).
- Candidate dadaia rules: `forbidden` on destructive sweeps over `repos/` (user projects).
- Projection invariant: `dadaia-command-policy.rules` must contain `prefix_rule(` and never `command_allowed(`.
- Keep a focused test for that shape — it separates current Codex command policy from older compatibility assumptions.

---

## 4. Skills in Codex — discovery, frontmatter deltas, cross-harness authoring

- Codex first sees only frontmatter (`name`, `description`); opens the full body only when it decides to use the skill.
- The description is the trigger surface — short, verb-first, scenario-named ("Use when..." / "Use for...").
- Codex scans repo `.agents/skills` directories from CWD upward to the repository root, plus user/admin/system locations.
- This repo discovery is native and automatic — no config key enables it.
- Large skill inventories are listing-budgeted; descriptions must front-load trigger words.
- A skill omitted from the initial list can still be used when explicitly mentioned.

| Claimed key | Reality |
|---|---|
| `[skills] paths = [...]` | INVALID — unknown field, hard error under `--strict-config`, silently ignored otherwise |
| `skills.config` | Real surface: array of per-skill `{path, enabled}` override objects — enable/disable only |

| Field | Claude Code | Codex | Cross-harness authoring rule |
|---|---|---|---|
| `name` | required | required | keep identical across both |
| `description` | required (trigger) | required (trigger) | one description that triggers in both |
| `applyTo` | path glob, honored | not a Codex primitive | safe to include; Codex ignores it gracefully |
| richer CC-only keys | may exist | unknown keys ignored | never depend on a CC-only key for correctness |

- dadaia projects one canonical `public/skills/<name>/SKILL.md` into both `.claude/` and `.codex`/`.agents`.
- A skill must remain correct when read by either harness.
- Never write a step that only works because a Claude-Code-only frontmatter key was honored.
- Body content is shared; never hardcode harness-specific file paths or tool names as load-bearing instructions.
- Description must trigger appropriately in both harnesses — it is read identically.

| Good | Bad |
|---|---|
| Encodes a repeatable execution protocol | Tries to replace the SPEC |
| One focused job; states when *not* to use on collision risk | Hides a decision that belongs in PLAN |
| Prefers instructions; scripts only when validation must be deterministic | Carries permanent global policy that belongs in AGENTS.md |

---

## 5. Subagents and fan-out — concurrency, deltas, guard conditions

- Codex has native subagent workflows and custom-agent TOML but does not spawn subagents automatically.
- The operator or a dispatcher running in the main thread must explicitly request delegation or parallel work.
- Each subagent does its own read/execute/synthesize; the primary consolidates.
- A declarative workflow topology does not execute parallelism by itself.

| Axis | Claude Code dispatch | Codex fan-out |
|---|---|---|
| Trigger | dispatcher agent with dispatch authority | explicit operator/dispatcher request for real spawn |
| Declarative topology | maps toward dispatch | does NOT auto-execute; needs explicit spawn or manual handoff |
| Safest pattern | task tool to a subagent | parallel read (explore, review, triage, logs, tests, compare) |

- Current Codex custom-agent schema requires `name`, `description`, `developer_instructions`.
- Optional `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, skill config inherit when omitted.
- Use `sandbox_mode` as a real role-boundary signal — evidence-only reviewers should not be general workspace writers.

| Guard | Rule |
|---|---|
| Read vs write | Parallel read is the safe default; parallel write needs disjoint allowlists + coordination |
| Same path family | Do not fan out parallel writes to the same path family; one implementer, one task owner |
| SPEC ambiguity | Never fan out to resolve SPEC ambiguity — that is operator refinement |
| Recursion depth | A subagent should not spawn another subagent except in exceptional cases |
| Output contract | Each subagent returns findings with severity, evidence, and a verdict |

- dadaia mapping: `project-manager` = primary orchestrator; `project-auditor` = audit orchestrator.
- Narrow roles (`qa-engineer`, `security-reviewer`, etc.) are candidate custom agents with scoped tools.

---

## 6. Config layers and trust model (EXPLICIT — what must NOT be project-local)

- Codex reads config in layers: personal `~/.codex/config.toml`, project `.codex/config.toml`.
- Project config loads only when the project is trusted; closer files may override earlier values.
- Some sensitive keys are ignored from project-local config and must remain user/admin-global.

| Concern | Layer | Project-local? | Why |
|---|---|---|---|
| Personal model / verbosity preference | `~/.codex/config.toml` | No — user-global | personal, not a product artifact |
| dadaia projected agents | `.codex/agents/*.toml` via `agents.<name>.config_file` | Yes (generated) | `config_file` is a real documented key |
| Skill enable/disable overrides | `skills.config` array | Yes, only if per-skill overrides needed | `[skills] paths` is NOT a key |
| SDD-gate / hook wiring | `.codex/hooks.json` | Yes, but scripts must be trusted workspace-level | hooks run host commands |
| Provider / base URL / auth / telemetry | user or admin config | NEVER project-local | must not change credentials or host-owned behavior |
| Sandbox / approval level | profile or per-command | escalate cautiously | stricter for review; permissive only in a trusted workspace |

- Project-local config must never emit `openai_base_url`, `chatgpt_base_url`, `model_provider`, `model_providers`.
- Project-local config must never emit `profile`, `profiles`, `notify`, or `otel`.
- Those keys redirect credentials, host-owned behavior, or telemetry — operator/admin only.
- `approved_commands` is NOT a config key — unknown field under `--strict-config`, silently ignored otherwise.
- Command approval is owned by Rules (`.rules`) and `approval_policy`/`[tools]` keys, not a flat allow-list.
- Provider/auth/telemetry stay user/admin-global — never emit into any `public/`-projected `.codex/` config.
- A trusted-project escalation must never be the path by which a repo silently rewrites credentials.
- No runtime projections committed inside the source repo — `.codex/` belongs at the workspace runtime root.
- No absolute paths or local-projection leakage into public packages — hooks/configs use portable paths only.
- Treat enabling project-local config/hooks as a privileged review step (pair with security-reviewer).

---

## 7. Hooks in Codex — types and lifecycle deltas

- Codex hooks fire on: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`.
- Codex hooks also fire on: `PostCompact`, `SubagentStart`, `SubagentStop`, `Stop`.
- Only command hook handlers run today; `prompt` and `agent` handlers are parsed but skipped.
- `UserPromptSubmit` and `Stop` do not honor matchers — never depend on a matcher there.

| Fact | Evidence level |
|---|---|
| The PreToolUse `matcher` is a regex string; `^(apply_patch\|Edit\|Write)$` is valid | official docs |
| `Edit`/`Write` are matcher aliases for `apply_patch`; hook input still reports `tool_name: "apply_patch"` | official docs |
| Preferred deny: `hookSpecificOutput.permissionDecision = "deny"`; legacy `block`/exit-0 accepted; exit 2 also denies | live-verified |
| Hook `command` strings run through a shell — env-prefix, `$(...)`, `~` all work | live-verified |
| A real `apply_patch` payload has `tool_input.command` with NO `file_path` key | live-verified |

- From the payload fact: a gate's header parser must classify every `*** Add/Update/Delete File:` header.
- Multi-file patch classification is most-restrictive-verdict-wins.
- Whether hooks fire in interactive `codex` TUI vs headless `codex exec` is a version-qualified fact.
- Consult the installed workspace's live probe (`dadaia public doctor`'s `codex:trust-boundary` line) instead of assuming.
- Rerun the live contract after any Codex CLI upgrade.
- The git chokepoints remain independent regardless of hook enforcement (pre-commit, pre-push).
- Inject full context once per session on `SessionStart` (matcher `startup|resume`), keyed on `session_id`.
- The bootstrap must stay a silent no-op after the first injection (session-keyed sentinel).
- Re-injecting the whole bootstrap per prompt is token waste and drift.

| Property | Consequence for authoring |
|---|---|
| Project-local hooks run only when the project layer is trusted | never assume a project hook fires in an untrusted clone |
| Unmanaged command hooks must be reviewed and trusted | treat any new hook as privileged-code review |
| Multiple hooks can match one event and run in parallel | a hook must be idempotent and side-effect-safe |
| Codex adds compaction + subagent lifecycle events | use them for context injection and subagent bookkeeping |

| Should | Should not |
|---|---|
| Validate SDD gate before write | Decide product scope |
| Block forbidden repo artifacts | Rewrite SPEC to justify code |
| Validate handoff/report format | Hide human approval |
| Update session heartbeat after every tool call | Depend on fragile state with no timeout or clear message |

---

## Customization decision table — goal -> layer + file type

| Goal | Layer / primitive | File type |
|---|---|---|
| One-off task, temporary context, operator decision | Prompt | (ephemeral) |
| Durable behavior, scoped | `AGENTS.md` (narrowest scope) | Markdown |
| Current product truth | Memory | `specs/memory/*.md` (write in DEFINITION + CLOSURE) |
| Repeatable procedure | Skill | `SKILL.md` |
| External system / context source | MCP | MCP server config |
| Mechanical invariant on a session event | Hook | hook script + `.codex/hooks.json` |
| Block / prompt on a command | Codex Rule | Starlark `.rules` |
| Explicit parallel read / review | Subagent (explicit spawn) | dispatch contract |

- Practical ladder: one-time -> prompt; permanent rule -> scoped AGENTS.md; repeated procedure -> skill.
- Ladder continued: command block/approval -> Codex Rule; must run on a session event -> hook; parallelize -> subagent.

---

## 8. Official reference index (links only — no content copied)

Consult on demand.

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
