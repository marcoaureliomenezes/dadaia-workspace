# ADR 0009 — One context-resolution authority

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
"Which Spec Context am I in?" was answered in several places, each with its own fallback
ladder, so a verb, a hook and the container could disagree about the same working directory.
Family F2 of the 0.5.0 forensic is precisely that: per-command patches that each fixed one
caller's answer and left the others. The release's ruling was that no further per-command
patch is accepted — the ladder and its side channels are deleted and one function,
`core.specs_resolver.resolve_context`, carries the law of `DADAIA.md` §3 verbatim. Exactly
three homes may import it directly: the CLI seam `cli._specs_resolution`, `container`, and
`hooks` (sanctioned by ADR 0012's hot-path argument).

## Decision
We will resolve a Spec Context in exactly one place — `core.specs_resolver.resolve_context` —
imported directly only by `cli._specs_resolution`, `container` and `hooks`; every other module
reaches it through the seam or the container.

## Consequences
+ One answer per working directory: the CLI, the container and a gated write agree by
  construction.
+ A regression in resolution has one file to fix and one test surface to cover.
− A verb that wants a variant behaviour must change the authority (and everyone's answer)
  rather than special-case itself — deliberately expensive.
− The contract's source list enumerates every verb module, so a new verb must be added to it.

## Confirmation
Measured by: `lint-imports --config setup.cfg --no-cache` — contract
`bind-resolution-seam-is-a-single-home` (zero `ignore_imports`; no edge has ever been
accepted as debt here).
