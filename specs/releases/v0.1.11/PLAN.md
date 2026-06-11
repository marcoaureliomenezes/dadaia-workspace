# PLAN: v0.1.11 — Lifecycle Hygiene + Kernel Tail

**Status:** Aprovado
**Release ID:** v0.1.11
**Owner:** product-engineer
**Created:** 2026-06-10

---

## Strategy

Six waves, five of them parallelizable across disjoint write sets. W1 (kernel tail) is
the spine — it reuses the v0.1.10 probe seam (`core/lock_liveness.is_stale` `pid_probe`
param + `session_identity`) and must not regress the no-steal invariants, so its tasks
run TDD-first against the existing two-actor/liveness suites. W2 and W4 are independent
feature seams. W3 (closure contract) touches the skill source + specs doctor and feeds
this release's own CLOSURE (the disposition sweep ships before it is first executed
here — the release closes itself with the new mechanism). W5 is hygiene. W6 reprojects
public assets and runs the final gate.

Cadence (ADR-2): single alpha-1 → qa-only commit → rc-1 ship-trio (qa + code +
security) → operator merge. Flat release dir; all work on `feature/v0.1.11`.

No state migration: pre-pid lease records are handled read-side (unprobeable ⇒
TTL-only reclaim); bind records without `last_seen_at` keep TTL-from-creation
behavior until the first heartbeat refresh writes the field (ADR-8).

## Layers affected

| Wave | Files | Layer |
|------|-------|-------|
| W1 | `features/spec_context/{lease.py,doctor.py,session_identity.py}`, `cli/commands/lock.py`, `features/specs/doctor.py` (029), `hooks/sdd_post_gate.py` (heartbeat→`last_seen_at`), `cli/commands/context.py:76`, `panel/views/kanban.py:85` (`core/specs_resolver.py` untouched — ADR-12 exception) | features + cli + hooks |
| W2 | `features/ci_preflight/service.py`, `features/reports_validation/service.py`, `cli/commands/context.py`, `features/spec_context/service.py` | features + cli |
| W3 | `public/skills/dadaia-release-closure/`, `features/specs/doctor.py` (031/032), `tests/contract/` incl. `tests/contract/README.md` (map authoring) | public + features + tests |
| W4 | `public/rules/plugin-scope.md`, `public/agents/{3 stubs}.md`, `features/panel/{auth,handler}.py`, `cli` panel launch, `hooks/ctx_inject.py` | public + features + hooks |
| W5 | `public/scripts/` hygiene, `pyproject.toml`, `hooks/sdd_gate.py`, `tests/unit/hooks/test_sdd_post_gate.py`, `features/specs/doctor.py` (027 allowlist), memory frontmatter/catalog | public + hooks + features + specs |
| W6 | projections (`dadaia public stage/install/doctor`), verification only | public + none |

## Execution order and parallelism

```
PRE   T-011-00 (PE: release start — ACTIVE.md → v0.1.11 IMPLEMENTATION at approval)

W1 — kernel tail (spine; sequenced inside the wave where files are shared)
  T-011-01 (probe side doors: lock steal + lease._main)
  T-011-02 (lease GC/reclaim, doctor --fix)          [after 01: shares lease.py]
  T-011-03 (SPEC-DOC-029 triage)                     [after 02: consumes GC semantics]
  T-011-04 (bind-record heartbeat/last_seen_at GC)   [after 02: shares spec_context/doctor.py]
  T-011-05 (session-path ownership, 3 sites, ADR-12) [after 04: shares spec_context/doctor.py]

W2 — CLI/validation (parallel with W1 except declared file overlaps)
  T-011-06 (ci-preflight runner argv)
  T-011-07 (handoff workspace-rooted resolution)
  T-011-08 (context repo_url lifecycle)              [after 05: shares cli/commands/context.py]

W3 — closure contract
  T-011-09 (closure skill disposition sweep — ai-engineer)
  T-011-10 (SPEC-DOC-031/032)                        [after 03: shares specs/doctor.py]
  T-011-11 (lifecycle-asymmetry contract test)

W4 — plugin + panel + inject (independent)
  T-011-12 (plugin honest-relabel — ai-engineer)
  T-011-13 (panel launch token)
  T-011-14 (ctx-inject digest + sentinel GC)

W5 — hygiene/docs/tooling
  T-011-15 (public-source hygiene)   T-011-16 (R8 code nits)   T-011-17 (R9 bumps)
  T-011-18 (R10 WARN cleanups)                       [after 10: shares specs/doctor.py]

W6 — projection + gate
  T-011-19 (reprojection — after 09, 12, 15)
  T-011-20 (final gate — after all code tasks)
  T-011-21 (PE: memory truth + R8 doc nits — CLOSURE phase, LAST)
```

Hard spine: 00 → 01 → 02 → {03, 04} → 05 → 08; 03 → 10 → 18; {09,12,15} → 19 → 20;
21 last. Everything else is cross-wave parallel (disjoint write sets declared in TASKS).

## Technical approach (condensed)

