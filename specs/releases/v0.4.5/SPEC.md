# SPEC — Release v0.4.5 — hardening and consolidation

**Status:** Aprovado
**Release ID:** v0.4.5
**Owner:** product-engineer
**Opened:** 2026-08-24
**Created:** 2026-08-24
**Branch:** `feature/0.4.5` (cut from `main` at the shipped v0.4.4 — the v2 contract, no
exception; branch model: `DADAIA.md` §4, operations: `dd-gitflow-default`)
**Consumes:** atomic-write-primitive-consolidation, byte-golden-test-inventory-roster-split,
coupled-inventory-shared-oracle, scan-test-vacuity-guard, doctor-slug-ownership-uniqueness,
bug-append-write-time-denylist-redaction, specs-init-symlinked-target-refusal,
bug-event-control-character-sanitation, always-on-token-diet, memory-catalog-digest-trimming,
persona-line-ceiling-trim, ai-surface-hygiene-residuals, intent-taxonomy-vocabulary-ruling,
dadaia-references-doctor-sanction
**Picked set:** the **8 open bugs** at pick time (zero HIGH/CRITICAL) **plus 14 of the 26
`## ACTIVE` backlog entries** — themes **A** (4), **B** (4), **C** (5 of 6) and **E** (1) of
the operator-adjudicated 2026-08-24 intake. Six bugs are solved in-release as Arm B on
`feature/0.4.5`; one (`bug-event-field-with-unicode-line-separator-silently-drops-the-event`)
is **bundled into FR7**; one (`two-atomic-writers-leak-temp-file-on-injected-os-replace-failure`)
is **superseded** by `atomic-write-primitive-consolidation` (§7). No audit is outstanding —
both 2026-07 audits are archived and fully dispositioned (v0.8.0).
**Grill (mandatory, done):** the operator's ratification session of **2026-08-24** — the
pre-SPEC grill for this release. Its five rulings are carried below as **O1–O5** and are
not re-litigated here. Residual micro-questions surfaced while authoring are recorded as
**stated assumptions** (§2.3), never as blockers.

---

## 1. Problem and context

v0.4.4 shipped a large reorganization of the core: the gitflow contract v2, the
rules→skills governance map, the skills consolidation, associated repos, an anti-loop pair
for Arm B, and a thirteen-bug sweep. It shipped **honestly incomplete** in three measured
places and left a bug ledger that grew while it was in flight:

1. **Measured misses, recorded not papered over.** Always-on load landed at ~8.2k tokens
   against an A21.9 acceptance of ≤3.5k, negations still above 60; the bound-session
   injection prefix measured ~2.78k against a ≤0.7k target; four of nine personas stayed
   above the 220-line ceiling with each overflow justified inline.
2. **Structural residuals the reviews and the architect rulings named but did not
   execute.** Eight near-identical atomic writers plus three inline `.tmp` writers; three
   hand-kept test inventories that drift apart (they produced two v0.4.4 bugs); two byte
   goldens carrying a file inventory they exist only to pin policy for; ~15 tree-walking
   scan tests with no vacuity guard.
3. **Gate and seam gaps the security review classed as recurrences.** The write-time
   bug-append redaction seam cannot see what the push-time seam refuses (third recurrence
   of the privacy-leak-into-committed-material class inside one release); the explicit
   `--specs-dir` branch of `specs init` still follows a symlinked target (CWE-59 class);
   control characters survive the bug-event round-trip (CWE-117); registry slug-ownership
   enforcement at the two write seams never heals a pre-existing colliding registry.

Alongside these, **8 bugs stand open** — zero HIGH, zero CRITICAL — and two of them are
the same surface twice: the SDD gate LAW-classifies **any** `repos/<slug>/AGENTS.md` while
the scaffold template shipped by the same library tells the agent to edit that file
directly. Under the operator's standing order, two open bugs on one surface are one
structural cause, not two patches.

This release is therefore **not** a feature release. It is the hardening and consolidation
round: close the open ledger at the root, execute the structural consolidations the
rulings already named, close the three gate/seam gaps, and run the token-economy program
that the measured misses demand. Everything it touches already exists; almost everything
it does is a deletion.

---

## 2. Objective, and the decisions that shape it

**Objective.** Leave the workspace with an empty open-bug ledger at a lower bug surface
than it had, one atomic-write primitive instead of eleven, one shared oracle instead of
three hand-kept inventories, three closed gate/seam lanes, and a measured, honest number
for the always-on budget — **without publishing a package**.

### 2.1 Operator rulings, ratified as given (O1–O5)

| # | Ruling | Recorded |
|---|---|---|
| **O1** | v0.4.5 is **hardening & consolidação**: the open-bug sweep + intake themes **A** and **B** + the token-economy program + the ROOT-4 ruling. Explicitly **not** this release: nine-skill execution, cli-help architecture, specs-canon-v6, entity-behavior-map — all four stay `ACTIVE` | operator, 2026-08-24 (also intake ruling R1) |
| **O2** | All **15** candidates of the v0.4.4 intake report are approved; they were materialized into `## ACTIVE` on 2026-08-24 | operator, 2026-08-24 (intake adjudication) |
| **O3** | The nine-skill study dispositions (Update×5, Merge×3, Fuse×1, zero Retire) are **ratified as provenance**; execution needs its own release pick and does not happen here | operator, 2026-08-24 (also intake ruling R2) |
| **O4** | `.dadaia/references/` is the **sanctioned** home for operator-placed reference material; the doctor learns it | operator, 2026-08-24 (also intake ruling R3) |
| **O5** | **RELEASE LAW — v0.4.5 does not publish to PyPI.** Ship means merge to `main` only. The release workflow's "Approve release to PyPI" gate is left deliberately unapproved; publication awaits a separate operator order | operator, 2026-08-24 |

### 2.2 Authoring decisions taken by `product-engineer` (D1–D8)

- **D1 — One flat `TASKS.md`.** Segments `S1 … S4` are blocks inside one marker surface;
  `ACTIVE.md` carries **no** `segment:` line. Same shape as v0.4.4.
- **D2 — The AGENTS.md-vs-gate pair is one investigation.** `sdd-gate-blocks-fresh-repo-root-agents-md`
  and `repo-agents-md-law-gate-contradicts-template` are the same structural cause seen from
  the gate side and the template side. **FR1** is one root-cause fix at one predicate; both
  bugs get their own `resolved` event citing that one cause. A second code path, a flag or a
  per-repo exception list would be a puxadinho and is refused.
