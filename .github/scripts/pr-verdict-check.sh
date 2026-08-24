#!/usr/bin/env bash
# pr-verdict-check.sh — the security-verdict PR gate's backend (v0.4.4 FR4, T-044-07).
#
# The diff-based security review that used to gate every push (pre-push hook, keyed on
# the pushed sha) is deleted from that path (A3.4, T-044-06) and relocates HERE — a CI
# job requiring an APPROVED security-reviewer verdict that covers the PR head sha,
# on feature -> develop and develop -> main (FR4).
#
# Verdict handoffs are LOCAL, workspace-level artifacts under `.dadaia/handoff/`
# (gitignored — see features/chokepoints/service.py's module docstring and
# `dadaia ci gc-push-verdicts`, which only ever reads a local clone). A GitHub Actions
# checkout never sees that directory, so the evidence THIS script reads is a COMMITTED
# copy of the security-reviewer's APPROVED handoff, placed on the branch at:
#
#   specs/releases/<release-id>/verdicts/<reviewed-sha>.handoff.json
#
# — the same "review artifact committed on the branch" cadence DADAIA.md §4 (Gitflow)
# already uses for a qa-engineer segment-close review.
#
# "Covers the PR head sha" (A4.3) cannot mean literal sha equality in the general
# case: committing the verdict file changes the tree, and therefore the sha, of
# whatever commit carries it — the reviewed commit can never retroactively include
# its own evidence. A verdict COVERS a PR head sha when:
#   1. its `metrics.commit_sha` IS the PR head sha, OR an ancestor of it, AND
#   2. every path that differs between the named sha and the PR head is itself under
#      specs/releases/*/verdicts/ — i.e. nothing but more verdict evidence landed
#      after the reviewed commit.
# This reuses the SAME qualification fields
# features/chokepoints/service.py::iter_security_approvals already applies to the
# (now push-retired, gc-only) local reader: agent == "security-reviewer",
# verdict == "APPROVED", a non-empty string metrics.commit_sha — one schema, two
# readers, never a second, drifted definition (A4.5).
#
# Usage (invoked from the repo root, as ci.yml's security-verdict-gate job does):
#   PR_HEAD_SHA=<sha> [RELEASE_ID=<id>] bash .github/scripts/pr-verdict-check.sh
#
# Environment variables:
#   PR_HEAD_SHA  required — the PR head sha to prove coverage for.
#   RELEASE_ID   optional — overrides the release id read from
#                specs/releases/ACTIVE.md's `release:` line.

set -euo pipefail

PR_HEAD_SHA="${PR_HEAD_SHA:?PR_HEAD_SHA is required}"
RELEASE_ID="${RELEASE_ID:-}"

if [ -z "$RELEASE_ID" ]; then
  if [ ! -f specs/releases/ACTIVE.md ]; then
    echo "::error::pr-verdict-check: RELEASE_ID not supplied and specs/releases/ACTIVE.md is missing — cannot resolve the active release."
    exit 1
  fi
  RELEASE_ID="$(sed -n 's/^release:[[:space:]]*//p' specs/releases/ACTIVE.md | head -1 | tr -d '[:space:]')"
fi

if [ -z "$RELEASE_ID" ]; then
  echo "::error::pr-verdict-check: could not resolve a release id (RELEASE_ID unset and specs/releases/ACTIVE.md carries no 'release:' line)."
  exit 1
fi

# RELEASE_ID is interpolated straight into a filesystem path below (VERDICTS_DIR) and,
# absent an override, is read from the PR head's OWN specs/releases/ACTIVE.md — so a
# PR that carries a crafted ACTIVE.md controls this value. Pin it to the release-id
# canon before it ever reaches a path, and fail closed on mismatch (no traversal
# shape, no unexpected characters). This mirrors, in bash, the ONE canonical pattern
# every other public entry point validates against
# (dadaia_workspace/core/specs_version.py::RELEASE_SEMVER_RE) — a bash script cannot
# import that Python object, so the pattern is restated here, not re-derived.
_RELEASE_ID_RE='^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z][0-9A-Za-z.]*)?$'
if ! [[ "$RELEASE_ID" =~ $_RELEASE_ID_RE ]]; then
  echo "::error::pr-verdict-check: RELEASE_ID '${RELEASE_ID}' does not match the canonical release-id pattern vMAJOR.MINOR.PATCH[-suffix] — refusing to interpolate it into a path."
  exit 1
