# DADAIA.md — the workspace system prompt

You are operating inside a dadaia-workspace. This file is the **complete always-on law**
of the workspace: one file, every rule, no second source. It is generated from
`dadaia_workspace/public/data/DADAIA.md` and projected to the workspace root and to every
harness directory. Sections cross-reference by name; no fact is stated twice.

Scoped `AGENTS.md` files govern their own subtree and take precedence there. Anything
else you find is the operator's own — this library ships exactly two kinds of rule file:
this one, and scoped `AGENTS.md`.

---

## 1. The flow — the mandatory default

Every demand runs through one of two arms. Classify the demand, **say which arm you are
in**, then follow it. Deviating requires an explicit, confirmed request from the
operator; when in doubt, follow the flow.

**Arm A — feature work** (new capability):

```
demand → backlog-definition → release-definition → implementation + reviews/gates → audit
```

**Arm B — bug** (the tool violated its own contract):

```
register → reproduce on the executed path → RED test → root-cause fix → GREEN → resolved event → commit
```

Choose the arm by one question: *does the tool violate a contract it already promises?*
Yes → Arm B, fixed on the spot. No → Arm A, matured through a release.

Bugs are never release material and never wait for one. Features never skip the backlog.

Arm A is agent-dispatched, not engine-run: each stage — backlog-definition,
release-definition, implementation with its reviews and gates, and audit — is carried out
by dispatching the owning agent for that stage (§2) against the SDD documents
(`ACTIVE.md`, SPEC, PLAN, TASKS, CLOSURE, per §5). No workflow engine assembles prompts or
advances gates on your behalf; you fan out explicitly and the documents themselves are
the record of progress.

---

## 2. Who does what

Dispatch by artifact class. Each agent's frontmatter carries its own write allowlist;
stay inside it.

| The work | Owner |
|---|---|
| Backlog curation — what enters, matures, leaves `specs/backlog/**` | `project-manager` |
| Coordination, grill-me intake, dispatch | `project-manager` |
| SPEC / PLAN / TASKS / CLOSURE, and `specs/memory/**` | `product-engineer` |
| Architecture: DRAFT, REVIEW, ONBOARD; root-cause and fidelity gates | `software-architect` |
| Production code and its tests, in any language | `software-engineer` |
| E2E, test pyramid, deploy validation; closes each `alpha-N` | `qa-engineer` |
| Six-axis review before a PR | `code-reviewer` |
| Vulnerabilities, secrets, CVEs; the push verdict (§6) | `security-reviewer` |
| Agents, skills, rules, workflows, commands, hooks — the AI surface | `ai-engineer` |
| Drift audits; dispatches evidence agents; scores compliance | `project-auditor` |

`product-engineer` reads the PM-curated backlog to author a release; it does not curate
the backlog. `ai-engineer` alone invokes the `ai-harness-*` and `ai-context-engineering`
skills — every other agent uses `harness-primitives` for harness literacy and dispatches
`ai-engineer` for depth.

---

## 3. What is enforced deterministically

One PreToolUse entrypoint — `dadaia_workspace.hooks.pre_gate` — reads each tool payload
once and evaluates three policies in fixed order, **first block wins**:

1. **Root whitelist** — file-tool writes that would create a new top-level workspace-root
   entry (§4).
2. **Venv guard** — `Bash` only, matched on fixed leading tokens: `dadaia`, `pip`, and
   `python -m dadaia_workspace` run from `.dadaia/.venv/bin/`. The block message carries
   the corrected command.
3. **SDD gate** — path class × presence × phase × mode.

**Path classes** are context-relative: the same `specs/` taxonomy applies at the workspace
root and inside every `repos/<slug>/`.

| Class | Paths | Verdict |
|---|---|---|
| ADDITIVE | `specs/bugs|backlog|audits/`, `.dadaia/reports|handoff|tmp/` | Always writable — register bugs freely, in any mode |
| MEMORY | `specs/memory/` | Writable in `DEFINITION` and `CLOSURE` phase |
| MUTATING | everything else in-repo | Writable; records advisory presence |
| FROZEN | `specs/_archive/` | Blocked — archive by `git mv`, never edit |
| PROTECTED | `.dadaia/sessions/`, projected law files (§7) | Blocked |

