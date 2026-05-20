# Plan: Release — token-cost-bigbang-v1

> **Status:** Aprovado
> **Release ID:** token-cost-bigbang-v1
> **Owner:** product-engineer (PLAN authorship); ai-engineer + devops-engineer + product-engineer (IMPLEMENTATION owners per task)
> **Created:** 2026-05-20
> **Predecessor SPEC:** `specs/releases/token-cost-bigbang-v1/SPEC.md` (Draft → must reach Aprovado before this PLAN flips to Em revisão → Aprovado)

---

## 1. Strategy

Single big-bang release. All 19 actionable decisions (D-01..D-11, D-13..D-20; D-12
explicitly dropped per backlog) land in one merge. No staged rollout, no backwards-
compat shims, no half-migrated agents. The argument is in audit §0 + backlog §0:
no external consumers gate this lib yet, so the cutover window is now.

Three execution phases inside the SDD `IMPLEMENTATION` gate, plus a post-CLOSURE
validation phase. The SDD pipeline wraps the backlog phases — it is NOT replaced by
them:

```
[DISCOVERY done] → SPEC (this Draft) → PLAN (this Draft) → TASKS
  → IMPLEMENTATION (P1 done; P2-A → P2-B + P2-C parallel → P2-D) → CLOSURE → ARCHIVED
                                                                  └── post-archive: P3 (T-50..T-54, 7-day validation)
```

Critical rule: **execute T-01 (operator plugin uninstalls) BEFORE dispatching
ai-engineer/devops-engineer for the rewrite.** T-01 is already done (backlog footnote
`Status 2026-05-19: 3/3 uninstalls done`). Operator restart of session (T-02) +
ccusage baseline capture (T-03) precede T-04 (release kickoff). The rewrite then runs
on the cheaper, leaner session.

---

## 2. Layers affected

| Layer | Surfaces touched | Owner |
|---|---|---|
| **Schema** | `dadaia_workspace/public/schemas/handoff-v1.schema.json` → upgrade to `handoff-v1.1` | devops-engineer |
| **CLI** | `dadaia reports validate` (accept v1.1, reject v1.0 missing fields), new `dadaia reports lint <dir>` | devops-engineer |
| **Doctor** | `dadaia public doctor` lint rule rejecting `subagent_type: software-engineer` references | devops-engineer |
| **Agent personas** | `dadaia_workspace/public/agents/*.md` × 20 — model flip, description trim ≤ 200 chars, body template extraction, allow-list lines for `frontend-design` plugin (2 agents only) | ai-engineer |
| **Skill catalogue** | `dadaia_workspace/public/skills/**` — 22 Tier-B skills migrated to `docs/agent-knowledge/<agent>/<topic>.md`, 11 Tier-A retained | ai-engineer |
| **Shared rules** | NEW `dadaia_workspace/public/rules/workspace-protocol.md` (factor-out from agent bodies); NEW `dadaia_workspace/public/rules/plugin-scope.md` (D-20 enforcement) | ai-engineer |
| **Workflows** | `dadaia_workspace/public/workflows/*.workflow.md` × 7 — add `consumes: [sidecar-path]`, inject dispatch-to-researcher at read-heavy stages | ai-engineer |
| **Projection install** | `dadaia_workspace/infrastructure/public_assets.py` — `_install_*` rewrite: AGENTS.md canonical, CLAUDE.md 1-line stub, `.agents/skills/` shared with symlinks | devops-engineer |
| **Constitution** | `specs/constitution.md` — ADRs X1..X7 amendment (CLOSURE phase only) | product-engineer |
| **Memory atoms** | `specs/memory/architecture.html`, `specs/memory/tech-stack.html`, `specs/memory/product/{index,agent-orchestration}.html` (CLOSURE phase only) | product-engineer |
| **Read-only / preserved** | `repos/tauan-games/**` (game scope rule), source code in `repos/*/src/**` outside scope | — |

---

## 3. Phase plan (verbatim from backlog §2)

### Phase mapping — backlog phase → SDD gate

