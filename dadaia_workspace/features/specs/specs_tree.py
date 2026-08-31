"""SpecsTree — the parsed snapshot of shared specs facts (F010, 20260830 audit).

Before this module every validator owned raw filesystem access: RELEASE.json was
re-read and re-parsed by four checks per doctor run, so rules could observe different
states mid-run and re-derive shared facts independently. A ``SpecsTree`` is built
FRESH at the start of every ``SpecsDoctor.check()`` run and handed to the validators;
its sections are lazy and cached for the lifetime of that one run.

Contract (the fix/check freshness rule): checks read the tree; fixes take paths and
mutate the filesystem; after fixing, the next ``check()`` builds a fresh tree — a
snapshot NEVER survives a mutation pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from dadaia_workspace.features.specs.doctor_common import resolve_active_release

__all__ = ["ActiveRelease", "SpecsTree"]


@dataclass(frozen=True)
class ActiveRelease:
    """The one shared answer to "which release is live, in which phase"."""

    release: str
    phase: str | None
    error: str | None


class SpecsTree:
    """Lazy, run-scoped snapshot over one ``specs/`` directory."""

    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir

    @cached_property
    def active_release(self) -> ActiveRelease:
        """Parsed ONCE per run — the four per-check re-reads collapse here."""
        release, phase, error = resolve_active_release(self.specs_dir)
        return ActiveRelease(release=release, phase=phase, error=error)
