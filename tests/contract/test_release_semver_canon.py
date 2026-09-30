"""Intent: CONTRACT — sa-release-id-has-three-grammars: a release id has ONE grammar, the
script's bare M.m.p (`_release_schema.SEMVER_RE`); core consults it; archived dirs are
exempt by location. Plus the release-please canon. Size: SMALL.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.release_state import RELEASE_ID_RE
from dadaia_workspace.features.specs.canon import is_canon_path

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO_ROOT / "dadaia_workspace/public/skills/dd-release-implementation/scripts"
sys.path.insert(0, str(_SCRIPTS))
import _release_schema  # noqa: E402


@pytest.mark.parametrize(
    ("release_id", "legal"),
    [
        ("0.5.0", True),
        ("10.20.30", True),
        ("0.5.0-rc1", False),
        ("v0.5.0", False),
        ("1.2", False),
        ("1.2.3-", False),
        ("next", False),
    ],  # fmt: skip
)
def test_one_release_id_grammar_everywhere(tmp_path: Path, release_id: str, legal: bool) -> None:
    """sa-release-id-has-three-grammars and sa-release-json-validated-three-times#B5: core,
    the canon and `release.py new` agree on every id — a suffix and a `v` are refused."""
    assert RELEASE_ID_RE.pattern == _release_schema.SEMVER_RE.pattern
    assert bool(RELEASE_ID_RE.match(release_id)) is legal
    assert is_canon_path(f"releases/{release_id}/SPEC.md") is legal
    (tmp_path / "specs" / "releases").mkdir(parents=True)
    new = subprocess.run([sys.executable, str(_SCRIPTS / "release.py"), "new", release_id,
                          "--specs", str(tmp_path / "specs")], capture_output=True, text=True)  # fmt: skip
    assert (new.returncode == 0) is legal, new.stderr


# ---------------------------------------------------------------------------
# release-please canon — the manifest floor and the pre-1.0 bump flags
# ---------------------------------------------------------------------------

_MANIFEST_PATH = _REPO_ROOT / ".release-please-manifest.json"
_CONFIG_PATH = _REPO_ROOT / "release-please-config.json"


def _published_tags() -> list[str]:
    """Every ``v*`` tag reachable in this checkout, newest last (version order).

    CI checks this repository out shallow and without tags, so an empty list is a
    legitimate environment, not a failure — the caller skips on it.
    """
    import subprocess

    result = subprocess.run(
        ["git", "tag", "-l", "v*", "--sort=version:refname"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_release_please_manifest_sits_at_the_last_published_version() -> None:
    """The manifest is release-please's floor: it must name the last PUBLISHED
    version, so the first release PR proposes the next one rather than re-minting a
    version that already carries a tag."""
    import json

    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert set(manifest) == {"."}, f"the manifest addresses one package, the root: {manifest}"
    version = manifest["."]
    assert isinstance(version, str) and RELEASE_ID_RE.match(version), (
        f"the manifest version must be a bare SemVer (no `v` prefix): {version!r}"
    )

    import tomllib

    minted = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"][
        "poetry"
    ]["version"]
    assert minted == version, (
        f"pyproject.toml mints {minted!r} but the release-please manifest floor is "
        f"{version!r} — release-please reads the manifest and expects pyproject to "
        "agree; the two move together, in one bot-authored commit (D10, T-047-90)"
    )

    tags = _published_tags()
    if not tags:
        pytest.skip("no v* tags in this checkout (shallow CI clone) — floor unverifiable here")
    assert f"v{version}" == tags[-1], (
        f"the manifest floor must equal the latest published tag {tags[-1]!r}, got v{version}"
    )


def test_release_please_config_mints_a_patch_below_one_point_zero() -> None:
    """Pre-1.0, release-please bumps the MINOR on a `feat` unless both flags are set.
    The project mints patch releases from `feat` commits, so both must be true."""
    import json

    config = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    assert config.get("bump-minor-pre-major") is True
    assert config.get("bump-patch-for-minor-pre-major") is True
    assert config.get("include-component-in-tag") is False, (
        "tags are bare `v<version>` — a component prefix would break every tag consumer"
    )

    root_package = config["packages"]["."]
    assert root_package["release-type"] == "python", (
        "the release type lives in the config's root package, never as an action input "
        f"(a `release-type:` input switches the action out of manifest mode): {root_package}"
    )
    assert root_package["changelog-path"] == "CHANGELOG.md"

    sections = {entry["type"]: entry for entry in config["changelog-sections"]}
    assert {"feat", "fix", "refactor", "docs", "ci", "test", "chore"} <= set(sections)
    for commit_type, entry in sections.items():
        assert entry["section"], f"section {commit_type} must carry a heading"
        assert isinstance(entry["hidden"], bool)