- **D3 — The unicode line-separator bug is bundled into FR7**, not swept separately: it and
  the ESC-family finding are one control/format-character sanitation pass at the same
  bug-event seam. One fix, two records.
- **D4 — `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` is SUPERSEDED**
  by `atomic-write-primitive-consolidation` (FR2), per the architect ruling that the
  structural fix absorb it rather than a two-call-site patch. The `superseded` event is
  appended in the **definition commit**.
- **D5 — The atomic-write primitive's home is `core/atomic_write.py`**, added to the core
  file-I/O ratchet-authorized set with its rationale recorded on the entry. This follows the
  existing `core/specs_repair` precedent — *"the single home both repair surfaces may import
  without a forbidden sibling edge"*. It satisfies both constraints the backlog entry
  demanded be adjudicated in writing: (a) `features/**` may import `core/**`, so no
  cross-feature import and no `features → infrastructure` edge is created; (b) the primitive
  is stdlib-only and imports no container, so the **hooks-never-import-container latency law
  holds** and **no sanctioned duplicate in `hooks/_common` is required**. `software-architect`
  rules on this at the head of `S2` (**AR-1**); if the ruling overturns it, the fallback is
  one sanctioned import-light duplicate, stated in writing in `CLOSURE.md` with its reason.
- **D6 — Ship without publish (mechanism, stated once).** `pyproject.toml` bumps
  `0.4.4 → 0.4.5` at the final `rc` per the one-axis law. The merge to `main` fires
  `release.yml`, whose `approve` job blocks on the `release-gate` GitHub environment; that
  approval is **withheld**, so `publish` never runs and **no `v0.4.5` git tag is created**.
  The number is minted locally and unpublished — the second such mint after `0.4.3`. §2.4
  records the tension this creates with the one-axis law.
- **D7 — `expand → switch → contract` for every demolition.** FR2, FR3 and FR4 each delete
  a surface. Each lands as: add the new path; switch every consumer; only then delete the
  old one — each step independently green. A demolition that arrives as one big-bang commit
  is refused at review.
- **D8 — The `rc` lane.** `S1 … S4` are internal work boundaries on `feature/0.4.5`, each
  closed by a `qa-engineer` review **committed on the branch** — no merge, no PR, no `rc`
  burned. `rc-1` burns when the whole scope is implemented, gate-green and closed by QA and
  is merged into `develop`. `rc-2 … rc-N` are adjustment rounds on that same scope, found by
  testing the merged `develop`; **no new backlog ever enters an `rc`**. The final `rc`
  carries memory → CLOSURE → archive and ships. If nothing is found, the final `rc` **is**
  `rc-1`. (The **definition PR** that opens once SPEC/PLAN/TASKS are `Aprovado` is milestone
  (a) and burns no `rc` — `DADAIA.md` §4 names it as a distinct develop-advancing PR.)

### 2.3 Stated assumptions (residual micro-questions, non-blocking)

| # | Assumption | Why it is safe |
|---|---|---|
| **AS-1** | **`persona-line-ceiling-trim` is executed against the sibling mechanisms that already exist**, not against the ones `nine-skill-study-execution` would create. Its entry sequences it "after C1"; C1 is not picked (O1) | The trim is bounded to relocating justified content into already-disclosed skill siblings. FR13's acceptance is a **measured reduction with a coverage table**, not "all four under 220" — an unreachable number would be a dishonest acceptance |
| **AS-2** | **`intent-taxonomy-vocabulary-ruling` is executed directly on `dadaia-test-stewardship`'s taxonomy section**, though its entry says execution "rides the C1 stewardship-skill update" | The ruling is a vocabulary decision, complete in itself; it does not pre-empt C1's later Update, which rebases on this text (the entry's own "adjudicate together" is satisfied by O3 having ratified C1's disposition first) |
| **AS-3** | **`always-on-token-diet` is consumed by executing and measuring the pass**, not by reaching ≤3.5k. If the measurement lands short, CLOSURE records the number, the operator rules, and the residual — if any — goes to the PM's intake report | v0.4.4 already proved the target is not reachable in one pass; restating it as a hard acceptance would make the release fail on a number rather than on its work |
| **AS-4** | **`doctor-slug-ownership-uniqueness` is consumed by either outcome** — the invariant added, or an explicit recorded rule-out in one paragraph | The entry itself asks for a decision, not necessarily an implementation |
| **AS-5** | **`windows-xdist-workers-crash-on-unit-fast-tier` may end the release still open.** It gets a bounded root-cause attempt; if that is inconclusive, `qa-engineer` issues an evidence-backed quarantine verdict, `software-engineer` executes it, and the bug **stays open and unpicked** — never closed by a quarantine | `dd-release-definition` §2: a bug that is neither fixed nor subsumed is not picked and is left open. A quarantine is not a resolution |

### 2.4 The version axis, recorded honestly (ADR — the no-publish tension)

**Decided.** The release id is `v0.4.5`; `pyproject.toml` bumps to `0.4.5` at the final
`rc`, per the one-axis law (`[[pypi-distribution]]`: a release id **is** the version that
release mints). **The PUBLISH step is withheld by operator order O5.**

**Rejected.** (a) Not bumping `pyproject.toml` — that would put the release id and the
package version on two axes, which is exactly the split the one-axis law exists to prevent.
(b) Naming the release something other than a semver id — releases are `major.minor.patch`
(`DADAIA.md` §6). (c) Publishing anyway because the pipeline is automated — the pipeline's
`approve` job exists precisely so a human decides.

**The tension, stated rather than hidden.** The one-axis law reads "the `pyproject.toml`
version tracks the published PyPI lineage". After this release that sentence is true of the
**lineage**, not of `HEAD`: the published lineage stays `0.4.2 → 0.4.4` while `main` reads
`0.4.5`. This is the same shape as the retired `0.4.3` mint, and it is now a **repeated**
shape, not an accident — so it is recorded as product truth in memory at closure rather
than as a footnote. `0.4.5` may later be published by a separate operator order, or be
superseded by a higher number; nothing here forecloses either.

**Revisit when.** The operator gives the publish order, or a third unpublished mint occurs
— at which point the one-axis law's wording is the thing to fix, not the release.

---

## 3. Scope

