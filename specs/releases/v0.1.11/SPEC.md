# SPEC: v0.1.11 — Lifecycle Hygiene + Kernel Tail (all open bugs + v0.1.11 audit residuals)

**Status:** Aprovado
**Release ID:** v0.1.11
**Owner:** product-engineer
**Created:** 2026-06-10
**Branch:** `feature/v0.1.11` (stacked on `feature/v0.1.10`, PR #53 open — operator holds merge)

---

## Objective

One release that (1) solves **all 6 open bugs** and (2) burns down the ranked residual
list of the v0.1.10 final re-audit (`specs/backlog/v0.1.11-audit-residuals.md`, items
1–10, sourced from `specs/audits/2026-06-10T052944Z/index.md §5`). Theme: finish the
v0.1.10 concurrency-kernel invariants (no-steal everywhere, durable READ binds, single
session-store owner) and close the **lifecycle hygiene loop** — consumed backlog/bugs
get terminal dispositions, stale leases get a safe reclaim path, and validation surfaces
(ci-preflight, handoff resolver, context repo_url) stop dead-ending honest workflows.

**Grill-me:** satisfied by the operator's explicit written goal-directive (2026-06-10:
"solve 5 bugs and solve the release v0.1.11 residuals", autonomous completion) plus the
pre-answered grill context recorded as Decisions ADR-1..ADR-10 below, per
release-governance (v0.1.10 precedent). The 6th bug
(`context-repo-url-not-settable-or-repairable`, filed 2026-06-10) is folded per the
v0.1.10 all-open-bugs precedent and the bugs-always-solved law (ADR-1).

---

## Bug inventory and resolution map (6/6)

| Bug | Sev | Resolution |
|-----|-----|-----------|
| `release-closure-leaves-consumed-backlog-unsanitized` | HIGH | W3 (T-011-09 skill sweep, T-011-10 doctor invariants) |
| `ci-preflight-checks-hardcode-poetry-run` | MEDIUM | W2 (T-011-06) |
| `doctor-stale-lease-misdiagnosed-as-forgery` | MEDIUM | W1 (T-011-01 probe side doors, T-011-02 lease GC, T-011-03 SPEC-DOC-029 triage) |
| `handoff-artifact-path-cannot-reference-specs-audits` | MEDIUM | W2 (T-011-07) |
| `plugin-install-command-missing` | MEDIUM | W4 (T-011-12, honest-relabel per ADR-4) |
| `context-repo-url-not-settable-or-repairable` | MEDIUM | W2 (T-011-08, scope per ADR-7) |

No bug is silently dropped (bug-always-solved law). Per-bug acceptance: the repro
recorded in the bug file now passes (behavior matches the bug's **Expected** section),
and each bug carries a named regression test, closed with the test reference.

## Residual inventory and resolution map (10/10)

| # | Residual | Resolution |
|---|----------|-----------|
| R1 | Probe-less CLI side doors (`lock steal`, `lease._main`) | T-011-01 (ADR-5: keep + probe-gate) |
| R2 | Lifecycle-asymmetry map mechanical enforcement | T-011-11 (contract test) |
| R3 | Bind-record GC decay (silent READ→IMPLEMENTATION) | T-011-04 (ADR-8 amended: heartbeat-renewed `last_seen_at` + TTL GC) |
| R4 | Session-path ownership residue (3 in-scope sites + documented core exception) | T-011-05 (ADR-12) |
| R5 | Panel token in launch URL | T-011-13 (ADR-10: short-TTL launch token) |
| R6 | ctx-inject bootstrap bloat + sentinel GC | T-011-14 |
| R7 | Public-source hygiene (`__pycache__`, `repos.xlsx`) | T-011-15 |
| R8 | Doc/ledger nits | T-011-16 (code half) + T-011-21 (memory half, CLOSURE) |
| R9 | Opportunistic venv tooling bumps | T-011-17 (bump-or-defer with reason) |
| R10 | WARN cleanups ONLY (token_estimate; SPEC-DOC-027 legacy dirs) | T-011-18 (ADR-3/ADR-9); escape-record axis OUT OF SCOPE |

---

## Workstreams

### W1 — Concurrency-kernel tail (bug B3 + residuals R1, R3, R4)

Finishes the v0.1.10 liveness/identity invariants on the surfaces the re-audit found
unfinished.

**Grounding:** `cli/commands/lock.py:51` (`lease.steal` TTL-only), `lease.py:576`
(`_main` acquire side door), bug `doctor-stale-lease-misdiagnosed-as-forgery` (36 h-old
heartbeat, `ttl: 120`, record predating the `pid` field, SPEC-DOC-029 alleging forgery),
residual #3 (bind records `ttl_seconds: 300`, never renewed), residual #4 (sites
constructing `sessions/` paths outside `session_identity` — in scope:
`cli/commands/context.py:76`, `spec_context/doctor.py:124`, `panel/views/kanban.py:85`;
`core/specs_resolver.py:34` stays as the documented closed-allowlist exception in
`tests/contract/test_session_store_ownership.py`, since core cannot import the
features-layer owner — ADR-12).

