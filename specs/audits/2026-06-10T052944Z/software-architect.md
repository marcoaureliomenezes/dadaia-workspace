# Software-Architect RE-AUDIT — dadaia-workspace after v0.1.10

> Audit: 2026-06-10T052944Z re-audit · agent: software-architect · mode: REVIEW
> Baseline: specs/audits/2026-06-10T010550Z/software-architect.md (score 6/10)
> Scope: feature/v0.1.10 HEAD f77e96c, 29/29 tasks [x]. Evidence-only; no production edits.
> All paths relative to `repos/dadaia-workspace/` unless noted.

---

## 0. Verdict

**Score: 7.5/10 (was 6).** This release is the first in the lock-bug family's history that
fixed at the **root-cause layer** instead of one layer above it: the classifier was re-rooted
at the context, the heartbeat became a real liveness signal, the ledger became
machine-checked, and the constitution/memory were rewritten to the verified contract. The
incident's actual entry vector (in-repo ADDITIVE write stealing a lease) is dead and proven
dead by a real-process e2e suite.

It is **not a 9**, for one precise reason: the never-built **trusted harness→gate identity
channel** (baseline systemic root cause #1) claimed two more victims inside this very fix.
Both new defects are "works in the test world, dead in the harness-real world" gaps:

- **NF-1**: the restored PID veto records the **ephemeral hook subprocess's pid** — dead
  milliseconds after acquire — so the no-steal veto is inert for every harness-acquired
  lease, and the exact incident window (>TTL single long Bash call) remains stealable by a
  foreign MUTATING write.
- **NF-2**: the bind-mode channel persists the session record under a **CLI-generated sid**
  that the gate (which resolves the **harness-native sid**) can never match — READ
  enforcement is unreachable in the default in-session bind flow.

Fixing both is small (record a long-lived pid at acquire; key/link the bind record to the
harness sid) and would honestly carry this architecture to 9+.

---

## 1. Core-workflow record

- **Core problem:** verify whether v0.1.10 resolved the original lane's findings at root
  cause, and whether the new architecture (session_identity, model_registry, probe
  injection) is clean or new debt.
- **Constraints:** read-only; Read/Glob/Grep only; evidence must be file:line; ≥9 bar with
  honesty over rubber-stamping.
- **Success criteria:** every original finding re-verified in current code; new modules
  judged; ≥3 bug closures spot-verified; score on the same six axes.
- **Prior art:** the baseline lane itself + the v0.1.10 SPEC (WS-R1..R6) + the two-actor
  e2e suite (`tests/e2e/test_two_actor_lease.py`).

---

## 2. Per-finding verdict table

| # | Original finding | Verdict | Evidence |
|---|---|---|---|
| F1 | Gate path taxonomy dead for every real Spec Context (CRITICAL) | **RESOLVED — root cause** | `gate_policy.py:150-193` — `_context_relative()` strips `repos/<slug>/`, ordered `specs/` taxonomy (`:133-147`) applied to the remainder; in-repo ADDITIVE/MEMORY/FROZEN all reachable; unmatched in-repo ⇒ MUTATING, never UNGATED (`:179-180`). MEMORY/FROZEN extension I demanded is in (`:60-61` applied via `_classify_specs_relative`). E2E proves an in-repo `specs/bugs` write through the **real hook subprocess** never appears in the lock history (`tests/e2e/test_two_actor_lease.py:219-256`). |
| F2 | Liveness = write-recency; PID lesson discarded (CRITICAL) | **PARTIAL** | Heartbeat is real: PostToolUse renews **every lease the sid holds**, sid resolved harness-native from stdin payload, old `DADAIA_SESSION_ID` no-op guard deleted (`hooks/sdd_post_gate.py:89-107,167-189`; `hooks/_common.py:102-116`). Renew runs inside the same O_EXCL sentinel CAS as acquire — the historical renew-vs-takeover interleave is closed (`lease.py:411-458`); holder-safe renew past TTL (`lease.py:377-385`). PID veto restored as designed: `core/lock_liveness.py:119-134` (veto only on the TTL-stale branch, fail-open on probe error), injected hook→adapter→lease with no new import-linter edge (`hooks/sdd_gate.py:38-61`, `lease.py:68-72`). **BUT see NF-1**: the pid written into the record on the harness path is the hook subprocess's own (`lease.py:328` `os.getpid()`; `gate_policy.evaluate` has no `pid` param, `sdd_gate.py:196-205` passes none; zero `getppid` in the tree) — dead on hook exit, so the veto never fires for hook-acquired leases. The >120 s single-call window (the incident's D2: long pytest) is therefore still stealable by a foreign MUTATING acquire. |
| F3 | `--mode read` / bind is theater at the gate (HIGH) | **PARTIAL** | READ is genuinely non-acquiring at the policy: blocked **before** any lease call, no record write (`gate_policy.py:95-107,253-258`). Mode resolution is env override → CLI-owned session record → IMPLEMENTATION default (`hooks/sdd_gate.py:96-120`). Bind persists mode/pid/release via session_identity (`cli/commands/context.py:364-391`). **BUT see NF-2**: bind keys the record by a fresh `sess_<uuid8>` (`context.py:364`) while the gate reads the record keyed by the **harness-native** sid (`_common.py:108-116`); no linkage exists (`ctx_inject` writes only a self-referential session ptr, `hooks/ctx_inject.py:100-107`). In the default in-session bind flow the record is unreachable ⇒ mode silently defaults to IMPLEMENTATION. The record path works only via the legacy `--print-env` pre-launch export. |
| F4 | Memory/constitution assert lock behavior code never had (HIGH) | **RESOLVED** (with one inherited overstatement) | Constitution §8 rewritten to the implemented contract: phase×class×lease matrix, context-relative re-root, record schema `{…,pid,heartbeat,ttl}`, TTL+PID-veto (`specs/constitution.md:215-274`). `specs/memory/architecture.md` §"Modelo de concorrência e lease (v0.1.10)" (`:100-233`) matches `gate_policy`/`lease`/`sdd_post_gate` line-for-line, including the honest "gate does not read TASKS.md/markers" disclosure (`:218-221`). `sdd-gate-v3.md` atom regenerated (release_origin v0.1.10). Residual: arch.md:170-173 claims a long-pytest holder is "kept fresh" by match-all PostToolUse and that the long-call window "é coberto pelo PID veto" — the first is only true *between* calls, the second is untrue on the harness path (NF-1). |
| F5 | Normative vision doc does not exist (HIGH) | **RESOLVED** | `docs/01_medium_codex.md` committed (Glob hit); constitution file refs now machine-checked by SPEC-DOC-028 (`features/specs/doctor.py:1121-1161`). |
| F6 | Release ledger lies; archive id collision (HIGH) | **RESOLVED** | All five ledger invariants implemented and wired: SPEC-DOC-024 phase↔markers, 026 unique ids releases+archive, 027 naming canon, 028 constitution refs, 029 lease↔session coherence backstop (`doctor.py:447-451,934-1206`). Archive repaired: v0.2.0's colliding internal milestones renamed `alpha-1..4`/`integration` (Glob: `_archive/releases/v0.2.0/alpha-*`); v0.1.9 archived with retro-CLOSURE (T-010-15); `ACTIVE.md` reads `v0.1.10 / alpha-1 / CLOSURE` — coherent with 29/29 `[x]`. |
| F7 | Identity-store fragmentation (MEDIUM) | **RESOLVED — minor residue** | `session_identity.py` is the sole constructor of both ptr namespaces + the session record, with validation, atomic writes, fail-soft reads, and an explicit `coherence()` contract consumed by the doctor (`session_identity.py:96-119,260-302`). `lease.py:163-184`, `ctx_inject.py:100-107`, doctor (`spec_context/doctor.py:546,576`), and bind (`context.py:391`) all route through it. Residue: `sdd_post_gate._refresh_session_record` still hand-builds `sessions/<id>.json` (`sdd_post_gate.py:118`) — the module's own docstring admits "next wave". One bypass left; LOW. |
| F8 | Stale "bash is the enforced gate" docstring (MEDIUM) | **RESOLVED** | `gate_policy.py:1-10` names the Python hook quartet as enforcement; bash quartet retired in v0.1.10 D-1 (T-010-13); only `pre-push-ci-gate.sh` remains, deliberately shell. |
| F9 | Pre-push gate never worked in canonical layout (MEDIUM) | **RESOLVED** | `public/scripts/pre-push-ci-gate.sh:12-52` — resolution order `$DADAIA_BIN` → walk-up `<ws>/.dadaia/.venv/bin/dadaia` (the canonical self-hosting layout) → poetry → repo-local `.venv`. Bug Closed with the right fix. |
| F10 | Lazy features→infrastructure fallbacks accumulate (LOW) | **RESOLVED** | Ignore-edge cap pinned in `tests/contract/test_import_linter_ignore_cap.py`, documented as a ratchet ("LOWERING encouraged, RAISING requires…") in `setup.cfg:16-22`. Count is 17 (12+5) — higher than the baseline's 11 because the subprocess contract's edges are now counted under the same cap; growth is now CI-blocked, which was the actual recommendation. |

