"""The standalone skills repository is rendered, never hand-written.

Intent: CONTRACT — AC2.1 (SPEC 0.4.7 FR2): `build-skills-repo.py <out>` renders exactly
the Agent Skills layout plus the two Claude plugin manifests, every `skills/<name>/**`
file is byte-identical to its `dadaia_workspace/public/skills/` source, the README's
`derived-from` markers carry the CURRENT hash of the atoms it derives from, and a
second build is byte-identical to the first.
Size: SMALL — one subprocess per build into `tmp_path`, no network, no venv.

The output is never tracked here and never read back: the out-dir on argv is the whole
seam, so this test is the only consumer of the renderer's shape.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC = _REPO_ROOT / "dadaia_workspace" / "public"
_SCRIPT = _PUBLIC / "scripts" / "build-skills-repo.py"
_SKILLS_SRC = _PUBLIC / "skills"
_MEMORY = _REPO_ROOT / "specs" / "memory"
_MARKER_RE = re.compile(r"^<!-- derived-from: ([A-Za-z0-9._-]+) sha256:([0-9a-f]{12}) -->$", re.M)
_DERIVED_ATOMS = {
    "public-asset-distribution": _MEMORY
    / "product"
    / "distribution"
    / "public-asset-distribution.md",
    "agentic-entities": _MEMORY / "product" / "agents" / "agentic-entities.md",
}


def _standalone_skills() -> list[str]:
    data = json.loads((_PUBLIC / "entities" / "behavior-map.json").read_text(encoding="utf-8"))
    names: list[str] = data["standalone_skills"]
    return names


def _build(out: Path) -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(_SCRIPT), str(out)], capture_output=True, text=True
    )
    assert result.returncode == 0, f"build failed ({result.returncode}): {result.stderr}"


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("skills-repo") / "dadaia-skills"
    _build(out)
    return out


def test_build_renders_exactly_the_documented_manifest_set(built: Path) -> None:
    """The output tree is the skill corpus plus README, LICENSE and the two manifests —
    nothing else, and no skill left behind."""
    names = _standalone_skills()
    assert names, "the standalone skill roster must not be empty"
    expected = {
        "README.md",
        "LICENSE",
        ".claude-plugin/marketplace.json",
        ".claude-plugin/plugin.json",
    }
    for name in names:
        for source in sorted(p for p in (_SKILLS_SRC / name).rglob("*") if p.is_file()):
            expected.add(f"skills/{name}/{source.relative_to(_SKILLS_SRC / name).as_posix()}")
    assert set(_tree(built)) == expected


def test_every_rendered_skill_file_is_byte_identical_to_its_source(built: Path) -> None:
    """`public/skills/` is the only place a skill's bytes exist; the build copies."""
    rendered = _tree(built)
    compared = 0
    for name in _standalone_skills():
        for source in sorted(p for p in (_SKILLS_SRC / name).rglob("*") if p.is_file()):
            rel = f"skills/{name}/{source.relative_to(_SKILLS_SRC / name).as_posix()}"
            assert rendered[rel] == source.read_bytes(), f"{rel} drifted from its source"
            compared += 1
    assert compared >= len(_standalone_skills()), "every skill contributes at least SKILL.md"


def test_manifests_carry_the_documented_field_set(built: Path) -> None:
    """Both Claude plugin manifests carry exactly the fields the marketplace format
    requires, with the repository's own version."""
    version = re.search(
        r'^version = "([^"]+)"', (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M
    )
    assert version is not None
    market = json.loads((built / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert market["name"] == "dadaia-skills"
    assert market["owner"] == {"name": "marcoaureliomenezes"}
    assert market["description"].strip()
    assert len(market["plugins"]) == 1
    plugin = market["plugins"][0]
    assert plugin["name"] == "dadaia-skills"
    assert plugin["source"] == "./"
    assert plugin["skills"] == ["./skills/"]
    assert plugin["version"] == version.group(1)
    assert plugin["license"] == "MIT"
    assert plugin["repository"] == "https://github.com/marcoaureliomenezes/dadaia-skills"
    assert plugin["description"].strip()

    manifest = json.loads((built / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert set(manifest) == {"name", "description", "version", "author"}
    assert manifest["name"] == "dadaia-skills"
    assert manifest["version"] == version.group(1)
    assert manifest["author"] == {"name": "Marco Menezes"}
    assert manifest["description"].strip()


def test_readme_derives_from_the_atoms_under_their_current_hashes(built: Path) -> None:
    """A changed atom byte reddens the README the build renders — the marker contract,
    applied to a derived output instead of a tracked page."""
    readme = (built / "README.md").read_text(encoding="utf-8")
    markers = dict(_MARKER_RE.findall(readme))
    assert set(markers) == set(_DERIVED_ATOMS)
    for slug, atom in _DERIVED_ATOMS.items():
        digest = hashlib.sha256(atom.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]
        assert markers[slug] == digest, f"marker for {slug} is stale — re-read {atom}"
    for line in (
        "npx skills add marcoaureliomenezes/dadaia-skills",
        "/plugin marketplace add marcoaureliomenezes/dadaia-skills",
        "/plugin install dadaia-skills@dadaia-skills",
        "git clone https://github.com/marcoaureliomenezes/dadaia-skills.git",
    ):
        assert line in readme, f"README is missing the install line: {line}"
    for name in _standalone_skills():
        assert name in readme, f"README omits {name} from the skill table"


def test_license_is_copied_from_the_repository_root(built: Path) -> None:
    assert (built / "LICENSE").read_bytes() == (_REPO_ROOT / "LICENSE").read_bytes()


def test_a_second_build_is_byte_identical(tmp_path: Path) -> None:
    """Idempotent by construction: the renderer owns the whole output, so re-running it
    over a dirty tree converges instead of accreting."""
    out = tmp_path / "dadaia-skills"
    _build(out)
    first = _tree(out)
    (out / "skills" / "STALE.md").write_text("left over from an older roster\n", encoding="utf-8")
    _build(out)
    assert _tree(out) == first


@pytest.mark.skipif(shutil.which("claude") is None, reason="the claude binary is not on PATH")
def test_claude_plugin_validate_accepts_the_output(built: Path) -> None:
    """The one external authority on the marketplace format, asserted when present."""
    result = subprocess.run(  # noqa: S603
        [shutil.which("claude") or "claude", "plugin", "validate", str(built)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"claude plugin validate rejected the output: {result.stdout}{result.stderr}"
    )