**Functional requirements:**
- FR-W1-01: `dadaia lock steal` consults the pid-liveness probe: recorded pid alive ⇒
  refuse (even past TTL); pid dead or record pre-pid ⇒ TTL rule as today. `lease._main`
  acquire threads the same probe (the v0.1.10 `pid_probe` param of
  `core/lock_liveness.is_stale`). `pid_probe` becomes a REQUIRED parameter on the
  lease acquire/steal call-site signatures (`mypy --strict` enforces it); existing
  pid-less test fixtures stay green via the no-pid ⇒ TTL rule. No probe-less
  acquire/steal path remains (grep-able).
- FR-W1-02: a GC/reclaim path exists for expired leases whose holder is demonstrably
  dead, **including records that predate the `pid` field** (treated as unprobeable ⇒
  TTL-only reclaimable). Exposed via workspace doctor `--fix` (new issue code, e.g.
  `LOCK-GC`); a live-pid holder is NEVER reclaimed regardless of TTL.
- FR-W1-03: SPEC-DOC-029 distinguishes three states: (a) stale lease, holder dead/
  unprobeable ⇒ WARN "stale lease from dead session — safe to reclaim" + remediation
  command named in the message (`dadaia doctor --fix` / `dadaia lock steal <ctx>`);
  (b) live-holder lease ↔ session record genuinely incoherent ⇒ ERR (forgery wording
  permitted ONLY here); (c) coherent ⇒ ok. A TTL-expired dead-holder record never
  produces forgery language or a doctor ERR.
- FR-W1-04 (ADR-8 amended): bind/session records carry a `last_seen_at` field that the
  **existing PostToolUse heartbeat** (`hooks/sdd_post_gate.py`, which already resolves
  the harness session id) also refreshes on every tool use; GC stays **TTL-based,
  measured against `last_seen_at`**. A still-active session renews on every tool use
  and never decays (no silent READ→IMPLEMENTATION decay); a dead session's bind decays
  after TTL. The session-record pid is NOT used for bind GC — it is the transient
  bind-CLI pid (`context.py:367`), dead by construction.
- FR-W1-05: the 3 in-scope residual sites (`cli/commands/context.py:76`,
  `spec_context/doctor.py:124`, `panel/views/kanban.py:85`) construct zero `sessions/`
  paths directly — they call `session_identity`; the
  `tests/contract/test_session_store_ownership.py` grep extends to cover them.
  `core/specs_resolver.py` remains the documented closed-allowlist exception in that
  contract test (ADR-12).

### W2 — CLI/validation seams (bugs B2, B4, B6)

**Functional requirements:**
- FR-W2-01 (B2): `features/ci_preflight/service.py` derives every check argv from the
  **resolved runner environment** via `_resolve_tool` with pinned order — venv sibling
  of `sys.executable` → `DADAIA_BIN`-derived bin dir → `("poetry","run",...)` fallback
  ONLY when no sibling exists. NO `shutil.which` (no ambient-PATH resolution).
  Acceptance includes the bug's repro: preflight passes with poetry absent from PATH.