**Tally: 7 resolved at root cause, 2 partial (F2, F3), 1 resolved-with-residue (F7).**

---

## 3. New findings (new debt introduced/uncovered in v0.1.10)

### [CRITICAL] NF-1 — The restored PID veto probes a dead pid on the harness-real path
Location: `features/spec_context/lease.py:328` (`holder_pid = os.getpid() if pid is None else pid`);
`features/spec_context/gate_policy.py:196-207` (`evaluate` has no `pid` parameter);
`hooks/sdd_gate.py:196-205` (passes none); zero `getppid`/`harness_pid` in `dadaia_workspace/` (Grep).
Issue: in the harness, `lease.acquire` runs inside the PreToolUse hook **subprocess**, which
exits within milliseconds. The `pid` stamped into the lock record is that subprocess's pid.
Every later `pid_probe` (the WS-R2 no-steal veto, `core/lock_liveness.py:119-134`) therefore
probes a dead pid and returns the plain TTL verdict. The veto is structurally inert for
every lease acquired through the gate — which is every harness lease.
Why it matters: the veto was *specifically* built to cover the heartbeat-starvation window —
a holder inside one >120 s tool call (full pytest, the canonical closure activity) gets no
PostToolUse until the call returns. In that window a foreign MUTATING acquire finds
TTL-stale + dead-pid ⇒ **TAKEOVER**. The reproduced incident's D2 scenario survives the fix;
only its ADDITIVE entry vector (D1) is dead. Exactly-one-mutating still fails under the
longest, most critical operations. The e2e suite never catches this because every test
holder is a **long-lived direct-API process** (`tests/e2e/test_two_actor_lease.py:78-98`) —
the hook-subprocess-acquired-holder case is untested.
Trade-off if fixed: the hook must record a pid that outlives it — `os.getppid()` chains to
the harness (or its shell wrapper; needs per-harness verification), or the sid-keyed session
record could carry a CLI/ctx-inject-established long-lived pid. Either is small but touches
the no-steal boundary: re-run the two-actor matrix with a **hook-acquired** holder.
Recommendation: add the missing e2e scenario (holder acquires THROUGH `run_hook_subprocess`,
goes busy past TTL, foreign MUTATING attempts) — it fails today; then fix the recorded-pid
identity until it passes. Do not close the lease-theft family before this is green.

