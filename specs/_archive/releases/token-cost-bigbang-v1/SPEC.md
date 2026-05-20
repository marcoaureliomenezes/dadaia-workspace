# Spec: Release — token-cost-bigbang-v1

> **Status:** Aprovado
> **Release ID:** token-cost-bigbang-v1
> **Owner:** product-engineer
> **Created:** 2026-05-20
> **Phase:** DISCOVERY
> **Branch:** `release/token-cost-bigbang-v1` (recommended cut from `main` at `bd40e83`,
> mirroring backlog §5 risk-mitigation default — single release branch = clean
> rollback via `git revert <merge-commit>` + `dadaia public install --target all`).
> **Predecessor (paused, not closed):** `codex-agent-orchestration-parity-v1` — SPEC Draft
> preserved at `specs/releases/codex-agent-orchestration-parity-v1/SPEC.md`; zero
> implementation on disk at pause point. Re-queued in `specs/backlog/candidates.md`
> `## Próxima release (queued)` with the pause note `paused 2026-05-20 — pre-empted by
> token-cost big-bang; resume after CLOSURE`.

---

## 0. Discovery inputs (canonical scope)

This SPEC is grounded in two binding audit artefacts. Both were read end-to-end in DISCOVERY.
Together they lock 20 decisions (D-01 .. D-20), 9 findings (F-01 .. F-09), 10 model-performance
impacts (P-01 .. P-10), and the 8-point acceptance checklist reproduced verbatim in §5 below.

| Path (absolute) | Role |
|---|---|
| `/home/marco/workspace/dadaia/.dadaia/reports/dadaia-workspace/audit/2026-05-19T2030Z-token-cost-audit.html` | Token-cost audit v2. §0 decisions log (D-01..D-06 locked after grill). §3 findings F-01..F-09. §4 cost decomposition. §5 Quick Wins / Structural / Strategic recommendations. §8 falsifiable predictions P-01..P-04. §10 model-performance impact P-01..P-10. ADRs X1..X4 listed in §0 callout. |
| `/home/marco/workspace/dadaia/.dadaia/reports/dadaia-workspace/audit/2026-05-19T2200Z-token-cost-backlog.html` | Big-bang execution plan. §0 north-star numbers. §1 D-01..D-20 (verbatim, locked). §2 three-phase execution (P1 / P2-A/B/C/D / P3). §3 DAG. §4 effort (~6–8 h parallel). §5 risk + rollback. §6 acceptance criteria (8-point). §7 explicit out-of-scope. ADR X-7 from D-20. |
| `/home/marco/workspace/dadaia/repos/dadaia-workspace/.dadaia/reports/dadaia-workspace/project-manager/2026-05-20T003804Z-audit-aware-intake.html` | PM intake. Maps backlog phases inside SDD gates. Confirms release-id, D-20 in-scope, branching recommendation. |

Operator follow-up (binding, verbatim from intake):

> "IS the hotfix considering the plan for fixes for issues registered in
> `.dadaia/reports/dadaia-workspace/audit?`"

Yes. The audit + backlog ARE the scope. This SPEC ratifies them into the SDD pipeline —
not re-derives scope.

---

## 1. Objective

Reduce per-invocation cost across the 20-agent topology and the 33-skill catalogue, AND
restore reasoning bandwidth lost to system-prompt bloat. Single big-bang release —
no backwards-compat, no staged rollout (no external consumers gate this lib yet).

**North-star (audit §0 + backlog §0):**

| Metric | Today | Target |
|---|---|---|
| Daily spend | ~$58 / day | ~$15–20 / day |
| System-prompt floor per turn | ~160 K tokens | ~80 K tokens |
| Daily-spend reduction (same workload) | — | **≈70 % cut** |
| Sonnet flip savings alone (D-02) | — | **~$700–900 / month** |
| Unread HTML reports eliminated (D-07) | — | ~78 % |
| Failed dispatches eliminated (D-06) | 113 / month | ~0 |
| `cache_read / msg` | ~159 K | ≤ 80 K (audit §8 P-02) |

---

## 2. Locked decisions (D-01 → D-20)

Verbatim from `2026-05-19T2200Z-token-cost-backlog.html` §1. Owner column + Phase column
preserved as in source. No paraphrase.

