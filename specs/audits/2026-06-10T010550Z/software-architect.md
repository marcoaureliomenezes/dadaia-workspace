# Software-Architect Audit — dadaia-workspace source library

> Audit: 2026-06-10T010550Z fan-out · agent: software-architect · mode: REVIEW
> Scope: dadaia_workspace/ (library), specs/ (constitution, memory, releases, all 32 bugs)
> Method: full inspection via Read/Glob/Grep. No production edits. All paths relative to
> `repos/dadaia-workspace/` unless absolute.

---

## 0. Verdict on the operator hypothesis

Hypothesis: *"great idea, weak-model architecture, bugs recur, root causes never solved,
features built on rotten foundations, slop."*

**Verdict: PARTIALLY TRUE — true for one foundation, false for the codebase at large.**

- **FALSE for the Python library layering.** core/protocols/features/infrastructure with a
  single composition root (`core/container.py` per `specs/memory/architecture.md:66`), a real
  platform seam (`core/platform.py`), a ProcessRunner port with infra adapter, and
  **enforced** import-linter contracts (`setup.cfg:16-75`) with honestly documented debt
  edges. 8/12 sampled Closed bugs were fixed at the actual root cause, with named regression
  tests. This is not weak-model slop; it is competent, layered work.
- **TRUE for the concurrency/identity foundation.** The product's keystone promise
  (constitution §0: ADDITIVE never locks; one MUTATING lease per context; bind→inject→enforce)
  has **never been implemented soundly**, and every lock-family bug since v0.1.5 (semaphore →
  persona gate → cross-context contamination → lease theft) descends from the same two
  never-fixed defects: (a) no trusted harness→gate identity/mode channel, (b) a path taxonomy
  that only works at workspace root. Each release patched the symptom layer above it; the
  rewrite from semaphore to lease **discarded an already-learned root-cause fix** (PID
  liveness). The currently-open CRITICAL (`lease-stolen-by-additive-write-from-live-session`)
  is the fourth recurrence of this family and is fully confirmed in code below.
- **TRUE for documentation/ledger fidelity.** The constitution, memory, and release ledger
  make claims the code contradicts (details §5), including after a release (v0.1.9) whose
  entire purpose was "Spec/Memory Fidelity".

**Architecture score: 6/10.** Rubric in §2.4.

---

## 1. Core-workflow record (architect-core-workflow)

- **Core problem:** determine whether recurring bugs in dadaia-workspace are random defects
  or expressions of unsolved foundational root causes.
- **Constraints:** read-only audit; evidence must be file:line; live self-hosting instance;
  no Bash available to this agent (no git archaeology — release artifacts used instead).
- **Success criteria:** every claim backed by code or spec citation; ≥8 Closed bugs verified
  in code; bug clusters mapped to named foundation defects.
- **Prior art:** the workspace's own audits (2026-06-04 dev/test/review 6.9/10; 2026-06-09
  drift audit 7.0) — both predicted the lease-theft failure ("heartbeat-vs-reclaim race",
  flagged 2026-06-04, reproduced in production 2026-06-10). The prediction-then-occurrence
  is itself evidence for the hypothesis.

---

## 2. Architecture assessment

### 2.1 What is sound

| Aspect | Evidence |
|---|---|
| Layering law enforced, not advisory | `setup.cfg:20-74` — 3 import-linter contracts (features↛infrastructure, features↛subprocess, core↛OS-primitives), run in CI |
| Platform seam | `core/platform.py` Capabilities singleton; sole `sys.platform` site (`specs/memory/architecture.md:58-60`) |
| ProcessRunner port | `core/protocols/process_runner.py` consumed by `features/specs/doctor.py:62,376-400`, `features/import_/service.py:9-27` |
| Panel layer-violation fixed for real | `features/panel/service.py:22-28,424-430` — WorkflowLauncher protocol, Popen moved to `infrastructure/workflow_launcher_adapter` |
| God module remediated | `infrastructure/public_assets.py` now 599 lines (was >2300 when bugs cited lines ~2305); helpers split into `install_helpers.py` |
| Projection pipeline converged | hash-compare overwrite `install_helpers.py:182-199`, orphan prune `:223,470-476`, staging↔projected drift check `public_assets.py:583-591` |
| Fail-open posture deliberate and documented | `gate_policy.py:151-155`, `hooks/sdd_gate.py:17-18` — a chosen trade (flow > exclusion), consistently applied |

