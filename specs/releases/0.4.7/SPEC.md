# SPEC — Release: 0.4.7

**Status:** Draft
**Release ID:** 0.4.7
**Owner:** product-engineer
**Opened:** 2026-09-12
**Consumes:** release-lifecycle-verbs, one-doctor-one-rule-registry, adr-ledger-hygiene, memory-hygiene

---

## 1. Problem and context

The 2026-09-12 SDD lifecycle audit (handoff `2026-09-12T181306Z`, grill rulings
Q1–Q17) found every doctor green while the governance tree was not conformant:
the newest archived release state failed its schema and the parser raised on it;
six of ten ADR records failed their schema; 27 backlog history records sat in a
provisional state no writer finalized; the instance memory law was a prose rewrite
of its source; and no live release existed on a minted branch, so the gate blocked
every memory write (a stall). One cause: schemas exist for live documents only and
are tested against synthetic fixtures; the three history ledgers have no schema and
no reader; the release state has one parser, three writers and zero readers of
archives; `dadaia release new` never creates the state file every resolver keys on.

Candidate 1 — "records tell the truth" — makes the records validated, the
compliance surface single, and the release lifecycle tool-driven, all
deletion-shaped: no new branch, no second path, no puxadinho.

## 2. Objective

After candidate 1 a schema-invalid or hand-drifted governance record cannot coexist
with a green `dadaia doctor`, and a release is born, archived and succeeded by one
CLI verb each, validated by one shared validator.

## 3. Scope (candidate 1)

- FR1 — **One release-tree validator.** `features/specs` exposes
  `validate_release_tree(specs_dir)`: every `_RELEASE.json` (live, `_ideas`
  excluded, every `_archive/<id>/`) validates `release-state-v1` and parses;
  `log[].ts` monotonic; `phase` ∈ {DEFINITION, IMPLEMENTATION, CLOSURE, ARCHIVED};
  archived dirs carry ARCHIVED; the live release carries its trio; `log[].kind` ∈
  the schema enum. Readers: the doctor (FR5), `rc-archive`, `release archive`
  (FR3) and one contract test over the real tree. AC: the 0.4.6 document as
  committed before Wave 0 fails the validator; `specs doctor` today reports it.
- FR2 — **`dadaia release new <id>` is the one birth act.** Writes `SPEC.md`
  stub and `_RELEASE.json` (phase DEFINITION, `rc: null`, one `note` log entry)
  in one transaction; refuses a second live release with a `fix:` line. AC: after
  `release new`, `dadaia context show` resolves the release and the gate's MEMORY
  class resolves DEFINITION.
- FR3 — **`dadaia release archive <id> --shipped <sha> --pr <n> --next <M.m.p>`.**
  Validates with FR1 plus: every task `[x]`, phase CLOSURE, `implemented` set;
  sets `shipped` and ARCHIVED; moves the whole directory to `_archive/<id>/`;
  appends the `releases_histo.jsonl` record (FR7 shape); births `<next>` via
  FR2; runs `bugs archive` (FR4); all-or-nothing (nothing written on any
  refusal). Prints the git `next:` lines (branch delete, cut) and never runs git.
  `rc-archive` shares the validator and the `bugs archive` call. AC: a dry
  fixture tree with one `[-]` task is refused with a `fix:` line and no file
  changes; the promote lane has no manual `git mv` step left in any skill.
- FR4 — **Release schema and bug archive threshold.** `release-state-v1` drops
  `segment` and `audited`, enumerates `log.kind`
  (`note summary size drifts dispositions test-dispositions artifact-gc reviews
  merge memory`); `core/release_state.PHASES` shrinks to the four phases;
  `rc-archive` parks the release in DEFINITION, not DISCOVERY. Every terminal bug
  verb writes `closed_at` (write-once); `bugs archive` ages by `closed_at` only;
  a one-time back-fill sets `closed_at` on the 507 live terminal records from the
  ledger commit that made each terminal. AC: no record is archivable by filing
  date; SPEC-DOC-041 counts by `closed_at`.
- FR5 — **One compliance surface.** `dadaia doctor` runs three sections —
  `workspace` (zones, root, harness dirs), `specs` (the SPEC-DOC rules),
  `ledgers` (FR6) — over one rule registry each feature contributes to; every
  finding is one line `<CODE> <verdict> <message>`; each section ends with
  `compliance(<section>): N/M <unit> canonical (P%)` and the run with a total
  line; one `--json`; exit 1 on any error-class finding; `--fix` scope unchanged.
  `dadaia specs doctor` and `dadaia backlog doctor` are deleted (not aliased);
  `--specs-dir`/`--context` move to `dadaia doctor`. AC: the Wave 0 instance
  before repair scores `< 100%` on `ledgers` and `specs`.
- FR6 — **Every committed governance record validates.** The `ledgers` section
  validates `decisions.jsonl` (`decision-record-v1`), `BACKLOG.json`,
  `BUGS.jsonl`, every `_RELEASE.json` (FR1) and every `_histo.jsonl` (FR7) with
  the one validator per schema; `test_adr_canon.py` uses the schema validator
  (its hand-rolled `_record_violations` deleted); a scaffolded `AGENTS.md` whose
  bytes match neither its source nor shipped history is a `specs` finding
  (`copy-drift`); `public/data/memory-AGENTS.md` (byte twin of the scaffold) is
  deleted and the behavior-map row corrected. AC: the six pre-Wave-0 ADR records
  and the prose `specs/memory/AGENTS.md` are findings.
