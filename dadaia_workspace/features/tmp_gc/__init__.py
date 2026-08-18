"""``dadaia_workspace.features.tmp_gc`` — FR29/T-043-44, the orphan backstop.

See :mod:`dadaia_workspace.features.tmp_gc.service` for the full doctrine and
implementation. This package's public surface is exactly the two names below.
"""

from __future__ import annotations

from dadaia_workspace.features.tmp_gc.service import TmpGcOutcome, run_tmp_gc

__all__ = ["TmpGcOutcome", "run_tmp_gc"]
