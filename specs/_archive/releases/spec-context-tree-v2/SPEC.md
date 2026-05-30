# SPEC — Release: spec-context-tree-v2

**Status:** Aprovado
**Release ID:** spec-context-tree-v2
**Owner:** product-engineer
**Opened:** 2026-05-30
**Semver target:** MINOR bump on the current 1.x line (scaffold changes are additive)
**Sequencing:** Release 1 of 2. Release 2 = `spec-context-session-locks-v1` (MAJOR — 2.0.0).

---

## 1. Problem and context

The `dadaia-workspace` library ships a consumer scaffold at
`dadaia_workspace/public/scaffold/` and Jinja templates at
`dadaia_workspace/public/templates/`. When an operator runs `dadaia init` + `dadaia
context create <name>`, the scaffold is copied into the new context's `specs/` directory.

**The current scaffold is behind the canonical layout** that the dadaia-workspace repo
itself already uses. A newly scaffolded consumer repo today receives:

- `specs/foundation/SPEC.md` — a deprecated architectural-notes directory that the SDD
  model no longer recognises.
- `specs/SPEC.md` at the tree root — a pre-release-model artifact; SDD specs now live
  exclusively under `specs/releases/<id>/SPEC.md`.
- `specs/memory/architecture.md` and `specs/memory/tech-stack.md` — Markdown files;
  memory must be HTML (enforced by `dadaia specs doctor` as of `orchestration-
  consolidation-v1`).
- `specs/memory/product.md` — a monolithic Markdown product file; the canonical model is
  a folder catalog at `specs/memory/product/index.html` + per-feature HTML pages.
- No `specs/backlog/`, `specs/bugs/`, or `specs/releases/` directories.
- No `specs/AGENTS.md` (SDD workflow contract for the spec tree).

The `dadaia-workspace` repo itself (the primary context for this workspace) has already
migrated past this layout. The gap is entirely in the **library scaffold** that new
consumer repos receive — no operator running `dadaia init` today gets a tree that passes
`dadaia specs doctor`.

Additionally, the doctor (`features/spec_context/doctor.py`) has no TREE-* invariants
to flag or repair these structural problems. INV-1 through INV-6 guard the ATIVO/INATIVO
state model; none covers the canonical specs/ tree shape.

Finally, the CLI has no commands to create new releases, backlog entries, or bug
stubs — operators create these files manually, leading to inconsistent frontmatter.

This release closes all of the above. It does **not** touch the concurrency, session
binding, or ALIVE/DEAD state model — those belong to Release 2 (`spec-context-session-
locks-v1`).

**Primary source material consumed:**
- PM intake: `.dadaia/reports/dadaia-workspace/project-manager/2026-05-30T000000Z-spec-context-v2-intake.html`
- Architect ADR (9 decisions): `.dadaia/reports/dadaia-workspace/software-architect/2026-05-30T000000Z-adr-spec-context-v2.html`
- QA test strategy: `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-30T120000Z-test-strategy-spec-context-v2.html`
- Original analysis: `.dadaia/reports/dadaia-workspace/spec-context/2026-05-29T000000Z-spec-context-onboarding-and-race-conditions.html`

---

## 2. Objective

Deliver the **canonical `specs/` tree v2** as the new scaffold baseline for all consumer
repos, together with the doctor TREE invariants that enforce and repair it, the CLI
commands that produce conformant artifacts, and a safe migration path for existing
consumer repos.

After this release:

1. A freshly scaffolded consumer workspace passes `dadaia specs doctor` with zero
   violations.
2. A live consumer workspace with the old layout receives TREE-* warnings from doctor
   and can migrate safely via `dadaia migrate tree-v2`.
3. Operators have `dadaia release new`, `dadaia backlog new`, and `dadaia bug new` to
   create conformant artifacts without manual frontmatter authoring.

---

## 3. Scope clusters (T-1 through T-9)

### T-1 — Remove `foundation/` from scaffold; service.py:119 fallback cleanup

**What changes:**
- Delete `dadaia_workspace/public/scaffold/foundation/` and its contents
  (`foundation/SPEC.md`).
