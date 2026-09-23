# SPEC — Release: 0.4.7

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** product-engineer
**Opened:** 2026-09-13
**Origin:** backlog:bug-policy-one-model-ask-first,governance-verbs-telemetry,law-and-skill-dedupe
**Consumes:** bug-policy-one-model-ask-first, governance-verbs-telemetry, law-and-skill-dedupe

---

## 1. Problem and context

Candidate 3 — "one model, one verb, one home" — takes the three governance surfaces the
2026-09-12 audit found doubled (grill rulings Q5/Q6/Q9/Q13 and the registration ruling;
GV-2/GV-3/GV-12..16, BG-1/2/5/8/9/13, BL-5, SK-01..SK-24) and leaves each with one
model, one writer and one home. No bug is open (`BUGS.jsonl`: 0 `open`).

- **Two bug models.** `DADAIA.md` §1.1 fixes a bug immediately outside release material;
  §6.7 ranks open bugs at pick, `dd-release-definition` §1.4 solves every picked bug in
  the candidate, `specs/AGENTS.md:47` makes `product-engineer` the resolver (audit
  C2/C17). Lineage has two writers (`bugs update --set caused_by` at Phase 0, then
  `--caused-by` on `resolve` — C10). A seven-key provenance cache (`lineage_source
  registration_commit registration_granularity resolved_commit resolution_granularity
  root_cause migration_note`) is derived by `core/bug_provenance.py` from a full git
  walk every CI job fetches history for (`fetch-depth: 0` ×13); 476 live records carry
  a key nothing reads but pillar 1, which writes it back. §7.3 says "register every bug
  you hit"; the operator observed agents registering their own mistakes; 268 records
  carry `surface: unknown`.
- **Record changes with no verb.** A backlog item exits `active[]` by hand
  (`dd-backlog-definition`: "use file tools directly"); an audit's dispositions, histo
  record and directory deletion have no actor (SK-19); `_RELEASE.json`'s `phase`,
  `defined`, `implemented` are Read-then-Edit, and the candidate-1 reviewer found
  `release archive` hanging on a hand-edited `implemented` that `archive` itself
  validates. Hand-shaped writes already produced an invalid archived release and an
  archived `[-]` task (grill Q5). Findings say `fixed`; `core/models/histo.py` says
  `resolved`.
- **Rules in many homes.** 71 statements restated across `DADAIA.md`, 20 skills and 12
  scoped `AGENTS.md` sources, 13 with conflicting values (phase 2 §4 C1–C13). Two skills
  pass the deletion test whole (`dd-workspace-doctor`, `dd-task-manager`), one sibling
  is a second job on the wrong owner (`SPEC-REVIEW.md`), merge→ship has two procedural
  homes, the PM persona routes to eight playbooks of a retired engine, `ctx_inject`
  re-injects the fixed slop blocks (GV-16), and `constitution.md` is 12.4 KB of prose
  citing sections that do not exist (GV-3).

## 2. Objective

After candidate 3 a bug has one lifecycle (proposed → confirmed → fixed on the live
branch → `resolved` with lineage) and one record shape with no derivable cache; every
governance record change is one CLI verb that writes one governance event into the
existing telemetry store, and a hand edit is measured by `dadaia doctor` as a WARNING,
never blocked; every rule of the law, skills, personas and scoped files has one home —
measured by the body-pointer test, the verb-citation test and a skill-corpus ratchet.

## 3. Scope (candidate 3)

