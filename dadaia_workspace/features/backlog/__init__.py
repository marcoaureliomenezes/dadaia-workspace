"""Backlog-consistency foundation (release v0.1.25 R1).

Pure feature modules — no I/O outside explicitly-injected roots (SPEC §3.8 #6):

* ``subject_registry`` — the canonical-subject registry (the linchpin); auto-derives five
  anchor kinds from live truth + an operator alias map; ``bind`` HALTs on unresolved/ambiguous.
* ``classifier`` — the Python-disposes, fail-closed conflict classifier.
* ``ledger`` — the ``consumed_backlog`` sidecar reader (BL-STALE feed; R1 reads only).
* ``preview`` — the read-only resolve/preview surface.
* ``doctor`` — ``backlog doctor`` (BL-SCHEMA/DUP/CONFLICT/STALE).
"""
