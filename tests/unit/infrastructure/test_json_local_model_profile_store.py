"""Unit tests for the operator-local model-profile store (T-30-C-01 / WS-PROFILES).

The store loads operator-registered Layer-2 profiles from
``.dadaia/states/workflow_model_profiles.local.json``. Contract (L1/L3/L8):

- **missing != invalid** — an absent store loads ``()`` (default-first), a present-but-
  invalid store raises :class:`LocalModelProfileStoreError`;
- **L1** — an operator profile MUST declare ``harness == "pi"`` this release;
- **L8** — the store MUST reject any API-key / secret-shaped field (root, profile, or
  nested), and the store is never projected into ``public/``.

The generic load/parse/save store contract (missing default / corrupt / unknown
top-level field / wrong schema_version / atomic-no-tmp) is asserted once via the
shared ``_store_contract`` helpers where the shape matches; this file keeps the
store-specific logic: L1 harness gate, L8 secret-field rejection (never echoes the
value), the AC-5 model-id allowlist, duplicate-id rejection, and the never-projected
guarantee.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.local_model_profile_store import (
    LocalModelProfileStoreError,
)
from dadaia_workspace.infrastructure.json_local_model_profile_store import (
    JsonLocalModelProfileStore,
)

from ._store_contract import (
    assert_corrupt_json_raises_typed_error,
    assert_missing_file_loads_default,
    assert_save_is_atomic_no_tmp_leftover,
    assert_unknown_top_level_field_rejected,
    assert_wrong_schema_version_rejected,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    return tmp_path


def _valid_profile() -> dict[str, object]:
    return {
        "id": "pi-operator-fast",
        "harness": "pi",
        "label": "PI — operator fast",
        "model_id": "openai-codex/gpt-5.6-sol",
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


def test_load_contract(tmp_path: Path) -> None:
    """missing->() default / corrupt->typed error / unknown-field / wrong
    schema_version / atomic-no-tmp — the shared store-contract template."""
    workspace = _workspace(tmp_path)
    assert JsonLocalModelProfileStore(workspace).path == (
        workspace / ".dadaia" / "states" / "workflow_model_profiles.local.json"
    )
    assert_missing_file_loads_default(JsonLocalModelProfileStore(workspace), ())
    assert_corrupt_json_raises_typed_error(
        JsonLocalModelProfileStore(_workspace(tmp_path / "corrupt")),
        LocalModelProfileStoreError,
    )
    assert_unknown_top_level_field_rejected(
        JsonLocalModelProfileStore(_workspace(tmp_path / "unknown")),
        _valid_store(),
        LocalModelProfileStoreError,
        bogus_key="unexpected",
    )
    assert_wrong_schema_version_rejected(
        JsonLocalModelProfileStore(_workspace(tmp_path / "schema")),
        _valid_store(),
        LocalModelProfileStoreError,
        "workflow-model-profiles-local-v0",
    )
    assert_save_is_atomic_no_tmp_leftover(
        JsonLocalModelProfileStore(_workspace(tmp_path / "atomic")),
        JsonLocalModelProfileStore(workspace).parse(_valid_store()),
    )


def test_valid_store_loads_operator_profile_and_round_trips_through_save(
    tmp_path: Path,
) -> None:
    store = _write(_workspace(tmp_path), _valid_store())
    profiles = store.load()
    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.id == "pi-operator-fast"
    assert profile.harness == "pi"
    # provenance is forced to a stable operator marker — never spoofable as built-in.
    assert profile.source == "operator-local"

    save_store = JsonLocalModelProfileStore(_workspace(tmp_path / "save"))
    parsed = save_store.parse(_valid_store())
    save_store.save(parsed)
    loaded = save_store.load()
    assert len(loaded) == 1
    assert loaded[0].id == "pi-operator-fast"


@pytest.mark.parametrize(
    ("mutate_document", "expected_message_fragment"),
    [
        pytest.param(
            lambda p, d: (p.__setitem__("harness", "codex"), d)[1],
            "harness",
            id="harness-not-pi-fails-closed",
        ),
        pytest.param(
            lambda p, d: (d.__setitem__("auth_token", "tok-leak"), d)[1],
            "auth_token",
            id="secret-field-at-root-rejected",
        ),
        pytest.param(
            lambda p, d: (p.__delitem__("model_id"), d)[1],
            "model_id",
            id="missing-required-field-rejected",
        ),
        pytest.param(
            lambda p, d: _valid_store([_valid_profile(), _valid_profile()]),
            "duplicate",
            id="duplicate-operator-ids-rejected",
        ),
    ],
)
def test_parse_rejection_matrix(
    tmp_path: Path, mutate_document: object, expected_message_fragment: str
) -> None:
    profile = _valid_profile()
    document = _valid_store([profile])
    document = mutate_document(profile, document)  # type: ignore[operator]
    store = _write(_workspace(tmp_path), document)
    with pytest.raises(LocalModelProfileStoreError) as exc:
        store.load()
    message = str(exc.value)
    assert expected_message_fragment in message.lower() or expected_message_fragment in message
    if expected_message_fragment == "auth_token":
        assert "tok-leak" not in message  # never echo the secret value (L8)


@pytest.mark.parametrize(
    ("mutate", "secret_value", "secret_token"),
    [
        pytest.param(
            lambda p: {**p, "api_key": "sk-super-secret-value"},
            "sk-super-secret-value",
            "api_key",
            id="api-key-on-profile",
        ),
        pytest.param(
            lambda p: {**p, "nested": {"client_secret": "leak"}},
            "leak",
            "secret",
            id="nested-secret",
        ),
    ],
)
def test_l8_secret_field_rejected_never_echoes_value(
    tmp_path: Path, mutate: object, secret_value: str, secret_token: str
) -> None:
    """L8: a credential-shaped field (root-level or recursively nested) is rejected;
    the secret VALUE is never echoed in the error message — this assert must survive
    verbatim."""
    bad = mutate(_valid_profile())  # type: ignore[operator]
    store = _write(_workspace(tmp_path), _valid_store([bad]))
    with pytest.raises(LocalModelProfileStoreError) as exc:
        store.load()
    message = str(exc.value)
    assert secret_token.lower() in message.lower()
    assert secret_value not in message  # never leak the secret value


@pytest.mark.parametrize(
    ("model_id", "should_load"),
    [
        pytest.param(
            "openai-codex/gpt-5.6-sol",
            True,
            id="codex-subscription-gpt-id-accepted",
        ),
        pytest.param("moonshotai/kimi-k2.5", True, id="allowlisted-openrouter-id-accepted"),
        pytest.param("gpt-5.5", False, id="ambiguous-gpt-id-rejected"),
        pytest.param("openai/gpt-5.5", False, id="api-key-gpt-provider-rejected"),
        pytest.param("totally-unknown-9.9", False, id="outside-allowlist-union-rejected"),
        pytest.param("claude-opus-4-8", False, id="claude-model-id-rejected-by-allowlist"),
    ],
)
def test_ac5_model_id_allowlist(tmp_path: Path, model_id: str, should_load: bool) -> None:
    """PI GPT profiles require openai-codex; curated non-GPT ids stay selectable."""
    candidate = _valid_profile()
    candidate["model_id"] = model_id
    store = _write(_workspace(tmp_path), _valid_store([candidate]))

    if should_load:
        profiles = store.load()
        assert len(profiles) == 1
        assert profiles[0].model_id == model_id
    else:
        with pytest.raises(LocalModelProfileStoreError) as exc:
            store.load()
        if model_id == "totally-unknown-9.9":
            message = str(exc.value)
            assert model_id in message
            assert "allowlist" in message.lower()


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