### W1 — kernel tail
- **T-011-01:** `lock.py:steal` and `lease._main` acquire pass the container-wired
  `OsProcessProbe` into the existing `pid_probe` param (`lease.py:70` contract:
  alive ⇒ held). `pid_probe` becomes a REQUIRED parameter on acquire/steal call sites
  (`mypy --strict` enforces); existing pid-less test fixtures stay green via the
  no-pid ⇒ TTL rule. Pre-pid records: probe receives no pid ⇒ TTL-only (existing
  semantics). Add a residue grep: no call site of `lease.acquire`/`lease.steal`
  without a probe arg outside tests.
- **T-011-02:** new `lease.reclaim_dead(workspace, ctx)` helper (TTL-expired AND
  (pid absent OR probe-dead) ⇒ delete record, return reclaimed); workspace doctor
  emits `LOCK-GC` and applies it under `--fix`. Never touches a live-pid record.
- **T-011-03:** `_check_lease_session_coherence` (`specs/doctor.py:1199-1245`) gains
  the triage: read record via `lease.read_record`; stale+dead ⇒ WARN with remediation
  text naming `dadaia doctor --fix` / `dadaia lock steal <ctx>`; live+incoherent ⇒
  ERR (forgery wording only here). The doctor's pid-probe seam is
  **composition-root-wired** (like `workspace_state_dir`) — never an adapter import
  inside features. Fixtures per state + the composed integration test (TTL-expired
  ~36 h pid-less record + fresh READ bind, built via production writers).
- **T-011-04 (ADR-8 amended):** extend the PostToolUse heartbeat
  (`hooks/sdd_post_gate.py`) — it already resolves the harness session id — to also
  refresh the session/bind record's `last_seen_at`; GC stays TTL-based against
  `last_seen_at`. No pid use for bind GC (the recorded pid is the dead-by-construction
  bind-CLI pid). Records without `last_seen_at` ⇒ TTL-from-creation as today
  (documented). TTL-semantics re-classification noted in the two renamed/extended
  test modules.
- **T-011-05:** mechanical refactor of the 3 legal sites to `session_identity`
  accessors (`core/specs_resolver.py` stays — ADR-12 documented allowlist exception);
  extend `tests/contract/test_session_store_ownership.py` grep set.

### W2 — CLI/validation
- **T-011-06:** add `_resolve_tool(name)` — pinned order, NO `shutil.which`:
  `Path(sys.executable).parent / name` (venv sibling) → `DADAIA_BIN`-derived bin dir →
  `("poetry","run",name)` fallback. All five Check argvs built through it. Unit tests
  fake both trees; e2e runs preflight against a FAKE tree / stubbed checks with PATH
  sanitized of poetry (no pytest-inside-pytest); real-tree proof = final-gate item 7.
- **T-011-07:** `_resolve_artifact_path`: after the `.dadaia/` branch, add — relative
  path AND `(workspace_root / p).exists()` ⇒ workspace-rooted (still
  `_within_workspace`-checked); else legacy handoff-dir fallback. Both-exist fixture
  asserts workspace-root precedence explicitly. Schema untouched.
- **T-011-08:** CLI `create --url` (overrides catalog lookup); `alive`/`dead`
  back-fill via `git remote get-url origin` (Lock-2 git-ops port) when record URL
  empty; new `update` verb (`--url` only, for now) over the store `update()`;
  workspace doctor `CTX-URL-1` for ALIVE+empty URL.

### W3 — closure contract
- **T-011-09:** skill SOURCE edit: new mandatory step "Disposition sweep" between
  template and memory protocol + `## Dispositions` CLOSURE template section; terminal
  tokens per the ADR-11 vocabulary (single source), with evidence pointer.
- **T-011-10:** SPEC-DOC-031: scan `specs/backlog/**` frontmatter/`**Status:**` for
  ADR-11 non-terminal tokens (case-insensitive prefix match); cross-reference slug/ID
  occurrences in `specs/_archive/releases/**/{CLOSURE,SPEC}.md`, excluding "Backlog
  returns" sections ⇒ WARN. SPEC-DOC-032: `specs/bugs/**` `status:` outside the
  ADR-11 bug canon {Open, Closed} ⇒ WARN (legacy tokens already normalized by the
  2026-06-10 PM sweep; this guards regressions). Fixtures per invariant;
  self-hosting tree must end clean.
- **T-011-11:** contract test parses the lifecycle-asymmetry map table in
  `tests/contract/README.md` and diffs against `dadaia_workspace/features/`
  subpackages enumerated via pkgutil/dir listing at test time; missing row and
  missing GAP cell both fail. Authoring the ~15 missing rows/GAP cells (current map
  covers ~6 of 21 subpackages) is part of the task — the current tree passes only
  after that authoring.

### W4 — plugin + panel + inject
- **T-011-12:** rewrite `plugin-scope.md` install column + `[PLUGIN REQUIRED]` block
  and the 3 stub bodies: state packs are not yet distributed; route to operator;
  point to the backlog slug. Grep-zero acceptance on `plugin install`, pinned
  permanently by `tests/contract/test_plugin_install_residue.py`.
