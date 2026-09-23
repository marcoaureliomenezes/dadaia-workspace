# SPEC — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** product-engineer
**Opened:** 2026-09-12
**Origin:** backlog:gate-context-scope-antistall,one-canon-registry,continuous-reaper-reaped-zone,privacy-selfscan-scope
**Consumes:** gate-context-scope-antistall, one-canon-registry, continuous-reaper-reaped-zone, privacy-selfscan-scope

---

## 1. Problem and context

Candidate 2 — "the gate blocks three things" — takes the four enforcement surfaces the
2026-09-12 audit found stacked with special cases (grill rulings Q1/Q2/Q7/Q8/Q12/Q15
and the audit's C3/C5/GV-1..GV-15 findings) and cuts each back to one rule with one
home. The bug ledger is the evidence for every cut:

- **Gate.** Today the PreToolUse chain has seven BLOCK paths (root whitelist, venv
  rule 1, venv rule 2 "cache guard", PROTECTED sessions, LAW, MEMORY-by-phase,
  READ-mode self-block) and six path classes (`ADDITIVE MEMORY MUTATING PROTECTED
  LAW UNGATED`). The MEMORY branch reads `_RELEASE.json` through `Invocation.phase`
  — the gate reads a spec artifact although `DADAIA.md` §3.5 says it reads none — and
  every gate Stall in the ledger came from that read: `sdd-gate-memory-phase-resolves-
  empty…`, `minted-feature-branch-without-live-release-blocks-every-memory-write`,
  `context-bind-implementation-requires-release-id-stall-when-none-live` (open). Three
  of the seven BLOCK messages carry no executable fix (root whitelist, PROTECTED, venv).
- **Canon.** Root law, `.dadaia/` zones and the `states/` canon are one registry
  (`core/workspace_layout.py`); the `specs/` canon rows live in `features/specs/canon.py`;
  `DADAIA.md` §5.1/§5.3/§6.2/§8.5 are hand-typed copies. Verified after candidate 1:
  `canon.py` and §6.2 agree on membership (`releases_histo.jsonl` present, no
  `_superseded/`, no `consumed_backlog_histo`); the residual deltas are `canon.py`'s
  legacy `releases/<M.m.p>/RELEASE.json` rename row (SPEC-DOC-046, ADR 0007, absent
  from the law by design) and a stale `<alpha|rc>-N` docstring. Seven allowlist
  oscillation bugs (audit C3) are the history of two lists drifting.
- **Reaper.** `DoctorService` deletes slop outright, guards each call site
  separately (`_entries`, `_mtime`, `_remove`, `_guarded`, `_remove_dead_repo`), never
  walks `repos/<slug>/`, and the CRIT `doctor-ptr-gc-deletes-valid-lock-free-bind`
  (2026-07-12) is what a reaper that judges liveness by a lock it invented did to a
  valid bind. Its lineage (`context-release-leaves-lease-heartbeat-renewing`,
  `doctor-stale-lease-misdiagnosed-as-forgery`, `doctor-fix-aborts-whole-pass…`,
  `doctor-scan-raises-when-a-ttl-entry-vanishes-mid-walk`) is one family: deletion
  plus per-site guards.
- **Privacy scan.** Fifteen ledger records name the scan by id (`self-scan-baseline-
  drift-*` ×5, `push-gate-refuses-its-own-privacy-baseline-fixtures`, `privacy-
  baseline-noreply-local-part-not-carved-out`, `repo-self-scan-hits-alpha2-qa-
  historical-literal`, `t043-33-absolute-path-leaked-into-tasks-md`, `new-branch-push-
  loses-prior-published-denylist-amnesty`, `test-git-history-reader-fixture-email-not-
  on-selfscan-baseline`, `push-gate-foreign-slug-layer-flags-library-asset-and-bug-id-
  substrings`, `bug-record-write-once-evidence-fields-can-embed-selfscan-triggering-
  literal…`, `backlog-histo-writer-skips-write-time-denylist-redaction`, `push-gate-own-
  repo-slug-not-excluded…`); the audit counts 26 by component. Every resolution is a
  literal rewrite, a baseline row, an `exclude_regex` carve-out, a regex anchor or an
  amnesty rule. The structural cause: the scan's scope is every blob of the repository,
  so the team's own prose (specs, reviews, bug evidence) and its synthetic fixtures are
  policed with the rule meant for published assets; the fix always lands on the
  literal, never on the scope, and the next literal reopens the loop.

## 2. Objective

After candidate 2 the Gate blocks exactly three things and every BLOCK anywhere carries
one executable `fix:`; canonical names have one home rendered into the law; slop is
moved, never deleted, until its own TTL; and the privacy scan polices only what is
published — measured by contract tests that make each recurrence unrepresentable.

## 3. Scope (candidate 2)

- FR1 — **The Gate blocks three things.** Path classes are `ADDITIVE`, `MUTATING`,
  `PROTECTED` (PROTECTED = `.dadaia/sessions/` + projected law files; the LAW and
  UNGATED classes fold away, a workspace-root path outside a class is MUTATING). The
  SDD gate blocks (1) a PROTECTED write, (2) — with the session bound — a MUTATING
  write under `repos/<slug>/` whose slug is outside the Bind's **scope** = the bound
  Context's main repo plus its associated repos (`all_repos()`), the workspace-root
  `specs/` counting as in scope only for a self-hosting Context with no
  `repos/<slug>/specs/`; the root whitelist blocks (3) a new workspace-root entry. A
  slug no Context registers, an unbound session and a workspace-root path outside
  `specs/` are never scope-blocked (the gate cannot attribute them; fail-open, as
  today's no-context MUTATING). Deleted: the MEMORY class, `release_state.
  MEMORY_WRITE_PHASES`, `Invocation.release`/`.phase` and the gate's
  `_RELEASE.json` read, the READ-mode self-block and its `_READ_BLOCK_MESSAGE`
  (Q2), the LAW/UNGATED enum members. AC: `classify_path` has three outcomes; a
  write to `repos/B/src/x.py` while bound to Context A (B not in A's repo set) is
  BLOCKed with `fix: .dadaia/.venv/bin/dadaia context bind <ctx-owning-B>`; the same
  write unbound, or to `repos/B/specs/bugs/BUGS.jsonl` (ADDITIVE), is ALLOWed; a
  `specs/memory/**` write is ALLOWed in every phase (memory authorship is
  constitution §13 discipline, audited by pillar 3, never gated); no test fixture in
  `tests/unit/hooks/` writes a `_RELEASE.json` to drive the gate.
- FR2 — **Anti-stall invariant.** Every BLOCK from every enforcement point — the
  three gate blocks, the venv guard, `ci push-gate-check` (branch policy, refspec,
  malformed stdin, specs canon, denylist, git read failure), `ci verdict-check`, the
  release verbs, and the Doctor's exit 1 — carries exactly one line `fix: <command>`
  naming a single executable command (venv-rooted when it is `dadaia`). The Doctor
  renders `fix:` under every error-class finding from its rule's `fix_help`, which
  becomes mandatory for error-class rules (`dadaia doctor --fix`, `--fix --expired-only`,
  or the governance verb owning the record). Contract test
  `tests/contract/test_every_block_carries_a_fix.py` drives every BLOCK path through
  its public seam, asserts the one `fix:` line, and feeds that line back through
  `pre_gate.evaluate_payload` as a Bash payload asserting ALLOW — a BLOCK whose fix is
  itself blocked fails the suite (a Stall, CRITICAL by definition). AC: the test is
  RED on today's tree for the root-whitelist, PROTECTED, venv and `verdict-check`
  messages before any production change.
- FR3 — **Venv guard rule 2 dies; caches redirect by configuration.** `venv_guard.py`
  keeps rule 1 only (`dadaia`/`pip`/`python -m dadaia_workspace` outside
  `.dadaia/.venv/bin/`, message carries `fix:`); the cache guard (`_cache_guard_reason`
  and its seven helpers/constants) and its three test groups are deleted. Cache
  redirection lives in configuration: `[tool.pytest.ini_options] addopts` already
  carries `-p no:cacheprovider`; `[tool.ruff] cache-dir` and `[tool.mypy] cache_dir`
  are set so a bare `pytest`, `ruff check`, `ruff format --check`, `mypy --strict` run
  from the repo root writes no in-repo cache (mypy: `os.devnull` semantics are the
  implementer's portability proof — see §5); `ci preflight` drops the now-redundant
  per-command flags and `resolve_mypy_cache_dir`. AC: `tests/unit/features/ci_preflight/
  test_no_pollution.py` proves the bare commands, not the flagged ones, leave the tree
  clean; DADAIA §5.3's redirect line names configuration, not command flags.
- FR4 — **Bind without a release; the open bug.** Bug `context-bind-implementation-
  requires-release-id-stall-when-none-live` (HIGH) is fixed in this candidate by
  deletion: `dadaia context bind <ctx>` takes no `--release` (the release is a fact of
  `_RELEASE.json`, never of a session record; `new_binding_record` loses the field) and
  — per Q2's recommendation — no `--mode` (READ's block is gone with FR1, `REVIEW` was
  never read by any policy, `spec` was an alias; `--force` was a documented no-op);
  `--print-env` stays for the `eval $(…)` flow and emits `DADAIA_CONTEXT` and
  `DADAIA_SESSION_ID` only; `DADAIA_MODE` leaves resolution. AC (the bug's repro):
  `dadaia context bind dadaia-workspace` with no `specs/releases/<id>/` on disk exits 0
  and the next MUTATING write in scope is ALLOWed; `resolve_mode` and the session
  record `mode` field are deleted with their tests.
- FR5 — **One canon registry.** `core/workspace_layout.py` is the one home of every
  canonical name: the root law (`ROOT_ALLOWED_DIRS/FILES`, `INSTANCE_EXCEPTIONS`),
  `DADAIA_ZONES`, `STATES_CANON`, the `specs/` canon rows (`CanonEntry` data moved from
  `features/specs/canon.py`, which keeps `scaffold`, `scaffold_entry`, `release_new`,
  `check_tree` as the renderer/checker over the core rows) and the repo-tree
  exclusion set of DADAIA §5.3 (`REPO_TREE_EXCLUDED`: `.dadaia .venv .pytest_cache
  .mypy_cache .hypothesis .ruff_cache test-results playwright-report coverage
  .coverage`), today spelled in the law, `privacy_check._PUBLIC_ASSET_IGNORED_DIRS`,
  `pyproject.toml` and `REPO-DADAIA-1`. `dadaia public stage` renders `<!-- root -->`,
  `<!-- repo-excluded -->`, `<!-- specs-canon -->` into `DADAIA.md` §5.1/§5.3/§6.2
  through the existing `render_registry_tables` (§8.5 already names the registry);
  the gate, the Doctor, the scaffold and the push-gate canon scan consume the rows.
  `tests/contract/test_zone_registry.py`'s "no second list" ratchet widens to root
  names, specs canon members and the exclusion set, over the package and the
  projected law. AC: the staged `DADAIA.md` §6.2 table equals the registry row for
  row (the zone-table test's shape); a literal holding three or more canonical names
  outside `core/workspace_layout.py` fails the ratchet.
- FR6 — **Continuous reaper, `reaped/` zone.** One traversal primitive,
  `features/spec_context/sweep.py` (`walk` + `stat` + `move` + `remove`, one guard: a
  symlink is never followed, an entry that vanished mid-walk is absent not an error,
  a location outside the workspace is skipped, every OSError is one `skipped` action),
  replaces the five per-site guards in `doctor.py`. The workspace section's scan widens
  to the top of every registered repo (main + associated, ALIVE) and, at any depth
  inside a repo, the `REPO_TREE_EXCLUDED` names and a nested `.dadaia/` — never a
  source entry (canonical at a repo top = anything not on that set). The reaper MOVES
  every `slop` and INV-5 leftover to `reaped/<YYYYMMDD>/<workspace-relative-path>` (a
  new EPHEMERAL zone row, 7-day TTL, clock starting at the move — Q3 decides
  `.dadaia/reaped/` vs the ruled `.dadaia/tmp/reaped/`); direct deletion is reserved to
  TTL expiry (`expired` entries of every TTL zone, `reaped/` included). It runs at
  SessionStart (the existing `doctor --fix --expired-only --quiet` lane, whose scope
  becomes "the workspace reaper": seed missing, move slop, delete expired) and on
  `sdd_post_gate`'s existing throttle beside `presence.gc`; `dadaia doctor --fix`
  runs the same function then the specs fixes. It never touches: session records and
  presence (their own reapers), a registered repo directory, `references/`, `.venv/`,
  manifest entries, instance exceptions, a zone's `AGENTS.md`. The workspace section
  lists held entries as `WS-reaped-reaped` lines (finding verdict `reaped`, canonical,
  printed: origin path, days left). Installed git hooks: for every ALIVE repo, `.git/
  hooks/{pre-commit,pre-push}` byte-differing from `public/scripts/` is `HOOKS-DRIFT-1`
  (error class, `fix: … ci install-hook --force`). `REPO-DADAIA-1` (specs section) is
  deleted, covered by the walk. AC: the CRIT bug's repro (bind, `doctor --fix`,
  `context show`) leaves the bind intact and moves nothing under `sessions/`; a
  `.pytest_cache/` at `repos/<slug>/tests/` is moved at the next throttled
  PostToolUse and expires 7 days later; nothing under `repos/<slug>/` outside the set
  is ever moved; `scan()` and `fix()` share one walk (no second `iterdir`).
- FR7 — **Privacy scan at the publication boundary — which is the push.** This
  repository is public (README: MIT, GitHub link), so every pushed blob is published:
  the full layer set (operator denylist, structural baseline, foreign slugs, secret
  shapes) applies to every tracked path, unchanged. The 26-bug loop (every fix a
  literal/baseline/regex edit) ends at its root instead: the 23 hand-kept rows of
  `_TESTS_SCOPE_BASELINE` (`tests/integration/test_repo_self_scan.py`) are deleted
  after each fixture literal they tolerate is rewritten to a synthetic value that
  matches no pattern (`example.invalid` hosts, RFC 5737 addresses, `AKIAEXAMPLE`-free
  key shapes, no `@` in fake mail); every `privacy_baseline.json` `exclude_regex`
  whose rationale names a test or spec path is deleted the same way (fix the literal,
  delete the row); the prior-published amnesty stays. A test fixture that needs a
  realistic secret shape builds it at runtime from parts, never as a literal.
  gitleaks (`secret-scan.yml`, already triggered on PRs to `main` and `develop`) becomes
  a required status check on `develop` (branch protection, whole required-checks list
  re-supplied — recorded in the `_RELEASE.json` log). AC: `_TESTS_SCOPE_BASELINE` and
  every path-scoped `exclude_regex` are gone; `test_repo_self_scan.py` asserts zero
  hits over the tracked tree with no tolerated-pairs list anywhere;
  `test_no_allowlist_or_sanctioned_terms_constant_in_matcher_source` stays green; a
  private hostname under `specs/**` or `tests/**` is refused at push exactly as under
  `dadaia_workspace/**`.
- FR8 — **Law, skills, entities, glossary — only where behavior changed.** DADAIA
  §3.1–§3.5 (three blocks, three classes, no phase, Bind = scope, `fix:` on every
  BLOCK), §5.1/§5.3/§6.2 rendered, §7.4 (config not flags), §8.2, §8.5 (move not
  delete; `reaped/`), §10.2 glossary (path class, zone, finding verdict, bind, scope,
  reaped, publication boundary, stall); `.dadaia/AGENTS.md` §4; `scaffold/memory/
  AGENTS.md` line "MEMORY path class"; `entities/registry.json` (`venv-guard`,
  `sdd-gate` mandates); skills `dd-ai-eng-knowhow`, `dd-task-manager`, `dd-cli-library`,
  `dd-spec-navigator`, `dd-workspace-doctor`, `dd-bug-registration`,
  `CONSUMER_VALIDATION_RECIPE.md`; agent `software-engineer.md` (`-p no:cacheprovider`);
  `kimi-code/AGENTS.md`; behavior-map hashes; re-projection; `CONTEXT.md` (Path class
  three, Zone `reaped`, Finding verdict `reaped`, Bind carries scope, new entries
  Scope, Reaped, Publication boundary, Sweep). AC: `grep` proves no `MEMORY` path
  class, `cache guard`, `--mode read`, `--release` bind option or "slop dies only by
  `--fix`" sentence survives in `public/`, skills or `CONTEXT.md`.
- FR9 — **Closure.** Memory atoms `sdd-gate-v3`, `context-management`,
  `workspace-doctor`, `workspace-init`, `spec-context-project`,
  `public-asset-distribution`, `ARCHITECTURE` Part 2 (one-decider rows: release phase
  vocabulary, `workspace_layout`, chokepoints, new `sweep` row),
  `QUALITY`/`TECHSTACK` where they name the cache flags; `CHANGELOG.md [0.4.7]`
  candidate 2; full preflight; `dadaia doctor` 100 % on this instance; the gitleaks
  required-check action recorded; candidate CLOSURE.

## 4. Out of scope

- Bug policy, `backlog exit`, `audit close`, telemetry events, law/skill dedupe
  (`dd-workspace-doctor` deletion, RC-FLOW folds) — candidate 3.
- Documentation derived from memory, distribution metadata — the docs candidate.
- Deleting advisory presence (backlog idea `delete-advisory-presence`); presence
  upsert and its throttled warning are untouched.
- The eight deferred standards replacements (backlog ideas); the verdict file model.
- A new ADR: no Part-1 principle changes (P-09's Invocation shrinks in fields, not in
  ownership; P-14/P-15 untouched). If review finds a principle moved, the decision
  record lands in the same commit.

## 5. Dependencies and risks

- Q1–Q5 answered by the PM under the operator's 2026-09-12 directive (each is one option
  or one registry row, reversible in one commit; the operator may overrule): Q1 only
  `repos/<slug>/` is scope-judged, root non-repo paths are in scope under a bind; Q2
  `--mode`/`--release`/`--force`/`--reason` deleted — bind is one verb, READ's block
  dies with the three-block rule; Q3 `.dadaia/reaped/` is its own zone row (7 d), not a
  TTL override inside `tmp`; Q4 superseded — the repository is public, so the full tier is every pushed path
  (FR7); Q5 canonical at a repo top =
  anything not in `REPO_TREE_EXCLUDED`, an untracked source entry is never moved.
- FR3 mypy: `cache_dir = /dev/null` is honoured through `os.devnull` on POSIX only; the
  implementer proves the Windows leg (CI typecheck runs on ubuntu) or keeps the env
  redirect for Windows shells and says so in the `size` log entry.
- FR6 walks every registered repo on a throttle inside a hook: bounded by pruning at
  `.git`, `.venv`, `node_modules` and every excluded name; the implementer records the
  walk's wall time on this instance (target under 200 ms) in the closure `size` entry.
- FR6 moves across filesystems fall back to copy+remove inside the primitive — one
  place; a failed move is one `skipped` action, never a partial delete.
- FR7 keeps the full scan everywhere because the repository is public (the earlier
  draft assumed private); the deletion target is the tolerated-pairs baseline, reached
  by fixing fixture literals at their root, never by narrowing what a push publishes.
- FR5 moves ~200 lines of rows into `core`; `test_core_file_io_purity` is unaffected
  (pure data), `lint-imports` contracts unchanged (features → core edge exists).
- Net: deletions (MEMORY/LAW/UNGATED classes, phase read, READ block, cache guard +
  helpers, `--mode/--release/--force/--reason`, `resolve_mode`, `MEMORY_WRITE_PHASES`,
  five per-site guards, INV-5 rmtree, `REPO-DADAIA-1`, `_TESTS_SCOPE_BASELINE`, prose
  carve-outs, preflight flags, `resolve_mypy_cache_dir`, `_PUBLIC_ASSET_IGNORED_DIRS`)
  against additions (scope rule, `fix:` grammar + one contract test, `sweep.py`,
  `reaped` row, three placeholders). Production net is expected
  negative; the closure `summary` entry applies the deletion test to every addition.
