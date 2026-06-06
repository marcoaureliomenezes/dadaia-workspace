# SPEC: v0.2.0 — "Agentic Development Lifecycle" (program / umbrella)

**Status:** Em revisão
**Release ID:** v0.2.0
**Owner:** product-engineer
**Created:** 2026-06-06
**Type:** Program SPEC — the umbrella over internal milestones v0.1.6 → v0.1.9, integrated and deployed ONCE as v0.2.0.

> **DESIGN OF RECORD (cite, do not duplicate):** consolidated roadmap `…/project-manager/2026-06-06T045436Z-consolidated-roadmap.md`; state-model proposal `…/2026-06-06T043437Z…`; agent-surface grill `…/2026-06-06T035141Z…`; architect validation `…/software-architect/2026-06-06T060000Z…`; backlog `specs/backlog/v0.2.0-agentic-lifecycle.md`.

---

## 1. Why this release exists

v0.2.0 is a **workspace-shape change**, not a feature batch. It fixes the root dysfunction the operator hit live: the SDD lock/session machinery soft-deadlocks legitimate work and accreted a 188-record graveyard, while the agent surface has grown into slop (15 agents, 22 skills, 7 stale workflows) whose roles are not tied to the development lifecycle. These are **one problem**: the lock guards the wrong things because the lifecycle phases and the agents that own them were never defined together.

This release defines the **canonical agentic development lifecycle**, the **lock model that enforces it without deadlocking**, the **coordinator + sub-agent architecture** that makes concurrency safe, and the **reduced, lifecycle-tailored agent/skill/workflow surface** — as one coherent evolution.

## 2. Deploy model (binding)

- The work is delivered as **four sequenced internal milestones**: **v0.1.6 → v0.1.7 → v0.1.8 → v0.1.9**. Each is fully implemented, tested, gate-reviewed (qa→commit, security→push, code-review→PR), and **validated by the operator in THIS instantiated workspace** before the next milestone begins.
- **None of v0.1.6–v0.1.9 is deployed** (no PyPI publish, no tag). They are workspace-internal checkpoints on a single `feature/0.2.0` branch.
- **Only v0.2.0 deploys** — once, after all milestones are integrated, the full lifecycle is dogfooded end-to-end on this instance, **drift to the instantiated workspace is eliminated** (`dadaia public install --target all` + `dadaia public doctor` exit 0 on all runtimes; `dadaia specs doctor` exit 0), and the ship-trio approves.
- v0.1.5's already-merged work (backlog-ownership, install/doctor fixes, panel) is on `main` and forms the 0.2.0 base; the parked v0.1.5 PyPI publish was **cancelled** (deploy only 0.2.0).

## 3. The connecting thesis — one matrix governs lock, agents, and lifecycle

Two activity classes partition every action; the partition is simultaneously the lock model, the agent-coordination model, and the lifecycle:

| Phase | Owner | Writes to | Class | Lease |
|---|---|---|---|---|
| Backlog definition · Bug filing | project-manager / any | `specs/backlog/**` · `specs/bugs/**` | **ADDITIVE** | none — **concurrent** |
| Research · Audit | researcher-fn / project-auditor | `.dadaia/reports/**` | **ADDITIVE** | none — **concurrent** |
| Release definition · Implementation · Review-closure | product-engineer · software-engineer · product-engineer | `specs/releases/<id>/**` · `repos/<ctx>/` prod+tests · `specs/memory/**` | **MUTATING** | **ONE lease, serialized** |
| Review gates (qa→commit · security→push · code-review→PR) | qa · security-reviewer · code-reviewer | `.dadaia/handoff/**` · `.dadaia/reports/**` | **ADDITIVE** evidence; **gates** transitions | none — they vote |

**One sentence:** exactly one MUTATING actor per context, serialized by one lease the coordinator holds; every ADDITIVE actor runs concurrently and never touches the lease.

## 4. The coordinator + sub-agent architecture (how concurrency is safe without deadlock)