| Backlog phase | SDD gate | Owner | Notes |
|---|---|---|---|
| P1 — operator quick wins (T-01..T-04) | DISCOVERY (T-01..T-03 pre-release; T-04 marks DISCOVERY → SPEC handoff) | operator | T-01 already done 2026-05-19 |
| P2-A — SPEC/PLAN/TASKS authorship (T-10..T-13) | SPEC + PLAN + TASKS | product-engineer | This file is T-11. T-10 = SPEC. T-12 = TASKS. T-13 = ADR-X1..X7 queued. |
| P2-B — Schema + validator (T-20..T-22) | IMPLEMENTATION (first wave, parallel with P2-C) | devops-engineer | Unlocks T-36 (sidecar-first) downstream |
| P2-C — Agent rewrites (T-30..T-39) | IMPLEMENTATION (first wave, parallel with P2-B) | ai-engineer | T-39 = D-20 enforcement |
| P2-D — Workflows + projection (T-40..T-43) | IMPLEMENTATION (second wave; depends on P2-B + P2-C) | devops-engineer + product-engineer | T-43 = constitution amendments (CLOSURE) |
| P3 — Validation gate (T-50..T-54) | post-CLOSURE / ARCHIVED | operator + project-auditor | 7-day window from release-close |

### Phase task lists (verbatim source: backlog §2)

#### P1 — operator quick wins (already + outstanding)

| T# | Task | Owner | Effort | Validates |
|---|---|---|---|---|
| T-01 | Uninstall plugins (`superpowers`, `skill-creator`, `code-simplifier`). Retain `frontend-design` per D-20. Verify `playwright` installed. *Status 2026-05-19: ✅ done.* | operator | 2 min | D-05, D-20 |
| T-02 | Start fresh Claude Code session (`/clear` or kill + restart). Confirm `using-superpowers` no longer auto-loaded at session start. | operator | 1 min | D-05 |
| T-03 | Run `npx ccusage@latest claude daily \| tail -3`. Note today's spend = pre-rewrite baseline for P-01..P-04. | operator | 1 min | baseline |
| T-04 | Open the release: `dadaia context activate dadaia-workspace`, dispatch product-engineer with SPEC-write request scoped to D-01..D-20. | operator | 5 min | kickoff |

#### P2-A — SPEC / PLAN / TASKS authorship (this release's curator work)

| T# | Task | Owner | Deps |
|---|---|---|---|
| T-10 | Write `specs/releases/token-cost-bigbang-v1/SPEC.md`. Scope: D-01..D-20. Constitution amendments (ADRs X1..X7). Status: Draft. | product-engineer | T-04 |
| T-11 | Write `PLAN.md` (this file): file-level change list — what edits per directory, what new files, what deletions. Status: Draft. | product-engineer | T-10 |
| T-12 | Write `TASKS.md` with task ids T-20..T-43 (P2-B/C/D) and T-50..T-54 (P3). Each task carries write-allowlist root + done criterion. Status: Draft → Aprovado after operator review. | product-engineer | T-11 |
| T-13 | Constitution amendments queued for CLOSURE: ADR-X1 (`AGENTS.md` canonical), ADR-X2 (skill scoping), ADR-X3 (agent size budget), ADR-X4 (default Sonnet + override), ADR-X5 (handoff-v1.1 schema), ADR-X6 (dispatch-to-researcher), ADR-X7 (plugin scope policy). | product-engineer | T-12 |

#### P2-B — Schema + validator (devops-engineer, ~2 h)

| T# | Task | Owner | Deps |
|---|---|---|---|
| T-20 | Update `dadaia_workspace/public/schemas/handoff-v1.schema.json` → `handoff-v1.1`. Required new fields: `findings[].detail_md`, `findings[].fix_recommendation`, `scope`, `metrics`. Make HTML `artifact.path` optional (was required). | devops-engineer | T-12 |
| T-21 | Update `dadaia reports validate` CLI to accept v1.1 + reject v1.0 silently-incomplete sidecars: missing `detail_md` → warning; missing `findings[]` → error. | devops-engineer | T-20 |
| T-22 | Add `dadaia reports lint <dir>` command. Walks `.dadaia/reports/`, flags orphaned HTML (no sidecar), oversized HTML (> 30 KB), missing schema fields. | devops-engineer | T-21 |