**Standing rules for every segment.**

- **Green at every commit:** `dadaia ci preflight`, `dadaia backlog doctor`,
  `dadaia specs doctor`, `dadaia public doctor`. **No `--no-verify`, ever.**
- **RED before GREEN**, on the executed path (`DADAIA.md` §7).
- **The standing order is an acceptance, not a preference.** Every task leaves the touched
  feature **smaller or equal** in surface. A fix that adds a branch, a flag, a second code
  path, a cross-feature reach-in or a new side effect is refused, whatever the test result.
  Every review verdict states, with bug-history evidence, whether the change reduced or
  increased the bug surface of the feature it touched. "Tests green" is not a verdict.
- **This release is net-negative in production LOC and in AI-surface lines.** It
  consolidates and diets; nothing here is additive by nature. A positive net in either
  accounting is a defect of the release, justified per contributing FR or refused (FR16).
- **Measurement rule.** `product-engineer` has no shell. Every number this release asserts
  is produced by a named task step run by an agent with a shell and captured under
  `.dadaia/tmp/<agent>/<YYYYMMDD>/`.
- **Bug work runs under `dd-bug-fix` and v0.4.4's FR23 evidence gate — they are law now,
  not release scope.** Every `resolved` event carries the three required evidence fields.
- **Zero-hit greps** exclude `specs/_archive/**`, `specs/bugs/**`, `specs/backlog/**`,
  `specs/releases/v0.4.5/**`, `CHANGELOG.md` and `.dadaia/{reports,handoff,tmp}/**`.
- **Test intent at birth**, per `dadaia-test-stewardship`. **Zero new `tests/e2e/**`**
  without a named `qa-engineer` exception recorded in that segment's QA artifact.
- **No home-absolute path, operator email literal or denylisted term** enters any authored
  file — the class recurred three times in v0.4.4 and FR6 exists because of it.

---

### Segment `S1` — the open-bug sweep (Arm B on `feature/0.4.5`)

Lands first: it is the smallest surface, it stabilizes the tree the consolidations rewrite,
and its lead item changes the **gate that classifies every write** the rest of the release
performs.

#### FR1 — The LAW path class covers projected law, not every file named `AGENTS.md` · **size M**

*Bugs: `sdd-gate-blocks-fresh-repo-root-agents-md` (MEDIUM) + `repo-agents-md-law-gate-contradicts-template` (MEDIUM) — one cause, per D2.*

`gate_policy._is_law_path` matches the basename `AGENTS.md` unconditionally for any
`repos/<slug>/` path, with no manifest-tracked or previously-projected check. The library's
own scaffold template for that same file says *"edit this file directly — NOT
lib-originated"*. The gate and the template state opposite contracts about one file; an
agent can neither maintain it nor route the change through `public/`.

The structural cause is that the classifier decides **by name** what the law defines **by
origin**. The fix is one predicate: a path is LAW when it is the workspace-root law family
(`DADAIA.md`, `AGENTS.md`, `CLAUDE.md` at the root) **or** it is listed in
`.dadaia/agentic/manifest.json` as a lib-originated projection. A repo's own
domain-scoped `AGENTS.md` — fresh or existing, tracked or not — classifies MUTATING.

**Acceptance**
- A1.1 RED first, on the executed path: a `Write` of `repos/<fresh-slug>/AGENTS.md` in a
  brand-new repo with no prior projection is BLOCKed before the fix and proceeds after it.
- A1.2 RED first: an `Edit` of an existing, **non-manifest-tracked** `repos/<slug>/AGENTS.md`
  is BLOCKed before and proceeds after.
- A1.3 The workspace-root law family and **every** manifest-tracked projection stay LAW —
  proven by a contract test enumerating the manifest, not by inspection.
- A1.4 **One** predicate carries the decision. No per-repo exception list, no flag, no
  second classification path — proven by the diff being net-negative or flat in
  `gate_policy.py`, and by the reviewer's bug-surface verdict.
- A1.5 The scaffold template's "edit this file directly" wording and the gate now state the
  **same** contract, proven by grep of both surfaces.
- A1.6 Both bug ids receive a `resolved` event naming the one shared root cause.

#### The five remaining sweep items (no FR — Arm B, `dd-bug-fix` + the FR23 evidence gate)

| Bug | Sev | Disposition in `S1` |
|---|---|---|
| `dadaia-task-manager-stale-workspace-protocol-citation` | LOW | Fix the citation at source (`public/skills/dadaia-task-manager/SKILL.md` cites §1 for content living at §3), re-project. Fixing it via Arm B does **not** pre-empt the ratified C1 disposition (O3) |
| `certify-skip-detail-leaks-full-codex-output` | LOW | Detail carries only the parsed `error.message`, length-capped, through the redaction helper — same for the FAIL branch (CWE-532) |
| `codex-probe-unit-fixture-carries-real-session-uuid` | LOW | Synthetic UUID in the fixture |
| `windows-xdist-workers-crash-on-unit-fast-tier` | LOW | Bounded root-cause attempt; **AS-5** governs the inconclusive outcome |
| *(carried)* `bug-event-field-with-unicode-line-separator-…` | MEDIUM | **Not here** — bundled into FR7 (D3) |

---

### Segment `S2` — structural consolidation (theme **A**)

#### FR2 — One atomic-write primitive replaces eleven writers · **size M**

*Entry: `atomic-write-primitive-consolidation` · supersedes bug `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` (D4).*

Eight near-identical named atomic writers (`hooks/_common.atomic_write_text`,
`infrastructure/public_assets_common._atomic_write_text`,
`features/migrate/frontmatter_keys.write_text_atomic`,
`features/specs/doctor_structural._write_text_atomic`,
`features/spec_context/session_identity._atomic_write_text`,
`features/spec_context/presence._atomic_write_json`, and the
`_atomic_write`/`_atomic_write_bytes` pair in
`infrastructure/json_agent_model_policy_store`) plus **three inline `.tmp` writers**
(`features/migrate/state_v2.py`, and two in `features/import_/service.py`) collapse into
**one parameterized primitive** at `core/atomic_write.py` (D5): preserve-mode on/off,
LF-bytes/binary, and **temp-cleanup-on-any-failure always**. Executed
`expand → switch → contract` (D7).

**Acceptance**
- A2.1 `software-architect` **AR-1** ruling on the home is recorded before the first
  consumer switches; if it overturns D5, the fallback duplicate and its reason are written
  into `CLOSURE.md`.
