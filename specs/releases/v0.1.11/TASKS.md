# TASKS: v0.1.11 — Lifecycle Hygiene + Kernel Tail

**Status:** Aprovado
**Release ID:** v0.1.11
**Owner:** product-engineer
**Created:** 2026-06-10

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

Waves W1–W6 are safe to run in parallel **across** waves except the declared shared
files: `features/specs/doctor.py` (T-011-03 → T-011-10 → T-011-18),
`features/spec_context/doctor.py` (T-011-02 → T-011-04 → T-011-05),
`features/spec_context/lease.py` (T-011-01 → T-011-02), and
`cli/commands/context.py` (T-011-05 → T-011-08). Hard spine:
T-011-00 → 01 → 02 → {03, 04} → 05 → 08; 03 → 10 → 18; {09, 12, 15} → 19 → 20;
T-011-21 runs LAST (CLOSURE phase). Maximum one `[-]` per owner unless tasks are in
different waves with disjoint write sets as declared here. TDD-first: each task lands
its failing test before the fix.

---

## Pre-work

### [x] T-011-00 — Release start: ACTIVE.md → v0.1.11 IMPLEMENTATION
- **Owner:** product-engineer · **Maps:** v0.1.10 release-start precedent (arch A5)
- **Write set:** `specs/releases/ACTIVE.md`
- **Preconditions:** SPEC+PLAN+TASKS `**Status:** Aprovado` (coordinator flips after
  spec-review).
- **Acceptance:** `ACTIVE.md` reads `release: v0.1.11` / `phase: IMPLEMENTATION`
  before any W1 work begins (gate legality + SPEC-DOC-024 phase↔markers hold all
  release long). Authored at DEFINITION as `phase: DEFINITION`; this task is the flip.
- **Parallelism:** first, before all waves.

---

## W1 — Concurrency-kernel tail (bug B3 + residuals R1/R3/R4)

### [x] T-011-01 — Probe the CLI side doors: `lock steal` + `lease._main` acquire
- **Owner:** software-engineer · **Maps:** residual R1; bug
  `doctor-stale-lease-misdiagnosed-as-forgery` (remediation-path half); ADR-5
- **Write set:** `dadaia_workspace/cli/commands/lock.py`,
  `dadaia_workspace/features/spec_context/lease.py` (`_main`, `steal`),
  `tests/unit/cli/test_lock_steal.py` (new/extend),
  `tests/unit/features/spec_context/test_lease_*.py`, residue grep contract test