- FR-W2-02 (B4): `reports_validation/service.py:_resolve_artifact_path` resolves ANY
  relative `artifact.path` that exists under `workspace_root` as workspace-rooted
  (covering `repos/<slug>/specs/audits/...`); the handoff-dir fallback is kept for
  legacy paths that only exist there; when a path is resolvable BOTH workspace-rooted
  and handoff-relative, workspace-root wins (asserted explicitly by a both-exist
  fixture); the schema stays anchored (no absolute paths, no `..`) — schema file
  unchanged.
- FR-W2-03 (B6, scope per ADR-7): (a) `dadaia context create --url <url>` passes
  through to the existing service `create(name, repo_slug, repo_url)`; (b) `context
  alive`/`dead` back-fill `repo_url` from `git remote get-url origin` when the record
  URL is empty and a repo exists on disk; (c) `dadaia context update --url <url>`
  repair verb over the existing store `update()` API; (d) workspace doctor flags an
  ALIVE context whose record has an empty `repo_url` (new code, e.g. `CTX-URL-1`).

### W3 — Closure contract (bug B1 + residual R2)

**Functional requirements:**
- FR-W3-01 (B1a): the `dadaia-release-closure` skill SOURCE
  (`dadaia_workspace/public/skills/dadaia-release-closure/`) gains a **mandatory
  disposition-sweep step** before archive: every backlog item and bug picked into (or
  superseded by) the release is flipped to a terminal status token per the ADR-11
  vocabulary (bugs ⇒ `Closed`, optionally with `superseded_by:` frontmatter; backlog ⇒
  one of the ADR-11 terminal tokens, e.g. `DELIVERED — vX.Y.Z` / `SUPERSEDED — <slug>`)
  with an evidence pointer (CLOSURE section or commit). The CLOSURE template gains a
  `## Dispositions` section listing the sweep. Never delete; always mark with reason
  (release-governance).
- FR-W3-02 (B1b): two new specs-doctor invariants, both consuming the ADR-11
  vocabulary: **SPEC-DOC-031** — a `specs/backlog/**` entry with non-terminal status
  (ADR-11 non-terminal set, case-insensitive prefix match on the Status line) whose
  slug/ID appears in an **archived** release CLOSURE/SPEC ⇒ WARN (not ERR — ADR-6:
  slug mention ≠ consumption; CLOSURE "Backlog returns" legitimately cites backlog
  slugs; defer/supersede mentions in archived CLOSUREs are the known false-positive
  class that keeps this WARN); **SPEC-DOC-032** — a `specs/bugs/**` file whose
  `status:` is outside the ADR-11 bug canon ({`Open`, `Closed`}) ⇒ WARN. Note: the
  2026-06-10 PM sweep already normalized legacy `Fixed`/`resolved` tokens — this
  invariant guards regressions, not a backlog of repairs.
- FR-W3-03 (R2): a contract test mechanically enforces the lifecycle-asymmetry map at
  its actual home — the map table in `tests/contract/README.md` (delivered in v0.1.10
  T-010-27): EVERY subpackage of `dadaia_workspace/features/` (enumerated via
  pkgutil/dir listing at test time) must have a map row or an explicit GAP cell. The
  current map covers ~6 of 21 subpackages — authoring the ~15 missing rows/GAP cells
  is part of the task; adding a feature without a row fails the test.

### W4 — Plugin honesty + panel + inject (bug B5 + residuals R5, R6)

**Functional requirements:**
- FR-W4-01 (B5, ADR-4): honest-relabel. Verified at definition time: NO plugin pack
  assets exist under `dadaia_workspace/` (only thin stubs with `plugin: true`
  frontmatter; `public/plugins/*.ts` are OpenCode harness plugins, unrelated). The
  `plugin-scope` rule and the 3 agent stubs (`frontend-engineer`, `design-specialist`,
  `devops-engineer`) stop referencing the nonexistent `dadaia plugin install` command;
  new wording states plugin packs are not yet distributed and routes the work to the
  operator (with the backlog pointer). All 7 `plugin install` references
  (`public/rules/plugin-scope.md:17,18,19,27`, 3 stubs `:12`) rewritten; a CLOSURE
  backlog return registers `plugin-packs-and-install-command` as the real feature.
