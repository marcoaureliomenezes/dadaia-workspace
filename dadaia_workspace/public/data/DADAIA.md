# DADAIA.md — the workspace system prompt

- The complete always-on law: one file, every rule, one source.
- Source: `dadaia_workspace/public/data/DADAIA.md`; projected to the workspace root, `.codex/`, `.kimi-code/`.
- Claude Code reaches it via `CLAUDE.md` -> `AGENTS.md` -> `DADAIA.md` — no second projected copy.
- Sections cross-reference by name; each fact is stated once.
- A scoped `AGENTS.md` governs its own subtree and takes precedence there.
- Exactly two rule-file kinds ship: this file, and scoped `AGENTS.md` — anything else is the operator's own.

---

## 1. The flow — the mandatory default

### 1.1 The two arms

- Classify every demand as Arm A (feature) or Arm B (bug); state which arm before acting.
- Deviating needs an explicit, confirmed operator request; default to the flow when unsure.
- Arm A: `demand -> backlog-definition -> release-definition -> implementation+reviews/gates -> audit`.
- Arm B: `register -> reproduce on the executed path -> RED test -> root-cause fix -> GREEN -> resolved record -> commit`.
- Test: does the tool violate a contract it already promises? Yes -> Arm B, fixed on the spot. No -> Arm A.
- A bug is fixed immediately, outside release material.
- A feature enters only through the backlog.

### 1.2 Dispatch

- Arm A is agent-dispatched: each stage runs by dispatching the owning agent (§2) against the SDD documents (§6).
- Fan out explicitly; the SDD documents are the record of progress — there is no workflow engine.

---

## 2. Who does what

### 2.1 Ownership

| The work | Owner |
|---|---|
| Backlog curation — what enters, matures, leaves `specs/backlog/**` | `project-manager` |
| Coordination, grill-me intake, dispatch | `project-manager` |
| SPEC / PLAN / TASKS / CLOSURE, and `specs/memory/**` | `product-engineer` |
| Architecture: DRAFT, REVIEW, ONBOARD; root-cause and fidelity gates | `software-architect` |
| Production code and its tests, in any language | `software-engineer` |
| E2E, test pyramid, deploy validation; closes each `rc-N` | `qa-engineer` |
| Six-axis review before a PR | `code-reviewer` |
| Vulnerabilities, secrets, CVEs; the push verdict (§4.2) | `security-reviewer` |
| Agents, skills, rules, workflows, commands, hooks — the AI surface | `ai-engineer` |
| Drift audits; dispatches evidence agents; scores compliance | `project-auditor` |

### 2.2 Cross-cutting

- `product-engineer` authors releases from the PM-curated backlog; it never curates the backlog itself.
- Every agent invokes `dd-ai-eng-knowhow` for harness literacy.
- Only `ai-engineer` reads its depth siblings to author or audit the AI-entity surface.
- Every other agent dispatches `ai-engineer` for that depth.

---

## 3. What is enforced deterministically

### 3.1 The gate

- One PreToolUse entrypoint, `dadaia_workspace.hooks.pre_gate`, reads each tool payload once.
- Evaluates three policies in fixed order, first block wins: root whitelist -> venv guard -> SDD gate.
- Root whitelist blocks a file-tool write that would create a new top-level workspace-root entry (§5.1).
- Venv guard (`Bash` only) matches fixed leading tokens `dadaia`, `pip`, `python -m dadaia_workspace` run outside `.dadaia/.venv/bin/`.
- The venv-guard block message carries the corrected command.
- SDD gate evaluates path class × presence × phase × mode.
- Path classes are context-relative: the same `specs/` taxonomy applies at the workspace root and inside every `repos/<slug>/`.

### 3.2 Path classes

| Class | Paths | Verdict |
|---|---|---|
| ADDITIVE | `specs/bugs\|backlog\|audits/`, each area's `_archive/*_histo.jsonl`, `.dadaia/reports\|handoff\|tmp/` | Always writable |
| MEMORY | `specs/memory/` | Writable in `DEFINITION` and `CLOSURE` phase |
| MUTATING | everything else in-repo | Writable; records advisory presence |
| PROTECTED | `.dadaia/sessions/`, projected law files (§8.2) | Blocked |

- ADDITIVE's record contract — immutable core, write-once, mutable governance — is audited, not gated.
- No FROZEN class: no root `_archive/` exists under `specs/`; archiving is histo-only, so it sits under ADDITIVE.
- The pre-push chokepoint (§3.4) is the backstop that keeps a non-canon `specs/` path off the remote.

