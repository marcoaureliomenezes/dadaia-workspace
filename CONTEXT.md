# dadaia-workspace

The library that scaffolds and governs a dadaia workspace: one root tree holding harness projections, spec-context trees and the deterministic gate that guards their writes. This glossary names each concept once; code, specs and reviews use these words and none of the alternatives.

## Workspace and invocation

**Workspace**:
The root tree that holds `.dadaia/`, `repos/` and every projection. Its path is the `workspace_root`.
_Avoid_: root (bare), instance root, ws dir

**Repo**:
One checked-out repository under `repos/<repo_slug>/`. Its path is the `repo_root`.
_Avoid_: project, root

**Context**:
One `specs/` tree governed by the law — the workspace's own or a repo's — registered under a `context_name`, living at `specs_dir`.
_Avoid_: spec context project, registry row, slug (for the name)

**Session**:
One harness process, identified by exactly one `session_id` — the harness's own id.
_Avoid_: sid ladder, CLI-minted session, thread id

**Bind**:
The session record that names the context a session works in, and nothing else — `dadaia context bind <ctx> [--print-env]` is one verb with no mode, release, force or reason. A context with at least one live bind is alive; a bind carries a Scope.
_Avoid_: alive flag, lease, lock, bind mode, bind release

**Presence**:
The advisory record a session leaves when it writes, surfaced to other sessions and collected by the one reaper, which never touches the writing session's own record.
_Avoid_: heartbeat, marker, sentinel

**Invocation**:
The facts resolved once per process from environment, cwd and payload: workspace, session, context, repo, specs_dir and bind. Every policy receives an Invocation; none re-derives it, and none carries a release or a phase — the gate reads no SDD artifact.
_Avoid_: resolution ladder, rung, resolve_context

## Enforcement

**Gate**:
The one PreToolUse chain (root whitelist, venv guard, SDD classifier) that decides whether a harness write proceeds. It blocks exactly three things — a new workspace-root entry, a non-venv `dadaia`/`pip`/`python -m dadaia_workspace`, and a PROTECTED or out-of-Scope write — each with one `fix:` line.
_Avoid_: hook (for the chain), guard (for the chain)

**Hook**:
A harness-invoked script (PreToolUse, PostToolUse, SessionStart) — the transport that calls the gate.
_Avoid_: gate, chokepoint

**Chokepoint**:
A git hook (pre-commit, pre-push) or CI job that validates at the Publication boundary. An installed copy byte-differing from the shipped script is `HOOKS-DRIFT-1`.
_Avoid_: hook, guard

**Publication boundary**:
The push — where a blob becomes public. This repository is public, so the full denylist scan applies to every tracked path, with no tolerated-pairs list and no path exemption; a fixture needing a secret shape composes it at runtime.
_Avoid_: release boundary, publish step, baseline (for a tolerated literal)

