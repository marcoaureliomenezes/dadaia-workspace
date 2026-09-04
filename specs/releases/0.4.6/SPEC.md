# SPEC — Release: 0.4.6

**Status:** Aprovado
**Release ID:** 0.4.6
**Owner:** product-engineer
**Opened:** 2026-09-03

---

## Candidate 4 — workspace instance compliance: one zone registry, one doctor

## 1. Problem and context

- The `.dadaia/` canon is a bare name list declared three times (`core/workspace_layout.
  DADAIA_ALLOWED_SUBDIRS`, `features/workspace/service._DADAIA_DURABLE_DIRS`, `core/models/
  hygiene.SlopPolicy.durable_top_level_dirs`) — no creator, class or TTL per name.
- Six ledger bugs edited that list in eight weeks, none changed its shape:
  workspace-doctor-root4-false-positive-dadaia-hooks (b8c40708), reconcile-legacy-dadaia-dirs-
  unmigrated (c0f4656f: a SECOND list + a quarantine mover), doctor-whitelist-legitimizes-slop-dirs
  (0f6d6e03), doctor-misses-root4-nonsense-directory + doctor-flags-product-created-dadaia-dirs-
  as-unknown (2ffc7d57: too wide and too narrow at once), dadaia-reconcile-quarantines-sanctioned-
  references-clone (92b8b3d6: list 2 derived from list 1, still two lists).
- Cleanup is split over four engines (`dadaia clean`, `dadaia tmp gc`, `dadaia reports cleanup`,
  `dadaia doctor --fix`) with three TTL authorities; only `tmp gc` ever ran unattended.
- Measured on this instance 2026-09-03: `tmp/` 5,599 of 5,706 files past TTL (402 MB); handoffs
  224 of 244 past TTL; 105 files in `.dadaia/reports/`; `states/` 74 files, 13 canonical; 8 wheels
  in `dist/`; `.dadaia/{runs,scripts,logs,academy}` and `states/lifecycle` have zero readers.
- `dadaia doctor` ROOT-1 flags the root `.env` that `DADAIA.md` §9 declares the credential home:
  bug doctor-root1-flags-env-that-dadaia-md-9-declares-canonical (open, picked, fixed by FR7);
  `states/harness_profile.json` is absent; `root_exceptions.txt` carries `.mcp.json` three times.
- Sources: grill `2026-09-03T140000Z-claude-workspace-compliance-grill` (16 decisions, §7);
  architect DRAFT `2026-09-03T153000Z-software-architect-workspace-compliance-draft` (A-G).
  Every decision is settled: this SPEC records, it does not reopen.

## 2. Objective

Measure compliance of the instantiated workspace the way `specs doctor` measures `specs/`: one
registry in `core` names every `.dadaia/` zone with class, creator, TTL and closed file canon;
`dadaia doctor` is the one scan and the one reaper over root, harness dirs, `.dadaia/` and
`states/`; four zones and four cleanup engines retire; export is one JSON file; the
`.dadaia/AGENTS.md` table is rendered from the registry. Net production diff about -7,460 lines.

## 3. Vocabulary

- **Zone** — one top-level `.dadaia/` directory with a `Zone(name, cls, creator, ttl_seconds,
  canon, purpose)` record in `core/workspace_layout.DADAIA_ZONES`. Classes: `projection state
  protected operator output ephemeral managed`; creators: `init install runtime operator`.
- **Finding verdict** — the classification of one scanned entry: `canon | operator | slop |
  expired | missing`; always qualified "finding verdict" — the bare `verdict` stays the PR
  approval record (`CONTEXT.md`). `canon` + `operator` count as canonical.
- **Finding code** — `WS-<zone>-<verdict>`; `<zone>` is `root`, a harness dir (`claude codex
  kimi-code agents`), `dadaia` (the `.dadaia/` top level) or a zone name with its leading dot
  stripped (`cache`). Examples: `WS-root-slop`, `WS-states-missing`, `WS-tmp-expired`.
- **Finding line** `WS-tmp-expired  tmp/claude/20260801/x.png  (mtime 33d > ttl 1d)`; **score
  line**, last of every run: `compliance: N/M entries canonical (P%)`, M = every entry
  classified in the walk, N = canon + operator.
