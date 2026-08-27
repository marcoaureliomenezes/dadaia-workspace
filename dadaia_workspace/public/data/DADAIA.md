# DADAIA.md — the workspace system prompt

You are operating inside a dadaia-workspace. This file is the **complete always-on law**:
one file, every rule, one source. It is generated from
`dadaia_workspace/public/data/DADAIA.md` and projected to the workspace root and
`.codex/`/`.kimi-code/`; Claude Code reaches it via `CLAUDE.md` -> `AGENTS.md` ->
`DADAIA.md` instead of a second projected copy. Sections cross-reference by name; each
fact is stated once.

Scoped `AGENTS.md` files govern their own subtree and take precedence there. This
library ships exactly two rule-file kinds: this one, and scoped `AGENTS.md` — anything
else you find is the operator's own.

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

A bug is fixed immediately, outside release material; a feature enters only through the
backlog.

Arm A is agent-dispatched: each stage — backlog-definition, release-definition,
implementation with its reviews and gates, and audit — is carried out by dispatching the
owning agent for that stage (§2) against the SDD documents (the `RELEASE.jsonl` fold,
SPEC, PLAN, TASKS, CLOSURE, per §6). You fan out explicitly; the documents themselves are
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
| E2E, test pyramid, deploy validation; closes each `rc-N` | `qa-engineer` |
| Six-axis review before a PR | `code-reviewer` |
| Vulnerabilities, secrets, CVEs; the push verdict (§7) | `security-reviewer` |
| Agents, skills, rules, workflows, commands, hooks — the AI surface | `ai-engineer` |
| Drift audits; dispatches evidence agents; scores compliance | `project-auditor` |

`product-engineer` reads the PM-curated backlog to author a release; it does not curate
the backlog. Every agent invokes `dd-ai-eng-knowhow` for harness literacy; only
`ai-engineer` reads its depth siblings to author or audit the AI-entity surface — every
other agent dispatches `ai-engineer` for that depth.

---

## 3. What is enforced deterministically

One PreToolUse entrypoint — `dadaia_workspace.hooks.pre_gate` — reads each tool payload
once and evaluates three policies in fixed order, **first block wins**:

1. **Root whitelist** — file-tool writes that would create a new top-level workspace-root
   entry (§5).
2. **Venv guard** — `Bash` only, matched on fixed leading tokens: `dadaia`, `pip`, and
   `python -m dadaia_workspace` run from `.dadaia/.venv/bin/`. The block message carries
   the corrected command.
3. **SDD gate** — path class × presence × phase × mode.

**Path classes** are context-relative: the same `specs/` taxonomy applies at the workspace
root and inside every `repos/<slug>/`.

| Class | Paths | Verdict |
|---|---|---|
| ADDITIVE | `specs/bugs|backlog|audits/`, `.dadaia/reports|handoff|tmp/` | Always writable; the record contract — immutable core, write-once, mutable governance — is audited, not gated. |
| MEMORY | `specs/memory/` | Writable in `DEFINITION` and `CLOSURE` phase |
| MUTATING | everything else in-repo | Writable; records advisory presence |
| FROZEN | `specs/_archive/` | Blocked — archive by `git mv`, never edit |
| PROTECTED | `.dadaia/sessions/`, projected law files (§8) | Blocked |

**Races are surfaced, always allowed** — locks, leases, and ownership blocks are absent by
design. A MUTATING write records an advisory presence record and proceeds; when another
live session holds presence on the same context, the write proceeds and one throttled
warning names that session. Presence I/O errors are swallowed and the write proceeds.

**Mode** resolves from the environment, then your own session record, defaulting to
IMPLEMENTATION. A session in READ mode blocks only its *own* MUTATING writes, as opt-in
self-protection; ADDITIVE paths stay writable and every other session is unaffected.

**Context and memory.** Resolve the active context from `DADAIA_CONTEXT`, then your own
session binding — the live session record keyed by your harness session id — then the
repo containing the working directory; inspect the result with `dadaia context show
--json`. `dadaia context bind` refreshes your session record and is the sole trigger for
context-memory injection; in a plain shell with no harness session id, the exported
`DADAIA_CONTEXT` env var **is** the binding (`bind` prints the export line). Bind selects
which memory you receive — it is optional, and ADDITIVE work needs none. Keep working;
alert the operator only when the workspace has zero ALIVE contexts.

