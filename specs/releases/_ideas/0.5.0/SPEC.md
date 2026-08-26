# SPEC — Release 0.5.0 — governance, lineage and audits: make the bug loop visible

**Status:** Em revisão
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
the home of the lineage check (**AS-11**). Bugs: **none picked**. Two bugs are open on this
tree at the time of writing — `windows-xdist-workers-crash-on-unit-fast-tier` (LOW) and
`bug-event-field-with-unicode-line-separator-silently-drops-the-event` (MEDIUM, component
`infrastructure/jsonl_bug_store.py`) — both governed by **AS-4**, which now covers both.
**Precondition, not scope:** the U+2028 line-splitting seam **is fixed** — `v0.4.5`
**T-045-20** is `[x]` and the bug carries `resolved` (ledger line 1006, 2026-08-26T13:41Z);
FR2/FR3 **build on that fix and do not re-specify it** (**AS-14**, **V23**).
**Review fold:** this Draft is the post-review revision. **Three** folds have run. Fold 1
folded five definition reviews (`software-architect` REWORK · `security-reviewer` REJECTED ·
`qa-engineer` REWORK · `ai-engineer` REWORK · `code-reviewer` REWORK); fold 2 folded the two
re-reviews (`software-architect` REWORK targeted · `security-reviewer` **APPROVED** with five
residuals); **fold 3 (2026-08-26, quantitative)** folds the two quantitative reviews —
`software-architect`'s full quantitative review (REWORK; ten ranked changes) and
`qa-engineer`'s test-minimization review (twelve amendments) — against three measured
baselines (`reviews/bug-history-forensic-100.md`, `reviews/architecture-metrics-baseline.md`,
`reviews/test-minimization-literature.md`). Nine reviews live in `reviews/`; every amendment
they raised carries an explicit disposition in **§9** (**§9.1 Pass 1**, **§9.2 Pass 2**,
**§9.3 Pass 3**).
**Fold-3 mandate, in the operator's terms:** *no worsening of the architecture; a number for
every claim; fewer tests while keeping the value; never again a temporary test without its
marker.* Every "IMPROVES" claim below therefore carries `baseline → projected` with the
mechanism that produces it (**§9.3**, K), the test suite gains a measured ceiling
(**A22.9**, **V25**), and the marking rules become test-suite ratchets (**V26**–**V30**).
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

Each chain below is **pinned to explicit `bugs.jsonl` ids** — this list, verbatim, is the
reference set FR16's dry run must rediscover (A16.2/V16). A chain named without one of these
ids is not evidence.

| Chain | Pinned bug ids (the reference set) | What it proves |
|---|---|---|
| **gitignore class** | **one class, nine registered instances**, three patched instance-by-instance: `backlog-candidates-md-tracked-violates-noncanonical-gitignore` · `grill-and-oq-decisions-records-gitignored-not-version-controlled` · `specs-bugs-jsonl-store-gitignored` · `backlog-gitignored-governance-vacuous` · `remote-bugs-gitignore-blocks-new-intake` · `gitignore-alpha-qa-review-untrackable` · `gitignore-code-review-artifact-untrackable` · `v0.4.4-reviews-dir-untrackable-gitignore-recurrence` · `gitignore-verdict-evidence-untrackable-fourth-recurrence` (the last self-labelled *fourth recurrence*) | a symptom patch per instance; the class was never named, so the class kept firing |
| **certify probe** | `codex-live-probe-gate-checks-presence-not-usability` → `certify-skip-detail-leaks-full-codex-output`, re-registered **37 minutes** after the first one's fix (firing 1 of the v0.4.4 FR23 evidence gate). Same surface, same session. A cheap sibling signature: `certify-cannot-install-installed-provider` was reported 18:41:56Z and resolved 18:41:57Z — a one-second registration→resolution interval, i.e. a bulk flip of an already-"fixed" bug with no red loop | a fix landed with no evidence that the failure was reproduced on the executed path |
| **frozen clock** | `no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock` (`bugs.jsonl` line 933) → its guard (**+294 LOC**) → the guard's own bug `frozen-clock-ratchet-scans-tests-tmp-scratch-dir` (line 1004) — three hops, two ids | the fix grew the feature; the growth was the next bug's cause |
| **bug-event ledger** | `bug-event-field-with-unicode-line-separator-silently-drops-the-event` (MEDIUM, **resolved on this tree** — `bugs.jsonl` line 1006, `resolved` 2026-08-26T13:41Z, as Arm B in `v0.4.5` T-045-20: the reader now splits on `"\n"` only and the write seam **strips** U+2028/U+2029/U+0085 and every C0 byte) plus the ESC/CWE-117 escaping finding on the same reader — one seam, two symptoms, closed in one fix. The finding carries no `bugs.jsonl` id: it was raised in a v0.4.4 security review, and pillar 1 must name it by that review artifact, not by a bug id | one seam produced a family; nothing in the record said so |

**132 of 470 resolutions carry zero evidence. 92 cross-bug references exist only as prose.**
No record has ever carried a structured cause, a lineage pointer, or a commit sha.
*(Measured 2026-08-26 — a dated observation, never an acceptance threshold; see the
measurement note closing §1.2.)*

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