- **Instance exceptions** — `states/instance_exceptions.txt`: one glob per line, `#` comments,
  deduplicated, order kept; matches at root and inside the harness dirs; outside the projection
  manifest and outside the exceptions = slop. Replaces `root_exceptions.txt`.
- The four terms enter `CONTEXT.md` in FR1's commit.

## 4. Functional requirements

Each FR cites the decision (D-n, §7) or architect section (A-G) it traces to.

- **FR1 — Zone registry** (D14, D16, A; finding 1). `core/workspace_layout.py` gains `ZoneClass`,
  `Creator`, `Zone`, `DADAIA_ZONES` (11 rows: `agentic hooks states sessions handoff tmp mcps
  .cache dist references .venv`), `STATES_CANON`, `DADAIA_ROOT_FILES = {AGENTS.md, .gitignore}`,
  `INSTANCE_EXCEPTIONS`, pure `parse_exception_globs(text)` and one pure derived view per
  consumer (init creates; doctor allows / expires / closed canon / never walks; gate ADDITIVE
  prefixes; table rows). `DADAIA_ALLOWED_SUBDIRS`, `DADAIA_ADDITIVE_PREFIXES`,
  `_DADAIA_DURABLE_DIRS`, `_DADAIA_EPHEMERAL_DIRS`, `_EMPTY_ACADEMY` and `core/models/hygiene.py`
  are deleted. No new leaf: `workspace_layout` is already the I/O-free single authority.
- **FR2 — Ratchets born with the registry** (D14, F). `tests/contract/test_zone_registry.py`:
  (1) the rendered `dadaia-AGENTS.md` table rows equal `DADAIA_ZONES` and the `states-AGENTS.md`
  canon table equals `STATES_CANON`; (2) no set/tuple/list literal outside `workspace_layout.py`
  holds 3+ zone names and no string literal equals `.dadaia/<retired>` for `reports academy logs
  runs scripts dev-report runtime`; (3) every `creator` maps to a live module. Same commit as FR1.
- **FR3 — One scan** (D9, D10, D11, B). `DoctorService._scan_zones()` walks in fixed order:
  root (ROOT_ALLOWED -> canon; exception glob -> operator; else `WS-root-slop`); harness dirs
  (an entry the install ledger names, read inside the one walk via `JsonInstallLedgerStore`, or
  an exception glob -> canon/operator; else `WS-<harness>-slop`; an unreadable ledger yields one
  non-fixable `WS-states-missing states/install_ledger.json` and classifies nothing under the
  harness dirs, bug doctor-unreadable-install-ledger-classifies-projections-as-slop 50de406b;
  `public doctor` keeps hash drift only); `.dadaia/` top level (`DADAIA_ROOT_FILES` / zone name
  -> canon; else `WS-dadaia-slop`; INIT/INSTALL zone absent -> `WS-<zone>-missing`); closed-canon
  zones `states dist sessions` (non-canon -> slop; seedable absent -> missing); TTL zones
  `handoff tmp mcps .cache` (file older than `ttl_seconds` by mtime -> expired; a directory
  emptied by expiry -> expired). `operator` and `managed` zones are never walked; symlinks never
  followed; every deletion target `resolve().relative_to(dadaia)`-guarded once. Deleted:
  `ROOT-1..4`, `RETIRED-LOCK-STATE`, `EFF-1`, `_root_exception_globs`, `_ROOT_FORBIDDEN_CACHES`,
  `_ROOT_TOOL_CONFIGS`. Unchanged: `INV-4/5/6`, `CTX-URL-1`, `VENV-1`, `PRESENCE-GC`. Output:
  one finding line each + the score line; exit 1 on any slop, expired or missing; `--json` ->
  `{"issues":[...],"findings":[{code,path,verdict,fixable,detail}],"compliance":{canonical,
  total,percent},"fixed":[...]}` (`issues` = the surviving INV/VENV/PRESENCE checks).
