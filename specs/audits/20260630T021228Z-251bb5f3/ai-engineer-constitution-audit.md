---
name: ai-engineer-constitution-audit
audit: constitution re-scope vs SDD/agent-constitution best practices
date: 2026-06-30
surface: specs/constitution.md
auditor: ai-engineer
session: 251bb5f3
---

# Constitution audit — re-scope to durable normative law

## 0. Method & evidence base

- **Target:** `specs/constitution.md` — 663 lines, 5,541 words, §0–§14.
- **Cross-checked against:** `specs/memory/product/sdd/sdd-gate-v3.md` (v0.1.41,
  updated 2026-06-29), `specs/memory/product/platform/multi-platform-parity.md`,
  `specs/memory/product/philosophy/product-vision.md`,
  `specs/memory/architecture.md`, `specs/memory/product/catalog.json`, and the
  **enforced code** (`core/models/lifecycle.py::AgentRuntimeKind`,
  `hooks/root_whitelist.py`, `features/lifecycle/policy_public_doctor.py`).
- **Research note (tooling limit):** this sandbox exposes no `WebSearch`/`WebFetch`
  tool, so the best-practices baseline in §1 is grounded in established SDD-constitution
  conventions from training knowledge (GitHub Spec-Kit `constitution`, agent
  operating-principle patterns) and is **cited by name, not by live-verified URL**.
  A follow-up live-link verification pass is recommended before the rewrite SPEC is
  finalized, but the principle it establishes is not contentious.

---

## 1. What belongs in a constitution (best-practice baseline)

Synthesis of SDD-constitution / agent operating-principle practice:

| Source / pattern | Principle it establishes |
|---|---|
| **GitHub Spec-Kit `constitution`** (`/memory/constitution.md`, `speckit.constitution`) | A constitution is a **small set of non-negotiable articles/principles** (Library-First, CLI Interface, Test-First, Simplicity, Versioning…). Each is a normative *rule + rationale*, technology-agnostic. It is **versioned and amended deliberately**, with amendment history kept in a dedicated log — never inline in an article body. |
| **Spec-Kit "principles, not mechanism"** | The constitution says *"tests must precede implementation"* — it does **not** carry the test-runner flags, the CI matrix, or a 4-step resolution algorithm. Mechanism lives in plan/architecture artifacts. |
| **Agent operating-principle docs (Anthropic-style "constitutions")** | Durable behavioral *invariants*, deliberately abstract so they survive implementation churn. Concrete enum values, schemas, and TTL constants are **anti-patterns** in a constitution: they force a constitutional amendment for a non-constitutional code change. |
| **dadaia's own §12.3** | "No fact is recorded in two sources." The constitution states a fact once; memory/architecture elaborates. A fact present in both is drift waiting to happen. |

**Crisp principle for this audit:**

> **Constitution = the smallest set of durable, normative principles that govern all
> specs (the immutable "must" + "why").** Mechanism, current structure, schemas,
> matrices, enum values, and version history = **memory/architecture** (the mutable
> "how" and "what it currently is"). Vision/value-proposition = the **product-vision**
> atom. If a statement changes when the code changes, it is mechanism, not law.

By this test the current constitution is **~65% mechanism, vision, or changelog** that
has migrated into the law. The three giant sections (§0=184, §8=159, §11=80 = 423 lines
= 64% of the document) carry almost all of it; the genuinely durable principles
(§1,2,3,5,6,12 ≈ 70 lines) are a small minority.

---

## 2. Per-section verdict (§0–§14)

Legend: **KEEP** = durable law, retain (possibly trim) · **TRIM** = keep principle,
cut mechanism · **MOVE** = relocate to named memory file · **STALE** = delete,
contradicts code · **CHANGELOG** = delete, version history in law.

