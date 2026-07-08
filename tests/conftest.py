"""Root conftest.py — workspace-level pytest fixtures.

TR-3 (T-GOS-A4): repo-root write-backstop guard.

This fixture captures the set of entries present in specific protected directories
at the lib repo root BEFORE each test and asserts that no NEW entries have appeared
in those directories AFTER the test completes.

The guard is intentionally scope=``function`` and autouse=True so it fires around
every test in the suite.  It is implemented as a *root-write guard only* — it does
NOT force-chdir tests to a temporary directory (that would break tests that rely on
their own CWD assumptions).

Protected paths (relative to the repo root, checked recursively):
  .claude/
  .agents/
  .codex/
  .dadaia/

Protected root files:
  CLAUDE.md
  Makefile
  playwright.config.ts

Session-level pollution guard (_session_root_pollution_guard):
  Fails the test session (not just warns) if any of the following directories
  exist at the repo root AFTER the full test run:
    .dadaia  .venv  .pytest_cache  .mypy_cache  .hypothesis  .ruff_cache  test-results
  These are created by tools running with the wrong working directory or misconfigured
  cache settings.  Their presence means a test escaped the tmp_path sandbox or a tool
  was invoked without the appropriate no-cache flags.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Repo-cleanliness law: the test run must never materialize bytecode caches inside
# the working tree. Import-time compilation happens BEFORE any in-script
# ``sys.dont_write_bytecode`` guard can run (e.g. tests importing the
# ``public/scripts/*.py`` sources), so the suite-wide switch is the only reliable
# enforcement point (AC-W5-01).
sys.dont_write_bytecode = True

# ---------------------------------------------------------------------------
# Hypothesis: redirect storage dir and disable the on-disk database so
# .hypothesis/ is never created inside the repo.
#
# Two layers of protection:
#   1. set_hypothesis_home_dir(tmpdir) — redirects the unicode_data cache and
#      any other hypothesis storage away from CWD (.hypothesis/) to a tmpdir.
#      This must happen BEFORE hypothesis initialises its storage (i.e. before
#      any @given test is collected), which is why it is at module-import time.
#   2. settings profile "no_db" with database=None — ensures the examples
#      database is not written even if the storage dir redirect ever fails.
#
# Import is lazy so that environments without hypothesis installed do not fail
# at collection time.
# ---------------------------------------------------------------------------
try:
    import tempfile

    import hypothesis.configuration as _hyp_cfg
    from hypothesis import HealthCheck, Phase, settings

    # Redirect ALL hypothesis storage to a temp dir outside the repo.
    _hyp_cfg.set_hypothesis_home_dir(tempfile.mkdtemp(prefix="dadaia-hypothesis-"))

    settings.register_profile(
        "no_db",
        database=None,
        suppress_health_check=[HealthCheck.too_slow],
        phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink],
    )
    settings.load_profile("no_db")
except ImportError:
    pass  # hypothesis not installed — nothing to configure

# ---------------------------------------------------------------------------
# Resolve repo root once at import time.
# tests/ lives one level below the repo root, so __file__/../.. is the root.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent.resolve()

# Directories that MUST NOT exist at the repo root after a test session.
# Their presence means a tool was invoked with the wrong CWD or without the
# appropriate no-cache flags, polluting the working tree.
_POLLUTION_DIRS: tuple[str, ...] = (
    ".dadaia",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".hypothesis",
    ".ruff_cache",
    "test-results",
)

# Directories (relative to repo root) whose contents must not grow during a test.
_GUARDED_DIRS: tuple[str, ...] = (
    ".claude",
    ".agents",
    ".codex",
    ".dadaia",
)

_GUARDED_ROOT_FILES: tuple[str, ...] = (
    "CLAUDE.md",
    "Makefile",
    "playwright.config.ts",
)

_PATH_MARKERS: tuple[tuple[str, str], ...] = (
    ("tests/unit/", "unit"),
    ("tests/contract/", "contract"),
    ("tests/integration/", "integration"),
    ("tests/e2e/", "e2e"),
    ("tests/tmp/", "tmp"),
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Apply layer markers from test directory layout.

    Directory placement is the first enforcement mechanism for the existing
    suite. Tests may still add explicit markers, but unmarked legacy tests do
    not fall out of layer-specific commands.
    """
    for item in items:
        rel = Path(str(item.fspath)).resolve().relative_to(_REPO_ROOT).as_posix()
        for prefix, marker in _PATH_MARKERS:
            if rel.startswith(prefix):
                item.add_marker(getattr(pytest.mark, marker))
                if marker == "e2e":
                    item.add_marker(pytest.mark.slow(reason="e2e process-boundary suite"))
                break


