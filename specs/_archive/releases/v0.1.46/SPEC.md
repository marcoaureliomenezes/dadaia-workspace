# SPEC — Release: v0.1.46 — SDD Governance v2

**Status:** Aprovado
**Release ID:** v0.1.46
**Owner:** product-engineer
**Opened:** 2026-07-01

Backbone EPIC: `specs/backlog/sdd-governance-v2-agents-lifecycle.md` (FEAT-GOV-V2-01).
Scoping audit: `specs/audits/20260701T135346Z-6145b869/audit.md` (overall 4/10;
bug-format 2/10, product-memory 3/10, disposition-hygiene 3/10).

---

## 1. Problem and context

The SDD governance surface has drifted from its own mandate on three axes.

1. **Bugs are Markdown when JSONL was mandated.** Release v0.1.14 mandated event-sourced
   JSONL bug telemetry for v0.1.15 (`specs/_archive/releases/v0.1.14/SPEC.md:308-310`).
   Only half shipped: the *rule-rewrite* half of the mandate was never done, so
   `bug-registration-guardrail` still prescribes a Markdown record and every agent
   correctly obeyed the stale rule. Result today: **99 `specs/bugs/*.md`** (76 Closed,
   22 Open, 1 off-canon Resolved), **zero JSONL**, and an empty `specs/bugs/_archive/`.
   This is the drift the operator escalated. The root lesson: a format change that ships
   *without* its enforcing rule-rewrite silently regrows the drift.

2. **No archive/disposition discipline, because the law that mandates it is unshipped.**
   There is no FROZEN gate-class for per-artifact `_archive` dirs, no audit-disposition
   law, and no doctor invariant for either — so 76 closed bugs sit unarchived, ~14 audit
   reports are undisposed (`specs/audits/_archive/` empty), and backlog statuses drift
   off-canon (EPIC frontmatter `status: candidate` while its body says PARTIALLY
   CONSUMED, referenced by shipped releases — SPEC-DOC-031).

3. **Product memory long-tail still claims OpenCode is a live target.** OpenCode was
   removed entirely in v0.1.24 (both layers), yet ~11 product atoms still present it as
   live, 5+ releases later.

This release is the dedicated remediation the audit recommends: ship the JSONL bug-event
system **with its rule-rewrite**, establish the `_archive` taxonomy + gate class +
audit-disposition law, and sweep the stale product memory — closing the mandate that was
left half-done and the debt that accreted behind it.

---

## 2. Objective

Make SDD bug telemetry event-sourced JSONL enforced by a rewritten guardrail rule and a
doctor invariant; establish the `_archive` FROZEN taxonomy and audit-disposition law with
doctor backstops; and sweep the stale OpenCode-as-live product memory — so the governance
surface matches its own mandate again.

---

## 3. Scope

Six acceptance clusters. The **JSONL core (AC-1 + AC-2 + AC-3)** is the operator's
priority and MUST ship in v0.1.46. AC-1 and AC-3 are a **hard pair** — the format without
the rule-rewrite regrows the exact drift being fixed (see §5 risk R-1).

### AC-1 — Bugs → event-sourced JSONL (EPIC §2)

- **Format:** append-only JSONL (one JSON object per line) under `specs/bugs/`. Filename
  `<YYYYMMDDTHH>Z-<n>.jsonl` where `<n>` is a zero-padded rotation counter (`00`, `01`, …).
  Rotate to `<same-hour>Z-<n+1>.jsonl` when the current file reaches **1000 rows**. The
  `-<n>` disambiguator is mandatory because >1000 rows is a hard doctor ERROR and a bare
  `<YYYYMMDDTHH>Z.jsonl` name has no within-hour room to rotate. Files sort
  chronologically by `(hour, n)`.
