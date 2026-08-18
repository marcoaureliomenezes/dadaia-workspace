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
| T-043-03 | #35 / FR1 | A1.1–A1.4 | skill diff, zero-hit grep — done `8fa6fcca` |
| T-043-04 | #32 / FR2 | A2.1–A2.4 | frontmatter diff, check green at HEAD (`lint-skill-collisions.py`, `--self-test` PASS) — done `584304ee` |
| T-043-05 | #33 / FR3 | A3.1–A3.2 | skill diff, grep (one-directional pointer confirmed) — done `f42f69b2` |
| T-043-06 | #34 / FR4 | A4.1–A4.3 | law-source diff + projection byte-identity (T-043-11 cycle) — done `2cbd74a2` |
| T-043-07 | #36 / FR5 | A5.1–A5.3 | frontmatter diff + derivation script (`lint-dadaia-cli-reachability.py`, `--self-test` PASS) — done `03d9b8b9` |
| T-043-08 | #15 / FR6 | A6.1–A6.2 | skill diff, single-writer grep — done `8556c8e2` |
| T-043-09 | idea / FR7 | A7.1–A7.2 | skill diff, T-043-24 citation confirmed at :591 — done `3a562a93` |
| T-043-10 | idea / FR8 | A8.1–A8.3 | RED-then-GREEN output (software-engineer, out of ai-engineer scope) |
| T-043-11 | — | A32.2 | V9 capture (183 `[ok]`, 0 `[error]`, 0 `[warn]`, incl. `[ok] public-privacy`), byte-verified skills/agents/scripts/law projections — done `e9b3434a`; re-projected after `ed94f5b0`'s post-cycle ruff-format (2 `[drift]` → V9 re-captured 183 `[ok]`/0/0/0, both lint scripts byte-verified + `--self-test` PASS) |
| T-043-12 | all `alpha-1` | A1–A8 ids | `qa-engineer` artifact |
| T-043-13 | #9 / FR9 | A9.1–A9.3 | RED-then-GREEN output |
| T-043-14 | #18 / FR10 | A10.1–A10.3 | RED-then-GREEN output |
| T-043-15 | #21 / FR11 | A11.1–A11.7 | reconciliation fixture output + header/body boundary fixture |
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
| T-043-38 | GC / FR23 | A23.1–A23.3, **AG.1** | skills diff + fixtures + lane-guard fixture |
| T-043-39 | GC / FR24 | A24.1–A24.4, **AG.1** | push fixtures + audit-ledger line + lane-guard fixture |
| T-043-40 | GC / FR25 | A25.1–A25.3, **AG.1** | skill template diff |
| T-043-41 | GC / FR26 | A26.1–A26.3, **AG.1** | V10 capture + lane-guard fixture |
| T-043-42 | GC / FR27 | A27.1–A27.3 | rotation fixtures |
| T-043-43 | GC / FR28 | A28.1–A28.3 | block-message fixtures |
| T-043-44 | GC / FR29 | A29.1–A29.4, **AG.1** | dry-run + idempotency output + lane-guard fixture |
| T-043-45 | all `alpha-5` | A23–A29 ids, **AG.1** | `qa-engineer` artifact |
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

- [x] **T-043-01 — [git] Definition commit** (commit `c4175ff1`)

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

- [x] **T-043-02 — [git] Milestone (a): merge, security review, push** (merge `cab4e6c1`; gate self-refusal remediated in-range — carve-out v6 rider `07c78366` + amendments `df3b1a93`; APPROVED handoff `2026-08-17T145516Z…rereview`; pushed, gate exit 0)

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

- [x] **T-043-03 — FR1: pin every prescribed third-party install**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-03): pin the audit and quality tool installs`

**Preconditions:** T-043-02 `[x]`. **Lands first in the release** (D-2): FR20 inherits this rule.

**Write set:** `dadaia_workspace/public/skills/dd-audit-project/SKILL.md` + projections.

**Description:** Replace the five unpinned installs (`:107`, `:118`, `:121`, `:132`, `:142`)
with exact version or hash pins, and state the pinning rule once, worded to cover audit
**and** quality tooling. The memory doctrine line (A1.3) rides the `rc-1` memory window.

**Done criterion:** A1.1, A1.2, A1.4 hold; `public doctor` green.

**Parallelism:** none.

---

- [x] **T-043-04 — FR2: resolve the two duplicate `dd-` activation claims (R2 scope)**

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

- [x] **T-043-05 — FR3: break the release-definition pointer loop**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-05): drop the dd-release-definition back-pointer`

**Preconditions:** T-043-04 `[x]`. **Write set:** `public/skills/dd-release-definition/SKILL.md` + projection.

**Description:** Drop the back-pointer at `:106-107`, leaving the `DADAIA.md` §5 reference;
`project-orchestration` keeps its dispatch note naming what it owns.

**Done criterion:** A3.1, A3.2 hold.

**Parallelism:** none.

---

- [x] **T-043-06 — FR4: one always-on sentence naming the forbidden bug-event field content**

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

- [x] **T-043-07 — FR5: make `dadaia-cli`'s grant and description agree**

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

- [x] **T-043-08 — FR6: record the reconciliation-merge mechanic**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-08): record the reconciliation-merge mechanic in dadaia-gitflow`

**Preconditions:** T-043-07 `[x]`. **Write set:** `public/skills/dadaia-gitflow/SKILL.md` + projection.

**Description:** One statement: every squash-merge to `main` is followed by a reconciliation
merge of `main` into `develop`, resolving resurrected loose copies in favour of `develop`'s
archives. v0.4.2's ship (`84a66d13`) is the worked example.

**Done criterion:** A6.1, A6.2 hold — the statement exists exactly once across `public/`.

**Parallelism:** none.

---

- [x] **T-043-09 — FR7: note the stewardship vocabulary's homonyms**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-09): note the scaffold/sentinel/quarantine homonyms`

**Preconditions:** T-043-08 `[x]`. **Write set:** `public/skills/dadaia-test-stewardship/SKILL.md` + projection.

**Description:** A short note naming the three colliding terms and their unrelated homes, so
T-043-24's greps do not chase homonyms.

**Done criterion:** A7.1 holds; T-043-24 cites it (A7.2).

**Parallelism:** none.

---

- [x] **T-043-10 — FR8: warn on an installed `tests/AGENTS.md` with unfilled placeholders**

**Owner role:** software-engineer · **Commit:** `feat(T-043-10): report placeholder tokens in an installed tests/AGENTS.md`

**Preconditions:** T-043-09 `[x]`.

**Write set:** `dadaia_workspace/features/specs/doctor.py` (the `MEM-PLACEHOLDER-1`
validator family), its tests.

**Description:** Reuse the existing validator shape. The check runs against the **installed
consumer** file only — the canonical template legitimately carries placeholders. RED first.

**Done criterion:** A8.1–A8.3 hold; `specs doctor` green on this workspace.

**Parallelism:** none.

---

- [x] **T-043-11 — [git] `alpha-1` projection cycle and evidence**

**Owner role:** ai-engineer · **Commit:** `chore(T-043-11): project the alpha-1 public surface`

**Preconditions:** T-043-03 … T-043-10 all `[x]`.

**Write set:** the projected trees (`.claude/`, `.codex/`, `.kimi-code/`, `.agents/`) and
the staged canonical assets.

**Description:** One cycle: `dadaia public stage` → `dadaia public install --target all` →
`dadaia public doctor`. Capture **V9** with all three `[ok]` lines.

**Done criterion:** A32.2 holds for this segment; staged/projected hashes agree.

**Parallelism:** none.

---

- [x] **T-043-12 — `alpha-1` close: `qa-engineer` review**

**Owner role:** qa-engineer · **Commit:** `test(T-043-12): alpha-1 qa review`

**Preconditions:** T-043-11 `[x]`. **Write set:** the QA artifact + handoff.

**Description:** Verify every `alpha-1` acceptance id; name any id that could not be
verified rather than reporting it passed. Segment gate only — no closure, no ship.

**Done criterion:** APPROVED `qa-engineer` artifact committed to the branch; PLAN §5
`alpha-1` exit criteria met.

**Parallelism:** none.

---

## `alpha-2` — WS-B + WS-E, gate hardening and governance primitives

- [x] **T-043-13 — FR9: interpreter-probe hardening (CWE-426 + timeout/stdin)**

**Owner role:** software-engineer · **Commit:** `fix(T-043-13): reject relative interpreter candidates and bound the probe`

**Preconditions:** T-043-12 `[x]`. **Write set:** `infrastructure/python_env.py` + its tests.

**Description:** RED first with a fixture returning a bare name and one that hangs. Filter
on `os.path.isabs()` for both `which` results and the `pyvenv.cfg` value; pass a bounded
`timeout=` and `stdin=subprocess.DEVNULL`.

**Done criterion:** A9.1–A9.3 hold.

**Parallelism:** **sanctioned pair with T-043-14** — disjoint write sets (D-7).

---

- [x] **T-043-14 — FR10: `commit_paths` index-scope hardening**

**Owner role:** software-engineer · **Commit:** `fix(T-043-14): check git add and path-scope the commit`

**Preconditions:** T-043-12 `[x]`. **Write set:** `infrastructure/git_subprocess.py`,
`core/protocols/git_client.py` (docstring/defence note), + tests.

**Description:** RED first: stage unrelated content, then prove it lands in the commit.
Raise `GitSyncError` on a non-zero `git add`; path-scope the commit; apply or explicitly
decline the pathspec-magic defence with a recorded reason.

**Done criterion:** A10.1–A10.3 hold.

**Parallelism:** **sanctioned pair with T-043-13**.

---

- [x] **T-043-15 — FR11: the push scan reads commit objects**

**Owner role:** software-engineer (acceptance co-signed by `security-reviewer`) · **Commit:**
`feat(T-043-15): scan the pushed range's commit objects`

**Preconditions:** T-043-13 `[x]`, T-043-14 `[x]`.

**Write set:** `container.py` (the reader seam), `features/chokepoints/service.py`,
`core/protocols/git_object_reader.py`, `infrastructure/git_objects.py`, + fixtures.

**Description:** Extend the reader to yield the range's commit objects and annotated tag
bodies through the same batched conversation and typed-error contract; feed them through
the same three term layers with the same masked, satisfiable refusal (healing action:
reword/amend). The v0.4.2 reconciliation shape — two commits, **zero blobs** — is an
acceptance fixture. **The boundary is the commit object's header/body split**: scan the
message body and an annotated tag's body only; never the `author`/`committer` headers (a
header hit is unamnestiable and would be a permanent self-refusal). RED first.

**Done criterion:** A11.1–A11.4 hold, **plus A11.6 (the header/body boundary: body and tag
body scanned, `author`/`committer` headers out of scope by design) and A11.7 (path-less
objects carry no prior text, so a body hit is never amnestied — fail-closed)**; A11.5's
memory edit is deferred to T-043-51.

**Parallelism:** none.

---

- [x] **T-043-16 — FR12: the privacy baseline stops growing literal by literal**

**Owner role:** software-engineer (acceptance co-signed by `security-reviewer`) · **Commit:**
`fix(T-043-16): baseline rationale check, structural dotted-chain rule, trailer carve-out`

**Preconditions:** T-043-15 `[x]`.

**Write set:** `infrastructure/privacy_check.py`, `infrastructure/data/privacy_baseline.json`
(version bump + `_header.excludes`), the rationale check + its doctor wiring, fixtures.

**Description:** Three parts plus two folded escapes: the rationale check; the cadence and
single-line constraint (recorded as memory truth at T-043-51); the structural rule for the
`internal-hostname` dotted-chain class; the Windows trailing-period escape (CR-6). The
`noreply@anthropic.com` **local-part** carve-out (A12.2) **already shipped as the Arm-B
rider** on bug `privacy-baseline-noreply-local-part-not-carved-out` (SPEC §6 D-10) — this
task **verifies** it at HEAD, with its counter-fixture proving a genuine address at the same
domain still fires, and never re-implements it.

**Done criterion:** A12.1, A12.3–A12.6 hold and A12.2 is **verified** as delivered by the
rider; `public doctor` `[ok] public-privacy`; sentinel green.

**Parallelism:** none.

---

- [x] **T-043-17 — FR13: decide the MEMORY path class and enumerate the standing lint warnings**

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

- [x] **T-043-18 — FR14: the `picked` bug-ledger event**

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

- [x] **T-043-19 — FR15: clarify the dangling deferral pointer**

**Owner role:** software-engineer · **Commit:** `fix(T-043-19): clarify the panel-runtime-reliability deferral pointer`

**Preconditions:** T-043-18 `[x]`. **Write set:** `specs/bugs/bugs.jsonl` via `dadaia bugs append` only.

**Description:** Append **one** clarifying event to
`panel-telemetry-sqlite-corrupts-under-concurrent-access` recording that the 2026-07-01
deferral target was already consumed by v0.1.52 at deferral time, and naming the corrected
disposition **with an existing token** (R6 — no new token). No existing line is modified.

**Done criterion:** A15.1–A15.3 hold; the 2026-07-01 line is byte-unchanged.

**Parallelism:** none.

---

- [x] **T-043-20 — FR16: one logic, one source for projected scripts (package half — software-engineer; public/ half pending ai-engineer)**

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

- [x] **T-043-21 — FR17: refuse a symlinked repo-`AGENTS.md` destination**

**Owner role:** software-engineer · **Commit:** `fix(T-043-21): harden the repo-AGENTS.md destination against symlinks`

**Preconditions:** T-043-20 `[x]`. **Write set:** `infrastructure/public_assets.py` + fixtures.

**Description:** Mirror the four refusal sites of the hardened sibling seam onto the
repo-`AGENTS.md` destination write, with a fixture per site. RED first.

**Done criterion:** A17.1, A17.2 hold — the memory atom's existing claim becomes true.

**Parallelism:** none.

---

- [x] **T-043-22 — [Arm-B rider] The segment router errors instead of going silent**

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

- [x] **T-043-23 — `alpha-2` close: `qa-engineer` review + security review of the gate delta**

**Owner role:** qa-engineer + security-reviewer · **Commit:** `test(T-043-23): alpha-2 qa review`

**Preconditions:** T-043-13 … T-043-22 all `[x]`. **Write set:** the QA artifact + handoffs.

**Description:** Verify every `alpha-2` acceptance id, including AB.1–AB.5;
`security-reviewer` covers the gate and baseline delta specifically (FR11, FR12).

**Done criterion:** APPROVED artifacts committed; PLAN §5 `alpha-2` exit criteria met.

