"""ENT-DERIVE-1 behavioral fidelity: each drift class, mutated alone into a clean scratch
tree, is reported as a BLOCKING line (v0.4.3 T-043-35).

Intent: CONTRACT — v0.4.3 A22.5
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core.models.doctor_report import DoctorStatus
from dadaia_workspace.infrastructure.entity_doctor import check_entities_derivation
from dadaia_workspace.infrastructure.projection_rules import harnesses_with_a_hook_derivation


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
                "implementations": {
                    name: "hook wiring via dadaia_workspace.hooks.pre_gate"
                    for name in harnesses_with_a_hook_derivation()
                },
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


def _drop_kimi_key(root: Path) -> None:
    path = root / "public" / "entities" / "registry.json"
    data = json.loads(path.read_text())
    del data["behaviors"][0]["implementations"]["kimi-code"]
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
            _drop_kimi_key, ["expected every harness with a hook derivation"], id="missing-key"
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
