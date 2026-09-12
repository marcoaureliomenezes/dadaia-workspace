"""Unit tests for ``dadaia_workspace.features.specs.canon.release_new``.

Intent: CONTRACT — release_new coverage, moved verbatim from the retired
``features.spec_artifacts.new_artifacts`` (v0.5.1 K4: the package existed only to
dodge a features -> features cross-feature edge; both this writer and the CANON
table it renders through now live in ``features/specs/``, so the edge never existed
here) plus two hardening rules carried forward from main: per-artifact no-clobber
(SPEC.md/PLAN.md/TASKS.md/RELEASE.json, not directory-existence alone) and symlink
refusal (CWE-59 — never mint through a symlinked release dir).

Covers:
- AC-T7-1: release_new creates SPEC.md with Draft frontmatter
- AC-T7-2: release_new exits non-zero (raises FileExistsError) when dir exists
- AC-T7-5: release_new raises ValueError for invalid slug
- release_new refuses to overwrite an already-minted artifact even when the release
  directory itself was created by something else first (defense in depth)
- release_new refuses to mint through a symlinked release directory

(The legacy ``bug_new`` scaffolder was retired in v0.1.53 — bugs are event-sourced JSONL
via ``dadaia bugs append``. ``backlog_new`` lives in ``features.backlog.document``,
untouched by this task.)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.canon import release_new


def test_existing_spec_raises_file_exists_error(tmp_path: Path) -> None:
    """AC-T7-2: raises FileExistsError when the release's SPEC.md already exists."""
    specs = tmp_path / "specs"
    (specs / "releases" / "my-feature-v1").mkdir(parents=True)
    (specs / "releases" / "my-feature-v1" / "SPEC.md").write_text("x")

    with pytest.raises(FileExistsError, match=r"already exist"):
        release_new(specs, "my-feature-v1")


def test_accepts_bare_semver_release_id(tmp_path: Path) -> None:
    """H1 (bug release-new-rejects-semver-but-doctor-requires-it): the bare SemVer
    canon ``X.Y.Z`` — which `specs doctor` SPEC-DOC-027 REQUIRES for a live release dir
    since canon v6 (T-050-06A/AS-13) — must be accepted (it used to be rejected by the
    slug-only validator, pre-FR3)."""
    specs = tmp_path / "specs"
    specs.mkdir()

    spec_path = release_new(specs, "0.1.23")
    assert spec_path == specs / "releases" / "0.1.23" / "SPEC.md"
    assert spec_path.is_file()


def test_refuses_v_prefixed_release_id_at_mint(tmp_path: Path) -> None:
    """A1.10/AS-13 (T-050-06A): the `v`-prefixed axis is retired-archive-only — minting
    a NEW release id carrying a `v` prefix is refused, even though the same string
    would have been accepted before the canon-v6 axis flip."""
    specs = tmp_path / "specs"
    specs.mkdir()

    with pytest.raises(ValueError, match=r"Invalid release ID"):
        release_new(specs, "v0.1.23")
    assert not (specs / "releases" / "v0.1.23").exists()


# ---------------------------------------------------------------------------
# release_new id validation matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "match"),
    [
        pytest.param("INVALID NAME", r"Invalid release ID", id="release-uppercase"),
        pytest.param("my feature v1", r"Invalid release ID", id="release-spaces"),
        pytest.param("1bad-slug", r"Invalid release ID", id="release-leading-digit"),
        # AS-13/T-050-06A: bare "0.1.23" is now the MINTABLE canon form (see
        # test_accepts_bare_semver_release_id); the v-prefixed retired axis is what's
        # refused at mint now (see test_refuses_v_prefixed_release_id_at_mint).
        pytest.param("v0.1", r"Invalid release ID", id="release-dotted-too-short"),
        pytest.param("v0.1.2.3", r"Invalid release ID", id="release-dotted-4-segments"),
        pytest.param("v1.2.x", r"Invalid release ID", id="release-dotted-non-numeric"),
    ],
)
def test_invalid_release_id_matrix(tmp_path: Path, slug: str, match: str) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    with pytest.raises(ValueError, match=match):
        release_new(specs, slug)