- Remove the `"foundation"` entry from the fallback subdirectory list at
  `features/spec_context/service.py:119` (the fallback that runs when `_SCAFFOLD_SRC`
  does not exist).
- Add doctor invariant TREE-1 (see T-9) that warns when an existing consumer repo has a
  `specs/foundation/` directory.

**Migration for existing consumer repos (via `dadaia migrate tree-v2`):**
Move the contents of `specs/foundation/` to `specs/releases/legacy/foundation/` and
remove the now-empty `specs/foundation/` directory.

**Acceptance criteria:**
- AC-T1-1: After scaffolding a new context, `specs/foundation/` does not exist.
- AC-T1-2: `service.py` no longer contains `"foundation"` in its fallback path list.
- AC-T1-3: Doctor TREE-1 fires on a fixture containing `specs/foundation/` and is
  marked `fixable=False` (warn-only; does not auto-delete).
- AC-T1-4: `dadaia migrate tree-v2` idempotently moves `foundation/` content to
  `releases/legacy/foundation/` and removes the empty directory.

---

### T-2 — Scaffold memory as HTML; drop markdown memory files

**What changes:**
- Remove `dadaia_workspace/public/scaffold/memory/architecture.md`,
  `memory/tech-stack.md`, and `memory/product.md`.
- Add scaffold generation that renders from the existing Jinja templates:
  - `dadaia_workspace/public/templates/memory-architecture.html.j2` →
    `scaffold/memory/architecture.html`
  - `dadaia_workspace/public/templates/memory-tech-stack.html.j2` →
    `scaffold/memory/tech-stack.html`
  The rendered scaffold files are committed as static HTML stubs (with placeholder
  content); they are not rendered at `context create` time via Jinja. Jinja rendering
  is done at CLOSURE time by product-engineer.

**Acceptance criteria:**
- AC-T2-1: After scaffolding, `specs/memory/architecture.html` and
  `specs/memory/tech-stack.html` exist as valid HTML files.
- AC-T2-2: After scaffolding, no `*.md` files exist under `specs/memory/` (other than
  any markdown files that belong to subdirs like `backlog/` — those are not memory).
- AC-T2-3: Doctor TREE-3 fires when `memory/architecture.html` or
  `memory/tech-stack.html` is absent and auto-fixes by rendering from the canonical
  template (see T-9).

---

### T-3 — Mandatory `memory/product/index.html`; new CLI `dadaia memory product add <slug>`

**What changes:**
- Add `dadaia_workspace/public/scaffold/memory/product/index.html` rendered from
  `memory-product-index.html.j2` (placeholder catalog, zero features).
- Remove the monolithic `memory/product.md` from the scaffold.
- New CLI subcommand: `dadaia memory product add <slug>` that:
  1. Creates `specs/memory/product/<slug>.html` rendered from
     `memory-product-feature.html.j2` with the given slug.
  2. Regenerates `specs/memory/product/index.html` deterministically from the
     existing feature HTML files in that directory (lexicographic order as the safe
     default; catalog ordering is a product-engineer responsibility — the CLI provides
     the deterministic baseline, not an opinionated order).

**Acceptance criteria:**
- AC-T3-1: After scaffolding, `specs/memory/product/index.html` exists, is valid HTML,
  contains a `<section id="catalog">` element, and has zero feature entries.
- AC-T3-2: `dadaia memory product add payments` creates
  `specs/memory/product/payments.html` from the canonical template and regenerates
  `index.html` so it contains a link to `payments.html`.
- AC-T3-3: Running `dadaia memory product add payments` twice produces the same
  `index.html` content (idempotent index regeneration).
- AC-T3-4: Doctor TREE-3 auto-fix also creates `specs/memory/product/index.html` when
  it is absent.

---

### T-4 — Scaffold `backlog/`, `bugs/`, `releases/` with README and `.gitkeep`

