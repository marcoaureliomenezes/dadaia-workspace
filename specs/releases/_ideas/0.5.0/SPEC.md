# SPEC — Release 0.5.0 — governance, lineage and audits: make the bug loop visible

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** product-engineer
**Opened:** 2026-08-26
**Created:** 2026-08-26
**Location:** `specs/releases/_ideas/0.5.0/` — a **future-release Draft**, not the live
release. Promoted to `specs/releases/0.5.0/` by `git mv` when `v0.4.5` archives (operator
ruling **D6 of 2026-08-23**, the `_ideas/` lane). While it sits here it authorizes nothing:
no task is reserved, no backlog entry is purged, no bug is `picked`.
**Branch (at promotion):** `feature/0.5.0`, cut from `main` at the shipped `v0.4.5` (branch
model: `DADAIA.md` §4, operations: `dd-gitflow-default`). See **AS-5** — this supersedes the
`feature/0.4.6` cut named in `specs/releases/v0.4.5/TASKS.md` T-045-41.
**Consumes (declared at promotion, NOT executed by this Draft):** `specs-canon-v6`,
`entity-behavior-map`, `bug-lineage-and-commit-discipline`, `audit-canon-v1`,
`memory-two-tier-principles`, `dd-diagnose`
**Intended picked set:** the six `## ACTIVE` backlog entries above — the five entries the
2026-08-26 grill produced or amended, plus `dd-diagnose`, whose diagnosing method becomes
the home of the lineage check (**AS-11**). Bugs: **none picked**; the single open bug at the
time of writing, `windows-xdist-workers-crash-on-unit-fast-tier` (LOW), is governed by
**AS-4**.
**Grill (mandatory, done):** the operator ratification session of **2026-08-26** — 3 rounds,
18 questions, 20 decisions — handoff
`.dadaia/handoff/dadaia-workspace/2026-08-26T120000Z-claude-code-governance-lineage-audits-adr-grill.handoff.json`.
Its rulings **D1–D15** are the single source of decisions for this release and are carried
below verbatim in intent (§2.1). They are **not re-litigated here**. Everything this SPEC
adds beyond them is recorded as a numbered authoring decision (§2.2) or a stated assumption
(§2.3).

---

## 1. Problem and context — the loop this release makes visible

**The stated purpose, in the operator's terms.** *The agent, to solve one bug, creates
others — the infinite bug loop. This release makes that loop VISIBLE and MEASURABLE: every
bug carries its root cause, its lineage (`caused_by`), the commit that registered it
(derived) and the commit that resolved it; releases carry milestone shas; audits read that
history through git diffs and detect recurrences and fix-induced bugs; memory principles
become measured invariants gated by ADRs; the skill / `AGENTS.md` / `DADAIA.md` map is
validated by tests.*

Everything below is that sentence, decomposed into requirements.

### 1.1 The loop is documented, and it is not anecdotal

The 2026-08-23 skills audit and the 2026-08-26 grill's inspection pass measured it
(handoff `findings[1]`):

| Chain | Shape | What it proves |
|---|---|---|
| **gitignore class** | four recurrences — `backlog-candidates-md-tracked-violates-noncanonical-gitignore`, `grill-and-oq-decisions-records-gitignored-not-version-controlled`, `specs-bugs-jsonl-store-gitignored`, `backlog-gitignored-governance-vacuous`, `remote-bugs-gitignore-blocks-new-intake`, `gitignore-alpha-qa-review-untrackable`, `gitignore-code-review-artifact-untrackable`, `gitignore-verdict-evidence-untrackable-fourth-recurrence` — three of them fixed instance-by-instance | a symptom patch per instance; the class was never named, so the class kept firing |
| **certify probe** | the bug was re-registered **37 minutes** after its own fix (named as firing 1 of the v0.4.4 FR23 evidence gate) | a fix landed with no evidence that the failure was reproduced on the executed path |
| **frozen clock** | frozen-clock bug → a guard (**+294 LOC**) → the guard's own bug — three hops | the fix grew the feature; the growth was the next bug's cause |
| **bug-event ledger** | `bug-event-field-with-unicode-line-separator-silently-drops-the-event` + the ESC/CWE-117 finding, one seam, two symptoms | one seam produced a family; nothing in the record said so |

**132 of 471 resolutions carry zero evidence. 92 cross-bug references exist only as prose.**
No record has ever carried a structured cause, a lineage pointer, or a commit sha.

### 1.2 The history itself is coarse — measured, not assumed

A one-pass scan of every non-merge commit touching `specs/bugs/` **across all refs** (map
captured at `.dadaia/tmp/claude-code/20260826/bug-commit-map-all-refs.json`) says:

| Fact | Number |
|---|---|
| Bug ids / events in `specs/bugs/bugs.jsonl` | **490 / 1005** |
| Ledger commits visible on `main` / `develop` | 75 / 70 |
| Ledger commits reachable across **all refs** (the 50 `archive/*` tags preserve the retired feature branches) | **295** |
| `reported` lines whose first adding commit is found | **490 / 490** |
| …spread over distinct commits | **124**, of which **79** register exactly one bug; the largest single commit registers **105** |
| `resolved` lines whose first adding commit is found | **470 / 470** |
| …spread over distinct commits | **117**, of which **70** resolve exactly one bug; the largest resolves **91** |
| Resolved bugs whose first resolving commit is a **release-level squash** (`chore: ship …`, `feat(v0.x) …`, `fix: 0.3.0 …`) | **155** |
| Resolution commits that touch **any non-`specs/` file** (i.e. the fix is actually in that commit) | **78 / 117** |

Read plainly: **`main` is squash-only, so squash-to-main erased per-bug granularity for a
large part of the history**, and for 39 of 117 resolution commits the ledger line moved
without a line of code beside it. A bug whose "resolution commit" is a 91-bug release squash
cannot be diffed, so today **no audit can tell a real fix from a bulk status flip.** That is
precisely why the going-forward discipline this release installs is *one isolated commit per
registration* and *the fix contained in the commit that resolves* — and why every derived sha
must carry, honestly, how coarse it is.

### 1.3 The three governance surfaces that cannot see any of it

- **Audits** (`dd-audit-project` + `project-auditor`) compare memory against code on six
  dimensions **at HEAD**. They read no bug, no diff, no recurrence, no history. The persona
  is forbidden `specs/**` and writes HTML into `.dadaia/reports/`; `specs/audits/README.md`
  claims a folder convention no tool honours; `specs doctor`'s SPEC-DOC-036 checks
  dispositions by **regex over prose**; the skill carries `disable-model-invocation: true`
  and is absent from the persona's own skill list. The audit lane is, in effect, off.
- **Memory** carries no measurable rule. `architecture.md` (294 lines), `quality-assurance.md`
  (324), `tech-stack.md` (52) and `constitution.md` (261) state laws in prose while the
  mechanical truths that actually hold — **nine** `[importlinter:contract…]` sections in
  `setup.cfg`, the LOC ceilings, the complexity ratchet, the LARGE-test census, the diagram
  drift guards — live somewhere else entirely and are connected to memory by nothing.
- **The AI surface** has a partial map (`rules-skills-map.json` + its enforcer) covering
  topic → section → skill, with **no scoped `AGENTS.md` column** and no completeness
  requirement. A skill can exist with no law behind it, and a law with no skill.

### 1.4 The three pillars this release is built on

Every FR below is traced to these, and every review verdict must state them.

1. **Clean architecture.** Features are encapsulated; boundaries between them are explicit
   and narrow; side effects live at the edges; no feature reaches into another's internals;
   no shared mutable state; no cross-cutting helper that hides coupling. Historical shapes
   (the v5 bug event, the `{file,content}` legacy archive) are decoded by an **adapter at the
   boundary**, never by a branch in the middle of a feature.
2. **Bug-surface minimization.** Every FR states its **bug-surface direction** — what it
   deletes or simplifies — and its **bug-history evidence** — which prior bugs on that
   surface justify the shape chosen. The operator's standing order applies as an acceptance:
   a fix or a feature that adds a branch, a flag, a special case, a second code path, a
   cross-feature reach-in or a new side effect ("a **puxadinho**" — a lean-to bolted onto an
   existing structure) is refused, whatever the test result.
3. **Enforcement posture — D15, verbatim in intent.** *Skills instruct procedure. Audits
   measure conformance from git and JSONL history. Hooks and the CLI validate only at the
   publication boundary (push / PR) and never block a human.* This release adds **no new
   blocking CLI validation and no new hook block**; it *removes* one of each (FR9).

---

## 2. Objective, and the decisions that shape it

**Objective.** Leave the workspace with: one record per bug carrying cause, lineage and
provenance-marked commit shas for all 490 historical bugs; releases whose milestones are sha
ranges; an audit that reads that history and names recurrences and fix-induced bugs; memory
whose fundamental rules are numbered principles each naming the check that measures it, gated
by ADRs only the operator accepts; a skill ↔ `AGENTS.md` ↔ `DADAIA.md` map that a test turns
RED the moment it is incomplete; and **two fewer hook blocks than it started with**.

### 2.1 Operator rulings, ratified as given (D1–D15)

Source: the 2026-08-26 grill handoff, `findings[0].detail_md`. Reproduced in intent, mapped
to the FR that executes them. Nothing here is re-decided.

| # | Ruling (abridged — the handoff is authoritative) | Executed by |
|---|---|---|
| **D1** | Packaging: amend `specs-canon-v6` and `entity-behavior-map`; create `bug-lineage-and-commit-discipline`, `audit-canon-v1`, `memory-two-tier-principles` — separable releases, no 60-task umbrella | §7 (this release picks all six together — see **D-B**) |
| **D2** | Registration sha and resolution sha are never hand-written; the resolution sha is a **mutable field filled after** the fix commit exists; the registration sha is **derivable from git** | FR2, FR3, FR8 |
| **D3** | *(reverses 2026-08-23 D5)* `RELEASE.jsonl` milestone records carry `sha` (+ `pr`) at exactly three milestones — `defined`, `implemented`, `shipped` — plus `audited` when an audit runs; individual commits stay out | FR4 |
| **D4** | **No push on bug resolve.** Commit only; a push is operator-requested | FR8 |
| **D5** | Audits are Markdown in `specs/audits/<YYYYMMDD>-<slug>/AUDIT.md` + `FINDINGS.jsonl`, committed; `project-auditor` gains write to that folder | FR13 |
| **D6** | All three pillars (bug history · spec compliance · memory/constitution drift) run **together in every audit**; an audit is **SUGGESTED every 5 releases, never mandatory** | FR14 |
| **D7** | The audit window runs **from the last audited release to the current one**; each audit appends an `audited` milestone to the `RELEASE.jsonl` of the release it runs in | FR4, FR14 |
| **D8** | The lineage check lives in skills / scoped `AGENTS.md` / a short `DADAIA.md` section, **never as new CLI validation**: same component/surface, read prior resolution diffs in the window, declare `caused_by: <bug_id> \| none` with evidence; audits measure compliance | FR7, FR11, FR14 |
| **D9** | Hooks de-slop: the pre-commit `backlog doctor` block and the fail-closed runner are agent-created slop that blocked humans; pre-commit becomes advisory-only or is removed; pre-push keeps **only** the publication boundary (branch policy + denylist scan); the CI preflight leaves the hook and becomes an always-on rule | FR9, FR11 |
| **D10** | Commit shapes (isolated commit per bug registration / backlog entry / ADR; fix contained in the resolving commit; release definition = one bundled commit; `_ideas` SPEC = SPEC only) are **skill/AGENTS.md rules measured by the audit via `git log`** — not hooks | FR8, FR14 |
| **D11** | *(replaces 2026-08-23 D3 "event-sourced")* **ONE record per bug/finding, appended once**; core fields immutable, governance fields mutable; `RELEASE.jsonl` milestones are immutable facts | FR2, FR4, FR13 |
| **D12** | `specs/ADRs/` canonical, its own `AGENTS.md`, `NNNN-<slug>.md`, monotonic numbering never reused, Nygard+MADR fields incl. **Confirmation = `Measured by:`**; accepted is immutable; one decision per ADR; any agent proposes, **only the operator accepts**; the commit that changes a Part-1 principle carries the accepted ADR; no CLI verb, no doctor rule | FR19, FR20 |
| **D13** | Memory two-tier: `ARCHITECTURE.md`, `QUALITY.md`, `TECHSTACK.md` each split into **Part 1 Principles** (ADR-gated, every principle carries `Measured by:`; a principle without a measure is not admitted; first authoring = an inventory) and **Part 2 Implementation** (evolves with releases); `product/` = functional descriptions; `constitution.md` references the principles | FR17, FR18, FR21 |
| **D14** | **Every** core skill and **every** scoped `AGENTS.md` maps to exactly one `DADAIA.md` section; validated by contract tests that go RED on any unmapped member or any section with no owner | FR10 |
| **D15** | Enforcement posture (§1.4 pillar 3) — the acceptance criterion of every FR in this release | FR11 + §3 standing rules |

