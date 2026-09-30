# CONTEXT-MAP — the context balance of a dadaia-workspace

Library document. Projected nowhere: `public stage` copies it into `.dadaia/agentic/data/`
with the rest of `data/`, and no projection rule installs it into a runtime tree. Pinned by
`tests/contract/test_context_map.py`.

One row per surface: what it is for, what belongs in it, its soft byte budget, and its measured
size at the last closure — the INSTALLED bytes, with every `<!-- … -->` registry table
rendered as `.dadaia/.venv/bin/dadaia public stage` writes it, not the authored source size. A budget is
soft: a surface over it is a review signal (one purpose, no restated rule), never a build failure
(ADR 0143). `Measured` is rewritten by `UPDATE_CONTEXT_MAP=1 pytest tests/contract/test_context_map.py`.

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

| Surface | Purpose | Belongs | Budget | Measured |
|---|---|---|---|---|
| `AGENTS.md` | the root map: the flow, the roles, the gate invariants, the root, credentials, and one line per scoped file | statements; the index of every other surface | 8192 | 8240 |
| `specs/AGENTS.md` | the canon of a specs tree and its status tokens | canon table, status tokens, doctor codes | 4096 | 3643 |
| `specs/releases/AGENTS.md` | candidates, phases, task markers, promote | release procedure and commit shapes | 4096 | 3669 |
| `specs/backlog/AGENTS.md` | the operator's demand queue and its exits | `BACKLOG.json` shape, intake gate, dispositions | 4096 | 3973 |
| `specs/bugs/AGENTS.md` | what a bug is and how it is proposed, recorded, resolved | bug procedure and the redaction rule | 4096 | 3847 |
| `specs/memory/AGENTS.md` | current product truth and who writes it | atoms, ownership | 4096 | 3938 |
| `specs/ADRs/AGENTS.md` | the decision record | `decisions.jsonl` shape, acceptance | 4096 | 3414 |
| `specs/audits/AGENTS.md` | the periodic three-pillar review | audit procedure, findings, closure | 4096 | 1832 |
| `.dadaia/AGENTS.md` | the runtime tree: zones, doctor, reprojection, context | zone registry rules, chokepoints | 4096 | 4088 |
| `.dadaia/handoff/AGENTS.md` | the handoff lane | emission, schema, ack-on-consume | 4096 | 1757 |
| `.dadaia/tmp/AGENTS.md` | the TTL scratch lane | what may be written there and for how long | 4096 | 1233 |
| `.dadaia/states/AGENTS.md` | CLI-owned state files | who writes them and by which verb | 4096 | 1397 |
| `worktrees/AGENTS.md` | the canonical worktrees | kinds, the merge ritual, one venv, hygiene | 4096 | 3831 |
| `repos/<slug>/AGENTS.md` | a repo working tree | clean-tree rule, cache redirection | 4096 | 3342 |
| `tests/AGENTS.md` | a repo's test tree | admission, intent, size tiers | 4096 | 2694 |

## 3. Skills — `.agents/skills/dd-*/SKILL.md`

One procedure each; a skill that touches a governed area opens its scoped law as step 1.

| Surface | Purpose | Step-1 law | Budget | Measured |
|---|---|---|---|---|
| `dd-ai-eng-knowhow` | harness literacy and the AI-entity authoring contract | — | 6144 | 2878 |
| `dd-architecture-survey` | portfolio-level architecture candidates from bug history | — | 6144 | 4650 |
| `dd-audit-project` | the three-pillar audit and its window | `specs/audits/AGENTS.md` | 6144 | 2834 |
| `dd-backlog-definition` | backlog curation, the intake gate, dispositions | `specs/backlog/AGENTS.md` | 6144 | 3188 |
| `dd-bug-registration` | classify-first bug proposal and its record | `specs/bugs/AGENTS.md` | 6144 | 2856 |
| `dd-bug-resolution` | the seven-phase diagnosing method and the resolve record | `specs/bugs/AGENTS.md` | 6144 | 5203 |
| `dd-cli-library` | CLI idioms, CLI-owned state, the dev-server registry | `.dadaia/AGENTS.md` | 6144 | 5169 |
| `dd-code-review` | the three review axes and the six lenses | `specs/memory/AGENTS.md` | 6144 | 5623 |
| `dd-codebase-design` | the deep-module vocabulary and the deletion test | — | 6144 | 5540 |
| `dd-domain-modeling` | the repo's domain terms and their one home | — | 6144 | 3766 |
| `dd-gitflow-default` | the branch contract, commit shapes, the PR gate | — | 6144 | 4719 |
| `dd-grill-me` | the operator grill that precedes a candidate | — | 6144 | 3367 |
| `dd-handoff-emitter` | handoff-first emission and ack-on-consume | `.dadaia/handoff/AGENTS.md` | 6144 | 2193 |
| `dd-manager-orchestration` | intake, dispatch and the closure pass | — | 6144 | 3749 |
| `dd-release-definition` | picking the set and authoring the trio | `specs/releases/AGENTS.md` | 6144 | 6124 |
| `dd-release-implementation` | the candidate arc from reservation to the gate | `specs/releases/AGENTS.md` | 6144 | 3638 |
| `dd-spec-navigator` | the three-phase session grounding protocol | `specs/AGENTS.md` | 6144 | 3393 |
| `dd-test-stewardship` | test intent, admission, demotion, quarantine | — | 6144 | 4416 |

## 4. Personas — `.agents/agents/*.md`

Three roles, no fourth; every retired role is a lens the reviewer applies.

| Surface | Purpose | Belongs | Budget | Measured |
|---|---|---|---|---|
| `dd-product-engineer` | backlog, SPEC, the product-memory pass at closure | role, read_only, model policy | — | 4614 |
| `dd-software-engineer` | PLAN/TASKS, production code and its tests | role, read_only, model policy | — | 8997 |
| `dd-code-reviewer` | the three-axis review and its six lenses | role, read_only, model policy | — | 6399 |

- A statement belongs to exactly one surface: the map indexes, the scoped file rules, the
  skill instructs, the persona declares who acts.
