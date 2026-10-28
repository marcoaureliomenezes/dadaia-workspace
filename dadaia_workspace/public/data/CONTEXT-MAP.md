# CONTEXT-MAP — the context balance of a dadaia-workspace

Library document. Projected nowhere: `public install` copies it into `.dadaia/agentic/data/`
with the rest of `data/`, and no projection rule installs it into a runtime tree.

One row per surface: what it is for and what belongs in it. A surface's size is a soft
review signal (one purpose, no restated rule), never a build failure; a SKILL.md's
line limit is a doctor warning (`SKILL-MD-LENGTH`).

The `Surface` column names the path or entity as it appears in an installed workspace.

## 1. Load triggers, per harness

One row per registered harness: the `HARNESS_RECORDS` row names it, `.dadaia/.venv/bin/dadaia harness list` lists it, and the row's `directory` is its own dir.

| Harness (registry `name`) | Root `AGENTS.md` | Scoped `AGENTS.md` | `.agents/skills/dd-*` | `.agents/agents/dd-*.md` | Own dir (registry `directory`) |
|---|---|---|---|---|---|
| Claude Code (`claude`) | session start, iff no `CLAUDE.md` on the path | attached when a file in that dir is Read | via per-skill symlink under `.claude/skills/` | via per-file symlink under `.claude/agents/` | the row's `directory` |
| Codex CLI (`codex`) | session start | chain root -> cwd only | native (cwd, parents, root) | TOML transcode `.codex/agents/*.toml` | the row's `directory` |
| Kimi Code (`kimi-code`) | session start | chain root -> cwd only | native | native (Claude-style Markdown) | the row's `directory` (none: hooks are user-level) |
| GitHub Copilot CLI (`copilot`) | session start | path + touched-file ancestors | native | `.github/agents/*.agent.md` | the row's `directory` |
| Cursor (`cursor`) | session start | files in subtree (IDE) | native | `.cursor/agents` | the row's `directory` |
| Devin CLI (`devin`) | session start | lazy on file access + parents | native | native | the row's `directory` |

- Universal core = the root `AGENTS.md` map + scoped `AGENTS.md` + `.agents/skills`. Codex and
  Kimi Code load scoped files by chain only; Claude Code reaches skills by projected entry.
- Every dd- skill that touches a governed area opens that area's scoped `AGENTS.md` as step 1,
  so the scoped law reaches every harness by procedure, not by loader luck.
- Sessions launch at the workspace root: a `CLAUDE.md` inside `repos/<slug>/` hides the map
  from a session started there.

## 2. The map and the scoped law

| Surface | Purpose | Belongs |
|---|---|---|
| `AGENTS.md` | the root map: the flow, the roles, the gate invariants, the root, credentials, and one line per scoped file | statements; the index of every other surface |
| `specs/AGENTS.md` | the canon of a specs tree and its status tokens | canon table, status tokens, load order |
| `specs/releases/AGENTS.md` | candidates, phases, promote | release procedure |
| `specs/backlog/AGENTS.md` | the operator's demand queue and its exits | `BACKLOG.json` shape, intake gate, dispositions |
| `specs/bugs/AGENTS.md` | what a bug is and how it is proposed, recorded, resolved | bug procedure and the redaction rule |
| `specs/memory/AGENTS.md` | current product truth and who writes it | atoms, ownership |
| `specs/ADRs/AGENTS.md` | the decision record | `decisions.jsonl` shape, acceptance |
| `specs/audits/AGENTS.md` | the periodic three-pillar review | audit procedure, findings, closure |
| `.dadaia/AGENTS.md` | the runtime tree: zones, doctor, reprojection, context | zone registry rules, chokepoints |
| `.dadaia/handoff/AGENTS.md` | the handoff lane | emission, schema, ack-on-consume |
| `.dadaia/tmp/AGENTS.md` | the TTL scratch lane | what may be written there and for how long |
| `.dadaia/states/AGENTS.md` | CLI-owned state files | who writes them and by which verb |
| `worktrees/AGENTS.md` | the canonical worktrees | the rc hierarchy and lanes, two gates, one review, one venv, hygiene |
| `repos/<slug>/AGENTS.md` | a repo working tree | clean-tree rule, cache redirection, the `verify:` and `tests:` lines |

## 3. Skills — `.agents/skills/dd-*/SKILL.md`

One procedure each; a skill that touches a governed area opens its scoped law as step 1.

| Surface | Purpose | Step-1 law |
|---|---|---|
| `dd-ai-eng-knowhow` | harness literacy and the AI-entity authoring contract | — |
| `dd-audit-project` | the three-pillar audit and its window | `specs/audits/AGENTS.md` |
| `dd-backlog-definition` | backlog curation, the intake gate, dispositions | `specs/backlog/AGENTS.md` |
| `dd-bug-registration` | classify-first bug proposal and its record | `specs/bugs/AGENTS.md` |
| `dd-bug-resolution` | the seven-phase diagnosing method and the resolve record | `specs/bugs/AGENTS.md` |
| `dd-cli-library` | CLI idioms, CLI-owned state, the dev-server registry | `.dadaia/AGENTS.md` |
| `dd-code-review` | the three review axes and the six lenses | `specs/memory/AGENTS.md` |
| `dd-gitflow-default` | the branch contract, commit shapes, the merge gate | — |
| `dd-grill-me` | the operator grill that precedes a candidate | — |
| `dd-handoff-emitter` | handoff-first emission and ack-on-consume | `.dadaia/handoff/AGENTS.md` |
| `dd-manager-orchestration` | intake, dispatch and the closure pass | — |
| `dd-release-definition` | picking the set and authoring the SPEC, PLAN and job files | `specs/releases/AGENTS.md` |
| `dd-release-implementation` | the candidate arc from the first task to the gate | `specs/releases/AGENTS.md` |
| `dd-spec-navigator` | the three-phase session grounding protocol | `specs/AGENTS.md` |

## 4. Personas — `.agents/agents/*.md`

One file per persona. Each file's frontmatter declares its role and tools; the
root map's Who does what table (`AGENTS.md`, Who does what) indexes them.

| Surface | Mandate |
|---|---|
| `dd-product-engineer` | its persona file |
| `dd-sw-engineer-sr` | its persona file |
| `dd-sw-engineer-jr` | its persona file |
| `dd-researcher` | its persona file |
| `dd-code-reviewer` | its persona file |
