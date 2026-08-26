"""FR8 (T-045-21, entry ``specs-init-symlinked-target-refusal``): ``specs init
--specs-dir`` refuses a symlinked target — same CWE-59 class the v0.4.4 resolver seam
(T-044-40, ``core.specs_resolver.resolve_specs_dir``) already closed for ``specs
upgrade`` / ``specs doctor --fix``, smaller blast radius.

Before the fix, ``init``'s explicit branch resolved its own path with a bare
``Path(specs_dir).resolve()`` instead of routing through the hardened resolver seam, so
a symlinked ``--specs-dir`` scaffolded straight through the link. The fix reuses that
seam's existing refusal (same function, same message shape, A8.2) instead of adding a
second, independent symlink check.

Intent: CONTRACT — FR8, A8.1-A8.3.
Size: SMALL (CliRunner over the real app, real tmp filesystem, no network/subprocess).
Owner: software-engineer
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def _can_symlink() -> bool:
    """Real capability probe (create-then-clean), not a platform-name guess — Windows
    can create symlinks under Developer Mode/elevation, so a ``sys.platform`` check
    would both false-skip and false-run. Mirrors the probe idiom in
    ``tests/integration/gate/test_classifier_symlink_canonicalization.py::_symlink_or_skip``,
    hoisted to collection time so the test itself stays a plain ``skipif``."""
    probe_dir = Path(tempfile.mkdtemp(prefix="dadaia-symlink-probe-"))
    try:
        target = probe_dir / "target"
        target.mkdir()
        (probe_dir / "link").symlink_to(target, target_is_directory=True)
    except OSError:
        return False
    else:
        return True
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)


_CAN_SYMLINK = _can_symlink()


@pytest.mark.skipif(not _CAN_SYMLINK, reason="symlink creation unsupported in this environment")
def test_specs_init_refuses_a_symlinked_specs_dir(tmp_path: Path) -> None:
    real = tmp_path / "real-specs"
    real.mkdir()
    linked = tmp_path / "proj" / "specs"
    linked.parent.mkdir()
    linked.symlink_to(real, target_is_directory=True)

    result = _runner.invoke(app, ["specs", "init", "--specs-dir", str(linked)])

    assert result.exit_code != 0, result.output
    assert "symlink" in result.output.lower(), result.output
    assert not (real / "constitution.md").exists(), "init scaffolded through the symlink"
    assert list(real.iterdir()) == [], "init wrote into the symlink's real target"


@pytest.mark.skipif(not _CAN_SYMLINK, reason="symlink creation unsupported in this environment")
def test_specs_init_symlink_refusal_reuses_the_hardened_resolver_message(tmp_path: Path) -> None:
    """A8.2: no new refusal vocabulary — the message shape matches the T-044-40 seam's
    ``resolve_specs_dir`` refusal verbatim, proving one refusal is reused, not
    reinvented for this call site."""
    real = tmp_path / "real-specs"
    real.mkdir()
    linked = tmp_path / "proj" / "specs"
    linked.parent.mkdir()
    linked.symlink_to(real, target_is_directory=True)

    result = _runner.invoke(app, ["specs", "init", "--specs-dir", str(linked)])

    assert result.exit_code != 0, result.output
    # Rich/Click box-wraps long error text; collapse borders + whitespace to a flowed
    # line before matching so wrapping never masks (or fakes) the message shape.
    flowed = re.sub(r"[\s│╭╮╰╯─]+", " ", result.output)
    assert "Refusing a symlinked specs root" in flowed, result.output
    assert "Point --specs-dir at the real directory instead of a link to it" in flowed, (
        result.output
    )


def test_specs_init_non_symlinked_explicit_specs_dir_still_works(tmp_path: Path) -> None:
    """A8.3: the non-symlinked explicit branch is unaffected."""
    target = tmp_path / "proj" / "specs"

    result = _runner.invoke(app, ["specs", "init", "--specs-dir", str(target)])

    assert result.exit_code == 0, result.output
    assert (target / "constitution.md").exists()