- FR-W4-02 (R5, ADR-10 amended): the long-lived panel Bearer token never appears in
  any URL. Panel launch uses a single-use, short-TTL (≤60 s) launch token exchanged
  server-side for the session credential; replay of a consumed/expired launch token ⇒
  401. CSRF posture pinned: the exchanged cookie is `SameSite=Strict; HttpOnly`;
  sensitive APIs remain **Bearer-only** — the cookie gates only the UI shell.
  Tokenless sensitive-API contract from v0.1.10 (AC-R7-03) stays green.
- FR-W4-03 (R6): ctx-inject injects a **tldr-digest** of `catalog.json` (drop the
  `summary` field; keep slug/title/tldr/path/rank) — measured payload reduction
  recorded; orphan/stale once-per-session sentinel files are GC'd (doctor `--fix`
  sweep or self-cleanup at inject time).

### W5 — Hygiene / docs / tooling (residuals R7, R8, R9, R10)

**Functional requirements:**
- FR-W5-01 (R7): `public/scripts/__pycache__/` eliminated and prevented from
  regenerating (scripts executed with bytecode writing disabled, e.g. `python -B` /
  `PYTHONDONTWRITEBYTECODE=1` at the invocation sites) + wheel/sdist exclusion +
  hygiene contract test; `public/data/repos.xlsx` investigated — its consumer is the
  context-create catalog lookup (`cli/commands/context.py:113-120`, `repos-catalog`
  memory atom): either confirmed generic/sample content + documented, or replaced
  with a generic sample (privacy law: public assets carry no operator-local data).
- FR-W5-02 (R8 code half): stale `_ENV_BASELINE` docstring ref fixed
  (`tests/unit/hooks/test_sdd_post_gate.py:12`); duplicate probe construction in
  `hooks/sdd_gate.py` deduplicated (cosmetic).
- FR-W5-03 (R8 memory half, CLOSURE phase): `specs/memory/architecture.md`
  mode-resolution parenthetical gains the liveness qualifier (DRIFT-M3); the sdd-gate
  atom gains the one-sentence `getppid` shell-wrapper caveat. MEMORY-class writes —
  scheduled for the CLOSURE phase (T-011-21), per gate law.
- FR-W5-04 (R9): dev/venv tooling bumps (`pip`/`poetry`/`dulwich`) applied where a
  fixed release exists; otherwise an explicit defer with reason recorded in CLOSURE
  (out-of-runtime CVEs, documented in `pyproject.toml` comments).
- FR-W5-05 (R10, ADR-3/ADR-9): WARN-cleanup work ONLY, split by writer: the
  software-engineer half (T-011-18) covers **non-memory** cleanups only — the
  SPEC-DOC-027 legacy `_archive` dir WARNs silenced via a **permanent documented
  legacy allowlist** in the doctor (no renames of frozen archive history). The memory
  `token_estimate` regeneration (catalog/frontmatter to actual estimates) is MEMORY
  class and MANDATED to T-011-21 (PE-only, CLOSURE phase); zero target
  `token_estimate` WARNs is re-verified at CLOSURE, not at the final gate. The
  escape-record axis is explicitly OUT OF SCOPE (time-earned non-work).

### W6 — Projection + final gate

Changed `public/**` assets (W3 skill, W4 rule/stubs, W5 scripts hygiene) are
re-staged and re-projected (`dadaia public stage && install --target all && public
doctor` exit 0). The final gate re-runs the full validation battery and assembles the
6/6 bug → named-regression-test table for CLOSURE.

---

## Decisions (ADR-1..ADR-12; ADR-1..3 are operator pre-answers from the goal-directive grill; ADR-8/10 amended and ADR-11/12 added at spec-review fold, coordinator pre-decided)

- **ADR-1 Scope = all 6 open bugs + residuals R1–R10.** Operator directive 2026-06-10
  ("solve 5 bugs and solve the release v0.1.11 residuals", autonomous completion); the
  6th bug (`context-repo-url-…`, filed the same day) folded per the v0.1.10
  all-open-bugs precedent and the bugs-always-solved law.