- A2.2 A call-site census test enumerates every atomic write in the package and asserts
  each routes through the one primitive — zero remaining named writers, zero inline `.tmp`
  writers. The census is **derived by scan**, not a hand-kept list.
- A2.3 The injected-`os.replace`-failure battery is re-pointed at the single primitive
  **before** any writer is deleted, and covers every parameter combination; the temp file is
  gone on every failure path.
- A2.4 The bug's characterization test (which pins the *leaking* behaviour as current) is
  deleted in the same commit that makes leaking impossible — a self-destructing test that
  survives its subject is slop.
- A2.5 `core/` stays stdlib-pure; `lint-imports` green with **no new accepted edge**; the
  core file-I/O authorized set gains exactly one entry, with its rationale on the entry.
- A2.6 Production LOC for this FR is **net-negative**, measured.
- A2.7 The bug carries a `superseded` event (appended at definition) and is `Closed` at the
  disposition sweep with `superseded_by: atomic-write-primitive-consolidation`.

#### FR3 — The two byte goldens pin policy; a derived roster pins the inventory · **size S**

*Entry: `byte-golden-test-inventory-roster-split` · zero production-code change.*

`test_install_target_goldens.py` and `test_public_assets_profile.py` keep a **policy-only**
byte golden. The inventory assertion moves to a roster derived by scanning
`dadaia_workspace/public/**`, so adding or removing an asset no longer forces a regen of a
golden that exists to pin policy — and a regen stops being the place an unintended change
hides (v0.4.4 **AR-1**).

**Acceptance**
- A3.1 Adding a throwaway asset under `public/` fails the **roster** assertion and leaves
  both byte goldens green — proven by an executed fixture, not by reasoning.
- A3.2 Neither byte golden contains a file inventory after the split.
- A3.3 Zero production-code lines change.

#### FR4 — One shared skill-inventory oracle replaces three hand-kept inventories · **size S**

*Entry: `coupled-inventory-shared-oracle` · this seam produced two v0.4.4 bugs.*

`test_public_pipeline.py` (`EXPECTED_SKILLS`), `test_public_assets.py` (path assertions) and
`check_skill_orphans.py` (roster) each keep their own inventory. One derived oracle replaces
all three.

**Acceptance**
- A4.1 The three hand-kept inventories are **deleted**; all three consumers read the one
  oracle.
- A4.2 A single skill add/rename/remove is green everywhere after touching **one** place —
  proven by an executed fixture.
- A4.3 The oracle is derived from the source tree, never a literal list.
- A4.4 Net-negative test LOC, measured.

#### FR5 — A vacuity guard convention for the tree-walking scan tests · **size S**

*Entry: `scan-test-vacuity-guard` · deliberately **not** a shared harness (the v0.4.4
S5-FR23 ruling evaluated and rejected one).*

Each of the ~15 tree-walking source-scan tests asserts (a) the enumerated population is
non-empty and (b) one known sentinel file is in it, so a future mis-rooted walker cannot
pass vacuously green forever.

**Acceptance**
- A5.1 Every tree-walking scan test carries both assertions; the census of such tests is
  produced by scan and recorded.
- A5.2 A deliberately mis-rooted walker turns each of them RED — proven on at least three
  sampled tests.
- A5.3 No shared harness or base class is introduced (the ruling stands); the helper is a
  two-line convention.

---

### Segment `S3` — gate, doctor and seam hardening (themes **B** + **E**)

#### FR6 — Write-time bug-append redaction sees what the push gate refuses · **size M**

*Entry: `bug-append-write-time-denylist-redaction` · third recurrence of the class.*

`core/models/bugs.redact_text` knows IPv4 and home-path patterns; the operator denylist is
consulted only at push time by `infrastructure/privacy_check.load_privacy_terms`. Inside
v0.4.4 alone this cost two committed leaks caught only at the push gate, one of which forced
an `rc-1` history rewrite. The denylist loader becomes a **single loading seam** consumed by
both the write-time redaction and the push-time scan.

**Acceptance**
- A6.1 RED first: appending a bug event whose free-text field carries a denylisted term
  writes the raw term before the fix and a masked term after it.
- A6.2 **One** loader, consumed twice — no second reader of the denylist file, proven by
  grep and by the diff.
- A6.3 The push-time scan is **unchanged in behaviour** (complements, never replaces) —
  proven by its existing fixtures staying green untouched.
- A6.4 The denylist data stays operator-local and never enters `public/**` —
  `dadaia public doctor` reports `[ok] public-privacy`.
- A6.5 Masking is applied to every free-text field the ledger accepts, enumerated by the
  schema, not by a hand-kept field list.

#### FR7 — One control/format-character sanitation pass at the bug-event seam · **size S**

*Entry: `bug-event-control-character-sanitation` · **bundles** open bug
`bug-event-field-with-unicode-line-separator-silently-drops-the-event` (MEDIUM) — D3.*

Two symptoms, one seam. `append_event` serialises with `json.dumps(ensure_ascii=False)`, so
a raw U+2028/U+2029 lands inside the JSON string, and `iter_events` reads with
`splitlines()`, which splits on it — the record becomes two unparseable fragments while the
CLI has already printed `[ok] appended` (**silent event loss**). Separately, ESC survives
the round-trip and `bugs status` renders titles raw (**CWE-117**, spoofed CLI output).

**Acceptance**
- A7.1 RED first: an event whose field contains U+2028 is appended and then **read back
  intact** by `bugs status`/`bugs stats`; before the fix it is absent.
- A7.2 RED first: an event whose title contains ESC renders with no raw control character.
- A7.3 The sanitation is **one pass at one seam**, covering the ESC family and the Unicode
  line/paragraph separators together — not two independent guards.
- A7.4 Every historical event in `specs/bugs/bugs.jsonl` still parses after the change —
  proven by a full read of the live ledger, and no historical event is rewritten.
- A7.5 The bug receives a `resolved` event carrying the three FR23 evidence fields.

#### FR8 — `specs init --specs-dir` refuses a symlinked target · **size S**

*Entry: `specs-init-symlinked-target-refusal` · same CWE-59 class the v0.4.4 resolver seam
closed, smaller blast radius.*

**Acceptance**
- A8.1 RED first: `specs init --specs-dir <symlink>` scaffolds through the link before the
  fix and refuses after it, with the same refusal posture and message shape as the hardened
  resolver seam.
