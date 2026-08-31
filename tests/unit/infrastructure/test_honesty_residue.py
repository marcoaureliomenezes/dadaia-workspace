"""F015/F016 (20260830-design-bug-surface-audit): honesty residue.

- The first-parent-of-a-sha git fact has ONE implementation (git_objects); ci.py
  delegates instead of hand-rolling a second subprocess with different error modes.
- gate_policy reads no mode token that no writer mints (BOUND_READ retired).
- python_env never re-narrates a failed repack-INSTALL as a failed repack.

Intent: contract; size: unit.
"""

from __future__ import annotations

import inspect


def test_ci_first_parent_delegates_to_the_one_reader() -> None:
    from dadaia_workspace.cli.commands import ci

    src = inspect.getsource(ci._first_parent_sha)
    assert "rev-parse" not in src, "ci.py must not hand-roll the first-parent git fact"
    assert "first_parent" in src


def test_read_modes_contains_only_tokens_a_writer_mints() -> None:
    from dadaia_workspace.features.spec_context import gate_policy

    # The bind CLI persists READ bare and BOUND_<mutating> for mutating modes;
    # BOUND_READ never existed on any write path.
    assert frozenset({"READ"}) == gate_policy._READ_MODES


def test_python_env_narrates_a_failed_repack_install_honestly() -> None:
    from dadaia_workspace.infrastructure import python_env

    src = inspect.getsource(python_env)
    assert "except subprocess.CalledProcessError:\n                        pass" not in src, (
        "the repack-install failure must not be silently swallowed and re-narrated "
        "as a repack failure"
    )
    assert "re-packed running distribution" in src


def test_handoff_index_docstring_claims_no_phantom_facade() -> None:
    from dadaia_workspace.core import handoff_index

    doc = handoff_index.__doc__ or ""
    assert "is a thin\npublic-facing re-export" not in doc
    assert "``features/handoff.py`` (this candidate's" not in doc
