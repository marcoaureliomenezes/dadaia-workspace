# SPEC — v0.1.47 — Context-Surface Truth + Fragments/Personas Optimization + Audit Remediation

**Status:** Aprovado
**Release:** v0.1.47 · **Branch:** `feature/v0.1.47` · **Origin:** operator `/goal` directive
2026-07-01 + audit `specs/audits/20260701T201136Z-0bcd6c19/` + audit
`specs/audits/20260701T135346Z-6145b869/` residual (the v0.1.47 sweep ACTIVE.md earmarked).
**Grill:** `GRILL.md` (mandatory session — decisions D-1..D-11).

**Consumes:** specs-truth-realignment-constitution-memory

## 1. Problem

The 2026-07-01 full audit scored the workspace 7/10: implementation green (4306 tests,
strict typing) but the **context surface lies in places** — the constitution encodes a
removed harness and a 5-member runtime enum as law; memory documents a panel auth control
that does not exist and a bug-format world v0.1.46 retired; enforcement claims exceed
mechanisms (persona injection pipeline-only; import-linter "in CI" nowhere; root-whitelist
nested hole); prompt-context assets (fragments/personas) have never had a dedicated
de-slop review; per-harness capability/scaffolding truth is scattered; and Layer-2 codex
workers are dead on the installed CLI. Additionally the bug JSONL store is untracked by
git and the source repo was un-commit-able until the backlog sanitization in this
release's definition.

## 2. Goal

Every context element an agent consumes — constitution, memory, rules, AGENTS.md, skills,
fragments, personas — states only what is true, exactly once, at the altitude an agent
needs; the prompt-assembly pipeline injects persona + fragment into every worker prompt on
every verb; Layer-2 workers run again on the installed CLIs; and every 2026-07-01 audit
finding carries an explicit disposition.

## 3. Workstreams

### W1 — Prompt-assembly + enforcement code fixes (software-engineer)