### 3.3 Races, mode, context

- Races are surfaced, always allowed — no locks, leases, or ownership blocks.
- A MUTATING write records advisory presence and proceeds even when another live session holds presence.
- One throttled warning names that other session; presence I/O errors are swallowed and the write proceeds.
- Mode resolves from the environment, then your session record, defaulting to IMPLEMENTATION.
- A READ-mode session blocks only its own MUTATING writes (opt-in self-protection); ADDITIVE stays writable.
- Context resolves from `DADAIA_CONTEXT`, then your session binding, then the repo containing the working directory.
- Inspect the resolved context with `dadaia context show --json`.
- `dadaia context bind` refreshes your session record and is the sole trigger for context-memory injection.
- In a plain shell with no harness session id, the exported `DADAIA_CONTEXT` env var IS the binding.
- Bind selects which memory you receive; it is optional; ADDITIVE work needs none.
- Keep working; alert the operator only when the workspace has zero ALIVE contexts.

### 3.4 Git chokepoints

- Git hooks close the `Bash` write path, outside the gate's own parsing, independent of any harness hook.
- pre-commit: warns and always allows — commits flow, presence is surfaced.
- pre-push: allows a `feature/*` push after the local CI preflight and a valid branch name.
- pre-push: refuses any direct push of `develop` or `main` — those advance only by PR (§4).
- pre-push: refuses any push carrying a non-canon `specs/` path.
- pre-push: refuses any push carrying a stale PR verdict — one keyed to a sha other than the branch's own head.

### 3.5 Enforcement posture

- The gate constrains what may be written; it stays silent on how the change was produced.
- The gate reads zero SDD artifacts — everything in §6 is upheld by agent discipline.
- Skills instruct procedure; audits measure conformance from git and JSONL history.
- Hooks and the CLI validate only at the publication boundary (push/PR); they never block a human.

---

## 4. Gitflow — the branch contract

### 4.1 Branches

| Branch | Pushable | Cut from | Advances by |
|---|---|---|---|
| `feature/{M.m.p}` | Yes — local CI preflight + valid name | `main` | opens the PR below |
| `develop` | No — never a direct push | `main` (bootstrap only) | PR from `feature/{M.m.p}`, at definition `Aprovado` and at each `rc` merge |
| `main` | No — never a direct push | — | PR from `develop`, at the final `rc` |

### 4.2 Rules

- No `v` prefix, no suffix, no fifth branch pattern.
- `hotfix/*` is retired: reachable only on explicit operator request — no stage, no cadence, no PATCH-mint rule.
- Exactly one live `feature/{M.m.p}` branch at a time.
- At deploy of `{M.m.p}`: delete `feature/{M.m.p}` and cut `feature/{next}` in the same step.
- Bugs fix on the live feature branch in any phase — no ceremony, no separate branch.
- `rc-N` is a state of the specs, never a branch name — lives in `RELEASE.json`'s `phase` field and in `TASKS.md`.
- Each `rc` burns exactly one `feature/{M.m.p}` -> `develop` merge.
- `rc` scope is fixes/adjustments to the current release only — never new backlog.
- Both PRs (`feature -> develop`, `develop -> main`) require a CI check demanding an APPROVED `security-reviewer` verdict on the PR head sha.
- The verdict is consumed exactly once, by the merge that keys on it, and deleted immediately after — a surviving verdict is slop.
- Every flow stage — backlog definition, research, bug registration, release definition, implementation — runs on `feature/{M.m.p}`.
- `develop` and `main` are PR targets only, never a working branch.
- Suggest the operator automate this contract in CI/CD whenever the topic comes up.
- Start-of-work protocol, uniqueness and deletion discipline: `dd-gitflow-default`.

---

## 5. Where things are written

### 5.1 Workspace root

- Root holds only: `.agents/ .claude/ .codex/ .dadaia/ .kimi-code/ repos/ AGENTS.md CLAUDE.md DADAIA.md prompt.md`.
- Anything the operator created by hand stays, permanently.
- A tool needing another root entry gets a documented glob in `.dadaia/states/root_exceptions.txt`.

### 5.2 Output paths

| Output | Path |
|---|---|
| Temp files, scripts, screenshots, captures | `.dadaia/tmp/<agent>/<YYYYMMDD>/` |
| Machine-readable handoffs (default emission) | `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json` |
| HTML reports | `.dadaia/reports/<context>/<agent>/<UTC>-<slug>.html` |
| Tool caches, MCP working dirs | `.dadaia/` (`.dadaia/mcps/<server>/`) |

