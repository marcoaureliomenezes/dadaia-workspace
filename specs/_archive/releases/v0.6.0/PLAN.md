# PLAN — Release v0.6.0 — Gitflow standardization

**Status:** Aprovado
**Release ID:** v0.6.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.6.0/SPEC.md`
**Grill:** `specs/releases/v0.6.0/GRILL.md`
**Branch:** `feature/v0.6.0` (cut from `develop`)

> Supersedes the untracked 2026-08-11 PLAN of the same release id (test runtime efficiency),
> whose scope was consumed by the bug flow the same day.

## 1. Planning problem

This release changes **governance text and one enforcement point**. That shape produces
three planning risks that are not the usual ones.

**The law is a projected, PROTECTED, `0444` artifact.** `DADAIA.md` exists in five places:
the source (`dadaia_workspace/public/data/DADAIA.md`) and four read-only projections. Only
the source is editable, and only the projection chain may produce the other four. An agent
that "fixes" a projection produces exactly the drift the file exists to prevent, and
`public doctor` will call it. So **every text task ends in a projection step**, not before.

**A dedup pass can silently delete a rule.** FR3 removes restatements from ten surfaces.
The failure mode is not a merge conflict — it is a rule that existed in a restatement, was
deleted as duplicate, and was never actually present in the new single home. The defence is
mechanical and stated as acceptance A2.3: after the pass, every occurrence of the four
branch-pattern literals under `public/` must resolve to the skill, to the law, or to a
reference. Relocation is provable; deletion is visible.

**This release is enforced by the thing it is changing.** The chokepoint being rewritten
(FR4) is the same chokepoint that will gate this release's own push, and the required check
being added (FR5) is the same check that will gate its own PR. Both need explicit ordering,
or the release locks itself out. Hence: `pr-source-guard` becomes *required* only after the
first merge (R2), and FR4's tests must prove the develop path **allowed** as carefully as
they prove the other paths refused.

One more property is deliberate: **this release ships by its own rules from the first
commit**. `feature/v0.6.0` is cut from `develop`, the definition trio merges at milestone
(a), and both milestones carry the diff-based security review and the `develop` push. If
the model cannot carry its own release, it is the wrong model — and we would rather learn
that in this release than in the next one.

## 2. Execution lanes

### Lane A — The law and its single home (FR1 + FR2 + FR7 text)

**Owner:** ai-engineer. **Write set:** `dadaia_workspace/public/data/DADAIA.md`;
`dadaia_workspace/public/skills/dadaia-gitflow/SKILL.md` (new).

1. **Write the skill first, then the law.** Counterintuitive but correct: the skill is the
   operational home, and the law's §5/§6 must be written *as a pointer to it*. Writing the
   law first produces a law that restates what the skill will say — the exact defect FR3
   exists to remove. The skill carries the four-branch table, the seven-row stage table
   (branch / commit cadence / merge target / push trigger), the two milestones with their
   mandatory post-merge sequence, the hotfix PATCH-mint rule, and an explicit
   mechanical-vs-discipline split naming the FR4/FR5 mechanisms. Budget: **≤ 150 lines**.
2. **Rewrite `DADAIA.md` §5/§6** to state the six law-level items (SPEC FR1.1–FR1.6) once
   each, with the operational detail delegated. Measure the file's always-on token count
   **before** the edit and after — the cap is +400 tokens (A1.4), and the number is
   reported either way. The law is the always-on prefix of every session; growth here is
   paid by every turn in the workspace forever.
3. **Project and verify.** `dadaia public stage` → `dadaia public install --target all` →
   `dadaia public doctor`. Required outcome: `[ok] public-privacy`, zero drift, four
   `0444` byte-identical copies of `DADAIA.md`, and `dadaia-gitflow` present under
   `.claude/skills/`, `.agents/skills/`, `.codex/`, `.kimi-code/`.

**Verification gate:** A1.1–A1.4 and A2.1–A2.4 met; `public doctor` green; the token
before/after pair recorded.

### Lane B — Tier-2 dedup and hygiene (FR3 + FR6)

**Owner:** ai-engineer. **Precondition:** Lane A `[x]` — there is nothing to defer to until
the skill exists. **Write set:** ten `public/` surfaces (four skills, six agents) plus the
four hygiene sites.

4. **The ten deferrals**, in one pass per file: `project-orchestration` (cadence table,
   `feature/{version}`), `dadaia-task-manager`, `dadaia-release-closure` (finalization order
   → **memory → CLOSURE → archive**), `dadaia-release-definition`, `product-engineer`
   (**hotfix section rewritten**, ceremony deleted), `security-reviewer` (push-gate
   `scan_target` diff-only; `full` only in the audit lane), `code-reviewer` (PR base
   `develop` → `main`), and the forbidden-action lists of `project-manager`,
   `software-engineer`, `qa-engineer`, `ai-engineer`.
   **`product-engineer.md` is the delicate one:** it currently carries a whole hotfix
   *release* lifecycle with a template, a status ladder, a scaffolding command and a
   condensed 7-phase flow. All of it is revoked (D4). The rewrite must say so **explicitly**
   — a reader of the old law must find the revocation, not silence (A3.2).
5. **The four hygiene sites**, same pass because they are the same files and the same
   subject: the 4 `release-governance` citations → `DADAIA.md` §5 or the new skill; the
   constitution §11/§13 gap → **one** uniform resolution (add the sections, or re-anchor
   every citation — never a mix, A6.2); `scaffold/releases/README.md:20` regex → the
   `^v\d+\.\d+\.\d+$` canon plus the v2 `ACTIVE.md` block with `segment:`;
   `ai-engineer.md:102/349` → the real `public/scripts/` inventory (5 files, 3 shell).
   Note: two of the four citation sites are **Python** (`features/specs/doctor_closure_audit.py:286`,
   `features/backlog/doctor.py:56`) — comment-only edits, but they are package files, so
   they belong to software-engineer's write set, not ai-engineer's. Split accordingly.
6. **Prove relocation, not deletion.** Run the A2.3 grep over
   `dadaia_workspace/public/`: every hit on the four branch-pattern literals must be inside
   `dadaia-gitflow/SKILL.md`, inside `DADAIA.md` §5/§6, or a reference to the skill. Any
   other hit is either a missed restatement or a rule with no home — both are stop
   conditions.
7. **Re-project** (same chain as step 3) and confirm no agent frontmatter allowlist widened
   (A3.5, diff-read).

**Verification gate:** A3.1–A3.5, A6.1–A6.5 met; `dadaia public doctor` and
`dadaia specs doctor` both exit 0.

### Lane C — Mechanical enforcement, TDD (FR4)

**Owner:** software-engineer. **Parallel-safe with Lane B** — disjoint write set (package
code + tests vs `public/` text), with the two Python comment sites from step 5 assigned
here to keep it disjoint.

8. **RED first, and prove it RED.** Write the contract tests before the implementation, in
   `tests/contract/` / `tests/unit/features/chokepoints/`, covering all seven cases of
   A4.1: `refs/heads/main` refused; `refs/heads/feature/v0.6.0` refused; `develop` with a
   covering APPROVED handoff allowed; `develop` with no covering handoff refused; tag push
   allowed (**the carve-out that keeps publishing alive**); `bugfix/*` name refused; each of
   the four permitted patterns accepted. Capture the failing output — **A4.4 requires the
   RED evidence in CLOSURE.** A test that never failed proves nothing, and this is a gate
   whose false-negative would be invisible.
9. **Implement at the natural seam.** `PushRef.local_ref` is parsed at
   `features/chokepoints/service.py:69` and read nowhere; that is the insertion point named
   by the backlog entry. Add (i) the develop-only ref policy, (ii) the four-pattern
   branch-name validator, (iii) the develop-diff-keyed verdict replacing the bare per-ref
   sha match in `push_gate_decision` (`:229-259`), and wire through
   `cli/commands/ci.py::push_gate_check` (`:227-244`). Every refusal message names the rule,
   the permitted value and the corrective action (A4.2) — a gate that refuses without
   telling you how to comply is a worse gate than none.
10. **Preserve what already works.** The CI preflight ladder (`ruff format --check`,
    `ruff check`, `mypy --strict`, `pytest`) is copied through verbatim (A4.5); the tag
    carve-out is untouched. This release adds a rule; it loosens nothing.
11. **Green the quality ladder:** full suite, `mypy --strict`, ruff, and
    `lint-imports --config setup.cfg --no-cache` (0 broken).

**Verification gate:** A4.1–A4.5 met; RED evidence captured; a **live demonstration** on
this instance that a `main` push and a `feature/*` push are actually refused by the
installed hook — the test suite proves the function, the demonstration proves the wiring.

### Lane D — CI and GitHub (FR5)

**Owner:** software-engineer. **Precondition:** Lane C `[x]` (the chokepoint and the CI
check must agree on the same four patterns).

12. **`pr-source-guard`** job in `.github/workflows/ci.yml`: on `pull_request` to `main`,
    fail when `head.ref != 'develop'`, with an error naming the rule. Demonstrate the
    failure once on a scratch PR and record the run URL (A5.1) — an untested guard is a
    guard nobody trusts.
13. **Retire the `feature/**` and `hotfix/v*` push triggers** (`ci.yml:5-9`) and the
    now-unreachable push-triggered `hotfix-branch-name` job (`:403-418`). Its PATCH≥1
    pattern knowledge moves to Lane C's validator, which runs at the boundary that actually
    exists. Confirm no job is left with an `if:` that can never be true (A5.3).
14. **Required check, after the first merge only.** Flip `pr-source-guard` into `main`'s
    required checks **after** this release's PR merges (R2). Sequencing recorded in CLOSURE
    (A5.4).

**Verification gate:** A5.1–A5.5; every CI job green on `develop` after the milestone-(b)
push.

### Lane E — QA `alpha-1`

**Owner:** qa-engineer. **Precondition:** Lanes A–D `[x]`.

15. Validate the whole contract on this **live instance**, not from the diff: the four
    projections' bytes and modes; the skill present in all four projection roots; the
    refusal of a `main` push and of a `feature/*` push by the installed hook; the acceptance
    of a `develop` push with a covering verdict; `pr-source-guard`'s red run and green run;
    `dadaia doctor` / `specs doctor` / `public doctor` all exit 0; the full quality ladder.
16. Re-run the A2.3 relocation grep independently. A dedup pass audited only by its own
    author is not audited.
17. Commit the `alpha-1` review to the branch (per the segment protocol).

**Verification gate:** SPEC §7 items 1–6 verified, each with its evidence. Any target missed
is reported as a finding with its evidence, never rounded into a pass.

### Lane F — Ship and close

**Owner:** code-reviewer + security-reviewer (verdicts), software-engineer (merge/push/PR),
product-engineer (closure).

18. Six-axis code review. Security review is **diff-based on `origin/develop..develop`** —
    this release's own rule, applied to itself. Surfaces that matter: the new refusal logic
    (can it be bypassed? does it fail open?), the CI job (no injection through
    `head.ref` interpolation), and the fact that the release edits its own gate.
19. **Milestone (b):** merge `feature/v0.6.0` → local `develop`, diff security review,
    APPROVED handoff, push `develop`, watch CI to green on **every** job, PR `develop` →
    `main`, merge.
20. **CLOSURE in the mandated order: memory update → CLOSURE.md → archive** (D5).
    `ACTIVE.md` phase set to `CLOSURE` **before** any memory write — the memory gate is
    phase-classed. Then the disposition sweep, then the `git mv`.

## 3. Sequencing

```
Lane A (skill, then law, then project)
   │
   ├──▶ Lane B (tier-2 dedup + hygiene, re-project) ──┐
   │                                                   │
   └──▶ Lane C (chokepoint TDD) ──▶ Lane D (CI) ───────┼──▶ Lane E (QA alpha-1) ──▶ Lane F (ship, close)
                                                       │
        (B and C are genuinely parallel: disjoint write sets)
```

- **A before everything** — nothing can defer to a skill that does not exist.
- **B ∥ C** — B writes `public/**` text, C writes `dadaia_workspace/features|cli/**` +
  `tests/**`. The two Python comment sites from FR6.1 are assigned to C to keep the split
  clean.
- **C before D** — the hook and the CI check must encode the same four patterns; writing D
  first risks two sources of truth for the pattern set.
- **Milestone (a) fires between the trio approval and Lane A** — the definition is on
  `develop`, reviewed and pushed, before implementation begins. That is D3, and it is why
  ACTIVE.md moves to IMPLEMENTATION with the trio already `Aprovado`.

## 4. Risk points

**The PROTECTED law file (R1).** `DADAIA.md` is `0444` in four projections. Edit **only**
`dadaia_workspace/public/data/DADAIA.md`; produce the other four **only** via
`public stage` + `public install --target all`; prove it with `public doctor` reporting zero
drift and four byte-identical `0444` copies. Hand-editing a projection to make a doctor pass
is the drift this workspace exists to eliminate — and it is also a gate violation, since the
projected law files are PROTECTED.

**Self-lockout (R2).** A required check that has never run blocks every PR. `pr-source-guard`
is added as a normal job, demonstrated red once and green once, and promoted to *required*
only after the first merge. Likewise, Lane C must prove the **allow** path with the same
rigour as the refuse paths, or the develop push itself becomes impossible.

**Deleting a rule while deduplicating (R6).** The A2.3 grep is the mechanical proof of
relocation, and Lane E re-runs it independently. Every removal from a tier-2 surface must be
answerable with "it now lives at `dadaia-gitflow` line N".

**Token cost of the always-on law (R5).** `DADAIA.md` is already ~3.5k tokens against a ≤3k
aspiration (deviation N-1, operator-approved at v0.3.0). This release must not make that
meaningfully worse: the cap is +400 tokens, measured, with both numbers in CLOSURE. The
operational table lives in a skill that is loaded on demand precisely for this reason.

**A subtler verdict (R4).** Replacing a sha equality with "does this APPROVED handoff cover
the `origin/develop..develop` delta" trades a trivially-correct check for a semantically
richer one. The failure mode is a *pass* on a stale handoff — invisible. Contract tests must
assert the refusal on a non-covering handoff, and the RED evidence is mandatory.

**Retiring CI push triggers (R7).** Feature branches lose their remote CI run. That is
acceptable only because the pre-push preflight already runs the full ladder locally before
any push, and because `develop` is pushed at both milestones. If the local preflight is ever
weakened, this trade-off must be revisited.

**The hotfix revocation could read as a loss of record (R9).** It is not: the append-only
bug ledger plus the `CHANGELOG.md` entry at merge already are the record. The rewrite in
`product-engineer.md` must say that explicitly, so the next reader does not "restore" the
ceremony as a perceived regression.

## 5. Validation strategy

- **Per task:** the quality ladder — `pytest -p no:cacheprovider -q`, `ruff format --check`,
  `ruff check`, `mypy --strict`, `lint-imports --config setup.cfg --no-cache`.
- **Per text task:** `dadaia public stage` → `dadaia public install --target all` →
  `dadaia public doctor` (zero drift, `[ok] public-privacy`), plus `dadaia specs doctor`.
- **Per enforcement task:** RED-before-GREEN evidence captured, then a **live** refusal
  demonstration on this instance — the unit proves the function, the demonstration proves
  the wiring, and only both together prove the gate.
- **Relocation audit:** the A2.3 grep, run by the author and again independently by QA.
- **Release-level:** SPEC §7 in full → qa `alpha-1` committed to the branch → six-axis code
  review + diff-based security APPROVE keyed to `origin/develop..develop` → milestone (b)
  merge → push `develop` → every CI job green → PR `develop` → `main` → merge → **memory
  update → CLOSURE → archive**, with `specs/backlog/gitflow-standardization.md` flipped to
  `DELIVERED — v0.6.0` and all six of its intents mapped to the FR that consumed them.