**Races are surfaced, never prevented.** There is no lock, lease, or ownership block. A
MUTATING write records an advisory presence record and proceeds; when another live
session holds presence on the same context, the write is allowed and one throttled
warning names that session. Presence I/O errors are swallowed and the write proceeds.

**Mode** resolves from the environment, then your own session record, then defaults to
IMPLEMENTATION. A session in READ mode blocks only its *own* MUTATING writes, as opt-in
self-protection; ADDITIVE paths stay writable and no other session is affected.

**Context and memory.** Resolve the active context from `DADAIA_CONTEXT`, then your own
session binding — the live session record keyed by your harness session id — then the
repo containing the working directory; inspect the result with `dadaia context show
--json`. `dadaia context bind` refreshes your session record and is the sole trigger for
context-memory injection; in a plain shell with no harness session id, the exported
`DADAIA_CONTEXT` env var **is** the binding (`bind` prints the export line). Bind selects
which memory you receive — it is never a precondition for work, and ADDITIVE work needs
none. Keep working; tell the operator only when the workspace has no ALIVE context at all.

**Git chokepoints** close the `Bash` write path, which the gate does not parse. They run
as git hooks and do not depend on any harness hook firing:

- **pre-commit** warns and always allows — commits flow, presence is surfaced.
- **pre-push** refuses any pushed ref other than `refs/heads/develop` (tag pushes carve
  out), validates the branch name against the four permitted patterns (§5), and requires
  an APPROVED `security-reviewer` verdict covering the delta being pushed, plus the CI
  preflight (§6).

The gate reads no SDD artifacts: it constrains **what** may be written, never **how** the
change was produced. Everything in §5 you uphold yourself.

---

## 4. Where things are written

**Workspace root** holds only: `.agents/` `.claude/` `.codex/` `.dadaia/` `.kimi-code/`
`repos/` `AGENTS.md` `CLAUDE.md` `DADAIA.md` `prompt.md`. Anything the operator
created by hand stays and is never auto-deleted. A tool that genuinely requires another
root entry gets a documented glob in `.dadaia/states/root_exceptions.txt`.

Everything else has a home under `.dadaia/`:

| Output | Path |
|---|---|
| Your temp files, scripts, screenshots, captures | `.dadaia/tmp/<agent>/<YYYYMMDD>/` |
| Machine-readable handoffs (the default emission) | `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json` |
| HTML reports | `.dadaia/reports/<context>/<agent>/<UTC>-<slug>.html` |
| Tool caches, MCP working dirs | `.dadaia/` (`.dadaia/mcps/<server>/`) |

**Repos stay clean.** A repo working tree carries source and its own artifacts — never
`.dadaia/`, `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.hypothesis/`, `.ruff_cache/`,
`test-results/`, `playwright-report/`, `coverage/`, `.coverage`. `.dadaia/` is
workspace-level only; creating one inside a repo corrupts context resolution for every
tool that walks the tree. Run tools with caching off or redirected: pytest
`-p no:cacheprovider`, mypy `incremental = false`, hypothesis `database = None`, ruff
`--no-cache`, Playwright `outputDir` into `.dadaia/tmp/`. Gitignore is defence in depth,
not permission to create them.

**Emission is handoff-first.** Emit the JSON handoff by default. Add an HTML report when
the operator asks for one or the next handoff target is human; split reports over 30 KB
into multiple files behind an `index.html`. Validate with
`dadaia reports validate <path>.handoff.json` — the validator takes handoff files, and the
HTML's integrity rides on the handoff's `content_hash`.

---

## 5. Specs, tasks and memory

`Aprovado`, `Em revisão` and `Draft` are the canonical status tokens — keep them as they
are, in any language.

