# TASKS: v0.1.7 — Constitution v2 + Development Lifecycle Law + Memory Canon

**Status:** Aprovado
**Release ID:** v0.1.7
**Parent program:** v0.2.0 — Agentic Development Lifecycle
**Owner:** product-engineer
**Created:** 2026-06-06

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.
Maximum one `[-]` per owner at a time unless disjoint write sets are declared below.
All tasks start `[ ]` OPEN.

> **Write-set safety note:** T-017-01 and T-017-02 have DISJOINT write sets
> (`specs/constitution.md` vs `specs/memory/product/**`). They MAY run concurrently
> if T-017-01 is under active authoring and the constitution draft is stable enough
> to cite. However: T-017-02 cites the §7 matrix and §14 roster from T-017-01;
> if T-017-01 is still changing, wait for T-017-01 commit before committing T-017-02.
> In practice, serial execution is safer and recommended.

---

### T-017-PRE — Diagnose existing LINT-1 doctor errors (read-only prerequisite)

- **Status:** [x]
- **Owner:** product-engineer
- **Write-set:** None (read-only audit)
- **Preconditions:** T-016-10 DONE (v0.1.6 committed and operator-validated)
- **Done criteria:**
  - Read `specs/memory/product/sdd-gate-v3.md` and identify the specific LINT-1
    violation(s): missing required frontmatter field, extra field not in
    `memory-frontmatter-v1.schema.json`, invalid `##` heading, broken `[[slug]]`
    wikilink.
  - Read `specs/memory/product/sdd-bug-backlog-governance.md` and identify the
    specific LINT-1 violation(s) using the same checklist.
  - Scan all atoms under `specs/memory/product/*.md` for `[[slug]]` wikilinks that
    resolve to a non-existent `.md` file; list each broken link.
  - Record the diagnosis (file → violation → proposed fix) as a comment below
    this task or in the PLAN.md T-017-PRE section. No file is edited.
  - This step has no commit. Its output feeds T-017-02.
- **Commit convention:** none (read-only step)

---

### T-017-01 — `specs/constitution.md` v2