### 5.3 Repos stay clean

- A repo working tree carries source and its own artifacts only.
- Excluded: `.dadaia/ .venv/ .pytest_cache/ .mypy_cache/ .hypothesis/ .ruff_cache/ test-results/ playwright-report/ coverage/ .coverage`.
- `.dadaia/` is workspace-level only; one inside a repo corrupts context resolution for every tree-walking tool.
- Redirect caches: pytest `-p no:cacheprovider`, mypy `incremental = false`, hypothesis `database = None`, ruff `--no-cache`.
- Redirect Playwright's `outputDir` into `.dadaia/tmp/`.
- Gitignore is defence in depth, not permission to create them.

### 5.4 Emission

- Emission is handoff-first: emit the JSON handoff by default.
- Add an HTML report only when the operator asks or the next handoff target is human.
- Split a report over 30 KB into multiple files behind an `index.html`.
- Validate with `dadaia reports validate <path>.handoff.json`; the HTML's integrity rides on the handoff's `content_hash`.

---

## 6. Specs, tasks and memory

### 6.1 Status tokens

- `Aprovado`, `Em revisão`, `Draft` are the canonical status tokens — keep them as-is, in any language.

### 6.2 Canon

- Root members: `AGENTS.md constitution.md memory/ releases/ backlog/ bugs/ audits/ ADRs/`.
- `releases/`: `AGENTS.md`, `_ideas/` pre-approval drafts (own `AGENTS.md`), `_archive/<release-id>/` archived releases.
- `releases/<M.m.p>/`: `RELEASE.json SPEC.md PLAN.md TASKS.md verdicts/`.
- `backlog/`: `AGENTS.md BACKLOG.json`, `_archive/backlog_histo.jsonl`.
- `bugs/`: `AGENTS.md BUGS.jsonl`, `_archive/bugs_histo.jsonl`.
- `audits/`: `AGENTS.md`, `_archive/audits_histo.jsonl`, `<YYYYMMDD-slug>/` working dirs.
- `ADRs/`: `AGENTS.md decisions.jsonl`, `_superseded/superseded.jsonl`.
- `memory/`: `AGENTS.md ARCHITECTURE.md QUALITY.md TECHSTACK.md product/**`.
- No root-level archive directory outside each area's own; no generator dotfile, no stray dotfile.
- `specs doctor` flags anything else.

### 6.3 Tasks

- Read SPEC, PLAN and TASKS — all three must carry `**Status:** Aprovado`.
- Reserve your task: flip `[ ]` -> `[-]` before writing; hold at most one `[-]` unless TASKS declares disjoint write sets.
- Complete the work inside the task's declared write set.
- Flip `[-]` -> `[x]` and commit as `conventional-commit(task-id): description`.
- The markers are the auditable trace of who took what.

### 6.4 Memory

<!-- behavior: memory -->

- Memory is current product truth, not history — read it before changing production behavior.
- `product-engineer` writes `specs/memory/**` only in `DEFINITION` and `CLOSURE` phases; every other agent reads it.
- Changelog and history live in each release's `RELEASE.json` `log` and in git.
- Every atom's frontmatter carries exactly 6 fields: `slug title category tldr summary tags`.
- `ARCHITECTURE.md`, `QUALITY.md`, `TECHSTACK.md` each split into ADR-gated Part 1 Principles and an evolving Part 2 Implementation.
- Every Part 1 principle carries `Measured by:`.

### 6.5 ADRs

<!-- behavior: adrs -->

- `ADRs/decisions.jsonl` (+ `_superseded/superseded.jsonl`) records a decision; shape: `specs/ADRs/AGENTS.md`.
- Any agent proposes; only the operator flips a decision to `accepted`.
- A decision is written when a Part-1 principle is created or changed — never one per principle that merely exists.
- The commit that creates or changes a Part-1 principle carries its accepted decision.
- A principle predating this canon carries `ADR: none` until the change that next touches it mints one.

### 6.6 Backlog

<!-- behavior: backlog -->