- A8.2 No new refusal vocabulary and no second symlink check — the existing posture is
  reused, proven by the diff.
- A8.3 The non-symlinked explicit branch is unaffected, proven by its existing fixtures.

#### FR9 — The healing lane for registry slug-ownership collisions is decided · **size S**

*Entry: `doctor-slug-ownership-uniqueness` · AS-4 governs the two admissible outcomes.*

Enforcement at the two v0.4.4 write seams (`add_repo`, `create`) never heals historical
state: the v2→v3 migration imports whatever the v2 registry says, so a pre-existing
colliding registry migrates its collision in.

**Acceptance**
- A9.1 Either a registry-wide slug-ownership-uniqueness invariant exists in the doctor lane,
  with a fixture proving a pre-existing collision is reported (and, if the decision includes
  it, healed) — **or** a one-paragraph rule-out is recorded in `CLOSURE.md` naming the
  reason and the residual risk.
- A9.2 Whichever outcome, the F-1/F-12 class has no remaining undecided lane — stated
  explicitly.
- A9.3 If the invariant lands, it is **one** check in the existing doctor lane, not a new
  doctor surface.

#### FR10 — The doctor learns `.dadaia/references/` · **size S**

*Entry: `dadaia-references-doctor-sanction` · operator ruling **O4**.*

`.dadaia/references/` is recognized as a legitimate operator-owned subtree: never flagged,
never GC'd, never treated as a managed context. The encoding states explicitly that
**reference clones are outside the context lifecycle** — no lifecycle verb may ever act on
one (prior history: lifecycle verbs acting on foreign trees destroyed work).

**Acceptance**
- A10.1 A workspace carrying `.dadaia/references/<clone>/` reports doctor-clean.
- A10.2 A test asserts the outside-context-lifecycle clause on the executed path: no
  lifecycle verb resolves, binds, alives, deads or GCs a reference clone.
- A10.3 The sanction is an allowlist line or the documented `.dadaia/`-level equivalent —
  **one** place, not a rule repeated per verb.
- A10.4 `specs/` is untouched by this FR (the ruling is about `.dadaia/`).

---

### Segment `S4` — the token-economy program (theme **C**)

The three entries `always-on-token-diet`, `memory-catalog-digest-trimming` and
`persona-line-ceiling-trim` shave **one** budget and are executed as one program, in that
order: measure the baseline once, cut the dominant contributor first, re-measure after each
cut. Two hygiene items ride along.

#### FR11 — The always-on diet pass, measured · **size M**

*Entry: `always-on-token-diet` · AS-3 governs consumption.*

A dedicated diet pass across `DADAIA.md` (source only), the personas and the always-on
rules, toward the A21.9 acceptance of **≤3.5k always-on tokens** and **≤60 negations**
(v0.4.4 landed ~8.2k and >60, from a ~8.4k/160 baseline).

**Acceptance**
- A11.1 Baseline and post-pass numbers are **measured** (never estimated) for both the token
  count and the negation count, with the capture path recorded.
- A11.2 A **coverage table** accompanies the pass: every removed block → the surviving home
  that carries it. **No law is dropped silently.**
- A11.3 A pointer replaces a restatement; a restatement never replaces a pointer.
- A11.4 If the target is missed, `CLOSURE.md` states the number, the reason and the operator
  ruling — an honest miss, never a redefined target.

#### FR12 — The catalog digest is trimmed, paged or tiered · **size M**

*Entry: `memory-catalog-digest-trimming` · the dominant single contributor to the
bound-session overage.*

The bound-session injection prefix measured ~2.78k tokens against a ≤0.7k target; the root
cause is the 28-entry `catalog.json` digest. The remedy is **catalog curation policy** —
trim, page or tier the digest. Explicitly **not** a `ctx_inject` rewrite: the hook's digest
logic stays out of scope (v0.4.4 A30.3).

**Acceptance**
- A12.1 The bound-session prefix is re-measured on a **real session**, before and after.
- A12.2 `ctx_inject`'s digest logic is byte-unchanged, proven by diff.
- A12.3 Every catalog entry remains reachable — the curation changes what is *injected*,
  never what *exists*; an agent that needs an atom can still find it in one step.
- A12.4 The policy is written down where the catalog is generated, not applied by hand once.

#### FR13 — The four over-ceiling personas are trimmed · **size M**

*Entry: `persona-line-ceiling-trim` · AS-1 bounds it.*

`product-engineer` (334), `qa-engineer` (274), `ai-engineer` (273) and `software-architect`
(252) exceed the 220-line ceiling, each overflow justified inline per A29.3. Justified
content relocates into the sibling mechanisms that **already exist**.

**Acceptance**
- A13.1 Per-persona line counts measured before and after; the fleet's net is negative.
- A13.2 A **coverage table** per removed block → surviving home; a fact with no home stays,
  and its overflow justification stays with it.
- A13.3 No persona loses a write-allowlist row, a scope boundary or a hard-stop block.
- A13.4 Any persona still above 220 after the pass is named in `CLOSURE.md` with its
  remaining count and the reason — never silently accepted.

#### FR14 — AI-surface hygiene residuals · **size S**

*Entry: `ai-surface-hygiene-residuals`.*

(a) `public/agents/ai-engineer.md` cites section 5 for content that lives in section 8 — the
F-3 stale-anchor class, inside `public/**`; (b) the F-7/F-8/F-10 naming/wording residuals,
cosmetic, zero behaviour.

**Acceptance**
- A14.1 The stale citation is fixed **at source** and re-projected; `dadaia public doctor`
  green.
- A14.2 The v0.4.4 citation check (A27.20) is green at HEAD after the fix — machine-verified.
- A14.3 The F-7/F-8/F-10 residuals are swept in the **same** pass; zero behaviour change,
  proven by the suite.

#### FR15 — The test-Intent vocabulary is ruled · **size S**

*Entry: `intent-taxonomy-vocabulary-ruling` · AS-2.*

Eight `REGRESSION` and three `BUG` Intent declarations sit outside the stewardship taxonomy.
Either admit the two tokens into the taxonomy or sweep the 11 declarations onto existing
tokens — one decision, encoded in `dadaia-test-stewardship`.

**Acceptance**
- A15.1 The ruling is written into the skill's taxonomy section — one canonical vocabulary,
  stated once.
