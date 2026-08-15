# TASKS — Release v0.10.0 — `dd-` lifecycle skills family and rule dehydration

**Status:** Aprovado
**Release ID:** v0.10.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.10.0/SPEC.md`
**Source PLAN:** `specs/releases/v0.10.0/PLAN.md`
**Branch:** `feature/v0.10.0` (cut from `develop` at `0f66fb3f`; branch contract: `dadaia-gitflow`)
**Segment:** none — flat release; one implementation increment, closed by T-100-16

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Standing rules for this release

- **`product-engineer` has no shell.** Every task marked **[git]** is executed by the
  dispatcher or `software-engineer`. `product-engineer` authors text only.
- **Ownership is hard.** `dadaia_workspace/public/**` is `ai-engineer`'s exclusive
  surface (`DADAIA.md` §2). `dadaia_workspace/infrastructure/**` and `tests/**` are
  `software-engineer`'s. A task that finds itself needing to cross is a design error:
  stop and raise it.
- **Destination before source.** Never cut a section out of the law or a skill before the
  skill that receives it exists and is committed. A cut with no destination is a deletion.
- **No second copy.** Every cross-skill dependency is a one-line pointer naming the target
  skill. Before completing any of T-100-04…T-100-10, run the proxy-2 shingle check of
  SPEC A1.3 against the family members already written.
- **RED before GREEN — where testable.** Only T-100-14 has a behavioral test; it is
  written first and observed failing for the real reason.
- **Test intent at birth.** Any test this release adds declares
  `Intent: CONTRACT — v0.10.0 <A-id>` or `Intent: SENTINEL — <seam>`. No undeclared
  SCAFFOLD.
- **No private term enters the repository.** Synthetic names only (`dd-nonexistent`,
  `zz-fake-skill`). No foreign context name, repo slug, hostname, IP, email or absolute
  local path in any authored skill, law, persona, test or spec file — including this one.
  The v0.9.0 range-scoped denylist scan refuses the push otherwise.
- **One `[-]` at a time.** This release declares **no** sanctioned parallel pair: ten
  tasks write into `dadaia_workspace/public/` and the rename ripples cross them.
- **A group of completed work is one commit** — not one commit per file.
- **Reservation is observable.** Flip `[ ]` → `[-]` and commit `chore(tasks): start <id>`
  before the work, per `dadaia-task-manager`.

---

- [x] **T-100-01 — [git] Commit the definition content on `feature/v0.10.0`**

**Owner role:** software-engineer (or dispatcher) · **Commit:**
`docs(T-100-01): v0.10.0 definition — dd- lifecycle skills family`

**Preconditions:** `SPEC.md`, `PLAN.md` and `TASKS.md` all carry `**Status:** Aprovado`
(operator). Working tree on `feature/v0.10.0`. **Check with the PM** whether the
purge-on-pick removal of `specs/backlog/20260814-dd-lifecycle-skills-family.md` has been
performed; if so, that deletion rides this commit (SPEC §7). If not, proceed and record
the pending purge in CLOSURE — never author the backlog change here.

**Write set (staging only — content already authored by `product-engineer`):**
`specs/releases/ACTIVE.md`, `specs/releases/v0.10.0/SPEC.md`,
`specs/releases/v0.10.0/PLAN.md`, `specs/releases/v0.10.0/TASKS.md`
(+ the PM-authored backlog deletion **only if** it already exists in the tree).

**Description:** Stage exactly those paths — never `-A` over the shared tree — and commit.
Set `ACTIVE.md` phase from `DEFINITION` to `IMPLEMENTATION` in the same commit.

**Done criterion:** one commit containing exactly those paths; `ACTIVE.md` reads
`release: v0.10.0` / `phase: IMPLEMENTATION`.

**Parallelism:** none — first task.

---

- [x] **T-100-02 — [git] Milestone (a): merge, security review, push**

**Owner role:** dispatcher + `security-reviewer` · **Commit:** merge commit on `develop`

**Preconditions:** T-100-01 `[x]`. All three of SPEC/PLAN/TASKS `Aprovado`.

**Write set:** git refs only (`develop`), plus the security-reviewer handoff under
`.dadaia/handoff/dadaia-workspace/`.

**Description:** Per `dadaia-gitflow` milestone (a), in this order: merge
`feature/v0.10.0` into local `develop`; run a **diff-based** `security-reviewer` review of
`origin/develop..develop`; push `develop`. The push gate requires an APPROVED handoff keyed
to the pushed tip, plus the CI preflight.

**Done criterion:** `develop` pushed; APPROVED handoff covering the pushed delta; CI green.

**Parallelism:** none.

---

- [x] **T-100-03 — Baseline census (the denominator for FR15)**

**Owner role:** ai-engineer · **Commit:**
`chore(T-100-03): capture pre-release always-on and skill-surface baseline`

**Preconditions:** T-100-02 `[x]`.

**Write set:** `.dadaia/tmp/ai-engineer/<YYYYMMDD>/` only (no repository file).

**Description:** Measure and capture, with the exact commands: `wc -w -l` on
`public/data/DADAIA.md` and `public/data/AGENTS.md`; `wc -w -l` on every
`public/skills/*/SKILL.md`; the count and names of staged skill directories. The Part A
figures (2,423 / 200 words) are a 2026-08-14 reference, **not** the acceptance datum —
this measurement is (SPEC A15.1).

**Done criterion:** a capture file under `.dadaia/tmp/ai-engineer/<YYYYMMDD>/` containing
every figure and the command that produced it, ready to be quoted in CLOSURE.

**Parallelism:** none.

---

- [x] **T-100-04 — `dd-backlog-definition` (new): vocabulary home, BACKLOG schema, intake gate**

**Owner role:** ai-engineer · **Commit:**
`feat(T-100-04): dd-backlog-definition — curation, vocabulary and operator-gated intake`

**Preconditions:** T-100-03 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md` (new).

