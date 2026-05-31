"""
Unit tests for the 4 memory atom JSON Schema files (T-MSS-02 / C-1).

Coverage targets:
  - AC-C1-1: All 4 schema files exist under dadaia_workspace/public/schemas/memory/.
  - AC-C1-2: Each schema has "additionalProperties": false at the top-level object.
  - AC-C1-3: memory-product-feature-v1 has all 6 required fields.
  - AC-C1-4: memory-product-index-v1 catalog entries require rank (int) + keywords (array).
  - AC-C1-5: A YAML atom with changelog/history/versions key fails schema validation.
  - AC-C1-6: A valid sample YAML atom for each type passes schema validation.

Field → template-variable mapping:
  See tests/fixtures/memory/MAPPING.md for the authoritative renderer contract.

Schema files:
  dadaia_workspace/public/schemas/memory/memory-architecture-v1.schema.json
  dadaia_workspace/public/schemas/memory/memory-tech-stack-v1.schema.json
  dadaia_workspace/public/schemas/memory/memory-product-index-v1.schema.json
  dadaia_workspace/public/schemas/memory/memory-product-feature-v1.schema.json

Fixtures (tests/fixtures/memory/):
  architecture.valid.yaml
  architecture.invalid-changelog.yaml
  tech-stack.valid.yaml
  tech-stack.invalid-changelog.yaml
  product-index.valid.yaml
  product-index.invalid-changelog.yaml
  product-feature.valid.yaml
  product-feature.invalid-changelog.yaml         (extra field: changelog)
  product-feature.invalid-missing-required.yaml  (missing: purpose)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft7Validator, ValidationError, validate

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent  # specs/features/unit/tests -> repo root
_SCHEMAS_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "schemas" / "memory"
_FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures" / "memory"

_SCHEMA_FILES = {
    "architecture": _SCHEMAS_DIR / "memory-architecture-v1.schema.json",
    "tech-stack": _SCHEMAS_DIR / "memory-tech-stack-v1.schema.json",
    "product-index": _SCHEMAS_DIR / "memory-product-index-v1.schema.json",
    "product-feature": _SCHEMAS_DIR / "memory-product-feature-v1.schema.json",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _is_valid(schema: dict[str, Any], instance: Any) -> bool:
    try:
        validate(instance=instance, schema=schema, cls=Draft7Validator)
        return True
    except ValidationError:
        return False


# ---------------------------------------------------------------------------
# AC-C1-1: Schema files exist
# ---------------------------------------------------------------------------

class TestSchemaFilesExist:
    """AC-C1-1: All 4 schema files must exist under dadaia_workspace/public/schemas/memory/."""

    @pytest.mark.parametrize("key", list(_SCHEMA_FILES.keys()))
    def test_schema_file_exists(self, key: str) -> None:
        schema_path = _SCHEMA_FILES[key]
        assert schema_path.exists(), (
            f"Schema file missing: {schema_path}. "
            f"Expected at dadaia_workspace/public/schemas/memory/{schema_path.name}"
        )

    @pytest.mark.parametrize("key", list(_SCHEMA_FILES.keys()))
    def test_schema_is_valid_json(self, key: str) -> None:
        schema_path = _SCHEMA_FILES[key]
        schema = _load_json(schema_path)
        assert isinstance(schema, dict), f"Schema at {schema_path} is not a JSON object"


# ---------------------------------------------------------------------------
# AC-C1-2: additionalProperties: false at top-level
# ---------------------------------------------------------------------------

class TestAdditionalPropertiesFalse:
    """AC-C1-2: Each schema must have additionalProperties:false at the top-level object (D-5)."""

    @pytest.mark.parametrize("key", list(_SCHEMA_FILES.keys()))
    def test_additional_properties_false(self, key: str) -> None:
        schema = _load_json(_SCHEMA_FILES[key])
        assert schema.get("additionalProperties") is False, (
            f"Schema '{key}' missing 'additionalProperties: false' at top level. "
            "This is D-5 (atomicity structural guarantee) — a changelog/history/versions "
            "field must be structurally impossible, not just heuristically rejected."
        )


# ---------------------------------------------------------------------------
# AC-C1-3: memory-product-feature-v1 has all 6 required fields
# ---------------------------------------------------------------------------

class TestFeatureSchemaRequiredFields:
    """AC-C1-3: memory-product-feature-v1 must have all 6 content fields as required."""

    _REQUIRED_6 = {"purpose", "flow_steps", "typical_trigger", "differential", "runtime_state", "dependencies"}

    def test_all_six_required_fields_present(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-feature"])
        required = set(schema.get("required", []))
        missing = self._REQUIRED_6 - required
        assert not missing, (
            f"memory-product-feature-v1 missing required fields: {sorted(missing)}. "
            "All 6 fields must be required per SPEC §C-1 (AC-C1-3)."
        )

    def test_flow_steps_typed_as_array_of_strings(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-feature"])
        flow_steps_prop = schema["properties"]["flow_steps"]
        assert flow_steps_prop["type"] == "array", "flow_steps must be type: array"
        assert flow_steps_prop["items"]["type"] == "string", "flow_steps items must be type: string"

    def test_runtime_state_typed_as_array_of_strings(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-feature"])
        rs_prop = schema["properties"]["runtime_state"]
        assert rs_prop["type"] == "array"
        assert rs_prop["items"]["type"] == "string"

    def test_dependencies_typed_as_array_of_strings(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-feature"])
        dep_prop = schema["properties"]["dependencies"]
        assert dep_prop["type"] == "array"
        assert dep_prop["items"]["type"] == "string"


# ---------------------------------------------------------------------------
# AC-C1-4: memory-product-index-v1 catalog entries require rank + keywords
# ---------------------------------------------------------------------------

class TestProductIndexCatalogEntryFields:
    """AC-C1-4: catalog entries must require rank (integer) and keywords (array of strings)."""

    def test_catalog_property_exists_and_is_array(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-index"])
        assert "catalog" in schema["properties"], "catalog property missing from product-index schema"
        assert schema["properties"]["catalog"]["type"] == "array"

    def test_catalog_entry_requires_rank(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-index"])
        item_schema = schema["properties"]["catalog"]["items"]
        assert "rank" in item_schema.get("required", []), (
            "catalog entry 'rank' must be required (AC-C1-4). "
            "rank encodes daily-relevance ordering for Phase-1 catalog.json."
        )

    def test_catalog_entry_rank_is_integer(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-index"])
        item_schema = schema["properties"]["catalog"]["items"]
        assert item_schema["properties"]["rank"]["type"] == "integer", "rank must be integer"

    def test_catalog_entry_requires_keywords(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-index"])
        item_schema = schema["properties"]["catalog"]["items"]
        assert "keywords" in item_schema.get("required", []), (
            "catalog entry 'keywords' must be required (AC-C1-4). "
            "keywords are consumed by Phase-1 catalog.json generator."
        )

    def test_catalog_entry_keywords_is_array_of_strings(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-index"])
        item_schema = schema["properties"]["catalog"]["items"]
        kw_prop = item_schema["properties"]["keywords"]
        assert kw_prop["type"] == "array"
        assert kw_prop["items"]["type"] == "string"

    def test_catalog_entry_additional_properties_false(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-index"])
        item_schema = schema["properties"]["catalog"]["items"]
        assert item_schema.get("additionalProperties") is False, (
            "catalog entry items should have additionalProperties:false to prevent drift"
        )


# ---------------------------------------------------------------------------
# AC-C1-5: changelog/history/versions key fails schema validation
# ---------------------------------------------------------------------------

class TestChangelogKeyFails:
    """AC-C1-5: A YAML atom with changelog/history/versions key must fail schema validation."""

    def test_architecture_changelog_fails(self) -> None:
        schema = _load_json(_SCHEMA_FILES["architecture"])
        instance = _load_yaml(_FIXTURES_DIR / "architecture.invalid-changelog.yaml")
        assert "changelog" in instance, "Fixture must contain 'changelog' key"
        assert not _is_valid(schema, instance), (
            "architecture: atom with 'changelog' key must fail schema validation (D-5 / AC-C1-5)"
        )

    def test_tech_stack_history_fails(self) -> None:
        schema = _load_json(_SCHEMA_FILES["tech-stack"])
        instance = _load_yaml(_FIXTURES_DIR / "tech-stack.invalid-changelog.yaml")
        assert "history" in instance, "Fixture must contain 'history' key"
        assert not _is_valid(schema, instance), (
            "tech-stack: atom with 'history' key must fail schema validation (D-5 / AC-C1-5)"
        )

    def test_product_index_versions_fails(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-index"])
        instance = _load_yaml(_FIXTURES_DIR / "product-index.invalid-changelog.yaml")
        assert "versions" in instance, "Fixture must contain 'versions' key"
        assert not _is_valid(schema, instance), (
            "product-index: atom with 'versions' key must fail schema validation (D-5 / AC-C1-5)"
        )

    def test_product_feature_changelog_fails(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-feature"])
        instance = _load_yaml(_FIXTURES_DIR / "product-feature.invalid-changelog.yaml")
        assert "changelog" in instance, "Fixture must contain 'changelog' key"
        assert not _is_valid(schema, instance), (
            "product-feature: atom with 'changelog' key must fail schema validation (D-5 / AC-C1-5)"
        )

    def test_validation_error_message_references_additional_properties(self) -> None:
        """The ValidationError for an extra field must be an additionalProperties violation."""
        schema = _load_json(_SCHEMA_FILES["product-feature"])
        instance = _load_yaml(_FIXTURES_DIR / "product-feature.invalid-changelog.yaml")
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=instance, schema=schema, cls=Draft7Validator)
        error = exc_info.value
        # The error must reference 'changelog' as an additional property
        assert "changelog" in error.message or "Additional properties" in error.message, (
            f"Expected additionalProperties error mentioning 'changelog', got: {error.message}"
        )


# ---------------------------------------------------------------------------
# AC-C1-5 (continued): missing required field also fails
# ---------------------------------------------------------------------------

class TestMissingRequiredFieldFails:
    """Missing required field in product-feature must fail schema validation."""

    def test_product_feature_missing_purpose_fails(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-feature"])
        instance = _load_yaml(_FIXTURES_DIR / "product-feature.invalid-missing-required.yaml")
        assert "purpose" not in instance, "Fixture must NOT contain 'purpose' field"
        assert not _is_valid(schema, instance), (
            "product-feature: atom missing 'purpose' must fail schema validation"
        )

    def test_validation_error_message_references_purpose(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-feature"])
        instance = _load_yaml(_FIXTURES_DIR / "product-feature.invalid-missing-required.yaml")
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=instance, schema=schema, cls=Draft7Validator)
        error = exc_info.value
        assert "purpose" in error.message or "'purpose' is a required property" in error.message, (
            f"Expected error mentioning 'purpose', got: {error.message}"
        )


# ---------------------------------------------------------------------------
# AC-C1-6: Valid fixtures pass schema validation
# ---------------------------------------------------------------------------

class TestValidFixturesPass:
    """AC-C1-6: Valid sample atoms for each of the 4 types must pass schema validation."""

    def test_architecture_valid_passes(self) -> None:
        schema = _load_json(_SCHEMA_FILES["architecture"])
        instance = _load_yaml(_FIXTURES_DIR / "architecture.valid.yaml")
        try:
            validate(instance=instance, schema=schema, cls=Draft7Validator)
        except ValidationError as exc:
            pytest.fail(f"Valid architecture fixture failed schema validation: {exc.message}")

    def test_tech_stack_valid_passes(self) -> None:
        schema = _load_json(_SCHEMA_FILES["tech-stack"])
        instance = _load_yaml(_FIXTURES_DIR / "tech-stack.valid.yaml")
        try:
            validate(instance=instance, schema=schema, cls=Draft7Validator)
        except ValidationError as exc:
            pytest.fail(f"Valid tech-stack fixture failed schema validation: {exc.message}")

    def test_product_index_valid_passes(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-index"])
        instance = _load_yaml(_FIXTURES_DIR / "product-index.valid.yaml")
        try:
            validate(instance=instance, schema=schema, cls=Draft7Validator)
        except ValidationError as exc:
            pytest.fail(f"Valid product-index fixture failed schema validation: {exc.message}")

    def test_product_feature_valid_passes(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-feature"])
        instance = _load_yaml(_FIXTURES_DIR / "product-feature.valid.yaml")
        try:
            validate(instance=instance, schema=schema, cls=Draft7Validator)
        except ValidationError as exc:
            pytest.fail(f"Valid product-feature fixture failed schema validation: {exc.message}")

    def test_product_feature_valid_has_all_six_required_fields(self) -> None:
        """Sanity check: valid fixture must actually contain all 6 required fields."""
        instance = _load_yaml(_FIXTURES_DIR / "product-feature.valid.yaml")
        required_6 = {"purpose", "flow_steps", "typical_trigger", "differential", "runtime_state", "dependencies"}
        present = set(instance.keys())
        missing = required_6 - present
        assert not missing, f"Valid product-feature fixture is missing fields: {sorted(missing)}"

    def test_product_index_valid_catalog_entries_have_rank_and_keywords(self) -> None:
        """Sanity check: valid product-index fixture catalog entries must have rank + keywords."""
        instance = _load_yaml(_FIXTURES_DIR / "product-index.valid.yaml")
        for entry in instance.get("catalog", []):
            assert "rank" in entry, f"Catalog entry missing 'rank': {entry}"
            assert "keywords" in entry, f"Catalog entry missing 'keywords': {entry}"
            assert isinstance(entry["rank"], int), f"rank must be int, got {type(entry['rank'])}"
            assert isinstance(entry["keywords"], list), f"keywords must be list, got {type(entry['keywords'])}"


# ---------------------------------------------------------------------------
# Additional structural invariant tests
# ---------------------------------------------------------------------------

class TestSchemaStructuralInvariants:
    """Additional invariants derived from SPEC §C-1 and OWASP-safe design."""

    @pytest.mark.parametrize("key", list(_SCHEMA_FILES.keys()))
    def test_schema_has_schema_keyword(self, key: str) -> None:
        """Each schema must declare its $schema (draft-07)."""
        schema = _load_json(_SCHEMA_FILES[key])
        assert "$schema" in schema, f"Schema '{key}' missing '$schema' keyword"
        assert "draft-07" in schema["$schema"], (
            f"Schema '{key}' must use draft-07 for broadest jsonschema Python lib support (SPEC OQ-1)"
        )

    @pytest.mark.parametrize("key", list(_SCHEMA_FILES.keys()))
    def test_schema_has_id(self, key: str) -> None:
        schema = _load_json(_SCHEMA_FILES[key])
        assert "$id" in schema, f"Schema '{key}' missing '$id'"

    @pytest.mark.parametrize("key", list(_SCHEMA_FILES.keys()))
    def test_schema_type_is_object(self, key: str) -> None:
        schema = _load_json(_SCHEMA_FILES[key])
        assert schema.get("type") == "object", f"Schema '{key}' top-level type must be 'object'"

    @pytest.mark.parametrize("key", list(_SCHEMA_FILES.keys()))
    def test_schema_has_required_array(self, key: str) -> None:
        schema = _load_json(_SCHEMA_FILES[key])
        assert "required" in schema, f"Schema '{key}' has no 'required' array at top level"
        assert isinstance(schema["required"], list), f"Schema '{key}' required must be a list"
        assert len(schema["required"]) > 0, f"Schema '{key}' required array is empty"

    def test_architecture_schema_does_not_allow_changelog(self) -> None:
        schema = _load_json(_SCHEMA_FILES["architecture"])
        assert "changelog" not in schema.get("properties", {}), (
            "changelog must NOT appear in architecture schema properties (D-5)"
        )

    def test_feature_schema_does_not_allow_changelog(self) -> None:
        schema = _load_json(_SCHEMA_FILES["product-feature"])
        assert "changelog" not in schema.get("properties", {}), (
            "changelog must NOT appear in product-feature schema properties (D-5)"
        )
        assert "history" not in schema.get("properties", {}), (
            "history must NOT appear in product-feature schema properties (D-5)"
        )
        assert "versions" not in schema.get("properties", {}), (
            "versions must NOT appear in product-feature schema properties (D-5)"
        )