### 2.2 What is rotten (the foundation under the locks)

The SDD gate's entire class taxonomy is computed on the **workspace-root-relative** path
(`hooks/sdd_gate.py:101` → `gate_policy.classify_path`), but **all real spec artifacts live
inside `repos/<slug>/specs/`**, where `repos/` wins first:

```
gate_policy.py:84-98
  _ADDITIVE_PREFIXES = ("specs/backlog/", "specs/bugs/", "specs/audits/", ...)   # root-only
  ...
  if p.startswith("specs/releases/") or p.startswith("repos/"):
      return PathClass.MUTATING        # ← every in-repo path, including specs/bugs|backlog|audits|memory|_archive
```

Consequences (all live today):
- In-repo bug/backlog/audit writes — promised "ADDITIVE, never blocked, never locked"
  (constitution §0 lines 69-72; `bug-registration-guardrail`; architecture.md:103) — are
  MUTATING: they **acquire or steal the per-context lease** (this very audit's report write
  classifies MUTATING).
- In-repo `specs/memory/**` is MUTATING, so the PE-only DEFINITION/CLOSURE memory phase lock
  (`gate_policy.py:137-142`) **never executes** for any actual context — RULE A is dead code
  for the paths it was written to govern.
- In-repo `specs/_archive/**` (FROZEN, "read-only") is **writable** under a lease — RULE B
  dead code likewise.

This is the precise "feature built on a stale layer" pattern: the lease (v0.1.6), the Python
hook port (v0.1.8), and the backlog-unlock (v0.1.7 rc-3) were all built on top of a
classifier whose root-relative assumption was wrong for the product's primary use case.

### 2.3 State stores — duplicated identity, no single truth

At least four runtime identity/liveness artifacts coexist:
1. `.dadaia/states/ctx_locks/<ctx>.lock.json` — lease record (session_id+heartbeat).
2. `.dadaia/sessions/runtime/<ctx>.ptr` — lease incumbent pointer (read by `lease.py:330`).
3. `.dadaia/sessions/runtime/<session_id>.ptr` — written by `hooks/ctx_inject.py:99-106`
   (a *session-keyed* ptr in the same namespace as the *context-keyed* lease ptr).
4. `.dadaia/sessions/<id>.json:last_seen_at` — heartbeat renewed by `sdd_post_gate` keyed on
   `DADAIA_SESSION_ID`, an env var harness hooks never receive (lease-stolen bug D2).

The open CRITICAL's "third identity" observation is confirmed: lock record, ctx-ptr,
session-ptr, and session-json can each name a different session for the same context.

### 2.4 Score rubric (1-10)

| Axis | Score | Basis |
|---|---|---|
| Layering & cohesion | 8 | enforced contracts, composition root, seams |
| Abstraction honesty | 7 | protocols real, DI partial (11 documented lazy-import debt edges, `setup.cfg:27-43`) |
| Concurrency/locking foundation | 3 | class taxonomy dead for real contexts; TTL-only liveness; identity fragmentation; open CRITICAL |
| Spec/code/memory fidelity | 4 | constitution & memory assert behaviors code does not have (§5 F2-F5) |
| Process ledger integrity | 4 | ACTIVE.md phase lie; release-id collisions; CLOSURE missing |
| Testability & regression discipline | 7 | named regression tests per fix; but label-deep-test class recurred (panel) |
| **Overall** | **6** | solid body, broken keystone |

---

## 3. Root-cause cluster map — all 32 bugs

Status census: 22 Closed, 1 Fixed, 3 resolved, 6 Open. Clusters:

**A. Gate/lease/lock correctness (8)** — foundation defect: *no trusted harness→gate
identity/mode/context channel + root-relative path taxonomy + write-recency-as-liveness.*
`semaphore-no-liveness-reclaim` (resolved→surface deleted),
`backlog-ownership-gate-persona-unreachable-claude-code` (Closed),
`codex-dispatched-agent-persona-not-propagated-to-sdd-gate` (Closed),
`lease-cross-context-false-positive-block` (Closed, superseded),
`gate-cross-context-lock-contamination` (Closed),
`gate-fpath-not-canonicalized-before-classifier` (Open),
`context-bind-forces-mode-choice-on-operator` (Open),
`lease-stolen-by-additive-write-from-live-session` (Open CRITICAL).
**4 generations of the same family; each fix one layer up from the cause.**

