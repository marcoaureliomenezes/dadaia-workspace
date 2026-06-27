"""Operator-profile merge tests for ``model_profiles`` (T-30-C-02 / WS-PROFILES).

``list_profiles`` / ``profiles_for`` / ``resolve`` surface built-in + merged operator
profiles. Contract:

- **default-first (L3):** with no store loaded, the public functions behave byte-identically
  to the built-in-only registry;
- a loaded operator profile is selectable (``resolve`` finds it, ``profiles_for("pi")``
  lists it) and carries the ``operator-local`` provenance;
- ``UnknownProfileError`` stays fail-closed for an unknown id;
- governance is re-asserted: an operator profile colliding with a built-in id, naming a
  non-Layer-2 harness, or an unresolvable model is rejected loudly.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.workflow_execution import WorkflowModelProfile
from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.model_profiles import UnknownProfileError


class _FakeStore:
    """A ``LocalModelProfileStorePort`` stand-in returning canned profiles."""

    def __init__(self, profiles: tuple[WorkflowModelProfile, ...]) -> None:
        self._profiles = profiles

    def load(self) -> tuple[WorkflowModelProfile, ...]:
        return self._profiles


def _operator_profile(profile_id: str = "pi-operator-fast", **over: object) -> WorkflowModelProfile:
    data: dict[str, object] = {
        "id": profile_id,
        "harness": "pi",
        "label": "PI — operator fast",
        "model_id": "gpt-5.5",
        "effort": "low",
        "purpose": "Operator's low-cost PI profile.",
        "source": "operator-local",
    }
    data.update(over)
    return WorkflowModelProfile.from_dict(data)


@pytest.fixture(autouse=True)
def _reset_operator_profiles() -> None:
    model_profiles.clear_operator_profiles()
    yield
    model_profiles.clear_operator_profiles()


def test_default_first_no_store_is_built_in_only() -> None:
    # L3: nothing loaded → exactly the built-in set.
    ids = {p.id for p in model_profiles.list_profiles()}
    assert "pi-operator-fast" not in ids
    assert "codex-implementation-standard" in ids


def test_empty_store_loads_nothing() -> None:
    model_profiles.load_operator_profiles(_FakeStore(()))
    ids = {p.id for p in model_profiles.list_profiles()}
    assert "codex-implementation-standard" in ids
    assert all(p.source == "built-in" for p in model_profiles.list_profiles())


def test_operator_profile_is_selectable() -> None:
    model_profiles.load_operator_profiles(_FakeStore((_operator_profile(),)))
    resolved = model_profiles.resolve("pi-operator-fast")
    assert resolved.harness == "pi"
    assert resolved.source == "operator-local"
    assert "pi-operator-fast" in {p.id for p in model_profiles.profiles_for("pi")}
    # built-ins still present (merge, not replace).
    assert "codex-implementation-standard" in {p.id for p in model_profiles.list_profiles()}


def test_unknown_profile_still_fail_closed() -> None:
    model_profiles.load_operator_profiles(_FakeStore((_operator_profile(),)))
    with pytest.raises(UnknownProfileError):
        model_profiles.resolve("does-not-exist")


def test_operator_id_colliding_with_builtin_rejected() -> None:
    collide = _operator_profile(profile_id="pi-implementation-standard")
    with pytest.raises(ValueError) as exc:
        model_profiles.load_operator_profiles(_FakeStore((collide,)))
    assert "collide" in str(exc.value).lower() or "built-in" in str(exc.value).lower()


def test_operator_profile_unresolvable_model_rejected() -> None:
    bad = _operator_profile(model_id="gpt-does-not-exist")
    with pytest.raises(ValueError):
        model_profiles.load_operator_profiles(_FakeStore((bad,)))


def test_load_is_idempotent_and_replaces() -> None:
    model_profiles.load_operator_profiles(_FakeStore((_operator_profile("pi-a"),)))
    assert "pi-a" in {p.id for p in model_profiles.list_profiles()}
    model_profiles.load_operator_profiles(_FakeStore((_operator_profile("pi-b"),)))
    ids = {p.id for p in model_profiles.list_profiles()}
    assert "pi-b" in ids
    assert "pi-a" not in ids  # replaced, not accumulated
