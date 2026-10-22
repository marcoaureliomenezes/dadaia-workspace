# CODEX.md — Compiled Decision Protocols for the Codex Harness

Sibling of [`SKILL.md`](SKILL.md) (`dd-ai-eng-knowhow`, authoring depth).
A protocol reference, not a doc mirror — the links in "Official reference index" carry the primitive-level detail.

- Mental anchor: Codex assembles an instruction chain before working.
- Global layer in `CODEX_HOME` first, then project root down to the current directory.
- Closer files appear later and win on conflict.

---

## 1. AGENTS.md as scoped constitution — discovery + stacking

| If the instruction... | It belongs in... | Failure if misplaced |
|---|---|---|
| Changes every task | the prompt or the SPEC, not AGENTS.md | stale constitution; agents trust dead rules |
| Must always hold, whole workspace | workspace-root `AGENTS.md` | heavy/private context taxes every agent |
| Governs only the library source repo | the source repo's `AGENTS.md` | editing generated projections |
| Governs SPEC/PLAN/job files/memory/closure | `specs/AGENTS.md` | implementation without approval |
| Governs the agent-to-agent contract | `.dadaia/handoff/AGENTS.md` | reviewers get prose, not a machine contract |

- Put a rule at the narrowest scope where it is true everywhere beneath that point.
- Keep the root file a global contract, not an encyclopedia — push specifics to the owning directory.
- When the same mistake recurs twice, update the correctly-scoped AGENTS.md, not a one-off prompt.
- Which scoped files are projections and which are the project's own: `.dadaia/AGENTS.md` (manifest projections).
- Never put long repeatable workflow into AGENTS.md — that is a skill's job.

---

## 2. Naming-collision disambiguation (EXPLICIT — read code/logs correctly)

| You see / hear | What it actually is | Executable? | Enforces? |
|---|---|---|---|
| Codex "Rules" | Starlark `.rules` files under `.codex/rules/*.rules` | Yes (Starlark) | Command approval / prompt policy |
| dadaia's rule-law corpus | One root `AGENTS.md` map plus scoped `AGENTS.md` files | No | Advisory text read via native discovery |

- File extension is the ground truth: `.rules` = official Codex command policy, `.md` = dadaia's advisory law.
- A `.codex/rules/foo.md` file is projection drift — report it, fix the source installer/doctor.
- In logs: an `allow`/`prompt`/`forbidden` decision on a command = a real Starlark Rule fired.
- Plain instruction-following with no approval gate = the Markdown law was merely in context.

---

## 3. Codex Rules (Starlark `.rules`) — what they enforce, when to use

- A Codex Rule decides whether a command may run, especially outside the sandbox.
- Rules live in a `rules/` folder near an active config layer, written in Starlark.
- The command policy dadaia ships is rendered by `_render_codex_command_policy_rules` in `codex_assets.py`; read its output there, never a copy here.
- Reach for a Codex Rule only for command policy, never to make the model "think" differently.

| Property | Behavior | Authoring consequence |
|---|---|---|
| Multiple matches | most restrictive decision wins | a `forbidden` cannot be downgraded by an `allow` elsewhere |
| Composite shell | conservative on redirection, substitution, variables, control flow | gate the verb, not the pipeline |
| Decision values | `allow`, `prompt`, `forbidden` | `prompt` = human intent required; `forbidden` = hard stop |

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
| `applyTo` | ignored (`paths:` is native) | not a Codex primitive | safe to include; Codex ignores it gracefully |
| richer CC-only keys | may exist | unknown keys ignored | never depend on a CC-only key for correctness |

- dadaia projects one canonical `SKILL.md` per skill into both `.claude/` and `.codex`/`.agents`.
- Body content is shared; never hardcode harness-specific file paths or tool names as load-bearing instructions.

---

## 5. Subagents and fan-out — concurrency, deltas, guard conditions

- Codex has native subagent workflows and custom-agent TOML but does not spawn subagents automatically.
- A custom-agent TOML file makes a role spawnable; it does not route prompts by itself.
- Each subagent does its own read/execute/synthesize; the primary consolidates.

