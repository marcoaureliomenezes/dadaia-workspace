# ADR 0011 — File I/O enters `core` only through an authorized set

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
The two layering contracts over `core` guard *imports* — upward edges and OS primitives —
and neither says anything about a call to `open(...)` or `Path.write_text`. So the file-I/O
purity of the bottom ring was undecided and unenforced: any `core` module could quietly start
touching the filesystem, which makes it untestable without a temp tree and puts I/O errors
below every ring that depends on it. The architect's disposition (A9) was to guard rather
than relocate: a named set of modules is allowed to do I/O, everything else in `core` is pure.
The guard is an AST walk, not a grep, so a dictionary key named `"open"` never false-fires and
an attribute call like `p.read_text()` never slips through.

## Decision
We will keep `core` file-I/O pure outside an authorized set of modules; new file I/O enters
`core` only by joining that set on purpose, with the rationale recorded where the set is
declared.

## Consequences
+ `core` stays unit-testable without a filesystem, and I/O failure modes stay where an adapter
  can handle them.
+ Accidental I/O — the "just read the file here" edit — fails immediately with the offending
  call site named.
− Adding a legitimate I/O module is a deliberate, reviewed change to the authorized set.
− The guard is call-shaped: an I/O path reached through an injected port is invisible to it by
  design (ports are ADR 0001's business, not this one's).

## Confirmation
Measured by: `pytest -p no:cacheprovider tests/contract/test_core_file_io_purity.py` (AST walk
over `dadaia_workspace/core/**/*.py`; every authorized stem must exist on disk).
