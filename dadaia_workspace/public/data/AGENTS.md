> **AI agent rules.** This file is generated from
> `dadaia_workspace/public/data/AGENTS.md` by `public install`.
> Do not put project-specific instructions here. Put them in a scoped
> `AGENTS.md` / `CLAUDE.md` inside the repo or directory they govern.

# dadaia-workspace — the map

- One workspace folder; the agent session launches at its root, always.
- Projects live in `repos/<slug>/`; governance (`AGENTS.md`, `.agents/`, `.dadaia/`) lives outside every repo.
- A project is a **context**: one **main repo** (where `specs/` lives) plus **associated repos**; never a monorepo.
- Two rule-file kinds exist: this map and the scoped `AGENTS.md` per governed area (§5); nothing else is law.
- A scoped file is the system of record for its area and takes precedence there — open it before acting in that area.

## 1. The flow

- Classify every demand: Arm A (feature) or Arm B (bug); state the arm before acting.
- Arm A: `demand -> backlog -> as-is review -> release candidate (SPEC/PLAN/job files) -> implementation + review -> memory -> closure -> promote by merging the release PR`.
- Arm B: `propose -> operator confirms -> register -> lowest-level RED test -> root-cause fix -> GREEN -> resolved`.
- Test: does the tool break its own contract? Yes -> Arm B. No -> Arm A.
- A feature enters only through the backlog or an operator demand recorded in the SPEC `Origin`; a confirmed bug is fixed per `specs/bugs/AGENTS.md` §2.
- Every change minimizes code and tests: DELETE → REBUILD → UPDATE → KEEP → ADD last; verbosity is a defect; documented behavior still works; tests assert behavior not text, mock only boundaries, expect literals; fixes never rewrite old asserts.
- The SDD documents (`specs/releases/AGENTS.md`) are the record of progress.

## 2. Who does what

