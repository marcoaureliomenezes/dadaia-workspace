"""Ratchet: no `tests/**` file freezes a clock while ageing a fixture with the real one.

Intent: CONTRACT — bug no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock

**The bug this guards against.** ``tests/unit/features/tmp_gc/test_tmp_gc_service.py``
(pre-fix, resolved by bug ``tmp-gc-tests-age-files-by-the-real-clock-against-a-frozen-now``,
v0.4.3) injected a FROZEN ``_NOW`` into the production clock while ageing its fixture files
with ``time.time()`` — the real clock. The two clocks drift apart at exactly the wall-clock
rate: a margin authored generously on the day the test was written erodes to nothing and the
suite goes red at whichever future instant the drift crosses the assertion threshold (it did,
at a UTC midnight boundary, four tests red with zero code change in between). The fix is
already in — every ``os.utime`` mtime in that file now derives from ``_NOW.timestamp()``, the
SAME clock the service is given, never ``time.time()``. Nothing except a mechanical ratchet
stops the shape from being reintroduced elsewhere.

**The rule, precisely.** A ``tests/**`` file FAILS this ratchet iff it declares, at MODULE
level, BOTH:

1. A **frozen datetime constant** — a constant-case name (``^_?[A-Z][A-Z0-9_]*$``) assigned
   either:

   (a) a call whose callee's trailing name/attribute is ``datetime`` or ``date`` — covers
       ``datetime(2026, 8, 18, ...)``, ``date(2026, 7, 15)``, and any ``dt.``-aliased or
       ``datetime.datetime(...)`` form. A constructed literal datetime/date IS frozen by
       construction, regardless of what its name happens to be; or

   (b) a bare numeric literal or an ISO-8601-shaped string literal
       (``^\\d{4}-\\d{2}-\\d{2}``) — but ONLY when the constant's OWN name carries a clock
       marker (``NOW``, ``FROZEN``, ``EPOCH``, ``TIMESTAMP``). Without that name restriction
       an unrelated numeric constant (``_TIMEOUT_S = 60``, ``_READY_DEADLINE = 30.0``) would
       trip this rule merely because the file also calls ``time.time()`` for an unrelated
       reason (a deadline poll loop, an id-generation seed, ...) — a false positive this
       ratchet must never produce.

2. A **real-clock call** anywhere in the file — an AST ``Call`` node shaped ``<name>.time()``
   (``time.time()`` / an aliased ``_time.time()`` — this codebase exposes no other ``.time()``
   zero-arg call convention) or a call whose own attribute is ``now`` where the callee's
   trailing dotted name is ``datetime`` (``datetime.now()``, ``dt.datetime.now()``,
   ``datetime.datetime.now()``).

There is no escape hatch. A file needing both a frozen reference clock AND a computed
timestamp derives the timestamp from the frozen constant (``_NOW.timestamp() - offset``,
exactly the tmp_gc fix), never from the real clock.

**Why AST, not the raw-text/regex shape
``test_denylist_scan.py::test_no_allowlist_or_sanctioned_terms_constant_in_matcher_source``
uses for the denylist module's no-allowlist contract.** That forbidden construct (an amnesty
list) is not something a legitimate docstring or comment would ever spell out verbatim, so a
regex over raw source text is safe there. A frozen-clock combination is the opposite: THIS
module's own docstring above, and the tmp_gc file's own explanatory comment ("never
time.time(): mixing the real clock with the frozen _NOW makes the effective age drift..."),
both contain the literal text ``time.time()`` in prose — a raw-text scan would refuse its own
commit and refuse the very comment that documents the fix. Parsing the AST and inspecting
only real ``ast.Call`` nodes (the same distinction ``tests/contract/test_core_file_io_purity.py``
draws, and for the identical reason) means a docstring or a ``#`` comment mentioning the
pattern in prose never trips it — only an actual call site does.

**Verified GREEN at HEAD (v0.4.4 audit).** Every ``tests/**`` file that performs fixture
ageing via ``os.utime`` at the time this ratchet was authored (10 files, found via
``grep -rln "os.utime(" tests/`` — the bug report's own prose cites an audit that counted 9;
this scan is authoritative for the rule as coded, not a re-derivation of that count, and in
any case the rule below runs over the ENTIRE ``tests/**`` tree, not merely this list):

* ``tests/unit/features/tmp_gc/test_tmp_gc_service.py`` — frozen ``_NOW``; every ``os.utime``
  mtime derives from ``_NOW.timestamp()`` (the fix already landed) — no real-clock call
  remains in the file.
* ``tests/contract/test_reports_retention_cleanup.py`` and
  ``tests/unit/features/reports/test_retention_service.py`` — frozen ``NOW``; every
  ``os.utime`` mtime derives from ``NOW - timedelta(...)`` — no real-clock call.
* ``tests/contract/cli/test_cli_reports_retention.py``,
  ``tests/unit/cli/commands/test_tmp_gc_cmd.py``,
  ``tests/unit/features/telemetry/test_runtime_adapters.py``,
  ``tests/unit/features/workspace_clean/test_clean_service.py``,
  ``tests/unit/hooks/test_ctx_inject_digest.py``,
  ``tests/unit/hooks/test_post_gate_reap.py`` — every mtime derives from a real-clock call
  with NO frozen constant anywhere in the same file, so the injected reference and the aged
  mtime move together — self-consistent, no drift possible.
* ``tests/unit/infrastructure/test_jsonl_log_rotation.py`` — ages a file to the literal Unix
  epoch (``stale_mtime = 0.0``, a LOCAL variable inside a function, never a module-level
  constant) — the bug report's "epoch 0.0" self-healing relative: as real wall-clock time
  advances the gap only GROWS, never erodes, so no ratchet is needed even in spirit.

The bug report's other self-healing relative — a fixed date compared against the real clock —
is the retention fixtures above (``produced_at="2026-06-01T00:00:00Z"`` /
``"2026-06-04T00:00:00Z"``): both resolve against the frozen ``NOW`` constant, never the real
clock, so they are not actually "compared against the real clock" in THIS file — the
comparison happens inside production code, out of this scan's scope by design (this rule
guards test-authored fixtures, not the module under test).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TESTS_DIR = _REPO_ROOT / "tests"

_CONSTANT_NAME_RE = re.compile(r"^_?[A-Z][A-Z0-9_]*$")
_CLOCK_MARKER_SUBSTRINGS = ("NOW", "FROZEN", "EPOCH", "TIMESTAMP")
_ISO_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _test_files() -> list[Path]:
    """Every ``*.py`` under ``tests/`` (recursively), excluding cache artifacts."""
    return sorted(p for p in _TESTS_DIR.rglob("*.py") if "__pycache__" not in p.parts)


def _trailing_name(node: ast.expr) -> str | None:
    """The trailing identifier of a ``Name``/``Attribute`` chain — ``datetime`` for both
    ``datetime`` and ``dt.datetime``/``datetime.datetime``; ``time``/``now`` similarly."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_frozen_datetime_value(name: str, value: ast.expr) -> bool:
    """True iff *value* is a frozen datetime/date literal, or — only when *name* itself
    carries a clock marker — a fixed numeric/ISO-string timestamp literal. See the module
    docstring's "The rule, precisely" section for the full justification."""
    if isinstance(value, ast.Call):
        return _trailing_name(value.func) in ("datetime", "date")
    if not any(marker in name for marker in _CLOCK_MARKER_SUBSTRINGS):
        return False
    if isinstance(value, ast.Constant):
        if isinstance(value.value, bool):
            return False
        if isinstance(value.value, (int, float)):
            return True
        if isinstance(value.value, str) and _ISO_DATE_PREFIX_RE.match(value.value):
            return True
    return False