### [HIGH] NF-2 — Bind-mode record is keyed by a sid the gate can never resolve
Location: `cli/commands/context.py:364` (`session_id = f"sess_{uuid.uuid4().hex[:8]}"`);
`hooks/sdd_gate.py:96-120` (`_resolve_mode` reads the record keyed by the harness-native sid
from `_common.resolve_session_id`, `hooks/_common.py:102-116`); `hooks/ctx_inject.py:100-107`
(no harness-sid→bind-record link is ever written).
Issue: the WS-R4 design says READ enforcement "flows entirely through the on-disk record the
bind CLI persisted" (`sdd_gate.py:102-104`). But bind invents its own sid; the gate resolves
the harness's. The two never meet: in the default flow (operator runs
`dadaia context bind <ctx> --mode read` via the Bash tool inside a live session) the gate's
`read_session(harness_sid)` misses and mode falls back to IMPLEMENTATION. The on-disk
channel is only reachable through the legacy `--print-env` + pre-launch `eval` ceremony —
i.e., the env channel the record was supposed to replace. Every WS-R4 test constructs the
linkage by hand (`session_identity.write_session(ws, sid, …)` with the *same* sid fed to the
payload — `tests/integration/gate/test_read_mode_non_acquiring.py:60,83`,
`tests/unit/hooks/test_sdd_gate.py:223-229`), so the gap is invisible to the suite.
Why it matters: a read-bound session silently retains full lease-taking power — the same
"bind is theater" defect (D3) re-closed one layer down. The `context-bind-forces-mode-choice`
and lease-stolen (D3 part) closures overstate what shipped. This is the **third** generation
of systemic root cause #1 (persona → session-id → bind-sid linkage): identity facts written
by one process under one key, read by another process under a different key.
Trade-off if fixed: bind cannot know the harness sid a priori. Options: (a) ctx_inject
links at SessionStart — copy the newest live bind record for the resolved context onto the
harness sid; (b) gate falls back to `resolve_identity(ctx)` (incumbent-ptr → record), which
`session_identity.py:238-252` already implements and nothing calls for this purpose.
(b) is one line of consumption of an existing seam.
Recommendation: wire `_resolve_mode` to fall back to the context's incumbent identity (or
add the ctx_inject link), plus one harness-real test: bind READ via the CLI (its own sid),
then drive the gate with a different payload sid and assert BLOCK.