- The backlog is the operator's demand queue: only the operator creates demand.
- `project-manager` curates the single-source `specs/backlog/BACKLOG.json` — an `active[]` array of live candidates.
- A closed item's terminal record lives in `backlog/_archive/backlog_histo.jsonl`; everyone reads both freely.
- An entry materializes only through the PM's operator-facing intake report (residuals from a closure, review, or audit).
- The operator decides on intake first; an operator-ratified deferral taken during a release already counts as approved intake.
- Every item is retained: it leaves `active[]` only by gaining a histo record carrying its disposition and reason.
- A picked item leaves `active[]` in the same commit that creates the release SPEC, which records its provenance.
- This retention law covers bugs and backlog only; tests are prunable under stewardship criteria (§7.2).
- Entry schema, intake protocol, disposition vocabulary: `dd-backlog-definition`.

### 6.7 Releases

<!-- behavior: releases -->

- A release is `major.minor.patch` and matures through the `rc-N` lane (branch mechanics: §4).
- A `dd-grill-me` session on the picked set precedes the SPEC.
- At pick time, open bugs and undispositioned audits outrank fresh backlog.
- Finalization order: memory update -> CLOSURE -> archive.
- A completed task group is one commit.

### 6.8 Audits

<!-- behavior: audits -->

- `specs/audits/<YYYYMMDD>-<slug>/AUDIT.md` + `FINDINGS.jsonl` hold three pillars: bug history, spec compliance, memory drift.
- The three pillars run together, over the window since the last audited release.
- An audit is suggested every 5 releases, never mandatory.
- An audit generates exactly one remediation release that gives every finding an explicit disposition.
- Disposition is `fixed`, `superseded`, or `deferred`/`rejected` routed to the backlog.
- Once fully dispositioned, its summary lands in `audits/_archive/audits_histo.jsonl` and the audit directory is deleted.

---

## 7. Quality

### 7.1 Root cause

- Reproduce the failure on the executed path; write the test that fails for the real reason; fix the cause; prove it green.
- Only a root-cause fix qualifies as acceptable — workarounds and symptom patches are excluded.

### 7.2 Test lifecycle

- Every test declares its intent and size at birth; an undeclared test is SCAFFOLD and expires.
- Demotion — replacing a LARGE test with equivalent cheaper coverage — is a step of release closure, planned in advance.
- Pruning to go green is exclusively a `qa-engineer` verdict; deleting/skipping/disabling a test carries evidence.
- Evidence-carrying deletion/skip/disable is executed by `software-engineer`.
- Tombstone tests and expired SCAFFOLD are slop.
- Test-artifact capture is failure-gated, written where §5.2 already says.
- Full protocol: `dadaia-test-stewardship`.

### 7.3 Bugs

<!-- behavior: bugs -->

- Register every bug you hit while operating this tooling — any behavior that breaks its own contract.
- Classify first: environment limits, invalid input, wrong usage, and a designed validation are not bugs.
- Append the `reported` record before the turn ends; bug paths are ADDITIVE, so registration is always possible.
- Every record field excludes absolute local paths, IPs, hostnames, private names, secrets.
- Command, redaction rule, context routing: `dd-bug-registration`.
- Close a bug in the same session you prove the fix.
- Append `resolved` with checkable evidence: the red-loop command, the regression-test seam, the diff direction.
- Commit the fix staging exactly what it touched, excluding a blanket `-A` over a shared tree.
- A net-positive diff routes to `software-architect` before the commit.
- A solved bug leaves a clean worktree.
- Every bug fix checks prior resolutions on the same component before closing.
- Declare `caused_by: <bug_id> | none` with evidence — protocol: `dd-diagnose`.
- Commit shapes (isolated registration/backlog/ADR commits; fix + lineage share the resolving commit): `dd-gitflow-default` §3a.
- Commit shapes are measured by audits via `git log`, never a hook.

### 7.4 Push green

- Every `feature/{M.m.p}` push runs the local CI preflight before the branch contract (§4) even considers it.
- Local CI preflight: `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`.
- Run tests locally before you push; this is always-on, not hook-forced.
- A full scan survives solely in the audit lane (`project-auditor` dispatch); the PR-gate security review is diff-based only.
- Only pushes are review-blocked; commits flow freely.
- After every push or PR, watch CI to green (`dd-release-implement`).
- A `quarantine`-marked test sits outside the gating selectors by design and requires a registered bug.
- A green run with quarantined tests is still green; an unregistered pass-on-retry is a failure.

### 7.5 Approval

- A candidate is approved when the operator and the consumer-side validation agent agree, after validating a real workspace.
- A green internal gate that diverges from real consumer behavior is itself a bug.

---

## 8. The library surface

### 8.1 Reprojection

