# TASKS — Release v0.4.5 — hardening and consolidation

**Status:** Aprovado
**Release ID:** v0.4.5
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.4.5/SPEC.md`
**Source PLAN:** `specs/releases/v0.4.5/PLAN.md`
**Branch:** `feature/0.4.5` (cut from `main` at the shipped v0.4.4)
**Segments:** `S1 … S4` — internal work boundaries on `feature/0.4.5`, each closed by a
`qa-engineer` review **committed on the branch**: no merge, no PR, no `rc` burned (SPEC D8).
**Candidates:** `rc-1 … rc-N`. `rc-1` burns when the **whole** scope is implemented,
validated, gate-green and closed by QA, and is merged into `develop`; `rc-2 … rc-N` are
adjustment rounds on that same scope found by testing the merged `develop`; the **final
`rc`** carries memory → CLOSURE → archive and ships **without publishing** (O5). If nothing
is found, the final `rc` **is** `rc-1`.

This file is the single marker surface for all of it (D1); the blocks below are the
segments and the lane. `ACTIVE.md` carries no `segment:` line.

## Task status markers

- `[ ]` OPEN · `[-]` IN PROGRESS · `[x]` DONE

## Segment and candidate map

**Ids are in execution order** — nothing below runs out of numeric sequence.

| Block | Tasks | Contents | Gate |
|---|---|---|---|
| W0 | T-045-01 … 03 | definition commit + milestone (a) definition PR + the operator-only required-checks wiring | definition PR merged into `develop`; APPROVED verdict on its head sha |
| `S1` | T-045-04 … 10 | the open-bug sweep — FR1 (two MEDIUM bugs, one cause) then four Arm-B items | `qa-engineer` review **committed** |
| `S2` | T-045-11 … 18 | structural consolidation (FR2–FR5) | `qa-engineer` review committed + `software-architect` **AR-1** ruling |
| `S3` | T-045-19 … 24 | gate, doctor and seam hardening (FR6–FR10) | `qa-engineer` review committed |
| `S4` | T-045-25 … 31 | the token-economy program (FR11–FR15) | `qa-engineer` review committed |
| scope complete | T-045-32 … 34 | invariants measured → six-axis review → security review + QA release verdict | the trio APPROVED on the same commit |
| `rc-1` | T-045-35 | PR `feature/0.4.5` → `develop` | merged, CI green |
| `rc-2 … rc-N` | T-045-36 | adjustment rounds on this scope | one QA close + one merge per round |
| final `rc` | T-045-37 … 41 | memory → CLOSURE → archive → version bump + merge → **ship without publish** | full trio still green, then the PR to `main` |

Order across the lane is fixed: **review → closure → archive → ship**. The six-axis review
runs on a **thawed** tree, before `rc-1` and again over any later `rc` delta — always before
the archive move.

## Standing rules for this release

- **`product-engineer` has no shell.** Every task marked **[git]**, **[shell]** or
  **[operator]** is executed by the dispatcher, `software-engineer`, `ai-engineer`,
  `qa-engineer` or the operator. `product-engineer` authors text only.
- **Shell-less reservation obligation.** When the dispatcher relays work for a shell-less
  sub-agent it commits that sub-agent's `[ ]`→`[-]` flip **before** relaying the next item —
  never batched. Applies to T-045-37 and T-045-38.
- **Reservation is observable.** Flip `[ ]`→`[-]` and commit `chore(tasks): start <id>`
  before the work (`dadaia-task-manager`). **One `[-]` at a time — this release declares no
  parallel pair.**
- **Green at every commit:** `dadaia ci preflight`, `dadaia backlog doctor`,
  `dadaia specs doctor`, `dadaia public doctor`. **No `--no-verify`, ever.**
- **RED before GREEN**, on the executed path.
- **The standing order is an acceptance.** A diff that adds a branch, a flag, a second code
  path, a cross-feature reach-in or a new side effect is rejected, whatever the test result.
  Every review verdict states the **bug-surface delta** of the feature it touched, with
  bug-history evidence.
- **Deletion needs its net first.** No writer, inventory, golden assertion or persona block
  is deleted before the thing that proves its behaviour survives exists and is green
  (`expand → switch → contract`, SPEC D7).
- **Bug work runs under `dd-bug-fix` and the FR23 evidence gate — law, not release scope.**
  Every `resolved` event carries the three required evidence fields; an empty-evidence
  `resolved` is refused by the CLI.
- **Test intent at birth.** `Intent: CONTRACT — v0.4.5 <A-id>` or `Intent: SENTINEL — <seam>`.
  **Zero new `tests/e2e/**`** without a named `qa-engineer` exception in that segment's QA
  artifact.
- **Never prune to go green.** A deletion, skip or disable is a `qa-engineer` verdict with
  evidence, executed by `software-engineer`.
- **Lane discipline.** `ai-engineer` performs every skill/persona/rule/projected-asset edit;
  `software-engineer` every production-code, CI-YAML and test edit; `project-manager` any
  backlog-file mechanics; `product-engineer` only specs and memory.
- **No new scope in an `rc`.** An `rc-N ≥ 2` carries only fixes and adjustments **on this
  release's scope** (SPEC A16.7, R-7).
- **A completed task group is one commit** — stage exactly the task's write set, never `-A`.
- **No home-absolute path, operator email literal or denylisted term** enters any authored
  file, including review and QA artifacts. Self-scan before every commit.
- **Measurements** (V1–V12, PLAN §5) are captured under `.dadaia/tmp/<agent>/<YYYYMMDD>/`.

## Acceptance and evidence map

| Task | FR / bug | Acceptance ids | Evidence |
|---|---|---|---|
| T-045-01 | — | — | definition commit sha; `ACTIVE.md` `DEFINITION`; 14 subsections purged; `superseded` event |
| T-045-02 | — | SPEC §7 | V1 + V2 capture; definition PR merged; APPROVED verdict on the head sha |
| T-045-03 | — | D-7 | screenshot/JSON of the required-checks list on both edges |
| T-045-04 | FR1 / 2 MEDIUM bugs | A1.1–A1.6 | RED-then-GREEN on both executed paths; manifest-enumerating contract test; two `resolved` events |
| T-045-05 | FR1 | D-3, A1.3 | venv reinstall output; V3 refusal probe (both directions) |
| T-045-06 | bug `dadaia-task-manager-stale-workspace-protocol-citation` | — | source diff + projection; citation check green; `resolved` event |
| T-045-07 | bug `certify-skip-detail-leaks-full-codex-output` | — | RED-then-GREEN; redaction-helper routing; `resolved` event |
| T-045-08 | bug `codex-probe-unit-fixture-carries-real-session-uuid` | — | fixture diff; self-scan clean; `resolved` event |
| T-045-09 | bug `windows-xdist-workers-crash-on-unit-fast-tier` | AS-5 | root cause + RED-then-GREEN **or** the evidenced negative + QA quarantine verdict; bug stays open if unpicked |
| T-045-10 | all `S1` | A1.x + bug ids | `qa-engineer` artifact committed |
| T-045-11 | FR2 / AR-1 | A2.1 | `software-architect` ruling, verbatim |
| T-045-12 | FR2 (expand) | A2.3, A2.5 | the primitive; battery re-pointed and green on every parameter combination |
| T-045-13 | FR2 (switch) | A2.5 | 11 call sites migrated; `lint-imports` green, no new accepted edge |
| T-045-14 | FR2 (contract) + superseded bug | A2.2, A2.4, A2.6, A2.7 | V4 census; deleted writers; deleted characterization test; `Closed` + `superseded_by` |
| T-045-15 | FR3 | A3.1–A3.3 | executed add-an-asset fixture; goldens carry no inventory |
| T-045-16 | FR4 | A4.1–A4.4 | executed rename fixture; three inventories deleted |
| T-045-17 | FR5 | A5.1–A5.3 | scan census; three mis-rooted-walker RED proofs |
| T-045-18 | all `S2` | A2–A5 ids | `qa-engineer` artifact committed + the AR-1 ruling referenced; V5 |
| T-045-19 | FR6 | A6.1–A6.5 | RED-then-GREEN; single-loader grep; `public doctor` `[ok] public-privacy` |
| T-045-20 | FR7 + MEDIUM bug | A7.1–A7.5 | RED-then-GREEN on U+2028 and ESC; full live-ledger parse; `resolved` event |
| T-045-21 | FR8 | A8.1–A8.3 | RED-then-GREEN symlink fixture |
| T-045-22 | FR9 | A9.1–A9.3 | the invariant + fixture **or** the recorded rule-out paragraph |
| T-045-23 | FR10 | A10.1–A10.4 | doctor-clean fixture; outside-lifecycle test |
| T-045-24 | all `S3` | A6–A10 ids | `qa-engineer` artifact committed |
| T-045-25 | FR11 (baseline) | A11.1 | V6 + V7 + V8 + V9 capture, before any cut |
| T-045-26 | FR12 | A12.1–A12.4 | V8 re-capture on a real session; `ctx_inject` byte-unchanged |
| T-045-27 | FR11 (pass) | A11.1–A11.4 | V6/V7 re-capture; the coverage table |
| T-045-28 | FR13 | A13.1–A13.4 | V9 re-capture; the coverage table; residuals named |
| T-045-29 | FR14 | A14.1–A14.3 | citation check green at HEAD; `public doctor` green |
| T-045-30 | FR15 | A15.1–A15.3 | zero off-taxonomy declarations, by scan |
| T-045-31 | all `S4` | A11–A15 ids | `qa-engineer` artifact committed |
| T-045-32 | FR16 | A16.1–A16.6 | gate output; V10 + V11 capture |
| T-045-33 | all | A16.1–A16.4 | `code-reviewer` APPROVED on a **thawed** tree, with the bug-surface verdict |
| T-045-34 | all | — | `security-reviewer` APPROVED + `qa-engineer` release verdict |
| T-045-35 | — | — | **`rc-1`**: PR merged; CI green; verdict handoff for the PR head sha |
| T-045-36 | — | A16.7 | **`rc-2 … rc-N`**: per round — the finding on `develop`, its fix, QA close, delta reviews, merge |
| T-045-37 | all | SPEC §5 | memory diff; `specs doctor` 0 errors |
| T-045-38 | all picked | A16.6 + closure obligations | `CLOSURE.md`; sweeps complete; `rc` ledger |
| T-045-39 | — | — | `git mv` archive; `ACTIVE.md` `ARCHIVED` |
| T-045-40 | — | — | `0.4.5` bump + `[0.4.5]`; final-`rc` PR merged; CI green |
| T-045-41 | — | A16.8 | PR to `main` merged; **V12: nothing published**; `feature/0.4.5` deleted; `feature/0.4.6` cut |

---

## W0 — definition

- [x] **T-045-01 — [git] Definition commit**

**Owner role:** dispatcher (+ `project-manager` for the backlog mechanics) · **Commit:**
`docs(specs): v0.4.5 definition — hardening and consolidation (Aprovado)`

**Preconditions:** SPEC, PLAN and TASKS authored and carrying `**Status:** Aprovado`;
working tree on `feature/0.4.5`, cut from `main` at the shipped v0.4.4.

**Write set (staging only — content authored by `product-engineer` / `project-manager`):**
`specs/releases/ACTIVE.md`, `specs/releases/v0.4.5/{SPEC,PLAN,TASKS}.md`,
`specs/backlog/BACKLOG.md` (purge-on-pick: 14 `## ACTIVE` subsections removed, 14
`CONSUMED · v0.4.5` `LEDGER` lines added), `specs/bugs/bugs.jsonl` (the one `superseded`
event).

**Description:** The pick and the SPEC ride **one** commit (`DADAIA.md` §5). `ACTIVE.md`
reads `release: v0.4.5` / `phase: DEFINITION` — the phase advances to `IMPLEMENTATION` in
T-045-02, not here. Append the supersession before committing:
`dadaia bugs append --bug-id two-atomic-writers-leak-temp-file-on-injected-os-replace-failure --event superseded --superseded-by atomic-write-primitive-consolidation`.

**Done criterion:** one commit with exactly those paths; the 14 picked subsections gone from
`## ACTIVE`; `backlog doctor` and `specs doctor` clean.

**Parallelism:** none — first task.

---

- [x] **T-045-02 — [git] Milestone (a): push and open the definition PR → `develop`**

**Owner role:** dispatcher + `security-reviewer` · **Commit:** the `ACTIVE.md` phase flip,
then git refs

**Preconditions:** T-045-01 `[x]`.

**Write set:** `specs/releases/ACTIVE.md` (`DEFINITION` → `IMPLEMENTATION`), then git refs,
the security handoff and the V1/V2 captures.

**Description:** Capture **V1** (`dadaia bugs status` — 8 picked bugs, one already
`superseded`) and **V2** (`specs doctor`, `backlog doctor`). Push `feature/0.4.5` (local CI
preflight + name validation), run a diff-based `security-reviewer` review of the delta, open
the PR to `develop` with the APPROVED verdict covering the PR head sha, watch CI to green,
merge. This is the definition PR named by `DADAIA.md` §4 — it **burns no `rc`**.

**Done criterion:** V1 and V2 captured and consistent with SPEC §7; definition PR merged;
CI green; `ACTIVE.md` reads `IMPLEMENTATION`.

**Parallelism:** none.

---

- [ ] **T-045-03 — [operator] Wire the verdict-gate required check on both PR edges**

**Owner role:** operator (GitHub settings; the dispatcher surfaces the exact steps) ·
**Commit:** none — a settings change, recorded in the handoff

**Preconditions:** T-045-02 `[x]`. **Due before the `rc-2` PR** (SPEC D-7).

**Description:** Add the context **"Security verdict gate (PR head sha)"** to the required
checks on **both** the `develop` and `main` PR edges. This is the v0.4.4 intake's item B1 —
deliberately not a backlog entry, scheduled here so it is not lost. Re-supply the
required-checks list **whole**: a PATCH clobbers it.

**Done criterion:** both edges list the context as required, evidenced in the handoff; no
secret, token or org-internal identifier is recorded anywhere.

**Parallelism:** none — it blocks `rc-2`, not the segments.

---

## Segment `S1` — the open-bug sweep

- [ ] **T-045-04 — FR1: the LAW path class decides by origin, not by basename**

**Owner role:** software-engineer · **Commit:** `fix(T-045-04): classify AGENTS.md as LAW by
origin, not by name` · **Lands first in the release** (SPEC D-2).

**Bugs:** `sdd-gate-blocks-fresh-repo-root-agents-md` + `repo-agents-md-law-gate-contradicts-template`
— **one structural cause, per D2.**

**Preconditions:** T-045-02 `[x]`. Read the bug history of the gate feature first
(`dadaia bugs stats` filtered to the gate surface, plus `git log -p` on `gate_policy.py`):
two open bugs on one surface is the standing order's signal.

**Write set:** `dadaia_workspace/features/spec_context/gate_policy.py`,
`dadaia_workspace/public/scaffold/**` (the repo `AGENTS.md` template header),
`tests/**`, `specs/bugs/bugs.jsonl`.

**Description:** RED first, both paths: `Write` of `repos/<fresh-slug>/AGENTS.md` in a
brand-new repo, and `Edit` of an existing non-manifest-tracked `repos/<slug>/AGENTS.md`.
Then the contract test that enumerates `.dadaia/agentic/manifest.json` and pins that every
listed projection **stays** LAW. Only then change the predicate: LAW = the workspace-root law
family **or** a manifest-tracked projection. Correct the scaffold template's wording in the
same commit so the two surfaces never state opposite contracts. **One** predicate carries the
decision — no per-repo exception list, no flag, no second classification path.

**Done criterion:** A1.1–A1.6; the `gate_policy.py` diff is net-negative or flat; two
`resolved` events, each naming the one shared root cause with the three evidence fields.

**Parallelism:** none.

---

- [ ] **T-045-05 — [shell] Install the gate fix and probe it on the executed path**

**Owner role:** software-engineer · **Commit:** the V3 capture reference only

**Preconditions:** T-045-04 `[x]`.

**Write set:** none in the repo — `.dadaia/.venv` and the V3 capture under
`.dadaia/tmp/software-engineer/<YYYYMMDD>/`.

**Description:** Gate code that is not installed is not live (SPEC D-3). Reinstall into
`.dadaia/.venv`, verify with `dadaia --version`, then run **V3** in both directions: a fresh
repo `AGENTS.md` write is allowed, and a manifest-tracked projection is still refused.

**Done criterion:** V3 captured, both directions, on the installed venv.

**Parallelism:** none.

---

- [ ] **T-045-06 — Bug (Arm B): `dadaia-task-manager-stale-workspace-protocol-citation`**

**Owner role:** ai-engineer · **Commit:** `fix(T-045-06): cite DADAIA.md §3 for the gate
description in dadaia-task-manager`

**Preconditions:** T-045-05 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dadaia-task-manager/SKILL.md`, the
projections regenerated by `dadaia public stage && dadaia public install --target all`,
`specs/bugs/bugs.jsonl`.

**Description:** The skill cites `DADAIA.md` §1 for the path-class × presence × phase × mode
description, which lives at §3. Fix at source, re-project. This does **not** pre-empt the
ratified nine-skill `dadaia-task-manager` Update (O3) — that release rebases on this text.

**Done criterion:** the citation check is green at HEAD; `dadaia public doctor` green;
`resolved` event with the three fields.

**Parallelism:** none.

---

- [ ] **T-045-07 — Bug (Arm B): `certify-skip-detail-leaks-full-codex-output` (CWE-532)**

**Owner role:** software-engineer · **Commit:** `fix(T-045-07): certify detail carries only
the parsed error message, redacted and capped`

**Preconditions:** T-045-06 `[x]`.

**Write set:** `dadaia_workspace/features/certification/service.py`, `tests/**`,
`specs/bugs/bugs.jsonl`.

**Description:** RED first: a failing probe embeds the whole captured blob (workdir, session
id) into `certify --json`. Fix at the classifier seam so both the skip branch and the FAIL
branch carry only the parsed `error.message`, length-capped, routed through the existing
redaction helper. No new redaction helper.

**Done criterion:** RED-then-GREEN; no upstream banner line survives in `detail`; `resolved`
event with the three fields.

**Parallelism:** none.

---

- [ ] **T-045-08 — Bug (Arm B): `codex-probe-unit-fixture-carries-real-session-uuid`**

**Owner role:** software-engineer · **Commit:** `fix(T-045-08): synthetic session UUID in
the codex probe fixture`

**Preconditions:** T-045-07 `[x]`.

**Write set:** `tests/unit/features/certification/test_service_codex_live_probe.py`,
`specs/bugs/bugs.jsonl`.

**Description:** Replace the real captured UUID with a synthetic one. Then confirm the
self-scan baseline does not need the old value — a baseline entry that exists only for this
fixture retires in the same commit.

**Done criterion:** no real identifier in the fixture; self-scan clean; `resolved` event.

**Parallelism:** none.

---

- [ ] **T-045-09 — Bug (Arm B, time-boxed): `windows-xdist-workers-crash-on-unit-fast-tier`**

**Owner role:** software-engineer (attempt) + `qa-engineer` (verdict) · **Commit:**
`fix(T-045-09): <root cause>` **or** `test(T-045-09): quarantine <selector> per QA verdict`

**Preconditions:** T-045-08 `[x]`.

**Write set:** `tests/**` and/or `.github/workflows/ci.yml` as the reproduction dictates;
`specs/bugs/bugs.jsonl`.

**Description:** Bounded root-cause attempt on the CI matrix: xdist worker count vs
`windows-latest` runner memory, and the specific test interleaving that killed gw0/gw2 on
otherwise-untouched tests. If a root cause is found, RED-then-GREEN and close it. If the
attempt is inconclusive at the box, **AS-5 applies**: `qa-engineer` issues an
evidence-backed quarantine verdict, `software-engineer` executes it, the bug **stays open**
and is recorded in `CLOSURE.md` as unpicked. A quarantine is never a resolution, and a
quarantined selector always carries its registered bug id.

**Done criterion:** either a `resolved` event with the three fields, or the quarantine
verdict plus the CLOSURE record of the still-open bug.

**Parallelism:** none.

---

- [ ] **T-045-10 — `S1` close: `qa-engineer` review committed on the branch**

**Owner role:** qa-engineer · **Commit:** `docs(T-045-10): S1 QA close`

**Preconditions:** T-045-04 … 09 all `[x]`.

**Write set:** `specs/releases/v0.4.5/reviews/S1-qa-close.md`.

**Description:** Evidence every `S1` acceptance id and every bug disposition. State the
**bug-surface delta of the gate feature** with its bug history — FR1's whole purpose is that
this surface stops producing bugs. No push, no PR, no `rc`.

**Done criterion:** `APPROVE` committed on the branch; no home-absolute path or denylisted
term in the artifact.

**Parallelism:** none.

---

## Segment `S2` — structural consolidation

- [ ] **T-045-11 — AR-1: the atomic-write primitive's home, ruled**

**Owner role:** software-architect · **Commit:** `docs(T-045-11): AR-1 ruling — atomic-write
home`

**Preconditions:** T-045-10 `[x]`.

**Write set:** `specs/releases/v0.4.5/reviews/S2-AR1-ruling.md`.

**Description:** Rule on SPEC **D5** — `core/atomic_write.py`, added to the core file-I/O
ratchet-authorized set on the `core/specs_repair` precedent — against the two constraints
the backlog entry demanded be adjudicated: the features-no-cross-feature-import rule with the
core-I/O ratchet, and the hooks-never-import-container latency law. If the ruling overturns
D5, state the alternative home **and** whether one sanctioned import-light duplicate in
`hooks/_common` is required, with its reason.

**Done criterion:** a ruling recorded verbatim, before any consumer moves (A2.1).

**Parallelism:** none.

---

- [ ] **T-045-12 — FR2 (expand): the primitive and its injected-failure battery**

**Owner role:** software-engineer · **Commit:** `feat(T-045-12): one atomic-write primitive
with temp cleanup on every failure path`

**Preconditions:** T-045-11 `[x]`.

**Write set:** `dadaia_workspace/core/atomic_write.py` (or the AR-1 home), the core
file-I/O authorized-set declaration, `tests/**`.

**Description:** Author the primitive: preserve-mode on/off, LF-bytes/binary, **temp cleanup
on any failure path, always**. Re-point the injected-`os.replace`-failure battery at it and
prove every parameter combination leaves no `.tmp` sibling. **Nothing is deleted in this
task** — the net exists before anything is cut (D7).

**Done criterion:** battery green on every parameter combination; `core/` stdlib-pure;
`lint-imports` green with no new accepted edge.

**Parallelism:** none.

---

- [ ] **T-045-13 — FR2 (switch): eleven call sites move to the primitive**

**Owner role:** software-engineer · **Commit:** one coherent commit per module family,
`refactor(T-045-13): route <module> through the atomic-write primitive`

**Preconditions:** T-045-12 `[x]`.

**Write set:** `dadaia_workspace/hooks/_common.py`,
`dadaia_workspace/infrastructure/{public_assets_common,json_agent_model_policy_store}.py`,
`dadaia_workspace/features/migrate/{frontmatter_keys,state_v2}.py`,
`dadaia_workspace/features/specs/doctor_structural.py`,
`dadaia_workspace/features/spec_context/{session_identity,presence}.py`,
`dadaia_workspace/features/import_/service.py`, `tests/**`.

**Description:** Eight named writers plus three inline `.tmp` writers now **delegate**; the
old names may remain as thin call-through shims for this task only. Suite green after each
commit. The hooks call site is the latency-sensitive one: verify the hook still imports no
container.

**Done criterion:** every call site delegates; suite green at each commit; hook load-time
posture unchanged, measured.

**Parallelism:** none.

---

- [ ] **T-045-14 — FR2 (contract): delete the writers, land the derived census**

**Owner role:** software-engineer · **Commit:** `refactor(T-045-14): delete the eight named
and three inline atomic writers`

**Preconditions:** T-045-13 `[x]`.

**Write set:** the same modules (shims removed), `tests/**` (the leak characterization test
deleted, the derived call-site census added), `specs/bugs/bugs.jsonl`.

**Description:** Delete every shim, every inline `.tmp` writer, and the self-destructing
characterization test that pinned the *leaking* behaviour — in the **same commit** that makes
leaking impossible. Land the census test that derives every atomic write in the package by
scan and asserts each routes through the one primitive. Capture **V4** (8 named + 3 inline →
1). Append the superseded bug's `Closed` disposition material.

**Done criterion:** A2.2, A2.4, A2.6, A2.7; V4 captured; production LOC for FR2
net-negative, measured.

**Parallelism:** none.

---

- [ ] **T-045-15 — FR3: split the inventory out of the two byte goldens**

**Owner role:** software-engineer · **Commit:** `test(T-045-15): policy-only byte goldens,
derived roster for the inventory`

**Preconditions:** T-045-14 `[x]`.

**Write set:** `tests/helpers/public_asset_roster.py` (new),
`tests/e2e/features/test_install_target_goldens.py`,
`tests/integration/test_public_assets_profile.py`.

**Description:** Derive the roster by scanning `dadaia_workspace/public/**`; the two goldens
keep policy-only assertions. Prove by an executed fixture: adding a throwaway asset fails the
**roster** and leaves both goldens green. Zero production-code lines change.

**Done criterion:** A3.1–A3.3.

**Parallelism:** none.

---

- [ ] **T-045-16 — FR4: one shared skill-inventory oracle**

**Owner role:** software-engineer · **Commit:** `test(T-045-16): one derived skill-inventory
oracle replaces three hand-kept lists`

**Preconditions:** T-045-15 `[x]`.

**Write set:** `tests/helpers/skill_inventory_oracle.py` (new),
`tests/e2e/features/test_public_pipeline.py`, `tests/integration/test_public_assets.py`,
`scripts/check_skill_orphans.py`.

**Description:** Delete `EXPECTED_SKILLS`, the hand-kept path assertions and the orphan
checker's roster; all three read the one derived oracle. Prove by an executed fixture: a
single skill rename is green everywhere after touching **one** place. This seam produced two
v0.4.4 bugs — the reviewer's bug-surface verdict must say so.

**Done criterion:** A4.1–A4.4.

**Parallelism:** none.

---

- [ ] **T-045-17 — FR5: the scan-test vacuity convention**

**Owner role:** software-engineer · **Commit:** `test(T-045-17): non-empty population +
sentinel on the tree-walking scan tests`

**Preconditions:** T-045-16 `[x]`.

**Write set:** `tests/helpers/scan_population.py` (new, two lines of helper),
the ~15 tree-walking scan tests.

**Description:** Apply the two-assertion convention test-by-test. **No shared harness and no
base class** — the v0.4.4 S5-FR23 ruling evaluated and rejected one. Produce the census of
such tests by scan, and prove the convention bites: a deliberately mis-rooted walker turns at
least three sampled tests RED.

**Done criterion:** A5.1–A5.3.

**Parallelism:** none.

---

- [ ] **T-045-18 — `S2` close: `qa-engineer` review committed on the branch**

**Owner role:** qa-engineer · **Commit:** `docs(T-045-18): S2 QA close`

**Preconditions:** T-045-11 … 17 all `[x]`.

**Write set:** `specs/releases/v0.4.5/reviews/S2-qa-close.md`.

**Description:** Evidence A2–A5, reference the AR-1 ruling, capture **V5** (test-LOC delta),
and state the bug-surface delta of the atomic-write and test-inventory surfaces. Confirm that
`expand → switch → contract` was actually followed — three commits, each independently green
— and refuse the segment if the demolition arrived as one commit.

**Done criterion:** `APPROVE` committed on the branch; V5 captured.

**Parallelism:** none.

---

## Segment `S3` — gate, doctor and seam hardening

- [ ] **T-045-19 — FR6: the denylist reaches the write-time redaction seam**

**Owner role:** software-engineer · **Commit:** `fix(T-045-19): one denylist loading seam,
consumed by write-time redaction and the push scan`

**Preconditions:** T-045-18 `[x]`.

**Write set:** `dadaia_workspace/core/models/bugs.py`,
`dadaia_workspace/infrastructure/privacy_check.py`, `tests/**`.

**Description:** RED first: a bug event whose free-text field carries a denylisted term is
written raw today. Wire `load_privacy_terms` into the write-time redaction so the leak never
reaches a commit. **One** loader, consumed twice — no second reader. The push-time scan is
unchanged in behaviour; its fixtures stay green untouched. Fields are enumerated from the
event schema, never from a hand-kept list. The denylist data stays operator-local.

**Done criterion:** A6.1–A6.5; `dadaia public doctor` reports `[ok] public-privacy`.

**Parallelism:** none.

---

- [ ] **T-045-20 — FR7: one control/format-character sanitation pass at the bug-event seam**

**Owner role:** software-engineer · **Commit:** `fix(T-045-20): sanitize control and format
characters at the bug-event seam`

**Bug (bundled, D3):** `bug-event-field-with-unicode-line-separator-silently-drops-the-event`
(MEDIUM).

**Preconditions:** T-045-19 `[x]`.

**Write set:** `dadaia_workspace/infrastructure/jsonl_bug_store.py`,
`dadaia_workspace/cli/commands/bugs.py` (rendering only, if needed), `tests/**`,
`specs/bugs/bugs.jsonl`.

**Description:** RED first, twice: an event carrying U+2028 is appended with `[ok]` and then
**unreadable** (`splitlines()` splits the record into two unparseable fragments — silent
event loss); an event whose title carries ESC renders raw in `bugs status` (CWE-117). One
pass at one seam closes both — not two independent guards. Then prove the whole live
`specs/bugs/bugs.jsonl` still parses, and rewrite **no** historical event.

**Done criterion:** A7.1–A7.5; `resolved` event with the three fields.

**Parallelism:** none.

---

- [ ] **T-045-21 — FR8: `specs init --specs-dir` refuses a symlinked target**

**Owner role:** software-engineer · **Commit:** `fix(T-045-21): refuse a symlinked target on
the explicit --specs-dir branch`

**Preconditions:** T-045-20 `[x]`.

**Write set:** `dadaia_workspace/features/specs/**`, `tests/**`.

**Description:** RED first: the explicit branch scaffolds through the link today. Reuse the
**existing** refusal posture and message shape from the T-044-40-hardened resolver seam — no
new vocabulary, no second symlink check. The non-symlinked explicit branch is unaffected.

**Done criterion:** A8.1–A8.3.

**Parallelism:** none.

---

- [ ] **T-045-22 — FR9: decide the healing lane for registry slug-ownership collisions**

**Owner role:** software-architect (decision) + software-engineer (if implemented) ·
**Commit:** `feat(T-045-22): registry-wide slug-ownership invariant` **or**
`docs(T-045-22): slug-ownership healing lane ruled out`

**Preconditions:** T-045-21 `[x]`.

**Write set:** `dadaia_workspace/features/spec_context/doctor.py` + `tests/**` **or**
`specs/releases/v0.4.5/reviews/S3-FR9-ruling.md`.

**Description:** The two v0.4.4 write seams never heal a pre-existing colliding registry
that the v2→v3 migration imports. Either add the registry-wide uniqueness invariant to the
existing doctor lane — **one** check, not a new doctor surface — with a fixture that plants
a colliding v2 registry and proves it is reported, or record the rule-out in one paragraph
naming the reason and the residual risk. Either way the F-1/F-12 class ends with no
undecided lane.

**Done criterion:** A9.1–A9.3.

**Parallelism:** none.

---

- [ ] **T-045-23 — FR10: the doctor learns `.dadaia/references/`**

**Owner role:** software-engineer · **Commit:** `feat(T-045-23): sanction .dadaia/references
as an operator-owned subtree outside the context lifecycle`

**Preconditions:** T-045-22 `[x]`.

**Write set:** `dadaia_workspace/features/spec_context/doctor.py` (or the documented
`.dadaia/`-level allowlist), `tests/**`.

**Description:** Encode operator ruling **O4**: `.dadaia/references/` is never flagged, never
GC'd, never a managed context. The part that matters is the second test — **no lifecycle
verb** resolves, binds, alives, deads or GCs a reference clone, asserted on the executed
path. Lifecycle verbs acting on foreign trees destroyed work before. One place, not a rule
repeated per verb. `specs/` is untouched.

**Done criterion:** A10.1–A10.4.

**Parallelism:** none.

---

- [ ] **T-045-24 — `S3` close: `qa-engineer` review committed on the branch**

**Owner role:** qa-engineer · **Commit:** `docs(T-045-24): S3 QA close`

**Preconditions:** T-045-19 … 23 all `[x]`.

**Write set:** `specs/releases/v0.4.5/reviews/S3-qa-close.md`.

**Description:** Evidence A6–A10 and the bundled bug. State the bug-surface delta of the bug
ledger surface — FR6 and FR7 both touch it, and the privacy-leak class has now recurred
three times.

**Done criterion:** `APPROVE` committed on the branch.

**Parallelism:** none.

---

## Segment `S4` — the token-economy program

- [ ] **T-045-25 — [shell] FR11 baseline: measure before any cut**

**Owner role:** ai-engineer · **Commit:** the capture reference only

**Preconditions:** T-045-24 `[x]`.

**Write set:** none in the repo — captures under `.dadaia/tmp/ai-engineer/<YYYYMMDD>/`.

**Description:** Capture **V6** (always-on token count: the law as each harness loads it, the
nine persona bodies, every always-loaded skill description), **V7** (negation count), **V8**
(bound-session injection prefix, on a **real** session) and **V9** (per-persona line counts,
all nine). Measured, never estimated — everything downstream is a delta against this.

**Done criterion:** V6–V9 captured with their exact commands recorded.

**Parallelism:** none.

---

- [ ] **T-045-26 — FR12: trim, page or tier the catalog digest**

**Owner role:** product-engineer (the curation policy) + ai-engineer (its mechanism) ·
**Commit:** `feat(T-045-26): catalog digest curation policy`

**Preconditions:** T-045-25 `[x]`. `ACTIVE.md` phase is `IMPLEMENTATION`; the memory write
here is the `catalog.json` curation policy and is authored by `product-engineer`.

**Write set:** `specs/memory/product/catalog.json` + the generator that produces it;
`specs/memory/product/index.md` if membership or order changes; `tests/**`.

**Description:** The 28-entry digest is the dominant contributor to the ~2.78k bound-session
prefix (target ≤0.7k). Trim, page or tier it — **catalog curation policy**, written where the
catalog is generated so it is not a one-off hand edit. `ctx_inject`'s digest logic is **byte
unchanged** (v0.4.4 A30.3). Every catalog entry stays reachable: this changes what is
*injected*, never what *exists*.

**Done criterion:** A12.1–A12.4; V8 re-captured on a real session.

**Parallelism:** none.

---

- [ ] **T-045-27 — FR11: the always-on diet pass**

**Owner role:** ai-engineer · **Commit:** `refactor(T-045-27): always-on diet pass —
<before>→<after> tokens`

**Preconditions:** T-045-26 `[x]`.

**Write set:** `dadaia_workspace/public/data/DADAIA.md` (source only — the projected law is
PROTECTED), `dadaia_workspace/public/agents/**`, the always-on rules, then one projection
cycle.

**Description:** Cut toward ≤3.5k tokens and ≤60 negations. A pointer replaces a
restatement; a restatement never replaces a pointer. Produce the **coverage table** — every
removed block → the surviving home that carries it. **No law is dropped silently.** If the
target is missed, the number and the reason go to `CLOSURE.md` for the operator's ruling; the
target is never redefined to fit the result (AS-3).

**Done criterion:** A11.1–A11.4; V6/V7 re-captured; projections byte-identical to source.

**Parallelism:** none.

---

- [ ] **T-045-28 — FR13: trim the four over-ceiling personas**

**Owner role:** ai-engineer · **Commit:** `refactor(T-045-28): relocate justified persona
overflow into existing siblings`

**Preconditions:** T-045-27 `[x]`.

**Write set:** `dadaia_workspace/public/agents/{product-engineer,qa-engineer,ai-engineer,software-architect}.md`,
the existing disclosed skill siblings that receive relocated content, then one projection
cycle.

**Description:** Relocate justified content into the sibling mechanisms that **already
exist** (AS-1 — the nine-skill execution that would create new ones is not in this release).
Coverage table per removed block. No persona loses a write-allowlist row, a scope boundary
or a hard-stop block. Any persona still above 220 lines afterwards is **named** in
`CLOSURE.md` with its count and reason — never silently accepted.

**Done criterion:** A13.1–A13.4; V9 re-captured; fleet net negative.

**Parallelism:** none.

---

- [ ] **T-045-29 — FR14: the AI-surface hygiene residuals**

**Owner role:** ai-engineer · **Commit:** `fix(T-045-29): ai-engineer citation + F-7/F-8/F-10
wording residuals`

**Preconditions:** T-045-28 `[x]`.

**Write set:** `dadaia_workspace/public/agents/ai-engineer.md` and the F-7/F-8/F-10 wording
sites, then one projection cycle.

**Description:** `ai-engineer.md` cites section 5 for content that lives in section 8 — the
F-3 stale-anchor class inside `public/**`. Fix at source, sweep the three cosmetic residuals
in the same pass, re-project. Zero behaviour change.

**Done criterion:** A14.1–A14.3; the v0.4.4 citation check green at HEAD; `public doctor`
green.

**Parallelism:** none.

---

- [ ] **T-045-30 — FR15: rule the test-Intent vocabulary**

**Owner role:** ai-engineer (the skill text) + software-engineer (the sweep, if that is the
ruling) · **Commit:** `docs(T-045-30): rule the test-Intent vocabulary`

**Preconditions:** T-045-29 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dadaia-test-stewardship/SKILL.md`, plus
`tests/**` if the ruling sweeps the 11 declarations, then one projection cycle.

**Description:** Eight `REGRESSION` and three `BUG` Intent declarations sit outside the
taxonomy. Either admit the two tokens or sweep the declarations onto existing tokens — one
decision, stated once in the skill's taxonomy section. Record in `CLOSURE.md` that this does
not pre-empt the ratified C1 stewardship Update (O3), so the later release rebases rather
than reverts (AS-2).

**Done criterion:** A15.1–A15.3; zero off-taxonomy declarations, proven by scan.

**Parallelism:** none.

---

- [ ] **T-045-31 — `S4` close: `qa-engineer` review committed on the branch**

**Owner role:** qa-engineer · **Commit:** `docs(T-045-31): S4 QA close`

**Preconditions:** T-045-25 … 30 all `[x]`.

**Write set:** `specs/releases/v0.4.5/reviews/S4-qa-close.md`.

**Description:** Evidence A11–A15. **Read the coverage tables, not the diff alone** — the
risk here is a law deleted with no other home (R-4). Record the before/after of V6–V9 and
say plainly whether each target was met, missed or partially met.

**Done criterion:** `APPROVE` committed on the branch.

**Parallelism:** none.

---

## Scope complete — gates and the trio

- [ ] **T-045-32 — [shell] FR16: the invariants, measured**

**Owner role:** software-engineer · **Commit:** the capture reference only

**Preconditions:** T-045-31 `[x]`; every task above `[x]`.

**Description:** Run `dadaia ci preflight`, `dadaia doctor`, `dadaia specs doctor`
(**0 errors**), `dadaia backlog doctor`, `dadaia public doctor`, `lint-imports`. Capture
**V10** (production LOC net) and **V11** (AI-surface LOC net). A positive net in either is a
defect of the release, justified per contributing FR or refused.

**Done criterion:** A16.1–A16.6; V10 and V11 captured.

**Parallelism:** none.

---

- [ ] **T-045-33 — Six-axis code review on the thawed tree**

**Owner role:** code-reviewer · **Commit:** `docs(T-045-33): release code review`

**Preconditions:** T-045-32 `[x]`.

**Write set:** `specs/releases/v0.4.5/reviews/T-045-33-code-review.md`.

**Description:** Review the whole delta on a **thawed** tree, before any archive move. For
every touched feature, state whether the change **reduced or increased its bug surface**,
with bug-history evidence — "tests green" is not a verdict. Two specific questions this
release must answer: did FR1 leave the gate feature smaller, and did the four demolitions
land as `expand → switch → contract` rather than big-bang?

**Done criterion:** `APPROVE` with the bug-surface verdict per touched feature.

**Parallelism:** none.

---

- [ ] **T-045-34 — Security review + the QA release verdict**

**Owner role:** security-reviewer + qa-engineer · **Commit:**
`docs(T-045-34): release verdicts`

**Preconditions:** T-045-33 `[x]`.

**Write set:** `specs/releases/v0.4.5/reviews/RELEASE-VERDICT.md`, the verdict handoffs.

**Description:** Diff-based `security-reviewer` review of the whole delta — FR1 (the gate
classifier), FR6 (redaction), FR7 (ledger input) and FR8 (CWE-59) are the surfaces that
matter. Then the `qa-engineer` release verdict closing the scope. All three verdicts —
QA, code, security — must `APPROVE` the **same** commit.

**Done criterion:** three `APPROVE`s on one sha; the verdict handoff is keyed to it.

**Parallelism:** none.

---

## `rc-1` — the whole scope integrates once

- [ ] **T-045-35 — [git] `rc-1`: PR `feature/0.4.5` → `develop`**

**Owner role:** dispatcher + security-reviewer · **Preconditions:** T-045-34 `[x]`.

**Description:** Push `feature/0.4.5`, open the PR to `develop` with the APPROVED verdict
covering the **PR head sha**, watch CI to green, merge. That merged `develop` **is `rc-1`**
(D8) — the first and only integration of the whole scope. **T-045-03 must be done before any
`rc-2` PR.**

**Done criterion:** PR merged; CI green; APPROVED verdict recorded; `develop` carries the
whole scope.

**Parallelism:** none.

---

## `rc-2 … rc-N` — adjustment rounds on the merged scope

- [ ] **T-045-36 — Adjustment rounds: test `develop`, fix on the branch, merge again**

**Owner role:** qa-engineer + operator (finding) · software-engineer / ai-engineer (fixing) ·
dispatcher + security-reviewer (merging) · **Preconditions:** T-045-35 `[x]`.

**Description:** The merged `develop` is exercised. Each finding **on this release's scope**
becomes a fix worked on `feature/0.4.5`, QA-closed, delta-reviewed and merged again by PR:
one `rc` per merge. **No new backlog enters an `rc`** (A16.7/R-7) — a demand outside this
scope is recorded for the PM's intake, never worked here. **This task may close with zero
rounds**, in which case the final `rc` **is** `rc-1`.

**Done criterion:** every round has a QA close, a delta review, a merge and a ledger row
(finding → who found it → fix → `rc` number) for CLOSURE; the accepted final `rc` is named.

**Parallelism:** none — one round at a time.

---

## The final `rc` — closure, archive, ship without publish

- [ ] **T-045-37 — Memory window (SPEC §5)**

**Owner role:** product-engineer · **Commit:** `docs(T-045-37): memory after v0.4.5`

**Preconditions:** T-045-36 `[x]` (the final `rc` is accepted); `ACTIVE.md` phase `CLOSURE`.

**Write set:** the atoms named in SPEC §5 — the **two mandatory rewrites**
(`sdd-gate-v3.md` for the origin-based LAW class, `pypi-distribution.md` for the
minted-unpublished lineage) **first**, then the rest, one authoring pass per atom;
`product/index.md` + `catalog.json` regenerated under FR12's curation policy.

**Done criterion:** memory describes the product as it now is, with no changelog;
`specs doctor` 0 errors.

**Parallelism:** none.

---

- [ ] **T-045-38 — `CLOSURE.md` with every sweep**

**Owner role:** product-engineer · **Commit:** `docs(T-045-38): v0.4.5 closure`

**Preconditions:** T-045-37 `[x]`.

**Description:** Per `dd-release-implement`: summary; tasks + final shas; validations
(`{description, command, evidence}`); `## Size accounting` (V10, V11, V6–V9 before/after);
`## Ship-without-publish record` (A16.8's three verifications, filled after T-045-41);
drifts; memory updates; **dispositions** — 14 `LEDGER` lines **updated** `CONSUMED · v0.4.5`
→ `DELIVERED · v0.4.5` (never a second line, BL-DUP), 7 bugs `Closed`, 1 `Closed` +
`superseded_by: atomic-write-primitive-consolidation`, and the AS-5 outcome for
`windows-xdist-workers-crash-on-unit-fast-tier`; test dispositions (demotions, quarantines
with their bug ids, SCAFFOLD expiries); the **AR-1 ruling** verbatim; the **`rc` ledger**;
the artifact GC sweep; **intake candidates** for the PM's operator-facing report (no backlog
entry is created here); the restated git-identity standing question; archive decision
`MOVE`.

**Done criterion:** every closure obligation in SPEC §5 is discharged.

**Parallelism:** none.

---

- [ ] **T-045-39 — [git] Archive the release**

**Owner role:** dispatcher · **Commit:** `chore(T-045-39): archive v0.4.5`

**Preconditions:** T-045-38 `[x]`.

**Description:** `git mv specs/releases/v0.4.5 specs/_archive/releases/v0.4.5`; set
`ACTIVE.md` to `phase: ARCHIVED`. Steps T-045-37 … 39 ride **one** commit, in the order
memory → CLOSURE → sweep → archive.

**Done criterion:** the release directory is under `_archive/`; `ACTIVE.md` repointed.

**Parallelism:** none.

---

- [ ] **T-045-40 — [git] Final-`rc` merge: version bump and PR → `develop`**

**Owner role:** dispatcher + software-engineer + security-reviewer

**Preconditions:** T-045-39 `[x]`.

**Write set:** `pyproject.toml` (`0.4.4` → `0.4.5`), `CHANGELOG.md` (`[0.4.5]`, stating
**once** that this version is minted locally and deliberately unpublished by operator order
O5), then git refs.

**Description:** One axis: the release id **is** the package version (SPEC §2.4/D6). The
memory window, `CLOSURE.md` and the archive move ride this merge. Push `feature/0.4.5`,
APPROVED verdict on the PR head sha, PR to `develop`, CI green, merge — this burns the
**final `rc`**.

**Done criterion:** PR merged; CI green; `CHANGELOG.md` states the unpublished mint exactly
once.

**Parallelism:** none.

---

- [ ] **T-045-41 — [git] Ship — merge to `main`, publish NOTHING**

**Owner role:** dispatcher + security-reviewer · **Preconditions:** T-045-40 `[x]`.

**Description:** PR `develop → main`; watch CI to green; merge. The merge fires
`release.yml`; its `approve` job blocks on the `release-gate` GitHub environment and **that
approval is deliberately withheld** (operator law **O5**) — `publish` never runs, and no
`v0.4.5` git tag is created. Publication awaits a separate operator order. Then, **in the
same step**: delete `feature/0.4.5` and cut **`feature/0.4.6` from `main`**. Run the
reconciliation merge of `main` into `develop`. Capture **V12**: the `approve` job pending and
unapproved, `git tag --list 'v0.4.5'` empty, PyPI's latest still `0.4.4`. Fill
`CLOSURE.md`'s `## Ship-without-publish record` with V12, then set `ACTIVE.md` to the next
release or `release: none`.

**Done criterion:** PR merged to `main`; CI green; **nothing published**; `feature/0.4.5`
gone; `feature/0.4.6` exists and is cut from `main`; V12 captured and recorded; worktree
clean.

**Parallelism:** none — last task.
