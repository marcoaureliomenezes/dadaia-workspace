# SPEC: Release v0.1.71 — Real-consumer remediation (4 reopened bugs)

**Status:** Aprovado
**Release ID:** v0.1.71
**Owner:** product-engineer

## Context

Four bugs the v0.1.68–70 arc marked `resolved` were re-verified STILL OPEN by the
operator on the remote against installed source `574a84bd` (identical to `main`). Root
cause of the miss (per the arc post-mortem, now durable law): fixes were validated against
internal test fixtures and fake harnesses, never against the real `sample-consumer`
consumer artifacts. This release closes each at root cause and its acceptance gate is a
real-remote replay of the reporter's exact commands.

## Functional Requirements

### FR1 — write-scope parser handles the real consumer grammar (HIGH)
`write_scope_from_tasks` returns `()` for the real `sample-consumer` `TASKS.md` because
`_TASK_MARKER_RE`/`_BULLET_RE`/`_extract_globs` assume the internal grammar only.

- FR1.1 Recognize the reserved task under BOTH grammars: (a) internal `### … `[-]`` H3
  heading with inline marker; (b) consumer `**T-x.y — …**` bold heading whose active
  marker is a fenced ` ``` [-] T-x.y ``` ` block elsewhere in the file.
- FR1.2 Recognize the Write-set bullet under BOTH `- **Write set:**` (bold key) and
  `- Write set:` (plain key).
- FR1.3 Extract ALL path-shaped backtick spans from the (multi-line-joined) Write-set
  value, stripping per-path parentheticals wherever they occur — not truncating at the
  first `(`. A `(reuse …)`/`(new)` annotation after each path is ignored, not a terminator.
- FR1.4 Exactly one reserved task across the file → its write set; zero or many → `()`.
  Any structural absence degrades to `()` (never raises).
- **Acceptance:** the real `sample-consumer` `v0.2.0` `TASKS.md` (committed verbatim as a
  test fixture) with `[-] T-3.1` yields its three declared paths; on the remote,
  `write_scope_from_tasks(<sample-consumer>/specs, 'v0.2.0')` returns the T-3.1 write set.

### FR2 — diagnostic commands accept real context/release filters (HIGH)
`lifecycle status` and `lifecycle handoffs doctor` reject `--context`. `LifecycleRun`
carries `context` + `release_id`, so the option is a real filter, not cosmetic.

- FR2.1 Both commands accept `--context` (default `dadaia-workspace`) and `--release-id`
  (optional), mirroring `preflight`.
- FR2.2 When `--context`/`--release-id` are supplied, the report is computed over only the
  runs whose `context`/`release_id` match; absent filters preserve current whole-workspace
  behavior (back-compat).
- **Acceptance:** on the remote, both commands accept
  `--context sample-consumer --release-id v0.2.0 --json` and return a real result; a run
  under a different context is excluded from a filtered report.

### FR3 — no-arg `context show` reflects the bound session (MEDIUM)
After a bare `context bind sample-consumer`, `context show sample-consumer --json` shows
the session but `context show --json` resolves to first-ALIVE (`dadaia-workspace`,
`session: null`).

- FR3.1 With no name, `show` resolves to the ALIVE context whose incumbent pointer
  references a live (non-stale) session, preferring the most recently seen; falls back to
  first-ALIVE when none has a live bound session. Named `show <ctx>` is unchanged.
- **Acceptance:** on the remote, after `context bind sample-consumer …`,
  `context show --json` surfaces `sample-consumer` with its bound session.

### FR4 — doctor exempts promote_to_evidence from unconsumed_required (HIGH)
A terminal APPROVED `implement-review` review payload (`retention_mode=promote_to_evidence`)
is flagged `unconsumed_required` forever; the v0.1.68 producer fix only helps NEW runs.

- FR4.1 The `unconsumed_required` check skips any payload whose
  `retention_mode is PROMOTE_TO_EVIDENCE` — such payloads are durable evidence whose
  terminal disposition is promotion, never consumption (symmetric with
  `is_cleanup_eligible`, which already exempts them).
- FR4.2 `delete_after_consumed` required payloads on a terminal run still flag as before.
- **Acceptance:** on the remote, the pre-existing terminal run `zbug-fake-implement-review`
  no longer blocks `handoffs doctor`; a `delete_after_consumed` unconsumed payload still does.

## Non-goals
- No change to the `promote_to_evidence` retention/consumption model itself.
- No new lifecycle run migration tool (FR4 heals via read-side semantics instead).

## Red lines
- Real sample-consumer artifacts are the fixtures; every FR has a remote replay before ship.
- RED-first executed-path tests; no workarounds.