- A15.2 Zero off-taxonomy Intent declarations remain, proven by the existing enforcement or
  by a scan whose zero-hit result is recorded.
- A15.3 The change does not pre-empt the ratified C1 `dadaia-test-stewardship` Update (O3) —
  stated in `CLOSURE.md` so the later release rebases rather than reverts.

---

### The `rc` lane — `rc-1 … rc-N` (D8)

Not a scope block: the lane is what happens to the **whole** scope once `S1 … S4` are done.

#### FR16 — The invariants this release must not break · **size S**

- A16.1 `dadaia ci preflight`, `dadaia doctor`, `dadaia specs doctor`,
  `dadaia backlog doctor` and `dadaia public doctor` green; `specs doctor` **0 errors**.
- A16.2 Layer rules hold: `features/**` imports neither `cli`, `infrastructure` nor `hooks`;
  `core/**` stays stdlib-pure; `lint-imports` green with **no new** accepted edge.
- A16.3 **Production LOC net for the release is negative.** This release consolidates; no
  segment is additive by nature. A positive net requires a written justification per
  contributing FR (FR2, FR4 and FR13 are the deletion engines).
- A16.4 **AI-surface lines net-negative** over `public/{agents,skills,data,entities}/**`
  (the v0.4.4 A21.8 invariant, which holds for every release after it).
- A16.5 Complexity ceilings (`C90`, `PLR1702`) unchanged or **lowered** — never raised.
- A16.6 Residual budget: every picked bug terminal or explicitly left open per AS-5; every
  picked entry dispositioned; residuals compiled into the PM's intake report, never
  materialized by an agent.
- A16.7 **Every `rc` holds A16.1–A16.6**, and every `rc-N ≥ 2` traces to a defect or
  adjustment **on this scope**, named with where it was found on `develop`.
- A16.8 **No PyPI publication occurs** (O5): after ship, `release.yml`'s `approve` job is
  pending-unapproved, no `v0.4.5` tag exists, and PyPI's latest published version is still
  `0.4.4` — each verified and recorded.

---

## 4. Out of scope (non-goals)

1. **`nine-skill-study-execution`** — its dispositions are ratified as provenance (O3);
   execution needs its own release pick. Stays `ACTIVE`.
2. **`cli-help-architecture-and-session-injection`** — stays `ACTIVE` (O1). No CLI help
   architecture, no help-digest verb, no new `SessionStart` matchers here.
3. **`specs-canon-v6`** and **`entity-behavior-map`** — stay `ACTIVE` (O1). `ACTIVE.md`,
   `CLOSURE.md`, `bugs.jsonl` and the current `specs/` layout are unchanged by this release.
4. **The eight new skills** the 2026-08-23 skills audit proposed (`dd-diagnose`,
   `dadaia-codebase-design`, `dd-architecture-survey`, `dd-code-review`, `dadaia-glossary`,
   `dadaia-router`, `dd-tasks-as-tracer-bullets`, `dadaia-wizard`) — all stay `ACTIVE`.
   **This release creates no skill.**
5. **Publishing `0.4.5` to PyPI** (O5). Ship is the merge to `main`; the approval gate is
   left unapproved by design.
6. **A `ctx_inject` rewrite** — FR12 is catalog curation policy only (v0.4.4 A30.3).
7. **A shared harness for the scan tests** — the v0.4.4 ruling rejected one; FR5 is a
   convention (A5.3).
8. **Re-litigating a ratified ruling.** O1–O5 are given. Where a backlog entry's sequencing
   note conflicts with them, §2.3's stated assumption governs.
9. **Any FR not listed in §3.** Nothing discovered mid-release is added without an operator
   ruling at the moment of discovery. The standing exception is a **bug**, fixed on the spot
   as Arm B on `feature/0.4.5` (`DADAIA.md` §1) — never backlog demand.
10. **The archived `specs/_archive/releases/**`** — frozen, quoted only, never edited.

---

## 5. Memory files affected at closure

Written in the CLOSURE phase only, one authoring pass per atom.

| File | Change | When |
|---|---|---|
| **`specs/memory/product/sdd/sdd-gate-v3.md`** | **mandatory rewrite** — the LAW path class restated by **origin** (workspace-root law family + manifest-tracked projections), and a repo's own domain-scoped `AGENTS.md` named explicitly as MUTATING (FR1) | CLOSURE |
| **`specs/memory/product/distribution/pypi-distribution.md`** | **mandatory rewrite** — the published lineage stays `0.4.2 → 0.4.4` while `main` reads `0.4.5`; the minted-unpublished shape is now **repeated**, so the one-axis law's wording is restated to distinguish *lineage* from *`HEAD`* (§2.4, D6, O5) | CLOSURE |
| `specs/memory/architecture.md` | the one atomic-write primitive and its core file-I/O ratchet entry (FR2, D5); the persona size contract after FR13 | CLOSURE |
| `specs/memory/quality-assurance.md` | the derived roster + shared skill-inventory oracle replacing three hand-kept inventories (FR3, FR4); the scan-vacuity convention (FR5); the Intent vocabulary ruling (FR15); any quarantine carried by AS-5 | CLOSURE |
| `specs/memory/product/sdd/sdd-bug-backlog-governance.md` | the bug-event write-time redaction seam and the control/format-character sanitation (FR6, FR7) | CLOSURE |
| `specs/memory/product/platform/workspace-doctor.md` | `.dadaia/references/` as a sanctioned operator-owned subtree, outside the context lifecycle (FR10) | CLOSURE |
| `specs/memory/product/platform/context-management.md` | the slug-ownership healing lane outcome (FR9); the leaner bound-session injection prefix (FR12) | CLOSURE |
| `specs/memory/product/agents/agentic-entities.md` | the always-on budget after the diet, with its measured number (FR11); the persona ceiling state (FR13) | CLOSURE |
| `specs/memory/product/distribution/public-asset-distribution.md` | the policy-only byte goldens and the derived roster (FR3) | CLOSURE |
| `specs/memory/product/sdd/specs-doctor.md` | only if a doctor rule changed (FR8/FR9) — otherwise "no change", with the reason | CLOSURE |
| `specs/memory/product/index.md` + `catalog.json` | regenerated; `index.md` touched only if catalog order or membership changed — **and** carrying FR12's curation policy | CLOSURE |
| `specs/memory/tech-stack.md` | only if a dependency changed — otherwise "no change", with the reason | CLOSURE |

