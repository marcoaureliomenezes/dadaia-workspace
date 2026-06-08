# Dadaia-Workspace Lifecycle Review — v0.1.5 → v0.2.0

- **Type:** project-auditor review (channel 3 — audit report, committed to `specs/audits/`)
- **Produced:** 2026-06-06T21:37:31Z
- **Scope:** the whole agentic-lifecycle redesign across releases v0.1.5, v0.1.5/rc-1, v0.1.5/rc-2, v0.1.6, v0.1.7, v0.1.8, v0.1.9, v0.2.0/integration, measured against the operator-confirmed canonical model (grill 2026-06-06).
- **Note on location:** this file lives at `specs/audits/<ts>/` per the operator's channel-3 ruling. The ratified constitution does **not yet** authorize this path (it says `.dadaia/reports/` only). That gap is **Finding D2** below; this report dogfoods the intended location.

---

## 0. Confirmed canonical model (the measuring stick)

Locked with the operator via `dadaia-grill-me` on 2026-06-06:

**Report / communication channels — exactly three, never mixed:**
1. **User-requested reports** → `.dadaia/reports/`, **HTML**, served on the dadaia-panel. Human consumption. Not necessarily tied to a spec context.
2. **Agent↔agent communication** → `.dadaia/handoff/`, **JSON** handoffs only. **No HTML reports for agent-to-agent comms.**
3. **project-auditor audits** → `specs/audits/<ts>/`, **Markdown**, committed inside the Spec Context's specs (you can only audit a project that has specs; the result is a durable spec artifact that PM converts into a patch release; archived to `specs/audits/_archive/`).

**Roster:** 9 core agents incl. **ai-engineer**; **project-manager** is sole writer of `specs/backlog/**`.

