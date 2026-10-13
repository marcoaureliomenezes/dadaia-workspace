> **AI agent rules.** This file is generated from
> `dadaia_workspace/public/data/AGENTS.md` by `public install`.
> Do not put project-specific instructions here. Put them in a scoped
> `AGENTS.md` / `CLAUDE.md` inside the repo or directory they govern.

# dadaia-workspace — the map

- Simplicity and lightness are the first law, never above an operator order, the test rule, or security and privacy. The lightest solution that works wins: every gate, step, file and line must earn its place, and a heavier option is chosen only when a lighter one was tried and failed.
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
- A test, or an existing assert, is removed or skipped only on the operator's order.
- Every change minimizes code: DELETE → REBUILD → UPDATE → KEEP → ADD last; verbosity is a defect; documented behavior still works; tests assert behavior not text, mock only boundaries, expect literals; a docstring states only its unit's contract (inputs, output, raises, side effects); no bug id, ADR, FR, AC, task id, candidate, review round or audit id appears in a docstring or comment.
- A fix hardens the contract test in that contract's one home: it tightens an assert or adds the missing partition and never loosens one, a new case is written only when no contract test covers the partition, and the reviewer reverts the fix and confirms the hardened test goes red.
- A failing old test is a question: outside a fix, an assert is moved or narrowed, or a guard's reach narrowed, only with the main thread's ruling named in a `test(...)` commit, and a product-contract change also needs the operator.
- Inventory existing gates and tools first; a new gate, lock, repo, layer or review round states what it buys and names the heavier one it deletes.
- A requirement applied to every task, job or deletion is a gate, states its measured cost per run, and that cost never exceeds one run of the job's `verify:` gate without the operator's ruling.
- Non-blocking findings go to the main thread's intake report (`dd-backlog-definition`).
- The SDD documents (`specs/releases/AGENTS.md`) are the record of progress; numbers, durations and dates are measured or read from a named source, and law text holds no dated snapshot value.

## 2. Who does what