- **ADR-2 Cadence: single alpha-1 segment → rc-1 ship-trio.** alpha-1 end = qa-only
  review commit; rc-1 end = qa + code-reviewer + security-reviewer, all APPROVE → push
  + PR. Operator holds the merge. Flat release dir (no `segment:` in ACTIVE.md),
  mirroring the v0.1.10 precedent.
- **ADR-3 R10 conservative.** Only the actual WARN-cleanup work is in scope; the
  escape-record axis (qa 1.5/2) is time-earned by letting this cycle run with no
  escapes past green tests — explicitly NOT work in this release.
- **ADR-4 B5 resolved by honest-relabel, not a `dadaia plugin` command.** Verified at
  definition: no plugin pack assets exist anywhere under `dadaia_workspace/` — an
  `install` command would have nothing to install, and `list` over a nonexistent
  manifest is invented surface. Smallest honest fix: rule + stubs stop citing the
  command; the real plugin-pack distribution + install command goes to backlog at
  CLOSURE (`plugin-packs-and-install-command`).
- **ADR-5 `dadaia lock steal` is kept, probe-gated — not deleted.** It becomes the
  documented operator remediation for B3's dead-session stale lease; with the liveness
  probe threaded it can no longer steal from a live holder, removing the reason to
  delete it.
- **ADR-6 SPEC-DOC-031 severity is WARN, not ERR.** A slug appearing in an archived
  CLOSURE is necessary-but-not-sufficient evidence of consumption (the "Backlog
  returns" section cites slugs it is ADDING, not consuming; defer/supersede mentions
  in archived CLOSUREs are a further known false-positive class). WARN keeps doctor
  exit 0 contractual while surfacing the drift; escalation to ERR is earned after a
  clean cycle. SPEC-DOC-032 (bug status canon) likewise WARN.
- **ADR-7 B6 ships (a) `create --url` + (b) alive/dead back-fill + doctor flag + (c)
  `context update --url`.** (c) is included: the store `update()` API already exists,
  and the VPS-migration scenario needs a repair path when no on-disk repo is present
  to back-fill from. All four surfaces from the bug's Expected section land.
- **ADR-8 (AMENDED at spec-review, architect A1) Bind-record GC is
  heartbeat-renewed TTL, not pid-liveness.** The original pid-liveness design was
  unsound: the session-record pid is the transient bind-CLI pid (`context.py:367`),
  dead by construction — pid-keyed GC would collect every real READ bind. Decided
  fork (a): the existing PostToolUse heartbeat (`hooks/sdd_post_gate.py`, which
  already resolves the harness session id) ALSO refreshes the session/bind record's
  `last_seen_at`; GC stays TTL-based, measured against `last_seen_at`. An active
  session renews on every tool use; a dead session's bind decays after TTL.
  Acceptance must exercise the REAL renewal path — no planted-pid fixtures.
- **ADR-9 SPEC-DOC-027 legacy `_archive` dirs: permanent documented allowlist, no
  renames.** Renaming frozen archive history to silence a WARN is churn that breaks
  historical pointers; the allowlist (with rationale) is the honest permanent record.
  Forward enforcement for NEW dirs is unchanged.
- **ADR-10 (AMENDED at spec-review, architect A3) Panel launch token: single-use
  short-TTL token; the Bearer never enters a URL; CSRF posture pinned.** The
  exchanged cookie is `SameSite=Strict; HttpOnly`; sensitive APIs remain Bearer-only
  (the cookie gates only the UI shell); launch token single-use, TTL ≤60 s, replay ⇒
  401; the Bearer appears in no URL of any kind. Implementer chooses the exchange
  mechanism within these pins.
- **ADR-11 Status-token vocabulary (single source).** Bugs: non-terminal = {`Open`};
  terminal = {`Closed`} (optionally with `superseded_by: <slug>` frontmatter);
  SPEC-DOC-032 WARNs on anything else. Backlog: non-terminal = {`OPEN`, `PICKED`,
  `CANDIDATE`}; terminal = {`DELIVERED`, `SUPERSEDED`, `RESOLVED`, `CONSUMED`,
  `DEFERRED`, `REJECTED`} — matched case-insensitively as a prefix of the Status line
  (suffixes like `— vX.Y.Z` / `— <slug>` allowed). FR-W3-01, FR-W3-02, and
  release-governance wording all reference THIS vocabulary; it is stated nowhere else.
