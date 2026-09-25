"""The upgrade journey starts from a release that is really on the index.

Intent: CONTRACT — e2e-upgrade-previous-version-equals-source-version.

Owner: dd-software-engineer.
"""

from __future__ import annotations

from tests.helpers.previous_release import previous_release

_PUBLISHED = ("0.4.2", "0.4.4", "0.4.5", "0.4.6", "0.4.7", "0.5.0rc1")


def test_a_source_bumped_past_the_index_upgrades_from_the_newest_published() -> None:
    assert previous_release("0.5.0", _PUBLISHED) == "0.4.7"


def test_a_source_already_published_upgrades_from_itself() -> None:
    assert previous_release("0.4.7", _PUBLISHED) == "0.4.7"
