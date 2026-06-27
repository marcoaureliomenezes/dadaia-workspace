"""Unit tests for the operator-local model-profile store (T-30-C-01 / WS-PROFILES).

The store loads operator-registered Layer-2 profiles from
``.dadaia/states/workflow_model_profiles.local.json``. Contract (L1/L3/L8):

- **missing != invalid** — an absent store loads ``()`` (default-first), a present-but-
  invalid store raises :class:`LocalModelProfileStoreError`;
- **L1** — an operator profile MUST declare ``harness == "pi"`` this release;
- **L8** — the store MUST reject any API-key / secret-shaped field (root, profile, or
  nested), and the store is never projected into ``public/``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.local_model_profile_store import (
    LocalModelProfileStoreError,
    LocalModelProfileStorePort,
)
from dadaia_workspace.infrastructure.json_local_model_profile_store import (
    JsonLocalModelProfileStore,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    return tmp_path


def _valid_profile() -> dict[str, object]:
    return {
        "id": "pi-operator-fast",
        "harness": "pi",
        "label": "PI — operator fast",
        "model_id": "gpt-5.5",
        "effort": "low",
        "purpose": "Operator's low-cost PI profile.",
    }


def _valid_store(profiles: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "schema_version": "workflow-model-profiles-local-v1",
        "profiles": profiles if profiles is not None else [_valid_profile()],
    }


def _write(workspace: Path, document: object) -> JsonLocalModelProfileStore:
    store = JsonLocalModelProfileStore(workspace)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(json.dumps(document), encoding="utf-8")
    return store


def test_satisfies_port() -> None:
    assert isinstance(JsonLocalModelProfileStore, type)
    # structural conformance — the adapter is a LocalModelProfileStorePort.
    store = JsonLocalModelProfileStore(Path("/nonexistent-root"))
    assert isinstance(store, LocalModelProfileStorePort)


def test_path_is_workspace_local(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonLocalModelProfileStore(workspace)
    assert store.path == (workspace / ".dadaia" / "states" / "workflow_model_profiles.local.json")


def test_missing_store_loads_empty_tuple_not_error(tmp_path: Path) -> None:
    # L3 default-first: a missing store is NOT an error.
    store = JsonLocalModelProfileStore(_workspace(tmp_path))
    assert store.load() == ()


def test_valid_store_loads_operator_profile(tmp_path: Path) -> None:
    store = _write(_workspace(tmp_path), _valid_store())
    profiles = store.load()
    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.id == "pi-operator-fast"
    assert profile.harness == "pi"
    # provenance is forced to a stable operator marker — never spoofable as built-in.
    assert profile.source == "operator-local"


def test_harness_not_pi_fails_closed(tmp_path: Path) -> None:
    # L1: an operator profile must be PI this release.
    bad = _valid_profile()
    bad["harness"] = "codex"
    store = _write(_workspace(tmp_path), _valid_store([bad]))
    with pytest.raises(LocalModelProfileStoreError) as exc:
        store.load()
    assert "harness" in str(exc.value)
    assert "pi" in str(exc.value)


def test_api_key_field_on_profile_rejected(tmp_path: Path) -> None:
    # L8: a credential-shaped field is rejected; the value is never echoed.
    bad = _valid_profile()
    bad["api_key"] = "sk-super-secret-value"
    store = _write(_workspace(tmp_path), _valid_store([bad]))
    with pytest.raises(LocalModelProfileStoreError) as exc:
        store.load()
    message = str(exc.value)
    assert "api_key" in message
    assert "sk-super-secret-value" not in message  # never leak the secret value


def test_secret_field_at_root_rejected(tmp_path: Path) -> None:
    document = _valid_store()
    document["auth_token"] = "tok-leak"
    store = _write(_workspace(tmp_path), document)
    with pytest.raises(LocalModelProfileStoreError) as exc:
        store.load()
    assert "auth_token" in str(exc.value)
    assert "tok-leak" not in str(exc.value)


def test_nested_secret_rejected(tmp_path: Path) -> None:
    # A secret buried inside an unexpected nested object is still caught (recursive guard).
    bad = _valid_profile()
    bad["label"] = "ok"
    bad["nested"] = {"client_secret": "leak"}
    store = _write(_workspace(tmp_path), _valid_store([bad]))
    with pytest.raises(LocalModelProfileStoreError) as exc:
        store.load()
    # the unknown 'nested' key is itself rejected too, but the secret guard runs first.
    assert "secret" in str(exc.value).lower()
    assert "leak" not in str(exc.value)


def test_corrupt_json_fails_closed(tmp_path: Path) -> None:
    store = JsonLocalModelProfileStore(_workspace(tmp_path))
    store.path.write_text("{not json", encoding="utf-8")
    with pytest.raises(LocalModelProfileStoreError):
        store.load()


def test_unknown_top_level_field_rejected(tmp_path: Path) -> None:
    document = _valid_store()
    document["unexpected"] = True
    store = _write(_workspace(tmp_path), document)
    with pytest.raises(LocalModelProfileStoreError) as exc:
        store.load()
    assert "unexpected" in str(exc.value)


def test_wrong_schema_version_rejected(tmp_path: Path) -> None:
    document = _valid_store()
    document["schema_version"] = "workflow-model-profiles-local-v0"
    store = _write(_workspace(tmp_path), document)
    with pytest.raises(LocalModelProfileStoreError):
        store.load()


def test_missing_required_field_rejected(tmp_path: Path) -> None:
    bad = _valid_profile()
    del bad["model_id"]
    store = _write(_workspace(tmp_path), _valid_store([bad]))
    with pytest.raises(LocalModelProfileStoreError) as exc:
        store.load()
    assert "model_id" in str(exc.value)


def test_duplicate_operator_ids_rejected(tmp_path: Path) -> None:
    store = _write(_workspace(tmp_path), _valid_store([_valid_profile(), _valid_profile()]))
    with pytest.raises(LocalModelProfileStoreError) as exc:
        store.load()
    assert "duplicate" in str(exc.value).lower()


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    store = JsonLocalModelProfileStore(_workspace(tmp_path))
    parsed = store.parse(_valid_store())
    store.save(parsed)
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].id == "pi-operator-fast"


def test_save_uses_atomic_write_no_temp_leftover(tmp_path: Path) -> None:
    store = JsonLocalModelProfileStore(_workspace(tmp_path))
    store.save(store.parse(_valid_store()))
    leftovers = list(store.path.parent.glob("*.tmp"))
    assert leftovers == []


def test_store_filename_is_not_a_packaged_public_asset() -> None:
    # L8 never-projected guarantee: the local-store filename does not appear anywhere under
    # the public/ source tree (it is workspace-local state, never a staged/projected asset).
    public_root = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
    assert public_root.is_dir(), public_root
    hits = [
        p
        for p in public_root.rglob("*")
        if p.is_file() and "workflow_model_profiles.local" in p.name
    ]
    assert hits == [], f"local profile store must never be a public asset: {hits}"