- **ADR-12 `core/specs_resolver.py` keeps its documented allowlist exception.**
  Core cannot import the features-layer `session_identity` owner (layer rule); the
  site stays as the closed-allowlist exception documented in
  `tests/contract/test_session_store_ownership.py`. Moving the session-path seam into
  core was considered and rejected as out-of-proportion for this release. T-011-05 is
  scoped to the 3 legal sites only.

---

## Architecture deltas

- `features/spec_context/lease.py` — probe threaded through `_main` acquire; steal
  probe-gated; GC/reclaim helper for dead-holder records (pre-pid-safe).
- `cli/commands/lock.py` — `steal` consumes the probe.
- `features/spec_context/doctor.py` — `LOCK-GC` reclaim under `--fix`;
  `last_seen_at`-TTL bind-record GC; `CTX-URL-1` empty-repo_url flag; `doctor.py:124`
  site migrated to `session_identity`.
- `hooks/sdd_post_gate.py` — PostToolUse heartbeat additionally refreshes the
  session/bind record `last_seen_at` (ADR-8).
- `features/specs/doctor.py` — SPEC-DOC-029 three-state triage with remediation
  message; SPEC-DOC-031/032 disposition invariants; SPEC-DOC-027 legacy allowlist.
- `features/ci_preflight/service.py` — runner-derived check argv (sibling-executable
  resolution, poetry fallback only).
- `features/reports_validation/service.py` — workspace-rooted relative artifact
  resolution with handoff-dir legacy fallback.
- `cli/commands/context.py` + `features/spec_context/service.py` — `create --url`,
  alive/dead back-fill, `update --url`; `context.py:76` site migrated.
- `panel/views/kanban.py` — session-path site migrated to `session_identity`
  (`core/specs_resolver.py` untouched — documented allowlist exception, ADR-12).
- `features/panel/` — launch-token exchange; Bearer out of URLs.
- `hooks/ctx_inject.py` — tldr-digest injection; sentinel GC; `hooks/sdd_gate.py`
  probe dedup.
- Public assets — closure skill disposition step; plugin-scope rule + 3 stubs
  relabeled; scripts bytecode hygiene. No new agent personas; no new path classes;
  no lease-record schema change.

## Tech-stack deltas

None at runtime. Dev/venv: opportunistic `pip`/`poetry`/`dulwich` bumps (FR-W5-04) or
documented defer.

## Security/operations deltas

- No-steal invariant extended to the last probe-less surfaces (`lock steal`,
  `lease._main`) — closes the residual confused-deputy tail.
- Panel long-lived credential removed from URLs (history/referrer exposure).
- `repos.xlsx` privacy posture verified for the public boundary.

## Memory files affected at closure

- `specs/memory/architecture.md` — mode-resolution liveness qualifier (R8); lease GC
  + bind-GC model.
- `specs/memory/product/sdd/sdd-gate-v3.md` — `getppid` caveat (R8).
- `specs/memory/product/sdd/specs-doctor.md` — SPEC-DOC-029 triage, 031/032, 027
  allowlist.
- `specs/memory/product/platform/context-management.md` — repo_url lifecycle, bind
  GC, lock-steal probe.
- `specs/memory/product/agents/agent-comms.md` — workspace-rooted artifact
  resolution.
- `specs/memory/product/philosophy/repos-catalog.md` — repos.xlsx disposition (if
  changed).
- `specs/memory/tech-stack.md` — only if dev pins change (else "no change" with
  reason).
- `specs/constitution.md` — no edit expected; any need surfaces to the operator first.

---

## Acceptance criteria

Each AC is evidence-triple friendly: {description, command, evidence}.

- **AC-W1-01** Probe side doors closed: unit tests — `lock steal` with TTL-expired +
  alive pid ⇒ refuse exit 1; TTL-expired + dead pid ⇒ steal ok; `lease._main` acquire
  blocked by alive-probed holder. Command: `pytest tests/unit/.../test_lease*.py
  tests/unit/cli/test_lock*.py`. (FR-W1-01)