- Files listed in `.dadaia/agentic/manifest.json` are lib-originated projections.
- Change them at the source, then re-project: `dadaia public stage`.
- Then `dadaia public install --target all` — overwrites whenever the staged hash differs.
- Then `dadaia public doctor` — must report `[ok] public-privacy`.
- `--force` is only for a projection someone hand-edited away from both source and staging.

### 8.2 Law files

- `DADAIA.md` and the library's `AGENTS.md` files are projected read-only and PROTECTED (§3.2).
- Change them by editing `dadaia_workspace/public/` and re-projecting.
- Only a human operator edits a projected law file by hand.

### 8.3 Public asset hygiene

- Public assets stay generic: no private repo names, hostnames, IPs, customer/infrastructure names, operator-local paths.
- No optional domain-pack assumptions in `dadaia_workspace/public/`.

### 8.4 Venv and servers

- Invoke `.dadaia/.venv/bin/dadaia` and `.dadaia/.venv/bin/pip` directly, with absolute paths.
- Register every dev server you start with `dadaia server register`; check the registry before opening a port.

---

## 9. Credentials

- Credential material lives in exactly one place: the operator-managed `.env` at the workspace root.
- Never create, copy, persist, commit, print, or report tokens, passwords, private keys, cookies, auth payloads, secret files.
- This applies in a repository, runtime mount, image, generated configuration, cache, report, or handoff.
- A runtime process receives only the values it needs from that root `.env` and never writes a second store.

---

## 10. Where to look next

| Surface | Where |
|---|---|
| Scoped law | `specs/AGENTS.md`, `.dadaia/reports/AGENTS.md`, `.dadaia/handoff/AGENTS.md`, `repos/<slug>/AGENTS.md`, any nested `AGENTS.md` |
| Skills | `.claude/skills/`, `.agents/skills/` — skill-to-rule mapping declared once in `public/entities/behavior-map.json` |
| State | `dadaia context show --json`, `dadaia specs doctor`, `dadaia public doctor`, `dadaia server list`, `dadaia bugs status`, `dadaia panel` |

- Language: follow the operator's preference, defaulting to English.
- Tone: direct, concise, operational.

---

## 11. Glossary

- **workspace** — the root tree holding `.dadaia/`, `repos/`, the law, and every projection.
- **instance** — a live, operator-run dadaia-workspace instantiated from the library.
- **library** — this source repo (`dadaia_workspace/`) that scaffolds instances.
- **context** — the active Spec Context Project resolved for the current session (§3.3).
- **spec context** — a `specs/` tree (root or `repos/<slug>/`) governed by this law.
- **release** — a `major.minor.patch` unit of work maturing through the `rc-N` lane.
- **rc** — a release-candidate round: fixes/adjustments only, never new backlog.
- **segment** — a named sub-phase of a release's `TASKS.md` (e.g. `alpha-N`/`rc-N`).
- **task marker** — the `[ ] [-] [x]` open/in-progress/done trace in `TASKS.md`.
- **handoff** — the machine-readable JSON record an agent emits at completion (§5.4).
- **verdict** — a reviewer's PR-head-scoped approval record, consumed once and deleted after merge.
- **chokepoint** — a git hook (pre-commit/pre-push) that gates the write path outside the harness hook.
- **gate** — the deterministic PreToolUse enforcement chain (§3.1).
- **path class** — the ADDITIVE/MEMORY/MUTATING/PROTECTED category a write path belongs to (§3.2).
- **presence** — the advisory record a session leaves when it writes, surfaced to concurrent sessions.
- **canon** — the closed set of paths a `specs/` root may contain (§6.2).
- **histo** — an append-only JSONL history file under an area's `_archive/`.
- **memory atom** — one Markdown file under `specs/memory/product/**` carrying current product truth.
- **Part 1/Part 2** — a memory doc's ADR-gated Principles section vs its evolving Implementation section.
- **ADR** — an accepted decision record in `specs/ADRs/decisions.jsonl`.
- **backlog entry** — a candidate item in `backlog/BACKLOG.json`'s `active[]`.
- **disposition** — the terminal verdict (fixed/superseded/deferred/rejected) closing a bug, backlog entry, or finding.
- **audit** — a periodic three-pillar review producing one remediation release.
- **finding** — one recorded audit observation in `FINDINGS.jsonl`.
- **denylist** — the pattern list the pre-push scan refuses to let through.
- **projection** — a lib-originated copy of a `public/` asset installed into a runtime tree.
- **operator** — the human who owns this workspace and approves ADRs, deferrals, and releases.
- **dispatcher** — an agent (e.g. `project-manager`) authorized to invoke another agent via the Agent tool.