**Parallelism:** none.

---

## `alpha-3` — WS-A, suite, measurements, complexity governance

- [x] **T-043-24 — FR18a: measure the census and derive the offender list**

**Owner role:** qa-engineer · **Commit:** `test(T-043-24): capture the v0.4.3 LARGE census baseline`

**Preconditions:** T-043-23 `[x]`. **Write set:** the **V4** capture under `.dadaia/tmp/`; no source edits.

**Description:** Measure the live LARGE census (e2e-tier pytest journeys and Playwright
specs) and re-derive the offender list from the tree — the entry's own numbers are **void**
(A18.1). Cite T-043-09's homonym note before grepping the stewardship vocabulary.

**Done criterion:** V4 captured; the offender list is a written artifact naming each test
and its proposed disposition.

**Evidence:** V4 (56 pytest e2e + 46 Playwright = 102 broad LARGE, cap 30) —
`v0.4.3-T-043-24-v4-large-census.md`; offender list (100% of 102 dispositioned: 2 DEMOTE,
0 DELETE, 100 KEEP [1 already compliant, 99 need Intent/Owner backfill], 1 tooling WIRE
verdict for `check_skill_orphans.py`) — `v0.4.3-T-043-24-offender-list.md`. Both under
`.dadaia/tmp/qa-engineer/20260817/`.

**Parallelism:** none.

---

- [x] **T-043-25 — FR18b: execute the curation under `qa-engineer` verdicts**

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

**Evidence (per-verdict commits, `feature/0.4.3`):**
- `24d0ba26` chore(tasks): start T-043-25
- `cb1986ce` test(T-043-25): demote the stderr-drain pair from e2e to integration (Verdict 1) — 2 tests moved verbatim to `tests/integration/features/test_panel_stderr_drain.py`; helper shared via `tests/helpers/subprocess_diag.py`
- `704a67cb` chore(bugs): register skill-orphans-unwired-agent-frontmatter — 3 pre-existing orphaned skills found while wiring; fix is ai-engineer's territory (agent frontmatter)
- `af51815b` test(T-043-25): wire check_skill_orphans.py into the gating suite (Verdict 3) — new real-repo case in `tests/integration/scripts/test_check_skill_orphans.py`, bug-cited exemption for the 3 known orphans
- `193ca6c4` test(T-043-25): backfill the plan-ref skip and re-aim the dangling pointer (Verdicts 2, 2b) — `spec-context-operation-journey.spec.ts` skip string + `test_handoff_pipeline.py` docstring re-aimed off the archived `test-suite-remediation-stewardship` slug
- `e5a205c1` test(T-043-25): backfill Intent/Owner across the remaining pytest e2e tier (Verdict 4) — 12 files
- `db7f7403` test(T-043-25): backfill Intent/Owner across the Playwright LARGE tier (Verdict 4) — 10 files
- `e23a28e5` chore(bugs): register repo-self-scan-hits-alpha2-qa-historical-literal — pre-existing, unrelated `test_repo_self_scan.py` failure found during the full-gate run; confirmed neither implicated file is touched by this task's diff

**A18.2/A18.4 held:** all 102 census-dispositioned LARGE tests carry an explicit
disposition (2 DEMOTE, 100 KEEP incl. the 1 already-compliant); every KEEP declares
Intent+Owner; the WIRE verdict is executed with a bug-tracked exemption, never a
silent hole; zero deletions performed (none authorized by the offender list). e2e-tier
count after demotion: 54 (was 56, `pytest -m e2e --collect-only`). Full suite:
`pytest -q -p no:cacheprovider -m 'not quarantine' -n auto` → 2425 passed, 3 skipped,
1 pre-existing failure unrelated to this task (registered as
`repo-self-scan-hits-alpha2-qa-historical-literal`, confirmed via empty diff on both
implicated files) — 0 failures/regressions attributable to this task's changes.

---

- [x] **T-043-26 — FR18c: re-measure and draft the demotion map**

**Owner role:** qa-engineer · **Commit:** `test(T-043-26): re-measure the census and draft the demotion map`

**Preconditions:** T-043-25 `[x]`. **Write set:** the **V5** capture + the demotion map draft.

**Description:** Re-run T-043-24's exact commands and selectors; record the before/after
delta and the per-test disposition map for CLOSURE's `## Test dispositions`.

**Done criterion:** A18.3, A18.5 hold.

**Parallelism:** none.