**Task lifecycle.** Read `ACTIVE.md` for the release and phase. Read SPEC, PLAN and TASKS
— all three carry `**Status:** Aprovado`. Reserve your task by flipping `[ ]` → `[-]`
*before* writing; hold at most one `[-]` at a time unless TASKS declares disjoint write
sets. Complete the work inside the task's declared write set. Flip `[-]` → `[x]` and
commit as `conventional-commit(task-id): description`. The markers are the auditable
trace of who took what.

**Memory is current product truth, not history.** Read it before changing production
behavior. `product-engineer` writes `specs/memory/**` in the `DEFINITION` and `CLOSURE`
phases; every other agent reads it. Changelog and history live in `CLOSURE.md` and
`_archive/`.

**Backlog.** The backlog is the **operator's demand queue**: only the operator creates
demand. `project-manager` curates the single-source `specs/backlog/BACKLOG.md` — an
ACTIVE section of live candidates and a LEDGER section of one line per closed item;
everyone reads it freely. No agent materializes an entry: residuals from a closure,
review or audit are compiled by the PM into an **intake report** the operator decides on
first, and an operator-ratified deferral taken during a release is already approved
intake. Nothing is deleted: an item leaves ACTIVE only by gaining a LEDGER line carrying
its disposition and reason, and a picked item leaves ACTIVE in the same commit that
creates the release SPEC, which records its provenance. This never-delete law covers
bugs and backlog only — tests are prunable under the stewardship criteria (§6). Entry
schema, intake protocol and the disposition vocabulary: `dd-backlog-definition`.

**Branches.** Exactly four patterns, no fifth: `main` (remote+local, never committed or
pushed to directly, advances only via a GitHub-enforced PR from `develop`); `develop`
(remote+local, **the only pushable branch**); `feature/{M.m.p}` and `hotfix/{M.m.p}`
(both local-only, cut from `develop`). Backlog-definition, research and bug registration
run directly on `develop`, one commit per entry. Stage contract, mechanical enforcers,
and the mechanical-vs-discipline split: the `dadaia-gitflow` skill.

**Releases.** A release is `major.minor.patch`, matures through `alpha-N → rc-N`.
Definition and implementation both run on `feature/{M.m.p}`, which merges into local
`develop` at two milestones — (a) when SPEC+PLAN+TASKS are `Aprovado`, (b) at ship — each
followed, in order, by a diff-based security review of `origin/develop..develop` and a
push of `develop`; ship then opens a PR `develop` → `main`. A `dadaia-grill-me` session
on the picked set precedes the SPEC. Each `alpha-N` closes with a `qa-engineer` review
committed to the branch. At pick time, open bugs and undispositioned audits outrank fresh
backlog. Finalization order is **memory update → CLOSURE → archive**; a completed task
group is one commit.

**Hotfixes.** A bug fix stays Arm B (§1) in full, run on `hotfix/{M.m.p}` at the next
PATCH — **no release ceremony**: no SPEC, PLAN, TASKS, or `specs/releases/<id>/`
directory. Procedure: `dd-bug-fix`.

**Audits.** One audit generates exactly one remediation release, and that release gives
**every** finding an explicit disposition — `fixed`, `superseded` by a broader picked
item, or `deferred`/`rejected` with a reason routed to the backlog. An audit archives to
`specs/audits/_archive/` only once fully dispositioned by an approved release, and names
that release.

---

## 6. Quality

**Root cause, always.** Reproduce the failure on the executed path, write the test that
fails for the real reason, fix the cause, prove it green. Workarounds and symptom patches
are not acceptable outcomes.

**Test lifecycle.** Every test declares its intent and its size at birth; an undeclared
test is SCAFFOLD and expires. Demotion — replacing a LARGE test with equivalent cheaper
coverage — is a step of release closure, never an afterthought. The implementer never
prunes to go green: deleting, skipping or disabling a test is a `qa-engineer` verdict
carrying evidence, executed by `software-engineer`. Tombstone tests and expired SCAFFOLD
are slop. Test-artifact capture is failure-gated, written where §4 already says. Full
protocol: `dadaia-test-stewardship`.

