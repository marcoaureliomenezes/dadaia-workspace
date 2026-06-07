#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

forbidden_tracked_regex='^(\.(claude|agents|codex|opencode)/|\.dadaia/|CLAUDE\.md$|opencode\.json$|Makefile$|playwright\.config\.ts$|playwright-report/|test-results/)'
tracked="$(git ls-files | grep -E "$forbidden_tracked_regex" || true)"

if [[ -n "$tracked" ]]; then
    printf 'ERROR: forbidden generated/local files are tracked:\n%s\n' "$tracked" >&2
    printf 'This repo is the dadaia-workspace source library. Generated consumer-workspace assets must not be versioned here.\n' >&2
    exit 1
fi

for path in .claude .agents .codex .opencode .dadaia CLAUDE.md opencode.json Makefile playwright.config.ts playwright-report test-results; do
    if [[ -e "$path" ]]; then
        printf 'ERROR: forbidden repo-root artefact exists: %s\n' "$repo_root/$path" >&2
        printf 'Run projection smoke tests in a temporary workspace, then remove generated root artefacts before finishing.\n' >&2
        exit 1
    fi
done

printf 'OK: repo-root generated projection/local artefacts are absent and untracked.\n'