**These numbers are not the marker's numbers, and the acceptance must not pretend they are.**
Row 5's **79** counts commits that register exactly one bug — it does **not** report how many
of those also touch a file outside `specs/`, which the `exact` marker additionally requires,
so the number of records marked `exact` is **≤ 79** and unknown until measured. Row 7's
**155** counts *bugs* whose resolving commit matches a release-squash **commit-message
pattern**, while the `release-squash` marker is purely **structural** ("the commit adds more
than one bug's line") — under the structural definition roughly **400** resolved records fall
in it (47 multi-bug commits carrying 470 − 70 = 400 bugs). Two different units, two different
criteria. Therefore: **V4 pins only quantities the implemented algorithm actually computes**
(A3.2/A3.3, re-derived from the marker definitions), and §1.2 stays what it is — the
narrative ground truth that motivated the markers, never their acceptance threshold. The
migration measures the marker distribution and **reports** it; a divergence from §1.2 is a
fact to record in the migration report, not a failure to chase.

**Measurement note — every number in §1.1 and §1.2 is dated evidence, not a target.** The
table above was measured on **2026-08-26**. The ledger is live and grows every day this
release is defined: by the time of the pass-2 review fold the same file already reads **503**
`reported` and **474** `resolved` events against the 490/470 measured that morning. A count
frozen into an acceptance therefore ages into a false RED before implementation even starts.
The rule this SPEC follows everywhere below: **acceptance is stated over "every record present
at branch cut"**, and the 2026-08-26 numbers survive only as the historical evidence that
motivated the markers (A3.1–A3.3, **V4**).

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
   blocking CLI validation and no new hook block**; it *removes* **three** things in one
   FR (FR9): the pre-commit `backlog doctor` block, the pre-commit fail-closed runner, and
   the pre-push preflight invocation — of which **two are blocks**. Every count of "what
   was removed" in this SPEC uses that split; A22.6 pins the block count at **two**.

### 1.5 The loop, end to end, on real records — what "visible" means

> **Worked example — the certify chain, using real ids from §1.1.** Read it as the story the
> canon must be able to tell. Shas are written `<sha-A>` / `<sha-B>` because the pre-canon
> history does not record them; deriving them is exactly FR3's job.
>
> 1. **Bug A's fix commit.** `codex-live-probe-gate-checks-presence-not-usability` is
>    resolved. Under FR8 shape 3 the resolving commit `<sha-A>` carries the code, the
>    regression test and the ledger line; FR3 derives `<sha-A>` for the historical record and
>    stores it as `resolved_commit` with `resolution_granularity` saying how coarse it is.
> 2. **Bug B's record declares the lineage.** Thirty-seven minutes later
>    `certify-skip-detail-leaks-full-codex-output` is registered on the same surface. Under
>    FR7 phase 0 its fixer reads every prior record on that `component`/`surface` inside the
>    window, reads `git show <sha-A>`, and writes into B's record:
>    `caused_by: "codex-live-probe-gate-checks-presence-not-usability"`,
>    `lineage_source: "declared"`, plus the evidence block (the `git show` line, the prior
>    diffs read) echoed in the fix commit body. Today B carries none of this: the link exists
>    only as prose, which is why nothing ever saw it.
> 3. **Pillar 1 turns it into a finding.** FR14's audit, over the window containing both
>    shas, matches A's resolution diff against B's `component` and B's declared `caused_by`,
>    and measures the registration→resolution interval on the chain's sibling
>    `certify-cannot-install-installed-provider` (1 second — no red loop). It appends to
>    `FINDINGS.jsonl` a record whose `refs` name **both bug ids and both shas**, whose
>    `claim` is one sentence ("fix-induced: B rides the probe path A's fix introduced; A
>    resolved with no reproduction evidence"), and whose `evidence` is the command plus its
>    redacted output. In the same atomic in-place rewrite it fills `audited: <audit-slug>` on
>    each reviewed record (FR14, one writer seam).
> 4. **Disposition closes it.** The finding is born `disposition: "open"`, `release: null`.
>    The **next** release picks it and rewrites those three governance fields in place —
>    `fixed` · `<that release id>` · the reason. `specs doctor` (FR15) folds the file: an
>    `open` record inside an archived audit is an error.
>
> **The falsifiable success statement of this release:** run the four steps above over this
> repository's own history and rediscover, with evidence, the four pinned chains of §1.1
> without a human pointing at them. That is A16.2/V16, and it is the only criterion by which
> this release succeeds or fails.

### 1.6 The three hot surfaces — what this release does to each, stated out loud

The forensic measured where the loop actually lives: **41 of the last 100 bugs** sit on three
surfaces, and **39 of those 41 re-bugged** the same surface within 14 days. "The loop made
visible" must not be read as "the loop made smaller", so each surface gets an explicit
statement here rather than an implication.

| Surface | Bugs / re-bugged | Its recurrence engines | What 0.5.0 does |
|---|---|---|---|
| **public-assets** (install · doctor · projection · law text) | 18 / 18 | four hand-kept-truth engines: (1) skill rosters and manifests in tests (`EXPECTED_SKILLS`-style tuples), (2) doctor goldens, (3) `shipped-hashes.json`, (4) two projection authorities (install vs upgrade-refresh) | **one of four engines retired — FR10A**, the roster class, whose single-source replacement FR10's glob discovery already provides. The other **three are deferred by name — AS-17 (operator-gated)**. Exposure is stated, not hidden: this release runs **ten** projection cycles and adds one skill, renames one and adds five scoped `AGENTS.md`, every one a `test-public-pipeline-stale-skill-roster` / `install-target-doctor-goldens-stale-after-v043-skill-additions` trigger. FR10A is what turns that exposure into a *deletion* rather than a tenth chance to re-fire |
| **specs-doctor** (doctor + migration/upgrade) | 13 / 12 | chain 1 of the forensic: `specs-upgrade-emits-atoms-violating-frontmatter-schema` → **four** followers in eight days. The engine is `cli/commands/specs.py#upgrade` (**CC 26**) and `#doctor` (**CC 30**) | **FR1 does not grow either function.** The `specs upgrade` rename automation of the first Draft is **cut** (`software-architect` change 3): the release ships `doctor --recipe` only, rendered by its **own** function so `#doctor`'s CC is unchanged, and the case-only renames are copy-paste steps executed by T-050-06. Measured acceptance: `#upgrade` **CC 26 → ≤ 26**, `#doctor` **CC 30 → ≤ 30** (A1.4, V19). The deferred automation is an intake candidate |
| **spec-context** (create · alive · dead · gate policy) | 10 / 9 | the classifier and its two authorities (gate by name vs by origin) | **unchanged, and said so.** FR6 moves one FROZEN prefix out and one in (A6.3); no classifier is touched, no path class is added. This release does **not** reduce this surface |

**Aggregate, honestly (`software-architect` §11).** Where this release acts — the bugs ledger,
release state, hooks, closure parsers, the skill map — the surface **reduces**, measurably
(§9.3 K's per-FR numbers). On the three surfaces above it reduces **one engine of four, none,
and none** respectively. The release makes the loop measurable across ~100 % of the ledger and
structurally smaller on ~40 % of the bug-producing surface. That is the claim; anything
stronger is not supported by the numbers.

**Terms.** Every term of art used below — *seam*, *Arm A / Arm B*, *rc-N*, *puxadinho*,
*provenance marker*, *histo*, *live photo*, *thawed tree*, *presence*, *verdict gate*,
*purge-on-pick*, *one-axis law*, *TREE-5 / TREE-8*, *FR23* — is defined once in **PLAN §0**
and used, never redefined, here.

---

## 2. Objective, and the decisions that shape it

**Objective.** Leave the workspace with: one record per bug carrying cause, lineage and
provenance-marked commit shas for **every historical bug present at branch cut** (490 at the
2026-08-26 measurement — §1.2's measurement note); releases whose milestones are sha
ranges; an audit that reads that history and names recurrences and fix-induced bugs; memory
whose fundamental rules are numbered principles each naming the check that measures it, gated
by ADRs only the operator accepts; a skill ↔ `AGENTS.md` ↔ `DADAIA.md` map that a test turns
RED the moment it is incomplete; and **exactly two fewer hook blocks than it started with**
(the count is fixed once, here, and every other statement of it cites this one — see §1.4
pillar 3 and A22.6).

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
  saying how it was obtained. **Three field names, one vocabulary, stated here and nowhere
  else:** `registration_granularity` and `resolution_granularity`
  (`exact | release-squash | ledger-only`), one per derived sha, and `lineage_source`
  (`declared | text-reference | null`) on `caused_by`. There is **no** field named
  `commit_granularity` — the two sha markers are per-sha by construction, and every other
  section of this SPEC, of PLAN §0 and of FR14's pillar-1 filter cites *these* two names.
  **Rationale:** without them an audit reads a 91-bug release squash as if it were a fix diff
  and manufactures false lineage findings — fabricated evidence is worse than no evidence.
  They are *closed enumerations on a record*, never branches in code: pillar 1 filters
  `resolution_granularity == "exact"` instead of sniffing commit messages heuristically,
  which makes the pillar **smaller**, not bigger.
- **D-B — One release, six entries, and the BL-CONFLICT adjudications collapse.** The five
  2026-08-26 entries and `dd-diagnose` carry cross-ownership adjudications ("this file's edit
  is owned by `entity-behavior-map`", "`LINEAGE.md` is owned by `bug-lineage-…`") written for
  the case where they land in *different* releases. They land in **one** release here, so the
  conflicts dissolve. The ownership rule is **sequencing, not exclusivity**, and it has two
  tiers:
  - **Tier 1 — four single-writer files, no exceptions.** Exactly one task in the release
    may contain each in its write set: `dadaia_workspace/public/data/DADAIA.md` (FR11 /
    T-050-20), `specs/constitution.md` (FR21 / T-050-32),
    `dadaia_workspace/public/entities/behavior-map.json` (FR10 / T-050-19) and
    `dadaia_workspace/public/skills/dd-bug-resolution/SKILL.md` (FR12 / T-050-21).
  - **Tier 2 — everything else is sequenced.** Several files are legitimately touched by
    more than one FR across the release (`infrastructure/jsonl_record_store.py`,
    `features/bugs/service.py`, `features/spec_context/gate_policy.py`, `hooks/sdd_gate.py`,
    `tests/**`). For those the rule is: **never concurrently, always in the task order this
    file declares, and the later task states what the earlier one left.** The earlier claim
    that "§3 assigns exactly one owning FR to every file" was false and is withdrawn; A11.1
    proves the Tier-1 property only, which is the property that is actually checkable.
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
| **AS-1** *(re-decided at review — `software-architect` change 3)* | **`resolved_commit` fill: derive-on-read is the sole authority; the field stays `null` at resolve time and is filled by the audit.** No follow-up ledger commit exists. One resolver function derives the sha from git; **pillar 1 (FR14) writes the derived value into `resolved_commit` in the *same* atomic in-place rewrite that sets `audited`** — one writer, one resolver, zero extra commits per bug | **(i) follow-up ledger commit alone** — a missed follow-up leaves a permanent hole; **(iii) derive-on-read *plus* a follow-up cache commit** (this SPEC's first answer) — two writers of one value kept equal by a contract test, i.e. a second path, and a second ledger commit per bug that pillar 2 must then learn to recognise, against D10's "the fix is contained in the commit that resolves". **Chosen: (ii), derive-on-read as authority with an audit-time cache write.** A commit cannot contain its own sha (the handoff's open reconciliation, `findings[2]`), so the field is a cache by construction; making the *audit* the only writer of that cache keeps the writer count at one. FR8 shape 3b is deleted; A8.2 becomes "audit-filled equals derived" |
| **AS-2** | **Historical `caused_by` is `null`, not `"none"`.** `null` = never assessed; `"none"` = a fixer looked at the prior diffs in the window and found no causal link. The entry's rule *"`caused_by` never absent on a resolved record"* binds records **resolved from this release onward** | Writing `"none"` on 470 historical records would assert an assessment nobody made — fabricated evidence, the exact failure mode D-A exists to prevent |
| **AS-3** | **`specs/bugs/_archive/archive.jsonl` (114 legacy `{file, content}` records) stays byte-frozen**, beside the new `bugs_histo.jsonl`; it is excluded from the record model and from every audit window | Converting free-form Markdown bodies into structured records means *inferring* `symptom`/`repro`/`cause` from prose, into a model whose whole purpose is measured truth. All 114 are terminal and predate every discipline here. Canon v6 already sets the precedent for the backlog (*"legacy `_archive/*.md` stay frozen, no retro-conversion"*); this applies it to bugs by symmetry |
| **AS-4** | **Neither open bug is picked, and both are named.** (a) `windows-xdist-workers-crash-on-unit-fast-tier` (LOW) — if `v0.4.5` closes it, nothing to do; if not, it migrates as `status: open`, `cause: null`, `caused_by: null` and stays open. (b) `bug-event-field-with-unicode-line-separator-silently-drops-the-event` (MEDIUM) — **resolved as Arm B inside `v0.4.5` (T-045-20)**, before this release opens; **AS-14** makes that a precondition, and this release neither picks nor supersedes it | `dd-release-definition` §2: a bug that is neither fixed nor subsumed is not picked. A quarantine is never a resolution. The earlier claim that the Windows bug was "the single open bug" was wrong on this tree and is corrected here and in every citation |
| **AS-5** *(a ruling, not an assumption)* | **The branch is `feature/0.5.0`**, superseding the `feature/0.4.6` cut named in `specs/releases/v0.4.5/TASKS.md` T-045-41 | The number of the next branch is the number of the next release actually picked. This canon change is consumer-visible (the `specs/` pattern moves 5 → 6), so MINOR is the honest bump. **This Draft edits no file of the live `v0.4.5` release** — the substitution happens at promotion |
| **AS-6** *(restates standing operator law)* | **Publication is not assumed.** `pyproject.toml` bumps to `0.5.0` at the final `rc` per the one-axis law; whether the PyPI publish gate is approved is the operator's call at ship, and closure records the answer either way | `v0.4.5` was minted unpublished by operator law O5 and is the second such mint; the wording tension it recorded (`specs/memory/product/distribution/pypi-distribution.md`) is inherited, not resolved here |
| **AS-7** *(an exemption granted to this Draft)* | **This `_ideas/` Draft carries SPEC + PLAN + TASKS**, although canon v6's commit rule reads *"`_ideas` SPEC = SPEC only"* | That rule is a **commit-shape** rule that exists once canon v6 exists (FR1) and the audit measures it (FR14). This Draft predates both, and the operator's dispatch asked for all three. From FR1 onward the rule binds |
| **AS-8** | **Every backlog entry is consumed in full** — no partial pick. `dd-release-definition` §5's full-slug granularity holds; six slugs, six full consumptions, declared at promotion. `specs-canon-v6`'s `dadaia bugs archive` clause is therefore **scoped into FR2 (A2.8)**, not deferred | A partially-shipped entry may not be declared; an entry clause left unimplemented would break AS-8 silently, so the clause is either in scope or the entry is not fully consumed. It is in scope |
| **AS-9** *(a measured fact, not an assumption)* | **The 50 `archive/*` tags are part of the source of truth** for FR3. The migration runs after `git fetch --all --tags`, records its ref scope and the reachable ledger-commit count in the migration report, and this release **deletes no `archive/*` tag** | Measured on this tree: **295** ledger commits in total, **75** on `main`, **50** `archive/*` tags — **220 of the 295** are reachable only through those tags. A `--single-branch` clone sees 75 and would silently produce a different map. The count is therefore a **validation**, not a footnote (V6) |
| **AS-10** | **FR16's first audit is a dry run.** It produces a real `AUDIT.md` + `FINDINGS.jsonl` and an `audited` milestone, and it opens **no remediation release**: its findings are compiled for the PM's operator-facing intake report | `DADAIA.md` §6 binds one audit to one remediation release; that release is the *next* pick, not this one. Running the audit inside this release is how the canon proves itself on a real corpus before it is shipped to consumers |
| **AS-11** | **The lineage check is phase 0 of `dd-diagnose`**, in the disclosed sibling `dd-diagnose/LINEAGE.md`; `dd-bug-resolution/SKILL.md` points at `dd-diagnose` and keeps only the bug lifecycle | The `bug-lineage-and-commit-discipline` entry's intent ref names `dd-bug-resolution/LINEAGE.md`; D8 names no file. Lineage and diagnosis are **one procedure** — you read the prior fix diffs *before* you form a hypothesis — so splitting them across two skills would restate the window and the `git show` recipe twice. One home, one statement, and `dd-bug-resolution` gets smaller. Flagged in §8 |
| **AS-12** *(new at review — `code-reviewer` 8)* | **`S4`'s memory writes run inside a declared, recorded memory window — never a phase toggled around a task.** `DADAIA.md` §3 makes `specs/memory/` writable in `DEFINITION` and `CLOSURE` only. `S4` is therefore opened by an explicit, ledger-recorded transition: one `RELEASE.jsonl` `phase: CLOSURE` record at the head of `S4` (T-050-28) and one `phase: IMPLEMENTATION` record at `S4`'s QA close (T-050-33), each with its agent and timestamp. The window is a **state of the release, visible in the ledger and readable by pillar 2** | The alternative in the first Draft — "the dispatcher sets the phase before relaying and flips it back afterwards", buried in a task precondition — is exactly the fabricated-evidence shape this release outlaws: an unrecorded ritual that makes the gate say yes. The operator must ratify this, because it is the one place the release opens a memory window outside the canonical closure. **If the operator refuses, the fallback is stated and costed:** FR17–FR21 move wholesale into the final `rc`'s closure window, at the price of the `S4` QA close and the ADR sitting (FR20) losing their own segment boundary |
| **AS-13** *(new at review — `software-architect` F4)* | **The release id stays `0.5.0`; the collision with the archived `v0.5.0` is resolved by the existing prefix canon, not by a rename.** Bare semver (`0.5.0`) is the PyPI/one-axis lineage; a `v`-prefixed id (`v0.5.0`, shipped 2026-08-12) belongs to the retired spec-lineage axis. The **46 in-code citations reading `v0.5.0 FRn` in 28 files are not renamed** — they correctly name the archived release | Renaming either axis would rewrite correct history to avoid a reader's ambiguity. Stating the disambiguation rule once (§7) costs one paragraph and makes every citation unambiguous forever; pillar 2's window recipe excludes the `v`-prefixed id from this release's history |
| **AS-14** *(new at review — `software-architect` change 1; **restated at pass 2** to the fix's real semantics)* | **The U+2028 line-splitting seam is a precondition of this release, not a requirement of it — and it is already discharged.** `infrastructure/jsonl_bug_store.py`'s `text.splitlines()` used to split on U+2028/U+2029/U+0085, so a record carrying one was read as two malformed lines and skipped. `v0.4.5` **T-045-20** fixed it at the seam, in two halves: the reader now splits on `"\n"` **only**, and the write seam **strips** those characters (plus every C0 byte, CWE-117) before a value is ever persisted. **The strip is why "byte-identical round-trip of a U+2028-carrying field" is unsatisfiable and is withdrawn** (it would go RED against the very fix it verifies): what V23 verifies is that the **stripped** record round-trips, the live ledger parses fully, `bugs status` reports `skipped: 0`, and **no historical record is rewritten** by the check. This release references the fix and verifies it **before FR3 runs**; it does not re-specify, re-implement or re-test it | A bug is Arm B and is fixed on the spot — never carried into a release (`DADAIA.md` §1). But FR2/FR3 would otherwise build a new record model and a 490-record migration **on top of a live silent-loss defect in the very reader they use**, which is the build-on-a-stale-layer shape this release exists to end. Verifying the precondition costs one validation; re-specifying the fix here would duplicate a fix that already has an owner |
| **AS-15** *(new at review — `security-reviewer` A-1; **narrowed at pass 2**)* | **Archive still precedes ship; the CI evidence contract is fixed at the gate, derived from the canon — over exactly two roots.** `dd-release-implement` and `DADAIA.md` §6 fix the finalization order as memory → CLOSURE → sweep → **archive** → ship. This release does **not** move the archive step after the ship PR. Instead FR1 owns `.github/scripts/pr-verdict-check.sh` + `ci.yml` + `core/specs_version.py` and makes the gate resolve its evidence roots **from the release-directory canon**: **the live `specs/releases/<id>/verdicts/` and the new per-area `specs/releases/_archive/<id>/verdicts/`, and nothing else**. **`specs/releases/_ideas/` is REFUSED as an evidence root** — T-050-01 `git mv`s this trio out of `_ideas/` as the release's first task, so no verdict ever lives there, and A6.3 keeps `_ideas/` deliberately **MUTATING** because a Draft is meant to be edited: a freely-writable directory must never be a trust root of a **required** check. Admitting it would widen that trust root for zero coverage. The id token `_ideas`/`_archive` and every traversal shape stay refused before interpolation, and the bare-vs-`v` prefix rule of AS-13 is carried by the canon object, not restated in bash | The reviewer offered two options; one of them contradicts a ruling and is refused on that ground alone. The other is also the structural one: `verdict-gate-cannot-resolve-evidence-after-release-archive` is now firing a **third** time (T-044-50 fixed the `ACTIVE.md`-pointer variant; an earlier fix patched the resolution shape) and every prior fix patched the glob instead of deriving it from the canon. The canon moved; a hard-coded glob broke. Deriving the roots from `core/specs_version.py` is the only shape that survives the *next* canon move |
| **AS-16** *(new at fold 3 — `software-architect` change 1; **OPERATOR-GATED**)* | **`BUGS.jsonl` has exactly one write seam on the executed path, and the operator chooses how it is exposed.** D11 gives every record a mutable-governance half; FR2/FR13/FR14 as written let **three** writers touch the file — `dadaia bugs append` (the registration, a real verb), the fixer's `status: resolved` rewrite (**no verb exists**: `cli/commands/bugs.py` registers `append`/`status`/`stats`, and `append --event resolved` dies with the event kinds) and the auditor's `audited`/`resolved_commit` rewrite (FR13 "writes with its file tools"). Two of the three would be **file-tool** writers, which makes A2.6 (redaction), A2.9 (refuse-stale) and A14.6 (one atomic rewrite) **unprovable on the executed path** — the release would add two unsealed writers to the one artifact it exists to make trustworthy. **The seam is fixed here** (FR2: `features/bugs`'s record store, atomic + refuse-stale + schema-derived redaction, governance fields only). **How it is exposed is the operator's call:** **(i)** one governance CLI verb `dadaia bugs update <id> --set <field>=<value>`, used by the fixer *and* the auditor — **recommended**; or **(ii)** a skill-invoked Python entry point (`python -m dadaia_workspace.features.bugs.update …`) with no CLI verb | **(i) is recommended, and the D8 reasoning is made explicit rather than assumed.** D8 forbids the lineage check becoming *new CLI validation*; D15 forbids *new blocking* CLI/hook surface. A **writer** is neither: it validates nothing, blocks nobody, and exits 0 on every input that succeeds today (A8.3). What D8 actually outlaws is growth **by reflex** — a verb added because a rule needed somewhere to live. This is the opposite: it **replaces three ad-hoc writers with one**, and it is leaf-neutral, which is the number that settles it. **Leaf arithmetic, exact:** 71 today **+ `bugs update` + `bugs archive` (A2.8) − `specs release open` − `specs segment open`** (both verified at `cli/commands/specs.py:26,28`; both write `ACTIVE.md` via `_write_active` and are **dead** the moment the phase is a `RELEASE.jsonl` fold — T-050-21A) = **71**. Option (ii) reaches the same one-seam property with 69 leaves, at the cost of a documented invocation an agent must not mistype and which no `--help` surface discloses; it is the honest fallback if the operator reads any new verb as growth. **Either way the seam is one**; only its door changes. If (ii) is chosen, T-050-08's write set drops `cli/commands/bugs.py` and the leaf count reads 69 |
| **AS-17** *(new at fold 3 — `software-architect` change 7; **OPERATOR-GATED**)* | **Three of public-assets' four recurrence engines are deferred, by name, with their intake target.** Retired here: the **skill-roster / manifest** class (FR10A) — FR10's glob discovery is already its single-source replacement, so retiring the hand rosters is a **deletion**, size **S**, net-negative, zero new checks. Deferred: **(1) doctor goldens** (`install-target-doctor-goldens-stale-after-v043-skill-additions`), **(2) `shipped-hashes.json`** (`upgrade-never-refreshes-uncustomised-scoped-law-projection` — where a *new* hand-kept list **was** the fix), **(3) the two projection authorities** (`retired-lib-asset-leaves-orphan-projection`, `dadaia-md-projected-twice-into-claude-code-context`). **Intake target:** one entry, `public-assets-single-source-engines`, compiled into the PM's operator-facing intake report at closure — created by nobody here (`DADAIA.md` §6) | The operator's fold-3 instruction is "(a) a bounded FR if it is ≤ S size and net-negative, else (b) a gated deferral". Measured against the tree the answer **splits**, and saying so is more useful than forcing one verdict: engine 1 of 4 qualifies for (a) and is taken as **FR10A**; engines 2–4 do not. Each of the three lives inside `infrastructure/public_assets.py` (**1 048 LOC, the largest module in the tree**, `#doctor` at **CC 40**) or in the install/upgrade pair, and each replacement is a *new derivation*, not a deletion — the exact "grow the CC-40 function on the surface that re-bugs 18/18" shape the standing order refuses mid-release. Deferring them **with their bug ids and their intake target** is the honest form; deferring them silently is what produced four of the eighteen |

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
- **The test suite does not grow (fold 3, operator mandate).** Baseline **1 859** test
  functions in 396 files (`architecture-metrics-baseline.md` §6, measured at `974a045f`;
  re-measured at T-050-03 and that re-measurement is the baseline that binds). The release's
  target is **net non-positive**: every FR declares `Tests: +N added / −M deleted (named)`,
  and **A22.9/V25** compute the total from `pytest --collect-only`. A deletion is never a
  prune-to-green: it is a `qa-engineer` verdict carrying the `file:line` map of the coverage
  that supersedes it, executed by `software-engineer` (`dadaia-test-stewardship` §E).
- **Every added test carries its marker, and the markers are ratcheted (fold 3).**
  `Intent:` + size at birth is doctrine already; what this release adds is the **measurement**
  that makes it true — one contract file, `tests/contract/test_test_suite_ratchets.py`
  (T-050-18A), pinning: private-symbol imports (**24 → 0**), `Intent:` header coverage
  (**94/396 → 396/396**, or a per-segment ratchet carrying its number), `SCAFFOLD` carrying
  `expires: <M.m.p>`, one number per parameter, and the pyramid shape reported from
  `--collect-only`. **These are test-suite ratchets, not product checks** — see the A18.3
  resolution in FR18.
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
concrete steps for everything the canon move requires). **Compliance is WARN-only** — the agent
and the operator decide, never a block (D15).

**`specs upgrade` is not grown by this release (fold 3, `software-architect` change 3).** The
first Draft had it "automate the safe renames". It is the engine of the forensic's **chain 1**
— `specs-upgrade-emits-atoms-violating-frontmatter-schema` bred **four followers in eight
days** — and `cli/commands/specs.py#upgrade` already sits at **CC 26** while `#doctor` sits at
**CC 30**. Growing either is the puxadinho shape on the surface carrying 13 bugs and 12
recurrences (§1.6). So: **`--recipe` only**, rendered by its **own** function (never inside
`#doctor`), the case-only renames executed by hand as recipe steps in T-050-06, and the
acceptance is measured rather than asserted — `#upgrade` **CC 26 → ≤ 26**, `#doctor`
**CC 30 → ≤ 30** (A1.4, V19). The migration chain may register whatever declarative v6 entry
keeps the version stamp reachable for a consumer sitting at v5, but **only** as a declarative
entry: any change that raises either function's complexity is refused at review. The deferred
rename automation is compiled as an intake candidate at closure.

**A release directory's conformant members are named by the canon, once** — `SPEC.md`,
`PLAN.md`, `TASKS.md`, `RELEASE.jsonl`, **`reviews/`** and **`verdicts/`**. Both of the last
two already exist at HEAD on live and archived releases and are law-mandated artifacts; a
canon that omitted them would make TREE-8 WARN permanently on this release's own files, and
would repeat the "a law-mandated artifact needs its own whitelist line" defect the
`.gitignore` already records nine times.

**FR1 owns two boundaries the canon change breaks, and they are in its write set:**

1. **`.gitignore` (S-2).** The `/specs/*` catch-all plus per-artifact opt-in is the shape
   that produced the nine-instance gitignore class, and it was already inverted once, for
   `specs/releases/**`. FR1 applies **the same proven inversion** to every area this release
   creates or moves: `!/specs/audits/**`, `!/specs/ADRs/**`, `!/specs/bugs/_archive/**`,
   `!/specs/backlog/_archive/**`, `!/specs/releases/_archive/**`, with only the narrow
   scratch class (`local-notes.md`, `tmp/`) denied. Verified today with `git check-ignore
   -q`: `specs/audits/<slug>/FINDINGS.jsonl`, `specs/ADRs/0001-x.md`, `specs/ADRs/AGENTS.md`
   and `specs/backlog/_archive/backlog_histo.jsonl` are all **IGNORED** — three of this
   release's own governance artifacts would have been born untracked, never reviewed, and
   never seen by the range-scoped denylist scan. The stanzas FR1/FR6 orphan
   (`specs/assets/`, `specs/backlog/remote-bugs/`, root `specs/_archive/`) are deleted in the
   same edit. The widening is a **deliberate privacy decision**, stated as such: the
   catch-all backstop is replaced by explicit per-area opt-in plus the push-time denylist
   scan, which is the boundary that actually holds.
2. **The CI verdict-evidence contract (S-1, AS-15).** `.github/scripts/pr-verdict-check.sh`
   resolves verdicts by globbing `specs/releases/*/verdicts/` and
   `specs/_archive/releases/*/verdicts/`. After FR6 the first glob no longer matches the new
   archive home (`specs/releases/_archive/<id>/verdicts/` is one level deeper and a
   **pathname** glob's `*` does not cross `/`) and the second path does not exist at all;
   `_RELEASE_ID_RE` additionally requires a `v` prefix that bare-semver ids do not carry.
   Both remaining PRs — the final `rc` and the ship PR — would fail a **required** check, and
   the release could not ship. **Exactly one of the two glob sites is broken:** in a bash
   `case` pattern `*` *does* cross `/`, so the offender allowlist at `pr-verdict-check.sh`
   (the `case` deciding which changed paths disqualify coverage) already matches
   `specs/releases/_archive/<id>/verdicts/*` and is **not** part of the defect — a fact
   T-050-06A records so no one "fixes" a working line. FR1 therefore derives the gate's
   evidence roots and its release-id pattern from `dadaia_workspace/core/specs_version.py`
   (one source, the canon) instead of hard-coded globs, over the two roots AS-15 names, and
   keeps every refusal **fail-closed**: `_archive`, `_ideas` and any traversal shape are
   still refused before interpolation, and a missing qualifying handoff still fails the gate.

   **2a. The canon object flips to bare semver, and its consumer set is enumerated — in
   FR1, in T-050-06A's write set.** The object the gate is told to derive from is today
   `core/specs_version.py`'s `RELEASE_SEMVER_RE = ^v\d+\.\d+\.\d+(-…)?$` — documented in
   that module as *"the ONE release-id canon every public entry point validates against"* and
   identity-locked (same compiled object everywhere, no re-compiled copy) by
   `tests/contract/test_release_semver_canon.py`. Canon v6 moves live and archived ids to
   **bare** semver, so the canon itself must flip; deriving the gate from a constant that
   still mandates `v` would re-create the defect one layer up. The flip is **stated here and
   scoped to T-050-06A**, with the same discipline FR4 applies to `ACTIVE.md`'s 28 consumers:
   - the pattern **stays anchored** `^…$` and keeps its optional `-suffix` segment; it gains
     an **optional** `v` prefix so the retired axis (AS-13 — every archived id is
     `v`-prefixed) still resolves for **read-only archive lookups**, while the current axis
     is bare. Two axes, **one** compiled object: `is_release_semver` remains the predicate
     for the current axis (bare only, so nothing can *mint* a `v`-prefixed id), and the
     optional-`v` match is used only to *resolve an id that already exists on disk*. No
     second pattern, no re-compiled copy, no traversal or `_`-prefixed shape admitted.
   - **Production consumers, verified at HEAD (grep, four call sites in three modules):**
     `dadaia_workspace/features/specs/scaffolder.py` (release-dir minting),
     `dadaia_workspace/features/specs/doctor_release.py` (**two** sites: release-folder
     naming and the archive scan), `dadaia_workspace/features/spec_artifacts/
     new_artifacts.py` (composed with its slug arm).
   - **Test consumers:** `tests/contract/test_release_semver_canon.py` (identity + the
     behaviour assertions `is_release_semver("1.2.3") is False` / `("v1.2.3") is True`, which
     **invert** with the axis and are rewritten under a recorded `qa-engineer` verdict, never
     deleted to go green) and `tests/unit/core/test_release_id_single_source.py`.
   - **The consumer the pass-2 review named does not exist on this tree:** there is no
     bug-lifecycle `resolved_release` validator — a grep for `resolved_release` across
     `dadaia_workspace/` returns **zero hits** at HEAD (the field is introduced by FR2 in this
     very release). Stated so the enumeration is closed rather than approximately closed.
   - **The derivation mechanism, named (no unnamed "derive from" left for an implementer to
     resolve by copying the regex back into bash).** `pr-verdict-check.sh` is bash and cannot
     import a Python object — the script's own comment says so and restates the pattern
     instead, which is the shape being retired. The gate instead **shells out to the
     interpreter on the bare checkout**: a one-line `python3 -c` that imports
     `dadaia_workspace.core.specs_version` from the repo root and prints the evidence roots
     and the id pattern, which bash reads. **Feasibility is verified, not assumed:**
     `security-verdict-gate` runs `bash` with no `setup-python` and no install step, and
     `dadaia_workspace/__init__.py` and `dadaia_workspace/core/__init__.py` are **empty**
     while `core/specs_version.py` imports only `re` and `pathlib` — a stdlib-only import
     that needs no installed package. Any richer export (`python -m … --gate-json`) would be
     **new CLI surface** and is refused (D15).
   - **Failure posture, stated (N-2).** Any derivation failure — interpreter absent, import
     error, missing symbol, empty or unparseable output — makes the gate **exit non-zero**
     with the reason. There is **no `|| <default glob>`**, no fallback root and no
     "assume the old pattern": a gate that cannot read the canon has not proved coverage.

**Bug-surface direction, with numbers (fold 3, K):** *net-additive in production LOC,
net-negative in surface count.* Production LOC **+≈200** (V19, per-FR). Scaffold `README.md`
**4 → 0**; canon-root shapes tolerated by the doctor **5 → 1**; `specs/assets/` and
`backlog/remote-bugs/` **1 → 0** each. Doctor check codes **47 → 48** here (+TREE-8), landing
at **≤ 45** release-wide once FR5 and FR15 delete theirs. Hand-kept truth constants: **+2**
(the canon-root tuple, the release-dir member tuple) against the release's **−13** (baseline
264 → ≈258, §5 of the metrics baseline). Complexity: `#upgrade` **26 → ≤ 26**, `#doctor`
**30 → ≤ 30**, functions with CC > 10 **131 → ≤ 133** release-wide with every new function
above 10 named in V19.
**Tests: +8 added / −2 deleted (named).** Added: TREE-8 WARN + exit-code fixtures (2), the
`--recipe`-traces-to-a-finding-id contract test (1), the `--recipe`-zero-findings-zero-steps
test (1), `#upgrade`/`#doctor` complexity assertions folded into the existing ratchet (0 new
functions), V21 `check-ignore` (1), V20's seven arms (3 functions, parametrized). Deleted, and
**named** (`qa-engineer` amendment 11): the scaffold `README.md` presence assertions in
`tests/unit/features/specs/test_scaffolder.py` (they assert an artifact this FR retires) and
the `assets/.gitkeep` scaffold assertion in the same file. The double-`upgrade` byte-comparison
fixture **replaces** nothing and is **not** added — A1.4 becomes a zero-diff assertion instead.
**Bug-history evidence:** the gitignore class (one class, **nine** registered instances,
§1.1) is a *governance-path* class — every instance was "a spec artifact that was not where
the canon said it was, or not where `.gitignore` allowed it to be". TREE-8 names the class
instead of patching instances, and the `.gitignore` inversion above refuses to re-enter the
shape that produced all nine. `remote-bugs-gitignore-blocks-new-intake` is one of the nine
and dies with the folder. The CI evidence contract carries its own history:
`verdict-gate-cannot-resolve-evidence-after-release-archive` (HIGH, T-044-50) is the
**second** firing of "the gate cannot resolve evidence after a release moves"; letting the
canon change land without it would be the **third**, and this time it would be discovered by
the release being unable to ship.

**Acceptance**
- A1.1 A freshly scaffolded workspace emits the v6 tree, `specs_pattern_version: 6`, scoped
  `AGENTS.md` per area, zero `README.md`, zero `assets/`.
- A1.2 TREE-8 reports any path under `specs/` that is not in the canon, as **WARN**; a
  fixture with a stray folder proves it, and a second fixture proves the exit code is
  unchanged (no block).
- A1.3 `specs doctor --recipe` emits ordered, concrete, copy-pasteable steps for every
  finding `specs upgrade` cannot execute; proven on this repo's own pre-migration tree.
  **`--recipe` is a *rendering of the same finding objects* `specs doctor --json` already
  emits** — the recipe text hangs off each finding, never a second step table that could
  drift from the findings (the `software-architect`'s accepted-with-condition on SA-11). A
  contract test asserts every `--recipe` step traces to a finding id present in the same
  run's `--json` output, and that a run with zero findings emits zero steps.
- A1.4 **`specs upgrade` is not grown** (fold 3). Its rename automation is cut; the acceptance
  is a **measured complexity assertion**, not a behaviour addition: `radon cc` reports
  `cli/commands/specs.py#upgrade` at **≤ 26** and `#doctor` at **≤ 30** after the release
  (baseline 26 / 30, `architecture-metrics-baseline.md` §2), and `--recipe` renders in its own
  function. Any declarative v6 entry added to the migration chain is proven not to raise either
  number. A zero-diff assertion covers `features/migrate/upgrade.py`'s existing steps.
- A1.5 The SDD gate's MEMORY-phase resolution and FROZEN class are repointed (FR4 supplies
  the phase source; FR6 supplies the archive paths) with **no new path class** and no second
  classifier. The **phase read** lives in `dadaia_workspace/hooks/sdd_gate.py`
  (`_active_field`, and its regex), not in `gate_policy.py` — the proof is the diff on
  **`hooks/sdd_gate.py`** being net-negative, plus `gate_policy.py`'s FROZEN prefix list
  changing by exactly one deletion and one addition (A6.3).
- A1.6 This repo's own `specs/` is migrated to v6 and `dadaia specs doctor` reports **0
  errors** afterwards.
- A1.7 **Every canon path is tracked.** A contract test asserts `git check-ignore` reports
  "not ignored" for each of: `specs/audits/<slug>/FINDINGS.jsonl`,
  `specs/audits/<slug>/AUDIT.md`, `specs/ADRs/0001-x.md`, `specs/ADRs/AGENTS.md`,
  `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/bugs_histo.jsonl`,
  `specs/backlog/_archive/backlog_histo.jsonl`,
  `specs/releases/_archive/releases_histo.jsonl`,
  `specs/releases/<id>/{RELEASE.jsonl,reviews/x.md,verdicts/<sha>.handoff.json}` (**V21**),
  and that the three orphaned stanzas are gone.
- A1.8 **The verdict gate resolves and refuses correctly against a v6 fixture tree, one
  stated expected outcome per arm** (**V20**), run **before T-050-41** (the archive move),
  not after it:
  1. a valid APPROVED handoff under the **live** `specs/releases/<id>/verdicts/` → **PASS**;
  2. the same handoff under `specs/releases/_archive/<id>/verdicts/` → **PASS** (the arm
     that is broken today);
  3. a would-be APPROVED handoff under `specs/releases/_ideas/<id>/verdicts/` → **the gate
     fails closed**: `_ideas/` is not an evidence root (AS-15), so this arm proves a
     *refusal*, not coverage;
  4. a **bare-semver** id is accepted as a narrowing value and a `v`-prefixed archived id
     still resolves an existing directory; `../`, `_ideas`, `_archive` and any other
     non-canon token are refused **before** interpolation;
  5. no qualifying handoff anywhere → **exit non-zero**;
  6. **a non-verdict path in the diff still disqualifies coverage:** the reviewed sha is an
     ancestor of the PR head and the intervening diff touches a path outside
     `*/verdicts/` — including the gate script's own offender-allowlist line — and the gate
     **refuses** that handoff. This arm exists so a derivation that touches the allowlist can
     never silently un-gate the check;
  7. the derivation itself fails (module or symbol unavailable) → **exit non-zero**, no
     fallback glob (FR1 boundary 2a).
- A1.9 The release-directory canon names `SPEC.md`, `PLAN.md`, `TASKS.md`, `RELEASE.jsonl`,
  `reviews/` and `verdicts/` as conformant, and TREE-8 emits **no** WARN on this release's
  own directory — proven on this repo's tree.
- A1.10 **The release-id canon is one object, flipped to bare semver, with every consumer
  moved with it** (FR1 boundary 2a). `tests/contract/test_release_semver_canon.py` still
  passes its **identity** assertion — every consumer resolves the *same* compiled object and
  no re-compiled copy exists anywhere — with its behaviour assertions inverted to the current
  axis under a recorded `qa-engineer` verdict; the three production modules
  (`scaffolder.py`, `doctor_release.py` ×2, `spec_artifacts/new_artifacts.py`) and
  `tests/unit/core/test_release_id_single_source.py` are updated in the **same** task; a
  fixture proves a new release id carrying a `v` prefix is refused at minting while an
  existing `v`-prefixed archived directory still resolves; and a zero-hit grep records that
  no `^v\d` release pattern survives outside the canon object and the archive-lookup arm.

#### FR2 — `BUGS.jsonl`: one record per bug, immutable core, mutable governance · **size M**

*Entry: `bug-lineage-and-commit-discipline` (A) · rulings D2, D11.*

`bug-event-v1.schema.json` is replaced by `bug-record-v1.schema.json`
(`additionalProperties: false` kept). One record per bug, appended once — no event stream, no
fold. The schema declares **three** field categories per property, not two:

- **Immutable core** — `id`, `ts`, `reported_by`, `title`, `severity`, **`surface` (a closed
  enum — see below)**, `component` (free text), `context`, `symptom`, `repro`, `expected`.
- **Write-once, absent until set** — `root_cause`, `solution`, **`evidence_loop`,
  `evidence_seam`, `evidence_diff`** (the v0.4.4 **FR23 evidence triple**, restored — fold 3,
  `software-architect` change 2), **`diff_direction`** (`net-negative|net-neutral|net-positive`),
  `superseded_by`, `migration_note`. They are legitimately missing from a freshly registered
  record and become immutable the moment they are written. This third category is why the
  earlier claim "the record's shape never changes" was false against this SPEC's own two
  examples, and it is tested (A2.2).
- **Mutable governance** — `status` (`open|resolved|superseded|deferred|rejected`), `cause`,
  `caused_by`, `lineage_source`, `registration_commit`, `registration_granularity`,
  `resolved_commit`, `resolution_granularity`, `resolved_release`, `audited`.

**The FR23 evidence triple is restored, not re-invented (fold 3).** `evidence_loop` (the
red-loop command actually run), `evidence_seam` (the regression test's seam) and
`evidence_diff` (what the diff did) exist **today** in `bug-event-v1.schema.json`
(lines 109/114/119) and are the **only structured evidence the ledger has ever carried** —
present on **23 of 92** recent resolutions (25 %, forensic §3), all but four of them from
v0.4.4 onward. The first Draft's record model dropped them, folding everything into a free-text
`solution`: that would have deleted the one measurable evidence field **in the release built to
make evidence measurable**, and FR3's migration could not have carried what the model no longer
had. D11 lists `cause`/`solution` as immutable core because they *are* the solution's
statement; the triple **is** that statement's evidence, so it takes the same write-once
posture. Forensic metric 2 (**25 % → target 100 % on post-0.5.0 resolutions**) becomes a
pillar-1 output (FR14).

**`surface` becomes a closed enum; free text moves to `component` (fold 3,
`software-architect` change 5, applied per the operator's single-source rule).** The forensic
had to hand-normalise **86 distinct `component` strings across 100 bugs** into 18 buckets
before recurrence could be counted at all — which means recurrence is not computable from the
record today, and pillar 1's "same `component`/`surface`" filter would be a substring guess.
The enum has **one source, the same one the independence contract uses (FR18/A18.5)**: the
feature-package inventory on disk. Members are the **24** `dadaia_workspace/features/<name>/`
packages (verified by glob at this fold), plus the non-feature layers `core`,
`infrastructure`, `cli`, `hooks`, `tests`, `public-assets`, plus **`unknown`**. A contract test
asserts the enum's feature arm **equals** the independence contract's `modules =` list, which
A18.5 makes equal to the packages on disk — so a package added tomorrow goes RED in one place
and is fixed in one place. `component` keeps the free-text `path#symbol` precision the fine-key
analysis needs. FR3 maps every legacy string; what it cannot map becomes `surface: unknown`,
**counted in the migration report** and never guessed.

**A sweep closure is `superseded`, not `resolved` (fold 3, forensic metric 8).** Nine of 92
recent resolutions were bulk "need met by shipped work" flips with no code-touching commit —
they read as fixes and pollute every rate computed from the ledger. One sentence of rule, no
mechanism: a record closed because another shipped item met the need takes
`status: superseded` with `superseded_by` naming it; `resolved` requires the regression seam.
Pillar 1 counts violations (baseline 9/92, target 0); nothing blocks.

**`picked` is not a status.** The pick is already recorded by the bundled definition commit
(FR8 shape 5) and is readable by pillar 2, so the value, its transition and `picked_by` all
disappear — one fewer enum member, one fewer branch in the fold, nothing lost.

A governance update rewrites that record's line in place — JSONL is a document keyed by `id`,
the line is the unit, git history is the change log. The rewrite is **read-modify-write**, so
it goes through the existing `dadaia_workspace/core/atomic_write.py` (temp file +
`os.replace`) and **re-reads the file immediately before rewriting**: the append-only stream's
`O_APPEND` made concurrent writes race-benign, and nothing in a record model replaces that
property for free. **One race semantics, stated once: refuse-stale, then the caller retries.**
Under the NO-LOCKS doctrine two live sessions may still collide; the writer compares the
file against the snapshot it read and, when it has moved, **refuses the rewrite** and returns
that to its caller, which re-reads and re-applies its change. Nothing blocks and nothing is
lost — a rewrite is never applied to a tree the writer did not see, and the file is never
left corrupt (A2.9). The earlier wording "the loser's write is *lost*" described a different
design (last-write-wins) and is withdrawn; pillar 1 still reports an in-window core-field
diff, which is the detection the design does not attempt to prevent.

A **reopen is a new record** with a new `id` declaring `caused_by: <prior-id>`. Registration
requires `symptom` + `repro` + `severity` + `expected`; reaching `status: resolved` requires
`cause` + `caused_by` + `resolved_release` + the regression seam in `solution`. Coherence is
checked as **WARN**, surfaced by `dadaia bugs status` and the doctor — **never a block** (D15).

**Redaction rides the existing write-time seam (S-3).** `core/models/bugs.py` gained, one day
before this Draft, a schema-derived redaction whose docstring records *why*: a hand-kept field
list "twice missed a newly added free-text field" (T-043-23 → T-044-62), and commits
`eb03d01b` / `0cb08157` (`v0.4.5` T-045-19) replaced it with a set derived from the schema.
FR2 adds **four** free-text fields at once (`cause`, `root_cause`, `solution`,
`migration_note`) and a **second** write path (the in-place rewrite). Both are routed through
that same seam — `BugService.append_event → BugEvent.redact` becomes
`BugService.write_record → BugRecord.redact`, with the field set still derived from
`bug-record-v1.schema.json` and **no hand-kept list anywhere**. The in-place update seam
redacts identically to the append seam; there is one redaction call site per write path and
both take the same derived set.

**"Derived" must become true — `_OPTIONAL_STR_FIELDS` is deleted, not re-mirrored (fold 3,
`software-architect` §3).** At HEAD `core/models/bugs.py:204` still holds a **16-name
module-level tuple** mirroring `bug-event-v1.schema.json`, and the redact docstring
(line 333) calls it "the SAME schema-mirror tuple". A mirror is a hand-kept list wearing a
derivation's name: it is the P1 class (16 of the last 100 bugs) sitting inside the very field
set whose two prior misses (T-043-23 → T-044-62) motivated the seam. FR2 **reads the property
names from the schema at load time**; the tuple is deleted, and **A2.10** asserts that
`core/models/{bugs,findings,release_events}.py` carry **zero** module-level field tuples.

**One write seam, three writers collapsed into it (fold 3, `software-architect` change 1 —
AS-16).** `features/bugs`'s record store is the **only** code path that may write a governance
field. It is the seam that already carries the atomic rewrite, the refuse-stale re-read and the
schema-derived redaction, and it is what makes A2.6/A2.9/A14.6 provable **on the executed
path** rather than only for whichever writer happens to be the CLI. Three writers exist in the
first Draft — registration, the fixer's resolve, the auditor's `audited` — and **two of them
would be file tools**. All three now go through this seam; core fields are refused at it
(A2.2), and the *exposure* of the seam is **AS-16, operator-gated** — one CLI verb
`dadaia bugs update` (recommended, leaf-neutral at **71**) or a skill-invoked Python entry
point (69 leaves). The SPEC fixes the seam; the operator fixes the door.

**`dadaia bugs archive` (A2.8, entry clause of `specs-canon-v6`).** The idempotent verb the
entry requires is in scope here, not deferred: terminal records older than 90 days move from
`BUGS.jsonl` to `specs/bugs/_archive/bugs_histo.jsonl`, one record per line, through the same
record-store seam; re-running it is a no-op; `specs doctor` emits an **overdue WARN** (never
an error, never a block) when terminal records past the threshold are still live.

The record as first appended — mutable-governance fields present and null; the write-once
fields absent until set:

```json
{"id":"certify-skip-detail-leaks-full-codex-output","ts":"2026-08-22T19:18:33Z","reported_by":"software-engineer","title":"certify skip detail leaks full codex output","severity":"MEDIUM","surface":"dadaia certify","component":"features/certification","context":"dadaia-workspace","symptom":"the skip detail line renders the whole probe output instead of a one-line reason","repro":"1. run certify with a provider that skips 2. read the skip detail","expected":"a one-line reason, output captured under .dadaia/tmp/","status":"open","cause":null,"caused_by":null,"lineage_source":null,"registration_commit":null,"registration_granularity":null,"resolved_commit":null,"resolution_granularity":null,"resolved_release":null,"audited":null}
```

The **same line** after the fix — immutable core byte-identical, the write-once fields set for
the first time, governance fields filled. Note what is **still `null`**: `resolved_commit` and
`resolution_granularity`, because a commit cannot contain its own sha (**AS-1**); the audit
fills them:

```json
…"root_cause":"the skip path formatted the raw probe transcript into the detail field","solution":"one-line reason built from the probe's status; transcript written under .dadaia/tmp/; regression test at the formatter seam","status":"resolved","cause":"the probe's own fix introduced the second render path","caused_by":"codex-live-probe-gate-checks-presence-not-usability","lineage_source":"declared","resolved_commit":null,"resolution_granularity":null,"resolved_release":"0.5.0","audited":null…
```

And the **same line again** after the audit that reviewed it — the one place `resolved_commit`,
`resolution_granularity` and `audited` are ever written, in a single atomic rewrite (FR14
pillar 1). Every other byte is identical:

```json
…"resolved_commit":"<40-hex derived by FR3>","resolution_granularity":"exact","audited":"20261020-five-release-window"…
```

**Bug-surface direction, with numbers (fold 3, K):** *net-negative in surface, +≈50 LOC.* The
fold logic (`reported` + N events → a state machine with terminal/non-terminal/repeatable
event kinds, seven `allOf` conditional blocks in the schema) is deleted and replaced by a flat
record; `core/models/bugs.py#BugEvent` becomes `BugRecord` with no state machine. Measured:
**write seams on `BUGS.jsonl` 3 → 1** (AS-16 — the release's one architecture-fidelity
regression, closed); **"two writers of one truth" 14 → 12** on the ledger (forensic P2 — the
pair `bugs-append-accepts-second-terminal-event` + `bugs-append-allows-terminal-event-without-reported`
collapses into one seam plus a WARN); **hand-kept truth constants −4** named
(`_OPTIONAL_STR_FIELDS` 16 names, `_BUG_LOG_RE`, `ROWS_PER_FILE`, `_sorted_files`);
**`ignore_imports` 15 → 14**, the retired edge named — `cli.commands.bugs ->
infrastructure.jsonl_bug_store` (`setup.cfg:232`) dies when the store is container-injected,
and the cap in `tests/contract/test_import_linter_ignore_cap.py` moves with it in the same
commit; **modules −2 / +2** (`jsonl_bug_store.py` + `core/protocols/bug_store.py` out,
`jsonl_record_store.py` + the record protocol in); **CLI leaves ±0** (AS-16 arithmetic).
**Tests: +9 added / −11 deleted (named).** Added: A2.2 a/b/c (3), A2.6 redaction-on-both-paths
(1), A2.9 stale-rewrite-refused (1), A2.8 archive idempotence (1), A2.10 no-field-tuple (1),
A2.11 FR23-triple write-once (1), A2.12 surface-enum-equals-package-list (1). Deleted, by
**file census** (`qa-engineer` amendment 2 — **9** files reference `BugEvent` at this fold, one
more than the review's 8; the census is **re-measured at task time**, never trusted from this
list): `tests/unit/features/bugs/test_service_picked_fold.py`,
`tests/unit/core/models/test_bugs_picked_event.py`,
`tests/unit/features/bugs/test_append_coherence.py`,
`tests/unit/features/bugs/test_jsonl_bug_store.py` — deleted whole with their subject; the
remaining five (`test_control_format_char_sanitation.py`,
`test_write_time_denylist_redaction.py`, `test_bugs_write_time_denylist_redaction.py`,
`test_live_bugs_ledger_still_parses.py`, `test_bind_resolution_seam_dynamic_walk.py`) are
**rewritten in place** against `BugRecord`, not counted as deletions. Each of the four carries
a `qa-engineer` verdict with the `file:line` of the coverage that supersedes it.
**Bug-history evidence:** the event stream itself produced a bug family — the U+2028 record
(`bug-event-field-with-unicode-line-separator-silently-drops-the-event`) is *silent event
loss*. **Stated precisely, because the first Draft overclaimed here:** the loss is caused by
`text.splitlines()` in the reader, which is fixed in `v0.4.5` T-045-20 (**AS-14**) — the
record model does **not** close it and must not claim to. What the record model does remove
is the *amplification*: with one line per bug, a lost line loses one bug, loudly and
countably (`bugs status` reports skipped lines), instead of half-folding a state machine
across a bug's several lines. The `picked`/`archived` non-terminal annotations, added to work
around the append-only model, disappear as `status` values.

**Acceptance**
- A2.1 The record schema is authored and `bug-event-v1.schema.json` retires; the
  **three-category** split (immutable core · write-once · mutable governance) is documented
  **per property** in the schema, not in prose elsewhere.
- A2.2 **Contract tests, stating what actually holds.** (a) An immutable core field cannot be
  changed on an existing record **through the service seam**; (b) a write-once field can be
  set from absent, and a second write to it is refused at the same seam; (c) a governance
  update rewrites the line in place leaving every other byte of the file identical. The test
  names, in its own docstring, the limit A2.7 measures: this is **seam-level** enforcement,
  and any agent's file tool can still rewrite any field.
- A2.6 **Redaction is schema-derived and covers both write paths.** A contract test adds a
  new free-text property to the schema fixture and proves it is scrubbed on *both* the append
  path and the in-place update path with **no code list edited** anywhere. The denylist terms
  come from the operator's configured set, as they do today.
- A2.7 **Immutability is detected, never prevented — and the detector exists.** `specs doctor`
  emits a **WARN** comparing each record's immutable core against FR3's first-add derivation
  (the derivation already exists; no new engine), and FR14 pillar 1 reports any in-window
  core-field diff as a HIGH finding. Proven by a fixture that hand-edits a core field with a
  file tool and shows the WARN and the finding, with the exit code unchanged.
- A2.8 **`dadaia bugs archive` is idempotent and non-blocking:** a fixture runs it twice over
  a corpus with terminal records older and newer than 90 days and proves byte-identical
  output on the second run, the newer records untouched, and the doctor's overdue signal a
  WARN with an unchanged exit code.
- A2.9 The in-place rewrite goes through `dadaia_workspace/core/atomic_write.py` and re-reads
  the file immediately before rewriting — proven by a test that mutates the file between read
  and write and shows the writer refusing a stale rewrite rather than clobbering it.
- A2.3 Coherence violations (resolved without `cause`/`caused_by`/`resolved_release`;
  superseded without `superseded_by`) are surfaced as **WARN** by `dadaia bugs status` and
  `specs doctor`, with **exit code unchanged** — proven by a fixture asserting the exit code.
- A2.4 `expand → switch → contract` (D-F): the record reader lands and every consumer switches
  before the event reader is deleted; each step independently green.
- A2.5 The v5 event shape is decoded by **one boundary adapter that lives in the migration
  module** (`dadaia_workspace/features/bugs/migrate_v5.py`), imported by nothing else and
  deletable with it — no v5 branch survives inside the bugs feature after the contract step.
  The record store itself is **model-agnostic**: `infrastructure/jsonl_record_store.py`
  exposes a generic `JsonlRecordStore` keyed by `id`, with parse/serialise injected through a
  `core.protocols` record protocol (sibling of the existing
  `core/protocols/git_object_reader.py`). Each feature owns its own model
  (`core/models/{bugs,findings,backlog}.py`) and receives its own store instance from the
  container; **no module knows more than one record shape**. The legacy hourly-file reader
  (`_BUG_LOG_RE`, `_sorted_files`, `ROWS_PER_FILE`, the v3→v4 consolidation) is deleted in
  the same task — it is dead under canon v6. **The deletion list is named in full:**
  `infrastructure/jsonl_bug_store.py` **and** its event-store protocol
  `core/protocols/bug_store.py` retire together — a protocol whose only implementation is
  gone is dead code behind a dead artifact, the FR15 shape applied to `core/`.
- A2.10 **Zero module-level field tuples survive.** `_OPTIONAL_STR_FIELDS`
  (`core/models/bugs.py:204`, 16 names at HEAD) is **deleted**, and a contract test asserts
  that `core/models/{bugs,findings,release_events}.py` declare no module-level tuple/list/set
  of property names — the field set is read from the schema. A zero-hit grep is recorded.
  Without this, A2.6 proves *scrub coverage* while a mirror quietly re-enters (fold 3, §3).
- A2.11 **The FR23 evidence triple is write-once and carried.** `evidence_loop`,
  `evidence_seam` and `evidence_diff` exist in `bug-record-v1.schema.json`, are settable once
  from absent, are refused on a second write at the seam, and FR3 migrates every v5 value that
  exists (baseline: present on 23 of 92 recent resolutions). `diff_direction` is a closed enum
  with the same posture.
- A2.12 **`surface` is an enum with one source.** A contract test asserts the schema enum's
  feature arm **equals** the independence contract's `modules =` list in `setup.cfg`, which
  A18.5 asserts equals the `dadaia_workspace/features/*/` packages on disk (**24** at this
  fold). Adding a package without extending either goes RED once, in one place. `component`
  remains free text; a fixture proves a legacy free-text surface is refused by the schema and
  lands as `unknown` through FR3's mapper only.
- A2.13 **One write seam on the executed path.** Every governance-field write — registration,
  resolution, `audited`/`resolved_commit` — goes through `features/bugs`'s record store, proven
  by a fixture that exercises **each** writer role and asserts redaction, atomic replacement
  and refuse-stale for all three (A2.6/A2.9/A14.6 hold for every writer, not only the CLI). Its
  exposure is **AS-16**, operator-gated; the acceptance is written so that either option
  satisfies it.

#### FR3 — Historical ledger rewrite: every record at branch cut, commits derived from git · **size L**

*Entry: `specs-canon-v6` (migration clause) + `bug-lineage-and-commit-discipline` (A) ·
rulings D2, D11 · the hard requirement of this release.*

**Every bug id present in `specs/bugs/bugs.jsonl` at branch cut** migrates to
`specs/bugs/BUGS.jsonl` in the FR2 record model, with `registration_commit` and
`resolved_commit` populated for the **whole** history from git. The corpus was 490 ids /
1 005 events on 2026-08-26 and reads 503 `reported` / 474 `resolved` events at this fold; the
acceptance is **"every record present at branch cut"**, never a frozen count (§1.2's
measurement note).

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
4. **Granularity marker (D-A).** Each derived sha is stored with its own marker —
   `registration_granularity` on `registration_commit`, `resolution_granularity` on
   `resolved_commit` — from one closed vocabulary:
   - `exact` — the commit adds exactly one bug's line **and** touches at least one file
     outside `specs/`;
   - `release-squash` — the commit adds more than one bug's line (release-level squash);
   - `ledger-only` — the commit adds exactly one bug's line and touches **no** file outside
     `specs/` (the code change is elsewhere or unknown).

   These three are **structural** definitions computed from the diff, and the acceptance
   thresholds below are derived from *them*, never from §1.2's differently-counted narrative
   metrics.
5. **Null only when nothing adds the line.** On the corpus measured today that is **0** cases;
   when it happens, the field is `null` and the record carries a `migration_note` naming the
   reason.
6. **Cause and lineage are never fabricated.** `cause` is copied from the v5
   `evidence_diff` / `notes` **only where that text literally states a cause**, else `null`.
   `caused_by` is populated **only** where a record's own text names another existing bug id
   (92 such cross-references exist) — every such link is stored with
   `lineage_source: "text-reference"` so audits know it is inferred. Everything else is
   `caused_by: null` (**AS-2**), `lineage_source: null`.
6b. **Every copied prose value is re-run through the redaction seam (S-4).** The migration
   does **not** write `BUGS.jsonl` directly. Every free-text value it carries forward —
   `symptom`, `repro`, `expected`, `notes`-derived `cause`, `migration_note` — goes through
   FR2's schema-derived `redact` (A2.6) with the operator's denylist terms loaded. This is
   not belt-and-braces: write-time denylist scrubbing only began on `eb03d01b`
   (2026-08-25), so the **entire** 1 005-event history predates it and denylisted terms may
   sit in `notes`/`evidence_diff` today. The migration report records **counts only** —
   never a redacted value, never the term that matched.
6c. **The rename voids the push-scan amnesty, and the procedure for that is stated, not
   discovered.** `bugs.jsonl` → `BUGS.jsonl` is a rename, so the new path has **no prior
   text**; `git_objects`' `prior_text` resolves per path and returns `None`, which means the
   range-scoped denylist scan suppresses nothing and re-flags every historical value as new.
   The first push after the migration is therefore **expected to be refused wholesale**, and
   the response is fixed in advance: run `dadaia ci push-gate-check` over the migration range
   **before** pushing (**V22**), remediate every hit **at the source record** through the
   redaction seam, and re-run until clean. **Never `--no-verify`, never a scan exclusion,
   never a suppression entry.** If a hit is a false positive, it is recorded in the migration
   report with its reason and the denylist is corrected at its source.
6d. **The FR23 triple and `surface` are carried, never re-derived (fold 3).** Every v5
   `evidence_loop` / `evidence_seam` / `evidence_diff` value present on a `resolved` event is
   copied verbatim into the record's write-once fields (baseline: **23 of 92** recent
   resolutions carry all three; the whole-corpus count is measured and reported). Absent stays
   **absent**, never `""`. `diff_direction` is populated **only** where the v5 `evidence_diff`
   text literally carries one of the three tokens — the forensic found the free text already
   says "net-negative"/"net-neutral"/"net-positive" — else absent. Legacy `surface`/`component`
   free text is mapped onto the FR2 enum by a **table in the migration module**, one row per
   legacy string, and every unmapped string becomes **`surface: unknown`** with the original
   preserved in `component`; the mapper's hit/miss counts and the full `unknown` list go in the
   migration report. Nothing is guessed and nothing is dropped.
7. **Legacy archive.** `specs/bugs/_archive/archive.jsonl` (114 `{file, content}` records)
   stays **byte-frozen** and is not converted (**AS-3**); the new
   `specs/bugs/_archive/bugs_histo.jsonl` is created empty and receives future archived
   records via `dadaia bugs archive`.

**The migration report** (`.dadaia/tmp/software-engineer/<YYYYMMDD>/bugs-migration-report.md`
+ its JSON sibling) records: ref scope and reachable ledger-commit count; records migrated
(with the branch-cut distinct-`bug_id` count it was compared against); registration commits
found / by granularity / distinct-commit count; resolution commits found / by granularity /
distinct-commit count; `cause` populated vs null; `caused_by` populated by `text-reference`
vs null; every `migration_note`.

**Its evidence is self-contained — the same rule as A13.5.** Every number the report or the
closure cites is written as **the reproducible command plus a redacted one-line result**
(`git log --all --no-merges --format=%H -- specs/bugs/ | wc -l` → `295`). A
`.dadaia/tmp/**` path is a **convenience pointer, never the citation**: that lane is GC'd at
three days, so a reader coming back at closure — or a remediation release reading a finding
months later — would follow a path that no longer exists. Headline counts additionally land
in this release's `RELEASE.jsonl` `note` records and in the closure record (CR-11).

**Bug-surface direction, with numbers (fold 3, K):** *net-additive, +≈280 LOC, of which
≈200 are deletable.* A one-shot conversion whose output is data, not a permanent branch. The
split is now structural, not a promise: **`core/bug_provenance.py` ≈80 LOC permanent** (pure,
consumed by FR8's resolver and FR14's pillar 1) and **`features/bugs/migrate_v5.py` ≈200 LOC
deletable** (v5 adapter + legacy-surface table + runner), with a contract test proving no
permanent consumer imports the deletable half (A3.10). Code modules **274 → 276** for this FR
(+2), side-effect call sites **+4** (report writes and the one `log_added_lines`), accepted
import edges **+0**. Nothing in the running bugs feature grows.
**Tests: +7 added / −0 deleted.** Added: five in-memory-history cases for
`core/bug_provenance.py` (single-bug registration · 3-bug squash · ledger-only resolution ·
line re-added by a later squash · never-added line), one `log_added_lines` synthetic-repo test
in `tests/contract/`, one idempotence double-run. **Marking (fold 3, `qa-engineer`
amendment 10):** the `core/bug_provenance.py` tests are `Intent: CONTRACT — 0.5.0 A3.10`
(permanent — the function outlives the migration); the `migrate_v5.py` adapter and runner tests
are `Intent: SCAFFOLD — T-050-09 — expires: 0.6.0`, the release that deletes their subject. A
slipped expiry is **renewed by an explicit `qa-engineer` verdict recorded at that release's
closure**, never by silence — V28 turns an unrenewed expiry RED.
**Bug-history evidence:** `specs-bugs-jsonl-store-gitignored` (the ledger itself was once
untracked) is why the derivation must run over **all refs including tags** rather than trust
`main`; the 155 release-squash resolutions and the 39/117 ledger-only resolution commits
(§1.2) are why the granularity marker exists at all.

**Acceptance**
- A3.1 **Every record present at branch cut migrates — none dropped, none invented.** The
  record count in `BUGS.jsonl` equals the distinct `bug_id` count of the v5 ledger **measured
  on the branch-cut tree in the same run**, proven by the report, which states that count.
  (490 on 2026-08-26; the ledger is live and the equality, not the constant, is the
  acceptance — §1.2's measurement note.)
- A3.2 `registration_commit` is non-null for **every migrated record**, spread over **≥ 124**
  distinct commits, of which **≥ 79** add exactly one bug's line — the two `≥` bars are the
  2026-08-26 floors and can only rise as the ledger grows; a count *below* one of them means
  the **ref scope** is wrong (V6). The **marker** distribution
  (`exact` / `release-squash` / `ledger-only`) is **measured and reported**, not thresholded:
  `exact` additionally requires a non-`specs/` file in the same commit, which §1.2 never
  measured, so `exact ≤ 79` and its true value is whatever the algorithm computes. A count
  below a `≥` threshold above means the **ref scope** is wrong (V6); a marker distribution
  that surprises is a **fact to record**, and re-running with a different ref scope to chase
  it is forbidden.
- A3.3 `resolved_commit` is non-null for **every resolved record present at branch cut**,
  spread over **≥ 117** distinct commits, of which **≥ 70** resolve exactly one bug (again
  2026-08-26 floors, not ceilings). `release-squash` and
  `ledger-only` counts are **measured and reported** against the structural definitions of
  step 4 — expect roughly **400** `release-squash` under the structural rule against §1.2's
  narrative **155**, because they count different things (§1.2). Neither number is a gate.
- A3.4 **Idempotence:** running the migration twice produces a byte-identical `BUGS.jsonl`
  and a report whose counts are identical — proven by an executed fixture, not by reasoning.
- A3.5 Every `caused_by` populated from prose carries `lineage_source: "text-reference"`;
  **zero** records carry `caused_by: "none"` (AS-2); zero records carry a `cause` string that
  is not literally present in the source record's text — proven by a scan comparing each
  populated `cause` against its source event.
- A3.6 `specs/bugs/_archive/archive.jsonl` is **byte-identical** before and after the release
  (`git diff --stat` empty for that path), and no audit window includes it.
- A3.7 **The live ledger parses fully and nothing is dropped.** `dadaia bugs status` renders
  **every** migrated record with no crash and **no silent drop**, reporting a skipped-line
  count of **0**. The fixture writes a free-text field containing U+2028 (and an ESC byte)
  **through the write seam**, and asserts the semantics T-045-20 actually has: those
  characters are **stripped** at write, so **the stripped record round-trips** — a read /
  write cycle is byte-stable — the file parses, `skipped: 0`, and **no historical record is
  rewritten** by the check. *"A record carrying U+2028 round-trips byte-identically" is
  unsatisfiable by construction against that fix and is withdrawn* (it would go RED against
  the very fix it verifies). The fixture **exercises** the fix (AS-14) rather than
  re-implementing it, and goes RED on any tree without it — there the character survives the
  write and the reader splits the line, so `skipped` is non-zero.
- A3.8 The migration is a **separate commit** from the FR2 schema change, and the report is
  referenced from it.
- A3.9 **Zero unredacted prose reaches the new ledger.** `dadaia ci push-gate-check` over the
  migration range returns clean **before** the first push (**V22**), and the migration report
  contains counts only — a scan of the report for values, terms or absolute paths returns
  zero hits.
- A3.10 **The derivation is a pure function and it lives in `core/`** (fold 3,
  `software-architect` change 4 — the first Draft called it "a pure core function" while
  T-050-09 placed it in the deletable `features/bugs/migrate_v5.py`, which FR8's resolver and
  FR14's pillar 1 then depended on: a permanent consumer importing a module declared
  disposable). Its home is **`dadaia_workspace/core/bug_provenance.py`** — pure, stdlib-only,
  over an iterator of `(sha, parents, date, touched_paths, added_lines)`. `migrate_v5.py` keeps
  **only** the v5 line adapter, the legacy-`surface` mapping table and the one-shot runner, and
  stays deletable **without touching a single permanent consumer**; a contract test asserts
  `core/bug_provenance.py` imports nothing from `features/**` and that no permanent consumer
  imports `migrate_v5`. Git access is a `core.protocols.GitHistoryReader` implemented in
  `dadaia_workspace/infrastructure/git_subprocess.py` (`GitSubprocessClient` gains
  `log_added_lines(pathspec)`) and injected via the container — so `features/**` imports
  neither `infrastructure` nor `subprocess`, and `lint-imports` stays green with **no new
  accepted edge**. Its unit tests run the pure function over an in-memory history fixture;
  no synthetic git repository is required for them.
- A3.11 **Every carried value is counted.** The migration report states: FR23-triple values
  carried (all-three / partial / none), `diff_direction` populated vs absent, `surface` mapped
  vs `unknown` (with the `unknown` list), each as a count against the branch-cut corpus. A
  `surface: unknown` share above **10 %** is a fact to record and a mapper row to add — never a
  reason to widen the enum.

#### FR4 — `RELEASE.jsonl`: milestone shas replace `ACTIVE.md` and `CLOSURE.md` · **size L**

*Entry: `specs-canon-v6` (releases part) · rulings D3, D7, D11.*

Each release directory gains `RELEASE.jsonl` (`release-event-v1`: `{ts, event, agent, data}`)
with exactly **seven** kinds — `phase`, `defined`, `implemented`, `shipped`, `audited`, `rc`
(open/close carried as `data`), `note`. The first Draft listed fifteen; `created`,
`spec_status`, `review`, `push`, `pr`, `ship` and `archive` are dropped because each is
already recorded elsewhere and none is required by D3: the SPEC header is the source of
status, `phase: ARCHIVED` *is* the archive record, `ship` duplicated `shipped`, and pushes
and reviews are git and `reviews/` facts. Smaller schema, smaller fold, nothing lost.

**No `session_id`.** A harness session id lives in `.dadaia/sessions/` (PROTECTED) and in
allowlist-gated telemetry; committing it into `specs/` would link every governance milestone
to a local session identifier permanently, for no governance value. The envelope is
`{ts, event, agent, data}` and the schema forbids any additional property.

The SDD gate folds the **last** `phase` record for the MEMORY path class. Individual commits
stay out; **milestone records carry `sha` (+ `pr`) as immutable facts** at exactly three
points, plus `audited` whenever an audit runs:

```json
{"ts":"2026-08-28T14:02:11Z","event":"defined","agent":"product-engineer","data":{"sha":"4e5f6a7","pr":210}}
{"ts":"2026-09-03T18:40:05Z","event":"implemented","agent":"qa-engineer","data":{"sha":"b8c9d0e","rc":2}}
{"ts":"2026-09-04T10:15:00Z","event":"shipped","agent":"project-manager","data":{"sha":"f1a2b3c","pr":214,"tag":"0.5.0"}}
{"ts":"2026-10-20T09:00:00Z","event":"audited","agent":"project-auditor","data":{"sha":"c0ffee1","audit":"audits/20261020-five-release-window"}}
```

**`implemented` is written at the final-`rc` QA close, on that closed commit's sha** — D3's
own wording — and **not** at the final-`rc` PR merge. The two differ by the merge commit, and
picking the QA-close sha is what makes the `[defined, implemented]` window a range of *worked*
commits rather than a range ending in an integration artifact. T-050-42 records it at that
moment and merges afterwards.

**The fold has one home: `dadaia_workspace/core/release_events.py`** — a stdlib-only,
tri-state resolver in the same shape as today's `_active_field`. `hooks/sdd_gate.py` calls it
directly (hooks never import the container, standing law), and so do `container.py` and the
doctor. One reader, one fold, three callers.

**`release_events.py` is read-only, and the append seam is named (fold 3,
`software-architect` §2 — an `UNSPECIFIED` closed).** The module **reads and folds; it never
writes**, so `core/`'s "modules mixing compute and write" count (53 of 77 writer modules at
baseline) does not gain a member. Milestone and `phase` records are appended by **agents with
file tools** — one writer class, stated plainly: T-050-11 (back-fill), T-050-26 (`audited`),
T-050-28/33 (the memory window), T-050-37/38 (`rc`), T-050-42/43 (`implemented`, `shipped`).
That is acceptable **because `RELEASE.jsonl` is append-only** — no in-place rewrite, no
read-modify-write, so the `O_APPEND` race-benign property the bug ledger had to give up is
kept here for free. A contract test asserts `core/release_events.py` contains no write call
(`open(... "w"/"a")`, `write_text`, `atomic_write`).

`ACTIVE.md` and `CLOSURE.md` **retire**: the active release and phase are the fold of the
newest `RELEASE.jsonl`; the closure narrative moves into the final `rc`'s records plus the
release's own `SPEC.md` provenance. **`ACTIVE.md` has 28 consumers in `dadaia_workspace/`,
and the retirement is not done until every one is repointed.** Enumerated from the tree:
`container.py`; `core/exceptions.py`; `core/release_events.py` (the new fold);
`features/specs/{doctor,doctor_common,doctor_release,doctor_structural,scaffolder}.py`;
`features/reports/next.py`; `features/spec_context/gate_policy.py`; `hooks/sdd_gate.py`
(`_active_field` and its regex); `cli/commands/specs.py` (the `specs release` / `specs
segment` verbs); six personas under `public/agents/`; five skills under `public/skills/`;
`public/scaffold/AGENTS.md`; `public/templates/specs-AGENTS.md`; and
`public/data/DADAIA.md`. `CLOSURE.md` appears in seven further modules
(`doctor_closure_audit.py`, `doctor_release.py`, `doctor_governance.py`,
`doctor_structural.py`, `doctor_common.py` — `RELEASE_ARTIFACTS` —, `catalog.py`,
`memory_lint.py`), and the parsers not covered by FR15 are retired by FR15's extended scope,
never left as dead code behind a file that no longer exists. On the test side, **26 test
files reference `ACTIVE.md` and 4 reference `CLOSURE.md`/`CLOSURE-TEMPLATE`**; each is
rewritten or deleted under a named `qa-engineer` verdict, never silently orphaned.

**Ordering (expand → switch → contract).** The `RELEASE.jsonl` writer/reader lands in `S1`
(T-050-11) and runs **in parallel with `ACTIVE.md`**. The **contract step — deleting
`ACTIVE.md` — moves to `S2`, immediately after T-050-21**, because the personas, skills and
law file that cite it are owned by FR11/FR12 in `S2`. Deleting it in `S1` would leave the
always-on law naming a file that does not exist for a whole segment: an expand→contract
violation by this SPEC's own D-F. A4.5's "at least one commit" therefore reads honestly
across the segment boundary.

Back-fill: `specs/releases/_archive/releases_histo.jsonl` (**D-G**) receives one milestone
block per already-archived release, `sha` and `pr` taken from that release's `CLOSURE.md`
tables where they are given, `null` where they are not — read **before** FR6 deletes the
archive. **Both archive layouts are scanned**, because the archive carries two:
`specs/_archive/releases/<id>/` (93 directories, four of which are not versions —
`ctx-inject-v2-drift-fix-v1`, `memory-markdown-source-v1`, `multiharness-engine-v0116`,
`pi-fourth-harness-v1`) and `specs/_archive/<id>/` (30 entries, `v0.1.47` … `v0.2.3`). V7's
denominator is defined as **the count of directories the scan actually visits across both
layouts**, reported with the four non-version directories named and excluded.

**Bug-surface direction, with numbers (fold 3, K):** *net-negative in surface, +≈50 LOC.* Two
hand-authored Markdown files with parsers (`ACTIVE.md`'s two-line schema; `CLOSURE.md`'s
section-and-table regexes in `doctor_closure_audit.py`) collapse into one machine record read
by one fold. Measured: **release-phase authorities 28 → 1** (the 28 enumerated consumers →
`core/release_events.py`); **modules reading `ACTIVE.md` 10 → 0**, reading `CLOSURE.md`
**4 → 0** (metrics baseline §5); **regexes parsing release prose 22 → ≈9** together with FR15
(**−59 %**), of which `_active_field`'s **2** die here; **hand-kept constants −2**
(`_active_field`'s two regexes) **+1** (the seven event kinds); **CLI leaves −2** —
`specs release open` and `specs segment open` (`cli/commands/specs.py:26,28`, both writing
`ACTIVE.md` through `_write_active` at lines 390/428) are **dead** once the phase is a fold and
are deleted in T-050-21A, which is the offset AS-16's arithmetic spends.
**`_ideas/` release directories carry no `RELEASE.jsonl`** (fold 3, contradiction 4): D10's
commit rule makes an `_ideas/` release **SPEC-only**, so the window scan of FR14 and A4.6 reads
the **live** release, `releases/_archive/**` and `releases_histo.jsonl` — and nothing under
`_ideas/`. The first Draft scanned `_ideas/**` for milestones that the canon forbids it to
carry; the scan is narrowed, not the rule.
**Tests: +5 added / −0 deleted here; the (26+4) census is dispositioned at T-050-21A with a
measured floor of −3 (fold 4, §9.4).** Added: milestone immutability (1), the no-`ACTIVE.md`
gate fixture (1, at T-050-21A), the `release_events.py`-is-read-only contract test (1), the
seven-kind schema fixture (1), V7's back-fill assertion (1). The **26 `ACTIVE.md` files**
(re-verified at this fold: 26 files, 84 occurrences) and **4 `CLOSURE.md`** files each carry a
`qa-engineer` per-file verdict at T-050-21A; every file whose *whole subject* is the retired
artifact is **deleted**, not rewritten. **Two files meet that test by inspection today** —
`tests/unit/features/specs/test_active_md_schema_v2.py` (**1** test function, 5 collected
items, its only subject `read_active_md`) and `tests/contract/cli/test_cli_specs_segments.py`
(**2** test functions, 4 collected items, their only subject the two verbs this task deletes)
— so the census floor is **−3 test functions**, counted the way V25 counts (`^def test_`),
inspected rather than predicted. The remaining census files are mixed-subject and are
rewritten in place; every further deletion their per-file verdicts produce **raises** the
floor and is counted in V25.
**Bug-history evidence:** the release-state surface has produced repeated bugs of the
"artifact says one thing, tree says another" shape — the v0.4.4 verdict gate resolving by
artifact across two trees (`ACTIVE=none` broke it), and the gate's phase lookup depending on
a file an agent hand-edits. A folded event stream has one writer and one reader.

**Acceptance**
- A4.1 `RELEASE.jsonl` exists for the live release; the SDD gate resolves the MEMORY phase by
  folding it, with `ACTIVE.md` gone and **no fallback branch** left behind (proven by the
  gate diff and a fixture with no `ACTIVE.md` present). **Owned by T-050-21A, not T-050-11**
  (fold 3, traceability gap 1): T-050-11 is the *expand* half and its done criterion is
  "`ACTIVE.md` still present", which cannot evidence an acceptance requiring it gone.
  T-050-11 evidences **A4.1a** — both files live, read in parallel, agreeing — and A4.1
  proper is evidenced at the contract step.
- A4.2 The three sha-bearing milestones are appended at their defined moments during **this
  release's own** lifecycle, and are immutable — a contract test refuses a rewrite.
- A4.3 `releases_histo.jsonl` carries one block per archived release; every sha it claims is
  resolvable by `git cat-file -e <sha>`, and every unavailable value is `null`, never a
  guess. The count of releases back-filled and the found/null split are recorded (V7).
- A4.4 **Every `CLOSURE.md` parser has a named fate.** `doctor_closure_audit.py`'s
  disposition regexes retire under FR15; the remaining `CLOSURE.md` checks in
  `doctor_closure_audit.py`, `doctor_release.py` and `doctor_governance.py`, plus
  `RELEASE_ARTIFACTS` in `doctor_common.py`, are **deleted** under FR15's extended scope. A
  zero-hit grep for `CLOSURE.md` across `dadaia_workspace/features/**` is recorded; no check
  survives against a file that no longer exists.
- A4.5 `expand → switch → contract`, **across the segment boundary**: `RELEASE.jsonl` is
  written and read in parallel with `ACTIVE.md` from T-050-11 (`S1`) until the contract step
  after T-050-21 (`S2`), by which point every one of the 28 consumers above is repointed;
  each step independently green.
- A4.7 The 28 `ACTIVE.md` consumers and the 26 + 4 test files are enumerated in the task that
  repoints them, and a zero-hit grep for `ACTIVE.md` outside `_archive/` and git history is
  recorded at the contract step.
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

**The code lives in `features/backlog/**`, not in the specs doctor.** BL-DUP is implemented in
`dadaia_workspace/features/backlog/doctor.py` (and referenced across that module), and the
in-file `## LEDGER` this FR retires is parsed by `features/backlog/document.py` and
`features/backlog/ledger.py`. FR5's write set is those three modules plus the scaffold; the
earlier attribution to `features/specs/doctor_governance.py` was wrong.

**BL-STALE keeps its data feed (the cross-cutting catch).** `features/backlog/ledger.py`
reads `specs/_archive/<release-id>/consumed_backlog.json` and documents that an absent ledger
degrades to `{}` — "BL-STALE is a no-op, never a false ERROR". **18 such sidecar files exist
under the root `specs/_archive/` that FR6 deletes.** Deleting the tree without relocating them
would make a backlog-doctor rule go quiet without ever failing — the exact "documented
convention with no data behind it" shape FR13 condemns. FR5 therefore **relocates all 18
sidecars into `specs/backlog/_archive/consumed_backlog_histo.jsonl`** (one record per release,
carrying the release id and its consumed slugs) and repoints `ledger.py` at it, **before** FR6
runs. The degrade-to-`{}` behaviour is kept for a genuinely absent record; what is removed is
the accidental permanent absence.

**Bug-surface direction, with numbers (fold 3, K):** *net-negative, −≈60 LOC.* The
dual-section document (ACTIVE + LEDGER) whose invariants `backlog doctor` polices (BL-DUP,
BL-STALE) becomes a single-section document plus an append-only file; the duplicate-ledger-line
class (BL-DUP) becomes structurally impossible. Measured: **BL check codes 4 → 3**;
`features/backlog/document.py` **LEDGER regexes 7 → ≈4**; hand-kept constants **−3**. The
backlog histo takes a **third instance** of the generic store — `core/models/backlog.py` exists
at HEAD and gains its container registration **here** (fold 3, traceability gap 4: A13.4 claims
"three registrations" and the third had no task write set).
**Tests: +3 added / −4 deleted (named).** Added: the exit fixture (1), the 18-sidecar
relocation + BL-STALE-still-fires fixture (2). Deleted with their subject, per `qa-engineer`
§7's best-in-class model — BL-DUP's tests **die because the invariant became structurally
impossible**, not because it stopped being watched: the BL-DUP cases in
`tests/unit/features/specs/test_doctor_ledger_invariants.py` and the backlog-doctor duplicate
cases, enumerated per-file at task time with the `file:line` of the structural argument.
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
- A5.5 **All 18 `consumed_backlog.json` sidecars are relocated and BL-STALE still fires.** A
  fixture proves BL-STALE reports a stale `ACTIVE` item using a relocated record, and the
  count of relocated records (18) is asserted. Relocation completes **before** FR6.

#### FR6 — [operator] Root `specs/_archive/` is tagged, then deleted · **size S**

*Entry: `specs-canon-v6` (destructive step) · operator ruling **D1 of 2026-08-23**: "git
history is the archive"; executed **only with the operator present** (D-H).*

**Bug-surface direction, with numbers (fold 3, K):** *neutral in LOC, neutral on the
spec-context surface.* FROZEN prefixes **1 out / 1 in** (`gate_policy.py`); path classes
**5 → 5**; classifier branches **unchanged**. §1.6 states the consequence plainly: this
release does **not** reduce the spec-context surface (10 bugs, 9 re-bugged) — it moves one
string and adds four fixtures.
**Tests: +5 added / −1 deleted (named).** Added: one FROZEN fixture per enumerated post-v6
path (4) and V8's throwaway-clone reachability (1). Deleted: the single-root FROZEN fixture
whose subject (`_FROZEN_PREFIX = "specs/_archive/"`) this FR retires — named at task time from
`tests/unit/hooks/` and `tests/integration/gate/`.

**Acceptance**
- A6.1 An `archive/specs-archive-<YYYYMMDD>` tag is created **and pushed**, and its
  reachability is proven **from the remote, not locally**: `git ls-remote --tags origin`
  lists it, then a throwaway clone fetches it and `git show <tag>:…` succeeds **from that
  clone**. A local `git show` proves nothing about a tag that never left the machine, and the
  entire recovery story for an irreversible deletion rests on this one premise.
- A6.2 FR3 (A3.x), FR4 (A4.3) and **FR5's sidecar relocation (A5.5)** are complete and
  committed **before** the deletion, **and every historical `verdicts/**` directory under
  root `specs/_archive/releases/*/` is relocated** to the per-area archive alongside its
  release, with the CI gate proven against the relocated path (**A1.8 / V20**). The archive
  is not read only by the back-fills: it holds every past security approval, and deleting it
  without relocation is what breaks the required PR check.
- A6.3 The deletion is one commit, executed with the operator present, and the FROZEN gate
  class is repointed in the **same** commit — never a window where FROZEN points at nothing.
  The **post-v6 FROZEN set is enumerated exhaustively**, one fixture per path:
  `specs/releases/_archive/`, `specs/bugs/_archive/`, `specs/backlog/_archive/`,
  `specs/audits/_archive/`. Concretely this is *one deletion* (`_FROZEN_PREFIX =
  "specs/_archive/"`) and *one addition* (`specs/releases/_archive/`) — the other three
  prefixes already exist in `gate_policy.py`. Omitting the addition would leave every
  archived release **MUTATING**, freely rewritable in IMPLEMENTATION mode: a net integrity
  loss versus today. `specs/releases/_ideas/` stays **MUTATING deliberately** — a Draft is
  meant to be edited — and that is stated, not left to inference.
- A6.4 After the deletion, `git show <tag>:specs/_archive/releases/v0.4.4/CLOSURE.md`
  succeeds **from the throwaway clone of A6.1** — demonstrated and captured, not asserted.
- A6.5 No `archive/*` tag is deleted by this release (AS-9).
- A6.6 **The tag push has a stated refusal path.** Tags are scanned by the range-scoped
  denylist scan and can be refused. If the push of `archive/specs-archive-<date>` is refused:
  stop, redact at the source object, re-tag, push again. **Never `--no-verify`, never disable
  the scan, never force past it.** The deletion does not proceed until the tag is on the
  remote and proven reachable from it.

---

### Segment `S2` — lineage, commit discipline, hooks, and the validated map

Owner: `ai-engineer` (skills, personas, `DADAIA.md`, `AGENTS.md`) + `software-engineer`
(contract tests, hook scripts, CLI).

#### FR7 — `dd-diagnose`, with the lineage check as phase 0 · **size M**

*Entries: `dd-diagnose` + `bug-lineage-and-commit-discipline` (B) · ruling D8 · **AS-11**.*

A new model-invoked core skill `dd-diagnose`, called by `dd-bug-resolution`, carrying the
diagnosing method as ordered phases each ending on a checkable *Done when*:

- **Phase 0 — lineage (D8), bounded.** Filter `BUGS.jsonl` for records with the same
  **`surface` (now an exact enum match, FR2) or `component`** inside the audit window (since
  the newest `audited` milestone in the live release, `releases/_archive/**` or
  `releases_histo.jsonl` — never `_ideas/`, which carries no `RELEASE.jsonl`; or the whole file
  when none). **The read is capped at the 20 most recent matching records, ordered by
  resolution date, and only those with `resolution_granularity == "exact"` are diffed**
  (fold 3, `software-architect` §5): at 3.2 bugs/day over a five-release window the uncapped
  filter is 100–300 records per fix, which is how a procedure becomes a ritual nobody performs.
  Twenty is the number; a fixer who wants more runs the audit. Read each prior record's
  resolution diff —
  `git show <resolved_commit>` when `resolution_granularity == "exact"`, and, when it is
  `release-squash` or `ledger-only`, say so instead of pretending the diff is the fix. Declare
  `caused_by: <bug-id>` or `caused_by: none`, with evidence, in the record and echoed in the
  fix commit body:

```text
caused_by: codex-live-probe-gate-checks-presence-not-usability
evidence: git show <its resolution sha> added a second render path in the certify skip branch; this bug is that path emitting the raw transcript.
prior diffs read: codex-live-probe-gate-checks-presence-not-usability (exact), certify-cannot-install-installed-provider (ledger-only — not diffed, coarse)
```

Every bug id in this SPEC's examples is a **real record** in `specs/bugs/bugs.jsonl`; shas are
written as placeholders only where FR3 derives them and the pre-canon history does not record
them. No illustrative identifier is invented.

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

**Bug-surface direction, with numbers (fold 3, K):** *net-additive in AI-surface lines,
net-negative in duplicated procedure; **zero** production LOC.* `dd-bug-fix` §3–§5 today
restates outcomes without procedure; that text is **moved**, not copied, and
`dd-bug-resolution` gets shorter. A coverage table (every removed block → its surviving home)
is mandatory. Measured: skills **21 → 22**, skill siblings **+1** (`LINEAGE.md`); CLI leaves
**+0**, hook files **+0** (A7.5). The governance cost is stated rather than hidden: **steps per
bug 7 → 9** (an isolated registration commit, and phase 0's bounded lineage read) — a
deliberate +2 whose payoff is forensic metric 1, **28 % → 100 %** attributable resolutions
going forward. Phase 0's cost is bounded at **≤ 20 records / ≤ 20 `git show` calls** per fix.
**Tests: +0 added / −0 deleted.** FR7 authors AI-surface text only; its acceptance is the
coverage table, the citation check (A7.2) and the zero-diff grep over `cli/`+`hooks/` (A7.5) —
none of which is a new test function. Stated explicitly so "AI work" never quietly imports a
test-count increase.
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
3. **The fix is contained in the commit that resolves — and there is no second commit.**
   `fix(<scope>): <what> (resolves <id>)` stages the code, the regression test and the
   `BUGS.jsonl` line carrying `status: resolved`, `cause`, `caused_by`, `resolved_release`.
   `resolved_commit` stays `null`: a commit cannot contain its own sha, git is the authority,
   and the audit writes the cache (**AS-1**, re-decided). The follow-up
   `chore(bugs): <id> resolved @<sha>` ledger commit of the first Draft — shape 3b — is
   **deleted**: it was a second writer of one value and a second ledger commit per bug that
   pillar 2 would have to learn to recognise, against D10's own "the fix is contained in the
   commit that resolves".
4. **No push on bug resolve** (D4) — commit only; a push happens when the operator asks, and
   then the agent runs `dadaia ci preflight` first because it is an always-on rule (FR9/FR11),
   not because a hook forces it.
5. Release definition is **one bundled commit** (SPEC + PLAN + TASKS + purge-on-pick + the
   picked bugs' records); an `_ideas/` SPEC commit carries the SPEC only. There is no
   `picked` status to write (FR2) — the pick is the commit.

**One resolver seam, one writer.** `resolved_commit` has exactly one resolver: a function that
returns the stored value when present and derives it (FR3's algorithm, scoped to one id)
otherwise. Git is the authority; the field is a cache; and the **only writer of that cache is
FR14's pillar 1**, in the same atomic in-place rewrite that sets `audited`. Pillar 1 reports a
stored value that disagrees with the derivation as a finding.

**`registration_commit` has a named writer too (fold 3, traceability gap 5).** The first Draft
named a writer for `resolved_commit` (pillar 1) and none for `registration_commit` on
post-0.5.0 records, leaving a field with no filler. Same answer, same seam: **pillar 1 writes
both derived shas and both granularity markers in the one atomic rewrite that sets `audited`**
(A14.6 extended). Registration itself stays `dadaia bugs append` in an isolated commit
(shape 1), which is what makes the derivation `exact`.

**Bug-surface direction, with numbers (fold 3, K):** *net-negative in code, net-additive in
documented rule.* Nothing is added to the CLI or the hooks by this FR; one resolver function
replaces the ad-hoc `git log --grep <slug>` recipes scattered through skills. Measured:
commits per bug **1–2 (often 0 attributable) → exactly 2, both attributable**; forensic
metric 1 **28 % → 100 %** on post-0.5.0 resolutions; ad-hoc `git log --grep` recipes in skills
**→ 0**, replaced by one resolver in `core/bug_provenance.py` (A3.10).
**Tests: +2 added / −0 deleted.** The audit-filled-equals-derived contract test over ≥ 20
historical records (1) and the duplicate-statement scan (1).
**Bug-history evidence:** §1.2 — 155 resolutions inside release squashes and 39 ledger-only
resolution commits mean the history cannot be diffed. These five shapes are the minimum that
makes the *next* 490 bugs diffable.

**Acceptance**
- A8.1 Every shape above appears exactly once across the AI surface, with the other homes
  pointing at it — proven by a duplicate-statement scan whose zero-hit result is recorded.
  **The scan's stated scope covers three surfaces, not two:** `DADAIA.md`, every core skill,
  **and every scoped `AGENTS.md`** (FR12 authors or rewrites seven of them in the same
  segment, so a pair-wise scan that skipped them would miss the most likely duplication).
- A8.2 The resolver seam is one function with one caller-facing signature, and the contract
  test is **"audit-filled equals derived"**: on a sample of ≥ 20 historical records and on
  this release's own bugs, the value pillar 1 wrote into `resolved_commit` equals what the
  resolver derives from git. A record that has not been audited carries `null` and that is
  correct, not a failure.
- A8.3 **Zero** new blocking validation: **`dadaia bugs append`** exit codes are unchanged for
  every input that succeeds today, proven by the existing CLI-output-stability fixtures staying
  green untouched; the same holds for `bugs update`/`bugs archive` if AS-16(i) is chosen. *(Fold
  3, contradiction 5: the first Draft named `dadaia bugs resolve`, **a verb that does not
  exist** — `cli/commands/bugs.py` registers `append`, `status` and `stats`, and the
  `--event resolved` route dies with the event kinds. That absence is exactly what AS-16
  exists to close, so the corrected wording names the verbs that will exist.)*
- A8.4 This release's own commits obey the shapes; FR16's pillar-2 dry run reads them and
  reports conformance (a self-check the release must pass on its own history).

#### FR9 — Hooks de-slopped to the publication boundary · **size M**

*Entry: `bug-lineage-and-commit-discipline` (D) · ruling D9 · the clearest deletion in the
release.*

- `pre-commit-presence-gate.sh` becomes **advisory-only** (presence WARN, always exit 0).
  **Only in this script** are the `backlog doctor` BLOCK and the fail-closed runner
  resolution deleted; `cli/commands/ci.py#pre_commit_check` drops `_run_backlog_doctor_gate`
  and `_staged_backlog_paths` (the CI `backlog-doctor` job already covers the sweep,
  unscoped).
- `pre-push-ci-gate.sh` keeps **only** the publication boundary: branch-name policy +
  range-scoped denylist scan — **and it keeps its fail-closed runner resolution** (exit 1
  with its message when the runner cannot be resolved; never a silent skip). The two scripts
  share the same `resolve_runner` text, and D9 attaches the deletion to the *pre-commit*
  bullet; a fail-open pre-push runner would mean a machine without the venv pushing with **no
  branch policy and no denylist scan**, silently — the exact boundary D9 preserves. Only
  pre-commit may become unconditionally exit 0. The `dadaia ci preflight --quick` invocation
  **leaves the hook** and becomes the always-on rule *"run `dadaia ci preflight` before you
  push"* in `DADAIA.md` §7 + `dd-gitflow-default` + `dd-release-implement`; the audit
  measures pushes whose CI went red for preflight-class failures.
- The security-verdict CI gate on PRs is **untouched** — it *is* the publication boundary.
- **The secret-scan lane's coverage is stated, not extended.** `.github/workflows/
  secret-scan.yml` triggers on `push: main`/`hotfix/v*` and `pull_request: [main]`; `hotfix/*`
  is retired and `main` is never pushed directly, so gitleaks effectively runs **once per
  release, on the ship PR**. The 490 migrated records and the first audit folder therefore
  reach `develop` at `rc-1` covered by the **privacy denylist scan only**, which is not a
  secret scanner. FR9's acceptance records this limit explicitly so "publication boundary
  intact" is never read as "secrets scanned at `rc-1`". Extending the trigger is **not** done
  here: it is new CI surface on a LOW finding, and the honest statement is the cheaper and
  more truthful fix. It is compiled as an intake candidate at closure.

**Bug-surface direction, with numbers (fold 3, K):** **net-negative, unambiguously, −≈60
LOC.** Two blocking mechanisms and one fail-closed runner invocation are deleted; nothing
replaces them in code. Measured: **git-hook hard-exit scripts 2 → 1**; **hook blocks a human
can hit 2 → 0**; `cli/commands/ci.py` **455 → ≈395 lines**; hand-kept constants **−1**
(`_staged_backlog_paths`' path set); V10 negative.
**Tests: +3 added / −2 deleted (named, verdict pre-committed).** Added: pre-commit-exits-0-on-a
-rejected-stage (1), failing-preflight-no-longer-blocks (1), unresolvable-runner-still-refuses
(1). **Deleted — `qa-engineer` amendment 4, verdict stated now rather than deferred:**
`tests/integration/test_precommit_backlog_scoping.py` (imports `_run_backlog_doctor_gate`;
would fail to import) **and** `tests/e2e/features/test_backlog_precommit.py` (**a LARGE-tier
file whose entire premise — pre-commit *blocking* a bad stage — is deleted by this FR**).
Rewriting either would be a change-detector test of the new advisory behaviour, the class
`dadaia-test-stewardship` §B prohibits; the three new contract fixtures above **are** their
replacement, at a cheaper tier, cited in the commit message per the stewardship separation of
powers. This is the release's **one LARGE-tier removal with no replacement at that tier**.
**Bug-history evidence:** `precommit-backlog-doctor-blocks-unrelated-commits` is registered in
the ledger; the block stopped human commits on a shared tree and pushed agents into
`--no-verify` and other worse workarounds — a gate that *causes* the behaviour it exists to
prevent. It is also redundant: CI already runs `backlog doctor`.

**Acceptance**
- A9.1 A contract test asserts `pre-commit` exits **0 on any staged set**, including a staged
  set that `backlog doctor` would reject — the executed path, not the script's text.
- A9.2 `pre-push` refuses exactly **three** things and nothing else — an invalid branch name,
  a denylist hit, and **an unresolvable runner** — proven by a fixture for each, plus a
  fixture proving a *failing preflight no longer blocks the push*. The runner fixture asserts
  the push is **refused**, not skipped.
- A9.3 `_run_backlog_doctor_gate` and `_staged_backlog_paths` are **deleted** (grep zero-hit
  recorded), not left dead. Their two direct exercisers —
  `tests/integration/test_precommit_backlog_scoping.py` (which imports
  `_run_backlog_doctor_gate` and would fail to import) and its E2E companion
  `tests/e2e/features/test_backlog_precommit.py` — are **DELETED**, under a recorded
  `qa-engineer` verdict whose evidence is the three replacement contract fixtures at
  `file:line` and the argument that the E2E's premise no longer exists. *(Fold 3, `qa-engineer`
  amendment 4: the first Draft left "delete or rewrite" open at task time; an open verdict on a
  test whose subject is deleted resolves toward "rewrite" by default, which is how a
  change-detector enters a suite.)* The implementer neither deletes nor skips them to go green:
  the verdict is `qa-engineer`'s and the execution is `software-engineer`'s, as always.
- A9.6 The secret-scan coverage limit above is recorded in the segment's QA artifact as a
  known, accepted gap with its intake candidate, not as a passed check.
- A9.4 The preflight rule exists in `DADAIA.md` §7 (landed by FR11) and in
  `dd-gitflow-default`; the CI job that would catch its absence is named in both.
- A9.5 Net LOC for this FR is **negative**, measured (V10).

#### FR10 — `behavior-map.json`: every skill and every scoped `AGENTS.md` maps to one `DADAIA.md` section · **size L**

*Entry: `entity-behavior-map` (amended) · ruling D14.*

`dadaia_workspace/public/entities/behavior-map.json` is the **superset** of
`rules-skills-map.json`, adding the scoped-`AGENTS.md` column and a completeness requirement.
One row per **core skill** under `dadaia_workspace/public/skills/` and per **scoped
`AGENTS.md`**, each mapped to **exactly one** `DADAIA.md` section, with a recorded hash tuple.

**Discovery is structural, never a hand-written roster.** The enforcer **globs the generators**
— every `AGENTS.md` and `*-AGENTS.md` source under
`dadaia_workspace/public/{data,scaffold,templates}/` — exactly as it already globs
`public/skills/*/SKILL.md`. A hand list is the defect D14 exists to catch, and this SPEC's own
first Draft proved it by omitting three sources that ship today:
`public/data/dadaia-AGENTS.md` (→ `.dadaia/AGENTS.md`), `public/data/states-AGENTS.md` (→
`.dadaia/states/AGENTS.md`) and `public/data/tmp-AGENTS.md` (→ `.dadaia/tmp/AGENTS.md`). For
orientation only, the corpus at authoring time is: the scaffolded `specs/AGENTS.md`,
`backlog/`, `bugs/`, `releases/`, `memory/`, `audits/`, `ADRs/`; the library's
`public/data/{dadaia,states,tmp,reports,handoff,memory}-AGENTS.md`; `tests/AGENTS.md`; and the
`repos/<slug>/AGENTS.md` template. **That list is illustrative; the glob is authoritative**,
and a source added tomorrow goes RED without anyone editing this SPEC.

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

**Bug-surface direction, with numbers (fold 3, K):** *net-neutral in tests, net-negative in
unmapped surface.* The existing enforcer is **extended**, not duplicated: one map file, one
enforcer module. A second map would be the puxadinho; `rules-skills-map.json` therefore retires
into `behavior-map.json` rather than living beside it. Measured — **the release's cleanest
gain**: map coverage **5 rows over 25 members (16 %) → 31 members (22 skills + 9 scoped
`AGENTS.md`) at 100 %, RED in five directions**; entity map files **2 → 1**; entity schemas
**1 → 1**.
**Tests: +5 added / −9 deleted (named).** Added: the five mutation fixtures, one per RED
condition. Deleted: `tests/contract/test_rules_skills_map.py` **whole-file, nine checks**,
proven ported by A10.6's name-diff with a zero-hit residue — a **rename-and-extend, not a
duplication**, which is why the count is roughly flat rather than additive.
**The five new fixtures carry a cross-platform obligation (fold 3, `qa-engineer` amendment
6).** The file being retired is the home of two registered bugs —
`citation-enforcer-resolves-projected-instance-paths-against-the-checkout` and
`citation-mutation-fixtures-never-turn-red-on-windows` — and the second is precisely *a
mutation fixture that never turned RED on Windows*. Replacing that file with **five new
mutation fixtures** re-creates the shape class unless the RED direction is proven on every
platform: each of the five is therefore **run on the cross-platform CI matrix and observed RED
before its correction and green after**, on the matrix, **before `S2` closes** — with both bug
ids cited by id in T-050-19's done criterion, the same discipline A16.2 demands of the audit.
"Watched" is not enough for a shape that has already fired.
**Bug-history evidence:** the AI surface's recurring class is the **stale citation** —
`dadaia-task-manager-stale-workspace-protocol-citation` (cites §1 for content at §3) and the
v0.4.5 FR14 `ai-engineer.md` citation (cites §5 for content at §8), both found by humans, both
inside `public/**`. A hash tuple that goes RED when either end moves is the structural answer
to a class that has now fired twice.

**Acceptance**
- A10.1 **Cardinality, as D14 actually states it.** Every skill on disk and every scoped
  `AGENTS.md` on disk has **exactly one** row (a member maps to one section); every
  `DADAIA.md` section has **at least one** owner row. D14 goes RED when a section has *no*
  owner — not when two skills share one. Demanding exactly one owner per section would go RED
  on the map's own existing rows, where more than one skill legitimately owns §7 Quality. The
  enforcer proves both directions with those two cardinalities.
- A10.2 Five mutation fixtures, one per RED condition, each proven to fail before and pass
  after the corresponding correction.
- A10.3 `rules-skills-map.json` retires; **one** map file exists at the end, proven by a
  zero-hit grep for the old filename outside `_archive`/history.
- A10.4 Re-recording a hash tuple is a deliberate act with a named reviewer — the test message
  says what to re-read, not just that a hash changed.
- A10.5 The map adds **no** runtime dependency: no CLI verb reads it, no hook loads it (D15) —
  it is consumed by the test suite and by agents.
- A10.6 **No hard-won regression is lost on the retirement.** `test_rules_skills_map.py`
  carries **nine** checks at HEAD — the schema check, the six original map modes, the FR27
  citation checks and the FR28 bidirectional model-invocation grant check — two of which
  carry their own registered bug histories
  (`citation-enforcer-resolves-projected-instance-paths-against-the-checkout`,
  `citation-mutation-fixtures-never-turn-red-on-windows`). Before the old file is deleted,
  **every test function present in it at HEAD has a named counterpart in
  `test_behavior_map.py`**, proven by a **name-diff with a zero-hit residue** plus a one-line
  note per check recording the behaviour it still asserts. Byte-for-byte equality is not the
  criterion and would be unachievable in an extended enforcer; *no behaviour dropped* is.
  Three further files reference `rules_skills_map` / `rules-skills-map.json` and are repointed
  in the same task, named explicitly: `tests/helpers/scan_population.py`,
  `tests/contract/test_frozen_clock_aging_ratchet.py`,
  `tests/contract/test_public_scripts_thin_wrapper.py`.

#### FR10A — public-assets: the hand rosters retire with the glob · **size S**

*New at fold 3 — `software-architect` change 7, second half; the one public-assets recurrence
engine that qualifies for a bounded FR (§1.6, AS-17).*

FR10 makes skill and scoped-`AGENTS.md` discovery **structural** — the enforcer globs the
generators. That single-sources the roster class **only if the hand rosters it makes redundant
are actually deleted**; left in place they keep drifting, and this release gives them ten fresh
chances to drift (ten projection cycles, one skill renamed, one added, five scoped `AGENTS.md`
authored).

**Scope, bounded and deletion-only:** every `EXPECTED_SKILLS`-style hand-kept roster or
manifest tuple under `tests/` whose membership FR10's glob now derives is **deleted** and its
assertion repointed at the glob. The exact file list is **produced by measurement at task
time** — `grep -rn "EXPECTED_SKILLS\|SKILL_ROSTER\|frozenset({" tests/` restricted to
skill/persona/`AGENTS.md` membership — and recorded in the task, because a hand list of hand
lists is the same defect one level up. **Zero new checks** are written: the existing assertions
keep their subject and lose their literal.

**Explicitly out of scope, and deferred by name — AS-17:** the doctor goldens,
`shipped-hashes.json`, and the two projection authorities. Each lives in
`infrastructure/public_assets.py` (1 048 LOC, `#doctor` at CC 40) and each replacement is a new
derivation rather than a deletion.

**Bug-surface direction, with numbers:** **net-negative, deletion-only.** Hand-kept truth
constants **−N** where N is the measured roster count (forensic P1: hand-kept lists are **16 of
the last 100 bugs**; the roster sub-family is **4** —
`skill-orphans-unwired-agent-frontmatter`, `test-public-assets-stale-grill-me-name`,
`test-public-pipeline-stale-skill-roster`, `skill-orphan-checker-misses-disable-model-invocation`).
Production LOC **±0** — this FR touches `tests/` only. public-assets recurrence engines retired
**1 of 4**; the other three carry AS-17's stated deferral and intake target.
**Bug-history evidence:** the four bugs above are one class — *"a roster a human must remember
to extend"* — and three of them were fixed by extending the roster. FR10's glob is the
structural replacement; this FR is the deletion that makes the replacement real.
**Tests: +0 added / −0 deleted; N literals removed.** No test function is added or removed —
assertions are repointed. Any assertion that cannot be repointed because its subject is genuinely
hand-curated is **kept, with its reason recorded in the task**, never deleted to make a number.

**Acceptance**
- A10A.1 The roster inventory is **measured, listed in the task, and each entry dispositioned**
  (repointed / kept-with-reason); zero entries are left undispositioned.
- A10A.2 A zero-hit grep records that no deleted roster literal survives; the repointed
  assertions are green and go RED when a skill is added without a `behavior-map.json` row
  (proven by reusing one of FR10's five mutation fixtures — no sixth fixture is written).
- A10A.3 `dadaia public doctor` green; the diff touches **no** file under
  `dadaia_workspace/infrastructure/` (that is AS-17's territory, and staying out of it is the
  bound).
- A10A.4 The three deferred engines are named in the closure record's intake candidates with
  their bug ids (AS-17) — a deferral without its target is how four of the eighteen happened.

#### FR11 — `DADAIA.md`: anchors, the D15 posture, and the three short sections · **size M**

*Entry: `entity-behavior-map` (single owner of the `DADAIA.md` write, BL-CONFLICT adjudication
2026-08-26) · ruling D15.*

`dadaia_workspace/public/data/DADAIA.md` (source only — the projected law is PROTECTED) gains
stable per-behavior anchors for the map to point at (Backlog / Bugs / Releases / Memory /
Audits / ADRs). **The anchors are zero-cost comment markup — `<!-- behavior: bugs -->` — never
titled subsections.** Six to eight new headings would themselves read as prose to every agent
that loads the file every session, and would materially change V12's delta; a comment marker
is invisible to a reading agent and near-free in tokens while being exactly as greppable for
the enforcer. On top of the anchors:

- **the enforcement-posture section (D15), verbatim in intent:** *"Skills instruct procedure.
  Audits measure conformance from git and JSONL history. Hooks and the CLI validate only at
  the publication boundary (push / PR) and never block a human."*
- **the short bug-lineage + commit-shape section** specified by FR7/FR8;
- **the short audits section** specified by FR13/FR14;
- **the short memory two-tier + ADR section** specified by FR17/FR19 (*"memory Part 1 is
  ADR-gated and measured; only the operator accepts an ADR"*);
- **the always-on preflight rule** from FR9;
- **one rewritten row in `DADAIA.md` §3's path-class table.** The ADDITIVE row today reads
  "Always writable — register bugs freely, in any mode", which was written when every write
  to `specs/bugs/` was an append. With a mutable-field record it becomes: *"Always writable;
  the record contract — immutable core, write-once, mutable governance — is **audited, not
  gated**."* No new path class, no second classifier, one row of text (SA-2/A-7).

**Bug-surface direction, with numbers and a ceiling (fold 3, K + I):** *net-additive in
always-on tokens, bounded.* Every section added here is a pointer, never a restatement, and the
FR reports the token delta with per-section attribution (V12). **The measurement is no longer
the whole control — there is a number.** Baseline **21 511** always-on tokens (law chain 3 692
· 9 personas 16 344 · 21 skill descriptions 1 475, `architecture-metrics-baseline.md` §7).

| Addition | Budget (tokens) |
|---|---|
| D15 enforcement-posture section | ≤ 90 |
| bug-lineage + commit-shape section | ≤ 130 |
| audits section | ≤ 110 |
| memory two-tier + ADR section | ≤ 110 |
| always-on preflight rule | ≤ 50 |
| §3 ADDITIVE-row rewrite | ≤ 10 net |
| behaviour anchors (comment markup, **counted separately**) | ≤ 60 |
| removed — the `ACTIVE.md` sentence | ≈ −15 |
| **Ceiling on the always-on set** | **+500 ⇒ ≤ 22 011 (+2.3 %)** |

**A ceiling is not a target and an overshoot is not renegotiated.** If V12 measures above
22 011, FR11 **cuts text** until it does not; re-measuring, averaging across the persona set,
or moving a section into a skill that the law then has to cite are all refused. Anchors are
comment markup (`<!-- behavior: bugs -->`) and are attributed on their own line so they can
never hide inside a section's number (A11.1). The v0.4.4 always-on target (≤ 3.5 k) was missed
by ~6× and v0.4.5 was still dieting the same file this month: a governance release is exactly
the shape that spends those gains silently.
**Tests: +0 added / −0 deleted.** FR11 is authored text plus a measurement; its acceptances are
V12, the duplicate scan and `public doctor`.
**Bug-history evidence:** the always-on budget missed its A21.9 target in v0.4.4 (~8.2k vs
≤3.5k) and was still being cut in v0.4.5 FR11. A governance release is exactly the kind that
grows the law file; naming the risk and measuring it is the mitigation.

**Acceptance**
- A11.1 **The Tier-1 single-writer property holds, and it is proven mechanically.** Exactly
  one task in `TASKS.md` contains `dadaia_workspace/public/data/DADAIA.md` in its write set
  (T-050-20), and the same holds for the other three Tier-1 files of D-B — proven by a grep
  over the write-set blocks, not by "inspection of §3". Anchors are comment-form markers, and
  **V12's attribution table separates anchor cost from section-body cost** so an anchor can
  never hide inside a section's number.
- A11.2 Each new section is ≤ the size the map row needs to point at it, and states no
  procedure that a skill already states — proven by the FR8/A8.1 duplicate scan.
- A11.3 The always-on token count is measured before and after (V12); an increase is reported
  with its per-section attribution, never averaged away, and **stays at or under the +500
  ceiling (≤ 22 011 total)**. An overshoot is closed by cutting text, in this task, before the
  segment closes (fold 3, I).
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
  `RC-FLOW.md` (the state ladder, absorbing `CLOSURE-CHECKS.md`, and **carrying forward the
  operative `dd-architecture-survey` pointer** the `entity-behavior-map` entry requires — a
  pointer dropped in a rebuild is a law relocated into nothing), `RELEASE-EVENTS.md` (the
  `RELEASE.jsonl` append recipes per milestone, including the sha-bearing ones and the
  `implemented`-at-QA-close rule), `MEMORY-UPDATE.md`. `CLOSURE-TEMPLATE.md` dies with
  `CLOSURE.md`.
- `dd-backlog-definition` rewritten for the live-photo `BACKLOG.md` + histo JSONL; its "no
  JSONL for backlog" clause retires.
- `dd-bug-registration` and `dd-release-definition` updated to the v6 record fields and the
  `RELEASE.jsonl` flow.
- The scoped `AGENTS.md` files (`specs/`, `backlog/`, `bugs/`, `releases/`, `memory/`,
  `audits/`, `ADRs/`) are authored short and direct, hash-projected under the TREE-5 regime.

**Bug-surface direction, with numbers (fold 3, K):** **net-negative in AI-surface lines**,
measured (V11); **zero** production LOC. Two files die (`CLOSURE-TEMPLATE.md`,
`CLOSURE-CHECKS.md` folded), one skill is renamed rather than duplicated, and procedure moves
out of prose into pointers. Measured file counts, stated so V11's *line* claim is read against
them rather than instead of them: skill siblings **+3 here** (`RC-FLOW.md`,
`RELEASE-EVENTS.md`, `MEMORY-UPDATE.md`) **−2** (`CLOSURE-TEMPLATE.md`, `CLOSURE-CHECKS.md`);
scoped `AGENTS.md` shipped by the library **4 → 9**; skills **22 → 22** (the rename is not an
addition). **File count rises while line count falls — both are reported** (V11 + the file
table), because a release that reports only the falling one is doing what this release exists
to stop.
**Tests: +0 added / −0 deleted.** Skill and scoped-law authoring; the enforcer that covers it
is FR10's, already counted.
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
`README.md` (scoped law + the index of audits). The HTML report/handoff remains the
operator-facing emission (`DADAIA.md` §5) but is **derived from**, never a substitute for,
the committed folder.

**The `project-auditor` write allowlist, decided explicitly (S-8).** Pillar 1 must write
`audited` (and, per AS-1, `resolved_commit`) onto bug records, which the first Draft
simultaneously forbade — a contradiction that the gate would have resolved silently toward
the wider access, since `specs/bugs/` is ADDITIVE and refuses nobody. The decision:

- The allowlist is **`specs/audits/**` plus `specs/bugs/BUGS.jsonl`** — the latter for
  **governance fields only**, written **through the FR2 record-store seam** so the write is
  redacted (A2.6) and atomic (A2.9). One writer seam, one code path; the auditor still never
  writes a core field, never writes a fix, and never writes anything else under `specs/`.
- **A13.2 is retargeted at a property that actually holds.** "A write elsewhere under
  `specs/` is refused" is unfulfillable as stated: `write_allowlist` is parsed at
  **projection** time and is documentation, not a write-time control, and nothing refuses a
  persona's write to an ADDITIVE path. What *is* mechanically true is that
  `specs/audits/_archive/` is **FROZEN** (matched before ADDITIVE) and stays FROZEN for the
  auditor — the archive move is a `git mv`, outside the file-tool envelope. The fixture
  proves that.

Immutable finding fields: `id` (`<audit-slug>-F<nnn>`), `pillar` (`bugs|specs|memory`),
`severity`, `refs` (file:line, bug ids, commit shas, release ids), `claim` (one sentence),
`evidence` (**the reproducible command + a redacted one-line result** — A13.5; a
`.dadaia/tmp/**` path may accompany it, never replace it). Mutable governance:
`disposition` (`open|fixed|superseded|deferred|rejected`), `release`, `reason`. As appended,
then the same line after the remediation release:

```json
{"id":"20261020-five-release-window-F003","pillar":"bugs","severity":"HIGH","refs":["certify-skip-detail-leaks-full-codex-output","codex-live-probe-gate-checks-presence-not-usability","<sha-B>","<sha-A>"],"claim":"fix-induced bug: the skip-detail leak rides the second render path the probe-gate fix introduced, and the probe-gate bug resolved without a structural cause","evidence":"git show <sha-A> -- dadaia_workspace/features/certification (second render path added); BUGS.jsonl codex-live-probe-gate-checks-presence-not-usability cause=null","disposition":"open","release":null,"reason":null}
```

The **same record** after its remediation release — the three governance fields rewritten in
place, every immutable field byte-identical (a valid JSON line, so it can seed a fixture for
a schema with `additionalProperties: false`):

```json
{"id":"20261020-five-release-window-F003","pillar":"bugs","severity":"HIGH","refs":["certify-skip-detail-leaks-full-codex-output","codex-live-probe-gate-checks-presence-not-usability","<sha-B>","<sha-A>"],"claim":"fix-induced bug: the skip-detail leak rides the second render path the probe-gate fix introduced, and the probe-gate bug resolved without a structural cause","evidence":"git show <sha-A> -- dadaia_workspace/features/certification (second render path added); BUGS.jsonl codex-live-probe-gate-checks-presence-not-usability cause=null","disposition":"fixed","release":"<the remediation release id>","reason":"one render path; regression test at the formatter seam"}
```

**Bug-surface direction, with numbers (fold 3, K):** *net-additive, +≈80 LOC*, justified: it
replaces an HTML artifact outside `specs/` that no tool could read with a committed record that
three tools read. `README.md` retires. Measured: public schemas **6 → 8** across the release
(−`bug-event-v1`, +`bug-record-v1`, +`finding-record-v1`, +`release-event-v1`); scaffold
`README.md` **4 → 0** (one of them here); store **implementations 1**, instances **= callers**
(A13.4).
**Tests: +3 added / −0 deleted.** The finding-schema fixture seeded from the valid-JSON example
(1), the FROZEN-for-auditor fixture (1), and A13.6's four persona-allowlist assertions folded
into **one** parametrized function (1) — parametrization over four copies is the DAMP/count
trade the literature names, and the count is the honest one.
**Bug-history evidence:** the audit lane's own failure history — `specs/audits/README.md`
documents a convention no tool honours, and the persona is *forbidden* to write the folder its
own README describes. A documented convention with no writer is how drift starts.

**Acceptance**
- A13.1 The finding schema exists with `additionalProperties: false` and the
  immutable/mutable split documented per property.
- A13.2 `project-auditor`'s allowlist gains exactly `specs/audits/**` and
  `specs/bugs/BUGS.jsonl` (governance fields, through the FR2 seam) and nothing else. The
  **fixture proves what is mechanically true**: `specs/audits/_archive/` is FROZEN and a
  file-tool write there is refused for this persona as for every other; the allowlist itself
  is projection-time documentation, and the SPEC says so rather than implying a control that
  does not exist.
- A13.3 `specs/audits/README.md` is deleted and its content lives in `audits/AGENTS.md`.
- A13.4 **A store instance exists only where a writer exists** (fold 3,
  `software-architect` §6 — the third architecture-fidelity finding). A finding's governance
  fields are rewritten in place leaving every other byte identical, and the **generic
  `JsonlRecordStore`** of A2.5 is the seam **wherever code writes**. The first Draft mandated
  "three models, three container registrations" while the auditor and the remediation closure
  both write `FINDINGS.jsonl` with **file tools** (D15/A14.5: no CLI verb) — a registration
  with no caller is dead code behind a protocol, the FR15 shape applied to
  `infrastructure/`. The acceptance is therefore: **one store module, three models, and
  exactly as many container registrations as have a caller — proven by a grep that shows a
  call site for each**, with the findings model registered **only if** FR15's fold or another
  consumer actually resolves it. `FINDINGS.jsonl`'s file-tool writer class is stated
  explicitly (as `RELEASE.jsonl`'s is, FR4) rather than implied by a seam nobody calls, and
  A13.5's hand-redaction rule is what covers it. **No module knows two record shapes.**
- A13.6 **The reviewer personas may write the artifacts the law requires of them.** Four
  reviewer personas gain `specs/releases/**/reviews/**` and `security-reviewer` additionally
  `specs/releases/**/verdicts/**` (T-050-03A), each with a fixture proving the parsed allowlist
  admits its declared globs and refuses `specs/memory/**`. *(Fold 3, traceability gap 3:
  T-050-03A carried no FR or acceptance id. It belongs to FR13 — "a persona forbidden to write
  the artifact its own law requires" is exactly the defect FR13 fixes for `project-auditor`,
  and the same honest posture applies: `write_allowlist` is projection-time documentation, not
  a write-time control.)*
- A13.5 **The audit folder is scanned by the push detector before it is trusted, and every
  `evidence` value is self-contained.** Before the `S3` QA close, the folder is run through
  the same detector a push uses (`dadaia ci push-gate-check` over the range, or a
  `specs doctor` WARN reusing `features/chokepoints/denylist_scan`), zero hits recorded.
  A finding's `evidence` is **the reproducible command plus a redacted one-line result** —
  e.g. `git show <sha> --stat -- <module> → 2 files changed, second render path added` — so
  the remediation release that reads the finding can re-run it and see the same thing. A
  `.dadaia/tmp/**` capture is a **convenience pointer, never the sole citation**: that lane
  is GC'd at three days (CR-11), so a path-only `evidence` decays into an unverifiable claim
  — the fabricated-evidence shape this release exists to end. The one-line result is written
  redacted **by hand** because the auditor writes with file tools and no seam can redact for
  it: pillar-3 runs (`lint-imports`, `pytest`, ratchet checks) emit runner-absolute paths
  routinely, so a transcript is never pasted, only its one-line conclusion. The same rule
  binds FR3's migration report.

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
  `git log --format` + `--stat`). It consumes only `resolution_granularity == "exact"` shas
  as diff-able lineage and records the rest as coarse (D-A).

  Three further measures, each cheap and each answering a documented chain:
  - **Registration→resolution interval.** A resolution whose interval from registration is
    implausibly short is the no-red-loop signature: the ledger shows
    `certify-cannot-install-installed-provider` reported 18:41:56Z and resolved 18:41:57Z —
    one second, a bulk flip of an already-"fixed" bug. Detecting the certify class becomes
    arithmetic instead of judgement.
  - **Core-field mutation.** A hunk in `git log -p -- specs/bugs/BUGS.jsonl` that changes an
    **immutable core field** of an existing `id` is a **HIGH** finding. This is the detector
    that makes A2.2's seam-level rule auditable, since nothing prevents a file-tool rewrite.
  - **Cache disagreement.** A stored `resolved_commit` that disagrees with the derivation is
    a finding (A8.2).

  **Pillar 1 measures all eight forensic metrics — the release's stated purpose, made
  checkable (fold 3, `software-architect` change 6 / directive F).** The first Draft measured
  six things the forensic did not ask for and **two of the eight** it did, both partially:
  A16.2 would then have passed on the four pinned chains (findable by
  `caused_by: "text-reference"` alone) while the loop's **aggregate rate stayed unmeasured**.
  `PILLAR-BUGS.md` carries this table verbatim, and **each row is a validation (V33)**:

  | # | Metric | Definition / command | Baseline | Carried by |
  |---|---|---|---|---|
  | 1 | **Per-bug diff attributability** | share of resolutions whose first-adding commit adds exactly one resolved record and touches a non-`specs/` path — i.e. `resolution_granularity == "exact"` | **26/92 = 28 %** | `resolution_granularity`; **target 100 % on post-0.5.0 resolutions** |
  | 2 | **FR23 triple coverage** | resolved records with `evidence_loop` + `evidence_seam` + `evidence_diff` all present | **23/92 = 25 %** | the restored triple (FR2); target 100 % post-0.5.0 |
  | 3 | **Fix-shape ratio** | `net-negative / (net-neutral + net-positive)` from the `diff_direction` enum | **21/31 = 0.68** | `diff_direction` (FR2) — the token the free text already carried |
  | 4 | **Same-surface re-bug rate** at 3 d / 14 d | grouped on the **`surface` enum**, not free text (86 distinct strings per 100 bugs before) | **55 % / 73 %** | the `surface` enum (FR2) |
  | 5 | **Hand-kept-list touch count** | resolving commits whose `git show --name-only` touches `.gitignore`, `privacy_baseline.json`, `shipped-hashes.json`, `*_golden/*.json`, a skill roster, or a `frozenset({…})` literal | **16/83** | a fixed path set in `PILLAR-BUGS.md`; FR10A moves it |
  | 6 | **Test-layer bug share** | records whose `surface == "tests"` or whose `component` starts with `tests/` | **21/100** | the `surface` enum |
  | 7 | **Scanner-vs-prose recurrence** | records whose `symptom` matches `self-scan\|denylist\|privacy` **and** whose fix touches only `specs/**/*.md` or `tests/` | **10/100**, **target 0** | reported honestly: this release **grows** scanned prose (4 QA closes, 3 reviews, `specs/audits/**`, the migration report, 5 `AGENTS.md`) and moves no prose out of the scanned tree — the metric exists so the growth is counted rather than discovered |
  | 8 | **Sweep closures as `resolved`** | terminal records whose evidence matches `^Need met\|re-affirmation` with no code-touching commit | **9/92**, **target 0** | FR2's one-sentence rule: a sweep is `superseded`, never `resolved` |

  Metrics 1–4 and 6 are computable **only because** FR2 restored the triple, added
  `diff_direction` and closed the `surface` enum — which is why those three record changes are
  not cosmetics but the release's measuring instrument.

  **Pillar 1 is the single writer of the derived cache.** On each record it reviews it writes
  `audited: <audit-slug>` **and** all four derived provenance fields —
  `registration_commit`, `registration_granularity`, `resolved_commit`,
  `resolution_granularity` — in **one atomic in-place rewrite**, through the FR2 record-store
  seam (redacted, atomic, re-read before write). *(Fold 3, traceability gap 5: the first Draft
  named a writer for the resolution sha and none for the registration sha on post-0.5.0
  records.)* One writer, one seam, one commit — this is what AS-1(ii) buys, and it is why FR8
  has no shape 3b.
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
audited release to the current one — the auditor scans every `RELEASE.jsonl` (the **live**
release and `releases/_archive/**`, plus `releases_histo.jsonl`) for the newest `audited`
milestone, takes `[that sha, HEAD]`, and appends an `audited` milestone at the end so the chain
never gaps. **`_ideas/` is not scanned** (fold 3, contradiction 4): D10/AS-7 make an `_ideas/`
release **SPEC-only**, so it carries no `RELEASE.jsonl` to fold, and scanning for a milestone
the canon forbids it to hold is a lookup that can only ever return nothing.

**Lifecycle.** One audit → exactly one remediation release that gives **every** finding a
disposition (`DADAIA.md` §6, unchanged); the release's closure rewrites each finding's
governance fields; the folder moves to `specs/audits/_archive/` only when no record is `open`.
**No new CLI verb**: the auditor writes the folder with its file tools (D15).

**Bug-surface direction, with numbers (fold 3, K):** *net-additive in AI-surface lines,
**zero** production LOC.* No CLI verb, no doctor rule is added by this FR; the six-dimension
HEAD comparison is **absorbed** into pillar 3 rather than kept beside it. Measured: skill
siblings **+4 / −2** (`RUBRIC.md`, `TOOLING.md` folded); CLI leaves **+0**; hook changes
**0**; forensic metrics measured **2 (partial) → 8**.
**Tests: +1 added / −0 deleted.** The one-atomic-rewrite-per-record fixture (A14.6). The eight
metrics are **procedure in a disclosed sibling**, executed by the auditor and evidenced by
FR16's artifact — deliberately **not** eight new test functions, which is what "audits measure,
hooks and the CLI do not" means in test-count terms (D15).
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
- A14.6 Pillar 1's write of `audited` + **all four provenance fields**
  (`registration_commit`, `registration_granularity`, `resolved_commit`,
  `resolution_granularity`) is **one** atomic in-place rewrite per record through the FR2 seam
  — proven by a fixture asserting a single file replacement per record and every other byte
  unchanged.
- A14.7 **Every one of the eight forensic metrics is computed, with its baseline and its
  target, and each appears in `AUDIT.md`** (**V33**). A pillar-1 run that reports fewer than
  eight is incomplete, not lenient — the release exists to make this loop measurable, and a
  metric named in §1 but absent from the artifact is the fabricated-evidence shape one level
  up. Metrics with target 0 (7, 8) report their measured value even when it is worse than
  baseline; metric 7 is expected to be **worse** and saying so is the acceptance.

#### FR15 — `specs doctor` folds `FINDINGS.jsonl` instead of parsing prose · **size S**

*Entry: `audit-canon-v1` (D).*

`doctor_closure_audit.py`'s `check_audit_disposition` / SPEC-DOC-036 / SPEC-DOC-038 stop
regexing prose: an `open` record inside an **archived** audit is an **error**; a live audit
whose records are all terminal with a named release is an **archive-due WARN**.

**Extended scope (A4.4): every `CLOSURE.md` parser retires here, not just the disposition
regexes.** FR4 deletes the file; a checker that parses a file which no longer exists is dead
code behind a dead artifact — the shape this release exists to stop. FR15 therefore also
deletes the remaining `CLOSURE.md` checks in `doctor_closure_audit.py`, `doctor_release.py`
and `doctor_governance.py`, plus `RELEASE_ARTIFACTS` in `doctor_common.py`, and the
`AUDIT_DIR_NAME_RE` duplication (the `<YYYYMMDD>-<slug>` shape gets a **single** home, also
replacing the comment that repeats it in `gate_policy.py`).

**Bug-surface direction, with numbers (fold 3, K):** **net-negative, −≈200 LOC** together with
T-050-25A. Regex-over-prose is deleted and replaced by a JSONL fold that reuses FR13's reader.
Measured: **regexes parsing release prose 22 → ≈9** (**−59 %**; the survivors are
`doctor_governance.py`'s six SPEC-DOC-031/032/033/035 SPEC/BACKLOG parsers and
`memory_lint.py`'s three, both out of scope and named as such); **doctor check codes −BL-DUP
and −4 CLOSURE-parsing SPEC-DOC codes**, landing the release at **≤ 45** from 47 — and V19
records the **post-release code list**, not just the count, so a silently kept code cannot hide
inside a total; hand-kept constants **−4** (`RELEASE_ARTIFACTS`, `AUDIT_DIR_NAME_RE`'s
duplicate, two disposition regexes).
**Tests: +2 added / −3 deleted (named).** Added: the archived-audit-with-an-`open`-record error
fixture (1) and the fully-terminal archive-due WARN fixture (1). Deleted with their subject
(fold 3, `qa-engineer` amendment 3 — the three files are named rather than hidden behind a
generic `tests/**`): `tests/unit/features/specs/test_doctor_taxonomy_disposition.py`,
`tests/unit/features/specs/test_doctor_golden.py`'s SPEC-DOC-036/038 cases and the
corresponding entries of the golden fixture `tests/unit/features/specs/_golden/
doctor_golden_v0155.json` — each with a per-file `qa-engineer` verdict. Regenerating the golden
by reflex is prohibited (`dadaia-test-stewardship` §B); the entries whose subject is deleted are
removed and the remainder is left untouched, which is the difference between curating a golden
and re-baselining one.
**Bug-history evidence:** SPEC-DOC-0xx rules that parse authored Markdown have repeatedly
produced both false positives and silent misses (the v0.1.73-era "gate never demands what the
tooling refuses" law came from this class). A structured fold cannot misread a sentence.

**Acceptance**
- A15.1 The regex path is **deleted**, not bypassed — zero-hit grep recorded, and a second
  zero-hit grep for `CLOSURE.md` across `dadaia_workspace/features/**` proves no parser
  survived its subject.
- A15.2 Two fixtures: an archived audit with one `open` record errors; a live fully-terminal
  audit warns `archive due`.
- A15.3 `dadaia specs doctor` reports **0 errors** on this repo after the migration.

#### FR16 — The first audit, run on this repository as a dry run · **size M**

*Entry: `audit-canon-v1` (proof of the canon) · **AS-10**.*

`project-auditor` runs the new protocol end to end over this repo, producing a real
`specs/audits/<YYYYMMDD>-canon-v6-first-audit/` folder with `AUDIT.md` + `FINDINGS.jsonl` and
appending the `audited` milestone. **It opens no remediation release**: the findings are
compiled for the PM's operator-facing intake report.

**Bug-surface direction, with numbers (fold 3, K):** *neutral in code, **0** production LOC* —
it produces data. Its value is that it makes the canon fail *here* rather than at a consumer.
It is also where the eight metrics acquire their first measured values against the baselines
in FR14's table.
**Tests: +0 added / −0 deleted.** An audit run is not a test.
**Bug-history evidence:** the workspace's own law — *"a green internal gate that diverges from
real consumer behavior is itself a bug"* (`DADAIA.md` §7). A canon that has never been run is
a green internal gate.

**Acceptance**
- A16.1 The folder exists, is committed, and carries all three pillars' sections.
- A16.2 Pillar 1 **names, with evidence, at least the four documented chains of §1.1, by the
  bug ids §1.1 pins** — the nine-instance gitignore class (≥ 3 of its ids), the certify
  chain (`codex-live-probe-gate-checks-presence-not-usability` →
  `certify-skip-detail-leaks-full-codex-output`), the frozen-clock chain
  (`no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock` →
  `frozen-clock-ratchet-scans-tests-tmp-scratch-dir`), and the bug-event ledger family
  (`bug-event-field-with-unicode-line-separator-silently-drops-the-event` plus the ESC
  escaping finding, cited by its review artifact since it carries no bug id). A finding that
  claims a chain without naming its pinned ids does **not** satisfy this acceptance — that is
  the whole point of pinning them. §1.5 is the worked shape each finding must take. A canon
  that cannot rediscover the loop it was built for is not accepted, and FR14 is reworked
  instead of the acceptance being lowered.
- A16.3 Pillar 2 reads **this release's own commits** and reports FR8 conformance (A8.4).
- A16.4 Pillar 3 executes every `Measured by:` check authored by FR18 and records each
  result; any principle whose check does not run is a finding against FR18, not a skipped row.
  **Because FR18 lands in `S4` and FR16 runs in `S3`, the pillar-3 half is completed at
  scope-complete** (fold 3, traceability gap 2): T-050-34 dispatches `project-auditor` to
  re-run pillar 3 against the now-authored Part-1 principles and **append** the resulting
  findings to the existing `FINDINGS.jsonl` (findings are appended once, so new findings take
  new ids — nothing is rewritten). Without this, A16.4 was an acceptance no task could
  discharge: the dry run recorded "principle not yet written" as a gap and nothing re-ran it.
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

**Bug-surface direction, with numbers (fold 3, K):** *net-neutral in LOC, net-negative in
ambiguity.* No new file; the existing three are restructured, and every rule that cannot name
its measure is **deleted from memory** (it was never true, only asserted). Measured: memory
files **3 → 3**; `memory_lint.py`'s hand-listed headings **85 → 87** — the two new Part
headings — and that **+2 is declared, not discovered**: `_HEADING_GROUP_*` is a P1 hand-kept
list (25/25/22/13 entries at `memory_lint.py:180/126/97/77`) that this FR **feeds** rather than
derives. Deriving the allowlist from the templates is out of scope here (it is a new
derivation, not a deletion) and is compiled as an intake candidate beside AS-17's three.
**Tests: +1 added / −0 deleted.** The two-top-level-parts file-shape contract test.
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

**A principle must be TRUE when it is accepted — the independence contract is completed
first (fold 3, `software-architect` change 8 / directive D).** The candidate principle *"features
are mutually independent"* is **measurably false at birth** as the contract stands. Measured on
this tree at this fold:

| Fact | Number |
|---|---|
| `dadaia_workspace/features/*/` packages carrying `__init__.py` (glob) | **24** |
| Packages listed in `[importlinter:contract:features-no-cross-feature]`'s `modules =` (`setup.cfg:177–197`) | **20** |
| Missing, named | **4** — `capabilities`, `certification`, `reconcile`, `tmp_gc` |
| Module-level cross-feature edges actually present | **5** |
| …declared as `ignore_imports` today | **2** (`specs.doctor_governance → backlog.document`, `chokepoints.service → spec_context`) |
| …**invisible** because their source package is unlisted | **3** — `features/reconcile/service.py:12,13,14` → `features.capabilities`, `features.migrate.legacy_dadaia_dirs`, `features.migrate.state_v2` |

*Two reviewer figures are corrected against the tree rather than transcribed: the review's
"20 of 25" and its fifth missing package `workspace_*` — `workspace` **and** `workspace_clean`
are both listed, the true gap is **four**, and the package inventory reads **24** by glob (the
metrics baseline's "25" counts one directory more than the importable packages). **The inventory
task re-counts from disk**, and this table is evidence, not an input.*

**The rule this FR follows:** T-050-29 **adds the four missing packages to `modules =`
before** the principle is promoted, then reports the contract's measured edge count. The three
reconcile edges are **declared `ignore_imports` with a reason line each**, and the cap moves by
exactly that count: `_RECORDED_IGNORE_EDGE_CAP` **15 → 17** — `15 − 1` (FR2 retires
`cli.commands.bugs → infrastructure.jsonl_bug_store`, `setup.cfg:232`) `+ 3` — with
`tests/contract/test_import_linter_ignore_cap.py` updated in the **same commit**, as its own
docstring requires. **Collapsing `reconcile`'s three edges is not attempted here** (it is a
feature rewrite, not an inventory step) and is compiled as an intake candidate. What is
refused is the third option: promoting *"features are mutually independent"* to an ADR-gated
principle while three edges are invisible to the check that is supposed to measure it — a
principle whose `Measured by:` line points at a contract that cannot see the violations is
exactly the decoration this segment exists to abolish.

**The `surface` enum shares this one source (FR2/A2.12).** The completed `modules =` list is
the same list the record schema's enum derives from, so a package added tomorrow goes RED in
one place.

**The A18.3 conflict, resolved explicitly (fold 3, directive H).** A18.3 says FR18 writes
**zero** new checks, and the test-suite ratchets of §3 (private-symbol imports, `Intent:`
coverage, SCAFFOLD expiry, one-number-per-parameter, pyramid shape) are new checks. They do
not collide, and the boundary is stated rather than assumed: **A18.3 governs *product* checks
— doctor rules, CI jobs, hook exits, anything that can fail a consumer's tree or block a
human.** The ratchets are **test-suite ratchets in `tests/contract/`**, one file
(`test_test_suite_ratchets.py`, T-050-18A), measuring **the suite itself**; they run in the
existing `pytest` job, add no CLI surface, no doctor code and no hook exit, and follow the
measure-then-pin-then-ratchet law `tests/contract/test_module_size_ceiling.py` and
`test_import_linter_ignore_cap.py` already use. FR18 still writes **none of them** — it
**promotes** them, exactly as it promotes the ceilings that already exist. A22.6's "zero new
blocking exits" is unaffected: a red contract test fails the suite, which is what every
contract test does.

**One number per parameter — the LARGE cap is reconciled here (fold 3, `qa-engineer`
amendment 7).** The census ceiling has **three homes and three values**:
`dadaia-test-stewardship/PARAMETERS.md:10` says **30** (with "current ~84"),
`tests/AGENTS.md:69–71` says **30**, and `specs/memory/quality-assurance.md:79,208` says the
census **is 100** and *that* is the ceiling. Promoting "the LARGE-test census ceiling" to a
Part-1 principle without picking one would promote a Sensitive-Equality smell **into the
constitution's own layer**. The decision: **`PARAMETERS.md`'s 30 is the number and its only
home**; `tests/AGENTS.md` and `QUALITY.md` **reference** it and their competing statements are
**deleted** (measured today: 42 functions under `tests/e2e/**`, 15 `e2e`-marked — so 30 is a
target above the measured count either way, and the remediation stays where
`PARAMETERS.md` already puts it). V29 scans for a second numeric cap and goes RED on one.

**Bug-surface direction, with numbers (fold 3, K):** *net-neutral in code, strictly
documentary* — **zero** new **product** check is written by this FR (the A18.3 boundary above).
If a rule has no existing check, it does not become a principle. Measured: import-linter
contracts **9 → 9**, their `modules =` coverage **20/24 → 24/24**, cross-feature edges visible
to the check **2 → 5** (three were invisible), `_RECORDED_IGNORE_EDGE_CAP` **15 → 17**, doctor
codes **+0**, CI jobs **+0**, CLI leaves **+0**.
**Tests: +1 added / −0 deleted.** The contract-count test (a tenth import-linter contract
without a principle goes RED), extended in the same file to assert `modules =` equals the
packages on disk (A18.5) — one function, not two.
**Bug-history evidence:** the frozen-clock chain shows what happens when a rule is enforced by
a guard nobody described: the guard grew, drifted and produced its own bug. Naming the check
in memory makes the guard's existence and purpose reviewable.

**Acceptance**
- A18.1 The inventory covers **every** `[importlinter:contract…]` section present in
  `setup.cfg` at implementation time, counted from the file (V13); a contract test asserts
  the counts agree, so adding a contract without a principle goes RED.
- A18.2 Every promoted principle's `Measured by:` command is executed once during `S4` and its
  output captured — a `Measured by:` that does not run is not admitted (V14).
- A18.3 **Zero** new **product** checks, doctor codes, CI jobs or hook exits are created by
  this FR, proven by the diff. The scope of this rule is stated above and is not open to
  reading: the test-suite ratchets of T-050-18A are `tests/contract/` measurements of the suite
  itself, promoted here and written there, and A22.6 is unaffected.
- A18.4 Every principle is traceable to exactly one ADR, and vice versa.
- A18.5 **The independence contract is true before it is promoted.** `modules =` lists **every**
  `dadaia_workspace/features/*/` package (24 at this fold, re-counted from disk at task time —
  the four missing ones named: `capabilities`, `certification`, `reconcile`, `tmp_gc`); the
  contract's measured cross-feature edge count is **reported** (5 today, of which 3 become
  declared ignores with a reason line each); `_RECORDED_IGNORE_EDGE_CAP` moves **15 → 17** in
  the same commit as `setup.cfg`, and a contract test asserts `modules =` equals the packages
  on disk so the next package cannot be silently unlisted (**V32**). Only then may
  *"features are mutually independent"* be authored as a `P-NN` and proposed as an ADR.
- A18.6 **One number per parameter.** The LARGE-test census cap lives **only** in
  `dadaia-test-stewardship/PARAMETERS.md` (value **30**); `tests/AGENTS.md` and
  `specs/memory/QUALITY.md` reference it and carry no competing number, proven by **V29**'s
  scan. The 100-census statement in memory is deleted, not reconciled by prose.

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

**Bug-surface direction, with numbers (fold 3, K):** *net-additive in documents, **0**
production LOC.* Measured: new spec area **1** (`specs/ADRs/`, already tracked by FR1's
`.gitignore` inversion — V21); doctor rules **+0**; CLI leaves **+0**; operator-only gates per
release **2 → 5** (+FR6's presence, +FR20's sitting, +AS-12's ratification) **plus one per
future ADR acceptance** — a governance cost imposed by D12/D-H/AS-12 and stated here rather
than discovered at the sitting.
**Tests: +1 added / −0 deleted.** The monotonic-numbering contract test.
**Bug-history evidence:** this workspace has reversed its own rulings repeatedly without a
record — the 2026-08-23 D5 "commits excluded" reversed by the 2026-08-26 D3; the 2026-08-23 D3
"event-sourced" replaced by D11; `hotfix/*` retired. Each reversal lived only in a handoff.
An ADR chain makes the reversal itself reviewable.

**Acceptance**
- A19.1 The folder, its `AGENTS.md` and the index exist; numbering is monotonic and a contract
  test refuses a reused number.
- A19.2 Every ADR authored by this release carries every field, including `Confirmation`.
- A19.3 A fixture proves the "accepted is immutable" rule is stated where an agent reads it
  before writing (the scoped `AGENTS.md`), and that pillar 3 detects **the pairing rule** —
  a Part-1 hunk in the window with no `accepted` ADR in the same commit is a HIGH finding.
  **Stated as the limitation it is:** pillar 3 cannot detect an *agent-written* `accepted`,
  because commit identity is shared across agents and the operator (the de-personalising
  question is still open, §7). Attribution is discipline; the pairing is the detector.
  Claiming otherwise would be exactly the fabricated-detection this release outlaws.
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

**Bug-surface direction, with numbers (fold 3, K):** **net-negative, measured** — the
restatement is deleted, not mirrored. Baseline `specs/constitution.md` **261 lines**; V15
reports the delta and it must be **negative**, with the coverage table accounting for every
removed clause. Duplicated rule text between the constitution and the memory trio: **→ 0**
(A21.3's scan).
**Tests: +0 added / −0 deleted.** Authored text; its acceptance is V15 and the duplicate scan.
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

**Tests: +5 added / −0 deleted (T-050-18A).** The five suite ratchets — **V26** private-symbol
imports, **V27** `Intent:` + size coverage, **V28** SCAFFOLD expiry, **V29**
one-number-per-parameter, **V30** pyramid shape — land as five test functions in the one
contract file `tests/contract/test_test_suite_ratchets.py`. They are counted **here** (fold 4,
§9.4): the suite's own ratchets are FR22's invariants, and until this fold they were the
release's only addition attributed to no FR, which made the per-FR roll-up understate itself
by 5 against the same gate (A22.9) it is supposed to sum to.

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
  and **zero** new hook blocks, and removes **exactly two blocks** — the pre-commit
  `backlog doctor` block and the pre-commit fail-closed runner (FR9 additionally moves the
  preflight invocation out of the pre-push hook, which is a third removal but not a third
  block). The pre-push fail-closed runner **survives** and its refusal is asserted (A9.2).
  Proven by a contract test over the hook scripts and by the CLI-output-stability fixtures.
- A22.7 Every picked entry is dispositioned; residuals — including all of FR16's findings —
  are compiled into the PM's intake report, never materialized by an agent.
- A22.8 **Every `rc` holds A22.1–A22.8**, and every `rc-N ≥ 2` traces to a defect or
  adjustment **on this scope**, named with where it was found on `develop`.
- A22.9 **The test suite is net non-positive** (fold 3, operator mandate; `qa-engineer`
  amendment 1). `pytest --collect-only -q` is captured **before** (T-050-03) and **after**
  (T-050-34), per tier, and the after-count of test **functions** is **≤ the before-count**
  (baseline **1 859** in 396 files, **2 873** collected items with parametrization; the
  T-050-03 re-measure is what binds). The per-FR `Tests: +N / −M` lines above sum to the
  claim; a divergence between the sum and the measurement is a defect of the accounting, not
  of the measurement. **The roll-up, as written at fold 4, is `+61 / −35 = +26`** — i.e. a
  paper after-count of **1 885 against a gate of 1 859**, with the **−26 shortfall named
  rather than implied**: the per-FR lines carry only the deletions inspection can prove today
  (including T-050-21A's **−3** census floor), and the remaining 26 come from the per-file
  verdicts on the mixed-subject census files and `qa-engineer`'s closure demotion map. The
  operator signs a declared overshoot with its number, never an arithmetic that hides one.
  **If the after-count exceeds the before-count, the release does not
  close on that number** — `qa-engineer` produces the demotion/deletion map that closes the
  gap, or the operator accepts the overshoot **explicitly, with the number in the closure
  record**. Silence is not acceptance.
- A22.10 **The suite's marking and structure ratchets hold** (**V26**–**V30**): private-symbol
  imports **24 → 0** (or a recorded number with its residue routed to intake), `Intent:` +
  size on **396/396** files (or a per-segment ratchet carrying its number), every `SCAFFOLD`
  carrying `expires: <M.m.p>` and none expired against an archived release, exactly one home
  for each numeric parameter, and the pyramid shape reported from `--collect-only`.
- A22.11 **The mutation floor on `core/` is a recorded number** (**V31**): one
  `tests/scripts/run_mutation_baseline.sh` pass over `core/` — the package taking the most new
  pure-function surface (`bug_provenance.py`, `release_events.py`, the record models) — with
  the score recorded as a floor that ratchets **up** only, and every zero-kill test outside a
  named `SENTINEL` entering the closure curation table with a disposition. **`mutmut`
  availability is verified, never assumed:** the fold-3 review could not reach a `mutmut`
  binary from its read-only session and reported that as **unverified, not absent**. If
  T-050-03 finds it unavailable, the floor is recorded as `null` **with the reason and an
  intake candidate** — a value nobody measured is never a default.
- A22.12 **The ruff complexity ceiling ratchets to reality** (**V35**, fold 3, directive J).
  `pyproject.toml`'s `max-complexity` is **63** while the measured maximum is **61**
  (`_list_agents_impl`, `features/telemetry/aggregator/queries.py:181`, untouched by this
  release) — a ceiling two above the code it governs is not a ratchet. At T-050-34 the observed
  maximum is re-measured with `radon cc` and the ceiling is set **to that number** (61 if
  nothing moved), never above; the change is recorded in the closure record's
  `## Size accounting`. Functions with CC > 10: **131 → ≤ 133**, with every new function above
  10 named.

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
9. **The three deferred public-assets engines** (AS-17) — doctor goldens,
   `shipped-hashes.json`, the two projection authorities — **the `specs upgrade` rename
   automation** (§1.6), **`reconcile`'s three cross-feature edges** (A18.5 declares and caps
   them; collapsing them is a feature rewrite), **`memory_lint.py`'s heading-allowlist
   derivation** (FR17), and **extending the `Intent:` gate beyond `tests/e2e/**`** (V27 measures
   and ratchets; extending `check_test_intent_declared.py`'s CI scope is a separate pick). Each
   is named with its bug ids or its number and routed to intake at closure — deferred **out
   loud**, never by omission.
10. **Any FR not listed in §3.** Nothing discovered mid-release is added without an operator
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
- **Test dispositions and the test-economy accounting (fold 3)** — every demotion, quarantine
  (with its bug id) and SCAFFOLD expiry, **plus the numbers**: V25's before/after per tier
  against A22.9's net-non-positive gate; the per-FR `Tests: +N / −M` roll-up and its agreement
  with the measurement; V26's private-import residue; V27's `Intent:` coverage; V30's pyramid
  shape and the e2e marker-vs-directory drift (42 vs 15) as measured known drift; V31's
  mutation floor (or `null` with its reason) and every zero-kill curation disposition;
  **V35's ruff ceiling change 63 → the observed maximum**, recorded here as the closure step
  directive J requires.
- **`QUALITY.md`'s mandatory rewrite reconciles the LARGE cap to one home** (A18.6) and
  records the measured 302/396 undeclared-`Intent:` baseline so the next release ratchets from
  a number instead of re-measuring cold.
- **The `rc` ledger** — every `rc` burned, what was found on `develop`, by whom, its fix.
- **Intake candidates** — FR16's findings plus any residual, compiled for the PM's
  operator-facing intake report; `product-engineer` creates no backlog entry. **Named at fold
  3, each with its reason:** (1) `public-assets-single-source-engines` — AS-17's three deferred
  engines with their bug ids; (2) the deferred `specs upgrade` rename automation (§1.6);
  (3) `reconcile`'s three cross-feature edges, to collapse the cap 17 → 14 (A18.5);
  (4) `memory_lint.py`'s 87-entry heading allowlist, to derive from the templates (FR17);
  (5) the `Intent:` gate's extension beyond `tests/e2e/**` and any private-import residue above
  0 (V26/V27); (6) the e2e marker-vs-directory fix (V30); (7) FR9's secret-scan coverage limit
  (A9.6). A deferral without a named target is what produced four of public-assets' eighteen.
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
| **V3** | Canon conformance | `dadaia specs doctor --json` reports `specs_pattern_version: 6`, TREE-8 present and WARN-only, and **no TREE-8 WARN on this release's own directory** (A1.9) | **T-050-06**, re-checked at `S1` close (T-050-15) |
| **V4** | Record migration counts | the FR3 migration report: **every record present at branch cut** migrates (the migrated count equals the distinct `bug_id` count measured on the same tree, in the same run — never a constant); `registration_commit` non-null on **every** record over **≥ 124** distinct commits, of which **≥ 79** single-bug; `resolved_commit` non-null on **every resolved** record over **≥ 117** distinct commits, of which **≥ 70** single-bug. The absolute 490 / 470 / 1 005 figures are the **2026-08-26 measurement kept as historical evidence** (the same ledger read 503 `reported` / 474 `resolved` at the pass-2 fold — §1.2's measurement note), never a threshold. The **marker distribution** (`exact`/`release-squash`/`ledger-only`, per sha kind) is **measured and reported**, never thresholded (A3.1–A3.3) | `S1` (A3.1–A3.3) |
| **V5** | Migration idempotence | run the migration twice; `git diff --stat specs/bugs/BUGS.jsonl` empty on the second run | `S1` (A3.4) |
| **V6** | Ref scope | `git log --all --no-merges --format=%H -- specs/bugs/ \| wc -l` ≥ **295**, with `git tag -l 'archive/*' \| wc -l` = **50** recorded beside it | before FR3 runs (AS-9) |
| **V7** | Back-fill report | `releases_histo.jsonl` block count = **the number of release directories the scan visited across both archive layouts** (`specs/_archive/releases/<id>/` and `specs/_archive/<id>/`), with the four non-version directories named and excluded; every non-null sha passes `git cat-file -e` | `S1` (A4.3) |
| **V8** | Archive reachability | `git show <archive-tag>:specs/_archive/releases/v0.4.4/CLOSURE.md \| head` succeeds after FR6 | `S1` (A6.4) |
| **V9** | Hook posture | `pre-commit` exits 0 on a staged set `backlog doctor` rejects; `pre-push` refuses on exactly **three** things and nothing else — invalid branch name, denylist hit, **unresolvable runner** — plus a fixture proving a failing preflight no longer blocks *(fold 3, contradiction 1: this row read "only on branch name and denylist" against A9.2's three refusals; the pre-push fail-closed runner **survives** by A-5/A22.6 and its refusal is asserted)* | `S2` (A9.1, A9.2) |
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
| **V20** | CI verdict-evidence contract | run `.github/scripts/pr-verdict-check.sh` against a **v6 fixture tree**, **one stated expected outcome per arm** (A1.8): (1) live `verdicts/` → PASS; (2) `specs/releases/_archive/<id>/verdicts/` → PASS; (3) `_ideas/<id>/verdicts/` → **fails closed** (`_ideas/` is refused as an evidence root, AS-15); (4) bare-semver id accepted, `v`-prefixed archived id still resolves, traversal / non-canon token refused before interpolation; (5) no qualifying handoff → exit non-zero; (6) **a non-verdict path in the intervening diff — including the gate's own offender-allowlist line — still disqualifies coverage**; (7) derivation failure → exit non-zero, **no fallback glob** | **before T-050-41** (A1.8, A1.10) |
| **V21** | Every canon path is tracked | `git check-ignore` reports *not ignored* for each path of A1.7; the three orphaned stanzas are gone | `S1` (A1.7) |
| **V22** | Migration range is clean | `dadaia ci push-gate-check` over the migration range, **before** the first push; zero hits, or every hit remediated at the source record | `S1`, before pushing T-050-10 (A3.9) |
| **V23** | U+2028 precondition present | write a free-text field carrying U+2028 (and an ESC byte) **through the write seam**: T-045-20 **strips** them, the **stripped record round-trips** (read/write cycle byte-stable), the live ledger parses fully, `bugs status` reports `skipped: 0`, and **no historical record is rewritten** — proving the `v0.4.5` T-045-20 fix is on the branch. "Byte-identical round-trip of a U+2028-carrying field" is unsatisfiable against that fix and is **withdrawn** (AS-14) | before FR3 runs (A3.7) |
| **V25** | **Test-suite size, before and after** | `pytest --collect-only -q -p no:cacheprovider tests` **per tier** at T-050-03 and again at T-050-34, plus `grep -rc "^def test_" tests` for the function count. Baseline **1 859** functions / 396 files / **2 873** items (unit 1 376 · integration 241 · contract 200 · e2e 42). **Gate: after ≤ before** (A22.9); the per-FR `Tests:` lines must sum to the measured delta | T-050-03 (baseline) + `scope complete` (A22.9) |
| **V26** | Private-symbol imports ratchet | `tests/contract/test_test_suite_ratchets.py` pins the count of `from dadaia_workspace… import …_name` statements in `tests/**` outside an inline-commented allowlist. Baseline **24 statements / ~21–22 files**; **target 0**, ratchet **down only**. One of the 24 dies with FR9's deletion; a residue above 0 is recorded with its number and routed to intake | `S2` (T-050-18A), re-checked at `scope complete` |
| **V27** | `Intent:` + size header coverage | same file: every `tests/**/test_*.py` carries `Intent: <KIND>` and a size in its module docstring. Baseline **94/396 declared, 302 undeclared (76 %, SCAFFOLD by doctrine)**; target **396/396**, or a **per-segment ratchet carrying the number** if the sweep is not completed in this release — never an unmeasured "later" | `S2` (T-050-18A) + T-050-33 |
| **V28** | SCAFFOLD carries an expiry | same file: every `Intent: SCAFFOLD` declares `expires: <M.m.p>`, and a SCAFFOLD whose named release is under `releases/_archive/` turns **RED**. Covers T-050-09's `migrate_v5` tests (`expires: 0.6.0`); a slipped expiry is renewed by a recorded `qa-engineer` verdict, never by silence | `S2` (T-050-18A) |
| **V29** | One number per parameter | same file: a scan proving each numeric cap (LARGE census, flake ceiling, quarantine cap) appears in **exactly one** doctrine file — `dadaia-test-stewardship/PARAMETERS.md`. Baseline: the LARGE cap has **three homes, two values** (30 / 30 / 100). Gate: **1 home, value 30** (A18.6) | `S4` (A18.6) |
| **V30** | Pyramid shape, reported | per-tier shares computed from the same `--collect-only` run. Baseline **unit 74.0 % · integration 13.0 % · contract 10.8 % · e2e 2.2 %** against the literature's SMALL ≥ 75 / MEDIUM ≤ 20 / LARGE ≤ 5. **Reported in the closure size accounting, not gated** — drift > 5 pp is a closure finding. Recorded beside it: the **e2e marker-vs-directory drift** (42 functions under `tests/e2e/**`, **15** `e2e`-marked — a 2.8× discrepancy for any `-m e2e` selector), as **measured known drift** with its fix routed to intake (`qa-engineer` amendment 8) | `scope complete` |
| **V31** | Mutation floor on `core/` | one `tests/scripts/run_mutation_baseline.sh` pass over `core/`; the score recorded as a **floor, ratchet up only**; zero-kill tests outside a named `SENTINEL` listed in the closure curation table with a disposition. **If `mutmut` is unreachable in the workspace venv, the value is `null` with its reason and an intake candidate** — never a fabricated number (A22.11) | T-050-03 (availability + baseline) + `scope complete` |
| **V32** | Independence contract is complete | `modules =` in `[importlinter:contract:features-no-cross-feature]` equals the `dadaia_workspace/features/*/` packages on disk (**20/24 → 24/24**); the measured cross-feature edge count is reported (**5**, of which **3** become declared ignores with a reason line); `_RECORDED_IGNORE_EDGE_CAP` reads **17** (`15 − 1 + 3`) and `tests/contract/test_import_linter_ignore_cap.py` agrees; `lint-imports` green | `S4`, **before** the principle is proposed (A18.5) |
| **V33** | The eight forensic metrics | `AUDIT.md` carries all eight of FR14's metrics with `baseline → measured` and, where one exists, the target. A run reporting fewer than eight is incomplete (A14.7) | `S3` (A16.2) + the pillar-3 re-run at `scope complete` |
| **V34** | Always-on ceiling | V12's after-value is **≤ 22 011 tokens** (+500 over the 21 511 baseline), with per-section attribution and anchors on their own line. An overshoot is closed by cutting text before `S2` closes (A11.3) | `S2` (A11.3) |
| **V35** | Ruff ceiling ratcheted to reality | `radon cc` re-measures the observed maximum (**61** today, `_list_agents_impl`); `pyproject.toml`'s `max-complexity` **63 → that number**, never above; `#upgrade` **≤ 26**, `#doctor` **≤ 30**; CC > 10 count **131 → ≤ 133** with every new function above 10 named | `scope complete` (A22.12, A1.4) |
| **V24** | Audit artifact is redaction-clean and self-cited | the FR16 folder and the FR3 migration report scanned by the push detector, zero hits; every `evidence` value is **the reproducible command + a redacted one-line result**, with any `.dadaia/tmp/**` capture as a convenience pointer only — that lane is GC'd at 3 days, so a path is never the sole citation; no transcript pasted | `S3` close (A13.5) |

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
| **Every historical bug record present at branch cut** (490 measured 2026-08-26) | `specs/bugs/bugs.jsonl` since 2026-06 | **migrated, never rewritten in substance** — FR3; `cause`/`caused_by` only where the text states them (A3.5) |
| The 114 legacy `{file, content}` records | `specs/bugs/_archive/archive.jsonl` | **frozen, byte-identical** — AS-3, A3.6 |
| Root `specs/_archive/**` | operator ruling 2026-08-23 D1 | **tagged, then deleted with the operator present** — FR6 |
| Audits | `specs/audits/_archive/` | **none outstanding** — FR16 opens the first audit under the new canon, dispositioned by the *next* release (AS-10) |
| Open reconciliation (`findings[2]` of the grill handoff) | grill 2026-08-26 | **decided** — **AS-1**: derive-on-read is the sole authority; the **audit (FR14 pillar 1) is the only writer of the cache**, in the same atomic rewrite that sets `audited`. There is **no** follow-up ledger commit (FR8 shape 3b deleted) |
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

**Release-id disambiguation — `0.5.0` is not `v0.5.0` (AS-13).** An archived release named
**`v0.5.0`** shipped on 2026-08-12, before the version-axis collapse, on the retired
**spec-lineage** axis. This release is **`0.5.0`** on the **PyPI/one-axis** lineage. The
prefix is the disambiguator and it is canon: a `v`-prefixed id always names the retired axis;
a bare semver id always names the current one. Consequently, the **46 in-code citations
reading `v0.5.0 FRn` across 28 files** (`setup.cfg`, `core/models/bugs.py`,
`hooks/sdd_gate.py` and others) refer to the **archived** release and are **not renamed** —
renaming correct history to spare a reader one lookup is exactly the kind of churn this
release exists to stop. Pillar 2's window recipe excludes the `v`-prefixed id from this
release's history, and any citation of this release's requirements is written `0.5.0 FRn`.

---

## 8. Decisions this SPEC took that the grill did not settle

Flagged for the operator; each is reversible before approval and none contradicts a ruling.

1. **AS-1** *(re-decided at review)* — the `resolved_commit` fill mechanism (the handoff's
   explicit open reconciliation): **derive-on-read is the sole authority; FR14 pillar 1 is
   the only writer of the cache**, in the rewrite that sets `audited`. No follow-up ledger
   commit; FR8 shape 3b deleted.
2. **AS-11 / D-I** — the lineage check lives as **phase 0 of `dd-diagnose`**, not as
   `dd-bug-resolution/LINEAGE.md` as the entry's intent ref proposed.
3. **D-A** — the provenance-marker rule, and with it three new record fields
   (`registration_granularity`, `resolution_granularity`, `lineage_source`) that no entry
   named. The single-name variant `commit_granularity` is withdrawn everywhere.
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
12. **AS-12** — `S4`'s memory window is a **recorded release state**, not a phase toggled
    around a task. The operator ratifies it or takes the stated fallback (FR17–FR21 move into
    the closure window).
13. **AS-13** — the release id stays `0.5.0`; the `v`-prefix rule disambiguates it from the
    archived `v0.5.0`, and 46 in-code citations are deliberately **not** renamed.
14. **AS-14** — the U+2028 seam is a **precondition** discharged by `v0.4.5` T-045-20 and
    verified by V23, not a requirement of this release. The fix **strips** the character at
    the write seam, so V23 asserts a *stripped-record* round-trip, never byte-identical
    preservation (pass 2, SA-R2).
15. **AS-15** — archive still precedes ship (ruling preserved); the verdict gate is fixed at
    the gate by deriving its evidence roots from the canon over **two** roots, with
    `specs/releases/_ideas/` **refused** as an evidence root (pass 2, SEC-R1), naming the
    **third** firing of `verdict-gate-cannot-resolve-evidence-after-release-archive`.
16. **`--recipe` is kept** against the `software-architect`'s S4 cut — see §9.1, the one
    reviewer amendment fold 1 refuses, with its reason. Pass 2 accepted that rejection on the
    merits with one condition, now in **A1.3**: `--recipe` renders the same
    `doctor --json` finding objects, never a second step table.
17. **The release-id canon flips to bare semver** (pass 2, SA-R1) — `RELEASE_SEMVER_RE`, its
    three production consumers, its identity contract test and the bash→canon derivation
    mechanism are named in **FR1 boundary 2a**, carried by **T-050-06A** and **A1.10**.
18. **Absolute ledger counts leave the acceptance** (pass 2, SA-R5) — every threshold reads
    "every record present at branch cut"; 490 / 470 / 1 005 survive as the dated 2026-08-26
    evidence (§1.2's measurement note).
19. **AS-16** *(fold 3, OPERATOR-GATED)* — one write seam for `BUGS.jsonl`, with the exposure
    left to the operator: **(i)** the `dadaia bugs update` governance verb (recommended,
    leaf-neutral at **71** once `specs release open` and `specs segment open` go) or **(ii)** a
    skill-invoked Python entry point (69 leaves). The seam itself is not optional.
20. **AS-17** *(fold 3, OPERATOR-GATED)* — three of public-assets' four recurrence engines are
    deferred by name with their bug ids and one intake target; the fourth (the roster class) is
    retired here as **FR10A**. **The deferral is also measured** (fold 4, §9.4 V-3): T-050-34
    reports the count of bugs registered with `surface: public-assets` during `S1`–`S4`, which
    the closed `surface` enum makes free at FR16's metric 4 — a deferral whose live cost is
    counted, not only estimated.
21. **The record model gains three measuring fields no entry named** — the restored **FR23
    evidence triple** (write-once), **`diff_direction`**, and a **closed `surface` enum**
    sharing the independence contract's package list as its single source. Without them,
    forensic metrics 1–4 and 6 are not computable and pillar 1 measures 2 of 8.
22. **The test suite acquires a ceiling and its markers acquire ratchets** — A22.9's
    net-non-positive gate, V25–V30's one contract file, and the explicit statement that these
    are **test-suite** ratchets, outside A18.3's product-check scope.
23. **The `specs upgrade` automation is cut and the complexity ceilings become acceptances** —
    `#upgrade` ≤ 26, `#doctor` ≤ 30, `max-complexity` 63 → the observed maximum (61).
24. **The always-on additions get a number, not just a measurement** — a **+500-token**
    ceiling with a per-section budget (V34); an overshoot is closed by cutting text.

---

## 9. Review fold (2026-08-26)

**Four** folds have run over this trio. **Every amendment every review raised carries a
disposition below — none is silently dropped.**

**Review-id namespaces, declared once (fold 3, `software-architect` §1).** The tables below —
and the few normative clauses that cite a review by id — use these prefixes, and nothing else:
`SA-*` / `SA-R*` / `SA-Q*` = `software-architect` (pass 1 / pass 2 / pass 3);
`A-*` and `SEC-R*` = `security-reviewer`; `QA-*` / `QA-Q*` = `qa-engineer`; `AI-*` =
`ai-engineer`; `CR-*` = `code-reviewer`; `S-*` and `N-*` = the `security-reviewer` reviews'
own internal finding and note numbering; `AR-*` = an architecture ruling requested by a task
(`AR-1`, T-050-04). **`BL-CONFLICT`** is a backlog cross-ownership adjudication recorded when
two entries claim the same file (D-B). Each resolves in `reviews/`; **§9 is their index**, and
a reader who has never opened those files needs nothing beyond this paragraph to follow the
normative text.

**Where a review conflicts with a ratified ruling, the ruling stands and the conflict is
named** (`DADAIA.md` §6 / `dd-release-implement`: finalization order is memory → CLOSURE →
sweep → **archive** → ship). One such conflict arose — S-1's first option — and is resolved
in favour of the ruling in AS-15.

### 9.1 Pass 1 (2026-08-26) — five definition reviews

Counts, per reviewer, matching each review's own list: `software-architect` **14** ·
`security-reviewer` **14** · `qa-engineer` **7** · `ai-engineer` **5** · `code-reviewer`
**15** — **55 total: 47 applied, 7 applied-modified, 1 rejected.**

#### 9.1.1 `software-architect` — REWORK (targeted)

| id | Amendment | Disposition | Where |
|---|---|---|---|
| SA-1 | F1 — fix the U+2028 `splitlines()` seam as Arm B before/inside T-050-07; add A2.6; correct AS-4 | **applied-modified** — the fix belongs to `v0.4.5` T-045-20 (Arm B, already owned); this release references it as a **precondition** and verifies it, rather than re-specifying a fix with another owner | AS-14 · AS-4 · A3.7 · **V23** · FR2 bug-history paragraph (overclaim removed) |
| SA-2 | F2 — FR2 states immutability is audited not gated; atomic replace + re-read; pillar-1 "core field changed" measure; rewrite the `DADAIA.md` §3 ADDITIVE row | **applied** | FR2 (three categories, atomic-write paragraph) · **A2.2**, **A2.7**, **A2.9** · FR14 pillar 1 (core-field mutation) · FR11 §3-row rewrite |
| SA-3 | AS-1 → option (ii); delete FR8 shape 3b; A8.2 becomes "audit-filled equals derived" | **applied** | **AS-1** · FR8 shape 3 · **A8.2** · FR14 pillar 1 · §8.1 |
| SA-4 | F3 — T-050-11 enumerates every `ACTIVE.md` consumer; the fold is `core/release_events.py`; the contract step moves after T-050-21 | **applied** | FR4 (28-consumer enumeration, fold home, ordering) · **A4.5**, **A4.7** · T-050-11, **T-050-21A** |
| SA-5 | F6/AR-1 — generic `jsonl_record_store.py`; migration-owned v5 adapter; pure derivation over a `GitHistoryReader` protocol; T-050-04 becomes a confirmation | **applied** | **A2.5**, **A3.10**, **A13.4** · PLAN §2 · T-050-04 |
| SA-6 | F4 — the release-id collision with the archived `v0.5.0` | **applied** | **AS-13** · §7 "Release-id disambiguation" |
| SA-7 | F5 — §1.1 row 1 is "one class, nine instances, three patched" | **applied** | §1.1 · FR1 bug-history |
| SA-8 | F8 — one marker name everywhere | **applied** | **D-A** · FR2 field list · FR3 step 4 · FR7 · FR14 pillar 1 · PLAN §0 · §8.3 |
| SA-9 | S2 — drop `picked` from `status` | **applied** | FR2 vocabulary · FR8 shape 5 · T-050-01, T-050-08 |
| SA-10 | S3 — `RELEASE.jsonl` kinds 15 → 7 | **applied** | FR4 |
| SA-11 | S4 — do not add `specs doctor --recipe`; let `specs upgrade` print it | **rejected** — `doctor` reports and `upgrade` acts; folding the recipe into `upgrade`'s output would force an agent to run a **mutating** verb to learn what it must do by hand. `--recipe` is a read-only output flag on a read-only verb, adds no blocking exit, and does not touch D15. The `specs-canon-v6` entry asks for the recipe; this is the cheaper home for it | FR1 · A1.3 · V3 (unchanged) |
| SA-12 | S5 — name the deletion list explicitly | **applied** | FR2 (`A2.5` legacy reader) · FR4/A4.4 · **FR15 extended scope** (`AUDIT_DIR_NAME_RE`, `RELEASE_ARTIFACTS`) · V19 |
| SA-13 | S7 — pillar 1 gains the registration→resolution interval measure | **applied** | FR14 pillar 1 · §1.1 certify row |
| SA-14 | Axis-5 drift — D3's `implemented` = final-rc **QA close** sha vs T-050-42's PR merge; pick one and state it | **applied** — QA-close sha | FR4 (`implemented` paragraph) · T-050-42 |

#### 9.1.2 `security-reviewer` — REJECTED (14 findings, A-1 … A-14)

| id | Amendment | Disposition | Where |
|---|---|---|---|
| A-1 | S-1 CRITICAL — own the CI evidence contract; canon names `verdicts/`/`reviews/`; V20 before T-050-41 | **applied-modified** — the amendment's alternative "archive **after** the ship PR merges" contradicts `DADAIA.md` §6 / `dd-release-implement` (memory → CLOSURE → archive → ship) and is refused on that ground; the **structural** option is taken instead: the gate derives its evidence roots and id pattern from `core/specs_version.py`, so the next canon move cannot break it. Third firing of `verdict-gate-cannot-resolve-evidence-after-release-archive`, named as such | **AS-15** · FR1 boundary 2 · **A1.8**, **A1.9** · **V20** · T-050-06A |
| A-2 | S-2 HIGH — own `.gitignore`; invert the shape per area; V21 `check-ignore` contract | **applied** | FR1 boundary 1 · **A1.7** · **V21** · T-050-06A |
| A-3 | S-3 HIGH — schema-derived redaction for `BugRecord` on both write paths, with its test | **applied** | FR2 redaction paragraph (`eb03d01b` / `0cb08157`, T-045-19) · **A2.6** |
| A-4 | S-4 HIGH — redact migrated prose through that seam; V22 scans the migration range pre-push | **applied** | FR3 steps **6b**/**6c** (rename amnesty + refusal procedure) · **A3.9** · **V22** |
| A-5 | S-5 HIGH — pre-push keeps its fail-closed runner; third fixture proving refusal | **applied** | FR9 bullet 2 · **A9.2** · **A22.6** |
| A-6 | S-6 MEDIUM — remote reachability proof, verdict relocation, scan-refusal path | **applied** | **A6.1**, **A6.2**, **A6.4**, **A6.6** |
| A-7 | S-7 MEDIUM — A2.2 states detection not prevention; add the core-vs-first-add doctor WARN | **applied** | **A2.2**, **A2.7** · FR14 pillar 1 |
| A-8 | S-8 MEDIUM — resolve the `audited`-write contradiction; retarget A13.2 at FROZEN | **applied** — resolved per `software-architect` AS-1(ii): pillar 1 writes `audited` **and** `resolved_commit` in one atomic rewrite through the FR2 seam; allowlist = `specs/audits/**` + `specs/bugs/BUGS.jsonl` (governance fields, via the seam) | FR13 allowlist paragraph · **A13.2** · FR14 pillar 1 · **A14.6** |
| A-9 | S-9 MEDIUM — scan the audit folder and the migration report with the push detector | **applied** | **A13.5** · **V24** |
| A-10 | S-10 MEDIUM — drop or constrain `session_id` | **applied** — dropped from the envelope entirely | FR4 (`{ts, event, agent, data}`) |
| A-11 | S-11 MEDIUM — enumerate the post-v6 FROZEN set, one fixture per path | **applied** — including `specs/releases/_archive/` and the deliberate MUTATING status of `_ideas/` | **A6.3** |
| A-12 | S-12 LOW — extend secret-scan to `develop` PRs, or state the limit | **applied-modified** — the limit is **stated** and carried as an intake candidate; the trigger is not extended (new CI surface on a LOW finding, and the honest statement is the truer fix) | FR9 last bullet · **A9.6** |
| A-13 | S-13 LOW — name the exact verdict path and the 40-hex rule in every verdict task | **applied** | T-050-02, T-050-36, T-050-37, T-050-42, T-050-43 |
| A-14 | Q6 — A19.3 claims the pairing detection only; record the attribution limit | **applied** | **A19.3** |

#### 9.1.3 `qa-engineer` — REWORK

| id | Amendment | Disposition | Where |
|---|---|---|---|
| QA-1 | Cite real bug ids for the certify chain, the frozen-clock hops and the ledger family's second symptom | **applied** — all four chains pinned to real ids; the non-existent `frozen-clock-guard-tz-boundary-031` is **removed from every example** and replaced with real records | §1.1 · §1.5 · FR2 examples · FR7 evidence block · FR13 example · **A16.2** |
| QA-2 | Reconcile FR3's structural `release-squash` marker against §1.2's narrative 155 | **applied** — the two units are named, the divergence (~400 vs 155) is stated, and V4 pins only what the algorithm computes | §1.2 · **A3.3** · **V4** |
| QA-3 | Drop the "≥ 79 marked `exact`" equivalence or measure the code-touching subset | **applied** — the `≥` thresholds move onto the definitions actually measured; marker distribution is reported | **A3.2** · **V4** |
| QA-4 | Add the two hook tests to T-050-18's write set with an explicit stewardship verdict | **applied** — both paths verified present at HEAD | **A9.3** · T-050-18 write set |
| QA-5 | State T-050-09's tier placement given the open xdist crash | **applied** — `tests/contract/`, never `tests/unit/`, with a CI-matrix note | T-050-09 · T-050-34 |
| QA-6 | Name the `ACTIVE.md`/`CLOSURE.md` test census (26 + 4) in T-050-11/T-050-21 | **applied** | FR4 · **A4.7** · T-050-11, T-050-21A |
| QA-7 | The QA closes confirm **zero** new `tests/e2e/**` exceptions were granted, or name them | **applied** | T-050-15, T-050-22, T-050-27, T-050-33 |

#### 9.1.4 `ai-engineer` — REWORK

| id | Amendment | Disposition | Where |
|---|---|---|---|
| AI-1 | **Blocking** — an `ai-engineer` task widening `software-architect`, `qa-engineer`, `code-reviewer`, `security-reviewer` to `specs/releases/**/reviews/**`, sequenced before T-050-04 | **applied** | **T-050-03A** |
| AI-2 | **Blocking** — every test in `test_rules_skills_map.py` at HEAD has a proven counterpart in `test_behavior_map.py` before the old file is deleted | **applied-modified** — "byte-for-byte-equivalent" is unachievable in an extended enforcer and would be a false criterion; the acceptance is a **name-diff with zero-hit residue plus a behaviour note per check**, which is what "no regression lost" actually means | **A10.6** · T-050-19 |
| AI-3 | Make scoped-`AGENTS.md` discovery structural (glob the generators); name the three unlisted `.dadaia/*-AGENTS.md` sources | **applied** — all three verified present in `public/data/` | FR10 discovery paragraph · T-050-19 |
| AI-4 | Anchors as zero-cost comment markup; extend A8.1's duplicate scan to scoped-`AGENTS.md` pairs | **applied** | FR11 anchors paragraph · **A11.1** · **A8.1** |
| AI-5 | Name the projection owner in T-050-23 (`ai-engineer`, the last write) | **applied** | T-050-23 |

#### 9.1.5 `code-reviewer` — REWORK (1 CRITICAL, 8 HIGH)

| id | Amendment | Disposition | Where |
|---|---|---|---|
| CR-1 | Add the loop end to end in one place: A's fix commit → B's record with `caused_by` → the pillar-1 finding → its disposition | **applied-modified** — built with **real** ids from the certify chain, so the reviewer's "mark synthetic ids as synthetic" becomes unnecessary rather than unaddressed; A16.2 points at it | **§1.5** · **A16.2** |
| CR-2 | Pin each of §1.1's four chains to an explicit bug-id list; fix the gitignore row | **applied** | §1.1 · **A16.2** · **V16** |
| CR-3 | Resolve FR6 vs `consumed_backlog.json` — relocate the 18 sidecars or retire BL-STALE | **applied-modified** — **relocate**; the "retire BL-STALE" alternative is refused (deleting a rule to avoid moving its data is the symptom patch this release exists to stop) | FR5 BL-STALE paragraph · **A5.5** · **A6.2** · T-050-13A |
| CR-4 | Disposition the U+2028 bug; correct "the single open bug" and its four citations | **applied-modified** — it is neither picked nor superseded here: it is **already owned as Arm B by `v0.4.5` T-045-20** and becomes this release's precondition. Every citation corrected | **AS-4**, **AS-14** · header · §1.1 · FR2 |
| CR-5 | One name for the granularity marker across D-A, PLAN §0, FR2, FR3, FR7, FR14, §8 | **applied** | as SA-8 |
| CR-6 | Re-derive A3.2/A3.3 from the marker definitions; drop T-050-10's "a low count means the ref scope was wrong" | **applied** — reworded: a **threshold** miss means the ref scope; a **marker distribution** surprise is a fact to record | **A3.2**, **A3.3** · T-050-10 |
| CR-7 | Fix the FR4 write set; give the surviving `CLOSURE.md` parsers a retiring FR | **applied** | FR4 enumeration · **A4.4**, **A4.7** · **FR15 extended scope** · T-050-25A |
| CR-8 | Resolve the `S4` memory-phase conflict by an operator ruling recorded as an assumption | **applied** | **AS-12** · T-050-28, T-050-33 |
| CR-9 | Move FR5's write set to `features/backlog/**`; add its row to PLAN §2 | **applied** — `doctor.py`, `document.py`, `ledger.py` verified present | FR5 · PLAN §2 · T-050-13 |
| CR-10 | Scope `dadaia bugs archive` with an acceptance, or relax AS-8 | **applied** — scoped into FR2 | FR2 archive paragraph · **A2.8** · **AS-8** · T-050-08 |
| CR-11 | Commit the FR3/FR4 reports somewhere durable — `.dadaia/tmp/` is GC'd at 3 days | **applied** — headline counts live in the release's `RELEASE.jsonl` `note` records and the closure record; the raw captures stay under `.dadaia/tmp/**` and are cited only where they are still in the retention window | T-050-10, T-050-12, T-050-40 |
| CR-12 | Name `reviews/` and `verdicts/` in FR1's release-directory canon, or accept a permanent self-WARN | **applied** — named | FR1 canon paragraph · **A1.9** · **V3** |
| CR-13 | Define at first use in the SPEC: `seam`, `FR23`, Arm A/B, `histo`, "live photo", TREE-5, "thawed tree", "one-axis law", "operator law O5"; add a falsifiable success statement to §1 | **applied** — one pointer to PLAN §0 (which gains the missing rows) rather than a second glossary, and §1.5 carries the falsifiable statement | §1.5 "Terms" · **PLAN §0** |
| CR-14 | Fix T-050-12's archive scan to cover both `_archive/` layouts; define V7's denominator | **applied** | FR4 back-fill paragraph · **V7** · T-050-12 |
| CR-15 | Housekeeping (A10.1 cardinality · FR2 "shape never changes" + a write-once test · one blocker count · AS-9 "295 of 295" → 220 · 471 → 470 · A1.5's `gate_policy.py` → `hooks/sdd_gate.py` · the two spellings of the follow-up commit · re-label AS-5/6/7/9 · restore `RC-FLOW.md`'s `dd-architecture-survey` pointer · a named task for `specs/assets/` and `remote-bugs/` · valid-JSON FINDINGS example without its `T-050-04` back-reference) | **applied**, every sub-item | **A10.1** · FR2 three categories + **A2.2(b)** · §2 objective + **A22.6** · **AS-9** · §1.1 · **A1.5** · FR8 shape 3 (one spelling, then deleted) · **AS-5/6/7/9** re-labelled · FR12 `RC-FLOW.md` · T-050-06 write set · FR13 example |

### 9.2 Pass 2 (2026-08-26) — the two blocking re-reviews

Both blocking reviewers re-read the folded trio at `b1d424b8`. `software-architect` returned
**REWORK (targeted, textual)** — root-cause gate **PASS**, architecture-fidelity gate **FAIL
(narrow)** on one understated consumer set — with five items; `security-reviewer` returned
**APPROVED (definition stage)** with five residuals that must land before the trio becomes
`Em revisão`. **Ten items, ten dispositions, nothing dropped; all ten are textual — no FR is
re-scoped, no ratified ruling reopened, no write set touches `.github/**` that did not
already.**

| Reviewer | id | Amendment | Disposition | Where |
|---|---|---|---|---|
| `software-architect` | **SA-R1** *(gate FAIL, §3 + verdict 1)* | FR1/T-050-06A: `RELEASE_SEMVER_RE` mandates `v`, is identity-locked by `tests/contract/test_release_semver_canon.py` and has production consumers — enumerate the bare-semver flip's consumers and **name** the bash→canon derivation mechanism | **applied** — the flip is scoped to **FR1** (which owns both boundaries), not FR4, and stated as new sub-clause **boundary 2a**: one anchored compiled object (optional `v` = the retired axis, bare = current, no second pattern), the **three** production consumers verified by grep (`scaffolder.py`, `doctor_release.py` ×2, `spec_artifacts/new_artifacts.py`) plus **two** test consumers, the mechanism named (a stdlib-only `python3 -c` import of `core.specs_version` on the bare checkout — feasible because both `__init__.py` are empty and the module imports only `re`/`pathlib`; a `--gate-json` export is refused as new CLI surface), and the failure posture pinned: **any derivation failure ⇒ the gate exits non-zero, no `\|\|` fallback glob, no default root**. Correction recorded: the review's *"bug-lifecycle `resolved_release` validator"* **does not exist at HEAD** (grep: zero hits) — the enumeration is closed | **FR1 boundary 2 + 2a** · **A1.10** · **A1.8** (arms 4/7) · **V20** · T-050-06A write set + description · PLAN §2 `core` row |
| `software-architect` | **SA-R2** *(verdict 2)* | V23/A3.7/T-050-10: "round-trips byte-identically" is unsatisfiable — the T-045-20 fix **strips** U+2028/ESC/C0 at the write seam (`core/models/bugs.py`, commit `2b9b30c1`); and §1.1 row 4 still says the bug is open | **applied** — restated to the fix's real semantics: the **stripped record round-trips**, the live ledger parses fully, `skipped: 0`, **no historical record rewritten**; the byte-identical claim is explicitly **withdrawn**. §1.1 row 4 now reads *resolved on this tree* (ledger line 1006, 2026-08-26T13:41Z; reader splits on `"\n"` only) and the header precondition line with it | §1.1 row 4 · header precondition · **AS-14** · **A3.7** · **V23** · T-050-10 · T-050-15 question 4 |
| `software-architect` | **SA-R3** *(verdict 3)* | A11.1 vs T-050-21A: the Tier-1 "by exception" `DADAIA.md` write makes A11.1 RED by its own definition — move the `ACTIVE.md`-citation edit into T-050-20 | **applied** — the exception is **deleted**, not documented: `DADAIA.md` leaves T-050-21A's write set entirely and T-050-20 (FR11, already sequenced before it) removes the `ACTIVE.md` citation in the same edit that lands the anchors. Tier 1 is again *exactly one task per file*, which is what A11.1's grep asserts | T-050-20 (write set + description) · T-050-21A (write set + description) · **A11.1** · D-B Tier 1 |
| `software-architect` | **SA-R4** *(verdict 4)* | FR2 prose says the race loser's write is "*lost*" while A2.9 says the writer "*refuses* a stale rewrite" — two designs; keep A2.9's | **applied** — one race semantics, stated once: **refuse-stale, caller retries**. The "lost" sentence is withdrawn with its reason (it described last-write-wins); pillar 1 still *detects* what the design does not prevent | FR2 atomic-write paragraph · **A2.9** · **A2.7** · FR14 pillar 1 |
| `software-architect` | **SA-R5** *(verdict 5 — housekeeping, 3 sub-items + the SA-11 advisory)* | delete §7's "the follow-up ledger commit is the cache" row text; name `core/protocols/bug_store.py` in the A2.5 deletion list; V4's absolute 490/490 → "every record at branch cut" (the ledger already reads 503/473). **Plus §2's advisory condition on the accepted `--recipe` rejection** | **applied**, every sub-item — §7's row now states AS-1 correctly (no follow-up commit exists); the event-store **protocol** retires with its implementation (a protocol whose only implementation is gone is dead code behind a dead artifact); every count-based acceptance is restated as *"every record present at branch cut"*, with 490/470/1 005 kept as **dated evidence** in a new §1.2 measurement note (re-measured at this fold: **503** `reported` / **474** `resolved` — the drift the review predicted, one more than it saw). The **SA-11 advisory is applied in A1.3**: `--recipe` is a rendering of the same `doctor --json` finding objects, proven by a contract test tracing each step to a finding id — never a second, driftable step table | §7 row · **A2.5** · **V4**, **A3.1**, **A3.2**, **A3.3**, FR3 opening + heading, §2 objective, §7 row, T-050-10 · **§1.2 measurement note** · **A1.3** |
| `security-reviewer` | **SEC-R1** *(residual 1 — N-1/S-1)* | V20 states an expected outcome per fixture arm, and **`_ideas/` is refused as an evidence root** (T-050-01 removes the only reason to admit it) | **applied — refused, not justified.** AS-15 now resolves **two** roots (live + per-area archive) and names the refusal's reason: T-050-01 `git mv`s the trio out of `_ideas/` before any PR exists, and A6.3 keeps `_ideas/` deliberately **MUTATING** — a freely-writable directory is never a trust root of a required check. V20's `_ideas/` arm becomes a **refusal** arm with a stated outcome | **AS-15** · **A1.8** (7 arms, each with its expected outcome) · **V20** · T-050-06A (b) · A6.3 cross-reference |
| `security-reviewer` | **SEC-R2** *(residual 2 — N-2)* | state the derivation's failure posture in FR1 boundary 2 and T-050-06A: interpreter failure, missing module or symbol ⇒ **gate exits non-zero**; no fallback glob, no `\|\|` default | **applied** — stated in the FR text, in the task, and as V20 arm 7 | **FR1 boundary 2a** (failure-posture bullet) · **A1.8** arm 7 · **V20** · T-050-06A |
| `security-reviewer` | **SEC-R3** *(residual 3 — S-1)* | V20 gains one arm proving **a non-verdict path in the diff still disqualifies coverage**; and T-050-06A records that only the pathname glob is broken today, **not** the bash `case` | **applied** — arm 6 uses the gate's **own** offender-allowlist line as the non-verdict path, so a derivation that touches that line can never silently un-gate the check; FR1 boundary 2 and T-050-06A both record that in a bash `case` `*` crosses `/`, so the offender allowlist already matches the deeper archive path and is **not** part of the defect | **A1.8** arm 6 · **V20** · FR1 boundary 2 · T-050-06A (b) |
| `security-reviewer` | **SEC-R4** *(residual 4 — S-1)* | name where the bare-vs-`v` id pattern lands **relative to `RELEASE_SEMVER_RE`** — identity-locked, three production consumers outside the write set — and keep it **anchored**, refusing `_`-prefixed and traversal shapes | **applied** — same clause as SA-R1: one anchored `^…$` object with the optional `v` reserved for read-only archive lookups, `is_release_semver` staying the current-axis predicate so no `v`-prefixed id can be **minted**; identity assertion preserved, behaviour assertions inverted under a recorded `qa-engineer` verdict; `_ideas`/`_archive`/traversal tokens still refused before interpolation | **FR1 boundary 2a** · **A1.10** · **A1.8** arm 4 · T-050-06A write set |
| `security-reviewer` | **SEC-R5** *(residual 5 — S-9/N-3)* | A13.5 and the FR3 report make `evidence` **self-contained** — reproducible command + redacted one-line result, the `.dadaia/tmp/**` capture a convenience only (that lane is GC'd at 3 days); and add `security-reviewer`'s `verdicts/**` path to T-050-03A | **applied** — `evidence` is redefined as *command + redacted one-line result* in A13.5, in FR13's immutable-field list, in V24 and in FR3's report paragraph, with the 3-day GC named as the reason a path-only citation decays into an unverifiable claim. T-050-03A's write set gains `specs/releases/**/verdicts/**` for `security-reviewer` — the same *"persona forbidden to write the artifact the law requires of it"* shape FR13 just fixed for `project-auditor`, and the persona whose own PR gate depends on committing that file | **A13.5** · FR13 `evidence` field · **V24** · FR3 report paragraph · **T-050-03A** (write set, description, done criterion) |

**Pass-2 tally.** 10 items · **10 applied** (0 applied-modified, 0 rejected). Two reviewer
statements were corrected against the tree rather than transcribed: the non-existent
`resolved_release` validator (SA-R1) and the ledger's own drift, 473 → **474** `resolved`
between the review and this fold (SA-R5) — which is itself the argument for retiring absolute
counts from acceptance. No re-review was required for those ten.

### 9.3 Pass 3 (2026-08-26, quantitative) — the two quantitative reviews

`software-architect`'s full quantitative review (**REWORK**; §9 ten ranked changes; §11 verdict)
and `qa-engineer`'s test-minimization review (**twelve ranked amendments**), read against
`reviews/bug-history-forensic-100.md` §5, `reviews/architecture-metrics-baseline.md` §8 and
`reviews/test-minimization-literature.md` Part 3. **22 items, 22 dispositions, nothing
dropped.** Where a review conflicts with a ratified ruling the ruling wins and the conflict is
recorded (none did at this fold); where a review conflicts with an operator directive of this
fold, the directive wins and the deviation is named (one did — SA-Q5).

| Reviewer | id | Amendment | Disposition | Where |
|---|---|---|---|---|
| `software-architect` | **SA-Q1** | One write seam for `BUGS.jsonl` on the executed path — the file has **3** writers, 2 of them file tools, so A2.6/A2.9/A14.6 are unprovable for them; add one governance verb and offset the leaf count | **applied** — the seam is fixed in `features/bugs`'s record store for **every** writer; the **exposure** becomes **AS-16 (operator-gated)**, (i) `bugs update` recommended with the D8 reasoning made explicit ("D8 forbids growth **by reflex**; replacing three ad-hoc writers with one seam is the opposite") and the leaf arithmetic closed at **71** by deleting `specs release open` + `specs segment open`, both verified at `cli/commands/specs.py:26,28`; (ii) the Python entry point stated as the honest fallback at 69 | **AS-16** · FR2 one-seam paragraph · **A2.13** · **A8.3** (verb correction) · FR4 bug-surface (the two dead leaves) · T-050-08, T-050-21A |
| `software-architect` | **SA-Q2** | Restore the FR23 triple (`evidence_loop`/`_seam`/`_diff`) as write-once fields; migrate from v5; make forensic metric 2 a pillar-1 output | **applied** — restored as write-once, with `diff_direction` beside it; FR3 carries every existing value verbatim and counts what it carried | FR2 field categories + the FR23 paragraph · **A2.11** · FR3 step **6d** · **A3.11** · FR14 metric table rows 2–3 |
| `software-architect` | **SA-Q3** | Do not automate `specs upgrade`; ship `doctor --recipe` only — chain 1 of the forensic is `specs upgrade` and the function is at CC 26 | **applied** — the automation is **cut**; `--recipe` renders in its own function; the acceptance becomes measured complexity (`#upgrade` ≤ 26, `#doctor` ≤ 30) and the deferral is an intake candidate | §1.6 specs-doctor row · FR1 (`specs upgrade` paragraph) · **A1.4** · **V35** · §4.9 · T-050-05 |
| `software-architect` | **SA-Q4** | Move the derivation to `core/`; `migrate_v5.py` keeps the adapter + runner and stays deletable; FR8's resolver imports core | **applied** — **`core/bug_provenance.py`**, pure and stdlib-only, with a contract test proving no permanent consumer imports the deletable module; T-050-09's placement and write set corrected | **A3.10** · FR3 bug-surface · PLAN §2 `core` row · T-050-09 |
| `software-architect` | **SA-Q5** | Canonical `surface` enum — the forensic's 18 buckets | **applied-modified — the operator's directive E supersedes the reviewer's shape, and the deviation is named.** The enum derives from **the feature-package list the independence contract uses**, not from the forensic's hand-normalised buckets: one source for two consumers (A2.12 ↔ A18.5) beats two lists that must be kept equal. The forensic's normalizer becomes FR3's legacy **mapping table**, unmapped → `surface: unknown`, counted | FR2 `surface` paragraph · **A2.12** · FR3 step **6d** · **A3.11** · **V32** |
| `software-architect` | **SA-Q6** | Add the 6 missing forensic metrics to `PILLAR-BUGS.md` with baselines and targets, plus `diff_direction` | **applied** — all **eight** metrics carry definition, command, baseline and the record field that makes each computable, as a table `PILLAR-BUGS.md` reproduces verbatim; each row is a validation | FR14 metric table · **A14.7** · **V33** · T-050-24 |
| `software-architect` | **SA-Q7** | Name the public-assets exposure and cap it; retire the hand rosters FR10's glob makes redundant | **applied — split, and the split is stated.** Engine 1 of 4 qualifies for a bounded FR and becomes **FR10A** (deletion-only, size S, `tests/` only); engines 2–4 do not (each lives in a 1 048-LOC module with a CC-40 `doctor` and each replacement is a new derivation) and become **AS-17**, operator-gated, with their bug ids and one intake target. Exposure quantified in §1.6: 10 projection cycles, 1 skill renamed, 1 added, 5 scoped `AGENTS.md` | **§1.6** · **AS-17** · **FR10A** (A10A.1–A10A.4) · §4.9 · T-050-19A |
| `software-architect` | **SA-Q8** | Complete the independence contract before FR18 promotes it — a principle must be true when accepted | **applied**, with two reviewer figures corrected against the tree: the gap is **4 packages of 24** (not 5 of 25) — `capabilities`, `certification`, `reconcile`, `tmp_gc`; `workspace` and `workspace_clean` are **both** listed. Edges 5 → 5 visible, of which 3 become declared ignores with a reason line; cap **15 → 17** (`15 − 1` FR2 + `3`) in the same commit as `setup.cfg` | **A18.5** · FR18 independence table · **V32** · §4.9 · T-050-29 |
| `software-architect` | **SA-Q9** | Test economy with numbers: tests before/after, private-symbol ratchet, 302 undeclared, one LARGE number, ruff 63 → 61 | **applied** — every clause landed as a validation: **V25** (count), **V26** (24 → 0), **V27** (94/396 → 396/396), **V29** (one number, PARAMETERS.md's 30), **V35** (63 → observed max) | **A22.9**–**A22.12** · **A18.6** · **V25**–**V35** · §3 standing rules · T-050-18A, T-050-34 |
| `software-architect` | **SA-Q10** | Textual closure: 8 undefined review ids, 6 traceability gaps, 5 contradictions, `_OPTIONAL_STR_FIELDS`, `release_events.py` read-only, V12 ceiling | **applied, every sub-item.** Ids: §9's preamble now declares the review-id namespaces and PLAN §0 carries the row. Gaps: A4.1 → T-050-21A (**A4.1a** for T-050-11) · A16.4 re-run at scope-complete · T-050-03A given **A13.6** · `core/models/backlog.py`'s registration placed in FR5/T-050-13 · `registration_commit`'s writer named (pillar 1, A14.6) · `specs/bugs/README.md` retires **in T-050-16** beside its replacement. Contradictions: V9 ↔ A9.2 · T-050-26/27 evidence wording ↔ A13.5 · T-050-26's duplicate `Preconditions` · FR14's `_ideas` window ↔ AS-7/D10 · `dadaia bugs resolve` ↔ the real verb set. Plus `_OPTIONAL_STR_FIELDS` deleted (A2.10), `release_events.py` declared read-only with its file-tool append seam named, and V12 given the **+500** ceiling | **A2.10** · **A4.1/A4.1a** · **A13.6** · **A14.6** · **A16.4** · **V9** · **V34** · FR4 read-only paragraph · FR14 window · §9 preamble · PLAN §0 · T-050-10, T-050-13, T-050-16, T-050-26, T-050-34 |
| `qa-engineer` | **QA-Q1** *(CRITICAL)* | Add `V-TESTCOUNT`: `--collect-only` before and after, per tier — the operator's "fewer tests" has **no metric anywhere** and PLAN disclaims the goal outright | **applied** — **V25** with a **gate** (A22.9: after ≤ before), per-FR `Tests: +N / −M` lines on **every** FR, and PLAN's "net-additive in tests by nature" **withdrawn and replaced** | **V25** · **A22.9** · §3 standing rules · every FR's `Tests:` line · PLAN §6 |
| `qa-engineer` | **QA-Q2** | T-050-08 enumerates the `BugEvent`-referencing files with a per-file disposition | **applied**, re-measured: **9** files at this fold (the review measured 8), four deleted whole and five rewritten in place, each named — and the census is **re-measured at task time**, never trusted from the list | FR2 `Tests:` line · T-050-08 write set + done criterion |
| `qa-engineer` | **QA-Q3** | T-050-25/25A enumerates the 3 SPEC-DOC-036/038 golden-fixture files | **applied**, all three verified present: `test_doctor_taxonomy_disposition.py`, `test_doctor_golden.py`, `_golden/doctor_golden_v0155.json` — with the anti-reflex rule stated (curate the entries whose subject died; never re-baseline the golden) | FR15 `Tests:` line · T-050-25A |
| `qa-engineer` | **QA-Q4** | T-050-18's hook-test verdict pre-committed to **DELETE**, not left open | **applied** — both files DELETE, with the three replacement contract fixtures as the evidence and the reasoning stated: an open verdict on a test whose premise was deleted resolves to "rewrite" by default, which is how a change-detector enters a suite. This is the release's one LARGE-tier removal with no same-tier replacement | **A9.3** · FR9 `Tests:` line · T-050-18 |
| `qa-engineer` | **QA-Q5** | T-050-33 records the measured 302/396 undeclared-SCAFFOLD count | **applied-modified** — recording alone leaves an invisible debt visible but unmoving; per the operator's mandate it becomes a **ratchet** (**V27**, 94/396 → 396/396 or a per-segment number) with the baseline also written into `QUALITY.md` so the next release ratchets from a number | **V27** · **A22.10** · §5 closure obligations · T-050-18A, T-050-33 |
| `qa-engineer` | **QA-Q6** | T-050-19 names the two Windows bug ids and requires a cross-platform CI run of the five new mutation fixtures before `S2` closes | **applied** — the file being retired is the home of `citation-enforcer-resolves-projected-instance-paths-against-the-checkout` and `citation-mutation-fixtures-never-turn-red-on-windows`, and the second **is** a mutation fixture that never turned RED on Windows; each of the five is proven RED-then-green **on the matrix**, both ids cited by id in the done criterion | FR10 cross-platform paragraph · T-050-19 |
| `qa-engineer` | **QA-Q7** | `QUALITY.md`'s rewrite reconciles the LARGE-cap 3-number contradiction into one source | **applied** — verified at HEAD (`PARAMETERS.md:10` = 30, `tests/AGENTS.md:69–71` = 30, `quality-assurance.md:79,208` = 100); per the operator's directive the decision is taken **now**: `PARAMETERS.md`'s **30** is the number and its only home, the other two statements are **deleted**, and V29 goes RED on a second numeric cap | **A18.6** · **V29** · FR18 one-number paragraph · §5 |
| `qa-engineer` | **QA-Q8** | Record the e2e directory-vs-marker mismatch (42 vs 15) as known drift | **applied** — recorded inside **V30** as measured known drift with its 2.8× selector consequence stated, and the fix routed to intake (A18.3 keeps the correction out of this release) | **V30** · §5 closure obligations · §4.9 |
| `qa-engineer` | **QA-Q9** | Add `V-MUT`: one mutation-baseline pass over `core/` | **applied** — **V31**/**A22.11**, floor recorded and ratcheting up only, zero-kill tests dispositioned at closure, and the availability caveat carried verbatim: `mutmut` was **unverified, not absent**, so an unreachable binary yields `null` **with its reason**, never a fabricated score | **V31** · **A22.11** · T-050-03, T-050-34 |
| `qa-engineer` | **QA-Q10** | T-050-09's tests carry `Intent: SCAFFOLD — expires: <release>` | **applied**, and split correctly against SA-Q4: the `core/bug_provenance.py` tests are **CONTRACT** (the function outlives the migration), only the `migrate_v5` adapter/runner tests are **SCAFFOLD — expires: 0.6.0**, with renewal by an explicit verdict and **V28** turning an unrenewed expiry RED | FR3 `Tests:` line · **V28** · T-050-09 |
| `qa-engineer` | **QA-Q11** | FR1's tasks name at least one existing test file each retires or supersedes | **applied** — FR1's `Tests:` line names the scaffold `README.md` presence assertions and the `assets/.gitkeep` assertion in `tests/unit/features/specs/test_scaffolder.py`, and the double-`upgrade` fixture is **not added** because A1.4 is now a zero-diff assertion | FR1 `Tests:` line · **A1.4** · T-050-05 |
| `qa-engineer` | **QA-Q12** | File the private-import ratchet and the intent-header extension as backlog candidates for a companion release | **applied-modified — the operator's mandate pulls them forward.** Both are adopted **in 0.5.0** as **test-suite ratchets** in one contract file (T-050-18A), with the A18.3 conflict resolved in writing rather than by scope-shifting: A18.3 governs **product** checks; these measure the suite. What still routes to intake is the *residue* — a private-import count above 0, and the CI-scope extension of `check_test_intent_declared.py` beyond `tests/e2e/**` | **V26**, **V27** · **A18.3** boundary paragraph · §3 standing rules · §5 intake candidates · T-050-18A |

**Pass-3 tally.** 22 items · **19 applied · 3 applied-modified** (SA-Q5, QA-Q5, QA-Q12 — each
with its deviation named) · **0 rejected**. Two new operator-gated assumptions (**AS-16**,
**AS-17**), one new bounded requirement (**FR10A**), one new task (**T-050-18A**) plus
**T-050-19A**, eleven new validations (**V25–V35**), four new invariants (**A22.9–A22.12**).
Three reviewer figures were corrected against the tree rather than transcribed: the
independence gap (**4 of 24**, not 5 of 25), the `BugEvent` file census (**9**, not 8) and the
fifth "missing" package `workspace_*` (both `workspace` and `workspace_clean` are listed).
`software-architect`'s architecture-fidelity **FAIL** rests on three findings — the three
`BUGS.jsonl` writers (SA-Q1), the derivation's placement (SA-Q4) and the caller-less findings
store (SA-Q10/§6) — plus the untrue independence contract (SA-Q8); **all four are closed
above**, which is the condition the verdict names for the gate to pass.

### 9.4 Verification (2026-08-26) — `software-architect` review 2, **APPROVE-DEFINITION**

`reviews/software-architect-full-quantitative-review-2.md` re-checked every §9.3 claim against
the tree and closed nine of the ten Q-items; **Q9 (test economy) stayed PARTIAL** on the
accounting, not the architecture. Three dispositions, all textual, all carried here:

| # | Amendment | Disposition | Where |
|---|---|---|---|
| **V-1** | FR22's `Tests:` line must read `+5 / −0 (T-050-18A)` — the ratchet file's five functions were attributed to no FR, so the roll-up understated itself | **applied** | FR22 `Tests:` line · **A22.9** |
| **V-2** | T-050-21A states a **floor** for its `−N` from the 26+4 census, so the roll-up sums to a number the operator can compare with 1 859 | **applied-modified — the floor is honest, and it does not reach ≤ 0.** Inspected today, exactly **two** census files have the retired parser as their *whole* subject (`test_active_md_schema_v2.py` **1** function; `test_cli_specs_segments.py` **2**), so the floor is **−3**, not a number chosen to make the sum land. The roll-up therefore reads **+61 / −35 = +26** and is written into A22.9 as a declared overshoot with its shortfall named; the remaining −26 is what the mixed-subject per-file verdicts and the closure demotion map must produce, exactly as A22.9's protocol says. Inventing a larger floor to close the arithmetic on paper would be the accounting defect the review exists to remove | FR4 `Tests:` line · **A22.9** · T-050-21A done criterion |
| **V-3** | AS-17's exposure is quantified but uncapped — ask **T-050-34** to report the bugs registered with `surface: public-assets` during `S1`–`S4` (free with FR16's metric 4) | **applied** | **AS-17** · T-050-34 report line |

**What this fold does not change:** no requirement, no acceptance beyond A22.9's added
sentence, no task write set, no ruling, no assumption, no validation, no number that describes
the tree. Both of the review's gates (root-cause, architecture-fidelity) already read **PASS**;
its verdict is **APPROVE-DEFINITION** with these amendments carried into the promotion commit.

---

## 10. Approval

Approving this SPEC ratifies, as written: **D1–D15** as carried in §2.1; the authoring
decisions **D-A … D-J**; the **seventeen** stated assumptions **AS-1 … AS-17** — including
AS-1's re-decided answer to the handoff's open reconciliation, AS-11's placement of the lineage
check, **AS-12's recorded `S4` memory window**, AS-13's release-id disambiguation, AS-14's
U+2028 precondition, AS-15's ruling-preserving verdict-gate fix, **AS-16's one write seam** and
**AS-17's named public-assets deferral**; the six-entry pick with **no bug picked**; the
destructive deletion of root `specs/_archive/` under FR6 with the operator present; the honest
net-additive accounting of §3 and A22.3 **against a net-non-positive test suite (A22.9)**; and
**all four review folds (§9.1, §9.2, §9.3, §9.4)** — including the single reviewer amendment fold 1
refuses (SA-11, `--recipe`, whose rejection pass 2 accepted on the merits, with A1.3's
condition), the ten pass-2 items and the twenty-two pass-3 items, all applied or
applied-modified with their deviation named.

**Four items need the operator specifically:** **AS-12** (the `S4` memory window, or its stated
fallback), **AS-16** (the write seam's exposure — `bugs update` recommended), **AS-17** (the
three deferred public-assets engines) and **FR20** (no agent may accept an ADR).

**Status:** Em revisão — authored 2026-08-26; folded **four times** the same day: five
definition reviews (§9.1), the two blocking re-reviews (§9.2 — `software-architect`
REWORK-targeted and `security-reviewer` **APPROVED**, ten textual items), and the two
quantitative reviews (§9.3 — `software-architect` **REWORK** with ten ranked changes and
`qa-engineer`'s twelve test-minimization amendments, **22 dispositions, none dropped**), and
the **verification fold** (§9.4 — `software-architect` **APPROVE-DEFINITION**, three textual
amendments, one applied-modified because the honest floor does not close the arithmetic).
**Awaiting the operator**, who reviews next and flips this to `Aprovado` at promotion.
