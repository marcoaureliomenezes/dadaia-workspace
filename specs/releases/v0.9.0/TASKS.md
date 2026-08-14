# TASKS — Release v0.9.0 — Push-range denylist scan

**Status:** Aprovado
**Release ID:** v0.9.0
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.9.0/SPEC.md`
**Source PLAN:** `specs/releases/v0.9.0/PLAN.md`
**Branch:** `feature/v0.9.0` (cut from `develop` at `1883b85b`; branch contract: `dadaia-gitflow`)
**Segment:** none — flat release; one implementation increment, closed by T-090-10

## Task status markers

- `[ ]` OPEN
- `[-]` IN PROGRESS
- `[x]` DONE

## Standing rules for this release

- **`product-engineer` has no shell.** Every task marked **[git]** is executed by the
  dispatcher or `software-engineer`. `product-engineer` authors text only.
- **RED before GREEN.** Each behavioral task writes its failing test first. A task that
  reaches GREEN without ever having been RED for the real reason is not done.
- **Purity is a hard constraint.** No task may make `features/chokepoints/**` import
  `infrastructure` or spawn a subprocess (SPEC A7.1). A task that finds itself needing to
  is a design error: stop and raise it.
- **No private term enters the repository.** Tests use synthetic terms
  (`zz-fake-context-name`) and temporary denylist files under `tmp_path`. Never a real
  operator term, never a real foreign slug, in any tracked file — including this file.
- **Test intent at birth.** Every new test module declares
  `Intent: CONTRACT — v0.9.0 <A-id>` or `Intent: SENTINEL — <seam>` (SPEC A9.3).
- **One `[-]` at a time**, with exactly one sanctioned exception: **T-090-07 may run in
  parallel with T-090-03…T-090-06**, whose write sets are disjoint (declared per task
  below). Never any other pair.
- **A group of completed work is one commit** — not one commit per file.
- **Reservation is observable.** Flip `[ ]` → `[-]` and commit `chore(tasks): start <id>`
  before the work, per `dadaia-task-manager`.

---

- [x] **T-090-01 — [git] Commit the definition content on `feature/v0.9.0`**

**Owner role:** software-engineer (or dispatcher) · **Commit:**
`docs(T-090-01): v0.9.0 definition — push-range denylist scan`

**Preconditions:** `SPEC.md`, `PLAN.md` and `TASKS.md` all carry `**Status:** Aprovado`
(operator). Working tree on `feature/v0.9.0`. **Check with the PM** whether the
purge-on-pick removal of `specs/backlog/push-range-denylist-scan.md` and
`specs/backlog/redact-foreign-context-names-at-qa-authoring.md` has been performed; if the
PM has acted, those deletions ride this commit (SPEC §7). If not, proceed and record the
pending purge in CLOSURE — never author the backlog change here.

**Write set (staging only — content already authored by `product-engineer`):**
`specs/releases/ACTIVE.md`, `specs/releases/v0.9.0/SPEC.md`,
`specs/releases/v0.9.0/PLAN.md`, `specs/releases/v0.9.0/TASKS.md`
(+ the two PM-authored backlog deletions **only if** they already exist in the tree).

**Description:** Stage exactly those paths — never `-A` over the shared tree — and commit.
Set `ACTIVE.md` phase from `DEFINITION` to `IMPLEMENTATION` in the same commit.

**Done criterion:** one commit containing exactly those paths; `ACTIVE.md` reads
`release: v0.9.0` / `phase: IMPLEMENTATION`.

**Parallelism:** none — first task.

---

- [x] **T-090-02 — [git] Milestone (a): merge, security review, push**

**Owner role:** dispatcher + `security-reviewer` · **Commit:** merge commit on `develop`

**Preconditions:** T-090-01 `[x]`. All three of SPEC/PLAN/TASKS `Aprovado`.

**Write set:** git refs only (`develop`), plus the security-reviewer handoff under
`.dadaia/handoff/dadaia-workspace/`.

**Description:** Per `dadaia-gitflow` milestone (a), in this order: merge `feature/v0.9.0`
into local `develop`; run a **diff-based** `security-reviewer` review of
`origin/develop..develop`; push `develop`. The push gate requires an APPROVED handoff keyed
to the pushed tip, plus the CI preflight.

**Done criterion:** `develop` pushed; APPROVED handoff covering the pushed delta; CI green.

**Parallelism:** none.

---

- [x] **T-090-03 — Git object port and adapter**

**Owner role:** software-engineer · **Commit:**
`feat(T-090-03): git object reader port + subprocess adapter`

**Preconditions:** T-090-02 `[x]`.

**Write set:** `dadaia_workspace/core/protocols/git_object_reader.py` (new),
`dadaia_workspace/infrastructure/git_subprocess.py` (or a new
`dadaia_workspace/infrastructure/git_objects.py` if that file would pass ~450 lines),
`tests/unit/infrastructure/test_git_object_reader.py` (new).

**Description:** Define `ScannedObject` (frozen: `path`, `sha`, `text`, `decodable`) and
the `GitObjectReader` Protocol in `core` (zero I/O). Implement the adapter: for a ref with
`local_sha` L and `remote_sha` S, run `git rev-list --objects L --not S` when S is non-zero
and resolvable locally, otherwise `git rev-list --objects L --not --remotes`; read each
blob, decode UTF-8, mark undecodable/oversized blobs `decodable=False` rather than raising.
Any non-zero git exit raises a typed error (SPEC FR6 row 2). Dedupe by object sha.

**Done criterion:** unit tests green over a temporary git repository built in `tmp_path`,
covering both range forms, a binary blob, a deletion sha, and a git failure.

**Parallelism:** may run concurrently with T-090-07 only.

---

- [x] **T-090-04 — Pure denylist matcher**

**Owner role:** software-engineer · **Commit:**
`feat(T-090-04): pure push-range denylist matcher`

**Preconditions:** T-090-03 `[x]`.

**Write set:** `dadaia_workspace/features/chokepoints/denylist_scan.py` (new),
`dadaia_workspace/infrastructure/privacy_check.py` (public accessors over the existing
private loaders — no change to matching semantics),
`tests/unit/features/chokepoints/test_denylist_scan.py` (new).

**Description:** `scan_objects(objects, terms, patterns, slugs)` → ordered hits
(`path`, `line`, `masked_term`, `source_layer`). Operator terms: case-insensitive
substring. Baseline patterns: compiled regex with `exclude_regex` honored. Foreign slugs:
word-boundary regex. Masking (`first…last`) happens **inside** the matcher so an unmasked
term never leaves it. Undecodable objects are skipped and counted. Write the self-slug
regression guard (SPEC A3.2) **before** the slug layer exists.

**Done criterion:** unit tests green for A3.1–A3.4, A4.1, A5.2 (unmasked term absent from
every returned string), A6.2 (skip counted); no `infrastructure` import in
`features/chokepoints/**`.

**Parallelism:** may run concurrently with T-090-07 only.

---

- [x] **T-090-05 — Wire the scan into the push decision**

**Owner role:** software-engineer · **Commit:**
`feat(T-090-05): scan the pushed range at the push gate`

**Preconditions:** T-090-04 `[x]`.

**Write set:** `dadaia_workspace/features/chokepoints/service.py`,
`dadaia_workspace/features/chokepoints/__init__.py`,
`tests/unit/features/chokepoints/test_push_gate_decision.py`,
`tests/unit/features/chokepoints/test_push_branch_policy.py`,
`tests/unit/features/chokepoints/test_push_denylist_scan.py` (new).

**Description:** `push_gate_decision` takes an injected object source. It computes the scan
ref set **independently of `review_refs`** (`service.py:344`) — every non-deletion ref,
tags included — and evaluates in order: malformed stdin → branch policy → **scan** →
security verdict. Compose the refusal per SPEC FR5: ref, `path:line`, short blob sha, masked
term + source layer, the law, the edit + rewrite-before-push remediation, `--no-verify` as
the only sanctioned bypass, first 10 hits then a remainder count. Never print the matched
line content.

**Done criterion:** unit tests green for A1.1–A1.5, A2.1–A2.4, A5.1–A5.4, A6.1; the
existing tag/deletion carve-out tests still pass unchanged.

**Parallelism:** may run concurrently with T-090-07 only.

---

- [x] **T-090-06 — CLI wiring and fail-closed boundary**

**Owner role:** software-engineer · **Commit:**
`feat(T-090-06): wire the range scan into ci push-gate-check`

**Preconditions:** T-090-05 `[x]`.

**Write set:** `dadaia_workspace/cli/commands/ci.py`,
`tests/contract/test_push_gate_wiring.py` (new),
`tests/integration/test_push_gate_denylist.py` (new).

**Description:** In `push_gate_check` (`ci.py:226`) build the adapter, load operator terms +
baseline patterns via the T-090-04 accessors, derive the foreign-slug set from
`<workspace>/repos/` **minus the pushed repository's own slug**, and pass them to the
decision. Git failure → refuse, naming the failure (FR6 row 2). No object source → refuse
(FR6 row 4). Emit the stderr mode line distinguishing "operator denylist + baseline" from
"baseline only" (A3.5). Integration test proves the FROZEN↔scan invariant on a temp repo:
`git mv` into `specs/_archive/` → clean scan; an edit of the same content → refusal (A4.2).

**Done criterion:** contract + integration tests green for A3.5, A4.2, A6.1, A6.3;
`dadaia ci preflight` green.

**Parallelism:** may run concurrently with T-090-07 only.

---

- [x] **T-090-07 — `--redact` output mode (FR8a)**

**Owner role:** software-engineer · **Commit:**
`feat(T-090-07): --redact output mode for doctor and context verbs`

**Preconditions:** T-090-02 `[x]`.

**Write set (disjoint from T-090-03…T-090-06):**
`dadaia_workspace/cli/commands/doctor.py`, `dadaia_workspace/cli/commands/context.py`,
a shared redaction helper module under `dadaia_workspace/cli/` (new),
`tests/unit/cli/test_redact_output.py` (new),
`tests/contract/test_cli_output_stability.py` (new or extended).

**Description:** Add `--redact` to `dadaia doctor`, `dadaia context list` and
`dadaia context show` (table and `--json`). Every Spec Context name and repo slug other than
the caller's resolved context becomes `[REDACTED-CONTEXT-<n>]`, ordinal by first appearance
and stable within one invocation. Apply **only at the render boundary** — services keep
returning true names. Default output stays byte-for-byte unchanged (A8.2). Covers the
`[stale-presence] context '<name>'` line (`features/spec_context/doctor.py:325`) and the
repo-coherence lines (`:453`, `:487`) as rendered by `dadaia doctor`.

**Done criterion:** tests green for A8.1–A8.4; existing CLI contract tests unchanged and
passing.

**Parallelism:** **sanctioned parallel** with T-090-03…T-090-06 (disjoint write sets). Not
parallel with anything else.

---

- [x] **T-090-08 — Redaction doctrine and projection (FR8b)**

**Owner role:** ai-engineer · **Commit:**
`docs(T-090-08): redaction-at-authoring doctrine for QA evidence`

**Preconditions:** T-090-07 `[x]`.

**Write set:** `dadaia_workspace/public/agents/qa-engineer.md` (canonical source) and the
resulting projections produced by `dadaia public stage` + `dadaia public install
--target all`.

**Description:** Add the doctrine line: diagnostic output transcribed into any authored
document — QA evidence, SPEC, CLOSURE, report, handoff — is captured with `--redact` or
masked by hand; a foreign Spec Context name is never pasted verbatim. Re-project and verify.

**Done criterion:** the line exists in the canonical source and in every projection;
`dadaia public doctor` reports `[ok] public-privacy` (A8.5).

**Parallelism:** none.

---

- [x] **T-090-09 — End-to-end journey and timing measurement**

**Owner role:** software-engineer · **Commit:**
`test(T-090-09): e2e planted-term push refusal + scan timing`

**Preconditions:** T-090-06 `[x]` and T-090-08 `[x]`.

**Write set:** `tests/e2e/test_push_denylist_journey.py` (new), plus timing captures under
`.dadaia/tmp/software-engineer/<YYYYMMDD>/`.

**Description:** Journey over a throwaway git repository in `tmp_path`: install the hooks,
commit a synthetic planted term, prove the `pre-push` refusal and its message shape, remove
the term, amend, prove the clean push. Separately measure the scan's wall clock over this
release's own push range and record the command with the figure (A7.3). The e2e file names
its owner, per the LARGE-tier rules.

**Done criterion:** journey green; measured figure < 2 s, captured for CLOSURE.

**Parallelism:** none.

---

- [x] **T-090-10 — qa-engineer review of the increment (flat alpha-close)**

**Owner role:** qa-engineer · **Commit:** review artifact committed to the branch

**Preconditions:** T-090-09 `[x]`.

**Write set:** `.dadaia/handoff/dadaia-workspace/` (+ `.dadaia/tmp/qa-engineer/<YYYYMMDD>/`
for captures); the review artifact committed to `feature/v0.9.0`.

**Description:** Verify the increment against SPEC FR1–FR9 acceptance ids one by one; run
the full suite; confirm test intents are declared (A9.3), no test was pruned to go green,
and the LARGE census did not silently grow past its declared handling. Apply the redaction
doctrine to this very artifact — it is the document class both incidents came from.

**Done criterion:** APPROVED verdict enumerating every acceptance id, or a REJECTED verdict
returning named defects to the implementer.

**Parallelism:** none.

---

- [-] **T-090-11 — Memory update (CLOSURE phase)**

**Owner role:** product-engineer · **Commit:**
`docs(T-090-11): memory — push-range scan and redaction posture`

**Preconditions:** T-090-10 `[x]` with APPROVED. `ACTIVE.md` phase set to `CLOSURE` **before
writing** (the gate allows `specs/memory/**` writes in `DEFINITION` and `CLOSURE` only).

**Write set:** `specs/memory/product/sdd/sdd-gate-v3.md`,
`specs/memory/quality-assurance.md`,
`specs/memory/product/platform/workspace-doctor.md`,
`specs/memory/product/platform/context-management.md`,
`specs/memory/architecture.md` (only if the port/adapter seam is judged structural),
`specs/memory/product/catalog.json` (regenerated **only** if a touched atom's `tldr`/
`summary` frontmatter changed — via `dadaia_workspace/public/scripts/generate-memory-catalog.py`).

**Description:** State the product as it is **now**: the push boundary scans the new objects
of the pushed range; tags are review-exempt and scan-covered; the fail-closed/fail-open
boundary; the FROZEN↔scan invariant quoted from SPEC FR4 (A4.3); `--redact` as part of the
doctor and context surfaces; the redaction-at-authoring posture in `quality-assurance.md`.
No changelog, history or version narrative in any atom.

**Done criterion:** `dadaia specs doctor` green on memory checks; no forbidden section
added; SPEC §5 satisfied file by file.

**Parallelism:** none.

---

- [ ] **T-090-12 — CLOSURE, dispositions, release archive, version bump**

**Owner role:** product-engineer (text) + software-engineer/dispatcher (**[git]** steps)
· **Commit:** `docs(T-090-12): close release v0.9.0`

**Preconditions:** T-090-11 `[x]`.

**Write set:** `specs/releases/v0.9.0/CLOSURE.md` (new), `specs/releases/ACTIVE.md`,
`pyproject.toml` (version), `CHANGELOG.md`, plus the release-directory move.

**Description:** In the finalization order **memory → CLOSURE → archive**:

1. Record the T-090-11 memory writes under `## Memory updates`.
2. Write `CLOSURE.md` per `dadaia-release-closure`: summary, tasks + commit SHAs,
   validations V1–V12 with evidence (including the FR7 timing figure and the
   masked-refusal capture), drifts, `## Dispositions` (both consumed backlog entries →
   `DELIVERED — v0.9.0`; state explicitly that **no bug and no audit** was picked), and
   `## Test dispositions`. Record as backlog returns: **commit-message scanning** (SPEC §4.2
   residual channel) and anything the increment surfaced. Record the purge-on-pick state:
   whether the PM removed the two entries before T-090-01, or whether the removal is still
   pending.
3. **[git]** `git mv specs/releases/v0.9.0 specs/_archive/releases/v0.9.0`; set `ACTIVE.md`
   to the next release or `release: none` / `phase: none`.
4. **[git]** Bump `pyproject.toml` and add the `CHANGELOG.md` entry per the gitflow
   contract.

**Done criterion:** `CLOSURE.md` complete under `specs/_archive/releases/v0.9.0/`;
`ACTIVE.md` no longer points at `v0.9.0`; `dadaia specs doctor` green.

**Parallelism:** none.

---

- [ ] **T-090-13 — [git] Milestone (b): ship**

**Owner role:** dispatcher + `code-reviewer` + `security-reviewer` · **Commit:** merge
commit + PR

**Preconditions:** T-090-12 `[x]`.

**Write set:** git refs only, plus the reviewer handoffs.

**Description:** Per `dadaia-gitflow` milestone (b), in order: `code-reviewer` six-axis pass
over the release delta; merge `feature/v0.9.0` into local `develop`; diff-based
`security-reviewer` review of `origin/develop..develop` — which is now itself subject to the
gate this release built; push `develop`; open PR `develop` → `main`; watch CI until every
job is green; merge.

**Done criterion:** PR merged to `main`; CI green; `feature/v0.9.0` no longer needed.

**Parallelism:** none — last task.