def _collect_entries(
    root: Path, rel_dirs: tuple[str, ...], rel_files: tuple[str, ...]
) -> frozenset[str]:
    """Return the set of all file paths (as strings) within the guarded dirs."""
    entries: set[str] = set()
    for rel in rel_dirs:
        guarded = root / rel
        if not guarded.exists():
            continue
        for path in guarded.rglob("*"):
            if path.is_file():
                entries.add(str(path))
    for rel in rel_files:
        guarded_file = root / rel
        if guarded_file.exists() and guarded_file.is_file():
            entries.add(str(guarded_file))
    return frozenset(entries)


@pytest.fixture(autouse=True)
def _no_real_venv_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disk guard: never build a real Python venv during the test suite.

    `WorkspaceService.init()` calls `VenvPythonEnvironmentManager.ensure_workspace_venv`,
    which runs `venv.create(..., with_pip=True)` — a ~30-50 MB venv + ensurepip PER call.
    ~20 integration/e2e `workspace` fixtures call `.init()`, so each full-suite run built
    hundreds of venvs into `tmp_path`; with pytest retaining the last runs, this filled the
    disk (ENOSPC) and made the suite take 15-24 min. No test asserts venv contents or execs
    the venv python, so we replace the builder with a no-op that just materialises the
    directory and returns its path (matching FakePythonEnvironmentManager's behaviour).
    """
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    def _fake_ensure(self: object, workspace_root: str) -> str:  # noqa: ANN001
        venv_dir = Path(workspace_root) / ".dadaia" / ".venv"
        venv_dir.mkdir(parents=True, exist_ok=True)
        return str(venv_dir)

    monkeypatch.setattr(
        VenvPythonEnvironmentManager, "ensure_workspace_venv", _fake_ensure, raising=True
    )


@pytest.fixture(autouse=True)
def _scrub_entry_signal_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-4 hermeticity envelope (v0.1.64 FR3): scrub the entry-harness signal vars.

    A developer running pytest inside a codex TUI carries ``CODEX_SESSION_ID`` (and a PI
    session may carry the ``DADAIA_ENTRY_HARNESS`` Ring-1 pin). With the lifecycle
    ``--harness`` default now ``auto``, an unscrubbed suite would auto-default a REAL,
    credit-spending worker from any test invoking a lifecycle verb without ``--harness``.
    This scrub makes every test resolve ``fake`` unless it sets a signal explicitly.
    """
    from tests.fixtures.harness_env import scrub_entry_signal_env

    scrub_entry_signal_env(monkeypatch)


_LIVE_OPT_IN_FLAGS: tuple[str, ...] = (
    "DADAIA_E2E_REAL_WORKER",
    "DADAIA_PI_LIVE",
    "DADAIA_CODEX_LIVE",
    "DADAIA_CLAUDE_LIVE",
)


def _real_worker_opt_in() -> bool:
    """Single named predicate: True iff ANY live-opt-in flag is set to "1".

    v0.1.67 FR3 (T-67-08, F1-corrected): the union of ALL FOUR established
    opt-in flags used across ``tests/integration/{pi,codex,claude}_live/`` —
    ``DADAIA_E2E_REAL_WORKER`` (pi_live smoke + e2e), ``DADAIA_PI_LIVE``
    (pi_live contract), ``DADAIA_CODEX_LIVE`` (codex_live), ``DADAIA_CLAUDE_LIVE``
    (claude_live). A guard keyed on a single flag would false-block a
    legitimate ``DADAIA_CODEX_LIVE=1`` run of the codex_live suite — this is
    the specific regression the architect review's F1 finding identified.
    """
    import os

    return any(os.environ.get(flag) == "1" for flag in _LIVE_OPT_IN_FLAGS)


@pytest.fixture(autouse=True)
def _real_worker_guard(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR3 (DEC-C) real-binary guardrail: fail loud instead of silently spawning the
    real ``pi``/``codex`` binary when a test constructs ``PiHeadlessAdapter`` or
    ``CodexExecAdapter`` with no explicit ``runner=`` and no live-opt-in flag is set.

    Patches ``PiHeadlessAdapter._resolve_runner`` / ``CodexExecAdapter._resolve_runner``
    (the call-time indirection FR1 — T-67-02/T-67-04 — introduced) to a sentinel that
    raises ``RuntimeError`` unless :func:`_real_worker_opt_in` returns ``True``.

    Deliberately NOT a patch of the module-qualified ``subprocess.run`` attribute
    (``pi_runtime.subprocess.run`` / ``codex_runtime.subprocess.run``): a Python module
    import is a process-wide singleton, so ``pi_runtime.subprocess IS subprocess``
    (the same object as the stdlib ``subprocess`` module) — patching that attribute
    patches the GLOBAL ``subprocess.run`` for the entire test process, breaking every
    unrelated test that legitimately shells out (git operations, CLI probes, the
    pre-push gate's own subprocess tests, etc.) — confirmed by a full-suite regression
    run during T-67-08 development (177 unrelated failures). Patching the two adapter
    CLASSES' ``_resolve_runner`` bound methods is scoped exclusively to
    ``PiHeadlessAdapter``/``CodexExecAdapter`` instances and leaves the shared
    ``subprocess`` module completely untouched, while still firing before any real
    subprocess is spawned (the same enforcement point FR1's call-time resolution
    created). A test that injects ``runner=fake_...`` explicitly at construction is
    UNAFFECTED: the replacement below re-checks ``self._runner is not None`` and
    returns the injected fake unchanged in that case — only the ``None`` (no explicit
    runner) branch is replaced with the raising sentinel, mirroring the original
    ``_resolve_runner`` body exactly except for its fallback target. The ``*_live/``
    suites set their own opt-in flag before invoking a real adapter, so this guard
    never fires there.

    **Narrow, explicit, per-test opt-out (NOT a blanket exemption).** AC1(repro)'s
    own mechanism-proof tests
    (``test_default_runner_resolves_subprocess_run_at_call_time_not_construction_time``
    in both ``test_pi_runtime.py`` and ``test_codex_exec_runtime.py``, T-67-01/T-67-03)
    legitimately construct the adapter with NO ``runner=`` and rely on a
    POST-construction module-attr monkeypatch of
    ``pi_runtime.subprocess.run``/``codex_runtime.subprocess.run`` to prove the exact
    call-time-vs-construction-time distinction FR1 fixes — that IS the mechanism this
    guard also patches, so the two must compose deliberately rather than collide.

    This is opted OUT of at the call site, not exempted here by name or module: each
    of those two tests requests the ``real_worker_guard_bypass_for_mechanism_proof``
    fixture explicitly as a normal test parameter (see its docstring for why each
    opt-out call site stays hermetic — the test itself installs a fake at the module
    boundary FIRST and never lets a real subprocess execute). Detection here is via
    ``request.fixturenames`` — the resolved fixture closure for THIS test item — never
    a node name list or module-wide exemption; a test must explicitly declare the
    bypass fixture as a parameter for the reviewer to see it at the call site.
    """
    if _real_worker_opt_in():
        return
    if "real_worker_guard_bypass_for_mechanism_proof" in request.fixturenames:
        return

    def _guarded_resolve_runner(self: object) -> object:
        injected = getattr(self, "_runner", None)
        if injected is not None:
            return injected
        raise RuntimeError(
            "real pi/codex binary invocation attempted without a live-opt-in flag "
            "set — set one of DADAIA_E2E_REAL_WORKER, DADAIA_PI_LIVE, "
            "DADAIA_CODEX_LIVE, DADAIA_CLAUDE_LIVE=1 to opt in, or inject an explicit "
            "runner= at construction to keep the test hermetic."
        )

    from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter
    from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter

    monkeypatch.setattr(PiHeadlessAdapter, "_resolve_runner", _guarded_resolve_runner, raising=True)
    monkeypatch.setattr(CodexExecAdapter, "_resolve_runner", _guarded_resolve_runner, raising=True)


@pytest.fixture
def real_worker_guard_bypass_for_mechanism_proof() -> None:
    """Explicit, per-test opt-out of :func:`_real_worker_guard`, for the exact two
    AC1(repro) mechanism-proof tests only (T-67-01 pi half, T-67-03 codex half).

    **Why each opt-out call site stays hermetic (not a real-binary risk):** both
    tests (a) construct the adapter with no ``runner=``, (b) IMMEDIATELY
    ``monkeypatch.setattr`` the module-level ``subprocess.run`` attribute on
    ``pi_runtime``/``codex_runtime`` to a fake BEFORE calling ``.run()``, and
    (c) assert the fake's call-recorder shows exactly one invocation. Because the
    module-attr patch is applied before any subprocess is spawned, the real binary is
    never reached even with this guard bypassed for that one test — the test's own
    monkeypatch is the hermeticity boundary, not this fixture. A future test that
    requests this fixture WITHOUT installing its own module-attr fake before calling
    ``.run()`` would genuinely spawn the real binary — that is exactly the risk this
    fixture is scoped narrowly to avoid normalizing; do not add new call sites without
    the same before-first-call monkeypatch discipline documented here.

    This fixture does nothing by itself — ``_real_worker_guard`` (autouse, declared
    above) detects its presence in the requesting test's resolved fixture closure
    (``request.fixturenames``) and skips patching ``_resolve_runner`` for that one
    test only. Requesting it is a plain, visible test-function parameter — an
    explicit opt-in the reviewer sees at the call site, never a name list or
    module-wide exemption.
    """
    return None


@pytest.fixture(autouse=True)
def _repo_root_write_guard() -> object:
    """Assert no new files appear in protected lib-repo paths during a test.

    Yields control to the test, then compares the file-set snapshot taken
    before the test against the one taken after.  If new files appear, the
    test fails with a descriptive message listing the offending paths.
    """
    before = _collect_entries(_REPO_ROOT, _GUARDED_DIRS, _GUARDED_ROOT_FILES)
    yield
    after = _collect_entries(_REPO_ROOT, _GUARDED_DIRS, _GUARDED_ROOT_FILES)
    new_files = after - before
    if new_files:
        formatted = "\n  ".join(sorted(new_files))
        pytest.fail(
            f"Test wrote unexpected files into protected lib-repo paths:\n  {formatted}\n"
            "These paths must not be modified by tests: "
            + ", ".join((*_GUARDED_DIRS, *_GUARDED_ROOT_FILES))
        )


# Snapshot of pollution dirs that already existed when the session started.
# The pollution guard is a pre/post DIFF: it fails only on dirs CREATED during
# the session, never on ones that were already present at session start.
#
# Why a diff and not an existence check (bug
# ``ci-preflight-self-pollution-gate-never-passes``, T-010-25): the
# ``dadaia ci preflight`` gate runs ruff + mypy BEFORE the pytest check.  When
# those earlier checks created cache dirs at the repo root, the existence-based
# guard tripped on the gate's OWN artifacts and the gate could never pass on a
# clean tree.  Detecting whether those dirs should exist *at all* is the job of
# ``tests/contract/test_source_repo_hygiene.py`` and CI repo-hygiene — not this
# session guard, whose only job is to catch tests that pollute the root.
_PREEXISTING_POLLUTION: set[str] = set()


def pytest_sessionstart(session: pytest.Session) -> None:
    """Record which pollution dirs already existed before any test ran."""
    _PREEXISTING_POLLUTION.clear()
    _PREEXISTING_POLLUTION.update(d for d in _POLLUTION_DIRS if (_REPO_ROOT / d).exists())


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Session-level pollution guard (pre/post snapshot diff).

    Fails the session (exit code 1) if any tool-generated cache or state
    directory was *created during the test run* at the repo root.  Dirs that
    already existed at session start are ignored — flagging their existence at
    all is the job of ``tests/contract/test_source_repo_hygiene.py`` and CI, not
    this guard.  This catches misconfigured tool invocations (wrong CWD, missing
    --no-cache flags, etc.) that the per-test _repo_root_write_guard cannot catch
    (e.g. directories created by pytest plugins that run outside fixture scope).

    Offending directories:
      .dadaia  .venv  .pytest_cache  .mypy_cache  .hypothesis  .ruff_cache  test-results
    """
    offenders = [
        d for d in _POLLUTION_DIRS if (_REPO_ROOT / d).exists() and d not in _PREEXISTING_POLLUTION
    ]
    if offenders:
        msg = (
            "\n\n[SESSION POLLUTION] The following cache/state directories were found at "
            f"the repo root ({_REPO_ROOT}) after the test session:\n"
            + "".join(f"  {d}\n" for d in offenders)
            + "\nThis means a tool was invoked with the wrong working directory or without "
            "the appropriate no-cache flags.  Fix the root cause:\n"
            "  pytest:    addopts must include '-p no:cacheprovider'\n"
            "  mypy:      incremental = false in [tool.mypy]\n"
            "  hypothesis: load_profile('no_db') with database=None in conftest.py\n"
            "  ruff:      invoke with --no-cache flag\n"
            "  playwright: outputDir / outputFolder must point outside the repo\n"
        )
        # Print visibly even when -q; session.config.option.verbose may be 0.
        print(msg)  # noqa: T201
        session.exitstatus = 1