**Register every bug you hit** while operating this tooling — any behavior that breaks
its own contract. Classify first: environment limits, invalid input, wrong usage, and a
validation the tool is designed to emit are not product bugs. Append the `reported`
event before the turn ends; bug paths are ADDITIVE, so registration is always possible
and there is no reason to defer it. Command, redaction rule and context routing:
`dd-bug-registration`.

Close a bug in the same session you prove the fix: append `resolved` with
`--resolution-evidence` (reproducing test, fix, suite result), then **commit** — stage
exactly what the fix touched, never `-A` over a shared tree. A solved bug leaves a clean
worktree.

**Push green.** The pre-push hook refuses any pushed ref other than `refs/heads/develop`
(tag pushes carve out) and validates the branch name against the four permitted patterns
(§5); it runs `ruff format --check`, `ruff check`, `mypy --strict` and `pytest`; and it
requires an APPROVED `security-reviewer` handoff whose review covers the
`origin/develop..develop` delta being pushed — diff-based only, with a full scan
surviving solely in the audit lane (`project-auditor` dispatch). Run the tests locally
before you push. Commits are never review-blocked — only pushes. After every push or PR,
watch CI to green (`dd-release-implement`). A `quarantine`-marked test sits outside the
gating selectors by design and requires a registered bug — a green run with quarantined
tests is still green, but an unregistered pass-on-retry is a failure.

**Approval.** A candidate is approved when the operator and the consumer-side validation
agent agree, after validating a real workspace. A green internal gate that diverges from
real consumer behavior is itself a bug.

---

## 7. The library surface

Files listed in `.dadaia/agentic/manifest.json` are lib-originated projections. Change
them at the source, then re-project:

```bash
dadaia public stage
dadaia public install --target all      # overwrites whenever the staged hash differs
dadaia public doctor                    # must report [ok] public-privacy
```

`--force` is only for a projection someone hand-edited away from both source and staging.

**The law files are human-only in an instantiated workspace.** `DADAIA.md` and the
library's `AGENTS.md` files are projected read-only and are PROTECTED (§3): change them by
editing `dadaia_workspace/public/` and re-projecting. Only a human operator edits a
projected law file by hand.

**Public assets stay generic.** No private repo names, hostnames, IPs, customer or
infrastructure names, operator-local paths, or optional domain-pack assumptions ever
enter `dadaia_workspace/public/`.

**Use the workspace venv.** Invoke `.dadaia/.venv/bin/dadaia` and `.dadaia/.venv/bin/pip`
directly, with absolute paths.

**Register every dev server** you start with `dadaia server register`, and check the
registry before opening a port.

---

## 8. Credentials

Credential material lives in exactly one place: the operator-managed `.env` at the
workspace root. Never create, copy, persist, commit, print, or report tokens, passwords,
private keys, cookies, auth payloads, or secret files — not in a repository, runtime
mount, image, generated configuration, cache, report, or handoff. A runtime process
receives only the values it needs from that root `.env` and never writes a second store.

---

## 9. Where to look next

| Surface | Where |
|---|---|
| Scoped law | `specs/AGENTS.md`, `.dadaia/reports/AGENTS.md`, `.dadaia/handoff/AGENTS.md`, `repos/<slug>/AGENTS.md`, and any nested `AGENTS.md` |
| Skills | `.claude/skills/`, `.agents/skills/` — `dadaia-cli` maps the CLI; `harness-primitives` covers harness literacy; `dadaia-gitflow` covers the branch contract; the `dd-*` family maps the development cycle, one skill per stage |
| State | `dadaia context show --json`, `dadaia specs doctor`, `dadaia public doctor`, `dadaia server list`, `dadaia bugs status`, `dadaia panel` |

Language: follow the operator's preference, defaulting to English. Tone: direct, concise,
operational.
