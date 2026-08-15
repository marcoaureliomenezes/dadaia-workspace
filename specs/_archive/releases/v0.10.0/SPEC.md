# SPEC — Release v0.10.0 — `dd-` lifecycle skills family and rule dehydration

**Status:** Aprovado
**Release ID:** v0.10.0
**Owner:** product-engineer
**Opened:** 2026-08-15
**Created:** 2026-08-15
**Branch:** `feature/v0.10.0` (cut from `develop` at `0f66fb3f`; branch contract: `dadaia-gitflow`)
**Consumes:** the single backlog candidate
`specs/backlog/20260814-dd-lifecycle-skills-family.md` ("release 3" in the grill's
prioritized sequence). **No bug is picked** and **no audit is outstanding** (both archived
by v0.8.0; the two disposition decisions of 2026-08-14 are recorded in the grill report).
**Grill (mandatory, done):**
`.dadaia/reports/dadaia-workspace/product-engineer/2026-08-14T130830Z-refine-specs.html`
— ADRs #7/E-1, #8/E-2, #9/E-3, #10/E-4, #11/E-5, #12/E-6, #13/E-7 and #14 are binding and
settled; they are **not re-litigated here**.
**Operator ADR #15 — operator-gated backlog intake (ratified 2026-08-15):** binding, and
**supersedes** any earlier text — in the grill report, the design report, the law, the
skills or the agent personas — that has an agent materialize technical residuals directly
into the backlog. See FR16.
**Design evidence (approved architecture, consumed not redesigned):**
`.dadaia/reports/dadaia-workspace/ai-engineer/2026-08-14T122310Z-dd-skills-design/index.html`
(Parts A–E). The design report predates ADR #15; where its Part B spine for
`dd-backlog-definition` describes a free "proposal intake" and its Part C leaves the
CLOSURE-returns flow untouched, **ADR #15 wins** (FR2, FR5, FR16).

---

## 1. Problem and context

The development cycle this workspace runs — backlog definition, release definition,
release implementation, release closure, project audit, bug registration, bug fix — has
**seven stages and no matching skill surface**. Today:

| Stage | Where its protocol actually lives | Cost |
|---|---|---|
| backlog definition | one paragraph of always-on law (`data/DADAIA.md:176-180`) + a duplicated step inside `dadaia-release-definition/SKILL.md:31-38` | no procedure exists; the entry schema, dedup method and proposal-intake shape are nowhere |
| release definition | `dadaia-release-definition` **+ a full prose restatement** in `project-orchestration/SKILL.md:230-242` | one workflow, two sources |
| release implementation | **nowhere end-to-end**; the load-bearing gate-cadence table sits in `project-orchestration/SKILL.md:120-150`, a skill scoped to dispatchers, not to the implementers who consult it | workers pay an indirection hop into a dispatcher skill to find their own gating rule |
| release closure | `dadaia-release-closure` (tight, well-scoped) | fine, but named off-family |
| project audit | `drift-detection` — ~90% audit content, with **no reference at all** to the audit-lifecycle law (`data/DADAIA.md:204-208`) | the technical method exists; the lifecycle wrapper does not |
| bug registration | `data/DADAIA.md:226-241` **and** a near-duplicate block at `dadaia-cli/SKILL.md:96-114` | the same command block is stated twice, one of them in the always-on file |
| bug fix (Arm B) | `data/DADAIA.md:14-24` + `:199-202` **and** a near-total duplicate at `dadaia-gitflow/SKILL.md:57-67` | procedure split across law and a branch-mechanics skill |

Two structural consequences follow.

**The always-on file carries procedure.** `public/data/DADAIA.md` (2,423 words measured
2026-08-14, Part A) is projected verbatim to the workspace root and to every harness
directory and is read by **every agent in every session**. Every procedural word inside it
is paid on every dispatch of all nine agents, whether or not the session is doing that
stage's work. The single `dadaia bugs append` block at `:230-234` costs ≈146 tokens per
session per agent and is consumed by the one turn in fifty that actually registers a bug.

