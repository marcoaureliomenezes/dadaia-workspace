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
- Arm B: `propose -> operator confirms -> register -> RED test -> root-cause fix -> GREEN -> resolved`.
- Test: does the tool break its own contract? Yes -> Arm B, fixed now. No -> Arm A, via a release.
- A feature enters only through the backlog; a confirmed bug is fixed immediately, outside release material.

### 1.2 Dispatch

- Each Arm-A stage runs by dispatching its owning agent (§2) against the SDD documents (§6).
- No workflow engine — the SDD documents are the record of progress.

---

## 2. Who does what

### 2.1 Ownership

| The work | Owner |
|---|---|
| Intake, grill-me, dispatch; backlog curation; SPEC; the memory pass at closure | `project-manager` |
| PLAN and TASKS as technical planning; production code and its tests, in any language | `software-engineer` |
| The three-axis review (`dd-code-review`) and its six lenses — architecture, security, QA, product, audit, AI surface — before a PR and at candidate close | `code-reviewer` |

### 2.2 Cross-cutting

- Three roles, no fourth: every retired role (architect, product, QA, security, audit, AI surface) is a lens the reviewer applies and the engineer anticipates.
- Every agent invokes `dd-ai-eng-knowhow` for harness literacy; an AI-entity change follows its AUTHORING contract and passes the AI-surface lens.

---

## 3. What is enforced deterministically

### 3.1 The gate

- One PreToolUse entrypoint (`pre_gate`), fixed order, first block wins: root whitelist -> venv guard -> SDD gate.
- The gate blocks exactly three things; there is no fourth.
- Root whitelist blocks a new top-level workspace-root entry (§5.1) — block one.
- Venv guard (`Bash` only) blocks `dadaia`/`pip`/`python -m dadaia_workspace` run outside `.dadaia/.venv/bin/` — block two, its only rule.
- SDD gate blocks a PROTECTED write, and a bound session's MUTATING write under a `repos/<slug>/` outside its scope (§3.3) — block three.
- Every BLOCK, from every enforcement point, carries exactly one `fix: <command>` line naming one executable command.
- A BLOCK whose own fix is itself blocked is a Stall: CRITICAL, and unrepresentable by contract test.

### 3.2 Path classes

| Class | Paths | Verdict |
|---|---|---|
| ADDITIVE | `specs/bugs\|backlog\|audits/`, each area's `_archive/*_histo.jsonl`, `.dadaia/{handoff,tmp,reaped,mcps,.cache}/` | Always writable |
| MUTATING | everything else in-repo | Writable, scope-judged under `repos/<slug>/` |
| PROTECTED | `.dadaia/sessions/`, projected law files (§8.2) | Blocked |

- Three classes, no fourth: a workspace-root path matching no ADDITIVE or PROTECTED prefix is MUTATING.
- `specs/memory/` is MUTATING, writable in every phase; memory discipline (§6.4, §6.7) is procedure, audited, never gated.
- ADDITIVE's record contract (immutable core, write-once, mutable governance) is audited, not gated.
- No FROZEN class: no root `_archive/` under `specs/`; archiving is histo-only under ADDITIVE, backstopped by pre-push (§3.4).

### 3.3 Races, context, scope

- Races surface, never block — no locks, leases, ownership blocks.
- Context: `DADAIA_CONTEXT` -> session binding -> repo of the cwd; inspect via `dadaia context show --json`.
- `dadaia context bind <ctx> [--print-env]` is one verb: no mode, no release, no session state beyond the context — it refreshes the session and is the sole context-memory-injection trigger.
- A plain shell's exported `DADAIA_CONTEXT` env var IS the binding.
- Scope = the bound context's main repo plus its associated repos; only `repos/<slug>/` is scope-judged.
- Out-of-scope write: BLOCKed with `fix: dadaia context bind <owner>`; an unbound session, an unregistered slug and a workspace-root path are never scope-blocked.
- Bind is optional; ADDITIVE needs none; alert the operator only at zero ALIVE contexts.
- One harness session per checked-out tree (ADR 0002); a parallel session's worktree is created before launch; staging discipline: §7.3.

### 3.4 Git chokepoints

