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
# Keyset desync — the drift bug this check exists to close
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


# ---------------------------------------------------------------------------
# Live-tree resolves clean (real canonical public/ dir)
# ---------------------------------------------------------------------------


def test_current_tree_resolves_clean() -> None:
    """The live canonical public/ tree (opus-4-8 deep agents + etc) resolves ⇒ [ok]."""
    public_dir = Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public"
    assert public_dir.is_dir(), public_dir

    reports = check_model_resolution(public_dir)

    assert not _has_error(reports), reports
    assert "[ok] model-resolution" in reports

    # PRICING_TABLE is no longer imported into model_resolution (audit A3 fix): the
    # cross-feature `features.public -> features.telemetry.pricing` import was removed,
    # since PRICING_TABLE is a derived view over core.model_registry (the registry
    # claude-id set IS the pricing key-set by construction). Pins the symbol is gone
    # from the module namespace so the old monkeypatch vector cannot silently reappear.
    import dadaia_workspace.features.public.model_resolution as mod

    assert not hasattr(mod, "PRICING_TABLE"), (
        "model_resolution must not import PRICING_TABLE — that was the cross-feature "
        "edge removed in audit A3; the pricing key-set is registry-derived."
    )


# ---------------------------------------------------------------------------
# Unknown-model / overlay / plugin variants — 1 param matrix
# ---------------------------------------------------------------------------


def test_unknown_model_variants(
    tmp_path: Path,
) -> None:
    """Unknown model ids surface as ERROR across every source: agent frontmatter,
    resolved overlay (FR7 T-65-09), and plugin pack staged frontmatter."""
    from dadaia_workspace.core.models.agent_model_policy import (
        AgentModelOverride,
        AgentModelPolicyOverlay,
    )

    # agent frontmatter
    public_dir = tmp_path / "agent"
    _write_agent(public_dir / "agents", "ghost-agent", "claude-does-not-exist")
    reports = check_model_resolution(public_dir)
    assert _has_error(reports)
    offending = [r for r in reports if "ghost-agent" in r]
    assert offending, reports
    assert "claude-does-not-exist" in offending[0]
    assert "[ok] model-resolution" not in reports

    # resolved overlay
    overlay_dir = tmp_path / "overlay"
    overlay_dir.mkdir()
    bad_overlay = AgentModelPolicyOverlay(
        applied_template=None,
        overrides={"software-engineer": AgentModelOverride(model="claude-ghost-9")},
    )
    overlay_reports = check_model_resolution(overlay_dir, overlay=bad_overlay)
    assert _has_error(overlay_reports), overlay_reports
    assert any("software-engineer" in line for line in overlay_reports), overlay_reports

    # valid overlay stays clean
    clean_overlay_dir = tmp_path / "overlay-clean"
    clean_overlay_dir.mkdir()
    good_overlay = AgentModelPolicyOverlay(applied_template="subscription-saver", overrides={})
    clean_reports = check_model_resolution(clean_overlay_dir, overlay=good_overlay)
    assert clean_reports == ["[ok] model-resolution"], clean_reports

    # known model in agent frontmatter stays clean
    known_dir = tmp_path / "known"
    _write_agent(known_dir / "agents", "good-agent", "claude-fable-5")
    _write_agent(known_dir / "agents", "another", "claude-opus-4-8")
    known_reports = check_model_resolution(known_dir)
    assert not _has_error(known_reports)
    assert "[ok] model-resolution" in known_reports

    # plugin pack staged frontmatter
    plugin_dir = tmp_path / "plugin"
    _write_agent(plugin_dir / "plugins" / "somepack" / "agents", "pack-agent", "claude-bogus-1")
    plugin_reports = check_model_resolution(plugin_dir)
    assert _has_error(plugin_reports), plugin_reports
    assert any("pack-agent" in line for line in plugin_reports), plugin_reports