### Closure obligations (not implementation FRs)

- **Disposition sweep.** 14 `LEDGER` lines updated `CONSUMED · v0.4.5` → `DELIVERED · v0.4.5`
  (`SUPERSEDED`/`DEFERRED` where an outcome requires it) — an **update**, never a duplicate
  line (BL-DUP). Seven bugs `Closed` (six fixed + one bundled into FR7); one `Closed` +
  `superseded_by: atomic-write-primitive-consolidation`; `windows-xdist-workers-crash-on-unit-fast-tier`
  either `Closed` or recorded still-open per **AS-5**.
- **`## Size accounting`** with measured values: production LOC net, AI-surface net,
  always-on tokens, negations, bound-session prefix, persona line counts.
- **`## Ship-without-publish record`** — A16.8's three verifications.
- **Test dispositions**: every demotion, quarantine (with its bug id) and SCAFFOLD expiry.
- **The AR-1 ruling** on the atomic-write home, verbatim.
- **The `rc` ledger** — every `rc` burned, what was found on `develop`, by whom, its fix.
- **Intake candidates** — residuals compiled for the PM's operator-facing intake report;
  `product-engineer` creates no backlog entry.
- **The restated standing question** (git commit identity de-personalisation) — carried, not
  decided.
- **Archive decision:** `MOVE`.

---

## 6. Dependencies and risks

| # | Item | Status / mitigation |
|---|---|---|
| D-1 | `product-engineer` has no shell | every git, CLI and measurement step is an explicit TASKS entry owned by the dispatcher, `software-engineer`, `ai-engineer` or `qa-engineer` |
| D-2 | **`S1` before everything** — FR1 changes the classifier that gates every write the rest of the release performs | segment order + TASKS preconditions |
| D-3 | **The installed venv is not editable** — FR1's gate code is not live until the workspace venv is reinstalled | an explicit task step reinstalls into `.dadaia/.venv` and re-verifies with a refusal probe before `S2` opens |
| D-4 | **AR-1 before the first consumer switch** in FR2 | task order inside `S2`; A2.1 |
| D-5 | **FR4 before any skill-surface change** — the shared oracle cheapens every later roster change (and FR14/FR15 touch `public/**`) | `S2` precedes `S3`/`S4` |
| D-6 | **FR11 measures the baseline once, before FR12 and FR13 cut** | task order inside `S4`; A11.1 |
| D-7 | **The verdict-gate required check must be wired on both PR edges before `rc-2`** — the intake's operator-only item B1, deliberately not a backlog entry | scheduled as an `[operator]` task in W0 with an explicit due point |
| **AR-1** | **Architecture review — the atomic-write home.** D5 places the primitive in `core/` on the `specs_repair` precedent; the entry demands the SPEC adjudicate the core-I/O ratchet and the hooks-latency law in writing | `software-architect` rules at the head of `S2`; the ruling is recorded verbatim in CLOSURE; the fallback (one sanctioned import-light duplicate) is stated in writing if taken |
| **R-1** | **FR1 touches the security boundary itself.** A classifier that wrongly de-classifies a projected law file is a security regression, not a bug fix | RED-first on both bugs' executed paths **plus** A1.3's manifest-enumerating contract test; the reviewer states the bug-surface delta of the gate feature with its full bug history |
| **R-2** | **The additive risk is INVERSE here.** v0.4.4's R-2 guarded its one additive segment; this release's dominant risk is the opposite — FR2 deletes eleven writers across the package, FR4 deletes three inventories, FR3 splits two goldens, FR13 removes ~40% of four persona bodies. **A big deletion has no natural safety net.** | The net is built first, deleted-into second: A2.3 re-points the injected-failure battery at the single primitive **before** any writer is deleted; A2.2's census is derived by scan; A4.2 proves one-place-change end to end; A11.2/A13.2's coverage tables prove no fact was dropped. D7's `expand → switch → contract` is the mechanic that makes each step independently green |
| R-3 | **FR2 shrinks the battery from 8 seams to 1** — coverage per call site can silently vanish with the seams | A2.2's derived census is the coverage proof, not the battery's size; the battery must cover every parameter combination (A2.3) |
| R-4 | **FR11/FR13 can delete a law that has no other home** (v0.4.4 R-9 recurring) | coverage tables are mandatory and per removed block (A11.2, A13.2); the six-axis review reads the coverage table, not the diff alone |
| R-5 | **FR13 lands without C1's sibling mechanism** (AS-1) | acceptance is a measured reduction plus a named residual, never a number the release cannot reach |
| R-6 | **A second minted-unpublished version** (O5/D6) creates a repeated shape that folklore will misread | recorded as product truth in memory at closure (§5, `pypi-distribution.md`), stated once in `CHANGELOG.md`, and verified by A16.8 |
| R-7 | **The `rc` lane can be abused as a second pick** — testing the merged `develop` invites new demand | A16.7 + the CLOSURE `rc` ledger: every `rc-N ≥ 2` names the defect on this scope it answers; anything else is intake for a later release (§4.9) |
| R-8 | **FR6 masks more text than it should** and corrupts legitimate evidence fields | A6.3 pins the push scan unchanged; A6.5 enumerates fields from the schema; a round-trip fixture proves non-denylisted text is byte-identical |
| R-9 | **AS-5's quarantine needs a registered bug** and an unregistered pass-on-retry is a failure | the bug is already registered; the quarantine verdict is `qa-engineer`'s with evidence, executed by `software-engineer`, and the bug stays open |

---

## 7. Traceability and provenance