#### P2-C — Agent rewrites (ai-engineer, ~6–8 h)

| T# | Task | Owner | Deps |
|---|---|---|---|
| T-30 | **Model flip:** rewrite `model:` frontmatter on 7 agents (`project-manager`, `project-auditor`, `product-engineer`, `software-architect`, `ai-engineer`, `game-designer`, `game-tester`) → `claude-sonnet-4-6`. Confirm `researcher` = `claude-haiku-4-5`. Confirm `security-reviewer` scan-mode dispatch ref points to researcher (Haiku). | ai-engineer | T-12 |
| T-31 | **Description trim:** rewrite every agent's `description:` field ≤ 200 chars. Move long description content into the agent body if still relevant; delete otherwise. | ai-engineer | T-30 |
| T-32 | **Template extraction:** for every agent > 350 lines (`devops-engineer`, `product-engineer`, `software-architect`, `ai-engineer`, `qa-engineer`), extract report templates to `docs/agent-knowledge/<agent>/templates/*.md`. Agent body keeps a one-liner pointer. | ai-engineer | T-31 |
| T-33 | **Shared workspace-protocol:** create `.claude/rules/workspace-protocol.md` with SDD gate + context discovery + task lifecycle + report path. Remove from each agent body (factor out). Source path is `dadaia_workspace/public/rules/workspace-protocol.md`; projection lands at `.claude/rules/`. | ai-engineer | T-32 |
| T-34 | **Skill Tier-A/B split:** 22 Tier-B SKILL.md files migrated to `docs/agent-knowledge/<agent>/<topic>.md`. Update owning agent body with new reference. Delete `SKILL.md` files from `public/skills/`. | ai-engineer | T-33 |
| T-35 | **Legacy software-engineer sweep:** `grep -rl 'subagent_type.*software-engineer\b' dadaia_workspace/public/ .claude/` → rewrite each occurrence to `-python` or `-node`. Add lint rule in `dadaia public doctor` to reject the alias going forward. | ai-engineer | T-34 |
| T-36 | **Sidecar-first contract:** rewrite every agent prompt so emission default is JSON sidecar v1.1 only. HTML emission requires explicit `--with-report` flag in dispatch prompt OR `next_handoff.agent == "human"`. | ai-engineer | T-20, T-35 |
| T-37 | **Dispatch-to-researcher playbooks:** update `project-orchestration` SKILL.md with parallel-researcher fan-out pattern. Add standing instruction to `software-architect`, `project-auditor`, `code-reviewer`, `security-reviewer`, `devops-engineer`: "for evidence harvest, dispatch researcher; do not Read large file sets inline." | ai-engineer | T-36 |
| T-38 | **Operator-facing dispatch logic:** when operator asks for a report, agent asks "HTML or sidecar?" before emitting. If report > 30 KB, agent splits into multi-HTML with `index.html`. Codify in dispatcher (`project-manager`) playbook. | ai-engineer | T-37 |
| T-39 | **D-20 enforcement (frontend-design plugin scope):** (a) write `dadaia_workspace/public/rules/plugin-scope.md` declaring: "`frontend-design` plugin is restricted to `frontend-engineer` and `design-specialist`. All other agents must NOT invoke its skills/tools. Refusal pattern: `[PLUGIN SCOPE ERROR] frontend-design plugin is restricted to frontend-engineer + design-specialist. Dispatch the correct agent.`" Mirror the structure of `game-developer-scope.md`. (b) Add allow-list line to `frontend-engineer.md` and `design-specialist.md` body: "`Plugins authorised: frontend-design, playwright (this agent only — see plugin-scope rule).`" (c) Stage + install via `dadaia public stage && dadaia public install --target all`; verify with `dadaia public doctor`. (d) devops-engineer queues ADR-X7 for CLOSURE. | ai-engineer + devops-engineer | T-37 |

#### P2-D — Workflows + projection (devops-engineer + product-engineer, ~2 h)