- **Event schema** shipped under `dadaia_workspace/public/schemas/bugs/` (projected to
  `.dadaia/agentic/schemas/bugs/`): required `bug_id`, `event`
  (`reported|resolved|superseded|deferred|rejected|archived`), `ts`, `reported_by`.
  Per-event payload:
  - `reported` → `title`, `severity`, `surface`, `component`, `context`, `tags[]`,
    `symptom`, `repro`, `expected`, `notes` (redacted — no operator-local path/IP/secret);
  - `resolved` → `release`;
  - `superseded` → `superseded_by`;
  - `deferred` / `rejected` → `reason`.
- **Event classes (DECISION — resolves the `archived` contradiction, review BLOCKING-2):**
  the **terminal set** is exactly `{resolved, superseded, deferred, rejected}` — a
  `bug_id` may have at most one terminal event. `reported` is the required opener.
  `archived` is retained in the enum (per EPIC §2) but is redefined as an explicitly
  **NON-terminal annotation** event: it is **exempt from the double-terminal coherence
  rule** and never counts as a terminal. **Archiving a bug is a source-`.md` `git mv`
  operation only** — it moves the legacy Markdown source to `specs/bugs/_archive/` and
  emits **no** JSONL event; the JSONL bug stream keeps its existing terminal event and is
  never re-eventful. Consequence: AC-5 archiving the 76 already-`resolved` bugs cannot
  trip the coherence doctor, because no `archived` (or any) event is appended to their
  streams. (`archived` is defined-but-unemitted this release; a future bug-trend audit
  per EPIC §4 may emit it as a non-terminal roll-up annotation — out of scope here.)
- **CLI:** `dadaia bugs append`, `dadaia bugs status`, `dadaia bugs stats`.
- **Doctor invariant:** JSONL line-schema validity + rotation ceiling (no file > 1000
  rows) + **event coherence** on the terminal set `{resolved, superseded, deferred,
  rejected}` — (a) a terminal event for a `bug_id` with no prior `reported` = ERROR;
  (b) a terminal event after an existing terminal for the same `bug_id` = ERROR. A valid
  `reported`→`resolved` stream is coherent (negative control). `archived` events are
  ignored by the terminal-coherence check.
- **How to verify:** `dadaia bugs append` writes a `reported` row; `dadaia bugs status`
  lists open bugs; `dadaia bugs stats` aggregates by severity/status; `dadaia specs
  doctor` reports the new invariant green on a coherent log and ERRORs on an injected
  incoherent log — BOTH classes: terminal-without-prior-`reported` AND double-terminal,
  plus a valid `reported`→`resolved` control that must NOT error (unit-tested);
  `dadaia public doctor` shows the schema projected under `.dadaia/agentic/schemas/bugs/`.

### AC-2 — One-time migration `*.md` → JSONL (EPIC §2)

- A converter reads the existing **99 `specs/bugs/*.md`**: for an **Open** bug, emit a
  single `reported` event; for a **Closed** bug, emit the full event history it can
  reconstruct (`reported` → `resolved`/`superseded` with the closing release / superseder
  where the frontmatter records it).
- **The archival move is INTRINSIC to the migration step, in-process (review BLOCKING-1).**
  In the same run that writes the JSONL, the migration moves each source `.md` to
  `specs/bugs/_archive/` — a filesystem move (`shutil.move`) in the write phase, upgraded
  to `git mv` when a git repo is detected. Precedent: `features/migrate/tree_v2.py` already
  moves sources in-process. The earlier "move must run outside the gate" framing was a red
  herring: the SDD gate classifies only Write/Edit **tool calls**, not a migration
  function's own Python file operations — so the migration can and must complete the move
  itself, leaving no loose `.md` behind for a consumer running `dadaia specs upgrade`.
  `--dry-run` PLANS the move (reports the source→dest pairs) and writes nothing.
- Shipped as a **`dadaia specs upgrade` migration step** (registered in the migration
  chain) so consumer workspaces migrate on upgrade. Idempotent + dry-run-capable per the
  existing migration-step contract.