- **AC-W1-02** `dadaia doctor --fix` reclaims a planted TTL-expired dead-holder lease
  (including a record WITHOUT a `pid` field) and never reclaims a live-pid record;
  bug B3 repro steps 1–4 re-run: doctor reports the stale-lease WARN + remediation
  command, exits 0 — no forgery wording, no ERR. (FR-W1-02/03)
- **AC-W1-03** SPEC-DOC-029 unit fixtures: dead-stale ⇒ WARN with remediation;
  live-incoherent ⇒ ERR; coherent ⇒ silent. PLUS a named composed integration test
  (`test_stale_pidless_lease_with_fresh_read_bind_warns_not_err`): fixture built via
  the PRODUCTION writers — TTL-expired (~36 h) pid-LESS lock record + fresh READ bind
  → `dadaia specs doctor` ⇒ WARN (not ERR), remediation text names the reclaim
  command, exit 0, output contains no forgery wording. (FR-W1-03, bug B3)
- **AC-W1-04** Bind-record GC exercises the REAL renewal path (no planted-pid
  fixtures): simulate a PostToolUse hook invocation refreshing the bind record's
  `last_seen_at`, then run the GC sweep ⇒ record survives and the gate still resolves
  READ; a stale record with old `last_seen_at` (past TTL, no renewal) ⇒ GC'd.
  (FR-W1-04, ADR-8)
- **AC-W1-05** Ownership grep contract covers the 3 migrated sites; grep for direct
  `sessions/` path construction outside `session_identity` returns only the owner
  module plus the documented `core/specs_resolver.py` allowlist entry (ADR-12).
  (FR-W1-05)
- **AC-W2-01** With poetry absent from PATH (env-sanitized subprocess test),
  `dadaia ci preflight` builds argv from the resolved venv bin and exits 0; argv unit
  tests cover the pinned order (venv sibling → `DADAIA_BIN` → poetry fallback; no
  `shutil.which`). The e2e runs against a FAKE tree / stubbed checks (no
  pytest-inside-pytest); the real-tree run is final-gate item 7. (FR-W2-01, bug B2)
- **AC-W2-02** A handoff whose `artifact.path` is
  `repos/<slug>/specs/audits/<UTC>/audit.md` (file present, correct sha256) validates
  exit 0 via `dadaia reports validate`; legacy handoff-dir-relative paths still
  validate; a both-exist fixture (path resolvable workspace-rooted AND
  handoff-relative) asserts workspace-root wins; absolute/`..` still rejected.
  (FR-W2-02, bug B4 repro)
- **AC-W2-03** `dadaia context create foo --repo foo --url <url>` persists the URL;
  empty-URL record + on-disk repo with origin ⇒ `context alive`/`dead` back-fills;
  `context update --url` repairs; workspace doctor flags ALIVE+empty-URL (CTX-URL-1).
  (FR-W2-03, bug B6 repro)
- **AC-W3-01** Closure skill source contains the mandatory disposition-sweep step +
  `## Dispositions` template section; projected copies match after reprojection.
  (FR-W3-01)
- **AC-W3-02** SPEC-DOC-031/032 unit fixtures fire on planted stale-backlog /
  non-canonical-bug-status trees; `dadaia specs doctor` on the repaired self-hosting
  tree exits 0 with the new invariants active (residual stale entries dispositioned
  via PM coordination, evidence in CLOSURE). (FR-W3-02)
- **AC-W3-03** Lifecycle-asymmetry contract test parses the map table in
  `tests/contract/README.md`, enumerates `features/` subpackages at test time, and
  fails on any subpackage without a row or explicit GAP cell; a synthetic unmapped
  subpackage makes it fail; the current tree passes ONLY after the ~15 missing
  rows/GAP cells are authored (that authoring is part of the task). (FR-W3-03)
- **AC-W4-01** `grep -r "plugin install" dadaia_workspace/public/` returns zero
  references to the nonexistent command, pinned permanently by
  `tests/contract/test_plugin_install_residue.py`; `[PLUGIN REQUIRED]` wording routes
  honestly; `dadaia public doctor` exit 0 after reprojection. (FR-W4-01, bug B5)
