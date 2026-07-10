"""FR5/FR6 (v0.1.62, T-62-40) — fan-out slug containment + symlink write-through refusal.

AC-7: a hostile ``repo_slug`` in ``spec_contexts.json`` (path traversal, separators,
absolute POSIX/Windows forms, dot components) is REJECTED at derivation
(``_consumer_repos_for_root``) with a non-silent ``[reject]`` stderr line, and the
write-site (``_install_guardrail_pair``) carries an independent belt-and-braces
containment assert (ADR-6). RED-first capture: pre-fix, the ``"../evil"`` slug landed
the AGENTS.md/CLAUDE.md pair OUTSIDE ``repos/``.

AC-8: a destination-FILE symlink (including dangling) is never written through
(ADR-7); the pair follows the FR9 sibling-fate ladder; the doctor classifies
symlinked pair files ``[foreign]`` (exit 0). Symlinked consumer DIRECTORIES stay
fully legitimate (the CI ``ln -sfn`` pattern). RED-first capture: pre-fix,
``shutil.copy2`` clobbered the out-of-repo target through the link.

Symlink tests degrade (skip) when the platform cannot create symlinks — the TEST
degrades, never the guard.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    _CANONICAL_AGENTS_BANNER,
    _CLAUDE_MD_STUB,
    _consumer_repos_for_root,
    _doctor_consumer_pair_lines,
    _install_workspace_guardrail_pair,
)

_SOURCE = _CANONICAL_AGENTS_BANNER + "\n# dadaia-workspace — Root Rules\n\nBody.\n"

_HOSTILE_SLUGS = [
    "../evil",
    "a/b",
    "/abs/evil",
    "C:\\evil",
    "C:evil",
    "..",
    ".",
    "..\\evil",
    "\\\\host\\share",
]


def _write_registry(workspace_root: Path, slugs: list[str]) -> None:
    states = workspace_root / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": f"ctx-{i}",
                        "state": "alive",
                        "repo_slug": slug,
                        "repo_url": "https://example.test/x.git",
                        "created_at": "2026-07-07T00:00:00Z",
                        "alive_since": "2026-07-07T00:00:00Z",
                        "dead_since": None,
                        "current_branch": "main",
                    }
                    for i, slug in enumerate(slugs)
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _source(tmp_path: Path) -> Path:
    src = tmp_path / "_src" / "AGENTS.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(_SOURCE, encoding="utf-8")
    return src


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / "repos").mkdir(parents=True, exist_ok=True)
    return ws


def _require_symlinks(tmp_path: Path) -> None:
    """POSIX-degrade marker: skip the TEST when symlinks cannot be created."""
    probe = tmp_path / "_symlink_probe"
    try:
        probe.symlink_to(tmp_path / "_symlink_probe_target")
    except (OSError, NotImplementedError):  # pragma: no cover - Windows CI without priv
        pytest.skip("platform cannot create symlinks — degrading the test, not the guard")
    probe.unlink()


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# AC-7 — hostile-slug matrix (derivation-level lexical validation)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", _HOSTILE_SLUGS)
def test_hostile_slug_rejected_at_derivation(
    tmp_path: Path, slug: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each hostile slug is skipped with a non-silent [reject] stderr line. A valid
    slug alongside them still survives (folded in as the second assert block)."""
    ws = _make_workspace(tmp_path)
    _write_registry(ws, [slug])
    # Plant a directory where the naive join would resolve, so only the lexical
    # validation (not .is_dir()) can be responsible for the rejection.
    naive = ws / "repos" / slug
    with contextlib.suppress(OSError):
        # An unplantable form (e.g. absolute Windows path on POSIX) is fine.
        naive.mkdir(parents=True, exist_ok=True)
    assert _consumer_repos_for_root(ws) == []
    err = capsys.readouterr().err
    assert "[reject]" in err
    assert "unsafe path component" in err

    if slug == _HOSTILE_SLUGS[0]:
        # A valid slug alongside hostile ones still survives (piggy-backed on the
        # first param to avoid a separate fixture setup).
        ws2 = _make_workspace(tmp_path / "valid-alongside")
        good = ws2 / "repos" / "game"
        good.mkdir(parents=True)
        _write_registry(ws2, ["../evil", "a/b", "game"])
        assert _consumer_repos_for_root(ws2) == [good]
        err2 = capsys.readouterr().err
        assert err2.count("[reject]") == 2
        assert "'../evil'" in err2
        assert "'a/b'" in err2


