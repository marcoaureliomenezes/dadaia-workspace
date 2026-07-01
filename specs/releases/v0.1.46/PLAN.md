# PLAN — Release: v0.1.46 — SDD Governance v2

**Status:** Aprovado
**Release ID:** v0.1.46
**Owner:** product-engineer

Implementation plan, module-by-module, for the six ACs in SPEC.md. Three waves
(A: JSONL core, B: taxonomy + law, C: cleanup + sweep). Real anchors cited throughout.

---

## Strategy

Ship the operator's priority — event-sourced JSONL bug telemetry with its enforcing
rule-rewrite — as an atomic Wave A, then layer the `_archive` FROZEN taxonomy + audit
law (Wave B) that gives the migration its landing zone and the disposition sweep its
enforcement, then run the manual data cleanup + memory sweep (Wave C) in DEFINITION/
CLOSURE. Reuse existing patterns: the atomic temp+rename write from
`infrastructure/json_lifecycle_run_store.py`, the typer command-group pattern from
`cli/commands/*.py`, the migration-step registry in `features/migrate/registry.py`, the
schema-under-`public/schemas/` projection, and the `SpecsDoctor` check pattern in
`features/specs/doctor.py`.

## Layers affected

- **Domain/core:** new bug-event model + JSONL store port (`features/bugs/`).
- **Infrastructure:** append-only JSONL store (new), reusing the atomic-write idiom.
- **CLI:** new `dadaia bugs` group (`cli/commands/bugs.py`), wired in `cli/main.py`.
- **Gate:** `features/spec_context/gate_policy.py#classify_path` (`_archive` → FROZEN).
- **Doctor:** `features/specs/doctor.py` (JSONL invariant + taxonomy + disposition checks).
- **Migration:** `features/migrate/` (new `*.md`→JSONL step + registry entry).
- **Public assets (ai-engineer):** `public/rules/bug-registration-guardrail.md`,
  `public/rules/release-governance.md`, `public/data/AGENTS.md`,
  `public/schemas/bugs/bug-event-v1.schema.json`, scaffolder `_archive` dirs.
- **Memory (product-engineer):** `specs/memory/product/*.md` + regenerated catalog.

---

## Wave A — JSONL bug-event core (AC-1, AC-2, AC-3)

### A1. Event schema — `public/schemas/bugs/bug-event-v1.schema.json`

Author a JSON Schema mirroring the existing schema style
(`public/schemas/handoff-v1.schema.json`). Required top-level: `bug_id`, `event`
(enum `reported|resolved|superseded|deferred|rejected|archived`), `ts` (ISO-8601 UTC),
`reported_by`. Conditional payloads (`if event == reported` requires
`title/severity/surface/component/context/tags/symptom/repro/expected/notes`;
`resolved`→`release`; `superseded`→`superseded_by`; `deferred|rejected`→`reason`).
`archived` carries no required payload (non-terminal annotation — see A4). Ship a rejection
test set: a missing required top-level field, a bad `event` enum value, and a `reported`
event missing a required payload field must all FAIL validation (not positive-only). Lives
under `public/schemas/` so `dadaia public install` projects it to
`.dadaia/agentic/schemas/bugs/` (the `schemas` asset kind is already listed in
`infrastructure/public_assets_common.py:27` and `cli/commands/public.py:31`).

### A2. Bug-event model + JSONL store — `features/bugs/`

- `features/bugs/models.py` — a frozen `BugEvent` dataclass with `to_dict`/`from_dict`,
  event-kind enum, and a `redact()` helper for `notes` (strip operator-local paths/IPs —
  reuse the redaction discipline already in the privacy rules).
- `infrastructure/jsonl_bug_store.py` — append-only store. **Pattern:** unlike the
  replace-on-save `JsonLifecycleRunStore._atomic_write` (mkstemp + `os.replace`), the JSONL
  store **appends** one line per event under `specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl` where
  `<n>` is a zero-padded rotation counter (`00`, `01`, …). Open the current
  `(hour, n)` file in append mode, write `json.dumps(event) + "\n"`. Rotation: before
  append, if the target file already has ≥ 1000 rows, roll to `<same-hour>Z-<n+1>.jsonl`
  (the within-hour disambiguator is required because >1000 rows is a hard doctor ERROR and
  a bare `<hour>Z.jsonl` has no rotation room). Reads: `iter_events()` streams all
  `*.jsonl` in the dir sorted by `(hour, n)` (chronological), skipping malformed lines with
  a logged WARN (mirror the corrupt-record tolerance in `JsonLifecycleRunStore.list_runs`).
  Reject repo-tree-root writes is N/A — `specs/bugs/` is inside the context, not `.dadaia`
  state.
- `features/bugs/service.py` — `append_event`, `status()` (fold events per `bug_id` →
  current state), `stats()` (aggregate counts by severity/status/component). The fold is
  the same event-sourcing reduce the coherence doctor check reuses.

### A3. CLI group — `cli/commands/bugs.py` + wire in `cli/main.py`