| id | item | acceptance |
|---|---|---|
| W1-1 | Codex exec argv: drop `--ask-for-approval` (approval is structurally "never" in exec); map "unexpected argument" stderr to an actionable adapter error; update the argv pin test | unit tests pass with new argv; a live `codex exec` smoke (env-gated) parses; bug `lifecycle-codex-review-passes-unsupported-ask-for-approval` → resolved |
| W1-2 | Delete inert `approved_commands` + `[skills] paths` from `runtime_config.codex_config()` | generated config carries neither; projection tests updated; bug `codex-config-emits-invalid-approved-commands` → resolved |
| W1-3 | Persona injection on ALL verbs: shared helper resolves role→persona; threaded into the 5 workflow bodies + CLI `_run_phase_step`; per-verb prompt-content tests | assembled prompt for every model step on every verb contains the persona body; bug `persona-injection-skipped-outside-pipeline-verb` → resolved |
| W1-4 | Pre-commit backlog gate scoping: BL-* block only when staged paths intersect `specs/backlog/**`; full sweep stays in CI | unrelated-file commit with pre-existing backlog debt passes; staged backlog violation still blocks; bugs `precommit-backlog-doctor-blocks-unrelated-commits` + `backlog-doctor-blocks-consumed-item-refactor-commit` → resolved |
| W1-5 | Preflight de-flake: exclude `tests/performance` from `ci preflight` pytest | preflight run selects no performance test; bug `prepush-gate-blocked-by-loadsensitive-perf-test-wallclock-bound` → resolved |
| W1-6 | Root-whitelist first-path-component classification (nested new-top-level writes blocked) | nested write under a non-whitelisted new root dir is blocked; allowed-root + exception-glob writes unaffected; bug `root-whitelist-misses-nested-new-toplevel-writes` → resolved |
| W1-7 | ctx-inject session attribution: `context bind` records the invoking harness pid (ProcessAncestry); the hook honors a bind-epoch marker only when attribution matches its own harness pid (fallback: unattributable ⇒ generic preflight, never another session's context) | two-session simulation test: session A bound ctx-a never receives ctx-b after B's later bind; bug `ctx-inject-newest-bind-epoch-steals-other-sessions-context` → resolved |
| W1-8 | `core/specs_resolver` persisted-bind fallback (env → persisted incumbent of an attributable/live bind → cwd) so `specs doctor`/`bugs`/`backlog` resolve from a bound workspace shell | `dadaia bugs status` succeeds from the workspace root in a bound session with no env; dup bug pair → one resolved, one superseded |
| W1-9 | Doctor recurrence guards: (a) SPEC-DOC-037 — constitution must enumerate no AgentRuntimeKind member/harness roster (cite memory) (backbone WS-E); (b) loose-undisposed-audit WARN on `specs/audits/` (the signal ACTIVE.md claimed of SPEC-DOC-035/036); (c) add `hooks` to `_DADAIA_ALLOWED_SUBDIRS` (bug `workspace-doctor-root4-false-positive-dadaia-hooks` → resolved) | new checks covered by tests; doctor green on the rewritten tree |
| W1-10 | SPEC-DOC-031 message text reconciled with BL-SCHEMA vocabulary (recommend bare terminal token + archive move, never `TOKEN — vX.Y.Z`) | following the doctor's remediation advice passes BL-SCHEMA; bug `backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict` → resolved |
| W1-11 | FAKE closure smoke (grill D-10): verify `lifecycle close --harness fake` advances or fails actionably; fix only if broken | smoke test recorded; fix or not-reproducible note |
| W1-12 | `setup.cfg` import-linter comment trued: contracts exist but are NOT CI-enforced yet; cite backlog `import-boundary-enforcement` | comment states deferred status; no source claims CI enforcement (see W3 grep acceptance) |

### W2 — Constitution + AGENTS.md truth (product-engineer; backbone WS-A consumed)

- Lean rewrite per WS-A1..A6 + grill D-2/D-3: ≈200 lines; zero OpenCode; zero runtime-kind
  enumeration (invariant + citation of `[[tech-stack]]`); §8 collapsed to binding invariants
  (≤ ~20 lines); §0 collapsed (vision → `[[product-vision]]`, layout → `[[architecture]]`);
  no inline amendment changelog (Governance section with semver header instead); no pinned
  tunables; root layout = nine entries. `Aprovado`/`Em revisão`/`Draft` tokens untouched.
- Layer model stated crisply: Layer 1 = entry harnesses `{claude, codex, pi}`; Layer 2 =
  dadaia-workflow workers `{pi, codex}` (+FAKE test-only); **Claude Code is Layer-1-only by
  law** (cost bound) and keeps its full scaffold; entry-harness-prefers-itself convention
  (grill D-7).
- `public/data/AGENTS.md`: reports-validate wording fixed (handoff JSON is the validated
  artifact — bugs `agents-md-says-validate-html-reports-with-json-only-validator` resolved,
  `reports-validate-rejects-html-despite-agents-md-contract` superseded); injection claim
  corrected (tech-stack digest + catalog, not constitution); harness preference convention
  added. Rules sweep: the 8 public rules checked for the same stale claims.

### W3 — Memory canon rewrite + harness docs (product-engineer; backbone WS-B/WS-C consumed)

- WS-B1..B8 as accepted (product-vision, harness-primitives, the 8 projection/runtime atoms,
  §13-compliant index.md, workflow-count single-source + dadaia-workflows atom, tech-stack
  PI-auth fix + kimi-2.7 + `#Agent runtimes` as roster single-source, architecture.md
  de-narrate/slim/extract + stale-line fixes, catalog regeneration).
- WS-C quality-assurance re-truing (budgets vs live counts, 5 governance jobs incl
  backlog-doctor, panel-e2e job, conftest guards, coverage statement).
- v0.1.46 catch-up: `sdd-bug-backlog-governance.md` rewritten for the JSONL event store;
  `specs-doctor.md` check inventory trued (022/023/033–036/SPECS-VERSION, 034 auto-fix);
  R-2 `_archive`-FROZEN rows added to `sdd-gate-v3.md` + architecture path tables.
- Truth fixes from the 2026-07-01 audit: panel.md + agent-monitoring.md auth sections →
  no-auth/Host-guard reality, kanban/workflows-JS claims, SQLite filename;
  spec-context-project.md injection claim; workspace-doctor.md check-vs-fix codes;
  context-management/server-registry/workspace-init nits; brand-identity token home.
  **Mechanical acceptance (auth truth):** `grep -Eci 'bearer|token-gated|loopback_bypass'`
  over panel.md, agent-monitoring.md, and the architecture.md panel sections == 0, and each
  states the loopback-bind + Host-allowlist model positively.
- **Import-linter CI-claim truth**: tech-stack.md, quality-assurance.md, architecture.md
  reworded — contracts exist, are red, and are NOT run in CI (deferred to backlog
  `import-boundary-enforcement`). **Acceptance:** no memory atom (nor `setup.cfg`, W1-12)
  claims import-linter runs in CI; grep for `import-linter` in `specs/memory/**` shows only
  the deferred/aspirational wording.
- NEW `memory/product/harness/{claude-code,codex,pi}.md` per grill D-5 (capability matrix ·
  scaffold matrix · isolation profile · Layer-2 defaults). `catalog.json`/`index.md`
  regenerated last.

### W2b — One-time consumer-law refresh (coordinator)

- `repos/dadaia-workspace/AGENTS.md` (the stale pre-Root-Law generated copy the dead
  fan-out never refreshes) manually re-synced from `public/data/AGENTS.md` once. This is a
  **sanctioned one-time exception** to the dev-guardrail non-edit rule, justified because
  the automated fan-out is structurally dead (audit A-7) and its redesign is deferred to
  backlog `consumer-agents-md-fanout-redesign`; a header note records this. Acceptance:
  byte-identical body to the source (modulo the generated header) via the guardrail-pair
  sha-compare, AND `dadaia public doctor` exit 0 after the sync (no drift introduced, no
  re-clobber on next install).

### W4 — Fragments + personas de-slop optimization (ai-engineer)

- All 32 `public/lifecycle_fragments/**`: each fragment states exactly what its ONE step
  prompt needs — role fit, inputs (static/dynamic), the task, output contract (transport
  `schema: agent-run-result-v1`; review verdict vs create artifact per `is_review`) — with
  no stale references, no duplicated boilerplate that belongs to shared fragments, no
  contradictions across fragments of the same workflow, no filler prose.
- All 8 `public/personas/*.md`: crisp sub-agent-style mandates (who you are, decision
  posture, what you never do), 5-key frontmatter, zero overlap with fragment task text,
  zero project-domain knowledge; `ai-engineer` persona's step-binding documented or the
  persona marked reserve.
- `dadaia-handoff-emitter` skill: workspace-root resolution instruction added (agent-side
  fix of `subagent-handoff-resolves-dadaia-inside-repo-cwd` → resolved; doctor backstop
  deferred to backlog).
- Acceptance: fragment/persona loaders + `persona_doctor`/`WMP` doctors green (parse
  validity), **plus a mandatory second-reviewer content sign-off**: an independent review
  pass over every rewritten fragment/persona judging de-slop criteria (no filler, no
  duplicated instruction blocks, no cross-fragment ambiguity, persona/fragment separation)
  with an APPROVE verdict recorded, and per-workflow prompt-assembly dumps attached as
  evidence; `dadaia public stage && install --target all && public doctor` exit 0 (also
  clears the live `lint-memory-atoms.py` drift).

### W5 — Dispositions (product-engineer + coordinator)

- Every finding of audit `20260701T201136Z-0bcd6c19` dispositioned (fixed here / deferred
  with reason to a NAMED backlog entry / superseded). New backlog entries (10):
  1. `lease-kernel-identity-hardening` — self-block sid-identity, pid-veto ACTIVE.md
     bypass, dangling by-session index, SPEC-DOC-029 namespace + `--specs-dir` isolation.
  2. `panel-runtime-reliability` — SQLite pragma'd-factory unification + DAO lifecycle +
     WAL-aware quarantine, kanban endpoint fate, mermaid render-or-escape.
  3. `context-dead-exit-path` — rmtree onexc + refspec push + pre-check ordering.
  4. `import-boundary-enforcement` — 5 red chains, CI + preflight wiring, cross-feature
     contract, workflows↔lifecycle cycle (and the setup.cfg comment finalization).
  5. `lifecycle-verb-governance-uniformity` — route `release define`/`backlog define`
     through the policy resolver (snapshot frozen, `apply_resolved_policy` sole author of
     `runtime_kind` on every verb); wire `audit`/`research`/`bug_report` as invocable verbs
     + container builders OR demote their catalog availability; fix
     `run_implement_review_loop` (inject the rejection digest, run through the runner gate,
     add a caller) — the audit B/Lifecycle cluster beyond persona injection (audit §E.4).
  6. `consumer-agents-md-fanout-redesign` — the structurally-dead marker detection.
  7. `harness-isolation-profiles` — `init` per-harness profiles + entry-harness
     auto-default for `--harness` (grill D-7/D-8 code half).
  8. `fragment-workflow-base-dedup` — the ~1,500-line FragmentGateWorkflow base extraction
     (grill D-6).
  9. `memory-heading-allowlist-extension` — consumer-extensible heading allowlist.
  10. `hygiene-and-dead-code-cleanup` — audit §C inventory (legacy hook `main()`s,
      `LEASE_TTL_SECONDS` re-export, `schema.open_connection` dead factory + telemetry
      `panel.token` drift-check, `academy.js` mermaid branch, `views/_assets.py` shim,
      `library_workflow_catalog()`, stale `core.js` comments, ADR-1 TODOs,
      `.import_linter_cache` location) + the `repos/*/.dadaia/` repo-hygiene doctor
      backstop (the deferred half of `subagent-handoff…`). Items overlapping entry 2 are
      owned there and cross-referenced.
- The W3 dadaia-workflows atom (T-47-48) documents invocability honestly: 4 operator-
  invocable workflow verbs today; `audit`/`research`/`bug_report` are governed catalog
  entries with real bodies pending verb wiring (entry 5) — it must NOT claim 7 invocable.
- Bug-store hygiene — every open bug leaves this release with an explicit state:
  - `resolved` (fixed in W1/W2/W4, evidence = task): `lifecycle-codex-review…`,
    `codex-config-emits-invalid…`, `persona-injection-skipped…`,
    `precommit-backlog-doctor-blocks-unrelated…`, `backlog-doctor-blocks-consumed-item…`,
    `prepush-gate-blocked…`, `root-whitelist-misses-nested…`, `ctx-inject-newest-bind…`,
    `specs-doctor-does-not-resolve-persisted-bound-context`,
    `backlog-doctor-bl-schema-vs-spec-doc-031…`, `workspace-doctor-root4…`,
    `agents-md-says-validate-html…`, `subagent-handoff-resolves-dadaia…` (skill-fix half;
    doctor half → entry 10), `grill-and-oq-decisions…`, `specs-bugs-jsonl-store-gitignored`,
    `backlog-doctor-default-alias-map…` (already fixed — audit evidence),
    `panel-csp-blocks-mermaid…` (already fixed — audit evidence), and
    `bugs-jsonl-migration-wrote-hollow-events` after the backfill lands.
  - `superseded`: `specs-doctor-ignores-persisted-context-bind` (by
    `…does-not-resolve-persisted-bound-context`), `reports-validate-rejects-html…` (by
    `agents-md-says-validate-html…`).
  - `deferred --reason <backlog-entry>`: `gate-self-blocks-lease-holder-own-session` →
    entry 1, `spec-doc-029-false-forgery…` → entry 1, `import-linter-contracts-red…` →
    entry 4, `panel-telemetry-sqlite-corrupts…` → entry 2,
    `context-dead-nonwritable-guard…` → entry 3, `context-dead-plain-git-push…` → entry 3,
    `memory-heading-allowlist-not-consumer-extensible` → entry 9.
  - `pytest-suite-leaves-mypy-cache…` → one isolated repro attempt; then `rejected`
    (external process) or kept open with the new evidence.
- Audit archive sweep: the 15 loose audits archived to `specs/audits/_archive/` each with a
  disposition line naming its disposing release; `20260701T135346Z-6145b869` references
  v0.1.46+v0.1.47; `20260701T201136Z-0bcd6c19` references this release.

### W6 — Ship

Full suite + `ruff` + `mypy --strict` + `specs doctor` + `backlog doctor` + `public doctor`
+ `dadaia doctor` green; qa checkpoint → commits; security APPROVE handoff keyed to each
pushed sha; push `feature/v0.1.47`; CI watched to all-green; PR; CLOSURE + memory stamps in
CLOSURE phase.

## 4. Out of scope (dispositioned, not dropped)

The deferred clusters listed in W5 — each carries a named backlog entry and the deferral
reason "deep code remediation not touching the context surface; bundling would risk the
truth release" (grill D-1).

## 5. Risks

- Constitution rewrite touches the supreme law: mitigated by WS-A acceptance greps, the
  SPEC-DOC-037 guard, and keeping every retained "must" (WS-A4 acceptance).
- Memory rewrite volume: mitigated by per-atom acceptance (doctor LINT-1/CAT-1 + targeted
  greps) and the backbone item's pre-reviewed acceptance criteria.
- ctx-inject attribution changes hook behavior for concurrent sessions: mitigated by
  fallback-to-generic-preflight (never a wrong context) and a two-session simulation test.
