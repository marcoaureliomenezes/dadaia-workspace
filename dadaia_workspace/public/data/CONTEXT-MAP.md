# CONTEXT-MAP — the context balance of a dadaia-workspace

Library document. Projected nowhere: `public stage` copies it into `.dadaia/agentic/data/`
with the rest of `data/`, and no projection rule installs it into a runtime tree.

One row per surface: what it is for and what belongs in it. A surface's size is a soft
review signal (one purpose, no restated rule), never a build failure (ADR 0143); a SKILL.md's
line limits are `behavior-map.json`'s (ADR 0170).

Every surface is sourced under `dadaia_workspace/public/`; the `Surface` column names the
path or entity as it appears in an installed workspace.

## 1. Load triggers, per harness

| Harness | Root `AGENTS.md` | Scoped `AGENTS.md` | `.agents/skills/dd-*` | `.agents/agents/dd-*.md` | Own dir |
|---|---|---|---|---|---|
| Claude Code | session start, iff no `CLAUDE.md` on the path | attached when a file in that dir is Read | via per-skill symlink under `.claude/skills/` | via per-file symlink under `.claude/agents/` | `.claude/` (hooks, settings) |
| Codex CLI | session start | chain root -> cwd only | native (cwd, parents, root) | TOML transcode `.codex/agents/*.toml` | `.codex/` (config, hooks, rules) |
| Kimi Code | session start | chain root -> cwd only | native | native (Claude-style Markdown) | none (hooks are user-level) |
| GitHub Copilot CLI | session start | path + touched-file ancestors | native | `.github/agents/*.agent.md` | `.github/` |
| Cursor | session start | files in subtree (IDE) | native | `.cursor/agents` | `.cursor/` |
| Devin CLI | session start | lazy on file access + parents | native | native | `.devin/` |
| OpenCode | session start | upward at start, lazy on read/list | native (walks up) | `.opencode/agents` | `.opencode/` |
| Gemini CLI | `context.fileName: AGENTS.md` | ancestors at start, JIT on tool touch | alias of `.gemini/skills` | `.gemini/agents` | `.gemini/` |
| DeepSeek dsh | session start | chain + JIT on read/write/edit | native | not documented | `.dsh/` |
| Z.AI ZCode | root only | none | `.zcode/skills` | user-level | `.zcode/` |

- Universal core = the root `AGENTS.md` map (10/10) + scoped `AGENTS.md` (8/10 automatic;
  Codex, Kimi Code and dsh by chain only) + `.agents/skills` (8/10 native; Claude Code and
  ZCode by projected entry).
- Every dd- skill that touches a governed area opens that area's scoped `AGENTS.md` as step 1,
  so the scoped law reaches every harness by procedure, not by loader luck.
- Sessions launch at the workspace root: a `CLAUDE.md` inside `repos/<slug>/` hides the map
  from a session started there.

## 2. The map and the scoped law

| Surface | Purpose | Belongs |
|---|---|---|
| `AGENTS.md` | the root map: the flow, the roles, the gate invariants, the root, credentials, and one line per scoped file | statements; the index of every other surface |
| `specs/AGENTS.md` | the canon of a specs tree and its status tokens | canon table, status tokens, doctor codes |
| `specs/releases/AGENTS.md` | candidates, phases, task markers, promote | release procedure and commit shapes |
| `specs/backlog/AGENTS.md` | the operator's demand queue and its exits | `BACKLOG.json` shape, intake gate, dispositions |
| `specs/bugs/AGENTS.md` | what a bug is and how it is proposed, recorded, resolved | bug procedure and the redaction rule |
| `specs/memory/AGENTS.md` | current product truth and who writes it | atoms, ownership |
| `specs/ADRs/AGENTS.md` | the decision record | `decisions.jsonl` shape, acceptance |
| `specs/audits/AGENTS.md` | the periodic three-pillar review | audit procedure, findings, closure |
| `.dadaia/AGENTS.md` | the runtime tree: zones, doctor, reprojection, context | zone registry rules, chokepoints |
| `.dadaia/handoff/AGENTS.md` | the handoff lane | emission, schema, ack-on-consume |
| `.dadaia/tmp/AGENTS.md` | the TTL scratch lane | what may be written there and for how long |
| `.dadaia/states/AGENTS.md` | CLI-owned state files | who writes them and by which verb |
| `worktrees/AGENTS.md` | the canonical worktrees | one tree per job, three gates, one review, one venv, hygiene |
| `repos/<slug>/AGENTS.md` | a repo working tree | clean-tree rule, cache redirection |

## 3. Skills — `.agents/skills/dd-*/SKILL.md`

One procedure each; a skill that touches a governed area opens its scoped law as step 1.

| Surface | Purpose | Step-1 law |
|---|---|---|
| `dd-ai-eng-knowhow` | harness literacy and the AI-entity authoring contract | — |
| `dd-architecture-survey` | portfolio-level architecture candidates from bug history | — |
| `dd-audit-project` | the three-pillar audit and its window | `specs/audits/AGENTS.md` |
| `dd-backlog-definition` | backlog curation, the intake gate, dispositions | `specs/backlog/AGENTS.md` |
| `dd-bug-registration` | classify-first bug proposal and its record | `specs/bugs/AGENTS.md` |
| `dd-bug-resolution` | the seven-phase diagnosing method and the resolve record | `specs/bugs/AGENTS.md` |
| `dd-cli-library` | CLI idioms, CLI-owned state, the dev-server registry | `.dadaia/AGENTS.md` |
| `dd-code-review` | the three review axes and the six lenses | `specs/memory/AGENTS.md` |
| `dd-codebase-design` | the deep-module vocabulary and the deletion test | — |
| `dd-domain-modeling` | the repo's domain terms and their one home | — |
| `dd-gitflow-default` | the branch contract, commit shapes, the PR gate | — |
| `dd-grill-me` | the operator grill that precedes a candidate | — |
| `dd-handoff-emitter` | handoff-first emission and ack-on-consume | `.dadaia/handoff/AGENTS.md` |
| `dd-manager-orchestration` | intake, dispatch and the closure pass | — |
| `dd-release-definition` | picking the set and authoring the trio | `specs/releases/AGENTS.md` |
| `dd-release-implementation` | the candidate arc from the first task to the gate | `specs/releases/AGENTS.md` |
| `dd-spec-navigator` | the three-phase session grounding protocol | `specs/AGENTS.md` |

## 4. Personas — `.agents/agents/*.md`

Three roles, no fourth; every retired role is a lens the reviewer applies.

| Surface | Purpose | Belongs |
|---|---|---|
| `dd-product-engineer` | backlog, SPEC, the product-memory pass at closure | role, read_only, model policy |
| `dd-software-engineer` | PLAN/TASKS, production code and its tests | role, read_only, model policy |
| `dd-code-reviewer` | the three-axis review and its six lenses | role, read_only, model policy |

- A statement belongs to exactly one surface: the map indexes, the scoped file rules, the
  skill instructs, the persona declares who acts.