**Git chokepoints** close the `Bash` write path, outside the gate's own parsing. They run
as git hooks, independent of any harness hook firing:

- **pre-commit** warns and always allows — commits flow, presence is surfaced.
- **pre-push** allows a `feature/*` push after the local CI preflight and a valid branch
  name; refuses any direct push of `develop` or `main` — those advance only by PR (full
  contract: §4 Gitflow).

The gate constrains **what** may be written; it stays silent on **how** the change was
produced, and reads zero SDD artifacts. Everything in §6 you uphold yourself.

**Skills instruct procedure. Audits measure conformance from git and JSONL history.
Hooks and the CLI validate only at the publication boundary (push/PR) and never block a
human.** This is the release's enforcement posture — the acceptance bar for every rule
in this file.

---

## 4. Gitflow — the branch contract

One law states the branch model; every other mention in this file is a cross-reference.
Start-of-work protocol, uniqueness and deletion discipline, and the CI/CD automation
suggestion for consumers: `dd-gitflow-default`.

| Branch | Pushable | Cut from | Advances by |
|---|---|---|---|
| `feature/{M.m.p}` | Yes — local CI preflight + valid name | `main` | opens the PR below |
| `develop` | No — never a direct push | `main` (bootstrap only) | PR from `feature/{M.m.p}`, at definition `Aprovado` and at each `rc` merge |
| `main` | No — never a direct push | — | PR from `develop`, at the final `rc` |

No `v` prefix, no suffix, no fifth pattern. `hotfix/*` is retired: reachable only on an
explicit operator request — no stage, no cadence, no PATCH-mint rule.

Exactly one live `feature/{M.m.p}` branch at a time. At deploy of `{M.m.p}`, delete
`feature/{M.m.p}` and cut `feature/{next}` in the same step. Bugs are fixed on the live
feature branch in any phase — no ceremony, no separate branch.

`rc-N` is a state of the specs, never a branch name: it lives in the `RELEASE.jsonl`
fold's phase and in `TASKS.md`, and each `rc` burns exactly one `feature/{M.m.p}` →
`develop` merge. `rc` scope is fixes and adjustments to the current release only — never
new backlog.

Both PRs — `feature/{M.m.p}` → `develop` and `develop` → `main` — are gated by a required
CI check demanding an APPROVED `security-reviewer` verdict covering the PR head sha.
Every stage of the flow — backlog definition, research, bug registration, release
definition and implementation — runs on `feature/{M.m.p}`; `develop` and `main` are PR
targets only, never a working branch.

Suggest the operator automate this contract in CI/CD whenever the topic comes up.

---

## 5. Where things are written

**Workspace root** holds only: `.agents/` `.claude/` `.codex/` `.dadaia/` `.kimi-code/`
`repos/` `AGENTS.md` `CLAUDE.md` `DADAIA.md` `prompt.md`. Anything the operator created
by hand stays, permanently. A tool that genuinely requires another root entry gets a
documented glob in `.dadaia/states/root_exceptions.txt`.

Everything else has a home under `.dadaia/`:

| Output | Path |
|---|---|
| Your temp files, scripts, screenshots, captures | `.dadaia/tmp/<agent>/<YYYYMMDD>/` |
| Machine-readable handoffs (the default emission) | `.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json` |
| HTML reports | `.dadaia/reports/<context>/<agent>/<UTC>-<slug>.html` |
| Tool caches, MCP working dirs | `.dadaia/` (`.dadaia/mcps/<server>/`) |

**Repos stay clean.** A repo working tree carries source and its own artifacts only,
excluding `.dadaia/`, `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.hypothesis/`,
`.ruff_cache/`, `test-results/`, `playwright-report/`, `coverage/`, `.coverage`.
`.dadaia/` is workspace-level only; creating one inside a repo corrupts context
resolution for every tool that walks the tree. Run tools with caching off or redirected:
pytest
`-p no:cacheprovider`, mypy `incremental = false`, hypothesis `database = None`, ruff
`--no-cache`, Playwright `outputDir` into `.dadaia/tmp/`. Gitignore is defence in depth,
not permission to create them.