- FR1 — **One bug model; the agent proposes, the operator confirms.** `DADAIA.md` §7.3
  is rewritten: a bug is a reproducible violation of a tool's documented contract
  (`--help`, law, schema); an agent's own mistake, wrong usage, an environment limit, a
  designed validation, a law ambiguity or a missing feature is not one (grill or
  backlog instead); the proposal names the contract line violated, one reproducing
  command and why it is not agent error; `dadaia bugs append` runs only after the
  operator confirms; with no operator present the proposal is a handoff finding whose
  `message` starts `bug-proposal:` and whose `fix_recommendation` is the exact `dadaia
  bugs append` line (Q1) — never a record, no new CLI flag. Deleted: §6.7's pick
  line, `dd-release-definition` §1.3–1.4 (bug-always-solved, `bugs supersede` at
  pick), `specs/AGENTS.md:47`; `resolved_release` stays a recorded fact. Lineage lives
  at `resolve` only: `--caused-by <bug-id>|none` is validated as a ledger id or the
  literal `none`; Phase 0 reads prior resolutions and declares at resolve;
  `lineage_source` and the `bugs update` path die. Provenance machinery deleted:
  `core/bug_provenance.py`, `core/models/git_history.py`,
  `GitSubprocessClient.log_added_lines`, `BugEventKind`, `BugService.resolved_commit`,
  the seven schema keys, every `fetch-depth: 0` in `ci.yml` except the
  `security-verdict-gate` checkout. `BugRecord.from_dict` ignores exactly the seven
  retired keys, `to_dict` never emits them; `LEDGER-BUGS-SCHEMA` gains the one ledgers
  fix — re-serialize a record that parses but fails the schema — so `dadaia doctor
  --fix` strips the 476 live and 65 archived records losslessly (a git-derived cache).
  `surface`'s feature arm is derived at validation from the `features/*` packages on
  disk (the schema keeps six non-feature layers and `unknown`); `append --surface
  unknown` is refused, the 268 committed `unknown` records stay valid.
  `dd-bug-registration` carries the one-line severity rubric (CRITICAL a stall or data
  loss; HIGH a contract broken on the default path; MEDIUM off the default path or
  with a documented workaround; LOW message/cosmetic). AC: `bugs resolve <id>
  --caused-by not-a-bug` exits 1 naming the ledger; `grep -c '"resolved_commit"'
  specs/bugs/BUGS.jsonl` is 0 after `--fix` and `LEDGER-BUGS-SCHEMA` is clean; `bugs
  append … --surface unknown` exits 1 with `fix:`; `test_bug_record_schema.py` pins the
  derived enum; no production module imports `bug_provenance`; the CI `lint` job checks
  out at default depth.
- FR2 — **Governance events in the existing telemetry store.** `core/models/telemetry.py`
  gains `GovernanceEvent {event_id, ts, session_id, context, verb, ledger, record_id,
  record_hash}` (no content; `record_hash` = sha256 of the record's canonical JSON after
  the verb; no `agent` field — `sessions.agent_name` joins on `session_id`, Q2);
  `TelemetryStore` gains migration 7 (`governance_events`, index `(ledger, record_id,
  ts)`), `insert_governance_event`, `latest_governance_events()` (one row per `(ledger,
  record_id)`); `container.build_telemetry_store()` is the one builder, shared by
  `panel_composition` and the verbs. Every governance verb — `bugs append|update|
  resolve|supersede|defer|reject|archive`, `backlog new|exit`, `release new|phase|
  rc-archive|archive`, `audit disposition|close` — writes one event after its record
  write through one helper at the CLI root; a store that cannot open (root uid,
  permission, corrupt) logs and the verb still succeeds — an event is observability,
  never a gate. AC: `bugs append` on a fresh store leaves one row whose `record_hash`
  equals the appended line's; the seven bug verbs leave seven rows; the panel boots on
  the same file.
- FR3 — **`dadaia backlog exit`.** `dadaia backlog exit <slug> --disposition
  delivered|superseded|rejected [--release <id>] [--reason <text>]` over
  `features/backlog/document.py::backlog_exit`: `delivered`/`superseded` require
  `--release` and a `picked` entry; `rejected` requires `--reason` and exits from any
  live status; histo store and denylist built at the CLI root as `bugs` does. The
  "file tools directly" line dies; RC-FLOW step 7 names the verb. AC: one `active[]`
  object removed, one `histo-record-v1` appended; a second exit of the slug exits 1
  with `fix:`; an unknown slug names the live slugs.
