# SPEC — Release v0.4.3 — claims-made-true / backlog-zero

**Status:** Aprovado
**Approval provenance:** operator-delegated, 2026-08-17 (fila inteira em 1 release — goal directive)
**Release ID:** v0.4.3
**Owner:** product-engineer
**Opened:** 2026-08-17
**Created:** 2026-08-17
**Branch:** `feature/0.4.3` (cut from `develop` at `84e369a0`; branch contract: `dadaia-gitflow`)
**Consumes:** test-suite-remediation-stewardship, consumer-side-validation-round, thin-wrapper-projected-scripts, bug-picked-ledger-event, codex-persona-law-context-dehydration, python-env-interpreter-probe-hardening, panel-runtime-reliability-dangling-ledger-pointer, mutation-testing-tool-selection-and-wiring, intent-docstring-mechanical-enforcement, gitflow-reconciliation-merge-mechanic, memory-path-class-dotfiles, commit-paths-index-scope-hardening, commit-message-scanning-residual, baseline-carve-out-review-cadence, dd-skills-applyto-glob-collisions, dd-release-definition-orchestration-pointer-loop, bug-event-redaction-always-on-reinforcement, dd-audit-project-pinned-tool-installs, dadaia-cli-skill-agent-grant, codex-skill-ref-phantom-memory-ctx-prefix, dadaia-artifact-event-driven-gc, repo-agents-md-symlink-hardening, stewardship-relocation-grep-homonym-note, tests-agents-md-placeholder-doctor-warning
**Picked set:** **the entire `## ACTIVE` queue — 25 entries** (20 candidates + 5 ideas, the
25th being `dadaia-artifact-event-driven-gc`, operator-created 2026-08-17 at `84e369a0`)
**plus 2 folded external items** (the co-author-trailer carve-out gap routed by handoff
`2026-08-17T132720Z`, folded into #24; the CHANGELOG-backfill intake candidate from the
v0.4.2 closure). Twenty-four slugs are declared consumed above; the twenty-fifth
(`bugs-jsonl-whole-blob-per-append`) is **REJECTED** by ruling R4 and leaves `## ACTIVE`
with a `LEDGER` line written in this same commit — it is not consumed, so it is not
declared. **No bug is picked, because there was no open bug at pick time**: the two LOWs
that outranked the queue at grill time were closed by Arm B on `develop` before this
definition (`specs/bugs/bugs.jsonl:889` and `:891`, commits `7971eefb` and `9a09b551`).
One bug registered **after** the pick rides the release as an Arm-B rider in `alpha-2`
(`specs-doctor-segment-router-silent-skip`, MEDIUM — §3). **No audit is outstanding** —
both 2026-07 audits are archived and fully dispositioned. Pick-time priority
(`DADAIA.md` §5) is satisfied with nothing outranking.
**Grill (mandatory, done):** `specs/releases/v0.4.3/GRILL.md` — a pointer to the
four-file report set (26 dossiers, 25 divergences D1–D25, six workstreams) and to the
rulings ratified below as **R1–R10**. None of them is re-litigated here.

---

## 1. Problem and context

**The operator's law for this release, verbatim and binding:**

> "fila inteira em 1 release"

> "minimização e se possível levar a zero backlogs residuais"

The queue is not 25 unrelated defects. Read as a set, twenty-one of the twenty-five
records are the **same act**: *make the thing that is already claimed actually true.*

- The **suite doctrine** is published and applied to everything except this repo's own
  suite: 56 LARGE e2e-tier journeys against a declared cap of 30, an intent-docstring
  rule with no enforcer, a mutation cadence with no tool.
- The **push gate** claims to protect the publish boundary but cannot read the largest
  object it publishes — the v0.4.2 reconciliation published *zero* scannable blobs and a
  106,327-character commit message that a human scanned by hand.
- The **privacy baseline** claims a reviewable shape but has no carve-out rationale
  check, grows literal-by-literal against an unbounded false-positive class, and refuses
  the very commit trailer the workspace law mandates.
- The **Codex projection** claims law visibility it does not prove, and certifies runtime
  behavior from static files.
- The **skills surface** claims activation boundaries and grants that do not exist: two
  `dd-` pairs claim the same path, `dadaia-cli` says "all agents may use it" while no
  agent frontmatter grants it, a pointer loop has no content at either end, and five
  third-party scanners are installed unpinned.
- **Memory itself** claims a version (`0.5.0`) the package does not have (`0.4.2`), and a
  symlink refusal the neighbouring seam does not implement.
- The **projected scripts** claim "one logic, one source" while the package shells out to
  the standalone script — the principle inverted.

Only four records add something genuinely new: the consumer-side validation round, the
`picked` ledger event, the complexity/size governance the operator ordered, and the
event-driven GC of `.dadaia` artifacts.

**Why now.** Every record is already adjudicated. The last four releases each shipped
clean and each left a residual list; v0.4.2 fixed the *process* that manufactured that
list (FR6 signal calibration, FR5 review-before-archive). This release is the first one
to run with those mechanisms in force, and the operator's instruction is to take the
queue to **zero** rather than to another partial pick.

---

## 2. Objective, and the decisions that shape it

Ship the whole queue as **six sequenced increments plus a shipping candidate**, so that
at `rc-1` the backlog's `## ACTIVE` section is **empty**, every picked record carries a
terminal `LEDGER` line, and the release's own reviews leave **zero actionable intake
candidates**.

Ownership is split by artifact class (`DADAIA.md` §2) and never crossed:
`ai-engineer` owns **every** skill, persona, rule, hook-surface and projected-asset edit;
`software-engineer` owns production Python, the CLI, the doctors and the tests;
`qa-engineer` owns test verdicts, the demotion map and each `alpha-N` close;
`code-reviewer` runs the six-axis review **before** the archive move;
`security-reviewer` covers each pushed delta; `project-manager` dispatches and relays;
`product-engineer` authors this definition, the memory window and the closure.

### ADRs — the dispatcher rulings (provenance: operator-delegated ruling, 2026-08-17)

| ADR | Decision | Consequence in this SPEC |
|---|---|---|
| **R1** | **SEGMENTED release**, six increments then a shipping candidate. Per ADR-3 a `qa-engineer` review gates each `alpha-N` (commit, no closure, no ship); the full trio + CLOSURE + archive happen at `rc-1`. | §3 groups every FR under its segment; TASKS carries one QA gate task per segment |
| **R2** | #32's acceptance **rewritten**: scope is the **two exact-duplicate `dd-` pairs only**. `applyTo: "**"` globs are **by design** and out of scope; no disjointness is asserted anywhere. | FR2 |
| **R3** | #34 gets the **honest terminal HEAD verification dictates**: the pointer line exists (`DADAIA.md:235-236`) → that half is `DELIVERED` with its anchor; the sentence naming the forbidden field content is absent → implement exactly that sentence. | FR4 |
| **R4** | The `bugs.jsonl` sharding idea is **REJECTED** — complexity exceeds value (three candidate shapes, four consumers, two laws in the blast radius); revisit only on a measured problem. | §7; `LEDGER` line in this commit |
| **R5** | CHANGELOG backfill = **minimal honest form**: a compact retroactive section per published version lacking one, derived from git history, **no invention**; the three phantom headings annotated as unpublished-internal; **nothing deleted**. | FR31 |
| **R6** | **No new disposition token.** #12 implements within its own scope. | FR15 |
| **R7** | Consumer validation runs against a **throwaway REAL workspace** created with `dadaia init` under the workspace tmp; limits recorded honestly. | FR30 |
| **R8** | Complexity governance is a **MEASURED RATCHET**: enable ruff `C90` (`C901`) and `PLR1702` with ceilings **at the observed maxima** (measure first, then pin), ratchet-only-down, plus a **mandatory `## Size accounting`** table in CLOSURE. **Never aspirational.** | FR21 |
| **R9** | The git-identity question (OD-A) **stays the operator's**; it is restated in CLOSURE, not decided here. | §5 closure obligations |
| **R10** | **Segment swap.** WS-G (event-driven GC) runs as **`alpha-5`** and WS-F (consumer validation + CHANGELOG) as **`alpha-6`**, so the consumer round runs **last** and certifies the assembled surface **including** the GC work. The `rc-1` delta re-check special case is **deleted** — there is nothing left for it to cover. | §3 segment order; FR23–FR29 = GC, FR30–FR31 = WS-F; `A32.6` removed |