- **T-011-13:** `panel/auth.py`: mint single-use launch token (TTL ≤60 s, stored
  server-side hashed); launch URL carries only it; first valid use sets the session
  cookie (`SameSite=Strict; HttpOnly` — gates the UI shell only) and invalidates the
  token; replay/expired ⇒ 401. Sensitive APIs stay Bearer-only (ADR-10). Bearer-grep
  corpus: panel views + launch/registry code + tests; loopback-tokenless-GET vs
  launch-token precedence stated in code/docstring; the e2e (URL content + replay
  401) is the binding contract.
- **T-011-14:** `ctx_inject` builds the injected catalog digest from `catalog.json`
  dropping `summary` (keep rank/slug/title/tldr/path); measure before/after bytes in
  the test; sentinel sweep: stale sentinels (dead sid or >N days) removed at inject
  or via doctor `--fix` (implementer picks one home, tests pin it).

### W5 — hygiene/docs/tooling
- **T-011-15:** invoke packaged scripts with `-B`/`PYTHONDONTWRITEBYTECODE`; delete
  tracked `.pyc`; wheel exclusion (`pyproject` include/exclude); hygiene contract
  test. repos.xlsx: inspect content; generic ⇒ document consumer
  (`context create` catalog lookup) in repos-catalog atom note at closure; private ⇒
  replace with generic sample.
- **T-011-16:** two named nits (docstring; probe dedup). Pure refactor, no behavior.
- **T-011-17:** `poetry update pip poetry dulwich` within constraints; `pip-audit`;
  if no fixed release exists ⇒ defer note in CLOSURE.
- **T-011-18 (non-memory half only, qa Q-M2):** SPEC-DOC-027 allowlist of the
  existing pre-canon archive dir names with rationale comment; forward WARN kept.
  The memory catalog/frontmatter `token_estimate` regeneration (script:
  `public/scripts/generate-memory-catalog.py`) is MEMORY class and MANDATED to
  T-011-21 (PE, CLOSURE phase).

### W6 — projection + gate
- **T-011-19:** `dadaia public stage && dadaia public install --target all && dadaia
  public doctor` (exit 0) after all public/** edits.
- **T-011-20:** full battery (see Validation plan) + 6/6 regression table.
- **T-011-21:** PE memory updates (CLOSURE phase) per SPEC "Memory files affected" +
  the mandated memory frontmatter/catalog `token_estimate` regeneration (re-verify
  zero target WARNs at CLOSURE); then CLOSURE.md including the FIRST execution of the
  new disposition sweep (B1 eats its own dogfood: this release's 6 bugs + picked
  residual backlog entry get terminal dispositions per ADR-11).

## Validation plan

1. `pytest -p no:cacheprovider` full suite — 0 failures (new: probe side-door units,
   GC fixtures, 029 triage states, bind-GC, ownership grep, preflight argv, resolver,
   repo_url lifecycle, 031/032 fixtures, asymmetry contract, launch token, digest,
   hygiene).
2. `ruff format --check && ruff check --no-cache` clean; `mypy --strict` clean.
3. `import-linter` 0 violations; ignore cap not increased.
4. `dadaia public doctor` exit 0 (post-reprojection; plugin-install grep zero).
5. `dadaia specs doctor` exit 0 — new invariants active; zero SPEC-DOC-027 WARNs and
   no NEW WARNs at the gate; zero `token_estimate` WARNs re-verified at CLOSURE
   (T-011-21, after PE regenerates memory frontmatter).
6. `dadaia ci preflight` exit 0 **with poetry removed from PATH** (B2 repro).
7. Manual smokes: B3 repro sequence → WARN + remediation, no ERR; B4 handoff
   validate exit 0; B6 create/update/back-fill; panel launch without Bearer in URL.
8. Reviewer cross-check at rc-1: memory deltas vs merged code; dispositions table.

## Technical risks

| Risk | L | Mitigation |
|------|---|-----------|
| Probe threading regresses v0.1.10 no-steal/two-actor suites | M | TDD against existing suites; two-actor e2e re-run in final gate |
| SPEC-DOC-031 false positives on slug mentions | M | WARN severity (ADR-6) + Backlog-returns section exclusion + fixtures |
| Launch-token rework breaks panel auth contracts | M | v0.1.10 AC-R7-03 tests kept green; e2e replay test |
| Preflight argv rework breaks pre-push hook on CI images | M | both resolution branches unit-tested with fake trees; fail-closed message kept |
| ctx-inject digest starves an agent of needed summary depth | L | summary remains in catalog.json on disk (self-pull unchanged); only the injection slims |
| Stacked branch rebase churn (PR #53 unmerged) | M | linear stack; operator owns merge order |
| Shared doctor files across waves cause merge conflicts | M | explicit sequencing 03→10→18 and 02→04→05 declared in TASKS |
| Memory writes attempted outside CLOSURE | L | R8 doc nits + token_estimate frontmatter regeneration scheduled exclusively in T-011-21 (CLOSURE phase, qa Q-M2) |
