"""F015/F016 (20260830-design-bug-surface-audit): honesty residue.

- The first-parent-of-a-sha git fact has ONE implementation (git_objects); ci.py
  delegates instead of hand-rolling a second subprocess with different error modes.
- gate_policy reads no mode token that no writer mints (BOUND_READ retired).
- python_env never re-narrates a failed repack-INSTALL as a failed repack.

Intent: contract; size: unit.
"""

from __future__ import annotations

import inspect


def test_python_env_narrates_a_failed_repack_install_honestly() -> None:
    from dadaia_workspace.infrastructure import python_env

    src = inspect.getsource(python_env)
    assert "except subprocess.CalledProcessError:\n                        pass" not in src, (
        "an install failure must not be silently swallowed and re-narrated as another"
    )
    # The paired assertion on the fallback's own narration ("re-packed running
    # distribution") died with the fallback itself (bug
    # init-venv-installs-index-version-not-running-distribution): there is one install
    # now, so there is no second failure to narrate as the first.


def test_handoff_index_docstring_claims_no_phantom_facade() -> None:
    from dadaia_workspace.core import handoff_index

    doc = handoff_index.__doc__ or ""
    assert "is a thin\npublic-facing re-export" not in doc
    assert "``features/handoff.py`` (this candidate's" not in doc
