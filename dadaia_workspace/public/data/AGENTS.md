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
- Arm A: `demand -> backlog -> as-is review -> release candidate (SPEC/PLAN/TASKS) -> implementation + review -> memory -> closure -> promote by merging the release PR`.
- Arm B: `propose -> operator confirms -> register -> lowest-level RED test -> root-cause fix -> GREEN -> resolved`.
- Test: does the tool break its own contract? Yes -> Arm B. No -> Arm A.
- A feature enters only through the backlog or an operator demand recorded in the SPEC `Origin`; a confirmed bug is fixed per `specs/bugs/AGENTS.md` §2.
- Every change minimizes code and tests: DELETE → REBUILD → UPDATE → KEEP → ADD last; verbosity is a defect; documented behavior still works; tests assert behavior not text, mock only boundaries, expect literals; fixes never rewrite old asserts.
- No workflow engine: the SDD documents (`specs/releases/AGENTS.md`) are the record of progress.

## 2. Who does what

| Work | Owner |
|---|---|
| Intake, grill, dispatch, the review checkpoint, gates | the main thread (the operator's session) |
| Backlog, SPEC, the product-memory pass at closure | `dd-product-engineer` |
| The as-is review, PLAN, TASKS, production code and tests in any language | `dd-software-engineer` |
| Three-axis review + six lenses (architecture, security, QA, product, audit, AI surface) | `dd-code-reviewer` |

- Three roles, no fourth; every retired role is a lens the reviewer applies and the engineer anticipates; only the operator accepts an ADR (`specs/ADRs/AGENTS.md` §2).
- Every agent invokes `dd-ai-eng-knowhow` for harness literacy; an AI-entity change follows its AUTHORING contract.

## 3. What is enforced

- One PreToolUse gate blocks: a file-tool write (`Write`, `Edit`, `MultiEdit`, `apply_patch`) creating a new entry at the root, `.dadaia/`, a closed-canon zone or the first level of `repos/`, `worktrees/` per §4 (root_whitelist); a Bash command of any position in the line whose first word is the `dadaia` CLI or `python -m dadaia_workspace` outside `.dadaia/.venv/bin/` (venv_guard); a file-tool write (those or `NotebookEdit`) to a PROTECTED path (PROTECTED); a file-tool write (those or `NotebookEdit`) out of the bound scope (out-of-scope); a file-tool write under `repos/<slug>/` outside `specs/audits/`, since `repos/` is merge-only (ADR 0105).
- The venv guard judges every command of a Bash line: after `&&`, a semicolon, `|` or `(`, behind an env assignment or a shell keyword, and as an absolute or relative path to a `dadaia` outside the venv. Not judged: PowerShell syntax, `$(…)`, backticks, `bash -c`, the `env`, `xargs`, `sudo` and `exec` wrappers, heredoc bodies and `time` options. It reads bash syntax, so on Windows an unquoted backslash path loses its backslashes as in Git Bash; unbalanced quotes fail open; a quoted argument made only of operator characters reads as a boundary, a false block.
- The gate fails open on: a missing `.dadaia/.venv` (ADR 0067); a pre-gate past 10 s (ADR 0118); a Bash write (ADRs 0096, 0103, 0133); an id-less unbound session under `worktrees/<r>/` (ADR 0116); a policy that raises (`pre_gate`); an unreadable payload (`read_stdin_json`); an unreadable registry, judging nothing below `repos/`, `worktrees/`, so only the merge-only block holds there (ADR 0132).
- Path classes: ADDITIVE (`.dadaia/AGENTS.md`'s output and ephemeral zones) writable; PROTECTED (`workspace_layout.CORE_FLOOR`, `sdd_gate._HOOK_WIRING`, the install ledger, the `.dadaiaignore` `[protected]` globs, repo-relative) blocked; the rest MUTATING.
- Writes under `repos/<slug>/`: `specs/audits/` directly, the rest by worktree merge; only `context create` and a repo's first `specs init` write `specs/` directly (ADR 0154).
- Every BLOCK carries exactly one fix line, `fix: <command>` or `Operator action: <one act>` (ADR 0158); a BLOCK whose fix is itself blocked is a Stall, CRITICAL.
- Git chokepoints (branch names: `specs/constitution.md` `gitflow:`): pre-push allows only the work branch, a job branch `wt/<M.m.p>-rc<N>/<job>` and a backlog branch `wt/backlog/<slug>`, and refuses a non-canon `specs/` path or a denylisted secret; both PRs need the repo's `verify:` line passing and a `dd-code-reviewer` APPROVED verdict, which `worktree.py merge` enforces on a job merge.
- Races surface, never block; the binding: `.dadaia/.venv/bin/dadaia context show --json`.
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
| releases | `specs/releases/AGENTS.md` | candidates, phases, task markers, promote, commit shapes |
| backlog | `specs/backlog/AGENTS.md` | demand queue, `exit`, dispositions |
| bugs | `specs/bugs/AGENTS.md` | what a bug is, propose/confirm, records, resolution |
| memory | `specs/memory/AGENTS.md` | product truth, atoms, ownership |
| ADRs | `specs/ADRs/AGENTS.md` | decisions.jsonl, acceptance |
| audits | `specs/audits/AGENTS.md` | three pillars, remediation release |
| runtime | `.dadaia/AGENTS.md` | zones, doctor, reprojection, chokepoints, context freeze |
| handoff | `.dadaia/handoff/AGENTS.md` | emission, schema, ack |
| tmp / states | `.dadaia/tmp/AGENTS.md`, `.dadaia/states/AGENTS.md` | TTL, state files |
| a repo | `repos/<slug>/AGENTS.md` | clean tree, caches, tests |
| worktrees | `worktrees/AGENTS.md` | one tree per job, three gates, one review, one venv |

## 6. Skills — `.agents/skills/dd-*`

| Skill | Use it for |
|---|---|
| `dd-grill-me` | the mandatory questioning session before any SPEC |
| `dd-backlog-definition` | curating the backlog from operator demand |
| `dd-release-definition` | SPEC -> PLAN -> TASKS for a candidate |
| `dd-release-implementation` | tasks, push green, closure order |
| `dd-code-review` | three axes, six lenses, slop detection |
| `dd-bug-registration`, `dd-bug-resolution` | Arm B end to end |
| `dd-gitflow-default` | branches, PRs, commit shapes |
| `dd-handoff-emitter` | machine-readable completion records |
| `dd-audit-project` | the periodic three-pillar audit |
| `dd-spec-navigator` | finding truth in `specs/` |
| `dd-cli-library` | the `dadaia` verbs, skill scripts, dev servers |
| `dd-ai-eng-knowhow` | harness literacy and AI-entity authoring |
| `dd-architecture-survey`, `dd-codebase-design`, `dd-domain-modeling` | design vocabulary for PLAN and SPEC |
| `dd-manager-orchestration` | dispatching the three roles |

- Language: operator preference, default English. Tone: direct, concise, operational.
- Instance state: `.dadaia/.venv/bin/dadaia doctor`, `.dadaia/.venv/bin/dadaia public doctor`, `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status --specs <specs-dir>`.

## 7. Onboarding — three levels

- Level 1 workspace: `uvx dadaia-workspace init [DIR]`; re-running it on an existing workspace is the upgrade.
- Level 2 context: `.dadaia/.venv/bin/dadaia context create <name> --main-repo <url> [--associated-repo <url>]...` clones, hooks and marks ALIVE; only `.dadaia/.venv/bin/dadaia context bind <ctx>` binds a session.
- Level 3 specs: 3a `.dadaia/.venv/bin/dadaia specs init --context <ctx>`; 3b the `dd-audit-project` first pass, done when memory holds real content (never a stamp); 3c `.dadaia/.venv/bin/dadaia context baseline <ctx>` publishes.
- The next step is never guessed: `.dadaia/.venv/bin/dadaia doctor` (`ONBOARDING`) and SessionStart print it with its `fix:` line.
