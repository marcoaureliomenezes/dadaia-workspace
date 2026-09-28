"""Intent: CONTRACT — 0.4.7 FR3 / T-047-76: four behaviours, N hook formats.

A hook exists ONLY as the per-harness implementation of a deterministic behaviour the
workspace defines. This contract pins both halves of that sentence against the live
projection table, not against a hand-listed set of harnesses. Coverage (the gate judges
every harness's native payload) is proven by payload parity, not string search:
``tests/integration/gate/test_gate_dialects_through_wrappers.py`` (sa-gate-blind-on-cursor-copilot-devin#B8).

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
        harness=None,
        overwrite=OverwritePolicy.PRESERVE,
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
def test_every_projected_wrapper_is_projected_executable(
    record: HarnessRecord, workspace: Path
) -> None:
    """A wrapper is projected with the exec bit; what it runs, and how it answers a
    missing venv, is executed in tests/integration/gate/test_hook_interpreter.py."""
    for rule in _workspace_wrappers(_hook_rules(record, workspace), workspace):
        assert rule.mode == 0o755, f"{rule.label} is not projected executable"


#: sa-hook-parity-claims-false-and-interpreter-rules-diverge#B1 — the table, literally.
_BEHAVIOUR_TABLE = {
    "claude": {"ctx_inject", "pre_gate", "reaper", "sdd_post_gate"},
    "codex": {"ctx_inject", "pre_gate", "reaper", "sdd_post_gate"},
    "kimi-code": {"ctx_inject", "pre_gate", "reaper", "sdd_post_gate"},
    "devin": {"ctx_inject", "pre_gate", "reaper"},
    "cursor": {"pre_gate", "reaper"},
    "copilot": {"pre_gate", "reaper"},
}
_BEHAVIOUR_RE = re.compile(r"-m dadaia_workspace(?:\.hooks\.([a-z_]+)| doctor)")


def _behaviours(text: str) -> set[str]:
    return {m.group(1) or "reaper" for m in _BEHAVIOUR_RE.finditer(text)}


def test_the_behaviour_table_is_derived_and_the_registry_declares_it(workspace: Path) -> None:
    """sa-hook-parity-claims-false-and-interpreter-rules-diverge#B1: rendering every
    harness's hooks yields the declared table; the registry names ctx_inject/the post gate
    exactly where they are wired."""
    derived = {
        record.name: _behaviours("\n".join(_rendered(_hook_rules(record, workspace)).values()))
        for record in _derived_records()
    }
    assert derived == _BEHAVIOUR_TABLE
    behaviors = {
        b["id"]: b["implementations"] for b in json.loads(_REGISTRY.read_text("utf-8"))["behaviors"]
    }
    for harness, wired in _BEHAVIOUR_TABLE.items():
        assert ("ctx_inject" in behaviors["context-memory-injection"][harness]) is (
            "ctx_inject" in wired
        )
        assert ("post" in behaviors["sdd-gate"][harness]) is ("sdd_post_gate" in wired)


def test_no_text_claims_behaviour_parity() -> None:
    """sa-hook-parity-claims-false-and-interpreter-rules-diverge#B2: the hook derivation
    never claims "only serialization" differs nor that "no harness adds a behaviour".
    (The memory atom's copy is reconciled at the closure memory pass — dd-product-engineer.)"""
    hooks_py = _REPO_ROOT / "dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py"
    text = " ".join(hooks_py.read_text("utf-8").split()).replace("*", "").lower()
    assert "only serialization" not in text
    assert "no harness adds a behaviour" not in text
    assert "same four" not in text


def test_runtime_config_bakes_no_interpreter() -> None:
    """sa-hook-parity-claims-false-and-interpreter-rules-diverge#B6: no render-time
    interpreter: runtime_config never reads sys.executable or builds a venv path."""
    source = (_REPO_ROOT / "dadaia_workspace/infrastructure/runtime_config.py").read_text("utf-8")
    assert "sys.executable" not in source
    assert "venv_scripts_dir" not in source
