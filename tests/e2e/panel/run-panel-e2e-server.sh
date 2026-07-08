#!/usr/bin/env bash
# Hermetic bootstrap + launcher for the panel E2E webServer (v0.1.65 T-65-14
# amendment — CI fix for the agent-policy.spec.ts 500s).
#
# Root cause: the panel process resolves its `workspace_root` by walking up
# from its OWN process cwd at startup (core/workspace_resolver.
# resolve_workspace_root). The old harness launched the panel with
# `cwd == the dadaia-workspace repo checkout root` (playwright.config.ts's
# `webServer.cwd: REPO_ROOT`, paired with a CI bootstrap step that wrote
# `.dadaia/states/spec_contexts.json` directly at that same checkout root).
# That makes `workspace_root == the source repo root`, so ANY PUT that
# re-renders L1 projections (agent-model-policy Apply — T-65-14, T-65-11)
# is correctly refused by the `_is_source_repo_root` production guard
# (dadaia_workspace/infrastructure/public_assets.py `install()`) — a 500 in
# CI. Locally, the same cwd walk-up instead escapes the (unpolluted) repo
# checkout and finds the developer's own enclosing REAL dadaia-workspace
# instance, silently re-rendering their live `.claude/agents/*.md`.
#
# Fix: build a disposable, hermetic temp workspace that is NEVER the repo
# root and NEVER a real enclosing operator workspace, initialize it as a
# minimal dadaia-workspace, register THIS checkout as its sole ALIVE
# consumer repo (a `repos/dadaia-workspace` symlink — read-only consumption
# of the checkout's real specs/memory so the Projects tab has genuine data;
# `_is_self_repo` makes `install()` skip writing AGENTS.md/CLAUDE.md back
# into the checkout, so it is never touched), stage + install a real
# projection INTO the temp workspace, and exec the panel there.
#
# Env overrides:
#   PANEL_E2E_WS       Pin the temp workspace dir instead of mktemp (for
#                       local inspection / debugging). Left in place on exit
#                       (never deleted) so the operator can inspect it.
#   PANEL_E2E_PYTHON    Python invocation used to resolve the interpreter,
#                       e.g. "poetry run python" in CI. Default: "python"
#                       (assumes an already-activated venv, as this repo's
#                       own dev workflow does).
#   PANEL_TEST_PORT     Port the panel listens on. Default: 5065 (never
#                       4999 — that is the conventional operator-local panel
#                       port; see the release governance note on T-65-14).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
PY_RESOLVE_CMD="${PANEL_E2E_PYTHON:-python}"
PANEL_PORT="${PANEL_TEST_PORT:-5065}"

log() { echo "[panel-e2e] $*" >&2; }

# Resolve ONE absolute python executable, once, with cwd=REPO_ROOT (so a
# `poetry run` resolver can find pyproject.toml there). Every later
# invocation uses this absolute path directly — never `poetry run` again —
# so it never depends on cwd (the temp workspace has no pyproject.toml).
# shellcheck disable=SC2086
PYTHON_BIN="$(cd "$REPO_ROOT" && $PY_RESOLVE_CMD -c 'import sys; print(sys.executable)')"
log "resolved python: $PYTHON_BIN (via '${PY_RESOLVE_CMD}')"

TEMP_WS="${PANEL_E2E_WS:-}"
CREATED_TEMP_WS=0
if [ -z "$TEMP_WS" ]; then
  TEMP_WS="$(mktemp -d "${TMPDIR:-/tmp}/dadaia-panel-e2e-XXXXXX")"
  CREATED_TEMP_WS=1
fi
mkdir -p "$TEMP_WS"
log "hermetic e2e workspace: $TEMP_WS (created_here=${CREATED_TEMP_WS})"

# On a BOOTSTRAP failure only, remove a workspace we created ourselves — a
# caller-pinned PANEL_E2E_WS is never auto-deleted. This trap is cleared
# before the final `exec` below, so a normal panel shutdown (SIGTERM from
# playwright) never triggers it; the temp dir is left for post-mortem, same
# as this suite's existing OUTPUT_DIR/REPORT_DIR convention (os.tmpdir(),
# no cleanup — ephemeral scratch, OS/CI-runner reclaimed).
cleanup_on_bootstrap_failure() {
  status=$?
  if [ "$status" -ne 0 ] && [ "$CREATED_TEMP_WS" -eq 1 ]; then
    log "bootstrap failed (exit $status) — removing $TEMP_WS"
    rm -rf "$TEMP_WS"
  fi
}
trap cleanup_on_bootstrap_failure EXIT

# 1. Initialize a minimal workspace (assets staged/installed explicitly
#    below, not via --skip-assets's opposite — we want full control of the
#    order relative to the repos/ symlink + spec_contexts.json below).
"$PYTHON_BIN" -m dadaia_workspace.cli.main init --workspace "$TEMP_WS" --skip-assets

# 2. Register THIS checkout as the sole ALIVE consumer repo. The panel's
#    Projects/memory views read repos/<slug>/specs/** through this symlink;
#    `_is_self_repo` (workspace_guardrail.py) makes install() SKIP writing
#    AGENTS.md/CLAUDE.md back into it (self-projection) — the checkout is
#    read, never written.
mkdir -p "$TEMP_WS/repos"
ln -sfn "$REPO_ROOT" "$TEMP_WS/repos/dadaia-workspace"
cat > "$TEMP_WS/.dadaia/states/spec_contexts.json" <<JSON
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
      "current_branch": "e2e"
    }
  ]
}
JSON

# 3. Stage + install a real projection INTO the temp workspace — never into
#    the checkout. `workspace_root` here is $TEMP_WS, which is never
#    `_is_source_repo_root` (public_assets.py): it carries no pyproject.toml
#    and no dadaia_workspace/public dir. This is what the agent-policy
#    Apply re-render (`public install --target all --only agents`) expects
#    to already exist (staged plugin bodies, manifest.json, etc).
( cd "$TEMP_WS" && "$PYTHON_BIN" -m dadaia_workspace.cli.main public stage )
( cd "$TEMP_WS" && "$PYTHON_BIN" -m dadaia_workspace.cli.main public install --target all )

# Fast-fail: verify this checkout's own memory atoms are reachable through
# the repos/ symlink so data-dependent panel paths (memory chip clicks,
# Projects tab) run in CI. Mirrors the check the old
# `.github/scripts/bootstrap-panel-ws.sh` performed, adjusted for the
# repos/<slug>/ indirection (memory now lives one level down, behind the
# symlink, not at $TEMP_WS directly).
REPO_SYMLINK="$TEMP_WS/repos/dadaia-workspace"
for atom in specs/memory/architecture.md specs/memory/tech-stack.md specs/memory/product/index.md; do
  if [ ! -f "$REPO_SYMLINK/$atom" ]; then
    log "ERROR: $atom missing under $REPO_SYMLINK"
    exit 1
  fi
done
log "Memory atoms verified OK"

trap - EXIT

log "starting panel on port $PANEL_PORT (workspace_root=$TEMP_WS)"
cd "$TEMP_WS"
exec "$PYTHON_BIN" -m dadaia_workspace.cli.main panel --port "$PANEL_PORT" --no-open
