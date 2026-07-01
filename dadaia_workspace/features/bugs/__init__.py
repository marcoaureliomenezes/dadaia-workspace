"""Event-sourced bug telemetry (release v0.1.46 AC-1/AC-2).

Pure feature modules — no I/O outside the injected store:

* ``service`` — ``BugService`` folds an append-only event stream into current per-``bug_id``
  state (``status``) and aggregates (``stats``).

The :class:`~dadaia_workspace.core.models.bugs.BugEvent` domain model, event-kind enum,
terminal set, and the ``notes`` redaction helper live in ``core/models/bugs.py`` — the
bottom layer both ``infrastructure`` and ``features`` may import. Field set mirrors
``public/schemas/bugs/bug-event-v1.schema.json``. The append-only JSONL persistence lives
in ``infrastructure/jsonl_bug_store.py``.
"""

from __future__ import annotations
