---
name: project-auditor-drift-scorecard-triage
audit: 20260630T021228Z-251bb5f3
date: 2026-06-30
surface: specs/** + dadaia_workspace/** (code)
agent: project-auditor
role: cross-cutting drift scorecard + bug/backlog triage (drift anchor)
---

# Project-Auditor — Cross-Cutting Drift Scorecard & Triage

> Drift anchor for the full specs/memory↔code audit. READ-ONLY + ADDITIVE.
> Four sibling specialist auditors (ai-engineer/constitution, software-architect/architecture,
> product-engineer/memory, qa-engineer/tests) run in parallel; this report is the
> cross-cutting scorecard + bug/backlog triage that feeds the release-definition synthesis.

## Scope

- **Audited:** `specs/constitution.md`, `specs/memory/**`, `specs/backlog/**`, `specs/bugs/**`,
  `specs/releases/ACTIVE.md` (→ v0.1.41 CLOSURE), `dadaia_workspace/**` (runtime enum + harness
  surface), `dadaia specs doctor` + `dadaia public doctor` output.
- **Excluded (owned by sibling auditors / out of mandate):** deep per-feature memory-atom
  acceptance review, full architecture layer-boundary walk, full test-coverage re-measurement,
  any fix or spec/memory mutation (this agent never fixes drift).
- **Method:** `dadaia specs doctor`, `dadaia public doctor`, runtime-enum vs constitution vs
  memory cross-reference, `ruff F401/F811/F841` dead-code scan, frontmatter bug/backlog tally.

## Compliance Scorecard

| Dimension                 | Score (1-10) | Drift items | Notes |
|---------------------------|:------------:|:-----------:|-------|
| Spec ↔ code fidelity      | 6            | 1 HIGH      | constitution.md still lists OpenCode / `OPENCODE_RUN` / `.opencode/` as current; code enum has 4 runtimes |
| Memory ↔ code fidelity    | 8            | 1 LOW       | architecture.md + tech-stack.md accurate; only 2 stale `.opencode` strings in catalog.json summaries |
| Dead / stale code         | 8            | 2 LOW       | ruff F401/F811/F841 clean; known tracked debt (features→infra imports, pid-probe seam) |
| Test coverage             | 8            | 0           | 184 test files; CI history ~4105 green; not re-measured this pass (working tree dirty mid-CLOSURE) |
| Doc / structure clarity   | 6            | 16 warns    | constitution internal contradiction (10 root entries incl `.opencode/` vs AGENTS.md 6 dirs); doctor hygiene warnings; closed releases unarchived |
| Governance / process      | 7            | 4 warns     | gate/lease/bug-backlog governance healthy; SPEC-DOC-031 status-token hygiene on 4 backlog items |
| **Overall**               | **7.2**      | —           | Healthy with bounded, well-understood drift concentrated in the constitution OpenCode-sweep miss |

Weighted (spec↔code .20, mem↔code .20, dead .15, tests .15, doc .15, gov .15) = **7.15**;
floor = 6 (no dimension < 3, **no floor breach**, no mandatory hotfix). Overall ≈ **7.2/10**.

Recommendation band (6 ≤ score < 8): **minor-to-moderate drift — fold remediation into the next
release** (it does not warrant an emergency hotfix), but the constitution OpenCode drift is a HIGH
governing-doc finding that should be a named release-scope item.

## Drift inventory

### DRIFT-1 — constitution.md still presents OpenCode as a current runtime/harness  — **HIGH**
- **Dimension:** spec↔code fidelity / governance.
- **Claim (constitution.md):**
  - L136: `- **CLI-headless** — codex exec (CODEX_EXEC), opencode run (OPENCODE_RUN), and pi --mode json (PI_HEADLESS)`
  - L144: "The five `AgentRuntimeKind`s today are **FAKE, CODEX_EXEC, CLAUDE_SDK, OPENCODE_RUN, PI_HEADLESS**"
  - L165: ".opencode/ — OpenCode projection" listed among the "ten allowed root entries"
  - L444: OpenCode row in the Layer-1 entry-harness enforcement matrix
  - L449: "worker runtimes are FAKE, CODEX_EXEC, CLAUDE_SDK, OPENCODE_RUN, PI_HEADLESS"
- **Actual (code):** `dadaia_workspace/core/models/lifecycle.py:51` —
  `class AgentRuntimeKind(StrEnum): FAKE, CODEX_EXEC, CLAUDE_SDK, PI_HEADLESS` — **four** members, no
  `OPENCODE_RUN`. `policy_public_doctor.py` actively forbids `opencode` as a Layer-2 worker token
  and the doctor reports `[ok] workflow-policy (no Layer-2 claude/opencode worker residue)`.
- **Cross-validation:** `memory/architecture.md` and `memory/tech-stack.md` **correctly** state
  "OpenCode foi removido inteiramente em v0.1.24 (ambas as layers)". So memory and code agree; the
  **constitution alone is stale** — and it is the supreme governing document.
- **Internal contradiction:** constitution L165 lists `.opencode/` as an allowed root entry, but the
  root `AGENTS.md` Workspace Root Law / `tmp-file-guardrail` whitelist lists only 6 dirs
  (`.agents/.claude/.codex/.dadaia/.pi/repos/`) with **no** `.opencode/`. The constitution
  contradicts its own subordinate law.
- **Evidence:** `specs/constitution.md:136,144,165,444,449`; `dadaia_workspace/core/models/lifecycle.py:51-55`.
- **Recommended owner:** `product-engineer` (constitution is a spec; memory-guardian authority) in a
  DEFINITION phase, coordinated by `project-manager`. The auditor does not edit specs.

### DRIFT-2 — catalog.json carries 2 stale `.opencode` string leftovers  — **LOW**
- **Dimension:** memory↔code.
- **Claim:** `memory/product/catalog.json:185` tldr "projected to Claude Code, Codex, OpenCode, and
  shared .agents roots"; L144 harness-primitives summary "... .claude/.codex/.opencode/.agents".
- **Actual:** install targets are `{agents, claude, codex, pi}` (no `opencode`); architecture.md L78
  states targets explicitly. The substantive atom prose (architecture.md L369, tech-stack.md L46) is
  already corrected — only these two catalog summary strings lag.
- **Evidence:** `specs/memory/product/catalog.json:144,185` vs `specs/memory/architecture.md:78`.
- **Recommended owner:** `product-engineer` (memory) — trivial; the catalog generator
  (`scripts/generate-memory-catalog.py`) may re-emit it from atom frontmatter.

### DRIFT-3 — features → infrastructure direct imports (tracked debt)  — **LOW**
- **Dimension:** dead/stale code / architecture.
- 7 import-linter `ignore_imports` entries permit transitional direct `features → infrastructure`
  imports that should sit behind Protocol/DI. Tracked by backlog `features-import-infrastructure-direct-debt`.
- **Recommended owner:** `software-engineer` (behind `software-architect` boundary call).

### DRIFT-4 — pid-probe seam duplication  — **LOW**
- **Dimension:** dead/stale code.
- Duplicated `_build_pid_probe` seam wiring; tracked by backlog `pid-probe-seam-consolidation`.
- **Recommended owner:** `software-engineer`.

## Dead code

- `ruff check dadaia_workspace --select F401,F811,F841 --no-cache` → **All checks passed** (no unused
  imports, redefinitions, or unused locals). No dead modules surfaced by the lint pass.
- `opencode_runtime` adapter and `public/plugins/sdd-gate.ts` were already **deleted** in v0.1.24
  (confirmed by architecture.md L70/L78) — no orphaned OpenCode code remains in the tree. The
  residue is documentation-only (DRIFT-1, DRIFT-2).
- Known, tracked structural debt: features→infrastructure imports (DRIFT-3), pid-probe seam (DRIFT-4),
  telemetry Tier-2 chmod on Windows (backlog `telemetry-tier2-chmod-unguarded-on-windows`).

## Spec consistency

- **`dadaia specs doctor`:** 0 errors, **16 warnings** — all hygiene-class, contract working as
  designed:
  - 7× SPEC-DOC-016 + 2× SPEC-DOC-027: legacy `_archive` release dirs with non-SemVer names
    (`v0.1.4.x`, `ctx-inject-v2-...`, `multiharness-engine-v0116`, `pi-fourth-harness-v1`). Preserved
    by design until renamed; no action required this release.
  - TREE-5: `specs/AGENTS.md` drifted from canonical template (auto-overwrite disabled to protect
    operator customisation) — review-and-merge item, not auto-fixable.
  - SPEC-DOC-030: audit dir `audits/2026-06-12T001813Z` predates the collision-safe naming law — rename-only.
  - 4× SPEC-DOC-031: backlog items `features-import-infrastructure-direct-debt`, `panel-ux-overhaul`,
    `plugin-packs-and-install-command`, `sdd-governance-v2-agents-lifecycle` have `status: candidate`
    but are slug-referenced by archived releases. Doctor itself labels this the ADR-6 false-positive
    class (a mention is not proof of consumption) — **correct contract behavior**, not drift. These
    items are genuinely still-open candidates (verified below).
- **`dadaia public doctor`:** `[ok] public-privacy`, `[ok] model-resolution`, `[ok] ai-surface`,
  `[ok] workflow-policy (no Layer-2 claude/opencode worker residue)`. 4× `[drift]` on Codex hook
  projections (`codex-pre-gate/post-gate/ctx-inject/ctx-inject-session-start`, `codex:config.toml`)
  + 3× `git-dirty` on public source files (`data/AGENTS.md`, `bug_report/bug-write.md`,
  `lint-memory-atoms.py`). The drift + git-dirty are consistent with the **in-progress v0.1.41
  CLOSURE** working tree (20+ modified code files staged/unstaged) — verify they are committed before
  the release ships; re-run `dadaia public install --target all` to clear the Codex-hook drift.
- **Closed-but-unarchived releases:** v0.1.35/alpha-1, v0.1.36/alpha-1+rc-1, v0.1.37/alpha-1,
  v0.1.38/alpha-1, v0.1.39/alpha-1, and v0.1.41 (flat, active CLOSURE) carry CLOSURE.md but live
  under `specs/releases/` not `_archive/releases/`. Doctor does not flag this (archival happens at
  next-release definition), but the spec-reviewer rule ("no closed release outside archive") makes
  it a hygiene item — sweep into `_archive/releases/` at the next release-definition.
- **ACTIVE.md** → `release: v0.1.41 / phase: CLOSURE`. Release dir exists and is well-formed
  (SPEC/PLAN/TASKS/CLOSURE/GRILL/OQ-DECISIONS present). No orphaned-pointer escalation.

## Bug triage

> **Seed correction:** the "2 Open" count is a **grep artifact**, not reality. The closed bug
> `bug-report-fake-bug-write-emits-stub-and-discards-fields.md` (frontmatter `status: Closed`,
> resolved v0.1.37) contains an **embedded example markdown block** with `status: Open` at
> line-start (its line 47), which a `grep "^status: Open"` falsely counts. Frontmatter-only
> extraction confirms exactly **ONE genuinely-open bug**.

| Bug | Status | Sev | Valid? | Belongs in next release? |
|---|---|---|---|---|
| `lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence` | **Open** | MEDIUM | **VALID** | **YES** |
| `bug-report-fake-bug-write-emits-stub-and-discards-fields` | Closed (v0.1.37) | MEDIUM | n/a | already fixed — no action |

- **`lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence`** (reported 2026-06-30):
  VALID, severity MEDIUM appropriate. The `lifecycle close --harness fake` path accepts `fake`,
  then **blocks at closure** with "agent result missing artifact evidence." This is the **same class**
  as the just-Closed `bug-report-fake-bug-write` and the earlier-Closed
  `release-definition-fake-runtime-does-not-produce-canonical-artifacts`: the FAKE runtime is
  presented as a viable default but cannot satisfy a workflow step's evidence gate. **Recommended
  fix shape (for the release SPEC):** the fake closure runtime should either (a) materialize valid
  closure artifact evidence, or (b) the CLI should reject/warn that `--harness fake` cannot drive a
  real closure before the workflow starts. **Belongs in the upcoming release** (per release-governance
  "bugs are always solved" — every picked bug is fixed unless superseded).

## Backlog triage

| Item | Status | Verdict | One-line |
|---|---|---|---|
| `workflow-model-governance-panel-control-plane` | candidate (CRIT) | **VALID-PICK** | operator's flagged next release; control-plane for workflow model/harness governance |
| `backlog-definition-workflow-dedup-conflict-control` | delivered | **ALREADY-DELIVERED** | shipped v0.1.26/27 (FEAT-BACKLOG-DEFINITION-WORKFLOW-01); frontmatter = delivered |
| `workflow-step-handoff-data-plane-cleanup` | delivered | **ALREADY-DELIVERED** | shipped v0.1.30 wave D (run-scoped handoff ledger); frontmatter = delivered |
| `sdd-governance-v2-agents-lifecycle` | candidate | **VALID-PICK (residual)** | see dedicated read below — JSONL bug-events + audit-disposition law remain |
| `panel-ux-overhaul` | candidate (MED) | **VALID-PICK** | tab consolidation + theme-switcher; intake only, mandatory grill before SPEC |
| `model-tier-efficiency-and-fast-tier-utilization` | candidate (P2) | **VALID-PICK** | Layer-1 `fast` tier has 0 assignments (all 9 = opus-4-8); no efficiency-audit trigger |
| `plugin-packs-and-install-command` | candidate (MED) | **VALID-PICK** | blocks the 3 plugin agents + panel-UX deviation; no install command exists yet |
| `centralize-release-semver-canon` | idea (LOW) | **VALID-PICK (low)** | one shared SemVer-canon constant across scaffolder/doctor/new_artifacts |
| `features-import-infrastructure-direct-debt` | candidate (MED) | **VALID-PICK** | remove 7 transitional features→infra import-linter ignores behind Protocol/DI |
| `pid-probe-seam-consolidation` | candidate (LOW) | **VALID-PICK (low)** | single composition-root builder for the PID probe |
| `telemetry-tier2-chmod-unguarded-on-windows` | candidate (LOW) | **VALID-PICK (low)** | Tier-2 telemetry os.chmod silent no-op on Windows; route via platform seam |
| `review-rejection-rework-path` | idea (LOW) | **VALID-PICK (low)** | wire/document `_blocked_result` → implementation_ladder rework loop on REJECTED |
| `codex-runtime-fidelity` | delivered | **ALREADY-DELIVERED** | frontmatter = delivered |
| `lifecycle-prompt-fragments-ai-surface-dehydration` | delivered | **ALREADY-DELIVERED** | frontmatter = delivered |
| `pi-agent-fourth-harness` | delivered | **ALREADY-DELIVERED** | PI shipped v0.1.18–22; frontmatter = delivered |
| `shared-headless-adapter-base` | delivered | **ALREADY-DELIVERED** | shipped v0.1.30 wave A; frontmatter = delivered |
| `wire-consumed-ledger-producer-at-release-definition` | delivered | **ALREADY-DELIVERED** | shipped v0.1.27; frontmatter = delivered |
| `workflow-model-governance-operator-profiles-and-context-overlays` | delivered | **ALREADY-DELIVERED** | shipped v0.1.28/30; frontmatter = delivered |
| `ideas.md → pytest-xdist` | idea | **STALE-DEFER** | informal; revisit only when CI wall-time exceeds budget |

Net open backlog actually pickable: **12 items** (3 CRITICAL/operator-flagged: panel-control-plane,
sdd-gov-v2 residual, panel-ux; the rest MEDIUM/LOW debt). 8 items are terminal `delivered` and should
have their SPEC-DOC-031 status handled at archival. No SUPERSEDED items detected this pass.

## Read on `sdd-governance-v2-agents-lifecycle` as the release vehicle

**Verdict: it is NOT the right vehicle for the constitution/memory OpenCode re-scoping — and it
already says so itself.** The entry was explicitly **scope-corrected on 2026-06-26**: its §22-24
and §82-87 strip all OpenCode-enforcement/parity scope as **dead** ("OpenCode removed v0.1.24") and
narrow the residual to exactly **two pillars**:

1. **event-sourced JSONL bug telemetry** — `dadaia bugs append|status|stats` over append-only
   `specs/bugs/<ts>.jsonl`, a shipped event schema, a one-time `*.md → JSONL` migration via
   `dadaia specs upgrade`, and a rewrite of the `bug-registration-guardrail` rule format section.
2. **audit-disposition law** — the first release after an audit must give every finding an explicit
   disposition (fixed/superseded/deferred/rejected), open bugs+audits outrank plain backlog at pick,
   and `project-auditor` owns a bug-trend audit gating bug archiving.

This is a **clean, well-scoped residual epic** and a VALID-PICK, but its subject is *bug/audit
governance plumbing*, not constitution-doc accuracy. **The OpenCode constitution drift (DRIFT-1) is
orphaned** — no current backlog item owns "make constitution.md match the 4-runtime / 6-root-entry
reality." It must be added as its own release-scope line (a `product-engineer` DEFINITION-phase
constitution+catalog correction), **not** folded into sdd-gov-v2.

Note also: this very audit effort is the kind of input that sdd-gov-v2's **audit-disposition law**
is designed to formalize — shipping that pillar would make the present findings flow into the next
release deterministically. That is an argument for picking sdd-gov-v2 **soon**, but still as a
separate concern from the doc-correction.

## Recommended actions (priority-ordered; names the owner — never "fix it yourself")

1. **[HIGH] Correct the constitution OpenCode drift (DRIFT-1).** Open a release-scope line for
   `product-engineer` (DEFINITION phase, dispatched by `project-manager`) to: drop `OPENCODE_RUN`
   from the runtime lists (4 runtimes, not "five"), remove `.opencode/` from the "ten allowed root
   entries" (→ aligns with AGENTS.md 6-dir law), and remove the OpenCode entry-harness matrix row.
   This is a governing-doc/code contradiction and the single biggest cross-cutting drift.
2. **[LOW] Sweep the 2 stale `.opencode` strings in catalog.json (DRIFT-2)** — `product-engineer`;
   regenerate via `scripts/generate-memory-catalog.py` after the atom prose is confirmed clean.
3. **[MEDIUM] Fix open bug `lifecycle-close-fake-harness...`** — `software-engineer` (after
   `project-manager` picks it into the release): make the fake closure path emit valid evidence OR
   reject/warn `--harness fake` for closure up front. Pairs with the FAKE-runtime-honesty class.
4. **[CRITICAL/operator] Pick the next release set** — `project-manager` → `product-engineer`:
   strongest candidates are `workflow-model-governance-panel-control-plane` (operator-flagged) and
   `sdd-governance-v2-agents-lifecycle` residual; both require the mandatory `dadaia-grill-me`
   before SPEC (release-governance).
5. **[LOW hygiene] Before v0.1.41 ships:** commit the dirty public source files and re-run
   `dadaia public install --target all` to clear the 4 Codex-hook `[drift]` lines; `devops-engineer`
   [plugin] or the closing implementer.
6. **[LOW hygiene] At next release-definition:** `git mv` the closed unarchived releases
   (v0.1.35–v0.1.40) into `_archive/releases/`; flip the 4 SPEC-DOC-031 terminal-status tokens for
   any genuinely-consumed backlog items — `product-engineer` / `project-manager`.

## Evidence sources

- `dadaia specs doctor` — 0 errors, 16 warnings (full output captured this session).
- `dadaia public doctor` — public-privacy/model-resolution/ai-surface/workflow-policy [ok]; 4 Codex
  hook [drift] + 3 git-dirty (in-progress CLOSURE).
- `dadaia_workspace/core/models/lifecycle.py:51-55` — `AgentRuntimeKind` enum (4 members).
- `dadaia_workspace/features/lifecycle/policy_public_doctor.py` — forbids `opencode` Layer-2 leak.
- `specs/constitution.md:136,144,165,444,449` — stale OpenCode references.
- `specs/memory/architecture.md:70,78,369`, `specs/memory/tech-stack.md:46` — correct OpenCode-removed prose.
- `specs/memory/product/catalog.json:144,185` — stale `.opencode` string leftovers.
- `ruff check dadaia_workspace --select F401,F811,F841 --no-cache` — All checks passed.
- `specs/bugs/` frontmatter scan — 135 Closed, **1 genuinely Open** (grep false-positive corrected).
- `specs/backlog/*.md` frontmatter scan + `candidates.md` + `ideas.md`.
- Sibling auditors (ai-engineer, software-architect, product-engineer, qa-engineer) running in
  parallel — cross-validation expected on DRIFT-1; this report is the cross-cutting synthesis.
