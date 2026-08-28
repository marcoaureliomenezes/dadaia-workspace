"""One record per bug — bug-record-v1, immutable core, mutable governance (v0.5.0 FR2).

Pure feature modules — no I/O outside the injected store:

* ``service`` — ``BugService`` is the one write seam (AS-16) plus the read view over
  the ledger (register/update/archive/status/stats/coherence_violations).
* ``migrate_v5`` — the deletable v5-event-shape boundary adapter the live ledger still
  needs until FR3/T-050-10 physically migrates it (A2.5); imported by nothing outside
  this package.

The :class:`~dadaia_workspace.core.models.bugs.BugRecord` domain model, its
:func:`~dadaia_workspace.core.models.bugs.governance_completeness_gaps` and
:func:`~dadaia_workspace.core.models.bugs.immutable_core_drift` WARN-only diagnostics,
and the ``notes``/free-text redaction helper live in ``core/models/bugs.py`` — the
bottom layer both ``infrastructure`` and ``features`` may import. Field set mirrors
``public/schemas/bugs/bug-record-v1.schema.json``. Persistence is the generic,
model-agnostic ``infrastructure/jsonl_record_store.py``, injected via
``container.build_bug_record_store``/``build_bug_archive_store``.
"""

from __future__ import annotations
