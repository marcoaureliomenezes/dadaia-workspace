# TASKS — Release v0.12.0 — backlog-tooling-single-source

**Status:** Aprovado
**Approval provenance:** operator-delegated approval, 2026-08-15 (goal directive)
**Release ID:** v0.12.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.12.0/SPEC.md`
**Source PLAN:** `specs/releases/v0.12.0/PLAN.md`
**Branch:** `feature/v0.12.0` (cut from `develop` at `523f0d8d`; branch contract: `dadaia-gitflow`)
**Segment:** none — flat release; one implementation increment closed by T-120-11 (the
`alpha-1` close), then ship.

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Standing rules for this release

- **`product-engineer` has no shell.** Every task marked **[git]** or carrying a command is
  executed by the dispatcher, `software-engineer`, `project-manager` or `ai-engineer`.
  `product-engineer` authors text only.
- **Green at every commit** (SPEC §3): `dadaia backlog doctor` and `dadaia specs doctor` pass
  before every commit that touches `specs/backlog/**` or the backlog tooling. **No
  `--no-verify`, ever** — a failing gate is fixed in the working tree.
- **RED before GREEN.** Every behavioural task writes its failing test first and observes it
  failing for the real reason (`DADAIA.md` §6).
- **Test intent at birth.** Every added test declares `Intent: CONTRACT — v0.12.0 <A-id>` or
  `Intent: SENTINEL — <seam>`. **Zero new e2e tests** — the CI backlog job's contract does not
  change.
- **Never prune to go green.** The four deletions in T-120-03 are **recorded supersessions**
  (their subject is deleted by FR4), listed there and dispositioned at closure. Any other
  deletion, skip or quarantine requires a `qa-engineer` verdict with evidence.
- **Never delete a record.** Every file leaving `specs/backlog/` leaves by `git mv` into
  `specs/backlog/_archive/`. Nothing under `specs/_archive/**` is touched.
- **Lane discipline.** Stay inside the task's declared write set; the only cross-lane task is
  T-120-08, and it is one commit.
- **One `[-]` at a time.** One sanctioned parallel pair: **T-120-09** may run concurrently
  with **T-120-10** (disjoint write sets: `public/scaffold` + `public/data` + `ci.yml` vs
  `public/skills/dd-*`). Both must re-run the projection chain; if they land together, one
  projection run covers both. No other pair is safe.
- **A group of completed work is one commit** — stage exactly the task's write set, never
  `-A` over a shared tree.
- **Reservation is observable.** Flip `[ ]` → `[-]` and commit `chore(tasks): start <id>`
  before the work, per `dadaia-task-manager`.

## Acceptance and evidence map

| Task | Entry | Acceptance ids | Evidence |
|---|---|---|---|
| T-120-01 | — | — | definition commit sha; `ACTIVE.md` reads `IMPLEMENTATION` |
| T-120-02 | — | — | pushed `develop` sha + APPROVED security handoff path |
| T-120-03 | #30 (2-2) | A4.1–A4.6 | V6 zero-hit output, commit sha |
| T-120-04 | #30 | A1.1–A1.6 | V1 + V10 output, commit sha |
| T-120-05 | #30 | A2.1–A2.8 | V3 fixture output, commit sha |
| T-120-06 | #30 | A3.1–A3.4 | V1 output, byte-diff assertion |
| T-120-07 | #31 | A7.1, A7.2, A7.4, A7.7 | V8 set-difference capture |
| T-120-08 | #30 + #31 | A2.9, A3.5, A5.1–A5.6, A7.3, A7.5, A7.6, A9.1, A9.2 | V2+V4+V5+V7+V9 output, cutover commit sha |
| T-120-09 | #30 | A6.1–A6.5 | V11 + V12 output |
| T-120-10 | #30 (2-2) | A8.1–A8.4 | V11 output, skill diff |
| T-120-11 | all | every id + A9.3–A9.6 | `qa-engineer` APPROVED artifact |
| T-120-12 | #30, #31 | SPEC §5 | memory diff; `specs doctor` green |
| T-120-13 | #30, #31 | closure obligations | `CLOSURE.md` under `_archive/`; `0.9.0` bump |
| T-120-14 | — | — | PR merged to `main`; CI green |

---

- [x] **T-120-01 — [git] Commit the definition content on `feature/v0.12.0`**

**Owner role:** software-engineer (or dispatcher) · **Commit:**
`docs(T-120-01): v0.12.0 definition — backlog tooling single source`

**Preconditions:** `SPEC.md`, `PLAN.md`, `TASKS.md` and `GRILL.md` authored; the trio carries
`**Status:** Aprovado`. Working tree on `feature/v0.12.0`.

**Write set (staging only — content already authored by `product-engineer`):**
`specs/releases/ACTIVE.md`, `specs/releases/v0.12.0/{GRILL,SPEC,PLAN,TASKS}.md`,
`specs/backlog/backlog-tooling-reconciliation.md`,
`specs/backlog/backlog-md-physical-consolidation.md`, `specs/backlog/candidates.md`.

**Description:** Stage exactly those paths and commit — the pick and the SPEC ride one commit
(`DADAIA.md` §5). Set `ACTIVE.md` phase from `DEFINITION` to `IMPLEMENTATION` in the same
commit. The pre-commit backlog gate fires (backlog paths are staged) and must pass on the
**old** shape with the two `status: picked` flips.

**Done criterion:** one commit containing exactly those paths; `ACTIVE.md` reads
`release: v0.12.0` / `phase: IMPLEMENTATION`; `dadaia backlog doctor` clean.

**Parallelism:** none — first task.

---

- [x] **T-120-02 — [git] Milestone (a): merge, security review, push**

**Owner role:** dispatcher + `security-reviewer` · **Commit:** merge commit on `develop`

**Preconditions:** T-120-01 `[x]`.

**Write set:** git refs only (`develop`), plus the security-reviewer handoff under
`.dadaia/handoff/dadaia-workspace/`.

**Description:** Per `dadaia-gitflow` milestone (a), in order: merge `feature/v0.12.0` into
local `develop`; run a **diff-based** `security-reviewer` review of `origin/develop..develop`;
push `develop`. The push gate requires an APPROVED handoff keyed to the pushed tip plus the CI
preflight.

**Done criterion:** `develop` pushed; APPROVED handoff covering the pushed delta; CI green.

**Parallelism:** none.

---

- [x] **T-120-03 — FR4: retire the dead removal/consumption write side and the dead fakes**

**Owner role:** software-engineer · **Commit:**
`refactor(T-120-03): delete the uncalled backlog removal/consumption write side`

**Preconditions:** T-120-02 `[x]`.

**Write set:** delete `dadaia_workspace/features/backlog/{removal_lifecycle,removal,ledger_writer,consumes}.py`;
edit `dadaia_workspace/container.py` (drop `build_backlog_removal_lifecycle`, its TYPE_CHECKING
import, `_backlog_context_roots` if it loses its last caller, `_fake_spec_stub`,
`_SCOPE_ITEM_RE`, `_FAKE_BACKLOG_CANARY_SLUG`, `_fake_backlog_canary_slug`,
`_fake_backlog_canary_ref`); edit `dadaia_workspace/features/backlog/__init__.py`;
delete `tests/unit/test_backlog_removal.py`, `tests/unit/test_backlog_ledger_writer.py`,
`tests/integration/test_backlog_removal_loop.py`, `tests/unit/backlog/test_consumes.py`.

**Description:** Deletion only — no behaviour is moved or reimplemented. `ledger.py`
(`read_consumed`, `LEDGER_FILENAME`) is **kept untouched**: it is a live BL-STALE input and
its test must pass unmodified (A4.2). Nothing under `specs/_archive/**` is touched, including
the 18 historical `consumed_backlog.json` sidecars.

**Recorded supersessions (D6 — no silent pruning).** Four test modules are deleted because
their subject no longer exists:

| Deleted test module | Deleted subject | Replacement coverage |
|---|---|---|
| `tests/unit/test_backlog_removal.py` | `features/backlog/removal.py` | none needed — behaviour removed, not moved |
| `tests/unit/test_backlog_ledger_writer.py` | `features/backlog/ledger_writer.py` | none needed |
| `tests/integration/test_backlog_removal_loop.py` | `removal_lifecycle` consume/remove loop | BL-STALE is covered over the new shape by T-120-05 (A2.6, A2.7) |
| `tests/unit/backlog/test_consumes.py` | `features/backlog/consumes.py` | none needed — `**Consumes:**` becomes provenance text (FR8) |

**Done criterion:** A4.1's zero-hit grep passes under the standing exclusions; A4.2, A4.5 and
A4.6 hold; `dadaia ci preflight` green; both doctors still clean on the **old** shape.

**Acceptance / evidence:** A4.1–A4.6 · V6 + V1 output, commit sha.

**Parallelism:** none.

---

- [x] **T-120-04 — FR1: `features/backlog/document.py`, the single-source parser**

**Owner role:** software-engineer · **Commit:**
`feat(T-120-04): parse BACKLOG.md into a typed ACTIVE/LEDGER model`

**Preconditions:** T-120-03 `[x]`.

**Write set:** `dadaia_workspace/features/backlog/document.py` (new),
`dadaia_workspace/core/models/backlog.py` (the six terminal disposition tokens defined once),
`tests/unit/features/backlog/test_document.py` (new).

**Description:** RED first — a fixture document exercising each A1 case before the parser
exists. Implement per PLAN §5: sectioning, the five required keys plus optional
`**Intents:**`, the four-field `·` LEDGER grammar, located errors captured never raised,
absent file ⇒ empty model. Reuse `core.models.backlog.parse_intents` and
`preview._format_yaml_error`'s message shape — do not write a second YAML error formatter.
**Not wired to anything yet**; the live CLI still reads per-entry files.

**Done criterion:** A1.1–A1.6 satisfied; `lint-imports` green; `dadaia ci preflight` green;
live doctors unchanged and clean.

**Acceptance / evidence:** A1.1–A1.6 · V1 + V10 output, commit sha.

**Parallelism:** none.

---

- [x] **T-120-05 — FR2: the four BL-* checks over the document model (unwired)**

**Owner role:** software-engineer · **Commit:**
`feat(T-120-05): run BL-SCHEMA/DUP/CONFLICT/STALE over the ACTIVE/LEDGER model`

**Preconditions:** T-120-04 `[x]`.

**Write set:** `dadaia_workspace/features/backlog/doctor.py`,
`dadaia_workspace/features/backlog/preview.py` (anchor half retained; `bound_anchor_changes`
takes an `ActiveItem`), `tests/integration/test_backlog_doctor.py`,
`tests/unit/features/backlog/test_frontmatter_yaml_parse_error.py`.

**Description:** RED first per A2.2–A2.7. Keep `_CHECKS`, `Finding`, `Severity`, the injected
roots signature, the message texts and the ordering contract. BL-STALE gains its three ORed
conditions (ADR D8) and keeps `ledger.read_consumed` as one of them. `load_backlog_items` and
`_NON_ITEM_STEMS` are deleted in this commit **only if** no live caller remains; otherwise
they die at T-120-08 — state which in the commit message. The CLI still calls the old path
until T-120-08 if the loader survives; the release must not carry two live readers past the
cutover.

**Done criterion:** A2.1–A2.8 satisfied against fixtures; the classifier and registry tests
pass **unmodified** (A9.4); `dadaia ci preflight` green.

**Acceptance / evidence:** A2.1–A2.8 · V3 fixture output, commit sha.

**Parallelism:** none.

---

- [x] **T-120-06 — FR3: `backlog new` authors an ACTIVE subsection**

**Owner role:** software-engineer · **Commit:**
`feat(T-120-06): backlog new appends an ACTIVE subsection to BACKLOG.md`

**Preconditions:** T-120-05 `[x]`.

**Write set:** `dadaia_workspace/features/spec_artifacts/new_artifacts.py`,
`tests/unit/features/spec_artifacts/test_new_artifacts.py`,
`tests/integration/cli/test_cli_newartifacts.py`.

**Description:** RED first per A3.1–A3.4. Replace the per-entry stub writer with a document
writer: create `BACKLOG.md` with both section headings when absent, append one conformant
subsection at `status: idea` with today's `Opened`, keep the teaching comment for the intents
block, and refuse a slug already present in `ACTIVE` **or** `LEDGER` with the same exit code
class as today's `FileExistsError` path. The append must leave every other byte untouched
(A3.2). `release_new` is not touched.

**Done criterion:** A3.1–A3.4 satisfied; the CLI's `[ok] created:` / `[error]` contract
unchanged; `dadaia ci preflight` green.

**Acceptance / evidence:** A3.1–A3.4 · V1 output + the byte-diff assertion.

**Parallelism:** none.

---

- [x] **T-120-07 — FR7a: author `BACKLOG.md` from the live tree (content only, uncommitted)**

**Owner role:** project-manager · **Commit:** none — the content is committed by T-120-08

**Preconditions:** T-120-06 `[x]`. The backlog pre-state is frozen: no backlog write between
this task and T-120-08.

**Write set (working tree only, **not staged**):** `specs/backlog/BACKLOG.md`.

**Description:** Per `dd-backlog-definition` §2 + SPEC FR7, fold into one document: every live
candidate and idea as an `ACTIVE` subsection with its Provenance line and its `**Intents:**`
block where the source file had one; every terminal record — the 20 LEDGER lines, the terminal
rows of `candidates.md` (terminal-at-materialization, rejected, intake-adjudication) and every
file under `specs/backlog/_archive/` — as a `LEDGER` line with its disposition token.
`tag-push-carve-out-reachability` resolves to **LEDGER only** (grill P6). The two picked
entries stay ACTIVE at `status: picked`. Live standing notices (the pick-precedence notice, the
undecided panel-telemetry operator question) are restated in the document; the PM
disposition-decision records travel with `candidates.md` into `_archive/`.

Produce the **countable never-delete proof** (A7.2): the sorted pre-state slug set (live files
∪ candidate/idea rows ∪ `_archive/` files ∪ LEDGER lines ∪ terminal-table rows) and the sorted
post-state slug set from the document, plus both set differences — captured under
`.dadaia/tmp/project-manager/<YYYYMMDD>/`. Baseline: 31 live files, 30 live rows, 46 archived
files, 20 LEDGER lines.

**Done criterion:** the document parses clean under `document.load_document`; both set
differences empty; **`git status` shows `BACKLOG.md` untracked and unstaged** — staging it here
would make the still-live per-entry loader parse it (grill P3/P4).

**Acceptance / evidence:** A7.1, A7.2, A7.4, A7.7 · V8 capture path.

**Parallelism:** none.

---

- [x] **T-120-08 — THE CUTOVER: wiring, loader deletion, governance re-target, document, `git mv`** (one commit)

**Owner role:** project-manager + software-engineer (sequenced inside one commit) ·
**Commit:** `feat(T-120-08): cut the backlog over to single-source BACKLOG.md`

**Preconditions:** T-120-07 done (document written, unstaged). All of T-120-03…T-120-06 `[x]`.

**Write set:** `dadaia_workspace/cli/commands/newartifacts.py` (doctor + `_explain_backlog`
wiring), `dadaia_workspace/features/backlog/{doctor,preview}.py` (residual loader deletion),
`dadaia_workspace/features/specs/doctor_governance.py` (SPEC-DOC-031 re-target, SPEC-DOC-035
single-source invariant, `check_backlog_schema` + `BACKLOG_BULLET_RE` + `BACKLOG_HOTFIX_RE` +
`_HOTFIX_STALE_HOURS` + `_BACKLOG_AGGREGATE_FILES` deletion),
`dadaia_workspace/features/specs/doctor.py` (check registration, if the coordinator lists them),
`tests/unit/features/specs/test_doctor*.py` and
`tests/unit/features/specs/_golden/fixture_specs/backlog/**`,
`tests/integration/test_governance_intake_not_gitignored.py`,
`tests/e2e/features/test_backlog_precommit.py`,
`tests/integration/test_precommit_backlog_scoping.py`, `specs/backlog/BACKLOG.md` (new), and
the `git mv` of the 31 live per-entry files + `candidates.md` into `specs/backlog/_archive/`.

**Description:** In one working-tree pass, then **one** commit:

1. Point `backlog doctor` and `--explain` at the document model; delete the last per-entry
   loader path.
2. Re-target the governance checks (PLAN §6): SPEC-DOC-031 over ACTIVE subsections with
   `_archive_consumption_hits` unchanged and severity still WARNING; SPEC-DOC-035 as the
   loose-file single-source invariant, excluding `_archive/` and `remote-bugs/`; retire
   `check_backlog_schema` (SPEC-DOC-012, and with it SPEC-DOC-022/023 — the entry #4 overlap
   recorded in SPEC §7).
3. Migrate the governance fixtures, including the **A5.2 regression**: no finding is ever
   emitted for a phantom `BACKLOG` slug.
4. `git mv` every superseded per-entry file and `candidates.md` into
   `specs/backlog/_archive/`; stage `BACKLOG.md`.
5. Run V2, V4 and V5 **before** committing. Fix in the working tree; never `--no-verify`.

**Done criterion:** one commit; `specs/backlog/` holds exactly `BACKLOG.md`, `README.md` and
`_archive/`; both doctors clean; `git status` reports renames, not deletions; A2.9, A3.5,
A5.1–A5.6, A7.3, A7.5, A7.6, A9.1, A9.2 all hold.

**Acceptance / evidence:** the ids above · V2+V4+V5+V7+V9 output, cutover commit sha.

**Parallelism:** none — this is the release's serialization point.

---

- [x] **T-120-09 — FR6: scaffold README, consumer recipe, CI job comment**

**Owner role:** software-engineer · **Commit:**
`docs(T-120-09): describe the single-source backlog to consumers`

**Preconditions:** T-120-08 `[x]`.

**Write set:** `dadaia_workspace/public/scaffold/backlog/README.md`,
`dadaia_workspace/public/data/CONSUMER_VALIDATION_RECIPE.md` (F-10, R-02, R-13),
`.github/workflows/ci.yml` (the `backlog-doctor` job comment),
`dadaia_workspace/cli/commands/newartifacts.py` (the `backlog doctor` docstring's false
gitignore clause), plus the refreshed projections.

**Description:** Rewrite the consumer-facing description against the shipped model (SPEC FR6):
one document, six subsection keys, the LEDGER grammar, the six terminal tokens by reference to
`dd-backlog-definition` §2, `dadaia backlog new` as the authoring path. Delete R-02's retired
consumed-backlog-ledger clause. Correct the two false "gitignored" claims (`.gitignore:133-142`
opts the tree back in). Job name, verb and arguments unchanged. Then
`dadaia public stage` → `install --target all` → `doctor`.

**Done criterion:** A6.1–A6.5 hold; `dadaia public doctor` green including
`[ok] public-privacy`.

**Acceptance / evidence:** A6.1–A6.5 · V11 + V12 output.

**Parallelism:** T-120-10 only.

---

- [x] **T-120-10 — FR8: the two skills state the mechanism that runs**

**Owner role:** ai-engineer · **Commit:**
`docs(T-120-10): dd-backlog-definition schema and dd-release-definition Consumes mechanism`

**Preconditions:** T-120-08 `[x]`.

**Write set:** `dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md` (§2 tooling note
deleted, optional `**Intents:**` key documented with its status gate, §7 caveat removed),
`dadaia_workspace/public/skills/dd-release-definition/SKILL.md` (§5 rewritten, checklist item
made executable), plus the refreshed projections.

**Description:** Per SPEC FR8 and ADR D2/D7. §5 keeps only what still describes something that
runs: `**Consumes:**` is SPEC provenance; the executors are the PM's purge-on-pick at
definition and the `dd-release-closure` disposition sweep at closure; the mechanical backstops
are `backlog doctor` BL-STALE and `specs doctor` SPEC-DOC-031. Every reference to
`removal_lifecycle.py` and to "until a CLI wrapper ships" is removed. Then
`dadaia public stage` → `install --target all` → `doctor`.

**Done criterion:** A8.1–A8.4 hold; this release's own `dd-release-definition` checklist can be
ticked truthfully against the rewritten §5.

**Acceptance / evidence:** A8.1–A8.4 · V11 output + skill diff.

**Parallelism:** T-120-09 only.

---

- [x] **T-120-11 — `qa-engineer` review of the increment (alpha-1 close)**

**Owner role:** qa-engineer · **Commit:** review artifact committed to the branch
(`specs/releases/v0.12.0/ALPHA-1-QA.md`)

**Preconditions:** T-120-09 `[x]` and T-120-10 `[x]`.

**Write set:** `specs/releases/v0.12.0/ALPHA-1-QA.md`,
`.dadaia/handoff/dadaia-workspace/`, `.dadaia/tmp/qa-engineer/<YYYYMMDD>/` for captures.

**Description:** Verify the increment against SPEC FR1–FR9 acceptance id by id, running
PLAN §9's V1–V14 and capturing every command's output. Give particular weight to: the
countable never-delete proof (A7.2) — recompute it independently rather than trusting the
captured artifact; the rename-not-delete evidence (A9.1); the two-doctor agreement on both a
clean and a planted-violation tree (A5.6); the phantom-`BACKLOG`-slug regression (A5.2); the
absent-document no-op on a fresh context (A1.2, A2.8, V14); and the unmodified-test set
(A4.2, A9.4) — confirm by diff that those five modules were not edited. Confirm every added
test declares intent and size at birth and that no test outside T-120-03's four recorded
supersessions was deleted, skipped or weakened. Apply the redaction-at-authoring doctrine to
the artifact.

**Done criterion:** APPROVED verdict enumerating every acceptance id, or REJECTED returning
named defects to the implementer.

**Acceptance / evidence:** all ids + A9.3–A9.6 · the APPROVED `qa-engineer` artifact + handoff.

**Parallelism:** none.

---

- [ ] **T-120-12 — Memory update (CLOSURE phase)**

**Owner role:** product-engineer · **Commit:**
`docs(T-120-12): memory — the backlog is one document, validated by the shipped tooling`

**Preconditions:** T-120-11 `[x]` with APPROVED. `ACTIVE.md` phase set to `CLOSURE`
**before writing** — the gate allows `specs/memory/**` writes in `DEFINITION` and `CLOSURE`
only.

**Write set:** `specs/memory/product/sdd/sdd-bug-backlog-governance.md`,
`specs/memory/product/sdd/specs-doctor.md`, `specs/memory/product/catalog.json` (regenerated
**only** if a touched atom's `tldr`/`summary` changed, via
`dadaia_workspace/public/scripts/generate-memory-catalog.py`).

**Description:** State the product as it is **now**, per SPEC §5 — no changelog, no history,
no version narrative. In `sdd-bug-backlog-governance`: replace the pending-consolidation
paragraph with the shipped truth (one `BACKLOG.md`, ACTIVE + LEDGER, the verbs read and write
it, BL-STALE means "an ACTIVE item already consumed or dispositioned"), fix §Runtime State
(no per-entry files; `specs/backlog/_archive/` is the historical store), and state the
`**Consumes:**` mechanism once — provenance plus the closure sweep. In `specs-doctor`: the
governance-check inventory after the re-target and the three retirements.

**Done criterion:** `dadaia specs doctor` green on the memory checks; no forbidden section
added; SPEC §5 satisfied file by file.

**Acceptance / evidence:** SPEC §5 · memory diff + `specs doctor` output.

**Parallelism:** none.

---

- [ ] **T-120-13 — CLOSURE, dispositions, archive, version bump**

**Owner role:** product-engineer (text) + software-engineer/dispatcher (**[git]** steps) ·
**Commit:** `docs(T-120-13): close release v0.12.0`

**Preconditions:** T-120-12 `[x]`.

**Write set:** `specs/releases/v0.12.0/CLOSURE.md` (new), `specs/releases/ACTIVE.md`,
`specs/backlog/BACKLOG.md` (the two terminal dispositions), `pyproject.toml` (version),
`CHANGELOG.md`, plus the release-directory move.

**Description:** In the finalization order **memory → CLOSURE → archive**:

1. Record the T-120-12 memory writes under `## Memory updates`.
2. Write `CLOSURE.md` per `dd-release-closure`: summary, tasks + commit SHAs, validations
   V1–V14 with evidence, drifts, `## Dispositions` (both picked entries →
   `DELIVERED — v0.12.0`; state explicitly that **no bug and no audit** was picked) and
   `## Test dispositions` (T-120-03's four recorded supersessions + every migrated module).
   **This is the first closure executed on the new shape**: each disposition is a `LEDGER`
   line in `BACKLOG.md` and the entry's `ACTIVE` subsection is removed in the same commit.
   Residuals — including **OD-2** (entry #4's rewrite to its residual) and any drift found
   while folding — go under `## Intake candidates`, **never materialized as backlog entries**
   (ADR #15). Restate **OD-1** (the `intents[]` schema decision) for the operator.
3. **[git]** `git mv specs/releases/v0.12.0 specs/_archive/releases/v0.12.0`; set `ACTIVE.md`
   to `release: none` / `phase: none`.
4. **[git]** Bump `pyproject.toml` to **0.9.0** (ADR D3; currently `0.8.0`) and add the
   `[0.9.0]` `CHANGELOG.md` entry in the same commit.

**Done criterion:** `CLOSURE.md` complete under `specs/_archive/releases/v0.12.0/`;
`ACTIVE.md` no longer points at `v0.12.0`; both doctors green.

**Acceptance / evidence:** closure obligations (SPEC §5) · `CLOSURE.md` path + bump commit sha.

**Parallelism:** none.

---

- [ ] **T-120-14 — [git] Milestone (b): ship**

**Owner role:** dispatcher + `code-reviewer` + `security-reviewer` · **Commit:** merge commit
+ PR

**Preconditions:** T-120-13 `[x]`.

**Write set:** git refs only, plus the reviewer handoffs.

**Description:** Per `dadaia-gitflow` milestone (b), in order: `code-reviewer` six-axis pass
over the release delta — pointed explicitly at the three non-rename hunks of the cutover
commit (CLI wiring, loader deletion, governance re-target); merge `feature/v0.12.0` into local
`develop`; diff-based `security-reviewer` review of `origin/develop..develop`, asked
specifically to confirm that no backlog record left the tree other than by rename and that
nothing under `specs/_archive/**` was modified; push `develop` with **no `--no-verify`**; open
PR `develop` → `main`; watch CI until every job is green — the `backlog-doctor` job green on
the consolidated tree is this release's own proof (V13); merge.

**Done criterion:** PR merged to `main`; CI green; `feature/v0.12.0` no longer needed.

**Acceptance / evidence:** — · PR number + green CI run.

**Parallelism:** none — last task.