- **Status:** [x]
- **Owner:** product-engineer
- **Write-set:** `specs/constitution.md`
- **Preconditions:** T-016-10 DONE; T-017-PRE complete (diagnosis recorded)
- **Done criteria:**
  - §1–§6 (existing laws) preserved verbatim, except §4 Runtime Parity Must Be Honest:
    update the cross-harness honesty claim to state: "Claude Code = real block (gate is
    an enforced shell hook); Codex = guardrail in trusted-workspace mode (advisory on
    untrusted Codex); opencode = advisory only." This must match the v0.1.6 implementation.
  - **§7 Canonical Development Lifecycle** present: 8-row table (columns: #, Phase,
    Owner, Writes to, Activity class, Lease behavior) authored using consolidated roadmap
    §1 as starting point; constitution §7 is the normative source once committed
    (roadmap is supporting context, not the gate). Row 6 "Writes to" must read:
    "`repos/<ctx>/` prod + tests (or `dadaia_workspace/**` when dadaia-workspace is the
    bound context)" — self-host generalization present. The single governing rule
    sentence present below the table: "Exactly one MUTATING actor per context at a time
    (phases 5/6/8), serialized by one lease that project-manager coordinates. ADDITIVE
    actors (1/2/3/4/7) run in parallel and never touch the lease." The umbrella-
    reconciliation sentence present: "The 4-row summary in v0.2.0/SPEC.md §3 maps to
    phases {1,2}/{3,4}/{5,6,8}/{7}; constitution §7 is normative."
  - **§8 Concurrency Model** present: two subsections (ADDITIVE paths, MUTATING paths).
    Lease schema `{context, release, session_id, mode, acquired_at, heartbeat, ttl}` cited
    verbatim from v0.1.6 `lease.py`. `LEASE_TTL_SECONDS = 120` stated (short heartbeat,
    OQ-1 operator decision 2026-06-06 — NOT 1800s). Stable-identity `.ptr` mechanism
    stated. Liveness formula `now − heartbeat ≤ LEASE_TTL_SECONDS` stated. `O_EXCL` CAS
    stated as the acquire mechanism.
    Fail-safe behavior stated: absent or expired lease heals and allows.
  - **§9 Coordinator + Sub-Agent Architecture** present: PM acquires ONE lease at phase 5
    entry; PE and SE run as PM sub-agents under that single lease; no independent acquire
    by PE or SE; `session_id` always stays as PM's coordinator session; writer role moves
    by PM dispatching the next sub-agent; lease never changes hands; cross-phase deadlock
    structurally impossible because only MUTATING span takes a lock. Exactly-one-lease
    invariant stated with explicit ai-engineer carve-out: outside a release span,
    ai-engineer (only) may take its own short MUTATING lease for surface fixes; this
    never overlaps a PM-held release lease because the gate blocks a second holder;
    exclusivity invariant preserved.
  - **§10 Backlog-Definition Process** present: 6-step numbered sequence (PM owns
    `specs/backlog/**`; PM dispatches PE never self-initiated; PE sanitizes; PE picks with
    bug-always-solved; grill mandatory; SPEC written). The mandatory grill step states:
    "A `dadaia-grill-me` session on the picked set is mandatory before the SPEC is written.
    PM will not advance a release to SPEC without it."
  - **§11 Review-Gate Sequence** present: rc-N gate (qa→commit, security→push,
    code-review→PR, PE memory after code-review); alpha-N gate (qa→commit only);
    evidence path (`.dadaia/handoff/<context>/` and `.dadaia/reports/<context>/` only,
    never `specs/releases/<id>/evidence/`); reject flow (re-opens relevant task).
  - **§12 Anti-Slop Law** present: three hard rules — (1) no agent/skill/rule/workflow
    ships without a phase in §7 that it owns or gates; (2) no store created without a GC
    mechanism; (3) no fact recorded in two sources.
  - **§13 Memory Canon** present: 4 canon memory AREAS named explicitly
    (`architecture.md`, the `product/**` atom tree, `tech-stack.md`,
    `quality-assurance.md`). PE is the sole author. PE write permission in DEFINITION
    phase + CLOSURE phase (both). Memory is current-state only — not a changelog.
  - **§14 Agent Roster** present: 9-row table (project-manager, project-auditor,
    product-engineer, software-engineer, qa-engineer, security-reviewer, code-reviewer,
    ai-engineer, software-architect) with columns (Agent, Phase, Activity class, Lease
    relationship). Plugins paragraph names frontend-engineer, design-specialist,
    devops-engineer as not in core. Persona-existence rule stated: every surviving persona
    must reference a §7 phase.
  - No new lease mechanics beyond OQ-1..4 ratified in v0.1.6. Specifically: no PID-based
    liveness, no semaphore fields, no per-phase lock variants.
  - qa-engineer can confirm: §7 matrix is internally self-consistent, the self-host
    path generalization is present (row 6), and the umbrella-reconciliation sentence is
    present. Operator confirms the matrix matches the lived workflow. The roadmap §1 is
    supporting context; no verbatim diff is required.
  - `git diff HEAD -- specs/constitution.md` shows only §4 update + new §7–§14 appended.
    No existing law text removed or paraphrased without explicit note.
- **Commit convention:** `feat(constitution): v2 — lifecycle law + anti-slop + roster (T-017-01)`
- **Parallelism note:** T-017-01 and T-017-02 have disjoint write sets. They may run
  concurrently only after T-017-01 content is stable. Serial execution recommended.

---

### T-017-02 — Memory atom authoring + LINT-1 fixes

- **Status:** [x]
- **Owner:** product-engineer
- **Write-set:**
  - `specs/memory/product/quality-assurance.md` (NEW)
  - `specs/memory/product/index.md`
  - `specs/memory/product/test-suite-architecture.md` (annotation only)
  - `specs/memory/product/sdd-gate-v3.md` (LINT-1 fix)
  - `specs/memory/product/sdd-bug-backlog-governance.md` (LINT-1 fix)