**What changes:**
- Add to `dadaia_workspace/public/scaffold/`:
  - `backlog/README.md` — authoring rules for backlog entries
  - `backlog/.gitkeep`
  - `bugs/README.md` — authoring rules for bug reports
  - `bugs/.gitkeep`
  - `releases/README.md` — authoring rules for release directories
  - `releases/.gitkeep`

**Acceptance criteria:**
- AC-T4-1: After scaffolding, `specs/backlog/`, `specs/bugs/`, and `specs/releases/`
  exist and each contains a `README.md` and a `.gitkeep`.
- AC-T4-2: Doctor TREE-4 fires when any of these three directories is absent and
  auto-fixes by creating the directory with `README.md` and `.gitkeep`.
- AC-T4-3: Doctor TREE-4 does not recreate directories that already exist.

---

### T-5 — New template `specs/AGENTS.md` (SDD workflow contract for the spec tree)

**What changes:**
- Add `dadaia_workspace/public/templates/specs-AGENTS.md` — a new canonical template
  describing the SDD workflow contract for operators and agents reading the spec tree.
  This file is DISTINCT from the repo-root `AGENTS.md` (which describes agents for the
  whole workspace and is lib-originated).
- Add `dadaia_workspace/public/scaffold/AGENTS.md` as the scaffolded version rendered
  from the template.
- Doctor TREE-5: detect when `specs/AGENTS.md` is absent OR when its content hash
  differs from the canonical template hash (drift detection). TREE-5 is warn-only with
  merge suggestion — it does NOT auto-overwrite a user-customised AGENTS.md.

**Acceptance criteria:**
- AC-T5-1: After scaffolding, `specs/AGENTS.md` exists and its content matches the
  canonical template.
- AC-T5-2: Doctor TREE-5 fires when `specs/AGENTS.md` is absent.
- AC-T5-3: Doctor TREE-5 fires (as a drift warning) when `specs/AGENTS.md` exists but
  its SHA-256 hash differs from the canonical template hash.
- AC-T5-4: `doctor --fix` on a TREE-5 violation does NOT overwrite a user-customised
  `specs/AGENTS.md`; it prints the diff and a merge suggestion.
- AC-T5-5: `specs/AGENTS.md` is distinct in content and purpose from the repo-root
  `AGENTS.md` (does not duplicate agent role definitions from that file).

---

### T-6 — Deprecate root `specs/SPEC.md`; remove from scaffold; doctor warn + migrate auto-fix

**What changes:**
- Remove `dadaia_workspace/public/scaffold/SPEC.md`.
- Doctor TREE-2: warn when `specs/SPEC.md` exists at the tree root.
- `dadaia migrate tree-v2` auto-fix: move `specs/SPEC.md` to
  `specs/releases/legacy/SPEC.md` (preserves content; changes location).

**Acceptance criteria:**
- AC-T6-1: After scaffolding a new context, `specs/SPEC.md` does not exist.
- AC-T6-2: Doctor TREE-2 fires when `specs/SPEC.md` exists at the root.
- AC-T6-3: TREE-2 is marked `fixable=False` in the initial release (warn-only; requires
  explicit migrate). `doctor --fix` does NOT move the file automatically.
- AC-T6-4: `dadaia migrate tree-v2` moves `specs/SPEC.md` to
  `specs/releases/legacy/SPEC.md` atomically (or to `specs/releases/legacy/` if the
  file already exists at the target, appending a timestamp suffix to avoid clobbering).

---

### T-7 — New CLI: `dadaia release new <id>`, `dadaia backlog new <slug>`, `dadaia bug new <slug>`

**What changes:**
- `dadaia release new <id>`: creates `specs/releases/<id>/` and writes `SPEC.md` stub
  with canonical frontmatter (Status: Draft, Release ID, Owner, Opened date).
  Validates that `<id>` matches `^[a-z][a-z0-9-]+$`.
- `dadaia backlog new <slug>`: creates `specs/backlog/<slug>.md` with a canonical
  frontmatter stub (title, status: idea, opened date, description placeholder).
- `dadaia bug new <slug>`: creates `specs/bugs/<slug>.md` with a canonical frontmatter
  stub (title, severity: TBD, opened date, description placeholder, session_id: null).

