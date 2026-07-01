# TASKS — Release: v0.1.46 — SDD Governance v2

**Status:** Aprovado
**Release ID:** v0.1.46
**Owner:** product-engineer

Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. Max one `[-]` per owner unless a
disjoint write set is declared. Task ids are stable (`T-46-*`).

Waves: **A** = JSONL core (AC-1/2/3, must ship), **B** = taxonomy + law (AC-4/5-law),
**C** = cleanup + memory sweep (AC-5-cleanup/AC-6). Wave C is disjoint from A/B code and
may run after A/B review.

---

## Wave A — JSONL bug-event core

### [x] T-46-01 — Bug-event JSON schema
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/public/schemas/bugs/bug-event-v1.schema.json`
- **Preconditions:** none
- **Done:** schema defines required `bug_id`/`event`/`ts`/`reported_by` + per-event
  conditional payloads (AC-1); `archived` allowed with no required payload (non-terminal
  annotation). Tests validate a sample of each event kind AND include **rejection cases**
  (not positive-only): a missing required top-level field FAILS, a bad `event` enum value
  FAILS, and a `reported` event missing a required payload field FAILS. Projects to
  `.dadaia/agentic/schemas/bugs/` after `public stage`+`install`.
- **Parallel:** yes (disjoint from T-46-02 code until wiring).

### [x] T-46-02 — Bug-event model + append-only JSONL store
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/bugs/` (`models.py`, `service.py`),
  `dadaia_workspace/infrastructure/jsonl_bug_store.py`, tests under `tests/`
- **Preconditions:** T-46-01
- **Done:** `BugEvent` model + `redact()`; append-only store writing
  `specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl` (zero-padded rotation counter `<n>`), rotating to
  `<same-hour>Z-<n+1>.jsonl` at 1000 rows, files sorted by `(hour, n)`; `iter_events`
  tolerant of malformed lines; `append_event`/`status`/`stats` fold; unit tests green
  (append, rotation-boundary roll to `-<n+1>`, fold coherence, malformed-line skip).

### [x] T-46-03 — `dadaia bugs` CLI group
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/bugs.py`, `dadaia_workspace/cli/main.py`
  (add_typer `bugs`), tests
- **Preconditions:** T-46-02
- **Done:** `dadaia bugs append|status|stats` work end-to-end; `append` validates against
  T-46-01 schema; ADDITIVE path (no lease); `bug` singular untouched. CLI tests assert
  **observable STDOUT** (not exit-0 smoke): `status` lists the expected open `bug_id`(s)
  after a seeded append; `stats` prints the expected per-severity/status aggregate counts.

### [x] T-46-04 — Doctor JSONL invariant (schema + rotation + coherence)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/specs/doctor.py`, tests
- **Preconditions:** T-46-02
- **Done:** new `SPEC-DOC-033` check — per-line schema validity (ERROR), rotation ceiling
  >1000 rows (ERROR), event coherence over the terminal set `{resolved, superseded,
  deferred, rejected}` (`archived` is non-terminal, IGNORED). Tests require BOTH
  incoherence classes to ERROR — (a) terminal-without-prior-`reported` AND (b)
  double-terminal — PLUS a valid `reported`→`resolved` **negative control** that must NOT
  error, PLUS an `archived`-after-`resolved` case that must NOT error (exemption).
  Pure-module constraint preserved.

