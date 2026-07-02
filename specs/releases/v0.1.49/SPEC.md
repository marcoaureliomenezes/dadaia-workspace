# SPEC — v0.1.49 — Intake Integrity

**Status:** Aprovado
**Branch:** `feature/v0.1.49` (base: `d81db184`, v0.1.48 closure)
**Origin:** operator-approved release sequence R1 (grill 2026-07-02, report
`.dadaia/reports/dadaia-workspace/product-engineer/2026-07-02T170324Z-refine-specs.html`,
operator decision #1: backlog becomes git-tracked repository truth). Disposes open bugs
`backlog-gitignored-governance-vacuous` and
`backlog-subject-registry-invariant-content-scan`.
**Consumes:** memory-heading-allowlist-extension

## 1. Problem

The intake machine that turns operator demand into releases has three defects:

1. **Backlog invisible to git.** `.gitignore` `/specs/*` opts back in constitution,
   memory, audits `*.md`, bugs `*.md`/`*.jsonl`, and `releases/ACTIVE.md` — but NOT
   `specs/backlog/`. Every live backlog entry is untracked (one historical
   force-added stray), so the pre-commit backlog-doctor scope ("commits touching
   `specs/backlog/**`") can never fire, the CI backlog-doctor job validates a folder
   that never reaches the repo, and consumed entries get *tracked* durable copies in
   `specs/_archive/` while the live set has no history. This invisibility is how
   consumed/stale entries accumulated undetected until the 2026-07-02 sanitization.
2. **Invariant anchors scraped from arbitrary content.** `_derive_invariant_anchors`
   (`features/backlog/subject_registry.py`) regex-matches `INV-*` in the FULL CONTENT
   of every `.py`/`.md` under `source_root` — in the self-hosting layout that includes
   `tests/` and production docstrings. Docstring examples (`INV-foo` in
   `ledger_writer.py`/`ledger.py`), comment mentions (`INV-x`), and test-fixture ids
   (`INV-made-up`, `INV-fixture-rule`) all resolve as live anchors, so a fabricated or
   typo'd invariant intent can pass the fail-closed BL-SCHEMA classifier.
3. **Heading allowlist is library-frozen and self-inconsistent.** The `##` heading
   allowlist lives hardcoded in `lint-memory-atoms.py`; consumers cannot extend it
   without editing a lib-originated file, and the library's own scaffold QA atom
   heading `Padrões de qualidade` (`public/scaffold/memory/quality-assurance.md`) is
   not allowlisted — a freshly scaffolded workspace lints with a warning out of the
   box. (The other scaffold atoms' headings — `architecture.md`, `tech-stack.md`,
   `product/feature.md` — are already covered by Groups A/C; verified 2026-07-02.)

## 2. Goals (what done means)

1. `specs/backlog/**` (entries + `_archive/`) is repository truth; the BL-* pre-commit
   chokepoint scope and the CI backlog-doctor job exercise the real committed tree.
2. A fabricated `INV-*` id binds `UNRESOLVED`; invariants declared in
   `specs/memory/**` (e.g. `INV-4`, `INV-5`) keep resolving. No anchor is ever derived
   from `.py` content or from `tests/`.
3. A consumer workspace can extend the heading allowlist via a data file without
   touching the library; a freshly scaffolded workspace lints clean (0 heading
   warnings).
4. Both consumed bugs carry `resolved` terminal events; the consumed backlog entry is
   removed with a durable copy (removal-on-release).

## 3. Functional requirements

### FR1 — Backlog becomes repository truth

- `.gitignore`: opt-in block for `specs/backlog/` mirroring the bugs block style:
  negate the directory, re-ignore its contents, then negate `*.md` and
  `_archive/` + `_archive/*.md`.
- Track the current sanitized backlog: all live entries, `candidates.md`, and
  `specs/backlog/_archive/*.md`.
- Acceptance: `git check-ignore specs/backlog/candidates.md` exits non-zero;
  `git ls-files specs/backlog/ | wc -l` == **31** after W1 (22 live entries +
  candidates.md + 8 archived `_archive/*.md`; `_archive/.gitkeep` intentionally
  untracked) and == **30** after the W5 consumed-entry removal; `dadaia backlog
  doctor` clean; the commit that touches `specs/backlog/**` passes the pre-commit
  chokepoint with the BL-* scope actually firing.

### FR2 — Fail-closed invariant derivation

- `_derive_invariant_anchors(specs_dir, source_root)` drops the `source_root` leg
  entirely: invariant anchors derive ONLY from `specs_dir/memory/**` Markdown files.
  (`.py` files are never a declaration surface for invariants; `tests/` junk and
  production docstrings stop leaking.)
- The signature keeps `specs_dir`; the `source_root` parameter is removed from the
  derivation (and from its call site in `build_registry`).
- Regression tests (all on `tmp_path` fixture trees — no coupling to live atoms):
  (a) an `INV-*` token present only in a `.py` docstring under the source root binds
  `UNRESOLVED`; (b) an `INV-*` token present only under `tests/` binds `UNRESOLVED`;
  (c) a synthetic `INV-*` token present in a fixture memory doc resolves; (d) the
  existing `INV-made-up → UNRESOLVED` unit assertion stays green; (e) the existing
  `test_invariant_resolves` stays green UNCHANGED — its fixture token
  (`INV-no-fixture-drift`) lives in the fixture memory doc, not the `.py` fixture.
- Acceptance (one-time live-tree probe at QA/closure — NOT a committed test, per the
  no-slop law): `dadaia backlog subjects --specs-dir specs --source-root . |
  grep '^invariant'` lists only memory-derived ids (expected set: exactly
  `INV-1`..`INV-6`); `INV-foo`, `INV-made-up`, `INV-x`, `INV-fixture-rule`,
  `INV-no-claude-at-L2`, `INV-no-fixture-drift` are gone.

### FR3 — Consumer-extensible heading allowlist + scaffold self-consistency

- `lint-memory-atoms.py` merges an optional workspace file
  `specs/memory/.heading-allowlist` (UTF-8, one exact heading per line, `#` comments
  and blank lines ignored) into the curated allowlist at lint time.
- Add a curated "Group S — scaffold template sections" to the script containing every
  `##` heading shipped by the **linted scaffold atoms only** —
  `public/scaffold/memory/{architecture,tech-stack,quality-assurance}.md` — that is
  not already allowlisted, so a fresh scaffold lints clean with NO allowlist file.
  `AGENTS.md` and `index.md` are `_NON_ATOM_FILES` (never linted): their governance
  headings (`Write Ownership`, `Tree Shape`, `Atom Format`, `Validation`) MUST NOT
  enter the allowlist — that would weaken the very guard this release strengthens.
  The verified live gap is exactly ONE heading (`Padrões de qualidade`); Group S may
  legitimately be a single-entry group — the coverage test enforces the invariant
  going forward.
- Consumer note: `specs/memory/.heading-allowlist` sits in the MEMORY path class —
  consumers edit it via file tools only in DEFINITION/CLOSURE phase (gate law); the
  library ships none and the tests create it under `tmp_path`.
- The script is lib-originated: edit the source under `public/scripts/`, then
  `dadaia public stage && install --target all && public doctor` exit 0.
- Tests: unit tests for the merge (file absent → curated only; file present → union;
  malformed lines ignored); a test asserting every `##` heading of the linted scaffold
  atoms (`public/scaffold/memory/*.md` minus the script's `_NON_ATOM_FILES` and
  `index.md`) is allowlisted.
- Acceptance: fresh-scaffold lint = 0 heading warnings; a consumer heading listed in
  `.heading-allowlist` stops warning; LINT-1 doctor behavior otherwise unchanged.

## 4. Non-goals

- No redesign of the subject registry beyond the invariant leg (code/cli/catalog/doc
  derivation untouched).
- No backlog content changes (the 2026-07-02 sanitization already ran; this release
  only makes the folder repository truth).
- The `bugs-append-bound-session-falls-through-to-cwd-specs` bug is R2 (v0.1.50)
  kernel scope — not consumed here.
- No new panel/CI surface beyond what the now-real backlog-doctor job already does.

## 5. Acceptance criteria

- **AC-1** `git ls-files specs/backlog/` == 31 files after W1 (== 30 after W5);
  `git check-ignore` negative for live entries and `_archive/*.md`.
- **AC-2** Live registry: zero invariant anchors sourced outside `specs/memory/**`
  (expected live set: exactly `INV-1`..`INV-6`), verified as a one-time QA/closure
  probe via `dadaia backlog subjects` — never frozen into a committed test.
- **AC-3** Fresh scaffold (pytest `tmp_path`) lints 0 heading warnings, with the
  coverage test scoped to the linted scaffold atoms (never `AGENTS.md`/`index.md`);
  `.heading-allowlist` union honored; malformed lines ignored without crash.
- **AC-4** `ruff format --check`, `ruff check`, `mypy --strict`, full `pytest` green
  locally (pre-push gate) and all CI jobs green on the PR.
- **AC-5** At closure: 2 bug `resolved` events (`--release v0.1.49`); consumed entry
  `memory-heading-allowlist-extension` removed from `specs/backlog/` with durable copy
  under `specs/_archive/v0.1.49/consumed-backlog/`; memory atoms updated
  (CLOSURE phase): `sdd-bug-backlog-governance` (registry derivation + backlog now
  git-tracked) and `specs-doctor` (allowlist extension file).

## 6. Risks

- The now-real CI backlog-doctor job runs against the committed tree for the first
  time — mitigated: `dadaia backlog doctor` validated clean locally on the exact set
  being committed.
- Dropping the source_root leg could orphan an invariant id referenced by a live
  backlog intent — mitigated: zero live intents use `kind: invariant` (verified
  2026-07-02).
