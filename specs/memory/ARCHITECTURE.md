---
slug: ARCHITECTURE
title: Architecture Memory
tldr: 16 measured architecture principles, then the one-decider module table and the diagrams of doctor classes, feature packages and panel view modules.
summary: Part 1 carries the ADR-gated architecture principles and the check measuring each; Part 2 names the module deciding each cross-cutting fact and carries the three diagrams.
tags: [architecture, layers, dependency-rules, agents, sdd]
---

## Part 1 — Principles

### P-01 · We keep the dependency ring: core imports nothing internal, infrastructure imports only core, no layer imports upward; a feature imports the concrete infrastructure class it alone consumes.
Measured by: `lint-imports --config setup.cfg --no-cache` — contracts `core-no-upper-layers` and `infrastructure-no-upper-layers` (zero ignored imports).
ADR: 0001 (accepted)
Rationale: the ledger shows zero adapter substitutions ever fixed a bug; the port requirement only grew the container funnel.

### P-02 · We never spawn a subprocess from a feature; process execution goes through the one infrastructure adapter, `infrastructure/subprocess_runner.py`.
Measured by: `lint-imports --config setup.cfg --no-cache` — contract `features-no-subprocess` (direct imports only, zero ignored edges).
ADR: none
Rationale: one process seam keeps execution observable, fakeable and bounded.

### P-03 · We keep `core` free of OS primitives (`fcntl`, `signal`, `subprocess`, `msvcrt`); `core/platform.py` is the sole platform seam.
Measured by: `lint-imports --config setup.cfg --no-cache` — contract `core-no-os-primitives`.
ADR: none
Rationale: a POSIX-only primitive in the bottom ring breaks every importer on Windows.

### P-04 · We make `core` the bottom ring: it imports no `features`, `infrastructure`, `cli` or `hooks`.
Measured by: `lint-imports --config setup.cfg --no-cache` — contract `core-no-upper-layers` (zero ignored imports).
ADR: none
Rationale: the ring everything imports must import nothing, or the graph has a cycle.

### P-05 · We let `infrastructure` depend on `core` only — never on `features`, `cli` or `hooks`.
Measured by: `lint-imports --config setup.cfg --no-cache` — contract `infrastructure-no-upper-layers` (zero ignored imports).
ADR: none
Rationale: an adapter that knows a use case is no longer an adapter.

### P-06 · We keep `core.kernel_tunables` a pure-constant leaf that imports no upper layer.
Measured by: `lint-imports --config setup.cfg --no-cache` — contract `kernel-tunables-is-a-leaf`.
ADR: none
Rationale: hooks import it on the write hot path; one upper edge drags in the composition graph.

### P-07 · We keep features mutually independent: they compose through the container, never through sibling imports; a helper two features need lives in each.
Measured by: `lint-imports --config setup.cfg --no-cache` — contract `features-no-cross-feature`, whose `modules =` list is asserted equal to the on-disk `features/*/__init__.py` package set by `pytest tests/contract/test_import_linter_ignore_cap.py`.
ADR: none
Rationale: a hand-kept `modules =` list hid three real sibling edges from the check.

### P-08 · We keep a Protocol in `core/protocols` only where two production adapters exist; `container.py` composes platform seams and shared collaborators, nothing single-consumer.
Measured by: `pytest tests/contract/test_protocols_have_two_adapters.py`.
ADR: 0001 (accepted)
Rationale: a Protocol with one implementer is interface text that hides a direct dependency.

### P-09 · We resolve the whole Invocation — workspace root, session, context, specs dir, the session's Bind — once per process in `core.invocation.resolve`, imported directly only by `cli._specs_resolution`, `container` and `hooks`.
Measured by: `lint-imports --config setup.cfg --no-cache` — contract `bind-resolution-seam-is-a-single-home` (zero ignored imports, none ever accepted); `pytest tests/unit/core/test_invocation.py`.
ADR: 0003 (accepted)
Rationale: every context bug came from a second resolution path answering differently.

