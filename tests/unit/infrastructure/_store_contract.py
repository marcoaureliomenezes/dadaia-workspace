"""Shared JSON-store contract assertions (T-2, v0.1.75 FR1).

Five workspace-state JSON stores repeat the same templated contract:
missing→None/(), corrupt→typed error, unknown-top-level-field→typed error, wrong
schema_version→typed error, atomic write (no .tmp leftover), and a last-good
snapshot of the PRIOR valid file on the second save. This module holds the ONE
shared assertion body for that template; each per-store test file calls the
matching helper with its own store factory / valid document / exception type so
per-store files keep only their own store-specific logic (D-7, L8 secrets,
extends graph, resilience, etc.) — never a re-implementation of the template.

Not a test module itself (no ``test_*`` functions) — it is a helper imported by
the store-owning test files, so pytest never collects it directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class LoadParseSaveStore(Protocol):
    """The shared shape of the load/parse/save+last-good stores."""

    @property
    def path(self) -> Path: ...

    @property
    def last_good_path(self) -> Path: ...

    def load(self) -> Any: ...

    def parse(self, raw: object) -> Any: ...

    def save(self, value: Any) -> None: ...


def assert_missing_file_loads_default(store: LoadParseSaveStore, default: Any) -> None:
    """missing != invalid: an absent store file loads the default (None/() etc)."""
    assert store.load() == default


def assert_corrupt_json_raises_typed_error(
    store: LoadParseSaveStore, error_type: type[Exception]
) -> None:
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{not json", encoding="utf-8")
    try:
        store.load()
    except error_type:
        pass
    else:
        raise AssertionError(f"expected {error_type.__name__} for corrupt JSON")


def assert_unknown_top_level_field_rejected(
    store: LoadParseSaveStore,
    valid_doc: dict[str, object],
    error_type: type[Exception],
    bogus_key: str = "bogus_field",
) -> None:
    doc = dict(valid_doc)
    doc[bogus_key] = 1
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(json.dumps(doc), encoding="utf-8")
    try:
        store.load()
    except error_type as exc:
        assert bogus_key in str(exc)
    else:
        raise AssertionError(f"expected {error_type.__name__} for unknown top-level field")


def assert_wrong_schema_version_rejected(
    store: LoadParseSaveStore,
    valid_doc: dict[str, object],
    error_type: type[Exception],
    bad_version: str,
) -> None:
    doc = dict(valid_doc)
    doc["schema_version"] = bad_version
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(json.dumps(doc), encoding="utf-8")
    try:
        store.load()
    except error_type:
        pass
    else:
        raise AssertionError(f"expected {error_type.__name__} for wrong schema_version")


def assert_root_not_object_rejected(store: LoadParseSaveStore, error_type: type[Exception]) -> None:
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("[1, 2, 3]", encoding="utf-8")
    try:
        store.load()
    except error_type:
        pass
    else:
        raise AssertionError(f"expected {error_type.__name__} for non-object root")


def assert_save_is_atomic_no_tmp_leftover(store: LoadParseSaveStore, value: Any) -> None:
    store.save(value)
    leftovers = [p for p in store.path.parent.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == [], f"atomic write left a .tmp sibling: {leftovers}"


def assert_last_good_snapshot_of_prior_valid_file(
    store: LoadParseSaveStore, first_value: Any, second_value: Any
) -> None:
    """The second save() snapshots the PRIOR valid file's bytes to last_good_path;
    the first save() creates no last-good (nothing prior to snapshot)."""
    store.save(first_value)
    assert not store.last_good_path.exists(), "first save must not create a last-good snapshot"
    prior_bytes = store.path.read_bytes()

    store.save(second_value)
    assert store.last_good_path.is_file()
    assert store.last_good_path.read_bytes() == prior_bytes


def assert_saved_value_reloads_identically(store: LoadParseSaveStore, value: Any) -> None:
    store.save(value)
    assert store.load() == value


# ---------------------------------------------------------------------------
# Simple read/write stores (harness_profile, plugin) — no exceptions, no
# last-good; the contract is: absent -> None, round-trip, canonical on-disk
# shape, idempotent-mtime (no rewrite when bytes match), overwrite on change.
# ---------------------------------------------------------------------------


class ReadWriteStore(Protocol):
    def read(self, states_dir: Path) -> Any: ...

    def write(self, states_dir: Path, value: Any) -> None: ...


def assert_read_write_store_contract(
    store: ReadWriteStore,
    states_dir: Path,
    filename: str,
    first_value: Any,
    second_value: Any,
    canonical_shape: dict[str, object],
) -> None:
    """absent->None / roundtrip / canonical on-disk shape / idempotent-mtime /
    overwrite-on-change, in one shared assertion body."""
    assert store.read(states_dir) is None

    store.write(states_dir, first_value)
    assert store.read(states_dir) == first_value

    path = states_dir / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == canonical_shape

    first_mtime = path.stat().st_mtime_ns
    store.write(states_dir, first_value)  # identical bytes -> no rewrite
    assert path.stat().st_mtime_ns == first_mtime

    store.write(states_dir, second_value)
    assert store.read(states_dir) == second_value
