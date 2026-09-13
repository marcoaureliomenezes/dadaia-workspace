# PLAN — Release: 0.4.7

**Status:** Aprovado
**Release ID:** 0.4.7
**Owner:** product-engineer

---

## Design (codebase-design vocabulary)

Three surfaces grew by layering — a second bug model beside the first, a cache beside
its source, a rule beside its home. Candidate 3 replaces; each FR names the seam it
cuts, what it deletes, and the deletion-test outcome of the one thing it adds.

- **Seam 1 — `BugRecord` and its verbs** (FR1). The record's interface shrinks by seven
  fields and one lineage path. Deletion test on the provenance cache: remove it and
  nothing reappears — its only reader was pillar 1, which reads `git log` for the same
  fact; P-16 existed to keep the cache honest and dies with the cache. Deletion test on
  Phase-0's `bugs update --set caused_by`: `resolve` already requires `--caused-by`, so
  the second writer was the C10 conflict itself. What is added — a seven-name retired-
  key tuple in `from_dict` and one ledgers fix — is the migration the schema drop owes
  (a schema drop ships its repair) and is deletable the release after every consumer
  tree has run `--fix`. The derived `surface` arm turns a hand-typed 24-name enum into a
  view of the package list the contract test already compares it to.
- **Seam 2 — `TelemetryStore`** (FR2, FR6). The store is already the one owner of the
  SQLite connection; a governance event is one more table behind the same open/migrate/
  quarantine interface, not a second store. The verbs call one helper at the CLI root
  (`cli/_governance_event.py`: build store, hash the record, insert, swallow OSError)
  — one place, N verbs. The doctor reads the store once into plain data and hands it
  to both sections the way `live_shas` already travels, so neither `features/specs`
  nor `features/backlog` imports `features/telemetry`. Deletion test on `agent` as an
  event field: the store's `sessions` table already carries `agent_name` per
  `session_id` — a field would be a second home.
- **Seam 3 — the record-change verbs** (FR3, FR4, FR5). `backlog exit` is a 20-line
  typer command over a function that exists; `audit disposition` is the first caller
  of `FindingRecord.apply_governance_update` (written for it, zero callers today) and
  `audit close` mirrors `archive_release`'s all-or-nothing shape with the histo append
  last; `release phase` folds `defined`/`implemented` into the two transitions that
  own them — the milestone IS the transition's sha, so `archive` can no longer hang on
  a milestone set by hand. Deletion test on a separate `implemented` verb: it would
  reappear as the same validation `phase CLOSURE` performs. Log entries stay hand-
  written: nothing downstream validates their content, only their shape.
- **Seam 4 — the law corpus** (FR7). The deletion test is applied to every restated
  rule: the copy outside its home passes it (removed, no behavior changes) and dies.
  Two skills pass it whole. The additions are the two measures the ruling names — the
  body-pointer finder extends the FR27 citation walker that already globs
  `public/**/*.md` (one more token grammar, not a second test file) and V35 is one
  more ratchet in the file that holds V32–V34. `constitution.md` keeps only what no
  other file states; `ctx_inject` stops loading a block the law chain already loaded.

## Order of work (tracer bullets)

1. FR1 first (T-047-25): the seven keys and their machinery go; `doctor --fix` strips
   the committed ledger; the operator sees the bug model become one model before any
   verb is added.
2. FR2 (T-047-26): the event table and the helper; the seven `bugs` verbs write events
   — slice: one verb, one row.
3. FR3, FR4, FR5 (T-047-27..29): each verb lands with its event and its `fix:` lines;
   each is independently demonstrable on this instance (an exit, a disposition + close
   on a fixture audit, a phase transition).
4. FR6 (T-047-30): the hand-edit rule, RED against a file-tool edit made after a verb.
5. FR7 (T-047-31 skills + map, T-047-32 personas + law + scaffolds + constitution +
   hook), reprojected once at the end of T-047-32.
6. FR8 closure (T-047-33).

## Verification

- Full preflight (`ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`,
  `pytest`) green; `lint-imports` shows no new `features -> features` edge (the doctor
  composition stays at the CLI root).
- `dadaia doctor` on this instance: `compliance(total)` 100 %, exit 0, zero
  `*-HANDEDIT` lines after the candidate's own verbs; then one deliberate file-tool edit
  of a resolved bug produces exactly one WARNING line and exit 0 (revert it).
- Real-verb replay on this repo: `dadaia backlog exit` for the three consumed slugs at
  closure; `dadaia release phase CLOSURE --sha <closed sha>` sets `implemented`; `dadaia
  audit close` exercised on a fixture audit in `tests/`.
- `tests/contract/test_behavior_map.py` green with the extended finder;
  `test_every_cited_dadaia_verb_exists` green with `backlog exit`, `audit
  disposition|close`, `release phase` cited in law and skills; V35 pinned.
- `git diff --stat main...HEAD` for the candidate: production lines net-negative or,
  per FR, justified against the deletion test in the closure `summary` log entry;
  ratchets move down only (V32 governance ids, V35 skill lines, import-linter cap).