- **FR4 — The one reaper** (D8, D9, D13, B, E). `dadaia doctor --fix` runs in order:
  `presence.gc` -> `session_store.reap_stale` -> migrate the exceptions file (FR6) -> seed
  missing -> delete expired -> delete slop. `--fix --expired-only` stops after "delete expired"
  and is the SessionStart lane: one command entry per harness runtime config, `<venv>/dadaia
  doctor --fix --expired-only --quiet` (Claude `matcher: startup|resume`; Codex via the hook
  wrapper command); `--quiet` prints only when something was deleted. A CLI process, never a
  hook module (P-12). Deleted: `dadaia clean`, `dadaia tmp gc`, `dadaia reports cleanup|status|
  mark-important|unmark-important|important|mark-efficiency-audit|lint|next`,
  `features/workspace_clean/`, `features/tmp_gc/`, `features/reports/{retention,next}.py`,
  `features/migrate/legacy_dadaia_dirs.py` (+ its reconcile call and setup.cfg ignore edge).
  Skip-and-report: an undeletable entry is a skipped action with its errno, stays a finding,
  exit 1, never raises (bug doctor-fix-aborts-whole-pass-on-first-undeletable-entry, b2b302f9).
  INV-5 dead-repo removal is the last step, after the `--expired-only` return.
- **FR5 — TTLs** (D5, D7). `handoff tmp mcps .cache`: 86,400 s by mtime; no importance ledger,
  no report pairing; a zone's own `AGENTS.md` is canon by projection, never a TTL candidate (bug
  public-install-restores-expired-zone-agents). Every other zone: `ttl_seconds = None`.
- **FR6 — Instance exceptions** (D11, E.1). Readers: hook `_operator_exception` and the doctor
  scan, both via `INSTANCE_EXCEPTIONS` (the third reader dies with `workspace_clean`). Migration
  lives in `fix()`: `root_exceptions.txt` present and `instance_exceptions.txt` absent ->
  `parse_exception_globs(old)` written new, old unlinked; 12 lines, deleted in the release after
  every consumer has run it.
- **FR7 — Root whitelist** (finding 4, E.6; the picked bug). `.env` and `.gitignore` join
  `ROOT_ALLOWED_FILES`; the `.gitignore` inline special case is deleted. Commit shape 3
  (`fix(bugs): …`) with the `BUGS.jsonl` resolved line.
- **FR8 — states/ closed canon** (D16, E.2). `STATES_CANON = {spec_contexts.json,
  server_registry.json, install_ledger.json, agent_model_policy.json,
  agent_model_policy.json.last-good.json, privacy_denylist.json, instance_exceptions.txt,
  backlog_subject_aliases.txt, harness_profile.json, presence/, AGENTS.md}`. A missing
  `harness_profile.json` is `WS-states-missing`, fixed by `HarnessProfile.of(present)`, `present`
  = L1 harnesses whose projection dir exists at root; the one writer is
  `infrastructure/json_harness_profile_store.write`, called by init and by fix; init's inline
  `_write_harness_profile` / `_persisted_profile_harnesses` are deleted.
- **FR9 — reports/ retired** (D2, C). Zone, `public/data/reports-AGENTS.md`, its projection row
  and behavior-map entry, panel views/api/css/js, routes, static entries, `core.js` and wrapper
  tab: deleted. `dadaia reports validate|doctor` survive on `core/handoff_index.py` (unchanged).
  HTML reports live in `repos/<slug>/reports/<agent>/<UTC>-<slug>.html`, stated once (FR16).
- **FR10 — academy retired** (D3, C). `features/academy/**` (44 course files), its CLI, model,
  store, container builder, panel views/api/css/js, routes, static, `core.js`, wrapper tab,
  init's academy dir and the export line: deleted.
- **FR11 — logs retired** (D4, C). `hooks/pre_gate.py::_append_latency` + main tail,
  `hooks/sdd_post_gate.py`'s three writers, `infrastructure/jsonl_log_rotation.py`,
  `core/kernel_tunables.LOG_ROTATION_MAX_BYTES`: deleted; no replacement writer.
- **FR12 — scripts projection stopped** (D6, C). `projection_rules._scripts_tree_rules` + call
  deleted; staging into `agentic/scripts` stays; git hooks and CI execute the package copy.
- **FR13 — Export/import** (D12, D15, D). `dadaia export` writes exactly
  `.dadaia/dist/spec-contexts.json` (overwritten via `core.atomic_write`, shape below);
  `dadaia import <file>` validates `schema_version`, `store.save`s each unknown name as `DEAD`
  (`dead_since = now`, `current_branch`, `associated_repos`), reports known names `skipped
  (exists)`, prints `dadaia context alive <name>` as the restore step. No tar, no `patch_state`,
  no `SubprocessProcessRunner` in import; `ImportService` takes the injected `JsonContextStore`.
  Anything else in `dist/` is `WS-dist-slop`.

