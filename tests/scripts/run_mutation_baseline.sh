#!/usr/bin/env bash
# Mutation-testing baseline runner (FR20, v0.4.3 T-043-28).
#
# Invoked manually, once per release, OFF THE PUSH PATH — never referenced from
# ci.yml, release.yml, or the local pre-push preflight (verify with:
#   grep -rn 'run_mutation_baseline\|mutmut' .github/workflows/*.yml \
#     dadaia_workspace/features/ci_preflight/
# ). Captures the mutation score for `dadaia_workspace/core/models/` against
# `tests/unit/core/models/` as evidence, never as a merge/push gate.
#
# Selection verdict (tool = mutmut 3.7.0, scope, config):
#   .dadaia/tmp/qa-engineer/20260817/v0.4.3-T-043-28-mutation-tool-verdict.md §3-4
#
# SCOPE NARROWING (recorded per the wiring dispatch's explicit bounded-run clause).
# The verdict recommended `dadaia_workspace/core/` (57 files) + `tests/unit/core/` as
# the first baseline, with `core/models/` + `tests/unit/core/models/` as its OWN already
# -validated smoke-trial sub-slice (§3.1: 207 mutants, 66 killed, 17 survived, 124
# no_tests, 2.47s). The wider `core/` scope was attempted first at wiring time and hit a
# structural wall the verdict's trial never had to face: mutmut's `mutants/` execution
# sandbox mirrors ONLY `source_paths` on disk (verified directly — it never contains
# `features/`, `hooks/`, `cli/`, `infrastructure/`, regardless of what this script
# stages alongside it), and `tests/unit/core/` (flat, non-`models/`) contains real
# cross-layer architecture/consistency tests by design, not test-isolation bugs:
#   - test_harness_registry.py::test_roster_literal_absent_and_registry_consumed reads
#     `dadaia_workspace/features/**` source by path (a repo-wide grep-style check).
#   - test_kernel_tunables.py's parametrized cases `importlib.import_module(...)` real
#     `dadaia_workspace.hooks.*` / other-layer modules (a single-source-of-truth check).
# Excluding one file at a time is whack-a-mole against tests that are correctly placed
# for the NORMAL gating suite but structurally incompatible with ANY mutmut sandbox
# scoped narrower than the whole package. Widening this script's scope back to the full
# `core/` (auditing every `tests/unit/core/**` file for cross-layer reads/imports, or
# staging the full `tests/` tree + full dependency set) is real, boundable follow-up
# work — tracked as a natural next-release refinement, not done here. This script ships
# on the verdict's OWN already-clean scope, once per release, off the push path,
# evidence-only.
#
# WHY a staged copy at all: mutmut's `mutants/` sandbox directory is hardcoded relative
# to its invocation cwd, with no config key to redirect it (mutmut's own
# configuration.py:107). Running it with cwd = repo root would create `mutants/` and a
# mutation cache tree inside the repo, violating this workspace's "no caches in the repo
# tree" law (DADAIA.md §4). This script therefore stages a scoped copy under
# `.dadaia/tmp/`, creates a throwaway venv and runs mutmut entirely inside that staged
# copy, and copies back only the JSON stats. It NEVER writes inside the repo tree.
#
# Usage:
#   tests/scripts/run_mutation_baseline.sh [output-filename.json]
#
# Env:
#   DADAIA_MUTATION_STAGE_ONLY=1   Stage the scoped copy and the generated
#                                  pyproject.toml, then exit 0 WITHOUT creating a venv
#                                  or invoking mutmut. Used by the wiring test
#                                  (tests/integration/scripts/
#                                  test_run_mutation_baseline_wiring.py) to prove the
#                                  staging step never touches the repo tree, without
#                                  paying for a real venv + network install.
set -euo pipefail