**Lifecycle (operator's 5-phase grouping):** backlog-definition · release-definition · implementation/review · audit · closure. (The constitution expresses these as 8 finer phases — a superset, not a contradiction.)

**Dispatcher purity:** ONLY `project-manager` and `project-auditor` may dispatch sub-agents. All others are workers; workers never talk agent-to-agent.

**Concurrency by phase (universal across runtimes — claude/codex/opencode):**
- **Parallel sessions allowed:** backlog-definition, audit, research/user-report-generation (additive, race-free). Parallel-produced markdown (backlog, audit) **must be collision-named** (session-id / timestamp).
- **Exactly ONE session:** release-definition, implementation, review (race risk). A genuinely-concurrent second session must not mutate. Mechanism = JSON state, deadlock-safe, **never fail-dead / never force a manual rebind**.

**Spec-review sequence (release-definition):** `qa-engineer` mandatory FIRST + `software-architect` optional IN PARALLEL → then `software-engineer` LAST confirms PLAN/TASKS are implementable. PM-mediated throughout.

**Implementation gates:** `qa-engineer` → commit · `security-reviewer` → push · `code-reviewer` → PR. PM-coordinated checkpoints (not mechanical shell blocks).

---

## 1. Verdict

**Substantially conformant, not shipped, with one architectural correction owed.**

The v0.1.5→v0.2.0 arc delivered the intended model with high fidelity: the 9-agent roster, PM-coordinator + sub-agent topology, single-lease concurrency, anti-slop law, and memory canon are all real and internally consistent. **Three things are not yet right:** (1) the just-shipped freeze fix relaxed the exactly-one-mutating-session invariant and must be corrected to the nuanced design; (2) the **3-channel report model is not encoded** — the constitution mandates `.dadaia/reports/` only and `specs/audits/` exists nowhere; (3) the entire v0.2.0 program is implemented + ship-trio-approved but **un-deployed and un-closed** (and v0.1.5 is likewise held). Plus four smaller drifts (dispatcher-purity-as-law, spec-review-sequence, collision-naming, stale semaphore docs).

---

## 2. Per-release review (what each delivered + status)

| Release | Delivered | Status |
|---|---|---|
| **v0.1.5** (flat) | Governance engine: `dadaia-release-definition` skill, `release-governance` rule, alpha/rc nested model (5 ADRs), pre-push CI gate, ACTIVE.md schema v2 (`segment:`), segment scaffolder + gate path-resolution. | **Aprovado**, all 20 tasks `[x]`; **deploy deferred** behind two blockers. |
| **v0.1.5/rc-1** | Closed deploy-blockers: runtime→session ptr (no relaunch), first per-context **semaphore** (`.semaphore.json`), backlog-ownership hard gate (D5), persona specialization (R3), PM→opus. | **Aprovado**; T-SHIP-05 `[-]` — **deploy HELD**. Logged drift `semaphore-no-liveness-reclaim`. |
| **v0.1.5/rc-2** | Hash-compare install + projected-drift doctor; semaphore PID-liveness reclaim (SEM-1); panel Reports-tab fix (RPT-1). | **Aprovado**; T-SHIP-05 `[-]` — **deploy HELD**. rc-2 supersedes rc-1 for closure; one v0.1.5 tag covers both. |
| **v0.1.6** | The lock redesign: **single JSON TTL-lease** `ctx_locks/<ctx>.lock.json`, O_EXCL CAS, no-PID liveness, gate ~1050→≤175 lines; retires the semaphore + impl-lock + session-writer (4 stores → 1). | **Em revisão**, 11/11 tasks `[x]`, **no CLOSURE.md**. |
| **v0.1.7** | THE FREEZE: constitution 6→14 laws (§7 lifecycle table, §8 concurrency/lease, §9 coordinator model, §10 backlog process, §11 gates, §12 anti-slop, §13 memory canon, §14 roster) + `quality-assurance.md`. | **Em revisão**, 4/4 `[x]`, **no CLOSURE.md**. |
| **v0.1.8** | Personas 15→9 core + 3 plugin stubs; generic `software-engineer`; coordinator personas deepened (lease/phase/dispatch); plugin-scope rule. | **Em revisão**, 9/9 `[x]`, **no CLOSURE.md**. |
| **v0.1.9** | Surface cleanup: skills 22→17, 7 stale workflows deleted + 2 authored (`release-ship`, `audit-fanout`), `product/` memory tree restructured (6 themes + wikilinked index). | **Em revisão**, T-019-02 still `[-]`, rest `[x]`, **no CLOSURE.md**. |
| **v0.2.0/integration** | Integrate v0.1.6–v0.1.9 on `feature/0.2.0`, dogfood lifecycle, drift-elim, ship-trio, single PyPI deploy. | **Em revisão**; T-020-04 (deploy) + T-020-05 (closure) **OPEN**. **Nothing on PyPI.** |

**Program shape (correct, well-reasoned):** v0.1.6 (lock) → v0.1.7 (freeze constitution) → v0.1.8 (personas) → v0.1.9 (surface) → integration. Lock-first so nothing later can deadlock; law-before-personas to avoid build-then-change thrash. Only v0.2.0 publishes. This sequencing is sound.

---

## 3. Conformance scorecard (canonical dimension → reality)

| # | Canonical dimension | Result | Evidence |
|---|---|---|---|
| 1 | 9 core agents incl. ai-engineer | **CONFORMS** | `@constitution.md:216-233` §14 |
| 2 | PM sole backlog writer | **CONFORMS** | §10 + `backlog-ownership` rule + gate path-owner check |
| 3 | Exactly-one-mutating-session **as law** | **CONFORMS (law)** | `@constitution.md:86-88, 105-106, 127` |
| 4 | Parallel additive sessions **as law** | **CONFORMS** | `@constitution.md:98-101` "Concurrent sessions allowed" |
| 5 | Single JSON TTL-lease, O_EXCL CAS, no-PID, cross-platform | **CONFORMS** | v0.1.6 `lease.py`; `@v0.1.6/SPEC.md:32-87` |
| 6 | Exactly-one enforced **in the running gate** | **DRIFT (D1)** | freeze fix made acquire always-takeover → 2 live sessions can both mutate |
| 7 | Never fail-dead / no manual rebind | **CONFORMS (now)** | freeze fix; verified e2e earlier today |
| 8 | 3-channel report model (HTML / handoff JSON / specs/audits MD) | **DRIFT (D2)** | §11/§12.3 say `.dadaia/reports/`+`.dadaia/handoff/` ONLY; `specs/audits` = 0 hits repo-wide |
| 9 | Dispatcher purity stated as law | **DRIFT (D3)** | implied by lease model; no explicit "only PM+PA dispatch / no agent-to-agent" clause |
| 10 | Spec-review sequence (qa first + arch parallel → SE last) | **DRIFT (D4)** | §11 encodes only the IMPL gate trio; no spec-review-ordering protocol |
| 11 | Review "gate" = coordinator checkpoint (honest) | **CONFORMS** | v0.1.8 §5 states A-2 is a convention, not a primitive |
| 12 | Parallel-session collision-naming for backlog/audit MD | **DRIFT (D6)** | no naming convention anywhere |
| 13 | v0.2.0 deployed + closed | **DRIFT (D8)** | all milestones `Em revisão`, no CLOSURE, T-020-04/05 OPEN, nothing on PyPI |

---

## 4. Findings & remediation (ordered)

### D1 — [P0] Restore exactly-one-mutating-session without re-introducing the freeze
The v0.1.6 lease blocked a foreign **live** lease (correct for exactly-one), but froze because **session identity is unstable** (relaunch / env-not-propagated → new `session_id` → the operator's own abandoned lease looks "foreign + live" for the full **1800 s TTL**). Today's emergency fix made `lease.acquire` **always take over** → freeze gone, but two genuinely-concurrent live sessions can now both mutate (race). Neither extreme is the canonical model.

**Correct design (release-worthy):**
1. **Short heartbeat-based liveness** + continuous heartbeat while a session is active (not a 30-min TTL gated on per-tool-use). An abandoned/relaunched holder goes stale in seconds–minutes, not 30 min.
2. **Stable session identity** per (operator, context) so a continuing/relaunched session is recognized as "mine" → RENEW, never a false conflict. (Build on the existing `.dadaia/sessions/runtime/<id>.ptr` mechanism.)
3. **Reclaim iff stale; yield iff live-foreign.** Foreign + stale → auto-reclaim (no manual step). Foreign + live in a mutating phase → **yield with an informative, non-fail-dead message** ("session X is actively implementing release Y; this session won't mutate to avoid a race and will auto-acquire when X goes idle") — never a deadlock, never a `lock steal`/rebind instruction.
4. Additive paths (backlog/bugs/audits/reports/handoff/tmp) → always allow, parallel.

This restores the operator's invariant while keeping the never-freeze guarantee. **Interim state:** the always-takeover fix stays live until this lands — it prioritizes never-freeze over exactly-one (acceptable for single-operator use; documented trade-off).

### D2 — [P0] Encode the 3-channel report model; create `specs/audits/`
Constitution §11 (`@:172-173`) and §12.3 (`@:188-189`) mandate `.dadaia/handoff/` + `.dadaia/reports/` **only** and forbid `specs/.../evidence/`. `specs/audits` has **zero hits** repo-wide. Canonical model needs three distinct channels.
**Remediation:** amend constitution §7 (Audit phase writes `specs/audits/<ts>/`), §11, §12.3 to encode the 3 channels (user HTML reports → `.dadaia/reports/`; agent↔agent JSON → `.dadaia/handoff/`; auditor MD → `specs/audits/<ts>/`, archive `specs/audits/_archive/`); update `project-auditor` persona + `audit-fanout` workflow to write `specs/audits/`; classify `specs/audits/**` as ADDITIVE in `sdd-spec-gate.sh` + `gate_policy.py` (parallel-safe, no lease); **relocate** the earlier lifecycle audit (`.dadaia/reports/dadaia-workspace/2026-06-06T193749Z/audit.md`) and this review into `specs/audits/`.

### D3 — [P1] State dispatcher purity as law
Add an explicit clause (§9 or §14): "Only `project-manager` and `project-auditor` may dispatch sub-agents (Agent tool). All other personas are workers — they reply only to their dispatcher and never invoke another agent." Tighten the one residual worker→worker line in `qa-engineer.md` (route via PM). (Overlaps the earlier-filed `constitution-persona-single-source-drift` bug.)

### D4 — [P1] Encode the spec-review sequence
Add to §11 (or a new §) the release-definition spec-review protocol distinct from the impl gates: `qa-engineer` reviews the SPEC **first (mandatory)** for testability/quality-gate-clarity; `software-architect` may review **in parallel (optional)**; only after QA APPROVE does `software-engineer` review PLAN/TASKS to confirm implementability. PM-mediated; sequential QA→SE.

### D5 — [P1] Relabel review "gates" → "coordinator-enforced checkpoints"
Operator chose the honest relabel (grill earlier today). Apply across §11 + qa/security/code-reviewer personas so "gate" stops implying a mechanical block. (Already filed: `specs/backlog/review-gate-enforcement-decision.md`.)

### D6 — [P1] Collision-safe naming for parallel additive markdown
Define a convention for files written by parallel sessions in backlog/audit/research: include a session discriminator + ISO timestamp (e.g. `<ts>-<session_id>-<slug>.md`; audit dir `specs/audits/<ts>-<session_id>/`). Mitigated today for backlog (PM-only writer) but **not** for audits (parallel sessions allowed). Add to §8/§12.

### D7 — [P2] Purge stale semaphore docs from memory
`specs/memory/product/platform/context-management.md`, `…/workspace-doctor.md`, `…/sdd/sdd-gate-v3.md` still describe the retired semaphore (Lock 4 / SEM-1 / dual-heartbeat) as live. product-engineer to fix in CLOSURE (memory is write-locked to PE in DEFINITION/CLOSURE). The store itself is fully deleted (code/tests/instance state) as of 2026-06-06.

### D8 — [P0-process] Close and ship v0.2.0 (and v0.1.5)
Every v0.2.0 milestone is `Em revisão` with **no CLOSURE.md**; T-019-02 still `[-]`; integration T-020-04 (deploy) + T-020-05 (closure) OPEN; **nothing on PyPI**; v0.1.5 T-SHIP-05 held. The lifecycle is dogfooded and ship-trio-approved but the release was never executed. Decide: fold D1–D6 into v0.2.0 before the single deploy (recommended — they touch the same constitution/personas being frozen), or ship v0.2.0 now and patch via a follow-up release from this audit.

### D9 — [note] 5 vs 8 phases
Constitution §7 has 8 phases; operator describes 5. Not a contradiction (8 is a clean superset: backlog-def={1,2}, audit={3,4}→ actually research+audit, release-def={5}, impl/review={6,7}, closure={8}). Optionally present the operator's 5-phase grouping as the headline with the 8 as sub-phases, for shared vocabulary.

---

## 5. What's genuinely right (keep)
- The 9-agent roster and two-dispatcher topology are correctly specified and internally consistent.
- §8 already encodes **exactly-one-mutating + parallel-additive as law** — the operator's concurrency model is in the constitution; only the *running mechanism* (D1) needs to match it.
- The single TTL-lease (O_EXCL CAS, no-PID, cross-platform) is the right primitive; D1 is a tuning/identity refinement, not a redesign.
- Milestone sequencing (lock → freeze → personas → surface → integrate) is well-reasoned and avoids build-then-change thrash.
- The anti-slop law (§12) and memory canon (§13) are sound foundations.

---

## 5b. Holistic / identity completeness — does the constitution carry the SOUL? (operator directive 2026-06-06)

The operator restated the full dadaia-workspace philosophy and required it be **registered in the constitution** and **reflected in memory**: a multi-AI-harness (Claude/Codex/opencode), multi-project, SDD-oriented, multi-agent workspace whose **keystone concept is the Spec Context Project** (spec folder + repo, bindable to a session, injects constitution+memory, enforces SDD, enables safe parallel multi-project work), staffed by **generic-but-role-specialized agents** with minimal tailored skills and context-engineered system prompts. Per the operator's own rule, the project-auditor treats the constitution as the **soul of the project** — so if the constitution doesn't express this, it is drifting regardless of mechanical correctness. Reviewed `@constitution.md:1-70`, `@specs/memory/product/index.md`, `@specs/memory/architecture.md`.

### D10 — [P0] Constitution has no Identity / Mission / Core-Concepts section
`@constitution.md:1-12` opens with one framing line then jumps to §1 "SDD Is Binding." There is **no statement of what dadaia-workspace IS**, no mission (multi-harness / multi-project / context-engineering value proposition), no agent philosophy, and — most critically — **the Spec Context Project concept is never defined** anywhere in the constitution. §8 uses "per context" purely mechanically. The keystone concept the operator capitalized is absent as a concept.
**Remediation:** add a §0 (or §1 preamble) **"Identity & Core Concepts"**: (a) what dadaia-workspace is + why (multi-harness, multi-project, SDD, multi-agent, context-engineering); (b) the **Spec Context Project** definition (spec folder pattern + repo + session binding + constitution/memory injection + SDD enforcement + safe parallel multi-project); (c) the value proposition (why operators/agents choose it). ai-engineer + product-engineer co-author in the v0.2.0 freeze.

### D11 — [P0] `architecture.md` memory is badly stale (drift) — predates the whole redesign
`@specs/memory/architecture.md:13-16` is `last_updated: 2026-06-04, release_origin: v0.1.4.6` — **before v0.1.6→v0.2.0**. It documents: **15 agents in 3 tiers** incl. `backend-engineer`/`software-engineer-node`/`software-engineer-python`/`researcher` (all deleted by v0.1.8) `@architecture.md:57`; **RULE E** (removed v0.1.6) `@architecture.md:112,136`; the **4-store lock model + semaphore + Lock 3 implementation lock** (retired by the single TTL lease) `@architecture.md:121,135,168-172`; "20/21 agent personas" `@architecture.md:66,243`; the old gate sequence diagram with `Session`/`Lock` participants `@architecture.md:114-149`.
**Remediation:** product-engineer rewrites `architecture.md` at CLOSURE to the v0.1.6–v0.2.0 reality: 9 core + 3 plugin roster, the single TTL-lease concurrency model, the lifecycle law, the 3-channel report model, the Spec Context Project. (Memory is write-locked to product-engineer in DEFINITION/CLOSURE.)

### D12 — [P1] Spec Context Project under-elevated in memory
The vision in `@specs/memory/product/index.md:3-8` is good, but the keystone concept is scattered across `platform/context-management.md` + `philosophy/repos-catalog.md` rather than framed as THE central value proposition. Elevate it (dedicated atom or a prominent index.md section) covering bind→inject→enforce→parallel-multi-project.

### D13 — [P1] Agent philosophy absent from the constitution
§14 is a roster table without the shaping philosophy: **generic capability, role-specialized for this SDD workflow, minimal tailored skills, context-engineered prompts, collaboration-only knowledge + dadaia core (CLI/panel/Spec Context)**. Add a short "Agent Philosophy" clause (to §14 or the new §0) with the per-agent specialization stance (ai-engineer=harness; product-engineer=specs+memory+slop-avoidance; project-manager=coordinator/lifecycle).

**Net:** the *mechanics* (roster, lease, lifecycle, anti-slop) are largely right; the *identity* (soul) is missing from the constitution and the architecture memory has drifted a full redesign behind. D10/D13 are constitution edits; D11/D12 are memory edits (product-engineer, CLOSURE) — all fold into v0.2.0.

## 6. Handoff
Per the canonical flow, this audit → `project-manager` converts D1–D13 into v0.2.0 scope or a follow-up patch release. Auditor does not implement.

Recommended single-fold into v0.2.0 (everything touches the constitution/personas/memory being frozen — close in one release, avoid a second freeze):
- **Constitution edits (ai-engineer + product-engineer):** D10 (Identity & Core Concepts + Spec Context Project), D13 (agent philosophy), D2 (3-channel report model + `specs/audits/`), D3 (dispatcher purity as law), D4 (spec-review sequence), D5 (gate→checkpoint relabel).
- **Gate/lease code (software-engineer + ai-engineer):** D1 (short-heartbeat liveness + stable session identity + reclaim-iff-stale/yield-iff-live — restores exactly-one-mutating without the freeze), D2 (`specs/audits/**` = ADDITIVE in the gate), D6 (collision-safe naming).
- **Memory (product-engineer, CLOSURE):** D11 (rewrite `architecture.md` to the v0.1.6–v0.2.0 reality — currently a full redesign stale), D12 (elevate Spec Context Project), D7 (purge stale semaphore docs).
- **Then D8 ships v0.2.0** (deploy + closure).

Priority of the two soul-level P0s: **D10** (constitution must describe what we are — the Spec Context Project keystone) and **D11** (architecture memory has drifted a full redesign behind) are the operator's headline concern: the constitution+memory must holistically represent dadaia-workspace, or they are lying.