- **How to verify:** a fixture bugs-tree **round-trip** test asserts, in one migration run:
  (1) each source `.md` now lives under `specs/bugs/_archive/` and no loose `.md` remains;
  (2) the emitted JSONL is the exact expected event stream per source bug (Open→`reported`;
  Closed→`reported`+terminal); (3) a re-run is a no-op (idempotent — already-migrated bugs
  skipped, no duplicate events, no re-move); (4) `--dry-run` writes nothing and moves
  nothing while reporting the plan.

### AC-3 — Guardrail-rule rewrite (EPIC §2 "Law") — MUST ship same release

- Rewrite `dadaia_workspace/public/rules/bug-registration-guardrail.md` for JSONL events:
  registration stays **ADDITIVE for every agent**; the "minimum bug record" section is
  replaced with the `dadaia bugs append` event contract (no more Markdown-frontmatter
  record). The redaction requirement is preserved verbatim.
- Update any other rule / `AGENTS.md` text that prescribes the Markdown bug record (the
  root `AGENTS.md` "Bug Registration" section referencing `.md` files; any agent-persona
  text that says "write `specs/bugs/<slug>.md`").
- This is **ai-engineer's** surface (lib-originated rule + AGENTS source under
  `public/`). Spec it here; ai-engineer authors it and runs `public stage` +
  `install --target all` + `public doctor`.
- **How to verify:** `dadaia public doctor` exits 0 with the rewritten rule projected;
  grep of `public/rules/` + `public/data/AGENTS.md` finds no surviving prescription to
  create a Markdown bug record; the rule instructs `dadaia bugs append`.

### AC-4 — Specs taxonomy + `_archive` FROZEN gate-class (EPIC §3)

- Create `specs/backlog/_archive/`, `specs/audits/_archive/`, `specs/bugs/_archive/`
  (workspace tree + scaffolder + consumer-onboarding paths, each with `.gitkeep`).
- `features/spec_context/gate_policy.py#classify_path`: classify these three `_archive`
  dirs as **FROZEN** for file-write tools. **Ordering note (implementation-critical):**
  the classifier currently matches the ADDITIVE prefixes (`specs/bugs/`, `specs/backlog/`,
  `specs/audits/`) *before* FROZEN, so `specs/bugs/_archive/` would resolve ADDITIVE. The
  `_archive` sub-prefixes MUST be checked *before* the ADDITIVE prefixes in
  `_classify_specs_relative`. Archive **moves** run via `git mv` (Bash), outside the gate
  envelope — FROZEN only blocks file-tool Write/Edit into the archive, not the move.
- Doctor: the three `_archive` dirs exist per class; **consumed-but-unarchived backlog**
  detection (a backlog entry with a terminal `DELIVERED|CONSUMED|SUPERSEDED` status still
  in `specs/backlog/` and not under `_archive/`); **audit-without-disposition** detection
  (an audit under `specs/audits/_archive/` must reference its disposing release).
- **How to verify:** unit test — `classify_path("specs/bugs/_archive/x.jsonl")` returns
  `FROZEN` and `classify_path("specs/bugs/20260701T00Z.jsonl")` returns `ADDITIVE`;
  gate `evaluate` BLOCKs a Write to `specs/audits/_archive/…`; `dadaia specs doctor`
  reports the new invariants; the three dirs exist in the scaffolder output.

### AC-5 — Audit-disposition law + disposition cleanup (EPIC §4, audit DRIFT-3/4)

- **The law:** the first release after an audit gives EVERY finding an explicit
  disposition (`fixed | superseded | deferred/rejected` with reason → backlog); an audit
  archives to `specs/audits/_archive/` only when all findings are dispositioned AND the
  release is approved. Encode it in the release-governance rule text (ai-engineer surface)
  and back it with the AC-4 audit-without-disposition doctor invariant. Open bugs + open
  audits outrank plain backlog at release-definition pick.