- **Preconditions:** T-011-00.
- **Acceptance (AC-W1-01):** `lock steal` with TTL-expired record + alive recorded
  pid ⇒ refuses (exit 1, message says holder alive); TTL-expired + dead pid ⇒ steals;
  record without `pid` ⇒ TTL rule (today's behavior); `lease._main` acquire threads
  the same probe; `pid_probe` is a REQUIRED parameter on acquire/steal call sites —
  `mypy --strict` enforces it; existing pid-less test fixtures stay green via the
  no-pid ⇒ TTL rule (no fixture rewrites needed); residue grep: no probe-less
  production call site of `lease.acquire`/`lease.steal`; suite + `mypy --strict`
  green.
- **Parallelism:** spine; before T-011-02.

### [x] T-011-02 — Stale-lease GC/reclaim (`LOCK-GC`, doctor `--fix`)
- **Owner:** software-engineer · **Maps:** bug B3 half (1) — no GC path; pre-pid
  records permanently un-reclaimable
- **Write set:** `dadaia_workspace/features/spec_context/lease.py` (reclaim helper),
  `dadaia_workspace/features/spec_context/doctor.py`,
  `tests/unit/features/spec_context/test_doctor_lock_gc.py` (new)
- **Preconditions:** T-011-01 (shares `lease.py`).
- **Acceptance (AC-W1-02 part):** doctor reports `LOCK-GC` for TTL-expired records
  whose holder is dead OR whose record predates the `pid` field; `--fix` reclaims
  (deletes record); a live-pid record is NEVER reclaimed regardless of TTL; fixtures
  for all three states; suite green.
- **Parallelism:** after 01; before 03 and 04.

### [x] T-011-03 — SPEC-DOC-029 triage: stale-dead ≠ forgery
- **Owner:** software-engineer · **Maps:** bug B3 half (2) —
  `features/specs/doctor.py:1199-1245` conflates staleness with forgery
- **Write set:** `dadaia_workspace/features/specs/doctor.py`,
  `tests/unit/features/specs/test_doctor_ledger_invariants.py`
- **Preconditions:** T-011-02 (consumes GC semantics; sequenced on specs/doctor.py).
- **Acceptance (AC-W1-03 + AC-W1-02 rest):** three-state fixtures — (a) TTL-expired +
  dead/unprobeable holder ⇒ WARN "stale lease from dead session — safe to reclaim"
  naming `dadaia doctor --fix` / `dadaia lock steal <ctx>`, exit unchanged (0 if no
  other ERR); (b) live holder + genuine lease↔session incoherence ⇒ ERR (forgery
  wording only here); (c) coherent ⇒ silent. PLUS the named composed integration
  test `test_stale_pidless_lease_with_fresh_read_bind_warns_not_err`: fixture built
  via PRODUCTION writers — TTL-expired (~36 h) pid-LESS lock record + fresh READ
  bind → `specs doctor` ⇒ WARN (not ERR), remediation text names the reclaim
  command, exit 0, output contains no forgery wording. The doctor pid-probe seam is
  composition-root-wired (like `workspace_state_dir`), never an adapter import
  inside features. Bug B3 repro steps 1–4 re-run end-to-end and produce (a), not
  ERR. Bug closed with the named regression test.
- **Parallelism:** after 02; before T-011-10.

### [x] T-011-04 — Bind-record GC: heartbeat-renewed `last_seen_at` (no READ→IMPLEMENTATION decay)
- **Owner:** software-engineer · **Maps:** residual R3; ADR-8 (amended — architect A1)
- **Write set:** `dadaia_workspace/hooks/sdd_post_gate.py` (heartbeat also refreshes
  the session/bind record's `last_seen_at`),
  `dadaia_workspace/features/spec_context/doctor.py` (TTL GC vs `last_seen_at`),
  `dadaia_workspace/features/spec_context/session_identity.py` (`last_seen_at`
  read/write), `tests/unit/features/spec_context/test_session_identity.py`,
  `tests/unit/features/spec_context/test_doctor_gc.py`,
  `tests/unit/features/spec_context/test_stable_session_identity.py` (both with a
  re-classification note: TTL semantics change to `last_seen_at`)
- **Preconditions:** T-011-02 (shares `spec_context/doctor.py`).
- **Acceptance (AC-W1-04):** exercises the REAL renewal path — no planted-pid
  fixtures: simulate a PostToolUse hook invocation that refreshes the bind record's
  `last_seen_at`, then run the GC sweep ⇒ record survives and the gate still
  resolves READ for that sid; a stale record with old `last_seen_at` (past TTL, no
  renewal) ⇒ collected; record without `last_seen_at` ⇒ TTL-from-creation behavior,
  documented in module docstring; the session-record pid is NOT consulted (it is the
  transient bind-CLI pid, dead by construction); suite green.
- **Parallelism:** after 02; before 05.

### [x] T-011-05 — Session-path ownership: migrate the 3 legal sites (ADR-12)
- **Owner:** software-engineer · **Maps:** residual R4 (arch NF-3 residue); ADR-12
- **Write set:** `dadaia_workspace/cli/commands/context.py` (`:76`),
  `dadaia_workspace/features/spec_context/doctor.py` (`:124`),
  `dadaia_workspace/features/panel/views/kanban.py` (`:85`),
  `tests/contract/test_session_store_ownership.py`
- **Preconditions:** T-011-04 (shares `spec_context/doctor.py`).
- **Acceptance (AC-W1-05):** the three sites consume `session_identity` accessors;
  `core/specs_resolver.py` stays untouched as the DOCUMENTED closed-allowlist
  exception in `test_session_store_ownership.py` (core cannot import the
  features-layer owner — ADR-12); the ownership grep contract extended to catch the
  previous patterns; grep for direct `sessions/` path construction returns only
  `session_identity.py` plus the documented allowlist entry; suite green.
- **Parallelism:** after 04; before T-011-08 (shares `cli/commands/context.py`).

---

## W2 — CLI/validation seams (bugs B2, B4, B6)

### [x] T-011-06 — ci-preflight: runner-derived tool argv (poetry fallback only)
- **Owner:** software-engineer · **Maps:** bug `ci-preflight-checks-hardcode-poetry-run`
- **Write set:** `dadaia_workspace/features/ci_preflight/service.py` (`:80-93`),
  `tests/unit/features/ci_preflight/`, e2e preflight test
- **Preconditions:** T-011-00.
- **Acceptance (AC-W2-01):** `_resolve_tool` pinned order, NO `shutil.which`:
  venv sibling of `sys.executable` → `DADAIA_BIN` bin dir → poetry fallback; all five
  checks built through it; unit tests fake both trees; e2e runs against a FAKE tree /
  stubbed checks with poetry stripped from PATH (no pytest-inside-pytest — the
  real-tree run is final-gate item 7); fail-closed message preserved when a tool is
  missing everywhere. Bug closed with named regression test.
- **Parallelism:** independent.

### [x] T-011-07 — Handoff resolver: workspace-rooted relative artifact paths
- **Owner:** software-engineer · **Maps:** bug
  `handoff-artifact-path-cannot-reference-specs-audits`
- **Write set:** `dadaia_workspace/features/reports_validation/service.py`
  (`_resolve_artifact_path`, `:166-173`), `tests/unit/features/reports_validation/`
- **Preconditions:** T-011-00.
- **Acceptance (AC-W2-02):** any relative `artifact.path` existing under
  `workspace_root` resolves workspace-rooted (incl.
  `repos/<slug>/specs/audits/<UTC>/audit.md` — bug repro validates exit 0); legacy
  handoff-dir-relative artifacts still validate; a both-exist fixture (path
  resolvable both workspace-rooted and handoff-relative) asserts explicitly that
  workspace-root wins; absolute and `..` paths still rejected by schema (no schema
  change); `_within_workspace` guard kept; suite green. Bug closed with named
  regression test.
- **Parallelism:** independent.

### [x] T-011-08 — Context repo_url lifecycle: `--url`, back-fill, `update`, doctor flag
- **Owner:** software-engineer · **Maps:** bug
  `context-repo-url-not-settable-or-repairable`; ADR-7
- **Write set:** `dadaia_workspace/cli/commands/context.py`,
  `dadaia_workspace/features/spec_context/service.py`,
  `dadaia_workspace/features/spec_context/doctor.py` (CTX-URL-1),
  CLI integration tests
- **Preconditions:** T-011-05 (shares `cli/commands/context.py` and
  `spec_context/doctor.py`).
- **Acceptance (AC-W2-03):** (a) `context create <n> --repo <slug> --url <url>`
  persists the URL (overrides catalog lookup); (b) `alive`/`dead` back-fill from
  `git remote get-url origin` when record URL empty and repo on disk (via the
  per-context git-ops port, no raw subprocess in features — back-fill test uses a
  local `file://` fixture remote as origin); (c) `context update <name> --url <url>`
  repairs through the store `update()`; (d) workspace doctor flags ALIVE + empty
  `repo_url` (`CTX-URL-1`); bug repro (export/import clone scenario) covered by
  test; suite green. Bug closed with named regression test.
- **Parallelism:** after 05.

---

## W3 — Closure contract (bug B1 + residual R2)

### [x] T-011-09 — Closure skill: mandatory disposition sweep (source edit)
- **Owner:** ai-engineer · **Maps:** bug
  `release-closure-leaves-consumed-backlog-unsanitized` half (a)
- **Write set:** `dadaia_workspace/public/skills/dadaia-release-closure/SKILL.md`
  (canonical source only; projection via T-011-19)
- **Preconditions:** T-011-00.
- **Acceptance (AC-W3-01):** the skill carries a mandatory "Disposition sweep" step
  (every picked/superseded backlog item + bug → terminal token per the ADR-11
  vocabulary: bugs ⇒ `Closed` (+ optional `superseded_by:`); backlog ⇒ an ADR-11
  terminal token, e.g. `DELIVERED — vX.Y.Z` / `SUPERSEDED — <slug>`; each with an
  evidence pointer) and the CLOSURE template gains a `## Dispositions` section;
  never-delete law restated; wording consistent with release-governance and ADR-11.
- **Parallelism:** independent; feeds T-011-19 and T-011-21.

### [x] T-011-10 — specs doctor: SPEC-DOC-031 (consumed backlog) + SPEC-DOC-032 (bug status canon)
- **Owner:** software-engineer · **Maps:** bug B1 half (b); ADR-6
- **Write set:** `dadaia_workspace/features/specs/doctor.py`,
  `tests/unit/features/specs/test_doctor_ledger_invariants.py`
- **Preconditions:** T-011-03 (shares `specs/doctor.py`).
- **Acceptance (AC-W3-02):** SPEC-DOC-031 WARN — backlog entry with ADR-11
  non-terminal status ({OPEN, PICKED, CANDIDATE}, case-insensitive prefix match on
  the Status line; terminal set = {DELIVERED, SUPERSEDED, RESOLVED, CONSUMED,
  DEFERRED, REJECTED}) whose slug/ID appears in an archived release CLOSURE/SPEC
  outside "Backlog returns" sections (defer/supersede mentions in archived CLOSUREs
  are the known false-positive class — reason it stays WARN, ADR-6); SPEC-DOC-032
  WARN — bug `status:` outside the ADR-11 canon {Open, Closed} (the 2026-06-10 PM
  sweep already normalized legacy `Fixed`/`resolved` tokens; this guards
  regressions); one fixture per invariant + a negative fixture (slug only in Backlog
  returns ⇒ silent); `dadaia specs doctor` on the self-hosting tree exits 0
  (residual stale entries dispositioned via PM coordination; evidence in CLOSURE).
  Bug B1 closed referencing T-011-09 + this test.
- **Parallelism:** after 03; before 18.

### [x] T-011-11 — Lifecycle-asymmetry map: mechanical contract test + map completion
- **Owner:** software-engineer · **Maps:** residual R2 (qa §blockers; qa Q-BL1)
- **Write set:** `tests/contract/test_lifecycle_asymmetry_map.py` (new),
  `tests/contract/README.md` (the map's actual home — author the ~15 missing
  rows/GAP cells; current map covers ~6 of 21 `features/` subpackages)
- **Preconditions:** T-011-00.
- **Acceptance (AC-W3-03):** test parses the map table in
  `tests/contract/README.md` and diffs against `dadaia_workspace/features/`
  subpackages enumerated via pkgutil/dir listing at test time; EVERY subpackage must
  have a row or an explicit GAP cell; a synthetic unmapped subpackage makes the test
  fail; the current tree passes ONLY after the missing rows/GAP cells are authored
  (that authoring is part of this task); suite green.
- **Parallelism:** independent.

---

## W4 — Plugin honesty + panel + inject (bug B5 + residuals R5/R6)

### [x] T-011-12 — Plugin honest-relabel (rule + 3 stubs)
- **Owner:** ai-engineer · **Maps:** bug `plugin-install-command-missing`; ADR-4
- **Write set:** `dadaia_workspace/public/rules/plugin-scope.md`,
  `dadaia_workspace/public/agents/{frontend-engineer,design-specialist,devops-engineer}.md`
  (canonical sources only), `tests/contract/test_plugin_install_residue.py` (new —
  permanent residue grep contract test)
- **Preconditions:** T-011-00.
- **Acceptance (AC-W4-01):** zero `plugin install` references under
  `dadaia_workspace/public/` (grep, pinned permanently by
  `tests/contract/test_plugin_install_residue.py`); `[PLUGIN REQUIRED]` wording honestly states the
  packs are not yet distributed and routes to the operator with the backlog pointer
  (`plugin-packs-and-install-command`); stub frontmatter (`plugin: true`) unchanged;
  bug closed referencing the grep evidence + backlog return (registered at CLOSURE).
- **Parallelism:** independent; feeds T-011-19.

### [x] T-011-13 — Panel launch token (Bearer never in a URL)
- **Owner:** software-engineer · **Maps:** residual R5 (security R-1); ADR-10
- **Write set:** `dadaia_workspace/features/panel/auth.py`,
  `dadaia_workspace/features/panel/handler.py`, panel launch CLI path, unit + e2e
  tests
- **Preconditions:** T-011-00.
- **Acceptance (AC-W4-02):** launch URL carries only a single-use token with TTL
  ≤60 s; first use sets the session cookie (`SameSite=Strict; HttpOnly` — gates only
  the UI shell; sensitive APIs remain Bearer-only, ADR-10) and invalidates the token;
  replay and expired ⇒ 401; the long-lived Bearer appears in no URL anywhere —
  grep corpus: panel views + launch/registry code + tests; loopback-tokenless-GET vs
  launch-token precedence stated explicitly; the e2e (URL content + replay 401) is
  the binding contract; v0.1.10 tokenless-sensitive-API 401 contract still green.
- **Parallelism:** independent.

### [x] T-011-14 — ctx-inject: tldr-digest catalog + sentinel GC
- **Owner:** software-engineer · **Maps:** residual R6 (ai N-5)
- **Write set:** `dadaia_workspace/hooks/ctx_inject.py`,
  `tests/unit/hooks/test_ctx_inject*.py`,
  (`dadaia_workspace/features/spec_context/doctor.py` ONLY if GC lands there —
  then sequence after T-011-05)
- **Preconditions:** T-011-00 (+ T-011-05 if doctor home chosen).
- **Acceptance (AC-W4-03):** injected catalog digest drops `summary` (keeps
  rank/slug/title/tldr/path); before/after byte size asserted in test and recorded
  for CLOSURE; `catalog.json` on disk unchanged (self-pull depth intact); stale
  sentinel files (dead sid or aged) swept — home (inject-time vs doctor `--fix`)
  pinned by test; suite green.
- **Parallelism:** independent (conditional doctor overlap declared).

---

## W5 — Hygiene / docs / tooling (residuals R7/R8/R9/R10)

### [x] T-011-15 — Public-source hygiene: `__pycache__` prevention + repos.xlsx disposition
- **Owner:** software-engineer · **Maps:** residual R7
- **Write set:** `dadaia_workspace/public/scripts/__pycache__/` (delete),
  script invocation sites (add `-B`/`PYTHONDONTWRITEBYTECODE`), `pyproject.toml`
  (wheel exclusion), `tests/contract/test_public_source_hygiene.py` (new),
  repos.xlsx replacement ONLY if private content found
- **Preconditions:** T-011-00.
- **Acceptance (AC-W5-01):** running the catalog/lint scripts leaves no
  `__pycache__` under `dadaia_workspace/public/` (test executes + asserts); wheel
  build contains no `.pyc`; repos.xlsx inspected — consumer documented
  (context-create catalog lookup, `cli/commands/context.py:113-120`); if
  operator-local data found ⇒ replaced with a generic sample (privacy law); decision
  + evidence recorded for CLOSURE.
- **Parallelism:** independent; feeds T-011-19.

### [x] T-011-16 — R8 code nits: docstring + probe dedup
- **Owner:** software-engineer · **Maps:** residual R8 (code half)
- **Write set:** `tests/unit/hooks/test_sdd_post_gate.py` (`:12` docstring),
  `dadaia_workspace/hooks/sdd_gate.py` (duplicate probe construction)
- **Preconditions:** T-011-00 (T-011-01 does NOT touch `hooks/sdd_gate.py` — the
  probe dedup here is independent of the lease-side probe threading).
- **Acceptance (AC-W5-02):** stale `_ENV_BASELINE` reference gone; single probe
  construction in `sdd_gate` (no behavior change — gate suites green unchanged);
  file:line evidence recorded for CLOSURE.
- **Parallelism:** independent.

### [x] T-011-17 — R9: opportunistic venv tooling bumps (or explicit defer)
- **Owner:** software-engineer · **Maps:** residual R9 (security F-6 tail)
- **Write set:** `pyproject.toml`, `poetry.lock`
- **Preconditions:** T-011-00.
- **Acceptance:** `pip`/`poetry`/`dulwich` bumped where a CVE-fixed release exists;
  `pip-audit` output captured; any non-bumpable CVE gets an explicit defer-with-
  reason note for CLOSURE; suite green after lock regen.
- **Parallelism:** independent.

### [ ] T-011-18 — R10: WARN cleanups, non-memory half only (SPEC-DOC-027 legacy allowlist)
- **Owner:** software-engineer · **Maps:** residual R10 (WARN half only); ADR-3/ADR-9;
  qa Q-M2 split
- **Write set:** `dadaia_workspace/features/specs/doctor.py` (027 allowlist),
  `tests/unit/features/specs/test_doctor_ledger_invariants.py`
- **Preconditions:** T-011-10 (shares `specs/doctor.py`).
- **Acceptance (AC-W5-03, gate half):** `dadaia specs doctor` shows zero SPEC-DOC-027
  WARNs on the self-hosting tree and no NEW WARNs introduced; allowlist enumerated in
  source with rationale; synthetic new bad dir still WARNs (forward enforcement
  intact); escape-record axis untouched (out of scope per ADR-3). The memory
  `token_estimate` frontmatter/catalog regeneration is MEMORY class and is MANDATED
  to T-011-21 (PE-only, CLOSURE phase) — this task does NOT touch
  `specs/memory/**`.
- **Parallelism:** after 10.

---

## W6 — Projection + final gate + closure

### [-] T-011-19 — Reprojection of changed public assets
- **Owner:** software-engineer · **Maps:** lib-guardrail workflow
- **Write set:** projections via CLI only (`dadaia public stage && dadaia public
  install --target all && dadaia public doctor`)
- **Preconditions:** T-011-09, T-011-12, T-011-15 merged.
- **Acceptance:** `dadaia public doctor` exit 0; projected skill/rule/stubs match
  staging; `[ok] public-privacy` present.
- **Parallelism:** after the public/** tasks.

### [ ] T-011-20 — Release final gate
- **Owner:** software-engineer · **Maps:** all
- **Write set:** none (verification)
- **Preconditions:** all code tasks `[x]` except T-011-21.
- **Acceptance (AC-W6-01):** (1) `pytest -p no:cacheprovider` 0 failures; (2) `ruff
  format --check && ruff check --no-cache` clean; (3) `mypy --strict` clean;
  (4) import-linter 0 violations, ignore cap not increased; (5) `dadaia public
  doctor` exit 0; (6) `dadaia specs doctor` exit 0 AND no NEW WARNs vs the release
  baseline (zero `token_estimate` WARNs is verified at CLOSURE by T-011-21, not
  here — qa Q-M2); (7) `dadaia ci preflight` exit 0 with poetry off PATH (real-tree
  proof for AC-W2-01); (8) 6/6 bug → named-regression-test table assembled for
  CLOSURE; (9) v0.1.10 two-actor e2e still green.
- **Parallelism:** last code-side task; gates rc-1 ship-trio (ADR-2).

### [ ] T-011-21 — Memory truth + token_estimate regeneration + R8 doc nits + CLOSURE (PE, CLOSURE phase)
- **Owner:** product-engineer · **Maps:** FR-W5-03; FR-W5-05 memory half (qa Q-M2,
  arch MINOR-3); SPEC "Memory files affected"; bug B1 dogfood (first disposition
  sweep)
- **Write set:** `specs/memory/architecture.md`,
  `specs/memory/product/sdd/{sdd-gate-v3,specs-doctor}.md`,
  `specs/memory/product/platform/context-management.md`,
  `specs/memory/product/agents/agent-comms.md`,
  `specs/memory/product/philosophy/repos-catalog.md` (if xlsx changed),
  `specs/memory/product/catalog.json` + atom frontmatter `token_estimate` values
  (mechanical regeneration via `public/scripts/generate-memory-catalog.py` —
  MANDATED here, MEMORY class, PE-only),
  `specs/memory/tech-stack.md` (if pins changed), `specs/releases/v0.1.11/CLOSURE.md`,
  bug/backlog disposition frontmatter (ADR-11 terminal tokens + evidence pointers)
- **Preconditions:** ALL tasks `[x]`; alpha-1 qa commit + rc-1 ship-trio APPROVE;
  ACTIVE.md phase CLOSURE.
- **Acceptance:** memory atoms describe the post-fix product (heartbeat-renewed bind
  GC, liveness qualifier, getppid caveat, new doctor invariants, repo_url lifecycle,
  artifact resolution) — no changelog sections; memory frontmatter regenerated and
  `dadaia specs doctor` re-verified with ZERO `token_estimate` WARNs (the CLOSURE
  half of AC-W5-03); CLOSURE.md carries the new `## Dispositions` section with 6/6
  bugs `Closed` + the picked residual backlog entry `DELIVERED — v0.1.11` + the
  `plugin-packs-and-install-command` backlog return (ADR-11 vocabulary); `dadaia
  specs doctor` exit 0; archive via `git mv` after operator merge gate.
- **Parallelism:** LAST.
