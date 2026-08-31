"""Bug lifecycle-accepts-noncanonical-release-id (retest): ONE release-id contract.

Every public entry point (release new, scaffolder, specs doctor
SPEC-DOC-027) validates against the SAME central canon.

T-050-06A (SPEC FR1 boundary 2a / AS-13) flips the axis: the current, mintable form is
bare ``MAJOR.MINOR.PATCH`` with an optional ``-suffix`` segment (rc/canary/hotfix flows
are legitimate); a ``v``-prefixed id is the retired axis, still matched by
``RELEASE_SEMVER_RE`` for archived-directory lookups but refused by the mint predicate
``is_release_semver``. This inverts the earlier "v-prefixed is canonical" assertions
below under a recorded ``qa-engineer`` verdict — never deleted to go green.
"""

from __future__ import annotations

from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE, is_release_semver


def test_canon_accepts_plain_and_suffixed_bare_semver() -> None:
    for good in ("0.0.1", "1.2.3", "0.0.1-livecanary", "0.1.0-rc1", "2.0.0-alpha.2"):
        assert RELEASE_SEMVER_RE.match(good), good
        assert is_release_semver(good), good


def test_canon_rejects_noncanonical_ids() -> None:
    for bad in ("valgame-v0.1.0", "release1", "v1.2", "v1.2.3-", "v1.2.3 x"):
        assert not RELEASE_SEMVER_RE.match(bad), bad


def test_v_prefixed_axis_resolves_but_never_mints() -> None:
    """AS-13: RELEASE_SEMVER_RE still matches the retired v-prefixed axis (archived
    directories must still resolve), but is_release_semver — the mint predicate — never
    accepts it."""
    for archived in ("v0.0.1", "v1.2.3", "v0.1.0-rc1"):
        assert RELEASE_SEMVER_RE.match(archived), archived
        assert not is_release_semver(archived), archived


def test_canon_path_fragment_is_derived_from_the_one_pattern() -> None:
    """F004 (20260830 audit): canon.py's path-regex release-id fragment must BE the
    core-derived fragment, not a re-typed bare ``\\d+.\\d+.\\d+`` copy. Intent:
    contract; size: unit."""
    from dadaia_workspace.core.specs_version import RELEASE_ID_FRAGMENT, RELEASE_SEMVER_RE
    from dadaia_workspace.features.specs import canon

    assert canon._SEMVER is RELEASE_ID_FRAGMENT
    # Mechanical derivation from the ONE compiled object — never a second hand copy
    # (the suffix group is neutralized to non-capturing so embedding never shifts a
    # consumer regex's group indices; bash's POSIX ERE keeps the capturing form).
    assert (
        RELEASE_SEMVER_RE.pattern.removeprefix("^v?").removesuffix("$").replace("(-", "(?:-")
    ) == RELEASE_ID_FRAGMENT


def test_suffixed_release_id_is_canon_conformant() -> None:
    """F004: a suffixed id (rc/canary/hotfix — legitimate per AS-13) passed the naming
    checks while TREE-8 errored every file under it. One decider: canon paths accept
    exactly what the naming canon accepts on the bare axis. Intent: regression;
    size: unit."""
    from dadaia_workspace.features.specs.canon import is_canon_path

    assert is_canon_path("releases/0.6.0-rc1/SPEC.md")
    assert is_canon_path("releases/0.6.0-rc1/RELEASE.json")
    assert is_canon_path("releases/_archive/0.6.0-rc1/SPEC.md")