| Work | Owner |
|---|---|
| Intake, grill, dispatch, the review checkpoint, gates | the main thread (the operator's session) |
| Backlog, SPEC, the product-memory pass at closure | `dd-product-engineer` |
| The as-is review, PLAN, job files, production code and tests for new behaviour | `dd-sw-engineer-sr` |
| Tasks fully stated by their AC and `W:` | `dd-sw-engineer-jr` |
| Read-only findings, each a `path:line` or URL | `dd-researcher` |
| Three-axis review + six lenses (architecture, security, QA, product, audit, AI surface) | `dd-code-reviewer` |

- Only the operator accepts an ADR (`specs/ADRs/AGENTS.md` §2).
- Every agent but `dd-researcher` invokes `dd-ai-eng-knowhow` for harness literacy; an AI-entity change follows its AUTHORING contract.

## 3. What is enforced

- One PreToolUse gate blocks: a file-tool write (`Write`, `Edit`, `MultiEdit`, `apply_patch`) creating a new entry at the root, `.dadaia/`, a closed-canon zone or the first level of `repos/`, `worktrees/` per §4 (root_whitelist); a file-tool write (those or `NotebookEdit`) to a PROTECTED path (PROTECTED); a file-tool write (those or `NotebookEdit`) out of the bound scope (out-of-scope); a file-tool write under `repos/<slug>/` outside `specs/audits/`, since `repos/` is merge-only: `specs/audits/` is written directly, the rest by worktree merge, and only `context create` and a repo's first `specs init` write `specs/` directly (_MERGE_ONLY_MESSAGE).
- The gate fails open on: a pre-gate past 10 s (TOOL_TIMEOUT_S); an id-less unbound session under `worktrees/<r>/` (gate_policy); a policy that raises (`pre_gate`); an unreadable payload (`read_stdin_json`); an unreadable registry, judging nothing below `repos/`, `worktrees/`, so only the merge-only block holds there (registered_slugs).
- The Bash hook wrapper accepts the workspace venv's POSIX or Windows Python; when neither is executable, it warns and exits 0, and each context-injection lane prints the `uvx dadaia-workspace init <workspace>` fix.
- Path classes: ADDITIVE (`.dadaia/AGENTS.md`'s output and ephemeral zones) writable; PROTECTED (projected law files and hook wiring, `.dadaia/states`, `hooks`, `agentic`, `sessions`, `.dadaiaignore` and its `[protected]` globs) blocked; the rest MUTATING.
- Every BLOCK carries exactly one fix line, `fix: <command>` or `Operator action: <one act>`; a BLOCK whose fix is itself blocked is a Stall, CRITICAL.
- Git chokepoints (branch contract and scope: `dd-gitflow-default` §2a): pre-push: `.dadaia/AGENTS.md` §3; `worktree.py merge` refuses a job, plain, `define` or `backlog` tree without a valid APPROVED verdict bound to its diff, and a job whose `verify:` does not exit 0; the PR gate is discipline (`dd-gitflow-default` §3b).
- The binding: `.dadaia/.venv/bin/dadaia context show --json`. The gate reads no SDD artifact; procedure is skill-taught and audit-measured, never gated.
- Common behaviour lives in skills and `AGENTS.md`; a persona or hook carries only the surface its harness cannot do without; a harness fact lives in one registry row.

## 4. Where things are written

- Root holds only: `<!-- root -->`; any other entry, the operator's included, needs a pattern in `.dadaiaignore`, which only the operator edits.
- Temp: `.dadaia/tmp/<agent>/<YYYYMMDD>/`; handoffs: `.dadaia/handoff/<context>/`; HTML reports: `.dadaia/reports/<context>/`; worktrees: `worktrees/<repo>/<name>/`; caches: `.dadaia/tmp/<tool>-cache/` (absolute, harness env); anything an MCP server needs: `.dadaia/mcps/<server>/`.
- A repo tree carries source and its own artifacts only — never `.dadaia/`; caches redirect by configuration (`repos/<slug>/AGENTS.md`); unexplained files are presumed yours, uncommitted work not yours is never discarded or restored, and no infrastructure is probed on a guess.
- Credentials live outside the workspace, in the operator's own file: never create, copy, persist, commit, print or report a secret, anywhere; the operator sets a secret from a real terminal, a job that uses it verifies it (never its name), and text is scrubbed before commit, not only at push, with generic names in review and QA text.
- Register every dev server through `dd-cli-library`.

## 5. Scoped law — open before acting there

| Area | File | Governs |
|---|---|---|
| specs tree | `specs/AGENTS.md` | canon, status tokens, load order, artifact authority |
| releases | `specs/releases/AGENTS.md` | candidates, phases, tasks, promote |
| backlog | `specs/backlog/AGENTS.md` | demand queue, `exit`, dispositions |
| bugs | `specs/bugs/AGENTS.md` | what a bug is, propose/confirm, records, resolution |
| memory | `specs/memory/AGENTS.md` | product truth, atoms, ownership |
| ADRs | `specs/ADRs/AGENTS.md` | decisions.jsonl, acceptance |
| audits | `specs/audits/AGENTS.md` | three pillars, remediation release |
| runtime | `.dadaia/AGENTS.md` | zones, doctor, reprojection, chokepoints |
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
| `dd-manager-orchestration` | dispatching the five roles |

- Language: operator preference, default English. Tone: direct, concise, operational.

## 7. Onboarding — three levels

- Level 1 workspace: `uvx dadaia-workspace init [DIR]`; re-running it on an existing workspace is the upgrade.
- Level 2 context: `.dadaia/.venv/bin/dadaia context create <name> --main-repo <url> [--associated-repo <url>]...` clones, hooks and marks ALIVE; only `.dadaia/.venv/bin/dadaia context bind <ctx>` binds a session.
- Level 3 specs: 3a `.dadaia/.venv/bin/dadaia specs init --context <ctx>`; 3b the `dd-audit-project` first pass, done when memory holds real content (never a stamp); 3c `.dadaia/.venv/bin/dadaia context baseline <ctx>` publishes.
- Read the next step from `.dadaia/.venv/bin/dadaia doctor` (`ONBOARDING`) and SessionStart print it with its `fix:` line.