**Description:** Author the seven-section spine of SPEC FR2. Three contents make this the
first destination task: (a) the **terminal disposition-token vocabulary** relocated here
from `dadaia-release-closure/SKILL.md:135-138` (ADR #13/E-7) — this file becomes its only
home in `public/`; (b) the **`BACKLOG.md` ACTIVE+LEDGER schema and purge-on-pick rule**
(ADR #14); (c) the **operator-gated intake protocol** (ADR #15, SPEC FR16) as a core
statement — an agent reading only this skill must learn that it may not create a backlog
entry, what the intake report is, and that an operator-ratified deferral is pre-approved
intake. Write from scratch: the entry schema, the dedup-detection method, the intake
mechanics. Do **not** restate picking (`dd-release-definition`) or the sweep
(`dd-release-closure`).

**Done criterion:** SPEC A2.1–A2.5 satisfied; ≤ 160 lines; proxy-2 clean against
`public/data/DADAIA.md`.

**Parallelism:** none.

---

- [x] **T-100-05 — `dd-release-definition` (rename + revisit)**

**Owner role:** ai-engineer · **Commit:**
`refactor(T-100-05): rename dadaia-release-definition to dd-release-definition`

**Preconditions:** T-100-04 `[x]`.

**Write set:** `git mv dadaia_workspace/public/skills/dadaia-release-definition
dadaia_workspace/public/skills/dd-release-definition`, then that `SKILL.md`.

**Description:** Rename the directory and the `name:` frontmatter. Delete the step-1
sanitize body (`:31-38`), replacing it with a one-line reference to
`dd-backlog-definition`. Add the pick-time-priority quote as a **≤2-line blockquote** —
the single sanctioned use of the proxy-2 blockquote exemption. Update the internal
reference to the closure skill at `:88` to `dd-release-closure`. Steps 2–6 otherwise
survive; the milestone-(a) mechanics at `:67-70` are untouched.

**Done criterion:** SPEC A3.1–A3.4 satisfied; ≤ 130 lines.

**Parallelism:** none.

---

- [x] **T-100-06 — `dd-release-implement` (new) + E-3 cadence table move**

**Owner role:** ai-engineer · **Commit:**
`feat(T-100-06): dd-release-implement and the gate-cadence table move`

**Preconditions:** T-100-05 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dd-release-implement/SKILL.md` (new),
`dadaia_workspace/public/skills/project-orchestration/SKILL.md`.

**Description:** Author the seven-section spine of SPEC FR4. **Move** the Review/QA
gate-cadence table out of `project-orchestration/SKILL.md:120-150` (ADR #9/E-3), leaving
one named reference line there and no table. Section 4 is the release's largest new prose:
a decision procedure taking (task, segment) and returning the permitted and forbidden
action sets — not a second copy of the table. Sections 3, 5 and 6 are references to
`dadaia-task-manager`, `dadaia-gitflow` and `dadaia-test-stewardship`.

**Done criterion:** SPEC A4.1–A4.4 satisfied; ≤ 160 lines; the table exists exactly once
in `public/`.

**Parallelism:** none.

---

- [x] **T-100-07 — `dd-release-closure` (rename + revisit)**

**Owner role:** ai-engineer · **Commit:**
`refactor(T-100-07): rename dadaia-release-closure and re-route release residuals`

**Preconditions:** T-100-06 `[x]`.

**Write set:** `git mv dadaia_workspace/public/skills/dadaia-release-closure
dadaia_workspace/public/skills/dd-release-closure`, then that `SKILL.md`.

**Description:** Rename directory and `name:`. Two content changes only: (1) replace the
terminal-token table at `:135-138` with a one-line reference to `dd-backlog-definition`,
keeping the sweep procedure, the never-delete citation and the SPEC-DOC-031/032 backstops;
(2) replace `## Backlog returns` (`:110-117`) with `## Intake candidates` per ADR #15 —
residuals are listed in CLOSURE and compiled into the PM's intake report, the closer
creates no backlog entry, and operator-ratified deferrals are marked pre-approved intake.
The strings `backlog/ideas.md` and `backlog/candidates.md` must not survive anywhere in
the file.

**Done criterion:** SPEC A5.1–A5.5 satisfied; ≤ 220 lines.

**Parallelism:** none.

---

- [x] **T-100-08 — `dd-audit-project` (full merge + rename of `drift-detection`)**

**Owner role:** ai-engineer · **Commit:**
`refactor(T-100-08): merge drift-detection into dd-audit-project with its lifecycle wrapper`

**Preconditions:** T-100-07 `[x]`.

**Write set:** `git mv dadaia_workspace/public/skills/drift-detection
dadaia_workspace/public/skills/dd-audit-project`, then that `SKILL.md`.

**Description:** Per ADR #8/E-2 `drift-detection` ceases to exist. Inherit its technical
content nearly verbatim — atom inventory, drift method, dead-code detection, the
6-dimension rubric (Dimension E keeps its v0.7.0 detection-quality anchors; no
line-coverage percentage returns to any score anchor), aggregation, CLI integration, item
template, recommendation policy. Add two sections: the **lifecycle wrapper** (one audit →
one remediation release → full disposition → archive naming that release, plus the
finding-id → `TASKS.md`-row mapping) and **evidence-agent dispatch** (which agent supplies
evidence for which dimension). Route dispositions by reference to
`dd-backlog-definition`'s vocabulary and its pre-approved-intake carve-out.

**Done criterion:** SPEC A6.1–A6.5 satisfied; ≤ 300 lines.

**Parallelism:** none.

---

- [x] **T-100-09 — `dd-bug-registration` (new) + `dadaia-cli` dehydration**

**Owner role:** ai-engineer · **Commit:**
`feat(T-100-09): dd-bug-registration consolidates the duplicated registration blocks`

**Preconditions:** T-100-08 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dd-bug-registration/SKILL.md` (new),
`dadaia_workspace/public/skills/dadaia-cli/SKILL.md`.

**Description:** Author the seven-section spine of SPEC FR7 — this is a consolidation, not
new doctrine. Then dehydrate `dadaia-cli/SKILL.md:96-114` ("Register a bug" + "When a
command fails") to a single pointer line (FR9-C8). The full `dadaia bugs append` block,
the classify-first rule, the redaction rule and the self-hosting-vs-consumer routing must
end up existing exactly once in `public/` — here. Section 6 states the explicit non-goal:
this skill never reproduces and never fixes.

**Done criterion:** SPEC A7.1–A7.3 satisfied; ≤ 110 lines.

**Parallelism:** none.

---

- [x] **T-100-10 — `dd-bug-fix` (new) + `dadaia-gitflow` dehydration**

**Owner role:** ai-engineer · **Commit:**
`feat(T-100-10): dd-bug-fix owns Arm B end-to-end`

**Preconditions:** T-100-09 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dd-bug-fix/SKILL.md` (new),
`dadaia_workspace/public/skills/dadaia-gitflow/SKILL.md`.

**Description:** Author the eight-section spine of SPEC FR8. Then dehydrate
`dadaia-gitflow/SKILL.md:57-67` (the "Hotfix: PATCH-mint, no ceremony" prose) to a pointer,
keeping its stage-contract table row at `:31` (FR9-C7); update the See-also at `:88` to the
new family names. Per ADR #10/E-4 the concurrency section describes **advisory presence
only** and names `bug-picked-ledger-event` as where the reservation primitive is designed —
invent no marker, no lock, no lease. The close-in-same-session law
(`data/DADAIA.md:243-246`) is **referenced, never restated**: that paragraph is explicitly
not cut.

**Done criterion:** SPEC A8.1–A8.4 satisfied; ≤ 130 lines.

**Parallelism:** none.

---

- [x] **T-100-11 — Law dehydration at the source (`public/data/DADAIA.md`)**

**Owner role:** ai-engineer · **Commit:**
`refactor(T-100-11): dehydrate stage protocol out of the always-on law`

**Preconditions:** T-100-04…T-100-10 all `[x]` — every destination skill exists, so every
pointer this task writes already resolves. ADR #7/E-1 guardrail (a) is satisfied by this
task's write set naming the file; guardrail (b) is T-100-12.

**Write set:** `dadaia_workspace/public/data/DADAIA.md` (only).

**Description:** Apply SPEC FR9 exactly. Replace C1 (§5 Backlog), C3 (§5 Hotfixes), C5
(§6 registration, including the command block) and C6 (§6 watch-CI) with the surviving text
quoted verbatim in the SPEC; add C11 to the §9 Skills row. **Verify before completing**
that C2 (§5 Releases, `:189-197`), C4 (§5 Audits, `:204-208`), §1 (`:14-24`) and §2
(`:46-70`) are byte-identical to their pre-task content — these are `KEEP` rows and their
survival is an acceptance criterion, not an oversight risk. Measure `wc -w` and compare
against the T-100-03 baseline; if the net is an increase, tighten C1's wording rather than
cutting a KEEP row.

**Done criterion:** SPEC A9.1–A9.5 and A15.2 satisfied; the measured before/after word
count is captured for CLOSURE. The law diff is prepared for the operator's pre-merge
eyeball (A9.6).

**Parallelism:** none.

---

- [x] **T-100-12 — F-0 persona-scope fix and the rename ripple**

**Owner role:** ai-engineer · **Commit:**
`fix(T-100-12): correct ai-engineer's declared rule surface and every renamed-skill reference`

**Preconditions:** T-100-11 `[x]`.

**Write set:** `dadaia_workspace/public/agents/ai-engineer.md`,
`dadaia_workspace/public/agents/product-engineer.md`,
`dadaia_workspace/public/agents/project-auditor.md`,
`dadaia_workspace/public/agents/project-manager.md`,
`dadaia_workspace/public/agents/software-engineer.md`,
`dadaia_workspace/public/agents/qa-engineer.md`,
`dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`,
`dadaia_workspace/public/skills/dadaia-test-stewardship/SKILL.md`,
`dadaia_workspace/public/skills/project-orchestration/SKILL.md`.

**Description:** Two jobs.

1. **F-0 (SPEC FR11).** Replace all three `public/rules/**` occurrences in
   `ai-engineer.md` (`:54` frontmatter `write_allowlist`, `:100` scope list, `:351`
   permission table) with the real paths — `public/data/*.md`,
   `public/scaffold/**/*AGENTS.md`, `public/templates/*-AGENTS.md` — and state in the
   permission table that `public/data/DADAIA.md` is the law **source** while its
   projections stay PROTECTED and human-only (`DADAIA.md` §7).
2. **Rename ripple (SPEC FR12)** across every live reference: `product-engineer.md`
   frontmatter `:16` and body `:156`, `:165`, `:200`, `:275`, `:360`, `:374`;
   `project-auditor.md` frontmatter `:17` and body `:131`, `:198`; `dadaia-grill-me`
   `:37`, `:41`; `dadaia-test-stewardship` `:67`, `:168`, `:170`; `project-orchestration`
   `:236` (also FR9-C9 — replace the five-step restatement with a pointer). In the same
   pass, apply the FR13(a) frontmatter grants for all seven `dd-` skills.

`CHANGELOG.md` and `specs/_archive/**` are **not** edited.

**Done criterion:** SPEC A11.1–A11.3, A12.1–A12.2 and A13.1 satisfied; V4's grep returns
zero hits.

**Parallelism:** none.

---

- [x] **T-100-13 — ADR #15 external surfaces (I4–I8)**

**Owner role:** ai-engineer · **Commit:**
`docs(T-100-13): operator-gated intake across the personas and orchestration surfaces`

**Preconditions:** T-100-12 `[x]`.

**Write set:** `dadaia_workspace/public/agents/product-engineer.md`,
`dadaia_workspace/public/agents/qa-engineer.md`,
`dadaia_workspace/public/agents/project-manager.md`,
`dadaia_workspace/public/skills/project-orchestration/SKILL.md`,
`dadaia_workspace/public/skills/ai-harness-codex/SKILL.md`.

**Description:** Correct the five surfaces outside the family that still describe the
superseded flow (SPEC FR16, rows I4–I8). **I4** — `product-engineer.md:370`: CLOSURE step 6
becomes "Intake candidates", residuals listed for the PM's intake report, PE creates no
backlog entry. **I5** — `qa-engineer.md:253-255`: the hotfix-candidate stub is routed to
the PM's intake report, not transcribed into `specs/backlog/candidates.md ## Hotfixes
pendentes` (stale on three axes). **I6** — `project-manager.md:83-87`: keep sole curation,
add the intake gate — curation is downstream of an operator decision; the PM compiles and
presents, it does not create demand. **I7** — `project-orchestration/SKILL.md:37`, `:55`:
one-line corrections naming the gate and pointing at `dd-backlog-definition`. **I8** —
`ai-harness-codex/SKILL.md:339`: the intake row yields an intake-report item, not a backlog
candidate. Each is a one-line correction or reference — the full doctrine stays only in
`dd-backlog-definition`.

**Done criterion:** SPEC A16.1–A16.6 satisfied; V5's grep returns zero hits.

**Parallelism:** none.

---

- [x] **T-100-14 — Codex D-CX-7 prefix gate, its contract test, and the test goldens**

**Owner role:** software-engineer · **Commit:**
`fix(T-100-14): keep the codex skill-reference check live for the dd- family`

**Preconditions:** T-100-13 `[x]` — the final skill set exists.

**Write set:** `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py`,
`tests/contract/test_codex_skill_ref_prefixes.py` (new),
`tests/e2e/features/test_public_pipeline.py`,
`tests/unit/infrastructure/_golden/doctor_all_four_v0158.json`,
`tests/unit/infrastructure/_golden/install_target_resolution_v0158.json`.

**Description:** **RED first.** Write the contract test before the constant changes: a
projected Codex persona citing a non-existent `dd-` skill must produce the D-CX-7
`missing skill` ERROR line, and one citing a real family skill must not. Observe it
failing for the real reason — `_CODEX_SKILL_REF_PREFIXES` (`codex_assets.py:42`, consumed
at `codex_doctor.py:269`) does not contain `"dd-"`, so the check silently skips the entire
family. Then remove `"drift-detection"` from the tuple and add `"dd-"`, and watch it go
green. Leave the pre-existing `"memory-ctx"` entry alone (SPEC §4.8). Finally update
`EXPECTED_SKILLS` to the 25-name set (21 with three renamed in place, plus four net-new)
and regenerate both golden fixtures. Test intent at birth:
`Intent: CONTRACT — v0.10.0 A13.3`.

**Done criterion:** SPEC A13.2–A13.4 satisfied; `dadaia ci preflight` green.

**Parallelism:** none.

---

- [x] **T-100-15 — Re-projection, orphan sweep, byte verification**

**Owner role:** ai-engineer · **Commit:**
`chore(T-100-15): re-project the dd- family and sweep orphaned projections`

**Preconditions:** T-100-14 `[x]`.

**Write set:** the projections produced by `dadaia public stage` +
`dadaia public install --target all`, and the removal of orphaned skill directories under
`.agents/skills/`, `.claude/skills/`, `.codex/`, `.kimi-code/`.

**Description:** Run the §7 chain in order: `dadaia public stage` (which rebuilds staging
with an `rmtree`, so staging self-heals), `dadaia public install --target all`, then
`dadaia public doctor`. **`install` prunes nothing** — explicitly remove the orphaned
`dadaia-release-definition`, `dadaia-release-closure` and `drift-detection` directories
from every projected tree. Byte-verify each of the seven family skills across source ↔
staging ↔ `.agents` ↔ `.claude`.

**Done criterion:** SPEC A14.1–A14.4 satisfied; `dadaia public doctor` exits 0 with
`[ok] public-privacy` and no `[missing]`/`[drift]` line attributable to a skill.

**Parallelism:** none.

---

- [x] **T-100-16 — `qa-engineer` review of the increment (flat alpha close)**

**Owner role:** qa-engineer · **Commit:** review artifact committed to the branch

**Preconditions:** T-100-15 `[x]`.

**Write set:** `.dadaia/handoff/dadaia-workspace/` (+ `.dadaia/tmp/qa-engineer/<YYYYMMDD>/`
for captures); the review artifact committed to `feature/v0.10.0`.

**Description:** Verify the increment against SPEC FR1–FR16 acceptance ids one by one. Run
PLAN §7's V1–V12 and V14–V15 and capture every command's output. In particular: the
proxy-2 shingle scan (V2) — this release's style bar has no linter and this review **is**
its enforcement; the two zero-hit greps (V4, V5); the law-fidelity diff against SPEC FR9's
verbatim text including the C2/C4/§1/§2 byte-identity check; and the FR15 token accounting
against the T-100-03 baseline. Confirm test intents are declared and that no test was
pruned to go green. Apply the redaction doctrine to this artifact.

**Done criterion:** APPROVED verdict enumerating every acceptance id, or REJECTED
returning named defects to the implementer.

**Parallelism:** none.

---

- [-] **T-100-17 — Memory update (CLOSURE phase)**

**Owner role:** product-engineer · **Commit:**
`docs(T-100-17): memory — dd- family, backlog doctrine and intake gate`

**Preconditions:** T-100-16 `[x]` with APPROVED. `ACTIVE.md` phase set to `CLOSURE`
**before writing** (the gate allows `specs/memory/**` writes in `DEFINITION` and `CLOSURE`
only).

**Write set:** `specs/memory/product/distribution/public-asset-distribution.md`,
`specs/memory/product/agents/agentic-entities.md`,
`specs/memory/product/sdd/sdd-bug-backlog-governance.md`,
`specs/memory/product/agents/agent-orchestration.md`,
`specs/memory/product/catalog.json` (regenerated **only** if a touched atom's
`tldr`/`summary` frontmatter changed, via
`dadaia_workspace/public/scripts/generate-memory-catalog.py`).

**Description:** State the product as it is **now**, per SPEC §5: the seven `dd-` skills as
the universal lifecycle surface with one canonical `.agents/skills/` home and no registry
entry; the backlog as the single-source `BACKLOG.md` with ACTIVE+LEDGER, purge-on-pick and
the operator-gated intake rule, plus the honest note that the physical consolidation and
the tooling reconciliation are pending; the lifecycle paragraph naming the skill that owns
each stage. No changelog, history or version narrative in any atom.

**Done criterion:** `dadaia specs doctor` green on memory checks; no forbidden section
added; SPEC §5 satisfied file by file.

**Parallelism:** none.

---

- [ ] **T-100-18 — CLOSURE, dispositions, archive, version bump**

**Owner role:** product-engineer (text) + software-engineer/dispatcher (**[git]** steps)
· **Commit:** `docs(T-100-18): close release v0.10.0`

**Preconditions:** T-100-17 `[x]`.

**Write set:** `specs/releases/v0.10.0/CLOSURE.md` (new), `specs/releases/ACTIVE.md`,
`pyproject.toml` (version — package axis currently `0.6.0`, ADR-2 split), `CHANGELOG.md`,
plus the release-directory move.

**Description:** In the finalization order **memory → CLOSURE → archive**:

1. Record the T-100-17 memory writes under `## Memory updates`.
2. Write `CLOSURE.md` per `dd-release-closure` (the skill this release renamed): summary,
   tasks + commit SHAs, validations V1–V15 with evidence, drifts, `## Dispositions`
   (`specs/backlog/20260814-dd-lifecycle-skills-family.md` → `DELIVERED — v0.10.0`; state
   explicitly that **no bug and no audit** was picked), and `## Test dispositions`. Carry
   the FR15 before/after token table with its commands, the V1–V3 style-bar figures, the
   V4/V5 zero-hit greps, and the A10.3 statement that the physical `BACKLOG.md`
   consolidation and the backlog tooling are **not** delivered here. Record the
   purge-on-pick state. Residuals go under **`## Intake candidates`** — compiled for the
   PM's operator-facing intake report, **never materialized as backlog entries** (ADR #15).
3. **[git]** `git mv specs/releases/v0.10.0 specs/_archive/releases/v0.10.0`; set
   `ACTIVE.md` to the next release or `release: none` / `phase: none`.
4. **[git]** Bump `pyproject.toml` and add the `CHANGELOG.md` entry per the gitflow
   contract.

**Done criterion:** `CLOSURE.md` complete under `specs/_archive/releases/v0.10.0/`;
`ACTIVE.md` no longer points at `v0.10.0`; `dadaia specs doctor` green.

**Parallelism:** none.

---

- [ ] **T-100-19 — [git] Milestone (b): ship**

**Owner role:** dispatcher + `code-reviewer` + `security-reviewer` · **Commit:** merge
commit + PR

**Preconditions:** T-100-18 `[x]`.

**Write set:** git refs only, plus the reviewer handoffs.

**Description:** Per `dadaia-gitflow` milestone (b), in order: `code-reviewer` six-axis
pass over the release delta — including the operator's pre-merge eyeball of the
`public/data/DADAIA.md` diff (SPEC A9.6, ADR #7/E-1 guardrail c); merge `feature/v0.10.0`
into local `develop`; diff-based `security-reviewer` review of `origin/develop..develop`;
push `develop`; open PR `develop` → `main`; watch CI until every job is green; merge.

**Done criterion:** PR merged to `main`; CI green; `feature/v0.10.0` no longer needed.

**Parallelism:** none — last task.
