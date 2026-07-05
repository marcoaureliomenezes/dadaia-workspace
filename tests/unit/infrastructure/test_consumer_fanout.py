"""FR4 (v0.1.58) — registry-based consumer ``AGENTS.md`` fan-out.

Detection moved off the dead in-repo ``.dadaia/agentic/`` marker onto the
workspace registry ``.dadaia/states/spec_contexts.json`` (Ruling G/H): the
repo-cleanliness law forbids ``.dadaia/`` inside a repo working tree, so the
old marker made the fan-out empty by construction. These tests assert:

- **AC-6** — the fan-out fires for a registry-listed, *marker-less* on-disk
  consumer repo (alive OR dead — Ruling H); a registry context with no on-disk
  repo is skipped without error; the self-repo is skipped; the tri-copy
  (``specs/AGENTS.md`` / ``specs/memory/AGENTS.md``) is never written (Ruling I).
- **A5 / Ruling L** — a divergent (hand-edited) consumer root ``AGENTS.md`` is
  restored to canonical AND ``_write_pair`` emits a DISTINCT
  ``[updated] ... (overwrote divergent workspace-law copy)`` line (never a
  silent ``[ok]``); a nested subtree ``repos/<slug>/src/AGENTS.md`` is never
  touched.
- **AC-7** — ``_doctor_guardrail_pair`` flags stale/missing consumer copies:
  the returned report list carries ``[drift]`` / ``[missing]`` / ``[ok]`` for
  ``repos/<slug>:AGENTS.md`` — never ``[skip]`` for a real consumer repo.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import (
    _CANONICAL_AGENTS_BANNER,
    _CLAUDE_MD_STUB,
    _doctor_guardrail_pair,
    _install_workspace_guardrail_pair,
)

# This suite's source is a SYNTHETIC BANNERLESS ``AGENTS.md``. Under the v0.1.60 FR9
# module-constant banner discriminator, a consumer copy projected from a bannerless source
# carries NO provenance banner and therefore classifies ``[foreign]`` (repo-owned) — a
# DELIBERATE Ruling-L amendment, recorded here, never a silent regen. Cases that must keep a
# lib-owned classification ([updated]) re-fixture the consumer content to EMBED
# ``_CANONICAL_AGENTS_BANNER``.
_SOURCE_CONTENT = b"# AGENTS\n\nWorkspace-law guardrail content for fan-out tests.\n"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_registry(workspace_root: Path, entries: list[tuple[str, str]]) -> None:
    """Write ``.dadaia/states/spec_contexts.json`` (schema v2) for *entries*.

    ``entries`` is a list of ``(repo_slug, state)`` tuples where ``state`` is
    ``"alive"`` or ``"dead"``.
    """
    states_dir = workspace_root / ".dadaia" / "states"
    states_dir.mkdir(parents=True, exist_ok=True)
    contexts = []
    for slug, state in entries:
        contexts.append(
            {
                "name": slug,
                "state": state,
                "repo_slug": slug,
                "repo_url": f"https://example.test/{slug}.git",
                "created_at": "2026-07-04T00:00:00Z",
                "alive_since": "2026-07-04T00:00:00Z" if state == "alive" else None,
                "dead_since": None if state == "alive" else "2026-07-04T00:00:00Z",
                "current_branch": "main",
            }
        )
    (states_dir / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": contexts}, indent=2),
        encoding="utf-8",
    )


def _make_source(tmp_path: Path) -> Path:
    """Write the workspace-law source ``AGENTS.md`` and return its path.

    Written under ``_src/`` so it never collides with a workspace-root or
    consumer projection target (avoids ``SameFileError``).
    """
    src = tmp_path / "_src" / "AGENTS.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(_SOURCE_CONTENT)
    return src


def _make_repo(workspace_root: Path, slug: str) -> Path:
    """Create a bare (marker-less) consumer repo dir under ``repos/<slug>/``."""
    repo = workspace_root / "repos" / slug
    repo.mkdir(parents=True, exist_ok=True)
    return repo


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _labels(lines: list[str]) -> set[str]:
    return {ln.split(" ", 1)[1] for ln in lines if " " in ln}


# ---------------------------------------------------------------------------
# AC-6 — fan-out fires for a registry-listed marker-less consumer
# ---------------------------------------------------------------------------


def test_fan_out_fires_for_registry_listed_marker_less_consumer(tmp_path: Path) -> None:
    """A ``demo`` context in the registry + a real ``repos/demo/`` (no in-repo
    ``.dadaia/``) receives the workspace-law ``AGENTS.md`` + the 1-line
    ``CLAUDE.md`` stub. RED-first: the pre-fix (marker-based) detection dropped
    the marker-less repo and wrote nothing.
    """
    source = _make_source(tmp_path)
    _write_registry(tmp_path, [("demo", "alive")])
    repo = _make_repo(tmp_path, "demo")
    assert not (repo / ".dadaia").exists()  # genuinely marker-less

    installed: list[str] = []
    _install_workspace_guardrail_pair(source, tmp_path, force=False, installed=installed)

    assert (repo / "AGENTS.md").exists(), "fan-out must write repos/demo/AGENTS.md"
    assert (repo / "CLAUDE.md").exists(), "fan-out must write repos/demo/CLAUDE.md"
    assert _sha(repo / "AGENTS.md") == _sha(source), "consumer AGENTS.md must be byte-identical"
    assert (repo / "CLAUDE.md").read_text(encoding="utf-8") == _CLAUDE_MD_STUB


def test_dead_context_repo_is_also_fanned(tmp_path: Path) -> None:
    """Ruling H: fan-out reaches a DEAD context's on-disk repo too, not only alive."""
    source = _make_source(tmp_path)
    _write_registry(tmp_path, [("deadctx", "dead")])
    repo = _make_repo(tmp_path, "deadctx")

    _install_workspace_guardrail_pair(source, tmp_path, force=False)

    assert (repo / "AGENTS.md").exists(), (
        "a dead context's on-disk repo must still receive the pair"
    )
    assert _sha(repo / "AGENTS.md") == _sha(source)