| # | Decision | Owner | Phase |
|---|---|---|---|
| D-01 | Keep `.codex/` + `.opencode/`. Unify skills via shared `.agents/skills/` (symlinks per runtime). `AGENTS.md` canonical; `CLAUDE.md` = 1-line stub. | devops + product-eng | P2 |
| D-02 | 7 Opus agents → Sonnet 4.6 default. `DADAIA_MODEL_OVERRIDE=opus` escalation per-dispatch. | ai-engineer | P1 |
| D-03 | Skill split: 11 Tier-A universal stay catalogued; 22 Tier-B demoted to `docs/agent-knowledge/<agent>/<topic>.md`, agent reads on-demand. | ai-engineer | P2 |
| D-04 | Uniform agent pattern: templates extracted, shared `workspace-protocol.md` rule, `description:` ≤ 200 chars. | ai-engineer | P2 |
| D-05 | Uninstall `superpowers`, `skill-creator`, `code-simplifier`. **Retain `frontend-design`** (scoped — see D-20). Keep `playwright`. *Status 2026-05-19: 3/3 uninstalls done.* | operator | P1 |
| D-06 | Sweep legacy `subagent_type: software-engineer` → python/node per call site. | ai-engineer | P2 |
| D-07 | Sidecar-first emission contract. HTML only when operator asks OR `next_handoff.agent == "human"`. | ai-engineer + product-eng | P2 |
| D-08 | When operator asks for a report → ask "HTML needed?". Extensive reports break into multiple HTMLs with `index.html`. | ai-engineer (dispatcher logic) | P2 |
| D-09 | Audit current workflows for agent-to-agent comm: 8 workflows pass HTML+sidecar today. Migrate to sidecar-only. | ai-engineer (workflow YAML) | P2 |
| D-10 | Enrich `handoff-v1` → `handoff-v1.1`: add `detail_md`, `fix_recommendation`, `scope`, `metrics`. | product-eng (schema) + devops (validator) | P2 |
| D-11 | `researcher` → Haiku 4.5. Zero risk (new agent, 0 dispatches). | ai-engineer | P1 |
| D-12 | Multi-mode pattern **dropped** — architecturally infeasible (CC fixes `model:` at agent registration). | — | n/a |
| D-13 | `code-reviewer` stays Sonnet 4.6 (new agent, operator preference). | ai-engineer | P1 |
| D-14 | `security-reviewer` scan → Haiku. Triage stays Sonnet. Dispatcher must declare scan patterns explicitly. | ai-engineer + product-eng | P2 |
| D-15 | **Big-bang schema migration (Option A)**. Ship `handoff-v1.1` + rewrite all 20 agents + update all 7 workflows in one release. | ai-engineer + product-eng + devops | P2 |
| D-16 | Dispatch-to-researcher is the canonical pattern for read-heavy phases. Document in `project-orchestration` skill. | ai-engineer | P2 |
| D-17 | Workflow YAML schema gains `consumes: [sidecar-path]` (not HTML). Update all 7 workflow files. | ai-engineer | P2 |
| D-18 | Keep "0-dispatch new agents" (researcher, code-reviewer, ai-engineer, design-specialist, data-engineer, data-analyst). They are intentionally new. | — | n/a |
| D-19 | Document parallel-researcher fan-out in `project-orchestration`. Playbook: "for evidence-heavy work, dispatch N researchers in parallel, synthesise from sidecars." | ai-engineer | P2 |
| D-20 | **Plugin scope policy — `frontend-design` restricted to `frontend-engineer` and `design-specialist` only.** All other agents must NOT invoke skills/tools from this plugin. Enforcement: (a) ai-engineer adds an explicit allow-list note to `frontend-engineer.md` and `design-specialist.md` frontmatter / body; (b) ai-engineer adds a `[PLUGIN SCOPE ERROR]` refusal pattern (mirroring `game-developer-scope.md`) to a new rule `.claude/rules/plugin-scope.md` listing the forbidden agents; (c) devops-engineer queues an ADR in CLOSURE (X-7) recording the policy + rationale. Rationale: `frontend-design` plugin pollutes context for non-UI agents and risks design-pattern leakage outside the UI/UX surface. | ai-engineer + devops-engineer | P2 |

---

## 3. Deltas summary

### 3.1 Product deltas

- **Sidecar-first reports.** Default emission is JSON sidecar (`handoff-v1.1`). HTML
  only emitted on explicit operator request OR when `next_handoff.agent == "human"`.
  Extensive reports break into multi-HTML with an `index.html` entry. (D-07, D-08)
