# DADAIA.md — the workspace system prompt

- Complete always-on law: one file, every rule, one source.
- Source: `dadaia_workspace/public/data/DADAIA.md`; projects to workspace root, `.codex/`, `.kimi-code/`.
- Claude Code reaches it via `CLAUDE.md -> AGENTS.md -> DADAIA.md` — no second copy.
- Each fact stated once; sections cross-reference by number.
- A scoped `AGENTS.md` governs its own subtree, takes precedence there.
- Two rule-file kinds ship: this file, and scoped `AGENTS.md` — anything else is the operator's own.

---

## 1. The flow — the mandatory default

### 1.1 The two arms

- Classify every demand: Arm A (feature) or Arm B (bug); state the arm before acting.
- Deviation needs an explicit, confirmed operator request; default to the flow.
- Arm A: `demand -> backlog-definition -> release-definition -> implementation+reviews -> audit`.
- Arm B: `register -> reproduce -> RED test -> root-cause fix -> GREEN -> resolved -> commit`.
- Test: does the tool break its own contract? Yes -> Arm B, fixed now. No -> Arm A, via a release.
- A feature enters only through the backlog; a bug is fixed immediately, outside release material.

### 1.2 Dispatch

- Each Arm-A stage runs by dispatching its owning agent (§2) against the SDD documents (§6).
- No workflow engine — the SDD documents are the record of progress.

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
- Every agent invokes `dd-ai-eng-knowhow` for harness literacy; only `ai-engineer` reads its depth siblings — others dispatch it.

---

## 3. What is enforced deterministically

### 3.1 The gate

- One PreToolUse entrypoint (`pre_gate`), fixed order, first block wins: root whitelist -> venv guard -> SDD gate.
- Root whitelist blocks a new top-level workspace-root entry (§5.1).
- Venv guard (`Bash` only) blocks `dadaia`/`pip`/`python -m dadaia_workspace` run outside `.dadaia/.venv/bin/`; message carries the fix.
- SDD gate: path class × presence × phase × mode — context-relative, root and every `repos/<slug>/` alike.

### 3.2 Path classes

| Class | Paths | Verdict |
|---|---|---|
| ADDITIVE | `specs/bugs\|backlog\|audits/`, each area's `_archive/*_histo.jsonl`, `.dadaia/reports\|handoff\|tmp/` | Always writable |
| MEMORY | `specs/memory/` | Writable in `DEFINITION` and `CLOSURE` phase |
| MUTATING | everything else in-repo | Writable; records advisory presence |
| PROTECTED | `.dadaia/sessions/`, projected law files (§8.2) | Blocked |

- ADDITIVE's record contract (immutable core, write-once, mutable governance) is audited, not gated.
- No FROZEN class: no root `_archive/` under `specs/`; archiving is histo-only under ADDITIVE, backstopped by pre-push (§3.4).

### 3.3 Races, mode, context

- Races surface, never block — no locks, leases, ownership blocks.
- A MUTATING write records advisory presence and proceeds; one throttled warning names a colliding session.
- Presence I/O errors are swallowed; the write proceeds.
- Mode: env -> session record -> IMPLEMENTATION default; READ blocks only your own MUTATING writes.
- Context: `DADAIA_CONTEXT` -> session binding -> repo of the cwd; inspect via `dadaia context show --json`.
- `dadaia context bind` refreshes the session; it is the sole context-memory-injection trigger.
- A plain shell's exported `DADAIA_CONTEXT` env var IS the binding.
- Bind is optional; ADDITIVE needs none; alert the operator only at zero ALIVE contexts.

### 3.4 Git chokepoints

- Git hooks gate the `Bash` write path, outside the gate's own parsing, independent of any harness hook.
- pre-commit: warns and always allows.
- pre-push: allows `feature/*` after CI preflight + valid name.
- pre-push: refuses a direct `develop`/`main` push (§4), a non-canon `specs/` path, or a stale PR verdict.

### 3.5 Enforcement posture

- The gate constrains what is written, not how — it reads zero SDD artifacts; §6 is upheld by agent discipline, not the gate.
- Skills instruct procedure; audits measure conformance from git and JSONL history.
- Hooks and the CLI validate only at the publication boundary (push/PR); never a human.

---

## 4. Gitflow — the branch contract

### 4.1 Branches

