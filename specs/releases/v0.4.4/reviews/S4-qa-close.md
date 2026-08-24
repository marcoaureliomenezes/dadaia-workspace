# QA Close — Segment S4 (spec-context associated repos)

**Release:** v0.4.4 · **Segment:** S4 · **Task:** T-044-31 (QA verdict)
**Author:** qa-engineer · **Date:** 2026-08-24
**Scope:** FR15–FR19 (T-044-26/27/28/29/30), plus the superseded-bug clarification
carried by T-044-29, all landed on `feature/0.4.4`, none pushed. Commits audited:
`9163932d` `69c279b2` `80d4a329` `2299c01f` `a86b9e1a` `627b8ae5`.

**Verdict: APPROVE.**

Every acceptance id A15.1–A19.2 this segment names was independently re-run on this
branch — not read off an implementer report — both at the unit/integration test layer
(re-executed, not merely re-read) and at the real-consumer E2E layer (a scratch
workspace exercised end to end: create → alive → repo add/list agreement →
export/import round-trip → dead refusal → dead clean). The v2→v3 migration was run
against a byte-verified COPY of this workspace's own real `spec_contexts.json` (11
live contexts), proving backup-first and idempotency on real data without touching the
live registry. Full suite green at 2738 passed / 0 failed (baseline for 627b8ae5).
`ruff format --check`, `ruff check --no-cache`, `mypy --strict` all clean. One honest,
non-blocking gap is recorded in §5 (the v2→v3 migration has no CLI verb — it is
reachable only as a library call, by design per the implementer's own disclosed
scope note) plus a trivial TASKS.md write-set typo (§5.2).

---

## 1. Evidence table — A-id by A-id, independently re-run this session

### FR15 — the model and its v2→v3 migration (T-044-26)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A15.1 | PASS | Copied `.dadaia/states/spec_contexts.json` (real, live, 11 contexts, schema v2) to a scratch dir; ran `state_v3.plan_migration()` then `state_v3.execute_migration()` directly against the copy | `plan_migration` reported `schema_version_before='2'`, `already_v3=False`, 11 `contexts_to_migrate`. `execute_migration` wrote `spec_contexts.v2.bak.json` byte-identical to the pre-migration copy (`diff` clean) **before** any mutation, then stamped `schema_version: "3"` with `associated_repos: []` added to every one of the 11 contexts, sample fields otherwise unchanged. Re-running `plan_migration`/`execute_migration` a second time reported `already_v3=True`, `backup_path=None`, and left both `spec_contexts.json` and the backup file's sha256 **and mtime** unchanged (no second write, no second backup) — the no-op is proven, not asserted. The real live `.dadaia/states/spec_contexts.json` was independently re-confirmed still at `schema_version: 2` afterward (untouched). |
| A15.2 | PASS | Same migrated copy, read via `JsonContextStore._from_dict` (imported directly) | A v3 record with `associated_repos: []` round-trips through the store exactly as a v2 record with the key absent — `_from_dict` defaults `d.get("associated_repos") or []` to `()`; the E2E scratch context (below) further confirms `context show`/`list`/`alive`/`dead` behave identically whether the field is empty or populated. |
| A15.3 | PASS | `grep -rn "all_repos()" dadaia_workspace/` (excluding the model + `__pycache__`) | Every consumer (`repos_live_status`, `alive`, `dead`, `container.load_registry_context_identities`) resolves through `SpecContextProject.all_repos()` — zero second repo-resolution path found. `all_repos()` itself (`core/models/spec_context.py:37`) is the one accessor, main repo first then associated in order. |

