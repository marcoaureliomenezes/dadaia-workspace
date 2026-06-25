# TASKS — Release `v0.1.18`

> **Status:** Aprovado
> **Release ID:** v0.1.18
> **Owner:** product-engineer (task authority); per-task owners below
> **Created:** 2026-06-25

## Marker contract

`[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. TDD-first for code: write the failing test
before the fix. Conventional commits. A task is DONE only when its acceptance is checkable
and (for the gate-ladder/global tasks) reviews are green.

## Parallelism declaration (disjoint write sets)

The three implementing owners — **product-engineer**, **ai-engineer**, **software-engineer**
— have **disjoint write sets** (see PLAN "Owners & disjoint write sets"). Therefore **each
owner may hold one `[-]` concurrently**. Within a single owner, max one `[-]` at a time.

**Hard sequencing exception:** the live `--target pi` smoke inside **T-PIO-07** (and the
global-gates **T-PIO-15**) depend on **T-PIO-05** (root-whitelist hook) being merged first
— `.pi/` is gate-blocked until `_WHITELIST` accepts it. **T-PIO-11** (regenerate index.md)
depends on **T-PIO-10** (catalog CLI emits index.md).

---

## Thread A — Constitution amendment (owner: product-engineer)

- [x] **T-PIO-01** — Apply constitution amendment blocks 1.1–1.6 (operator sign-off required).
  - **Owner:** product-engineer
  - **Write set:** `specs/constitution.md`
  - **Preconditions:** ACTIVE.md phase allows MUTATING constitution edit; operator sign-off
    obtained (constitution is product law). Design doc Deliverable 1 is the verbatim source.
  - **Done criterion:** §0 has the "The two agentic layers" subsection (1.1); the layout
    list has `.pi/` with the trust-boundary note and now lists ten entries (1.2); the §0
    identity line names the four entry harnesses + both layers (1.3); §4 honesty clause is
    Layer-1-scoped + PI row (1.4); §8 split into Layer-1 enforcement matrix (PI row) +
    Layer-2 worker-runtime posture note, 5 kinds, only CLAUDE_SDK Ring-1 (1.5); the
    `ai-engineer` §0-philosophy clause names the four harnesses + both layers (1.6).
    `public/scaffold/constitution.md` is UNCHANGED. `dadaia specs doctor` 0 errors and
    SPEC-DOC-028 passes.
  - **Parallelism:** independent of all other threads.

---

## Thread C — Root-whitelist update (owners: software-engineer + ai-engineer)
*(Listed before B because it gates B's live smoke.)*

- [x] **T-PIO-05** — Add `.pi/` to the `pre_gate` root-whitelist hook (TDD).
  - **Owner:** software-engineer
  - **Write set:** `dadaia_workspace/hooks/root_whitelist.py`; hook unit test module;
    the `dadaia doctor` ROOT check that enumerates the whitelist (+ its test).
  - **Preconditions:** failing test first — a payload creating `.pi/settings.json` is
    asserted allowed (currently blocked).
  - **Done criterion:** `_WHITELIST` includes `.pi/`; a Write creating `.pi/...` is NOT
    blocked; a non-whitelisted new root dir is still blocked; the doctor ROOT check accepts
    `.pi/`; unit tests cover both allow (`.pi/`) and still-block (other) cases; tests green.
  - **Parallelism:** software-engineer slot. **MUST merge before T-PIO-07 live smoke.**

- [x] **T-PIO-06** — Update the projected root-law surface for `.pi/`.
  - **Owner:** ai-engineer
  - **Write set:** `dadaia_workspace/public/rules/tmp-file-guardrail.md` (root-whitelist
    table); `dadaia_workspace/public/data/AGENTS.md` (Workspace Root Law text).
  - **Preconditions:** none (disjoint from T-PIO-05).
  - **Done criterion:** both surfaces list `.pi/` as an allowed root entry with the
    post-trust-executable note; `dadaia public stage && install --target all && doctor`
    exits 0 after projection.
  - **Parallelism:** ai-engineer slot; parallel with T-PIO-05.

---

## Thread B — WS-PI-3 `.pi/` projection (owners: ai-engineer + software-engineer)

- [x] **T-PIO-02** — Author the `public/pi/` source tree.
  - **Owner:** ai-engineer
  - **Write set:** `dadaia_workspace/public/pi/SYSTEM.md`,
    `dadaia_workspace/public/pi/settings.json`,
    `dadaia_workspace/public/pi/prompts/dadaia-context.md` (optional affordance).
  - **Preconditions:** design doc Deliverable 2.1 is the shape source.
  - **Done criterion:** `SYSTEM.md` ≤~50 lines, POINTS AT AGENTS.md (no law restatement),
    names the `dadaia` CLI/lifecycle by reference, carries the inline trust-boundary note;
    `settings.json` is the smallest valid PI-native object, generic only (no operator-local
    values); optional `prompts/dadaia-context.md` adds real affordance or is omitted; no
    private names/paths/IPs anywhere in `public/pi/**`.
  - **Parallelism:** ai-engineer slot; can be authored in parallel with T-PIO-05/06.

- [x] **T-PIO-03** — Wire the `pi` install target (TDD) mirroring OpenCode.
  - **Owner:** software-engineer
  - **Write set:** `dadaia_workspace/infrastructure/public_assets.py` (`_install_pi`,
    `all` targets tuple, install dispatch); `dadaia_workspace/infrastructure/public_assets_common.py`
    (`_VALID_TARGETS` += `"pi"`, `_PI_DIRS = ("prompts",)`); installer unit tests.
  - **Preconditions:** failing test first (`--target pi` copies tree → `.pi/`; `--target
    all` includes `pi`; factory/dispatch total). T-PIO-02 source available (or fixtured).
  - **Done criterion:** `_install_pi` copies `public/pi/` → `.pi/`, writes generated
    `settings.json` via `write_generated`; `"pi"` in `_VALID_TARGETS` and the `all` tuple;
    install dispatch handles `item == "pi"`; idempotent re-install; tests green.
  - **Parallelism:** software-engineer slot (after T-PIO-05 if same owner serializes;
    distinct write set from T-PIO-05 so order is owner-internal).

- [x] **T-PIO-04** — `dadaia public doctor` PI lines + manifest tracking (TDD).
  - **Owner:** software-engineer
  - **Write set:** doctor compare set in `public_assets.py` (PI files);
    `.dadaia/agentic/manifest.json` (via `stage()`, lib-originated); doctor unit tests.
  - **Preconditions:** failing test first asserting `[ok] pi:SYSTEM.md` / `[ok]
    pi:settings.json` emitted; `[drift]`/`[missing]` behave like other targets.
  - **Done criterion:** `public doctor` emits `[ok] pi:` lines and exits 0; `[ok]
    public-privacy` stays green; `.pi/**` projections are manifest-tracked; tests green.
  - **Parallelism:** software-engineer slot, after T-PIO-03.

- [x] **T-PIO-07** — Live `--target pi` projection smoke + clean re-install.
  - **Owner:** software-engineer
  - **Write set:** none beyond running the projection (produces `.pi/` at workspace root —
    a generated projection, NOT a source edit).
  - **Preconditions:** **T-PIO-05 merged** (else gate-blocked); T-PIO-02/03/04 done.
  - **Done criterion:** `dadaia public install --target pi` produces a `.pi/` tree;
    re-running is idempotent (no drift); `dadaia public doctor` exits 0 `[ok] pi:` +
    `[ok] public-privacy`.
  - **Parallelism:** sequenced after T-PIO-05.

---

## Thread D — Drift fixes F1–F12 (owners: product-engineer, ai-engineer, software-engineer)

- [x] **T-PIO-08** — Public-surface drift fixes F6–F8.
  - **Owner:** ai-engineer
  - **Write set:** `public/agents/ai-engineer.md` (F6: "two runtime harnesses" → four + PI
    row + two-layer + PI skill ref); `public/skills/harness-primitives/SKILL.md` (F7:
    4-harness + two-layer + "9 core"); `public/rules/bug-registration-guardrail.md`,
    `public/data/AGENTS.md` (closed-3 runtime enumerations), `public/plugins/sdd-gate.ts`,
    `public/skills/project-orchestration/SKILL.md` (F8: 4-aware or Layer-1-scoped); also
    the `--harness` help text (M-6) if owned here.
  - **Preconditions:** audit F6–F8 are the change source.
  - **Done criterion:** no closed-3-harness framing remains in the listed surfaces (4-aware
    or explicitly Layer-1-scoped); `ai-engineer` persona has a PI row; `dadaia public stage
    && install --target all && doctor` exits 0.
  - **Parallelism:** ai-engineer slot.

- [x] **T-PIO-09** — `lint-memory-atoms.py` heading allowlist (F9, TDD).
  - **Owner:** software-engineer
  - **Write set:** `lint-memory-atoms.py` curated allowlist; its test.
  - **Preconditions:** failing test first — the legitimate WARNing headings no longer WARN.
  - **Done criterion:** allowlist includes the legitimate headings (architecture
    "Multi-harness runtime parity", "Topologia de agentes (9 core + 3 plugins)";
    lifecycle-foundation "Purpose"/"Core services"/"Harness runtime boundary"; etc.); EN/PT
    canon resolved; LINT-1 heading WARNs gone; tests green.
  - **Parallelism:** software-engineer slot.

- [x] **T-PIO-10** — `dadaia memory catalog generate` emits `index.md` (F10/M-4, TDD).
  - **Owner:** software-engineer
  - **Write set:** `dadaia_workspace/features/specs/catalog.py`; its test; close bug
    `specs/bugs/memory-catalog-cli-skips-index-md.md` (disposition at CLOSURE).
  - **Preconditions:** failing test first asserting the CLI writes BOTH `catalog.json` and
    `index.md`.
  - **Done criterion:** `dadaia memory catalog generate` emits `index.md` alongside
    `catalog.json` (parity with the standalone `--index-out` path); tests green; bug ready
    to flip `Closed` at CLOSURE.
  - **Parallelism:** software-engineer slot. **Precedes T-PIO-11.**

- [x] **T-PIO-12** — Memory atom drift fixes F1–F4 (DEFINITION/CLOSURE phase).
  - **Owner:** product-engineer
  - **Write set:** `specs/memory/architecture.md` (F1/D-1/D-2: two-layer section +
    Layer-2 worker table [5 kinds] + scope parity table to Layer-1 + "três runtimes"
    framing); `specs/memory/product/platform/multi-platform-parity.md` (F3/G-2: Layer-2
    worker note + PI post-trust surface); `specs/memory/product/agents/harness-primitives.md`
    (F4: "15 agents" → "9 core" + 4-harness/two-layer).
  - **Preconditions:** ACTIVE.md phase = DEFINITION or CLOSURE (MEMORY gate). Audit F1–F4
    are the change source.
  - **Done criterion:** the two-layer model is documented in `architecture.md` with the
    Layer-2 table; the listed atoms are 4-harness/two-layer aware; `dadaia specs doctor`
    stays 0-error.
  - **Parallelism:** product-engineer slot. (Memory writes require the memory-write phase;
    coordinate with CLOSURE — see T-PIO-16.)

- [x] **T-PIO-13** — product-vision (F2) — gated on operator vision-doc confirmation.
  - **Owner:** product-engineer + operator decision
  - **Write set:** `specs/memory/product/philosophy/product-vision.md`.
  - **Preconditions:** operator confirms `docs/01_medium_codex.md` stance on PI / 4
    harnesses. If unconfirmed, this task is DEFERRED with a recorded reason (does NOT block
    the release; constitution amendment lands independently).
  - **Done criterion:** product-vision carries the two-layer summary + 4-worker reality
    AFTER operator confirmation; OR the task is dispositioned DEFERRED with reason in
    CLOSURE.
  - **Parallelism:** product-engineer slot; operator-gated.

- [x] **T-PIO-14** — `token_estimate` frontmatter refresh (F5).
  - **Owner:** product-engineer
  - **Write set:** frontmatter of `specs/memory/tech-stack.md`,
    `specs/memory/product/.../lifecycle-foundation.md`,
    `specs/memory/product/platform/multi-platform-parity.md`,
    `specs/memory/product/.../spec-context-project.md`.
  - **Preconditions:** memory-write phase.
  - **Done criterion:** `token_estimate` refreshed to computed values; LINT-1 token WARNs
    cleared for these atoms.
  - **Parallelism:** product-engineer slot.

- [x] **T-PIO-11** — Regenerate `index.md` from catalog (F11) — depends on T-PIO-10.
  - **Owner:** product-engineer
  - **Write set:** `specs/memory/product/index.md`.
  - **Preconditions:** **T-PIO-10 done**; memory-write phase.
  - **Done criterion:** `index.md` regenerated via the fixed `dadaia memory catalog
    generate`; the stale lifecycle-foundation row is current; index ↔ catalog in sync.
  - **Parallelism:** product-engineer slot, after T-PIO-10.

---

## Thread E — "no 2 projects" pointer (owner: product-engineer)

- [x] **T-PIO-17** — Deprecation README pointer for `dadaia-pi-workspace`.
  - **Owner:** product-engineer
  - **Write set:** `repos/dadaia-pi-workspace/README.md`.
  - **Preconditions:** none (minimal/ADDITIVE-ish).
  - **Done criterion:** README points at this release + the EPIC (PI now lives in
    dadaia-workspace); the repo is NOT deleted; the `dadaia context` DEAD-mark is noted as
    a CLOSURE/operator follow-up, not done here.
  - **Parallelism:** product-engineer slot; independent.

---

## Global gates & gate ladder

- [x] **T-PIO-15** — Global gates (last implementation task).
  - **Owner:** software-engineer
  - **Preconditions:** T-PIO-01..14, T-PIO-17 done; **T-PIO-05 merged** (live smoke).
  - **Done criterion:** `dadaia ci preflight` 4/4; `lint-imports` 6/0; `dadaia public stage
    && install --target all && public doctor` exit 0 with `[ok] public-privacy` + `[ok]
    pi:`; live `dadaia public install --target pi` smoke producing `.pi/` then a clean
    re-install (idempotent); `dadaia specs doctor` 0 errors.
  - **Parallelism:** terminal; runs after all implementation tasks.

- [x] **T-PIO-16** — CLOSURE: CLOSURE.md + memory finalization + drift RE-AUDIT + archive.
  - **Owner:** product-engineer
  - **Preconditions:** all prior tasks `[x]`; gate ladder (qa-engineer + security-reviewer
    + code-reviewer) APPROVE; commit + push + PR per release-governance.
  - **Write set:** `specs/releases/v0.1.18/CLOSURE.md`; final
    `specs/memory/**` atomic finalization (CLOSURE phase); `specs/releases/ACTIVE.md`.
  - **Done criterion:** CLOSURE.md complete (summary, tasks+SHAs, validations triples,
    drifts, memory updates, **disposition sweep** [bug `memory-catalog-cli-skips-index-md`
    → `Closed`; EPIC WS-PI-3/WS-PI-5 dispositioned; F2/T-PIO-13 disposition recorded],
    backlog returns, archive decision); a memory drift **RE-AUDIT** confirms the PI /
    two-layer surface drift resolved (audit floor-breach cleared); ACTIVE.md set to
    ARCHIVED then `git mv` to `_archive/` (request devops/operator for the `git mv`); the
    `dadaia-pi-workspace` DEAD-mark recorded as an operator follow-up.
  - **Parallelism:** terminal; held for ship.

---

## Task count & per-owner breakdown

- **Total: 17 tasks** (T-PIO-01 … T-PIO-17).
- **product-engineer (7):** T-PIO-01 (constitution), T-PIO-11 (index regen), T-PIO-12
  (memory F1–F4), T-PIO-13 (product-vision F2, operator-gated), T-PIO-14 (token_estimate
  F5), T-PIO-16 (CLOSURE), T-PIO-17 (pi-workspace README).
- **ai-engineer (3):** T-PIO-02 (`public/pi` assets), T-PIO-06 (projected root-law
  surface), T-PIO-08 (public-surface F6–F8).
- **software-engineer (7):** T-PIO-03 (`_install_pi` wiring), T-PIO-04 (doctor + manifest),
  T-PIO-05 (root-whitelist hook), T-PIO-07 (live `--target pi` smoke), T-PIO-09 (lint
  allowlist F9), T-PIO-10 (catalog index.md F10), T-PIO-15 (global gates).

## Sequencing constraints (summary)

- **T-PIO-05 before T-PIO-07** and **before T-PIO-15's live smoke** (root-whitelist gates
  the `.pi/` write).
- **T-PIO-10 before T-PIO-11** (catalog CLI must emit index.md before regen).
- **T-PIO-15 before T-PIO-16** (gates green before CLOSURE).
- **Gate ladder (qa + security + code) before T-PIO-16's `[x]`** and before push/PR.
- Threads A, D-memory, and E are independent of B/C and of each other (disjoint write
  sets) — full per-owner parallelism.