- FR4 — **Audit verbs; one finding vocabulary.** `features/specs/audit.py` (beside
  `candidate.py`) and a new `dadaia audit` group: `dadaia audit disposition <dir>
  <finding-id> --disposition resolved|superseded|deferred|rejected --release <id>
  [--reason]` rewrites the governance triple through `FindingRecord.apply_governance_
  update` inside `JsonlRecordStore.update` (the model's first caller; `reason` required
  for `deferred`/`rejected`); `dadaia audit close <dir> --sha <window-end>` refuses
  while any finding is `open`, appends the one `audits_histo.jsonl` record
  (`disposition: resolved`, `release` = the one remediation release every finding
  names, `summary` = per-disposition counts, `entry` = `{sha, pillars: {bugs, specs,
  memory}, dispositions}`) and deletes the directory — all-or-nothing, every refusal a
  `fix:`. `finding-record-v1`'s enum becomes `open resolved superseded deferred rejected`
  (zero committed FINDINGS.jsonl — no migration); `doctor_closure_audit._TERMINAL_
  DISPOSITIONS` dies for `core.models.histo.FINDINGS_DISPOSITIONS`; SPEC-DOC-036/038
  `fix_help` name the verbs. Finding appends stay file-tool authoring (immutable core,
  like an ADR). AC: `close` with one `open` finding exits 1 naming the id; after
  `disposition` ×N and `close`, SPEC-DOC-038 is silent, the histo line validates, the
  dir is gone; `close` on a missing dir names `specs/audits/`.
- FR5 — **`dadaia release phase`.** `dadaia release phase IMPLEMENTATION --sha <sha>`
  requires SPEC/PLAN/TASKS at root all `**Status:** Approved` and stamps `defined {sha,
  ts}`; `dadaia release phase CLOSURE --sha <sha>` requires every task `[x]` and stamps
  `implemented {sha, rc: state.rc + 1, ts}`; another target, a wrong order or a re-run
  is refused with `fix:`; one `note` per transition; `DEFINITION` is set only by
  `release new`/`rc-archive`, `ARCHIVED` only by `archive`. `RELEASE-EVENTS.md`'s
  milestone table shrinks to the verb and `archive`; `log` entries stay
  Read-then-Edit. AC: `archive` cannot refuse on `implemented` after `phase CLOSURE`;
  `phase CLOSURE` with one `[-]` exits 1 naming the task; `phase IMPLEMENTATION` with a
  `Draft` PLAN exits 1 naming the file.
- FR6 — **A hand edit is measured, never blocked.** Term (`CONTEXT.md`): a **hand edit**
  is a governance record change with no matching governance event — distinct from
  *drift* (a projection whose bytes differ from its render). The doctor's CLI root
  reads `latest_governance_events()` once into plain data (as `live_shas` travels) and
  passes it to the `ledgers` and `specs` contexts; `LEDGER-BUGS|BACKLOG-HISTO|AUDITS-
  HISTO|RELEASES-HISTO-HANDEDIT` (WARNING, unit = record) fires when the latest event's
  `record_hash` differs from the committed record, or when a record has no event and
  is newer than the store's first governance event (the baseline is the store, never a
  date constant); `RELEASE-TREE-HANDEDIT` (WARNING) fires when the live
  `_RELEASE.json`'s `phase`/`defined`/`implemented` differ from the latest `release`
  event. No store (CI, fresh machine) = silent. `BACKLOG.json` maturation (status,
  intents, description), ADRs and memory atoms stay hand-written, doctor-validated
  (Q3). AC: `bugs resolve` then a file-tool edit of that record's `cause` yields one
  `LEDGER-BUGS-HANDEDIT` line and exit 0; a hand-flipped `phase` yields
  `RELEASE-TREE-HANDEDIT`; `doctor --json` with no store carries no `*-HANDEDIT`.
