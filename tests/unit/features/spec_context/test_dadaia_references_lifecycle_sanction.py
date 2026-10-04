"""``.dadaia/references/<clone>/`` holds operator-placed reference clones. A10.1: the doctor's
zone walk never flags one (``references`` is an OPERATOR zone, never walked). A10.2: no
lifecycle verb resolves, binds or GCs one — proven at the shared resolution seam, on the real
bind/show resolution path, and on the whole ``DoctorService.fix()`` sweep. A10.4: nothing here
writes under ``specs/``.
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import json  # noqa: E402
import os  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.cli._specs_resolution import (  # noqa: E402
    resolve_context_for_cli,
)
from dadaia_workspace.core import invocation  # noqa: E402
from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fixtures.harness_env import scrub_context_resolution_env  # noqa: E402
from tests.fixtures.stores import context_store


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every rung-0/1/2 env var neutralized — see ``test_specs_resolver_resolve_context.py``
    for why (ambient session leaks make this suite flaky otherwise)."""
    scrub_context_resolution_env(monkeypatch)


def _init_workspace(root: Path) -> None:
    """Minimal initialized-workspace skeleton (registry + repos/ + sessions dir)."""
    (root / ".dadaia" / "states").mkdir(parents=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": []}), encoding="utf-8"
    )
    (root / ".dadaia" / "sessions").mkdir(parents=True)
    (root / "repos").mkdir(parents=True)


def _plant_reference_clone(root: Path, clone: str = "mattpocock-skills") -> Path:
    """Plant an operator-owned reference clone with real file content under it, the way
    ``git clone`` would — the content is what a foreign-tree-acting verb would destroy."""
    clone_dir = root / ".dadaia" / "references" / clone
    (clone_dir / ".git").mkdir(parents=True)
    (clone_dir / "README.md").write_text("# reference material\n", encoding="utf-8")
    return clone_dir


def _make_doctor(root: Path, store: JsonContextStore | None = None) -> DoctorService:
    return DoctorService(
        context_store=store or context_store(root / ".dadaia" / "states"),
        git_client=GitSubprocessClient(),
        workspace_root=root,
    )


# ---------------------------------------------------------------------------
# A10.1 — doctor-clean
# ---------------------------------------------------------------------------


def test_reference_clone_reports_doctor_clean(tmp_path: Path) -> None:
    """``references`` reads canon at the ``.dadaia/`` top level and nothing beneath it is
    ever an entry of the walk (operator ruling O4; OPERATOR zones are never walked)."""
    _init_workspace(tmp_path)
    _plant_reference_clone(tmp_path)

    findings = _make_doctor(tmp_path).scan()

    assert [f.verdict.value for f in findings if f.path == "references"] == ["canon"]
    assert not any("references/" in f.path for f in findings), findings


# ---------------------------------------------------------------------------
# A10.2 — outside the context lifecycle, proven at the shared seam AND on real verb paths
# ---------------------------------------------------------------------------


def test_no_resolution_path_selects_a_reference_clone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cwd inside ``.dadaia/references/<clone>/`` is outside ``<root>/repos/``: the shared seam
    (``core.invocation.resolve``) selects nothing, and the bind/show path raises instead of inventing one."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(_plant_reference_clone(tmp_path))

    assert invocation.resolve(env=os.environ, cwd=Path.cwd()).context_name is None
    with pytest.raises(ValueError, match="No caller-owned Spec Context is selected"):
        resolve_context_for_cli(None)


def test_doctor_fix_gc_sweep_never_touches_a_reference_clone(tmp_path: Path) -> None:
    """Real verb call path: the whole, real ``DoctorService.fix()`` GC sweep
    (``dadaia doctor --fix``) — run alongside other genuinely GC-eligible state — must
    leave the reference clone's directory and its content byte-for-byte untouched.
    Lifecycle verbs acting on foreign trees destroyed work before; GC is no exception."""
    _init_workspace(tmp_path)
    clone_dir = _plant_reference_clone(tmp_path)
    before = (clone_dir / "README.md").read_text(encoding="utf-8")

    # Plant genuinely reapable state alongside it (``WS-states-slop``), so fix() has
    # real work to do.
    (tmp_path / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "ctx_locks" / "stale.lock.json").write_text(
        "{}", encoding="utf-8"
    )

    actions = _make_doctor(tmp_path).fix()

    assert (clone_dir / "README.md").read_text(encoding="utf-8") == before
    assert (clone_dir / ".git").exists()
    assert not any("references" in a.lower() for a in actions), actions
