---
name: bind-mode-session-record-keyed-by-cli-sid
status: Closed
severity: MEDIUM
session_id: null
reported: 2026-06-10
surface: cli/commands/context.py bind (FR-R4-02 harness-real mode path)
---

**Resolution (v0.1.10 rc-2):** gate mode resolution gained the context-incumbent fallback (env -> record[harness sid] -> incumbent `sessions/runtime/<ctx>.ptr` via `session_identity.resolve_identity` -> default), and bind refreshes the incumbent pointer; a sid-keyed record from a live different holder wins over a stale read-bind. Regression: `tests/unit/hooks/test_sdd_gate.py::test_resolve_mode_falls_back_to_context_incumbent` (+ `_self_record_wins_over_incumbent`, `_incumbent_ignored_when_live_holder_differs`, `_incumbent_honored_when_no_lease_holder`) and the cross-sid READ subprocess tests in `tests/integration/gate/test_read_mode_non_acquiring.py`.

**Symptom:** `dadaia context bind <ctx> --mode read|implementation|review` always mints
a fresh session id (`session_id = f"sess_{uuid4().hex[:8]}"`, context.py:364) and keys
the persisted session record by it. The SDD gate resolves the HARNESS-native session id
(stdin `session_id` / `CLAUDE_CODE_SESSION_ID` / `CODEX_SESSION_ID`;
`sdd_gate._resolve_mode` → `session_identity.read_session`), so in a real harness
session the bind-created record is never found and mode silently defaults to
IMPLEMENTATION. Net: `--mode read` does not make a harness session non-acquiring, and
the documented write-rights path ("the operator binds implementation mode once",
task-manager skill / READ block message) has no effect — READ enforcement is reachable
only via the legacy `--print-env` + `eval` env flow (`DADAIA_SESSION_ID`/`DADAIA_MODE`
inheritance).

**Repro:** In a harness session: Bash `dadaia context bind <ctx> --mode read` (no
eval), then perform a MUTATING Edit. Gate resolves the harness sid →
`sessions/<harness-sid>.json` absent → mode=IMPLEMENTATION → lease acquired (no READ
block). `ls .dadaia/sessions/` shows the orphan `sess_<uuid8>.json`.

**Expected:** SPEC v0.1.10 WS-R4 fix text: record "keyed by the harness-native session
id when resolvable, else by the bind-created session id"; FR-R4-02: "the gate reads it
without any env var present (the harness-real path)".

**Notes:** Fail-open direction (default IMPLEMENTATION — no freeze risk). Fix: bind
resolves the harness-native sid first (`_common.resolve_session_id` order) and only
falls back to a minted sid; alternatively key by incumbent `.ptr`. Found by the
2026-06-10T052944Z ai-engineer re-audit.
