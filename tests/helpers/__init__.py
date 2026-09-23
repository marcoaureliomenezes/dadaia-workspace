"""Shared test helper packages (code, not fixtures).

``tests.helpers.golden_platform`` is the single platform-invariance normalization
layer for byte-golden capture (v0.1.64 FR1) — see its module docstring for the
leak-class taxonomy.

``tests.helpers.release_state`` is the shared ``RELEASE.json`` phase-state writer
(v0.5.0 T-050-22, renamed at the RELEASE.json migration) any fixture uses to put a
context into a known phase now that ``ACTIVE.md`` is retired (v0.5.0 FR4/T-050-21A).
"""
