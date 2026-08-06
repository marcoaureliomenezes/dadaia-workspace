# Full Workspace Audit — dadaia-workspace (specs/memory/constitution vs implementation)

> Auditor: claude (coordinator, project-auditor role) · Date: 2026-07-01 · Session: 0bcd6c19
> Trigger: operator request — full audit of every feature (panel, spec contexts, dadaia-workflows,
> codex/pi support, fragments, personas, distribution, gate/leases, bugs/backlog governance) plus
> architecture review and root-cause verification of the open bugs. Claude-only fan-out (9 lanes);
> no dadaia-workflows dispatched. Read-only except ADDITIVE outputs (this audit + 3 bug events).
> HEAD at audit time: `f88f73d1` (v0.1.46 closure). Active release: none.

## Live baseline (coordinator-run, this tree)

- `pytest -q -p no:cacheprovider`: **4306 passed, 17 skipped** (all opt-in live / Windows-only / LAN), 0 failed, 349 s. No cache dirs left in tree.
- `ruff format --check`: clean (746 files) · `ruff check`: clean · `mypy --strict`: clean (298 files).
- `dadaia specs doctor`: **exit 0, 0 errors, 16 warnings** (the pre-v0.1.45 8-error frozen-archive situation is genuinely resolved).
- `dadaia backlog doctor`: **exit 1 — 4 BL-SCHEMA errors → every commit into this repo is currently blocked** by the pre-commit chokepoint.
- `dadaia public doctor` (instance): **exit 1 — 1 real drift** (`scripts/lint-memory-atoms.py`: v0.1.46 source never re-staged/installed post-merge).
- `dadaia doctor` (instance): exit 0 with 5 issues (2 correct LOCK-GC, 1 real ROOT-1 stray, 1 ROOT-4 false positive, 1 advisory).
- `lint-imports`: **exit 1 — 2 of 6 contracts broken** (5 violation chains; grew from 3 since the bug was filed). Not run anywhere in CI.

## Scorecard (memory/constitution truthfulness per subsystem, 1-10)

| Subsystem | Score | One-line verdict |
|---|:---:|---|
| SDD gate / leases / chokepoints | 8 | Mechanisms byte-accurate; HIGH self-block identity hole + root-whitelist overclaim undocumented |
| Layer-2 adapters / model governance | 8.5 | Faithful; constitution §4/§8 OpenCode prose is flatly false; one dead codex flag kills live codex workers |
| Public distribution / projections | 8.5 | Counts/mechanics exact; consumer-repo AGENTS.md fan-out structurally dead; instance drift post-v0.1.46 |
| Context mgmt / workspace platform | 7.5 | Kernel faithful; doctor atom and injection-content claims drifted; `context dead` broken for any repo with commits |
| Lifecycle engine / fragments / personas | 7 | Engine spine faithful; persona injection is pipeline-verb-only (v0.1.44 flagship contract silently unmet elsewhere) |
| specs-doctor / bugs store / backlog | 6.5 | v0.1.46 code ahead of memory; owning atoms describe the retired `.md` bug world |
| Panel | 6 | Redesign claims mostly true; documents a Bearer-auth control that does not exist; kanban deletion never happened in code |
| Architecture / layering | 6 | Enforcement story false in 4 sources at once; import contracts red; cross-feature rule has no mechanism |
| **OVERALL** | **7** | Sound, green, well-documented core with a stale law band (constitution §0/§4/§8 OpenCode, panel auth, bug-store atoms) and an enforcement-claims gap (import-linter, persona injection, root-whitelist) |

Pattern: the failure mode is almost never fabrication — it is **staleness bands after big releases**
(v0.1.24 OpenCode removal never swept the constitution; v0.1.45 panel redesign half-executed its
deletion claims; v0.1.46 shipped code but not its memory atoms) and **enforcement claims wider than
the mechanism** (import-linter "runs in CI", persona "injected in every step", root-whitelist
"blocks new top-level entries", "SPEC-DOC-035/036 enforce the audit sweep").

## A. Critical / high findings

