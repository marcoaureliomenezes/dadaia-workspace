"""One record per bug — bug-record-v1, immutable core, mutable governance (v0.5.0 FR2).

Pure feature modules — no I/O outside the injected store:

* ``service`` — ``BugService`` is the one write seam (AS-16) plus the read view over
  the ledger (register/update/transition/archive/status/stats).

The :class:`~dadaia_workspace.core.models.bugs.BugRecord` domain model — its
:meth:`~dadaia_workspace.core.models.bugs.BugRecord.resolve`/:meth:`supersede`/
:meth:`defer`/:meth:`reject` transitions (v0.5.1 K5 deepening: status is unreachable
without its own required fields — ``governance_completeness_gaps``, the WARN-only
completeness detector these transitions replace, is deleted) and its
:func:`~dadaia_workspace.core.models.bugs.immutable_core_drift` WARN-only diagnostic —
and the ``notes``/free-text redaction helper live in ``core/models/bugs.py`` — the
bottom layer both ``infrastructure`` and ``features`` may import. Field set mirrors
``public/schemas/bugs/bug-record-v1.schema.json``. Persistence is the generic,
model-agnostic ``infrastructure/jsonl_record_store.py``, injected via
``container.build_bug_record_store``/``build_bug_archive_store``.
"""

from __future__ import annotations
