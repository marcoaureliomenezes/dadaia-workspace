---
name: verification-audit-architecture-v0110
date: 2026-06-10T140553Z
auditor: software-architect
scope: dadaia_workspace/ source library @ feature/v0.1.10 (post-remediation) — module architecture, layering enforcement, side-effects, dead/stale/slop code, root-cause verification of original audit (2026-06-10T010550Z) findings
mode: ADVERSARIAL VERIFICATION (independent; prior audits treated as claims, not evidence)
---

# Verification Audit — Architecture Lane — v0.1.10

> Method: full source inspection (Read/Glob/Grep). Import-linter contracts read in full
> and spot-checked against actual imports. Kernel rewrite (gate_policy / lease /
> session_identity / lock_liveness / hooks package) read line-by-line. No Bash available
> to this agent (read-only inspection; no git archaeology — code + ledger artifacts used).
> No production file modified.

## Core-workflow record

- **Core problem:** determine whether v0.1.10's claimed architectural remediation is
  structurally real (root-cause fixes in code) or self-certified patching.
- **Constraints:** read-only; evidence must be file:line; prior audits assumed possibly wrong.
- **Success criteria:** every original finding re-verified against current code; new
  defects hunted independently (dead code, side effects, broken invariants).
- **Prior art:** original audit 2026-06-10T010550Z (6/10), re-audit 052944Z (9.0) — both
  treated as hypotheses only.

---

## 1. Dependency graph & layering

### 1.1 Real dependency graph (verified by import grep, not by docs)

```
cli/  ──────────────► features/* , container, core            (entrypoint, unconstrained)
hooks/ ─────────────► features/spec_context, core, (lazy) infrastructure.process_probe_adapter
container.py ───────► features/* + infrastructure/*           (sole composition root — verified)
features/* ─────────► core/, core/protocols/                  (12 documented ignore edges → infrastructure)
infrastructure/* ───► core/, stdlib OS primitives             (no imports of features/cli/hooks — verified)
core/ ──────────────► stdlib only                             (zero imports of upper layers — verified;
                                                                core/platform.py sole sys.platform site)
```

Verified facts:
- `core/` contains **zero** imports of features/infrastructure/cli/hooks (grep: only
  docstring mentions in `core/protocols/*.py`).
- `infrastructure/` contains **zero** imports of features/cli; hook module names appear
  only as projected command strings (`runtime_config.py:70-108`, `codex_doctor.py:263-266`).
- `container.py` is a genuine composition root (all concrete adapters bound there;
  platform-conditional adapters behind `PLATFORM` capability flags, lazy-imported —
  `container.py:73-147`).
- One cross-feature import exists: `features/public/model_resolution.py:38` →
  `features.telemetry.pricing.PRICING_TABLE`. Data-only, documented (R8b anti-drift
  check), benign — but unbanned by any contract (see A3).

### 1.2 Import-linter contracts (setup.cfg — not pyproject)

Three contracts (`setup.cfg:24-89`): `features-no-infrastructure` (12 ignore edges),
`features-no-subprocess` (5 ignore edges), `core-no-os-primitives` (0 ignores). Spot-check
of actual imports found **no undeclared violation**: every features→infrastructure import
in the tree corresponds to a documented `ignore_imports` edge (transitional lock/telemetry
adapter selection `locking.py:74-100`, `telemetry/service.py:58-60`; markdown/launcher
stores; 4 lazy ProcessRunner fallbacks; the v0.1.10 model-resolution data re-export).

