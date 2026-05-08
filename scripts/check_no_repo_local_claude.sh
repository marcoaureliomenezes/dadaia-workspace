#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
forbidden_path="$repo_root/.claude"

if [[ -e "$forbidden_path" ]]; then
    printf 'ERROR: forbidden repo-local path exists: %s\n' "$forbidden_path" >&2
    printf 'The only versioned source of agent assets is %s\n' "$repo_root/dadaia_workspace/public" >&2
    exit 1
fi

printf 'OK: repo-local .claude/ is absent. Product assets remain versioned only in %s\n' "$repo_root/dadaia_workspace/public"