- FR7 — **One home per rule.** Skills: `dd-workspace-doctor/` deleted (one idiom line
  in `dd-cli-library`; `states-AGENTS.md` moves to a skill-less §3 row);
  `dd-task-manager/` deleted (Recovery lines fold into RC-FLOW step 1; six grants and
  the overlap pair removed); `dd-audit-project/SPEC-REVIEW.md` deleted (traceability and
  intake-routing lines move to `dd-release-definition` Done-when; description and §3
  go); RC-FLOW ends at step 9 with one pointer to `dd-gitflow-default` steps 11–14,
  gitflow §2 drops steps 5–7 for a §4.2 citation; `dd-manager-orchestration` drops the
  agent inventory, the stage table, the pre-implementation agreement and rewrites the
  two Forbidden rows contradicting §2/§6; `dd-backlog-definition` keeps curation +
  intake + pick and cites `scaffold/backlog/AGENTS.md` (whose stale `entry_md` line
  dies); `dd-handoff-emitter` owns emission, `data/handoff-AGENTS.md` keeps scope +
  read rules; `dd-bug-registration`/`dd-bug-resolution`/`LINEAGE.md`/`PILLAR-BUGS.md`/
  `FINDINGS-FORMAT.md` say FR1/FR4 once (pillar 1 loses the cache section and metric
  1's granularity column; its registrations-per-session metric reads governance
  events); `dd-architecture-survey` is granted to `software-architect` (flag dropped,
  RC-FLOW step 3 names it). Every C1–C13 conflict resolves by deleting the wrong copy;
  the SK-17 provenance lines and the SK-14 dead pointers (PM playbook table and the
  eleven listed lines) are deleted; reviewer personas and `registry.json` carry one
  sentence ("validates at candidate close, RC-FLOW step 4"; three-axis); the nine
  personas lose the restated `handoff-v1.2`/`self_pull` bullet; `product-engineer`
  gains `Bash` (Q4); `templates/specs-AGENTS.md` is rewritten to ≤ 20 statements (load
  order → `dd-spec-navigator`, authority table, escalation; no gate claim, no root
  `_archive/`, bugs resolved on the live branch), its map row moves to §6 and
  `repo-AGENTS.md`'s to §5; `constitution.md` keeps frontmatter, the fixed block and
  the statements that exist nowhere else — identity, the operational-change lane,
  dispatcher purity, the versioning rule — at `constitution_version` 6.0.0 (Q5);
  `scaffold/memory/AGENTS.md` repoints §13 to `DADAIA.md` §6.4;
  `ctx_inject._fixed_law_blocks` is deleted. `DADAIA.md`: §6.6 (exit by verb), §6.7
  (pick line deleted; `release phase`), §6.8 (`resolved`; the two verbs), §7.3 (FR1,
  six bullets), §8.5 (`*-HANDEDIT`), §10.2 (governance verb, governance event, hand
  edit, bug proposal). Measures: `test_every_cited_dadaia_verb_exists` (existing) for
  every verb the law cites; `test_behavior_map.py` gains the body-pointer finder —
  every backticked `dd-*` token and every `` `dd-x` §N `` pair in `public/agents/*.md`
  and `public/skills/**/*.md` resolves to a skill dir and a `## N.` heading;
  `test_slop_ratchets.py` gains V35: skill dirs ≤ 18 and `public/skills/**/*.md` total
  lines pinned at the post-candidate value, down only. AC: `grep -rn "outrank\|
  bug-always-solved\|lineage_source\|Six-axis\|playbook\|SPEC-REVIEW\|dd-task-manager\|
  dd-workspace-doctor" dadaia_workspace/public CONTEXT.md specs/constitution.md` is
  empty; `dadaia public doctor` reports `[ok] public-privacy`; V35 pins ≥ 180 lines
  below 3,160.
