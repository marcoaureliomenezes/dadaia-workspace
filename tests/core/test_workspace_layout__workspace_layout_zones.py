"""Expected values are literals, never read from the module under test: the 12 rows in order, the three TTL zones
(handoff and tmp a day, reaped seven days), the three closed canons, the creators per zone, and the pure exception-glob parser.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from dadaia_workspace.core import workspace_layout as wl
from tests.helpers.oslib import write_text

C, K = wl.Creator, wl.ZoneClass
#: (name, class, creator, ttl seconds), in registry order.
_SPEC_ZONES = [
    ("agentic", K.PROJECTION, C.INSTALL, None),
    ("hooks", K.PROJECTION, C.INSTALL, None),
    ("states", K.STATE, C.INIT, None),
    ("sessions", K.PROTECTED, C.RUNTIME, None),
    ("handoff", K.OUTPUT, C.RUNTIME, 86_400),
    ("reports", K.OUTPUT, C.RUNTIME, None),
    ("tmp", K.EPHEMERAL, C.RUNTIME, 86_400),
    ("reaped", K.EPHEMERAL, C.RUNTIME, 604_800),
    ("dist", K.STATE, C.RUNTIME, None),
    ("mcps", K.OPERATOR, C.OPERATOR, None),
    ("references", K.OPERATOR, C.OPERATOR, None),
    (".venv", K.MANAGED, C.INIT, None),
]
_SPEC_STATES_CANON = {
    "spec_contexts.json",
    "server_registry.json",
    "install_ledger.json",
    "agent_model_policy.json",
    "agent_model_policy.json.last-good.json",
    "privacy_denylist.json",
    "harness_profile.json",
    "AGENTS.md",
}


def test_registry_holds_the_twelve_spec_zones_in_order() -> None:
    """There is no .cache zone; ``reaped/`` is its own row held 7 days, never a TTL override inside ``tmp``."""
    rows = [(z.name, z.cls, z.creator, z.ttl_seconds) for z in wl.DADAIA_ZONES]
    assert rows == _SPEC_ZONES
    assert wl.zone_names() == frozenset(name for name, *_ in _SPEC_ZONES)
    with pytest.raises(dataclasses.FrozenInstanceError):
        wl.DADAIA_ZONES[0].ttl_seconds = 1  # type: ignore[misc]


def test_derived_views_follow_the_registry() -> None:
    """TTL, canon, walked, additive and table views are projections of the one registry."""
    assert [z.name for z in wl.zones_with_ttl()] == ["handoff", "tmp", "reaped"]
    assert {z.name: z.canon for z in wl.zones_with_canon()} == {
        "states": frozenset(_SPEC_STATES_CANON),
        "sessions": frozenset({"*.json"}),
        "dist": frozenset({"spec-contexts.json", "workspace-export.tar.gz"}),
    }
    assert [z.name for z in wl.walked_zones()] == [name for name, *_ in _SPEC_ZONES[:9]]
    assert wl.additive_prefixes() == (
        ".dadaia/handoff/",
        ".dadaia/reports/",
        ".dadaia/tmp/",
        ".dadaia/reaped/",
    )
    rows = {row[0]: row for row in wl.zone_table_rows()}
    assert rows["tmp"][2:] == ("ephemeral", "86400", "runtime")
    assert rows["references"][2:] == ("operator", "never", "operator")
    assert frozenset({"AGENTS.md", ".gitignore"}) == wl.DADAIA_ROOT_FILES
    assert wl.DADAIAIGNORE in wl.ROOT_ALLOWED_FILES and "worktrees" in wl.ROOT_ALLOWED_DIRS
    # the floor is what init/install create, plus the CLI's PROTECTED zone, or the operator's
    # own file inside one of those
    zones = [z for z in wl.DADAIA_ZONES if z in wl.provisioned_zones() or z.cls is K.PROTECTED]
    made = {"AGENTS.md", *wl.LEVEL1_SEEDS, *(f".dadaia/{z.name}" for z in zones)}
    canon = {f".dadaia/{z.name}/{n}" for z in zones for n in z.canon or ()}
    assert set(wl.CORE_FLOOR) <= made | canon


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("", (), id="empty"),
        pytest.param("# only a comment\n\n   \n", (), id="comments-and-blanks"),
        pytest.param("  *.iml \n.idea\n", ("*.iml", ".idea"), id="stripped-in-order"),
        pytest.param(
            ".idea\n# note\n.idea\n*.iml\n.idea", (".idea", "*.iml"), id="dedupe-keeps-first"
        ),
        pytest.param(
            # A directory glob written gitignore-style names the directory: ``fnmatch``
            # never matches a trailing slash, so the parser drops it (and dedupes across).
            "z_img/\n.playwright-mcp/\nz_img\n",
            ("z_img", ".playwright-mcp"),
            id="directory-slash-dropped",
        ),
    ],
)
def test_parse_dadaiaignore(text: str, expected: tuple[str, ...]) -> None:
    """``.dadaiaignore`` parses to stripped, deduped, slash-free root-relative patterns."""
    assert wl.parse_dadaiaignore(text) == (expected, (), ())


def test_dadaiaignore_invalid_lines_and_segment_scope(tmp_path: Path) -> None:
    """``!``, ``**``, an absolute path or ``..`` is invalid, never a pattern; ``*``
    stays inside one segment, so a root pattern admits nothing below the root."""
    text = "!keep\nnotes/**\n/abs\na/../b\n*.png\n[protected]\nsecrets/\n**/k\n"
    invalid = ("!keep", "notes/**", "/abs", "a/../b", "**/k")
    assert wl.parse_dadaiaignore(text) == (("*.png",), ("secrets",), invalid)
    tree = tmp_path / "worktrees" / "r" / "x" / "y"
    (tree / "src").mkdir(parents=True)
    write_text(tree / ".git", "gitdir: ../main/.git/worktrees/j1\n")

    def pg(rel: str, *globs: str) -> str | None:
        return wl.protected_glob(tmp_path, rel, globs or ("secrets",))

    assert pg("repos/r/secrets/k") == "secrets"
    assert pg("repos/r/a/secrets") is None
    assert pg("worktrees/r/x/y/secrets/k") == "secrets"
    assert pg("worktrees/r/x/y/src/secrets/k") is None  # anchored at the tree root, as under repos/
    assert pg("worktrees/r/x/y/specs/AGENTS.md", "AGENTS.md") is None
    assert pg("worktrees/r/x/y/AGENTS.md", "AGENTS.md") == "AGENTS.md"
    assert pg("worktrees/r/x/y/src/k", "*.md") is None
    assert pg("worktrees/r/x/y/docs/k", "docs") == "docs"
    assert pg("worktrees/r/x/y/src/docs/k", "docs") is None
    assert pg("worktrees/r/stray/z/secrets/k") == "secrets"  # no .git above: fail closed, any depth
    assert pg("worktrees/r/x/y/z/src/k") is None
    assert wl.verdict("shot.png", False, ("*.png",), (), ()) == "operator"
    assert wl.verdict(".dadaia/shot.png", False, ("*.png",), (), ()) == "slop"
    assert wl.verdict(".dadaia/shot.png", False, (".dadaia/*.png",), (), ()) == "operator"


def test_a_planted_git_entry_never_unanchors_a_multi_segment_glob(tmp_path: Path) -> None:
    """A ``.git`` written below the real tree root adds an anchor and never removes the root."""
    tree = tmp_path / "worktrees" / "r" / "0.5.0-rc1" / "j1"
    (tree / "docs" / "data-master").mkdir(parents=True)
    write_text(tree / ".git", "gitdir: ../main/.git/worktrees/j1\n")
    rel, globs = "worktrees/r/0.5.0-rc1/j1/docs/data-master/x.md", ("docs/data-master",)
    assert wl.protected_glob(tmp_path, rel, globs) == "docs/data-master"
    write_text(tree / "docs" / ".git", "")
    assert wl.protected_glob(tmp_path, rel, globs) == "docs/data-master"


@pytest.mark.parametrize(
    ("rel", "is_dir", "expected"),
    [
        (".dadaia/dist/spec-contexts.json", False, "canon"),
        (".dadaia/dist/workspace-export.tar.gz", False, "canon"),
        (".dadaia/dist/myrepo", True, "canon"),
        (".dadaia/dist/myrepo/r.bundle", False, "canon"),
        (".dadaia/dist/stray", True, "slop"),
        (".dadaia/dist/stray.bundle", False, "slop"),
    ],
)
def test_dist_admits_the_export_artifacts_and_registered_slug_folders(
    rel: str, is_dir: bool, expected: str
) -> None:
    assert wl.verdict(rel, is_dir, (), ("myrepo",), ()) == expected


def test_the_doctor_fix_never_moves_a_registered_repos_bundle() -> None:
    """``--fix`` moves exactly the ``slop`` entries, so a bundle of a registered repo must not be one."""
    assert (
        wl.verdict(".dadaia/dist/myrepo/0.5.0/rc-1/wt-rc.bundle", False, (), ("myrepo",), ())
        != "slop"
    )