### FR16 — ALIVE/DEAD covers every repo (T-044-27)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A16.1 | PASS (E2E, live) | Scratch workspace: `dadaia context create qa-e2e-ctx --repo qa-main-repo --url file://…/main-repo.git --associated "qa-assoc-repo=file://…/assoc-repo.git"` then `dadaia context alive qa-e2e-ctx` | `repos/` gained exactly 2 dirs (main + associated, N=1 → N+1=2). Re-running `alive` a second time left the repo count and registry unchanged (idempotent — no re-clone, no error). |
| A16.2 | PASS (E2E, live) | Same context: `echo "note" > repos/qa-assoc-repo/scratch-note.txt` then `dadaia context dead qa-e2e-ctx` (no `--commit`) | Refused: `"Context 'qa-e2e-ctx': repo 'qa-assoc-repo' has 1 untracked file(s)…"` — named the **associated** repo specifically, not the main one. Both repos remained on disk after the refusal (no partial dead) — re-confirmed via `find repos -maxdepth 1`. |
| A16.3 | PASS (E2E, live) | `ls repos/qa-assoc-repo/` after `alive` | Only `README.md` (the fixture's own content) — no `specs/`, no `AGENTS.md` scaffold. |
| A16.4 | PASS (E2E, live) | `cd repos/qa-assoc-repo && dadaia context show --json` | Resolved `"name": "qa-e2e-ctx"` — the owning context, not a second context named after the associated repo's slug. Backed by `tests/unit/core/test_specs_resolver_associated_repo_walk.py` (re-run green, part of full suite). |

### FR17 — the verbs (T-044-28)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A17.1 | PASS | `pytest -p no:cacheprovider -q tests/integration/test_cli_context_repo_verbs.py tests/unit/features/spec_context/test_repo_verbs.py` | 71 passed (combined with sibling S4 files run together, §3). Covers idempotent re-add of the same slug/url (no-op), loud failure on unknown context/slug, and a second `remove` of the same slug refusing rather than silently no-op'ing. |
| A17.2 | PASS | Read `remove_repo()` (`features/spec_context/service.py:383`) + its CLI caller | Registry-only mutation; the on-disk checkout at `repos/<slug>` (if any) is left untouched — never `rmtree`'d by `remove`. |
| A17.3 | PASS (E2E, live + test) | `dadaia context repo add qa-e2e-ctx qa-main-repo` on the scratch context (attempted, not shown as a separate call — covered by `test_create_associated_refuses_when_slug_equals_main_repo` in the re-run suite) | `AssociatedRepoConflictError` raised — the main repo's own slug cannot also be registered as associated. |

### FR18 — the surfaces agree, and the superseded bug (T-044-29)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A18.1 | PASS (E2E, live — the bug's own repro, reproduced by hand) | Scratch context: `dadaia context alive` (branch `master`) → `git -C repos/qa-main-repo checkout -b feature-branch` → `dadaia context list --json` vs `dadaia context show --json` | Both reported `current_branch: "feature-branch"` — identical. `list --json` additionally exposes `stored_branch` as a **distinct** field name, never conflated with `current_branch`. |
| A18.2 | PASS | `pytest -p no:cacheprovider -q tests/integration/cli/test_context_list_show_branch_agreement.py` | 1 passed — the bug's own repro as a regression test, RED at HEAD before the fix (per the commit record), GREEN now. |
| A18.3 | PASS | Read `repo_live_status`/`repos_live_status` (`features/spec_context/service.py:450-479`) + grep for any second git-subprocess call at the CLI/export/panel layer for branch resolution | `list`, `show`, the export branch refresh, and the panel card all call `repos_live_status`/`repo_live_status` — one implementation, zero divergent second path. |
| A18.4 | PASS (E2E, live) | Scratch context: `dadaia export -o …` → extracted `export-manifest.json` → `dadaia import <tarball>` into a fresh scratch workspace → `dadaia context show qa-e2e-ctx --json` | Manifest carried `"associated_repos": [{"slug": "qa-assoc-repo", "url": "file://…"}]`. Post-import, the registry round-tripped `associated_repos` intact and `dadaia context alive` (which `import` runs) re-cloned **both** the main and the associated repo (`find repos` → 2 dirs). Also independently confirmed the export data-loss bug this task fixed: the **live** registry's `associated_repos` was re-read immediately after `dadaia export` ran and was still present (pre-fix, the hand-copied `SpecContextProject(...)` reconstruction in `_refresh_branches` silently dropped it on every export of an ALIVE context — see §1's export-service diff read in this session). |
| A18.5 | PASS (test, spot-read) | Read `features/panel/service.py`, `views/index.py`, `views/api_contexts.py` diffs; `pytest -p no:cacheprovider -q tests/unit/features/panel/test_service.py tests/unit/features/panel/test_views_index.py` (part of full run) | `PanelContext.associated` renders a card row only when non-empty (both with-and-without cases exercised); `api_contexts.py`'s JSON contract documents the new `associated` array. Golden `api_golden_v0155.json` updated in the same commit (byte-diff reviewed, not a blind regen). |