```json
{"schema_version": "spec-contexts-export-v1", "exported_at": "<UTC>", "dadaia_version": "0.4.6",
 "contexts": [{"slug": "…", "name": "…", "state": "ALIVE|DEAD", "repo_url": "…",
   "branch": "…", "associated_repos": [{"slug": "…", "url": "…"}], "last_sync_at": "<UTC>"}]}
```

- **FR14 — Rendered zone table** (D14, A). `public/data/dadaia-AGENTS.md` carries a
  `<!-- zones -->` placeholder; `infrastructure/public_assets.stage` renders one row per `Zone`
  (name, purpose, class, ttl or `never`, creator); `states-AGENTS.md` renders the closed canon
  from `STATES_CANON` the same way. The 18 hand rows and three stale prose lines are deleted.
- **FR15 — Migration on this instance is `--fix` itself** (D8, E). Dry list -> the operator
  moves any wanted `.dadaia/reports/` file under `repos/<slug>/reports/` by hand -> `dadaia
  doctor --fix` -> reprojection. Retired zones, `states/` residue (`lifecycle/ audit/
  workflow_model_policy.json* .ws_lock report_retention.json last_efficiency_audit.json
  ctx_locks/`), `sessions/runtime/`, 8 wheels, kaykit packs and 5,599 expired tmp files are
  deleted, never quarantined.
- **FR16 — Law and skill text** (D2, D9, D13, F risk d; owner `ai-engineer`, `public/` source,
  reprojected). `DADAIA.md`: §3.2 ADDITIVE row -> `.dadaia/{handoff,tmp,mcps,.cache}/`; §5.2 HTML
  row -> `repos/<slug>/reports/<agent>/<UTC>-<slug>.html`; §5.4 states reports live in the repo
  and are never TTL-reaped, handoffs expire after one day; §8 gains three bullets (zones and the
  table derive from the registry; `dadaia doctor` is the one scan and reaper with the finding
  vocabulary; SessionStart runs `--fix --expired-only`); §10.1 State row gains `dadaia doctor`,
  Scoped-law row drops `.dadaia/reports/AGENTS.md`; §10.2 gains `zone`, `finding verdict`,
  `instance exceptions`. `dadaia-AGENTS.md`: §1 -> placeholder + registry law (no quarantine
  line, no ROOT-4); §2/§4/§5 lose `reports/ academy/ logs/ runs/ dev-report/`, `dadaia clean`.
  Every other `public/` mention of `.dadaia/reports` (four fragments, the scaffold twin, the
  repo template, nine personas, `dd-handoff-emitter` step 3, three more skills) -> the repo
  reports path; `handoff-AGENTS.md` states the 1-day TTL. `RC-FLOW.md` step 8 -> `dadaia
  doctor` dry, `dadaia doctor --fix --expired-only`, remaining slop listed for the operator, done
  when the score line reads 100%. `dd-workspace-doctor` rewritten around the one scan (course/
  academy steps and the report step deleted). `behavior-map.json` hashes re-recorded.
- **FR17 — Memory** (CLOSURE, `product-engineer`). `workspace-doctor` atom: finding codes and
  finding verdicts replace `ROOT-1..4`, `RETIRED-LOCK-STATE`, `EFF-1`; `ARCHITECTURE.md` Part 2
  decider table gains "what `.dadaia/` may contain -> `core/workspace_layout.DADAIA_ZONES`" and
  drops the retired packages from the feature diagram; P-11 wording "six" -> "eight" (matches
  `test_core_file_io_purity._AUTHORIZED_STEMS`; principle unchanged, `ADR: none` kept);
  `workspace-init`, `context-management`, `catalog.json` lose academy, clean, tmp gc, tarballs.

## 5. Out of scope

- No new hook module, gate stage, path class or zone; no repo-tree scan (`repos/<slug>/` hygiene
  stays `DADAIA.md` §5.3 discipline).
- `core/handoff_index.py`, `reports validate|doctor`, presence and session reapers: unchanged.
- `.dadaia/references/` and `.venv/`: never walked. Structural slop at SessionStart (D13).
- Consumer workspaces migrate on their next `dadaia doctor --fix`; no `specs upgrade` step.
- `hooks/ctx_inject.py` and the memory bootstrap.

