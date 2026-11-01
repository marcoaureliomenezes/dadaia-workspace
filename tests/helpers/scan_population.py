"""The scan-test vacuity guard: a test that scans a population of files asserts, at its
own call site, that the population is non-empty and holds one known sentinel, so a
mis-rooted walker fails loudly instead of scanning nothing and passing green.

A convention, not a scan harness: each detector stays with its own rule.
"""

from __future__ import annotations

from collections.abc import Collection


def assert_populated[T](population: Collection[T], sentinel: T) -> None:
    assert population, "scan found nothing — mis-rooted walker?"
    assert sentinel in population, f"sentinel {sentinel!r} missing from the scanned population"
