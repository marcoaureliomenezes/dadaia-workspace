# ADR 0015 — The release-record envelope is closed

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
A governance record that accepts unknown fields drifts: each writer adds the key it needs, and
within a few releases no reader can trust the shape it folds. The milestone model is small on
purpose — a fixed set of event kinds marking defined, implemented-and-tested, shipped, and
audited — so an open envelope buys nothing and costs the audit its footing. Separately, a
harness `session_id` is agent-identity data with no governance meaning and a privacy cost; it
has no business in a record that is committed to the repository.

## Decision
We will close the release-record envelope: exactly the seven declared event kinds,
`additionalProperties: false` in the schema, and no harness `session_id` in any governance
record.

## Consequences
+ Readers fold a known shape; an unexpected key fails at the boundary instead of being
  silently ignored.
+ Committed governance records carry no session identity.
− A genuinely new milestone kind requires a schema change and a review — which is the point.

## Confirmation
Measured by: `pytest -p no:cacheprovider tests/contract/test_release_event_schema.py` (seven
kinds, closed envelope, `session_id` absent).