**B. Projection/install/doctor drift (6)** — foundation defect: *no desired-state
reconciliation model; install/doctor/prune semantics implemented verb-by-verb.*
`install-skips-existing-files`, `doctor-blind-to-projected-drift`,
`install-does-not-prune-orphan-projections`, `agent-skill-surface-slop`,
`session-bind-primary-residue` (partial-migration residue),
`opencode-parity-test-asserts-stale-bash-script-ref` (Open — stale test asserting the old
layer). Took three release cycles (rc-2, rc-4 ×2) to make one-way file sync correct; now
converged.

**C. Panel (7)** — foundation defect: *knowledge duplicated across call sites (URL shape ×4,
auth registries ×3) + label-deep tests that cannot fail.* `panel-memory-doc-links-broken-html`,
`panel-wikilink-slug-hardcoded`, `panel-handler-parallel-auth-registries`,
`panel-subprocess-in-features-layer`, `panel-theme-switcher-broken-ugly`,
`panel-token-file-chmod-toctou`, `panel-e2e-shallow-coverage-no-deploy-gate`. All Closed
(T-016-P0x) with deep-interaction E2E guards.

**D. Hook/context-injection & harness honesty (4)** — foundation defect: *two writers of one
config + idempotence keyed on unstable identity + capability claims ahead of implementation.*
`configure-hook-writes-malformed-duplicate-userpromptsubmit` (Fixed),
`repeated-visible-userpromptsubmit-memory-injection` (Closed),
`codex-workflow-dispatch-not-deterministically-enforced` (Closed — honesty-scoped),
`codex-agent-orchestration-mismatch` (Closed — capabilities made truthful).

**E. CLI/doctor environment assumptions (4)** — foundation defect: *tool does not model its
own canonical workspace layout (poetry-on-PATH, repo-local venv).*
`ci-preflight-raw-traceback-when-poetry-absent` (Closed),
`specs-upgrade-fails-on-preexisting-doctor-error` (Closed),
`specs-doctor-dual-error-counter-confusing-output` (Closed),
`pre-push-gate-cannot-locate-workspace-venv` (Open — the pre-push gate has **never been able
to run** in the canonical self-hosting layout; "never push red" is enforced by manual
discipline only).