def test_traversal_slug_writes_nothing_outside_repos_and_write_site_containment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-7 end-to-end (RED-first): pre-fix, '../evil' landed the pair OUTSIDE
    repos/. ADR-6 belt-and-braces: even if derivation returned a hostile path
    directly (bypassing the derivation-level reject), the write-site containment
    assert skips it too (never writes, never raises) — two independent layers."""
    ws = _make_workspace(tmp_path)
    evil_dir = ws / "evil"  # where repos/../evil lexically lands
    evil_dir.mkdir(parents=True)
    _write_registry(ws, ["../evil"])
    src = _source(tmp_path)
    installed: list[str] = []
    _install_workspace_guardrail_pair(src, ws, force=True, installed=installed)
    assert not (evil_dir / "AGENTS.md").exists()
    assert not (evil_dir / "CLAUDE.md").exists()
    assert "[reject]" in capsys.readouterr().err
    # Workspace-root pair is unaffected (fail-open overall).
    assert (ws / "AGENTS.md").exists()

    from dadaia_workspace.infrastructure import workspace_guardrail as wg

    ws2 = _make_workspace(tmp_path / "ws2")
    evil_dir2 = ws2 / "evil"
    evil_dir2.mkdir(parents=True)
    hostile = ws2 / "repos" / "../evil"
    monkeypatch.setattr(wg, "_consumer_repos_for_root", lambda _root: [hostile])
    src2 = _source(tmp_path / "ws2")
    installed2: list[str] = []
    wg._install_guardrail_pair(src2, ws2, force=True, installed=installed2, targets={"repos"})
    assert not (evil_dir2 / "AGENTS.md").exists()
    assert "[reject]" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# AC-8 — symlink write-through refusal (files) / symlinked consumer dirs stay ok
# ---------------------------------------------------------------------------


def _consumer(ws: Path, slug: str = "game") -> Path:
    repo = ws / "repos" / slug
    repo.mkdir(parents=True, exist_ok=True)
    _write_registry(ws, [slug])
    return repo


@pytest.mark.parametrize(
    "case",
    [
        "symlinked-agents-target-survives-byte-identical",
        "symlinked-banner-bearing-target-survives",
        "dangling-symlink-refused-never-created-through",
        "symlinked-claude-md-refused",
    ],
)
def test_symlink_write_through_refusal(tmp_path: Path, case: str) -> None:
    """AC-8(a)/(b): a destination-FILE symlink (real target, banner-bearing target,
    dangling target, or the CLAUDE.md sibling) is NEVER written through — the pair
    follows the FR9 sibling-fate ladder and the target bytes are untouched."""
    _require_symlinks(tmp_path)
    ws = _make_workspace(tmp_path)
    repo = _consumer(ws)

    if case == "symlinked-agents-target-survives-byte-identical":
        target = tmp_path / "outside" / "precious.md"
        target.parent.mkdir(parents=True)
        target.write_text("# precious out-of-repo file\n", encoding="utf-8")
        before = _sha(target)
        (repo / "AGENTS.md").symlink_to(target)
        installed: list[str] = []
        _install_workspace_guardrail_pair(_source(tmp_path), ws, force=True, installed=installed)
        assert _sha(target) == before
        assert (repo / "AGENTS.md").is_symlink()
        assert any("[foreign]" in ln and "(symlink)" in ln for ln in installed)
        assert not (repo / "CLAUDE.md").exists()

    elif case == "symlinked-banner-bearing-target-survives":
        target = tmp_path / "outside2" / "stale.md"
        target.parent.mkdir(parents=True)
        target.write_text(_CANONICAL_AGENTS_BANNER + "\nSTALE BODY\n", encoding="utf-8")
        before = _sha(target)
        (repo / "AGENTS.md").symlink_to(target)
        installed = []
        _install_workspace_guardrail_pair(_source(tmp_path), ws, force=True, installed=installed)
        assert _sha(target) == before
        assert any("[foreign]" in ln and "(symlink)" in ln for ln in installed)

    elif case == "dangling-symlink-refused-never-created-through":
        missing_target = tmp_path / "nowhere" / "gone.md"
        (repo / "AGENTS.md").symlink_to(missing_target)
        installed = []
        _install_workspace_guardrail_pair(_source(tmp_path), ws, force=True, installed=installed)
        assert not missing_target.exists()
        assert (repo / "AGENTS.md").is_symlink()
        assert any("[foreign]" in ln and "(symlink)" in ln for ln in installed)
        assert not (repo / "CLAUDE.md").exists()

    else:  # symlinked-claude-md-refused
        target = tmp_path / "outside3" / "claude-target.md"
        target.parent.mkdir(parents=True)
        target.write_text("not the stub\n", encoding="utf-8")
        before = _sha(target)
        (repo / "CLAUDE.md").symlink_to(target)
        installed = []
        _install_workspace_guardrail_pair(_source(tmp_path), ws, force=True, installed=installed)
        assert _sha(target) == before
        assert (repo / "CLAUDE.md").is_symlink()
        assert any(
            "[foreign]" in ln and "(symlink)" in ln and "CLAUDE.md" in ln for ln in installed
        )


@pytest.mark.parametrize(
    "case",
    [
        "doctor-classifies-symlinked-pair-foreign",
        "symlinked-consumer-dir-stays-ok",
        "regular-file-provenance-ladder-unchanged",
    ],
)
def test_symlink_classification_and_regular_ladder(tmp_path: Path, case: str) -> None:
    """AC-8(c)/(d): doctor classifies symlinked pair FILES [foreign] (never
    ok/drift/missing); a symlinked consumer DIRECTORY (the CI ln -sfn pattern) stays
    fully [ok]; and the FR9 regular-file provenance ladder is unchanged (no false
    (symlink) suffix on a hand-authored file)."""
    if case == "doctor-classifies-symlinked-pair-foreign":
        _require_symlinks(tmp_path)
        ws = _make_workspace(tmp_path)
        repo = _consumer(ws)
        target = tmp_path / "t.md"
        target.write_text(_SOURCE, encoding="utf-8")  # byte-identical to source through link
        (repo / "AGENTS.md").symlink_to(target)
        (repo / "CLAUDE.md").symlink_to(tmp_path / "dangling.md")
        lines = _doctor_consumer_pair_lines(_source(tmp_path), ws, emit_stderr=False)
        assert lines == [
            "[foreign] repos/game:AGENTS.md",
            "[foreign] repos/game:CLAUDE.md",
        ]

    elif case == "symlinked-consumer-dir-stays-ok":
        _require_symlinks(tmp_path)
        ws = _make_workspace(tmp_path)
        real = tmp_path / "real_game"
        real.mkdir()
        src = _source(tmp_path)
        (real / "AGENTS.md").write_text(_SOURCE, encoding="utf-8")
        (real / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8")
        (ws / "repos" / "game").symlink_to(real, target_is_directory=True)
        _write_registry(ws, ["game"])
        assert _consumer_repos_for_root(ws) == [ws / "repos" / "game"]
        lines = _doctor_consumer_pair_lines(src, ws, emit_stderr=False)
        assert lines == [
            "[ok] repos/game:AGENTS.md",
            "[ok] repos/game:CLAUDE.md",
        ]
        installed: list[str] = []
        _install_workspace_guardrail_pair(src, ws, force=True, installed=installed)
        assert any("[ok]" in ln and "AGENTS.md" in ln and "game" in ln for ln in installed)
        assert (real / "AGENTS.md").read_text(encoding="utf-8") == _SOURCE

    else:  # regular-file-provenance-ladder-unchanged
        ws = _make_workspace(tmp_path)
        repo = _consumer(ws)
        (repo / "AGENTS.md").write_text("# hand-authored\n", encoding="utf-8")
        installed = []
        _install_workspace_guardrail_pair(_source(tmp_path), ws, force=True, installed=installed)
        foreign = [ln for ln in installed if "[foreign]" in ln and "AGENTS.md" in ln]
        assert foreign and all("(symlink)" not in ln for ln in foreign)