| Branch | Pushable | Cut from | Advances by |
|---|---|---|---|
| `feature/{M.m.p}` | Yes — local CI preflight + valid name | `main` | opens the PR below |
| `develop` | No — never a direct push | `main` (bootstrap only) | PR from `feature/{M.m.p}`, at definition `Aprovado` and at each `rc` merge |
| `main` | No — never a direct push | — | PR from `develop`, at the final `rc` |

### 4.2 Rules

- No `v` prefix, no suffix, no fifth pattern; `hotfix/*` retired (operator-request only, no cadence).
- Exactly one live `feature/{M.m.p}`; at deploy, delete it and cut `feature/{next}` in the same step; bugs fix on it in any phase, no ceremony.
- `rc-N` is a specs state (`RELEASE.json`'s `phase` field + `TASKS.md`), never a branch name.
- Each `rc` burns one `feature -> develop` merge; scope is fixes only, never new backlog.
- Both PRs require an APPROVED `security-reviewer` verdict on the PR head sha, consumed once by the merge and deleted after — a survivor is slop.
- Every flow stage runs on `feature/{M.m.p}`; `develop`/`main` are PR targets only, never a working branch.
- Suggest CI/CD automation of this contract to the operator; mechanics: `dd-gitflow-default`.

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

- A repo working tree carries source and its own artifacts only — never `.dadaia/`.
- A nested `.dadaia/` corrupts context resolution for every tree-walking tool.
- Excluded: `.venv/ .pytest_cache/ .mypy_cache/ .hypothesis/ .ruff_cache/ test-results/ playwright-report/ coverage/ .coverage`.
- Redirect caches: pytest `-p no:cacheprovider`, mypy `incremental = false`, hypothesis `database = None`, ruff `--no-cache`.
- Redirect Playwright's `outputDir` into `.dadaia/tmp/`.
- Gitignore is defence in depth, not permission to create them.

### 5.4 Emission

- Handoff-first: JSON handoff by default; HTML report only on operator request or when the next hop is human.
- Split a report over 30 KB into multiple files behind an `index.html`.
- Validate with `dadaia reports validate <path>.handoff.json`; HTML integrity rides on `content_hash`.

---

## 6. Specs, tasks and memory

### 6.1 Status tokens

- `Aprovado`, `Em revisão`, `Draft` are the canonical status tokens — keep as-is, any language.

### 6.2 Canon

| Area | Members |
|---|---|
| root | `AGENTS.md constitution.md memory/ releases/ backlog/ bugs/ audits/ ADRs/` |
| `releases/` | `AGENTS.md`, `_ideas/` (own `AGENTS.md`), `_archive/<release-id>/` |
| `releases/<M.m.p>/` | `RELEASE.json SPEC.md PLAN.md TASKS.md verdicts/` |
| `backlog/` | `AGENTS.md BACKLOG.json`, `_archive/backlog_histo.jsonl` |
| `bugs/` | `AGENTS.md BUGS.jsonl`, `_archive/bugs_histo.jsonl` |
| `audits/` | `AGENTS.md`, `_archive/audits_histo.jsonl`, `<YYYYMMDD-slug>/` |
| `ADRs/` | `AGENTS.md decisions.jsonl`, `_superseded/superseded.jsonl` |
| `memory/` | `AGENTS.md ARCHITECTURE.md QUALITY.md TECHSTACK.md product/**` |

- No stray root archive directory or dotfile; `specs doctor` flags anything else.

### 6.3 Tasks

- Read SPEC, PLAN and TASKS — all three must carry `**Status:** Aprovado`.
- Reserve: flip `[ ] -> [-]` before writing; one `[-]` at a time unless TASKS declares disjoint write sets.
- Complete the work inside the task's declared write set.
- Flip `[-] -> [x]` and commit as `conventional-commit(task-id): description` — the auditable trace.

### 6.4 Memory

<!-- behavior: memory -->

- Current product truth, not history — read it before changing production behavior.
- `product-engineer` writes `specs/memory/**` only in `DEFINITION`/`CLOSURE` phases; every other agent reads it.
- Changelog and history live in each release's `RELEASE.json` `log` and in git.
- Atom frontmatter carries exactly 6 fields: `slug title category tldr summary tags`.
- `ARCHITECTURE.md QUALITY.md TECHSTACK.md` split into ADR-gated Part 1 Principles (each `Measured by:`) and Part 2 Implementation.

### 6.5 ADRs

<!-- behavior: adrs -->

- `ADRs/decisions.jsonl` (+ `_superseded/superseded.jsonl`) records a decision; shape: `specs/ADRs/AGENTS.md`.
- Any agent proposes; only the operator flips a decision to `accepted`.
- One decision per Part-1 principle created or changed — never one per principle that merely exists.
- The commit touching a Part-1 principle carries its accepted decision; a pre-canon principle carries `ADR: none` until next touched.

### 6.6 Backlog

<!-- behavior: backlog -->

- The operator's demand queue: only the operator creates demand; `project-manager` curates `specs/backlog/BACKLOG.json`'s `active[]`.
- A closed item's terminal record lives in `backlog/_archive/backlog_histo.jsonl`; everyone reads both freely.
- An entry materializes only via the PM's operator-facing intake report; an operator-ratified in-release deferral already counts as intake.
- Every item is retained: leaves `active[]` only via a histo disposition record.
- A picked item leaves `active[]` in the same commit that creates the release SPEC.
- Covers bugs and backlog only — tests are prunable under stewardship criteria (§7.2). Protocol: `dd-backlog-definition`.

### 6.7 Releases

<!-- behavior: releases -->

- A release is `major.minor.patch`, matures through the `rc-N` lane (branch mechanics: §4).
- A `dd-grill-me` session on the picked set precedes the SPEC.
- At pick time, open bugs and undispositioned audits outrank fresh backlog.
- Finalization order: memory update -> CLOSURE -> archive; a completed task group is one commit.

### 6.8 Audits

<!-- behavior: audits -->

- `specs/audits/<YYYYMMDD>-<slug>/AUDIT.md` + `FINDINGS.jsonl` hold three pillars: bug history, spec compliance, memory drift.
- The three pillars run together, over the window since the last audited release.
- Suggested every 5 releases, never mandatory.
- Generates exactly one remediation release; every finding gets a disposition: `fixed`, `superseded`, or `deferred`/`rejected` to backlog.
- Fully dispositioned: summary lands in `audits/_archive/audits_histo.jsonl`, the audit directory is deleted.

---

## 7. Quality

### 7.1 Root cause

- Reproduce the failure on the executed path; write the test that fails for the real reason; fix the cause; prove it green.
- Only a root-cause fix qualifies as acceptable — workarounds and symptom patches are excluded.

### 7.2 Test lifecycle

- Every test declares its intent and size at birth; an undeclared test is SCAFFOLD and expires.
- Demotion (LARGE test -> equivalent cheaper coverage) is planned release-closure work.
- Pruning to go green is exclusively a `qa-engineer` verdict; deletion/skip/disable carries evidence, executed by `software-engineer`.
- Tombstones and expired SCAFFOLD are slop; artifact capture is failure-gated (§5.2). Protocol: `dadaia-test-stewardship`.

### 7.3 Bugs

<!-- behavior: bugs -->

- Register every bug you hit while operating this tooling — any behavior that breaks its own contract.
- Classify first: environment limits, invalid input, wrong usage, and a designed validation are not bugs.
- Append `reported` before the turn ends; bug paths are ADDITIVE, so registration is always possible.
- Redact local paths, IPs, hostnames, private names, secrets from every field. Protocol: `dd-bug-registration`.
- Close in the same session as the fix: append `resolved` with the red-loop command, the regression-test seam, the diff direction.
- Commit exactly what the fix touched, never a blanket `-A`; a net-positive diff routes to `software-architect` first.
- Check prior resolutions on the same component first; declare `caused_by: <bug_id>|none` — protocol: `dd-diagnose`.
- Commit shapes: `dd-gitflow-default` §3a — measured by audits via `git log`, never a hook.

### 7.4 Push green

- Every `feature/{M.m.p}` push runs the local CI preflight first — always-on, not hook-forced.
- Preflight: `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`.
- A full scan lives only in the audit lane; the PR-gate review is diff-based; only pushes are review-blocked, commits flow freely.
- Watch every push/PR to green (`dd-release-implement`).
- A `quarantine`-marked test sits outside the gating selectors, bug-gated; unregistered pass-on-retry is a failure.

### 7.5 Approval

- Approved when the operator and the consumer-side validation agent agree, after validating a real workspace.
- A green internal gate that diverges from real consumer behavior is itself a bug.

---

## 8. The library surface

### 8.1 Reprojection

- Files listed in `.dadaia/agentic/manifest.json` are lib-originated projections — change them at the source.
- Re-project: `dadaia public stage` -> `dadaia public install --target all` (overwrites on hash diff).
- Then `dadaia public doctor` — must report `[ok] public-privacy`.
- `--force` is only for a projection hand-edited away from both source and staging.

### 8.2 Law files

- `DADAIA.md` and library `AGENTS.md` files are projected read-only and PROTECTED (§3.2).
- Change them by editing `dadaia_workspace/public/` and re-projecting; only a human hand-edits a projected copy.

### 8.3 Public asset hygiene

- No private repo names, hostnames, IPs, customer/infrastructure names, or operator-local paths in `public/`.
- No optional domain-pack assumptions in `dadaia_workspace/public/` either.

### 8.4 Venv and servers

- Invoke `.dadaia/.venv/bin/dadaia` and `.dadaia/.venv/bin/pip` directly, with absolute paths.
- Register every dev server you start with `dadaia server register`; check the registry before opening a port.

---

## 9. Credentials

- Credential material lives in exactly one place: the operator-managed `.env` at the workspace root.
- Never create, copy, persist, commit, print, or report tokens, passwords, keys, cookies, auth payloads, secrets.
- Applies everywhere: repo, runtime mount, image, generated config, cache, report, handoff.
- A runtime process receives only the values it needs from that root `.env` and never writes a second store.

---

## 10. Where to look next

### 10.1 Reference

| Surface | Where |
|---|---|
| Scoped law | `specs/AGENTS.md`, `.dadaia/reports/AGENTS.md`, `.dadaia/handoff/AGENTS.md`, `repos/<slug>/AGENTS.md`, any nested `AGENTS.md` |
| Skills | `.claude/skills/`, `.agents/skills/` — skill-to-rule mapping declared once in `public/entities/behavior-map.json` |
| State | `dadaia context show --json`, `dadaia specs doctor`, `dadaia public doctor`, `dadaia server list`, `dadaia bugs status`, `dadaia panel` |

- Language: operator preference, default English. Tone: direct, concise, operational.

### 10.2 Glossary

- **workspace** — root tree holding `.dadaia/`, `repos/`, the law, every projection.
- **instance** — a live, operator-run dadaia-workspace instantiated from the library.
- **library** — this source repo, `dadaia_workspace/`, that scaffolds instances.
- **context** — the active Spec Context Project resolved for this session (§3.3).
- **spec context** — a `specs/` tree (root or `repos/<slug>/`) governed by this law.
- **release** — a `major.minor.patch` unit maturing through the `rc-N` lane.
- **rc** — a release-candidate round: fixes/adjustments only, never new backlog.
- **segment** — a named sub-phase of a release's `TASKS.md` (e.g. `alpha-N`/`rc-N`).
- **task marker** — the `[ ] [-] [x]` open/in-progress/done trace in `TASKS.md`.
- **handoff** — the machine-readable JSON completion record an agent emits (§5.4).
- **verdict** — a PR-head-scoped approval record, consumed once, deleted after merge.
- **chokepoint** — a git hook that gates the write path outside the harness hook.
- **gate** — the deterministic PreToolUse enforcement chain (§3.1).
- **path class** — the ADDITIVE/MEMORY/MUTATING/PROTECTED category a write path belongs to (§3.2).
- **presence** — the advisory record a session leaves when it writes, surfaced to others.
- **canon** — the closed set of paths a `specs/` root may contain (§6.2).
- **histo** — an append-only JSONL history file under an area's `_archive/`.
- **memory atom** — one Markdown file under `specs/memory/product/**` carrying current truth.
- **Part 1/Part 2** — a memory doc's ADR-gated Principles section vs its Implementation section.
- **ADR** — an accepted decision record in `ADRs/decisions.jsonl`.
- **backlog entry** — a candidate item in `backlog/BACKLOG.json`'s `active[]`.
- **disposition** — the terminal verdict closing a bug, backlog entry, or audit finding.
- **audit** — a periodic three-pillar review producing one remediation release.
- **finding** — one recorded audit observation in `FINDINGS.jsonl`.
- **denylist** — the pattern list the pre-push scan refuses to let through.
- **projection** — a lib-originated copy of a `public/` asset installed into a runtime tree.
- **operator** — the human who owns the workspace and approves ADRs, deferrals, releases.
- **dispatcher** — an agent authorized to invoke another agent via subagent dispatch.