**F. Duplicated hand-maintained truth (3)** — foundation defect: *one fact, N tables, no
reconciliation check until it bites.* `model-catalog-modelmap-pricing-drift-no-registry`
(Open — MODEL_MAP vs PRICING_TABLE), `constitution-persona-single-source-drift` (Closed —
lint added), `init-ignores-workspace-flag` (Closed; resolver precedence ambiguity).
(Cluster C's auth registries and URL sites are the same defect expressed in the panel.)

---

## 4. Sampled Closed/resolved bug verdicts (code-verified)

| Bug | Verdict | Evidence |
|---|---|---|
| gate-cross-context-lock-contamination | **root-cause-solved** | PATH-first slug derivation `hooks/sdd_gate.py:44-63`; survived the bash→Python port |
| install-skips-existing-files | **root-cause-solved** | hash-compare overwrite `install_helpers.py:182-199` |
| doctor-blind-to-projected-drift | **root-cause-solved** | staging↔projected `[drift]` + non-zero `public_assets.py:583-591` |
| install-does-not-prune-orphan-projections | **root-cause-solved** | prune sweeps `install_helpers.py:223,470-476` (all copy strategies) |
| panel-wikilink-slug-hardcoded | **root-cause-solved** | `build_renderer(slug)` per-slug cache `_md_render.py:139-222` (default slug retained for compat) |
| panel-subprocess-in-features-layer | **root-cause-solved** | WorkflowLauncher protocol + infra adapter `panel/service.py:22-28,424-430`; import-linter edge documented `setup.cfg:36,59` |
| panel-token-file-chmod-toctou | **root-cause-solved** | `os.open(..., O_CREAT|O_WRONLY|O_EXCL, 0o600)` `panel/auth.py:101-106` |
| repeated-visible-userpromptsubmit-memory-injection | **root-cause-solved** | sentinel guards entire injection, harness-native session key `hooks/ctx_inject.py:5-12,152-162`, `hooks/_common.py:102-116` |
| specs-upgrade-fails-on-preexisting-doctor-error | **root-cause-solved** | pre/post error-set diff `cli/commands/specs.py:202-227` |
| semaphore-no-liveness-reclaim | **symptom-patched → REGRESSED** | PID-liveness fix landed in semaphore.py (v0.1.5 rc-2), then the semaphore was deleted; the replacement lease is *explicitly* TTL-only — `lease.py:16` "Liveness is TTL-only … no PID, no os.kill". The learned root cause was discarded in the rewrite and re-manifested as the open CRITICAL lease theft |
| backlog-ownership-gate-persona-unreachable (+ codex sibling) | **symptom-patched (closure claim false in code)** | deleting the keyless persona lock was right, but the closure's "specs/backlog/** plain ADDITIVE-allow" holds only at workspace root — every in-repo backlog/bug path is MUTATING (`gate_policy.py:94`); the underlying identity-channel defect re-manifested as lease-stolen D3 |
| codex-workflow-dispatch-not-deterministically-enforced | **symptom-patched (honest scoping)** | closed as advisory preflight + documented harness limit; the identity bridge it needed was never built (resurfaced in the persona bug 2 days later) |

**Tally: 9 root-cause-solved, 3 symptom-patched (1 of them regressed into the current open CRITICAL).**

---

## 5. Findings

### [CRITICAL] F1 — Gate path taxonomy is dead for every real Spec Context
Location: `dadaia_workspace/features/spec_context/gate_policy.py:84-98`; `hooks/sdd_gate.py:101-105`
Issue: ADDITIVE/MEMORY/FROZEN prefixes match only workspace-root-relative paths; `repos/`
matches MUTATING first. All real contexts keep specs under `repos/<slug>/specs/`, so in-repo
bugs/backlog/audits acquire/steal the lease, in-repo memory bypasses the PE-phase lock, and
in-repo `_archive` is writable. Confirms open bug `lease-stolen…` D1 and **extends it**:
MEMORY and FROZEN classes are equally dead — broader than the bug as filed.
Why it matters: the product's single deterministic lock fires on the writes the law says can
never lock, and does not fire (memory/archive) where the law says it must. This produced a
live lease theft mid-CLOSURE (2026-06-10).
Trade-off if fixed: re-rooting classification at the context (`repos/<slug>/` stripped) is a
small change but touches the one fail-closed/fail-open boundary — needs the full gate
integration matrix re-run.
Recommendation: classify on the context-relative path; add matrix tests for every class ×
{workspace-root, in-repo} — v0.1.10 WS-1 covers D1; extend it to MEMORY/FROZEN explicitly.

### [CRITICAL] F2 — Liveness = write-recency; the PID-liveness lesson was thrown away
Location: `features/spec_context/lease.py:16,272-357`; `hooks/sdd_post_gate.py` (heartbeat
keyed on `DADAIA_SESSION_ID`, never present in harness env)
Issue: lease staleness is heartbeat-age only; heartbeat renews only on gate-visible
Write/Edit; auto-TAKEOVER on staleness never raises. A holder inside any >120 s Bash call
(pytest — the canonical closure activity) is indistinguishable from dead. The identical root
cause was fixed once (semaphore `_is_stale` + PID + session-file, v0.1.5 rc-2) and dropped in
the v0.1.6 lease rewrite as a documented design choice.
Why it matters: mutual exclusion silently evaporates exactly during the longest, most
critical operations; 2026-06-04 audit predicted it, 2026-06-10 production reproduced it.
Trade-off if fixed: PID liveness is platform-sensitive — but the v0.1.8 platform seam
(`has_os_kill_liveness`, non-destructive OpenProcess probe) already exists for this purpose.
Recommendation: renew heartbeat on *any* PostToolUse by the holder + consult the existing
`lock_liveness`/process-probe seam before TAKEOVER. (v0.1.10 WS-2 — correct direction.)

### [HIGH] F3 — `--mode read` and `context bind` are theater at the gate
Location: `hooks/sdd_gate.py:127` (`mode = os.environ.get("DADAIA_MODE", "IMPLEMENTATION")`)
Issue: bind only prints `export` lines; hooks run in harness env; every writer therefore
presents as an IMPLEMENTATION candidate. A read-bound session became a lease holder (live
incident). This is the surviving half of the never-built harness→gate identity channel —
the same gap that made the persona lock keyless.
Why it matters: any session can steal MUTATING authority it never asked for; the bind UX
(`context-bind-forces-mode-choice-on-operator`, Open) forces a choice that then has no effect.
Trade-off if fixed: a CLI-written, gate-readable session-mode record reuses the PROTECTED
`.dadaia/sessions/` store (already trusted); minor surface, high leverage.
Recommendation: persist bind mode in CLI-owned session state keyed by harness-native session
id; gate treats missing/READ as non-acquiring (block MUTATING instead of acquiring).

### [HIGH] F4 — Memory/constitution assert lock behavior the code never had
Location: `specs/memory/architecture.md:103` ("Gate permite incondicionalmente" for ADDITIVE)
and `:123` ("Heartbeat renovado a cada PreToolUse"); `specs/constitution.md` §0 (lines 69-72);
vs `gate_policy.py:84-98`, `lease.py` acquire-only renewal.
Issue: the documented concurrency contract is not the implemented one — and this survived
v0.1.9, a release whose sole objective was spec/memory fidelity (34 findings).
Why it matters: agents plan against memory (it is injected truth); a false "heartbeat every
PreToolUse" is exactly the assumption under which the theft window was invisible.
Trade-off if fixed: documentation-only; cost is PE time in v0.1.10 CLOSURE.
Recommendation: REJECT any v0.1.10 closure that fixes the code without rewriting
architecture.md §"Modelo de concorrência" and constitution §8 to the verified behavior.

### [HIGH] F5 — The constitution's normative vision document does not exist
Location: `specs/constitution.md:19-23` ("The normative human-readable Product Vision is
`docs/01_medium_codex.md` … agents must read it first"); `docs/` absent from the repo (Glob:
no matches).
Issue: the law's declared root document is a dangling reference (operator-local untracked
file; flagged as "dead docs refs" in the v0.2.2 backlog, still unfixed).
Why it matters: every agent instructed to consult the vision silently cannot; the
constitution's own single-source rule (§12) is violated by its own preamble.
Trade-off if fixed: commit the doc (redacted) or remove the normative pointer.
Recommendation: commit or de-normativize; add a doctor check for constitution file refs.