OUTPUT_NAME="${1:-mutation-baseline.json}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"                    # repos/dadaia-workspace
# DADAIA_WORKSPACE_ROOT override: staging/output destination only (source files always
# come from the real REPO above). Lets the wiring test isolate staged output under a
# fake tmp_path tree without touching the real workspace's .dadaia/tmp/.
WORKSPACE_ROOT="${DADAIA_WORKSPACE_ROOT:-$(cd "$REPO/../.." && pwd)}"
DATE_STAMP="$(date -u +%Y%m%d)"
OUT_DIR="$WORKSPACE_ROOT/.dadaia/tmp/software-engineer/$DATE_STAMP"
STAGE_ABS="$OUT_DIR/mutation-run"
# Resolve the EXACT interpreter the workspace venv itself was built from, via its own
# pyvenv.cfg `executable =` line, rather than invoking `.dadaia/.venv/bin/python -m venv`
# directly. On this host, chaining `-m venv` off a venv's own python resolves the base
# interpreter through pyvenv.cfg's `home` field and a generic `python3` lookup in that
# directory — which silently picked up `/usr/bin/python3` (Python 3.10, this host's
# default `python3` symlink) instead of the pinned 3.12, even with `--copies`
# (reproduced: both symlink and copy modes land on 3.10). Reading `executable =` gives
# the real path (`/usr/bin/python3.12` on this host) and sidesteps the nested-venv
# resolution entirely. Never hardcode a `python3.12` path — always derive it here.
WORKSPACE_VENV_CFG="$WORKSPACE_ROOT/.dadaia/.venv/pyvenv.cfg"
if [ -f "$WORKSPACE_VENV_CFG" ]; then
  MUTATION_VENV_PYTHON="$(grep '^executable' "$WORKSPACE_VENV_CFG" | cut -d= -f2 | tr -d ' ')"
else
  MUTATION_VENV_PYTHON="$WORKSPACE_ROOT/.dadaia/.venv/bin/python"
fi

rm -rf "$STAGE_ABS"
mkdir -p "$STAGE_ABS/dadaia_workspace/core" "$STAGE_ABS/tests/unit/core"
cp -r "$REPO/dadaia_workspace/core/models" "$STAGE_ABS/dadaia_workspace/core/models"
cp -r "$REPO/tests/unit/core/models"       "$STAGE_ABS/tests/unit/core/models"
touch "$STAGE_ABS/dadaia_workspace/__init__.py" "$STAGE_ABS/dadaia_workspace/core/__init__.py" \
      "$STAGE_ABS/tests/__init__.py" "$STAGE_ABS/tests/unit/__init__.py" \
      "$STAGE_ABS/tests/unit/core/__init__.py"

cat > "$STAGE_ABS/pyproject.toml" <<'TOML'
[tool.mutmut]
source_paths = ["dadaia_workspace/core/models"]
pytest_add_cli_args_test_selection = ["tests/unit/core/models"]
mutate_only_covered_lines = true
use_git_change_detection = false
timeout_multiplier = 15.0
timeout_constant = 1.0
TOML

if [ "${DADAIA_MUTATION_STAGE_ONLY:-0}" = "1" ]; then
  echo "DADAIA_MUTATION_STAGE_ONLY=1 — staged at $STAGE_ABS, stopping before venv/mutmut."
  exit 0
fi

cd "$STAGE_ABS"
"$MUTATION_VENV_PYTHON" -m venv .mutmut-venv
.mutmut-venv/bin/python --version
# mutmut + pytest (the tool). `dadaia_workspace/core/models/` + `tests/unit/core/
# models/` import nothing beyond stdlib + pytest (verified: no third-party top-level
# import across either tree) and nothing outside `core/` (constitution layering) —
# this staged subset needs no more than the tool itself.
.mutmut-venv/bin/pip install --quiet mutmut==3.7.0 pytest
.mutmut-venv/bin/mutmut run
.mutmut-venv/bin/mutmut export-cicd-stats

mkdir -p "$OUT_DIR"
cp mutants/mutmut-cicd-stats.json "$OUT_DIR/$OUTPUT_NAME"

echo "Mutation baseline stats copied to $OUT_DIR/$OUTPUT_NAME"
