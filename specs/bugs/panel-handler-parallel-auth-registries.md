---
title: panel-handler-parallel-auth-registries
severity: High
opened: 2026-06-07
session_id: null
status: Closed
shipped_in: 0.1.5
resolved_in: main (post-v0.1.5, T-016-P0x)
---

**Resolution (verified 2026-06-09, code-reviewer root-cause investigation):** fixed in current `main` (T-016-P0x pass). Source evidence cited in handoff `.dadaia/handoff/dadaia-workspace/2026-06-09T032430Z-code-reviewer-panel-bug-cluster-root-cause.handoff.json`; named E2E regression tests present (E2E-GUARD-01/02, E2E-SCP-03..06, E2E-THM-10). Closed; E2E suite is the standing guard.


# Bug: panel-handler-parallel-auth-registries

## Description

The panel HTTP handler enforces auth across **three independent registries**
(`_BEARER_AUTH_ROUTE_NAMES` / telemetry loop, `_BEARER_ONLY_ROUTES`,
`_SECOND_LOOP_AUTH_ROUTES`) plus an implicit public set. A developer adding a new
route must correctly classify it across all of them. A route added to
`_RAW_ROUTES` but omitted from the auth sets is **publicly accessible with no
auth check and no test will catch it** — a latent auth-bypass footgun.

## Location

- `dadaia_workspace/features/panel/handler.py:~84-167` — parallel auth
  classification lists + two dispatch loops; loopback bypass further diverges
  local-dev vs production posture invisibly.

## Related risk (same file)

- `handler.py:~128-129` — the DELETE route ordering is load-bearing and
  invisible: `^/api/reports/(?P<path>.+)/important$` must precede the catch-all
  `^/api/reports/(?P<path>.+)$`, or `DELETE .../important` deletes the report
  instead of unmarking it. No structural enforcement of the ordering invariant.

## Impact

Silent auth gap on a misclassified route; silent data loss on a route-ordering
regression. Both are production-grade.

## Environment

- dadaia version: 0.1.5 + current `main`

## Fix direction

Collapse the three auth registries into one declarative route struct
`(pattern, name, auth_class)` where `auth_class ∈ {PUBLIC, BEARER,
BEARER_SECOND_LOOP, BEARER_TELEMETRY}`; the dispatch loop reads `auth_class`.
Give DELETE its own route table or anchor the ordering with a test. Add a unit
test asserting every route has an explicit auth classification.