- **Cleanup (data, not code) — now VERIFY-heavy, since AC-2 does the bug archival:**
  - the **76 closed bugs** are archived **by AC-2's intrinsic in-process move** (their
    `.md` sources land under `specs/bugs/_archive/`, their JSONL streams carry the terminal
    event). Archiving a resolved bug is a source-`.md` `git mv` **only** and emits no JSONL
    event, so it cannot trip the terminal-coherence doctor (see AC-1 decision). AC-5's job
    here is to **VERIFY** `specs/bugs/_archive/` is populated and no Closed `.md` remains
    loose — not to perform the move.
  - disposition the **~14 undisposed audits** — give each a disposition pointer and
    `git mv` to `specs/audits/_archive/` where fully dispositioned.
  - normalize the off-canon statuses (SPEC-DOC-031/032): EPIC frontmatter `status:` →
    machine-terminal; the `panel-ux-overhaul` / `features-import-infrastructure-direct-debt`
    same-class entries; any bug `status:` outside `{Open, Closed}`.
  - dedupe the HTML-report bug cluster (1 Closed + 2 Open on one defect) → single event
    stream in JSONL, others `superseded`.
- **Owner:** PE (dispositions in DEFINITION/CLOSURE) + PM (backlog curation) + ai-engineer
  (law rule text). **Never delete** a bug/backlog/audit file — always terminal-status +
  reason (release-governance never-delete law).
- **How to verify:** `dadaia specs doctor` shows no consumed-but-unarchived backlog and no
  undisposed audit warnings; grep finds no `status: candidate` on a
  referenced-by-shipped-release EPIC; the HTML-report defect has one JSONL stream.

### AC-6 — OpenCode product-memory sweep (audit DRIFT-2) + minor doctor debt (DRIFT-5)

- Purge stale "OpenCode-as-live" from the ~11 atoms the audit lists: `workspace-init.md`,
  `product-vision.md`, `public-asset-distribution.md`, `harness-primitives.md`,
  `cross-platform-portability.md`, `workspace-portability.md`, `agent-sdd-alignment.md`,
  `agent-comms.md`, `agent-orchestration.md` (plus the generated `index.md` /
  `catalog.json`). The live Layer-1 harness set is `{claude, codex, pi}`.
- Regenerate the catalog: `dadaia memory catalog generate`.
- Minor doctor debt (DRIFT-5, real items only): fix the `lifecycle-foundation.md`
  `token_estimate` drift (LINT-1), the malformed audit dir name
  `specs/audits/2026-06-12T001813Z` missing its session-id suffix (SPEC-DOC-030), and the
  4 unknown-heading LINT-1 warnings (heading allowlist). Do **not** touch the
  benign/grandfathered items the audit lists (SPEC-DOC-027 legacy names, SPEC-DOC-029
  stale sample lease, TREE-5 template drift, SPEC-DOC-016 grandfathered v0.1.45).
- **Owner:** product-engineer, DEFINITION/CLOSURE phase (memory writes are gate-allowed
  only in those phases).
- **How to verify:** grep of `specs/memory/product/*.md` finds no OpenCode-as-live claim;
  `dadaia memory catalog generate` is clean; `dadaia specs doctor` clears the three DRIFT-5
  items.

---

## 4. Out of scope

- OpenCode enforcement / projection parity — **dead** (OpenCode removed v0.1.24).
- The alpha-N/rc-N ↔ gate-ladder change — shipped v0.1.15.
- Python lifecycle workflow bodies — owned by `lifecycle-prompt-fragments-ai-surface-dehydration`.
- Panel bug-analytics UI beyond minimal `dadaia bugs stats` text rendering.
- `architecture.md` rewrite — audit rates it 8/10; touch it when v0.1.44/45 close.
- Rewriting the `bug new` (singular) Markdown command's behavior beyond deprecating it in
  favour of `dadaia bugs append` — deprecation note only; no removal this release.
- The `project-auditor` bug-trend audit that clusters JSONL root causes (EPIC §4) — the
  law is spec'd here; the trend-audit tooling is a follow-up.

---