**Emission is handoff-first.** Emit the JSON handoff by default. Add an HTML report when
the operator asks for one or the next handoff target is human; split reports over 30 KB
into multiple files behind an `index.html`. Validate with
`dadaia reports validate <path>.handoff.json` — the validator takes handoff files, and the
HTML's integrity rides on the handoff's `content_hash`.

---

## 6. Specs, tasks and memory

`Aprovado`, `Em revisão` and `Draft` are the canonical status tokens — keep them as they
are, in any language.

**Task lifecycle.** Read SPEC, PLAN and TASKS — all three carry `**Status:** Aprovado`.
Reserve your task by flipping `[ ]` → `[-]` *before* writing; hold at most one `[-]` at a
time unless TASKS declares disjoint write sets. Complete the work inside the task's
declared write set. Flip `[-]` → `[x]` and commit as `conventional-commit(task-id):
description`. The markers are the auditable trace of who took what.

<!-- behavior: memory -->
**Memory is current product truth, not history.** Read it before changing production
behavior. `product-engineer` writes `specs/memory/**` in the `DEFINITION` and `CLOSURE`
phases; every other agent reads it. Changelog and history live in `CLOSURE.md` and
`_archive/`. Each of `ARCHITECTURE.md`, `QUALITY.md` and `TECHSTACK.md` splits into
ADR-gated Part 1 Principles (each carrying `Measured by:`) and an evolving Part 2
Implementation.

<!-- behavior: adrs -->
**ADRs.** `specs/ADRs/NNNN-<slug>.md` records every principle-level decision — any agent
proposes, only the operator flips a decision to `accepted`, and the commit that changes a
Part-1 principle carries its accepted ADR.

<!-- behavior: backlog -->
**Backlog.** The backlog is the **operator's demand queue**: only the operator creates
demand. `project-manager` curates the single-source `specs/backlog/BACKLOG.md` — an
ACTIVE section of live candidates and a LEDGER section of one line per closed item;
everyone reads it freely. An entry materializes only through the PM's operator-facing
**intake report** (residuals from a closure, review or audit), which the operator decides
on first — an operator-ratified deferral taken during a release already counts as
approved intake. Every item is retained: it leaves ACTIVE only by gaining a LEDGER line
carrying its disposition and reason, and a picked item leaves ACTIVE in the same commit
that creates the release SPEC, which records its provenance. This retention law covers
bugs and backlog only — tests are prunable under the stewardship criteria (§7). Entry
schema, intake protocol and the disposition vocabulary: `dd-backlog-definition`.

**Branches.** Branch model, stage placement and merge/push mechanics: §4 (Gitflow).

<!-- behavior: releases -->
**Releases.** A release is `major.minor.patch` and matures through the `rc-N` lane
(branch mechanics: §4 Gitflow). A `dd-grill-me` session on the picked set precedes
the SPEC. At pick time, open bugs and undispositioned audits outrank fresh backlog.
Finalization order is **memory update → CLOSURE → archive**; a completed task group is
one commit.

<!-- behavior: audits -->
**Audits.** `specs/audits/<YYYYMMDD>-<slug>/AUDIT.md` + `FINDINGS.jsonl` hold the three
pillars — bug history, spec compliance, memory drift — run together, over the window
since the last audited release. An audit is suggested every 5 releases, never mandatory,
and generates exactly one remediation release that gives every finding an explicit
disposition — `fixed`, `superseded`, or `deferred`/`rejected` routed to the backlog. An
audit archives to `specs/audits/_archive/` only once fully dispositioned.

---

## 7. Quality

**Root cause, always.** Reproduce the failure on the executed path, write the test that
fails for the real reason, fix the cause, prove it green. Only a root-cause fix qualifies
as an acceptable outcome — workarounds and symptom patches are excluded.