**The law states facts twice.** `DADAIA.md`'s own preamble says "no fact is stated twice".
Four measured violations exist today: bug registration (law ↔ `dadaia-cli`), the hotfix
procedure (law ↔ `dadaia-gitflow`), release definition (skill ↔ `project-orchestration`),
and the disposition-token vocabulary (declared in ≥4 places, grill problem #13).

The operator's thesis, ratified at the 2026-08-14 grill: **the skill surface is the
operational interface of the development cycle and must mirror it 1:1** — one `dd-`
prefixed skill per stage, seven in total, each owning its stage with zero overlap, written
in clear, direct, non-verbose statements; and cycle-specific content is **dehydrated** out
of the always-on rules into those on-demand skills (rules = always-on law, skills =
on-demand protocol).

---

## 2. Objective

Seven `dd-` skills exist, one per lifecycle stage, each the single source of its stage's
protocol. The always-on law keeps only what an agent must read **before** it knows which
stage it is in; every stage procedure is one on-demand hop away. No fact is stated twice
inside the family or between the family and the law. Every textual reference to a renamed
skill — in law, agent personas, skills citing skills, production Python, and tests — is
updated in the same release, verified by grep, not by hope.

This is an **AI-surface release**. The deliverables are skills, rules and agent text at the
canonical source `dadaia_workspace/public/`, implemented by `ai-engineer` (`DADAIA.md` §2 —
sole owner of the AI surface). Exactly one narrow production-code touchpoint exists (FR13),
owned by `software-engineer`, because the rename would otherwise silently disable a doctor
check.

---

## 3. Scope

### FR1 — The family: seven skills, one per stage, zero overlap, measurable style bar

Seven skills exist at `dadaia_workspace/public/skills/<name>/SKILL.md`:

| Skill | Stage | Origin | FR |
|---|---|---|---|
| `dd-backlog-definition` | backlog definition | new | FR2 |
| `dd-release-definition` | release definition | rename + revisit of `dadaia-release-definition` | FR3 |
| `dd-release-implement` | release implementation | new | FR4 |
| `dd-release-closure` | release closure | rename + revisit of `dadaia-release-closure` | FR5 |
| `dd-audit-project` | project audit | full merge + rename of `drift-detection` (ADR #8/E-2) | FR6 |
| `dd-bug-registration` | bug registration | new | FR7 |
| `dd-bug-fix` | bug fix (Arm B in full) | new | FR8 |

**Zero overlap** is a scope contract: each stage's protocol has exactly one home. A skill
that needs another stage's rule **names that skill in one line** and does not restate it.

**Style bar (operator-dictated: clear, direct, NON-verbose).** Made testable by four
mechanical proxies:

1. **Size budget per skill**, body + frontmatter, measured by `wc -l`:
   `dd-backlog-definition` ≤ 160 · `dd-release-definition` ≤ 130 · `dd-release-implement`
   ≤ 160 · `dd-release-closure` ≤ 220 · `dd-audit-project` ≤ 300 · `dd-bug-registration`
   ≤ 110 · `dd-bug-fix` ≤ 130. Family total ≤ 1,210 lines.
2. **No duplicated law text.** Zero normalized 15-word shingles shared between any two of
   the seven skills, and zero shared between any family skill and `public/data/DADAIA.md`.
   Deliberate law citations are exempt **only** when rendered as a Markdown blockquote of
   at most 2 lines — the exemption is what makes the check satisfiable for the one quote
   FR3 requires.
3. **Listing tax.** Each skill's frontmatter `description` is ≤ 350 characters.
4. **Pointer, not restatement.** Every cross-skill dependency is a single line naming the
   target skill. No section of a family skill consists solely of a restatement of another
   skill's section.

**Acceptance**

- A1.1 The seven skill directories exist at the canonical source, each with a `SKILL.md`
  carrying a `name:` matching its directory.
- A1.2 Every per-skill line budget in proxy 1 holds; the family total is ≤ 1,210 lines.
  The measured figures are recorded in `CLOSURE.md`.
- A1.3 The proxy-2 shingle scan reports zero non-exempt shared shingles. The command used
  is recorded with its output in `CLOSURE.md`.
- A1.4 Every family `description` is ≤ 350 characters.
- A1.5 A stage-ownership table exists (this FR's table) and each skill's "When to invoke"
  section names exactly one stage.

### FR2 — `dd-backlog-definition` (new)

**Scope (one line):** continuously curate the backlog and sanitize bugs into a
disposition-clean, deduplicated set ready to be picked by release definition.

Required sections (Part B spine, section 5 restated by ADR #15): 1. When to invoke
(`project-manager`, continuously) · 2. Entry schema and status vocabulary · 3. Continuous
sanitize protocol · 4. Never-delete law (cited, not restated) · **5. Operator-gated
intake — the only path by which anything becomes a backlog entry (FR16)** · 6. The "picked
set" handoff contract to `dd-release-definition` · 7. CLI reference.

Two contents are **relocated into this skill and removed from their current homes**:

- the sanitize step, today duplicated at `dadaia-release-definition/SKILL.md:31-38`
  (removed there by FR3);
- the **terminal disposition-token vocabulary**, today sole-sourced at
  `dadaia-release-closure/SKILL.md:135-138`. Per ADR #13/E-7 this skill becomes its
  canonical home; closure, audit and bug-registration skills reference it by name.

One content is **written from scratch**: the backlog entry schema, the dedup-detection
method, and the proposal-intake workflow — none exists today as a procedure.

Per ADR #14 the entry schema this skill declares is the **single-source
`specs/backlog/BACKLOG.md`**: an `ACTIVE` section (live candidates, full prose, strict
per-entry schema) and a `LEDGER` section (one line per dead item — id · disposition ·
release-or-reason · date). Purge-on-pick is mandatory: a picked entry leaves `ACTIVE` in
the same commit that creates the release SPEC, which records the provenance. Every new
entry triggers a total-consolidation review of the whole file. JSONL is rejected for
backlog (bugs stay JSONL: bugs are append-only event streams; the backlog is a living
re-consolidated document, where append is the anti-pattern).

**Acceptance**

- A2.1 The skill exists with all seven spine sections.
- A2.2 The disposition-token table (`DELIVERED`/`SUPERSEDED`/`RESOLVED`/`CONSUMED`/
  `DEFERRED`/`REJECTED`, and bug `Closed`) appears **exactly once** in the whole
  `public/` tree, in this skill. A grep for the token set returns this file plus
  reference-only mentions.
- A2.3 The `BACKLOG.md` ACTIVE/LEDGER schema and the purge-on-pick rule are stated here.
- A2.4 The operator-gated intake protocol of FR16 is one of this skill's **core
  statements** — an agent reading only this skill learns that it may not create a backlog
  entry, and learns the intake-report path it must use instead.
- A2.5 The skill carries **no** procedure owned by another stage — it points at
  `dd-release-definition` for picking and at `dd-release-closure` for the sweep.

### FR3 — `dd-release-definition` (rename + revisit)

Renamed from `dadaia-release-definition` by `git mv` of the directory plus the `name:`
frontmatter. Protocol steps 2–6 (`SKILL.md:40-97`) are kept, minus the following two
changes:

- **Step 1 (sanitize) is removed**, replaced by a one-line reference to
  `dd-backlog-definition` (dehydration, not duplication).
- The pick-time-priority rule — "open bugs and undispositioned audits outrank fresh
  backlog" (`data/DADAIA.md:195-196`) — is quoted as a **2-line blockquote**, because it
  directly gates step 2 and is easy to miss by generic reference. This is the single
  sanctioned use of the FR1 proxy-2 blockquote exemption.

The milestone-(a) branch/push mechanics at `:67-70` already reference `dadaia-gitflow`
and are unchanged.

**Acceptance**

- A3.1 `dd-release-definition/SKILL.md` exists; `dadaia-release-definition/` no longer
  exists at the source, in staging, or in any projection.
- A3.2 The sanitize step body is gone and replaced by a one-line reference.
- A3.3 The pick-time-priority quote is present as a blockquote of ≤ 2 lines.
- A3.4 The mandatory-grill step survives verbatim in substance — a release from backlog
  still cannot reach SPEC without a grill session.

### FR4 — `dd-release-implement` (new)

**Scope (one line):** execute an `Aprovado` release's TASKS through the reserve→TDD loop,
the review-gate cadence, and the segment/ship push boundary.

Required sections: 1. When to invoke · 2. Resolve release and segment · 3. Reserve → TDD
loop (reference to `dadaia-task-manager`) · 4. **Which review boundary applies now** ·
5. Push checkpoint (reference) · 6. Test-stewardship touchpoints (reference) · 7. Checklist.

Per **ADR #9/E-3** the Review/QA gate-cadence table **moves** out of
`project-orchestration/SKILL.md:120-150` into this skill; `project-orchestration`
references it by name in one line. The table is the most-consulted artifact by
implementers and must live in the implementers' skill.

Section 4 is the release's largest write-from-scratch item: a **decision procedure**, not
a reference table — given "I am inside task T-3 of `alpha-2`", it states in order what is
unlocked and what is forbidden (may not push, PR, merge, mark `[x]`, or touch CLOSURE
until `qa-engineer` approves this alpha).

**Acceptance**

- A4.1 The skill exists with all seven sections.
- A4.2 The gate-cadence table appears **exactly once** in `public/`, in this skill;
  `project-orchestration/SKILL.md` retains a one-line named reference and no table.
- A4.3 Section 4 is a decision procedure whose input is (task, segment) and whose output
  is the permitted and forbidden action sets.
- A4.4 Sections 3, 5 and 6 are references, not restatements — proxy-2 clean against
  `dadaia-task-manager`, `dadaia-gitflow`, `dadaia-test-stewardship` and the law.

### FR5 — `dd-release-closure` (rename + revisit)

Renamed from `dadaia-release-closure`. Content kept as-is (the full read found no
redundancy) with exactly two changes:

1. The terminal-token table at `:135-138` is replaced by a one-line reference to
   `dd-backlog-definition` (ADR #13/E-7). Everything else in the Disposition sweep section
   — the sweep procedure, the never-delete citation, the `SPEC-DOC-031`/`SPEC-DOC-032`
   doctor backstops — stays, because closure is where the sweep executes.
2. **`## Backlog returns` becomes `## Intake candidates` (ADR #15).** The section at
   `:110-117` today instructs the closer to push discovered items "to either
   `specs/backlog/ideas.md` (informal) or `specs/backlog/candidates.md` (formal
   candidate)" — direct materialization, now forbidden, and pointing at two files that
   ADR #14 dissolves. It becomes: residuals discovered during the release are **listed in
   CLOSURE and compiled into the PM's intake report** for operator decision; the closer
   creates no backlog entry. Operator-ratified deferrals recorded in the release's own
   SPEC/approval are marked as **pre-approved intake** in that list, so they are not
   re-adjudicated.

**Acceptance**

- A5.1 `dd-release-closure/SKILL.md` exists; `dadaia-release-closure/` no longer exists at
  source, in staging, or in any projection.
- A5.2 The token table is gone and replaced by a reference; the sweep procedure survives.
- A5.3 The CLOSURE.md template, the memory-update protocol, the finalization order
  (memory → CLOSURE → archive), and the `## Test dispositions` block are unchanged in
  substance.
- A5.4 No section of the skill instructs any agent to write a backlog entry, and the
  strings `backlog/ideas.md` and `backlog/candidates.md` do not appear in it.
- A5.5 The `## Intake candidates` section distinguishes pre-approved (operator-ratified
  during the release) from to-be-adjudicated residuals.

### FR6 — `dd-audit-project` (full merge + rename of `drift-detection`, ADR #8/E-2)

`drift-detection` **ceases to exist**. `dd-audit-project` inherits its technical content —
memory atom inventory, drift-detection method, dead-code detection, the 6-dimension scoring
rubric, the aggregation formula, CLI integration, the drift-item template, the
recommendation policy — nearly verbatim, and gains two new sections:

- **Lifecycle wrapper** — the audit law today referenced nowhere inside the skill
  (`data/DADAIA.md:204-208`): one audit generates exactly one remediation release; that
  release gives every finding an explicit disposition; the audit archives to
  `specs/audits/_archive/` only once fully dispositioned, naming that release. Plus the
  audit→release handoff contract: how a finding id maps 1:1 to a future `TASKS.md` row.
- **Evidence-agent dispatch** — the pattern implied by `DADAIA.md` §2's "dispatches
  evidence agents": which agent supplies evidence for which scoring dimension.

**Acceptance**

- A6.1 `dd-audit-project/SKILL.md` exists; `drift-detection/` no longer exists at source,
  in staging, or in any projection.
- A6.2 The 6-dimension rubric and aggregation formula survive with unchanged semantics
  (Dimension E keeps its v0.7.0 detection-quality anchors — no line-coverage percentage
  reappears in any score anchor).
- A6.3 The lifecycle wrapper states the one-audit-one-release contract and the finding→
  TASKS-row mapping.
- A6.4 The evidence-agent dispatch section names an agent per scoring dimension.
- A6.5 The skill is ≤ 300 lines despite the two added sections.

### FR7 — `dd-bug-registration` (new)

**Scope (one line):** register a genuine product bug as a classified, redacted `reported`
event in the ADDITIVE bugs ledger — the opening move of Arm B only, never the fix.

This is a pure consolidation of two existing near-duplicate blocks:
`data/DADAIA.md:226-241` (dehydrated by FR9-C3) and `dadaia-cli/SKILL.md:96-114`
(dehydrated by FR9-C7). Sections: 1. When to invoke · 2. Classify-first decision table ·
3. Redaction rule · 4. `dadaia bugs append` command reference · 5. Context routing
(self-hosting vs consumer) · 6. Handoff to `dd-bug-fix` — with the explicit non-goal that
this skill never reproduces or fixes · 7. CLI reference (`bugs status`/`stats`).

**Acceptance**

- A7.1 The skill exists with all seven sections.
- A7.2 The full `dadaia bugs append` command block appears **exactly once** in `public/`,
  in this skill.
- A7.3 The classify-first rule, the redaction rule and the self-hosting-vs-consumer
  routing each appear exactly once in `public/`, in this skill (the law keeps only the
  one-sentence classification fact of FR9-C3).

### FR8 — `dd-bug-fix` (new)

**Scope (one line):** execute Arm B end-to-end on an already-registered bug — reproduce,
RED, root-cause fix, GREEN, `resolved` event, commit — on `hotfix/{M.m.p}`.

Sections: 1. When to invoke (the bug already carries a `reported` event) · 2. Branch
(reference to the `dadaia-gitflow` stage-contract row) · 3. Reproduce on the executed path
· 4. RED test (reference to `dadaia-test-stewardship` §A intent classification) · 5.
Root-cause fix (reference to the law) · 6. GREEN + `resolved` event + evidence · 7. PATCH
mint + `CHANGELOG.md`, same commit, merge to `develop` · 8. Checklist.

This skill becomes the **single procedural source of the hotfix flow**;
`dadaia-gitflow/SKILL.md:57-67` is dehydrated to its stage-contract table row plus a
pointer (FR9-C6).

Per **ADR #10/E-4** the skill documents **today's advisory-presence signal only** — races
are surfaced, never blocked (NO-LOCKS). It states plainly that no reservation marker exists
for bugs and names `specs/backlog/bug-picked-ledger-event.md` as where that primitive is
being designed. **No reservation mechanism is invented here.**

**Acceptance**

- A8.1 The skill exists with all eight sections.
- A8.2 The hotfix procedure (PATCH mint, same-commit `pyproject.toml` + `CHANGELOG.md`, no
  ceremony) appears **exactly once** in `public/`, in this skill.
- A8.3 The concurrency section describes advisory presence only and cites the backlog entry
  by slug; it declares no marker, no lock, no lease.
- A8.4 The close-in-same-session rule (`data/DADAIA.md:243-246`) is **referenced, not
  restated** — that law paragraph is explicitly not cut (FR9).

### FR9 — The dehydration ledger: nine cuts + one table move, surviving text verbatim

Per **ADR #11/E-5** the trimmed-law wording rides this SPEC: the operator approves the
exact surviving sentences at normal SPEC `Aprovado`, and the E-1 law-diff eyeball at review
then verifies fidelity only. Rows marked **KEEP** are stated so no implementer
"helpfully" trims them.

| # | Source | Action | Destination |
|---|---|---|---|
| C1 | `data/DADAIA.md:176-180` (§5 Backlog) | replace (see C1 text; also carries FR10) | `dd-backlog-definition` |
| C2 | `data/DADAIA.md:189-197` (§5 Releases) | **KEEP verbatim** — classification-relevant before an agent picks a skill | — |
| C3 | `data/DADAIA.md:199-202` (§5 Hotfixes) | replace (see C3 text) | `dd-bug-fix` |
| C4 | `data/DADAIA.md:204-208` (§5 Audits) | **KEEP verbatim** — short and classification-relevant | — |
| C5 | `data/DADAIA.md:226-241` (§6 bug registration) | replace (see C5 text) | `dd-bug-registration` |
| C6 | `data/DADAIA.md:254-255` (§6 watch-CI) | replace (see C6 text) | `dd-release-implement` |
| C7 | `skills/dadaia-gitflow/SKILL.md:57-67` | replace the prose with a 1-line pointer; the stage-contract row at `:31` already carries the fact | `dd-bug-fix` |
| C8 | `skills/dadaia-cli/SKILL.md:96-114` | replace both blocks with a 1-line pointer | `dd-bug-registration` |
| C9 | `skills/project-orchestration/SKILL.md:230-242` (Playbook — release-definition) | replace the 5-step restatement with a 1-line pointer | `dd-release-definition` |
| C10 | `skills/project-orchestration/SKILL.md:120-150` (gate-cadence table) | **move** (ADR #9/E-3), leaving a 1-line named reference | `dd-release-implement` |

`data/DADAIA.md:14-24` (§1, the Arm A/B classification) and `:46-70` (§2, the dispatch
table) are **not touched**: they are what every agent reads before deciding which arm it is
in, and before any skill is invoked.

**C4 and ADR #15.** The Audits paragraph stays verbatim, including *"deferred/rejected with
a reason routed to the backlog"*, and this is consistent with the intake gate rather than
an exception to it: an audit disposition is an operator-ratified decision at the
remediation release's approval, and ADR #15 counts an operator-ratified deferral as
pre-approved intake. FR16 states that equivalence once, in `dd-backlog-definition`, so the
law needs no amendment here.

**Surviving text — C1** (§5 Backlog, replaces lines 176-180; also satisfies FR10):

> **Backlog.** The backlog is the **operator's demand queue**: only the operator creates
> demand. `project-manager` curates the single-source `specs/backlog/BACKLOG.md` — an
> ACTIVE section of live candidates and a LEDGER section of one line per closed item;
> everyone reads it freely. No agent materializes an entry: residuals from a closure,
> review or audit are compiled by the PM into an **intake report** the operator decides on
> first, and an operator-ratified deferral taken during a release is already approved
> intake. Nothing is deleted: an item leaves ACTIVE only by gaining a LEDGER line carrying
> its disposition and reason, and a picked item leaves ACTIVE in the same commit that
> creates the release SPEC, which records its provenance. This never-delete law covers
> bugs and backlog only — tests are prunable under the stewardship criteria (§6). Entry
> schema, intake protocol and the disposition vocabulary: `dd-backlog-definition`.

**Surviving text — C3** (§5 Hotfixes, replaces lines 199-202):

> **Hotfixes.** A bug fix stays Arm B (§1) in full, run on `hotfix/{M.m.p}` at the next
> PATCH — **no release ceremony**: no SPEC, PLAN, TASKS, or `specs/releases/<id>/`
> directory. Procedure: `dd-bug-fix`.

**Surviving text — C5** (§6, replaces lines 226-241 including the command block):

> **Register every bug you hit** while operating this tooling — any behavior that breaks
> its own contract. Classify first: environment limits, invalid input, wrong usage, and a
> validation the tool is designed to emit are not product bugs. Append the `reported`
> event before the turn ends; bug paths are ADDITIVE, so registration is always possible
> and there is no reason to defer it. Command, redaction rule and context routing:
> `dd-bug-registration`.

**Surviving text — C6** (§6, replaces the two sentences at lines 254-255):

> After every push or PR, watch CI to green (`dd-release-implement`).

**Addition — C11** (§9 "Where to look next", Skills row): the row gains one clause naming
the family, so an agent that has never met a `dd-` skill can find the surface from the law:

> the `dd-*` family maps the development cycle, one skill per stage

**Acceptance**

- A9.1 Each of C1, C3, C5, C6 in `public/data/DADAIA.md` matches its surviving text above
  **byte-for-byte** modulo line wrapping at the file's existing column width.
- A9.2 C2 and C4 are byte-identical to their current content.
- A9.3 `data/DADAIA.md:14-24` and `:46-70` are byte-identical to their current content.
- A9.4 C7, C8, C9 leave a single line naming the destination skill and no residual
  procedure; C10 leaves a single named reference and no table.
- A9.5 C11 is present in §9.
- A9.6 The law-file diff is presented to the operator at the pre-merge review as an
  explicitly highlighted section (ADR #7/E-1 guardrail c).

### FR10 — §5 backlog law amended to the single-source doctrine (ADR #14)

The C1 replacement above **is** the §5 amendment: `specs/backlog/BACKLOG.md` as the single
source, ACTIVE + LEDGER, mandatory purge-on-pick, never-delete reconciled as
"leaves ACTIVE only by gaining a LEDGER line". It lands at the library source
(`public/data/DADAIA.md`) through the E-1 path and reaches every workspace through the §7
projection chain.

**Scope boundary — this FR ships the doctrine, not its enforcement.** The physical
consolidation of the 35 current per-entry files plus `candidates.md` into `BACKLOG.md` is
`project-manager` curation surface (§7 of this SPEC), and the tooling that still assumes
per-entry files is **out of scope** (§4.5) with a named follow-up. This split is called out
for explicit operator ratification at approval (§8).

**Acceptance**

- A10.1 The amended §5 Backlog paragraph is present at the source and in every projection
  after re-projection.
- A10.2 `dd-backlog-definition` and the law agree on the schema — no second, divergent
  description of `BACKLOG.md` exists anywhere in `public/`.
- A10.3 The SPEC records, and CLOSURE repeats, that the physical consolidation and the
  tooling reconciliation are **not** delivered by this release.

### FR11 — F-0: `ai-engineer`'s declared rule surface matches reality

`dadaia_workspace/public/agents/ai-engineer.md` names `dadaia_workspace/public/rules/**`
as its rule write surface in three places — frontmatter `write_allowlist` (`:54`), the
scope list (`:100`) and the permission table (`:351`). **That directory does not exist
anywhere in the tree** (verified). The real rule-like artifacts are `public/data/*.md` (the
law plus the scoped `*-AGENTS.md` files) and the `*-AGENTS.md` files under
`public/scaffold/` and `public/templates/`.

This is ADR #7/E-1 guardrail (b) and is a **precondition of FR9**: without it, the agent
authoring the law source is writing outside its own declared allowlist.

**Acceptance**

- A11.1 All three occurrences of `public/rules/**` in `ai-engineer.md` are replaced by the
  real paths: `dadaia_workspace/public/data/*.md`,
  `dadaia_workspace/public/scaffold/**/*AGENTS.md`,
  `dadaia_workspace/public/templates/*-AGENTS.md`.
- A11.2 A repository-wide grep for `public/rules` returns zero hits outside
  `specs/_archive/**` and this SPEC.
- A11.3 The permission table states explicitly that `public/data/DADAIA.md` is the **law
  source** and that its *projections* remain PROTECTED and human-only (`DADAIA.md` §7) —
  the source/projection distinction ADR #7 turns on.

### FR12 — Rename ripple: zero stale references

Scenario 1 (ADR #12/E-6): three names change — `dadaia-release-definition` →
`dd-release-definition`, `dadaia-release-closure` → `dd-release-closure`,
`drift-detection` → `dd-audit-project`. Every textual reference is updated in this release.
The verified live reference set (grep over the working tree, `specs/_archive/**` and
`CHANGELOG.md` excluded as history):

| File | Reference | Owner |
|---|---|---|
| `public/agents/product-engineer.md` | frontmatter `skills:` `:16`; body `:156`, `:165`, `:200`, `:275`, `:360`, `:374` | ai-engineer |
| `public/agents/project-auditor.md` | frontmatter `skills:` `:17`; body `:131`, `:198` | ai-engineer |
| `public/skills/dadaia-gitflow/SKILL.md` | See-also `:88` | ai-engineer |
| `public/skills/dadaia-grill-me/SKILL.md` | `:37`, `:41` | ai-engineer |
| `public/skills/dadaia-test-stewardship/SKILL.md` | `:67`, `:168`, `:170` | ai-engineer |
| `public/skills/project-orchestration/SKILL.md` | `:236` (also C9) | ai-engineer |
| `public/skills/dd-release-definition/SKILL.md` | its own `:88` reference to the closure skill | ai-engineer |
| `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py:42` | `_CODEX_SKILL_REF_PREFIXES` literal | **software-engineer** (FR13) |
| `tests/e2e/features/test_public_pipeline.py:47-…` | `EXPECTED_SKILLS` golden set | **software-engineer** (FR13) |
| `tests/unit/infrastructure/_golden/doctor_all_four_v0158.json` | 6 path lines | **software-engineer** (FR13) |
| `tests/unit/infrastructure/_golden/install_target_resolution_v0158.json` | ~10 path lines | **software-engineer** (FR13) |

**Note a correction to the design map (Part D):** `product-engineer.md`'s frontmatter
carries **one** stale entry (`dadaia-release-closure`), not two —
`dadaia-release-definition` is absent from every agent's `skills:` list today, though the
persona body invokes it at `:275`. FR13 fixes the wiring.

`CHANGELOG.md` historical entries (`:128`, `:140`) and `specs/_archive/**` are **not
edited** — history is history; `_archive/` is FROZEN.

**Acceptance**

- A12.1 `grep -rn "dadaia-release-definition\|dadaia-release-closure\|drift-detection"`
  over the working tree, excluding `specs/_archive/**` and `CHANGELOG.md`, returns
  **zero** hits.
- A12.2 The same grep for the three new names returns a hit in every row of the table
  above.
- A12.3 No projected tree (`.claude/`, `.agents/`, `.codex/`, `.kimi-code/`) or staging
  tree (`.dadaia/agentic/`) retains a directory under an old name (see FR14).

### FR13 — Skill wiring: frontmatter grants, the Codex D-CX-7 prefix gate, test goldens

Three wiring surfaces must move with the family, or the family ships unreachable or
unvalidated.

**(a) Agent frontmatter `skills:` grants.** Each `dd-` skill is granted to the agents that
run its stage:

| Skill | Granted to |
|---|---|
| `dd-backlog-definition` | `project-manager` |
| `dd-release-definition` | `product-engineer`, `project-manager` |
| `dd-release-implement` | `software-engineer`, `ai-engineer`, `qa-engineer` |
| `dd-release-closure` | `product-engineer` |
| `dd-audit-project` | `project-auditor` |
| `dd-bug-registration` | all nine core agents |
| `dd-bug-fix` | `software-engineer`, `ai-engineer` |

**(b) The Codex D-CX-7 gate — a silent-fail-open risk.**
`dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py:42` holds
`_CODEX_SKILL_REF_PREFIXES`, consumed by `infrastructure/codex_doctor.py:269`: a skill name
cited in a projected Codex persona is only checked for existence **when it starts with one
of those prefixes**. The tuple contains the literal `"drift-detection"`. If the rename
lands without updating it, D-CX-7 stops validating that reference **and never validates a
single `dd-` skill** — the check degrades to a silent no-op for the entire new family, with
no error and no drift line. The tuple must lose `"drift-detection"` and gain `"dd-"`.

This is the one production-code touchpoint of the release; it belongs to
`software-engineer`, per `DADAIA.md` §2.

**(c) Test goldens.** `EXPECTED_SKILLS` and the two `_golden/*.json` fixtures pin the
literal skill set: 21 today → **25** after this release (21 with three renamed in place,
plus four net-new).

**Acceptance**

- A13.1 Every grant in table (a) exists in the named agent's frontmatter `skills:` list.
- A13.2 `_CODEX_SKILL_REF_PREFIXES` contains `"dd-"` and does not contain
  `"drift-detection"`.
- A13.3 A **new contract test** proves D-CX-7 is live for the family: a projected Codex
  persona citing a non-existent `dd-` skill produces the `missing skill` ERROR line, and
  one citing a real family skill does not. Test intent declared at birth:
  `Intent: CONTRACT — v0.10.0 A13.3`.
- A13.4 `EXPECTED_SKILLS` equals the 25-name set; both golden JSON fixtures are
  regenerated and the suite is green.
- A13.5 `dadaia public doctor` emits no `[missing]`/`[drift]`/`ERROR` line attributable to
  a skill reference.

### FR14 — Projection integrity and orphan removal

The family lands through the §7 chain: source change → `dadaia public stage` →
`dadaia public install --target all` → `dadaia public doctor` green including
`[ok] public-privacy`.

**Orphan hazard, verified.** `stage()` (`infrastructure/public_assets.py:414`) rebuilds
staging with an `rmtree`, so staging self-heals on a rename. `install` copies staged →
projected and **prunes nothing**: after a rename the old directories
`.agents/skills/<old>/`, `.claude/skills/<old>/` (and any harness tree carrying them)
survive as orphans that no doctor pass compares. They must be removed explicitly.

**Acceptance**

- A14.1 `dadaia public stage`, `dadaia public install --target all` and
  `dadaia public doctor` run clean in that order; doctor reports `[ok] public-privacy` and
  exits 0.
- A14.2 No directory named `dadaia-release-definition`, `dadaia-release-closure` or
  `drift-detection` exists under `.dadaia/agentic/skills/`, `.agents/skills/`,
  `.claude/skills/`, `.codex/` or `.kimi-code/` after the release.
- A14.3 Each of the seven family skills is present and byte-identical between the canonical
  source, `.dadaia/agentic/skills/`, `.agents/skills/` and `.claude/skills/`.
- A14.4 The e2e `EXPECTED_SKILLS` equality assertions pass for both the staged tree and the
  installed `.agents/skills/` tree.

### FR15 — Token-economy accounting as closure evidence

The release's stated purpose is recurring per-session savings. It must be measured, not
asserted.

A baseline is captured **before** any edit and the same measurement is repeated after:

| Surface | Metric | Baseline (Part A, 2026-08-14) |
|---|---|---|
| `public/data/DADAIA.md` (always-on, every agent, every session) | `wc -w`, `wc -l` | 2,423 words |
| `public/data/AGENTS.md` (always-on root pointer) | `wc -w` | 200 words |
| The 7 family skills (on-demand) | `wc -l`, `wc -w` per file | n/a (4 new) |
| `dadaia-cli`, `dadaia-gitflow`, `project-orchestration` (on-demand, dehydrated) | `wc -w` | 867 / 733 / 1,887 words |

**Acceptance**

- A15.1 Baseline figures are re-measured on the release branch at implementation start
  (the Part A figures are a 2026-08-14 reference, not the acceptance datum) and captured
  under `.dadaia/tmp/ai-engineer/<YYYYMMDD>/`.
- A15.2 `public/data/DADAIA.md`'s post-release word count **does not exceed** its measured
  baseline. The C1 amendment adds text and C3/C5/C6 remove more; net non-increase is the
  bar, and the itemized cut-vs-addition arithmetic is recorded.
- A15.3 `CLOSURE.md` carries a before/after table for every row above, with the measuring
  command, and states the always-on saving in words and in estimated tokens (≈1.33
  tokens/word, the ratio used throughout the design report).
- A15.4 The on-demand surfaces are allowed to grow — the release moves cost from always-on
  to on-demand by design. CLOSURE states the total on-demand growth alongside the
  always-on saving, so the trade is visible rather than hidden.

### FR16 — Operator-gated backlog intake (operator ADR #15, 2026-08-15)

**The doctrine.** The backlog is the operator's demand queue. **Only the operator creates
demand.** No agent — `project-manager` included — materializes a technical residual (a
review finding, a CLOSURE return, a reviewer note, an audit observation) directly into the
backlog. At each release close and each review round, the PM **compiles residuals into an
intake report** and presents it to the operator; each item is approved, rejected or
discarded **before** it can become a backlog entry. An operator-ratified deferral taken
during a release ("defer to backlog", recorded in the SPEC or at approval) is **pre-approved
intake** and is not re-adjudicated.

**Why.** After v0.9.0, the then-current CLOSURE-returns doctrine had the PM materialize 12
entries directly. The operator rejected that model: auto-generated P3 residuals polluted
the demand queue. The gate restores the queue to what it is for.

**The intake report artifact.** It is a human-facing deliverable, so `DADAIA.md` §4's
handoff-first rule already fixes its shape: a JSON handoff whose `next_handoff.agent` is
`human`, plus the HTML report it points at, under
`.dadaia/reports/<context>/project-manager/<UTC>-intake.html`. No new artifact class and no
new path convention is invented.

**Surfaces that today describe the superseded flow and are corrected in this release:**

| # | Surface | Current text | Change |
|---|---|---|---|
| I1 | `public/data/DADAIA.md:176-180` | "routes additions through the PM" | FR9-C1 surviving text (operator-gated wording) |
| I2 | `public/skills/dd-release-closure/SKILL.md` (ex `:110-117`) | `## Backlog returns` → `ideas.md` / `candidates.md` | FR5 change 2 — `## Intake candidates` |
| I3 | `public/skills/dd-backlog-definition/SKILL.md` | (new file) | FR2 section 5 — the canonical statement of this doctrine |
| I4 | `public/agents/product-engineer.md:370` | CLOSURE step 6 "**Backlog returns** — items pushed to `backlog/ideas.md` or `backlog/candidates.md`" | becomes "**Intake candidates** — residuals listed for the PM's operator-facing intake report; PE creates no backlog entry" |
| I5 | `public/agents/qa-engineer.md:253-255` | "product-engineer reads this stub and transcribes it as a bullet in `specs/backlog/candidates.md ## Hotfixes pendentes`" | stale on three axes (PE does not write backlog; `candidates.md` dissolves under ADR #14; direct materialization is now forbidden) — becomes: the hotfix-candidate stub is routed to the PM's intake report |
| I6 | `public/agents/project-manager.md:83-87` ("Core identity — backlog owner") | "sole agent that curates `specs/backlog/**`" | keeps curation, **gains** the intake gate: curation is downstream of an operator decision; the PM compiles and presents, it does not create demand |
| I7 | `public/skills/project-orchestration/SKILL.md:37`, `:55` | PM row "Backlog/bug intake"; "Backlog definition \| `project-manager` (curates)" | one-line correction naming the intake gate and pointing at `dd-backlog-definition` |
| I8 | `public/skills/ai-harness-codex/SKILL.md:339` | intake row yielding "backlog candidate / bug" | corrected to "intake report item / bug" |

**Acceptance**

- A16.1 The doctrine appears **exactly once** as a full statement, in
  `dd-backlog-definition` (FR2 section 5); I1, I2 and I4–I8 carry a one-line
  correction or reference, never a second copy (proxy-2 clean).
- A16.2 Every row I1–I8 is corrected as described.
- A16.3 A grep over `dadaia_workspace/public/**` for `backlog/ideas.md`,
  `backlog/candidates.md` and `## Hotfixes pendentes` returns zero hits.
- A16.4 No text anywhere in `public/**` instructs an agent to create, add, append or push
  a backlog entry as the outcome of a closure, review, audit or reviewer note.
- A16.5 The pre-approved-intake carve-out (operator-ratified deferrals) is stated once, in
  `dd-backlog-definition`, and is what `dd-audit-project` and `dd-release-closure`
  reference when they route a disposition.
- A16.6 The intake report's location and shape are stated as an application of the
  existing handoff-first law, with no new artifact class introduced.

---

## 4. Out of scope (non-goals)

1. **Fleet-wide `dadaia-*` → `dd-*` rename (Scenario 2).** ADR #12/E-6 chose Scenario 1.
   The remaining 11 `dadaia-*` skills keep their names. Scenario 2 crosses three ownership
   boundaries, including a production hook docstring
   (`dadaia_workspace/hooks/ctx_inject.py:305`) and law-cited names, and is a separate
   future release if the operator wants it.

2. **`specs/backlog/codex-persona-law-context-dehydration.md` — NOT absorbed; stays a
   candidate.** See §6-D for the full reasoning and the baseline-invalidation warning it
   inherits from this release.

3. **The bug reservation primitive (ADR #10/E-4).** `dd-bug-fix` documents today's
   advisory-presence signal only. The new `BugEventKind`, its coherence rules and CLI live
   in `specs/backlog/bug-picked-ledger-event.md` — a `software-architect` +
   `software-engineer` schema change that must not contaminate an AI-surface release.

4. **The physical consolidation of `specs/backlog/**` into `BACKLOG.md`.** `specs/backlog/`
   is `project-manager` surface (`DADAIA.md` §2); `product-engineer` does not curate it and
   `ai-engineer` does not either. This release ships the **doctrine** (law + skill); the PM
   performs the consolidation. Delegated — see §7.

5. **Backlog tooling reconciliation.** The per-entry-file model is wired into production
   Python and scaffolding: `features/backlog/{doctor,ledger,ledger_writer,preview,
   removal_lifecycle}.py`, `features/spec_artifacts/new_artifacts.py` +
   `cli/commands/newartifacts.py` (`dadaia backlog new <slug>`),
   `features/specs/doctor_governance.py` (`SPEC-DOC-031`), the `BL-SCHEMA`/`BL-STALE`
   codes, `public/scaffold/backlog/README.md`, and
   `public/data/CONSUMER_VALIDATION_RECIPE.md`. Reconciling all of that with a single
   `BACKLOG.md` is a `software-engineer` release, not an AI-surface one. **This release
   does not touch it, and therefore does not break it**: the doctrine is documented and the
   tooling keeps working against per-entry files until the follow-up ships. The
   consequential decision is surfaced for ratification in §8.

6. **No new CLI verb, no new doctor validator, no new script.** In particular, no
   `BACKLOG.md` schema validator and no automated shingle-duplication linter — FR1's
   proxy-2 check is a documented command run by `qa-engineer` at review and recorded in
   CLOSURE.

7. **F-1 (`dadaia-cli` reachability).** `dadaia-cli`'s description claims "all agents may
   use it" while it appears in **no** agent's frontmatter `skills:` list — so under
   frontmatter-scoped grants it is reachable only by the top-level session. Pre-existing,
   independent of this family; routed to `project-manager` as an entry, not fixed here.

8. **`memory-ctx` in `_CODEX_SKILL_REF_PREFIXES`.** The tuple already names a skill that
   does not exist in `public/skills/`. Pre-existing; FR13 changes only the two entries the
   rename requires. Routed to the PM as an observation.

9. **Remediation of the 12 entries materialized after v0.9.0.** ADR #15 rejects the model
   that produced them; deciding what happens to those 12 existing files (retain, present
   for retroactive operator adjudication, or LEDGER them) is `project-manager` curation
   work on `specs/backlog/**`, not an AI-surface change. This release fixes the **rule**;
   the queue cleanup is delegated (§7).

10. **`public/scaffold/backlog/README.md`.** The consumer-seeded backlog README documents
    the per-entry-file tooling (`dadaia backlog new`, `backlog doctor`, `BL-SCHEMA`) and
    is left untouched with §4.5 — rewriting it before the tooling changes would ship a
    consumer a README describing a model its CLI does not implement. Consumers still
    receive the intake doctrine, because it is in the projected law (FR9-C1).

11. **No memory-atom rewrite beyond §5's list, no constitution change, no production code
    beyond FR13's named touchpoints, no changes under `specs/_archive/**` (FROZEN).**

---

## 5. Memory files affected at closure

| File | Change | When |
|---|---|---|
| `specs/memory/product/distribution/public-asset-distribution.md` | the "Universal skills have one canonical home" paragraph names the `dd-` family as the lifecycle skill surface alongside `dadaia-gitflow` / `dadaia-test-stewardship` | **CLOSURE** |
| `specs/memory/product/agents/agentic-entities.md` | universal-surface section records that the cycle's seven `dd-` skills are universal (no registry entry, one canonical `.agents/skills/` home) | **CLOSURE** |
| `specs/memory/product/sdd/sdd-bug-backlog-governance.md` | the backlog paragraph becomes the single-source `BACKLOG.md` ACTIVE+LEDGER doctrine with purge-on-pick **and the operator-gated intake rule (ADR #15)**; the runtime-state list (`specs/backlog/*.md`) is updated to state the doctrine and the pending consolidation | **CLOSURE** |
| `specs/memory/product/agents/agent-comms.md` | only if closure judges the intake report a new handoff usage worth recording; expected **no change** — FR16 introduces no new artifact class | **CLOSURE** |
| `specs/memory/product/agents/agent-orchestration.md` | the ordered-lifecycle paragraph names the skill that owns each stage | **CLOSURE** |
| `specs/memory/product/catalog.json` | regenerated only if a touched atom's `tldr`/`summary` changed (`public/scripts/generate-memory-catalog.py`) | **CLOSURE** |
| `specs/memory/architecture.md` | no change expected — no layer boundary, port or module contract changes (FR13 edits a constant and a test) | — |
| `specs/memory/tech-stack.md`, `specs/memory/product/index.md` | no change — no dependency added, no product feature added or removed | — |

---

## 6. Dependencies and risks

| # | Item | Status |
|---|---|---|
| D1 | ADR #7/E-1 authorizes `ai-engineer` to author the law **source** under three guardrails: (a) only inside an approved task naming the file, (b) the same release fixes F-0, (c) the law diff is eyeballed pre-merge | (a) T-100-11 write set · (b) FR11 · (c) A9.6 |
| D2 | `product-engineer` has no shell | every git and measurement step is an explicit TASKS entry owned by the dispatcher, `software-engineer` or `ai-engineer` |
| D3 | FR13 crosses into `software-engineer`'s surface | one task (T-100-14), narrowly scoped to a constant, a new contract test, and golden regeneration |
| D4 | PM purge-on-pick of the consumed candidate | Pending — see §7 |
| D5 | The physical `BACKLOG.md` consolidation is PM work that this release's law now describes | ordering: law ships first, consolidation follows; §4.4 and §8 make the gap explicit rather than silent |
| R1 | **Silent doctor degradation.** The rename lands without the prefix-tuple update and D-CX-7 quietly stops checking the whole family | FR13/A13.2 + the A13.3 contract test that would fail if the gate went inert |
| R2 | **Orphan projections.** `install` prunes nothing; old skill directories linger in `.agents/`, `.claude/` and harness trees | FR14/A14.2 makes removal an acceptance criterion; A14.4 pins it in a fresh tree |
| R3 | **Dehydration removes classification signal.** An agent can no longer tell which arm/stage it is in from the law alone | C2/C4 kept verbatim; §1 and §2 untouched (A9.3); every cut leaves a one-line pointer naming its destination skill |
| R4 | **The law grows instead of shrinking.** C1 adds the BACKLOG doctrine while C3/C5/C6 remove | A15.2 makes net non-increase an acceptance criterion with itemized arithmetic |
| R5 | **Duplication reappears.** Seven new files invite copy-paste of the same law paragraph | FR1 proxy 2 (shingle scan) is an acceptance criterion, not a style wish; A1.3 records the command and its output |
| R6 | **The doctrine outruns the tooling.** The law describes `BACKLOG.md` while `dadaia backlog new`/`backlog doctor` still write and validate per-entry files | §4.5 declares the boundary; A10.3 forces CLOSURE to repeat it; §8 asks the operator to ratify the gap and its follow-up |
| R7 | **Privacy.** Everything this release authors is pushed and scanned by the v0.9.0 range-scoped denylist gate | standing rule in TASKS: synthetic terms only; no foreign context name, repo slug, hostname, IP or absolute local path in any authored skill, law, agent, test or spec file — including this one |
| R8 | **Reachability.** A projected skill nobody is granted is a skill nobody uses | FR13(a) grants the family per stage |
| R9 | **A rename touching four projected trees drifts one of them** | A14.3 byte-verifies source ↔ staging ↔ `.agents` ↔ `.claude`; `public doctor`'s three passes back it |
| R10 | **The intake gate is stated in the new skill but the old flow survives in an unedited persona.** Six of the eight ADR #15 surfaces are outside the family's own files | FR16's I1–I8 table enumerates every one, verified by A16.2–A16.4; the greps in A16.3/A16.4 are what make "no residual old flow" mechanical rather than a reading exercise |
| R11 | **The gate stalls the residual flow.** Findings pile up with no queue while the operator has not yet run an intake round | FR16 makes the intake report a **release-close obligation** of the PM, not an ad-hoc favour; residuals stay recorded in CLOSURE's `## Intake candidates` (A5.4/A5.5) so nothing is lost while it waits |

### 6-D — Disposition of the orbiting Codex candidate

`specs/backlog/codex-persona-law-context-dehydration.md` orbits this release: both are
"dehydration" work and both touch persona text. **Decision: not absorbed — it stays a
candidate, and is an explicit non-goal (§4.2).** Three reasons, in order of weight:

1. **Different surface, different owner.** This release dehydrates the *always-on rule
   source* and authors *skills* — `ai-engineer`'s exclusive lane. The Codex candidate's
   dehydration target is the **generated** `.codex/agents/*.toml`, produced by
   `infrastructure/runtime_transforms/codex_assets.py#_render_codex_agent_toml`, plus
   `codex_doctor.py`, `features/certification/service.py` and `hooks/ctx_inject.py` — all
   `software-engineer` production code, with live-probe certification that is
   `qa-engineer` work. Its seven `intents[]` are `kind: code` on five distinct Python
   modules. Merging them makes an AI-surface release a production release.

2. **Its acceptance criteria become unsatisfiable if merged.** The candidate requires
   *"for identical staged inputs, before/after SHA-256 manifests for `.claude/agents/**`,
   `.kimi-code/**` and their harness configuration outputs are byte-identical; Codex is the
   only changed projection"*. This release changes `.claude/` and `.agents/` projections by
   construction (three renamed skills, four new ones, two edited personas). Run together,
   that criterion cannot be met and would have to be weakened — which is exactly the
   safeguard it exists to provide.

3. **No ADR absorbs it.** The 2026-08-14 grill dispositioned fourteen items and sequenced
   four releases; the Codex candidate appears in none of them. Absorbing it now would be a
   scope decision taken outside the grill that settled this release's scope.

**Inherited consequence, recorded so it is not discovered later.** This release invalidates
the Codex candidate's numeric baseline. That candidate pins *"nine generated Codex agent
TOMLs totaling 124,557 bytes; smallest 8,208; largest 22,836"* and derives its target
(*"at most 49,823 bytes, at least 60% below baseline"*) from it. v0.10.0 edits
`public/agents/product-engineer.md`, `project-auditor.md` and `ai-engineer.md` (FR11, FR12,
FR13a) — all three are rendered into Codex TOMLs — so the byte census must be **re-measured
after v0.10.0 ships** and the candidate's figures rewritten before it is picked. Routed to
`project-manager` as a backlog-entry rewrite, in the same class as ADR #6's rewrite of
`test-suite-remediation-stewardship`.

One item is **not** an absorption but a ripple of this release's own rename: FR13(b) edits
`_CODEX_SKILL_REF_PREFIXES` in `codex_assets.py`, a file the Codex candidate also targets.
The edit is two tuple entries and changes no rendering behavior; it does not overlap any of
the candidate's seven intents.

---

## 7. Traceability and provenance

| Item | Provenance | Disposition |
|---|---|---|
| `specs/backlog/20260814-dd-lifecycle-skills-family.md` | operator thesis, 2026-08-14; grill ADRs #7–#14 | **picked** — this release; terminal `DELIVERED — v0.10.0` at closure |
| ADR #14 (single-source `BACKLOG.md`) | grill, operator-ratified | **partially delivered**: doctrine in law (FR10) + schema in `dd-backlog-definition` (FR2). Physical consolidation → PM; tooling → follow-up release (§4.4, §4.5) |
| **ADR #15 (operator-gated intake)** | operator, ratified 2026-08-15, after the v0.9.0 12-entry materialization | **delivered as FR16** — rule in law (C1), full doctrine in `dd-backlog-definition`, closure re-routed (FR5), six external surfaces corrected (I4–I8). **Supersedes** the design report's free "proposal intake" spine item and any CLOSURE-returns wording that predates it |
| The 12 backlog entries materialized after v0.9.0 | the model ADR #15 rejects | **retroactive adjudication** (operator, 2026-08-15 — §8): PM compiles the first ADR #15 intake report with the **8 technical residuals** for operator decision; the **4 operator deferrals are pre-approved intake**. Queue cleanup remains **delegated to the PM** and outside this release (§4.9) |
| `specs/backlog/bug-picked-ledger-event.md` | ADR #10/E-4 | **not picked** — referenced by name from `dd-bug-fix` (A8.3) |
| `specs/backlog/codex-persona-law-context-dehydration.md` | operator Codex audit, 2026-08-14 | **not absorbed** — stays `candidate`; §4.2 + §6-D; PM to rewrite its byte baseline after this release ships |
| `specs/backlog/test-suite-remediation-stewardship.md` | ADR #6 | untouched — awaiting PM rewrite |
| `specs/backlog/retire-dead-hotfix-surface.md` | operator ruling D4 | untouched — the dead `release_hotfix.md.j2` / `closure_hotfix.md.j2` templates and the `specs hotfix open` verb are **not** removed here; `dd-bug-fix` describes the live no-ceremony flow only |
| `specs/backlog/changelog-version-axis-reconciliation.md` | prior release return | untouched — the closure version bump follows today's gitflow contract (package axis currently `0.6.0`) |
| F-1 (`dadaia-cli` not granted to any agent) | design report Part A | **new PM entry** (§4.7) |
| `memory-ctx` phantom prefix | verified this session | **new PM entry** (§4.8) |

**Purge-on-pick (ADR #14) — delegated and pending.** The doctrine requires the picked entry
to leave the live backlog in the same commit that creates the release SPEC, with provenance
recorded here. `specs/backlog/**` is `project-manager` surface; `product-engineer` does not
curate it. Therefore:

- this section **is** the provenance record the doctrine requires;
- removal of `20260814-dd-lifecycle-skills-family.md` from the live backlog, and its LEDGER
  line, are **delegated to `project-manager` and pending** at authoring time;
- the pending purge is a precondition check of T-100-01, so the definition commit carries
  it if the PM has acted by then; CLOSURE records the state either way.

---

## 8. Approval

**Approved by the operator on 2026-08-15** (via dispatcher), **as written** — no scope
change. SPEC, PLAN and TASKS all carry `**Status:** Aprovado`; milestone (a) of the
`dadaia-gitflow` contract may fire once the definition commit (T-100-01) lands.

Ratified with the approval:

- **D-A — the ADR #14 scope split (§4.4, §4.5, §4.10, R6): the stated default is
  RATIFIED.** The grill recorded that the `BACKLOG.md` consolidation "lands inside this
  release"; verification against the tree showed three separable parts, and the operator
  ruled: **ship the doctrine now** (the §5 law amendment FR10 + the entry schema and
  purge-on-pick rule in `dd-backlog-definition` FR2); **the physical file merge is
  delegated to `project-manager`**; **the tooling is routed to a named follow-up
  release** — the five `features/backlog/*` modules, the `dadaia backlog new` verb,
  `backlog doctor`'s `BL-SCHEMA`/`BL-STALE`, `SPEC-DOC-031`, the consumer scaffold README
  and the validation recipe, all `software-engineer` surface. This release therefore ships
  a documented doctrine whose tooling still writes per-entry files, deliberately and
  visibly (A10.3 forces CLOSURE to repeat it).

- **D-B — the C1/C3/C5/C6 surviving law text (FR9): APPROVED with the SPEC, as written.**
  The four replacement paragraphs quoted verbatim in FR9 are the approved wording of the
  always-on law. Per ADR #11/E-5 the ai-engineer authors exactly that text at
  `public/data/DADAIA.md`, and the ADR #7/E-1 pre-merge law diff (A9.6) checks **fidelity
  only** — it is not a second wording review. Any deviation found at that diff is a defect
  to correct against this SPEC, not a new decision.

- **D-C — the F-0 allowlist correction (FR11): RATIFIED.** `ai-engineer`'s declared write
  surface moves from the non-existent `dadaia_workspace/public/rules/**` to the real paths
  — `public/data/*.md`, `public/scaffold/**/*AGENTS.md`, `public/templates/*-AGENTS.md` —
  in all three places (`ai-engineer.md:54`, `:100`, `:351`), with the permission table
  stating that `public/data/DADAIA.md` is the law **source** while its projections stay
  PROTECTED and human-only (`DADAIA.md` §7). This is the permission basis on which
  T-100-11 authors the law source; T-100-12 delivers it.

- **The 12 post-v0.9.0 entries (§4.9, §7): decision recorded — retroactive
  adjudication.** They are not grandfathered and not deleted. `project-manager` compiles
  the **first intake report** under the ADR #15 protocol, carrying the **8 technical
  residuals** for operator adjudication; the **4 operator deferrals are pre-approved
  intake** and are not re-adjudicated (the carve-out stated once in
  `dd-backlog-definition`, A16.5). The queue cleanup itself stays **delegated to the PM**
  and outside this release's scope — this release fixes the rule (FR16), not the queue.

**ADR #15 was ratified before approval, not requested at it.** FR16 implements it; the
only related operator word needed was the fate of the 12 entries, recorded above.

Still delegated and pending at approval time: the PM's purge-on-pick of the consumed
candidate `specs/backlog/20260814-dd-lifecycle-skills-family.md` (§7). It rides the
T-100-01 definition commit if performed by then; CLOSURE records the state either way.