New `bugs_app = typer.Typer(...)` (mirror `newartifacts.py` `bug_app` structure and the
`_resolve_specs_dir` helper):
- `dadaia bugs append` — options for `--event`, `--bug-id`, and per-event fields; validates
  against A1 schema before append; ADDITIVE path, no lease.
- `dadaia bugs status` — fold + list open bugs (optionally `--all`).
- `dadaia bugs stats` — aggregate table.
Wire `app.add_typer(bugs_app, name="bugs")` in `cli/main.py` (alongside the existing
`bug_app` at `main.py:68` — keep `bug` singular for now; AC-4/out-of-scope: deprecate note
only). **Naming caution:** `bug` (singular, existing Markdown `new`) vs `bugs` (plural,
new JSONL) coexist this release; the rule-rewrite (A6) points agents at `bugs append`.

### A4. Doctor invariant — extend `SpecsDoctor` in `features/specs/doctor.py`

Add a check (new code, e.g. `SPEC-DOC-033`) that: (a) validates every line of every
`specs/bugs/*.jsonl` against the A1 schema (ERROR on invalid line); (b) enforces the
rotation ceiling (ERROR on a file > 1000 rows); (c) **event coherence** — fold events per
`bug_id` over the **terminal set `{resolved, superseded, deferred, rejected}`** (the
`archived` annotation is NON-terminal per AC-1 and is IGNORED by this check): a terminal
event with no prior `reported` = ERROR; a terminal event after an existing terminal for
the same `bug_id` = ERROR. Tests must cover BOTH incoherence classes (terminal-without-
`reported` AND double-terminal) AND a valid `reported`→`resolved` negative control that
must NOT error, plus an `archived`-after-`resolved` case that must NOT error (exemption).
Follow the existing `Issue`/`Severity` emission pattern used by the other `SPEC-DOC-*`
checks. Pure-module constraint holds (no I/O outside `specs_dir`).

### A5. Migration `*.md` → JSONL — `features/migrate/` + registry

- `features/migrate/bugs_jsonl.py` — `migrate_bugs_jsonl(specs_dir, *, dry_run)` returning
  a `MigrateResult` (same shape as `tree_v2.migrate_tree_v2`). For each `specs/bugs/*.md`:
  parse frontmatter (`status`, `severity`, `surface`, `session_id`, `superseded_by`,
  closing release if present) + body (`Symptom`/`Repro`/`Expected`/`Notes`). Emit a
  `reported` event; for Closed, also emit the reconstructed terminal event
  (`resolved` with `release`, or `superseded` with `superseded_by`); missing closing
  release → `release: "unknown"` sentinel + WARN (R-3).
- **The archival move is INTRINSIC and in-process (review BLOCKING-1).** In the same run,
  after writing the JSONL, the migration MOVES each source `.md` to `specs/bugs/_archive/`
  itself — `shutil.move` (upgraded to `git mv` when a `.git` is detected), exactly like
  `features/migrate/tree_v2.py:78,97` already does. This is **not** gate-intercepted: the
  SDD gate classifies only Write/Edit tool CALLS, never a migration function's own Python
  fs ops — so no loose `.md` is ever left for a consumer running `dadaia specs upgrade`.
  `--dry-run` PLANS the move (records source→dest in the `MigrateResult`) and writes/moves
  nothing. Idempotent: a bug already present in JSONL is skipped (no duplicate event, no
  re-move). The `specs/bugs/_archive/` dir (B2/T-46-11) must exist before this runs.
- Register as the next step in `features/migrate/registry.py` `REGISTRY` (from_version =
  current latest, to_version = +1, key `bugs-jsonl`). `dadaia specs upgrade` walks it via
  the existing `run_chain`; consumers migrate on upgrade. Bump
  `core/specs_version.CANONICAL_SPECS_VERSION` accordingly.

### A6. Rule rewrite (ai-engineer) — `public/rules/bug-registration-guardrail.md`

Rewrite the "Minimum bug record" section: replace the Markdown-frontmatter record with the
`dadaia bugs append` event contract; keep "registration stays ADDITIVE for every agent"
and the redaction requirement verbatim. Update the root bug-registration text in
`public/data/AGENTS.md` (the "Bug Registration (all runtimes)" section) to reference JSONL
+ `dadaia bugs append` instead of `specs/bugs/<slug>.md`. Then `dadaia public stage &&
dadaia public install --target all && dadaia public doctor` (must exit 0, `[ok]
public-privacy`). **R-1 gate:** A6 lands in the same branch as A1–A5; the release does not
close with A6 open.

---

## Wave B — Taxonomy + `_archive` FROZEN + audit-disposition law (AC-4, AC-5-law)

### B1. Gate classifier — `features/spec_context/gate_policy.py`

In `_classify_specs_relative`, add an `_ARCHIVE_SUBDIR_PREFIXES` tuple
(`specs/backlog/_archive/`, `specs/audits/_archive/`, `specs/bugs/_archive/`) and match it
**before** the `_SPECS_ADDITIVE_PREFIXES` loop, returning `PathClass.FROZEN`. This is the
R-2 ordering fix: today `specs/bugs/` (ADDITIVE) is checked first and would swallow
`specs/bugs/_archive/`. The existing `_FROZEN_PREFIX = "specs/_archive/"` stays. The
in-repo re-root path (`_context_relative`) already funnels through
`_classify_specs_relative`, so both workspace-root and `repos/<slug>/` archive paths get
FROZEN for free.