### [HIGH] F6 — Release ledger lies; release-id collision in the archive
Location: `specs/releases/ACTIVE.md` (`release: v0.1.9 / segment: alpha-1 / phase: SPEC`) vs
`specs/releases/v0.1.9/alpha-1/TASKS.md` (all 18 tasks `[x]`, Status Aprovado, no CLOSURE.md);
`specs/_archive/releases/v0.2.0/v0.1.9/SPEC.md` vs active `v0.1.9` (same id, different
release); mixed naming `0.1.6`/`0.1.8` vs `v0.1.7`/`v0.1.4.x`.
Issue: the phase field was never advanced through IMPLEMENTATION; v0.1.9 is implemented but
the ledger says SPEC. The v0.2.x abandonment reused version ids already present in the
archive (v0.2.0's internal milestones were named v0.1.6–v0.1.9, then real releases took the
same numbers).
Why it matters: ACTIVE.md is the gate's and every agent's source for phase (`sdd_gate.py:124`
feeds RULE A from it) — a stale phase silently changes memory-write legality; duplicate ids
make archive archaeology ambiguous, which is how lessons get lost (see F2).
Trade-off if fixed: a doctor invariant (phase vs task-marker consistency; unique release ids
across releases+archive) is cheap.
Recommendation: add both doctor checks; correct ACTIVE.md in the v0.1.9 closure.

### [MEDIUM] F7 — Identity-store fragmentation in `.dadaia/sessions/runtime/`
Location: `hooks/ctx_inject.py:99-106` writes `<session_id>.ptr`; `lease.py:330` reads
`<ctx>.ptr`; `sdd_post_gate` heartbeats `.dadaia/sessions/<id>.json`.
Issue: three artifacts, two key schemes, one directory; no module owns "who is this session".
Why it matters: this is the substrate of every identity bug in cluster A; the next lock fix
built on it will inherit the ambiguity.
Trade-off if fixed: a single session-identity module (CLI-owned, PROTECTED) consolidates;
medium effort, kills the bug family's substrate.
Recommendation: fold into v0.1.10 WS-3 design rather than patching each consumer again.