- **AC-W4-02** Panel e2e (the binding contract): launch URL contains no long-lived
  Bearer (grep corpus: panel views + launch/registry code + tests); consumed/expired
  launch token replay ⇒ 401; exchanged cookie is `SameSite=Strict; HttpOnly` and
  gates only the UI shell — sensitive APIs stay Bearer-only; v0.1.10
  tokenless-sensitive-API contract still green. (FR-W4-02)
- **AC-W4-03** ctx-inject payload test: injected catalog digest carries no `summary`
  field; byte-size reduction asserted and recorded; stale sentinel sweep covered by
  test. (FR-W4-03)
- **AC-W5-01** No `__pycache__` under `dadaia_workspace/public/` after running the
  catalog/lint scripts (test executes them and asserts); wheel build excludes `.pyc`;
  repos.xlsx disposition documented (commit or doc pointer). (FR-W5-01)
- **AC-W5-02** Named nit fixes verified by file:line in CLOSURE
  (`test_sdd_post_gate.py:12` docstring; `sdd_gate.py` single probe construction).
  (FR-W5-02)
- **AC-W5-03** Split per writer (qa Q-M2): at the final gate, `dadaia specs doctor`
  exits 0 with zero SPEC-DOC-027 WARNs (legacy allowlist active, documented in the
  doctor source; forward enforcement still fires on a synthetic new bad dir) and no
  NEW WARNs introduced by this release; zero target `token_estimate` WARNs is
  re-verified at CLOSURE (T-011-21) after PE regenerates the memory frontmatter
  (MEMORY class, PE-only). (FR-W5-05)
- **AC-W6-01** Final gate: (1) `pytest -p no:cacheprovider` 0 failures;
  (2) `ruff format --check && ruff check --no-cache` clean; (3) `mypy --strict`
  clean; (4) import-linter 0 violations, ignore cap not increased; (5) `dadaia public
  doctor` exit 0; (6) `dadaia specs doctor` exit 0 AND no NEW WARNs vs the release
  baseline (zero `token_estimate` WARNs is a CLOSURE criterion, T-011-21, not a gate
  criterion); (7) `dadaia ci preflight` exit 0 with poetry off PATH (real tree);
  (8) 6/6 bug → named-regression-test table assembled for CLOSURE.

---

## Out of scope

- The escape-record axis (R10) — time-earned non-work (ADR-3).
- A real `dadaia plugin` command group / plugin pack distribution — backlog return at
  CLOSURE (ADR-4).
- Renaming legacy `_archive` release dirs (ADR-9).
- Escalating SPEC-DOC-031/032 to ERR (earned next cycle, ADR-6).
- Classifying Bash command strings; harness env propagation (v0.1.10 D-2 posture
  unchanged).
- PyPI publish; PR #53 / feature-branch merges (operator-gated).

## Dependencies and risks

- **Stacked branch:** `feature/v0.1.11` stacks on unmerged `feature/v0.1.10` (PR #53).
  Rebase risk if rc feedback lands on v0.1.10; mitigation: keep the stack linear,
  operator owns merges.
- **SPEC-DOC-031 matching heuristics** (slug in archived CLOSURE/SPEC) risk false
  positives — mitigated by WARN severity (ADR-6) and a "Backlog returns"-section
  exclusion in the matcher.
- **Bind-GC renewal** depends on the PostToolUse heartbeat firing — a session that
  never issues a tool call decays after TTL (accepted: such a session holds no work);
  records without `last_seen_at` keep today's TTL-from-creation behavior (documented).
- **Panel launch-token** touches auth; the v0.1.10 401-contract tests must stay green
  (regression suite re-run).
- **ci-preflight argv rework** runs inside the pre-push hook — fail-closed messaging
  preserved; both resolution branches unit-tested with fake trees.
- **Shared files:** `features/specs/doctor.py` (T-011-03/10/18) and
  `features/spec_context/doctor.py` (T-011-02/04/05) and `cli/commands/context.py`
  (T-011-05/08) are sequenced, not parallel — declared in TASKS.
