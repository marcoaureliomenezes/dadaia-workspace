---
name: public-source-hygiene-flaky-pycache-pollution
status: Closed
severity: MEDIUM
reported: 2026-06-25
surface: tests/contract/test_public_source_hygiene.py (full-suite run) + public/scripts/*.py bytecode guard
session_id: null
---

**Symptom:** In a full `pytest` run of the whole suite, two contract tests in
`tests/contract/test_public_source_hygiene.py` FAIL:

- `test_no_bytecode_committed_under_public`
- `test_running_public_scripts_leaves_no_pycache`

Both fail because `dadaia_workspace/public/scripts/__pycache__/generate-memory-catalog.cpython-312.pyc`
exists at the time the contract test runs. Observed run:
`2 failed, 3348 passed, 11 skipped in 249.41s`.

**Repro:**
1. From a clean working tree (`rm -rf dadaia_workspace/public/scripts/__pycache__`), run
   the full suite: `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider -q`.
2. Observe the two `test_public_source_hygiene.py` failures.
3. Run the contract module alone on a clean tree
   (`pytest tests/contract/test_public_source_hygiene.py`) → 3 passed (no failure).
4. Running subsets (`tests/integration/scripts/ tests/unit/scripts/
   tests/contract/test_public_source_hygiene.py`) also pass — the pollution only
   manifests in the full-suite ordering.

**Expected:** The public-source-hygiene contract is order-independent: no test in the
suite leaves a `__pycache__` under `dadaia_workspace/public/scripts/`. The standalone
script `generate-memory-catalog.py` sets `sys.dont_write_bytecode = True` (line 60), but
a test that imports it via `importlib.util.spec_from_file_location(...)` (e.g.
`tests/integration/scripts/test_generate_memory_catalog.py:40`) — or another importer in
the full-run ordering — can cause CPython to write the module's own bytecode *before* the
in-module guard line executes, polluting `public/scripts/`.

**Notes / scope:**
- **Pre-existing, NOT introduced by release v0.1.18.** The three involved files
  (`public/scripts/generate-memory-catalog.py`,
  `tests/integration/scripts/test_generate_memory_catalog.py`,
  `tests/contract/test_public_source_hygiene.py`) are byte-identical to the release base
  `f980cd7` (`git diff f980cd7..97cd5f6 -- <those> | wc -l` = 0). The v0.1.18 NEW tests
  (`test_catalog.py`, `test_lint_memory_atoms.py`) do NOT pollute `public/scripts/` when
  run in isolation (verified clean).
- The polluting artifact is **untracked / gitignored** — never committed, never in any
  release diff. It is purely a working-tree/CI-run pollution.
- **Impact on the push gate:** the pre-push `dadaia ci preflight` runs the full suite, so
  this flake can intermittently RED the push gate for any release. Recommend fixing before
  the v0.1.18 push (rc boundary), not as an alpha-gate blocker.
- **Suggested fixes:** (a) make `test_generate_memory_catalog.py` (and any other importer
  of a `public/scripts/*.py`) import under `sys.dont_write_bytecode = True` set in the test
  module *before* the `spec_from_file_location` exec, or run the script only via
  `subprocess … -B`; and/or (b) add a session-scoped autouse fixture that asserts/cleans
  `public/**/__pycache__` so the hygiene contract is deterministic regardless of ordering;
  and/or (c) move the bytecode guard to the script's `#!`/`-B` invocation contract and have
  the contract test tolerate a transient cache it cleans in teardown.
- Found during the v0.1.18 (`pi-operational-two-layer`) alpha QA gate, 2026-06-25.
