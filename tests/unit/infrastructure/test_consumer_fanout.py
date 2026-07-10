"""FR4 (v0.1.58) — registry-based consumer ``AGENTS.md`` fan-out.

Detection moved off the dead in-repo ``.dadaia/agentic/`` marker onto the
workspace registry ``.dadaia/states/spec_contexts.json`` (Ruling G/H): the
repo-cleanliness law forbids ``.dadaia/`` inside a repo working tree, so the
old marker made the fan-out empty by construction. These tests assert:

- **AC-6** — the fan-out fires for a registry-listed, *marker-less* on-disk
  consumer repo (alive OR dead — Ruling H); a registry context with no on-disk
  repo is skipped without error; the self-repo is skipped; the tri-copy
  (``specs/AGENTS.md`` / ``specs/memory/AGENTS.md``) is never written (Ruling I).
- Ruling L — a nested subtree ``repos/<slug>/src/AGENTS.md`` is never touched
  by the fan-out (divergent-root restore + [updated] classification is owned by
  ``test_consumer_fanout_provenance.py``).
- Doctor never-skip / drift / missing coverage for a registered consumer is
  owned by ``test_consumer_fanout_provenance.py`` and
  ``test_consumer_fanout_containment.py``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    _CLAUDE_MD_STUB,
    _consumer_repos_for_root,
    _install_workspace_guardrail_pair,
    _is_self_repo,
)

_INSTALLED_VERSION = "1.2.3"
_OTHER_VERSION = "0.0.1"

# This suite's source is a SYNTHETIC BANNERLESS ``AGENTS.md``. Under the v0.1.60 FR9
# module-constant banner discriminator, a consumer copy projected from a bannerless source
# carries NO provenance banner and therefore classifies ``[foreign]`` (repo-owned) — a
# DELIBERATE Ruling-L amendment. Cases that must keep a lib-owned classification
# ([updated]) live in ``test_consumer_fanout_provenance.py``.
_SOURCE_CONTENT = b"# AGENTS\n\nWorkspace-law guardrail content for fan-out tests.\n"


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


@pytest.mark.parametrize(
    "case",
    [
        "dead-context-repo-is-also-fanned",
        "registry-context-without-on-disk-repo-skipped",
        "self-repo-is-skipped",
        "tri-copy-targets-not-written",
        "nested-subtree-agents-md-left-untouched",
    ],
)
def test_fan_out_targeting_matrix(tmp_path: Path, case: str) -> None:
    """Ruling H/I: dead contexts are still fanned; a registered context with no
    on-disk repo is skipped without error; the self-repo (dadaia-workspace) is
    never overwritten; the tri-copy targets are never produced by this fan-out;
    and (Ruling L) a nested subtree AGENTS.md is never touched — only the repo
    ROOT pair is lib-owned."""
    source = _make_source(tmp_path)

    if case == "dead-context-repo-is-also-fanned":
        _write_registry(tmp_path, [("deadctx", "dead")])
        repo = _make_repo(tmp_path, "deadctx")
        _install_workspace_guardrail_pair(source, tmp_path, force=False)
        assert (repo / "AGENTS.md").exists(), (
            "a dead context's on-disk repo must still receive the pair"
        )
        assert _sha(repo / "AGENTS.md") == _sha(source)

    elif case == "registry-context-without-on-disk-repo-skipped":
        _write_registry(tmp_path, [("ghost", "alive"), ("demo", "alive")])
        demo = _make_repo(tmp_path, "demo")  # ghost intentionally NOT created
        # Must not raise even though repos/ghost/ does not exist.
        _install_workspace_guardrail_pair(source, tmp_path, force=False)
        assert (demo / "AGENTS.md").exists(), "the on-disk context (demo) must be written"
        assert not (tmp_path / "repos" / "ghost").exists(), "the absent context is not materialized"

    elif case == "self-repo-is-skipped":
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

    elif case == "tri-copy-targets-not-written":
        _write_registry(tmp_path, [("demo", "alive")])
        _make_repo(tmp_path, "demo")
        (tmp_path / "specs" / "memory").mkdir(parents=True)
        _install_workspace_guardrail_pair(source, tmp_path, force=False)
        assert not (tmp_path / "specs" / "AGENTS.md").exists()
        assert not (tmp_path / "specs" / "memory" / "AGENTS.md").exists()

    else:  # nested-subtree-agents-md-left-untouched
        _write_registry(tmp_path, [("demo", "alive")])
        repo = _make_repo(tmp_path, "demo")
        nested = repo / "src" / "AGENTS.md"
        nested.parent.mkdir(parents=True)
        operator_content = b"# Operator-authored nested AGENTS for repos/demo/src\n"
        nested.write_bytes(operator_content)
        _install_workspace_guardrail_pair(source, tmp_path, force=False)
        assert nested.read_bytes() == operator_content, (
            "nested subtree AGENTS.md must remain untouched"
        )
        # The root pair was still installed.
        assert (repo / "AGENTS.md").exists()


# ---------------------------------------------------------------------------
# Relocated from test_public_assets.py (T-2, v0.1.75): the module-level
# _consumer_repos_for_root / _is_self_repo functions share this file's registry
# fixture family. The former instance-method duplicates
# (manager._consumer_repos / manager._is_self_repo, both thin delegations to
# these same module functions) were DELETED as byte-duplicates.
# ---------------------------------------------------------------------------


def _add_marker_consumer(
    workspace_root: Path, slug: str, pkg_version: str = _OTHER_VERSION
) -> Path:
    """Register a consumer repo under workspace_root/repos/ (v0.1.58 FR4).

    Detection is registry-based (Ruling G): the slug is registered in
    ``spec_contexts.json``. The ``.dadaia/agentic/manifest.json`` is still written
    because ``_is_self_repo`` reads ``package_version`` from it for the self-skip
    check (RETAINED, Ruling G) — it is NO LONGER what drives detection.
    """
    consumer = workspace_root / "repos" / slug
    (consumer / ".dadaia" / "agentic").mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": "1", "package_version": pkg_version}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    _write_registry(workspace_root, [(slug, "alive")])
    return consumer


def test_consumer_repos_for_root_registry_detection(tmp_path: Path) -> None:
    """A registry-registered on-disk repo is returned (v0.1.58 FR4); a bare on-disk
    repo NOT in the registry is invisible — no stderr [skip] line either, for a
    fully bare repo or a repo carrying only a (no-longer-driving) in-repo
    ``.dadaia/`` marker; a plain file inside repos/ is skipped."""
    assert _consumer_repos_for_root(tmp_path) == []

    consumer = _add_marker_consumer(tmp_path, "my-repo")
    assert consumer in _consumer_repos_for_root(tmp_path)

    unregistered = tmp_path / "repos" / "no-markers"
    unregistered.mkdir(parents=True)
    assert unregistered not in _consumer_repos_for_root(tmp_path)

    partial = tmp_path / "repos" / "partial"
    (partial / ".dadaia").mkdir(parents=True)
    assert partial not in _consumer_repos_for_root(tmp_path)

    repos_dir = tmp_path / "repos"
    (repos_dir / "somefile.txt").write_text("x")
    # A file in repos/ contributes nothing (still only the registered consumer).
    assert _consumer_repos_for_root(tmp_path) == [consumer]


def test_is_self_repo_manifest_and_pyproject_precedence(tmp_path: Path) -> None:
    """self-repo identification: manifest package_version match; missing/invalid/
    different-version manifest is NOT self; a poetry OR PEP-621 pyproject.toml
    named dadaia-workspace IS self (with or without a manifest — pyproject wins);
    a differently-named or malformed pyproject falls through to the manifest
    check (never raises)."""
    with patch(
        "dadaia_workspace.infrastructure.workspace_guardrail._package_version",
        return_value=_INSTALLED_VERSION,
    ):
        matching = _add_marker_consumer(tmp_path, "self", pkg_version=_INSTALLED_VERSION)
        assert _is_self_repo(matching) is True

        different = _add_marker_consumer(tmp_path, "other", pkg_version=_OTHER_VERSION)
        assert _is_self_repo(different) is False

    no_manifest = tmp_path / "repos" / "no-manifest"
    (no_manifest / ".dadaia" / "agentic").mkdir(parents=True)
    assert _is_self_repo(no_manifest) is False

    invalid_json = tmp_path / "repos" / "bad-json"
    (invalid_json / ".dadaia" / "agentic").mkdir(parents=True)
    (invalid_json / ".dadaia" / "agentic" / "manifest.json").write_text(
        "NOT JSON", encoding="utf-8"
    )
    assert _is_self_repo(invalid_json) is False

    empty_version = tmp_path / "repos" / "empty-ver"
    (empty_version / ".dadaia" / "agentic").mkdir(parents=True)
    (empty_version / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps({"package_version": ""}), encoding="utf-8"
    )
    assert _is_self_repo(empty_version) is False

    for slug, pyproject in {
        "poetry": '[tool.poetry]\nname = "dadaia-workspace"\nversion = "0.0.0"\n',
        "pep621": '[project]\nname = "dadaia-workspace"\nversion = "0.0.0"\n',
    }.items():
        pyproject_consumer = tmp_path / "repos" / slug
        pyproject_consumer.mkdir(parents=True)
        (pyproject_consumer / "pyproject.toml").write_text(pyproject, encoding="utf-8")
        assert _is_self_repo(pyproject_consumer) is True

    other_lib = tmp_path / "repos" / "other-lib"
    other_lib.mkdir(parents=True)
    (other_lib / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "some-other-lib"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    assert _is_self_repo(other_lib) is False

    broken_pyproject = tmp_path / "repos" / "broken-pyproject"
    broken_pyproject.mkdir(parents=True)
    (broken_pyproject / "pyproject.toml").write_text("NOT VALID TOML ][[\n", encoding="utf-8")
    assert _is_self_repo(broken_pyproject) is False  # falls through, never raises

    # pyproject guard fires before the manifest check; result is still True even
    # with a non-matching manifest version present.
    lib_with_manifest = tmp_path / "repos" / "lib-with-manifest"
    lib_with_manifest.mkdir(parents=True)
    (lib_with_manifest / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "dadaia-workspace"\nversion = "0.0.0"\n', encoding="utf-8"
    )
    (lib_with_manifest / ".dadaia" / "agentic").mkdir(parents=True)
    (lib_with_manifest / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps({"package_version": "999.0.0"}), encoding="utf-8"
    )
    assert _is_self_repo(lib_with_manifest) is True