| § | Lines | Size | Verdict | Target / rationale |
|---|---|---|---|---|
| §0 Identity & Core Concepts | 11–194 | 184 | **MOVE + STALE + TRIM** | Self-labeled "declarative, **not normative**" (line 15). "What it is"/value-prop/agent-philosophy → `product-vision.md`. Two agentic layers + root layout + agent topology → `architecture.md`. **Keep only ~18 lines** of keystone vocabulary (Spec Context Project, bind→inject→enforce→parallel, two activity classes) as Article "Core Definitions". OpenCode mentions (L30, L95, L118, L121, L136–145, L165) → **STALE**. "supersedes … T-SANI-02 pending" (L182–183) → **CHANGELOG**. |
| §1 SDD Is Binding | 195–201 | 7 | **KEEP** | Pure durable principle. Verbatim retain. |
| §2 Public Defaults Generic | 202–213 | 12 | **KEEP / TRIM** | Principle durable. The enumerated capability list (L211–212: "frontend, backend, QA, DevOps, research…") is current-surface state and drift-prone → MOVE to `multi-platform-parity.md`/catalog. |
| §3 Memory Is Repo Truth | 214–222 | 9 | **KEEP** | Durable. Markdown-only format clause is borderline mechanism but stable; retain. |
| §4 Runtime Parity Honest | 223–246 | 24 | **TRIM + STALE** | **Principle** (~4 lines: "projections/doctor/AGENTS.md must not claim behavior a runtime does not enforce") = **KEEP**. The per-harness enforcement matrix (L229–245) duplicates `sdd-gate-v3.md` → **MOVE**. OpenCode row + "Claude Code, Codex, OpenCode, and PI" (L226, L234) → **STALE**. |
| §5 Source Repo Clean | 247–256 | 10 | **KEEP / TRIM** | Principle durable. `.opencode/`, `opencode.json` in the forbidden-artifact list (L251–252) → **STALE** (delete those two tokens). |
| §6 Layering | 257–267 | 11 | **KEEP** | Genuine durable architectural law (import directions). Retain. |
| §7 Canonical Lifecycle | 268–296 | 29 | **KEEP / CHANGELOG** | The 8-phase matrix is **THE normative spine** the whole doc references — KEEP. "consolidated roadmap §1 … genesis traceability" (L271–272) and "4-row summary in v0.2.0/SPEC.md §3 maps…" (L289) → **CHANGELOG**. |
| §8 Concurrency Model | 297–455 | 159 | **MOVE (majority) + TRIM + CHANGELOG** | **Principle** (~15 lines: two activity classes; exactly one MUTATING lease per context; ADDITIVE never leases; enforcement-honesty mechanical-vs-advisory) = **KEEP**. Lease record schema, `LEASE_TTL_SECONDS=120`, 4-step mode chain, DP-4 probe chain, O_EXCL/by-session index, both enforcement matrices (L346–454) **duplicate `sdd-gate-v3.md` + `context-management.md` verbatim-in-spirit** → **MOVE** (§12.3 self-violation). The 2026-06-10 v0.1.10 rc-3 amendment block (L327–338) → **CHANGELOG**. OpenCode matrix row (L444) + `OPENCODE_RUN` worker (L449) → **STALE**. |
| §9 Coordinator + Sub-Agent | 456–483 | 28 | **KEEP / TRIM** | Exactly-one-lease coordinator invariant + dispatcher-purity = durable normative. KEEP (~15 lines). ai-engineer carve-out is durable; retain compactly. |
| §10 Backlog-Definition | 484–503 | 20 | **TRIM + MOVE** | **Principle** (~5 lines: PM owns backlog; PE picks dispatched by PM; bugs never silently dropped; grill mandatory before SPEC) = **KEEP**. The numbered 6-step procedure → **MOVE** to `sdd-bug-backlog-governance.md` + the `backlog-ownership` rule. |
| §11 Review Checkpoints & Channels | 504–583 | 80 | **TRIM + MOVE + CHANGELOG** | Durable: checkpoint-vs-gate distinction; review ordering (qa→commit · security→push · code→PR); three exclusive report channels. KEEP (~22 lines). Push-gate mechanics (commit_sha keying) → **MOVE** to `release-governance` rule + `sdd-gate-v3.md`. "codified in v0.1.15 (the governance release)" (L551–555) → **CHANGELOG**. |
| §12 Anti-Slop Law | 584–603 | 20 | **KEEP / TRIM** | Three durable hard rules. KEEP. The collision-naming restatement (L599–602) duplicates §8 → cut to a pointer. |
| §13 Memory Canon | 604–628 | 25 | **KEEP / TRIM** | Four authoritative areas + PE sole author + no-changelog = durable. KEEP (~16 lines). |
| §14 Agent Roster | 629–663 | 35 | **KEEP** | 9-core roster + phase mapping + plugin-stub exemption + persona-existence rule = durable normative. Retain (already avoids restating agent philosophy). |