- FR8 — **Closure.** Memory atoms `sdd-bug-backlog-governance`, `audits-canon`,
  `agent-monitoring`, `agentic-entities`, `agent-orchestration`, `workspace-doctor`,
  `harness-claude-code`, `public-asset-distribution`; `ARCHITECTURE.md` Part 1 deletes
  P-16 (its measure dies with FR1) with the one accepted-at-append decision record
  (grill ruling 2026-09-12) in the same commit, Part 2 rows for `GovernanceEvent`,
  `features/specs/audit.py`, the phase verb, the `*-HANDEDIT` codes; `TECHSTACK.md`
  where it names the CI history fetch; `CHANGELOG.md [0.4.7]` candidate 3; reprojection
  (`public stage` → `install --target all` → `public doctor`); full preflight; `dadaia
  doctor` 100 % on this instance; CLOSURE entered by `dadaia release phase CLOSURE`.

## 4. Out of scope

- Documentation derived from memory, distribution metadata — the docs candidate.
- A `BACKLOG.json` maturation verb (`idea → candidate → picked`, intents) and a
  `release log` verb — hand-written, doctor-validated (Q3).
- The verdict file model, presence, the eight deferred standards replacements.
- Renaming `TERMINAL_EVENTS`; the `audited` bug field (pillar 1 still stamps it).
- Any Part-1 principle beyond P-16's deletion; if review finds another moved, its
  decision record lands in the same commit.

## 5. Dependencies, risks, questions

- Sequencing: candidate 2 (T-047-20..24) is editing `hooks/**`, `features/spec_context/**`,
  `dd-workspace-doctor`, `dd-task-manager`, `dd-cli-library`, `dd-bug-registration`;
  candidate 3 starts after its merge and rc-archive — FR7 deletes two of those skills.
- FR1's `--fix` rewrite touches 541 committed lines in one `chore(bugs): strip retired
  provenance keys` commit, reviewed as a key-strip only (`jq del(...)` equivalence
  recorded in the closure `size` entry).
- FR2's store lives at `~/.dadaia/state/telemetry/` (operator home, one per machine):
  two workspaces on one machine share a file — `context` on the event keeps them apart;
  CI never has one, so FR6 is silent there.
- FR6 baseline: a record older than the store's first event is never a hand edit —
  the 564 existing bug records enter measurement only when a verb touches them.
- FR7 is the largest AI-entity diff of the release (≈ −180 skill lines, two dirs, one
  sibling, nine personas); `ai-engineer` owns it end to end, behavior-map hashes
  re-recorded once at the end.
- Net: deletions (provenance module, models, reader method, seven keys, twelve
  `fetch-depth` lines, `BugEventKind`, resolver, second lineage home, two skill dirs,
  one sibling, RC-FLOW 10–12, three tables, playbook table, fixed-block injection,
  ~14 provenance lines, `_TERMINAL_DISPOSITIONS`, constitution prose) against additions
  (one event model + table + helper, three verbs in two groups, one transition verb,
  two doctor codes, one finder, one ratchet). Production net is expected negative; the
  closure `summary` applies the deletion test to every addition.

Q1–Q6 answered by the PM under the operator's 2026-09-12 directive (each reversible in
one commit; Q4 and Q5 flagged to the operator):

- Q1 `bug-proposal:` message prefix on an ordinary handoff finding, no schema bump.
- Q2 event fields `record_hash` + `ts`, no `sha` (a verb never runs git), no `agent`
  field (join on session).
- Q3 hand-edit scope = `BUGS.jsonl`, the three histos, `_RELEASE.json` phase and
  milestones; `BACKLOG.json` maturation, ADRs, memory atoms and the `log` stay hand-written.
- Q4 `product-engineer` gains `Bash`; `dd-cli-library`'s shell-less clause dies.
- Q5 constitution survivors: identity, operational-change lane, dispatcher purity,
  versioning; every article already stated in DADAIA deleted; `constitution_version` 6.0.0.
- Q6 one `audit disposition` verb with a closed `--disposition` option.
