"""Intent: CONTRACT — 0.4.7 FR3 / T-047-76: four behaviours, N hook formats.

A hook exists ONLY as the per-harness implementation of a deterministic behaviour the
workspace defines. This contract pins both halves of that sentence against the live
projection table, not against a hand-listed set of harnesses:

- **Coverage** — every record whose ``hooks`` format renders something derives the SAME
  four behaviours: root whitelist, venv guard and the SDD gate (the ONE merged
  ``dadaia_workspace.hooks.pre_gate`` entrypoint) plus the session-start reaper
  (``dadaia_workspace doctor --fix --expired-only``).
- **No invention** — every ``dadaia_workspace`` entrypoint any projected hook artifact
  references must be named by some Deterministic Behavior in
  ``public/entities/registry.json``. A harness may not grow a fifth behaviour, and no
  file may exist for a behaviour the workspace does not define.

The seam under test is the ``HookFormat`` enum value: the test walks
``HOOK_RULE_BUILDERS`` and renders each record's own hook rules, so a new format joins
this contract the day it grows a builder, with no edit here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import HARNESS_RECORDS, HarnessRecord
from dadaia_workspace.infrastructure.install_plan import InstallPlan
from dadaia_workspace.infrastructure.projection import ProjectionRule
from dadaia_workspace.infrastructure.projection_rules import (
    HOOK_RULE_BUILDERS,
    harnesses_with_a_hook_derivation,
)
from dadaia_workspace.infrastructure.public_assets_common import OverwritePolicy

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC = _REPO_ROOT / "dadaia_workspace" / "public"
_REGISTRY = _PUBLIC / "entities" / "registry.json"

#: The SDD gate's single merged PreToolUse entrypoint — root whitelist, venv guard and
#: the gate itself are three behaviours behind ONE module (FR-W4-01).
_PRE_GATE = "dadaia_workspace.hooks.pre_gate"
#: The session-start reaper lane: a CLI process, never a ``hooks.*`` module (P-12).
_REAPER = "-m dadaia_workspace doctor --fix --expired-only"

#: Every ``dadaia_workspace`` reference a hook artifact may carry, as a dotted module
#: tail or the reaper CLI — the union is asserted against the registry below.
_ENTRYPOINT_RE = re.compile(r"dadaia_workspace(?:\.hooks\.[a-z_]+)?")


def _plan(workspace_root: Path) -> InstallPlan:
    return InstallPlan(
        workspace_root=workspace_root,
        agentic_dir=_PUBLIC,
        target="all",
        scope="all",
        only=None,
        overwrite=OverwritePolicy.PRESERVE,
        guardrail_targets=frozenset({"workspace"}),
        harness_targets=("agents", *HARNESS_RECORDS),
        active_harnesses=frozenset(HARNESS_RECORDS),
        overlay=None,
        resolved_models={},
    )


def _hook_rules(record: HarnessRecord, workspace_root: Path) -> tuple[ProjectionRule, ...]:
    return HOOK_RULE_BUILDERS[record.hooks](record, _plan(workspace_root))


def _rendered(rules: tuple[ProjectionRule, ...]) -> dict[str, str]:
    """``{rule label: rendered text}`` for a hook rule table on a pristine workspace."""
    return {rule.label: rule.render(None).decode("utf-8") for rule in rules}


def _workspace_wrappers(
    rules: tuple[ProjectionRule, ...], workspace_root: Path
) -> list[ProjectionRule]:
    """The on-disk executables a derivation projects under ``<ws>/.dadaia/hooks/``."""
    hooks_dir = workspace_root / ".dadaia" / "hooks"
    return [rule for rule in rules if rule.dst.parent == hooks_dir and rule.mode is not None]


def _derived_records() -> list[HarnessRecord]:
    return [HARNESS_RECORDS[name] for name in sorted(harnesses_with_a_hook_derivation())]


def _record_ids(record: HarnessRecord) -> str:
    return record.name


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A bare workspace root with the kimi user home redirected inside it."""
    monkeypatch.setenv("KIMI_CODE_HOME", str(tmp_path / "kimi-home"))
    root = tmp_path / "ws"
    (root / ".dadaia").mkdir(parents=True)
    return root


