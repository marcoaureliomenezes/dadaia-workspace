"""Intent: CONTRACT — SPEC v0.4.5 FR10, A10.1-A10.4; operator ruling O4 (T-045-23).

``.dadaia/references/`` is the sanctioned home for operator-placed reference clones
(``.dadaia/references/<clone>/``). Two independent guarantees, proven at the seam every
consumer actually shares — never a rule bolted onto each verb (A10.3):

1. A10.1 — the ROOT-4 doctor invariant never flags a reference clone: it is a legitimate,
   documented top-level ``.dadaia/`` subdir now (``DoctorService._DADAIA_ALLOWED_SUBDIRS``).
2. A10.2 — a reference clone sits OUTSIDE the context lifecycle: no lifecycle verb can ever
   resolve, bind, alive, dead or GC it. This is proven twice: once at the ONE shared
   enumeration seam every lifecycle verb funnels context resolution through
   (``core.specs_resolver.resolve_context`` / ``_repo_slug_under_repos``, scoped to
   ``<workspace_root>/repos/`` only — a reference clone under ``.dadaia/references/`` is
   structurally unreachable from it), and once on a REAL verb call path: the exact function
   backing ``dadaia context bind``/``show``'s no-arg resolution
   (``cli._specs_resolution.resolve_context_for_cli``), and the real, whole
   ``DoctorService.fix()`` GC sweep (``dadaia doctor --fix``).

Bug history this FR closes off (prior-art: lifecycle verbs acting on foreign trees
destroyed work before — e.g. ``dadaia context alive`` committing foreign dirty work,
bug ``alive-scaffold-blocks-dead``/class). A10.4: ``specs/`` is untouched by this FR — no
test here writes under ``specs/``.
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import json  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.cli._specs_resolution import (  # noqa: E402
    resolve_context_for_cli,
)
from dadaia_workspace.core import specs_resolver  # noqa: E402
from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402
from tests.fixtures.harness_env import scrub_context_resolution_env  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every rung-0/1/2 env var neutralized — see ``test_specs_resolver_resolve_context.py``
    for why (ambient ``WORKSPACE_ROOT``/session leaks make this suite flaky otherwise)."""
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


def _make_doctor(root: Path, store: FakeContextStore | None = None) -> DoctorService:
    return DoctorService(
        context_store=store or FakeContextStore(),
        git_client=FakeGitClient(),
        workspace_root=root,
    )


# ---------------------------------------------------------------------------
# A10.1 — doctor-clean
# ---------------------------------------------------------------------------


def test_reference_clone_reports_doctor_clean(tmp_path: Path) -> None:
    """RED before the fix: ROOT-4 flags ``.dadaia/references/<clone>/`` today. GREEN after:
    the ROOT-4 allowlist sanctions ``references`` (operator ruling O4) and the workspace
    reports zero issues for it."""
    _init_workspace(tmp_path)
    _plant_reference_clone(tmp_path)

    issues = _make_doctor(tmp_path).check()

    assert "ROOT-4" not in {i.code for i in issues}, issues


# ---------------------------------------------------------------------------
# A10.2 — outside the context lifecycle, proven at the shared seam AND on real verb paths
# ---------------------------------------------------------------------------


def test_shared_resolution_seam_never_resolves_a_reference_clone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ONE seam every lifecycle verb (bind/alive/dead/show's default resolution)
    funnels context resolution through is ``core.specs_resolver.resolve_context`` — its
    cwd rung (``_repo_slug_under_repos``) is scoped to ``<workspace_root>/repos/`` only.
    A cwd inside ``.dadaia/references/<clone>/`` sits entirely outside that tree, so the
    seam can never select the reference clone as an active context — proven directly,
    not inferred from the allowlist."""
    _init_workspace(tmp_path)
    clone_dir = _plant_reference_clone(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.chdir(clone_dir)

    assert specs_resolver.resolve_context() is None


def test_bind_and_show_resolution_path_refuses_to_select_a_reference_clone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real verb call path: ``resolve_context_for_cli`` is the exact function
    ``dadaia context bind``/``dadaia context show``'s no-arg resolution calls. With cwd
    inside the reference clone and no explicit/env/session override, it must raise —
    never silently resolve to (or "invent") the reference clone as a bindable context."""
    _init_workspace(tmp_path)
    clone_dir = _plant_reference_clone(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.chdir(clone_dir)

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

    # Plant genuinely GC-eligible state alongside it, so fix() has real work to do.
    (tmp_path / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "ctx_locks" / "stale.lock.json").write_text(
        "{}", encoding="utf-8"
    )

    actions = _make_doctor(tmp_path).fix()

    assert clone_dir.exists()
    assert (clone_dir / "README.md").exists()
    assert (clone_dir / "README.md").read_text(encoding="utf-8") == before
    assert (clone_dir / ".git").exists()
    assert not any("references" in a.lower() for a in actions), actions