### B2. Scaffolder + onboarding `_archive` dirs

Create `specs/backlog/_archive/`, `specs/audits/_archive/`, `specs/bugs/_archive/` (each
with `.gitkeep`) in the workspace tree now, and in the scaffolder
(`features/specs/scaffolder.py`) + consumer-onboarding path so new/upgraded workspaces get
them. Wire dir creation into the AC-2 migration step too (the migration must not `git mv`
into a missing dir).

### B3. Doctor — taxonomy + disposition invariants — `features/specs/doctor.py`

- `_archive` dirs exist per class (WARNING/AUTO-FIX, mirror TREE-4 create-dir pattern).
- **consumed-but-unarchived backlog**: a backlog entry whose `status:` is terminal
  (`DELIVERED|CONSUMED|SUPERSEDED|RESOLVED`) but still in `specs/backlog/` (not under
  `_archive/`) → WARNING (extends the SPEC-DOC-031 family).
- **audit-without-disposition**: an audit dir under `specs/audits/_archive/` must reference
  its disposing release; a live audit older than the newest shipped release with no
  disposition → WARNING.

### B4. Audit-disposition law text (ai-engineer)

Encode the law in `public/rules/release-governance.md`: the first release after an audit
dispositions every finding; an audit archives only when fully dispositioned + release
approved; open bugs + open audits outrank plain backlog at pick. Re-stage + install +
doctor.

---

## Wave C — Cleanup + memory sweep (AC-5-cleanup, AC-6) — PE, DEFINITION/CLOSURE

### C1. Disposition data sweep (PE + PM) — VERIFY-heavy (bug archival done by AC-2)

- **VERIFY only** (not perform): AC-2's intrinsic in-process move already populated
  `specs/bugs/_archive/` and the JSONL carries the 76 closed bugs' terminal events; confirm
  no loose Closed `.md` remains. Archiving a resolved bug appended no JSONL event, so
  coherence is not tripped (AC-1 decision).
- Disposition the ~14 undisposed audits: add disposing-release pointer, `git mv` fully
  dispositioned ones to `specs/audits/_archive/`.
- Normalize off-canon statuses: EPIC `sdd-governance-v2-agents-lifecycle.md` frontmatter
  `status:` → terminal (this release consumes it); same-class `panel-ux-overhaul.md`,
  `features-import-infrastructure-direct-debt.md`; any bug `status:` outside `{Open,Closed}`.
- Dedupe the HTML-report bug cluster → one JSONL event stream, others `superseded`.
- Never delete any file (never-delete law) — terminal status + reason only.

### C2. OpenCode memory sweep (PE, memory phase)

Edit the ~11 atoms listed in SPEC AC-6 to remove OpenCode-as-live (harness set is
`{claude, codex, pi}`), then `dadaia memory catalog generate` to refresh
`index.md`/`catalog.json`. Memory writes are gate-allowed because ACTIVE.md phase is
DEFINITION (now) / CLOSURE (at close). **Falsifiable done-predicate:** a grep over
`specs/memory/product/*.md` (live atoms only — NOT `_archive/`, so historical mentions
don't false-positive) for OpenCode-as-a-live-target phrasing returns zero hits.

### C3. Minor doctor debt (PE)

Fix `lifecycle-foundation.md` `token_estimate` (LINT-1), rename the malformed audit dir
`specs/audits/2026-06-12T001813Z` to add its session-id suffix (SPEC-DOC-030, via `git
mv`), extend the heading allowlist for the 4 unknown headings (LINT-1). Leave all
benign/grandfathered items untouched.

---

## Execution order

A1 → A2 → A3 → A4 → A5 → A6 (Wave A, atomic) → B1 → B2 → B3 → B4 (Wave B) → C1 → C2 → C3
(Wave C). Wave C may run after Wave A/B code review (disjoint write set).

## Technical risks (see SPEC §5 for the full table)

- R-1 (CRITICAL): A6 must land with A1–A5 — enforced by the TASKS done-criterion.
- R-2 (HIGH): classifier ordering — B1 reorders `_archive` before ADDITIVE + unit test.
- R-3 (MEDIUM): lossy Closed-bug migration — `release: unknown` sentinel + WARN, never drop.

## Validation plan

- `poetry run pytest` (new: JSONL store, event model, doctor invariant, classifier
  ordering, migration idempotency/dry-run) — green.
- `ruff format --check && ruff check && mypy --strict` — green (pre-push CI gate).
- `dadaia specs doctor` — new invariants green on this workspace after Wave C.
- `dadaia public doctor` — schema + rewritten rules projected, `[ok] public-privacy`.
- Manual: `dadaia bugs append|status|stats` round-trip; migration on a fixture bugs tree.
