"""Golden (a) — the v0.1.60 W1 PRE-DESCRIPTOR refactor-lock (T-60-10, AC-1).

Captured BEFORE any pack descriptor or projection/precedence code lands, this golden
byte-locks the two behaviour-bearing public-asset surfaces so the W1 ports-and-adapters
seam (T-60-11: new ``core`` model + port + JSON adapter + ``dadaia plugin`` CLI) can be
proven to leave the observable install/doctor behaviour UNCHANGED:

1. ``FileSystemPublicAssetManager.install()`` per-``--target`` ``installed`` list for each
   of ``{all, agents, claude, codex, pi}`` (path-normalized, sorted multiset).
2. ``FileSystemPublicAssetManager.doctor()``'s full report list on a fully-installed
   all-four (no-profile) ``tmp_path`` tree.

**Integration layer (QA-8b).** Real stage/install/doctor via ``FileSystemPublicAssetManager``
against the live ``public/`` source into an isolated ``tmp_path`` workspace — not a unit
fake — so this is an ``integration`` test, not ``unit``.

**Transience (Ruling 14 / QA-2).** Golden (a) is the TRANSIENT refactor-lock, retired at
ship/closure once the machinery lands and golden (b) — the durable "descriptors-present,
zero-plugin-installed" baseline captured in W2 (T-60-20) — becomes the post-upgrade
byte-lock consumers see. Golden (a)'s only job is to prove W1's seam addition does not
perturb the pre-descriptor surface.

**Normalization strategy — three-leak-class platform-invariance FROM DAY ONE (Ruling 14 /
QA-2).** A byte-golden of the doctor surface leaks host/OS state through four channels; each
is canonicalized at capture so the golden is byte-stable on the 3-OS CI matrix:

  * v0.1.55 path/version — every ``tmp_path`` workspace path is stripped to ``<WS>`` and
    ``os.sep`` normalized to ``/`` (:func:`tests.helpers.golden_platform.norm_path_line`).
  * v0.1.58 leak (1) host-state cwd-walk — ``_check_public_privacy`` resolves the operator
    denylist by walking up from cwd, so the ``[ok] public-privacy`` marker renders with or
    without the ``(baseline structural scan, no operator denylist)`` suffix depending on the
    capture tree; both are canonicalized to the bare marker (:func:`tests.helpers.golden_platform.norm_path_line`).
  * v0.1.58 leak (2) directory-iteration order — a report list built by iterating a
    directory (e.g. the ``.pi/`` projection lines) has a stable MULTISET but a
    platform-variant SEQUENCE; the golden locks a SORTED multiset, never a byte-sequence
    (:func:`tests.helpers.golden_platform.sort_line_lists`).
  * v0.1.58 leak (3) OS-phrased exec-probe text — the D-CX-9 probe executes the codex hook
    wrapper, so its error text carries the host OS phrasing (POSIX ``exited 127`` vs Windows
    ``[WinError 193]``); the wrapper path is kept, the OS reason canonicalized
    (:func:`tests.helpers.golden_platform.canon_env_line`).

Additionally, the environmental ``git-dirty`` lines (LIVE source-repo working-tree state,
not projection behaviour) are dropped (:func:`_is_env_doctor_line`), and the
``stage:plugins/...`` descriptor-source parity lines are excluded (:func:`_is_plugins_line`)
because they are golden (b)'s territory per SPEC AC-5: pre-descriptor there are none, and
excluding them keeps golden (a) byte-stable across W1's pack.json addition (T-60-11) — the
whole point of the pre-descriptor refactor-lock. Any OTHER install/doctor line that moves
when the descriptors land is a real regression that must STOP-and-report.

Regenerate (ONLY on a deliberate, reviewed behaviour change) with:
``UPDATE_INSTALL_GOLDENS=1 pytest tests/integration/test_plugin_install_goldens.py``.
A byte diff without that flag is a behaviour regression — fix the consumer, never the golden.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers.golden_platform import assert_golden, is_env_doctor_line, norm_path_line

pytestmark = pytest.mark.integration

_HERE = Path(__file__).resolve().parent
_GOLDEN_DIR = _HERE / "_golden"
_INSTALL_GOLDEN = _GOLDEN_DIR / "plugin_install_targets_golden_a_v0160.json"
_DOCTOR_GOLDEN = _GOLDEN_DIR / "plugin_doctor_report_golden_a_v0160.json"

_INSTALL_TARGETS = ("all", "agents", "claude", "codex", "pi")


# ---------------------------------------------------------------------------
# Normalization helpers (v0.1.55 path/version + v0.1.58 three-leak-class law):
# consolidated into tests/helpers/golden_platform.py (v0.1.64 FR1).
# ---------------------------------------------------------------------------


def _is_plugins_line(line: str) -> bool:
    """A pack-descriptor-source parity line — golden (b)'s territory (SPEC AC-5), not (a)'s.

    Pre-descriptor (T-60-10 capture) there are NONE, so excluding them is a no-op at capture;
    once W1's ``public/plugins/**/pack.json`` descriptors land (T-60-11) the doctor gains
    ``[ok] stage:plugins/<pack>/pack.json`` lines and ``install()`` gains the
    ``[stage] <WS>/.dadaia/agentic/plugins`` copytree line — excluding both keeps golden (a) a
    stable pre-descriptor refactor-lock. Any OTHER moved line is a real regression.
    """
    return "stage:plugins/" in line or "/.dadaia/agentic/plugins" in line


# ---------------------------------------------------------------------------
# Capture functions
# ---------------------------------------------------------------------------


def _golden_a_message(what: str) -> str:
    return (
        f"{what} diverged from the committed v0.1.60 golden (a) — the change altered "
        "observable pre-descriptor install/doctor behaviour. Fix the consumer, never the "
        "golden. If ONLY stage:plugins/* lines moved, that is golden (b)'s territory "
        "(SPEC AC-5) and must be excluded here — otherwise STOP and adjudicate."
    )


def _capture_install(tmp_path: Path) -> dict[str, list[str]]:
    mgr = FileSystemPublicAssetManager()
    result: dict[str, list[str]] = {}
    for target in _INSTALL_TARGETS:
        ws = tmp_path / f"install_{target}"
        ws.mkdir()
        installed = mgr.install(ws, target=target)
        result[target] = [
            norm_path_line(line, ws) for line in installed if not _is_plugins_line(line)
        ]
    return result


def _capture_doctor(tmp_path: Path) -> list[str]:
    ws = tmp_path / "doctor_all_four"
    ws.mkdir()
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")
    report = mgr.doctor(ws)
    return [
        norm_path_line(line, ws)
        for line in report
        if not is_env_doctor_line(line) and not _is_plugins_line(line)
    ]


# ---------------------------------------------------------------------------
# Golden compare / update
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pre_descriptor_install_targets_are_byte_identical(tmp_path: Path) -> None:
    """AC-1: install() per-target ``installed`` lists reproduce byte-identically (golden a)."""
    assert_golden(
        _INSTALL_GOLDEN,
        _capture_install(tmp_path),
        "plugin-golden-a-install-targets",
        message=_golden_a_message("plugin-golden-a-install-targets"),
    )


def test_pre_descriptor_doctor_report_is_byte_identical(tmp_path: Path) -> None:
    """AC-1: doctor()'s all-four (no-profile) report reproduces byte-identically (golden a)."""
    assert_golden(
        _DOCTOR_GOLDEN,
        _capture_doctor(tmp_path),
        "plugin-golden-a-doctor-report",
        message=_golden_a_message("plugin-golden-a-doctor-report"),
    )


def test_golden_a_capture_is_non_vacuous(tmp_path: Path) -> None:
    """Guard: golden (a) locks real content, not an empty surface (mutation-sanity backstop).

    A vacuous capture (all lines filtered / empty install) would make the byte-lock pass
    trivially and stop catching a refactor regression. Assert the two surfaces carry the
    canonical anchors every all-four tree must project.
    """
    install = _capture_install(tmp_path)
    doctor = _capture_doctor(tmp_path)
    # Every target resolves to a non-empty install set.
    for target in _INSTALL_TARGETS:
        assert install[target], f"install(target={target!r}) captured no lines"
    # The doctor report carries the harness-independent public-privacy marker and the
    # data/AGENTS.md stage-parity line — anchors that must never silently vanish.
    assert any("public-privacy" in ln for ln in doctor), doctor
    assert any(ln == "[ok] stage:data/AGENTS.md" for ln in doctor), doctor
