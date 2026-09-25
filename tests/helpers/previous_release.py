"""The release the onboarding journey upgrades FROM: the newest final release on the
index not newer than the source — never the source by assumption, which release-please
bumps to an unpublished version on the release PR."""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Iterable

from packaging.version import Version

_INDEX = "https://pypi.org/pypi/dadaia-workspace/json"


def previous_release(source: str, published: Iterable[str]) -> str:
    ceiling = Version(source)
    candidates = [v for v in map(Version, published) if not v.is_prerelease and v <= ceiling]
    return str(max(candidates))


def published_releases() -> list[str]:
    with urllib.request.urlopen(_INDEX, timeout=30) as response:  # noqa: S310 — fixed https URL
        return list(json.load(response)["releases"])