### [LOW] NF-3 — `sdd_post_gate` still bypasses the session-identity owner
Location: `hooks/sdd_post_gate.py:110-135` builds `sessions/<sess_id>.json` directly vs
`session_identity.read_session/write_session`; the owner's docstring itself flags it
("next wave", `session_identity.py:14-16`).
Issue: one remaining hand-built path into the consolidated namespace; honest, documented,
but it is exactly how fragmentation regrows.
Recommendation: route it in the next segment; add a grep contract test that no module
outside `session_identity` constructs `".dadaia" / "sessions"` paths.

---

## 4. New-architecture judgment (session_identity, model_registry, probe chain)

| Module | Verdict | Notes |
|---|---|---|
| `features/spec_context/session_identity.py` | **Clean** | Single owner, validated names (CWE-22), atomic writes, fail-soft reads, ignored-and-superseded migration law, explicit `coherence()` contract with doctor backstop (SPEC-DOC-029). Honest about its one un-migrated consumer (NF-3). Two pointer namespaces still exist but are now owned, documented, and coherence-checked — acceptable. |
| `core/model_registry.py` | **Clean — exemplary** | Pure data in core (zero I/O, contract-compliant), `MODEL_MAP`/`PRICING_TABLE` become derived views (`features/telemetry/pricing.py:35-43`), append-only dated pricing preserves telemetry reproducibility. This is the correct cure for systemic root cause #4 (one fact, N tables). |
| Probe injection chain (hook → `OsProcessProbe` → `lease.pid_probe` → `lock_liveness.is_stale`) | **Clean design, mis-bound value** | Layering perfect: features never import the adapter, no new import-linter ignore, veto only suppresses staleness (can never create it), fail-open on probe error. The *mechanism* is right; the *pid identity* fed into it on the harness path is wrong (NF-1). |

No spaghetti, no code-on-code: the bash hook quartet was deleted (not wrapped), the v0.1.9
nested-archive residue was renamed (not papered over), and the ratchet cap turns the debt
list into a CI-enforced one-way street.

---

## 5. Bug-closure honesty (spot-verified)