# ---------------------------------------------------------------------------
# release_new creation-content facets (+ other valid-slug shapes) — 1 test
# ---------------------------------------------------------------------------


def test_release_new_creation_content(tmp_path: Path) -> None:
    """AC-T7-1: SPEC.md is created with Draft status, the release id, every required
    frontmatter field, and releases/ is auto-created when absent. Also covers other
    valid-slug shapes (hyphenated, digits-after-first-letter)."""
    specs = tmp_path / "specs"
    specs.mkdir()
    # releases/ deliberately NOT pre-created — auto-creation facet.

    spec_path = release_new(specs, "my-feature-v1")

    assert spec_path == specs / "releases" / "my-feature-v1" / "SPEC.md"
    assert spec_path.is_file(), "SPEC.md must be created (AC-T7-1)"

    content = spec_path.read_text(encoding="utf-8")
    assert "Status:** Draft" in content or "Status: Draft" in content
    assert "my-feature-v1" in content
    for field in ("Status", "Release ID", "Owner", "Opened"):
        assert field in content, f"Missing frontmatter field: {field}"

    # Other valid slug shapes also create successfully — each in its OWN tree: the
    # release-candidates model (0.4.6, ADR 0005) allows exactly one live release.
    for slug in ("hyphenated-release-v1", "release2026"):
        other_specs = tmp_path / f"specs-{slug}"
        other_specs.mkdir()
        other_path = release_new(other_specs, slug)
        assert other_path.is_file()


# ---------------------------------------------------------------------------
# Hardening carried forward: per-artifact no-clobber + symlink refusal
# ---------------------------------------------------------------------------


def test_refuses_when_release_dir_already_holds_a_minted_artifact(tmp_path: Path) -> None:
    """Defense in depth: even a release dir that predates ``release new`` (e.g. a
    RELEASE.json written by another path first) is refused — not just the
    directory-existence check, but each of SPEC.md/PLAN.md/TASKS.md/RELEASE.json
    individually."""
    specs = tmp_path / "specs"
    (specs / "releases" / "0.2.0").mkdir(parents=True)
    (specs / "releases" / "0.2.0" / "RELEASE.json").write_text("{}", encoding="utf-8")

    with pytest.raises(FileExistsError, match=r"already exist"):
        release_new(specs, "0.2.0")


@pytest.mark.skipif(sys.platform.startswith("win"), reason="symlink perms differ on Windows CI")
def test_refuses_to_mint_through_a_symlinked_release_dir(tmp_path: Path) -> None:
    """CWE-59: a symlinked ``releases/<id>`` must never be minted through — that could
    write the release stub outside specs_dir entirely."""
    specs = tmp_path / "specs"
    (specs / "releases").mkdir(parents=True)
    real_target = tmp_path / "outside-specs-dir"
    real_target.mkdir()
    (specs / "releases" / "0.3.0").symlink_to(real_target, target_is_directory=True)

    with pytest.raises(FileExistsError, match=r"symlink"):
        release_new(specs, "0.3.0")
    assert list(real_target.iterdir()) == [], "nothing must be written through the symlink"


def test_release_new_accepts_a_directory_that_holds_only_verdicts(tmp_path: Path) -> None:
    """Bug ``release-new-refuses-a-verdicts-only-lane-directory``: the bug lane commits
    its PR verdict under ``releases/<id>/verdicts/`` before the release opens."""
    specs = tmp_path / "specs"
    (specs / "releases" / "0.9.0" / "verdicts").mkdir(parents=True)
    (specs / "releases" / "0.9.0" / "verdicts" / "abc.handoff.json").write_text("{}")

    path = release_new(specs, "0.9.0")

    assert path == specs / "releases" / "0.9.0" / "SPEC.md"
    assert path.is_file()


