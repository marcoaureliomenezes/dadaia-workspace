"""Bug lifecycle-accepts-noncanonical-release-id (retest): ONE release-id contract.

Every public entry point (lifecycle verbs, release new, scaffolder, specs doctor
SPEC-DOC-027) validates against the SAME central canon — vMAJOR.MINOR.PATCH with an
optional -suffix segment (rc/canary/hotfix flows are legitimate).
"""

from __future__ import annotations

from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE, is_release_semver


def test_canon_accepts_plain_and_suffixed_semver() -> None:
    for good in ("v0.0.1", "v1.2.3", "v0.0.1-livecanary", "v0.1.0-rc1", "v2.0.0-alpha.2"):
        assert RELEASE_SEMVER_RE.match(good), good
        assert is_release_semver(good), good


def test_canon_rejects_noncanonical_ids() -> None:
    for bad in ("valgame-v0.1.0", "release1", "0.1.0", "v1.2", "v1.2.3-", "v1.2.3 x"):
        assert not RELEASE_SEMVER_RE.match(bad), bad