| Bug | Closure verdict | Evidence |
|---|---|---|
| `lease-stolen-by-additive-write-from-live-session` (CRITICAL) | **Honest for D1, overstated for D2/D3** | D1 (ADDITIVE steals lease) root-cause dead, proven through the real hook subprocess (e2e i). The closure's "a live holder is never taken over" holds only for direct-API holders (NF-1); D3's read-mode promise holds only when the sid linkage exists (NF-2). |
| `gate-fpath-not-canonicalized-before-classifier` | **Honest — root cause** | `sdd_gate.py:158` `fpath.resolve().relative_to(workspace.resolve())`; dedicated regression suite `tests/integration/gate/test_classifier_symlink_canonicalization.py`. |
| `model-catalog-modelmap-pricing-drift-no-registry` | **Honest — root cause** | Single registry + derived views (above); haiku id reconciled with history preserved (`model_registry.py:32-38`). |
| `pre-push-gate-cannot-locate-workspace-venv` | **Honest — root cause** | Walk-up workspace-venv probe + `DADAIA_BIN` (F9). |

---

## 6. Score rubric (same axes as baseline)

| Axis | Was | Now | Basis |
|---|---|---|---|
| Layering & cohesion | 8 | **9** | bash layer deleted not wrapped; registry in core; probe chain respects every contract; ratchet cap |
| Abstraction honesty | 7 | **7** | protocols/registry real; but `_resolve_mode`'s "harness-real path" docstring and arch.md's veto claims overstate what the harness actually gets (NF-1/NF-2) |
| Concurrency/locking foundation | 3 | **6** | taxonomy fixed + ADDITIVE truly lock-free + real heartbeat + CAS renew + READ non-acquiring; residual CRITICAL window: >TTL single call protected only by a dead-pid veto (NF-1), mode channel unreachable by default (NF-2) |
| Spec/code/memory fidelity | 4 | **8** | constitution §8 + architecture.md + atoms rewritten to verified behavior; SPEC-DOC-028 guards refs; two narrative overstatements inherit NF-1/NF-2 |
| Process ledger integrity | 4 | **9** | five machine-enforced invariants; archive collision repaired; retro-CLOSURE; ACTIVE coherent |
| Testability & regression discipline | 7 | **7** | real-process two-actor e2e is the best suite this repo has produced; but both new defects live exactly where tests hand-construct the state the harness never constructs (hook-acquired holder; sid linkage) |
| **Overall** | **6** | **7.5** | root-cause release; the harness-identity channel claimed two more victims |

---

## 7. Review-gate verdicts (persona §0.1)

- **Root-cause gate: APPROVED for F1/F4/F5/F6/F8/F9/F10 and the D1 theft vector; REJECTED
  for declaring the lease-theft *family* closed.** The no-steal half (D2) and the read-mode
  half (D3) are root-caused on paper but mis-bound in the harness-real path (NF-1, NF-2).
  Required correction: hook-acquired-holder e2e + long-lived pid identity; incumbent-identity
  fallback (or ctx_inject link) for mode resolution + a cross-sid READ test.
- **Architecture-fidelity gate: APPROVED with two corrections.** The rewritten constitution
  §8 / architecture.md are faithful to the implemented mechanism; amend the two sentences
  that overstate harness-path protection (arch.md:170-173 PID-veto coverage of long calls;
  the "session record is the harness-real mode path" claim) when NF-1/NF-2 land.

## 8. What blocks 9/10

1. **NF-1** — record a pid that outlives the hook; prove no-steal with a hook-acquired
   holder in the two-actor e2e. (CRITICAL)
2. **NF-2** — make the bind-mode record reachable from the harness sid
   (`resolve_identity` fallback already exists, unconsumed). (HIGH)
3. Minor: NF-3 routing + the two doc sentences above.

Nothing else in the original lane remains open.

---

*software-architect · evidence-only · no production files modified. This report's own Write
into `repos/dadaia-workspace/specs/audits/…` classified ADDITIVE under the re-rooted gate —
the baseline's self-demonstrating defect is now a self-demonstrating fix.*