# ── 0.4.7 FR2 (T-047-06): release new is the ONE birth act ─────────────────────
#
# Intent: CONTRACT — 0.4.7 FR2 / T-047-06, bugs
# `release-new-writes-spec-only-never-creates-release-state` and
# `minted-feature-branch-without-live-release-blocks-every-memory-write`. The gate's
# MEMORY class, `context show`, `dd-spec-navigator`, V34 and `rc-archive` all resolve
# the live release by the presence of `_RELEASE.json`; writing SPEC.md alone means the
# release does not exist for any of them until a human hand-writes the state document.
# Size: SMALL (tmp_path trees, no subprocess, no network).


def test_release_new_writes_the_release_state_document(tmp_path: Path) -> None:
    """FR2: birth writes SPEC.md AND `_RELEASE.json` — phase DEFINITION, `rc: null`,
    every milestone null, exactly one `note` log entry."""
    from dadaia_workspace.core.release_state import parse_release_state

    specs = tmp_path / "specs"
    specs.mkdir()

    spec_path = release_new(specs, "0.4.9")

    state_path = spec_path.parent / "_RELEASE.json"
    assert state_path.is_file(), "release new must write the release-state document"
    state = parse_release_state(state_path.read_text(encoding="utf-8"))
    assert state.schema == "release-state-v1"
    assert state.release == "0.4.9"
    assert state.phase == "DEFINITION"
    assert state.rc is None
    assert (state.defined, state.implemented, state.shipped) == (None, None, None)
    assert len(state.log) == 1
    entry = state.log[0]
    assert entry["agent"] == "dadaia release new"
    assert entry["kind"] == "note"
    assert entry["text"] == "Release 0.4.9 born"
    assert entry["ts"]


def test_the_born_release_is_resolvable_as_live_in_definition(tmp_path: Path) -> None:
    """FR2 AC: after birth, the live-release resolver the gate's MEMORY class and
    `dadaia context show` key on finds the release, in phase DEFINITION."""
    from dadaia_workspace.features.specs.doctor_common import resolve_live_release_id

    specs = tmp_path / "specs"
    specs.mkdir()
    release_new(specs, "0.4.9")

    release_id, error = resolve_live_release_id(specs)
    assert error is None
    assert release_id == "0.4.9"


def test_release_new_refuses_a_second_live_release_with_an_executable_fix(
    tmp_path: Path,
) -> None:
    """FR2: exactly one live release. The refusal names the live one and carries a
    `fix:` line the operator can execute verbatim."""
    specs = tmp_path / "specs"
    specs.mkdir()
    release_new(specs, "0.4.9")

    with pytest.raises(FileExistsError) as excinfo:
        release_new(specs, "0.5.0")

    message = str(excinfo.value)
    assert "0.4.9" in message
    assert "fix:" in message
    assert "dadaia release rc-archive" in message
    assert "dadaia release archive 0.4.9" in message


def test_a_refused_birth_leaves_no_partial_release_directory(tmp_path: Path) -> None:
    """FR2 all-or-nothing: a refused birth writes nothing — no directory, no SPEC.md,
    no half-written state document."""
    specs = tmp_path / "specs"
    specs.mkdir()
    release_new(specs, "0.4.9")

    with pytest.raises(FileExistsError):
        release_new(specs, "0.5.0")

    assert not (specs / "releases" / "0.5.0").exists()


def test_a_born_release_passes_the_release_tree_validator(tmp_path: Path) -> None:
    """FR2 x FR1: the document birth writes is valid `release-state-v1` by the ONE
    validator (T-047-01) — the trio issue is the only one a just-born release carries."""
    from dadaia_workspace.features.specs.release_tree import validate_release_tree

    specs = tmp_path / "specs"
    specs.mkdir()
    release_new(specs, "0.4.9")

    codes = {issue.code for issue in validate_release_tree(specs)}
    assert "RELEASE-STATE-MISSING" not in codes
    assert "RELEASE-STATE-SCHEMA" not in codes
    assert "RELEASE-STATE-PARSE" not in codes
    assert "RELEASE-PHASE" not in codes