| Work | Owner |
|---|---|
| Intake, grill, dispatch, the review checkpoint, gates | the main thread (the operator's session) |
| Backlog, SPEC, the product-memory pass at closure | `dd-product-engineer` |
| The as-is review, PLAN, job files, production code and tests in any language | `dd-software-engineer` |
| Three-axis review + six lenses (architecture, security, QA, product, audit, AI surface) | `dd-code-reviewer` |

- Three roles, no fourth; only the operator accepts an ADR (`specs/ADRs/AGENTS.md` §2).
- Every agent invokes `dd-ai-eng-knowhow` for harness literacy; an AI-entity change follows its AUTHORING contract.

## 3. What is enforced

- One PreToolUse gate blocks: a file-tool write (`Write`, `Edit`, `MultiEdit`, `apply_patch`) creating a new entry at the root, `.dadaia/`, a closed-canon zone or the first level of `repos/`, `worktrees/` per §4 (root_whitelist); a file-tool write (those or `NotebookEdit`) to a PROTECTED path (PROTECTED); a file-tool write (those or `NotebookEdit`) out of the bound scope (out-of-scope); a file-tool write under `repos/<slug>/` outside `specs/audits/`, since `repos/` is merge-only: `specs/audits/` is written directly, the rest by worktree merge, and only `context create` and a repo's first `specs init` write `specs/` directly.
- The gate fails open on: a pre-gate past 10 s or a missing `.dadaia/.venv`; a Bash write; an id-less unbound session under `worktrees/<r>/`; a policy that raises; an unreadable payload; an unreadable registry, judging nothing below `repos/`, `worktrees/`, so only the merge-only block holds there.
- Path classes: ADDITIVE (`.dadaia/AGENTS.md`'s output and ephemeral zones) writable; PROTECTED (projected law files and hook wiring, `.dadaia/states`, `hooks`, `agentic`, `sessions`, `.dadaiaignore` and its `[protected]` globs) blocked; the rest MUTATING.
- Every BLOCK carries exactly one fix line, `fix: <command>` or `Operator action: <one act>`; a BLOCK whose fix is itself blocked is a Stall, CRITICAL.
- Git chokepoints (branch names: `specs/constitution.md` `gitflow:`): pre-push admits the work branch, a job branch `wt/<M.m.p>-rc<N>/<job>` and a backlog branch `wt/backlog/<slug>`, plus a principal or integration birth when origin has neither gitflow branch or the birth publishes no new objects; it refuses a non-canon `specs/` path or a denylisted secret; `worktree.py merge` refuses a job, plain, `define` or `backlog` tree without a valid APPROVED verdict bound to its diff, and a job without a green `verify:`; the PR gate is discipline (`dd-gitflow-default` §3b).
- The binding: `.dadaia/.venv/bin/dadaia context show --json`.
- The gate reads no SDD artifact; procedure is skill-taught and audit-measured, never gated.

## 4. Where things are written

- Root holds only: `<!-- root -->`; any other entry, the operator's included, needs a pattern in `.dadaiaignore`, which only the operator edits.
- Temp: `.dadaia/tmp/<agent>/<YYYYMMDD>/`; handoffs: `.dadaia/handoff/<context>/`; HTML reports: `.dadaia/reports/<context>/`; worktrees: `worktrees/<repo>/<name>/`; caches: `.dadaia/tmp/<tool>-cache/` (absolute, harness env); anything an MCP server needs: `.dadaia/mcps/<server>/`.
- A repo tree carries source and its own artifacts only — never `.dadaia/`; caches redirect by configuration (`repos/<slug>/AGENTS.md`).
- Credentials live outside the workspace, in the operator's own file: never create, copy, persist, commit, print or report a secret, anywhere.
- Register every dev server through `dd-cli-library`.

## 5. Scoped law — open before acting there

| Area | File | Governs |
|---|---|---|
| specs tree | `specs/AGENTS.md` | canon, status tokens, doctor codes |
| releases | `specs/releases/AGENTS.md` | candidates, phases, tasks, promote |
| backlog | `specs/backlog/AGENTS.md` | demand queue, `exit`, dispositions |
| bugs | `specs/bugs/AGENTS.md` | what a bug is, propose/confirm, records, resolution |
| memory | `specs/memory/AGENTS.md` | product truth, atoms, ownership |
| ADRs | `specs/ADRs/AGENTS.md` | decisions.jsonl, acceptance |
| audits | `specs/audits/AGENTS.md` | three pillars, remediation release |
| runtime | `.dadaia/AGENTS.md` | zones, doctor, reprojection, chokepoints, context freeze |
| handoff | `.dadaia/handoff/AGENTS.md` | emission, schema, ack |
| tmp / states | `.dadaia/tmp/AGENTS.md`, `.dadaia/states/AGENTS.md` | TTL, state files |
| a repo | `repos/<slug>/AGENTS.md` | clean tree, caches, tests |
| worktrees | `worktrees/AGENTS.md` | plain changes plus release jobs/tasks, two gates, one review, one venv |

## 6. Skills — `.agents/skills/dd-*`

| Skill | Use it for |
|---|---|
| `dd-grill-me` | the mandatory questioning session before any SPEC |
| `dd-backlog-definition` | curating the backlog from operator demand |
| `dd-release-definition` | SPEC -> PLAN -> job files for a candidate |
| `dd-release-implementation` | tasks, push green, closure order |
| `dd-code-review` | three axes, six lenses, slop detection |
| `dd-bug-registration`, `dd-bug-resolution` | Arm B end to end |
| `dd-gitflow-default` | branches, PRs, commit shapes |
| `dd-handoff-emitter` | machine-readable completion records |
| `dd-audit-project` | the periodic three-pillar audit |
| `dd-spec-navigator` | finding truth in `specs/` |
| `dd-cli-library` | the `dadaia` verbs, skill scripts, dev servers |
| `dd-ai-eng-knowhow` | harness literacy and AI-entity authoring |
| `dd-manager-orchestration` | dispatching the three roles |

- Language: operator preference, default English. Tone: direct, concise, operational.

## 7. Onboarding — three levels

- Level 1 workspace: `uvx dadaia-workspace init [DIR]`; re-running it on an existing workspace is the upgrade.
- Level 2 context: `.dadaia/.venv/bin/dadaia context create <name> --main-repo <url> [--associated-repo <url>]...` clones, hooks and marks ALIVE; only `.dadaia/.venv/bin/dadaia context bind <ctx>` binds a session.
- Level 3 specs: 3a `.dadaia/.venv/bin/dadaia specs init --context <ctx>`; 3b the `dd-audit-project` first pass, done when memory holds real content (never a stamp); 3c `.dadaia/.venv/bin/dadaia context baseline <ctx>` publishes.
- Read the next step from `.dadaia/.venv/bin/dadaia doctor` (`ONBOARDING`) and SessionStart print it with its `fix:` line.