| T# | Task | Owner | Deps |
|---|---|---|---|
| T-40 | Update all 7 workflow YAML files: each stage declares `consumes: [path-to-upstream-sidecar.json]` (not HTML). `audit-cycle`, `code-review-fan-out`, `cross-cutting-feature`, `spec-refinement` get dispatch-to-researcher injected at read-heavy stages. | devops-engineer | T-37 |
| T-41 | Re-architect `dadaia public install`: emit single `AGENTS.md` at workspace root + 1-line stub `CLAUDE.md` with `@AGENTS.md` include (or empty if CC fallback verified). Skills live in `.agents/skills/` with symlinks at `.claude/skills/`, `.codex/skills/`, `.opencode/skills/`. | devops-engineer | T-34 |
| T-42 | Run `dadaia public stage && dadaia public install --target all` in a clean workspace clone. Verify `dadaia public doctor` all green. | devops-engineer | T-41 |
| T-43 | Update `specs/constitution.md` (product-engineer hand, CLOSURE phase only) with ADRs X1..X7. Render/update memory atoms (`architecture.html`, `tech-stack.html`, `product/agent-orchestration.html`, `product/index.html` if catalog changed). | product-engineer | T-42, all P2-C tasks |

#### P3 — Validation gate (post-CLOSURE, 7-day window)

| T# | Task | Owner | Pass criterion |
|---|---|---|---|
| T-50 | Re-run `npx ccusage@latest claude daily \| tail -7`. Compare to T-03 baseline. | operator | Daily cost ≤ $25 average over 7-day window |
| T-51 | Re-run the per-session `cache_read / msg` script from audit §1. | operator | Cache-read per message ≤ 80 K (falsifies audit §8 P-02) |
| T-52 | Spot-check 5 dispatches: confirm researcher fan-out happening; sidecars carry `detail_md`; no HTML unless explicitly requested. | operator + project-auditor | 0 surprise HTML reports in window |
| T-53 | Run `dadaia reports lint .dadaia/reports/`. | operator | Clean lint — 0 orphans, 0 oversized |
| T-54 | Sub-agent dispatch ratio. | operator | ≥ 8 dispatches/session avg |

---

## 4. Dependency graph (DAG, verbatim from backlog §3)

```
T-01..T-04 (operator quick wins) ─┐
                                  ▼
                              T-10 SPEC.md ─► T-11 PLAN.md ─► T-12 TASKS.md ─► T-13 ADRs queued
                                                                   │
                            ┌───── parallel after T-12 ─────────────┤
                            ▼                                       ▼
                          T-20 schema v1.1                       T-30 model flip
                            │                                       │
                          T-21 validator                          T-31 desc trim
                            │                                       │
                          T-22 lint cli                           T-32 template extract
                                                                    │
                                                                  T-33 shared rule
                                                                    │
                                                                  T-34 skill split
                                                                    │
                                                                  T-35 legacy sweep
                                                                    │
                                                                  T-36 sidecar-first ◄── needs T-20
                                                                    │
                                                                  T-37 dispatch-to-researcher
                                                                    │
                                                                  T-38 operator-facing report logic
                                                                    │
                            ┌───────────────────────────────────────┤
                            ▼                                       ▼
                          T-40 workflows YAML                    T-41 projection re-architecture
                                            │                       │
                                            └──────► T-42 ◄─────────┘
                                                       │
                                                     T-43 constitution + memory (CLOSURE)
                                                       │
                                                       ▼
                                            P3 validation gate (T-50..T-54)
                                            (post-archive, 7-day window)
```

**Critical paths:**

- **Schema → sidecar:** T-20 → T-21 → T-22 (P2-B) gates T-36 (sidecar-first contract).
  Without v1.1 schema landed and validator updated, agent rewrites would emit sidecars
  the CLI cannot validate.
- **Agent rewrites linear:** T-30 → T-31 → T-32 → T-33 → T-34 → T-35 → T-36 → T-37 → T-38.
  Order matters — model flip first (cheapest sanity check), then trimming, then
  extraction, then shared rule, then skill catalogue surgery, then legacy sweep, then
  sidecar contract, then dispatch-to-researcher playbooks, then operator-facing logic.
- **Convergence:** T-40 (workflows) + T-41 (projection install) converge on T-42 (verify),
  then T-43 (CLOSURE constitution + memory). Memory writes only happen in CLOSURE
  phase per gate enforcement.