| Axis | Claude Code dispatch | Codex fan-out |
|---|---|---|
| Trigger | dispatcher agent with dispatch authority | explicit operator/dispatcher request for real spawn |
| Declarative topology | maps toward dispatch | does NOT auto-execute; needs explicit spawn or manual handoff |
| Safest pattern | task tool to a subagent | parallel read (explore, review, triage, logs, tests, compare) |

- Current Codex custom-agent schema requires `name`, `description`, `developer_instructions`.
- The TOML a persona renders to (its optional fields and `sandbox_mode`) is emitted by `_render_codex_agent_toml` in `codex_assets.py`; read its output there.

| Guard | Rule |
|---|---|
| Read vs write | Parallel read is the safe default; parallel write needs disjoint allowlists + coordination |
| Same path family | Do not fan out parallel writes to the same path family; one implementer, one task owner |
| SPEC ambiguity | Never fan out to resolve SPEC ambiguity — that is operator refinement |
| Recursion depth | A subagent should not spawn another subagent except in exceptional cases |
| Output contract | Each subagent returns findings with severity, evidence, and a verdict |

- dadaia mapping: the main thread = primary orchestrator; `dd-code-reviewer` = the verdict-only custom agent (its one write: `verdict.py`).

---

## 6. Config layers and trust model (EXPLICIT — what must NOT be project-local)

- Codex reads config in layers: personal `~/.codex/config.toml`, project `.codex/config.toml`.
- Project config loads only when the project is trusted.
- Some sensitive keys are ignored from project-local config and must remain user/admin-global.

| Concern | Layer | Project-local? | Why |
|---|---|---|---|
| Personal model / verbosity preference | `~/.codex/config.toml` | No — user-global | personal, not a product artifact |
| dadaia projected agents | `_render_agents_config_file_blocks` in `codex_assets.py` | Yes (generated) | `config_file` is a real documented key |
| Skill enable/disable overrides | `skills.config` array | Yes, only if per-skill overrides needed | `[skills] paths` is NOT a key |
| SDD-gate / hook wiring | `.codex/hooks.json` | Yes, but scripts must be trusted workspace-level | hooks run host commands |
| Provider / base URL / auth / telemetry | user or admin config | NEVER project-local | must not change credentials or host-owned behavior |
| Sandbox / approval level | profile or per-command | escalate cautiously | stricter for review; permissive only in a trusted workspace |

- Project-local config must never emit `openai_base_url`, `chatgpt_base_url`, `model_provider`, `model_providers`, `profile`, `profiles`, `notify` or `otel`: those keys redirect credentials, host-owned behavior, or telemetry.
- `approved_commands` is NOT a config key — unknown field under `--strict-config`, silently ignored otherwise.
- Command approval is owned by Rules (`.rules`) and `approval_policy`/`[tools]` keys, not a flat allow-list.
- A trusted-project escalation must never be the path by which a repo silently rewrites credentials.
- No runtime projections committed inside the source repo — `.codex/` belongs at the workspace runtime root.
- No absolute paths or local-projection leakage into public packages — hooks/configs use portable paths only.
- Treat enabling project-local config/hooks as a privileged review step (the security lens).

---

## 7. Hooks in Codex — types and lifecycle deltas

- `UserPromptSubmit` and `Stop` do not honor matchers — never depend on a matcher there.
- `command` and `mcp_tool` handlers run today; `prompt` and `agent` handlers are parsed but skipped.

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
- Consult the live probe (`.dadaia/.venv/bin/dadaia certify --json`'s `codex-live-probe` check) instead of assuming.
- Rerun the live contract after any Codex CLI upgrade.
- The git chokepoints remain independent regardless of hook enforcement (pre-push).
- Context injection is decided by `decide_injection` in `injection_policy.py`; on Codex it fires on `SessionStart` (matcher `startup|resume`), keyed on `session_id`.

| Property | Consequence for authoring |
|---|---|
| Project-local hooks run only when the project layer is trusted | never assume a project hook fires in an untrusted clone |
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
| Current product truth | Memory | `specs/memory/*.md` (`specs/memory/AGENTS.md`) |
| Repeatable procedure | Skill | `SKILL.md` |
| External system / context source | MCP | MCP server config |
| Mechanical invariant on a session event | Hook | hook script + `.codex/hooks.json` |
| Block / prompt on a command | Codex Rule | Starlark `.rules` |
| Explicit parallel read / review | Subagent (explicit spawn) | dispatch contract |

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