### P-10 · We cap every suppressed layering edge and ratchet the cap only downward; an edge is added with its reason and the cap moved in the same commit.
Measured by: `pytest tests/contract/test_import_linter_ignore_cap.py` — the test module is the cap's one numeric home.
ADR: none
Rationale: a pinned exception list turns every new suppression into a reviewable diff.

### P-11 · We keep `core` file-I/O pure outside an authorized set of eight modules; new file I/O enters `core` only by joining that set on purpose.
Measured by: `pytest tests/contract/test_core_file_io_purity.py` (AST walk; every authorized stem must exist).
ADR: none
Rationale: joining the set is legal; arriving there unnoticed is not.

### P-12 · We never import the composition root from a hook; hooks reach the resolution authority directly because they are one-shot processes on the write hot path.
Measured by: `pytest tests/contract/test_hook_import_surface.py` (six hook modules plus the executed gate path, with `container` absent from `sys.modules`).
ADR: none
Rationale: the composition graph costs seconds of import time per gated tool call.

### P-13 · We keep the architecture diagrams derived from live code: every diagrammed class, view module and feature package is introspected against the live tree.
Measured by: `dadaia doctor` — `specs`-section rule `MEM-DRIFT-1` (`features/specs/doctor_memory.py`), one WARNING per package the map and the live tree disagree on.
ADR: none
Rationale: a diagram nobody checks is the first artifact to lie.

### P-14 · We keep the release-state reader pure: `core/release_state.py` parses and serializes already-read text and performs no file I/O.
Measured by: `pytest tests/contract/test_release_state_read_only.py`.
ADR: 0004 (accepted)
Rationale: a reader that can write is a reader that can rewrite history.

### P-15 · We close the release-state envelope: `release-state-v1` carries `additionalProperties: false` at every level, a closed log-entry shape, and no harness `session_id`.
Measured by: `pytest tests/contract/test_release_state_schema.py`.
ADR: 0004 (accepted)
Rationale: an open envelope accumulates fields until no consumer can fold it.

### P-17 · We map every core skill and every scoped `AGENTS.md` source to exactly one `DADAIA.md` section, every section to at least one owner, with content hashes re-recorded only by review.
Measured by: `pytest tests/contract/test_behavior_map.py` (bijection, hash tuples, citation check, invocation grants).
ADR: none
Rationale: law that no asset owns is law nobody applies.

## Part 2 — Implementation

### One decider per fact