- **Dispatch-to-researcher canonical pattern.** Read-heavy phases delegate to
  `researcher` (Haiku 4.5) with tightly-scoped questions. Parallel fan-out playbook
  documented in `project-orchestration` SKILL.md. (D-16, D-19)
- **Plugin scope policy.** `frontend-design` plugin restricted to `frontend-engineer`
  + `design-specialist`. New rule `plugin-scope.md` mirrors `game-developer-scope.md`
  with a `[PLUGIN SCOPE ERROR]` refusal pattern. (D-20)
- **Failed-dispatch elimination.** Legacy `subagent_type: software-engineer` rewritten
  to `-python` or `-node` per call site; lint rule prevents regression. (D-06)

### 3.2 Architecture deltas

- **Workspace topology consolidation.** Keep `.codex/` + `.opencode/` runtimes; unify
  skills via shared `.agents/skills/` (symlinks per runtime). `AGENTS.md` becomes
  canonical workspace-root instruction; `CLAUDE.md` becomes 1-line stub
  (`@AGENTS.md` or literal "see AGENTS.md") pending CC 2.1.x fallback verification.
  (D-01, ADR-X1)
- **Skill catalogue Tier-A/B split.** 11 universal Tier-A skills stay catalogued via
  `public/skills/`. 22 Tier-B skills demote to `docs/agent-knowledge/<agent>/<topic>.md`
  (read on-demand by the owning agent). Catalogue shrinks 47 → 11 entries. (D-03,
  ADR-X2)
- **Agent body uniformity.** Every agent > 350 lines extracts report templates to
  `docs/agent-knowledge/<agent>/templates/*.md`. Shared workspace protocol factored
  into a new `.claude/rules/workspace-protocol.md` rule. Agent `description:` ≤ 200
  chars. (D-04, ADR-X3)
- **Schema upgrade `handoff-v1 → handoff-v1.1`.** Adds required `findings[].detail_md`,
  `findings[].fix_recommendation`, `scope`, `metrics`. Makes `artifact.path` (HTML)
  optional (was required). (D-10, D-15, ADR-X5)
- **Workflow YAML `consumes: [sidecar-path]`.** All 7 workflows updated to declare
  sidecar (not HTML) as the agent-to-agent contract. (D-09, D-17)

### 3.3 Tech-stack deltas

- **Default model Sonnet 4.6.** All 7 currently-Opus agents (`project-manager`,
  `project-auditor`, `product-engineer`, `software-architect`, `ai-engineer`,
  `game-designer`, `game-tester`) flip to `claude-sonnet-4-6` as default. Escalation
  via `DADAIA_MODEL_OVERRIDE=opus` per-dispatch for hard cases (greenfield arch,
  multi-spec drift, memory atomicity writes). (D-02, ADR-X4)
- **`researcher` → Haiku 4.5.** Zero-dispatch agent, lowest-risk to flip. (D-11)
- **`security-reviewer` scan → Haiku.** Triage stays Sonnet. Dispatcher declares
  scan patterns explicitly. (D-14)
- **`code-reviewer` stays Sonnet 4.6.** Operator preference (new agent). (D-13)
- **Plugin set.** Removed: `superpowers`, `skill-creator`, `code-simplifier` (already
  uninstalled per D-05 status note 2026-05-19). Retained: `playwright`,
  `frontend-design` (scoped per D-20). (D-05)

### 3.4 Security / operations deltas

- **Plugin scope rule** (`public/rules/plugin-scope.md`, ADR-X7) declares the allow-list
  for `frontend-design`. Non-authorised agents must respond with `[PLUGIN SCOPE ERROR]`.
- **CLI hardening.** `dadaia reports validate` accepts v1.1 + rejects v1.0 silently-
  incomplete sidecars (warning for missing `detail_md`, error for missing `findings[]`).
  New command `dadaia reports lint <dir>` flags orphaned HTMLs, oversized HTMLs
  (> 30 KB), missing fields.
- **`dadaia public doctor` gains a lint rule** rejecting any future `subagent_type:
  software-engineer` reference. (D-06)

### 3.5 Memory files affected at CLOSURE

Memory writes are gate-locked to CLOSURE phase. The following atoms WILL be updated
when this release reaches CLOSURE — listed here for traceability only; NOT touched
in any earlier phase:

- `specs/memory/architecture.html` — agent-topology layer gains new tier table
  (Sonnet default + Haiku researcher + Opus override flag). Skill catalogue rule
  block (Tier-A catalogued, Tier-B on-demand) added.