## 6. Acceptance

- AC1 (FR1, FR2) — `pytest tests/contract/test_zone_registry.py tests/contract/
  test_workspace_layout_single_authority.py` green; `grep -rn 'DADAIA_ALLOWED_SUBDIRS\|
  DADAIA_ADDITIVE_PREFIXES\|_DADAIA_DURABLE_DIRS\|SlopPolicy' dadaia_workspace | wc -l` = 0;
  `core/models/hygiene.py` absent; `CONTEXT.md` carries the four §3 terms.
- AC2 (FR3) — on this instance before `--fix`: `dadaia doctor` exits 1, every finding line
  matches `^WS-[a-z.-]+-(slop|expired|missing) `, the last line matches `^compliance: [0-9]+/
  [0-9]+ entries canonical \([0-9]+%\)$`; `dadaia doctor --json | python -m json.tool` succeeds
  with keys at least `findings compliance fixed`; `dadaia public doctor` prints no `[foreign]`
  line for a runtime directory (consumer-repo `repos/<slug>/AGENTS.md|CLAUDE.md` provenance
  lines are pre-existing, grill ruling 16 of the skills-consolidation candidate, out of scope).
- AC3 (FR4, FR15) — `dadaia doctor --fix` then `dadaia doctor`: exit 0, `compliance: N/N entries
  canonical (100%)`; `ls -A .dadaia` is a subset of `{agentic hooks states sessions handoff tmp
  mcps .cache dist references .venv AGENTS.md .gitignore}`; `ls -A .dadaia/states` a subset of
  `STATES_CANON`; `find .dadaia/tmp .dadaia/handoff .dadaia/mcps -type f -mtime +1 | wc -l` = 0;
  `.dadaia/sessions/runtime` absent.
- AC4 (FR4) — `dadaia --help` lists no `clean tmp academy`; `dadaia reports --help` lists exactly
  `validate doctor`; `dadaia doctor --help` shows `--fix --expired-only --json --quiet`; `dadaia
  doctor --fix --expired-only --quiet` on a compliant instance prints nothing.
- AC5 (FR4) — each harness runtime config projected by `public install` carries one SessionStart
  entry ending in `doctor --fix --expired-only --quiet`; `pytest tests/contract/
  test_hook_import_surface.py` green (P-12).
- AC6 (FR5) — a file under `handoff/` or `tmp/` with mtime 2 days old is reported
  `WS-<zone>-expired` and deleted by `--fix --expired-only`; a zone `AGENTS.md` never is.
- AC7 (FR6) — after `--fix`: `states/root_exceptions.txt` absent; `instance_exceptions.txt` has
  `grep -c '^\.mcp\.json$'` = 1 and no duplicate line; a file matching one of its globs is
  reported nowhere, at root or inside `.claude/`.
- AC8 (FR7) — root `.env` and `.gitignore` produce no finding; `dadaia bugs status` shows
  doctor-root1-flags-env-that-dadaia-md-9-declares-canonical resolved, RED test named.
- AC9 (FR8) — `.dadaia/states/harness_profile.json` exists after `--fix` and lists only harnesses
  whose projection dir exists at root; `grep -c '_write_harness_profile' dadaia_workspace/
  features/workspace/service.py` = 0.
- AC10 (FR9-FR12) — `ls dadaia_workspace/features` has no `academy tmp_gc workspace_clean`;
  `reports/{retention,next}.py`, `jsonl_log_rotation.py`, `legacy_dadaia_dirs.py` absent; panel
  goldens green with no `/reports` or `/academy` route; a gated write creates no `.dadaia/logs`;
  `public install --target all` creates no `.dadaia/scripts` and the manifest names none.
- AC11 (FR13) — `dadaia export` writes only `.dadaia/dist/spec-contexts.json` in the FR13 shape;
  on a scratch workspace under `.dadaia/tmp/qa-engineer/<date>/`, `dadaia import <file>`
  registers every unknown name `DEAD` and skips known names; `dadaia doctor` there reports
  `WS-dist-slop` for any other `dist/` entry.