- The pre-push git hook gates the `Bash` write path, outside the gate's own parsing, independent of any harness hook.
- pre-push: allows `feature/*` after CI preflight + valid name.
- pre-push: refuses a direct `develop`/`main` push (§4) or a non-canon `specs/` path the pushed range introduces or rewrites.
- pre-push scans the pushed range only: published history is the baseline and is never rescanned (ADR 0013).
- pre-push applies the v6 canon only to a `specs/` tree stamped at the canonical pattern; a lower stamp is doctor drift, never a push block.

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
- Exactly one live `feature/{M.m.p}`, named for the live release; at deploy, delete it and cut `feature/{next}` in the same step; bugs fix on it in any phase, no ceremony.
- The release version = last published PyPI + 1 patch, minted at birth; it increments ONLY at operator-approved deploy (ADR 0005).
- `rc-N/` is an archived candidate folder under the live release (`dadaia release rc-archive`), never a branch name and never a scaffolded sub-phase.
- `releases/_archive/<M.m.p>/` holds PUBLISHED versions only: a candidate closed between two publications is an `rc-N/` of the version that published it, never its own archived release; `dadaia release fold <id> --into <published>` is the one repair (ADR 0014).
- Each candidate closure burns one `feature -> develop` merge; after it the agent asks the operator: promote (deploy) or continue (archive the trio to `rc-N/`, stack more backlog/bugs/findings).
- Both PRs need the `security-review` required check green on the PR head (the official `anthropics/claude-code-security-review` Action; secret and ruleset are the operator's).
- Every flow stage runs on `feature/{M.m.p}`; `develop`/`main` are PR targets only, never a working branch.
- Suggest CI/CD automation of this contract to the operator; mechanics: `dd-gitflow-default`.

---

## 5. Where things are written

### 5.1 Workspace root

- Root holds only: `<!-- root -->`.
- Anything the operator created by hand stays, permanently.
- A tool needing another root or harness-dir entry gets a documented glob in `.dadaia/states/instance_exceptions.txt`.

### 5.2 Output paths

| Output | Path |
|---|---|
| Temp files, scripts, screenshots, captures | `.dadaia/tmp/<agent>/<YYYYMMDD>/` |
| Machine-readable handoffs (default emission) | `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json` |
| HTML reports | `repos/<slug>/reports/<agent>/<UTC>-<slug>.html` |
| Tool caches, MCP working dirs | `.dadaia/.cache/`, `.dadaia/mcps/<server>/` |

### 5.3 Repos stay clean

- A repo working tree carries source and its own artifacts only — never `.dadaia/`.
- A nested `.dadaia/` corrupts context resolution for every tree-walking tool.
- Excluded: `<!-- repo-excluded -->`.
- Caches redirect by configuration, never by a remembered command flag: `[tool.pytest.ini_options] addopts`, `[tool.ruff] cache-dir`, `[tool.mypy] cache_dir`, hypothesis `database = None`.
- A bare `pytest`/`ruff check`/`mypy --strict` from the repo root leaves the tree clean; the excluded set is rendered from the one registry (§8.5).
- Redirect Playwright's `outputDir` into `.dadaia/tmp/`.
- Gitignore is defence in depth, not permission to create them.

### 5.4 Emission

- Handoff-first: JSON handoff by default; HTML report only on operator request or when the next hop is human.
- Split a report over 30 KB into multiple files behind an `index.html`.
- A report lives in its repo and is never TTL-reaped; a handoff, scratch file, MCP dir or cache expires one day after its mtime (§8.5).
- Validate with `dadaia reports validate <path>.handoff.json`; HTML integrity rides on `content_hash`.

---

## 6. Specs, tasks and memory

### 6.1 Status tokens

- `Aprovado`, `Em revisão`, `Draft` are the canonical status tokens — keep as-is, any language.

### 6.2 Canon

<!-- specs-canon -->

- No stray root archive directory or dotfile; `dadaia doctor` flags anything else.

### 6.3 Tasks

- Read SPEC, PLAN and TASKS — all three must carry `**Status:** Aprovado`.
- Reserve: flip `[ ] -> [-]` before writing; one `[-]` at a time unless TASKS declares disjoint write sets.
- Complete the work inside the task's declared write set.
- Flip `[-] -> [x]` and commit as `conventional-commit(task-id): description` — the auditable trace.

### 6.4 Memory

<!-- behavior: memory -->

- Current product truth, not history — read it before changing production behavior.
- `project-manager` writes `specs/memory/**` only in `DEFINITION`/`CLOSURE` phases; every other agent reads it.
- Changelog and history live in each release's `_RELEASE.json` `log` and in git.
- Atom frontmatter carries exactly 5 fields: `slug title tldr summary tags`.
- `ARCHITECTURE.md QUALITY.md TECHSTACK.md` split into ADR-gated Part 1 Principles (each `Measured by:`) and Part 2 Implementation.

### 6.5 ADRs

<!-- behavior: adrs -->

- `ADRs/decisions.jsonl` records every decision, superseded in place; shape: `specs/ADRs/AGENTS.md`.
- Any agent proposes; only the operator flips a decision to `accepted`.
- One decision per change set, naming every Part-1 principle it creates or changes — never one per principle that merely exists.
- A record born from an operator grill ruling is `accepted` at append, the ruling date in `context`.
- The commit touching a Part-1 principle carries its accepted decision; a pre-canon principle carries `ADR: none` until next touched.

### 6.6 Backlog

<!-- behavior: backlog -->

- The operator's demand queue: only the operator creates demand; `project-manager` curates `specs/backlog/BACKLOG.json`'s `active[]`.
- A closed item's terminal record lives in `backlog/_archive/backlog_histo.jsonl`; everyone reads both freely.
- An entry materializes only via the PM's operator-facing intake report; an operator-ratified in-release deferral already counts as intake.
- Every item is retained: it leaves `active[]` only by `dadaia backlog exit <slug> --disposition …`, once, at closure.
- Covers bugs and backlog only — tests are prunable under stewardship criteria (§7.2). Protocol: `dd-backlog-definition`.

### 6.7 Releases

<!-- behavior: releases -->

- A release is `major.minor.patch` with OPEN scope, born by `dadaia release new <id>` (SPEC.md + `_RELEASE.json`, DEFINITION, one transaction).
- It grows by stacked closed-scope candidates; exactly one live release ever, a second is refused (ADR 0005).
- A candidate is one full SDD cycle: grill -> SPEC/PLAN/TASKS `Aprovado` at the release root -> implementation -> memory -> CLOSURE -> `feature -> develop` merge.
- `phase` and the `defined`/`implemented` milestones move only by `dadaia release phase IMPLEMENTATION|CLOSURE --sha <sha>`; `shipped` only by `release archive`.
- A `dd-grill-me` session on the picked set precedes each candidate's SPEC.
- After each merge, the promote-or-continue gate (§4.2): continue = `dadaia release rc-archive` moves the trio to `rc-N/` and a fresh trio is born at root; promote = the ship lane, then `dadaia release archive <id> --shipped --pr --next` (final trio stays at root, ADR 0009).
- Candidate finalization order: memory update -> CLOSURE -> gate; a completed task group is one commit.
- A candidate's SPEC.md fits 24 KB and TASKS.md 12 KB — measured by V34 (`tests/contract/test_slop_ratchets.py`).

### 6.8 Audits

<!-- behavior: audits -->

- `specs/audits/<YYYYMMDD>-<slug>/AUDIT.md` + `FINDINGS.jsonl` hold three pillars: bug history, spec compliance, memory drift.
- The three pillars run together, over the window read from `audits/_archive/audits_histo.jsonl`.
- Suggested every 5 releases, never mandatory.
- Generates exactly one remediation release; every finding moves by `dadaia audit disposition <dir> <finding> --disposition resolved|superseded|deferred|rejected`.
- With none `open`, `dadaia audit close <dir> --sha <window-end>` appends the `audits_histo.jsonl` summary and deletes the directory.

---

## 7. Quality

### 7.1 Root cause

- Reproduce the failure on the executed path; write the test that fails for the real reason; fix the cause; prove it green.
- Only a root-cause fix qualifies as acceptable — workarounds and symptom patches are excluded.

### 7.2 Test lifecycle

- Every test declares its intent and size at birth; an undeclared test is SCAFFOLD and expires.
- Demotion (LARGE test -> equivalent cheaper coverage) is planned release-closure work.
- Pruning to go green is exclusively a `code-reviewer` verdict (QA lens); deletion/skip/disable carries evidence, executed by `software-engineer`.
- Tombstones and expired SCAFFOLD die at closure (§7.6); artifact capture is failure-gated (§5.2). Protocol: `dd-test-stewardship`.

### 7.3 Bugs

<!-- behavior: bugs -->

- A bug is a reproducible violation of a contract the tool documents — `--help`, this law, a schema.
- Not a bug: your own mistake, wrong usage, an environment limit, a designed validation, a law ambiguity, a missing feature.
- The agent proposes, the operator confirms: name the contract line violated, one reproducing command, why it is not agent error.
- `dadaia bugs append` runs only after that confirmation; with no operator, the proposal is a handoff finding whose `message` starts `bug-proposal:` — never a record.
- Redact local paths, IPs, hostnames, private names, secrets from every field. Protocol: `dd-bug-registration`.
- Close in the same session as the fix: `dadaia bugs resolve` with the red-loop command, the regression-test seam, the diff direction.
- Commit exactly what the fix touched, never a blanket `-A`; a net-positive diff passes the architecture lens first.
- Check prior resolutions on the same component first; declare `caused_by: <bug_id>|none` — protocol: `dd-bug-resolution`.
- Commit shapes: `dd-gitflow-default` §3a — measured by audits via `git log`, never a hook.

### 7.4 Push green

- Every `feature/{M.m.p}` push runs the local CI preflight first — always-on, not hook-forced.
- Preflight: `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`.
- A full scan lives only in the audit lane; the PR-gate review is diff-based; only pushes are review-blocked, commits flow freely.
- The push IS the publication boundary: pre-push runs the denylist scan over every object the pushed range introduces or rewrites.
- Published history is the baseline and is never rescanned; the only amnesty is a term the baseline already publishes under the same matcher (ADR 0013).
- No path is exempt and no tolerated-pairs list exists; a fixture needing a secret shape composes it at runtime, never as a tracked literal.
- Watch every push/PR to green (`dd-release-implementation`).
- A `quarantine`-marked test sits outside the gating selectors, bug-gated; unregistered pass-on-retry is a failure.

### 7.5 Approval

- Approved when the operator and the consumer-side validation agent agree, after validating a real workspace.
- A green internal gate that diverges from real consumer behavior is itself a bug.

### 7.6 Slop

- Slop is what passes the deletion test without loss: removed, no behavior changes and no decision loses its record.
- The test applies to a file, line, comment, test, spec sentence, acronym, branch, release, rule or handoff.
- Slop dies in the change that finds it; it is never commented out, marked, archived or deferred.
- The writer proves the artifact fails the deletion test; the reviewer applies the test; the auditor measures the balance.
- A rule lives in one home; the second copy is deleted; a consumed handoff is deleted in the same turn.
- Artifact rules live by class: constitution `Slop`, memory `ARCHITECTURE`/`QUALITY` fixed sections; `dadaia doctor` keeps them byte-exact.
- Detection and ratchets: `dd-code-review` SLOP.md; measured by `tests/contract/test_slop_ratchets.py` and audit pillar 2.

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
- Register every dev server you start through `dd-cli-library` (`scripts/registry.py register`); check the registry before opening a port.

### 8.5 Instance compliance

- `dadaia doctor` is the one scan and reaper — sections `workspace`, `specs`, `ledgers`; `--fix`, `--specs-dir`, `--context`, `--public-dir`, `--json`; exit 1 on any error-class finding.
- One finding per line, `<CODE> <verdict> <message>`; codes `WS-<zone>-<verdict>`, `SPEC-DOC-*`, `TREE-*`, `RELEASE-TREE-*`, `BL-SCHEMA|CONFLICT|STALE`, `LEDGER-<NAME>-SCHEMA`; scored `compliance(<section>): N/M <unit> canonical (P%)` plus `compliance(total)`.
- `ledgers` schema-validates every committed governance record: `decisions.jsonl`, `BACKLOG.json`, `BUGS.jsonl`, `FINDINGS.jsonl`, every `_RELEASE.json`, the three `_histo.jsonl`.
- `.dadaia/` zones and the `states/` canon are one registry (`core/workspace_layout.DADAIA_ZONES`), rendered into `.dadaia/AGENTS.md` at `public stage`; outside manifest, registry and exceptions (§5.1) = slop.
- The workspace section scans the root, the harness dirs, the `.dadaia/` zones and the top of every ALIVE registered repo — plus, at any depth in a repo, an excluded name or a nested `.dadaia/`.
- Slop and dead-repo leftovers are MOVED to `.dadaia/reaped/<YYYYMMDD>/<workspace-relative-path>` (a zone, 7-day TTL from the move, one hold per origin per day) and listed `WS-reaped-reaped`.
- Nothing is deleted directly: deletion happens only when a TTL zone's entry expires, `reaped/` included.
- `--fix` runs that reaper then the specs fixes; `--expired-only` scopes the report to the TTL lane, never the deletion.
- SessionStart runs `dadaia doctor --fix --expired-only --quiet`; the PostToolUse throttle runs the same reaper, which also owns marker GC.
- `HOOKS-DRIFT-1`: an ALIVE repo's installed `.git/hooks/pre-push` byte-differing from the shipped script; `fix: .dadaia/.venv/bin/dadaia ci install-hook --force`.

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
| Scoped law | `specs/AGENTS.md`, `.dadaia/AGENTS.md`, `.dadaia/handoff/AGENTS.md`, `repos/<slug>/AGENTS.md`, any nested `AGENTS.md` |
| Skills | `.claude/skills/`, `.agents/skills/` — skill-to-rule mapping declared once in `public/entities/behavior-map.json` |
| State | `dadaia context show --json`, `dadaia doctor`, `dadaia public doctor`, `dadaia bugs status` |

- Language: operator preference, default English. Tone: direct, concise, operational.

### 10.2 Glossary

- **workspace** — root tree holding `.dadaia/`, `repos/`, the law, every projection.
- **instance** — a live, operator-run dadaia-workspace instantiated from the library.
- **library** — this source repo, `dadaia_workspace/`, that scaffolds instances.
- **context** — the active Spec Context Project resolved for this session (§3.3).
- **spec context** — a `specs/` tree (root or `repos/<slug>/`) governed by this law.
- **release** — the open-scope publication unit, named last-published-PyPI + 1 patch; exactly one live.
- **candidate** — one closed-scope SDD cycle inside the live release; its trio lives at the release root.
- **rc-N** — the archive folder of the N-th completed-but-not-shipped candidate's trio.
- **task marker** — the `[ ] [-] [x]` open/in-progress/done trace in `TASKS.md`.
- **handoff** — the machine-readable JSON completion record an agent emits (§5.4).
- **verdict** — a reviewer's `APPROVED`/`REJECTED` recommendation in its handoff; the PR itself is gated by the `security-review` check.
- **chokepoint** — a git hook that gates the write path outside the harness hook.
- **gate** — the deterministic PreToolUse enforcement chain (§3.1).
- **path class** — the ADDITIVE/MUTATING/PROTECTED category a write path belongs to (§3.2).
- **scope** — the repo set a bind owns: the context's main repo plus its associated repos (§3.3).
- **stall** — a BLOCK whose own `fix:` command is itself blocked; CRITICAL (§3.1).
- **publication boundary** — the push, where the denylist scan runs over the pushed range against the published baseline (§7.4).
- **canon** — the closed set of paths a `specs/` root may contain (§6.2).
- **histo** — an append-only JSONL history file under an area's `_archive/`; one `histo-record-v1` per exited entry.
- **memory atom** — one Markdown file under `specs/memory/product/**` carrying current truth.
- **Part 1/Part 2** — a memory doc's ADR-gated Principles section vs its Implementation section.
- **ADR** — an accepted decision record in `ADRs/decisions.jsonl`.
- **backlog entry** — a candidate item in `backlog/BACKLOG.json`'s `active[]`.
- **disposition** — the terminal verdict closing a bug, backlog entry, audit or release: `delivered resolved superseded deferred rejected`.
- **audit** — a periodic three-pillar review producing one remediation release.
- **finding** — one recorded audit observation in `FINDINGS.jsonl`.
- **denylist** — the pattern list the pre-push scan refuses to let through.
- **projection** — a lib-originated copy of a `public/` asset installed into a runtime tree.
- **zone** — one top-level `.dadaia/` directory with a registry record: class, creator, TTL, canon, purpose (§8.5).
- **finding verdict** — `dadaia doctor`'s class for one scanned entry: `canon | operator | reaped | slop | expired | missing`; `canon`, `operator` and `reaped` count as canonical.
- **reaped** — an entry held in `.dadaia/reaped/` after the reaper moved it, awaiting its own TTL (§8.5).
- **finding code** — `WS-<zone>-<verdict>`, `<zone>` = `root`, a harness dir, `dadaia`, or a zone name without its leading dot.
- **instance exceptions** — `.dadaia/states/instance_exceptions.txt`, one glob per line, honoured at the root and inside the harness dirs (§5.1).
- **operator** — the human who owns the workspace and approves ADRs, deferrals, releases.
- **dispatcher** — an agent authorized to invoke another agent via subagent dispatch.
- **governance verb** — the one CLI command authorized to change a governance record (§6.6, §6.7, §6.8, §7.3).
- **bug proposal** — the operator-facing case for a bug before any record exists; `bug-proposal:` in a handoff finding when no operator is present (§7.3).
- **slop** — what passes the deletion test without loss (§7.6).
- **ratchet** — a contract test pinning a measured count that moves down only (§7.6).
- **fixed section** — a marker-bounded law block in a scaffolded spec, kept byte-equal to its fragment by `dadaia doctor` (§7.6).
