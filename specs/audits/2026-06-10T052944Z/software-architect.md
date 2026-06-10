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

---

## rc-2 delta (commit fc388d7, re-verified 2026-06-10)

> Adversarial re-verification of the rc-2 amendment. Same rubric. Execution caveat: this
> session has no shell; the named pytest selectors were verified by adversarial reading of
> the test code (all are real-subprocess, falsifying designs), not re-executed here —
> demand a green run of `tests/e2e/test_two_actor_lease.py`,
> `tests/integration/gate/test_read_mode_non_acquiring.py`, and
> `tests/unit/hooks/test_sdd_gate.py` in the ship evidence.

### NF-1 — RESOLVED at root cause (CRITICAL → closed)

- `hooks/sdd_gate.py:64-95` `_resolve_holder_pid`: payload `harness_pid`/`parent_pid`/`ppid`
  (int or string, >0 validated, `:84-94`) else `os.getppid()` (`:95`). Threaded at `:281`
  into `gate_policy.evaluate(holder_pid=…)` (`gate_policy.py:207`), which passes
  `pid=holder_pid` into `lease.acquire` (`gate_policy.py:279`); stamped into the record at
  `lease.py:328,360-361,368,381,390` (`acquire` signature gained `pid:` at `lease.py:296`,
  `steal` at `:496`).
- **Renew preserves the holder pid** — checked: `lease.renew_heartbeat` rewrites only
  `heartbeat` (`lease.py:453`) inside the same sentinel CAS; `sdd_post_gate` renews solely
  via `renew_heartbeat` (`sdd_post_gate.py:100`), so the PostToolUse hook can never clobber
  the harness pid with its own ephemeral pid. The acquire-RENEW branches re-stamp
  `pid=holder_pid` (`lease.py:360,381`) — same harness pid on the harness path; harmless.
- **E2E is genuinely adversarial**: scenario (v)
  (`test_two_actor_lease.py:480-532`) spawns a long-lived DRIVER that invokes the **real**
  `python -m dadaia_workspace.hooks.sdd_gate` as its child (`:432-435`), asserts the lock
  record's `pid` equals the **driver's** pid (`:497` — fails on the rc-1 code by
  construction), ages the record past TTL while the driver lives, proves foreign MUTATING
  is YIELDED with the real `OsProcessProbe` (`:506-511`), then kills the driver, waits for
  OS reap, and proves TAKEOVER (`:516-527`) with the full lock-history invariant (`:530`).
  The `_set_short_ttl_on_record` accelerant (`:466-477`) rewrites only `ttl` on a record
  the real hook wrote — pid/sid/heartbeat untouched; acceptable.
- Residue (LOW, documented in the code itself): `getppid()` names the harness only when the
  harness spawns hooks as direct children; a non-exec'ing shell wrapper would record a
  short-lived shell pid and the veto degrades to TTL-only — i.e. the **pre-fix posture,
  never worse**, and the payload-pid key (`:73-76`) is the forward-compatible cure.
  PID-reuse false-live is inherent to pid-probe designs; bounded by record GC. Neither
  blocks closure.

**Verdict: the exact correction §8.1 demanded (long-lived pid + hook-acquired-holder e2e)
shipped, and the e2e is the falsification I asked for.**

### NF-2 — SUBSTANTIALLY RESOLVED; precedence guard has one liveness defect (see NF-4)

- Resolution chain implemented as specified: env → self-keyed record → context-incumbent
  via `session_identity.resolve_identity` → IMPLEMENTATION default
  (`sdd_gate.py:160-178`, ctx passed at `:261`); bind now refreshes the context incumbent
  pointer inside the workspace lock (`cli/commands/context.py:396-399`), consuming the
  exact unconsumed seam the original lane named (`session_identity.py:238-252`).
- The demanded **cross-sid harness-real test exists**:
  `test_read_mode_non_acquiring.py:125-148` binds via a CLI-style sid the harness never
  reports, drives the real hook subprocess with a *different* payload sid, asserts BLOCK
  and **no lease file created** (`:148`); ADDITIVE companion `:151-162`. Unit precedence
  matrix: self-record-wins (`test_sdd_gate.py:405-417`), live-divergent-holder ignores
  incumbent (`:420-434`), no-holder honors read-bind (`:437-448`).
