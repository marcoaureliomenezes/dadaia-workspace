# TASKS — Release v0.4.3 — claims-made-true / backlog-zero

**Status:** Aprovado
**Approval provenance:** operator-delegated, 2026-08-17 (fila inteira em 1 release — goal directive)
**Release ID:** v0.4.3
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.4.3/SPEC.md`
**Source PLAN:** `specs/releases/v0.4.3/PLAN.md`
**Branch:** `feature/0.4.3` (cut from `develop` at `84e369a0`; branch contract: `dadaia-gitflow`)
**Segments:** `alpha-1` … `alpha-6` → `rc-1` (ADR R1, order amended by **R10**). This file
is the single marker surface for all of them (ADR D1, ratified) — the blocks below are the
segments.

## Task status markers

- `[ ]` OPEN · `[-]` IN PROGRESS · `[x]` DONE

## Segment map

| Segment | Tasks | Contents | Gate |
|---|---|---|---|
| W0 | T-043-01 … 02 | definition commit + milestone (a) | APPROVED security verdict on the pushed delta |
| `alpha-1` | T-043-03 … 12 | WS-D — the AI surface (FR1–FR8) | `qa-engineer` review committed |
| `alpha-2` | T-043-13 … 23 | WS-B + WS-E — gate hardening + governance primitives (FR9–FR17) **+ the Arm-B rider** (T-043-22) | `qa-engineer` review + `security-reviewer` on the gate delta |
| `alpha-3` | T-043-24 … 31 | WS-A — suite, measurements, complexity governance (FR18–FR21) | `qa-engineer` review + demotion map draft |
| `alpha-4` | T-043-32 … 37 | WS-C — the Codex fidelity boundary (FR22) | `qa-engineer` review + certification evidence |
| `alpha-5` | T-043-38 … 45 | **WS-G — event-driven artifact GC (FR23–FR29)** (R10: before the consumer round) | `qa-engineer` review |
| `alpha-6` | T-043-46 … 49 | **WS-F — consumer round + CHANGELOG (FR30, FR31)** (R10: runs last, certifies GC too) | `qa-engineer` review |
| `rc-1` | T-043-50 … 53 | review → memory → CLOSURE + archive → ship | full trio, then the PR to `main` |

Order within the release is fixed: **review → closure → archive → ship** (D8/FR5). The
six-axis review is its own task and runs on a **thawed** tree, before the archive move.

## Standing rules for this release

- **`product-engineer` has no shell.** Every task marked **[git]** or carrying a command is
  executed by the dispatcher, `software-engineer`, `ai-engineer` or `qa-engineer`.
  `product-engineer` authors text only.
- **Shell-less reservation obligation.** When the dispatcher relays work for a shell-less
  sub-agent, it commits that sub-agent's `[ ]`→`[-]` flip **before** relaying the next work
  item — never batched. Applies to T-043-51 and T-043-52.
- **Reservation is observable.** Flip `[ ]`→`[-]` and commit `chore(tasks): start <id>`
  before the work (`dadaia-task-manager`). One `[-]` at a time — the **only** sanctioned
  parallel pair is T-043-13 ∥ T-043-14 (disjoint write sets).
- **Green at every commit:** `dadaia ci preflight`, `dadaia backlog doctor`,
  `dadaia specs doctor`, `dadaia public doctor`. **No `--no-verify`, ever.**
- **RED before GREEN.** Every behavioural task writes its failing test first and observes it
  failing for the real reason.
- **Satisfiable diagnostics.** Every new check is green at HEAD the moment it lands, and no
  new check goes silent where it should error (T-043-22 is the worked example).
- **Test intent at birth.** `Intent: CONTRACT — v0.4.3 <A-id>` or `Intent: SENTINEL — <seam>`.
  **Zero new `tests/e2e/**` tests** without a named `qa-engineer` exception recorded in that
  segment's QA artifact.
- **Never prune to go green.** A deletion, skip or disable is a `qa-engineer` verdict with
  evidence, executed by `software-engineer`.
- **Lane discipline.** `ai-engineer` performs **every** skill/persona/rule/projected-asset
  edit; `software-engineer` every production-code and test edit; `project-manager` any
  backlog-file mechanics after T-043-01; `product-engineer` only specs and memory.
- **Escalate at discovery.** An actionable defect found mid-segment is fixed in that segment
  or escalated to the operator immediately — never accumulated for the closure. A defect in
  the tooling itself is **registered as a bug and fixed as an Arm-B rider**, like T-043-22.
- **A group of completed work is one commit** — stage exactly the task's write set, never `-A`.
- **Measurements** (V1–V13, PLAN §4) are captured under `.dadaia/tmp/<agent>/<YYYYMMDD>/`
  and cited as CLOSURE evidence.

## Acceptance and evidence map

| Task | Entry / FR | Acceptance ids | Evidence |
|---|---|---|---|
| T-043-01 | — | — | definition commit sha; `ACTIVE.md` reads `IMPLEMENTATION`; empty `## ACTIVE` |
| T-043-02 | — | SPEC §7 precedence | V1 + V2 capture, pushed `develop` sha, APPROVED security handoff |
| T-043-03 | #35 / FR1 | A1.1–A1.4 | skill diff, zero-hit grep |
| T-043-04 | #32 / FR2 | A2.1–A2.4 | frontmatter diff, check green at HEAD |
| T-043-05 | #33 / FR3 | A3.1–A3.2 | skill diff, grep |
| T-043-06 | #34 / FR4 | A4.1–A4.3 | law-source diff + projection byte-identity |
| T-043-07 | #36 / FR5 | A5.1–A5.3 | frontmatter diff + derivation test |
| T-043-08 | #15 / FR6 | A6.1–A6.2 | skill diff |
| T-043-09 | idea / FR7 | A7.1–A7.2 | skill diff |
| T-043-10 | idea / FR8 | A8.1–A8.3 | RED-then-GREEN output |
| T-043-11 | — | A32.2 | V9 capture, manifest hash parity |
| T-043-12 | all `alpha-1` | A1–A8 ids | `qa-engineer` artifact |
| T-043-13 | #9 / FR9 | A9.1–A9.3 | RED-then-GREEN output |
| T-043-14 | #18 / FR10 | A10.1–A10.3 | RED-then-GREEN output |
| T-043-15 | #21 / FR11 | A11.1–A11.5 | reconciliation fixture output |
| T-043-16 | #24 + trailer / FR12 | A12.1–A12.6 | fixture + baseline diff + `public-privacy` |
| T-043-17 | #16 / FR13 | A13.1–A13.3 | V3 capture + gate fixtures |
| T-043-18 | #7 / FR14 | A14.1–A14.4 | schema + CLI output |
| T-043-19 | #12 / FR15 | A15.1–A15.3 | appended event + byte-unchanged proof |
| T-043-20 | #6 + RO-5 / FR16 | A16.1–A16.4 | wrapper contract test |
| T-043-21 | idea / FR17 | A17.1–A17.2 | per-site fixtures |
| **T-043-22** | **bug `specs-doctor-segment-router-silent-skip`** | **AB.1–AB.5** | RED-then-GREEN output + `resolved` event |
| T-043-23 | all `alpha-2` | A9–A17 ids, AB ids | `qa-engineer` + `security-reviewer` artifacts |
| T-043-24 | #2 / FR18 | A18.1 | V4 capture + offender list |
| T-043-25 | #2 / FR18 | A18.2, A18.4 | per-verdict evidence, commit shas |
| T-043-26 | #2 / FR18 | A18.3, A18.5 | V5 capture + demotion map draft |
| T-043-27 | #14 / FR19 | A19.1–A19.3 | check green at HEAD |
| T-043-28 | #13 / FR20 | A20.1–A20.4 | V11 capture + pinned invocation |
| T-043-29 | governance / FR21 | A21.1–A21.3 | V6 capture + `pyproject.toml` diff |
| T-043-30 | governance / FR21 | A21.4 | skill template diff |
| T-043-31 | all `alpha-3` | A18–A21 ids | `qa-engineer` artifact |
| T-043-32 | #8 / FR22 | A22.1 (baseline) | V7 capture + scoping note |
| T-043-33 | #8 / FR22 | A22.1–A22.2 | TOML diff + executed-path evidence |
| T-043-34 | #8 / FR22 | A22.3–A22.4 | live-probe output |
| T-043-35 | #8 + #37 / FR22 | A22.5–A22.6 | mutation fixtures + inventory test |
| T-043-36 | #8 / FR22 | A22.7–A22.8 | V8 byte-diff |
| T-043-37 | all `alpha-4` | A22.x | `qa-engineer` artifact + certify evidence |
| T-043-38 | GC / FR23 | A23.1–A23.3 | skills diff + fixtures |
| T-043-39 | GC / FR24 | A24.1–A24.3 | push fixtures |
| T-043-40 | GC / FR25 | A25.1–A25.3 | skill template diff |
| T-043-41 | GC / FR26 | A26.1–A26.3 | V10 capture |
| T-043-42 | GC / FR27 | A27.1–A27.3 | rotation fixtures |
| T-043-43 | GC / FR28 | A28.1–A28.3 | block-message fixtures |
| T-043-44 | GC / FR29 | A29.1–A29.4 | dry-run + idempotency output |
| T-043-45 | all `alpha-5` | A23–A29 ids | `qa-engineer` artifact |
| T-043-46 | #5 / FR30 | A30.1–A30.4, A30.6 | round artifact incl. recorded limits + GC coverage |
| T-043-47 | #5 / FR30 | A30.5 | remediation commits or "unused" statement |
| T-043-48 | CHANGELOG / FR31 | A31.1–A31.4 | `CHANGELOG.md` diff + range citations |
| T-043-49 | all `alpha-6` | A30–A31 ids | `qa-engineer` artifact |
| T-043-50 | all | A32.1–A32.4 | `code-reviewer` APPROVED on a **thawed** tree |
| T-043-51 | all | SPEC §5 | memory diff; `specs doctor` 0 errors, 0 `LINT-1` |
| T-043-52 | all picked | A32.5, closure obligations | `CLOSURE.md`; empty `## ACTIVE`; V12 |
| T-043-53 | — | — | `0.4.3` published lineage bump; PR merged to `main`; CI green; V13 |

---

## W0 — definition

- [ ] **T-043-01 — [git] Commit the definition content on `feature/0.4.3`**

**Owner role:** software-engineer (or dispatcher) · **Commit:**
`docs(T-043-01): v0.4.3 definition — claims-made-true / backlog-zero`

**Preconditions:** `GRILL.md`, `SPEC.md`, `PLAN.md`, `TASKS.md` authored and carrying
`**Status:** Aprovado`; working tree on `feature/0.4.3`.

**Write set (staging only — content already authored by `product-engineer`):**
`specs/releases/ACTIVE.md`, `specs/releases/v0.4.3/{GRILL,SPEC,PLAN,TASKS}.md`,
`specs/backlog/BACKLOG.md` (purge-on-pick: all 25 `## ACTIVE` subsections removed, the
rejected idea's `LEDGER` line written).

**Description:** Stage exactly those paths and commit — the pick and the SPEC ride one
commit (`DADAIA.md` §5). Flip `ACTIVE.md` phase `DEFINITION` → `IMPLEMENTATION` in the same
commit. The pre-commit backlog gate fires and must pass.

**Done criterion:** one commit with exactly those paths; `ACTIVE.md` reads
`release: v0.4.3` / `phase: IMPLEMENTATION`; `## ACTIVE` empty; `backlog doctor` and
`specs doctor` clean.

**Parallelism:** none — first task.

---

- [ ] **T-043-02 — [git] Milestone (a): measure, merge, security review, push**

**Owner role:** dispatcher + `security-reviewer` · **Commit:** merge commit on `develop`

**Preconditions:** T-043-01 `[x]`.

**Write set:** git refs only (`develop`), plus the security handoff under
`.dadaia/handoff/dadaia-workspace/` and V1/V2 captures under `.dadaia/tmp/<agent>/<date>/`.

**Description:** Run **V1** (`dadaia bugs status`) and **V2** (`specs doctor`,
`backlog doctor`) and capture both — V1 confirms SPEC §7's pick-time zero-open-bug claim
(the `alpha-2` rider bug was registered after the pick and is expected to appear as open),
V2 fixes the baseline the `rc-1` delta is measured against. Then per `dadaia-gitflow`
milestone (a), in order: merge `feature/0.4.3` into local `develop`; run a **diff-based**
`security-reviewer` review of `origin/develop..develop`; push `develop`.

**Done criterion:** V1 and V2 captured and consistent with SPEC §7; `develop` pushed;
APPROVED handoff covering the pushed delta; CI green.

**Parallelism:** none.

---

## `alpha-1` — WS-D, the AI surface

- [ ] **T-043-03 — FR1: pin every prescribed third-party install**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-03): pin the audit and quality tool installs`

**Preconditions:** T-043-02 `[x]`. **Lands first in the release** (D-2): FR20 inherits this rule.

**Write set:** `dadaia_workspace/public/skills/dd-audit-project/SKILL.md` + projections.

**Description:** Replace the five unpinned installs (`:107`, `:118`, `:121`, `:132`, `:142`)
with exact version or hash pins, and state the pinning rule once, worded to cover audit
**and** quality tooling. The memory doctrine line (A1.3) rides the `rc-1` memory window.

**Done criterion:** A1.1, A1.2, A1.4 hold; `public doctor` green.

**Parallelism:** none.

---

- [ ] **T-043-04 — FR2: resolve the two duplicate `dd-` activation claims (R2 scope)**

**Owner role:** ai-engineer · **Commit:** `fix(T-043-04): narrow the duplicate dd- applyTo claims and check undeclared overlap`

**Preconditions:** T-043-03 `[x]`.

**Write set:** `public/skills/dd-backlog-definition/SKILL.md`,
`public/skills/dd-release-definition/SKILL.md`, `public/skills/dd-bug-registration/SKILL.md`,
`public/skills/dd-bug-fix/SKILL.md`, the collision check and its fixtures, + projections.

**Description:** Narrow each duplicate pair to the sub-path its stage owns; document the
precedence rule (universal `**` skills are always-on and never compete). The check flags
**only undeclared overlap between non-universal skills** — it must never assert anything
about `applyTo: "**"` skills or `dadaia-grill-me`'s `specs/**` (R2).

**Done criterion:** A2.1–A2.4 hold; the check is green at HEAD.

**Parallelism:** none.

---

- [ ] **T-043-05 — FR3: break the release-definition pointer loop**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-05): drop the dd-release-definition back-pointer`

**Preconditions:** T-043-04 `[x]`. **Write set:** `public/skills/dd-release-definition/SKILL.md` + projection.

**Description:** Drop the back-pointer at `:106-107`, leaving the `DADAIA.md` §5 reference;
`project-orchestration` keeps its dispatch note naming what it owns.

**Done criterion:** A3.1, A3.2 hold.

**Parallelism:** none.

---

- [ ] **T-043-06 — FR4: one always-on sentence naming the forbidden bug-event field content**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-06): name the redaction rule's forbidden field content in law §6`

**Preconditions:** T-043-05 `[x]`.

**Write set:** `dadaia_workspace/public/data/DADAIA.md` (**source only** — projected law
files are human-only and PROTECTED), then `public stage` + `public install --target all`.

**Description:** §6's register-every-bug paragraph gains exactly one sentence: absolute
local paths, IPs, hostnames, private names and secrets never enter an event field. The
existing pointer sentence (`:235-236`) stays or is absorbed — never duplicated. No edit to
`dd-bug-registration` §3.

**Done criterion:** A4.1–A4.3 hold; every projected copy is byte-identical to the source.

**Parallelism:** none.

---

- [ ] **T-043-07 — FR5: make `dadaia-cli`'s grant and description agree**

**Owner role:** ai-engineer · **Commit:** `fix(T-043-07): reconcile the dadaia-cli grant with its description`

**Preconditions:** T-043-06 `[x]`.

**Write set:** `public/skills/dadaia-cli/SKILL.md`, the affected agent frontmatters, the
derivation surface, a new test, + projections.

**Description:** Decide reachability per agent with a written reason — never a blanket
grant. A shell-less agent (`product-engineer`) is excluded explicitly. The test derives the
expectation from the frontmatters so drift fails loud.

**Done criterion:** A5.1–A5.3 hold.

**Parallelism:** none.

---

- [ ] **T-043-08 — FR6: record the reconciliation-merge mechanic**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-08): record the reconciliation-merge mechanic in dadaia-gitflow`

**Preconditions:** T-043-07 `[x]`. **Write set:** `public/skills/dadaia-gitflow/SKILL.md` + projection.

**Description:** One statement: every squash-merge to `main` is followed by a reconciliation
merge of `main` into `develop`, resolving resurrected loose copies in favour of `develop`'s
archives. v0.4.2's ship (`84a66d13`) is the worked example.

**Done criterion:** A6.1, A6.2 hold — the statement exists exactly once across `public/`.

**Parallelism:** none.

---

- [ ] **T-043-09 — FR7: note the stewardship vocabulary's homonyms**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-09): note the scaffold/sentinel/quarantine homonyms`

**Preconditions:** T-043-08 `[x]`. **Write set:** `public/skills/dadaia-test-stewardship/SKILL.md` + projection.

**Description:** A short note naming the three colliding terms and their unrelated homes, so
T-043-24's greps do not chase homonyms.

**Done criterion:** A7.1 holds; T-043-24 cites it (A7.2).

**Parallelism:** none.

---

- [ ] **T-043-10 — FR8: warn on an installed `tests/AGENTS.md` with unfilled placeholders**

**Owner role:** software-engineer · **Commit:** `feat(T-043-10): report placeholder tokens in an installed tests/AGENTS.md`

**Preconditions:** T-043-09 `[x]`.

**Write set:** `dadaia_workspace/features/specs/doctor.py` (the `MEM-PLACEHOLDER-1`
validator family), its tests.

**Description:** Reuse the existing validator shape. The check runs against the **installed
consumer** file only — the canonical template legitimately carries placeholders. RED first.

**Done criterion:** A8.1–A8.3 hold; `specs doctor` green on this workspace.

**Parallelism:** none.

---

- [ ] **T-043-11 — [git] `alpha-1` projection cycle and evidence**

**Owner role:** ai-engineer · **Commit:** `chore(T-043-11): project the alpha-1 public surface`

**Preconditions:** T-043-03 … T-043-10 all `[x]`.

**Write set:** the projected trees (`.claude/`, `.codex/`, `.kimi-code/`, `.agents/`) and
the staged canonical assets.

**Description:** One cycle: `dadaia public stage` → `dadaia public install --target all` →
`dadaia public doctor`. Capture **V9** with all three `[ok]` lines.

**Done criterion:** A32.2 holds for this segment; staged/projected hashes agree.

**Parallelism:** none.

---

- [ ] **T-043-12 — `alpha-1` close: `qa-engineer` review**

**Owner role:** qa-engineer · **Commit:** `test(T-043-12): alpha-1 qa review`

**Preconditions:** T-043-11 `[x]`. **Write set:** the QA artifact + handoff.

**Description:** Verify every `alpha-1` acceptance id; name any id that could not be
verified rather than reporting it passed. Segment gate only — no closure, no ship.

**Done criterion:** APPROVED `qa-engineer` artifact committed to the branch; PLAN §5
`alpha-1` exit criteria met.

**Parallelism:** none.

---

## `alpha-2` — WS-B + WS-E, gate hardening and governance primitives

- [ ] **T-043-13 — FR9: interpreter-probe hardening (CWE-426 + timeout/stdin)**

**Owner role:** software-engineer · **Commit:** `fix(T-043-13): reject relative interpreter candidates and bound the probe`

**Preconditions:** T-043-12 `[x]`. **Write set:** `infrastructure/python_env.py` + its tests.

**Description:** RED first with a fixture returning a bare name and one that hangs. Filter
on `os.path.isabs()` for both `which` results and the `pyvenv.cfg` value; pass a bounded
`timeout=` and `stdin=subprocess.DEVNULL`.

**Done criterion:** A9.1–A9.3 hold.

**Parallelism:** **sanctioned pair with T-043-14** — disjoint write sets (D-7).

---

- [ ] **T-043-14 — FR10: `commit_paths` index-scope hardening**

**Owner role:** software-engineer · **Commit:** `fix(T-043-14): check git add and path-scope the commit`

**Preconditions:** T-043-12 `[x]`. **Write set:** `infrastructure/git_subprocess.py`,
`core/protocols/git_client.py` (docstring/defence note), + tests.

**Description:** RED first: stage unrelated content, then prove it lands in the commit.
Raise `GitSyncError` on a non-zero `git add`; path-scope the commit; apply or explicitly
decline the pathspec-magic defence with a recorded reason.

**Done criterion:** A10.1–A10.3 hold.

**Parallelism:** **sanctioned pair with T-043-13**.

---

- [ ] **T-043-15 — FR11: the push scan reads commit objects**

**Owner role:** software-engineer (acceptance co-signed by `security-reviewer`) · **Commit:**
`feat(T-043-15): scan the pushed range's commit objects`

**Preconditions:** T-043-13 `[x]`, T-043-14 `[x]`.

**Write set:** `container.py` (the reader seam), `features/chokepoints/service.py`,
`core/protocols/git_object_reader.py`, `infrastructure/git_objects.py`, + fixtures.

**Description:** Extend the reader to yield the range's commit objects and annotated tag
bodies through the same batched conversation and typed-error contract; feed them through
the same three term layers with the same masked, satisfiable refusal (healing action:
reword/amend). The v0.4.2 reconciliation shape — two commits, **zero blobs** — is an
acceptance fixture. RED first.

**Done criterion:** A11.1–A11.4 hold; A11.5's memory edit is deferred to T-043-51.

**Parallelism:** none.

---

- [ ] **T-043-16 — FR12: the privacy baseline stops growing literal by literal**

**Owner role:** software-engineer (acceptance co-signed by `security-reviewer`) · **Commit:**
`fix(T-043-16): baseline rationale check, structural dotted-chain rule, trailer carve-out`

**Preconditions:** T-043-15 `[x]`.

**Write set:** `infrastructure/privacy_check.py`, `infrastructure/data/privacy_baseline.json`
(version bump + `_header.excludes`), the rationale check + its doctor wiring, fixtures.

**Description:** Three parts plus two folded escapes: the rationale check; the cadence and
single-line constraint (recorded as memory truth at T-043-51); the structural rule for the
`internal-hostname` dotted-chain class; the Windows trailing-period escape (CR-6); and the
`noreply@anthropic.com` **local-part** carve-out with a counter-fixture proving a genuine
address at the same domain still fires.

**Done criterion:** A12.1–A12.6 hold; `public doctor` `[ok] public-privacy`; sentinel green.

**Parallelism:** none.

---

- [ ] **T-043-17 — FR13: decide the MEMORY path class and enumerate the standing lint warnings**

**Owner role:** software-architect (doctrine) + software-engineer (code) · **Commit:**
`fix(T-043-17): encode the memory path-class decision for dotfiles`

**Preconditions:** T-043-16 `[x]`.

**Write set:** `features/spec_context/gate_policy.py` + fixtures; the **V3** capture under
`.dadaia/tmp/`.

**Description:** Encode (a) whether memory dotfiles are MEMORY-class or a documented
carve-out and (b) how the gate treats a SPEC-assigned memory write outside
`DEFINITION`/`CLOSURE` — as code **plus** a stated rule, never an ad-hoc exception. Capture
**V3**: the twelve `LINT-1` heading warnings by name. The `.heading-allowlist` edit itself
is MEMORY-class and rides T-043-51 (D-6).

**Done criterion:** A13.1, A13.2 hold; V3 captured and handed to T-043-51 (A13.3).

**Parallelism:** none.

---

- [ ] **T-043-18 — FR14: the `picked` bug-ledger event**

**Owner role:** software-architect (schema/coherence) + software-engineer · **Commit:**
`feat(T-043-18): add the non-terminal picked bug event`

**Preconditions:** T-043-17 `[x]`.

**Write set:** `core/models/bugs.py`, the `bug-event-v1` schema, the fold, `cli/commands/bugs.py`, tests.

**Description:** One change carries schema + fold + CLI (single-authority law). `picked` is
non-terminal; a repeated pick on an open stream is **allowed and surfaced** (NO-LOCKS); a
pick after a terminal event is incoherent. Older ledgers must still fold.

**Done criterion:** A14.1–A14.4 hold.

**Parallelism:** none.

---

- [ ] **T-043-19 — FR15: clarify the dangling deferral pointer**

**Owner role:** software-engineer · **Commit:** `fix(T-043-19): clarify the panel-runtime-reliability deferral pointer`

**Preconditions:** T-043-18 `[x]`. **Write set:** `specs/bugs/bugs.jsonl` via `dadaia bugs append` only.

**Description:** Append **one** clarifying event to
`panel-telemetry-sqlite-corrupts-under-concurrent-access` recording that the 2026-07-01
deferral target was already consumed by v0.1.52 at deferral time, and naming the corrected
disposition **with an existing token** (R6 — no new token). No existing line is modified.

**Done criterion:** A15.1–A15.3 hold; the 2026-07-01 line is byte-unchanged.

**Parallelism:** none.

---

- [ ] **T-043-20 — FR16: one logic, one source for projected scripts**

**Owner role:** software-engineer (package) + ai-engineer (`public/` half) · **Commit:**
`refactor(T-043-20): move the memory lint into the package and thin the projected scripts`

**Preconditions:** T-043-19 `[x]`.

**Write set:** `features/specs/doctor_memory.py`, the new in-package lint implementation,
`public/scripts/lint-memory-atoms.py`, `public/scripts/generate-memory-catalog.py`, the
contract tests, + projections.

**Description:** Invert the inversion: LINT-1 imports the shared implementation; the
projected script becomes a thin wrapper execing the workspace venv's package entry point; a
doctor/projection test asserts the contract. RO-5's duplicated `estimate_tokens` is removed
or CLOSURE states precisely why not. Delete the docstring note advertising the exception.

**Done criterion:** A16.1–A16.4 hold; `lint-imports` green with no new edge.

**Parallelism:** none.

---

- [ ] **T-043-21 — FR17: refuse a symlinked repo-`AGENTS.md` destination**

**Owner role:** software-engineer · **Commit:** `fix(T-043-21): harden the repo-AGENTS.md destination against symlinks`

**Preconditions:** T-043-20 `[x]`. **Write set:** `infrastructure/public_assets.py` + fixtures.

**Description:** Mirror the four refusal sites of the hardened sibling seam onto the
repo-`AGENTS.md` destination write, with a fixture per site. RED first.

**Done criterion:** A17.1, A17.2 hold — the memory atom's existing claim becomes true.

**Parallelism:** none.

---

- [ ] **T-043-22 — [Arm-B rider] The segment router errors instead of going silent**

*Bug: `specs-doctor-segment-router-silent-skip` (MEDIUM, registered 2026-08-17)*

**Owner role:** software-engineer · **Commit:**
`fix(T-043-22): error when ACTIVE.md names a missing segment directory`

**Preconditions:** T-043-21 `[x]`.

**Write set:** `dadaia_workspace/features/specs/doctor_release.py` (`:162-165`),
`dadaia_workspace/features/specs/doctor_structural.py` (`:339-342`), their tests; the
`resolved` event via `dadaia bugs append`.

**Description:** Arm B in full, riding this segment because it lives in the same doctor
surface. Reproduce on the executed path: an `ACTIVE.md` carrying a non-`none` `segment:`
whose directory does not exist currently makes **both** `SPEC-DOC-004` and `TREE-6` return
early with **no** finding — the stale comment claims check 9 already reported it, but
`check_active_md` validates only the **release** directory. RED first: a fixture with a
live segment pointer at a missing directory that today passes clean. Fix at the cause: emit
an explicit ERROR naming the missing segment directory, and correct or delete the stale
comment. Then append `resolved` with the reproducing test, the fix and the suite result,
and commit — staging exactly what the fix touched.

**Done criterion:** AB.1–AB.5 hold; the healthy segmented path and the flat path are both
unchanged; the bug is `Closed` with a clean worktree.

**Parallelism:** none.

---

- [ ] **T-043-23 — `alpha-2` close: `qa-engineer` review + security review of the gate delta**

**Owner role:** qa-engineer + security-reviewer · **Commit:** `test(T-043-23): alpha-2 qa review`

**Preconditions:** T-043-13 … T-043-22 all `[x]`. **Write set:** the QA artifact + handoffs.

**Description:** Verify every `alpha-2` acceptance id, including AB.1–AB.5;
`security-reviewer` covers the gate and baseline delta specifically (FR11, FR12).

**Done criterion:** APPROVED artifacts committed; PLAN §5 `alpha-2` exit criteria met.

**Parallelism:** none.

---

## `alpha-3` — WS-A, suite, measurements, complexity governance

- [ ] **T-043-24 — FR18a: measure the census and derive the offender list**

**Owner role:** qa-engineer · **Commit:** `test(T-043-24): capture the v0.4.3 LARGE census baseline`

**Preconditions:** T-043-23 `[x]`. **Write set:** the **V4** capture under `.dadaia/tmp/`; no source edits.

**Description:** Measure the live LARGE census (e2e-tier pytest journeys and Playwright
specs) and re-derive the offender list from the tree — the entry's own numbers are **void**
(A18.1). Cite T-043-09's homonym note before grepping the stewardship vocabulary.

**Done criterion:** V4 captured; the offender list is a written artifact naming each test
and its proposed disposition.

**Parallelism:** none.

---

- [ ] **T-043-25 — FR18b: execute the curation under `qa-engineer` verdicts**

**Owner role:** software-engineer (executing `qa-engineer` verdicts) · **Commit:**
`test(T-043-25): curate the suite under the stewardship doctrine`

**Preconditions:** T-043-24 `[x]`.

**Write set:** the tests named in T-043-24's offender list, `tests/scripts/check_skill_orphans.py`
(wired or deleted), + any production seam a rework requires.

**Description:** Every LARGE test is demoted with a named replacement, deleted with a
recorded "behaviour removed" supersession, or kept with a written justification and a
declared owner. **No deletion without a `qa-engineer` verdict carrying evidence.** Rework
the tautological and implementation-coupled families; adopt quarantine where it belongs;
give every env-gated skip a plan ref or delete it.

**Done criterion:** A18.2, A18.4 hold; the suite is green; no coverage lost silently.

**Parallelism:** none.

---

- [ ] **T-043-26 — FR18c: re-measure and draft the demotion map**

**Owner role:** qa-engineer · **Commit:** `test(T-043-26): re-measure the census and draft the demotion map`

**Preconditions:** T-043-25 `[x]`. **Write set:** the **V5** capture + the demotion map draft.

**Description:** Re-run T-043-24's exact commands and selectors; record the before/after
delta and the per-test disposition map for CLOSURE's `## Test dispositions`.

**Done criterion:** A18.3, A18.5 hold.

**Parallelism:** none.

---

- [ ] **T-043-27 — FR19: refuse a test with no declared intent**

**Owner role:** software-engineer (under a `qa-engineer` shape verdict) · **Commit:**
`feat(T-043-27): enforce the test intent declaration mechanically`

**Preconditions:** T-043-26 `[x]` — the check is unsatisfiable before the curation (D-3).

**Write set:** the check + its wiring, its tests, the doctrine statement's shape note.

**Description:** The check must accept the declaration shape the repo actually uses
(directory placement + module/section `Intent:` headers) or change that shape deliberately.

**Done criterion:** A19.1–A19.3 hold; **green at HEAD** the moment it lands.

**Parallelism:** none.

---

- [ ] **T-043-28 — FR20: select, pin and wire the mutation tool**

**Owner role:** qa-engineer (selection verdict) + software-engineer (wiring) · **Commit:**
`feat(T-043-28): wire the pinned mutation-testing tool at the declared cadence`

**Preconditions:** T-043-27 `[x]`; T-043-03 `[x]` (the pin rule).

**Write set:** `pyproject.toml` (pinned dev dependency + config), the invocation, the **V11** capture.

**Description:** Choose the tool with a written verdict, pin it exactly per FR1, and wire it
once per release **off the push path** with a bounded wall clock. Capture the first baseline
score as evidence — never as a gate.

**Done criterion:** A20.1–A20.4 hold; push-path selectors unchanged.

**Parallelism:** none.

---

- [ ] **T-043-29 — FR21a: measure the complexity maxima and pin the ceilings at them**

**Owner role:** software-engineer · **Commit:** `feat(T-043-29): enable C90/PLR1702 ratcheted at the measured maxima`

**Preconditions:** T-043-28 `[x]`.

**Write set:** `pyproject.toml` (`select` + `[tool.ruff.lint.mccabe]`), the **V6** capture.

**Description:** **One task, two steps, no gap:** run ruff with `C90`/`PLR1702` at a
permissive ceiling and record the observed maxima (V6); set the ceilings **at** those maxima
in the same task. Never an aspirational number (R8). Document that the ceilings ratchet
**only downward** and that any decrease is justified in CLOSURE.

**Done criterion:** A21.1–A21.3 hold; `ruff check` green at HEAD by construction.

**Parallelism:** none.

---

- [ ] **T-043-30 — FR21b: make `## Size accounting` a required CLOSURE section**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-30): require a Size accounting table in release closure`

**Preconditions:** T-043-29 `[x]`. **Write set:** `public/skills/dd-release-closure/SKILL.md` + projection.

**Description:** The CLOSURE template gains a mandatory `## Size accounting` table:
production LOC added/deleted/net, the three largest additions and deletions by file, max
complexity before/after, and the nesting-violation count.

**Done criterion:** A21.4 holds; T-043-52 fills it (A21.5).

**Parallelism:** none.

---

- [ ] **T-043-31 — `alpha-3` close: `qa-engineer` review**

**Owner role:** qa-engineer · **Commit:** `test(T-043-31): alpha-3 qa review`

**Preconditions:** T-043-24 … T-043-30 all `[x]`. **Write set:** the QA artifact + handoff.

**Done criterion:** every `alpha-3` acceptance id verified or explicitly named unverified;
PLAN §5 `alpha-3` exit criteria met.

**Parallelism:** none.

---

## `alpha-4` — WS-C, the Codex fidelity boundary

- [ ] **T-043-32 — FR22a: scope the six surviving intents and re-measure the byte baseline**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-32): scope the Codex fidelity work against the current tree`

**Preconditions:** T-043-31 `[x]`. **Write set:** the scoping note + the **V7** capture.

**Description:** Re-verify each surviving intent against HEAD and give it an acceptance id.
Intent 6 and the 12-persona sub-claim are **struck at pick** (SPEC FR22) — record their
anchors so the strike is auditable. Re-measure the nine TOMLs' bytes (the 126,155 B figure
is from 2026-08-15 and is not quoted).

**Done criterion:** every surviving intent has an id and a verified anchor; V7 captured.

**Parallelism:** none.

---

- [ ] **T-043-33 — FR22b: compact the personas and load the law once**

**Owner role:** ai-engineer · **Commit:** `refactor(T-043-33): compact Codex personas and load the canonical law once`

**Preconditions:** T-043-32 `[x]`.

**Write set:** `infrastructure/runtime_transforms/codex_assets.py` (renderer),
`public/entities/registry.json` if the persona bodies require it, + the Codex projection.

**Description:** Personas keep role identity, role-specific decisions, authority and
write/refusal boundaries; shared law and cross-role repetition are removed. Prove the law
loads exactly once for the parent session **and** a delegated custom agent, with
executed-path evidence.

**Done criterion:** A22.1, A22.2 hold against V7's re-measured baseline.

**Parallelism:** none.

---

- [ ] **T-043-34 — FR22c: truthful trust boundary and live certification**

**Owner role:** software-engineer · **Commit:** `fix(T-043-34): version-qualify the Codex trust boundary and certify live`

**Preconditions:** T-043-33 `[x]`.

**Write set:** `infrastructure/codex_doctor.py` (`codex_trust_boundary_info`,
`check_codex_rule_corpus_reachable`), `features/certification/service.py`, tests.

**Description:** Replace the stale headless-no-hooks claim with version-qualified
observations from the installed Codex; distinguish static reference integrity from
effective prompt visibility; certification probes exercise the installed Codex — static
tests may validate shape but never attest runtime behavior.

**Done criterion:** A22.3, A22.4 hold.

**Parallelism:** none.

---

- [ ] **T-043-35 — FR22d: behavioral `ENT-DERIVE-1` and the phantom skill prefix (#37)**

**Owner role:** software-engineer · **Commit:** `fix(T-043-35): prove derivation behaviorally and bind the skill-ref prefixes to the inventory`

**Preconditions:** T-043-34 `[x]`.

**Write set:** `infrastructure/codex_doctor.py` (`check_entities_derivation`),
`infrastructure/runtime_transforms/codex_assets.py` (`_CODEX_SKILL_REF_PREFIXES`), mutation fixtures, tests.

**Description:** Extend `ENT-DERIVE-1` from name bijection to behavioral fidelity with
mutation fixtures proving each drift class blocks. Remove the phantom `memory-ctx` prefix
(or document it as a runtime-asset exception) and derive the expectation from the real
`public/skills/` inventory in a test.

**Done criterion:** A22.5, A22.6 hold.

**Parallelism:** none.

---

- [ ] **T-043-36 — FR22e: reconcile the Codex documentation and prove isolation**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-36): reconcile the Codex skill and docs with live behaviour`

**Preconditions:** T-043-35 `[x]`.

**Write set:** `public/skills/ai-harness-codex/SKILL.md`, the Codex academy/doc surfaces,
+ projections; the **V8** capture.

**Description:** Remove the `public/rules/*.md` taxonomy documented against a directory that
does not exist; reconcile the skill and academy with live hook behaviour, the nine-persona
registry and the proven delegation topology. Then capture **V8**: a byte-diff proving **no**
non-Codex projection changed.

**Done criterion:** A22.7, A22.8 hold.

**Parallelism:** none.

---

- [ ] **T-043-37 — `alpha-4` close: `qa-engineer` review**

**Owner role:** qa-engineer · **Commit:** `test(T-043-37): alpha-4 qa review`

**Preconditions:** T-043-32 … T-043-36 all `[x]`. **Write set:** the QA artifact + handoff.

**Done criterion:** certification evidence and `entities-derivation` `[ok]` recorded; PLAN §5
`alpha-4` exit criteria met.

**Parallelism:** none.

---

## `alpha-5` — WS-G, event-driven artifact GC (R10: before the consumer round)

- [ ] **T-043-38 — FR23: ack-on-consume for coordination handoffs**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-38): consumer skills delete the coordination handoff they read`

**Preconditions:** T-043-37 `[x]`. **Write set:** the handoff-consumer discipline on the
skills surface (one location) + projections.

**Description:** State the rule **once**: a consumer skill deletes the coordination handoff
it consumed; a handoff carrying `artifact.path` is exempt and follows its report's
retention. No per-skill restatement.

**Done criterion:** A23.1–A23.3 hold.

**Parallelism:** none.

---

- [ ] **T-043-39 — FR24: a consumed push verdict dies with the push**

**Owner role:** software-engineer · **Commit:** `feat(T-043-39): delete the security verdict consumed by a successful push`

**Preconditions:** T-043-38 `[x]`. **Write set:** `features/chokepoints/service.py` + tests.

**Description:** After a successful push, delete the APPROVED verdict handoff(s) covering the
pushed delta. A verdict for an unpushed delta is never touched; deletion is best-effort and
never changes a push verdict.

**Done criterion:** A24.1–A24.3 hold.

**Parallelism:** none.

---

- [ ] **T-043-40 — FR25: release closure sweeps its own artifacts**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-40): add the artifact GC sweep to release closure`

**Preconditions:** T-043-39 `[x]`. **Write set:** `public/skills/dd-release-closure/SKILL.md` + projection.

**Description:** The closure template gains a sweep step with an explicit keep/delete rule.
Nothing referenced by a surviving CLOSURE evidence pointer may be deleted. Lands in the same
skill T-043-30 edited — re-read it before writing.

**Done criterion:** A25.1, A25.3 hold; T-043-52 executes it (A25.2).

**Parallelism:** none.

---

- [ ] **T-043-41 — FR26: the reconciler reaps what it already walks**

**Owner role:** software-engineer · **Commit:** `feat(T-043-41): reap stale session, marker and zombie run records`

**Preconditions:** T-043-40 `[x]`. **Write set:** `hooks/sdd_post_gate.py` + tests; the **V10** capture.

**Description:** Delete session/presence records stale beyond N×TTL together with their tmp
markers and empty context dirs; reap zombie lifecycle/state run records. Best-effort and
fail-open, matching the reconciler it extends. A live session's records are never touched.

**Done criterion:** A26.1–A26.3 hold; V10 captured before/after.

**Parallelism:** none.

---

- [ ] **T-043-42 — FR27: writers rotate their own logs**

**Owner role:** software-engineer · **Commit:** `feat(T-043-42): rotate .dadaia log files at write time`

**Preconditions:** T-043-41 `[x]`. **Write set:** the `.dadaia/logs/*.jsonl` appenders
(`hooks/pre_gate.py` and peers) + tests.

**Description:** Each writer caps its log at ~1 MB and keeps current+1. Rotation happens at
write time by the owner of the file, never by an external cron; telemetry stays fail-open.

**Done criterion:** A27.1–A27.3 hold, including the concurrent-writer fixture.

**Parallelism:** none.

---

- [ ] **T-043-43 — FR28: the cache must not be born**

**Owner role:** software-engineer · **Commit:** `feat(T-043-43): block cache-enabling mypy/pytest/ruff invocations`

**Preconditions:** T-043-42 `[x]`. **Write set:** `hooks/venv_guard.py` + tests.

**Description:** Block `mypy`/`pytest`/`ruff` Bash invocations that would run with caching
enabled; the block message carries the corrected command, matching the existing venv-guard
contract. Token-matched on fixed leading tokens — **no shell parsing**.

**Done criterion:** A28.1–A28.3 hold; no false block on an unrelated command.

**Parallelism:** none.

---

- [ ] **T-043-44 — FR29: `dadaia tmp gc`, the orphan backstop**

**Owner role:** software-engineer · **Commit:** `feat(T-043-44): add the dadaia tmp gc orphan backstop`

**Preconditions:** T-043-43 `[x]`. **Write set:** the new CLI verb + its wiring + tests.

**Description:** The **only** calendar-based deletion in the release: dated scratch older
than 3 days, any `*cache*` directory under `.dadaia`, orphaned session markers. Idempotent,
`SessionStart`-safe, with a dry-run mode.

**Done criterion:** A29.1–A29.4 hold.

**Parallelism:** none.

---

- [ ] **T-043-45 — `alpha-5` close: `qa-engineer` review**

**Owner role:** qa-engineer · **Commit:** `test(T-043-45): alpha-5 qa review`

**Preconditions:** T-043-38 … T-043-44 all `[x]`. **Write set:** the QA artifact + handoff.

**Description:** Verify every `alpha-5` acceptance id and the fail-open posture of each
capability that rides a hook. The artifact names the GC surface `alpha-6`'s consumer round
must exercise (feeds A30.6).

**Done criterion:** PLAN §5 `alpha-5` exit criteria met; V10 recorded.

**Parallelism:** none.

---

## `alpha-6` — WS-F, consumer round and published lineage (R10: last)

- [ ] **T-043-46 — FR30a: run the consumer round on a throwaway real workspace**

**Owner role:** consumer-side validation agent / qa-engineer (dispatched by `project-manager`) ·
**Commit:** `test(T-043-46): consumer-side validation round`

**Preconditions:** T-043-45 `[x]` — the round runs on the **fully assembled** surface,
GC included (R10).

**Write set:** the round artifact + handoff; the throwaway workspace lives under
`.dadaia/tmp/<agent>/<YYYYMMDD>/` and is never committed.

**Description:** Create a real workspace with `dadaia init` under the workspace tmp (R7) and
validate through supported interfaces only, against the three inherited criteria (A30.1–A30.3).
Record **every** limit of the environment honestly (A30.4) — an unexercised criterion is
never reported as passed — and name which `alpha-5` GC capabilities the journey exercised
(A30.6).

**Done criterion:** A30.1–A30.4 and A30.6 hold or are explicitly recorded as unexercised
with a reason.

**Parallelism:** none.

---

- [ ] **T-043-47 — FR30b: spend (or explicitly not spend) the remediation cycle**

**Owner role:** software-engineer / ai-engineer as the finding requires · **Commit:**
`fix(T-043-47): remediate the consumer round's findings`

**Preconditions:** T-043-46 `[x]`.

**Write set:** determined by the findings; declared before the work starts.

**Description:** One budgeted remediation cycle **inside** this segment. A finding too large
to absorb is escalated to the operator **at the moment of discovery** for a ratified
exception — never carried silently to the closure.

**Done criterion:** A30.5 holds; if unused, the task records "no finding required remediation".

**Parallelism:** none.

---

- [ ] **T-043-48 — FR31: backfill the CHANGELOG in the minimal honest form**

**Owner role:** software-engineer · **Commit:** `docs(T-043-48): backfill the published CHANGELOG lineage`

**Preconditions:** T-043-47 `[x]`. **Write set:** `CHANGELOG.md`.

**Description:** Per R5: a compact retroactive section for each of the ten published versions
lacking one (`0.1.2`, `0.1.5`, `0.1.6`, `0.2.0`–`0.2.3`, `0.3.0`, `0.4.0`, `0.4.1`),
**derived from git history with no invention** — a version whose history yields nothing
substantive gets one factual line. Annotate `[0.1.24]`, `[0.1.7]` and `[0.1.3]` as
unpublished-internal. **Delete and rename nothing.**

**Done criterion:** A31.1–A31.4 hold; each line is checkable against a commit range.

**Parallelism:** none.

---

- [ ] **T-043-49 — `alpha-6` close: `qa-engineer` review**

**Owner role:** qa-engineer · **Commit:** `test(T-043-49): alpha-6 qa review`

**Preconditions:** T-043-46 … T-043-48 all `[x]`. **Write set:** the QA artifact + handoff.

**Done criterion:** PLAN §5 `alpha-6` exit criteria met; the recorded environment limits and
the GC coverage statement are carried forward for CLOSURE.

**Parallelism:** none.

---

## `rc-1` — review → memory → closure → archive → ship

- [ ] **T-043-50 — Six-axis code review on a thawed tree**

**Owner role:** code-reviewer · **Commit:** `docs(T-043-50): pre-PR six-axis review`

**Preconditions:** T-043-49 `[x]`. **Write set:** the review artifact + handoff.

**Description:** Review the whole release delta **before** the archive move (D8/FR5), so any
finding lands on a thawed tree and is fixed in place. An actionable finding returns to its
owning lane and is fixed here — it never becomes intake demand (residual budget).

**Done criterion:** APPROVED `code-reviewer` artifact; A32.1–A32.4 verified.

**Parallelism:** none.

---

- [ ] **T-043-51 — [phase] Memory window: one authoring pass per atom**

**Owner role:** product-engineer (dispatcher commits the reservation flip first) · **Commit:**
`docs(T-043-51): v0.4.3 memory window`

**Preconditions:** T-043-50 `[x]`; `ACTIVE.md` phase set to `CLOSURE` **before** any memory
write (the gate allows `specs/memory/**` only in `DEFINITION`/`CLOSURE`).

**Write set:** exactly the atoms declared in SPEC §5, plus `specs/memory/.heading-allowlist`
(V3's twelve headings + the new governance heading) and the regenerated
`specs/memory/product/catalog.json`.

**Description:** One pass per atom, never in pieces — the 5k-token gate atom is targeted by
four FRs and is written once. Includes **PE-2**: drop `tech-stack.md`'s false
"currently `0.5.0`" parenthetical rather than restating a number that re-stales every
release. Memory describes the product **as it is now** — no changelog, no history.

**Done criterion:** SPEC §5 satisfied atom by atom; `dadaia specs doctor` reports **0 errors**
and **0 `LINT-1` heading warnings** (A13.4); the catalog regenerated.

**Parallelism:** none.

---

- [ ] **T-043-52 — [phase] CLOSURE, disposition sweep, archive**

**Owner role:** product-engineer (dispatcher commits the reservation flip first) · **Commit:**
`docs(T-043-52): v0.4.3 closure and archive`

**Preconditions:** T-043-51 `[x]`.

**Write set:** `specs/releases/v0.4.3/CLOSURE.md`, `specs/backlog/BACKLOG.md` (the 24
`LEDGER` lines), `specs/releases/ACTIVE.md`, then the `git mv` to `specs/_archive/releases/`.

**Description:** Write CLOSURE per `dd-release-closure`, carrying: the disposition sweep (24
`DELIVERED`/`SUPERSEDED · v0.4.3` lines — the rejection line was written at definition —
plus the Arm-B rider bug as `Closed`); the `## Test dispositions` demotion map; the mandatory
`## Size accounting` table (V12); the FR25 artifact sweep; `## Record-only observations` and
`## Intake candidates` per the FR6 calibration — **the second must be empty** (A32.5); the R9
git-identity restatement; and the PE-1 record. Then archive:
`git mv specs/releases/v0.4.3 specs/_archive/releases/v0.4.3` and point `ACTIVE.md` at
`release: none`.

**Done criterion:** `## ACTIVE` **empty** with 25 total new `LEDGER` lines; zero actionable
intake candidates; release archived; `specs doctor` green.

**Parallelism:** none.

---

- [ ] **T-043-53 — [git] Ship: version bump, merge, security review, push, PR to `main`**

**Owner role:** dispatcher + software-engineer + security-reviewer · **Commit:**
`chore(T-043-53): release v0.4.3`

**Preconditions:** T-043-52 `[x]`.

**Write set:** `pyproject.toml` (`0.4.2` → `0.4.3`), `CHANGELOG.md` (`[0.4.3]` section above
FR31's backfilled lineage), then git refs.

**Description:** One axis: the release id **is** the package version. Then per
`dadaia-gitflow` ship: merge `feature/0.4.3` into local `develop`; diff-based
`security-reviewer` review of `origin/develop..develop`; push `develop`; open the PR
`develop` → `main`; watch CI to green; after the merge, run the reconciliation merge the
newly-documented mechanic (FR6) describes. Capture **V13** — the `SPEC-DOC-031` count
**after** the archive move, never before.

**Done criterion:** PR merged to `main`; CI green; V13 captured; worktree clean.

**Parallelism:** none — last task.
