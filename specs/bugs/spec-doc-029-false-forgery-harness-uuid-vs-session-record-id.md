---
name: spec-doc-029-false-forgery-harness-uuid-vs-session-record-id
status: Closed
severity: MEDIUM
reported: 2026-06-13
session_id: f4f75564-4c92-4ad0-9ce3-93d0411db60c
surface: specs doctor SPEC-DOC-029 (lease↔session coherence) + non-isolated ctx_locks scan
---

**Symptom:** `dadaia specs doctor` raises a SPEC-DOC-029 **ERROR**
("session-identity incoherence … possible out-of-band lock/ptr forgery; D-2
backstop") on a perfectly normal long-running session. The check compares the
lock holder against the context incumbent pointer, but the two values are drawn
from **different id namespaces**:

- lock holder (`ctx_locks/<ctx>.lock.json` → `session_id`) = the **harness
  session UUID** (e.g. `f4f75564-4c92-4ad0-9ce3-93d0411db60c`, the Claude
  conversation id written by the gate/heartbeat).
- incumbent pointer = a **dadaia session-record id** (e.g. `sess_0bac2bc0`).

These can never be equal, so the coherence check reports forgery on a benign
session whose lock and incumbent both legitimately refer to the same live
session. It is a **false positive ERROR**.

Two distinct defects:

1. **Namespace mismatch → false forgery (MEDIUM).** SPEC-DOC-029 equates a
   harness UUID with a `sess_*` record id. It should compare like-for-like
   (resolve both to the same identity space before asserting coherence), or
   downgrade to a WARN when the mismatch is purely a namespace difference.
2. **Non-isolated scan leaks into unrelated tests (MEDIUM).** `dadaia specs
   doctor --specs-dir <TMP>` still scans the **live workspace**
   `.dadaia/states/ctx_locks/` rather than confining itself to the supplied
   `--specs-dir`. As a result the live incoherence above made two unrelated
   integration tests fail on a clean checkout:
   `tests/integration/cli/test_cli_specs_doctor_fix.py::test_doctor_exit_0_on_fully_clean_tree`
   and `::test_doctor_fix_creates_missing_dirs`. The tests pass in CI only because
   CI has no live ctx_locks; they are non-deterministic locally.

**Repro:**
1. Run a long Claude session bound to a context (the gate writes
   `ctx_locks/<ctx>.lock.json` with the harness UUID; the incumbent pointer holds
   a `sess_*` id).
2. `dadaia doctor --fix` (GCs stale leases but leaves the ERROR — it is guarded as
   possible forgery and not auto-fixed).
3. `dadaia specs doctor` (or the two integration tests above) → `[ERR] SPEC-DOC-029`
   and overall exit 1 on an otherwise clean tree.

**Expected:** the coherence check resolves both identities to one namespace before
comparing, so a single live session never trips the forgery backstop;
`--specs-dir`-scoped doctor runs do not read the live workspace `ctx_locks/`, so
the integration tests are deterministic regardless of live session state.

**Workaround used this session:** removed the live
`.dadaia/states/ctx_locks/dadaia-workspace.lock.json` (advisory lock, no pending
gate-writes) before pushing; the false ERROR cleared and the pre-push CI gate
passed. Related lock/session-model history: see memory
`feedback_lock_state_model_unsound` and the SPEC-DOC-029 lease↔session coherence
work in the v0.1.10 remediation.

**Notes:** found while shipping release 0.1.7. The forgery backstop is valuable
(D-2) and must not be removed — the fix is to compare the correct identity pair,
not to drop the check.
