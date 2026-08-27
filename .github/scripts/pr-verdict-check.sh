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
# already uses for a qa-engineer segment-close review. At release closure, the whole
# release directory (verdicts included) is `git mv`'d verbatim to
# `specs/releases/_archive/<release-id>/verdicts/` (canon v6, T-050-06A — one level
# DEEPER than the pre-v6 `specs/_archive/releases/<release-id>/verdicts/` layout) — so
# a PASSING PR against a closed release (the final-rc PR, and every develop -> main
# deploy PR) must resolve its evidence there too.
#
# Bug `verdict-gate-cannot-resolve-evidence-after-release-archive` (HIGH, T-044-50):
# the gate used to resolve `RELEASE_ID` by reading `specs/releases/ACTIVE.md`'s
# `release:` line, which legitimately reads `none` once the release is closed — a
# LIFECYCLE POINTER, not the evidence itself. `none` fails the release-id canon and
# the script exited before ever reading a directory, making every closure/deploy PR
# permanently ungateable regardless of where evidence was placed. The fix removes
# that pointer read entirely: evidence is resolved BY THE ARTIFACT — a glob over
# every release's verdicts directory, live and archived — never by asking a lifecycle
# document which release is "active". `RELEASE_ID` survives only as an OPTIONAL
# narrowing (see below); it is never required and its absence/`none` is never an
# error, and it is never itself an "is a verdict required" gate — a qualifying
# handoff must still be found, or the gate fails closed.
#
# "Covers the PR head sha" (A4.3) cannot mean literal sha equality in the general
# case: committing the verdict file changes the tree, and therefore the sha, of
# whatever commit carries it — the reviewed commit can never retroactively include
# its own evidence. A verdict COVERS a PR head sha when:
#   1. its `metrics.commit_sha` IS the PR head sha, OR an ancestor of it, AND
#   2. every path that differs between the named sha and the PR head is itself under
#      specs/releases/*/verdicts/ OR specs/releases/_archive/*/verdicts/ (a bash
#      `case` pattern's `*` crosses `/`, so this ALREADY matches the per-area
#      archive shape below — verified, not part of the T-050-06A defect, and left
#      untouched here) — i.e. nothing but more verdict evidence landed after the
#      reviewed commit.
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
#   RELEASE_ID   optional narrowing only. Unset, empty, or the literal "none"
#                (the exact value ACTIVE.md carries at closure) means: search every
#                release's verdicts directory, live and archived — never an error.
#                A value matching the release-id canon (derived below) restricts the
#                search to that one release id, in both trees. Any other value is
#                refused before it ever reaches a path (no traversal shape, no
#                unexpected characters).
#
# T-050-06A (SPEC FR1 boundary 2a / AS-13 / §9.2 SEC-R1/SEC-R2): the id pattern and
# the two evidence roots below are DERIVED from the canon
# (dadaia_workspace/core/specs_version.py), never hard-coded — the third firing of
# `verdict-gate-cannot-resolve-evidence-after-release-archive` (HIGH, T-044-50) was
# caused by a canon move (v6's per-area archive: specs/releases/_archive/<id>/
# instead of specs/_archive/releases/<id>/) leaving this script's own hard-coded
# glob and `v`-required id pattern behind, exactly as it did twice before. Bash
# cannot `import` the Python object, so it shells out to the interpreter instead
# (feasible on the bare checkout: `security-verdict-gate` runs with no
# `setup-python`/install step, and both `dadaia_workspace/__init__.py` and
# `core/__init__.py` are empty while `core/specs_version.py` imports only stdlib
# `re` + `pathlib`).

set -euo pipefail

PR_HEAD_SHA="${PR_HEAD_SHA:?PR_HEAD_SHA is required}"
RELEASE_ID="${RELEASE_ID:-}"