fi

VERDICTS_DIR="specs/releases/${RELEASE_ID}/verdicts"
EXPECTED_SHAPE="${VERDICTS_DIR}/<reviewed-sha>.handoff.json (agent=\"security-reviewer\", verdict=\"APPROVED\", metrics.commit_sha=\"<reviewed-sha>\")"

if [ ! -d "$VERDICTS_DIR" ]; then
  echo "::error::pr-verdict-check: no APPROVED security-reviewer verdict covers PR head ${PR_HEAD_SHA} — expected one at ${EXPECTED_SHAPE} (directory not found)."
  exit 1
fi

pass=0
for handoff in "$VERDICTS_DIR"/*.handoff.json; do
  [ -e "$handoff" ] || continue

  agent="$(jq -r '.agent // empty' "$handoff" 2>/dev/null || true)"
  verdict="$(jq -r '.verdict // empty' "$handoff" 2>/dev/null || true)"
  sha="$(jq -r '.metrics.commit_sha // empty' "$handoff" 2>/dev/null || true)"

  if [ "$agent" != "security-reviewer" ] || [ "$verdict" != "APPROVED" ] || [ -z "$sha" ]; then
    echo "[pr-verdict-check] SKIP: ${handoff} (agent=${agent:-<none>} verdict=${verdict:-<none>} commit_sha=${sha:-<none>}) does not qualify."
    continue
  fi

  if ! git cat-file -e "${sha}^{commit}" 2>/dev/null; then
    echo "[pr-verdict-check] SKIP: ${handoff} names sha ${sha}, which is not a known commit in this checkout."
    continue
  fi

  if [ "$sha" != "$PR_HEAD_SHA" ] && ! git merge-base --is-ancestor "$sha" "$PR_HEAD_SHA" 2>/dev/null; then
    echo "[pr-verdict-check] SKIP: ${handoff}'s reviewed sha ${sha} is not an ancestor of PR head ${PR_HEAD_SHA}."
    continue
  fi

  offenders=""
  if [ "$sha" != "$PR_HEAD_SHA" ]; then
    # A command substitution used only to build a heredoc's body does NOT trip
    # `set -e` on failure — the heredoc is simply empty and the loop below sees no
    # offenders, silently converting "prove nothing unreviewed landed" into "assume
    # nothing did" (a real fail-open, reproduced against this exact shape). Capture
    # the output into a variable first and check its exit status explicitly, BEFORE
    # any of it is interpreted, so a git failure fails closed (SKIP this handoff)
    # instead of passing.
    if ! diff_output="$(git diff --name-only "$sha" "$PR_HEAD_SHA")"; then
      echo "[pr-verdict-check] SKIP: ${handoff} — 'git diff --name-only ${sha} ${PR_HEAD_SHA}' failed; cannot prove nothing unreviewed landed since the review, treating as non-qualifying."
      continue
    fi
    while IFS= read -r changed_path; do
      [ -z "$changed_path" ] && continue
      case "$changed_path" in
        specs/releases/*/verdicts/*) ;; # pure evidence — never disqualifies coverage.
        *) offenders="${offenders}${changed_path}"$'\n' ;;
      esac
    done <<< "$diff_output"
  fi

  if [ -n "$offenders" ]; then
    echo "[pr-verdict-check] SKIP: ${handoff}'s reviewed sha ${sha} does not cover PR head ${PR_HEAD_SHA} — unreviewed change(s) landed since the review:"
    echo "$offenders" | sed '/^$/d; s/^/    /'
    continue
  fi

  echo "[pr-verdict-check] PASS: ${handoff} — security-reviewer APPROVED ${sha}, which covers PR head ${PR_HEAD_SHA}."
  pass=1
  break
done

if [ "$pass" -ne 1 ]; then
  echo "::error::pr-verdict-check: no APPROVED security-reviewer verdict covers PR head ${PR_HEAD_SHA} — expected a qualifying file at ${EXPECTED_SHAPE}."
  exit 1
fi

echo "[pr-verdict-check] security-verdict-gate PASSED for PR head ${PR_HEAD_SHA} (release ${RELEASE_ID})."