| Record | Provenance | Disposition in this release |
|---|---|---|
| `atomic-write-primitive-consolidation` | intake A1 (approved 2026-08-24) — S5-FR23 architect ruling; T-044-45 review | **picked** · FR2 · `CONSUMED · v0.4.5` at definition |
| `byte-golden-test-inventory-roster-split` | intake A2 — S3-AR1 ruling §4 | **picked** · FR3 · `CONSUMED · v0.4.5` |
| `coupled-inventory-shared-oracle` | intake A3 — S3-AR1 ruling §4 | **picked** · FR4 · `CONSUMED · v0.4.5` |
| `scan-test-vacuity-guard` | intake A4 — S5-FR23 ruling Firing 3 | **picked** · FR5 · `CONSUMED · v0.4.5` |
| `doctor-slug-ownership-uniqueness` | intake B2 — S5-FR23 ruling Firing 5 | **picked** · FR9 (either outcome, AS-4) · `CONSUMED · v0.4.5` |
| `bug-append-write-time-denylist-redaction` | intake B3 — security-reviewer T-044-46 round 1 | **picked** · FR6 · `CONSUMED · v0.4.5` |
| `specs-init-symlinked-target-refusal` | intake B4 — S5-FR23 ruling Firing 4 | **picked** · FR8 · `CONSUMED · v0.4.5` |
| `bug-event-control-character-sanitation` | intake B5 — security-reviewer T-044-46 round 1 | **picked** · FR7 (bundling the MEDIUM bug, D3) · `CONSUMED · v0.4.5` |
| `always-on-token-diet` | intake C2 — T-044-44 gate capture vs A21.9 | **picked** · FR11 (AS-3) · `CONSUMED · v0.4.5` |
| `memory-catalog-digest-trimming` | intake C3 — S3 qa-close A30.2 (FAIL, measured) | **picked** · FR12 · `CONSUMED · v0.4.5` |
| `persona-line-ceiling-trim` | intake C4 — S3 qa-close A29.1 (PARTIAL) | **picked** · FR13 (AS-1) · `CONSUMED · v0.4.5` |
| `ai-surface-hygiene-residuals` | intake C5 — T-044-45 review | **picked** · FR14 · `CONSUMED · v0.4.5` |
| `intent-taxonomy-vocabulary-ruling` | intake C6 — T-044-45 review | **picked** · FR15 (AS-2) · `CONSUMED · v0.4.5` |
| `dadaia-references-doctor-sanction` | intake E1 + operator ruling R3/O4 — T-044-44 ROOT-4 | **picked** · FR10 · `CONSUMED · v0.4.5` |
| bug `sdd-gate-blocks-fresh-repo-root-agents-md` (MEDIUM) | ai-engineer, 2026-08-24 | **solved in release, Arm B** · `S1` · FR1 · one cause with the row below (D2) |
| bug `repo-agents-md-law-gate-contradicts-template` (MEDIUM) | operator session, 2026-08-23 | **solved in release, Arm B** · `S1` · FR1 · same cause |
| bug `bug-event-field-with-unicode-line-separator-silently-drops-the-event` (MEDIUM) | code-reviewer, 2026-08-24 | **solved in release, Arm B** · `S3` · **bundled into FR7** (D3) |
| bug `two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` (LOW) | software-engineer, 2026-08-24 | **SUPERSEDED by `atomic-write-primitive-consolidation`** — the architect ruling recommends the structural fix absorb it; its acceptance is carried by **FR2/A2.3–A2.4**. `superseded` event appended **at definition**; `Closed` at the sweep (D4) |
| bug `dadaia-task-manager-stale-workspace-protocol-citation` (LOW) | qa-engineer, 2026-08-23 | **solved in release, Arm B** · `S1` · does not pre-empt the ratified C1 disposition (O3) |
| bug `certify-skip-detail-leaks-full-codex-output` (LOW) | claude, 2026-08-23 | **solved in release, Arm B** · `S1` |
| bug `codex-probe-unit-fixture-carries-real-session-uuid` (LOW) | claude, 2026-08-23 | **solved in release, Arm B** · `S1` |
| bug `windows-xdist-workers-crash-on-unit-fast-tier` (LOW) | project-manager, 2026-08-24 | **bounded root-cause attempt** · `S1` · **AS-5**: if inconclusive it is unpicked, stays open, and carries an evidence-backed quarantine verdict — never closed by a quarantine |
| Operator-only item **B1** (verdict-gate required check on both PR edges) | v0.4.4 intake, marked "not backlog material in the ordinary sense" | **scheduled**, not an entry · W0 `[operator]` task · **due before the `rc-2` PR** (D-7) |
| Audits | `specs/audits/_archive/` | **none outstanding** |
| **Standing order** — permanent architecture review oriented by bug history | operator, standing | governs D2 (one cause, not two patches), R-2 (deletion over addition) and every review verdict in this release |
| **Standing question** — de-personalising the git commit identity | operator, open since 2026-08-16 | **restated, not decided** — carried into `CLOSURE.md` |

**Pick tally.** 14 backlog entries (all 14 declared in `**Consumes:**`) + **8 bugs** =
**7 solved in-release** (6 in `S1`, 1 bundled into FR7) + **1 superseded**, with
`windows-xdist-workers-crash-on-unit-fast-tier` counted among the seven only if its root
cause is found (AS-5). No bug is dropped. Twelve entries stay `ACTIVE` — the four O1 names
plus the eight audit-proposed skills.

**Purge-on-pick (`dd-backlog-definition` §2).** The 14 picked `## ACTIVE` subsections leave
`specs/backlog/BACKLOG.md` in the **same commit** that creates this SPEC, executed by
`project-manager`; this section is the provenance record that removal requires. Each gains a
`CONSUMED · v0.4.5` `LEDGER` line in that same commit, **updated in place** to its terminal
token at the closure disposition sweep — never a second line.

**Version lineage — stated once.** `pyproject.toml` reads `0.4.4` at the branch cut and
bumps to `0.4.5` at the final `rc`. PyPI's latest published version is `0.4.4` and **stays
`0.4.4`** through this release (O5). `0.4.5` is minted locally and unpublished; §2.4 is its
ADR, and `pypi-distribution.md` carries it as product truth at closure.

---

## 8. Approval

Approving this SPEC ratifies, as written: **O1–O5** (the operator's 2026-08-24 rulings,
including the **no-PyPI release law**), **D1–D8** (the authoring decisions — **D5** places
the atomic-write primitive in `core/` and adds one entry to the core file-I/O
ratchet-authorized set, **D6** is the ship-without-publish mechanism, **D8** defines what an
`rc` is), the **five stated assumptions AS-1 … AS-5** (including that
`windows-xdist-workers-crash-on-unit-fast-tier` may end the release still open), the
**version lineage and its recorded tension** (§2.4, §7), and the **supersession** of
`two-atomic-writers-leak-temp-file-on-injected-os-replace-failure`.

**Status:** Aprovado — operator, 2026-08-24, at the ratification session that answered Q1–Q4
and issued the release law; SPEC, PLAN and TASKS all carry `**Status:** Aprovado`.
