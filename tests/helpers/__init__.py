"""Shared test helper packages (code, not fixtures).

``tests.helpers.golden_platform`` is the single platform-invariance normalization
layer for byte-golden capture (v0.1.64 FR1) — see its module docstring for the
leak-class taxonomy.

``tests.helpers.subprocess_diag`` is the shared non-blocking subprocess stderr drain
(v0.4.3 T-043-25 / FR18b) used by both the panel e2e diagnostic path and its own
dedicated integration coverage.

``tests.helpers.release_jsonl`` is the shared ``RELEASE.jsonl`` phase-record writer
(v0.5.0 T-050-22) any fixture uses to put a context into a known phase now that
``ACTIVE.md`` is retired (v0.5.0 FR4/T-050-21A).
"""