# Self-locate the package, never rely on the caller's cwd (bug
# pr-verdict-check-wiring-fixture-lacks-cwd-relative-dadaia-workspace-package): the
# canon derivation below imports `dadaia_workspace.core.specs_version`, a pure
# module whose output never depends on which repo instance invokes this script — it
# is always this script's OWN sibling package, never the caller's cwd. CWD-relative
# `python3 -c` resolution happened to work because every real CI invocation's cwd is
# already the checkout root (`security-verdict-gate` runs `bash
# .github/scripts/pr-verdict-check.sh` with no `working-directory:` override) — but
# that made the derivation's correctness an incidental property of the caller's cwd
# rather than a property of the script itself, exactly the assumption a synthetic
# git-repo fixture (a throwaway tmp_path repo with no dadaia_workspace/ tree at all)
# legitimately does not share. `PYTHONPATH` is set to this script's own repo root
# (derived from `BASH_SOURCE[0]`, never `$0` — robust if this script is ever
# sourced) so the derivation resolves identically regardless of cwd; every later git
# operation in this script still runs against the CALLER's cwd (the checked-out PR
# tree in CI, the synthetic fixture repo in tests) — only the python3 import path is
# self-located, nothing else.
_SCRIPT_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Derive the id pattern + the exactly-two verdict-evidence root templates from the
# canon. Fail-closed (SPEC §9.2 SEC-R2): interpreter absent, import error, missing
# symbol, or empty/unparseable output all exit non-zero with the reason — there is
# NO `|| <default glob>`, no fallback root, no "assume the old pattern". `_ideas/` is
# never a root here BY CONSTRUCTION — it is not one of the two templates the canon
# exports (AS-15/A6.3: a freely-writable directory is never a trust root of a
# required check) — so no separate `_ideas` refusal line is needed for the roots
# themselves; the id-pattern check below still refuses the literal token
# "_ideas"/"_archive" (or any traversal shape) before it is ever interpolated,
# because none of those strings can match a release-id pattern.
if ! _CANON_OUTPUT="$(PYTHONPATH="${_SCRIPT_REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" python3 -c '
import dadaia_workspace.core.specs_version as s
print(s.release_semver_ere_pattern())
for template in s.VERDICT_EVIDENCE_ROOT_TEMPLATES:
    print(template)
' 2>&1)"; then
  echo "::error::pr-verdict-check: could not derive the release-id pattern and verdict-evidence roots from dadaia_workspace.core.specs_version — refusing to fall back to a hard-coded glob. Interpreter/import output: ${_CANON_OUTPUT}"
  exit 1
fi

_CANON_LINE_COUNT="$(printf '%s\n' "$_CANON_OUTPUT" | sed '/^$/d' | wc -l | tr -d ' ')"
if [ "$_CANON_LINE_COUNT" -ne 3 ]; then
  echo "::error::pr-verdict-check: expected 1 id pattern + exactly 2 verdict-evidence root templates from the canon, got ${_CANON_LINE_COUNT} non-empty line(s): ${_CANON_OUTPUT}"
  exit 1
fi

_RELEASE_ID_RE="$(printf '%s\n' "$_CANON_OUTPUT" | sed -n '1p')"
_ROOT_TEMPLATE_1="$(printf '%s\n' "$_CANON_OUTPUT" | sed -n '2p')"
_ROOT_TEMPLATE_2="$(printf '%s\n' "$_CANON_OUTPUT" | sed -n '3p')"
if [ -z "$_RELEASE_ID_RE" ] || [ -z "$_ROOT_TEMPLATE_1" ] || [ -z "$_ROOT_TEMPLATE_2" ]; then
  echo "::error::pr-verdict-check: the canon derivation produced an empty id pattern or root template — refusing to interpolate an empty value into a path."
  exit 1
fi

# RELEASE_ID, when supplied, is interpolated straight into the derived root
# templates below — so a PR that supplies (or, upstream, a crafted ACTIVE.md that
# fed) this value controls a path. Pin it to the derived release-id canon before it
# ever reaches a path, and fail closed on mismatch (no traversal shape, no
# unexpected characters — "_ideas", "_archive", "../" and every other non-canon
# token are refused here, since none of them can match a release-id pattern).
# "none" (unset/empty's sibling — the literal ACTIVE.md carries at closure) is
# deliberately exempt from this check: it means "no narrowing", not "malformed
# value".
RELEASE_GLOB='*'
if [ -n "$RELEASE_ID" ] && [ "$RELEASE_ID" != "none" ]; then
  if ! [[ "$RELEASE_ID" =~ $_RELEASE_ID_RE ]]; then
    echo "::error::pr-verdict-check: RELEASE_ID '${RELEASE_ID}' does not match the canon-derived release-id pattern (${_RELEASE_ID_RE}) — refusing to interpolate it into a path."
    exit 1
  fi
  RELEASE_GLOB="$RELEASE_ID"
fi

EXPECTED_SHAPE="specs/releases/<release-id>/verdicts/<reviewed-sha>.handoff.json or specs/releases/_archive/<release-id>/verdicts/<reviewed-sha>.handoff.json (agent=\"security-reviewer\", verdict=\"APPROVED\", metrics.commit_sha=\"<reviewed-sha>\")"

# Resolve candidate verdict files BY THE ARTIFACT, never by a lifecycle pointer:
# every release's verdicts directory under the two canon-derived roots, live and
# per-area archived, optionally narrowed by RELEASE_ID. `nullglob` makes a
# directory that does not exist (or a release id with no verdicts at all)
# contribute zero candidates rather than a literal, unexpanded glob string.
# Deliberately UNQUOTED: RELEASE_GLOB is either the literal wildcard `*` or a value
# already validated against `_RELEASE_ID_RE` above (digits/dots/hyphens/alnum only,
# never whitespace or another shell metacharacter) — quoting it here would turn the
# intentional `*` into a literal asterisk character and silently match nothing
# (verified: this exact bug reproduced and was fixed on this line).
shopt -s nullglob
CANDIDATES=(
  ${_ROOT_TEMPLATE_1/\{glob\}/$RELEASE_GLOB}/*.handoff.json
  ${_ROOT_TEMPLATE_2/\{glob\}/$RELEASE_GLOB}/*.handoff.json
)
shopt -u nullglob

if [ "${#CANDIDATES[@]}" -eq 0 ]; then
  echo "::error::pr-verdict-check: no APPROVED security-reviewer verdict covers PR head ${PR_HEAD_SHA} — expected one at ${EXPECTED_SHAPE} (no candidate verdict files found)."
  exit 1
fi

pass=0
for handoff in "${CANDIDATES[@]}"; do
  agent="$(jq -r '.agent // empty' "$handoff" 2>/dev/null || true)"
  verdict="$(jq -r '.verdict // empty' "$handoff" 2>/dev/null || true)"
  sha="$(jq -r '.metrics.commit_sha // empty' "$handoff" 2>/dev/null || true)"

  if [ "$agent" != "security-reviewer" ] || [ "$verdict" != "APPROVED" ] || [ -z "$sha" ]; then
    echo "[pr-verdict-check] SKIP: ${handoff} (agent=${agent:-<none>} verdict=${verdict:-<none>} commit_sha=${sha:-<none>}) does not qualify."
    continue
  fi

  # T-044-46 S-1: metrics.commit_sha must be a 40-hex SHA-1 object id before it
  # reaches any git argv. Without this, a symbolic or option-shaped value —
  # "HEAD", "@", "--glob=..." — resolves dynamically against whatever the CI job's
  # checkout happens to have at HEAD. Inside the job the checkout puts HEAD at the
  # PR head sha, so an unvalidated "HEAD" IS the PR head: both the ancestor check
  # and the diff-emptiness check below collapse into tautologies (a commit is
  # trivially its own ancestor, and the diff against itself is empty), letting an
  # unreviewed PR head PASS. Mirrors features/chokepoints/service.py's
  # _SHA_SHAPE_RE — the 40-hex arm only: `git rev-parse --show-object-format`
  # confirms this repository is sha1, so the chokepoint's 64-hex/SHA-256 arm could
  # never resolve a real commit here and is deliberately not mirrored.
  if ! [[ "$sha" =~ ^[0-9a-fA-F]{40}$ ]]; then
    echo "[pr-verdict-check] SKIP: ${handoff} names commit_sha '${sha}', which is not a 40-hex sha — refusing to pass it to git."
    continue
  fi

  if ! git cat-file -e -- "${sha}^{commit}" 2>/dev/null; then
    echo "[pr-verdict-check] SKIP: ${handoff} names sha ${sha}, which is not a known commit in this checkout."
    continue
  fi

  if [ "$sha" != "$PR_HEAD_SHA" ] && ! git merge-base --is-ancestor -- "$sha" "$PR_HEAD_SHA" 2>/dev/null; then
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
    if ! diff_output="$(git diff --name-only "$sha" "$PR_HEAD_SHA" --)"; then
      echo "[pr-verdict-check] SKIP: ${handoff} — 'git diff --name-only ${sha} ${PR_HEAD_SHA}' failed; cannot prove nothing unreviewed landed since the review, treating as non-qualifying."
      continue
    fi
    while IFS= read -r changed_path; do
      [ -z "$changed_path" ] && continue
      case "$changed_path" in
        specs/releases/*/verdicts/*|specs/_archive/releases/*/verdicts/*)
          ;; # pure evidence, live or archived — never disqualifies coverage.
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

echo "[pr-verdict-check] security-verdict-gate PASSED for PR head ${PR_HEAD_SHA} (release filter: ${RELEASE_GLOB})."
