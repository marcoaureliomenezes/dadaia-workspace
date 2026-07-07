#!/usr/bin/env bash
# Bootstrap a self-hosting panel workspace for the e2e-panel CI legs.
# Shared by .github/workflows/ci.yml and .github/workflows/release.yml (v0.1.61 CI-2).
set -euo pipefail

poetry run python -m dadaia_workspace.cli.main init --workspace "$PWD" --skip-assets
poetry run python -m dadaia_workspace.cli.main public stage
mkdir -p repos
ln -sfn "$PWD" repos/dadaia-workspace
cat > .dadaia/states/spec_contexts.json <<JSON
{
  "schema_version": "2",
  "contexts": [
    {
      "name": "dadaia-workspace",
      "state": "alive",
      "repo_slug": "dadaia-workspace",
      "repo_url": "https://github.com/marcoaureliomenezes/dadaia-workspace.git",
      "created_at": "2026-06-03T00:00:00+00:00",
      "alive_since": "2026-06-03T00:00:00+00:00",
      "dead_since": null,
      "current_branch": "main"
    }
  ]
}
JSON
# Fast-fail: verify the repo's own memory atoms are accessible so
# data-dependent panel paths (memory chip clicks) run in CI.
test -f "$PWD/specs/memory/architecture.md" || \
  { echo "ERROR: specs/memory/architecture.md missing"; exit 1; }
test -f "$PWD/specs/memory/tech-stack.md" || \
  { echo "ERROR: specs/memory/tech-stack.md missing"; exit 1; }
test -f "$PWD/specs/memory/product/index.md" || \
  { echo "ERROR: specs/memory/product/index.md missing"; exit 1; }
echo "Memory atoms verified OK"