## 5. Dependencies and risks

### Sequencing (recommended)

1. **Wave A — JSONL core (AC-1, AC-2, AC-3).** Schema → store → CLI → doctor invariant →
   migration step → rule rewrite. AC-3 lands in the same PR/branch as AC-1 (R-1).
2. **Wave B — taxonomy + law (AC-4, AC-5-law).** `_archive` dirs + gate FROZEN class +
   doctor invariants + audit-disposition rule text. The `specs/bugs/_archive/` dir
   (T-46-11) must exist **before** AC-2's migration runs, because the migration moves the
   source `.md` there in-process — so B's dir-creation precedes A5's move.
3. **Wave C — cleanup + sweep (AC-5-cleanup, AC-6).** Audit dispositions + status
   normalization + OpenCode memory sweep (the 76-bug archival is done by AC-2, not here).
   Runs in DEFINITION/CLOSURE. Depends on B (dirs + doctor to verify).

### Risk table

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R-1 | **Format ships without rule-rewrite** → drift regrows exactly as it did v0.1.15 → today. | CRITICAL | AC-1 and AC-3 are a hard pair; TASKS gates AC-1 done-criterion on AC-3 landing in the same branch. Do not close the release with AC-3 open. |
| R-2 | Gate classifier ordering bug — `_archive` matched as ADDITIVE (checked first). Confirmed by both reviewers as the correct + safe fix. | HIGH | AC-4 reorders `_archive` before ADDITIVE in `_classify_specs_relative`; unit test asserts `_archive/`→FROZEN, live `*.jsonl`→ADDITIVE, AND the prefix-boundary case `_archivefoo.jsonl`→ADDITIVE (only `_archive/` with trailing slash is FROZEN). |
| R-3 | Migration lossy on Closed bugs whose frontmatter lacks a closing release. | MEDIUM | Reconstruct best-effort; emit `reported`+`resolved` with `release: unknown` sentinel + WARN; never drop a bug (never-delete law). |
| R-4 | Release too large to land cleanly in one cycle. | MEDIUM | See split recommendation below. |
| R-5 | `archived`-after-`resolved` double-terminal would ERROR on AC-5's own cleanup. | RESOLVED | AC-1 decision: `archived` is a non-terminal annotation exempt from the coherence rule; bug archival is a source-`.md` `git mv` only, no JSONL event appended → cannot trip the doctor. |
| R-6 | Audit-disposition manual sweep mixed with code in one lease → long IMPLEMENTATION window. | LOW | Wave C is PE/PM manual, disjoint write set from Wave A/B code; can run after code review. |

### Split recommendation (R-4)

This is a **large** release. Recommendation: **keep AC-1/2/3/4 and AC-6 in v0.1.46; make
the AC-5 heavy manual cleanup the natural descope valve.**

- **Must be in v0.1.46 (non-negotiable):** AC-1 + AC-2 + AC-3 (operator priority; the
  JSONL core with its rule-rewrite). Splitting AC-3 out is forbidden (R-1).
- **Should stay in v0.1.46:** AC-4 (taxonomy + gate FROZEN + doctor) — it is the landing
  zone the AC-2 migration `git mv`s into, and the AC-5 law's doctor backstop; and AC-5's
  *law* (rule text + audit-disposition doctor invariant, which is part of AC-4's doctor
  work). AC-6 is cheap, self-contained, PE-only, DEFINITION/CLOSURE — keep it.
- **Candidate to slip to v0.1.47 if the cycle runs long:** the AC-5 *cleanup data sweep*
  (dispositioning the ~14 undisposed audits + status normalization + HTML-cluster dedupe;
  the 76-bug archival is NOT in this valve — it is intrinsic to AC-2 and always ships). It
  is disjoint from the code and can follow once the law + gate + doctor exist to enforce it.
  If it slips, v0.1.46 still ships the mechanism; v0.1.47 applies it.

The JSONL core (AC-1/2/3) must not slip under any circumstance.