- **A-1 (HIGH, live outage)** — `codex exec` Layer-2 workers are dead: `infrastructure/codex_runtime.py:162-163` emits `--ask-for-approval never`, rejected by installed codex-cli 0.142.4 (`exec` no longer has the flag; interactive-only). Unit test `tests/unit/infrastructure/test_codex_exec_runtime.py:95-96` pins the stale argv, so CI stays green while every live codex step fails at argv parse. Root cause of open HIGH bug `lifecycle-codex-review-passes-unsupported-ask-for-approval`. Fix: drop the flag (or `-c` config override), fix the pin test, add a version-floor/live-smoke probe.
- **A-2 (HIGH, live blocker)** — All commits into this repo are blocked: pre-commit backlog gate (`cli/commands/ci.py:134-175`) runs repo-global `backlog doctor` on every commit; 4 pre-existing BL-SCHEMA unresolved-anchor errors (2 dead panel anchors on `panel-ux-overhaul` — symbols deleted by v0.1.45; 1 doc; 1 code anchor on a delivered item) freeze unrelated work. Live proof of open bugs `precommit-backlog-doctor-blocks-unrelated-commits` + `backlog-doctor-blocks-consumed-item-refactor-commit`. Fix: clear the 4 anchors AND scope the gate to staged `specs/backlog/**` paths (keep repo-global as WARN/CI).
- **A-3 (HIGH)** — Lease self-block at root (open HIGH bug `gate-self-blocks-lease-holder-own-session`, STILL-REAL): holder identity is sid-string + `.ptr` only (`features/spec_context/lease.py:579-584`); with sid skew/rotation the pid-veto blocks the holder against **its own live pid**, and the heartbeat starves on the same mis-resolved sid. Empirically reproduced (same recorded pid, different sid ⇒ `LockHeldError`). Fix: RENEW when `rec.pid == holder_pid`; prefer harness payload sid over inherited env sids; regression test.
- **A-4 (HIGH)** — Persona injection is pipeline-verb-only: role→persona resolution exists solely in `LifecyclePipeline._scope()` (`pipeline.py:400`); all five fragment workflow bodies and CLI single-step verbs build `PromptScope` without persona — `release define`/`backlog define`/single-step reviews run persona-less, contradicting the v0.1.44 contract in root AGENTS.md + architecture.md. Registered as bug `persona-injection-skipped-outside-pipeline-verb`. Fix: extract the shared fragment-gate workflow base (~1,500 duplicated lines across the 5 bodies) and inject at that one seam.
- **A-5 (HIGH)** — Import-boundary enforcement story false in four sources simultaneously (`setup.cfg:3`, `architecture.md:348`, `tech-stack.md:114`, `quality-assurance.md:52` all claim import-linter runs in the CI lint job): CI lint runs ruff only; `lint-imports` is red (2/6 contracts broken, 5 chains — 2 new since the bug was filed, including v0.1.46's `subject_registry → cli.main → infrastructure.bug_reporter → subprocess`); the "features don't import features" rule has zero contract and 8 live edges including a `workflows ↔ lifecycle` cycle. Open bug `import-linter-contracts-red-but-not-ci-enforced` confirmed on both halves and worse.
- **A-6 (HIGH, doc-safety)** — Panel memory documents a Bearer-token auth control that does not exist (`panel.md:19-20,39,48,168`, `architecture.md:53`; all auth removed 2026-06-11; mutations guarded only by loopback bind + Host allowlist; no token minted; no `loopback_bypass` kwarg; claimed startup warning string absent). Most dangerous drift class — an agent may assume mutation routes are token-gated.
- **A-7 (HIGH, structural)** — Consumer-repo AGENTS.md fan-out is structurally dead: `workspace_guardrail._consumer_repos_for_root` requires an in-repo `.dadaia/agentic/` marker that the repo-cleanliness law forbids, so no consumer repo ever refreshes; `repos/dadaia-workspace/AGENTS.md` is a stale generated copy (pre-Root-Law era) that doctor `[skip]`s — invisible drift served as law to any agent reading it.

- **A-8 (HIGH, caught live post-synthesis)** — ctx-inject cross-session contamination: the bind-driven injection selects the **newest bind-epoch marker globally** (newer than this session's sentinel) with no session affinity, so a concurrent session's bind steals another session's memory injection. Observed live during this audit: this session (bound `dadaia-workspace`, marker 16:52) received **sample-games** memory after a concurrent operator session bound sample-games at 17:15. The flagship parallel-multi-project scenario is exactly the one that breaks. Registered as bug `ctx-inject-newest-bind-epoch-steals-other-sessions-context`. Fix direction: attribute markers/bind to the session (via session record self-keyed on harness sid or the by-session index), never select by global recency; unattributable ⇒ generic preflight.

## B. Medium findings (grouped)

**Gate/lease kernel**: pid-veto bypass when `ACTIVE.md` is unreadable or post-archive (`sdd_gate.py:273` resolves `"none"` instead of veto-preserving `None` → TTL-stale record of a live holder becomes reclaimable in the closure window); root-whitelist gates only immediate-parent==root writes — nested `<root>/.opencode/agents/x.md` ALLOWs (reproduced; open bug confirmed); SPEC-DOC-029 false-forgery only symptom-fixed (live-holder UUID-vs-`sess_*` namespace compare still ERRORs — the live instance is in exactly that state now; `--specs-dir` runs still scan live ctx_locks); pre-push preflight runs the 90 s wall-clock perf test → load-dependent pushes (open bug confirmed).

**Lifecycle/governance**: model/harness governance (D-3/LAW-7/D-2) covers only the `pipeline` verb — `release define`/`backlog define` accept raw `<id>:<effort>`, freeze no snapshot, author `runtime_kind` directly; `audit`/`research`/`bug_report` marked `AVAILABLE` in the catalog but not operator-invocable (no CLI verb, no container builder); `run_implement_review_loop` drops the rejection digest (`pipeline.py:306` is literally `_ = resolved`), bypasses the runner gate, and has no CLI caller; `GRILL.md`/`OQ-DECISIONS.md` still gitignored (`.gitignore:117` re-includes omit them) despite being mandatory gate evidence.

**Panel**: kanban deletion claimed by v0.1.45 never happened in code (route+view+CSS+tests alive, zero JS consumers — orphaned endpoint); telemetry SQLite corruption bug confirmed at root — the only WAL/busy-PRAGMA connection factory (`store/schema.py:129-141`) has zero production callers, panel `_dao_factory` raw-connects one shared `check_same_thread=False` connection across ThreadingHTTPServer threads, refresh leaks unclosed write DAOs, quarantine leaves `-wal`/`-shm` siblings; memory/academy mermaid fences emit unescaped `<pre class="mermaid">` that nothing renders (silent raw text + sanitizer bypass; `<img onerror>` passes — loopback-mitigated).

**Distribution/platform**: instance projection drift (v0.1.46 `lint-memory-atoms.py` never re-installed — `public doctor` exit 1); `codex_config()` still emits invalid `approved_commands` + `[skills] paths` keys while backlog `codex-runtime-fidelity` claims that removal `delivered`; `context dead` broken twice at root for any repo with local commits (non-writable guard rejects git's 0444 objects AND runs after push → half-dead contexts; plain `git push` fails on mismatched upstream names); `dadaia doctor` ROOT-4 false-positives on `.dadaia/hooks` (library's own artifact; registered as bug); doctor atom claims SENTINEL-GC/PTR-GC are checks (fix-only in reality) and omits ROOT-1..4/LOCK-4/LOCK-5.

**specs-doctor/bugs/backlog**: owning atoms not updated at v0.1.46 closure — `specs-doctor.md` omits SPEC-DOC-022/023/033-036/SPECS-VERSION and the 034 auto-fix; `sdd-bug-backlog-governance.md` still documents `.md` frontmatter bugs and **no atom documents the JSONL store**; gate atoms lack the R-2 `_archive`-FROZEN reorder; ACTIVE.md's "SPEC-DOC-035/036 enforce the v0.1.47 sweep" is half-false (036 scans only `audits/_archive/` — the 14 loose undisposed audits produce zero doctor signal); SPEC-DOC-031's remediation text (`DELIVERED — vX.Y.Z`) is hard-rejected by BL-SCHEMA at pre-commit — following the doctor's advice blocks the commit; v0.1.46 migration wrote schema-hollow events (registered as bug).

**Constitution/memory staleness band**: constitution §0/§4/§8 still enumerate OpenCode — "five AgentRuntimeKinds", `.opencode/` root entry, OpenCode enforcement-matrix row (code enum has four; already tracked by backlog `specs-truth-realignment-constitution-memory`); keystone atom claims bind injects `constitution.md` + memory (reality: tech-stack digest + catalog tldr only); tech-stack restrictions still say PI needs `ANTHROPIC_API_KEY` and its LAW-2 list omits `kimi-2.7`; `OPENCODE_SESSION_ID` still in the documented sid chain; architecture.md: 22→**23** CLI subcommands, 5 feature packages missing (`ai_surface`, `bugs`, `chokepoints`, `reports_validation`, `workspace_clean`), internal kanban contradiction, hooks dependency diagram omits real edges (incl. `cli/commands/lock.py:12` importing private hook symbols); `agent-monitoring.md` most-stale atom (deleted tabs, Bearer fetches, wrong sqlite filename, unwired WAL); QA atom says 4 governance jobs (reality 5 — `backlog-doctor` missing); `pytest-randomly`/`hypothesis` undeclared in tech-stack.

## C. Dead code / slop inventory

Legacy `main()` in `hooks/sdd_gate.py:343` + `hooks/root_whitelist.py:93` ("kept for one release", v0.1.14 → still here); `lease.LEASE_TTL_SECONDS` re-export (zero importers); `/api/kanban` full chain + `KANBAN_CSS` + `AGENTS_CSS`; `store/schema.py:open_connection` (dangerous dead code — hides the WAL regression); `academy.js` `window.mermaid` branch; telemetry `panel.token` permission drift-check referencing deleted `auth.py`; `views/_assets.py` legacy shim; `library_workflow_catalog()` (test-only consumers); stale `core.js` router comments promising a never-shipped `workflows.js`; `ai-engineer` persona referenced by no step role (inert); 6 ADR-1 transitional TODOs (~38 releases stale); `.import_linter_cache/` untracked at repo root (should live outside per repo-cleanliness policy).

## D. Open-bug disposition table (23 open + 3 new)

| bug_id | verdict | disposition proposal |
|---|---|---|
| gate-self-blocks-lease-holder-own-session (HIGH) | STILL-REAL (A-3) | fix in remediation release |
| lifecycle-codex-review-passes-unsupported-ask-for-approval (HIGH) | STILL-REAL (A-1) | fix first |
| precommit-backlog-doctor-blocks-unrelated-commits | STILL-REAL (A-2) | fix; merge with next |
| backlog-doctor-blocks-consumed-item-refactor-commit | STILL-REAL (A-2) | merge into one "pre-commit backlog gate over-blocks" remediation |
| backlog-doctor-bl-schema-vs-spec-doc-031-… | STILL-REAL narrowed (message-text conflict only; bare `delivered` passes both) | fix 031 wording or BL-SCHEMA prefix-match |
| backlog-doctor-default-alias-map-… | FIXED-AT-ROOT (`newartifacts.py:45-52`) | append `resolved` |
| prepush-gate-blocked-by-loadsensitive-perf-test | STILL-REAL | deselect `tests/performance` in preflight |
| import-linter-contracts-red-but-not-ci-enforced | STILL-REAL, worse (A-5) | fix chains + wire CI |
| root-whitelist-misses-nested-new-toplevel-writes | STILL-REAL (reproduced) | first-path-component classification |
| spec-doc-029-false-forgery-… | FIXED-SYMPTOM-ONLY | namespace-aware coherence + `--specs-dir` isolation |
| context-dead-nonwritable-guard-… | STILL-REAL | `rmtree(onexc=chmod+retry)`; pre-check before push |
| context-dead-plain-git-push-… | STILL-REAL | explicit refspec `HEAD:<upstream>`; skip when up-to-date |
| specs-doctor-does-not-resolve-persisted-bound-context | STILL-REAL | fix `core/specs_resolver.py` fallback |
| specs-doctor-ignores-persisted-context-bind | DUPLICATE of previous | append `superseded --superseded-by` |
| subagent-handoff-resolves-dadaia-inside-repo-cwd | Python FIXED-AT-ROOT; agent-side STILL-REAL | skill root-resolution step + `repos/*/.dadaia/` doctor check |
| grill-and-oq-decisions-records-gitignored | STILL-REAL | 6 gitignore re-include lines + doctor warning |
| panel-csp-blocks-mermaid-cdn-… | FIXED-AT-ROOT | append `resolved` |
| panel-telemetry-sqlite-corrupts-… | STILL-REAL (root chain in B/Panel) | pragma'd factory everywhere + close DAOs + WAL-aware quarantine |
| agents-md-says-validate-html-reports-… | STILL-REAL (doc-side wrong) | one-line AGENTS.md fix; merge with next |
| reports-validate-rejects-html-… | DUPLICATE of previous | append `superseded` |
| codex-config-emits-invalid-approved-commands | STILL-REAL | delete dead config keys + doctor lint |
| memory-heading-allowlist-not-consumer-extensible | STILL-REAL (scaffold self-inconsistency confirmed) | workspace allowlist-extension file |
| pytest-suite-leaves-mypy-cache-in-repo-root | NEEDS-REPRO; attribution likely external (full suite left tree clean today) | one isolated repro, else `rejected` |
| **NEW** workspace-doctor-root4-false-positive-dadaia-hooks | registered this audit | add `hooks` to `_DADAIA_ALLOWED_SUBDIRS` |
| **NEW** persona-injection-skipped-outside-pipeline-verb (HIGH) | registered this audit (A-4) | shared workflow base + single injection seam |
| **NEW** bugs-jsonl-migration-wrote-hollow-events | registered this audit | backfill from `_archive` + reject empty required fields |
| **NEW** ctx-inject-newest-bind-epoch-steals-other-sessions-context (HIGH) | registered this audit (A-8, observed live) | session-attributed marker selection; no global-recency pick |

## E. Recommended remediation (routes to project-manager; one audit → one release)

Ordered by blast radius:

1. **Unblock the repo + revive codex workers** (A-1, A-2): clear the 4 BL-SCHEMA anchors; scope the pre-commit backlog gate to staged paths; drop `--ask-for-approval` from `codex exec` argv (+ pin-test fix + live-smoke seam); deselect `tests/performance` from the pre-push preflight.
2. **Lease-kernel identity hardening** (A-3 + veto bypass + F-7 dangling index): pid-based self-recognition; veto-preserving `None` on unreadable ACTIVE.md; index-remove in the `.ptr`-RENEW branch; SPEC-DOC-029 namespace-aware coherence + `--specs-dir` isolation.
3. **Make enforcement claims true** (A-5): fix the 5 red import chains (port for the policy store; break `subject_registry → cli.main`), add `lint-imports` to CI lint + `ci preflight`, add a cross-feature contract, break the `workflows ↔ lifecycle` cycle; root-whitelist first-component classification.
4. **Persona/governance uniformity** (A-4 + B/Lifecycle): shared fragment-gate workflow base with persona injection + policy-resolver routing for all run verbs; wire or demote `audit`/`research`/`bug_report` + the implement/review loop; gitignore re-includes for GRILL/OQ-DECISIONS.
5. **Panel truth + SQLite** (A-6 + B/Panel): rewrite auth sections to the no-auth reality; finish-or-revert the kanban deletion; unify SQLite through the pragma'd factory (WAL + busy_timeout, closed DAOs, WAL-aware quarantine); escape-or-render mermaid fences.
6. **Memory/constitution catch-up pass** (product-engineer, DEFINITION/CLOSURE): constitution OpenCode sweep (§0/§4/§8); v0.1.46 atoms (specs-doctor checks, JSONL bug-store atom, R-2 FROZEN rows); panel/agent-monitoring/tech-stack/QA/architecture corrections enumerated in §B; keystone-atom injection claim; re-project the instance (`public stage + install + doctor`) and make post-merge projection refresh part of the ship ritual.
7. **Disposition hygiene** (with v0.1.47's planned sweep): 3 `resolved` events (alias-map, panel-CSP, frozen-archives already has one), 2 `superseded` dedupes, backfill hollow events, disposition the now-15 loose audits (this one included), 11 backlog normalizations, add the loose-audit doctor signal ACTIVE.md already claims exists.

## F. What is verifiably healthy (keep; do not churn)

Suite/typing/lint fully green; lease CAS + by-session index + TTL/pid-veto mechanics exactly as documented; merged pre_gate order + fail-open/fail-closed split; DP-4 pre-commit chain + per-sha security-verdict push gate; v0.1.46 JSONL store contract (naming, rotation, terminal set, redaction, validate-before-write) and complete 99-file migration; backlog R1 registry/classifier/ledger/consumes chain incl. end-to-end define→close loop test; headless adapter single-sourcing with divergence tests; LAW-1/LAW-2 model governance incl. kimi-2.7 allowlist isolation and the no-`claude-*` bound; Ring-1 `scope_match` in the Claude SDK adapter; panel CSP (2 verified hashes, no CDN), PUT validation ladder, PI telemetry metadata-only invariant; projection counts and privacy checks; 5-layer test taxonomy + 15-job CI with 80% CI-only coverage.
