#!/usr/bin/env bash
# pr-verdict-check.sh — thin CLI wrapper (v0.5.1 K7, "split chokepoints.service into
# its four modules; one verdict store"). The security-verdict PR gate's backend is
# `dadaia ci verdict-check`, built over
# `features.chokepoints.verdict.covering_verdict` — the ONE rule reading the
# COMMITTED evidence at `specs/releases/<id>/verdicts/<sha>.handoff.json` (live) and
# `specs/releases/_archive/<id>/verdicts/<sha>.handoff.json` (archived). See that
# module's docstring for exactly what "covers PR_HEAD_SHA" means (v0.4.4 FR4; the
# two-hop head-or-first-parent model doctor_release's SPEC-DOC-044 already
# established).
#
# Usage (invoked from the repo root, as ci.yml's security-verdict-gate job does):
#   PR_HEAD_SHA=<sha> [RELEASE_ID=<id>] bash .github/scripts/pr-verdict-check.sh
#
# The caller's job installs the package first (`pip install -e .`) so `dadaia` is on
# PATH — see .github/workflows/ci.yml's security-verdict-gate job.

set -euo pipefail

PR_HEAD_SHA="${PR_HEAD_SHA:?PR_HEAD_SHA is required}"
RELEASE_ID="${RELEASE_ID:-}"

if [ -n "$RELEASE_ID" ] && [ "$RELEASE_ID" != "none" ]; then
  exec dadaia ci verdict-check --head "$PR_HEAD_SHA" --release-id "$RELEASE_ID"
fi
exec dadaia ci verdict-check --head "$PR_HEAD_SHA"