- `specs/memory/tech-stack.html` — model assignments updated (7 Opus → Sonnet,
  researcher → Haiku, security-reviewer scan → Haiku). Plugin inventory updated
  (removed: superpowers, skill-creator, code-simplifier; retained: playwright,
  frontend-design with scope note).
- `specs/memory/product/agent-orchestration.html` — sidecar-first contract,
  dispatch-to-researcher pattern, plugin scope policy.
- `specs/memory/product/index.html` — catalog updated if any new feature surface
  emerges; otherwise unchanged.
- `specs/constitution.md` — amended with ADRs X1..X7 (see §4 below).

Forbidden sections (`Changelog`, `History`, `Histórico`, `Versions`) MUST remain
absent in all memory HTMLs. History lives in this release's CLOSURE.md.

---

## 4. ADRs queued for CLOSURE phase

The seven ADRs below will be written during CLOSURE (NOT in this DISCOVERY phase, NOT
in PLAN or TASKS). They amend `specs/constitution.md` atomically with the release.

| ADR | Title | Source decision |
|---|---|---|
| ADR-X1 | Provider-agnostic instruction files (`AGENTS.md` canonical; `CLAUDE.md` 1-line stub or absent) | D-01 |
| ADR-X2 | Skill scoping policy (Tier-A universal stays catalogued; Tier-B per-agent docs) | D-03 |
| ADR-X3 | Agent size budget (`description:` ≤ 200 chars; body ≤ 300 lines; templates externalised) | D-04 |
| ADR-X4 | Default model Sonnet 4.6; Opus reserved for `DADAIA_MODEL_OVERRIDE=opus` dispatches | D-02 |
| ADR-X5 | `handoff-v1.1` schema (`detail_md` / `fix_recommendation` / `scope` / `metrics`) | D-10, D-15 |
| ADR-X6 | Dispatch-to-researcher as canonical pattern for read-heavy phases | D-16, D-19 |
| ADR-X7 | Plugin scope policy (`frontend-design` restricted to frontend-engineer + design-specialist) | D-20 |

---

## 5. Acceptance criteria (verbatim from backlog §6 — 8-point checklist)

Each point is machine-verifiable and has evidence registered in CLOSURE.md. No paraphrase.

1. `specs/releases/token-cost-bigbang-v1/{SPEC,PLAN,TASKS,CLOSURE}.md` all show
   `**Status:** Aprovado`.
2. Constitution amended with ADRs X1–X6. *(SPEC adds X7 — see §4 above; AC enforces
   X1–X6 from backlog source. X7 enforcement is delegated to task T-39 and reviewed
   in CLOSURE.)*
3. `dadaia public doctor` all green after `dadaia public install --target all`.
4. `dadaia reports validate` accepts v1.1 sidecars; rejects v1.0 with missing fields.
5. `dadaia reports lint .dadaia/reports/` clean (no orphans, no oversize).
6. 7-day post-release ccusage shows average daily cost ≤ $25.
7. Re-run of the per-session script in audit §1 shows `cache_read / msg ≤ 80 K`.
8. 5 spot-checked dispatches: sidecar-only emission, dispatch-to-researcher visible,
   no surprise HTML.

---

## 6. Risk + rollback (summary from backlog §5)

| Risk | Likelihood | Mitigation |
|---|---|---|
| Claude Code 2.1.x does NOT fall back to `AGENTS.md` when `CLAUDE.md` absent | Medium | Keep `CLAUDE.md` as 1-line stub (`@AGENTS.md` include or literal "see AGENTS.md") — easy revert: re-emit full `CLAUDE.md` (T-41) |
| Sonnet 4.6 produces lower-quality `product-engineer` synthesis on hard releases | Low | Escalation flag `DADAIA_MODEL_OVERRIDE=opus` ships day 1; operator flips per-dispatch (D-02) |
| Haiku `researcher` misses context on complex codebases | Medium | Researcher prompts tightly scoped; `project-orchestration` playbook documents convention; caller escalates via `DADAIA_MODEL_OVERRIDE=sonnet` on insufficient context (D-11, D-16) |
| Sidecar-only handoffs break a downstream agent expecting HTML | High during cutover | Big-bang migration in lockstep (T-36 rewrites all 20 agents simultaneously); `dadaia reports lint` flags orphans (D-15, T-22) |
| Skill Tier-B move breaks an agent referencing the now-deleted `SKILL.md` | Medium | Update owning agent body BEFORE deleting the `SKILL.md` (T-34 dependency order) |
| Rewriter (`ai-engineer`) hits SDD HARD STOP on its own files | Low | `ai-engineer` write_allowlist explicitly includes `public/{agents,skills,workflows,commands,rules,hooks}/**` (verified CLAUDE.md §8) |