**Important — bound-only enforcement boundary:**
The full enforcement that `dadaia bug new` is blocked when no session is bound
(`DADAIA_SESSION_ID` absent) is a Release 2 feature (requires session binding from
`spec-context-session-locks-v1`). In R1, `dadaia bug new` creates the file and writes
the frontmatter with `session_id: null` but does NOT block execution if no session is
bound. The deterministic BLOCK on unbound sessions is explicitly deferred to R2.

**Acceptance criteria:**
- AC-T7-1: `dadaia release new my-feature-v1` creates
  `specs/releases/my-feature-v1/SPEC.md` with `Status: Draft` and all required
  frontmatter fields.
- AC-T7-2: `dadaia release new my-feature-v1` with an existing directory exits non-zero
  with an informative error (no clobber).
- AC-T7-3: `dadaia backlog new cool-idea` creates `specs/backlog/cool-idea.md` with
  canonical frontmatter.
- AC-T7-4: `dadaia bug new login-crash` creates `specs/bugs/login-crash.md` with
  `session_id: null` in frontmatter regardless of session binding state.
- AC-T7-5: `dadaia release new "INVALID NAME"` exits non-zero with a slug validation
  error.

---

### T-8a — Per-release SDD gate: remove legacy root-TASKS.md search path (R1 portion)

**Context:** The full per-release gate resolution (resolving the active release from the
implementation lock rather than from `ACTIVE.md`) is a Release 2 deliverable, completed
as part of T-13 (the new RULE E in `sdd-spec-gate.sh`). See architect ADR D-6 and D-9.

**What changes in R1 (T-8a only):**
- Remove any fallback in `dadaia_workspace/public/scripts/sdd-spec-gate.sh` that looks
  for `TASKS.md` at the spec tree root (i.e., a path like
  `$PRIMARY_SPECS/TASKS.md`). This legacy path predates the release-directory model.
  The gate must only search in `$PRIMARY_SPECS/releases/<active-release-id>/TASKS.md`
  (already implemented; this task removes the legacy fallback).
- Do NOT change the gate's primary context resolution logic (still reads
  `primary_context.json`). That changes in R2/T-13.

**Cross-reference note (required):** T-8a is the first half of T-8 from the architect
ADR D-9. T-13 in R2 (`spec-context-session-locks-v1`) completes T-8 by rewriting the
gate's context resolution to use the implementation lock. The TASKS.md for R2 must
reference T-8a as a prerequisite of T-13 (per architect D-9).

**Acceptance criteria:**
- AC-T8a-1: `sdd-spec-gate.sh` contains no reference to a root-level `TASKS.md` path
  (e.g., no `$PRIMARY_SPECS/TASKS.md` pattern; only `releases/<id>/TASKS.md`).
- AC-T8a-2: Existing gate integration tests continue to pass after this change.
- AC-T8a-3: New gate test `test_gate_resolves_active_release_tasks` passes (gate
  reads `releases/ACTIVE.md` → `releases/<id>/TASKS.md` and allows when `[-]` present).