- FR7 — **One history record shape.** `histo-record-v1`:
  `{id, ts, disposition, release, reason, summary, entry}` (`entry` = the removed
  backlog object or null). One lowercase terminal vocabulary in
  `core/models` — `delivered resolved superseded deferred rejected` — each
  ledger's schema naming its subset (backlog: delivered/superseded/rejected;
  bugs: resolved/superseded/deferred/rejected; findings: resolved/superseded/
  deferred/rejected). Migrations, one pass each: `backlog_histo.jsonl` (drop
  `entry_md_source`, `by`; JSON snapshots become `entry`), `audits_histo.jsonl`
  (event wrapper removed; window-end sha and per-pillar counts in `summary` for
  canon-era audits), `releases_histo.jsonl` (one record per release, notes
  folded into `summary`). `consumed_backlog_histo.jsonl`, `features/backlog/
  ledger.py`, `ConsumedBacklogHistoRecord`, its store builder, BL-STALE (a) and
  their tests are deleted; the provisional `CONSUMED` token and the SPEC-DOC-031
  duplicate of BL-STALE are deleted (a picked item stays `picked` in `active[]`
  and exits once, at closure). The audit window is read from `audits_histo`.
  AC: `dadaia doctor` validates all three histories; no writer of `CONSUMED`
  survives in code or skill text.
- FR8 — **ADR ledger.** `status: superseded` in place; `_superseded/` and its
  move rule deleted from canon, law and test; a record born from an operator grill
  ruling is `accepted` at append with the ruling date in `context`; `measured_by`
  must match the resolvable pattern (`pytest <path>[::node]`, `lint-imports …
  contract <name>`, `SPEC-DOC-nnn`, `WS-…`, `BL-…`) before `accepted`; DADAIA
  §6.5 reworded to one decision per change set naming every principle touched;
  P-02 corrected to `ADR: none`. AC: ADR 0005–0009's prose `measured_by` is a
  finding until rewritten to a resolvable check; ADR 0004/0010 carry the
  operator's accept/reject decision (decision required, `_RELEASE.json` log).
- FR9 — **Memory hygiene.** The wikilink alias table (`memory_canon.py`,
  `memory_lint.py`) is deleted and the 15 links point at
  `ARCHITECTURE.md`/`TECHSTACK.md`/`QUALITY.md`; `_TLDR_INJECTED_CATEGORIES` is
  deleted and `catalog.json` carries `tldr` for every atom; `category` leaves
  `memory-frontmatter-v1` (five fields; DADAIA §6.4 updated); the closure memory
  pass logs `kind: memory` with atoms reviewed-unchanged vs changed; the two stale
  facts (`chokepoints is four modules`, "release directory and CHANGELOG carry
  the same digits") are corrected in their one home; the generated index heading
  is English. AC: LINT-1 passes without the alias table; the ctx-inject digest
  carries a `tldr` per atom.
- FR10 — **Law and skills, only where this candidate changed behavior.** DADAIA
  §6.2 (canon members: `releases_histo.jsonl`, no `consumed_backlog_histo`, no
  `_superseded/`), §6.4, §6.5, §6.6 (one exit at closure), §6.7 (birth and
  archive verbs), §6.8 (window from `audits_histo`), §8.5 (one doctor);
  `specs/releases/AGENTS.md`, `specs/backlog/AGENTS.md`, `specs/ADRs/AGENTS.md`,
  `specs/audits/AGENTS.md` scaffolds; `dd-release-definition`,
  `dd-release-implementation` (RC-FLOW steps 9–12 → the two verbs;
  RELEASE-EVENTS shape), `dd-backlog-definition` (no provisional token, `exit`
  named as the one path even though the verb lands in candidate 3),
  `dd-audit-project` (window), `dd-cli-library`, `dd-workspace-doctor` (doctor
  sections); behavior-map hashes; re-projection; `CONTEXT.md` (Stall recorded in
  Wave 0; Histo record, Compliance section, Doctor section added).
- FR11 — **Closure.** Memory atoms `specs-doctor`, `workspace-doctor`,
  `audits-canon`, `sdd-bug-backlog-governance`, `pypi-distribution` updated;
  `CHANGELOG.md [0.4.7]` candidate 1 section; full preflight; `dadaia doctor`
  100 % on this instance; candidate CLOSURE.

## 4. Out of scope

- The gate (context-scope rule, anti-stall contract test, MEMORY-phase deletion),
  the canon registry, the reaper and the privacy-scan scope — candidate 2.
- Bug policy, `backlog exit`, `audit close`, telemetry events, the law/skill
  dedupe — candidate 3.
- The eight deferred standards replacements (backlog ideas).
- Renaming archived release directories (0.5.x ids stay as history).

## 5. Dependencies and risks

- FR5 deletes two commands; every skill and law line naming `specs doctor` or
  `backlog doctor` is rewritten in FR10 in the same candidate — a stale pointer
  is a finding of the body-pointer test that lands in candidate 3, so FR10 is
  checked by grep at closure.
- FR7 migrations rewrite history files in place: immutable-core fields (`id`,
  `ts`, `disposition` once terminal) are byte-preserved; a migration is one
  commit per file with the record count before/after in its message.
- FR4's `closed_at` back-fill reads `git log -- specs/bugs/BUGS.jsonl` on this
  branch only (squash lineage): the date is the terminal commit's, never earlier
  than `ts`; the validator refuses `closed_at < ts`.
- Wave 0 already performed the data repairs FR1/FR6/FR7 would have flagged; the
  tests land against fixtures that reproduce the pre-repair state.
- ADR 0004 and 0010 need an operator decision inside this candidate (FR8).