def _frozen_constants(tree: ast.Module) -> list[tuple[int, str]]:
    """``(lineno, name)`` for every MODULE-LEVEL frozen-datetime-constant assignment."""
    found: list[tuple[int, str]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
            value: ast.expr | None = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        if value is None:
            continue
        for target in targets:
            if (
                isinstance(target, ast.Name)
                and _CONSTANT_NAME_RE.match(target.id)
                and _is_frozen_datetime_value(target.id, value)
            ):
                found.append((node.lineno, target.id))
    return found


def _is_real_clock_call(node: ast.Call) -> bool:
    """``time.time()`` (any receiver name) or a ``.now()`` call whose own callee chain
    ends in ``datetime`` (``datetime.now()`` / ``dt.datetime.now()`` /
    ``datetime.datetime.now()``)."""
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr == "time" and isinstance(func.value, ast.Name):
        return True
    return func.attr == "now" and _trailing_name(func.value) == "datetime"


def _real_clock_calls(tree: ast.Module) -> list[int]:
    """Line numbers of every real-clock ``ast.Call`` anywhere in *tree* — a genuine call
    site only; a docstring or ``#`` comment mentioning the pattern in prose is never an
    ``ast.Call`` node and so never appears here."""
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_real_clock_call(node)
    )


def _offenses(source: str) -> tuple[list[tuple[int, str]], list[int]]:
    """``(frozen constants, real-clock call line numbers)`` found in *source*."""
    tree = ast.parse(source)
    return _frozen_constants(tree), _real_clock_calls(tree)