- **project-manager is the lease coordinator.** When a release enters its MUTATING span it acquires **one** lease (keyed to PM's coordinator session) and holds it through definition → implementation → review-closure.
- **product-engineer and software-engineer run as PM sub-agents under that single lease** — they never independently bind a session, so there is **no session handoff and no second lock** (architect resolution A-2, ratified). The "writer role" moves between sub-agents by PM dispatching the next one; the lease never changes hands.
- **Reviewers (qa, security, code-reviewer), researcher, and project-auditor are ADDITIVE** — they write evidence/reports, vote on gates, and run **concurrently** with each other and with backlog work. They never contend for the lease.
- Result: the only thing serialized is a single release's mutation. Backlog/audit/research are parallel by construction. **A deadlock between sessions in different lifecycle phases is structurally impossible** because only one class takes a lock and that lock auto-heals (see v0.1.6).

## 5. Resolved decisions (operator-delegated; review and override if desired)

| # | Decision | Resolution |
|---|---|---|
| TTL/heartbeat (OD-2) | idle-but-alive false-reclaim window | **TTL = 1800s (30 min); heartbeat renews on every PreToolUse (any tool).** No background thread (cross-platform). An actively-working coordinator renews constantly; only a >30-min fully-idle holder is reclaimable. |
| Workflows (OD-1) | redesign vs delete | **Delete all 7 stale workflows.** Orchestration is the coordinator's dispatch logic, not scripted files. Author NEW workflows ONLY for deterministic, non-judgment sequences where scripting beats dispatch — provisionally: `release-ship` (the deploy gate sequence) and `audit-fanout`. Net surface shrinks; PM personas carry the orchestration. |
| Memory tree (OD-3) | `product/` grouping | **`product/{agents,sdd,panel,platform,distribution,philosophy}/`** + `index.md` with wikilinks. project-auditor refines exact placement during v0.1.9. |
| devops-engineer (OD-4) | stub vs remove | **Remove from `public/agents/`; ship as a plugin.** Fresh `dadaia init` emits nothing for it; `plugin-scope` rule references the plugin. |
| QA memory (OD-5) | absorb `test-suite-architecture.md` | **New `specs/memory/quality-assurance.md` absorbs it; old file `git mv` → `specs/_archive/legacy-memory/<ts>/`.** Never two QA sources. |
| Gate vs new memory atom | can PE create `quality-assurance.md`? | The v0.1.6 gate classifies `specs/memory/**` writes by **author + phase**: product-engineer may write memory during **DEFINITION and CLOSURE** (not only CLOSURE); other agents never. So creating the QA canon in v0.1.7 is allowed for PE. Encoded in the v0.1.6 gate. |
| Concurrency model | explicit | backlog/bug/research/audit = ADDITIVE → **concurrent sessions allowed**; definition/impl/review-closure = MUTATING → **one lease**. §3 matrix is binding law (encoded in v0.1.7 constitution). |

## 6. The milestone sequence (each fully validated in-workspace before the next)

### v0.1.6 — State model (foundation)
**Scope:** one cross-platform JSON TTL-lease per context (`.dadaia/states/ctx_locks/<ctx>.lock.json`, heartbeat+TTL, **no PID/os.kill/proc**); acquire via **`O_EXCL` CAS** (MUST-NOT-SHIP red line) as a side effect of the first MUTATING write; fail-safe PreToolUse gate (block ONLY on a live-lease conflict, always print a working `dadaia lock steal <ctx>`); GC inline + on `context show|list` + `doctor --fix` that **actually deletes**; full cut of Lock-3 + session-file writer + `semaphore.py`; **keep fcntl Lock-1/Lock-2** (git ops); gate `sdd-spec-gate.sh` 1050→~150 lines (RULE E dies, RULE C→PostToolUse WARN, RULE D→compiled `agents.index.json`); injectable clock + pid-free liveness seams.
**Acceptance:** the soft-deadlock is unreproducible; no input state leaves an agent without a working unblock (property test); 0 graveyard accumulation; cross-harness honesty (real block on Claude Code + trusted Codex; advisory on opencode).
**In-workspace validation:** operator drives a mutate→edit→commit cycle and a forced stale-lease + reclaim; doctor exit 0.

### v0.1.7 — Constitution v2 + lifecycle law + memory canon (THE FREEZE)
**Scope:** encode §3 matrix, §4 coordinator/sub-agent architecture, the anti-slop law, the review-gate sequence, and the memory canon (`architecture.md`, `product/**` tree, `tech-stack.md`, **`quality-assurance.md`**) as binding constitution. Create `quality-assurance.md` (absorbs `test-suite-architecture.md`).
**Acceptance:** the lifecycle, roster, lock contract, and gate sequence are derivable from the constitution without operator explanation; no agent/skill/workflow exists without a phase it owns or gates.
**In-workspace validation:** operator reads the constitution and confirms it matches the lived workflow; `dadaia specs doctor` passes memory-canon checks.

### v0.1.8 — Coordinator + sub-agent architecture + roster 15→9 + tailoring
**Scope:** implement §4 — deepen/tailor the coordinators (**project-manager** → `claude-opus-4-8`, grill-mandatory, lease-coordinator, dispatch logic; **product-engineer** backlog-consumer + memory guardian; **project-auditor** peer + scoring + constitution/memory anchor; **ai-engineer** surface owner). Reduce roster to 9 core: one `software-engineer` (absorbs python/node/backend); frontend-engineer + design-specialist (+5 skills) → plugin; devops-engineer → plugin; researcher out of core. **Every persona declares its activity class + lease relationship + how it is dispatched** (§3/§4).
**Acceptance:** each surviving agent owns or gates a lifecycle phase; the coordinators run the full lifecycle from their personas without operator narration; no persona references a deleted agent/skill.
**In-workspace validation:** operator runs a small end-to-end demand through PM (grill → backlog → definition → implementation under one lease → review gates) and confirms no lock friction.

### v0.1.9 — Skills cleanup + workflow redesign + memory tree + surface cleanup
**Scope:** skills 22→17 (frontend/design 5 → plugin); **delete the 7 stale workflows**, author the redesigned minimal set (§5 OD-1); restructure `product/` into the tree (§5 OD-3); manifest + `dadaia public doctor` reconcile across all runtimes.
**Acceptance:** no orphan skill/workflow/agent on any runtime; `product/` is navigable by a human and an agent; doctor exit 0.
**In-workspace validation:** operator inspects the reduced surface + the memory tree; fresh-init parity check.

### v0.2.0 — Integration, in-workspace validation, drift-elimination, single deploy
**Scope:** integrate all milestones on `feature/0.2.0`; bump `pyproject` → `0.2.0`; **dogfood the entire lifecycle end-to-end on this instance**; **eliminate drift** (`dadaia public install --target all` + `dadaia public doctor` exit 0 on `.claude`/`.codex`/`.agents`/`.opencode`); ship-trio (qa+security+code-review) APPROVE; then the **single deploy** (merge → release-gate approval → PyPI + tag v0.2.0).
**Acceptance:** the operator can run the whole workflow on the live instance with zero lock friction and zero drift; CLOSURE memory updated; v0.2.0 published.

## 7. Per-milestone gate (in-workspace, no deploy)

Each milestone obeys the v0.1.7 gate sequence locally: all tests run → **qa-engineer approves → commit**; **security-reviewer approves → push** (to `feature/0.2.0`, not main); **code-reviewer approves → PR/merge into the milestone integration**. Evidence in `.dadaia/handoff/` + `.dadaia/reports/` (no `evidence/` subtree — architect A-1). The operator gives the final in-workspace sign-off per milestone before the next opens.

## 8. Non-goals

- No PyPI publish before v0.2.0. - No new agents/skills beyond the reduced set. - No memory-engine rewrite (catalog.json + atoms stay; this is craft + lock, not engine). - frontend/design/devops capability is preserved **as plugins**, not deleted from the world.

## 9. Open items for operator review (flagged, not blocking)

- Milestone version labels 0.1.6–0.1.9 are **internal checkpoints**, not published versions; `pyproject` stays at the base until the v0.2.0 bump. Confirm this is the intended meaning of "break it on 0.1.6, 0.1.7…".
- TTL=1800s/renew-on-tool-use (§5) — confirm the idle window is acceptable for your working style.
- The redesigned workflow set (§5 OD-1: `release-ship`, `audit-fanout`) — confirm scope or name others.
- `product/` tree groups (§5 OD-3) — confirm or re-cut.

---

**Detailed PLAN.md (sequenced approach + module map per milestone) and TASKS.md (all tasks grouped by milestone, dependency-ordered, every task `[ ]` OPEN) follow as siblings. This umbrella SPEC is the contract the operator reviews first.**