| Fact | The module that decides it |
|---|---|
| workspace root, session, context, the session's Bind | `core/invocation.py` — `resolve() -> Invocation`, over rungs 0 (explicit/`target_path`) … 3 (repo of the cwd); `Bind(context_name, repos)` with `all_repos()` (main + associated) is the scope, resolved from `DADAIA_CONTEXT` then the live session record, never the cwd |
| the gate's three blocks and three path classes | `hooks/root_whitelist.py` (a new root entry), `hooks/venv_guard.py` (one rule: venv-rooting), `features/spec_context/gate_policy.py` (`classify_path` → ADDITIVE/MUTATING/PROTECTED; `evaluate` → PROTECTED or out-of-scope BLOCK, else ALLOW with presence); `hooks/sdd_gate.py` resolves the Invocation once and passes the Bind and target owner as plain data — no phase, no mode, no `_RELEASE.json` read |
| the BLOCK envelope | one `fix: <command>` line per refusal, every enforcement point; `tests/contract/test_every_block_carries_a_fix.py` is the interface (68 refusals, each fed back through `pre_gate.evaluate_payload` as ALLOW) |
| session record schema, read, liveness and reaping | `core/session_store.py` — `new_binding_record`/`is_live`/`live_session`/`reap_stale`; `core/record_liveness.py` holds the raw TTL predicate |
| presence liveness and reaping | `features/spec_context/presence.py` — `gc()` is the only reaper of records, markers, sentinels and emptied directories |
| every canonical name — the root law, `.dadaia/` zones (class, creator, TTL, canon; `reaped` at 7 days), the `states/` canon, the `specs/` canon rows, the repo-tree exclusion set, the installed git hooks | `core/workspace_layout.py` — `ROOT_ALLOWED_DIRS`/`ROOT_ALLOWED_FILES`, `INSTANCE_EXCEPTIONS`, `DADAIA_ZONES`, `STATES_CANON`, `SPECS_CANON` (`CanonEntry` shape → matcher, `CANON_ROOT_MEMBERS` derived), `REPO_TREE_EXCLUDED` (= `.dadaia` + `REPO_TREE_ARTIFACTS`), `INSTALLED_GIT_HOOKS`; init, `dadaia doctor`, the gate's ADDITIVE prefixes, the root-whitelist hook, `privacy_check`, `ci install-hook`, export and the stage renderer (`<!-- zones\|canon\|root\|repo-excluded\|specs-canon -->` into `.dadaia/AGENTS.md` and DADAIA §5.1/§5.3/§6.2) are derived views; a literal of three or more canonical names outside this module fails `tests/contract/test_zone_registry.py` |
| what a `specs/` tree may contain | `core/workspace_layout.SPECS_CANON` rows; `features/specs/canon.py` is the renderer (`scaffold`, `release_new`) and checker (`check_tree`) over them |
| whether a projection is current | `infrastructure/projection.py`'s `ProjectionRule` plus `projection_rules()`; install writes and doctor compares the same table |
| which harness a projection targets | `HarnessProjection` in `infrastructure/projection_rules.py`, with three production adapters — Claude Code, Codex, Kimi Code |
| a bug record's status, `closed_at`, lineage and shape | `core/models/bugs.py` transition methods, every terminal one ending in `_reach_terminal` (stamps `closed_at` once); `resolve` is the one `caused_by` writer; `from_dict`/`to_dict` are the one authority on which keys a record has (the seven git-derived provenance keys are retired — no stored fact a resolver re-derives, ADR 0011); `infrastructure/jsonl_record_store.py::JsonlRecordStore.scan()` is the one ledger parser, yielding `MalformedLine` for a bad row |
| the `surface` enum's feature arm | `features/specs/schemas.py` appends the `features/<name>/` packages on disk at load (`x-enum-append: feature-packages`); the schema lists only the six non-feature layers and `unknown` |
| the histo record shape, the terminal vocabulary, which disposition needs which evidence | `core/models/histo.py` — `HistoRecord`, `TERMINAL_DISPOSITIONS`, the per-ledger subsets (`FINDINGS_DISPOSITIONS` serves findings and the audits histo) and `REQUIRED_EVIDENCE` (`release` vs `reason` per disposition), read by `backlog exit`, `audit disposition` and the doctor alike; `features/specs/ledgers.py::LEDGERS` is the one table of validated ledgers, each row naming its `events_ledger` or none |
| a governance event and its record hash | `core/models/telemetry.py` — `GovernanceEvent {event_id, ts, session_id, context, verb, ledger, record_id, record_hash}` and `record_hash()` (sha256 of the canonical JSONL line), beside each other so writer and reader hash identically; `cli/_governance_event.py::record_governance_event` is the one writer every verb calls after its record write, swallowing a store that cannot open; `features/telemetry/store.py` migration 7 holds the table |
| the context a governance event is stamped with | `cli/_specs_resolution.py::resolve_event_context_for_cli` — from the `specs/` tree the verb resolved, never the session's env binding; the doctor filters its baseline with the same function, so a verb-written record is never reported as a hand edit by the tree that owns it |
| whether a verb-owned record was hand-edited | `features/specs/ledgers.py` (`LEDGER-<NAME>-HANDEDIT`, latest event hash vs committed record, baseline = the store's first event) and `features/specs/release_tree.py` (`RELEASE-TREE-HANDEDIT`, live phase/milestones vs the latest `release` event); `cli/commands/doctor.py` reads `latest_governance_events()` once and passes plain data — neither feature imports `features/telemetry` |
| an audit finding's disposition and the audit archive | `features/specs/audit.py` — `disposition_finding` (the first caller of `FindingRecord.apply_governance_update`) and `close_audit` (all-or-nothing, histo append last); `_audit_dir` confines every `<dir>` argument to `specs/audits/` |
| the release phase transition and its milestone | `features/specs/candidate.py` — `release phase IMPLEMENTATION` stamps `defined`, `release phase CLOSURE` stamps `implemented {sha, rc + 1, ts}`; `archive` validates `CLOSURE` only, so no milestone can be set by hand for it to hang on |
| the venv `dadaia` spelling in every `fix:` line | `core/kernel_tunables.DADAIA_BIN` — one literal, imported by every verb and rule that renders a fix |
| a packaged JSON schema | `features/specs/schemas.py::validator_for` — one loader, one cache, addressed as `<dir>/<id>` under `public/schemas/` |
| a handoff's version, artifact and validity | `core/handoff_index.py` — `HandoffIndex`/`Handoff`, the stdlib schema walker internal to it |
| the git publication boundary | `features/chokepoints/{branch_policy,denylist_scan,pre_commit,push_gate,verdict}.py`; `covering_verdict()` is the single verdict reader, `live_verdict_shas()` the one stale-verdict rule |
| the telemetry database connection | `features/telemetry/store.py`'s `TelemetryStore`, owning open/migrate/`integrity_check`/`quarantine` |
| a YAML frontmatter block | `core/frontmatter.py` |
| the release phase vocabulary | `core/release_state.py` — `PHASES`; the schema enum, the doctor and the release verbs import it, the gate reads none |
| the reaper's filesystem acts — walk, mtime, move, remove | `features/spec_context/sweep.py` — one primitive, one guard (symlink never followed, vanished = absent, outside the workspace = skipped, `OSError` = one `skipped` action, cross-device move = copy + remove); `DoctorService` classifies over `walk()` and dispatches `move()`/`remove()`; `doctor.reap()` is the container-free lane the PostToolUse throttle and SessionStart run |
| the release-id shape | `core/specs_version.py` — `RELEASE_SEMVER_RE` with `RELEASE_ID_FRAGMENT` derived for path regexes; `is_release_semver` is the mint predicate |
| memory-canon shape facts | `features/specs/memory_canon.py` — the top-level file tuple (a slug is its filename stem, no alias table), forbidden-heading matcher, wikilink grammar, fixed-section lookup |
| fail-soft registry reads | `core/invocation.py` — `alive_context_slugs` + the name↔slug maps; `JsonContextStore` stays the schema-gated CRUD |
| first parent of a sha | `infrastructure/git_objects.py::GitSubprocessObjectReader.first_parent` |
| the ctx-inject decision | `features/spec_context/injection_policy.py::decide_injection` — pure over plain values; the hook is transport |
| the doctor rule record, section scoring, the total line | `core/doctor_rules.py` — `Rule`, `SectionFinding`, `run_section`, `merge_sections`, `total_line`; `cli/commands/doctor.py` is the one composition point of the `workspace`/`specs`/`ledgers` sections |
| specs-rule order, fix dispatch, --fix help | `features/specs/rules.py::RULES` — one ordered registry, three derived projections |
| conformance of every `_RELEASE.json`, live or archived | `features/specs/release_tree.py::validate_release_tree` — the doctor, `rc-archive` and `release archive` all call it |
| shared specs facts per doctor run | `features/specs/specs_tree.py::SpecsTree` — fresh per check(), active release parsed once |

- `container.py` is composition wiring only, contract-tested so every definition keeps a production consumer (no orphaned factories); the panel's 15-route composition lives with its single consumer in `cli/commands/panel_composition.py`; a single-consumer adapter is imported directly by its feature and never passes through the container (ADR 0001).
- `core/protocols/` holds six Protocols: three two-adapter OS seams (`FilePermissionSetter`, `ShutdownHandler`, `TelemetryRefreshLock`) and three panel cross-feature seams whose implementer lives under `features/` (`AgentsProvider`, `ContextProjectProvider`, `ServerRegistryProvider`); every other adapter is imported by its one consumer (the consumer-less `ProcessAncestry` chain was deleted at 0.5.3).
- `setup.cfg` carries seven import-linter contracts; `features-no-infrastructure` and `cli-no-infrastructure` were deleted by ADR 0001, `features-no-subprocess` is direct-imports-only with no suppressed edge, and the two surviving suppressed edges (`reconcile.service` -> `capabilities`, `reconcile.service` -> `migrate.state_v2`) both sit under `features-no-cross-feature`.
- `features/migrate` stamps `specs_pattern_version: 6` or refuses, instructing a tree below v6 to upgrade to 0.4.x first — no in-wheel pre-v6 lineage.
- Hooks import `core.invocation` directly and build the `Invocation` once per process; they never import `container` (P-12); the PostToolUse hook `sdd_post_gate` renews presence, touches `last_seen_at` and runs `doctor.reap(own_session_id=…)` on one throttle (the reaper owns `presence.gc`) — it writes nothing else.

### `features/specs/doctor` — SpecsDoctor coordinator + validator siblings

```mermaid
classDiagram
    class SpecsDoctor
    class StructuralValidator
    class MemoryValidator
    class ReleaseValidator
    class ClosureAuditValidator
    class GovernanceValidator
    class CoherenceValidator
    SpecsDoctor --> StructuralValidator : owns ORDER
    SpecsDoctor --> MemoryValidator : owns ORDER
    SpecsDoctor --> ReleaseValidator : owns ORDER
    SpecsDoctor --> ClosureAuditValidator : owns ORDER
    SpecsDoctor --> GovernanceValidator : owns ORDER
    SpecsDoctor --> CoherenceValidator : owns ORDER
    note for MemoryValidator "takes the specs dir; runs the memory lint in-process; owns CAT-1, LINT-1 and MEM-DRIFT-1"
    note for GovernanceValidator "sole features.backlog.document import; reads BUGS.jsonl only through the injected bug store"
    note for SpecsDoctor "iterates rules.RULES over a fresh SpecsTree per check(); fix dispatch and --fix help derive from the same registry; takes bug_store_factory; imports neither spec_context nor infrastructure"
```

### `dadaia_workspace/features` — package map (19 packages)

```mermaid
flowchart TB
    subgraph features["dadaia_workspace/features"]
      pkgs["agents · backlog · bugs · capabilities · certification · chokepoints · ci_preflight · export · import_ · migrate · panel · public · reconcile · repos · server_registry · spec_context · specs · telemetry · workspace"]
    end
    container["container.py"] --> features
    features --> core["core"]
```

### `features/panel/views` — per-domain API view modules

```mermaid
classDiagram
    container : build_panel_views()
    api_servers : render_api_servers()
    api_contexts : render_api_contexts()
    api_agents : render_api_agents_canonical()
    api_agents : render_api_agent_prompt()
    api_agents : render_api_agent_sessions()
    agent_policy : render_api_agent_model_policy()
    agent_policy : render_api_agent_model_templates()
    api_sessions : render_api_sessions()
    api_health : render_health()
    note "no api.py barrel — container named-imports each render_api_* from its own module; each view imports only features.panel.service and core.models; handler._ROUTES is the one (method, pattern, view_name) table and a route absent from it cannot exist"
```

<!-- dadaia:fixed slop-code -->
### Slop — code (fixed)
- A comment explains a non-obvious why; the what, the history and any spec, task, ADR or version id live in git and the ledgers.
- A docstring states the contract in at most 3 lines; bug history lives in `BUGS.jsonl`.
- Code is born with a real caller in the same change; without a caller it does not exist.
- A fix replaces the old path; it never wraps it and never opens a second path.
- A `core/protocols` port exists only with two production adapters; a parameter exists only when it is read.
- Detection: `dd-code-review` SLOP.md S1, S2, S4, S5; measured by ratchet V32 and `test_protocols_have_two_adapters`.
<!-- /dadaia:fixed slop-code -->