def test_every_registered_hook_format_has_a_derivation() -> None:
    """No record declares a hook format it never renders: a declared-but-dead format is
    a harness claiming a behaviour it does not implement."""
    declared = {name for name, record in HARNESS_RECORDS.items() if record.hooks.value != "none"}
    assert declared == set(harnesses_with_a_hook_derivation()), (
        "records declaring a hook format without a builder: "
        f"{sorted(declared - set(harnesses_with_a_hook_derivation()))}"
    )


@pytest.mark.parametrize("record", _derived_records(), ids=_record_ids)
def test_the_four_behaviours_reach_every_harness_with_a_hook_derivation(
    record: HarnessRecord, workspace: Path
) -> None:
    """FR3: root whitelist + venv guard + SDD gate (one ``pre_gate``) and the
    session-start reaper are derived into EVERY hook format. No behaviour may exist in
    only one harness."""
    blob = "\n".join(_rendered(_hook_rules(record, workspace)).values())
    assert _PRE_GATE in blob, (
        f"{record.name}: the merged pre_gate entrypoint (root whitelist + venv guard + "
        "SDD gate) is not wired by its hook derivation"
    )
    assert _REAPER in blob, f"{record.name}: the session-start reaper lane is not wired"


@pytest.mark.parametrize("record", _derived_records(), ids=_record_ids)
def test_no_hook_artifact_references_an_undefined_behaviour(
    record: HarnessRecord, workspace: Path
) -> None:
    """No file exists for a behaviour the workspace does not define: every entrypoint a
    projected hook artifact names must trace to a Deterministic Behavior."""
    behaviors_blob = json.dumps(json.loads(_REGISTRY.read_text(encoding="utf-8"))["behaviors"])
    referenced = set()
    for text in _rendered(_hook_rules(record, workspace)).values():
        referenced.update(_ENTRYPOINT_RE.findall(text))
    assert referenced, f"{record.name}: its hook derivation references no entrypoint at all"
    undefined = {
        ref
        for ref in referenced
        if ref.startswith("dadaia_workspace.hooks.") and ref not in behaviors_blob
    }
    assert not undefined, (
        f"{record.name}: hook artifacts invoke {sorted(undefined)}, which no "
        "Deterministic Behavior in public/entities/registry.json defines"
    )


@pytest.mark.parametrize("record", _derived_records(), ids=_record_ids)
def test_every_hook_file_only_cites_wrappers_the_same_derivation_projects(
    record: HarnessRecord, workspace: Path
) -> None:
    """A hook FILE may only name an on-disk executable its own derivation writes — the
    wrapper-script rule is what makes the reference resolvable, on every format that
    needs one."""
    rules = _hook_rules(record, workspace)
    wrappers = {rule.dst.name for rule in _workspace_wrappers(rules, workspace)}
    for label, text in _rendered(rules).items():
        for cited in re.findall(r"\.dadaia/hooks/([A-Za-z0-9._-]+)", text):
            assert cited in wrappers, (
                f"{record.name}: {label} cites wrapper {cited!r}, which its own hook "
                f"derivation never projects (projected: {sorted(wrappers)})"
            )


@pytest.mark.parametrize("record", _derived_records(), ids=_record_ids)
def test_every_projected_wrapper_is_self_locating_and_executable(
    record: HarnessRecord, workspace: Path
) -> None:
    """The exit-127 bug family: a workspace wrapper resolves its interpreter from its
    OWN path, never from ``PATH``, and is projected with the exec bit. (User-level
    shims are workspace-agnostic by construction and resolve upward from the hook cwd
    instead — a different, separately tested contract.)"""
    for rule in _workspace_wrappers(_hook_rules(record, workspace), workspace):
        body = rule.render(None).decode("utf-8")
        assert rule.mode == 0o755, f"{rule.label} is not projected executable"
        assert body.startswith("#!/usr/bin/env sh\n"), rule.label
        assert 'dirname -- "$0"' in body, (
            f"{rule.label} does not resolve its interpreter from its own location"
        )