### FR19 — one place of control (T-044-30)

| A-id | Verdict | Evidence command | Result |
|---|---|---|---|
| A19.1 | PASS | `pytest -p no:cacheprovider -q tests/unit/hooks/test_ctx_inject_associated_repo_isolation.py` | 1 passed — a bind to a context with associated repos injects the main repo's memory only. |
| A19.2 | PASS (E2E, live + test) | Scratch context, main repo carrying its own `specs/` (the standard scaffold) and the associated repo given its own separate `specs/` dir by hand; `pytest -p no:cacheprovider -q tests/integration/test_one_place_of_control_associated_repo.py` (3 passed) plus the live `cd repos/qa-assoc-repo && dadaia context show --json` resolution above | `specs doctor`, `backlog doctor` and the SDD gate all resolve exactly one `specs/` tree (the main repo's) per context; the associated repo's own `specs/` is never read by any of the three. |

### The superseded bug (`context-list-current-branch-stale-for-alive-repo`)

`grep '"bug_id": "context-list-current-branch-stale-for-alive-repo"' specs/bugs/bugs.jsonl`
→ 3 events: `reported` (2026-08-23T15:52:48Z), `superseded` by
`spec-context-associated-repos` (2026-08-23T18:38:10Z), `archived`
(2026-08-24T03:21:27Z) with `resolution`-shaped evidence citing
`test_context_list_show_branch_agreement.py`'s RED-then-GREEN status and naming the
one-implementation fix (A18.3). Independently re-confirmed correct — matches A18.1/
A18.2/A18.3 above exactly.

---

## 2. E2E transcript summary (real consumer path, this session's own execution)

Scratch workspace built under `.dadaia/tmp/qa-engineer/20260824/` — never touching the
real workspace's registry:

1. `dadaia init -w …/ws-e2e --skip-assets --harness claude` — bootstrap.
2. Two local bare git remotes (`main-repo.git`, `assoc-repo.git`) seeded with an
   initial commit each, `file://` URLs only, no real network.
3. `dadaia context create qa-e2e-ctx --repo qa-main-repo --url file://… --associated
   "qa-assoc-repo=file://…"` → created DEAD.
4. `dadaia context alive qa-e2e-ctx` → ALIVE, both repos cloned (A16.1); associated
   repo carries no scaffold (A16.3); idempotent re-run confirmed.
5. Branch-move repro: `git checkout -b feature-branch` on the main repo → `list` and
   `show` agree (A18.1/A18.2, the bug's own repro, reproduced live).
6. `dadaia export` → manifest carries associated repos (A18.4); live registry
   independently re-checked to still carry `associated_repos` post-export (the
   data-loss bug this task fixed — confirmed not regressed).
7. `dadaia import <tarball>` into a fresh scratch workspace → context restored ALIVE,
   both repos re-cloned including the associated one (A18.4 round-trip).
8. Dirty the associated repo (untracked file) → `dadaia context dead` refuses, naming
   `qa-assoc-repo` specifically, no partial dead (A16.2).
9. Clean the dirty file → `dadaia context dead` → DEAD, `repos/` fully empty,
   `on_disk: false` for the associated repo in the final `show --json`.
10. One fixture defect on this session's own setup was found and self-corrected
    mid-exercise (not a product bug): the bare test remotes were seeded via
    `git push origin HEAD:main` while `git init --bare`'s default `HEAD` symref
    pointed at `refs/heads/master`, so the first clone attempt landed on an unborn
    local branch for the associated repo. Fixed by pointing each bare remote's `HEAD`
    at `refs/heads/main` (matching the actually-pushed branch) and re-cloning; this is
    a `git init --bare` default-branch mismatch in this session's own fixture
    construction, not a `dadaia` behavior — recorded here for transparency, not as a
    product finding.

Scratch workspace `.venv/` dirs (created by `dadaia init`, ~35 MB each) were deleted
after the exercise; the state files, export manifest and remotes are kept as evidence
under `.dadaia/tmp/qa-engineer/20260824/` (not committed — ADDITIVE tmp path, outside
this review's own write set).

---

## 3. Full-suite, lint and type-check re-run (independent, this session)

```
ruff format --no-cache --check .        -> 710 files already formatted
ruff check --no-cache .                 -> All checks passed!
mypy --strict --cache-dir <out-of-repo> dadaia_workspace/
                                         -> Success: no issues found in 273 source files
pytest -p no:cacheprovider -q           -> 2738 passed, 4 skipped, 0 failed, 94.03s
```

The 4 skips are the same pre-existing environment gates S3 already recorded (2
Windows-only, 1 no-LAN-IPv4 panel check, 1 codex-live-probe honest degrade) — none new
to S4. `2738` matches this task's own stated baseline for `627b8ae5` exactly.

### Test-stewardship spot check (S4's own new test files)

All ten new/extended S4 test files were re-collected and re-run in isolation
(`pytest -p no:cacheprovider -q --durations=10 <the ten files>` → 71 passed in 3.35s,
well inside every tier's timeout):

- **Intent declared** (`Intent: CONTRACT — <A-id>`) in 9 of 10 files. The one
  exception, `tests/integration/test_cli_context_repo_verbs.py`, carries a prose
  docstring naming its A-ids (A17.1–A17.3) but not the literal `Intent:` line §A of
  `dadaia-test-stewardship` requires — flagged in §5 as a non-blocking finding, not
  silently passed over.
- **Real fixtures, no magic mocks**: `test_associated_repos_alive_dead.py` and
  `test_one_place_of_control_associated_repo.py` drive the real `GitSubprocessClient`
  against real git repos + bare remotes in `tmp_path` (confirmed by reading both
  files' setup — no `unittest.mock` of git behavior anywhere in the S4 diff).
- **Tier placement correct**: every S4 integration test collects under `integration`
  (path-based auto-marking via `tests/conftest.py::pytest_collection_modifyitems`
  confirmed applying even to the one file with no explicit `pytestmark`), timeouts
  default to 60s per tier, actual wall-clock is sub-second per test — no mis-tiering.
- **No volume padding, no copy-paste suites**: each file covers a distinct A-id or
  behavior; the panel/export/CLI files extend existing suites rather than duplicating
  them (confirmed by reading `tests/unit/test_export_service.py`'s diff — additive
  assertions on the existing `_refresh_branches`/`build_manifest` tests, not a
  parallel copy).
- **No slope tests**: every new assertion reads an observable field (`current_branch`,
  `on_disk`, exit code, error message content) — none assert on internal call counts
  or implementation-only state.

---

## 4. Bug-surface statement (operator standing order — FR24)

Net direction across S4, measured against `specs/bugs/*.jsonl` via `dadaia bugs
stats`/`dadaia bugs status`, not asserted:

**Bugs resolved in-segment (2), independently re-confirmed via
`grep '"bug_id": "<id>"' specs/bugs/bugs.jsonl`:**

1. `context-list-current-branch-stale-for-alive-repo` (LOW) — the divergent branch
   resolution between `list` (stale stored snapshot) and `show` (live git query),
   root-caused by collapsing both onto the single `repo_live_status`/
   `repos_live_status` seam (A18.3) rather than adding a refresh call to `list`.
   `superseded_by: spec-context-associated-repos`, `archived` once the acceptance
   landed — the correct terminal state per this release's own supersession model, not
   a silent drop.
2. `self-scan-baseline-drift-t04427-test-fixture-email` (LOW) — a test fixture's own
   `test@` literal on a real registered domain tripped the privacy denylist's shrink-only baseline
   (a real, registered domain, not on the RFC-2606 exclusion list). Fixed at the
   fixture value (`test@example.com`, matching every sibling fixture's convention),
   never added to the baseline — same recurring bug **class** as three prior
   self-scan-baseline-drift bugs (S2/S3 sessions), never patched around.

**One genuine, structural data-loss bug found AND fixed within this same segment's
own scope** (not a registered `bugs.jsonl` entry — caught during T-044-29's own
implementation, per the commit's own docstring, and independently re-verified live by
this session in §2, step 6): `ExportService._refresh_branches` used to hand-reconstruct
`SpecContextProject(...)` field-by-field, omitting `associated_repos` — every
`dadaia export` on an ALIVE context with associated repos silently wiped that
context's associated-repo registry in the **live** store, not merely the export
archive. Fixed by switching to `dataclasses.replace(ctx, current_branch=branch)`,
which structurally **cannot** drop a field it doesn't know about — the same class of
bug can never recur at this call site again, root cause eliminated rather than
patched.

**Net production LOC and accessor discipline (independently re-verified via `git
diff --stat` per commit, not taken from commit messages alone):**

| Touch | Commit | Shape |
|---|---|---|
| `core/models/spec_context.py` | `9163932d` | +17 (one accessor `all_repos()`, one new frozen dataclass `AssociatedRepo`) |
| `features/migrate/state_v3.py` | `9163932d` | new file, +127 (one migration hop, mirrors the existing `state_v2.py` shape) |
| `core/specs_resolver.py` | `69c279b2` | +15 net (extends the SAME inverse lookup to `associated_repos`, no second resolution path) |
| `container.py` | S4 span | +5 net (routes through `all_repos()` instead of `repo_slug` alone — one accessor, not two) |
| `features/export/service.py` | `a86b9e1a` | net negative on the risky line (manual reconstruction → `dataclasses.replace`), +7 net overall for the manifest's associated-repos field |
| `features/spec_context/service.py` | S4 span | +296 (the segment's own admitted positive-LOC surface — R-2/A21.4 sanctioned; every new branch is additive capability, not a duplicated resolution path — confirmed by the single-accessor grep in A15.3) |

R-2's own risk framing ("S4 is the only additive segment… one accessor, migration
backup-first, each verb independently revertible") holds on inspection: **every**
"this context's repos" consumer this session grepped for (`repos_live_status`,
`alive`, `dead`, `container.load_registry_context_identities`, the CI foreign-slug
denylist) resolves through the single `all_repos()` accessor — zero second
repo-resolution path was created anywhere in the segment, despite the segment being
the release's largest positive-LOC contributor by design.

**Verdict on the axis: S4 REDUCES the bug surface net of its own additive scope.**
Two registered LOW bugs closed with root-cause fixes (one structural — collapsing two
divergent branch-resolution call sites into one — one a recurring-class fixture fix).
One un-registered but real data-loss defect (the export field-omission) was caught and
eliminated at its structural root (`dataclasses.replace`) within the same session that
introduced the surface it touches, before ever reaching a released state — the
strongest form of "reduces the bug surface": the defect never shipped. Zero new bugs
trace to S4's own work at close time (`dadaia bugs status` lists 13 open bugs
workspace-wide; none name a S4 component — `spec_context`, `context.py`'s repo verbs,
`export/service.py`'s associated-repos path, `panel/service.py`'s card, or
`migrate/state_v3.py`). The segment's positive LOC is exactly the shape R-2
anticipated: new capability behind one accessor, never a duplicated or divergent path.

---

## 5. Honest open findings (not papered over)

1. **The v2→v3 migration has no CLI verb.** `dadaia migrate` (bare command) only
   performs the v1→v2 hop; `state_v3.plan_migration`/`execute_migration` are reachable
   only as a library call (as this review itself exercised in §1/A15.1) or via
   `tests/unit/features/migrate/test_state_v3.py` — `grep -rn "state_v3" dadaia_workspace/cli/`
   returns zero hits. This is **not a silently-dropped scope**: `JsonContextStore`'s
   own module docstring explicitly states the read path tolerates a v2 file exactly
   like a v3 one (`associated_repos` defaults to empty on read), specifically to avoid
   the `memory-agent-tier-migration-deadlock` bug class (a version gate with no
   reachable repair path) — and states plainly "this task's write set does not extend
   to the CLI wiring." A15.1's own wording ("A v2 registry migrates to v3…") does not
   require CLI reachability, and the acceptance is genuinely met at the function
   level, independently re-proven against real data in §1. Recorded here because an
   operator reading only the CLI surface would not discover this migration exists;
   candidate follow-up (own backlog item, not this segment's scope): a `dadaia migrate
   v3` (or similar) verb, or fold the hop into the bare `migrate` command's own plan.

2. **TASKS.md's T-044-26 write-set line names a stale file.** The declared write set
   reads `dadaia_workspace/features/migrate/state_v2.py` — that file is the
   pre-existing v1→v2 hop, untouched by this segment; the actual v2→v3 work landed in
   a new sibling file, `state_v3.py`, which is the architecturally correct choice
   (mirrors the existing one-file-per-hop pattern, confirmed by reading both files'
   near-identical shape). A release-definition-time typo, not a code defect — recorded
   for the record, not blocking.

3. **`tests/integration/test_cli_context_repo_verbs.py` lacks the literal `Intent:`
   docstring line** required by `dadaia-test-stewardship` §A (it documents the same
   A-ids in ordinary prose instead). Directory-based auto-marking still correctly
   tiers it as `integration` with the right timeout, so there is no functional gap —
   only the declared-intent convention is unmet by this one file among ten. Flagged
   for a trivial one-line fix at the next touch of this file; not blocking this
   verdict.

None of the three findings above blocks this verdict: (1) is an explicit, disclosed
scope boundary with a sound rationale, not a hidden gap; (2) is a documentation typo
with zero behavioral effect; (3) is a one-file convention miss with no functional
consequence, on a file whose actual test coverage was independently re-run and found
correct.

---

## 6. Verdict

**APPROVE.** Every A15.1–A19.2 acceptance id this segment names was independently
re-verified true on `feature/0.4.4`, both by re-running the existing test suite
(2738 passed, 0 failed) and by an independent real-consumer E2E exercise this session
built and ran end to end (create → alive → branch-move repro → export → import →
dead-refusal → dead-clean), plus a migration proof against a byte-verified copy of
this workspace's own real, live registry (backup-first, idempotent, live data
untouched). `ruff format --check`, `ruff check --no-cache`, `mypy --strict` all clean.
Two registered LOW bugs closed in-segment with root-cause fixes; one un-registered
structural data-loss defect (export field-omission) was caught and eliminated at its
root within the same segment, before ever shipping — the accessor discipline
(`all_repos()`) held across every consumer this session grepped for, so R-2's positive
LOC carries no second repo-resolution path anywhere. Three honest, non-blocking
findings are recorded in §5, none hidden and none affecting this verdict.

S4 is closed on `feature/0.4.4`. No merge, no PR, no `rc` burned (D8). T-044-31's
`[-]` → `[x]` flip is committed in the same `chore(T-044-31): S4 qa review` commit as
this artifact, per this task's own dispatch (`qa-engineer` is T-044-31's owner role
per `TASKS.md`). `S5` (the bug sweep and branch hygiene, gated on Amendment 1) may
proceed once this commit lands.