### 2.2 Authoring decisions taken by `product-engineer` (D-A … D-J)

- **D-A — The provenance-marker rule (a design law this release installs).** Every value this
  release *derives* or *infers* carries, in the same record, a closed-vocabulary marker
  saying how it was obtained. Two markers exist: `commit_granularity`
  (`exact | release-squash | ledger-only`) on each derived sha, and `lineage_source`
  (`declared | text-reference | null`) on `caused_by`. **Rationale:** without them an audit
  reads a 91-bug release squash as if it were a fix diff and manufactures false lineage
  findings — fabricated evidence is worse than no evidence. They are *closed enumerations on
  a record*, never branches in code: pillar 1 filters `commit_granularity == "exact"` instead
  of sniffing commit messages heuristically, which makes the pillar **smaller**, not bigger.
- **D-B — One release, six entries, and the BL-CONFLICT adjudications collapse.** The five
  2026-08-26 entries and `dd-diagnose` carry cross-ownership adjudications ("this file's edit
  is owned by `entity-behavior-map`", "`LINEAGE.md` is owned by `bug-lineage-…`") written for
  the case where they land in *different* releases. They land in **one** release here, so the
  conflicts dissolve: §3 assigns **exactly one owning FR to every file**, and that assignment
  is the ownership of record for this release. A second FR may *touch* an owned file only
  under the owner's stated contract, in a later task, never concurrently — and four files are
  **single-writer, no exceptions**: `dadaia_workspace/public/data/DADAIA.md` (FR11),
  `specs/constitution.md` (FR21), `dadaia_workspace/public/entities/behavior-map.json` (FR10)
  and `dadaia_workspace/public/skills/dd-bug-resolution/SKILL.md` (FR12).
- **D-C — The historical derivation is one algorithm, run once, over all refs.** §3/FR3
  states it in full. It replaces the per-bug `git log -S` pickaxe (which is O(bugs × history)
  and, on this repo, returns ambiguous multi-commit matches) with a **single chronological
  pass over the 295 ledger commits**, keyed by the bug id token on added lines. One pass, one
  map, one report.
- **D-D — `registration_commit` and `resolved_commit` are caches of one derivation, never
  hand-written (honours D2).** Both are stored so an agent reading the ledger does not have to
  re-walk 295 commits, and both are recomputable; one resolver function is the only reader,
  and a contract test asserts the stored value equals the derived value on a sample. See
  **AS-1** for the fill mechanism.
- **D-E — Segments `S1 … S4`, one flat `TASKS.md`.** Same shape as v0.4.4 and v0.4.5: the
  segments are blocks inside one marker surface; the live release directory carries no
  `segment:` line. (`ACTIVE.md` itself retires inside this release — FR4 — so segment state
  moves into `RELEASE.jsonl`'s `phase` events from the moment FR4 lands.)
- **D-F — `expand → switch → contract` for every retirement.** FR2/FR3 (event stream →
  record), FR4 (`ACTIVE.md`/`CLOSURE.md` → `RELEASE.jsonl`), FR5 (in-file LEDGER → histo
  JSONL), FR9 (hook blocks → nothing), FR12 (skill renames) each retire a surface: add the new
  path, switch every consumer, only then delete the old — each step independently green. A
  retirement that arrives as one big-bang commit is refused at review.
- **D-G — `releases_histo.jsonl` is the home of back-filled history.** Canon v6 gives
  `releases/_archive/{version}/` to *future* archives and deletes root `specs/_archive/`. The
  milestone shas of the **already-archived** releases therefore need a home that survives that
  deletion: `specs/releases/_archive/releases_histo.jsonl`, one milestone line per historical
  release — symmetric with `bugs/_archive/bugs_histo.jsonl` and
  `backlog/_archive/backlog_histo.jsonl`. Three areas, one convention. (Not named by the
  entry — flagged in §8.)
- **D-H — The destructive deletion is tagged first and operator-present.** FR6 deletes root
  `specs/_archive/` under the 2026-08-23 ruling *"git history is the archive"*. Before the
  deletion, an `archive/specs-archive-<YYYYMMDD>` git tag is pushed so the tree stays
  reachable by sha forever (`dd-gitflow-default` §6). The deletion runs **only with the
  operator present**, and only after FR3 and FR4 have read everything they need from it.
- **D-I — `dd-diagnose` owns the lineage check as its phase 0.** The operator's dispatch
  names it; D8 names no file. See **AS-11** for the deviation from the entry's intent ref and
  its reason.
- **D-J — The `rc` lane.** `S1 … S4` are internal work boundaries on `feature/0.5.0`, each
  closed by a `qa-engineer` review **committed on the branch** — no merge, no PR, no `rc`
  burned. `rc-1` ("release candidate 1" — a state of the specs, never a branch name) burns
  when the whole scope is implemented, gate-green and QA-closed, and is merged into `develop`.
  `rc-2 … rc-N` are adjustment rounds on that same scope; **no new backlog ever enters an
  `rc`**. The final `rc` carries memory → CLOSURE → archive and ships. If nothing is found,
  the final `rc` **is** `rc-1`. The definition PR that opens once SPEC/PLAN/TASKS are
  `Aprovado` burns no `rc` (`DADAIA.md` §4).

### 2.3 Stated assumptions (decided here, non-blocking, each with its reason)

| # | Assumption | Options considered, and why this one |
|---|---|---|
| **AS-1** | **`resolved_commit` fill: derive-on-read is the authority; a follow-up ledger-only commit is the cache write.** After the resolving commit exists, the same session appends `chore(bugs): <id> resolved @<sha>` staging only the ledger line. Audits and the CLI **never trust the field over git**: one resolver returns the stored value when present and derives it otherwise, and pillar 1 flags a stored value that disagrees with the derivation | **(i) follow-up ledger commit alone** — explicit, but a missed follow-up leaves a permanent hole; **(ii) derive-on-read alone** — zero extra commits, but every reader re-walks the history. **Chosen: both, with one authority.** A commit cannot contain its own sha (the handoff's open reconciliation, `findings[2]`), so the field is a cache by construction. This is **not** a second code path: there is one resolver seam, and the cache is verifiable against the authority. Nothing in the five entries argues against it; the entry itself declares the field nullable so both are admissible |
| **AS-2** | **Historical `caused_by` is `null`, not `"none"`.** `null` = never assessed; `"none"` = a fixer looked at the prior diffs in the window and found no causal link. The entry's rule *"`caused_by` never absent on a resolved record"* binds records **resolved from this release onward** | Writing `"none"` on 470 historical records would assert an assessment nobody made — fabricated evidence, the exact failure mode D-A exists to prevent |
| **AS-3** | **`specs/bugs/_archive/archive.jsonl` (114 legacy `{file, content}` records) stays byte-frozen**, beside the new `bugs_histo.jsonl`; it is excluded from the record model and from every audit window | Converting free-form Markdown bodies into structured records means *inferring* `symptom`/`repro`/`cause` from prose, into a model whose whole purpose is measured truth. All 114 are terminal and predate every discipline here. Canon v6 already sets the precedent for the backlog (*"legacy `_archive/*.md` stay frozen, no retro-conversion"*); this applies it to bugs by symmetry |
| **AS-4** | **`windows-xdist-workers-crash-on-unit-fast-tier` (LOW) is not picked.** If `v0.4.5` closes it, nothing to do; if `v0.4.5` ends with it open (its **AS-5**), it migrates into `BUGS.jsonl` as `status: open`, `cause: null`, `caused_by: null` and stays open | `dd-release-definition` §2: a bug that is neither fixed nor subsumed is not picked. A quarantine is never a resolution |
| **AS-5** | **The branch is `feature/0.5.0`**, superseding the `feature/0.4.6` cut named in `specs/releases/v0.4.5/TASKS.md` T-045-41 | The number of the next branch is the number of the next release actually picked. This canon change is consumer-visible (the `specs/` pattern moves 5 → 6), so MINOR is the honest bump. **This Draft edits no file of the live `v0.4.5` release** — the substitution happens at promotion |
| **AS-6** | **Publication is not assumed.** `pyproject.toml` bumps to `0.5.0` at the final `rc` per the one-axis law; whether the PyPI publish gate is approved is the operator's call at ship, and CLOSURE records the answer either way | `v0.4.5` was minted unpublished by operator law O5 and is the second such mint; the wording tension it recorded (`specs/memory/product/distribution/pypi-distribution.md`) is inherited, not resolved here |
| **AS-7** | **This `_ideas/` Draft carries SPEC + PLAN + TASKS**, although canon v6's commit rule reads *"`_ideas` SPEC = SPEC only"* | That rule is a **commit-shape** rule that exists once canon v6 exists (FR1) and the audit measures it (FR14). This Draft predates both, and the operator's dispatch asked for all three. From FR1 onward the rule binds |
| **AS-8** | **Every backlog entry is consumed in full** — no partial pick. `dd-release-definition` §5's full-slug granularity holds; six slugs, six full consumptions, declared at promotion | A partially-shipped entry may not be declared; the release is scoped so that no entry needs splitting |
| **AS-9** | **The 50 `archive/*` tags are part of the source of truth** for FR3. The migration runs after `git fetch --all --tags`, records its ref scope and the reachable ledger-commit count in the migration report, and this release **deletes no `archive/*` tag** | 295 of the 295 ledger commits are reachable only with the tags; a `--single-branch` clone sees 75 and would silently produce a different map. The count is therefore a **validation**, not a footnote (V6) |
| **AS-10** | **FR16's first audit is a dry run.** It produces a real `AUDIT.md` + `FINDINGS.jsonl` and an `audited` milestone, and it opens **no remediation release**: its findings are compiled for the PM's operator-facing intake report | `DADAIA.md` §6 binds one audit to one remediation release; that release is the *next* pick, not this one. Running the audit inside this release is how the canon proves itself on a real corpus before it is shipped to consumers |
| **AS-11** | **The lineage check is phase 0 of `dd-diagnose`**, in the disclosed sibling `dd-diagnose/LINEAGE.md`; `dd-bug-resolution/SKILL.md` points at `dd-diagnose` and keeps only the bug lifecycle | The `bug-lineage-and-commit-discipline` entry's intent ref names `dd-bug-resolution/LINEAGE.md`; D8 names no file. Lineage and diagnosis are **one procedure** — you read the prior fix diffs *before* you form a hypothesis — so splitting them across two skills would restate the window and the `git show` recipe twice. One home, one statement, and `dd-bug-resolution` gets smaller. Flagged in §8 |

---

## 3. Scope

**Standing rules for every segment.**

- **The D15 posture is an acceptance, not a preference.** Every FR is checked against it: no
  new blocking CLI validation, no new hook block, nothing that can stop a human at commit
  time. Procedure lives in skills and scoped `AGENTS.md`; conformance is measured by audits
  from git and JSONL history.
- **Green at every commit:** `dadaia ci preflight`, `dadaia backlog doctor`,
  `dadaia specs doctor`, `dadaia public doctor`. **No `--no-verify`, ever.**
- **RED before GREEN**, on the executed path (`DADAIA.md` §7).
- **The standing order is an acceptance.** Every task leaves the touched feature smaller or
  equal in surface. Every review verdict states, with bug-history evidence, whether the change
  reduced or increased the bug surface of the feature it touched. "Tests green" is not a
  verdict.
- **Net direction, honestly.** This release **adds** a canon: production LOC is expected
  net-positive, and §3/FR22 fixes the accounting rule — every FR declares its direction, the
  additive ones justify themselves against the standing order, and the deletion engines (FR9,
  FR12, FR15, FR21) are measured separately so the addition is never hidden inside a total.
- **Measurement rule.** `product-engineer` has no shell. Every number this release asserts is
  produced by a named task step run by an agent with a shell and captured under
  `.dadaia/tmp/<agent>/<YYYYMMDD>/`.
- **No fabricated evidence.** A derived value carries its provenance marker (D-A). An
  inferred value is marked inferred. A value nobody assessed is `null`, never a default.
- **Test intent at birth**, per `dadaia-test-stewardship`. **Zero new `tests/e2e/**`** without
  a named `qa-engineer` exception recorded in that segment's QA artifact.
- **No home-absolute path, operator email literal, IP, hostname, private name or denylisted
  term** enters any authored file, including migration reports and audit artifacts.

---

### Segment `S1` — the canon and the historical ledger rewrite

Lands first: every other segment reads the shapes it creates. Owner: `software-engineer`
(+ `product-engineer` for authored spec text, + the operator for FR6).

#### FR1 — The v6 canon: tree, scaffold, doctor · **size L**

*Entry: `specs-canon-v6` (layout part) · rulings D5/D11/D12 (folder shapes).*

`specs_pattern_version` moves 5 → 6. The canon root becomes exactly: `backlog/`, `bugs/`,
`memory/`, `releases/`, `audits/`, `ADRs/`, `constitution.md`, `AGENTS.md` — nothing else is
conformant. Per area: `bugs/BUGS.jsonl` (rename of `bugs.jsonl`) + `bugs/AGENTS.md` +
`bugs/_archive/`; `memory/ARCHITECTURE.md`, `TECHSTACK.md`, `QUALITY.md` (renames of the
lowercase trio) + `memory/AGENTS.md` + `product/`; `releases/` with at most **one** live
`{version}/` (bare semver, no `v` prefix) plus `_ideas/{version}/` and `_archive/{version}/`;
`audits/` and `ADRs/` per FR13/FR19. `specs/assets/` retires into `memory/ARCHITECTURE.md`;
`specs/backlog/remote-bugs/` dies; every `README.md` in the scaffold retires into the area's
`AGENTS.md`. `specs doctor` gains **TREE-8 "nothing beyond canon"** and `--recipe` (ordered
concrete steps for what `specs upgrade` cannot do alone); `specs upgrade` automates the safe
renames. **Compliance is WARN-only** — the agent and the operator decide, never a block (D15).

**Bug-surface direction:** *net-additive in production LOC, net-negative in surface count* —
one canonical tree replaces "the tree plus the four legacy shapes doctor tolerated"; four
`README.md` files retire; `specs/assets/` and `remote-bugs/` disappear.
**Bug-history evidence:** the gitignore class (four recurrences, §1.1) is a *governance-path*
class — every instance was "a spec artifact that was not where the canon said it was". TREE-8
names the class instead of patching instances. `remote-bugs-gitignore-blocks-new-intake` is
one of those four and dies with the folder.

**Acceptance**
- A1.1 A freshly scaffolded workspace emits the v6 tree, `specs_pattern_version: 6`, scoped
  `AGENTS.md` per area, zero `README.md`, zero `assets/`.
- A1.2 TREE-8 reports any path under `specs/` that is not in the canon, as **WARN**; a
  fixture with a stray folder proves it, and a second fixture proves the exit code is
  unchanged (no block).
- A1.3 `specs doctor --recipe` emits ordered, concrete, copy-pasteable steps for every
  finding `specs upgrade` cannot execute; proven on this repo's own pre-migration tree.
- A1.4 `specs upgrade` performs the safe renames idempotently: running it twice is a no-op,
  proven by a byte-comparison fixture.
- A1.5 The SDD gate's MEMORY-phase resolution and FROZEN class are repointed (FR4 supplies
  the phase source; FR6 supplies the archive paths) with **no new path class** and no second
  classifier — proven by the diff on `dadaia_workspace/features/spec_context/gate_policy.py`
  being flat or net-negative.
- A1.6 This repo's own `specs/` is migrated to v6 and `dadaia specs doctor` reports **0
  errors** afterwards.

#### FR2 — `BUGS.jsonl`: one record per bug, immutable core, mutable governance · **size M**

*Entry: `bug-lineage-and-commit-discipline` (A) · rulings D2, D11.*

`bug-event-v1.schema.json` is replaced by `bug-record-v1.schema.json`
(`additionalProperties: false` kept). One record per bug, appended once — no event stream, no
fold. **Immutable core:** `id`, `ts`, `reported_by`, `title`, `severity`, `surface`,
`component`, `context`, `symptom`, `repro`, `expected`, and `root_cause` / `solution` once
set. **Mutable governance:** `status` (`open|picked|resolved|superseded|deferred|rejected`),
`cause`, `caused_by`, `lineage_source`, `registration_commit`, `registration_granularity`,
`resolved_commit`, `resolution_granularity`, `resolved_release`, `superseded_by`, `audited`.
A governance update rewrites that record's line in place — JSONL is a document keyed by `id`,
the line is the unit, git history is the change log. A **reopen is a new record** with a new
`id` declaring `caused_by: <prior-id>`. Registration requires `symptom` + `repro` +
`severity` + `expected`; reaching `status: resolved` requires `cause` + `caused_by` +
`resolved_release` + the regression seam in `solution`. Coherence is checked as **WARN**,
surfaced by `dadaia bugs status` and the doctor — **never a block** (D15).

The record as first appended — governance fields present and null, so the record's shape never
changes:

```json
{"id":"ci-preflight-quick-skips-lint-imports-048","ts":"2026-08-26T10:02:41Z","reported_by":"software-engineer","title":"ci preflight --quick skips lint-imports","severity":"MEDIUM","surface":"dadaia ci preflight","component":"cli/commands/ci.py","context":"dadaia-workspace","symptom":"--quick returns 0 while lint-imports fails in CI","repro":"1. break an import contract 2. dadaia ci preflight --quick 3. exit 0","expected":"--quick runs lint-imports (only e2e is skipped)","status":"open","cause":null,"caused_by":null,"lineage_source":null,"registration_commit":null,"registration_granularity":null,"resolved_commit":null,"resolution_granularity":null,"resolved_release":null,"audited":null}
```

The **same line** after the fix — core fields byte-identical, `root_cause`/`solution` set once,
governance fields filled:

```json
…"root_cause":"quick mode built its step list from a hard-coded tuple that never included lint-imports","solution":"single step registry consumed by both modes; regression test tests/integration/test_ci_preflight.py::test_quick_runs_lint_imports","status":"resolved","cause":"duplicated step list (two code paths)","caused_by":"frozen-clock-guard-tz-boundary-031","lineage_source":"declared","resolved_commit":"9d8e7f6","resolution_granularity":"exact","resolved_release":"0.5.0","audited":null…
```

**Bug-surface direction:** *net-negative* — the fold logic (`reported` + N events → a state
machine with terminal/non-terminal/repeatable event kinds, seven `allOf` conditional blocks
in the schema) is deleted and replaced by a flat record; `core/models/bugs.py#BugEvent`
becomes `BugRecord` with no state machine.
**Bug-history evidence:** the event stream itself produced a bug family — the U+2028 record
(`bug-event-field-with-unicode-line-separator-silently-drops-the-event`) is *silent event
loss*, only possible because a bug's truth is spread across lines that must be re-folded on
every read. One line per bug means a corrupt line loses one bug, loudly, instead of
half-folding a state machine. The `picked`/`archived` non-terminal annotations, added to work
around the append-only model, disappear as `status` values.

**Acceptance**
- A2.1 The record schema is authored and `bug-event-v1.schema.json` retires; the mutable /
  immutable split is documented **per property** in the schema, not in prose elsewhere.
- A2.2 A contract test proves an immutable core field cannot be changed on an existing record
  through the service seam, and that a governance update rewrites the line in place leaving
  every other byte of the file identical.
- A2.3 Coherence violations (resolved without `cause`/`caused_by`/`resolved_release`;
  superseded without `superseded_by`) are surfaced as **WARN** by `dadaia bugs status` and
  `specs doctor`, with **exit code unchanged** — proven by a fixture asserting the exit code.
- A2.4 `expand → switch → contract` (D-F): the record reader lands and every consumer switches
  before the event reader is deleted; each step independently green.
- A2.5 The v5 event shape is decoded by **one boundary adapter** used only by FR3's derivation
  and the migration — no v5 branch survives inside the bugs feature after the contract step.

#### FR3 — Historical ledger rewrite: 490 bugs, commits derived from git · **size L**

*Entry: `specs-canon-v6` (migration clause) + `bug-lineage-and-commit-discipline` (A) ·
rulings D2, D11 · the hard requirement of this release.*

The 490 bug ids / 1005 events of `specs/bugs/bugs.jsonl` migrate to `specs/bugs/BUGS.jsonl`
in the FR2 record model, with `registration_commit` and `resolved_commit` populated for the
**whole** history from git.

**The derivation algorithm — one pass, all refs, first-add wins.**

1. **Ref scope.** `git fetch --all --tags` first. Enumerate candidate commits with
   `git log --all --no-merges --reverse --date-order --format=%H -- specs/bugs/`. On this
   repo that is **295** commits (75 on `main`, 70 on `develop`; the rest reachable only
   through the 50 `archive/*` tags — **AS-9**). The count is asserted, not assumed (V6).
2. **Single chronological pass.** For each commit in that order, read the added lines of its
   diff restricted to `specs/bugs/**`. Parse each added line as JSON through the FR2 boundary
   adapter (which understands both the v5 event shape and the v6 record shape — A2.5).
3. **First-add wins.** For each `(bug_id)` the **first** commit adding a line whose parsed
   form is a registration (`event == "reported"`, or a v6 record with `status == "open"`
   newly present) is that bug's `registration_commit`. The **first** commit adding a line
   whose parsed form is terminal (`event ∈ {resolved, superseded, deferred, rejected}`, or a
   v6 record whose `status` is terminal) supplies `resolved_commit` and `status`. Because the
   pass is chronological and only *additions* count, a later squash or ship commit that
   re-adds the same line never wins. Ties inside one commit are impossible; ties across
   commits with identical dates break by topological order, then by sha, and the tie-break
   used is recorded in the report.
4. **Granularity marker (D-A).** Each derived sha is stored with its marker:
   - `exact` — the commit adds exactly one bug's line **and** touches at least one file
     outside `specs/`;
   - `release-squash` — the commit adds more than one bug's line (release-level squash);
   - `ledger-only` — the commit adds exactly one bug's line and touches **no** file outside
     `specs/` (the code change is elsewhere or unknown).
5. **Null only when nothing adds the line.** On the corpus measured today that is **0** cases;
   when it happens, the field is `null` and the record carries a `migration_note` naming the
   reason.
6. **Cause and lineage are never fabricated.** `cause` is copied from the v5
   `evidence_diff` / `notes` **only where that text literally states a cause**, else `null`.
   `caused_by` is populated **only** where a record's own text names another existing bug id
   (92 such cross-references exist) — every such link is stored with
   `lineage_source: "text-reference"` so audits know it is inferred. Everything else is
   `caused_by: null` (**AS-2**), `lineage_source: null`.
7. **Legacy archive.** `specs/bugs/_archive/archive.jsonl` (114 `{file, content}` records)
   stays **byte-frozen** and is not converted (**AS-3**); the new
   `specs/bugs/_archive/bugs_histo.jsonl` is created empty and receives future archived
   records via `dadaia bugs archive`.

**The migration report** (`.dadaia/tmp/software-engineer/<YYYYMMDD>/bugs-migration-report.md`
+ its JSON sibling) records: ref scope and reachable ledger-commit count; records migrated;
registration commits found / by granularity / distinct-commit count; resolution commits found
/ by granularity / distinct-commit count; `cause` populated vs null; `caused_by` populated by
`text-reference` vs null; every `migration_note`.

**Bug-surface direction:** *net-additive* (a migration module and its report), **explicitly
justified**: it is a one-shot conversion whose output is data, not a permanent branch. The
migration module is *deletable* after the release — FR3 states the deletion criterion (once
`BUGS.jsonl` is canon in every consumer, the v5 adapter and migration retire with a follow-up
entry). Nothing in the running bugs feature grows.
**Bug-history evidence:** `specs-bugs-jsonl-store-gitignored` (the ledger itself was once
untracked) is why the derivation must run over **all refs including tags** rather than trust
`main`; the 155 release-squash resolutions and the 39/117 ledger-only resolution commits
(§1.2) are why the granularity marker exists at all.

**Acceptance**
- A3.1 **490/490** records migrate; the record count in `BUGS.jsonl` equals the distinct
  `bug_id` count of the v5 ledger, proven by the report.
- A3.2 `registration_commit` is non-null for **≥ 490** records; the report reproduces the
  measured distribution — **≥ 124** distinct commits, **≥ 79** marked `exact`.
- A3.3 `resolved_commit` is non-null for **≥ 470** resolved records; the report reproduces
  **≥ 117** distinct commits, **≥ 70** single-bug commits, **≥ 155** marked `release-squash`,
  and **≤ 39** marked `ledger-only`.
- A3.4 **Idempotence:** running the migration twice produces a byte-identical `BUGS.jsonl`
  and a report whose counts are identical — proven by an executed fixture, not by reasoning.
- A3.5 Every `caused_by` populated from prose carries `lineage_source: "text-reference"`;
  **zero** records carry `caused_by: "none"` (AS-2); zero records carry a `cause` string that
  is not literally present in the source record's text — proven by a scan comparing each
  populated `cause` against its source event.
- A3.6 `specs/bugs/_archive/archive.jsonl` is **byte-identical** before and after the release
  (`git diff --stat` empty for that path), and no audit window includes it.
- A3.7 The full migrated ledger parses, and `dadaia bugs status` renders all 490 records with
  no crash and no silent drop — the drop being the exact failure mode of
  `bug-event-field-with-unicode-line-separator-silently-drops-the-event`.
- A3.8 The migration is a **separate commit** from the FR2 schema change, and the report is
  referenced from it.

#### FR4 — `RELEASE.jsonl`: milestone shas replace `ACTIVE.md` and `CLOSURE.md` · **size L**

*Entry: `specs-canon-v6` (releases part) · rulings D3, D7, D11.*

Each release directory gains `RELEASE.jsonl` (`release-event-v1`:
`{ts, event, agent, session_id, data}`) with kinds `created`, `spec_status`
(Draft/Em revisão/Aprovado), `phase` (DEFINITION/IMPLEMENTATION/CLOSURE — the SDD gate folds
the **last** `phase` for the MEMORY path class), `rc_open`/`rc_close`, `review`, `push`/`pr`,
`ship`, `archive`, `note`, `audited`. Individual commits stay out; **milestone records carry
`sha` (+ `pr`) as immutable facts** at exactly three points, plus `audited` whenever an audit
runs:

```json
{"ts":"2026-08-28T14:02:11Z","event":"defined","agent":"product-engineer","session_id":"s-9f1c","data":{"sha":"4e5f6a7","pr":210}}
{"ts":"2026-09-03T18:40:05Z","event":"implemented","agent":"qa-engineer","session_id":"s-77ab","data":{"sha":"b8c9d0e","rc":2}}
{"ts":"2026-09-04T10:15:00Z","event":"shipped","agent":"project-manager","session_id":"s-77ab","data":{"sha":"f1a2b3c","pr":214,"tag":"0.5.0"}}
{"ts":"2026-10-20T09:00:00Z","event":"audited","agent":"project-auditor","session_id":"s-3d4e","data":{"sha":"c0ffee1","audit":"audits/20261020-five-release-window"}}
```

`ACTIVE.md` and `CLOSURE.md` **retire**: the active release and phase are the fold of the
newest `RELEASE.jsonl`; the closure narrative moves into the final `rc`'s records plus the
release's own `SPEC.md` provenance. Back-fill: `specs/releases/_archive/releases_histo.jsonl`
(**D-G**) receives one milestone block per already-archived release, `sha` and `pr` taken from
that release's `CLOSURE.md` tables where they are given, `null` where they are not — read
**before** FR6 deletes the archive.

**Bug-surface direction:** *net-negative in surface, net-additive in LOC* — two hand-authored
Markdown files with parsers (`ACTIVE.md`'s two-line schema; `CLOSURE.md`'s section-and-table
regexes in `doctor_closure_audit.py`) collapse into one machine record read by one fold.
Every regex that parses release prose is deleted.
**Bug-history evidence:** the release-state surface has produced repeated bugs of the
"artifact says one thing, tree says another" shape — the v0.4.4 verdict gate resolving by
artifact across two trees (`ACTIVE=none` broke it), and the gate's phase lookup depending on
a file an agent hand-edits. A folded event stream has one writer and one reader.

**Acceptance**
- A4.1 `RELEASE.jsonl` exists for the live release; the SDD gate resolves the MEMORY phase by
  folding it, with `ACTIVE.md` gone and **no fallback branch** left behind (proven by the
  gate diff and a fixture with no `ACTIVE.md` present).
- A4.2 The three sha-bearing milestones are appended at their defined moments during **this
  release's own** lifecycle, and are immutable — a contract test refuses a rewrite.
- A4.3 `releases_histo.jsonl` carries one block per archived release; every sha it claims is
  resolvable by `git cat-file -e <sha>`, and every unavailable value is `null`, never a
  guess. The count of releases back-filled and the found/null split are recorded (V7).
- A4.4 `CLOSURE.md`'s validators (`doctor_closure_audit.py`) stop parsing prose — see FR15.
- A4.5 `expand → switch → contract`: `RELEASE.jsonl` is written and read in parallel with
  `ACTIVE.md` for at least one commit, then `ACTIVE.md` is deleted; each step green.
- A4.6 The audit window is computable: `audited` milestones across live, `_ideas/` and
  `_archive/` are scannable in one pass, and the newest one yields `[sha, HEAD]` (consumed by
  FR14).

#### FR5 — `BACKLOG.md` becomes a live photo; exits move to `backlog_histo.jsonl` · **size M**

*Entry: `specs-canon-v6` (backlog part).*

`specs/backlog/BACKLOG.md` keeps **only** the `## ACTIVE` entries. The in-file `## LEDGER`
section retires; every exit appends
`{ts, slug, disposition, reason, release?, by, entry_md}` — the full entry snapshot — to
`specs/backlog/_archive/backlog_histo.jsonl`. The disposition vocabulary is unchanged. Legacy
`specs/backlog/_archive/*.md` stay frozen, no retro-conversion.

**Bug-surface direction:** *net-negative* — the dual-section document (ACTIVE + LEDGER) whose
invariants `backlog doctor` polices (BL-DUP, BL-STALE) becomes a single-section document plus
an append-only file; the duplicate-ledger-line class (BL-DUP) becomes structurally impossible.
**Bug-history evidence:** `backlog-candidates-md-tracked-violates-noncanonical-gitignore` and
`backlog-gitignored-governance-vacuous` are two of the four gitignore-class recurrences and
both are about *where backlog state lives*; the BL-DUP rule exists because closure sweeps
appended a second LEDGER line instead of updating the first.

**Acceptance**
- A5.1 Every existing `## LEDGER` line migrates into `backlog_histo.jsonl` with its full
  entry snapshot where the entry text is recoverable, and with an explicit
  `entry_md: null` + note where it is not; the counts are reported.
- A5.2 `BACKLOG.md` after the migration contains `## ACTIVE` only; `backlog doctor` is green
  and its BL-DUP rule is **deleted**, not disabled — proven by the diff.
- A5.3 An entry exit (any disposition) appends exactly one histo record and removes exactly
  one `## ACTIVE` subsection, proven by an executed fixture.
- A5.4 Legacy `_archive/*.md` are byte-identical before and after.

#### FR6 — [operator] Root `specs/_archive/` is tagged, then deleted · **size S**

*Entry: `specs-canon-v6` (destructive step) · operator ruling **D1 of 2026-08-23**: "git
history is the archive"; executed **only with the operator present** (D-H).*

**Acceptance**
- A6.1 An `archive/specs-archive-<YYYYMMDD>` tag is created **and pushed** at the commit
  immediately preceding the deletion; the tag is verified reachable before anything is
  removed.
- A6.2 FR3 (A3.x) and FR4 (A4.3) are complete and their outputs committed **before** the
  deletion — nothing that the back-fills need is read after this point.
- A6.3 The deletion is one commit, executed with the operator present, and the FROZEN gate
  class is repointed to the per-area `*/_archive/` paths in the **same** commit — never a
  window where FROZEN points at nothing.
- A6.4 After the deletion, `git show <tag>:specs/_archive/releases/v0.4.4/CLOSURE.md`
  succeeds — the archive is reachable, and this is demonstrated and captured, not asserted.
- A6.5 No `archive/*` tag is deleted by this release (AS-9).

---

### Segment `S2` — lineage, commit discipline, hooks, and the validated map

Owner: `ai-engineer` (skills, personas, `DADAIA.md`, `AGENTS.md`) + `software-engineer`
(contract tests, hook scripts, CLI).

#### FR7 — `dd-diagnose`, with the lineage check as phase 0 · **size M**

*Entries: `dd-diagnose` + `bug-lineage-and-commit-discipline` (B) · ruling D8 · **AS-11**.*

A new model-invoked core skill `dd-diagnose`, called by `dd-bug-resolution`, carrying the
diagnosing method as ordered phases each ending on a checkable *Done when*:

- **Phase 0 — lineage (D8).** Filter `BUGS.jsonl` for records with the same `component` or
  `surface` inside the audit window (since the newest `audited` milestone in any
  `RELEASE.jsonl`, or the whole file when none). Read each prior record's resolution diff —
  `git show <resolved_commit>` when `resolution_granularity == "exact"`, and, when it is
  `release-squash` or `ledger-only`, say so instead of pretending the diff is the fix. Declare
  `caused_by: <bug-id>` or `caused_by: none`, with evidence, in the record and echoed in the
  fix commit body:

```text
caused_by: frozen-clock-guard-tz-boundary-031
evidence: git show 4c1d2e3 added _quick_steps tuple in ci.py (+18) separate from STEPS; this bug is that second path drifting.
prior diffs read: frozen-clock-guard-tz-boundary-031 (4c1d2e3), ci-preflight-runner-fail-closed-029 (7a7b7c7)
```

- **Phase 1** reproduction loop, actually run **red** before any hypothesis is written;
  **Phase 2** minimise the failing input/path; **Phase 3** falsifiable hypotheses, one at a
  time; **Phase 4** instrument rather than guess; **Phase 5** a regression test at the
  **correct seam** — the boundary the bug actually crossed, not the nearest convenient unit
  (a *seam* is a place where a test or a replacement can be inserted without editing the
  module under test); **Phase 6** remove the instrumentation.

**The no-correct-seam clause:** when no correct seam exists, the fix does **not** proceed —
the agent registers an architecture finding and the dispatcher routes `software-architect`
first. **The caused_by clause:** a `caused_by` that points at a prior fix is the trigger of
the standing architecture-review order — the fixer shows the structural cause and a diff that
does not grow the feature; a net-positive diff routes to `software-architect` before the
commit (`DADAIA.md` §7, unchanged).

Home: `dd-diagnose/SKILL.md` (short) + disclosed sibling `dd-diagnose/LINEAGE.md` (phase 0 in
full) + `specs/bugs/AGENTS.md` (the scoped summary) + the short `DADAIA.md` section FR11 lands.
`dd-bug-resolution/SKILL.md` points at it and keeps only the bug lifecycle.

**Bug-surface direction:** *net-additive in AI-surface lines, net-negative in duplicated
procedure* — `dd-bug-fix` §3–§5 today restates outcomes without procedure; that text is
**moved**, not copied, and `dd-bug-resolution` gets shorter. A coverage table (every removed
block → its surviving home) is mandatory.
**Bug-history evidence:** the certify probe re-bugged 37 minutes after its fix (no red loop
before the hypothesis — phases 1–3); the frozen-clock → guard → guard's-bug chain (no lineage
read, and the fix grew the feature by 294 LOC — phase 0 plus the `caused_by` clause); 132/471
resolutions with no evidence at all.

**Acceptance**
- A7.1 The skill exists with the seven phases, each carrying a *Done when* that a reviewer can
  check without reading the code.
- A7.2 Phase 0's window computation is stated once and matches FR14's pillar-1 window exactly
  — the same definition, cited, not restated (proven by a citation check).
- A7.3 Phase 0 explicitly instructs the reader to distrust a `release-squash` /
  `ledger-only` sha rather than diff it as if it were a fix (D-A).
- A7.4 A coverage table records every block moved out of `dd-bug-resolution`, with its
  surviving home; no law is dropped silently; the fleet's AI-surface net for FR7+FR12
  together is reported.
- A7.5 **No CLI verb and no hook** is added for the lineage check (D8/D15) — proven by the
  diff touching no file under `dadaia_workspace/cli/` or `dadaia_workspace/hooks/`.

#### FR8 — Commit shapes, and the `resolved_commit` fill · **size M**

*Entry: `bug-lineage-and-commit-discipline` (C) · rulings D2, D4, D10 · **AS-1**.*

Rules, stated in `dd-gitflow-default` §3 + `dd-bug-registration` + `dd-backlog-definition` +
the scoped `AGENTS.md` files, **measured by the audit via `git log`, never by a hook**:

1. Bug registration is an **isolated commit** staging only `specs/bugs/BUGS.jsonl` —
   `chore(bugs): report <id>` — so `registration_commit` is derivable and `exact`.
2. A backlog entry is an isolated commit `chore(backlog): add <slug>` staging only
   `specs/backlog/BACKLOG.md`; an ADR is an isolated `docs(adr): propose NNNN-<slug>`.
3. **The fix is contained in the commit that resolves:**
   `fix(<scope>): <what> (resolves <id>)` stages the code, the regression test and the
   `BUGS.jsonl` line carrying `status: resolved`, `cause`, `caused_by`, `resolved_release`.
   Then, because a commit cannot contain its own sha, the same session appends
   `chore(bugs): <id> resolved @<sha>` staging only that line (**AS-1**).
4. **No push on bug resolve** (D4) — commit only; a push happens when the operator asks, and
   then the agent runs `dadaia ci preflight` first because it is an always-on rule (FR9/FR11),
   not because a hook forces it.
5. Release definition is **one bundled commit** (SPEC + PLAN + TASKS + purge-on-pick +
   `status: picked` on the picked bug records); an `_ideas/` SPEC commit carries the SPEC only.

**One resolver seam.** `resolved_commit` has exactly one reader: a function that returns the
stored value when present and derives it (FR3's algorithm, scoped to one id) otherwise. Git is
the authority; the field is a cache; pillar 1 reports a disagreement as a finding.

**Bug-surface direction:** *net-negative in code, net-additive in documented rule* — nothing
is added to the CLI or the hooks; one resolver function replaces the ad-hoc
`git log --grep <slug>` recipes scattered through skills.
**Bug-history evidence:** §1.2 — 155 resolutions inside release squashes and 39 ledger-only
resolution commits mean the history cannot be diffed. These five shapes are the minimum that
makes the *next* 490 bugs diffable.

**Acceptance**
- A8.1 Every shape above appears exactly once across the AI surface, with the other homes
  pointing at it — proven by a duplicate-statement scan whose zero-hit result is recorded.
- A8.2 The resolver seam is one function with one caller-facing signature; a contract test
  proves stored-equals-derived on a sample of ≥ 20 historical records and on this release's
  own bugs.
- A8.3 **Zero** new blocking validation: `dadaia bugs append`/`resolve` exit codes are
  unchanged for every input that succeeds today, proven by the existing CLI-output-stability
  fixtures staying green untouched.
- A8.4 This release's own commits obey the shapes; FR16's pillar-2 dry run reads them and
  reports conformance (a self-check the release must pass on its own history).

#### FR9 — Hooks de-slopped to the publication boundary · **size M**

*Entry: `bug-lineage-and-commit-discipline` (D) · ruling D9 · the clearest deletion in the
release.*

- `pre-commit-presence-gate.sh` becomes **advisory-only** (presence WARN, always exit 0). The
  `backlog doctor` BLOCK and the fail-closed runner are deleted;
  `cli/commands/ci.py#pre_commit_check` drops `_run_backlog_doctor_gate` and
  `_staged_backlog_paths` (the CI `backlog-doctor` job already covers the sweep, unscoped).
- `pre-push-ci-gate.sh` keeps **only** the publication boundary: branch-name policy +
  range-scoped denylist scan. The `dadaia ci preflight --quick` invocation **leaves the hook**
  and becomes the always-on rule *"run `dadaia ci preflight` before you push"* in
  `DADAIA.md` §7 + `dd-gitflow-default` + `dd-release-implement`; the audit measures pushes
  whose CI went red for preflight-class failures.
- The security-verdict CI gate on PRs is **untouched** — it *is* the publication boundary.

**Bug-surface direction:** **net-negative, unambiguously** — two blocking mechanisms and one
fail-closed runner are deleted; nothing replaces them in code.
**Bug-history evidence:** `precommit-backlog-doctor-blocks-unrelated-commits` is registered in
the ledger; the block stopped human commits on a shared tree and pushed agents into
`--no-verify` and other worse workarounds — a gate that *causes* the behaviour it exists to
prevent. It is also redundant: CI already runs `backlog doctor`.

**Acceptance**
- A9.1 A contract test asserts `pre-commit` exits **0 on any staged set**, including a staged
  set that `backlog doctor` would reject — the executed path, not the script's text.
- A9.2 `pre-push` refuses exactly two things and nothing else — an invalid branch name and a
  denylist hit — proven by fixtures for both, plus a fixture proving a *failing preflight no
  longer blocks the push*.
- A9.3 `_run_backlog_doctor_gate` and `_staged_backlog_paths` are **deleted** (grep zero-hit
  recorded), not left dead.
- A9.4 The preflight rule exists in `DADAIA.md` §7 (landed by FR11) and in
  `dd-gitflow-default`; the CI job that would catch its absence is named in both.
- A9.5 Net LOC for this FR is **negative**, measured (V10).

#### FR10 — `behavior-map.json`: every skill and every scoped `AGENTS.md` maps to one `DADAIA.md` section · **size L**

*Entry: `entity-behavior-map` (amended) · ruling D14.*

`dadaia_workspace/public/entities/behavior-map.json` is the **superset** of
`rules-skills-map.json`, adding the scoped-`AGENTS.md` column and a completeness requirement.
One row per **core skill** under `dadaia_workspace/public/skills/` and per **scoped
`AGENTS.md`** — the scaffolded ones (`specs/AGENTS.md`, `backlog/`, `bugs/`, `releases/`,
`memory/`, `audits/`, `ADRs/`) and the library's own (`.dadaia/reports/AGENTS.md`,
`.dadaia/handoff/AGENTS.md`, `tests/AGENTS.md`, the `repos/<slug>/AGENTS.md` template) — each
mapped to **exactly one** `DADAIA.md` section, with a recorded hash tuple:

```json
{"section":"§7 Quality — Register every bug you hit","skill":"dd-bug-registration","scoped_agents_md":["specs/bugs/AGENTS.md"],"hash_tuple":{"section":"sha256:…","skill":"sha256:…","scoped":["sha256:…"]},"recorded_by":"ai-engineer","recorded_at":"2026-09-01"}
```

The five original rows stay; the Audits deferral is lifted (**Audits → `dd-audit-project` →
`audits/AGENTS.md` → `DADAIA.md` §6 Audits**; **ADRs → no core skill, procedure in
`ADRs/AGENTS.md` → `DADAIA.md` §6 Memory**), and every remaining skill gets its row.

`tests/contract/test_behavior_map.py` extends `tests/contract/test_rules_skills_map.py`'s
enforcer and goes **RED** when: a skill on disk has no row; a scoped `AGENTS.md` on disk has
no row; a `DADAIA.md` section has no owner row; a row names a member that does not exist; a
member changed without its hash tuple being re-recorded. Mutation fixtures prove **each**
direction.

**Bug-surface direction:** *net-additive in tests, net-negative in unmapped surface* — the
existing enforcer is **extended**, not duplicated: one map file, one enforcer module. A second
map would be the puxadinho; `rules-skills-map.json` therefore retires into
`behavior-map.json` rather than living beside it.
**Bug-history evidence:** the AI surface's recurring class is the **stale citation** —
`dadaia-task-manager-stale-workspace-protocol-citation` (cites §1 for content at §3) and the
v0.4.5 FR14 `ai-engineer.md` citation (cites §5 for content at §8), both found by humans, both
inside `public/**`. A hash tuple that goes RED when either end moves is the structural answer
to a class that has now fired twice.

**Acceptance**
- A10.1 Every skill on disk and every scoped `AGENTS.md` on disk has exactly one row; every
  `DADAIA.md` section has exactly one owner row; the enforcer proves both directions.
- A10.2 Five mutation fixtures, one per RED condition, each proven to fail before and pass
  after the corresponding correction.
- A10.3 `rules-skills-map.json` retires; **one** map file exists at the end, proven by a
  zero-hit grep for the old filename outside `_archive`/history.
- A10.4 Re-recording a hash tuple is a deliberate act with a named reviewer — the test message
  says what to re-read, not just that a hash changed.
- A10.5 The map adds **no** runtime dependency: no CLI verb reads it, no hook loads it (D15) —
  it is consumed by the test suite and by agents.

#### FR11 — `DADAIA.md`: anchors, the D15 posture, and the three short sections · **size M**

*Entry: `entity-behavior-map` (single owner of the `DADAIA.md` write, BL-CONFLICT adjudication
2026-08-26) · ruling D15.*

`dadaia_workspace/public/data/DADAIA.md` (source only — the projected law is PROTECTED) gains
stable per-behavior anchors (named subsections for Backlog / Bugs / Releases / Memory /
Audits / ADRs) for the map to point at, plus:

- **the enforcement-posture section (D15), verbatim in intent:** *"Skills instruct procedure.
  Audits measure conformance from git and JSONL history. Hooks and the CLI validate only at
  the publication boundary (push / PR) and never block a human."*
- **the short bug-lineage + commit-shape section** specified by FR7/FR8;
- **the short audits section** specified by FR13/FR14;
- **the short memory two-tier + ADR section** specified by FR17/FR19 (*"memory Part 1 is
  ADR-gated and measured; only the operator accepts an ADR"*);
- **the always-on preflight rule** from FR9.

**Bug-surface direction:** *net-additive in always-on tokens* — and therefore governed by a
hard rule: **every section added here is a pointer, never a restatement**, and the FR reports
the token delta of the always-on set (V12). The v0.4.5 token-economy program measured the
budget; this release must not silently spend its gains.
**Bug-history evidence:** the always-on budget missed its A21.9 target in v0.4.4 (~8.2k vs
≤3.5k) and was still being cut in v0.4.5 FR11. A governance release is exactly the kind that
grows the law file; naming the risk and measuring it is the mitigation.

**Acceptance**
- A11.1 One file writes `DADAIA.md` in this release: FR11. No other FR's write set contains it
  (D-B), proven by inspection of §3 and by the TASKS write sets.
- A11.2 Each new section is ≤ the size the map row needs to point at it, and states no
  procedure that a skill already states — proven by the FR8/A8.1 duplicate scan.
- A11.3 The always-on token count is measured before and after (V12); an increase is reported
  with its per-section attribution, never averaged away.
- A11.4 `dadaia public stage && dadaia public install --target all && dadaia public doctor`
  is green and the projected law is byte-identical to source.

#### FR12 — The skill surface rides the canon · **size L**

*Entry: `entity-behavior-map` (skill-surface part) · relates to FR7 (which owns
`dd-diagnose/**`).*

- `dd-bug-fix` → **`dd-bug-resolution`**, all references updated; content aligned to the
  record model; the reproduce/RED/root-cause steps become an operative pointer to
  `dd-diagnose`; the skill keeps only the bug lifecycle (branch, record update, commit, no
  push).
- `dd-release-implement` rebuilt in the short-SKILL-plus-disclosed-siblings shape:
  `RC-FLOW.md` (the state ladder, absorbing `CLOSURE-CHECKS.md`), `RELEASE-EVENTS.md` (the
  `RELEASE.jsonl` append recipes per milestone, including the sha-bearing ones),
  `MEMORY-UPDATE.md`. `CLOSURE-TEMPLATE.md` dies with `CLOSURE.md`.
- `dd-backlog-definition` rewritten for the live-photo `BACKLOG.md` + histo JSONL; its "no
  JSONL for backlog" clause retires.
- `dd-bug-registration` and `dd-release-definition` updated to the v6 record fields and the
  `RELEASE.jsonl` flow.
- The scoped `AGENTS.md` files (`specs/`, `backlog/`, `bugs/`, `releases/`, `memory/`,
  `audits/`, `ADRs/`) are authored short and direct, hash-projected under the TREE-5 regime.

**Bug-surface direction:** **net-negative in AI-surface lines**, measured (V11) — two files
die (`CLOSURE-TEMPLATE.md`, `CLOSURE-CHECKS.md` folded), one skill is renamed rather than
duplicated, and procedure moves out of prose into pointers.
**Bug-history evidence:** the stale-citation class again (A10's evidence) — every one of these
renames breaks references, which is exactly what FR10's enforcer now catches; and
`dadaia-task-manager-stale-workspace-protocol-citation` is the registered proof that a rename
without an enforcer produces a bug.

**Acceptance**
- A12.1 `dd-bug-fix` no longer exists; zero references to the old name survive outside history
  and `_archive` — zero-hit grep recorded.
- A12.2 `CLOSURE-TEMPLATE.md` and `CLOSURE-CHECKS.md` are deleted and everything they carried
  has a named surviving home in a coverage table.
- A12.3 Every rewritten skill's steps end on a checkable *Done when*.
- A12.4 `dadaia public doctor` green; every projection byte-identical to source; FR10's
  enforcer green with re-recorded hash tuples and a named reviewer per tuple.
- A12.5 AI-surface LOC net for `S2` is **negative** (FR7's addition included), measured.

---

### Segment `S3` — the audit canon

Owner: `software-engineer` (doctor, schema) + `ai-engineer` (skill, persona) +
`project-auditor` (the dry run).

#### FR13 — Audits become committed spec artifacts · **size M**

*Entry: `audit-canon-v1` (A) · rulings D5, D11.*

`specs/audits/<YYYYMMDD>-<slug>/` holds `AUDIT.md` (scope; the window `[from-sha, to-sha]`
and the releases inside it; method per pillar; the score; the operator-facing summary) and
`FINDINGS.jsonl` (one record per finding, appended once). `specs/audits/AGENTS.md` replaces
`README.md` (scoped law + the index of audits). `project-auditor`'s write allowlist gains
`specs/audits/**` — it stays forbidden everywhere else under `specs/`, and it still never
fixes. The HTML report/handoff remains the operator-facing emission (`DADAIA.md` §5) but is
**derived from**, never a substitute for, the committed folder.

Immutable finding fields: `id` (`<audit-slug>-F<nnn>`), `pillar` (`bugs|specs|memory`),
`severity`, `refs` (file:line, bug ids, commit shas, release ids), `claim` (one sentence),
`evidence` (the command + the observed output, redacted). Mutable governance:
`disposition` (`open|fixed|superseded|deferred|rejected`), `release`, `reason`. As appended,
then the same line after the remediation release:

```json
{"id":"20261020-five-release-window-F003","pillar":"bugs","severity":"HIGH","refs":["ci-preflight-quick-skips-lint-imports-048","frozen-clock-guard-tz-boundary-031","4c1d2e3","9d8e7f6"],"claim":"fix-induced bug: 048 rides the second step list that the 031 fix introduced; 031 resolved without a structural cause","evidence":"git show 4c1d2e3 -- dadaia_workspace/cli/commands/ci.py (+18 _quick_steps); BUGS.jsonl 031 cause=null","disposition":"open","release":null,"reason":null}
{"id":"20261020-five-release-window-F003", "…same immutable fields…":"…","disposition":"fixed","release":"0.5.0","reason":"single step registry (T-050-04)"}
```

**Bug-surface direction:** *net-additive* (a schema and a folder), justified: it replaces an
HTML artifact outside `specs/` that no tool could read with a committed record that three
tools read. `README.md` retires.
**Bug-history evidence:** the audit lane's own failure history — `specs/audits/README.md`
documents a convention no tool honours, and the persona is *forbidden* to write the folder its
own README describes. A documented convention with no writer is how drift starts.

**Acceptance**
- A13.1 The finding schema exists with `additionalProperties: false` and the
  immutable/mutable split documented per property.
- A13.2 `project-auditor`'s allowlist gains `specs/audits/**` and **nothing else**; a fixture
  proves a write elsewhere under `specs/` is still refused.
- A13.3 `specs/audits/README.md` is deleted and its content lives in `audits/AGENTS.md`.
- A13.4 A finding's governance fields can be rewritten in place leaving every other byte
  identical (the FR2 mechanic, reused — **not** re-implemented; one JSONL record-update seam
  serves bugs, findings and the backlog histo, proven by the diff).

#### FR14 — `dd-audit-project`: three pillars over a sha window · **size L**

*Entry: `audit-canon-v1` (B, C, E) · rulings D6, D7, D8.*

The skill is rewritten short with per-pillar *Done when* and four disclosed siblings —
`PILLAR-BUGS.md`, `PILLAR-SPECS.md`, `PILLAR-MEMORY.md`, `FINDINGS-FORMAT.md`;
`disable-model-invocation` is lifted and the skill is listed in `project-auditor`'s skills.
All three pillars run **together**, always:

- **Pillar 1 — bug history.** Input: every `BUGS.jsonl` record whose registration or
  resolution sha falls in the window. Measures **recurrence** (same `component`/`surface`
  re-registered after a resolution — the gitignore ×4 pattern), **fix-induced bugs** (a
  resolution diff whose touched files appear in a later bug's `refs`/`component`; the record's
  `caused_by` must agree, and a `caused_by: none` contradicted by the diff is a finding),
  resolutions without `cause` or a regression seam, net-positive diffs that never routed to
  `software-architect`, and **commit-shape conformance** (FR8's five shapes, read from
  `git log --format` + `--stat`). It consumes only `commit_granularity == "exact"` shas as
  diff-able lineage and records the rest as coarse (D-A). On each record reviewed it sets
  `audited: <audit-slug>`.
- **Pillar 2 — spec compliance.** `dadaia specs doctor --json` across every release in the
  window, conformance to the v6 canon, `RELEASE.jsonl` milestone completeness (`defined` /
  `implemented` / `shipped`, each with a sha), SPEC provenance and `**Consumes:**`,
  purge-on-pick executed in the SPEC commit, and commit-shape discipline via `git log`.
- **Pillar 3 — memory/constitution drift.** Every Part-1 principle of the memory trio is
  **run through the check it names** in its `Measured by:` line and the result recorded;
  `product/` atoms vs the code they describe (the existing six-dimension method survives
  here); `constitution.md` violations; and the finding class **"Part 1 principle changed
  without an accepted ADR"** — `git log -p` on the Part-1 sections in the window, each hunk
  matched to an `accepted` ADR named in the same commit; an unmatched hunk is HIGH.

**Cadence and window.** An audit is **SUGGESTED every 5 releases and never mandatory**; the
operator triggers it (`project-manager` surfaces the suggestion at release close once ≥ 5
`shipped` milestones have accrued since the last `audited`). The window runs from the last
audited release to the current one — the auditor scans every `RELEASE.jsonl` (live, `_ideas/`,
`_archive/`, plus `releases_histo.jsonl`) for the newest `audited` milestone, takes
`[that sha, HEAD]`, and appends an `audited` milestone at the end so the chain never gaps.

**Lifecycle.** One audit → exactly one remediation release that gives **every** finding a
disposition (`DADAIA.md` §6, unchanged); the release's closure rewrites each finding's
governance fields; the folder moves to `specs/audits/_archive/` only when no record is `open`.
**No new CLI verb**: the auditor writes the folder with its file tools (D15).

**Bug-surface direction:** *net-additive in AI-surface lines, net-negative in code* — no CLI
verb, no doctor rule is added by this FR; the six-dimension HEAD comparison is **absorbed**
into pillar 3 rather than kept beside it.
**Bug-history evidence:** every chain in §1.1 is a pillar-1 detection target, and the release
is only worth shipping if the dry run (FR16) actually finds them. That is why FR16 exists.

**Acceptance**
- A14.1 The three pillars are documented with a *Done when* each; none can be run alone
  (stated as a refusal in the skill, and proven by the dry run's artifact carrying all three).
- A14.2 The window computation is stated **once** (shared with FR7/A7.2) and is executable:
  given this repo's refs, the skill's own recipe produces a concrete `[from-sha, HEAD]`.
- A14.3 Pillar 1's recurrence and fix-induced definitions are operational, not adjectival — a
  reader can compute them from `BUGS.jsonl` + `git show` with no further judgement about
  *what counts*.
- A14.4 `disable-model-invocation` is lifted and the skill appears in `project-auditor.md`'s
  skills list — the v0.4.4-class defect (a skill nobody can invoke) does not survive.
- A14.5 **Zero** CLI verbs and **zero** hook changes in this FR's diff.

#### FR15 — `specs doctor` folds `FINDINGS.jsonl` instead of parsing prose · **size S**

*Entry: `audit-canon-v1` (D).*

`doctor_closure_audit.py`'s `check_audit_disposition` / SPEC-DOC-036 / SPEC-DOC-038 stop
regexing prose: an `open` record inside an **archived** audit is an **error**; a live audit
whose records are all terminal with a named release is an **archive-due WARN**.

**Bug-surface direction:** **net-negative** — regex-over-prose is deleted and replaced by a
JSONL fold that reuses FR13's reader. Prose parsing is the largest false-positive source in
the doctor.
**Bug-history evidence:** SPEC-DOC-0xx rules that parse authored Markdown have repeatedly
produced both false positives and silent misses (the v0.1.73-era "gate never demands what the
tooling refuses" law came from this class). A structured fold cannot misread a sentence.

**Acceptance**
- A15.1 The regex path is **deleted**, not bypassed — zero-hit grep recorded.
- A15.2 Two fixtures: an archived audit with one `open` record errors; a live fully-terminal
  audit warns `archive due`.
- A15.3 `dadaia specs doctor` reports **0 errors** on this repo after the migration.

#### FR16 — The first audit, run on this repository as a dry run · **size M**

*Entry: `audit-canon-v1` (proof of the canon) · **AS-10**.*

`project-auditor` runs the new protocol end to end over this repo, producing a real
`specs/audits/<YYYYMMDD>-canon-v6-first-audit/` folder with `AUDIT.md` + `FINDINGS.jsonl` and
appending the `audited` milestone. **It opens no remediation release**: the findings are
compiled for the PM's operator-facing intake report.

**Bug-surface direction:** *neutral in code* — it produces data. Its value is that it makes the
canon fail *here* rather than at a consumer.
**Bug-history evidence:** the workspace's own law — *"a green internal gate that diverges from
real consumer behavior is itself a bug"* (`DADAIA.md` §7). A canon that has never been run is
a green internal gate.

**Acceptance**
- A16.1 The folder exists, is committed, and carries all three pillars' sections.
- A16.2 Pillar 1 **names, with evidence, at least the four documented chains of §1.1** —
  the gitignore class, the certify 37-minute re-bug, the frozen-clock 3-hop chain, and the
  bug-event ledger family. A canon that cannot rediscover the loop it was built for is not
  accepted, and FR14 is reworked instead of the acceptance being lowered.
- A16.3 Pillar 2 reads **this release's own commits** and reports FR8 conformance (A8.4).
- A16.4 Pillar 3 executes every `Measured by:` check authored by FR18 and records each
  result; any principle whose check does not run is a finding against FR18, not a skipped row.
- A16.5 Every finding is `disposition: open` with `release: null`; **no** backlog entry is
  created by any agent (`DADAIA.md` §6 — intake is operator-gated).
- A16.6 The `audited` milestone is appended to this release's `RELEASE.jsonl`.

---

### Segment `S4` — memory two-tier, principles, and the ADR canon

Owner: `product-engineer` (memory and constitution text) + `software-architect` (the
principle inventory and its measures) + the **operator** (ADR acceptance).

#### FR17 — The memory trio splits into Part 1 Principles and Part 2 Implementation · **size M**

*Entry: `memory-two-tier-principles` (A) · ruling D13.*

`ARCHITECTURE.md`, `QUALITY.md` and `TECHSTACK.md` (uppercase names from FR1) are each
explicitly divided. **Part 1 — Principles:** fundamental, ADR-gated, numbered `P-NN`, each
carrying a `Measured by:` line naming an **existing mechanical check** — *a principle without
a measure is not admitted*; a rule nobody can measure is Part-2 prose or a proposed ADR, never
a principle. **Part 2 — Implementation:** modules, diagrams, flows, dependencies, boundaries,
tunables — the living description `product-engineer` evolves at DEFINITION/CLOSURE with every
release, no ADR needed. `product/<area>/<feature>.md` atoms stay **functional descriptions**
only.

```markdown
## Part 1 — Principles

### P-04 · Features are mutually independent
Features compose through the container, never through sibling imports; a helper two
features need lives inside each feature (duplication over coupling).
Measured by: `lint-imports` contract "features must be mutually independent (compose via
container, not sibling imports)" (`setup.cfg`), run by `dadaia ci preflight` and CI.
Accepted by: ADR 0002 (2026-09-02). Amended by: —
```

**Bug-surface direction:** *net-neutral in LOC, net-negative in ambiguity* — no new file; the
existing three are restructured, and every rule that cannot name its measure is **deleted from
memory** (it was never true, only asserted).
**Bug-history evidence:** the whole loop. The standing order exists because a clean
architecture was corrupted by fixes; memory described that architecture in prose that no
check enforced, so nothing went red as it eroded.

**Acceptance**
- A17.1 Each of the three files carries exactly two top-level parts, in that order.
- A17.2 Every Part-1 entry has `P-NN`, a `Measured by:` line and an `Accepted by: ADR NNNN`
  line — enforced by pillar 3 (FR14) and by a contract test on the file shape.
- A17.3 Any prose rule that survives without a measure is moved to Part 2 or deleted, and the
  move is listed in a coverage table — no law is dropped silently.
- A17.4 `specs/memory/product/**` atoms lose any architecture principle or implementation tour
  they carried; the moved content lands in Part 1 or Part 2 by the same coverage table.
- A17.5 Memory stays a *current-state* document: no `Changelog`, `History`, `Histórico` or
  `Versions` section anywhere (`specs doctor` memory lane green).

#### FR18 — The first principle inventory: promote what is already measured · **size M**

*Entry: `memory-two-tier-principles` (B) · ruling D13 ("the first authoring is an inventory,
not new rules").*

Promote, one principle per existing mechanical check:

- one principle per `[importlinter:contract…]` section in `setup.cfg` — **the count is read
  from the file, never hard-coded** (nine at HEAD; the grill counted eight, and the inventory
  rule is "every contract");
- the module LOC ceilings and the complexity ratchet (`Measured by:` the ratchet tests /
  `ruff` configuration that hold them);
- the LARGE-test census ceiling and the test pyramid / lifecycle laws of
  `dadaia-test-stewardship` — intent + size at birth, timeouts per tier, quarantine
  bug-gated, demotion at closure (`Measured by:` the stewardship contract tests);
- the architecture-diagram drift guard (`Measured by:` its test).

Each inventory principle is admitted through its own `accepted` ADR (FR19/FR20).

**Bug-surface direction:** *net-neutral in code, strictly documentary* — **zero** new check is
written by this FR. If a rule has no existing check, it does not become a principle. This
constraint is what keeps the inventory from becoming a second enforcement layer.
**Bug-history evidence:** the frozen-clock chain shows what happens when a rule is enforced by
a guard nobody described: the guard grew, drifted and produced its own bug. Naming the check
in memory makes the guard's existence and purpose reviewable.

**Acceptance**
- A18.1 The inventory covers **every** `[importlinter:contract…]` section present in
  `setup.cfg` at implementation time, counted from the file (V13); a contract test asserts
  the counts agree, so adding a contract without a principle goes RED.
- A18.2 Every promoted principle's `Measured by:` command is executed once during `S4` and its
  output captured — a `Measured by:` that does not run is not admitted (V14).
- A18.3 **Zero** new checks, ratchets or CI jobs are created by this FR, proven by the diff.
- A18.4 Every principle is traceable to exactly one ADR, and vice versa.

#### FR19 — `specs/ADRs/`: the decision record canon · **size M**

*Entry: `memory-two-tier-principles` (C) · ruling D12.*

`specs/ADRs/AGENTS.md` (the law + an index table `NNNN · title · status · date`) and one file
per decision `NNNN-<slug>.md`, monotonic 4-digit numbering **never reused**. Fields per Nygard
(2011) + MADR 4: **Title**, **Status** (`proposed | accepted | rejected | superseded by
NNNN`), **Date**, **Context**, **Decision** ("We will …"), **Consequences** (positive and
negative), **Confirmation** (`Measured by:` — the check that proves the decision holds; an ADR
with no confirmation cannot be accepted), and links **Supersedes / Amends / Amended by**.

```markdown
# ADR 0007 — Hooks validate only at the publication boundary

Status: proposed
Date: 2026-09-10
Supersedes: — · Amends: — · Amended by: —

## Context
Pre-commit hooks grew a backlog-doctor block and a fail-closed runner that blocked human
commits (bugs precommit-backlog-doctor-blocks-unrelated-commits, …).

## Decision
We will keep hooks and CLI validation at the push/PR boundary only; procedure lives in
skills and scoped AGENTS.md; audits measure conformance from git history.

## Consequences
+ humans are never blocked at commit; − discipline drift surfaces only at audit time.

## Confirmation
Measured by: tests/contract/test_hooks_publication_boundary.py (pre-commit exits 0 on any
staged set) + audit pillar 2 commit-shape review.
```

The accepted form differs only in `Status: accepted` (+ `Accepted by: operator, <date>`).
Rules: **accepted is immutable** — a reversal is a new ADR that supersedes, and the old one's
Status flip is its only permitted edit; one decision per ADR, never a changelog; **any agent
may author `proposed`; ONLY the operator flips a Status to `accepted`** (an agent that writes
`accepted` has violated the law — a pillar-3 finding). Commit rule: an ADR proposal is an
isolated `docs(adr): propose NNNN-<slug>`; the commit that changes a Part-1 principle
**carries the accepted ADR** (`docs(adr): accept NNNN-<slug>` stages the status flip, the
Part-1 hunk and the constitution reference together — that is exactly what pillar 3 reads).
**No CLI verb, no doctor rule** beyond FR1's folder shape.

**Bug-surface direction:** *net-additive in documents, zero in code.*
**Bug-history evidence:** this workspace has reversed its own rulings repeatedly without a
record — the 2026-08-23 D5 "commits excluded" reversed by the 2026-08-26 D3; the 2026-08-23 D3
"event-sourced" replaced by D11; `hotfix/*` retired. Each reversal lived only in a handoff.
An ADR chain makes the reversal itself reviewable.

**Acceptance**
- A19.1 The folder, its `AGENTS.md` and the index exist; numbering is monotonic and a contract
  test refuses a reused number.
- A19.2 Every ADR authored by this release carries every field, including `Confirmation`.
- A19.3 A fixture proves the "accepted is immutable" rule is stated where an agent reads it
  before writing (the scoped `AGENTS.md`), and that pillar 3 detects an agent-written
  `accepted` (FR14).
- A19.4 Zero CLI verbs, zero doctor rules beyond the folder shape.

#### FR20 — [operator] The ADR acceptance sitting · **size S**

*Ruling D12: only the operator accepts.*

The inventory ADRs (FR18/FR19) are authored `proposed` by `product-engineer` /
`software-architect` and reviewed by the operator in one sitting; the operator flips each to
`accepted` (or `rejected`, with the reason). **No agent may perform this step.**

**Acceptance**
- A20.1 Every inventory ADR has a terminal operator decision — `accepted` or `rejected` with
  a reason; none is left `proposed` at ship.
- A20.2 Each acceptance is committed as `docs(adr): accept NNNN-<slug>` carrying the ADR's
  status flip **plus** the Part-1 principle hunk it admits (FR19's commit rule) — proven on
  this release's own history by FR16's pillar 2.
- A20.3 A rejected proposal's principle does **not** enter Part 1; it is recorded in the
  coverage table with its rejection reason.

#### FR21 — `constitution.md` references principles instead of restating rules · **size S**

*Entry: `memory-two-tier-principles` (A, constitution clause).*

`specs/constitution.md` (261 lines) stops restating rules and references principles by id
(`see ARCHITECTURE.md P-04`). A constitution clause with no principle behind it becomes a
`proposed` ADR or is deleted.

**Bug-surface direction:** **net-negative, measured** — the restatement is deleted, not
mirrored.
**Bug-history evidence:** the same fact stated in two documents drifts; that is the
stale-citation class (A10's evidence) applied to the constitution, which is read by every
agent on every session.

**Acceptance**
- A21.1 Every surviving constitution clause names a principle id or an ADR number.
- A21.2 A coverage table maps each removed clause to its surviving home or to its deletion
  reason; the line-count delta is measured (V15).
- A21.3 Zero rule text is duplicated between `constitution.md` and the memory trio — proven by
  the FR8/A8.1 duplicate scan extended to these files.

---

### The `rc` lane — `rc-1 … rc-N` (D-J)

#### FR22 — The invariants this release must not break · **size S**

- A22.1 `dadaia ci preflight`, `dadaia doctor`, `dadaia specs doctor` (**0 errors**),
  `dadaia backlog doctor`, `dadaia public doctor` all green.
- A22.2 Layer rules hold: `features/**` imports neither `cli`, `infrastructure` nor `hooks`;
  `core/**` stays stdlib-pure; `lint-imports` green with **no new accepted edge**.
- A22.3 **Net accounting, per FR, honestly.** Production LOC is expected net-positive for the
  release (FR1/FR3/FR4/FR10/FR13 add a canon); the report gives the per-FR direction and shows
  the deletion engines (FR9, FR12, FR15, FR21) separately. A positive net inside an FR that
  declared itself net-negative is a defect.
- A22.4 **AI-surface lines**: FR12's net is negative and `S2`'s total (FR7 + FR11 + FR12) is
  reported with its per-FR attribution; the always-on token delta (V12) is reported.
- A22.5 Complexity ceilings (`C90`, `PLR1702`) unchanged or **lowered** — never raised.
- A22.6 **The D15 posture holds mechanically:** the diff adds **zero** new blocking CLI exits
  and **zero** new hook blocks, and removes two (FR9) — proven by a contract test over the
  hook scripts and by the CLI-output-stability fixtures.
- A22.7 Every picked entry is dispositioned; residuals — including all of FR16's findings —
  are compiled into the PM's intake report, never materialized by an agent.
- A22.8 **Every `rc` holds A22.1–A22.7**, and every `rc-N ≥ 2` traces to a defect or
  adjustment **on this scope**, named with where it was found on `develop`.

---

## 4. Out of scope (non-goals)

1. **A remediation release for FR16's findings** (AS-10). One audit binds one remediation
   release; that release is the next pick.
2. **`nine-skill-study-execution`**, **`cli-help-architecture-and-session-injection`**, and the
   audit-proposed skills other than `dd-diagnose` (`dadaia-codebase-design`,
   `dd-architecture-survey`, `dd-code-review`, `dadaia-glossary`, `dadaia-router`,
   `dd-tasks-as-tracer-bullets`, `dadaia-wizard`) — all stay `## ACTIVE`. Where a picked FR
   names one of them as a relation, the pointer is authored so the later release can land it
   without editing this one's text.
3. **Retro-converting `specs/bugs/_archive/archive.jsonl`** (AS-3) or
   `specs/backlog/_archive/*.md` (FR5/A5.4).
4. **Fabricating cause or lineage for history** — `cause` and `caused_by` are populated only
   from text that literally states them (FR3/A3.5).
5. **Any new blocking CLI validation or hook block** (D15). This release only removes.
6. **A `ctx_inject` rewrite or a token-economy program.** FR11 measures its own delta; cutting
   the always-on budget further is a separate pick.
7. **Publishing `0.5.0` to PyPI** as an assumption (AS-6) — the operator decides at ship.
8. **Re-litigating a ratified ruling.** D1–D15 are given; where an entry's older wording
   conflicts, the ruling governs and §2.3's stated assumption records the residue.
9. **Any FR not listed in §3.** Nothing discovered mid-release is added without an operator
   ruling at the moment of discovery. The standing exception is a **bug**, fixed on the spot
   as Arm B on `feature/0.5.0` (`DADAIA.md` §1) — never backlog demand.

---

## 5. Memory files affected at closure

Written in the CLOSURE phase only, one authoring pass per atom. **This release restructures
memory itself (FR17–FR21), so the closure pass writes into the new Part 1 / Part 2 shape.**

| File | Change | When |
|---|---|---|
| **`specs/memory/ARCHITECTURE.md`** | **mandatory rewrite** — Part 1 with the inventoried principles (FR18), Part 2 with the record-model, `RELEASE.jsonl` and audit-artifact seams | CLOSURE (structure lands in `S4`) |
| **`specs/memory/QUALITY.md`** | **mandatory rewrite** — Part 1 test pyramid/lifecycle principles, Part 2 suites/runners/evidence paths; the contract tests FR10/FR14 add | CLOSURE |
| **`specs/memory/TECHSTACK.md`** | Part 1 toolchain laws with their `Measured by:`, Part 2 versions and runtime seams | CLOSURE |
| **`specs/memory/AGENTS.md`** | the scoped law: Part 1 changes only in the commit carrying an accepted ADR; a principle without `Measured by:` is not admitted; `product/` atoms are functional only | `S4` (FR17) |
| `specs/memory/product/sdd/sdd-bug-backlog-governance.md` | **mandatory rewrite** — the record model, lineage, commit shapes, the live-photo backlog and the histo files (FR2, FR3, FR5, FR7, FR8) | CLOSURE |
| `specs/memory/product/sdd/specs-doctor.md` | TREE-8, `--recipe`, the `FINDINGS.jsonl` fold replacing the prose regexes (FR1, FR15) | CLOSURE |
| `specs/memory/product/sdd/sdd-gate-v3.md` | the MEMORY phase resolved from `RELEASE.jsonl`; FROZEN repointed to per-area `_archive/` (FR4, FR6) | CLOSURE |
| **`specs/memory/product/sdd/<new>-audit-canon.md`** | **new atom** — audits as committed artifacts, the three pillars, the window (FR13, FR14); linked from `product/index.md` | CLOSURE |
| `specs/memory/product/agents/agentic-entities.md` | the validated behavior map and its enforcer; the skill surface after the renames (FR10, FR12) | CLOSURE |
| `specs/memory/product/platform/workspace-doctor.md` | the hook posture after the de-slop (FR9) | CLOSURE |
| `specs/memory/product/distribution/public-asset-distribution.md` | the scaffold's v6 tree and the retirement of the scaffold READMEs (FR1, FR12) | CLOSURE |
| `specs/memory/product/distribution/pypi-distribution.md` | only if the operator's publish decision changes the lineage (AS-6) — otherwise "no change", with the reason | CLOSURE |
| `specs/memory/product/index.md` + `catalog.json` | regenerated; `index.md` touched for the new audit-canon atom | CLOSURE |
| `specs/constitution.md` | references principles by id (FR21) | `S4` (FR21) |

### Closure obligations (not implementation FRs)

- **Disposition sweep.** Six backlog slugs move to their terminal `backlog_histo.jsonl`
  disposition (`DELIVERED · 0.5.0`), executed through the FR5 mechanism — never a duplicate
  line. No bug is closed by this release (AS-4).
- **`## Size accounting`** with measured values: production LOC per FR and total, AI-surface
  net, always-on token delta, constitution line delta, `DADAIA.md` line delta.
- **The migration report** (FR3) and the **back-fill report** (FR4) referenced by path and by
  their headline counts.
- **The FR16 audit** referenced by folder, with its finding count per pillar and severity.
- **The ADR ledger** — every inventory ADR with its operator decision (FR20).
- **Coverage tables** — FR7, FR12, FR17, FR21, each mapping removed block → surviving home.
- **Test dispositions** — every demotion, quarantine (with its bug id) and SCAFFOLD expiry.
- **The `rc` ledger** — every `rc` burned, what was found on `develop`, by whom, its fix.
- **Intake candidates** — FR16's findings plus any residual, compiled for the PM's
  operator-facing intake report; `product-engineer` creates no backlog entry.
- **Archive decision:** `MOVE` — into `specs/releases/_archive/0.5.0/` (the per-area archive
  this release creates), not the deleted root `_archive/`.

---

## 6. Validations

Every item is checkable by a command; each is captured by a shell-holding agent under
`.dadaia/tmp/<agent>/<YYYYMMDD>/` and cited by id in the closure record.

| id | What | Command / check | Gate |
|---|---|---|---|
| **V1** | Doctor suite clean | `dadaia specs doctor` (**0 errors**), `dadaia backlog doctor`, `dadaia public doctor`, `dadaia doctor` | every segment close |
| **V2** | Local CI preflight | `dadaia ci preflight` | every commit |
| **V3** | Canon conformance | `dadaia specs doctor --json` reports `specs_pattern_version: 6`, TREE-8 present and WARN-only | `S1` close |
| **V4** | Record migration counts | the FR3 migration report: 490/490 records; registration ≥ 490 found / ≥ 124 distinct / ≥ 79 `exact`; resolution ≥ 470 found / ≥ 117 distinct / ≥ 155 `release-squash` / ≤ 39 `ledger-only` | `S1` (A3.1–A3.3) |
| **V5** | Migration idempotence | run the migration twice; `git diff --stat specs/bugs/BUGS.jsonl` empty on the second run | `S1` (A3.4) |
| **V6** | Ref scope | `git log --all --no-merges --format=%H -- specs/bugs/ \| wc -l` ≥ **295**, with `git tag -l 'archive/*' \| wc -l` = **50** recorded beside it | before FR3 runs (AS-9) |
| **V7** | Back-fill report | `releases_histo.jsonl` line count = archived-release count; every non-null sha passes `git cat-file -e` | `S1` (A4.3) |
| **V8** | Archive reachability | `git show <archive-tag>:specs/_archive/releases/v0.4.4/CLOSURE.md \| head` succeeds after FR6 | `S1` (A6.4) |
| **V9** | Hook posture | `pre-commit` exits 0 on a staged set `backlog doctor` rejects; `pre-push` refuses only on branch name and denylist | `S2` (A9.1, A9.2) |
| **V10** | FR9 LOC delta | `git diff --stat` over the hook scripts + `cli/commands/ci.py`, **negative** | `S2` (A9.5) |
| **V11** | AI-surface net | line count over `public/{agents,skills,data,entities}/**` before and after `S2` | `S2` close |
| **V12** | Always-on token delta | the v0.4.5 measurement recipe re-run before and after FR11, with per-section attribution | `S2` (A11.3) |
| **V13** | Import-linter contract count | `grep -c '^\[importlinter:contract' setup.cfg` = the number of Part-1 principles promoted from it | `S4` (A18.1) |
| **V14** | Every `Measured by:` runs | each Part-1 principle's named command executed once, output captured | `S4` (A18.2) |
| **V15** | Constitution delta | `wc -l specs/constitution.md` before and after; coverage table complete | `S4` (A21.2) |
| **V16** | Audit dry run | the FR16 folder exists; pillar 1 names the four §1.1 chains with evidence; every finding `open`, `release: null` | `S3` (A16.2) |
| **V17** | Behavior map completeness | `pytest tests/contract/test_behavior_map.py` green; five mutation fixtures each RED before their fix | `S2` (A10.2) |
| **V18** | No new blocker | contract test: zero new non-zero exits in hooks; CLI-output-stability fixtures green untouched | scope complete (A22.6) |
| **V19** | Release invariants | `lint-imports` green, no new accepted edge; complexity ceilings unchanged or lower; production LOC per FR reported | scope complete (A22.2, A22.3, A22.5) |

---

## 7. Traceability and provenance

| Record | Provenance | Disposition in this release |
|---|---|---|
| `specs-canon-v6` | operator grill 2026-08-23 (handoff `2026-08-23-claude-code-specs-canon-grill`), **amended 2026-08-26** (D3, D11, D12) | **picked** · FR1, FR2, FR3, FR4, FR5, FR6 · `CONSUMED · 0.5.0` at promotion |
| `entity-behavior-map` | operator grill 2026-08-23, **amended 2026-08-26** (D14, D15) | **picked** · FR10, FR11, FR12 · `CONSUMED · 0.5.0` |
| `bug-lineage-and-commit-discipline` | operator ratification 2026-08-26 (D2, D4, D8, D9, D10, D11) | **picked** · FR2, FR3, FR7, FR8, FR9 · `CONSUMED · 0.5.0` |
| `audit-canon-v1` | operator ratification 2026-08-26 (D5, D6, D7 + D11, D15) | **picked** · FR13, FR14, FR15, FR16 · `CONSUMED · 0.5.0` |
| `memory-two-tier-principles` | operator ratification 2026-08-26 (D12, D13 + D15) | **picked** · FR17, FR18, FR19, FR20, FR21 · `CONSUMED · 0.5.0` |
| `dd-diagnose` | operator ratification 2026-08-23 of the skills-audit report, section D | **picked** · FR7 (lineage as phase 0, **AS-11**) · `CONSUMED · 0.5.0` |
| bug `windows-xdist-workers-crash-on-unit-fast-tier` (LOW) | project-manager, 2026-08-24 | **not picked** — **AS-4**; migrates as `status: open`, `caused_by: null` |
| The 490 historical bug records | `specs/bugs/bugs.jsonl` since 2026-06 | **migrated, never rewritten in substance** — FR3; `cause`/`caused_by` only where the text states them (A3.5) |
| The 114 legacy `{file, content}` records | `specs/bugs/_archive/archive.jsonl` | **frozen, byte-identical** — AS-3, A3.6 |
| Root `specs/_archive/**` | operator ruling 2026-08-23 D1 | **tagged, then deleted with the operator present** — FR6 |
| Audits | `specs/audits/_archive/` | **none outstanding** — FR16 opens the first audit under the new canon, dispositioned by the *next* release (AS-10) |
| Open reconciliation (`findings[2]` of the grill handoff) | grill 2026-08-26 | **decided** — **AS-1**: derive-on-read is the authority, the follow-up ledger commit is the cache |
| PM decision (`decisions_required[0]`) | grill 2026-08-26 | **executed** — hooks de-slop (D9) is folded into `bug-lineage-and-commit-discipline` → FR9 |
| **Standing order** — permanent architecture review oriented by bug history | operator, standing | this release *is* its mechanism: FR7 phase 0, FR14 pillar 1, FR16's proof |
| **Standing question** — de-personalising the git commit identity | operator, open since 2026-08-16 | **restated, not decided** — carried into closure |

**Pick tally.** Six backlog entries, all six declared at promotion. Zero bugs picked. Twelve
entries stay `## ACTIVE`.

**Purge-on-pick (`dd-backlog-definition` §2).** **Not executed by this Draft.** While this
SPEC lives in `_ideas/`, `specs/backlog/BACKLOG.md` is untouched and every entry keeps its
`## ACTIVE` subsection. At promotion, `project-manager` removes the six subsections in the
**same commit** that moves this directory to `specs/releases/0.5.0/` and appends their
`CONSUMED · 0.5.0` records (the FR5 mechanism, if FR5 has landed; the legacy `## LEDGER` line
otherwise). The `**Consumes (declared at promotion)**` header line is deliberately **not** the
machine-readable `**Consumes:**` key, so no tool acts on a Draft.

**Version lineage.** `pyproject.toml` reads whatever `v0.4.5` left at the branch cut and bumps
to `0.5.0` at the final `rc`, per the one-axis law. MINOR, not PATCH: the `specs/` pattern
moves 5 → 6, which is consumer-visible. Publication is the operator's call at ship (**AS-6**).

---

## 8. Decisions this SPEC took that the grill did not settle

Flagged for the operator; each is reversible before approval and none contradicts a ruling.

1. **AS-1** — the `resolved_commit` fill mechanism (the handoff's explicit open
   reconciliation): derive-on-read as authority **plus** a follow-up ledger-only commit as
   cache, one resolver seam.
2. **AS-11 / D-I** — the lineage check lives as **phase 0 of `dd-diagnose`**, not as
   `dd-bug-resolution/LINEAGE.md` as the entry's intent ref proposed.
3. **D-A** — the provenance-marker rule, and with it two new record fields
   (`commit_granularity` on each derived sha, `lineage_source` on `caused_by`) that no entry
   named.
4. **D-G** — `specs/releases/_archive/releases_histo.jsonl` as the home of back-filled
   milestone shas for already-archived releases.
5. **AS-2** — historical `caused_by` is `null` (unassessed), never `"none"`; the
   never-absent rule binds post-0.5.0 resolutions only.
6. **AS-3** — `specs/bugs/_archive/archive.jsonl` stays frozen rather than converted.
7. **AS-5** — the branch is `feature/0.5.0`, superseding the `feature/0.4.6` cut named in the
   live `v0.4.5` TASKS (no file of that release is edited by this Draft).
8. **D-H** — the destructive root-`_archive` deletion is preceded by a pushed
   `archive/specs-archive-<date>` tag.
9. **AS-10** — FR16 runs the first audit as a **dry run** with no remediation release, and
   **A16.2** makes rediscovering the four documented loop chains an acceptance rather than a
   hope.
10. **AS-7** — this `_ideas/` Draft carries all three artifacts although canon v6's commit
    rule will say `_ideas` = SPEC only.
11. **§3 net-LOC accounting** — this release is net-additive in production code and says so;
    the standing order is honoured per FR, not by a total.

---

## 9. Approval

Approving this SPEC ratifies, as written: **D1–D15** as carried in §2.1; the authoring
decisions **D-A … D-J**; the eleven stated assumptions **AS-1 … AS-11** (including AS-1's
answer to the handoff's open reconciliation and AS-11's placement of the lineage check); the
six-entry pick with **no bug picked**; the destructive deletion of root `specs/_archive/`
under FR6 with the operator present; and the honest net-additive accounting of §3 and A22.3.

**Status:** Draft — authored 2026-08-26, awaiting the operator's review and the reviewer trio
(`software-architect`, `security-reviewer`, `qa-engineer`, `ai-engineer`, `code-reviewer`).