- **Precedence soundness — adversarial answers:**
  - *Can a stale read-bind downgrade a live implementation holder?* No, in both live cases:
    a self-bound session's record wins (`sdd_gate.py:163-167`), and a live divergent lease
    holder voids the incumbent (`:181-193` + test `:420-434`). A busy >TTL holder is also
    safe today (any divergent record voids the incumbent), but see NF-4 for why that
    over-breadth is itself the defect.
  - *Can a foreign record downgrade?* No: self records are keyed by own sid; the incumbent
    is per-context (`<ctx>.ptr`), and `lease.acquire` rewrites the ptr to the real holder
    on first MUTATING write (`lease.py:393`), so a bind ptr self-corrects.
  - *Can a stale incumbent READ-bind block a legitimate implementation harness?* By design
    yes until the operator binds implementation — that IS the bind contract (D-3), not a
    defect.

### [HIGH] NF-4 (new, rc-2) — Anti-downgrade guard tests record *presence*, not *liveness*: a dead leftover lock record silently defeats a fresh READ bind
Location: `hooks/sdd_gate.py:189-193` — `_incumbent_is_stale` calls `lease.read_record`
(pure read, `lease.py:187-196`) and returns stale on **any** divergent `session_id`; it
never consults `core/lock_liveness.is_stale` (no TTL check, no pid probe).
Issue: lock records are not deleted when a session ends (nothing calls `lease.release` at
session end; only takeover overwrites or doctor GC removes them). So in the **canonical
flow** — implementation session finishes, operator runs `dadaia context bind <ctx> --mode
read` to review — the leftover TTL-stale record's sid differs from the bind sid, the guard
declares the *incumbent* stale, mode falls to IMPLEMENTATION, and the next harness write
TAKEOVERs the dead record and mutates. The fresh READ bind is silently inert exactly when
it is most used. The code contradicts its own docstring ("a **live** lease record",
`sdd_gate.py:182`) and `specs/memory/architecture.md:218` ("não contradiz um lease holder
**vivo**") — and it introduces a second, divergent liveness definition ("record present")
beside the kernel's canonical one (`is_stale` = TTL + pid veto). None of the rc-2 tests
cover this: every incumbent test has either no lock record or a live one.
Why it matters: READ enforcement (the D3 family) regains a common-path hole — narrower
than the old NF-2 (it fails toward the default-permissive D-3 posture; lease serialization
and no-steal are intact; no live session is ever harmed), but the operator's read-bind
promise is broken in the most ordinary sequence.
Trade-off if fixed: one-line predicate change — guard returns stale **only when the
divergent holder is live**: `holder is None or is_stale(holder, pid_probe=…) ⇒ False`.
Reusing the canonical predicate (with the probe threaded into `_resolve_mode`) also keeps
a busy >TTL live holder protected from mid-flight downgrade; TTL-only would downgrade it.
Cost: threading `pid_probe` into `_resolve_mode` + one regression test (stale divergent
record + fresh read-bind ⇒ READ honored).
Recommendation: make `_incumbent_is_stale` consume `lock_liveness.is_stale` with the same
injected probe the MUTATING path uses — one liveness definition, used everywhere — and add
the missing falsifying test. Until then, the arch.md:218 sentence overstates the guard.

### NF-3 — RESOLVED as scoped (LOW → closed; ownership residue noted)

- `sdd_post_gate._refresh_session_record` now routes read+write through
  `session_identity.read_session/write_session` (`sdd_post_gate.py:119-127`); the hook no
  longer constructs the session-record path.
- Residue (LOW, pre-existing, not an rc-2 regression): `core/specs_resolver.py:34`
  still builds `.dadaia/sessions/<id>.json` directly (core cannot import features — the
  duplication is acknowledged at `:23` but remains a schema copy), and read-side
  constructors persist in `cli/commands/context.py:76`, `spec_context/doctor.py:124`,
  `panel/views/kanban.py:85`. The grep contract test I recommended ("no module outside
  session_identity constructs sessions paths") was not added. Carry forward, LOW.

### Doc-overstatement sentences — FIXED (one new narrower one created by NF-4)

- `specs/memory/architecture.md:174-178` now states the long->TTL single call "é coberto
  pelo PID veto" — **true post NF-1** (e2e v proves it); `:147-158` documents the
  `_resolve_holder_pid` chain precisely, including the "nunca o pid do subprocesso efêmero"
  law. Constitution §8 (`specs/constitution.md:272-284`) matches the implemented record
  schema and TTL+veto semantics. The "session record is the harness-real mode path" claim
  was rewritten to the incumbent-pointer truth (`architecture.md:202-224`).
- New residual: `architecture.md:218-219` says the incumbent yields only to a **live**
  holder — that is the *intended* design; the code checks any record (NF-4). The doc is
  right and the code is wrong; fix the code, not the doc.

### rc-2 diff sweep — nothing else broken

- `gate_policy.evaluate` gained `holder_pid` (default `None` ⇒ `os.getpid()` —
  backward-compatible for long-lived direct-API callers; sole caller is the hook).
- `lease.acquire/steal` gained `pid:`; renew path untouched; CAS discipline intact.
- Bind's `set_incumbent` cannot corrupt lease identity: acquire's ptr-match branch only
  fires on `ptr == session_id` and the real holder re-stamps the ptr on its next write.
- Probe-less side doors persist (pre-existing): `cli/commands/lock.py:51` (`lock steal`)
  and `lease._main` CLI acquire (`lease.py:576`) run TTL-only with no pid probe — the
  no-steal veto can be bypassed by invoking the CLI directly via Bash. MEDIUM note for the
  backlog: thread the probe (or delete `lock steal`, which the forbidden-law already bans
  from every message).
- Bind session records (`ttl_seconds: 300`, `context.py:384`) are never renewed by
  anything; the doctor graveyard GC (`spec_context/doctor.py:465,536`) can therefore
  delete a still-wanted READ bind record ~5 min after bind, silently decaying READ → 
  IMPLEMENTATION on the next resolution. LOW note (GC is operator-run), fold with NF-4.

### Review-gate verdicts (rc-2)

- **Root-cause gate: APPROVED.** NF-1 fixed at the identity layer with the demanded
  falsifying e2e; NF-2 fixed by consuming the existing `resolve_identity` seam with the
  demanded cross-sid harness-real test; NF-3 routed. NF-4 is a new, narrower defect in the
  guard's liveness predicate — it does not reopen the family (no theft, no live-session
  harm) but must be fixed before the read-bind promise is advertised as closed.
- **Architecture-fidelity gate: APPROVED.** Constitution §8 + architecture.md now match
  the implemented mechanism; the single remaining overstated sentence
  (architecture.md:218 "holder vivo") describes the correct design that NF-4's fix will
  make true.

### Score (rc-2, same rubric)

| Axis | rc-1 | rc-2 | Basis |
|---|---|---|---|
| Layering & cohesion | 9 | **9** | probe/pid threading respects every contract (hook owns wiring, features import no adapter); NF-4 is a logic defect, not a layer breach — though "second liveness definition" is mild cohesion debt |
| Abstraction honesty | 7 | **8** | both overstated narratives corrected; one residual sentence (arch.md:218) now overstates only the guard predicate |
| Concurrency/locking foundation | 6 | **8** | the >TTL busy-holder window is closed with the production process topology proven end-to-end; READ channel harness-real; residual: NF-4 common-path READ inertness + probe-less CLI steal/acquire side doors |
| Spec/code/memory fidelity | 8 | **8.5** | docs rewritten to verified behavior incl. the pid chain; one sentence ahead of the code (NF-4) |
| Process ledger integrity | 9 | **9** | unchanged |
| Testability & regression discipline | 7 | **9** | rc-2 tests attack exactly the two hand-constructed blind spots (real-hook-child pid assertion `:497`; cross-sid incumbent at the real hook boundary); remaining blind spot (stale divergent record + fresh read-bind) is newly found here |
| **Overall** | **7.5** | **8.5** | both blockers closed at root cause with falsifying tests; NF-4 (HIGH, one-line fix + one test) + side-door notes are what hold back 9+ |

**What blocks 9+ now:** (1) NF-4 — `_incumbent_is_stale` must use the canonical
`lock_liveness.is_stale` (probe-threaded) + falsifying test; (2) probe-less `lock steal` /
lease-CLI acquire; (3) bind-record GC decay note + the NF-3 ownership contract test.
All small; none reopens the lease-theft family.

*software-architect · rc-2 delta · evidence-only · no production files modified.*
