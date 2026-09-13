# TASKS — Release: 0.4.7

**Status:** Aprovado
**Release ID:** 0.4.7
**Owner:** product-engineer

---

## Candidate 3 — one model, one verb, one home

- [x] T-047-25 — FR1: delete `core/bug_provenance.py`, `core/models/git_history.py`,
  `GitSubprocessClient.log_added_lines`, `BugEventKind`, `BugService.resolved_commit`
  and the seven schema keys; `from_dict` ignores the retired keys, `to_dict` never
  emits them; `LEDGER-BUGS-SCHEMA` fix re-serializes a parseable record (`--fix` strips
  the committed ledger + histo, one `chore(bugs)` commit); `resolve --caused-by`
  validated against the ledger or `none`; `surface` feature arm derived from
  `features/*` at validation, `append --surface unknown` refused; `ci.yml` keeps
  `fetch-depth: 0` on `security-verdict-gate` only; tests deleted with the machinery
  (RED: `from_dict` on a legacy line, the strip fix, the refused `--caused-by`). Write
  set: `dadaia_workspace/core/{bug_provenance.py,models/bugs.py,models/git_history.py}`,
  `dadaia_workspace/infrastructure/git_subprocess.py`, `dadaia_workspace/features/bugs/
  service.py`, `dadaia_workspace/features/specs/ledgers.py`, `dadaia_workspace/cli/
  commands/{bugs,doctor}.py`, `dadaia_workspace/container.py`, `dadaia_workspace/public/
  schemas/bugs/bug-record-v1.schema.json`, `.github/workflows/ci.yml`, `specs/bugs/**`,
  `tests/**`. Blocked by: none. Delivers: one bug record shape with no derivable cache;
  `doctor --fix` heals every committed record; CI checks out shallow.
- [x] T-047-26 — FR2: `GovernanceEvent` in `core/models/telemetry.py`; migration 7 +
  `insert_governance_event` + `latest_governance_events()` in `features/telemetry/
  store.py`; `container.build_telemetry_store()` shared with `panel_composition`;
  `cli/_governance_event.py` (build, hash, insert, swallow OSError); the seven `bugs`
  verbs write one event each (RED: a fresh store holds one row per verb whose hash
  equals the record). Write set: `dadaia_workspace/core/models/telemetry.py`,
  `dadaia_workspace/features/telemetry/store.py`, `dadaia_workspace/container.py`,
  `dadaia_workspace/cli/_governance_event.py`, `dadaia_workspace/cli/commands/
  {bugs,panel_composition}.py`, `tests/**`. Blocked by: T-047-25. Delivers: `dadaia
  bugs append` leaves one governance event the panel's store can be queried for.
- [-] T-047-27 — FR3: `dadaia backlog exit <slug> --disposition delivered|superseded|
  rejected [--release] [--reason]` over `backlog_exit` (rules per disposition, `fix:` on
  every refusal, denylist from the container) + its event; `backlog new` writes an
  event. Write set: `dadaia_workspace/cli/commands/newartifacts.py`,
  `dadaia_workspace/features/backlog/document.py`, `tests/**`. Blocked by: T-047-26.
  Delivers: a backlog item exits by one verb, one histo record, one event.
