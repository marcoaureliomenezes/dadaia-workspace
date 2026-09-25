> **AI agent rules.** This file is generated from
> `dadaia_workspace/public/data/AGENTS.md` by `dadaia public install`.
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
- Arm B: `propose -> operator confirms -> register -> RED test -> root-cause fix -> GREEN -> resolved`.
- Test: does the tool break its own contract? Yes -> Arm B, fixed now. No -> Arm A, via a candidate.
- A feature enters only through the backlog or an operator demand recorded in the SPEC `Origin`; a confirmed bug is fixed immediately.
- No workflow engine: the SDD documents (`specs/releases/AGENTS.md`) are the record of progress.

## 2. Who does what

| Work | Owner |
|---|---|
| Intake, grill, dispatch, the review checkpoint, gates | the main thread (the operator's session) |
| Backlog, SPEC, the product-memory pass at closure | `dd-product-engineer` |
| The as-is review, PLAN, TASKS, production code and tests in any language | `dd-software-engineer` |
| Three-axis review + six lenses (architecture, security, QA, product, audit, AI surface) | `dd-code-reviewer` |

- Three roles, no fourth; every retired role is a lens the reviewer applies and the engineer anticipates.
- Every agent invokes `dd-ai-eng-knowhow` for harness literacy; an AI-entity change follows its AUTHORING contract.

## 3. What is enforced

- One PreToolUse gate blocks exactly three things: a new workspace-root entry (§4), a `dadaia`/`pip` run outside `.dadaia/.venv/bin/`, a PROTECTED or out-of-scope write.
- Path classes: ADDITIVE (the append-only governance areas of `specs/AGENTS.md` and the runtime scratch zones of `.dadaia/AGENTS.md`) always writable; PROTECTED (session state, the projected law files) blocked; everything else MUTATING, scope-judged under `repos/<slug>/`.
- Every BLOCK carries exactly one `fix: <command>` line; a BLOCK whose fix is itself blocked is a Stall, CRITICAL.
- Git chokepoints (branch names: `specs/constitution.md` `gitflow:`): pre-push allows the work branch and refuses the integration and principal branches, a non-canon `specs/` path or a denylisted secret; both PRs need CI green and a `dd-code-reviewer` APPROVED verdict; no CI job calls a model API. Mechanics: `dd-gitflow-default`, `.dadaia/AGENTS.md`.
- Races surface, never block; context binding: `.dadaia/.venv/bin/dadaia context show --json`, `.dadaia/.venv/bin/dadaia context bind <ctx>`.
- The gate reads no SDD artifact; procedure is skill-taught and audit-measured, never gated.

## 4. Where things are written

- Root holds only: `<!-- root -->`; what the operator created by hand stays; a tool's extra entry needs a glob in `.dadaia/states/instance_exceptions.txt`.
- Temp: `.dadaia/tmp/<agent>/<YYYYMMDD>/`; handoffs: `.dadaia/handoff/<context>/`; HTML reports: `repos/<slug>/reports/<agent>/`; caches: `.dadaia/.cache/`, `.dadaia/mcps/<server>/`.
- A repo tree carries source and its own artifacts only — never `.dadaia/`; caches redirect by configuration (`repos/<slug>/AGENTS.md`).
- Credentials live only in the operator's root `.env`: never create, copy, persist, commit, print or report a secret, anywhere.
- Invoke `.dadaia/.venv/bin/dadaia` by absolute path; register every dev server through `dd-cli-library`.

## 5. Scoped law — open before acting there

| Area | File | Governs |
|---|---|---|
| specs tree | `specs/AGENTS.md` | canon, status tokens, doctor codes |
| releases | `specs/releases/AGENTS.md` | candidates, phases, task markers, promote, commit shapes |
| backlog | `specs/backlog/AGENTS.md` | demand queue, `exit`, dispositions |
| bugs | `specs/bugs/AGENTS.md` | what a bug is, propose/confirm, records, resolution |
| memory | `specs/memory/AGENTS.md` | product truth, atoms, Part 1/Part 2, ownership |
| ADRs | `specs/ADRs/AGENTS.md` | decisions.jsonl, acceptance |
| audits | `specs/audits/AGENTS.md` | three pillars, remediation release |
| runtime | `.dadaia/AGENTS.md` | zones, doctor, reprojection, chokepoints, context freeze |
| handoff | `.dadaia/handoff/AGENTS.md` | emission, schema, ack |
| tmp / states | `.dadaia/tmp/AGENTS.md`, `.dadaia/states/AGENTS.md` | TTL, state files |
| a repo | `repos/<slug>/AGENTS.md` | clean tree, caches, tests |

## 6. Skills — `.agents/skills/dd-*`

| Skill | Use it for |
|---|---|
| `dd-grill-me` | the mandatory questioning session before any SPEC |
| `dd-backlog-definition` | curating the backlog from operator demand |
| `dd-release-definition` | SPEC -> PLAN -> TASKS for a candidate |
| `dd-release-implementation` | tasks, push green, closure order |
| `dd-code-review` | three axes, six lenses, slop detection |
| `dd-bug-registration`, `dd-bug-resolution` | Arm B end to end |
| `dd-test-stewardship` | test intent, size, demotion, pruning |
| `dd-gitflow-default` | branches, PRs, commit shapes |
| `dd-handoff-emitter` | machine-readable completion records |
| `dd-audit-project` | the periodic three-pillar audit |
| `dd-spec-navigator` | finding truth in `specs/`; the glossary |
| `dd-cli-library` | the `dadaia` verbs, skill scripts, dev servers |
| `dd-ai-eng-knowhow` | harness literacy and AI-entity authoring |
| `dd-architecture-survey`, `dd-codebase-design`, `dd-domain-modeling` | design vocabulary for PLAN and SPEC |
| `dd-manager-orchestration` | dispatching the three roles |

- Language: operator preference, default English. Tone: direct, concise, operational.
- Instance state: `.dadaia/.venv/bin/dadaia context show --json`, `.dadaia/.venv/bin/dadaia doctor`, `.dadaia/.venv/bin/dadaia public doctor`, `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status`.

## 7. Onboarding — three levels

- Level 1 workspace: `uvx dadaia-workspace init [DIR]`; re-running it on an existing workspace is the upgrade.
- Level 2 context: `.dadaia/.venv/bin/dadaia context create <name> --main-repo <url> [--associated-repo <url>]...` clones, hooks, marks ALIVE and binds in one step.
- Level 3 specs: `.dadaia/.venv/bin/dadaia specs init --context <ctx>` (`--replace-foreign` moves a foreign tree to `specs-bkp/`), then the `dd-audit-project` first pass fills memory.
- A new project in an existing workspace is levels 2 + 3; procedure: `dd-cli-library` (1-2), `dd-audit-project` (3).
- The next step is never guessed: `.dadaia/.venv/bin/dadaia doctor` (`ONBOARDING`) and SessionStart print it with its `fix:` line.