**Evidence:** V5 re-measurement, T-043-24's commands/selectors re-run verbatim at
`1a75ac4c` — pytest e2e-tier 54 (was 56, -2), Playwright 46 (unchanged), broad LARGE
100 (was 102, -2); id-set diff confirms the -2 delta is exactly Verdict 1's demotion,
no other change. All 6 offender-list verdicts (1, 2, 2b, 3, 4-pytest, 4-Playwright)
independently re-verified executed as verdicted, including a 14-file Intent/Owner
spot-check (exceeds the 10-file minimum) and a demoted-test tier/collection check. Full
gating suite re-run green: 2426 passed, 3 skipped, 0 failed (the 1 pre-existing failure
T-043-25 reported was resolved by a concurrent, unrelated Arm-B rider, confirmed
zero-overlap with this task's scope). A18.3 holds (numbers + delta captured, see V5 §8).
A18.5 holds for its "drafted in the segment" half (CLOSURE recording is `rc-1`/
`product-engineer` territory, out of this task's write set). Artifacts:
`v0.4.3-T-043-26-v5-census-remeasure.md`, `v0.4.3-T-043-26-demotion-map-draft.md`,
raw captures `v5-pytest-e2e-collect.txt`/`v5-pytest-e2e-dir-collect.txt` — all under
`.dadaia/tmp/qa-engineer/20260817/`.

---

- [x] **T-043-27 — FR19: refuse a test with no declared intent**

**Owner role:** software-engineer (under a `qa-engineer` shape verdict) · **Commit:**
`feat(T-043-27): enforce the test intent declaration mechanically`

**Preconditions:** T-043-26 `[x]` — the check is unsatisfiable before the curation (D-3).

**Write set:** the check + its wiring, its tests, the doctrine statement's shape note.

**Description:** The check must accept the declaration shape the repo actually uses
(directory placement + module/section `Intent:` headers) or change that shape deliberately.

**Done criterion:** A19.1–A19.3 hold; **green at HEAD** the moment it lands.

**Parallelism:** none.

**Evidence:** Accepted the qa-engineer shape verdict verbatim (V5 census: size by
directory placement, `Intent: <KIND> — <ref>` module docstring/header) — no shape
change. RED-first: `tests/integration/scripts/test_check_test_intent_declared.py`
written and run against the not-yet-existing script — 5/5 fail for the real reason
(`FileNotFoundError`, exit 2). New `tests/scripts/check_test_intent_declared.py`
(standalone checker, `check_skill_orphans.py`'s exact pattern) scans `tests/e2e/**`
(Python `test_*.py` + Playwright `*.spec.ts`, non-test support modules excluded) for a
declared `Intent:` line; exit 1 names offenders, exit 0 is silent. GREEN: 5/5 wiring
tests pass (2 fake-tree refusal cases, 1 fake-tree pass case, 1 support-module
exclusion case, 1 real-repo case). A19.1 holds: script exits 0 against the real repo
at HEAD (T-043-26's V5 census — 15/15 pytest + 11/11 Playwright e2e files already
declare `Intent:`). A19.2 holds per the 4 fake-tree cases. A19.3 holds:
`tests/AGENTS.md`'s Intent-taxonomy section now documents the mechanical enforcement,
its scope (`tests/e2e/**` only — the LARGE tier T-043-24..26 backfilled) and exclusion
list. Wired into the gating pytest run only (`tests/integration/scripts/`, same surface
as `check_skill_orphans.py`) — nothing added to the push path beyond the existing
`pytest -m 'not quarantine'` selector. Full gate green: `ruff format --check .`,
`ruff check --no-cache .`, `mypy --strict dadaia_workspace/` (266 files, no issues —
check touches no package code), full suite `pytest -p no:cacheprovider -m 'not
quarantine' -n auto` — 2431 passed (was 2426, +5 new tests), 3 skipped, 0 failed;
`dadaia doctor` — all invariants OK; `dadaia specs doctor --context dadaia-workspace` —
0 errors, 5 pre-existing warnings (unchanged, out of scope, T-043-51 territory). LOC
delta: +210 net (0 deletions) across 3 files — 49-line checker, 151-line wiring test,
10-line doctrine note. New-function complexity: trivial (`_candidate_files` ~3,
`main` ~2 branches) — `C90` is not yet selected in `pyproject.toml` (FR21 lands after
FR19/FR20 per PLAN.md §3), so no ratchet number to pin here.

---

- [x] **T-043-28 — FR20: select, pin and wire the mutation tool**

**Owner role:** qa-engineer (selection verdict) + software-engineer (wiring) · **Commit:**
`feat(T-043-28): wire the pinned mutation-testing tool at the declared cadence`

**Preconditions:** T-043-27 `[x]`; T-043-03 `[x]` (the pin rule).

**Write set:** `pyproject.toml` (pinned dev dependency + config), the invocation, the **V11** capture.

**Description:** Choose the tool with a written verdict, pin it exactly per FR1, and wire it
once per release **off the push path** with a bounded wall clock. Capture the first baseline
score as evidence — never as a gate.

**Done criterion:** A20.1–A20.4 hold; push-path selectors unchanged.

**Parallelism:** none.

**Evidence:** qa-engineer's selection verdict
(`.dadaia/tmp/qa-engineer/20260817/v0.4.3-T-043-28-mutation-tool-verdict.md`) selected
`mutmut==3.7.0`. Wired: `pyproject.toml` gained an optional, non-default
`[tool.poetry.group.mutation]` (`optional = true`) with the exact pin, plus an inert
`[tool.mutmut]` config table (real source of truth is the staged copy's generated
config); `poetry.lock` regenerated (`poetry lock`, additions only — 0 existing pins
changed, verified `git diff poetry.lock | grep -c '^-version'` = 0) and confirmed both
ways: a plain `poetry install --dry-run` never selects mutmut/textual/libcst/
setproctitle; `poetry install --dry-run --with mutation` does. `click` resolves to
8.4.1 (>= the verdict's 8.3.3 floor for PYSEC-2026-2132). New
`tests/scripts/run_mutation_baseline.sh`: stages a scoped copy under
`.dadaia/tmp/software-engineer/<date>/mutation-run/`, creates a throwaway venv, runs
mutmut, copies back only the JSON stats — never writes inside the repo tree (verified
`git status --porcelain` unchanged before/after). Two wiring-time findings, both fixed
in the script and recorded in its header: (1) `.dadaia/.venv/bin/python -m venv`
chained a nested venv onto this host's `/usr/bin/python3` (3.10, this host's default
symlink) instead of the pinned 3.12 even with `--copies` — fixed by resolving the
workspace venv's own `pyvenv.cfg` `executable =` line instead of invoking it directly;
(2) the verdict's full `core/` + `tests/unit/core/` first-baseline scope hit two
`tests/unit/core/` (flat) files that are real cross-layer architecture tests
(`test_harness_registry.py`, `test_kernel_tunables.py`) mutmut's `mutants/` sandbox
(which mirrors only `source_paths`) cannot run — narrowed to the verdict's own
already-validated `core/models/` + `tests/unit/core/models/` smoke-trial sub-slice per
the dispatch's bounded-run clause; widening back is recorded follow-up, not done here.
A20.3 grep proof: `run_mutation_baseline`/`mutmut` absent from `ci.yml`, `release.yml`,
`ci_preflight/service.py` (0 hits, guarded permanently by
`test_script_never_referenced_from_a_push_path_selector`). V11 baseline captured:
73 mutants, 66 killed, 7 survived, 0 no_tests, 90.4% score, ~9s wall clock —
`.dadaia/tmp/software-engineer/20260817/v0.4.3-T-043-28-v11-mutation-baseline.md`.
New tests: `tests/integration/scripts/test_run_mutation_baseline_wiring.py` (5 tests:
executable+syntax, exact pin, staging isolation + config content, push-path absence
guard) — no real venv built in tests (stage-only env var stops before venv creation),
per `dadaia-test-stewardship`. Full gate green: `ruff format --check .`,
`ruff check --no-cache .`, `mypy --strict dadaia_workspace/` (266 files, no issues),
full suite `pytest -p no:cacheprovider -m 'not quarantine' -n auto` — 2436 passed (was
2431, +5 new tests), 3 skipped, 0 failed; `dadaia doctor` — all invariants OK. LOC
delta: +381/-15 in `pyproject.toml`+`poetry.lock` (mostly lockfile), +271 new lines
across 2 new files (122-line runner script, 149-line wiring test).

---

- [x] **T-043-29 — FR21a: measure the complexity maxima and pin the ceilings at them**

**Owner role:** software-engineer · **Commit:** `feat(T-043-29): enable C90/PLR1702 ratcheted at the measured maxima`

**Preconditions:** T-043-28 `[x]`.

**Write set:** `pyproject.toml` (`select` + `[tool.ruff.lint.mccabe]`), the **V6** capture.

**Description:** **One task, two steps, no gap:** run ruff with `C90`/`PLR1702` at a
permissive ceiling and record the observed maxima (V6); set the ceilings **at** those maxima
in the same task. Never an aspirational number (R8). Document that the ceilings ratchet
**only downward** and that any decrease is justified in CLOSURE.

**Done criterion:** A21.1–A21.3 hold; `ruff check` green at HEAD by construction.

**Parallelism:** none.

**Evidence:** Synced the shared venv's stale `ruff 0.15.20` to the exact
`poetry.lock`-pinned `0.16.2` before measuring (a stale binary would have silently
drifted from what the pin enforces). V6 (full-repo scope, matching the actual
`ruff check .` gate — `dadaia_workspace/` + `tests/` + `scripts/`):
`ruff check --no-cache --select C901,PLR1702 --preview --config
"lint.mccabe.max-complexity=1" --config "lint.pylint.max-nested-blocks=1"
--output-format=concise .` — 2703 findings at ceiling 1. True observed maxima:
complexity **63** (`dadaia_workspace/features/panel/handler.py:330
make_handler_class`), nesting **6**
(`dadaia_workspace/features/telemetry/reader/allowlist.py:116`); both already inside
`dadaia_workspace/`, so no `tests/**` per-file-ignore was needed (A21.1). Full top-10
tables, raw captures and the ratchet-bites probe:
`.dadaia/tmp/software-engineer/20260817/v0.4.3-T-043-29-v6-complexity-maxima.md`.
Pinned in the same task: `select` gains `C90`, `PLR1702`; `[tool.ruff.lint.mccabe]
max-complexity = 63`; `[tool.ruff.lint.pylint] max-nested-blocks = 6`.
`PLR1702` is preview-status at 0.16.2 (`ruff rule PLR1702` demands `--preview`) —
`preview = true` added, scoped to `[tool.ruff.lint]` only (verified it never touches
`ruff format`); its one measured side effect, the preview rule `B903` newly active
under the already-selected `B` prefix (4 hits, all in `tests/**`), went to `ignore`
rather than widening this task's write set into unrelated test-file edits — both
documented inline at the config site alongside the ratchet-only-down doctrine block
(A21.3; ties to T-043-30's mandatory CLOSURE `## Size accounting` table, A21.4/A21.5).
Ratchet-bites probe (RED-equivalent): one ceiling below each measured maximum,
scoped to the exact offending file, flags exactly that top offender and nothing else
(`max-complexity=62` on `handler.py` → `make_handler_class is too complex (63 > 62)`;
`max-nested-blocks=5` on `allowlist.py` → `Too many nested blocks (6 > 5)`) — the
committed `pyproject.toml` ceilings stay at the measured 63/6, never the probe values.
A21.2: `ruff check --no-cache .` — `All checks passed!`, green at HEAD by construction.
**Side finding, registered not fixed here** (out of this task's write set; the affected
paths are FROZEN `specs/_archive/**`): with the correctly pinned `ruff==0.16.2`, `ruff
format --check .` newly reformats 5 archived Markdown files (fenced Python code blocks)
— reproduced as pre-existing via `git stash` (identical before/after this task's diff).
Bug `ruff-0-16-2-markdown-python-fence-format-drift` registered
(`specs/bugs/bugs.jsonl`). Full gate: `ruff check --no-cache .` green;
`ruff format --check .` fails only on the 5 pre-existing/bug-registered archive files
(unrelated to this diff, confirmed via `git stash`); `mypy --strict dadaia_workspace/`
— 266 files, no issues; full suite `pytest -p no:cacheprovider -m 'not quarantine' -n
auto` — 2436 passed (unchanged from T-043-28's baseline — no new tests, config-only
change), 3 skipped, 0 failed; `dadaia doctor` — all invariants OK. LOC delta: `git diff
--stat` — `pyproject.toml` +47/-2 (mostly comments — the doctrine block, the preview/B903
rationale — plus 4 real governance config lines: `C90`/`PLR1702` in `select`, `B903` in
`ignore`, `preview = true`, `max-complexity = 63`, `max-nested-blocks = 6`); +1 line
`specs/bugs/bugs.jsonl` for the bug event (ADDITIVE).

---

- [x] **T-043-30 — FR21b: make `## Size accounting` a required CLOSURE section**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-30): require a Size accounting table in release closure`

**Preconditions:** T-043-29 `[x]`. **Write set:** `public/skills/dd-release-closure/SKILL.md` + projection.

**Description:** The CLOSURE template gains a mandatory `## Size accounting` table:
production LOC added/deleted/net, the three largest additions and deletions by file, max
complexity before/after, and the nesting-violation count.

**Done criterion:** A21.4 holds; T-043-52 fills it (A21.5).

**Parallelism:** none.

**Evidence:** `dadaia_workspace/public/skills/dd-release-closure/SKILL.md` gained a
mandatory `## Size accounting` section between `## Validations` and `## Drifts`,
matching the skill's existing `**Mandatory**` framing style (same pattern as the
"Disposition sweep (mandatory)" section). The table covers exactly A21.4's five items:
production LOC added/deleted/net; a 3-row "three largest additions by file" table; a
3-row "three largest deletions by file" table; a ceiling before/after table for `C90`
(`max-complexity`) and `PLR1702` (`max-nested-blocks`) with a justification column
required only on decrease, cross-referencing the T-043-29-pinned 63/6 ceilings; and a
nesting-violation count against the pinned `PLR1702` ceiling. Closing law line included
verbatim: "ceilings ratchet only downward; a decrease is justified in CLOSURE."
Projection: `dadaia public stage` (12 asset groups staged) → `dadaia public install
--target all` (`.claude/skills/dd-release-closure/SKILL.md` and
`.agents/skills/dd-release-closure/SKILL.md` both synced from source — `dd-release-closure`
is not projected to `.codex`/`.kimi-code`, confirmed via `manifest.json`, unaffected) →
`dadaia public doctor` — zero `[error]` lines, `public-privacy` `[ok]`, only the expected
`[warn] git-dirty` on the just-edited source file (pre-commit) and pre-existing
`[foreign]`/`[info]` lines unrelated to this diff. No golden/byte-identity test pins this
skill's content — `tests/e2e/features/test_public_pipeline.py` and the two
`_golden/*_v0158.json` fixtures only assert the skill's presence by name/path, unaffected
by a body-content change; confirmed no regeneration needed. Gate: `ruff check --no-cache
.` — `All checks passed!`; `ruff format --check .` fails only on the same 5 pre-existing
archived Markdown files from T-043-29's bug `ruff-0-16-2-markdown-python-fence-format-drift`
(unrelated to this diff — a Markdown-only skill-source change cannot touch those paths);
`mypy --strict dadaia_workspace/` — 266 files, no issues; full suite `pytest -p
no:cacheprovider -m 'not quarantine' -n auto` — 2436 passed (unchanged from T-043-29's
baseline — doc-only change, no test delta), 3 skipped, 0 failed; `dadaia doctor` — all
invariants OK. LOC delta: `git diff --stat` —
`dadaia_workspace/public/skills/dd-release-closure/SKILL.md` +36/-0 (new section only,
no restructuring of existing content).

---

- [x] **T-043-31 — `alpha-3` close: `qa-engineer` review**

**Owner role:** qa-engineer · **Commit:** `test(T-043-31): alpha-3 qa review`

**Preconditions:** T-043-24 … T-043-30 all `[x]`. **Write set:** the QA artifact + handoff.

**Done criterion:** every `alpha-3` acceptance id verified or explicitly named unverified;
PLAN §5 `alpha-3` exit criteria met.

**Evidence:** `specs/releases/v0.4.3/ALPHA-3-QA.md` — **APPROVED**. 19/21 acceptance ids
(A18.1–A20.4, A21.1–A21.4) verified PASS against the live tree at `5b517854`; A21.5/A21.6
named UNVERIFIED-by-design (MEMORY-class, CLOSURE-phase work, correctly out of this
IMPLEMENTATION-phase segment). PLAN §5 `alpha-3` exit criteria all met. All three
in-segment Arm-B riders (`03bc12d3`, `10775510`, `5b517854`) carry complete
`reported`→`resolved` bug-ledger pairs; `dadaia bugs status` — 0 open bugs. Live re-run:
full suite `pytest -p no:cacheprovider -m 'not quarantine' -n auto` — 2437 passed, 3
skipped, 0 failed; `dadaia ci preflight` — 5/5 PASS; `dadaia doctor` — all invariants OK;
`dadaia specs doctor --context dadaia-workspace` — 0 errors, 5 pre-existing warnings
(unrelated to this segment); `dadaia public doctor` — 0 error/drift/missing lines.
Repo self-scan (`tests/integration/test_repo_self_scan.py`) — 5/5 passed, confirming the
committed QA artifact carries no contiguous denylisted literal.

**Parallelism:** none.

---

## `alpha-4` — WS-C, the Codex fidelity boundary

- [x] **T-043-32 — FR22a: scope the six surviving intents and re-measure the byte baseline**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-32): scope the Codex fidelity work against the current tree`

**Preconditions:** T-043-31 `[x]`. **Write set:** the scoping note + the **V7** capture.

**Description:** Re-verify each surviving intent against HEAD and give it an acceptance id.
Intent 6 and the 12-persona sub-claim are **struck at pick** (SPEC FR22) — record their
anchors so the strike is auditable. Re-measure the nine TOMLs' bytes (the 126,155 B figure
is from 2026-08-15 and is not quoted).

**Done criterion:** every surviving intent has an id and a verified anchor; V7 captured.

**Parallelism:** none.

**Evidence:** both struck items re-verified live and anchored — intent 6 (`ctx_inject`
law order) confirmed **already delivered** at `hooks/ctx_inject.py:185-218` (2-line drift
from the SPEC's `185-216` citation, same function, explicit law-order docstring, no
first-alive fallback); the "12-persona" sub-claim confirmed **void** at
`public/entities/registry.json:4-41` (exactly 9 personas; repo-wide grep for the phrase
outside this release's own SPEC returns only archived/historical hits). All six surviving
intents re-verified live with a fresh anchor each, none invalidated, all given their
acceptance id per the SPEC scheme: A22.1 compact TOMLs
(`infrastructure/install_helpers.py:572-600`, no compaction step exists today) → T-043-33;
A22.2 law-loaded-once (`.codex/hooks.json`, parent `SessionStart` wired, no
`SubagentStart` wiring — delegated visibility unproven) → T-043-33; A22.3 stale
headless-no-hooks claim (`infrastructure/codex_doctor.py:624-636`, still unqualified,
contradicts the live-verified codex-cli-0.144.4 fact already recorded in the
`ai-harness-codex` skill) → T-043-34; A22.4 certification exercising installed Codex
(`features/certification/service.py`, one static-string hit only, no installed-Codex
probe) → T-043-34; A22.5 `ENT-DERIVE-1` behavioral fidelity
(`infrastructure/codex_doctor.py:673-…`, name/shape bijection only, no mutation fixture)
→ T-043-35; A22.6 phantom skill-ref prefix (absorbed #37,
`infrastructure/runtime_transforms/codex_assets.py:39-46`, `"memory-ctx"` has no
`public/skills/` match, only a `public/runtime/codex/memory-ctx/` runtime asset) →
T-043-35; A22.7 stale doc (`public/skills/ai-harness-codex/SKILL.md:99`, exact line
match, `public/rules/*.md` documented against a directory confirmed **not** to exist) →
T-043-36; A22.8 cross-cutting isolation constraint (no single anchor — judged at
T-043-36's V8 against this task's V7) → T-043-36. Full per-intent verdict table + method:
`.dadaia/tmp/ai-engineer/20260817/v0.4.3-T-043-32-codex-scoping-note.md`. V7 byte
baseline captured via the real production `install(target="codex")` path into an
isolated scratch root (never touching the live `.codex/` projection): 9 TOMLs, 127,594 B
total (ai-engineer 17,890; code-reviewer 9,558; product-engineer 23,164; project-auditor
14,095; project-manager 8,548; qa-engineer 16,199; security-reviewer 11,473;
software-architect 16,024; software-engineer 10,643) — **+1,439 B above** the void
2026-08-15 figure of 126,155 B, which is not quoted as current; determinism confirmed by
sha256-identical re-run; cross-checked byte-identical against the live `.codex/agents/`
projection at the workspace root. Full command + per-file detail:
`.dadaia/tmp/ai-engineer/20260817/v0.4.3-T-043-32-v7-codex-byte-baseline.md` (measurement
script: `.dadaia/tmp/ai-engineer/20260817/measure_codex_tomls.py`). No non-Codex file
touched; no production source, no `public/agents/**`, no `public/skills/**` edited by
this task — scoping only, as declared in the write set.

---

- [x] **T-043-33 — FR22b: compact the personas and load the law once**

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

**Evidence:** A22.1 — new `_compact_codex_developer_instructions()` (7 disjoint regex
patterns) added to `infrastructure/runtime_transforms/codex_assets.py`, applied inside
`_render_codex_agent_toml()` to `developer_instructions` before TOML serialization (the
renderer seam; no hand-edit of any projection; `install_helpers.py`/`codex.py`
untouched). Removed: the two generic H1 pointer blockquotes (DADAIA §4 handoff-first +
"shared workspace protocol"), the "## Step 0 — Memory bootstrap" heading+pointer, the
"Artifact emission" subsection (EN + PT variants), the "Report/handoff emission
follows…" trailing blockquote, the "## Implementation review gate" section, and the
generic "## dadaia CLI" command block — all byte-identical (or near-identical)
restatements of law/protocol already covered natively by `AGENTS.md` or by a named
skill (`dadaia-step0-memory-bootstrap`, `dadaia-handoff-emitter`, `dadaia-task-manager`,
`dadaia-cli`), never role identity/decisions/authority/refusal boundaries. Kept intact
and test-pinned: `project-manager`'s role-specific continuation inside its mixed
blockquote, `project-auditor`'s trailing appended scope-rule content past its `## dadaia
CLI` section, and `product-engineer`'s DISTINCT "## dadaia CLI reference" (D-1
shell-less routing table, never matched by the generic-CLI pattern). Re-measured via the
identical T-043-32 production-path script (`measure_codex_tomls.py`) into an isolated
scratch root: V7 127,594 B → V8 **116,970 B**, **−10,624 B (−8.3%)**, every one of the 9
TOMLs shrank (ai-engineer 17,890→15,753 −11.9%; code-reviewer 9,558→8,590 −10.1%;
product-engineer 23,164→22,113 −4.5%; project-auditor 14,095→13,073 −7.3%;
project-manager 8,548→8,197 −4.1%; qa-engineer 16,199→15,117 −6.7%; security-reviewer
11,473→10,505 −8.4%; software-architect 16,024→14,969 −6.6%; software-engineer
10,643→8,653 −18.7%); determinism re-verified sha256-identical across two independent
scratch renders; the live `.codex/agents/*.toml` projection (via `dadaia public install
--target all`) confirmed byte-identical to the scratch capture, and the install run
touched exactly those 9 files (`[ok]`) — every other Codex asset (`hooks.json`,
`config.toml`, `rules/*.rules`, `skills/memory-ctx/SKILL.md`) and every non-Codex
projection reported `[skip]` (zero byte-change), satisfying A22.8's cross-cutting
constraint one task early. A22.2 — investigated and resolved the scoping note's open
question: the law reaches every Codex agent context via NATIVE per-directory
`AGENTS.md` discovery, independent of `SessionStart`/`SubagentStart` hooks (the
`.codex/hooks.json` `SessionStart`-only gap covers the separate dadaia `ctx_inject`
memory-bootstrap injection, not the law). Live executed-path proof (codex-cli 0.147.0,
`codex exec --sandbox read-only`, real workspace root): the **parent session**
unprompted quoted the literal opening words of the projected root `AGENTS.md`
(`YES-AGENTS-MD-VISIBLE > **AI agent rules.** This file is generated from`, session
`01a0117d-…`); a **delegated custom-agent subagent** (`agent_type="software-engineer"`,
non-forked) independently confirmed both its own compacted persona identity
("Software Engineer") and AGENTS.md visibility (`YES — "AGENTS.md instructions for
<workspace-root>"` [operator absolute path masked, repo self-scan convention — the
quoted value was this workspace's real root], session `01a0117e-…`) — proving the law now loads
exactly once (native `AGENTS.md`) for both, since the A22.1 compaction removed the
inline restatement that had made it load twice. Stated gap (routed to T-043-37): the
`ctx_inject` `SessionStart`-only memory-bootstrap convenience injection (not the law)
remains parent-session-only — no `SubagentStart` wiring exists; fixing it touches
`runtime_config.py`'s `codex_hooks()` builder, outside this task's write set. Full
evidence, per-file table and verbatim transcripts:
`.dadaia/tmp/ai-engineer/20260817/v0.4.3-T-043-33-compaction-and-law-once-evidence.md`.
Rendering-contract tests added/verified in
`tests/unit/infrastructure/test_public_assets_render.py` (4 new tests: strip-keeps-role-
content, mixed-blockquote/trailing-content preservation, `CLI reference` non-match,
renderer-seam application) — full suite 2441 passed, 3 skipped (platform-only),
`ruff format --check`/`ruff check`/`mypy --strict` clean, `dadaia public doctor` all
`[ok]`, `dadaia doctor` healthy.

---

- [x] **T-043-34 — FR22c: truthful trust boundary and live certification**

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

**Evidence:** A22.3 — `codex_doctor.py`'s `codex_trust_boundary_info` (`WS-CDX-HYGIENE`)
replaced the unqualified "interactive fire / headless never fire" claim with a runtime
`codex --version` probe (`_probe_installed_codex_version`, injectable via
`version_probe=`, defaulting to the real probe — production wiring unchanged) that
degrades honestly: absent Codex → explicit UNVERIFIED line, an installed version other
than `_CODEX_HOOKS_LIVE_CERTIFIED_VERSION` ("codex-cli 0.144.4", the `ai-harness-codex`
skill §9 / T-043-32 scoping-note citation) → UNVERIFIED + "rerun `dadaia certify`",
only an EXACT version match asserts the fire-in-both fact. `check_codex_rule_corpus_reachable`'s
docstring now names its own claim as STATIC reference integrity only, distinct from
`codex_trust_boundary_info`'s effective prompt visibility. RED-first: the pre-fix test
`test_trust_boundary_info_line_states_boundary` (pinning the stale claim) was replaced
with 8 new tests covering all 3 branches + the probe's own absent/nonzero-exit/timeout/
success cases (`tests/unit/infrastructure/test_codex_rule_corpus_reachable.py`) —
confirmed RED against pre-fix code (`ImportError` on the new symbols), GREEN after.
`tests/helpers/golden_platform.py`'s `canon_env_line` gained a trust-boundary
canonicalization regex (leak-class-3 style, D-CX-9 precedent) since the line is now
genuinely host-state-dependent (whether/which Codex CLI is on PATH); golden regenerated,
1-line diff, `test_golden_never_buries_an_attesting_check` still passes (the
`codex:trust-boundary` substring survives canonicalization).

A22.4 — `certification/service.py` gained `_codex_live_probe_detail` (bounded: 15s
`codex --version` + 60s `codex exec --sandbox read-only --skip-git-repo-check`, a fixed
marker prompt/response pair) wired as the `codex-live-probe` check inside `certify()`;
absent Codex raises `_CertificationSkip` (never `FAIL`) via a new `check()` branch;
`_all_checks_ok` now accepts PASS **and** SKIP. Unit tests
(`tests/unit/features/certification/test_service_codex_live_probe.py`, 8 tests) inject a
fake `CertificationProcess` — never the real binary — covering skip/nonzero-version/
nonzero-exec/missing-marker/success/`_all_checks_ok` shape. One env-gated integration
test (`tests/integration/features/certification/test_codex_live_probe_live.py`,
`skipif(shutil.which("codex") is None, reason="... plan ref T-043-34 (v0.4.3 A22.4) ...")`)
runs the REAL `SubprocessCertificationProcess` against the installed Codex CLI — 1 passed
in 4.99s, this environment (codex-cli 0.147.0). Live-probe evidence (direct function
call + a full `dadaia certify --json` run, `"ok": true`, `codex-live-probe` PASS among
11 other PASS checks) captured at
`.dadaia/tmp/software-engineer/20260817/v0.4.3-T-043-34-live-probe.md`.

**Arm-B in-segment rider (escalate-at-discovery, precedent `03bc12d3`):** the full-suite
gate run surfaced a pre-existing, out-of-write-set failure — the T-043-33 evidence
paragraph above (this same file, authored by the prior task) quoted a live Codex
transcript verbatim, reproducing the operator's absolute local workspace path
(`home-abs-path` denylist pattern). Registered + fixed same session: bug
`t043-33-absolute-path-leaked-into-tasks-md` (`reported`+`resolved`), masked to
`<workspace-root>` with an inline redaction note, commit `8c50e1ca` staging exactly
`specs/releases/v0.4.3/TASKS.md` + `specs/bugs/bugs.jsonl`.
`tests/integration/test_repo_self_scan.py::test_no_hit_outside_the_shrink_only_baseline`
RED before (1 unexpected hit) → GREEN after; full self-scan suite 5 passed / 0 failed.

**Full gate (this task's commit + the rider, both on `feature/0.4.3`):**
`ruff format --check .` / `ruff check --no-cache .` / `mypy --strict dadaia_workspace/`
all clean; `pytest -p no:cacheprovider -m 'not quarantine' -n auto` — 2456 passed, 3
skipped (pre-existing, platform-only: 2 Windows-only, 1 no-non-loopback-IPv4), 0 failed;
`dadaia doctor` — "All invariants OK"; `dadaia ci preflight` — 5/5 PASS (ruff
format/check, mypy --strict, lint-imports, pytest).

---

- [x] **T-043-35 — FR22d: behavioral `ENT-DERIVE-1` and the phantom skill prefix (#37)**

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

**Evidence:** A22.5 — `check_entities_derivation` gained three helpers
(`_persona_content_drift`, `_behavior_content_drift`, `_behavior_module_ref_missing`)
extending both existing checks from name/shape to content: (2) Persona ↔ sub-agent
bijection now also opens each correctly-bijected file — a stub with no parseable
frontmatter, or an internal identity swap (frontmatter `name:` diverging from its own
filename), is DRIFT even though filename-only bijection passes it; (3) Deterministic
Behavior harness-key coverage now also follows every `dadaia_workspace.<module>`
reference embedded in an implementation description back to a real source file — the
concrete "a hook silently stops enforcing" drift the T-043-32 scoping note named (#8
intent 5). Six drift classes total, each proven by a scratch-render mutation fixture in
`tests/unit/infrastructure/test_entities_derivation_behavioral.py` (10 tests): the 3
pre-existing name/shape classes under the same methodology
(`test_orphan_subagent_without_persona_blocks`,
`test_dead_persona_without_subagent_blocks`,
`test_behavior_missing_harness_key_blocks`) plus 3 new behavioral classes
(`test_persona_stub_body_blocks`, `test_persona_identity_mismatch_blocks`,
`test_behavior_implementation_module_reference_broken_blocks`), plus a package-form
resolution edge case, an additive-multi-drift case, a clean-scratch baseline, and a
real-packaged-tree sanity check. RED-first: the 3 new-class fixtures failed against the
pre-fix check (name-only bijection/coverage cannot see stub bodies, identity swaps, or
broken module references — confirmed by running the file before the extension: 4
failed / 6 passed), extension applied, all 10 GREEN. The real tree carries zero
behavioral drift — `entities-derivation` stays a single `[ok]` line, unchanged text
(`9 Personas ↔ 9 core sub-agents; 5 Deterministic Behaviors derived for all entry
harnesses`), confirmed both by the dedicated real-tree test and a live `dadaia public
doctor` run.

A22.6 — `memory-ctx` in `_CODEX_SKILL_REF_PREFIXES` is NOT phantom: it is a Codex-only
runtime adapter (`public/runtime/codex/memory-ctx/SKILL.md`, projected to
`.codex/skills/memory-ctx/SKILL.md` by `dcx6_codex_runtime_adapters`) that D-CX-7
already resolves via its `.codex/skills` root — it was simply never proven. Decision:
documented, not removed — a new `_CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS` frozenset
names it, with an inline comment on `_CODEX_SKILL_REF_PREFIXES` explaining the
two-source contract (a real `public/skills/` name/prefix match, or a documented
runtime-asset exception backed by a real `public/runtime/codex/<name>/SKILL.md`).
`tests/contract/test_codex_skill_ref_prefixes.py` gained 5 tests deriving the whole
tuple from the on-disk inventory: `test_codex_skill_ref_prefixes_bind_to_the_real_inventory`
(every entry, zero phantoms), `test_runtime_asset_exceptions_are_a_declared_subset_of_the_prefixes`,
`test_memory_ctx_is_a_documented_exception_backed_by_a_real_runtime_adapter` (the exact
#37 claim), and two self-tests of the detector itself
(`test_phantom_prefix_detector_catches_a_fabricated_phantom`,
`test_phantom_prefix_detector_honors_an_undocumented_exception_as_phantom`) proving the
methodology would actually fail on a genuine future phantom, not just pass on today's
clean tuple. RED-first: importing `_CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS` before the
production edit existed failed with `ImportError` (confirmed via a scoped `git stash`
re-run); GREEN after.

Both extensions stayed inside the declared write set — `check_entities_derivation`
(+3 helpers, same module) and `_CODEX_SKILL_REF_PREFIXES` (comment + one companion
constant, same module) — with mutation fixtures and tests as the only other touched
paths; zero non-Codex or unrelated-Codex projection files touched (`dadaia public
doctor` unchanged: still all `[ok]`/`[foreign]` lines it was before, `entities-derivation`
line byte-identical). Complexity of every touched/added function stays far under the
`max-complexity = 63` ceiling: `check_entities_derivation` 13 (was ~9 pre-extension),
`_persona_content_drift` 5, `_behavior_content_drift` 6, `_behavior_module_ref_missing`
2. LOC delta (`git diff --numstat`): `codex_doctor.py` +113/-2 (3 new helpers +
docstring + 2 call-site splices), `codex_assets.py` +18/-0 (comment + 1 constant,
`_CODEX_SKILL_REF_PREFIXES` itself unchanged), `test_codex_skill_ref_prefixes.py`
+104/-7, new file `test_entities_derivation_behavioral.py` +246 — production net +129
/ tests net +343.

**Full gate (this task's commit, on `feature/0.4.3`):** `ruff format --check .` /
`ruff check --no-cache .` / `mypy --strict dadaia_workspace/` all clean (266 source
files); `pytest -p no:cacheprovider -m 'not quarantine' -n auto` — 2471 passed, 3
skipped (pre-existing, platform-only: 2 Windows-only, 1 no-non-loopback-IPv4), 0 failed
— +15 over the T-043-34 baseline (2456), exactly the 10 + 5 new tests added this task;
`dadaia doctor` — "All invariants OK"; `dadaia public doctor` — exit 0, every line
`[ok]`/`[foreign]`/`[info]` as before, `entities-derivation` line unchanged; `dadaia ci
preflight` — 5/5 PASS (ruff format/check, mypy --strict, lint-imports, pytest).

---

- [x] **T-043-36 — FR22e: reconcile the Codex documentation and prove isolation**

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

**Evidence — A22.7 (stale claims removed/updated, 4 files, 6 edits):**
`public/skills/ai-harness-codex/SKILL.md` §2 — the `public/rules/*.md` taxonomy (line 99,
a directory confirmed absent from disk) replaced with the real single-file surface
(`DADAIA.md`, sourced from `public/data/DADAIA.md`, projected to `.claude/rules/DADAIA.md`)
plus an explicit "no `public/rules/` directory" statement; §9 — the self-contradicting
"interactive-only (live-verified 0.139.0)" headline/table and the trailing "enforces only
in interactive sessions" line rewritten as a version-qualified table (0.139.0 historical
SUPERSEDED row vs 0.144.4 current live-certified row), pointed at `dadaia public doctor`'s
`codex:trust-boundary` line. Three academy lessons under
`features/academy/knowledge_basis/07_codex/` carried the same stale unqualified
headless-never-fires claim, each corrected to the version-qualified fact:
`01_codex_mental_model.md` (§"What Codex Enforces vs What It Reads"),
`04_hooks_rules_and_config.md` (the "Hooks fire only in interactive sessions" section
header + body, and the closing "dadaia Projection Rules" note),
`05_subagents_and_delegation.md` (the dispatcher-mapping table's hooks row). Repo-wide
grep confirmed zero remaining live hits for `public/rules`, the headless-never-fires
claim, or `12 persona`/`12-persona` outside `_archive/` material (consistent with
T-043-32's D3). `specs/memory/product/harness/harness-codex.md` still carries the stale
framing — out of scope by SPEC's own memory-ownership table (routed to **CLOSURE**,
`product-engineer`); flagged, not edited.

**Evidence — A22.8 (V8 byte-diff isolation):** Full detail + method:
`.dadaia/tmp/ai-engineer/20260817/v0.4.3-T-043-36-v8-projection-isolation.md`. Sha256
inventory of all 81 files across `.claude/**`, `.agents/**`, `.codex/**`, `.kimi-code/**`,
`DADAIA.md`/`AGENTS.md`/`CLAUDE.md`, captured before the edit and again after
`dadaia public stage && dadaia public install --target all`: exactly two lines differ —
`.agents/skills/ai-harness-codex/SKILL.md` (Codex's own skill-discovery path) and
`.claude/skills/ai-harness-codex/SKILL.md` (Claude Code's mirror of the same canonical
skill file — skill bodies carry no Codex-specific rendering seam, per this same skill's
"Cross-harness degradation constraint (HARD)"). Every persona TOML/`.md`, hook, config,
Rules file, the other 23 skills, every `.kimi-code/**` file, and the four law/rule copies
are byte-identical before and after. A22.8 holds under this reasoned classification: zero
byte-changes landed in any Codex-unrelated surface.

**Full gate (this task's commit, on `feature/0.4.3`):** `ruff format --check .` (852
files already formatted) / `ruff check --no-cache .` (all checks passed) / `mypy --strict
dadaia_workspace/` (266 source files, no issues) all clean; `pytest -p no:cacheprovider
-m 'not quarantine' -n auto` — 2471 passed, 3 skipped (pre-existing, platform-only), 0
failed — unchanged from the T-043-35 baseline (doc-only change, no test added/removed);
`dadaia doctor` — "All invariants OK"; `dadaia public doctor` — 0 `[error]` lines, 183
`[ok]` lines, only the expected `[foreign]` repo entries and the pre-existing
`codex:trust-boundary` UNVERIFIED-for-0.147.0 `[info]` line; `pytest
tests/integration/test_repo_self_scan.py` — 5 passed.

---

- [x] **T-043-37 — `alpha-4` close: `qa-engineer` review**

**Owner role:** qa-engineer · **Commit:** `test(T-043-37): alpha-4 qa review`

**Preconditions:** T-043-32 … T-043-36 all `[x]`. **Write set:** the QA artifact + handoff.

**Done criterion:** certification evidence and `entities-derivation` `[ok]` recorded; PLAN §5
`alpha-4` exit criteria met.

**Parallelism:** none.

**Evidence:** `specs/releases/v0.4.3/ALPHA-4-QA.md` — **APPROVED**. All 8 acceptance ids
(A22.1–A22.8) independently re-verified against the live tree at `02c129fe` (byte counts,
greps, targeted pytest re-runs, an independent re-diff of the T-043-36 81-file sha256
capture), not re-quoted from the implementer's own session. PLAN §5's `alpha-4` exit
criteria fully met: live `dadaia certify --json` run by this review → `"ok": true`, 12/12
checks PASS, `codex-live-probe — codex-cli 0.147.0: live exec probe observed
'DADAIA-LIVE-PROBE-OK'`; `dadaia public doctor` → `[ok] entities-derivation: 9 Personas ↔
9 core sub-agents; 5 Deterministic Behaviors derived for all entry harnesses`. Three
explicit dispositions recorded in the artifact's §4: (1) the T-043-33 stated
`ctx_inject` `SubagentStart`-only gap does not block A22.2 — the law itself (not the
dadaia convenience injection) is proven to load once for both parent and delegated
sessions via native `AGENTS.md` discovery; (2) exactly **one** Arm-B rider bug exists in
the `alpha-4` window (`t043-33-absolute-path-leaked-into-tasks-md`, `8c50e1ca`,
`reported`→`resolved` complete), correcting the "two rider bugs" framing with evidence;
`dadaia bugs status` → `[ok] 0 open bug(s)`; (3) `specs/memory/product/harness/
harness-codex.md`'s stale headless-asymmetry framing is MEMORY-class, unwritable in this
release's `IMPLEMENTATION` phase — correctly deferred to `rc-1` CLOSURE and named
UNVERIFIED-by-design, matching `ALPHA-3-QA.md`'s precedent for A21.5/A21.6. Full gate
(live, this session): `pytest -p no:cacheprovider -m 'not quarantine' -n auto` — 2471
passed, 3 skipped, 0 failed; `dadaia ci preflight` 5/5 PASS; `dadaia doctor` — All
invariants OK; `dadaia specs doctor` — 0 errors, 5 pre-existing warnings (none new);
`dadaia backlog doctor` — clean; `pytest tests/integration/test_repo_self_scan.py` — 5
passed (redaction law honored in the artifact itself).

---

## `alpha-5` — WS-G, event-driven artifact GC (R10: before the consumer round)

- [x] **T-043-38 — FR23: ack-on-consume for coordination handoffs**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-38): consumer skills delete the coordination handoff they read`

**Preconditions:** T-043-37 `[x]`. **Write set:** the handoff-consumer discipline on the
skills surface (one location) + projections.

**Description:** State the rule **once**: a consumer skill deletes the coordination handoff
it consumed; a handoff carrying `artifact.path` is exempt and follows its report's
retention. No per-skill restatement.

**Done criterion:** A23.1–A23.3 hold, **and AG.1 holds for this deletion lane** (target
resolved, refused outside `.dadaia/`, symlinked directory never followed — FR17's doctrine
by reference).

**Parallelism:** none.

**Evidence:** The rule lands in exactly one location — `public/skills/dadaia-handoff-emitter/SKILL.md`,
new `## Consuming a handoff (ack-on-consume — FR23)` section — chosen because every one of
the nine core personas already lists `dadaia-handoff-emitter` in its `skills:` frontmatter
(grep-confirmed against all nine `public/agents/*.md`), so the rule is reachable from every
consumer without adding a new skill (no extra listing-budget tax) and without restating it
anywhere else (A23.1). A repo-wide grep for `retention|consumed handoff|delete.*handoff`
across `public/skills/` and `public/agents/` before the edit found zero existing
restatements of handoff-retention/deletion, so no pointer replacement was needed. The added
text states: (a) the deletion rule with the `artifact.path` exemption following its report's
retention (A23.2); (b) the AG.1 lane guard — resolve the target, refuse outside `.dadaia/`,
never follow a symlinked directory — inheriting FR17/A17.1 by reference, not restated
(AG.1); (c) an explicit "never break a surviving handoff" guardrail scoping deletion to
exactly the one consumed file, never a directory sweep (A23.3). Projection: `dadaia public
stage` (12 asset groups staged) → `dadaia public install --target all` (`.claude/skills/…`
and `.agents/skills/…` copies byte-diffed clean against the source after install) →
`dadaia public doctor` — no `[error]`/drift lines; only the pre-existing `[info]
codex:trust-boundary` UNVERIFIED-for-0.147.0 note and the expected `[foreign]` repo entries.
Full gate (live, this session): `pytest -p no:cacheprovider -m 'not quarantine' -n auto` —
2471 passed, 3 skipped, 0 failed; `dadaia doctor` — All invariants OK; `dadaia public doctor`
— zero drift; `pytest tests/integration/test_repo_self_scan.py` — 5 passed.

---

- [x] **T-043-39 — FR24: a consumed push verdict dies with the push**

**Owner role:** software-engineer · **Commit:** `feat(T-043-39): delete the security verdict consumed by a successful push`

**Preconditions:** T-043-38 `[x]`. **Write set:** `features/chokepoints/service.py`, the
append-only verdict ledger under `.dadaia/` + tests.

**Description:** After a successful push, delete the APPROVED verdict handoff(s) covering the
pushed delta. A verdict for an unpushed delta is never touched; deletion is best-effort and
never changes a push verdict. **The record outlives the handoff**: append one line (agent,
verdict, covered tip sha, timestamp) to the append-only ledger **before** deleting — a
failed append leaves the handoff in place.

**Done criterion:** A24.1–A24.4 hold — including the append-before-delete audit line
(A24.4) — **and AG.1 holds for this deletion lane**.

**Parallelism:** none.

**Evidence:** `push_gate_decision` (pre-push) runs entirely BEFORE git transfers any object,
so "the push succeeded" is categorically unknowable from inside it — a remote rejection can
still fail the push after that hook already returned allow. `gc_consumed_push_verdicts`
(`features/chokepoints/service.py`) is therefore a SEPARATE pure action function, never
callable from the pre-push path, documented (module docstring, above the new section) as
requiring an out-of-band, already-confirmed-successful `pushed_shas` set from its future
caller — a `reference-transaction` git hook or a `git push`-wrapping CLI verb, both
explicitly OUT OF SCOPE here (not in the declared write set: no hook script, no CLI
wiring). Ledger: `.dadaia/logs/push-verdict-gc-ledger.jsonl` (one JSON line per consumed
verdict: `ts`, `event="PUSH_VERDICT_CONSUMED"`, `agent`, `verdict`, `commit_sha`,
`source`) — same directory family as the pre-existing `.dadaia/logs/reconciler-events.jsonl`,
so a future FR27 (T-043-42) covers it with no separate carve-out. AG.1: `_iter_handoff_paths`
walks with `os.walk(..., followlinks=False)` (explicit, not an incidental `Path.rglob`
default) and `_resolved_within` refuses any candidate whose resolved path falls outside
`<workspace>/.dadaia/` before either the ledger append or the delete runs.
Tests: `tests/unit/features/chokepoints/test_push_verdict_gc.py` (10 new, RED confirmed via
`ImportError` before the implementation existed, GREEN after) — unrelated-verdict-survives +
multi-sha + non-qualifying-agent/verdict (A24.1); empty-`pushed_shas` no-op (A24.2);
best-effort unlink failure with a second handoff still processed in the same sweep (A24.3);
append-before-delete positive path + failed-append-leaves-handoff-in-place via a
directory-collision at the ledger path (A24.4); symlinked-directory-never-followed
(temporarily flipped to `followlinks=True` to confirm the fixture genuinely fails without the
guard, then reverted) + resolved-outside-`.dadaia/`-refused via a symlinked handoff FILE
(AG.1); one reconciliation-shape-tip-sha fixture proving no special-casing. Full gate (live,
this session): `ruff format --check` / `ruff check --no-cache` clean; `mypy --strict
dadaia_workspace/` — 266 source files, no issues; `pytest -p no:cacheprovider -m 'not
quarantine' -n auto` — 2481 passed, 3 skipped, 0 failed (was 2471 passed pre-change, +10 net
new); `dadaia doctor` — all invariants OK; `dadaia ci preflight --quick` — 5/5 PASS;
`pytest tests/integration/test_repo_self_scan.py` — 5 passed. `ruff check --select C901
--preview` clean at the pinned `max-complexity = 63` ceiling; `gc_consumed_push_verdicts`
measures ~12 (AST-walk approximation), well under the ceiling — no ratchet touched.

---

- [x] **T-043-40 — FR25: release closure sweeps its own artifacts**

**Owner role:** ai-engineer · **Commit:** `docs(T-043-40): add the artifact GC sweep to release closure`

**Preconditions:** T-043-39 `[x]`. **Write set:** `public/skills/dd-release-closure/SKILL.md` + projection.

**Description:** The closure template gains a sweep step with an explicit keep/delete rule.
Nothing referenced by a surviving CLOSURE evidence pointer may be deleted. Lands in the same
skill T-043-30 edited — re-read it before writing.

**Done criterion:** A25.1, A25.3 hold; T-043-52 executes it (A25.2); **the sweep step states
AG.1's lane guard** (resolve the target, refuse anything outside `.dadaia/`, never follow a
symlinked directory) as part of its keep/delete rule.

**Parallelism:** none.

**Evidence:** Re-read `public/skills/dd-release-closure/SKILL.md` current-on-disk (the
T-043-30-edited version carrying the mandatory `## Size accounting` CLOSURE section) before
writing, per the task's instruction. Two additions, both minimal-diff in the T-043-30/38
style: (a) a `## Artifact GC sweep` subsection added to the CLOSURE.md template (positioned
right before `## Archive decision`, mirroring the mini table + "referenced, not restated"
pointer pattern the `## Dispositions` section already uses for the "Disposition sweep"
section below it) — a 4-row kept/deleted/evidence table over handoffs, reports, tmp
captures, and lifecycle run records; (b) a new `## Artifact GC sweep (FR25, mandatory)`
protocol section, positioned after `## Memory Markdown update protocol` and before
`## Move-to-archive command` (the sweep needs CLOSURE's evidence pointers final, so it runs
after CLOSURE is written and before the archive move) stating the scope (this release's own
`.dadaia/` artifacts only), the keep/delete rule (KEEP anything a surviving `##
Validations`/`## Dispositions` evidence pointer references, no exception; DELETE the rest
once unreferenced), a pointer to `dadaia-handoff-emitter`'s ack-on-consume rule (T-043-38,
commit `47255c21`) for the handoff sub-case rather than restating it, and **AG.1's lane
guard stated verbatim**: "resolve the target, refuse any resolved target outside
`.dadaia/`, never follow a symlinked directory." The `## Finalization order` line updated
from "memory → CLOSURE → archive" to "memory → CLOSURE → sweep → archive" so the new step
composes into the existing sequencing statement rather than sitting orphaned. Composes
cleanly with T-043-30's `## Size accounting` section: both are mandatory CLOSURE
subsections that sit between `## Validations`/`## Dispositions` and `## Archive decision`
in the template, neither references or restates the other, and both close the same
"the CLOSURE document is the evidence-of-record" pattern — Size accounting for
production-code delta, Artifact GC sweep for this release's own working artifacts.
Projection: `dadaia public stage` (12 asset groups staged) → `dadaia public install
--target all` (`.claude/skills/dd-release-closure/SKILL.md` and
`.agents/skills/dd-release-closure/SKILL.md` byte-identical to source after install,
4 occurrences of "Artifact GC sweep" confirmed in each) → `dadaia public doctor` — no
`[error]`/drift; only the pre-existing `[info] codex:trust-boundary` UNVERIFIED-for-0.147.0
note, the expected `[foreign]` repo entries, and the expected `[warn] git-dirty` on the
uncommitted source file (cleared by this commit). Full gate (live, this session): `pytest
-p no:cacheprovider -m 'not quarantine' -n auto` — 2481 passed, 3 skipped, 0 failed;
`dadaia doctor` — All invariants OK; `pytest tests/integration/test_repo_self_scan.py` —
5 passed.

---

- [x] **T-043-41 — FR26: the reconciler reaps what it already walks**

**Owner role:** software-engineer · **Commit:** `feat(T-043-41): reap stale session, marker and zombie run records`

**Preconditions:** T-043-40 `[x]`. **Write set:** `hooks/sdd_post_gate.py` + tests; the **V10** capture.

**Description:** Delete session/presence records stale beyond N×TTL together with their tmp
markers and empty context dirs; reap zombie lifecycle/state run records. Best-effort and
fail-open, matching the reconciler it extends. A live session's records are never touched.

**Done criterion:** A26.1–A26.3 hold; V10 captured before/after; **AG.1 holds for this
deletion lane** (records, markers and empty context dirs are resolved and refused outside
`.dadaia/`; a symlinked directory is never followed).

**Parallelism:** none.

**Evidence:** New `sdd_post_gate._reap_stale_records` (+`ReapOutcome`, `_reap_sessions`,
`_reap_markers`, `_reap_presence`, `_reap_zombie_lifecycle_runs`), called from inside the
EXISTING throttled `_reconcile_working_tree` pass (right after `_stamp_throttle`, before
`_bound_context`) — no second, independent, unthrottled sweep; it runs on the same 30s
cadence the working-tree walk already had. Reap classes: (1) session records
(`.dadaia/sessions/<id>.json`) stale beyond N×TTL — `N = RECONCILER_REAP_TTL_MULTIPLIER =
3` (new `core/kernel_tunables.py` constant), deliberately more conservative than `dadaia
doctor --fix`'s manually-invoked 1×TTL graveyard GC, since this reaper fires automatically
on every PostToolUse call; (2) their paired tmp markers (`reconciler-last-*`,
`ctx-inject-fired-*`) — deleted unconditionally once the owning session is reaped, or via
their own mtime (same N×TTL) when orphaned (no owning session record at all — the real
workspace's own pre-existing garbage: markers for sessions/pseudo-sessions with no
`.dadaia/sessions/<id>.json`, e.g. `doctor`); (3) presence records
(`.dadaia/states/presence/<ctx>/<id>.json`) stale beyond N×PRESENCE_TTL_SECONDS, with the
now-(or-already-)empty context dir removed in the same pass; (4) zombie
`.dadaia/states/lifecycle/*.json` run records — `status` "running" or "completed" (no code
in `dadaia_workspace/` reads or writes this directory any more — the retired workflow
engine's orphaned state); "blocked" is excluded on purpose (a paused run still awaiting an
operator decision, never a zombie). The invoking session's OWN records (session, every
presence entry it owns, both its markers) are NEVER a candidate — an identity check, not
TTL math, since `_reap_stale_records` is also invoked directly by tests bypassing `main()`'s
own-record refresh. AG.1 (uniform across all four lanes): every unlink/rmdir target is
resolved (`_resolved_within`, mirroring `features.chokepoints.service`'s FR24 guard) and
refused if it resolves outside `.dadaia/`; every walk uses `os.walk(..., followlinks=False)`
(`_iter_files` for the flat session/marker/lifecycle lanes, an inline walk for the nested
presence lane) — verified with the T-043-39 trick (temporarily flipped to
`followlinks=True`, confirmed the isolated fixture then fails by actually discovering and
deleting a decoy reachable only through the symlinked dir, reverted). A26.3: every lane
wrapped in its own `contextlib.suppress(Exception)` (inner net) plus the caller's own
try/except (outer net) — never surfaced to, or capable of blocking, the git-status pass
that follows it. Tests: `tests/unit/hooks/test_post_gate_reap.py` (17 new, RED confirmed via
`AttributeError` before the implementation existed, GREEN after) — stale-session-reaped-
with-paired-markers, fresh-heartbeat-foreign-session-untouched, self-session-untouched-even-
when-ancient (A26.1), orphaned-marker-reaped-by-own-age, malformed-record-never-aborts-sweep
(session/presence/lifecycle, 3 fixtures), stale-presence-reaped-empty-dir-removed,
fresh-presence-survives, self-owned-presence-untouched, pre-existing-empty-dir-removed,
zombie-lifecycle-running-and-completed-reaped-blocked-survives (A26.2), the two AG.1
lane-guard fixtures (symlinked-dir-never-followed — isolated from the outside-resolve guard
by placing the decoy's real target INSIDE `.dadaia/`; outside-resolve-refused), unlink-
failure-best-effort (read-only lifecycle dir, unrelated session lane still completes —
A26.3), reap-never-raises-changes-exit-code (`main()` still returns 0), and
reap-shares-the-reconciler-throttle-window. Full suite unaffected: `tests/unit/hooks/`
(182 pre-existing) + this file (17 new) all green, no regression to the existing
`_reconcile_working_tree`/throttle/fail-open contract tests.

**V10 (real-workspace, not synthetic).** This workspace self-hosts
(`dadaia-workspace` editable-installed at `repos/dadaia-workspace`), so the installed
PostToolUse hook ran this exact change automatically — the AFTER snapshot is a REAL
production execution, not a manual script, logged to `.dadaia/logs/reconciler-events.jsonl`
at `2026-08-17T22:48:39Z`: `{"event": "RECONCILER_REAP", "sessions_reaped": 1,
"presence_reaped": 0, "markers_reaped": 10, "empty_context_dirs_removed": 2,
"lifecycle_runs_reaped": 67}`. BEFORE: 2 session records (1 live, 1 ~3-day-stale) / 1
presence record / 3 presence context dirs (2 already empty) / 6 `reconciler-last-*` + 6
`ctx-inject-fired-*` markers (2 self, 10 stale-or-orphaned) / 121 lifecycle records (54
blocked, 38 completed, 29 running — matches the SPEC's own measured evidence exactly).
AFTER: 1 session record (self only) / 1 presence record (unchanged, self, live) / 1
presence context dir / 1 `reconciler-last-*` + 1 `ctx-inject-fired-*` marker (self only) /
54 lifecycle records (all blocked). Live-session-untouched proof: this session's
`bound_at` stayed `2026-08-14T13:55:30Z` unchanged across the whole reap while
`last_seen_at`/`is_stale: false` kept advancing normally (`dadaia context show --json`),
its presence record and both its markers survived byte-identical in placement. Full
capture: `.dadaia/tmp/software-engineer/20260817/v0.4.3-T-043-41-v10-reconciler-reap.md`.

Full gate (live, this session): `ruff format --check .` / `ruff check --no-cache .` clean;
`mypy --strict dadaia_workspace/` — 266 source files, no issues; `pytest -p no:cacheprovider
-m 'not quarantine' -n auto` — 2498 passed, 3 skipped, 0 failed (was 2481 passed
pre-change, +17 net new); `dadaia doctor` — all invariants OK; `dadaia ci preflight --quick`
— 5/5 PASS; `pytest tests/integration/test_repo_self_scan.py` — 5 passed. `ruff check
--select C901 --preview` clean at the pinned `max-complexity = 63` ceiling; AST-walk
approximation of the new functions: `_reap_markers` ~14 (the highest), `_reap_presence`
~13, `_reap_sessions` ~9, `_reap_zombie_lifecycle_runs` ~8, `_reconcile_working_tree` ~10,
`_reap_stale_records` ~5 — all well under the ceiling, no ratchet touched.

---

- [x] **T-043-42 — FR27: writers rotate their own logs**

**Owner role:** software-engineer · **Commit:** `feat(T-043-42): rotate .dadaia log files at write time`

**Preconditions:** T-043-41 `[x]`. **Write set:** the `.dadaia/logs/*.jsonl` appenders
(`hooks/pre_gate.py` and peers) + tests.

**Description:** Each writer caps its log at ~1 MB and keeps current+1. Rotation happens at
write time by the owner of the file, never by an external cron; telemetry stays fail-open.

**Done criterion:** A27.1–A27.3 hold, including the concurrent-writer fixture.

**Parallelism:** none.

**Evidence:** Inventory of every ``.dadaia/logs/*.jsonl`` writer (grep for the directory
family): `hooks/pre_gate.py`'s `_append_latency` (`hook-latency.jsonl`);
`hooks/sdd_post_gate.py`'s `_append_reconciler_flag` + `_append_reap_event` (both write
`reconciler-events.jsonl`, unified behind one new local `_append_reconciler_event`
helper so the file has exactly one write call site); `features/chokepoints/service.py`'s
`_append_ledger_line` (`push-verdict-gc-ledger.jsonl`, the T-043-39/FR24 audit ledger).
The telemetry readers under `features/telemetry/` were inventoried and excluded — they
read FOREIGN session logs (`~/.claude`, `~/.codex`, `~/.kimi-code`), never write under
`.dadaia/logs/`. The bug store (`specs/bugs/bugs.jsonl`) was inventoried and excluded —
outside the `.dadaia/logs/` directory family and ADDITIVE/never-delete-law protected by
`DADAIA.md` §5, not an FR27 target.

**Ledger decision (push-verdict-gc-ledger.jsonl):** rotated, not exempted. The SPEC's own
FR27 text carries no carve-out, and T-043-39's own code comment/evidence (this file, the
`_LEDGER_RELPATH` block) already committed to it: "same directory family as
`reconciler-events.jsonl`, so a future FR27 covers it too, with no separate carve-out."
Rotation does not contradict A24.4's append-only property: "append-only" means the
ledger is never mutated/edited in place (still true — rotation only renames the whole
file, never touches a line inside it), not "retained forever" — FR27's current+1
retention applies to it exactly like every other appender.

**Helper design** (new `infrastructure/jsonl_log_rotation.py`, single implementation,
every appender funneled through it — none copy-pastes rotation):
`append_rotating_jsonl(path, line, *, max_bytes=None)` resolves its cap from
`core.kernel_tunables.LOG_ROTATION_MAX_BYTES` (a new zero-I/O constant, 1,000,000 bytes)
read at CALL TIME (a global lookup, never a bound default) so a test — or a future
caller — that reassigns the module attribute observes the new cap on the very next call
(the mechanism all five wiring tests below rely on). Design constraints that ruled out
the two more obvious homes: `core/` is blocked because its file-I/O purity ratchet
(`tests/contract/test_core_file_io_purity.py`) pins an exact 5-stem authorized set in
`specs/memory/architecture.md`, itself MEMORY-class and phase-gated to
DEFINITION/CLOSURE (current phase: IMPLEMENTATION) — unreachable this session, and not
this task's to touch regardless (product-engineer-owned surface); a plain `features/`
home is blocked by the `features-no-cross-feature` independence contract (chokepoints
is one of the enumerated mutually-independent packages). `infrastructure/` is the
sanctioned I/O layer with no such ratchet. `hooks/pre_gate.py` and
`hooks/sdd_post_gate.py` import it directly (hooks already import `infrastructure`/
`subprocess` freely — no contract restricts that edge).
`features/chokepoints/service.py` cannot import `infrastructure` at module level
(`features-no-infrastructure`) and its own docstring promises "NEVER imports
infrastructure" as a module-load-time guarantee, so `_append_ledger_line` uses a
function-scoped lazy import — the SAME "features -> infrastructure while container DI
is incomplete" idiom already used for `features.telemetry.service`'s ADR-1 lock-adapter
selection — with one new `ignore_imports` edge in `setup.cfg`
(`features-no-infrastructure` family) and the ignore-edge cap ratchet bumped 14 -> 15 /
family 6 -> 7 in `tests/contract/test_import_linter_ignore_cap.py`, in this same commit
(`lint-imports --no-cache`: 9 contracts kept, 0 broken).

Concurrency (A27.3): only a caller that observes the file AT/OVER the cap takes a lock —
every call below the cap stays a single `stat` + append, identical cost to every writer's
pre-FR27 code. The lock is a directory-mkdir mutex (`<path>.rotlock/`, `os.mkdir` atomic
on POSIX and Windows, no `fcntl`/platform split needed for a critical section this
short), bounded at 50 attempts x 2 ms, with a 5 s staleness reclaim so a crashed holder's
abandoned lock dir can never permanently stall rotation (`test_stale_lock_directory_is_
reclaimed`). Inside the lock, size is RE-CHECKED before rotating (double-checked
locking) — the mechanism that stops two near-simultaneous crossers from both calling
`os.replace` and destroying each other's rotated generation; a writer that observed
"under cap" never rotates at all, so O_APPEND's own atomicity guarantee (every append is
one buffered `write()` -> one OS syscall, and O_APPEND always targets end-of-file) is
what makes even a lock-free append near the boundary safe — its bytes land intact in
whichever generation its fd targets, never interleaved, never truly lost (worst case
relocated to the `.1` file instead of `current`). Fail-open (A27.2) throughout: every
failure — unwritable parent, target-already-a-directory, read-only file, a lock-timeout
— returns `False` without raising (9 fixtures in
`tests/unit/infrastructure/test_jsonl_log_rotation.py`, including
`test_readonly_logs_dir_blocks_rotation_but_append_still_lands`, which proves the append
still lands even when the containing dir is read-only and BOTH the lock and the rotate
fail).

**Concurrent-writer proof (A27.3):**
`tests/integration/infrastructure/test_jsonl_log_rotation_concurrency.py` spawns two REAL
`multiprocessing.get_context("spawn")` processes, synchronized on a `Barrier(2)` so both
start writing at the same instant (never sleep-luck) — 60 lines each (120 total) through
`append_rotating_jsonl` at a shared path, cap sized deterministically at 60% of the
combined planned bytes (`_choose_cap`) so the run crosses the cap exactly once regardless
of interleaving order (the module docstring proves the bound: the post-crossing
remainder, 40% of total, is always < the 60% cap). Assertions: no crash (`exitcode == 0`
for both workers); no corrupt/interleaved line (`json.loads` on every surviving line
raises on the first malformed byte, across `current` + `.1`); no lost line (the union of
`(proc, seq)` pairs across both surviving files equals the full expected 120-pair set);
at most cap+slack bytes (`current` stays within `max_bytes` + 4 lines' worth of slack).
Re-run 8x consecutively — deterministically green every time (`0.34s`-`0.53s` per run).

**RED -> GREEN:** every wiring test (`test_latency_log_rotates_at_the_shared_cap`,
`test_reconciler_flag_rotates_the_shared_events_log`,
`test_reap_event_rotates_the_shared_events_log`, `test_ledger_rotates_at_the_shared_cap`)
confirmed RED (`AssertionError: assert False` — no `.1` file existed) against a
pre-seeded oversized log BEFORE the corresponding writer was wired through the helper,
GREEN immediately after. The 9 helper-level unit tests and the concurrency fixture were
authored RED-first against the not-yet-existing `infrastructure/jsonl_log_rotation`
module (`ImportError`), GREEN once it existed. `test_failed_ledger_append_leaves_
handoff_in_place` (T-043-39, unmodified — the ledger-path-is-a-directory fixture) stays
green through the rewiring, proving A24.4's fail-open contract survived intact.

Full gate (live, this session): `ruff format --check .` / `ruff check --no-cache .`
clean; `mypy --strict dadaia_workspace/` — 267 source files (+1), no issues; `pytest -p
no:cacheprovider -m 'not quarantine' -n auto` — 2512 passed, 3 skipped, 0 failed (was
2498 passed pre-change, +14 net new); `dadaia doctor` — all invariants OK; `dadaia ci
preflight --quick` — 5/5 PASS; `pytest tests/integration/test_repo_self_scan.py` — 5
passed. `ruff check --select C901 --preview` clean at the pinned `max-complexity = 63`
ceiling; highest new-function complexity (`--config lint.mccabe.max-complexity=1`
probe): `_acquire` ~6, `_rotate_and_append`/`append_rotating_jsonl` ~4, everything else
2-4 — no ratchet touched. LOC delta (`git diff --numstat`): one new production module
(178 lines, `infrastructure/jsonl_log_rotation.py`) + production edits +87/-55 across
`core/kernel_tunables.py` (+11/-1), `features/chokepoints/service.py` (+23/-15),
`hooks/pre_gate.py` (+8/-6), `hooks/sdd_post_gate.py` (+39/-33), `setup.cfg` (+6/-0) +
two new test files (300 lines: 184 unit + 116 integration) + test edits +126/-2 across
five existing test files.

---

- [x] **T-043-43 — FR28: the cache must not be born**

**Owner role:** software-engineer · **Commit:** `feat(T-043-43): block cache-enabling mypy/pytest/ruff invocations`

**Preconditions:** T-043-42 `[x]`. **Write set:** `hooks/venv_guard.py` + tests.

**Description:** Block `mypy`/`pytest`/`ruff` Bash invocations that would run with caching
enabled; the block message carries the corrected command, matching the existing venv-guard
contract. Token-matched on fixed leading tokens — **no shell parsing**.

**Done criterion:** A28.1–A28.3 hold; no false block on an unrelated command.

**Parallelism:** none.

**Design.** A second, orthogonal rule (`_cache_guard_reason`) added to the existing
venv-guard policy (one Bash PreToolUse slot, one call site — no new hook, no new module,
matching the write-set constraint). Recognition (`_cache_tool_name`) reuses the file's own
fixed-leading-token/venv-rooted-token discipline: the bare name `pytest`/`ruff`/`mypy`, or
a token rooted in `.dadaia/.venv/bin/` (or its workspace-absolute equivalent) whose
basename matches. Evaluated BEFORE rule 1's "already venv-rooted → ALLOW" shortcut, so a
venv-rooted-but-cache-enabling invocation is still caught. Per-tool detection (flag
presence scanning on the full `shlex.split` args, never general shell parsing — A28.3):
`pytest` requires the adjacent pair `-p no:cacheprovider`; `ruff check`/`ruff format`
require `--no-cache` (every other ruff subcommand — `--version`, `rule`, `config`,
`linter` — is out of scope, never blocked, since only `check`/`format` write
`.ruff_cache/`); `mypy` requires `--cache-dir` (bare or `--cache-dir=PATH`) present
anywhere — presence-only, per A28.3's letter (the guard cannot resolve or judge the
destination path without a shell parser; `pyproject.toml`'s own `[tool.mypy]` comment
already documents that `incremental = false` alone does NOT stop `.mypy_cache/` creation).
Corrected commands are built via `shlex.join` on the args list with the missing flag(s)
spliced in — verified against the real installed tools (not just asserted): `ruff
--no-cache check .` is REJECTED by ruff itself (`--no-cache` is a `check`/`format`-scoped
flag, not global — `error: unexpected argument '--no-cache' found`), so the ruff
correction splices `--no-cache` in right after the subcommand token, never before it;
`ruff check --no-cache …`, `ruff format --no-cache --check …`, `mypy --strict … --cache-dir
X`, and `pytest -p no:cacheprovider …` were each confirmed to actually run clean against
the real venv binaries. Deliberately OUT of scope (documented in the module docstring,
not a silent gap): `python -m pytest`/`python -m ruff`/`python -m mypy` forms — only
`python -m dadaia_workspace` is special-cased (rule 1); extending module-invocation
matching to three more modules widens the false-block surface with no evidence any agent
here invokes them that way, and a miss there fails OPEN (ALLOW), never closed.

**False-positive fixtures (A28.2/A28.3 — the "never brick the workspace" requirement).**
31 new negative-space fixtures across two matrices in `tests/unit/hooks/test_venv_guard.py`:
(1) an ALLOW matrix of 19 REAL compliant invocations mirroring `dadaia ci preflight`'s own
argv construction (`features/ci_preflight/service.py:_lint_type_checks/_pytest_check`) and
DADAIA.md §6's documented gate commands — bare, venv-rooted-relative, and
workspace-absolute forms of all three tools, `--cache-dir=PATH` long-option form, and 4
ruff subcommands that never write a cache; (2) a no-false-block matrix of 12 rows: a
command that merely CONTAINS a tool name in a quoted string or another command's argument
(`git commit -m "fix pytest issue"`, `echo ruff`, `grep -r "pytest" repos/`), an in-repo
path ending in the name (`cat repos/x/mypy_notes.txt`), a similarly-named-but-different
tool (`pytest-watch`, `mypyc build`, `./scripts/pytest-runner.sh`), and a foreign venv's
own pytest/ruff/mypy (`repos/other/.venv/bin/pytest`) — same false-block discipline as
rule 1's pre-existing foreign-venv exemption.

**RED → GREEN.** The 11 new `test_blocks_cache_enabling_invocation` rows were run against
the pre-change `venv_guard.py` (git-show'd from `HEAD`, restored after) BEFORE the
production code existed: all 11 failed (`assert None is not None`), the other 70
rows in the same file already passed unchanged (proving they exercise the untouched rule
1 / pre-existing behavior, not the new logic) — 11 failed, 70 passed. Production code
restored, full file re-run: 81 passed. Three pre-existing ALLOW-matrix rows
(`"ruff check ."`, `"ruff format --check"`, `"mypy --strict dadaia_workspace"`) were
updated to their now-required compliant forms in the same commit — they would otherwise
have flipped to BLOCK under the new rule (module docstring's own worked-through
narrowness reasoning documents why this is intended, not a regression).

**Full gate (live, this session):** `ruff format --check --no-cache .` /
`ruff check --no-cache .` clean; `mypy --strict --cache-dir <out-of-repo> dadaia_workspace/`
— 267 source files, no issues; `pytest -p no:cacheprovider -m 'not quarantine' -n auto` —
2554 passed, 3 skipped, 0 failed (was 2512 passed pre-change, +42 net new); `dadaia doctor`
— all invariants OK; `dadaia ci preflight` — 5/5 PASS (re-run in isolation after an
initial concurrent-background-load false failure on two independently-documented
load-sensitive wall-clock-bound subprocess tests — `test_full_handoff_emit_and_validate`
and `test_codex_live_probe_exercises_the_real_installed_codex`, neither touching
`venv_guard.py` or any cache flag — confirmed unrelated by re-running alone, green);
`pytest tests/integration/test_repo_self_scan.py` — 5 passed (the new
`/home/<user>/ws/.dadaia/.venv/bin/…` fixture rows land in the SAME file/pattern baseline row
already on the shrink-only allowlist — no new row needed, set-membership is per
`(path, pattern_id)`, not per-occurrence). `ruff check --select C901 --preview
--config lint.mccabe.max-complexity=63` clean at the pinned ceiling; AST-walk
approximation (`--config lint.mccabe.max-complexity=1` probe) of the new/changed
functions: `_cache_guard_reason` ~11 (the highest new function), `evaluate_payload` ~11
(pre-existing, +1 branch for the new early cache-guard call), `_cache_tool_name` ~4,
`_first_token` ~3 (pre-existing, unchanged) — all well under the 63 ceiling, no ratchet
touched. LOC delta (`git diff --numstat`): `dadaia_workspace/hooks/venv_guard.py` +174/-8
(docstring rewrite + 8 new helper functions); `tests/unit/hooks/test_venv_guard.py`
+160/-12 (3 ALLOW-row updates + 3 new parametrized matrices: 11 BLOCK rows, 19 ALLOW rows,
11 no-false-block rows). Worktree clean after this commit (write set exactly the two
files above, per the task's declared scope).

---

- [x] **T-043-44 — FR29: `dadaia tmp gc`, the orphan backstop**

**Owner role:** software-engineer · **Commit:** `feat(T-043-44): add the dadaia tmp gc orphan backstop`

**Preconditions:** T-043-43 `[x]`. **Write set:** the new CLI verb + its wiring + tests.

**Description:** The **only** calendar-based deletion in the release: dated scratch older
than 3 days, any `*cache*` directory under `.dadaia`, orphaned session markers. Idempotent,
`SessionStart`-safe, with a dry-run mode.

**Done criterion:** A29.1–A29.4 hold, **and AG.1 holds for this deletion lane** — the
calendar backstop resolves every target, refuses anything outside `.dadaia/`, and never
follows a symlinked directory.

**Parallelism:** none.

**Design.** A new `features/tmp_gc/service.py` (pure, no `hooks`/`infrastructure` import —
`features` must not import `hooks`, so the two small AG.1/marker-prefix idioms it needs
are duplicated locally from `features.chokepoints.service`/`hooks.sdd_post_gate`, the
segment's own established precedents, rather than reaching across a layer boundary) plus a
thin `cli/commands/tmp.py` Typer verb (`dadaia tmp gc [--dry-run]`, default REAL/
destructive — `--dry-run` opts into the safe preview, matching "SessionStart-safe" meaning
"safe to run for real unattended", not "safe only in preview"). One shared 3-day age
constant (`_MAX_AGE_DAYS`) drives two of the three lanes: (a) dated scratch —
`tmp/<agent>/<YYYYMMDD>/` directories whose OWN embedded calendar date (never mtime) is
more than 3 days before now; a name that fails `^\d{8}$` or is not a real calendar date is
never a candidate (A29.2 "non-dated path"); (b) cache directories — any directory anywhere
under `.dadaia` whose name contains `cache` (case-insensitive), unconditional on age,
excluding the managed `.venv` and the PROTECTED `sessions` store; (c) orphaned session
markers — `reconciler-last-*`/`ctx-inject-fired-*` (the same two prefixes
`hooks.sdd_post_gate` owns) with no `.dadaia/sessions/<sid>.json` record AND older than 3
days by mtime — the mtime floor is what makes unattended `SessionStart` invocation safe: a
session that has not yet written its own record has markers too young to qualify, so it can
never sweep its own bootstrap evidence. AG.1 lane guard (`_resolved_within` + symlink
exclusion in every directory walk/listing) applied uniformly before every deletion,
mirroring `features.chokepoints.service`/`hooks.sdd_post_gate` byte-for-byte in intent.
Idempotent by construction — no separate "already processed" state; every lane re-derives
its candidate set from the filesystem each call, so a deleted target is simply absent next
time (A29.1).

**RED → GREEN.** 22 new tests written first against the not-yet-existing module
(`ModuleNotFoundError: No module named 'dadaia_workspace.features.tmp_gc.service'` —
collection-time RED, the real reason) — `tests/unit/features/tmp_gc/test_tmp_gc_service.py`
(17: age-boundary trio at 2/3/4 days, non-dated-path protection, cache sweep incl. nested-
inside-a-surviving-dated-dir and the managed-venv/sessions-store exclusion, orphan-vs-owned
markers incl. the fresh-orphan SessionStart-safety fixture, dry-run across all three lanes,
idempotent second real run, two AG.1 lane-guard fixtures — never-follow-a-symlinked-
directory and refuse-a-target-resolving-outside-`.dadaia/`, mirroring both
`test_push_verdict_gc.py`'s and `test_post_gate_reap.py`'s fixture shapes — plus a third
AG.1 fixture for the cache lane's own symlinked-directory exclusion, and a best-effort
unlink-failure-does-not-abort-other-lanes fixture) + `tests/unit/cli/commands/
test_tmp_gc_cmd.py` (5: dry-run prints without deleting, real run deletes, the "nothing to
reclaim" clean message, the A29.4 help-text doctrine check, and an end-to-end owned-marker
survival sanity check through the full CLI). Implementation written to green; all 22 pass
on the first post-implementation run (no red-herring iterations after the module existed).

**Real-workspace dry-run evidence (A29.3, safe-only per the task brief — destructive form
never run against the real workspace).** `dadaia tmp gc --dry-run` against this workspace's
own live `.dadaia/` reported **10 item(s)**, all in the `cache directories` lane
(`tmp/ai-engineer/20260817/mypy-cache`, `tmp/ci-preflight/mypy-cache`, four
`tmp/software-engineer/**mypy*cache*` entries from this and earlier same-day sessions, and
two `mypy-cache-t04344*` directories this very session's own out-of-repo `mypy --strict
--cache-dir` invocations created under `tmp/software-engineer/20260818/`) — the honest
self-inclusion is expected, not a bug: this task's own mypy cache dirs are exactly the kind
of thing lane (b) exists to sweep. **Zero** items in the `dated scratch` or `orphaned
session markers` lanes: every dated dir under `tmp/` on this real workspace is 1-2 days old
(within the 3-day floor), and every `reconciler-last-*`/`ctx-inject-fired-*` marker present
either has a live owning session record or is minutes-to-hours old — confirming the task
brief's prediction that the 3-day threshold protects this release's own `.dadaia/tmp`
CLOSURE-evidence captures.

**Full gate (live, this session).** `ruff format --check --no-cache .` — 864 files already
formatted; `ruff check --no-cache .` clean; `mypy --strict --cache-dir <out-of-repo>
dadaia_workspace/` — 270 source files, no issues; `pytest -p no:cacheprovider -m 'not
quarantine' -n auto` — 2576 passed, 3 skipped, 0 failed (was 2554 pre-change, +22 net new,
matching the 22 new tests exactly — zero incidental churn elsewhere); `dadaia doctor` — all
invariants OK; `dadaia ci preflight` — 5/5 PASS (ruff format-check, ruff check, mypy
--strict, lint-imports, pytest); `pytest tests/integration/test_repo_self_scan.py` — 5
passed. `ruff check --select C901 --preview --config lint.mccabe.max-complexity=63` clean
at the pinned ceiling; AST-walk approximation (`--config lint.mccabe.max-complexity=1`
probe) of the new functions: `_orphan_marker_candidates` ~9 (the highest new function),
`_cache_candidates` ~8, `_scratch_candidates` ~7, `_apply_lane` ~5, `_remove` ~4, `gc`
(CLI) ~6, `_resolved_within`/`_relpath`/`_sorted_real_subdirs` ~2, `_print_lane` ~3 — all
well under the 63 ceiling, no ratchet touched. A pre-existing, unrelated
`test_architecture_diagrams_present_and_match_live_names` regression (this task's own new
`features/tmp_gc` package not yet diagrammed) was fixed in the same commit by adding one
`tmp_gc["tmp_gc"]` node to `specs/assets/architecture/feature-packages.md` — the
introspection drift-guard's forward check, no reverse/stale check exists for this
particular diagram so the pre-existing stale `ai_surface`/`lifecycle`/`workflows` nodes
were left untouched (out of this task's scope). A second, genuinely pre-existing and
unrelated `test_repo_self_scan.py` failure (T-043-43's own evidence prose quoting a literal
`/home/<redacted>/…` fixture path, tripping the shrink-only baseline's `home-abs-path`
pattern) was found while running the full gate, confirmed pre-existing via `git stash`
before any T-043-44 code existed, registered as bug
`self-scan-baseline-drift-t04343-evidence-prose`, root-cause fixed (one-line redaction in
this same file, two commits prior in this session) and the bug closed with resolution
evidence in the same session — full Arm B, off this task's own write set.

LOC delta (`git diff --numstat`, this task's write set only):
`dadaia_workspace/features/tmp_gc/__init__.py` +11/-0;
`dadaia_workspace/features/tmp_gc/service.py` +313/-0;
`dadaia_workspace/cli/commands/tmp.py` +72/-0; `dadaia_workspace/cli/main.py` +2/-0;
`specs/assets/architecture/feature-packages.md` +1/-0;
`tests/unit/features/tmp_gc/test_tmp_gc_service.py` +351/-0;
`tests/unit/features/tmp_gc/__init__.py` +0/-0;
`tests/unit/cli/commands/test_tmp_gc_cmd.py` +112/-0 — total +862/-0. Worktree clean after
this commit (write set exactly the eight files above, per the task's declared scope; the
two-commit self-scan bug fix was staged and committed separately, before this commit, per
its own out-of-scope root cause).

---

- [x] **T-043-45 — `alpha-5` close: `qa-engineer` review**

**Owner role:** qa-engineer · **Commit:** `test(T-043-45): alpha-5 qa review`

**Preconditions:** T-043-38 … T-043-44 all `[x]`. **Write set:** the QA artifact + handoff.

**Description:** Verify every `alpha-5` acceptance id and the fail-open posture of each
capability that rides a hook. **AG.1 is verified per deletion lane** (FR23, FR24, FR25,
FR26, FR29) — one lane-guard fixture each, none accepted by inspection. The artifact names
the GC surface `alpha-6`'s consumer round must exercise (feeds A30.6).

**Done criterion:** PLAN §5 `alpha-5` exit criteria met; V10 recorded.

**Evidence:** `specs/releases/v0.4.3/ALPHA-5-QA.md` — **APPROVED**. All 23 in-scope
acceptance ids (A23.1–A23.3, A24.1–A24.4, A25.1, A25.3, A26.1–A26.3, A27.1–A27.3,
A28.1–A28.3, A29.1–A29.4) PASS with live-tree evidence. AG.1 verified per lane: the two
doc-only lanes (FR23, FR25) by reading the stated skill text, the three code lanes (FR24,
FR26, FR29) by running all 7 lane-guard fixtures live (`test_lane_guard_*`, 7 passed).
Fail-open posture of every hook-riding capability (reconciler reap, log rotation, cache
guard, `pre_gate` latency) cited with a live-run fixture each (8 passed). V10 confirmed on
disk and coherent (`.dadaia/tmp/software-engineer/20260817/v0.4.3-T-043-41-v10-reconciler-reap.md`).
Full targeted alpha-5 code-lane suite: 147 passed (incl. `test_repo_self_scan.py` 5/5).
Live `dadaia tmp gc --dry-run`: 10 items, all cache-lane, zero scratch/marker items.
Bug ledger: `dadaia bugs status` → 0 open (segment's one Arm-B rider,
`self-scan-baseline-drift-t04343-evidence-prose`, fully closed). One decision routed to
`project-manager`: T-043-39's `gc_consumed_push_verdicts` is a correct, tested pure
action function with no live push-path caller yet — A24.x hold at the function-contract
level; the live-wiring gap is named, not absorbed, and routed to the `rc-1` CLOSURE
memory window + operator/PM backlog intake (never an `alpha-5` blocker). GC surface for
`alpha-6`'s consumer round (A30.6) named concretely in §6.3 of the artifact. Full suite
2576 passed/3 skipped/0 failed; `dadaia ci preflight` 5/5; `dadaia doctor`/`specs
doctor`/`public doctor` all green (0 errors).

**Parallelism:** none.

---

## `alpha-6` — WS-F, consumer round and published lineage (R10: last)

- [x] **T-043-46 — FR30a: run the consumer round on a throwaway real workspace**

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

**Evidence:** Round artifact:
`.dadaia/tmp/qa-engineer/20260818/v0.4.3-T-043-46-consumer-round.md`. Throwaway workspace
created via the supported editable-install path (a runner venv `pip install -e` the
`feature/0.4.3` tree, then `dadaia init --workspace <path> --harness all` from that
runner, so the throwaway's own `.dadaia/.venv` self-hosts the same editable checkout —
confirmed via `direct_url.json` and `dadaia --version` → `0.4.2` matching
`pyproject.toml`). Tested tree tip at reservation `5495fd16`; final tip `8ca8ac41` (adds
the one bug this round registered). A30.1–A30.3 (the three inherited criteria) PASS with
live evidence (skill-verb cross-check against `dadaia --help`; a fresh consumer context's
marker-discipline + schema-coherence cycle proving both SPEC-DOC-004/024 fire correctly
and fold to 0/0; the pre-v0.12.0 loose-backlog-file scenario reproducing the exact
SPEC-DOC-035-WARN-count == loose-file-count / backlog-doctor-clean split, then folding to
a clean two-doctor state after migration). A30.4 environment limits recorded honestly (4
items, none silently absorbed). A30.6: 5 of 7 `ALPHA-5-QA.md` §6.3 GC touchpoints
live-exercised with evidence (ack-on-consume, reconciler reap, log rotation, cache guard,
`dadaia tmp gc` dry-run+destructive); 2 explicitly recorded not-exercisable exactly as
§6.1/§6.3 pre-warned (push-verdict GC — no live caller yet; release-closure sweep — out
of the round's scope). One finding registered as a bug
(`ancestor-walk-workspace-root-silent-mistarget`, HIGH — `dadaia init`'s bare-invocation
ancestor-walk and `dadaia reports validate`'s lack of a `--workspace` override both
silently mistarget an ancestor workspace's root with no diagnostic; discovered live
during setup and during the ack-on-consume exercise), routed to T-043-47 for the
segment's budgeted remediation cycle. Self-scan
(`tests/integration/test_repo_self_scan.py`) 5/5 passed before this commit. Worktree
clean.

**Parallelism:** none.

---

- [x] **T-043-47 — FR30b: spend (or explicitly not spend) the remediation cycle**

**Owner role:** software-engineer / ai-engineer as the finding requires · **Commit:**
`fix(T-043-47): remediate the consumer round's findings`

**Preconditions:** T-043-46 `[x]`.

**Write set:** determined by the findings; declared before the work starts.

**Description:** One budgeted remediation cycle **inside** this segment. A finding too large
to absorb is escalated to the operator **at the moment of discovery** for a ratified
exception — never carried silently to the closure.

**Done criterion:** A30.5 holds; if unused, the task records "no finding required remediation".

**Evidence:** Spent — one finding (F-1, bug
`ancestor-walk-workspace-root-silent-mistarget`, HIGH), root-caused within this
segment's budget, `resolved` event appended.

Root cause (shared by both reproductions): the bare (`--workspace`-less)
`resolve_workspace_root_for_init` ancestor-walk never distinguished cwd nested INSIDE
an ancestor's own `.dadaia/` tree (the R7-sanctioned throwaway-workspace pattern) from
a sub-repo that merely carries a sibling `.dadaia/`, so it silently walked past the
former and returned the wrong ancestor; `reports validate` had no way to target a
workspace other than the one its cwd-based ancestor-walk resolved.

Fix (both surfaces): (a) `dadaia_workspace/core/workspace_resolver.py` —
`resolve_workspace_root_for_init` now detects the `.dadaia/`-nesting boundary and
returns cwd directly instead of crossing it (root-caused the resolution policy, not a
print-more patch); `dadaia_workspace/cli/commands/init.py` adds a loud stderr
diagnostic naming cwd and the resolved root for the one remaining legitimate
ancestor-walk shape (a sentinel-less sub-repo). (b) `dadaia_workspace/cli/commands/
reports.py` — `validate` gains a `--workspace`/`-w` override (same explicit-first
precedence already established for `dadaia init --workspace` and context resolution)
and always emits the resolved workspace root to stderr, never polluting `--json`'s
stdout list shape, so a false `INVALID`/`missing_artifact` is never misread.

RED before fix, GREEN after: `tests/unit/core/test_workspace_resolver.py::
test_bare_init_nested_inside_ancestor_dotdadaia_targets_cwd_not_ancestor`,
`::test_bare_init_nested_one_level_inside_dotdadaia_targets_cwd`,
`::test_bare_init_sub_repo_not_inside_dotdadaia_still_walks_up` (non-regression);
`tests/integration/test_cli_init.py::
test_bare_init_nested_inside_ancestor_dotdadaia_targets_cwd`;
`tests/contract/cli/test_cli_reports.py::
test_reports_validate_workspace_override_fixes_false_invalid`,
`::test_reports_validate_always_emits_resolved_workspace_root_json_mode`. Full suite:
2582 passed / 3 skipped / 0 failed (`-p no:cacheprovider -m 'not quarantine' -n auto`,
+6 over T-043-46's 2576 baseline). `ruff format --check --no-cache` / `ruff check
--no-cache` clean; `mypy --strict` clean (270 source files); `dadaia ci preflight` 5/5
PASS; `dadaia doctor` healthy; `specs doctor` 0 errors (5 pre-existing unrelated
legacy warnings). Bug ledger: `dadaia bugs status` → 0 open. Worktree clean after
commit.

**Parallelism:** none.

---

- [x] **T-043-48 — FR31: backfill the CHANGELOG in the minimal honest form**

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

- [x] **T-043-49 — `alpha-6` close: `qa-engineer` review**

**Owner role:** qa-engineer · **Commit:** `test(T-043-49): alpha-6 qa review`

**Preconditions:** T-043-46 … T-043-48 all `[x]`. **Write set:** the QA artifact + handoff.

**Done criterion:** PLAN §5 `alpha-6` exit criteria met; the recorded environment limits and
the GC coverage statement are carried forward for CLOSURE.

**Evidence:** `specs/releases/v0.4.3/ALPHA-6-QA.md` — **APPROVED**. All 10 in-scope
acceptance ids (A30.1–A30.6, A31.1–A31.4) PASS, independently re-verified against the live
tree. A30.5's bug (`ancestor-walk-workspace-root-silent-mistarget`) re-verified with all 6
RED-then-GREEN reproducing/regression tests re-run live (6 passed). A30.6's GC-coverage
table cross-checked against `ALPHA-5-QA.md` §6.3's own pre-named 7-touchpoint list — exact
match, 5 exercised / 2 not-exercisable for the pre-warned reasons. A31 CHANGELOG backfill:
4 of 10 retroactive sections spot-checked commit-by-commit against `git log` on their own
stated ranges (exceeds the required 3) — exact sha/count/subject match in all 4; 3
unpublished-internal annotations present and correctly worded; `e2eb28f8..e323ed9f` diff
confirmed additions-only (138 insertions, 0 deletions). Bug ledger: `dadaia bugs status` →
0 open. Full suite 2582 passed / 3 skipped / 0 failed (unchanged from T-043-47's baseline);
`dadaia ci preflight` 5/5 PASS; `dadaia doctor` healthy; `specs doctor` 0 errors / 5
pre-existing unrelated warnings (same as `alpha-5`'s baseline); `public doctor` all `[ok]`.
A30.4 environment limits and the A30.6 GC coverage statement carried forward verbatim in
the artifact's §6 for T-043-51/52. `tests/integration/test_repo_self_scan.py` 5/5 passed
before this commit. Worktree clean.

**Parallelism:** none.

---

## `rc-1` — review → memory → closure → archive → ship

- [x] **T-043-50 — Six-axis code review on a thawed tree**

**Evidence:** APPROVED at `6ba60c48` — 0 CRITICAL/HIGH; 1 MEDIUM (M-1, FR24 wiring — resolved
in-release by the ship-flow CLI wiring rider), 3 LOW (L-1/L-2/L-3, folded into the
T-043-51/52 authoring pass as CLOSURE-accuracy items), 3 INFO record-only. A32.1–A32.4
verified (A32.3 with the documented net-down cap arithmetic). Review committed as
`PRE-PR-REVIEW.md`; handoff `2026-08-18T014638Z-code-reviewer-T-043-50-six-axis`.
Suite 2582/0 failed; preflight 5/5; lint-imports 9/9 contracts.

**Owner role:** code-reviewer · **Commit:** `docs(T-043-50): pre-PR six-axis review`

**Preconditions:** T-043-49 `[x]`. **Write set:** the review artifact + handoff.

**Description:** Review the whole release delta **before** the archive move (D8/FR5), so any
finding lands on a thawed tree and is fixed in place. An actionable finding returns to its
owning lane and is fixed here — it never becomes intake demand (residual budget).

**Done criterion:** APPROVED `code-reviewer` artifact; A32.1–A32.4 verified.

**Parallelism:** none.

---

- [x] **T-043-51 — [phase] Memory window: one authoring pass per atom**

**Evidence:** 13 atoms + `.heading-allowlist` (22 entries: all 20 V3 headings as 19 unique
lines + the governance heading + 2 corrected forms) authored by `product-engineer` in one
pass each; catalog + index regenerated by the dispatcher. PE-2 (version parenthetical
dropped), L-2 (`tests/e2e/**`-only scope stated), L-3 (census re-pinned at measured 100),
harness-codex version-qualified rewrite, FR24 recorded wired-via-`dadaia ci
gc-push-verdicts` — all folded. `specs doctor`: **0 memory errors, 0 LINT-1 warnings**
(A13.4); sole remaining error is `SPEC-DOC-024`, the structural transient of the rc-1
phase ladder itself (its own tasks complete during CLOSURE), clearing at the T-043-52
archive. Six overlong `tldr` values compressed to the 160 cap in the same window.

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

- [x] **T-043-52 — [phase] CLOSURE, disposition sweep, archive**

**Evidence:** CLOSURE.md authored (`**Status:** Aprovado`) with the 24-line disposition
sweep (23 DELIVERED + 1 SUPERSEDED, mirrored into the BACKLOG LEDGER), 10 Arm-B riders
Closed, the demotion map, the V12 Size-accounting table, the executed FR25 artifact GC
sweep (43 handoffs + 24 tmp items + all cache dirs deleted under the AG.1 lane guard,
zero refusals), Record-only observations, and an **empty** Intake candidates section
(A32.5). ACTIVE.md reset to `release: none`; archive by `git mv` in this commit.

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