- **Preconditions:** T-017-01 DONE (quality-assurance.md cites §7 matrix and §14 roster)
- **Done criteria:**
  - **`quality-assurance.md` created** with all 6 required sections:
    - `## Propósito` — five-layer pytest architecture (unit/contract/integration/e2e/tmp),
      CI 7-job split, no-slop policy. States this is the design-of-record for implementers
      and qa-engineer, absorbing `test-suite-architecture.md`.
    - `## Fluxo de uso` — 5-step numbered sequence:
      1. Developer picks the test layer (pure function → unit; public contract → contract;
         multi-component real fs → integration; user journey → e2e).
      2. Test receives `@pytest.mark.<layer>` decorator; slow tests also `@pytest.mark.slow`.
      3. Local fast path: `pytest -q -m "unit and not slow" tests/unit` — under 10 seconds,
         no coverage instrumentation.
      4. CI runs 7 jobs (lint, typecheck, unit-fast, contract-coverage, integration,
         e2e-python, e2e-panel) each with explicit timeout and targeted marker filter.
      5. One-off debugging reproduction goes to `tests/tmp/` with expiry note; never counted
         toward coverage or release closure.
    - `## Trigger típico` — single sentence: used when implementing a new feature,
      refactoring a public contract, or reproducing a CI failure.
    - `## Diferencial` — without the layer taxonomy: no boundary between fast and slow,
      local runs slow, coverage inflation hides weak contracts, release-history tests
      accumulate. The layer taxonomy + CI split + no-slop policy close all three failure
      modes simultaneously.
    - `## Estado runtime tocado` — files read/written: `pyproject.toml`, `tests/unit/**`,
      `tests/contract/**`, `tests/integration/**`, `tests/e2e/**`, `tests/tmp/**`,
      `.github/workflows/ci.yml`, `tests/conftest.py`.
    - `## Dependências` — `[[specs-doctor]]`, `[[public-asset-distribution]]`,
      `[[agent-comms]]`, `[[sdd-gate-v3]]`.
  - **`quality-assurance.md` frontmatter valid:**
    - `slug: quality-assurance`
    - `title: quality-assurance`
    - `category: product`
    - `tldr:` ≤120 chars, one sentence
    - `summary:` 2–3 sentences
    - `tags:` contains at minimum `testing`, `pytest`, `ci`, `quality`
    - `agent_tier: self-pull`
    - `token_estimate:` present (integer estimate ≥ 1)
    - `last_updated: '2026-06-06'`
    - `release_origin: v0.1.7`
  - No forbidden headings (`## Changelog`, `## History`, `## Histórico`, `## Versions`) present.
  - `[[slug]]` wikilinks in the new atom resolve to real `.md` files in `specs/memory/`.
  - **`index.md` updated:** catalog row for `quality-assurance` present with `slug`,
    `title`, `tldr` matching the atom frontmatter exactly. Row placed in appropriate
    daily-relevance position (near `test-suite-architecture` which it supersedes).
  - **`test-suite-architecture.md` annotation added:** the SUPERSEDED block appears as
    the very first content after the frontmatter delimiter (`---`), before ALL existing
    body content (headings, prose, diagrams). No content may precede the block in the
    body. Block text:
    ```
    > **SUPERSEDED** — Content absorbed into `quality-assurance.md` (v0.1.7).
    > This file will be moved to `specs/_archive/legacy-memory/` at v0.2.0 CLOSURE.
    > Do not edit. Read `quality-assurance.md` instead.
    ```
    Frontmatter unchanged. Existing body content unchanged and present after the block.
    File not deleted.
  - **`index.md` catalog entry — no dangling pointer:** the catalog row for
    `test-suite-architecture` is updated to redirect readers to `quality-assurance.md`.
    Specifically: the `tldr` or a note in the entry must indicate "SUPERSEDED — see
    quality-assurance.md" so that any agent scanning the catalog does not follow a stale
    pointer to the superseded atom. The `quality-assurance` catalog row added in the same
    commit is the live entry. Both rows must be present; `test-suite-architecture` row
    must not be silently removed (it will be archived at v0.2.0 CLOSURE).
  - **`sdd-gate-v3.md` LINT-1 fix:** two pre-diagnosed mechanical repairs applied:
    (1) `summary:` frontmatter shortened to ≤ 280 characters (schema limit); content
    meaning preserved. (2) Broken wikilink `[[semaphore-no-liveness-reclaim]]` in the
    "Context semaphore" paragraph removed and replaced with plain text
    `tracked in \`specs/bugs/\`` — the slug is a bug file, not a memory atom; wikilink
    is categorically invalid. No content meaning change. `dadaia specs doctor` LINT-1
    passes on this file after the fix.
  - **`sdd-bug-backlog-governance.md` LINT-1 fix:** one pre-diagnosed mechanical repair:
    `summary:` frontmatter shortened to ≤ 280 characters (schema limit); content meaning
    preserved. `dadaia specs doctor` LINT-1 passes on this file after the fix.
  - **`dadaia specs doctor` exits 0** after all five write targets are committed
    (LINT-1 passes on all atoms including the new one and the two fixed ones).
  - No atom under `specs/memory/product/` has a `[[slug]]` wikilink that resolves to a
    non-existent `.md` file.