def test_no_file_combines_a_frozen_datetime_constant_with_a_real_clock_call() -> None:
    """No ``tests/**`` file declares a frozen datetime constant AND calls
    ``time.time()``/``datetime.now()`` in the same file — see the module docstring for the
    precise rule and why every currently-known aging site stays green under it."""
    violations: list[str] = []
    for path in _test_files():
        constants, clock_calls = _offenses(path.read_text(encoding="utf-8"))
        if constants and clock_calls:
            rel = path.relative_to(_REPO_ROOT)
            const_desc = ", ".join(f"{name}:{lineno}" for lineno, name in constants)
            clock_desc = ", ".join(str(lineno) for lineno in clock_calls)
            violations.append(
                f"{rel} — frozen constant(s) [{const_desc}] + real-clock call(s) at "
                f"line(s) [{clock_desc}]"
            )
    assert not violations, (
        "the following tests/** file(s) freeze a clock constant while also calling "
        "time.time()/datetime.now() — a time bomb (bug "
        "no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock): "
        "derive every timestamp from the SAME frozen constant instead (never the real "
        "clock; there is no escape hatch):\n" + "\n".join(violations)
    )


def test_mutation_fixture_frozen_constant_plus_real_clock_call_turns_red() -> None:
    """Mutation-sanity proof, built entirely in-memory (never a repo file — the pattern
    ``tests/contract/test_rules_skills_map.py``'s two mutation fixtures use): a synthetic
    module reproducing the tmp_gc shape (a frozen ``_NOW`` constant plus a ``time.time()``
    aging call) must trip both detectors, proving the ratchet bites."""
    source = (
        "from __future__ import annotations\n"
        "import time\n"
        "from datetime import datetime\n"
        "\n"
        "_NOW = datetime(2026, 1, 1, 0, 0, 0)\n"
        "\n"
        "def age_fixture(path):\n"
        "    mtime = time.time() - 86400\n"
        "    return mtime\n"
    )
    constants, clock_calls = _offenses(source)
    assert constants == [(5, "_NOW")]
    assert clock_calls == [8]

    # And the same shape via datetime.now(), never time.time():
    source_now_variant = (
        "from __future__ import annotations\n"
        "import datetime as dt\n"
        "\n"
        "_FROZEN_NOW = dt.datetime(2026, 1, 1, 0, 0, 0)\n"
        "\n"
        "def age_fixture(path):\n"
        "    mtime = dt.datetime.now().timestamp()\n"
        "    return mtime\n"
    )
    constants_now, clock_calls_now = _offenses(source_now_variant)
    assert constants_now == [(4, "_FROZEN_NOW")]
    assert clock_calls_now == [7]


def test_control_fixture_frozen_constant_alone_stays_green() -> None:
    """Negative control: a frozen constant with NO real-clock call anywhere in the file —
    the tmp_gc file's post-fix shape (mtime derived from ``_NOW.timestamp()`` only) — must
    NOT trip the ratchet. Without this control, a detector that flags any file merely
    containing a frozen constant (ignoring the AND) would silently pass the positive
    mutation fixture above while producing false positives on every legitimate frozen-clock
    test in the suite."""
    source = (
        "from __future__ import annotations\n"
        "from datetime import datetime\n"
        "\n"
        "_NOW = datetime(2026, 8, 18, 0, 0, 0)\n"
        "\n"
        "def age_fixture(path):\n"
        "    mtime = _NOW.timestamp() - 86400\n"
        "    return mtime\n"
    )
    constants, clock_calls = _offenses(source)
    assert constants == [(4, "_NOW")]
    assert clock_calls == []


def test_control_fixture_real_clock_call_alone_stays_green() -> None:
    """Negative control: a real-clock call with NO frozen constant anywhere in the file —
    the self-consistent shape most of the 10 known aging sites use (both the injected
    reference and the aged mtime derive from the SAME live call) — must NOT trip the
    ratchet."""
    source = (
        "from __future__ import annotations\n"
        "import time\n"
        "\n"
        "_TIMEOUT_S = 60\n"
        "\n"
        "def age_fixture(path):\n"
        "    mtime = time.time() - 86400\n"
        "    return mtime\n"
    )
    constants, clock_calls = _offenses(source)
    assert constants == []
    assert clock_calls == [7]
