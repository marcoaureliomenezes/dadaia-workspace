"""ENT-DERIVE-1 behavioral fidelity: each drift class, mutated alone into a clean scratch
tree, is reported as a BLOCKING line, and harness coverage is derived
never restated by the registry.

Seam: ``check_entities_derivation(public_dir)`` reads the harness
records from the module attribute ``entity_doctor.HARNESS_RECORDS`` and the hook table
from ``entity_doctor.HOOK_DIALECTS``; these tests replace both at that boundary. A registry
behavior is ``{id, mandate, modules: [dotted hook modules], gaps: {harness: reason}}``.
Harness H implements behavior X when H is a record, not in X's ``gaps``, and a lane of
``HOOK_DIALECTS[H.hooks]`` runs one of X's ``modules`` (a lane whose argv is no
``dadaia_workspace.<module>``, such as the reaper CLI, names no module).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import (
    AgentTranscode,
    HarnessRecord,
    HookFormat,
)
from dadaia_workspace.core.models.doctor_report import DoctorStatus
from dadaia_workspace.infrastructure import entity_doctor
from dadaia_workspace.infrastructure.entity_doctor import check_entities_derivation
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    HookDialect,
    HookLane,
)

_GATE_MODULE = "dadaia_workspace.hooks.pre_gate"


def _record(name: str, hooks: HookFormat) -> HarnessRecord:
    return HarnessRecord(name, None, AgentTranscode.NONE, hooks)


@pytest.fixture(autouse=True)
def _fake_harnesses(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two harnesses: ``full`` carries the gate lane, ``bare`` has no hook lane at all."""
    monkeypatch.setattr(
        entity_doctor,
        "HARNESS_RECORDS",
        {
            "full": _record("full", HookFormat.CLAUDE_SETTINGS),
            "bare": _record("bare", HookFormat.CODEX_HOOKS),
        },
    )
    monkeypatch.setattr(
        entity_doctor,
        "HOOK_DIALECTS",
        {
            HookFormat.CLAUDE_SETTINGS: HookDialect(
                lanes=(
                    HookLane("pre-gate", _GATE_MODULE + ' "$@"'),
                    HookLane("doctor-expired", "dadaia_workspace doctor --fix"),
                )
            ),
            HookFormat.CODEX_HOOKS: HookDialect(),
        },
    )


def _clean_scratch(root: Path) -> Path:
    """Two self-consistent personas and one Behavior citing a module that exists;
    ``root`` stands for the package root the module reference resolves against."""
    public_dir = root / "public"
    (public_dir / "entities").mkdir(parents=True)
    (public_dir / "agents").mkdir(parents=True)
    (root / "hooks").mkdir(parents=True)
    registry = {
        "schema_version": "agentic-entities-v1",
        "personas": [{"id": "alpha", "mandate": "a"}, {"id": "beta", "mandate": "b"}],
        "behaviors": [
            {
                "id": "gate-behavior",
                "mandate": "gates something",
                "modules": [_GATE_MODULE],
                "gaps": {"bare": "no hook events"},
            }
        ],
        "rules": [],
        "universal": {},
    }
    (public_dir / "entities" / "registry.json").write_text(json.dumps(registry))
    for pid in ("alpha", "beta"):
        (public_dir / "agents" / f"{pid}.md").write_text(f"---\nname: {pid}\n---\nBody.\n")
    (root / "hooks" / "pre_gate.py").write_text("# stub\n")
    return public_dir


def _edit_behavior(root: Path, **change: object) -> None:
    path = root / "public" / "entities" / "registry.json"
    data = json.loads(path.read_text())
    data["behaviors"][0].update(change)
    path.write_text(json.dumps(data))


def _module_becomes_package(root: Path) -> None:
    (root / "hooks" / "pre_gate.py").unlink()
    (root / "hooks" / "pre_gate").mkdir()
    (root / "hooks" / "pre_gate" / "__init__.py").write_text("")


def _stub(root: Path) -> None:
    (root / "public" / "agents" / "alpha.md").write_text("placeholder prose, no frontmatter\n")


def _module_gone(root: Path) -> None:
    (root / "hooks" / "pre_gate.py").unlink()


_STUB = "'alpha' has no parseable frontmatter identity"
_GONE = "references module 'dadaia_workspace.hooks.pre_gate' which no longer exists"


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        pytest.param(lambda root: None, [], id="clean-baseline"),
        pytest.param(_module_becomes_package, [], id="module-as-package-is-honored"),
        pytest.param(
            lambda root: (root / "public" / "agents" / "beta.md").unlink(),
            ["Persona 'beta' has no derived core"],
            id="dead-persona",
        ),
        pytest.param(
            lambda root: _edit_behavior(root, gaps={}), ["'bare'"], id="uncovered-harness"
        ),
        pytest.param(
            lambda root: _edit_behavior(root, gaps={"bare": "x", "ghost": "x"}),
            ["'ghost'"],
            id="gap-names-no-harness",
        ),
        pytest.param(_stub, [_STUB], id="stub-body"),
        pytest.param(
            lambda root: (root / "public" / "agents" / "alpha.md").write_text(
                "---\nname: beta\n---\nBody.\n"
            ),
            ["frontmatter name 'beta' does not match its filename"],
            id="identity-swap",
        ),
        pytest.param(_module_gone, [_GONE], id="hook-module-deleted"),
        pytest.param(
            lambda root: (_stub(root), _module_gone(root)),
            [_STUB, _GONE],
            id="every-drift-reported",
        ),
    ],
)
def test_each_drift_class_blocks(
    tmp_path: Path, mutate: Callable[[Path], object], expected: list[str]
) -> None:
    public_dir = _clean_scratch(tmp_path)
    mutate(tmp_path)

    lines = check_entities_derivation(public_dir)

    if not expected:
        assert [line.status for line in lines] == [DoctorStatus.OK]
        return
    assert all(line.status.blocking for line in lines)
    for needle in expected:
        assert any(needle in line.text for line in lines)


def test_a_harness_record_added_without_a_registry_edit_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    public_dir = _clean_scratch(tmp_path)
    records = {
        **entity_doctor.HARNESS_RECORDS,
        "newcomer": _record("newcomer", HookFormat.CLAUDE_SETTINGS),
    }
    monkeypatch.setattr(entity_doctor, "HARNESS_RECORDS", records)

    lines = check_entities_derivation(public_dir)

    assert [line.status for line in lines] == [DoctorStatus.OK]


def test_a_hook_module_no_behavior_names_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    public_dir = _clean_scratch(tmp_path)
    (tmp_path / "hooks" / "orphan.py").write_text("# stub\n")
    dialects = dict(entity_doctor.HOOK_DIALECTS)
    dialects[HookFormat.CLAUDE_SETTINGS] = HookDialect(
        lanes=(
            HookLane("pre-gate", _GATE_MODULE + ' "$@"'),
            HookLane("orphan", 'dadaia_workspace.hooks.orphan "$@"'),
        )
    )
    monkeypatch.setattr(entity_doctor, "HOOK_DIALECTS", dialects)

    lines = check_entities_derivation(public_dir)

    assert all(line.status.blocking for line in lines)
    assert any("dadaia_workspace.hooks.orphan" in line.text for line in lines)
