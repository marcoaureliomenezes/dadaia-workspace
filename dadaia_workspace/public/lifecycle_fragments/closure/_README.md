# closure — no step fragments (generic worker)

The `closure` workflow runs today: `dadaia lifecycle close` advances a release from
CODE_REVIEW to CLOSURE via a single generic product-engineer worker step, followed by a
Python-owned removal gate that applies residual-aware backlog removal over the
consumed-ledger. That close step is **generic** — it carries no fragment — so this
directory ships no step fragment. This stub exists only because the fragment loader
requires the workflow directory to be present.

The authoritative step definition lives in the `dadaia lifecycle close` verb and the
workflow catalog, not here. Author a per-step closure fragment in this directory only if
the close step is ever migrated off the generic prompt.
