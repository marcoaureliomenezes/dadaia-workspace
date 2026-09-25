# CONTEXT-MAP — the context balance of a dadaia-workspace

Library document. Projected nowhere: `public stage` copies it into `.dadaia/agentic/data/`
with the rest of `data/`, and no projection rule installs it into a runtime tree. Pinned by
`tests/contract/test_context_map.py`.

One row per surface: what it is for, what belongs in it, its byte ceiling, and its measured
size at the last closure — the INSTALLED bytes, with every `<!-- … -->` registry table
rendered as `.dadaia/.venv/bin/dadaia public stage` writes it, not the authored source size. Ceilings are
ratchets — they move down. `Measured` is rewritten by
`UPDATE_CONTEXT_MAP=1 pytest tests/contract/test_context_map.py`; a value above its ceiling
fails the build.

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

| Surface | Purpose | Belongs | Ceiling | Measured |
|---|---|---|---|---|
| `AGENTS.md` | the root map: the flow, the roles, the gate invariants, the root, credentials, and one line per scoped file | statements; the index of every other surface | 8192 | 7211 |
| `specs/AGENTS.md` | the canon of a specs tree and its status tokens | canon table, status tokens, doctor codes | 4096 | 3661 |
| `specs/releases/AGENTS.md` | candidates, phases, task markers, promote | release procedure and commit shapes | 4096 | 3416 |
| `specs/backlog/AGENTS.md` | the operator's demand queue and its exits | `BACKLOG.json` shape, intake gate, dispositions | 4096 | 4081 |
| `specs/bugs/AGENTS.md` | what a bug is and how it is proposed, recorded, resolved | bug procedure and the redaction rule | 4096 | 4046 |
| `specs/memory/AGENTS.md` | current product truth and who writes it | atoms, Part 1/Part 2, ownership | 4096 | 3760 |
| `specs/ADRs/AGENTS.md` | the decision record | `decisions.jsonl` shape, acceptance | 4096 | 3476 |
| `specs/audits/AGENTS.md` | the periodic three-pillar review | audit procedure, findings, closure | 4096 | 1813 |
| `.dadaia/AGENTS.md` | the runtime tree: zones, doctor, reprojection, context | zone registry rules, chokepoints | 4096 | 4078 |
| `.dadaia/handoff/AGENTS.md` | the handoff lane | emission, schema, ack-on-consume | 4096 | 1635 |
| `.dadaia/tmp/AGENTS.md` | the TTL scratch lane | what may be written there and for how long | 4096 | 1135 |
| `.dadaia/states/AGENTS.md` | CLI-owned state files | who writes them and by which verb | 4096 | 1427 |
| `repos/<slug>/AGENTS.md` | a repo working tree | clean-tree rule, cache redirection | 4096 | 3191 |
| `tests/AGENTS.md` | a repo's test tree | admission, intent, size tiers | 4096 | 2694 |

## 3. Skills — `.agents/skills/dd-*/SKILL.md`

One procedure each; a skill that touches a governed area opens its scoped law as step 1.

| Surface | Purpose | Step-1 law | Ceiling | Measured |
|---|---|---|---|---|
| `dd-ai-eng-knowhow` | harness literacy and the AI-entity authoring contract | — | 6144 | 2976 |
| `dd-architecture-survey` | portfolio-level architecture candidates from bug history | — | 6144 | 4650 |
| `dd-audit-project` | the three-pillar audit and its window | `specs/audits/AGENTS.md` | 6144 | 2844 |
| `dd-backlog-definition` | backlog curation, the intake gate, dispositions | `specs/backlog/AGENTS.md` | 6144 | 3265 |
| `dd-bug-registration` | classify-first bug proposal and its record | `specs/bugs/AGENTS.md` | 6144 | 2782 |
| `dd-bug-resolution` | the seven-phase diagnosing method and the resolve record | `specs/bugs/AGENTS.md` | 6144 | 5356 |
| `dd-cli-library` | CLI idioms, CLI-owned state, the dev-server registry | `.dadaia/AGENTS.md` | 6144 | 4888 |
| `dd-code-review` | the three review axes and the six lenses | `specs/memory/AGENTS.md` | 6144 | 4783 |
| `dd-codebase-design` | the deep-module vocabulary and the deletion test | — | 6144 | 5540 |
| `dd-domain-modeling` | the repo's domain terms and their one home | — | 6144 | 3766 |
| `dd-gitflow-default` | the branch contract, commit shapes, the PR gate | — | 6144 | 4723 |
| `dd-grill-me` | the operator grill that precedes a candidate | — | 6144 | 3256 |
| `dd-handoff-emitter` | handoff-first emission and ack-on-consume | `.dadaia/handoff/AGENTS.md` | 6144 | 2174 |
| `dd-manager-orchestration` | intake, dispatch and the closure pass | — | 6144 | 3661 |
| `dd-release-definition` | picking the set and authoring the trio | `specs/releases/AGENTS.md` | 6144 | 4638 |
| `dd-release-implementation` | the candidate arc from reservation to the gate | `specs/releases/AGENTS.md` | 6144 | 3351 |
| `dd-spec-navigator` | the three-phase session grounding protocol | `specs/AGENTS.md` | 6144 | 5204 |
| `dd-test-stewardship` | test intent, admission, demotion, quarantine | — | 6144 | 4178 |

## 4. Personas — `.agents/agents/*.md`

Three roles, no fourth; every retired role is a lens the reviewer applies.

| Surface | Purpose | Belongs | Ceiling | Measured |
|---|---|---|---|---|
| `dd-product-engineer` | backlog, SPEC, the product-memory pass at closure | role, activity class, model policy | — | 4495 |
| `dd-software-engineer` | PLAN/TASKS, production code and its tests | role, activity class, model policy | — | 8754 |
| `dd-code-reviewer` | the three-axis review and its six lenses | role, activity class, model policy | — | 6511 |

- A statement belongs to exactly one surface: the map indexes, the scoped file rules, the
  skill instructs, the persona declares who acts.
