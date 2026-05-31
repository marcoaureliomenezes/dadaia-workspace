"""Unit tests for ``dadaia migrate memory-yaml`` (T-MSS-07 / C-7).

Coverage:
- AC-C7-1: ``--help`` exits 0.
- AC-C7-2: Running on a real HTML atom produces a .yaml that passes ``validate_atom``.
- AC-C7-4: Second run does NOT overwrite existing .yaml (idempotent guard).
- All 4 atom types covered (feature + architecture + tech-stack + product-index).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from dadaia_workspace.cli.commands.migrate import app
from dadaia_workspace.features.specs.renderer import validate_atom

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Resolve paths to real HTML atoms in this repo (used in copy-to-tmp_path tests).
_REPO_ROOT = Path(__file__).resolve().parents[4]  # tests/unit/cli/commands/ → repo root
_MEMORY_DIR = _REPO_ROOT / "specs" / "memory"

_ARCHITECTURE_HTML = _MEMORY_DIR / "architecture.html"
_TECH_STACK_HTML = _MEMORY_DIR / "tech-stack.html"
_PRODUCT_INDEX_HTML = _MEMORY_DIR / "product" / "index.html"
_WORKSPACE_INIT_HTML = _MEMORY_DIR / "product" / "workspace-init.html"


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _copy_atom_to_tmp(tmp_path: Path, src: Path) -> Path:
    """Copy an HTML atom to a temp directory, preserving relative structure."""
    dest = tmp_path / src.name
    shutil.copy2(src, dest)
    return dest


def _copy_feature_atom_to_tmp(tmp_path: Path, src: Path) -> Path:
    """Copy a product/<slug>.html atom into tmp_path/product/ sub-directory."""
    product_dir = tmp_path / "product"
    product_dir.mkdir(exist_ok=True)
    dest = product_dir / src.name
    shutil.copy2(src, dest)
    return dest


def _copy_index_atom_to_tmp(tmp_path: Path, src: Path) -> Path:
    """Copy product/index.html into tmp_path/product/index.html."""
    product_dir = tmp_path / "product"
    product_dir.mkdir(exist_ok=True)
    dest = product_dir / "index.html"
    shutil.copy2(src, dest)
    return dest


# ---------------------------------------------------------------------------
# AC-C7-1: --help exits 0
# ---------------------------------------------------------------------------


def test_help_exits_zero(runner: CliRunner) -> None:
    """AC-C7-1: ``dadaia migrate memory-yaml --help`` exits 0."""
    result = runner.invoke(app, ["memory-yaml", "--help"])
    assert result.exit_code == 0, f"--help exited {result.exit_code}:\n{result.output}"
    assert "migrate" in result.output.lower() or "html" in result.output.lower()


# ---------------------------------------------------------------------------
# AC-C7-2 — Feature atom (product/<slug>.html)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _WORKSPACE_INIT_HTML.exists(),
    reason="workspace-init.html not present in this checkout",
)
def test_feature_atom_migration_validates(tmp_path: Path, runner: CliRunner) -> None:
    """AC-C7-2: Migrating a real feature HTML atom produces a schema-valid YAML."""
    html_file = _copy_feature_atom_to_tmp(tmp_path, _WORKSPACE_INIT_HTML)

    result = runner.invoke(app, ["memory-yaml", str(html_file)])
    assert result.exit_code == 0, f"Command failed:\n{result.output}"

    yaml_file = html_file.with_suffix(".yaml")
    assert yaml_file.exists(), f"Expected {yaml_file} to be created"

    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    # Must not raise
    validate_atom(data, "memory-product-feature-v1")

    # Required fields must be present
    for field in ("purpose", "flow_steps", "typical_trigger", "differential", "runtime_state", "dependencies"):
        assert field in data, f"Required field '{field}' missing from extracted YAML"

    # flow_steps must be a list with at least one item
    assert isinstance(data["flow_steps"], list) and len(data["flow_steps"]) >= 1
    # runtime_state and dependencies must be lists
    assert isinstance(data["runtime_state"], list) and len(data["runtime_state"]) >= 1
    assert isinstance(data["dependencies"], list) and len(data["dependencies"]) >= 1


# ---------------------------------------------------------------------------
# AC-C7-4 — Idempotent guard (feature atom)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _WORKSPACE_INIT_HTML.exists(),
    reason="workspace-init.html not present in this checkout",
)
def test_second_run_does_not_overwrite(tmp_path: Path, runner: CliRunner) -> None:
    """AC-C7-4: A second run does not overwrite an existing .yaml file."""
    html_file = _copy_feature_atom_to_tmp(tmp_path, _WORKSPACE_INIT_HTML)

    # First run — should succeed
    result1 = runner.invoke(app, ["memory-yaml", str(html_file)])
    assert result1.exit_code == 0, f"First run failed:\n{result1.output}"

    yaml_file = html_file.with_suffix(".yaml")
    assert yaml_file.exists()

    content_after_first = yaml_file.read_text(encoding="utf-8")
    mtime_after_first = yaml_file.stat().st_mtime

    # Second run — must be a no-op
    result2 = runner.invoke(app, ["memory-yaml", str(html_file)])
    assert result2.exit_code == 0, f"Second run failed:\n{result2.output}"

    content_after_second = yaml_file.read_text(encoding="utf-8")
    mtime_after_second = yaml_file.stat().st_mtime

    assert content_after_first == content_after_second, "YAML content changed on second run"
    assert mtime_after_first == mtime_after_second, "YAML mtime changed on second run"

    # Warning must be emitted on second run
    assert "warn" in result2.output.lower() or "skip" in result2.output.lower(), (
        f"Expected a skip/warn message on second run, got:\n{result2.output}"
    )


# ---------------------------------------------------------------------------
# AC-C7-2 — Architecture atom
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _ARCHITECTURE_HTML.exists(),
    reason="architecture.html not present in this checkout",
)
def test_architecture_atom_migration_validates(tmp_path: Path, runner: CliRunner) -> None:
    """AC-C7-2 (architecture): Migration produces a schema-valid YAML."""
    html_file = _copy_atom_to_tmp(tmp_path, _ARCHITECTURE_HTML)

    result = runner.invoke(app, ["memory-yaml", str(html_file)])
    assert result.exit_code == 0, f"Command failed:\n{result.output}"

    yaml_file = html_file.with_suffix(".yaml")
    assert yaml_file.exists()

    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    # Must not raise
    validate_atom(data, "memory-architecture-v1")

    for field in ("overview", "layers", "dependency_rules_diagram", "data_flow_diagram", "runtime_state"):
        assert field in data, f"Required field '{field}' missing"

    assert isinstance(data["layers"], list) and len(data["layers"]) >= 1
    assert isinstance(data["runtime_state"], list) and len(data["runtime_state"]) >= 1


# ---------------------------------------------------------------------------
# AC-C7-2 — Tech-stack atom
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _TECH_STACK_HTML.exists(),
    reason="tech-stack.html not present in this checkout",
)
def test_tech_stack_atom_migration_validates(tmp_path: Path, runner: CliRunner) -> None:
    """AC-C7-2 (tech-stack): Migration produces a schema-valid YAML."""
    html_file = _copy_atom_to_tmp(tmp_path, _TECH_STACK_HTML)

    result = runner.invoke(app, ["memory-yaml", str(html_file)])
    assert result.exit_code == 0, f"Command failed:\n{result.output}"

    yaml_file = html_file.with_suffix(".yaml")
    assert yaml_file.exists()

    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    validate_atom(data, "memory-tech-stack-v1")

    for field in ("languages", "runtimes", "dependencies", "constraints", "canonical_commands"):
        assert field in data, f"Required field '{field}' missing"

    assert isinstance(data["languages"], list) and len(data["languages"]) >= 1
    assert isinstance(data["runtimes"], list) and len(data["runtimes"]) >= 1


# ---------------------------------------------------------------------------
# AC-C7-2 — Product-index atom
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _PRODUCT_INDEX_HTML.exists(),
    reason="product/index.html not present in this checkout",
)
def test_product_index_atom_migration_validates(tmp_path: Path, runner: CliRunner) -> None:
    """AC-C7-2 (product-index): Migration produces a schema-valid YAML."""
    html_file = _copy_index_atom_to_tmp(tmp_path, _PRODUCT_INDEX_HTML)

    result = runner.invoke(app, ["memory-yaml", str(html_file)])
    assert result.exit_code == 0, f"Command failed:\n{result.output}"

    yaml_file = html_file.with_suffix(".yaml")
    assert yaml_file.exists()

    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    validate_atom(data, "memory-product-index-v1")

    for field in ("vision_oneliner", "vision_paragraph", "users", "catalog", "capability_map_diagram", "non_goals"):
        assert field in data, f"Required field '{field}' missing"

    assert isinstance(data["catalog"], list) and len(data["catalog"]) >= 1
    # Each catalog entry must have rank (integer ≥ 1) and keywords (list)
    entry = data["catalog"][0]
    assert isinstance(entry["rank"], int) and entry["rank"] >= 1
    assert isinstance(entry["keywords"], list) and len(entry["keywords"]) >= 1


# ---------------------------------------------------------------------------
# AC-C7-4 — Idempotent guard (architecture atom)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _ARCHITECTURE_HTML.exists(),
    reason="architecture.html not present in this checkout",
)
def test_architecture_second_run_no_overwrite(tmp_path: Path, runner: CliRunner) -> None:
    """AC-C7-4 (architecture): Second run does not overwrite .yaml."""
    html_file = _copy_atom_to_tmp(tmp_path, _ARCHITECTURE_HTML)

    runner.invoke(app, ["memory-yaml", str(html_file)])
    yaml_file = html_file.with_suffix(".yaml")
    assert yaml_file.exists()
    content_first = yaml_file.read_text(encoding="utf-8")

    result2 = runner.invoke(app, ["memory-yaml", str(html_file)])
    assert result2.exit_code == 0
    assert yaml_file.read_text(encoding="utf-8") == content_first
    assert "warn" in result2.output.lower() or "skip" in result2.output.lower()


# ---------------------------------------------------------------------------
# Batch mode (--all) — minimal specs/ tree
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _WORKSPACE_INIT_HTML.exists() or not _ARCHITECTURE_HTML.exists(),
    reason="Real HTML atoms not present in this checkout",
)
def test_batch_all_migrates_multiple_atoms(tmp_path: Path, runner: CliRunner) -> None:
    """Batch --all mode discovers and migrates atoms under specs/memory/."""
    # Build a minimal specs/ tree in tmp_path
    specs_dir = tmp_path / "specs"
    memory_dir = specs_dir / "memory"
    memory_dir.mkdir(parents=True)
    product_dir = memory_dir / "product"
    product_dir.mkdir()

    shutil.copy2(_ARCHITECTURE_HTML, memory_dir / "architecture.html")
    shutil.copy2(_WORKSPACE_INIT_HTML, product_dir / "workspace-init.html")

    result = runner.invoke(app, ["memory-yaml", "--all", "--specs-dir", str(specs_dir)])
    assert result.exit_code == 0, f"Batch --all failed:\n{result.output}"

    assert (memory_dir / "architecture.yaml").exists()
    assert (product_dir / "workspace-init.yaml").exists()

    # Both should validate
    arch_data = yaml.safe_load((memory_dir / "architecture.yaml").read_text())
    validate_atom(arch_data, "memory-architecture-v1")

    feat_data = yaml.safe_load((product_dir / "workspace-init.yaml").read_text())
    validate_atom(feat_data, "memory-product-feature-v1")


# ---------------------------------------------------------------------------
# Error: no argument and no --all
# ---------------------------------------------------------------------------


def test_no_argument_exits_nonzero(runner: CliRunner) -> None:
    """Running memory-yaml with no path and no --all should exit non-zero."""
    result = runner.invoke(app, ["memory-yaml"])
    assert result.exit_code != 0, "Expected non-zero exit when no arguments provided"


# ---------------------------------------------------------------------------
# Error: --all and positional are mutually exclusive
# ---------------------------------------------------------------------------


def test_all_and_path_are_exclusive(tmp_path: Path, runner: CliRunner) -> None:
    """--all and a positional path must be mutually exclusive."""
    result = runner.invoke(app, ["memory-yaml", "--all", "some/path.html"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Minimal synthetic HTML — feature atom with all sections
# ---------------------------------------------------------------------------

_SYNTHETIC_FEATURE_HTML = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Test Feature</title></head>
<body>
<h1>test-feature</h1>
<p class="meta">CLI: dadaia test</p>

<section id="purpose">
  <h2>Propósito</h2>
  <p>This is the purpose of the feature.</p>
  <p>Second paragraph of purpose.</p>
</section>

<section id="flow">
  <h2>Fluxo</h2>
  <ol class="flow">
    <li>Step one.</li>
    <li>Step two.</li>
  </ol>
</section>

<section id="trigger">
  <h2>Trigger</h2>
  <p>When the operator needs to test something.</p>
</section>

<section id="differential">
  <h2>Diferencial</h2>
  <p>It makes testing easier.</p>
</section>

<section id="runtime-state">
  <h2>Estado runtime</h2>
  <ul>
    <li>.dadaia/states/test.json — test state file</li>
    <li>.dadaia/logs/test.log — test log</li>
  </ul>
</section>

<section id="dependencies">
  <h2>Dependências</h2>
  <ul>
    <li>workspace-init must run first.</li>
    <li>context-management must be active.</li>
  </ul>
</section>

</body>
</html>
"""


def test_synthetic_feature_html_validates(tmp_path: Path, runner: CliRunner) -> None:
    """Synthetic feature HTML with all sections produces a valid YAML."""
    product_dir = tmp_path / "product"
    product_dir.mkdir()
    html_file = product_dir / "test-feature.html"
    html_file.write_text(_SYNTHETIC_FEATURE_HTML, encoding="utf-8")

    result = runner.invoke(app, ["memory-yaml", str(html_file)])
    assert result.exit_code == 0, f"Command failed:\n{result.output}"

    yaml_file = product_dir / "test-feature.yaml"
    assert yaml_file.exists()

    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    validate_atom(data, "memory-product-feature-v1")

    # Check content was actually extracted (not all placeholders)
    assert "purpose" in data["purpose"].lower() or "TODO" not in data["purpose"]
    assert data["flow_steps"] == ["Step one.", "Step two."]
    assert "operator" in data["typical_trigger"].lower()
    assert data["runtime_state"] == [
        ".dadaia/states/test.json — test state file",
        ".dadaia/logs/test.log — test log",
    ]
    assert data["dependencies"] == [
        "workspace-init must run first.",
        "context-management must be active.",
    ]