### [MEDIUM] F8 — Stale "executable specification" header claims bash is the enforced gate
Location: `gate_policy.py:1-8` ("The enforced gate is `public/scripts/sdd-spec-gate.sh`
(bash, ≤175 lines)") vs `hooks/sdd_gate.py` being the v0.1.8 enforcement entrypoint and
architecture.md:68 ("Substitui os hooks bash").
Issue: the module that calls itself the single source of truth misstates which artifact
enforces it; classic code-on-code residue from the bash→Python migration.
Recommendation: fix the docstring; delete or demote the bash gate if it is no longer wired.

### [MEDIUM] F9 — The pre-push CI gate has never worked in the canonical layout
Location: open bug `pre-push-gate-cannot-locate-workspace-venv`; `pre-push-ci-gate.sh`
probes only PATH-poetry and repo-local `.venv` — the workspace venv (`.dadaia/.venv`) is
unknown to it.
Issue: "never push red" is structurally unenforced; every push in this layout uses
`--no-verify` with manual evidence.
Recommendation: v0.1.10 WS-6 — verify it probes the workspace root venv and honors
`DADAIA_BIN`.

### [LOW] F10 — Lazy features→infrastructure fallbacks accumulate
Location: `setup.cfg:27-43` — 11 ignored edges, 4 added in v0.1.9 alone.
Issue: each "lazy ProcessRunner fallback" is tracked debt, but the list is growing, not
shrinking; the backlog item `features-import-infrastructure-direct-debt` has no release.
Recommendation: cap the list (fail CI if it grows) and schedule the container-DI cleanup.

---

## 6. Top 5 systemic root causes (ranked)

1. **No trusted harness→gate identity/mode/context channel.** The design assumed env vars
   (`DADAIA_CONTEXT/MODE/SESSION_ID/PERSONA`) that no harness propagates into hook
   processes. Spawned: persona lock-with-no-key (2 bugs), cross-context lease contamination
   (2 bugs), read-mode theater + heartbeat-key no-op (lease theft D2/D3), bind-ergonomics bug.
   Fixed piecemeal (PATH-first slug, payload session-id); mode/identity still unfixed
   (`sdd_gate.py:127`).
2. **Workspace-root-relative gate taxonomy** while all real specs live in `repos/<slug>/specs/`
   — ADDITIVE/MEMORY/FROZEN are unreachable classes for actual contexts (F1). Contradicts
   constitution §0/§8, architecture.md, and three bug closures' claims.
3. **Liveness modeled as write-recency TTL, not process liveness** — plus auto-TAKEOVER and
   fail-open, the lock self-destructs under any long-running holder task; the corrective
   lesson existed (semaphore PID fix) and was discarded in the lease rewrite (F2).
4. **Duplicated hand-maintained truth with no reconciliation check until failure** —
   MODEL_MAP/PRICING_TABLE, 3 panel auth registries, 4 memory-URL sites, 2 settings.json hook
   writers, constitution/persona facts, release-id reuse. Each instance eventually gets a
   post-hoc lint; the *pattern* (no "one fact, one place" check at authoring time) persists.
5. **Ledger/closure discipline not machine-enforced** — ACTIVE.md phase drift, missing
   CLOSURE, archive id collisions, stale normative doc pointer (F5/F6). The SDD machine
   gates writes but never validates its own state transitions, so the truth the gate reads
   (phase, release) can silently rot.

---

## 7. Review-gate verdicts (per persona §0.1)

- **Root-cause gate: REJECTED for the lock family as historically closed.** The
  `semaphore-no-liveness-reclaim` resolution and the "backlog is ADDITIVE-allow" closure
  claims do not hold in current code (F1/F2). v0.1.10's SPEC (Em revisão) names the correct
  root causes (WS-1/2/3) — it must also (a) extend D1 to MEMORY/FROZEN classes, (b) restore
  the liveness probe via the existing platform seam, (c) consolidate session identity (F7),
  or it will be the fifth symptom pass.
- **Architecture-fidelity gate: REJECTED for constitution §0/§8 + architecture.md
  concurrency sections as they stand** (F4): they describe an ADDITIVE-parallel /
  heartbeat-per-PreToolUse world the code does not implement. Closure of v0.1.10 must
  rewrite them to the verified contract.

---

*software-architect · evidence-only · no production files modified. Companion note: this
report's own Write into `repos/dadaia-workspace/specs/audits/…` is classified MUTATING by the
live gate (F1) — a self-demonstrating instance of the finding.*