**Roll-up:** KEEP/TRIM-to-principle ≈ 180–210 lines; MOVE ≈ 330 lines; STALE ≈ 35
lines; CHANGELOG ≈ 25 lines. Target rewrite: **~200 lines (~70% reduction)**.

---

## 3. Drifts & duplications (severity-ranked)

### D1 — OpenCode 4-harness world is comprehensively STALE — **HIGH**
Code truth: `AgentRuntimeKind = {FAKE, CODEX_EXEC, CLAUDE_SDK, PI_HEADLESS}`
(`core/models/lifecycle.py:51`). `hooks/root_whitelist.py` allows only
`.agents .claude .codex .dadaia .pi repos`. `features/lifecycle/policy_public_doctor.py`
**actively forbids** `opencode`/`claude` as Layer-2 worker residue in public docs.
Memory is correct: `multi-platform-parity.md` + `catalog.json` state "OpenCode removed
entirely in v0.1.24 (both layers)". The **constitution alone is stale** at: L30, L95–96,
L118, L121, L136–145 (asserts "**five** `AgentRuntimeKind`s … `OPENCODE_RUN`"), L165
(`.opencode/` as root entry #5), L226, L234 (matrix row), L251–252 (`opencode.json`),
L444 (matrix row), L449 (`OPENCODE_RUN`). **8+ distinct stale assertions.**

### D2 — Root-entry count contradicts enforced law — **HIGH**
§0 L159 says "**ten** allowed root entries" and lists `.opencode/` as #5. The enforced
root-whitelist (`root_whitelist.py`, the root `AGENTS.md` Workspace Root Law, and the
`tmp-file-guardrail` rule) is **nine** entries: `.agents .claude .codex .dadaia .pi
repos` + `AGENTS.md CLAUDE.md prompt.md` — **no `.opencode/`**. The constitution's
count and membership are both wrong against the gate that actually blocks writes.

### D3 — §8 duplicates `sdd-gate-v3.md` (§12.3 self-violation) — **HIGH**
§8 (159 lines) restates the lease record schema, the 4-step mode-resolution chain, the
DP-4 pre-commit probe chain, the O_EXCL/by-session mechanics, and both enforcement
matrices. `sdd-gate-v3.md` carries the same content **more currently** (v0.1.41, dated
2026-06-29, vs the constitution's 2026-06-10 amendment). This is the exact pattern §12.3
forbids — and the two copies have **already diverged** (the constitution still shows an
OpenCode enforcement row; the memory file's matrix at L260 also retains a residual
OpenCode row, so *both* copies are independently stale — proof that duplication breeds
drift).

### D4 — Embedded changelog/amendment notes inside law — **MEDIUM**
A constitution must carry durable law, not version history. Offenders: the dated
2026-06-10 v0.1.10 rc-3 amendment block (§8 L327–338, incl. the four grandfathered audit
dir names); "supersedes any prior 'under investigation' or 'T-SANI-02 pending'" (§0
L182–183); "4-row summary in v0.2.0/SPEC.md §3 maps to…" (§7 L289); "codified in v0.1.15
(the governance release)" (§11 L551–555); "consolidated roadmap §1 … genesis
traceability" (§7 L271–272). These belong in CLOSURE.md / an amendments log.

### D5 — §0 self-admits non-normativity yet occupies 28% of the law — **MEDIUM**
§0 L15: "It is **declarative, not normative**: it imposes no new constraint." By its own
statement, 184 of 663 lines add no law. Vision and architecture description embedded in
binding law inflates every reader's load and blurs what is actually enforceable.

### D6 — Mechanism constants pinned in law — **MEDIUM**
`LEASE_TTL_SECONDS = 120` (§8 L348) is sourced in code from `core/kernel_tunables.py`
(per `sdd-gate-v3.md` L126–129). Pinning the literal in the constitution means a tunable
change would technically require a constitutional amendment — the §1 anti-pattern.

### D7 (secondary, out of ai-engineer scope) — Memory also retains OpenCode residue — **MEDIUM**
`architecture.md` (13 mentions) and `sdd-gate-v3.md` matrix (L260) still carry OpenCode
rows. These are **product-engineer's** files (memory canon, §13). Flagged for the same
release; not an AI-surface item.

---

## 4. Proposed lean constitution outline (~200 lines)

Principle-first; each article = normative rule + one-line rationale; mechanism replaced
by a single pointer to the owning memory file.

| New article | ~lines | One-line description | Source |
|---|---|---|---|
| Preamble | 3 | Permanent normative law; mechanism lives in memory; amendments logged in CLOSURE, never inline. | new |
| 1. Core Definitions | 18 | Spec Context Project (keystone); bind→inject→enforce→parallel; two activity classes (ADDITIVE/MUTATING); two agentic layers — one sentence each, pointer to `architecture.md`. | §0 (trimmed) |
| 2. SDD Is Binding | 7 | No production change without approved release gate + reserved task. | §1 |
| 3. Public Defaults Generic | 8 | No private data / domain packs in public assets. | §2 |
| 4. Memory Is Repository Truth | 8 | Memory = current state, not changelog; Markdown source only. | §3 |
| 5. Runtime Parity Honest | 5 | Projections/doctor/AGENTS.md must never claim behavior a runtime does not enforce. (matrix → `sdd-gate-v3.md`) | §4 (principle) |
| 6. Source Repo Clean | 6 | No generated projections/harness artefacts tracked at the source root. | §5 |
| 7. Layering | 11 | core ↛ features/infra/cli; features ↛ cli; compose via container. | §6 |
| 8. Canonical Lifecycle | 24 | The normative 8-phase matrix (owner × write target × activity class × lease). THE spine. | §7 (matrix only) |
| 9. Concurrency Invariant | 15 | One MUTATING lease per context; ADDITIVE never leases; enforcement honesty (mechanical vs advisory). Pointer to `sdd-gate-v3.md` + `context-management.md`. | §8 (principle) |
| 10. Coordinator & Dispatcher Purity | 15 | PM holds the single release lease across the MUTATING span; only PM + project-auditor dispatch. | §9 |
| 11. Backlog & Release Definition | 6 | PM owns backlog; PE picks dispatched by PM; bugs never dropped; grill mandatory before SPEC. (procedure → rule/memory) | §10 (principle) |
| 12. Review Checkpoints & Channels | 22 | Checkpoint vs gate; review ordering (qa→commit · security→push · code→PR); three exclusive report channels. | §11 (principle) |
| 13. Anti-Slop Law | 18 | Three hard rules (phase-ownership, GC-per-store, single-source-of-truth). | §12 |
| 14. Memory Canon | 16 | Four authoritative areas; PE sole author; no changelogs. | §13 |
| 15. Agent Roster | 35 | 9-core roster + phase mapping + plugin-stub exemption + persona-existence rule. | §14 |
| **Total** | **~215** | | |

### Migration map (what moves where)

| Content (current) | New home |
|---|---|
| §0 "what it is" / value proposition / agent philosophy | `memory/product/philosophy/product-vision.md` |
| §0 two agentic layers (full detail) | `memory/architecture.md` (+ `lifecycle-foundation.md` "Harness runtime boundary") |
| §0 workspace-root layout (full) | `memory/architecture.md` (enforced copy already in `root_whitelist.py` + root `AGENTS.md`) |
| §4 per-harness enforcement matrix | `sdd-gate-v3.md` (already present, more current) |
| §8 lease schema / mode chain / chokepoint chains / matrices / TTL | `sdd-gate-v3.md` + `context-management.md` (already present) |
| §10 6-step backlog procedure | `sdd-bug-backlog-governance.md` + `backlog-ownership` rule |
| §11 push-gate mechanics (commit_sha keying) | `release-governance` rule + `sdd-gate-v3.md` |
| All dated amendments / "codified in vX" notes | release `CLOSURE.md` / a dedicated amendments log |

---

## 5. AI-surface drift flag (grep, count-only)

**Clean.** The public AI-entity surface does **not** propagate the OpenCode / old
harness-count drift:

| Surface | OpenCode references |
|---|---|
| `public/agents/**` | **0** |
| `public/rules/**` | **0** |
| `public/skills/**` | **0** |
| `public/workflows/**` | **0** |
| "four/4 harness" in `public/**` | **0** |

The drift is **isolated to `specs/constitution.md`** (and, secondarily, to
product-engineer's memory atoms — D7). **No ai-engineer surface fix is required.** The
personas already speak in three-harness (Claude/Codex/PI) terms. ai-engineer's only
release obligation is to confirm the surface stays clean after the constitution rewrite
(regression check), not to author changes.

---

## 6. Prioritized release-scope items

> Ownership note: `specs/constitution.md` is a MUTATING `specs/` path — its author is
> **product-engineer** (spec/memory guardian, §13), dispatched by PM under the release
> lease. The memory relocations are likewise product-engineer's. **ai-engineer owns only
> the surface-regression check (R7).** Items are ordered by severity/leverage.

| # | What to change | File(s) | Owner | Acceptance criterion |
|---|---|---|---|---|
| R1 | Purge all OpenCode / "five AgentRuntimeKind" / `.opencode/` assertions; restate harness world as {Claude, Codex, PI} Layer-1 and {FAKE, CODEX_EXEC, CLAUDE_SDK, PI_HEADLESS} Layer-2. | `specs/constitution.md` | product-engineer | `grep -ci opencode specs/constitution.md` == 0; harness/runtime enumerations match `core/models/lifecycle.py::AgentRuntimeKind` exactly. |
| R2 | Fix the root-entry count + membership to the enforced nine (`.agents .claude .codex .dadaia .pi repos` + `AGENTS.md CLAUDE.md prompt.md`). | `specs/constitution.md` | product-engineer | Constitution root list is set-equal to `hooks/root_whitelist.py` allowed set + root `AGENTS.md` Workspace Root Law; no "ten" claim. |
| R3 | Collapse §8 to the ~15-line concurrency *invariant*; relocate lease schema / mode chain / DP-4 / matrices / TTL to memory; replace with a single pointer. | `specs/constitution.md`; cross-ref `sdd-gate-v3.md`, `context-management.md` | product-engineer | §8 ≤ 20 lines, contains no lease-record schema / TTL literal / probe-chain steps; `dadaia specs doctor` green; no fact appears in both constitution and `sdd-gate-v3.md`. |
| R4 | Move §0 vision/value-prop/agent-philosophy/two-layers/root-layout to memory; keep only a ~18-line "Core Definitions" article. | `specs/constitution.md`; `product-vision.md`, `architecture.md` | product-engineer | §0 successor ≤ 20 lines; relocated content present in named memory atoms; no normative claim lost (diff reviewed). |
| R5 | Strip every embedded changelog/amendment note (D4) from article bodies; relocate to CLOSURE / amendments log. | `specs/constitution.md` | product-engineer | No dated "Amendment (YYYY-MM-DD…)", "codified in vX", "supersedes T-…", or "maps to vN/SPEC §" string remains in the constitution body. |
| R6 | Replace pinned mechanism constants (e.g. `LEASE_TTL_SECONDS=120`) with a named pointer to `core/kernel_tunables.py` / `sdd-gate-v3.md`. | `specs/constitution.md` | product-engineer | No numeric tunable literal in the constitution; pointer present. |
| R7 | Regression-check the public AI surface stays OpenCode-free and harness-accurate after the rewrite; update any persona/skill/rule that the rewritten constitution renders inaccurate. | `dadaia_workspace/public/**` | **ai-engineer** | `grep -ric opencode dadaia_workspace/public/` == 0; no persona references a 4/5-harness world; `dadaia public doctor` green incl. `[ok] public-privacy`. |
| R8 | (secondary) Reconcile residual OpenCode in memory atoms (`architecture.md` 13×, `sdd-gate-v3.md` matrix L260). | `specs/memory/**` | product-engineer | Memory OpenCode mentions are either removed or explicitly historical ("removed in v0.1.24"); `policy_public_doctor` + `specs doctor` green. |

---

## 7. One-paragraph operator answer

The operator is correct on every count. The constitution is ~65% non-law: §0 (28%,
self-admittedly "declarative, not normative") is vision+architecture that belongs in
`product-vision.md` + `architecture.md`; §8 (24%) is a stale, more-detailed duplicate of
`sdd-gate-v3.md` that violates the constitution's own §12.3; and dated amendment notes
have leaked changelog into law. On top of that the whole OpenCode 4-harness world is
**stale** — code, the enforced root-whitelist, a dedicated doctor check, and memory all
agree OpenCode was removed in v0.1.24, but the constitution still asserts it 8+ times and
miscounts root entries as ten. The fix is a principle-first rewrite to ~200 lines (15
short articles, the 8-phase matrix as the spine), with all mechanism relocated to its
single memory home. The public AI surface is already clean (0 OpenCode references), so
ai-engineer's role is the post-rewrite regression check; the constitution and memory
rewrites belong to product-engineer.
</content>
</invoke>