**Full rollback path.** The entire lib-side rewrite is one release branch. Standard
`git revert <merge-commit>` + `dadaia public install --target all` restores prior
state. Operator-side P1 changes are reversed by `/plugin install <name>` per plugin.

---

## 7. Non-goals (out of scope — explicit deferrals from backlog §7)

These items are recognised but explicitly OUT of scope for token-cost-bigbang-v1. They
re-surface as backlog candidates in CLOSURE if still relevant:

- **SDD lightweight mode for solo work** (audit §5 ST-02). Deferred — first see how
  this big-bang already simplifies the surface.
- **Auto-memory pruning policy** (audit §10 P-10). Cap at 10 memory files. Implement
  after token-cost-bigbang-v1 lands and the new flow's memory pattern is observed.
- **TaskCreate/TaskUpdate churn cap** (audit §10 P-09). Operator habit: cap 5
  concurrent tasks per session. Not enforced by tooling yet.
- **Session-length policy** (audit §10 P-07, recommendation QW-06). Operator habit:
  `/clear` on phase boundaries. Could be enforced via hook later.
- **ccusage in `dadaia panel`** (audit §5 ST-03). Live cost visibility. Nice-to-have,
  not blocking.
- **OpenCode parity / Codex parity rework.** The paused predecessor
  `codex-agent-orchestration-parity-v1` resumes after this release closes; D-01 here
  is a topology consolidation (`.codex/` + `.opencode/` kept) — full Codex parity
  rework remains the predecessor's scope.

---

## 8. Dependencies and risks

**Dependencies:**

- `agents-r3-v1` is CLOSED + ARCHIVED (the 20-agent topology that this release flips
  to Sonnet defaults is the artefact of `agents-r3-v1`).
- T-01 (operator quick-win plugin uninstalls) is already DONE per backlog footnote
  (`Status 2026-05-19: 3/3 uninstalls done`). Confirmed in PM intake.
- Branch `release/token-cost-bigbang-v1` to be cut from `main` at `bd40e83`
  (operator/devops action — backlog §5 risk-mitigation default).
- `ai-engineer` write_allowlist on `public/{agents,skills,workflows,commands,rules,hooks}/**`
  is the gating contract; verified in CLAUDE.md §8.

**Risks tracked in §6 above.** Cross-cutting risk that the rewrite itself runs on
Opus and burns ~$50–80 in lib-side dispatches: mitigated by backlog §4 tip — execute
P1 first (already done), restart session, THEN dispatch ai-engineer + devops-engineer
for IMPLEMENTATION. Rewrite then runs on Sonnet, costing ~$10–15.

---

## 9. Open questions (DISCOVERY phase — resolved via binding inputs)

All grill-me-style ambiguity is already answered by the binding inputs. The three items
PM enumerated in the dispatch (GQ-A/B/C) are resolved as follows:

- **GQ-A — Release-id `token-cost-bigbang-v1`.** Confirmed by operator (PM intake §OQ-A
  selection). Matches canonical backlog HTML title; cleaner self-documentation than
  the date-suffixed alternative `r-cost-2026-05`. No re-grill.
- **GQ-B — SDD-gate ordering honored.** PM call: yes. Backlog phase taxonomy
  (P1 / P2-A..D / P3) is *content* milestones nested INSIDE SDD gates
  (DISCOVERY → SPEC → PLAN → TASKS → IMPLEMENTATION → CLOSURE → ARCHIVED). No
  big-bang implementation outside TASKS. Each artefact still requires
  `**Status:** Aprovado` to unlock the next phase.
- **GQ-C — D-20 (frontend-design plugin scope + ADR-X7) in-scope.** PM call: yes.
  Backlog §1 D-20 + §2 P2-C T-39 are fully specified (rule body, allow-list lines,
  install propagation, ADR-X7 queued for CLOSURE). Excluding D-20 would orphan T-39
  and break the §3 DAG dependency (T-39 → T-37).

No further open questions before SPEC review. Operator may flip
`**Status:** Em revisão → Aprovado` once content is reviewed.

---

**Status:** Aprovado