- [ ] T-047-28 — FR4: `features/specs/audit.py` (`disposition_finding`, `close_audit`,
  all-or-nothing, histo append last); `cli/commands/audit.py` group `dadaia audit
  disposition|close` registered in `cli/main.py`, each writing an event;
  `finding-record-v1` enum `open resolved superseded deferred rejected`;
  `doctor_closure_audit._TERMINAL_DISPOSITIONS` → `core.models.histo.FINDINGS_
  DISPOSITIONS`; SPEC-DOC-036/038 `fix_help` name the verbs (RED: `close` with an open
  finding; `disposition deferred` without `--reason`; the histo line's `entry` counts).
  Write set: `dadaia_workspace/features/specs/{audit.py,doctor_closure_audit.py,
  rules.py}`, `dadaia_workspace/cli/{main.py,commands/audit.py}`, `dadaia_workspace/
  core/models/{findings,histo}.py`, `dadaia_workspace/public/schemas/audits/
  finding-record-v1.schema.json`, `tests/**`. Blocked by: T-047-26. Delivers: an audit
  is dispositioned and archived by two verbs; the finding vocabulary is one.
- [ ] T-047-29 — FR5: `dadaia release phase IMPLEMENTATION|CLOSURE --sha <sha>` in
  `features/specs/candidate.py` (trio `Aprovado` check, every-task-`[x]` check, stamps
  `defined`/`implemented {sha, rc: rc+1, ts}`, one `note`, refuses order/re-run with
  `fix:`), CLI in `newartifacts.py`; `release new|rc-archive|archive` write events (RED:
  `phase CLOSURE` with a `[-]`; `archive` after `phase CLOSURE` never refuses on
  `implemented`). Write set: `dadaia_workspace/features/specs/candidate.py`,
  `dadaia_workspace/cli/commands/newartifacts.py`, `tests/**`. Blocked by: T-047-27.
  Delivers: `_RELEASE.json`'s phase and milestones move only by verb; `archive` cannot
  hang on a hand-set milestone.
- [ ] T-047-30 — FR6: the doctor CLI reads `latest_governance_events()` once into
  plain data; `LEDGER-<NAME>-HANDEDIT` (BUGS + three histos, WARNING, hash mismatch or
  no event newer than the store's first) in `ledgers.py`; `RELEASE-TREE-HANDEDIT` in
  `release_tree.py` for `phase`/`defined`/`implemented`; silent with no store (RED: a
  file-tool edit after `bugs resolve`; a hand-flipped phase; no store → no finding).
  Write set: `dadaia_workspace/cli/commands/doctor.py`, `dadaia_workspace/features/
  specs/{ledgers.py,release_tree.py,rules.py}`, `tests/**`. Blocked by: T-047-28,
  T-047-29. Delivers: a hand edit of a verb-owned record is one WARNING line, exit 0.
- [ ] T-047-31 — FR7a (`ai-engineer`): delete `dd-workspace-doctor/`, `dd-task-manager/`,
  `dd-audit-project/SPEC-REVIEW.md`; RC-FLOW ends at step 9 (+ pointer, Recovery lines
  in step 1, step 3 names `software-architect`, step 7 names `backlog exit`/`audit
  close`, step 5 names `release phase`); gitflow §2 steps 5–7 → §4.2 citation;
  `dd-manager-orchestration` tables/agreement/Forbidden rows/router line;
  `dd-backlog-definition`, `dd-handoff-emitter`, `dd-cli-library` (doctor idiom, no
  shell-less clause), `dd-release-definition` (§1.3–1.4 deleted, two Done-when lines),
  `dd-bug-registration` (ask-first, rubric, `bug-proposal:`), `dd-bug-resolution` +
  `LINEAGE.md` (lineage at resolve), `PILLAR-BUGS.md`, `FINDINGS-FORMAT.md`,
  `MEMORY-UPDATE.md` header, `dd-release-implementation/SKILL.md` numbering, C1–C13
  copies and SK-17 provenance lines deleted; `dd-architecture-survey` flag dropped;
  `behavior-map.json` rows/overlaps/hashes; body-pointer finder in
  `test_behavior_map.py`; V35 in `test_slop_ratchets.py` (RED on today's corpus for
  `dd-bug-registration §5`, `reports-AGENTS.md`). Write set: `dadaia_workspace/public/
  skills/**`, `dadaia_workspace/public/entities/behavior-map.json`, `tests/**`. Blocked
  by: T-047-29. Delivers: 18 skills, every skill pointer resolves, the corpus ratchet
  is pinned.
- [ ] T-047-32 — FR7b (`ai-engineer`): personas (playbook table, `--with-report`, dead
  pointers, checkpoint sentences, `handoff-v1.2` bullets, `product-engineer` `Bash` +
  grants, `software-architect` grant, `dd-task-manager`/`dd-workspace-doctor` grants
  removed); `registry.json` mandates (three-axis, candidate close); `DADAIA.md` §6.6–6.8,
  §7.3, §8.5, §10.2; `data/handoff-AGENTS.md`; `scaffold/{backlog,bugs,audits,memory}/
  AGENTS.md`; `templates/specs-AGENTS.md` ≤ 20 statements + map rows §6/§5;
  `constitution.md` (survivors, 6.0.0); `CONTEXT.md` (hand edit, governance verb,
  governance event, bug proposal); `ctx_inject._fixed_law_blocks` deleted; `public
  stage` → `install --target all` → `public doctor`; grep proves no retired term
  survives. Write set: `dadaia_workspace/public/{agents,data,scaffold,templates}/**`,
  `dadaia_workspace/public/entities/registry.json`, `dadaia_workspace/hooks/
  ctx_inject.py`, `CONTEXT.md`, `specs/constitution.md`, the instance projections via
  the CLI, `tests/**`. Blocked by: T-047-31. Delivers: law, personas, scaffolds and the
  glossary say one thing about bugs, verbs, hand edits and the corpus.
- [ ] T-047-33 — FR8 closure: `CHANGELOG.md [0.4.7]` candidate 3; preflight; `dadaia
  doctor` 100 %; `dadaia release phase CLOSURE --sha`; the three `backlog exit`
  records; `_RELEASE.json` `summary`/`size`/`drifts`/`test-dispositions`/
  `dispositions`/`artifact-gc`/`reviews` entries; the memory pass (the eight atoms,
  `ARCHITECTURE` P-16 deletion with its accepted decision record in the same commit,
  Part 2 rows, `TECHSTACK` fetch line) is closure procedure (RC-FLOW step 5), never a
  task write set. Write set: `CHANGELOG.md`, `specs/releases/0.4.7/**`,
  `specs/backlog/**`, `specs/bugs/**`, `specs/ADRs/decisions.jsonl`. Blocked by:
  T-047-32. Delivers: candidate 3 closed, ready for the `feature → develop` PR and the
  promote-or-continue gate.