### ADRs — authoring decisions taken by `product-engineer`

| ADR | Decision | Reason / status |
|---|---|---|
| **D1** | One authoritative document set at `releases/v0.4.3/`; the segment cadence lives in `TASKS.md` per-segment blocks; `ACTIVE.md`'s `segment:` pointer stays `none`. | A non-`none` `segment:` routes both `SPEC-DOC-004` and `TREE-6` to `releases/<id>/<segment>/`; six duplicated document sets would recreate the knowledge-duplication class this lineage removed. **RATIFIED as authored** by the dispatcher, 2026-08-17 — stands. |
| **D2** | `GRILL.md` is a **pointer** to the report set, not a copy of it. | Same reason: one writer per fact. |
| **D3** | *(withdrawn)* A `rc-1` consumer delta re-check covering WS-G. | **Superseded by R10** — swapping the segments makes the re-check unnecessary: the consumer round now runs after GC and certifies it directly. No trace of the special case remains. |

---

## 3. Scope

**Standing scope rule for every zero-hit acceptance criterion.** Each grep-based
criterion is evaluated over the working tree **excluding** `specs/_archive/**`,
`specs/bugs/**`, `specs/backlog/**`, `specs/releases/v0.4.3/**`, `CHANGELOG.md` and
`.dadaia/{reports,handoff,tmp}/**` — this release's own documents, the append-only
ledgers and the archive must be able to quote the symbols they retire.

**Standing green rule.** `dadaia ci preflight` (`ruff format --check`, `ruff check`,
`mypy --strict`, `pytest`), `dadaia backlog doctor`, `dadaia specs doctor` and
`dadaia public doctor` are green at **every** commit. No `--no-verify`, ever.

**Standing census-freeze rule (D12).** No segment adds a `tests/e2e/**` test — pytest
journey or Playwright spec — without a named `qa-engineer` exception recorded in that
segment's QA artifact. FR18's census is therefore measured against a tree only FR18 is
allowed to grow. v0.4.2 already achieved zero new e2e tests, so the bar is proven.

**Standing measurement rule (OD-3 pattern).** `product-engineer` has no shell. Every
number this release asserts — census, warning names, byte sizes, complexity maxima,
doctor output — is produced by a **named task step** run by an agent with a shell and
captured under `.dadaia/tmp/<agent>/<YYYYMMDD>/`. No FR quotes a number the release did
not measure.

**Standing simplicity rule (R5, carried from v0.4.2).** Where a fix can be made by
deleting, it is made by deleting. No new module, no second parse path, and no new doctor
code where an existing validator can carry the check.

---

### Segment `alpha-1` — WS-D, the AI surface (owner: `ai-engineer` unless noted)

Eight records, one projection cycle. `ai-engineer` performs every edit under
`dadaia_workspace/public/**`; the projection runs once at the end of the segment.

#### FR1 — Every prescribed third-party install is pinned