---

## 5. Effort estimate (verbatim from backlog §4)

| Phase | Owner | Tasks | Effort |
|---|---|---|---|
| P1 quick wins | operator | T-01..T-04 | ~10 min (T-01 done; T-02/T-03/T-04 outstanding) |
| P2-A SPEC/PLAN/TASKS | product-engineer | T-10..T-13 | ~3 h |
| P2-B schema + validator | devops-engineer | T-20..T-22 | ~2 h |
| P2-C agent rewrites | ai-engineer | T-30..T-39 | ~6–8 h |
| P2-D workflows + projection | devops-engineer + product-eng | T-40..T-43 | ~2 h |
| **P2 total (parallelizable B+C, then D)** | — | — | **~10–12 h serial** / **~6–8 h parallel** |
| P3 validation | operator | T-50..T-54 | ~30 min on day 7 |

**Tip on cost during the rewrite itself** (audit-aware): the big-bang IS a heavy SDD
cycle (product-engineer + ai-engineer + devops-engineer working through TASKS.md). If
executed BEFORE T-01..T-02 (already done) the rewrite itself would have burnt
~$50–80 in Opus rates. With T-01 done + Sonnet defaults pending, the lib-side rewrite
will run on a leaner session at ~$10–15.

---

## 6. Technical risks

Detailed in SPEC §6. Summary of PLAN-level mitigations:

1. **Big-bang cutover risk** — sidecar-only handoffs break a downstream agent that
   expected HTML. **PLAN mitigation:** T-36 rewrites all 20 agents in lockstep (no
   per-agent staging). T-22 lint flags orphans immediately. Doctor + validate run
   green in T-42.
2. **Skill Tier-B deletion order** — agent body must point at new doc path BEFORE
   `SKILL.md` is deleted. **PLAN mitigation:** T-34 task description fixes the order
   (update body first, then delete).
3. **`ai-engineer` SDD HARD STOP on its own files** — the rewriter touches the
   surface it owns. **PLAN mitigation:** verified in CLAUDE.md §8 that `ai-engineer`
   write_allowlist explicitly covers `public/{agents,skills,workflows,commands,rules,hooks}/**`.
   No further action needed at PLAN time.
4. **CC 2.1.x `AGENTS.md` fallback** — operator may run Claude Code version that does
   not honour `@AGENTS.md` include. **PLAN mitigation:** T-41 keeps `CLAUDE.md` as
   1-line stub (literal "see AGENTS.md") so content remains discoverable manually
   if the include fails silently. Easy revert path: re-emit full `CLAUDE.md`.

---

## 7. Validation plan

Three independent validation surfaces:

**7.1 — Per-task validation (during IMPLEMENTATION).** Each task in TASKS.md will
carry a `done criterion` line. ai-engineer / devops-engineer flip `[ ]` → `[-]` to
reserve, do the work, flip `[-]` → `[x]` with a conventional-commit referencing the
task id (per `dadaia-task-manager` skill protocol).

**7.2 — CLOSURE validation triples (in CLOSURE.md).** Each of the 8 backlog AC items
(SPEC §5) becomes a `{description, command, evidence}` triple per
`dadaia-release-closure` skill template. Evidence MUST be one of: commit SHA, stdout
snippet, or path to a report HTML under `.dadaia/reports/dadaia-workspace/`.

**7.3 — P3 7-day post-release validation (T-50..T-54).** Operator + project-auditor
run the 5 P3 tasks during the 7 days after the release archives. If P3 fails any of
the 5 pass-criteria, a follow-up release is filed (NOT a SPEC.md re-edit on this
archive).

---

## 8. Branch + merge strategy

Per backlog §5 risk-mitigation default + PM intake recommendation:

- **Branch:** `release/token-cost-bigbang-v1`, cut from `main` at `bd40e83`.
- **Merge:** standard PR into `main` once TASKS.md fully `[x]` DONE + CLOSURE.md
  Status: Aprovado.
- **Rollback:** `git revert <merge-commit>` + `dadaia public install --target all`
  restores prior state. Operator-side P1 plugin changes reversed via
  `/plugin install <name>` per plugin.

---

**Status:** Aprovado