- AC12 (FR14) — after `public stage && public install --target all`, `.dadaia/AGENTS.md` has a
  table of exactly 11 zone rows and `.dadaia/states/AGENTS.md` a canon table of 11 entries;
  hand-editing one row makes `test_zone_registry` red.
- AC13 (FR16) — `grep -rn '\.dadaia/reports\|academy\|dadaia clean\|tmp gc\|reports cleanup\|
  ROOT-4\|legacy-quarantine' dadaia_workspace/public | wc -l` = 0; `grep -c 'repos/<slug>/
  reports/' dadaia_workspace/public/data/DADAIA.md` = 1; `pytest -k behavior_map` green;
  `dadaia public doctor` `[ok] public-privacy`.
- AC14 (FR17) — `dadaia specs doctor` 0 errors after the closure pass; `grep -c 'set of eight'
  specs/memory/ARCHITECTURE.md` = 1; `grep -rn 'ROOT-4\|RETIRED-LOCK-STATE\|EFF-1' specs/memory |
  wc -l` = 0.
- AC15 (all) — local CI preflight green; `test_import_linter_ignore_cap` cap = 3; `lint-imports`
  zero new ignored edges; V32/V33 re-pinned downward; V34 holds for this trio; `git diff
  --shortstat develop..HEAD -- dadaia_workspace` net at most -7,400 lines (08736ddb: 260 files,
  +6,004/-13,466, net -7,462; shortstat counts rewritten lines, -8,000 was the DRAFT's net-new
  estimate; nothing landed was reverted).

## 7. Operator decisions (grill record, ADR lines)

1. **D1** Continue at the gate: candidate 3 -> `rc-3/`, candidate 4 trio at root, version 0.4.6.
2. **D2** `.dadaia/reports/` retired; only `reports validate|doctor` survive; panel routes, tab
   and the cleanup/status/importance verbs deleted; HTML reports in `repos/<slug>/reports/`,
   stated once in `DADAIA.md` §5.2.
3. **D3** academy retired (CLI group, panel tab, zone, courses).
4. **D4** `.dadaia/logs` retired with both hook writers and `jsonl_log_rotation`.
5. **D5** `.dadaia/mcps` kept, ephemeral, TTL 1 day.
6. **D6** `.dadaia/scripts` projection stopped, zone removed.
7. **D7** `.dadaia/handoff` TTL 1 day by mtime; no importance ledger; no report pairing.
8. **D8** `doctor --fix` on this instance deletes everything slop or expired, kaykit included.
9. **D9** `dadaia doctor` is THE scan and THE reaper; `dadaia clean` and `dadaia tmp gc` deleted.
10. **D10** One finding per line, `WS-<zone>-<class>` code, final `compliance:` line, `--json`
    mirror, exit 1 on any slop or expired.
11. **D11** `states/instance_exceptions.txt` (globs) replaces `root_exceptions.txt`, covers root
    and harness dirs; outside manifest and outside exceptions = slop.
12. **D12** `dadaia export` writes one fixed `.dadaia/dist/spec-contexts.json`, overwritten.
13. **D13** SessionStart runs `doctor --fix --expired-only`; structural slop only by explicit
    operator `--fix`.
14. **D14** The `.dadaia/AGENTS.md` table is rendered from the registry at `public stage`,
    pinned by a contract test.
15. **D15** `dadaia import` reads `spec-contexts.json`, registers contexts DEAD; `context alive`
    clones.
16. **D16** `states/` closed canon (FR8); anything else slop; a missing `harness_profile.json` is
    a fixable finding.

## 8. Dependencies and risks

- FR1+FR2 land first and alone; every later FR only deletes or derives. Between FR1 and FR9-FR12
  the instance doctor lists the retired zones as `WS-dadaia-slop`; the dry default is the safety
  step, nothing is deleted without `--fix`.
- `--fix` on this instance deletes 105 HTML reports and 402 MB of expired tmp: the dry list runs
  first and the operator moves what is wanted (D8).
- SessionStart adds one CLI process per session start (~100 ms over 5k files, tens after the
  first fix); `--quiet` keeps the model context clean.
- Suppressed-edge cap 4 -> 3 (`reconcile -> migrate.legacy_dadaia_dirs` gone); `modules =` loses
  three packages; `_RATCHET` in `test_cli_help_quality` and V32 re-measure downward.
- Reprojection is the proof of every `public/` edit; a hand-edited projection is itself the bug.
