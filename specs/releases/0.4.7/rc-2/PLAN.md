# PLAN — Release: 0.4.7

**Status:** Aprovado
**Release ID:** 0.4.7
**Owner:** product-engineer

---

## Design (codebase-design vocabulary)

Four modules grew by layering; each fix in their ledgers added a branch, a guard, a
carve-out or a row. Candidate 2 replaces, never layers: every FR names the seam it
cuts, what it deletes, and the deletion-test outcome of the one thing it adds.

- **Seam 1 — `gate_policy.classify_path` / `evaluate`** (FR1, FR2, FR4). The interface
  shrinks from `(rel_path, ctx, phase, session_id, release, mode, …)` to
  `(rel_path, bind, target_slug, session_id, …)`: a `Bind` value (context name + repo
  slugs, resolved once by `core.invocation` from the session record or
  `DADAIA_CONTEXT`) replaces three loosely coupled strings. Deletion test on the MEMORY
  branch: remove it and nothing reappears — memory authorship is constitution §13
  discipline audited by pillar 3, and the constitution never promised a gate. Deletion
  test on the READ block: remove it and only a bind option with no reader remains, so
  the option goes too (FR4). What is added — one scope comparison (`target_slug ∉
  bind.slugs`) — has four consumers if deleted (the fix line, the contract test, the
  law, the memory atom), so it earns its keep. `Invocation` loses `release`/`phase`
  (`resolve_active_release` moves to its one remaining reader, `SpecsTree`, or dies).
- **Seam 2 — the BLOCK envelope** (FR2). `fix:` is not a new module; it is a grammar
  every existing refusal already half-carries (`candidate.py`, `canon.py`, `pre-push-
  ci-gate.sh` do; `root_whitelist`, `gate_policy._PROTECTED_MESSAGE`, `venv_guard`,
  `verdict_check` do not). One contract test is the interface: it lists every BLOCK
  path by public seam, so a future refusal without a `fix:` is a failing test, not a
  review note. The Doctor already has `Rule.fix_help`; making it mandatory for
  error-class rules is depth at the existing interface, not a new field.
- **Seam 3 — `core.workspace_layout`** (FR5). The `CanonEntry` rows are pure data
  (pattern, kind, template path/string, area, dest); moving them to core costs no
  I/O and gives `render_registry_tables` (infrastructure, core-only importer) the
  rows it needs. `features/specs/canon.py` keeps the implementation that touches disk.
  Deletion test on the hand-typed §5.1/§5.3/§6.2 lines: rendered from the rows, they
  cannot drift; the ratchet that made a second zone list unrepresentable widens to
  every canonical name set (one AST walk, three name sets).
- **Seam 4 — `features/spec_context/sweep.py`** (FR6). Replace-don't-layer applied
  to the doctor: today `scan()` and `fix()` each carry a guard per call site
  (`_entries`, `_mtime`, `_remove`, `_guarded`, `_remove_dead_repo`) because the walk
  and the mutation were written separately. One primitive owns the walk and the two
  mutations (move, remove) behind one guard; `DoctorService` becomes a classifier
  over `sweep.walk()` entries and a dispatcher over `sweep.move()`/`sweep.remove()`.
  The CRIT bug's lesson is encoded as an invariant of the primitive, not a check at a
  site: the reaper judges by the registry (canon, exception, manifest) and never by
  liveness; session records and presence keep their own reapers. Moving instead of
  deleting removes the reason `--expired-only` existed (deletion was destructive), so
  the SessionStart lane simply becomes "the reaper" and `--fix` = reaper + specs fixes.
- **Seam 5 — the fixture, not the scope** (FR7). The repository is public, so every
  push publishes; the scan layers stay full on every path. The hand-kept baseline of
  23 tolerated pairs fails the deletion test once each fixture literal it tolerates
  is synthetic (matches no pattern) — the loop of literal/baseline/regex edits ends
  because nothing tolerated remains; no predicate, no second scope decision.

## Order of work (tracer bullets)

1. FR2 contract test first (RED on today's messages) — the operator sees the
   stalling BLOCKs enumerated before any production change.
2. FR1 gate shrink + scope rule + `fix:` lines; the test from step 1 turns GREEN for
   the gate paths. Slice: bound to A, a write into B is refused with a runnable fix.
3. FR3 + FR4: cache guard and bind options deleted, configuration carries the
   redirects, the bug's repro passes.
4. FR5 registry move + rendered law + widened ratchet (RED first on the hand-typed
   §6.2 table). Slice: `dadaia public stage` writes §6.2 from the rows.
5. FR6 primitive (RED: symlink/vanished/outside matrix over one function), then the
   reaper lane (`reaped/` row, move semantics, repo-top walk, hooks drift, INV-5
   move, SessionStart/PostToolUse wiring).
6. FR7 scope predicate, detectors rewired, self-scan baseline deleted, carve-outs
   pruned; the `develop` required check.
7. FR8 law/skills/entities/glossary; re-project; `public doctor` green.
8. FR9 closure.

## Verification

- Full preflight (`ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`,
  `pytest`) green with the bare commands producing no in-repo cache (FR3).
- `tests/contract/test_every_block_carries_a_fix.py` green: every BLOCK path listed,
  every `fix:` line ALLOWed by the gate itself.
- `dadaia doctor` on this instance: `compliance(total)` 100 %, exit 0; the `reaped/`
  zone empty after the run's own TTL pass; `HOOKS-DRIFT-1` absent in every ALIVE repo.
- Real-chokepoint replay: `ci push-gate-check` fed the candidate's own refspec passes
  with `specs/**` and `tests/**` carrying their synthetic literals and no baseline row.
- `git diff --stat main...HEAD` for the candidate: production lines net-negative or,
  per FR, justified against the deletion test in the closure `summary` log entry;
  ratchets move down only (import-linter cap, `#doctor` complexity, test census).