- AC-T8a-4: New gate test `test_gate_blocks_when_active_release_has_no_task` passes
  (gate blocks when no `[-]` marker in the active release's TASKS.md).

---

### T-9 — Doctor TREE-1 through TREE-7 invariants

**What changes:**
New `TreeDoctorService` (or extension of `DoctorService`) implementing seven invariants:

| Invariant | Trigger | Auto-fix policy |
|-----------|---------|-----------------|
| TREE-1 | `specs/foundation/` exists | WARN-ONLY: report, do not move. Requires `dadaia migrate tree-v2`. |
| TREE-2 | `specs/SPEC.md` exists at tree root | WARN-ONLY: report, do not move. Requires `dadaia migrate tree-v2`. |
| TREE-3 | `memory/architecture.html` or `memory/tech-stack.html` or `memory/product/index.html` absent | AUTO-FIX: render from canonical Jinja templates. |
| TREE-4 | `backlog/`, `bugs/`, or `releases/` absent | AUTO-FIX: create directory with `README.md` and `.gitkeep`. |
| TREE-5 | `specs/AGENTS.md` absent or hash differs from canonical template | DRIFT-DETECT: warn + show diff; no auto-overwrite. |
| TREE-6 | A `releases/<id>/` directory missing a mandatory SDD artifact given its phase (e.g. `PLAN.md` absent when phase is IMPLEMENTATION) | NO AUTO-FIX: report; do not create unapproved artifacts. |
| TREE-7 | A `bugs/<slug>.md` missing the required `session_id` frontmatter field | NO AUTO-FIX: report; human review required. |

**Rationale for fix policies:**
- TREE-1 and TREE-2 are warn-only because `foundation/` and root `SPEC.md` may contain
  SDD-approved content; auto-moving would reclassify approved content without operator
  consent.
- TREE-3 and TREE-4 are auto-fixable because they create missing structural artifacts
  (templates + empty directories) — no existing content is destroyed or reclassified.
- TREE-5 drift-detection is warn-only because user customisation of `AGENTS.md` is
  expected; silent overwrite would destroy operator work.
- TREE-6 and TREE-7 require human review: creating an empty `PLAN.md` would produce an
  unapproved artifact; backdating or injecting a `session_id` would falsify authorship.

**QA test contract (per QA strategy §5):**
14 minimum tests: 2 per invariant (violating fixture confirms `doctor.check()` returns
the invariant code; fixed/warn fixture confirms the expected post-fix filesystem state
or the no-auto-fix guarantee). All tests are end-to-end on a real `tmp_path` filesystem.

**Acceptance criteria:**
- AC-T9-1 through AC-T9-14: Each TREE-N invariant has exactly two tests: one that
  asserts the invariant code appears in `doctor.check()` output for a violating fixture;
  one that asserts the expected post-`doctor.fix()` state (or the guarantee that auto-fix
  did NOT modify files, for warn-only invariants).
- AC-T9-15: `dadaia doctor` exits 0 on a freshly scaffolded workspace (all seven TREE
  invariants pass).
- AC-T9-16: `dadaia doctor` exits 0 on the dadaia-workspace repo itself (which is ahead
  of the new scaffold and must not trigger TREE warnings).

---

## 4. Migration — `dadaia migrate tree-v2`

**Command:** `dadaia migrate tree-v2 [--dry-run] [--yes]`

**Scope:** Scaffold-level migration only (moves legacy directories/files). This command
is NOT the same as `dadaia migrate` (state-file migration from spec_contexts.json v1→v2,
which belongs to Release 2). They are separate subcommands of `dadaia migrate`.

**Actions performed by `dadaia migrate tree-v2`:**
1. If `specs/foundation/` exists: move its contents to
   `specs/releases/legacy/foundation/` (creating `releases/legacy/` if needed); remove
   the now-empty `specs/foundation/` directory.
2. If `specs/SPEC.md` exists at root: move to `specs/releases/legacy/SPEC.md` (or add
   timestamp suffix if the destination already exists).
3. If `specs/memory/*.md` files exist (Markdown memory): report them for operator
   review; do NOT auto-convert (conversion is product-engineer's responsibility as it
   involves content judgment).

**Properties:**
- `--dry-run`: print what would be done without writing.
- `--yes`: skip interactive confirmation.
- Idempotent: running twice is safe (if `releases/legacy/foundation/` already exists,
  the command no-ops step 1).
- Explicit consent: without `--yes`, the command prints a diff-like summary and asks
  for confirmation before any destructive operation.

**Loud guard:** When `dadaia doctor` (or any `dadaia context` command) detects the old
layout (TREE-1 or TREE-2 firing), it prints a prominent warning:

```
[TREE MIGRATION REQUIRED]
  specs/foundation/ detected (TREE-1). Run: dadaia migrate tree-v2
  specs/SPEC.md detected at root (TREE-2). Run: dadaia migrate tree-v2
```

This prompt appears regardless of whether `--fix` is passed.

**Versioning note (architect D-8):** R1 is a MINOR version bump (1.x → 1.(x+1).0).
The scaffold changes are additive from a consumer perspective. The MAJOR break (2.0.0)
belongs to R2 (`spec-context-session-locks-v1`), which removes `ATIVO/INATIVO` and
`primary_context.json`. The `dadaia migrate tree-v2` command in R1 does not touch
`spec_contexts.json`.

---

## 5. Architecture deltas

All architecture deltas in this release are confined to the library source at
`repos/dadaia-workspace/dadaia_workspace/`. No changes to `.dadaia/` state files,
`spec_contexts.json` schema, or the `ContextState` enum. The `primary_context.json` file
continues to be written and read by the gate (no change until R2).

| Layer | What changes |
|-------|-------------|
| `public/scaffold/` | Remove `foundation/`, `SPEC.md`, `memory/*.md`; add `backlog/`, `bugs/`, `releases/`, `memory/product/`, `AGENTS.md` |
| `public/templates/` | Add `specs-AGENTS.md` template |
| `features/spec_context/doctor.py` | Add TREE-1..TREE-7 invariants (extend `DoctorService` or introduce `TreeDoctorService`) |
| `features/spec_context/service.py` | Remove `"foundation"` from fallback scaffold path list (line 119) |
| `cli/commands/` | Add `memory product add`, `release new`, `backlog new`, `bug new`, `migrate tree-v2` subcommands |
| `public/scripts/sdd-spec-gate.sh` | Remove legacy root-TASKS.md fallback path |

No changes to:
- `core/models/spec_context.py` (ContextState enum unchanged — that is R2)
- `infrastructure/json_context_store.py` (no locking changes — that is R2)
- `features/spec_context/service.py` beyond the line-119 fallback removal
- `.dadaia/states/` files
- Any hook scripts beyond the gate cleanup in T-8a

---

## 6. Tech-stack deltas

None. All implementation is in Python (existing stack) and Bash (existing gate script).
No new dependencies are introduced. The Jinja2 rendering used by `dadaia public stage`
is already a project dependency; `dadaia migrate tree-v2` and `dadaia memory product add`
reuse it.

---

## 7. Acceptance criteria summary

The following is the consolidated AC list, grouped by test category, for use in PLAN
and TASKS authoring. ACs are traceable to QA strategy sections (§5 for TREE tests, §4.2
for gate tests, §9 of original report for onboarding flow).

### 7.1 Scaffold correctness (fresh `dadaia init → context create`)
- AC-S-1: `specs/foundation/` absent after scaffold.
- AC-S-2: `specs/SPEC.md` absent at root after scaffold.
- AC-S-3: `specs/memory/architecture.html` present and valid HTML.
- AC-S-4: `specs/memory/tech-stack.html` present and valid HTML.
- AC-S-5: `specs/memory/product/index.html` present, valid HTML, zero feature entries.
- AC-S-6: `specs/backlog/`, `specs/bugs/`, `specs/releases/` present with `README.md` and `.gitkeep`.
- AC-S-7: `specs/AGENTS.md` present with content matching canonical template.
- AC-S-8: `dadaia specs doctor` exits 0 on freshly scaffolded workspace.

### 7.2 Migration (`dadaia migrate tree-v2`)
- AC-M-1: `--dry-run` prints what would change without writing.
- AC-M-2: `foundation/` content moved to `releases/legacy/foundation/`; `foundation/` removed.
- AC-M-3: Root `SPEC.md` moved to `releases/legacy/SPEC.md`.
- AC-M-4: Command is idempotent (running twice is safe).
- AC-M-5: Without `--yes`, command asks for confirmation before any write.

### 7.3 CLI commands
- AC-C-1 through AC-C-5: Per AC-T7-1..AC-T7-5 (release new, backlog new, bug new).
- AC-C-6: `dadaia memory product add <slug>` creates feature HTML + regenerates index.
- AC-C-7: `dadaia memory product add <slug>` is idempotent on index regeneration.

### 7.4 Doctor TREE invariants (14 tests per QA strategy §5)
- AC-D-1 through AC-D-14: 2 tests per invariant (TREE-1..TREE-7): violating fixture
  detected + expected post-fix state verified.
- AC-D-15: `dadaia doctor` exits 0 on fresh scaffold.
- AC-D-16: `dadaia doctor` exits 0 on dadaia-workspace repo itself.

### 7.5 Gate (T-8a)
- AC-G-1: Gate contains no root-TASKS.md fallback path.
- AC-G-2 through AC-G-8: Per QA strategy §4.2 table (7 new gate behavior tests).

### 7.6 Onboarding end-to-end
- AC-O-1: `dadaia init → dadaia context create my-project → dadaia context activate
  my-project` produces a fully canonical `specs/` tree that passes `dadaia specs doctor`
  without any manual intervention (per original report §9 onboarding flow).

---

## 8. Out of scope

### 8.1 All of Thrust B (Release 2 — `spec-context-session-locks-v1`)
The following are explicitly deferred to Release 2 and must not appear in R1
implementation:
- ALIVE/DEAD state model (replacing ATIVO/INATIVO).
- Removal of `is_primary` field and `primary_context.json`.
- Session binding (`dadaia context bind --mode`), session files, `DADAIA_SESSION_ID`.
- Workspace-wide fcntl lock and per-context file lock.
- Per-release implementation lock (`dadaia/locks/implementation/`).
- Heartbeat, TTL, and audited reclaim.
- New CLI verbs: `context alive`, `context dead`, `context bind`, `context release`.
- `dadaia migrate` (state-file migration for `spec_contexts.json` v1→v2).
- RULE E in `sdd-spec-gate.sh` (session/lock enforcement).
- `sdd-post-gate.sh` (new post-tool hook).
- Doctor LOCK-1..LOCK-5 invariants.
- `2.0.0` semver MAJOR — stays in R2.

### 8.2 `bugs/` bound-only enforcement
The block that prevents `dadaia bug new` when no session is bound
(`DADAIA_SESSION_ID` absent) is deferred to R2. In R1, the command creates the file
with `session_id: null` unconditionally.

### 8.3 Per-release gate lock-based resolution (T-8 full)
T-8a in R1 removes the legacy root-TASKS.md fallback. The full T-8 resolution —
rewriting the gate to resolve the active release from the implementation lock rather
than from `ACTIVE.md` — is T-13 in R2 (per architect ADR D-9).

### 8.4 Race condition remediation
Race conditions R-1 through R-10 (identified in the original analysis report) are
architectural in nature and require the R2 locking mechanisms. R1 does not address
any of them. The QA strategy mandates that the deterministic race reproduction tests
ship as `@pytest.mark.xfail(strict=True)` in R1 — they document the known bugs and
automatically promote to green regression guards when R2 fixes them.

---

## 9. Open questions

The following open questions were identified during SPEC authoring. Items marked
**[RESOLVED]** have been answered by the operator or specialist reports. Items marked
**[OPEN]** require operator confirmation before PLAN can be written.

### OQ-1 — Versioning bump [RESOLVED]
**Question:** Should R1 be a MINOR or PATCH version bump?
**Resolution:** MINOR (operator confirmed via PM intake, Q-1 resolution and ADR D-8).
Rationale: the scaffold changes are additive for new consumers; existing consumers get
doctor warnings but no breakage.

### OQ-2 — Migration consent model [RESOLVED]
**Question:** Should `dadaia doctor --fix` auto-move `foundation/` and root `SPEC.md`,
or require an explicit migrate command?
**Resolution:** Warn-only for TREE-1 and TREE-2; explicit `dadaia migrate tree-v2`
required for destructive moves (operator confirmed via PM intake Q-6, QA strategy §5).

### OQ-3 — T-8a scope boundary [RESOLVED]
**Question:** Does removing the legacy root-TASKS.md path risk breaking any existing
consumer that still has the old tree layout?
**Resolution:** No. The legacy root-TASKS.md fallback was only used before the
release-directory model existed. Any consumer running the current library version has
`releases/ACTIVE.md` and `releases/<id>/TASKS.md`. The fallback has been dead code
since the release-directory gate was introduced (ADR D-9 confirms this).

### OQ-4 — Scaffold rendered vs. static HTML [RESOLVED]
**Question:** Should the scaffold ship static pre-rendered HTML (committed to
`public/scaffold/memory/`) or should `dadaia context create` render the Jinja templates
at creation time?
**Resolution:** Static pre-rendered HTML committed to the scaffold (operator confirmed via
grill-me 2026-05-30). Rationale: simpler; no Jinja dependency at `context create` time;
`dadaia public stage` re-renders the statics. PLAN must keep `context create` a pure copy
(no render step). Affects the staging pipeline only.

### OQ-5 — `dadaia memory product add` index ordering [RESOLVED]
**Question:** What order should the regenerated `index.html` catalog use?
**Resolution:** Lexicographic order as the deterministic default (per T-3 spec above).
Product-engineer is responsible for manual reordering to reflect daily-relevance order
at CLOSURE time. The CLI provides a safe, reproducible baseline.

---

## 10. Dependencies and risks

### 10.1 Dependencies
- **go-open-source** (currently IMPLEMENTATION): R1 may not enter IMPLEMENTATION until
  `go-open-source` is CLOSED and `ACTIVE.md` is freed. SPEC and PLAN authoring are
  unblocked (PE writes to the new release directory only — disjoint). Implementation
  starts after `go-open-source` closes.
- **R1 is a prerequisite for R2**: T-10 in `spec-context-session-locks-v1` depends on
  the canonical `releases/` directory structure introduced in T-4. The `context bind`
  command (R2) creates lock files in the `releases/` tree; that tree must exist in the
  scaffold before R2 ships.
- **`dadaia public stage`**: After any change to `public/scaffold/` or
  `public/templates/`, `dadaia public stage && dadaia public install --target all` must
  be run. This is a devops-engineer action.

### 10.2 Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `dadaia migrate tree-v2` moves approved content without operator awareness | Low (requires explicit command + confirmation) | High | Warn-only TREE-1/TREE-2; require `--yes` in migrate |
| Gate change in T-8a breaks existing consumers | Very low (legacy path is dead code) | High | Gate integration tests (AC-G-2..G-8) gate the PR |
| Static scaffold HTML diverges from templates over time | Medium | Medium | `dadaia specs doctor` TREE-3 and TREE-5 detect this; doctor run in CI |
| OQ-4 resolution (static vs. dynamic rendering) delays T-2/T-3 implementation | Low | Low | Confirm in PLAN before implementation starts |

---

## 11. Concurrency note

This release is disjoint from `go-open-source`:
- R1 writes only to: `repos/dadaia-workspace/specs/releases/spec-context-tree-v2/` (this
  SPEC and future PLAN/TASKS), `dadaia_workspace/public/scaffold/`,
  `dadaia_workspace/public/templates/`, `dadaia_workspace/features/spec_context/`,
  `dadaia_workspace/cli/`, and `dadaia_workspace/public/scripts/sdd-spec-gate.sh`.
- `go-open-source` has completed all code changes (T-GOS-OPS1 is an operator action
  with no file writes). There is zero write-set overlap.

No file modified in R1's scope is touched by `go-open-source`. Parallel SPEC authoring
is safe. Implementation must wait until `go-open-source` closes and `ACTIVE.md` is freed.

---

## 12. Suggested implementer surfaces (informational — not binding until PLAN)

| Work area | Suggested agent |
|-----------|----------------|
| Scaffold changes, Jinja template wiring, CLI commands (T-1..T-7), doctor TREE invariants (T-9), migrate command | `software-engineer-python` |
| Gate cleanup (T-8a) | `software-engineer-python` (the gate is a bash script in `public/scripts/`; SE-Python owns the public scripts layer) |
| `dadaia public stage && dadaia public install` after scaffold changes | `devops-engineer` |
| TREE invariant tests (AC-D-1..D-16), gate tests (AC-G-1..G-8), onboarding E2E (AC-O-1) | `qa-engineer` |

---

*Product Engineer — dadaia-workspace | 2026-05-30*
