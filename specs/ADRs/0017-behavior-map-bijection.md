# ADR 0017 — Every behavior surface maps to exactly one law section

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
The always-on law (`DADAIA.md`), the core skills and the scoped `AGENTS.md` files are three
surfaces that describe the same behaviour. Left unmapped they diverge in both directions: a
skill restates a rule the law has since changed, and a law section ends up with no owner to
operate it. The predecessor map modelled a row as "N skills share a topic", which needed a
justification field to excuse sharing; the current model is one row per member, so the
sharing question is structurally gone. Content hashes on each row make a silent edit to a
mapped source visible — re-recording a hash is a review act, not a side effect.

## Decision
We will map every core skill and every scoped `AGENTS.md` source to exactly one `DADAIA.md`
section, and every section to at least one owner, through a single map file, a single schema
and a single enforcer; content hashes are re-recorded only by review.

## Consequences
+ A skill added without a home section, or a law section left unowned, goes red immediately.
+ There is one enforcer, not two — the retired map, its schema and its enforcer were deleted
  in the same commit that introduced this one.
− Every new skill or scoped `AGENTS.md` costs a map row and a hash tuple.
− Editing a mapped source requires re-recording its hash deliberately.

## Confirmation
Measured by: `pytest -p no:cacheprovider tests/contract/test_behavior_map.py` (one row per
member, section coverage, hash tuples, citation check, invocation grants).