*(entry `dd-audit-project-pinned-tool-installs` #35 — lands **first** in the release)*

`dd-audit-project` prescribes five unpinned installs (`SKILL.md:107,118,121,132,142`:
`pip install vulture`, `npx ts-prune`, `npx knip`, `npx depcheck`, `pip install pydeps`).
Each becomes an exact version (or hash) pin, and the **rule** is stated once so a future
tool addition inherits it — covering **audit and quality tooling alike**, because FR20 is
about to add a sixth third-party tool.

**Acceptance**
- A1.1 Every install command in `dd-audit-project/SKILL.md` carries an exact version or hash pin.
- A1.2 The skill states the pinning rule once, in a form a new tool inherits by reading it.
- A1.3 The dependency-hygiene doctrine in `specs/memory/quality-assurance.md` records that
  audit and quality tooling follow the production pinning rule (CLOSURE memory window, §5).
- A1.4 A tree-wide grep (standing exclusions) shows no `pip install <name>` or `npx <name>`
  without a version specifier in any `public/skills/**/SKILL.md`.

#### FR2 — The two duplicate `dd-` activation claims are resolved; universal skills are declared, not partitioned

*(entry `dd-skills-applyto-glob-collisions` #32, acceptance rewritten by **R2**; D5)*

Scope is **exactly** the two exact-duplicate pairs verified at HEAD:
`dd-backlog-definition:4` and `dd-release-definition:4` both claim `specs/backlog/**`;
`dd-bug-registration:4` and `dd-bug-fix:4` both claim `specs/bugs/**`. Each pair narrows
to the sub-path its stage actually owns. `applyTo: "**"` skills
(`architect-core-workflow`, `dadaia-step0-memory-bootstrap`, `harness-primitives`) and
`dadaia-grill-me`'s `specs/**` are **always-on by design and out of scope** — no
disjointness is asserted about them anywhere, and no check may assert it.

**Acceptance**
- A2.1 The two duplicate pairs no longer share an identical `applyTo` glob.
- A2.2 A documented precedence rule states: universal (`**`) skills are always-on and never
  compete; stage skills resolve by most-specific glob; declared overlaps are recorded.
- A2.3 A projection-time check flags only **undeclared** overlap **between non-universal
  skills**, and is **green at HEAD after A2.1** (the Satisfiable Diagnostics law: a check
  that cannot go green is itself a defect).
- A2.4 A fixture proves the check stays silent for a `**` skill and fires for a newly
  introduced undeclared duplicate.

#### FR3 — The release-definition pointer loop becomes a DAG

*(entry `dd-release-definition-orchestration-pointer-loop` #33)*

`dd-release-definition/SKILL.md:106-107` points at the `project-orchestration`
release-definition playbook, which points back saying the skill "owns the full protocol".
The playbook already names what it owns (dispatch), so the **skill's back-pointer is
dropped**, leaving the `DADAIA.md` §5 reference.

**Acceptance**
- A3.1 No pointer loop remains: exactly one of the two files carries the authority/dispatch
  statement, the other points at it (or does not point at all).
- A3.2 A grep over `public/` shows no file pair whose only content is a mutual reference.

#### FR4 — The bug-event redaction rule is visible at the moment the event is written

*(entry `bug-event-redaction-always-on-reinforcement` #34, per **R3**)*

The always-on **pointer** already exists at `public/data/DADAIA.md:235-236` and is
recorded as delivered. What is missing is one sentence naming **what** the rule forbids.
`DADAIA.md` §6's register-every-bug paragraph gains **exactly one sentence**: absolute
local paths, IPs, hostnames, private names and secrets never enter an event field. The
full rule stays on-demand in `dd-bug-registration` §3 — no rehydration.

**Acceptance**
- A4.1 §6 carries one new sentence naming the forbidden field content; the existing pointer
  sentence is unchanged or absorbed, never duplicated.
- A4.2 `DADAIA.md` §6 grows by **one** sentence, not a block; `dd-bug-registration` §3 is unedited.
- A4.3 The projected law files at the workspace root and in all three harness dirs are
  byte-identical to the canonical source after `public install` (law files are human-only
  in an instantiated workspace — the edit is made at the source, §7 of the law).

#### FR5 — `dadaia-cli`'s grant and its description agree

*(entry `dadaia-cli-skill-agent-grant` #36)*

`public/skills/dadaia-cli/SKILL.md:7` claims "All agents may use it" while **no agent
frontmatter grants it**. The release decides the reachability per agent — a reasoned
selection, never a blanket grant — and makes description and grants agree. Agents with no
shell (`product-engineer`) are excluded explicitly, because a CLI-literacy grant to a
shell-less agent is inert.

**Acceptance**
- A5.1 Either every agent whose protocol invokes the CLI carries the grant, or the
  description states the actual reachability; the two never disagree.
- A5.2 The decided reachability is recorded on the derivation surface so drift is checkable.
- A5.3 A test derives the expectation from the agent frontmatters — grant/description drift fails loud.

#### FR6 — The reconciliation-merge mechanic is written where the branch contract lives

*(entry `gitflow-reconciliation-merge-mechanic` #15)*

`dadaia-gitflow/SKILL.md` carries zero mentions of "reconciliation" while v0.4.2's ship
**executed** the mechanic for real (merge `84a66d13`, two parents, tree-identical) and it
took a security review to describe the shape. One line: every squash-merge to `main` is
followed by a reconciliation merge of `main` into `develop`, resolving resurrected loose
copies in favour of `develop`'s archives.

**Acceptance**
- A6.1 `dadaia-gitflow/SKILL.md` states the mechanic and the resurrected-copy resolution rule.
- A6.2 The statement exists exactly once across `public/` (no second writer).

#### FR7 — The stewardship vocabulary's homonyms are named

*(idea `stewardship-relocation-grep-homonym-note`)*

`dadaia-test-stewardship/SKILL.md` gains a short note that "scaffold", "sentinel" and
"quarantine" have pre-existing unrelated uses in this codebase (`public/scaffold/`,
`scaffolder.py`, the self-scan sentinel family), so FR18's curation greps do not chase
homonyms. It lands **before** FR18 runs those greps.

**Acceptance**
- A7.1 The note exists, naming the three colliding terms and their unrelated homes.
- A7.2 FR18's measurement task cites it as an input.

#### FR8 — An installed `tests/AGENTS.md` with unfilled placeholders is reported

*(idea `tests-agents-md-placeholder-doctor-warning`; owner: `software-engineer`)*

Placeholder detection exists only for memory atoms (`features/specs/doctor.py:119`,
`MEM-PLACEHOLDER-1`). The same validator family gains a check for an **installed**
`tests/AGENTS.md` still carrying `<[A-Z_]+>` tokens. Satisfiability: the check runs
against the installed consumer file, **never** the canonical template, which legitimately
carries placeholders.

**Acceptance**
- A8.1 An installed `tests/AGENTS.md` containing `<PLACEHOLDER>` tokens produces one WARN naming the file.
- A8.2 The canonical template produces no finding.
- A8.3 A filled file produces no finding; the check is green on this workspace at HEAD.

---

### Segment `alpha-2` — WS-B + WS-E, gate hardening and governance primitives

Nine records **plus one Arm-B rider**. `#9` and `#18` are a **declared disjoint parallel
pair** (D25); everything else is serial.

#### FR9 — The interpreter probe rejects relative candidates and cannot hang

*(entry `python-env-interpreter-probe-hardening` #9; owner: `software-engineer`)*

`infrastructure/python_env.py`: `_path_candidates` (`:229-241`) appends
`shutil.which(...)` results with no absoluteness check and `_current_venv_pyvenv_executable`
(`:196-214`) returns the raw `pyvenv.cfg` value unvalidated (CWE-426);
`_interpreter_version` (`:169-193`) runs its probe with no `timeout=` and inherited stdin.

**Acceptance**
- A9.1 Any candidate failing `os.path.isabs()` is rejected before reaching `subprocess.run` —
  covering both the `which` results and the `pyvenv.cfg` value. RED first with a fixture
  returning a bare name.
- A9.2 The probe passes a bounded `timeout=` and `stdin=subprocess.DEVNULL`; a hung candidate
  degrades to `None` and is skipped, proven by a fixture that would otherwise hang.
- A9.3 `dadaia init` behaviour on a healthy machine is byte-identical.

#### FR10 — `commit_paths` is honest by construction

*(entry `commit-paths-index-scope-hardening` #18; owner: `software-engineer`)*

`infrastructure/git_subprocess.py:139-151` discards the `git add -- <paths>` exit status
and then commits the **whole index**.

**Acceptance**
- A10.1 A non-zero `git add` exit raises `GitSyncError`; a stage that did not happen never becomes a commit.
- A10.2 The commit is path-scoped (`git commit -m <msg> -- <paths>`); operator pre-staged
  content is ignored, proven by a fixture that stages unrelated content first.
- A10.3 The pathspec-magic defence (`:(literal)` or `--pathspec-from-file`) is applied or
  explicitly recorded as declined with its reason.

#### FR11 — The push scan reads the commit objects it publishes

*(entry `commit-message-scanning-residual` #21; owner: `software-engineer` + `security-reviewer`)*

`rev-list --objects` lists commits without a path and the shipped scanner reads blobs
only. The v0.4.2 reconciliation published **zero** blobs and one 106,327-character /
2,005-line commit object that was hand-scanned. The reader seam
(`container.py:191 build_git_object_reader`) yields the range's commit objects — message
bodies and annotated tag bodies — through the same batched conversation and typed-error
contract; `features/chokepoints/service.py:615 push_gate_decision` feeds them through the
same three term layers with the same masked, satisfiable refusal shape (healing action:
reword/amend before push).

**Acceptance**
- A11.1 A range whose only private-term exposure is in a commit message is **refused**, with
  the term masked in the refusal and a reword/amend healing action. RED first.
- A11.2 The **reconciliation shape** (two commits, zero blobs) is an acceptance fixture, not a hypothesis.
- A11.3 An annotated tag body is scanned for a tag-ref push.
- A11.4 Typed-error and degradation behaviour matches the blob path exactly — no silent skip;
  a commit-object read failure is reported, never rationalized.
- A11.5 The `sdd-gate-v3` atom's blob-only non-goal is retired at CLOSURE (§5).

#### FR12 — The privacy baseline stops growing literal by literal

*(entry `baseline-carve-out-review-cadence` #24 **+ the folded co-author-trailer gap**;
owner: `software-engineer` + `security-reviewer`)*

Three parts. **(a) Rationale check:** every `exclude_regex` carve-out carries a documented
rationale and a doctor/CI check flags a pattern lacking one. **(b) Cadence as product
truth:** what triggers re-examination and a version bump, the single-line-pattern
constraint (the push scan matches line-by-line while the public-privacy doctor matches
whole text), and the gap-class — a declared-support platform with no covering pattern —
becomes something the cadence catches. **(c) Structural fix** for the `internal-hostname`
dotted-chain false-positive class, replacing the treadmill; plus the two folded escapes:
the Windows trailing-period carve-out escape (CR-6) and the **co-author trailer** — the v5
`email-address` carve-out is `@`-anchored on the domain `noreply.anthropic.com`, so the
law-mandated `noreply@anthropic.com` local-part form is **not** carved out and would
refuse the first push that lands it in a tracked blob.

**Acceptance**
- A12.1 A carve-out with no rationale is reported by a doctor/CI check; the shipped baseline passes it.
- A12.2 The `noreply@anthropic.com` local-part form is carved out, with a paired counter-fixture
  proving a genuine address at the same domain still fires.
- A12.3 The Windows trailing-period escape no longer defeats the carve-out, with a fixture in prose form.
- A12.4 The dotted-chain class has a structural rule (not a fourth literal), with counter-fixtures
  proving narrowness is preserved.
- A12.5 Every baseline pattern stays **single-line**; the version bumps with its `_header` rationale extended.
- A12.6 `dadaia public doctor` reports `[ok] public-privacy`; the self-scan sentinel is green.

#### FR13 — The MEMORY path class is a decision, and the standing lint warnings are cleared

*(entry `memory-path-class-dotfiles` #16 **+ the 12 standing LINT-1 heading warnings**, D14;
owners: `software-architect` doctrine, `software-engineer` gate code, `product-engineer` allowlist)*

`features/spec_context/gate_policy.py:56` classifies by bare prefix, so
`specs/memory/.heading-allowlist` is MEMORY-class **by accident**. The release decides and
encodes: (a) whether memory dotfiles are MEMORY-class or a documented carve-out; (b)
whether a SPEC may assign a memory-class write to a non-`DEFINITION`/`CLOSURE` task and
how the gate treats it. Folded in: the 12 standing `LINT-1` heading warnings that v0.4.2's
RO-12 called "a known library limitation", contradicted by the existence of the populated
extension file — they are enumerated and cleared.

**Acceptance**
- A13.1 The classification is encoded in code **and** stated as a rule; no ad-hoc exception remains.
- A13.2 A fixture pins the decided behaviour for a dotfile write in each phase.
- A13.3 The 12 `LINT-1` warnings are enumerated by a measurement task, then eliminated by
  extending `specs/memory/.heading-allowlist` (CLOSURE memory window, §5) or fixing the atoms.
- A13.4 `dadaia specs doctor` reports **zero** `LINT-1` heading warnings at `rc-1`.

#### FR14 — Arm B gets an observable reservation marker

*(entry `bug-picked-ledger-event` #7; owners: `software-architect` schema + `software-engineer`)*

`core/models/bugs.py:30-40` is a closed six-kind enum. A **non-terminal** `picked` event
kind is added, with coherence rules: valid only on an open stream; never terminal;
repeated picks **allowed and surfaced** (NO-LOCKS); pick-after-terminal incoherent. Schema,
fold and CLI evolve in **one** change (single-authority law).

**Acceptance**
- A14.1 `dadaia bugs append --event picked` records the reservation with its actor; `bugs status` surfaces picked-by.
- A14.2 A second pick on the same open stream is accepted and visible — never blocked.
- A14.3 A pick after a terminal event is refused as incoherent.
- A14.4 Schema `bug-event-v1`, the fold and the CLI ship in the same change; older ledgers still fold.

#### FR15 — The dangling deferral pointer is clarified, not rewritten

*(entry `panel-runtime-reliability-dangling-ledger-pointer` #12, per **R6**; owner: `software-engineer`)*

Bug `panel-telemetry-sqlite-corrupts-under-concurrent-access` was deferred to a backlog
slug already consumed by v0.1.52. A **new clarifying event** records that the target was
already terminal at deferral time and names the corrected disposition **using the existing
vocabulary** — R6 forbids a new token. No existing ledger line is modified.

**Acceptance**
- A15.1 One appended event; the 2026-07-01 line is byte-unchanged.
- A15.2 The event names the corrected disposition with an existing token and states the reason.
- A15.3 No new disposition token exists anywhere in the schema or the CLI.

#### FR16 — One logic, one source: the projection stops being the implementation

*(entry `thin-wrapper-projected-scripts` #6 **+ v0.4.2's RO-5**; owners: `software-engineer` + `ai-engineer`)*

Today the principle is inverted: `features/specs/doctor_memory.py:38`/`:357` shells out to
`public/scripts/lint-memory-atoms.py`. The lint logic moves **into the package**, imported
by LINT-1; the projected script becomes a thin wrapper that execs the workspace venv's
package entry point. RO-5 rides along: `estimate_tokens` duplicated verbatim in
`public/scripts/generate-memory-catalog.py` — a second writer pinned only by a byte-identity
contract test.

**Acceptance**
- A16.1 LINT-1 imports the shared implementation; no `subprocess` call to a projected script remains.
- A16.2 Every script under `public/scripts/` is a thin wrapper — a doctor/projection test asserts
  the contract so script↔package drift is structurally impossible.
- A16.3 RO-5's duplication is removed, or CLOSURE states precisely why it could not be.
- A16.4 The module docstring's "architectural exception it HOLDS" note is deleted with the exception itself.

#### FR17 — The repo-`AGENTS.md` destination refuses a symlink

*(idea `repo-agents-md-symlink-hardening`; owner: `software-engineer`)*

`infrastructure/public_assets.py` carries **zero** symlink refusals while the
`public-asset-distribution` memory atom already advertises "destination-file symlink
refusal". The four refusal sites of the hardened sibling seam are mirrored onto the
repo-`AGENTS.md` destination write.

**Acceptance**
- A17.1 A symlinked destination is refused at every write site, with a fixture per site.
- A17.2 The memory atom's claim becomes true (no atom edit needed beyond §5's precision check).

#### Arm-B rider (not an FR) — the segment router stops going silent

*(bug `specs-doctor-segment-router-silent-skip`, MEDIUM, registered 2026-08-17; owner:
`software-engineer`; task T-043-22)*

Found while authoring this definition, registered as a bug and fixed here as an Arm-B
rider rather than smuggled in as scope. `features/specs/doctor_release.py:162-165` and
`features/specs/doctor_structural.py:339-342` route to `releases/<release>/<segment>/`
when `ACTIVE.md` carries a non-`none` `segment:`, then `return issues` if that directory
is absent — the comment claims "already reported by check 9", but `check_active_md` only
validates the **release** directory. A live segment pointer at a missing directory
therefore disables `SPEC-DOC-004` **and** `TREE-6` **silently**: no artifact-presence
check, no `**Status:** Aprovado` check, no error. It is the doctor going blind instead of
loud — and it is the reason ADR D1 keeps this release's pointer at `none`.

**Acceptance** (RED first)
- AB.1 An `ACTIVE.md` whose `segment:` names a non-existent directory produces an explicit
  **ERROR** naming the missing segment directory — never a silent pass.
- AB.2 A segmented release **with** its directory keeps validating exactly as today
  (no behaviour change on the healthy path).
- AB.3 A flat release (`segment: none` or no line) is unaffected.
- AB.4 The stale "already reported by check 9" comment is corrected or deleted.
- AB.5 The bug is closed with a `resolved` event carrying its evidence, in the same session
  that proves the fix.

---

### Segment `alpha-3` — WS-A, the suite and its measurements

#### FR18 — The suite doctrine is applied to this repo's own suite

*(entry `test-suite-remediation-stewardship` #2; owners: `qa-engineer` verdicts, `software-engineer` execution)*

The first full curation under the shipped stewardship doctrine: the LARGE census down to
the declared cap of 30 **or** an explicit written justification per excess test; an owner
declared for every LARGE test; the tautological and implementation-coupled families
reworked; quarantine adopted where it belongs; orphan tooling
(`tests/scripts/check_skill_orphans.py`) wired or deleted; env-gated skips carrying a plan
ref or deleted. **The steward never edits**: every deletion or demotion is a `qa-engineer`
verdict with evidence, executed by `software-engineer`.

**No number in this FR is quoted from the entry's text** — the entry's baseline has gone
stale twice. The census is measured at segment start and again at segment end.

**Acceptance**
- A18.1 The census is measured at segment start (task step), producing the offender list; the
  entry's own numbers are treated as void.
- A18.2 Every LARGE test is either demoted with a named replacement, deleted with a recorded
  "behaviour removed" supersession, or kept with a written justification and a declared owner.
- A18.3 The census is re-measured at segment end; both numbers and the delta are captured for CLOSURE.
- A18.4 No test is deleted, skipped or disabled without a `qa-engineer` verdict carrying evidence.
- A18.5 The demotion map is drafted in the segment and recorded in CLOSURE's `## Test dispositions`.
- A18.6 `quality-assurance.md`'s census sentence and its two justified-timeout citations — which
  name this backlog entry as their remediation reference — are rewritten at CLOSURE (§5) so no
  memory pointer dangles into a consumed slug.

#### FR19 — A new test without a declared intent is refused

*(entry `intent-docstring-mechanical-enforcement` #14; strictly after FR18)*

The mechanical check that refuses a test file without a declared intent/size. It is
**satisfiable by construction only after FR18** — the same Satisfiable Diagnostics law
that has kept this record blocked. It must accept the shape the repo actually uses
(v0.4.2 RO-9: size declared by directory placement plus module/section `Intent:` headers),
or change that shape deliberately.

**Acceptance**
- A19.1 The check is **green at HEAD** the moment it is enabled.
- A19.2 A new test file with no `Intent:` declaration fails the check; a compliant one passes.
- A19.3 The accepted declaration shape is documented where the doctrine lives.

#### FR20 — The declared mutation cadence gets an executor

*(entry `mutation-testing-tool-selection-and-wiring` #13; after FR18, inheriting FR1's pin rule)*

`quality-assurance.md:190-191` states outright that the cadence is declared and "the tool
is not yet selected". The tool is chosen (`qa-engineer` verdict), **pinned per FR1**, and
wired at the declared cadence — once per release, **never** on the push path, with a
bounded wall clock.

**Acceptance**
- A20.1 A named tool with an exact pin is wired and runs to completion on this repo.
- A20.2 The invocation is recorded in QA memory (§5) so the cadence claim is backed by a runnable command.
- A20.3 The tool is absent from every push-path selector; CI push timing is unchanged.
- A20.4 The first baseline score is captured **after** FR18, as evidence, not as a gate.

#### FR21 — Complexity and size become measured, ratcheted governance

*(operator law, per **R8**; owners: `software-engineer` rules, `ai-engineer` skill, `product-engineer` memory)*

`pyproject.toml:101` selects `["E","F","I","UP","B","SIM"]` — `C90` is absent, so `C901`
is enforced nowhere, and no `PL` family gives a nesting rule. The FR is a **ratchet, never
an aspiration**: one task measures the actual maxima with a permissive ceiling, and the
**same task pins the ceiling at the observed maximum**. Later reductions are reviewable
diffs in later releases. CLOSURE gains a mandatory `## Size accounting` table.

**Acceptance**
- A21.1 `C90` and `PLR1702` are selected with ceilings **equal to the measured maxima**; the
  measurement output is captured as evidence.
- A21.2 `ruff check` is green at HEAD the moment the rules land — zero violations by construction.
- A21.3 The ratchet direction is documented: a ceiling may only decrease, and any decrease is justified in CLOSURE.
- A21.4 `dd-release-closure/SKILL.md`'s CLOSURE template requires a `## Size accounting` table:
  production LOC added/deleted/net, the three largest additions and deletions by file, max
  complexity before/after, and the nesting-violation count.
- A21.5 This release's own CLOSURE carries that table, filled with measured values.
- A21.6 `quality-assurance.md` gains the governance section (§5); its heading enters
  `specs/memory/.heading-allowlist` in the same memory window (ties to A13.3).

---

### Segment `alpha-4` — WS-C, the Codex fidelity boundary

#### FR22 — Codex is repaired as one fidelity boundary

*(entry `codex-persona-law-context-dehydration` #8, scope-corrected, **absorbing** entry
`codex-skill-ref-phantom-memory-ctx-prefix` #37; owners: `ai-engineer` + `software-engineer`)*

Six intents, not seven. **Struck at pick, with their anchors, so the deletion is
auditable:** intent 6 (`ctx_inject` context order) is **already delivered** —
`hooks/ctx_inject.py:185-216` implements the three law rungs with an explicit law-order
docstring and no first-alive fallback (D2); and the "false 12-persona count" sub-claim is
**void** — zero hits repo-wide, and `public/entities/registry.json:4-41` holds exactly
nine personas (D3). The surviving work: compact persona TOMLs (role identity and
role-specific decisions only); the canonical law loaded **once** with proven parent **and**
delegated visibility; the stale headless-no-hooks claim (`codex_doctor.py:624-636`)
replaced with version-qualified live evidence; certification exercising the **installed**
Codex instead of inferring runtime behavior from static files; `ENT-DERIVE-1` strengthened
from name bijection to behavioral fidelity with mutation fixtures; and the stale Codex
documentation corrected, including `ai-harness-codex/SKILL.md:99`'s `public/rules/*.md`
taxonomy against a directory that **does not exist**. **Absorbed (#37):** the phantom
`memory-ctx` prefix in `runtime_transforms/codex_assets.py:39-46`, with a test deriving
the expectation from the real `public/skills/` inventory.

**Constraint held as acceptance:** scope is 100 % Codex — **zero byte-changes to any
non-Codex projection**.

**Acceptance**
- A22.1 The nine persona TOMLs shrink measurably against a **re-measured** byte baseline (the
  126,155 B figure is from 2026-08-15 and is re-measured by a task step, not quoted).
- A22.2 The law is loaded exactly once in the effective Codex context, with executed-path
  evidence for the parent session **and** a delegated custom agent.
- A22.3 `codex_trust_boundary_info` carries version-qualified observations from the installed
  Codex; no unqualified headless claim survives.
- A22.4 Certification probes exercise the installed Codex; static projection tests may validate
  shape but never attest runtime behavior.
- A22.5 `ENT-DERIVE-1` proves behavioral fidelity with mutation fixtures — each drift class blocks.
- A22.6 Every prefix in `_CODEX_SKILL_REF_PREFIXES` corresponds to an existing skill or a
  documented runtime-asset exception; a test derives it from the inventory.
- A22.7 `ai-harness-codex/SKILL.md` no longer documents a non-existent directory.
- A22.8 A byte-diff proves **no** non-Codex projection changed.

---

### Segment `alpha-5` — WS-G, event-driven artifact GC

*(entry `dadaia-artifact-event-driven-gc`, operator-created 2026-08-17; owners:
`ai-engineer` for the skills/hooks surface, `software-engineer` for code. Runs **before**
the consumer round per **R10**, so `alpha-6` certifies this work too.)*

The doctrine: **an artifact dies when the thing it exists for dies**, not when a clock
says so. Calendar-based deletion survives **only** in FR29's backstop. Every capability
below is fail-open where it rides a hook — a GC error never changes a gate verdict.

#### FR23 — Ack-on-consume for coordination handoffs

Every consumer skill that reads a handoff as its input contract deletes that handoff once
consumed. Handoffs carrying an `artifact.path` are **exempt** and follow their report's
retention. The rule lands **once**, in the handoff-consumer discipline, never per-skill.

- A23.1 The rule is stated once on the skills surface; no skill restates it.
- A23.2 A consumed coordination handoff is deleted; an artifact-bearing handoff is untouched.
- A23.3 Deleting a handoff never breaks `dadaia reports validate` on a surviving one.

#### FR24 — A consumed push verdict is deleted by the push that consumed it

After a successful push, the pre-push chokepoint deletes the APPROVED `security-reviewer`
verdict handoff(s) whose review covered the delta just pushed. A verdict for an unpushed
delta is never touched.

- A24.1 A successful push deletes exactly the covering verdict(s); a fixture proves an
  unrelated verdict survives.
- A24.2 A failed or refused push deletes nothing.
- A24.3 Deletion is best-effort: an I/O error never changes the push verdict.

#### FR25 — Closing a release ends its artifacts' lives

`dd-release-closure` gains a GC sweep step: closing a release deletes or archives that
release's reports, handoffs and lifecycle run records.

- A25.1 The skill's template carries the sweep step with an explicit keep/delete rule.
- A25.2 This release's own CLOSURE executes it and records what was swept.
- A25.3 Nothing referenced by a surviving CLOSURE evidence pointer is deleted.

#### FR26 — The reconciler reaps what it already walks

Session/presence records stale beyond N×TTL are deleted together with their tmp markers
(`reconciler-last-*`, `ctx-inject-fired-*`) and any empty context dirs; zombie
lifecycle/state run records are reaped (measured 2026-08-17: 29 "running" zombies from
closed releases, 38 dead "completed").

- A26.1 A stale record and its markers are deleted; a live session's records are never touched.
- A26.2 Zombie run records are reaped; the count before/after is captured.
- A26.3 Reaping is best-effort/fail-open, matching the reconciler it extends.

#### FR27 — Every `.dadaia/logs/*.jsonl` writer rotates its own file

Each appender caps its log at ~1 MB and keeps current+1 rotated file. Rotation happens at
write time by the file's owner, never by an external cron; telemetry stays fail-open.

- A27.1 A log crossing the cap rotates; exactly one rotated file is retained.
- A27.2 A rotation error never changes a gate verdict.
- A27.3 Concurrent writers do not corrupt the rotation (fixture with two writers).

#### FR28 — The cache must not be born

The venv guard blocks `mypy`/`pytest`/`ruff` Bash invocations that would run with caching
enabled (missing `-p no:cacheprovider` / `incremental` / `--no-cache` posture). The block
message carries the corrected command, matching the existing venv-guard contract.
Evidence: 6 duplicate mypy caches (~68 MB) cleaned 2026-08-17; a concurrent session
recreated 5 new cache dirs (~35 MB) within 40 minutes.

- A28.1 A cache-enabling invocation is blocked with the corrected command in the message.
- A28.2 A compliant invocation passes untouched; no false block on an unrelated command.
- A28.3 The guard stays token-matched on fixed leading tokens — no shell parsing.

#### FR29 — `dadaia tmp gc`, the orphan backstop

The **only** calendar-based deletion in the release: dated scratch older than 3 days, any
`*cache*` directory under `.dadaia`, and orphaned session markers. Idempotent and safe to
run from `SessionStart`.

- A29.1 The verb is idempotent — a second run reports nothing and changes nothing.
- A29.2 It never deletes a live session's markers or a non-dated path.
- A29.3 A dry-run mode reports what it would remove.
- A29.4 It is documented as the backstop, with every other capability named as event-driven.

---

### Segment `alpha-6` — WS-F, the outward-facing close

*(Runs **last** per **R10**: the consumer round certifies the fully assembled surface,
GC included, so no delta re-check is needed and none exists.)*

#### FR30 — The assembled consumer journey is proven on a real workspace

*(entry `consumer-side-validation-round` #5, per **R7**; owner: consumer-side validation
agent / `qa-engineer`, dispatched by `project-manager`)*

A **throwaway REAL workspace**, created with `dadaia init` under the workspace tmp
(`.dadaia/tmp/<agent>/<YYYYMMDD>/`), validated through supported interfaces only. This
record **cannot be dispositioned away**: two archived audits (2026-07-15 consumer,
2026-07-18 resilience) reached terminal state *citing* it and #6 as the inheritors of
their surviving findings (D10). The three inherited criteria are its acceptance.

**Acceptance**
- A30.1 The consumer prompt/tests consume the **installed, version-matched** skill surface and
  exercise canonical verbs only — no reference to a removed lifecycle command.
- A30.2 The consumer's owning repository is governance-coherent: one `[-]` at a time, valid
  memory/schema state, immutable release evidence.
- A30.3 A pre-v0.12.0 workspace upgraded in place **surfaces** its un-migrated backlog state —
  the `SPEC-DOC-035` WARN count equals the loose per-entry-file count while `backlog doctor`
  is clean on an absent `BACKLOG.md` — and folds to a clean two-doctor state after migration.
- A30.4 Every limit of the throwaway environment (what could not be exercised, and why) is
  recorded **honestly** in the round's artifact and carried into CLOSURE — an unexercised
  criterion is never reported as passed.
- A30.5 One remediation cycle is budgeted **inside** this segment; a finding is fixed here, not deferred.
- A30.6 The round's scope explicitly includes the `alpha-5` GC surface — the artifact names
  which GC capabilities the journey exercised (R10's whole point).

#### FR31 — The published lineage's record becomes honest

*(v0.4.2 intake candidate, per **R5**; owner: `software-engineer`)*

Minimal honest form. Ten published versions carry no section (`0.1.2`, `0.1.5`, `0.1.6`,
`0.2.0`–`0.2.3`, `0.3.0`, `0.4.0`, `0.4.1`): each gains a **compact retroactive section
derived from git history**, with **no invention** — a version whose history yields nothing
substantive gets a one-line factual entry, never a fabricated feature list. The three
headings matching no published version (`[0.1.24]`, `[0.1.7]`, `[0.1.3]`) are **annotated**
as unpublished-internal. **Nothing is deleted or renamed.**

**Acceptance**
- A31.1 Every published version in the PyPI lineage has a section; each is traceable to commits.
- A31.2 No section asserts a change git history does not show — a reviewer can check each line against a range.
- A31.3 The three phantom headings carry an unpublished-internal annotation; no heading is removed or renamed.
- A31.4 The one-axis rule (v0.4.2 FR13) still holds: the release id **is** the package version.

---

### `rc-1` — shipping candidate

#### FR32 — The invariants this release must not break

- A32.1 `dadaia ci preflight`, `dadaia doctor`, `dadaia specs doctor`, `dadaia backlog doctor`
  and `dadaia public doctor` are green at `rc-1`; `specs doctor` reports **0 errors**.
- A32.2 `dadaia public doctor` reports `[ok] public-privacy`, `[ok] entities-derivation` and
  `[ok] model-resolution`.
- A32.3 Layer rules hold: `features/**` imports neither `cli`, `infrastructure` nor `hooks`;
  `core/**` stays stdlib-pure; `lint-imports` green with **no new** accepted edge.
- A32.4 No harness projection changes except where an FR requires it, proven by byte-diff.
- A32.5 **Residual budget: zero actionable intake candidates**, and `## ACTIVE` **empty**.

---

## 4. Out of scope (non-goals)

1. **`bugs.jsonl` sharding** (R4). Rejected with reason, not forgotten: three candidate
   shapes, four consumers, two laws in the blast radius, and the resurfacing half already
   mitigated by the shipped amnesty. Revisit only on a **measured** problem.
2. **Disjoint `applyTo` globs across all skills** (R2). Universal `**` skills are always-on
   by design; asserting disjointness would require deleting them.
3. **A new disposition token** (R6).
4. **Rehydrating the bug-event redaction rule into the law** (R3) — one sentence, not a block.
5. **Reconstructing invented CHANGELOG history** (R5) — git-derived or one honest line.
6. **The git-identity decision** (R9) — restated in CLOSURE, not taken here.
7. **Six duplicated per-segment document sets** (D1, ratified).
8. **A `rc-1` consumer delta re-check** (R10 deleted it — the swap makes it unnecessary).
9. **Any FR not listed in §3.** The queue is the scope; nothing discovered mid-release is
   added without an operator ruling at the moment of discovery (§5 residual budget). The
   one exception already taken: the `alpha-2` Arm-B rider, which is a **bug** fixed on the
   spot per `DADAIA.md` §1 Arm B — never backlog demand.

---

## 5. Memory files affected at closure

| File | Change | When |
|---|---|---|
| `specs/memory/tech-stack.md` | **PE-2:** the false "currently `0.5.0`" parenthetical is dropped (not restated with a new number — the one-axis rule makes the literal redundant); the pinning doctrine line from FR1/A1.3 lands here or in `quality-assurance.md` | **CLOSURE** |
| `specs/memory/quality-assurance.md` | the census sentence and the two justified-timeout citations rewritten (A18.6); the mutation tool + invocation recorded (A20.2); the new **Complexity And Size** governance section (A21.6); the intent-declaration shape (A19.3) | **CLOSURE** |
| `specs/memory/.heading-allowlist` | the 12 enumerated `LINT-1` headings (A13.3) and the new governance heading (A21.6) | **CLOSURE** |
| `specs/memory/product/sdd/sdd-gate-v3.md` | blob-only non-goal retired, coverage becomes blob + commit-object (A11.5); the baseline cadence, version and single-line constraint as product truth (FR12); the MEMORY path-class decision (FR13); the venv-guard cache rule (FR28) — **one authoring pass, one task** | **CLOSURE** |
| `specs/memory/product/sdd/sdd-bug-backlog-governance.md` | the `picked` reservation event and its coherence rules (FR14) | **CLOSURE** |
| `specs/memory/product/agents/agent-comms.md` | ack-on-consume retention for coordination vs artifact-bearing handoffs (FR23) | **CLOSURE** |
| `specs/memory/product/agents/agent-monitoring.md` | release-closure GC of run records; reconciler reaping; log rotation (FR25, FR26, FR27) | **CLOSURE** |
| `specs/memory/product/agents/agentic-entities.md` | the decided `dadaia-cli` reachability on the derivation surface (FR5); the skill-collision check (FR2) | **CLOSURE** |
| `specs/memory/product/harness/harness-codex.md` | law-load-once, live certification, ENT-DERIVE-1 behavioral fidelity (FR22) | **CLOSURE** |
| `specs/memory/product/distribution/public-asset-distribution.md` | the thin-wrapper contract (FR16); the repo-`AGENTS.md` symlink refusal made true (FR17) | **CLOSURE** |
| `specs/memory/product/platform/consumer-agent-support.md` | the round's result and the honestly-recorded environment limits (FR30) | **CLOSURE** |
| `specs/memory/product/sdd/specs-doctor.md` | the `tests/AGENTS.md` placeholder check (FR8); the baseline-rationale check (FR12); the segment-router ERROR from the Arm-B rider | **CLOSURE** |
| `specs/memory/product/distribution/pypi-distribution.md` | the CHANGELOG lineage statement (FR31) | **CLOSURE** |
| `specs/memory/product/index.md` + `catalog.json` | regenerated; `index.md` touched only if the catalog order or membership changed | **CLOSURE** |
| `specs/memory/architecture.md` | only if FR16's package/wrapper seam or FR14's schema changes a layer contract — otherwise "no change" with the reason stated | **CLOSURE** |

**One memory task per atom**, authored in a single pass after every contributing FR is
`[x]` (D9/D21: three FRs target the 5k-token gate atom; v0.4.2 over-ran its declared
memory write set in three places by editing an atom in pieces).

### Closure obligations (not implementation FRs)

- **Disposition sweep.** The 24 consumed slugs reach `DELIVERED · v0.4.3` (or
  `SUPERSEDED · v0.4.3` for #37) as `LEDGER` lines; the rejected idea's line is already
  written at definition. `## Dispositions` records each with an evidence pointer, plus the
  `alpha-2` Arm-B rider bug as `Closed`, and states explicitly that **no backlog-picked
  bug and no audit** was in the pick.
- **`## ACTIVE` is empty** and stays empty — the release's headline acceptance (A32.5).
- **Test dispositions.** FR18's demotion map and every quarantine/SCAFFOLD expiry.
- **`## Size accounting`** table, filled with measured values (A21.5).
- **Record-only vs intake (FR6 calibration, in force).** Two sections; record-only
  observations terminate in CLOSURE; only actionable defects reach the PM's intake report.
- **Residual budget.** Zero actionable intake candidates. Any actionable defect surfaced by
  any review in any segment is fixed **in that segment**, or escalated to the operator **at
  the moment of discovery** — never accumulated for the closure. A defect found after the
  final review is registered as a bug (Arm B) and fixed on the spot; it never becomes
  backlog demand. The one honest exception: FR30 runs against an external surface and may
  surface a defect too large to absorb — that requires an **operator-ratified exception
  taken knowingly**, not discovered at closure.
- **R9 restatement.** The git-identity question is restated for the operator's ruling.
- **PE-1 record.** CLOSURE states that the two bugs that outranked the queue were closed by
  Arm B before the pick, with their evidence — the precedence claim is measured, not asserted.

---

## 6. Dependencies and risks

| # | Item | Status / mitigation |
|---|---|---|
| D-1 | `product-engineer` has no shell | every git, CLI and measurement step is an explicit TASKS entry owned by the dispatcher, `software-engineer`, `ai-engineer` or `qa-engineer` |
| D-2 | **FR1 before FR20** — the pin rule must exist before a sixth third-party tool is wired | TASKS precondition; FR1 is the first implementation task of the release |
| D-3 | **FR18 before FR19 and FR20** — the check is unsatisfiable and the score is noise on a suite mid-remediation | segment order + TASKS preconditions |
| D-4 | **`alpha-1` before `alpha-4`** — the Codex renderer consumes persona/skill frontmatter | segment order |
| D-5 | **FR15 needs no ruling** — R6 settled it | closed |
| D-6 | **FR13's allowlist write is MEMORY-class** — it cannot land mid-implementation | the enumeration lands in `alpha-2`; the file edit rides the `rc-1` memory window |
| D-7 | **FR9 ∥ FR10** are the only sanctioned parallel pair (disjoint write sets: `python_env.py` vs `git_subprocess.py`) | declared in TASKS; everything else is one `[-]` at a time |
| D-8 | **`ACTIVE.md` `segment:` stays `none`** (D1, ratified) — because a non-`none` value pointing at a missing directory silently disables `SPEC-DOC-004` and `TREE-6` | that silent skip is **registered** as bug `specs-doctor-segment-router-silent-skip` (MEDIUM) and fixed as the `alpha-2` Arm-B rider (T-043-22, AB.1–AB.5); D1 stands regardless of the fix, because the document-set shape is a knowledge-duplication decision, not a doctor workaround |
| D-9 | **`alpha-5` (GC) before `alpha-6` (consumer)** per R10 | the consumer round certifies the assembled surface including GC (A30.6); no delta re-check exists or is needed |
| R1 | **Release size.** 25 records + 2 folded items + 1 Arm-B rider, 32 FRs — ~1.9× v0.4.2, the largest ever shipped here | segmentation (R1) + the declared residual budget + FR6 routing + review-before-archive. Three of those four mechanisms shipped days ago and are unproven at this scale |
| R2 | **WS-G is L-sized** (7 FRs across hooks, CLI, skills and the chokepoint) and now lands second-to-last | capability-level task split, fail-open posture as acceptance, each capability independently revertible; and — the R10 gain — the consumer round runs **after** it, so a GC regression is caught inside the release rather than after ship |
| R3 | **The consumer round is now the last gate before `rc-1`** — a late failure has less runway | one remediation cycle budgeted inside `alpha-6` (A30.5); R7 fixed the environment question before the segment opens; a finding too large to absorb goes to the operator at the moment of discovery |
| R4 | **FR18 destabilizes the suite** — deletions and demotions on a ~2,300-test suite whose census every other segment could perturb | census-freeze rule; verdict-only steward; no deletion without a named replacement or a recorded "behaviour removed"; measure at both ends |
| R5 | **FR20 adds a supply-chain surface** | FR1 lands first and covers quality tooling; off the push path; bounded wall clock |
| R6 | **FR30 can re-open the release** — a consumer-side failure is by law a release blocker | one remediation cycle budgeted inside `alpha-6`; the round's scope is fixed before the segment opens |
| R7 | **FR21 fires on day one** if the ceiling is aspirational | R8's measure-then-pin, in the **same** task; A21.2 makes green-at-landing an acceptance |
| R8 | **Memory window overload** — 13 atoms, one of them targeted by four FRs | one memory task per atom, single authoring pass, atoms declared in §5, catalog regenerated |
| R9 | **Eight `public/**` records, one manifest** — a partial projection leaves staged/projected drift | one projection cycle at the end of `alpha-1`, with the three `[ok]` lines captured as segment evidence |
| R10 | **FR22 sprawls** — intents authored by another session against an older tree; one already struck, one sub-claim void | its own scoping task first, each surviving intent given an acceptance id, byte baseline re-measured, A22.8's zero-diff constraint |

---

## 7. Traceability and provenance

| Entry | Provenance | Disposition in this release |
|---|---|---|
| `test-suite-remediation-stewardship` (#2) | operator request, v0.7.0 lineage; rewritten under grill ADR #6 | **picked** · FR18 · `DELIVERED · v0.4.3` |
| `consumer-side-validation-round` (#5) | v0.8.0 grill ADR #1; intake #3 item 3-20 folded | **picked** · FR30 (R7, `alpha-6`) · discharges two archived audits' inherited findings |
| `thin-wrapper-projected-scripts` (#6) | v0.8.0 grill ADR #2 (W6 extraction) | **picked** · FR16 · absorbs v0.4.2 RO-5 |
| `bug-picked-ledger-event` (#7) | grill ADR #10/E-4 | **picked** · FR14 |
| `codex-persona-law-context-dehydration` (#8) | adopted from a parallel Codex session; intake #2 item 2-7 merged | **picked, scope-corrected** · FR22 · intent 6 struck (delivered), 12-persona sub-claim struck (void) |
| `python-env-interpreter-probe-hardening` (#9) | APPROVED v0.5.1 security-review LOW routing | **picked** · FR9 |
| `panel-runtime-reliability-dangling-ledger-pointer` (#12) | v0.8.0 CLOSURE return | **picked** · FR15 (R6) |
| `mutation-testing-tool-selection-and-wiring` (#13) | v0.7.0 CLOSURE return, grill ADR #5 | **picked** · FR20 |
| `intent-docstring-mechanical-enforcement` (#14) | v0.7.0 CLOSURE return, grill ADR #5 | **picked** · FR19 · unblocked by FR18 |
| `gitflow-reconciliation-merge-mechanic` (#15) | v0.7.0 CLOSURE return, grill ADR #5 | **picked** · FR6 |
| `memory-path-class-dotfiles` (#16) | v0.7.0 CLOSURE return, grill ADR #5 | **picked, extended** · FR13 · folds the 12 standing `LINT-1` warnings |
| `commit-paths-index-scope-hardening` (#18) | APPROVED v0.5.2 security-review LOW routing | **picked** · FR10 |
| `commit-message-scanning-residual` (#21) | v0.9.0 SPEC §4.2 operator-ratified non-goal | **picked** · FR11 |
| `baseline-carve-out-review-cadence` (#24) | v0.9.0 CLOSURE return; intake #3 item 3-1; residual after v0.4.2's partial pick | **picked in full** · FR12 · **absorbs** the co-author-trailer gap and CR-6 |
| `dd-skills-applyto-glob-collisions` (#32) | intake #2 item 2-1 | **picked, acceptance rewritten** · FR2 (R2) |
| `dd-release-definition-orchestration-pointer-loop` (#33) | intake #2 item 2-3 | **picked** · FR3 |
| `bug-event-redaction-always-on-reinforcement` (#34) | intake #2 item 2-4 | **picked, ruling-resolved** · FR4 (R3) · pointer half `DELIVERED` at `DADAIA.md:235-236`, content sentence implemented |
| `dd-audit-project-pinned-tool-installs` (#35) | intake #2 item 2-5 | **picked, first** · FR1 |
| `dadaia-cli-skill-agent-grant` (#36) | pre-approved intake P-3 | **picked** · FR5 |
| `codex-skill-ref-phantom-memory-ctx-prefix` (#37) | pre-approved intake P-4 | **picked by MERGE into #8** · inside FR22 (A22.6) · `SUPERSEDED · v0.4.3` |
| `dadaia-artifact-event-driven-gc` | operator request, approved in-session 2026-08-17 (ADR #15 direct intake) | **picked** · FR23–FR29 · WS-G, **`alpha-5`** (R10) |
| `repo-agents-md-symlink-hardening` (idea) | v0.7.0 CLOSURE return | **picked** · FR17 |
| `stewardship-relocation-grep-homonym-note` (idea) | v0.7.0 CLOSURE return | **picked** · FR7 |
| `tests-agents-md-placeholder-doctor-warning` (idea) | v0.7.0 CLOSURE return | **picked** · FR8 |
| `bugs-jsonl-whole-blob-per-append` (idea) | v0.9.0 CLOSURE return (ideas lane) | **REJECTED** (R4) · `LEDGER` line written **in this definition commit**, reason recorded · not declared in `**Consumes:**` |
| co-author-trailer carve-out gap | APPROVED v0.4.2 main-reconciliation security review, 2026-08-17T13:27:20Z | **folded into #24** · FR12/A12.2 · no entry materialized (ADR #15) |
| CHANGELOG backfill | v0.4.2 CLOSURE, the release's single intake candidate | **folded, ruled** · FR31 (R5) · never becomes an `ACTIVE` entry |
| bug `specs-doctor-segment-router-silent-skip` | found while authoring this definition; registered 2026-08-17 (MEDIUM) | **Arm-B rider** · T-043-22 (AB.1–AB.5) in `alpha-2` · not backlog demand, not an FR |
| Open bugs at pick | `specs/bugs/bugs.jsonl` | **none** — the two that outranked the queue were closed by Arm B before the pick (`:889`, `:891`; commits `7971eefb`, `9a09b551`). No bug is superseded or dropped |
| Audits | `specs/audits/_archive/` | **none outstanding** — every audit archived and dispositioned |

**Pick tally.** 25 `ACTIVE` = **22 implement** + **1 merge** (#37 → #8) + **1
ruling-resolved** (#34) + **1 rejected** (sharding idea); plus **2 folded external items**
(CHANGELOG → FR31, trailer gap → FR12) and **1 Arm-B rider bug**. Twenty-four slugs
declared in `**Consumes:**`.

**Purge-on-pick (`dd-backlog-definition` §2).** All **25** `ACTIVE` subsections were
removed from `specs/backlog/BACKLOG.md` in the **same commit** that creates this SPEC;
this section is the provenance record that removal requires. `## ACTIVE` is now **empty** —
the state the release must preserve to `rc-1`. The 24 consumed slugs receive their
`LEDGER` lines at the closure disposition sweep; the rejected idea's `LEDGER` line is
written in this commit, because its disposition is terminal at definition and nothing
awaits implementation.

**Version axis (one axis, v0.4.2 FR13).** The release id `v0.4.3` **is** the minted
package version `0.4.3`. `pyproject.toml:3` reads `0.4.2` at the branch cut and is bumped
in the ship task, together with the `[0.4.3]` `CHANGELOG.md` section — above FR31's
backfilled lineage.

---

## 8. Approval

**Approved by the operator on 2026-08-17** (operator-delegated, goal directive — "fila
inteira em 1 release"), **as written**. SPEC, PLAN and TASKS all carry
`**Status:** Aprovado`; milestone (a) of the `dadaia-gitflow` contract may fire once the
definition commit lands.

Ratified with the approval: **R1–R10 as given** — segmentation; #32's rewritten
acceptance; #34's honest terminal; the sharding rejection; the CHANGELOG's minimal honest
form; no new disposition token; the throwaway real consumer workspace; the measured
complexity ratchet; the git-identity question left with the operator; and the `alpha-5`/
`alpha-6` swap that puts the consumer round last. **D1 stands as authored** (ratified),
**D2** holds, and **D3 is withdrawn** — superseded by R10.
