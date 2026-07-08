"""Unit tests for the public-doctor model-resolution check (T-010-24, R8b).

Closes the `model-catalog-modelmap-pricing-drift-no-registry` bug's doctor half:
every ``model:`` frontmatter value across canonical ``public/agents/*.md`` must
resolve in ``core.model_registry.REGISTRY``, and the three derived/source key-sets
(``MODEL_MAP`` keys, ``PRICING_TABLE`` keys, ``REGISTRY`` claude ids) must be
identical. Any breach is an ERROR line that makes ``dadaia public doctor`` exit
nonzero (emitted with the ``[drift]`` prefix the CLI already treats as failing).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.public.model_resolution import check_model_resolution


def _write_agent(agents_dir: Path, name: str, model: str) -> None:
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f"{name}.md").write_text(
        f"---\nname: {name}\nmodel: {model}\n---\n\n# {name}\n",
        encoding="utf-8",
    )


def _has_error(reports: list[str]) -> bool:
    """An ERROR line is any [drift]/[error]/[fail] line — all exit-nonzero in the CLI."""
    return any(line.startswith(("[drift]", "[error]", "[fail]")) for line in reports)


# ---------------------------------------------------------------------------
# 1. Unknown-model fixture ⇒ error
# ---------------------------------------------------------------------------


def test_unknown_model_in_agent_frontmatter_errors(tmp_path: Path) -> None:
    public_dir = tmp_path / "public"
    _write_agent(public_dir / "agents", "ghost-agent", "claude-does-not-exist")

    reports = check_model_resolution(public_dir)

    assert _has_error(reports)
    offending = [r for r in reports if "ghost-agent" in r]
    assert offending, reports
    assert "claude-does-not-exist" in offending[0]
    # No spurious [ok] model-resolution when an unknown id is present.
    assert "[ok] model-resolution" not in reports


def test_known_model_in_agent_frontmatter_ok(tmp_path: Path) -> None:
    public_dir = tmp_path / "public"
    _write_agent(public_dir / "agents", "good-agent", "claude-fable-5")
    _write_agent(public_dir / "agents", "another", "claude-opus-4-8")

    reports = check_model_resolution(public_dir)

    assert not _has_error(reports)
    assert "[ok] model-resolution" in reports


def test_missing_agents_dir_is_clean(tmp_path: Path) -> None:
    # No agents dir → only the key-set check runs (current tree is consistent).
    public_dir = tmp_path / "public"
    public_dir.mkdir()

    reports = check_model_resolution(public_dir)

    assert not _has_error(reports)
    assert "[ok] model-resolution" in reports


# ---------------------------------------------------------------------------
# 2. Key-set desync fixture (monkeypatched derived view) ⇒ error
# ---------------------------------------------------------------------------


def test_keyset_desync_modelmap_vs_pricing_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hand-edited MODEL_MAP that drops a key the others keep ⇒ ERROR."""
    import dadaia_workspace.features.public.model_resolution as mod

    desynced = {"claude-fable-5": "gpt-5.5"}  # missing every other registered id
    monkeypatch.setattr(mod, "MODEL_MAP", desynced)

    public_dir = tmp_path / "public"
    public_dir.mkdir()

    reports = check_model_resolution(public_dir)

    assert _has_error(reports)
    desync_lines = [r for r in reports if "key-set" in r.lower() or "desync" in r.lower()]
    assert desync_lines, reports
    assert "[ok] model-resolution" not in reports


def test_pricing_keyset_is_registry_derived_not_cross_feature_import(
    tmp_path: Path,
) -> None:
    """PRICING_TABLE is no longer imported into model_resolution (audit A3 fix).

    The cross-feature ``features.public -> features.telemetry.pricing`` import was
    removed: ``PRICING_TABLE`` is a derived view over ``core.model_registry`` so the
    registry claude-id set IS the pricing key-set by construction, and the doctor
    check now computes it from ``REGISTRY`` directly. This test pins that the symbol
    is gone from the module namespace (so the old monkeypatch vector cannot silently
    reappear) and that the live tree still resolves clean. The genuine
    PRICING_TABLE↔registry coherence guard lives in
    ``tests/unit/features/telemetry/test_pricing.py`` (key-set equality assertions).
    """
    import dadaia_workspace.features.public.model_resolution as mod

    assert not hasattr(mod, "PRICING_TABLE"), (
        "model_resolution must not import PRICING_TABLE — that was the cross-feature "
        "edge removed in audit A3; the pricing key-set is registry-derived."
    )

    public_dir = tmp_path / "public"
    public_dir.mkdir()

    reports = check_model_resolution(public_dir)

    assert not _has_error(reports)
    assert "[ok] model-resolution" in reports


# ---------------------------------------------------------------------------
# 3. Current tree ⇒ ok (real canonical public/ dir)
# ---------------------------------------------------------------------------


def test_current_tree_resolves_clean() -> None:
    """The live canonical public/ tree (opus-4-8 deep agents + etc) resolves ⇒ [ok]."""
    public_dir = Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public"
    assert public_dir.is_dir(), public_dir

    reports = check_model_resolution(public_dir)

    assert not _has_error(reports), reports
    assert "[ok] model-resolution" in reports


# ---------------------------------------------------------------------------
# v0.1.65 FR7 (T-65-09) — resolved-roster + plugin staged-model validation
# ---------------------------------------------------------------------------


def test_resolved_roster_validates_against_registry_and_vocab(tmp_path: Path) -> None:
    """FR7: check_model_resolution validates the RESOLVED (model, effort) per core
    agent — a synthetic overlay carrying an out-of-registry model errors."""
    from dadaia_workspace.core.models.agent_model_policy import (
        AgentModelOverride,
        AgentModelPolicyOverlay,
    )

    public_dir = tmp_path / "public"
    public_dir.mkdir()
    bad_overlay = AgentModelPolicyOverlay(
        applied_template=None,
        overrides={"software-engineer": AgentModelOverride(model="claude-ghost-9")},
    )
    reports = check_model_resolution(public_dir, overlay=bad_overlay)
    assert _has_error(reports), reports
    assert any("software-engineer" in line for line in reports), reports


def test_resolved_roster_clean_with_valid_overlay(tmp_path: Path) -> None:
    from dadaia_workspace.core.models.agent_model_policy import AgentModelPolicyOverlay

    public_dir = tmp_path / "public"
    public_dir.mkdir()
    overlay = AgentModelPolicyOverlay(applied_template="subscription-saver", overrides={})
    reports = check_model_resolution(public_dir, overlay=overlay)
    assert reports == ["[ok] model-resolution"], reports


def test_plugin_staged_model_must_resolve_in_registry(tmp_path: Path) -> None:
    """FR7: plugin pack staged frontmatter models are validated too."""
    public_dir = tmp_path / "public"
    _write_agent(public_dir / "plugins" / "somepack" / "agents", "pack-agent", "claude-bogus-1")
    reports = check_model_resolution(public_dir)
    assert _has_error(reports), reports
    assert any("pack-agent" in line for line in reports), reports