- **Commit convention:** `feat(memory): quality-assurance.md atom + LINT-1 fixes + superseded annotation (T-017-02)`

---

### T-017-03 — qa-engineer gate (pre-commit) + operator in-workspace validation

- **Status:** [x]
- **Owner:** qa-engineer
- **Write-set:** `.dadaia/handoff/dadaia-workspace/` (ADDITIVE — evidence only)
- **Preconditions:** T-017-01 DONE; T-017-02 DONE
- **Disjoint write set declared:** yes — qa-engineer writes only to `.dadaia/handoff/`
  (ADDITIVE path); no contention with any product-engineer write.
- **Done criteria:**
  - qa-engineer reads T-017-01 commit and checks:
    - §7 matrix is internally self-consistent: 8 rows, correct columns, row 6 "Writes
      to" includes the self-host generalization (`dadaia_workspace/**`), umbrella-
      reconciliation sentence present (4-row umbrella maps to phases {1,2}/{3,4}/{5,6,8}/{7}).
      Operator confirms the matrix matches the lived workflow. (Constitution §7 is
      normative once committed; roadmap is supporting context only — no verbatim diff
      required.)
    - No new lease mechanics beyond OQ-1..4. Specifically: no PID field in §8 lease
      schema, no semaphore-related fields, no per-phase lock variants, no session-file
      schema changes.
    - §9 sub-agent model stated explicitly: PE and SE do not independently acquire;
      `session_id` always stays as PM's coordinator session. ai-engineer carve-out
      present: outside a release span, ai-engineer may hold its own short MUTATING lease
      for surface fixes; gate blocks overlap with PM release lease; exclusivity invariant
      preserved.
    - §11 evidence convention states `.dadaia/handoff/` + `.dadaia/reports/` only;
      no `specs/releases/<id>/evidence/` subtree mentioned or authorized.
    - §14 roster: exactly 9 agents named; each has activity class + lease relationship
      declared in the table.
    - §12 anti-slop law: all 3 hard rules present.
    - §13 memory canon: all 4 canon memory AREAS named (architecture.md, product/** tree,
      tech-stack.md, quality-assurance.md).
    - §4 cross-harness honesty update: Claude Code = real block; Codex = guardrail;
      opencode = advisory. Statement is accurate relative to v0.1.6 implementation.
  - qa-engineer reads T-017-02 commit and checks:
    - `quality-assurance.md` has all 6 required `##` headings (Propósito, Fluxo de uso,
      Trigger típico, Diferencial, Estado runtime tocado, Dependências).
    - Frontmatter has all required fields; no extra fields; no forbidden headings.
    - `index.md` catalog entry for `quality-assurance` present and correct; the
      `test-suite-architecture` catalog entry is also present and updated with a
      "SUPERSEDED — see quality-assurance.md" note (no dangling pointer).
    - `test-suite-architecture.md` SUPERSEDED annotation block is the first content
      after the frontmatter delimiter, before ALL existing body content (verify: no
      heading or prose appears before the block in the body).
    - `sdd-gate-v3.md` LINT-1 fixes applied: (a) `summary:` shortened to ≤ 280 chars;
      (b) `[[semaphore-no-liveness-reclaim]]` wikilink removed and replaced with
      `tracked in \`specs/bugs/\``. Content meaning unchanged.
    - `sdd-bug-backlog-governance.md` LINT-1 fix: `summary:` shortened to ≤ 280 chars;
      content meaning unchanged.
  - `dadaia specs doctor` run result confirms exit 0. Output shows no LINT-1 errors, no
    broken wikilinks, no missing required frontmatter fields.
  - Handoff JSON emitted at:
    `.dadaia/handoff/dadaia-workspace/T-017-03-qa-gate.handoff.json`
    with `"schema_version": "handoff-v1.1"`, `"agent": "qa-engineer"`,
    `"scope": "v0.1.7 constitution + memory atom"`,
    and `"verdict": "APPROVED"` (or `"REJECTED"` if any check fails).
  - If verdict is REJECTED: findings listed in handoff `"findings"` array with
    `"severity"` and `"fix_recommendation"` per finding; the failing T-017-0x task
    is re-opened to `[ ]` status; T-017-03 itself stays `[-]` until re-run after fix.
  - If verdict is APPROVED: operator in-workspace validation proceeds.
  - **Operator validation:**
    - Operator reads `specs/constitution.md` and confirms:
      (a) The 8 lifecycle phases match how work actually flows on this instance.
      (b) The 9-agent roster is correct and complete.
      (c) The gate sequence (qa→commit, security→push, code-review→PR) matches how
          gates actually run on this instance.
      (d) The backlog-definition process (6 steps) matches PM's actual workflow.
      (e) The concurrency model (ADDITIVE parallel, MUTATING serialized) matches
          what the v0.1.6 lock enforces.
    - Operator sign-off recorded: either as a comment appended below this task or as
      `"operator_signoff": "CONFIRMED"` in the handoff JSON.
  - All checks above pass → APPROVE verdict → commit to `feature/0.2.0` allowed.
- **Commit convention:** `chore(gate): v0.1.7 qa-engineer approval + operator sign-off (T-017-03)`

---

---

### T-017-04 — Constitution §0 + D2/D3/D4/D5/D6-law/D10/D13 soul-fold additions

- **Status:** [x]
- **Owner:** ai-engineer (constitution philosophy text + identity; product-engineer reviews for anti-slop compliance)
- **Write-set:** `specs/constitution.md`
- **Preconditions:** T-017-01 DONE (constitution v2 base committed); T-016-17 DONE (v0.1.6 soul-fold committed and operator-validated — constitution §0 cites the stable-session-identity as implemented fact)
- **Disjoint write set:** yes — same file as T-017-01 but T-017-01 is a precondition (no concurrent edit)
- **Done criteria:**
  - **§0 "Identity & Core Concepts" added** as the first section of `specs/constitution.md` (before §1). Content (see SPEC §11 soul-fold addendum D10/D13):
    - Sub-section "What dadaia-workspace is": multi-AI-harness × multi-project × SDD × multi-agent × context-engineering workspace. 3–5 sentences, no implementation detail.
    - Sub-section "The Spec Context Project": the keystone concept. One definition paragraph: a Spec Context Project is a spec folder (`specs/`) + one repo bound to it, session-bindable (a session binds to a context and works under its constitution + memory), injects constitution+memory into the session via lazy consumption, enforces the SDD lifecycle end-to-end, and enables safe parallel multi-project work (one lease per context; ADDITIVE work runs concurrently). The paragraph covers the bind→inject→enforce→parallel-multi-project value chain.
    - Sub-section "Agent Philosophy" (D13): agents are generic AI implementations specialized only in their dadaia-workspace SDD role — how they fit the lifecycle, which phases they own or gate, what skills and context-engineering they carry. No project-domain knowledge in agents — that lives in the Spec Context's specs. Key per-agent specialization stated: ai-engineer = multi-harness surface + agent/skill/persona engineering; product-engineer = specs + memory + anti-slop guardianship; project-manager = full lifecycle coordinator + every agent's attributions as delegator; software-engineer = production code + TDD + SDD task discipline. Other agents cited by role briefly.
    - Sub-section "Value proposition": why operators and agents choose dadaia-workspace (1–2 sentences).
  - **§7 Phase 4 (Audit) "Writes to" column updated** (D2): from `.dadaia/reports/**` to `specs/audits/<ts>-<session_id_8chars>/`. The row notes: "Audit output is committed Markdown in the Spec Context's `specs/audits/` tree; not HTML, not `.dadaia/reports/`."
  - **§11 evidence path updated** (D2/D5): add enumeration of all 3 channels. Add spec-review sequence sub-section (D4). Replace "gate" wording for reviewer transitions with "coordinator-enforced checkpoint" (D5). Existing qa→commit/security→push/code-review→PR sequencing is preserved; only the vocabulary changes for the reviewer-transition steps.
  - **§9 dispatcher-purity clause added** (D3): explicit sentence: "Only `project-manager` and `project-auditor` may dispatch sub-agents via the Agent tool. All other personas are workers — they reply only to their dispatcher and never invoke another agent."
  - **§8 ADDITIVE section updated** (D6-law): add naming convention rule for parallel additive markdown in `specs/audits/`: `<YYYYMMDDTHHMMSSZ>-<session_id_8chars>/` for directories.
  - **§12 anti-slop law updated** (D2/D6): rule 3 updated to enumerate all three evidence channels explicitly; add rule about naming convention for parallel audit sessions.
  - No existing §1–§6 law text removed or paraphrased. No new lease mechanics beyond OQ-1..4. §0 is declarative — no new normative constraint that would conflict with §7–§14.
  - `git diff HEAD -- specs/constitution.md` shows only additions (§0 new, §7 Phase-4 Writes-to column edit, §9 dispatcher clause, §11 channel enum + spec-review sequence + D5 wording, §8 naming law, §12 rule 3 update). No deletions of existing law text.
- **Commit convention:** `feat(constitution): §0 Identity+CoreConcepts+AgentPhilosophy + D2/D3/D4/D5/D6/D13 soul-fold (T-017-04)`

---

### T-017-05 — Delete CLOSURE-only duplicates in product-engineer + workspace-protocol (P1a deduplication)

- **Status:** [x]
- **Owner:** ai-engineer (persona surface edit)
- **Write-set:**
  - `dadaia_workspace/public/agents/product-engineer.md` (remove CLOSURE-only wording from "atomicity contract" section — the losing duplicate)
  - `dadaia_workspace/public/rules/workspace-protocol.md` (remove §5 CLOSURE-only wording — the losing duplicate)
- **Preconditions:** T-017-04 DONE (constitution §13 "DEFINITION+CLOSURE" is the single source — T-017-05 cites it as canonical; the duplicates in persona/rule must be removed after the canon is committed)
- **Done criteria:**
  - `product-engineer.md`: locate the "Memory atomicity contract" or equivalent section that says memory writes are permitted "only during CLOSURE phase." Update to say "permitted in DEFINITION phase (new atoms and quality-assurance.md) and CLOSURE phase (updating atoms after a release ships), per constitution §13." The expanded meaning (DEFINITION+CLOSURE) replaces the narrower CLOSURE-only statement. Cite: `constitution.md §13` as the source.
  - `workspace-protocol.md §5`: locate the "Memory atomicity" rule that says "write-locked... except product-engineer during CLOSURE phase." Update to say "write-locked for all agents except product-engineer, who may write in DEFINITION phase and CLOSURE phase per constitution §13." Cite: `constitution.md §13`.
  - No other content change in either file (scope is strictly the P1a deduplication).
  - After this commit, `grep -r "CLOSURE-only\|only.*CLOSURE" dadaia_workspace/public/agents/product-engineer.md dadaia_workspace/public/rules/workspace-protocol.md` → 0 hits that contradict the DEFINITION+CLOSURE canonical answer.
  - `dadaia public doctor` exit 0 after this commit (no broken asset references).
- **Commit convention:** `fix(persona): dedupe memory-write-phase CLOSURE-only language → DEFINITION+CLOSURE per §13 (T-017-05)`

---

### T-017-06 — qa-engineer gate: soul-fold (D2/D3/D4/D5/D6-law/D10/D13) + extended operator sign-off

- **Status:** [x]
- **Owner:** qa-engineer
- **Write-set:** `.dadaia/handoff/dadaia-workspace/` (ADDITIVE — evidence only)
- **Preconditions:** T-017-04 DONE; T-017-05 DONE
- **Done criteria:**
  - qa-engineer reads T-017-04 commit and checks all 7 acceptance criteria 14–20 from SPEC §8:
    - §0 present: Identity sub-section + Spec Context Project sub-section + Agent Philosophy sub-section + Value Proposition sub-section (AC-14, AC-15)
    - §7 Phase 4 "Writes to" updated to `specs/audits/<ts>/` (AC-16)
    - §9 dispatcher-purity clause present (AC-17)
    - §11 contains spec-review sequence sub-section + 3-channel enumeration + "coordinator-enforced checkpoint" wording (AC-18, AC-19)
    - §8 ADDITIVE section contains D6 naming law (AC-20)
    - §12 rule 3 updated with 3-channel separation and naming convention
    - No new lease mechanics introduced (existing AC-10 guard)
    - No existing §1–§14 law text removed (text is additive only)
  - qa-engineer reads T-017-05 commit and checks:
    - product-engineer.md no longer says memory writes are CLOSURE-only; cites §13 for DEFINITION+CLOSURE
    - workspace-protocol.md §5 no longer says memory writes are CLOSURE-only; cites §13
    - Both files cite `constitution.md §13` as the canonical source
  - `dadaia specs doctor` run result confirms exit 0 (no new doctor errors from the constitution additions).
  - **Operator extended sign-off:** Operator reads `specs/constitution.md §0` and confirms:
    - (a) §0 correctly describes what dadaia-workspace is (the operator recognizes the description as accurate to their intent)
    - (b) The Spec Context Project definition matches the operator's stated keystone concept (bind→inject→enforce→parallel)
    - (c) The Agent Philosophy clause matches the operator's stated view on agent genericity + role-specialization
    - (d) §11 "coordinator-enforced checkpoint" wording correctly describes how reviewer checkpoints actually work (PM-mediated, not mechanical-shell-block)
    - (e) §7 Phase 4 Audit row "Writes to `specs/audits/<ts>/`" matches the channel-3 model the operator ratified
    - Operator sign-off recorded in handoff JSON or comment below this task.
  - Handoff JSON emitted at: `.dadaia/handoff/dadaia-workspace/T-017-06-soul-fold-qa-gate.handoff.json` with `"verdict": "APPROVED"` (or `"REJECTED"` with findings).
  - APPROVE verdict → milestone complete; push to `feature/0.2.0` authorized.
- **Commit convention:** `chore(gate): v0.1.7 soul-fold qa-engineer approval + extended operator sign-off (T-017-06)`

---

## Summary

| Task | Owner | Write-set | Status |
|------|-------|-----------|--------|
| T-017-PRE | product-engineer | None (read-only) | [x] |
| T-017-01 | product-engineer | `specs/constitution.md` | [x] |
| T-017-02 | product-engineer | `specs/memory/product/**` (5 files) | [x] |
| T-017-03 | qa-engineer | `.dadaia/handoff/dadaia-workspace/` | [x] |
| **T-017-04** | ai-engineer | **`specs/constitution.md` §0+D2/D3/D4/D5/D6/D13 soul-fold** | [x] |
| **T-017-05** | ai-engineer | **`product-engineer.md` + `workspace-protocol.md` (P1a deduplication)** | [x] |
| **T-017-06** | qa-engineer | **`.dadaia/handoff/dadaia-workspace/` (soul-fold qa gate)** | [x] |

**Original: 4 tasks** (T-017-PRE through T-017-03, all DONE). **Soul-fold adds: 3 tasks** (T-017-04 through T-017-06). **Grand total: 7 tasks.**

T-017-04 and T-017-05 may run concurrently (disjoint write sets: `constitution.md` vs persona + rule files). T-017-06 requires both DONE.

> **Operator note for T-017-06:** after qa-engineer APPROVE and extended operator sign-off,
> push the T-017-04 + T-017-05 + T-017-06 commits to `feature/0.2.0`. A security-reviewer
> gate and code-reviewer gate are NOT required for this milestone (document-only alpha segment;
> qa→commit is the gate per ADR-3 alpha cadence). The ship-trio runs at the v0.2.0 final rc.
>
> **Precondition note:** T-017-04 requires T-016-17 DONE (v0.1.6 soul-fold committed). If
> v0.1.6 soul-fold tasks are not yet complete, T-017-04 is blocked. T-017-04 must not cite
> the stable-session-identity mechanism as implemented fact until T-016-11..17 are committed.