def test_registry_context_without_on_disk_repo_skipped_silently(tmp_path: Path) -> None:
    """A registered context whose ``repos/<slug>/`` is absent is skipped without error."""
    source = _make_source(tmp_path)
    _write_registry(tmp_path, [("ghost", "alive"), ("demo", "alive")])
    demo = _make_repo(tmp_path, "demo")  # ghost intentionally NOT created

    # Must not raise even though repos/ghost/ does not exist.
    _install_workspace_guardrail_pair(source, tmp_path, force=False)

    assert (demo / "AGENTS.md").exists(), "the on-disk context (demo) must be written"
    assert not (tmp_path / "repos" / "ghost").exists(), "the absent context is not materialized"


def test_self_repo_is_skipped(tmp_path: Path) -> None:
    """The dadaia-workspace source tree (self) is skipped; other consumers still write."""
    source = _make_source(tmp_path)
    _write_registry(tmp_path, [("dadaia-workspace", "alive"), ("demo", "alive")])
    self_repo = _make_repo(tmp_path, "dadaia-workspace")
    (self_repo / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "dadaia-workspace"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    demo = _make_repo(tmp_path, "demo")

    _install_workspace_guardrail_pair(source, tmp_path, force=False)

    assert not (self_repo / "AGENTS.md").exists(), "self-repo must never be overwritten"
    assert (demo / "AGENTS.md").exists(), "a non-self consumer is still written"


def test_tri_copy_targets_not_written_by_fan_out(tmp_path: Path) -> None:
    """Ruling I: the fan-out writes ONLY workspace-root + consumer-repo roots.

    ``specs/AGENTS.md`` and ``specs/memory/AGENTS.md`` (the v0.1.48 tri-copy)
    are never produced by the guardrail fan-out.
    """
    source = _make_source(tmp_path)
    _write_registry(tmp_path, [("demo", "alive")])
    _make_repo(tmp_path, "demo")
    (tmp_path / "specs" / "memory").mkdir(parents=True)

    _install_workspace_guardrail_pair(source, tmp_path, force=False)

    assert not (tmp_path / "specs" / "AGENTS.md").exists()
    assert not (tmp_path / "specs" / "memory" / "AGENTS.md").exists()


# ---------------------------------------------------------------------------
# A5 / Ruling L — divergent consumer root restored, DISTINCT [updated] line
# ---------------------------------------------------------------------------


def test_divergent_consumer_root_restored_with_updated_line(tmp_path: Path) -> None:
    """A divergent but BANNER-BEARING (lib-owned) consumer root ``AGENTS.md`` is restored to
    canonical AND ``_write_pair`` emits the DISTINCT ``[updated]`` line — never a silent
    ``[ok]``.

    v0.1.60 FR9 amendment: only a *provable canonical projection* (carries
    ``_CANONICAL_AGENTS_BANNER``) is lib-owned and eligible for restore; the divergent copy is
    re-fixtured WITH the banner to keep the ``[updated]`` classification (a bannerless
    divergent copy is now ``[foreign]`` — see the provenance suite).
    """
    source = _make_source(tmp_path)
    _write_registry(tmp_path, [("demo", "alive")])
    repo = _make_repo(tmp_path, "demo")
    (repo / "AGENTS.md").write_bytes(
        _CANONICAL_AGENTS_BANNER.encode() + b"\n# HAND-EDITED divergent (but lib-owned) copy\n"
    )

    installed: list[str] = []
    _install_workspace_guardrail_pair(source, tmp_path, force=False, installed=installed)

    # Restored to canonical.
    assert _sha(repo / "AGENTS.md") == _sha(source), "divergent consumer copy must be restored"

    updated_lines = [
        e
        for e in installed
        if e.startswith("[updated]")
        and str(repo / "AGENTS.md") in e
        and "overwrote divergent workspace-law copy" in e
    ]
    assert updated_lines, (
        "a divergent consumer overwrite must emit a DISTINCT [updated] line, not a silent [ok].\n"
        f"  installed: {installed}"
    )
    # It must NOT be reported as a plain fresh-create [ok].
    assert not any(e.startswith("[ok]") and str(repo / "AGENTS.md") in e for e in installed), (
        "the divergent-overwrite line must not masquerade as a fresh [ok]."
    )


def test_nested_subtree_agents_md_left_untouched(tmp_path: Path) -> None:
    """Ruling L: operator customization in a nested ``repos/<slug>/src/AGENTS.md``
    is NEVER touched by the fan-out — only the repo ROOT pair is lib-owned.
    """
    source = _make_source(tmp_path)
    _write_registry(tmp_path, [("demo", "alive")])
    repo = _make_repo(tmp_path, "demo")
    nested = repo / "src" / "AGENTS.md"
    nested.parent.mkdir(parents=True)
    operator_content = b"# Operator-authored nested AGENTS for repos/demo/src\n"
    nested.write_bytes(operator_content)

    _install_workspace_guardrail_pair(source, tmp_path, force=False)

    assert nested.read_bytes() == operator_content, "nested subtree AGENTS.md must remain untouched"
    # The root pair was still installed.
    assert (repo / "AGENTS.md").exists()


# ---------------------------------------------------------------------------
# AC-7 — doctor flags stale/missing consumer copies (never [skip])
# ---------------------------------------------------------------------------


def test_doctor_flags_foreign_for_bannerless_consumer(tmp_path: Path) -> None:
    """A bannerless (hand-authored / stale-bannerless) ``repos/demo/AGENTS.md`` yields
    ``[foreign] repos/demo:AGENTS.md`` — never ``[skip]``.

    v0.1.60 FR9 amendment ([drift]→[foreign]): under the module-constant banner, a consumer
    AGENTS.md that does NOT carry ``_CANONICAL_AGENTS_BANNER`` is repo-owned, not a drift — so
    ``public doctor`` does not perpetually flag it. (A banner-bearing stale copy is still
    ``[drift]`` — see ``test_consumer_fanout_provenance.py``.)
    """
    source = _make_source(tmp_path)
    _write_registry(tmp_path, [("demo", "alive")])
    repo = _make_repo(tmp_path, "demo")
    (repo / "AGENTS.md").write_bytes(b"# STALE bannerless consumer copy\n")
    (repo / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8", newline="")

    lines = _doctor_guardrail_pair(source, tmp_path)

    assert "[foreign] repos/demo:AGENTS.md" in lines, (
        f"bannerless consumer AGENTS.md must be flagged [foreign] in the report list.\n  lines: {lines}"
    )
    assert not any(ln.startswith("[skip]") for ln in lines), (
        "the doctor report list must never contain a [skip] line for a real consumer repo."
    )


def test_doctor_flags_missing_consumer(tmp_path: Path) -> None:
    """An absent ``repos/demo/AGENTS.md`` yields ``[missing] repos/demo:AGENTS.md``."""
    source = _make_source(tmp_path)
    _write_registry(tmp_path, [("demo", "alive")])
    _make_repo(tmp_path, "demo")  # repo exists; AGENTS.md not written

    lines = _doctor_guardrail_pair(source, tmp_path)

    assert "[missing] repos/demo:AGENTS.md" in lines, (
        f"absent consumer AGENTS.md must be flagged [missing].\n  lines: {lines}"
    )


def test_doctor_reports_foreign_for_fresh_bannerless_consumer(tmp_path: Path) -> None:
    """After a fresh install of a BANNERLESS source the consumer copy reads
    ``[foreign] repos/demo:AGENTS.md``.

    v0.1.60 FR9 amendment ([ok]→[foreign]): the synthetic source carries no banner, so the
    projected consumer copy is not a provable lib-owned projection — it classifies
    ``[foreign]``. In production the shipped ``data/AGENTS.md`` DOES carry the banner, so a
    real fresh consumer reads ``[ok]`` (covered by ``test_consumer_fanout_provenance.py``).
    """
    source = _make_source(tmp_path)
    _write_registry(tmp_path, [("demo", "alive")])
    _make_repo(tmp_path, "demo")

    _install_workspace_guardrail_pair(source, tmp_path, force=True)
    lines = _doctor_guardrail_pair(source, tmp_path)

    labels = _labels(lines)
    assert "repos/demo:AGENTS.md" in labels
    assert "repos/demo:CLAUDE.md" in labels
    assert "[foreign] repos/demo:AGENTS.md" in lines, (
        f"a bannerless fresh consumer copy must read [foreign].\n  lines: {lines}"
    )


def test_doctor_never_skips_a_registered_consumer(tmp_path: Path) -> None:
    """Ruling J: a registered on-disk consumer is always represented by a
    ``[drift]``/``[missing]``/``[ok]`` line — the report list never carries a
    ``[skip]`` for it.
    """
    source = _make_source(tmp_path)
    _write_registry(tmp_path, [("demo", "alive")])
    _make_repo(tmp_path, "demo")

    lines = _doctor_guardrail_pair(source, tmp_path)

    assert any("repos/demo:AGENTS.md" in ln for ln in lines)
    assert not any("[skip]" in ln for ln in lines)
