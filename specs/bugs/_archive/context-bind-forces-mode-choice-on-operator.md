---
name: context-bind-forces-mode-choice-on-operator
status: Closed
severity: MEDIUM
reported: 2026-06-09
resolved_in: v0.1.10
surface: dadaia context bind — mandatory --mode option / bind ergonomics
session_id: sess_61345db3
---

**Resolution (v0.1.10):** Fixed by T-010-08 — `--mode` is now optional and
defaults to `read` (mode-agnostic bind), so `dadaia context bind <name>` exits 0
and prints a human confirmation without forcing the operator to pick a lifecycle
mode. Regression tests (green):
`tests/contract/cli/test_cli_context.py::test_context_bind_no_mode_exits_zero_default_read`
and `::test_context_bind_no_mode_prints_human_confirmation`.


**Symptom:** `dadaia context bind <name>` fails closed when `--mode` is omitted:

```
Error: Missing option '--mode'.
```

There is no "normal" (mode-agnostic) bind. The operator/agent is forced to pick
a lifecycle mode (`read | spec | implementation | review`) at bind time. In
practice an agent that cannot infer the mode from the demand surfaces the choice
to the **operator** — which is wrong: binding should just bind the session, and
the *dispatched role* (project-manager for backlog/release/feature work,
project-auditor for audits) is what conducts the lifecycle phase and acquires the
single-session lease only when it actually reaches implementation/review.

**Repro:**

```bash
dadaia context bind dadaia-workspace
# -> Missing option '--mode'.  (exit 2)
```

**Expected (operator's product model):**

- `dadaia context bind <name>` binds **normally** with no required mode — a plain
  session bind (effectively `read`/observe), never lock-blocked.
- The main agent then routes the demand to `project-manager` or
  `project-auditor` based on what is asked (bug fix vs feature vs audit), and that
  role determines which lifecycle phase we are in.
- Lease-taking modes (`implementation`, `review`) are escalated by the dispatched
  role *when the work requires them*, not chosen up front by the human.
- The agent MUST NOT ask the operator "which mode?" — the mode is derived from the
  demand + lifecycle, not an operator decision. Asking is the feature behaving
  wrongly.

**Notes:**

- Today's workaround used `--mode read` to bind without taking a lease
  (`DADAIA_MODE=READ`, `sess_61345db3`). Read/spec are documented as
  "never blocked", so the friction is purely the *required* flag + the
  operator-facing mode prompt, not a lock.
- Fix direction (for PM/PE to scope, not prescribed here): make `--mode` optional
  with a safe default (plain observe bind), and defer lease acquisition to the
  role/phase that needs it. Reconcile with `workspace-protocol` §2 which already
  states context resolves automatically and a bind is "optional convenience…
  never a precondition for doing work" — the mandatory `--mode` flag contradicts
  that contract.
- Related: [[session-bind-primary-residue]] (bind surface cleanup),
  `lease-cross-context-false-positive-block`, `gate-cross-context-lock-contamination`
  (lease-correctness neighborhood).