**Test lifecycle.** Every test declares its intent and its size at birth; an undeclared
test is SCAFFOLD and expires. Demotion — replacing a LARGE test with equivalent cheaper
coverage — is a step of release closure, planned in advance. Pruning to go green is
exclusively a `qa-engineer` verdict: deleting, skipping or disabling a test carries
evidence, executed by `software-engineer`. Tombstone tests and expired SCAFFOLD are slop.
Test-artifact capture is failure-gated, written where §5 already says. Full protocol:
`dadaia-test-stewardship`.

<!-- behavior: bugs -->
**Register every bug you hit** while operating this tooling — any behavior that breaks
its own contract. Classify first: environment limits, invalid input, wrong usage, and a
validation the tool is designed to emit count as working-as-designed, outside the
product-bug definition. Append the `reported` event before the turn ends; bug paths are
ADDITIVE, so registration is always possible and immediate registration is always the
right call. Every event field excludes absolute local paths, IPs, hostnames, private
names and secrets. Command, redaction rule and context routing: `dd-bug-registration`.

Close a bug in the same session you prove the fix: append `resolved` with evidence that
is checkable — the red-loop command, the regression-test seam, and the diff direction on
the touched feature — then **commit**, staging exactly what the fix touched, excluding a
blanket `-A` over a shared tree; a net-positive diff routes to `software-architect` before
the commit. A solved bug leaves a clean worktree.

**Lineage and commit shape.** Every bug fix checks prior resolutions on the same
component before closing, declaring `caused_by: <bug_id> | none` with evidence —
protocol: `dd-diagnose`. Commit shapes (isolated registration/backlog/ADR commits; the
fix and its lineage line share the resolving commit) are `dd-gitflow-default` §3a —
measured by audits via `git log`, never a hook.

**Push green.** Every `feature/{M.m.p}` push runs the local CI preflight —
`ruff format --check`, `ruff check`, `mypy --strict` and `pytest` — before the branch
contract (§4 Gitflow) even considers it; run the tests locally before you push. This is
an always-on rule — the agent runs `dadaia ci preflight` before every push, not because
a hook forces it. A full scan survives solely in the audit lane (`project-auditor`
dispatch); the PR-gate security review is diff-based only. Only pushes are
review-blocked; commits flow freely. After every push or PR, watch CI to green
(`dd-release-implement`). A `quarantine`-marked test sits outside the gating selectors by
design and requires a registered bug — a green run with quarantined tests is still
green, but an unregistered pass-on-retry is a failure.

**Approval.** A candidate is approved when the operator and the consumer-side validation
agent agree, after validating a real workspace. A green internal gate that diverges from
real consumer behavior is itself a bug.

---

## 8. The library surface

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

**Public assets stay generic:** private repo names, hostnames, IPs, customer or
infrastructure names, operator-local paths, and optional domain-pack assumptions are
excluded from `dadaia_workspace/public/` entirely.

**Use the workspace venv.** Invoke `.dadaia/.venv/bin/dadaia` and `.dadaia/.venv/bin/pip`
directly, with absolute paths.

**Register every dev server** you start with `dadaia server register`, and check the
registry before opening a port.

---

## 9. Credentials

Credential material lives in exactly one place: the operator-managed `.env` at the
workspace root. Never create, copy, persist, commit, print, or report tokens, passwords,
private keys, cookies, auth payloads, or secret files — not in a repository, runtime
mount, image, generated configuration, cache, report, or handoff. A runtime process
receives only the values it needs from that root `.env` and never writes a second store.

---

## 10. Where to look next

| Surface | Where |
|---|---|
| Scoped law | `specs/AGENTS.md`, `.dadaia/reports/AGENTS.md`, `.dadaia/handoff/AGENTS.md`, `repos/<slug>/AGENTS.md`, and any nested `AGENTS.md` |
| Skills | `.claude/skills/`, `.agents/skills/` — which skill operates which rule is declared once, in `public/entities/behavior-map.json` alone |
| State | `dadaia context show --json`, `dadaia specs doctor`, `dadaia public doctor`, `dadaia server list`, `dadaia bugs status`, `dadaia panel` |

Language: follow the operator's preference, defaulting to English. Tone: direct, concise,
operational.