**Cap = 17, and it is a hard ratchet, not a comment.**
`tests/contract/test_import_linter_ignore_cap.py` pins the cap with **exact equality**
(`:87-99` — a removed edge that doesn't lower the cap FAILS), caps growth (`:73-84`), and
rejects any non-`features →` edge smuggled into the list (`:102-118`). Honest mechanism.
However: the count grew 11 → 17 across v0.1.9/v0.1.10 and the DI cleanup that would shrink
it (`features-import-infrastructure-direct-debt`) has no scheduled release. The cap is a
**well-built fence around a debt pile that is not shrinking** (finding A4).

### 1.3 Kernel verification (the v0.1.10 rewrite)

- **Path taxonomy re-rooted at the context.** `gate_policy.py:150-193` —
  `repos/<slug>/<rest>` is classified by `<rest>` with the same ordered `specs/` rules as
  root; unmatched in-repo remainder ⇒ MUTATING, **never** UNGATED (`:179-180`). In-repo
  `specs/bugs|backlog|audits` = ADDITIVE, `specs/memory` = MEMORY (phase rule now live for
  real contexts, `:254-260`), `specs/_archive` = FROZEN. Phase is read from the **context's
  own** `releases/ACTIVE.md` (`hooks/sdd_gate.py:264-267`). Original F1 structurally dead — fixed.
- **Liveness = TTL floor + PID veto.** `core/lock_liveness.py:111-134` — probe consulted
  only on the TTL-stale branch (can never *create* staleness); dead/absent pid ⇒ plain TTL
  verdict; probe exception ⇒ TTL fallback. `lease.acquire` BLOCKs (never takes over) a
  TTL-expired-but-pid-alive foreign holder (`lease.py:387-402`). Probe injected from the
  hook layer (`hooks/sdd_gate.py:39-62`), so `features/` never imports the adapter — no new
  ignore edge. Platform-seamed (`has_os_kill_liveness`).
- **Long-lived holder pid.** `hooks/sdd_gate.py:65-96` — payload pid keys first, else
  `os.getppid()` (harness process), explicitly never the ephemeral hook child's own pid
  (the rc-2 "ephemeral-pid" fix). Residual assumption documented in A7.
- **Heartbeat actually renews.** `hooks/sdd_post_gate.py` — the old
  `DADAIA_SESSION_ID`-env no-op guard is gone; sid resolves from harness-native env/stdin
  (`_common.resolve_session_id:102-116`); renewal targets **the leases this sid actually
  holds** by scanning lock records (`:72-106`) — never `DADAIA_CONTEXT`→first-ALIVE (the
  contamination vector). Claude PostToolUse matcher is explicit match-all `"*"`
  (`runtime_config.py:56-99`), PreToolUse gates scoped to write tools.
- **Renew is CAS-atomic.** `lease.renew_heartbeat` runs read→verify→write inside the same
  O_EXCL sentinel CAS as acquire (`lease.py:411-458`) — the historical
  heartbeat-vs-takeover interleave is closed. Holder-safe renewal past TTL (`:377-385`).
- **Mode is no longer theater.** Resolution chain `hooks/sdd_gate.py:131-179`: `DADAIA_MODE`
  env → self-keyed CLI session record → context-incumbent pointer (refreshed by
  `cli/commands/context.py:399 set_incumbent`) with an anti-downgrade guard that ignores a
  stale read-bind when a **live** lease holder diverges (`_incumbent_is_stale:182-205`,
  using the same canonical liveness predicate) → IMPLEMENTATION default. READ-resolved
  sessions are non-acquiring: blocked **before** any lease call (`gate_policy.py:262-267`).
- **Single acquisition point.** Only `gate_policy.evaluate` → `lease.acquire` writes the
  record via tool-gated paths; PROTECTED `.dadaia/sessions/` is the sole fail-CLOSED class,
  evaluated first (`gate_policy.py:242-246`).

Layering verdict: **the keystone the original audit called rotten has been rebuilt at the
root cause, with the policy/mechanism split (gate_policy = policy, lease = mechanism,
lock_liveness = pure predicate, session_identity = identity store, hooks = thin adapters)
clean enough to draw the UML directly from the imports.**

---

## 2. Encapsulation & side-effects

- **No module-level mutable global state found** (regex sweep for top-level `= {}`/`= []`:
  zero hits in `dadaia_workspace/`).
- **Import-time work:** `core/platform.py` builds the `PLATFORM` Capabilities singleton at
  import — pure computation, documented as the sole `sys.platform` site; acceptable seam.
  `lease.py:104-107` has an import-time assert on a test seam — trivial, guarded. No
  module-level file I/O, env mutation, or directory creation found in the inspected kernel,
  hooks, container, or CLI wiring.
- **Hooks are thin and uniform:** all five entrypoints delegate to `_common` for stdin/JSON/
  envelope/session-id; fail-open posture is consistent and per-line justified; PROTECTED is
  the one fail-closed branch. `root_whitelist.py` is 100-odd lines of policy with the
  operator-exception file — clean.
- **Identity store encapsulation:** `session_identity.py` is the declared single owner of
  both `.ptr` namespaces + session records; `lease.py:163-184` routes pointer I/O through
  it; `ctx_inject.py:100-107` and `sdd_post_gate.py:109-128` likewise; the workspace doctor
  consumes `iter_ptr_files`/`read_session` (`spec_context/doctor.py:546,576`). Ownership
  consolidation (F7) is real — with the corpses noted in A2.

---

## 3. Dead / stale / slop inventory

### A1 [HIGH] — SPEC-DOC-029 "lease↔session coherence backstop" is dead on arrival
Location: `features/specs/doctor.py:1167-1211`; `features/spec_context/lease.py:151`;
`infrastructure/file_lock_posix.py:113-117`; `tests/unit/features/specs/test_doctor_ledger_invariants.py:375`
Issue: the check globs `locks_dir.glob("*.lock")` (`doctor.py:1188`), but lease records are
written as `<ctx>.lock.json` (`lease.py:151`) — never matched by `*.lock`. The only real
`*.lock` files in that directory are the fcntl git-op locks (`locking.py:55`), whose content
is a bare pid string (`file_lock_posix.py:117`) — `json.loads` yields an int, the
`isinstance(rec, dict)` guard skips it. **The invariant can never fire on any artifact
production actually writes.** Its unit test passes only because the fixture fabricates a
`<ctx>.lock` JSON file that no production code path ever creates — the exact
"label-deep test that cannot fail" defect class the original audit documented for the panel
(cluster C), recurring inside the remediation release itself (T-010-14/R6b is a claimed
v0.1.10 deliverable, `doctor.py:446-451`).
Compounding: `session_identity.coherence()` (`session_identity.py:260-302`) is the designed
API for exactly this check — its docstring says "the doctor consumes it as a backstop"
(`:23-24`) — yet it has **zero production callers**; the specs doctor reimplemented a
divergent (and broken) copy instead. One fact, two implementations, the live one wrong.
Why it matters: this is the D-2 backstop — the *only* after-the-fact coverage for
Bash-tool writes that bypass the gate. A dead backstop is a false safety claim baked into
the remediation's own evidence.
Trade-off if fixed: small — read `<ctx>.lock.json` via `lease.read_record` (or call
`session_identity.coherence` with the lock holder), and rewrite the test against the real
artifact name. No design change.
Recommendation: fix the glob/consumer to the real record, delete the duplicate logic in
favor of `session_identity.coherence`, and add one integration test that creates the record
through `lease.acquire` (not by hand).

### A2 [MEDIUM] — WS-R3 consolidation left vocabulary corpses in `session_identity`
Location: `session_identity.py:159-160` (`incumbent` read-alias — no callers),
`:168-174` (`read_session_ptr` — no production callers), `:228-230` (`record_for` — no
callers), `:260-302` (`coherence` — no production callers, see A1), `:311-320`
(`gc_orphan_session_ptr` — no callers); `ctx_inject.py:100-107` (session-keyed
`<sid>.ptr` is **write-only data**: written every session start, read by nothing; the
workspace doctor only GC-sweeps the namespace).
Issue: PLAN-vocabulary aliases and a "preserved verbatim" artifact survived the rewrite as
exported API with no consumers. Rewrites leave corpses; these are them.
Why it matters: dead exported API misleads the next maintainer into believing these paths
are load-bearing; the write-only `.ptr` is state that exists only to be garbage-collected.
Recommendation: delete the unused aliases and `read_session_ptr`; either wire `coherence`
(A1) or delete it; decide whether the session-keyed ptr has a future reader — if not,
stop writing it.

### A3 [MEDIUM] — Contract surface is one-directional
Location: `setup.cfg:24-89`
Issue: only features→infrastructure, features→subprocess, and core→OS-primitives are
enforced. Not enforced: core↛{features,infrastructure,cli} (core is clean today, by
discipline only), infrastructure↛features (clean today), features↛features
(one live edge: `model_resolution.py:38`), and cli/hooks are wholly unconstrained.
Why it matters: the layers that are clean are clean by discipline, and discipline is what
rotted last time. A single import-linter `layers` contract (cli | hooks → features →
core ← infrastructure) would freeze the whole verified graph at near-zero cost.
Recommendation: add a `layers`-type contract; declare the one cross-feature data edge.

### A4 [MEDIUM] — Suppressed-edge debt capped but growing; stale TODO anchors
Location: `setup.cfg:35-57` (17 edges); `locking.py:72,76,90,94` ("once PLATFORM is stable
in T-018-05"), `telemetry/service.py:58-60` ("once WS-1 lands" — ambiguous: 0.1.8's WS-1,
not 0.1.10's WS-1).
Issue: 11 → 17 edges across two releases; the DI cleanup backlog item has no release; the
TODO comments anchor to task ids of shipped releases, so their trigger condition is
already-true-and-ignored or unintelligible.
Recommendation: schedule the container-DI cleanup; re-anchor or resolve the four TODOs.

### A5 [LOW] — Controlled corpse: `server_registry/dashboard.py`
Location: `features/server_registry/dashboard.py:1`; `cli/commands/server.py:297-328`
Issue: module self-declares DEPRECATED "removed in a future release" and remains wired to
a deprecated CLI command. Removal has been "future" across multiple releases.
Recommendation: name the removal release or delete now (panel supersedes it).

### A6 [LOW] — Two lock namespaces share one directory with confusable names
Location: `.dadaia/states/ctx_locks/` — `<slug>.lock` (fcntl, `locking.py:55`) vs
`<ctx>.lock.json` (lease, `lease.py:151`) vs `<ctx>.lock.sentinel`.
Issue: this naming adjacency is precisely what let A1's `*.lock` glob look plausible and
pass review. Same-directory, near-same-name artifacts with different owners is an
encapsulation smell with a demonstrated bug yield.
Recommendation: separate subdirectories or unmistakable names (`<ctx>.lease.json`).

### A7 [LOW] — Holder-pid liveness assumes no persistent shell interposition
Location: `hooks/sdd_gate.py:65-96`
Issue: `os.getppid()` names the harness only if the harness spawns the hook directly or
via an exec-optimizing `sh -c`. The forward-compatible payload keys (`harness_pid`…) are
sent by no current harness. If any harness/platform interposes a persistent wrapper, the
recorded pid dies with the hook and the no-steal veto silently degrades to TTL-only.
The PostToolUse heartbeat covers the common case regardless.
Recommendation: per-harness live verification (an e2e exists — `tests/e2e/test_two_actor_lease.py`);
consider stamping and probing the *oldest live ancestor* on platforms with `/proc`.

### A8 [LOW] — Temporal naming slop became permanent API
Location: `features/reports_next/`, `cli/commands/newartifacts.py`, `features/spec_artifacts/new_artifacts.py`
Issue: "next/new" names for now-permanent, wired features (`container.py:306`,
`main.py:27-31,64-66`). Misleads about maturity and invites a future `reports_next_next`.
Recommendation: rename at the next breaking-change window.

Hunted and NOT found: commented-out blocks (none in inspected modules); `_old`/`_v2`
production shadows (the `migrate/tree_v2|state_v2` modules are the live migration feature,
wired at `main.py:61`); orphan bash hooks (`public/scripts/` holds exactly 3 files, the gate
quartet is gone — the only `sdd-spec-gate` references are the supersede logic in
`workspace/service.py:131-133` which actively *removes* stale `.sh` entries, and the
OpenCode `.ts` shim); duplicate classifier implementations (the hook delegates to
`gate_policy`, verified — no second copy); module-level mutable globals (none).

---

## 4. Prior-finding verification table (original audit 2026-06-10T010550Z)

| # | Original finding | Verdict | Evidence |
|---|---|---|---|
| F1 (CRIT) | Gate taxonomy dead for in-repo specs (`repos/` ⇒ MUTATING first) | **SOLVED** | `gate_policy.py:150-193` context-relative re-root; unmatched in-repo ⇒ MUTATING never UNGATED (`:179-180`); MEMORY/FROZEN live in-repo (`:254-260`, F1's extension covered); phase read from the context's own ACTIVE.md (`sdd_gate.py:264-267`) |
| F2 (CRIT) | Liveness = write-recency; PID lesson discarded; heartbeat keyed on env var never set | **SOLVED** (residual A7) | TTL floor + PID veto `lock_liveness.py:111-134`; no-steal in `lease.py:387-402,509-510`; long-lived pid `sdd_gate.py:65-96`; heartbeat renews per PostToolUse match-all on held leases by harness-native sid `sdd_post_gate.py:72-106` + `runtime_config.py:88-100`; CAS-atomic renew `lease.py:411-458` |
| F3 (HIGH) | `--mode read`/bind theater (`DADAIA_MODE` env only) | **SOLVED** | env → self session record → context-incumbent (anti-downgrade w/ canonical liveness) → default, `sdd_gate.py:131-205`; READ blocks MUTATING before any lease write `gate_policy.py:262-267`; bind persists mode + refreshes incumbent `cli/commands/context.py:399` |
| F4 (HIGH) | Memory/constitution assert behavior code lacks | **SOLVED** | `specs/memory/architecture.md:107-117` (re-rooted taxonomy), `:164-176` (PostToolUse heartbeat, harness-native sid), `:388-390` (record schema incl. `pid`, TTL+PID-veto) — matches verified code |
| F5 (HIGH) | Normative vision doc `docs/01_medium_codex.md` missing | **SOLVED** | `docs/01_medium_codex.md` exists in-repo; SPEC-DOC-028 doctor check guards constitution file refs (`features/specs/doctor.py:1155-1163`) |
| F6 (HIGH) | Ledger lies (phase=SPEC w/ all-[x]); archive release-id collision | **SOLVED** | ACTIVE.md = `release: none / phase: none` post-CLOSURE; v0.1.9 + v0.1.10 archived **with CLOSURE.md**; v0.2.0 nested milestones renamed `alpha-1..4/integration` (collision gone); machine invariants SPEC-DOC-024 (`doctor.py:949-1036`, encodes the exact live incident) + SPEC-DOC-026 unique ids incl. archive (`:1038-1069`) |
| F7 (MED) | Identity-store fragmentation (4 artifacts, 2 key schemes, no owner) | **PARTIAL** | `session_identity.py` is the real single owner; lease/ctx_inject/post_gate/doctor route through it (`lease.py:163-184`, `ctx_inject.py:100-107`, `sdd_post_gate.py:109-128`, `spec_context/doctor.py:546,576`). Deductions: `coherence()` unconsumed + reimplemented wrongly (A1); dead aliases + write-only session ptr (A2) |
| F8 (MED) | Stale "bash is the enforced gate" docstring | **SOLVED** | `gate_policy.py:1-26` names the Python hook package; bash quartet retired (D-1); `public/scripts/` holds only 3 legitimate files |
| F9 (MED) | Pre-push gate never worked in canonical layout | **SOLVED** | `pre-push-ci-gate.sh:38-85` — `$DADAIA_BIN` → walk-up to `<ws>/.dadaia/.venv/bin/dadaia` → poetry → repo venv; fail-CLOSED; `--probe-only` |
| F10 (LOW) | ignore_imports growing unbounded | **SOLVED-as-specified** (debt itself unshrunk — A4) | exact-equality ratchet + growth cap + features-only-edge guard, `tests/contract/test_import_linter_ignore_cap.py:44,73-118` |

Tally: **8 SOLVED, 1 SOLVED-as-specified, 1 PARTIAL, 0 UNSOLVED.** Every solved item is a
structural fix at the named root cause — none is a patch-around. The original audit's two
REJECT gates (root-cause; architecture-fidelity) are now satisfiable: the lock family's
root causes (identity channel, taxonomy root, liveness model) were each rebuilt, and the
documented contract matches the code I read.

---

## 5. Score

| Axis | Score | Basis |
|---|---|---|
| Layering & cohesion | 9 | enforced contracts + ratchet; clean graph verified by grep; real composition root; policy/mechanism split in kernel |
| Abstraction honesty | 8 | protocols real; 17 documented suppressions, capped but not shrinking (A4); contract surface one-directional (A3) |
| Concurrency/locking foundation | 8.5 | all three root causes rebuilt and mutually reinforcing (taxonomy, liveness, mode/identity); residual A7 assumption documented |
| Spec/code/memory fidelity | 8.5 | architecture.md/constitution match verified code; ledger machine-enforced — minus the dead SPEC-DOC-029 (A1) |
| Process ledger integrity | 8.5 | CLOSUREs present, ACTIVE freed, collisions renamed, invariants in doctor; one of the six new invariants is dead (A1) |
| Dead/stale/slop hygiene | 7 | small but real: dead backstop with fabricated-fixture test (A1), exported dead API (A2), controlled corpse (A5), naming slop (A8) |
| **Overall** | **8.5** | the remediation is genuine root-cause engineering — but one *claimed v0.1.10 deliverable* (the D-2 coherence backstop) is dead on arrival behind a test that fabricates its evidence, which is exactly the defect class this audit exists to refuse to certify |

**Verdict: FAIL at the ≥9 deploy bar — by a narrow, precisely-scoped margin.**
I will not stake my name on a release whose own safety-net deliverable cannot fire and is
"proven" by a fixture production never produces. Fix A1 (+ the A2 corpses it exposes) and
this codebase is a defensible 9.

## 6. Residual actions (ranked)

1. **A1 — make SPEC-DOC-029 real**: read `<ctx>.lock.json` (via `lease.read_record` /
   `session_identity.coherence`), rewrite the test to create the record through
   `lease.acquire`. Small diff, restores the D-2 backstop claim.
2. **A2 — delete or wire the dead identity API** (`coherence`, `read_session_ptr`,
   `record_for`, `incumbent` alias, `gc_orphan_session_ptr`); decide the write-only
   session-keyed `.ptr`'s fate.
3. **A3 — add an import-linter `layers` contract** freezing the full verified graph
   (core ← infrastructure; features → core; cli/hooks top).
4. **A4 — schedule the container-DI cleanup** that shrinks the 17-edge carpet; fix the four
   stale TODO anchors in `locking.py`/`telemetry/service.py`.
5. **A6 — disambiguate the two lock namespaces** sharing `ctx_locks/`.
6. **A7 — per-harness live verification of the recorded holder pid** (process-tree check on
   Claude/Codex/OpenCode hosts).
7. **A5/A8 — name the removal release for `server dashboard`; rename `reports_next` /
   `newartifacts` at the next breaking window.**

---

*software-architect · adversarial verification · evidence-only · no production files
modified. This report's own Write into `repos/dadaia-workspace/specs/audits/…` classified
ADDITIVE under the re-rooted taxonomy (`gate_policy.py:50-54,177-180`) — the original
audit's self-demonstrating F1 footnote now demonstrates the fix.*

---

## rc-3 delta re-audit (2026-06-10, HEAD 762b4b6)

> Adversarial verification of the rc-3 iteration (commits e93a7d8 + 762b4b6) against the
> morning findings above. Method: read-only code trace (no Bash in this lane — red path
> traced end-to-end through `lease.acquire` → `SpecsDoctor._check_lease_session_coherence`
> → `session_identity.coherence`); all greps repo-wide.

### Finding → verdict table

| Finding | rc-3 claim | Verdict | Evidence |
|---|---|---|---|
| **A1 (HIGH)** dead SPEC-DOC-029 backstop | reads production records, delegates to `coherence()`, wired from CLI, production-writer tests | **FIXED** | `features/specs/doctor.py:1228` globs `*.lock.json` (the real record name, `lease.py:151`; cannot match the fcntl `<slug>.lock` or `.lock.sentinel` — the A6 trap is defused at this consumer); holder read via `lease.read_record` (`:1234-1236`); verdict delegated to `session_identity.coherence` (`:1237`) — the divergent duplicate is **deleted**, one implementation remains. `coherence()` now has a real production caller. CLI wiring confirmed: `cli/commands/specs.py:52-65` (`_resolve_workspace_state_dir` via `resolve_workspace_root()/.dadaia`, fail-soft `None`) injected at `:123-128` — the backstop fires from `dadaia specs doctor`, not just the service layer. |
| **A1 tests** | built via production writers | **VERIFIED** | Three layers, all state created exclusively through `lease.acquire` + `session_identity.set_incumbent`/`write_session` — zero fabricated fixtures: unit `tests/unit/features/specs/test_doctor_ledger_invariants.py:373-432` (red fires on the real `<ctx>.lock.json` path, green clears, no-op without `workspace_state_dir`); service-level integration `tests/integration/test_specs_doctor_coherence_backstop.py`; **CLI-level** integration `tests/integration/cli/test_cli_specs_doctor_coherence.py` (invokes `specs doctor` via CliRunner from a tmp workspace cwd — covers the coordinator-caught wiring gap both red and green). Red path traced by hand: acquire ⇒ record holder S1 + incumbent ptr S1; drift ptr→S2 + S2 session record ⇒ `coherence` returns three-source divergence ⇒ SPEC-DOC-029 ERROR on `ctx-a.lock.json`. Fires. |
| **A2 (MED)** dead identity exports | corpses deleted; remaining API all called; ctx_inject change sound | **FIXED** | Repo-wide grep: `read_session_ptr`/`write_session_ptr`/`session_ptr_path`/`gc_orphan_session_ptr`/`record_for`/`incumbent`-alias — **zero hits** in production *and* tests (only docstring/audit/spec prose remains). Every remaining `__all__` name has a production caller: `coherence`→`specs/doctor.py:1237`; `iter_ptr_files`→`spec_context/doctor.py:576`; `ptr_path`→`lease.py:172`; `read_incumbent_ptr`→`lease.py:178`; `read_session`→`sdd_gate.py:164`/`sdd_post_gate.py:119`/`doctor.py:546`; `resolve_identity`→`sdd_gate.py:170`; `set_incumbent`→`cli/context.py:399`; `write_incumbent_ptr`→`lease.py:184`; `write_session`→`sdd_post_gate.py:125`/`cli/context.py:398`. (`session_record_path` is exported with only internal-production callers — canonical path constructor of the path-owner module; LOW residue, not a corpse.) ctx_inject: the write-only `<sid>.ptr` write is **gone entirely** (`ctx_inject.py` no longer touches `session_identity` at all); legacy `<sid>.ptr` orphans are still swept by PTR-GC (`spec_context/doctor.py:576-588` — no matching `<sid>.lock.json` ⇒ orphan ⇒ deleted). Sound migration path. |
| **A3 (MED)** one-directional contracts | 2 reverse contracts, zero ignores; cross-feature edge removed via core registry | **FIXED** | `setup.cfg:98-117` adds `core-no-upper-layers` + `infrastructure-no-upper-layers`, both with **zero** `ignore_imports`. Independently verified by grep: zero imports of features/infrastructure/cli/hooks in `core/`, zero of features/cli/hooks in `infrastructure/` — both contracts pass on the actual import graph. `model_resolution.py` no longer imports `features.telemetry.pricing`: pricing key-set computed from `core.model_registry.REGISTRY` (`:98`), and the "by construction" claim is **true, not asserted** — `PRICING_TABLE` is a genuine comprehension over `REGISTRY` (`telemetry/pricing.py:42-44`), so its key-set cannot hand-drift from the registry without a code change. The `MODEL_MAP` infra import remains the documented ignore edge (`setup.cfg:57`). |
| **A3/A4 cap** | unchanged ≤17 with shrink note | **VERIFIED** | `setup.cfg` edges counted by hand: 12 + 5 = 17. Exact-equality ratchet intact (`test_import_linter_ignore_cap.py:96-108`); explicit SHRINK NOTE (`:45-52`) names the backlog item and states the reverse contracts add zero edges. Parser handles ignore-less contracts (`:71-78` defaults to `""`). |
| **NEW edge** `features/specs/doctor.py:63 → features.spec_context.{lease,session_identity}` | flagged out-of-scope by implementers | **ACCEPTABLE DEBT — not a regression** | Judgment: (a) it is delegation to the **single designed identity owner** — the alternative (a local copy of coherence logic) is literally the A1 defect being fixed; (b) net cross-feature edge count is **flat at 1** (the telemetry data edge was removed in the same iteration — repo-wide grep confirms this is now the *only* features→features import in the tree); (c) caveat recorded: no contract governs features→features, so this edge is held by discipline alone — when the A3 follow-on `layers`/independence contract lands, this edge must be explicitly declared (or `session_identity`, which is pure stdlib, promoted to `core/`). |
| **New corpses from rc-3 edits** | — | **NONE FOUND** | The old fabricated-fixture test is replaced (no `*.lock` fabrication remains in `test_doctor_ledger_invariants.py`); no dangling test references to the deleted API; all imports in the touched files (`doctor.py`: `lease`, `session_identity`, `_CTX_NAME_RE`; `ctx_inject.py`; `model_resolution.py`; `cli/specs.py`: `_resolve_workspace_state_dir`) are used. `specs upgrade`'s internal pre/post doctors intentionally omit `workspace_state_dir` (migration-scoped; documented no-op) — not dead code. |

### Unchanged residuals (out of rc-3 scope, all LOW/MED, pre-acknowledged)

A4 debt pile itself (cap honest, shrink scheduled via backlog), A5 dashboard corpse,
A6 namespace adjacency (mitigated at the new consumer by the precise `*.lock.json` glob),
A7 ppid assumption, A8 temporal naming.

### FINAL RE-SCORE: 9.2/10 — PASS (≥9)

Justification: the two findings that scoped the 8.5 FAIL are fixed **at their root cause**
— the D-2 backstop now reads the genuine production artifact through the single designed
API, is wired all the way to the CLI surface, and is proven by tests that create state
exclusively through production writers at three layers (unit, service, CLI), eliminating
the fabricated-evidence defect class this lane refused to certify. The A2 corpses are
deleted with zero dangling references, and the surviving API is 100% production-consumed.
rc-3 additionally went beyond the minimum bar: the reverse-direction layering contracts
freeze `core`/`infrastructure` purity with zero suppressions, and the only cross-feature
import was re-routed through the core registry on a derivation that is verifiably true by
construction. Per-axis deltas: spec/code fidelity 8.5→9.5 (backstop real, CLI-wired,
three-layer proven), ledger integrity 8.5→9.5 (all six invariants now live),
dead/stale/slop hygiene 7→8.5 (A1/A2 cleared; A5/A8 LOW remain), abstraction honesty
8→9 (reverse contracts; minus the one discipline-held features→features edge). Held below
9.5 overall by the undeclared-by-contract `specs→spec_context` seam, the unshrunk 17-edge
debt pile (A4), and the unchanged LOW residuals.

*software-architect · rc-3 delta re-audit · read-only except this appendix.*