### [x] T-46-05 — One-time `*.md`→JSONL migration step
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/migrate/bugs_jsonl.py`,
  `dadaia_workspace/features/migrate/registry.py`, `dadaia_workspace/core/specs_version.py`,
  tests
- **Preconditions:** T-46-02, T-46-11 (`specs/bugs/_archive/` must exist BEFORE this runs —
  the move is in-process, not deferred)
- **Done:** `migrate_bugs_jsonl` converts each `specs/bugs/*.md` → coherent event stream
  (Open→`reported`; Closed→full history; missing release→`unknown` sentinel + WARN) AND
  **moves the source `.md` to `specs/bugs/_archive/` in-process** (`shutil.move`, upgraded
  to `git mv` when a repo is detected — precedent `tree_v2.py:78,97`); the move is NOT a
  deferred Bash follow-task. Registered in `REGISTRY` + `CANONICAL_SPECS_VERSION` bumped.
- **Round-trip test (mandatory):** a fixture bugs-tree test asserts, in one migration run —
  (1) each source `.md` now under `specs/bugs/_archive/` and no loose `.md` remains;
  (2) the emitted JSONL is the **exact** expected event stream per source bug;
  (3) re-run is a no-op (idempotent — no duplicate events, no re-move);
  (4) `--dry-run` writes nothing AND moves nothing (reports the plan only).

### [x] T-46-06 — Guardrail rule rewrite for JSONL events (R-1 pair)
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/rules/bug-registration-guardrail.md`,
  `dadaia_workspace/public/data/AGENTS.md`
- **Preconditions:** T-46-03 (CLI must exist for the rule to reference)
- **Done:** "minimum bug record" replaced with `dadaia bugs append` event contract;
  ADDITIVE + redaction preserved; root AGENTS "Bug Registration" section references JSONL;
  no surviving prescription to create a `.md` bug record (grep clean); `public stage` +
  `install --target all` + `public doctor` exit 0 (`[ok] public-privacy`).
- **CRITICAL (R-1):** this task MUST be `[x]` before the release closes — the format
  without the rule rewrite regrows the drift.

---

## Wave B — Taxonomy + `_archive` FROZEN + audit law

### [x] T-46-11 — Create `_archive` dirs (workspace + scaffolder + onboarding)
- **Owner:** software-engineer
- **Write set:** `specs/backlog/_archive/.gitkeep`, `specs/audits/_archive/.gitkeep`,
  `specs/bugs/_archive/.gitkeep`, `dadaia_workspace/features/specs/scaffolder.py`, tests
- **Preconditions:** none
- **Done:** the three `_archive` dirs exist in this workspace and are produced by the
  scaffolder + consumer-onboarding path; tests assert their presence.

### [x] T-46-12 — Gate: classify `_archive` subdirs as FROZEN (R-2 ordering fix)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/spec_context/gate_policy.py`, tests
- **Preconditions:** none
- **Done:** `_ARCHIVE_SUBDIR_PREFIXES` (with trailing `/`) matched **before**
  `_SPECS_ADDITIVE_PREFIXES` in `_classify_specs_relative`. Tests assert ALL directions:
  `classify_path("specs/bugs/_archive/x.jsonl")`→FROZEN; live
  `classify_path("specs/bugs/20260701T00Z-00.jsonl")`→ADDITIVE; **prefix-boundary**
  `classify_path("specs/bugs/_archivefoo.jsonl")`→ADDITIVE (only `_archive/` with trailing
  slash is FROZEN, not a `_archive`-prefixed sibling); in-repo
  `repos/<slug>/specs/audits/_archive/…`→FROZEN; `evaluate` BLOCKs a Write into `_archive`.

### [x] T-46-13 — Doctor: taxonomy + disposition invariants
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/specs/doctor.py`, tests
- **Preconditions:** T-46-11
- **Done:** three invariants, each with a **passes-on-clean-tree + fails-on-broken-fixture
  test PAIR** (not one blanket "tests green"):
  (1) `_archive` dirs-exist (WARN/auto-fix) — pair: all three dirs present → clean;
  a missing dir → warns;
  (2) consumed-but-unarchived backlog — pair: terminal-status entry already under
  `_archive/` → clean; terminal-status entry still loose in `specs/backlog/` → warns;
  (3) audit-without-disposition — pair: archived audit referencing its disposing release →
  clean; archived/undisposed audit with no release pointer → warns.

### [x] T-46-14 — Audit-disposition law text
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/rules/release-governance.md`
- **Preconditions:** T-46-13
- **Done:** law encoded (first release after audit dispositions every finding; archive
  only when fully dispositioned + approved; open bugs/audits outrank plain backlog at
  pick); `public stage`+`install`+`doctor` exit 0.

---

## Wave C — Cleanup + memory sweep (PE, DEFINITION/CLOSURE; disjoint from A/B)

### [x] T-46-21 — Disposition data sweep (audits + statuses + HTML cluster) — VERIFY-heavy

> **Partial (descope valve R-4 taken):** the 76-bug archival SHIPPED — `dadaia specs
> upgrade` ran the in-process migration, moving all 99 `.md` (incl. the 76 Closed) to
> `specs/bugs/_archive/` and emitting 18 JSONL event files; `specs/bugs/` has 0 loose
> `.md`; doctor 0-errors. The **audit-disposition + backlog-status-normalize + HTML-cluster
> dedupe** portion is explicitly SLIPPED to **v0.1.47** (the SPEC-DOC-035 undisposed-audit
> warnings are the now-live enforcing mechanism). Recorded in CLOSURE.

- **Owner:** product-engineer (+ project-manager for backlog curation)
- **Write set:** `specs/audits/**` (dispositions), `specs/backlog/*.md` (status
  normalization), JSONL dedupe of the HTML-report cluster; `git mv` for audit archive moves
- **Preconditions:** T-46-05, T-46-11, T-46-12, T-46-13
- **Done:** the 76-bug archival is **VERIFIED only** (AC-2/T-46-05 performed the in-process
  move) — confirm `specs/bugs/_archive/` populated + no loose Closed `.md`. Then: ~14 audits
  dispositioned/archived; EPIC + same-class backlog statuses machine-terminal; HTML-report
  defect = one JSONL stream (others `superseded`); `dadaia specs doctor` shows no
  consumed-but-unarchived / no undisposed-audit warnings. Never-delete law upheld.
- **Descope valve (R-4):** if the cycle runs long, the audit-disposition + status-normalize
  portion may slip to v0.1.47 (the 76-bug archival is NOT in the valve — it ships with
  AC-2). The mechanism (T-46-05/11/12/13/14) always ships in v0.1.46. Record any slip in
  CLOSURE.

### [x] T-46-22 — OpenCode product-memory sweep + catalog regen
- **Owner:** product-engineer (memory phase)
- **Write set:** `specs/memory/product/{workspace-init,product-vision,
  public-asset-distribution,harness-primitives,cross-platform-portability,
  workspace-portability,agent-sdd-alignment,agent-comms,agent-orchestration}.md`,
  `specs/memory/product/index.md`, `specs/memory/product/catalog.json`
- **Preconditions:** none (ACTIVE.md phase = DEFINITION/CLOSURE)
- **Done:** **falsifiable predicate** — a grep over `specs/memory/product/*.md` (LIVE
  atoms only, excluding `_archive/` so historical mentions do not false-positive) for
  OpenCode-as-a-live-target phrasing returns **zero** hits; the live harness set reads
  `{claude, codex, pi}`; `dadaia memory catalog generate` clean.

### [x] T-46-23 — Minor doctor debt (DRIFT-5 real items only)
- **Owner:** product-engineer
- **Write set:** `specs/memory/product/lifecycle-foundation.md` (token_estimate),
  `git mv` of malformed audit dir `specs/audits/2026-06-12T001813Z`,
  `dadaia_workspace/features/specs/doctor.py` (heading allowlist for 4 unknown headings)
- **Preconditions:** none
- **Done:** LINT-1 token drift cleared; audit dir has session-id suffix (SPEC-DOC-030);
  4 unknown-heading warnings cleared. **Negative test:** a genuinely-unknown heading (not
  in the extended allowlist) still WARNs — the allowlist widens for the 4 known headings
  only, it does not disable the check. Benign/grandfathered items untouched.

---

## Close criteria

- All Wave A tasks `[x]` (T-46-06 non-negotiable — R-1).
- Wave B tasks `[x]`.
- Wave C: T-46-22/23 `[x]`; T-46-21 either `[x]` or explicitly slipped to v0.1.47 in
  CLOSURE with rationale.
- `pytest` + `ruff` + `mypy --strict` + `dadaia specs doctor` + `dadaia public doctor`
  all green. Trio review (qa/code/security) APPROVE per release-governance cadence.