**Verdict**:
A security-reviewer APPROVED handoff bound to one commit sha, committed under `releases/<id>/verdicts/`, consumed once by the PR gate and deleted after merge.
_Avoid_: approval, decision (the gate's boolean), review

**Path class**:
The category a written path belongs to — ADDITIVE, MUTATING, PROTECTED, three and no fourth — and the only thing the gate classifies. `specs/memory/` is MUTATING in every phase.
_Avoid_: lane, zone, MEMORY, LAW, UNGATED, FROZEN (retired classes)

**Scope**:
The repo set one Bind owns — its context's main repo plus its associated repos. A bound session's MUTATING write under a `repos/<slug>/` outside it is the gate's one non-PROTECTED block; an unbound session, an unregistered slug and a workspace-root path are never scope-judged.
_Avoid_: ownership, lease, territory, allowlist (for the repo set)

**Stall**:
The flow cannot advance because an enforcement point (gate, chokepoint, doctor exit, CLI refusal) refuses the next action the law itself requires; every BLOCK carries one executable `fix:` line, and a BLOCK whose fix is itself blocked is a CRITICAL bug by definition (operator ruling 2026-09-12).
_Avoid_: lock (a concurrency lock — the NO-LOCKS doctrine), block (one gate verdict; a stall is its consequence on the flow)

## Projection

**Asset**:
A library-owned file under `dadaia_workspace/public/`, the source of every projection.
_Avoid_: template (except for rendered scaffolds), public file

**Projection**:
An asset rendered for one harness into a runtime tree. Install writes it; doctor compares it to the render.
_Avoid_: install target, stage copy, agentic file

**Harness**:
One of the entry AI runtimes — Claude Code, Codex, Kimi Code — each with its own projection directory.
_Avoid_: target, runtime, agent-target, tool

**Drift**:
A projection whose bytes differ from its render. The only projection fault; doctor reports it, install repairs it.
_Avoid_: parity, mismatch, stale copy

## Specs

**Canon**:
The closed set of paths a `specs/` tree may contain. Scaffold is canon rendered; doctor is canon checked.
_Avoid_: schema (for paths), layout, tree version

**Record**:
One JSONL line in a store — a bug, a backlog exit, a finding, a decision. Immutable core, write-once evidence, mutable governance fields.
_Avoid_: event, entry, row

**Histo**:
An append-only archive JSONL under an area's `_archive/`, one record per exit.
_Avoid_: archive file, ledger, log

**Histo record**:
The one shape every histo line carries — `histo-record-v1`: `{id, ts, disposition, release, reason, summary, entry}`, where `entry` is the removed live object. Each area's `disposition` is a subset of the one lowercase vocabulary `delivered resolved superseded deferred rejected`.
_Avoid_: exit record, summary record, archive event, CONSUMED (retired)

**Terminal**:
A record's final status — `delivered`, `resolved`, `superseded`, `deferred`, `rejected` — reached only through a transition that carries its evidence and stamps `closed_at`.
_Avoid_: closed, dispositioned, done

**Transition**:
The one way a record changes status; refuses incomplete input.
_Avoid_: update --set status, flip

**Release**:
The open-scope publication unit, named last-published-PyPI + 1 patch — exactly one live, growing by stacked Candidates; its state is `_RELEASE.json`, its narrative is that file's `log`. The version increments only at operator-approved deploy (ADR 0005). _Avoid_: "release" for one closed scope — that is a Candidate.

**Candidate**:
One closed-scope SDD cycle inside the live Release (grill → SPEC/PLAN/TASKS `Aprovado` → implementation → memory → closure → develop merge → promote-or-continue gate). The live Candidate's trio sits at the release root.

**rc-N**:
The archive folder of the N-th completed-but-not-shipped Candidate's trio, created by `dadaia release rc-archive`. _Avoid_: "rc" as a branch name, a fixes-only round, or a scaffolded sub-phase — the segment lane (`alpha-N`) is retired (ADR 0006).
_Avoid_: version (for the unit), sprint

**Memory**:
The current product truth under `specs/memory/`; never history.
_Avoid_: docs, notes

## Output

**Handoff**:
The machine-readable JSON completion record an agent emits under `.dadaia/handoff/`.
_Avoid_: sidecar, result file

**Report**:
The HTML rendering of a handoff, written only for a human hop.
_Avoid_: artifact (bare), page

**Doctor**:
`dadaia doctor` — the one validator and reaper over three Compliance sections (`workspace`, `specs`, `ledgers`), reporting one finding per line as `<CODE> <verdict> <message>`; `--fix` runs the reaper then the specs repairs, `--expired-only` scopes the report to the TTL lane; exit 1 on any error-class finding, each carrying one `fix:` line. `dadaia public doctor` (lib-vs-projection) is the only other one, always qualified.
_Avoid_: specs doctor, backlog doctor (both retired, not aliased), checker, linter (for doctors), audit (for doctors)

**Compliance section**:
One scored half-open group of doctor rules — `workspace` (zones, root and harness-dir entries, every ALIVE repo's top, held reaped entries, installed hook drift), `specs` (canon tree, releases, fixed law, memory) or `ledgers` (schema validation of every committed governance record). Each prints `compliance(<section>): N/M <unit> canonical (P%)`, then `compliance(total)` last.
_Avoid_: doctor area, lane, pass (for a section)

**Store**:
The module that owns one record file's reads and writes; the only parser of that file.
_Avoid_: ledger, reader, dao

**Registry**:
A name-to-identity map (contexts, servers, harnesses); it holds no behaviour.
_Avoid_: service, store, catalog (except the memory catalog)

## Doctor internals (0.5.3)

**SpecsTree**:
The parsed snapshot of shared specs facts, built fresh at the start of every doctor `check()` run; the active release is parsed once per run. Checks read the tree; fixes take paths; a snapshot never survives a mutation pass.
_Avoid_: cached doctor, tree model (bare)

**Rule registry**:
`features/specs/rules.py::RULES` — the one ordered table check order, fix dispatch and the `--fix` help derive from.
_Avoid_: check list, fix branch table

**Injection decision**:
The pure outcome `decide_injection` returns for one ctx-inject invocation (what to emit, which slug to stamp); the hook is transport.
_Avoid_: injection state machine, hook branch

**Shipped history**:
`shipped-hashes.json` — the sha256 set of every published version of a projected law file; bytes found there are provably uncustomised, so refreshing them is lossless.
_Avoid_: template hashes, drift allowlist

**Scoped law**:
A per-area `AGENTS.md` projected from `public/scaffold/<area>/` (or the repo/tests pair placed by `scoped_law.install_scoped_law`); governed by TREE-5's shipped-history discipline.
_Avoid_: sub-AGENTS, area rules file

## Workspace zones (0.4.6)

**Zone**:
One top-level `.dadaia/` directory with a `Zone(name, cls, creator, ttl_seconds, canon, purpose)` record in `core/workspace_layout.DADAIA_ZONES` — the one registry that also holds the root law, the states canon, the `specs/` canon rows and `REPO_TREE_EXCLUDED`; classes `projection state protected operator output ephemeral managed`, creators `init install runtime operator`. Every other list of canonical names is a view of it.
_Avoid_: folder, lane, path class (the gate's category — a zone is a directory record)

**Finding verdict**:
The doctor's classification of one scanned entry — `canon | operator | reaped | slop | expired | missing`; `canon`, `operator` and `reaped` count as canonical. Always written qualified.
_Avoid_: verdict (bare — the PR approval record above), status, class

**Reaped**:
An entry the reaper MOVED out of the working tree into the `reaped` zone (`.dadaia/reaped/<YYYYMMDD>/<workspace-relative-path>`), held 7 days from the move, one hold per origin per day. Slop is never deleted directly — deletion happens only when a TTL zone's entry expires.
_Avoid_: deleted, purged, quarantined (the pytest mark), trash

**Sweep**:
`features/spec_context/sweep.py` — the one traversal primitive (`walk`, `mtime`, `move`, `remove`) behind every doctor walk, under one guard: a symlink is never followed, a vanished entry is absent, a location outside the workspace is skipped, every OSError is one `skipped` action.
_Avoid_: reaper walk, gc, cleanup pass, per-call-site guard

**Finding code**:
`WS-<zone>-<verdict>` — `<zone>` is `root`, a harness dir (`claude codex kimi-code agents`), `dadaia` (the `.dadaia/` top level) or a zone name with its leading dot stripped (`cache`); the `workspace` section's code family, beside `SPEC-DOC-*`, `TREE-*`, `RELEASE-TREE-*` (specs) and `BL-SCHEMA|CONFLICT|STALE`, `LEDGER-<NAME>-SCHEMA` (ledgers).
_Avoid_: ROOT-n, EFF-n, issue code

**Instance exceptions**:
`states/instance_exceptions.txt` — one glob per line, `#` comments, deduplicated, order kept; matches at the root and inside the harness dirs. Outside the projection manifest and outside the exceptions = slop. Replaces `root_exceptions.txt`.
_Avoid_: root exceptions, allowlist, whitelist (the root whitelist is the gate's law, not the operator's globs)

## Homonyms — one canonical sense

**Scaffold**:
The specs-tree renderer (`features/specs/canon.py` scaffold half) and its output under `public/scaffold/`. The test tier is always written SCAFFOLD (an undeclared test's expiring intent) — qualify on collision.
_Avoid_: scaffold (bare) for the test tier

**Sentinel**:
The ctx-inject exactly-once file (`.dadaia/tmp/ctx-inject-fired-<session>`), carrying the last injected slug. Any other marker file is a marker, not a sentinel.
_Avoid_: marker (for this file), sentinel (for presence records or workspace detection files — say "workspace sentinel" explicitly for spec_contexts.json)

**Quarantine**:
The pytest mark that parks a flaky test outside the gating selectors, always bug-gated. A bug is never "quarantined" — it is open, or it carries a terminal disposition.
_Avoid_: quarantine for any bug state

**Context**:
The Spec Context (a registered `specs/` tree) — the workspace sense, always. The harness's context window is written "context window", ctx-inject's payload is "the injected bootstrap".
_Avoid_: context (bare) for the model's window

**Workflow**:
A GitHub Actions workflow file — the only live sense. The in-repo workflow engine is retired (v0.3.0); the SDD sequence is "the flow" (DADAIA.md §1), never "the workflow".
_Avoid_: workflow for the flow or for the retired engine
