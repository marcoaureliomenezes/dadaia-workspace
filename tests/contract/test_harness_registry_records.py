"""Intent: CONTRACT — AC3.1 / T-047-71: one harness record, no per-harness branch.

The 0.4.7 FR2 refactor replaces the three ``HarnessProjection`` classes with one
``HarnessRecord`` row per harness. Its whole promise is that nothing observable
changed: the rendered rule table for ``claude``, ``codex`` and ``kimi-code`` must be
byte-for-byte the table the classes produced, captured as a golden BEFORE the
refactor (``tests/_golden/harness_projection_table.json``). The second assertion is
the structural one the PLAN's Risks section demands: the projection table carries no
harness-named literal, so the per-harness-branch bug family (public-install /
init --harness / harness-profile disagreements) cannot reappear by construction.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType

import pytest

from dadaia_workspace.cli.commands import init as init_module
from dadaia_workspace.core.harness_registry import (
    HARNESS_PROJECTION_DIRS,
    HARNESS_RECORDS,
    L1_ENTRY_HARNESSES,
    PROJECTION_TARGETS,
    parse_harness_name,
)
from dadaia_workspace.features.workspace import service as workspace_service_module
from dadaia_workspace.infrastructure import agent_transcodes as agent_transcodes_module
from dadaia_workspace.infrastructure import projection_rules as projection_rules_module
from dadaia_workspace.infrastructure.install_plan import InstallPlan
from dadaia_workspace.infrastructure.projection_rules import projection_rules
from dadaia_workspace.infrastructure.public_assets_common import OverwritePolicy

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC = _REPO_ROOT / "dadaia_workspace" / "public"
_GOLDEN = _REPO_ROOT / "tests" / "_golden" / "harness_projection_table.json"


def render_table(workspace_root: Path, kimi_home: Path) -> list[dict[str, object]]:
    """The rule table for all three harnesses, normalised to root-relative rows.

    Kept importable so the golden can be regenerated from exactly this code path.
    """
    plan = InstallPlan(
        workspace_root=workspace_root,
        agentic_dir=_PUBLIC,
        harness=None,
        scope="all",
        only=None,
        overwrite=OverwritePolicy.PRESERVE,
        guardrail_targets=frozenset({"workspace"}),
        harness_targets=("agents", *L1_ENTRY_HARNESSES),
        active_harnesses=frozenset(L1_ENTRY_HARNESSES),
        overlay=None,
        resolved_models={},
    )

    def rel(path: Path) -> str:
        for root, tag in ((workspace_root, "ws"), (kimi_home, "kimi-home")):
            try:
                return f"{tag}:{path.relative_to(root).as_posix()}"
            except ValueError:
                continue
        return f"abs:{path.as_posix()}"

    return sorted(
        (
            {
                "label": rule.label,
                "harness": rule.harness,
                "dst": rel(rule.dst),
                "compare": rule.compare,
                "link_to": None if rule.link_to is None else rel(rule.link_to),
                # mode is OS-derived (the source exec bit; Windows reports none) and has
                # its own test — the golden holds OS-independent fields only.
            }
            for rule in projection_rules(plan)
        ),
        key=lambda row: (str(row["label"]), str(row["dst"])),
    )


def test_the_record_table_renders_the_pre_refactor_rule_table_byte_for_byte(
    tmp_path: Path, monkeypatch
) -> None:
    kimi_home = tmp_path / "kimi-home"
    monkeypatch.setenv("KIMI_CODE_HOME", str(kimi_home))
    workspace_root = tmp_path / "ws"
    (workspace_root / ".dadaia").mkdir(parents=True)

    actual = render_table(workspace_root, kimi_home)
    expected = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected, (
        "the harness-record rule table diverged from the golden captured before the "
        "T-047-71 refactor — the refactor is proven by equality, not by re-asserting files"
    )


def test_every_record_carries_a_directory_an_agent_transcode_and_a_hook_derivation() -> None:
    assert tuple(HARNESS_RECORDS) == L1_ENTRY_HARNESSES
    for name, record in HARNESS_RECORDS.items():
        assert record.name == name
        assert record.agent_transcode is not None
        assert record.hooks is not None


def test_the_legacy_constants_derive_from_the_record_table() -> None:
    assert tuple(HARNESS_RECORDS) == L1_ENTRY_HARNESSES
    assert {
        name: ((record.directory,) if record.directory else ())
        for name, record in HARNESS_RECORDS.items()
    } == HARNESS_PROJECTION_DIRS
    assert ("agents", *HARNESS_RECORDS) == PROJECTION_TARGETS
    last = next(reversed(HARNESS_RECORDS))
    assert parse_harness_name(last) == last


@pytest.mark.parametrize(
    "module",
    [
        projection_rules_module,
        agent_transcodes_module,
        workspace_service_module,
        init_module,
    ],
    ids=lambda m: m.__name__,
)
def test_the_projection_table_carries_no_harness_named_literal(module: ModuleType) -> None:
    """A harness name in the projection table — or in `init`, which owns no projection —
    IS the per-harness branch coming back."""
    source = Path(module.__file__ or "").read_text(encoding="utf-8")
    offenders = [
        f'"{name}"' for name in L1_ENTRY_HARNESSES if f'"{name}"' in source or f"'{name}'" in source
    ]
    assert not offenders, (
        f"{Path(module.__file__ or '').name} names harnesses {offenders}; "
        "every harness fact belongs to core/harness_registry.py's record table"
    )
